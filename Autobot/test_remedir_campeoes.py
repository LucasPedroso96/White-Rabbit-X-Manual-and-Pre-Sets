# -*- coding: utf-8 -*-
"""Testa remedir_campeoes.py (2026-09-26) sem MT5: escolha da linha do
ledger que produziu o arquivo, janela da remedicao e o julgamento.

    python test_remedir_campeoes.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import remedir_campeoes as rc

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


tmp = Path(tempfile.mkdtemp())
try:
    arq = tmp / "VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set"
    arq.write_text("; t\r\nTake=9.00||0||0||0||N\r\nTimeFrame=5||0||0||0||N\r\n",
                   encoding="utf-16")
    campeao = {"quando": "2026-09-21T13:53:29", "janela_dias": 360,
               "aprovado": True, "parametros": {"Take": "9.00", "TimeFrame": "5"}}
    desafiante = {"quando": "2026-09-26T06:24:00", "aprovado": False,
                  "parametros": {"Take": "7.00", "TimeFrame": "3"}}
    checar("linha do arquivo = a do campeao, nao a do desafiante posterior",
           rc.linha_do_arquivo(arq, [campeao, desafiante]), campeao)
    checar("sem linha com os mesmos parametros -> {}",
           rc.linha_do_arquivo(arq, [desafiante]), {})
    checar("janela: mesmo comprimento, terminando na aprovacao",
           rc.janela(campeao), ("2025.09.26", "2026.09.21"))
    checar("retencao real acima do piso: confirma", rc.julgar(54.6)[0], True)
    checar("retencao real abaixo do piso: rebaixa", rc.julgar(12.0)[0], False)
    checar("sem medida: rebaixa (nao existe prova)", rc.julgar(None)[0], False)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if FALHAS:
    print("remedir_campeoes: FALHOU")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1)
print("remedir_campeoes: todos os casos passaram")
