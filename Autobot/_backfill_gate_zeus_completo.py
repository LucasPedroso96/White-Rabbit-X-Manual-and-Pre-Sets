# -*- coding: utf-8 -*-
"""Backfill de profit_factor/max_dd_pct/sharpe/composite_score (gate
completo do Zeus, ver avaliar_gate_relativo() em optimize_two_stage.py)
pros campeoes ATUAIS (VALIDADO_*.set) -- esses campos so existem daqui pra
frente (JSON final do Estagio 4, 2026-08-30); pra ja ter baseline HOJE,
precisa re-rodar o passe combinado de cada campeao.

Diferente de _backfill_ledger_campeoes.py (que so lia um log ja gravado):
aqui precisa rodar de VERDADE no MT5, porque o ALL_FORMULAS (PF/DD/Sharpe)
nunca foi persistido em disco pra passes antigos -- o FILE_COMMON e
sobrescrito a cada passe, so o expectancy_r (via R METRICS, impresso no
proprio log de texto) sobreviveu.

Escopo: SO combos cujo log de sweep vencedor tem o cabecalho
"=== SIMBOLO SISTEMA VARIANTE | INICIO a FIM ===" (mesmo padrao de
achar_json_vencedor() do backfill anterior) -- sem ele nao da pra saber a
janela EXATA que produziu aquele campeao, e usar uma janela errada
contaminaria o baseline com um numero que nao e o do campeao de verdade.
Combos aprovados via campanha.py direto (sem sweep_*.log, ja estavam no
ledger antes deste backfill) ficam de fora por enquanto -- nao e perda,
so nao da pra fazer com seguranca agora; pegam o campo na proxima vez que
forem re-testados.

Uso: python _backfill_gate_zeus_completo.py [--aplicar]
Sem --aplicar e dry-run (mostra quem seria rodado, sem tocar o MT5).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import auto_manager_live
import optimize_sets as base
import optimize_two_stage as ots
import ready_library as rl
from mt5_runner import garantir_terminal_livre

AQUI = Path(__file__).resolve().parent
_CABECALHO = re.compile(
    r"^=== \S+ \S+ \S+ \| ([\d.]+) a ([\d.]+) ===", re.MULTILINE)


def achar_json_e_janela(nome_set: str) -> tuple[dict, str, str, Path] | tuple[None, None, None, None]:
    marcador = f"set gravado (WFO desligado): {nome_set}"
    candidatos = []
    for log in AQUI.glob("sweep_*.log"):
        try:
            texto = log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if marcador not in texto:
            continue
        linhas = texto.splitlines()
        for i, linha in enumerate(linhas):
            if marcador not in linha:
                continue
            for seguinte in linhas[i + 1:]:
                seguinte = seguinte.strip()
                if not seguinte:
                    continue
                if seguinte.startswith("{"):
                    try:
                        reg = json.loads(seguinte)
                    except json.JSONDecodeError:
                        break
                    m = _CABECALHO.search(texto)
                    if m:
                        candidatos.append(
                            (log.stat().st_mtime, reg, m.group(1), m.group(2), log))
                break
            break
    if not candidatos:
        return None, None, None, None
    candidatos.sort(key=lambda t: t[0])
    _, reg, inicio, fim, log = candidatos[-1]
    return reg, inicio, fim, log


def rodar_combo(origem: Path, simbolo: str, parametros: dict, inicio: str,
                fim: str, deposito: float) -> dict:
    trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_BACKFILL_GATE.set"
    wfo = ots.janelas_wfo(inicio, fim)
    passo = dict(wfo, **parametros, MetodoDeEntradawfo="1",
                InterfaceLanguage="1")
    ots.reescrever(origem, trabalho, [], passo)
    ots.limpar_todas_formulas()
    r = ots.passe_unico(trabalho, simbolo, "M1", inicio, fim, deposito, 4)
    stats_list = ots.carregar_todas_formulas()
    stats = stats_list[-1] if stats_list else None
    if stats is None:
        return {}
    gp, gl = stats.get("gross_profit"), stats.get("gross_loss")
    pf = gp / abs(gl) if gp is not None and gl not in (None, 0) else None
    dd = stats.get("equity_dd_rel_pct")
    sharpe = stats.get("sharpe")
    trades = stats.get("trades")
    profit = stats.get("profit")
    score = (ots.composite_score(profit, deposito, pf, dd, trades)
            if None not in (pf, dd, trades, profit) else None)
    return {"profit_factor": pf, "max_dd_pct": dd, "sharpe": sharpe,
           "composite_score": score, "expectancy_conferida": r["expectancy"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    ligado = False
    atualizacoes = []
    for set_validado in sorted(rl.TESTER.glob("VALIDADO_*.set")):
        info = rl.analisar_nome(set_validado.name)
        if info is None:
            continue
        simbolo, sistema, variante = info["simbolo_exibicao"], info["sistema"], info["variante"]
        reg, inicio, fim, log = achar_json_e_janela(set_validado.name)
        if reg is None:
            print(f"  [SEM JANELA CONFIAVEL] {simbolo}/{sistema}/{variante} "
                  "-- sem sweep_*.log com cabecalho, pulando (nao aprovado "
                  "via sweep_formulas.py).")
            continue
        parametros = reg.get("parametros")
        # Mesmo capital minimo da CLASSE que campanha.py/resolver_deposito()
        # ja usa quando --deposit nao e passado -- nao o CapitalBaseR do set
        # entregue (so existe pra sizing Fixed-R; a maioria dos VALIDADO_
        # sai em Percentage, ficaria vazio/nao confiavel pra isso).
        deposito = auto_manager_live.capital_minimo_classe(simbolo) or 10000.0
        print(f"  [OK] {simbolo}/{sistema}/{variante} <- {log.name} "
              f"| janela {inicio} a {fim} | deposito {deposito}")
        atualizacoes.append((simbolo, sistema, variante, parametros, inicio,
                            fim, deposito))

    print(f"\n{len(atualizacoes)} combo(s) com janela confiavel "
          f"({'aplicando' if args.aplicar else 'dry-run, nada rodado'}).")
    if not args.aplicar or not atualizacoes:
        return 0

    garantir_terminal_livre(fechar=True)
    existentes = rl.metricas_do_ledger(rl.LEDGER)
    origens = {}
    novas_linhas = []
    for simbolo, sistema, variante, parametros, inicio, fim, deposito in atualizacoes:
        chave_origem = (simbolo, sistema, variante)
        origem = origens.get(chave_origem) or base.achar_set(simbolo, sistema, variante)
        origens[chave_origem] = origem
        if origem is None:
            print(f"  [ABORTADO] {simbolo}/{sistema}/{variante}: template "
                  "de origem nao encontrado.")
            continue
        print(f"\n### rodando {simbolo}/{sistema}/{variante} ###", flush=True)
        gate_stats = rodar_combo(origem, simbolo, parametros, inicio, fim, deposito)
        print(f"    {gate_stats}", flush=True)
        if not gate_stats:
            print("    sem ALL_FORMULAS -- pulando gravacao no ledger.")
            continue
        # MERGE com o registro existente, nao substitui -- metricas_do_ledger()
        # so ve o ULTIMO registro de cada combo; escrever so os campos novos
        # apagaria expectancy_r/retencao_oos/parametros/etc. que ja estavam
        # la (achado ao revisar este script antes de rodar: quase reintroduzi
        # o mesmo tipo de perda de dado que o backfill anterior existe pra
        # evitar).
        simbolo_norm = simbolo.replace(".", "_")
        chave_ledger = (simbolo_norm, sistema, variante)
        reg = dict(existentes.get(chave_ledger, {}))
        reg.update({"simbolo": simbolo, "sistema": sistema, "variante": variante,
                   "profit_factor": gate_stats["profit_factor"],
                   "max_dd_pct": gate_stats["max_dd_pct"],
                   "sharpe": gate_stats["sharpe"],
                   "composite_score": gate_stats["composite_score"],
                   "origem_backfill_gate": "reconferido via _backfill_gate_zeus_completo.py"})
        novas_linhas.append(reg)

    if novas_linhas:
        with rl.LEDGER.open("a", encoding="utf-8") as fh:
            for reg in novas_linhas:
                fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
        print(f"\n{len(novas_linhas)} registro(s) gravado(s) em {rl.LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
