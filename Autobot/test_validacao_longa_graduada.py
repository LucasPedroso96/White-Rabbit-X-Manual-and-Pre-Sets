# -*- coding: utf-8 -*-
"""Testes das camadas graduadas de validacao longa (2026-09-20).

Funcoes puras -- nao precisam do MT5. Os numeros de referencia sao casos
reais: CHFJPY/03_TRAIL_ONLY (saldo final 7.11 de 1000 em 3 anos, reprovado
certo) e GBPUSD/03_TRAIL_ONLY (holdout 3 anos +4076.66, aprovado).
"""
from __future__ import annotations

import sys

from optimize_two_stage import (LIMITE_CATASTROFE_PCT, LIMITE_PERDA_ANTERIOR_PCT,
                                MIN_TRADES_PERIODO_ANTERIOR,
                                avaliar_catastrofe, avaliar_periodo_anterior)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- camada 1: catastrofe ----------------------------------------------------
# CHFJPY: 1000 -> 7.11, profit -992.89. Tem que reprovar (era o buraco).
ok, motivo = avaliar_catastrofe(-992.89, 1000)
checar("CHFJPY perdeu 99%: reprova", ok, False)
checar("CHFJPY: motivo cita catastrofe", "catastrofe" in (motivo or ""), True)

# GBPUSD aprovado: +4076.66 -- passa.
checar("GBPUSD lucrativo passa", avaliar_catastrofe(4076.66, 1000)[0], True)
# exatamente no limite (-50%): nao reprova; um centavo abaixo reprova.
lim = -1000 * LIMITE_CATASTROFE_PCT / 100
checar("no limite exato passa", avaliar_catastrofe(lim, 1000)[0], True)
checar("um centavo abaixo reprova", avaliar_catastrofe(lim - 0.01, 1000)[0], False)
# ausencia de dado nunca derruba
checar("profit None passa", avaliar_catastrofe(None, 1000)[0], True)
checar("deposito 0 passa", avaliar_catastrofe(-5, 0)[0], True)

# --- camada 2: periodo anterior ao treino -----------------------------------
# critério MENOR que lucrar: perda pequena passa.
ok, msg = avaliar_periodo_anterior(-50.0, 40, 1000)
checar("perda pequena (-5%) passa", ok, True)
# perda destrutiva reprova.
ok, msg = avaliar_periodo_anterior(-300.0, 40, 1000)
checar("perda de 30% reprova", ok, False)
checar("msg cita periodo anterior", "periodo anterior" in msg, True)
# limite exato / um centavo.
lim2 = -1000 * LIMITE_PERDA_ANTERIOR_PCT / 100
checar("no limite exato passa", avaliar_periodo_anterior(lim2, 40, 1000)[0], True)
checar("um centavo abaixo reprova",
       avaliar_periodo_anterior(lim2 - 0.01, 40, 1000)[0], False)
# lucro passa.
checar("lucro passa", avaliar_periodo_anterior(120.0, 40, 1000)[0], True)
# amostra pequena: nao avalia (nao reprova nem com prejuizo grande).
ok, msg = avaliar_periodo_anterior(-900.0, MIN_TRADES_PERIODO_ANTERIOR - 1, 1000)
checar("poucos trades: nao avalia", ok, True)
checar("poucos trades: msg diz nao avaliado", "nao avaliado" in msg, True)
# exatamente o minimo de trades: avalia.
checar("minimo de trades avalia",
       avaliar_periodo_anterior(-900.0, MIN_TRADES_PERIODO_ANTERIOR, 1000)[0],
       False)
# sem medida / trades desconhecido.
checar("profit None: nao avalia", avaliar_periodo_anterior(None, None, 1000)[0], True)
checar("trades None avalia pelo lucro",
       avaliar_periodo_anterior(-900.0, None, 1000)[0], False)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("validacao longa graduada: todos os casos passaram")
