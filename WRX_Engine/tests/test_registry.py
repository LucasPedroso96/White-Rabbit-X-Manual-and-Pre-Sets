import csv
from pathlib import Path

import pytest

from wrx_engine import registry as R
from wrx_engine.setfile import _DEFAULTS, parse_set_text, read_set_text

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "Manuals" / "01_English" / "06_Input_Reference.csv"
SETS = ROOT / "Sets"


@pytest.mark.skipif(not CSV.exists(), reason="CSV publico de inputs ausente")
def test_every_public_input_is_classified():
    names = [r[3] for r in csv.reader(CSV.open(encoding="utf-8-sig"), delimiter=";")][1:]
    assert len(names) > 100
    missing = [n for n in names if R.lookup(n).status == "UNKNOWN"]
    assert not missing, f"inputs sem status no registro: {missing}"


@pytest.mark.skipif(not SETS.exists(), reason="Sets ausentes")
def test_every_key_in_shipped_sets_is_classified():
    seen = set()
    for f in list(SETS.glob("01_Forex/EURUSD/*/*.set"))[:12] + list(SETS.glob("02_Metals/*/12_*/*.set"))[:4]:
        seen |= set(parse_set_text(read_set_text(f)))
    assert len(seen) > 100
    missing = sorted(n for n in seen if R.lookup(n).status == "UNKNOWN")
    assert not missing, f"chaves de .set sem status: {missing}"


def test_engine_defaults_only_cover_classified_inputs_and_ported_ones_are_not_refused():
    for k in _DEFAULTS:
        assert R.lookup(k).status != "UNKNOWN", k
    for k, info in R.REGISTRY.items():
        assert info.status in (R.PORTED, R.PARTIAL, R.DEFERRED, R.UI, R.INERT), k
