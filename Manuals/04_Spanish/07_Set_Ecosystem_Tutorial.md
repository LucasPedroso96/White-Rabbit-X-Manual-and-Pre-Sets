# White Rabbit X — Tutorial del ecosistema de sets

Referencia autoritativa generada desde la fuente actual y el manifiesto de sets — EA 1.11 — 127 inputs — 3738 sets

## Alcance y fuentes de verdad

La fuente define inputs, valores y funciones; el manifiesto define cada set, estado, ruta y SHA-256. El archivo Quantum antiguo es solo histórico.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Material generado; los identificadores coinciden exactamente con la EA.

## Instalación y primera prueba

Instale el EX5 correcto, cargue un set en Tester Inputs, elija el símbolo exacto y revise el Journal.

## Biblioteca de sets detectada

Las cantidades se leen de archivos y manifiesto. Cada set es una hipótesis, no una promesa. Counts and fingerprints were read at generation time.

| Folder | Sets | Purpose |
| --- | --- | --- |
| 01_Forex | 168 | Per-asset baselines — Forex. |
| 02_Metals | 18 | Per-asset baselines — Metals. |
| 03_Cryptocurrencies | 36 | Per-asset baselines — Cryptocurrencies. |
| 04_Indices_Energies | 42 | Per-asset baselines — Indices Energies. |
| 05_US_Stocks_CFD | 300 | Per-asset baselines — US Stocks CFD. |
| 06_Research_Matrix | 935 | Controlled one-axis research. |
| 07_Entry_System_Matrix | 3360 | Indicator × entry method × management matrix. |
| 08_Filter_Stack_Matrix | 320 | Signal-filter stack combinations. |
| 09_Risk_Engine_Matrix | 130 | Compatible sizing, risk and recovery models. |
| 10_Exit_Stack_Matrix | 720 | Exit-control stack combinations. |

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

## Flujo seguro

Cambie una sola matriz por etapa y conserve la evidencia.

1. Confirme que EX5, fuente, esquema y manifiesto son de la misma versión.
2. Cargue la biblioteca mediante Strategy Tester Inputs.
3. Mapee el símbolo y suffix exactos del bróker.
4. Navegue por clase y activo: cada activo trae los 11 tipos de sistema (01_SLTP a 11_SIGNAL_ONLY), un set por lado (BUY/SELL; BOTH en el grid unificado) y dos variantes de entrada — MULTI disputa los indicadores 0–10 en un solo eje, ICHIMOKU tiene archivo propio.
5. La fase 1 es descubrimiento de regiones: ejecute el genetico con el set tal cual — grupo de entrada completo (indicador, metodo, timeframe, applied price, periodos), salidas del sistema y llaves de filtro, todo a la vez.
6. De las rondas siguientes en adelante, bloquee (Y→N) los inputs de escritura — enums y booleanos — decididos por la fase anterior y deje abiertos solo los numericos; el ajuste de cada filtro solo entra si su llave sobrevivio encendida.
7. El filtro ATR de entrada (EntradaATR) existe solo en los sistemas de grid; en los demas permanece apagado por diseño.
8. Valide al ganador en ticks reales: deciden la divergencia contra OHLC y la retencion out-of-sample, nunca la ganancia in-sample.
9. Tras el tick real, cambie el dimensionamiento a Percentage y ejecute de nuevo: solo promueva si tambien pasa — y ese es el modo en que el set debe operar.

## Telemetría de ciclos del panel

El panel usa los mismos snapshots que el cálculo de lotes y el cierre de cestas.

- La actualización periódica por tick se limita a una vez por segundo; inicio y eventos de trading pueden refrescar inmediatamente.
- Balance y Equity son de toda la cuenta. El P&L cerrado es el cambio desde OnInit; P&L abierto y posiciones son el estado actual filtrado por Symbol + Magic.
- Martingale muestra por BUY/SELL pérdidas consecutivas, número e importe bruto de pérdidas, recuperado, déficit y objetivo = déficit × Multiplicador.
- Superar MaxMartingaleSteps hace hard reset: descarta el déficit y la siguiente orden usa lote base. Máximo una posición abierta por lado.
- D'Alembert muestra nivel actual y próximo lote normalizado para BUY/SELL.
- Grid muestra piernas/volumen, realizado con costes, P&L abierto, P&L del ciclo, objetivo congelado al inicio y restante.
- La ancla es la posición confirmada más reciente. BUY exige estrictamente anchor − ATR × DistanciaMinima por debajo; SELL estrictamente por encima; el progreso se expresa en ATR.
- Separate termina solo el ciclo del lado que queda flat; Unified termina cuando ambos lados quedan flat. Órdenes en tránsito retrasan el reset.
- El objetivo dispara la solicitud de cierre; comisión, tasas y slippage de salida pueden dejar el resultado final algo por debajo.
- InterfaceLanguage conserva 11 idiomas. Auto usa inglés en Tester y el idioma del terminal en vivo; etiquetas sin traducción usan inglés.

## Compatibilidad y restricciones

Son reglas conservadoras; el bróker puede imponer límites más estrictos.

- Percentage y Fixed-R requieren AtivarStop=true.
- Grid: solo Monetary/Fixed Lot, Recovery_None y cuenta hedging.
- Grid requiere take, DistanciaMinima positivo y límite de al menos dos posiciones.
- Mientras la cesta siga abierta, las pérdidas realizadas, swap, comisión y tasas del ciclo permanecen incluidos en el resultado necesario para alcanzar el objetivo; la ganancia aislada de una pierna no los borra.
- En Grid_SeparateProfit, BUY y SELL tienen ciclos independientes. Si desaparecen todas las posiciones de un lado, termina su ciclo; una entrada posterior inicia otro sin arrastrar el déficit cerrado.
- D'Alembert: Fixed Lot, Grid_Disabled y DAlembertStep>0.
- Martingale respeta MaxMartingaleSteps y MaxMartingaleLot.
- OnOppositeOrder exige hedging, ambos lados y grid apagado.
- Backtest de noticias requiere CSV en Common\Files.
- El horario usa tiempo del servidor.
- Valide suffix y especificaciones con cada bróker.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Aviso de riesgo

Ninguna EA, set ni resultado histórico garantiza el futuro. Valide OOS y en demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
