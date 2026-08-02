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
andamento -- `mt5_runner.terminal_aberto()` e a fonte da verdade (nao um
lockfile proprio, que poderia mentir se algo travou fora do painel).

Uso:
    python dashboard_campanha.py                # porta 8020
    python dashboard_campanha.py --port 8021
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import optimize_sets as base
from generate_system_sets import ASSETS, CLASSES, SYSTEMS
from mt5_runner import fechar_terminal, terminal_aberto

AQUI = Path(__file__).resolve().parent
LEDGER = AQUI / "campanha_resultados.jsonl"
LOG = AQUI / "campanha_run.log"
LOCK = AQUI / "campanha_dashboard.lock.json"
PERFIL_ATUAL = AQUI / "perfil_dashboard.json"
CUSTO_CACHE = AQUI / "_custo_nativo.json"

app = FastAPI(title="WRX Autobot Dashboard")

# ------------------------------------------------------------- estado global

_processo: subprocess.Popen | None = None  # so valido no MESMO processo do
# uvicorn -- ver estado_campanha()
# para o caso de o painel reiniciar
_jobs: dict[str, dict] = {}


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
    limpeza que tive que fazer a mao repetidas vezes nesta sessao."""
    if not LEDGER.exists():
        return 0
    boas, removidas = [], 0
    for linha in LEDGER.read_text(encoding="utf-8").splitlines():
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
    if removidas:
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
            "mc_pass_rate": 0.0,
            "retencao_media": None,
            "lucro_medio_tick_real": None,
            "wfe_status": "sem relatorio no ledger",
            "mc_status": "sem resultado no ledger",
        }

    mc_ok = sum(1 for r in resultados if r.get("mc_aprovado") is True)
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
    mc_disponivel = any(r.get("mc_aprovado") is not None for r in resultados)

    return {
        "mc_pass_rate": round((mc_ok / total) * 100.0, 1) if total else 0.0,
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
            "relatorio Monte Carlo presente"
            if mc_disponivel
            else "sem relatorio MC no ledger"
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
def status() -> JSONResponse:
    resultados = ler_ledger()
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
            "total_feitos": len(resultados),
            "aprovados": len(aprovados),
            "reprovados": len(resultados) - len(aprovados),
            "por_sistema": por_sistema,
            "atual": combo_atual(),
            "recentes": list(reversed(resultados))[:30],
            "qualidade": resumo_qualidade(resultados),
        }
    )


# ---------------------------------------------------------------- /api/config


@app.get("/api/config")
def config() -> JSONResponse:
    sistemas = [{"code": s.code, "label": s.label, "status": s.status} for s in SYSTEMS]
    classes = {
        codigo: {"capital_base": CLASSES[codigo].capital_base, "ativos": ativos}
        for codigo, ativos in ASSETS.items()
    }
    return JSONResponse({"sistemas": sistemas, "classes": classes})


# ------------------------------------------------------------ campanha start/stop


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
    return {"rodando": vivo, "terminal_aberto": terminal_aberto(), **info}


@app.get("/api/campanha/estado")
def campanha_estado() -> JSONResponse:
    return JSONResponse(estado_campanha())


@app.post("/api/campanha/start")
def campanha_start(body: dict) -> JSONResponse:
    global _processo
    if estado_campanha()["rodando"]:
        return JSONResponse(
            {"ok": False, "erro": "ja ha uma corrida rodando"}, status_code=409
        )
    if terminal_aberto():
        return JSONResponse(
            {"ok": False, "erro": "MT5 ocupado por outra acao -- espere terminar"},
            status_code=409,
        )

    modo = body.get("modo", "auto")
    cmd = [
        sys.executable,
        str(AQUI / "campanha.py"),
        "--from",
        body.get("inicio", "2023.08.01"),
        "--to",
        body.get("fim", "2026.07.21"),
        "--deposit",
        str(body.get("deposit", 500)),
        "--min-retencao",
        str(body.get("min_retencao", 30.0)),
        "--timeout",
        str(body.get("timeout", 21600)),
    ]
    if modo == "manual":
        sistemas = body.get("sistemas") or []
        simbolos = body.get("simbolos") or []
        if sistemas:
            cmd += ["--sistemas", ",".join(sistemas)]
        if simbolos:
            cmd += ["--simbolos", ",".join(simbolos)]

    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n### painel: iniciando ({modo}) em "
            f"{datetime.now().isoformat(timespec='seconds')} ###\n"
        )
    _processo = subprocess.Popen(
        cmd,
        stdout=open(LOG, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        cwd=str(AQUI),
    )
    LOCK.write_text(
        json.dumps(
            {
                "pid": _processo.pid,
                "modo": modo,
                "iniciado_em": datetime.now().isoformat(timespec="seconds"),
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
    # `terminal_aberto()` continuava True com um PID novo, de um combo que
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
    fechado = fechar_terminal()
    LOCK.unlink(missing_ok=True)
    removidas = limpar_ledger_incompleto()
    return JSONResponse(
        {
            "ok": True,
            "terminal_fechado": fechado,
            "entradas_incompletas_removidas": removidas,
        }
    )


# ---------------------------------------------------------- deteccao de ativos


@app.post("/api/ativos/detectar")
def ativos_detectar() -> JSONResponse:
    if estado_campanha()["rodando"] or terminal_aberto():
        return JSONResponse(
            {"ok": False, "erro": "MT5 ocupado -- pare a corrida atual primeiro"},
            status_code=409,
        )
    job_id = lancar_job(
        [sys.executable, str(AQUI / "descobrir_ativos.py")], timeout=120
    )
    return JSONResponse({"ok": True, "job_id": job_id})


# ------------------------------------------------------------------ biblioteca


def _manifesto_stats() -> dict | None:
    caminho = base.SETS / "MANIFESTO_SISTEMAS.csv"
    if not caminho.exists():
        return None
    st = caminho.stat()
    with caminho.open(encoding="utf-8-sig") as fh:
        total = sum(1 for _ in fh) - 1
    return {
        "total_sets": max(total, 0),
        "gerado_em": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


@app.get("/api/biblioteca")
def biblioteca() -> JSONResponse:
    return JSONResponse({"manifesto": _manifesto_stats()})


@app.post("/api/biblioteca/regenerar")
def biblioteca_regenerar() -> JSONResponse:
    # terminal_aberto() e a checagem que importa de verdade: uma corrida
    # iniciada FORA do painel (por CLI, como aconteceu na pratica) nao
    # aparece em estado_campanha()["rodando"] (isso so ve o que o proprio
    # painel lancou) -- confirmado num teste real: sem esta linha, uma
    # regeneracao concorrente corrompeu a biblioteca (3738 -> 2920 sets)
    # enquanto uma campanha rodando por fora ainda lia os templates.
    if estado_campanha()["rodando"] or terminal_aberto():
        return JSONResponse(
            {
                "ok": False,
                "erro": "corrida ativa -- regenerar agora sobrescreveria "
                "o template que ela esta lendo",
            },
            status_code=409,
        )
    job_id = lancar_job(
        [sys.executable, str(AQUI / "generate_system_sets.py")], timeout=600
    )
    return JSONResponse({"ok": True, "job_id": job_id})


# ------------------------------------------------------------------ portfolios


def _prontos_dir() -> Path:
    return base.DADOS / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets_Autobot"


def _md_para_html(texto: str) -> str:
    """Conversor minimo: cabecalho, lista, tabela, negrito. O conteudo de
    MAPA.md/_PORTFOLIOS e sempre esses quatro elementos -- nao vale trazer a
    dependencia `markdown` so pra isso."""
    linhas_html = []
    dentro_tabela = False
    for linha in texto.splitlines():
        bruta = linha.rstrip()
        if bruta.startswith("### "):
            linhas_html.append(f"<h3>{bruta[4:]}</h3>")
        elif bruta.startswith("## "):
            linhas_html.append(f"<h2>{bruta[3:]}</h2>")
        elif bruta.startswith("# "):
            linhas_html.append(f"<h1>{bruta[2:]}</h1>")
        elif bruta.startswith("|"):
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
            linhas_html.append(f"<li>{bruta[2:]}</li>")
        elif not bruta.strip():
            if dentro_tabela:
                linhas_html.append("</table>")
                dentro_tabela = False
            linhas_html.append("<br>")
        else:
            linhas_html.append(f"<p>{bruta}</p>")
    if dentro_tabela:
        linhas_html.append("</table>")
    html = "\n".join(linhas_html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    return html


@app.get("/api/portfolios")
def portfolios() -> JSONResponse:
    pasta = _prontos_dir()
    mapa = pasta / "MAPA.md"
    resultado = {
        "mapa_html": (
            _md_para_html(mapa.read_text(encoding="utf-8")) if mapa.exists() else None
        ),
        "sistemas": {},
    }
    pasta_port = pasta / "_PORTFOLIOS"
    if pasta_port.is_dir():
        for arq in sorted(pasta_port.glob("*.md")):
            resultado["sistemas"][arq.stem] = _md_para_html(
                arq.read_text(encoding="utf-8")
            )
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
    saida = AQUI / f"portfolio_{nome}.html"
    job_id = lancar_job(
        [
            sys.executable,
            str(AQUI / "portfolio_builder.py"),
            "--relatorios",
            pasta,
            "--html",
            str(saida),
            "--out",
            str(AQUI / f"portfolio_{nome}.csv"),
        ],
        timeout=300,
    )
    return JSONResponse({"ok": True, "job_id": job_id, "arquivo": saida.name})


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
    if not dry_run and (estado_campanha()["rodando"] or terminal_aberto()):
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
    if estado_campanha()["rodando"] or terminal_aberto():
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

ESTATICOS = AQUI / "dashboard_static"
app.mount("/static", StaticFiles(directory=str(ESTATICOS)), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(str(ESTATICOS / "index.html"))


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
