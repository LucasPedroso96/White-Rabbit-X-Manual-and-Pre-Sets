# -*- coding: utf-8 -*-
"""Roda o circuito de validacao em lote, de forma RESUMIVEL.

Cada combo custa ~20 min, e a campanha inteira nao cabe numa sessao. Entao o
progresso mora em disco (`campanha_resultados.jsonl`), nao na memoria do
processo: relancar o script pula o que ja foi medido e continua de onde parou.
Sem isso, qualquer interrupcao -- cota, queda de energia, reinicio -- custaria
todas as horas ja gastas.

ORDEM: por TIPO DE SISTEMA primeiro, nao por simbolo. Sao 11 tipos e 9 simbolos
com tick real; varrer simbolo a simbolo daria 9 medidas do 01_SLTP antes da
primeira do 02_SLTP. Como a pergunta em aberto e "quais TIPOS sobrevivem a
metodologia", a largura vale mais que a profundidade no comeco -- interromper
depois de 11 corridas deixa um retrato dos 11 tipos, e nao um retrato exaustivo
de um tipo so.

    python campanha.py                 # continua de onde parou
    python campanha.py --listar        # so mostra a fila
    python campanha.py --limite 5      # roda 5 combos e para
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import optimize_sets as base

AQUI = Path(__file__).resolve().parent
LEDGER = AQUI / "campanha_resultados.jsonl"

# EURUSD SO, todos os sistemas (dono, 2026-07-31): a pergunta em aberto e
# "quais TIPOS sobrevivem a metodologia", e ela se responde num ativo com tick
# real. Espalhar por 9 simbolos antes disso multiplicaria por 9 o custo de
# descobrir que um tipo nao presta. Os outros entram depois, com os tipos ja
# triados.
SIMBOLOS = ["EURUSD.HT"]

# Ordem pedida pelo dono: grid, trailing e so-indicador primeiro. O resto e
# escolha minha, por quanto cada um ENSINA sobre o proximo:
#   - geometria fixa (01/02/06) depois do trailing, para comparar "deixar
#     correr" contra "alvo fixo" com o mesmo sinal ja conhecido;
#   - recovery (09/10) por ultimo: sao os que mais dependem da geometria de
#     saida estar resolvida, e os mais provaveis de reprovar -- se reprovarem,
#     reprovam sabendo que o resto ja foi medido.
SISTEMAS = ["07_GRID_SEPARATE", "08_GRID_UNIFIED",             # cesta
            "03_TRAIL_ONLY", "04_SLTP_TRAIL", "05_BE_TRAIL",   # trailing
            "11_SIGNAL_ONLY",                                  # so indicador
            "01_SLTP", "02_SLTP_ORGANIC", "06_REVERSAL_EXIT",  # geometria fixa
            "09_MARTINGALE", "10_DALEMBERT"]                   # recovery

# 08_GRID_UNIFIED e bilateral: opera os dois lados no mesmo passe, entao o set
# e BOTH_*. Os demais tem um set por lado.
BILATERAL = {"08_GRID_UNIFIED"}

# Cada "rodada" percorre os 11 sistemas com UMA variante antes de avancar. As
# ICHIMOKU entram DEPOIS das MULTI de proposito, nao por esquecimento como
# antes: a MULTI ja disputa 11 indicadores (0..10) no proprio genetico, entao
# ela rende o retrato mais largo por corrida -- mas o Ichimoku (11) vive em
# arquivo proprio (Tenkan<Kijun<SenkouB no OnInit), e sem estas rodadas ele
# era o unico indicador que NUNCA era testado.
RODADAS = [("SELL_MULTI", "BOTH_MULTI"), ("BUY_MULTI", None),
           ("SELL_ICHIMOKU", "BOTH_ICHIMOKU"), ("BUY_ICHIMOKU", None)]


def variantes(sistema: str) -> list[str]:
    duplo = sistema in BILATERAL
    return [b if duplo else a for a, b in RODADAS if not (duplo and b is None)]


def fila() -> list[tuple[str, str, str]]:
    """Combos na ordem de execucao: TODOS os sistemas antes de trocar de
    variante, todas as variantes antes de trocar de simbolo.

    Assim as 11 primeiras corridas (~4h) sao os 11 tipos em EURUSD, e nao 11
    variacoes do mesmo tipo. Interromper cedo deixa um retrato de todos os
    tipos; a ordem inversa deixaria um tipo exaustivamente medido e dez sem
    nenhuma medida.
    """
    itens = []
    for simbolo in SIMBOLOS:
        for unilateral, bilateral in RODADAS:
            for sistema in SISTEMAS:
                v = bilateral if sistema in BILATERAL else unilateral
                if v is None:          # bilateral nao tem BUY_* proprio
                    continue
                if base.achar_set(simbolo, sistema, v) is not None:
                    itens.append((simbolo, sistema, v))
    return itens


def feitos() -> set[tuple[str, str, str]]:
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
        vistos.add((r["simbolo"], r["sistema"], r["variante"]))
    return vistos


def registrar(reg: dict) -> None:
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")


def rodar_combo(simbolo: str, sistema: str, variante: str, args) -> dict:
    cmd = [sys.executable, str(AQUI / "optimize_two_stage.py"),
           "--symbol", simbolo, "--sistema", sistema, "--variante", variante,
           "--from", args.inicio, "--to", args.fim,
           "--deposit", str(args.deposit),
           "--min-retencao", str(args.min_retencao),
           "--fechar-terminal", "--timeout", str(args.timeout)]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       timeout=args.timeout + 600)
    saida = (p.stdout or "") + (p.stderr or "")
    print(saida, flush=True)

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
               "erro": "sem JSON final", "returncode": p.returncode}
    reg["minutos"] = round((time.time() - t0) / 60, 1)
    reg["quando"] = datetime.now().isoformat(timespec="seconds")
    reg["aprovado"] = "VALIDADO" in saida and "REPROVADO: nao promova" not in saida
    return reg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="inicio", default="2023.08.01")
    ap.add_argument("--to", dest="fim", default="2026.07.21")
    ap.add_argument("--deposit", type=int, default=500)
    ap.add_argument("--min-retencao", type=float, default=30.0)
    ap.add_argument("--timeout", type=int, default=21600)
    ap.add_argument("--limite", type=int, default=0, help="0 = sem limite")
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args()

    todos = fila()
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
