# White Rabbit X

Doce motores de entrada nativos. Once arquitecturas de salida. Un Expert Advisor.

La mayoría de los EA entregan una estrategia cerrada. Este entrega el taller: usted elige el motor de señal, el esqueleto de gestión y los filtros, y el walk-forward integrado le dice si el resultado sobrevive fuera de la muestra.

## Doce motores de entrada, todos nativos

MACD · EMA Cross · Momentum · Stochastic · TRIX · RSI · CCI · Williams %R · DeMarker · MFI · OsMA · Ichimoku

Todos son indicadores nativos de MetaTrader: nada que instalar y nada que se rompa en la próxima actualización del terminal.

Ichimoku lee los cinco búferes: el disparador de referencia es la ruptura de la nube (Kumo), no un cruce Tenkan/Kijun, y el Chikou queda disponible como filtro de confirmación. El Estocástico expone el suavizado, el método de media y el campo de precio Low/High o Close/Close, los tres parámetros que la mayoría de los EA deja fijos en el código.

Tres tipos de disparador se combinan en siete métodos de entrada.

## Once arquitecturas de salida

SL/TP · objetivo orgánico · solo trailing · SL/TP con trailing · breakeven y trailing · salida por reversión · grid separado · grid unificado · martingala · D'Alembert · solo señal.

El esqueleto de gestión es una elección suya, no una parte fija de la estrategia.

## Walk-forward dentro del EA

No es la pestaña Forward del probador. El EA divide el período en ventanas in-sample y out-of-sample y, en modo de optimización, opera solo el in-sample: el algoritmo genético nunca ve los datos con los que será juzgado.

Tres modos de ventana: secuencial, deslizante (el clásico, unas tres veces más ciclos con el mismo histórico) y anclado.

El informe da la Walk Forward Efficiency por ciclo, con media y desviación estándar. Un EA que devuelve 70% en cada ciclo y otro que devuelve 200% en uno y −20% en el resto comparten la misma media; solo el primero es robusto, y la dispersión los distingue.

## Riesgo medido en R

Fixed-R dimensiona cada posición para arriesgar exactamente 1R, calculado sobre un capital base fijo y no sobre el saldo corriente. Los resultados se vuelven comparables entre símbolos, cuentas y pruebas: +40R en oro y +40R en EURUSD significan lo mismo, mientras que «+3.200 USD» no significa nada sin conocer el lote y el saldo.

Quince criterios de optimización, incluido un puntaje compuesto que devuelve cero por debajo de treinta operaciones, lo que por sí solo descarta al clásico «ganador» construido sobre tres operaciones afortunadas.

## Protección que actúa antes de la orden

Pérdida diaria máxima, techo de drawdown sobre el patrimonio, margen libre mínimo, límite de spread, ventanas de sesión y días de la semana, y filtro de noticias con caché CSV para backtest. Las distancias de freeze level y stops level se verifican antes de cada solicitud, así el registro se mantiene legible en lugar de llenarse de rechazos del bróker.

## Panel en el gráfico

Estrategia, indicador y parámetros activos, capital de la cuenta y del EA, P&L cerrado, flotante y neto, posiciones abiertas y —con martingala, D'Alembert o grid— el ciclo en vivo: pérdidas consecutivas, déficit pendiente, importe recuperado, objetivo, órdenes, ancla y espaciado de ATR.

Interfaz en once idiomas.

## Qué incluye

- Expert Advisor para MetaTrader 5, con 136 parámetros documentados
- 3.738 archivos .set listos: 89 activos × 11 sistemas × ambos sentidos
- Instalador automático que encuentra su terminal, copia los sets y los adapta al sufijo de símbolo y al lote mínimo de su bróker
- Manual, guía de WFO, referencia de parámetros, tutorial de sets y FAQ en once idiomas
- Soporte y actualizaciones por el canal oficial

## Antes de comprar

Esto es un marco de investigación, no una señal para encender y olvidar. Cada set es una hipótesis: exige optimización, validación fuera de muestra y forward-demo antes de dinero real.

Grid, martingala y D'Alembert cambian la naturaleza de la curva de riesgo. El grid exige una cuenta de cobertura real.

Ningún EA, preset ni resultado histórico garantiza rendimiento futuro.

---

Canal oficial: https://t.me/MrRabbit_MT5 — biblioteca de sets gratuita, manuales en su idioma y avisos de actualización. El EA se vende únicamente aquí en el MQL5 Market; los sets se distribuyen gratis en ese canal y en ningún otro lugar.
