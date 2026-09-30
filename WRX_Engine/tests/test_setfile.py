from pathlib import Path

import pytest

from wrx_engine.setfile import UnsupportedConfig, load_set, params_from_text, parse_set_text, unsupported

REAL = (Path(__file__).resolve().parents[2] / "Sets" / "01_Forex" / "EURUSD" / "01_SLTP" / "BUY_MULTI.set")


def test_current_value_is_the_token_before_the_first_pipe():
    d = parse_set_text("; comentario\nStop=3.5||1||0.5||6||Y\nTimeFrame=2||1||1||5||Y\nNomedaEstrategia=WRX x\n")
    assert d == {"Stop": "3.5", "TimeFrame": "2", "NomedaEstrategia": "WRX x"}


def test_missing_inputs_take_the_ea_default_not_ours():
    base = "PositionSizeMode=3\nMaxEquityDrawdownPercent=0\nMinFreeMarginPercent=0"
    p = params_from_text(base)
    assert p.reversal_exit_mode == 2                       # default do EA: fecha no sinal contrario (agora portado)
    with pytest.raises(UnsupportedConfig, match="OnOppositeOrder"):
        params_from_text(base + "\nReversalExitMode=1")
    assert p.max_risco_rel_min == 1.5 and p.fast == 12 and p.slow == 26 and p.stop == 3.0


def test_guard_refuses_what_the_engine_does_not_port():
    with pytest.raises(UnsupportedConfig) as e:
        params_from_text("EntryOrderType=1\nPositionSizeMode=2\nGridMode=1\nAtivarTrailATR=true")
    txt = str(e.value)
    assert "entrada pendente" in txt and "FixedLot" in txt and "GridMode" in txt and "trailing" in txt


def test_ea_defaults_that_would_silently_change_results_are_flagged():
    # sem zerar, o EA usa MaxEquityDrawdownPercent=30 e MinFreeMarginPercent=50
    assert any("MaxEquityDrawdownPercent" in m for m in unsupported({"PositionSizeMode": "3"}))


@pytest.mark.skipif(not REAL.exists(), reason="set do repo ausente")
def test_shipped_01_sltp_set_needs_wfo_off():
    with pytest.raises(UnsupportedConfig) as e:
        load_set(REAL)
    assert "AtivarWFO" in str(e.value) and len(e.value.motivos) == 1     # so o WFO barra
    from wrx_engine.setfile import parse_set_text, read_set_text
    d = parse_set_text(read_set_text(REAL)) | {"AtivarWFO": "false"}
    assert unsupported(d) == []
