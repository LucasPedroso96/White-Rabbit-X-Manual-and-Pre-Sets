# White Rabbit X

Twelve native entry engines. Eleven exit architectures. One Expert Advisor.

Most EAs give you a strategy. This one gives you the workshop: you choose the signal engine, the management skeleton and the filters, and the built-in walk-forward tells you whether the result survives outside the sample.

## Twelve entry engines, all native

MACD · EMA Cross · Momentum · Stochastic · TRIX · RSI · CCI · Williams %R · DeMarker · MFI · OsMA · Ichimoku

Every one is a native MetaTrader indicator — no custom indicator files to install, nothing to break on the next terminal update.

Ichimoku reads all five buffers: the reference trigger is the Kumo breakout, not a Tenkan/Kijun cross, and the Chikou span works as a confirmation filter. Stochastic exposes slowing, smoothing method and the Low/High vs Close/Close price field — the three parameters most EAs hardcode.

Three trigger types combine into seven entry methods.

## Eleven exit architectures

SL/TP · organic target · trailing only · SL/TP with trailing · breakeven and trailing · reversal exit · separate grid · unified grid · Martingale · D'Alembert · signal only.

The management skeleton is a choice, not a fixed part of the strategy.

## Walk-forward inside the EA

Not the tester's Forward tab. The EA slices the period into in-sample and out-of-sample windows and, in optimization mode, trades only the in-sample — so the genetic algorithm never sees the data it will be judged on.

Three window modes: sequential, rolling (the classic — roughly three times more cycles from the same history) and anchored.

The report gives the Walk Forward Efficiency per cycle, with mean and standard deviation. An EA returning 70% every cycle and one returning 200% once and −20% the rest share the same average; only the first is robust, and the dispersion tells them apart.

## Risk measured in R

Fixed-R sizes every position so one trade risks exactly 1R, computed on a fixed base capital rather than the running balance. Results become comparable across symbols, accounts and runs: +40R on gold and +40R on EURUSD mean the same thing, while "+3,200 USD" means nothing without knowing the lot and the balance.

Fifteen optimization criteria, including a composite score that returns zero below thirty trades — which alone discards the classic "winner" built on three lucky trades.

## Protection that runs before the order

Maximum daily loss, equity drawdown ceiling, minimum free margin, spread limit, session and weekday windows, and a news filter with CSV cache for backtesting. Freeze-level and stops-level distances are checked before each request, so the log stays readable instead of filling with broker rejections.

## Chart panel

Strategy, indicator and active parameters, account and EA capital, closed, floating and net P&L, open positions and — under Martingale, D'Alembert or Grid — the live cycle: consecutive losses, outstanding debt, recovered amount, target, legs, anchor and ATR spacing.

Interface in eleven languages.

## What ships with it

- Expert Advisor for MetaTrader 5 — 136 documented inputs
- 3,738 ready-made set files: 89 symbols × 11 systems × both directions
- Automatic installer that finds your terminal, copies the sets and adapts them to your broker's symbol suffix and minimum lot
- Manual, WFO guide, input reference, set tutorial and FAQ in eleven languages
- Support and updates through the official channel

## Before you buy

This is a research framework, not a signal to switch on and walk away. Every set is a hypothesis: it needs optimization, out-of-sample validation and forward-demo before real money.

Grid, Martingale and D'Alembert change the nature of the risk curve. Grid requires a real hedging account.

No Expert Advisor, preset or historical result guarantees future performance.

---

Official channel: https://t.me/MrRabbit_MT5 — free set library, manuals in your language and update notices. The EA is sold only here on the MQL5 Market; the sets are distributed free on that channel and nowhere else.
