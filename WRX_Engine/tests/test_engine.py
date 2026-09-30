"""Cenarios do motor com precos construidos a mao.

O ATR esperado e recalculado AQUI por um caminho independente (barras M1 do bid, TR e media
simples de 14 incluindo a barra parcial) -- nao reusa o codigo do motor.
"""
import math

import numpy as np
import pytest

from conftest import T0, base_path, build_ticks, epoch, make_params
from wrx_engine.engine import run_backtest

WARM = 130          # minutos antes do cenario (>= 100 barras de ATR exigidas pelo EA)
SPREAD = 0.00010


def ref_atr0(minute_bids, upto_minute, period=14):
    """ATR[0] no 1o tick do minuto `upto_minute` (barra parcial = so esse tick)."""
    bars = [(b[0], max(b), min(b), b[-1]) for b in minute_bids[:upto_minute]]
    bars.append((minute_bids[upto_minute][0],) * 4)
    tr = []
    for i in range(1, len(bars)):
        _, h, l, _ = bars[i]
        pc = bars[i - 1][3]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(tr[-period:]) / period


def scenario(after_entry, warm=WARM, **over):
    """warm minutos de ruido + minuto de entrada (j0) + minutos de `after_entry`."""
    mb = base_path(warm, step=0.0002)
    j0 = len(mb)
    entry_bid = mb[-1][-1]
    mb.append([entry_bid] * 4)
    mb.extend(after_entry(entry_bid))
    return mb, j0


def run(mb, j0, spec, side="buy", **over):
    ticks = build_ticks(mb)
    params = make_params(**over)
    hook_bar = {}
    res = run_backtest(params, spec, ticks,
                       signal_hook=lambda j, b: ((side == "buy") and j == j0, (side == "sell") and j == j0))
    return res, params


def expected_entry(mb, j0, params, spec, side):
    atr0 = ref_atr0(mb, j0)
    ask = round(mb[j0][0] + SPREAD, 5)
    bid = mb[j0][0]
    sl_d, tp_d = atr0 * params.stop, atr0 * params.take
    if side == "buy":
        return ask, spec.price_to_tick(ask - sl_d, False), spec.price_to_tick(ask + tp_d, True), sl_d
    return bid, spec.price_to_tick(bid + sl_d, True), spec.price_to_tick(bid - tp_d, False), sl_d


def test_buy_entry_prices_lot_and_take_profit_exit(spec):
    def after(e):
        return [[e, e + 0.0002, e + 0.0004, e + 0.0006]] + [[e + 0.02] * 4] + [[e + 0.02] * 4]
    mb, j0 = scenario(after)
    res, p = run(mb, j0, spec)
    price, sl, tp, sl_d = expected_entry(mb, j0, p, spec, "buy")
    t = res.trades.iloc[0]
    assert len(res.trades) == 1
    assert t.side == "buy" and t.open_price == price and t.sl == sl and t.tp == tp
    vol = math.floor(5.0 / (sl_d / 1e-5 * 1.0) / 0.01 + 1e-9) * 0.01
    assert t.volume == pytest.approx(max(round(vol, 2), 0.01))
    assert t.reason == "tp" and t.close_price == tp and t.gross > 0
    assert t.open_ms == (T0 + 60 * j0) * 1000


def test_buy_stop_loss_loses_about_one_r(spec):
    mb, j0 = scenario(lambda e: [[e, e - 0.0002, e - 0.0004, e - 0.0006]] + [[e - 0.05] * 4] * 2)
    res, p = run(mb, j0, spec)
    price, sl, tp, sl_d = expected_entry(mb, j0, p, spec, "buy")
    t = res.trades.iloc[0]
    assert t.reason == "sl" and t.close_price == sl
    assert t.gross == pytest.approx(-t.volume * (price - sl) / 1e-5)
    assert -1.0 <= t.r < -0.4      # ~1R perdido; o piso do passo de lote deixa um pouco abaixo


def test_sell_uses_ask_for_stop_and_bid_for_entry(spec):
    mb, j0 = scenario(lambda e: [[e, e + 0.0002, e + 0.0004, e + 0.0006]] + [[e + 0.05] * 4] * 2)
    res, p = run(mb, j0, spec, side="sell")
    price, sl, tp, _ = expected_entry(mb, j0, p, spec, "sell")
    t = res.trades.iloc[0]
    assert t.side == "sell" and t.open_price == price and t.sl == sl and t.tp == tp
    assert t.reason == "sl" and t.gross < 0


def test_stop_fill_policy_on_gap(spec):
    mb, j0 = scenario(lambda e: [[e - 0.05] * 4] * 2)        # o mercado abre 500 pips abaixo do SL
    hook = lambda j, b: (j == j0, False)
    lvl = run_backtest(make_params(), spec, build_ticks(mb), signal_hook=hook).trades.iloc[0]
    tck = run_backtest(make_params(), spec, build_ticks(mb), stop_fill="tick", signal_hook=hook).trades.iloc[0]
    assert lvl.close_price == lvl.sl                         # 'level': executa no preco do SL
    assert tck.close_price == round(mb[j0 + 1][0], 5) < tck.sl   # 'tick': no bid do tick que rompeu
    assert tck.gross < lvl.gross


def test_breakeven_is_evaluated_only_at_decisions_not_on_every_tick(spec):
    # Pico dentro do minuto (acima do gatilho de BE, abaixo do TP) que volta antes da proxima decisao:
    # o EA so olha o breakeven no 1o tick do minuto, entao o SL original segue valendo.
    mb0, j0 = scenario(lambda e: [[e] * 4])
    tp_d = ref_atr0(mb0, j0) * 3
    spike = 0.8 * tp_d                                        # > 50% do TP (gatilho), < 100%
    mb, j0 = scenario(lambda e: [[e, e + spike, e, e]] + [[e - 0.05] * 4] * 2)
    res, p = run(mb, j0, spec, AtivarBreakeven="true", BreakevenDistancia=0.5)
    _, sl, _, _ = expected_entry(mb, j0, p, spec, "buy")
    t = res.trades.iloc[0]
    assert t.reason == "sl" and t.close_price == sl and t.gross < 0


def test_breakeven_moves_sl_to_open_and_scratches_a_pullback(spec):
    # minuto 1: sobe ate quase o TP e fecha la; minuto 2 (decisao): BE dispara; minuto 3: volta ao preco de abertura
    mb0, j0 = scenario(lambda e: [[e]*4])
    atr0 = ref_atr0(mb0, j0)
    tp_d = atr0 * 3
    def after(e):
        up = e + tp_d * 0.7
        return [[e, e + 0.00005, up, up], [up] * 4, [up, e + 0.00003, e - 0.00002, e - 0.0001], [e - 0.05] * 4]
    mb, j0 = scenario(after)
    res, p = run(mb, j0, spec, AtivarBreakeven="true", BreakevenDistancia=0.5)
    t = res.trades.iloc[0]
    price = t.open_price
    assert t.reason == "sl" and t.sl == pytest.approx(price) and t.close_price == pytest.approx(price)
    assert t.gross == 0.0


def test_no_second_position_and_no_opposite_when_not_hedging(spec):
    mb, j0 = scenario(lambda e: [[e + 0.0001] * 4] * 3)
    ticks = build_ticks(mb)
    p = make_params()
    res = run_backtest(p, spec, ticks, signal_hook=lambda j, b: (j0 <= j <= j0 + 2, j0 <= j <= j0 + 2))
    assert len(res.trades) == 0 and len(res.open_positions) == 1    # 1 buy aberto; sell bloqueado (sem hedge)
    assert res.open_positions[0]["is_buy"]


def test_minimum_interval_between_entries_is_enforced(spec):
    # 1o tick do minuto de entrada chega tarde (:10); o SL estoura no 1o tick da barra seguinte (:00),
    # 50 s depois. A nova entrada nesse mesmo instante viola NextOpenTradeAfterBars(=60 s) -> bloqueada.
    mb, j0 = scenario(lambda e: [[e - 0.0012] * 4] * 3)
    ticks = build_ticks(mb)
    ticks.t_ms[4 * j0:4 * j0 + 4] += 10_000
    p = make_params()
    res = run_backtest(p, spec, ticks, signal_hook=lambda j, b: (j in (j0, j0 + 1), False))
    assert len(res.trades) == 1 and res.skipped["intervalo_minimo"] == 1 and not res.open_positions
    # com o 1o tick pontual (:00 e :00, 60 s), a reentrada e permitida
    res2 = run_backtest(p, spec, build_ticks(mb), signal_hook=lambda j, b: (j in (j0, j0 + 1), False))
    assert res2.skipped["intervalo_minimo"] == 0 and len(res2.trades) + len(res2.open_positions) == 2


def test_day_and_time_filters(spec):
    mb, j0 = scenario(lambda e: [[e + 0.05] * 4] * 2)
    saturday = epoch(2026, 3, 7, 9, 0)
    res = run_backtest(make_params(), spec, build_ticks(mb, t0=saturday), signal_hook=lambda j, b: (j == j0, False))
    assert len(res.trades) == 0 and len(res.open_positions) == 0
    # janela horaria: entrada em T0 + (WARM+1)min ~ 11:11 -> restringe a 12:00-13:00
    res2 = run_backtest(make_params(TOD_From_Hour=12, TOD_To_Hour=13), spec, build_ticks(mb),
                        signal_hook=lambda j, b: (j == j0, False))
    assert len(res2.trades) == 0 and len(res2.open_positions) == 0


def test_max_spread_blocks_wide_spread(spec):
    mb, j0 = scenario(lambda e: [[e + 0.05] * 4] * 2)
    ticks = build_ticks(mb, spread=0.0002)      # 20 pontos
    res = run_backtest(make_params(MaxSpread=15), spec, ticks, signal_hook=lambda j, b: (j == j0, False))
    assert len(res.trades) == 0 and len(res.open_positions) == 0
    res = run_backtest(make_params(MaxSpread=25), spec, ticks, signal_hook=lambda j, b: (j == j0, False))
    assert len(res.trades) + len(res.open_positions) == 1


def test_stops_level_pushes_sl_away_and_risk_gate_only_lets_it_through_at_broker_minimum(spec):
    from dataclasses import replace
    wide = replace(spec, stops_level=200)          # 0.002 > 2 x ATR
    mb, j0 = scenario(lambda e: [[e] * 4] * 2)
    hook = lambda j, b: (j == j0, False)
    # 1R = 5: o SL empurrado estoura o risco projetado -> o EA recusa a ordem
    res = run_backtest(make_params(), wide, build_ticks(mb), signal_hook=hook)
    assert res.skipped["risco_estourado"] == 1 and not res.open_positions
    # 1R = 1: lote cai no minimo do corretor, e ai o gate deixa passar (decisao do dono, 2026-08-24)
    res = run_backtest(make_params(PositionSizeValue=0.2), wide, build_ticks(mb), signal_hook=hook)
    pos = res.open_positions[0]
    assert pos["volume"] == 0.01 and pos["sl"] == pytest.approx(round(mb[j0][0] - 0.002, 5), abs=1e-5)


def test_engine_needs_warmup_bars_before_it_acts(spec):
    mb, j0 = scenario(lambda e: [[e] * 4] * 2, warm=40)
    res = run_backtest(make_params(), spec, build_ticks(mb), signal_hook=lambda j, b: (j == j0, False))
    assert len(res.trades) == 0 and len(res.open_positions) == 0     # < 100 barras: ProcessNewBar retorna


def test_real_macd_signals_invariants_on_random_walk(spec):
    mb = base_path(2500, seed=3, step=0.00012)
    res = run_backtest(make_params(Stop=1.5, Take=2.0, MaxShortTrades=0), spec, build_ticks(mb))
    t = res.trades
    assert len(t) > 10
    assert (t.side == "buy").all()
    assert (t.close_ms > t.open_ms).all()
    assert np.allclose(((t.volume / 0.01).round() * 0.01), t.volume)
    assert ((t.reason == "sl") | (t.reason == "tp")).all()
    assert np.allclose(np.where(t.reason == "sl", t.close_price - t.sl, t.close_price - t.tp), 0.0, atol=1e-9)
    # nunca duas posicoes ao mesmo tempo (MaxLongTrades=1)
    assert (t.open_ms.iloc[1:].to_numpy() >= t.close_ms.iloc[:-1].to_numpy()).all()
    again = run_backtest(make_params(Stop=1.5, Take=2.0, MaxShortTrades=0), spec, build_ticks(mb))
    assert again.trades.equals(t)          # deterministico


def test_risk_gate_rejects_when_tick_rounding_pushes_projected_loss_over_1r(spec):
    # ATR pequeno: SL de ~15.1 ticks arredonda para 16 -> perda projetada 0.33 x 16 = 5.28 > 5.005
    mb = base_path(WARM, step=0.00004)
    j0 = len(mb)
    mb.append([mb[-1][-1]] * 4)
    mb.append([mb[-1][-1] + 0.05] * 4)
    res = run_backtest(make_params(), spec, build_ticks(mb), signal_hook=lambda j, b: (j == j0, False))
    assert res.skipped["risco_estourado"] == 1
    assert len(res.trades) == 0 and len(res.open_positions) == 0


def test_sell_stop_triggers_on_ask_not_bid(spec):
    mb0, j0 = scenario(lambda e: [[e] * 4])
    p = make_params()
    _, sl, _, _ = expected_entry(mb0, j0, p, spec, "sell")
    # bid fica 5 pontos ABAIXO do SL; o ask (bid + spread 10 pts) fica 5 ACIMA -> so o ask rompe
    bid_at = round(sl - 0.00005, 5)
    mb, j0 = scenario(lambda e: [[e] * 4, [bid_at] * 4, [e - 0.05] * 4])
    res, _ = run(mb, j0, spec, side="sell")
    t = res.trades.iloc[0]
    assert t.reason == "sl" and t.close_ms == (T0 + 60 * (j0 + 2)) * 1000      # minuto do bid_at


def _naive_macd_buy_reversal_bars(closes, fast=12, slow=26):
    def ema(x, n):
        a, out = 2 / (n + 1), [x[0]]
        for v in x[1:]:
            out.append(a * v + (1 - a) * out[-1])
        return out
    f, s = ema(closes, fast), ema(closes, slow)
    main = [a - b for a, b in zip(f, s)]
    return main


def test_real_macd_reversal_signal_wiring_against_naive_loop(spec):
    """Confere os SHIFTS do sinal (barras 1,2,3 fechadas) contra um laco ingenuo escrito a partir do .mq5:
       IsBuyEntryReversal = main[1] > main[2] && main[2] < main[3]  (0 = barra em formacao)."""
    from wrx_engine.bars import m1_from_ticks, resample
    from wrx_engine.engine import _combine, _signal_arrays

    mb = base_path(600, seed=11, step=0.00015)
    ticks = build_ticks(mb)
    p = make_params(EntryMethod=0)
    m1, _ = m1_from_ticks(ticks)
    rev_b, rev_s, *_ = _signal_arrays(p, resample(m1, 1))
    main = _naive_macd_buy_reversal_bars(list(m1.close))
    for b in range(4, len(m1)):
        want_buy = main[b - 1] > main[b - 2] and main[b - 2] < main[b - 3]
        want_sell = main[b - 1] < main[b - 2] and main[b - 2] > main[b - 3]
        assert bool(rev_b[b]) == want_buy and bool(rev_s[b]) == want_sell, b
    assert rev_b.sum() > 20 and rev_s.sum() > 20

    # integracao: cada barra pronta (>= 100 barras) em que o laco ingenuo manda comprar e uma TENTATIVA de entrada.
    # Antes da 1a posicao nada bloqueia, entao cada tentativa que nao virou trade foi vetada pelo gate de risco
    # (arredondamento de tick) -- o motor tem que ter contado exatamente essas.
    res = run_backtest(make_params(EntryMethod=0, MaxShortTrades=0, Stop=3.0, Take=3.0), spec, ticks)
    candidates = [b for b in range(99, len(m1)) if main[b - 1] > main[b - 2] and main[b - 2] < main[b - 3]]
    first = (res.trades.open_ms.iloc[0] if len(res.trades) else res.open_positions[0]["open_ms"])
    entered_bar = (first // 1000 - T0) // 60
    assert entered_bar in candidates
    assert res.skipped["risco_estourado"] >= candidates.index(entered_bar)
    assert res.skipped["lote_zero"] == 0 and res.skipped["intervalo_minimo"] == 0


def test_higher_signal_timeframe_decides_only_on_first_minute_of_each_bar(spec):
    """TimeFrame=M5: o sinal e avaliado 1x por barra M5 (na 1a decisao M1 dela), com ATR ainda em M1."""
    mb = base_path(3000, seed=5, step=0.00015)
    res = run_backtest(make_params(TimeFrame=1, EntryMethod=6, Stop=3.0, Take=3.0), spec, build_ticks(mb))
    assert len(res.trades) > 5
    minutes = (res.trades.open_ms // 1000 - T0) // 60
    assert ((T0 // 60 + minutes) % 5 == 0).all()
    res1 = run_backtest(make_params(TimeFrame=0, EntryMethod=6, Stop=3.0, Take=3.0), spec, build_ticks(mb))
    m1 = (res1.trades.open_ms // 1000 - T0) // 60
    assert ((T0 // 60 + m1) % 5 != 0).any()          # em M1 as entradas nao ficam presas a multiplos de 5
