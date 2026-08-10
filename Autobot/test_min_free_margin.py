# -*- coding: utf-8 -*-
"""Testa MinFreeMarginPercent nos sistemas sem SL nativo (dono, 2026-08-10):
apply_defaults() zera esse input pra todo mundo (neutro pros 6 sistemas
Fixed-R, que ja tem CapitalBaseR como rede de risco). Mas grid (07/08),
martingale (09) e d'Alembert (10) NAO tem SL nativo -- a EA ja tem um guard
de verdade (CanSendTradeRequest, .mq5) que recusa nova ordem se a margem
livre projetada cair abaixo deste percentual, e ele ficava desligado (0)
bem nesses tres sistemas -- exatamente onde mais importa. Sem cobertura
de contagem (MaxLongTrades/MaxShortTrades continua 999 por decisao do
dono -- nao e essa a trava), a margem livre real e o unico freio que
sobra durante a busca genetica, entao ela nao pode ficar zerada aqui.

    python test_min_free_margin.py
"""
from __future__ import annotations

import sys

from generate_system_sets import CLASSES, Profile, apply_defaults, apply_system

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def _min_free_margin(sistema: str) -> str:
    ac = CLASSES["01_Forex"]
    p = Profile()
    apply_defaults(p, ac, "BUY", magic=1, name="teste")
    apply_system(p, sistema, ac, "BUY")
    return p.values["MinFreeMarginPercent"]


for sistema in ("07_GRID_SEPARATE", "08_GRID_UNIFIED",
                "09_MARTINGALE", "10_DALEMBERT"):
    valor_atual = _min_free_margin(sistema).split("||")[0]
    checar(f"{sistema}: MinFreeMarginPercent nao fica zerado",
           valor_atual != "0", True)

# Sistemas com CapitalBaseR (Fixed-R) ja tem rede de risco propria --
# continuam neutros (0), nada muda pra eles.
for sistema in ("01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY",
                "04_SLTP_TRAIL", "05_BE_TRAIL", "06_REVERSAL_EXIT"):
    valor_atual = _min_free_margin(sistema).split("||")[0]
    checar(f"{sistema}: MinFreeMarginPercent continua neutro (Fixed-R ja "
           "protege)", valor_atual, "0")

# 11_SIGNAL_ONLY e deliberadamente sem rede (tier HIGH_RISK_RESEARCH,
# achado documentado 2026-08-10) -- continua neutro tambem, de proposito.
checar("11_SIGNAL_ONLY: continua sem rede, por decisao de tier",
       _min_free_margin("11_SIGNAL_ONLY").split("||")[0], "0")

# MaxLongTrades/MaxShortTrades do grid continuam 999 -- decisao explicita
# do dono de NAO travar por contagem, so por margem real.
ac = CLASSES["01_Forex"]
p = Profile()
apply_defaults(p, ac, "BOTH", magic=1, name="teste")
apply_system(p, "08_GRID_UNIFIED", ac, "BOTH")
checar("grid: MaxLongTrades continua 999 (sem teto de contagem)",
       p.values["MaxLongTrades"].split("||")[0], "999")


if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("min_free_margin: todos os casos passaram")
