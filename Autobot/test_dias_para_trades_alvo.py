# -*- coding: utf-8 -*-
"""Testa `dias_para_trades_alvo()` -- a inversa de `piso_trades_da_janela()`.

Existe pra fundamentar a Fase 1 da mudanca de direcao (2026-09-13): em vez de
sempre pedir 3 anos fixos de historico, o circuito passa a poder pedir SO os
dias necessarios pra acumular um numero-alvo de trades, dada a taxa anual
observada/estimada do combo. Esta funcao e aritmetica pura (sem MT5), roda em
milissegundos -- mesma disciplina de test_dimensionar_wfo.py.

    python test_dias_para_trades_alvo.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

from optimize_two_stage import (
    BLOCO_MINIMO_WFO,
    dias_para_trades_alvo,
    piso_trades_da_janela,
)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def checar_que(rotulo: str, condicao: bool) -> None:
    if not condicao:
        FALHAS.append(rotulo)


# --- round-trip com piso_trades_da_janela: ida e volta consistentes --------
# 100 trades/ano, 3 anos (1095 dias) -> piso_trades_da_janela deveria bater
# perto de 100*3=300 trades esperados no periodo.
taxa = 100.0
dias = dias_para_trades_alvo(300, taxa)
fim = (datetime(2023, 1, 1) + timedelta(days=dias)).strftime("%Y.%m.%d")
esperado_trades = piso_trades_da_janela("2023.01.01", fim, taxa, piso_minimo=0)
checar_que(f"round-trip: {dias}d a {taxa}/ano da perto de 300 trades "
          f"(deu {esperado_trades})",
          280 <= esperado_trades <= 320)

# --- taxa alta -> janela curta; taxa baixa -> janela longa ------------------
checar_que(
    "taxa alta pede janela mais curta que taxa baixa",
    dias_para_trades_alvo(100, 1000.0) < dias_para_trades_alvo(100, 10.0))

# --- clamp de piso: nunca menor que o WFO tolera ----------------------------
checar("taxa altissima ainda respeita o piso minimo",
      dias_para_trades_alvo(10, 1_000_000.0), BLOCO_MINIMO_WFO * 2)
checar("piso minimo customizado e respeitado",
      dias_para_trades_alvo(10, 1_000_000.0, minimo_dias=90), 90)

# --- clamp de teto: nunca mais que o teto pedido ----------------------------
checar("taxa baixissima e limitada pelo teto",
      dias_para_trades_alvo(1000, 1.0, maximo_dias=1095), 1095)
checar_que(
    "sem teto, taxa baixissima pede janela bem mais longa",
    dias_para_trades_alvo(1000, 1.0) > 1095)

# --- taxa zero ou negativa: cai no minimo, nunca divide por zero -----------
checar("taxa zero cai no minimo, sem excecao",
      dias_para_trades_alvo(100, 0.0), BLOCO_MINIMO_WFO * 2)
checar("taxa negativa (sonda malformada) tambem cai no minimo",
      dias_para_trades_alvo(100, -5.0), BLOCO_MINIMO_WFO * 2)

# --- teto nunca fica abaixo do proprio minimo -------------------------------
checar_que(
    "teto menor que o minimo nao produz janela menor que o minimo",
    dias_para_trades_alvo(1000, 1.0, minimo_dias=90, maximo_dias=10) >= 90)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("dias_para_trades_alvo: todos os casos passaram")
