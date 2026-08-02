# -*- coding: utf-8 -*-
"""Calcula o capital base minimo para o Fixed-R funcionar em cada classe.

O problema: com capital pequeno, o menor lote negociavel arrisca mais do que o
percentual pedido. O Fixed-R entao nao consegue respeitar o 1R -- ou o EA nao
abre, ou abre arriscando mais do que o configurado, e a otimizacao inteira mede
uma coisa diferente da que foi pedida.

O capital nao vem do deposito do tester: vem de CapitalBaseR. Com ele em zero,
o EA usa o saldo do OnInit, e a otimizacao passa a depender de quanto havia na
conta naquele dia -- dois testes do mesmo set em contas diferentes dao
resultados diferentes. Com CapitalBaseR fixo, o 1R e sempre o mesmo e os
resultados ficam comparaveis entre ativos, contas e rodadas.

Este script pergunta ao broker qual o menor capital que faz o lote minimo caber
no risco, para um stop de 3x ATR -- que e o multiplicador central dos sets.
"""
from __future__ import annotations

import statistics
import sys
from datetime import datetime, timedelta

CLASSES = {
    "01_Forex": (["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY"], "H1"),
    "02_Metals": (["XAUUSD", "XAGUSD"], "H1"),
    "03_Cryptocurrencies": (["BTCUSD", "ETHUSD"], "H4"),
    "04_Indices_Energies": (["BRENT", "WTI"], "M30"),
    "05_US_Stocks_CFD": (["AAPL", "MSFT", "TSLA"], "H4"),
}
STOP_ATR = 3.0        # sl_mid dos sets fica em torno disso
ATR_PERIODO = 14
BARRAS = 500


def resolver(mt5, base: str):
    """Acha o nome real do simbolo, com o sufixo que o broker usa."""
    info = mt5.symbol_info(base)
    if info:
        return info
    for s in mt5.symbols_get():
        if s.name.startswith(base):
            mt5.symbol_select(s.name, True)
            return mt5.symbol_info(s.name)
    return None


def atr_medio(mt5, symbol: str, timeframe) -> float:
    barras = mt5.copy_rates_from(symbol, timeframe, datetime.now(), BARRAS)
    if barras is None or len(barras) < ATR_PERIODO + 1:
        return 0.0
    faixas = []
    for i in range(1, len(barras)):
        anterior = barras[i - 1]["close"]
        faixas.append(max(
            barras[i]["high"] - barras[i]["low"],
            abs(barras[i]["high"] - anterior),
            abs(barras[i]["low"] - anterior)))
    return statistics.fmean(faixas[-ATR_PERIODO * 4:]) if faixas else 0.0


def main() -> int:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 nao instalado.")
        return 1
    if not mt5.initialize():
        print(f"Terminal nao respondeu: {mt5.last_error()}")
        return 1

    tf_map = {"M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1,
              "H4": mt5.TIMEFRAME_H4}
    print(f"Stop de referencia: {STOP_ATR:g}x ATR({ATR_PERIODO})")
    print(f"{'Classe':<22}{'Simbolo':<12}{'ATR':>10}{'Risco/trade':>13}"
          f"{'Cap. 1%':>11}{'Cap. 2%':>11}")
    print("-" * 79)

    piores: dict[str, float] = {}
    for classe, (simbolos, tf) in CLASSES.items():
        for base in simbolos:
            info = resolver(mt5, base)
            if info is None:
                continue
            atr = atr_medio(mt5, info.name, tf_map[tf])
            if atr <= 0 or info.trade_tick_size <= 0:
                continue

            # Perda, em moeda, de um stop de STOP_ATR no menor lote possivel.
            ticks = (atr * STOP_ATR) / info.trade_tick_size
            risco = ticks * info.trade_tick_value * info.volume_min

            # Para 1% cobrir esse risco, o capital base precisa ser 100x ele.
            cap1 = risco * 100
            cap2 = risco * 50
            piores[classe] = max(piores.get(classe, 0.0), cap1)
            print(f"{classe:<22}{info.name:<12}{atr:>10.5f}{risco:>12.2f} "
                  f"{cap1:>10.0f}{cap2:>11.0f}")

    print("\nCapital base minimo por classe, com 1% de risco por trade:")
    for classe, valor in sorted(piores.items()):
        sugerido = 500
        for degrau in (500, 1000, 2500, 5000, 10000, 25000, 50000):
            if degrau >= valor:
                sugerido = degrau
                break
        else:
            sugerido = 100000
        print(f"  {classe:<24} precisa {valor:>9.0f}  ->  usar {sugerido}")

    geral = max(piores.values()) if piores else 0
    print(f"\nUm valor unico para toda a biblioteca precisaria cobrir a classe "
          f"mais exigente: {geral:.0f}")
    print("Usar valor por classe evita inflar o capital do forex so porque "
          "cripto e ouro pedem mais.")
    mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
