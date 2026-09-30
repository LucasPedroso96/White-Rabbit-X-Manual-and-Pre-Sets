import pytest

from conftest import T0, base_path, build_ticks, make_params
from scen import WARM, go, ref_atr0
from wrx_engine.engine import run_backtest
from wrx_engine.sizing import normalize_trade_volume_nearest


def flat_after(mb, n=1):
    return [[mb[-1][-1]] * 4 for _ in range(n)]


def start_path(warm=WARM):
    mb = base_path(warm, step=0.0002)
    j0 = len(mb)
    e = mb[-1][-1]
    mb.append([e] * 4)
    return mb, j0, e


# ------------------------------------------------------------------ trailing
TRAIL = dict(PositionSizeMode=2, PositionSizeValue=0.10, AtivarTake="false", AtivarStop="true", Stop=6,
             AtivarTrailATR="true", Trail=2, TrailVela=0, MetodoDeCalculo=1, AtivarBreakeven="false")


def test_trailing_ratchets_sl_up_with_close_price_and_never_back_down(spec):
    mb, j0, e = start_path()
    for i in range(1, 7):
        mb.append([e + 0.0004 * i] * 4)            # sobe 4 pontos-de-ATR aprox. por minuto
    top = mb[-1][-1]
    mb.append([top - 0.0003] * 4)                   # recuo pequeno: o SL nao pode descer
    res, p = go(mb, [j0], spec, **TRAIL)
    pos = res.open_positions[0]
    last = len(mb) - 1
    # SL = maximo de (Close[0] - ATR[0]*Trail) ja visto, avaliado no 1o tick de cada minuto
    best = 0.0
    for m in range(j0 + 1, last + 1):
        cand = mb[m][0] - ref_atr0(mb, m) * 2
        if cand > best and cand < mb[m][0]:
            best = cand
    assert pos["sl"] == pytest.approx(best, abs=2e-5)
    assert pos["sl"] > pos["open_price"] - 6 * ref_atr0(mb, j0)           # subiu acima do SL inicial
    # o SL inicial (Stop=6 ATR abaixo da entrada) e o piso do trailing
    assert pos["sl"] > 0


def test_trail_only_in_profit_does_not_move_sl_below_open(spec):
    mb, j0, e = start_path()
    mb.append([e + 0.0001] * 4)
    mb.append([e + 0.0002] * 4)
    res, _ = go(mb, [j0], spec, **{**TRAIL, "TrailSoLucro": "true", "Trail": 30})        # trail calcula muito abaixo da entrada
    pos = res.open_positions[0]
    assert pos["sl"] == pytest.approx(pos["open_price"] - 6 * ref_atr0(mb, j0), abs=2e-5)   # SL inicial intacto


def test_trail_is_evaluated_once_per_entry_timeframe_bar(spec):
    mb, j0, e = start_path(260)                       # j0 alinhado a barra M5 e >= 50 barras M5
    for i in range(1, 12):
        mb.append([e + 0.0005 * i] * 4)
    res1, _ = go(mb, [j0], spec, **{**TRAIL, "TimeFrame": 1})                            # M5: o trail so anda a cada 5 min
    res0, _ = go(mb, [j0], spec, **TRAIL)                                                 # M1: a cada minuto
    assert res0.open_positions[0]["sl"] > res1.open_positions[0]["sl"]


# ------------------------------------------------------------------ take organico
def test_organic_take_closes_at_market_when_price_beats_last_entry_by_atr_take(spec):
    mb, j0, e = start_path()
    tp_d = ref_atr0(mb, j0) * 3
    mb.append([e + tp_d * 0.5] * 4)                 # meio caminho: nada
    mb.append([e + tp_d * 1.5] * 4)                 # passa: fecha no bid desse tick (nao no nivel)
    mb.append([e + tp_d * 1.5] * 4)
    res, _ = go(mb, [j0], spec, PositionSizeMode=2, PositionSizeValue=0.10, TakeOrganico="true", AtivarTake="false")
    t = res.trades.iloc[0]
    assert t.reason == "take_organico" and t.close_price == pytest.approx(round(e + tp_d * 1.5, 5))
    assert t.close_ms == (T0 + 60 * (j0 + 2)) * 1000


# ------------------------------------------------------------------ grid classico
GRID = dict(GridMode=1, PositionSizeMode=2, PositionSizeValue=0.10, AtivarStop="false", AtivarTake="true", Take=3,
            MaxLongTrades=5, MaxShortTrades=0, UsarsomenteATRGRID="true", DistanciaMinima=2, Multiplicador=1,
            AtivarBreakeven="false")


def test_classic_grid_seed_continuation_basket_target_and_cycle_reset(spec):
    mb, j0, e = start_path()
    atr_seed = ref_atr0(mb, j0)
    drop = 0.0030
    mb.append([e - drop] * 4)                        # cai alem de DistanciaMinima*ATR -> 2a perna
    mb.extend(flat_after(mb, 2))
    mb.append([e + 0.02] * 4)                        # rally forte -> alvo da cesta
    mb.extend(flat_after(mb, 2))
    res, p = go(mb, [j0], spec, **GRID)
    t = res.trades
    assert len(t) == 2 and set(t.reason) == {"grid_target"}
    assert t.close_ms.nunique() == 1                 # a cesta fecha inteira no mesmo tick
    # perna 1: lote-base
    assert t.volume.iloc[0] == pytest.approx(0.10)
    # alvo congelado na semente: lucro de 1 lote ate ATR*Take x lote x Multiplicador
    ask = round(e + 1e-4, 5)
    tp_d = atr_seed * 3
    target_px = spec.price_to_tick(ask + tp_d, True)
    ppl = (target_px - ask) / 1e-5 * 1.0
    target = ppl * 0.10
    # perna 2: lote que fecharia o alvo no proximo nivel (CalculateGridVolume), arredondado ao passo mais proximo
    atr_leg2 = ref_atr0(mb, j0 + 1)
    ask2 = round(e - drop + 1e-4, 5)
    ppl2 = (spec.price_to_tick(ask2 + atr_leg2 * 3, True) - ask2) / 1e-5 * 1.0
    pnl_leg1 = (round(e - drop, 5) - ask) / 1e-5 * 1.0 * 0.10
    want = max(0.10, (target - pnl_leg1) / ppl2)
    assert t.volume.iloc[1] == pytest.approx(normalize_trade_volume_nearest(want, spec), abs=1e-9)
    assert t.gross.sum() >= target - 1e-6            # o fechamento so acontece com PnL do ciclo >= alvo
    assert res.ledger.grid[1].cycle_start == 0 and not res.open_positions


def test_grid_needs_signal_for_continuation_unless_atr_only(spec):
    mb, j0, e = start_path()
    mb.append([e - 0.003] * 4)
    mb.extend(flat_after(mb, 3))
    only_atr, _ = go(mb, [j0], spec, **GRID)
    needs_sig, _ = go(mb, [j0], spec, **{**GRID, "UsarsomenteATRGRID": "false"})
    assert len(only_atr.open_positions) == 2 and len(needs_sig.open_positions) == 1


def test_grid_respects_max_trades_per_side(spec):
    mb, j0, e = start_path()
    for i in range(1, 8):
        mb.append([e - 0.003 * i] * 4)
    res, _ = go(mb, [j0], spec, **{**GRID, "MaxLongTrades": 3})
    assert len(res.open_positions) == 3


# ------------------------------------------------------------------ piramide (12_GRID_INVERSO)
PYR = dict(GridMode=3, PositionSizeMode=2, PositionSizeValue=0.10, AtivarStop="true", Stop=6, AtivarTake="false",
           AtivarTrailATR="true", Trail=0.5, TrailVela=0, MaxLongTrades=5, MaxShortTrades=0, UsarsomenteATRGRID="true",
           DistanciaMinima=2, Multiplicador=0.5, AtivarBreakeven="false")


def test_pyramid_adds_levels_with_the_price_geometric_lots_and_closes_basket_by_trailing(spec):
    mb, j0, e = start_path(765)                       # j0 alinhado a barra M15 (>= 50 barras): o trailing por perna nao roda na janela
    mb.append([e + 0.003] * 4)                       # sobe >= DistanciaMinima*ATR: 2a perna, lote 0.10*0.5
    mb.append([e + 0.006] * 4)                       # novo topo (3a perna nasce aqui)
    mb.append([e + 0.006 - 0.0015] * 4)              # recuo > ATR*Trail e < Stop: sai a cesta pelo trailing
    mb.extend(flat_after(mb, 2))
    res, p = go(mb, [j0], spec, **{**PYR, "TimeFrame": 2})
    t = res.trades
    assert len(t) >= 2 and set(t.reason) == {"pyramid_trail"}
    assert list(t.volume.iloc[:2]) == [0.10, 0.05]
    assert t.open_price.iloc[1] > t.open_price.iloc[0]                # empilha A FAVOR do preco
    assert t.close_ms.nunique() == 1 and res.ledger.pyr[1].cycle_start == 0
    peak = round(e + 0.006, 5)
    atr_snap = ref_atr0(mb, j0 + 2)                                   # ATR do ultimo ProcessNewBar antes da saida
    assert t.close_price.iloc[0] == pytest.approx(round(e + 0.006 - 0.0015, 5))
    assert (peak - t.close_price.iloc[0]) >= 0.5 * atr_snap


def test_pyramid_legs_also_trail_individually_when_the_entry_bar_changes(spec):
    mb, j0, e = start_path()
    mb.append([e + 0.003] * 4)
    mb.append([e + 0.006] * 4)
    mb.append([e + 0.006 - 0.0015] * 4)
    mb.extend(flat_after(mb, 2))
    res, _ = go(mb, [j0], spec, **PYR)                                # M1: TrailingStopSet sobe o SL de cada perna
    assert set(res.trades.reason) <= {"sl", "pyramid_trail"} and len(res.trades) >= 2
    assert (res.trades.close_price.iloc[0] > res.trades.open_price.iloc[0])


def test_pyramid_never_stacks_on_a_leg_that_still_has_no_stop(spec):
    # Sem AtivarStop a perna nasce sem SL; o TrailingStopSet so cria o SL quando a barra do TF de entrada muda (M5).
    mb, j0, e = start_path(260)
    mb.append([e + 0.003] * 4)                       # mesma barra M5: perna 1 ainda sem SL -> bloqueia a 2a
    early = flat_after(mb, 1)
    mb_a = mb + early
    res_a, _ = go(mb_a, [j0], spec, **{**PYR, "AtivarStop": "false", "TimeFrame": 1})
    assert len(res_a.open_positions) == 1 and res_a.open_positions[0]["sl"] == 0.0
    mb_b = mb + [[e + 0.003] * 4 for _ in range(4)]   # barra M5 seguinte: o trailing cria o SL e libera a 2a perna
    res_b, _ = go(mb_b, [j0], spec, **{**PYR, "AtivarStop": "false", "TimeFrame": 1})
    assert len(res_b.open_positions) == 2
    assert res_b.open_positions[0]["sl"] > 0 and res_b.open_positions[1]["sl"] == 0.0    # a 2a nasce nua ate a proxima barra


def test_grid_basket_closes_exactly_when_cycle_pnl_reaches_the_frozen_target(spec):
    mb, j0, e = start_path()
    atr_seed = ref_atr0(mb, j0)
    mb.append([e - 0.0030] * 4)
    res0, _ = go(mb + flat_after(mb, 1), [j0], spec, **GRID)
    v1, v2 = res0.open_positions[0]["volume"], res0.open_positions[1]["volume"]
    a1, a2 = res0.open_positions[0]["open_price"], res0.open_positions[1]["open_price"]
    tp_px = spec.price_to_tick(a1 + atr_seed * 3, True)
    target = (tp_px - a1) / 1e-5 * 0.10                              # alvo congelado na semente
    # bid p* em que o PnL flutuante das 2 pernas (ao bid) iguala o alvo
    k_ = 1.0 / 1e-5
    p_star = (target + v1 * a1 * k_ + v2 * a2 * k_) / ((v1 + v2) * k_)
    above = round(p_star + 0.00005, 5)
    below = round(p_star - 0.00020, 5)
    hit, _ = go(mb + [[above] * 4, [above] * 4], [j0], spec, **GRID)
    miss, _ = go(mb + [[below] * 4, [below] * 4], [j0], spec, **GRID)
    assert len(hit.trades) == 2 and set(hit.trades.reason) == {"grid_target"}
    assert len(miss.trades) == 0 and len(miss.open_positions) == 2
    assert hit.trades.gross.sum() >= target - 1e-6


def test_pyramid_peak_is_tracked_tick_by_tick_inside_the_minute(spec):
    mb, j0, e = start_path(765)
    mb.append([e + 0.003] * 4)                                        # 2a perna
    peak, after = round(e + 0.006, 5), round(e + 0.006 - 0.0015, 5)
    mb.append([round(e + 0.003, 5), peak, after, after])             # o topo e um tick NO MEIO do minuto
    mb.extend(flat_after(mb, 1))
    res, _ = go(mb, [j0], spec, **{**PYR, "TimeFrame": 2})
    t = res.trades
    assert len(t) == 2 and set(t.reason) == {"pyramid_trail"}
    assert t.close_price.iloc[0] == pytest.approx(after)


def test_reversal_exit_on_opposite_order_closes_the_other_side_on_the_next_tick(spec):
    mb, j0, e = start_path()
    for _ in range(3):
        mb.append([e] * 4)
    j1 = len(mb) - 1
    ticks = build_ticks(mb)
    p = make_params(ReversalExitMode=1, Hedging="true", MaxLongTrades=1, MaxShortTrades=1, PositionSizeMode=2,
                    PositionSizeValue=0.10, AtivarStop="false", AtivarTake="false")
    res = run_backtest(p, spec, ticks, signal_hook=lambda j, b: (j == j1, j == j0))        # venda em j0, compra em j1
    t = res.trades
    assert len(t) == 1 and t.side.iloc[0] == "sell" and t.reason.iloc[0] == "opposite_order"
    assert len(res.open_positions) == 1 and res.open_positions[0]["is_buy"]                # a compra que disparou segue aberta
    assert t.close_ms.iloc[0] > res.open_positions[0]["open_ms"]                            # fechou no tick SEGUINTE


def test_reversal_exit_on_opposite_order_is_rejected_without_hedging():
    from wrx_engine.setfile import oninit_errors, params_from_dict
    v = params_from_dict({"ReversalExitMode": "1", "Hedging": "false", "MaxLongTrades": "1", "MaxShortTrades": "1"}).v
    assert any("ordem oposta" in e for e in oninit_errors(v))
