# -*- coding: utf-8 -*-
"""Mantem a biblioteca de sets alinhada com a conta real e com os interesses.

O gerador monta os 3.738 sets a partir de premissas genericas: lote 0.01,
simbolo sem sufixo, capital indefinido. Na conta de verdade nada disso e
verdade -- o broker usa "EURUSDm" ou "XAUUSD.r", o lote minimo pode ser 0.10,
o saldo muda, e voce nao vai otimizar 89 ativos ao mesmo tempo.

Este manager le a conta pelo terminal e reescreve o que precisa:

  SIMBOLO   descobre o nome real no broker (com sufixo) e escreve nos sets;
            avisa quais ativos o broker nao oferece
  LOTE      ajusta ao volume minimo e ao passo do simbolo
  RISCO     dimensiona o 1R conforme o saldo e o teto de risco do perfil
  ESCOPO    mantem so os sets que interessam agora, arquivando o resto

Sem MetaTrader5 conectado, roda em modo seco: usa o perfil e avisa o que nao
pode verificar.

Uso:
    python auto_set_manager.py --perfil meu_perfil.json
    python auto_set_manager.py --criar-perfil     # gera um modelo comentado
    python auto_set_manager.py --perfil p.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import wrx_paths
from mt5_runner import fechar_terminal

TERMINAL = wrx_paths.TERMINAL / "MQL5"
SETS = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"
ARCHIVE = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_Arquivados"

PERFIL_MODELO = {
    "_comentario": "Perfil do automatizador de sets do White Rabbit X.",
    "interesses": {
        "_comentario": "Vazio = tudo. Preencha para restringir o escopo.",
        "ativos": ["EURUSD", "GBPUSD", "XAUUSD"],
        "sistemas": ["01_SLTP", "03_TRAIL_ONLY", "04_SLTP_TRAIL"],
        "lados": ["BUY", "SELL"],
        "variantes": ["MULTI", "ICHIMOKU"],
    },
    "risco": {
        "_comentario": (
            "risco_por_trade_pct define o 1R nos sistemas Fixed-R. "
            "lote_fixo vale para grid e recovery, que nao aceitam Fixed-R."),
        "risco_por_trade_pct": 1.0,
        "lote_fixo": 0.01,
        "usar_lote_minimo_do_broker": True,
    },
    "walk_forward": {
        "_comentario": "ligar=false mantem o WFO desligado nos sets.",
        "ligar": False,
        "data_final": "2026.07.21",
        "is_dias": 122,
        "oos_dias": 61,
    },
    "arquivar_fora_do_escopo": False,
}


def carregar_mt5():
    """Devolve o modulo MetaTrader5 conectado, ou None."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 nao instalado: modo seco.")
        return None
    if not mt5.initialize():
        print(f"Terminal nao respondeu ({mt5.last_error()}): modo seco.")
        return None
    return mt5


def conta(mt5) -> dict:
    info = mt5.account_info()
    if info is None:
        return {}
    return {
        "login": info.login,
        "servidor": info.server,
        "moeda": info.currency,
        "saldo": info.balance,
        "alavancagem": info.leverage,
        "hedging": info.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
    }


def mapear_simbolos(mt5, desejados: list[str]) -> dict[str, dict]:
    """Casa o nome canonico com o nome real do broker, sufixo incluido."""
    todos = mt5.symbols_get()
    if not todos:
        return {}
    por_nome = {s.name: s for s in todos}
    encontrados: dict[str, dict] = {}

    for base in desejados:
        alvo = por_nome.get(base)
        if alvo is None:
            # Sufixo do broker: EURUSDm, EURUSD.r, EURUSD-ECN...
            candidatos = [s for s in todos
                          if re.fullmatch(rf"{re.escape(base)}[.\-_a-zA-Z0-9]*",
                                          s.name)]
            # O nome mais curto costuma ser o principal, nao um derivado.
            alvo = min(candidatos, key=lambda s: len(s.name)) if candidatos else None
        if alvo is None:
            continue
        if not alvo.visible:
            mt5.symbol_select(alvo.name, True)
            alvo = mt5.symbol_info(alvo.name) or alvo
        encontrados[base] = {
            "nome": alvo.name,
            "digitos": alvo.digits,
            "volume_min": alvo.volume_min,
            "volume_step": alvo.volume_step,
            "volume_max": alvo.volume_max,
            "contrato": alvo.trade_contract_size,
        }
    return encontrados


def normalizar_lote(valor: float, spec: dict) -> float:
    minimo = spec.get("volume_min", 0.01)
    passo = spec.get("volume_step", 0.01) or 0.01
    maximo = spec.get("volume_max", 100.0)
    passos = round(max(valor, minimo) / passo)
    return min(round(passos * passo, 8), maximo)


def checar_viabilidade(mt5, specs: dict[str, dict], saldo: float,
                       risco_pct: float) -> list[str]:
    """Avisa quando o lote minimo do broker ja estoura o risco pretendido.

    Com saldo pequeno acontece de o menor lote negociavel arriscar mais do que
    o percentual escolhido, para qualquer stop de tamanho razoavel. O Fixed-R
    entao nao consegue respeitar o 1R: ou o EA nao abre, ou abre arriscando
    mais do que o pedido. Melhor descobrir aqui do que no extrato.
    """
    if not mt5 or saldo <= 0 or risco_pct <= 0:
        return []
    risco_moeda = saldo * risco_pct / 100.0
    avisos: list[str] = []
    for base, spec in sorted(specs.items()):
        info = mt5.symbol_info(spec["nome"])
        if info is None or info.trade_tick_value <= 0 or info.trade_tick_size <= 0:
            continue
        # Quanto custa 1 ponto no menor lote possivel.
        pontos_por_unidade = info.point / info.trade_tick_size
        custo_ponto = info.trade_tick_value * pontos_por_unidade * spec["volume_min"]
        if custo_ponto <= 0:
            continue
        pontos_max = risco_moeda / custo_ponto
        pips = pontos_max / (10 if info.digits in (3, 5) else 1)
        if pips < 10:
            avisos.append(
                f"  {base}: no lote minimo ({spec['volume_min']:g}), "
                f"{risco_pct:g}% de {saldo:.2f} so cobre um stop de "
                f"{pips:.1f} pips")
    return avisos


def ler_set(path: Path) -> list[str]:
    return path.read_text(encoding="utf-16").splitlines()


def escrever_set(path: Path, linhas: list[str]) -> None:
    path.write_text("\r\n".join(linhas) + "\r\n", encoding="utf-16")


def ajustar(linhas: list[str], mudancas: dict[str, str]) -> tuple[list[str], int]:
    """Reescreve valores mantendo a tupla start||step||stop||flag."""
    saida, tocados = [], 0
    for linha in linhas:
        m = re.match(r"^([^;=]+)=(.*)$", linha)
        if not m or m.group(1) not in mudancas:
            saida.append(linha)
            continue
        nome, atual = m.group(1), m.group(2)
        novo = mudancas[nome]
        partes = atual.split("||")
        if len(partes) == 5:
            passo = "0" if novo in ("true", "false") else "1"
            valor = f"{novo}||{novo}||{passo}||{novo}||N"
        else:
            valor = novo
        if valor != atual:
            tocados += 1
        saida.append(f"{nome}={valor}")
    return saida, tocados


def no_escopo(rel: Path, interesses: dict) -> bool:
    partes = rel.parts
    if len(partes) < 4:
        return True   # manifesto, README: nao sao sets
    _, ativo, sistema, arquivo = partes[0], partes[1], partes[2], partes[3]
    lado, _, variante = arquivo.replace(".set", "").partition("_")
    for chave, valor in (("ativos", ativo), ("sistemas", sistema),
                         ("variantes", variante)):
        alvo = interesses.get(chave) or []
        if alvo and valor not in alvo:
            return False
    # O lado "BOTH" (08_GRID_UNIFIED) cobre compra e venda no mesmo arquivo,
    # entao satisfaz qualquer filtro de lado. Compara-lo literalmente contra
    # ["BUY","SELL"] descartava o sistema inteiro em silencio.
    lados = interesses.get("lados") or []
    if lados and lado != "BOTH" and lado not in lados:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfil", help="arquivo JSON do perfil")
    ap.add_argument("--criar-perfil", metavar="ARQUIVO",
                    help="grava um perfil modelo e sai")
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra o que faria, sem gravar")
    args = ap.parse_args()

    if args.criar_perfil:
        destino = Path(args.criar_perfil)
        destino.write_text(json.dumps(PERFIL_MODELO, indent=2,
                                      ensure_ascii=False), encoding="utf-8")
        print(f"Perfil modelo: {destino}")
        return 0

    if not args.perfil:
        ap.error("informe --perfil ou --criar-perfil")
    perfil = json.loads(Path(args.perfil).read_text(encoding="utf-8"))
    interesses = perfil.get("interesses", {})
    risco = perfil.get("risco", {})
    wfo = perfil.get("walk_forward", {})

    if not SETS.is_dir():
        print(f"Biblioteca nao encontrada: {SETS}")
        return 1

    mt5 = carregar_mt5()
    dados = conta(mt5) if mt5 else {}
    if dados:
        print(f"Conta {dados['login']} em {dados['servidor']}")
        print(f"  saldo {dados['saldo']:.2f} {dados['moeda']} | "
              f"alavancagem 1:{dados['alavancagem']} | "
              f"{'hedging' if dados['hedging'] else 'netting'}")
    else:
        print("Sem dados da conta: sizing sai do perfil.")

    ativos_desejados = interesses.get("ativos") or [
        d.name for c in sorted(SETS.iterdir()) if c.is_dir()
        for d in sorted(c.iterdir()) if d.is_dir()]
    specs = mapear_simbolos(mt5, ativos_desejados) if mt5 else {}

    ausentes = [a for a in ativos_desejados if a not in specs] if mt5 else []
    if ausentes:
        print(f"\nO broker nao oferece ({len(ausentes)}): "
              + ", ".join(ausentes[:10])
              + (f" (+{len(ausentes) - 10})" if len(ausentes) > 10 else ""))

    renomeados = {b: s["nome"] for b, s in specs.items() if s["nome"] != b}
    if renomeados:
        print("\nSufixo do broker detectado:")
        for base, real in list(renomeados.items())[:6]:
            print(f"  {base} -> {real}")

    apertados = checar_viabilidade(mt5, specs, dados.get("saldo", 0.0),
                                   risco.get("risco_por_trade_pct", 1.0))
    if apertados:
        print("\nSaldo apertado para o risco pedido:")
        for aviso in apertados:
            print(aviso)
        print("  O Fixed-R nao consegue respeitar o 1R nesses casos. Opcoes: "
              "subir o risco por trade, usar stops mais curtos, ou operar so "
              "os simbolos que cabem.")

    alterados = arquivados = fora = 0
    for path in sorted(SETS.rglob("*.set")):
        rel = path.relative_to(SETS)
        if not no_escopo(rel, interesses):
            fora += 1
            if perfil.get("arquivar_fora_do_escopo") and not args.dry_run:
                destino = ARCHIVE / rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(destino))
                arquivados += 1
            continue

        ativo = rel.parts[1]
        spec = specs.get(ativo, {})
        mudancas: dict[str, str] = {}

        # Nome da estrategia carrega o simbolo real: e o que aparece no
        # comentario da ordem e no painel.
        if spec.get("nome") and spec["nome"] != ativo:
            for linha in ler_set(path):
                if linha.startswith("NomedaEstrategia="):
                    mudancas["NomedaEstrategia"] = (
                        linha.split("=", 1)[1].replace(ativo, spec["nome"]))
                    break

        linhas = ler_set(path)
        modo = next((linha.split("=")[1].split("||")[0] for linha in linhas
                     if linha.startswith("PositionSizeMode=")), "2")
        if modo == "3":                      # Fixed-R: 1R em % do capital
            mudancas["PositionSizeValue"] = f"{risco.get('risco_por_trade_pct', 1.0):g}"
        else:                                # Fixed Lot: respeita o broker
            lote = risco.get("lote_fixo", 0.01)
            if spec and risco.get("usar_lote_minimo_do_broker", True):
                lote = normalizar_lote(lote, spec)
            mudancas["PositionSizeValue"] = f"{lote:g}"

        if wfo.get("ligar"):
            mudancas.update({
                "AtivarWFO": "true",
                "input_end_date": wfo.get("data_final", "2026.07.21"),
                "wfo_windowSize": "-1",
                "wfo_customWindowSizeDays": str(wfo.get("is_dias", 122)),
                "wfo_stepSize": "-1",
                "wfo_customStepSizePercent": str(-abs(wfo.get("oos_dias", 61))),
            })
        else:
            mudancas["AtivarWFO"] = "false"

        novas, tocados = ajustar(linhas, mudancas)
        if tocados and not args.dry_run:
            escrever_set(path, novas)
        if tocados:
            alterados += 1

    print(f"\nSets no escopo alterados: {alterados}")
    print(f"Sets fora do escopo: {fora}"
          + (f" (arquivados: {arquivados})" if arquivados else ""))
    if args.dry_run:
        print("\n--dry-run: nada foi gravado.")

    if mt5:
        registro = {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "conta": dados,
            "alterados": alterados,
            "fora_do_escopo": fora,
            "ausentes_no_broker": ausentes,
            "sufixos": renomeados,
        }
        if not args.dry_run:
            (SETS / "ULTIMA_SINCRONIZACAO.json").write_text(
                json.dumps(registro, indent=2, ensure_ascii=False),
                encoding="utf-8")
        # mt5.shutdown() so fecha a conexao Python-terminal, nao o processo
        # terminal64.exe -- fechar_terminal() e o que efetivamente libera a
        # maquina pro proximo `/config:` de outra ferramenta.
        fechar_terminal()
    return 0


if __name__ == "__main__":
    sys.exit(main())
