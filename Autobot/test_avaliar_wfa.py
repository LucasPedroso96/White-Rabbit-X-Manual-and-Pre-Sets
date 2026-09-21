# -*- coding: utf-8 -*-
"""Piso do WFA calibrado com os candidatos revalidados (WFA corrigido).

Casos REAIS de 2026-09-21: (sistema, ciclos, WFE) -> veredito esperado. O gate
antigo ("WFE global > 0") deixava passar o campeao real 02_SLTP_ORGANIC com 2/4
ciclos e WFE ~0%; o piso novo o barra e mantem todos os candidatos bons.
"""
from __future__ import annotations

import sys

from optimize_two_stage import (WFA_FRACAO_CICLOS_MIN, WFA_WFE_MIN_PCT,
                                WFA_WFE_MIN_PCT_SEM_SL, avaliar_wfa)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# (rotulo, sistema, ciclos, wfe, passa?)
REAIS = [
    ("11_SIGNAL f09",        "11_SIGNAL_ONLY",   "3/4", 126.9, True),
    ("04 XAUUSD f09",        "04_SLTP_TRAIL",    "4/4", 88.0,  True),
    ("04 XAUUSD f11 (oficial)", "04_SLTP_TRAIL", "3/4", 66.0,  True),
    ("04 XAUUSD f11",        "04_SLTP_TRAIL",    "3/4", 49.0,  True),
    ("04 XAUUSD f04",        "04_SLTP_TRAIL",    "4/4", 48.0,  True),
    ("05_BE XAUUSD f03",     "05_BE_TRAIL",      "3/4", 47.0,  True),
    ("04 XAUUSD f08",        "04_SLTP_TRAIL",    "4/4", 46.0,  True),
    ("04 XAUUSD f03",        "04_SLTP_TRAIL",    "3/4", 39.0,  True),
    ("04 XAUUSD f12",        "04_SLTP_TRAIL",    "3/4", 38.0,  True),
    ("04 XAUUSD f01",        "04_SLTP_TRAIL",    "3/4", 34.0,  True),
    ("11_SIGNAL f11",        "11_SIGNAL_ONLY",   "3/4", 20.0,  True),   # sem SL: piso 10
    ("07_GRID AUDNZD f10",   "07_GRID_SEPARATE", "3/4", 12.0,  True),   # grade: piso 10
    ("CAMPEAO 02 GBPUSD",    "02_SLTP_ORGANIC",  "2/4", 0.3,   False),  # WFE ~0%
    ("04 XAUUSD f10",        "04_SLTP_TRAIL",    "2/3", -37.0, False),
]
for rot, sis, ciclos, wfe, esperado in REAIS:
    checar(f"real: {rot}", avaliar_wfa(wfe, ciclos, sis)[0], esperado)

# --- limites e bordas --------------------------------------------------------
checar("constantes", (WFA_WFE_MIN_PCT, WFA_WFE_MIN_PCT_SEM_SL, WFA_FRACAO_CICLOS_MIN),
       (20.0, 10.0, 0.5))
checar("Fixed-R: 20.0 passa", avaliar_wfa(20.0, "3/4", "04_SLTP_TRAIL")[0], True)
checar("Fixed-R: 19.9 reprova", avaliar_wfa(19.9, "3/4", "04_SLTP_TRAIL")[0], False)
checar("grade: 10.0 passa", avaliar_wfa(10.0, "3/4", "12_GRID_INVERSO")[0], True)
checar("grade: 9.9 reprova", avaliar_wfa(9.9, "3/4", "12_GRID_INVERSO")[0], False)
# ciclos: minimo = ceil(50%)
checar("2/4 com WFE alto passa (metade)", avaliar_wfa(80, "2/4", "04_SLTP_TRAIL")[0], True)
checar("1/4 com WFE alto reprova", avaliar_wfa(80, "1/4", "04_SLTP_TRAIL")[0], False)
checar("2/3 passa (ceil(1.5)=2)", avaliar_wfa(80, "2/3", "04_SLTP_TRAIL")[0], True)
checar("1/3 reprova", avaliar_wfa(80, "1/3", "04_SLTP_TRAIL")[0], False)
checar("1/2 passa (ceil(1)=1)", avaliar_wfa(80, "1/2", "04_SLTP_TRAIL")[0], True)
# dados ausentes
ok, msg = avaliar_wfa(None, None, "04_SLTP_TRAIL")
checar("sem WFE reprova", ok, False)
checar("sem WFE: motivo", "sem nenhuma janela" in msg, True)
checar("ciclos ilegivel nao derruba (so WFE decide)",
       avaliar_wfa(50, None, "04_SLTP_TRAIL")[0], True)
checar("motivo de piso cita o piso",
       "piso de 20%" in avaliar_wfa(5, "3/4", "04_SLTP_TRAIL")[1], True)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("avaliar_wfa: todos os casos passaram")
