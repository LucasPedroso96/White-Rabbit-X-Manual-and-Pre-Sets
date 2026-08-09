# -*- coding: utf-8 -*-
"""Motor de sugestao do AutoManagerLive -- ver PLANO_TREINAMENTO_100_A_MILHAO.md
secao 8 ("Deployment: AutoManagerLive") para o desenho completo.

Pega o pool que o painel "Certified sets" ja expoe (`/api/implantacao`) e
produz uma fila NUMERADA de sugestoes de combinacao: combos certificados que
cabem juntos por correlacao (reaproveitando portfolio_builder.py), ordenados
primeiro pela ordem de graduacao por risco (RESEARCH -> HEDGE_ACCOUNT_REQUIRED
-> HIGH_RISK -> HIGH_RISK_RESEARCH), e cada sugestao ja diz quantas contas
precisa e de que tipo.

Fora daqui, de proposito: promocao/rebaixamento por metrica ao vivo (EM_PROVA)
exige historico de trade ao vivo real, que este codebase ainda nao ingere --
ver secao 8 do plano, "Fora de escopo por enquanto".
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

import portfolio_builder as pb
from generate_system_sets import ASSETS, CLASSES, SYSTEMS

# Mesma ordem de graduacao pra capital ao vivo da secao 5 do plano.
TIER_ORDEM = ["RESEARCH", "HEDGE_ACCOUNT_REQUIRED", "HIGH_RISK",
             "HIGH_RISK_RESEARCH"]

SYSTEM_STATUS: dict[str, str] = {s.code: s.status for s in SYSTEMS}

ASSET_CLASS_OF: dict[str, str] = {
    ativo: classe for classe, ativos in ASSETS.items() for ativo in ativos
}


def capital_minimo_classe(simbolo: str) -> float | None:
    """Capital minimo da classe do ativo (generate_system_sets.CLASSES).

    Tenta em tres estagios:
    1. Simbolo exato (cobre "BRK.B" com ponto proprio, nao sufixo de corretora)
    2. Radical antes do primeiro separador (cobre "EURUSD.HT")
    3. Simbolo conhecido mais longo que eh prefixo do input, seguido apenas
       por caracteres de sufixo de broker (cobre "EURUSDm" com bare suffixes)
    """
    # Stage 1: Exact match
    classe = ASSET_CLASS_OF.get(simbolo)
    if classe is not None:
        return CLASSES[classe].capital_base

    # Stage 2: Radical before first separator
    radical = re.split(r"[.\-_]", simbolo)[0]
    classe = ASSET_CLASS_OF.get(radical)
    if classe is not None:
        return CLASSES[classe].capital_base

    # Stage 3: Longest known symbol as prefix (handles bare broker suffixes)
    longest_known = None
    for known_symbol in ASSET_CLASS_OF.keys():
        if simbolo.startswith(known_symbol):
            # Check that after the known symbol, we only have valid broker-suffix chars
            suffix = simbolo[len(known_symbol):]
            # Allow alphanumeric, dots, dashes, underscores for broker suffixes
            if re.match(r'^[a-zA-Z0-9.\-_]*$', suffix):
                if longest_known is None or len(known_symbol) > len(longest_known):
                    longest_known = known_symbol

    if longest_known is not None:
        classe = ASSET_CLASS_OF.get(longest_known)
        if classe is not None:
            return CLASSES[classe].capital_base

    return None
