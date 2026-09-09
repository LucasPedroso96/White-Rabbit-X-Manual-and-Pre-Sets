# -*- coding: utf-8 -*-
"""Roda em sequencia as partes 1, 2 e 3 do plano de divisao de testes de
formula (PLANO_DIVISAO_TESTES_FORMULAS.md), local, uma apos a outra --
nunca em paralelo, pra nao repetir a colisao de processo ja vista com
campanha.py duplicado. Uso interno, apagar depois."""
import subprocess
import sys

TAREFAS = [
    ("04_SLTP_TRAIL", "XAUUSD", 10000),
    ("05_BE_TRAIL", "XAUUSD", 10000),
    # 12_GRID_INVERSO adiantado pra logo depois da familia trend (XAUUSD):
    # o proprio PLANO_DIVISAO_TESTES_FORMULAS.md ja reconhece que ele e
    # regime-irmao do trail (piramide A FAVOR da tendencia), so ficava por
    # ultimo por causa da divisao original em 5 pessoas em paralelo -- numa
    # fila sequencial nao ha motivo pra isso. E o sistema mais exercitado
    # pelos 3 fixes de hoje (Pyramid+MaxRiscoTradeR), entao roda-lo cedo da
    # sinal rapido se os fixes seguram fora do trail (decisao do dono,
    # 2026-08-24).
    ("12_GRID_INVERSO", "XAUUSD", 10000),
    ("09_MARTINGALE", "AUDNZD", 1000),
    ("10_DALEMBERT", "AUDNZD", 1000),
    ("07_GRID_SEPARATE", "AUDNZD", 1000),
]

for sistema, simbolo, deposito in TAREFAS:
    print(f"\n########## INICIANDO {sistema} / {simbolo} ##########", flush=True)
    ret = subprocess.run(
        [sys.executable, "sweep_formulas.py",
         "--sistema", sistema, "--simbolo", simbolo,
         "--deposit", str(deposito)])
    print(f"########## FIM {sistema} / {simbolo} (returncode={ret.returncode}) ##########",
          flush=True)

print("\n########## TODAS AS PARTES 1-3 CONCLUIDAS ##########", flush=True)
