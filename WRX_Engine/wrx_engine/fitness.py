"""Fitness do OnTester: `TesterStatistics(...)` reconstruido a partir do backtest + as 15 formulas do EA.

O EA devolve ao otimizador o numero de `customEstimator()` (formula escolhida em `selectedFormula`, vezes o
`ConsistencyFactor` nas formulas nao-grid). Aqui as formulas sao portadas linha a linha de Multi.mq5
(mesmas variaveis, mesmos pisos e tetos). O que NAO e trivial e depende de calibracao contra o MT5 real:

  * as estatisticas do Tester (Sharpe, DD de equity, nivel de margem minimo, series de perdas) sao
    reconstruidas aqui -- ver `TesterStats` e as hipoteses no docstring de `compute_stats`;
  * o EA grava, a cada passe, a linha `ALL_FORMULAS ...` em `levain_wrx_all_formulas.txt`; `parse_all_formulas`
    le essa linha e `compare_with_tester` mostra, campo a campo, onde este motor diverge do MT5.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, fields

import numpy as np

MIN_TRADES = 30          # MinTradesOnTester (global nao-input do EA)
PF_CAP = 10.0            # PF_CAP

FORMULAS = {
    0: "None", 1: "GridSurvivalScore", 2: "Profit", 3: "ProfitWinTradeDD", 4: "EfficiencyRelativeToDeposit",
    5: "AdjustedEfficiencyForGrid", 6: "ProfitRelativeToDDAndDeposit", 7: "ProfitPerTradeAdjustedByDD",
    8: "SharpeAdjustedByDD", 9: "PessimisticProfit", 10: "ResilienceToDrawdown", 11: "ReturnUniformity",
    12: "SystemRobustness", 13: "LevainCompositeScore", 14: "SomaR", 15: "ZeusCompositeScore",
}
GRID_FORMULAS = (1, 5)   # excluidas do ConsistencyFactor


@dataclass
class Filters:
    """Globais nao-input do EA (`ActivateFilter*` / `Threshold*`)."""
    zero_transactions: bool = True
    negative_profit: bool = True
    max_drawdown: bool = False
    threshold_max_drawdown: float = 50.0
    recovery_factor: bool = False
    threshold_recovery_factor: float = 1.0
    sharpe_index: bool = False
    threshold_sharpe: float = 0.5


@dataclass
class TesterStats:
    profit: float = 0.0                 # STAT_PROFIT
    trades: int = 0                     # STAT_TRADES
    profit_trades: int = 0              # STAT_PROFIT_TRADES
    gross_profit: float = 0.0           # STAT_GROSS_PROFIT
    gross_loss: float = 0.0             # STAT_GROSS_LOSS (negativo, como no MT5)
    sharpe: float = 0.0                 # STAT_SHARPE_RATIO
    recovery_factor: float = 0.0        # STAT_RECOVERY_FACTOR
    equity_dd: float = 0.0              # STAT_EQUITY_DD (maior DD em dinheiro)
    equity_dd_percent: float = 0.0      # STAT_EQUITYDD_PERCENT
    equity_ddrel_percent: float = 0.0   # STAT_EQUITY_DDREL_PERCENT (maior DD percentual)
    min_margin_level: float = 0.0       # STAT_MIN_MARGINLEVEL (0 = sem posicao/margem)
    conloss_max_trades: int = 0         # STAT_CONLOSSMAX_TRADES
    initial_deposit: float = 0.0        # STAT_INITIAL_DEPOSIT
    # extras do EA (nao sao TesterStatistics)
    ea_initial_deposit: float = 0.0     # initialDeposit do EA = EffectiveCapital() no OnInit
    net: np.ndarray = field(default_factory=lambda: np.zeros(0), repr=False)   # g_closedOperations[].net


# ----------------------------------------------------------------------------------------------------------
# estatisticas
# ----------------------------------------------------------------------------------------------------------
def equity_curve(result, deposit: float):
    """Equity e nivel de margem por tick (aberta a mercado: bid p/ compra, ask p/ venda; comissao de entrada
    debitada na abertura; swap e resultado so entram no fechamento). Retorna (equity, margin) com len = ticks."""
    sim = result.sim
    t_ms, bid, ask, spec = sim.t_ms, sim.bid, sim.ask, sim.spec
    n = len(t_ms)
    step = np.zeros(n + 1)                                  # realizado acumulado (degrau no tick do fechamento)
    flo = np.zeros(n + 1)
    mar = np.zeros(n + 1)
    k = spec.tick_value / spec.tick_size if spec.tick_size else 0.0

    def leg(i0, i1, is_buy, vol, px, comm_in, margin):
        if i1 <= i0:
            return
        if is_buy:
            flo[i0:i1] += (bid[i0:i1] - px) * k * vol - comm_in
        else:
            flo[i0:i1] += (px - ask[i0:i1]) * k * vol - comm_in
        if margin:
            mar[i0:i1] += margin

    t = result.trades
    if not t.empty:
        oi = np.searchsorted(t_ms, t["open_ms"].to_numpy(), side="left")
        ci = np.searchsorted(t_ms, t["close_ms"].to_numpy(), side="left")
        for j, row in enumerate(t.itertuples(index=False)):
            comm_in = -row.commission / 2.0
            margin = row.volume * (spec.margin_a * row.open_price + spec.margin_b)
            leg(int(oi[j]), int(ci[j]), row.side == "buy", row.volume, row.open_price, comm_in, margin)
            step[int(ci[j])] += row.net
    for pos in result.open_positions:                       # BacktestResult guarda as abertas como dict
        d = pos if isinstance(pos, dict) else pos.__dict__
        i0 = int(np.searchsorted(t_ms, d["open_ms"], side="left"))
        margin = d["volume"] * (spec.margin_a * d["open_price"] + spec.margin_b)
        leg(i0, n, d["is_buy"], d["volume"], d["open_price"], d["commission"], margin)
    eq = deposit + np.cumsum(step)[:n] + flo[:n]
    return eq, mar[:n]


def _series(net: np.ndarray):
    """Series de perdas consecutivas: (maior perda em dinheiro, n de trades dessa serie) -- STAT_CONLOSSMAX(_TRADES)."""
    best_sum, best_n, cur_sum, cur_n = 0.0, 0, 0.0, 0
    for x in net:
        if x < 0:
            cur_sum += x
            cur_n += 1
            if cur_sum < best_sum:
                best_sum, best_n = cur_sum, cur_n
        else:
            cur_sum, cur_n = 0.0, 0
    return best_sum, best_n


def compute_stats(result, deposit: float = 10000.0, *, equity=None) -> TesterStats:
    """Hipoteses a confirmar contra a linha ALL_FORMULAS do MT5:
      H1 gross profit/loss = soma do `net` (lucro+swap+comissao) por posicao, >0 / <0;
      H2 Sharpe = media(net)/desvio(net, n-1) por trade, sem anualizar;
      H3 DD de equity: pico corrente desde o deposito; `equity_dd` = maior queda em dinheiro e
         `equity_dd_percent` = essa mesma queda como % do pico daquele momento; `equity_ddrel_percent` = maior
         queda percentual (pode ser outro episodio);
      H4 recovery factor = lucro / equity_dd; H5 conloss_max_trades = n de trades da serie de perdas seguidas
         com MAIOR perda em dinheiro (definicao da doc do MT5, nao 'maior sequencia de perdas');
      H6 nivel de margem = equity/margem*100 com margem = lote*(margin_a*preco_abertura+margin_b)."""
    t = result.trades
    net = t["net"].to_numpy(float) if not t.empty else np.zeros(0)
    s = TesterStats(initial_deposit=deposit, net=net)
    tp = result.params.v["TradeCapitalPercentage"] if result.params is not None else 100.0
    s.ea_initial_deposit = deposit * (tp / 100.0 if 0 < tp <= 100 else 1.0)
    s.trades = int(len(net))
    if s.trades:
        s.profit = float(net.sum())
        s.profit_trades = int((net > 0).sum())
        s.gross_profit = float(net[net > 0].sum())
        s.gross_loss = float(net[net < 0].sum())
        sd = float(np.std(net, ddof=1)) if len(net) > 1 else 0.0
        s.sharpe = float(net.mean() / sd) if sd > 0 else 0.0
        s.conloss_max_trades = _series(net)[1]
    if result.sim is not None and result.sim.n_t:
        eq, mar = equity if equity is not None else equity_curve(result, deposit)
        peak = np.maximum.accumulate(np.maximum(eq, deposit))
        dd = peak - eq
        i = int(np.argmax(dd))
        s.equity_dd = float(dd[i])
        s.equity_dd_percent = float(dd[i] / peak[i] * 100.0) if peak[i] > 0 else 0.0
        s.equity_ddrel_percent = float(np.max(dd / np.where(peak > 0, peak, 1.0)) * 100.0)
        m = mar > 0
        if m.any():
            s.min_margin_level = float(np.min(eq[m] / mar[m] * 100.0))
    s.recovery_factor = s.profit / s.equity_dd if s.equity_dd > 0 else 0.0
    return s


# ----------------------------------------------------------------------------------------------------------
# formulas (porte literal)
# ----------------------------------------------------------------------------------------------------------
def capped_pf(gp: float, gl: float) -> float:
    agl = abs(gl)
    if agl < 0.0001:
        return PF_CAP if gp > 0 else 1.0
    return min(gp / agl, PF_CAP)


def additional_filters(s: TesterStats, f: Filters, np_=None, trades=None, sharpe=None, dd_pct=None, gp=None, gl=None) -> bool:
    np_ = s.profit if np_ is None else np_
    trades = s.trades if trades is None else trades
    sharpe = s.sharpe if sharpe is None else sharpe
    dd_pct = s.equity_dd_percent if dd_pct is None else dd_pct
    gp = s.gross_profit if gp is None else gp
    gl = s.gross_loss if gl is None else gl
    if trades <= 0 or trades < MIN_TRADES or s.initial_deposit <= 0:
        return False
    if f.zero_transactions and trades == 0:
        return False
    if f.negative_profit and np_ < 0:
        return False
    if f.max_drawdown and dd_pct > f.threshold_max_drawdown:
        return False
    if f.recovery_factor and abs(gl) > 0.0001 and gp / abs(gl) < f.threshold_recovery_factor:
        return False
    if f.sharpe_index and sharpe < f.threshold_sharpe:
        return False
    return True


def stdev_ops(s: TesterStats) -> float:
    """CalculateStandardDeviation(): desvio amostral (n-1) do `net` por operacao."""
    n = len(s.net)
    if n < 1:
        return 0.0
    mean = float(s.net.sum()) / n
    var = float(((s.net - mean) ** 2).sum()) / (n - 1 if n > 1 else n)
    return math.sqrt(var)


def _wins_losses(s: TesterStats):
    return int((s.net > 0).sum()), int((s.net < 0).sum())


def f_profit(s, f, **_):
    return s.profit if additional_filters(s, f) else 0.0


def f_profit_win_trade_dd(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    win, loss = _wins_losses(s)
    if win + loss <= 0:
        return 0.0
    wtp = win / (win + loss) * 100.0
    if wtp <= 0:
        return 0.0
    dd = s.equity_dd_percent
    if abs(dd) < 0.0001:
        dd = 1.0
    return (s.profit * wtp / dd) / 100000


def f_pessimistic(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    win, loss = _wins_losses(s)
    adj_win = 1 - 1 / math.sqrt(max(1, win + 1))
    adj_loss = 1 + 1 / math.sqrt(max(1, loss + 1))
    pess = (s.gross_profit * adj_win + s.gross_loss * adj_loss) / s.trades
    w = pess * 0.7 + (s.profit / s.trades) * 0.3
    return 0.0 if w <= 0 else w


def f_ppt_dd(s, f, **_):
    if s.trades <= 0 or not additional_filters(s, f):
        return 0.0
    pf = capped_pf(s.gross_profit, s.gross_loss)
    penalty = max(1.0, 100.0 / s.trades)
    stability = max(0.5, 1 - s.equity_dd_percent / 100.0)
    avg = (s.profit / s.trades) / max(s.initial_deposit, 1.0)
    result = avg * stability * pf
    w = result * 0.7 + (avg * 0.3) / penalty
    return 0.0 if w < 0.00001 else w


def f_eff_deposit(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    dep = s.initial_deposit
    bal = dep + s.profit
    roi = s.profit / dep
    stability = 1 - (s.equity_ddrel_percent / 100 + s.equity_dd / bal)
    w = (roi * stability * 100) * 0.6 + (s.profit / dep) * 0.4
    return 0.0 if w <= 0 else w


def f_adj_eff_grid(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    bal = s.initial_deposit + s.profit
    penalty = 1 - (s.equity_ddrel_percent / 100 + s.equity_dd / bal)
    fr = ((s.profit / bal) * penalty * 100) * 100
    w = fr * 0.7 + (s.profit / bal) * 0.3
    return 0.0 if w <= 0 else w


def f_sharpe_adj(s, f, **_):
    sd = stdev_ops(s)
    if not additional_filters(s, f) or sd <= 0:
        return 0.0
    adj = s.sharpe / sd
    fr = adj * s.profit / (1 + s.equity_ddrel_percent / 100)
    w = fr * 0.5 + (s.profit / sd) * 0.5
    return 0.0 if w <= 0 else w


def f_profit_rel_dd_dep(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    if abs(s.gross_loss) < 0.0001 or s.equity_dd <= 0 or s.initial_deposit <= 0:
        return 0.0
    pf = capped_pf(s.gross_profit, s.gross_loss)
    stability = (s.profit / (s.equity_dd * s.initial_deposit)) * pf
    w = (stability * 0.7 + (s.profit / s.initial_deposit) * 0.3) * 100
    return 0.0 if (w <= 0 or not math.isfinite(w)) else w


def _margin_penalty(s):
    m = s.min_margin_level
    return 1.0 if m <= 0 else max(0.0, min(1.0, (m - 100) / 200))


def f_resilience(s, f, **_):
    if not additional_filters(s, f) or s.equity_dd_percent <= 0 or s.initial_deposit <= 0:
        return 0.0
    roi_pct = s.profit / s.initial_deposit * 100.0
    fr = (roi_pct / s.equity_dd_percent) * 0.7 + s.gross_profit * 0.3
    fr *= _margin_penalty(s)
    return 0.0 if fr <= 0 else fr


def f_return_uniformity(s, f, **_):
    sd = stdev_ops(s)
    if not additional_filters(s, f) or sd <= 0:
        return 0.0
    avg = s.profit / (s.ea_initial_deposit * s.trades)
    r = ((avg / sd) * 1000000.0) * 100
    return 0.0 if r < 0 else r


def f_system_robustness(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    r = (s.profit / math.sqrt(s.trades)) * 0.8 + s.profit * 0.2
    return 0.0 if r <= 0 else r


def f_grid_survival(s, f, **_):
    if not additional_filters(s, f):
        return 0.0
    pf = capped_pf(s.gross_profit, s.gross_loss)
    win_rate = s.profit_trades / s.trades if s.trades > 0 else 0.0
    density = math.log(s.trades + 1)
    dd_pen = 1 - min(s.equity_dd_percent / 50, 1)
    vol_adj = 1 / (1 + stdev_ops(s))
    return (s.profit * win_rate * pf * density * vol_adj * dd_pen * _margin_penalty(s)) / (s.initial_deposit * 0.01)


def f_levain(s, f, **_):
    if s.trades < 30 or s.initial_deposit <= 0:
        return 0.0
    if not additional_filters(s, f):
        return 0.0
    pf = capped_pf(s.gross_profit, s.gross_loss)
    pf_norm = min(1.0, pf / 3.0)
    avg_pct = (s.profit / s.trades) / s.initial_deposit
    stability = max(0.5, 1.0 - s.equity_dd_percent / 100.0)
    pptdd = min(1.0, max(0.0, avg_pct * stability * pf / 0.005))
    sharpe_n = min(1.0, s.sharpe / 2.0) if s.sharpe > 0 else 0.0
    rf_n = min(1.0, s.recovery_factor / 5.0) if s.recovery_factor > 0 else 0.0
    sc = pf_norm * 0.35 + pptdd * 0.30 + sharpe_n * 0.20 + rf_n * 0.15
    return max(0.0, min(1.0, sc))


def r_metrics(result, stats: TesterStats):
    """ComputeRMetrics(): retorna dict ou None (modos que nao sao R Fixo nem Porcentagem)."""
    p = result.params
    if p is None or result.trades.empty:
        return None
    size_mode, val = p.size_mode, p.size_value
    mode_r = size_mode == 3 and result.valor_r > 0
    mode_pct = size_mode == 0 and val > 0
    if not (mode_r or mode_pct):
        return None
    t = result.trades
    net = t["net"].to_numpy(float)
    if mode_r:
        vr = np.full(len(net), result.valor_r)
    else:
        tp = p.v["TradeCapitalPercentage"]
        fator = tp / 100.0 if 0 < tp <= 100 else 1.0
        comm_in = -t["commission"].to_numpy(float) / 2.0
        # saldo reconstruido deal a deal: deposito + resultados dos deals anteriores (entrada so com a comissao)
        ev_t = np.concatenate([t["open_ms"].to_numpy(), t["close_ms"].to_numpy()])
        ev_v = np.concatenate([-comm_in, net + comm_in])
        ev_k = np.concatenate([np.zeros(len(net)), np.ones(len(net))])
        ev_i = np.concatenate([np.arange(len(net)), np.arange(len(net))])
        order = np.lexsort((ev_i, ev_k, ev_t))
        cum = stats.initial_deposit + np.concatenate(([0.0], np.cumsum(ev_v[order])))
        pos_of = np.empty(len(order), int)
        pos_of[order] = np.arange(len(order))
        bal_at_entry = cum[pos_of[:len(net)]]
        vr = val / 100.0 * fator * bal_at_entry
    r = np.where(vr > 0, net / np.where(vr > 0, vr, 1.0), 0.0)
    wins, losses = int((r >= 0).sum()), int((r < 0).sum())
    avg_win = float(r[r >= 0].sum()) / wins if wins else 0.0
    avg_loss = float(-r[r < 0].sum()) / losses if losses else 0.0
    return {"soma_r": float(r.sum()), "media_r": float(r.mean()), "win_rate_pct": 100.0 * wins / len(r),
            "payoff_r": avg_win / avg_loss if avg_loss > 0 else 0.0,
            "max_ganho_r": float(max(r.max(), 0.0)), "max_perda_r": float(min(r.min(), 0.0)), "n": len(r)}


def f_soma_r(s, f, result=None, **_):
    m = r_metrics(result, s) if result is not None else None
    if m is None or m["n"] < MIN_TRADES:
        return 0.0
    return m["soma_r"]


def f_zeus(s, f, **_):
    if s.trades < 30 or s.initial_deposit <= 0:
        return -1e9
    pf = s.gross_profit / abs(s.gross_loss) if s.gross_loss != 0.0 else 0.0
    return (s.profit / s.initial_deposit * 100.0) * pf / (1.0 + s.equity_ddrel_percent / 20.0)


def consistency_factor(s: TesterStats) -> float:
    if s.trades <= 0:
        return 1.0
    wr = s.profit_trades / s.trades
    wr_norm = max(0.0, min(1.0, (wr - 0.35) / 0.35))
    streak_norm = max(0.0, min(1.0, 1.0 - s.conloss_max_trades / 10.0))
    return 0.85 + 0.15 * (0.5 * wr_norm + 0.5 * streak_norm)


def _consistent(v: float, s: TesterStats) -> float:
    return v * consistency_factor(s) if v > 0 else v


_IMPL = {1: f_grid_survival, 2: f_profit, 3: f_profit_win_trade_dd, 4: f_eff_deposit, 5: f_adj_eff_grid,
         6: f_profit_rel_dd_dep, 7: f_ppt_dd, 8: f_sharpe_adj, 9: f_pessimistic, 10: f_resilience,
         11: f_return_uniformity, 12: f_system_robustness, 13: f_levain, 14: f_soma_r, 15: f_zeus}


def custom_estimator(formula: int, s: TesterStats, f: Filters | None = None, result=None) -> float:
    """customEstimator(): a formula escolhida (+ ConsistencyFactor nas nao-grid)."""
    f = f or Filters()
    if formula == 0 or formula not in _IMPL:
        return 0.0
    v = _IMPL[formula](s, f, result=result)
    if v > 0 and formula not in GRID_FORMULAS:
        v *= consistency_factor(s)
    return v


def all_formulas(s: TesterStats, f: Filters | None = None, result=None) -> dict:
    """Os 14 numeros da linha ALL_FORMULAS (brutos nas de grid, com ConsistencyFactor nas demais)."""
    f = f or Filters()
    g = lambda k: _IMPL[k](s, f, result=result)
    c = lambda k: _consistent(g(k), s)
    return {"GridSurvival": g(1), "ProfitFormula": c(2), "ProfitWinTradeDD": c(3), "EffRelDeposit": c(4),
            "AdjEffGrid": g(5), "ProfitRelDDDeposit": c(6), "PPTDD": c(7), "SharpeAdjDD": c(8),
            "PessimisticProfit": c(9), "ResilienceDD": c(10), "ReturnUniformity": c(11),
            "SystemRobustness": c(12), "LevainComposite": c(13), "SomaR": c(14), "ZeusScore": c(15)}


def all_formulas_line(s: TesterStats, f: Filters | None = None, result=None) -> str:
    """Linha no MESMO formato que o EA grava em levain_wrx_all_formulas.txt."""
    a = all_formulas(s, f, result)
    return (f"ALL_FORMULAS Profit={s.profit:.6f} Trades={s.trades} GrossProfit={s.gross_profit:.6f} "
            f"GrossLoss={s.gross_loss:.6f} EquityDDPercent={s.equity_dd_percent:.6f} Sharpe={s.sharpe:.6f} "
            f"InitialDeposit={s.initial_deposit:.2f} | GridSurvival={a['GridSurvival']:.6f} "
            f"ProfitFormula={a['ProfitFormula']:.6f} ProfitWinTradeDD={a['ProfitWinTradeDD']:.6f} "
            f"EffRelDeposit={a['EffRelDeposit']:.6f} AdjEffGrid={a['AdjEffGrid']:.6f} "
            f"ProfitRelDDDeposit={a['ProfitRelDDDeposit']:.6f} PPTDD={a['PPTDD']:.6f} "
            f"SharpeAdjDD={a['SharpeAdjDD']:.6f} PessimisticProfit={a['PessimisticProfit']:.6f} "
            f"ResilienceDD={a['ResilienceDD']:.6f} ReturnUniformity={a['ReturnUniformity']:.6f} "
            f"SystemRobustness={a['SystemRobustness']:.6f} LevainComposite={a['LevainComposite']:.6f} "
            f"SomaR={a['SomaR']:.6f} EquityDDRelPercent={s.equity_ddrel_percent:.6f} "
            f"ZeusScore={a['ZeusScore']:.6f}")


_KV = re.compile(r"([A-Za-z]+)=(-?[0-9.eE+-]+)")


def parse_all_formulas(line: str) -> dict:
    return {k: float(v) for k, v in _KV.findall(line)}


def compare_with_tester(mine: str, theirs: str, rel_tol: float = 0.02) -> list[dict]:
    """Campo a campo: valor deste motor x valor do MT5 (linha gravada pelo EA). `ok` se dentro de rel_tol."""
    a, b = parse_all_formulas(mine), parse_all_formulas(theirs)
    rows = []
    for k in b:
        if k not in a:
            continue
        x, y = a[k], b[k]
        den = max(abs(x), abs(y), 1e-9)
        rows.append({"campo": k, "motor": x, "mt5": y, "dif_rel": abs(x - y) / den, "ok": abs(x - y) / den <= rel_tol})
    return rows


def evaluate(result, deposit: float = 10000.0, formula: int | None = None, f: Filters | None = None) -> dict:
    """Atalho: estatisticas + formula escolhida (default: `selectedFormula` do set) + linha ALL_FORMULAS."""
    s = compute_stats(result, deposit)
    if formula is None:
        formula = int(result.params.v.get("selectedFormula", 7)) if result.params is not None else 7
    return {"stats": s, "formula": formula, "name": FORMULAS.get(formula, "?"),
            "score": custom_estimator(formula, s, f, result), "line": all_formulas_line(s, f, result)}
