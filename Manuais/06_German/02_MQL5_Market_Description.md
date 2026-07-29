# White Rabbit X — MQL5-Market-Beschreibung

Verbindliche Referenz aus aktuellem EA-Quelltext und Set-Manifest — EA 1.11 — 127 inputs — 3738 sets

## Softwarefunktion

White Rabbit X ist ein MT5-Multiindikator-EA für systematische Forschung, kontrollierte Ausführung und WFO.

Current schema: 127 inputs. Current manifest: 3738 sets.

- Zwölf native Engines: MACD, EMA Cross, Momentum, Stochastic, TRIX, RSI, CCI, Williams %R, DeMarker, MFI, OsMA und Ichimoku.
- Sieben Methoden mit expliziter AND/OR-Semantik auf geschlossener Kerze.
- Unabhängige MTF-, MA-, ADX-, ATR- und News-Filter.
- Vier PositionSizeMode und Equity/Margin-Schutz.
- Stop, Take, Breakeven, Trailing und Reversal bilden den Exit.
- Dashboard, Zeitplan, Sprachen und WFO sind integriert.

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

## Community und Downloads

Treten Sie dem offiziellen Telegram-Kanal bei: **https://t.me/MrRabbit_MT5**

Handbücher und die vollständige Set-Bibliothek: **https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- Fertige Sets pro Symbol und pro Systemtyp (SL/TP, Trailing, Grid, Martingale und weitere), so aufbereitet, dass sie direkt in den Strategietester geladen werden können.
- Handbücher in Ihrer Sprache: Portugiesisch, Englisch, Russisch, Chinesisch, Spanisch, Japanisch, Deutsch, Koreanisch, Französisch, Italienisch und Türkisch.
- Update-Hinweise zum EA und zu den Set-Bibliotheken.
- Support und Erfahrungsaustausch mit anderen Nutzern.

> Dies ist der einzige offizielle Kanal. Kaufen Sie keine Sets oder Kopien des EA von Dritten, die vorgeben, White Rabbit X zu vertreten: Der EA wird ausschließlich im MQL5 Market verkauft und die Sets werden im oben genannten Kanal kostenlos verteilt.

## Risikohinweis

EA, Set und historische Ergebnisse garantieren keine Zukunft. OOS und Demo validieren.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
