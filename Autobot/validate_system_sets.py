# -*- coding: utf-8 -*-
"""Valida a biblioteca de sets por sistema contra o OnInit do White Rabbit X.

Diferente de uma checagem de sintaxe, este validador expande os eixos Y e
verifica que NENHUMA combinacao alcancavel dispara INIT_PARAMETERS_INCORRECT.
Ele reimplementa as regras do OnInit; quando o EA mudar, este arquivo muda.
"""
from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

import wrx_paths

TERMINAL = wrx_paths.data_dir() / "MQL5"
EA = TERMINAL / "Experts" / "White Rabbit X (Global Multi-Indicator).mq5"
ROOT = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"

# Eixos cujo cruzamento o OnInit avalia. Expandidos por produto cartesiano.
CROSS = [
    "PositionSizeMode", "AtivarStop", "AtivarTake", "GridMode", "RecoveryMode",
    "MaxLongTrades", "MaxShortTrades", "Hedging", "DistanciaMinima",
    "Multiplicador", "DAlembertStep", "ReversalExitMode", "AtivarBreakeven",
    "BreakevenDistancia", "Stop", "Take", "AtivarTrailATR", "Trail",
    "EntryIndicator", "Fast_EMA", "Slow_EMA", "MACD_SMA", "PeriodoATR",
    "AtivarFiltroMTF", "TradeCapitalPercentage", "MaxSlippage",
]


def parse(value: str):
    """Retorna (lista_de_valores, e_eixo) para uma tupla do .set."""
    parts = value.split("||")
    if len(parts) != 5:
        return None, False
    cur, start, step, stop, flag = parts
    if flag != "Y":
        return [num(cur)], False
    if start in ("true", "false"):
        return ([0.0, 1.0] if start != stop else [num(start)]), True
    a, s, b = float(start), float(step), float(stop)
    out, v = [], a
    while v <= b + 1e-9:
        out.append(round(v, 10))
        v += s
    return out, True


def num(token: str) -> float:
    if token == "true":
        return 1.0
    if token == "false":
        return 0.0
    return float(token)


def check(v: dict[str, float]) -> str | None:
    """Reimplementa as rejeicoes do OnInit. Retorna a causa ou None."""
    percentage = v["PositionSizeMode"] == 0
    monetary = v["PositionSizeMode"] == 1
    fixed_lot = v["PositionSizeMode"] == 2
    fixed_r = v["PositionSizeMode"] == 3
    grid = v["GridMode"] != 0
    pyramid = v["GridMode"] == 3  # Grid_Pyramid: sai por trail, nao TP
    martingale = v["RecoveryMode"] == 1
    dalembert = v["RecoveryMode"] == 2
    sl, tp = v["AtivarStop"] == 1, v["AtivarTake"] == 1

    if v["TradeCapitalPercentage"] <= 0 or v["TradeCapitalPercentage"] > 100:
        return "TradeCapitalPercentage fora de (0,100]"
    if sl and v["Stop"] <= 0:
        return "AtivarStop com Stop <= 0"
    if tp and v["Take"] <= 0:
        return "AtivarTake com Take <= 0"
    if v["AtivarTrailATR"] == 1 and v["Trail"] <= 0:
        return "trailing com Trail <= 0"
    if v["AtivarBreakeven"] == 1 and v["BreakevenDistancia"] <= 0:
        return "breakeven com distancia <= 0"
    if v["PeriodoATR"] <= 0:
        return "PeriodoATR <= 0"
    if v["MaxSlippage"] < 0 or v["MaxLongTrades"] < 0 or v["MaxShortTrades"] < 0:
        return "limites negativos"

    # Periodos do indicador: fast<slow quando o indicador usa os dois, ou
    # quando o filtro MTF esta ligado (o EA exige a ordem nesse caso tambem).
    # ENUM_ENTRY_INDICATOR: 0 MACD, 1 EMA, 2 Momentum, 3 Stochastic, 4 TRIX,
    # 5 RSI, 6 CCI, 7 WPR, 8 DeMarker, 9 MFI, 10 OsMA, 11 Ichimoku.
    # Fast/slow so importa para MACD, EMA, OsMA e Ichimoku.
    uses_fast_slow = v["EntryIndicator"] in (0.0, 1.0, 10.0, 11.0)
    if (uses_fast_slow or v["AtivarFiltroMTF"] == 1) and \
            (v["Slow_EMA"] <= 0 or v["Fast_EMA"] >= v["Slow_EMA"]):
        return (f"fast>=slow (ind={v['EntryIndicator']:.0f} "
                f"fast={v['Fast_EMA']:.0f} slow={v['Slow_EMA']:.0f})")
    if v["EntryIndicator"] == 11 and (
            v["Slow_EMA"] <= v["Fast_EMA"] or v["MACD_SMA"] <= v["Slow_EMA"]):
        return "Ichimoku sem Tenkan<Kijun<SenkouB"
    if v["Fast_EMA"] <= 0 or v["MACD_SMA"] <= 0:
        return "periodo <= 0"

    if percentage and not sl:
        return "Percentage sem Stop Loss"
    if fixed_r and not sl:
        return "Fixed-R sem Stop Loss"
    if fixed_r and (percentage or monetary or fixed_lot or grid):
        return "Fixed-R combinado com outro modo"
    if fixed_r and dalembert:
        return "Fixed-R com D'Alembert"
    if (martingale or grid) and v["Multiplicador"] <= 0:
        return "Multiplicador <= 0 com grid/martingale"
    if martingale and (v["MaxLongTrades"] > 1 or v["MaxShortTrades"] > 1):
        return "Martingale com mais de 1 posicao por lado"
    if dalembert and (not fixed_lot or grid or v["DAlembertStep"] <= 0):
        return "D'Alembert fora de Fixed Lot / grid ligado / passo <= 0"
    if grid:
        if percentage or fixed_r or (not monetary and not fixed_lot):
            return "Grid com sizing incompativel"
        if v["RecoveryMode"] != 0:
            return "Grid com recovery ligado"
        if v["DistanciaMinima"] <= 0:
            return "Grid sem distancia"
        # Pyramid ("grid inverso") sai por trailing na cesta, nao por TP --
        # o inverso do grid classico logo abaixo. Espelha o OnInit (.mq5).
        if pyramid:
            if v["AtivarTrailATR"] != 1:
                return "Grid Pyramid sem trailing ATR"
        elif not tp:
            return "Grid sem TP"
        if v["MaxLongTrades"] == 1 or v["MaxShortTrades"] == 1:
            return "Grid com lado == 1"
    if v["ReversalExitMode"] == 1 and (
            v["Hedging"] == 0 or v["MaxLongTrades"] == 0 or
            v["MaxShortTrades"] == 0 or grid):
        return "saida por ordem oposta sem hedging bilateral"
    return None


def main() -> int:
    ea_inputs = re.findall(
        r"^\s*input\s+(?!group\b)[A-Za-z_][A-Za-z0-9_]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
        EA.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)

    files = sorted(ROOT.rglob("*.set"))
    if not files:
        print(f"Nenhum .set em {ROOT}")
        return 1

    errors: list[str] = []
    combos_checked = 0
    biggest = (0, "")

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        order: list[str] = []
        axes: dict[str, list[float]] = {}
        flags = 0
        total = 1
        for line in path.read_text(encoding="utf-16").splitlines():
            if line.startswith(";") or not line:
                continue
            m = re.match(r"^([^;=]+)=(.*)$", line)
            if not m:
                errors.append(f"{rel}: linha invalida: {line[:50]}")
                continue
            name, raw = m.group(1), m.group(2)
            order.append(name)
            values, is_axis = parse(raw)
            if values is None:
                continue
            if is_axis:
                flags += 1
                total *= len(values)
                if len(values) < 2:
                    errors.append(f"{rel}: {name} marcado Y com 1 valor")
            if name in CROSS:
                axes[name] = values

        if order != ea_inputs:
            errors.append(f"{rel}: schema divergente do EA")
            continue
        if flags == 0:
            errors.append(f"{rel}: nenhum eixo Y")
        if total > biggest[0]:
            biggest = (total, rel)

        # As regras do OnInit sao todas comparacoes com zero, com 1, ou entre
        # periodos: uma violacao, se existe, aparece num extremo do eixo. Testar
        # {min, max} por eixo cobre isso sem estourar o produto cartesiano.
        names = list(axes)
        corners = [sorted({min(axes[n]), max(axes[n])}) for n in names]
        for combo in itertools.product(*corners):
            combos_checked += 1
            why = check(dict(zip(names, combo)))
            if why:
                errors.append(f"{rel}: {why}")
                break

    print(f"Sets validados: {len(files)}")
    print(f"Combinacoes cruzadas testadas: {combos_checked:,}".replace(",", "."))
    print(f"Maior espaco: {biggest[0]:,}".replace(",", ".") + f"  ({biggest[1]})")
    if errors:
        print(f"\nERROS: {len(errors)}")
        for err in errors[:25]:
            print(f"  - {err}")
        return 1
    print("\nOK: schema bate com o EA e nenhuma combinacao dispara "
          "INIT_PARAMETERS_INCORRECT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
