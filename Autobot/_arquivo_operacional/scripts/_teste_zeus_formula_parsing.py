# -*- coding: utf-8 -*-
"""Confere o parsing de ler_todas_formulas() contra uma linha ALL_FORMULAS
sintetica mas no formato EXATO que o .mq5 grava agora (com ZeusScore no
fim) -- sem MT5, so pra nao concorrer com a campanha rodando no terminal
agora. Uso interno, apagar depois."""
import optimize_two_stage as ots

linha_real = (
    "ALL_FORMULAS Profit=11087.070000 Trades=192 GrossProfit=17571.840000 "
    "GrossLoss=-6484.770000 EquityDDPercent=9.884750 Sharpe=6.019977 "
    "InitialDeposit=10000.00 | GridSurvival=2.057289 "
    "ProfitFormula=11087.070000 ProfitWinTradeDD=0.397245 "
    "EffRelDeposit=54.752487 AdjEffGrid=3004.866534 "
    "ProfitRelDDDeposit=33.378883 PPTDD=0.011603 SharpeAdjDD=162.810622 "
    "PessimisticProfit=47.918117 ResilienceDD=5279.403437 "
    "ReturnUniformity=2617.825278 SystemRobustness=2857.526285 "
    "LevainComposite=0.966133 SomaR=110.870700 EquityDDRelPercent=9.884750 "
    "ZeusScore=201.057288\r\n"
)

resultado = ots.ler_todas_formulas(linha_real)
print("resultado:", resultado)
assert len(resultado) == 1, f"esperava 1 linha parseada, veio {len(resultado)}"
d = resultado[0]
assert d["zeus_score"] == 201.057288, d["zeus_score"]
assert d["soma_r"] == 110.8707, d["soma_r"]
assert d["equity_dd_rel_pct"] == 9.88475, d["equity_dd_rel_pct"]
print("\nOK: zeus_score/soma_r/equity_dd_rel_pct parseados corretamente.")

print("\ncampo da formula 15:", ots._CAMPO_POR_INDICE_FORMULA[15])
assert ots._CAMPO_POR_INDICE_FORMULA[15] == "zeus_score"
print("OK: indice 15 mapeia pra zeus_score.")
