# White Rabbit X — Руководство по WFO

Авторитетная справка, созданная из текущего исходника EA и манифеста set — EA 1.11 — 127 inputs — 3738 sets

**Внимание к дате.** При включённом WFO функция OnTester сравнивает реальное окончание теста с input_end_date и возвращает ноль, если тест закончился раньше (допуск 80 часов). Неверная дата обнуляет все проходы, и вся оптимизация выглядит сломанной. Укажите в input_end_date ту же конечную дату, что и в тестере стратегий.

## Область и источники истины

Исходник EA определяет inputs, значения и функции; манифест определяет каждый set, статус, путь и SHA-256. Старый Quantum-архив не является текущей документацией.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Сгенерированный материал. Имена параметров точно соответствуют EA.

## Walk-forward метод

Используйте хронологические IS, OOS и forward demo с реальными spread, commission, swap и slippage.

## Безопасный процесс

Меняйте только одну матрицу за этап и сохраняйте доказательства решения.

1. Сверьте версии EX5, исходника, schema set и манифеста.
2. Загрузите библиотеку через Strategy Tester Inputs.
3. Сопоставьте точный символ и suffix брокера.
4. Перемещайтесь по классам и активам: у каждого актива 11 типов систем (01_SLTP — 11_SIGNAL_ONLY), один сет на сторону (BUY/SELL; BOTH для единого грида) и два варианта входа — MULTI разыгрывает индикаторы 0–10 на одной оси, ICHIMOKU имеет отдельный файл.
5. Фаза 1 — поиск областей: запустите генетическую оптимизацию сета как есть — полная группа входа (индикатор, метод, таймфрейм, applied price, периоды), выходы системы и переключатели фильтров, всё сразу.
6. Со следующих раундов фиксируйте (Y→N) «письменные» входы — enum и bool, решённые предыдущей фазой, — оставляя открытыми только числовые; настройка фильтра включается лишь если его переключатель выжил включённым.
7. ATR-фильтр входа (EntradaATR) существует только в грид-системах; в остальных он отключён по построению.
8. Проверяйте победителя на реальных тиках: решают расхождение с OHLC и out-of-sample-ретенция, а не прибыль in-sample.
9. После реальных тиков переключите расчёт лота на Percentage и прогоните снова: продвигайте только если пройдено и это — именно в этом режиме сет должен торговать.

## Статус манифеста и решение

Исходный статус сохраняется и консервативно сопоставляется с USE, REOPTIMIZE, RESEARCH или HOLD.

| Система | Управление | Наборы |
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

> Этот раздел пока доступен только на английском языке.

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

Именно поэтому контур сохраняет одобренный сет только после повторного финального прогона в режиме Percentage: если результат не держится при сложном проценте, он не был готов — и валидированный сет сохраняется именно в этом режиме.

## Предупреждение о риске

EA, set и исторические результаты не гарантируют будущую доходность. Проверяйте OOS и demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
