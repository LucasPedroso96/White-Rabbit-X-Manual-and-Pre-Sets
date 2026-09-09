# -*- coding: utf-8 -*-
"""Fila oficial pos-triagem (dono, 2026-09-06): roda o circuito COMPLETO
(campanha.py, periodo longo default de 3 anos, protegido pelo gate novo de
holdout longo + WFA) nos 8 sistemas que a triagem rapida achou sinal, cada
um no ativo ja mapeado como compativel (PLANO_DIVISAO_TESTES_FORMULAS.md),
sequencial -- MT5 so roda uma campanha por vez com seguranca.
"""
import subprocess
import sys

SISTEMAS = [
    ("01_SLTP", "EURUSD", 1000),
    ("02_SLTP_ORGANIC", "EURUSD", 1000),
    ("03_TRAIL_ONLY", "XAUUSD", 10000),
    ("05_BE_TRAIL", "XAUUSD", 10000),
    ("06_REVERSAL_EXIT", "EURGBP", 1000),
    ("07_GRID_SEPARATE", "AUDNZD", 1000),
    ("09_MARTINGALE", "AUDNZD", 1000),
    ("12_GRID_INVERSO", "XAUUSD", 10000),
]

for sistema, simbolo, deposito in SISTEMAS:
    print(f"\n{'#'*70}\n# OFICIAL: {sistema} / {simbolo} (${deposito})\n{'#'*70}",
          flush=True)
    r = subprocess.run(
        [sys.executable, "campanha.py", "--sistemas", sistema,
        "--simbolos", simbolo, "--deposit", str(deposito)],
        cwd=r"C:\Users\Lucas Pedroso\Documents\White Rabbit X\Autobot")
    print(f"# {sistema}/{simbolo}: campanha.py saiu com codigo {r.returncode}",
          flush=True)

print("\n\n=== FILA OFICIAL CONCLUIDA (8 sistemas) ===", flush=True)
