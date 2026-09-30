import math
from dataclasses import replace

import numpy as np
import pytest

from scen import go, script
from wrx_engine import fitness as F
from wrx_engine.fitness import Filters, TesterStats

LOT = dict(PositionSizeMode=2, PositionSizeValue=0.10)


def S(**kw) -> TesterStats:
    base = dict(profit=1200.0, trades=50, profit_trades=30, gross_profit=3000.0, gross_loss=-1800.0, sharpe=0.8,
                recovery_factor=2.4, equity_dd=500.0, equity_dd_percent=4.0, equity_ddrel_percent=5.0,
                min_margin_level=0.0, conloss_max_trades=4, initial_deposit=10000.0, ea_initial_deposit=10000.0)
    base.update(kw)
    s = TesterStats(**base)
    rng = np.random.default_rng(3)
    s.net = np.round(rng.normal(24, 120, s.trades), 2)
    return s


# ---------------------------------------------------------------- estatisticas (independentes do vetorizado)
def naive_equity(res, deposit):
    sim = res.sim
    spec = sim.spec
    eq = []
    rows = list(res.trades.itertuples(index=False))
    opens = list(res.open_positions)
    for k in range(len(sim.t_ms)):
        t = sim.t_ms[k]
        v = deposit
        for r in rows:
            if t >= r.close_ms and k >= int(np.searchsorted(sim.t_ms, r.close_ms)):
                v += r.net
            elif k >= int(np.searchsorted(sim.t_ms, r.open_ms)):
                px = sim.bid[k] if r.side == "buy" else sim.ask[k]
                mv = (px - r.open_price) if r.side == "buy" else (r.open_price - px)
                v += mv / spec.tick_size * spec.tick_value * r.volume + r.commission / 2.0
        for p in opens:
            if k >= int(np.searchsorted(sim.t_ms, p["open_ms"])):
                px = sim.bid[k] if p["is_buy"] else sim.ask[k]
                mv = (px - p["open_price"]) if p["is_buy"] else (p["open_price"] - px)
                v += mv / spec.tick_size * spec.tick_value * p["volume"] - p["commission"]
        eq.append(v)
    return np.array(eq)


def scenario(spec, outcomes, **kw):
    mb, ents = script(outcomes, gap=4)
    res, _ = go(mb, ents, spec, **(LOT | kw))
    return res


def test_equity_curve_matches_tick_by_tick_loop(spec):
    spec = replace(spec, commission_per_lot_side=7.0, margin_a=50000.0, margin_b=0.0)
    res = scenario(spec, ["tp", "sl", "sl", "tp", "tp"])
    assert len(res.trades) == 5
    eq, mar = F.equity_curve(res, 10000.0)
    assert np.allclose(eq, naive_equity(res, 10000.0))
    assert mar.max() > 0 and (mar >= 0).all()
    assert abs(eq[-1] - (10000.0 + res.trades["net"].sum())) < 1e-6          # sem posicao aberta: equity = saldo


def test_equity_with_position_still_open_at_the_end(spec):
    from scen import script as sc
    spec = replace(spec, commission_per_lot_side=7.0)
    mb, ents = sc(["tp", "tp"], gap=4)
    mb = mb[:ents[1] + 1]                                   # corta logo depois da 2a entrada: fica uma posicao aberta
    res, _ = go(mb, ents, spec, **LOT)
    assert len(res.open_positions) == 1 and len(res.trades) == 1
    eq, _ = F.equity_curve(res, 10000.0)
    assert np.allclose(eq, naive_equity(res, 10000.0))
    s = F.compute_stats(res, 10000.0)
    assert s.profit == pytest.approx(res.trades["net"].sum()) and s.trades == 1     # so fechadas contam no STAT_PROFIT
    assert eq[-1] != pytest.approx(10000.0 + s.profit)                               # o flutuante/comissao aberta pesa no equity


def test_stats_against_definitions(spec):
    res = scenario(spec, ["tp", "sl", "sl", "sl", "tp", "sl", "tp", "tp", "sl", "sl"])
    s = F.compute_stats(res, 10000.0)
    net = res.trades["net"].to_numpy()
    assert s.trades == 10 and s.profit == pytest.approx(net.sum())
    assert s.profit_trades == int((net > 0).sum())
    assert s.gross_profit == pytest.approx(net[net > 0].sum()) and s.gross_loss == pytest.approx(net[net < 0].sum())
    assert s.gross_loss < 0
    assert s.sharpe == pytest.approx(net.mean() / net.std(ddof=1))
    # serie de perdas com MAIOR perda em dinheiro: sl,sl,sl (3 trades), nao necessariamente a mais longa
    assert s.conloss_max_trades == 3
    # DD de equity contra laco ingenuo
    eq = naive_equity(res, 10000.0)
    peak, worst, worst_pct, rel = 10000.0, 0.0, 0.0, 0.0
    for v in eq:
        peak = max(peak, v)
        d = peak - v
        if d > worst:
            worst, worst_pct = d, d / peak * 100
        rel = max(rel, d / peak * 100)
    assert s.equity_dd == pytest.approx(worst) and s.equity_dd_percent == pytest.approx(worst_pct)
    assert s.equity_ddrel_percent == pytest.approx(rel)
    assert s.recovery_factor == pytest.approx(s.profit / worst)
    assert s.min_margin_level == 0.0                                          # sem modelo de margem


def test_conloss_series_picks_largest_money_not_longest():
    assert F._series(np.array([-1, -1, -1, 5, -10, 4]))[1] == 1
    assert F._series(np.array([-1, -1, -1, 5, -2, -2]))[1] == 2
    assert F._series(np.array([-1, -1, -1, 5, -1, -1]))[1] == 3
    assert F._series(np.array([3, 4]))[1] == 0


def test_min_margin_level_uses_margin_model(spec):
    spec = replace(spec, margin_a=30000.0)
    res = scenario(spec, ["tp", "sl"])
    s = F.compute_stats(res, 10000.0)
    eq, mar = F.equity_curve(res, 10000.0)
    m = mar > 0
    assert s.min_margin_level == pytest.approx((eq[m] / mar[m] * 100).min())
    assert 0 < s.min_margin_level < 1e6


# ---------------------------------------------------------------- formulas (expressoes escritas a mao a partir do .mq5)
def test_filters_and_floor():
    assert F.f_profit(S(), Filters()) == 1200.0
    assert F.f_profit(S(trades=29), Filters()) == 0.0                         # piso de 30 trades
    assert F.f_profit(S(profit=-1.0), Filters()) == 0.0                       # lucro negativo
    assert F.f_profit(S(profit=-1.0), Filters(negative_profit=False)) == -1.0
    assert F.f_profit(S(equity_dd_percent=60), Filters(max_drawdown=True)) == 0.0
    assert F.f_profit(S(equity_dd_percent=60), Filters()) == 1200.0
    assert F.f_profit(S(gross_profit=1000, gross_loss=-2000), Filters(recovery_factor=True)) == 0.0
    assert F.f_profit(S(sharpe=0.1), Filters(sharpe_index=True)) == 0.0
    assert F.f_profit(S(initial_deposit=0.0), Filters()) == 0.0


def test_formulas_by_hand():
    s, f = S(), Filters()
    assert F.capped_pf(3000, -1800) == pytest.approx(5 / 3)
    assert F.capped_pf(3000, 0.0) == 10.0 and F.capped_pf(0.0, 0.0) == 1.0 and F.capped_pf(100000, -1) == 10.0
    # ProfitPerTradeAdjustedByDD
    avg = (1200 / 50) / 10000
    res = avg * max(0.5, 1 - 0.04) * (5 / 3)
    assert F.f_ppt_dd(s, f) == pytest.approx(res * 0.7 + (avg * 0.3) / max(1.0, 100 / 50))
    # ProfitWinTradeDD: win/loss contados sobre os nets das operacoes
    win, loss = int((s.net > 0).sum()), int((s.net < 0).sum())
    assert F.f_profit_win_trade_dd(s, f) == pytest.approx((1200 * (win / (win + loss) * 100) / 4.0) / 100000)
    assert F.f_profit_win_trade_dd(S(equity_dd_percent=0.0), f) == pytest.approx(
        (1200 * (win / (win + loss) * 100) / 1.0) / 100000)                   # dd ~ 0 vira 1
    # Pessimistic
    aw, al = 1 - 1 / math.sqrt(win + 1), 1 + 1 / math.sqrt(loss + 1)
    w = ((3000 * aw + -1800 * al) / 50) * 0.7 + (1200 / 50) * 0.3
    assert F.f_pessimistic(s, f) == pytest.approx(max(w, 0.0))
    # EfficiencyRelativeToDeposit / AdjEfficiencyForGrid
    bal = 11200.0
    assert F.f_eff_deposit(s, f) == pytest.approx(((0.12 * (1 - (0.05 + 500 / bal))) * 100) * 0.6 + 0.12 * 0.4)
    assert F.f_adj_eff_grid(s, f) == pytest.approx((((1200 / bal) * (1 - (0.05 + 500 / bal)) * 100) * 100) * 0.7
                                                   + (1200 / bal) * 0.3)
    # Sharpe ajustado
    sd = float(np.std(s.net, ddof=1))
    assert F.stdev_ops(s) == pytest.approx(sd)
    assert F.f_sharpe_adj(s, f) == pytest.approx(((0.8 / sd) * 1200 / 1.05) * 0.5 + (1200 / sd) * 0.5)
    # ProfitRelativeToDDAndDeposit
    assert F.f_profit_rel_dd_dep(s, f) == pytest.approx(((1200 / (500 * 10000)) * (5 / 3) * 0.7 + 0.12 * 0.3) * 100)
    assert F.f_profit_rel_dd_dep(S(gross_loss=0.0), f) == 0.0
    # Resilience (sem margem e com margem)
    assert F.f_resilience(s, f) == pytest.approx((12.0 / 4.0) * 0.7 + 3000 * 0.3)
    assert F.f_resilience(S(min_margin_level=200.0), f) == pytest.approx(((12.0 / 4.0) * 0.7 + 3000 * 0.3) * 0.5)
    assert F.f_resilience(S(min_margin_level=90.0), f) == 0.0
    assert F.f_resilience(S(min_margin_level=400.0), f) == pytest.approx((12.0 / 4.0) * 0.7 + 3000 * 0.3)
    assert F.f_resilience(S(equity_dd_percent=0.0), f) == 0.0
    # ReturnUniformity usa o initialDeposit EFETIVO do EA
    assert F.f_return_uniformity(S(ea_initial_deposit=5000.0), f) == pytest.approx(
        ((1200 / (5000 * 50)) / sd) * 1e6 * 100)
    # SystemRobustness
    assert F.f_system_robustness(s, f) == pytest.approx(1200 / math.sqrt(50) * 0.8 + 1200 * 0.2)
    # GridSurvival
    gs = 1200 * 0.6 * (5 / 3) * math.log(51) * (1 / (1 + sd)) * (1 - min(4 / 50, 1)) * 1.0 / (10000 * 0.01)
    assert F.f_grid_survival(s, f) == pytest.approx(gs)
    assert F.f_grid_survival(S(min_margin_level=250.0), f) == pytest.approx(gs * 0.75)
    # Levain
    pf_n = min(1, (5 / 3) / 3)
    pp = min(1.0, max(0.0, (24 / 10000) * 0.96 * (5 / 3) / 0.005))
    assert F.f_levain(s, f) == pytest.approx(pf_n * 0.35 + pp * 0.30 + min(1, 0.8 / 2) * 0.20 + min(1, 2.4 / 5) * 0.15)
    assert F.f_levain(S(trades=29), f) == 0.0
    # Zeus
    assert F.f_zeus(s, f) == pytest.approx(12.0 * (3000 / 1800) / (1 + 5 / 20))
    assert F.f_zeus(S(trades=29), f) == -1e9
    assert F.f_zeus(S(gross_loss=0.0), f) == 0.0


def test_consistency_factor_and_estimator():
    s = S(profit_trades=25, trades=50, conloss_max_trades=5)                   # wr .5 -> .4286 ; streak .5
    assert F.consistency_factor(s) == pytest.approx(0.85 + 0.15 * (0.5 * (0.15 / 0.35) + 0.5 * 0.5))
    assert F.consistency_factor(S(profit_trades=50, conloss_max_trades=0)) == pytest.approx(1.0)
    assert F.consistency_factor(S(profit_trades=0, conloss_max_trades=20)) == pytest.approx(0.85)
    assert F.consistency_factor(S(trades=0)) == 1.0
    s = S()
    cf = F.consistency_factor(s)
    assert F.custom_estimator(7, s) == pytest.approx(F.f_ppt_dd(s, Filters()) * cf)
    assert F.custom_estimator(1, s) == pytest.approx(F.f_grid_survival(s, Filters()))       # grid: sem fator
    assert F.custom_estimator(5, s) == pytest.approx(F.f_adj_eff_grid(s, Filters()))
    assert F.custom_estimator(0, s) == 0.0 and F.custom_estimator(99, s) == 0.0
    assert F.custom_estimator(15, S(trades=29)) == -1e9                          # negativo nao leva o fator
    a = F.all_formulas(s)
    assert a["GridSurvival"] == pytest.approx(F.f_grid_survival(s, Filters()))
    assert a["ProfitFormula"] == pytest.approx(1200 * cf) and a["ZeusScore"] == pytest.approx(F.f_zeus(s, Filters()) * cf)


def test_all_formulas_line_roundtrip_and_compare():
    s = S()
    line = F.all_formulas_line(s)
    d = F.parse_all_formulas(line)
    assert d["Trades"] == 50 and d["Profit"] == pytest.approx(1200.0) and d["InitialDeposit"] == 10000.0
    assert d["EquityDDRelPercent"] == pytest.approx(5.0)
    assert line.index("Sharpe=") < line.index("|") < line.index("GridSurvival=") < line.index("ZeusScore=")
    same = F.compare_with_tester(line, line)
    assert same and all(r["ok"] for r in same)
    other = F.all_formulas_line(S(profit=2400.0))
    bad = {r["campo"] for r in F.compare_with_tester(line, other) if not r["ok"]}
    assert {"Profit", "ProfitFormula"} <= bad


# ---------------------------------------------------------------- metricas em R
def test_r_metrics_fixed_r(spec):
    mb, ents = script(["tp", "sl", "tp", "tp", "sl"], gap=6, noisy_gap=True, jump=0.004)
    res, _ = go(mb, ents, spec, PositionSizeMode=3, PositionSizeValue=1, CapitalBaseR=10000, Stop=2, Take=3)
    n = len(res.trades)
    assert n >= 4
    s = F.compute_stats(res, 10000.0)
    m = F.r_metrics(res, s)
    assert m["n"] == n and m["soma_r"] == pytest.approx(res.trades["net"].sum() / 100.0)       # 1R = 1% de 10000
    r = res.trades["net"].to_numpy() / 100.0
    assert m["win_rate_pct"] == pytest.approx(100 * (r >= 0).mean())
    assert m["max_perda_r"] == pytest.approx(min(r.min(), 0.0))
    assert F.f_soma_r(s, Filters(), result=res) == 0.0                                           # < 30 trades
    assert F.r_metrics(res, s) is not None


def test_r_metrics_none_for_other_modes(spec):
    res = scenario(spec, ["tp", "sl", "tp"])
    assert F.r_metrics(res, F.compute_stats(res, 10000.0)) is None
    assert F.f_soma_r(S(), Filters(), result=res) == 0.0


def test_r_metrics_percentage_uses_rebuilt_balance_at_entry(spec):
    mb, ents = script(["tp", "tp", "sl", "tp"], gap=6)
    res, _ = go(mb, ents, spec, PositionSizeMode=0, PositionSizeValue=2, TradeCapitalPercentage=50)
    s = F.compute_stats(res, 10000.0)
    m = F.r_metrics(res, s)
    assert m is not None and m["n"] == len(res.trades)
    t = res.trades
    r, bal = [], 10000.0
    for row in t.itertuples(index=False):            # trades nao se sobrepoem: saldo na entrada = deposito + anteriores
        r.append(row.net / (0.02 * 0.5 * bal))
        bal += row.net
    assert m["soma_r"] == pytest.approx(sum(r), rel=1e-9)


def test_evaluate_uses_selected_formula(spec):
    res = scenario(spec, ["tp", "sl", "tp"])
    out = F.evaluate(res, 10000.0, formula=2)
    assert out["name"] == "Profit" and out["score"] == 0.0                 # 3 trades < piso 30
    assert out["line"].startswith("ALL_FORMULAS Profit=")
    assert F.evaluate(res, 10000.0)["formula"] == 7                        # default do EA
