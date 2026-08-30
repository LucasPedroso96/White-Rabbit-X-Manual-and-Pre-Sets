# -*- coding: utf-8 -*-
"""CV Purgado com Embargo, PORTE LITERAL do cv.py do Zeus (ver plano
2026-08-30): CV k-fold padrao vaza informacao aqui porque o label de uma
amostra de treino depende de ate TB_N barras futuras (o horizonte do
triple-barrier). Uma amostra de treino cuja janela de label sobrepoe o
intervalo de tempo de uma amostra de validacao efetivamente "ve" price
action do periodo de validacao. Cada fold remove essas amostras de treino
sobrepostas (purge) mais uma janela extra de embargo logo apos o fold de
validacao.

Requer `df` com colunas `time`, `exit_idx`, ja filtrado a linhas com label
nao-nulo, indice posicional resetado (0..n-1) -- mesmo contrato do Zeus.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd

CV_FOLDS = 6
EMBARGO_BARS = 24  # = TB_N (ml_labeling.py)


def purged_walk_forward_splits(df: pd.DataFrame, n_folds: int = CV_FOLDS,
                               embargo_bars: int = EMBARGO_BARS
                               ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    n = len(df)
    all_idx = np.arange(n)
    exit_idx = df["exit_idx"].to_numpy()
    fold_bounds = np.linspace(0, n, n_folds + 1, dtype=int)

    for f in range(n_folds):
        val_start, val_end = fold_bounds[f], fold_bounds[f + 1]
        val_idx = all_idx[val_start:val_end]
        embargo_end = min(n, val_end + embargo_bars)

        excluded = np.zeros(n, dtype=bool)
        excluded[val_start:embargo_end] = True
        overlaps = (all_idx < embargo_end) & (exit_idx >= val_start)
        excluded |= overlaps

        train_idx = all_idx[~excluded]
        yield train_idx, val_idx
