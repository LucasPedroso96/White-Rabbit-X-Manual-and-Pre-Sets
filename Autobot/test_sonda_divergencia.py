# -*- coding: utf-8 -*-
"""Testa sonda_divergencia_estagio1() (2026-09-26): mede OHLC x tick real do
vencedor do Estagio 1 SEM gate, e nunca derruba o combo -- qualquer falha
vira None. Sem MT5: passe_unico/reescrever trocados por dubles.

    python test_sonda_divergencia.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import optimize_two_stage as ots

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


args = SimpleNamespace(symbol="XAUUSD", period="M1", inicio="2025.01.01",
                       fim="2025.12.31", deposit=1000, variante="BUY_MULTI")
salvos = (ots.passe_unico, ots.reescrever)
gravados: list[dict] = []
try:
    ots.reescrever = lambda _o, _t, _e, travar: gravados.append(dict(travar))
    ots.passe_unico = lambda *a, **_k: {"saldo": {1: 1100.0, 4: 1060.0}[a[6]]}
    div = ots.sonda_divergencia_estagio1(Path("o.set"), Path("t.set"),
                                         {"EntryIndicator": "3"}, args)
    checar("OHLC +100 x tick +60 = 40%", round(div, 1), 40.0)
    checar("mede em modo In-Sample (igual a conferencia do Estagio 4)",
           gravados[-1].get("MetodoDeEntradawfo"), "0")

    ots.passe_unico = lambda *a, **_k: {"saldo": None}
    checar("passe sem saldo -> None",
           ots.sonda_divergencia_estagio1(Path("o"), Path("t"), {}, args), None)

    def _explode(*_a, **_k):
        raise RuntimeError("terminal ocupado")
    ots.passe_unico = _explode
    checar("excecao nao derruba o combo -> None",
           ots.sonda_divergencia_estagio1(Path("o"), Path("t"), {}, args), None)
finally:
    ots.passe_unico, ots.reescrever = salvos

if FALHAS:
    print("sonda_divergencia: FALHOU")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("sonda_divergencia: todos os casos passaram")
