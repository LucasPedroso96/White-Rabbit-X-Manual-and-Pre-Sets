# White Rabbit X — FAQ e supporto

Riferimento autorevole generato dalla fonte EA e dal manifesto correnti — EA 1.11 — 127 inputs — 3738 sets

## Ambito e fonti di verità

La fonte definisce inputs, valori e funzioni; il manifesto definisce ogni set, stato, percorso e SHA-256. L'archivio Quantum è solo storico.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Materiale generato; gli identificatori corrispondono esattamente all'EA.

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

## Risposte operative

Controllare stop, modalità conto, suffix, ora server, CSV news e limiti broker.

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

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Community e download

Entra nel canale Telegram ufficiale: **https://t.me/MrRabbit_MT5**

Manuali e libreria completa dei set: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- Set pronti per strumento e per tipo di sistema (SL/TP, trailing, griglia, martingala e altri), organizzati per essere caricati direttamente nello Strategy Tester.
- Manuali nella tua lingua: portoghese, inglese, russo, cinese, spagnolo, giapponese, tedesco, coreano, francese, italiano e turco.
- Avvisi di aggiornamento dell'EA e delle librerie di set.
- Supporto e scambio di esperienze con altri utenti.

> Questo è l'unico canale ufficiale. Non acquistare set o copie dell'EA da terzi che dichiarano di rappresentare White Rabbit X: l'EA è venduto solo sul MQL5 Market e i set sono distribuiti gratuitamente sul canale indicato.

## Avviso di rischio

Nessun EA, set o storico garantisce il futuro. Validare OOS e demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
