# -*- coding: utf-8 -*-
"""Testa a fatia pura de priorizar_lucro_no_topo() sem precisar do MT5 nem
do arquivo FileWrite de formulas.

Achado do dono, 2026-08-05: olhando o relatorio ao vivo do grid, o topo por
formula as vezes elegia um passe de score alto e lucro baixo (~600 de
GridSurvivalScore, ~60 de lucro) na frente de outro so um pouco atras em
score mas com lucro bem maior. A formula continua sendo o PISO de risco (o
genetico do MT5 so evolui por ela, OptimizationCriterion=6); esta funcao so
reordena o relatorio JA FINALIZADO -- corta o topo por formula, depois
reordena SO essa fatia por lucro, sem tocar quem ficou de fora do corte.

    python test_priorizar_lucro_no_topo.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import _priorizar_lucro_na_fatia

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


CAB = ["Pass", "Profit", "Equity DD %"]

# --- 20 linhas ja ordenadas por formula (indice 0 = melhor score) -----------
# index0: score-melhor mas lucro baixo (o caso real que o dono viu: 60).
# index1: score-segundo mas lucro bem maior (5000) -- deve virar o vencedor.
# index10: FORA do topo (corte_pct=0.5 -> corte=10), lucro gigante (999999)
#          mas nao pode ser promovido: a formula ja decidiu que ele nao e
#          elegivel, lucro so reordena DENTRO de quem passou o piso.
LINHAS = [["0", "60", "5"], ["1", "5000", "5"]]
LINHAS += [[str(i), "10", "5"] for i in range(2, 10)]
LINHAS += [["10", "999999", "5"]]
LINHAS += [[str(i), "1", "5"] for i in range(11, 20)]

resultado = _priorizar_lucro_na_fatia(CAB, LINHAS, corte_pct=0.5, minimo=1)
checar("topo: lucro 5000 vira o 1o (era 2o em score)", resultado[0][0], "1")
checar("topo: lucro 60 cai pro 2o (era 1o em score)", resultado[1][0], "0")
checar("resto: lucro 999999 fora do corte NAO e promovido",
       resultado[10][0], "10")
checar("resto: ordem de formula preservada fora do corte",
       [r[0] for r in resultado[10:]], [str(i) for i in range(10, 20)])
checar("tamanho preservado", len(resultado), len(LINHAS))

# --- minimo maior que o total: corte vira o total, resto fica vazio ---------
pequeno = [["a", "1", "0"], ["b", "9", "0"], ["c", "5", "0"]]
resultado = _priorizar_lucro_na_fatia(CAB, pequeno, corte_pct=0.1, minimo=10)
checar("minimo > total: reordena tudo por lucro",
       [r[0] for r in resultado], ["b", "c", "a"])

# --- desempate por Equity DD % (menor dd vence entre lucros iguais) ---------
empate = [["x", "100", "20"], ["y", "100", "5"]]
resultado = _priorizar_lucro_na_fatia(CAB, empate, corte_pct=1.0, minimo=1)
checar("desempate: menor DD vence com lucro igual", resultado[0][0], "y")

# --- sem coluna Profit: devolve a lista original, sem excecao ---------------
sem_profit = _priorizar_lucro_na_fatia(["Pass", "Result"], [["1", "5"]], 0.5, 1)
checar("sem coluna Profit: inalterado", sem_profit, [["1", "5"]])

# --- lista vazia: devolve vazio, sem excecao ---------------------------------
checar("lista vazia", _priorizar_lucro_na_fatia(CAB, [], 0.5, 1), [])

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("priorizar_lucro_no_topo: todos os casos passaram")
