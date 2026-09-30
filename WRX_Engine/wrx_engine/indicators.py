"""Indicadores no formato dos built-ins do MT5 (iMACD, iATR, iMA-EMA).

Cada funcao devolve uma serie alinhada barra a barra (indice 0 = barra mais antiga;
o EA usa ArraySetAsSeries, entao "shift k" = indice `i - k`). Valores ainda nao
definidos ficam NaN.

Pontos de fidelidade (conferir contra o Tester -- ver parity.py):
  * EMA semeia no PRIMEIRO preco (alpha = 2/(n+1)); depende de quanto historico existe.
  * iMACD: main = EMA(fast) - EMA(slow); signal = SMA(main, signal)  (SMA, nao EMA).
  * iATR: media SIMPLES do True Range (nao Wilder); TR[0] = 0 e nao entra na media.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ENUM_APPLIED_PRICE
PRICE_CLOSE, PRICE_OPEN, PRICE_HIGH, PRICE_LOW, PRICE_MEDIAN, PRICE_TYPICAL, PRICE_WEIGHTED = range(1, 8)


def applied_price(o, h, l, c, mode: int) -> np.ndarray:
    if mode == PRICE_OPEN:
        return np.asarray(o, float)
    if mode == PRICE_HIGH:
        return np.asarray(h, float)
    if mode == PRICE_LOW:
        return np.asarray(l, float)
    if mode == PRICE_MEDIAN:
        return (np.asarray(h) + np.asarray(l)) / 2.0
    if mode == PRICE_TYPICAL:
        return (np.asarray(h) + np.asarray(l) + np.asarray(c)) / 3.0
    if mode == PRICE_WEIGHTED:
        return (np.asarray(h) + np.asarray(l) + 2.0 * np.asarray(c)) / 4.0
    return np.asarray(c, float)


def ema(x, n: int) -> np.ndarray:
    return pd.Series(np.asarray(x, float)).ewm(alpha=2.0 / (n + 1.0), adjust=False).mean().to_numpy()


def sma(x, n: int) -> np.ndarray:
    return pd.Series(np.asarray(x, float)).rolling(n, min_periods=n).mean().to_numpy()


def macd(price, fast: int, slow: int, signal: int) -> tuple[np.ndarray, np.ndarray]:
    main = ema(price, fast) - ema(price, slow)
    return main, sma(main, signal)


def true_range(h, l, c) -> np.ndarray:
    h, l, c = (np.asarray(a, float) for a in (h, l, c))
    tr = np.zeros(len(h))
    if len(h) > 1:
        pc = c[:-1]
        tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - pc), np.abs(l[1:] - pc)])
    return tr


def atr(h, l, c, n: int) -> tuple[np.ndarray, np.ndarray]:
    """(ATR, TR). ATR[i] = media de TR[i-n+1..i], valida a partir de i = n."""
    tr = true_range(h, l, c)
    src = tr.copy()
    if len(src):
        src[0] = np.nan
    return pd.Series(src).rolling(n, min_periods=n).mean().to_numpy(), tr
