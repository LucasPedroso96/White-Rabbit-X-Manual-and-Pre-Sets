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
4. Начните с baseline 01–05 и тестируйте BUY/SELL отдельно.
5. Папка 06 — одноосевое исследование.
6. Папка 07 — система входа, 08 — фильтры, 09 — риск, 10 — выход.
7. Проводите хронологические IS, OOS и forward-demo тесты.
8. Проверяйте Status, RelativePath и SHA256.
9. Только явный USE означает готовность для указанной среды.

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

## Предупреждение о риске

EA, set и исторические результаты не гарантируют будущую доходность. Проверяйте OOS и demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
