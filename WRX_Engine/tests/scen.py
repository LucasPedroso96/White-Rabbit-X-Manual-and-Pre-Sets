"""Cenarios de precos construidos a mao (resultado de cada trade controlado por saltos de +-0.05)."""
from conftest import base_path, build_ticks, make_params  # noqa: F401
from wrx_engine.engine import run_backtest

WARM = 130


def ref_atr0(minute_bids, upto_minute, period=14):
    bars = [(b[0], max(b), min(b), b[-1]) for b in minute_bids[:upto_minute]]
    bars.append((minute_bids[upto_minute][0],) * 4)
    tr = []
    for i in range(1, len(bars)):
        _, h, l, _ = bars[i]
        pc = bars[i - 1][3]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(tr[-period:]) / period


def script(outcomes, side="buy", warm=WARM, gap=6, jump=0.05, noisy_gap=False):
    """Uma entrada por resultado ('tp' ou 'sl'); devolve (minutos, [indice do minuto de cada entrada])."""
    mb = base_path(warm, step=0.0002)
    ents = []
    for o in outcomes:
        e = mb[-1][-1]
        ents.append(len(mb))
        mb.append([e] * 4)
        up = (o == "tp") == (side == "buy")
        mb.append([e + (jump if up else -jump)] * 4)
        mb.append([e] * 4)
        if noisy_gap:
            mb.extend(base_path(gap, seed=len(mb), step=0.0002, start=e))     # ATR nao pode zerar em intervalos longos
        else:
            mb.extend([[e] * 4 for _ in range(gap)])
    return mb, ents


def go(mb, ents, spec, side="buy", kw=None, **over):
    kw = kw or {}
    """Roda com sinal forcado nos minutos `ents`."""
    ticks = build_ticks(mb)
    p = make_params(**over)
    es = set(ents)
    hook = lambda j, b: ((side == "buy") and j in es, (side == "sell") and j in es)   # noqa: E731
    return run_backtest(p, spec, ticks, signal_hook=hook, **kw), p
