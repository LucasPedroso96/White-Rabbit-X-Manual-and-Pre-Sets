# White Rabbit X — Autobot

The automation behind the `Sets/` library one level up: the same code that
generates, validates and walk-forward-tests every `.set` file in this
repository. Publishing it because the sets are more useful once you can see
how they were produced, and because you may want to run the same circuit on
your own broker, your own symbol list, or a different date range.

**This is research tooling, not a turnkey signal generator.** It drives
MetaTrader 5's Strategy Tester through a Python subprocess loop; you still
need MT5 installed, the EA loaded, and — for a full campaign — hours to days
of unattended machine time.

## Requirements

- MetaTrader 5, with **White Rabbit X** installed under `MQL5\Experts\`
  ([MQL5 Market](https://www.mql5.com/en/market/product/187173)).
- A **hedging account** for the grid systems (`07`/`08`) — on a netting
  account the two legs cancel each other out.
- Python 3.11+, and:
  ```
  pip install -r requirements.txt
  ```

## First run

The tools locate your terminal automatically — they scan
`%APPDATA%\MetaQuotes\Terminal\*\MQL5\Experts\` for the first install that has
White Rabbit X in it. If you have more than one terminal installed, or the
auto-detection picks the wrong one, point it explicitly:

```
setx WRX_MT5_DATA_DIR "C:\Users\you\AppData\Roaming\MetaQuotes\Terminal\<hash>"
```

(Find that folder from MetaTrader: **File → Open Data Folder**.)

Then, once, fetch your real account numbers — leverage, in particular, changes
margin behavior enough to shift results between the OHLC and real-tick passes:

```
python atualizar_conta_real.py
```

This writes `_conta_real.json` next to these scripts (git-ignored — it is
account data, not code). Nothing here uses a fictitious leverage or balance;
if this file is missing, the tools that need it stop with a clear message
instead of guessing.

## What each tool does

| Script | Role |
|---|---|
| `generate_system_sets.py` | Rebuilds the entire `Sets/` library from scratch (3,738 files) — every asset × system × side × entry variant, every axis marked for optimization. |
| `auto_set_manager.py` | Rewrites the generic library against **your** broker: real symbol suffix (`EURUSDm`, `XAUUSD.r`...), real minimum lot, real capital. |
| `campanha.py` | Batch-runs the full 5-stage circuit (below) over a queue of symbol/system/side combinations, resumable via a ledger file so a multi-day run survives interruption. |
| `optimize_two_stage.py` | The circuit itself for a single combination — called by `campanha.py`, or run standalone with `--symbol`/`--sistema`/`--variante`. |
| `monte_carlo_wrx.py` | Bootstrap resampling over the trade sequence (R-multiples, not currency) — the drawdown-robustness gate inside stage 4. |
| `wfo_matrix.py` | Sweeps a grid of In-Sample/Out-of-Sample window ratios and reports which proportions hold up **in the neighborhood**, not just at one arbitrary split. |
| `validate_system_sets.py` | Static check: expands every reachable axis combination in the library and confirms none trips `INIT_PARAMETERS_INCORRECT` in the EA's `OnInit`. |
| `smoke_test_sets.py` | Dynamic check: actually loads a sample of sets into the Strategy Tester and confirms they run, not just parse. |
| `audit_wfo_sets.py` | Audits the Walk-Forward block specifically — the traps here (a silent `OnTester` returning `0.0`, a sign flip in `wfo_customStepSizePercent`) pass every other check and still return a wrong number. |
| `ready_library.py` | Mirrors validated, approved sets into a separate "ready" folder, grouped by symbol and indicator. |
| `portfolio_builder.py` / `portfolio_html.py` | Turns a Strategy Tester `.htm` report into structured metrics (drawdown, R-expectancy, retention) and an HTML view. |
| `amostra_formulas.py` / `amostra_noite.py` | Compares the EA's built-in fitness formulas against each other on a fixed system/period — how each one behaves in practice, not just what it computes. |
| `calc_capital_base.py` | Per-asset-class capital reference used for Fixed-R sizing (`CapitalBaseR`). |

## The five-stage circuit

Each combination (symbol × system × side) goes through, in order:

1. **Regions** — genetic search over the full parameter space, OHLC modeling
   (fast enough to search; not fast enough to trust for the final answer).
2. **Numbers** — same modeling, refined search with the winning switches
   already locked.
3. **Execution filters** — same modeling, formula overridden so the exit
   filters get their own pass.
4. **Real-tick confirmation** — the same candidate re-run under
   `Every tick based on real ticks`. OHLC understated losses by 3.3× on
   trailing systems and 23× on grid, measured across 3 years — this stage is
   why. Also where Monte Carlo and the R-expectancy gate run.
5. **Percentage proof** — the delivered set re-validated under percentage-of-
   balance sizing, since that's how it behaves live, not in Fixed-R research
   mode.

A set only reaches `Sets/` after all five pass. `campanha.py`'s queue starts
with the grid systems and then works through the rest in a fixed, unweighted
order — no system gets more search time than another by default.

## Honest limits

- A campaign for one symbol across all 11 systems and both entry-indicator
  modes takes on the order of days of unattended MT5 time, not minutes.
- The Strategy Tester's interleaved-holdout mode is not walk-forward in the
  strict sense (it cannot re-optimize at each window boundary) — see
  `Manuals/*/03_WFO_Optimization_Guide` for what that distinction means in
  practice.
- No script here places a trade. Everything stops at a validated `.set` file.
