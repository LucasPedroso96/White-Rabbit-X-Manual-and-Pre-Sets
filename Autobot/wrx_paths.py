# -*- coding: utf-8 -*-
"""Resolve o terminal MT5 do usuario -- sem caminho pessoal cravado no codigo.

Cada instalacao do MetaTrader tem uma PASTA DE DADOS com hash proprio
(`AppData\\Roaming\\MetaQuotes\\Terminal\\<hash>\\`, onde moram MQL5/Experts,
MQL5/Profiles/Tester etc.) separada do DIRETORIO DE INSTALACAO (onde mora
`terminal64.exe`). As ferramentas deste pacote precisam dos dois, e cada
maquina tem os seus -- por isso nada aqui e um caminho fixo.

Resolucao da pasta de dados, nesta ordem:
  1. Variavel de ambiente WRX_MT5_DATA_DIR.
  2. Auto-deteccao: primeiro terminal em
     `%APPDATA%\\MetaQuotes\\Terminal\\*\\` com "White Rabbit X" instalado
     em MQL5/Experts (.mq5 ou .ex5).
  3. Erro claro -- nunca um numero ou caminho inventado.

Resolucao do diretorio de instalacao (para achar `terminal64.exe`): o proprio
MetaTrader grava um `origin.txt` (UTF-16) dentro da pasta de dados, apontando
para onde foi instalado. Le-se esse arquivo em vez de adivinhar Program Files,
porque instalacao portable ou em outro disco quebraria esse chute.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_DATA_DIR = "WRX_MT5_DATA_DIR"


def _autodetect_data_dir() -> Path | None:
    base = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if not base.exists():
        return None
    for terminal_dir in base.iterdir():
        experts = terminal_dir / "MQL5" / "Experts"
        if not experts.exists():
            continue
        if any("White Rabbit X" in p.name
               for p in list(experts.glob("*.mq5")) + list(experts.glob("*.ex5"))):
            return terminal_dir
    return None


def data_dir() -> Path:
    """Pasta de dados do terminal (onde moram MQL5/Experts, Profiles/Tester)."""
    env = os.environ.get(ENV_DATA_DIR)
    if env:
        p = Path(env)
        if not p.exists():
            raise SystemExit(f"{ENV_DATA_DIR} aponta para um caminho que nao "
                              f"existe: {p}")
        return p
    found = _autodetect_data_dir()
    if found is not None:
        return found
    raise SystemExit(
        "Nao encontrei um terminal MT5 com o White Rabbit X instalado.\n"
        f"Configure a variavel de ambiente {ENV_DATA_DIR} apontando para a "
        "pasta de dados do terminal (no MetaTrader: File -> Open Data Folder), "
        "ou instale o EA em MQL5/Experts antes de rodar estas ferramentas."
    )


def install_dir() -> Path:
    """Diretorio de instalacao (onde mora terminal64.exe), via origin.txt."""
    origin = data_dir() / "origin.txt"
    if not origin.exists():
        raise SystemExit(
            f"{origin} nao existe -- nao consigo achar o terminal64.exe. "
            f"Rode o MetaTrader ao menos uma vez para ele gerar esse arquivo."
        )
    caminho = origin.read_text(encoding="utf-16").strip("\x00﻿ \r\n")
    p = Path(caminho)
    if not p.exists():
        raise SystemExit(f"origin.txt aponta para um caminho que nao existe: {p}")
    return p


def terminal_exe() -> Path:
    exe = install_dir() / "terminal64.exe"
    if not exe.exists():
        raise SystemExit(f"terminal64.exe nao encontrado em {exe}")
    return exe


TERMINAL = data_dir()
