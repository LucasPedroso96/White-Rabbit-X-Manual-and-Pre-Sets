# White Rabbit X — Manuals, Set Library and Autobot

Public material for **White Rabbit X**, an Expert Advisor for MetaTrader 5:
manuals in 11 languages, the complete library of **3,738 optimization sets**,
and the **Autobot** — the automation that generates, walk-forward-tests and
validates every one of those sets end to end.

> **The sets are starting points, not finished strategies.** Each file opens a
> complete trading system with every axis marked for optimization. The values
> they ship with are where the search begins — do not run a set as-is on a live
> account. Optimize, lock what you have settled, validate out of sample.

- **Expert Advisor**: [MQL5 Market](https://www.mql5.com/en/market/product/187173)
- **Historical Tool Manager** (real tick/M1 data as MT5 Custom Symbols): [MQL5 Market](https://www.mql5.com/pt/market/product/188711)
- **Community and support**: [Telegram](https://t.me/MrRabbit_MT5)

---

## Getting the files

Click the green **Code** button above, then **Download ZIP** — you do not need a
GitHub account or any Git knowledge to use this library.

If any part of this is unfamiliar, ask an AI assistant such as Claude or
ChatGPT: paste the link to this page and describe what you are trying to do.
They walk through downloading, unzipping and locating your MetaTrader data
folder step by step, in your own language. There is no shame in it — the
interesting part of this project is the trading research, not the file
management.

> **Looking for the one-click installer?** `AutoBotSetup/Install_AutoBot_and_Sets.py`
> in this ZIP is the *source code* that builds it, not the installer itself.
> It can run directly from this ZIP too — it installs the sets from the
> `Sets/` folder below and offers to `pip install` the Autobot's own
> dependencies — but the ready-to-run installer
> (`White Rabbit X - Instalador.exe`), distributed separately through
> [Telegram](https://t.me/MrRabbit_MT5), needs nothing installed at all. If
> you just want the `.set` files, the ZIP you already downloaded is
> everything you need — see below.

## Using the library

```text
Sets/<class>/<SYMBOL>/<NN_SYSTEM>/<SIDE>_<VARIANT>.set
Sets/01_Forex/EURUSD/01_SLTP/BUY_MULTI.set
```

Copy the `Sets/` folder into your terminal's `MQL5\Profiles\Tester\`. In the
Strategy Tester: **Inputs → Load**.

To find that folder: in MetaTrader, **File → Open Data Folder**, then go into
`MQL5\Profiles\Tester`.

- **SIDE** — `BUY` or `SELL` in ten of the eleven systems. `08_GRID_UNIFIED`
  uses **`BOTH`**, because a unified basket has a single target covering both
  directions at once.
- **MULTI** — the entry indicator is an optimization axis (MACD, EMA, Momentum,
  Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA).
- **ICHIMOKU** — indicator fixed, because it requires Tenkan < Kijun < SenkouB
  and does not fit in the same period ranges as the others.

## The eleven systems

| System | Exit management | Position sizing |
|---|---|---|
| `01_SLTP` | Stop and target as ATR multiples | Fixed-R |
| `02_SLTP_ORGANIC` | Target anchored to the previous trade | Fixed-R |
| `03_TRAIL_ONLY` | Trailing only, no target | Fixed-R |
| `04_SLTP_TRAIL` | Stop, target and trailing behind | Fixed-R |
| `05_BE_TRAIL` | Breakeven then trailing | Fixed-R |
| `06_REVERSAL_EXIT` | Closes on the opposite signal | Fixed-R |
| `07_GRID_SEPARATE` | Grid, one target per side | Fixed lot |
| `08_GRID_UNIFIED` | Grid, single basket target | Fixed lot |
| `09_MARTINGALE` | Lot grows after a loss | Fixed lot |
| `10_DALEMBERT` | Arithmetic lot progression | Fixed lot |
| `11_SIGNAL_ONLY` | No stop, no target — measures the raw signal | Fixed lot |

Systems **01 through 06 use Fixed-R**: the lot is derived from the risk budget,
so they adapt themselves to any account size. Systems **07 through 11 use a
fixed lot** — their risk is whatever the minimum lot costs on that instrument,
regardless of your balance. Start with the Fixed-R ones.

---

## Autobot

`Autobot/` is the automation that produced this library — not a black box
that hands you a finished strategy, but the actual Python circuit: generate
the sets, run each one through a five-stage validation (genetic search →
refined search → exit-filter pass → **real-tick confirmation** → percentage-
sizing proof), gate on Monte Carlo drawdown robustness and out-of-sample
R-expectancy, and only then mark it ready.

Run it yourself — against your own broker, your own symbol list, your own
date range — or read it to see exactly how a set earned its place in `Sets/`.
Setup, requirements and what each script does: [`Autobot/README.md`](Autobot/README.md).

It pairs with **Historical Tool Manager** (linked above): the Autobot's
real-tick confirmation stage is only as good as the tick data behind it, and
HTM is what imports deep tick/M1 history into MT5 as Custom Symbols for
symbols your broker doesn't carry far enough back.

---

## Two things that change your results

### 1. Strategy Tester modeling mode

Under the **Settings** tab, **Modeling** field:

```
Every tick based on real ticks   <- use this
OHLC 1 minute                    <- only for 01_SLTP and 02_SLTP_ORGANIC
```

Measuring the same set in both modes across 3 years, the OHLC mode
**understated losses by 3.3× on trailing systems and by 23× on grid** — always
in the optimistic direction. Only fixed SL/TP stayed within 3%.

The reason is structural: trailing and grid depend on **when** price touched
each level inside the bar. OHLC mode interpolates that and smooths away exactly
the adverse excursions that would have taken the position out.

Real-tick modeling needs real tick data behind it — if your broker's own
history doesn't reach back far enough, **Historical Tool Manager** (linked
above) imports it as an MT5 Custom Symbol.

### 2. Lock what you have already found

Each set opens millions of combinations — the largest one exceeds 240 sextillion.
The workflow is iterative: run it, learn something, then flip that parameter's
`Y` to `N` and keep the winning value. The search space collapses by orders of
magnitude and the next round is far sharper.

Lock the **switches** before the geometry: `EntryIndicator` alone decides
whether four other parameters mean anything at all. A parameter sitting behind a
disabled switch is optimization time spent on nothing.

### Fixed-R and percentage sizing are complementary

Optimize in **Fixed-R**: with the base capital frozen, passes stay comparable to
each other and across symbols — +40R on gold and +40R on EURUSD mean the same
thing, while "+3,200 USD" means nothing without knowing the lot and the balance.

Live, **percentage of balance** usually makes more sense: it tracks the account,
compounds as it grows and cuts exposure as it shrinks — protection Fixed-R
cannot give, because it deliberately ignores the running balance. Both modes
report in R, so the record stays readable after the switch.

---

## Manuals

`Manuals/<language>/` — each in `.md`, `.pdf` and `.docx`:

| File | Contents |
|---|---|
| `01_User_Manual` | Complete manual |
| `02_MQL5_Market_Description` | Product description |
| `03_WFO_Optimization_Guide` | Walk-forward guide |
| `04_FAQ_and_Support` | Frequently asked questions |
| `07_Set_Ecosystem_Tutorial` | Set library tutorial |
| `08_Technical_Compatibility` | Technical compatibility |

Português · English · Русский · 中文 · Español · 日本語 · Deutsch · 한국어 ·
Français · Italiano · Türkçe

---

## Requirements and honest limits

- MetaTrader 5. Systems `07` and `08` (grid) require a **hedging** account — on
  a netting account the legs cancel each other out.
- This is a research framework, not a signal to switch on and forget. Every set
  is a hypothesis: it needs optimization, out-of-sample validation and
  forward-demo testing before real money.
- No Expert Advisor, preset or historical result guarantees future performance.
