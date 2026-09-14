# -*- coding: utf-8 -*-
"""Testa a repeticao do passe_unico() quando o agente do tester recusa a
conexao ("authorization failed (Invalid parameters)") -- o teste nem roda.

Achado de 2026-09-14: 17 de ~800 passes da bateria_logica perdidos assim, e
no pipeline a mesma falha virava lucro_real=None numa conferencia em tick
real -> "SEM VEREDITO" -> reprovado em silencio. Sem MT5: lancar_terminal,
os logs e a escrita do .ini sao trocados por dubles.

    python test_passe_unico_agente.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import optimize_sets as base
import optimize_two_stage as ots

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# Mesmo texto que o MT5 grava no log (conferido no log real do terminal).
LOG_RECUSA = ("Core 01\tagent process started on 127.0.0.1:3000\n"
              "Core 01\tauthorization failed (Invalid parameters)\n"
              "Tester\tautomatic testing finished\n")
LOG_OK = ("Trades: 12 | Total R: +3.00 | Average R (expectancy): +0.250\n"
          "final balance 1030.00 USD\n"
          "Tester\tautomatic testing finished\n")

chamadas = {"lancar": 0}
roteiro: list[str] = []


def lancar_fake(*_a, **_k) -> None:
    chamadas["lancar"] += 1


def texto_fake(_antes) -> str:
    return roteiro[min(chamadas["lancar"], len(roteiro)) - 1]


def ini_fake(destino, *_a, **_k) -> None:
    Path(destino).write_text("Optimization=2\n", encoding="utf-16")


def rodar(novo_roteiro: list[str]) -> dict:
    chamadas["lancar"] = 0
    roteiro[:] = novo_roteiro
    set_falso = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_teste_agente.set"
    return ots.passe_unico(set_falso, "EURUSD", "M1", "2026.01.01",
                           "2026.02.01", 1000, 1)


originais = (ots.lancar_terminal, base.marcar_logs, base.texto_novo,
             base.escrever_ini, ots.time.sleep)
ots.lancar_terminal = lancar_fake
base.marcar_logs = lambda: {}
base.texto_novo = texto_fake
base.escrever_ini = ini_fake
ots.time.sleep = lambda _s: None
try:
    # --- agente recusa uma vez, depois roda: repete e usa o resultado bom
    r = rodar([LOG_RECUSA, LOG_OK])
    checar("recusa + sucesso: relanca uma vez", chamadas["lancar"], 2)
    checar("recusa + sucesso: trades da tentativa boa", r["trades"], 12)
    checar("recusa + sucesso: saldo da tentativa boa", r["saldo"], 1030.0)

    # --- agente recusa sempre: para no limite, sem inventar resultado
    r = rodar([LOG_RECUSA] * (ots.TENTATIVAS_AGENTE + 2))
    checar("sempre recusa: para em TENTATIVAS_AGENTE", chamadas["lancar"],
           ots.TENTATIVAS_AGENTE)
    checar("sempre recusa: saldo vazio, nao inventado", r["saldo"], None)
    checar("sempre recusa: trades vazio", r["trades"], None)

    # --- roda de primeira: nao repete nada (custo zero no caminho normal)
    r = rodar([LOG_OK])
    checar("sucesso de primeira: um lancamento so", chamadas["lancar"], 1)
    checar("sucesso de primeira: resultado lido", r["trades"], 12)
finally:
    (ots.lancar_terminal, base.marcar_logs, base.texto_novo,
     base.escrever_ini, ots.time.sleep) = originais

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("passe_unico_agente: todos os casos passaram")
