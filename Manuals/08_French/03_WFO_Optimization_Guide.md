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
4. Naviguez par classe et actif : chaque actif porte les 11 types de systeme (01_SLTP a 11_SIGNAL_ONLY), un set par sens (BUY/SELL ; BOTH pour le grid unifie) et deux variantes d'entree — MULTI met en concurrence les indicateurs 0–10 sur un seul axe, ICHIMOKU a son propre fichier.
5. La phase 1 est la decouverte de regions : lancez le genetique sur le set tel quel — groupe d'entree complet (indicateur, methode, timeframe, applied price, periodes), sorties du systeme et interrupteurs de filtres, tout a la fois.
6. Des les tours suivants, verrouillez (Y→N) les inputs « d'ecriture » — enums et booleens — decides par la phase precedente et ne laissez ouverts que les numeriques ; le reglage d'un filtre n'entre que si son interrupteur a survecu active.
7. Le filtre ATR d'entree (EntradaATR) n'existe que dans les systemes grid ; partout ailleurs il reste desactive par construction.
8. Validez le gagnant sur ticks reels : la divergence face a l'OHLC et la retention out-of-sample decident, jamais le profit in-sample.
9. Apres le tick reel, passez le dimensionnement en Percentage et relancez : ne promouvez que si cela passe aussi — et c'est dans ce mode que le set doit operer.

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

> Cette section n'est pour l'instant disponible qu'en anglais.

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

C'est pourquoi le circuit n'enregistre un set approuve qu'apres avoir repete la passe finale en mode Percentage : si le resultat ne tient pas sous interets composes, il n'etait pas pret — et le set valide est livre dans ce mode.

## Avertissement de risque

Aucun EA, set ou historique ne garantit l'avenir. Validez OOS et en démo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
