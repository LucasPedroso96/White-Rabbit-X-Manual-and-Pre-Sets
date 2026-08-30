# -*- coding: utf-8 -*-
"""Piloto de ML no 12_GRID_INVERSO/XAUUSD -- Passo 5 do plano: roda o
sistema com UsarEntradaML=true (mantendo TODOS os outros parametros
travados iguais ao campeao atual -- geometria de grid/recuperacao
inalterada, mesmo pedido do dono de "manter nossos filtros"), captura
PF/DD/Sharpe/composite_score/expectancy via ALL_FORMULAS (mesmo mecanismo
do gate ja commitado), e compara contra o campeao real via
avaliar_gate_relativo(). Uso interno, apagar depois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_sets as base
import optimize_two_stage as ots
from mt5_runner import garantir_terminal_livre

garantir_terminal_livre(fechar=True)

SISTEMA, SIMBOLO, VARIANTE = "12_GRID_INVERSO", "XAUUSD", "BUY_MULTI"
INICIO, FIM, DEPOSITO = "2025.08.25", "2026.08.25", 10000

campeao = ots.carregar_campeao_atual(SISTEMA, SIMBOLO, VARIANTE)
print(f"campeao atual: expectancy_r={campeao.get('expectancy_r')} "
      f"pf={campeao.get('profit_factor')} dd={campeao.get('max_dd_pct')} "
      f"sharpe={campeao.get('sharpe')} score={campeao.get('composite_score')}")

origem = base.achar_set(SIMBOLO, SISTEMA, VARIANTE)
trabalho = base.DADOS / "MQL5" / "Profiles" / "Tester" / "_TESTE_ML_PILOTO.set"

parametros_campeao = campeao["parametros"]
wfo = ots.janelas_wfo(INICIO, FIM)
passo = dict(wfo, **parametros_campeao, MetodoDeEntradawfo="1",
            InterfaceLanguage="1", UsarEntradaML="true")
ots.reescrever(origem, trabalho, [], passo)
faltando = ots.conferir_set(trabalho, passo)
if faltando:
    print(f"ABORTADO: set incompleto, faltando {faltando}")
    sys.exit(1)

ots.limpar_todas_formulas()
r = ots.passe_unico(trabalho, SIMBOLO, "M1", INICIO, FIM, DEPOSITO, 4)
print(f"\nresultado com UsarEntradaML=true: {r}")

stats_list = ots.carregar_todas_formulas()
stats = stats_list[-1] if stats_list else None
print(f"all_formulas: {stats}")

if stats is None:
    print("\nSEM DADO -- provavel 0 trades (modelo nunca abriu ordem) ou "
          "falha no carregamento do modelo. Ver log do MT5.")
    sys.exit(1)

gp, gl = stats.get("gross_profit"), stats.get("gross_loss")
pf = gp / abs(gl) if gp is not None and gl not in (None, 0) else None
dd = stats.get("equity_dd_rel_pct")
sharpe = stats.get("sharpe")
trades = stats.get("trades")
profit = stats.get("profit")
score = (ots.composite_score(profit, DEPOSITO, pf, dd, trades)
        if None not in (pf, dd, trades, profit) else None)
desafiante = {"profit_factor": pf, "max_dd_pct": dd, "sharpe": sharpe,
             "composite_score": score, "trades": trades,
             "expectancy_r": r["expectancy"]}
print(f"\ndesafiante (ML): {desafiante}")

print("\n===== avaliar_gate_relativo(campeao, desafiante_ML) =====")
ok, motivos = ots.avaliar_gate_relativo(campeao, desafiante)
for m in motivos:
    print(" ", m)
print("aprovado =", ok)
