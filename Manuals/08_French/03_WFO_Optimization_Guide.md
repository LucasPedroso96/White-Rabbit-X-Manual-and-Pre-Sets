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
8. Validez le gagnant sur ticks reels : la divergence face a l'OHLC et la retention out-of-sample decident, jamais le profit in-sample. Rejetez un candidat dont le résultat en ticks réels diverge du résultat OHLC de plus de 30 % — les deux doivent s'accorder sur la forme du résultat, pas seulement sur son signe.
8a. Filtrez le survivant par Monte Carlo : rééchantillonnez la séquence de trades par bootstrap (en multiples de R, pas en devise) et rejetez si le drawdown au 95e percentile dépasse le double du drawdown observé, ou si la probabilité de ruine rééchantillonnée dépasse 5 %. Un set qui ne paraît stable qu'à cause de l'ordre particulier dans lequel ses trades se sont produits n'est pas stable.
8b. Pour les six systèmes Fixed-R (`01` à `06`), exigez une espérance en R positive hors échantillon. Un set qui a fait match nul ou perdu du R hors échantillon n'est pas promu, quel que soit son score in-sample.
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

## Formules : ce qu'elles optimisent, et ce qui rapporte le résultat

`selectedFormula` détermine ce qu'OnTester renvoie à l'optimiseur génétique — le nombre unique sur lequel un passage est classé. Ce n'est pas la même question que « dans quelle unité le set livré rapporte-t-il son résultat ». Le circuit utilise des formules différentes selon les tâches : les phases précoces privilégient des formules qui récompensent un résultat large et bien peuplé (pour que la recherche génétique ait un gradient à gravir), plutôt qu'une formule étroite qui obtient un score élevé sur un seul chemin.

Pour les six systèmes Fixed-R, le rapport final du set livré utilise **SomaR** (la somme des résultats des trades en multiples de R) : une fois qu'un candidat a déjà franchi la rétention, la divergence, le Monte Carlo et le seuil d'espérance en R ci-dessus, SomaR exprime le résultat dans la même unité que ce guide utilise par ailleurs pour comparer symboles et systèmes — le R, pas la devise. Elle ne décide pas du gagnant ; elle rapporte le résultat du gagnant déjà déterminé dans une unité comparable.

## Autobot et Historical Tool Manager

Cette bibliothèque est livrée pré-validée, mais le circuit décrit ci-dessus n'est pas une boîte noire — il est publié sous le nom **Autobot** dans le même dépôt que ce manuel (`Autobot/`), le code réel qui exécute chacune des étapes de ce guide. Lisez-le pour voir exactement comment un set a mérité son statut, ou exécutez-le vous-même contre votre propre courtier, votre liste de symboles ou votre plage de dates.

L'étape de confirmation sur ticks réels dépend de la disponibilité de données de ticks réels pour la confirmation. **Historical Tool Manager** (MQL5 Market : https://www.mql5.com/pt/market/product/188711) importe un historique profond de ticks et M1 dans MT5 sous forme de Custom Symbols, pour les instruments dont l'historique propre du courtier ne remonte pas assez loin — utile que vous exécutiez l'Autobot ou que vous vouliez simplement plus d'historique pour tester manuellement.

## Avertissement de risque

Aucun EA, set ou historique ne garantit l'avenir. Validez OOS et en démo.

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`
