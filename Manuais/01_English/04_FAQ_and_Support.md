# White Rabbit X — FAQ and Support

Authoritative reference generated from the current EA source and set manifest — EA 1.11 — 127 inputs — 3738 sets

## Scope and source of truth

The EA source defines the input schema, defaults, enumerations and current feature surface. The set manifest defines every preset, family, status, path and integrity hash. Older Quantum material is historical only and must not be used to operate the current release.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Generated material. Parameter identifiers remain exactly as declared by the EA.

## Cycle-dashboard telemetry

The panel uses the same state snapshots used by position sizing and basket closure.

- Periodic tick refresh is capped at once per second; initialization and trade events can request an immediate refresh.
- Balance and Equity cover the whole account. Closed P&L is the delta since OnInit, while open P&L and positions are current snapshots; these strategy metrics are filtered by Symbol + Magic.
- Martingale reports, independently for BUY and SELL, consecutive losses, cycle loss count and gross amount, recovered value, outstanding deficit and target equal to deficit × Multiplicador.
- Exceeding MaxMartingaleSteps performs a hard Martingale reset: the old deficit is discarded and the next order uses the base lot. Martingale permits at most one open position per side.
- D'Alembert reports the current level and normalized next lot for BUY and SELL.
- Grid reports legs and volume, realized result including costs, open P&L, total cycle P&L, the monetary target frozen at cycle start and the remaining amount.
- The Grid anchor is the most recent confirmed position. BUY triggers strictly below anchor − ATR × DistanciaMinima; SELL strictly above anchor + ATR × DistanciaMinima. Progress is adverse distance in ATR versus the threshold.
- In Separate mode, becoming flat ends only that side's cycle; in Unified mode, the cycle ends when both BUY and SELL are flat. In-flight managed orders delay the reset.
- The target triggers a close request. Actual exit commission, fees and slippage can leave the final result slightly below that target.
- InterfaceLanguage preserves 11 UI languages. Auto uses English in the Tester and the terminal language live; a label without a specific translation falls back to English.

## Operational answers

Most failures come from an incompatible sizing/recovery combination, missing stop, wrong account mode, unresolved symbol suffix, server-time mismatch, missing news CSV or broker execution limits.

- PositionSize_Percentage and PositionSize_FixedR require AtivarStop=true and a calculable stop.
- Grid supports only PositionSize_Monetary or PositionSize_FixedLot, Recovery_None and a real hedging account.
- Grid requires AtivarTake=true, DistanciaMinima>0 and an active side limit of zero or at least two positions.
- Grid_SeparateProfit manages each side; Grid_UnifiedProfit manages the aggregate cycle result.
- While a basket remains open, its realized losses, swap, commission and fees remain included in the result still required to reach the target; profit from one isolated leg does not erase those costs.
- In Grid_SeparateProfit, BUY and SELL have independent cycles. If every position on one side disappears, that side's cycle ends; a later entry starts a new cycle without carrying the closed deficit forward.
- Recovery_DAlembert is restricted to Fixed Lot, Grid_Disabled and DAlembertStep>0.
- Recovery_Martingale observes MaxMartingaleSteps and MaxMartingaleLot; zero means no additional cap.
- ReversalExit_OnOppositeOrder requires a hedging account, Hedging=true, both sides enabled and grid disabled.
- News backtests require NewsCSVFile under Common\Files; NewsMoedasManual takes precedence over auto-detection.
- Schedules use broker server time; overnight intervals and weekend controls require explicit tests.
- Revalidate symbol suffix, contract size, tick value, minimum volume and costs for every broker.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Community and downloads

Join the official Telegram channel: **https://t.me/MrRabbit_MT5**

- Ready-made sets per symbol and per system type (SL/TP, trailing, grid, martingale and others), organized to load straight into the Strategy Tester.
- Manuals in your language: Portuguese, English, Russian, Chinese, Spanish, Japanese, German, Korean, French, Italian and Turkish.
- Update notices for the EA and for the set libraries.
- Support and shared experience with other users.

> This is the only official channel. Do not buy sets or copies of the EA from third parties claiming to represent White Rabbit X: the EA is sold only on the MQL5 Market and the sets are distributed free of charge on the channel above.

## Risk warning

No EA, preset, indicator, optimization or historical result guarantees future performance. Validate symbol mapping, costs, execution, out-of-sample data and forward demo behavior before assuming financial risk.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
