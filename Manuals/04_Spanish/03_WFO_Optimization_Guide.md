# White Rabbit X — Guía de optimización WFO

Referencia autoritativa generada desde la fuente actual y el manifiesto de sets — EA 1.11 — 127 inputs — 3738 sets

**Atención a la fecha.** Con el WFO activado, OnTester compara el final real de la prueba con input_end_date y devuelve cero si la prueba terminó antes (tolerancia de 80 horas). Una fecha equivocada pone a cero todas las pasadas y toda la optimización parece rota. Ajuste input_end_date a la misma fecha final configurada en el Probador de Estrategias.

## Alcance y fuentes de verdad

La fuente define inputs, valores y funciones; el manifiesto define cada set, estado, ruta y SHA-256. El archivo Quantum antiguo es solo histórico.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Material generado; los identificadores coinciden exactamente con la EA.

## Método walk-forward

Use IS, OOS y forward demo cronológicos con spread, comisión, swap y slippage realistas.

## Flujo seguro

Cambie una sola matriz por etapa y conserve la evidencia.

1. Confirme que EX5, fuente, esquema y manifiesto son de la misma versión.
2. Cargue la biblioteca mediante Strategy Tester Inputs.
3. Mapee el símbolo y suffix exactos del bróker.
4. Empiece por baseline 01–05 y separe BUY/SELL.
5. Use 06 para una sola variable.
6. Use 07 entrada, 08 filtros, 09 riesgo y 10 salidas.
7. Ejecute IS, OOS y forward demo cronológicos.
8. Compruebe Status, RelativePath y SHA256.
9. Solo USE explícito autoriza el entorno definido.

## Estados y decisión

Se conserva el estado exacto y se mapea de forma conservadora a USE, REOPTIMIZE, RESEARCH o HOLD.

| Sistema | Gestión | Sets |
| --- | --- | ---: |
| `01_SLTP` | Stop Loss + Take Profit as ATR multiples | 356 |
| `02_SLTP_ORGANIC` | SL + organic take anchored on the last trade | 356 |
| `03_TRAIL_ONLY` | SL + trailing, no TP: let it run | 356 |
| `04_SLTP_TRAIL` | SL + TP + trailing behind | 356 |
| `05_BE_TRAIL` | Mandatory breakeven + trailing | 356 |
| `06_REVERSAL_EXIT` | Closes on the indicator's opposite signal | 356 |
| `07_GRID_SEPARATE` | Grid with a target per side (hedging account) | 356 |
| `08_GRID_UNIFIED` | Grid with a single basket target (hedging account) | 356 |
| `09_MARTINGALE` | Lot doubles after a loss, one position per side | 356 |
| `10_DALEMBERT` | Lot grows in arithmetic steps after a loss | 356 |
| `11_SIGNAL_ONLY` | No SL and no TP: measures the raw signal | 356 |

> Esta sección todavía está disponible solo en inglés.

## Modeling mode: use real ticks

In the Strategy Tester's **Settings** tab, **Modeling** field:

```
Every tick based on real ticks   <- use this
OHLC 1 minute                    <- only 01_SLTP and 02_SLTP_ORGANIC
```

This is not a preference. Measuring the same set in both modes across three
years, the OHLC mode **understated losses by 3.3x on trailing systems and 23x
on grid** — always in the optimistic direction. Only fixed SL/TP stayed within
3%.

The cause is structural: trailing and grid depend on **when** price touched each
level inside the bar. OHLC mode interpolates that from four prices per minute
and smooths away exactly the adverse excursions that would have closed the
position. Optimizing a trailing system on interpolated bars selects parameters
that survived a price path which never happened.

Real ticks cost roughly 20x more time per pass. It is worth it: that is the
difference between a result and a number.

### If you must save time, save it in the right place

Signals are evaluated at BAR CLOSE, so choosing indicator, method or timeframe
gives the same entry instant in both modes. Stop, target and trailing, on the
other hand, depend on the intrabar path.

So use each model where it is reliable: OHLC to narrow the switches (indicator,
method, timeframe, periods) and real ticks for the exit geometry. With the
signal locked the search space collapses by orders of magnitude, and real ticks
stop being prohibitive.

## Fixed-R to research, percentage to trade

Optimize in **Fixed-R**: with the base capital frozen, passes stay comparable to
each other and across symbols. +40R on gold and +40R on EURUSD mean the same
thing, while "+3,200 USD" means nothing without knowing the lot and the balance.

Live, **Percentage** usually makes more sense: it tracks the account, compounds
as it grows and cuts exposure as it shrinks — protection Fixed-R cannot give,
because it deliberately ignores the running balance. Both modes report in R, so
the record stays readable after the switch.

## Aviso de riesgo

Ninguna EA, set ni resultado histórico garantiza el futuro. Valide OOS y en demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
