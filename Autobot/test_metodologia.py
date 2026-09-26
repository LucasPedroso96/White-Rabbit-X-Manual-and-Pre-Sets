# -*- coding: utf-8 -*-
"""Testa as regras da revisao de metodologia de 2026-09-26 sem o MT5.

  - holdout lacrado: poucos trades = inconclusivo, nunca reprova (TF alto)
  - periodo anterior: piso -5% do deposito
  - retencao com poucas entradas no OOS = inconclusiva (nem aprova nem reprova)
  - cobertura de tick real lida do log do tester
  - MT5 que nao executou teste = erro de infraestrutura, nunca veredito

    python test_metodologia.py
"""
from __future__ import annotations

import sys

import optimize_two_stage as ots

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- holdout lacrado --------------------------------------------------------
h = ots.avaliar_holdout_lacrado
checar("lacrado sem medida", h(None, None, 1000)["veredito"], "sem_medida")
checar("lacrado D1 com 2 trades e prejuizo: inconclusivo, nao reprova",
       h(-80.0, 2, 1000)["veredito"], "inconclusivo")
checar("lacrado sem trade nenhum: inconclusivo", h(0.0, 0, 1000)["veredito"],
       "inconclusivo")
checar("lacrado com amostra e prejuizo: reprova",
       h(-15.0, ots.MIN_TRADES_LACRADO, 1000)["veredito"], "reprovado")
checar("lacrado com amostra e lucro: aprova", h(40.0, 30, 1000)["veredito"],
       "aprovado")
checar("lacrado zero a zero com amostra: nao e prejuizo",
       h(0.0, 12, 1000)["veredito"], "aprovado")

# --- periodo anterior: -5% --------------------------------------------------
pa = ots.avaliar_periodo_anterior
checar("PA -10% (US500 SELL): reprova agora", pa(-1000.0, 40, 10000)[0], False)
checar("PA -4%: passa", pa(-400.0, 40, 10000)[0], True)
checar("PA amostra pequena: nao avalia", pa(-5000.0, 3, 10000)[0], True)
checar("PA sem medida: nao avalia", pa(None, None, 10000)[0], True)

# --- retencao inconclusiva --------------------------------------------------
ok, mot = ots.veredito(5.0, -40.0, 30, entradas_oos=4)
checar("poucas entradas OOS + retencao ruim: nao reprova", ok, True)
checar("poucas entradas OOS: motivo diz inconclusiva",
       any("INCONCLUSIVA" in m for m in mot), True)
ok, _ = ots.veredito(5.0, -40.0, 30, entradas_oos=ots.MIN_ENTRADAS_OOS_RETENCAO)
checar("amostra suficiente + retencao ruim: reprova", ok, False)
ok, _ = ots.veredito(5.0, None, 30, entradas_oos=3,
                     motivo_retencao="In-Sample quase sem lucro (2.63)")
checar("IS quase sem lucro continua reprovando mesmo com pouca entrada", ok, False)
ok, _ = ots.veredito(45.0, 80.0, 30, entradas_oos=2)
checar("inconclusiva nao salva divergencia reprovada", ok, False)
ok, _ = ots.veredito(5.0, 80.0, 30, entradas_oos=None)
checar("sem contagem de entradas (.ex5 antigo): regra antiga", ok, True)

# --- cobertura de tick real --------------------------------------------------
LOG = ("Tester\tXAUUSD: ticks data begins from 2025.03.01 00:00\n"
       "Tester\tXAUUSD,M1 (RoboForex-ECN): testing of Experts\\X.ex5 from "
       "2024.09.01 00:00 to 2025.09.01 00:00\n")
checar("cobertura: metade do ano com tick real",
       ots.cobertura_tick_real(LOG), 50.4)
checar("cobertura: tick desde antes do teste = 100%",
       ots.cobertura_tick_real(LOG.replace("2025.03.01", "2020.01.01")), 100.0)
checar("cobertura: tick so depois do fim = 0%",
       ots.cobertura_tick_real(LOG.replace("2025.03.01", "2026.01.01")), 0.0)
checar("cobertura: log sem as linhas -> None",
       ots.cobertura_tick_real("final balance 100"), None)

# --- terminal que nao executou ----------------------------------------------
LIVEUPDATE = ("LiveUpdate\tfailed to create copy of terminal64.exe [32]\n"
              "Terminal\tcannot load config otim.ini\n")
try:
    ots.conferir_execucao(LIVEUPDATE, "a otimizacao")
    FALHAS.append("LiveUpdate sem teste: deveria levantar TerminalNaoExecutou")
except ots.TerminalNaoExecutou:
    pass
try:
    ots.conferir_execucao(LOG + "Core 01\tautomatical testing finished\n",
                          "o passe unico")
except ots.TerminalNaoExecutou:
    FALHAS.append("log com teste iniciado nao pode levantar erro")

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("metodologia: todos os casos passaram")
