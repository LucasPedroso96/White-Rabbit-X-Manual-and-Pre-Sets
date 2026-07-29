# White Rabbit X — FAQ и поддержка

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

## Операционные ответы

Проверьте stop, режим счёта, suffix, время сервера, CSV новостей и лимиты брокера.

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

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Сообщество и загрузки

Присоединяйтесь к официальному каналу в Telegram: **https://t.me/MrRabbit_MT5**

Руководства и полная библиотека наборов: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- Готовые наборы параметров по инструментам и типам систем (SL/TP, трейлинг, сетка, мартингейл и другие), готовые к загрузке в тестер стратегий.
- Руководства на вашем языке: португальский, английский, русский, китайский, испанский, японский, немецкий, корейский, французский, итальянский и турецкий.
- Уведомления об обновлениях советника и библиотек наборов.
- Поддержка и обмен опытом с другими пользователями.

> Это единственный официальный канал. Не покупайте наборы или копии советника у третьих лиц, утверждающих, что они представляют White Rabbit X: советник продаётся только на MQL5 Market, а наборы бесплатно распространяются на канале выше.

## Предупреждение о риске

EA, set и исторические результаты не гарантируют будущую доходность. Проверяйте OOS и demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
