# -*- coding: utf-8 -*-
"""Validacao final antes do LIVE dos sets aprovados (VALIDADO_*) desta
instalacao -- dono, 2026-09-28: "vou subir na live se tiver realmente tudo ok".

Mede o set EXATAMENTE como esta gravado (o arquivo VALIDADO_, com o sizing
da entrega) no dado que a otimizacao nunca viu -- periodo anterior ao treino
+ 90 dias finais, janelas da linha do ledger que o aprovou:
  - base: lucro somado nas janelas (tem que bater com a decisao);
  - queda maxima: passe CONTINUO dos 3 anos (o gate de drawdown so alcanca os
    sets em R; num lote fixo/grade ninguem media isso) e o capital que o lote
    pede pra ficar em DD_MAX_TRADER_PCT;
  - robustez: vizinhos +-10% dos parametros principais (plato x pico);
  - consistencia: lucro trimestre a trimestre;
  - --comparar-mercado: o mesmo set com a entrada a mercado (EntryOrderType=0),
    pra quem adotou a entrada pendente.
Nada aqui reprova: imprime o relatorio, grava validacao_live_<combo>.json e
acrescenta uma linha ao ledger com `alertas_trader`.

    python validar_live.py [--comparar-mercado] [--dry]
    python validar_live.py --so-queda      # so a queda maxima (~2 min por set),
                                           # somada aos alertas ja gravados
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import campanha
import optimize_sets as base
import optimize_two_stage as ots
import ready_library
import relatorio_resumo
from remedir_campeoes import ler_ledger

AQUI = Path(__file__).resolve().parent


def linha_do_set(arq: Path) -> dict | None:
    info = ready_library.analisar_nome(arq.name)
    if info is None:
        return None
    iguais = [r for r in ler_ledger()
              if r.get("sistema") == info["sistema"]
              and r.get("variante") == info["variante"]
              and str(r.get("simbolo", "")).replace(".", "_") == info["simbolo"]
              and r.get("parametros") and r.get("janela_treino")
              and not ots.conferir_set(arq, r["parametros"])]
    return iguais[-1] if iguais else None


def dd_valor_do_relatorio() -> float | None:
    """Queda maxima do patrimonio em MOEDA no ultimo relatorio do tester desta
    instalacao (conf_wrx.htm): o campo vem como '71.10% (770.49)'."""
    try:
        txt = relatorio_resumo.resumo_relatorio(
            base.DADOS / "conf_wrx.htm").get("equity_dd_relative") or ""
    except (OSError, ValueError):
        return None
    m = re.search(r"\(([\d\s.,]+)\)", txt)
    if not m:
        return None
    try:
        return float(m.group(1).replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def medir_queda_continua(arq: Path, params: dict, simbolo: str, inicio: str,
                         fim: str, deposito: int) -> dict:
    """Passe continuo (WFO fora, como vai ao ar) de `inicio` a `fim`."""
    med = ots._medir_desempenho(
        arq, dict(params, AtivarWFO="false", MetodoDeEntradawfo="1"),
        simbolo, "M1", inicio, fim, deposito)
    queda = ots.resumir_queda(med.get("max_dd_pct"), dd_valor_do_relatorio(),
                              deposito, f"no passe continuo {inicio}..{fim}")
    queda.update(lucro=med.get("profit"), trades=med.get("trades"),
                 janela=[inicio, fim])
    return queda


def contexto(arq: Path) -> tuple | None:
    """(linha do ledger, simbolo, deposito, janelas nunca vistas, params)."""
    row = linha_do_set(arq)
    if row is None:
        return None
    simbolo = row["simbolo"]
    deposito = campanha.resolver_deposito(simbolo, None)
    treino_ini, treino_fim = row["janela_treino"].split("..")
    quando = datetime.fromisoformat(row["quando"])
    inicio_pa = (quando - timedelta(days=round(ots.ANOS_HOLDOUT_LONGO * 365))
                 ).strftime("%Y.%m.%d")
    janelas = [(inicio_pa, treino_ini), (treino_fim, quando.strftime("%Y.%m.%d"))]
    params = ots.valores_do_set(arq)          # o set inteiro, como vai ao ar
    return row, simbolo, deposito, janelas, params


def validar(arq: Path, comparar_mercado: bool, dry: bool) -> None:
    print(f"\n=== {arq.name}", flush=True)
    ctx = contexto(arq)
    if ctx is None:
        print("   sem linha do ledger (com janela_treino) pra este set -- pulando.")
        return
    row, simbolo, deposito, janelas, params = ctx
    print(f"   dado nunca visto: {janelas[0][0]}..{janelas[0][1]} + "
          f"{janelas[1][0]}..{janelas[1][1]} | deposito {deposito}", flush=True)

    base_lucro, base_trades = ots.lucro_nunca_visto(arq, params, simbolo, "M1",
                                                    janelas, deposito)
    print(f"   base: lucro {base_lucro} em {base_trades} trades", flush=True)
    rel = {"set": arq.name, "janelas": janelas, "deposito": deposito,
           "base": {"lucro": base_lucro, "trades": base_trades}}
    if comparar_mercado and str(params.get("EntryOrderType", "0")) != "0":
        m_lucro, m_trades = ots.lucro_nunca_visto(
            arq, dict(params, EntryOrderType="0"), simbolo, "M1", janelas, deposito)
        rel["mercado"] = {"lucro": m_lucro, "trades": m_trades}
        print(f"   mesma estrategia com entrada A MERCADO: lucro {m_lucro} em "
              f"{m_trades} trades", flush=True)
    queda = medir_queda_continua(arq, params, simbolo, janelas[0][0],
                                 janelas[1][1], deposito)
    print(("   ALERTA " if queda["alerta"] else "   ") + queda["msg"], flush=True)
    robustez = ots.medir_robustez(arq, params, simbolo, "M1", janelas, deposito)
    print(("   ALERTA " if robustez["alerta"] else "   ") + robustez["msg"], flush=True)
    for v in robustez["variacoes"]:
        print(f"      {v['eixo']}={v['valor']}: lucro {v['lucro']} ({v['trades']} trades)")
    consistencia = ots.medir_consistencia(arq, params, simbolo, "M1", janelas,
                                          deposito)
    print(("   ALERTA " if consistencia["alerta"] else "   ") + consistencia["msg"],
          flush=True)
    for q in consistencia["trimestres"]:
        print(f"      {q['inicio']}..{q['fim']}: lucro {q['lucro']} ({q['trades']} trades)")
    rel.update(queda_maxima=queda, robustez=robustez, consistencia=consistencia)
    saida = AQUI / f"validacao_live_{arq.stem}.json"
    saida.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   relatorio: {saida.name}", flush=True)
    if dry:
        return
    novo = dict(row)
    novo.update({"quando": datetime.now().isoformat(timespec="seconds"),
                 "alertas_trader": {"robustez": robustez,
                                    "consistencia": consistencia,
                                    "queda_maxima": queda},
                 "validacao_live": {"de": row.get("quando"), "base": rel["base"],
                                    "mercado": rel.get("mercado")},
                 "proveniencia": ots.proveniencia(row.get("variante", ""))})
    campanha.registrar(novo)


def validar_so_queda(arq: Path, dry: bool) -> None:
    """So a queda maxima, somada aos alertas que a linha ja tem (robustez e
    consistencia de uma rodada completa anterior)."""
    print(f"\n=== {arq.name}", flush=True)
    ctx = contexto(arq)
    if ctx is None:
        print("   sem linha do ledger (com janela_treino) pra este set -- pulando.")
        return
    row, simbolo, deposito, janelas, params = ctx
    queda = medir_queda_continua(arq, params, simbolo, janelas[0][0],
                                 janelas[1][1], deposito)
    print(("   ALERTA " if queda["alerta"] else "   ") + queda["msg"], flush=True)
    print(f"   no mesmo passe: lucro {queda['lucro']} em {queda['trades']} trades",
          flush=True)
    saida = AQUI / f"validacao_live_{arq.stem}.json"
    rel = (json.loads(saida.read_text(encoding="utf-8")) if saida.exists()
           else {"set": arq.name})
    rel["queda_maxima"] = queda
    saida.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   relatorio: {saida.name}", flush=True)
    if dry:
        return
    novo = dict(row)
    alertas = dict(row.get("alertas_trader") or {})
    alertas["queda_maxima"] = queda
    novo.update({"quando": datetime.now().isoformat(timespec="seconds"),
                 "alertas_trader": alertas,
                 "proveniencia": ots.proveniencia(row.get("variante", ""))})
    campanha.registrar(novo)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comparar-mercado", action="store_true")
    ap.add_argument("--so-queda", action="store_true",
                    help="mede so a queda maxima dos 3 anos continuos")
    ap.add_argument("--dry", action="store_true", help="nao grava no ledger")
    args = ap.parse_args()
    print("pasta de dados:", ready_library.TESTER, flush=True)
    sets = sorted(ready_library.TESTER.glob("VALIDADO_*.set"))
    if not sets:
        print("nenhum VALIDADO_ nesta instalacao.")
    for arq in sets:
        if args.so_queda:
            validar_so_queda(arq, args.dry)
        else:
            validar(arq, args.comparar_mercado, args.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
