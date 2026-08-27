---
paths:
  - "app/routers/of_import.py"
  - "app/routers/fabrication.py"
  - "app/routers/produits_memoire.py"
  - "app/routers/ao.py"
  - "app/web/fabrication_page.py"
  - "app/web/ao_page.py"
---
## OF et fiches techniques — qui a le dernier mot

Deux sources écrivent dans `of_imports` et `fiches_techniques` : le pont Access
(`scripts/access_sync_of.py`, `scripts/access_sync_fiches.py` → `/api/bridge/*`)
et les humains (import d'un PDF d'OF, correction dans une modale MySifa). Le
déstockage de production lit ces deux tables. Un arbitrage faux ne se voit pas :
il sort à l'inventaire, des semaines plus tard.

**Deux règles, arbitrées au niveau du CHAMP.**

1. Le document le plus récent fait foi.
2. Sauf sur une valeur saisie par un humain.

Au niveau du document ces deux règles se contredisent, et c'est ce qui donnait
deux comportements opposés selon la table (avant le 7 août 2026) : un OF portant
un PDF était gelé en entier — une quantité corrigée dans Access n'arrivait
jamais — tandis qu'une fiche technique était intégralement écrasée à chaque
sync, correction atelier comprise, sans trace. Au niveau du champ, les deux
règles tiennent ensemble.

Tout passe désormais par **`app/services/documents_verite.py`**. Aucun autre
chemin ne doit écrire dans ces deux tables.

- `appliquer_maj(...)` — écriture arbitrée. `proteger_manuels` refuse
  d'écraser une colonne listée dans `champs_manuels` (JSON) et journalise le
  refus ; `marquer_manuels` ajoute les colonnes écrites à cette liste ;
  `seulement_vides` reproduit `enrich_if_exists` ; `autoriser_effacement` n'est
  vrai que pour une saisie humaine — un `None` venu d'Access est presque
  toujours une jointure vide, pas une décision.
- `constater_remplacement(...)` — pour l'import d'un PDF d'OF, qui réécrit la
  ligne d'un bloc. On n'arbitre pas ce geste, on en tire les conséquences.

**La validation se périme.** Toute écriture sur un champ de
`CHAMPS_CALCUL_OF` / `CHAMPS_CALCUL_FT` remet `valide` à 0, efface `valide_par`
et renseigne `invalide_motif`. Sans cela le verrou de déstockage atteste d'une
relecture qui a bien eu lieu — mais pas sur les valeurs qui serviront au calcul.
Corriger n'est pas relire : une correction humaine dévalide au même titre
qu'une modification Access.

`reference` et `machine` sont dans les champs de calcul bien qu'ils ne soient
pas des quantités : ce sont eux qui décident QUELLE fiche technique est
rapprochée du dossier.

**Tout est journalisé** dans `documents_valeurs_historique` (avant, après,
origine, auteur, `etait_valide`, `refuse`). Un mouvement de déstockage porte en
plus `mp_mouvements.of_import_id` et `.fiche_id` : le dossier seul ne suffit
pas, il change d'OF et une fiche se modifie.

**Ce qu'il ne faut pas faire**

- ❌ `UPDATE of_imports SET ...` ou `UPDATE fiches_techniques SET ...` en direct
- ❌ Rendre `valide` modifiable par un endpoint de mise à jour de données
- ❌ Ignorer un conflit en silence : un désaccord Access / MySifa se remonte

**Vérifier l'état d'une base**

```bash
python scripts/audit_documents_validation.py --db data/production.db
```

Sections 3 et 4 du rapport doivent rester vides. Une ligne en section 3 (document
validé malgré un changement postérieur) signale un chemin d'écriture qui
court-circuite le service.

Tests : `python3 tests/test_documents_verite.py` (arbitrage, péremption,
journal) et `python3 tests/test_besoins_verrou_documents.py` (SQL réelle de
Besoins matières + blocage du déstockage).

---

## Nombre de fronts — `outil1_nb_front`, jamais `mod_nb_front`

Le nombre de fronts est au **dénominateur** du métrage :

    métrage = qte_étiquettes ÷ nb_fronts × mod_longueur ÷ 1000

S'y tromper d'un facteur 18 multiplie le besoin en frontal par 18.

**Constat du 7 août 2026, base de production :** `mod_nb_front` vaut 1 sur
**878 fiches sur 909**. Ce n'est pas une valeur, c'est un champ que personne ne
remplit. Le vrai nombre de fronts est `outil1_nb_front` — les poses de l'outil
de découpe — confirmé par la géométrie sur **868 fiches sur 909**.

Conséquence avant correction : les 585 OF sans métrage (sur 745) passaient par
le repli géométrique et sortaient un besoin surestimé d'un facteur égal au vrai
nombre de fronts. Un dossier est ressorti à **55 823 km de frontal**, dix fois
le total d'un mois entier.

`app/services/coherence_fiche.py` porte les deux fonctions :

- `nb_fronts(ft, laize_of)` — la valeur à utiliser et sa provenance. Ordre :
  `outil1_nb_front`, puis `mod_nb_front` s'il est > 1, puis la géométrie.
- `controler(ft, laize_of)` — vérifie que la fiche boucle, et chiffre le
  facteur d'erreur.

**L'identité qui rend le contrôle possible**, et qui ne demande aucune source
extérieure :

    nb_fronts ≈ laize_bobine ÷ laize_module

La laize de l'OF prime sur celle de la fiche : c'est la bobine réellement
montée. `eti_laize` est la largeur de l'ÉTIQUETTE, jamais celle de la bobine —
les confondre redonne un nombre de fronts de 1.

`GET /api/stock/besoins-matieres/fiches-incoherentes` liste les fiches à
corriger, classées par facteur d'erreur puis par nombre de dossiers concernés.

**On ne corrige jamais d'office.** Une fiche fausse se répare dans Access, à la
source. Compenser en silence à chaque lecture cacherait le problème pendant que
les commandes continuent de partir de travers.

Test : `python3 tests/test_coherence_fiche.py` (fiches réelles relevées en
production).

---
