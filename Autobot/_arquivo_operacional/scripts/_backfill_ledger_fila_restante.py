# -*- coding: utf-8 -*-
"""Backfill do ledger pros 6 campeoes que a fila de calibracao restante
produziu (01_SLTP, 02_SLTP_ORGANIC, 06_REVERSAL_EXIT, 11_SIGNAL_ONLY,
04_SLTP_TRAIL, 09_MARTINGALE) -- todos rodaram via sweep_formulas.py ->
optimize_two_stage.py direto, sem passar por campanha.py, entao nao
gravaram ledger sozinhos. O log de origem de cada um foi identificado
por mtime mais proximo do VALIDADO_ real (mesmo metodo usado pro
conserto do AUDNZD/07_GRID_SEPARATE em 2026-08-31). Uso interno, apagar
depois."""
import datetime
import json
from pathlib import Path

import ready_library as rl

FONTES = {
    ("EURUSD", "01_SLTP", "BUY_MULTI"): "sweep_01_SLTP_EURUSD_14_SomaR.log",
    ("EURUSD", "02_SLTP_ORGANIC", "BUY_MULTI"): "sweep_02_SLTP_ORGANIC_EURUSD_10_ResilienceToDrawdown.log",
    ("EURGBP", "06_REVERSAL_EXIT", "BUY_MULTI"): "sweep_06_REVERSAL_EXIT_EURGBP_02_Profit.log",
    ("XAUUSD", "11_SIGNAL_ONLY", "BUY_MULTI"): "sweep_11_SIGNAL_ONLY_XAUUSD_07_ProfitPerTradeAdjustedByDD.log",
    ("BTCUSD", "04_SLTP_TRAIL", "BUY_MULTI"): "sweep_04_SLTP_TRAIL_BTCUSD_15_ZeusCompositeScore.log",
    ("NZDUSD", "09_MARTINGALE", "BUY_MULTI"): "sweep_09_MARTINGALE_NZDUSD_03_ProfitWinTradeDD.log",
    # Fila 2 (2026-09-03): mesmo problema de ledger obsoleto do
    # AUDNZD/07_GRID_SEPARATE -- essas duas chaves ja tinham registro
    # velho (pre-reset), entao o lookup simples do dict achava o antigo.
    ("XAUUSD", "05_BE_TRAIL", "BUY_MULTI"): "sweep_05_BE_TRAIL_XAUUSD_04_EfficiencyRelativeToDeposit.log",
    ("EURUSD", "10_DALEMBERT", "BUY_MULTI"): "sweep_10_DALEMBERT_EURUSD_11_ReturnUniformity.log",
}

gravados = 0
with rl.LEDGER.open("a", encoding="utf-8") as fh:
    for (simbolo, sistema, variante), nome_log in FONTES.items():
        log = Path(nome_log)
        texto = log.read_text(encoding="utf-8", errors="replace")
        registro = None
        for linha in reversed(texto.splitlines()):
            if linha.startswith("{"):
                registro = json.loads(linha)
                break
        if registro is None:
            print(f"[FALHOU] {simbolo}/{sistema}: sem JSON em {nome_log}")
            continue
        destino = rl.TESTER / f"VALIDADO_{simbolo}_{sistema}_{variante}.set"
        registro["aprovado"] = True
        registro["quando"] = datetime.datetime.fromtimestamp(
            destino.stat().st_mtime).isoformat()
        registro["origem_backfill"] = nome_log
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
        gravados += 1
        print(f"[OK] {simbolo}/{sistema}: aprovado={registro.get('aprovado')} "
              f"PF={registro.get('profit_factor')} DD%={registro.get('max_dd_pct')} "
              f"Sharpe={registro.get('sharpe')} Score={registro.get('composite_score')}")

print(f"\n{gravados}/{len(FONTES)} registros gravados em {rl.LEDGER}")
