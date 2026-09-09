# -*- coding: utf-8 -*-
"""Retomada pontual do 12_GRID_INVERSO/XAUUSD depois que o PC desligou
sem querer no meio da formula 8/15 (2026-09-03). Formulas 1-7 ja
rodaram completas e reais (log termina em JSON, todas REPROVADO -- sem
campeao pra este combo ainda, entao pular elas nao perde nada) -- so
faltam 8-15. Roda so essas, escreve no MESMO log que a fila 2 esperava
(_fila2_12_GRID_INVERSO_XAUUSD.log) e fecha o marcador de conclusao da
fila 2 igual o script normal faria, pra fila 3 (que ja esta esperando
o marcador) seguir sozinha. Uso interno, apagar depois."""
import subprocess
import sys
from pathlib import Path

log = Path("_fila2_12_GRID_INVERSO_XAUUSD.log")
with log.open("w", encoding="utf-8") as fh:
    resultado = subprocess.run(
        [sys.executable, "sweep_formulas.py",
         "--sistema", "12_GRID_INVERSO", "--simbolo", "XAUUSD",
         "--deposit", "10000",
         "--formulas", "8,9,10,11,12,13,14,15"],
        stdout=fh, stderr=subprocess.STDOUT)

master = Path("_fila_calibracao_restante_2_master.log")
with master.open("a", encoding="utf-8") as fm:
    fm.write("\n===== FILA 2: 12_GRID_INVERSO / XAUUSD (deposito 10000) "
              "-- RETOMADO apos queda de energia, formulas 8-15 =====\n")
    fm.write(f"    log salvo em {log} (exit={resultado.returncode})\n")
    fm.write("\n===== FILA 2 COMPLETA =====\n")

print(f"\n12_GRID_INVERSO retomado e concluido (exit={resultado.returncode}).",
      flush=True)
