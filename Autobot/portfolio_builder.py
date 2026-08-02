# -*- coding: utf-8 -*-
"""Monta portfolio escolhendo estrategias que NAO andam juntas.

Dez estrategias que ganham e perdem nos mesmos dias nao sao dez estrategias:
sao uma, com dez vezes o risco. O drawdown de todas chega no mesmo dia, e o
capital nao aguenta. E por isso que somar lucro nao basta para montar
portfolio -- o que decide e a correlacao entre as curvas.

O que este script faz:

  1. Le os relatorios do Strategy Tester (HTML) ou CSVs de trades
  2. Converte cada um numa serie DIARIA de resultado
  3. Calcula a correlacao entre todas as series
  4. Escolhe, de forma gulosa, o subconjunto de menor correlacao
  5. Aloca risco por paridade de volatilidade
  6. Mede o drawdown do conjunto, que e o numero que importa

Passo 6 e o que separa isto de somar planilhas: o drawdown de um portfolio nao
e a soma dos drawdowns, nem o maior deles. Depende de quando cada um acontece.

Uso:
    python portfolio_builder.py --relatorios pasta_com_htmls
    python portfolio_builder.py --relatorios pasta --max 8 --teto-correlacao 0.4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd


def _achar_coluna(df: pd.DataFrame, nomes: list[str]) -> str | None:
    """Procura coluna por nome, tolerando o idioma do terminal."""
    for coluna in df.columns:
        texto = str(coluna).strip().lower()
        for alvo in nomes:
            if alvo in texto:
                return coluna
    return None


def ler_html(path: Path) -> pd.DataFrame | None:
    """Extrai (tempo, lucro) do relatorio do Strategy Tester.

    O relatorio muda de idioma conforme o terminal, entao a tabela certa e
    localizada pelo formato dos dados -- datas na primeira coluna e uma coluna
    numerica de lucro -- e nao pelo titulo.
    """
    try:
        tabelas = pd.read_html(path, encoding="utf-8")
    except Exception:
        try:
            tabelas = pd.read_html(path)
        except Exception:
            return None

    melhor: pd.DataFrame | None = None
    for tabela in tabelas:
        if tabela.shape[0] < 5 or tabela.shape[1] < 4:
            continue
        # O MT5 costuma repetir o cabecalho como primeira linha de dados.
        if not isinstance(tabela.columns[0], str) or "Unnamed" in str(tabela.columns[0]):
            tabela = tabela.rename(columns=tabela.iloc[0]).drop(tabela.index[0])
        col_tempo = _achar_coluna(tabela, ["time", "tempo", "hora", "data"])
        col_lucro = _achar_coluna(tabela, ["profit", "lucro", "ganancia",
                                           "gewinn", "profitto"])
        if col_tempo is None or col_lucro is None:
            continue
        limpo = pd.DataFrame({
            "tempo": pd.to_datetime(tabela[col_tempo], errors="coerce"),
            "lucro": pd.to_numeric(
                tabela[col_lucro].astype(str).str.replace(" ", "")
                .str.replace(",", "."), errors="coerce"),
        }).dropna()
        if len(limpo) >= 5 and (melhor is None or len(limpo) > len(melhor)):
            melhor = limpo
    return melhor


def ler_csv(path: Path) -> pd.DataFrame | None:
    for sep in (";", ",", "\t"):
        try:
            bruto = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        except Exception:
            continue
        if bruto.shape[1] < 2:
            continue
        col_tempo = _achar_coluna(bruto, ["time", "tempo", "data", "date"])
        col_lucro = _achar_coluna(bruto, ["profit", "lucro", "resultado", "pnl"])
        if col_tempo is None or col_lucro is None:
            continue
        limpo = pd.DataFrame({
            "tempo": pd.to_datetime(bruto[col_tempo], errors="coerce"),
            "lucro": pd.to_numeric(bruto[col_lucro], errors="coerce"),
        }).dropna()
        if len(limpo) >= 5:
            return limpo
    return None


def serie_diaria(trades: pd.DataFrame) -> pd.Series:
    """Resultado por dia. Dias sem trade valem zero, e isso importa: sem eles
    a correlacao mediria so os dias em que ambas operaram."""
    diario = trades.set_index("tempo")["lucro"].resample("D").sum()
    return diario


def drawdown_maximo(curva: pd.Series) -> float:
    acumulado = curva.cumsum()
    pico = acumulado.cummax()
    return float((acumulado - pico).min())


def metricas(curva: pd.Series) -> dict:
    total = float(curva.sum())
    dd = drawdown_maximo(curva)
    operou = curva[curva != 0]
    vol = float(operou.std()) if len(operou) > 1 else 0.0
    # Sharpe diario anualizado; 252 dias uteis e a convencao.
    sharpe = (float(operou.mean()) / vol * np.sqrt(252)) if vol > 0 else 0.0
    return {
        "resultado": total,
        "drawdown": dd,
        "recuperacao": (total / abs(dd)) if dd < 0 else float("inf"),
        "sharpe": sharpe,
        "dias_operados": int(len(operou)),
    }


def selecionar(series: dict[str, pd.Series], maximo: int, teto: float,
               recuperacao_minima: float) -> tuple[list[str], pd.DataFrame, list[str]]:
    """Escolha gulosa entre as estrategias que se pagam.

    Duas regras que parecem detalhe e nao sao:

    ELEGIBILIDADE  estrategia que perde dinheiro nao entra, por mais
                   descorrelacionada que seja. Diversificar reduz o drawdown,
                   nao transforma prejuizo em lucro -- somar uma perdedora so
                   troca retorno por suavidade.

    SINAL DA CORRELACAO  o teto se aplica a correlacao POSITIVA. Correlacao
                   negativa e o melhor caso do portfolio: uma estrategia
                   ganha quando a outra perde, e as duas juntas oscilam menos
                   que qualquer uma sozinha. Cortar por valor absoluto
                   descartaria justamente o par mais valioso.
    """
    quadro = pd.DataFrame(series).fillna(0.0)
    correl = quadro.corr().fillna(0.0)

    avaliacao = {nome: metricas(serie) for nome, serie in series.items()}
    elegiveis, recusadas = [], []
    for nome, m in avaliacao.items():
        if m["resultado"] <= 0:
            recusadas.append(f"{nome}: resultado negativo")
        elif m["recuperacao"] < recuperacao_minima:
            recusadas.append(
                f"{nome}: recuperacao {m['recuperacao']:.2f} "
                f"abaixo de {recuperacao_minima:g}")
        else:
            elegiveis.append(nome)

    if not elegiveis:
        return [], correl, recusadas

    notas = {n: avaliacao[n]["recuperacao"] for n in elegiveis}
    escolhidas = [max(notas, key=notas.get)]

    while len(escolhidas) < maximo:
        candidatos = []
        for nome in elegiveis:
            if nome in escolhidas:
                continue
            # So a correlacao positiva incomoda; a negativa protege.
            pior = max(correl.loc[nome, j] for j in escolhidas)
            if pior > teto:
                continue
            candidatos.append((pior, -notas[nome], nome))
        if not candidatos:
            break
        candidatos.sort()
        escolhidas.append(candidatos[0][2])
    return escolhidas, correl, recusadas


def alocar(series: dict[str, pd.Series], nomes: list[str]) -> dict[str, float]:
    """Paridade de risco: quem oscila mais recebe menos. Sem isso, a estrategia
    mais volatil domina o portfolio inteiro e as outras viram decoracao."""
    vols = {}
    for nome in nomes:
        operou = series[nome][series[nome] != 0]
        vols[nome] = float(operou.std()) if len(operou) > 1 else 0.0
    invertido = {n: (1.0 / v if v > 0 else 0.0) for n, v in vols.items()}
    soma = sum(invertido.values())
    if soma <= 0:
        return {n: 1.0 / len(nomes) for n in nomes}
    return {n: v / soma for n, v in invertido.items()}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--relatorios", required=True,
                    help="pasta com os relatorios (.htm/.html/.csv)")
    ap.add_argument("--max", type=int, default=8,
                    help="quantas estrategias no portfolio")
    ap.add_argument("--teto-correlacao", type=float, default=0.5,
                    help="correlacao POSITIVA maxima aceita (negativa e bem-vinda)")
    ap.add_argument("--recuperacao-minima", type=float, default=1.0,
                    help="fator de recuperacao minimo para entrar no portfolio")
    ap.add_argument("--out", default="portfolio.csv")
    ap.add_argument("--html", default="portfolio.html",
                    help="painel visual autocontido; vazio desliga")
    args = ap.parse_args()

    pasta = Path(args.relatorios)
    if not pasta.is_dir():
        print(f"Pasta nao encontrada: {pasta}")
        return 1

    series: dict[str, pd.Series] = {}
    for path in sorted(pasta.iterdir()):
        if path.suffix.lower() in (".htm", ".html"):
            trades = ler_html(path)
        elif path.suffix.lower() == ".csv":
            trades = ler_csv(path)
        else:
            continue
        if trades is None or trades.empty:
            print(f"  ignorado (sem trades legiveis): {path.name}")
            continue
        series[path.stem] = serie_diaria(trades)

    if len(series) < 2:
        print(f"Preciso de pelo menos 2 relatorios legiveis; achei {len(series)}.")
        return 1

    print(f"Estrategias lidas: {len(series)}\n")
    print(f"{'Estrategia':<34}{'Resultado':>12}{'Drawdown':>11}"
          f"{'Recup.':>8}{'Sharpe':>8}{'Dias':>7}")
    print("-" * 80)
    for nome, serie in series.items():
        m = metricas(serie)
        print(f"{nome[:33]:<34}{m['resultado']:>12.2f}{m['drawdown']:>11.2f}"
              f"{m['recuperacao']:>8.2f}{m['sharpe']:>8.2f}"
              f"{m['dias_operados']:>7}")

    escolhidas, correl, recusadas = selecionar(
        series, args.max, args.teto_correlacao, args.recuperacao_minima)
    if recusadas:
        print("\nFora do portfolio por qualidade propria:")
        for motivo in recusadas:
            print(f"  {motivo}")
    if not escolhidas:
        print("\nNenhuma estrategia elegivel.")
        return 1
    pesos = alocar(series, escolhidas)

    print(f"\nPortfolio ({len(escolhidas)} de {len(series)}, "
          f"correlacao maxima aceita {args.teto_correlacao:g}):")
    for nome in escolhidas:
        piores = [(correl.loc[nome, o], o) for o in escolhidas if o != nome]
        pior = max(piores)[0] if piores else 0.0
        print(f"  {nome[:40]:<42} peso {pesos[nome]:>6.1%}  "
              f"correlacao maxima com o grupo {pior:>5.2f}")

    quadro = pd.DataFrame(series).fillna(0.0)
    combinado = sum(quadro[n] * pesos[n] for n in escolhidas)
    soma_simples = quadro[escolhidas].sum(axis=1)

    m_comb = metricas(combinado)
    print(f"\nPortfolio ponderado: resultado {m_comb['resultado']:.2f} | "
          f"drawdown {m_comb['drawdown']:.2f} | "
          f"recuperacao {m_comb['recuperacao']:.2f} | "
          f"Sharpe {m_comb['sharpe']:.2f}")

    # O ganho da diversificacao aparece aqui: se o DD do conjunto fosse a soma
    # dos DDs individuais, nao haveria diversificacao nenhuma.
    soma_dds = sum(drawdown_maximo(quadro[n]) for n in escolhidas)
    dd_conjunto = drawdown_maximo(soma_simples)
    if soma_dds < 0:
        poupado = (1 - dd_conjunto / soma_dds) * 100
        print(f"Drawdown somado dos individuais: {soma_dds:.2f} | "
              f"do conjunto: {dd_conjunto:.2f} "
              f"({poupado:.0f}% poupado pela diversificacao)")

    correl.to_csv(args.out, sep=";", encoding="utf-8-sig")
    print(f"\nMatriz de correlacao: {args.out}")

    if args.html:
        from portfolio_html import gerar as gerar_html
        gerar_html(Path(args.html), series, correl, escolhidas, pesos,
                   metricas, recusadas)
        print(f"Painel visual: {args.html}")

    altas = [(correl.loc[a, b], a, b)
             for i, a in enumerate(correl.columns)
             for b in correl.columns[i + 1:]
             if abs(correl.loc[a, b]) >= 0.7]
    if altas:
        print("\nPares que andam praticamente juntos (nao somam diversificacao):")
        for valor, a, b in sorted(altas, reverse=True)[:8]:
            print(f"  {valor:>5.2f}  {a[:30]} <-> {b[:30]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
