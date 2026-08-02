# -*- coding: utf-8 -*-
"""Gera o painel visual do portfolio: um HTML autocontido.

Numero em tabela nao mostra QUANDO cada estrategia sofre -- e e disso que
depende a decisao de portfolio. Duas curvas podem ter o mesmo resultado e o
mesmo drawdown e, ainda assim, uma salvar a outra ou as duas afundarem juntas.
Sobrepor as curvas responde isso de um olhar.

O arquivo nao busca nada na rede: os graficos sao SVG desenhado aqui. Abre
offline, em qualquer navegador, sem depender de CDN.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

CORES = [
    "#60a5fa",
    "#34d399",
    "#fbbf24",
    "#f87171",
    "#a78bfa",
    "#22d3ee",
    "#fb923c",
    "#4ade80",
    "#f472b6",
    "#94a3b8",
]


def _participacao_barras(escolhidas: list[str], pesos: dict[str, float]) -> str:
    total = sum(pesos[n] for n in escolhidas)
    if not total:
        return ""
    linhas = []
    for i, nome in enumerate(escolhidas):
        pct = (pesos[nome] / total) * 100.0
        linhas.append(
            f'<div class="bar-row"><div class="bar-meta"><span class="bolinha" '
            f'style="background:{CORES[i % len(CORES)]}"></span>{html.escape(nome)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;'
            f'background:{CORES[i % len(CORES)]}"></div></div>'
            f'<span class="bar-pct">{pct:.1f}%</span></div>'
        )
    return "".join(linhas)


def _caminho_svg(
    valores: list[float], largura: int, altura: int, minimo: float, maximo: float
) -> str:
    if len(valores) < 2 or maximo <= minimo:
        return ""
    passo = largura / (len(valores) - 1)
    faixa = maximo - minimo
    pontos = [
        f"{i * passo:.1f},{altura - (v - minimo) / faixa * altura:.1f}"
        for i, v in enumerate(valores)
    ]
    return "M" + " L".join(pontos)


def _grafico_curvas(
    series: dict[str, pd.Series], escolhidas: list[str], pesos: dict[str, float]
) -> str:
    largura, altura = 1000, 320
    curvas = {n: series[n].cumsum() for n in escolhidas}
    combinado = sum(series[n] * pesos[n] for n in escolhidas).cumsum()

    todos = [v for c in curvas.values() for v in c.tolist()] + combinado.tolist()
    if not todos:
        return ""
    minimo, maximo = min(todos), max(todos)
    folga = (maximo - minimo) * 0.05 or 1.0
    minimo, maximo = minimo - folga, maximo + folga

    partes = [
        f'<svg viewBox="0 0 {largura} {altura}" '
        f'preserveAspectRatio="none" class="grafico">'
    ]
    # Linha do zero: separa lucro de prejuizo sem precisar ler eixo.
    if minimo < 0 < maximo:
        y = altura - (0 - minimo) / (maximo - minimo) * altura
        partes.append(
            f'<line x1="0" y1="{y:.1f}" x2="{largura}" ' f'y2="{y:.1f}" class="zero"/>'
        )
    for i, (_nome, curva) in enumerate(curvas.items()):
        d = _caminho_svg(curva.tolist(), largura, altura, minimo, maximo)
        if d:
            partes.append(
                f'<path d="{d}" fill="none" '
                f'stroke="{CORES[i % len(CORES)]}" '
                f'stroke-width="1.5" opacity="0.75"/>'
            )
    d = _caminho_svg(combinado.tolist(), largura, altura, minimo, maximo)
    if d:
        partes.append(
            f'<path d="{d}" fill="none" stroke="#e2e8f0" ' f'stroke-width="3"/>'
        )
    partes.append("</svg>")
    return "".join(partes)


def _heatmap(correl: pd.DataFrame, escolhidas: list[str]) -> str:
    nomes = list(correl.columns)
    saida = ['<table class="heat"><thead><tr><th></th>']
    for n in nomes:
        marca = " *" if n in escolhidas else ""
        saida.append(
            f'<th title="{html.escape(n)}">' f"{html.escape(n[:12])}{marca}</th>"
        )
    saida.append("</tr></thead><tbody>")
    for a in nomes:
        marca = " *" if a in escolhidas else ""
        saida.append(
            f'<tr><th title="{html.escape(a)}">' f"{html.escape(a[:18])}{marca}</th>"
        )
        for b in nomes:
            v = float(correl.loc[a, b])
            # Vermelho: andam juntas (nao diversificam).
            # Verde: opostas (uma protege a outra).
            if a == b:
                cor, texto = "#1e293b", "#64748b"
            elif v > 0:
                cor = f"rgba(248,113,113,{min(abs(v), 1) * 0.85:.2f})"
                texto = "#ffffff" if v > 0.5 else "#e2e8f0"
            else:
                cor = f"rgba(52,211,153,{min(abs(v), 1) * 0.85:.2f})"
                texto = "#ffffff" if abs(v) > 0.5 else "#e2e8f0"
            saida.append(f'<td style="background:{cor};color:{texto}">' f"{v:.2f}</td>")
        saida.append("</tr>")
    saida.append("</tbody></table>")
    return "".join(saida)


ESTILO = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;padding:32px;background:#0b1017;color:#e2e8f0;
 font:15px/1.6 "Segoe UI",system-ui,sans-serif}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:15px;margin:32px 0 12px;color:#94a3b8;font-weight:600;
 text-transform:uppercase;letter-spacing:.06em}
.sub{color:#64748b;margin:0 0 28px;font-size:13px}
.cartoes{display:grid;gap:14px;
 grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.cartao{background:#131c2b;border:1px solid #24344d;border-radius:10px;
 padding:16px}
.cartao .rot{font-size:11px;color:#64748b;text-transform:uppercase;
 letter-spacing:.07em}
.cartao .val{font-size:26px;font-weight:600;margin-top:6px}
.up{color:#34d399} .neg{color:#f87171}
.grafico{width:100%;height:320px;background:#0e1622;border:1px solid #24344d;
 border-radius:10px;margin-top:8px}
.zero{stroke:#334155;stroke-width:1;stroke-dasharray:4 4}
.bar-row{display:grid;grid-template-columns:minmax(160px,1fr) minmax(220px,1.5fr) 56px;align-items:center;gap:10px;margin:10px 0}
.bar-meta{display:flex;align-items:center;color:#e2e8f0;font-size:12.5px}
.bar-track{height:10px;background:#0e1622;border:1px solid #24344d;border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px}
.bar-pct{color:#94a3b8;font-size:11.5px;text-align:right}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 10px;border-bottom:1px solid #1e293b;text-align:left}
th{color:#64748b;font-weight:600;font-size:11px;text-transform:uppercase;
 letter-spacing:.05em}
.num{text-align:right;font-variant-numeric:tabular-nums}
.bolinha{display:inline-block;width:9px;height:9px;border-radius:50%;
 margin-right:9px}
.heat{font-size:11.5px}
.heat th{font-size:10px}
.heat td{text-align:center;padding:7px 4px;border:1px solid #0b1017;
 font-variant-numeric:tabular-nums}
.rolagem{overflow-x:auto}
.legenda{color:#64748b;font-size:12.5px;margin-top:10px}
.fora{color:#94a3b8;font-size:13.5px;margin:0;padding-left:20px}
"""


def gerar(
    destino: Path,
    series: dict[str, pd.Series],
    correl: pd.DataFrame,
    escolhidas: list[str],
    pesos: dict[str, float],
    metricas_fn,
    recusadas: list[str],
) -> None:
    m_ind = {n: metricas_fn(s) for n, s in series.items()}
    combinado = sum(series[n] * pesos[n] for n in escolhidas)
    m_port = metricas_fn(combinado)
    melhor = max((m_ind[n]["sharpe"] for n in escolhidas), default=0.0)

    linhas = []
    for i, nome in enumerate(escolhidas):
        m = m_ind[nome]
        linhas.append(
            f'<tr><td><span class="bolinha" style="background:'
            f'{CORES[i % len(CORES)]}"></span>{html.escape(nome)}</td>'
            f'<td class="num">{pesos[nome]:.1%}</td>'
            f'<td class="num">{m["resultado"]:,.0f}</td>'
            f'<td class="num neg">{m["drawdown"]:,.0f}</td>'
            f'<td class="num">{m["recuperacao"]:.2f}</td>'
            f'<td class="num">{m["sharpe"]:.2f}</td></tr>'
        )

    bloco_fora = ""
    if recusadas:
        itens = "".join(f"<li>{html.escape(r)}</li>" for r in recusadas)
        bloco_fora = (
            "<section><h2>Fora do portfolio</h2>"
            f'<ul class="fora">{itens}</ul></section>'
        )

    classe_res = "up" if m_port["resultado"] > 0 else "neg"
    corpo = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio White Rabbit X</title>
<style>{ESTILO}</style></head><body>
<h1>Portfolio White Rabbit X</h1>
<p class="sub">{len(escolhidas)} estrategias de {len(series)} avaliadas &middot;
 alocacao por paridade de volatilidade</p>

<div class="cartoes">
 <div class="cartao"><div class="rot">Resultado</div>
  <div class="val {classe_res}">{m_port['resultado']:,.0f}</div></div>
 <div class="cartao"><div class="rot">Drawdown</div>
  <div class="val neg">{m_port['drawdown']:,.0f}</div></div>
 <div class="cartao"><div class="rot">Recuperacao</div>
  <div class="val">{m_port['recuperacao']:.2f}</div></div>
 <div class="cartao"><div class="rot">Sharpe</div>
  <div class="val">{m_port['sharpe']:.2f}</div>
  <div class="rot" style="margin-top:6px">melhor sozinha: {melhor:.2f}</div>
 </div>
</div>

<h2>Curvas acumuladas</h2>
{_grafico_curvas(series, escolhidas, pesos)}
<p class="legenda">A linha branca grossa e o portfolio ponderado; as coloridas
 sao os componentes. O que importa aqui nao e quem sobe mais, e se as quedas
 acontecem no mesmo lugar.</p>

<h2>Participacao no portfolio</h2>
<div class="rolagem">{_participacao_barras(escolhidas, pesos)}</div>
<p class="legenda">Cada faixa mostra a proporcao de peso no desenho final.
 O ideal e balances de risco com pouca co-movimentacao entre as linhas.</p>

<h2>Composicao</h2>
<table><thead><tr><th>Estrategia</th><th class="num">Peso</th>
<th class="num">Resultado</th><th class="num">Drawdown</th>
<th class="num">Recuperacao</th><th class="num">Sharpe</th></tr></thead>
<tbody>{''.join(linhas)}</tbody></table>

<h2>Correlacao entre as curvas</h2>
<div class="rolagem">{_heatmap(correl, escolhidas)}</div>
<p class="legenda">Vermelho: sobem e descem juntas, nao diversificam.
 Verde: opostas, uma protege a outra -- o melhor caso.
 O asterisco marca quem entrou no portfolio.</p>

{bloco_fora}
</body></html>"""
    destino.write_text(corpo, encoding="utf-8")
