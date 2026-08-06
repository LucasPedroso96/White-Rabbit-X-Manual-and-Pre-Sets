# -*- coding: utf-8 -*-
"""Diagnostico pontual (2026-08-04): AtivarWFO=false vs true+IS/OOS no periodo
completo, contra o candidato EURUSD/07_GRID_SEPARATE/BUY_MULTI aprovado hoje
(pedido do dono: testar em EURUSD, nao no AUDCHF antigo que ja foi limpo).

Todo o resto do circuito roda com AtivarWFO=true (so alterna IS <-> IS+OOS);
so a entrega final (e o gate de sobrevivencia) desligava tudo -- um regime
NUNCA testado em nenhum outro estagio. Pergunta do dono: sera que o problema
e o AtivarWFO=false em si (regime nao testado), ou a explosao acontece de
qualquer jeito no periodo completo, independente disso?

Este combo especifico JA sobreviveu ao gate com AtivarWFO=false (saldo final
3335.25, partindo de 500) -- entao aqui nao se espera achar uma explosao,
mas sim comparar se os DOIS regimes dao o MESMO resultado (confirmando que
AtivarWFO nao muda o comportamento de trading) ou resultados DIFERENTES
(mostrando que o regime importa, mesmo quando os dois "passam").

Roda DOIS passes de sobrevivencia (periodo completo, tick real) com os
MESMOS parametros vencedores:
  A) AtivarWFO=false                              (como foi entregue)
  B) AtivarWFO=true, MetodoDeEntradawfo=1 (IS+OOS) (o mesmo regime que
     mediu a retencao aprovada no Estagio 4 -- WFOENABLE=false nesse modo,
     entao nao restringe quando opera, so rotula os trades)

Uso:
    python diagnostico_wfo_regime.py
"""
from __future__ import annotations

import optimize_sets as base
import optimize_two_stage as ots

TEMPLATE = (base.DADOS / "MQL5" / "Profiles" / "Tester" /
            "White_Rabbit_X_Sets_templates" / "01_Forex" / "EURUSD" /
            "07_GRID_SEPARATE" / "BUY_MULTI.set")

# Parametros vencedores do EURUSD/07_GRID_SEPARATE/BUY_MULTI aprovado em
# 2026-08-04 (retencao medida no Estagio 4, saldo final do periodo completo
# com AtivarWFO=false = 3335.25, partindo de deposito 500).
VENCEDOR = {
    "TimeFrame": "1", "EntryIndicator": "1", "InpAppliedPrice": "3",
    "EntryMethod": "2", "StochasticMethod": "1", "StochasticPriceField": "1",
    "ATR_TimeFrame": "0", "AtivarFiltroMTF": "false", "AtivarFiltroMA": "false",
    "AtivarFiltroADX": "false", "EntradaATR": "false",
    "UsarsomenteATRGRID": "true", "Fast_EMA": "9", "Slow_EMA": "45",
    "PeriodoATR": "21", "VelaTake": "2", "Take": "8.5",
    "DistanciaMinima": "3.0", "Fecharordensforadohorario": "false",
    "TOD_From_Hour": "5", "TOD_To_Hour": "20", "TradeMonday": "true",
    "TradeTuesday": "true", "TradeWednesday": "true", "TradeThursday": "true",
    "TradeFriday": "true", "MaxSpread": "25", "InterfaceLanguage": "0",
}

SYMBOL = "EURUSD"
INICIO = "2023.08.01"
FIM = "2026.08.03"
DEPOSITO = 500


def main() -> None:
    tester = base.DADOS / "MQL5" / "Profiles" / "Tester"
    trabalho_a = tester / "_DIAG_WFO_OFF.set"
    trabalho_b = tester / "_DIAG_WFO_ON_MODE1.set"

    # Variante A: como foi entregue (AtivarWFO desligado).
    entrega_a = dict(VENCEDOR, AtivarWFO="false")
    ots.reescrever(TEMPLATE, trabalho_a, [], entrega_a)

    # Variante B: AtivarWFO ligado, mesmo regime (IS+OOS) que mediu a
    # retencao aprovada no Estagio 4 -- janelas_wfo() deriva IS/OOS da MESMA
    # forma que o circuito real usa, so troca o modo para 1.
    janelas = ots.janelas_wfo(INICIO, FIM)
    janelas["MetodoDeEntradawfo"] = "1"
    entrega_b = dict(VENCEDOR, **janelas)
    ots.reescrever(TEMPLATE, trabalho_b, [], entrega_b)

    print(f"=== Variante A: AtivarWFO=false (como foi entregue em 2026-08-03) ===",
          flush=True)
    ra = ots.verificar_sobrevivencia_completa(
        trabalho_a, SYMBOL, "M1", INICIO, FIM, DEPOSITO, 1800)
    print(f"resultado A: {ra}", flush=True)

    print(f"\n=== Variante B: AtivarWFO=true, MetodoDeEntradawfo=1 (proposta) ===",
          flush=True)
    rb = ots.verificar_sobrevivencia_completa(
        trabalho_b, SYMBOL, "M1", INICIO, FIM, DEPOSITO, 1800)
    print(f"resultado B: {rb}", flush=True)

    print("\n=== CONCLUSAO ===", flush=True)
    if ra["sobreviveu"] == rb["sobreviveu"]:
        print("Mesmo resultado nos dois regimes -- o problema NAO e o "
              "AtivarWFO=false em si, e o periodo completo continuo mesmo.",
              flush=True)
    elif rb["sobreviveu"] and not ra["sobreviveu"]:
        print("Variante B sobreviveu e A nao -- AtivarWFO=false E O "
              "DIFERENCIADOR. Entregar em AtivarWFO=true+modo1 evita a "
              "explosao (precisa investigar o mecanismo: WithdrawProfit(), "
              "capital-base, ou algo em EffectiveCapital()).", flush=True)
    else:
        print("Variante A sobreviveu e B nao -- inesperado, investigar o "
              "log bruto de ambas as corridas antes de tirar conclusao.",
              flush=True)


if __name__ == "__main__":
    main()
