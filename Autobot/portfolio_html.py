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

# Paleta Okabe–Ito (legível por daltônicos, sobre fundo escuro). Passando de 5 séries a cor
# sozinha não separa mais: da 6ª em diante a linha do gráfico sai tracejada (ver _traco()).
CORES = [
    "#e69f00",
    "#56b4e9",
    "#2fc59a",
    "#f0e442",
    "#4d9de0",
    "#ff7f50",
    "#cc79a7",
    "#b8c2cc",
    "#a8d85a",
    "#9d8cff",
]


def _traco(i: int) -> str:
    """Séries 0-4 contínuas; 5-9 tracejadas (a forma separa o que a cor não separa)."""
    return "" if i < 5 else ' stroke-dasharray="7 4"'


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
            f'<line x1="0" y1="{y:.1f}" x2="{largura}" ' f'y2="{y:.1f}" class="zero" vector-effect="non-scaling-stroke"/>'
        )
    for i, (_nome, curva) in enumerate(curvas.items()):
        d = _caminho_svg(curva.tolist(), largura, altura, minimo, maximo)
        if d:
            partes.append(
                f'<path d="{d}" fill="none" '
                f'stroke="{CORES[i % len(CORES)]}"{_traco(i)} '
                f'stroke-width="1.75" vector-effect="non-scaling-stroke" opacity="0.85"/>'
            )
    d = _caminho_svg(combinado.tolist(), largura, altura, minimo, maximo)
    if d:
        partes.append(
            f'<path d="{d}" class="combinado" fill="none" '
            f'stroke-width="3" vector-effect="non-scaling-stroke"/>'
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
            # Laranja: andam juntas (nao diversificam). Azul: opostas (uma protege a outra).
            # Divergente laranja x azul: segue legivel para daltonico; o numero fica sempre na celula.
            if a == b:
                cor, texto = "var(--surface-2)", "var(--text-3)"
            elif v > 0:
                cor = f"color-mix(in srgb, var(--warn) {min(abs(v), 1) * 85:.0f}%, transparent)"
                texto = "var(--text)"
            else:
                cor = f"color-mix(in srgb, var(--info) {min(abs(v), 1) * 85:.0f}%, transparent)"
                texto = "var(--text)"
            saida.append(f'<td style="background:{cor};color:{texto}">' f"{v:.2f}</td>")
        saida.append("</tr>")
    saida.append("</tbody></table>")
    return "".join(saida)


ESTILO = """
/* Mesa (tokens): Noite por padrao, Dia segue o aparelho. Relatorio autocontido: sem CDN. */
:root{--bg:#0b0f14;--surface:#121820;--surface-2:#18202a;--surface-3:#222c39;--line:#232e3b;--border:#6b7a8d;--scrim:#05080cb3;--text:#e8ecf1;--text-2:#aab4c2;--text-3:#8c98a8;--ink:#e8ecf1;--on-ink:#0b0f14;--focus:#e8ecf1;--ok:#3ecf8e;--ok-soft:#10281f;--warn:#f0a43a;--warn-soft:#2f2310;--bad:#ff6b5e;--bad-soft:#35191b;--info:#7aa5ff;--info-soft:#152340;--off:#8c98a8;--pnl-up:#3ecf8e;--pnl-down:#ff6b5e;--sys-mesa:#e8ecf1;--sys-zeus:#c6963a;--sys-claudetrader:#34d6c4;--sys-bigguys:#4b94ec;--sys-levain:#a08cff;--sys-correlation:#d28be8;--sys-whiterabbit:#d9d2bf;--on-sys:#0b0f14;--shadow-float:0 8px 24px #00000066,0 1px 2px #0000004d;--shadow-sheet:0 -12px 32px #00000099}@media (prefers-color-scheme:light){:root:not([data-theme]){--bg:#f3f5f8;--surface:#ffffff;--surface-2:#eceff3;--surface-3:#dde3ea;--line:#dbe0e7;--border:#6f7b8a;--scrim:#14181d73;--text:#14181d;--text-2:#454f5e;--text-3:#596575;--ink:#14181d;--on-ink:#ffffff;--focus:#14181d;--ok:#17744a;--ok-soft:#dcf2e6;--warn:#8f5200;--warn-soft:#faebd0;--bad:#b42318;--bad-soft:#fbe0dd;--info:#2457c5;--info-soft:#dde8fb;--off:#596575;--pnl-up:#17744a;--pnl-down:#b42318;--sys-mesa:#14181d;--sys-zeus:#8f6518;--sys-claudetrader:#0a7266;--sys-bigguys:#1f64bd;--sys-levain:#5b43d6;--sys-correlation:#9a3db8;--sys-whiterabbit:#6a5f45;--on-sys:#ffffff;--shadow-float:0 8px 24px #14181d29,0 1px 2px #14181d14;--shadow-sheet:0 -12px 32px #14181d33}}:root[data-theme="dark"]{--bg:#0b0f14;--surface:#121820;--surface-2:#18202a;--surface-3:#222c39;--line:#232e3b;--border:#6b7a8d;--scrim:#05080cb3;--text:#e8ecf1;--text-2:#aab4c2;--text-3:#8c98a8;--ink:#e8ecf1;--on-ink:#0b0f14;--focus:#e8ecf1;--ok:#3ecf8e;--ok-soft:#10281f;--warn:#f0a43a;--warn-soft:#2f2310;--bad:#ff6b5e;--bad-soft:#35191b;--info:#7aa5ff;--info-soft:#152340;--off:#8c98a8;--pnl-up:#3ecf8e;--pnl-down:#ff6b5e;--sys-mesa:#e8ecf1;--sys-zeus:#c6963a;--sys-claudetrader:#34d6c4;--sys-bigguys:#4b94ec;--sys-levain:#a08cff;--sys-correlation:#d28be8;--sys-whiterabbit:#d9d2bf;--on-sys:#0b0f14;--shadow-float:0 8px 24px #00000066,0 1px 2px #0000004d;--shadow-sheet:0 -12px 32px #00000099}:root[data-theme="light"]{--bg:#f3f5f8;--surface:#ffffff;--surface-2:#eceff3;--surface-3:#dde3ea;--line:#dbe0e7;--border:#6f7b8a;--scrim:#14181d73;--text:#14181d;--text-2:#454f5e;--text-3:#596575;--ink:#14181d;--on-ink:#ffffff;--focus:#14181d;--ok:#17744a;--ok-soft:#dcf2e6;--warn:#8f5200;--warn-soft:#faebd0;--bad:#b42318;--bad-soft:#fbe0dd;--info:#2457c5;--info-soft:#dde8fb;--off:#596575;--pnl-up:#17744a;--pnl-down:#b42318;--sys-mesa:#14181d;--sys-zeus:#8f6518;--sys-claudetrader:#0a7266;--sys-bigguys:#1f64bd;--sys-levain:#5b43d6;--sys-correlation:#9a3db8;--sys-whiterabbit:#6a5f45;--on-sys:#ffffff;--shadow-float:0 8px 24px #14181d29,0 1px 2px #14181d14;--shadow-sheet:0 -12px 32px #14181d33}:root[data-theme="safe"]{--ok:#56b4e9;--ok-soft:#0f2433;--warn:#f0e442;--warn-soft:#2b2a0c;--bad:#ff8a4a;--bad-soft:#33200f;--info:#e59ac4;--info-soft:#341a29;--pnl-up:#56b4e9;--pnl-down:#ff8a4a}:root{--space-1:4px;--space-2:8px;--space-3:12px;--space-4:16px;--space-5:20px;--space-6:24px;--space-8:32px;--space-10:40px;--space-12:48px;--touch-target:44px;--touch-gap:8px;--nav-height:56px;--content-max:1240px;--radius-xs:4px;--radius-sm:6px;--radius-md:8px;--radius-lg:12px;--radius-xl:20px;--radius-pill:999px;--bp-phone:560px;--bp-tablet:900px;--bp-wide:1240px;--z-sticky:10;--z-nav:20;--z-sheet:30;--z-toast:40;--font-display:"Instrument Serif",Georgia,"Times New Roman",serif;--font-sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--font-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Consolas,monospace}
:root{color-scheme:dark light}
*{box-sizing:border-box}
body{margin:0;padding:32px;max-width:1240px;margin-inline:auto;background:var(--bg);color:var(--text);
 font:15px/1.6 var(--font-sans)}
h1{font:400 32px/1.15 var(--font-display);margin:0 0 4px;color:var(--text)}
h2{font-size:12px;margin:32px 0 12px;color:var(--text-3);font-weight:600;
 text-transform:uppercase;letter-spacing:.14em}
.sub{color:var(--text-3);margin:0 0 28px;font-size:13px}
.cartoes{display:grid;gap:14px;
 grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.cartao{background:var(--surface);border:1px solid var(--line);border-radius:12px;
 padding:16px}
.cartao .rot{font-size:11px;color:var(--text-3);text-transform:uppercase;
 letter-spacing:.14em}
.cartao .val{font:600 26px/1.2 var(--font-mono);margin-top:6px;font-variant-numeric:tabular-nums}
.up{color:var(--pnl-up)} .neg{color:var(--pnl-down)}
.grafico{width:100%;height:320px;background:var(--surface);border:1px solid var(--line);
 border-radius:12px;margin-top:8px}
.zero{stroke:var(--border);stroke-width:1;stroke-dasharray:4 4}
.combinado{stroke:var(--text)}
.bar-row{display:grid;grid-template-columns:minmax(160px,1fr) minmax(220px,1.5fr) 56px;align-items:center;gap:10px;margin:10px 0}
.bar-meta{display:flex;align-items:center;color:var(--text);font-size:13px}
.bar-track{height:10px;background:var(--surface-2);border:1px solid var(--line);border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px}
.bar-pct{color:var(--text-2);font:12px var(--font-mono);text-align:right}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--text-3);font-weight:600;font-size:11px;text-transform:uppercase;
 letter-spacing:.1em}
.num{text-align:right;font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.bolinha{display:inline-block;width:9px;height:9px;border-radius:50%;
 margin-right:9px;flex:none}
.heat{font-size:12px}
.heat th{font-size:11px}
.heat td{text-align:center;padding:7px 4px;border:1px solid var(--bg);
 font-variant-numeric:tabular-nums}
.rolagem{overflow-x:auto}
.legenda{color:var(--text-3);font-size:13px;margin-top:10px}
.fora{color:var(--text-2);font-size:13.5px;margin:0;padding-left:20px}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
@media (max-width:560px){body{padding:16px}h1{font-size:26px}.bar-row{grid-template-columns:1fr 56px}.bar-track{grid-column:1/-1;grid-row:2}}
@media print{body{background:#fff;color:#000}}
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
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
<p class="legenda">A linha clara grossa e o portfolio ponderado; as coloridas
 sao os componentes (da sexta em diante, tracejadas). O que importa aqui nao e quem sobe mais, e se as quedas
 acontecem no mesmo lugar.</p>

<h2>Participacao no portfolio</h2>
<div class="rolagem">{_participacao_barras(escolhidas, pesos)}</div>
<p class="legenda">Cada faixa mostra a proporcao de peso no desenho final.
 O ideal e balances de risco com pouca co-movimentacao entre as linhas.</p>

<h2>Composicao</h2>
<div class="rolagem"><table><thead><tr><th>Estrategia</th><th class="num">Peso</th>
<th class="num">Resultado</th><th class="num">Drawdown</th>
<th class="num">Recuperacao</th><th class="num">Sharpe</th></tr></thead>
<tbody>{''.join(linhas)}</tbody></table></div>

<h2>Correlacao entre as curvas</h2>
<div class="rolagem">{_heatmap(correl, escolhidas)}</div>
<p class="legenda">Laranja: sobem e descem juntas, nao diversificam.
 Azul: opostas, uma protege a outra -- o melhor caso.
 O asterisco marca quem entrou no portfolio.</p>

{bloco_fora}
</body></html>"""
    destino.write_text(corpo, encoding="utf-8")
