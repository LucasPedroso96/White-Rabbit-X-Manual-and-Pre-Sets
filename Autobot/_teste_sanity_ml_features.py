# -*- coding: utf-8 -*-
"""Sanity check manual das 13 features sobre dado real cacheado (sem MT5) --
confere ranges plausiveis (ATR positivo e na escala certa de XAUUSD, RSI
0-100, sinais de retorno batendo com a direcao do preco) antes de treinar
em cima. Uso interno, apagar depois."""
import pandas as pd

import ml_features as feats

m15 = pd.read_parquet("ml_data/XAUUSD_M15.parquet")
h1 = pd.read_parquet("ml_data/XAUUSD_H1.parquet")

df = feats.compute_features(m15, h1)
print("linhas:", len(df), "| NaN por coluna (warm-up esperado):")
print(df.isna().sum())

valido = df.dropna()
print(f"\nlinhas validas (pos warm-up): {len(valido)}")
print("\n--- 5 linhas do MEIO do periodo ---")
meio = valido.iloc[len(valido) // 2: len(valido) // 2 + 5]
print(meio.to_string())

print("\n--- ranges (sanity) ---")
for col in feats.FEATURE_NAMES:
    print(f"  {col:<16} min={valido[col].min():>10.4f}  max={valido[col].max():>10.4f}  "
          f"media={valido[col].mean():>10.4f}")

# ATR14 embutido no atr_mom_8/macd -- reconstrui separado so pra ver a
# escala em dolares (XAUUSD M15 costuma ficar na casa de 1-4 USD de ATR).
atr14 = feats.wilder_atr(m15["high"], m15["low"], m15["close"])
print(f"\nATR14 (USD) valido: min={atr14.dropna().min():.3f} "
      f"max={atr14.dropna().max():.3f} media={atr14.dropna().mean():.3f}")

# Sinal de ret_1 bate com a direcao real do preco?
sample = m15.iloc[100:110].copy()
sample["ret_1_manual"] = (sample["close"] / sample["close"].shift(1) - 1)
print("\n--- conferindo sinal de ret_1 manualmente (linhas 100-109) ---")
print(sample[["time", "close", "ret_1_manual"]].to_string())
