# -*- coding: utf-8 -*-
"""Semaforo de pre-voo: rode ANTES de subir uma campanha.

Existe porque quase todo prejuizo de terminal deste projeto veio da mesma familia de
erro: campanha de dias rodando contra EA/template/regra VELHOS (variante errada,
build antigo, template sem o input novo, validacao feita com outro .ex5). Aqui cada
uma dessas coisas vira uma linha OK / ALERTA / FALHA, em segundos, sem MT5:

  EA          .ex5 igual nas 2 instalacoes, mais novo que o .mq5, fonte igual ao repo
  templates   biblioteca de sets com os 10 sistemas e mais nova que os geradores
  processos   nada de fila/campanha/teste rodando; pausa armada ou nao
  validacoes  testar_pendentes / testar_sistemas / bateria_logica: feitas DEPOIS do
              build atual da EA e sem FALHA
  biblioteca  validate_system_sets.py: nenhum set alcanca combinacao que o OnInit recuse
  testes      bateria de testes offline (pule com --rapido)
  git         commits sem push / atras da main

    python preflight.py [--rapido]

Codigo de saida: 0 tudo OK, 2 so alertas, 1 alguma FALHA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EAS = ["White Rabbit X (Global Multi-Indicator)",
       "White Rabbit X (Global -  Bolinger Bands)",
       "White Rabbit (Candles Entry)"]
REPO_EA = Path.home() / "Documents" / "Metatrader5EAS" / "White Rabbit" / "EA"
SISTEMAS_ESPERADOS = {"01_SLTP", "02_SLTP_ORGANIC", "03_TRAIL_ONLY", "04_SLTP_TRAIL",
                      "05_BE_TRAIL", "06_REVERSAL_EXIT", "07_GRID_SEPARATE",
                      "11_SIGNAL_ONLY", "12_GRID_INVERSO", "13_OCO_ROMPIMENTO"}
GERADORES = ["generate_system_sets.py", "generate_bollinger_sets.py",
             "generate_candleentry_sets.py"]
# "campanha.py" sem confundir com dashboard_campanha.py (o painel pode ficar de pe)
PADROES_PROCESSO = (r"_fila_", r"(?<![_\w])campanha\.py", r"optimize_two_stage", r"bateria_logica",
                    r"testar_pendentes", r"testar_sistemas", r"validar_live")

Linha = tuple[str, str, str]      # (nivel, titulo, detalhe)


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()[:12]


def _quando(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m %H:%M")


# ---------------------------------------------------------------------------

def checar_ea(dirs: list[tuple[str, Path]]) -> tuple[list[Linha], float]:
    """Linhas da checagem da EA e o mtime do build mais novo (pra comparar validacoes)."""
    linhas: list[Linha] = []
    mais_novo = 0.0
    for ea in EAS:
        hashes: dict[str, str] = {}
        for rotulo, d in dirs:
            ex5 = d / "MQL5" / "Experts" / f"{ea}.ex5"
            mq5 = d / "MQL5" / "Experts" / f"{ea}.mq5"
            if not ex5.exists():
                linhas.append(("falha", f"EA {ea} [{rotulo}]", ".ex5 nao existe"))
                continue
            hashes[rotulo] = _md5(ex5)
            mais_novo = max(mais_novo, ex5.stat().st_mtime)
            if mq5.exists() and mq5.stat().st_mtime > ex5.stat().st_mtime + 2:
                linhas.append(("falha", f"EA {ea} [{rotulo}]",
                               f".mq5 ({_quando(mq5)}) mais novo que o .ex5 ({_quando(ex5)}): recompilar"))
        if len(set(hashes.values())) > 1:
            linhas.append(("falha", f"EA {ea}", f"builds diferentes entre as instalacoes: {hashes}"))
        elif hashes:
            linhas.append(("ok", f"EA {ea}", f"build {next(iter(hashes.values()))} igual em "
                           f"{', '.join(hashes)}"))
        fonte = REPO_EA / f"{ea}.mq5"
        instalada = dirs[0][1] / "MQL5" / "Experts" / f"{ea}.mq5"
        if fonte.exists() and instalada.exists() and _md5(fonte) != _md5(instalada):
            linhas.append(("alerta", f"EA {ea}", "fonte da instalacao difere da do repo "
                           "(Metatrader5EAS): qual e a verdadeira?"))
    return linhas, mais_novo


def checar_templates(dirs: list[tuple[str, Path]]) -> list[Linha]:
    linhas: list[Linha] = []
    for rotulo, d in dirs:
        raiz = d / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"
        man = raiz / "MANIFESTO_SISTEMAS.csv"
        if not man.exists():
            linhas.append(("falha", f"templates [{rotulo}]", "MANIFESTO_SISTEMAS.csv nao existe"))
            continue
        with man.open(encoding="utf-8-sig") as fh:
            sistemas = {r["System"] for r in csv.DictReader(fh, delimiter=";")}
        if sistemas != SISTEMAS_ESPERADOS:
            linhas.append(("falha", f"templates [{rotulo}]",
                           f"sistemas do manifesto != esperados: faltam "
                           f"{sorted(SISTEMAS_ESPERADOS - sistemas)}, sobram "
                           f"{sorted(sistemas - SISTEMAS_ESPERADOS)}"))
        else:
            linhas.append(("ok", f"templates [{rotulo}]", f"10 sistemas, manifesto de {_quando(man)}"))
        amostra = next(iter(raiz.glob("*/EURUSD/04_SLTP_TRAIL/BUY_MULTI.set")), None)
        if amostra is not None:
            texto = amostra.read_bytes().decode("utf-16", errors="replace")
            for chave in ("EntryOrderType", "PendingDistanciaATR", "RecoveryMode"):
                if chave + "=" not in texto:
                    linhas.append(("falha", f"templates [{rotulo}]",
                                   f"template de amostra sem o input {chave} (EA nova, template velho)"))
        for g in GERADORES:
            gp = AQUI / g
            if gp.exists() and gp.stat().st_mtime > man.stat().st_mtime + 2:
                linhas.append(("alerta", f"templates [{rotulo}]",
                               f"{g} ({_quando(gp)}) mais novo que o manifesto ({_quando(man)}): "
                               "regenerar os sets?"))
    return linhas


def checar_processos() -> list[Linha]:
    if sys.platform != "win32":
        return []
    cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine } | "
           "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    try:
        saida = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True,
                               text=True, timeout=60).stdout
        procs = json.loads(saida) if saida.strip() else []
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return [("alerta", "processos", "nao consegui listar os processos")]
    if isinstance(procs, dict):
        procs = [procs]
    vivos = [p for p in procs
             if any(re.search(pad, p["CommandLine"] or "") for pad in PADROES_PROCESSO)
             and "preflight.py" not in p["CommandLine"] and "Get-CimInstance" not in p["CommandLine"]]
    linhas: list[Linha] = []
    if vivos:
        nomes = sorted({next((pad for pad in PADROES_PROCESSO if re.search(pad, p["CommandLine"])), "?")
                        for p in vivos})
        linhas.append(("alerta", "processos", f"{len(vivos)} processo(s) de fila/teste vivo(s): {nomes}"))
    else:
        linhas.append(("ok", "processos", "nenhuma fila, campanha ou teste rodando"))
    pausa = AQUI / "campanha_pausa.json"
    linhas.append(("ok" if pausa.exists() else "alerta", "pausa",
                   "campanha_pausa.json armado (a campanha nao sobe sozinha)" if pausa.exists()
                   else "SEM pausa armada: uma fila que reinicie volta a rodar"))
    return linhas


def _falhas_de_resultado(arq: Path) -> tuple[int, int]:
    dados = json.loads(arq.read_text(encoding="utf-8"))
    return (sum(1 for r in dados.values() if r.get("falhas")), len(dados))


def checar_validacoes(build_mais_novo: float) -> list[Linha]:
    linhas: list[Linha] = []
    itens = [("testar_pendentes", AQUI / "_pendentes_teste" / "resultado.json"),
             ("testar_sistemas", AQUI / "_sistemas_teste" / "resultado.json")]
    for nome, arq in itens:
        if not arq.exists():
            linhas.append(("alerta", f"validacao {nome}", "nunca rodada"))
            continue
        ruins, total = _falhas_de_resultado(arq)
        velho = arq.stat().st_mtime < build_mais_novo
        nivel = "falha" if ruins else ("alerta" if velho else "ok")
        linhas.append((nivel, f"validacao {nome}", f"{total} cenarios, {ruins} com FALHA, verificada em "
                       f"{_quando(arq)}" + (" (ANTES do build atual da EA: refazer)" if velho else "")))
    rels = sorted((AQUI / "bateria_logica").glob("*/relatorio.txt"), key=lambda p: p.stat().st_mtime)
    if not rels:
        linhas.append(("alerta", "validacao bateria_logica", "nenhuma rodada com relatorio"))
    else:
        rel = rels[-1]
        cab = rel.read_text(encoding="utf-8").splitlines()[0]
        velho = rel.stat().st_mtime < build_mais_novo
        linhas.append(("alerta" if velho else "ok", "validacao bateria_logica",
                       f"{rel.parent.name}: {cab}" + (" (ANTES do build atual: refazer)" if velho else "")))
    return linhas


def checar_biblioteca_oninit(rapido: bool) -> list[Linha]:
    """validate_system_sets.py: schema de cada familia contra a SUA EA e nenhuma combinacao
    alcancavel que o OnInit recuse (fora o acoplamento conhecido do 06 BOTH)."""
    if rapido:
        return [("alerta", "biblioteca x OnInit", "pulada (--rapido)")]
    r = subprocess.run([sys.executable, str(AQUI / "validate_system_sets.py")], cwd=AQUI,
                       capture_output=True, text=True, timeout=900)
    saida = r.stdout
    m_sets = re.search(r"Sets validados: (\d+)", saida)
    m_av = re.search(r"AVISOS \(acoplamento conhecido[^)]*\): (\d+)", saida)
    if r.returncode != 0:
        m_err = re.search(r"ERROS: (\d+)", saida)
        return [("falha", "biblioteca x OnInit", f"{m_err.group(1) if m_err else '?'} sets que a EA "
                 "recusa (rode validate_system_sets.py)")]
    extra = f", {m_av.group(1)} com acoplamento conhecido (06 BOTH)" if m_av else ""
    return [("ok", "biblioteca x OnInit", f"{m_sets.group(1) if m_sets else '?'} sets validados{extra}")]


def checar_testes(rapido: bool) -> list[Linha]:
    if rapido:
        return [("alerta", "testes offline", "pulados (--rapido)")]
    falhos = []
    arquivos = sorted(AQUI.glob("test_*.py"))
    for f in arquivos:
        r = subprocess.run([sys.executable, str(f)], cwd=AQUI, capture_output=True, text=True,
                           timeout=600)
        if r.returncode != 0:
            falhos.append(f.name)
    if falhos:
        return [("falha", "testes offline", f"{len(falhos)} de {len(arquivos)} falharam: {falhos}")]
    return [("ok", "testes offline", f"{len(arquivos)} arquivos, todos passaram")]


def checar_git() -> list[Linha]:
    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=AQUI, capture_output=True, text=True).stdout.rstrip("\n")

    try:
        ramo = git("branch", "--show-current").strip()
        atras, _, adiante = git("rev-list", "--left-right", "--count",
                                "origin/main...HEAD").strip().partition("\t")
    except OSError:
        return [("alerta", "git", "git indisponivel")]
    linhas: list[Linha] = []
    if adiante.strip() not in ("", "0"):
        linhas.append(("alerta", "git", f"{adiante.strip()} commit(s) a frente de origin/main sem push "
                       f"(ramo {ramo})"))
    if atras.strip() not in ("", "0"):
        linhas.append(("alerta", "git", f"{atras.strip()} commit(s) atras de origin/main"))
    sujos = [x for x in git("status", "--short").splitlines() if x[:2].strip() == "M"
             and not any(s in x for s in ("sets_implantados.json", "mt5_pular_update.json"))]
    if sujos:
        linhas.append(("alerta", "git", f"{len(sujos)} arquivo(s) modificado(s) sem commit: "
                       f"{[s[3:] for s in sujos][:4]}"))
    if not linhas:
        linhas.append(("ok", "git", f"ramo {ramo} em dia com origin/main"))
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rapido", action="store_true", help="nao roda os testes offline")
    args = ap.parse_args()
    sys.path.insert(0, str(AQUI))
    import wrx_paths
    dirs = wrx_paths.pastas_de_dados_do_projeto()
    linhas: list[Linha] = []
    l_ea, build = checar_ea(dirs)
    linhas += l_ea
    linhas += checar_templates(dirs)
    linhas += checar_processos()
    linhas += checar_validacoes(build)
    linhas += checar_biblioteca_oninit(args.rapido)
    linhas += checar_testes(args.rapido)
    linhas += checar_git()
    marca = {"ok": "OK    ", "alerta": "ALERTA", "falha": "FALHA "}
    for nivel, titulo, detalhe in linhas:
        print(f"{marca[nivel]} {titulo:38} {detalhe}")
    falhas = sum(1 for n, _, _ in linhas if n == "falha")
    alertas = sum(1 for n, _, _ in linhas if n == "alerta")
    print(f"\n{len(linhas)} verificacoes: {falhas} FALHA, {alertas} alerta(s).")
    return 1 if falhas else (2 if alertas else 0)


if __name__ == "__main__":
    sys.exit(main())
