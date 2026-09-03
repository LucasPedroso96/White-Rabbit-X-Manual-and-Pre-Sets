# -*- coding: utf-8 -*-
"""Terceira fila -- 03_TRAIL_ONLY e 07_GRID_SEPARATE nos ativos ORIGINAIS
do PLANO_DIVISAO_TESTES_FORMULAS.md (XAUUSD e AUDNZD). Pedido do dono
(2026-09-03): o trabalho distribuido pros amigos (distribuir_amigos/,
outros ativos) fica como material exploratorio, sem a mesma supervisao
-- "a dos meus amigos nao vai ter [o percurso completo]! somos nos que
iremos fazer a calibracao completa!". Esta fila e a calibracao oficial
desses 2 sistemas, feita aqui com o mesmo processo/auditoria dos outros
9 ja calibrados.

So um sweep de cada vez, MESMO terminal MT5 que a fila 2 usa -- por
isso este script espera a fila 2 terminar de verdade (confere o
marcador "FILA 2 COMPLETA" no master dela) antes de comecar, evitando
dois processos disputando o mesmo terminal WRX.

Ativos:
    03_TRAIL_ONLY    XAUUSD  10000  ativo original do plano (persegue
                                    tendencia, precisa de ativo que tende)
    07_GRID_SEPARATE AUDNZD  1000   ativo original do plano (reversao a
                                    media, precisa de ativo sem tendencia
                                    sustentada)

Uso:
    python _fila_calibracao_restante_3.py
    python _fila_calibracao_restante_3.py --a-partir-de 07_GRID_SEPARATE
    python _fila_calibracao_restante_3.py --sem-esperar  # pula a espera da fila 2
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

FILA = [
    ("03_TRAIL_ONLY", "XAUUSD", 10000),
    ("07_GRID_SEPARATE", "AUDNZD", 1000),
]

MARCADOR_FILA2 = "FILA 2 COMPLETA"
LOG_FILA2 = Path("_fila_calibracao_restante_2_master.log")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--a-partir-de", default=None,
                     help="nome do sistema pra retomar a fila a partir dele")
parser.add_argument("--sem-esperar", action="store_true",
                     help="nao espera a fila 2 terminar antes de comecar")
args = parser.parse_args()

if not args.sem_esperar:
    print("aguardando a fila 2 (12_GRID_INVERSO) terminar antes de comecar...",
          flush=True)
    while True:
        texto = LOG_FILA2.read_text(encoding="utf-8", errors="replace") \
            if LOG_FILA2.exists() else ""
        if MARCADOR_FILA2 in texto:
            print("fila 2 terminou, comecando a fila 3.", flush=True)
            break
        time.sleep(300)

fila = FILA
if args.a_partir_de:
    nomes = [s for s, _, _ in FILA]
    idx = nomes.index(args.a_partir_de)
    fila = FILA[idx:]

master = Path("_fila_calibracao_restante_3_master.log")
with master.open("a", encoding="utf-8") as fm:
    for sistema, simbolo, deposito in fila:
        titulo = f"===== FILA 3: {sistema} / {simbolo} (deposito {deposito}) ====="
        print(f"\n{titulo}", flush=True)
        fm.write(f"\n{titulo}\n")
        fm.flush()

        log = Path(f"_fila3_{sistema}_{simbolo}.log")
        with log.open("w", encoding="utf-8") as fh:
            resultado = subprocess.run(
                [sys.executable, "sweep_formulas.py",
                 "--sistema", sistema, "--simbolo", simbolo,
                 "--deposit", str(deposito)],
                stdout=fh, stderr=subprocess.STDOUT)
        linha = f"    log salvo em {log} (exit={resultado.returncode})"
        print(linha, flush=True)
        fm.write(linha + "\n")

print("\n===== FILA 3 COMPLETA =====", flush=True)
