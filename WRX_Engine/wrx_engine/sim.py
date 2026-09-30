"""Nucleo da simulacao: laco de decisoes (1x/minuto) + varredura VETORIZADA de eventos por tick entre elas.

Entre duas decisoes o conjunto de posicoes/ordens e constante, entao tudo que o EA/corretora dispara "a cada tick"
(SL/TP, preenchimento de pendente, alvo monetario do grid, trailing de cesta da piramide, travas de equity,
rollover de swap) e encontrado com numpy sobre o trecho de ticks, tratado o mais cedo, e a busca recomeca.

Ordem dentro de UM tick (MT5): corretora (SL/TP, pendentes) -> OnTick: protecao global -> trava de equity ->
fechamentos por ordem oposta -> cestas de grid/piramide -> (se barra M1 nova) ProcessNewBar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import sizing
from .bars import floor_tf
from .ledger import Ledger, Pend, Pos
from .spec import SymbolSpec

NEXT_OPEN_AFTER_S = 60


@dataclass
class Halt:
    gp_total: bool = False
    gp_daily_day: int = -1          # dia (indice) em que a trava diaria esta ativa
    gp_anchor_day: int = -1
    gp_anchor_eq: float = 0.0
    stopped: bool = False           # tradingStopped (permanente)


class Sim:
    def __init__(self, p, spec: SymbolSpec, ticks, pre, *, deposit: float, stop_fill: str, pending_fill: str,
                 signal_hook, hedging_account: bool, news_events=None, news_currencies=None):
        self.p, self.spec, self.pre = p, spec, pre
        self.t_ms, self.bid, self.ask = ticks.t_ms, ticks.bid, ticks.ask
        self.n_t = len(self.t_ms)
        self.L = Ledger(deposit)
        self.stop_fill, self.pending_fill = stop_fill, pending_fill
        self.hook = signal_hook
        self.hedging_account = hedging_account
        v = p.v
        self.martingale = v["RecoveryMode"] == 1
        self.dalembert = v["RecoveryMode"] == 2
        self.grid_on = v["GridMode"] != 0
        self.pyramid = v["GridMode"] == 3
        self.lot_digits = sizing.lot_digits(spec.volume_step)
        pct = v["TradeCapitalPercentage"]
        self._pct = pct / 100.0 if 0 < pct <= 100 else 1.0
        self.eff_initial = deposit * self._pct
        self.initial_deposit = self.eff_initial                     # initialDeposit do WFO
        base_r = p.capital_base_r if p.capital_base_r > 0 else deposit
        base_r *= self._pct
        self.valor_r = p.size_value / 100.0 * base_r if p.size_mode == 3 else 0.0
        self.halt = Halt()
        self.skipped = {"lote_zero": 0, "risco_estourado": 0, "intervalo_minimo": 0, "ordem_sem_sl_tp": 0,
                        "margem": 0, "sem_atr": 0}
        self.closed_rows: list[dict] = []
        self.last_j = 0
        self.last_proc_bar = 0
        self.last_trail_bar = {1: 0, -1: 0}
        self.close_opp = {1: False, -1: False}          # g_closeBuyOnOppositeEntry etc (chave = lado a FECHAR)
        self.session_day = -1
        self.bar_times = pre.sig_tf.time
        # dias (indice de dia de servidor por tick) e ticks em que o dia vira
        days = self.t_ms // 86_400_000
        self.day_of = days
        self.day_change = np.flatnonzero(np.diff(days) != 0) + 1 if self.n_t > 1 else np.zeros(0, int)
        # WFO
        self.wfo = None
        self.news_events = news_events or []
        self.news_currencies = news_currencies or []
        self.carencia_dias = 0.0
        self.cesta_inicio = {1: 0, -1: 0}
        self.duracoes: list[float] = []
        self.block_buy = self.block_sell = False
        self.debito_ini = {1: 0, -1: 0}
        self.debito_ate = {1: 0, -1: 0}
        self.withdrawal_made = False
        self.cur_tick = 0

    # ------------------------------------------------------------------ utilidades de conta
    def eff_capital(self) -> float:
        return self.L.balance * self._pct

    def atr_snap(self, idx: int) -> float:
        """SafeIndex(ATR, idx) com o ATR copiado no ULTIMO ProcessNewBar."""
        return self.pre.atr_at(idx, self.last_j)

    def tick(self, i: int):
        return float(self.bid[i]), float(self.ask[i])

    def pos_profit(self, pos: Pos, bid: float, ask: float) -> float:
        px = bid if pos.is_buy else ask
        return self.spec.profit(pos.is_buy, pos.volume, pos.open_price, px)

    def total_open_profit(self, side: int, tick) -> float:
        """TotalOpenProfit(direction): side 0 = tudo; inclui swap."""
        bid, ask = tick
        s = 0.0
        for p in self.L.positions:
            if side > 0 and not p.is_buy or side < 0 and p.is_buy:
                continue
            s += self.pos_profit(p, bid, ask) + p.swap
        return s

    def float_array(self, i0: int, i1: int, side: int = 0, positions=None) -> np.ndarray:
        """Lucro flutuante (profit+swap) por tick no trecho [i0,i1] das posicoes abertas."""
        n = i1 - i0 + 1
        out = np.zeros(n)
        spec = self.spec
        k = spec.tick_value / spec.tick_size
        for p in (positions if positions is not None else self.L.positions):
            if side > 0 and not p.is_buy or side < 0 and p.is_buy:
                continue
            if p.is_buy:
                out += (self.bid[i0:i1 + 1] - p.open_price) * k * p.volume + p.swap
            else:
                out += (p.open_price - self.ask[i0:i1 + 1]) * k * p.volume + p.swap
        return out

    def equity_at(self, i: int) -> float:
        b, a = self.tick(i)
        return self.L.balance + self.total_open_profit(0, (b, a))

    # ------------------------------------------------------------------ margem (opcional)
    def margin_of(self, volume: float, price: float) -> float:
        s = self.spec
        if s.margin_a == 0.0 and s.margin_b == 0.0:
            return 0.0
        return volume * (s.margin_a * price + s.margin_b)

    def used_margin(self, price: float) -> float:
        return sum(self.margin_of(p.volume, price) for p in self.L.positions)

    # ------------------------------------------------------------------ entradas
    def order_price_rounds_up(self, kind: str) -> bool:
        return kind in ("buy", "buy_stop", "sell_limit")

    def send_order(self, kind: str, price_arg: float, volume: float, sl_dist: float, tp_dist: float,
                   apply_sl: bool, tag: str, k: int) -> int:
        """myOrderSend(): devolve ticket (>0) ou 0 se o EA/corretora recusa."""
        p, spec, L = self.p, self.spec, self.L
        t_ms = int(self.t_ms[k])
        t_s = t_ms // 1000
        if t_s - L.last_entry_s < NEXT_OPEN_AFTER_S:
            self.skipped["intervalo_minimo"] += 1
            return 0
        vol = sizing.normalize_trade_volume(volume, spec)
        if vol <= 0.0:
            self.skipped["lote_zero"] += 1
            return 0
        if apply_sl and sl_dist <= 0.0:
            self.skipped["ordem_sem_sl_tp"] += 1
            return 0
        bid, ask = self.tick(k)
        market = kind in ("buy", "sell")
        is_buy = kind.startswith("buy")
        if market:
            price = ask if is_buy else bid
        else:
            if price_arg <= 0.0:
                return 0
            price = price_arg
        price = spec.price_to_tick(price, self.order_price_rounds_up(kind))
        ref_bid = bid if market else price
        ref_ask = ask if market else price
        md = (spec.stops_level + max(0, p.safety_points)) * spec.point
        sl = tp = 0.0
        if apply_sl:
            if is_buy:
                d = price - sl_dist
                if ref_bid - d < md:
                    d = ref_bid - md
                sl = spec.price_to_tick(d, False)
            else:
                d = price + sl_dist
                if d - ref_ask < md:
                    d = ref_ask + md
                sl = spec.price_to_tick(d, True)
            if sl <= 0.0:
                self.skipped["ordem_sem_sl_tp"] += 1
                return 0
        if tp_dist > 0.0:
            if is_buy:
                d = price + tp_dist
                if d - ref_bid < md:
                    d = ref_bid + md
                tp = spec.price_to_tick(d, True)
            else:
                d = price - tp_dist
                if ref_ask - d < md:
                    d = ref_ask - md
                tp = spec.price_to_tick(d, False)
            if tp <= 0.0:
                self.skipped["ordem_sem_sl_tp"] += 1
                return 0
        # gate de risco: Percentage (sem martingale) ou FixedR (sem martingale ou com teto)
        pct_chk = p.size_mode == 0 and not self.martingale
        r_chk = p.size_mode == 3 and (not self.martingale or p.max_risco_r > 0.0)
        if sl > 0.0 and (pct_chk or r_chk):
            projected = abs(spec.profit(is_buy, vol, price, sl))
            if pct_chk:
                budget = self.eff_capital() * p.size_value / 100.0
            elif not self.martingale and not self.pyramid:
                budget = self.valor_r if p.max_risco_r <= 0 else min(self.valor_r, self.valor_r * p.max_risco_r)
            else:
                budget = self.valor_r * p.max_risco_r
            at_min = vol <= spec.volume_min + 1e-8
            if not at_min and budget > 0.0 and projected > budget * 1.001:
                self.skipped["risco_estourado"] += 1
                return 0
        # OrderCheck: margem livre
        if self.spec.margin_a or self.spec.margin_b:
            eq = L.balance + self.total_open_profit(0, (bid, ask))
            need = self.margin_of(vol, price)
            free_after = eq - self.used_margin(price) - need
            if free_after < 0.0:
                self.skipped["margem"] += 1
                return 0
            mf = p.v["MinFreeMarginPercent"]
            if mf > 0.0 and free_after < eq * mf / 100.0:
                self.skipped["margem"] += 1
                return 0
        ticket = L.new_ticket()
        L.last_entry_s = t_s
        if market:
            pos = Pos(ticket, is_buy, vol, price, t_ms, sl, tp, tag)
            self.fill_entry(pos, k)
        else:
            L.pendings.append(Pend(ticket, kind, price, vol, sl, tp, t_ms, tag))
        return ticket

    def fill_entry(self, pos: Pos, k: int) -> None:
        """Deal de ENTRADA: comissao imediata + OnTradeTransaction (grid, piramide, OCO, ordem oposta)."""
        L, p = self.L, self.p
        comm = self.spec.commission_per_lot_side * pos.volume
        pos.commission = comm
        L.realized -= comm
        L.positions.append(pos)
        side = 1 if pos.is_buy else -1
        t_s = int(self.t_ms[k]) // 1000
        L.last_entry_s = max(L.last_entry_s, t_s)
        if p.v["EntryOrderType"] == 3:                                   # OCO: cancela a outra perna
            L.pendings = [o for o in L.pendings if o.is_buy == pos.is_buy]
        if self.pyramid:
            ps = L.pyr[side]
            if ps.cycle_start == 0:
                ps.cycle_start = t_s
                b, a = self.tick(k)
                ps.peak = b if pos.is_buy else a
        if self.grid_on and not self.pyramid:
            g = L.grid[side]
            if g.cycle_start == 0:
                ppl = sizing.grid_profit_per_lot(self, pos.is_buy, self.tick(k))
                if ppl > 0.0:
                    g.cycle_start, g.realized, g.target = t_s, 0.0, 0.0
                    g.seed_order, g.seed_ppl = pos.ticket, ppl
            if g.seed_order == pos.ticket and g.seed_ppl > 0.0:
                g.target += g.seed_ppl * pos.volume * p.v["Multiplicador"]
            if g.cycle_start > 0:
                g.realized += -comm
        if p.v["ReversalExitMode"] == 1:
            self.close_opp[-side] = True

    # ------------------------------------------------------------------ saidas
    def close_position(self, pos: Pos, k: int, reason: str, price: float) -> None:
        L, spec = self.L, self.spec
        gross = spec.profit(pos.is_buy, pos.volume, pos.open_price, price)
        comm_exit = spec.commission_per_lot_side * pos.volume
        net_exit = gross + pos.swap - comm_exit
        L.realized += net_exit
        net_all = net_exit - pos.commission
        t_ms = int(self.t_ms[k])
        side = 1 if pos.is_buy else -1
        L.positions.remove(pos)
        L.close_operation(pos, net_all, t_ms, self.p.v["MaxMartingaleSteps"], self.dalembert)
        if self.grid_on and not self.pyramid and L.grid[side].cycle_start > 0:
            L.grid[side].realized += net_exit
        vr = self.valor_r
        self.closed_rows.append({"open_ms": pos.open_ms, "close_ms": t_ms, "side": "buy" if pos.is_buy else "sell",
                                 "volume": pos.volume, "open_price": pos.open_price, "close_price": price,
                                 "sl": pos.sl, "tp": pos.tp, "reason": reason, "gross": gross,
                                 "commission": -(pos.commission + comm_exit), "swap": pos.swap, "net": net_all,
                                 "r": (net_all / vr) if vr else 0.0})

    def close_side(self, side: int, k: int, reason: str) -> None:
        """myOrderClose(type, 100%): fecha TODAS as posicoes do lado ao preco de mercado do tick."""
        bid, ask = self.tick(k)
        for pos in list(self.L.of_side(side)):
            self.close_position(pos, k, reason, bid if pos.is_buy else ask)

    def close_everything(self, k: int, reason: str) -> None:
        self.close_side(1, k, reason)
        self.close_side(-1, k, reason)
        self.L.pendings.clear()

    def modify_sl(self, pos: Pos, new_sl: float, k: int, new_tp: float = 0.0) -> bool:
        """myOrderModify() + CanModifyPositionStops(): devolve True se o SL mudou."""
        spec, p = self.spec, self.p
        bid, ask = self.tick(k)
        md = (max(spec.stops_level, spec.freeze_level) * spec.point + max(0.0, ask - bid)
              + p.safety_points * spec.point)
        new_sl = round(new_sl, spec.digits)
        if pos.is_buy:
            if new_sl != 0 and bid - new_sl < md:
                new_sl = bid - md
            if new_tp != 0 and new_tp - bid < md:
                new_tp = bid + md
        else:
            if new_sl != 0 and new_sl - ask < md:
                new_sl = ask + md
            if new_tp != 0 and ask - new_tp < md:
                new_tp = ask - md
        if new_sl > 0.0:
            new_sl = spec.price_to_tick(new_sl, round_up=not pos.is_buy)
        if new_tp > 0.0:
            new_tp = spec.price_to_tick(new_tp, round_up=pos.is_buy)
        if new_sl == 0:
            new_sl = pos.sl
        if new_tp == 0:
            new_tp = pos.tp
        safety = md
        if pos.is_buy:
            if new_sl > 0 and bid - new_sl <= safety or pos.tp > 0 and pos.tp - bid <= safety:
                return False
        else:
            if new_sl > 0 and new_sl - ask <= safety or pos.tp > 0 and ask - pos.tp <= safety:
                return False
        if abs(new_sl - pos.sl) <= spec.point and abs(new_tp - pos.tp) <= spec.point:
            return False
        pos.sl, pos.tp = new_sl, new_tp
        return True

    # ================================================================== varredura de eventos por tick
    def swap_per_night(self, pos: Pos) -> float:
        s = self.spec
        pts = s.swap_long if pos.is_buy else s.swap_short
        return pos.volume * pts * s.point / s.tick_size * s.tick_value

    def _srv_events(self, i0: int, i1: int):
        """Primeiro evento de CORRETORA em [i0,i1]: (idx, tipo) com tipo sl/tp/pend/rollover."""
        best = None
        bid, ask = self.bid, self.ask
        for pos in self.L.positions:
            if pos.is_buy:
                sl_hit = np.flatnonzero(bid[i0:i1 + 1] <= pos.sl) if pos.sl > 0 else ()
                tp_hit = np.flatnonzero(bid[i0:i1 + 1] >= pos.tp) if pos.tp > 0 else ()
            else:
                sl_hit = np.flatnonzero(ask[i0:i1 + 1] >= pos.sl) if pos.sl > 0 else ()
                tp_hit = np.flatnonzero(ask[i0:i1 + 1] <= pos.tp) if pos.tp > 0 else ()
            for hits, kind in ((sl_hit, "sl"), (tp_hit, "tp")):
                if len(hits):
                    idx = i0 + int(hits[0])
                    if best is None or idx < best[0]:
                        best = (idx, kind)
        for o in self.L.pendings:
            if o.kind == "buy_stop":
                h = np.flatnonzero(ask[i0:i1 + 1] >= o.price)
            elif o.kind == "buy_limit":
                h = np.flatnonzero(ask[i0:i1 + 1] <= o.price)
            elif o.kind == "sell_stop":
                h = np.flatnonzero(bid[i0:i1 + 1] <= o.price)
            else:
                h = np.flatnonzero(bid[i0:i1 + 1] >= o.price)
            if len(h):
                idx = i0 + int(h[0])
                if best is None or idx < best[0]:
                    best = (idx, "pend")
        if (self.spec.swap_long or self.spec.swap_short) and self.L.positions:
            c = np.searchsorted(self.day_change, i0)
            if c < len(self.day_change) and self.day_change[c] <= i1:
                idx = int(self.day_change[c])
                if best is None or idx < best[0]:
                    best = (idx, "rollover")
        return best

    def _cycles_active(self) -> bool:
        L = self.L
        if self.pyramid:
            return any(L.pyr[s_].cycle_start > 0 for s_ in (1, -1))
        if self.grid_on:
            return any(L.grid[s_].cycle_start > 0 for s_ in (1, -1))
        return False

    def _ea_active(self) -> bool:
        p = self.p.v
        return bool(self.L.positions or any(self.close_opp.values()) or p["Trava_Diaria_Percent"] > 0
                    or p["Trava_Total_Percent"] > 0 or self._cycles_active())

    def _ea_event(self, i0: int, i1: int):
        """Primeiro tick em [i0,i1] onde algum gatilho do OnTick dispara (idx) ou None."""
        L, p, v = self.L, self.p, self.p.v
        if any(self.close_opp.values()):
            return i0
        if self.halt.stopped:
            return i0 if L.positions or L.pendings else None
        gp_on = (v["Trava_Diaria_Percent"] > 0 or v["Trava_Total_Percent"] > 0) and not self.halt.gp_total
        if not L.positions and not gp_on and not self._cycles_active():
            return None
        best = None

        def upd(idx):
            nonlocal best
            if idx is not None and (best is None or idx < best):
                best = idx

        # tick de virada de dia: ancora da protecao global
        if gp_on:
            c = np.searchsorted(self.day_change, i0)
            if c < len(self.day_change) and self.day_change[c] <= i1:
                upd(int(self.day_change[c]))
            if self.halt.gp_anchor_day != int(self.day_of[i0]):
                upd(i0)
        n = i1 - i0 + 1
        flt = self.float_array(i0, i1) if L.positions else np.zeros(n)
        bal = L.balance
        eq = bal + flt
        if gp_on and not self.halt.gp_total:
            lt = v["Trava_Total_Percent"]
            if lt > 0:
                hit = np.flatnonzero(eq <= self.initial_deposit_real * (1 - lt / 100.0) + 1e-12)
                if len(hit):
                    upd(i0 + int(hit[0]))
            ld = v["Trava_Diaria_Percent"]
            if ld > 0 and self.halt.gp_anchor_day == int(self.day_of[i0]) and self.halt.gp_daily_day != self.halt.gp_anchor_day:
                hit = np.flatnonzero(eq <= self.halt.gp_anchor_eq * (1 - ld / 100.0) + 1e-12)
                if len(hit):
                    upd(i0 + int(hit[0]))
        # trava de equity da estrategia (sempre ativa)
        eff = self.eff_initial
        if eff > 0 and not self.halt.stopped:
            closed = L.realized
            if closed <= -eff:
                upd(i0)
            liq_hit = np.flatnonzero(flt <= -eff + 1e-12)
            if len(liq_hit):
                upd(i0 + int(liq_hit[0]))
            dd = v["MaxEquityDrawdownPercent"]
            if dd > 0:
                se = eff + closed + flt
                hit = np.flatnonzero(se <= eff * (1 - dd / 100.0) + 1e-12)
                if len(hit):
                    upd(i0 + int(hit[0]))
        # cestas
        if self.grid_on and not self.pyramid:
            for side in (1, -1):
                g = L.grid[side]
                if g.cycle_start > 0:
                    if L.count(side) == 0:
                        upd(i0)
                    elif g.target > 0:
                        pnl = g.realized + self.float_array(i0, i1, side)
                        hit = np.flatnonzero(pnl >= g.target - 1e-12)
                        if len(hit):
                            upd(i0 + int(hit[0]))
        if self.pyramid:
            for side in (1, -1):
                ps = L.pyr[side]
                if ps.cycle_start > 0:
                    if L.count(side) == 0:
                        upd(i0)
                        continue
                    if not v["AtivarTrailATR"]:
                        continue
                    dist = self.atr_snap(p.v["TrailVela"]) * v["Trail"]
                    if side > 0:
                        peak = np.maximum(ps.peak, np.maximum.accumulate(self.bid[i0:i1 + 1]))
                        stop = peak - dist
                        cond = (self.bid[i0:i1 + 1] <= stop) & (stop > 0)
                    else:
                        base = ps.peak if ps.peak != 0.0 else np.inf
                        peak = np.minimum(base, np.minimum.accumulate(self.ask[i0:i1 + 1]))
                        stop = peak + dist
                        cond = (self.ask[i0:i1 + 1] >= stop) & (stop > 0)
                    if v["PyramidTrailSoLucro"]:
                        cond &= self.float_array(i0, i1, side) > 0.0
                    hit = np.flatnonzero(cond)
                    if len(hit):
                        upd(i0 + int(hit[0]))
        return best

    @property
    def initial_deposit_real(self) -> float:
        return self.L.deposit

    def scan(self, i0: int, i1: int) -> None:
        if i0 > i1:
            return
        srv0 = ea0 = i0
        guard = 0
        while True:
            guard += 1
            if guard > 100000:
                raise RuntimeError("scan: laco de eventos sem progresso")
            srv = self._srv_events(srv0, i1) if (srv0 <= i1 and (self.L.positions or self.L.pendings)) else None
            ea = self._ea_event(ea0, i1) if (ea0 <= i1 and self._ea_active()) else None
            if srv is None and ea is None:
                break
            if srv is not None and (ea is None or srv[0] <= ea):
                idx, kind = srv
                self.update_peaks(ea0, idx)
                self.handle_server(idx, kind)
                srv0 = idx
                ea0 = idx
                self.ea_tick(idx)                   # o OnTick desse tick roda depois da corretora
                ea0 = idx + 1
                srv0 = idx if kind in ("sl", "tp", "pend") else idx + 1
                if kind == "rollover":
                    srv0 = idx + 1
            else:
                self.update_peaks(ea0, ea)
                self.ea_tick(ea)
                ea0 = ea + 1
        self.update_peaks(ea0, i1)

    def update_peaks(self, a: int, b: int) -> None:
        if not self.pyramid or a > b:
            return
        for side in (1, -1):
            ps = self.L.pyr[side]
            if ps.cycle_start > 0 and self.L.count(side) > 0:
                if side > 0:
                    ps.peak = max(ps.peak, float(self.bid[a:b + 1].max()))
                else:
                    m = float(self.ask[a:b + 1].min())
                    ps.peak = m if ps.peak == 0.0 else min(ps.peak, m)

    def handle_server(self, idx: int, kind: str) -> None:
        L = self.L
        bid, ask = self.tick(idx)
        if kind == "rollover":
            dow = int(((self.t_ms[idx] // 1000) // 86400 + 4) % 7)          # dia que ACABOU = dia anterior
            prev_dow = (dow - 1) % 7
            mult = 3 if prev_dow == self.spec.swap_3days else 1
            if prev_dow in (0, 6):
                return                                                     # sem rollover sab/dom
            for pos in L.positions:
                pos.swap += self.swap_per_night(pos) * mult
            return
        if kind in ("sl", "tp"):
            for pos in list(L.positions):
                if pos.is_buy:
                    hit_sl = pos.sl > 0 and bid <= pos.sl
                    hit_tp = pos.tp > 0 and bid >= pos.tp
                else:
                    hit_sl = pos.sl > 0 and ask >= pos.sl
                    hit_tp = pos.tp > 0 and ask <= pos.tp
                if hit_sl:
                    px = pos.sl if self.stop_fill == "level" else (bid if pos.is_buy else ask)
                    self.close_position(pos, idx, "sl", px)
                elif hit_tp:
                    self.close_position(pos, idx, "tp", pos.tp)
            return
        if kind == "pend":
            for o in list(L.pendings):
                trig = ((o.kind == "buy_stop" and ask >= o.price) or (o.kind == "buy_limit" and ask <= o.price)
                        or (o.kind == "sell_stop" and bid <= o.price) or (o.kind == "sell_limit" and bid >= o.price))
                if not trig or o not in L.pendings:
                    continue
                L.pendings.remove(o)
                if self.pending_fill == "tick" and o.kind.endswith("stop"):
                    px = ask if o.is_buy else bid
                else:
                    px = o.price
                self.fill_entry(Pos(o.ticket, o.is_buy, o.volume, px, int(self.t_ms[idx]), o.sl, o.tp, o.tag), idx)

    # ================================================================== rotina de um tick do OnTick
    def ea_tick(self, k: int) -> bool:
        """WR_GP_Enforce -> CheckStopTradingCondition -> fechamentos por ordem oposta -> cestas.
        True = o OnTick retorna aqui (nao chega ao ProcessNewBar)."""
        if self.gp_enforce(k):
            return True
        if self.check_stop_trading(k):
            return True
        for side in (1, -1):
            if self.close_opp[side]:
                self.close_opp[side] = False
                self.close_side(side, k, "opposite_order")
        self.manage_grid_basket(k)
        self.manage_pyramid_basket(k)
        return False

    def gp_enforce(self, k: int) -> bool:
        v = self.p.v
        td, tt = v["Trava_Diaria_Percent"], v["Trava_Total_Percent"]
        if td <= 0 and tt <= 0:
            return False
        h = self.halt
        if h.gp_total:
            return True
        eq = self.equity_at(k)
        init = self.L.deposit
        total_pct = (eq - init) / init * 100.0 if init > 0 else 0.0
        if tt > 0 and total_pct <= -tt:
            h.gp_total = True
            if v["Protecao_Fecha_Posicoes"]:
                self.close_everything(k, "global_total")
            return True
        day = int(self.day_of[k])
        if h.gp_anchor_day != day:
            h.gp_anchor_day, h.gp_anchor_eq = day, eq
            h.gp_daily_day = -1
        if h.gp_daily_day == day:
            return True
        anchor = h.gp_anchor_eq
        daily_pct = (eq - anchor) / anchor * 100.0 if anchor > 0 else 0.0
        if td > 0 and daily_pct <= -td:
            h.gp_daily_day = day
            if v["Protecao_Fecha_Posicoes"]:
                self.close_everything(k, "global_daily")
            return True
        return False

    def check_stop_trading(self, k: int) -> bool:
        h = self.halt
        if h.stopped:
            if self.L.positions or self.L.pendings:
                self.close_everything(k, "equity_stop")
            return True
        eff = self.eff_initial
        if eff <= 0:
            return False
        liquid = self.total_open_profit(0, self.tick(k))
        closed = self.L.realized
        strat = eff + closed + liquid
        dd = self.p.v["MaxEquityDrawdownPercent"]
        if ((dd > 0 and strat <= eff * (1 - dd / 100.0)) or liquid <= -eff or closed <= -eff):
            h.stopped = True
            self.close_everything(k, "equity_stop")
            return True
        return False

    def manage_grid_basket(self, k: int) -> None:
        if not self.grid_on or self.pyramid:
            return
        L = self.L
        tk = self.tick(k)
        for side in (1, -1):
            g = L.grid[side]
            if g.cycle_start <= 0:
                continue
            if L.count(side) == 0:
                L.grid[side] = type(g)()                # HasManagedActiveOrder(): nao ha ordens de mercado em transito
            else:
                pnl = g.realized + self.total_open_profit(side, tk)
                if g.target > 0.0 and pnl >= g.target:
                    self.close_side(side, k, "grid_target")

    def manage_pyramid_basket(self, k: int) -> None:
        if not self.pyramid:
            return
        L, v = self.L, self.p.v
        bid, ask = self.tick(k)
        for side in (1, -1):
            ps = L.pyr[side]
            if ps.cycle_start <= 0:
                continue
            if L.count(side) == 0:
                L.pyr[side] = type(ps)()
                continue
            if side > 0:
                if bid > ps.peak:
                    ps.peak = bid
            else:
                if ps.peak == 0.0 or ask < ps.peak:
                    ps.peak = ask
            if v["AtivarTrailATR"]:
                dist = self.atr_snap(v["TrailVela"]) * v["Trail"]
                ok = (not v["PyramidTrailSoLucro"]) or self.total_open_profit(side, (bid, ask)) > 0.0
                if side > 0:
                    stop = ps.peak - dist
                    if stop > 0.0 and bid <= stop and ok:
                        self.close_side(side, k, "pyramid_trail")
                else:
                    stop = ps.peak + dist
                    if stop > 0.0 and ask >= stop and ok:
                        self.close_side(side, k, "pyramid_trail")

    # ================================================================== decisao (OnTick -> ProcessNewBar)
    def in_window(self, t_s: int) -> bool:
        p = self.p
        minutes = (t_s % 86400) // 60
        a, z = p.tod_from, p.tod_to
        return True if a == z else (a <= minutes < z if a < z else (minutes >= a or minutes < z))

    def trade_day_ok(self, t_s: int) -> bool:
        return bool(self.p.days[(t_s // 86400 + 4) % 7])

    def run(self):
        pre = self.pre
        k_prev = None
        for j in range(pre.nw, pre.n_m1):
            k = int(pre.first_tick_of[j])
            self.cur_tick = k
            if k_prev is not None:
                self.scan(k_prev + 1, k)
            self.decide(j, k)
            k_prev = k
        if k_prev is not None:
            self.scan(k_prev + 1, self.n_t - 1)

    def decide(self, j: int, k: int) -> None:
        if self.ea_tick(k):
            return
        if self.wfo is not None:
            self.wfo_step(j, k)
        self.process_new_bar(j, k)

    # ------------------------------------------------------------------ WFO (OnTick, antes do ProcessNewBar)
    def wfo_step(self, j: int, k: int) -> None:
        w, L = self.wfo, self.L
        bar_t = int(self.pre.m1.time[j])
        self.block_buy = self.block_sell = False
        nominal_is = w.in_sample(bar_t)
        carencia = False
        enable = self.p.v["MetodoDeEntradawfo"] == 0
        if self.grid_on and enable:
            self.carencia_registrar(bar_t)
        carencia = enable and self.grid_on and nominal_is and self.carencia_ativa(bar_t)
        if nominal_is:
            self.withdrawal_made = False
        if not nominal_is and enable:
            if self.grid_on:
                for side in (1, -1):
                    if L.count(side) > 0:
                        if self.debito_ini[side] == 0:
                            self.debito_ini[side] = bar_t
                    elif self.debito_ini[side] > 0:
                        dias = int((bar_t - self.debito_ini[side]) // 86400) + 1
                        self.debito_ate[side] = bar_t + dias * 86400
                        self.debito_ini[side] = 0
            if not L.positions and not self.withdrawal_made:
                profit = self.eff_capital() - self.initial_deposit
                if profit > 0:
                    L.withdrawn += profit                     # TesterWithdrawal(profit)
                self.withdrawal_made = True
        self.block_buy = enable and (not nominal_is or carencia or bar_t < self.debito_ate[1])
        self.block_sell = enable and (not nominal_is or carencia or bar_t < self.debito_ate[-1])

    def carencia_registrar(self, now: int) -> None:
        pct = self.p.v["WFO_CarenciaPercentil"]
        for side in (1, -1):
            abertas = self.L.count(side)
            if abertas > 0 and self.cesta_inicio[side] == 0:
                self.cesta_inicio[side] = now
            elif abertas == 0 and self.cesta_inicio[side] > 0:
                self.duracoes.append((now - self.cesta_inicio[side]) / 86400.0)
                self.cesta_inicio[side] = 0
                k = len(self.duracoes) - 1
                if k + 1 >= 3 and pct > 0:
                    srt = sorted(self.duracoes)
                    idx = int(math.floor(k * min(pct, 100) / 100.0))
                    self.carencia_dias = srt[min(idx, k)]

    def carencia_ativa(self, now: int) -> bool:
        if self.p.v["WFO_CarenciaPercentil"] <= 0 or self.carencia_dias <= 0.0:
            return False
        c, in_is = self.wfo.cycle_of(now)
        if c < 0 or not in_is:
            return False
        janela = (self.wfo.is_end[c] - self.wfo.is_start[c]) / 86400.0
        dias = min(self.carencia_dias, janela / 3.0)
        return (self.wfo.is_end[c] - now) / 86400.0 < dias

    # ------------------------------------------------------------------ valores auxiliares do ProcessNewBar
    def candle_value(self, is_buy: bool, j: int, k: int) -> float:
        """GetCandlestickValue(MetodoDeCalculo, 0): barra do TF de entrada em formacao."""
        m = self.p.v["MetodoDeCalculo"]
        pre = self.pre
        bid, ask = self.tick(k)
        if m == 0:
            return float(pre.f_open[j])
        if m == 1:
            return float(pre.f_close[j])
        if m == 2:
            return float(pre.f_high[j])
        if m == 3:
            return float(pre.f_low[j])
        return bid if is_buy else ask                      # Preco

    def apply_breakeven(self, side: int, j: int, k: int) -> None:
        p, spec = self.p, self.spec
        bid, ask = self.tick(k)
        is_buy = side > 0
        for pos in list(self.L.of_side(side)):
            if pos.sl > 0 and (round(pos.sl, spec.digits) >= round(pos.open_price, spec.digits) if is_buy
                               else round(pos.sl, spec.digits) <= round(pos.open_price, spec.digits)):
                continue
            ref = self.be_reference(pos, j)
            if not ref > 0:
                continue
            reached = (bid >= pos.open_price + ref * p.breakeven_dist) if is_buy \
                else (ask <= pos.open_price - ref * p.breakeven_dist)
            if reached:
                self.modify_sl(pos, pos.open_price, k)

    def be_reference(self, pos: Pos, j: int) -> float:
        p = self.p
        if p.use_take:
            d = self.atr_snap(p.vela_take) * p.take
            if d > 0:
                return d
        if pos.sl > 0:
            return (pos.open_price - pos.sl) if pos.is_buy else (pos.sl - pos.open_price)
        return self.atr_snap(p.vela_stop) * p.stop

    def trailing_set(self, side: int, price: float, k: int) -> None:
        """TrailingStopSet(type, price)."""
        p, spec = self.p, self.spec
        bid, ask = self.tick(k)
        min_step = max(float(spec.stops_level), 1.0) * spec.point
        for pos in list(self.L.of_side(side)):
            if side > 0 and price >= bid:
                continue
            if side < 0 and price <= ask:
                continue
            if p.v["TrailSoLucro"]:
                if side > 0 and price < pos.open_price:
                    continue
                if side < 0 and price > pos.open_price:
                    continue
            worth = (pos.sl == 0 or (side > 0 and price - pos.sl > min_step)
                     or (side < 0 and pos.sl - price > min_step))
            if worth:
                self.modify_sl(pos, price, k)

    def apply_bollinger_be(self, side: int, b: int, k: int) -> None:
        """ApplyBollingerBreakevenForSide(): so no modo Reversal; fecha de volta na base da banda -> SL = abertura."""
        bb, v = self.pre.bb, self.p.v
        if v["BollingerEntryMode"] != 0:
            return
        crossed = (bb.c1[b] >= bb.main1[b]) if side > 0 else (bb.c1[b] <= bb.main1[b])
        if not crossed:
            return
        spec = self.spec
        for pos in list(self.L.of_side(side)):
            if pos.sl > 0 and (round(pos.sl, spec.digits) >= round(pos.open_price, spec.digits) if side > 0
                               else round(pos.sl, spec.digits) <= round(pos.open_price, spec.digits)):
                continue
            self.modify_sl(pos, pos.open_price, k)

    def bollinger_exits(self, side: int, b: int, k: int) -> None:
        """TakeBolinger / StopBolinger (geometria depende do modo de entrada)."""
        bb, v, L = self.pre.bb, self.p.v, self.L
        last = L.last_trade(side)
        if last is None:
            return
        c1, c2, o1 = bb.c1[b], bb.c2[b], bb.o1[b]
        reversal = v["BollingerEntryMode"] == 0
        take, stop = v["TakeBolinger"], v["StopBolinger"]
        if side > 0:
            if reversal:
                if take and c1 < bb.up1[b] and c2 >= bb.up2[b] and c1 < o1 and c1 > last.open_price:
                    self.close_side(1, k, "bollinger_take")
                    return
                if stop and c1 < bb.lo1[b] and c1 < last.open_price:
                    self.close_side(1, k, "bollinger_stop")
            elif stop and c1 < bb.up1[b] and c2 >= bb.up2[b] and c1 < o1:
                self.close_side(1, k, "bollinger_stop")
        else:
            if reversal:
                if take and c1 > bb.lo1[b] and c2 <= bb.lo2[b] and c1 > o1 and c1 < last.open_price:
                    self.close_side(-1, k, "bollinger_take")
                    return
                if stop and c1 > bb.up1[b] and c1 > last.open_price:
                    self.close_side(-1, k, "bollinger_stop")
            elif stop and c1 > bb.lo1[b] and c2 <= bb.lo2[b] and c1 > o1:
                self.close_side(-1, k, "bollinger_stop")

    def check_daily_loss(self, k: int) -> bool:
        """CheckDailyLossLimit(): pior caso do dia (fechado desde a ancora + SL das abertas)."""
        lim = self.p.v["DailyLossLimitPercent"]
        if lim <= 0:
            return False
        d = int(self.day_of[k])
        if getattr(self, "_dl_day", -1) != d:
            self._dl_day = d
            self._dl_anchor = self.eff_capital()
            self._dl_closed0 = self.L.realized
        if self._dl_anchor <= 0:
            return False
        closed_delta = self.L.realized - self._dl_closed0
        worst = closed_delta + self.open_worst_case()
        pct = (self._dl_anchor + worst - self._dl_anchor) / self._dl_anchor * 100.0
        return pct <= -lim

    def open_worst_case(self) -> float:
        p, spec = self.p, self.spec
        tot = 0.0
        for pos in self.L.positions:
            close_px = pos.sl
            if close_px == 0:
                dist = self.atr_snap(p.vela_stop) * p.stop
                if dist <= 0:
                    continue
                close_px = pos.open_price - dist if pos.is_buy else pos.open_price + dist
            tot += spec.profit(pos.is_buy, pos.volume, pos.open_price, close_px)
        return tot

    def check_news(self, t_s: int) -> bool:
        v = self.p.v
        if not v["AtivarFiltroNoticias"] or not self.news_currencies:
            return False
        before, after = v["NewsMinutosAntes"] * 60, v["NewsMinutosDepois"] * 60
        for ts, cur, _imp in self.news_events:
            if cur in self.news_currencies and ts - before <= t_s <= ts + after:
                return True
        return False

    # ------------------------------------------------------------------ pendentes
    def sessao_agora(self, t_s: int) -> bool:
        import datetime as _dt
        d = _dt.datetime.fromtimestamp(t_s, _dt.timezone.utc)
        doy = d.timetuple().tm_yday
        if d.hour != self.p.v["PendingHoraSessao"] or doy == self.session_day:
            return False
        self.session_day = doy
        return True

    def pending_entry_price(self, is_buy: bool, k: int) -> float:
        v, pre = self.p.v, self.pre
        atr = self.atr_snap(0)
        if not atr > 0.0:
            return 0.0
        b = self.cur_b
        as_stop = v["EntryOrderType"] in (1, 3)
        above = as_stop == is_buy
        tf = pre.sig_tf
        if v["PendingReferencia"] == 1:
            ref = tf.high[b - 1] if above else tf.low[b - 1]
        else:
            ref = tf.close[b - 1]
        if v["PendingGatilho"] == 1:
            n = max(1, v["PendingFaixaBarras"])
            ref = tf.high[max(0, b - n):b].max() if above else tf.low[max(0, b - n):b].min()
        if ref <= 0.0:
            return 0.0
        dist = max(0.0, v["PendingDistanciaATR"]) * atr
        level = ref + dist if above else ref - dist
        spec = self.spec
        min_dist = (spec.stops_level + max(0, self.p.safety_points) + 1.0) * spec.point
        bid, ask = self.tick(k)
        market = ask if is_buy else bid
        return max(level, market + min_dist) if above else min(level, market - min_dist)

    def cancel_pendings(self, is_buy: bool | None = None) -> None:
        self.L.pendings = [o for o in self.L.pendings if is_buy is not None and o.is_buy != is_buy]

    def manage_entry_pendings(self, raw_buy: bool, raw_sell: bool, k: int, t_s: int) -> None:
        v, L = self.p.v, self.L
        if v["EntryOrderType"] == 0:
            return
        fora = not self.trade_day_ok(t_s) or not self.in_window(t_s)
        perda = self.check_daily_loss(k)
        for is_buy in (True, False):
            pend = next((o for o in L.pendings if o.is_buy == is_buy), None)
            if pend is None:
                continue
            lt, st = L.count(1), L.count(-1)
            motivo = ""
            if v["EntryOrderType"] == 3 and (st if is_buy else lt) > 0:
                motivo = "OCO other leg filled"
            elif v["EntryOrderType"] != 3 and (raw_sell if is_buy else raw_buy):
                motivo = "opposite signal"
            elif self.block_buy if is_buy else self.block_sell:
                motivo = "WFO entry block"
            elif fora:
                motivo = "outside session"
            elif perda:
                motivo = "daily loss"
            else:
                tf = self.pre.sig_tf
                setup_idx = int(np.searchsorted(
                    tf.time, int(floor_tf(np.array([pend.setup_ms // 1000]), self.p.tf_min)[0])))
                if self.cur_b - setup_idx >= v["PendingExpiracaoBarras"]:
                    motivo = "expired"
            if motivo:
                self.cancel_pendings(is_buy)

    # ------------------------------------------------------------------ abertura
    def exec_open(self, is_buy: bool, sl_dist: float, tp_dist: float, volume: float, tag: str,
                  apply_sl: bool, k: int) -> int:
        """ExecOpenOrder(): mercado, ou pendente para a SEMENTE do lado quando EntryOrderType != Market."""
        v, L = self.p.v, self.L
        eot = v["EntryOrderType"]
        if eot != 0:
            has_pos = L.count(1 if is_buy else -1)
            if has_pos == 0:
                if eot == 3:
                    return self.exec_oco(sl_dist, tp_dist, volume, tag, apply_sl, k)
                if L.pend_count(1 if is_buy else -1) > 0:
                    return 0
                level = self.pending_entry_price(is_buy, k)
                if level <= 0.0:
                    return 0
                kind = ("buy_" if is_buy else "sell_") + ("stop" if eot == 1 else "limit")
                return self.send_order(kind, level, volume, sl_dist, tp_dist, apply_sl, tag + "/Pend", k)
        return self.send_order("buy" if is_buy else "sell", 0.0, volume, sl_dist, tp_dist, apply_sl, tag, k)

    def exec_oco(self, sl_dist, tp_dist, volume, tag, apply_sl, k) -> int:
        L, p = self.L, self.p
        if L.positions or L.pendings:
            return 0
        wants_buy, wants_sell = p.max_long > 0, p.max_short > 0
        before = L.last_entry_s
        buy_t = sell_t = 0
        if wants_buy:
            lv = self.pending_entry_price(True, k)
            if lv > 0.0:
                buy_t = self.send_order("buy_stop", lv, volume, sl_dist, tp_dist, apply_sl, tag + "/OCO", k)
        if wants_sell:
            L.last_entry_s = before
            lv = self.pending_entry_price(False, k)
            if lv > 0.0:
                sell_t = self.send_order("sell_stop", lv, volume, sl_dist, tp_dist, apply_sl, tag + "/OCO", k)
        if wants_buy and wants_sell and ((buy_t == 0) != (sell_t == 0)):
            self.cancel_pendings(None)
            return 0
        return buy_t or sell_t

    def dispatch(self, is_buy: bool, k: int) -> None:
        """DispatchOpenOrder() -> Open{Buy,Sell}Order*()."""
        p, v, L = self.p, self.p.v, self.L
        side = 1 if is_buy else -1
        if L.count(side) >= (p.max_long if is_buy else p.max_short):
            return
        tag = ("Buy" if is_buy else "Sell")
        mode = p.size_mode
        tk = self.tick(k)
        if self.grid_on:
            sl_d = (self.atr_snap(p.vela_stop) * p.stop) if p.use_stop else 0.0
            if self.pyramid:
                vol = sizing.pyramid_volume(self, is_buy, mode == 2)
                if vol <= 0.0:
                    return
                self.exec_open(is_buy, sl_d, 0.0, vol, tag + " / Pyramid", p.use_stop, k)
            else:
                vol = sizing.grid_volume(self, is_buy, mode == 2, tk)
                if vol <= 0.0:
                    return
                g = L.grid[side]
                if g.cycle_start <= 0 and sizing.grid_profit_per_lot(self, is_buy, tk) <= 0.0:
                    return
                self.exec_open(is_buy, sl_d, 0.0, vol, tag + " / Grid", p.use_stop, k)
            return
        atr_sl = self.atr_snap(p.vela_stop)
        atr_tp = self.atr_snap(p.vela_take)
        sl_d = atr_sl * p.stop if (p.use_stop or mode == 3) else 0.0
        tp_d = atr_tp * p.take if p.use_take else 0.0
        if mode == 3:
            if not sl_d > 0:
                self.skipped["sem_atr"] += 1
                return
            vol = sizing.size_fixed_r_side(self, is_buy, sl_d)
            if vol <= 0:
                self.skipped["lote_zero"] += 1
                return
            self.exec_open(is_buy, sl_d, tp_d, vol, tag + "/RFixo", True, k)
        elif mode == 0:
            vol = sizing.size_percentage(self, is_buy, sl_d)
            self.exec_open(is_buy, sl_d, tp_d, vol, tag + "/Porcentagem", p.use_stop, k)
        elif mode == 1:
            self.exec_open(is_buy, sl_d, tp_d, sizing.size_monetary(self, is_buy), tag + "/Monetario", p.use_stop, k)
        else:
            self.exec_open(is_buy, sl_d, tp_d, sizing.size_fixed_lot(self, is_buy), tag + "/LoteFixo", p.use_stop, k)

    def pyramid_last_leg_ready(self, side: int) -> bool:
        last = self.L.last_trade(side)
        if last is None:
            return True
        if last.sl == 0.0:
            return False
        if not self.p.v["PyramidLevelOnlyInProfit"]:
            return True
        return last.sl >= last.open_price if side > 0 else last.sl <= last.open_price

    # ------------------------------------------------------------------ ProcessNewBar
    def process_new_bar(self, j: int, k: int) -> None:
        p, v, L, pre = self.p, self.p.v, self.L, self.pre
        t_ms = int(self.t_ms[k])
        t_s = t_ms // 1000
        bid, ask = self.tick(k)

        # 1) Fecharordensforadohorario -- primeiro comando, roda mesmo sem dados prontos
        if p.close_outside_hours and not self.in_window(t_s):
            self.close_side(1, k, "outside_hours")
            self.close_side(-1, k, "outside_hours")
            self.cancel_pendings(None)

        # 2) dados prontos? (CopyBuffer/CopyClose < bars => retorna)
        b = int(pre.sb[j])
        if not (b + 1 >= 50 and pre.ab[j] + 1 >= pre.copy_atr and pre.flt.ready[j]):
            return
        self.last_j = j
        self.cur_b = b

        # 3) cestas com o ATR recem-copiado
        self.manage_grid_basket(k)
        self.manage_pyramid_basket(k)

        # 4) breakeven / trailing / take organico (BUY antes de SELL)
        for side in (1, -1):
            if p.use_breakeven and L.positions:
                self.apply_breakeven(side, j, k)
            if pre.family == "bollinger" and v["BreakevenBolinger"]:
                self.apply_bollinger_be(side, b, k)
            if v["AtivarTrailATR"]:
                bar = int(pre.sig_tf.time[b])
                if bar != self.last_trail_bar[side]:
                    val = self.candle_value(side > 0, j, k)
                    dist = self.atr_snap(v["TrailVela"]) * v["Trail"]
                    self.trailing_set(side, val - dist if side > 0 else val + dist, k)
                    self.last_trail_bar[side] = bar
            if v["TakeOrganico"]:
                last = L.last_trade(side)
                if last is not None:
                    d = self.atr_snap(p.vela_take) * p.take
                    if (side > 0 and bid > last.open_price + d) or (side < 0 and bid < last.open_price - d):
                        self.close_side(side, k, "take_organico")
            if pre.family == "bollinger":
                self.bollinger_exits(side, b, k)

        # 5) contagens e ancoras do grid
        long_trades, short_trades = L.count(1), L.count(-1)
        had_buy, had_sell = long_trades > 0, short_trades > 0
        last_b, last_s = L.last_trade(1), L.last_trade(-1)
        anchor_b = last_b.open_price if had_buy and last_b else 0.0
        anchor_s = last_s.open_price if had_sell and last_s else 0.0

        # 6) sinais
        new_bar = int(pre.sig_tf.time[b]) != self.last_proc_bar
        if self.hook is not None:
            rb, rs = self.hook(j, b)
        elif pre.buy_j is not None:
            rb, rs = bool(pre.buy_j[j]), bool(pre.sell_j[j])
        else:
            rb, rs = bool(pre.buy_raw[b]), bool(pre.sell_raw[b])
        raw_buy, raw_sell = new_bar and rb, new_bar and rs
        cond_b, cond_s = bool(pre.flt.cond_buy[j]), bool(pre.flt.cond_sell[j])
        buy_entry, sell_entry = raw_buy and cond_b, raw_sell and cond_s
        if v["EntryOrderType"] != 0 and v["PendingGatilho"] == 1:
            ses = self.sessao_agora(t_s)
            raw_buy = raw_sell = False
            buy_entry, sell_entry = ses and cond_b, ses and cond_s
        self.manage_entry_pendings(raw_buy, raw_sell, k, t_s)

        # 7) saida por sinal contrario completo
        if p.reversal_exit_mode == 2:
            buy_exit = raw_sell and (not p.reversal_use_filters or cond_s)
            sell_exit = raw_buy and (not p.reversal_use_filters or cond_b)
            if buy_exit and long_trades > 0:
                self.close_side(1, k, "reversal")
            if sell_exit and short_trades > 0:
                self.close_side(-1, k, "reversal")
        if new_bar:
            self.last_proc_bar = int(pre.sig_tf.time[b])
        long_trades, short_trades = L.count(1), L.count(-1)

        # 8) filtros de agenda / noticias / perda diaria / spread
        if not self.trade_day_ok(t_s) or not self.in_window(t_s):
            return
        if self.check_news(t_s):
            return
        if self.check_daily_loss(k):
            return
        if p.max_spread > 0 and round((ask - bid) / self.spec.point) > p.max_spread:
            return

        buy_exposure = (not p.hedging and short_trades == 0) or p.hedging
        sell_exposure = (not p.hedging and long_trades == 0) or p.hedging
        can_start_buy = (not self.grid_on) or not had_buy
        can_start_sell = (not self.grid_on) or not had_sell
        if buy_entry and can_start_buy and buy_exposure and long_trades < p.max_long and not self.block_buy:
            self.dispatch(True, k)
        if sell_entry and can_start_sell and sell_exposure and short_trades < p.max_short and not self.block_sell:
            self.dispatch(False, k)

        # 9) continuacao do grid / pirâmide
        if self.grid_on:
            dist = self.atr_snap(0) * v["DistanciaMinima"]
            pyr = self.pyramid
            cont_b = (ask > anchor_b + dist) if pyr else (ask < anchor_b - dist)
            cont_s = (bid < anchor_s - dist) if pyr else (bid > anchor_s + dist)
            ready_sig_b = v["UsarsomenteATRGRID"] or raw_buy
            ready_sig_s = v["UsarsomenteATRGRID"] or raw_sell
            if (had_buy and anchor_b > 0.0 and dist > 0.0 and buy_exposure and long_trades < p.max_long and cond_b
                    and ready_sig_b and cont_b and (not pyr or self.pyramid_last_leg_ready(1))):
                self.dispatch(True, k)
            if (had_sell and anchor_s > 0.0 and dist > 0.0 and sell_exposure and short_trades < p.max_short and cond_s
                    and ready_sig_s and cont_s and (not pyr or self.pyramid_last_leg_ready(-1))):
                self.dispatch(False, k)
