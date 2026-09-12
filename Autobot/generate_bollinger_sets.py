# -*- coding: utf-8 -*-
"""Gera a biblioteca de sets de otimizacao da variante BOLLINGER BANDS.

Espelha generate_system_sets.py (mesmos 11 sistemas, mesma filosofia de
fases), mas para a EA "White Rabbit X (Global -  Bolinger Bands).mq5" --
schema de inputs totalmente diferente (sem EntryIndicator/Fast_EMA como eixo
de entrada; em vez disso BandsPeriod/BandsDeviation/BandsShift, mais 3 saidas
novas: BreakevenBolinger/TakeBolinger/StopBolinger).

ADITIVO DE PROPOSITO (achado do dono, 2026-09-06): generate_system_sets.py
APAGA (shutil.rmtree) e reconstroi White_Rabbit_X_Sets_templates inteiro a
cada rodada -- rodar de novo destruiria as travas manuais (Y->N) que ja
existem nos sets MULTI/ICHIMOKU (pelo menos 15 arquivos editados a mao depois
da ultima geracao, confirmado por timestamp). Este script NUNCA apaga nada:
so escreve arquivos novos terminados em "_BOLLINGER.set", ao lado dos que ja
existem, e um manifesto proprio (nao mexe no MANIFESTO_SISTEMAS.csv).

Reaproveita de generate_system_sets.py tudo que e independente do indicador
de entrada (sistemas, sizing/formula, exposicao, classes de ativo, Profile) --
so a secao de ENTRADA e os FILTROS (que citam Stochastic/Ichimoku, que nao
existem na EA Bollinger) sao reescritos aqui.

Uso:
    python generate_bollinger_sets.py
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import wrx_paths
import generate_system_sets as base
from generate_system_sets import (
    ASSETS, CLASSES, SYSTEMS, BILATERAL,
    Profile, AssetClass,
    apply_defaults, apply_system, apply_sizing_and_formula,
)

TERMINAL = wrx_paths.data_dir() / "MQL5"
EA_SOURCE = TERMINAL / "Experts" / "White Rabbit X (Global -  Bolinger Bands).mq5"
OUTPUT = TERMINAL / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"

# Namespace de magic number DISJUNTO do usado por MULTI/ICHIMOKU
# (610.000.000-699.999.999, ver generate_system_sets.py) -- uma conta pode
# rodar as duas variantes ao mesmo tempo sem as posicoes se confundirem.
MAGIC_BASE = 700_000_000
MAGIC_SPAN = 89_999_999   # 700.000.000-789.999.999


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

# Gates extras, so relevantes pra Bollinger: Fast_EMA/Slow_EMA/MACD_SMA agora
# alimentam SOMENTE o MACD interno do filtro MTF (a EA Bollinger nao tem mais
# indicador de entrada plugavel) -- sem isto, desativar_inertes() (herdado de
# generate_system_sets.py) nao sabe que esses 3 eixos ficam inertes quando o
# filtro MTF esta desligado, e a fase 1 desperdicaria busca num eixo morto.
base.GATES_DEPENDENCIAS.setdefault("Fast_EMA", "AtivarFiltroMTF")
base.GATES_DEPENDENCIAS.setdefault("Slow_EMA", "AtivarFiltroMTF")
base.GATES_DEPENDENCIAS.setdefault("MACD_SMA", "AtivarFiltroMTF")


def apply_core_bollinger(p: Profile, ac: AssetClass, grid: bool = False) -> None:
    """Entrada + filtros da variante Bollinger Bands.

    Espelha apply_core() de generate_system_sets.py: mesma filosofia de fase 1
    (tudo aberto), mesmas faixas nos filtros que nao dependem do indicador de
    entrada (MTF/MA/ADX/ATR-volatilidade/noticias). So a secao de ENTRADA
    muda -- Bollinger nao tem Stochastic nem Ichimoku, tem periodo/desvio/
    deslocamento das bandas, e ganha as 3 saidas alternativas por banda.
    """
    # Faixa classica de Bollinger: periodo 10-40 (20 e o padrao de mercado),
    # desvio 1.0-3.5 (2.0 e o padrao), shift quase sempre 0 -- aberto pra o
    # genetico confirmar isso em vez de assumir.
    p.opt("BandsPeriod", 20, 10, 2, 40)
    p.opt("BandsDeviation", 2.0, 1.0, 0.25, 3.5)
    p.opt("BandsShift", 0, 0, 1, 2)
    p.opt("InpAppliedPrice", 1, 1, 1, 7)

    # As tres leituras canonicas de John Bollinger (achado do dono,
    # 2026-09-06, substituiu o esquema de 7 combinacoes herdado do Multi):
    # 0=Reversal, 1=Breakout, 2=Squeeze.
    p.opt("BollingerEntryMode", 1, 0, 1, 2)
    # So tem efeito no ramo Squeeze (BollingerEntryMode==2) -- GATES_
    # DEPENDENCIAS so sabe desativar por FLAG BOOLEANA false, nao por um
    # valor especifico de enum, entao os dois ficam abertos nos tres ramos
    # mesmo (mesma imprecisao ja aceita hoje pra ICHIMOKU: sem coluna
    # EntryIndicator, eixos_do_indicador() em optimize_two_stage.py tambem
    # reabre tudo sem filtrar na Fase 2 -- ver docstring da funcao).
    p.opt("SqueezeLookback", 20, 10, 5, 40)
    p.opt("SqueezeTolerancePct", 10.0, 5.0, 2.5, 20.0)
    p.opt("TimeFrame", ac.timeframe, ac.tf_lo, 1, ac.tf_hi)

    p.opt("ATR_TimeFrame", ac.timeframe, max(0, ac.tf_lo - 1), 1, ac.tf_hi)
    p.opt("PeriodoATR", 14, 7, 7, 28)

    # MTF Alignment: MACD interno, independente do indicador de entrada desde
    # a reescrita pra Bollinger -- mesmas faixas que o Multi usa (fast<slow
    # sempre vale, exigencia do OnInit).
    p.opt_bool("AtivarFiltroMTF")
    p.opt_bool("MTF_RequererAmbos", "false")
    p.opt("Fast_EMA", 12, 6, 3, 18)
    p.opt("Slow_EMA", 27, 21, 6, 45)
    p.opt("MACD_SMA", 9, 3, 3, 15)

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

    # Presente na EA (herdado do Multi-Indicator, guard anti-oversizing do
    # Fixed-R -- ZeusRisk.mqh) mas ausente de apply_defaults() em
    # generate_system_sets.py: input adicionado 2026-08-29/30, depois da
    # ultima regeneracao registrada da biblioteca MULTI/ICHIMOKU (manifesto de
    # 2026-08-24) -- a MESMA lacuna existe la, so nao foi notada porque
    # ninguem rodou main() de novo desde entao. Mesmo default da EA (1.5).
    p.fix("MaxRiscoRelativoAoLoteMinimo", 1.5)

    # Saidas alternativas por Bollinger (novas nesta variante): abertas desde
    # a fase 1, mesmo tratamento que os demais eixos booleanos de descoberta.
    p.opt_bool("BreakevenBolinger")
    p.opt_bool("TakeBolinger")
    p.opt_bool("StopBolinger")

    if grid:
        p.opt_bool("EntradaATR")
        p.opt("VolatilityFilter", 1, 0, 1, 1)
        # PeriodoBaselineATR/MultiplicadorATR (dono, 2026-09-12): mesmos
        # eixos novos do generate_system_sets.py, mesma regra de onde
        # entram (so grid) -- ver comentario la pro porque da troca de
        # filtro de volatilidade.
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
    variant = "BOLLINGER"

    for class_code, assets in ASSETS.items():
        ac = CLASSES[class_code]
        for asset in assets:
            for system in SYSTEMS:
                # ADITIVO, nao substitutivo -- espelha generate_system_sets.py
                # (mesma mudanca, "Modo Economico", 2026-09-07): todo sistema
                # em BILATERAL ganha "BOTH" JUNTO com BUY/SELL separados,
                # nunca no lugar deles. Achado ao auditar a biblioteca depois
                # da regeneracao (dono, 2026-09-07): esta linha ainda tinha a
                # semantica antiga (BOTH SUBSTITUI, de quando BILATERAL era
                # so um sistema removido) -- com BILATERAL agora cobrindo os
                # 11 sistemas, gerava SO BOTH pra tudo, zero BUY_BOLLINGER/
                # SELL_BOLLINGER na biblioteca inteira.
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
                    # Bollinger tem rotulos proprios (ex.: myBlankSpace
                    # BollingerExit) que nao existem la -- completa aqui.
                    for blank in BLANKS:
                        if blank not in p.values:
                            p.raw(blank, "")
                    apply_core_bollinger(
                        p, ac,
                        grid=system.code in ("07_GRID_SEPARATE",
                                             "12_GRID_INVERSO"))
                    apply_system(p, system.code, ac, side)
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
                        "; White Rabbit X - set de otimizacao por sistema (Bollinger Bands)",
                        f"; Sistema={system.code} ({system.label})",
                        f"; Ativo={asset} | Classe={class_code} | Lado={side}",
                        "; Indicador=Bollinger Bands (reversao/rompimento/cruzamento de referencia)",
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

    manifest_path = OUTPUT / "MANIFESTO_SISTEMAS_BOLLINGER.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(manifest)

    print(f"Sets Bollinger gerados: {len(manifest)}")
    print(f"Ativos: {sum(len(v) for v in ASSETS.values())} | "
          f"Sistemas: {len(SYSTEMS)} | Variante: BOLLINGER | "
          f"Lados: 2, menos {len(BILATERAL)} bilateral(is) com arquivo unico")
    print(f"Maior espaco de busca: {total_passes_max:,}".replace(",", "."))
    print(f"Saida (aditiva, nada existente foi apagado): {OUTPUT}")
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
