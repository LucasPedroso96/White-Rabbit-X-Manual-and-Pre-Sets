# -*- coding: utf-8 -*-
"""medir_wfa NAO pode herdar os inputs de WFO da corrida original.

Regressao do bug de 2026-09-21: `travados` trazia input_end_date/
wfo_customWindowSizeDays de outra epoca; numa janela de anos atras a EA via o
fim do teste diferente de input_end_date (tolerancia 80 h) e o OnTester
devolvia 0.0 em todo passe (otimizacao as cegas). Aqui capturamos o que
medir_wfa manda pro MT5 -- sem terminal -- e exigimos WFO desligado na busca
IS e no passe OOS de CADA janela.
"""
from __future__ import annotations

import sys
from pathlib import Path

import optimize_sets as base
import optimize_two_stage as ots
import wfa_real

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


capturado = {"reescrever": [], "rodar": [], "medir": []}


def fake_reescrever(origem, destino, otimizar, travar):
    capturado["reescrever"].append(dict(travar))
    return len(otimizar)


def fake_rodar(caminho, symbol, periodo, inicio, fim, deposito, modelo,
               timeout, variante=""):
    capturado["rodar"].append((inicio, fim))
    cab = ["Pass", "Result", "Profit", "Expected Payoff", "Profit Factor",
           "Recovery Factor", "Sharpe Ratio", "Custom", "Equity DD %",
           "Trades", "EixoA"]
    return cab, [["1", "5.0", "100.0", "1", "2.0", "1", "1", "5.0", "10.0",
                  "50", "7"]]


def fake_medir(origem, params, simbolo, periodo, inicio, fim, deposito):
    capturado["medir"].append((dict(params), inicio, fim))
    return {"profit": 50.0}


orig = (ots.reescrever, ots.rodar, ots._medir_desempenho,
        base.escolher_candidatos)
ots.reescrever, ots.rodar, ots._medir_desempenho = (
    fake_reescrever, fake_rodar, fake_medir)
base.escolher_candidatos = lambda cab, linhas, piso, pf: linhas
try:
    # travados COM os inputs de WFO velhos (o que a corrida original deixa)
    velhos = {"AtivarWFO": "true", "MetodoDeEntradawfo": "0",
              "input_end_date": "2026.09.12", "wfo_customWindowSizeDays": "122",
              "EixoB": "3"}
    r = wfa_real.medir_wfa(Path("dummy_origem.set"), velhos, ["EixoA"],
                           "XAUUSD", "04_SLTP_TRAIL", "M1", "2023.09.21",
                           "2026.09.20", 1000, ciclos_alvo=4, timeout=60)
finally:
    (ots.reescrever, ots.rodar, ots._medir_desempenho) = orig[:3]
    base.escolher_candidatos = orig[3]

n_jan = len(capturado["rodar"])
checar("rodou uma busca IS por janela", n_jan >= 2, True)
checar("uma medida OOS por janela", len(capturado["medir"]), n_jan)
for i, tr in enumerate(capturado["reescrever"], 1):
    checar(f"janela {i}: busca IS com AtivarWFO=false", tr.get("AtivarWFO"), "false")
    checar(f"janela {i}: busca IS com MetodoDeEntradawfo=1",
           tr.get("MetodoDeEntradawfo"), "1")
    checar(f"janela {i}: nao vaza eixo travado", tr.get("EixoB"), "3")
for i, (params, ini, fim) in enumerate(capturado["medir"], 1):
    checar(f"janela {i}: passe OOS com AtivarWFO=false", params.get("AtivarWFO"), "false")
    checar(f"janela {i}: passe OOS com MetodoDeEntradawfo=1",
           params.get("MetodoDeEntradawfo"), "1")
checar("o dict de entrada nao foi alterado (sem efeito colateral)",
       velhos["AtivarWFO"], "true")
checar("WFO_DESLIGADO exposto", wfa_real.WFO_DESLIGADO,
       {"AtivarWFO": "false", "MetodoDeEntradawfo": "1"})

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("medir_wfa sem WFO interno: todos os casos passaram")
