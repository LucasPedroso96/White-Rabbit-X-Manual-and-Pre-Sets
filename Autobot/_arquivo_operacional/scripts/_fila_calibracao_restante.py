# -*- coding: utf-8 -*-
"""Fila sequencial dos sistemas que AINDA nao tem campeao nenhum (nunca
rodados ou reprovados nas tentativas anteriores) -- pedido do dono
(2026-08-31): "voce vai terminar de calibrar os outros sistemas inclusive
os reprovados com novos assets se preciso".

So um sweep de cada vez -- MT5 so aguenta um terminal WRX por vez sem
colidir (mesmo risco documentado em mt5_runner.py). Cada combo roda o
sweep completo das 15 formulas (sweep_formulas.py), sequencial, com o
proprio master log dele; este script so encadeia.

Ativos escolhidos:
    01_SLTP          EURUSD   1000   nunca tentado -- piso neutro (PLANO_DIVISAO)
    02_SLTP_ORGANIC  EURUSD   1000   nunca tentado -- mesma logica do 01_SLTP
    06_REVERSAL_EXIT EURGBP   1000   nunca tentado -- par que inverte com frequencia
    11_SIGNAL_ONLY   XAUUSD   10000  nunca tentado -- precisa de movimento real
    04_SLTP_TRAIL    BTCUSD   2500   XAUUSD ja reprovou (REPROVADO_XAUUSD_04_SLTP_TRAIL);
                                     ativo novo, mesma familia de tendencia
    09_MARTINGALE    NZDUSD   1000   AUDNZD e EURUSD ja reprovaram; ativo novo
                                     de reversao a media, ainda nao testado

Uso:
    python _fila_calibracao_restante.py
    python _fila_calibracao_restante.py --a-partir-de 04_SLTP_TRAIL  # retomar
"""
import argparse
import subprocess
import sys
from pathlib import Path

FILA = [
    ("01_SLTP", "EURUSD", 1000),
    ("02_SLTP_ORGANIC", "EURUSD", 1000),
    ("06_REVERSAL_EXIT", "EURGBP", 1000),
    ("11_SIGNAL_ONLY", "XAUUSD", 10000),
    ("04_SLTP_TRAIL", "BTCUSD", 2500),
    ("09_MARTINGALE", "NZDUSD", 1000),
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

master = Path("_fila_calibracao_restante_master.log")
with master.open("a", encoding="utf-8") as fm:
    for sistema, simbolo, deposito in fila:
        titulo = f"===== FILA: {sistema} / {simbolo} (deposito {deposito}) ====="
        print(f"\n{titulo}", flush=True)
        fm.write(f"\n{titulo}\n")
        fm.flush()

        log = Path(f"_fila_{sistema}_{simbolo}.log")
        with log.open("w", encoding="utf-8") as fh:
            resultado = subprocess.run(
                [sys.executable, "sweep_formulas.py",
                 "--sistema", sistema, "--simbolo", simbolo,
                 "--deposit", str(deposito)],
                stdout=fh, stderr=subprocess.STDOUT)
        linha = f"    log salvo em {log} (exit={resultado.returncode})"
        print(linha, flush=True)
        fm.write(linha + "\n")

print("\n===== FILA COMPLETA =====", flush=True)
