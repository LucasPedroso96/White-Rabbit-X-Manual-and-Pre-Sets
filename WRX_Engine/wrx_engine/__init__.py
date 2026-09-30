"""White Rabbit X -- motor de backtest proprio (o MT5 so executa ordens).

Porta a semantica do `White Rabbit X (Global Multi-Indicator).mq5` para Python.
Escopo atual (passo 1): 01_SLTP + MACD, lote Fixed-R, SL/TP na abertura, breakeven.
Tudo fora desse escopo e RECUSADO por `setfile.unsupported()` -- nunca ignorado.
"""
from .bars import Bars, Ticks
from .engine import BacktestResult, run_backtest
from .setfile import UnsupportedConfig, WrxParams, load_set
from .spec import SymbolSpec

__all__ = ["Bars", "Ticks", "BacktestResult", "run_backtest", "UnsupportedConfig",
           "WrxParams", "load_set", "SymbolSpec"]
