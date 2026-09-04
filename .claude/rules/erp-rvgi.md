---
paths:
  - "app/routers/erp*.py"
  - "app/web/erp*.py"
  - "app/services/erp*.py"
  - "scripts/**/*rvgi*"
  - "docs/rvgi/**/*"
---
## RVGI — la base de l'ERP, en lecture seule

RVGI est l'ERP de SIFA. Sa base `sifa_cs` tourne sur un serveur HFSQL
Client/Serveur (PC SOFT / WinDev) : `192.168.100.199:4949`, encodage
ISO-8859-1, 183 tables utiles. On l'atteint par le provider OLE DB
`PCSoft.HFSQL` — celui qu'Excel utilise déjà, donc déjà installé sur les postes,
appelable en COM depuis PowerShell ou Python sans rien installer.

**Le détail vit dans `docs/rvgi/data_rvgi.md`** : carte des domaines, tables
qui comptent avec le sens de leurs colonnes, clés de jointure, gisements
identifiés. Le relevé brut est dans `docs/rvgi/rapport_rvgi.md` et
`docs/rvgi/schema_rvgi.json`, régénérés par
`scripts/inventaire_rvgi.ps1` (lecture seule, aucune écriture sur l'ERP).

**Règles absolues**

- **RVGI est une source, jamais une destination.** Aucun code MySifa n'écrit
  dans `sifa_cs`. La connexion se fait avec un compte de lecture seule dédié,
  pour que ce soit structurellement impossible et pas seulement conventionnel.
- **`corbeille = 0`, partout.** RVGI ne supprime pas, il marque. Toute autre
  valeur — `1`, `9`, mais aussi `2.1` ou `18.2` — est une ligne supprimée dont
  les valeurs ne veulent plus rien dire. Plus d'une ligne sur deux est dans ce
  cas (`mat_mat` : 1 536 vivantes sur 7 521). Le filtre porte sur les
  comptages, les agrégats, les extraits, et **des deux côtés d'une jointure**.
- **Le VPS ne voit pas le LAN.** `192.168.100.x` n'est pas joignable depuis
  `mysifa.com`. Toute synchro est un **push** depuis un poste du réseau vers
  `/api/bridge/*` avec une clé `X-Api-Key`, planifié côté Windows — le motif de
  `scripts/access_sync_of.py`. Jamais un pull depuis MySifa.
- **Trois colonnes à ne jamais lire** : `gen_sala.mdp`, `fic_clt.inftpmdp`,
  `fic_fou.inftpmdp` contiennent des mots de passe en clair. Pas de `SELECT *`
  paresseux sur ces tables, pas de journalisation de ligne entière, pas de
  recopie dans MySifa.

**Les deux clés**

- **`code1` / `code2` — l'article.** `code1` = numéro du client, `code2` = rang
  de l'article chez lui. `_erp_reference()` dans `app/routers/reconciliation.py`
  construit déjà `890/0112` à partir de ce couple : l'appeler, ne pas la
  réécrire. `code3` porte la laize sur les matières et les mouvements.
- **`cde_entete.numero` en `99xxxxx` — la commande**, soit le numéro d'OF que
  `_OF_RACINE_RE` reconnaît déjà. Il se reporte dans `liv_ligne.numcde`,
  `vte_ligne.livno`, `stk_hist.numcde`, `cdi_ligne.nocde`. Les autres domaines
  ont leur propre numérotation : **ne jamais joindre deux domaines sur `numero`
  seul**, toujours par la colonne de report explicite.

**Deux pièges de lecture qui ont déjà faussé un relevé**

- **Les tableaux WinDev sont dépilés en colonnes.** `mat_mat` déclare 76
  colonnes logiques et en expose 483 : `pafou1`, `pafou1_2`… Là où MySifa
  aurait une table fille, RVGI a des colonnes numérotées. Les replier vers un
  modèle relationnel est le gros du travail de mapping.
- **Des sentinelles à la place des nuls** : `30/11/1999` pour une date vide,
  `4710000000` pour un compte absent, `99999999999.99` pour « pas de maximum »,
  `0` sur un prix pour « non renseigné » — jamais « gratuit ».

**Le module production de RVGI est abandonné**

`cdi_*` et `gpr_gpr` / `gpr_mat` n'ont plus une écriture depuis avril 2026 :
SIFA a cessé de les alimenter parce que le module ne convenait pas, et c'est ce
qui a motivé la création de MySifa. Ces tables n'ont plus qu'une valeur
d'historique — ne rien construire dessus, ne pas les présenter comme un état
courant. `gpr_ff` (fiches de fabrication) fait exception et reste maintenue.

Conséquence pour la traçabilité : le lien dossier ↔ lot matière que portait
`gpr_mat.reflot` n'est plus alimenté côté ERP et doit exister dans MySifa.

**Et l'entrée non plus n'est pas tracée.** Ce document affirmait que
`lif_ligne.lot` et `stm_hist.lot` « restent vivants ». C'est faux, relevé le
02/09/2026 : **zéro ligne sur 8 984 réceptions et zéro sur 18 074 mouvements
matière**, jusqu'aux écritures du jour même. Les colonnes existent, personne ne
les saisit. Aucun numéro de lot n'entre donc dans MySifa par l'ERP — toute
traçabilité amont, FSC comprise, se saisit côté MySifa, en réception MyStock.

---

## Le type d'article — `cdf_ligne.type`, et ses libellés dans `fic_para`

`lif_ligne` ne porte **aucun article** : ni code, ni désignation, ni type. Elle
dit qu'une quantité est arrivée sur la ligne n° X de la commande fournisseur
n° Y. Ce qui a été reçu se lit sur `cdf_ligne`, jointe sur le **couple**
`(numero, ligne)` — le numéro seul ramènerait toutes les lignes de la commande
pour chaque réception. Couverture relevée le 02/09/2026 : 8 984 sur 8 984.

`cdf_ligne.type` porte 18 valeurs sur les réceptions. Ce n'est pas
`mat_mat.type` : la ligne d'achat réserve ses deux premiers rangs à ce qui n'est
pas une matière — **1 pour l'article acheté** (3 825 des 3 832 lignes sont dans
`fic_art` : c'est la sous-traitance), **2 pour l'outil de découpe** (1 367 sur
1 367 dans `out_dec`). Le reste suit avec deux de décalage :

    cdf_ligne.type = mat_mat.type + 2

Vérifié sur les types purs : adhésifs 9 → 7 (169/169), encres 10 → 8 (462/462),
clichés 11 → 9 (702/703). Quand les deux divergent sur une ligne, c'est une
erreur de saisie RVGI — et **c'est le type de la ligne d'achat qui fait foi**,
puisque c'est lui qui décrit ce qui a été commandé.

**Les libellés se lisent dans `fic_para`**, contrairement à ce que le catalogue
a longtemps supposé. Un paramètre porte un `numero` de la forme `15 TT PP`, où
`TT` est le type de matière et `PP` le rang du paramètre ; le libellé est le
suffixe de `des1` après « : ». On prend le suffixe **majoritaire** du bloc :
RVGI porte ses propres coquilles de recopie (`150705` annonce « Encres » au
milieu du bloc des adhésifs). `app/services/erp_types.py` fait ce travail — ne
pas recopier ces libellés en dur, les renommer dans RVGI doit suffire.

Le regroupement en **familles** (matière, sous-traitance, outillage,
consommable), lui, n'existe pas dans RVGI : c'est une décision MySifa, stockée
dans `erp_type_famille` et modifiable dans Paramètres › Types d'article RVGI.

`cdf_ligne.code3` porte la **laize en mm**, remplie sur 100 % des lignes des six
types laizés (complexes, glassines, vélins, couchés, thermiques, synthétiques)
et vide partout ailleurs, adhésifs compris.

---

## ERP RVGI — l'app `/erp` et son miroir

RVGI est l'ERP de SIFA (base HFSQL `sifa_cs`, serveur `192.168.100.199:4949`).
MySifa en expose une lecture dans l'app `/erp`, ouverte à **`ROLES_ADMIN`** —
direction, services administration et super administrateur. La documentation de la base elle-même est dans
`docs/rvgi/data_rvgi.md` — la lire avant de toucher à quoi que ce soit ici.

### MyERP est un MIROIR — rien d'autre

**Sauf contre-indication explicite d'Eugène, on ne crée dans `/erp` RIEN qui ne
soit pas un miroir de l'ERP** — ni donnée, ni outil de gestion.

Cela veut dire, concrètement :

- **Pas d'écran qui ne vienne pas du catalogue.** Les domaines et les écrans du
  menu sont ceux de `erp_catalogue.py`, qui décrit les tables de RVGI. On
  n'ajoute pas un domaine côté client, on n'invente pas d'écran de travail.
- **Pas de liste de tâches, pas de tableau de bord, pas d'outil de contrôle.**
  Une liste « à traiter », une comparaison entre les deux bases, un suivi
  d'écarts : tout cela est du travail MySifa. Sa place est dans l'app métier
  concernée — le monitoring de stock dans MyStock, les dossiers à rattacher
  dans MyProd, les départs dans MyExpé. Pas ici.
- **Pas de données saisies dans MyERP.** L'écran lit, il n'enregistre pas.

Ce qui est autorisé, parce que ça reste de la lecture posée sur du RVGI :
afficher, à côté d'une ligne de l'ERP, ce que MySifa en a fait — la colonne
« Dossier de fab » sur les commandes en est l'exemple, demandée explicitement.
La règle porte sur la création d'écrans et d'outils, pas sur l'enrichissement
d'une ligne existante.

**Historique de la règle.** Deux écrans avaient été ajoutés sans être demandés :
« À rattacher » (les dossiers MySifa sans pièce RVGI) et « Stocks RVGI ↔
MySifa ». Ils ont été retirés le 26/08/2026. Le premier n'avait rien à faire
dans un miroir ; le second existait déjà, à sa vraie place, dans le monitoring
de MyStock. En cas de doute sur un ajout à `/erp` : demander.

### Les trois règles absolues

1. **Le sens d'écriture est unique.** RVGI est la source, MySifa lit. Aucun code
   MySifa n'écrit dans l'ERP. Côté miroir, ce n'est pas une consigne mais un
   fait : `app/services/erp_mirror.py` ouvre la base en `mode=ro`, une écriture
   lève `attempt to write a readonly database`.
2. **`corbeille = 0`, partout.** RVGI ne supprime pas, il marque. Plus d'une
   ligne sur deux est morte (`fic_art` : 7 678 vivantes sur 41 389). Le filtre
   est appliqué à l'export, donc le miroir ne contient que du vivant — mais
   toute requête écrite directement contre l'ERP doit le porter, des deux côtés
   d'une jointure.
3. **Trois colonnes ne sont JAMAIS lues** : `gen_sala.mdp` et `pasmail`,
   `fic_clt.inftpmdp`, `fic_fou.inftpmdp` — mots de passe en clair côté ERP.
   `scripts/export_rvgi_csv.ps1` les retire de la liste des colonnes **avant**
   la requête (`$COLS_INTERDITES`) : leur valeur n'entre jamais en mémoire.
   Ne pas « simplifier » en `SELECT *`.

### Où vit quoi

| Fichier | Rôle |
|---|---|
| `scripts/export_rvgi_csv.ps1` | ERP → CSV, lecture seule, 61 tables. Lit le `.env`. |
| `scripts/import_rvgi_csv.py` | CSV → `data/erp_mirror.db`. stdlib seule, aucun import de `app.*`. |
| `scripts/sync_rvgi.ps1` | Export + zip + envoi HTTPS. Tâche planifiée, 5 h et 12 h 30. |
| `app/services/erp_mirror.py` | Connexion `mode=ro`, moteur de liste générique, sentinelles. |
| `app/services/erp_catalogue.py` | Les 27 écrans, en déclaratif. |
| `app/services/erp_export.py` | La vue courante en `.xlsx`. Ne décide rien, écrit. |
| `app/routers/erp.py` | API lecture seule, `ROLES_ADMIN`. Aucun verbe d'écriture. |
| `app/web/erp_page.py` | La page `/erp`. |
| `app/routers/api_bridge.py` | `POST /api/bridge/erp/miroir` — réception des exports. |
| `scripts/audit_liens_erp.py` | Vérifie les 59 liens du catalogue contre le miroir. |

Le miroir vit dans **son propre fichier** (`ERP_MIRROR_DB`, défaut
`data/erp_mirror.db`), pas dans `production.db`. C'est délibéré : il est
entièrement reconstructible depuis l'ERP, donc il n'a rien à faire dans les
backups de production ni dans les migrations, et il se purge d'un `rm`. Il n'est
pas dans git. Chaque instance a le sien — v1 et la prod ne le partagent pas.

### Ajouter un écran

On n'écrit pas de page : on ajoute une entrée à `ECRANS` dans
`app/services/erp_catalogue.py` — table, alias, jointures, colonnes, filtres,
groupes du panneau de détail. Le moteur fait le reste.

`adapter_ecran()` élague ensuite l'écran de ce que le miroir n'a pas : une
colonne absente disparaît au lieu de faire tomber la requête, un écran dont la
table manque n'est pas proposé. C'est ce qui permet d'écrire un catalogue à
partir du relevé sans avoir vu les données.

### Ajouter un lien entre écrans

`LIENS` (même fichier) déclare, écran par écran, les pièces rattachées :
`{"label", "ecran", "sur": {"<colonne cible>": "<champ source>"}}`. Le front
n'envoie jamais un nom de colonne — il envoie l'écran d'origine, l'identifiant
de la ligne et le **rang** du lien, et le serveur reconstruit la condition
depuis le catalogue. Ne pas réordonner `LIENS` sans y penser : le rang, c'est
l'index dans la liste.

**Une colonne peut porter un lien** : `_c(..., saut="<clé du lien>")` rend la
cellule cliquable dans la grille — elle bascule sur l'écran d'en face, restreint
à cette ligne, sans passer par le panneau. La colonne nomme le lien par sa
**clé** (`"cle"` dans l'entrée de `LIENS`), jamais par son rang :
`adapter_ecran()` traduit la clé en rang au moment de servir l'écran, ce qui
rend un réordonnancement de `LIENS` inoffensif pour les sauts. Un saut dont la
clé n'existe pas laisse la colonne telle quelle, et le front n'enveloppe que si
l'écran visé est servi par ce miroir — un lien mort vaut moins qu'un nombre nu.
Portés aujourd'hui : réceptions → commande fournisseur (`cde_piece`,
`cde_ligne`), commandes fournisseur → réceptions (`receptions_cde`,
`receptions_ligne`), factures fournisseur → commande (`cde_piece`).

**Après tout ajout ou modification, lancer `python scripts/audit_liens_erp.py`.**
Un lien branché sur une colonne que RVGI ne remplit jamais ne remonte rien et
ne le dit pas — le 25/08/2026, trois liens étaient dans ce cas : `col_ligne.numcde`
vaut 0 sur les 257 lignes de colisage, et `lot` est NULL partout dans
`lif_ligne` comme dans `stm_hist`. Le script les trouve en quelques secondes.

Deux pièges de typage, tous deux traités, à ne pas défaire :

- `code1` / `code2` / `code3` sont **toujours** stockés en TEXT. Sinon `code1`
  vaut `890` (INTEGER) dans `cde_ligne` et `« FR »` (TEXT) dans `fic_art`, et la
  jointure ne remonte rien — sans erreur.
- Les valeurs sentinelles de RVGI (`30/11/1999` = date vide, `99999999999.99` =
  pas de maximum, `0` sur un prix = non renseigné, `255` sur un octet = non
  renseigné) sont **conservées en base** et neutralisées à la lecture, dans
  `nettoyer()`. Corriger en base ferait mentir le miroir sur sa source.

### La synchro

Le VPS ne voit pas `192.168.100.x` : la synchro tourne sur une machine du
**réseau SIFA**, jamais sur le serveur. Elle exporte, zippe (~20 Mo pour 110 Mo
de CSV), et pousse vers chaque instance ; c'est le serveur qui reconstruit le
miroir en tâche de fond. La machine du LAN n'a donc besoin ni de Python ni de
SQLite — mais elle doit avoir le provider OLE DB `PCSoft.HFSQL` (celui du client
RVGI ou d'Excel).

Trois prérequis côté serveur, faciles à oublier :

- `client_max_body_size 64M;` dans les vhosts nginx — le défaut d'1 Mo rejette
  l'archive ;
- une clé API de portée `erp:write` **par instance** : v1 et la prod ont chacune
  leur base, et le resync nocturne de v1 écrase ses clés avec celles de prod. La
  clé à conserver est donc celle créée en prod. `MYSIFA_SYNC_URLS` accepte
  `url|clé` pour en donner une par cible ;
- `MYSIFA_SYNC_URLS` et `MYSIFA_API_KEY` dans le `.env` de la machine du LAN —
  le Planificateur de tâches Windows n'hérite d'aucune variable de terminal.

### Deux détails d'implémentation

**Jamais de WAL sur le miroir.** Une base ouverte en `mode=ro` ne peut pas créer
les fichiers `-wal` / `-shm` dont WAL a besoin, et certains montages réseau la
refusent carrément (`disk I/O error`). L'import construit un `.tmp` puis fait un
`os.replace` : l'app ne voit jamais un miroir à moitié construit, et un import
raté laisse le précédent en place.

**La disposition des colonnes** (ordre, colonnes verrouillées) est mémorisée
dans le `localStorage` du navigateur, par écran. C'est un confort d'affichage,
pas une donnée : elle ne suit pas l'utilisateur d'un poste à l'autre. Si ça doit
changer, c'est une table de préférences côté serveur.

### Une ligne sans son entête n'est pas une pièce

Sur les écrans de lignes de document, la jointure vers l'entête est marquée
`"obligatoire": True` au catalogue, et `_from()` la sort alors en `JOIN`, pas en
`LEFT JOIN`. Ce n'est pas un réglage de performance, c'est une règle de lecture :
RVGI lit la pièce puis ses lignes, il ne peut pas montrer une ligne sans pièce,
et l'écran MySifa non plus.

Le motif du 28/08/2026, pour qu'on ne le redécouvre pas : l'écran Commandes
annonçait **920 commandes à traiter** quand RVGI en montrait **178**. Sur les
880 lignes `lpos = 0` du miroir, **744 n'avaient plus d'entête** — 493 numéros
de commande, échoués là depuis 2019, dont neuf seulement avaient jamais produit
un BL. `export_rvgi_csv.ps1` filtre `corbeille = 0` **table par table** : quand
RVGI met une commande à la corbeille sans marquer ses lignes, l'entête ne sort
pas de l'export et les lignes, elles, sortent. Le `LEFT JOIN` les affichait avec
un client vide et une date de création vide — donc comme des commandes.

Le défaut touchait neuf écrans : commandes 744, commandes fournisseur 500,
livraisons 107, devis 79, marchés 36, appels d'offres 3 ; factures, factures
fournisseur et réceptions étaient déjà propres. **`receptions` garde son
`LEFT JOIN` volontairement** : sa jointure vise `cdf_entete`, la commande
fournisseur d'origine, pas son propre entête — une réception sans commande
reste une réception.

Si la table d'une jointure obligatoire manque au miroir, `adapter_ecran()`
renvoie `None` et l'écran n'est pas proposé. L'abandonner en silence rendrait
l'écran faux, ce qui est pire que de ne pas l'avoir.

**Le carnet s'ouvre sur « En cours » seul, pas sur « non soldée ».** Mesuré le
même jour : les 91 lignes « Partielle » du miroir sont 10 de 2026 — celles que
RVGI montre — et 81 de 2015 à 2024, sans le moindre BL, dont `orig` et `prod`
valent 255, la sentinelle « non renseigné ». Ce sont des reliquats d'avant les
champs que RVGI utilise aujourd'hui ; les faire entrer par défaut remplacerait
un bruit par un autre. Le choix composé « Non soldée (en cours ou partielle) »
reste offert dans le rail : un filtre `enum` accepte plusieurs codes séparés par
`|`, déclarés au catalogue dans `choix`, et recollés en `IN (?, ?)` avec un
paramètre lié par code.

**Les tableaux de bord portent la même règle**, par un autre chemin.
`erp_tdb.py` compte sur `cde_ligne` seule — pas de `FROM` à modifier — donc le
prédicat s'ajoute au `WHERE` sous forme d'EXISTS corrélé, `_existe_piece()`.
Il entre dans le carnet ADV (et par lui dans retard, dormant, semaine et la
liste des lignes en retard), dans « lignes sans dossier », dans les « écartées »
et dans l'encours du TDB Direction ; côté BL, `_existe_piece(sch,
entete="liv_entete")` fait la même chose pour « à facturer ». **Tout nouveau
compteur bâti sur une table `*_ligne` doit le porter.**

Le carnet du tableau de bord retient `COALESCE(lpos,0) = POS_EN_COURS`, pas
`<> POS_SOLDEE` — la même définition que le filtre par défaut de l'écran
Commandes, pour la raison exposée plus haut : sur 91 lignes « partielle »,
81 sont des reliquats de 2015-2024. Les deux corrections ensemble ont ramené
la tuile « Commandes à traiter » de **683 commandes sur 999 lignes** à
**100 sur 136**, et ce 136 est exactement le total que rend l'écran Commandes
ouvert sur son filtre par défaut. C'est le point : deux écrans ne donnent
jamais deux chiffres pour le même sujet.

**Le contrôle qui retrouve le défaut**, sur n'importe quel écran à jointure :

```sql
SELECT COUNT(*) FROM "<table_ligne>" l
 WHERE NOT EXISTS (SELECT 1 FROM "<table_entete>" e WHERE e.numero = l.numero);
```

### Filtrer et exporter une vue

Deux mécanismes de filtre cohabitent, volontairement.

**Le rail de gauche** porte les filtres MÉTIER déclarés au catalogue
(`"filtres"` de l'écran) : Position, Client, plage de dates. Ce sont eux qui
portent les valeurs par défaut — un carnet de commandes s'ouvre sur « En
cours ». Ils voyagent en `f_<nom>`.

**Les en-têtes de colonne** portent un filtre libre sur n'importe quelle
colonne AFFICHÉE, avec un opérateur : contient, ne contient pas, est égal /
différent, commence / finit par, supérieur, supérieur ou égal, inférieur,
inférieur ou égal, compris entre, est vide, n'est pas vide. Ils voyagent en
`c_<colonne>=<operateur>:<valeur>` (`entre` prend `v1|v2`). Les deux jeux se
combinent en ET ; un filtre d'en-tête n'efface jamais un filtre de rail.

Trois choses à ne pas défaire :

- **Les opérateurs sont déclarés côté serveur** (`OPS_PAR_FAMILLE` dans
  `erp_mirror.py`) et servis par `/api/erp/meta`. La page n'en redéfinit aucun.
  Une liste recopiée des deux côtés finit par proposer un opérateur que le
  serveur refuse.
- **Rien du client n'entre dans le SQL.** Le nom de colonne est résolu contre
  les colonnes de l'écran — donc contre le catalogue —, l'opérateur contre la
  table, la valeur passe en paramètre lié, et un `%` tapé par l'utilisateur est
  échappé au lieu de devenir un joker.
- **« Est vide » connaît les sentinelles.** Une date à `30/11/1999`, un prix à
  `0`, un maximum à `99999999999.99` s'affichent comme « rien » via
  `nettoyer()` : le filtre dit la même chose, sinon « est vide » ne ramènerait
  aucune des lignes qui montrent un tiret. Même logique pour les dates, toujours
  comparées sur `substr(...,1,10)` — le miroir les stocke avec une heure.

**L'export** (`GET /api/erp/{ecran}/export`, bouton dans le pied de grille)
rejoue exactement la requête de la vue et rend un `.xlsx` : mêmes filtres, même
tri, mêmes colonnes dans l'ordre où l'utilisateur les a rangées — c'est le
paramètre `cols`, la seule chose que le serveur ne peut pas deviner puisque
déplacer une colonne est un réglage de navigateur. Il ne pagine pas : il ramène
tout le résultat, plafonné à `TAILLE_EXPORT_MAX` (20 000). Au-delà le fichier
sort quand même, tronqué, et la feuille « Critères » le dit en toutes lettres —
un fichier silencieusement incomplet serait pire qu'une erreur. Les nombres
sortent en nombres et les dates en dates, avec leur format : une quantité
écrite en texte ne se somme pas, et c'est tout l'intérêt du fichier.

---
