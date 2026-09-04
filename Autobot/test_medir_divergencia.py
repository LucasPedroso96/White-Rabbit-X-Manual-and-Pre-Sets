# -*- coding: utf-8 -*-
"""Testa o gate de divergencia OHLC vs tick real.

Existe por causa da auditoria de 2026-09-03: nos 5 sistemas do Estagio 3.5 a
divergencia saia 0.0% POR CONSTRUCAO (tick real contra tick real) e o log
afirmava "OK divergencia (0.0%): o lucro do OHLC e real" embaixo de uma
promessa de OHLC que nao tinha se sustentado. Os casos abaixo sao numeros
REAIS lidos dos logs de sweep -- se alguem reintroduzir a base errada, eles
quebram.

    python test_medir_divergencia.py
"""
from __future__ import annotations

import sys

from optimize_two_stage import medir_divergencia, veredito

FALHAS: list[str] = []


def perto(a, b, tol=0.05) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def checar_perto(rotulo: str, obtido, esperado) -> None:
    if not perto(obtido, esperado):
        FALHAS.append(f"{rotulo}: esperado ~{esperado!r}, obtido {obtido!r}")


# --- caso 1: sistema SEM Estagio 3.5 -- base e o lucro do OHLC, como sempre -
div, base, motivo = medir_divergencia(
    lucro_real=1200.0, lucro_ohlc=1000.0, lucro_ohlc_pre_geometria=None,
    geometria_refeita_tick_real=False, deposito=500)
checar_perto("sem 3.5: divergencia", div, 20.0)
checar("sem 3.5: base e o proprio lucro OHLC", base, 1000.0)
checar("sem 3.5: sem motivo de falha", motivo, "")

# --- caso 2: a REGRESSAO -- 12_GRID_INVERSO/XAUUSD, formula 11 -------------
# Do log real: o Estagio 3.5 achou 1648.73 em tick real, a conferencia deu os
# mesmos 1648.73 (0.0%), e o memo registrava que o OHLC prometia 3239.40.
div, base, _ = medir_divergencia(
    lucro_real=1648.73, lucro_ohlc=1648.73,
    lucro_ohlc_pre_geometria=3239.40,
    geometria_refeita_tick_real=True, deposito=10000)
checar("com 3.5: a base e a PROMESSA do OHLC, nao o tick real", base, 3239.40)
checar_perto("com 3.5: divergencia real", div, 49.1)
aprovado, _ = veredito(div, 28.45, 30.0)
checar("com 3.5: 49.1% reprova (antes passava com 0.0%)", aprovado, False)

# --- caso 3: 07_GRID_SEPARATE/AUDNZD formula 7, um dos 2 campeoes afetados --
div, _, _ = medir_divergencia(
    lucro_real=79.73, lucro_ohlc=79.73, lucro_ohlc_pre_geometria=206.73,
    geometria_refeita_tick_real=True, deposito=1000)
checar_perto("campeao 07_GRID f7: divergencia real", div, 61.4)
# Retencao era 160.21% -- passava folgado no eixo dela; quem tinha que barrar
# era a divergencia, e ela estava cega.
aprovado, _ = veredito(div, 160.21, 30.0)
checar("campeao 07_GRID f7: reprova agora", aprovado, False)

# --- caso 4: geometria refeita e o OHLC se sustentou -- continua aprovando --
div, _, _ = medir_divergencia(
    lucro_real=29647.78, lucro_ohlc=29647.78,
    lucro_ohlc_pre_geometria=29572.94,
    geometria_refeita_tick_real=True, deposito=10000)
checar_perto("03_TRAIL f6: divergencia real baixa", div, 0.25)
checar("03_TRAIL f6: aprova (retencao ok)", veredito(div, 110.0, 30.0)[0], True)

# --- caso 5: piso do denominador ------------------------------------------
# Base de 1.50 num deposito de 1000 (piso 10.00): percentual nao mede nada.
div, base, motivo = medir_divergencia(
    lucro_real=26.0, lucro_ohlc=1.50, lucro_ohlc_pre_geometria=None,
    geometria_refeita_tick_real=False, deposito=1000)
checar("base minuscula: sem divergencia", div, None)
checar("base minuscula: base ainda e reportada pro log", base, 1.50)
if "abaixo do piso" not in motivo:
    FALHAS.append(f"base minuscula: motivo pouco claro -> {motivo!r}")
checar("base minuscula: reprova por falta de prova",
       veredito(div, 95.0, 30.0)[0], False)
# Exatamente no piso ainda mede.
div, _, _ = medir_divergencia(10.0, 10.0, None, False, 1000)
checar_perto("base exatamente no piso (1% de 1000): mede", div, 0.0)
# Deposito pequeno: o piso nunca cai abaixo de 1.00.
div, _, motivo = medir_divergencia(5.0, 0.50, None, False, 10)
checar("deposito minusculo: piso absoluto de 1.00 vale", div, None)

# --- caso 6: sem conferencia em tick real ---------------------------------
div, base, motivo = medir_divergencia(None, 1000.0, None, False, 500)
checar("sem tick real: sem divergencia", div, None)
checar("sem tick real: sem base", base, None)
if "nao produziu resultado" not in motivo:
    FALHAS.append(f"sem tick real: motivo pouco claro -> {motivo!r}")

# --- caso 7: 3.5 rodou mas o estagio 2/3 nao deixou referencia -------------
div, base, motivo = medir_divergencia(1000.0, 1000.0, None, True, 500)
checar("3.5 sem referencia de OHLC: sem divergencia", div, None)
if "lucro de referencia" not in motivo:
    FALHAS.append(f"3.5 sem referencia: motivo pouco claro -> {motivo!r}")

# --- caso 8: divergencia simetrica -- tick real MELHOR tambem diverge ------
# 04_SLTP_TRAIL/XAUUSD formula 11: OHLC prometia 2467.74, tick real deu
# 4530.59. O modelo barato errou por baixo, mas errou -- a busca mediu outra
# coisa, e o gate e sobre isso, nao sobre a direcao do erro.
div, _, _ = medir_divergencia(4530.59, 4530.59, 2467.74, True, 10000)
checar_perto("tick real acima do OHLC: divergencia mesmo assim", div, 83.6)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("medir_divergencia: todos os casos passaram")
