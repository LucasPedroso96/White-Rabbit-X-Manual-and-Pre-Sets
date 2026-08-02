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
4. Navigate per classe e asset: ogni asset porta gli 11 tipi di sistema (01_SLTP a 11_SIGNAL_ONLY), un set per lato (BUY/SELL; BOTH per il grid unificato) e due varianti di ingresso — MULTI mette in gara gli indicatori 0–10 su un solo asse, ICHIMOKU ha un file dedicato.
5. La fase 1 e la scoperta delle regioni: lanciate il genetico sul set cosi com'e — gruppo di ingresso completo (indicatore, metodo, timeframe, applied price, periodi), uscite del sistema e interruttori dei filtri, tutto insieme.
6. Dai giri successivi, bloccate (Y→N) gli input 'di scrittura' — enum e booleani — decisi dalla fase precedente e lasciate aperti solo i numerici; la taratura di un filtro entra solo se il suo interruttore e sopravvissuto acceso.
7. Il filtro ATR di ingresso (EntradaATR) esiste solo nei sistemi grid; altrove resta spento per costruzione.
8. Validate il vincitore su tick reali: decidono la divergenza contro l'OHLC e la retention out-of-sample, mai il profitto in-sample. Scartate un candidato il cui risultato su tick reali diverge da quello OHLC per più del 30% — i due devono concordare sulla forma del risultato, non solo sul segno.
8a. Filtrate il sopravvissuto con Monte Carlo: ricampionate la sequenza di trade con bootstrap (in multipli di R, non in valuta) e scartate se il drawdown al 95° percentile supera il doppio del drawdown osservato, o se la probabilità di rovina ricampionata supera il 5%. Un set che sembra stabile solo per l'ordine specifico in cui i suoi trade sono avvenuti non è stabile.
8b. Per i sei sistemi Fixed-R (`01` a `06`), richiedete un'aspettativa in R positiva fuori campione. Un set che ha pareggiato o perso R fuori campione non viene promosso, indipendentemente dal punteggio in-sample.
9. Dopo il tick reale, passate il dimensionamento a Percentage e rilanciate: promuovete solo se passa anche questa — ed e in quel modo che il set deve operare.

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

Per questo il circuito salva un set approvato solo dopo aver ripetuto il passaggio finale in modalita Percentage: se il risultato non regge sotto interesse composto, non era pronto — e il set validato viene consegnato in quella modalita.

## Formule: cosa ottimizzano e cosa riporta il risultato

`selectedFormula` decide cosa OnTester restituisce all'ottimizzatore genetico — il numero unico in base al quale un passaggio viene classificato. Non è la stessa domanda di "in che unità riporta il risultato il set consegnato". Il circuito usa formule diverse per compiti diversi: le fasi iniziali favoriscono formule che premiano un risultato ampio e ben popolato (così la ricerca genetica ha un gradiente da risalire), invece di una formula ristretta che ottiene un punteggio alto solo su un percorso specifico.

Per i sei sistemi Fixed-R, il report finale del set consegnato usa **SomaR** (la somma degli esiti dei trade in multipli di R): una volta che un candidato ha già superato retention, divergenza, Monte Carlo e il gate di aspettativa in R sopra descritto, SomaR è ciò che esprime il risultato nella stessa unità che questa guida usa per confrontare simboli e sistemi altrove — R, non valuta. Non decide il vincitore; riporta il risultato del vincitore già determinato in un'unità comparabile.

## Autobot e Historical Tool Manager

Questa libreria viene consegnata pre-validata, ma il circuito sopra descritto non è una scatola nera — è pubblicato come **Autobot** nello stesso repository in cui si trova questo manuale (`Autobot/`), il codice reale che esegue ogni passaggio di questa guida. Leggetelo per vedere esattamente come un set ha guadagnato il suo status, oppure eseguitelo voi stessi contro il vostro broker, la vostra lista di strumenti o il vostro intervallo di date.

La fase di conferma su tick reali dipende dalla disponibilità di dati di tick reali con cui confrontarsi. **Historical Tool Manager** (MQL5 Market: https://www.mql5.com/pt/market/product/188711) importa in MT5 uno storico profondo di tick e M1 come Custom Symbol per gli strumenti il cui storico presso il proprio broker non copre un periodo sufficientemente lungo — utile sia che eseguiate l'Autobot, sia che vogliate semplicemente più storico per testare manualmente.

## Avviso di rischio

Nessun EA, set o storico garantisce il futuro. Validare OOS e demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
