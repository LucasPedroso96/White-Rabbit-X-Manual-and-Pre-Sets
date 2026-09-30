import math

import numpy as np
import pytest

from conftest import T0, base_path, build_ticks, make_params
from scen import go
from wrx_engine import signals as S
from wrx_engine.bars import m1_from_ticks, resample
from wrx_engine.engine import run_backtest
from wrx_engine.setfile import oninit_errors, params_from_dict


def vol_regime_ticks(n=1200, seed=3):
    """Volatilidade que oscila (aperta e expande) para o Squeeze/Breakout terem o que ler."""
    rng = np.random.default_rng(seed)
    price, out = 1.1, []
    for m in range(n):
        amp = 0.00003 + 0.00040 * (0.5 + 0.5 * math.sin(m / 55.0)) ** 2
        ticks = []
        for _ in range(4):
            price += rng.normal(0, amp)
            ticks.append(round(price, 5))
        out.append(ticks)
    return out


def naive_bands(close, period, dev):
    main, up, lo = [], [], []
    for i in range(len(close)):
        if i < period - 1:
            main.append(np.nan); up.append(np.nan); lo.append(np.nan)
            continue
        w = close[i - period + 1:i + 1]
        m = sum(w) / period
        sd = math.sqrt(sum((x - m) ** 2 for x in w) / period)
        main.append(m); up.append(m + dev * sd); lo.append(m - dev * sd)
    return main, up, lo


def test_bollinger_signals_match_definitions_for_the_three_modes():
    ticks = build_ticks(vol_regime_ticks())
    m1, _ = m1_from_ticks(ticks)
    tf = resample(m1, 1)
    c, o = list(tf.close), list(tf.open)
    main, up, lo = naive_bands(c, 20, 2.0)
    for mode in (0, 1, 2):
        p = make_params(BandsPeriod=20, BandsDeviation=2.0, BollingerEntryMode=mode, SqueezeLookback=20,
                        SqueezeTolerancePct=10)
        assert p.family == "bollinger"
        buy, sell, _ = S.bollinger_signals(p, tf)
        hits = 0
        for b in range(60, len(tf)):
            c1, c2, o1 = c[b - 1], c[b - 2], o[b - 1]
            want_brk_b = c1 > up[b - 1] and c2 <= up[b - 2]
            want_brk_s = c1 < lo[b - 1] and c2 >= lo[b - 2]
            if mode == 0:
                wb = c1 > lo[b - 1] and c2 <= lo[b - 2] and c1 > o1 and c1 < main[b - 1]
                ws = c1 < up[b - 1] and c2 >= up[b - 2] and c1 < o1 and c1 > main[b - 1]
            elif mode == 1:
                wb, ws = want_brk_b, want_brk_s
            else:
                width = [(up[b - i] - lo[b - i]) / main[b - i] for i in range(2, min(22, 49) + 1)]
                active = width[0] <= min(width) * 1.10
                wb, ws = active and want_brk_b, active and want_brk_s
            assert bool(buy[b]) == wb and bool(sell[b]) == ws, (mode, b)
            hits += int(wb) + int(ws)
        assert hits > 3, f"modo {mode}: cenario sem sinais"


def test_bollinger_engine_trades_in_every_mode(spec):
    ticks = build_ticks(vol_regime_ticks(2500, seed=5))
    for mode in (0, 1, 2):
        res = run_backtest(make_params(BandsPeriod=20, BollingerEntryMode=mode, Stop=3.0, Take=3.0, MaxShortTrades=1),
                           spec, ticks)
        assert len(res.trades) + len(res.open_positions) > 3, mode


def first_hit(conds, start):
    return next((b for b in range(start, len(conds)) if conds[b]), None)


def test_bollinger_stop_take_and_breakeven_exits_follow_the_band_geometry(spec):
    n = 1500
    mb = vol_regime_ticks(n, seed=9)
    ticks = build_ticks(mb)
    m1, _ = m1_from_ticks(ticks)
    c, o = list(m1.close), list(m1.open)
    main, up, lo = naive_bands(c, 20, 2.0)
    j0 = 300
    far = dict(Stop=500.0, AtivarTake="false", AtivarBreakeven="false", PositionSizeMode=2, PositionSizeValue=0.1)
    # --- Breakout/Squeeze: StopBolinger = rompimento fracassado (volta pra dentro da banda superior, vela de baixa)
    cond = [b > j0 and c[b - 1] < up[b - 1] and c[b - 2] >= up[b - 2] and c[b - 1] < o[b - 1] for b in range(n)]
    want = first_hit(cond, j0 + 1)
    assert want is not None
    res, _ = go(mb, [j0], spec, BandsPeriod=20, BollingerEntryMode=1, StopBolinger="true", **far)
    t = res.trades.iloc[0]
    assert t.reason == "bollinger_stop" and t.close_ms == (T0 + 60 * want) * 1000
    off, _ = go(mb, [j0], spec, BandsPeriod=20, BollingerEntryMode=1, StopBolinger="false", **far)
    assert off.trades.empty                                               # sem a flag a posicao segue aberta
    # --- Reversal: TakeBolinger so fecha no LUCRO (c1 > preco de entrada); StopBolinger so no prejuizo
    entry = round(mb[j0][0] + 1e-4, 5)
    cond_take = [b > j0 and c[b - 1] < up[b - 1] and c[b - 2] >= up[b - 2] and c[b - 1] < o[b - 1] and c[b - 1] > entry
                 for b in range(n)]
    cond_stop = [b > j0 and c[b - 1] < lo[b - 1] and c[b - 1] < entry for b in range(n)]
    w_take, w_stop = first_hit(cond_take, j0 + 1), first_hit(cond_stop, j0 + 1)
    res, _ = go(mb, [j0], spec, BandsPeriod=20, BollingerEntryMode=0, TakeBolinger="true", StopBolinger="true", **far)
    first = min(x for x in (w_take, w_stop) if x is not None)
    t = res.trades.iloc[0]
    assert t.close_ms == (T0 + 60 * first) * 1000
    assert t.reason == ("bollinger_take" if first == w_take else "bollinger_stop")
    # --- BreakevenBolinger (so Reversal): apos fechar na base da banda, SL vai para a abertura
    # (o EA so move o SL para a abertura se o bid atual estiver acima dela: senao CanModifyPositionStops recusa)
    cross = first_hit([b > j0 and c[b - 1] >= main[b - 1] and mb[b][0] > entry + 2e-4 for b in range(n)], j0 + 1)
    assert cross is not None
    res, _ = go(mb[:cross + 2], [j0], spec, BandsPeriod=20, BollingerEntryMode=0, BreakevenBolinger="true", **far)
    pos = res.open_positions[0]
    assert pos["sl"] == pytest.approx(pos["open_price"], abs=2e-5)
    none, _ = go(mb[:cross + 2], [j0], spec, BandsPeriod=20, BollingerEntryMode=1, BreakevenBolinger="true", **far)
    assert none.open_positions[0]["sl"] < none.open_positions[0]["open_price"]      # inerte fora do Reversal


# ------------------------------------------------------------------ Candles Entry
def naive_candle_ok(m1, j, first_bid, tf_min, idx, price_mode, side):
    """Slot: applied price x open, em um TF, no candle `idx` (0 = em formacao, parcial no 1o tick do minuto j)."""
    per = tf_min * 60
    def grp(t):
        return t // per
    bars = {}
    for t, o, h, l, cl in zip(m1.time, m1.open, m1.high, m1.low, m1.close):
        bars.setdefault(grp(t), []).append((t, o, h, l, cl))
    keys = sorted(bars)
    cur = grp(m1.time[j])
    def agg(g, upto=None, tick=None):
        rows = [r for r in bars[g] if upto is None or r[0] < upto]
        o = bars[g][0][1]
        h = max(r[2] for r in rows) if rows else tick
        l = min(r[3] for r in rows) if rows else tick
        cl = rows[-1][4] if rows else tick
        if tick is not None:
            h, l, cl = max(h, tick), min(l, tick), tick
        return o, h, l, cl
    ci = keys.index(cur)
    if idx == 0:
        o, h, l, cl = agg(cur, upto=m1.time[j], tick=first_bid[j])
    else:
        if ci - idx < 0:
            return False
        o, h, l, cl = agg(keys[ci - idx])
    price = {1: cl, 5: (h + l) / 2, 6: (h + l + cl) / 3, 7: (h + l + 2 * cl) / 4}[price_mode]
    return price > o if side > 0 else price < o


@pytest.mark.parametrize("slots,price_mode", [
    (((0, 1), (0, 1), (0, 1)), 1),
    (((0, 1), (1, 1), (2, 2)), 1),
    (((0, 0), (0, 2), (1, 1)), 1),
    (((0, 1), (1, 1), (1, 2)), 6),
])
def test_candle_slots_match_definition(slots, price_mode):
    mb = base_path(1500, seed=6, step=0.0003)
    ticks = build_ticks(mb)
    m1, first = m1_from_ticks(ticks)
    fb = ticks.bid[first]
    kw = {}
    for k, (tf, idx) in enumerate(slots, 1):
        kw[f"CandleTF{k}"], kw[f"CandleIndex{k}"] = tf, idx
    p = make_params(InpAppliedPrice=price_mode, **kw)
    assert p.family == "candles" and p.tf_min == [1, 5, 15, 30, 60][slots[0][0]]
    buy, sell = S.candles_signals(p, m1, fb)
    hits = 0
    for j in range(200, len(m1), 7):
        wb = all(naive_candle_ok(m1, j, fb, [1, 5, 15, 30, 60, 240, 1440, 10080][tf], idx, price_mode, +1) for tf, idx in slots)
        ws = all(naive_candle_ok(m1, j, fb, [1, 5, 15, 30, 60, 240, 1440, 10080][tf], idx, price_mode, -1) for tf, idx in slots)
        assert bool(buy[j]) == wb and bool(sell[j]) == ws, (slots, j)
        hits += int(wb) + int(ws)
    if slots[0] == (0, 0):            # M1 em formacao no 1o tick: applied price(close) == open -> nunca dispara (comportamento do EA)
        assert hits == 0
    else:
        assert hits > 5


def test_candles_family_trades_and_rejects_invalid_applied_price(spec):
    ticks = build_ticks(base_path(2500, seed=8, step=0.0003))
    res = run_backtest(make_params(CandleTF1=0, CandleIndex1=1, CandleTF2=0, CandleIndex2=2, CandleTF3=0,
                                   CandleIndex3=3, Stop=3.0, Take=3.0, MaxShortTrades=1), spec, ticks)
    assert len(res.trades) + len(res.open_positions) > 5
    for bad in (2, 3, 4):                                 # OPEN/HIGH/LOW: o EA recusa no OnInit
        v = params_from_dict({"CandleTF1": "0", "InpAppliedPrice": str(bad)}).v
        assert any("Candles" in e for e in oninit_errors(v, family="candles"))
    assert not oninit_errors(params_from_dict({"CandleTF1": "0", "InpAppliedPrice": "1"}).v, family="candles")


def test_family_is_detected_from_the_set_keys():
    assert make_params().family == "multi"
    assert make_params(BandsPeriod=20).family == "bollinger"
    assert make_params(CandleTF1=2).family == "candles"
    assert make_params(CandleTF1=2).tf_min == 15                         # TF base = slot 1


def _bars(closes, opens=None):
    from wrx_engine.bars import Bars
    closes = np.asarray(closes, float)
    opens = closes if opens is None else np.asarray(opens, float)
    n = len(closes)
    return Bars(T0 + 60 * np.arange(n), opens, np.maximum(opens, closes), np.minimum(opens, closes), closes)


def test_bollinger_equality_boundaries_with_flat_price():
    # preco PARADO: desvio 0 => bandas == preco exatamente. c2 == banda conta como ">=" / "<=" (bordas do .mq5)
    flat = [1.10000] * 30
    p = make_params(BandsPeriod=20, BollingerEntryMode=1)
    buy, sell, _ = S.bollinger_signals(p, _bars(flat + [1.09900, 1.09800]))
    idx = len(flat) + 1                    # c1 = 1.09900 (rompeu a inferior), c2 = 1.10000 == banda inferior
    assert sell[idx] and not buy[idx]


def test_bollinger_reversal_requires_close_still_below_the_middle_band():
    flat = [1.10000] * 30
    closes = flat + [1.09900, 1.10300, 1.10300]     # c2 <= inferior; c1 volta ACIMA da base; +1 barra 'formando'
    opens = flat + [1.10000, 1.09950, 1.10300]
    p = make_params(BandsPeriod=20, BollingerEntryMode=0)
    buy, sell, bb = S.bollinger_signals(p, _bars(closes, opens))
    idx = len(flat) + 2
    assert bb.c1[idx] > bb.lo1[idx] and bb.c2[idx] <= bb.lo2[idx] and bb.c1[idx] > bb.o1[idx]
    assert bb.c1[idx] > bb.main1[idx]      # acima da base -> nao e reversao
    assert not buy[idx]


@pytest.mark.parametrize("seed", range(12))
def test_bollinger_take_needs_profit_not_only_the_band_rejection(spec, seed):
    n = 1200
    mb = vol_regime_ticks(n, seed=100 + seed)
    ticks = build_ticks(mb)
    m1, _ = m1_from_ticks(ticks)
    c, o = list(m1.close), list(m1.open)
    main, up, lo = naive_bands(c, 20, 2.0)
    j0 = 300
    entry = round(mb[j0][0] + 1e-4, 5)
    base = [b for b in range(j0 + 1, n) if c[b - 1] < up[b - 1] and c[b - 2] >= up[b - 2] and c[b - 1] < o[b - 1]]
    with_profit = [b for b in base if c[b - 1] > entry]
    res, _ = go(mb, [j0], spec, BandsPeriod=20, BollingerEntryMode=0, TakeBolinger="true", StopBolinger="false",
                Stop=500.0, AtivarTake="false", AtivarBreakeven="false", PositionSizeMode=2, PositionSizeValue=0.1)
    if with_profit:
        t = res.trades.iloc[0]
        assert t.reason == "bollinger_take" and t.close_ms == (T0 + 60 * with_profit[0]) * 1000
    else:
        assert res.trades.empty            # rejeicao da banda SEM lucro nao fecha (mesmo havendo a condicao de banda)
