---
paths:
  - "app/routers/of_import.py"
  - "app/services/of_pdf_generator.py"
  - "app/routers/fabrication.py"
  - "app/routers/produits_memoire.py"
  - "app/routers/ao.py"
  - "app/web/fabrication_page.py"
  - "app/web/ao_page.py"
---
## OF et fiches techniques — qui a le dernier mot

Trois sources écrivent dans `of_imports` et `fiches_techniques` : le pont Access
(`scripts/access_sync_of.py`, `scripts/access_sync_fiches.py` → `/api/bridge/*`),
les humains qui corrigent (import d'un PDF d'OF, modale MySifa), et depuis le
04/09/2026 la CRÉATION dans MySifa (`POST /api/of`, `POST /api/fiches-techniques`).
Le déstockage de production lit ces deux tables. Un arbitrage faux ne se voit
pas : il sort à l'inventaire, des semaines plus tard.

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

**Un document créé dans MySifa** (`source = 'mysifa'`) part avec tous ses champs
saisis dans `champs_manuels` et `valide = 0`. Les deux vont ensemble : le
marquage dit à Access de ne pas réécrire ce qu'un humain vient d'écrire, et
`valide = 0` dit que créer n'est pas relire. Un OF saisi ici entre donc dans le
même circuit de contrôle qu'un OF importé — c'est le service ADV qui le valide,
et le verrou de déstockage s'applique pareil.

`source` vaut `access`, `pdf` ou `mysifa`. Un OF sans PDF n'est plus forcément
un OF venu d'Access : ne pas déduire l'origine de `pdf_filename`.

**Le numéro d'un OF créé dans MySifa se PROPOSE, il ne s'invente pas.** Il suit
la règle des dossiers de fabrication — `rvgi_rattachement.proposer_reference()`
à partir des commandes rattachées : « 9932128 », « 9932128/L1-3 »,
« 9932128+129 ». Un OF peut couvrir une commande entière, quelques-unes de ses
lignes ou plusieurs commandes ; c'est l'ADV qui arbitre, parce qu'elle seule
sait ce qui part sur la même bobine. Le rattachement vit dans
`rvgi_rattachements` avec `objet = 'of'`, et l'état retombe sur
`of_imports.cmd_rvgi` / `.rvgi_etat`, exactement comme `dos_rvgi` sur un dossier.

Un rattachement d'OF ne compte PAS dans `deja_couvertes()` : l'OF pointe la même
ligne de commande que le dossier qui en sort, et le compter ferait naître en
« Reliquat » le premier dossier issu de cet OF.

**Le lien fiche technique ↔ article RVGI est stocké**, dans `article_code1` /
`article_code2`. La référence d'une fiche (« 1026/0020 ») EST le couple
code1/code2 d'un article — on pourrait donc le relire à chaque affichage, mais
une référence corrigée ferait alors glisser la fiche d'un article à l'autre
sans que personne l'ait décidé. On résout une fois, à la création, et on écrit.
Ce que `gpr_ff` (la fiche de fabrication de RVGI) apporte est PROPOSÉ dans les
cases vides, jamais imposé : SIFA a cessé d'alimenter ce module en avril 2026.

**Ce qu'il ne faut pas faire**

- ❌ `UPDATE of_imports SET ...` ou `UPDATE fiches_techniques SET ...` en direct
- ❌ Rendre `valide` modifiable par un endpoint de mise à jour de données
- ❌ Ignorer un conflit en silence : un désaccord Access / MySifa se remonte
- ❌ Créer un OF ou une fiche sans marquer les champs saisis (`marquer_champs_manuels`)
- ❌ Poser `valide = 1` à la création
- ❌ Fabriquer un numéro d'OF côté client : la règle vit dans `proposer_reference()`

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

## Le modèle vierge de l'OF — `data/of_template.pdf`

Un OF sans PDF (venu d'Access, ou saisi dans MySifa) s'imprime en posant ses
valeurs sur `data/of_template.pdf` : l'OF réel de l'atelier dont toutes les
valeurs ont été retirées, le cadre, les libellés et les aplats de couleur
conservés. `app/services/of_pdf_generator.py` porte, case par case, les
coordonnées relevées sur le document d'origine — ce ne sont pas des réglages
esthétiques, les déplacer sort le texte de sa case.

Le modèle est en **A4** (595,28 × 841,92). La première version du générateur
supposait du US Letter : 46 points de décalage cumulés en bas de page.

Piège : `merge_page` colle la surcouche à la suite du flux du modèle, qui finit
par « … W* n Q » sans retour à la ligne. Collé au « Q » qu'ouvre pypdf, cela
donne l'opérateur « QQ », que ne connaît aucun lecteur — et la page s'affiche
alors SANS aucune valeur, sans la moindre erreur côté serveur.
`_terminer_le_flux()` ajoute l'octet manquant. Refaire le modèle un jour sans
cette précaution redonnerait le même symptôme, très difficile à relier à sa
cause.

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
