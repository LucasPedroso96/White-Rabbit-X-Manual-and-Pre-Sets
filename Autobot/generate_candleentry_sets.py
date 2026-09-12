# -*- coding: utf-8 -*-
"""Gera a biblioteca de sets de otimizacao da variante CANDLES (Candle Entry).

Espelha generate_bollinger_sets.py (mesmos 11 sistemas, mesma filosofia de
fases, mesmo padrao aditivo), mas para a EA "White Rabbit (Candles Entry).mq5"
-- schema de inputs sem EntryIndicator/Fast_EMA/Stochastic/Ichimoku como eixo
de entrada; em vez disso 4 "slots" de vela (CandleTF1-4/CandleIndex1-4,
slots 1-2 obrigatorios, 3-4 opcionais via AtivarSlot3/AtivarSlot4) que
comparam o preco aplicado contra o open de cada slot pra definir direcao.

ADITIVO DE PROPOSITO, mesma razao de generate_bollinger_sets.py: NUNCA apaga
nada, so escreve arquivos novos terminados em "_CANDLES.set", ao lado dos que
ja existem (MULTI/ICHIMOKU/BOLLINGER), e um manifesto proprio (nao mexe no
MANIFESTO_SISTEMAS.csv nem no _BOLLINGER.csv).

Reaproveita de generate_system_sets.py tudo que e independente do indicador
de entrada (sistemas, sizing/formula, exposicao, classes de ativo, Profile) --
so a secao de ENTRADA (candle slots) e reescrita aqui; os filtros MTF/MA/ADX/
volatilidade-ATR/noticias sao IDENTICOS aos de apply_core() (mesmo schema de
inputs, copiados verbatim).

Uso:
    python generate_candleentry_sets.py
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import wrx_paths
import generate_system_sets as base
from generate_system_sets import (
    ASSETS, CLASSES, SYSTEMS, BILATERAL, SISTEMAS_RECUPERACAO_OPCIONAL,
    Profile, AssetClass,
    apply_defaults, apply_system, apply_sizing_and_formula,
)

TERMINAL = wrx_paths.data_dir() / "MQL5"
EA_SOURCE = TERMINAL / "Experts" / "White Rabbit (Candles Entry).mq5"
OUTPUT = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"

# Namespace de magic number DISJUNTO de MULTI/ICHIMOKU (610.000.000-699.999.999)
# e de BOLLINGER (700.000.000-789.999.999) -- as tres variantes podem rodar na
# mesma conta ao mesmo tempo sem as posicoes se confundirem.
MAGIC_BASE = 800_000_000
MAGIC_SPAN = 89_999_999   # 800.000.000-889.999.999


def magic_estavel(chave: str, usados: dict[int, str]) -> int:
    """Mesma logica de generate_system_sets.magic_estavel, base deslocada."""
    bruto = hashlib.blake2s(chave.encode("utf-8"), digest_size=8).digest()
    magic = MAGIC_BASE + int.from_bytes(bruto, "big") % MAGIC_SPAN
    while magic in usados and usados[magic] != chave:
        magic = MAGIC_BASE + (magic - MAGIC_BASE + 1) % MAGIC_SPAN
    usados[magic] = chave
    return magic


def load_schema(source: Path) -> tuple[list[str], list[str]]:
    """Copia de generate_system_sets.load_schema() apontando pra outra EA."""
    src = source.read_text(encoding="utf-8", errors="replace")
    order: list[str] = []
    structure: list[str] = []
    for line in src.splitlines():
        group = re.match(r'^\s*input\s+group\s+"([^"]*)"', line)
        if group:
            structure.append(f"; {group.group(1)}")
            continue
        found = re.match(
            r"^\s*input\s+(?!group\b)[A-Za-z_][A-Za-z0-9_]*\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if found:
            order.append(found.group(1))
            structure.append(found.group(1))
    if not order:
        raise SystemExit(f"Nenhum input encontrado em {source}.")
    return order, structure


SCHEMA, STRUCTURE = load_schema(EA_SOURCE)
BLANKS = [n for n in SCHEMA if n.startswith("myBlankSpace")]

# Gates extras, so relevantes pra Candles: os slots 3/4 so tem efeito com o
# respectivo AtivarSlot3/AtivarSlot4 ligado -- sem isto, desativar_inertes()
# (herdado de generate_system_sets.py) nao sabe que CandleTF3/CandleIndex3 e
# CandleTF4/CandleIndex4 ficam inertes quando o slot correspondente esta
# desligado, e a fase 1 desperdicaria busca em eixos mortos. Espelha
# GATES_DEPENDENCIAS/GATES do gerador/optimize_two_stage.py -- mexeu aqui,
# mexa la tambem (ver optimize_two_stage.py:GATES).
base.GATES_DEPENDENCIAS.setdefault("CandleTF3", "AtivarSlot3")
base.GATES_DEPENDENCIAS.setdefault("CandleIndex3", "AtivarSlot3")
base.GATES_DEPENDENCIAS.setdefault("CandleTF4", "AtivarSlot4")
base.GATES_DEPENDENCIAS.setdefault("CandleIndex4", "AtivarSlot4")


def apply_core_candles(p: Profile, ac: AssetClass, grid: bool = False) -> None:
    """Entrada + filtros da variante Candle Entry.

    Espelha apply_core() de generate_system_sets.py: mesma filosofia de fase 1
    (tudo aberto), mesmas faixas nos filtros que nao dependem do indicador de
    entrada (MTF/MA/ADX/ATR-volatilidade/noticias). So a secao de ENTRADA
    muda -- Candles nao tem MACD/Stochastic/Ichimoku, tem 4 "slots" de vela
    (timeframe + indice), os dois primeiros obrigatorios, os dois ultimos
    opcionais via AtivarSlot3/AtivarSlot4.
    """
    p.opt("InpAppliedPrice", 1, 1, 1, 7)

    # Slots 1-2: OBRIGATORIOS, sempre abertos desde a fase 1 (sem gate --
    # HasRawBuyIndicatorSignal() os exige incondicionalmente, ver .mq5).
    # Timeframe segue a mesma faixa por classe de ativo que TimeFrame usa no
    # Multi/Bollinger; indice de vela (quantas barras atras) fica numa faixa
    # modesta (1-5), mesmo espirito de VelaStop/VelaTake/TrailVela (todos em
    # NUMEROS, refinados na fase 2).
    p.opt("CandleTF1", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("CandleIndex1", 1, 1, 1, 5)
    p.opt("CandleTF2", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("CandleIndex2", 1, 1, 1, 5)

    # Slots 3-4: OPCIONAIS -- o proprio flag decide se entram na confluencia.
    # Abertos desde a fase 1 (mesmo "funil" dos filtros MA/ADX/MTF abaixo);
    # desativar_inertes() rebaixa os dependentes (CandleTF3/4, CandleIndex3/4)
    # pra N quando o flag correspondente morre em false nesta fase.
    p.opt_bool("AtivarSlot3")
    p.opt("CandleTF3", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("CandleIndex3", 1, 1, 1, 5)
    p.opt_bool("AtivarSlot4")
    p.opt("CandleTF4", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("CandleIndex4", 1, 1, 1, 5)

    p.opt("ATR_TimeFrame", ac.timeframe, max(0, ac.tf_lo - 1), 1, ac.tf_hi)
    p.opt("PeriodoATR", 14, 7, 7, 28)

    # Filtros: IDENTICOS a apply_core() (mesmo schema de inputs, MTF/MA/ADX
    # nao dependem de indicador de entrada nenhum).
    p.opt_bool("AtivarFiltroMTF")
    p.opt_bool("MTF_RequererAmbos", "false")
    p.opt_bool("AtivarFiltroMA")
    p.opt("MA_TimeFrame", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("MA_Period", 200, 100, 100, 300)
    p.opt("MA_Method", 1, 0, 1, 3)
    p.opt("MetodoMA", 2, 0, 1, 3)
    p.opt("SentidoMA", 0, 0, 1, 1)
    p.opt("MA_AppliedPrice", 1, 1, 1, 7)
    p.opt("MA_SlopeLookback", 3, 1, 1, 5)
    p.opt_bool("AtivarFiltroADX")
    p.opt("ADX_TimeFrame", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)
    p.opt("ADX_Period", 14, 7, 7, 28)
    p.opt("ADX_Limiar", 25, 15, 5, 30)
    p.opt("MetodoADX", 0, 0, 1, 1)
    p.fix("MaxRiscoRelativoAoLoteMinimo", 1.5)

    if grid:
        p.opt_bool("EntradaATR")
        p.opt("VolatilityFilter", 1, 0, 1, 1)
        p.opt("PeriodoBaselineATR", 100, 50, 25, 200)
        p.opt("MultiplicadorATR", 1.5, 1.2, 0.1, 2.5)
    else:
        p.fix("EntradaATR", "false")
        p.fix("VolatilityFilter", 1)
        p.fix("PeriodoBaselineATR", 100)
        p.fix("MultiplicadorATR", 1.5)

    p.fix("AtivarFiltroNoticias", "false")
    p.fix("NewsSomenteAltoImpacto", "false")
    p.fix("NewsMinutosAntes", 15)
    p.fix("NewsMinutosDepois", 15)
    p.raw("NewsMoedasManual", ac.news)
    p.raw("NewsCSVFile", "WhiteRabbit_News.csv")


def render(p: Profile, header: list[str]) -> str:
    lines = list(header)
    lines.append("; this file contains input parameters for testing/optimizing")
    lines.append("; to use it, click Load in the context menu of the Inputs tab")
    lines.append(";")
    for item in STRUCTURE:
        if item.startswith(";"):
            lines.append(item)
        else:
            lines.append(f"{item}={p.values[item]}")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    magics_usados: dict[int, str] = {}
    total_passes_max = 0
    variant = "CANDLES"

    for class_code, assets in ASSETS.items():
        ac = CLASSES[class_code]
        for asset in assets:
            for system in SYSTEMS:
                # ADITIVO, nao substitutivo -- mesma semantica de BILATERAL
                # que MULTI/BOLLINGER ja seguem (ver generate_system_sets.py).
                for side in (("BUY", "SELL", "BOTH") if system.code in BILATERAL
                             else ("BUY", "SELL")):
                    name = f"WRX {system.code} {asset} {side} {variant}"
                    magic = magic_estavel(
                        f"{class_code}/{asset}/{system.code}/"
                        f"{side}_{variant}", magics_usados)
                    p = Profile()
                    apply_defaults(p, ac, side, magic, name)
                    # apply_defaults() preenche os myBlankSpace* da EA MULTI
                    # (BLANKS importado de generate_system_sets); a EA
                    # Candles tem rotulos proprios (ex.: myBlankSpaceCandleSlots)
                    # que nao existem la -- completa aqui.
                    for blank in BLANKS:
                        if blank not in p.values:
                            p.raw(blank, "")
                    apply_core_candles(
                        p, ac,
                        grid=system.code in ("07_GRID_SEPARATE",
                                             "12_GRID_INVERSO"))
                    apply_system(p, system.code, ac, side)
                    if system.code in SISTEMAS_RECUPERACAO_OPCIONAL:
                        # Mesmo range que generate_system_sets.py:main() usa
                        # pros 7 sistemas boosteveis -- ver comentario la.
                        p.opt("MaxMartingaleSteps", 3, 2, 2, 8)
                        p.opt("DAlembertStep", 0.02, 0.01, 0.02, 0.09)
                    apply_sizing_and_formula(p, system.code, ac)
                    p.desativar_inertes()

                    missing = [n for n in SCHEMA if n not in p.values]
                    if missing:
                        raise SystemExit(f"{name}: sem valor -> {missing}")

                    passes = p.passes()
                    total_passes_max = max(total_passes_max, passes)
                    algorithm = ("COMPLETE_SEARCH" if passes <= 20_000
                                 else "FAST_GENETIC")
                    header = [
                        "; White Rabbit X - set de otimizacao por sistema (Candle Entry)",
                        f"; Sistema={system.code} ({system.label})",
                        f"; Ativo={asset} | Classe={class_code} | Lado={side}",
                        "; Indicador=Candle Entry (confluencia de 2-4 velas contra o open)",
                        f"; ParametrosOtimizados={len(p.flags())}",
                        f"; Combinacoes={passes:,}".replace(",", "."),
                        f"; Algoritmo={algorithm}",
                        f"; Status={system.status}",
                        f"; Nota={system.notes}",
                        "; Desligue (Y->N) o que ja tiver resolvido antes da proxima rodada.",
                    ]
                    content = render(p, header)
                    rel = (Path(class_code) / asset / system.code /
                           f"{side}_{variant}.set")
                    target = OUTPUT / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-16")

                    manifest.append({
                        "Class": class_code, "Symbol": asset,
                        "System": system.code, "Side": side,
                        "Variant": variant,
                        "OptimizedParams": len(p.flags()),
                        "Combinations": passes,
                        "Algorithm": algorithm,
                        "MagicNumber": magic,
                        "Status": system.status,
                        "Path": rel.as_posix(),
                        "SHA256": hashlib.sha256(
                            target.read_bytes()).hexdigest().upper(),
                    })

    manifest_path = OUTPUT / "MANIFESTO_SISTEMAS_CANDLES.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(manifest)

    print(f"Sets Candles gerados: {len(manifest)}")
    print(f"Ativos: {sum(len(v) for v in ASSETS.values())} | "
          f"Sistemas: {len(SYSTEMS)} | Variante: CANDLES | "
          f"Lados: 2, menos {len(BILATERAL)} bilateral(is) com arquivo unico")
    print(f"Maior espaco de busca: {total_passes_max:,}".replace(",", "."))
    print(f"Saida (aditiva, nada existente foi apagado): {OUTPUT}")
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
