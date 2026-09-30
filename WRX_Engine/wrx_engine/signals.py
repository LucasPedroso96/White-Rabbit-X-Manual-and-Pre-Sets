"""Sinal de entrada dos 12 indicadores -- espelho de CreateEntryIndicatorHandles, CopyEntryBuffers,
Is{Buy,Sell}Entry{Reversal,Cross,BaselineCross} e Has{Buy,Sell}RawIndicatorSignal.

Todas as series sao indexadas pela barra do TimeFrame de entrada; `x[b]` e o valor para a barra
`b` "em formacao", entao o EA le `main[1], main[2], main[3]` como `main_shift(k) = a[b-k]`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import indicators as ind
from .bars import Bars
from .setfile import WrxParams

(MACD, EMA_CROSS, MOMENTUM, STOCHASTIC, TRIX, RSI, CCI, WPR, DEMARKER, MFI, OSMA, ICHIMOKU) = range(12)
INDICATOR_NAMES = ["MACD", "EMA_Cross", "Momentum", "Stochastic", "TRIX", "RSI", "CCI",
                   "WPR", "DeMarker", "MFI", "OsMA", "Ichimoku"]


def neutral_level(entry_indicator: int) -> float:
    """EntryNeutralLevel()."""
    if entry_indicator in (STOCHASTIC, RSI, MFI):
        return 50.0
    if entry_indicator == MOMENTUM:
        return 100.0
    if entry_indicator == WPR:
        return -50.0
    if entry_indicator == DEMARKER:
        return 0.5
    return 0.0


@dataclass
class EntrySeries:
    main: np.ndarray
    signal: np.ndarray
    close: np.ndarray                 # Close[] do TF (sem applied price)
    span_a: np.ndarray | None = None  # Ichimoku SEM deslocamento
    span_b: np.ndarray | None = None


def build_entry_series(p: WrxParams, tf: Bars, tick_volume: np.ndarray | None) -> EntrySeries:
    price = ind.applied_price(tf.open, tf.high, tf.low, tf.close, p.applied_price)
    e, fast, slow, sig_n = p.entry_indicator, p.fast, p.slow, p.signal
    span_a = span_b = None
    if e == MACD:
        main, signal = ind.macd(price, fast, slow, sig_n)
    elif e == EMA_CROSS:
        main, signal = ind.ema(price, fast), ind.ema(price, slow)
    elif e == STOCHASTIC:
        main, signal = ind.stochastic(tf.high, tf.low, tf.close, fast, sig_n, p.stoch_slowing,
                                      p.stoch_method, p.stoch_price_field == 0)
    elif e == ICHIMOKU:
        main, signal, span_a, span_b = ind.ichimoku(tf.high, tf.low, fast, slow, sig_n)
    else:
        if e == MOMENTUM:
            main = ind.momentum(price, fast)
        elif e == TRIX:
            main = ind.trix(price, fast)
        elif e == RSI:
            main = ind.rsi(price, fast)
        elif e == CCI:
            main = ind.cci(price, fast)
        elif e == WPR:
            main = ind.wpr(tf.high, tf.low, tf.close, fast)
        elif e == DEMARKER:
            main = ind.demarker(tf.high, tf.low, fast)
        elif e == MFI:
            if tick_volume is None:
                raise ValueError("MFI usa volume de ticks: passe tick_volume")
            main = ind.mfi(tf.high, tf.low, tf.close, tick_volume, fast)
        elif e == OSMA:
            main = ind.osma(price, fast, slow, sig_n)
        else:
            raise ValueError(f"EntryIndicator invalido: {e}")
        signal = ind.ema_from_first_valid(main, sig_n)      # iMA(EMA, handle) sobre o buffer 0
    return EntrySeries(main, signal, np.asarray(tf.close, float), span_a, span_b)


def _shift(a: np.ndarray, k: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    if len(a) > k:
        out[k:] = a[:-k]
    return out


def _cloud(es: EntrySeries, kijun: int, k: int):
    """(topo, fundo) da nuvem sobre a barra de shift k: valor calculado em (b - k - kijun); False se ausente/zero."""
    a, b = _shift(es.span_a, k + kijun), _shift(es.span_b, k + kijun)
    return np.fmax(a, b), np.fmin(a, b)


def raw_triggers(p: WrxParams, es: EntrySeries):
    """(rev_b, rev_s, sig_b, sig_s, ref_b, ref_s) por barra formando."""
    m1, m2, m3 = _shift(es.main, 1), _shift(es.main, 2), _shift(es.main, 3)
    s1, s2 = _shift(es.signal, 1), _shift(es.signal, 2)
    c1, c2 = _shift(es.close, 1), _shift(es.close, 2)
    with np.errstate(invalid="ignore"):
        rev_b, rev_s = (m1 > m2) & (m2 < m3), (m1 < m2) & (m2 > m3)
        sig_b, sig_s = (m1 > s1) & (m2 < s2), (m1 < s1) & (m2 > s2)
        e = p.entry_indicator
        if e == ICHIMOKU and p.ichimoku_use_kumo:
            top1, bot1 = _cloud(es, p.slow, 1)
            top2, bot2 = _cloud(es, p.slow, 2)
            ok = ~(np.isnan(top1) | np.isnan(top2))
            ref_b = ok & (c1 > top1) & (c2 <= top2)
            ref_s = ok & (c1 < bot1) & (c2 >= bot2)
        elif e in (EMA_CROSS, ICHIMOKU):
            ref_b, ref_s = (c1 > s1) & (c2 < s2), (c1 < s1) & (c2 > s2)
        else:
            lv = neutral_level(e)
            ref_b, ref_s = (m1 > lv) & (m2 < lv), (m1 < lv) & (m2 > lv)
        if e == ICHIMOKU and p.ichimoku_chikou:
            past = p.slow + 1
            chb, chs = _shift(es.close, past), None
            conf_b = ~(np.isnan(chb)) & (c1 > chb) | np.isnan(chb)      # sem historico: nao bloqueia
            conf_s = ~(np.isnan(chb)) & (c1 < chb) | np.isnan(chb)
            rev_b, sig_b, ref_b = rev_b & conf_b, sig_b & conf_b, ref_b & conf_b
            rev_s, sig_s, ref_s = rev_s & conf_s, sig_s & conf_s, ref_s & conf_s
    return rev_b, rev_s, sig_b, sig_s, ref_b, ref_s


def combine(method: int, rev, sg, ref):
    """ENUM_ENTRY_TRIGGER_MODE."""
    return {0: rev, 1: sg, 2: ref, 3: rev & sg, 4: rev & ref, 5: sg & ref, 6: rev | sg | ref}[method]


def raw_signals(p: WrxParams, tf: Bars, tick_volume: np.ndarray | None = None):
    es = build_entry_series(p, tf, tick_volume)
    rb, rs, sb_, ss, fb, fs = raw_triggers(p, es)
    return combine(p.entry_method, rb, sb_, fb), combine(p.entry_method, rs, ss, fs)



# ------------------------------------------------------------------ familia Bollinger (EA "Global - Bolinger Bands")
@dataclass
class BollingerArrays:
    """Series por barra FORMANDO b: valores das barras fechadas de shift 1/2 usados pelas saidas alternativas."""
    main1: np.ndarray
    up1: np.ndarray
    up2: np.ndarray
    lo1: np.ndarray
    lo2: np.ndarray
    c1: np.ndarray
    c2: np.ndarray
    o1: np.ndarray


def bollinger_signals(p: WrxParams, tf: Bars):
    """(buy_raw, sell_raw, BollingerArrays) por barra formando. Reversao / Rompimento / Squeeze."""
    v = p.v
    price = ind.applied_price(tf.open, tf.high, tf.low, tf.close, p.applied_price)
    main, up, lo = ind.bands(price, v["BandsPeriod"], v["BandsDeviation"])
    c, o = np.asarray(tf.close, float), np.asarray(tf.open, float)
    m1, u1, u2, l1, l2 = _shift(main, 1), _shift(up, 1), _shift(up, 2), _shift(lo, 1), _shift(lo, 2)
    c1, c2, o1 = _shift(c, 1), _shift(c, 2), _shift(o, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rev_b = (c1 > l1) & (c2 <= l2) & (c1 > o1) & (c1 < m1)
        rev_s = (c1 < u1) & (c2 >= u2) & (c1 < o1) & (c1 > m1)
        brk_b = (c1 > u1) & (c2 <= u2)
        brk_s = (c1 < l1) & (c2 >= l2)
        width = np.where(main != 0.0, (up - lo) / main, 0.0)
        width[np.isnan(main)] = np.nan
        limit = min(v["SqueezeLookback"] + 2, 49)                       # ArraySize(Bands_Upper)-1 com CopyBars=50
        w_span = max(limit - 1, 1)                                      # shifts 2..limit
        roll_min = pd.Series(width).rolling(w_span, min_periods=w_span).min().to_numpy()
        w2, min2 = _shift(width, 2), _shift(roll_min, 2)
        active = w2 <= min2 * (1.0 + v["SqueezeTolerancePct"] / 100.0)
        sqz_b, sqz_s = active & brk_b, active & brk_s
    mode = v["BollingerEntryMode"]
    buy = {0: rev_b, 1: brk_b, 2: sqz_b}[mode]
    sell = {0: rev_s, 1: brk_s, 2: sqz_s}[mode]
    return buy, sell, BollingerArrays(m1, u1, u2, l1, l2, c1, c2, o1)


# ------------------------------------------------------------------ familia Candles (EA "Candles Entry")
def candles_signals(p: WrxParams, m1: Bars, first_bid: np.ndarray):
    """(buy_j, sell_j) POR BARRA M1: 3 slots (TF, indice), todos com applied price x open no mesmo sentido.

    Indice >= 1: barra fechada; indice 0: barra em formacao (parcial no 1o tick do minuto)."""
    from .bars import forming_partial, resample, tf_index_of, TF_MINUTES
    v = p.v
    n = len(m1)
    buy = np.ones(n, bool)
    sell = np.ones(n, bool)
    for k in (1, 2, 3):
        tfm = TF_MINUTES[v[f"CandleTF{k}"]]
        idx = int(v[f"CandleIndex{k}"])
        tf = resample(m1, tfm)
        t = tf_index_of(m1, tf, tfm)
        if idx >= 1:
            ref = t - idx
            ok = ref >= 0
            r = np.maximum(ref, 0)
            price = ind.applied_price(tf.open, tf.high, tf.low, tf.close, p.applied_price)[r]
            opn = tf.open[r]
        else:
            hi, lo, cl = forming_partial(m1, tfm, first_bid)
            ok = np.ones(n, bool)
            opn = tf.open[t]
            mode = p.applied_price
            price = {7: (hi + lo + 2 * cl) / 4.0, 6: (hi + lo + cl) / 3.0, 5: (hi + lo) / 2.0}.get(mode, cl)
        with np.errstate(invalid="ignore"):
            buy &= ok & (price > opn)
            sell &= ok & (price < opn)
    return buy, sell
