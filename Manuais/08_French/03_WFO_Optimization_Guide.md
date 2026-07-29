# White Rabbit X — Guide d'optimisation WFO

Référence faisant autorité, générée depuis la source EA et le manifeste actuels — EA 1.11 — 127 inputs — 3738 sets

**Attention à la date.** Avec le WFO activé, OnTester compare la fin réelle du test à input_end_date et renvoie zéro si le test s'est terminé plus tôt (tolérance de 80 heures). Une date erronée met toutes les passes à zéro et l'optimisation entière semble cassée. Réglez input_end_date sur la même date de fin que celle configurée dans le Testeur de Stratégies.

## Périmètre et sources de vérité

La source définit inputs, valeurs et fonctions ; le manifeste définit chaque set, statut, chemin et SHA-256. L'archive Quantum est uniquement historique.

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

Document généré ; les identifiants correspondent exactement à l'EA.

## Méthode walk-forward

Utilisez IS, OOS et forward démo chronologiques avec spread, commission, swap et slippage réalistes.

## Flux sûr

Modifiez une matrice par étape et conservez les preuves.

1. Alignez les versions EX5, source, schéma set et manifeste.
2. Chargez la bibliothèque par Strategy Tester Inputs.
3. Mappez le symbole et le suffixe exacts.
4. Commencez par les baselines 01–05, BUY/SELL séparés.
5. 06 sert à la recherche mono-axe.
6. 07 entrée, 08 filtres, 09 risque, 10 sorties.
7. Exécutez IS, OOS et forward démo chronologiques.
8. Contrôlez Status, RelativePath et SHA256.
9. Seul USE explicite autorise l'environnement défini.

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

## Avertissement de risque

Aucun EA, set ou historique ne garantit l'avenir. Validez OOS et en démo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
