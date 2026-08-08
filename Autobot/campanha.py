# -*- coding: utf-8 -*-
"""Roda o circuito de validacao em lote, de forma RESUMIVEL.

Cada combo custa ~20 min, e a campanha inteira nao cabe numa sessao. Entao o
progresso mora em disco (`campanha_resultados.jsonl`), nao na memoria do
processo: relancar o script pula o que ja foi medido e continua de onde parou.
Sem isso, qualquer interrupcao -- cota, queda de energia, reinicio -- custaria
todas as horas ja gastas.

ORDEM: por SISTEMA primeiro (grid abrindo a fila, depois peso igual pros
outros 10), simbolo por dentro -- ver o docstring de `fila()` para o porque
(9 simbolos .HT com tick real, o que virou default do autobot em 2026-08-02).

    python campanha.py                 # continua de onde parou
    python campanha.py --listar        # so mostra a fila
    python campanha.py --limite 5      # roda 5 combos e para
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import descobrir_ativos
import optimize_sets as base

AQUI = Path(__file__).resolve().parent
LEDGER = AQUI / "campanha_resultados.jsonl"

# Multi-ativo (dono, 2026-08-02): a lista de simbolos NUNCA e cravada aqui --
# uma lista fixa (ex.: "os 9 .HT do dono") so funciona na maquina de quem a
# escreveu. Em qualquer outro terminal os simbolos nao existem, o `/config:`
# falha em silencio, e o combo sai com "sem JSON final" (foi exatamente o
# que aconteceu com um usuario externo do Autobot publicado). Ver
# `descobrir_ativos.py`: auto-detecta o que este terminal/conta pode testar
# (nativo ou injetado via Historical Tool Manager, filtrado por saldo), a
# menos que o usuario tenha gravado uma lista propria em campanha_ativos.json.

# Ordem por TIER DE RISCO (dono, 2026-08-08, ver PLANO_TREINAMENTO_100_A_MILHAO.md
# secao 5): substitui a ordem antiga "grid primeiro" (prioridade de produto,
# 2026-08-02) porque o Modo Automatico precisa seguir a mesma diretriz que o
# dono ja aplicou manualmente -- RESEARCH primeiro (Fixed-R, validado por
# Monte Carlo, menor risco estrutural), HEDGE_ACCOUNT_REQUIRED depois (grid,
# so promovivel ao vivo com conta de hedging confirmada), HIGH_RISK e
# HIGH_RISK_RESEARCH por ultimo (o proprio status em generate_system_sets.py
# ja avisa). Essa e a ordem de MEDICAO; a ordem de GRADUACAO pra capital ao
# vivo e separada e documentada no plano. Continua sendo o DEFAULT (nenhuma
# flag = esta ordem, todos os 11); o modo manual do dashboard so
# filtra/reordena por cima disso via --sistemas.
SISTEMAS = ["01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL",
            "05_BE_TRAIL", "06_REVERSAL_EXIT",
            "07_GRID_SEPARATE", "08_GRID_UNIFIED",
            "09_MARTINGALE", "10_DALEMBERT", "11_SIGNAL_ONLY"]

# 08_GRID_UNIFIED e bilateral: opera os dois lados no mesmo passe, entao o set
# e BOTH_*. Os demais tem um set por lado.
BILATERAL = {"08_GRID_UNIFIED"}

# Cada "rodada" percorre os 11 sistemas com UMA variante antes de avancar. As
# ICHIMOKU entram DEPOIS das MULTI de proposito, nao por esquecimento como
# antes: a MULTI ja disputa 11 indicadores (0..10) no proprio genetico, entao
# ela rende o retrato mais largo por corrida -- mas o Ichimoku (11) vive em
# arquivo proprio (Tenkan<Kijun<SenkouB no OnInit), e sem estas rodadas ele
# era o unico indicador que NUNCA era testado.
RODADAS = [("BUY_MULTI", "BOTH_MULTI"), ("SELL_MULTI", None),
           ("BUY_ICHIMOKU", "BOTH_ICHIMOKU"), ("SELL_ICHIMOKU", None)]


def variantes(sistema: str) -> list[str]:
    duplo = sistema in BILATERAL
    return [b if duplo else a for a, b in RODADAS if not (duplo and b is None)]


def fila(simbolos: list[str], sistemas: list[str] | None = None) -> list[tuple[str, str, str]]:
    """Combos na ordem de execucao: SIMBOLO por fora, depois variante,
    depois SISTEMA por dentro (grid primeiro por default).

    `simbolos` vem de `descobrir_ativos` (auto-detectado ou escolhido pelo
    usuario) -- nunca uma lista cravada aqui, ver comentario acima.
    `sistemas` e opcional: None usa o SISTEMAS default (todos os 11, grid
    primeiro); passado explicitamente (modo manual do dashboard, ou
    `--sistemas` na CLI), filtra E define a ordem -- quem chama decide a
    prioridade, a funcao so respeita.

    Invertido de "sistema por fora" pra "simbolo por fora" (dono, 2026-08-05):
    a ordem antiga (2026-08-02) processava 1 combo de cada simbolo por
    rodada antes de repetir -- resiliente a interrupcao (todo ativo ganha
    alguma cobertura cedo), mas visto ao vivo parecia os simbolos
    "brigando" pra ver quem termina primeiro (AUDCAD sumia da tela por
    varios combos de outros ativos antes de reaparecer). Prioridade agora e
    "terminar o ativo escolhido do inicio ao fim" antes do proximo -- o
    custo e que uma interrupcao no meio deixa os ativos seguintes com
    cobertura zero, nao parcial.
    """
    sistemas = sistemas if sistemas is not None else SISTEMAS
    itens = []
    for simbolo in simbolos:
        for unilateral, bilateral in RODADAS:
            for sistema in sistemas:
                v = bilateral if sistema in BILATERAL else unilateral
                if v is None:              # bilateral nao tem BUY_* proprio
                    continue
                if base.achar_set(simbolo, sistema, v) is not None:
                    itens.append((simbolo, sistema, v))
    return itens


def feitos() -> set[tuple[str, str, str]]:
    """Combos ja com resultado definitivo no ledger.

    Exclui entradas com "erro" (rodar_combo() grava isso quando o processo
    nunca imprimiu um JSON final -- crash antes de qualquer resultado real,
    ex.: cache de conta ausente antes do fix de 2026-08-08). Achado real,
    2026-08-08: um comprador com combos travados assim antes do fix nunca
    via a campanha tentar de novo mesmo depois de corrigido, porque
    "feitos" nao distinguia "nunca rodou de verdade" de "rodou e foi
    reprovado". Nao da pra usar retencao_oos=None como sinal disso: uma
    reprovacao LEGITIMA do Estagio 1/2/4 (emitir_reprovado_cedo, sem
    candidato que passasse o piso) tambem grava retencao_oos None, e essa
    tem que continuar "feita" pra sempre -- repeti-la seria desperdicar
    horas re-testando um combo que ja provou nao ter estrategia viavel.
    "erro" so aparece na falha de infraestrutura, nunca na reprovacao.
    """
    if not LEDGER.exists():
        return set()
    vistos = set()
    for linha in LEDGER.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            r = json.loads(linha)
        except json.JSONDecodeError:
            # Uma linha truncada (queda no meio da escrita) nao pode derrubar a
            # leitura do resto do ledger -- so aquele combo volta para a fila.
            continue
        if "erro" in r:
            continue
        chave = (r.get("simbolo"), r.get("sistema"), r.get("variante"))
        if None in chave:
            # Linha valida como JSON mas sem os campos de identidade --
            # nao deveria acontecer (todo caminho que grava aqui, sucesso
            # ou "erro", sempre inclui os tres), mas nao vale travar
            # feitos() inteiro (e a campanha junto) por uma linha
            # corrompida de um jeito que nao virou JSONDecodeError.
            continue
        vistos.add(chave)
    return vistos


def registrar(reg: dict) -> None:
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")


def rodar_combo(simbolo: str, sistema: str, variante: str, args) -> dict:
    # --period M1 explicito (dono, 2026-07-31): obrigatorio em todos os
    # algoritmos porque cada indicador carrega o proprio TF via input -- com
    # o chart period != M1, qualquer input "Current TF" colapsaria pro period
    # do chart. O default de optimize_two_stage.py ja e M1, mas nao vale a
    # pena depender disso silenciosamente aqui.
    cmd = [sys.executable, str(AQUI / "optimize_two_stage.py"),
           "--symbol", simbolo, "--sistema", sistema, "--variante", variante,
           "--period", "M1",
           "--from", args.inicio, "--to", args.fim,
           "--deposit", str(args.deposit),
           "--min-retencao", str(args.min_retencao),
           "--fechar-terminal", "--timeout", str(args.timeout)]
    t0 = time.time()
    # CREATE_NO_WINDOW: so suprime a janela de console que este python.exe
    # filho abriria sozinho (achado do dono, 2026-08-06 -- cada combo novo
    # roubava foco/atrapalhava outros apps). Continua visivel no Task
    # Manager e matavel normalmente.
    #
    # Popen + thread de leitura, nao mais subprocess.run(capture_output=True)
    # (achado do dono, 2026-08-07): capture_output bufferiza TUDO em memoria
    # e so devolve quando o filho termina -- durante um combo de horas (grid
    # facilmente passa de 2h so no Estagio 1), campanha_run.log ficava sem
    # NENHUMA linha nova ate o combo inteiro acabar, mesmo com
    # optimize_two_stage.py imprimindo progresso o tempo todo por dentro.
    # Sem visibilidade, um combo lento parece indistinguivel de travado --
    # ja custou um combo de 135min morto por engano por parecer sem
    # atividade. `print(linha, flush=True)` agora acontece LINHA A LINHA,
    # assim que o filho escreve -- e dashboard_campanha.py ja grava o stdout
    # deste script em tempo real no LOG, entao a linha aparece la na hora.
    processo = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace",
                                creationflags=subprocess.CREATE_NO_WINDOW)
    linhas: list[str] = []

    def _ler_e_ecoar() -> None:
        assert processo.stdout is not None
        for linha in processo.stdout:
            linha = linha.rstrip("\n")
            print(linha, flush=True)
            linhas.append(linha)

    # Thread separada pra leitura: o timeout abaixo precisa disparar mesmo
    # se o filho parar de escrever por completo (travado de verdade, nao so
    # lento) -- `Popen.wait(timeout=...)` nao bloqueia esperando dado no
    # pipe, ao contrario de iterar `processo.stdout` direto na thread
    # principal.
    leitor = threading.Thread(target=_ler_e_ecoar, daemon=True)
    leitor.start()
    try:
        returncode = processo.wait(timeout=args.timeout + 600)
    except subprocess.TimeoutExpired:
        processo.kill()
        returncode = processo.wait()
    leitor.join(timeout=10)
    saida = "\n".join(linhas)

    # O JSON final e a ULTIMA linha que abre com '{'. Procurar a primeira
    # pegaria qualquer dict impresso no meio do caminho (o sinal travado, por
    # exemplo) e registraria um combo como se fosse resultado.
    reg = None
    for linha in reversed(saida.splitlines()):
        if linha.startswith("{"):
            try:
                reg = json.loads(linha)
                break
            except json.JSONDecodeError:
                continue
    if reg is None:
        reg = {"simbolo": simbolo, "sistema": sistema, "variante": variante,
               "erro": "sem JSON final", "returncode": returncode}
    reg["minutos"] = round((time.time() - t0) / 60, 1)
    reg["quando"] = datetime.now().isoformat(timespec="seconds")
    reg["aprovado"] = "VALIDADO" in saida and "REPROVADO: nao promova" not in saida
    return reg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="inicio", default="2023.08.01")
    ap.add_argument("--to", dest="fim", default=datetime.now().strftime("%Y.%m.%d"))
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--min-retencao", type=float, default=30.0)
    ap.add_argument("--timeout", type=int, default=43200)
    ap.add_argument("--limite", type=int, default=0, help="0 = sem limite")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--sistemas", default="",
                    help="lista separada por virgula, filtra e ordena "
                         "(ex.: 07_GRID_SEPARATE,01_SLTP); vazio = os 11 default")
    ap.add_argument("--simbolos", default="",
                    help="lista separada por virgula, sobrepoe a "
                         "auto-deteccao/campanha_ativos.json so nesta corrida")
    args = ap.parse_args()

    if args.simbolos.strip():
        simbolos = [s.strip() for s in args.simbolos.split(",") if s.strip()]
    else:
        simbolos = descobrir_ativos.carregar_ou_descobrir()
    if not simbolos:
        print("Sem simbolos elegiveis -- nada a rodar.", flush=True)
        return 1

    sistemas = ([s.strip() for s in args.sistemas.split(",") if s.strip()]
                if args.sistemas.strip() else None)
    if sistemas:
        desconhecidos = [s for s in sistemas if s not in SISTEMAS]
        if desconhecidos:
            print(f"--sistemas com codigo(s) desconhecido(s): {desconhecidos}",
                  flush=True)
            return 1

    todos = fila(simbolos, sistemas)
    ja = feitos()
    pendentes = [c for c in todos if c not in ja]
    print(f"campanha: {len(todos)} combos | {len(ja)} feitos | "
          f"{len(pendentes)} pendentes", flush=True)
    if args.listar:
        for i, (s, sis, v) in enumerate(pendentes, 1):
            print(f"  {i:3}. {s:<12} {sis:<18} {v}")
        return 0

    feitos_agora = 0
    for simbolo, sistema, variante in pendentes:
        if args.limite and feitos_agora >= args.limite:
            print(f"limite de {args.limite} atingido; parando.", flush=True)
            break
        print(f"\n{'=' * 70}\n[{feitos_agora + 1}/{len(pendentes)}] "
              f"{simbolo} {sistema} {variante}\n{'=' * 70}", flush=True)
        try:
            reg = rodar_combo(simbolo, sistema, variante, args)
        except subprocess.TimeoutExpired:
            reg = {"simbolo": simbolo, "sistema": sistema, "variante": variante,
                   "erro": "timeout", "quando": datetime.now().isoformat(timespec="seconds")}
        # Grava SEMPRE, inclusive erro: um combo que falha e informacao, e sem
        # registro ele voltaria para a fila em toda relancada, travando a
        # campanha no mesmo ponto para sempre.
        registrar(reg)
        # O espelho de prontos acompanha o ledger combo a combo -- e depois de
        # um VALIDADO que ele muda, mas rodar sempre tambem apaga marcador de
        # combo recorrido que reprovou. Falha aqui e avisada em voz alta e nao
        # derruba a campanha: o espelho se reconstroi inteiro na proxima
        # passada (ou via `python ready_library.py`).
        try:
            import ready_library
            ready_library.sincronizar()
        except Exception as exc:                     # noqa: BLE001
            print(f"AVISO: espelho de prontos nao sincronizou: {exc}",
                  flush=True)
        feitos_agora += 1
        marca = "APROVADO" if reg.get("aprovado") else "reprovado"
        print(f"-> {marca} | retencao={reg.get('retencao_oos')} "
              f"| {reg.get('minutos')} min", flush=True)

    print(f"\ncampanha: {feitos_agora} combos nesta rodada. "
          f"Ledger: {LEDGER.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
