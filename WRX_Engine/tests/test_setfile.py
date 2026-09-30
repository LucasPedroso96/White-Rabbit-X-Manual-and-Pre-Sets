from pathlib import Path

import pytest

from wrx_engine.setfile import UnsupportedConfig, load_set, params_from_text, parse_set_text, unsupported

REAL = (Path(__file__).resolve().parents[2] / "Sets" / "01_Forex" / "EURUSD" / "01_SLTP" / "BUY_MULTI.set")


def test_current_value_is_the_token_before_the_first_pipe():
    d = parse_set_text("; comentario\nStop=3.5||1||0.5||6||Y\nTimeFrame=2||1||1||5||Y\nNomedaEstrategia=WRX x\n")
    assert d == {"Stop": "3.5", "TimeFrame": "2", "NomedaEstrategia": "WRX x"}


def test_missing_inputs_take_the_ea_default_not_ours():
    p = params_from_text("PositionSizeMode=3")
    assert p.reversal_exit_mode == 2                       # default do EA: fecha no sinal contrario
    assert p.max_risco_rel_min == 1.5 and p.fast == 12 and p.slow == 26 and p.stop == 3.0
    assert p.v["MaxEquityDrawdownPercent"] == 30.0 and p.v["MinFreeMarginPercent"] == 50.0   # defaults do .mq5
    assert p.v["Multiplicador"] == 1.0 and p.v["DistanciaMinima"] == 2.0 and p.v["WFO_CarenciaPercentil"] == 75


def test_oninit_validation_mirrors_the_ea():
    from wrx_engine.setfile import oninit_errors, params_from_dict
    def errs(**kw):
        d = {k: str(v) for k, v in kw.items()}
        return oninit_errors(params_from_dict(d).v)
    assert not errs(PositionSizeMode=3)
    assert any("Martingale" in e for e in errs(PositionSizeMode=2, RecoveryMode=1, MaxLongTrades=2))
    assert any("Percentage exige" in e for e in errs(PositionSizeMode=0, AtivarStop="false"))
    assert any("aposentado" in e for e in errs(GridMode=2))
    assert any("Grid classico" in e for e in errs(GridMode=1, PositionSizeMode=3, MaxLongTrades=0, MaxShortTrades=0))
    assert any("Com Grid" in e for e in errs(GridMode=1, PositionSizeMode=2, MaxLongTrades=1))
    assert any("Pirâmide exige trailing" in e for e in errs(GridMode=3, PositionSizeMode=2, MaxLongTrades=0, MaxShortTrades=3))
    assert any("Grid exige conta hedging" in e for e in oninit_errors(
        params_from_dict({"GridMode": "1", "PositionSizeMode": "2", "MaxLongTrades": "3", "MaxShortTrades": "0"}).v,
        hedging_account=False))
    assert any("D'Alembert" in e for e in errs(RecoveryMode=2, PositionSizeMode=1))
    assert any("Fast < Slow" in e for e in errs(Fast_EMA=30, Slow_EMA=26))
    assert any("Ichimoku" in e for e in errs(EntryIndicator=11, Fast_EMA=9, Slow_EMA=26, MACD_SMA=20))


def test_guard_only_flags_invalid_enums_now_that_wfo_is_ported():
    with pytest.raises(UnsupportedConfig):
        params_from_text("EntryIndicator=99")
    params_from_text("AtivarWFO=true\nMetodoDeEntradawfo=0")          # WFO 'In Sample' agora e portado


@pytest.mark.skipif(not REAL.exists(), reason="set do repo ausente")
def test_shipped_01_sltp_set_loads_with_wfo_on():
    p = load_set(REAL)                                     # WFO ligado ('In Sample') e suportado
    assert p.v["AtivarWFO"] is True and p.v["MetodoDeEntradawfo"] == 0
    from wrx_engine.setfile import oninit_errors
    assert oninit_errors(p.v) == []
