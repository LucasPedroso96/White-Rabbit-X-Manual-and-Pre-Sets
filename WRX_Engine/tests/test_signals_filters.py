import numpy as np
import pytest

from conftest import T0, base_path, build_ticks, make_params
from wrx_engine import indicators as I
from wrx_engine import signals as S
from wrx_engine.bars import Bars, m1_from_ticks, resample
from wrx_engine.engine import run_backtest
from wrx_engine.filters import compute_filters, higher_timeframes


# EntryNeutralLevel(): Stoch/RSI/MFI 50, Momentum 100, WPR -50, DeMarker 0.5, resto 0
NEUTRAL = {1: 0.0, 2: 100.0, 3: 50.0, 4: 0.0, 5: 50.0, 6: 0.0, 7: -50.0, 8: 0.5, 9: 50.0, 10: 0.0}


def m1_bars(n=900, seed=4, step=0.00015):
    ticks = build_ticks(base_path(n, seed=seed, step=step))
    return ticks, m1_from_ticks(ticks)[0]


@pytest.mark.parametrize("ind_idx", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_every_indicator_wiring_matches_definition(ind_idx):
    _, m1 = m1_bars()
    p = make_params(EntryIndicator=ind_idx, Fast_EMA=9, Slow_EMA=21, MACD_SMA=5)
    tf = resample(m1, 1)
    es = S.build_entry_series(p, tf, tf.volume)
    rev_b, rev_s, sig_b, sig_s, ref_b, ref_s = S.raw_triggers(p, es)
    lv = NEUTRAL[ind_idx]                       # literais do .mq5 (EntryNeutralLevel), nao a propria funcao
    hits = 0
    for b in range(80, len(tf) - 1):
        vals = [es.main[b - k] for k in (1, 2, 3)] + [es.signal[b - 1], es.signal[b - 2]]
        if any(np.isnan(v) for v in vals):
            continue
        if ind_idx == S.EMA_CROSS:
            c1, c2, s1, s2 = es.close[b - 1], es.close[b - 2], es.signal[b - 1], es.signal[b - 2]
            want_ref_b, want_ref_s = c1 > s1 and c2 < s2, c1 < s1 and c2 > s2
        else:
            want_ref_b = es.main[b - 1] > lv and es.main[b - 2] < lv
            want_ref_s = es.main[b - 1] < lv and es.main[b - 2] > lv
        m = es.main
        assert bool(rev_b[b]) == (m[b - 1] > m[b - 2] and m[b - 2] < m[b - 3])
        assert bool(rev_s[b]) == (m[b - 1] < m[b - 2] and m[b - 2] > m[b - 3])
        assert bool(sig_b[b]) == (m[b - 1] > es.signal[b - 1] and m[b - 2] < es.signal[b - 2])
        assert bool(ref_b[b]) == want_ref_b and bool(ref_s[b]) == want_ref_s
        hits += int(rev_b[b]) + int(sig_s[b]) + int(ref_b[b] or ref_s[b])
    assert hits > 5, "cenario sem sinais: teste nao mediu nada"


def test_oscillator_signal_line_is_ema_of_main_and_macd_uses_sma():
    _, m1 = m1_bars()
    tf = resample(m1, 1)
    rsi = S.build_entry_series(make_params(EntryIndicator=5, Fast_EMA=14, MACD_SMA=7), tf, tf.volume)
    assert np.allclose(rsi.signal[50:], I.ema_from_first_valid(I.rsi(tf.close, 14), 7)[50:])
    mac = S.build_entry_series(make_params(), tf, tf.volume)
    assert np.allclose(mac.signal[60:], I.sma(mac.main, 9)[60:])


def test_ichimoku_kumo_breakout_uses_cloud_computed_kijun_bars_ago():
    _, m1 = m1_bars(1200, seed=9, step=0.0003)
    tf = resample(m1, 1)
    p = make_params(EntryIndicator=11, Fast_EMA=9, Slow_EMA=26, MACD_SMA=52, EntryMethod=2)
    es = S.build_entry_series(p, tf, tf.volume)
    ref_b, ref_s = S.raw_triggers(p, es)[4:]
    h, l, c = tf.high, tf.low, tf.close
    def cloud(idx):    # topo/fundo da nuvem calculada na barra `idx`
        a = ((h[idx - 8:idx + 1].max() + l[idx - 8:idx + 1].min()) / 2 + (h[idx - 25:idx + 1].max() + l[idx - 25:idx + 1].min()) / 2) / 2
        b = (h[idx - 51:idx + 1].max() + l[idx - 51:idx + 1].min()) / 2
        return max(a, b), min(a, b)
    n_hit = 0
    for b in range(200, len(tf) - 1):
        top1, bot1 = cloud(b - 1 - 26)       # nuvem SOBRE a barra de shift 1
        top2, bot2 = cloud(b - 2 - 26)
        assert bool(ref_b[b]) == (c[b - 1] > top1 and c[b - 2] <= top2)
        assert bool(ref_s[b]) == (c[b - 1] < bot1 and c[b - 2] >= bot2)
        n_hit += int(ref_b[b]) + int(ref_s[b])
    assert n_hit > 0


def test_ichimoku_without_kumo_uses_price_vs_kijun_and_chikou_filter_blocks():
    _, m1 = m1_bars(1200, seed=9, step=0.0003)
    tf = resample(m1, 1)
    p = make_params(EntryIndicator=11, Fast_EMA=9, Slow_EMA=26, MACD_SMA=52, EntryMethod=2, IchimokuUseKumo="false")
    es = S.build_entry_series(p, tf, tf.volume)
    ref_b = S.raw_triggers(p, es)[4]
    b = np.flatnonzero(ref_b)[3]
    assert es.close[b - 1] > es.signal[b - 1] and es.close[b - 2] < es.signal[b - 2]
    pc = make_params(EntryIndicator=11, Fast_EMA=9, Slow_EMA=26, MACD_SMA=52, EntryMethod=6, IchimokuUseKumo="false",
                     IchimokuChikouFilter="true")
    ref = S.raw_triggers(pc, es)
    for bb in range(60, len(tf) - 1):
        if ref[0][bb] or ref[2][bb] or ref[4][bb]:
            assert es.close[bb - 1] > es.close[bb - 1 - 26]          # Chikou confirma a compra


@pytest.mark.parametrize("ind_idx", list(range(12)))
def test_engine_trades_with_every_entry_indicator(spec, ind_idx):
    ticks = build_ticks(base_path(2500, seed=13, step=0.00025))
    over = dict(EntryIndicator=ind_idx, Stop=3.0, Take=3.0, MaxShortTrades=1, Fast_EMA=9, Slow_EMA=21, MACD_SMA=5)
    if ind_idx == 11:
        over.update(Fast_EMA=9, Slow_EMA=26, MACD_SMA=52)
    res = run_backtest(make_params(**over), spec, ticks)
    total = len(res.trades) + len(res.open_positions)
    assert total > 3, S.INDICATOR_NAMES[ind_idx]
    assert (res.trades.close_ms > res.trades.open_ms).all()


# ------------------------------------------------------------------ filtros
def test_higher_timeframes_map():
    assert higher_timeframes(1) == (15, 60) and higher_timeframes(15) == (60, 240)
    assert higher_timeframes(60) == (240, 1440) and higher_timeframes(240) == (1440, 10080)
    assert higher_timeframes(1440)[1] == 43200 and higher_timeframes(10080) == (43200, 43200)


def test_mtf_filter_compares_current_bid_with_open_of_forming_higher_bars():
    ticks = build_ticks(base_path(600, seed=2, step=0.0002))
    m1, first = m1_from_ticks(ticks)
    fb = ticks.bid[first]
    p = make_params(AtivarFiltroMTF="true", MTF_RequererAmbos="true")
    n = len(m1)
    atr_c = np.ones(n); atr0 = np.ones(n); ab = np.arange(n)
    f = compute_filters(p, m1, fb, atr_c, atr0, ab)
    m15, m60 = resample(m1, 15), resample(m1, 60)
    for j in range(0, n, 7):
        o15 = m15.open[np.searchsorted(m15.time, (m1.time[j] // 900) * 900)]
        o60 = m60.open[np.searchsorted(m60.time, (m1.time[j] // 3600) * 3600)]
        assert f.cond_buy[j] == (fb[j] > o15 and fb[j] > o60)
        assert f.cond_sell[j] == (fb[j] < o15 and fb[j] < o60)
    p2 = make_params(AtivarFiltroMTF="true", MTF_RequererAmbos="false")
    f2 = compute_filters(p2, m1, fb, atr_c, atr0, ab)
    assert f2.cond_buy.sum() >= f.cond_buy.sum()


def test_volatility_filter_high_and_low():
    n = 400
    t = build_ticks(base_path(n, seed=5, step=0.0001))
    m1, first = m1_from_ticks(t)
    fb = t.bid[first]
    atr_c, _ = I.atr(m1.high, m1.low, m1.close, 14)
    ab = np.arange(n)
    atr0 = np.where(ab >= 14, atr_c, np.nan)
    atr0[300] = np.nanmean(atr_c[200:299]) * 5           # explosao de volatilidade
    atr_c2 = atr_c.copy(); atr_c2[299] = atr0[300]        # ATR[1] tambem alto
    hi = compute_filters(make_params(EntradaATR="true", VolatilityFilter=1, MultiplicadorATR=1.5, PeriodoBaselineATR=100),
                         m1, fb, atr_c2, atr0, ab)
    lo = compute_filters(make_params(EntradaATR="true", VolatilityFilter=0, MultiplicadorATR=1.5, PeriodoBaselineATR=100),
                         m1, fb, atr_c2, atr0, ab)
    assert hi.cond_buy[300] and not hi.cond_buy[250]
    atr_c3 = atr_c2.copy(); atr_c3[299] = atr_c[299]        # ATR[0] alto mas ATR[1] normal: exige os DOIS
    only0 = compute_filters(make_params(EntradaATR="true", VolatilityFilter=1, MultiplicadorATR=1.5, PeriodoBaselineATR=100),
                            m1, fb, atr_c3, atr0, ab)
    assert not only0.cond_buy[300]
    assert not lo.cond_buy[300]
    assert not (hi.cond_buy & lo.cond_buy).any()


def test_ma_filter_rules_and_reversal_and_adx_gate():
    ticks = build_ticks(base_path(1500, seed=6, step=0.0002))
    m1, first = m1_from_ticks(ticks)
    fb = ticks.bid[first]
    n = len(m1); ab = np.arange(n); one = np.ones(n)
    line = I.ma(m1.close, 50, 1)
    for rule in (0, 1, 2, 3):
        for rev in (0, 1):
            p = make_params(AtivarFiltroMA="true", MA_Period=50, MetodoMA=rule, SentidoMA=rev, MA_SlopeLookback=3)
            f = compute_filters(p, m1, fb, one, one, ab)
            for j in range(120, n, 37):
                price, m0, mN = m1.close[j - 1], line[j - 1], line[j - 4]
                pb, sb_ = (price > m0, m0 > mN) if not rev else (price < m0, m0 < mN)
                want = {0: pb, 1: sb_, 2: pb and sb_, 3: pb or sb_}[rule]
                assert bool(f.cond_buy[j]) == bool(want), (rule, rev, j)
                ps, ss = (price < m0, m0 < mN) if not rev else (price > m0, m0 > mN)
                want_s = {0: ps, 1: ss, 2: ps and ss, 3: ps or ss}[rule]
                assert bool(f.cond_sell[j]) == bool(want_s), ("sell", rule, rev, j)
    a, pdi, ndi = I.adx(m1.high, m1.low, m1.close, 14)
    p = make_params(AtivarFiltroADX="true", ADX_Limiar=20, MetodoADX=1)
    f = compute_filters(p, m1, fb, one, one, ab)
    for j in range(60, n, 41):
        strong = a[j - 1] >= 20
        assert bool(f.cond_buy[j]) == (strong and pdi[j - 1] > ndi[j - 1])
        assert bool(f.cond_sell[j]) == (strong and ndi[j - 1] > pdi[j - 1])


def test_filters_reduce_entries_in_engine(spec):
    ticks = build_ticks(base_path(3000, seed=8, step=0.0002))
    base = dict(Stop=3.0, Take=3.0, MaxShortTrades=1)
    free = run_backtest(make_params(**base), spec, ticks)
    filt = run_backtest(make_params(**base, AtivarFiltroMA="true", MA_Period=100, MetodoMA=2), spec, ticks)
    assert 0 < len(filt.trades) + len(filt.open_positions) < len(free.trades) + len(free.open_positions)
