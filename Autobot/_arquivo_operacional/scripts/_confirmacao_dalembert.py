# -*- coding: utf-8 -*-
"""Confirmacao de 1 ano das 6 formulas aprovadas na retriagem curta do
10_DALEMBERT pos-fix do piso (29/08/2026): GridSurvivalScore(1),
ProfitWinTradeDD(3), ProfitRelativeToDDAndDeposit(6), PessimisticProfit(9),
SystemRobustness(12), SomaR(14). Ultima etapa da recalibracao dos 7
sistemas. Uso interno, apagar depois."""
import subprocess
import sys
from pathlib import Path

PY = sys.executable
log = Path("confirmacao_longa_10_DALEMBERT_AUDNZD_pos_fix_master.log")
print("\n########## CONFIRMACAO LONGA (1 ano) 10_DALEMBERT/AUDNZD: "
      "formulas 1,3,6,9,12,14 ##########", flush=True)
with log.open("w", encoding="utf-8") as fh:
    ret = subprocess.run(
        [PY, "sweep_formulas.py", "--sistema", "10_DALEMBERT", "--simbolo", "AUDNZD",
         "--deposit", "1000", "--formulas", "1,3,6,9,12,14",
         "--from-data", "2025.08.25", "--to-data", "2026.08.25"],
        stdout=fh, stderr=subprocess.STDOUT)
print(f"########## FIM confirmacao 10_DALEMBERT/AUDNZD "
      f"(returncode={ret.returncode}) ##########", flush=True)
print("\n########## CONFIRMACAO 10_DALEMBERT COMPLETA -- RODADA DOS 7 SISTEMAS ENCERRADA ##########",
      flush=True)
