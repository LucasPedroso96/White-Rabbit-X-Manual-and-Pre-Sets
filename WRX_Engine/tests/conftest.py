import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrx_engine.setfile import params_from_text  # noqa: E402
from wrx_engine.spec import SymbolSpec  # noqa: E402
from wrx_engine.bars import Ticks  # noqa: E402

SPREAD = 0.00010
OFFSETS_MS = (0, 15_000, 30_000, 45_000)


def epoch(y, mo, d, h=0, mi=0, s=0) -> int:
    return int(datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc).timestamp())


T0 = epoch(2026, 3, 2, 9, 0)      # segunda-feira 09:00 (servidor)


@pytest.fixture
def spec():
    return SymbolSpec(symbol="EURUSD", digits=5, point=1e-5, tick_size=1e-5, tick_value=1.0,
                      volume_min=0.01, volume_max=100.0, volume_step=0.01, stops_level=0)


def make_params(**over):
    base = {"PositionSizeMode": 3, "PositionSizeValue": 1, "CapitalBaseR": 500, "Stop": 2, "Take": 3,
            "AtivarBreakeven": "false", "MaxLongTrades": 1, "MaxShortTrades": 1, "ReversalExitMode": 0,
            "EntryMethod": 6, "MaxEquityDrawdownPercent": 0, "MinFreeMarginPercent": 0,
            "MACD_SMA": 9, "Fast_EMA": 12, "Slow_EMA": 26}
    base.update(over)
    return params_from_text("\n".join(f"{k}={v}" for k, v in base.items()))


def build_ticks(minute_bids, t0=T0, spread=SPREAD, offsets=OFFSETS_MS):
    """minute_bids: lista (por minuto) de listas de bids; se o minuto tiver <4 ticks, usa os offsets iniciais."""
    t, bid = [], []
    for m, bids in enumerate(minute_bids):
        for off, b in zip(offsets, bids):
            t.append((t0 + 60 * m) * 1000 + off)
            bid.append(b)
    bid = np.round(np.array(bid), 5)
    return Ticks(np.array(t), bid, np.round(bid + spread, 5))


def base_path(n_min, seed=7, start=1.10000, step=0.00004):
    """Caminho deterministico: pequenas oscilacoes com range parecido em todo minuto."""
    rng = np.random.default_rng(seed)
    price, out = start, []
    for _ in range(n_min):
        ticks = []
        for _k in range(4):
            price += rng.normal(0, step)
            ticks.append(round(price, 5))
        out.append(ticks)
    return out
