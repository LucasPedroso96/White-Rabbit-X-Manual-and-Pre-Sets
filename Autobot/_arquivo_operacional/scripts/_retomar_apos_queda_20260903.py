# -*- coding: utf-8 -*-
"""Retoma a calibracao depois da queda de 2026-09-03 ~23:25 (processo do
driver da fila 2 sumiu sem traceback, provavel interferencia da recompilacao
da EA feita nesta mesma janela de horario -- ver auditoria).

O que ja tinha sido feito NAO e refeito: 12_GRID_INVERSO/XAUUSD ja tem as
formulas 1-13 completas (13 = LevainCompositeScore, aprovada, e o campeao
VALIDADO_ atual). So faltam as formulas 14 (SomaR) e 15 (ZeusCompositeScore)
-- rodar sweep_formulas.py --formulas 14,15 em vez de recomecar do 1 evita
redigitar ~6h de trabalho ja concluido e ja auditado.

Decisao do dono (2026-09-03, apos a queda): mesma janela de 92 dias (agora
com o fix de dimensionar_wfo(), 3 ciclos em vez de 1,5) e --indicador-solo
continua DESLIGADO -- nao mistura o novo Estagio 1.5 no meio de um sweep que
ja tem 13/15 formulas medidas sem ele.

Depois de fechar o 12_GRID_INVERSO, escreve o marcador "FILA 2 COMPLETA" no
master log da fila 2 -- mesmo texto que _fila_calibracao_restante_2.py
escreveria no fim normal dela -- e entao roda a fila 3 (03_TRAIL_ONLY e
07_GRID_SEPARATE) direto, sem esperar 300s em loop atras de um marcador que
este proprio script acabou de escrever.

Uso:
    python _retomar_apos_queda_20260903.py
"""
import subprocess
import sys
from pathlib import Path

MASTER_FILA2 = Path("_fila_calibracao_restante_2_master.log")

with MASTER_FILA2.open("a", encoding="utf-8") as fm:
    titulo = "===== RETOMADA (queda 23:25): 12_GRID_INVERSO formulas 14-15 ====="
    print(f"\n{titulo}", flush=True)
    fm.write(f"\n{titulo}\n")
    fm.flush()

    log = Path("_fila2_12_GRID_INVERSO_XAUUSD_retomada.log")
    with log.open("w", encoding="utf-8") as fh:
        resultado = subprocess.run(
            [sys.executable, "sweep_formulas.py",
             "--sistema", "12_GRID_INVERSO", "--simbolo", "XAUUSD",
             "--deposit", "10000", "--formulas", "14,15"],
            stdout=fh, stderr=subprocess.STDOUT)
    linha = f"    log salvo em {log} (exit={resultado.returncode})"
    print(linha, flush=True)
    fm.write(linha + "\n")
    fm.write("\n===== FILA 2 COMPLETA =====\n")

print("\n===== FILA 2 COMPLETA (retomada) =====", flush=True)

# Fila 3 direto, sem o loop de espera de 300s: o marcador ja esta gravado.
subprocess.run([sys.executable, "_fila_calibracao_restante_3.py",
                "--sem-esperar"])
