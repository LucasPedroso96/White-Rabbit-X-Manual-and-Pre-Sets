# -*- coding: utf-8 -*-
"""Testa eixos_reotimizaveis(), extraida de dentro de main() (auditoria
2026-09-04, plano de WFA de verdade) pra virar chamavel de fora sem duplicar
a regra do Estagio 2.

Existe pra travar a extracao contra regressao de comportamento: antes a
logica era `eixos_do_indicador(NUMEROS, ind)` menos os eixos de recuperacao
quando o sistema e martingale/d'Alembert, escrita inline em main(). Se a
extracao mudar esse resultado pra QUALQUER sistema/indicador, o Estagio 2 da
campanha reabriria (ou deixaria de reabrir) eixos diferentes do que reabria
antes, silenciosamente.

    python test_eixos_reotimizaveis.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import (EIXOS_RECUPERACAO, NUMEROS,
                                eixos_do_indicador, eixos_reotimizaveis)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- sistema comum (nao martingale/d'Alembert): igual a eixos_do_indicador --
# EMA_Cross (indicador 1) nao usa Slow_EMA/MACD_SMA/Stochastic* -- mesmo
# filtro condicional que eixos_do_indicador ja aplica.
esperado_ema = eixos_do_indicador(NUMEROS, "1")
checar("01_SLTP/EMA: igual a eixos_do_indicador puro (sem recuperacao)",
       eixos_reotimizaveis("01_SLTP", "1"), esperado_ema)
checar("06_REVERSAL_EXIT/Stochastic: igual a eixos_do_indicador puro",
       eixos_reotimizaveis("06_REVERSAL_EXIT", "3"),
       eixos_do_indicador(NUMEROS, "3"))

# --- martingale: MaxMartingaleSteps sai, o resto do filtro do indicador
# continua valendo -----------------------------------------------------------
base_martingale = eixos_do_indicador(NUMEROS, "5")  # RSI
esperado_martingale = [e for e in base_martingale
                       if e not in EIXOS_RECUPERACAO["09_MARTINGALE"]]
obtido_martingale = eixos_reotimizaveis("09_MARTINGALE", "5")
checar("09_MARTINGALE/RSI: MaxMartingaleSteps fora",
       "MaxMartingaleSteps" in obtido_martingale, False)
checar("09_MARTINGALE/RSI: bate com o filtro manual", obtido_martingale,
       esperado_martingale)
checar("09_MARTINGALE/RSI: eixos normais do indicador continuam",
       set(base_martingale) - {"MaxMartingaleSteps"} <= set(obtido_martingale),
       True)

# --- d'Alembert: DAlembertStep E MaxMartingaleSteps saem (os dois, ver
# EIXOS_RECUPERACAO no modulo) -----------------------------------------------
base_dalembert = eixos_do_indicador(NUMEROS, "6")  # CCI
obtido_dalembert = eixos_reotimizaveis("10_DALEMBERT", "6")
checar("10_DALEMBERT/CCI: DAlembertStep fora",
       "DAlembertStep" in obtido_dalembert, False)
checar("10_DALEMBERT/CCI: MaxMartingaleSteps tambem fora (usado pelos dois)",
       "MaxMartingaleSteps" in obtido_dalembert, False)
checar("10_DALEMBERT/CCI: bate com o filtro manual", obtido_dalembert,
       [e for e in base_dalembert
        if e not in EIXOS_RECUPERACAO["10_DALEMBERT"]])

# --- indicador None (variante ICHIMOKU): eixos_do_indicador passa tudo,
# martingale/d'Alembert ainda filtram o que corresponde ----------------------
checar("12_GRID_INVERSO/sem indicador (nao e recuperacao): passa tudo",
       eixos_reotimizaveis("12_GRID_INVERSO", None),
       eixos_do_indicador(NUMEROS, None))
checar("09_MARTINGALE/sem indicador: ainda tira MaxMartingaleSteps",
       "MaxMartingaleSteps" in eixos_reotimizaveis("09_MARTINGALE", None),
       False)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("eixos_reotimizaveis: todos os casos passaram")
