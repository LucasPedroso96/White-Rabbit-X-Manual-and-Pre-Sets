# -*- coding: utf-8 -*-
"""Paridade sintetica com o self-check do proprio gate.py do Zeus (numeros
inventados, so pra confirmar que avaliar_gate_relativo()/composite_score()
nao tem erro de sinal/formula antes de gastar tempo de MT5 de verdade).
Uso interno, apagar depois."""
import optimize_two_stage as ots

deposit = 10000.0
campeao = {
    "profit_factor": 1.3, "max_dd_pct": 10.0, "sharpe": 1.5,
    "composite_score": ots.composite_score(1000, deposit, 1.3, 10.0, 100),
}
desafiante_melhor = {
    "profit_factor": 1.4, "max_dd_pct": 9.0, "sharpe": 1.8,
    "composite_score": ots.composite_score(1500, deposit, 1.4, 9.0, 110),
    "trades": 110,
}
desafiante_pior = {
    "profit_factor": 1.1, "max_dd_pct": 20.0, "sharpe": 0.5,
    "composite_score": ots.composite_score(200, deposit, 1.1, 20.0, 40),
    "trades": 40,
}

print("campeao composite_score:", campeao["composite_score"])
print()
print("=== desafiante MELHOR em tudo (esperado: aprovado) ===")
ok, motivos = ots.avaliar_gate_relativo(campeao, desafiante_melhor)
for m in motivos:
    print(" ", m)
print("aprovado =", ok)
assert ok, "esperava aprovado para o desafiante melhor"

print()
print("=== desafiante PIOR em tudo (esperado: reprovado) ===")
ok, motivos = ots.avaliar_gate_relativo(campeao, desafiante_pior)
for m in motivos:
    print(" ", m)
print("aprovado =", ok)
assert not ok, "esperava reprovado para o desafiante pior"

print()
print("=== sem campeao (esperado: so o check de trades roda -- e o UNICO")
print("    absoluto, sem depender do campeao; os outros 4 saem, sem dado")
print("    do campeao pra comparar) ===")
ok, motivos = ots.avaliar_gate_relativo({}, desafiante_pior)
print("motivos:", motivos)
print("aprovado =", ok)
assert ok and motivos == ["OK: trades 40 >= 30"]

print("\nOK: os tres cenarios bateram com o esperado.")
