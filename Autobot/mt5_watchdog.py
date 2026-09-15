# -*- coding: utf-8 -*-
"""Watchdog de travamento pra passes longos do MT5 (Strategy Tester).

Existe porque o teto de tempo do MT5 tester (`--timeout` de
`optimize_two_stage.py`) e POR LANCAMENTO individual (uma otimizacao ou um
passe unico dentro do circuito), nao pelo CIRCUITO inteiro que um sweep de
formula roda -- um travamento genuino (achado ja documentado,
`mt5_runner.py`: "processo que nao fecha a tempo, mesmo com o teste tendo
terminado") nunca era detectado enquanto quem chama so espera o processo
inteiro terminar via `subprocess.run()`.

Detecta progresso pelo CRESCIMENTO DO LOG (tamanho do arquivo), nao por uso
de CPU -- mais simples, funciona igual em qualquer maquina, e reflete
direto se o filho ainda esta imprimindo alguma coisa (o log em disco e o
unico sinal de vida confiavel de um subprocess cujo stdout/stderr foi
redirecionado pra arquivo). Exige que o comando rode com saida SEM buffer
(`-u` no Python) -- com buffer, o arquivo so cresce quando o buffer do SO
enche, e o watchdog dispararia falso-positivo.

    from mt5_watchdog import rodar_com_watchdog
    status = rodar_com_watchdog(comando, log_path, sem_progresso_max=900)
    # status: "ok" (o processo terminou sozinho -- sucesso ou falha do
    #         proprio comando, o log de dentro conta qual dos dois foi)
    #         ou "travado" (matei o processo, o log parou de crescer)

Achado ao vivo, 2026-09-14: o dono viu um sweep "parecer travado" (na
verdade em progresso normal, so no Estagio 3.5, que nao mostra barra no
MT5) e pediu deteccao de verdade pra nao ficar dias esperando um
travamento genuino sem saber.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path


def rodar_com_watchdog(comando: list[str], log_path: Path,
                       sem_progresso_max: int = 900,
                       checar_a_cada: int = 60) -> str:
    """Roda `comando`, escrevendo stdout/stderr em `log_path` (sobrescrito).

    Mata o processo (e volta "travado") se o arquivo de log ficar
    `sem_progresso_max` segundos SEGUIDOS sem crescer nem um byte. Volta
    "ok" se o processo terminar sozinho antes disso, de qualquer jeito
    (`comando` pode ter saido com erro -- isso e problema de quem chama
    ler no proprio log, nao deste watchdog: o unico papel dele e nao
    deixar o SO ficar preso esperando um filho que nunca mais vai sair
    sozinho).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        proc = subprocess.Popen(comando, stdout=fh, stderr=subprocess.STDOUT)
        try:
            ultimo_tamanho = -1
            parado_desde: float | None = None
            while proc.poll() is None:
                time.sleep(checar_a_cada)
                tamanho = log_path.stat().st_size if log_path.exists() else 0
                agora = time.monotonic()
                if tamanho > ultimo_tamanho:
                    ultimo_tamanho = tamanho
                    parado_desde = None
                    continue
                if parado_desde is None:
                    parado_desde = agora
                elif agora - parado_desde >= sem_progresso_max:
                    proc.kill()
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        pass  # matou; nao ha mais o que esperar
                    fh.write(
                        f"\n\n>>> WATCHDOG: log sem crescer por "
                        f"{sem_progresso_max}s -- processo morto "
                        "(considerado travado).\n")
                    fh.flush()
                    return "travado"
        except BaseException:
            proc.kill()
            raise
        return "ok"
