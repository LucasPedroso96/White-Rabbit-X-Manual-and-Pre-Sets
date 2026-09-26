# -*- coding: utf-8 -*-
"""Painel de controle do Autobot -- unico ponto pra rodar tudo.

Junta o que antes era so linha de comando: iniciar/parar a campanha (modo
automatico ou manual, escolhendo sistema e ativo por caixinha), regenerar a
biblioteca de sets, sincronizar o perfil da corretora (`auto_set_manager.py`),
ver os portfolios prontos e medir custo nativo -- tudo pela mesma tela.

Duas categorias de acao, por causa do tempo que cada uma leva:

  SINCRONA   `/api/status`, `/api/config`, `/api/biblioteca`, `/api/portfolios`,
             `/api/custo-nativo`, `/api/perfil` -- so leem arquivo, respondem
             na hora.
  ASSINCRONA `POST /api/.../...` que dispara um subprocesso (alguns levam
             minutos, ex.: medir custo nativo roda um passe real no Strategy
             Tester) -- devolvem um job_id na hora, o front consulta
             `GET /api/jobs/{id}` ate `status` virar "feito"/"erro".

GUARDA-CORPO: nenhuma acao que toca o MT5 roda se outra ja estiver em
andamento -- `mt5_runner.terminal_aberto(base.TERMINAL)` e a fonte da verdade (nao um
lockfile proprio, que poderia mentir se algo travou fora do painel).

Uso:
    python dashboard_campanha.py                # porta 8020
    python dashboard_campanha.py --port 8021
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

_FALTANDO = [pacote for pacote in
             ("fastapi", "uvicorn", "numpy", "pandas", "MetaTrader5")
             if find_spec(pacote) is None]
if _FALTANDO:
    # Rodando com o Python do proprio comprador (fora do .exe empacotado,
    # que ja vem com tudo instalado) -- ModuleNotFoundError cru no meio de
    # um import em cascata nao diz o que fazer nem o resto que falta. Checa
    # tudo de uma vez, antes de qualquer import de terceiro, e manda o
    # comando exato. Achado real, 2026-08-08: cliente rodou isto direto sem
    # ter instalado as dependencias primeiro.
    print(f"ERRO: dependencia(s) ausente(s): {', '.join(_FALTANDO)}")
    print("Rode:")
    print(f"  pip install -r \"{Path(__file__).resolve().parent / 'requirements.txt'}\"")
    sys.exit(1)

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import optimize_sets as base
import campanha
import campeoes_arquivo
import ready_library
import relatorio_resumo
import auto_manager_live
import em_prova
import wrx_paths
from generate_system_sets import ASSETS, CLASSES, SYSTEMS
from mt5_runner import fechar_terminal, terminal_aberto
from optimize_two_stage import conferir_set

AQUI = Path(__file__).resolve().parent
LEDGER = AQUI / "campanha_resultados.jsonl"
LOG = AQUI / "campanha_run.log"
LOCK = AQUI / "campanha_dashboard.lock.json"
PERFIL_ATUAL = AQUI / "perfil_dashboard.json"
# Escrito por optimize_two_stage.py (achado do dono, 2026-08-07): estagio/
# rodada/finalista atual do combo em andamento, pra nao depender de abrir o
# log bruto do MT5 pra saber se uma campanha lenta esta progredindo ou
# travada.
PROGRESSO = AQUI / "campanha_progresso.json"
# Escrito por optimize_two_stage.py (achado do dono, 2026-08-07): estagio/
# rodada/finalista atual do combo em andamento, pra nao depender de abrir o
# log bruto do MT5 pra saber se uma campanha lenta esta progredindo ou
# travada.
PROGRESSO = AQUI / "campanha_progresso.json"
CUSTO_CACHE = AQUI / "_custo_nativo.json"
SETS_IMPLANTADOS = AQUI / "sets_implantados.json"
RELATORIOS_DIR = AQUI / "campanha_relatorios"
RELATORIOS_DIR.mkdir(exist_ok=True)
PORTFOLIO_OUT = AQUI / "portfolio_outputs"
PORTFOLIO_OUT.mkdir(exist_ok=True)

app = FastAPI(title="WRX Autobot Dashboard")
# Cada rota so serve a PROPRIA pasta -- nunca a raiz de DADOS (MT5) nem AQUI
# (fonte/ledger/credenciais).
app.mount("/relatorios", StaticFiles(directory=str(RELATORIOS_DIR)), name="relatorios")
app.mount("/portfolio-out", StaticFiles(directory=str(PORTFOLIO_OUT)), name="portfolio_out")

# ------------------------------------------------------------- estado global

_processo: subprocess.Popen | None = None  # so valido no MESMO processo do
# uvicorn -- ver estado_campanha()
# para o caso de o painel reiniciar
_jobs: dict[str, dict] = {}
# Achado do dono, 2026-08-05: duplo-clique (ou 2 requests quase simultaneos)
# em "Iniciar Corrida" passava os DOIS pela checagem de estado_campanha()
# ANTES de qualquer um escrever o LOCK/lancar o Popen -- TOCTOU classico,
# resultou em 2 campanha.py rodando a MESMA fila em paralelo, cada um
# abrindo seu proprio terminal64.exe (visto brigando por AUDCAD/CADCHF).
_lock_start = threading.Lock()


def _executar_job(job_id: str, cmd: list[str], timeout: int) -> None:
    _jobs[job_id]["status"] = "rodando"
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _jobs[job_id].update(
            {
                "status": "feito" if p.returncode == 0 else "erro",
                "saida": (p.stdout or "") + (p.stderr or ""),
                "codigo": p.returncode,
            }
        )
    except subprocess.TimeoutExpired:
        _jobs[job_id].update({"status": "erro", "saida": "estourou o tempo limite"})
    except Exception as exc:  # noqa: BLE001 -- job em thread nao pode matar o servidor
        _jobs[job_id].update({"status": "erro", "saida": str(exc)})
    _jobs[job_id]["terminado_em"] = datetime.now().isoformat(timespec="seconds")


def lancar_job(cmd: list[str], timeout: int = 600) -> str:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {
        "status": "iniciado",
        "cmd": cmd,
        "iniciado_em": datetime.now().isoformat(timespec="seconds"),
    }
    threading.Thread(
        target=_executar_job, args=(job_id, cmd, timeout), daemon=True
    ).start()
    return job_id


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> JSONResponse:
    return JSONResponse(_jobs.get(job_id, {"status": "desconhecido"}))


# --------------------------------------------------------------- ledger/log


def ler_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    linhas = []
    for linha in LEDGER.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            linhas.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return linhas


def limpar_ledger_incompleto() -> int:
    """Remove entradas 'sem JSON final' (combo interrompido no meio) -- sem
    isso o combo fica preso como 'feito' e nunca e refeito de verdade. Mesma
    limpeza que tive que fazer a mao repetidas vezes nesta sessao.

    Guarda de seguranca (achado 2026-08-09): um dia inteiro de resultados
    aprovados (XAUUSD.HT/08_GRID_UNIFIED, madrugada de 08/08 -- retencao
    361% e 143%, sobreviveram ao periodo completo) sumiu do ledger em algum
    momento sem deixar rastro de erro. Esta e a UNICA funcao do projeto que
    reescreve o arquivo inteiro (tudo o resto so acrescenta linha por linha
    via campanha.registrar()); se ela rodar contra uma leitura ruim (corrida
    concorrente com o subprocesso da campanha ainda escrevendo, por exemplo)
    o resultado antigo era sobrescrever tudo silenciosamente, sem copia pra
    recuperar. Agora: sempre faz backup antes de escrever, e recusa a
    escrita se o corte pareceria remover mais de 20% das linhas de uma vez
    (isso nunca deveria acontecer so por combos incompletos -- normalmente
    0 ou 1 por Stop; um corte grande e sinal de leitura ruim, nao de ledger
    sujo de verdade).

    2026-09-26: leitura+reescrita agora sob a MESMA trava de
    campanha.registrar(). Com campanhas CLI gravando no ledger ao mesmo
    tempo, uma linha acrescentada entre a leitura e a escrita sumia, e uma
    linha pela METADE (sendo escrita) era removida como JSON corrompido."""
    with campanha._lock_ledger():
        return _limpar_ledger_incompleto_sob_trava()


def _limpar_ledger_incompleto_sob_trava() -> int:
    if not LEDGER.exists():
        return 0
    todas = LEDGER.read_text(encoding="utf-8").splitlines()
    boas, removidas = [], 0
    for linha in todas:
        if not linha.strip():
            continue
        try:
            r = json.loads(linha)
        except json.JSONDecodeError:
            removidas += 1
            continue
        if r.get("erro") == "sem JSON final":
            removidas += 1
            continue
        boas.append(linha)
    if not removidas:
        return 0
    if len(todas) >= 10 and removidas > len(todas) * 0.2:
        print(f"limpar_ledger_incompleto: recusando remover {removidas}/"
              f"{len(todas)} linhas de uma vez (parece leitura ruim, nao "
              "combos incompletos) -- ledger nao mexido.", flush=True)
        return 0
    shutil.copy2(LEDGER, LEDGER.with_suffix(".jsonl.bak"))
    LEDGER.write_text("\n".join(boas) + ("\n" if boas else ""), encoding="utf-8")
    return removidas


def resumo_qualidade(resultados: list[dict]) -> dict:
    """Consolida o que o ledger já conhece sobre robustez do passe atual.

    WFE e MC nao aparecem em todos os registros; quando nao existe a metrica
    o painel mostra o estado conforme o dado coletado, sem inventar valor.
    """
    total = len(resultados)
    if not total:
        return {
            "mc_pass_rate": None,
            "mc_medidos": 0,
            "mc_cobertura_pct": 0.0,
            "retencao_media": None,
            "lucro_medio_tick_real": None,
            "wfe_status": "sem relatorio no ledger",
            "mc_status": "sem resultado no ledger",
        }

    # mc_aprovado comeca True por padrao pra nao reprovar sistemas
    # estruturalmente isentos de MC (grid/martingale/d'Alembert) -- por isso
    # o pass rate so soma sobre linhas com mc_medido=True (Monte Carlo rodou
    # de verdade), nunca sobre o default. Linhas de antes desse campo existir
    # ficam de fora tambem (mc_medido ausente): tratar como "desconhecido" e
    # mais honesto do que contar como medido.
    medidos = [r for r in resultados if r.get("mc_medido") is True]
    mc_ok = sum(1 for r in medidos if r.get("mc_aprovado") is True)
    retencoes = [
        float(r["retencao_oos"])
        for r in resultados
        if r.get("retencao_oos") is not None
    ]
    lucros = [
        float(r["lucro_tick_real"])
        for r in resultados
        if r.get("lucro_tick_real") is not None
    ]
    wfe_disponivel = any(r.get("wfe") is not None for r in resultados)

    return {
        "mc_pass_rate": (
            round((mc_ok / len(medidos)) * 100.0, 1) if medidos else None
        ),
        "mc_medidos": len(medidos),
        "mc_cobertura_pct": round((len(medidos) / total) * 100.0, 1) if total else 0.0,
        "retencao_media": (
            round(sum(retencoes) / len(retencoes), 2) if retencoes else None
        ),
        "lucro_medio_tick_real": (
            round(sum(lucros) / len(lucros), 2) if lucros else None
        ),
        "wfe_status": (
            "relatorio WFE presente"
            if wfe_disponivel
            else "sem relatorio WFE no ledger"
        ),
        "mc_status": (
            f"Monte Carlo medido em {len(medidos)} de {total} combos"
            if medidos
            else "Monte Carlo ainda nao mediu nenhum combo (fora de Fixed-R "
                 "ou poucos trades)"
        ),
    }


_HEADER = re.compile(r"\[(\d+)/(\d+)\]\s+(\S+)\s+(\S+)\s+(\S+)")
_VEREDITO = re.compile(r"^-> (aprovado|reprovado) \| retencao=(\S+) \| ([\d.]+) min")


def combo_atual() -> dict | None:
    if not LOG.exists():
        return None
    linhas = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    ultimo_i = ultimo = None
    for i, linha in enumerate(linhas):
        m = _HEADER.search(linha)
        if m:
            ultimo_i, ultimo = i, m
    if ultimo is None:
        return None
    resto = linhas[ultimo_i:]
    if any(_VEREDITO.match(linha) for linha in resto):
        return None
    n, total, simbolo, sistema, variante = ultimo.groups()
    estagio = ""
    for linha in reversed(resto[1:]):
        limpa = linha.strip()
        if limpa and not limpa.startswith("="):
            estagio = limpa
            break
    return {
        "posicao": f"{n}/{total}",
        "simbolo": simbolo,
        "sistema": sistema,
        "variante": variante,
        "estagio": estagio,
    }


@app.get("/api/status")
def status(familia: str = "MULTI") -> JSONResponse:
    """`familia` ("MULTI", "ICHIMOKU", "BOLLINGER" ou "CANDLES") filtra o
    ledger pela familia de variante -- ver ready_library.familia_da_variante()
    -- para o dashboard mostrar cada modo como uma campanha independente.

    Uma linha por COMBO (a ultima vence, mesma regra de
    ready_library.metricas_do_ledger) -- o ledger e append-only: rebaixar
    um campeao, refazer um combo interrompido ou revalidar acrescenta
    linha, nunca apaga a antiga. Contar linhas cruas (achado 2026-09-25)
    mantinha os 2 campeoes GBPUSD rebaixados em 21/09 no contador de
    aprovados e contava cada combo refeito duas vezes."""
    ultimo_por_combo: dict[tuple[str, str, str], dict] = {}
    for r in ler_ledger():
        if ready_library.familia_da_variante(r.get("variante", "")) != familia:
            continue
        chave = (str(r.get("simbolo", "")).replace(".", "_"),
                 r.get("sistema", ""), r.get("variante", ""))
        ultimo_por_combo.pop(chave, None)   # reinsere no fim: ordem = recencia
        ultimo_por_combo[chave] = r
    resultados = list(ultimo_por_combo.values())
    aprovados = [r for r in resultados if r.get("aprovado")]
    por_sistema: dict[str, dict[str, int]] = {}
    for r in resultados:
        s = r.get("sistema", "?")
        d = por_sistema.setdefault(s, {"total": 0, "aprovados": 0})
        d["total"] += 1
        if r.get("aprovado"):
            d["aprovados"] += 1
    return JSONResponse(
        {
            "familia": familia,
            "total_feitos": len(resultados),
            "aprovados": len(aprovados),
            "reprovados": len(resultados) - len(aprovados),
            "por_sistema": por_sistema,
            "atual": combo_atual(),
            "recentes": [_com_aviso_bug_oos(r)
                         for r in list(reversed(resultados))[:30]],
            "qualidade": resumo_qualidade(resultados),
        }
    )


# EA com a entrada bloqueada nas janelas OOS em 'In Sample + Out Sample'
# (regressao de 13/09, corrigida 26/09 02:05 -- ver sonda_oos.py): toda
# retencao medida nesse intervalo e vazamento de borda, e o combo esta na
# fila de refacao. O painel marca em vez de esconder.
JANELA_BUG_OOS = ("2026-09-13", "2026-09-26T02:06")


def _com_aviso_bug_oos(r: dict) -> dict:
    quando = str(r.get("quando", ""))
    if (JANELA_BUG_OOS[0] <= quando < JANELA_BUG_OOS[1]
            and r.get("retencao_oos") is not None):
        return {**r, "aviso_bug_oos": True}
    return r


# ---------------------------------------------------------------- /api/config


@app.get("/api/config")
def config(familia: str = "MULTI") -> JSONResponse:
    capital = ready_library.capital_por_sistema(familia=familia)
    sistemas = [{
        "code": s.code, "label": s.label, "status": s.status,
        "capital_agregado": capital.get(s.code, 0.0),
        "capital_aplica": s.code in ready_library.SISTEMAS_R_CAPAZES,
    } for s in SYSTEMS]
    # Desempate pelo CODIGO (01, 02, 03...), nao pelo label: com capital
    # empatado -- o caso comum antes de haver sets validados, tudo em 0.0 --
    # desempatar por label embaralhava a lista (ex.: 05, 10, 08, 07...) sem
    # nenhuma ordem reconhecivel. Pelo codigo, o empate cai na ordem natural
    # numerada em que os sistemas ja sao declarados.
    sistemas.sort(key=lambda s: (0 if s["capital_agregado"] > 0 else 1,
                                  -s["capital_agregado"], s["code"]))
    # numero_exibicao (dono, 2026-09-07: "ainda nao existe sistema 8!"): so
    # cosmetico -- sequencial 1..N na ordem ja decidida acima, nunca troca
    # `code` (que continua "01_SLTP".."12_GRID_INVERSO", o identificador real
    # usado em toggleSistema()/achar_set()/nomes de arquivo). O buraco no 08
    # e historico de proposito (08_GRID_UNIFIED foi removido, ver comentario
    # em generate_system_sets.py) -- renumerar o codigo de verdade invalidaria
    # templates/VALIDADO_/ledger/memoria que ja usam 09/10/11/12. Isto so
    # tira o "buraco" que aparece NA TELA.
    for i, s in enumerate(sistemas, start=1):
        s["numero_exibicao"] = i
    classes = {
        codigo: {"capital_base": CLASSES[codigo].capital_base, "ativos": ativos}
        for codigo, ativos in ASSETS.items()
    }
    return JSONResponse({"sistemas": sistemas, "classes": classes})


# --------------------------------------------------------------- /api/heatmap


def _simbolo_base(simbolo: str) -> str:
    return simbolo.split(".")[0] if "." in simbolo else simbolo


def montar_heatmap(resultados: list[dict]) -> dict:
    """Cruza simbolo x sistema pra responder 'onde ja foi feito'. Uma celula
    pode ter varias variantes (BUY/SELL, MULTI/ICHIMOKU) -- aprovado vence
    (uma variante boa ja justifica o par), reprovado so aparece se NENHUMA
    variante testada passou."""
    celulas: dict[str, dict[str, dict]] = {}
    for r in resultados:
        base_symb = _simbolo_base(r.get("simbolo", ""))
        sistema = r.get("sistema")
        if not base_symb or not sistema:
            continue
        c = celulas.setdefault(base_symb, {}).setdefault(
            sistema, {"testados": 0, "aprovados": 0, "melhor_retencao": None}
        )
        c["testados"] += 1
        if r.get("aprovado"):
            c["aprovados"] += 1
            ret = r.get("retencao_oos")
            if ret is not None and (
                c["melhor_retencao"] is None or ret > c["melhor_retencao"]
            ):
                c["melhor_retencao"] = ret

    sistemas_codigos = [s.code for s in SYSTEMS]
    classes: dict[str, dict] = {}
    for codigo_classe, ativos in ASSETS.items():
        linhas = []
        for simbolo in ativos:
            por_sistema = celulas.get(simbolo, {})
            if not por_sistema:
                continue  # sem nenhum resultado ainda -- nao polui o mapa
            celula_linha = {}
            for sc in sistemas_codigos:
                info = por_sistema.get(sc)
                if not info:
                    celula_linha[sc] = {"status": "sem_teste"}
                elif info["aprovados"] > 0:
                    celula_linha[sc] = {"status": "aprovado", **info}
                else:
                    celula_linha[sc] = {"status": "reprovado", **info}
            linhas.append({"simbolo": simbolo, "celulas": celula_linha})
        if linhas:
            classes[codigo_classe] = {"ativos": linhas}
    return {"sistemas": sistemas_codigos, "classes": classes}


@app.get("/api/heatmap")
def heatmap() -> JSONResponse:
    return JSONResponse(montar_heatmap(ler_ledger()))


# ------------------------------------------------------------ campanha start/stop


def _pid_vivo(pid: int) -> bool:
    """Confere um PID pelo tasklist -- necessario porque `_processo` (Popen
    em memoria) se perde toda vez que o PROPRIO painel reinicia, mesmo com a
    campanha real continuando rodando num processo separado. Sem isso, um
    restart do dashboard (ex.: pra aplicar uma correcao) mostrava "parada"
    com o botao Stop desabilitado enquanto ela seguia rodando de verdade."""
    try:
        saida = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=10, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return str(pid) in saida


_CLI = {"quando": 0.0, "lista": []}
_CLI_LOCK = threading.Lock()


def _atualizar_campanhas_cli() -> None:
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR "
          "Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match "
          "'campanha\\.py' } | Select-Object ProcessId,CommandLine | "
          "ConvertTo-Json -Compress")
    try:
        saida = subprocess.run(  # noqa: S603
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=20, check=False).stdout.strip()
        dados = json.loads(saida) if saida else []
        if isinstance(dados, dict):
            dados = [dados]
        lista = []
        for d in dados:
            m = re.search(r"campanha\.py\"?\s*(.*)$", d.get("CommandLine") or "")
            lista.append({"pid": d.get("ProcessId"),
                          "args": (m.group(1) if m else "")[:300]})
        _CLI["lista"] = lista
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    finally:
        _CLI_LOCK.release()


def campanhas_cli() -> list[dict]:
    """campanha.py rodando FORA do painel (linha de comando, 2 instalacoes em
    paralelo). Achado 2026-09-25: o selo dizia "Campaign: stopped" com duas
    campanhas rodando -- o painel so conhecia a que ele mesmo lancou.
    Get-CimInstance leva ~1 s: cache de 30 s atualizado em thread, o polling
    de 8 s nunca espera por ele."""
    if time.time() - _CLI["quando"] > 30 and _CLI_LOCK.acquire(blocking=False):
        _CLI["quando"] = time.time()
        threading.Thread(target=_atualizar_campanhas_cli, daemon=True).start()
    return _CLI["lista"]


def estado_campanha() -> dict:
    vivo = False
    info: dict = {}
    if LOCK.exists():
        try:
            info = json.loads(LOCK.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            info = {}
    if _processo is not None and _processo.poll() is None:
        vivo = True
    elif info.get("pid") and _pid_vivo(info["pid"]):
        vivo = True
    progresso = None
    if PROGRESSO.exists():
        try:
            progresso = json.loads(PROGRESSO.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            progresso = None
    # "pausado": ultimo progresso gravado foi exatamente o marcador que
    # optimize_two_stage.py escreve ao honrar uma pausa (estagio="pausado",
    # ver linha ~1327 la) -- mais confiavel que so "LOCK existe e nao esta
    # rodando", que tambem seria verdade apos uma campanha terminar todos
    # os combos sozinha (LOCK so e apagado pelo Stop, nunca ao concluir).
    pausado = (not vivo and LOCK.exists() and bool(progresso)
              and progresso.get("estagio") == "pausado")
    proprio = {info.get("pid"), _processo.pid if _processo is not None else None}
    cli = [c for c in campanhas_cli() if c["pid"] not in proprio]
    return {"rodando": vivo, "terminal_aberto": terminal_aberto(base.TERMINAL),
           # PROGRESSO e global (last-writer-wins): com campanha CLI rodando
           # ele mostra a que gravou por ultimo -- melhor que nada.
           "progresso": progresso if (vivo or cli) else None,
           "pausando": (vivo or bool(cli)) and base.PAUSA.exists(),
           "pausado": pausado,
           **info,
           "campanhas_cli": cli,
           # Sinal de pausa gravado (vale pra TODAS as campanhas, inclusive
           # as filas CLI, que param antes da proxima etapa).
           "pausa_pendente": base.PAUSA.exists()}


@app.get("/api/campanha/estado")
def campanha_estado() -> JSONResponse:
    return JSONResponse(estado_campanha())


@app.post("/api/campanha/start")
def campanha_start(body: dict) -> JSONResponse:
    global _processo
    # Nao-bloqueante de proposito: se ja tem uma request de start em curso,
    # rejeita na hora em vez de esperar -- so precisa fechar a janela entre
    # "estado_campanha() disse que nao ha nada rodando" e "Popen+LOCK
    # gravados", nao serializar starts legitimos um atras do outro.
    if not _lock_start.acquire(blocking=False):
        return JSONResponse(
            {"ok": False, "erro": "outro start ja esta em andamento"},
            status_code=409,
        )
    try:
        if estado_campanha()["rodando"]:
            return JSONResponse(
                {"ok": False, "erro": "ja ha uma corrida rodando"}, status_code=409
            )
        if terminal_aberto(base.TERMINAL):
            return JSONResponse(
                {"ok": False, "erro": "MT5 ocupado por outra acao -- espere terminar"},
                status_code=409,
            )
        return _lancar_campanha(body)
    finally:
        _lock_start.release()


def _lancar_campanha(body: dict) -> JSONResponse:
    global _processo
    modo = body.get("modo", "auto")
    cmd = [
        sys.executable,
        str(AQUI / "campanha.py"),
        "--to",
        body.get("fim") or datetime.now().strftime("%Y.%m.%d"),
        "--min-retencao",
        str(body.get("min_retencao", 30.0)),
        "--timeout",
        # 43200 (12h): 21600 (6h) nao bastou pro primeiro combo depois da
        # limpeza do cache do tester -- 3 rodadas do estagio 1 sozinhas
        # consumiram 6h10 com o cache frio (AUDCAD/07_GRID_SEPARATE,
        # 2026-08-05). Com cache quente sobra folga; a campanha continua
        # regravando e seguindo em frente mesmo se um combo estourar isso.
        str(body.get("timeout", 43200)),
        "--familia",
        body.get("familia", "MULTI"),
    ]
    # Modo Economico (dono, 2026-09-07): compra+venda juntos (Hedge) em vez
    # de BUY/SELL separados, pros sistemas em campanha.BILATERAL -- ver
    # campanha.variantes()/fila(). Default False preserva o fluxo de sempre.
    if body.get("modo_economico"):
        cmd += ["--modo-economico"]
    # Estagio 0 (dono, 2026-09-10): rankeia a entrada (11_SIGNAL_ONLY, sem
    # nenhuma administracao) por ativo/lado antes dos sistemas de verdade --
    # ver rankear_entradas.py. Default False preserva o fluxo de sempre.
    if body.get("rankear_entrada_primeiro"):
        cmd += ["--rankear-entrada-primeiro"]
    # Camada de recuperacao (dono, 2026-09-08/09): booster opcional
    # Martingale/D'Alembert, so tem efeito nos sistemas elegiveis (ver
    # SISTEMAS_RECUPERACAO_OPCIONAL) -- campanha.py ja filtra por sistema,
    # aqui so repassa o que veio do painel. Default "nenhuma" preserva o
    # fluxo de sempre.
    recuperacao = body.get("recuperacao") or "nenhuma"
    if recuperacao != "nenhuma":
        cmd += ["--recuperacao", recuperacao]
    # --deposit so vai explicito se o chamador mandou um numero de verdade
    # -- sem isso, cai no default do proprio campanha.py (None = automatico,
    # resolve o capital minimo pela CLASSE de CADA simbolo). Achado do dono,
    # 2026-08-10: o Auto-suggest do front mandava o MAIOR capital_base entre
    # as classes marcadas como um numero fixo unico -- misturar Forex com
    # Metais numa campanha manual testava Forex com deposito de Metais
    # (10000), inflando a margem disponivel e aprovando no gate de
    # sobrevivencia combos que nao aguentariam o capital real da propria
    # classe. Cada combo resolve o proprio deposito agora (ver
    # campanha.resolver_deposito).
    if body.get("deposit") is not None:
        cmd += ["--deposit", str(body["deposit"])]
    # --from so vai explicito se o chamador mandou um; sem isso, cai no
    # default do proprio campanha.py (anos_atras(3) -- sempre 3 anos antes
    # de HOJE). Achado 2026-08-09: aqui tinha um fallback "2023.08.01"
    # cravado, que ficava mais desatualizado a cada dia e so nao aparecia
    # pro usuario porque o dashboard SEMPRE manda campo-inicio preenchido
    # (anosAtrasMT5(3) no app.js) -- so uma chamada direta na API (sem
    # passar por essa tela) caia nesse fallback congelado.
    if body.get("inicio"):
        cmd += ["--from", body["inicio"]]
    limite = body.get("limite", 0)
    if limite:
        cmd += ["--limite", str(limite)]
    if modo == "manual":
        sistemas = body.get("sistemas") or []
        simbolos = body.get("simbolos") or []
        if sistemas:
            cmd += ["--sistemas", ",".join(sistemas)]
        if simbolos:
            cmd += ["--simbolos", ",".join(simbolos)]

    # Limpa um sinal de pausa que tenha sobrado no disco ANTES de lancar
    # (achado do dono, 2026-09-09): /retomar ja limpava isto, mas /start
    # (uma corrida NOVA, sem relacao com a que foi pausada) nao -- uma
    # pausa pedida e nunca retomada/parada deixava o arquivo no disco pra
    # sempre, e todo Start seguinte (o painel foi clicado repetidas vezes
    # numa noite inteira, >5h, 0 combos em cada tentativa) topava com
    # pausa_solicitada()==True antes do primeiro combo e saia na hora.
    # Centralizado aqui (chamado por /start e por /retomar) em vez de cada
    # endpoint lembrar de limpar por conta propria.
    base.PAUSA.unlink(missing_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n### painel: iniciando ({modo}) em "
            f"{datetime.now().isoformat(timespec='seconds')} ###\n"
        )
    # CREATE_NO_WINDOW so suprime a JANELA DE CONSOLE que este python.exe
    # filho abriria sozinho (achado do dono, 2026-08-06: cada combo novo
    # roubava foco/atrapalhava outros apps na tela). Continua 100% visivel
    # no Task Manager/tasklist e matavel por taskkill igual antes -- nao e
    # o processo "escondido" que a regra do projeto proibe, so a janela
    # que ninguem le (stdout ja vai pro LOG, nunca pra um console).
    _processo = subprocess.Popen(
        cmd,
        stdout=open(LOG, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        cwd=str(AQUI),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    LOCK.write_text(
        json.dumps(
            {
                "pid": _processo.pid,
                "modo": modo,
                "iniciado_em": datetime.now().isoformat(timespec="seconds"),
                # Parametros de lancamento, guardados pra Resume relancar
                # IDENTICO sem o usuario reconfigurar tudo de novo (achado
                # 2026-08-09, feature de pausa) -- mesmos campos que
                # montaram `cmd` acima, ja resolvidos (nao os defaults
                # crus do body, que podem estar ausentes).
                "sistemas": body.get("sistemas") or [],
                "simbolos": body.get("simbolos") or [],
                # None (chave ausente ou nula) = automatico, preservado tal
                # e qual pro Resume relancar com o MESMO comportamento
                # (nunca forcar 500 aqui, senao Resume perderia o auto).
                "deposit": body.get("deposit"),
                "min_retencao": body.get("min_retencao", 30.0),
                "timeout": body.get("timeout", 43200),
                "inicio": body.get("inicio"),
                "fim": body.get("fim") or datetime.now().strftime("%Y.%m.%d"),
                "limite": body.get("limite", 0),
                # Familia da corrida (achado do dono, 2026-09-07): o painel
                # deixava trocar o toggle MULTI/BOLLINGER/ICHIMOKU livremente
                # mesmo com uma campanha rodando, mostrando o status/config de
                # uma familia parada enquanto outra rodava de verdade por
                # baixo -- confuso e arriscado (dava pra achar que "nada esta
                # rodando" olhando a tela errada). Gravado aqui pro painel
                # conseguir travar o toggle na familia REAL da corrida ativa
                # (ver carregarEstado() em app.js).
                "familia": body.get("familia", "MULTI"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return JSONResponse({"ok": True, "pid": _processo.pid})


@app.post("/api/campanha/stop")
def campanha_stop() -> JSONResponse:
    global _processo
    # ARVORE inteira, nao so o filho direto: campanha.py e so o pai --
    # optimize_two_stage.py (neto) e quem de fato abre o terminal64.exe a
    # cada combo. `Popen.terminate()` mata so o pai e deixa o neto (e o
    # terminal dele) orfaos rodando -- confirmado na pratica: apos um Stop,
    # `terminal_aberto(base.TERMINAL)` continuava True com um PID novo, de um combo que
    # campanha.py ja tinha avancado antes do sinal chegar. "/T" no taskkill
    # mata a arvore inteira de uma vez, fechando essa janela de corrida.
    pid = None
    if LOCK.exists():
        try:
            pid = json.loads(LOCK.read_text(encoding="utf-8")).get("pid")
        except json.JSONDecodeError:
            pid = None
    if pid is None and _processo is not None:
        pid = _processo.pid
    if pid is not None:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, check=False
        )
    _processo = None
    # So DEPOIS da arvore python estar morta -- senao um filho ainda vivo
    # pode reabrir o terminal entre o fechamento gracioso e o taskkill acima.
    fechado = fechar_terminal(terminal=base.TERMINAL)
    LOCK.unlink(missing_ok=True)
    # Stop cancela tudo, inclusive um pedido de pausa pendente -- sem isto,
    # um Pause seguido de Stop (em vez de Resume) deixava o sinal no disco
    # e o PROXIMO Start (uma corrida nova, sem relacao com a pausada)
    # pausava sozinho antes do primeiro combo.
    base.PAUSA.unlink(missing_ok=True)
    removidas = limpar_ledger_incompleto()
    return JSONResponse(
        {
            "ok": True,
            "terminal_fechado": fechado,
            "entradas_incompletas_removidas": removidas,
        }
    )


@app.post("/api/campanha/pausar")
def campanha_pausar() -> JSONResponse:
    # So grava o sinal (optimize_sets.pausa_solicitada() olha so a
    # PRESENCA do arquivo) -- quem realmente para e' o proprio processo da
    # campanha, no proximo ponto seguro (fim de rodada do Estagio 1 ou
    # antes do proximo combo). Idempotente: pedir pausa duas vezes nao e'
    # erro. Vale tambem pras campanhas CLI (2026-09-26): elas checam o mesmo
    # sinal, e as filas de refacao param antes da proxima etapa.
    estado = estado_campanha()
    if not (estado["rodando"] or estado["campanhas_cli"]):
        return JSONResponse(
            {"ok": False, "erro": "nenhuma corrida rodando pra pausar"},
            status_code=409,
        )
    base.PAUSA.touch()
    return JSONResponse({"ok": True, "pausando": True})


@app.post("/api/campanha/cancelar_pausa")
def campanha_cancelar_pausa() -> JSONResponse:
    """Apaga o sinal de pausa SEM relancar nada. Pra campanha CLI e o unico
    "retomar" seguro: o /retomar relanca a corrida guardada no LOCK do
    PAINEL (que pode ser de outra campanha, dias atras). Pausa ja honrada
    (processo saiu) nao volta sozinha -- relancar a fila CLI."""
    base.PAUSA.unlink(missing_ok=True)
    return JSONResponse({"ok": True, "pausa_pendente": False})


@app.get("/api/auditoria")
def auditoria(n: int = 25) -> JSONResponse:
    """Ultimos `n` eventos do vigia (auditoria_eventos.log): avaliacao de
    cada combo que termina (AVALIAR), saude dos terminais (SAUDE),
    revalidacoes. Antes so chegavam a quem tivesse uma sessao armada lendo
    o arquivo; o painel nao mostrava. Le so o fim do arquivo."""
    arq = AQUI / "auditoria_eventos.log"
    if not arq.exists():
        return JSONResponse({"eventos": []})
    with arq.open("rb") as fh:
        fh.seek(max(0, arq.stat().st_size - 200_000))
        texto = fh.read().decode("utf-8", errors="replace")
    eventos: list[dict] = []
    for linha in texto.splitlines()[1:]:
        if not linha.strip():
            continue
        if linha.startswith((" ", "\t")) and eventos:
            eventos[-1]["detalhes"].append(linha.strip())
            continue
        tipo = linha.split(" ", 1)[0]
        eventos.append({"tipo": tipo, "texto": linha.strip(), "detalhes": []})
    return JSONResponse({"eventos": list(reversed(eventos))[:max(1, min(n, 200))]})


@app.post("/api/campanha/retomar")
def campanha_retomar() -> JSONResponse:
    # Retomar so faz sentido depois que o processo pausado de fato
    # terminou (estado_campanha()["rodando"] passa a False sozinho quando
    # o PID some do tasklist) -- LOCK continua no disco com o PID antigo
    # ate aqui de proposito, so pra guardar os parametros da corrida
    # pausada (ver _lancar_campanha).
    if estado_campanha()["rodando"]:
        return JSONResponse(
            {"ok": False, "erro": "corrida ainda rodando -- espere pausar antes"},
            status_code=409,
        )
    if not LOCK.exists():
        return JSONResponse(
            {"ok": False, "erro": "nada pra retomar (nenhuma corrida pausada)"},
            status_code=409,
        )
    if not _lock_start.acquire(blocking=False):
        return JSONResponse(
            {"ok": False, "erro": "outro start ja esta em andamento"},
            status_code=409,
        )
    try:
        if terminal_aberto(base.TERMINAL):
            return JSONResponse(
                {"ok": False, "erro": "MT5 ocupado por outra acao -- espere terminar"},
                status_code=409,
            )
        try:
            info = json.loads(LOCK.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            info = {}
        # Sinal precisa sumir ANTES de relancar -- senao campanha.py le o
        # arquivo ainda presente e pausa de novo antes do primeiro combo.
        base.PAUSA.unlink(missing_ok=True)
        body = {
            "modo": info.get("modo", "auto"),
            "sistemas": info.get("sistemas") or [],
            "simbolos": info.get("simbolos") or [],
            "deposit": info.get("deposit"),
            "min_retencao": info.get("min_retencao", 30.0),
            "timeout": info.get("timeout", 43200),
            "inicio": info.get("inicio"),
            "fim": info.get("fim"),
            "limite": info.get("limite", 0),
            # Sem isso o Resume caia no default "MULTI" de _lancar_campanha
            # (achado do dono, 2026-09-07) -- uma campanha BOLLINGER/ICHIMOKU
            # pausada voltaria rodando MULTI silenciosamente, o mesmo bug de
            # familia-nao-propagada ja visto em optimize_two_stage.py.
            "familia": info.get("familia", "MULTI"),
        }
        return _lancar_campanha(body)
    finally:
        _lock_start.release()


# ---------------------------------------------------------- deteccao de ativos


@app.post("/api/ativos/detectar")
def ativos_detectar() -> JSONResponse:
    if estado_campanha()["rodando"] or terminal_aberto(base.TERMINAL):
        return JSONResponse(
            {"ok": False, "erro": "MT5 ocupado -- pare a corrida atual primeiro"},
            status_code=409,
        )
    job_id = lancar_job(
        [sys.executable, str(AQUI / "descobrir_ativos.py")], timeout=120
    )
    return JSONResponse({"ok": True, "job_id": job_id})


# ------------------------------------------------------------------ biblioteca


def _manifesto_stats(familia: str = "MULTI") -> dict | None:
    """`total_sets` do manifesto da familia. BOLLINGER e CANDLES tem CSV
    proprio cada (geradores aditivos separados, ver generate_bollinger_sets.py
    e generate_candleentry_sets.py); ICHIMOKU NAO tem -- ele sai do MESMO
    generate_system_sets.py que gera MULTI, so mais um valor na coluna
    Variant do MESMO CSV, entao filtra a coluna em vez de trocar de arquivo
    (achado do dono, 2026-09-07: dar visibilidade de familia propria no
    dashboard sem inventar um gerador que nao existe)."""
    if familia == "BOLLINGER":
        nome = "MANIFESTO_SISTEMAS_BOLLINGER.csv"
    elif familia == "CANDLES":
        nome = "MANIFESTO_SISTEMAS_CANDLES.csv"
    else:
        nome = "MANIFESTO_SISTEMAS.csv"
    caminho = base.SETS / nome
    if not caminho.exists():
        return None
    st = caminho.stat()
    with caminho.open(encoding="utf-8-sig", newline="") as fh:
        linhas = list(csv.DictReader(fh, delimiter=";"))
    if familia == "ICHIMOKU":
        linhas = [row for row in linhas if row.get("Variant", "").upper() == "ICHIMOKU"]
    elif familia == "MULTI":
        linhas = [row for row in linhas if row.get("Variant", "").upper() != "ICHIMOKU"]
    return {
        "total_sets": len(linhas),
        "gerado_em": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


@app.get("/api/biblioteca")
def biblioteca(familia: str = "MULTI") -> JSONResponse:
    return JSONResponse({"manifesto": _manifesto_stats(familia)})


@app.post("/api/biblioteca/regenerar")
def biblioteca_regenerar(body: dict | None = None) -> JSONResponse:
    # terminal_aberto(base.TERMINAL) e a checagem que importa de verdade: uma corrida
    # iniciada FORA do painel (por CLI, como aconteceu na pratica) nao
    # aparece em estado_campanha()["rodando"] (isso so ve o que o proprio
    # painel lancou) -- confirmado num teste real: sem esta linha, uma
    # regeneracao concorrente corrompeu a biblioteca (3738 -> 2920 sets)
    # enquanto uma campanha rodando por fora ainda lia os templates.
    if estado_campanha()["rodando"] or terminal_aberto(base.TERMINAL):
        return JSONResponse(
            {
                "ok": False,
                "erro": "corrida ativa -- regenerar agora sobrescreveria "
                "o template que ela esta lendo",
            },
            status_code=409,
        )
    familia = (body or {}).get("familia", "MULTI")
    # BOLLINGER e CANDLES usam gerador ADITIVO cada (generate_bollinger_sets.py
    # / generate_candleentry_sets.py): nunca apagam nada, so escrevem/
    # atualizam os proprios "*_BOLLINGER.set"/"*_CANDLES.set". MULTI continua
    # no gerador antigo (generate_system_sets.py), que apaga e reconstroi a
    # arvore inteira -- comportamento de sempre, intocado.
    if familia == "BOLLINGER":
        script = "generate_bollinger_sets.py"
    elif familia == "CANDLES":
        script = "generate_candleentry_sets.py"
    else:
        script = "generate_system_sets.py"
    job_id = lancar_job(
        [sys.executable, str(AQUI / script)], timeout=600
    )
    return JSONResponse({"ok": True, "job_id": job_id})


# ------------------------------------------------------------------ portfolios


def _md_para_html(texto: str) -> str:
    """Conversor minimo: cabecalho, lista, tabela, negrito. O conteudo de
    MAPA.md/_PORTFOLIOS e sempre esses quatro elementos -- nao vale trazer a
    dependencia `markdown` so pra isso.

    Linhas de texto puro se acumulam num paragrafo so ate a proxima linha em
    branco ou bloco especial -- achado 2026-08-09: cada linha virava um <p>
    separado, entao uma frase so quebrada em 3 linhas no .md (word wrap, sem
    linha em branco entre elas) aparecia na tela como 3 paragrafos soltos.
    Isso e o comportamento normal de markdown (CommonMark junta linhas
    consecutivas no mesmo paragrafo), so faltava aqui."""
    linhas_html = []
    dentro_tabela = False
    paragrafo: list[str] = []

    def fechar_paragrafo() -> None:
        if paragrafo:
            linhas_html.append(f"<p>{' '.join(paragrafo)}</p>")
            paragrafo.clear()

    for linha in texto.splitlines():
        bruta = linha.rstrip()
        if bruta.startswith("### "):
            fechar_paragrafo()
            linhas_html.append(f"<h3>{bruta[4:]}</h3>")
        elif bruta.startswith("## "):
            fechar_paragrafo()
            linhas_html.append(f"<h2>{bruta[3:]}</h2>")
        elif bruta.startswith("# "):
            fechar_paragrafo()
            linhas_html.append(f"<h1>{bruta[2:]}</h1>")
        elif bruta.startswith("|"):
            fechar_paragrafo()
            celulas = [c.strip() for c in bruta.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", c) for c in celulas):
                continue  # linha separadora do cabecalho da tabela
            tag = "th" if not dentro_tabela else "td"
            linhas_html.append(
                "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in celulas) + "</tr>"
            )
            if not dentro_tabela:
                linhas_html.insert(-1, "<table>")
                dentro_tabela = True
        elif bruta.startswith("- "):
            fechar_paragrafo()
            linhas_html.append(f"<li>{bruta[2:]}</li>")
        elif not bruta.strip():
            fechar_paragrafo()
            if dentro_tabela:
                linhas_html.append("</table>")
                dentro_tabela = False
            linhas_html.append("<br>")
        else:
            paragrafo.append(bruta)
    fechar_paragrafo()
    if dentro_tabela:
        linhas_html.append("</table>")
    html = "\n".join(linhas_html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    return html


def _mesclar_mapas(mapas: list[dict]) -> dict | None:
    """Uniao dos MAPA.json de cada instalacao: por classe/ativo/sistema, as
    variantes prontas de qualquer uma. `prontos` e recontado da uniao (o
    mesmo combo pronto nas duas nao conta duas vezes)."""
    if not mapas:
        return None
    saida = json.loads(json.dumps(mapas[0]))
    for m in mapas[1:]:
        saida["atualizado_em"] = max(saida.get("atualizado_em") or "",
                                     m.get("atualizado_em") or "")
        for classe, ativos in (m.get("classes") or {}).items():
            destino = saida.setdefault("classes", {}).setdefault(classe, {})
            for ativo, sistemas in ativos.items():
                d_ativo = destino.setdefault(ativo, {})
                for sistema, variantes in sistemas.items():
                    d_ativo[sistema] = sorted(set(d_ativo.get(sistema, []))
                                              | set(variantes))
    saida["prontos"] = sum(len(v) for ativos in saida.get("classes", {}).values()
                          for sistemas in ativos.values()
                          for v in sistemas.values())
    return saida


@app.get("/api/portfolios")
def portfolios() -> JSONResponse:
    """Espelho de sets prontos (＊) de TODAS as instalacoes. Achado
    2026-09-25: so lia o do ORIGINAL (0 prontos) enquanto os 4 campeoes
    reais moravam no espelho do CLONE, onde a campanha oficial roda."""
    htmls, mapas = [], []
    resultado: dict = {"sistemas": {}}
    for rotulo, dados in wrx_paths.pastas_de_dados_do_projeto():
        pasta = dados / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets_Autobot"
        mapa = pasta / "MAPA.md"
        mapa_json = pasta / "MAPA.json"
        if mapa.exists():
            htmls.append(f"<h2>Instalacao: {rotulo}</h2>\n"
                         + _md_para_html(mapa.read_text(encoding="utf-8")))
        if mapa_json.exists():
            try:
                mapas.append(json.loads(mapa_json.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
        pasta_port = pasta / "_PORTFOLIOS"
        if pasta_port.is_dir():
            for arq in sorted(pasta_port.glob("*.md")):
                nome = arq.stem if arq.stem not in resultado["sistemas"] \
                    else f"{arq.stem} ({rotulo})"
                resultado["sistemas"][nome] = _md_para_html(
                    arq.read_text(encoding="utf-8"))
    resultado["mapa_html"] = "\n<br>\n".join(htmls) if htmls else None
    resultado["mapa"] = _mesclar_mapas(mapas)
    resultado["gerados"] = [
        {"nome": p.stem.removeprefix("portfolio_"), "url": f"/portfolio-out/{p.name}"}
        for p in sorted(PORTFOLIO_OUT.glob("portfolio_*.html"))
    ]
    resultado["capital_por_sistema"] = ready_library.capital_por_sistema()
    return JSONResponse(resultado)


@app.post("/api/portfolios/gerar")
def portfolios_gerar(body: dict) -> JSONResponse:
    """O espelho de prontos (`ready_library.py`) so guarda o `.set` validado,
    NUNCA o `.htm` original -- o proprio `_PORTFOLIOS/<sistema>.md` ja avisa
    disso ("rode portfolio_builder.py com os relatorios HTML dos membros").
    Por isso esta rota exige a pasta com os relatorios de verdade, coletados
    a mao pelo usuario -- fingir que ela existe sozinha no espelho (como uma
    versao anterior deste endpoint fazia) so falha tarde, com um erro
    confuso de "0 relatorios legiveis"."""
    pasta = (body.get("pasta") or "").strip()
    if not pasta:
        return JSONResponse(
            {
                "ok": False,
                "erro": "informe a pasta com os relatorios .htm/.csv "
                "coletados -- o espelho de prontos so guarda "
                "o .set, nao o relatorio original",
            },
            status_code=400,
        )
    if not Path(pasta).is_dir():
        return JSONResponse(
            {"ok": False, "erro": f"pasta nao encontrada: {pasta}"}, status_code=400
        )
    nome = body.get("nome", "geral")
    PORTFOLIO_OUT.mkdir(exist_ok=True)
    saida = PORTFOLIO_OUT / f"portfolio_{nome}.html"
    job_id = lancar_job(
        [
            sys.executable,
            str(AQUI / "portfolio_builder.py"),
            "--relatorios",
            pasta,
            "--html",
            str(saida),
            "--out",
            str(PORTFOLIO_OUT / f"portfolio_{nome}.csv"),
        ],
        timeout=300,
    )
    return JSONResponse(
        {"ok": True, "job_id": job_id, "arquivo": saida.name, "url": f"/portfolio-out/{saida.name}"}
    )


# ---------------------------------------------------------------- implantacao


def _carregar_implantados() -> set[str]:
    if not SETS_IMPLANTADOS.exists():
        return set()
    try:
        return set(json.loads(SETS_IMPLANTADOS.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return set()


def _salvar_implantados(chaves: set[str]) -> None:
    SETS_IMPLANTADOS.write_text(
        json.dumps(sorted(chaves), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _motivo_sem_certificado(origem: Path, reg: dict) -> dict | None:
    """None = certificado. Senao, POR QUE nao -- {"codigo", "detalhe"}: o
    codigo vira o rotulo curto da aba, o detalhe o tooltip.

    Antes (ate 2026-09-25) "certificado" era so "existe a pasta do
    relatorio", e a pasta e por COMBO, nao por corrida: um VALIDADO_ de
    SWEEP de formula (que nao escreve no ledger) herdava o relatorio e as
    metricas da campanha oficial do mesmo combo -- inclusive de uma
    REPROVADA (XAUUSD/11_SIGNAL_ONLY aparecia certificado com a reprovacao
    por stop de emergencia do lado). Agora exige as tres coisas: ledger
    aprovado, relatorio arquivado e o ARQUIVO ser o mesmo que o ledger
    registrou (conferir_set, a mesma checagem de gravacao do circuito)."""
    if not reg:
        return {"codigo": "sem_ledger",
                "detalhe": "nenhuma linha do ledger para este combo"}
    if not reg.get("aprovado"):
        if reg.get("rebaixado"):
            return {"codigo": "rebaixado",
                    "detalhe": reg.get("motivo_rebaixamento")
                    or "rebaixado no ledger"}
        return {"codigo": "reprovado",
                "detalhe": f"ultima corrida do combo reprovada "
                           f"({reg.get('quando', '?')})"}
    relatorio_dir = reg.get("relatorio_dir")
    if not (relatorio_dir and (RELATORIOS_DIR / relatorio_dir).is_dir()):
        return {"codigo": "sem_relatorio",
                "detalhe": "sem relatorio arquivado em campanha_relatorios/"}
    divergentes = conferir_set(origem, reg.get("parametros") or {})
    if divergentes:
        return {"codigo": "arquivo_diverge",
                "detalhe": f"{origem.name} difere do ledger em "
                           f"{len(divergentes)} parametro(s) "
                           f"({', '.join(divergentes[:4])}) -- e saida de "
                           f"outra corrida (sweep?), nao a aprovada"}
    return None


def _registro_do_arquivo(origem: Path, linhas: list[dict]) -> dict:
    """A linha do ledger que PRODUZIU este arquivo: a ultima com os mesmos
    parametros. Nao simplesmente a ultima do combo -- um desafiante
    reprovado pelo gate relativo (outros parametros) acrescenta linha
    "reprovado" sem derrubar o campeao, e com "a ultima vence" o campeao
    que continua valido aparecia reprovado (achado ao preparar a refacao
    dos aprovados, 2026-09-26). Rebaixamento copia os parametros do
    rebaixado, entao continua valendo. Sem nenhuma com os mesmos
    parametros: a ultima (e _motivo_sem_certificado acusa a divergencia)."""
    iguais = [r for r in linhas
              if r.get("parametros") and not conferir_set(origem, r["parametros"])]
    if iguais:
        return iguais[-1]
    return linhas[-1] if linhas else {}


def _sets_com_origem() -> list[tuple[dict, Path]]:
    """(linha da aba, arquivo) de todo `VALIDADO_*.set` de TODAS as
    instalacoes do projeto (original + clones, wrx_paths) -- a campanha
    oficial roda no clone e os campeoes reais moram la. So leitura: nao
    recria pasta nem copia arquivo. Mesmo combo em duas instalacoes (ex.:
    sobra de sweep num, oficial no outro): fica UM, o certificado."""
    por_combo: dict[tuple[str, str, str], list[dict]] = {}
    for r in ler_ledger():
        por_combo.setdefault(
            (str(r.get("simbolo", "")).replace(".", "_"),
             r.get("sistema", ""), r.get("variante", "")), []).append(r)
    implantados = _carregar_implantados()
    por_chave: dict[str, tuple[dict, Path]] = {}
    for rotulo, pasta in wrx_paths.pastas_de_dados_do_projeto():
        tester = pasta / "MQL5" / "Profiles" / "Tester"
        for origem in sorted(tester.glob("VALIDADO_*.set")):
            info = ready_library.analisar_nome(origem.name)
            if info is None:
                continue
            reg = _registro_do_arquivo(origem, por_combo.get(
                (info["simbolo"], info["sistema"], info["variante"]), []))
            chave = f"{info['simbolo']}__{info['sistema']}__{info['variante']}"
            motivo = _motivo_sem_certificado(origem, reg)
            linha = _linha_implantacao(chave, info, reg, motivo, rotulo,
                                       chave in implantados)
            atual = por_chave.get(chave)
            if atual is None or (linha["certificado"]
                                 and not atual[0]["certificado"]):
                por_chave[chave] = (linha, origem)
    saida = list(por_chave.values())
    # Melhor primeiro: saldo do periodo completo quando medido (a metrica
    # que decide "sobrevive de verdade"), lucro OOS como desempate/
    # fallback pra quem nao passou pelo gate (sistemas fora de grid).
    saida.sort(key=lambda par: (
        par[0]["sobrevivencia_saldo_final"] if par[0]["sobrevivencia_medida"]
        and par[0]["sobrevivencia_saldo_final"] is not None else -1e18,
        par[0]["lucro_oos"] if par[0]["lucro_oos"] is not None else -1e18,
    ), reverse=True)
    return saida


def _sets_certificados() -> list[dict]:
    return [linha for linha, _ in _sets_com_origem()]


def _linha_implantacao(chave: str, info: dict, reg: dict, motivo: dict | None,
                       instalacao: str, implantado: bool) -> dict:
    relatorio_dir = reg.get("relatorio_dir")
    return {
        "chave": chave,
        "simbolo": info["simbolo_exibicao"],
        "sistema": info["sistema"],
        "variante": info["variante"],
        "instalacao": instalacao,
        "motivo_sem_certificado": motivo,
        "retencao": reg.get("retencao_oos"),
        "expectancy": reg.get("expectancy_r"),
        "trades": reg.get("trades_oos"),
        "mc_prob_ruina": reg.get("mc_prob_ruina"),
        # Lucro na janela OOS != lucro no periodo completo -- o achado
        # do dono, 2026-08-03/04 (AUDCHF aprovado com lucro OOS alto e
        # estourando margem no periodo inteiro) e exatamente por isso
        # que o gate de sobrevivencia existe. Mostrar os dois, nunca so
        # o OOS: escolher "o melhor set pra subir" olhando so pra ele
        # foi o que gerou o problema.
        "lucro_oos": reg.get("lucro_tick_real"),
        "sobrevivencia_medida": reg.get("sobrevivencia_medida", False),
        "sobrevivencia_saldo_final": reg.get("sobrevivencia_saldo_final"),
        # Quantas posicoes o MT5 liquidou a forca no CORTE do periodo
        # (achado do dono, 2026-08-16) -- nao e a estrategia quebrando,
        # e uma cesta de recuperacao sem prazo fixo pega no meio do
        # ciclo pela borda do calendario. Nao afeta o veredito de
        # sobrevivencia, so avisa quem for avaliar que o saldo final
        # pode ter uma fatia vinda de fechamento forcado, nao organico.
        "sobrevivencia_fechados_fim_teste": reg.get(
            "sobrevivencia_fechados_fim_teste"),
        "certificado": motivo is None,
        "relatorio_dir": relatorio_dir,
        # Curva de equity do PERIODO COMPLETO (nao a da janela OOS) --
        # achado do dono, 2026-08-04: sem isso nao dava pra CONFERIR
        # visualmente um veredito de sobrevivencia, so confiar no
        # numero. Mesma pasta do relatorio_dir (sobrevivencia.* e
        # conf_wrx.* vivem juntos), mas so existe se o gate rodou.
        "sobrevivencia_grafico": bool(
            reg.get("sobrevivencia_relatorio_dir")
            and (RELATORIOS_DIR / reg["sobrevivencia_relatorio_dir"]
                / "sobrevivencia.png").is_file()),
        "implantado": implantado,
    }


@app.get("/api/implantacao")
def implantacao() -> JSONResponse:
    return JSONResponse({"sets": _sets_certificados()})


@app.get("/api/implantacao/sugestoes")
def implantacao_sugestoes(saldo: float = 0.0) -> JSONResponse:
    """Fila numerada de combinacoes sugeridas pra subir ao vivo -- so entre os
    certificados que ainda NAO estao marcados como implantados. Aceitar uma
    sugestao e o /api/implantacao/marcar de sempre, por chave -- este
    endpoint so calcula a fila, nunca escreve em sets_implantados.json."""
    disponiveis = [s for s in _sets_certificados()
                  if s["certificado"] and not s["implantado"]]
    series = auto_manager_live.carregar_series_certificadas(
        disponiveis, RELATORIOS_DIR)
    sugestoes = auto_manager_live.montar_sugestoes(disponiveis, series, saldo)
    return JSONResponse({
        "sugestoes": sugestoes,
        "pool": len(disponiveis),
        "com_serie": len(series),
    })


@app.get("/api/implantacao/em_prova")
def implantacao_em_prova() -> JSONResponse:
    """Status ao vivo (EM_PROVA/DENTRO_DA_FAIXA/REBAIXAR/PROMOVER) dos combos
    JA implantados -- ver em_prova.py e secao 8 do plano de treinamento.

    Sob demanda, nao entra no polling de /api/status (mesmo padrao de
    /api/relatorio/{relatorio_dir}/resumo): ler historico ao vivo tem custo
    que nao cabe no ritmo de poucos segundos do resto do painel.

    So computa/expoe -- nunca abre, fecha ou redimensiona ordem nenhuma."""
    implantados = [s for s in _sets_certificados() if s["implantado"]]
    if not implantados:
        return JSONResponse({"ok": True, "combos": []})

    trades = em_prova.historico_mt5()
    fonte = "mt5"
    if trades is None:
        return JSONResponse({
            "ok": False,
            "erro": ("Sem acesso ao MT5 ao vivo nesta maquina -- rode o "
                     "dashboard na maquina com o terminal ao vivo, ou "
                     "carregue o relatorio de historico manualmente."),
        })

    tabela = em_prova.tabela_magics()
    trades["chave"] = trades["magic"].apply(
        lambda m: em_prova.combo_do_magic(m, tabela))

    estado = em_prova._carregar_estado()
    saida = []
    for s in implantados:
        chave = s["chave"]
        trades_combo = trades[trades["chave"] == chave]
        r = em_prova.status_ao_vivo(chave, trades_combo, LEDGER, estado)
        estado[chave] = r
        saida.append(r)
    em_prova._salvar_estado(estado)
    return JSONResponse({"ok": True, "fonte": fonte, "combos": saida})


_NOMES_RELATORIO_VALIDOS = {"conf_wrx", "sobrevivencia"}


@app.get("/api/relatorio/{relatorio_dir}/resumo")
def relatorio_resumo_endpoint(relatorio_dir: str,
                              nome: str = "conf_wrx") -> JSONResponse:
    """Metricas-chave (Profit Factor, Sharpe, drawdowns...) ja arquivadas no
    .htm do combo -- sob demanda, so quando uma linha e expandida no
    dashboard (nao entra em /api/status nem /api/implantacao, que sao
    pollados a cada poucos segundos e parsear .htm de ~1MB nesse ritmo
    seria desperdicio)."""
    if (nome not in _NOMES_RELATORIO_VALIDOS or "/" in relatorio_dir
            or "\\" in relatorio_dir or ".." in relatorio_dir):
        return JSONResponse({"ok": False, "erro": "parametro invalido"},
                            status_code=400)
    caminho = RELATORIOS_DIR / relatorio_dir / f"{nome}.htm"
    if not caminho.is_file():
        return JSONResponse({"ok": False, "erro": "relatorio nao encontrado"},
                            status_code=404)
    return JSONResponse({"ok": True,
                         "resumo": relatorio_resumo.resumo_relatorio(caminho)})


@app.post("/api/implantacao/marcar")
def implantacao_marcar(body: dict) -> JSONResponse:
    chaves = body.get("chaves") or []
    marcar_como = bool(body.get("implantado"))
    atuais = _carregar_implantados()
    if marcar_como:
        atuais |= set(chaves)
    else:
        atuais -= set(chaves)
    _salvar_implantados(atuais)
    return JSONResponse({"ok": True, "implantados": sorted(atuais)})


def _origem_do_set(chave: str) -> Path | None:
    """Acha o VALIDADO_*.set dono da `chave` pela MESMA varredura que monta
    a tabela (_sets_com_origem: todas as instalacoes, uma por combo) --
    garante que o arquivo apagado/exportado e exatamente o que a linha da
    tabela representa, nunca o homonimo da outra instalacao."""
    for linha, origem in _sets_com_origem():
        if linha["chave"] == chave:
            return origem
    return None


@app.post("/api/implantacao/deletar")
def implantacao_deletar(body: dict) -> JSONResponse:
    """Remove um set ENTREGUE (VALIDADO_*.set) da raiz do Tester -- pra
    limpar combos que nunca passaram do "sem certificado" (achado do dono,
    2026-09-07: sets orfaos de corridas antigas ficavam empacando a lista
    de implantacao pra sempre, sem jeito de tirar de la fora de mexer na
    pasta na mao). Tambem apaga o relatorio arquivado (se certificado) e a
    marca de implantado (se tiver) -- NUNCA mexe no ledger
    (campanha_resultados.jsonl): so a ENTREGA some, o historico de
    pesquisa que levou ate ali continua existindo."""
    chaves = set(body.get("chaves") or [])
    if not chaves:
        return JSONResponse({"ok": False, "erro": "nenhum set selecionado"},
                            status_code=400)
    ledger = ler_ledger()
    removidos = []
    nao_encontrados = []
    for chave in chaves:
        origem = _origem_do_set(chave)
        if origem is None:
            nao_encontrados.append(chave)
            continue
        info = ready_library.analisar_nome(origem.name)
        reg = _registro_do_arquivo(origem, [
            r for r in ledger
            if (str(r.get("simbolo", "")).replace(".", "_"), r.get("sistema"),
                r.get("variante")) == (info["simbolo"], info["sistema"],
                                       info["variante"])])
        relatorio_dir = reg.get("relatorio_dir")
        # Arquiva ANTES de apagar (mesmo principio de todo outro caminho que
        # toca um VALIDADO_ real, ver campeoes_arquivo.py) -- achado ao vivo,
        # 2026-09-07: um reset do ledger (campanha_resultados.jsonl) fez 3
        # campeoes REAIS aparecerem como "sem certificado" nesta mesma lista
        # (metricas_do_ledger() ficou vazia), e este endpoint os apagou sem
        # nenhuma copia de seguranca -- 1 dos 3 (XAUUSD/11_SIGNAL_ONLY) nao
        # tinha versao arquivada antes e nao foi recuperavel. "Sem
        # certificado no ledger" nao e o mesmo que "sem valor": o ledger
        # pode ficar vazio por outros motivos (reset, corrupcao, migracao)
        # sem que o campeao deixe de ser real.
        # O relatorio e por COMBO, nao por arquivo: so e deste set se ele
        # for o certificado (mesmo arquivo que o ledger registrou). Apagar
        # uma sobra de sweep NAO pode levar junto o relatorio da campanha
        # oficial do mesmo combo (2026-09-25).
        relatorio_e_deste_set = _motivo_sem_certificado(origem, reg) is None
        campeoes_arquivo.arquivar_campeao_anterior(
            info["sistema"], info["simbolo"], info["variante"], origem)
        origem.unlink(missing_ok=True)
        if (relatorio_e_deste_set and relatorio_dir
                and (RELATORIOS_DIR / relatorio_dir).is_dir()):
            shutil.rmtree(RELATORIOS_DIR / relatorio_dir, ignore_errors=True)
        removidos.append(chave)
    if removidos:
        atuais = _carregar_implantados()
        atuais -= set(removidos)
        _salvar_implantados(atuais)
    return JSONResponse({"ok": bool(removidos), "removidos": removidos,
                         "nao_encontrados": nao_encontrados})


@app.post("/api/implantacao/exportar")
def implantacao_exportar(body: dict):
    """Zip so com o `.set` real (sem ＊, e so marcador de exibicao no
    espelho) de cada set selecionado, uma pasta por sistema. So local --
    quem leva pro VPS/conta live e o proprio usuario, copiar-colar. Recusa
    qualquer set sem certificado (relatorio arquivado em disco): o gate
    exige a evidencia EXISTIR para liberar o export, mesmo sem empacotar o
    relatorio junto -- exportar sem evidencia nenhuma devolveria o mesmo
    problema que a Parte D existe pra evitar (administrar sem evidencia)."""
    chaves = set(body.get("chaves") or [])
    if not chaves:
        return JSONResponse({"ok": False, "erro": "nenhum set selecionado"},
                            status_code=400)
    disponiveis = {linha["chave"]: (linha, origem)
                   for linha, origem in _sets_com_origem()}
    sem_certificado = [c for c in chaves
                       if c not in disponiveis or not disponiveis[c][0]["certificado"]]
    if sem_certificado:
        return JSONResponse(
            {"ok": False,
             "erro": f"sem certificado: {sem_certificado}"},
            status_code=400,
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for chave in chaves:
            item, origem_set = disponiveis[chave]
            if origem_set.is_file():
                zf.write(origem_set, f"{item['sistema']}/{origem_set.name}")
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=sets_certificados.zip"},
    )


# --------------------------------------------------------------- perfil (auto_set_manager)


@app.get("/api/perfil")
def perfil() -> JSONResponse:
    atual = (
        json.loads(PERFIL_ATUAL.read_text(encoding="utf-8"))
        if PERFIL_ATUAL.exists()
        else None
    )
    ultima = None
    log_sync = base.SETS / "ULTIMA_SINCRONIZACAO.json"
    if log_sync.exists():
        try:
            ultima = json.loads(log_sync.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ultima = None
    return JSONResponse({"perfil_atual": atual, "ultima_sincronizacao": ultima})


@app.post("/api/perfil/sincronizar")
def perfil_sincronizar(body: dict) -> JSONResponse:
    dry_run = bool(body.get("dry_run", True))
    if not dry_run and (estado_campanha()["rodando"] or terminal_aberto(base.TERMINAL)):
        return JSONResponse(
            {"ok": False, "erro": "MT5 ocupado -- so dry-run agora"}, status_code=409
        )
    perfil_corpo = body.get("perfil") or {}
    PERFIL_ATUAL.write_text(
        json.dumps(perfil_corpo, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    cmd = [
        sys.executable,
        str(AQUI / "auto_set_manager.py"),
        "--perfil",
        str(PERFIL_ATUAL),
    ]
    if dry_run:
        cmd.append("--dry-run")
    job_id = lancar_job(cmd, timeout=300)
    return JSONResponse({"ok": True, "job_id": job_id})


# --------------------------------------------------------------- custo nativo


@app.get("/api/custo-nativo")
def custo_nativo_cache() -> JSONResponse:
    if not CUSTO_CACHE.exists():
        return JSONResponse({})
    return JSONResponse(json.loads(CUSTO_CACHE.read_text(encoding="utf-8")))


@app.post("/api/custo-nativo/medir")
def custo_nativo_medir(body: dict) -> JSONResponse:
    simbolo = (body.get("symbol") or "").strip()
    if not simbolo:
        return JSONResponse(
            {"ok": False, "erro": "informe o simbolo nativo"}, status_code=400
        )
    if estado_campanha()["rodando"] or terminal_aberto(base.TERMINAL):
        return JSONResponse(
            {"ok": False, "erro": "MT5 ocupado -- pare a corrida atual primeiro"},
            status_code=409,
        )
    job_id = lancar_job(
        [
            sys.executable,
            str(AQUI / "custo_nativo.py"),
            "--symbol",
            simbolo,
        ],
        timeout=1800,
    )
    return JSONResponse({"ok": True, "job_id": job_id})


# --------------------------------------------------------------------- static

class EstaticosSempreRevalidados(StaticFiles):
    """StaticFiles com Cache-Control: no-cache em toda resposta -- mesmo
    principio ja aplicado em `/` (ver home() abaixo, achado do dono,
    2026-09-06: HTML em cache apontando pro app.js antigo). Achado de novo,
    2026-09-07: i18n.js foi editado (Modo Economico) e o navegador do dono
    continuou servindo a copia velha do cache ate um hard refresh manual --
    sem Cache-Control explicito, um .js estatico fica sujeito a heuristica
    do navegador, que pode nao revalidar sozinha. no-cache (nao no-store)
    ainda deixa o navegador guardar uma copia, so obriga a checar com o
    servidor antes de usa-la -- praticamente gratis (round-trip condicional
    curto) e elimina esta classe inteira de "editei mas nao apareceu"."""
    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        return resp


ESTATICOS = AQUI / "dashboard_static"
app.mount("/static", EstaticosSempreRevalidados(directory=str(ESTATICOS)), name="static")


@app.get("/")
def home() -> FileResponse:
    # no-cache (nao "no-store"): o navegador ainda guarda uma copia, mas e
    # OBRIGADO a revalidar com o servidor antes de usa-la -- sem isso, um
    # index.html sem Cache-Control explicito fica sujeito a heuristica do
    # navegador e pode servir da memoria sem revalidar. Achado do dono,
    # 2026-09-06: o toggle MULTI/BOLLINGER parecia travado porque o HTML
    # em cache ainda apontava pro app.js?v= antigo (de antes do toggle
    # existir) -- bumpar a versao no arquivo nao adianta se o proprio
    # index.html que referencia essa versao nunca busca de novo no servidor.
    return FileResponse(str(ESTATICOS / "index.html"),
                        headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/sw.js")
def service_worker() -> FileResponse:
    # Servido na raiz (nao em /static/sw.js) de proposito -- o escopo padrao
    # de um service worker e a pasta de onde ele foi servido, e a pagina que
    # ele precisa controlar (o dashboard) mora em "/", nao em "/static/".
    return FileResponse(str(ESTATICOS / "sw.js"), media_type="application/javascript")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--port", type=int, default=8020)
    args = ap.parse_args()
    import uvicorn

    print(f"WRX Autobot Dashboard -> http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
