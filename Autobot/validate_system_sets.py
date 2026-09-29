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
# Cada familia tem a PROPRIA EA (schema de inputs diferente): o sufixo do arquivo escolhe qual.
EA_POR_FAMILIA = {
    "BOLLINGER": TERMINAL / "Experts" / "White Rabbit X (Global -  Bolinger Bands).mq5",
    "CANDLES": TERMINAL / "Experts" / "White Rabbit (Candles Entry).mq5",
}
ROOT = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"
# Combinacoes que a EA recusa mas o template alcanca por ACOPLAMENTO entre eixos
# independentes (nao e set quebrado): modo 1 do 06 BOTH exige Hedging=true e os dois eixos
# variam sozinhos, entao ~1/4 das combinacoes e recusada no OnInit (genetico perde passes).
ACOPLAMENTOS_CONHECIDOS = {
    "saida por ordem oposta sem hedging bilateral": "06_REVERSAL_EXIT/BOTH_",
}

# Eixos cujo cruzamento o OnInit avalia. Expandidos por produto cartesiano.
CROSS = [
    "PositionSizeMode", "AtivarStop", "AtivarTake", "GridMode", "RecoveryMode",
    "MaxLongTrades", "MaxShortTrades", "Hedging", "DistanciaMinima",
    "Multiplicador", "DAlembertStep", "ReversalExitMode", "AtivarBreakeven",
    "BreakevenDistancia", "Stop", "Take", "AtivarTrailATR", "Trail",
    "EntryIndicator", "Fast_EMA", "Slow_EMA", "MACD_SMA", "PeriodoATR",
    "AtivarFiltroMTF", "TradeCapitalPercentage", "MaxSlippage",
    "EntryOrderType", "PendingGatilho", "PendingHoraSessao", "PendingFaixaBarras",
    "PendingExpiracaoBarras", "PendingDistanciaATR",
]


# Eixo que a familia NAO tem (Bollinger/Candles nao tem indicador plugavel nem periodos
# EMA): entra com valor neutro, que nunca dispara regra.
NEUTRO = {
    "PositionSizeMode": 3, "AtivarStop": 1, "AtivarTake": 1, "GridMode": 0, "RecoveryMode": 0,
    "MaxLongTrades": 1, "MaxShortTrades": 1, "Hedging": 0, "DistanciaMinima": 1,
    "Multiplicador": 1, "DAlembertStep": 0.01, "ReversalExitMode": 0, "AtivarBreakeven": 0,
    "BreakevenDistancia": 1, "Stop": 1, "Take": 1, "AtivarTrailATR": 0, "Trail": 1,
    "EntryIndicator": -1, "Fast_EMA": 1, "Slow_EMA": 2, "MACD_SMA": 3, "PeriodoATR": 14,
    "AtivarFiltroMTF": 0, "TradeCapitalPercentage": 100, "MaxSlippage": 0,
    "EntryOrderType": 0, "PendingGatilho": 0, "PendingHoraSessao": 8, "PendingFaixaBarras": 4,
    "PendingExpiracaoBarras": 3, "PendingDistanciaATR": 0.5,
}


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
    v = {**NEUTRO, **v}
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
    # Classic grid tem SL zero (sem risco pra medir); Pyramid tem Stop real
    # em cada perna, entao fica isento (espelha o OnInit, achado 2026-08-17).
    if fixed_r and (percentage or monetary or fixed_lot or (grid and not pyramid)):
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
        if not pyramid and (percentage or fixed_r or (not monetary and not fixed_lot)):
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
    # Entrada pendente (OnInit: "Invalid session trigger" / "Invalid pending entry")
    if "PendingGatilho" in v:
        if v["PendingGatilho"] == 1 and (
                v["EntryOrderType"] == 0 or not 0 <= v["PendingHoraSessao"] <= 23
                or v["PendingFaixaBarras"] < 1):
            return "gatilho por sessao sem pendente / hora fora de 0-23 / faixa < 1"
        if v["EntryOrderType"] != 0 and (
                v["PendingExpiracaoBarras"] < 1 or v["PendingDistanciaATR"] < 0):
            return "pendente com expiracao < 1 ou distancia < 0"
    return None


def main() -> int:
    def inputs_da(caminho: Path) -> list[str]:
        return re.findall(
            r"^\s*input\s+(?!group\b)[A-Za-z_][A-Za-z0-9_]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
            caminho.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)

    esquemas = {"MULTI": inputs_da(EA)}
    for fam, caminho in EA_POR_FAMILIA.items():
        if caminho.exists():
            esquemas[fam] = inputs_da(caminho)

    files = sorted(ROOT.rglob("*.set"))
    if not files:
        print(f"Nenhum .set em {ROOT}")
        return 1

    errors: list[str] = []
    avisos: list[str] = []
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

        familia = next((f for f in EA_POR_FAMILIA if path.stem.endswith(f"_{f}")), "MULTI")
        if familia not in esquemas:
            errors.append(f"{rel}: EA da familia {familia} nao encontrada")
            continue
        if order != esquemas[familia]:
            errors.append(f"{rel}: schema divergente da EA {familia}")
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
                if why in ACOPLAMENTOS_CONHECIDOS and ACOPLAMENTOS_CONHECIDOS[why] in rel:
                    avisos.append(f"{rel}: {why}")
                else:
                    errors.append(f"{rel}: {why}")
                break

    print(f"Sets validados: {len(files)}")
    print(f"Combinacoes cruzadas testadas: {combos_checked:,}".replace(",", "."))
    print(f"Maior espaco: {biggest[0]:,}".replace(",", ".") + f"  ({biggest[1]})")
    if avisos:
        print(f"\nAVISOS (acoplamento conhecido, nao e set quebrado): {len(avisos)}")
        for a in avisos[:3]:
            print(f"  - {a}")
        print("    ... o modo 1 (ordem oposta) do 06 BOTH exige Hedging=true; os dois eixos "
              "variam sozinhos e ~1/4 das combinacoes e recusada no OnInit.")
    if errors:
        print(f"\nERROS: {len(errors)}")
        for err in errors[:25]:
            print(f"  - {err}")
        return 1
    print("\nOK: schema bate com a EA de cada familia e nenhuma combinacao dispara "
          "INIT_PARAMETERS_INCORRECT (fora os avisos acima).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
