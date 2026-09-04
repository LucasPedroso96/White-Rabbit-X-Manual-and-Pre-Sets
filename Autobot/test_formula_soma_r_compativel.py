# -*- coding: utf-8 -*-
"""Testa formula_soma_r_compativel() -- a checagem que impede o circuito de
gastar um Estagio 1 inteiro (~15-20min) guiado por um criterio CONSTANTE.

Existe por causa de um bug real pego ao vivo, 2026-09-04: 07_GRID_SEPARATE/
AUDNZD usa PositionSizeMode=2 (FixedLot), e a formula 14 (SomaR) So calcula
algo em Percentage(0)/FixedR(3) -- ComputeRMetrics() no .mq5 devolve false
em qualquer outro modo e FormulaSomaR() sai sempre 0.0 ("demais modos: 0",
comentario da propria EA). O genetico do Estagio 1 rodava sem NENHUMA
pressao de selecao nesse caso, equivalente a busca aleatoria, e so
descobria isso ao fim do circuito inteiro.

    python test_formula_soma_r_compativel.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import (MODOS_COMPATIVEIS_SOMA_R,
                                formula_soma_r_compativel)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- os 4 modos reais do enum ENUM_POSITION_SIZE_MODE do .mq5 --------------
checar("Percentage(0): compativel", formula_soma_r_compativel("0"), True)
checar("Monetary(1): INcompativel -- o bug real (07_GRID_SEPARATE usa isto)",
       formula_soma_r_compativel("1"), False)
checar("FixedLot(2): INcompativel -- o combo que disparou o achado usa isto",
       formula_soma_r_compativel("2"), False)
checar("FixedR(3): compativel", formula_soma_r_compativel("3"), True)

# --- casos de borda ----------------------------------------------------
checar("None (set sem PositionSizeMode legivel): INcompativel, direcao segura",
       formula_soma_r_compativel(None), False)
checar("string vazia: INcompativel", formula_soma_r_compativel(""), False)
checar("string invalida: INcompativel", formula_soma_r_compativel("99"), False)

# --- a constante em si bate com o enum do .mq5 (Percentage=0, FixedR=3) ---
checar("MODOS_COMPATIVEIS_SOMA_R sao exatamente Percentage e FixedR",
       set(MODOS_COMPATIVEIS_SOMA_R), {"0", "3"})

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("formula_soma_r_compativel: todos os casos passaram")
