# -*- coding: utf-8 -*-
"""Testa resolver_deposito() (dono, 2026-08-10): o deposito de UM combo tem
que vir da classe do PROPRIO simbolo (Forex, Metais...), nunca de um numero
fixo pra campanha inteira.

Achado do dono: o Auto-suggest do dashboard calculava o MAIOR capital_base
entre as classes marcadas (`maiorCapitalBase()` em app.js) e mandava esse
numero unico como --deposit pra TODOS os combos da corrida -- misturar Forex
com Metais numa campanha manual testava Forex com o deposito de Metais
(10000), inflando a margem disponivel e aprovando no gate de sobrevivencia
combos que nao aguentariam o capital real da propria classe (1000).

    python test_deposito_por_classe.py
"""
from __future__ import annotations

import sys

import campanha

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# ==================================================================== resolver_deposito
checar("Forex sem override -> capital_base da classe (1000)",
       campanha.resolver_deposito("EURUSD", None), 1000)
checar("Metais sem override -> capital_base da classe (10000)",
       campanha.resolver_deposito("XAUUSD", None), 10000)
checar("simbolo com sufixo de corretora/HT ainda resolve a classe",
       campanha.resolver_deposito("EURUSD.HT", None), 1000)
checar("override explicito sempre vence, nao importa a classe",
       campanha.resolver_deposito("XAUUSD", 500), 500)
checar("override explicito de 0 tambem vence (falsy mas nao None)",
       campanha.resolver_deposito("EURUSD", 0), 0)

try:
    campanha.resolver_deposito("SIMBOLO_QUE_NAO_EXISTE_XYZ", None)
    FALHAS.append("simbolo sem classe conhecida deveria levantar, nao "
                  "silenciar com um numero chutado")
except SystemExit:
    pass


# ==================================================================== rodar_combo usa o resolver
class _ProcessoFalso:
    def __init__(self, returncode: int) -> None:
        self._returncode = returncode
        self.stdout = iter(())

    def wait(self, timeout=None) -> int:
        return self._returncode

    def kill(self) -> None:
        pass


def _cmd_usado_por_rodar_combo(simbolo: str, deposito_arg) -> list[str]:
    from types import SimpleNamespace
    capturado: dict = {}
    popen_original = campanha.subprocess.Popen

    def _popen_espiao(cmd, **kwargs):
        capturado["cmd"] = cmd
        return _ProcessoFalso(0)

    campanha.subprocess.Popen = _popen_espiao
    try:
        args = SimpleNamespace(inicio="2023.01.01", fim="2026.01.01",
                               deposit=deposito_arg, min_retencao=30.0,
                               timeout=1)
        campanha.rodar_combo(simbolo, "07_GRID_SEPARATE", "BUY_MULTI", args)
    finally:
        campanha.subprocess.Popen = popen_original
    return capturado["cmd"]


cmd_forex_auto = _cmd_usado_por_rodar_combo("EURUSD", None)
i = cmd_forex_auto.index("--deposit")
checar("rodar_combo (Forex, auto): --deposit vem da classe",
       cmd_forex_auto[i + 1], "1000")

cmd_metal_auto = _cmd_usado_por_rodar_combo("XAUUSD", None)
i = cmd_metal_auto.index("--deposit")
checar("rodar_combo (Metais, auto): --deposit vem da classe",
       cmd_metal_auto[i + 1], "10000")

cmd_override = _cmd_usado_por_rodar_combo("XAUUSD", 250)
i = cmd_override.index("--deposit")
checar("rodar_combo com override explicito: respeita o numero passado",
       cmd_override[i + 1], "250")


if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("deposito_por_classe: todos os casos passaram")
