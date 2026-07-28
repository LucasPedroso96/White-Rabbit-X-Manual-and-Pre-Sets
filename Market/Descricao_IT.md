# White Rabbit X

Dodici motori di ingresso nativi. Undici architetture di uscita. Un Expert Advisor.

La maggior parte degli EA consegna una strategia chiusa. Questo consegna l'officina: sei tu a scegliere il motore di segnale, lo scheletro di gestione e i filtri, e il walk-forward integrato ti dice se il risultato regge fuori campione.

## Dodici motori di ingresso, tutti nativi

MACD · EMA Cross · Momentum · Stochastic · TRIX · RSI · CCI · Williams %R · DeMarker · MFI · OsMA · Ichimoku

Sono tutti indicatori nativi di MetaTrader: niente da installare e niente che si rompa al prossimo aggiornamento del terminale.

Ichimoku legge tutti e cinque i buffer: il segnale di riferimento è la rottura della nuvola (Kumo), non un incrocio Tenkan/Kijun, e la Chikou è disponibile come filtro di conferma. Lo Stocastico espone lo smorzamento, il metodo di media e il campo prezzo Low/High o Close/Close — i tre parametri che la maggior parte degli EA fissa nel codice.

Tre tipi di innesco si combinano in sette metodi di ingresso.

## Undici architetture di uscita

SL/TP · obiettivo organico · solo trailing · SL/TP con trailing · pareggio e trailing · uscita su inversione · griglia separata · griglia unificata · martingala · D'Alembert · solo segnale.

Lo scheletro di gestione è una tua scelta, non una parte fissa della strategia.

## Walk-forward dentro l'EA

Non è la scheda Forward del tester. L'EA divide il periodo in finestre in-sample e out-of-sample e, in modalità ottimizzazione, opera solo l'in-sample: l'algoritmo genetico non vede mai i dati su cui verrà giudicato.

Tre modalità di finestra: sequenziale, scorrevole (la classica — circa tre volte più cicli sullo stesso storico) e ancorata.

Il report fornisce la Walk Forward Efficiency per ciclo, con media e deviazione standard. Un EA che rende 70% in ogni ciclo e uno che rende 200% in uno e −20% negli altri hanno la stessa media; solo il primo è robusto, e a distinguerli è la dispersione.

## Rischio misurato in R

La modalità Fixed-R dimensiona ogni posizione perché un'operazione rischi esattamente 1R, calcolato su un capitale base fisso e non sul saldo corrente. I risultati diventano confrontabili tra strumenti, conti e prove: +40R sull'oro e +40R su EURUSD significano la stessa cosa, mentre «+3.200 USD» non significa nulla senza sapere lotto e saldo.

Quindici criteri di ottimizzazione, tra cui un punteggio composito che restituisce zero sotto le trenta operazioni — cosa che da sola scarta il classico «vincitore» costruito su tre operazioni fortunate.

## Protezione che agisce prima dell'ordine

Perdita massima giornaliera, tetto di drawdown sul patrimonio, margine libero minimo, limite di spread, finestre di sessione e giorni della settimana, e filtro notizie con cache CSV per il backtest. Le distanze di freeze level e stops level sono verificate prima di ogni richiesta, così il log resta leggibile invece di riempirsi di rifiuti del broker.

## Pannello sul grafico

Strategia, indicatore e parametri attivi, capitale del conto e dell'EA, P&L chiuso, fluttuante e netto, posizioni aperte e — con martingala, D'Alembert o griglia — il ciclo in corso: perdite consecutive, deficit aperto, importo recuperato, obiettivo, ordini, ancora e spaziatura ATR.

Interfaccia in undici lingue.

## Cosa è incluso

- Expert Advisor per MetaTrader 5 — 136 parametri documentati
- 3.738 file .set pronti: 89 strumenti × 11 sistemi × entrambe le direzioni
- Installatore automatico: trova il tuo terminale, copia i set e li adatta al suffisso del simbolo e al lotto minimo del tuo broker
- Manuale, guida WFO, riferimento dei parametri, tutorial dei set e FAQ in undici lingue
- Supporto e aggiornamenti tramite il canale ufficiale

## Prima di acquistare

Questo è un framework di ricerca, non un segnale da accendere e dimenticare. Ogni set è un'ipotesi: richiede ottimizzazione, validazione fuori campione e forward-demo prima del denaro reale.

Griglia, martingala e D'Alembert cambiano la natura della curva di rischio. La griglia richiede un conto hedging reale.

Nessun Expert Advisor, preset o risultato storico garantisce le prestazioni future.

---

Canale ufficiale: https://t.me/MrRabbit_MT5 — libreria di set gratuita, manuali nella tua lingua e avvisi di aggiornamento. L'EA è venduto solo qui sul MQL5 Market; i set sono distribuiti gratuitamente su quel canale e in nessun altro luogo.
