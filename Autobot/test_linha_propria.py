# -*- coding: utf-8 -*-
"""escolher_linha_propria: o arquivo ALL_FORMULAS e da MAQUINA inteira.

Regressao do bug de 2026-09-20: ler "a ultima linha" depois de um passe unico
pegava uma linha do terminal vizinho (que grava ~15 linhas/s durante a
otimizacao genetica). Casos com os numeros reais do log local do MT5:
holdout 3 anos = saldo 827.60 / 317 trades; periodo anterior = 914.61 / 287.
"""
from __future__ import annotations

import random
import sys

from optimize_two_stage import escolher_linha_propria

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def linha(profit: float, trades: int, **extra) -> dict:
    return {"profit": profit, "trades": trades, **extra}


rng = random.Random(7)
vizinho = [linha(round(rng.uniform(-300, 2500), 2), rng.randint(20, 700))
           for _ in range(600)]

# --- a linha verdadeira esta ENTERRADA no meio do fluxo do vizinho -----------
propria = linha(-172.40, 317, marca="minha")
mistura = vizinho[:300] + [propria] + vizinho[300:]
checar("acha a linha propria enterrada",
       escolher_linha_propria(mistura, 827.60, 317, 1000), propria)
# a "ultima linha" (comportamento antigo) NAO era a minha:
checar("a ultima linha era do vizinho", mistura[-1] is propria, False)

# --- periodo anterior (outro passe, outra linha) ----------------------------
propria2 = linha(-85.39, 287, marca="minha2")
checar("segundo passe",
       escolher_linha_propria(vizinho + [propria2] + vizinho[:50], 914.61, 287,
                              1000), propria2)

# --- sem linha confiavel: None (nunca um numero de outro terminal) -----------
checar("sem match nenhum", escolher_linha_propria(vizinho, 827.60, 317, 1000),
       None)
checar("lista vazia", escolher_linha_propria([], 827.60, 317, 1000), None)
checar("saldo desconhecido", escolher_linha_propria(mistura, None, 317, 1000),
       None)
checar("trades desconhecido", escolher_linha_propria(mistura, 827.60, None,
                                                     1000), None)

# --- criterio: trades EXATO + lucro dentro da tolerancia ---------------------
checar("trades diferente nao casa",
       escolher_linha_propria([linha(-172.40, 316)], 827.60, 317, 1000), None)
checar("lucro dentro de 0.5 casa",
       escolher_linha_propria([linha(-172.10, 317)], 827.60, 317, 1000) is not None,
       True)
checar("lucro longe (5.0) nao casa",
       escolher_linha_propria([linha(-167.40, 317)], 827.60, 317, 1000), None)
# tolerancia proporcional (1%) em lucro grande
checar("1% de um lucro grande casa",
       escolher_linha_propria([linha(2610.0, 400)], 3617.01, 400, 1000) is not None,
       True)
checar("3% de um lucro grande nao casa",
       escolher_linha_propria([linha(2690.0, 400)], 3617.01, 400, 1000), None)

# --- deposito diferente: lucro = saldo - deposito ----------------------------
checar("deposito 10000",
       escolher_linha_propria([linha(250.0, 90, marca="x")], 10250.0, 90,
                              10000)["marca"], "x")

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("escolher_linha_propria: todos os casos passaram")
