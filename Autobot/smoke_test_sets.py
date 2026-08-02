# -*- coding: utf-8 -*-
"""Prova que os sets carregam E OPERAM de verdade no Strategy Tester.

O validate_system_sets confere o schema e reimplementa as regras do OnInit em
Python -- util, mas e uma simulacao das regras, nao o EA rodando. Este script
fecha a lacuna: pega uma amostra de sets, roda cada um num backtest curto e le
o log procurando o que so aparece na execucao real.

O que cada coluna responde:

  Init      o OnInit aceitou os parametros? Recusa aparece como
            "incorrect input parameters" e nada mais acontece.
  Handles   os indicadores foram criados? Handle invalido derruba a EA
            silenciosamente na primeira barra.
  Trades    quantos negocios fecharam.
  Abort     ordens recusadas antes de ir ao mercado. Esta coluna existe
            porque um set pode iniciar bem, criar todos os indicadores e
            ainda assim nunca operar -- foi assim que apareceu o
            11_SIGNAL_ONLY, com 111 abortos e saldo intacto.
  Saldo     saldo final. Igual ao deposito = nao operou.

ARMADILHA DO LOG: o MT5 ANEXA todas as corridas no mesmo arquivo do dia. Ler o
arquivo inteiro faz cada corrida herdar as contagens das anteriores -- os
numeros sobem em escada e parecem plausiveis. Por isso guardamos o tamanho do
log antes de rodar e so interpretamos os bytes novos.
"""
from __future__ import annotations

import argparse
import configparser
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from mt5_runner import garantir_terminal_livre

TERMINAL = Path(r"C:\Users\Lucas Pedroso\Desktop\Levain 2.0 (Em Andamento)"
                r"\Levain-2.0\MetaTrader5\terminal64.exe")
DADOS = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
             r"\59EECBFD4A9CCD98CCBC61E96D5DED8E")
SETS = DADOS / "MQL5" / "Profiles" / "Tester" / "White_Rabbit_X_Sets_templates"
EA = r"White Rabbit X (Global Multi-Indicator).ex5"
LOGS = DADOS / "Tester" / "logs"

CLASSES = ("01_Forex", "02_Metals", "03_Cryptocurrencies",
           "04_Indices_Energies", "05_US_Stocks_CFD")


def pasta_do_ativo(symbol: str) -> Path | None:
    """Pasta dos sets do ativo, aceitando simbolo custom ou com sufixo.

    A biblioteca usa o ativo puro (XAUUSD), mas o tester pode rodar num simbolo
    custom (XAUUSD.HT, historico curado) ou no nome do broker com sufixo
    (XAUUSDm). O set nao amarra simbolo, entao vale o radical.
    """
    candidatos = [symbol]
    radical = re.split(r"[.\-_]", symbol)[0]
    if radical != symbol:
        candidatos.append(radical)
    for nome in candidatos:
        for classe in CLASSES:
            alvo = SETS / classe / nome
            if alvo.is_dir():
                return alvo
    return None


def escrever_ini(destino: Path, symbol: str, periodo: str, set_rel: str,
                 inicio: str, fim: str, deposito: int, modelo: int) -> None:
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
        "Leverage": "1:100",
        "Optimization": "0",
        "ShutdownTerminal": "1",
        "Visual": "0",
        "ExpertParameters": set_rel,
    }
    with destino.open("w", encoding="utf-16") as fh:
        ini.write(fh, space_around_delimiters=False)


def marcar_logs() -> dict[Path, int]:
    """Tamanho atual de cada log, para depois ler so o que for novo."""
    if not LOGS.is_dir():
        return {}
    return {p: p.stat().st_size for p in LOGS.glob("*.log")}


def texto_novo(antes: dict[Path, int]) -> str:
    """Devolve apenas os bytes escritos depois de marcar_logs()."""
    if not LOGS.is_dir():
        return ""
    pedacos = []
    for p in LOGS.glob("*.log"):
        inicio = antes.get(p, 0)
        tamanho = p.stat().st_size
        if tamanho <= inicio:
            continue
        with p.open("rb") as fh:
            fh.seek(inicio)
            bruto = fh.read()
        # Log do tester e UTF-16LE. Comecando no meio do arquivo nao ha BOM, e
        # um offset impar dessincronizaria os pares de bytes.
        if inicio % 2:
            bruto = bruto[1:]
        pedacos.append(bruto.decode("utf-16-le", errors="replace"))
    return "\n".join(pedacos)


def esperar_corrida(antes: dict[Path, int], limite: float = 30.0) -> str:
    """Espera o log da corrida ficar completo antes de interpretar.

    terminal64.exe devolve o controle antes de terminar de escrever o log, e o
    que faltou aparece durante a corrida SEGUINTE -- o que faz uma corrida
    parecer muda e a proxima herdar os trades das duas. "automatic testing
    finished" e a ultima linha que o tester escreve, entao ela e o sinal de
    que o texto esta inteiro.
    """
    limite_em = time.monotonic() + limite
    texto = ""
    while time.monotonic() < limite_em:
        texto = texto_novo(antes)
        if "automatic testing finished" in texto:
            return texto
        time.sleep(0.3)
    return texto


def interpretar(texto: str) -> dict:
    r = {"init_ok": True, "handles_ok": True, "motivo": "",
         "trades": 0, "abortos": 0, "saldo": None}
    if not texto.strip():
        r["motivo"] = "o tester nao escreveu nada no log"
        r["init_ok"] = False
        return r
    if "incorrect input parameters" in texto.lower():
        r["init_ok"] = False
    if "Failed to create" in texto or "invalid handle" in texto.lower():
        r["handles_ok"] = False
    for linha in texto.splitlines():
        if re.search(r"Invalid|requires?|cannot|must be|aborted", linha):
            r["motivo"] = re.sub(r"^.*?\t", "", linha).strip()[:110]
            break
    r["trades"] = len(re.findall(r"\bdeal #\d+", texto))
    r["abortos"] = len(re.findall(r"aborted", texto))
    m = re.findall(r"final balance ([\d.]+)", texto)
    if m:
        r["saldo"] = float(m[-1])
    return r


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--period", default="H1")
    ap.add_argument("--from", dest="inicio", default="2025.01.01")
    ap.add_argument("--to", dest="fim", default="2025.04.01")
    ap.add_argument("--deposit", type=int, default=10000)
    ap.add_argument("--model", type=int, default=1,
                    help="1 = OHLC M1 (rapido; suficiente para fumaca)")
    ap.add_argument("--amostra", type=int, default=1,
                    help="sets sorteados por sistema")
    ap.add_argument("--sistemas", default="", help="filtra, separado por virgula")
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--fechar-terminal", action="store_true",
                    help="fecha um MetaTrader aberto em vez de abortar")
    args = ap.parse_args()

    # Terminal aberto faz o /config virar no-op silencioso.
    garantir_terminal_livre(fechar=args.fechar_terminal)

    if not TERMINAL.exists():
        print(f"Terminal nao encontrado: {TERMINAL}")
        return 1
    pasta = pasta_do_ativo(args.symbol)
    if pasta is None:
        print(f"Sem sets instalados para {args.symbol} em {SETS}")
        return 1

    filtro = [s.strip() for s in args.sistemas.split(",") if s.strip()]
    alvos: list[Path] = []
    for sistema in sorted(pasta.iterdir()):
        if not sistema.is_dir() or (filtro and sistema.name not in filtro):
            continue
        arquivos = sorted(sistema.glob("*.set"))
        random.seed(7)   # amostra reproduzivel entre execucoes
        alvos.extend(random.sample(arquivos, min(args.amostra, len(arquivos))))

    print(f"{args.symbol} {args.period} | {args.inicio} a {args.fim} | "
          f"modelo {args.model} | deposito {args.deposit}")
    print(f"{len(alvos)} sets na amostra\n")
    cab = (f"{'Sistema / arquivo':<40}{'Init':>6}{'Hnd':>5}"
           f"{'Trades':>8}{'Abort':>7}{'Saldo':>11}")
    print(cab)
    print("-" * len(cab))

    falhas, mudos = [], []
    for caminho in alvos:
        rel = caminho.relative_to(DADOS / "MQL5" / "Profiles" / "Tester")
        rotulo = f"{caminho.parent.name}/{caminho.name}"
        antes = marcar_logs()
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / "smoke.ini"
            escrever_ini(ini, args.symbol, args.period,
                         str(rel).replace("/", "\\"),
                         args.inicio, args.fim, args.deposit, args.model)
            try:
                subprocess.run([str(TERMINAL), f"/config:{ini}"],
                               timeout=args.timeout, capture_output=True,
                               check=False)
            except subprocess.TimeoutExpired:
                print(f"{rotulo[:39]:<40}{'timeout':>6}")
                falhas.append((rotulo, "estourou o tempo"))
                continue
        r = interpretar(esperar_corrida(antes))

        saldo = f"{r['saldo']:.2f}" if r["saldo"] is not None else "-"
        print(f"{rotulo[:39]:<40}"
              f"{'ok' if r['init_ok'] else 'NAO':>6}"
              f"{'ok' if r['handles_ok'] else 'NAO':>5}"
              f"{r['trades']:>8}{r['abortos']:>7}{saldo:>11}")

        if not r["init_ok"] or not r["handles_ok"]:
            falhas.append((rotulo, r["motivo"] or "sem detalhe no log"))
        elif r["trades"] == 0:
            mudos.append((rotulo, r["abortos"], r["motivo"]))

    print()
    if falhas:
        print(f"FALHAS DE CARGA ({len(falhas)}):")
        for rotulo, motivo in falhas:
            print(f"  {rotulo}\n      {motivo}")
    else:
        print("Todos os sets iniciaram e criaram os indicadores.")

    if mudos:
        print(f"\nINICIARAM MAS NAO OPERARAM ({len(mudos)}):")
        for rotulo, abortos, motivo in mudos:
            print(f"  {rotulo}  ({abortos} ordens abortadas)")
            if motivo:
                print(f"      {motivo}")
        print("\n  Zero trades COM abortos e defeito: a EA quis operar e foi")
        print("  barrada. Zero trades SEM abortos costuma ser so o periodo")
        print("  curto ou filtro fechado nos valores de partida do set.")
    return 1 if falhas or any(a for _, a, _ in mudos) else 0


if __name__ == "__main__":
    sys.exit(main())
