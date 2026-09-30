"""Filtros de entrada avaliados em cada decisao (1o tick do minuto), vetorizados por barra M1.

Espelham CheckBuy/SellVolatility, CheckMTFAlignment, CheckMAFilter e CheckADXFilter. O resultado
`cond_buy/cond_sell[j]` e o `condEntradaATR_Buy/Sell` do ProcessNewBar. `ready[j]` e falso quando
algum CopyBuffer do ProcessNewBar falharia por falta de barras (o EA retorna sem fazer nada).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import indicators as ind
from .bars import MN1, Bars, resample, tf_index_of
from .setfile import WrxParams


@dataclass
class FilterArrays:
    ready: np.ndarray
    cond_buy: np.ndarray
    cond_sell: np.ndarray


def higher_timeframes(base_min: int) -> tuple[int, int]:
    """GetHigherTimeframes() -- minutos; MN1 = 43200."""
    if base_min <= 5:
        return 15, 60
    if base_min <= 30:
        return 60, 240
    if base_min == 60:
        return 240, 1440
    if base_min == 240:
        return 1440, 10080
    if base_min == 1440:
        return 10080, MN1
    if base_min == 10080:
        return MN1, MN1
    return MN1, MN1


def _map_bar(m1: Bars, tf_min: int) -> tuple[Bars, np.ndarray]:
    tf = resample(m1, tf_min)
    return tf, tf_index_of(m1, tf, tf_min)


def compute_filters(p: WrxParams, m1: Bars, first_bid: np.ndarray, atr_c: np.ndarray, atr0: np.ndarray,
                    ab: np.ndarray) -> FilterArrays:
    n = len(m1)
    ready = np.ones(n, bool)
    ok_b = np.ones(n, bool)
    ok_s = np.ones(n, bool)

    if p.use_vol:                                       # CheckBuy/SellVolatility
        N = p.period_baseline_atr
        atr1 = np.where(ab >= 1, atr_c[np.maximum(ab - 1, 0)], np.nan)
        if N > 1:
            roll = pd.Series(atr_c).rolling(N - 1, min_periods=N - 1).sum().to_numpy()
            tail = np.where(ab >= 1, roll[np.maximum(ab - 1, 0)], np.nan)
            base = (atr0 + tail) / N
        else:
            base = atr0.copy()
        with np.errstate(invalid="ignore"):
            if p.vol_high:
                v = (atr0 > base * p.vol_mult) & (atr1 > base * p.vol_mult)
            else:
                v = (atr0 < base / p.vol_mult) & (atr1 < base / p.vol_mult)
            # baseline invalido (<=0) => modo seguro: com o filtro LIGADO, bloqueia
            v = np.where(base <= 0.0, False, v)
        v = np.where(np.isnan(base), False, v)
        ok_b &= v
        ok_s &= v

    if p.use_mtf:                                       # CheckMTFAlignment (candle ABERTO do TF superior)
        from .bars import TF_MINUTES
        tf1, tf2 = higher_timeframes(TF_MINUTES[p.timeframe_idx])
        buy_ok, sell_ok = [], []
        for tfm in (tf1, tf2):
            tf, idx = _map_bar(m1, tfm)
            o = tf.open[idx]
            buy_ok.append(first_bid > o)
            sell_ok.append(first_bid < o)
        comb = np.logical_and if p.mtf_both else np.logical_or
        ok_b &= comb(buy_ok[0], buy_ok[1])
        ok_s &= comb(sell_ok[0], sell_ok[1])

    if p.use_ma:                                        # CheckMAFilter (barra fechada, shift 1)
        from .bars import TF_MINUTES
        tfm = TF_MINUTES[p.ma_tf_idx]
        tf, idx = _map_bar(m1, tfm)
        price = ind.applied_price(tf.open, tf.high, tf.low, tf.close, p.ma_applied_price)
        line = ind.ma(price, p.ma_period, p.ma_method)
        uses_slope = p.ma_rule in (1, 2, 3)
        need = min(50, max(2, 2 + max(0, p.ma_slope_lookback))) if uses_slope else 2
        ready &= (idx + 1) >= need
        L = p.ma_slope_lookback
        pr = np.where(idx >= 1, price[np.maximum(idx - 1, 0)], np.nan)
        m0 = np.where(idx >= 1, line[np.maximum(idx - 1, 0)], np.nan)
        mN = np.where(idx >= 1 + L, line[np.maximum(idx - 1 - L, 0)], np.nan)
        with np.errstate(invalid="ignore"):
            if not p.ma_reversal:
                pb, ps, sb_, ss = pr > m0, pr < m0, m0 > mN, m0 < mN
            else:
                pb, ps, sb_, ss = pr < m0, pr > m0, m0 < mN, m0 > mN
        if p.ma_rule == 0:
            fb, fs = pb, ps
        elif p.ma_rule == 1:
            fb, fs = sb_, ss
        elif p.ma_rule == 2:
            fb, fs = pb & sb_, ps & ss
        else:
            fb, fs = pb | sb_, ps | ss
        ok_b &= fb
        ok_s &= fs

    if p.use_adx:                                       # CheckADXFilter (barra fechada, shift 1)
        from .bars import TF_MINUTES
        tfm = TF_MINUTES[p.adx_tf_idx]
        tf, idx = _map_bar(m1, tfm)
        a, pdi, ndi = ind.adx(tf.high, tf.low, tf.close, p.adx_period)
        ready &= (idx + 1) >= 2
        prev = np.maximum(idx - 1, 0)
        with np.errstate(invalid="ignore"):
            strong = a[prev] >= p.adx_limit
            if p.adx_with_di:
                fb, fs = strong & (pdi[prev] > ndi[prev]), strong & (ndi[prev] > pdi[prev])
            else:
                fb = fs = strong
        ok_b &= fb & (idx >= 1)
        ok_s &= fs & (idx >= 1)

    return FilterArrays(ready, ok_b, ok_s)
