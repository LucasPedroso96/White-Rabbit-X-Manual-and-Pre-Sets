# White Rabbit X — Guida di ottimizzazione WFO

Riferimento autorevole generato dalla fonte EA e dal manifesto correnti — EA 1.11 — 127 inputs — 3738 sets

**Attenzione alla data.** Con il WFO attivo, OnTester confronta la fine reale del test con input_end_date e restituisce zero se il test è terminato prima (tolleranza di 80 ore). Una data sbagliata azzera tutte le passate e l'intera ottimizzazione sembra rotta. Imposta input_end_date sulla stessa data finale configurata nello Strategy Tester.

## Ambito e fonti di verità

La fonte definisce inputs, valori e funzioni; il manifesto definisce ogni set, stato, percorso e SHA-256. L'archivio Quantum è solo storico.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Materiale generato; gli identificatori corrispondono esattamente all'EA.

## Metodo walk-forward

Usare IS, OOS e forward demo cronologici con spread, commissione, swap e slippage realistici.

## Flusso sicuro

Modificare una sola matrice per fase e conservare le prove.

1. Allineare EX5, fonte, schema set e manifesto.
2. Caricare la libreria tramite Strategy Tester Inputs.
3. Mappare simbolo e suffix esatti.
4. Iniziare dai baseline 01–05 con BUY/SELL separati.
5. 06 è ricerca a un solo asse.
6. 07 ingresso, 08 filtri, 09 rischio, 10 uscita.
7. Eseguire IS, OOS e forward demo cronologici.
8. Controllare Status, RelativePath e SHA256.
9. Solo USE esplicito autorizza l'ambiente definito.

## Stati e decisione

Lo stato esatto resta e viene mappato prudentemente in USE, REOPTIMIZE, RESEARCH o HOLD.

| Sistema | Gestione | Set |
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

> Questa sezione è per ora disponibile solo in inglese.

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

## Avviso di rischio

Nessun EA, set o storico garantisce il futuro. Validare OOS e demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
