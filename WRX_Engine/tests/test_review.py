from pathlib import Path

import pytest

from conftest import base_path, build_ticks
from wrx_engine import registry as R
from wrx_engine import review as V
from wrx_engine.setfile import params_from_dict, parse_set_text, read_set_text, unsupported

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "Sets" / "01_Forex" / "EURUSD" / "01_SLTP" / "BUY_MULTI.set"


def test_probe_inputs_are_all_known_and_ported_or_partial():
    for pr in V.PROBES:
        for i in pr.inputs:
            assert R.lookup(i).status in (R.PORTED, R.PARTIAL), (pr.id, i)


def test_every_ported_input_has_at_least_one_probe():
    by = V.probes_by_input()
    orphan = [n for n, i in R.REGISTRY.items() if i.status == R.PORTED and n not in by]
    # sem sonda dedicada (cobertos indiretamente pelo baseline ou por sondas de outros inputs):
    assert len(orphan) <= 45, orphan


@pytest.mark.skipif(not SAMPLE.exists(), reason="set de exemplo ausente")
def test_all_probes_generate_load_strict_and_run(tmp_path, spec):
    paths = V.make_probes(SAMPLE, tmp_path)
    assert len(paths) == len(V.PROBES) >= 50
    assert (tmp_path / "P00_base.set").read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff")       # UTF-16 com BOM
    from wrx_engine.engine import run_backtest
    from wrx_engine.setfile import load_set
    ticks = build_ticks(base_path(1800, seed=21, step=0.0002))
    ran = 0
    for pr, p in zip(V.PROBES, paths):
        params = load_set(p)                         # strict: se o motor recusar, quebra aqui
        run_backtest(params, spec, ticks)
        ran += 1
    assert ran == len(V.PROBES)


@pytest.mark.skipif(not SAMPLE.exists(), reason="set de exemplo ausente")
def test_probe_changes_only_what_it_claims(tmp_path):
    base = parse_set_text(read_set_text(SAMPLE))
    p0 = V.merged(base, V.PROBES[0])
    p3 = V.merged(base, next(p for p in V.PROBES if p.id == "P03_breakeven"))
    diff = {k for k in p0 if p0[k] != p3.get(k)}
    assert diff == {"AtivarBreakeven", "BreakevenDistancia"}


def test_checklist_and_sync_report(tmp_path):
    md = V.checklist_markdown()
    assert "`EntryIndicator`" in md and "DEFERRED" in md and "SEM SONDA" not in md.split("PORTED")[0]
    md2 = V.checklist_markdown({"P03_breakeven": "PASS", "P00_base": "FAIL"})
    assert "FAIL" in md2 and "PASS" in md2
    ea = tmp_path / "x.mq5"
    ea.write_text('input group "G"\ninput int Fast_EMA = 12; // c\ninput ENUM_TIMEFRAMES  NovoInput = 5;\n'
                  'input string myBlankSpace1 = ""; //||=||\n', encoding="utf-8")
    assert V.ea_inputs(ea) == ["Fast_EMA", "NovoInput", "myBlankSpace1"]
    rep = V.sync_report(ea)
    assert "NovoInput" in rep and "sem status" in rep
