# -*- coding: utf-8 -*-
"""Re-roda o proprio campeao ATUAL (VALIDADO_XAUUSD_12_GRID_INVERSO_
BUY_MULTI.set, ja com WFO desligado) na MESMA janela de 1 ano da confirmacao
original, e aplica a MESMA condicao do gate relativo real (linha do
optimize_two_stage.py) contra o expectancy_r que o ledger backfilled guarda
pra esse campeao -- teste de verdade (MT5, tick real), nao so aritmetica
isolada. Uso interno, apagar depois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre

garantir_terminal_livre(fechar=True)

caminho_set = base.DADOS / "MQL5" / "Profiles" / "Tester" / "VALIDADO_XAUUSD_12_GRID_INVERSO_BUY_MULTI.set"
campeao = ots.carregar_campeao_atual("12_GRID_INVERSO", "XAUUSD", "BUY_MULTI")
expectancy_campeao = campeao.get("expectancy_r")
print(f"campeao no ledger: expectancy_r={expectancy_campeao}")

real = ots.passe_unico(caminho_set, "XAUUSD", "M1", "2025.08.25", "2026.08.25",
                       10000, modelo=4)
print(f"\nre-teste do proprio campeao (mesma janela): {real}")

expectancy_novo = real["expectancy"]
if expectancy_novo is None or expectancy_campeao is None:
    print("\nSEM DADO pra comparar.")
else:
    reprovado = expectancy_novo <= expectancy_campeao
    print(f"\ngate relativo: novo={expectancy_novo:+.3f}R vs "
          f"campeao={expectancy_campeao:+.3f}R -> "
          f"{'REPROVADO (nao supera)' if reprovado else 'APROVADO (supera)'}")
