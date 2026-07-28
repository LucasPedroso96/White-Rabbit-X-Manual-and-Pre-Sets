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

## Avviso di rischio

Nessun EA, set o storico garantisce il futuro. Validare OOS e demo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
