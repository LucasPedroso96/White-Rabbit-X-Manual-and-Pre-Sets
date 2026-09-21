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
# Combos da campanha OFICIAL reprovados so no gate final sob codigo antigo
# (contaminado): (rotulo, log, "SIM SIS VAR"). Ex.: USDJPY/03_TRAIL_ONLY passou
# retencao/divergencia/% e caiu em holdout+WFA medidos com o arquivo do vizinho.
REPROV_CAMPANHA = [
    ("REPROV-CAMP USDJPY 03_TRAIL_ONLY", "campanha_oficial_trail.log",
     "USDJPY 03_TRAIL_ONLY BOTH_MULTI"),
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
    for rotulo, nome, chave in CAMPEOES + REPROV_CAMPANHA:
        veredito_alvo = "REPROVADO" if rotulo.startswith("REPROV") else "APROVADO"
        f = AQUI / nome
        if not f.exists():
            continue
        alvo = None
        for rot, bloco in ac.blocos_campanha(
                f.read_text(encoding="utf-8", errors="replace")):
            if rot == chave and ac.auditar(bloco, rot)["veredito"] == veredito_alvo:
                alvo = bloco  # o mais recente com o veredito procurado
        if alvo is None:
            print(f"AVISO: sem bloco {veredito_alvo} de {chave}", flush=True)
            continue
        sistema = chave.split()[1]
        c = _candidato(rotulo, alvo, FORMULA_POR_SISTEMA.get(sistema))
        if c:
            out.append(c)
    return out


def carregar_anteriores() -> dict[str, dict]:
    """Melhor registro por rotulo em revalidacao_resultados.jsonl: o que tem
    veredito final vence; senao a fase 1 valida mais recente."""
    out: dict[str, dict] = {}
    if not RESULTADOS.exists():
        return out
    for ln in RESULTADOS.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        rot = r.get("rotulo")
        if not rot:
            continue
        if r.get("veredito"):
            out[rot] = r
        elif rot not in out or not out[rot].get("veredito"):
            out[rot] = r
    return out


def emitir(texto: str) -> None:
    print(texto, flush=True)
    with EVENTOS.open("a", encoding="utf-8") as fh:
        fh.write(texto + "\n")


def _contexto(c: dict):
    import optimize_sets as base
    import optimize_two_stage as ots
    import wfa_real
    origem = base.achar_set(c["simbolo"], c["sistema"], c["variante"])
    travados = {k: str(v) for k, v in c["parametros"].items()}
    if c.get("formula"):
        travados["selectedFormula"] = str(c["formula"])  # criterio do WFA
    fim_h = datetime.now().strftime("%Y.%m.%d")
    inicio_h = (datetime.now() - timedelta(
        days=round(ots.ANOS_HOLDOUT_LONGO * 365))).strftime("%Y.%m.%d")
    return ots, wfa_real, origem, travados, inicio_h, fim_h


def fase1(c: dict) -> dict:
    """Camadas BARATAS (2-3 passes): catastrofe e periodo anterior."""
    ots, wfa_real, origem, travados, inicio_h, fim_h = _contexto(c)
    if origem is None:
        return {"erro": "sem template (achar_set devolveu None)"}
    dep = c["deposito"]
    res: dict = {"quando": datetime.now().isoformat(timespec="seconds"),
                 "janela_3a": [inicio_h, fim_h]}
    t0 = time.time()
    # 1) catastrofe: 3 anos continuos
    d3 = ots._medir_desempenho(
        origem, dict(travados, AtivarWFO="false", MetodoDeEntradawfo="1"),
        c["simbolo"], PERIODO, inicio_h, fim_h, dep)
    res["tres_anos_lucro"] = d3.get("profit")
    res["tres_anos_trades"] = d3.get("trades")
    res["tres_anos_expectancy_r"] = d3.get("expectancy_r")
    res["catastrofe_ok"] = ots.avaliar_catastrofe(d3.get("profit"), dep)[0]
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
    res["fase1_ok"] = bool(res["catastrofe_ok"] and ok_ant)
    res["minutos_fase1"] = round((time.time() - t0) / 60, 1)
    return res


def fase2(c: dict, res: dict) -> dict:
    """WFA de reotimizacao (4 ciclos) -- a parte CARA (~8 mil passes por
    janela no XAUUSD). So roda em quem passou a fase 1."""
    ots, wfa_real, origem, travados, inicio_h, fim_h = _contexto(c)
    dep = c["deposito"]
    t0 = time.time()
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
    res["wfa_ok"] = (wfa["wfe_global_pct"] is not None
                     and wfa["wfe_global_pct"] > 0)
    res["minutos_fase2"] = round((time.time() - t0) / 60, 1)
    return res


def fechar(res: dict) -> dict:
    ok = {"catastrofe": res.get("catastrofe_ok", True),
          "periodo_anterior": res.get("anterior_ok", True),
          "wfa": res.get("wfa_ok", True)}
    res["falhou_em"] = [n for n, v in ok.items() if not v]
    res["veredito"] = "REVALIDADO" if not res["falhou_em"] else "REPROVADO"
    return res


def _fmt_base(r: dict) -> str:
    return (f"3 anos: lucro {r.get('tres_anos_lucro')} / "
            f"{r.get('tres_anos_trades')} tr / exp "
            f"{r.get('tres_anos_expectancy_r')}R | anterior: "
            f"{r.get('anterior_lucro')} ({r.get('anterior_trades')} tr)")


def resumo_fase1(c: dict, r: dict) -> str:
    if "erro" in r:
        return f"REVALIDACAO {c['rotulo']} -> ERRO: {r['erro']}"
    if r["fase1_ok"]:
        return (f"REVALIDACAO fase1 {c['rotulo']} -> PASSOU catastrofe e "
                f"periodo anterior (WFA a seguir)\n  {_fmt_base(r)}")
    falhou = [n for n, v in (("catastrofe", r["catastrofe_ok"]),
                             ("periodo_anterior", r["anterior_ok"])) if not v]
    return (f"REVALIDACAO {c['rotulo']} -> REPROVADO (falhou: "
            f"{', '.join(falhou)}) sem precisar de WFA\n  {_fmt_base(r)}")


def resumo_final(c: dict, r: dict) -> str:
    wfe = r.get("wfe_global_pct")
    return (f"REVALIDACAO {c['rotulo']} -> {r['veredito']}"
            + (f" (falhou: {', '.join(r['falhou_em'])})" if r["falhou_em"] else "")
            + f"\n  {_fmt_base(r)} | WFA {r.get('wfa_ciclos_positivos')} WFE "
            f"{'n/d' if wfe is None else round(wfe)}% | fase2 "
            f"{r.get('minutos_fase2')} min")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--so", default="", help="rotulos separados por ';'")
    ap.add_argument("--continuar", action="store_true",
                    help="reaproveita revalidacao_resultados.jsonl: nao refaz "
                         "candidato com veredito final nem a fase 1 ja medida")
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
    def gravar(c: dict, r: dict) -> None:
        with RESULTADOS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rotulo": c["rotulo"], **r},
                                ensure_ascii=False) + "\n")

    # FASE 1: camadas baratas em TODOS (resultado rapido, decide quem precisa
    # da fase cara).
    estado: dict[str, dict] = {}
    anteriores = carregar_anteriores() if args.continuar else {}
    for c in cands:
        a = anteriores.get(c["rotulo"])
        if a and a.get("veredito"):  # ja tem veredito final: nao refaz nada
            estado[c["rotulo"]] = {**a, "_final": True}
            continue
        if a and a.get("fase1_ok") is not None and "erro" not in a:
            estado[c["rotulo"]] = a  # fase 1 ja medida: so falta a fase 2
            continue
        try:
            r = fase1(c)
        except Exception as exc:  # um candidato quebrado nao para a fila
            r = {"erro": f"{type(exc).__name__}: {exc}"}
            traceback.print_exc()
        estado[c["rotulo"]] = r
        if "erro" in r:
            gravar(c, {"fase": 1, **r})
        elif r["fase1_ok"]:
            gravar(c, {"fase": 1, **r})
        else:
            gravar(c, {"fase": "final", **fechar(r)})
        emitir(resumo_fase1(c, r))
    # FASE 2: WFA so nos que sobreviveram.
    for c in cands:
        r = estado[c["rotulo"]]
        if r.get("_final") or "erro" in r or not r.get("fase1_ok"):
            continue
        try:
            r = fechar(fase2(c, r))
        except Exception as exc:
            r = {**r, "erro": f"{type(exc).__name__}: {exc}"}
            traceback.print_exc()
            emitir(f"REVALIDACAO {c['rotulo']} -> ERRO no WFA: {r['erro']}")
            gravar(c, {"fase": "final", **r})
            continue
        gravar(c, {"fase": "final", **r})
        emitir(resumo_final(c, r))
    emitir(f"REVALIDACAO: fila de {len(cands)} candidato(s) terminou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
