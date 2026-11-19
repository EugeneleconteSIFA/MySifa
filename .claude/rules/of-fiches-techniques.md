---
paths:
  - "app/routers/of_import.py"
  - "app/services/of_pdf_generator.py"
  - "app/services/rvgi_article_fiche.py"
  - "app/services/fiche_choix.py"
  - "app/services/of_depuis_fiche.py"
  - "scripts/access_sync_fiches.py"
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

Un numéro PROPOSÉ déjà porté par un autre OF reçoit un suffixe : « 9932128/L1 (2) », puis « (3) » (`numero_of_libre()`). C'est le cas de deux OF qui se partagent une ligne : la quantité n'entre pas dans le numéro. Parenthèses et pas tiret, qui se lirait comme une plage de lignes. Un numéro TAPÉ par l'ADV n'est jamais suffixé : son doublon reste refusé (409).

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
- ❌ Laisser le client écrire la colonne texte d'un champ matière : elle découle de l'id
- ❌ Ouvrir la modale OF sur une ligne de `/api/of/list`

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

## Les champs matière pointent une RÉFÉRENCE, pas un texte

Six familles — support, glassine, adhésif, carton, mandrin, palette — sont des
matières de MyStock, pas des libellés. Elles portent donc un id
(`*_ref_id` sur `of_imports` et `fiches_techniques`) et la colonne texte en
DÉCOULE : `_appliquer_references()` la réécrit côté serveur depuis
`matieres_premieres.designation`. Laisser le client poster les deux, c'est
accepter qu'ils divergent le jour où une désignation change dans MyStock.

Ce que ça remplace : `mp_fiche_mapping`, qui rapprochait APRÈS COUP un texte
libre d'une référence. Il reste — les documents venus d'Access n'ont que du
texte — mais un document saisi dans MySifa n'a plus besoin de lui. Une frappe
près (« ITASA KA » contre « ITASA jaune KA ») suffisait à faire sortir un
besoin matière faux, et l'erreur se voyait à l'inventaire, pas à l'écran.

**Un OF créé depuis une fiche imprime le libellé de la fiche** (décision du
18/11/2026, comparaison aux OF Access) : « THERMIQUE PRO », pas « Thermique Pro
70 g/m² ». `of_proposition.libelles_de_la_fiche()` passe après
`_appliquer_references()`, côté serveur, pour chaque matière dont l'OF porte la
référence de la fiche. L'id reste posé : besoins matières et déstockage le
lisent. Une matière changée à la main garde sa désignation MyStock.

**Une correction de l'ADV reste sur l'OF** (décision du 18/11/2026).
`of_imports.champs_corriges` liste les cases corrigées à la main ; `champs_manuels`
ne peut pas servir, il marque tout à la création. Les calculs partent de la fiche
vue à travers l'OF (`of_proposition.fiche_selon_of`). Étiquettes, bobines et levées
forment une chaîne : la dernière corrigée mène les deux autres. Une correction ne
modifie jamais la fiche technique. Les écarts avec la fiche et les incohérences de
l'OF (`controler_coherence`) se montrent avant d'enregistrer mais ne bloquent pas.
Changer de fiche ou de commande remet l'OF à zéro (`ofeViderOF`) : une
autre fiche ou une autre commande, c'est un autre OF. Une confirmation annonce
ce qui serait perdu (corrections, cases libres, écarts).
Le panneau « Modifications et points à relire » tient le journal des cases
changées à la main (valeur d'avant → valeur actuelle, heure) ; chaque ligne
s'annule : retour à la fiche, au calcul, ou à la commande pour la chaîne
étiquettes / bobines / levées, et tout ce qui en dépend se recalcule.
**Fronts et qté au mille** (19/11/2026) : la qté au mille de la fiche vaut
pour SON outil. Corriger les fronts la ramène à proportion
(`qte_au_mille_selon_fronts` : 890/0017, 31,9 à 4 fronts = 25,5 à 5), et le
métrage suit. Une qté au mille corrigée à la main prime. L'écran n'envoie pas
la valeur posée par le calcul (`m._qamCalcule`), sinon elle figerait l'ancien
nombre de fronts.

**Palettes** (19/11/2026) : `nb_palettes` = ⌈ cartons ÷ (cartons au sol ×
cartons en hauteur de la fiche) ⌉, calculées comme les autres quantités et
suivant des cartons corrigés.

**Cases verrouillées** (19/11/2026) : sur la feuille, ce qui découle du
calcul est en lecture seule (`OFE_VERROUILLES` : métrage, mandrins, tubes,
cartons, palettes, adhésif en kg). L'ADV modifie les entrées : quantité
(étiquettes, bobines OU levées, trois façons de la dire), fronts,
conditionnement, qté au mille, laize, mandrin, adhésif. Le cadenas d'une case
verrouillée l'ouvre pour forcer une valeur ; forcée, elle reste ouverte et
signalée dans « À relire ». Refermer le cadenas la rend au calcul (une étape
d'historique). Ouverte puis quittée sans saisie, elle se referme seule.

Les flèches Annuler / Rétablir de la barre de l'OF (`ofeMemoriser`,
`ofeRestaurer`) mémorisent l'état complet avant chaque geste et le restaurent
sans recalcul. Une case en cours de frappe n'est jamais réécrite par le calcul
(`ofeEnFrappe`).

Un id à `None` détache la référence **sans effacer le texte** : un OF Access
porte un libellé qu'aucune référence ne recouvre encore, et le perdre serait
perdre la seule chose qu'on sache de sa matière. L'écran affiche alors
« non rattaché au stock ».

**Le type de palette est UN champ.** `palette_europe` / `palette_perdues`
existent encore en base, vides et inutilisées : le type est un choix parmi des
références (« Pallet Europe », « Pallet Perdue », « Anti-bactérienne »), pas
deux compteurs. Le nombre vit dans `nb_palettes`.

`POST /api/stock/matieres/brouillon` crée la référence qui manque, sans prix ni
laize ni seuil, avec `brouillon = 1`. Sans cette porte, une ADV bloquée devant
une liste sans son carton retape du texte libre et tout le mécanisme ne sert à
rien. Mais un prix inventé est pire qu'un prix absent — il se propage dans la
valorisation sans jamais lever d'alerte : c'est MyStock qui complète, depuis
« matières à compléter ».

---

## Pré-remplir une fiche technique depuis RVGI

`app/services/rvgi_article_fiche.py` joint les cinq tables que personne ne
joignait à la main :

    fic_art   l'article vendu — libellé, référence client, format commandé
    gpr_ff    sa fiche de fabrication — machine, laize matière, outils, matière
    out_dec   l'outil de découpe — LA source de la géométrie
    mat_mat   la matière — support, adhésif, protecteur, grammage
    gpr_ff1   l'impression — pantone, anilox, composition, tête par tête

**`out_dec` est la table qui compte.** Vérifié sur la fiche papier de 623/0014,
outil 2796 : `ftl`/`fta` = 104,5 × 148,4, `ray` = 6, `ftl+espl` / `fta+espa` =
107,75 × 152,4 (le module), `espl` = 3,25 (latéral int.), `espa` = 4
(horizontal), `espl/2` = 1,625 (latéral ext.), `nbd` = 192 dents, `nbl` = 4 de
front, `nba` = 4 d'avance, `eps` = 52. Tout concorde au centième — et c'est ce
relevé que `tests/test_of_creation.py` rejoue.

`nbl` alimente `outil1_nb_front`, **jamais** `mod_nb_front`. Et la colonne
« Laize » de l'outil sur le papier est celle de la BOBINE (`gpr_ff.laimat`),
pas la laize développée de l'outil (`out_dec.lt`) : 440 contre 443,75.

Trois précautions à ne pas retirer :

- **Un zéro de RVGI n'est pas une valeur.** `laiout = 0`, `nbcoul = 0`,
  `ray = 0` sont des cases vides ; les recopier écrit un zéro qui se lit
  ensuite comme vérifié.
- **On ne remplit que les cases vides.** Une fiche corrigée par l'atelier a
  raison contre l'ERP.
- **Chaque champ dit d'où il vient.** `provenance` nomme la table, l'écran
  l'affiche. `gpr_ff` ne couvre que 585 articles sur 7 688, et la plupart de
  ses lignes datent d'avant 2010 : c'est un service rendu, jamais une promesse.

### Rattacher une commande remplit l'OF

Une ligne de commande porte un article, et l'article porte la moitié de l'OF.
`prefill_of()` le rend au moment où l'ADV coche la ligne — mais **seulement si
les lignes cochées portent UN SEUL article**. Deux articles dans un même OF,
c'est un regroupement décidé en connaissance de cause : en prendre un au hasard
serait pire que ne rien faire.

Les libellés de `fic_art` ne sont pas de la décoration :

    libc2  « Therm. Eco. Permanent, M. 76, Enr. Ext. »   matière, mandrin, enroulement
    libc3  « Bobine de 300 étiquettes, M. 25. »          LE conditionnement de l'OF
    libc4  « Carton de 16 bobines »                      nb bobines / carton

`libc3` est mot pour mot ce que l'OF imprime — vérifié sur 24/0023 (« Paravent
de 1000 plis de 4 étiquettes ») et 1164/0058. Ce sont des PHRASES : les motifs
d'extraction sont ancrés au plus court et tout ce qui en sort est marqué
`libellé` dans la provenance, parce qu'une extraction se trompe silencieusement
là où une colonne vide se voit.

**Le repli sur l'OF précédent n'est pas un bonus, c'est ce qui rend la
fonction utilisable.** `gpr_ff` ne couvre que 585 articles sur 7 688 — 58 des
125 articles en commande ouverte au 04/09/2026. Pour les autres, MySifa a déjà
fabriqué le produit : `_completer_depuis_mysifa()` reprend le dernier OF de la
même référence, sans jamais écraser ce que RVGI a répondu, et la provenance
nomme l'OF repris (« OF 9931861 »). `_REPRISE_OF` liste ce qui décrit le
PRODUIT ; quantités, dates et numéro en sont exclus — une quantité recopiée
d'un OF précédent part en production.

---

## La modale OF charge l'OF entier, pas la ligne de liste

`GET /api/of/{id}` existe pour ça. `/api/of/list` ne renvoie qu'une vingtaine
de colonnes sur soixante ; la modale en poste quarante-deux. Ouverte sur une
ligne de liste, elle affichait vides la laize, la glassine, la réf. adhésif et
tout l'outillage — et « Enregistrer » les écrivait à NULL, parce que
`autoriser_effacement=True` traite un champ vidé comme une décision humaine.
Ce qu'il est, quand le champ a réellement été montré à un humain.

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

**L'OF se corrige directement à l'écran** (décision du 18/11/2026). Au-delà de
900 px, la fenêtre pose une vraie case sur chaque valeur, aux positions de
`_CHAMPS` (`cases_du_modele()`, `GET /api/of/modele`), sur `data/of_modele.png`.
Les cases se calent sur les cadres du modèle (`data/of_modele_cadres.json`), et
tout cadre vide qu'aucun champ n'occupe devient une case libre
(`of_imports.cases_libres`, JSON), imprimée à cet endroit. Refaire le modèle PDF
impose de relancer `scripts/of_modele_ecran.py`, qui refait l'image et les cadres. Une case imprimée ajoutée à
`_CHAMPS` s'ajoute aussi à `OFE_FEUILLE` (`mysifa_prod_core.js`) ; le test le
vérifie. Sous 900 px, le formulaire reste.

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

---

## Choisir LA fiche d'un produit — `app/services/fiche_choix.py`

Un produit a souvent une fiche par machine (« 1220/0001 - COHESIO1 - Laize
470 » / « … COHESIO2 - Laize 570 »). Le planning écrit « Cohésio 2 », Access
« COHESIO 2 » ou « COHESIO2 » : comparées en `LOWER(TRIM())`, elles ne sont
JAMAIS égales, et le repli prenait la plus petite id — la fiche de l'autre
machine, avec un autre outil et un autre nombre de fronts (constat du
17/09/2026, dossier 9931675+996).

- Python : `choisir_fiche(conn, ref, machine, laize, reference)` ou
  `meilleure_fiche(candidates, …)`. Ordre : référence complète identique, puis
  machine + laize, machine, laize, fiche sans machine / « COHESIO » générique.
  **À rang égal, la plus récente** (`recence()` : `date_modif`, `date_import`,
  id) — jusqu'au 18/11/2026 c'était la plus petite id, donc la plus ancienne.
  En SQL : `ORDER BY …, ft.date_modif DESC, ft.date_import DESC, ft.id DESC`.
- SQL : `sql_cle_machine("ft.machine")` produit l'expression équivalente, en
  SQL pur (pas de fonction Python enregistrée — elle manquerait hors `get_db()`).

❌ `LOWER(TRIM(machine)) = LOWER(TRIM(?))` pour départager des fiches.
Restent à convertir : `expe_departs.py` et `expe_pilotage.py` (jointure `km.mk`).

## Un OF sans PDF se complète depuis sa fiche — `app/services/of_depuis_fiche.py`

L'aperçu d'un OF Access ou MySifa (`/api/of/{id}/pdf-preview`) passe par
`completer_of()` : produit retrouvé par l'OF, sinon par le dossier relié,
sinon par la commande RVGI (un seul article, sinon rien) ; cases VIDES
complétées — machine, laize, matière, outils 1 et 2, mandrin, conditionnement,
cartons, palette, particularités. Lecture seule : rien n'est écrit en base.
La case Réf. porte la clé produit, jamais le numéro d'OF ni le libellé
complet de la fiche (qu'Access envoie aussi dans `format`).

## Fiche manquante : l'ADV la signale

Environ 40 % des articles commandés n'ont pas de fiche (relevé du 19/11/2026).
Le bouton « Signaler la fiche manquante » de la fenêtre OF appelle
`POST /api/of/signaler-fiche-manquante`, qui crée une tâche (type support,
module prod) assignée aux superadmins par `creer_tache_pour()`, avec article,
désignation, commande, quantité, délai, fiches du même client et OF déjà faits.
Un article déjà signalé et pas traité ne crée pas de seconde tâche.

## Relier un OF à un dossier : `_promote_of_link`, jamais un UPDATE direct

Le slot lit `planning_entries.of_import_id`, l'œil « Voir l'OF relié » lit
`planning_of_links`. Le pont Access écrivait la colonne seule : 102 dossiers
divergeaient. Migration `realigner_liens_of_planning` pour l'existant.

## Sync des fiches : par empreinte, plus par `modif`

`modif` est une date sans heure : une fiche corrigée le jour même d'un
passage n'était jamais renvoyée (1341/0012, dupliquée de 1341/0008 puis
corrigée l'après-midi). `access_sync_fiches.py` compare désormais une
empreinte du contenu (`sync_fiches_empreintes.json` à côté de la base).

**Fraîcheur des fiches Access** (19/11/2026) : le pont
(`scripts/access_sync_fiches.py`, poste Windows, 11 h et 17 h) envoie à
chaque passage un compte rendu `POST /api/bridge/passage` (table
`ponts_passages`), même sans fiche modifiée. MyProd › Fiches techniques
l'affiche (`GET /api/fiches-techniques/actualisation`). Tant que le script
n'est pas redéployé sur le poste, seule la dernière fiche reçue est connue
(création ou mise à jour via `documents_valeurs_historique`).

**Scans d'OF** (19/11/2026) : `scripts/of_scans_import_quotidien.py` rend
compte de chaque passage de la même façon (pont `scans`, clé `scan:write` ;
`PONTS` de `api_bridge.py` donne le droit exigé par pont), y compris un
dossier introuvable (1 erreur). Le sous-titre de MyProd › Scans d'OF affiche
le dernier import (`GET /api/of/scans/actualisation`), « il y a N jours » au
delà de 3 jours. Constat : 473 scans importés en une fois le 26/08/2026, plus
rien ensuite, l'import quotidien n'ayant jamais été planifié. Liste des OF :
icône de scan active s'il y en a un, orange « scan attendu » si l'OF est
terminé au planning (`termine` de `/api/of/list`), sinon rien.

## L'OF et la fiche se contredisent — `app/services/of_fiche_accord.py`

Constat du 18/11/2026, dossier 9932921 : fiche 1341/0012 dupliquée de la
1341/0008 (DSI, 100 x 99,6, Vélin H400) face à un OF Cohésio 1, 110 x 150,
PP 95µ. Le contrôle ne comparait que des ids de matière (vides sur tout
document Access) et la quantité au mille.

- `comparer(of, fiche)` : machine (`cle_machine`, « COHESIO » générique
  toléré), format (libellé, sinon `eti_laize` x `eti_longueur`, tolérance
  `ACCORD_FORMAT_TOLERANCE_MM`, sens indifférent), matière (id si les deux en
  ont, sinon famille du libellé : `FAMILLES_MATIERE` de `config.py` ; un
  libellé sans famille ou à deux familles ne conclut rien), laize, quantité
  au mille. Un champ vide d'un côté n'est pas comparé.
- `verdict()` : **le document le plus récent fait foi**. OF : max de
  `date_creation` et `date_import`. Fiche : max de `date_modif` et de la
  dernière correction manuelle journalisée. À date égale, l'OF. Deux écarts
  parmi machine / format / matière = « fiche d'un autre produit ».
- `fiche_affichee()` : quand l'OF fait foi, ses valeurs remplacent celles de
  la fiche **à l'affichage seulement**, sur les champs en écart. Le PDF
  (`/api/fiches-techniques/{id}/pdf-preview?of_id=`) les marque « (OF) » et
  porte un bandeau rouge. Décision d'Eugène : alerte + le plus récent fait
  foi à l'écran. Besoins matières et déstockage lisent toujours la fiche en
  base — on ne corrige jamais d'office, la fiche se répare à la source.

Le planning (`/api/of/planning/{id}` → `fiche_accord`) affiche l'écart
au-dessus des onglets OF / Fiche ; la règle de cohérence `documents.of_fiche`
utilise la même comparaison. Test : `python3 tests/test_of_fiche_accord.py`.
