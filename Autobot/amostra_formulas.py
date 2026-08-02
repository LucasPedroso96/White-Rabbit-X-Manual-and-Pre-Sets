# -*- coding: utf-8 -*-
"""Compara as formulas de otimizacao (selectedFormula) isoladas da variavel
"tipo de sistema" -- MESMO sistema, MESMO periodo curto, so troca a formula.

Por que isolar assim: cada sistema do circuito ja usa uma formula fixa
(FORMULA_POR_SISTEMA em generate_system_sets.py), entao rodar sistemas
diferentes tambem mistura duas variaveis -- formula E tipo de estrategia.
Aqui so uma muda por vez: o genetico busca no MESMO sistema, e cada rodada
so troca selectedFormula (travado em N, fora da busca) antes de otimizar.

Periodo CURTO de proposito: e diagnostico da formula (converge? favorece
lucro raso ou trade denso? sensivel a DD?), nao validacao de estrategia --
isso continua exigindo o circuito completo com WFO de varios ciclos.

Uso:
    python amostra_formulas.py --from 2026.06.01 --to 2026.07.15
    python amostra_formulas.py --sistema 07_GRID_SEPARATE --variante BOTH_MULTI \
        --from 2026.06.01 --to 2026.07.15 --formulas 1,7,13
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import optimize_sets as base
from mt5_runner import garantir_terminal_livre

# Indice = valor gravado no .set (enum CustomFormulaType, 0-based no .mq5).
# 0 (None) fica de fora -- nao calcula nada, nao ha o que comparar.
FORMULAS = {
    1: "GridSurvivalScore",
    2: "Profit",
    3: "ProfitWinTradeDD",
    4: "EfficiencyRelativeToDeposit",
    5: "AdjustedEfficiencyForGrid",
    6: "ProfitRelativeToDDAndDeposit",
    7: "ProfitPerTradeAdjustedByDD",
    8: "SharpeAdjustedByDD",
    9: "PessimisticProfit",
    10: "ResilienceToDrawdown",
    11: "ReturnUniformity",
    12: "SystemRobustness",
    13: "LevainCompositeScore",
    14: "SomaR",
}


def fixar_formula(origem: Path, destino: Path, formula: int) -> None:
    """Copia o set trocando SO selectedFormula, travado (N) -- nunca eixo.

    Tambem desliga AtivarWFO: o template traz janelas IS/OOS fixas (calibradas
    pro periodo cheio da campanha, ~3 anos -- normalmente 100+ dias). Rodar
    com --from/--to curto sem desligar faz o OnInit rejeitar TODO passe com
    "invalid IS or OOS window sizes", porque o periodo pedido fica menor que
    a janela fixa. O circuito principal nao sofre disso porque janelas_wfo()
    (optimize_two_stage.py) recalcula IS/OOS a partir do periodo de cada
    corrida -- aqui, sem WFO, o teste roda no periodo inteiro pedido.
    """
    linhas = origem.read_text(encoding="utf-16").replace("\r", "").split("\n")
    saida, achou = [], False
    for linha in linhas:
        if re.match(r"^selectedFormula=", linha):
            saida.append(f"selectedFormula={formula}||{formula}||1||{formula}||N")
            achou = True
        elif re.match(r"^AtivarWFO=", linha):
            saida.append("AtivarWFO=false||false||0||false||N")
        else:
            saida.append(linha)
    if not achou:
        raise SystemExit("selectedFormula nao encontrado no set de origem")
    destino.write_text("\n".join(saida), encoding="utf-16")


def rodar_uma(trabalho: Path, args, formula: int) -> dict:
    """Roda o genetico rapido (mesma maquina do optimize_sets.main()) e
    devolve o melhor candidato deste passe."""
    garantir_terminal_livre(fechar=True)
    rel = str(trabalho.relative_to(base.DADOS / "MQL5" / "Profiles" / "Tester"))
    nome_relatorio = f"amostra_formula_{formula}"
    antes = base.marcar_logs()
    for velho in base.DADOS.glob(f"{nome_relatorio}*"):
        velho.unlink(missing_ok=True)

    inicio_em = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "otim.ini"
        base.escrever_ini(ini, args.symbol, args.period, rel, args.inicio,
                          args.fim, args.deposit, 1, 6, nome_relatorio)
        try:
            subprocess.run([str(base.TERMINAL), f"/config:{ini}"],  # noqa: S603
                           timeout=args.timeout, capture_output=True, check=False)
        except subprocess.TimeoutExpired:
            return {"formula": formula, "nome": FORMULAS[formula],
                    "erro": f"estourou {args.timeout}s"}
    decorrido = (time.monotonic() - inicio_em) / 60

    log = base.texto_novo(antes)
    m = re.search(r"local (\d+) tasks", log)
    executados = int(m.group(1)) if m else 0
    # A trilha evolutiva: cada linha e um novo recorde que o genetico achou.
    # Poucas linhas com saltos grandes = ainda subindo rapido; linhas que
    # param de melhorar cedo = convergiu (ou a formula ficou sem gradiente).
    geracoes = re.findall(
        r"Best result ([\-\d.]+) produced at generation (\d+)", log)

    candidatos = sorted(base.DADOS.glob(f"{nome_relatorio}*"),
                        key=lambda p: (p.suffix.lower() != ".xml", p.name))
    relatorio = candidatos[0] if candidatos else base.DADOS / f"{nome_relatorio}.xml"
    cab, linhas = base.ler_relatorio(relatorio)
    if not linhas:
        return {"formula": formula, "nome": FORMULAS[formula],
                "minutos": decorrido, "executados": executados,
                "erro": "sem relatorio legivel"}

    uteis = base.escolher_candidatos(cab, linhas, args.min_trades, args.min_pf)
    fonte = uteis if uteis else linhas
    melhor = fonte[0]

    def pega(nome: str) -> float | None:
        return base.num(melhor[cab.index(nome)]) if nome in cab else None

    return {
        "formula": formula, "nome": FORMULAS[formula], "minutos": decorrido,
        "executados": executados, "aptos": len(uteis), "geracoes": geracoes,
        "result": pega("Result"), "profit": pega("Profit"),
        "pf": pega("Profit Factor"), "payoff": pega("Expected Payoff"),
        "sharpe": pega("Sharpe Ratio"), "dd": pega("Equity DD %"),
        "trades": pega("Trades"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="EURUSD.HT")
    ap.add_argument("--sistema", default="01_SLTP")
    ap.add_argument("--variante", default="BUY_MULTI")
    ap.add_argument("--period", default="M1")
    ap.add_argument("--from", dest="inicio", required=True)
    ap.add_argument("--to", dest="fim", required=True)
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--min-trades", type=int, default=15,
                    help="piso baixo de proposito -- periodo curto gera poucos trades")
    ap.add_argument("--min-pf", type=float, default=1.0)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--formulas", default="",
                    help="lista separada por virgula (ex 1,7,13); vazio = todas")
    args = ap.parse_args()

    origem = base.achar_set(args.symbol, args.sistema, args.variante)
    if origem is None:
        print(f"Set nao encontrado: {args.symbol}/{args.sistema}/{args.variante}")
        return 1

    alvo = ([int(x) for x in args.formulas.split(",")] if args.formulas
            else sorted(FORMULAS))
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_AMOSTRA_FORMULA.set"

    print(f"{args.symbol} {args.sistema} {args.variante} | "
          f"{args.inicio} a {args.fim}")
    print(f"{len(alvo)} formulas, mesmo sistema e periodo -- so a formula muda\n")

    resultados = []
    for formula in alvo:
        if formula not in FORMULAS:
            print(f"  [{formula}] indice desconhecido, pulado")
            continue
        fixar_formula(origem, trabalho, formula)
        r = rodar_uma(trabalho, args, formula)
        resultados.append(r)
        if "erro" in r:
            print(f"  [{formula:2}] {FORMULAS[formula]:<28} "
                  f"{r.get('minutos', 0):5.1f}min  {r['erro']}")
        else:
            print(f"  [{formula:2}] {FORMULAS[formula]:<28} {r['minutos']:5.1f}min  "
                  f"lucro={r['profit']:>9.2f}  PF={r['pf']:.2f}  "
                  f"trades={int(r['trades']) if r['trades'] else 0:>4}  "
                  f"DD%={r['dd']:.1f}  aptos={r['aptos']}/{r['executados']}")
            if r["geracoes"]:
                trilha = " -> ".join(f"g{g}:{float(v):.1f}"
                                     for v, g in r["geracoes"])
                print(f"        evolucao: {trilha}")
            else:
                print("        evolucao: sem registro de geracao no log "
                      "(possivel convergencia na 1a leva de passes)")

    validos = [r for r in resultados if "erro" not in r]
    if validos:
        print(f"\n{'formula':<28} {'lucro':>10} {'PF':>6} {'trades':>7} "
              f"{'DD%':>6} {'aptos':>6}")
        for r in sorted(validos, key=lambda x: x["profit"], reverse=True):
            print(f"{r['nome']:<28} {r['profit']:>10.2f} {r['pf']:>6.2f} "
                  f"{int(r['trades']):>7} {r['dd']:>6.1f} {r['aptos']:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
