# -*- coding: utf-8 -*-
"""Liga/desliga o Walk-Forward nos sets do White Rabbit X.

O WFO do EA nao e o "Forward" nativo do Strategy Tester: e interno. Com
AtivarWFO=true e isBacktest, o OnInit fatia o periodo em janelas In-Sample e
Out-of-Sample a partir da PRIMEIRA BARRA do teste ate input_end_date, e o
OnTick usa IsInSample() para decidir se opera.

  MetodoDeEntradawfo = Insample (0)
      WFOENABLE = true -> fora das janelas IS o EA FECHA posicoes, nao abre
      novas e chama WithdrawProfit() para nao contaminar o equity.
      E o modo de OTIMIZAR: o genetico so ve In-Sample.

  MetodoDeEntradawfo = InSampleAndOutSample (1)
      WFOENABLE = false -> opera o periodo inteiro, mas continua marcando as
      janelas, e o relatorio de walk-forward sai no ONDEINIT (nao no OnTester):
      WFE agregada = lucro medio diario OOS / lucro medio diario IS * 100, mais
      a WFE de CADA ciclo com media e desvio. E o modo de VALIDAR o vencedor.

      Ler o desvio, nao so a media: WFE media de 80% com desvio de 90% e sorte
      concentrada numa janela, nao robustez. O relatorio tambem diz quantos
      ciclos foram lucrativos fora da amostra, que e o numero mais honesto.

ARMADILHA: o OnTester compara o fim real do teste com input_end_date e
devolve 0.0 se o teste terminou antes (tolerancia de 80h). Data errada =
TODOS os passes valem zero. Por isso este script existe: a data tem que ser
escrita nos arquivos, nao lembrada.

Uso:
    python configure_wfo.py --end-date 2026.07.21 --is-days 180 --oos-days 60
    python configure_wfo.py --off
    python configure_wfo.py --end-date 2026.07.21 --is-days 180 --oos-days 60 \\
        --mode validate --only 01_Forex/USDJPY
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Lucas Pedroso\AppData\Roaming\MetaQuotes\Terminal"
            r"\D2A36B4A61A508797F5C460B1F34DC5D\MQL5\Profiles\Tester"
            r"\White_Rabbit_X_Sets_templates")

# WFO_TIME_PERIOD do EA: os valores sao dias, Custom = -1 (CUSTOM_DAYS).
PRESETS = {360: "Ano", 180: "Semestre", 90: "Trimestre", 30: "Mes",
           7: "Semana", 1: "Dia"}
CUSTOM = -1


def window_fields(days: int) -> tuple[int, int]:
    """(wfo_windowSize, wfo_customWindowSizeDays) para um IS de N dias.

    Sempre Custom. Usar o preset quando o numero calha de estar na lista
    deixaria o arquivo inconsistente -- 180 viraria "Semestre" e 122 ficaria em
    Custom, com a janela aparecendo em campos diferentes conforme o valor. Em
    Custom o numero de dias fica sempre no mesmo lugar e legivel.
    """
    return CUSTOM, days


def step_fields(days: int) -> tuple[int, int]:
    """(wfo_stepSize, wfo_customStepSizePercent) para um OOS de N dias.

    No EA, customStepSizePercent NEGATIVO significa "dias fixos" (o sinal e
    invertido internamente); positivo seria percentual do IS.
    """
    return CUSTOM, -days


def patch(path: Path, changes: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-16")
    out, touched = [], False
    for line in text.splitlines():
        m = re.match(r"^([^;=]+)=(.*)$", line)
        if m and m.group(1) in changes:
            name = m.group(1)
            value = changes[name]
            parts = m.group(2).split("||")
            new = (f"{value}||{value}||"
                   f"{'0' if value in ('true', 'false') else '1'}||{value}||N"
                   if len(parts) == 5 else value)
            if new != m.group(2):
                touched = True
            out.append(f"{name}={new}")
        else:
            out.append(line)
    if touched:
        path.write_text("\r\n".join(out) + "\r\n", encoding="utf-16")
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--end-date", help="fim do teste, yyyy.mm.dd (igual ao tester)")
    ap.add_argument("--is-days", type=int, help="dias da janela In-Sample")
    ap.add_argument("--oos-days", type=int, help="dias da janela Out-of-Sample")
    ap.add_argument("--mode", choices=("optimize", "validate"), default="optimize",
                    help="optimize = so In-Sample; validate = IS+OOS com WFE")
    ap.add_argument("--only", default="", help="filtra por trecho do caminho")
    ap.add_argument("--off", action="store_true", help="desliga o WFO")
    ap.add_argument("--fase", type=int, choices=(1, 2, 3),
                    help="troca o criterio de otimizacao junto: 1 sinal, "
                         "2 filtros, 3 sessao")
    args = ap.parse_args()

    if args.off:
        changes = {"AtivarWFO": "false"}
        label = "WFO DESLIGADO"
    else:
        missing = [f for f in ("end_date", "is_days", "oos_days")
                   if getattr(args, f) is None]
        if missing:
            ap.error(f"faltam: {', '.join('--' + m.replace('_', '-') for m in missing)}")
        try:
            datetime.strptime(args.end_date, "%Y.%m.%d")
        except ValueError:
            ap.error("--end-date precisa ser yyyy.mm.dd")
        if args.is_days <= 0 or args.oos_days <= 0:
            ap.error("janelas precisam ser > 0 (o OnInit rejeita zero ou negativo)")
        if args.oos_days > args.is_days:
            print(f"AVISO: OOS ({args.oos_days}d) maior que IS ({args.is_days}d). "
                  "O usual e IS entre 2x e 4x o OOS.")
        win, win_days = window_fields(args.is_days)
        step, step_pct = step_fields(args.oos_days)
        changes = {
            "AtivarWFO": "true",
            "MetodoDeEntradawfo": "0" if args.mode == "optimize" else "1",
            "input_end_date": args.end_date,
            "wfo_windowSize": str(win),
            "wfo_customWindowSizeDays": str(win_days),
            "wfo_stepSize": str(step),
            "wfo_customStepSizePercent": str(step_pct),
        }
        label = (f"WFO {args.mode.upper()} | IS={args.is_days}d OOS={args.oos_days}d "
                 f"| fim={args.end_date}")

        # Cada fase decide uma coisa diferente, e o criterio precisa medir o que
        # ela decide. Usar o mesmo nas tres ATRAPALHA: filtro reduz o numero de
        # operacoes, entao otimizar a fase 2 por lucro total pune justamente o
        # filtro que corta entrada ruim, mesmo melhorando a qualidade de cada
        # uma. Indices conferidos no enum CustomFormulaType da EA.
        CRITERIO_DA_FASE = {
            1: (9, "Pessimistic Average Profit",
                "o sinal tem vantagem, ou os ganhos vieram de poucas "
                "operacoes felizes?"),
            2: (7, "Drawdown-Adjusted Profit per Trade",
                "qualidade POR OPERACAO -- nao pune o filtro por operar menos"),
            3: (11, "Return Uniformity",
                "filtro de sessao existe para tirar periodo ruim; "
                "uniformidade mede exatamente isso"),
        }
        if args.fase:
            indice, nome, porque = CRITERIO_DA_FASE[args.fase]
            changes["selectedFormula"] = str(indice)
            label += f"\nFase {args.fase}: criterio {nome} -- {porque}"
            if args.fase > 1:
                label += ("\nLembre de TRAVAR o que a fase anterior decidiu "
                          "(valor vencedor nos quatro campos, marca em N).")

    files = [p for p in sorted(ROOT.rglob("*.set"))
             if not args.only or args.only in p.relative_to(ROOT).as_posix()]
    if not files:
        print("Nenhum .set encontrado com esse filtro.")
        return 1

    changed = sum(1 for p in files if patch(p, changes))
    print(f"{label}")
    print(f"Arquivos alcancados: {len(files)} | alterados: {changed}")
    if not args.off:
        total = args.is_days + args.oos_days
        print(f"\nO teste precisa cobrir pelo menos {total} dias "
              f"(o OnInit rejeita IS+OOS maior que o periodo).")
        print(f"A data final do Strategy Tester tem que ser {args.end_date} "
              "(tolerancia de 80h); senao o OnTester devolve 0 em todo passe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
