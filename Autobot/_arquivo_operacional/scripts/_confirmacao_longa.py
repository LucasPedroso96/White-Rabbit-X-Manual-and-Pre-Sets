# -*- coding: utf-8 -*-
"""Estagio 3 da cadeia de recalibracao (24-25/08/2026): depois que a
triagem curta (3 meses, 14 formulas) de cada sistema termina, confirma so
as formulas APROVADAS numa janela de 1 ano -- 15 dias de OOS da triagem
curta e pouco pra confiar sozinho, um periodo de sorte/azar vira o
veredito. Nao substitui a triagem (mantem WFO, so alarga a janela), so
confirma os vencedores antes de qualquer mudanca em FORMULA_POR_SISTEMA.
Disparado pelo watcher que espera a triagem+trail terminarem. Uso interno,
apagar depois."""
import glob
import re
import subprocess
import sys
from pathlib import Path

TAREFAS = [
    ("04_SLTP_TRAIL", "XAUUSD", 10000),
    ("05_BE_TRAIL", "XAUUSD", 10000),
    ("12_GRID_INVERSO", "XAUUSD", 10000),
    ("09_MARTINGALE", "AUDNZD", 1000),
    ("10_DALEMBERT", "AUDNZD", 1000),
    ("07_GRID_SEPARATE", "AUDNZD", 1000),
    ("03_TRAIL_ONLY", "XAUUSD", 10000),
]

DE = "2025.08.25"
ATE = "2026.08.25"


def formulas_aprovadas(sistema: str, simbolo: str) -> list[int]:
    aprovadas = []
    padrao = f"sweep_{sistema}_{simbolo}_*.log"
    for caminho in sorted(glob.glob(padrao)):
        if "master" in caminho:
            continue
        m = re.search(r"_(\d{2})_[A-Za-z]+\.log$", caminho)
        if not m:
            continue
        formula = int(m.group(1))
        texto = Path(caminho).read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^\s*APROVADO", texto, re.MULTILINE):
            aprovadas.append(formula)
    return aprovadas


for sistema, simbolo, deposito in TAREFAS:
    aprovadas = formulas_aprovadas(sistema, simbolo)
    if not aprovadas:
        print(f"\n########## {sistema}/{simbolo}: nenhuma formula aprovada na "
              "triagem curta, pulando confirmacao longa ##########", flush=True)
        continue
    lista = ",".join(str(f) for f in aprovadas)
    print(f"\n########## CONFIRMACAO LONGA (1 ano) {sistema}/{simbolo}: "
          f"formulas {lista} ##########", flush=True)
    log = Path(f"confirmacao_longa_{sistema}_{simbolo}_master.log")
    with log.open("w", encoding="utf-8") as fh:
        ret = subprocess.run(
            [sys.executable, "sweep_formulas.py",
             "--sistema", sistema, "--simbolo", simbolo,
             "--deposit", str(deposito), "--formulas", lista,
             "--from-data", DE, "--to-data", ATE],
            stdout=fh, stderr=subprocess.STDOUT)
    print(f"########## FIM confirmacao {sistema}/{simbolo} "
          f"(returncode={ret.returncode}) ##########", flush=True)

print("\n########## CONFIRMACAO LONGA COMPLETA (todos os sistemas) ##########",
      flush=True)
