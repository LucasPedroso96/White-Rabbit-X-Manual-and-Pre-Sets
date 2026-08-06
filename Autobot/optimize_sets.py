# -*- coding: utf-8 -*-
"""Roda otimizacao GENETICA de um set e devolve os melhores passes.

O smoke test prova que o set carrega e opera. Isto e o passo seguinte: deixar o
algoritmo genetico do MT5 procurar os parametros.

Optimization=2 e o genetico rapido -- a unica opcao viavel nesta biblioteca,
onde o maior set tem 22 trilhoes de combinacoes (busca completa levaria
seculos). O criterio e Custom max (6), porque a EA devolve a formula propria
pelo OnTester: usar saldo ou profit factor ignoraria o selectedFormula que cada
sistema escolhe (o grid usa Grid Survival Score, os demais o Levain Composite).

ARMADILHAS que este script trata:

  - O relatorio XML do MT5 e um Spreadsheet 2003, nao XML comum: os dados ficam
    em Row/Cell/Data e o namespace muda por versao. A leitura ignora namespace.
  - O Report precisa ser um nome RELATIVO, e o arquivo sai na pasta de DADOS
    (AppData\\...\\Terminal\\<hash>\\), nao na de instalacao. Caminho absoluto e
    engolido calado: o MT5 aceita o .ini, roda a otimizacao inteira e nao
    escreve nada, sem erro no log. Custou 25 minutos de otimizacao boa (8.704
    passes) para descobrir, e mais uma rodada porque a primeira hipotese
    (pasta de instalacao) tambem estava errada -- o que resolveu foi testar a
    mesma chave num backtest simples, que leva 9 segundos.
  - Passe com OnTester 0 nao e ruim: e reprovado. Os filtros internos zeram o
    criterio de proposito, entao ordenar por criterio ja empurra o lixo pro fim.

Uso:
    python optimize_sets.py --symbol EURUSD --sistema 01_SLTP \\
        --variante SELL_MULTI --from 2024.01.01 --to 2026.07.21
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from mt5_runner import garantir_terminal_livre, lancar_terminal

TERMINAL = Path(r"C:\Program Files\RoboForex MT5 Terminal (WhiteRabbitEA)"
                r"\terminal64.exe")
DADOS = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
             r"\D2A36B4A61A508797F5C460B1F34DC5D")
SETS = DADOS / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"
CONTA_CACHE = Path(__file__).resolve().parent / "_conta_real.json"
EA = r"White Rabbit X (Global Multi-Indicator).ex5"
LOGS = DADOS / "Tester" / "logs"

CLASSES = ("01_Forex", "02_Metals", "03_Cryptocurrencies",
           "04_Indices_Energies", "05_US_Stocks_CFD")

# Criterios de otimizacao do MT5 (aba Settings).
CRITERIOS = {0: "Saldo max", 1: "Profit Factor max", 2: "Payoff esperado max",
             3: "Drawdown min", 4: "Recovery Factor max", 5: "Sharpe max",
             6: "Custom max (OnTester)", 7: "Complex Criterion max"}


def achar_set(symbol: str, sistema: str, variante: str) -> Path | None:
    """Localiza o set do ativo, aceitando simbolo custom ou com sufixo.

    A biblioteca e organizada pelo ativo puro (XAUUSD), mas o tester pode rodar
    num simbolo custom (XAUUSD.HT, com historico curado) ou no nome do broker
    com sufixo (XAUUSDm). O set e o mesmo -- ele nao amarra simbolo --, entao a
    busca tenta o nome inteiro e depois o radical antes do primeiro separador.
    """
    candidatos = [symbol]
    radical = re.split(r"[.\-_]", symbol)[0]
    if radical != symbol:
        candidatos.append(radical)
    for nome in candidatos:
        for classe in CLASSES:
            alvo = SETS / classe / nome / sistema / f"{variante}.set"
            if alvo.is_file():
                return alvo
    return None


def contar_flags(caminho: Path) -> int:
    """Quantos parametros estao marcados Y (o que o genetico vai mexer)."""
    txt = caminho.read_text(encoding="utf-16", errors="replace")
    return len(re.findall(r"\|\|Y\s*$", txt, re.M))


_leverage_cache: str | None = None


def leverage_conta() -> str:
    """Alavancagem REAL da conta, lida de `_conta_real.json`.

    Nunca um numero digitado: alavancagem errada no .ini muda o comportamento
    de MARGEM da simulacao (chamada de margem, stop-out), e isso e
    path-dependent -- pode divergir entre o passe OHLC e o tick real sem que
    nada mais tenha mudado. Falha alto se o cache nao existe em vez de supor
    um valor (mesma regra de `src/risk/margin_calculator.py`: sem dado real,
    sem numero fictício).
    """
    global _leverage_cache
    cache = _leverage_cache
    if cache is None:
        if not CONTA_CACHE.is_file():
            raise SystemExit(
                "Sem cache de conta real (_conta_real.json). Rode "
                "`python atualizar_conta_real.py` com o terminal fechado "
                "antes de otimizar.")
        cache = json.loads(CONTA_CACHE.read_text(encoding="utf-8"))["leverage"]
        _leverage_cache = cache
    return cache


def escrever_ini(destino: Path, symbol: str, periodo: str, set_rel: str,
                 inicio: str, fim: str, deposito: int, modelo: int,
                 criterio: int, relatorio: str, forward: int = 0) -> None:
    """Monta o .ini do tester. `forward` aciona o holdout NATIVO do MT5.

    ForwardMode: 0 desligado, 1 = metade do periodo, 2 = um terco, 3 = um
    quarto, 4 = data custom (exige ForwardDate).

    Vale preferir isto ao mecanismo interno da EA quando o objetivo e holdout:
    o tester corta o periodo sozinho, o genetico so enxerga a primeira parte, e
    os melhores passes sao reexecutados na segunda automaticamente. O caminho
    interno exige AtivarWFO ligado E o input_end_date batendo com a data do
    tester -- duas condicoes que, erradas, zeram todos os passes em silencio.
    O interno continua util pelo relatorio POR CICLO, que o Forward nao da.
    """
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini["Tester"] = {
        "Expert": EA,
        "Symbol": symbol,
        "Period": periodo,
        "Model": str(modelo),
        "FromDate": inicio,
        "ToDate": fim,
        "Deposit": str(deposito),
        "Currency": "USD",
        "Leverage": leverage_conta(),
        "Optimization": "2",            # genetico rapido
        "OptimizationCriterion": str(criterio),
        "ShutdownTerminal": "1",
        "Visual": "0",
        "ExpertParameters": set_rel,
        "Report": str(relatorio),
        "ReplaceReport": "1",
        "ForwardMode": str(forward),
    }
    with destino.open("w", encoding="utf-16") as fh:
        ini.write(fh, space_around_delimiters=False)


def marcar_logs() -> dict[Path, int]:
    if not LOGS.is_dir():
        return {}
    return {p: p.stat().st_size for p in LOGS.glob("*.log")}


def texto_novo(antes: dict[Path, int]) -> str:
    if not LOGS.is_dir():
        return ""
    partes = []
    for p in LOGS.glob("*.log"):
        ini = antes.get(p, 0)
        if p.stat().st_size <= ini:
            continue
        with p.open("rb") as fh:
            fh.seek(ini)
            bruto = fh.read()
        if ini % 2:
            bruto = bruto[1:]
        partes.append(bruto.decode("utf-16-le", errors="replace"))
    return "\n".join(partes)


def ler_relatorio(caminho: Path) -> tuple[list[str], list[list[str]]]:
    """Le o Spreadsheet 2003 do MT5. Devolve (cabecalho, linhas)."""
    if not caminho.exists():
        return [], []
    bruto = caminho.read_bytes()
    # Decodificar por tentativa e erro NAO serve aqui: UTF-8 lido como UTF-16
    # nunca levanta excecao (qualquer sequencia de bytes de tamanho par e
    # UTF-16 valido), so devolve caracteres CJK sem sentido. Um except
    # UnicodeDecodeError jamais dispara e o lixo passa adiante. O BOM decide.
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texto = bruto.decode("utf-16")
    else:
        try:
            texto = bruto.decode("utf-8")
        except UnicodeDecodeError:
            texto = bruto.decode("cp1252", errors="replace")
    # Sem DOCTYPE nao existe entidade para expandir, o que fecha XXE e
    # billion-laughs sem depender de defusedxml. O arquivo e gerado pelo MT5
    # nesta maquina, mas nao custa nada nao confiar nele.
    texto = re.sub(r"<!DOCTYPE.*?>", "", texto, flags=re.S)
    texto = re.sub(r"<!ENTITY.*?>", "", texto, flags=re.S)
    # O namespace do Spreadsheet muda entre versoes; remove antes de parsear.
    # Tirar so o xmlns e os prefixos de ELEMENTO nao basta: sobram prefixos em
    # ATRIBUTO (ss:ID, ss:Type, ss:Format) e o parser morre com "unbound
    # prefix" logo na primeira <Style ss:ID="ce0">.
    texto = re.sub(r'\sxmlns(:[\w.-]+)?="[^"]*"', "", texto)
    texto = re.sub(r"<(/?)[A-Za-z_][\w.-]*:", r"<\1", texto)
    texto = re.sub(r"(\s)[A-Za-z_][\w.-]*:([A-Za-z_][\w.-]*\s*=)", r"\1\2", texto)
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError:
        return [], []
    linhas = []
    for row in raiz.iter("Row"):
        celulas = []
        for cell in row.iter("Cell"):
            dado = cell.find("Data")
            celulas.append((dado.text or "").strip() if dado is not None else "")
        if any(celulas):
            linhas.append(celulas)
    if not linhas:
        return [], []
    return linhas[0], linhas[1:]


def num(txt: str) -> float:
    try:
        return float(txt.replace(",", "."))
    except (ValueError, AttributeError):
        return float("-inf")


def escolher_candidatos(cab: list[str], linhas: list[list[str]],
                        min_trades: int, min_pf: float) -> list[list[str]]:
    """Ordena os passes por criterios que NAO saturam.

    O criterio da EA (Levain Composite) e um score normalizado: os quatro
    componentes tem teto e os pesos somam 1, entao todo passe que atinge os
    benchmarks devolve exatamente 1.0. Como nota de qualidade esta certo; como
    criterio de ORDENACAO ele para de discriminar justamente onde o campeao e
    escolhido, e o genetico perde o gradiente no topo.

    Pior: quem maximiza os quatro componentes com facilidade e o passe PEQUENO.
    Um pass com 33 trades e nenhuma perda em 3 anos zera a perda bruta (PF no
    teto), infla o Sharpe muito acima do teto de 2 e passa raspando no piso de
    30 trades. Ele ganha por nao ter tido tempo de perder, nao por ser melhor.

    Aqui a selecao e explicita:
      - piso de trades bem acima do minimo da formula (amostra, nao sorte);
      - Profit Factor REAL: o MT5 reporta 0 quando a perda bruta e zero, o que
        parece otimo e significa "a cauda ainda nao apareceu";
      - ordenacao por lucro, que nao satura.
    """
    def col(nome: str) -> int | None:
        return cab.index(nome) if nome in cab else None

    i_pf, i_tr = col("Profit Factor"), col("Trades")
    i_lucro, i_dd = col("Profit"), col("Equity DD %")
    if i_lucro is None:
        return linhas

    aptos = []
    for linha in linhas:
        if num(linha[i_lucro]) <= 0:
            continue
        if i_tr is not None and num(linha[i_tr]) < min_trades:
            continue
        if i_pf is not None and num(linha[i_pf]) < min_pf:
            continue          # inclui PF=0, que e ausencia de perda, nao virtude
        aptos.append(linha)

    # Lucro como chave, drawdown como desempate: entre dois lucros parecidos, o
    # que sofreu menos para chegar la e o mais provavel de sobreviver.
    aptos.sort(key=lambda r: (num(r[i_lucro]),
                              -num(r[i_dd]) if i_dd is not None else 0),
               reverse=True)
    return aptos


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--sistema", default="01_SLTP")
    ap.add_argument("--variante", default="SELL_MULTI")
    # M1 e OBRIGATORIO (dono, 2026-07-31): cada indicador carrega o proprio TF
    # via input (MTF_TF1/TF2, ATR_TimeFrame etc.) -- period != M1 faz qualquer
    # input "Current TF" colapsar pro period do chart em vez do TF pretendido.
    ap.add_argument("--period", default="M1")
    ap.add_argument("--from", dest="inicio", default="2024.01.01")
    ap.add_argument("--to", dest="fim", default=datetime.now().strftime("%Y.%m.%d"))
    ap.add_argument("--deposit", type=int, default=10000)
    ap.add_argument("--model", type=int, default=1,
                    help="1 = OHLC M1 (rapido). 4 = ticks reais (fiel a "
                         "SL/TP/trailing intrabar, muito mais lento)")
    ap.add_argument("--criterion", type=int, default=6,
                    help="6 = Custom max, que respeita o selectedFormula do set")
    ap.add_argument("--top", type=int, default=12, help="melhores passes a exibir")
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--min-trades", type=int, default=100,
                    help="piso de trades do candidato (a formula da EA usa 30, "
                         "que em 3 anos e ~10/ano e nao sustenta conclusao)")
    ap.add_argument("--min-pf", type=float, default=1.2,
                    help="Profit Factor minimo REAL; descarta PF=0, que no MT5 "
                         "significa perda bruta zero, nao excelencia")
    ap.add_argument("--fechar-terminal", action="store_true",
                    help="fecha um MetaTrader aberto em vez de abortar")
    args = ap.parse_args()

    # Terminal aberto faz o /config virar no-op silencioso.
    garantir_terminal_livre(fechar=args.fechar_terminal)

    if not TERMINAL.exists():
        print(f"Terminal nao encontrado: {TERMINAL}")
        return 1
    caminho = achar_set(args.symbol, args.sistema, args.variante)
    if caminho is None:
        print(f"Set nao encontrado: {args.symbol}/{args.sistema}/{args.variante}")
        return 1

    rel = str(caminho.relative_to(DADOS / "MQL5" / "Profiles" / "Tester")).replace("/", "\\")
    # Nome RELATIVO, resolvido contra a pasta de DADOS (nao a de instalacao,
    # como parecia). Caminho absoluto e engolido calado: o MT5 aceita o .ini,
    # roda a otimizacao inteira e nao escreve nada.
    # A extensao tambem nao manda: em backtest simples o MT5 grava .htm mesmo
    # quando o nome pede .xml. Em otimizacao ele grava a tabela de passes em
    # .xml. Por isso a leitura procura os dois.
    nome_relatorio = "otim_wrx"
    flags = contar_flags(caminho)

    print(f"{args.symbol} {args.period} | {args.sistema} / {args.variante}")
    print(f"{args.inicio} a {args.fim} | modelo {args.model} | "
          f"deposito {args.deposit}")
    print(f"genetico rapido | criterio {args.criterion} "
          f"({CRITERIOS.get(args.criterion, '?')})")
    print(f"parametros marcados Y: {flags}\n")

    antes = marcar_logs()
    # Limpa restos de corridas anteriores para nao ler resultado velho como se
    # fosse desta. O MT5 gera .xml/.htm e ainda PNGs dos graficos.
    for velho in DADOS.glob(f"{nome_relatorio}*"):
        velho.unlink(missing_ok=True)
    inicio_em = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "otim.ini"
        escrever_ini(ini, args.symbol, args.period, rel, args.inicio, args.fim,
                     args.deposit, args.model, args.criterion, nome_relatorio)
        try:
            lancar_terminal(TERMINAL, ini, args.timeout)
        except subprocess.TimeoutExpired:
            print(f"Estourou {args.timeout}s. O genetico pode precisar de mais "
                  "tempo, ou o periodo/modelo esta caro demais.")
            return 1
    decorrido = time.monotonic() - inicio_em

    log = texto_novo(antes)
    # "finished on pass N (of TOTAL)" e o indice que o genetico alcancou;
    # "local N tasks" e quanto foi realmente executado. Os dois interessam: o
    # primeiro diz ate onde a busca chegou, o segundo o custo.
    m = re.search(r"genetic optimization finished on pass (\d+) \(of (\d+)\)", log)
    alcance, espaco = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    m = re.search(r"local (\d+) tasks", log)
    executados = int(m.group(1)) if m else 0
    print(f"tempo: {decorrido/60:.1f} min | passes executados: {executados}"
          + (f" | genetico parou no indice {alcance:,} de {espaco:,}"
             .replace(",", ".") if alcance else ""))

    # O .xml e a tabela de passes da otimizacao; o .htm e o relatorio de um
    # backtest so. Preferir o xml quando os dois existirem.
    candidatos = sorted(DADOS.glob(f"{nome_relatorio}*"),
                        key=lambda p: (p.suffix.lower() != ".xml", p.name))
    relatorio = candidatos[0] if candidatos else DADOS / f"{nome_relatorio}.xml"

    cab, linhas = ler_relatorio(relatorio)
    if not linhas:
        print("\nO tester nao gerou relatorio legivel.")
        erro = [linha for linha in log.splitlines()
                if re.search(r"error|cannot|failed|no history", linha, re.I)]
        if erro:
            print("Do log:")
            for linha in erro[:6]:
                print("   ", re.sub(r"^.*?\t", "", linha).strip()[:120])
        elif executados > 0:
            # Distincao que importa: a otimizacao ACONTECEU. Concluir aqui que
            # "nenhuma combinacao sobreviveu" seria inventar um resultado a
            # partir de uma falha de escrita.
            print(f"Mas {executados} passes RODARAM. Entao isto nao e um")
            print("resultado sobre a estrategia -- e o relatorio que nao saiu")
            print("ou nao foi lido. Procure por otim_wrx* em:")
            print(f"  {DADOS}")
            print("Os passes tambem ficam em Tester/cache/*.opt, que prova que")
            print("a otimizacao aconteceu mesmo sem relatorio.")
        else:
            print("Nenhum passe rodou. Verifique simbolo, periodo e historico.")
        return 1

    # A ordenacao por "Result" (criterio da EA) saiu daqui: ela satura e para
    # de discriminar no topo. Quem escolhe agora e escolher_candidatos().
    uteis = escolher_candidatos(cab, linhas, args.min_trades, args.min_pf)
    print(f"passes no relatorio: {len(linhas)} | com criterio > 0: {len(uteis)}")
    if len(linhas) > executados * 1.2 and executados:
        # O MT5 guarda um cache por (simbolo, periodo, datas, set) e o
        # relatorio traz o cache INTEIRO, nao so a corrida de agora. Repetir a
        # mesma configuracao acumula. Nao e erro, mas sem dizer isso o numero
        # parece nao bater com os passes executados.
        print(f"  ({len(linhas) - executados} vem do cache de corridas "
              "anteriores com a mesma configuracao)")
    if not uteis:
        print("\nTodos os passes foram zerados pelos filtros internos da EA.")
        print("Nenhuma combinacao deste set sobreviveu no periodo pedido.")
        return 0

    # "Custom" fica de fora: e o mesmo numero de "Result", so que sem
    # arredondar -- e com 17 casas ele estourava a coluna e colava na vizinha.
    mostrar = [c for c in ("Result", "Profit", "Profit Factor",
                           "Expected Payoff", "Recovery Factor",
                           "Sharpe Ratio", "Equity DD %", "Trades")
               if c in cab]
    idx = [cab.index(c) for c in mostrar]
    rotulos = {"Profit Factor": "PF", "Expected Payoff": "Payoff",
               "Recovery Factor": "Recovery", "Sharpe Ratio": "Sharpe",
               "Equity DD %": "DD %"}

    def curto(txt: str) -> str:
        """Numero legivel: 3 casas bastam para comparar passes."""
        try:
            v = float(txt)
        except (TypeError, ValueError):
            return txt
        return f"{v:.0f}" if v == int(v) and abs(v) < 1e6 else f"{v:.3f}"

    corpo = [[curto(linha[i]) if i < len(linha) else "-" for i in idx]
             for linha in uteis[:args.top]]
    cab_txt = [rotulos.get(c, c) for c in mostrar]
    # Largura vinda do conteudo, nao chutada.
    larg = [max(len(cab_txt[j]), *(len(linha[j]) for linha in corpo)) + 2
            for j in range(len(cab_txt))] if corpo else []

    print("\n" + "".join(f"{c:>{w}}" for c, w in zip(cab_txt, larg)))
    print("-" * sum(larg))
    for linha in corpo:
        print("".join(f"{v:>{w}}" for v, w in zip(linha, larg)))

    print(f"\nRelatorio completo: {relatorio}")
    print("Leia como candidato, nao como resultado: o topo de uma otimizacao e")
    print("o passe mais bem ajustado AO PASSADO. Valide fora da amostra antes")
    print("de confiar -- wfo_matrix.py mede se a janela sustenta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
