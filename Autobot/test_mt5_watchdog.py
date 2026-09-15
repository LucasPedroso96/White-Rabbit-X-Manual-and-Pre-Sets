# -*- coding: utf-8 -*-
"""Testa mt5_watchdog.rodar_com_watchdog() com processos reais e curtos
(scripts Python inline via -c) -- sem MT5, sem rede, so subprocess de
verdade pra cobrir o caminho de detectar progresso pelo tamanho do arquivo.

    python test_mt5_watchdog.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from mt5_watchdog import rodar_com_watchdog

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


with tempfile.TemporaryDirectory() as tmp:
    log = Path(tmp) / "saida.log"

    # --- termina sozinho, imprimindo -- nunca deveria parecer travado
    t0 = time.monotonic()
    script_ok = ("import time\n"
                "for _ in range(3):\n"
                "    print('progresso')\n"
                "    time.sleep(0.3)\n")
    status = rodar_com_watchdog([sys.executable, "-u", "-c", script_ok], log,
                                sem_progresso_max=5, checar_a_cada=0.5)
    dt = time.monotonic() - t0
    checar("termina sozinho: status", status, "ok")
    checar("termina sozinho: log tem o texto esperado",
           "progresso" in log.read_text(encoding="utf-8"), True)
    if dt > 4:
        FALHAS.append(f"termina sozinho: demorou {dt:.1f}s (esperado < 4s "
                      "-- watchdog nao devia segurar um processo que ja "
                      "terminou)")

    # --- nunca imprime nada (dorme) -- watchdog tem que matar antes do
    # sleep() do proprio script terminar (60s), nao esperar ele por educacao
    t0 = time.monotonic()
    script_travado = "import time\ntime.sleep(60)\n"
    status = rodar_com_watchdog([sys.executable, "-u", "-c", script_travado],
                                log, sem_progresso_max=1.5, checar_a_cada=0.5)
    dt = time.monotonic() - t0
    checar("trava: status", status, "travado")
    checar("trava: log registra o motivo",
           "WATCHDOG" in log.read_text(encoding="utf-8"), True)
    if dt > 10:
        FALHAS.append(f"trava: demorou {dt:.1f}s pra matar (esperado < 10s "
                      "-- watchdog devia matar bem antes do sleep(60) do "
                      "script acabar sozinho)")

if FALHAS:
    print(f"\n{len(FALHAS)} FALHA(S):")
    for f in FALHAS:
        print("  " + f)
    sys.exit(1)
print("mt5_watchdog: todos os casos passaram")
