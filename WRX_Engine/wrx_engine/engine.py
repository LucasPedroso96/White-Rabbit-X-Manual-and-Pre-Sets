"""Orquestrador do backtest: pre-calculos vetorizados (barras, sinais, filtros, ATR parcial) + `sim.Sim`.

Como o EA realmente roda (lido de OnTick/ProcessNewBar do .mq5):
  * DECIDE uma vez por barra M1, no PRIMEIRO tick do minuto. Sinal so na 1a decisao de cada barra do TimeFrame;
    usa barras FECHADAS (shift 1..3). `ATR[0]` e o ATR da barra em FORMACAO (parcial no 1o tick do minuto).
  * Entrada a mercado no ask/bid desse tick, SL/TP ja no pedido. SL/TP/cestas/travas sao avaliados a CADA tick
    (varredura vetorizada em `sim.py`); breakeven/trailing so nas decisoes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import indicators as ind
from . import signals
from .bars import Bars, Ticks, forming_partial, m1_from_ticks, resample, tf_index_of
from .filters import compute_filters
from .setfile import InvalidConfig, UnsupportedConfig, WrxParams, oninit_errors, unsupported
from .sim import Sim
from .sizing import (normalize_risk_volume, normalize_trade_volume, size_fixed_r)  # noqa: F401 (API publica)
from .spec import SymbolSpec
from .wfo import build_plan

COPY_BARS = 50            # `const int CopyBars = 50;` em ProcessNewBar
NEXT_OPEN_AFTER_S = 60
DEFAULT_DEPOSIT = 10_000.0


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    open_positions: list = field(default_factory=list)
    params: WrxParams | None = None
    spec: SymbolSpec | None = None
    valor_r: float = 0.0
    skipped: dict = field(default_factory=dict)   # contadores: por que uma entrada nao saiu
    ledger: object = None
    sim: object = None

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


@dataclass
class Pre:
    """Tudo que e funcao so dos dados + params (sem estado de conta)."""
    m1: Bars
    nw: int
    n_m1: int
    first_tick_of: np.ndarray
    first_bid: np.ndarray
    sig_tf: Bars
    sb: np.ndarray
    ab: np.ndarray
    buy_raw: np.ndarray
    sell_raw: np.ndarray
    atr_c: np.ndarray
    atr0: np.ndarray
    copy_atr: int
    flt: object
    f_open: np.ndarray
    f_high: np.ndarray
    f_low: np.ndarray
    f_close: np.ndarray
    family: str = "multi"
    bb: object = None                      # BollingerArrays (familia Bollinger)
    buy_j: np.ndarray | None = None        # sinal POR BARRA M1 (familia Candles)
    sell_j: np.ndarray | None = None

    def atr_at(self, idx: int, j: int) -> float:
        """SafeIndex(ATR, idx): 0 = barra em formacao (parcial); k>=1 = k-esima barra fechada."""
        if idx < 0 or idx >= self.copy_atr:
            idx = 0
        if idx == 0:
            return float(self.atr0[j])
        k = self.ab[j] - idx
        return float(self.atr_c[k]) if k >= 0 else float("nan")


def _signal_arrays(params: WrxParams, sig_tf: Bars):
    """Compat: gatilhos brutos (rev, sig, ref) por lado -- ver signals.raw_triggers."""
    es = signals.build_entry_series(params, sig_tf, sig_tf.volume)
    return signals.raw_triggers(params, es)


def _combine(method: int, rev, sg, ref):
    return signals.combine(method, rev, sg, ref)


def _trades_frame(rows: list[dict]) -> pd.DataFrame:
    cols = ["open_ms", "close_ms", "side", "volume", "open_price", "close_price", "sl", "tp",
            "reason", "gross", "commission", "swap", "net", "r"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols).sort_values(["close_ms", "open_ms"]).reset_index(drop=True)


def _prepare(params: WrxParams, ticks: Ticks, warmup_m1: Bars | None) -> Pre:
    m1_t, first_idx = m1_from_ticks(ticks)
    nw = 0
    if warmup_m1 is not None and len(warmup_m1):
        keep = warmup_m1.time < m1_t.time[0]
        w = Bars(*(getattr(warmup_m1, f)[keep] for f in ("time", "open", "high", "low", "close")),
                 volume=None if warmup_m1.volume is None else warmup_m1.volume[keep])
        nw = len(w)
        m1 = Bars(*(np.concatenate((getattr(w, f), getattr(m1_t, f))) for f in ("time", "open", "high", "low", "close")))
        m1.volume = (np.concatenate((w.volume, m1_t.volume))
                     if (w.volume is not None and m1_t.volume is not None) else None)
    else:
        m1 = m1_t
    n_m1 = len(m1)
    first_bid = np.concatenate((m1.open[:nw], ticks.bid[first_idx]))
    sig_tf = resample(m1, params.tf_min)
    atr_tf = sig_tf if params.atr_tf_min == params.tf_min else resample(m1, params.atr_tf_min)
    sb = tf_index_of(m1, sig_tf, params.tf_min)
    ab = tf_index_of(m1, atr_tf, params.atr_tf_min)
    bb = buy_j = sell_j = None
    if params.family == "bollinger":
        buy_raw, sell_raw, bb = signals.bollinger_signals(params, sig_tf)
    elif params.family == "candles":
        buy_j, sell_j = signals.candles_signals(params, m1, first_bid)
        buy_raw = sell_raw = np.zeros(len(sig_tf), bool)
    else:
        buy_raw, sell_raw = signals.raw_signals(params, sig_tf, sig_tf.volume)
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
    flt = compute_filters(params, m1, first_bid, atr_c, atr0, ab)
    f_hi, f_lo, f_cl = forming_partial(m1, params.tf_min, first_bid)
    first_tick_of = np.concatenate((np.full(nw, -1, dtype=np.int64), first_idx))
    return Pre(m1, nw, n_m1, first_tick_of, first_bid, sig_tf, sb, ab, buy_raw, sell_raw, atr_c, atr0, copy_atr,
               flt, sig_tf.open[sb], f_hi, f_lo, f_cl, params.family, bb, buy_j, sell_j)


def news_currencies(params: WrxParams, symbol: str) -> list[str]:
    """WR_ParseCurrencyList(NewsMoedasManual) ou, se vazio, base+cotacao de um simbolo FX de 6 letras."""
    raw = params.v["NewsMoedasManual"].strip()
    if raw:
        return [t.strip().upper() for t in raw.split(",") if t.strip()]
    if len(symbol) == 6:
        return [symbol[:3].upper(), symbol[3:].upper()]
    return []


def load_news_csv(path, high_only: bool = False) -> list[tuple]:
    """WR_LoadNewsCSV + WR_ImportanceAllowed: linhas `datetime;currency;importance;event`."""
    import datetime as _dt
    from pathlib import Path
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="latin-1").splitlines()):
        parts = line.split(";")
        if not parts or not parts[0].strip() or (n == 0 and parts[0].strip() == "datetime") or len(parts) < 3:
            continue
        try:
            t = int(_dt.datetime.strptime(parts[0].strip(), "%Y.%m.%d %H:%M").replace(tzinfo=_dt.timezone.utc).timestamp())
        except ValueError:
            continue
        imp = int(parts[2]) if parts[2].strip().lstrip("-").isdigit() else 0
        if (imp == 3) if high_only else (imp in (2, 3)):
            out.append((t, parts[1].strip().upper(), imp))
    return out


def run_backtest(params: WrxParams, spec: SymbolSpec, ticks: Ticks, *,
                 warmup_m1: Bars | None = None, stop_fill: str = "level", pending_fill: str = "tick",
                 signal_hook=None, deposit: float = DEFAULT_DEPOSIT, hedging_account: bool = True,
                 news_events: list | None = None, wfo_start: int | None = None,
                 validate: bool = True) -> BacktestResult:
    """Roda o EA sobre `ticks`.

    deposit: deposito inicial do Tester (base do Fixed-R quando CapitalBaseR=0, do Monetary e das travas).
    warmup_m1: barras M1 ANTERIORES ao 1o tick (o Tester tambem tem historico antes da data inicial).
    stop_fill: 'level' (SL executa no preco do SL) ou 'tick' (no bid/ask do tick que rompeu) -- CALIBRAR.
    pending_fill: 'tick' (stops preenchem no preco do tick; limits no da ordem) ou 'level' -- CALIBRAR.
    news_events: lista (epoch_s, moeda, importancia) ja filtrada (ver load_news_csv).
    validate: recusa o que o OnInit() do EA recusaria (InvalidConfig).
    """
    if stop_fill not in ("level", "tick"):
        raise ValueError("stop_fill deve ser 'level' ou 'tick'")
    if pending_fill not in ("level", "tick"):
        raise ValueError("pending_fill deve ser 'level' ou 'tick'")
    bad = unsupported({k: str(v) for k, v in params.v.items()})
    if bad:
        raise UnsupportedConfig(bad)
    if validate:
        errs = oninit_errors(params.v, hedging_account=hedging_account, family=params.family)
        if errs:
            raise InvalidConfig("o EA recusaria no OnInit: " + "; ".join(errs))
    if len(ticks) == 0:
        return BacktestResult(trades=_trades_frame([]), params=params, spec=spec)

    pre = _prepare(params, ticks, warmup_m1)
    cur = news_currencies(params, spec.symbol) if params.v["AtivarFiltroNoticias"] else []
    if params.v["AtivarFiltroNoticias"] and not cur:
        raise InvalidConfig("filtro de noticias sem moedas: defina NewsMoedasManual")
    sim = Sim(params, spec, ticks, pre, deposit=deposit, stop_fill=stop_fill, pending_fill=pending_fill,
              signal_hook=signal_hook, hedging_account=hedging_account, news_events=news_events,
              news_currencies=cur)
    if params.v["AtivarWFO"]:
        start = wfo_start if wfo_start is not None else int(pre.m1.time[pre.nw])
        sim.wfo = build_plan(params.v, start)
    sim.run()
    open_left = [dict(p.__dict__) for p in sim.L.positions]
    return BacktestResult(trades=_trades_frame(sim.closed_rows), open_positions=open_left, params=params,
                          spec=spec, valor_r=sim.valor_r, skipped=sim.skipped, ledger=sim.L, sim=sim)
