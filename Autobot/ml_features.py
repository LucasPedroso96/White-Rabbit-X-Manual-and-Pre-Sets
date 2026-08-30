# -*- coding: utf-8 -*-
"""13 features do piloto de ML, PORTE LITERAL do features.py do Zeus (ver
plano 2026-08-30) -- mesmas formulas, mesma ordem, mesmas convencoes:

  - ATR e RSI usam suavizacao Wilder/RMA (seed = media simples dos
    primeiros `period` valores, depois recursao x[t] = x[t-1] +
    (raw[t]-x[t-1])/period) -- e o que iATR/iRSI do MetaTrader fazem por
    dentro; uma media movel simples dessincronizaria este calculo do que
    a EA vai calcular ao vivo em WhiteRabbitMLFeatures.mqh.
  - Todo desvio-padrao usa ddof=0 (populacional, convencao de indicador do
    MetaTrader) -- pandas usa ddof=1 por padrao, nunca confiar nisso.
  - EMA (MACD e tendencia H1) e semeada pelo primeiro valor
    (ewm(adjust=False)), nao por SMA-seeded EMA como o iMA do MetaTrader --
    aproximacao reconhecida (mesma do Zeus): a convergencia exponencial e
    rapida o bastante pra divergencia ficar desprezivel com milhares de
    barras de warm-up.

Precisa bater 1:1 com WhiteRabbitMLFeatures.mqh (a EA calcula estas MESMAS
features ao vivo) -- qualquer mudanca aqui tem que ser espelhada la.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-10

RET_WINDOWS = (1, 4, 16)
ATR_PERIOD = 14
ATR_MOM_WINDOW = 8
RSI_PERIOD = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
MACD_SLOPE_LAG = 3
BB_PERIOD, BB_STD = 20, 2.0
REALIZED_VOL_WINDOW = 20
MA_ZSCORE_WINDOW = 50
HTF_EMA_FAST, HTF_EMA_SLOW = 20, 50
HTF_TREND_CLIP = 3.0

FEATURE_NAMES = (
    "ret_1", "ret_4", "ret_16", "atr_mom_8", "rsi_14",
    "macd_hist_norm", "macd_hist_slope", "bb_pctb", "realized_vol_20",
    "z_price_ma50", "htf_trend_align", "hour_sin", "hour_cos",
)
N_FEATURES = len(FEATURE_NAMES)
assert N_FEATURES == 13


def wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = ATR_PERIOD) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    atr = pd.Series(np.nan, index=close.index)
    if len(tr) <= period:
        return atr
    seed = tr.iloc[1:period + 1].mean()
    atr.iloc[period] = seed
    valores = tr.to_numpy()
    saida = atr.to_numpy()
    for i in range(period + 1, len(saida)):
        saida[i] = saida[i - 1] + (valores[i] - saida[i - 1]) / period
    return pd.Series(saida, index=close.index)


def wilder_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    ganho = delta.clip(lower=0.0)
    perda = -delta.clip(upper=0.0)
    avg_ganho = pd.Series(np.nan, index=close.index)
    avg_perda = pd.Series(np.nan, index=close.index)
    if len(close) <= period:
        return pd.Series(np.nan, index=close.index)
    avg_ganho.iloc[period] = ganho.iloc[1:period + 1].mean()
    avg_perda.iloc[period] = perda.iloc[1:period + 1].mean()
    g, p = ganho.to_numpy(), perda.to_numpy()
    ag, ap = avg_ganho.to_numpy(), avg_perda.to_numpy()
    for i in range(period + 1, len(ag)):
        ag[i] = (ag[i - 1] * (period - 1) + g[i]) / period
        ap[i] = (ap[i - 1] * (period - 1) + p[i]) / period
    rs = ag / np.where(ap == 0, np.nan, ap)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = np.where(ap == 0, 100.0, rsi)
    return pd.Series(rsi, index=close.index)


def _htf_trend_align(h1: pd.DataFrame) -> pd.DataFrame:
    ema_fast = h1["close"].ewm(span=HTF_EMA_FAST, adjust=False).mean()
    ema_slow = h1["close"].ewm(span=HTF_EMA_SLOW, adjust=False).mean()
    atr_h1 = wilder_atr(h1["high"], h1["low"], h1["close"], period=ATR_PERIOD)
    raw = (ema_fast - ema_slow) / (atr_h1 + EPS)
    raw = raw.clip(-HTF_TREND_CLIP, HTF_TREND_CLIP)
    return pd.DataFrame({
        "h1_close_time": h1["time"] + pd.Timedelta(hours=1),
        "htf_trend_align": raw,
    })


def compute_features(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    """Devolve um DataFrame com `time` + as 13 features, mesma ordem de
    FEATURE_NAMES. Linhas de warm-up saem com NaN (dropadas por quem
    monta o dataset de treino, nao aqui -- mesma divisao de trabalho do
    Zeus, quem descarta e train.py/load_dataset())."""
    close, high, low = m15["close"], m15["high"], m15["low"]

    ret_1 = np.log(close / close.shift(1))
    ret_4 = np.log(close / close.shift(4))
    ret_16 = np.log(close / close.shift(16))

    atr14 = wilder_atr(high, low, close, period=ATR_PERIOD)
    atr_mom_8 = (close - close.shift(ATR_MOM_WINDOW)) / (atr14 + EPS)

    rsi_14 = wilder_rsi(close, period=RSI_PERIOD)

    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    macd_hist_norm = (macd_line - macd_signal) / (atr14 + EPS)
    macd_hist_slope = macd_hist_norm - macd_hist_norm.shift(MACD_SLOPE_LAG)

    sma20 = close.rolling(BB_PERIOD).mean()
    std20 = close.rolling(BB_PERIOD).std(ddof=0)
    bb_upper = sma20 + BB_STD * std20
    bb_lower = sma20 - BB_STD * std20
    bb_pctb = (close - bb_lower) / (bb_upper - bb_lower + EPS)

    realized_vol_20 = ret_1.rolling(REALIZED_VOL_WINDOW).std(ddof=0)

    sma50 = close.rolling(MA_ZSCORE_WINDOW).mean()
    std50 = close.rolling(MA_ZSCORE_WINDOW).std(ddof=0)
    z_price_ma50 = (close - sma50) / (std50 + EPS)

    horas = m15["time"].dt.hour + m15["time"].dt.minute / 60.0
    hour_sin = np.sin(2 * np.pi * horas / 24.0)
    hour_cos = np.cos(2 * np.pi * horas / 24.0)

    trend_h1 = _htf_trend_align(h1).sort_values("h1_close_time")
    m15_ordenado = m15[["time"]].sort_values("time")
    alinhado = pd.merge_asof(m15_ordenado, trend_h1, left_on="time",
                             right_on="h1_close_time", direction="backward")
    htf_trend_align = alinhado.set_index(m15_ordenado.index)["htf_trend_align"]

    saida = pd.DataFrame({
        "time": m15["time"],
        "ret_1": ret_1, "ret_4": ret_4, "ret_16": ret_16,
        "atr_mom_8": atr_mom_8, "rsi_14": rsi_14,
        "macd_hist_norm": macd_hist_norm, "macd_hist_slope": macd_hist_slope,
        "bb_pctb": bb_pctb, "realized_vol_20": realized_vol_20,
        "z_price_ma50": z_price_ma50, "htf_trend_align": htf_trend_align,
        "hour_sin": hour_sin, "hour_cos": hour_cos,
    })
    assert list(saida.columns[1:]) == list(FEATURE_NAMES)
    return saida
