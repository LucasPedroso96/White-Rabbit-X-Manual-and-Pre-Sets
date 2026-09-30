"""Especificacao do simbolo -- os numeros que o EA le com SymbolInfo*().

Capture-os do MESMO terminal/conta do Tester (tools/export_mt5_data.py). O Tester
usa a especificacao da corretora, entao lote, tick value e custos tem que vir dela.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SymbolSpec:
    symbol: str
    digits: int
    point: float
    tick_size: float
    tick_value: float          # moeda da conta por tick_size por 1.00 lote
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int = 0       # SYMBOL_TRADE_STOPS_LEVEL, em pontos
    freeze_level: int = 0      # SYMBOL_TRADE_FREEZE_LEVEL, em pontos
    commission_per_lot_side: float = 0.0   # moeda da conta, cobrada na entrada E na saida

    def price_to_tick(self, price: float, round_up: bool) -> float:
        """Espelho de PriceToTick() do EA."""
        import math
        if self.tick_size <= 0.0 or price <= 0.0:
            return 0.0
        units = price / self.tick_size
        r = math.ceil(units - 1e-10) if round_up else math.floor(units + 1e-10)
        return round(r * self.tick_size, self.digits)

    def profit(self, is_buy: bool, volume: float, open_price: float, close_price: float) -> float:
        move = (close_price - open_price) if is_buy else (open_price - close_price)
        return move / self.tick_size * self.tick_value * volume

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "SymbolSpec":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))
