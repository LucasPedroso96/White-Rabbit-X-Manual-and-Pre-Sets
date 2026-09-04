# -*- coding: utf-8 -*-
"""Testa o dimensionamento das janelas de WFO.

Existe por causa da auditoria de 2026-09-03: a formula antiga
(`bloco = max(60, dias // ciclos_alvo)`, pisos absolutos de 30/15) foi
calibrada pra corridas multi-ano e DEGENERAVA em silencio na janela de 92
dias do sweep de formulas -- 1,5 ciclo, uma unica janela OOS de 15 dias, e um
segundo OOS de UM dia (sabado) que a EA nunca conseguia casar com deal
nenhum. Nada no codigo reclamava; so aparecia lendo o log do tester.

Estes casos travam a propriedade que importa: quantos ciclos COMPLETOS a
janela comporta. Rodam em milissegundos, sem MT5.

    python test_dimensionar_wfo.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import BLOCO_MINIMO_WFO, dimensionar_wfo, janelas_wfo

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def checar_que(rotulo: str, condicao: bool) -> None:
    if not condicao:
        FALHAS.append(rotulo)


# --- a regressao concreta: a janela do sweep de formulas --------------------
# 2026.05.22 -> 2026.08.22 = 92 dias. A formula antiga dava 1,5 ciclo.
ciclos, is_d, oos_d = dimensionar_wfo(92)
checar("sweep 92d: ciclos completos", ciclos, 3)
checar("sweep 92d: dias de In-Sample", is_d, 22)
checar("sweep 92d: dias de Out-of-Sample", oos_d, 8)
checar_que("sweep 92d: o periodo comporta os 3 ciclos inteiros",
           ciclos * (is_d + oos_d) <= 92)
checar_que("sweep 92d: mais de um ciclo (senao nao ha desvio-padrao)",
           ciclos > 1)
# O ganho real: dias OOS totais, que e o tamanho da amostra da retencao.
checar_que("sweep 92d: mais dias fora da amostra que os 15 de antes",
           ciclos * oos_d > 15)

# --- a proporcao IS:OOS fica na faixa usual (2:1 a 4:1) --------------------
for dias in (92, 180, 365, 730, 1085):
    c, i, o = dimensionar_wfo(dias)
    checar_que(f"{dias}d: proporcao IS:OOS entre 2:1 e 4:1 (deu {i}:{o})",
               2.0 <= i / o <= 4.0)
    checar_que(f"{dias}d: os ciclos cabem no periodo", c * (i + o) <= dias)
    checar_que(f"{dias}d: nunca passa de ciclos_alvo", c <= 6)

# --- corridas multi-ano continuam com 6 ciclos, como antes -----------------
checar("3 anos: ciclos", dimensionar_wfo(1085)[0], 6)
checar_que("3 anos: In-Sample generoso", dimensionar_wfo(1085)[1] >= 120)

# --- janelas curtas demais: 1 ciclo, sem inventar numero --------------------
c, i, o = dimensionar_wfo(BLOCO_MINIMO_WFO - 1)
checar("periodo menor que o bloco minimo: 1 ciclo", c, 1)
checar_que("periodo curtissimo: ainda devolve dias positivos", i > 0 and o > 0)
checar("periodo de 1 dia nao estoura", dimensionar_wfo(1)[0], 1)
checar("periodo de 0 dias nao divide por zero", dimensionar_wfo(0)[0], 1)

# --- janelas_wfo() continua entregando o dict que vai pro .set --------------
w = janelas_wfo("2026.05.22", "2026.08.22")
checar("janelas_wfo: WFO ligado", w["AtivarWFO"], "true")
checar("janelas_wfo: busca so ve In-Sample", w["MetodoDeEntradawfo"], "0")
checar("janelas_wfo: data final casada com o .ini", w["input_end_date"],
       "2026.08.22")
checar("janelas_wfo: janela custom", w["wfo_windowSize"], "-1")
checar("janelas_wfo: IS bate com dimensionar_wfo",
       w["wfo_customWindowSizeDays"], str(is_d))
# Negativo = dias fixos (a EA converte com -wfo_customStepSizePercent).
checar("janelas_wfo: OOS negativo, em dias fixos",
       w["wfo_customStepSizePercent"], str(-oos_d))
checar_que("janelas_wfo: OOS realmente negativo",
           int(w["wfo_customStepSizePercent"]) < 0)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("dimensionar_wfo / janelas_wfo: todos os casos passaram")
