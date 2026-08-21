# -*- coding: utf-8 -*-
"""Testa o loop EM_PROVA sem precisar do MT5 nem do dashboard -- puro Python
sobre dados sinteticos e o relatorio real ja usado como smoke test manual,
mesmo espirito de test_auto_manager_live.py.

    python test_em_prova.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path as _Path

import pandas as pd

import em_prova

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


# --- tabela_magics / combo_do_magic (via manifesto sintetico) ---------------
with tempfile.TemporaryDirectory() as tmp:
    manifesto = _Path(tmp) / "MANIFESTO_SISTEMAS.csv"
    linhas = [
        {"Class": "01_Forex", "Symbol": "EURUSD", "System": "07_GRID_SEPARATE",
         "Side": "BUY", "Variant": "MULTI", "MagicNumber": "610000123"},
        {"Class": "01_Forex", "Symbol": "EURGBP", "System": "09_MARTINGALE",
         "Side": "SELL", "Variant": "ICHIMOKU", "MagicNumber": "610000456"},
    ]
    with manifesto.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(linhas[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)

    tabela = em_prova._tabela_magics_do_manifesto(manifesto)
    checar("magic BUY_MULTI resolve", tabela.get(610000123),
           "EURUSD__07_GRID_SEPARATE__BUY_MULTI")
    checar("magic SELL_ICHIMOKU resolve", tabela.get(610000456),
           "EURGBP__09_MARTINGALE__SELL_ICHIMOKU")
    checar("combo_do_magic com tabela real", em_prova.combo_do_magic(610000123, tabela),
           "EURUSD__07_GRID_SEPARATE__BUY_MULTI")

checar("combo_do_magic: magic=0 -> None (ordem manual/mobile)",
       em_prova.combo_do_magic(0, {0: "nao_deveria_bater"}), None)
checar("combo_do_magic: magic=None -> None", em_prova.combo_do_magic(None, {}), None)
checar("combo_do_magic: magic desconhecido -> None",
       em_prova.combo_do_magic(999999999, {}), None)


# --- tabela_magics recomputada (fallback sem manifesto) ----------------------
tabela_recomputada = em_prova._tabela_magics_recomputada()
checar("recomputada: tamanho bate com o manifesto real (3916 combos)",
       len(tabela_recomputada), 3916)


# --- ler_relatorio_historico (formato real: Trade History Report) -----------
def _relatorio_sintetico_historico(linhas: list[tuple]) -> str:
    """linhas: (tempo_abertura, ticket, simbolo, tipo, comentario, volume,
    preco, tempo_fechamento, preco_fecha, comissao, swap, lucro)."""
    corpo = "\n".join(
        f'<tr bgcolor="#FFFFFF" align="right">'
        f"<td>{ta}</td><td>{tk}</td><td>{sm}</td><td>{tp}</td>"
        f'<td class="hidden" colspan="8">{cm}</td>'
        f'<td class="">{vol}</td><td class="">{pr}</td>'
        f'<td class=""></td><td class=""></td>'
        f'<td class="">{tf}</td><td class="">{pf}</td>'
        f'<td class="">{co}</td><td class="">{sw}</td>'
        f'<td colspan="2">{lu}</td></tr>'
        for ta, tk, sm, tp, cm, vol, pr, tf, pf, co, sw, lu in linhas
    )
    return f"""<html><body>
    <table><tr align="center"><th colspan="14" style="height:25px">
    <div style="font:10pt Tahoma"><b>Positions</b></div></th></tr>
    <tr align="center" bgcolor="#E5F0FC">
      <td nowrap style="height:30px"><b>Time</b></td>
      <td nowrap><b>Position</b></td><td nowrap><b>Symbol</b></td>
      <td nowrap><b>Type</b></td><td nowrap><b>Volume</b></td>
      <td nowrap><b>Price</b></td><td nowrap><b>S / L</b></td>
      <td nowrap><b>T / P</b></td><td nowrap><b>Time</b></td>
      <td nowrap><b>Price</b></td><td nowrap><b>Commission</b></td>
      <td nowrap><b>Swap</b></td><td nowrap colspan="2"><b>Profit</b></td>
    </tr>
    {corpo}
    <tr><th colspan="14">Orders</th></tr>
    </table></body></html>"""


with tempfile.TemporaryDirectory() as tmp:
    caminho = _Path(tmp) / "historico.html"
    conteudo = _relatorio_sintetico_historico([
        ("2026.08.13 16:30:00", "728886016", "EURUSD", "sell",
         "Sell / Grid / FixedLot / Unifie", "0.01", "1.15352",
         "2026.08.17 18:02:50", "1.15853", "-0.04", "0.00", "-5.01"),
        ("2026.08.13 17:15:00", "728960494", "EURUSD", "buy",
         "Buy / Grid / FixedLot / Unified", "0.01", "1.15416",
         "2026.08.17 00:05:01", "1.15639", "-0.04", "0.00", "2.23"),
    ])
    caminho.write_bytes(("\ufeff" + conteudo).encode("utf-16"))
    df = em_prova.ler_relatorio_historico(caminho)
    checar("ler_relatorio_historico: numero de posicoes (celula hidden filtrada)",
           len(df) if df is not None else None, 2)
    checar("ler_relatorio_historico: simbolo", list(df["simbolo"]),
           ["EURUSD", "EURUSD"])
    checar("ler_relatorio_historico: tipo", list(df["tipo"]), ["sell", "buy"])
    checar("ler_relatorio_historico: lucro", list(df["lucro"]), [-5.01, 2.23])
    checar("ler_relatorio_historico: magic ausente -> None (nao 0)",
           list(df["magic"]), [None, None])
    checar("ler_relatorio_historico: ticket extraido",
           list(df["ticket"]), ["728886016", "728960494"])

    caminho_vazio = _Path(tmp) / "vazio.html"
    caminho_vazio.write_bytes("<html><body>nada</body></html>".encode("utf-8"))
    checar("ler_relatorio_historico: sem secao Positions -> None",
           em_prova.ler_relatorio_historico(caminho_vazio), None)

    checar("ler_relatorio_historico: arquivo inexistente -> None",
           em_prova.ler_relatorio_historico(_Path(tmp) / "nao_existe.html"), None)


# --- smoke manual: relatorio real colado na conversa -------------------------
_REAL = _Path(r"C:\Users\Lucas Pedroso\Desktop\07_GRID_SEPARATE\ReportHistory-77034660.html")
if _REAL.is_file():
    df_real = em_prova.ler_relatorio_historico(_REAL)
    checar("relatorio real: 15 posicoes extraidas",
           len(df_real) if df_real is not None else None, 15)
    checar("relatorio real: nenhum magic (coluna nao habilitada neste export)",
           df_real["magic"].isna().all() if df_real is not None else False, True)


# --- status_ao_vivo: maquina de estados ---------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    ledger = _Path(tmp) / "ledger.jsonl"
    ledger.write_text(json.dumps({
        "simbolo": "EURUSD", "sistema": "01_SLTP", "variante": "BUY_MULTI",
        "expectancy_r": 0.30,
    }) + "\n", encoding="utf-8")
    chave = "EURUSD__01_SLTP__BUY_MULTI"

    sem_baseline = em_prova.status_ao_vivo(
        "EURUSD__07_GRID_SEPARATE__BUY_MULTI",
        pd.DataFrame({"ticket": [], "lucro": []}), ledger, {})
    checar("sem expectancy_r no ledger -> SEM_BASELINE",
           sem_baseline["status"], "SEM_BASELINE")

    poucos_trades = pd.DataFrame({"ticket": [str(i) for i in range(5)],
                                  "lucro": [0.3] * 5})
    r = em_prova.status_ao_vivo(chave, poucos_trades, ledger, {})
    checar("menos que MIN_TRADES_PROVA -> EM_PROVA", r["status"], "EM_PROVA")
    checar("EM_PROVA carrega alocacao reduzida",
           r["alocacao"], em_prova.ALOCACAO_REDUZIDA_EM_PROVA)

    dentro_faixa = pd.DataFrame({"ticket": [str(i) for i in range(25)],
                                 "lucro": [0.30] * 25})
    r = em_prova.status_ao_vivo(chave, dentro_faixa, ledger, {})
    checar("trades ao vivo igual ao baseline -> DENTRO_DA_FAIXA",
           r["status"], "DENTRO_DA_FAIXA")

    ruins = pd.DataFrame({"ticket": [str(i) for i in range(25)],
                          "lucro": [-0.5] * 25})
    estado: dict = {}
    for rodada in range(5):
        r = em_prova.status_ao_vivo(chave, ruins, ledger, estado)
        estado[chave] = r
    checar("5 avaliacoes seguidas abaixo da faixa -> REBAIXAR",
           r["status"], "REBAIXAR")

    bons = pd.DataFrame({"ticket": [str(i) for i in range(25)],
                         "lucro": [1.5] * 25})
    estado = {}
    for rodada in range(5):
        r = em_prova.status_ao_vivo(chave, bons, ledger, estado)
        estado[chave] = r
    checar("5 avaliacoes seguidas acima da faixa -> PROMOVER",
           r["status"], "PROMOVER")

    # ticket excluido (ruido de infra marcado a mao) nao conta na amostra
    excluidos_path_original = em_prova.EXCLUIDOS_PATH
    em_prova.EXCLUIDOS_PATH = _Path(tmp) / "excluidos.json"
    em_prova.EXCLUIDOS_PATH.write_text(
        json.dumps([str(i) for i in range(20)]), encoding="utf-8")
    r = em_prova.status_ao_vivo(chave, ruins, ledger, {})
    em_prova.EXCLUIDOS_PATH = excluidos_path_original
    checar("tickets excluidos nao contam pro minimo de trades (20 de 25 excluidos)",
           r["status"], "EM_PROVA")


if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  {f}")
    sys.exit(1)
print("ok")
