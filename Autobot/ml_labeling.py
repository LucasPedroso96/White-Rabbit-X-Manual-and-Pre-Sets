# -*- coding: utf-8 -*-
"""Triple-barrier labeling, PORTE LITERAL do labeling.py do Zeus (ver plano
2026-08-30): pra cada barra i, projeta barreiras em +-k*ATR14[i] e olha ate
n barras a frente; a barreira tocada primeiro decide o label; sem toque ate
o timeout -> neutro. k=1.5, n=24 (~6h em M15) -- mesmos valores do Zeus,
ponto de partida razoavel pro piloto (mesmo ativo, XAUUSD, que o Zeus ja
validou com esses parametros).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml_features import wilder_atr

TB_K = 1.5
TB_N = 24
LABEL_NEUTRAL, LABEL_LONG, LABEL_SHORT = 0, 1, 2


def triple_barrier_labels(m15: pd.DataFrame, k: float = TB_K,
                          n: int = TB_N) -> pd.DataFrame:
    close = m15["close"].to_numpy()
    high = m15["high"].to_numpy()
    low = m15["low"].to_numpy()
    open_ = m15["open"].to_numpy()
    atr = wilder_atr(m15["high"], m15["low"], m15["close"]).to_numpy()

    total = len(m15)
    labels = np.full(total, np.nan)
    exit_idx = np.full(total, -1, dtype=np.int64)

    last_valid_i = total - n - 1
    for i in range(last_valid_i + 1):
        if np.isnan(atr[i]):
            continue
        upper = close[i] + k * atr[i]
        lower = close[i] - k * atr[i]
        label = LABEL_NEUTRAL
        ej = i + n
        for j in range(i + 1, i + n + 1):
            hit_up = high[j] >= upper
            hit_down = low[j] <= lower
            if hit_up and hit_down:
                dist_up = abs(open_[j] - upper)
                dist_down = abs(open_[j] - lower)
                label = LABEL_LONG if dist_up < dist_down else LABEL_SHORT
                ej = j
                break
            if hit_up:
                label = LABEL_LONG
                ej = j
                break
            if hit_down:
                label = LABEL_SHORT
                ej = j
                break
        labels[i] = label
        exit_idx[i] = ej

    out = pd.DataFrame({"time": m15["time"], "label": labels, "exit_idx": exit_idx})
    valido = out["exit_idx"] >= 0
    out.loc[valido, "exit_time"] = m15["time"].to_numpy()[exit_idx[valido]]
    out.loc[~valido, "exit_time"] = pd.NaT
    return out


if __name__ == "__main__":
    m15 = pd.read_parquet("ml_data/XAUUSD_M15.parquet")
    labels = triple_barrier_labels(m15)
    print(labels["label"].value_counts(dropna=False))
    print(f"\n{labels['label'].notna().sum()} labels validos de {len(labels)} barras")
    labels.to_parquet("ml_data/XAUUSD_M15_labels.parquet")
