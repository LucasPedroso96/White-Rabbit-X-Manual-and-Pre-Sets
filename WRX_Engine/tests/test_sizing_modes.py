import pytest

from scen import go, script


def test_fixed_lot_no_sl_no_tp_signal_only(spec):
    mb, ents = script(["tp"], gap=3)
    res, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.05, AtivarStop="false", AtivarTake="false")
    assert len(res.trades) == 0 and len(res.open_positions) == 1        # 11_SIGNAL_ONLY: sem SL/TP nada fecha
    pos = res.open_positions[0]
    assert pos["volume"] == 0.05 and pos["sl"] == 0.0 and pos["tp"] == 0.0


def test_fixed_lot_with_sl_tp(spec):
    mb, ents = script(["tp", "sl"])
    res, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.07)
    assert list(res.trades.volume) == [0.07, 0.07] and list(res.trades.reason) == ["tp", "sl"]


def test_monetary_lot_is_initial_capital_over_value_and_ignores_balance_growth(spec):
    mb, ents = script(["tp", "tp"])
    res, _ = go(mb, ents, spec, kw=dict(deposit=10_000.0), PositionSizeMode=1, PositionSizeValue=5000)
    assert list(res.trades.volume) == [2.0, 2.0]                        # 10000/5000, base FIXA (nao compoe)
    res2, _ = go(mb, ents, spec, kw=dict(deposit=10_000.0), PositionSizeMode=1, PositionSizeValue=5000,
                 TradeCapitalPercentage=50)
    assert list(res2.trades.volume) == [1.0, 1.0]                       # EffectiveInitialCapital = 50% do deposito


def test_percentage_lot_compounds_with_live_balance(spec):
    mb, ents = script(["tp", "tp", "tp"])
    res, p = go(mb, ents, spec, kw=dict(deposit=10_000.0), PositionSizeMode=0, PositionSizeValue=5)
    t = res.trades
    assert len(t) == 3
    for i, row in t.iterrows():
        bal = 10_000.0 + t.net.iloc[:i].sum()                      # saldo AO VIVO antes desta entrada
        risk_per_lot = abs(row.open_price - row.sl) / 1e-5 * 1.0
        ideal = 0.05 * bal / risk_per_lot
        assert row.volume == pytest.approx(int(ideal / 0.01 + 1e-9) * 0.01, abs=1e-9)
    assert res.ledger.balance == pytest.approx(10_000.0 + t.net.sum())


def test_commission_is_charged_on_entry_and_exit(spec):
    from dataclasses import replace
    mb, ents = script(["tp"])
    res, _ = go(mb, ents, replace(spec, commission_per_lot_side=3.5), PositionSizeMode=2, PositionSizeValue=0.10)
    t = res.trades.iloc[0]
    assert t.commission == pytest.approx(-2 * 3.5 * 0.10) and t.net == pytest.approx(t.gross - 0.70)
    assert res.ledger.balance == pytest.approx(10_000.0 + t.net)


def test_fixed_lot_martingale_doubles_after_loss_and_resets_after_win(spec):
    mb, ents = script(["sl", "sl", "tp", "sl"])
    res, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.02, RecoveryMode=1, Multiplicador=2)
    assert list(res.trades.volume) == [0.02, 0.04, 0.08, 0.02]         # 3a entrada ganha -> 4a volta ao lote base


def test_martingale_caps_and_hard_reset_after_max_steps(spec):
    mb, ents = script(["sl"] * 5)
    res, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.02, RecoveryMode=1, Multiplicador=2,
                MaxMartingaleLot=0.06)
    assert list(res.trades.volume) == [0.02, 0.04, 0.06, 0.06, 0.06]   # teto absoluto
    res2, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.02, RecoveryMode=1, Multiplicador=2,
                 MaxMartingaleSteps=2)
    # 3 perdas seguidas > 2 passos: a divida antiga e descartada e a proxima ordem volta ao lote base
    assert list(res2.trades.volume) == [0.02, 0.04, 0.08, 0.02, 0.04]


def test_dalembert_steps_up_on_loss_down_on_win_with_cap(spec):
    mb, ents = script(["sl", "sl", "tp", "tp", "tp", "sl"])
    res, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.02, RecoveryMode=2, DAlembertStep=0.01)
    assert [round(x, 2) for x in res.trades.volume] == [0.02, 0.03, 0.04, 0.03, 0.02, 0.02]
    res2, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.02, RecoveryMode=2, DAlembertStep=0.01,
                 MaxMartingaleLot=0.03)
    assert max(res2.trades.volume) == 0.03


def test_monetary_martingale_with_take_targets_recovery_of_the_debt(spec):
    mb, ents = script(["sl", "sl"])
    res, p = go(mb, ents, spec, PositionSizeMode=1, PositionSizeValue=10000, RecoveryMode=1, Multiplicador=1)
    t = res.trades
    debt = -t.net.iloc[0]
    assert debt > 0 and t.volume.iloc[0] == 1.0
    # sem ser o lote base: precisa de lote tal que o TP (ATR[VelaTake]*Take, em ticks x tick_value) pague a divida
    assert t.volume.iloc[1] >= 1.0


def test_recovery_ledger_outstanding_matches_trades(spec):
    mb, ents = script(["sl", "sl", "tp"])
    res, _ = go(mb, ents, spec, PositionSizeMode=2, PositionSizeValue=0.02, RecoveryMode=1, Multiplicador=1)
    r = res.ledger.rec[1]
    t = res.trades
    losses = -t.net.iloc[:2].sum()
    win = t.net.iloc[2]
    assert r.outstanding == pytest.approx(max(0.0, losses - win), abs=1e-9)
