# White Rabbit X — Preguntas y soporte

Referencia autoritativa generada desde la fuente actual y el manifiesto de sets — EA 1.11 — 127 inputs — 3738 sets

## Alcance y fuentes de verdad

La fuente define inputs, valores y funciones; el manifiesto define cada set, estado, ruta y SHA-256. El archivo Quantum antiguo es solo histórico.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Material generado; los identificadores coinciden exactamente con la EA.

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

## Respuestas operativas

Revise stop, modo de cuenta, suffix, hora del servidor, CSV de noticias y límites del bróker.

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

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Comunidad y descargas

Únase al canal oficial de Telegram: **https://t.me/MrRabbit_MT5**

- Sets listos por activo y por tipo de sistema (SL/TP, trailing, grid, martingala y otros), organizados para cargar directamente en el Probador de Estrategias.
- Manuales en su idioma: portugués, inglés, ruso, chino, español, japonés, alemán, coreano, francés, italiano y turco.
- Avisos de actualización del EA y de las bibliotecas de sets.
- Soporte e intercambio de experiencia con otros usuarios.

> Este es el único canal oficial. No compre sets ni copias del EA a terceros que digan representar a White Rabbit X: el EA se vende únicamente en el MQL5 Market y los sets se distribuyen gratuitamente en el canal indicado.

## Aviso de riesgo

Ninguna EA, set ni resultado histórico garantiza el futuro. Valide OOS y en demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
