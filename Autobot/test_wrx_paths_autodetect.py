# -*- coding: utf-8 -*-
"""Testa _autodetect_data_dir() (dono, 2026-08-10): achado ao vivo -- uma
copia antiga da EA num projeto totalmente diferente (Desktop\\Levain 2.0...)
tambem tinha "White Rabbit X" instalado em MQL5\\Experts, sem nenhum set
gerado. _autodetect_data_dir() so olhava "tem a EA?" e devolvia o primeiro
terminal que batesse, na ordem crua de `Path.iterdir()` -- que NAO e
determinada (varia por SO/filesystem). Um `amostra_noite.py` de 154 itens
(~16h) rodou inteiro contra esse terminal errado: zero sets, zero corrida de
verdade, "concluido" impresso como se tivesse dado certo. Silencioso e caro.

    python test_wrx_paths_autodetect.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import wrx_paths

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def _criar_terminal(base: Path, nome: str, com_sets: bool) -> Path:
    terminal = base / nome
    experts = terminal / "MQL5" / "Experts"
    experts.mkdir(parents=True)
    (experts / "White Rabbit X (Global Multi-Indicator).ex5").write_bytes(b"")
    if com_sets:
        sets = (terminal / "MQL5" / "Profiles" / "Tester"
                / "White_Rabbit_X_Sets_templates" / "01_Forex" / "EURUSD")
        sets.mkdir(parents=True)
    return terminal


tmp = Path(tempfile.mkdtemp())
appdata_original = os.environ.get("APPDATA")
try:
    base = tmp / "MetaQuotes" / "Terminal"

    # Nomeado pra vir ANTES do de verdade em ordem alfabetica -- prova que a
    # escolha nao depende de sorte de ordenacao.
    _criar_terminal(base, "AAAA_sem_sets", com_sets=False)
    real = _criar_terminal(base, "ZZZZ_com_sets", com_sets=True)
    os.environ["APPDATA"] = str(tmp)
    achado = wrx_paths._autodetect_data_dir()
    checar("prefere o terminal com Sets de verdade, mesmo vindo depois "
           "na ordem alfabetica", achado, real)

    shutil.rmtree(base)
    base.mkdir(parents=True)
    # Inverte a ordem alfabetica -- mesmo resultado, decoy nao pode vencer
    # so por vir primeiro.
    real2 = _criar_terminal(base, "AAAA_com_sets", com_sets=True)
    _criar_terminal(base, "ZZZZ_sem_sets", com_sets=False)
    achado2 = wrx_paths._autodetect_data_dir()
    checar("mesma preferencia com a ordem alfabetica invertida",
           achado2, real2)

    shutil.rmtree(base)
    base.mkdir(parents=True)
    # Nenhum candidato tem Sets -- nao pode quebrar, cai pro primeiro em
    # ordem determinada (nunca a ordem crua do iterdir).
    unico = _criar_terminal(base, "UNICO", com_sets=False)
    achado3 = wrx_paths._autodetect_data_dir()
    checar("sem nenhum Sets: nao quebra, devolve o unico candidato",
           achado3, unico)

    shutil.rmtree(base)
    base.mkdir(parents=True)
    checar("pasta Terminal sem nenhuma instalacao da EA: None",
           wrx_paths._autodetect_data_dir(), None)
finally:
    if appdata_original is not None:
        os.environ["APPDATA"] = appdata_original
    else:
        os.environ.pop("APPDATA", None)
    shutil.rmtree(tmp, ignore_errors=True)


if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("wrx_paths_autodetect: todos os casos passaram")
