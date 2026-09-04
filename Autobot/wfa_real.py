# -*- coding: utf-8 -*-
"""Compara os TRES jeitos que este projeto tem (ou pode ter) de medir se um
campeao ja aprovado se sustenta fora da amostra:

  holdout   O que o circuito ja usa hoje: UM conjunto de parametros (o
            campeao, travado), medido em segmentos IS/OOS intercalados
            DENTRO de um unico passe (AtivarWFO=true, o mecanismo interno da
            EA). Barato (~35s, um passe so). NAO reotimiza -- e o mesmo
            numero que optimize_two_stage.py ja mede no Estagio 4/gate
            relativo, so que reusado aqui pra virar um dos tres lados da
            comparacao.

  forward   O holdout NATIVO do MT5 (ForwardMode no .ini): o tester corta o
            periodo sozinho, o genetico ve so a parte de tras, os melhores
            candidatos sao reexecutados na parte forward automaticamente.
            NUNCA foi exercitado neste projeto antes (achado da auditoria de
            2026-09-04: escrever_ini() ja aceita o parametro `forward`, mas
            wfo_matrix.py -- o unico chamador -- sempre passa 0/desligado).
            O formato do relatorio headless pra forward nao esta documentado
            no manual local nem foi validado ao vivo aqui -- ver o aviso que
            este modo imprime.

  wfa       WFA DE VERDADE (Pardo): reotimiza a cada janela -- N passes do
            genetico, um por periodo, curva OOS concatenada entre eles. O
            unico dos tres que responde "por quanto tempo um parametro
            continua bom antes de precisar reajuste".

MESMA formula de WFE nos tres, pra comparacao ser correta (mesma unidade que
a EA ja usa no proprio relatorio OnDeinit -- "Out-of-Sample Retention"):

    WFE = (lucro_OOS / dias_OOS) / (lucro_IS / dias_IS) * 100

Nao entra no laco automatico de campanha.py -- roda so sobre um campeao
JA VALIDADO (--symbol/--sistema/--variante, ou --todos pra iterar a
biblioteca inteira). Ferramenta pos-hoc, no mesmo espirito que wfo_matrix.py
ja e hoje.

Uso:
    python wfa_real.py --symbol XAUUSD --sistema 12_GRID_INVERSO \\
        --variante BUY_MULTI --from 2023.09.04 --to 2026.09.04 \\
        --modo todos --ciclos 6

    python wfa_real.py --todos --modo holdout   # so os campeoes atuais, so o barato
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import optimize_sets as base
import optimize_two_stage as ots
import ready_library
from mt5_runner import garantir_terminal_livre

AQUI = Path(__file__).resolve().parent
SAIDA_DIR = AQUI / "wfa_real_resultados"
SAIDA_CSV = AQUI / "wfa_real_resumo.csv"


def ler_valores_set(caminho: Path) -> dict[str, str]:
    """Todo parametro do .set como {nome: valor_atual} -- so o primeiro
    campo antes do primeiro "||", igual conferir_set() ja faz em
    optimize_two_stage.py, so exposto como funcao geral aqui.

    Le direto do .set VALIDADO_ em vez do ledger de proposito (achado desta
    sessao: carregar_campeao_atual() devolve {} pra varios combos que tem
    arquivo real mas nunca foram registrados no ledger -- ler o .set nunca
    tem esse buraco, o arquivo E o campeao).
    """
    saida: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-16").replace("\r", "").split("\n"):
        if "=" in linha and not linha.startswith(";"):
            nome, valor = linha.split("=", 1)
            saida[nome] = valor.split("||")[0]
    return saida


def janelas_sequenciais(inicio: str, fim: str, ciclos: int, is_dias: int,
                        oos_dias: int) -> list[tuple[str, str, str, str]]:
    """[(is_inicio, is_fim, oos_inicio, oos_fim), ...] -- janelas lado a
    lado, sem sobreposicao, mesma convencao de janelas_wfo()/dimensionar_wfo
    (ver optimize_two_stage.py:2129-2138: deslizante infla a WFE porque
    IsInSample()/WfoCycleOf() passam a discordar sobre a mesma barra --
    aqui isso nao se aplica de verdade, mas manter sequencial evita um
    segundo conceito de "rolling" novo no codigo).
    """
    d0 = datetime.strptime(inicio, "%Y.%m.%d")
    janelas = []
    cursor = d0
    for _ in range(ciclos):
        is_ini = cursor
        is_fim = is_ini + timedelta(days=is_dias - 1)
        oos_ini = is_fim + timedelta(days=1)
        oos_fim = oos_ini + timedelta(days=oos_dias - 1)
        janelas.append((is_ini.strftime("%Y.%m.%d"), is_fim.strftime("%Y.%m.%d"),
                        oos_ini.strftime("%Y.%m.%d"), oos_fim.strftime("%Y.%m.%d")))
        cursor = oos_fim + timedelta(days=1)
    return janelas


def wfe(lucro_oos: float | None, dias_oos: int, lucro_is: float | None,
       dias_is: int) -> float | None:
    """(lucro_OOS/dias_OOS) / (lucro_IS/dias_IS) * 100 -- mesma formula que
    o .mq5 ja usa em OnDeinit (avgProfitOutSample/avgProfitInSample*100),
    reusada aqui pra a comparacao entre os 3 modos ser na MESMA unidade.

    None quando o IS nao foi lucrativo -- mesmo criterio do .mq5: "a WFE so
    tem significado com In-Sample LUCRATIVO... Nao ha nada a preservar
    quando a estrategia ja falhou na amostra."
    """
    if lucro_is is None or lucro_oos is None or dias_is <= 0 or dias_oos <= 0:
        return None
    media_is = lucro_is / dias_is
    if media_is <= 0.0001:
        return None
    media_oos = lucro_oos / dias_oos
    return media_oos / media_is * 100.0


# ---------------------------------------------------------------------------
# Modo 1: holdout -- o que o circuito ja usa hoje, reusado como-esta
# ---------------------------------------------------------------------------

def medir_holdout(origem: Path, travados: dict, symbol: str, periodo: str,
                  inicio: str, fim: str, deposito: int) -> dict:
    """UM passe, campeao travado, holdout interno da EA (janelas_wfo)."""
    t0 = time.time()
    wfo = ots.janelas_wfo(inicio, fim)
    passo = dict(wfo, **travados, MetodoDeEntradawfo="1",
                InterfaceLanguage="1")
    r = ots._medir_desempenho(origem, passo, symbol, periodo, inicio, fim,
                              deposito)
    return {"modo": "holdout", "segundos": time.time() - t0,
           "passes_mt5": 1, "retencao_pct": r.get("retencao"),
           "expectancy_r": r.get("expectancy_r"),
           "profit": r.get("profit"), "metricas": r, "detalhe": None}


# ---------------------------------------------------------------------------
# Modo 2: forward -- ForwardMode nativo do MT5, NUNCA exercitado antes
# ---------------------------------------------------------------------------

def medir_forward(origem: Path, travados: dict, symbol: str, periodo: str,
                  inicio: str, fim: str, deposito: int, timeout: int,
                  forward: int = 3) -> dict:
    """Optimization=2 com ForwardMode ligado -- o tester corta sozinho e
    reexecuta os melhores candidatos na parte de tras.

    AVISO DE CONFIANCA (auditoria 2026-09-04): este mecanismo nunca foi
    exercitado neste projeto -- escrever_ini() ja aceita `forward` desde
    sempre, mas o unico chamador (wfo_matrix.py) sempre passa 0. O formato
    do relatorio headless com ForwardMode ligado NAO esta documentado no
    manual local nem foi validado ao vivo aqui. `ler_relatorio()` junta
    TODAS as linhas <Row> do XML sem distinguir worksheet -- se o forward
    sair numa aba separada com colunas diferentes, a leitura abaixo pode
    ficar sutilmente errada sem erro nenhum. Por isso os campos vem
    marcados "confianca=baixa ate verificar ao vivo" -- NAO tratar como
    numero comparavel aos outros dois modos sem antes abrir o .xml/.htm
    bruto desta corrida na mao e confirmar o que ele realmente contem.
    """
    t0 = time.time()
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_WFA_FORWARD.set"
    ots.reescrever(origem, trabalho,
                  [], dict(travados, MetodoDeEntradawfo="1", AtivarWFO="false"))
    rel_nome = "wfa_forward"
    for velho in base.DADOS.glob(f"{rel_nome}*"):
        velho.unlink(missing_ok=True)
    antes = base.marcar_logs()
    import tempfile
    from mt5_runner import lancar_terminal
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "forward.ini"
        rel = str(trabalho.relative_to(base.DADOS / "MQL5" / "Profiles" / "Tester"))
        base.escrever_ini(ini, symbol, periodo, rel.replace("/", "\\"),
                          inicio, fim, deposito, 1, 6, rel_nome, forward=forward)
        lancar_terminal(base.TERMINAL, ini, timeout)
    log = base.texto_novo(antes)
    candidatos = sorted(base.DADOS.glob(f"{rel_nome}*"),
                        key=lambda p: (p.suffix.lower() != ".xml", p.name))
    if not candidatos:
        return {"modo": "forward", "segundos": time.time() - t0,
               "passes_mt5": None, "retencao_pct": None, "profit": None,
               "metricas": {}, "confianca": "sem relatorio",
               "detalhe": "nenhum otim_wrx*/wfa_forward* apareceu -- "
                          "verificar o log bruto."}
    cab, linhas = base.ler_relatorio(candidatos[0])
    m = re.search(r"local (\d+) tasks", log)
    passes = int(m.group(1)) if m else None
    if not linhas or "Profit" not in cab:
        return {"modo": "forward", "segundos": time.time() - t0,
               "passes_mt5": passes, "retencao_pct": None, "profit": None,
               "metricas": {}, "confianca": "relatorio sem coluna Profit",
               "detalhe": f"relatorio: {candidatos[0].name}"}
    # Best-effort: pega a MELHOR linha por lucro -- se o forward realmente
    # reexecutou os campeoes na parte de tras, ESTA linha e o resultado
    # forward; se o relatorio so trouxe o back-test in-sample (formato nao
    # confirmado), este numero mede outra coisa e o campo `confianca` avisa.
    aptos = base.escolher_candidatos(cab, linhas, 1, 0.0)
    lucro = base.num(aptos[0][cab.index("Profit")]) if aptos else None
    return {"modo": "forward", "segundos": time.time() - t0,
           "passes_mt5": passes, "retencao_pct": None, "profit": lucro,
           "metricas": {"profit": lucro}, "confianca": "BAIXA -- nunca "
           "validado ao vivo, ver docstring de medir_forward()",
           "detalhe": f"relatorio: {candidatos[0].name}, {len(linhas)} linhas"}


# ---------------------------------------------------------------------------
# Modo 3: wfa -- reotimiza por janela, curva OOS concatenada, WFE de verdade
# ---------------------------------------------------------------------------

def medir_wfa(origem: Path, travados: dict, numeros: list[str], symbol: str,
             sistema: str, periodo: str, inicio: str, fim: str,
             deposito: int, ciclos_alvo: int, timeout: int,
             taxa_anual: float = 33.0) -> dict:
    """Reotimiza dentro de CADA janela IS (OHLC, Optimization=2) e mede o
    vencedor da janela no OOS correspondente (tick real, 1 passe).
    """
    t0 = time.time()
    dias_totais = (datetime.strptime(fim, "%Y.%m.%d")
                  - datetime.strptime(inicio, "%Y.%m.%d")).days
    ciclos, is_dias, oos_dias = ots.dimensionar_wfo(dias_totais, ciclos_alvo)
    janelas = janelas_sequenciais(inicio, fim, ciclos, is_dias, oos_dias)
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_WFA_JANELA.set"

    detalhe = []
    total_passes = 0
    lucro_is_acumulado = 0.0
    lucro_oos_acumulado = 0.0
    dias_is_validos = 0
    dias_oos_validos = 0
    wfes = []

    for i, (is_ini, is_fim, oos_ini, oos_fim) in enumerate(janelas, 1):
        piso = ots.piso_trades_da_janela(is_ini, is_fim, taxa_anual)
        n = ots.reescrever(origem, trabalho, numeros, travados)
        cab, linhas = ots.rodar(trabalho, symbol, periodo, is_ini, is_fim,
                                deposito, 1, timeout)
        total_passes += len(linhas)
        aptos = base.escolher_candidatos(cab, linhas, piso, 1.0) if linhas else []
        if not aptos:
            detalhe.append({"janela": i, "is": [is_ini, is_fim],
                            "oos": [oos_ini, oos_fim],
                            "motivo": "nenhum candidato passou o piso "
                                     f"({piso} trades) na busca IS"})
            continue
        vencedor_janela = {c: v for c, v in zip(cab, aptos[0])
                           if c not in ("Pass", "Result", "Profit",
                                       "Profit Factor", "Expected Payoff",
                                       "Recovery Factor", "Sharpe Ratio",
                                       "Custom", "Equity DD %", "Trades")}
        lucro_is = base.num(aptos[0][cab.index("Profit")])
        oos_r = ots._medir_desempenho(origem, dict(travados, **vencedor_janela),
                                      symbol, periodo, oos_ini, oos_fim, deposito)
        lucro_oos = oos_r.get("profit")
        wfe_i = wfe(lucro_oos, oos_dias, lucro_is, is_dias)
        detalhe.append({"janela": i, "is": [is_ini, is_fim],
                        "oos": [oos_ini, oos_fim], "lucro_is": lucro_is,
                        "lucro_oos": lucro_oos, "wfe_pct": wfe_i,
                        "params": vencedor_janela})
        if lucro_is > 0:
            lucro_is_acumulado += lucro_is
            dias_is_validos += is_dias
        if lucro_oos is not None:
            lucro_oos_acumulado += lucro_oos
            dias_oos_validos += oos_dias
        if wfe_i is not None:
            wfes.append(wfe_i)

    wfe_global = wfe(lucro_oos_acumulado if dias_oos_validos else None,
                     dias_oos_validos, lucro_is_acumulado if dias_is_validos else None,
                     dias_is_validos)
    media = sum(wfes) / len(wfes) if wfes else None
    desvio = ((sum((w - media) ** 2 for w in wfes) / len(wfes)) ** 0.5
             if wfes and len(wfes) > 1 else None)
    return {"modo": "wfa", "segundos": time.time() - t0,
           "passes_mt5": total_passes, "ciclos": ciclos,
           "is_dias": is_dias, "oos_dias": oos_dias,
           "wfe_global_pct": wfe_global, "wfe_media_pct": media,
           "wfe_desvio_pct": desvio,
           "ciclos_positivos": f"{sum(1 for w in wfes if w > 0)}/{len(wfes)}",
           "detalhe": detalhe}


# ---------------------------------------------------------------------------

def rodar_combo(symbol: str, sistema: str, variante: str, inicio: str,
                fim: str, deposito: int, modos: list[str], ciclos: int,
                timeout: int) -> dict:
    validado = (ready_library.TESTER /
               f"VALIDADO_{symbol.replace('.', '_')}_{sistema}_{variante}.set")
    if not validado.exists():
        return {"erro": f"sem campeao VALIDADO_ para {symbol}/{sistema}/{variante}"}
    origem = base.achar_set(symbol, sistema, variante)
    if origem is None:
        return {"erro": f"template de origem nao encontrado para {symbol}/{sistema}"}

    valores = ler_valores_set(validado)
    ind = valores.get("EntryIndicator")
    escrita_campos = ots.ESCRITA | {"selectedFormula"}
    travados = {k: v for k, v in valores.items() if k in escrita_campos
               or k in ots.NUMEROS}
    numeros = ots.eixos_reotimizaveis(sistema, ind)

    resultado = {"simbolo": symbol, "sistema": sistema, "variante": variante,
                "de": inicio, "ate": fim, "indicador": ind}
    if "holdout" in modos:
        print(f"    [holdout] rodando (1 passe, ~35s)...", flush=True)
        resultado["holdout"] = medir_holdout(origem, travados, symbol, "M1",
                                             inicio, fim, deposito)
    if "forward" in modos:
        print(f"    [forward] rodando (Optimization=2, ForwardMode)...",
              flush=True)
        resultado["forward"] = medir_forward(origem, travados, symbol, "M1",
                                             inicio, fim, deposito, timeout)
    if "wfa" in modos:
        print(f"    [wfa] rodando ({ciclos} janelas, reotimiza cada uma)...",
              flush=True)
        resultado["wfa"] = medir_wfa(origem, travados, numeros, symbol,
                                     sistema, "M1", inicio, fim, deposito,
                                     ciclos, timeout)
    return resultado


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol")
    ap.add_argument("--sistema")
    ap.add_argument("--variante", default="BUY_MULTI")
    ap.add_argument("--todos", action="store_true",
                    help="roda sobre TODOS os VALIDADO_*.set atuais, "
                         "ignorando --symbol/--sistema/--variante")
    ap.add_argument("--from", dest="inicio", default="2023.09.04")
    ap.add_argument("--to", dest="fim", default=datetime.now().strftime("%Y.%m.%d"))
    ap.add_argument("--deposit", type=int, default=10000)
    ap.add_argument("--ciclos", type=int, default=6)
    ap.add_argument("--modo", default="holdout,wfa",
                    help="lista separada por virgula entre holdout,forward,wfa "
                         "(default: holdout,wfa -- forward e opt-in de "
                         "proposito, ver AVISO DE CONFIANCA na docstring)")
    ap.add_argument("--timeout", type=int, default=21600)
    ap.add_argument("--fechar-terminal", action="store_true")
    args = ap.parse_args()

    garantir_terminal_livre(fechar=args.fechar_terminal, terminal=base.TERMINAL)
    modos = [m.strip() for m in args.modo.split(",") if m.strip()]

    if args.todos:
        combos = []
        for p in sorted(ready_library.TESTER.glob("VALIDADO_*.set")):
            meio = p.stem[len("VALIDADO_"):]
            for sistema in ots.FORMULA_POR_SISTEMA:
                marcador = f"_{sistema}_"
                if marcador in meio:
                    simbolo, variante = meio.split(marcador, 1)
                    combos.append((simbolo, sistema, variante))
                    break
    else:
        if not (args.symbol and args.sistema):
            print("Precisa de --symbol e --sistema (ou --todos).")
            return 1
        combos = [(args.symbol, args.sistema, args.variante)]

    SAIDA_DIR.mkdir(exist_ok=True)
    linhas_csv = []
    for simbolo, sistema, variante in combos:
        print(f"\n=== {simbolo} {sistema} {variante} | {args.inicio}..{args.fim} "
              f"| modos: {modos} ===", flush=True)
        resultado = rodar_combo(simbolo, sistema, variante, args.inicio,
                               args.fim, args.deposit, modos, args.ciclos,
                               args.timeout)
        if "erro" in resultado:
            print(f"    {resultado['erro']}")
            continue
        destino = SAIDA_DIR / f"{simbolo}__{sistema}__{variante}.json"
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        for modo in modos:
            r = resultado.get(modo, {})
            print(f"    [{modo}] {json.dumps(r, ensure_ascii=False)[:300]}")
        linhas_csv.append({
            "simbolo": simbolo, "sistema": sistema, "variante": variante,
            "holdout_wfe_ou_expectancy": resultado.get("holdout", {}).get("retencao_pct"),
            "forward_profit": resultado.get("forward", {}).get("profit"),
            "forward_confianca": resultado.get("forward", {}).get("confianca"),
            "wfa_wfe_global_pct": resultado.get("wfa", {}).get("wfe_global_pct"),
            "wfa_ciclos_positivos": resultado.get("wfa", {}).get("ciclos_positivos"),
            "wfa_passes_mt5": resultado.get("wfa", {}).get("passes_mt5"),
            "wfa_segundos": resultado.get("wfa", {}).get("segundos"),
        })

    if linhas_csv:
        campos = list(linhas_csv[0].keys())
        with SAIDA_CSV.open("w", encoding="utf-8") as fh:
            fh.write(",".join(campos) + "\n")
            for linha in linhas_csv:
                fh.write(",".join(str(linha.get(c, "")) for c in campos) + "\n")
        print(f"\nResumo: {SAIDA_CSV}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
