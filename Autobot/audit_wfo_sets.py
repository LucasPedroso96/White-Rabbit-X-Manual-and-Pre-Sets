# -*- coding: utf-8 -*-
"""Audita o bloco Walk-Forward de todos os sets da biblioteca.

O validate_system_sets confere o schema e as regras do OnInit. Este script olha
so o WFO, porque ele tem armadilhas que nao disparam erro nenhum -- o teste
roda, termina, e devolve numero errado (ou zero) sem avisar:

  1. input_end_date que nao bate com a data final do tester faz o OnTester
     devolver 0.0 em TODO passe (tolerancia de 80h). Otimizacao inteira zerada,
     sem mensagem de erro.
  2. wfo_customStepSizePercent POSITIVO significa percentual do In-Sample;
     NEGATIVO significa dias fixos. Trocar o sinal muda a janela em silencio.
  3. wfo_windowSize/stepSize precisam ser -1 (Custom) para os campos em dias
     valerem. Com um preset (Ano=360, Semestre=180...) os dias sao IGNORADOS.
  4. IS + OOS maior que o periodo do teste faz o OnInit recusar tudo.
  5. wfo_windowMode nao existe mais: janelas deslizantes se sobrepoem e fazem a
     mesma barra contar como IS e OOS ao mesmo tempo. Set que ainda carregue a
     chave veio de uma geracao antiga.

Uso:
    python audit_wfo_sets.py
    python audit_wfo_sets.py --periodo-dias 1095
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
            r"\59EECBFD4A9CCD98CCBC61E96D5DED8E\MQL5\Profiles\Tester"
            r"\White_Rabbit_X_Sets_templates")

CUSTOM = -1


def campos(texto: str) -> dict[str, list[str]]:
    """nome -> partes da tupla (1 elemento quando o campo e string crua)."""
    saida = {}
    for linha in texto.splitlines():
        m = re.match(r"^([^;=]+)=(.*)$", linha)
        if m:
            saida[m.group(1).strip()] = m.group(2).split("||")
    return saida


def auditar(path: Path, periodo_dias: int) -> list[str]:
    d = campos(path.read_text(encoding="utf-16"))
    problemas: list[str] = []

    def valor(nome: str) -> str | None:
        return d[nome][0] if nome in d else None

    def travado(nome: str) -> bool:
        """Campo com 5 partes e sufixo N nao entra na otimizacao."""
        return nome in d and len(d[nome]) == 5 and d[nome][4] == "N"

    if "wfo_windowMode" in d:
        problemas.append("wfo_windowMode presente (geracao antiga; janelas "
                         "deslizantes se sobrepoem)")

    for nome in ("AtivarWFO", "MetodoDeEntradawfo", "wfo_windowSize",
                 "wfo_customWindowSizeDays", "wfo_stepSize",
                 "wfo_customStepSizePercent", "input_end_date"):
        if nome not in d:
            problemas.append(f"{nome} ausente")
    if problemas:
        return problemas

    # Nenhum campo do WFO pode virar eixo: sao metodologia, nao parametro. Um
    # Y aqui multiplica os passes e mistura janelas diferentes no mesmo estudo.
    for nome in ("AtivarWFO", "MetodoDeEntradawfo", "wfo_windowSize",
                 "wfo_customWindowSizeDays", "wfo_stepSize",
                 "wfo_customStepSizePercent"):
        if not travado(nome):
            problemas.append(f"{nome} marcado para otimizar (deveria ser N)")

    data = valor("input_end_date")
    try:
        datetime.strptime(data, "%Y.%m.%d")
    except (ValueError, TypeError):
        problemas.append(f"input_end_date invalido: {data!r} (esperado yyyy.mm.dd)")

    try:
        win = int(valor("wfo_windowSize"))
        step = int(valor("wfo_stepSize"))
        is_dias = int(valor("wfo_customWindowSizeDays"))
        pct = int(valor("wfo_customStepSizePercent"))
    except (TypeError, ValueError):
        problemas.append("campos numericos do WFO ilegiveis")
        return problemas

    if win != CUSTOM:
        problemas.append(f"wfo_windowSize={win} nao e Custom(-1): "
                         f"os {is_dias} dias serao IGNORADOS")
    if step != CUSTOM:
        problemas.append(f"wfo_stepSize={step} nao e Custom(-1): "
                         f"o passo em dias sera IGNORADO")
    if is_dias <= 0:
        problemas.append(f"In-Sample = {is_dias} dias (OnInit recusa <= 0)")
    if pct == 0:
        problemas.append("wfo_customStepSizePercent=0 anula o passo Custom")
    elif pct > 0:
        oos = int(pct / 100.0 * is_dias)
        problemas.append(f"wfo_customStepSizePercent={pct} e POSITIVO = "
                         f"{pct}% do IS = {oos} dias (para dias fixos use negativo)")
    else:
        oos = -pct
        if oos > is_dias:
            problemas.append(f"OOS ({oos}d) maior que IS ({is_dias}d); "
                             "o usual e IS entre 2x e 4x o OOS")
        if is_dias + oos > periodo_dias:
            problemas.append(f"IS+OOS = {is_dias + oos}d nao cabe em "
                             f"{periodo_dias}d de teste (OnInit recusa)")
    return problemas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--periodo-dias", type=int, default=1095,
                    help="periodo do backtest planejado (default 3 anos)")
    args = ap.parse_args()

    arquivos = sorted(ROOT.rglob("*.set"))
    if not arquivos:
        print(f"Nenhum .set em {ROOT}")
        return 1

    ruins: dict[str, list[str]] = {}
    perfis = Counter()
    for path in arquivos:
        p = auditar(path, args.periodo_dias)
        if p:
            ruins[str(path.relative_to(ROOT))] = p
        d = campos(path.read_text(encoding="utf-16"))
        perfis[(d.get("AtivarWFO", ["?"])[0],
                d.get("wfo_customWindowSizeDays", ["?"])[0],
                d.get("wfo_customStepSizePercent", ["?"])[0],
                d.get("input_end_date", ["?"])[0])] += 1

    print(f"Sets auditados: {len(arquivos)}")
    print(f"Periodo de teste assumido: {args.periodo_dias} dias\n")
    print("Configuracoes WFO encontradas (AtivarWFO, IS dias, passo, data final):")
    for chave, n in perfis.most_common():
        ativo, isd, passo, data = chave
        oos = f"{-int(passo)}d" if passo.lstrip("-").isdigit() and int(passo) < 0 \
            else f"{passo}?"
        print(f"  {n:>5} sets | WFO={ativo:<5} IS={isd}d OOS={oos} fim={data}")

    if ruins:
        print(f"\nPROBLEMAS em {len(ruins)} sets:")
        amostra = list(ruins.items())[:15]
        for nome, lista in amostra:
            print(f"  {nome}")
            for item in lista:
                print(f"      - {item}")
        if len(ruins) > len(amostra):
            print(f"  ... e mais {len(ruins) - len(amostra)}")
        return 1

    print("\nOK: bloco WFO integro e coerente em todos os sets.")
    print("Lembrete: AtivarWFO=false e proposital -- o WFO e opt-in, porque")
    print("ligar exige que input_end_date bata com a data final do tester.")
    print("Para ligar:  python configure_wfo.py --end-date <yyyy.mm.dd> "
          "--is-days 122 --oos-days 61")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
