# White Rabbit X - Optimization sets, organized BY SYSTEM

**3738 sets** = 89 symbols x 11 systems x 2 indicator variants x the sides each system has.

Every file is a complete trading system, optimizable end to end: entry
indicator, trigger method, timeframe, periods, ATR, filters and that
system's exit geometry are ALL marked `Y` in the same file. There is no
mandatory staging — you run it, you learn something, and you turn off by
hand (`Y` -> `N`) what you have already settled before the next round.

## Layout

```text
<class>/<SYMBOL>/<NN_SYSTEM>/<SIDE>_<VARIANT>.set
01_Forex/USDJPY/01_SLTP/BUY_MULTI.set
01_Forex/USDJPY/01_SLTP/BUY_ICHIMOKU.set
01_Forex/USDJPY/08_GRID_UNIFIED/BOTH_MULTI.set
```

- **SIDE**: `BUY` or `SELL` in ten of the eleven systems. `08_GRID_UNIFIED`
  uses **`BOTH`** and ships one file per variant: a unified basket has a
  single target covering both directions, so both sides must be open. With
  one side only it would be indistinguishable from `07_GRID_SEPARATE`.
- **MULTI**: `EntryIndicator` is an axis across 11 engines (MACD, EMA,
  Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA).
- **ICHIMOKU**: indicator fixed to Ichimoku (value 11), because it requires
  Tenkan < Kijun < SenkouB and does not fit the other engines' period ranges.

## The 11 systems

| System | Management skeleton | Own exit axes | Typical space |
|---|---|---|---:|
| `01_SLTP` | SL + TP as ATR multiples | Stop, Take, Breakeven on/off, BE distance | 7.98e+11 |
| `02_SLTP_ORGANIC` | SL + organic TP (anchored to the last trade) | Stop, Take, Breakeven on/off, BE distance | 7.98e+11 |
| `03_TRAIL_ONLY` | SL + trailing, no TP: lets it run | Stop, trailing source, Trail, BE | 2.40e+12 |
| `04_SLTP_TRAIL` | SL + TP with trailing behind | Stop, Take, Trail, BE | 1.20e+13 |
| `05_BE_TRAIL` | Mandatory breakeven + trailing, no TP | Stop, BE distance, trailing source, Trail | 1.20e+12 |
| `06_REVERSAL_EXIT` | Closes on the indicator's opposite signal | Stop, trailing on/off, Trail, BE, exit filters | 1.92e+12 |
| `07_GRID_SEPARATE` | Grid, one target per side | Take, Multiplier, MinimumDistance, number of legs | 3.59e+12 |
| `08_GRID_UNIFIED` | Grid, single basket target, both sides open | Take, Multiplier, MinimumDistance, legs per side | 1.80e+13 |
| `09_MARTINGALE` | Lot grows after a loss, 1 position per side | Stop, Take, Multiplier, maximum steps, BE | 2.24e+13 |
| `10_DALEMBERT` | Lot grows in arithmetic steps after a loss | Stop, Take, lot step, maximum steps, BE | 1.60e+13 |
| `11_SIGNAL_ONLY` | No SL and no TP: measures the raw signal | entry and filters only (negative coverage) | 3.55e+08 |

Systems **01 to 06 use Fixed-R**: the lot is derived from the risk budget,
so the same file adapts itself to any account size. Systems **07 to 11 use
a fixed lot** — their risk is whatever the minimum lot costs on that
instrument, independent of your balance. Start with the Fixed-R ones.

## Shared core (present in every system)

| Axis | Start | Step | Stop |
|---|---:|---:|---:|
| `EntryIndicator` (MULTI) | 0 MACD | 1 | 10 OsMA |
| `EntryMethod` | 0 reversal | 1 | 6 any trigger |
| `TimeFrame` | 3 values, per asset class | 1 | |
| `Fast_EMA` | 6 | 3 | 18 |
| `Slow_EMA` | 21 | 6 | 45 |
| `MACD_SMA` | 3 | 3 | 15 |
| `PeriodoATR` | 7 | 7 | 28 |
| `AtivarFiltroMTF` / `AtivarFiltroMA` / `AtivarFiltroADX` / `EntradaATR` | false | | true |
| `StochasticPriceField` (MULTI) | 0 Low/High | 1 | 1 Close/Close |
| `IchimokuUseKumo` / `IchimokuChikouFilter` (ICHIMOKU) | false | | true |
| `MA_Period` | 100 | 100 | 300 |
| `MetodoMA` | 0 | 1 | 3 |
| `ADX_Limiar` | 15 | 5 | 30 |

`Fast_EMA` stops at 18 and `Slow_EMA` starts at 21 on purpose: the EA
requires fast < slow and rejects the whole pass with
`incorrect input parameters` if the order breaks. The same constraint is why
Ichimoku gets its own file.

## Modeling mode: use real ticks

In the Strategy Tester's **Settings** tab, **Modeling** field:

```text
Every tick based on real ticks   <- use this
OHLC 1 minute                    <- only 01_SLTP and 02_SLTP_ORGANIC
```

This is not a style preference. Measuring the same set in both modes over 3
years on the same symbol, the OHLC mode understated the loss by **3.3x on
trailing systems and 23x on grid** — always in the optimistic direction.
Only fixed SL/TP stayed within 3%.

The cause is structural: trailing and grid depend on **when** price touched
each level inside the bar. OHLC mode interpolates that from four prices per
minute and smooths away exactly the adverse excursions that would have taken
the position out. Optimizing a trailing system on interpolated bars selects
parameters that survived a price path which never happened.

Real ticks cost roughly 20x more time per pass. Budget for it: it is the
difference between a result and a number.

## How to run

1. Strategy Tester -> `White Rabbit X (Global Multi-Indicator).ex5`. Pick the
   broker's real symbol (mind the suffix) and the history range.
2. **Settings -> Modeling -> Every tick based on real ticks.**
3. Inputs tab -> **Load** -> the `.set` for the symbol/system/side you want.
4. Optimization: **Fast genetic based algorithm**. Above 100 million
   combinations MT5 switches to genetic on its own.
5. Run it. Re-launching the genetic algorithm continues the same search and
   refines the result.
6. **Lock what you found**: flip that parameter's `Y` to `N` and put the
   winning value in all four fields. The search space collapses by orders of
   magnitude and the next round is far sharper.
7. Repeat until only the exit geometry is left; Complete Search becomes
   viable at that point.

### Lock the switches before the geometry

Locking order matters more than most people expect: entry indicator and
method -> timeframe -> periods -> filter stack -> exit geometry.

The reason is measurable. Several parameters are **conditionally inert** —
they mean nothing while their switch is off. `MetodoMA` only matters with
`AtivarFiltroMA=true`; `ADX_Limiar` only with the ADX filter on;
`StochasticPriceField` only when the engine is Stochastic. In one measured
run, 818 of 3,435 distinct results came back duplicated because the genetic
algorithm was varying parameters sitting behind a disabled switch — each one
a full backtest spent on nothing.

So the most valuable parameter to fix first is not the one that moves the
result the most. It is the **switch** that decides whether the others mean
anything at all.

### Reading the winner

The composite score caps each component at 1.0, which means it stops
discriminating at the top: passes that exceed the caps all tie at 1.0 while
genuinely better passes can rank below them. Break ties by profit and by a
real Profit Factor.

Treat `Profit Factor = 0` with suspicion rather than enthusiasm — MT5 reports
it when gross loss is zero, so it means *no losing trade in the sample*, not
excellence. Combined with a stop several times wider than the target, that is
the classic shape of winning small often and losing big once, where the risk
simply has not materialized yet.

### Fixed-R for research, percentage for live

Optimize in **Fixed-R**: with the base capital frozen, passes stay comparable
to each other and across symbols. +40R on gold and +40R on EURUSD mean the
same thing, while "+3,200 USD" means nothing without the lot and the balance.

Live, **percentage of balance** usually makes more sense: it tracks the
account, compounds as it grows and cuts exposure as it shrinks — protection
Fixed-R cannot give, because it deliberately ignores the running balance.
Both modes report in R, so the record stays readable after the switch.

## Warnings by status

- `HEDGE_ACCOUNT_REQUIRED`: 534 sets
- `HIGH_RISK`: 712 sets
- `HIGH_RISK_RESEARCH`: 356 sets
- `RESEARCH`: 2136 sets

- **HEDGE_ACCOUNT_REQUIRED** (grid): requires a real MT5 hedging account.
  Netting cannot represent independent legs and the legs cancel out.
- **HIGH_RISK** (martingale, d'alembert): the risk curve changes nature.
  Optimizing without a lot cap is valid only as research; set a cap your
  broker accepts before any forward-demo.
- **HIGH_RISK_RESEARCH** (signal only): no stop loss. It exists to measure
  the raw signal, never to trade.

None of these files is a production preset. After validating out of sample,
copy the winners into a new file with every flag set to `N` and its own
MagicNumber.

## Tooling

- Generator: `generate_system_sets.py`
- Validator: `validate_system_sets.py`

The validator reimplements the EA's `OnInit` rules and tests the extremes of
every axis across all files: if any `.set` could produce
`INIT_PARAMETERS_INCORRECT`, it fails before you find out in the tester.

Full manifest (symbol, system, combinations, magic, SHA-256):
`MANIFESTO_SISTEMAS.csv`.
## Walk-forward, and how to read it

The EA runs its own walk-forward — this is not the tester's Forward tab. Enable
`AtivarWFO` and the period is sliced into In-Sample and Out-of-Sample windows.

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

