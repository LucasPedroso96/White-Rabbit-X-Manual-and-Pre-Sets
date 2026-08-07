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
automatical testing finished
"""
r = avaliar_sobrevivencia(ESTOURO_REAL, 500)
checar("estouro real: nao sobrevive", r["sobreviveu"], False)
checar("estouro real: saldo final", r["saldo_final"], 273.98)
checar("estouro real: motivo cita stop out", "stop out" in r["motivo"], True)

# --- caso real: EURUSD/BUY_MULTI aprovado (saldo final 3335.25, sem stop
# out) mas preso sem margem pra abrir posicao nova em 2025.10.29 -- achado
# do dono testando manualmente o set que o gate tinha deixado passar
# (2026-08-04). "No money" nao derruba saldo nem estoura, so trava a conta
# -- e por isso o piso de 50% e o stop-out sozinhos nao pegavam.
SEM_MARGEM_REAL = """
2025.10.29 06:40:00   Order opening not sent: OrderCheck retcode=10019, No money
2025.10.29 07:33:32   order performed sell 2.47 at 1.16281 [#12789 sell 2.47 EURUSD at 1.16281]
final balance 3335.25 USD
OnTester result 420.8364211437089
automatical testing finished
"""
r = avaliar_sobrevivencia(SEM_MARGEM_REAL, 500)
checar("sem margem real: nao sobrevive apesar do saldo saudavel",
       r["sobreviveu"], False)
checar("sem margem real: saldo final ainda e lido", r["saldo_final"], 3335.25)
checar("sem margem real: motivo cita retcode=10019", "10019" in r["motivo"], True)

# --- sobrevive: completa o periodo, sem estourar, saldo saudavel ------------
SAUDAVEL = """
2026.07.20 23:59:58   position closed [#900 sell 0.02 AUDCHF 0.60000]
final balance 812.40 USD
OnTester result 812.4
automatical testing finished
"""
r = avaliar_sobrevivencia(SAUDAVEL, 500)
checar("saudavel: sobrevive", r["sobreviveu"], True)
checar("saudavel: sem motivo de reprovacao", r["motivo"], None)

# --- a outra grafia: o MT5 se auto-atualizou no meio desta sessao
# (2026-08-07, terminal64.exe trocou de mtime as 15:13:59) e passou a
# escrever "automatic testing finished" (sem "-al") em vez de "automatical
# testing finished" -- as duas tem que ser aceitas, builds antigo e novo.
SAUDAVEL_GRAFIA_NOVA = SAUDAVEL.replace("automatical testing finished",
                                        "automatic testing finished")
r = avaliar_sobrevivencia(SAUDAVEL_GRAFIA_NOVA, 500)
checar("grafia nova (sem -al): sobrevive", r["sobreviveu"], True)
checar("grafia nova (sem -al): sem motivo de reprovacao", r["motivo"], None)

# --- fronteira: termina positivo mas abaixo do piso de 50% do deposito ------
QUASE_ZERO = SAUDAVEL.replace("final balance 812.40", "final balance 240.00")
r = avaliar_sobrevivencia(QUASE_ZERO, 500)
checar("quase zero: nao sobrevive (sem stop out literal)", r["sobreviveu"], False)
checar("quase zero: motivo cita o piso", "50%" in r["motivo"], True)

# --- caso real: gate reprovado erroneamente por falta so da linha de
# bookkeeping (achado do dono, 2026-08-07): EURUSD/BOTH_MULTI rodou o
# periodo completo de verdade em 2.1min (nada perto de qualquer timeout),
# saldo final ja calculado e saudavel, saem sem estouro nem sem-margem --
# so a linha "automatical testing finished" do Tester nao chegou a tempo
# antes do ShutdownTerminal=1 fechar o processo. saldo_final e prova mais
# forte de conclusao que essa linha de bookkeeping: se o OnTester/deinit
# calculou um saldo, o periodo inteiro ja foi simulado.
SEM_LINHA_FINAL_MAS_COMPLETO = """
2026.07.20 23:59:58   position closed [#900 sell 0.02 EURUSD 1.10000]
final balance 881.15 USD
OnTester result 881.15
"""
r = avaliar_sobrevivencia(SEM_LINHA_FINAL_MAS_COMPLETO, 500)
checar("sem linha final mas com saldo: sobrevive", r["sobreviveu"], True)
checar("sem linha final mas com saldo: saldo final", r["saldo_final"], 881.15)
checar("sem linha final mas com saldo: sem motivo de reprovacao",
       r["motivo"], None)

# --- teste nao completou de verdade: nem a linha de bookkeeping nem saldo --
INCOMPLETO = "2026.07.20 23:59:58   position closed [#1 sell 0.01 AUDCHF]"
r = avaliar_sobrevivencia(INCOMPLETO, 500)
checar("incompleto: nao sobrevive", r["sobreviveu"], False)
checar("incompleto: saldo final ausente", r["saldo_final"], None)
checar("incompleto: motivo nao inventa timeout literal",
       "final" in r["motivo"], True)

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
