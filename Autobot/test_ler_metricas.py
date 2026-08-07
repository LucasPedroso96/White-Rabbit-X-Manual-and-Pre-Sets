# -*- coding: utf-8 -*-
"""Testa a leitura do log sem precisar do MT5.

Existe porque dois defeitos de UMA linha em ler_metricas() so apareceram depois
dos ~25 min de otimizacao que rodam antes dela -- e a segunda vez derrubou a
corrida inteira no ultimo passo. O parsing nao depende do terminal, entao nao ha
motivo para so descobrir que ele quebrou depois de meia hora.

    python test_ler_metricas.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import wrx_paths
from optimize_two_stage import ler_metricas

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- corrida completa, como a EA imprime ------------------------------------
COMPLETO = """
2026.07.20 23:59:58   ==================== R METRICS ====================
2026.07.20 23:59:58   Fixed-R mode: 1R = 5.00 USD | base capital = 500.00
2026.07.20 23:59:58   Trades: 410 | Total R: +64.20 | Average R (expectancy): +0.157
2026.07.20 23:59:58   Win rate: 36.3% | Payoff: 2.30R | Largest gain: +3.16R
final balance 827.92 USD
2026.07.20 23:59:58   Out-of-Sample Retention: 41.50% (out-of-sample daily ...)
automatical testing finished
"""
m = ler_metricas(COMPLETO)
checar("saldo", m["saldo"], 827.92)
checar("trades", m["trades"], 410)
checar("total_r", m["total_r"], 64.20)
checar("expectancy", m["expectancy"], 0.157)
checar("win_rate", m["win_rate"], 36.3)
checar("retencao", m["retencao"], 41.5)

# --- expectancy negativa: o sinal de menos tem que sobreviver ---------------
NEGATIVO = COMPLETO.replace("Average R (expectancy): +0.157",
                            "Average R (expectancy): -0.088")
checar("expectancy negativa", ler_metricas(NEGATIVO)["expectancy"], -0.088)

# --- retencao negativa: OOS perdeu dinheiro, e um resultado valido ----------
NEG_RET = COMPLETO.replace("Retention: 41.50%", "Retention: -12.75%")
checar("retencao negativa", ler_metricas(NEG_RET)["retencao"], -12.75)

# --- In-Sample sem lucro: a EA escreve texto, nao numero --------------------
# None e 0.0 precisam continuar distintos: "nao ha o que reter" nao e "reteve
# zero". Tratar os dois como 0.0 foi o que fez a retencao parecer medida.
NAO_APLICA = COMPLETO.replace(
    "Out-of-Sample Retention: 41.50% (out-of-sample daily ...)",
    "Out-of-Sample Retention: not applicable - In-Sample was not profitable")
checar("retencao n/a", ler_metricas(NAO_APLICA)["retencao"], None)

# --- modo In-Sample: retencao 0.00% e um numero, nao ausencia ---------------
ZERO = COMPLETO.replace("Retention: 41.50%", "Retention: 0.00%")
checar("retencao zero", ler_metricas(ZERO)["retencao"], 0.0)

# --- log vazio: tudo None, nada de excecao ---------------------------------
vazio = ler_metricas("")
checar("vazio/saldo", vazio["saldo"], None)
checar("vazio/trades", vazio["trades"], None)
checar("vazio/abortos", vazio["abortos"], 0)

# --- log CUMULATIVO: tem que pegar a corrida mais recente -------------------
ANTIGO = COMPLETO.replace("Trades: 410", "Trades: 184").replace(
    "final balance 827.92", "final balance 591.63")
checar("cumulativo/trades", ler_metricas(ANTIGO + COMPLETO)["trades"], 410)
checar("cumulativo/saldo", ler_metricas(ANTIGO + COMPLETO)["saldo"], 827.92)

# --- e contra um log REAL, se houver um por perto ---------------------------
try:
    LOGS = wrx_paths.data_dir() / "Tester" / "logs"
except SystemExit:
    LOGS = None
reais = sorted(LOGS.glob("*.log"), key=lambda p: p.stat().st_mtime) \
    if LOGS and LOGS.is_dir() else []
if reais:
    texto = reais[-1].read_text(encoding="utf-16-le", errors="replace")
    r = ler_metricas(texto)
    print(f"log real ({reais[-1].name}): trades={r['trades']} "
          f"saldo={r['saldo']} expectancy={r['expectancy']} "
          f"retencao={r['retencao']}")
    if r["trades"] is None:
        FALHAS.append("log real: nao achou o bloco R METRICS")

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("ler_metricas: todos os casos passaram")
