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


# --- selecionar_ordenado ------------------------------------------------------
# s1 e s2 sobem em linha reta (s2 = 2*s1): correlacao exatamente +1.0.
# s3 desce em linha reta com a mesma soma de s1 (s3 = 6 - s1): correlacao
# exatamente -1.0 com s1 -- negativa e bem-vinda, so a positiva incomoda.
s1 = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
s2 = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
s3 = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
s4_perdedora = pd.Series([-1.0, -2.0, -3.0, -4.0, -5.0])

series = {"s1": s1, "s2": s2, "s3": s3, "s4_perdedora": s4_perdedora}
escolhidas, recusadas = aml.selecionar_ordenado(
    series, ["s1", "s2", "s3", "s4_perdedora"], maximo=4, teto=0.5,
    recuperacao_minima=1.0)
checar("s1 entra (primeiro da ordem)", "s1" in escolhidas, True)
checar("s2 fora (correlacao +1.0 com s1, acima do teto)",
       "s2" in escolhidas, False)
checar("s3 entra (correlacao -1.0 com s1 -- negativa protege)",
       "s3" in escolhidas, True)
checar("s4 nunca entra (resultado negativo)",
       "s4_perdedora" in escolhidas, False)
checar("s4 aparece nas recusadas", any("s4_perdedora" in r for r in recusadas), True)
checar("ordem final respeita a prioridade (s1 antes de s3)",
       escolhidas, ["s1", "s3"])

# maximo limita o tamanho da sugestao mesmo com mais candidatos elegiveis.
escolhidas_lim, _ = aml.selecionar_ordenado(
    series, ["s1", "s2", "s3", "s4_perdedora"], maximo=1, teto=0.5,
    recuperacao_minima=1.0)
checar("maximo=1 devolve so o primeiro", escolhidas_lim, ["s1"])


if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  {f}")
    sys.exit(1)
print("ok")
