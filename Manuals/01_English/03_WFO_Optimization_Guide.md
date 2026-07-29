# White Rabbit X — WFO Optimization Guide

Authoritative reference generated from the current EA source and set manifest — EA 1.11 — 127 inputs — 3738 sets

**Mind the date.** With WFO enabled, OnTester compares the real end of the test against input_end_date and returns zero if the test ended earlier (80-hour tolerance). A wrong date zeroes every pass and the whole optimization looks broken. Set input_end_date to the same end date configured in the Strategy Tester.

## Scope and source of truth

The EA source defines the input schema, defaults, enumerations and current feature surface. The set manifest defines every preset, family, status, path and integrity hash. Older Quantum material is historical only and must not be used to operate the current release.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Generated material. Parameter identifiers remain exactly as declared by the EA.

## Walk-forward method

Use chronological in-sample, out-of-sample and forward-demo segments. Keep spreads, commissions, swaps and slippage realistic. Reject unstable parameter islands and any result that depends on one trade, one market regime or a broker-specific artifact. With a Custom step, a positive wfo_customStepSizePercent is a percentage of the in-sample window; a negative value such as -61 means a fixed 61-day out-of-sample step.

## Safe workflow

Change one matrix at a time and retain complete evidence for each promotion decision.

1. Confirm that the EX5, audited source, set schema and manifest belong to the same release.
2. Copy the library to MQL5\Profiles\Tester or select it when loading Strategy Tester Inputs.
3. Map each asset to the broker's exact symbol, suffix, session, profit currency and contract size.
4. Start with folders 01–05: load the asset baseline and test BUY and SELL separately.
5. Use folder 06 for controlled one-axis research; do not mix changes before measuring their effect.
6. Use folder 07 to compare indicator, entry method and management archetype.
7. Use folder 08 for filter stacks and verify that the statistical sample remains adequate.
8. Use folder 09 to compare risk engines only in documented compatible combinations.
9. Use folder 10 to test exit stacks while keeping the entry system frozen.
10. Run chronological in-sample, out-of-sample and forward-demo phases with realistic costs.
11. For news tests, generate WhiteRabbit_News.csv for the full date range and every required currency.
12. Run WhiteRabbit Filters SelfTest and proceed only when its final line reports zero failures.
13. Check Status, RelativePath and SHA256 in the manifest before promoting a result.
14. USE is explicit authorization for a defined environment; REOPTIMIZE, RESEARCH and HOLD are not live presets.

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

## Risk warning

No EA, preset, indicator, optimization or historical result guarantees future performance. Validate symbol mapping, costs, execution, out-of-sample data and forward demo behavior before assuming financial risk.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
