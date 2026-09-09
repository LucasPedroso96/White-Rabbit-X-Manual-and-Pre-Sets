# -*- coding: utf-8 -*-
"""Retomada da confirmacao longa depois que o PC desligou no meio do
07_GRID_SEPARATE (27/08/2026, ~10h29 -- so a formula 1/3 chegou a rodar, e
parou no estagio 1/5, sem veredito). 04_SLTP_TRAIL, 05_BE_TRAIL,
12_GRID_INVERSO e 10_DALEMBERT ja fecharam a confirmacao de 1 ano antes do
desligamento (09_MARTINGALE foi pulado, sem candidato) -- nao repete esses.
Formulas aprovadas vem do snapshot salvo (TRIAGEM_CURTA_SNAPSHOT_2026-08-26.md),
nao re-derivadas dos logs, porque o log da formula 1 do grid ja foi
sobrescrito pela tentativa interrompida. Uso interno, apagar depois."""
import subprocess
import sys
from pathlib import Path

TAREFAS = [
    ("07_GRID_SEPARATE", "AUDNZD", 1000, "1,5,7"),
    ("03_TRAIL_ONLY", "XAUUSD", 10000, "7,8,13"),
]

DE = "2025.08.25"
ATE = "2026.08.25"

for sistema, simbolo, deposito, lista in TAREFAS:
    print(f"\n########## RETOMADA CONFIRMACAO LONGA (1 ano) {sistema}/{simbolo}: "
          f"formulas {lista} ##########", flush=True)
    log = Path(f"confirmacao_longa_{sistema}_{simbolo}_master.log")
    with log.open("w", encoding="utf-8") as fh:
        ret = subprocess.run(
            [sys.executable, "sweep_formulas.py",
             "--sistema", sistema, "--simbolo", simbolo,
             "--deposit", str(deposito), "--formulas", lista,
             "--from-data", DE, "--to-data", ATE],
            stdout=fh, stderr=subprocess.STDOUT)
    print(f"########## FIM confirmacao {sistema}/{simbolo} "
          f"(returncode={ret.returncode}) ##########", flush=True)

print("\n########## CONFIRMACAO LONGA COMPLETA (retomada) ##########", flush=True)
