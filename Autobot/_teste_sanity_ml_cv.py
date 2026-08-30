# -*- coding: utf-8 -*-
"""Confere as propriedades do purge/embargo com dado real (nao so
unitario/sintetico): nenhuma amostra de treino cai dentro do bloco de
validacao+embargo, e nenhuma tem exit_idx que alcance o inicio da
validacao. Uso interno, apagar depois."""
import pandas as pd

import ml_cv as cv

labels = pd.read_parquet("ml_data/XAUUSD_M15_labels.parquet")
df = labels.dropna(subset=["label"]).reset_index(drop=True)
print(f"dataset: {len(df)} amostras validas")

for f, (train_idx, val_idx) in enumerate(cv.purged_walk_forward_splits(df)):
    val_start, val_end = val_idx[0], val_idx[-1] + 1
    embargo_end = min(len(df), val_end + cv.EMBARGO_BARS)

    dentro_do_bloco = set(train_idx) & set(range(val_start, embargo_end))
    exit_vaza = df["exit_idx"].to_numpy()[train_idx]
    vazamento = ((train_idx < embargo_end) & (exit_vaza >= val_start)).sum()

    print(f"fold {f}: val=[{val_start}:{val_end}) embargo_ate={embargo_end} "
          f"| treino={len(train_idx)} | dentro_do_bloco={len(dentro_do_bloco)} "
          f"| ainda_vazando={vazamento}")
    assert not dentro_do_bloco, f"fold {f}: treino invadindo bloco de validacao+embargo"
    assert vazamento == 0, f"fold {f}: treino com exit_idx vazando pra validacao"

print("\nOK: purge+embargo sem vazamento em nenhum dos 6 folds (dado real).")
