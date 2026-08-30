# -*- coding: utf-8 -*-
"""Reconstroi o passe combinado (Estagio 4, mesmo formato que
torneio_retencao([None], ...) roda por dentro) para as DUAS formulas reais
que a confirmacao de 27/08 aprovou pro 12_GRID_INVERSO/XAUUSD -- formula 7
(ProfitPerTradeAdjustedByDD, perdeu) e formula 13 (LevainCompositeScore,
virou campea) -- desta vez capturando PF/DD/Sharpe/composite_score DE
VERDADE via ALL_FORMULAS, nao so o expectancy_r que ja tinha sido testado.
Confirma se avaliar_gate_relativo() reprova a 7 com a lista COMPLETA de
motivos (nao so 1 eixo). Uso interno, apagar depois."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre

garantir_terminal_livre(fechar=True)

SISTEMA, SIMBOLO, VARIANTE = "12_GRID_INVERSO", "XAUUSD", "BUY_MULTI"
INICIO, FIM, DEPOSITO = "2025.08.25", "2026.08.25", 10000

origem = base.achar_set(SIMBOLO, SISTEMA, VARIANTE)
trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_TESTE_GATE_COMPLETO.set"

FORMULAS = {
    7: "sweep_12_GRID_INVERSO_XAUUSD_07_ProfitPerTradeAdjustedByDD.log",
    13: "sweep_12_GRID_INVERSO_XAUUSD_13_LevainCompositeScore.log",
}


def carregar_parametros(caminho_log: str) -> dict:
    texto = Path(caminho_log).read_text(encoding="utf-8", errors="replace")
    for linha in reversed(texto.splitlines()):
        if linha.startswith("{"):
            return json.loads(linha)["parametros"]
    raise RuntimeError(f"sem JSON final em {caminho_log}")


def rodar_formula(numero: int) -> dict:
    parametros = carregar_parametros(FORMULAS[numero])
    wfo = ots.janelas_wfo(INICIO, FIM)
    passo = dict(wfo, **parametros, MetodoDeEntradawfo="1",
                InterfaceLanguage="1")
    ots.reescrever(origem, trabalho, [], passo)
    ots.limpar_todas_formulas()
    r = ots.passe_unico(trabalho, SIMBOLO, "M1", INICIO, FIM, DEPOSITO, 4)
    stats_list = ots.carregar_todas_formulas()
    stats = stats_list[-1] if stats_list else None
    print(f"\n--- formula {numero}: r={r}")
    print(f"--- formula {numero}: all_formulas={stats}")
    if stats is None:
        return {}
    gp, gl = stats.get("gross_profit"), stats.get("gross_loss")
    pf = gp / abs(gl) if gp is not None and gl not in (None, 0) else None
    dd = stats.get("equity_dd_rel_pct")
    sharpe = stats.get("sharpe")
    trades = stats.get("trades")
    profit = stats.get("profit")
    score = (ots.composite_score(profit, DEPOSITO, pf, dd, trades)
            if None not in (pf, dd, trades, profit) else None)
    return {"profit_factor": pf, "max_dd_pct": dd, "sharpe": sharpe,
           "composite_score": score, "trades": trades,
           "expectancy_r": r["expectancy"]}


dados_13 = rodar_formula(13)
dados_7 = rodar_formula(7)

print("\n===== RESUMO =====")
print("formula 13 (campea):", dados_13)
print("formula 7 (desafiante):", dados_7)

print("\n===== avaliar_gate_relativo(campeao=13, desafiante=7) =====")
ok, motivos = ots.avaliar_gate_relativo(dados_13, dados_7)
for m in motivos:
    print(" ", m)
print("aprovado =", ok)
