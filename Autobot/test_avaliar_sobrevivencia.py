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
checar("saudavel: zero fechamentos forcados no fim do teste",
       r["fechados_fim_teste"], 0)

# --- caso real: EURUSD/08_GRID_UNIFIED aprovado (saldo 1219.76, sem stop out,
# sem tradingStopped) mas os ultimos 7 deals foram liquidacao forcada no
# CORTE do calendario, nao a estrategia quebrando -- achado do dono,
# 2026-08-16, revisando o grafico de saldo (queda de ~1494 pra ~1220 no
# ultimo ponto). O gate continua aprovando (nao e culpa da estrategia: cesta
# de recuperacao sem prazo fixo vs. data de corte fixa, pura sorte de onde a
# borda cai), mas agora com o numero de fechamentos forcados visivel, em vez
# de exigir abrir o log de deals na mao pra descobrir.
FECHAMENTO_FORCADO_REAL = """
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2287 sell 0.01 EURUSD 1.16460]
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2288 sell 0.01 EURUSD 1.16074]
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2289 buy 0.01 EURUSD 1.15930]
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2290 sell 0.01 EURUSD 1.15891]
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2291 sell 0.01 EURUSD 1.15841]
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2292 buy 0.01 EURUSD 1.16939]
2026.08.14 23:54:57   position closed due end of test at 1.16303 [#2293 buy 0.01 EURUSD 1.17641]
final balance 1219.76 USD
OnTester result 1219.76
automatical testing finished
"""
r = avaliar_sobrevivencia(FECHAMENTO_FORCADO_REAL, 1000)
checar("fechamento forcado: ainda sobrevive (nao e culpa da estrategia)",
       r["sobreviveu"], True)
checar("fechamento forcado: saldo final ainda e lido",
       r["saldo_final"], 1219.76)
checar("fechamento forcado: conta as 7 posicoes liquidadas no corte",
       r["fechados_fim_teste"], 7)

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

# --- caso real: EURUSD/08_GRID_UNIFIED/BOTH_MULTI aprovado (saldo final
# 1237.15, bem acima do piso de 50%, sem stop out nem retcode=10019) mas o
# EA se autodesligou pra sempre em 2025.04.03 via CheckStopTradingCondition()
# (stop de emergencia por drawdown de equity, tradingStopped=true permanente)
# -- ficou ~16 meses parado ate o fim do periodo de 3 anos, e o saldo
# congelado passou pelo piso porque nada mais mexeu nele depois. Achado do
# dono, 2026-08-15, revisando os aprovados apos o fix do swap: a cesta
# cresceu uma perna de 0.25/0.13 lote (25x/13x o FixedLot base) perseguindo
# o alvo, e quando o preco nao voltou o stop de emergencia liquidou tudo de
# uma vez (-1020.32 num so grupo de fechamentos "StopLoss triggered"). O
# gate so olhava saldo final e "stop out occurred" (mensagem da CORRETORA);
# nao enxergava o EA se autodesligando por conta propria.
EMERGENCIA_REAL = """
2025.04.03 11:40:40   Trading stopped: strategy equity=1318.38, initial capital=1000.00
2025.04.03 11:40:40   deal #531 buy 0.13 EURUSD at 1.10181 done (based on order #531)
final balance 1237.15 USD
OnTester result 1237.15
automatical testing finished
"""
r = avaliar_sobrevivencia(EMERGENCIA_REAL, 1000)
checar("stop de emergencia: nao sobrevive apesar do saldo saudavel",
       r["sobreviveu"], False)
checar("stop de emergencia: saldo final ainda e lido", r["saldo_final"], 1237.15)
checar("stop de emergencia: motivo cita o autodesligamento",
       "Trading stopped" in r["motivo"], True)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("avaliar_sobrevivencia: todos os casos passaram")
