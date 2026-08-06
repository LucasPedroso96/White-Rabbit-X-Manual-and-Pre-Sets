# -*- coding: utf-8 -*-
"""Varre uma grade de janelas IS x OOS e monta o mapa de robustez.

Escolher IS=122 e OOS=61 e um chute. Esta ferramenta responde qual proporcao
sustenta o desempenho fora da amostra -- e, mais importante, se ela sustenta
tambem na VIZINHANCA.

O metodo veio do WFA do Thiago Oliveira (OlimBot), com uso autorizado, mas com
uma diferenca que importa: o Olimbot roda um backtest unico e depois recorta os
trades por data para montar os ciclos, o que trata os ciclos como
independentes. Eles nao sao -- saldo, ciclo de martingale e cesta de grid
atravessam a fronteira das janelas. Aqui cada celula da grade e um backtest
proprio, com o WFO interno da EA encadeando os ciclos de verdade.

O custo e maior. Em troca, o numero e confiavel.

Como ler o resultado: nao procure a celula de maior WFE. Procure a REGIAO onde
o WFE se mantem. Pico isolado que despenca na celula ao lado e ajuste a janela;
planalto e robustez.

Uso:
    python wfo_matrix.py --symbol EURUSD --set caminho.set \\
        --from 2023.01.01 --to 2026.07.21 \\
        --is 90,120,150,180 --oos 30,45,60,90
"""
from __future__ import annotations

import argparse
import configparser
import csv
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

TERMINAL_DIR = Path(r"C:\Users\Lucas Pedroso\Desktop\Levain 2.0 (Em Andamento)"
                    r"\Levain-2.0\MetaTrader5")
TERMINAL_EXE = TERMINAL_DIR / "terminal64.exe"
DATA_DIR = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
                r"\D2A36B4A61A508797F5C460B1F34DC5D")
EA_REL = r"White Rabbit X (Global Multi-Indicator).ex5"


def escrever_set(origem: Path, destino: Path, is_dias: int, oos_dias: int,
                 data_final: str) -> None:
    """Copia o .set ligando o WFO em modo validacao com as janelas pedidas."""
    # As janelas do EA sao sequenciais (disjuntas). Ja tentamos deslizar o IS
    # para render mais ciclos; nao da: num unico passe do tester, janelas que
    # se sobrepoem fazem a mesma barra contar como IS e OOS ao mesmo tempo, e a
    # WFE sai inflada. Menos ciclos e a leitura honesta.
    mudancas = {
        "AtivarWFO": "true",
        "MetodoDeEntradawfo": "1",        # IS + OOS: e o modo que reporta WFE
        "input_end_date": data_final,
        "wfo_windowSize": "-1",
        "wfo_customWindowSizeDays": str(is_dias),
        "wfo_stepSize": "-1",
        "wfo_customStepSizePercent": str(-abs(oos_dias)),
    }
    saida = []
    for linha in origem.read_text(encoding="utf-16").splitlines():
        m = re.match(r"^([^;=]+)=(.*)$", linha)
        if m and m.group(1) in mudancas:
            nome, valor = m.group(1), mudancas[m.group(1)]
            partes = m.group(2).split("||")
            if len(partes) == 5:
                passo = "0" if valor in ("true", "false") else "1"
                saida.append(f"{nome}={valor}||{valor}||{passo}||{valor}||N")
            else:
                saida.append(f"{nome}={valor}")
        else:
            saida.append(linha)
    destino.write_text("\r\n".join(saida) + "\r\n", encoding="utf-16")


def escrever_ini(caminho: Path, symbol: str, period: str, set_name: str,
                 inicio: str, fim: str, deposito: float, modelo: int) -> None:
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini["Tester"] = {
        "Expert": EA_REL,
        "Symbol": symbol,
        "Period": period,
        "Model": str(modelo),
        "FromDate": inicio.replace(".", "."),
        "ToDate": fim.replace(".", "."),
        "Deposit": str(int(deposito)),
        "Currency": "USD",
        "Leverage": "1:100",
        "Optimization": "0",          # backtest simples, nao otimizacao
        "ShutdownTerminal": "1",
        "ExpertParameters": set_name,
        "Visual": "0",
    }
    with caminho.open("w", encoding="utf-16") as fh:
        ini.write(fh, space_around_delimiters=False)


def ler_wfe(log: Path) -> dict:
    """Extrai o WFE e a dispersao do log do tester."""
    if not log.exists():
        return {}
    texto = log.read_text(encoding="utf-16", errors="replace")
    saida: dict = {}
    m = re.search(r"Walk Forward Efficiency \(WFE\):\s*([-\d.]+)%", texto)
    if m:
        saida["wfe"] = float(m.group(1))
    m = re.search(r"WFE per cycle: mean ([-\d.]+)% \| stdev ([-\d.]+)% \| "
                  r"(\d+) of (\d+) cycles", texto)
    if m:
        saida.update({
            "wfe_medio": float(m.group(1)),
            "wfe_desvio": float(m.group(2)),
            "ciclos_positivos": int(m.group(3)),
            "ciclos": int(m.group(4)),
        })
    m = re.search(r"Total accumulated profit:\s*([-\d.]+)", texto)
    if m:
        saida["lucro"] = float(m.group(1))
    return saida


def rodar(symbol: str, period: str, set_path: Path, inicio: str, fim: str,
          is_dias: int, oos_dias: int, deposito: float, modelo: int,
          timeout: int) -> dict:
    tester_dir = DATA_DIR / "MQL5" / "Profiles" / "Tester"
    nome_set = f"_wfo_matrix_{is_dias}_{oos_dias}.set"
    escrever_set(set_path, tester_dir / nome_set, is_dias, oos_dias, fim)

    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "matrix.ini"
        log = Path(tmp) / "tester.log"
        escrever_ini(ini, symbol, period, nome_set, inicio, fim, deposito, modelo)
        try:
            lancar_terminal(TERMINAL_EXE, ini, timeout, f"/report:{log}")
        except subprocess.TimeoutExpired:
            return {"erro": "timeout"}

        # O terminal grava o log do tester na pasta de logs, nao no report.
        logs = sorted((DATA_DIR / "Tester" / "logs").glob("*.log"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        return ler_wfe(logs[0]) if logs else {"erro": "log nao encontrado"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--period", default="H1")
    ap.add_argument("--set", dest="set_path", required=True,
                    help="set base; as janelas sao sobrescritas")
    ap.add_argument("--from", dest="inicio", required=True, help="AAAA.MM.DD")
    ap.add_argument("--to", dest="fim", required=True, help="AAAA.MM.DD")
    ap.add_argument("--is", dest="is_list", default="90,120,150,180",
                    help="dias de In-Sample, separados por virgula")
    ap.add_argument("--oos", dest="oos_list", default="30,45,60,90",
                    help="dias de Out-of-Sample, separados por virgula")
    ap.add_argument("--deposit", type=float, default=10000.0)
    # Modelagem: 4 usa os ticks reais gravados pelo broker. O White Rabbit
    # decide SL, TP e trailing DENTRO da barra, entao OHLC M1 (modo 1)
    # inventa o caminho do preco entre abertura e fechamento -- e o resultado
    # de um trailing testado assim nao vale. Precisao acima de velocidade.
    ap.add_argument("--model", type=int, default=4,
                    help="4 ticks reais (padrao), 0 every tick, 1 OHLC M1, "
                         "2 so aberturas. Use 1 apenas para triagem grosseira")
    ap.add_argument("--timeout", type=int, default=1800,
                    help="segundos por celula")
    ap.add_argument("--out", default="wfo_matrix.csv")
    args = ap.parse_args()

    if not TERMINAL_EXE.exists():
        print(f"Terminal nao encontrado: {TERMINAL_EXE}")
        return 1
    set_path = Path(args.set_path)
    if not set_path.exists():
        print(f"Set nao encontrado: {set_path}")
        return 1

    is_dias = [int(x) for x in args.is_list.split(",")]
    oos_dias = [int(x) for x in args.oos_list.split(",")]
    total = len(is_dias) * len(oos_dias)
    print(f"{args.symbol} {args.period} | {args.inicio} a {args.fim}")
    print(f"Grade: {len(is_dias)} IS x {len(oos_dias)} OOS = {total} backtests")
    print("Cada celula roda o WFO encadeado da EA, nao um recorte por data.\n")

    inicio_dt = datetime.strptime(args.inicio, "%Y.%m.%d")
    fim_dt = datetime.strptime(args.fim, "%Y.%m.%d")
    dias_totais = (fim_dt - inicio_dt).days

    resultados = []
    feito = 0
    for i in is_dias:
        for o in oos_dias:
            feito += 1
            if i + o > dias_totais:
                print(f"[{feito}/{total}] IS {i} OOS {o}: pulado "
                      f"(IS+OOS excede os {dias_totais} dias do periodo)")
                continue
            print(f"[{feito}/{total}] IS {i} OOS {o}...", end=" ", flush=True)
            r = rodar(args.symbol, args.period, set_path, args.inicio,
                      args.fim, i, o, args.deposit, args.model, args.timeout)
            if "erro" in r:
                print(r["erro"])
            elif "wfe_medio" in r:
                print(f"WFE {r['wfe_medio']:.1f}% "
                      f"(desvio {r['wfe_desvio']:.1f}, "
                      f"{r['ciclos_positivos']}/{r['ciclos']} ciclos +)")
            elif "wfe" in r:
                print(f"WFE {r['wfe']:.1f}% (agregado)")
            else:
                print("sem WFE no log")
            resultados.append({"is_dias": i, "oos_dias": o, **r})

    if not resultados:
        print("\nNenhum resultado.")
        return 1

    campos = sorted({k for r in resultados for k in r})
    with Path(args.out).open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(resultados)

    # Mapa: linha = IS, coluna = OOS.
    print(f"\nMapa de WFE medio (linha IS, coluna OOS)")
    print("       " + "".join(f"{o:>9}" for o in oos_dias))
    for i in is_dias:
        linha = f"{i:>5}  "
        for o in oos_dias:
            achado = next((r for r in resultados
                           if r["is_dias"] == i and r["oos_dias"] == o), None)
            valor = achado.get("wfe_medio", achado.get("wfe")) if achado else None
            linha += f"{valor:>8.1f}%" if valor is not None else f"{'-':>9}"
        print(linha)

    validos = [r for r in resultados if "wfe_medio" in r]
    if validos:
        print("\nMais estaveis (WFE alto com desvio baixo):")
        # Desvio alto derruba a nota: um WFE que oscila muito nao e robusto.
        ordenado = sorted(validos,
                          key=lambda r: r["wfe_medio"] - r["wfe_desvio"],
                          reverse=True)
        for r in ordenado[:5]:
            print(f"  IS {r['is_dias']:>4} / OOS {r['oos_dias']:>3}: "
                  f"WFE {r['wfe_medio']:.1f}% +- {r['wfe_desvio']:.1f} | "
                  f"{r['ciclos_positivos']}/{r['ciclos']} ciclos positivos")
        print("\nOlhe a vizinhanca no mapa antes de escolher: valor alto "
              "cercado de valores baixos e ajuste a janela, nao robustez.")
    print(f"\nCSV: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
