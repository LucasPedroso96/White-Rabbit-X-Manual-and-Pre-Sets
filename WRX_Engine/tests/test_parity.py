"""O HTML aqui e SINTETICO (layout assumido do MT5) -- prova o parser/comparador, nao o formato real."""
from datetime import datetime, timezone

import pandas as pd
import pytest

from conftest import base_path, build_ticks, make_params
from wrx_engine.engine import run_backtest
from wrx_engine.parity import compare, deals_to_trades, parse_deals_html


def fmt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S")


def make_report(trades: pd.DataFrame, path, headers=("Time", "Deal", "Symbol", "Type", "Direction", "Volume",
                                                     "Price", "Order", "Commission", "Swap", "Profit", "Balance", "Comment")):
    rows = ["<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>",
            "<tr><td>2026.03.02 00:00:00</td><td>1</td><td></td><td>balance</td><td></td><td></td><td></td>"
            "<td></td><td></td><td></td><td>10 000.00</td><td>10 000.00</td><td></td></tr>"]
    n = 2
    for t in trades.itertuples():
        typ_in, typ_out = ("buy", "sell") if t.side == "buy" else ("sell", "buy")
        rows.append(f"<tr><td>{fmt(t.open_ms)}</td><td>{n}</td><td>EURUSD</td><td>{typ_in}</td><td>in</td>"
                    f"<td>{t.volume:.2f}</td><td>{t.open_price:.5f}</td><td>{n}</td><td>0.00</td><td>0.00</td>"
                    f"<td>0.00</td><td>10 000.00</td><td></td></tr>")
        rows.append(f"<tr><td>{fmt(t.close_ms)}</td><td>{n + 1}</td><td>EURUSD</td><td>{typ_out}</td><td>out</td>"
                    f"<td>{t.volume:.2f}</td><td>{t.close_price:.5f}</td><td>{n + 1}</td><td>0.00</td><td>0.00</td>"
                    f"<td>{t.gross:.2f}</td><td>10 000.00</td><td>{t.reason}</td></tr>")
        n += 2
    path.write_bytes(("<html><body><table>" + "".join(rows) + "</table></body></html>").encode("utf-16"))


@pytest.fixture
def engine_trades(spec):
    res = run_backtest(make_params(Stop=3.0, Take=3.0, MaxShortTrades=0), spec,
                       build_ticks(base_path(2500, seed=3, step=0.00012)))
    assert len(res.trades) > 5
    return res.trades


def test_roundtrip_report_is_pass(tmp_path, engine_trades):
    make_report(engine_trades, tmp_path / "r.htm")
    tester = deals_to_trades(parse_deals_html(tmp_path / "r.htm"))
    assert len(tester) == len(engine_trades)
    rep = compare(engine_trades, tester, gross_tol=0.011)
    assert rep.passed, rep.text()


def test_localized_headers_are_understood(tmp_path, engine_trades):
    pt = ("Hora", "Negócio", "Símbolo", "Tipo", "Direção", "Volume", "Preço", "Ordem", "Comissão", "Swap", "Lucro",
          "Saldo", "Comentário")
    make_report(engine_trades, tmp_path / "r.htm", headers=pt)
    assert len(deals_to_trades(parse_deals_html(tmp_path / "r.htm"))) == len(engine_trades)


def test_divergences_are_detected_and_localized(tmp_path, engine_trades):
    make_report(engine_trades, tmp_path / "r.htm")
    tester = deals_to_trades(parse_deals_html(tmp_path / "r.htm"))
    bad = tester.copy()
    bad.loc[3, "close_price"] += 0.00002       # 2 pontos de diferenca na saida do 4o trade
    bad = bad.drop(index=5)                    # o Tester nao abriu o 6o trade
    rep = compare(engine_trades, bad)
    assert not rep.passed and len(rep.only_engine) == 1 and rep.matched == len(bad)
    assert int((~rep.diffs["ok"]).sum()) == 1 and abs(rep.diffs["d_close_price"]).max() == pytest.approx(2e-5)
    assert "FAIL" in rep.text()


def test_unknown_layout_fails_loudly(tmp_path):
    (tmp_path / "x.htm").write_text("<table><tr><td>nada</td></tr></table>", encoding="utf-16")
    with pytest.raises(ValueError, match="tabela de Deals"):
        parse_deals_html(tmp_path / "x.htm")


def test_cli_end_to_end_exit_codes(tmp_path, spec):
    from wrx_engine.parity import main
    ticks = build_ticks(base_path(2500, seed=3, step=0.00012))
    pd.DataFrame({"time_msc": ticks.t_ms, "bid": ticks.bid, "ask": ticks.ask}).to_csv(tmp_path / "t.csv", index=False)
    spec.to_json(tmp_path / "spec.json")
    (tmp_path / "s.set").write_text("PositionSizeMode=3\nPositionSizeValue=1||1||1||1||N\nCapitalBaseR=500\nStop=3\nTake=3\n"
                                    "AtivarBreakeven=false\nMaxShortTrades=0\nReversalExitMode=0\nEntryMethod=6\n"
                                    "MaxEquityDrawdownPercent=0\nMinFreeMarginPercent=0\n", encoding="utf-16")
    eng = run_backtest(make_params(Stop=3.0, Take=3.0, MaxShortTrades=0), spec, ticks).trades
    make_report(eng, tmp_path / "ok.htm")
    args = ["--set", str(tmp_path / "s.set"), "--spec", str(tmp_path / "spec.json"), "--ticks", str(tmp_path / "t.csv")]
    assert main(["--report", str(tmp_path / "ok.htm"), *args, "--json", str(tmp_path / "o.json")]) == 0
    make_report(eng.iloc[:-2], tmp_path / "short.htm")
    assert main(["--report", str(tmp_path / "short.htm"), *args]) == 1
