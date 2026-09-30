"""Exporta do MT5 (via pacote `MetaTrader5`) o que o motor precisa: spec do simbolo, ticks e M1.

  py tools/export_mt5_data.py --symbol EURUSD --from 2026-01-05 --to 2026-03-01 --out dados/eurusd
      [--warmup-days 10] [--commission-per-lot-side 3.5]

Gera  <out>_spec.json | <out>_ticks.csv | <out>_m1_warmup.csv  (formatos que `python -m wrx_engine.parity` le).

NAO TESTADO neste repositorio: precisa de um terminal MT5 no Windows com o simbolo ativo.
Roda no MESMO terminal/conta do Tester -- spec, ticks e tick value tem que ser os mesmos.
As datas do servidor NAO sao convertidas: a API devolve o horario do servidor como se fosse UTC,
que e o relogio que o EA enxerga em TimeCurrent().
Comissao nao vem do SymbolInfo: informe --commission-per-lot-side (moeda da conta, por lado).
Margem: ajuste linear por lote (margin_a*preco + margin_b) a partir de order_calc_margin em dois precos; so e USADA
pelo motor se margin_a/margin_b != 0 (senao o motor nao modela margem). Swap: so modo em pontos (SYMBOL_SWAP_MODE_POINTS);
outros modos geram aviso e swap 0. Confira tambem o STAT_MIN_MARGINLEVEL no relatorio.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    import MetaTrader5 as mt5
    import pandas as pd

    from wrx_engine.spec import SymbolSpec

    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--warmup-days", type=int, default=10)
    ap.add_argument("--commission-per-lot-side", type=float, default=0.0)
    a = ap.parse_args()

    if not mt5.initialize():
        print("MT5 nao inicializou:", mt5.last_error())
        return 2
    try:
        if not mt5.symbol_select(a.symbol, True):
            print("simbolo indisponivel:", a.symbol)
            return 2
        i = mt5.symbol_info(a.symbol)
        tk = mt5.symbol_info_tick(a.symbol)
        mid = (tk.bid + tk.ask) / 2 if tk and tk.bid > 0 else 0.0
        margin_a = margin_b = 0.0
        if mid > 0:
            m1 = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, a.symbol, 1.0, mid)
            m2 = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, a.symbol, 1.0, mid * 1.1)
            if m1 and m2:
                margin_a = (m2 - m1) / (mid * 0.1)
                margin_b = m1 - margin_a * mid
        swap_long = swap_short = 0.0
        if i.swap_mode == mt5.SYMBOL_SWAP_MODE_POINTS:
            swap_long, swap_short = i.swap_long, i.swap_short
        else:
            print("AVISO: swap_mode", i.swap_mode, "nao e 'pontos': swap sera 0 no motor (compare o Swap do relatorio)")
        SymbolSpec(symbol=a.symbol, digits=i.digits, point=i.point,
                   tick_size=i.trade_tick_size, tick_value=i.trade_tick_value,
                   volume_min=i.volume_min, volume_max=i.volume_max, volume_step=i.volume_step,
                   stops_level=i.trade_stops_level, freeze_level=i.trade_freeze_level,
                   commission_per_lot_side=a.commission_per_lot_side, margin_a=margin_a, margin_b=margin_b,
                   swap_long=swap_long, swap_short=swap_short, swap_3days=i.swap_rollover3days).to_json(f"{a.out}_spec.json")
        t0 = datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc)
        t1 = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
        ticks = mt5.copy_ticks_range(a.symbol, t0, t1, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            print("sem ticks no periodo:", mt5.last_error())
            return 2
        df = pd.DataFrame(ticks)[["time_msc", "bid", "ask"]]
        df = df[(df.bid > 0) & (df.ask > 0)]
        df.to_csv(f"{a.out}_ticks.csv", index=False)
        rates = mt5.copy_rates_range(a.symbol, mt5.TIMEFRAME_M1, t0 - timedelta(days=a.warmup_days), t0)
        if rates is not None and len(rates):
            pd.DataFrame(rates)[["time", "open", "high", "low", "close"]].to_csv(f"{a.out}_m1_warmup.csv", index=False)
        print(f"ok: {len(df)} ticks, spec e warmup em {a.out}_*")
        print("margem/lote ajustada: a=%.4f b=%.4f (preco de referencia %.5f)" % (margin_a, margin_b, mid))
        print("tick_value atual:", i.trade_tick_value, "(em cruzados/indices ele varia no tempo no Tester)")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
