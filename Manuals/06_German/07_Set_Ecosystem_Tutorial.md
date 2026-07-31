# White Rabbit X — Set-Ökosystem-Leitfaden

Verbindliche Referenz aus aktuellem EA-Quelltext und Set-Manifest — EA 1.11 — 127 inputs — 3738 sets

## Umfang und Wahrheitsquellen

Der EA-Quelltext definiert Inputs, Defaults und Funktionen; das Manifest jedes Set, Status, Pfad und SHA-256. Das alte Quantum-Archiv ist nur historisch.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Generiertes Material; Parameternamen entsprechen exakt dem EA.

## Installation und erster Lauf

Passendes EX5 installieren, Set in Tester Inputs laden, exaktes Symbol wählen und Journal prüfen.

## Gefundene Set-Bibliothek

Zahlen stammen aus Dateien und Manifest. Jedes Set ist eine Forschungshypothese. Counts and fingerprints were read at generation time.

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

## Manifeststatus und Entscheidung

Der Originalstatus bleibt erhalten und wird konservativ auf USE, REOPTIMIZE, RESEARCH oder HOLD abgebildet.

| System | Management | Sets |
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

## Sicherer Ablauf

Pro Stufe nur eine Matrix ändern und Nachweise aufbewahren.

1. Version von EX5, Quelle, Set-Schema und Manifest abgleichen.
2. Bibliothek über Strategy Tester Inputs laden.
3. Exaktes Brokersymbol und Suffix zuordnen.
4. Navigieren Sie nach Klasse und Asset: Jedes Asset umfasst die 11 Systemtypen (01_SLTP bis 11_SIGNAL_ONLY), einen Set pro Seite (BUY/SELL; BOTH beim vereinigten Grid) und zwei Einstiegsvarianten — MULTI lässt die Indikatoren 0–10 auf einer Achse antreten, ICHIMOKU hat eine eigene Datei.
5. Phase 1 ist Regionssuche: Starten Sie die genetische Optimierung mit dem Set wie geliefert — komplette Einstiegsgruppe (Indikator, Methode, Timeframe, applied price, Perioden), die Ausstiege des Systems und die Filterschalter, alles auf einmal.
6. Ab den folgenden Runden sperren Sie (Y→N) die »Schrift«-Inputs — Enums und Booleans — aus der Vorphase und lassen nur die numerischen offen; die Feinabstimmung eines Filters kommt nur hinein, wenn sein Schalter eingeschaltet überlebt hat.
7. Der ATR-Einstiegsfilter (EntradaATR) existiert nur in den Grid-Systemen; überall sonst bleibt er konstruktionsbedingt aus.
8. Validieren Sie den Gewinner mit echten Ticks: Es entscheiden die Divergenz gegen OHLC und die Out-of-Sample-Retention, nie der In-Sample-Gewinn.
9. Nach dem Echt-Tick-Lauf stellen Sie die Positionsgröße auf Percentage um und testen erneut: Nur bei Bestehen befördern — und genau in diesem Modus soll der Set handeln.

## Zyklus-Telemetrie im Dashboard

Das Panel nutzt dieselben Zustands-Snapshots wie Lotberechnung und Basket-Schließung.

- Die periodische Tick-Aktualisierung ist auf einmal pro Sekunde begrenzt; Initialisierung und Trade-Ereignisse können sofort aktualisieren.
- Balance und Equity gelten fürs gesamte Konto. Closed P&L ist die Änderung seit OnInit; Open P&L und Positionen sind aktuell und nach Symbol + Magic gefiltert.
- Martingale zeigt je BUY/SELL Verlustserie, Anzahl und Bruttosumme der Zyklusverluste, recovered, deficit und target = deficit × Multiplicador.
- Über MaxMartingaleSteps erfolgt Hard Reset: alter Deficit entfällt, die nächste Order nutzt Base Lot. Maximal eine offene Position je Seite.
- D'Alembert zeigt aktuelles Level und nächsten normalisierten Lot für BUY/SELL.
- Grid zeigt Legs/Volumen, Realized inklusive Kosten, Open P&L, Cycle P&L, beim Start fixiertes Target und Remaining.
- Anchor ist die neueste bestätigte Position. BUY muss strikt unter anchor − ATR × DistanciaMinima, SELL strikt darüber liegen; Fortschritt wird in ATR gezeigt.
- Separate beendet nur den flat gewordenen Seitenzyklus; Unified endet, wenn beide Seiten flat sind. Laufende Orders verzögern Reset.
- Target löst die Schließanforderung aus; tatsächliche Exit-Provision, Gebühren und Slippage können das Endergebnis leicht darunter setzen.
- InterfaceLanguage behält 11 Sprachen. Auto nutzt English im Tester und die Terminalsprache live; nicht übersetzte Labels fallen auf English zurück.

## Kompatibilität und Grenzen

Konservative Regeln; strengere Brokergrenzen gelten vorrangig.

- Percentage und Fixed-R benötigen AtivarStop=true.
- Grid nur mit Monetary/Fixed Lot, Recovery_None und Hedging-Konto.
- Grid benötigt Take, positive DistanciaMinima und Limit mindestens zwei.
- Solange der Basket offen bleibt, zählen realisierte Verluste, Swap, Provision und Gebühren des Zyklus weiter zum noch benötigten Zielergebnis; der Gewinn eines einzelnen Legs löscht diese Kosten nicht.
- Bei Grid_SeparateProfit sind BUY- und SELL-Zyklen getrennt. Verschwinden alle Positionen einer Seite, endet deren Zyklus; ein späterer Einstieg beginnt ohne Übertrag des geschlossenen Defizits neu.
- D'Alembert nur Fixed Lot, Grid_Disabled und DAlembertStep>0.
- Martingale beachtet MaxMartingaleSteps und MaxMartingaleLot.
- OnOppositeOrder benötigt Hedging, beide Seiten und Grid aus.
- News-Backtest benötigt CSV in Common\Files.
- Zeitplan verwendet Broker-Serverzeit.
- Suffix und Symbolspezifikation je Broker prüfen.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Risikohinweis

EA, Set und historische Ergebnisse garantieren keine Zukunft. OOS und Demo validieren.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
