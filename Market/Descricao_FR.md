# White Rabbit X

Douze moteurs d'entrée natifs. Onze architectures de sortie. Un Expert Advisor.

La plupart des EA livrent une stratégie fermée. Celui-ci livre l'atelier : vous choisissez le moteur de signal, le squelette de gestion et les filtres, et le walk-forward intégré vous dit si le résultat tient hors échantillon.

## Douze moteurs d'entrée, tous natifs

MACD · EMA Cross · Momentum · Stochastic · TRIX · RSI · CCI · Williams %R · DeMarker · MFI · OsMA · Ichimoku

Tous sont des indicateurs natifs de MetaTrader : rien à installer, rien qui casse à la prochaine mise à jour du terminal.

Ichimoku lit les cinq tampons : le déclencheur de référence est la cassure du nuage (Kumo), pas un croisement Tenkan/Kijun, et la Chikou sert de filtre de confirmation. Le Stochastique expose le lissage, la méthode de moyenne et le champ de prix Low/High ou Close/Close — les trois paramètres que la plupart des EA figent dans le code.

Trois types de déclencheur se combinent en sept méthodes d'entrée.

## Onze architectures de sortie

SL/TP · objectif organique · trailing seul · SL/TP avec trailing · seuil de rentabilité et trailing · sortie sur retournement · grille séparée · grille unifiée · martingale · D'Alembert · signal seul.

Le squelette de gestion est votre choix, pas une partie figée de la stratégie.

## Walk-forward intégré à l'EA

Ce n'est pas l'onglet Forward du testeur. L'EA découpe la période en fenêtres in-sample et out-of-sample et, en mode optimisation, ne trade que l'in-sample : l'algorithme génétique ne voit jamais les données sur lesquelles il sera jugé.

Trois modes de fenêtre : séquentiel, glissant (le classique — environ trois fois plus de cycles sur le même historique) et ancré.

Le rapport donne la Walk Forward Efficiency par cycle, avec moyenne et écart-type. Un EA qui rend 70% à chaque cycle et un autre qui rend 200% une fois et −20% le reste ont la même moyenne ; seul le premier est robuste, et c'est la dispersion qui les sépare.

## Risque mesuré en R

Le mode Fixed-R dimensionne chaque position pour risquer exactement 1R, calculé sur un capital de base fixe et non sur le solde courant. Les résultats deviennent comparables entre instruments, comptes et tests : +40R sur l'or et +40R sur EURUSD veulent dire la même chose, alors que « +3 200 USD » ne veut rien dire sans le lot et le solde.

Quinze critères d'optimisation, dont un score composite qui renvoie zéro en dessous de trente trades — ce qui écarte à lui seul le classique « gagnant » bâti sur trois trades chanceux.

## Une protection qui agit avant l'ordre

Perte journalière maximale, plafond de drawdown sur le capital, marge libre minimale, limite de spread, fenêtres de session et de jours, et filtre d'actualités avec cache CSV pour le backtest. Les distances de freeze level et de stops level sont vérifiées avant chaque requête, si bien que le journal reste lisible au lieu de se remplir de refus du courtier.

## Panneau sur le graphique

Stratégie, indicateur et paramètres actifs, capital du compte et de l'EA, P&L clôturé, latent et net, positions ouvertes et — sous martingale, D'Alembert ou grille — le cycle en cours : pertes consécutives, déficit en cours, montant récupéré, objectif, ordres, ancre et espacement ATR.

Interface en onze langues.

## Ce qui est fourni

- Expert Advisor pour MetaTrader 5 — 136 paramètres documentés
- 3 738 fichiers .set prêts : 89 actifs × 11 systèmes × les deux sens
- Installateur automatique : trouve votre terminal, copie les sets et les adapte au suffixe de symbole et au lot minimum de votre courtier
- Manuel, guide WFO, référence des paramètres, tutoriel des sets et FAQ en onze langues
- Support et mises à jour via le canal officiel

## Avant d'acheter

Ceci est un cadre de recherche, pas un signal à activer puis oublier. Chaque set est une hypothèse : il demande optimisation, validation hors échantillon et forward-demo avant l'argent réel.

Grille, martingale et D'Alembert changent la nature de la courbe de risque. La grille exige un compte de couverture réel.

Aucun Expert Advisor, preset ou résultat historique ne garantit les performances futures.

---

Canal officiel : https://t.me/MrRabbit_MT5 — bibliothèque de sets gratuite, manuels dans votre langue et avis de mise à jour. L'EA est vendu uniquement ici sur le MQL5 Market ; les sets sont distribués gratuitement sur ce canal et nulle part ailleurs.
