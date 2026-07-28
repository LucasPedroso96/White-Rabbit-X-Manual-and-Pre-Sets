# White Rabbit X

Zwölf native Einstiegs-Engines. Elf Ausstiegs-Architekturen. Ein Expert Advisor.

Die meisten EAs liefern eine fertige Strategie. Dieser liefert die Werkstatt: Sie wählen Signal-Engine, Management-Gerüst und Filter, und der eingebaute Walk-Forward zeigt Ihnen, ob das Ergebnis außerhalb der Stichprobe standhält.

## Zwölf Einstiegs-Engines, alle nativ

MACD · EMA Cross · Momentum · Stochastic · TRIX · RSI · CCI · Williams %R · DeMarker · MFI · OsMA · Ichimoku

Alle sind native MetaTrader-Indikatoren: nichts zu installieren, nichts das beim nächsten Terminal-Update bricht.

Ichimoku liest alle fünf Puffer: Das Referenzsignal ist der Ausbruch aus der Wolke (Kumo), nicht eine Tenkan/Kijun-Kreuzung, und die Chikou-Linie steht als Bestätigungsfilter bereit. Stochastik legt Glättung, Mittelungsmethode und das Preisfeld Low/High oder Close/Close offen — die drei Parameter, die die meisten EAs fest im Code halten.

Drei Auslösertypen ergeben sieben Einstiegsmethoden.

## Elf Ausstiegs-Architekturen

SL/TP · organisches Ziel · nur Trailing · SL/TP mit Trailing · Break-even und Trailing · Ausstieg bei Umkehr · getrenntes Grid · vereinheitlichtes Grid · Martingale · D'Alembert · nur Signal.

Das Management-Gerüst ist Ihre Wahl, kein fester Bestandteil der Strategie.

## Walk-Forward im EA selbst

Nicht der Forward-Reiter des Testers. Der EA teilt den Zeitraum in In-Sample- und Out-of-Sample-Fenster und handelt im Optimierungsmodus ausschließlich das In-Sample — der genetische Algorithmus sieht die Daten nie, an denen er gemessen wird.

Drei Fenstermodi: sequenziell, rollierend (der klassische — etwa dreimal so viele Zyklen aus derselben Historie) und verankert.

Der Bericht liefert die Walk Forward Efficiency je Zyklus, mit Mittelwert und Standardabweichung. Ein EA mit 70% in jedem Zyklus und einer mit 200% in einem und −20% im Rest haben denselben Mittelwert; robust ist nur der erste, und unterscheiden lassen sie sich an der Streuung.

## Risiko in R gemessen

Fixed-R bemisst jede Position so, dass ein Trade genau 1R riskiert, berechnet auf einem festen Basiskapital statt auf dem laufenden Kontostand. Ergebnisse werden über Symbole, Konten und Testläufe hinweg vergleichbar: +40R auf Gold und +40R auf EURUSD bedeuten dasselbe, während „+3.200 USD“ ohne Lot und Kontostand nichts aussagt.

Fünfzehn Optimierungskriterien, darunter ein zusammengesetzter Score, der unterhalb von dreißig Trades null zurückgibt — das allein verwirft den klassischen „Gewinner“, der auf drei glücklichen Trades beruht.

## Schutz, der vor der Order greift

Maximaler Tagesverlust, Drawdown-Obergrenze, minimale freie Margin, Spread-Limit, Sitzungs- und Wochentagsfenster sowie ein Nachrichtenfilter mit CSV-Cache für Backtests. Freeze-Level und Stops-Level werden vor jeder Anfrage geprüft, sodass das Log lesbar bleibt und sich nicht mit Broker-Ablehnungen füllt.

## Chart-Panel

Strategie, Indikator und aktive Parameter, Konto- und EA-Kapital, geschlossenes, laufendes und Netto-P&L, offene Positionen und — bei Martingale, D'Alembert oder Grid — der laufende Zyklus: aufeinanderfolgende Verluste, offenes Defizit, aufgeholter Betrag, Ziel, Teilorders, Anker und ATR-Abstand.

Oberfläche in elf Sprachen.

## Im Lieferumfang

- Expert Advisor für MetaTrader 5 — 136 dokumentierte Parameter
- 3.738 fertige Set-Dateien: 89 Symbole × 11 Systeme × beide Richtungen
- Automatischer Installer: findet Ihr Terminal, kopiert die Sets und passt sie an Symbol-Suffix und Mindestlot Ihres Brokers an
- Handbuch, WFO-Leitfaden, Parameterreferenz, Set-Tutorial und FAQ in elf Sprachen
- Support und Updates über den offiziellen Kanal

## Vor dem Kauf

Dies ist ein Forschungsrahmen, kein Signal zum Einschalten und Vergessen. Jedes Set ist eine Hypothese: Es braucht Optimierung, Out-of-Sample-Validierung und Forward-Demo vor echtem Geld.

Grid, Martingale und D'Alembert verändern die Natur der Risikokurve. Grid setzt ein echtes Hedging-Konto voraus.

Kein Expert Advisor, kein Preset und kein historisches Ergebnis garantiert künftige Performance.

---

Offizieller Kanal: https://t.me/MrRabbit_MT5 — kostenlose Set-Bibliothek, Handbücher in Ihrer Sprache und Update-Hinweise. Der EA wird ausschließlich hier im MQL5 Market verkauft; die Sets werden kostenlos in diesem Kanal und nirgendwo sonst verteilt.
