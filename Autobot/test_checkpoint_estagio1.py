# -*- coding: utf-8 -*-
"""Testa o checkpoint do Estagio 1 (salvar/carregar/limpar) sem precisar do
MT5 nem de uma corrida real.

Achado do dono, 2026-08-06: reiniciar a campanha (pra aplicar um fix) jogava
fora o `linhas` acumulado das rodadas ja rodadas -- o cache do tester (.opt)
acelera RE-SIMULAR um passe, mas nao substitui o que o Estagio 1 ja tinha
DECIDIDO sobre quantas rodadas e quais linhas passaram o piso. Este teste
usa CHECKPOINTS_DIR real (pasta gitignored), limpando antes/depois de cada
caso pra nao deixar lixo.

    python test_checkpoint_estagio1.py
"""
from __future__ import annotations

import shutil
import sys

from optimize_two_stage import (
    CHECKPOINTS_DIR,
    carregar_checkpoint_estagio1,
    limpar_checkpoint_estagio1,
    salvar_checkpoint_estagio1,
)

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


shutil.rmtree(CHECKPOINTS_DIR, ignore_errors=True)

# --- sem checkpoint: None, sem excecao -------------------------------------
checar("sem checkpoint", carregar_checkpoint_estagio1("EURUSD", "07_GRID_SEPARATE",
                                                       "BUY_MULTI"), None)

# --- salva e recarrega o MESMO combo: dados batem ---------------------------
cab = ["Pass", "Profit", "EntryIndicator"]
linhas = [["1", "500.0", "0"], ["2", "300.0", "1"]]
salvar_checkpoint_estagio1("EURUSD", "07_GRID_SEPARATE", "BUY_MULTI", cab, linhas, 2)
dado = carregar_checkpoint_estagio1("EURUSD", "07_GRID_SEPARATE", "BUY_MULTI")
checar("recarrega: nao e None", dado is not None, True)
checar("recarrega: cab bate", dado["cab"], cab)
checar("recarrega: linhas bate", dado["linhas"], linhas)
checar("recarrega: rodada_concluida bate", dado["rodada_concluida"], 2)

# --- combo DIFERENTE (mesmo sistema/variante, simbolo trocado): None --------
checar("combo diferente: nao reaproveita",
       carregar_checkpoint_estagio1("GBPUSD", "07_GRID_SEPARATE", "BUY_MULTI"), None)

# --- variante diferente do MESMO simbolo/sistema: None -----------------------
checar("variante diferente: nao reaproveita",
       carregar_checkpoint_estagio1("EURUSD", "07_GRID_SEPARATE", "SELL_MULTI"), None)

# --- limpar: some de vez ------------------------------------------------------
limpar_checkpoint_estagio1("EURUSD", "07_GRID_SEPARATE", "BUY_MULTI")
checar("depois de limpar: None",
       carregar_checkpoint_estagio1("EURUSD", "07_GRID_SEPARATE", "BUY_MULTI"), None)

# --- limpar sem nunca ter existido: nao explode ------------------------------
limpar_checkpoint_estagio1("USDJPY", "09_MARTINGALE", "SELL_MULTI")

# --- arquivo corrompido (json invalido): None, sem excecao -------------------
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
(CHECKPOINTS_DIR / "AUDCAD__07_GRID_SEPARATE__BUY_MULTI.json").write_text(
    "isso nao e json valido {{{", encoding="utf-8")
checar("json corrompido: None",
       carregar_checkpoint_estagio1("AUDCAD", "07_GRID_SEPARATE", "BUY_MULTI"), None)

shutil.rmtree(CHECKPOINTS_DIR, ignore_errors=True)

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("checkpoint_estagio1: todos os casos passaram")
