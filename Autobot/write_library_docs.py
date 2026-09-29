# -*- coding: utf-8 -*-
"""Writes the README that ships with the set library.

English, because the library is public and its readers are not only Brazilian.
The per-language manuals cover the product; this file covers the LIBRARY: what
each system is, what is being optimized, and how to run it without fooling
yourself.

Everything prescriptive here was measured on this EA, not assumed. Where a
number appears, it came from a run.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import wrx_paths

ROOT = (wrx_paths.data_dir() / "MQL5" / "Profiles" / "Tester"
        / "White_Rabbit_X_Sets_templates")

EXTRA = """
## Out-of-sample validation, and what it is not

**This is not walk-forward, and the distinction matters.** A real walk-forward
re-optimizes at every window: the parameters tested on period N+1 come from an
optimization run only on period N, and the final curve concatenates the
out-of-sample segments, each from a different optimization. That needs N
separate tester passes.

The MetaTrader tester runs one continuous pass and cannot go back in time. So
what the EA does inside a single run is one parameter set evaluated over
interleaved In-Sample and Out-of-Sample segments — an **interleaved holdout**.
It is genuinely useful (alternating segments sample more regimes than one
contiguous split) but it does not answer walk-forward's actual question, which
is how long a set of parameters stays valid before it needs refitting.

**It only means something if the optimization ran in In-Sample mode.** With
`MetodoDeEntradawfo = 0` the EA closes positions and does not trade outside the
IS windows, so the genetic algorithm never profits from out-of-sample data.
Optimize with `AtivarWFO` off and the algorithm has already seen the whole
period — the retention number that follows proves nothing.

Real walk-forward here means driving several tester passes from outside, which
is what `wfo_matrix.py` does.

## How the internal windows work

Enable `AtivarWFO` and the period is sliced into In-Sample and Out-of-Sample
windows.

  `MetodoDeEntradawfo = 0` (In-Sample) trades ONLY the in-sample windows. This
  is the optimization mode: the genetic algorithm never sees the data it will
  be judged on.

  `MetodoDeEntradawfo = 1` (In-Sample + Out-of-Sample) trades the whole period
  and reports the efficiency. This is the validation mode.

The windows advance side by side and reuse no day. That is a requirement, not a
preference: the walk-forward runs inside a single tester pass, with one
parameter set and one timeline, so every bar needs exactly one label. Sliding
windows overlap by construction — one cycle's out-of-sample falls inside the
next cycle's in-sample — and inflate the number.

**`input_end_date` must match the tester's To date**, within 80 hours. If it
does not, `OnTester` returns 0 for every pass and a perfectly good optimization
looks like a total failure.

The report, printed at the end of the run:

```
Walk Forward Efficiency (WFE): 68.40%
  Cycle 1: IS 120.50 | OOS 88.20 | WFE 73.2%
  Cycle 2: IS 96.10  | OOS 61.40 | WFE 63.9%
WFE per cycle: mean 68.6% | stdev 4.7% | 2 of 2 cycles profitable out-of-sample
```

WFE is average daily out-of-sample profit divided by average daily in-sample
profit. Below 50% the system is over-fitted to the in-sample; above 100% is
usually window luck rather than superiority. The healthy band sits between 50%
and 100%.

**Read the dispersion, not just the mean.** A system returning 70% in every
cycle and one returning 200% in a single cycle and -20% elsewhere can share the
same average, and only the first is robust. The line also reports how many
cycles were profitable out of sample, which is the most honest number in the
block.

When the in-sample itself was not profitable, the report says WFE is *not
applicable* instead of printing a percentage. There is nothing to carry over
from a strategy that already failed on the data it was fitted to, and the ratio
would invert its sign and mislead in both directions.
"""

with (ROOT / "MANIFESTO_SISTEMAS.csv").open(encoding="utf-8-sig") as fh:
    rows = list(csv.DictReader(fh, delimiter=";"))

by_system: dict[str, list[int]] = {}
for row in rows:
    by_system.setdefault(row["System"], []).append(int(row["Combinations"]))
status = Counter(row["Status"] for row in rows)

lines = [
    "# White Rabbit X - Optimization sets, organized BY SYSTEM",
    "",
    f"**{len(rows)} sets** = 89 symbols x {len(by_system)} systems x 2 indicator "
    "variants x the sides each system has.",
    "",
    "Every file is a complete trading system, optimizable end to end: entry",
    "indicator, trigger method, timeframe, periods, ATR, filters and that",
    "system's exit geometry are ALL marked `Y` in the same file. There is no",
    "mandatory staging — you run it, you learn something, and you turn off by",
    "hand (`Y` -> `N`) what you have already settled before the next round.",
    "",
    "## Layout",
    "",
    "```text",
    "<class>/<SYMBOL>/<NN_SYSTEM>/<SIDE>_<VARIANT>.set",
    "01_Forex/USDJPY/01_SLTP/BUY_MULTI.set",
    "01_Forex/USDJPY/01_SLTP/BUY_ICHIMOKU.set",
    "01_Forex/USDJPY/07_GRID_SEPARATE/BUY_MULTI.set",
    "01_Forex/USDJPY/13_OCO_ROMPIMENTO/BOTH_MULTI.set",
    "```",
    "",
    "- **SIDE**: `BUY`, `SELL` or `BOTH`. `BOTH` is one file that trades the two",
    "  directions (with `Hedging=true` it needs a hedging account). "
    "`13_OCO_ROMPIMENTO`",
    "  ships ONLY `BOTH_MULTI`: it arms a buy stop and a sell stop, so it needs",
    "  both directions and no indicator. (`08_GRID_UNIFIED` was retired",
    "  2026-08-16: once take-profit and next-lot sizing went per-side it stopped",
    "  being different from `07_GRID_SEPARATE`.)",
    "- **MULTI**: `EntryIndicator` is an axis across 11 engines (MACD, EMA,",
    "  Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA).",
    "- **ICHIMOKU**: indicator fixed to Ichimoku (value 11), because it requires",
    "  Tenkan < Kijun < SenkouB and does not fit the other engines' period ranges.",
    "",
    f"## The {len(by_system)} systems",
    "",
    "| System | Management skeleton | Own exit axes | Typical space |",
    "|---|---|---|---:|",
]

DESC = {
    "01_SLTP": ("SL + TP as ATR multiples",
                "Stop, Take, Breakeven on/off, BE distance"),
    "02_SLTP_ORGANIC": ("SL + organic TP (anchored to the last trade)",
                        "Stop, Take, Breakeven on/off, BE distance"),
    "03_TRAIL_ONLY": ("SL + trailing, no TP: lets it run",
                      "Stop, trailing source, Trail, BE"),
    "04_SLTP_TRAIL": ("SL + TP with trailing behind",
                      "Stop, Take, Trail, BE"),
    "05_BE_TRAIL": ("Mandatory breakeven + trailing, no TP",
                    "Stop, BE distance, trailing source, Trail"),
    "06_REVERSAL_EXIT": ("Closes on the indicator's opposite signal",
                         "Stop, trailing on/off, Trail, BE, exit filters"),
    "07_GRID_SEPARATE": ("Grid, one target per side",
                         "Take, Multiplier, MinimumDistance, number of legs"),
    "09_MARTINGALE": ("Lot grows after a loss, 1 position per side",
                      "Stop, Take, Multiplier, maximum steps, BE"),
    "10_DALEMBERT": ("Lot grows in arithmetic steps after a loss",
                     "Stop, Take, lot step, maximum steps, BE"),
    "11_SIGNAL_ONLY": ("No SL and no TP: measures the raw signal",
                       "entry and filters only (negative coverage)"),
    "12_GRID_INVERSO": ("Grid pyramid: opens levels WITH the price, exits by "
                        "ATR trailing on the basket",
                        "Stop, Trail, Multiplier, MinimumDistance, number of legs"),
    "13_OCO_ROMPIMENTO": ("OCO bracket armed once a day at a fixed session "
                         "hour: buy stop above + sell stop below the recent "
                         "range, one leg cancels the other on fill",
                         "session hour, range length, bracket distance, "
                         "expiration, SL/TP/Trail/BE (04's exit)"),
}

for code in sorted(by_system):
    skeleton, axes = DESC[code]
    typical = max(by_system[code])
    lines.append(f"| `{code}` | {skeleton} | {axes} | {typical:.2e} |")

lines += [
    "",
    "Systems **01 to 06, 12 and 13 use Fixed-R**: the lot is derived from the risk",
    "budget, so the same file adapts itself to any account size. Systems **07 and",
    "11 use a fixed lot** — their risk is whatever the minimum lot costs on that",
    "instrument, independent of your balance (07 has no stop by design: the",
    "basket is the management; 11 has neither SL nor TP). Start with the Fixed-R",
    "ones.",
    "",
    "## Systems and boosters",
    "",
    "A **system** is how a position is managed after the entry: stop, target,",
    "trailing, grid, session bracket. It is validated on its own. A **booster** is",
    "an OPTIONAL layer that sits on top of a system that already has an edge, and it",
    "never creates an edge by itself. In the Autobot circuit the pending entry and",
    "the execution filters are adopted only when they raise the out-of-sample",
    "retention by at least 5 points; the recovery layer is applied when you ask for",
    "it and the final gates (survival, drawdown, sealed holdout) judge the whole",
    "result. The entry engine (MULTI, Ichimoku, Bollinger, Candles) is a third,",
    "independent choice.",
    "",
    "| Booster | Inputs | Works on | What it does |",
    "|---|---|---|---|",
    "| Recovery | `RecoveryMode` 1 Martingale / 2 D'Alembert, `MaxMartingaleSteps`, "
    "`DAlembertStep`, `Multiplicador` | 01-06 and 11 (the EA refuses it with a "
    "grid) | Martingale sizes the next lot to win back the accumulated loss "
    "(Fixed-R: capped at `MaxRiscoTradeR` = 3R of risk; fixed lot: last lot x "
    "`Multiplicador`). D'Alembert adds a fixed lot step per loss and REQUIRES "
    "Fixed Lot. `MaxMartingaleSteps` consecutive losses reset to the base lot. |",
    "| Pending entry | `EntryOrderType` 1 Stop / 2 Limit / 3 OCO, "
    "`PendingReferencia` (close or extreme of the signal candle), "
    "`PendingDistanciaATR`, `PendingExpiracaoBarras` | every system (only the "
    "SEED entry of a grid/pyramid) | Instead of entering at market, places a "
    "pending order k x ATR from the reference; SL/TP are relative to the ORDER "
    "price; it expires after N bars or when the opposite signal arrives. OCO "
    "places a buy stop and a sell stop and one fill cancels the other. |",
    "| Execution filters | `TOD_From_Hour`, `TOD_To_Hour`, `Trade<Weekday>`, "
    "`MaxSpread` | every system | Hours, weekdays and spread ceiling. |",
    "| Volatility filter | `EntradaATR`, `VolatilityFilter` (high / low), "
    "`PeriodoBaselineATR`, `MultiplicadorATR` | every system | Trades only when the "
    "current ATR is above (high) or below (low) its own baseline by the "
    "multiplier. |",
    "| Secondary filters | `AtivarFiltroMA`, `AtivarFiltroADX`, `AtivarFiltroMTF` "
    "| every system | Trend/strength/multi-timeframe confirmation. |",
    "",
    "`09_MARTINGALE` and `10_DALEMBERT` were systems once; since 2026-09-08 they are",
    "the Recovery booster. What the EA accepts together:",
    "",
    "| Combination | Accepted? |",
    "|---|---|",
    "| Fixed-R + Martingale | yes (loss recovery capped at 3R) |",
    "| Fixed-R + D'Alembert | NO — an absolute lot step breaks the balance-independence of R |",
    "| D'Alembert | needs Fixed Lot, no grid, `DAlembertStep` > 0 |",
    "| Grid (07) or pyramid (12) + recovery | NO |",
    "| Fixed-R + classic grid (07) | NO (no stop to measure R against) |",
    "| Percentage sizing | needs a stop loss |",
    "| Grid / `Hedging=true` | needs a hedging account |",
    "| OCO / Pending entry | works on netting too (two legs firing together net out) |",
    "",
    "## Shared core (present in every system)",
    "",
    "| Axis | Start | Step | Stop |",
    "|---|---:|---:|---:|",
    "| `EntryIndicator` (MULTI) | 0 MACD | 1 | 10 OsMA |",
    "| `EntryMethod` | 0 reversal | 1 | 6 any trigger |",
    "| `TimeFrame` | 3 values, per asset class | 1 | |",
    "| `Fast_EMA` | 6 | 3 | 18 |",
    "| `Slow_EMA` | 21 | 6 | 45 |",
    "| `MACD_SMA` | 3 | 3 | 15 |",
    "| `PeriodoATR` | 7 | 7 | 28 |",
    "| `AtivarFiltroMTF` / `AtivarFiltroMA` / `AtivarFiltroADX` / `EntradaATR` | false | | true |",
    "| `StochasticPriceField` (MULTI) | 0 Low/High | 1 | 1 Close/Close |",
    "| `IchimokuUseKumo` / `IchimokuChikouFilter` (ICHIMOKU) | false | | true |",
    "| `MA_Period` | 100 | 100 | 300 |",
    "| `MetodoMA` | 0 | 1 | 3 |",
    "| `ADX_Limiar` | 15 | 5 | 30 |",
    "",
    "`Fast_EMA` stops at 18 and `Slow_EMA` starts at 21 on purpose: the EA",
    "requires fast < slow and rejects the whole pass with",
    "`incorrect input parameters` if the order breaks. The same constraint is why",
    "Ichimoku gets its own file.",
    "",
    "## Modeling mode: use real ticks",
    "",
    "In the Strategy Tester's **Settings** tab, **Modeling** field:",
    "",
    "```text",
    "Every tick based on real ticks   <- use this",
    "OHLC 1 minute                    <- only 01_SLTP and 02_SLTP_ORGANIC",
    "```",
    "",
    "This is not a style preference. Measuring the same set in both modes over 3",
    "years on the same symbol, the OHLC mode understated the loss by **3.3x on",
    "trailing systems and 23x on grid** — always in the optimistic direction.",
    "Only fixed SL/TP stayed within 3%.",
    "",
    "The cause is structural: trailing and grid depend on **when** price touched",
    "each level inside the bar. OHLC mode interpolates that from four prices per",
    "minute and smooths away exactly the adverse excursions that would have taken",
    "the position out. Optimizing a trailing system on interpolated bars selects",
    "parameters that survived a price path which never happened.",
    "",
    "Real ticks cost roughly 20x more time per pass. Budget for it: it is the",
    "difference between a result and a number.",
    "",
    "## The optimization circuit",
    "",
    "These files ship configured for **phase 1**. The library is not a set of",
    "finished presets; it is the first step of a repeatable circuit, and each",
    "phase narrows what the next one has to search.",
    "",
    "| Phase | What you decide | Model | Criterion | What is open |",
    "|---|---|---|---|---|",
    "| **1 (shipped)** | signal and exit geometry | OHLC | Pessimistic Average Profit | indicator, method, timeframe, periods, ATR, stop, target, breakeven |",
    "| 2 | filters | OHLC | Drawdown-Adjusted Profit per Trade | MTF, moving average, ADX — ranges already calibrated, flip `N` to `Y` |",
    "| 3 | session | OHLC | Return Uniformity | spread ceiling, hours, weekdays |",
    "| 4 | confirmation | **real ticks** | — | nothing new — re-run the winner and compare |",
    "",
    "**The criterion changes with the phase, and using one criterion throughout",
    "actively works against you.** A filter REDUCES the number of trades, so",
    "optimizing phase 2 on total profit punishes the very filter that cuts bad",
    "entries, even when it improves the quality of every remaining one. Phase 2",
    "asks about quality *per trade*; phase 3 asks whether returns became more",
    "even, which is exactly what a session filter is for.",
    "",
    "Phase 1 uses Pessimistic Average Profit because it answers the only question",
    "that phase has: does this signal have an edge, or did the gains come from a",
    "handful of lucky trades? It discounts reliance on outlier wins, so",
    "concentrated luck does not climb the ranking.",
    "",
    "`configure_wfo.py --fase 1|2|3` switches criterion and walk-forward mode",
    "together, and writes the end date — which the next section explains you",
    "cannot afford to get wrong.",
    "",
    "A note on the shipped Levain Composite score: it works as a quality **gate**",
    "but poorly as a **ranking** criterion. Its four components are capped and the",
    "weights sum to 1, so every pass that meets the benchmarks returns exactly",
    "1.0 — the genetic algorithm loses its gradient precisely where the champion",
    "is chosen. Measured: six passes tied at 1.0, with profit-42 passes ranking",
    "below profit-23 ones.",
    "",
    "Phase 1 ships with the filters **off on purpose**. A filter means nothing",
    "until the signal is settled, and leaving them open costs real money in time:",
    "the six filter axes multiply the phase-1 space by **384x** (398 billion",
    "against 1.04 billion without them) while contributing no information. In one",
    "measured run, 818 of 3,435 distinct results came back duplicated because the",
    "genetic algorithm was varying parameters sitting behind a disabled switch —",
    "each duplicate a full backtest spent on nothing.",
    "",
    "Their ranges are already written in the file, flagged `N`. Phase 2 is just",
    "flipping those to `Y`; you do not have to invent the range.",
    "",
    "**Between phases, lock what you found**: put the winning value in all four",
    "fields and set the flag to `N`. Each lock collapses the space by orders of",
    "magnitude, which is what makes the next phase sharper rather than longer.",
    "",
    "**Order matters more than most people expect.** Lock the switches before the",
    "geometry: `EntryIndicator` alone decides whether four other parameters mean",
    "anything at all.",
    "",
    "### About phase 4",
    "",
    "For fixed SL/TP the real-tick pass is a confirmation: measured across three",
    "years, OHLC and real ticks differed by 1.2%. For **trailing and grid it is",
    "not** — there the divergence was 3.3x and 23x, always optimistic, so real",
    "ticks belong BEFORE you tune the exit geometry, not after. Signals are",
    "evaluated at bar close and are unaffected either way; only the management is.",
    "",
    "## How to run",
    "",
    "1. Strategy Tester -> `White Rabbit X (Global Multi-Indicator).ex5`. Pick the",
    "   broker's real symbol (mind the suffix) and the history range.",
    "2. **Settings -> Modeling -> Every tick based on real ticks.**",
    "3. Inputs tab -> **Load** -> the `.set` for the symbol/system/side you want.",
    "4. Optimization: **Fast genetic based algorithm**. Above 100 million",
    "   combinations MT5 switches to genetic on its own.",
    "5. Run it. Re-launching the genetic algorithm continues the same search and",
    "   refines the result.",
    "6. **Lock what you found**: flip that parameter's `Y` to `N` and put the",
    "   winning value in all four fields. The search space collapses by orders of",
    "   magnitude and the next round is far sharper.",
    "7. Repeat until only the exit geometry is left; Complete Search becomes",
    "   viable at that point.",
    "",
    "### Lock the switches before the geometry",
    "",
    "Locking order matters more than most people expect: entry indicator and",
    "method -> timeframe -> periods -> filter stack -> exit geometry.",
    "",
    "The reason is measurable. Several parameters are **conditionally inert** —",
    "they mean nothing while their switch is off. `MetodoMA` only matters with",
    "`AtivarFiltroMA=true`; `ADX_Limiar` only with the ADX filter on;",
    "`StochasticPriceField` only when the engine is Stochastic. In one measured",
    "run, 818 of 3,435 distinct results came back duplicated because the genetic",
    "algorithm was varying parameters sitting behind a disabled switch — each one",
    "a full backtest spent on nothing.",
    "",
    "So the most valuable parameter to fix first is not the one that moves the",
    "result the most. It is the **switch** that decides whether the others mean",
    "anything at all.",
    "",
    "### Reading the winner",
    "",
    "The composite score caps each component at 1.0, which means it stops",
    "discriminating at the top: passes that exceed the caps all tie at 1.0 while",
    "genuinely better passes can rank below them. Break ties by profit and by a",
    "real Profit Factor.",
    "",
    "Treat `Profit Factor = 0` with suspicion rather than enthusiasm — MT5 reports",
    "it when gross loss is zero, so it means *no losing trade in the sample*, not",
    "excellence. Combined with a stop several times wider than the target, that is",
    "the classic shape of winning small often and losing big once, where the risk",
    "simply has not materialized yet.",
    "",
    "### Fixed-R for research, percentage for live",
    "",
    "Optimize in **Fixed-R**: with the base capital frozen, passes stay comparable",
    "to each other and across symbols. +40R on gold and +40R on EURUSD mean the",
    "same thing, while \"+3,200 USD\" means nothing without the lot and the balance.",
    "",
    "Live, **percentage of balance** usually makes more sense: it tracks the",
    "account, compounds as it grows and cuts exposure as it shrinks — protection",
    "Fixed-R cannot give, because it deliberately ignores the running balance.",
    "Both modes report in R, so the record stays readable after the switch.",
    "",
    "## Warnings by status",
    "",
]
for name, count in sorted(status.items()):
    lines.append(f"- `{name}`: {count} sets")
lines += [
    "",
    "- **HEDGE_ACCOUNT_REQUIRED** (grid): requires a real MT5 hedging account.",
    "  Netting cannot represent independent legs and the legs cancel out.",
    "- **Recovery booster** (Martingale, D'Alembert): the risk curve changes",
    "  nature — the lot grows with the losing streak. Keep `MaxMartingaleSteps`",
    "  and a lot cap your broker accepts before any forward-demo.",
    "- **HIGH_RISK_RESEARCH** (signal only): no stop loss. It exists to measure",
    "  the raw signal, never to trade.",
    "",
    "None of these files is a production preset. After validating out of sample,",
    "copy the winners into a new file with every flag set to `N` and its own",
    "MagicNumber.",
    "",
    "## Tooling",
    "",
    "- Generator: `generate_system_sets.py`",
    "- Validator: `validate_system_sets.py`",
    "",
    "The validator reimplements the EA's `OnInit` rules and tests the extremes of",
    "every axis across all files: if any `.set` could produce",
    "`INIT_PARAMETERS_INCORRECT`, it fails before you find out in the tester.",
    "",
    "Full manifest (symbol, system, combinations, magic, SHA-256):",
    "`MANIFESTO_SISTEMAS.csv`.",
]

body = "\r\n".join(lines) + EXTRA.replace("\n", "\r\n")
(ROOT / "README.md").write_text(body + "\r\n", encoding="utf-8-sig")
print(f"README written: {ROOT / 'README.md'}")
for code in sorted(by_system):
    print(f"  {code:<20} {len(by_system[code]):>4} sets  "
          f"max {max(by_system[code]):.2e}")
