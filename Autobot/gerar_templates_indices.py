# -*- coding: utf-8 -*-
"""Gera templates .set SO para os 5 indices CFD novos, SEM tocar no resto.

generate_system_sets.main() faz shutil.rmtree(OUTPUT) e reconstroi a
biblioteca INTEIRA (todos os ativos, todos os sistemas) -- destrutivo demais
pra rodar so pra ADICIONAR 5 simbolos, ainda mais com campanhas ao vivo lendo
esses mesmos arquivos como `origem` (achar_set()) nos dois terminais.

Este script reusa a MESMA logica de apply_defaults/apply_core/apply_system/
apply_sizing_and_formula (import direto, zero duplicacao de regra) mas
escreve SO os combos dos indices novos, em `OUTPUT / classe / ativo / ...`,
sem tocar em nenhum arquivo de outro ativo. MANIFESTO_SISTEMAS.csv e o
README nao sao regravados (achar_set() so faz glob, nao depende deles).

Indices adicionados a 03_Indices_Energies (mesma classe de BRENT/WTI, deposito
2500): .US30Cash, .US500Cash, .USTECHCash, .JP225Cash, .DE40Cash -- pedido do
dono, 2026-09-22 ("os que voce falou de deixar de fora, vamos fazer em
sequencia"), mesmo criterio de tendencia sustentada (3 anos positivos) usado
pra XAGUSD/XAUEUR/AAPL/NVDA/AMZN.

    python gerar_templates_indices.py --dry     # so lista o que geraria
    python gerar_templates_indices.py            # grava (na instalacao do
                                                  #  WRX_MT5_* atual)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import generate_system_sets as g

NOVOS_INDICES = [".US30Cash", ".US500Cash", ".USTECHCash", ".JP225Cash",
                 ".DE40Cash"]
CLASSE = "03_Indices_Energies"


def gerar(dry: bool) -> list[dict]:
    ac = g.CLASSES[CLASSE]
    manifest: list[dict] = []
    for asset in NOVOS_INDICES:
        for system in g.SYSTEMS:
            lados = ("BUY", "SELL", "BOTH") if system.code in g.BILATERAL \
                else ("BUY", "SELL")
            for side in lados:
                for ichimoku in (False, True):
                    variant = "ICHIMOKU" if ichimoku else "MULTI"
                    name = f"WRX {system.code} {asset} {side} {variant}"
                    magic = g.magic_estavel(
                        f"{CLASSE}/{asset}/{system.code}/{side}_{variant}", {})
                    p = g.Profile()
                    g.apply_defaults(p, ac, side, magic, name)
                    g.apply_core(p, ac, ichimoku,
                                grid=system.code in ("07_GRID_SEPARATE",
                                                     "12_GRID_INVERSO"))
                    g.apply_system(p, system.code, ac, side)
                    if system.code in g.SISTEMAS_RECUPERACAO_OPCIONAL:
                        p.opt("MaxMartingaleSteps", 3, 2, 2, 8)
                        p.opt("DAlembertStep", 0.02, 0.01, 0.02, 0.09)
                    g.apply_sizing_and_formula(p, system.code, ac)
                    p.desativar_inertes()

                    missing = [n for n in g.SCHEMA if n not in p.values]
                    if missing:
                        raise SystemExit(f"{name}: sem valor -> {missing}")

                    passes = p.passes()
                    algorithm = ("COMPLETE_SEARCH" if passes <= 20_000
                                else "FAST_GENETIC")
                    header = [
                        "; White Rabbit X - set de otimizacao por sistema",
                        f"; Sistema={system.code} ({system.label})",
                        f"; Ativo={asset} | Classe={CLASSE} | Lado={side}",
                        "; Indicadores=" + ("Ichimoku" if ichimoku else
                                            "MACD/EMA/Momentum/Stochastic/TRIX"),
                        f"; ParametrosOtimizados={len(p.flags())}",
                        f"; Combinacoes={passes:,}".replace(",", "."),
                        f"; Algoritmo={algorithm}",
                        f"; Status={system.status}",
                        f"; Nota={system.notes}",
                        "; Desligue (Y->N) o que ja tiver resolvido antes da "
                        "proxima rodada.",
                    ]
                    content = g.render(p, header)
                    rel = (Path(CLASSE) / asset / system.code /
                           f"{side}_{variant}.set")
                    target = g.OUTPUT / rel
                    manifest.append({
                        "Class": CLASSE, "Symbol": asset, "System": system.code,
                        "Side": side, "Variant": variant,
                        "OptimizedParams": len(p.flags()),
                        "Combinations": passes, "Algorithm": algorithm,
                        "MagicNumber": magic, "Status": system.status,
                        "Path": rel.as_posix(),
                        "SHA256": hashlib.sha256(
                            content.encode("utf-16")).hexdigest().upper(),
                        "existia_antes": target.exists(),
                    })
                    if not dry:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(content, encoding="utf-16")
    return manifest


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    print("OUTPUT (instalacao alvo):", g.OUTPUT)
    m = gerar(args.dry)
    ja_existiam = sum(1 for r in m if r["existia_antes"])
    print(f"{len(m)} combos ({len(NOVOS_INDICES)} ativos x {len(g.SYSTEMS)} "
          f"sistemas x lados/variantes) | ja existiam antes: {ja_existiam}")
    if args.dry:
        print("(dry-run: nada foi gravado)")
        for r in m[:8]:
            print(" ", r["Path"], "|", r["Combinations"], "combinacoes")
    else:
        print("gravado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
