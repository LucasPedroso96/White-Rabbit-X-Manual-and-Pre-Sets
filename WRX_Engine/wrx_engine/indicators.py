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


# ------------------------------------------------------------------ medias moveis (iMA)
MODE_SMA, MODE_EMA, MODE_SMMA, MODE_LWMA = range(4)


def ema_from_first_valid(x, n: int) -> np.ndarray:
    """EMA de uma serie que comeca com NaN (indicador ainda sem dado): semeia no 1o valor valido.
    E o que iMA(..., handle_de_indicador) faz sobre o buffer de outro indicador."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    ok = np.flatnonzero(~np.isnan(x))
    if len(ok):
        out[ok[0]:] = ema(x[ok[0]:], n)
    return out


def smma(x, n: int) -> np.ndarray:
    """SMMA do MT5: semente = SMA das n primeiras barras; depois (prev*(n-1)+preco)/n."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = x[:n].mean()
    a = 1.0 / n
    prev = out[n - 1]
    for i in range(n, len(x)):
        prev = prev * (1 - a) + x[i] * a
        out[i] = prev
    return out


def lwma(x, n: int) -> np.ndarray:
    x = np.asarray(x, float)
    w = np.arange(1, n + 1, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        win = np.lib.stride_tricks.sliding_window_view(x, n)
        out[n - 1:] = (win * w).sum(axis=1) / w.sum()
    return out


def ma(x, n: int, method: int) -> np.ndarray:
    """iMA / suavizacao do %D: SMA=0, EMA=1, SMMA=2, LWMA=3 (ENUM_MA_METHOD)."""
    return {MODE_SMA: sma, MODE_EMA: ema, MODE_SMMA: smma, MODE_LWMA: lwma}[method](x, n)


# ------------------------------------------------------------------ osciladores
def momentum(price, n: int) -> np.ndarray:
    p = np.asarray(price, float)
    out = np.full(len(p), np.nan)
    if len(p) > n:
        out[n:] = p[n:] / p[:-n] * 100.0
    return out


def rsi(price, n: int) -> np.ndarray:
    """RSI.mq5: medias iniciais simples das n primeiras variacoes; depois suavizacao de Wilder."""
    p = np.asarray(price, float)
    out = np.full(len(p), np.nan)
    if len(p) <= n:
        return out
    d = np.diff(p)
    pos, neg = np.maximum(d, 0.0), np.maximum(-d, 0.0)
    ap, an = pos[:n].mean(), neg[:n].mean()

    def val(a_p, a_n):
        if a_n != 0.0:
            return 100.0 - 100.0 / (1.0 + a_p / a_n)
        return 100.0 if a_p != 0.0 else 50.0

    out[n] = val(ap, an)
    for i in range(n + 1, len(p)):
        ap = (ap * (n - 1) + pos[i - 1]) / n
        an = (an * (n - 1) + neg[i - 1]) / n
        out[i] = val(ap, an)
    return out


def cci(price, n: int) -> np.ndarray:
    p = np.asarray(price, float)
    out = np.full(len(p), np.nan)
    if len(p) < n:
        return out
    win = np.lib.stride_tricks.sliding_window_view(p, n)
    m = win.mean(axis=1)
    md = np.abs(win - m[:, None]).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        out[n - 1:] = np.where(md != 0.0, (p[n - 1:] - m) / (0.015 * md), 0.0)
    return out


def wpr(h, l, c, n: int) -> np.ndarray:
    h, l, c = (np.asarray(a, float) for a in (h, l, c))
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    hh = np.lib.stride_tricks.sliding_window_view(h, n).max(axis=1)
    ll = np.lib.stride_tricks.sliding_window_view(l, n).min(axis=1)
    rng = hh - ll
    with np.errstate(divide="ignore", invalid="ignore"):
        out[n - 1:] = np.where(rng != 0.0, -(hh - c[n - 1:]) * 100.0 / rng, 0.0)
    return out


def demarker(h, l, n: int) -> np.ndarray:
    h, l = np.asarray(h, float), np.asarray(l, float)
    out = np.full(len(h), np.nan)
    if len(h) <= n:
        return out
    demax = np.maximum(h[1:] - h[:-1], 0.0)
    demin = np.maximum(l[:-1] - l[1:], 0.0)
    smax = pd.Series(demax).rolling(n, min_periods=n).mean().to_numpy()
    smin = pd.Series(demin).rolling(n, min_periods=n).mean().to_numpy()
    tot = smax + smin
    with np.errstate(divide="ignore", invalid="ignore"):
        dem = np.where(tot != 0.0, smax / tot, 0.5)
    dem[np.isnan(smax)] = np.nan
    out[1:] = dem
    return out


def mfi(h, l, c, vol, n: int) -> np.ndarray:
    h, l, c, v = (np.asarray(a, float) for a in (h, l, c, vol))
    tp = (h + l + c) / 3.0
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(tp)
    flow = tp[1:] * v[1:]
    pos = np.where(d > 0, flow, 0.0)
    neg = np.where(d < 0, flow, 0.0)
    sp = pd.Series(pos).rolling(n, min_periods=n).sum().to_numpy()
    sn = pd.Series(neg).rolling(n, min_periods=n).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        val = np.where(sn != 0.0, 100.0 - 100.0 / (1.0 + sp / sn), 100.0)
    val[np.isnan(sp)] = np.nan
    out[1:] = val
    return out


def trix(price, n: int) -> np.ndarray:
    e3 = ema(ema(ema(price, n), n), n)
    out = np.full(len(e3), np.nan)
    if len(e3) > 1:
        with np.errstate(divide="ignore", invalid="ignore"):
            out[1:] = (e3[1:] - e3[:-1]) / e3[:-1]
    return out


def osma(price, fast: int, slow: int, signal: int) -> np.ndarray:
    main, sig = macd(price, fast, slow, signal)
    return main - sig


def stochastic(h, l, c, k: int, d: int, slowing: int, method: int, low_high: bool):
    """Stochastic.mq5: numerador/denominador somados em `slowing` barras; %D = MA(method) do %K."""
    h, l, c = (np.asarray(a, float) for a in (h, l, c))
    n = len(c)
    main = np.full(n, np.nan)
    if n < k + slowing - 1:
        return main, np.full(n, np.nan)
    src_h, src_l = (h, l) if low_high else (c, c)
    hh = np.full(n, np.nan)
    ll = np.full(n, np.nan)
    hh[k - 1:] = np.lib.stride_tricks.sliding_window_view(src_h, k).max(axis=1)
    ll[k - 1:] = np.lib.stride_tricks.sliding_window_view(src_l, k).min(axis=1)
    num = pd.Series(c - ll).rolling(slowing, min_periods=slowing).sum().to_numpy()
    den = pd.Series(hh - ll).rolling(slowing, min_periods=slowing).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        main = np.where(den != 0.0, num / den * 100.0, 100.0)
    main[np.isnan(num)] = np.nan
    sig = np.full(n, np.nan)
    ok = np.flatnonzero(~np.isnan(main))
    if len(ok):
        sig[ok[0]:] = ma(main[ok[0]:], d, method)
    return main, sig


def ichimoku(h, l, tenkan: int, kijun: int, senkou_b: int):
    """(tenkan, kijun, spanA, spanB) SEM deslocamento: o valor calculado na barra i vale para a barra i+kijun."""
    h, l = np.asarray(h, float), np.asarray(l, float)
    n = len(h)

    def mid(p):
        out = np.full(n, np.nan)
        if n >= p:
            out[p - 1:] = (np.lib.stride_tricks.sliding_window_view(h, p).max(axis=1)
                           + np.lib.stride_tricks.sliding_window_view(l, p).min(axis=1)) / 2.0
        return out

    t, k, b = mid(tenkan), mid(kijun), mid(senkou_b)
    return t, k, (t + k) / 2.0, b


def adx(h, l, c, n: int):
    """ADX.mq5: +DI/-DI e DX suavizados por EMA (alpha=2/(n+1)) sobre os valores brutos.
    Devolve (adx, +di, -di). HIPOTESE de fidelidade -- confira no Tester."""
    h, l, c = (np.asarray(a, float) for a in (h, l, c))
    m = len(h)
    pdi, ndi, dx, out = (np.zeros(m) for _ in range(4))
    a = 2.0 / (n + 1.0)
    for i in range(1, m):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        up, dn = max(up, 0.0), max(dn, 0.0)
        if up > dn:
            dn = 0.0
        elif up < dn:
            up = 0.0
        else:
            up = dn = 0.0
        tr = max(abs(h[i] - l[i]), abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        rp, rn = (100.0 * up / tr, 100.0 * dn / tr) if tr != 0.0 else (0.0, 0.0)
        pdi[i] = rp * a + pdi[i - 1] * (1 - a)
        ndi[i] = rn * a + ndi[i - 1] * (1 - a)
        s = pdi[i] + ndi[i]
        dx_i = 100.0 * abs((pdi[i] - ndi[i]) / s) if s != 0.0 else 0.0
        out[i] = dx_i * a + out[i - 1] * (1 - a)
    if m:
        for arr in (out, pdi, ndi):
            arr[0] = np.nan
    return out, pdi, ndi
