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
4. Mit Baseline 01–05 beginnen und BUY/SELL trennen.
5. 06 dient Ein-Achsen-Forschung.
6. 07 Einstieg, 08 Filter, 09 Risiko, 10 Ausstieg.
7. IS, OOS und Forward Demo chronologisch durchführen.
8. Status, RelativePath und SHA256 prüfen.
9. Nur explizites USE gilt für die definierte Umgebung.

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

## Risikohinweis

EA, Set und historische Ergebnisse garantieren keine Zukunft. OOS und Demo validieren.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
