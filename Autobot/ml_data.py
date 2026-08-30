# -*- coding: utf-8 -*-
"""Coleta de candles para o piloto de ML (metodologia Zeus, ver plano
2026-08-30) -- so busca e cacheia dado, nunca calcula feature nem toca
modelo. Mesmo split de responsabilidade do data.py do Zeus: o resto do
pipeline (ml_features.py em diante) nunca precisa de conexao ao terminal,
so le o parquet cacheado aqui.

Fonte: pacote MetaTrader5 (Python), conectado ao terminal REAL -- mesmo
mecanismo ja usado em calc_capital_base.py/descobrir_ativos.py, nao
export do Strategy Tester. M15 (grao da entrada travada no 12_GRID_INVERSO
campeao, TimeFrame=2 no set) + H1 (contexto de tendencia, mesmo par de
timeframes do Zeus).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import wrx_paths
from mt5_runner import fechar_terminal, garantir_terminal_livre

AQUI = Path(__file__).resolve().parent
DADOS_DIR = AQUI / "ml_data"
DADOS_DIR.mkdir(exist_ok=True)

SYMBOL = "XAUUSD"
N_M15_BARS = 60_000
COLUNAS = ["time", "open", "high", "low", "close", "tick_volume", "spread"]


def resolve_symbol(mt5, symbol: str = SYMBOL) -> str:
    """Resolve o nome real do simbolo no broker, tolerante a sufixo --
    mesma logica de resolucao por radical que optimize_sets.achar_set()
    ja usa pra sets (XAUUSD -> XAUUSD.o/.raw/etc, prefere o mais curto)."""
    todos = mt5.symbols_get()
    nomes = {s.name for s in todos} if todos else set()
    if symbol in nomes:
        mt5.symbol_select(symbol, True)
        return symbol
    candidatos = [n for n in nomes if n.startswith(symbol)]
    if not candidatos:
        raise RuntimeError(f"simbolo {symbol!r} (nem variantes) nao existe neste terminal")
    resolvido = min(candidatos, key=len)
    mt5.symbol_select(resolvido, True)
    return resolvido


def fetch_rates(mt5, symbol: str, timeframe, n_bars: int) -> pd.DataFrame:
    barras = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
    if barras is None or len(barras) == 0:
        raise RuntimeError(f"sem candles pra {symbol} ({mt5.last_error()})")
    df = pd.DataFrame(barras)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[COLUNAS]


def load_and_cache(n_m15_bars: int = N_M15_BARS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Busca M15+H1, cacheia em parquet, devolve os DataFrames. H1 pede
    n_m15_bars/4 + 500 barras -- cobre o MESMO periodo do M15 com folga
    de warm-up (mesma conta do data.py do Zeus)."""
    import MetaTrader5 as mt5

    garantir_terminal_livre(fechar=True)
    if not mt5.initialize(path=str(wrx_paths.terminal_exe())):
        raise SystemExit(f"Nao consegui conectar ao MT5: {mt5.last_error()}")
    try:
        simbolo = resolve_symbol(mt5)
        print(f"simbolo resolvido: {simbolo}", flush=True)
        m15 = fetch_rates(mt5, simbolo, mt5.TIMEFRAME_M15, n_m15_bars)
        n_h1 = n_m15_bars // 4 + 500
        h1 = fetch_rates(mt5, simbolo, mt5.TIMEFRAME_H1, n_h1)
        print(f"M15: {len(m15)} barras ({m15['time'].min()} a {m15['time'].max()})", flush=True)
        print(f"H1:  {len(h1)} barras ({h1['time'].min()} a {h1['time'].max()})", flush=True)
    finally:
        mt5.shutdown()
        fechar_terminal()

    m15.to_parquet(DADOS_DIR / f"{SYMBOL}_M15.parquet")
    h1.to_parquet(DADOS_DIR / f"{SYMBOL}_H1.parquet")
    return m15, h1


if __name__ == "__main__":
    load_and_cache()
