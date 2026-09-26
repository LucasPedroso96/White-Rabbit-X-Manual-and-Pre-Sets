# -*- coding: utf-8 -*-
"""Testa a repeticao do passe_unico() quando o agente do tester recusa a
conexao ("authorization failed (Invalid parameters)") -- o teste nem roda --
ou quando o poll de 90s estoura sem sinal nenhum (nem sucesso, nem recusa).

Achado de 2026-09-14: 17 de ~800 passes da bateria_logica perdidos assim, e
no pipeline a mesma falha virava lucro_real=None numa conferencia em tick
real -> "SEM VEREDITO" -> reprovado em silencio. Sem MT5: lancar_terminal,
os logs e a escrita do .ini sao trocados por dubles.

Achado ao vivo, mesmo dia, validando o refactor de 3 slots da Candles: 8 de
11 passes numa fatia isolada deram trades=None em ~92s cada -- nao era o
agente recusando (log sem "authorization failed"), era o poll de 90s
estourando sem "automatic testing finished" nenhum (causa real, confirmada
depois: o MESMO terminal clone tinha uma campanha Bollinger pesada rodando
em paralelo, disputando os 4 agentes locais -- refeito no terminal ocioso,
os mesmos 11 passes rodaram limpo em 10-28s cada). O retry antigo so cobria
a recusa explicita; esse estouro silencioso caia direto pra ler_metricas()
com o log incompleto, sem repetir nunca.

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
# Poll de 90s estourou sem nenhum sinal -- nem "finished" nem "authorization
# failed" (achado ao vivo 2026-09-14, ver docstring do modulo).
LOG_MUDO = "Core 01\tagent process started on 127.0.0.1:3000\n"

chamadas = {"lancar": 0}
roteiro: list[str] = []


def lancar_fake(*_a, **_k) -> None:
    chamadas["lancar"] += 1


def texto_fake(_antes) -> str:
    return roteiro[min(chamadas["lancar"], len(roteiro)) - 1]


def ini_fake(destino, *_a, **_k) -> None:
    Path(destino).write_text("Optimization=2\n", encoding="utf-16")


# time.monotonic() de mentira: avanca 30s "de verdade" a cada chamada, entao
# o poll de 90s (limite = monotonic()+90) fecha em so 3 iteracoes fake em vez
# de segurar o teste por 90s reais quando o roteiro nunca casa TESTE_CONCLUIDO
# (caso LOG_MUDO abaixo).
relogio = {"t": 0.0}


def monotonic_fake() -> float:
    relogio["t"] += 30.0
    return relogio["t"]


def rodar(novo_roteiro: list[str]) -> dict:
    chamadas["lancar"] = 0
    relogio["t"] = 0.0
    roteiro[:] = novo_roteiro
    set_falso = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_teste_agente.set"
    return ots.passe_unico(set_falso, "EURUSD", "M1", "2026.01.01",
                           "2026.02.01", 1000, 1)


originais = (ots.lancar_terminal, base.marcar_logs, base.texto_novo,
             base.escrever_ini, ots.time.sleep, ots.time.monotonic)
ots.lancar_terminal = lancar_fake
base.marcar_logs = lambda: {}
base.texto_novo = texto_fake
base.escrever_ini = ini_fake
ots.time.sleep = lambda _s: None
ots.time.monotonic = monotonic_fake
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

    # --- poll estoura mudo (sem "finished" nem recusa), depois roda: repete
    r = rodar([LOG_MUDO, LOG_OK])
    checar("estouro mudo + sucesso: relanca uma vez", chamadas["lancar"], 2)
    checar("estouro mudo + sucesso: trades da tentativa boa", r["trades"], 12)

    # --- poll estoura mudo sempre, SEM teste nenhum iniciado: e falha de
    # infraestrutura (2026-09-26, LiveUpdate do build 6230) -- levanta em vez
    # de devolver trades=None, que o circuito lia como reprovacao
    try:
        rodar([LOG_MUDO] * (ots.TENTATIVAS_AGENTE + 2))
        FALHAS.append("sempre mudo sem teste: deveria levantar "
                      "TerminalNaoExecutou")
    except ots.TerminalNaoExecutou:
        pass
    checar("sempre mudo: para em TENTATIVAS_AGENTE", chamadas["lancar"],
           ots.TENTATIVAS_AGENTE)

    # --- teste INICIOU mas nunca terminou: resultado vazio, sem excecao
    LOG_INICIOU = LOG_MUDO + ("Core 01\tEURUSD,M1: testing of Experts\\X.ex5 "
                              "from 2026.01.01 00:00 to 2026.02.01 00:00\n")
    r = rodar([LOG_INICIOU] * (ots.TENTATIVAS_AGENTE + 2))
    checar("iniciou e nao terminou: trades vazio", r["trades"], None)
finally:
    (ots.lancar_terminal, base.marcar_logs, base.texto_novo,
     base.escrever_ini, ots.time.sleep, ots.time.monotonic) = originais

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("passe_unico_agente: todos os casos passaram")
