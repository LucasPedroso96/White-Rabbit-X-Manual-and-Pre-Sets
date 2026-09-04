# -*- coding: utf-8 -*-
"""Testa a montagem do .set do Estagio 1.5 (--indicador-solo).

Existe porque o estagio depende de UMA sutileza de reescrever(): ela checa
`nome in travar` ANTES de `nome in otimizar`, entao cravar EntryIndicator e
so poe-lo em `travar` -- mas os DEMAIS eixos de escrita (EntryMethod,
TimeFrame, InpAppliedPrice, flags) precisam continuar em Y, senao a fase
inteira vira uma revalidacao do mesmo ponto que o Estagio 1 ja achou. Esse
erro exato ja aconteceu no Estagio 3.5 ("0 parametros" no primeiro combo
real, AUDCAD) e custou uma corrida completa pra ser notado -- ali a correcao
foi travados_sem_geo; aqui e o inverso, e o teste trava as duas pontas.

Roda em milissegundos, sem MT5, sem tocar a biblioteca (escreve num .set
temporario).

    python test_indicador_solo.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from optimize_two_stage import ESCRITA, eixos_da_fase1, eixos_do_indicador, reescrever

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# Amostra minima no formato da biblioteca: nome=valor||inicio||passo||fim||flag.
# EntryIndicator com faixa 0..10 (o eixo MULTI), mais um eixo de escrita
# (EntryMethod), um numerico (Fast_EMA), um condicional ao indicador
# (StochasticSlowing, so vale pro Stochastic=3) e um sem faixa (Hedging).
ORIGEM = """; White Rabbit X
EntryIndicator=0||0||1||10||Y
EntryMethod=0||0||1||2||Y
TimeFrame=0||0||1||5||Y
Fast_EMA=12||6||2||24||Y
StochasticSlowing=3||3||1||9||Y
AtivarFiltroMA=false||false||0||true||Y
Hedging=true||true||0||true||N
TOD_From_Hour=0||0||1||23||Y
selectedFormula=10||10||1||10||N
"""

tmp = Path(tempfile.mkdtemp())
origem = tmp / "origem.set"
destino = tmp / "_ETAPA.set"
origem.write_text(ORIGEM.replace("\n", "\r\n"), encoding="utf-16")


def ler(caminho: Path) -> dict[str, list[str]]:
    saida = {}
    for linha in caminho.read_text(encoding="utf-16").replace("\r", "").split("\n"):
        if "=" in linha and not linha.startswith(";"):
            nome, valor = linha.split("=", 1)
            saida[nome] = valor.split("||")
    return saida


# --- Estagio 1: tudo com faixa, menos os filtros de execucao ----------------
eixos_fase1 = eixos_da_fase1(origem)
checar("estagio 1: TOD_From_Hour fica de fora (filtro de execucao)",
       "TOD_From_Hour" in eixos_fase1, False)
checar("estagio 1: Hedging fica de fora (sem faixa)",
       "Hedging" in eixos_fase1, False)
checar("estagio 1: EntryIndicator entra", "EntryIndicator" in eixos_fase1, True)

# --- Estagio 1.5 com vencedor Stochastic (3) --------------------------------
ind = "3"
eixos_solo = eixos_do_indicador(
    [e for e in eixos_fase1 if e != "EntryIndicator"], ind)
checar("solo: EntryIndicator sai da lista de otimizar",
       "EntryIndicator" in eixos_solo, False)
checar("solo: StochasticSlowing fica (o vencedor E o Stochastic)",
       "StochasticSlowing" in eixos_solo, True)

n = reescrever(origem, destino, eixos_solo, {"EntryIndicator": ind})
gravado = ler(destino)

checar("solo: EntryIndicator cravado no vencedor", gravado["EntryIndicator"][0], "3")
checar("solo: EntryIndicator sai de Y", gravado["EntryIndicator"][4], "N")
# O ponto central: a escrita RESTANTE continua aberta. Sem isso a fase so
# revalidaria o vencedor do Estagio 1 em vez de rebusca-lo.
for nome in ("EntryMethod", "TimeFrame", "AtivarFiltroMA"):
    checar(f"solo: {nome} (escrita) continua em Y", gravado[nome][4], "Y")
    checar(f"solo: {nome} esta em ESCRITA", nome in ESCRITA, True)
checar("solo: Fast_EMA (numerico) continua em Y", gravado["Fast_EMA"][4], "Y")
checar("solo: TOD_From_Hour segue fora", gravado["TOD_From_Hour"][4], "N")
checar("solo: contagem de Y bate com o gravado", n,
       sum(1 for p in gravado.values() if len(p) == 5 and p[4] == "Y"))
checar("solo: a fase tem eixo de verdade pra buscar", n > 0, True)

# --- vencedor que NAO usa os eixos condicionais -----------------------------
eixos_ema = eixos_do_indicador(
    [e for e in eixos_fase1 if e != "EntryIndicator"], "1")   # EMA_Cross
checar("solo/EMA: StochasticSlowing sai (o EMA nao usa)",
       "StochasticSlowing" in eixos_ema, False)
n_ema = reescrever(origem, destino, eixos_ema, {"EntryIndicator": "1"})
checar("solo/EMA: menos eixos que o Stochastic", n_ema < n, True)
checar("solo/EMA: StochasticSlowing gravado em N",
       ler(destino)["StochasticSlowing"][4], "N")

# --- set com indicador cravado (variante ICHIMOKU): a fase nao se aplica ----
checar("ICHIMOKU: sem indicador, eixos_do_indicador nao filtra nada",
       eixos_do_indicador(["StochasticSlowing", "Fast_EMA"], None),
       ["StochasticSlowing", "Fast_EMA"])

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("estagio 1.5 (indicador solo): todos os casos passaram")
