"""Simulador por tick do White Rabbit X -- passo 1: 01_SLTP + MACD, lote Fixed-R.

Como o EA realmente roda (lido de OnTick/ProcessNewBar do .mq5):
  * DECIDE uma vez por barra M1, no PRIMEIRO tick do minuto (OnTick retorna se a barra M1
    nao mudou). Sinal so e avaliado na 1a decisao de cada barra do TimeFrame de entrada.
  * O sinal olha barras FECHADAS (shift 1..3). Ja `ATR[0]` (VelaStop/VelaTake = 0) e o ATR
    da barra que esta FORMANDO -- no 1o tick do minuto, uma barra parcial (ver bars.forming_partial).
  * Entrada a mercado no ask/bid desse tick, com SL/TP ja no pedido (myOrderSend).
  * SL/TP ficam na corretora: sao testados a CADA tick. Breakeven so e reavaliado nas
    decisoes (1x por minuto), no bid/ask do 1o tick.

Ordem dentro da decisao (identica ao ProcessNewBar): breakeven BUY -> breakeven SELL ->
sinais -> filtros de dia/hora/spread -> entrada BUY -> entrada SELL.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import indicators as ind
from .bars import Bars, Ticks, forming_partial, m1_from_ticks, resample, tf_index_of
from .setfile import UnsupportedConfig, WrxParams
from .spec import SymbolSpec

COPY_BARS = 50            # `const int CopyBars = 50;` em ProcessNewBar
NEXT_OPEN_AFTER_S = 60    # NextOpenTradeAfterBars(1) * 60s, em myOrderSend
DEFAULT_DEPOSIT = 10_000.0


@dataclass
class _Pos:
    is_buy: bool
    volume: float
    open_price: float
    open_ms: int
    sl: float
    tp: float


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    open_positions: list = field(default_factory=list)
    params: WrxParams | None = None
    spec: SymbolSpec | None = None
    valor_r: float = 0.0
    skipped: dict = field(default_factory=dict)   # contadores: por que uma entrada nao saiu

    def summary(self, deposit: float = DEFAULT_DEPOSIT) -> dict:
        t = self.trades
        if t.empty:
            return {"trades": 0, "net": 0.0, "sum_r": 0.0}
        net = t["net"].to_numpy()
        bal = deposit + np.cumsum(net)
        peak = np.maximum.accumulate(np.concatenate(([deposit], bal)))[1:]
        gp, gl = net[net > 0].sum(), -net[net < 0].sum()
        return {"trades": int(len(t)), "wins": int((net > 0).sum()), "net": float(net.sum()),
                "sum_r": float(t["r"].sum()), "profit_factor": float(gp / gl) if gl > 0 else float("inf"),
                "max_dd_abs": float((peak - bal).max())}


# ---------------------------------------------------------------- sizing / ordens
def normalize_risk_volume(volume: float, spec: SymbolSpec, max_rel_min: float) -> float:
    """NormalizeRiskVolume() do EA: piso no passo; abaixo do minimo promove ao minimo,
    exceto quando o minimo estoura o risco pedido mais que `max_rel_min` vezes."""
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
    """NormalizeTradeVolume() do EA (chamada dentro de myOrderSend)."""
    if volume <= 0.0 or spec.volume_min <= 0.0 or spec.volume_max < spec.volume_min or spec.volume_step <= 0.0:
        return 0.0
    bounded = min(max(volume, spec.volume_min), spec.volume_max)
    norm = math.floor(bounded / spec.volume_step + 1e-9) * spec.volume_step
    if norm < spec.volume_min:
        norm = spec.volume_min
    return round(norm, 8)


def size_fixed_r(sl_dist: float, valor_r: float, params: WrxParams, spec: SymbolSpec) -> float:
    """MM_Size_R() sem recovery."""
    if spec.tick_size <= 0.0 or spec.tick_value <= 0.0 or sl_dist <= 0.0 or valor_r <= 0.0:
        return 0.0
    budget = valor_r
    if params.max_risco_r > 0.0:
        budget = min(budget, params.max_risco_r * valor_r)
    lots = normalize_risk_volume(budget / ((sl_dist / spec.tick_size) * spec.tick_value),
                                 spec, params.max_risco_rel_min)
    if lots < spec.volume_min:
        return 0.0
    return min(lots, spec.volume_max)


def _min_distance_order(spec: SymbolSpec, params: WrxParams) -> float:
    return (spec.stops_level + max(0, params.safety_points)) * spec.point


def _min_distance_modify(spec: SymbolSpec, params: WrxParams, bid: float, ask: float) -> float:
    """ModificationMinimumDistance() do EA."""
    return (max(spec.stops_level, spec.freeze_level) * spec.point + max(0.0, ask - bid)
            + params.safety_points * spec.point)


def _signal_arrays(params: WrxParams, sig_tf: Bars):
    price = ind.applied_price(sig_tf.open, sig_tf.high, sig_tf.low, sig_tf.close, params.applied_price)
    main, sig = ind.macd(price, params.fast, params.slow, params.signal)
    n = len(main)

    def sh(a, k):
        out = np.full(n, np.nan)
        if n > k:
            out[k:] = a[:-k]
        return out

    m1, m2, m3, s1, s2 = sh(main, 1), sh(main, 2), sh(main, 3), sh(sig, 1), sh(sig, 2)
    with np.errstate(invalid="ignore"):
        rev_b, rev_s = (m1 > m2) & (m2 < m3), (m1 < m2) & (m2 > m3)
        sig_b, sig_s = (m1 > s1) & (m2 < s2), (m1 < s1) & (m2 > s2)
        ref_b, ref_s = (m1 > 0.0) & (m2 < 0.0), (m1 < 0.0) & (m2 > 0.0)
    return rev_b, rev_s, sig_b, sig_s, ref_b, ref_s


def _combine(method: int, rev, sg, ref):
    return {0: rev, 1: sg, 2: ref, 3: rev & sg, 4: rev & ref, 5: sg & ref, 6: rev | sg | ref}[method]


# ---------------------------------------------------------------- motor
def run_backtest(params: WrxParams, spec: SymbolSpec, ticks: Ticks, *,
                 warmup_m1: Bars | None = None, stop_fill: str = "level",
                 signal_hook=None) -> BacktestResult:
    """Roda o EA sobre `ticks`.

    warmup_m1: barras M1 ANTERIORES ao 1o tick, para os indicadores ja nascerem aquecidos
      (o Tester tambem tem historico antes da data inicial). Sem isso, as primeiras horas divergem.
    stop_fill: 'level' (SL executa no preco do SL) ou 'tick' (no bid/ask do tick que rompeu).
      E um ponto a CALIBRAR contra o Tester -- a paridade mostra qual bate.
    signal_hook: (j, b) -> (buy_raw, sell_raw); so para testes.
    """
    if params.entry_indicator != 0 or params.size_mode != 3:
        raise UnsupportedConfig(["motor do passo 1 so porta MACD + FixedR"])
    if stop_fill not in ("level", "tick"):
        raise ValueError("stop_fill deve ser 'level' ou 'tick'")
    if len(ticks) == 0:
        return BacktestResult(trades=_trades_frame([]), params=params, spec=spec)

    m1_t, first_idx = m1_from_ticks(ticks)
    nw = 0
    if warmup_m1 is not None and len(warmup_m1):
        keep = warmup_m1.time < m1_t.time[0]
        w = Bars(*(getattr(warmup_m1, f)[keep] for f in ("time", "open", "high", "low", "close")))
        nw = len(w)
        m1 = Bars(*(np.concatenate((getattr(w, f), getattr(m1_t, f))) for f in ("time", "open", "high", "low", "close")))
    else:
        m1 = m1_t
    n_m1 = len(m1)
    first_bid = np.concatenate((m1.open[:nw], ticks.bid[first_idx]))

    sig_tf = resample(m1, params.tf_min)
    atr_tf = sig_tf if params.atr_tf_min == params.tf_min else resample(m1, params.atr_tf_min)
    sb = tf_index_of(m1, sig_tf, params.tf_min)
    ab = tf_index_of(m1, atr_tf, params.atr_tf_min)

    rev_b, rev_s, sig_b, sig_s, ref_b, ref_s = _signal_arrays(params, sig_tf)
    buy_raw_b = _combine(params.entry_method, rev_b, sig_b, ref_b)
    sell_raw_b = _combine(params.entry_method, rev_s, sig_s, ref_s)

    atr_c, tr_c = ind.atr(atr_tf.high, atr_tf.low, atr_tf.close, params.period_atr)
    hi, lo, cl = forming_partial(m1, params.atr_tf_min, first_bid)
    with np.errstate(invalid="ignore"):
        prev_close = np.where(ab >= 1, atr_tf.close[np.maximum(ab - 1, 0)], np.nan)
        tr0 = np.maximum.reduce([hi - lo, np.abs(hi - prev_close), np.abs(lo - prev_close)])
        back = ab - params.period_atr
        tr_back = np.where(back >= 1, tr_c[np.maximum(back, 0)], np.nan)
        atr_prev = np.where(ab >= 1, atr_c[np.maximum(ab - 1, 0)], np.nan)
        atr0 = atr_prev + (tr0 - tr_back) / params.period_atr
    copy_atr = max(COPY_BARS, params.period_baseline_atr)

    def atr_at(idx: int, j: int) -> float:
        if idx < 0 or idx >= copy_atr:
            idx = 0
        if idx == 0:
            return float(atr0[j])
        k = ab[j] - idx
        return float(atr_c[k]) if k >= 0 else float("nan")

    # capital do R (congelado no OnInit)
    base = params.capital_base_r if params.capital_base_r > 0 else DEFAULT_DEPOSIT
    base *= params.trade_capital_pct / 100.0 if 0 < params.trade_capital_pct <= 100 else 1.0
    valor_r = params.size_value / 100.0 * base

    t_ms, bid, ask = ticks.t_ms, ticks.bid, ticks.ask
    n_t = len(t_ms)
    first_tick_of = np.concatenate((np.full(nw, -1, dtype=np.int64), first_idx))

    positions: list[_Pos] = []
    closed: list[dict] = []
    skipped = {"lote_zero": 0, "risco_estourado": 0, "intervalo_minimo": 0, "ordem_sem_sl_tp": 0}
    last_open_s = -10**12
    last_proc_bar = 0

    def close_pos(p: _Pos, i: int, reason: str, price: float):
        gross = spec.profit(p.is_buy, p.volume, p.open_price, price)
        comm = 2.0 * spec.commission_per_lot_side * p.volume
        closed.append({"open_ms": p.open_ms, "close_ms": int(t_ms[i]), "side": "buy" if p.is_buy else "sell",
                       "volume": p.volume, "open_price": p.open_price, "close_price": price,
                       "sl": p.sl, "tp": p.tp, "reason": reason, "gross": gross, "commission": -comm,
                       "net": gross - comm, "r": (gross - comm) / valor_r if valor_r else 0.0})

    def scan(i0: int, i1: int):
        """Testa SL/TP nos ticks i0..i1 (inclusive) para as posicoes abertas."""
        if i0 > i1 or not positions:
            return
        for p in list(positions):
            b_seg, a_seg = bid[i0:i1 + 1], ask[i0:i1 + 1]
            if p.is_buy:
                sl_hit = np.flatnonzero(b_seg <= p.sl) if p.sl > 0 else np.empty(0, int)
                tp_hit = np.flatnonzero(b_seg >= p.tp) if p.tp > 0 else np.empty(0, int)
            else:
                sl_hit = np.flatnonzero(a_seg >= p.sl) if p.sl > 0 else np.empty(0, int)
                tp_hit = np.flatnonzero(a_seg <= p.tp) if p.tp > 0 else np.empty(0, int)
            s = sl_hit[0] if len(sl_hit) else None
            t = tp_hit[0] if len(tp_hit) else None
            if s is None and t is None:
                continue
            if t is None or (s is not None and s <= t):
                i = i0 + int(s)
                px = p.sl if stop_fill == "level" else float((bid if p.is_buy else ask)[i])
                close_pos(p, i, "sl", px)
            else:
                close_pos(p, i0 + int(t), "tp", p.tp)
            positions.remove(p)

    for j in range(nw, n_m1):
        k = int(first_tick_of[j])
        t_now_ms = int(t_ms[k])
        t_s = t_now_ms // 1000
        b_now, a_now = float(bid[k]), float(ask[k])
        b = int(sb[j])

        # ---- dados prontos? (CopyBuffer/CopyClose < bars => ProcessNewBar retorna)
        if not (b + 1 >= COPY_BARS and ab[j] + 1 >= copy_atr):
            scan(k + 1, (int(first_tick_of[j + 1]) if j + 1 < n_m1 else n_t - 1))
            continue

        # ---- breakeven (BUY antes de SELL), 1x por minuto
        if params.use_breakeven and positions:
            _breakeven(positions, params, spec, atr_at, j, b_now, a_now)

        # ---- sinais (so na 1a decisao de cada barra do TF de entrada)
        new_bar = int(sig_tf.time[b]) != last_proc_bar
        if signal_hook is not None:
            rb, rs = signal_hook(j, b)
        else:
            rb, rs = bool(buy_raw_b[b]), bool(sell_raw_b[b])
        raw_buy, raw_sell = new_bar and rb, new_bar and rs
        if new_bar:
            last_proc_bar = int(sig_tf.time[b])

        if _filters_pass(t_s, a_now, b_now, params, spec):
            n_long = sum(p.is_buy for p in positions)
            n_short = len(positions) - n_long
            buy_exposure = (not params.hedging and n_short == 0) or params.hedging
            sell_exposure = (not params.hedging and n_long == 0) or params.hedging
            if raw_buy and buy_exposure and n_long < params.max_long:
                last_open_s = _open(True, positions, params, spec, atr_at, j, b_now, a_now,
                                    t_now_ms, valor_r, last_open_s, skipped)
            if raw_sell and sell_exposure and n_short < params.max_short:
                last_open_s = _open(False, positions, params, spec, atr_at, j, b_now, a_now,
                                    t_now_ms, valor_r, last_open_s, skipped)

        scan(k + 1, (int(first_tick_of[j + 1]) if j + 1 < n_m1 else n_t - 1))

    open_left = [p.__dict__.copy() for p in positions]
    return BacktestResult(trades=_trades_frame(closed), open_positions=open_left, params=params,
                          spec=spec, valor_r=valor_r, skipped=skipped)


def _trades_frame(rows: list[dict]) -> pd.DataFrame:
    cols = ["open_ms", "close_ms", "side", "volume", "open_price", "close_price", "sl", "tp",
            "reason", "gross", "commission", "net", "r"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols).sort_values(["close_ms", "open_ms"]).reset_index(drop=True)


def _filters_pass(t_s: int, ask_: float, bid_: float, params: WrxParams, spec: SymbolSpec) -> bool:
    dow = (t_s // 86400 + 4) % 7                       # MQL: 0=domingo (1970-01-01 foi quinta)
    if not params.days[dow]:
        return False
    minutes = (t_s % 86400) // 60
    a, z = params.tod_from, params.tod_to
    in_window = True if a == z else (a <= minutes < z if a < z else (minutes >= a or minutes < z))
    if not in_window:
        return False
    if params.max_spread > 0 and round((ask_ - bid_) / spec.point) > params.max_spread:
        return False
    return True


def _breakeven(positions, params, spec, atr_at, j, bid_, ask_):
    """ApplyBreakevenForSide() + myOrderModify(): SL -> preco de abertura."""
    for is_buy in (True, False):
        for p in positions:
            if p.is_buy != is_buy:
                continue
            if p.sl > 0 and (round(p.sl, spec.digits) >= round(p.open_price, spec.digits) if is_buy
                             else round(p.sl, spec.digits) <= round(p.open_price, spec.digits)):
                continue
            ref = _be_reference(p, params, atr_at, j)
            if not ref > 0:
                continue
            reached = (bid_ >= p.open_price + ref * params.breakeven_dist) if is_buy \
                else (ask_ <= p.open_price - ref * params.breakeven_dist)
            if not reached:
                continue
            md = _min_distance_modify(spec, params, bid_, ask_)
            new_sl = round(p.open_price, spec.digits)
            if is_buy and bid_ - new_sl < md:
                new_sl = bid_ - md
            if not is_buy and new_sl - ask_ < md:
                new_sl = ask_ + md
            new_sl = spec.price_to_tick(new_sl, round_up=not is_buy)
            # CanModifyPositionStops: recusa se SL ou TP atual esta a <= md do preco
            if is_buy:
                if new_sl > 0 and bid_ - new_sl <= md or p.tp > 0 and p.tp - bid_ <= md:
                    continue
            else:
                if new_sl > 0 and new_sl - ask_ <= md or p.tp > 0 and ask_ - p.tp <= md:
                    continue
            if abs(new_sl - p.sl) <= spec.point:
                continue
            p.sl = new_sl


def _be_reference(p: _Pos, params: WrxParams, atr_at, j: int) -> float:
    """BreakevenReferenceDistance(): distancia do TP (ATR atual x Take) ou, sem TP, a do SL."""
    if params.use_take:
        d = atr_at(params.vela_take, j) * params.take
        if d > 0:
            return d
    if p.sl > 0:
        return (p.open_price - p.sl) if p.is_buy else (p.sl - p.open_price)
    return atr_at(params.vela_stop, j) * params.stop


def _open(is_buy, positions, params, spec, atr_at, j, bid_, ask_, t_ms, valor_r, last_open_s, skipped):
    """OpenBuyOrderRFixo/OpenSellOrderRFixo -> ExecOpenOrder -> myOrderSend. Devolve last_open_s."""
    sl_dist = atr_at(params.vela_stop, j) * params.stop
    tp_dist = atr_at(params.vela_take, j) * params.take if params.use_take else 0.0
    if not sl_dist > 0:
        skipped["ordem_sem_sl_tp"] += 1
        return last_open_s
    vol = size_fixed_r(sl_dist, valor_r, params, spec)
    if vol <= 0:
        skipped["lote_zero"] += 1
        return last_open_s
    vol = normalize_trade_volume(vol, spec)
    t_s = t_ms // 1000
    if t_s - last_open_s < NEXT_OPEN_AFTER_S:
        skipped["intervalo_minimo"] += 1
        return last_open_s
    price = spec.price_to_tick(ask_ if is_buy else bid_, round_up=is_buy)
    md = _min_distance_order(spec, params)
    if is_buy:
        d_sl = price - sl_dist
        if bid_ - d_sl < md:
            d_sl = bid_ - md
        sl = spec.price_to_tick(d_sl, False)
        tp = 0.0
        if tp_dist > 0:
            d_tp = price + tp_dist
            if d_tp - bid_ < md:
                d_tp = bid_ + md
            tp = spec.price_to_tick(d_tp, True)
    else:
        d_sl = price + sl_dist
        if d_sl - ask_ < md:
            d_sl = ask_ + md
        sl = spec.price_to_tick(d_sl, True)
        tp = 0.0
        if tp_dist > 0:
            d_tp = price - tp_dist
            if ask_ - d_tp < md:
                d_tp = ask_ - md
            tp = spec.price_to_tick(d_tp, False)
    if sl <= 0.0 or (tp_dist > 0 and tp <= 0.0):
        skipped["ordem_sem_sl_tp"] += 1
        return last_open_s
    # gate de risco (fixedRRiskCheck): perda projetada no SL vs orcamento de 1R
    projected = abs(spec.profit(is_buy, vol, price, sl))
    budget = valor_r if params.max_risco_r <= 0 else min(valor_r, valor_r * params.max_risco_r)
    at_min = vol <= spec.volume_min + 1e-8
    if not at_min and budget > 0 and projected > budget * 1.001:
        skipped["risco_estourado"] += 1
        return last_open_s
    positions.append(_Pos(is_buy, vol, price, t_ms, sl, tp))
    return t_s
