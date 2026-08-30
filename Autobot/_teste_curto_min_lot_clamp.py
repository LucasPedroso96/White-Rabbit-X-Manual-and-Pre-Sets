# -*- coding: utf-8 -*-
"""Teste curto (passe unico, nao otimizacao) pra verificar o fix de
NormalizeRiskVolume (2026-08-24): lote ideal abaixo do minimo do broker
agora deve ABRIR no minimo em vez de abortar a ordem.

03_TRAIL_ONLY/XAUUSD, timeframe H4 (ATR(14) real ~$39, Stop/Trail forcado
no maximo do range=7 -> distancia ~$277, bem acima do orcamento de 1R=$100
com CapitalBaseR=10000), 3 meses, AtivarWFO=false. Uso interno, apagar
depois."""
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre, lancar_terminal

garantir_terminal_livre(fechar=True)

origem = base.achar_set("XAUUSD", "03_TRAIL_ONLY", "BUY_MULTI")
texto = origem.read_text(encoding="utf-16")

# Forca Stop=Trail=7 (topo do range, o cenario mais largo possivel) pra
# garantir estourar o orcamento de 1R no timeframe testado.
texto = re.sub(r"Stop=[\d.]+\|\|[\d.]+\|\|[\d.]+\|\|[\d.]+\|\|[YN]",
              "Stop=7||7||0.5||7||N", texto)
texto = re.sub(r"Trail=[\d.]+\|\|[\d.]+\|\|[\d.]+\|\|[\d.]+\|\|[YN]",
              "Trail=7||7||0.5||7||N", texto)
texto = re.sub(r"AtivarWFO=true\|\|true\|\|0\|\|true\|\|N",
              "AtivarWFO=false||false||0||false||N", texto)

TESTER_DIR = base.DADOS / "MQL5" / "Profiles" / "Tester"
trabalho = TESTER_DIR / "_teste_min_lot_clamp.set"
trabalho.write_text(texto, encoding="utf-16")
rel = str(trabalho.relative_to(TESTER_DIR)).replace("/", "\\")

with tempfile.TemporaryDirectory() as tmp:
    ini = Path(tmp) / "conf.ini"
    base.escrever_ini(ini, "XAUUSD", "H4", rel, "2026.05.24", "2026.08.24",
                      10000, 4, 6, "teste_min_lot_clamp")
    texto_ini = ini.read_text(encoding="utf-16")
    texto_ini = texto_ini.replace("Optimization=2", "Optimization=0")
    ini.write_text(texto_ini, encoding="utf-16")

    antes = base.marcar_logs()
    lancar_terminal(base.TERMINAL, ini, 1800)

limite = time.monotonic() + 90
log = ""
while time.monotonic() < limite:
    log = base.texto_novo(antes)
    if ots.TESTE_CONCLUIDO.search(log):
        break
    time.sleep(1)

Path("teste_min_lot_clamp_log_bruto.txt").write_text(log, encoding="utf-8")
print("===== METRICAS =====")
print(ots.ler_metricas(log))
print("\n===== ABORTOS / TRADES =====")
aborto_count = log.count("order aborted to preserve the configured R risk")
print(f"Abortos 'order aborted to preserve the configured R risk': {aborto_count}")
for linha in log.splitlines():
    if any(k in linha for k in ("MM_Size_R:", "order aborted", "Total R",
                                "R medio", "Expectanc", "Total Trades",
                                "buy 0.01", "sell 0.01", "buy 0.0", "sell 0.0")):
        print(linha)
print(f"\nlog bruto salvo em teste_min_lot_clamp_log_bruto.txt ({len(log)} chars)")
