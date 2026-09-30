import numpy as np

from conftest import T0, epoch
from wrx_engine.bars import Bars, Ticks, floor_tf, forming_partial, m1_from_ticks, resample


def test_m1_from_bid_and_first_tick_index():
    t = np.array([0, 20_000, 59_000, 60_000, 90_000]) + T0 * 1000
    bid = np.array([1.0, 1.2, 0.9, 1.1, 1.3])
    bars, first = m1_from_ticks(Ticks(t, bid, bid + 0.0001))
    assert list(first) == [0, 3]
    assert (bars.open[0], bars.high[0], bars.low[0], bars.close[0]) == (1.0, 1.2, 0.9, 0.9)
    assert (bars.open[1], bars.high[1], bars.low[1], bars.close[1]) == (1.1, 1.3, 1.1, 1.3)


def test_resample_m5_and_weekly_alignment():
    times = T0 + 60 * np.arange(10)
    m1 = Bars(times, np.arange(10.0), np.arange(10.0) + 1, np.arange(10.0) - 1, np.arange(10.0) + 0.5)
    m5 = resample(m1, 5)
    assert len(m5) == 2 and m5.high[0] == 5.0 and m5.low[0] == -1.0 and m5.close[0] == 4.5
    sunday = epoch(2026, 3, 1)
    saturday = sunday - 3600
    assert floor_tf(np.array([sunday + 5 * 3600]), 10080)[0] == sunday
    assert floor_tf(np.array([saturday]), 10080)[0] == sunday - 7 * 86400


def test_forming_partial_accumulates_only_the_same_bigger_bar():
    times = T0 + 60 * np.arange(7)           # T0 = 09:00 -> M5 abre 09:00 e 09:05
    h = np.array([5.0, 7, 6, 6, 6, 9, 9])
    l = np.array([4.0, 3, 4, 4, 4, 8, 8])
    m1 = Bars(times, h - 0.5, h, l, h - 0.5)
    first_bid = np.array([4.5, 5, 5, 5, 5, 8.5, 8.6])
    hi, lo, cl = forming_partial(m1, 5, first_bid)
    assert hi[0] == 4.5 and lo[0] == 4.5           # 1a M1 da barra: so o proprio tick
    assert hi[2] == 7.0 and lo[2] == 3.0           # inclui M1 anteriores (7 e 3), nao a propria M1
    assert hi[5] == 8.5 and lo[5] == 8.5           # barra M5 nova reinicia
    assert hi[6] == 9.0 and lo[6] == 8.0
