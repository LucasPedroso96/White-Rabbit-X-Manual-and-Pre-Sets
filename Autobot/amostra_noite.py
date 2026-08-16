# -*- coding: utf-8 -*-
"""Orquestra a noite de diagnostico.

FULLTEST (dono, 2026-08-10) -- as 14 formulas, nos 11 sistemas, MESMO periodo
curto, SEM WFO (fixar_formula ja desliga AtivarWFO). Extensao da FASE 1
original (que so cobria o grid): antes so 1 sistema tinha contraprova real
contra as outras 13 formulas que ninguem usa -- os outros 10 sistemas so
tinham UMA corrida, com a formula ja escolhida, sem nada pra comparar (achado
2026-08-10: FORMULA_POR_SISTEMA nunca teve validacao A/B pros indices 8, 9 e
10, so raciocinio de design escrito no mesmo commit da atribuicao). Isto cobre
o buraco: cada sistema roda as 14, entao da pra ver se a formula que ele usa
hoje realmente ganha do resto no proprio terreno dele, nao so no do grid.

Pedido explicito do dono: SEM WFO, periodo de 1-2 meses, so pra avaliar
performance BRUTA (lucro puro) e tirar uma conclusao -- nao e validacao de
estrategia (isso continua exigindo o circuito completo com WFO de varios
ciclos e o gate de sobrevivencia), e sim diagnostico rapido de qual formula
favorece qual tipo de sistema.

So um MT5 por vez (mesma maquina que a campanha usa), entao roda tudo em
SEQUENCIA, resumivel: grava cada resultado assim que sai, em JSONL, e pula o
que ja foi feito se relancado. 11 sistemas x 14 formulas = 154 corridas;
media historica de 6.2min/corrida (amostra do grid, 2026-08-02) da ~16h.

Uso:
    python amostra_noite.py --from 2026.06.10 --to 2026.08.10
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

# So usado aqui pra saber QUAIS sistemas iterar -- o valor de cada chave nao
# importa pro fulltest (testa as 14 formulas em todos, independente do que
# esta atribuido). Mantido em sincronia com generate_system_sets.py so por
# documentacao/referencia -- valores pos-revisao de peso/risco de
# 2026-08-10 (ver comentario la: 02_SLTP_ORGANIC e 09_MARTINGALE corrigidos
# pra fora do vencedor bruto do fulltest, que caiu numa formula diluida ou
# cega a risco em cada caso).
FORMULA_POR_SISTEMA = {
    "01_SLTP": 10, "02_SLTP_ORGANIC": 4,
    "03_TRAIL_ONLY": 5, "04_SLTP_TRAIL": 5, "05_BE_TRAIL": 6,
    "06_REVERSAL_EXIT": 5,
    "07_GRID_SEPARATE": 1,
    "09_MARTINGALE": 10, "10_DALEMBERT": 5,
    "11_SIGNAL_ONLY": 4,
}
# 08_GRID_UNIFIED removido (2026-08-16) -- ver generate_system_sets.py:SYSTEMS.
BILATERAL: set[str] = set()


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
        # "erro" (set nao encontrado, timeout...) nao e resultado de
        # verdade -- mesmo criterio de campanha.feitos(), so que aqui
        # faltava (achado do dono, 2026-08-10: uma corrida contra o
        # terminal MT5 errado gravou 154 erros que o relance seguinte
        # tratou como "ja feito").
        if "erro" in r:
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
    # Nativo, nao .HT -- ver comentario em amostra_formulas.py (mesmo
    # achado do dono, 2026-08-10, mesmo motivo).
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--period", default="M1")
    ap.add_argument("--from", dest="inicio", required=True)
    ap.add_argument("--to", dest="fim", required=True)
    ap.add_argument("--deposit", type=int, default=1000)
    ap.add_argument("--min-trades", type=int, default=15)
    ap.add_argument("--min-pf", type=float, default=1.0)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--sistemas", default="",
                    help="lista separada por virgula (ex 07_GRID_SEPARATE,"
                         "09_MARTINGALE); vazio = os 10 default")
    ap.add_argument("--fase", default="fulltest",
                    help="tag gravada no ledger -- troque pra nao colidir "
                         "com uma rodada anterior que usou EA diferente "
                         "(feitos() so pula combos com a MESMA fase)")
    args = ap.parse_args()

    sistemas = ([s.strip() for s in args.sistemas.split(",") if s.strip()]
                if args.sistemas.strip() else list(FORMULA_POR_SISTEMA))
    desconhecidos = [s for s in sistemas if s not in FORMULA_POR_SISTEMA]
    if desconhecidos:
        print(f"--sistemas com codigo(s) desconhecido(s): {desconhecidos}")
        return 1

    ja = feitos()
    itens: list[tuple[str, str, str, int]] = []
    for sistema in sistemas:
        variante = "BOTH_MULTI" if sistema in BILATERAL else "BUY_MULTI"
        for formula in sorted(af.FORMULAS):
            itens.append((args.fase, sistema, variante, formula))

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
