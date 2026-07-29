# White Rabbit X — Техническая совместимость

Авторитетная справка, созданная из текущего исходника EA и манифеста set — EA 1.11 — 127 inputs — 3738 sets

## Область и источники истины

Исходник EA определяет inputs, значения и функции; манифест определяет каждый set, статус, путь и SHA-256. Старый Quantum-архив не является текущей документацией.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Сгенерированный материал. Имена параметров точно соответствуют EA.

## Телеметрия циклов на панели

Панель использует те же снимки состояния, что расчёт лота и закрытие корзины.

- Периодическое обновление по тику ограничено одним разом в секунду; запуск и торговые события могут обновить панель сразу.
- Balance и Equity относятся ко всему счёту. Закрытый P&L — изменение с OnInit; открытый P&L и позиции — текущее состояние, отфильтрованное по Symbol + Magic.
- Martingale отдельно для BUY/SELL показывает последовательные убытки, число и сумму убытков цикла, recovered, deficit и target = deficit × Multiplicador.
- При превышении MaxMartingaleSteps выполняется hard reset: старый дефицит удаляется, следующая сделка использует базовый лот. Разрешена максимум одна открытая позиция на сторону.
- D'Alembert показывает текущий уровень и следующий нормализованный лот BUY/SELL.
- Grid показывает legs/volume, realized с затратами, open P&L, cycle P&L, замороженную при старте цель и remaining.
- Anchor — последняя подтверждённая позиция. BUY требует строго меньше anchor − ATR × DistanciaMinima, SELL — строго больше anchor + ATR × DistanciaMinima; прогресс выражен в ATR.
- Separate завершает цикл только ставшей flat стороны; Unified — когда flat обе стороны. Активная заявка задерживает reset.
- Target запускает закрытие; фактические commission, fee и slippage выхода могут оставить итог немного ниже цели.
- InterfaceLanguage сохраняет 11 языков. Auto использует English в Tester и язык терминала live; отсутствующий перевод label заменяется English.

## Совместимость и ограничения

Правила консервативны; брокер может применять более строгие ограничения.

- Percentage и Fixed-R требуют AtivarStop=true.
- Grid: только Monetary/Fixed Lot, Recovery_None и hedging account.
- Grid требует take, положительный DistanciaMinima и минимум две позиции активной стороны.
- Пока корзина открыта, реализованные убытки, swap, commission и fees цикла остаются в результате, необходимом для достижения цели; прибыль одной позиции их не обнуляет.
- В Grid_SeparateProfit циклы BUY и SELL независимы. Если все позиции одной стороны исчезли, её цикл завершён; следующий вход начинает новый цикл без переноса закрытого дефицита.
- D'Alembert: Fixed Lot, Grid_Disabled и DAlembertStep>0.
- Martingale ограничивается MaxMartingaleSteps и MaxMartingaleLot.
- OnOppositeOrder требует hedging, обе стороны и отключённый grid.
- News backtest требует CSV в Common\Files.
- Расписание использует серверное время брокера.
- Проверяйте suffix и спецификацию символа.

## Сигналы и методы входа

Шесть движков используют разворот, пересечение signal/reference и baseline/reference. Методы And требуют событий на одной закрытой свече; All означает любое событие.

- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

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

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Предупреждение о риске

EA, set и исторические результаты не гарантируют будущую доходность. Проверяйте OOS и demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
