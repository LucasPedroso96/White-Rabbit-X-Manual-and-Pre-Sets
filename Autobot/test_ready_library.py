# -*- coding: utf-8 -*-
"""Testa o espelho de prontos e a fila/estagio-1 SEM precisar do MT5.

Mesma razao de existir do test_ler_metricas: os defeitos destas pecas so
apareceriam no fim de uma corrida de ~20 min (ou de uma campanha inteira). O
espelho, o parse de nome, a fila da campanha e o agrupamento por indicador
sao puro Python -- entao se testam em segundos.

    python test_ready_library.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import campanha
import ready_library as rl
from optimize_two_stage import melhor_por_indicador

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def checar_contem(rotulo: str, texto: str, trecho: str) -> None:
    if trecho not in texto:
        FALHAS.append(f"{rotulo}: nao achei {trecho!r}")


# --- parse do nome de entrega ------------------------------------------------
n = rl.analisar_nome("VALIDADO_EURUSD_HT_01_SLTP_SELL_MULTI.set")
checar("nome simples: simbolo", n["simbolo"], "EURUSD_HT")
checar("nome simples: sistema", n["sistema"], "01_SLTP")
checar("nome simples: variante", n["variante"], "SELL_MULTI")
checar("nome simples: exibicao", n["simbolo_exibicao"], "EURUSD.HT")

# Sistema com underscore + variante BOTH: o regex nao pode cortar cedo.
n = rl.analisar_nome("VALIDADO_XAGUSD_HT_08_GRID_UNIFIED_BOTH_ICHIMOKU.set")
checar("nome composto: sistema", n["sistema"], "08_GRID_UNIFIED")
checar("nome composto: variante", n["variante"], "BOTH_ICHIMOKU")

# Simbolo com digitos (US30): o `\d{2}_` do sistema nao pode morder o simbolo.
n = rl.analisar_nome("VALIDADO_US30_HT_04_SLTP_TRAIL_BUY_MULTI.set")
checar("simbolo com digitos", (n["simbolo"], n["sistema"]),
       ("US30_HT", "04_SLTP_TRAIL"))

checar("nome fora do padrao", rl.analisar_nome("VALIDADO_qualquercoisa.set"),
       None)

# --- fila da campanha: ICHIMOKU presente, sistemas antes de variantes --------
vs = campanha.variantes("01_SLTP")
checar("variantes unilaterais", vs,
       ["BUY_MULTI", "SELL_MULTI", "BUY_ICHIMOKU", "SELL_ICHIMOKU"])
vs = campanha.variantes("08_GRID_UNIFIED")
checar("variantes bilaterais", vs, ["BOTH_MULTI", "BOTH_ICHIMOKU"])

# --- melhor_por_indicador: um campeao por valor, ordem preservada ------------
CAB = ["Pass", "Profit", "Trades", "EntryIndicator", "Fast_EMA"]
LINHAS = [
    ["1", "900", "200", "3", "12"],    # Stochastic, melhor geral
    ["2", "800", "180", "3", "9"],     # Stochastic de novo: nao repete
    ["3", "700", "150", "5", "12"],    # RSI
    ["4", "600", "220", "0", "6"],     # MACD
]
campeoes = melhor_por_indicador(CAB, LINHAS)
checar("campeoes: um por indicador", [c[3] for c in campeoes], ["3", "5", "0"])
checar("campeoes: melhor do grupo", campeoes[0][1], "900")

# Sem coluna EntryIndicator (variante ICHIMOKU): grupo unico.
checar("ichimoku: grupo unico",
       melhor_por_indicador(["Pass", "Profit"], [["1", "5"], ["2", "3"]]),
       [["1", "5"]])

# --- espelho de prontos ------------------------------------------------------
UTF16 = "utf-16"
CONTEUDO = ("; teste\r\nCapitalBaseR=15000||15000||0||15000||N\r\n"
            "Stop=3.0||1.0||0.5||5.0||Y\r\n")

with tempfile.TemporaryDirectory() as tmp:
    raiz = Path(tmp)
    bib = raiz / "Biblioteca"
    tester = raiz / "Tester"
    destino = raiz / "PRONTOS"
    ledger = raiz / "ledger.jsonl"

    for no in ("01_Forex/EURUSD/01_SLTP", "01_Forex/EURUSD/03_TRAIL_ONLY",
               "01_Forex/GBPUSD/01_SLTP", "02_Metals/XAUUSD/01_SLTP"):
        (bib / no).mkdir(parents=True)
        (bib / no / "BUY_MULTI.set").write_text(CONTEUDO, encoding=UTF16)
    tester.mkdir()
    for nome in ("VALIDADO_EURUSD_HT_01_SLTP_BUY_MULTI.set",
                 "VALIDADO_XAUUSD_HT_01_SLTP_BUY_MULTI.set",
                 "VALIDADO_estranho.set"):
        (tester / nome).write_text(CONTEUDO, encoding=UTF16)
    ledger.write_text(json.dumps({
        "simbolo": "EURUSD.HT", "sistema": "01_SLTP", "variante": "BUY_MULTI",
        "retencao_oos": 41.5, "expectancy_r": 0.157, "trades_oos": 410,
        "aprovado": True}) + "\n", encoding="utf-8")

    r = rl.sincronizar(bib, tester, destino, ledger)
    checar("sync: prontos", r["prontos"], 2)
    checar("sync: copiados", r["copiados"], 2)
    checar("sync: aviso do nome estranho", len(r["avisos"]), 1)

    m = rl.MARCA
    marcado = destino / f"{m}01_Forex" / f"{m}EURUSD" / f"{m}01_SLTP" / f"{m}BUY_MULTI.set"
    checar("sync: marcador no lugar", marcado.is_file(), True)
    checar("sync: pasta ancestral marcada (classe)",
           (destino / f"{m}01_Forex").is_dir(), True)
    checar("sync: pasta ancestral marcada (ativo)",
           (destino / f"{m}01_Forex" / f"{m}EURUSD").is_dir(), True)
    checar("sync: sistema irmao sem set pronto fica sem marca",
           (destino / f"{m}01_Forex" / f"{m}EURUSD" / "03_TRAIL_ONLY").is_dir(),
           True)
    checar("sync: ativo sem nada pronto fica sem marca",
           (destino / f"{m}01_Forex" / "GBPUSD" / "01_SLTP").is_dir(), True)
    checar("sync: outra classe com set pronto tambem marca",
           (destino / f"{m}02_Metals" / f"{m}XAUUSD" / f"{m}01_SLTP" /
            f"{m}BUY_MULTI.set").is_file(), True)

    mapa = (destino / "MAPA.md").read_text(encoding="utf-8")
    checar_contem("mapa: marca do EURUSD", mapa, "**EURUSD**: *01_SLTP/BUY_MULTI")
    checar_contem("mapa: ativos sem pronto", mapa, "(1 ativos sem set pronto)")

    port = (destino / rl.PASTA_PORTFOLIOS / "01_SLTP.md").read_text(encoding="utf-8")
    checar_contem("portfolio: membro com metricas", port,
                  "| EURUSD.HT | BUY_MULTI | 41.5% | +0.157R | 410 | n/d "
                  "| 15000 |")
    checar_contem("portfolio: membro sem ledger", port,
                  "| XAUUSD.HT | BUY_MULTI | n/d |")
    checar_contem("portfolio: capital somado", port, "30,000")

    # Idempotencia: nada muda, nada copia.
    r2 = rl.sincronizar(bib, tester, destino, ledger)
    checar("resync: nada a copiar", r2["copiados"], 0)
    checar("resync: nada a remover", r2["removidos"], 0)

    # Rebaixamento: sumiu o VALIDADO_, o marcador e o portfolio acompanham.
    (tester / "VALIDADO_XAUUSD_HT_01_SLTP_BUY_MULTI.set").unlink()
    r3 = rl.sincronizar(bib, tester, destino, ledger)
    checar("rebaixado: removido do espelho", r3["removidos"], 1)
    checar("rebaixado: prontos", r3["prontos"], 1)
    checar("rebaixado: pasta ancestral perde a marca (nada mais embaixo)",
           (destino / "02_Metals").is_dir(), True)
    checar("rebaixado: pasta marcada antiga nao sobrevive",
           (destino / f"{m}02_Metals").exists(), False)
    port = (destino / rl.PASTA_PORTFOLIOS / "01_SLTP.md").read_text(encoding="utf-8")
    checar("rebaixado: fora do portfolio", "XAUUSD" in port, False)


if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  - {f}")
    sys.exit(1)
print("ok: espelho, nomes, fila e agrupamento por indicador")
