from conftest import make_params
from wrx_engine.engine import normalize_risk_volume, normalize_trade_volume, size_fixed_r


def test_fixed_r_lot_floors_to_step(spec):
    p = make_params()
    # 1R = 1% de 500 = 5; SL 0.0020 = 200 ticks x 1 = 200/lote -> 0.025 -> 0.02
    assert size_fixed_r(0.0020, 5.0, p, spec) == 0.02


def test_exact_multiples_are_not_lost_to_float_error(spec):
    p = make_params()
    assert size_fixed_r(0.0050, 5.0, p, spec) == 0.01    # 5/(500) = 0.01 exatos
    assert normalize_risk_volume(0.07, spec, 1.5) == 0.07


def test_below_minimum_is_promoted_unless_it_overshoots_risk_guard(spec):
    p = make_params()
    # ideal 0.0025 -> minimo 0.01 estoura 4x o risco > 1.5 -> recusa
    assert size_fixed_r(0.0020, 0.5, p, spec) == 0.0
    # guarda desligada -> promove ao minimo
    p2 = make_params(MaxRiscoRelativoAoLoteMinimo=0)
    assert size_fixed_r(0.0020, 0.5, p2, spec) == 0.01
    # 1.4x o risco pedido -> promove
    assert size_fixed_r(0.0050, 3.5, p, spec) == 0.01


def test_max_risk_cap_and_max_volume(spec):
    p = make_params(MaxRiscoTradeR=0.5)
    assert size_fixed_r(0.0020, 5.0, p, spec) == 0.01    # orcamento 2.5 -> 0.0125 -> 0.01
    assert normalize_trade_volume(1000.0, spec) == 100.0
    assert normalize_trade_volume(0.004, spec) == 0.01
