# -*- coding: utf-8 -*-
"""Revalida candidatos APROVADOS refazendo so os gates finais, com a medicao
CORRIGIDA (escolher_linha_propria), sem repetir a busca.

Motivo (2026-09-20): o holdout de 3 anos, o periodo anterior, o WFA e o PF/DD
do JSON liam linha do terminal vizinho no arquivo ALL_FORMULAS da maquina
(ver project_contaminacao_all_formulas_entre_terminais). As aprovacoes feitas
com os dois terminais rodando juntos tem elegibilidade desconhecida -- inclusive
as que sustentam as formulas aplicadas em FORMULA_POR_SISTEMA.

Para cada candidato (parametros vencedores gravados no JSON final do log):
  1. catastrofe: passe continuo de 3 anos, saldo final >= 50% do deposito;
  2. periodo anterior ao treino: perda <= 20% do deposito;
  3. WFA de reotimizacao (4 ciclos): WFE global > 0.
Mesmas funcoes e limites do circuito (optimize_two_stage.py). Grava
`revalidacao_resultados.jsonl` e acorda o revisor via auditoria_eventos.log.

    python revalidar_aprovados.py --dry          # so lista os candidatos
    python revalidar_aprovados.py                # revalida todos
    python revalidar_aprovados.py --so "04_SLTP_TRAIL XAUUSD f11"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import auditar_combo as ac

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "revalidacao_resultados.jsonl"
EVENTOS = AQUI / "auditoria_eventos.log"
PERIODO = "M1"

# (rotulo, log com o JSON final, formula que produziu esse candidato)
SWEEPS = [
    ("04_SLTP_TRAIL XAUUSD f04", "sweep_04_SLTP_TRAIL_XAUUSD_04_EfficiencyRelativeToDeposit.log", 4),
    ("04_SLTP_TRAIL XAUUSD f08", "sweep_04_SLTP_TRAIL_XAUUSD_08_SharpeAdjustedByDD.log", 8),
    ("04_SLTP_TRAIL XAUUSD f09", "sweep_04_SLTP_TRAIL_XAUUSD_09_PessimisticProfit.log", 9),
    ("04_SLTP_TRAIL XAUUSD f10", "sweep_04_SLTP_TRAIL_XAUUSD_10_ResilienceToDrawdown.log", 10),
    ("04_SLTP_TRAIL XAUUSD f11", "sweep_04_SLTP_TRAIL_XAUUSD_11_ReturnUniformity.log", 11),
    ("04_SLTP_TRAIL XAUUSD f12", "sweep_04_SLTP_TRAIL_XAUUSD_12_SystemRobustness.log", 12),
    ("11_SIGNAL_ONLY XAUUSD f03", "sweep_11_SIGNAL_ONLY_XAUUSD_03_ProfitWinTradeDD.log", 3),
    ("11_SIGNAL_ONLY XAUUSD f09", "sweep_11_SIGNAL_ONLY_XAUUSD_09_PessimisticProfit.log", 9),
    ("11_SIGNAL_ONLY XAUUSD f11", "sweep_11_SIGNAL_ONLY_XAUUSD_11_ReturnUniformity.log", 11),
    ("07_GRID_SEPARATE AUDNZD f10", "sweep_07_GRID_SEPARATE_AUDNZD_10_ResilienceToDrawdown.log", 10),
    ("01_SLTP EURUSD f14", "sweep_01_SLTP_EURUSD_14_SomaR.log", 14),
    ("02_SLTP_ORGANIC GBPUSD f04", "sweep_02_SLTP_ORGANIC_GBPUSD_04_EfficiencyRelativeToDeposit.log", 4),
    ("02_SLTP_ORGANIC GBPUSD f11", "sweep_02_SLTP_ORGANIC_GBPUSD_11_ReturnUniformity.log", 11),
]
# Reprovadas NO GATE FINAL (holdout/periodo anterior/WFA) sob a medicao
# contaminada: se aqui der REVALIDADO, a reprovacao original estava errada.
REPROVADOS_FINAL = [
    ("REPROV 01_SLTP EURUSD f15", "sweep_01_SLTP_EURUSD_15_ZeusCompositeScore.log", 15),
    ("REPROV 02_SLTP_ORGANIC EURUSD f14", "sweep_02_SLTP_ORGANIC_EURUSD_14_SomaR.log", 14),
    ("REPROV 04_SLTP_TRAIL XAUUSD f01", "sweep_04_SLTP_TRAIL_XAUUSD_01_GridSurvivalScore.log", 1),
    ("REPROV 04_SLTP_TRAIL XAUUSD f03", "sweep_04_SLTP_TRAIL_XAUUSD_03_ProfitWinTradeDD.log", 3),
    ("REPROV 05_BE_TRAIL XAUUSD f03", "sweep_05_BE_TRAIL_XAUUSD_03_ProfitWinTradeDD.log", 3),
]
# Campeoes REAIS da campanha (bloco APROVADO no log): (rotulo, log, "SIM SIS VAR")
CAMPEOES = [
    ("CAMPEAO 02_SLTP_ORGANIC GBPUSD", "campanha_clone_handoff_producao.log",
     "GBPUSD 02_SLTP_ORGANIC BOTH_MULTI"),
    ("CAMPEAO 03_TRAIL_ONLY GBPUSD", "campanha_clone_handoff_producao.log",
     "GBPUSD 03_TRAIL_ONLY BOTH_MULTI"),
]
_CAB_JANELA = re.compile(
    r"^=== (\S+) (\S+) (\S+) \| (\d{4}\.\d\d\.\d\d) a (\d{4}\.\d\d\.\d\d) ===",
    re.M)


def deposito_do_ativo(simbolo: str) -> int:
    return 10000 if simbolo == "XAUUSD" else 1000


def _candidato(rotulo: str, texto: str, formula: int | None) -> dict | None:
    js = ac.json_final(texto)
    m = _CAB_JANELA.search(texto)
    if not js or not m or not js.get("parametros"):
        return None
    return {"rotulo": rotulo, "simbolo": js["simbolo"],
            "sistema": js["sistema"], "variante": js["variante"],
            "parametros": js["parametros"], "formula": formula,
            "inicio": m.group(4), "fim": m.group(5),
            "deposito": deposito_do_ativo(js["simbolo"])}


def carregar_candidatos() -> list[dict]:
    from generate_system_sets import FORMULA_POR_SISTEMA
    out = []
    for rotulo, nome, formula in SWEEPS + REPROVADOS_FINAL:
        f = AQUI / nome
        c = _candidato(rotulo, f.read_text(encoding="utf-8", errors="replace"),
                       formula) if f.exists() else None
        if c is None:
            print(f"AVISO: sem candidato legivel em {nome}", flush=True)
            continue
        out.append(c)
    for rotulo, nome, chave in CAMPEOES:
        f = AQUI / nome
        if not f.exists():
            continue
        alvo = None
        for rot, bloco in ac.blocos_campanha(
                f.read_text(encoding="utf-8", errors="replace")):
            if rot == chave and ac.auditar(bloco, rot)["veredito"] == "APROVADO":
                alvo = bloco  # o mais recente aprovado
        if alvo is None:
            print(f"AVISO: sem bloco APROVADO de {chave}", flush=True)
            continue
        sistema = chave.split()[1]
        c = _candidato(rotulo, alvo, FORMULA_POR_SISTEMA.get(sistema))
        if c:
            out.append(c)
    return out


def emitir(texto: str) -> None:
    print(texto, flush=True)
    with EVENTOS.open("a", encoding="utf-8") as fh:
        fh.write(texto + "\n")


def revalidar(c: dict) -> dict:
    import optimize_sets as base
    import optimize_two_stage as ots
    import wfa_real

    origem = base.achar_set(c["simbolo"], c["sistema"], c["variante"])
    if origem is None:
        return {"erro": "sem template (achar_set devolveu None)"}
    travados = {k: str(v) for k, v in c["parametros"].items()}
    if c.get("formula"):
        travados["selectedFormula"] = str(c["formula"])  # criterio do WFA
    dep = c["deposito"]
    fim_h = datetime.now().strftime("%Y.%m.%d")
    inicio_h = (datetime.now() - timedelta(
        days=round(ots.ANOS_HOLDOUT_LONGO * 365))).strftime("%Y.%m.%d")
    res: dict = {"rotulo": c["rotulo"], "quando": datetime.now().isoformat(
        timespec="seconds"), "janela_3a": [inicio_h, fim_h]}
    t0 = time.time()

    # 1) catastrofe: 3 anos continuos
    d3 = ots._medir_desempenho(
        origem, dict(travados, AtivarWFO="false", MetodoDeEntradawfo="1"),
        c["simbolo"], PERIODO, inicio_h, fim_h, dep)
    res["tres_anos_lucro"] = d3.get("profit")
    res["tres_anos_trades"] = d3.get("trades")
    res["tres_anos_expectancy_r"] = d3.get("expectancy_r")
    ok_cat, mot_cat = ots.avaliar_catastrofe(d3.get("profit"), dep)
    res["catastrofe_ok"] = ok_cat

    # 2) periodo anterior ao treino
    dias_ant = (datetime.strptime(c["inicio"], "%Y.%m.%d")
                - datetime.strptime(inicio_h, "%Y.%m.%d")).days
    ok_ant, msg_ant = True, "nao avaliado (poucos dias)"
    if dias_ant >= ots.MIN_DIAS_PERIODO_ANTERIOR:
        ant = wfa_real.medir_holdout(origem, travados, c["simbolo"], PERIODO,
                                     inicio_h, c["inicio"], dep)
        res["anterior_lucro"] = ant["profit"]
        res["anterior_trades"] = ant["metricas"].get("trades")
        ok_ant, msg_ant = ots.avaliar_periodo_anterior(
            ant["profit"], ant["metricas"].get("trades"), dep)
    res["anterior_ok"] = ok_ant
    res["anterior_msg"] = msg_ant

    # 3) WFA de reotimizacao (mesma chamada do circuito)
    numeros = ots.eixos_reotimizaveis(c["sistema"], travados.get("EntryIndicator"))
    travados_wfa = {k: v for k, v in travados.items() if k not in numeros}
    wfa = wfa_real.medir_wfa(origem, travados_wfa, numeros, c["simbolo"],
                             c["sistema"], PERIODO, inicio_h, fim_h, dep,
                             ciclos_alvo=4, timeout=3600)
    if wfa["wfe_global_pct"] is None:  # mesmo retry do circuito (0/0 transitorio)
        wfa = wfa_real.medir_wfa(origem, travados_wfa, numeros, c["simbolo"],
                                 c["sistema"], PERIODO, inicio_h, fim_h, dep,
                                 ciclos_alvo=4, timeout=3600)
    res["wfe_global_pct"] = wfa["wfe_global_pct"]
    res["wfa_ciclos_positivos"] = wfa["ciclos_positivos"]
    res["wfa_detalhe"] = [{k: v for k, v in j.items() if k != "params"}
                          for j in wfa["detalhe"]]
    ok_wfa = wfa["wfe_global_pct"] is not None and wfa["wfe_global_pct"] > 0
    res["wfa_ok"] = ok_wfa

    res["veredito"] = "REVALIDADO" if (ok_cat and ok_ant and ok_wfa) else "REPROVADO"
    res["falhou_em"] = [n for n, ok in (("catastrofe", ok_cat),
                                        ("periodo_anterior", ok_ant),
                                        ("wfa", ok_wfa)) if not ok]
    res["minutos"] = round((time.time() - t0) / 60, 1)
    return res


def resumo(c: dict, r: dict) -> str:
    if "erro" in r:
        return f"REVALIDACAO {c['rotulo']} -> ERRO: {r['erro']}"
    wfe = r.get("wfe_global_pct")
    return (f"REVALIDACAO {c['rotulo']} -> {r['veredito']}"
            + (f" (falhou: {', '.join(r['falhou_em'])})" if r["falhou_em"] else "")
            + f"\n  3 anos: lucro {r.get('tres_anos_lucro')} / "
            f"{r.get('tres_anos_trades')} tr / exp {r.get('tres_anos_expectancy_r')}R"
            f" | anterior: {r.get('anterior_lucro')} ({r.get('anterior_trades')} tr)"
            f" | WFA {r.get('wfa_ciclos_positivos')} WFE "
            f"{'n/d' if wfe is None else round(wfe)}% | {r.get('minutos')} min")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--so", default="", help="rotulos separados por ';'")
    args = ap.parse_args()
    cands = carregar_candidatos()
    if args.so:
        quer = {s.strip() for s in args.so.split(";")}
        cands = [c for c in cands if c["rotulo"] in quer]
    if args.dry:
        for c in cands:
            print(f"{c['rotulo']:<34} {c['simbolo']} {c['sistema']} "
                  f"{c['variante']} f{c['formula']} dep {c['deposito']} "
                  f"treino {c['inicio']}..{c['fim']} "
                  f"({len(c['parametros'])} params)")
        print(f"{len(cands)} candidatos")
        return 0
    for c in cands:
        try:
            r = revalidar(c)
        except Exception as exc:  # um candidato quebrado nao para a fila
            r = {"erro": f"{type(exc).__name__}: {exc}"}
            traceback.print_exc()
        with RESULTADOS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rotulo": c["rotulo"], **r},
                                ensure_ascii=False) + "\n")
        emitir(resumo(c, r))
    emitir(f"REVALIDACAO: fila de {len(cands)} candidato(s) terminou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
