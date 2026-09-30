import numpy as np

from wrx_engine import indicators as ind


def test_ema_seeds_on_first_price_and_matches_loop():
    x = np.array([1.0, 2.0, 4.0, 3.0, 5.0])
    a = 2 / (3 + 1)
    ref = [x[0]]
    for v in x[1:]:
        ref.append(a * v + (1 - a) * ref[-1])
    assert np.allclose(ind.ema(x, 3), ref)


def test_macd_signal_is_sma_of_main():
    rng = np.random.default_rng(1)
    p = 1.1 + np.cumsum(rng.normal(0, 1e-3, 200))
    main, sig = ind.macd(p, 12, 26, 9)
    assert np.allclose(main, ind.ema(p, 12) - ind.ema(p, 26))
    assert np.isnan(sig[7]) and not np.isnan(sig[8])
    assert np.isclose(sig[50], main[42:51].mean())


def test_atr_is_simple_mean_of_true_range_excluding_first_bar():
    h = np.array([10, 12, 13, 12, 15, 16, 15.0])
    l = np.array([9, 10, 11, 10, 12, 14, 13.0])
    c = np.array([9.5, 11, 12, 11, 14, 15, 14.0])
    atr, tr = ind.atr(h, l, c, 3)
    assert tr[0] == 0.0
    assert np.isnan(atr[2]) and not np.isnan(atr[3])
    assert np.isclose(atr[3], tr[1:4].mean())
    assert np.isclose(atr[6], tr[4:7].mean())
    # forma incremental usada pelo motor no ATR[0] parcial
    assert np.isclose(atr[5], atr[4] + (tr[5] - tr[2]) / 3)


def test_true_range_uses_gap_from_previous_close():
    tr = ind.true_range([10, 12], [9, 11.5], [9.5, 11.8])
    assert np.isclose(tr[1], max(0.5, abs(12 - 9.5), abs(11.5 - 9.5)))


def test_applied_price_variants():
    o, h, l, c = 1.0, 3.0, 0.0, 2.0
    assert ind.applied_price(o, h, l, c, ind.PRICE_CLOSE) == 2.0
    assert ind.applied_price(o, h, l, c, ind.PRICE_MEDIAN) == 1.5
    assert ind.applied_price(o, h, l, c, ind.PRICE_TYPICAL) == 5.0 / 3
    assert ind.applied_price(o, h, l, c, ind.PRICE_WEIGHTED) == 7.0 / 4
