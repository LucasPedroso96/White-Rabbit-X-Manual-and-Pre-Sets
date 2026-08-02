# White Rabbit X — MQL5 Market Description

Authoritative reference generated from the current EA source and set manifest — EA 1.11 — 127 inputs — 3738 sets

## What the software does

White Rabbit X is a multi-indicator MT5 Expert Advisor for systematic research, controlled execution and WFO. It combines signal engines, optional filters, four sizing models, exit stacks, schedule controls, news blocking, a chart dashboard and a manifest-driven preset library.

Current schema: 127 inputs. Current manifest: 3738 sets.

- Twelve native engines: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA and Ichimoku.
- Seven trigger methods with explicit reversal, cross, AND and OR semantics.
- Independent MTF/MACD, moving-average, ADX, ATR-volatility and news filters.
- Percentage, Monetary, Fixed Lot or Fixed-R sizing plus account-level risk protection.
- Stop, ATR take, breakeven, trailing and reversal controls form the exit stack.
- Dashboard, deal labels, languages, weekly schedule and WFO complete the operating layer.

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

## Supported combinations and restrictions

These are conservative operating rules for the current architecture. A broker can impose stricter limits, and a successful backtest does not override an incompatible account mode.

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

## Community and downloads

Join the official Telegram channel: **https://t.me/MrRabbit_MT5**

Manuals and the full set library: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- Ready-made sets per symbol and per system type (SL/TP, trailing, grid, martingale and others), organized to load straight into the Strategy Tester.
- **Autobot**: the automation behind that library, published in the same repository — the actual code that generates, walk-forward-tests, Monte Carlo-gates and real-tick-confirms every set before it ships. Run it yourself against your own broker and symbols, or read it to see how a set earned its place.
- Manuals in your language: Portuguese, English, Russian, Chinese, Spanish, Japanese, German, Korean, French, Italian and Turkish.
- Update notices for the EA and for the set libraries.
- Support and shared experience with other users.

Companion product: **Historical Tool Manager** (MQL5 Market: https://www.mql5.com/pt/market/product/188711) imports deep tick and M1 history into MT5 as Custom Symbols — the data source the Autobot's real-tick confirmation stage depends on.

> This is the only official channel. Do not buy sets or copies of the EA from third parties claiming to represent White Rabbit X: the EA is sold only on the MQL5 Market and the sets are distributed free of charge on the channel above.

## Risk warning

No EA, preset, indicator, optimization or historical result guarantees future performance. Validate symbol mapping, costs, execution, out-of-sample data and forward demo behavior before assuming financial risk.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
