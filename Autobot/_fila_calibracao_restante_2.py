# -*- coding: utf-8 -*-
"""Segunda fila -- os 3 sistemas que ficaram de fora tanto da primeira
fila quanto da distribuicao pros amigos: 05_BE_TRAIL, 10_DALEMBERT,
12_GRID_INVERSO. Pedido do dono (2026-09-02): "vai ficar tudo pra esse
pc! rode agora" -- roda os 3 aqui mesmo, sequencial, mesmo padrao de
_fila_calibracao_restante.py.

Ativos:
    05_BE_TRAIL    XAUUSD  10000  ativo original do PLANO_DIVISAO (irmao
                                  do 03_TRAIL_ONLY, mesmo regime)
    10_DALEMBERT   EURUSD  1000   AUDNZD (ativo original do plano) ja
                                  reprovou antes; EURUSD teve campeao
                                  real ate ontem ser zerado -- territorio
                                  ja provado viavel, tenta de novo do zero
    12_GRID_INVERSO XAUUSD 10000  ativo original -- o mesmo que levou a
                                  maratona de 3 dias na calibracao anterior

Uso:
    python _fila_calibracao_restante_2.py
    python _fila_calibracao_restante_2.py --a-partir-de 12_GRID_INVERSO
"""
import argparse
import subprocess
import sys
from pathlib import Path

FILA = [
    ("05_BE_TRAIL", "XAUUSD", 10000),
    ("10_DALEMBERT", "EURUSD", 1000),
    ("12_GRID_INVERSO", "XAUUSD", 10000),
]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--a-partir-de", default=None,
                     help="nome do sistema pra retomar a fila a partir dele")
args = parser.parse_args()

fila = FILA
if args.a_partir_de:
    nomes = [s for s, _, _ in FILA]
    idx = nomes.index(args.a_partir_de)
    fila = FILA[idx:]

master = Path("_fila_calibracao_restante_2_master.log")
with master.open("a", encoding="utf-8") as fm:
    for sistema, simbolo, deposito in fila:
        titulo = f"===== FILA 2: {sistema} / {simbolo} (deposito {deposito}) ====="
        print(f"\n{titulo}", flush=True)
        fm.write(f"\n{titulo}\n")
        fm.flush()

        log = Path(f"_fila2_{sistema}_{simbolo}.log")
        with log.open("w", encoding="utf-8") as fh:
            resultado = subprocess.run(
                [sys.executable, "sweep_formulas.py",
                 "--sistema", sistema, "--simbolo", simbolo,
                 "--deposit", str(deposito)],
                stdout=fh, stderr=subprocess.STDOUT)
        linha = f"    log salvo em {log} (exit={resultado.returncode})"
        print(linha, flush=True)
        fm.write(linha + "\n")

print("\n===== FILA 2 COMPLETA =====", flush=True)
