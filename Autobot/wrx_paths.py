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

origin.txt pode ficar desatualizado -- se o terminal foi reinstalado ou
movido depois que o MetaTrader escreveu esse arquivo pela primeira vez, o
caminho gravado nao existe mais. Achado real, 2026-08-08: aconteceu com um
comprador (RoboForex). Isso e por maquina e o dono nao tem como corrigir a
distancia, entao `install_dir()` aceita uma correcao manual, feita uma vez
so e lembrada depois -- variavel de ambiente WRX_MT5_INSTALL_DIR (por
sessao) ou um arquivo `wrx_install_dir.txt` gravado dentro da propria pasta
de dados (permanente, sobrevive a reinstalacao do Autobot).
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_DATA_DIR = "WRX_MT5_DATA_DIR"
ENV_INSTALL_DIR = "WRX_MT5_INSTALL_DIR"
ENV_MANUALS_STAGING_DIR = "WRX_MANUALS_STAGING_DIR"


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


def manuals_staging_root() -> Path:
    """Pasta de staging dos manuais fora do repo (config por maquina, so
    usada pelas ferramentas internas de manutencao de manual)."""
    env = os.environ.get(ENV_MANUALS_STAGING_DIR)
    if env:
        p = Path(env)
        if not p.exists():
            raise SystemExit(f"{ENV_MANUALS_STAGING_DIR} aponta para um "
                              f"caminho que nao existe: {p}")
        return p
    raise SystemExit(
        f"Configure a variavel de ambiente {ENV_MANUALS_STAGING_DIR} "
        "apontando para a pasta de staging dos manuais "
        "(Pacote_Completo_White_Rabbit_X/Languages)."
    )


def _install_dir_override_file() -> Path:
    return data_dir() / "wrx_install_dir.txt"


def set_install_dir_override(caminho: Path) -> None:
    """Grava a correcao manual do diretorio de instalacao, uma vez so."""
    _install_dir_override_file().write_text(str(caminho), encoding="utf-8")


def install_dir() -> Path:
    """Diretorio de instalacao (onde mora terminal64.exe).

    Ordem: WRX_MT5_INSTALL_DIR, depois o override gravado em
    wrx_install_dir.txt, depois o origin.txt que o proprio MetaTrader grava
    na pasta de dados (ver docstring do modulo -- esse ultimo pode ficar
    desatualizado).
    """
    env = os.environ.get(ENV_INSTALL_DIR)
    if env:
        p = Path(env)
        if not p.exists():
            raise SystemExit(f"{ENV_INSTALL_DIR} aponta para um caminho que "
                              f"nao existe: {p}")
        return p

    override = _install_dir_override_file()
    if override.exists():
        p = Path(override.read_text(encoding="utf-8").strip())
        if not p.exists():
            raise SystemExit(
                f"{override} aponta para um caminho que nao existe: {p}\n"
                "Apague o arquivo e rode de novo, ou edite-o com o caminho certo "
                "(a pasta que tem terminal64.exe, sem o nome do arquivo no fim).")
        return p

    origin = data_dir() / "origin.txt"
    if not origin.exists():
        raise SystemExit(
            f"{origin} nao existe -- nao consigo achar o terminal64.exe. "
            f"Rode o MetaTrader ao menos uma vez para ele gerar esse arquivo."
        )
    caminho = origin.read_text(encoding="utf-16").strip("\x00﻿ \r\n")
    p = Path(caminho)
    if p.exists():
        return p

    raise SystemExit(
        f"origin.txt aponta para um caminho que nao existe: {p}\n\n"
        "Isso acontece quando o MetaTrader foi reinstalado ou movido depois\n"
        "que esse arquivo foi escrito -- e por maquina, nao da pra detectar\n"
        "sozinho de forma confiavel.\n\n"
        "Corrija uma vez so: ache a pasta onde fica o terminal64.exe de\n"
        "verdade (atalho do MetaTrader na area de trabalho -> botao direito\n"
        "-> Abrir local do arquivo) e faca UMA das duas opcoes:\n\n"
        f"  1) crie o arquivo:\n     {override}\n"
        "     com uma linha so: o caminho da pasta (sem terminal64.exe no fim)\n\n"
        f"  2) ou defina a variavel de ambiente {ENV_INSTALL_DIR} com esse\n"
        "     mesmo caminho antes de rodar."
    )


def terminal_exe() -> Path:
    exe = install_dir() / "terminal64.exe"
    if not exe.exists():
        raise SystemExit(f"terminal64.exe nao encontrado em {exe}")
    return exe


TERMINAL = data_dir()
