---
paths:
  - "app/routers/besoins_matieres.py"
  - "app/services/**/*carnet*"
  - "app/services/**/*besoin*"
---
## Prévision des besoins matières — pourquoi on photographie le carnet

**Ne pas supprimer `carnet_snapshots` sous prétexte qu'elle ne sert à rien.**
Elle ne servira à rien jusqu'à novembre 2026, et c'est exactement pourquoi elle
existe depuis août.

Prévoir la consommation matière à 3-4 mois ne consiste pas à extrapoler une
courbe. Sur cet horizon, une partie du besoin est déjà connue — les dossiers au
planning livrés dans la fenêtre, que Besoins matières chiffre exactement. Ce
qui reste à estimer, c'est le **remplissage** :

    prévision(M+k) = besoin_connu(M+k) ÷ p(k)

où p(k) est la part du volume final déjà visible k mois à l'avance.

p(k) se mesure — mais seulement si l'on sait ce que le carnet contenait à une
date passée. Or `planning_entries` ne garde que le présent : au 7 août 2026,
ses 295 dossiers avaient TOUS été créés dans les quatre mois précédents. Un
dossier terminé quitte la fenêtre et emporte la trace de ce qu'il pesait.

Diagnostic reproductible :

```bash
python scripts/diag_previsions_matieres.py --db data/production.db
```

D'où `app/services/carnet_snapshot.py` : une photo par jour du besoin calculé,
par mois de livraison et par matière. Déclenchée par la consultation de Besoins
matières (l'écran est ouvert chaque jour ouvré), idempotente, best-effort — son
échec ne doit jamais empêcher l'affichage.

Deux points de conception à ne pas défaire :

- **On stocke le besoin CALCULÉ, pas les dossiers.** C'est la grandeur à
  prédire, et elle survit à la suppression du dossier qui l'a produite.
- **`nb_incalculables` compte à part les besoins non chiffrables.** Un carnet
  dont les OF n'ont pas de métrage ressemble trait pour trait à un carnet vide ;
  sans ce compteur on calibrerait sur une pénurie de données en croyant
  calibrer sur une pénurie de commandes.

`GET /api/stock/besoins-matieres/carnet/couverture` dit où en est
l'accumulation et quels horizons sont calibrables. Tant que
`horizons_calibrables` est vide, aucun modèle fondé sur le remplissage n'est
honnête — l'écran doit le dire plutôt qu'afficher un chiffre.

L'historique antérieur (2022 → 2026) n'est pas dans la base : il vit dans le
classeur « Point Besoin des commandes ». Deux feuilles complémentaires dans le
temps — « analyse Eugene » (2022 et 2026) et « Controle dossier » (2023-09 à
2025-12) — à dédoublonner par numéro d'OF, avec deux définitions différentes du
métrage (théorique d'un côté, utilisé de l'autre, plus une colonne
`Surconsommation`).

Test : `python3 tests/test_carnet_snapshot.py`.

---
