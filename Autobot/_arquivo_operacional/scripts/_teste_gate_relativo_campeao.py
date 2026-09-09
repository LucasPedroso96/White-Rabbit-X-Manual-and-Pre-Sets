# -*- coding: utf-8 -*-
"""Teste isolado (sem MT5) de carregar_campeao_atual() -- confirma que le
o VALIDADO_*.set real da raiz do Tester + o registro real no ledger, e que
devolve None quando o combo nao tem campeao. Uso interno, apagar depois."""
import optimize_two_stage as ots

print("=== combo com campeao conhecido (12_GRID_INVERSO/XAUUSD/BUY_MULTI) ===")
c = ots.carregar_campeao_atual("12_GRID_INVERSO", "XAUUSD", "BUY_MULTI")
print(c)

print("\n=== combo sem campeao (sistema/simbolo inventado) ===")
c2 = ots.carregar_campeao_atual("99_INEXISTENTE", "ZZZUSD", "BUY_MULTI")
print(c2)
assert c2 is None, "esperava None para combo sem VALIDADO_*.set"
print("\nOK: combo sem campeao devolveu None como esperado.")
