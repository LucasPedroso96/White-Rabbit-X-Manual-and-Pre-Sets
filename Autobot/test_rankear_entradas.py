# -*- coding: utf-8 -*-
"""Testa a parte sem MT5 de rankear_entradas.py: validade de cache por
periodo e reuso de entrada ja medida no ledger. O ranking de verdade (rodar
11_SIGNAL_ONLY nas 3 familias) precisa do terminal, entao fica fora daqui --
mesmo espirito de test_ready_library.py/test_auto_manager_live.py.

    python test_rankear_entradas.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import rankear_entradas as re

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- caminho_saida -----------------------------------------------------------
checar("caminho_saida usa SIMBOLO_LADO.json",
       re.caminho_saida("XAUUSD", "BUY").name, "XAUUSD_BUY.json")

# --- cache_valido --------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    caminho = Path(tmp) / "AAA_BUY.json"

    checar("cache_valido: arquivo ausente", re.cache_valido(caminho, "a", "b"), False)

    caminho.write_text(json.dumps({"inicio": "2023.01.01", "fim": "2026.01.01",
                                   "entradas": [{"familia": "MULTI"}]}),
                       encoding="utf-8")
    checar("cache_valido: mesmo periodo",
           re.cache_valido(caminho, "2023.01.01", "2026.01.01"), True)
    checar("cache_valido: periodo diferente (from mudou)",
           re.cache_valido(caminho, "2024.01.01", "2026.01.01"), False)
    checar("cache_valido: periodo diferente (to mudou)",
           re.cache_valido(caminho, "2023.01.01", "2027.01.01"), False)

    caminho.write_text(json.dumps({"inicio": "2023.01.01", "fim": "2026.01.01",
                                   "entradas": []}), encoding="utf-8")
    checar("cache_valido: entradas vazia nunca e valida (nenhuma familia mediu)",
           re.cache_valido(caminho, "2023.01.01", "2026.01.01"), False)

    caminho.write_text("{nao e json valido", encoding="utf-8")
    checar("cache_valido: JSON corrompido", re.cache_valido(caminho, "a", "b"), False)

# --- _entrada_do_ledger --------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    ledger_original = re.campanha.LEDGER
    ledger_tmp = Path(tmp) / "campanha_resultados.jsonl"
    linhas = [
        {"simbolo": "EURUSD", "sistema": "01_SLTP", "variante": "BUY_MULTI",
         "composite_score": 100.0},
        {"simbolo": "EURUSD", "sistema": "11_SIGNAL_ONLY", "variante": "SELL_MULTI",
         "composite_score": 50.0},
        {"simbolo": "EURUSD", "sistema": "11_SIGNAL_ONLY", "variante": "BUY_MULTI",
         "composite_score": 10.0},
        {"simbolo": "EURUSD", "sistema": "11_SIGNAL_ONLY", "variante": "BUY_MULTI",
         "erro": "timeout"},
        # entrada mais recente e valida pra BUY_MULTI -- deve vencer sobre a
        # de composite_score=10 acima (_entrada_do_ledger fica com a ULTIMA
        # linha que bate, nao a primeira).
        {"simbolo": "EURUSD", "sistema": "11_SIGNAL_ONLY", "variante": "BUY_MULTI",
         "composite_score": 77.0},
    ]
    ledger_tmp.write_text("\n".join(json.dumps(linha) for linha in linhas) + "\n",
                          encoding="utf-8")
    re.campanha.LEDGER = ledger_tmp
    try:
        achado = re._entrada_do_ledger("EURUSD", "BUY_MULTI")
        checar("_entrada_do_ledger: pega a ULTIMA entrada valida que bate",
               achado["composite_score"] if achado else None, 77.0)
        checar("_entrada_do_ledger: ignora sistema diferente (01_SLTP)",
               re._entrada_do_ledger("EURUSD", "BUY_MULTI") is not None, True)
        checar("_entrada_do_ledger: simbolo sem nenhuma linha",
               re._entrada_do_ledger("XAUUSD", "BUY_MULTI"), None)
        checar("_entrada_do_ledger: variante sem match",
               re._entrada_do_ledger("EURUSD", "BOTH_MULTI"), None)
    finally:
        re.campanha.LEDGER = ledger_original

# --- _entrada_do_ledger: ledger ausente nao explode, so devolve None ----------
with tempfile.TemporaryDirectory() as tmp:
    ledger_original = re.campanha.LEDGER
    re.campanha.LEDGER = Path(tmp) / "nao_existe.jsonl"
    try:
        checar("_entrada_do_ledger: arquivo ausente devolve None",
               re._entrada_do_ledger("EURUSD", "BUY_MULTI"), None)
    finally:
        re.campanha.LEDGER = ledger_original

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("rankear_entradas: todos os casos passaram")
