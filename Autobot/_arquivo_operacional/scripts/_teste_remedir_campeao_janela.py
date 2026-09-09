# -*- coding: utf-8 -*-
"""Testa remedir_campeao_na_janela() com dado real -- confirma que
reproduz os MESMOS numeros ja medidos hoje pra formula 13 do
12_GRID_INVERSO/XAUUSD (expectancy_r=0.577, PF=2.7097, DD=9.88475,
sharpe=6.019977, score=201.057), ja que usa a mesma janela e os mesmos
parametros travados -- backtest deterministico, mesmo resultado esperado.
Uso interno, apagar depois."""
from mt5_runner import garantir_terminal_livre
import optimize_two_stage as ots

garantir_terminal_livre(fechar=True)

campeao_fresco = ots.remedir_campeao_na_janela(
    "12_GRID_INVERSO", "XAUUSD", "BUY_MULTI",
    "2025.08.25", "2026.08.25", 10000, "M1")

print("campeao re-medido na janela:", campeao_fresco)

esperado = {"profit_factor": 2.7097090567591446, "max_dd_pct": 9.88475,
           "sharpe": 6.019977, "composite_score": 201.05728836227578}
print("\nesperado (medido antes, mesma janela/parametros):", esperado)

for chave, valor_esperado in esperado.items():
    valor_real = campeao_fresco.get(chave)
    bate = valor_real is not None and abs(valor_real - valor_esperado) < 1e-4
    print(f"  {chave}: {valor_real} vs {valor_esperado} -> "
          f"{'OK' if bate else 'DIVERGIU'}")
