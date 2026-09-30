"""Ticks e barras, com o alinhamento de tempo do MT5.

Tempos em SEGUNDOS/MILISSEGUNDOS de servidor tratados como UTC (e assim que a API
Python do MT5 devolve): `TimeCurrent()` do EA e o mesmo relogio. Barras M1 saem do
BID, como no Tester. Timeframes maiores saem do M1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TF_MINUTES = (1, 5, 15, 30, 60, 240, 1440, 10080)  # ENUM_ALLOWED_TIMEFRAMES: M1..W1
MN1 = 43200                                        # so aparece como TF superior do filtro MTF
_WEEK = 7 * 86400
_WEEK_OFFSET = 4 * 86400  # 1970-01-01 e quinta; barra semanal do MT5 abre no domingo


@dataclass
class Ticks:
    t_ms: np.ndarray   # int64
    bid: np.ndarray    # float64
    ask: np.ndarray    # float64

    def __post_init__(self):
        self.t_ms = np.asarray(self.t_ms, dtype=np.int64)
        self.bid = np.asarray(self.bid, dtype=np.float64)
        self.ask = np.asarray(self.ask, dtype=np.float64)
        if not (len(self.t_ms) == len(self.bid) == len(self.ask)):
            raise ValueError("ticks: colunas com tamanhos diferentes")
        if len(self.t_ms) > 1 and np.any(np.diff(self.t_ms) < 0):
            raise ValueError("ticks fora de ordem cronologica")

    def __len__(self) -> int:
        return len(self.t_ms)

    @classmethod
    def from_frame(cls, df: pd.DataFrame) -> "Ticks":
        col = "time_msc" if "time_msc" in df.columns else "t_ms"
        return cls(df[col].to_numpy(), df["bid"].to_numpy(), df["ask"].to_numpy())


@dataclass
class Bars:
    time: np.ndarray   # int64, segundos
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray | None = None      # volume de ticks (MFI)

    def __len__(self) -> int:
        return len(self.time)

    @classmethod
    def from_frame(cls, df: pd.DataFrame) -> "Bars":
        vol = df["tick_volume"].to_numpy(float) if "tick_volume" in df.columns else None
        return cls(df["time"].to_numpy(dtype=np.int64), df["open"].to_numpy(float),
                   df["high"].to_numpy(float), df["low"].to_numpy(float),
                   df["close"].to_numpy(float), vol)


def floor_tf(t_sec: np.ndarray, tf_min: int) -> np.ndarray:
    t = np.asarray(t_sec, dtype=np.int64)
    if tf_min == MN1:
        return t.astype("datetime64[s]").astype("datetime64[M]").astype("datetime64[s]").astype(np.int64)
    if tf_min == 10080:
        return ((t + _WEEK_OFFSET) // _WEEK) * _WEEK - _WEEK_OFFSET
    step = tf_min * 60
    return (t // step) * step


def _group_starts(keys: np.ndarray) -> np.ndarray:
    if len(keys) == 0:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate(([0], np.flatnonzero(np.diff(keys) != 0) + 1))


def m1_from_ticks(ticks: Ticks) -> tuple[Bars, np.ndarray]:
    """Barras M1 a partir do BID + indice do primeiro tick de cada barra."""
    keys = floor_tf(ticks.t_ms // 1000, 1)
    starts = _group_starts(keys)
    bid = ticks.bid
    counts = np.diff(np.append(starts, len(bid))).astype(float)
    bars = Bars(time=keys[starts],
                open=bid[starts],
                high=np.maximum.reduceat(bid, starts),
                low=np.minimum.reduceat(bid, starts),
                close=bid[np.append(starts[1:] - 1, len(bid) - 1)],
                volume=counts)
    return bars, starts.astype(np.int64)


def resample(m1: Bars, tf_min: int) -> Bars:
    if tf_min == 1:
        return m1
    keys = floor_tf(m1.time, tf_min)
    starts = _group_starts(keys)
    ends = np.append(starts[1:] - 1, len(keys) - 1)
    vol = np.add.reduceat(m1.volume, starts) if m1.volume is not None else None
    return Bars(time=keys[starts], open=m1.open[starts],
                high=np.maximum.reduceat(m1.high, starts),
                low=np.minimum.reduceat(m1.low, starts),
                close=m1.close[ends], volume=vol)


def tf_index_of(m1: Bars, tf: Bars, tf_min: int) -> np.ndarray:
    """Para cada barra M1: indice da barra de `tf` que a contem (a que esta 'formando')."""
    return np.searchsorted(tf.time, floor_tf(m1.time, tf_min), side="left")


def forming_partial(m1: Bars, tf_min: int, first_bid: np.ndarray):
    """OHLC PARCIAL da barra de `tf_min` no primeiro tick de cada barra M1.

    E o que `ATR[0]` enxerga quando o EA decide no 1o tick do minuto: as barras M1
    anteriores da mesma barra maior + o proprio tick (H=max, L=min, C=tick).
    Devolve (high, low, close) por barra M1.
    """
    keys = floor_tf(m1.time, tf_min)
    df = pd.DataFrame({"k": keys, "h": m1.high, "l": m1.low})
    g = df.groupby("k", sort=False)
    prev_h = g["h"].cummax().groupby(df["k"], sort=False).shift(1).to_numpy()
    prev_l = g["l"].cummin().groupby(df["k"], sort=False).shift(1).to_numpy()
    hi = np.fmax(prev_h, first_bid)
    lo = np.fmin(prev_l, first_bid)
    return hi, lo, np.asarray(first_bid, dtype=float)
