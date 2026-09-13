# -*- coding: utf-8 -*-
"""Testa a parte PURA do adaptador Optuna do Estagio 2 -- Fase 3 da mudanca
de direcao (2026-09-13): `_formatar_valor_eixo()` (tipagem inteiro/float do
valor sugerido) e `_linhas_do_optuna()` (monta cab/linhas no formato que
escolher_candidatos()/torneio_retencao() esperam, sem alterar nenhuma
delas). `otimizar_estagio2_optuna()` em si RODA passes reais e so e
validavel num piloto A/B ao vivo, deliberadamente fora deste arquivo.

    python test_estagio2_optuna.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import _formatar_valor_eixo, _linhas_do_optuna

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- _formatar_valor_eixo: tipagem por faixa, nao por valor sugerido -------
checar("faixa inteira (sem ponto) -> valor inteiro, mesmo com float de entrada",
      _formatar_valor_eixo(7.0, "1", "10"), "7")
checar("faixa inteira arredonda pro inteiro mais proximo",
      _formatar_valor_eixo(7.6, "1", "10"), "8")
checar("faixa com ponto decimal no start -> mantem float",
      _formatar_valor_eixo(7.5, "1.0", "10"), "7.5")
checar("faixa com ponto decimal no stop -> mantem float",
      _formatar_valor_eixo(7.5, "1", "10.0"), "7.5")
checar("valor negativo em faixa inteira",
      _formatar_valor_eixo(-3.2, "-10", "10"), "-3")

# --- _linhas_do_optuna: cab sempre eixos + Profit/Trades, nessa ordem ------
eixos = ["Fast_EMA", "Slow_EMA"]
resultados = {
    0: ({"Fast_EMA": "12", "Slow_EMA": "26"}, {"saldo": 1200.0, "trades": 50}),
    1: ({"Fast_EMA": "8", "Slow_EMA": "21"}, {"saldo": 900.0, "trades": 30}),
}
cab, linhas = _linhas_do_optuna(eixos, resultados, deposito=1000)
checar("cab = eixos + Profit + Trades, nessa ordem",
      cab, ["Fast_EMA", "Slow_EMA", "Profit", "Trades"])
checar("numero de linhas bate com numero de trials medidos",
      len(linhas), 2)
checar("linha 0: valores dos eixos + Profit (saldo-deposito) + Trades",
      linhas[0], ["12", "26", "200.0", "50"])
checar("linha 1: mesma conta pro segundo trial",
      linhas[1], ["8", "21", "-100.0", "30"])

# --- trial sem saldo medido (timeout/erro): Profit vira 0.0, nao quebra ----
resultados_com_falha = {
    0: ({"Fast_EMA": "12", "Slow_EMA": "26"}, {"saldo": None, "trades": None}),
}
_, linhas_falha = _linhas_do_optuna(eixos, resultados_com_falha, deposito=1000)
checar("trial sem saldo medido: Profit 0.0 e Trades 0, sem excecao",
      linhas_falha[0], ["12", "26", "0.0", "0"])

# --- sem nenhum resultado: linhas vazia, cab ainda correto ------------------
cab_vazio, linhas_vazias = _linhas_do_optuna(eixos, {}, deposito=1000)
checar("sem resultados: cab ainda correto", cab_vazio,
      ["Fast_EMA", "Slow_EMA", "Profit", "Trades"])
checar("sem resultados: linhas vazia", linhas_vazias, [])

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("estagio2_optuna (partes puras): todos os casos passaram")
