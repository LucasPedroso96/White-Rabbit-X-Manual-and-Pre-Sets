# -*- coding: utf-8 -*-
"""Testa feitos() do amostra_noite.py (dono, 2026-08-10): achado ao vivo --
a corrida contra o terminal MT5 errado (ver test_wrx_paths_autodetect.py)
gravou 154 linhas de "erro: set nao encontrado" no ledger. feitos() nao
distinguia isso de resultado de verdade (ao contrario de campanha.feitos(),
que ja ignora "erro" de proposito) -- relancar o script achava "154 ja
feitos, 0 pendentes" e nao rodava nada, so pra confirmar que o erro anterior
"ja tinha sido feito".

    python test_amostra_noite.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import amostra_noite as an

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


tmp = Path(tempfile.mkdtemp())
ledger_original = an.LEDGER
an.LEDGER = tmp / "ledger_teste.jsonl"
try:
    with an.LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"fase": "fulltest", "sistema": "01_SLTP",
                             "formula": 9, "erro": "set nao encontrado"}) + "\n")
        fh.write(json.dumps({"fase": "fulltest", "sistema": "01_SLTP",
                             "formula": 2, "profit": 123.45}) + "\n")

    vistos = an.feitos()
    checar("entrada com erro NAO conta como feita",
           ("fulltest", "01_SLTP", "9") in vistos, False)
    checar("entrada com resultado de verdade conta como feita",
           ("fulltest", "01_SLTP", "2") in vistos, True)
finally:
    an.LEDGER = ledger_original
    shutil.rmtree(tmp, ignore_errors=True)


if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("amostra_noite: todos os casos passaram")
