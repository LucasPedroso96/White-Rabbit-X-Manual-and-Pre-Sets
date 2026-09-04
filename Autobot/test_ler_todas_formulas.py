# -*- coding: utf-8 -*-
"""Testa o parser das 14 formulas (ALL_FORMULAS) e o casamento com o
relatorio do genetico, sem precisar do MT5.

Existe pelo mesmo motivo dos outros test_*: o formato da linha ALL_FORMULAS
(optimize_two_stage.py) tem que bater EXATO com o PrintFormat da EA (.mq5,
OnTester) -- um typo de qualquer lado quebra silenciosamente (a lista fica
vazia, nao um erro visivel), e so apareceria depois de rodar o circuito
inteiro contra o log real.

    python test_ler_todas_formulas.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import casar_formula_com_relatorio, ler_todas_formulas

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- uma linha real (mesmo formato do PrintFormat da EA) --------------------
LINHA = (
    "ALL_FORMULAS Profit=607.140000 Trades=42 GrossProfit=1200.500000 "
    "GrossLoss=-593.360000 EquityDDPercent=12.340000 Sharpe=1.230000 "
    "InitialDeposit=500.00 | GridSurvival=3.456789 ProfitFormula=607.140000 "
    "ProfitWinTradeDD=250.120000 EffRelDeposit=1.214280 AdjEffGrid=15.670000 "
    "ProfitRelDDDeposit=45.230000 PPTDD=0.028900 SharpeAdjDD=0.099700 "
    "PessimisticProfit=10.450000 ResilienceDD=0.876500 "
    "ReturnUniformity=0.654300 SystemRobustness=0.789000 "
    # EquityDDRelPercent/ZeusScore entraram no FileWrite da EA em 2026-08-30 e
    # viraram obrigatorios em _PADRAO_ALL_FORMULAS no mesmo dia, mas esta
    # amostra ficou parada em SomaR -- o regex deixou de casar e o teste
    # quebrou com IndexError (formulas[0] em lista vazia) em vez de reportar a
    # divergencia. E exatamente a drift que o arquivo existe pra pegar; ele so
    # nao estava sendo rodado.
    "LevainComposite=0.612000 SomaR=0.000000 "
    "EquityDDRelPercent=9.870000 ZeusScore=41.230000"
)
formulas = ler_todas_formulas(LINHA)
checar("uma linha: quantidade", len(formulas), 1)
checar("uma linha: profit", formulas[0]["profit"], 607.14)
checar("uma linha: trades (inteiro)", formulas[0]["trades"], 42)
checar("uma linha: grid_survival", formulas[0]["grid_survival"], 3.456789)
checar("uma linha: soma_r zero (fora de Fixed-R)", formulas[0]["soma_r"], 0.0)
checar("uma linha: gross_loss negativo preservado",
       formulas[0]["gross_loss"], -593.36)

# --- multiplas linhas: ordem de execucao, nao de resultado -------------------
LINHA2 = LINHA.replace("Profit=607.140000", "Profit=112.500000").replace(
    "Trades=42", "Trades=18")
formulas = ler_todas_formulas(f"lixo antes\n{LINHA}\nlixo no meio\n{LINHA2}\n")
checar("duas linhas: quantidade", len(formulas), 2)
checar("duas linhas: ordem preservada", [f["trades"] for f in formulas],
       [42, 18])

# --- log sem nenhuma linha ALL_FORMULAS: lista vazia, sem excecao ------------
checar("log vazio", ler_todas_formulas("nada aqui\nautomatical testing finished"), [])

# --- casamento com o relatorio: por fingerprint, nao por posicao ------------
CAB = ["Pass", "Result", "Profit", "Profit Factor", "Trades", "Equity DD %"]
# O relatorio chega ORDENADO por Result (melhor primeiro) -- linha 0 e o
# passe de 18 trades (Profit 112.5), linha 1 e o de 42 (Profit 607.14):
# ordem INVERSA da execucao (formulas[0]=607.14/42, formulas[1]=112.5/18).
LINHAS_RELATORIO = [
    ["7", "9.80", "112.50", "1.90", "18", "12.34"],
    ["3", "8.10", "607.14", "2.20", "42", "12.34"],
]
casados = casar_formula_com_relatorio(CAB, LINHAS_RELATORIO, formulas)
checar("casamento: linha 0 do relatorio (18 trades) pega formulas[1]",
       casados[0]["trades"], 18)
checar("casamento: linha 1 do relatorio (42 trades) pega formulas[0]",
       casados[1]["trades"], 42)
checar("casamento: grid_survival da linha certa",
       casados[1]["grid_survival"], 3.456789)

# --- casamento sem coluna Trades/Profit: dict vazio, sem excecao ------------
checar("casamento sem colunas", casar_formula_com_relatorio(
    ["Pass", "Result"], [["1", "5"]], formulas), {})

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("ler_todas_formulas / casar_formula_com_relatorio: todos os casos passaram")
