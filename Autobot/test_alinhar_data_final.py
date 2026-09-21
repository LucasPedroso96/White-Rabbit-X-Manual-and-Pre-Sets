# -*- coding: utf-8 -*-
"""input_end_date do .set sempre casado com o fim do teste (ponto unico).

Regressao do bug do WFA cego (2026-09-21): a EA compara input_end_date com o
fim real do teste (tolerancia 80 h) e, se nao bater, o OnTester zera a formula
em silencio. rodar() e passe_unico() chamam alinhar_data_final() antes de
lancar o MT5 -- nenhum chamador consegue desalinhar.
"""
from __future__ import annotations

import inspect
import shutil
import sys
import tempfile
from pathlib import Path

import optimize_two_stage as ots

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


CONTEUDO = ("; teste\r\nAtivarWFO=true||true||0||true||N\r\n"
            "MetodoDeEntradawfo=0||0||1||0||N\r\n"
            "input_end_date=2026.09.12\r\n"
            "wfo_customWindowSizeDays=122||122||1||122||N\r\n"
            "selectedFormula=11||11||1||11||N\r\n")


def escrever(pasta: Path, nome: str, texto: str = CONTEUDO) -> Path:
    p = pasta / nome
    p.write_bytes(texto.encode("utf-16"))
    return p


def ler(p: Path) -> str:
    return p.read_bytes().decode("utf-16")


tmp = Path(tempfile.mkdtemp())
try:
    # 1) copia de trabalho com data velha -> alinha e devolve o valor antigo
    p = escrever(tmp, "_WFA_JANELA.set")
    checar("devolve o valor antigo", ots.alinhar_data_final(p, "2026.09.17"),
           "2026.09.12")
    t = ler(p)
    checar("gravou a data nova", "input_end_date=2026.09.17\r\n" in t, True)
    checar("nao sobrou a velha", "2026.09.12" in t, False)
    checar("nao mexeu em WFO", "wfo_customWindowSizeDays=122||122||1||122||N" in t, True)
    checar("nao mexeu na formula", "selectedFormula=11||11||1||11||N" in t, True)
    checar("preservou o BOM UTF-16", p.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff"), True)

    # 2) idempotente: ja alinhado -> None e sem reescrever
    checar("ja alinhado devolve None", ots.alinhar_data_final(p, "2026.09.17"), None)

    # 3) TRAVA: template/campeao (nome sem '_') nunca e alterado
    orig = escrever(tmp, "BUY_MULTI.set")
    antes = orig.read_bytes()
    checar("template nao e alterado (retorno)", ots.alinhar_data_final(orig, "2026.09.17"), None)
    checar("template nao e alterado (bytes)", orig.read_bytes(), antes)
    val = escrever(tmp, "VALIDADO_XAUUSD_04_SLTP_TRAIL_BUY_MULTI.set")
    antes = val.read_bytes()
    ots.alinhar_data_final(val, "2026.09.17")
    checar("VALIDADO_ nao e alterado", val.read_bytes(), antes)

    # 4) sem a linha / arquivo inexistente: nao quebra
    sem = escrever(tmp, "_SEM.set", "AtivarWFO=false||false||0||false||N\r\n")
    checar("sem input_end_date -> None", ots.alinhar_data_final(sem, "2026.09.17"), None)
    checar("arquivo inexistente -> None",
           ots.alinhar_data_final(tmp / "_NAO_EXISTE.set", "2026.09.17"), None)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 5) os DOIS pontos de lancamento chamam o alinhamento
for fn in (ots.rodar, ots.passe_unico):
    checar(f"{fn.__name__} chama alinhar_data_final",
           "alinhar_data_final(caminho_set, fim)" in inspect.getsource(fn), True)

if FALHAS:
    print(f"{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("alinhar_data_final: todos os casos passaram")
