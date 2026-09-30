"""Dimensionamento de lote -- espelho de MM_Size_Buy/Sell, MM_SizeMonetary, MM_SizeFixo{Buy,Sell}, MM_Size_R*,
CalculateGridVolume, CalculatePyramidVolume e helpers (ClampMartingaleLot, NormalizeRiskVolume...).

Todas recebem `sim` (estado da simulacao) e devolvem o lote PEDIDO; `myOrderSend` ainda aplica
NormalizeTradeVolume depois (ver sim.send_market). 0.0 = o EA nao abre a ordem.
"""
from __future__ import annotations

import math

from .spec import SymbolSpec


# ------------------------------------------------------------------ normalizacao de volume
def normalize_risk_volume(volume: float, spec: SymbolSpec, max_rel_min: float) -> float:
    """NormalizeRiskVolume(): piso no passo; abaixo do minimo promove ao minimo, exceto se estourar o guarda."""
    if volume <= 0.0 or spec.volume_min <= 0.0 or spec.volume_max < spec.volume_min or spec.volume_step <= 0.0:
        return 0.0
    bounded = min(volume, spec.volume_max)
    norm = math.floor(bounded / spec.volume_step + 1e-9) * spec.volume_step
    if norm < spec.volume_min:
        if max_rel_min > 0.0 and volume > 0.0 and spec.volume_min / volume > max_rel_min:
            return 0.0
        norm = spec.volume_min
    return round(norm, 8)


def normalize_trade_volume(volume: float, spec: SymbolSpec) -> float:
    """NormalizeTradeVolume(): clamp [min,max] e piso no passo."""
    if volume <= 0.0 or spec.volume_min <= 0.0 or spec.volume_max < spec.volume_min or spec.volume_step <= 0.0:
        return 0.0
    bounded = min(max(volume, spec.volume_min), spec.volume_max)
    norm = math.floor(bounded / spec.volume_step + 1e-9) * spec.volume_step
    if norm < spec.volume_min:
        norm = spec.volume_min
    return round(norm, 8)


def normalize_trade_volume_nearest(volume: float, spec: SymbolSpec) -> float:
    """NormalizeTradeVolumeNearest(): como acima mas arredonda ao passo MAIS PROXIMO (usado so no grid)."""
    if volume <= 0.0 or spec.volume_min <= 0.0 or spec.volume_max < spec.volume_min or spec.volume_step <= 0.0:
        return 0.0
    bounded = min(max(volume, spec.volume_min), spec.volume_max)
    norm = round(bounded / spec.volume_step) * spec.volume_step
    if norm < spec.volume_min:
        norm = spec.volume_min
    return round(norm, 8)


def lot_digits(step: float) -> int:
    if round(step, 3) == round(step):
        return 0
    if round(10 * step, 3) == round(10 * step):
        return 1
    if round(100 * step, 3) == round(100 * step):
        return 2
    return 3


def clamp_martingale_lot(sim, lots: float, base_lot: float, side: int) -> float:
    """ClampMartingaleLot(): apos estourar MaxMartingaleSteps volta ao lote base; teto MaxMartingaleLot."""
    if sim.L.rec[side].force_base_next:
        return base_lot
    cap = sim.p.v["MaxMartingaleLot"]
    if cap > 0.0 and lots > cap:
        lots = cap
    return lots


# ------------------------------------------------------------------ Fixed-R
def size_fixed_r(sl_dist: float, valor_r: float, p, spec: SymbolSpec) -> float:
    """MM_Size_R() sem recovery."""
    if spec.tick_size <= 0.0 or spec.tick_value <= 0.0 or sl_dist <= 0.0 or valor_r <= 0.0:
        return 0.0
    budget = valor_r
    if p.max_risco_r > 0.0:
        budget = min(budget, p.max_risco_r * valor_r)
    lots = normalize_risk_volume(budget / ((sl_dist / spec.tick_size) * spec.tick_value), spec, p.max_risco_rel_min)
    if lots < spec.volume_min:
        return 0.0
    return min(lots, spec.volume_max)


def size_fixed_r_side(sim, is_buy: bool, sl_dist: float) -> float:
    """MM_Size_R_Buy/Sell(): lote-base de 1R + recovery de Martingale medido em R."""
    p, spec, L = sim.p, sim.spec, sim.L
    base = size_fixed_r(sl_dist, sim.valor_r, p, spec)
    if not sim.martingale or base <= 0.0:
        return base
    side = 1 if is_buy else -1
    tick_size, tick_value = spec.tick_size, spec.tick_value
    outstanding = L.rec[side].outstanding
    has_take = p.use_take
    lots = base
    if has_take:
        atr_v = sim.atr_snap(p.vela_take)
        atr_v = atr_v if atr_v != 0 else tick_size
        target = abs(-outstanding) * p.v["Multiplicador"]
        tp_points = round(atr_v / tick_size) * p.take
        tp_value = tp_points * tick_value if tp_points > 0 else tick_value
        lots = max(base, target / tp_value) if outstanding > 0 else base
    else:
        rec_lots = abs(-outstanding) * p.v["Multiplicador"] / ((sl_dist / tick_size) * tick_value)
        lots = max(base, rec_lots)
    lots = clamp_martingale_lot(sim, lots, base, side)
    if p.max_risco_r > 0:
        lots = min(lots, p.max_risco_r * sim.valor_r / ((sl_dist / tick_size) * tick_value))
    lots = normalize_risk_volume(lots, spec, p.max_risco_rel_min)
    if lots < spec.volume_min:
        return 0.0
    return min(lots, spec.volume_max)


# ------------------------------------------------------------------ Percentage
def size_percentage(sim, is_buy: bool, sl_dist: float) -> float:
    """MM_Size_Buy/Sell(): % do capital efetivo (saldo AO VIVO x TradeCapitalPercentage) pelo risco do SL."""
    p, spec = sim.p, sim.spec
    tick_size, tick_value = spec.tick_size, spec.tick_value
    bal = sim.eff_capital()
    if tick_size <= 0.0 or tick_value <= 0.0 or sl_dist <= 0.0:
        return 0.0
    lots = p.size_value / 100.0 * bal / ((sl_dist / tick_size) * tick_value)
    if lots < spec.volume_min:
        return 0.0
    initial = lots
    if sim.martingale:
        side = 1 if is_buy else -1
        outstanding = sim.L.rec[side].outstanding
        mult = p.v["Multiplicador"]
        if p.use_take:
            atr_v = sim.atr_snap(p.vela_take)
            atr_v = atr_v if atr_v != 0 else tick_size
            target = abs(-outstanding) * mult
            tp_points = round(atr_v / tick_size) * p.take
            tp_value = tp_points * tick_value if tp_points > 0 else tick_value
            lots_m = max(initial, target / tp_value) if outstanding > 0 else initial
            lots_m = clamp_martingale_lot(sim, lots_m, initial, side)
        else:
            loss_pct = abs(-outstanding * mult / bal) * 100.0 if bal > 0 else 0
            lots_m = loss_pct / 100.0 * bal / ((sl_dist / tick_size) * tick_value)
            if lots_m < lots:
                lots_m = lots
            lots_m = clamp_martingale_lot(sim, lots_m, lots, side)
        if lots_m < spec.volume_min:
            return 0.0
        return min(lots_m, spec.volume_max)
    lots = min(lots, spec.volume_max)
    return lots if lots >= spec.volume_min else 0.0


# ------------------------------------------------------------------ Monetary
def size_monetary(sim, is_buy: bool) -> float:
    """MM_SizeMonetary(): N lotes por PositionSizeValue de capital INICIAL (base fixa), + recovery."""
    p, spec = sim.p, sim.spec
    base = sim.eff_initial / p.size_value
    lots = base
    if sim.martingale:
        side = 1 if is_buy else -1
        mult = p.v["Multiplicador"]
        if p.use_take:
            outstanding = -sim.L.rec[side].outstanding        # negativo quando ha divida
            atr_v = sim.atr_snap(p.vela_take)
            tick_size, tick_value = spec.tick_size, spec.tick_value
            if outstanding < 0.0 and tick_size > 0.0 and tick_value > 0.0 and atr_v > 0.0:
                tp_ticks = round(atr_v / tick_size) * p.take
                ppl = tp_ticks * tick_value
                if ppl > 0.0:
                    lots = max(base, abs(outstanding) * mult / ppl)
        else:
            op = sim.L.last_closed(side)
            if op is not None and op.net < 0.0 and op.volume > 0.0:
                lots = max(base, op.volume * mult)
        lots = clamp_martingale_lot(sim, lots, base, side)
    lots = min(lots, spec.volume_max)
    return max(lots, spec.volume_min)


# ------------------------------------------------------------------ Fixed lot (+ Martingale / D'Alembert)
def size_fixed_lot(sim, is_buy: bool) -> float:
    p, spec = sim.p, sim.spec
    base = p.size_value
    side = 1 if is_buy else -1
    lots = base
    if sim.dalembert:
        lots = base + sim.L.dal[side] * p.v["DAlembertStep"]
        cap = p.v["MaxMartingaleLot"]
        if cap > 0.0:
            lots = min(lots, cap)
    elif sim.martingale:
        op = sim.L.last_closed(side)
        if op is not None and op.net < 0.0 and op.volume > 0.0:
            lots = op.volume * p.v["Multiplicador"]
        lots = clamp_martingale_lot(sim, lots, base, side)
    lots = min(lots, spec.volume_max)
    lots = max(lots, spec.volume_min)
    return round(lots, sim.lot_digits)


# ------------------------------------------------------------------ Grid classico / Piramide
def grid_profit_per_lot(sim, is_buy: bool, tick) -> float:
    """GridProfitPerLot(): lucro de 1 lote ate a distancia ATR[VelaTake]*Take a partir do preco de entrada."""
    p, spec = sim.p, sim.spec
    distance = sim.atr_snap(p.vela_take) * p.take
    if distance <= 0.0:
        return 0.0
    bid, ask = tick
    open_price = ask if is_buy else bid
    target = open_price + distance if is_buy else open_price - distance
    target = spec.price_to_tick(target, is_buy)
    return abs(spec.profit(is_buy, 1.0, open_price, target))


def grid_volume(sim, is_buy: bool, fixed: bool, tick) -> float:
    """CalculateGridVolume(): lote-base, ou o necessario para fechar o alvo do ciclo no proximo nivel."""
    p, spec = sim.p, sim.spec
    base = p.size_value if fixed else sim.eff_initial / p.size_value
    side = 1 if is_buy else -1
    g = sim.L.grid[side]
    cycle_pnl = g.realized + sim.total_open_profit(side, tick)
    lots = base
    if g.cycle_start > 0 and g.target > cycle_pnl:
        ppl = grid_profit_per_lot(sim, is_buy, tick)
        if ppl > 0.0:
            lots = max(base, (g.target - cycle_pnl) / ppl)
    cap = p.v["MaxMartingaleLot"]
    if cap > 0.0:
        lots = min(lots, cap)
    return normalize_trade_volume_nearest(lots, spec)


def pyramid_volume(sim, is_buy: bool, fixed: bool) -> float:
    """CalculatePyramidVolume(): progressao geometrica ultimo_lote x Multiplicador."""
    p, spec = sim.p, sim.spec
    mode = p.size_mode
    sl_dist = 0.0
    if mode in (3, 0):
        sl_dist = sim.atr_snap(p.vela_stop) * p.stop
        base = size_fixed_r_side(sim, is_buy, sl_dist) if mode == 3 else size_percentage(sim, is_buy, sl_dist)
    else:
        base = p.size_value if fixed else sim.eff_initial / p.size_value
    side = 1 if is_buy else -1
    last = sim.L.last_trade(side)
    if last is None or last.volume <= 0.0:
        return normalize_trade_volume(base, spec)
    lots = last.volume * p.v["Multiplicador"]
    cap = p.v["MaxMartingaleLot"]
    if cap > 0.0:
        lots = min(lots, cap)
    if mode == 3 and p.max_risco_r > 0.0 and sl_dist > 0.0:
        lots = min(lots, p.max_risco_r * sim.valor_r / ((sl_dist / spec.tick_size) * spec.tick_value))
    return normalize_trade_volume(max(lots, 0.0), spec)
