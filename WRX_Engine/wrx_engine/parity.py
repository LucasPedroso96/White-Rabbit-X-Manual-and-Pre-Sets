"""Paridade trade a trade: motor x relatorio do Strategy Tester.

Regra de adocao (a mesma do simulador do Zeus): o motor so substitui o Tester na peneira
depois que `compare()` der PASS contra rodadas reais em Every tick based on real ticks.
Antes disso ele e ferramenta de estudo e o Tester decide.

ATENCAO -- o parser de relatorio foi escrito a partir do layout conhecido do MT5 (tabela
"Deals": Time, Deal, Symbol, Type, Direction, Volume, Price, Order, Commission, Swap, Profit,
Balance, Comment) e testado so contra um HTML SINTETICO gerado neste repositorio. Ainda nao
foi conferido contra um .htm real do seu terminal: se o layout/idioma diferir, ele levanta
erro explicito em vez de adivinhar.

Uso:
  python -m wrx_engine.parity --report ReportTester.htm --set meu.set --spec eurusd.json \
      --ticks eurusd_ticks.csv [--warmup eurusd_m1.csv] [--stop-fill level|tick]
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_HEADERS = {
    "time": ("time", "hora", "data/hora"),
    "deal": ("deal", "negócio", "negocio"),
    "symbol": ("symbol", "símbolo", "simbolo"),
    "type": ("type", "tipo"),
    "direction": ("direction", "direção", "direcao"),
    "volume": ("volume",),
    "price": ("price", "preço", "preco"),
    "order": ("order", "ordem"),
    "commission": ("commission", "comissão", "comissao"),
    "swap": ("swap",),
    "profit": ("profit", "lucro"),
    "balance": ("balance", "saldo"),
    "comment": ("comment", "comentário", "comentario"),
}


def _num(text: str) -> float:
    t = re.sub(r"[\s ]", "", text).replace(",", ".") if text.count(",") == 1 and "." not in text \
        else re.sub(r"[\s ,]", "", text)
    return float(t) if t not in ("", "-") else 0.0


def _ts_ms(text: str) -> int:
    text = text.strip()
    for fmt in ("%Y.%m.%d %H:%M:%S.%f", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return int(datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"data/hora nao reconhecida: {text!r}")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    raise ValueError(f"nao consegui decodificar {path}")


def parse_deals_html(path: str | Path) -> pd.DataFrame:
    """Tabela de deals do relatorio do Tester -> DataFrame (sem a linha de saldo inicial)."""
    txt = _read_text(Path(path))
    rows = [[_html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
             for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", txt, flags=re.S | re.I)]
    header_idx, colmap = None, {}
    for i, r in enumerate(rows):
        low = [c.lower() for c in r]
        m = {}
        for key, names in _HEADERS.items():
            for pos, cell in enumerate(low):
                if cell in names:
                    m[key] = pos
                    break
        if {"time", "type", "direction", "volume", "price", "profit"} <= m.keys():
            header_idx, colmap = i, m
            break
    if header_idx is None:
        raise ValueError("tabela de Deals nao encontrada (cabecalho esperado: Time/Type/Direction/"
                         "Volume/Price/Profit -- ou equivalentes em portugues). Layout diferente? "
                         "Veja a nota no topo de parity.py.")
    out = []
    for r in rows[header_idx + 1:]:
        if len(r) <= max(colmap.values()):
            continue
        typ = r[colmap["type"]].lower()
        if typ not in ("buy", "sell", "compra", "venda"):
            continue          # balance/credito/linhas de total
        out.append({
            "time_ms": _ts_ms(r[colmap["time"]]),
            "type": "buy" if typ in ("buy", "compra") else "sell",
            "direction": r[colmap["direction"]].lower(),
            "volume": _num(r[colmap["volume"]]),
            "price": _num(r[colmap["price"]]),
            "commission": _num(r[colmap["commission"]]) if "commission" in colmap else 0.0,
            "swap": _num(r[colmap["swap"]]) if "swap" in colmap else 0.0,
            "profit": _num(r[colmap["profit"]]),
            "comment": r[colmap["comment"]] if "comment" in colmap and len(r) > colmap["comment"] else "",
        })
    return pd.DataFrame(out)


def deals_to_trades(deals: pd.DataFrame) -> pd.DataFrame:
    """Casa entrada->saida por FIFO dentro de cada lado (fechamentos totais, passo 1)."""
    longs, shorts, rows = [], [], []
    for d in deals.itertuples():
        if d.direction in ("in",):
            (longs if d.type == "buy" else shorts).append(d)
        elif d.direction in ("out", "in/out"):
            book = longs if d.type == "sell" else shorts        # venda fecha compra
            if not book:
                raise ValueError(f"saida sem entrada correspondente em {d.time_ms}")
            o = book.pop(0)
            if abs(o.volume - d.volume) > 1e-9:
                raise ValueError("fechamento parcial/volume divergente ainda nao suportado no harness")
            c = d.comment.lower()
            reason = "sl" if "sl" in c else "tp" if "tp" in c else "other"
            rows.append({"open_ms": o.time_ms, "close_ms": d.time_ms,
                         "side": "buy" if o.type == "buy" else "sell", "volume": d.volume,
                         "open_price": o.price, "close_price": d.price, "gross": d.profit,
                         "commission": o.commission + d.commission, "swap": d.swap, "reason": reason})
    return pd.DataFrame(rows)


@dataclass
class ParityReport:
    n_engine: int
    n_tester: int
    matched: int
    only_engine: list = field(default_factory=list)
    only_tester: list = field(default_factory=list)
    diffs: pd.DataFrame = field(default_factory=pd.DataFrame)
    tol: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        if self.n_engine != self.n_tester or self.matched != self.n_tester:
            return False
        return bool(self.diffs.empty or self.diffs["ok"].all())

    def text(self) -> str:
        L = [f"trades: motor={self.n_engine} tester={self.n_tester} casados={self.matched}",
             f"so no motor: {len(self.only_engine)} | so no tester: {len(self.only_tester)}"]
        if not self.diffs.empty:
            d = self.diffs
            for col in ("d_open_price", "d_close_price", "d_volume", "d_gross"):
                L.append(f"  {col:<14} mediana|.|={d[col].abs().median():.6g}  max|.|={d[col].abs().max():.6g}")
            L.append(f"  fora da tolerancia: {int((~d['ok']).sum())} de {len(d)}"
                     f"  | motivo de saida diferente: {int((~d['same_reason']).sum())}")
            bad = d[~d["ok"]]
            if not bad.empty:
                L.append("primeira divergencia:\n" + bad.iloc[[0]].T.to_string(header=False))
        L.append("VEREDITO: " + ("PASS" if self.passed else "FAIL"))
        return "\n".join(L)


def compare(engine_trades: pd.DataFrame, tester_trades: pd.DataFrame, *, time_tol_s: float = 2.0,
            price_tol: float = 1e-9, gross_tol: float = 0.011, tick_size: float | None = None) -> ParityReport:
    """Casa trades pelo horario de abertura (+-time_tol_s) e lado; mede erro em preco, lote e lucro bruto.

    price_tol default 0 (+ folga de float): paridade ESTRITA, como no Zeus. Para saber quanto
    falta, olhe as medianas/maximos do relatorio, nao so o veredito.
    """
    tol = {"time_tol_s": time_tol_s, "price_tol": price_tol, "gross_tol": gross_tol}
    e = engine_trades.reset_index(drop=True)
    t = tester_trades.reset_index(drop=True)
    used, rows, only_t = set(), [], []
    for j, tr in t.iterrows():
        cand = e[(e.side == tr.side) & ~e.index.isin(used)
                 & ((e.open_ms - tr.open_ms).abs() <= time_tol_s * 1000)]
        if cand.empty:
            only_t.append(int(tr.open_ms))
            continue
        i = (cand.open_ms - tr.open_ms).abs().idxmin()
        used.add(i)
        en = e.loc[i]
        d = {"open_ms": int(tr.open_ms), "side": tr.side,
             "d_open_price": en.open_price - tr.open_price, "d_close_price": en.close_price - tr.close_price,
             "d_volume": en.volume - tr.volume, "d_gross": en.gross - tr.gross,
             "d_close_s": (en.close_ms - tr.close_ms) / 1000.0,
             "same_reason": (en.reason == tr.reason) or tr.reason == "other"}
        d["ok"] = bool(abs(d["d_open_price"]) <= price_tol and abs(d["d_close_price"]) <= price_tol
                       and abs(d["d_volume"]) < 1e-9 and abs(d["d_gross"]) <= gross_tol and d["same_reason"])
        rows.append(d)
    only_e = [int(e.loc[i].open_ms) for i in e.index if i not in used]
    return ParityReport(len(e), len(t), len(rows), only_e, only_t, pd.DataFrame(rows), tol)


def _load_frame(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def main(argv=None) -> int:
    from .bars import Bars, Ticks
    from .engine import run_backtest
    from .setfile import load_set
    from .spec import SymbolSpec

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", required=True, help="relatorio .htm do Tester")
    ap.add_argument("--set", required=True, dest="setfile")
    ap.add_argument("--spec", required=True, help="json do SymbolSpec (tools/export_mt5_data.py)")
    ap.add_argument("--ticks", required=True, help="csv/parquet com time_msc,bid,ask")
    ap.add_argument("--warmup", help="csv/parquet M1 anterior ao teste: time,open,high,low,close")
    ap.add_argument("--stop-fill", default="level", choices=["level", "tick"])
    ap.add_argument("--json", help="grava o relatorio em json")
    a = ap.parse_args(argv)

    tester = deals_to_trades(parse_deals_html(a.report))
    warm = Bars.from_frame(_load_frame(a.warmup)) if a.warmup else None
    res = run_backtest(load_set(a.setfile), SymbolSpec.from_json(a.spec),
                       Ticks.from_frame(_load_frame(a.ticks)), warmup_m1=warm, stop_fill=a.stop_fill)
    rep = compare(res.trades, tester)
    print(rep.text())
    print("recusas do motor:", res.skipped)
    if a.json:
        Path(a.json).write_text(json.dumps({"passed": rep.passed, "engine": rep.n_engine, "tester": rep.n_tester,
                                            "matched": rep.matched, "tol": rep.tol}, indent=2))
    return 0 if rep.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
