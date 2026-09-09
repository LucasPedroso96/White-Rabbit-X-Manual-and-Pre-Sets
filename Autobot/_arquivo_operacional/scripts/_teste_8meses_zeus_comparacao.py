# -*- coding: utf-8 -*-
"""Teste de 8 meses (2026.01.01 a 2026.08.28, MESMA janela que o proprio
codigo do Zeus usa de exemplo) do set VALIDADO (Percentage, juros
compostos de verdade) do 12_GRID_INVERSO/XAUUSD -- pra comparar de forma
justa contra o resultado que o dono viu no Zeus no mesmo periodo.
Uso interno, apagar depois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre

garantir_terminal_livre(fechar=True)

caminho_set = base.DADOS / "MQL5" / "Profiles" / "Tester" / "VALIDADO_XAUUSD_12_GRID_INVERSO_BUY_MULTI.set"
print(f"Set: {caminho_set}")

r = ots.passe_unico(caminho_set, "XAUUSD", "M1", "2026.01.01", "2026.08.28",
                    10000, modelo=4, timeout=1800)
print("\n===== RESULTADO (8 meses, Percentage, tick real) =====")
print(r)
