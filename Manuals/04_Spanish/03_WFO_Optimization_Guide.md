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
4. Navegue por clase y activo: cada activo trae los 11 tipos de sistema (01_SLTP a 11_SIGNAL_ONLY), un set por lado (BUY/SELL; BOTH en el grid unificado) y dos variantes de entrada — MULTI disputa los indicadores 0–10 en un solo eje, ICHIMOKU tiene archivo propio.
5. La fase 1 es descubrimiento de regiones: ejecute el genetico con el set tal cual — grupo de entrada completo (indicador, metodo, timeframe, applied price, periodos), salidas del sistema y llaves de filtro, todo a la vez.
6. De las rondas siguientes en adelante, bloquee (Y→N) los inputs de escritura — enums y booleanos — decididos por la fase anterior y deje abiertos solo los numericos; el ajuste de cada filtro solo entra si su llave sobrevivio encendida.
7. El filtro ATR de entrada (EntradaATR) existe solo en los sistemas de grid; en los demas permanece apagado por diseño.
8. Valide al ganador en ticks reales: deciden la divergencia contra OHLC y la retencion out-of-sample, nunca la ganancia in-sample. Rechace un candidato cuyo resultado en tick real diverja del resultado OHLC en más del 30% — ambos deben coincidir en la forma del resultado, no solo en el signo.
8a. Filtre al sobreviviente con Monte Carlo: remuestree la secuencia de operaciones mediante bootstrap (en múltiplos de R, no en moneda) y rechace si el drawdown en el percentil 95 supera el doble del drawdown observado, o si la probabilidad de ruina remuestreada supera el 5%. Un set que solo parece estable por el orden específico en que ocurrieron sus operaciones no es estable.
8b. Para los seis sistemas Fixed-R (`01` a `06`), exija una expectativa en R positiva fuera de muestra. Un set que empató o perdió R fuera de muestra no se promueve, sin importar su puntuación in-sample.
9. Tras el tick real, cambie el dimensionamiento a Percentage y ejecute de nuevo: solo promueva si tambien pasa — y ese es el modo en que el set debe operar.

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

Por eso el circuito solo guarda un set aprobado tras repetir el pase final en modo Percentage: si el resultado no se sostiene bajo interes compuesto, no estaba listo — y el set validado se entrega en ese modo.

## Fórmulas: qué optimizan y qué reporta el resultado

`selectedFormula` decide qué devuelve OnTester al optimizador genético — el número único con el que se clasifica cada pasada. No es la misma pregunta que "en qué reporta el set entregado". El circuito usa fórmulas distintas para tareas distintas: las fases iniciales favorecen fórmulas que premian un resultado amplio y bien poblado (para que la búsqueda genética tenga un gradiente que escalar), en lugar de una fórmula estrecha que puntúa alto solo en un camino específico.

Para los seis sistemas Fixed-R, el reporte final del set entregado usa **SomaR** (la suma de los resultados de las operaciones en múltiplos de R): una vez que un candidato ya pasó la retención, la divergencia, el Monte Carlo y el filtro de expectativa en R anterior, SomaR es lo que expresa el resultado en la misma unidad que el resto de esta guía usa para comparar símbolos y sistemas — R, no moneda. No decide al ganador; reporta el resultado del ganador ya decidido en una unidad comparable.

## Autobot y Historical Tool Manager

Esta biblioteca se entrega prevalidada, pero el circuito descrito arriba no es una caja negra — se publica como **Autobot** en el mismo repositorio donde vive este manual (`Autobot/`), el código real que ejecuta cada paso de esta guía. Léalo para ver exactamente cómo un set se ganó su estatus, o ejecútelo usted mismo contra su propio bróker, lista de símbolos o rango de fechas.

El paso de confirmación en tick real depende de contar con datos de tick reales contra los cuales confirmar. **Historical Tool Manager** (MQL5 Market: https://www.mql5.com/pt/market/product/188711) importa historial profundo de tick y M1 a MT5 como Custom Symbol para instrumentos cuyo propio historial del bróker no cubre suficiente tiempo atrás — útil tanto si ejecuta el Autobot como si solo quiere más historial para probar manualmente.

## Aviso de riesgo

Ninguna EA, set ni resultado histórico garantiza el futuro. Valide OOS y en demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
