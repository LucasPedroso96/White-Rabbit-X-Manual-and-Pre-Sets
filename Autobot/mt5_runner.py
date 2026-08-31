# -*- coding: utf-8 -*-
"""Utilitarios compartilhados para rodar o Strategy Tester pela linha de comando.

Existe por causa de UMA armadilha que custou tres diagnosticos separados no
mesmo dia: com um terminal ja aberto, `terminal64.exe /config:...` nao roda
nada. O Windows apenas da foco a instancia existente e o processo novo sai --
sem erro, sem log, sem exit code diferente de zero. O teste simplesmente nao
acontece, e quem le o resultado ve "0 trades" e vai investigar a estrategia.

Por isso a checagem vive aqui e nao no comentario de cada script.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path


def _pids_do_terminal(terminal: Path) -> list[str]:
    """PIDs de terminal64.exe rodando EXATAMENTE deste caminho.

    2026-08-30: esta maquina roda varias instalacoes de MT5 lado a lado para
    projetos diferentes (Zeus, ClaudeTrader Bridge, etc.), todas com o mesmo
    nome de processo terminal64.exe. Um `taskkill /IM` por nome (o que este
    modulo fazia antes) mata TODAS elas, nao so a do White Rabbit -- inclusive
    um EA de outro projeto rodando ao vivo numa conta demo real. Descoberto
    correlacionando reinicios inexplicados do terminal do Zeus com este
    otimizador rodando ao mesmo tempo. `tasklist` nao expõe o caminho
    completo do executavel; usa-se Get-CimInstance via PowerShell, que expõe.
    """
    ps_cmd = (
        "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | "
        f"Where-Object {{ $_.ExecutablePath -eq '{terminal}' }} | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        saida = subprocess.run(  # noqa: S603
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [linha.strip() for linha in saida.splitlines() if linha.strip().isdigit()]


def terminal_aberto(terminal: Path | None = None) -> bool:
    """Ha um terminal MetaTrader em execucao nesta maquina?

    Se `terminal` for passado, filtra por caminho exato -- so conta a
    instalacao do White Rabbit, nunca outro projeto rodando na mesma
    maquina. Sem `terminal` (uso antigo, mantido por compatibilidade),
    tasklist por nome: nao distingue QUAL instalacao esta aberta -- so
    seguro numa maquina com uma unica instalacao de MT5.
    """
    if terminal is not None:
        return len(_pids_do_terminal(terminal)) > 0
    try:
        saida = subprocess.run(  # noqa: S603
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/NH"],
            capture_output=True, text=True, timeout=15, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "terminal64.exe" in saida.lower()


def fechar_terminal(espera: int = 45, terminal: Path | None = None) -> bool:
    """Fecha o terminal COM GRACA e espera ele sumir de verdade.

    /F destroi trabalho: o MT5 persiste definicao de simbolo custom e cache de
    otimizacao no encerramento limpo. Matar a forca ja deixou centenas de MB de
    ticks no disco para um simbolo que o tester passou a responder "not exist".
    So recorre ao /F depois de esperar -- preso e pior que forcado.

    Com `terminal` informado, fecha SO os PIDs daquele caminho exato (por
    /PID, nao /IM) -- nunca outra instalacao de MT5 rodando na mesma maquina.
    """
    if terminal is not None:
        for pid in _pids_do_terminal(terminal):
            subprocess.run(["taskkill", "/PID", pid],  # noqa: S603
                           capture_output=True, check=False)
        for _ in range(espera):
            time.sleep(1)
            if not terminal_aberto(terminal):
                time.sleep(2)
                return True
        for pid in _pids_do_terminal(terminal):
            subprocess.run(["taskkill", "/PID", pid, "/F"],  # noqa: S603
                           capture_output=True, check=False)
        time.sleep(3)
        return not terminal_aberto(terminal)

    subprocess.run(["taskkill", "/IM", "terminal64.exe"],  # noqa: S603
                   capture_output=True, check=False)
    for _ in range(espera):
        time.sleep(1)
        if not terminal_aberto():
            time.sleep(2)          # deixa o flush terminar
            return True
    subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"],  # noqa: S603
                   capture_output=True, check=False)
    time.sleep(3)
    return not terminal_aberto()


def garantir_terminal_livre(fechar: bool = False, terminal: Path | None = None) -> None:
    """Levanta se houver terminal aberto, ou fecha quando autorizado.

    Falhar aqui e MUITO melhor do que rodar: o custo de um erro visivel e
    reabrir o terminal; o custo do silencio e concluir coisa errada sobre uma
    estrategia a partir de um teste que nunca rodou.

    Passe `terminal` (o Path da instalacao do White Rabbit) para so
    checar/fechar essa instalacao especifica -- ver `_pids_do_terminal`.
    """
    if not terminal_aberto(terminal):
        return

    porque = ("Com o terminal em execucao o /config nao executa nada -- a "
              "janela apenas ganha foco, nenhum log e escrito, e o resultado "
              "vem vazio como se a estrategia nao tivesse operado.")

    if not fechar:
        raise SystemExit(f"Ha um MetaTrader aberto. Feche-o antes de rodar.\n"
                         f"{porque}\n"
                         "Use --fechar-terminal para fechar automaticamente.")

    if fechar_terminal(terminal=terminal):
        return

    # Mandar usar a flag que ja foi usada manda procurar no lugar errado: o
    # problema aqui nao e permissao, e algo REABRINDO o terminal. Foi o que
    # aconteceu ao deixar um orquestrador de campanha rodando -- ele subia
    # outro terminal a cada vez que este fechava.
    raise SystemExit(
        "Fechei o MetaTrader e ele voltou a aparecer.\n"
        f"{porque}\n"
        "Isso costuma significar que algo esta REABRINDO o terminal: outra "
        "campanha ou script ainda em execucao. Encerre o orquestrador antes "
        "do terminal -- na ordem inversa ele simplesmente abre outro.")


def lancar_terminal(terminal: Path, ini: Path, timeout: int | None,
                    *args_extra: str) -> None:
    """Roda `/config:` minimizado e SEM ativar -- nao rouba o foco de quem
    esta trabalhando na maquina.

    SW_SHOWMINNOACTIVE (7) mostra a janela minimizada sem trazer o processo
    pra frente nem tirar o foco da janela atual -- diferente de SW_MINIMIZE
    (6), que ativa antes de minimizar e ainda rouba o foco por um instante.
    O processo continua visivel na barra de tarefas; nada aqui esconde o
    terminal, so evita que ele interrompa o que esta em primeiro plano.

    2026-08-23: tres tentativas de ir alem disso (desktop virtual isolado,
    VM Hyper-V, restaurar foco + Enter sintetico) causaram problema NOVO
    cada uma -- respectivamente: Windows trocando o desktop ativo do dono
    junto (e corrompendo passes), estouro de RAM do host, e um Enter as
    cegas acertando o menu de pausa do jogo que o dono estava jogando e
    saindo dele. Revertido pra so isto -- e o unico nivel em que o codigo
    tem certeza do que esta fazendo. Nao tentar de novo sem um jeito de
    saber o ESTADO da janela alvo antes de mandar input pra ela.

    `args_extra` repassa flags adicionais (`/report:...` etc.) que alguns
    chamadores precisam junto do `/config:`.

    Nunca deixa `TimeoutExpired` escapar: achado do dono, 2026-08-06, um
    UNICO passe travado (o bug ja conhecido de processo que nao fecha a
    tempo, mesmo com o teste tendo terminado) derrubava o script inteiro
    com traceback -- jogando fora horas de estagio ja completo so porque
    UM passe de conferencia no meio do caminho nao respondeu a tempo.
    `subprocess.run(timeout=...)` ja mata o processo antes de levantar a
    excecao (documentado no proprio Python); todo chamador aqui ja
    descobre sucesso/falha lendo o LOG depois, nunca o retorno desta
    funcao -- entao engolir o timeout e seguro: o chamador ve o log sem
    a linha de bookkeeping do Tester e trata como qualquer outro passe
    incompleto, o mesmo caminho que ja existe pra log vazio ou estourado.

    `stdout`/`stderr` vao pro DEVNULL, nao capturados (dono, 2026-08-06,
    causa raiz do "processo nao fecha a tempo"): com `capture_output=True`
    o Python cria PIPEs e so retorna de `communicate()` quando eles fecham
    (EOF) -- e um processo DESCENDENTE do terminal (um dos agentes locais)
    que herda o handle do pipe e demora pra sair prende o Python esperando
    o PIPE, nao o processo principal. Confirmado no log do MT5: a
    otimizacao terminou limpa (genetic optimization finished, cache salvo,
    todos os cores com "connection closed") as 02:43:59, e mesmo assim o
    Python so retornou 9 HORAS depois. Ninguem le o retorno desta funcao
    (todo chamador confere pelo LOG do MT5, nunca por stdout/stderr) --
    DEVNULL nao cria esse pipe, entao nao ha o que prender.
    """
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    try:
        subprocess.run([str(terminal), f"/config:{ini}", *args_extra],  # noqa: S603
                       timeout=timeout, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False,
                       startupinfo=info)
    except subprocess.TimeoutExpired:
        pass


def ler_novo(logs_dir: Path, antes: dict[Path, int]) -> str:
    """Le so o que foi escrito nos logs depois de `antes`.

    O MT5 ANEXA todas as corridas no mesmo arquivo do dia; ler o arquivo inteiro
    faz cada corrida herdar as contagens das anteriores. Offset impar
    dessincroniza os pares de bytes do UTF-16LE.
    """
    if not logs_dir.is_dir():
        return ""
    partes = []
    for p in logs_dir.glob("*.log"):
        inicio = antes.get(p, 0)
        if p.stat().st_size <= inicio:
            continue
        with p.open("rb") as fh:
            fh.seek(inicio)
            bruto = fh.read()
        if inicio % 2:
            bruto = bruto[1:]
        partes.append(bruto.decode("utf-16-le", errors="replace"))
    return "\n".join(partes)


def marcar_logs(logs_dir: Path) -> dict[Path, int]:
    if not logs_dir.is_dir():
        return {}
    return {p: p.stat().st_size for p in logs_dir.glob("*.log")}
