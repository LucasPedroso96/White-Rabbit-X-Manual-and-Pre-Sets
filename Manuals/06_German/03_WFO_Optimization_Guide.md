# White Rabbit X — WFO-Optimierungsleitfaden

Verbindliche Referenz aus aktuellem EA-Quelltext und Set-Manifest — EA 1.11 — 127 inputs — 3738 sets

**Auf das Datum achten.** Bei aktiviertem WFO vergleicht OnTester das tatsächliche Testende mit input_end_date und liefert null zurück, wenn der Test früher endete (Toleranz 80 Stunden). Ein falsches Datum setzt jeden Durchlauf auf null und die gesamte Optimierung wirkt defekt. Setzen Sie input_end_date auf dasselbe Enddatum, das im Strategietester konfiguriert ist.

## Umfang und Wahrheitsquellen

Der EA-Quelltext definiert Inputs, Defaults und Funktionen; das Manifest jedes Set, Status, Pfad und SHA-256. Das alte Quantum-Archiv ist nur historisch.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Generiertes Material; Parameternamen entsprechen exakt dem EA.

## Walk-forward-Methode

Chronologische IS-, OOS- und Forward-Demo-Phasen mit realistischem Spread, Provision, Swap und Slippage.

## Sicherer Ablauf

Pro Stufe nur eine Matrix ändern und Nachweise aufbewahren.

1. Version von EX5, Quelle, Set-Schema und Manifest abgleichen.
2. Bibliothek über Strategy Tester Inputs laden.
3. Exaktes Brokersymbol und Suffix zuordnen.
4. Navigieren Sie nach Klasse und Asset: Jedes Asset umfasst die 11 Systemtypen (01_SLTP bis 11_SIGNAL_ONLY), einen Set pro Seite (BUY/SELL; BOTH beim vereinigten Grid) und zwei Einstiegsvarianten — MULTI lässt die Indikatoren 0–10 auf einer Achse antreten, ICHIMOKU hat eine eigene Datei.
5. Phase 1 ist Regionssuche: Starten Sie die genetische Optimierung mit dem Set wie geliefert — komplette Einstiegsgruppe (Indikator, Methode, Timeframe, applied price, Perioden), die Ausstiege des Systems und die Filterschalter, alles auf einmal.
6. Ab den folgenden Runden sperren Sie (Y→N) die »Schrift«-Inputs — Enums und Booleans — aus der Vorphase und lassen nur die numerischen offen; die Feinabstimmung eines Filters kommt nur hinein, wenn sein Schalter eingeschaltet überlebt hat.
7. Der ATR-Einstiegsfilter (EntradaATR) existiert nur in den Grid-Systemen; überall sonst bleibt er konstruktionsbedingt aus.
8. Validieren Sie den Gewinner mit echten Ticks: Es entscheiden die Divergenz gegen OHLC und die Out-of-Sample-Retention, nie der In-Sample-Gewinn. Verwerfen Sie einen Kandidaten, dessen Echt-Tick-Ergebnis um mehr als 30 % vom OHLC-Ergebnis abweicht — beide sollten in der Form des Ergebnisses übereinstimmen, nicht nur im Vorzeichen.
8a. Prüfen Sie den Überlebenden per Monte Carlo: Resampeln Sie die Trade-Sequenz per Bootstrap (in R-Vielfachen, nicht in Währung) und verwerfen Sie, wenn der Drawdown im 95. Perzentil den beobachteten Drawdown um mehr als das Doppelte übersteigt oder wenn die resampelte Ruin-Wahrscheinlichkeit 5 % übersteigt. Ein Set, das nur wegen der konkreten Reihenfolge seiner Trades stabil aussieht, ist nicht stabil.
8b. Verlangen Sie für die sechs Fixed-R-Systeme (`01` bis `06`) eine positive Out-of-Sample-R-Erwartung. Ein Set, das außerhalb der Stichprobe nur ausgeglichen war oder R verloren hat, wird unabhängig vom In-Sample-Ergebnis nicht befördert.
9. Nach dem Echt-Tick-Lauf stellen Sie die Positionsgröße auf Percentage um und testen erneut: Nur bei Bestehen befördern — und genau in diesem Modus soll der Set handeln.

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

> Dieser Abschnitt ist derzeit nur auf Englisch verfügbar.

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

Deshalb speichert der Ablauf einen genehmigten Set erst, nachdem der finale Lauf im Percentage-Modus wiederholt wurde: Hält das Ergebnis dem Zinseszins nicht stand, war es nicht reif — und der validierte Set wird in genau diesem Modus ausgeliefert.

## Formeln: wofür sie optimieren und was das Ergebnis meldet

`selectedFormula` legt fest, was OnTester an den genetischen Optimierer zurückgibt — die einzige Zahl, nach der ein Durchlauf eingestuft wird. Das ist nicht dieselbe Frage wie „in welcher Einheit meldet das gelieferte Set sein Ergebnis". Der Ablauf verwendet unterschiedliche Formeln für unterschiedliche Aufgaben: frühere Phasen bevorzugen Formeln, die ein breites, gut besetztes Ergebnis belohnen (damit die genetische Suche einen Gradienten zum Erklimmen hat), statt einer engen Formel, die nur auf einem bestimmten Pfad hoch punktet.

Für die sechs Fixed-R-Systeme verwendet der finale Bericht des gelieferten Sets **SomaR** (die Summe der Trade-Ergebnisse in R-Vielfachen): Sobald ein Kandidat Retention, Divergenz, Monte Carlo und das oben genannte R-Erwartungs-Gate bereits bestanden hat, drückt SomaR das Ergebnis in derselben Einheit aus, die dieser Leitfaden sonst zum Vergleich von Symbolen und Systemen verwendet — R, nicht Währung. Es entscheidet nicht über den Gewinner; es meldet das Ergebnis des bereits ermittelten Gewinners in einer vergleichbaren Einheit.

## Autobot und Historical Tool Manager

Diese Bibliothek wird vorvalidiert ausgeliefert, aber der oben beschriebene Ablauf ist keine Black Box — er ist als **Autobot** im selben Repository veröffentlicht, in dem dieses Handbuch liegt (`Autobot/`), der tatsächliche Code, der jeden Schritt dieses Leitfadens ausführt. Lesen Sie ihn, um genau zu sehen, wie ein Set seinen Status verdient hat, oder führen Sie ihn selbst gegen Ihren eigenen Broker, Ihre Symbolliste oder Ihren Datumsbereich aus.

Die Echt-Tick-Bestätigungsstufe hängt davon ab, dass echte Tickdaten zum Abgleich vorhanden sind. **Historical Tool Manager** (MQL5 Market: https://www.mql5.com/pt/market/product/188711) importiert tiefe Tick- und M1-Historie als Custom Symbols in MT5 für Instrumente, deren eigene Broker-Historie nicht weit genug zurückreicht — nützlich, egal ob Sie den Autobot betreiben oder einfach nur mehr Historie zum manuellen Testen möchten.

## Risikohinweis

EA, Set und historische Ergebnisse garantieren keine Zukunft. OOS und Demo validieren.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
