# -*- coding: utf-8 -*-
"""Triagem RAPIDA de forca de sinal por formula, so-insample, pra sistema
parado -- pedido do dono (2026-09-05): "6 semanas rapido para medir forca
nas formulas... nao deu certo num asset vai em outro da sua preferencia".

NAO e o circuito de calibracao (sweep_formulas.py roda o circuito COMPLETO
por formula: WFO interno, filtros de execucao IS+OOS, geometria tick real,
sobrevivencia, agora tambem o gate de holdout longo + WFA -- por isso um
sweep leva horas/dias). Isto aqui e so o Estagio 1 (regiao+indicador,
genetico OHLC, UMA rodada) repetido por formula, numa janela curta (default
42 dias = 6 semanas), sem WFO, sem OOS, sem tick real. Responde só "essa
formula acha ALGUMA coisa lucrativa neste ativo, nestas 6 semanas?" -- um
sinal de "vale a pena investir mais tempo aqui", nunca um veredito de
producao. Todo candidato que aparecer aqui ainda precisa passar pelo
circuito completo (sweep_formulas.py) e pelo gate de holdout longo/WFA
(optimize_two_stage.py, ANOS_HOLDOUT_LONGO) antes de virar VALIDADO_.

Uso:
    python calibracao_rapida.py --sistema 07_GRID_SEPARATE
    python calibracao_rapida.py --sistema 01_SLTP --formulas 2,9,11,15
    python calibracao_rapida.py --todos-pendentes
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from optimize_two_stage import formula_soma_r_compativel

TODAS_FORMULAS = {
    1: "GridSurvivalScore", 2: "Profit", 3: "ProfitWinTradeDD",
    4: "EfficiencyRelativeToDeposit", 5: "AdjustedEfficiencyForGrid",
    6: "ProfitRelativeToDDAndDeposit", 7: "ProfitPerTradeAdjustedByDD",
    8: "SharpeAdjustedByDD", 9: "PessimisticProfit", 10: "ResilienceToDrawdown",
    11: "ReturnUniformity", 12: "SystemRobustness", 13: "LevainCompositeScore",
    14: "SomaR", 15: "ZeusCompositeScore",
}

# Ativo/deposito primario = PLANO_DIVISAO_TESTES_FORMULAS.md (ja calibrado
# por carater estrategico do sistema). Alternativas = escolha do Claude,
# pedidas explicitamente pelo dono ("vai em outro da sua preferencia") --
# mesma familia de regime, ativo diferente, so se o primario nao mostrar
# sinal em NENHUMA formula.
SISTEMAS_PENDENTES = {
    "01_SLTP":          ("EURUSD", 1000,  ["GBPUSD", "AUDUSD"]),
    "02_SLTP_ORGANIC":  ("EURUSD", 1000,  ["GBPUSD", "AUDUSD"]),
    "03_TRAIL_ONLY":    ("XAUUSD", 10000, ["BTCUSD", "USDJPY"]),
    "05_BE_TRAIL":      ("XAUUSD", 10000, ["BTCUSD", "USDJPY"]),
    "06_REVERSAL_EXIT": ("EURGBP", 1000,  ["AUDNZD", "EURCHF"]),
    "07_GRID_SEPARATE": ("AUDNZD", 1000,  ["AUDCAD", "EURGBP"]),
    "09_MARTINGALE":    ("AUDNZD", 1000,  ["AUDCAD", "NZDCAD"]),
    "12_GRID_INVERSO":  ("XAUUSD", 10000, ["BTCUSD", "EURUSD"]),
}

PREFIXO = "_CALIBRACAO_RAPIDA"
PADRAO_FORMULA = re.compile(r"selectedFormula=\d+\|\|\d+\|\|1\|\|\d+\|\|N")


def gravar_formula(origem: Path, indice: int) -> None:
    texto = origem.read_text(encoding="utf-16")
    texto = PADRAO_FORMULA.sub(
        f"selectedFormula={indice}||{indice}||1||{indice}||N", texto)
    origem.write_text(texto, encoding="utf-16")


def formula_original_de(origem: Path) -> int | None:
    m = PADRAO_FORMULA.search(origem.read_text(encoding="utf-16"))
    return int(re.search(r"\d+", m.group(0)).group(0)) if m else None


def escanear_formula(origem: Path, trabalho: Path, sistema: str,
                     simbolo: str, deposito: int, inicio: str, fim: str,
                     formula_id: int, timeout: int,
                     formula_original: int | None) -> dict:
    """Uma rodada de Estagio 1 (regiao+indicador, OHLC, sem WFO/OOS).

    Restaura `formula_original` no `origem` logo apos `reescrever()` copiar o
    valor pro `trabalho` -- ANTES de `rodar()` (o passo caro, que lanca o
    terminal e pode travar/morrer). Achado ao vivo (2026-09-05): o processo
    morreu durante um `rodar()` e deixou o template da BIBLIOTECA (nao uma
    copia) com selectedFormula=9 gravado por cima do 11 de producao --
    ninguem restaura sozinho depois de um kill duro (finally nao roda). Essa
    janela agora dura milissegundos, nao o tempo inteiro do passe genetico.
    """
    gravar_formula(origem, formula_id)
    duas_etapas = sistema in ots.SISTEMAS_RECUPERACAO_DUAS_ETAPAS
    eixos_recuperacao = ots.EIXOS_RECUPERACAO.get(sistema, []) if duas_etapas else []
    eixos = ots.eixos_da_fase1(origem)
    if eixos_recuperacao:
        eixos = [e for e in eixos if e not in eixos_recuperacao]
    travar = {"InterfaceLanguage": "1", "AtivarWFO": "false"}
    if duas_etapas:
        travar["RecoveryMode"] = "0"
    ots.reescrever(origem, trabalho, eixos, travar)
    if formula_original is not None:
        gravar_formula(origem, formula_original)
    # Retry curto pra PermissionError/OSError no lancamento do terminal --
    # achado ao vivo, 2026-09-06: lancar_terminal() ja engole TimeoutExpired
    # (bug antigo, documentado no proprio mt5_runner.py) mas NAO um
    # PermissionError (WinError 32, "arquivo ja em uso"), que aqui derrubou
    # o processo inteiro sem traceback capturado na 1a queda e com traceback
    # na 2a. Causa provavel: este script fecha/abre o terminal MUITO mais
    # rapido em sequencia (uma vez por FORMULA) do que o circuito principal
    # (uma vez por ESTAGIO) -- aumenta a chance de pegar o executavel ainda
    # com handle preso pelo Windows entre o ShutdownTerminal do passe
    # anterior e o lancamento do proximo. no maximo 3 tentativas com pausa
    # crescente; se persistir, e um problema de verdade, nao so uma corrida.
    for tentativa in range(3):
        try:
            cab, linhas = ots.rodar(trabalho, simbolo, "M1", inicio, fim,
                                    deposito, 1, timeout)
            break
        except (PermissionError, OSError) as e:
            if tentativa == 2:
                raise
            espera = 5 * (tentativa + 1)
            print(f"    aviso: falha ao lancar o terminal ({e}) -- "
                  f"tentativa {tentativa + 1}/3, aguardando {espera}s",
                  flush=True)
            time.sleep(espera)
    if not linhas:
        return {"formula": formula_id, "nome": TODAS_FORMULAS[formula_id],
               "sinal": False, "motivo": "relatorio vazio"}
    piso = ots.piso_trades_da_janela(inicio, fim, taxa_anual=33.0,
                                     piso_minimo=10)
    aptos = base.escolher_candidatos(cab, linhas, piso, 1.0)
    if not aptos:
        return {"formula": formula_id, "nome": TODAS_FORMULAS[formula_id],
               "sinal": False,
               "motivo": f"nenhum candidato com lucro>0 e >={piso} trades "
                        f"({len(linhas)} passes)"}
    top = aptos[0]
    return {"formula": formula_id, "nome": TODAS_FORMULAS[formula_id],
           "sinal": True,
           "lucro": base.num(top[cab.index("Profit")]),
           "pf": (base.num(top[cab.index("Profit Factor")])
                  if "Profit Factor" in cab else None),
           "trades": (base.num(top[cab.index("Trades")])
                      if "Trades" in cab else None),
           "passes": len(linhas)}


def escanear_sistema(sistema: str, ativos: list[tuple[str, int]],
                     formulas: list[int], dias: int, timeout: int) -> dict:
    fim = datetime.now().strftime("%Y.%m.%d")
    inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y.%m.%d")
    trabalho = (base.DADOS / "MQL5" / "Profiles" / "Tester"
               / f"{PREFIXO}_{sistema}.set")
    log_path = Path(f"calibracao_rapida_{sistema}.log")
    for simbolo, deposito in ativos:
        variante = "BUY_MULTI"
        try:
            origem = base.achar_set(simbolo, sistema, variante)
        except Exception as e:
            print(f"  {simbolo}: sem template ({e}), pulando", flush=True)
            continue
        original = formula_original_de(origem)
        pos_sizing_m = re.search(r"PositionSizeMode=(\d+)",
                                 origem.read_text(encoding="utf-16"))
        pos_sizing = pos_sizing_m.group(1) if pos_sizing_m else None
        print(f"\n=== {sistema} / {simbolo} (${deposito}) | "
              f"{inicio}..{fim} ({dias}d, so insample) ===", flush=True)
        resultados = []
        try:
            for fid in formulas:
                if fid == 14 and not formula_soma_r_compativel(pos_sizing):
                    print(f"  [{fid:2}] {TODAS_FORMULAS[fid]:28} PULADA "
                          f"(PositionSizeMode={pos_sizing} incompativel "
                          "com SomaR)", flush=True)
                    continue
                t0 = time.time()
                r = escanear_formula(origem, trabalho, sistema, simbolo,
                                     deposito, inicio, fim, fid, timeout,
                                     original)
                dt = time.time() - t0
                resultados.append(r)
                if r["sinal"]:
                    print(f"  [{fid:2}] {r['nome']:28} SINAL: lucro "
                          f"{r['lucro']:.2f} | PF {r['pf']} | "
                          f"{r['trades']:.0f} trades | {dt:.0f}s", flush=True)
                else:
                    print(f"  [{fid:2}] {r['nome']:28} sem sinal "
                          f"({r['motivo']}) | {dt:.0f}s", flush=True)
                # Grava a cada formula, nao so no fim do ativo -- um
                # crash/kill no meio nao perde o que ja rodou (achado ao
                # vivo, 2026-09-05: o processo morreu na formula 9 e o log
                # so escrito no final nunca chegou a existir).
                log_path.write_text(json.dumps(
                    {"sistema": sistema, "simbolo": simbolo,
                    "deposito": deposito, "inicio": inicio, "fim": fim,
                    "resultados": resultados, "completo": False},
                    ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            if original is not None:
                gravar_formula(origem, original)
            trabalho.unlink(missing_ok=True)
        with_signal = [r for r in resultados if r["sinal"]]
        log_path.write_text(json.dumps(
            {"sistema": sistema, "simbolo": simbolo, "deposito": deposito,
            "inicio": inicio, "fim": fim, "resultados": resultados,
            "completo": True},
            ensure_ascii=False, indent=2), encoding="utf-8")
        if with_signal:
            melhor = max(with_signal, key=lambda r: r["lucro"])
            print(f"\n  >>> {simbolo}: {len(with_signal)}/{len(resultados)} "
                  f"formulas com sinal. Melhor: [{melhor['formula']}] "
                  f"{melhor['nome']} (lucro {melhor['lucro']:.2f}) <<<",
                  flush=True)
            return {"sistema": sistema, "simbolo": simbolo,
                   "deposito": deposito, "resultados": resultados,
                   "melhor": melhor}
        print(f"\n  >>> {simbolo}: NENHUMA formula mostrou sinal em {dias} "
              "dias -- tentando proximo ativo <<<", flush=True)
    return {"sistema": sistema, "simbolo": None, "resultados": [],
           "melhor": None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sistema")
    ap.add_argument("--simbolo", help="sobrescreve o ativo padrao do mapeamento")
    ap.add_argument("--deposit", type=int)
    ap.add_argument("--dias", type=int, default=42)
    ap.add_argument("--formulas", default="",
                    help="lista separada por virgula; vazio = todas as 15")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--todos-pendentes", action="store_true",
                    help="roda os 8 sistemas de SISTEMAS_PENDENTES em fila")
    ap.add_argument("--pular", default="",
                    help="sistemas ja concluidos, separados por virgula -- "
                         "retomada apos queda, nao refaz do zero")
    args = ap.parse_args()

    formulas = ([int(x) for x in args.formulas.split(",")]
               if args.formulas.strip() else sorted(TODAS_FORMULAS))
    pular = {s.strip() for s in args.pular.split(",") if s.strip()}

    if args.todos_pendentes:
        resumo = []
        for sistema, (simbolo, deposito, alternativas) in SISTEMAS_PENDENTES.items():
            if sistema in pular:
                print(f"\n=== {sistema}: pulado (--pular, ja concluido) ===",
                      flush=True)
                continue
            ativos = [(simbolo, deposito)] + [(a, deposito) for a in alternativas]
            resumo.append(escanear_sistema(sistema, ativos, formulas,
                                           args.dias, args.timeout))
        print("\n\n=== RESUMO FINAL ===", flush=True)
        for r in resumo:
            if r["melhor"]:
                print(f"{r['sistema']:20} {r['simbolo']:8} formula "
                      f"{r['melhor']['formula']} ({r['melhor']['nome']}) "
                      f"lucro {r['melhor']['lucro']:.2f}", flush=True)
            else:
                print(f"{r['sistema']:20} SEM SINAL em nenhum ativo testado",
                      flush=True)
        return 0

    if not args.sistema:
        ap.error("--sistema ou --todos-pendentes")
    padrao = SISTEMAS_PENDENTES.get(args.sistema, (None, None, []))
    simbolo = args.simbolo or padrao[0]
    deposito = args.deposit or padrao[1]
    if not simbolo or not deposito:
        ap.error(f"sistema {args.sistema} nao tem mapeamento padrao -- "
                 "passe --simbolo e --deposit")
    ativos = [(simbolo, deposito)] + [(a, deposito) for a in padrao[2]]
    escanear_sistema(args.sistema, ativos, formulas, args.dias, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
