# Passation — chantier entrées / sorties de stock matières

Écrit le 02/09/2026, fin de session Cowork sur le poste Windows `dell-integr`.
À lire en entier avant de toucher au code. La suite du chantier se fait sur le Mac.

---

## Le chantier en une phrase

Mieux gérer les entrées et sorties de stock des matières premières. **Les entrées
viennent toutes des réceptions de matières de RVGI**, vues dans `/erp` ; **les
sorties se font toutes en fin de dossier de production**.

Quatre points ont été posés par Eugène, dans cet ordre :

1. Le **type d'article** manque dans les colonnes de réception — on ne sait pas si
   on reçoit de la matière, de la sous-traitance ou des outils. → **FAIT**
2. Gérer la **correspondance des références matières RVGI ↔ MySifa** : elles ne
   sont pas identiques. → à faire
3. Les sorties de fin de dossier sont déjà bien faites, avec l'ajustement possible
   par l'administration technique depuis le planning de prod. → rien à faire
4. Même correspondance à établir entre la **matière de l'OF / de la fiche
   technique** et la référence MySifa. → à faire

---

## Arbitrages pris avec Eugène — ne pas les rouvrir

- Les réceptions RVGI doivent **alimenter** le stock MyStock, pas seulement être
  consultées.
- L'écran Réceptions porte **deux** colonnes de type : une « Famille » MySifa en
  quatre valeurs, et le type RVGI détaillé à côté.
- Regroupement en familles : les **pièces Cohésio et les clichés** vont avec
  l'outil de découpe dans *Outillage* ; les **encres** vont dans *Consommables*.
- Périmètre des entrées automatiques : **ce que MyStock gère déjà** — complexes,
  glassines, vélins, couchés, thermiques, synthétiques, adhésifs, mandrins,
  cartons, palettes. Pas d'extension aux encres ni à l'emballage pour l'instant.
- Traçabilité : la réception RVGI crée une entrée **en attente** ; le magasin
  complète lot, certificat FSC et codes-barres bobines dans MyStock. La quantité
  vient de l'ERP, la traçabilité de l'atelier.

---

## Ce qui a été livré (point 1)

### Fichiers

| Fichier | Rôle |
|---|---|
| `app/services/erp_types.py` | **nouveau** — libellés des types depuis `fic_para`, familles depuis `erp_type_famille`, les trois énumérations de l'écran |
| `app/core/migrations/2026_09_02_erp_type_famille.py` | **nouveau** — table du regroupement, seedée sur l'arbitrage |
| `tests/test_erp_types_article.py` | **nouveau** — 25 contrôles, dont la non-duplication de la jointure sur données réelles |
| `app/services/erp_catalogue.py` | écran Réceptions enrichi, `enums()`, `_c(sans_filtre=)`, `adapter_ecran` valide les jointures multi-colonnes |
| `app/services/erp_mirror.py` | `_from()` gère `et` (jointure à plusieurs colonnes), `conditions_colonnes` respecte `sans_filtre` |
| `app/routers/erp.py` | `catalogue.ENUMS` → `catalogue.enums()` (4 endroits) |
| `app/routers/settings.py` | `GET`/`PUT /api/settings/erp-types-article` |
| `app/web/settings_page.py` | onglet **Paramètres › Types d'article RVGI** (groupe Logistique) |
| `app/web/erp_page.py` | l'entonnoir d'en-tête respecte `sans_filtre` |
| `.claude/rules/erp-rvgi.md`, `docs/rvgi/data_rvgi.md` | documentation corrigée, voir plus bas |

### Ce que ça donne

L'écran `/erp` › Achats › Réceptions gagne sept colonnes — Réf. article,
Désignation, **Famille**, **Type d'article**, **Commandée**, **Position**,
Laize — et trois filtres de rail. « Quantité » devient « Reçue », qui n'a de
sens qu'à côté de « Commandée ». Il passe de 10 à 17 colonnes et reste à
8 949 lignes : la jointure ne duplique rien. Les quatre familles partitionnent
exactement les réceptions :

| Famille | Lignes |
|---|---|
| Sous-traitance | 3 614 |
| Outillage et clichés | 2 049 |
| Matière première | 1 668 |
| Consommables et emballage | 1 618 |

### La connexion commande fournisseur ↔ réception

C'était le vrai défaut, relevé par Eugène sur la modale de la commande 5905 :
le lien entre les deux écrans portait sur le **seul numéro de pièce**. Depuis la
ligne 3 d'une commande de six lignes, il ramenait les six réceptions — sans dire
laquelle répondait à la ligne ouverte.

Ce qui a été mesuré le 02/09/2026 :

- `cdf_ligne` n'a **aucun couple `(numero, ligne)` en double** : c'est une vraie
  clé.
- `lif_ligne` en a **277 en double** — 8 984 réceptions pour 8 552 couples : une
  ligne de commande se reçoit couramment en plusieurs fois. La relation est donc
  n réceptions → 1 ligne de commande, et la jointure ne duplique rien.
- **680 lignes de commande n'ont jamais été reçues** (sur 9 232).

D'où, des deux côtés, un lien à la **ligne** et un lien à la **pièce**, dans cet
ordre :

| Depuis | Lien | Portée |
|---|---|---|
| Commandes fournisseurs | Réceptions de cette ligne | `(numero, ligne)` |
| Commandes fournisseurs | Réceptions de la commande | `numero` |
| Réceptions | La ligne de commande | `(numero, ligne)` |
| Réceptions | La commande fournisseur | `numero` |

Et trois liens **nouveaux** depuis une réception — L'article, La matière, Le
fournisseur — qui étaient impossibles avant : leurs clés (`code1`/`code2`,
`numfou`) vivent sur la commande, pas sur la réception. Ils ne coûtent rien,
`ligne_brute()` faisant déjà un `SELECT *` sur l'écran joint.

`scripts/audit_liens_erp.py` a été corrigé dans la foulée : il vérifiait ses
colonnes sur les **tables de base** et annonçait « COLONNE ABSENTE » sur des
liens qui fonctionnent — huit d'entre eux, dont tous ceux de `clients` et
`fournisseurs`, n'avaient jamais été mesurés. Les deux côtés passent maintenant
par l'écran, jointures comprises : **103 liens, aucun mort, aucun à zéro**.

**La modale de pièce hérite des mêmes colonnes** (`erp_mirror.piece()` rend les
lignes avec les colonnes de la grille) : le tableau « LIGNES DE LA PIÈCE » passe
de 23 à 28 colonnes et affiche Réf. article / Désignation / Famille / Type /
Laize entre Fournisseur et Quantité. Vérifié sur la commande fournisseur 5980.

### Ce que ça donne, concrètement

    matière + ligne non soldée — 12 lignes
    552/0005   Glassine Siliconé Jaune    reçue  64 008   commandée 128 000   Partielle
    574/0003   Thermique Bicolore         reçue  81 500   commandée 782 400   Partielle
    1091/0002  Couché Blanc Brillant      reçue  62 340   commandée 124 000   Partielle
    1091/0001  Velin Mat Blanc ETIWELL    reçue 155 103   commandée 302 400   Partielle

---

## Les six trouvailles RVGI qui portent tout le chantier

Elles sont vérifiées sur les données. Ne pas les redécouvrir, ne pas les contredire
sans nouvelle mesure.

**1. `lif_ligne` ne porte aucun article.** Ni code, ni désignation, ni type. Elle
dit qu'une quantité est arrivée sur la ligne n° X de la commande fournisseur n° Y.
Ce qui a été reçu se lit sur `cdf_ligne`, jointe sur le **couple** `(numero, ligne)`.
Couverture : 8 984 sur 8 984. Le numéro seul ferait exploser le nombre de lignes.

**2. `cdf_ligne.type` est le type d'article**, 18 valeurs sur les réceptions. Ce
n'est **pas** `mat_mat.type` : la ligne d'achat réserve ses deux premiers rangs à
ce qui n'est pas une matière — **1 = article acheté** (3 825 des 3 832 lignes sont
dans `fic_art`, c'est la sous-traitance), **2 = outil de découpe** (1 367 sur 1 367
dans `out_dec`). Le reste suit avec deux de décalage :

    cdf_ligne.type = mat_mat.type + 2

Vérifié sur les types purs : adhésifs 9 → 7 (169/169), encres 10 → 8 (462/462),
clichés 11 → 9 (702/703). Quand les deux divergent, **le type de la ligne d'achat
fait foi** — c'est lui qui décrit ce qui a été commandé.

**3. Les libellés des types se lisent dans `fic_para`.** Le catalogue supposait
depuis toujours que les énumérations RVGI n'étaient dans aucune table. C'est vrai
partout sauf ici. Un paramètre porte un `numero` de forme `15 TT PP` (`TT` = type
de matière, `PP` = rang du paramètre) et le libellé est le suffixe de `des1` après
« : ». **On prend le suffixe majoritaire du bloc** : RVGI porte ses propres
coquilles de recopie (`150705` annonce « Encres » au milieu du bloc des adhésifs).

**4. `cdf_ligne.code3` porte la laize en mm**, remplie sur 100 % des lignes des six
types laizés (complexes, glassines, vélins, couchés, thermiques, synthétiques),
vide partout ailleurs — adhésifs compris, ce qui est correct. C'est ce qui permet
d'entrer une bobine dans la bonne laize de MyStock.

**5. Les numéros de lot n'existent pas dans RVGI.** `lif_ligne.lot` : **0 sur
8 984**. `stm_hist.lot` : **0 sur 18 074**. Jusqu'aux écritures du jour même. Les
colonnes existent, personne ne les saisit. `erp-rvgi.md` affirmait le contraire,
c'est corrigé. **Conséquence FSC : aucune traçabilité amont ne viendra de l'ERP**,
elle se saisit entièrement en réception MyStock.

**6. Le type RVGI tombe exactement sur les catégories MyStock.** C'est la clé du
point 2 :

| Type RVGI | `matieres_premieres` | Réfs actives |
|---|---|---|
| 3 Complexes | `complexe` | 17 |
| 4 Glassines | `glassine` | 4 |
| 5 Vélins | `frontal` / Velin | 3 |
| 6 Couchés | `frontal` / Couché | 3 |
| 7 Thermiques | `frontal` / Thermiques | 6 |
| 8 Synthétiques | `frontal` / Synthétique | 3 |
| 9 Adhésifs | `adhesif` | 6 |
| 15 Mandrins | `mandrin` | 5 |
| 19 Cartons | `carton` | 24 |
| 20 Palettes | `palette` | 2 |

73 des 78 références actives, **sans un seul cas ambigu**. Seul
« autre / têtes d'impression » (2 réfs) reste dehors, et il est hors périmètre.
Apparier un thermique, c'est donc choisir parmi 6, pas parmi 78.

---

## Point 2 — correspondance des références RVGI ↔ MySifa

### L'état des lieux

`matieres_premieres` (78 lignes) porte une `reference` en texte libre et
**aucune colonne RVGI**. Rien ne relie les deux référentiels.

Côté ERP la clé est `code1`/`code2`, avec `code3` = la laize sur les matières et
les mouvements. `mat_mat` compte 1 536 matières vivantes, avec `libc1`, `libt1`,
`libt2`, `ref` (référence fournisseur) et jusqu'à dix fournisseurs dépliés en
colonnes numérotées.

Les seuls liens actuels sont `stock_receptions.rvgi_cde` / `rvgi_bl` /
`rvgi_qte_attendue` : du texte libre vers une **pièce**, jamais vers un article.
Et cette table ne compte que 14 réceptions — l'entrée matière MyStock est
aujourd'hui quasi inutilisée.

### Ce qui reste à décider avec Eugène

- Une matière MySifa peut-elle correspondre à **plusieurs** articles RVGI (le même
  thermique acheté chez deux fournisseurs sous deux codes) ? Probablement oui — le
  modèle doit donc être une table de liens, pas une colonne sur `matieres_premieres`.
- La **laize** fait-elle partie de la clé d'appariement, ou l'appariement se
  fait-il matière à matière avec la laize lue sur `code3` au moment du mouvement ?
  (MyStock tient déjà son stock par laize via `mp_stock_laize` / `mp_matiere_laizes`.)
- Faut-il une **proposition automatique** d'appariement (par type + libellé) à
  valider, sur le modèle de l'écran de mapping de Besoins matières ?

### Le précédent à suivre

`mp_fiche_mapping` + `GET/POST/DELETE /api/stock/besoins-matieres/mapping`
(`app/routers/besoins_matieres.py`, autour de la ligne 3030) est le modèle : une
table de correspondance éditable, un écran qui liste les valeurs non mappées
détectées dans les données. Le défaut à ne pas reproduire est décrit au point 4.

---

## Point 4 — matière de l'OF / fiche technique ↔ référence MySifa

Le mécanisme **existe** : `mp_fiche_mapping`, clé `(kind, source_value)` →
`matiere_id`, 61 correspondances. `kind` vaut `support`, `glassine`, `adhesif`,
`mandrin`, `carton`, `palette` ; `source_value` est le **texte libre** de la fiche
technique.

Il est à moitié rempli :

| Champ | Valeurs distinctes | Lignes non mappées |
|---|---|---|
| support | 124 | 359 / 911 |
| adhésif | 66 | 171 / 825 |
| glassine | 12 | 32 / 656 |

124 libellés de support distincts pour 78 matières : chaque variante d'orthographe
crée une entrée à mapper.

**Le défaut de l'écran** : `list_mapping` ne remonte les valeurs non mappées que
pour les **dossiers actifs** (`_load_dossiers(conn)` sans filtre de période, mais
la vue ne porte que le carnet courant). Le stock de retard sur les fiches
historiques est donc invisible.

Le déstockage lui-même est solide et ne demande rien :
`/api/stock/destockage/{planning_id}` (`besoins_matieres.py` à partir de la ligne
2600) — calcul reparti du réel (`production_data` prime sur l'OF), conversion dans
l'unité de gestion (bobines fractionnaires, kg, palettes), laize suggérée par
rapprochement avec celle du dossier, blocage tant que l'OF et la fiche technique
ne sont pas validés, mouvements tracés avec `of_import_id` et `fiche_id`.

---

## Puis : brancher les entrées

Une fois le point 2 posé, la ligne de réception RVGI sait à quelle référence
MySifa elle correspond, dans quelle laize et pour quelle quantité. Reste à écrire
le mouvement d'entrée — en attente, complété par le magasin (arbitrage ci-dessus).

Attention : **`/erp` est un miroir et n'écrit rien**
(`.claude/rules/erp-rvgi.md`). L'écran qui présente les réceptions à intégrer et
le geste d'intégration appartiennent à **MyStock**, pas à MyERP.

---

## Deux corrections faites au passage

- L'onglet `transport` des Paramètres manquait dans `VALID_TABS` depuis sa
  création : un lien `#transport` retombait sur le menu. Corrigé.
- `ENUMS["type_produit"]` était un relevé manuel de 3 codes sur 18 du même
  référentiel, branché sur aucune colonne. Retiré.

---

## Comment vérifier que tout va bien

```bash
python3 tests/test_erp_types_article.py      # 25 contrôles, dont sur le miroir réel
python3 scripts/audit_liens_erp.py           # doit finir sur « LIENS MORTS : 0 sur 99 »
```

Le test saute silencieusement ses contrôles sur données réelles si le miroir
(`data/erp_mirror.db`) est absent — sur le Mac, il faut donc soit copier le
miroir, soit se contenter des contrôles unitaires.

---

## Conventions du dépôt à ne pas oublier

- **Une migration = un fichier** dans `app/core/migrations/`, `NOM` unique et
  définitif, toujours rejouable. Jamais dans `_migrate()`.
- **Ne jamais bumper `APP_VERSION`** — le collaborateur s'en charge sur staging.
- Rien de spécifique à SIFA en dur : les référentiels se lisent en base ou dans
  l'ERP, les réglages vivent dans Paramètres.
- Lire la règle `.claude/rules/` du sujet touché avant d'écrire — l'index est en
  fin de `CLAUDE.md`. Pour ce chantier : `erp-rvgi.md`, `besoins-matieres.md`,
  `of-fiches-techniques.md`, `couts-matieres.md`, `migrations.md`.
