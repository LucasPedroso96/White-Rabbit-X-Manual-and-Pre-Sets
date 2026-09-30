"""Os osciladores vs valores calculados a mao / propriedades exatas. Fidelidade ao MT5: ver README."""
import numpy as np
import pytest

from wrx_engine import indicators as I


def test_momentum_is_price_over_price_n_bars_ago():
    p = np.array([1.0, 2.0, 4.0, 3.0, 6.0])
    m = I.momentum(p, 2)
    assert np.isnan(m[1]) and m[2] == pytest.approx(400.0) and m[4] == pytest.approx(150.0)


def test_rsi_extremes_and_wilder_recursion():
    up = np.arange(1.0, 40.0)
    assert I.rsi(up, 14)[-1] == 100.0
    assert I.rsi(np.full(40, 1.0), 14)[-1] == 50.0
    p = np.array([1, 2, 1.5, 2.5, 2.0, 3.0, 2.5], float)
    r = I.rsi(p, 3)
    d = np.diff(p)
    ap, an = np.maximum(d[:3], 0).mean(), np.maximum(-d[:3], 0).mean()
    assert r[3] == pytest.approx(100 - 100 / (1 + ap / an))
    ap = (ap * 2 + max(d[3], 0)) / 3
    an = (an * 2 + max(-d[3], 0)) / 3
    assert r[4] == pytest.approx(100 - 100 / (1 + ap / an))
    assert np.isnan(r[2])


def test_cci_hand_example():
    p = np.array([1.0, 2.0, 3.0, 4.0])
    c = I.cci(p, 3)
    # janela [2,3,4]: media 3, desvio medio 2/3 -> (4-3)/(0.015*2/3)
    assert c[3] == pytest.approx(1.0 / (0.015 * 2.0 / 3.0))


def test_wpr_bounds():
    h = np.array([2.0, 3.0, 4.0]); l = np.array([1.0, 1.5, 2.0])
    assert I.wpr(h, l, np.array([1.5, 2.0, 4.0]), 3)[2] == 0.0          # fechou na maxima
    assert I.wpr(h, l, np.array([1.5, 2.0, 1.0]), 3)[2] == pytest.approx(-100 * (4 - 1) / (4 - 1))


def test_demarker_and_mfi_bounds_and_neutral_cases():
    rng = np.random.default_rng(3)
    p = 1 + np.cumsum(rng.normal(0, .01, 200)); h = p + .01; l = p - .01
    d = I.demarker(h, l, 14)
    assert np.nanmin(d) >= 0 and np.nanmax(d) <= 1
    assert I.demarker(np.full(30, 2.0), np.full(30, 1.0), 14)[-1] == 0.5
    m = I.mfi(h, l, p, rng.integers(50, 200, 200).astype(float), 14)
    assert np.nanmin(m) >= 0 and np.nanmax(m) <= 100
    rising = np.arange(1.0, 40.0)
    assert I.mfi(rising + .1, rising - .1, rising, np.full(39, 10.0), 14)[-1] == 100.0


def test_trix_is_relative_change_of_triple_ema():
    p = 1 + np.cumsum(np.random.default_rng(1).normal(0, .01, 100))
    e3 = I.ema(I.ema(I.ema(p, 9), 9), 9)
    assert I.trix(p, 9)[50] == pytest.approx((e3[50] - e3[49]) / e3[49])


def test_osma_is_macd_minus_signal():
    p = 1 + np.cumsum(np.random.default_rng(2).normal(0, .01, 100))
    m, s = I.macd(p, 12, 26, 9)
    assert np.allclose(I.osma(p, 12, 26, 9)[30:], (m - s)[30:])


def test_stochastic_hand_example_and_slowing_sums():
    h = np.array([10.0, 11, 12, 11, 13]); l = np.array([8.0, 9, 9, 8, 10]); c = np.array([9.0, 10, 11, 9, 12])
    m, s = I.stochastic(h, l, c, k=3, d=2, slowing=1, method=0, low_high=True)
    assert m[2] == pytest.approx((11 - 8) / (12 - 8) * 100)       # HH=12 LL=8
    assert m[4] == pytest.approx((12 - 8) / (13 - 8) * 100)
    assert s[3] == pytest.approx((m[2] + m[3]) / 2)
    m3, _ = I.stochastic(h, l, c, k=3, d=2, slowing=2, method=0, low_high=True)
    num = (c[2] - 8) + (c[3] - 8); den = (12 - 8) + (12 - 8)
    assert m3[3] == pytest.approx(num / den * 100)                # soma/soma, nao media dos %K
    mc, _ = I.stochastic(h, l, c, 3, 2, 1, 0, low_high=False)     # Close/Close
    assert mc[2] == pytest.approx((11 - 9) / (11 - 9) * 100)


def test_ma_methods_hand_values():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert I.ma(x, 3, I.MODE_SMA)[2] == 2.0
    assert I.ma(x, 3, I.MODE_LWMA)[2] == pytest.approx((1 * 1 + 2 * 2 + 3 * 3) / 6)
    sm = I.ma(x, 3, I.MODE_SMMA)
    assert sm[2] == 2.0 and sm[3] == pytest.approx((2.0 * 2 + 4) / 3)
    assert I.ma(x, 3, I.MODE_EMA)[0] == 1.0


def test_ema_from_first_valid_skips_leading_nans():
    x = np.array([np.nan, np.nan, 2.0, 4.0, 3.0])
    e = I.ema_from_first_valid(x, 3)
    assert np.isnan(e[1]) and e[2] == 2.0 and e[3] == pytest.approx(0.5 * 4 + 0.5 * 2)


def test_ichimoku_midpoints_and_span_a():
    h = np.arange(1.0, 61.0) + 1; l = np.arange(1.0, 61.0) - 1
    t, k, a, b = I.ichimoku(h, l, 9, 26, 52)
    assert t[20] == pytest.approx((h[12:21].max() + l[12:21].min()) / 2)
    assert k[30] == pytest.approx((h[5:31].max() + l[5:31].min()) / 2)
    assert a[30] == pytest.approx((t[30] + k[30]) / 2) and np.isnan(b[40]) and not np.isnan(b[59])


def test_adx_strong_trend_reads_high_and_directional():
    n = 200
    c = 1 + 0.002 * np.arange(n); h = c + 0.0005; l = c - 0.0005
    adx, pdi, ndi = I.adx(h, l, c, 14)
    assert adx[-1] > 60 and pdi[-1] > ndi[-1] and 0 <= adx[-1] <= 100
    rng = np.random.default_rng(0); c2 = 1 + np.cumsum(rng.normal(0, 1e-3, n))
    assert I.adx(c2 + 5e-4, c2 - 5e-4, c2, 14)[0][-1] < adx[-1]


def test_stochastic_signal_line_honours_ma_method():
    rng = np.random.default_rng(8)
    c = 1 + np.cumsum(rng.normal(0, .01, 120)); h = c + .01; l = c - .01
    m, s_sma = I.stochastic(h, l, c, 5, 3, 3, I.MODE_SMA, True)
    _, s_ema = I.stochastic(h, l, c, 5, 3, 3, I.MODE_EMA, True)
    _, s_lw = I.stochastic(h, l, c, 5, 3, 3, I.MODE_LWMA, True)
    assert not np.allclose(s_sma[20:], s_ema[20:]) and not np.allclose(s_sma[20:], s_lw[20:])
    i = 60
    assert s_sma[i] == pytest.approx(m[i - 2:i + 1].mean())
    assert s_lw[i] == pytest.approx((m[i - 2] * 1 + m[i - 1] * 2 + m[i] * 3) / 6)
