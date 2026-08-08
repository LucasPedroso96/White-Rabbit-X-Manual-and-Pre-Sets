# -*- coding: utf-8 -*-
"""Consulta a conta REAL via MT5 (alavancagem etc.) e grava em _conta_real.json.

`escrever_ini()` (optimize_sets.py) precisa da alavancagem real para o .ini do
tester -- alavancagem errada muda o comportamento de MARGEM da simulacao
(chamada de margem, stop-out), e isso e path-dependent: pode divergir entre o
passe OHLC e o passe tick real sem que nada mais tenha mudado. Por isso nao
pode ser um numero digitado no codigo.

Roda em separado, ANTES da campanha, e nao dentro de escrever_ini a cada
passe: a conexao Python (mt5.initialize) e o `/config:...` do tester nao
coexistem com o mesmo terminal (ver mt5_runner.py) -- por isso fecha o
terminal no fim, deixando o caminho livre pro `/config:` de cada combo.

`atualizar()` tambem e chamada automaticamente por `optimize_sets.
leverage_conta()` na primeira vez que o cache nao existe (achado real,
2026-08-08: um comprador rodando pelo dashboard nunca saberia que
precisava rodar este script na mao antes -- a campanha simplesmente
reprovava todo combo de sistemas que precisam de alavancagem real, tipo
grid, com "sem cache de conta real"). Continua dando pra rodar solto
tambem, pra atualizar o cache sem esperar a campanha precisar dele.

Uso:
    python atualizar_conta_real.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

import wrx_paths
from mt5_runner import fechar_terminal, garantir_terminal_livre

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / "_conta_real.json"
TERMINAL = wrx_paths.terminal_exe()


def atualizar() -> dict | None:
    """Consulta a conta real e grava o cache. Devolve os dados gravados, ou
    None se a consulta falhar (terminal sem login, por exemplo) -- quem
    chama decide como reagir a None, nunca supoe um valor no lugar."""
    garantir_terminal_livre(fechar=True)
    if not mt5.initialize(path=str(TERMINAL)):
        return None
    try:
        conta = mt5.account_info()
        if conta is None:
            return None
        dados = {
            "login": conta.login,
            "servidor": conta.server,
            "leverage": f"1:{conta.leverage}",
            "moeda": conta.currency,
            "quando": datetime.now().isoformat(timespec="seconds"),
        }
        CACHE.write_text(json.dumps(dados, indent=2, ensure_ascii=False),
                         encoding="utf-8")
        return dados
    finally:
        fechar_terminal()


def main() -> int:
    dados = atualizar()
    if dados is None:
        print(f"Falha ao conectar/ler conta: {mt5.last_error()}")
        return 1
    print(f"leverage real: {dados['leverage']} | conta {dados['login']} "
          f"@ {dados['servidor']} | gravado em {CACHE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
