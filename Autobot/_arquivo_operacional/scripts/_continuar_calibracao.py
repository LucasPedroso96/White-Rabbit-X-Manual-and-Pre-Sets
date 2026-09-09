# -*- coding: utf-8 -*-
"""Continuacao da calibracao pos-fixes (28/08/2026):
1. Confirmacao de 1 ano das formulas novas que apareceram na re-triagem:
   09_MARTINGALE (4: GridSurvivalScore, ProfitWinTradeDD, ReturnUniformity,
   SystemRobustness) e 04_SLTP_TRAIL (1: ProfitWinTradeDD, unica que
   sobreviveu ao fix de geometria tick-real, divergencia 0.0%).
2. Retriagem curta completa (14 formulas) do 10_DALEMBERT, que ainda nunca
   rodou com o fix do piso -- so 09_MARTINGALE foi usado pra validar antes.
Uso interno, apagar depois."""
import subprocess
import sys
from pathlib import Path

PY = sys.executable
DE_LONGA, ATE_LONGA = "2025.08.25", "2026.08.25"
DE_CURTA, ATE_CURTA = "2026.05.22", "2026.08.22"

TAREFAS_CONFIRMACAO = [
    ("09_MARTINGALE", "AUDNZD", 1000, "1,3,11,12"),
    ("04_SLTP_TRAIL", "XAUUSD", 10000, "3"),
]

for sistema, simbolo, deposito, lista in TAREFAS_CONFIRMACAO:
    print(f"\n########## CONFIRMACAO LONGA (1 ano) {sistema}/{simbolo}: "
          f"formulas {lista} ##########", flush=True)
    log = Path(f"confirmacao_longa_{sistema}_{simbolo}_pos_fix_master.log")
    with log.open("w", encoding="utf-8") as fh:
        ret = subprocess.run(
            [PY, "sweep_formulas.py", "--sistema", sistema, "--simbolo", simbolo,
             "--deposit", str(deposito), "--formulas", lista,
             "--from-data", DE_LONGA, "--to-data", ATE_LONGA],
            stdout=fh, stderr=subprocess.STDOUT)
    print(f"########## FIM confirmacao {sistema}/{simbolo} "
          f"(returncode={ret.returncode}) ##########", flush=True)

print("\n########## RETRIAGEM CURTA 10_DALEMBERT (14 formulas) ##########",
      flush=True)
log = Path("sweep_10_DALEMBERT_AUDNZD_pos_fix_master.log")
with log.open("w", encoding="utf-8") as fh:
    ret = subprocess.run(
        [PY, "sweep_formulas.py", "--sistema", "10_DALEMBERT", "--simbolo", "AUDNZD",
         "--deposit", "1000", "--from-data", DE_CURTA, "--to-data", ATE_CURTA],
        stdout=fh, stderr=subprocess.STDOUT)
print(f"########## FIM retriagem 10_DALEMBERT (returncode={ret.returncode}) ##########",
      flush=True)

print("\n########## CONTINUACAO DA CALIBRACAO COMPLETA ##########", flush=True)
