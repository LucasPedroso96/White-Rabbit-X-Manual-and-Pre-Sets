# White Rabbit X — Guida all'ecosistema dei set

Riferimento autorevole generato dalla fonte EA e dal manifesto correnti — EA 1.11 — 127 inputs — 3738 sets

## Ambito e fonti di verità

La fonte definisce inputs, valori e funzioni; il manifesto definisce ogni set, stato, percorso e SHA-256. L'archivio Quantum è solo storico.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Materiale generato; gli identificatori corrispondono esattamente all'EA.

## Installazione e primo test

Installare l'EX5 corretto, caricare un set in Tester Inputs, scegliere il simbolo esatto e controllare il Journal.

## Libreria set rilevata

I conteggi provengono da file e manifesto. Ogni set è un'ipotesi. Counts and fingerprints were read at generation time.

| Folder | Sets | Purpose |
| --- | --- | --- |
| 01_Forex | 168 | Per-asset baselines — Forex. |
| 02_Metals | 18 | Per-asset baselines — Metals. |
| 03_Cryptocurrencies | 36 | Per-asset baselines — Cryptocurrencies. |
| 04_Indices_Energies | 42 | Per-asset baselines — Indices Energies. |
| 05_US_Stocks_CFD | 300 | Per-asset baselines — US Stocks CFD. |
| 06_Research_Matrix | 935 | Controlled one-axis research. |
| 07_Entry_System_Matrix | 3360 | Indicator × entry method × management matrix. |
| 08_Filter_Stack_Matrix | 320 | Signal-filter stack combinations. |
| 09_Risk_Engine_Matrix | 130 | Compatible sizing, risk and recovery models. |
| 10_Exit_Stack_Matrix | 720 | Exit-control stack combinations. |

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

## Flusso sicuro

Modificare una sola matrice per fase e conservare le prove.

1. Allineare EX5, fonte, schema set e manifesto.
2. Caricare la libreria tramite Strategy Tester Inputs.
3. Mappare simbolo e suffix esatti.
4. Navigate per classe e asset: ogni asset porta gli 11 tipi di sistema (01_SLTP a 11_SIGNAL_ONLY), un set per lato (BUY/SELL; BOTH per il grid unificato) e due varianti di ingresso — MULTI mette in gara gli indicatori 0–10 su un solo asse, ICHIMOKU ha un file dedicato.
5. La fase 1 e la scoperta delle regioni: lanciate il genetico sul set cosi com'e — gruppo di ingresso completo (indicatore, metodo, timeframe, applied price, periodi), uscite del sistema e interruttori dei filtri, tutto insieme.
6. Dai giri successivi, bloccate (Y→N) gli input 'di scrittura' — enum e booleani — decisi dalla fase precedente e lasciate aperti solo i numerici; la taratura di un filtro entra solo se il suo interruttore e sopravvissuto acceso.
7. Il filtro ATR di ingresso (EntradaATR) esiste solo nei sistemi grid; altrove resta spento per costruzione.
8. Validate il vincitore su tick reali: decidono la divergenza contro l'OHLC e la retention out-of-sample, mai il profitto in-sample.
9. Dopo il tick reale, passate il dimensionamento a Percentage e rilanciate: promuovete solo se passa anche questa — ed e in quel modo che il set deve operare.

## Telemetria dei cicli nel dashboard

Il pannello usa gli stessi snapshot del calcolo lotti e della chiusura basket.

- L'aggiornamento periodico per tick è limitato a una volta al secondo; inizializzazione ed eventi trade possono aggiornare subito.
- Balance ed Equity riguardano l'intero conto. Closed P&L è la variazione da OnInit; Open P&L e posizioni sono attuali e filtrati per Symbol + Magic.
- Martingale mostra per BUY/SELL perdite consecutive, numero e importo lordo delle perdite, recovered, deficit e target = deficit × Multiplicador.
- Superare MaxMartingaleSteps esegue hard reset: elimina il vecchio deficit e il prossimo ordine usa base lot. Massimo una posizione aperta per lato.
- D'Alembert mostra livello corrente e prossimo lotto normalizzato BUY/SELL.
- Grid mostra legs/volume, realized con costi, open P&L, cycle P&L, target congelato all'avvio e remaining.
- Anchor è la posizione confermata più recente. BUY richiede strettamente meno di anchor − ATR × DistanciaMinima, SELL strettamente più; avanzamento in ATR.
- Separate termina solo il ciclo del lato flat; Unified termina quando entrambi sono flat. Ordini in corso ritardano il reset.
- Target avvia la richiesta di chiusura; commissioni, fee e slippage di uscita possono lasciare il risultato finale leggermente inferiore.
- InterfaceLanguage mantiene 11 lingue. Auto usa English nel Tester e la lingua terminale live; label non tradotte tornano a English.

## Compatibilità e limiti

Regole prudenti; prevalgono limiti broker più rigidi.

- Percentage e Fixed-R richiedono AtivarStop=true.
- Grid solo Monetary/Fixed Lot, Recovery_None e conto hedging.
- Grid richiede take, DistanciaMinima positivo e limite almeno due.
- Finché il basket resta aperto, perdite realizzate, swap, commissioni e costi del ciclo restano inclusi nel risultato necessario al target; il profitto isolato di una gamba non li cancella.
- In Grid_SeparateProfit i cicli BUY e SELL sono indipendenti. Se spariscono tutte le posizioni di un lato, quel ciclo termina; un ingresso successivo riparte senza riportare il deficit chiuso.
- D'Alembert solo Fixed Lot, Grid_Disabled e DAlembertStep>0.
- Martingale rispetta MaxMartingaleSteps e MaxMartingaleLot.
- OnOppositeOrder richiede hedging, entrambi i lati e grid spento.
- Backtest news richiede CSV in Common\Files.
- Gli orari usano l'ora server.
- Validare suffix e specifiche per ogni broker.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Avviso di rischio

Nessun EA, set o storico garantisce il futuro. Validare OOS e demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
