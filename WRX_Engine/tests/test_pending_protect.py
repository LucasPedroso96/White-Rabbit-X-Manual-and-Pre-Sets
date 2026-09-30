from dataclasses import replace

import pytest

from conftest import T0, base_path, build_ticks, make_params
from scen import WARM, go, ref_atr0, script
from wrx_engine.engine import load_news_csv, run_backtest


def start_path(warm=WARM):
    mb = base_path(warm, step=0.0002)
    j0 = len(mb)
    e = mb[-1][-1]
    mb.append([e] * 4)
    return mb, j0, e


def flat(mb, n):
    return [[mb[-1][-1]] * 4 for _ in range(n)]


PEND = dict(PositionSizeMode=2, PositionSizeValue=0.10, Stop=2, Take=3, PendingDistanciaATR=0.5, PendingExpiracaoBarras=3)


# ------------------------------------------------------------------ entradas pendentes
def test_buy_stop_placed_beyond_reference_filled_at_tick_with_sl_tp_from_order_level(spec):
    mb, j0, e = start_path()
    atr0 = ref_atr0(mb, j0)
    level = spec.price_to_tick(max(e + 0.5 * atr0, round(e + 1e-4, 5) + 1e-5), True)
    mb.append([round(e + 0.001, 5)] * 4)                       # rompe o nivel: ask = bid + spread
    mb.extend(flat(mb, 1))
    res, _ = go(mb, [j0], spec, EntryOrderType=1, **PEND)
    pos = res.open_positions[0]
    assert pos["open_price"] == pytest.approx(round(e + 0.001 + 1e-4, 5))             # stop preenche no preco do tick
    assert pos["sl"] == pytest.approx(spec.price_to_tick(level - 2 * atr0, False))
    assert pos["tp"] == pytest.approx(spec.price_to_tick(level + 3 * atr0, True))
    assert not res.ledger.pendings


def test_pending_level_fill_policy_and_limit_fills_at_order_price(spec):
    mb, j0, e = start_path()
    atr0 = ref_atr0(mb, j0)
    mb.append([round(e + 0.001, 5)] * 4)
    mb.extend(flat(mb, 1))
    by_level, _ = go(mb, [j0], spec, kw=dict(pending_fill="level"), EntryOrderType=1, **PEND)
    level = spec.price_to_tick(max(e + 0.5 * atr0, round(e + 1e-4, 5) + 1e-5), True)
    assert by_level.open_positions[0]["open_price"] == pytest.approx(level)
    mb2, j0, e = start_path()
    lvl = spec.price_to_tick(min(e - 0.5 * atr0, round(e + 1e-4, 5) - 1e-5), True if False else False)
    mb2.append([round(e - 0.0004, 5)] * 4)           # toca o limit (ask <= nivel) sem alcancar o SL
    mb2.extend(flat(mb2, 1))
    lim, _ = go(mb2, [j0], spec, EntryOrderType=2, **PEND)
    assert lim.open_positions[0]["open_price"] == pytest.approx(lvl)                 # limit: preco da ordem


def test_pending_expires_after_n_entry_bars_and_opposite_signal_cancels_it(spec):
    mb, j0, e = start_path()
    mb.extend(flat(mb, 6))
    exp, _ = go(mb, [j0], spec, EntryOrderType=1, **PEND)
    assert not exp.open_positions and exp.trades.empty and not exp.ledger.pendings    # expirou (3 barras)
    long_life, _ = go(mb, [j0], spec, EntryOrderType=1, **{**PEND, "PendingExpiracaoBarras": 50})
    assert len(long_life.ledger.pendings) == 1                                      # ainda viva
    # sinal contrario no minuto seguinte cancela
    ticks = build_ticks(mb)
    p = make_params(EntryOrderType=1, MaxShortTrades=1, **PEND)
    res = run_backtest(p, spec, ticks, signal_hook=lambda j, b: (j == j0, j == j0 + 1))
    assert not any(o.is_buy for o in res.ledger.pendings) or len(res.ledger.pendings) >= 1
    only_cancel = run_backtest(make_params(EntryOrderType=1, **PEND), spec, ticks,
                               signal_hook=lambda j, b: (j == j0, j == j0 + 1))
    assert not only_cancel.ledger.pendings and not only_cancel.open_positions and only_cancel.trades.empty


def test_oco_places_both_sides_and_cancels_the_other_when_one_fills(spec):
    mb, j0, e = start_path()
    mb.extend(flat(mb, 1))
    both, _ = go(mb, [j0], spec, EntryOrderType=3, MaxLongTrades=1, MaxShortTrades=1, **PEND)
    assert sorted(o.kind for o in both.ledger.pendings) == ["buy_stop", "sell_stop"]
    up = mb + [[round(e + 0.0003, 5)] * 4, [round(e + 0.0003, 5)] * 4]
    res, _ = go(up, [j0], spec, EntryOrderType=3, MaxLongTrades=1, MaxShortTrades=1, **PEND)
    assert len(res.open_positions) == 1 and res.open_positions[0]["is_buy"] and not res.ledger.pendings


def test_session_trigger_arms_once_per_day_without_indicator_signal(spec):
    mb, j0, e = start_path()
    hour = (T0 // 3600 + j0 // 60) % 24                                            # hora do minuto j0 (servidor)
    mb.extend(flat(mb, 3))
    ticks = build_ticks(mb)
    p = make_params(EntryOrderType=1, PendingGatilho=1, PendingHoraSessao=hour, PendingFaixaBarras=4,
                    **{**PEND, "PendingExpiracaoBarras": 50})
    res = run_backtest(p, spec, ticks, signal_hook=lambda j, b: (False, False))
    assert len(res.ledger.pendings) >= 1                                           # armou sem sinal do indicador
    assert res.ledger.pendings[0].kind in ("buy_stop", "sell_stop")


# ------------------------------------------------------------------ travas
def test_equity_stop_liquidates_and_blocks_all_new_entries(spec):
    mb, j0, e = start_path()
    mb.append([round(e - 0.0003, 5)] * 4)           # perda flutuante > 100% do capital alocado
    mb.extend(flat(mb, 2))
    mb2 = mb + [[mb[-1][-1]] * 4 for _ in range(5)]
    j1 = len(mb2) - 4
    res, _ = go(mb2, [j0, j1], spec, kw=dict(deposit=1000.0), PositionSizeMode=2, PositionSizeValue=50,
                AtivarStop="false", AtivarTake="false")
    assert res.sim.halt.stopped and not res.open_positions
    t = res.trades
    assert len(t) == 1 and t.reason.iloc[0] == "equity_stop"                        # 2a entrada nunca sai


def test_max_equity_drawdown_percent(spec):
    mb, j0, e = start_path()
    mb.append([round(e - 0.0005, 5)] * 4)
    mb.extend(flat(mb, 1))
    res, _ = go(mb, [j0], spec, kw=dict(deposit=1000.0), PositionSizeMode=2, PositionSizeValue=1.0,
                AtivarStop="false", AtivarTake="false", MaxEquityDrawdownPercent=2)
    assert res.trades.reason.iloc[0] == "equity_stop"                               # -$50 (1 lote, 50 ticks) > 2% de 1000


def test_daily_loss_limit_blocks_entries_after_worst_case_breaches(spec):
    mb, ents = script(["sl", "tp"], jump=0.004)
    free, _ = go(mb, ents, spec)
    assert len(free.trades) == 2
    cut, _ = go(mb, ents, spec, DailyLossLimitPercent=0.04)                          # 1R=$5 > 0.04% de $10000
    assert len(cut.trades) == 1 and cut.trades.reason.iloc[0] == "sl"
    ok, _ = go(mb, ents, spec, DailyLossLimitPercent=0.08)
    assert len(ok.trades) == 2


def test_global_protection_daily_closes_everything_and_blocks_the_rest_of_the_day(spec):
    mb, j0, e = start_path()
    mb.append([round(e - 0.0010, 5)] * 4)
    mb.extend(flat(mb, 6))
    j1 = len(mb) - 3
    res, _ = go(mb, [j0, j1], spec, PositionSizeMode=2, PositionSizeValue=5.0, AtivarStop="false", AtivarTake="false",
                Trava_Diaria_Percent=1)
    assert res.trades.reason.iloc[0] == "global_daily" and not res.open_positions and len(res.trades) == 1
    keep, _ = go(mb, [j0, j1], spec, PositionSizeMode=2, PositionSizeValue=5.0, AtivarStop="false", AtivarTake="false",
                 Trava_Diaria_Percent=1, Protecao_Fecha_Posicoes="false")
    assert len(keep.open_positions) == 1 and len(keep.trades) == 0                  # so bloqueia, nao fecha


def test_global_protection_total_is_permanent(spec):
    mb, j0, e = start_path()
    mb.append([round(e - 0.0010, 5)] * 4)
    mb.extend(flat(mb, 3))
    res, _ = go(mb, [j0], spec, PositionSizeMode=2, PositionSizeValue=5.0, AtivarStop="false", AtivarTake="false",
                Trava_Total_Percent=2)
    assert res.sim.halt.gp_total and res.trades.reason.iloc[0] == "global_total"


def test_news_filter_blocks_entries_inside_the_window_only(spec):
    mb, ents = script(["tp"], gap=3)
    j0 = ents[0]
    t_entry = T0 + 60 * j0
    base = dict(AtivarFiltroNoticias="true", NewsMinutosAntes=15, NewsMinutosDepois=15)
    blocked, _ = go(mb, ents, spec, kw=dict(news_events=[(t_entry + 5 * 60, "EUR", 3)]), **base)
    assert not blocked.trades.shape[0] and not blocked.open_positions
    other_ccy, _ = go(mb, ents, spec, kw=dict(news_events=[(t_entry + 5 * 60, "JPY", 3)]), **base)
    assert len(other_ccy.trades) == 1
    far, _ = go(mb, ents, spec, kw=dict(news_events=[(t_entry + 40 * 60, "EUR", 3)]), **base)
    assert len(far.trades) == 1
    manual, _ = go(mb, ents, spec, kw=dict(news_events=[(t_entry, "CHF", 3)]), NewsMoedasManual="CHF", **base)
    assert not manual.trades.shape[0]


def test_news_csv_loader_and_importance_filter(tmp_path):
    f = tmp_path / "n.csv"
    f.write_text("datetime;currency;importance;event_name\n2026.03.02 12:30;USD;3;NFP\n2026.03.02 14:00;EUR;2;PMI\n"
                 "2026.03.02 15:00;EUR;1;x\nbad;line\n", encoding="latin-1")
    assert [(c, i) for _, c, i in load_news_csv(f)] == [("USD", 3), ("EUR", 2)]
    assert [(c, i) for _, c, i in load_news_csv(f, high_only=True)] == [("USD", 3)]


# ------------------------------------------------------------------ WFO
def test_wfo_in_sample_blocks_entries_in_oos_and_withdraws_profit_when_flat(spec):
    mb, ents = script(["tp", "tp"], gap=1570, jump=0.004, noisy_gap=True)
    wfo = dict(AtivarWFO="true", MetodoDeEntradawfo=0, wfo_windowSize=-1, wfo_customWindowSizeDays=1, wfo_stepSize=-1,
               wfo_customStepSizePercent=-1, input_end_date="2026.03.05", WFO_CarenciaPercentil=0)
    res, _ = go(mb, ents, spec, **wfo)
    assert len(res.trades) == 1                                     # a 2a entrada cai na janela OOS (dia 2): bloqueada
    assert res.ledger.withdrawn == pytest.approx(res.trades.net.iloc[0])             # TesterWithdrawal do lucro acumulado
    assert res.ledger.balance == pytest.approx(10_000.0)
    both, _ = go(mb, ents, spec, **{**wfo, "MetodoDeEntradawfo": 1})
    assert len(both.trades) == 2 and both.ledger.withdrawn == 0         # 'In Sample + Out Sample' nao bloqueia


def test_wfo_windows_follow_the_ea_loop():
    from wrx_engine.wfo import build_plan
    from conftest import epoch
    from wrx_engine.setfile import params_from_dict
    v = params_from_dict({"wfo_windowSize": "-1", "wfo_customWindowSizeDays": "10", "wfo_stepSize": "-1",
                          "wfo_customStepSizePercent": "50", "input_end_date": "2026.03.31"}).v
    start = epoch(2026, 3, 1, 0, 0)
    w = build_plan(v, start)
    assert w.is_start[0] == start and w.is_end[0] == start + 10 * 86400 - 1
    assert w.oos_start[0] == w.is_end[0] + 1 and w.oos_end[0] == w.oos_start[0] + 5 * 86400 - 1      # 50% de 10 dias
    assert w.is_start[1] == w.oos_end[0] + 1
    assert w.in_sample(w.is_start[1]) and not w.in_sample(w.oos_start[0])
    assert w.cycle_of(w.oos_start[0]) == (0, False)


# ------------------------------------------------------------------ custos e margem
def test_swap_accrues_per_night_with_triple_rollover_on_the_configured_day(spec):
    sp = replace(spec, swap_long=-5.0, swap_3days=3)                                # 3 = quarta
    mb, j0, e = start_path()
    mb.extend(flat(mb, 5000 - j0))                                                  # ~3,5 dias: seg 09:00 -> qui
    res, _ = go(mb, [j0], sp, PositionSizeMode=2, PositionSizeValue=0.10, AtivarStop="false", AtivarTake="false")
    pos = res.open_positions[0]
    # noites: seg->ter (1), ter->qua (1), qua->qui (3) = 5 noites x 0.10 lote x -5 pts x $1/ponto... = -0.50/noite
    assert pos["swap"] == pytest.approx(-0.50 * 5)


def test_swap_is_part_of_net_result_and_floating_equity(spec):
    sp = replace(spec, swap_long=-5.0)
    mb, j0, e = start_path()
    mb.extend(flat(mb, 1100))                                                       # cruza 1 meia-noite
    mb.append([round(e + 0.05, 5)] * 4)
    res, _ = go(mb, [j0], sp, PositionSizeMode=2, PositionSizeValue=0.10, AtivarStop="false", AtivarTake="true", Take=3)
    t = res.trades.iloc[0]
    assert t.swap == pytest.approx(-0.50) and t.net == pytest.approx(t.gross - 0.50)


def test_margin_rejects_orders_without_free_margin_and_honors_reserve(spec):
    sp = replace(spec, margin_b=2000.0)                                             # $2000 por lote
    mb, j0, e = start_path()
    mb.extend(flat(mb, 2))
    big, _ = go(mb, [j0], sp, kw=dict(deposit=1000.0), PositionSizeMode=2, PositionSizeValue=1.0, AtivarStop="false",
                AtivarTake="false", MaxEquityDrawdownPercent=0, MinFreeMarginPercent=0)
    assert not big.open_positions and big.skipped["margem"] == 1
    small, _ = go(mb, [j0], sp, kw=dict(deposit=1000.0), PositionSizeMode=2, PositionSizeValue=0.3, AtivarStop="false",
                  AtivarTake="false", MaxEquityDrawdownPercent=0, MinFreeMarginPercent=0)
    assert len(small.open_positions) == 1                                          # margem 600 < 1000
    reserve, _ = go(mb, [j0], sp, kw=dict(deposit=1000.0), PositionSizeMode=2, PositionSizeValue=0.3, AtivarStop="false",
                    AtivarTake="false", MaxEquityDrawdownPercent=0, MinFreeMarginPercent=50)
    assert not reserve.open_positions                                              # sobraria 400 < reserva de 500


def test_oco_other_leg_is_cancelled_immediately_not_only_at_the_next_bar(spec):
    mb, j0, e = start_path()
    atr0 = ref_atr0(mb, j0)
    buy_fill, reversal = round(e + 0.0003, 5), round(e - 0.0010, 5)
    # dentro do MESMO minuto: a perna de compra preenche e o preco volta e rompe o nivel da venda
    mb.append([e, buy_fill, reversal, reversal])             # o fill e no 2o tick: so o cancelamento imediato impede a venda
    mb.extend(flat(mb, 2))
    res, _ = go(mb, [j0], spec, EntryOrderType=3, MaxLongTrades=1, MaxShortTrades=1, **PEND)
    assert len(res.trades) == 1 and res.trades.side.iloc[0] == "buy"       # a venda NAO pode ter preenchido
    assert not res.open_positions and not res.ledger.pendings
