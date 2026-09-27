# -*- coding: utf-8 -*-
"""Reavalia combos ja feitos pela regra de trader solo (dono, 2026-09-27)
SEM reotimizar.

Pega a ultima linha do ledger do combo, reusa as medidas gravadas e mede SO o
que faltou -- queda maxima dos 3 anos (sistemas em R), periodo anterior ao
treino e os 90 dias finais -- com os parametros gravados sobre o template
atual. Decide com optimize_two_stage.decidir_trader(), grava linha NOVA no
ledger (append-only, com lock) e troca o prefixo do .set quando o veredito
muda (VALIDADO_ que cai e arquivado antes, como em remedir_campeoes.py).

    python reavaliar_trader.py "USDCAD 07_GRID_SEPARATE BUY_MULTI" [...] [--dry]

Roda na instalacao onde o combo rodou (WRX_MT5_DATA_DIR do clone, se for la).
A divergencia vem do ledger (divergencia_pct) ou, em linha antiga, do log da
fila (ultima linha "divergencia: X%" do bloco do combo).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import campanha
import campeoes_arquivo
import optimize_sets as base
import optimize_two_stage as ots
import ready_library
import wfa_real
from remedir_campeoes import ler_ledger

AQUI = Path(__file__).resolve().parent


def ultima_linha(simbolo: str, sistema: str, variante: str,
                 desde: str) -> dict | None:
    linhas = [r for r in ler_ledger()
              if r.get("simbolo") == simbolo and r.get("sistema") == sistema
              and r.get("variante") == variante and not r.get("erro")
              and r.get("parametros") and str(r.get("quando", "")) >= desde]
    return linhas[-1] if linhas else None


def divergencia_do_log(simbolo: str, sistema: str, variante: str) -> float | None:
    combo = f"{simbolo} {sistema} {variante}"
    achada = None
    for log in sorted(AQUI.glob("campanha*.log"), key=lambda p: p.stat().st_mtime):
        texto = log.read_text(encoding="utf-8", errors="replace")
        cabs = list(re.finditer(r"^\[\d+/\d+\] (\S+ \S+ \S+)\s*$", texto, re.M))
        for i, m in enumerate(cabs):
            if m.group(1) != combo:
                continue
            fim = cabs[i + 1].start() if i + 1 < len(cabs) else len(texto)
            d = re.findall(r"^\s+divergencia:\s+(-?[\d.]+)%", texto[m.start():fim], re.M)
            if d:
                achada = float(d[-1])
    return achada


def set_do_combo(simbolo: str, sistema: str, variante: str,
                 params: dict) -> Path | None:
    sim = simbolo.replace(".", "_")
    for prefixo in ("VALIDADO", "REPROVADO"):
        arq = ready_library.TESTER / f"{prefixo}_{sim}_{sistema}_{variante}.set"
        if arq.exists() and not ots.conferir_set(arq, params):
            return arq
    return None


def reavaliar(combo: str, desde: str, dry: bool) -> None:
    simbolo, sistema, variante = combo.split()
    row = ultima_linha(simbolo, sistema, variante, desde)
    print(f"\n=== {combo}", flush=True)
    if row is None:
        print("   sem linha do ledger com parametros -- pulando.")
        return
    params = dict(row["parametros"])
    origem = base.achar_set(simbolo, sistema, variante)
    deposito = campanha.resolver_deposito(simbolo, None)
    treino_ini, treino_fim = row["janela_treino"].split("..")
    quando = datetime.fromisoformat(row["quando"])
    novas: list[str] = []

    div = row.get("divergencia_pct")
    if div is None:
        div = divergencia_do_log(simbolo, sistema, variante)

    r_capavel = ots.modo_de_sizing(origem) == "3"
    dd = None
    if r_capavel:
        dd = (row.get("benchmark_historico_completo") or {}).get("estrategia_max_dd_pct")
        if dd is None:
            ini = (datetime.strptime(treino_fim, "%Y.%m.%d")
                   - timedelta(days=365 * ots.PERIODO_PADRAO_HISTORICO_COMPLETO_ANOS)
                   ).strftime("%Y.%m.%d")
            print(f"   medindo queda maxima nos 3 anos ({ini}..{treino_fim})...", flush=True)
            med = ots._medir_desempenho(
                origem, dict(params, AtivarWFO="false", MetodoDeEntradawfo="1"),
                simbolo, "M1", ini, treino_fim, deposito)
            dd = med.get("max_dd_pct")
            print(f"   3 anos: lucro {med.get('profit')} | DD {dd}% | "
                  f"{med.get('trades')} trades", flush=True)
            novas.append("dd_3anos")

    sobreviveu = None
    if sistema in ots.SISTEMAS_GATE_SOBREVIVENCIA and row.get("sobrevivencia_medida"):
        sobreviveu = row.get("sobrevivencia_motivo_reprovacao") is None

    pa_lucro, pa_trades = row.get("periodo_anterior_lucro"), row.get("periodo_anterior_trades")
    if pa_lucro is None:
        inicio_holdout = (quando - timedelta(days=round(ots.ANOS_HOLDOUT_LONGO * 365))
                          ).strftime("%Y.%m.%d")
        dias = (datetime.strptime(treino_ini, "%Y.%m.%d")
                - datetime.strptime(inicio_holdout, "%Y.%m.%d")).days
        if dias >= ots.MIN_DIAS_PERIODO_ANTERIOR:
            print(f"   medindo periodo anterior ({inicio_holdout}..{treino_ini})...",
                  flush=True)
            pa = wfa_real.medir_holdout(origem, params, simbolo, "M1",
                                        inicio_holdout, treino_ini, deposito)
            pa_lucro, pa_trades = pa["profit"], pa["metricas"].get("trades")
            print(f"   periodo anterior: lucro {pa_lucro} | {pa_trades} trades", flush=True)
            novas.append("periodo_anterior")

    lacrado = row.get("holdout_lacrado")
    if not lacrado:
        fim_l = quando.strftime("%Y.%m.%d")
        print(f"   medindo 90 dias finais ({treino_fim}..{fim_l})...", flush=True)
        med_l = ots._medir_desempenho(origem, dict(params, AtivarWFO="false"),
                                      simbolo, "M1", treino_fim, fim_l, deposito)
        lacrado = ots.avaliar_holdout_lacrado(med_l.get("profit"),
                                              med_l.get("trades"), deposito)
        lacrado.update(inicio=treino_fim, fim=fim_l,
                       tick_real_pct=med_l.get("tick_real_pct"))
        print(f"   90 dias finais: {lacrado['msg']}", flush=True)
        novas.append("holdout_lacrado")

    decisao = ots.decidir_trader(div, sobreviveu, dd, pa_lucro, pa_trades,
                                 lacrado.get("profit"), lacrado.get("trades"),
                                 None, deposito)
    for linha in decisao["linhas"]:
        print(f"   {linha}", flush=True)
    aprovado = decisao["aprovado"]
    print(f"   -> {'APROVADO' if aprovado else 'REPROVADO'} pela regra de trader "
          f"(antes: {'aprovado' if row.get('aprovado') else 'reprovado em ' + str(row.get('reprovado_em'))})",
          flush=True)
    if dry:
        return

    arq = set_do_combo(simbolo, sistema, variante, params)
    novo = dict(row)
    novo.update({
        "quando": datetime.now().isoformat(timespec="seconds"),
        "aprovado": aprovado, "reprovado_em": decisao["reprovado_em"],
        "decisao_trader": decisao, "divergencia_pct": div,
        "periodo_anterior_lucro": pa_lucro, "periodo_anterior_trades": pa_trades,
        "holdout_lacrado": lacrado, "proveniencia": ots.proveniencia(variante),
        "reavaliacao_trader": {"de": row.get("quando"), "medidas_novas": novas,
                               "set": arq.name if arq else None},
    })
    if arq is None:
        print("   AVISO: .set do combo nao encontrado com estes parametros -- "
              "so o ledger foi atualizado.", flush=True)
    elif aprovado and arq.name.startswith("REPROVADO_"):
        destino = arq.with_name("VALIDADO_" + arq.name[len("REPROVADO_"):])
        os.replace(arq, destino)
        print(f"   {arq.name} -> {destino.name}", flush=True)
    elif not aprovado and arq.name.startswith("VALIDADO_"):
        versao = campeoes_arquivo.arquivar_campeao_anterior(sistema, simbolo,
                                                            variante, arq)
        destino = arq.with_name("REPROVADO_" + arq.name[len("VALIDADO_"):])
        os.replace(arq, destino)
        print(f"   arquivado v{versao}; {arq.name} -> {destino.name}", flush=True)
    campanha.registrar(novo)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("combos", nargs="+", help='"SIMBOLO SISTEMA VARIANTE"')
    ap.add_argument("--desde", default="2026-09-26T23:35",
                    help="so linhas do ledger a partir daqui (metodologia final)")
    ap.add_argument("--dry", action="store_true", help="nao grava nem renomeia")
    args = ap.parse_args()
    print("pasta de dados:", ready_library.TESTER, flush=True)
    for combo in args.combos:
        reavaliar(combo, args.desde, args.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
