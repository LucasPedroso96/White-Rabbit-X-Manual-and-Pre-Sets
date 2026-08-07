# -*- coding: utf-8 -*-
"""Testa o parser da secao Resultados SEM precisar do MT5 nem de um relatorio
real (campanha_relatorios/ nao pode ser versionado -- esta no .gitignore).

O HTML sintetico abaixo reproduz a estrutura REAL de um relatorio MT5
(6 secoes com titulo colspan=13: Relatorio, Corretora, Configuracao,
Resultados, Ordens, Transacoes -- confirmada contra um relatorio arquivado de
verdade em campanha_relatorios/EURUSD__08_GRID_UNIFIED__BOTH_ICHIMOKU/), so
com menos linhas de dado.

    python test_relatorio_resumo.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import relatorio_resumo as rr

FALHAS: list[str] = []


def checar(rotulo: str, obtido, esperado) -> None:
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: esperado {esperado!r}, obtido {obtido!r}")


def _titulo(texto: str) -> str:
    return f'<tr><td colspan="13"><div style="font: 10pt Tahoma"><b>{texto}</b></div></td></tr>'


HTML_SINTETICO = "<html><body><table>" + "".join([
    _titulo("Relatório do Testador de Estratégia"),
    "<tr><td>x</td></tr>",
    _titulo("RoboForex-ECN (Build 5830)"),
    "<tr><td>x</td></tr>",
    _titulo("Configuração"),
    "<tr><td>Symbol=EURUSD</td></tr>",
    _titulo("Resultados"),
    "<tr><td>Lucro Líquido Total:</td><td></td><td>889.45</td></tr>",
    "<tr><td>Fator de Lucro:</td><td></td><td>1.90</td></tr>",
    "<tr><td>Fator de Recuperação:</td><td></td><td>2.42</td></tr>",
    "<tr><td>Índice de Sharpe:</td><td></td><td>1.07</td></tr>",
    "<tr><td>Rebaixamento Relativo do Saldo :</td><td></td><td>18.45% (117.47)</td></tr>",
    "<tr><td>Máximo ganhos consecutivos ($):</td><td></td><td>10 (36.81)</td></tr>",
    "<tr><td>Qualidade do histórico:</td><td></td><td>100% de ticks reais</td></tr>",
    _titulo("Ordens"),
    "<tr><td>2024.01.01</td><td>ordem que nao deve entrar no resumo</td></tr>",
    _titulo("Transações"),
    "<tr><td>2024.01.01</td><td>deal que nao deve entrar no resumo</td></tr>",
]) + "</table></body></html>"


pares = rr.extrair_pares(HTML_SINTETICO)
checar("pares: nao vaza secao Ordens", "2024.01.01" in pares, False)
checar("pares: profit factor bruto", pares.get("Fator de Lucro"), "1.90")

with tempfile.TemporaryDirectory() as tmp:
    caminho = Path(tmp) / "conf_wrx.htm"
    caminho.write_text(HTML_SINTETICO, encoding="utf-16")

    resumo = rr.resumo_relatorio(caminho)
    checar("resumo: profit_factor", resumo["profit_factor"], "1.90")
    checar("resumo: recovery_factor", resumo["recovery_factor"], "2.42")
    checar("resumo: sharpe_ratio", resumo["sharpe_ratio"], "1.07")
    checar("resumo: balance_dd_relative", resumo["balance_dd_relative"],
           "18.45% (117.47)")
    checar("resumo: max_consecutive_wins", resumo["max_consecutive_wins"],
           "10 (36.81)")
    checar("resumo: quality_of_history", resumo["quality_of_history"],
           "100% de ticks reais")
    # Nao existe no HTML sintetico -- tem que voltar None, nunca inventar.
    checar("resumo: campo ausente vira None", resumo["z_score"], None)

    faltando = Path(tmp) / "nao_existe.htm"
    resumo_vazio = rr.resumo_relatorio(faltando)
    checar("resumo: arquivo ausente -- tudo None",
           all(v is None for v in resumo_vazio.values()), True)

if FALHAS:
    print(f"{len(FALHAS)} falha(s):")
    for f in FALHAS:
        print(f"  - {f}")
    sys.exit(1)
print("ok: parser da secao Resultados")
