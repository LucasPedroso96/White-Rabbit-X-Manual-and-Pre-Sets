# -*- coding: utf-8 -*-
"""Testa o motor de sugestao do AutoManagerLive sem precisar do MT5 nem do
dashboard -- puro Python sobre dados sinteticos, mesmo espirito de
test_ready_library.py.

    python test_auto_manager_live.py
"""
from __future__ import annotations

import sys

import pandas as pd

import auto_manager_live as aml

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- capital_minimo_classe ---------------------------------------------------
checar("classe direta: metais", aml.capital_minimo_classe("XAUUSD"), 10000)
checar("classe direta: forex", aml.capital_minimo_classe("EURUSD"), 500)
checar("classe com ponto proprio (nao e sufixo)",
       aml.capital_minimo_classe("BRK.B"), 5000)
checar("sufixo de corretora/HT cai pro radical",
       aml.capital_minimo_classe("EURUSD.HT"), 500)
checar("sufixo bare de broker (sem separador) -- nao resolvido (limitacao conhecida)",
       aml.capital_minimo_classe("EURUSDm"), None)
checar("simbolo desconhecido", aml.capital_minimo_classe("NAOEXISTE"), None)
checar("regressao: simbolo real nao misclassificado por short ticker (V = Visa stock)",
       aml.capital_minimo_classe("VETUSD"), None)


# --- ordenar_candidatos -------------------------------------------------------
combos = [
    {"chave": "hedge_alta", "sistema": "07_GRID_SEPARATE", "retencao": 90.0, "mc_prob_ruina": 0.01},
    {"chave": "research_baixa", "sistema": "01_SLTP", "retencao": 10.0, "mc_prob_ruina": 0.04},
    {"chave": "research_alta", "sistema": "02_SLTP_ORGANIC", "retencao": 80.0, "mc_prob_ruina": 0.02},
    {"chave": "research_sem_retencao", "sistema": "03_TRAIL_ONLY", "retencao": None, "mc_prob_ruina": None},
]
ordenados = [c["chave"] for c in aml.ordenar_candidatos(combos)]
checar("tier RESEARCH antes de HEDGE, e dentro do tier maior retencao primeiro",
       ordenados,
       ["research_alta", "research_baixa", "research_sem_retencao", "hedge_alta"])


if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  {f}")
    sys.exit(1)
print("ok")
