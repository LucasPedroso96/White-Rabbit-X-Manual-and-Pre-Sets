# -*- coding: utf-8 -*-
"""Teste curto (passe unico, nao otimizacao) pra verificar:
1. SomaR (formula 14) reporta numeros sensatos no log ("Relatorio em
   multiplos de R").
2. O fix do MaxRiscoTradeR nas pernas 2+ do Pyramid segura o risco --
   forca Multiplicador=1.4 (fora do range normal do Autobot [0.3,1.0],
   pernas CRESCEM em vez de encolher, exatamente o cenario que estourava
   o cap antes do fix de 2026-08-24).

12_GRID_INVERSO/XAUUSD, 3 meses (mesmo periodo curto usado nos sweeps de
formula), AtivarWFO=false (periodo inteiro, sem janela). Uso interno,
apagar depois."""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre, lancar_terminal

garantir_terminal_livre(fechar=True)

origem = base.achar_set("XAUUSD", "12_GRID_INVERSO", "BUY_MULTI")
texto = origem.read_text(encoding="utf-16")

# Forca Multiplicador=1.4 fixo (fora do [0.3,1.0] que o Autobot usa) --
# cada perna do pyramid fica MAIOR que a anterior, o cenario que so a
# perna 1 tinha cap antes do fix.
texto = re.sub(r"Multiplicador=[\d.]+\|\|[\d.]+\|\|[\d.]+\|\|[\d.]+\|\|[YN]",
              "Multiplicador=1.4||1.4||1||1.4||N", texto)
# Periodo inteiro, sem WFO -- quero ver o pyramid operar livre.
texto = re.sub(r"AtivarWFO=true\|\|true\|\|0\|\|true\|\|N",
              "AtivarWFO=false||false||0||false||N", texto)

TESTER_DIR = base.DADOS / "MQL5" / "Profiles" / "Tester"
trabalho = TESTER_DIR / "_teste_somar_multiplo.set"
trabalho.write_text(texto, encoding="utf-16")
rel = str(trabalho.relative_to(TESTER_DIR)).replace("/", "\\")

with tempfile.TemporaryDirectory() as tmp:
    ini = Path(tmp) / "conf.ini"
    base.escrever_ini(ini, "XAUUSD", "M1", rel, "2026.05.24", "2026.08.24",
                      10000, 4, 6, "teste_somar_multiplo")
    texto_ini = ini.read_text(encoding="utf-16")
    texto_ini = texto_ini.replace("Optimization=2", "Optimization=0")
    ini.write_text(texto_ini, encoding="utf-16")

    antes = base.marcar_logs()
    lancar_terminal(base.TERMINAL, ini, 1800)

import time
limite = time.monotonic() + 90
log = ""
while time.monotonic() < limite:
    log = base.texto_novo(antes)
    if ots.TESTE_CONCLUIDO.search(log):
        break
    time.sleep(1)

Path("teste_somar_multiplo_log_bruto.txt").write_text(log, encoding="utf-8")
print("===== METRICAS =====")
print(ots.ler_metricas(log))
print("\n===== TRECHO R/SomaR =====")
for linha in log.splitlines():
    if any(k in linha for k in ("SomaR", "multiplos de R", "R medio", "Payoff",
                                "ALL_FORMULAS", "Total R", "Expectanc")):
        print(linha)
print(f"\nlog bruto salvo em teste_somar_multiplo_log_bruto.txt ({len(log)} chars)")
