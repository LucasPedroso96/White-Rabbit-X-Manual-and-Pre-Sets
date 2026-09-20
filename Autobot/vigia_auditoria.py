# -*- coding: utf-8 -*-
"""Vigia de veredito: emite um EVENTO a cada algoritmo que termina.

Cada linha/bloco impresso e um evento pro revisor (a sessao do Claude, via
Monitor) avaliar se a aprovacao/reprovacao foi justa -- pedido do dono,
2026-09-20: "sempre que terminar um algoritmo chame voce para avaliar se foi
justa a aprovacao ou reprovacao". A parte mecanica (extrair motivo, numeros e
sinais) esta em auditar_combo.py; aqui so se detecta "terminou".

O que vigia:
  - campanha*.log: cada combo com a linha final "-> ..." (SEMPRE emite);
  - fila_calibracao_*.log: cada formula de sweep que fecha ("log salvo em
    sweep_...log"). Emite se APROVADA, INCOMPLETA (travou/morreu) ou com sinal
    relevante; as demais (reprovacao rotineira, sem sinal) vao so pro digesto
    `auditoria_calibracao.log` -- nunca somem, mas nao acordam ninguem.

Estado em `auditoria_estado.json`: na PRIMEIRA execucao marca tudo que ja
existe como visto (sem inundar). `--dry N` reprocessa os N ultimos sem estado.

    python vigia_auditoria.py                # loop (Monitor)
    python vigia_auditoria.py --dry 3        # teste: ultimos 3 eventos
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import auditar_combo as ac

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / "auditoria_estado.json"
DIGESTO = AQUI / "auditoria_calibracao.log"
# Eventos ficam tambem num arquivo: o Monitor expira (max 30 min) e um evento
# emitido no intervalo entre dois Monitors nao pode se perder -- o leitor le
# deste arquivo a partir de um deslocamento salvo.
EVENTOS = AQUI / "auditoria_eventos.log"
_SALVO = re.compile(r"^\s+log salvo em (sweep_\S+\.log)", re.M)


def carregar_estado() -> set[str] | None:
    if not ESTADO.exists():
        return None
    try:
        return set(json.loads(ESTADO.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None


def salvar_estado(estado: set[str]) -> None:
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(estado)), encoding="utf-8")
    os.replace(tmp, ESTADO)


def ler(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def eventos_campanha() -> list[tuple[str, str]]:
    """[(chave, texto do evento)] de todos os combos prontos, em ordem."""
    out = []
    for f in sorted(AQUI.glob("campanha*.log")):
        for rot, bloco in ac.blocos_campanha(ler(f)):
            final = re.search(r"^-> .*$", bloco, re.M)
            chave = f"C|{f.name}|{rot}|{final.group(0) if final else ''}"
            out.append((chave, ac.formatar(ac.auditar(bloco, rot))))
    return out


def eventos_calibracao() -> list[tuple[str, str, bool]]:
    """[(chave, texto, acorda)] das formulas de sweep fechadas."""
    out = []
    for fila in sorted(AQUI.glob("fila_calibracao_*.log")):
        for nome in dict.fromkeys(_SALVO.findall(ler(fila))):
            f = AQUI / nome
            if not f.exists():
                continue
            texto = ler(f)
            a = ac.auditar(texto, ac.rotulo_sweep(texto, f.stem))
            curto = re.sub(r"^sweep_|\.log$", "", nome)
            a["rotulo"] += f" [{curto}]"
            relevante = (a["veredito"] != "REPROVADO"
                         or a["sugestao"].startswith("REVISAR"))
            chave = f"S|{nome}|{int(f.stat().st_mtime)}"
            out.append((chave, ac.formatar(a), relevante))
    return out


def emitir(texto: str) -> None:
    print(texto, flush=True)
    with EVENTOS.open("a", encoding="utf-8") as fh:
        fh.write(texto + "\n")


def registrar_digesto(texto: str) -> None:
    with DIGESTO.open("a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now():%d/%m %H:%M}] {texto}\n")


def um_ciclo(estado: set[str], silencioso: bool) -> int:
    novos = 0
    for chave, texto in eventos_campanha():
        if chave in estado:
            continue
        estado.add(chave)
        novos += 1
        if not silencioso:
            emitir(texto)
    for chave, texto, acorda in eventos_calibracao():
        if chave in estado:
            continue
        estado.add(chave)
        novos += 1
        if silencioso:
            continue
        if acorda:
            emitir(texto)
        else:
            registrar_digesto(texto.splitlines()[0]
                              + "  " + texto.splitlines()[-1].strip())
    return novos


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--intervalo", type=int, default=60)
    ap.add_argument("--dry", type=int, default=0,
                    help="reprocessa os N ultimos eventos (sem estado) e sai")
    args = ap.parse_args()

    if args.dry:
        ev = [t for _, t in eventos_campanha()]
        ev += [t for _, t, _ in eventos_calibracao()]
        for t in ev[-args.dry:]:
            print(t, flush=True)
            print(flush=True)
        return 0

    estado = carregar_estado()
    if estado is None:  # primeira execucao: marca o que ja existe, em silencio
        estado = set()
        n = um_ciclo(estado, silencioso=True)
        salvar_estado(estado)
        print(f"vigia_auditoria armado: {n} resultado(s) existentes marcados "
              "como ja avaliados; a partir de agora cada algoritmo que "
              "terminar gera um evento (auditoria_eventos.log).", flush=True)
    while True:
        try:
            if um_ciclo(estado, silencioso=False):
                salvar_estado(estado)
        except Exception as exc:  # silencio nao pode parecer sucesso
            print(f"ERRO no vigia_auditoria (segue tentando): {exc!r}",
                  flush=True)
        time.sleep(args.intervalo)


if __name__ == "__main__":
    sys.exit(main())
