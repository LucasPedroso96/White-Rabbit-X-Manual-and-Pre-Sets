# White Rabbit X — Technical Compatibility

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

## Signal engines and entry methods

The selected entry indicator supplies three universal events: reversal, signal/reference cross and baseline/reference cross. Combination methods whose names contain “And” require their events on the same closed bar; “All” accepts any of the three events. A position is dispatched at most once per side for the selected signal bar.

- EntryIndicator: MACD, EMA_Cross, Momentum, Stochastic, TRIX, RSI, CCI, WPR, DeMarker, MFI, OsMA, Ichimoku.
- EntryMethod: Reversal, SignalCross, ReferenceCross, ReversalAndSignalCross, ReversalAndReferenceCross, SignalAndReferenceCross, All.
- PositionSizeMode: Percentage, Monetary, FixedLot, FixedR.
- RecoveryMode: None, Martingale, DAlembert.
- GridMode: Disabled, SeparateProfit, UnifiedProfit.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Manifest statuses and release disposition

The exact manifest status is preserved. For a conservative release decision it is also mapped to USE, REOPTIMIZE, RESEARCH or HOLD. Only an explicit USE status is treated as ready for the defined environment.

| System | Management | Sets |
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

## Risk warning

No EA, preset, indicator, optimization or historical result guarantees future performance. Validate symbol mapping, costs, execution, out-of-sample data and forward demo behavior before assuming financial risk.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
