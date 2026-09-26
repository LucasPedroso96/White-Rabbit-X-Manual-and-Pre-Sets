# -*- coding: utf-8 -*-
"""Sonda: a EA ABRE trade nas janelas Out-of-Sample quando roda em
'In Sample + Out Sample'? Le o log bruto do tester (Tester/logs/AAAAMMDD.log,
UTF-16) e, para cada passe nesse modo, compara as entradas dentro das janelas
OOS com o que o ritmo do IS (entradas por dia) prometia.

Existe por causa do achado de 2026-09-25: uma regressao de 13/09 deixou o
bloqueio de entrada nova no OOS valendo tambem nesse modo -- quase nenhuma
entrada abria fora da amostra, e a "retencao" passou 12 dias medindo so
posicao do IS fechando depois da borda (0.0% exato, 5740%...). Nada no Python
via isso: o numero de retencao parecia plausivel.

    python sonda_oos.py <pasta_de_dados_mt5> [AAAAMMDD] [--desde HH:MM]

Saida 1 = ha passe suspeito (OOS abrindo menos de 1/4 do ritmo do IS).
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

_DATA = r"(\d{4}\.\d{2}\.\d{2})"
_JANELA_OOS = re.compile(r"Out-Sample \(OOS\): " + _DATA + " - " + _DATA)
_JANELA_IS = re.compile(r"In-Sample \(IS\): " + _DATA + " - " + _DATA)
_ENTRADA = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+market (buy|sell) ")
_INICIO_PASSE = "Running with In-Sample + Out-of-Sample data"
_FIM_PASSE = "--- Out-of-Sample Retention"


def _data(txt: str) -> datetime:
    return datetime.strptime(txt, "%Y.%m.%d")


def analisar(linhas: list[str]) -> list[dict]:
    """Um dict por passe IS+OOS completo: hora do log, simbolo, dias e
    entradas no IS e no OOS. `linhas` = log ja decodificado."""
    passes: list[dict] = []
    janelas: list[tuple[datetime, datetime]] = []
    dias_is = 0
    simbolo = None
    atual: dict | None = None
    for linha in linhas:
        campos = linha.split("\t")
        msg = campos[-1]
        hora = campos[2] if len(campos) >= 5 else ""
        if "testing of Experts" in msg and "started with inputs" in msg:
            simbolo = msg.split(",", 1)[0].strip()
            janelas, dias_is = [], 0
            continue
        m = _JANELA_IS.search(msg)
        if m:
            dias_is += (_data(m.group(2)) - _data(m.group(1))).days
            continue
        m = _JANELA_OOS.search(msg)
        if m:
            janelas.append((_data(m.group(1)), _data(m.group(2))))
            continue
        if _INICIO_PASSE in msg:
            atual = {"hora": hora, "simbolo": simbolo,
                     "janelas": list(janelas), "dias_is": dias_is,
                     "dias_oos": sum((f - i).days for i, f in janelas),
                     "entradas_is": 0, "entradas_oos": 0}
            continue
        if atual is None:
            continue
        m = _ENTRADA.search(msg.strip())
        if m:
            quando = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
            dentro = any(ini <= quando < fim for ini, fim in atual["janelas"])
            atual["entradas_oos" if dentro else "entradas_is"] += 1
            continue
        if _FIM_PASSE in msg:
            passes.append(atual)
            atual = None
    return passes


def esperado_oos(p: dict) -> float:
    """Entradas que o OOS teria no MESMO ritmo (por dia) do IS."""
    if not p["dias_is"]:
        return 0.0
    return p["entradas_is"] * p["dias_oos"] / p["dias_is"]


def suspeitos(passes: list[dict], min_esperado: float = 8.0,
              fracao: float = 0.25) -> list[dict]:
    """Passes cujo OOS abriu bem menos que o ritmo do IS prometia. Zero nao
    e o unico sintoma: continuacao de grid e entrada no dia exato da borda
    escapavam do bloqueio (GBPUSD 25/09: 112 no IS, 4 no OOS, ~37
    esperados). Menos de 1/4 do esperado, com esperado >= 8, nao e acaso."""
    return [p for p in passes
            if esperado_oos(p) >= min_esperado
            and p["entradas_oos"] < fracao * esperado_oos(p)]


def ler_log(caminho: Path) -> list[str]:
    texto = caminho.read_text(encoding="utf-16", errors="replace")
    return texto.replace("\r", "").split("\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta_dados", type=Path)
    ap.add_argument("dia", nargs="?", default=datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--desde", default="", help="HH:MM do log (hora real)")
    ap.add_argument("--quieto", action="store_true",
                    help="so o resumo final")
    args = ap.parse_args()
    log = args.pasta_dados / "Tester" / "logs" / f"{args.dia}.log"
    passes = [p for p in analisar(ler_log(log)) if p["hora"] >= args.desde]
    if not args.quieto:
        for p in passes:
            print(f"{p['hora'][:8]} {p['simbolo']:<14} "
                  f"IS {p['entradas_is']:5d} entradas/{p['dias_is']}d | "
                  f"OOS {p['entradas_oos']:5d}/{p['dias_oos']}d "
                  f"(esperado ~{esperado_oos(p):.0f})")
    ruins = suspeitos(passes)
    print(f"{len(passes)} passe(s) IS+OOS; {len(ruins)} com o OOS abrindo "
          "menos de 1/4 do ritmo do IS"
          + (" -- SUSPEITO de bloqueio no OOS" if ruins else ""))
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
