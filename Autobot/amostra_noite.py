# -*- coding: utf-8 -*-
"""Orquestra a noite de diagnostico: duas fases, tudo num periodo curto.

FASE 1 -- todas as 14 formulas, MESMO sistema (grid), MESMO periodo. Isola a
formula como variavel: mostra o que CADA formula faria com a mesma estrategia,
incluindo as 10 que hoje nenhum sistema usa (2,3,4,5,6,7,11,12,13,14).

FASE 2 -- os 11 sistemas, cada um com a formula que JA esta em
FORMULA_POR_SISTEMA (generate_system_sets.py), mesmo periodo. Reavalia se o
mapeamento atual (1=grid, 8=trailing, 9=geometria fixa/saida por sinal,
10=recovery) se sustenta na pratica, nao so na intencao de design.

So um MT5 por vez (mesma maquina que a campanha usa), entao roda tudo em
SEQUENCIA, resumivel: grava cada resultado assim que sai, em JSONL, e pula o
que ja foi feito se relancado.

Uso:
    python amostra_noite.py --from 2026.05.01 --to 2026.07.06
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import amostra_formulas as af
import optimize_sets as base

AQUI = Path(__file__).resolve().parent
LEDGER = AQUI / "amostra_noite_resultados.jsonl"

FORMULA_POR_SISTEMA = {
    "01_SLTP": 9, "02_SLTP_ORGANIC": 9,
    "03_TRAIL_ONLY": 8, "04_SLTP_TRAIL": 8, "05_BE_TRAIL": 8,
    "06_REVERSAL_EXIT": 9,
    "07_GRID_SEPARATE": 1, "08_GRID_UNIFIED": 1,
    "09_MARTINGALE": 10, "10_DALEMBERT": 10,
    "11_SIGNAL_ONLY": 9,
}
BILATERAL = {"08_GRID_UNIFIED"}
SISTEMA_FASE1 = "07_GRID_SEPARATE"
VARIANTE_FASE1 = "BUY_MULTI"


def feitos() -> set[tuple[str, str, str]]:
    if not LEDGER.is_file():
        return set()
    vistos = set()
    for linha in LEDGER.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            r = json.loads(linha)
        except json.JSONDecodeError:
            continue
        vistos.add((r["fase"], r["sistema"], str(r["formula"])))
    return vistos


def registrar(reg: dict) -> None:
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")


def rodar_item(fase: str, sistema: str, variante: str, formula: int,
               args) -> dict:
    origem = base.achar_set(args.symbol, sistema, variante)
    if origem is None:
        return {"fase": fase, "sistema": sistema, "variante": variante,
                "formula": formula, "nome": af.FORMULAS.get(formula, "?"),
                "erro": "set nao encontrado"}
    trabalho = (base.DADOS / "MQL5" / "Profiles" / "Tester" /
               "_AMOSTRA_NOITE.set")
    af.fixar_formula(origem, trabalho, formula)
    r = af.rodar_uma(trabalho, args, formula)
    r["fase"] = fase
    r["sistema"] = sistema
    r["variante"] = variante
    r["quando"] = datetime.now().isoformat(timespec="seconds")
    return r


def imprimir(r: dict) -> None:
    tag = f"[{r['fase']}] {r['sistema']:<18} {r['nome']:<28}"
    if "erro" in r:
        print(f"  {tag} {r.get('minutos', 0):5.1f}min  {r['erro']}")
        return
    print(f"  {tag} {r['minutos']:5.1f}min  lucro={r['profit']:>9.2f}  "
          f"PF={r['pf']:.2f}  trades={int(r['trades']) if r['trades'] else 0:>4}  "
          f"DD%={r['dd']:.1f}  aptos={r['aptos']}/{r['executados']}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="EURUSD.HT")
    ap.add_argument("--period", default="M1")
    ap.add_argument("--from", dest="inicio", required=True)
    ap.add_argument("--to", dest="fim", required=True)
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--min-trades", type=int, default=15)
    ap.add_argument("--min-pf", type=float, default=1.0)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    ja = feitos()
    itens: list[tuple[str, str, str, int]] = []
    for formula in sorted(af.FORMULAS):
        itens.append(("fase1", SISTEMA_FASE1, VARIANTE_FASE1, formula))
    for sistema, formula in FORMULA_POR_SISTEMA.items():
        variante = "BOTH_MULTI" if sistema in BILATERAL else "BUY_MULTI"
        itens.append(("fase2", sistema, variante, formula))

    pendentes = [it for it in itens if (it[0], it[1], str(it[3])) not in ja]
    print(f"{args.symbol} | {args.inicio} a {args.fim}")
    print(f"{len(itens)} itens no total | {len(itens) - len(pendentes)} ja "
          f"feitos | {len(pendentes)} pendentes\n")

    for fase, sistema, variante, formula in pendentes:
        r = rodar_item(fase, sistema, variante, formula, args)
        registrar(r)
        imprimir(r)

    print(f"\nconcluido. resultados em {LEDGER.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
