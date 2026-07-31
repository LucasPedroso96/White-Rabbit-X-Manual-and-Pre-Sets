# White Rabbit X — Guide de l'écosystème de sets

Référence faisant autorité, générée depuis la source EA et le manifeste actuels — EA 1.11 — 127 inputs — 3738 sets

## Périmètre et sources de vérité

La source définit inputs, valeurs et fonctions ; le manifeste définit chaque set, statut, chemin et SHA-256. L'archive Quantum est uniquement historique.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Document généré ; les identifiants correspondent exactement à l'EA.

## Installation et premier test

Installez l'EX5 correspondant, chargez un set dans Tester Inputs, choisissez le symbole exact et vérifiez le Journal.

## Bibliothèque de sets détectée

Les nombres viennent des fichiers et du manifeste. Chaque set est une hypothèse. Counts and fingerprints were read at generation time.

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

## Statuts et décision

Le statut exact est conservé et mappé prudemment vers USE, REOPTIMIZE, RESEARCH ou HOLD.

| Système | Gestion | Sets |
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

## Flux sûr

Modifiez une matrice par étape et conservez les preuves.

1. Alignez les versions EX5, source, schéma set et manifeste.
2. Chargez la bibliothèque par Strategy Tester Inputs.
3. Mappez le symbole et le suffixe exacts.
4. Naviguez par classe et actif : chaque actif porte les 11 types de systeme (01_SLTP a 11_SIGNAL_ONLY), un set par sens (BUY/SELL ; BOTH pour le grid unifie) et deux variantes d'entree — MULTI met en concurrence les indicateurs 0–10 sur un seul axe, ICHIMOKU a son propre fichier.
5. La phase 1 est la decouverte de regions : lancez le genetique sur le set tel quel — groupe d'entree complet (indicateur, methode, timeframe, applied price, periodes), sorties du systeme et interrupteurs de filtres, tout a la fois.
6. Des les tours suivants, verrouillez (Y→N) les inputs « d'ecriture » — enums et booleens — decides par la phase precedente et ne laissez ouverts que les numeriques ; le reglage d'un filtre n'entre que si son interrupteur a survecu active.
7. Le filtre ATR d'entree (EntradaATR) n'existe que dans les systemes grid ; partout ailleurs il reste desactive par construction.
8. Validez le gagnant sur ticks reels : la divergence face a l'OHLC et la retention out-of-sample decident, jamais le profit in-sample.
9. Apres le tick reel, passez le dimensionnement en Percentage et relancez : ne promouvez que si cela passe aussi — et c'est dans ce mode que le set doit operer.

## Télémétrie des cycles du tableau

Le panneau utilise les mêmes snapshots que le calcul des lots et la clôture des paniers.

- Le rafraîchissement périodique par tick est limité à une fois par seconde ; initialisation et événements de trading peuvent rafraîchir immédiatement.
- Balance et Equity couvrent tout le compte. Closed P&L est la variation depuis OnInit ; Open P&L et positions sont actuels et filtrés par Symbol + Magic.
- Martingale affiche par BUY/SELL pertes consécutives, nombre et montant brut des pertes, recovered, deficit et target = deficit × Multiplicador.
- Dépasser MaxMartingaleSteps produit un hard reset : ancien déficit supprimé et prochain ordre au lot de base. Une position ouverte maximum par côté.
- D'Alembert affiche le niveau actuel et le prochain lot normalisé BUY/SELL.
- Grid affiche legs/volume, realized coûts compris, open P&L, cycle P&L, target figée au départ et remaining.
- Anchor est la position confirmée la plus récente. BUY exige strictement moins que anchor − ATR × DistanciaMinima, SELL strictement plus ; la progression est en ATR.
- Separate termine seulement le cycle du côté devenu flat ; Unified se termine quand les deux côtés sont flat. Les ordres en cours retardent le reset.
- Target déclenche la demande de clôture ; commission, frais et slippage de sortie peuvent laisser le résultat final légèrement inférieur.
- InterfaceLanguage conserve 11 langues. Auto utilise English dans Tester et la langue du terminal en live ; un label non traduit revient à English.

## Compatibilité et restrictions

Règles prudentes ; les limites plus strictes du courtier prévalent.

- Percentage et Fixed-R exigent AtivarStop=true.
- Grid : Monetary/Fixed Lot, Recovery_None et compte hedging uniquement.
- Grid exige take, DistanciaMinima positif et limite d'au moins deux.
- Tant que le panier reste ouvert, ses pertes réalisées, swap, commission et frais restent inclus dans le résultat requis pour atteindre la cible ; le gain isolé d'une jambe ne les efface pas.
- En Grid_SeparateProfit, les cycles BUY et SELL sont indépendants. Si toutes les positions d'un côté disparaissent, son cycle se termine ; une entrée ultérieure repart sans reporter le déficit clôturé.
- D'Alembert : Fixed Lot, Grid_Disabled et DAlembertStep>0.
- Martingale respecte MaxMartingaleSteps et MaxMartingaleLot.
- OnOppositeOrder exige hedging, deux côtés et grid désactivé.
- Le backtest news exige le CSV dans Common\Files.
- L'horaire utilise l'heure serveur.
- Validez suffixe et spécifications chez chaque courtier.

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## Avertissement de risque

Aucun EA, set ou historique ne garantit l'avenir. Validez OOS et en démo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
