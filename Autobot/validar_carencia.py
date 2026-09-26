# -*- coding: utf-8 -*-
"""Valida as duas mudancas da EA de 2026-09-26 contra o log bruto do MT5.

  1. Carencia no fim do IS (grid, modo 'In Sample'): nos passes geneticos de
     grid (logs dos AGENTES), quantos pegam dias emprestados do OOS e que
     fracao do OOS isso ocupa -- ANTES x DEPOIS da EA nova. Linha de base
     medida no mesmo dia: 75% dos passes, 21% do OOS em media.
  2. Retencao pela janela de ABERTURA: nos passes IS+OOS (log principal), a
     oficial x a do metodo antigo (janela de SAIDA), que a EA imprime ao lado.

    python validar_carencia.py [--desde HH:MM] [--dia AAAAMMDD]

`--desde` separa antes/depois (padrao 08:59, a implantacao da EA nova).
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

MEIO = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes")
INSTALACOES = {"ORIGINAL": "D2A36B4A61A508797F5C460B1F34DC5D",
               "CLONE": "4A85BF7BB91E709E95066E8432253C88"}
_OOS = re.compile(r"Out-Sample \(OOS\): (\d{4}\.\d{2}\.\d{2}) - (\d{4}\.\d{2}\.\d{2})")
_DIVIDA = re.compile(r"Divida de dias emprestados \(WFO\): (\d+) cesta\(s\) "
                     r"flexionaram apos o IS, (\d+) dia")
_CARENCIA = re.compile(r"Carencia de fim de IS \(grid\): ([\d.]+) dia\(s\) = p(\d+) "
                       r"de (\d+) cesta\(s\) fechada\(s\); (\d+) barra")
_RET = re.compile(r"Out-of-Sample Retention: (-?[\d.]+)%")
_RET_ANTIGA = re.compile(r"Retention \(metodo antigo, lucro na janela de SAIDA\): (-?[\d.]+)%")


def _dias(a: str, b: str) -> int:
    return (datetime.strptime(b, "%Y.%m.%d") - datetime.strptime(a, "%Y.%m.%d")).days


def _linhas(caminho: Path):
    with caminho.open("rb") as fh:
        for bruta in fh.read().decode("utf-16-le", errors="replace").split("\n"):
            yield bruta.rstrip("\r")


def passes_grid_so_is(log: Path) -> list[dict]:
    """Um dict por passe genetico de grid em modo 'In Sample' (marcador da EA
    'Running with Out-of-Sample data' -- o texto enganoso e o do modo IS)."""
    saida, atual = [], None
    for linha in _linhas(log):
        campos = linha.split("\t")
        msg, hora = campos[-1], (campos[2] if len(campos) >= 4 else "")
        if "Out-Sample (OOS) days:" in msg:
            atual = {"hora": hora, "oos_dias": 0, "divida": None, "carencia": None}
            continue
        if atual is None:
            continue
        m = _OOS.search(msg)
        if m:
            atual["oos_dias"] += _dias(m.group(1), m.group(2))
            continue
        m = _CARENCIA.search(msg)
        if m:
            atual["carencia"] = (float(m.group(1)), int(m.group(3)), int(m.group(4)))
            continue
        m = _DIVIDA.search(msg)
        if m:
            atual["divida"] = (int(m.group(1)), int(m.group(2)))
            if atual["oos_dias"]:
                saida.append(atual)
            atual = None
    return saida


def resumo_divida(passes: list[dict]) -> str:
    if not passes:
        return "sem passes de grid"
    com = [p for p in passes if p["divida"][0] > 0]
    fr = [p["divida"][1] / p["oos_dias"] for p in com]
    txt = (f"{len(passes)} passes | pegaram dias do OOS: {len(com)} "
           f"({100 * len(com) / len(passes):.0f}%)")
    if fr:
        txt += (f" | fracao do OOS nesses: media {100 * sum(fr) / len(fr):.1f}% "
                f"max {100 * max(fr):.1f}%")
    car = [p["carencia"] for p in passes if p["carencia"]]
    if car:
        ativas = [c for c in car if c[0] > 0]
        txt += (f" | carencia ativa em {len(ativas)} de {len(car)}"
                + (f", media {sum(c[0] for c in ativas) / len(ativas):.1f} dias"
                   if ativas else ""))
    return txt


def pares_retencao(log: Path, desde: str) -> list[tuple[float, float]]:
    pares, oficial = [], None
    for linha in _linhas(log):
        campos = linha.split("\t")
        msg, hora = campos[-1], (campos[2] if len(campos) >= 4 else "")
        if hora < desde:
            continue
        m = _RET.search(msg)
        if m:
            oficial = float(m.group(1))
            continue
        m = _RET_ANTIGA.search(msg)
        if m and oficial is not None:
            pares.append((oficial, float(m.group(1))))
            oficial = None
    return pares


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default="08:59")
    ap.add_argument("--dia", default=datetime.now().strftime("%Y%m%d"))
    args = ap.parse_args()
    antes, depois = [], []
    for nome, h in INSTALACOES.items():
        for agente in sorted((MEIO / "Tester" / h).glob("Agent-*")):
            log = agente / "logs" / f"{args.dia}.log"
            if not log.exists():
                continue
            for p in passes_grid_so_is(log):
                (depois if p["hora"] >= args.desde else antes).append(p)
    print("CARENCIA / DIVIDA (passes geneticos de grid, modo In Sample)")
    print("  antes :", resumo_divida(antes))
    print("  depois:", resumo_divida(depois))
    print("\nRETENCAO por ABERTURA (oficial) x por SAIDA (metodo antigo)")
    for nome, h in INSTALACOES.items():
        log = MEIO / "Terminal" / h / "Tester" / "logs" / f"{args.dia}.log"
        if not log.exists():
            continue
        pares = pares_retencao(log, args.desde)
        if not pares:
            print(f"  {nome}: nenhum passe IS+OOS com as duas ainda")
            continue
        difs = [abs(a - b) for a, b in pares]
        print(f"  {nome}: {len(pares)} passes | |diferenca| media "
              f"{sum(difs) / len(difs):.1f} pp, max {max(difs):.1f} pp | "
              f"ex.: " + ", ".join(f"{a:.1f}x{b:.1f}" for a, b in pares[:4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
