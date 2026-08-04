# -*- coding: utf-8 -*-
"""Testa o gate de sobrevivencia (periodo completo) sem precisar do MT5.

Existe pelo mesmo motivo do test_ler_metricas: o defeito que motivou este
gate (AUDCHF/07_GRID_SEPARATE aprovado com 0% de divergencia numa janela OOS
curta, e o set ENTREGUE estourando margem no periodo completo, 2026-08-03) so
apareceria depois de ~200 min de circuito. O trecho de log real do estouro
vira caso de regressao aqui, testavel em milissegundos.

    python test_avaliar_sobrevivencia.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import avaliar_sobrevivencia

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- caso real: o estouro do AUDCHF (trecho verdadeiro do log do MT5) -------
ESTOURO_REAL = """
2024.07.29 00:48:02   position stop out triggered at 45.56% [#370 buy 0.01 AUDCHF 0.60644]
2024.07.29 00:48:02   deal #374 sell 0.01 AUDCHF at 0.57764 done (based on order #374)
2024.07.29 00:48:02   position closed due end of test at 0.57764 [#373 buy 1.99 AUDCHF 0.57874]
final balance 273.98 USD
OnTester result 0
stop out occurred on 33% of testing interval
AUDCHF,M1: 24749597 ticks, 364972 bars generated.
automatic testing finished
"""
r = avaliar_sobrevivencia(ESTOURO_REAL, 500)
checar("estouro real: nao sobrevive", r["sobreviveu"], False)
checar("estouro real: saldo final", r["saldo_final"], 273.98)
checar("estouro real: motivo cita stop out", "stop out" in r["motivo"], True)

# --- sobrevive: completa o periodo, sem estourar, saldo saudavel ------------
SAUDAVEL = """
2026.07.20 23:59:58   position closed [#900 sell 0.02 AUDCHF 0.60000]
final balance 812.40 USD
OnTester result 812.4
automatic testing finished
"""
r = avaliar_sobrevivencia(SAUDAVEL, 500)
checar("saudavel: sobrevive", r["sobreviveu"], True)
checar("saudavel: sem motivo de reprovacao", r["motivo"], None)

# --- fronteira: termina positivo mas abaixo do piso de 50% do deposito ------
QUASE_ZERO = SAUDAVEL.replace("final balance 812.40", "final balance 240.00")
r = avaliar_sobrevivencia(QUASE_ZERO, 500)
checar("quase zero: nao sobrevive (sem stop out literal)", r["sobreviveu"], False)
checar("quase zero: motivo cita o piso", "50%" in r["motivo"], True)

# --- teste nao completou (travou/timeout): nao e sobrevivencia, e ausencia --
INCOMPLETO = "2026.07.20 23:59:58   position closed [#1 sell 0.01 AUDCHF]\nfinal balance 500.00 USD"
r = avaliar_sobrevivencia(INCOMPLETO, 500)
checar("incompleto: nao sobrevive", r["sobreviveu"], False)
checar("incompleto: motivo cita timeout", "timeout" in r["motivo"], True)

# --- log vazio: tudo cai pro caso seguro (reprovado), nada de excecao -------
r = avaliar_sobrevivencia("", 500)
checar("vazio: nao sobrevive", r["sobreviveu"], False)
checar("vazio: saldo final", r["saldo_final"], None)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("avaliar_sobrevivencia: todos os casos passaram")
