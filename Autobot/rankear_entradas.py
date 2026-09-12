# -*- coding: utf-8 -*-
"""Estagio 0: rankeia a ENTRADA (sem nenhuma administracao) por ativo/lado,
nas 4 familias (MULTI, ICHIMOKU, BOLLINGER, CANDLES), antes de rodar os 9
sistemas de administracao de verdade.

O PORQUE (dono, 2026-09-10): cada um dos 9 sistemas (01_SLTP..12_GRID_INVERSO)
descobre a entrada sozinho, com o orcamento do genetico do Estagio 1 dividido
entre ate 12 indicadores concorrentes -- a mesma pergunta ("qual entrada
funciona neste ativo?") e respondida de novo, do zero, em cada sistema.
Rodar 6 meses pra "explorar tudo" e consequencia direta disso.

Este script usa o sistema `11_SIGNAL_ONLY`, que ja existe pronto nas 4
familias pra todo ativo (AtivarStop/AtivarTake/AtivarBreakeven/AtivarTrailATR
todos cravados false -- "nada de ATR aqui", literal) -- e o "modo puro de
entrada" que o dono pediu, sem precisar gerar nenhum .set novo. Roda o
circuito inteiro do 11_SIGNAL_ONLY (via optimize_two_stage.py, reaproveitando
rodar_combo() de campanha.py) nas 4 familias, compara por composite_score()
(a mesma metrica ja usada nos outros gates) e grava as 4 entradas ranqueadas
-- MULTI, ICHIMOKU, BOLLINGER e CANDLES -- em
entrada_vencedora/<SIMBOLO>_<LADO>.json.

campanha.py --rankear-entrada-primeiro le esse arquivo e passa
--entrada-travada pros outros 9 sistemas: cada um pula a redescoberta da
entrada (Estagio 1 e 1.5) e ja nasce com ESCRITA_ENTRADA travada na entrada
da PROPRIA familia que esta rodando.

    python rankear_entradas.py --symbol XAUUSD --lado BUY
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import campanha
from optimize_two_stage import ESCRITA_ENTRADA

AQUI = Path(__file__).resolve().parent
SAIDA_DIR = AQUI / "entrada_vencedora"

FAMILIAS = ["MULTI", "ICHIMOKU", "BOLLINGER", "CANDLES"]
LADOS_VALIDOS = ("BUY", "SELL", "BOTH")


def caminho_saida(simbolo: str, lado: str) -> Path:
    return SAIDA_DIR / f"{simbolo}_{lado}.json"


def _entrada_do_ledger(simbolo: str, variante: str) -> dict | None:
    """Reusa um 11_SIGNAL_ONLY ja medido no ledger em vez de rodar de novo --
    mesmo espirito de feitos()/campanha.py: identidade (simbolo, sistema,
    variante), sem checar periodo (feitos() tambem nao checa)."""
    if not campanha.LEDGER.exists():
        return None
    ultimo = None
    for linha in campanha.LEDGER.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            r = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if (r.get("simbolo") == simbolo and r.get("sistema") == "11_SIGNAL_ONLY"
                and r.get("variante") == variante and "erro" not in r):
            ultimo = r
    return ultimo


def rankear(simbolo: str, lado: str, args) -> dict:
    """Roda (ou reusa) 11_SIGNAL_ONLY nas 3 familias pra (simbolo, lado) e
    devolve o dict pronto pra gravar em entrada_vencedora/*.json."""
    if lado not in LADOS_VALIDOS:
        raise SystemExit(f"--lado precisa ser um de {LADOS_VALIDOS}, veio {lado!r}")

    entradas = []
    for familia in FAMILIAS:
        variante = f"{lado}_{familia}"
        if campanha.base.achar_set(simbolo, "11_SIGNAL_ONLY", variante) is None:
            print(f"  [{familia}] sem set 11_SIGNAL_ONLY/{variante} pra "
                  f"{simbolo} -- pulando familia.", flush=True)
            continue
        reg = _entrada_do_ledger(simbolo, variante)
        if reg is not None:
            print(f"  [{familia}] reusando do ledger: retencao_oos="
                  f"{reg.get('retencao_oos')}", flush=True)
        else:
            print(f"  [{familia}] rodando 11_SIGNAL_ONLY/{variante}...", flush=True)
            reg = campanha.rodar_combo(simbolo, "11_SIGNAL_ONLY", variante, args)
            if reg.get("pausado"):
                raise SystemExit("pausa solicitada durante o ranking de entrada "
                                 "-- retome depois, nada foi gravado ainda.")
            campanha.registrar(reg)
        # Rankeia por retencao_oos, NAO composite_score (achado 2026-09-12):
        # composite_score() precisa de trades/profit_factor/max_dd_pct vindos
        # de ler_metricas(), que so extrai "trades" da linha "R METRICS" que a
        # propria EA imprime -- e essa linha exige um SL/TP ativo pra ter uma
        # unidade de R pra normalizar. 11_SIGNAL_ONLY crava AtivarStop=false
        # (sem rede de protecao, de proposito), entao a EA NUNCA imprime a
        # linha, "trades" sai None mesmo com trades reais acontecendo, e
        # composite_score sai None em cascata -- pra TODA familia, sempre,
        # nao um bug deste ranking. retencao_oos vem de uma regex separada
        # ("Out-of-Sample Retention:"), independente do R-metrics, e por
        # isso continua confiavel aqui. Corrigir composite_score pra
        # sistemas sem SL fica pra outra hora -- mexe em ler_metricas()/no
        # log que a EA imprime, nao so neste script.
        if "erro" in reg or reg.get("retencao_oos") is None:
            print(f"  [{familia}] sem retencao_oos utilizavel "
                  f"({reg.get('erro', 'sem candidato aprovado no piso')}) -- "
                  "fora do ranking.", flush=True)
            continue
        escrita = {k: v for k, v in (reg.get("parametros") or {}).items()
                  if k in ESCRITA_ENTRADA}
        entradas.append({
            "familia": familia,
            "variante": variante,
            "retencao_oos": reg["retencao_oos"],
            "composite_score": reg.get("composite_score"),
            "escrita": escrita,
        })

    entradas.sort(key=lambda e: e["retencao_oos"], reverse=True)
    return {
        "simbolo": simbolo,
        "lado": lado,
        "inicio": args.inicio,
        "fim": args.fim,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "entradas": entradas,
    }


def cache_valido(caminho: Path, inicio: str, fim: str) -> bool:
    """O cache so vale pro MESMO periodo de sweep -- um ranking feito num
    --from/--to diferente comparou entradas em dados diferentes, nao serve
    de referencia pros sistemas rodando o periodo atual."""
    if not caminho.exists():
        return False
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return dados.get("inicio") == inicio and dados.get("fim") == fim and bool(
        dados.get("entradas"))


def garantir_ranking(simbolo: str, lado: str, args) -> Path:
    """Usado por campanha.py --rankear-entrada-primeiro: devolve o path do
    JSON, rodando o ranking so se nao houver cache valido pro periodo atual."""
    caminho = caminho_saida(simbolo, lado)
    if cache_valido(caminho, args.inicio, args.fim):
        return caminho
    resultado = rankear(simbolo, lado, args)
    SAIDA_DIR.mkdir(exist_ok=True)
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return caminho


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--lado", required=True, choices=LADOS_VALIDOS)
    ap.add_argument("--from", dest="inicio", default=campanha.anos_atras(3))
    ap.add_argument("--to", dest="fim", default=datetime.now().strftime("%Y.%m.%d"))
    ap.add_argument("--deposit", type=int, default=None)
    ap.add_argument("--min-retencao", type=float, default=30.0)
    ap.add_argument("--timeout", type=int, default=43200)
    ap.add_argument("--recuperacao", default="nenhuma")
    args = ap.parse_args()

    resultado = rankear(args.symbol, args.lado, args)
    SAIDA_DIR.mkdir(exist_ok=True)
    caminho = caminho_saida(args.symbol, args.lado)
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    print(f"\n=== ranking de entrada: {args.symbol} {args.lado} ===")
    if not resultado["entradas"]:
        print("  nenhuma familia produziu candidato utilizavel.")
    for i, e in enumerate(resultado["entradas"], 1):
        score = e.get("composite_score")
        print(f"  {i}. {e['familia']:<10} retencao={e['retencao_oos']:.1f}% "
              f"score={'n/d (sem SL, ver ler_metricas)' if score is None else f'{score:.2f}'} "
              f"| {e['escrita']}", flush=True)
    print(f"\ngravado em {caminho}")
    return 0 if resultado["entradas"] else 1


if __name__ == "__main__":
    sys.exit(main())
