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

CONTRATO MUDOU (dono, 2026-09-08, generalizacao do booster de recuperacao):
a exclusao de MaxMartingaleSteps/DAlembertStep e INCONDICIONAL agora, pra
QUALQUER sistema -- nao so 09_MARTINGALE/10_DALEMBERT. Motivo: com o booster,
os 7 sistemas em generate_system_sets.SISTEMAS_RECUPERACAO_OPCIONAL tambem
ganharam faixa REAL pra estes dois eixos no .set (antes eram fixos, sem
faixa, entao ficavam inertes por construcao mesmo sem filtro aqui). Sem a
exclusao incondicional, uma corrida NORMAL (sem --recuperacao) desses 7
sistemas reabriria dois eixos mortos no genetico (RecoveryMode fica em "0"
o combo inteiro nos Estagios 1/2, pra todo mundo) -- diluicao pura, o mesmo
problema que Profile.desativar_inertes() existe pra evitar do lado do
gerador.

    python test_eixos_reotimizaveis.py
"""
from __future__ import annotations

import sys

from generate_system_sets import SISTEMAS_RECUPERACAO_OPCIONAL
from optimize_two_stage import (EIXOS_RECUPERACAO, EIXOS_RECUPERACAO_TODOS,
                                NUMEROS, SISTEMAS_RECUPERACAO_ELEGIVEIS,
                                eixos_do_indicador, eixos_reotimizaveis,
                                tipo_de_recuperacao)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- exclusao incondicional: MaxMartingaleSteps/DAlembertStep somem pra
# QUALQUER sistema, boostavel ou nao (RecoveryMode fica em "0" nos Estagios
# 1/2 sempre) -----------------------------------------------------------------
checar("EIXOS_RECUPERACAO_TODOS e a uniao dos dois tipos",
       set(EIXOS_RECUPERACAO_TODOS), {"MaxMartingaleSteps", "DAlembertStep"})

esperado_ema = [e for e in eixos_do_indicador(NUMEROS, "1")
                if e not in EIXOS_RECUPERACAO_TODOS]
checar("01_SLTP/EMA: eixos_do_indicador menos a uniao de recuperacao",
       eixos_reotimizaveis("01_SLTP", "1"), esperado_ema)
checar("01_SLTP/EMA: MaxMartingaleSteps fora mesmo sem ser 09/10",
       "MaxMartingaleSteps" in eixos_reotimizaveis("01_SLTP", "1"), False)
checar("01_SLTP/EMA: DAlembertStep fora mesmo sem ser 09/10",
       "DAlembertStep" in eixos_reotimizaveis("01_SLTP", "1"), False)
checar("06_REVERSAL_EXIT/Stochastic: mesma exclusao incondicional",
       eixos_reotimizaveis("06_REVERSAL_EXIT", "3"),
       [e for e in eixos_do_indicador(NUMEROS, "3")
        if e not in EIXOS_RECUPERACAO_TODOS])

# --- martingale/d'Alembert (09/10 puros): mesmo resultado de sempre, agora
# via exclusao incondicional em vez de checar identidade do sistema ----------
base_martingale = eixos_do_indicador(NUMEROS, "5")  # RSI
obtido_martingale = eixos_reotimizaveis("09_MARTINGALE", "5")
checar("09_MARTINGALE/RSI: MaxMartingaleSteps fora",
       "MaxMartingaleSteps" in obtido_martingale, False)
checar("09_MARTINGALE/RSI: eixos normais do indicador continuam",
       set(base_martingale) - set(EIXOS_RECUPERACAO_TODOS) <= set(obtido_martingale),
       True)

base_dalembert = eixos_do_indicador(NUMEROS, "6")  # CCI
obtido_dalembert = eixos_reotimizaveis("10_DALEMBERT", "6")
checar("10_DALEMBERT/CCI: DAlembertStep fora",
       "DAlembertStep" in obtido_dalembert, False)
checar("10_DALEMBERT/CCI: MaxMartingaleSteps tambem fora (usado pelos dois)",
       "MaxMartingaleSteps" in obtido_dalembert, False)

# --- indicador None (variante ICHIMOKU): eixos_do_indicador passa tudo menos
# a uniao de recuperacao, pra qualquer sistema --------------------------------
checar("12_GRID_INVERSO/sem indicador: exclusao incondicional tambem vale",
       eixos_reotimizaveis("12_GRID_INVERSO", None),
       [e for e in eixos_do_indicador(NUMEROS, None)
        if e not in EIXOS_RECUPERACAO_TODOS])

# --- booster generalizado (dono, 2026-09-08): quem pode pedir --recuperacao
# explicito, e como tipo_de_recuperacao() resolve o pedido -------------------
checar("01_SLTP e boostavel", "01_SLTP" in SISTEMAS_RECUPERACAO_OPCIONAL, True)
checar("07_GRID_SEPARATE NAO e boostavel (cesta ja e recuperacao)",
       "07_GRID_SEPARATE" in SISTEMAS_RECUPERACAO_OPCIONAL, False)
checar("12_GRID_INVERSO NAO e boostavel", "12_GRID_INVERSO" in
       SISTEMAS_RECUPERACAO_OPCIONAL, False)
checar("07_GRID_SEPARATE fica de fora de SISTEMAS_RECUPERACAO_ELEGIVEIS",
       "07_GRID_SEPARATE" in SISTEMAS_RECUPERACAO_ELEGIVEIS, False)
checar("01_SLTP entra em SISTEMAS_RECUPERACAO_ELEGIVEIS",
       "01_SLTP" in SISTEMAS_RECUPERACAO_ELEGIVEIS, True)

checar("tipo_de_recuperacao: sem pedido, 01_SLTP nao vira recuperacao",
       tipo_de_recuperacao("01_SLTP", None), None)
checar("tipo_de_recuperacao: pedido explicito vence pra sistema comum",
       tipo_de_recuperacao("01_SLTP", "martingale"), "martingale")
checar("tipo_de_recuperacao: 'nenhuma' desliga ate a identidade do 09",
       tipo_de_recuperacao("09_MARTINGALE", "nenhuma"), None)
checar("tipo_de_recuperacao: sem pedido, 09_MARTINGALE continua por identidade",
       tipo_de_recuperacao("09_MARTINGALE", None), "martingale")
checar("EIXOS_RECUPERACAO (compat, por sistema) ainda serve 09/10",
       EIXOS_RECUPERACAO["10_DALEMBERT"], ["DAlembertStep", "MaxMartingaleSteps"])

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("eixos_reotimizaveis: todos os casos passaram")
