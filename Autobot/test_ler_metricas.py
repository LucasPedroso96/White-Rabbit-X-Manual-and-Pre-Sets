# -*- coding: utf-8 -*-
"""Testa a leitura do log sem precisar do MT5.

Existe porque dois defeitos de UMA linha em ler_metricas() so apareceram depois
dos ~25 min de otimizacao que rodam antes dela -- e a segunda vez derrubou a
corrida inteira no ultimo passo. O parsing nao depende do terminal, entao nao ha
motivo para so descobrir que ele quebrou depois de meia hora.

    python test_ler_metricas.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import wrx_paths
from optimize_two_stage import ler_metricas

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- corrida completa, como a EA imprime ------------------------------------
COMPLETO = """
2026.07.20 23:59:58   ==================== R METRICS ====================
2026.07.20 23:59:58   Fixed-R mode: 1R = 5.00 USD | base capital = 500.00
2026.07.20 23:59:58   Trades: 410 | Total R: +64.20 | Average R (expectancy): +0.157
2026.07.20 23:59:58   Win rate: 36.3% | Payoff: 2.30R | Largest gain: +3.16R
final balance 827.92 USD
2026.07.20 23:59:58   Out-of-Sample Retention: 41.50% (out-of-sample daily ...)
automatical testing finished
"""
m = ler_metricas(COMPLETO)
checar("saldo", m["saldo"], 827.92)
checar("trades", m["trades"], 410)
checar("total_r", m["total_r"], 64.20)
checar("expectancy", m["expectancy"], 0.157)
checar("win_rate", m["win_rate"], 36.3)
checar("retencao", m["retencao"], 41.5)

# --- expectancy negativa: o sinal de menos tem que sobreviver ---------------
NEGATIVO = COMPLETO.replace("Average R (expectancy): +0.157",
                            "Average R (expectancy): -0.088")
checar("expectancy negativa", ler_metricas(NEGATIVO)["expectancy"], -0.088)

# --- retencao negativa: OOS perdeu dinheiro, e um resultado valido ----------
NEG_RET = COMPLETO.replace("Retention: 41.50%", "Retention: -12.75%")
checar("retencao negativa", ler_metricas(NEG_RET)["retencao"], -12.75)

# --- retencao "not applicable": IS sem lucro -> None COM o motivo da EA -----
# Log real do CHFJPY/03_TRAIL_ONLY em % (2026-09-20): sem o motivo, o gate da
# prova em % reprovava com a mensagem errada ("nao sobreviveu aos juros
# compostos") quando a causa era o In-Sample negativo.
SEM_RETENCAO = COMPLETO.replace(
    "Out-of-Sample Retention: 41.50% (out-of-sample daily ...)",
    "Out-of-Sample Retention: not applicable - In-Sample was not profitable "
    "(average daily -0.76). The strategy failed in-sample; there is nothing "
    "to retain.")
m = ler_metricas(SEM_RETENCAO)
checar("sem retencao: valor", m["retencao"], None)
checar("sem retencao: motivo lido", "In-Sample was not profitable" in (m["retencao_motivo"] or ""), True)
checar("com retencao: sem motivo", ler_metricas(COMPLETO)["retencao_motivo"], None)

# --- In-Sample sem lucro: a EA escreve texto, nao numero --------------------
# None e 0.0 precisam continuar distintos: "nao ha o que reter" nao e "reteve
# zero". Tratar os dois como 0.0 foi o que fez a retencao parecer medida.
NAO_APLICA = COMPLETO.replace(
    "Out-of-Sample Retention: 41.50% (out-of-sample daily ...)",
    "Out-of-Sample Retention: not applicable - In-Sample was not profitable")
checar("retencao n/a", ler_metricas(NAO_APLICA)["retencao"], None)

# --- modo In-Sample: retencao 0.00% e um numero, nao ausencia ---------------
ZERO = COMPLETO.replace("Retention: 41.50%", "Retention: 0.00%")
checar("retencao zero", ler_metricas(ZERO)["retencao"], 0.0)

# --- OOS sem NENHUM trade (2026-09-25): 0.00% com lucro OOS 0.00 exato e
# ausencia de medida, nao "reteve zero" -- era o sintoma do bloqueio de
# entrada no OOS que vazou pro modo IS+OOS.
SEM_OOS = ZERO + ("\n2026.09.23 23:14:59   Final accumulated In-Sample profit: 371.16"
                  "\n2026.09.23 23:14:59   Final accumulated Out-Sample profit: 0.00")
m_sem = ler_metricas(SEM_OOS)
checar("OOS sem trade: retencao vira None", m_sem["retencao"], None)
checar("OOS sem trade: motivo explicado",
       "sem trade fora da amostra" in (m_sem["retencao_motivo"] or ""), True)
COM_OOS = ZERO + "\n2026.09.23 23:14:59   Final accumulated Out-Sample profit: -3.20"
checar("OOS operou e deu ~0%: continua numero", ler_metricas(COM_OOS)["retencao"], 0.0)

# --- denominador minusculo (2026-09-26, EURUSD/06 SELL: IS 2.63, 14442%) ---
MINUSCULO = (COMPLETO.replace("Retention: 41.50%", "Retention: 14442.32%")
             + "\n2026.09.24 23:54:44   Initial deposit recorded: 1000.00"
             "\n2026.09.24 23:54:44   Final accumulated In-Sample profit: 2.63"
             "\n2026.09.24 23:54:44   Final accumulated Out-Sample profit: 125.68")
m_min = ler_metricas(MINUSCULO)
checar("IS < 1% do deposito: retencao vira None", m_min["retencao"], None)
checar("IS < 1% do deposito: motivo explicado",
       "quase sem lucro" in (m_min["retencao_motivo"] or ""), True)
SAUDAVEL = MINUSCULO.replace("In-Sample profit: 2.63", "In-Sample profit: 371.16")
checar("IS com lucro de verdade: retencao continua numero",
       ler_metricas(SAUDAVEL)["retencao"], 14442.32)

# --- retencao pelo metodo antigo (janela de SAIDA), impressa ao lado ---------
AB = COMPLETO + ("\n2026.09.26 09:10:00   Retention (metodo antigo, lucro na "
                 "janela de SAIDA): 88.10% -- a oficial acima conta pela janela "
                 "de ABERTURA da posicao")
m_ab = ler_metricas(AB)
checar("A/B: retencao oficial (abertura) intacta", m_ab["retencao"], 41.5)
checar("A/B: metodo antigo lido", m_ab["retencao_metodo_antigo"], 88.1)
checar("A/B: .ex5 antigo sem a linha -> None",
       ler_metricas(COMPLETO)["retencao_metodo_antigo"], None)

# --- benchmark buy&hold impresso pela EA (2026-09-26) -----------------------
from optimize_two_stage import comparar_buy_and_hold

BH = COMPLETO + ("\n2026.09.23 23:14:59   BENCHMARK buy&hold: inicial 1900.12345 "
                 "| final 4332.00000 | retorno 127.98% | maxDD comprado 14.20% "
                 "| maxDD vendido 128.50%")
m_bh = ler_metricas(BH)
checar("buy&hold: retorno", m_bh["bh_retorno_pct"], 127.98)
checar("buy&hold: DD comprado/vendido",
       (m_bh["bh_dd_compra_pct"], m_bh["bh_dd_venda_pct"]), (14.2, 128.5))
checar("buy&hold ausente (.ex5 antigo) -> None",
       ler_metricas(COMPLETO)["bh_retorno_pct"], None)
cmp_buy = comparar_buy_and_hold({"profit": 12588.0, "max_dd_pct": 12.3,
                                 "bh_retorno_pct": 127.98,
                                 "bh_dd_compra_pct": 14.2,
                                 "bh_dd_venda_pct": 128.5}, 10000, "BUY_MULTI")
checar("comparacao BUY: contra ficar comprado", cmp_buy["lado"], "comprado")
checar("comparacao BUY: retorno/DD estrategia x ativo",
       (cmp_buy["mar_estrategia"], cmp_buy["mar_ativo"]), (10.234, 9.013))
cmp_sell = comparar_buy_and_hold({"profit": 500.0, "max_dd_pct": 10.0,
                                  "bh_retorno_pct": 20.0, "bh_dd_compra_pct": 5.0,
                                  "bh_dd_venda_pct": 25.0}, 2500, "SELL_MULTI")
checar("comparacao SELL: ativo vendido perdeu o que o ativo subiu",
       cmp_sell["ativo_retorno_pct"], -20.0)
checar("sem benchmark no passe -> None",
       comparar_buy_and_hold({"profit": 1.0}, 1000, "BUY_MULTI"), None)

# --- FixedLot/Monetario: sem bloco R METRICS, so "Total Trades" incondicional
# (dono, 2026-09-14: 07_GRID_SEPARATE com sizing default sempre lia
# trades=None mesmo operando de verdade, porque o bloco R METRICS so
# imprime com RiscoRFixo/Porcentagem ativos). total_r/expectancy continuam
# None de proposito -- sem sizing baseado em R, esses numeros nao existem.
SEM_R_METRICS = """
2026.09.14 01:12:00   Total Trades: 27
final balance 1678.00 USD
automatical testing finished
"""
m2 = ler_metricas(SEM_R_METRICS)
checar("sem R METRICS: trades vem do fallback incondicional", m2["trades"], 27)
checar("sem R METRICS: saldo continua lido normalmente", m2["saldo"], 1678.00)
checar("sem R METRICS: total_r continua None (nao existe sem sizing em R)",
      m2["total_r"], None)
checar("sem R METRICS: expectancy continua None (nao existe sem sizing em R)",
      m2["expectancy"], None)

# --- bloco R METRICS presente: continua vencendo sobre o fallback ----------
# Corrida com RiscoRFixo/Porcentagem imprime OS DOIS ("Total Trades" e o
# bloco R) -- o valor mais completo (com Total R/expectancy) tem que
# prevalecer, nao o fallback.
COM_OS_DOIS = COMPLETO.replace(
    "==================== R METRICS ====================",
    "Total Trades: 999\n==================== R METRICS ====================")
checar("com os dois blocos: bloco R METRICS vence (nao o fallback)",
      ler_metricas(COM_OS_DOIS)["trades"], 410)

# --- log vazio: tudo None, nada de excecao ---------------------------------
vazio = ler_metricas("")
checar("vazio/saldo", vazio["saldo"], None)
checar("vazio/trades", vazio["trades"], None)
checar("vazio/abortos", vazio["abortos"], 0)

# --- log CUMULATIVO: tem que pegar a corrida mais recente -------------------
ANTIGO = COMPLETO.replace("Trades: 410", "Trades: 184").replace(
    "final balance 827.92", "final balance 591.63")
checar("cumulativo/trades", ler_metricas(ANTIGO + COMPLETO)["trades"], 410)
checar("cumulativo/saldo", ler_metricas(ANTIGO + COMPLETO)["saldo"], 827.92)

# --- e contra um log REAL, se houver um por perto ---------------------------
try:
    LOGS = wrx_paths.data_dir() / "Tester" / "logs"
except SystemExit:
    LOGS = None
reais = sorted(LOGS.glob("*.log"), key=lambda p: p.stat().st_mtime) \
    if LOGS and LOGS.is_dir() else []
if reais:
    texto = reais[-1].read_text(encoding="utf-16-le", errors="replace")
    r = ler_metricas(texto)
    print(f"log real ({reais[-1].name}): trades={r['trades']} "
          f"saldo={r['saldo']} expectancy={r['expectancy']} "
          f"retencao={r['retencao']}")
    if r["trades"] is None:
        FALHAS.append("log real: nao achou o bloco R METRICS")

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("ler_metricas: todos os casos passaram")
