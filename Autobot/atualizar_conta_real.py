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

Uso:
    python atualizar_conta_real.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

from mt5_runner import fechar_terminal, garantir_terminal_livre

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / "_conta_real.json"
TERMINAL = Path(r"C:\Program Files\RoboForex MT5 Terminal (WhiteRabbitEA)"
                r"\terminal64.exe")


def main() -> int:
    garantir_terminal_livre(fechar=True)
    if not mt5.initialize(path=str(TERMINAL)):
        print(f"Falha ao conectar: {mt5.last_error()}")
        return 1
    try:
        conta = mt5.account_info()
        if conta is None:
            print(f"Sem account_info: {mt5.last_error()}")
            return 1
        dados = {
            "login": conta.login,
            "servidor": conta.server,
            "leverage": f"1:{conta.leverage}",
            "moeda": conta.currency,
            "quando": datetime.now().isoformat(timespec="seconds"),
        }
        CACHE.write_text(json.dumps(dados, indent=2, ensure_ascii=False),
                         encoding="utf-8")
        print(f"leverage real: {dados['leverage']} | conta {dados['login']} "
              f"@ {dados['servidor']} | gravado em {CACHE.name}")
    finally:
        fechar_terminal()
    return 0


if __name__ == "__main__":
    sys.exit(main())
