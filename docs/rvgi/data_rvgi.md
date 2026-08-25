# RVGI — architecture des données et usage dans MySifa

RVGI est l'ERP de SIFA. Sa base s'appelle `sifa_cs`, elle tourne sur un serveur
HFSQL Client/Serveur (PC SOFT / WinDev) et contient 183 tables utiles plus
17 copies de sauvegarde. Ce document décrit ce qu'elle contient, comment la
lire sans se tromper, et ce que MySifa en tire.

Relevé du 24 août 2026 par `scripts/inventaire_rvgi.ps1`. Le détail complet est
dans `docs/rvgi/rapport_rvgi.md` (lisible) et `docs/rvgi/schema_rvgi.json`
(exploitable par script). **Relancer le script plutôt que se fier aux chiffres
ci-dessous** dès qu'ils ont plus de quelques semaines.

---

## 1. Accès

| | |
|---|---|
| Moteur | HFSQL Client/Serveur (PC SOFT) |
| Serveur | `192.168.100.199:4949` — **LAN SIFA uniquement** |
| Base | `sifa_cs` |
| Provider OLE DB | `PCSoft.HFSQL` (déjà installé sur les postes : c'est celui d'Excel) |
| Encodage | ISO-8859-1, déclaré dans `extended properties` |
| Compte | compte de **lecture seule** dédié, jamais un compte applicatif |

Chaîne de connexion type — les identifiants viennent de l'environnement, jamais
du fichier :

```
provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1";User ID=...;Password=...
```

Trois voies d'accès, par ordre de friction croissante :

- **ADO/COM** — PowerShell (`New-Object -ComObject ADODB.Connection`) ou Python
  (`win32com`). Rien à installer, même provider qu'Excel. C'est ce
  qu'utilise `scripts/inventaire_rvgi.ps1`.
- **Driver ODBC HFSQL** — à installer, suppose un DSN système, et fait planter
  `pyodbc` au niveau C (il faut `pypyodbc`). Sans intérêt ici.
- **Excel** — sert à vérifier qu'une connexion passe, jamais comme pont de
  production.

L'architecture du process doit correspondre à celle du provider : Excel 64 bits
→ Python/PowerShell 64 bits. Un « Fournisseur introuvable » alors qu'Excel
fonctionne, c'est ça.

---

## 2. Les six règles de lecture

Chacune a déjà faussé une lecture pendant le relevé initial.

### 2.1 `corbeille = 0`, partout, sans exception

RVGI ne supprime pas : il marque. Une ligne vivante porte `corbeille = 0`.
Toute autre valeur — `1`, `9`, mais aussi `2.1`, `17.1`, `18.2` — est une ligne
supprimée dont les valeurs n'ont plus aucune garantie de cohérence.

Plus d'une ligne sur deux est dans ce cas : `mat_mat` compte 7 521 lignes dont
**1 536 vivantes**, `vte_ligne` 74 190 dont 36 998, `fic_art` 41 389 dont 7 678.

Toute requête — comptage, agrégat, extrait, jointure — porte le filtre. Une
jointure doit le porter **des deux côtés**.

Les valeurs décimales restent inexpliquées (numéro de version ? de session de
suppression ?). Tant qu'on ne sait pas, `= 0` est la seule lecture sûre. Les
tables qui n'ont pas la colonne (`stk_hist`, `stm_hist`, `gen_bloq`…) sont
intégralement vivantes.

### 2.2 Des sentinelles à la place des nuls

| Valeur | Signification |
|---|---|
| `30/11/1999 00:00:00` | date vide |
| `31/12/2099` | pas de fin de validité |
| `4710000000` | compte comptable non renseigné |
| `99999999999.99` | pas de maximum |
| `0` sur un prix | non renseigné — **jamais** « gratuit » |

Prises au pied de la lettre elles produisent des agrégats absurdes. Les
neutraliser à la lecture, pas en base.

### 2.3 Les tableaux WinDev sont dépilés en colonnes

Une table a **deux vues** qui ne se déduisent pas l'une de l'autre :

- **logique** (`adSchemaColumns`) — le modèle de l'éditeur. Un tableau
  `pafou1[10]` y compte pour une colonne.
- **physique** (`SELECT *`) — ce qu'on lit réellement : `pafou1`, `pafou1_2`,
  … `pafou1_10`.

`mat_mat` : 76 colonnes logiques, **483 physiques**. `gpr_ff` : 231 / 302.
`fic_artv` : 17 / 104.

Conséquence de conception : là où MySifa aurait une table fille, RVGI a des
colonnes numérotées. Les dix prix fournisseur d'une matière sont dix colonnes,
pas dix lignes. **Replier ces tableaux vers un modèle relationnel est le gros du
travail de mapping**, et c'est là que se logeront les erreurs.

Le JSON du relevé porte les deux vues (`colonnes_logiques`,
`colonnes_physiques`).

### 2.4 Aucune liaison n'est déclarée

Le provider n'expose aucune clé étrangère : l'analyse HFSQL n'en définit pas.
Toutes les jointures de ce document sont **conventionnelles**, déduites des noms
et vérifiées sur les données. Chaque nouvelle jointure se valide sur un
échantillon avant d'être codée.

### 2.5 Des mots de passe en clair

- `gen_sala.mdp` — mot de passe des salariés, en clair
- `fic_clt.inftpmdp` — accès FTP client
- `fic_fou.inftpmdp` — accès FTP fournisseur

**Ne jamais lire ces colonnes.** Ne jamais journaliser une ligne entière de ces
trois tables. Ne jamais les recopier dans MySifa, même par un `SELECT *`
paresseux. À remonter à l'éditeur par ailleurs.

### 2.6 La base n'est pas joignable depuis le VPS

`192.168.100.199` est une adresse du réseau SIFA. MySifa tourne sur un VPS
public. **Aucun code hébergé sur le VPS ne peut interroger RVGI.** Voir §6.

---

## 3. Les deux clés qui relient tout

### 3.1 `code1` / `code2` — l'article

Partout dans RVGI, un article se désigne par ce couple : `code1` = numéro du
client, `code2` = rang de l'article chez ce client. `890` / `0112` =
« Étiquette 100 × 210 mm, 2 couleurs R° » du client 890.

`code3` s'ajoute sur les matières et les mouvements pour porter la **laize**.

**MySifa construit déjà cette clé** : `_erp_reference()` dans
`app/routers/reconciliation.py` assemble `code1` et `code2` zéro-complété sur
quatre chiffres pour produire `890/0112` — le format des références de fiches
techniques. Ne pas réécrire cette fonction, l'appeler.

Tables portant la clé : `fic_art`, `fic_artv`, `fic_arta`, `fic_artc`,
`mat_mat`, `mat_nomen`, `gpr_ff`, `gpr_ff1`, `cde_ligne`, `vte_ligne`,
`stk_hist`, `stm_hist`, `cdi_ligne`, `cdi_res`, `gpr_mat`.

### 3.2 `numero` en `99xxxxx` — la commande

`cde_entete.numero` vaut `9932399`. C'est le **numéro d'OF** que MySifa
reconnaît déjà via `_OF_RACINE_RE` (`\b(99\d{5})\b`) dans
`app/routers/api_bridge.py`.

Il se propage : `liv_ligne.numcde`, `vte_ligne.livno`, `stk_hist.numcde`,
`cdi_ligne.nocde`. Une commande se suit donc de bout en bout avec ce seul
numéro.

Attention : les autres domaines ont **leur propre numérotation**, sans rapport.
`cdf_entete.numero` = 6013 (commandes fournisseurs), `liv_entete.numero` =
9938775 (BL, dans la même plage `99xxxxx` mais séquence distincte),
`vte_entete.numero` = 26080047 (factures, forme `AAMMxxxx`),
`cdi_entete.numero` = 1018 (dossiers d'ordonnancement, séquence interne).

**Ne jamais joindre deux domaines sur `numero` seul** — toujours par la colonne
de report explicite (`numcde`, `livbl`, `nocde`, `nofac`).

---

## 4. Carte des domaines

Volumes en lignes vivantes (corbeille exclue) au 24/08/2026.

| Préfixe | Domaine | Tables | Lignes | Dernière écriture |
|---|---|---:|---:|---|
| `cde_` | Commandes clients | 9 | 120 328 | 24/08/2026 |
| `liv_` | Bons de livraison | 4 | 66 891 | 24/08/2026 |
| `vte_` | Factures de vente | 4 | 59 908 | 07/08/2026 |
| `ecc_` | Échéances et règlements clients | 4 | 43 646 | 07/08/2026 |
| `fic_` | Référentiels (articles, tiers, paramètres) | 59 | 33 565 | 24/08/2026 |
| `stk_` | Mouvements de stock produits finis | 1 | 25 588 | 24/08/2026 |
| `stm_` | Mouvements de stock matière | 1 | 18 040 | 07/08/2026 |
| `cdf_` | Commandes fournisseurs | 6 | 15 781 | 24/08/2026 |
| `vtf_` | Factures fournisseurs | 4 | 13 784 | 06/08/2026 |
| `gen_` | Utilisateurs, droits, société | 7 | 13 398 | 29/07/2026 |
| `out_` | Outillage (découpe, cylindres) | 7 | 11 134 | 05/08/2026 |
| `lif_` | Réceptions fournisseurs | 3 | 8 949 | 24/08/2026 |
| `gpr_` | Production (fiches, déclarations, sorties matière) | 9 | 5 397 | 08/07/2026 |
| `dev_` | Devis | 9 | 4 825 | 24/07/2026 |
| `cdm_` | Marchés et appels de livraison | 8 | 3 686 | 06/08/2026 |
| `mat_` | Matières et nomenclatures | 7 | 3 419 | 07/08/2026 |
| `cpr_` | Calcul de prix de revient | 11 | 502 | 17/07/2026 |
| `cdi_` | Ordonnancement atelier | 5 | 265 | **16/04/2026** |
| `col_` | Colisage | 1 | 257 | 25/02/2026 |
| `aof_` | Appels d'offres | 7 | 105 | 27/03/2025 |
| `mac_` | Machines, gammes, plages horaires | 4 | 34 | 22/04/2026 |
| `pro_` | Prospects | 6 | 9 | 18/11/2021 |
| `com_` `ecf_` `lab_` `pal_` | Modules jamais ouverts | 7 | 0 | — |

Le suffixe `_com*` désigne systématiquement des tables de **commentaires**
rattachées à l'entité principale (`cde_com`, `mat_matcomif`, `gpr_ffcomic`…) :
peu de colonnes, un champ `com`, un `typt` qui dit à quel emplacement le
commentaire s'affiche. Volume important, valeur faible — à ignorer en première
approche.

### Le module production est abandonné — c'est l'origine de MySifa

`gpr_mat` s'arrête au 10 avril 2026, `cdi_entete` au 16, `gpr_gpr` au 17. Les
autres domaines écrivent à la minute.

Ce n'est pas un incident : **SIFA a cessé d'alimenter le module production de
RVGI parce qu'il ne convenait pas, et c'est précisément ce qui a motivé la
création de MySifa.** Le suivi de production a migré, l'ERP a gardé le reste.

Trois conséquences directes :

- `cdi_*` et `gpr_gpr` / `gpr_mat` n'ont plus qu'une **valeur d'historique**.
  Ne rien construire dessus, ne pas les afficher comme un état courant.
- La traçabilité dossier ↔ lot matière que portait `gpr_mat.reflot` n'est plus
  alimentée côté ERP. Elle doit exister dans MySifa — c'est le point dur de la
  préparation FSC. Côté entrée, `lif_ligne.lot` et `stm_hist.lot` restent
  vivants et donnent la maille réception.
- `gpr_ff` (fiches de fabrication) fait exception : encore écrite le
  08/07/2026. Le référentiel technique n'a pas été abandonné avec le suivi.

C'est aussi ce qui délimite le périmètre d'une page ERP dans MySifa : elle a
vocation à montrer ce que RVGI fait encore — commercial, achats, stock,
référentiels, comptabilité client — pas à ressusciter ce que MySifa fait mieux.

---

## 5. Les tables qui comptent

Colonnes listées : celles qui portent du sens. Le reste est dans le JSON.

### Référentiels

**`fic_art` — articles / produits finis** · 7 678 vivants sur 41 389

`code1`, `code2`, `code3` (clé) · `numclt` propriétaire · `libc1..libc4`
libellés internes · `cltd1..cltd4` libellés client · `cltc1..cltc3` références
client · `ftl` × `fth` format en mm · `numart` numéro d'article ·
`fam`/`sfam`/`gamme` classement · `cua`/`cuv`/`cuc` unités achat/vente/conditionnement ·
`douane` code douanier · `nomen` nomenclature · `mini`/`maxi` seuils de stock ·
`cliche` · `pdsn`/`pdsb` poids net/brut · `amj` date de création.

**`fic_artv` — prix de vente par palier** · 3 184 · `code1`/`code2`,
`qtemin`/`qtemax` (tableau de paliers), `pv`, `amjv` fin de validité.

**`fic_arta` — prix d'achat par fournisseur** · 2 714 · idem + `numfou`, `pa`,
`def` (fournisseur par défaut).

**`fic_artc` — prix négocié par client** · 689 · idem + `numclt`, `cltc2`
(référence client), `amjd`.

**`mat_mat` — matières** · 1 536 vivantes sur 7 521 · 76 colonnes logiques,
**483 physiques**
`code1`/`code2` · `libc1`, `libc2` désignation · `libt1[10]`, `libt2[10]`
libellés techniques · `m1_lai[30]` **laizes disponibles** · `m1_epais`
épaisseur · `m1_adh` type d'adhésif · `m1_pro` protecteur (glassine) ·
`m1_syn`, `m1_film`, `m1_abs` nature · `coul` · `pds` grammage ·
`numfou[10]` fournisseurs · `ref[10]` références fournisseur ·
`pafou1[10]`…`pafou10[10]` **prix d'achat par fournisseur et par palier**,
avec `qtemin1[10]`/`qtemax1[10]` correspondants · `amjv[10]` validités ·
`stk`, `depot`, `mini`, `maxi`.

C'est la table la plus riche et la plus pénible : dix fournisseurs × dix
paliers, en colonnes.

**`fic_clt` / `fic_fou` — clients et fournisseurs** · 1 264 / 1 217 ·
`numero` clé · `code` code mnémonique · `rs` raison sociale · `groupe`
rattachement groupe · `siret`, `ntva` · adresse · `reg` mode de règlement ·
`nbjliv` délai · `adv` commercial · `lang`, `dev`.
⚠ contiennent `inftpmdp` — ne pas lire.

**`out_dec` — outils de découpe** · 2 643 · `numero` clé, cité par
`gpr_ff.ndec1..ndec5` · `machine` · `ftl` × `fta` format étiquette ·
`nbl` × `nba` = **`nbt` nombre total de poses** · `espl`/`espa` espacements ·
`eche` échenillage · `lt`/`at`/`ft` dimensions de l'outil · `nbd` nombre de
dents · `ray` rayon · `qm` quantité au tour · `nbeti` · `forme` · `etat`.

`nbt` est **la** valeur qui fait foi pour le nombre de fronts. Voir §7.

**`mac_pro` — machines** · 10 vivantes sur 43 · `code`, `nom` (`COHESIO 1`,
`COHESIO 2`, `DSI`…), `lai` laize max, `nbcoul`, `vit` vitesse, `tht`/`thd`/`ths`
taux horaires, `nbout`, `nbpap`, plus une trentaine de drapeaux de capacité
(`pel`, `dor`, `ver`, `ser`, `num`, `per`, `gau`, `emb`…).

**`mac_tra` — travaux / gammes** · 16 · `code` (machine), `tra`, `noml`
(`Fabrication`, `Dorure`…), temps et vitesses par tranche.

**`mac_ptps` — plages horaires par jour** · 8 · `j1..j7` avec `jNhd`/`jNhf`
sur six créneaux — le calendrier d'ouverture de l'atelier.

### Chaîne commerciale

**`dev_entete` / `dev_ligne` — devis** · 865 / 1 341 · `numero` (forme
`AAMMxxx`), `numclt`, `amjd`, montants.

**`cde_entete` / `cde_ligne` — commandes clients** · 19 846 / 34 942 ·
**écrit à la minute**
Entête : `numero` **`99xxxxx` = n° d'OF** · `numclt`, `rs`, `groupeclt` ·
`amjc` **date de création** · `amjl` **date de livraison prévue** · `amje` date
d'expédition prévue · `nbjliv` · `modliv` · `vref` référence client ·
adresse de livraison `lrs`/`ladr1`/`lcp`/`lville` · montants · `exped`.
Ligne : `numero` (report entête) · `ligne` · `code1`/`code2`/`code3` ·
`des1..des4` désignation · `qte` · `pub`/`pun`/`net` prix · `suv`/`vuv` unité
et coefficient de vente · `amjl`/`amje` propres à la ligne · `mar`/`lmar`/`amar`
marge · `bat`/`amjb` **bon à tirer et sa date** · `ofimp` · `qtep`, `qtex`.

**`liv_entete` / `liv_ligne` — bons de livraison** · 23 034 / 35 787 ·
**écrit à la minute**
Entête : `numero` (BL) · `numclt` · `amje` date d'expédition ·
`col` colis, `pal` palettes, `pds` poids · `modliv` · adresse de livraison.
Ligne : `numero` (report BL) · **`numcde` → `cde_entete.numero`** ·
`lignecde` → `cde_ligne.ligne` · `qte`, `qtefac` · `fac_no`/`fac_lg` → facture.

**`vte_entete` / `vte_ligne` — factures de vente** · 21 821 / 36 998 ·
Entête : `numero` (forme `AAMMxxxx`) · `numclt` · `amjf` date de facture ·
montants, TVA par taux (`htnb[9]`, `tvab[9]`) · `nfa`, `comavoir` pour les
avoirs.
Ligne : `code1`/`code2` · `des1..des4` · `qte`, `pun` · **`livbl` → n° de BL**,
**`livno` → n° de commande**, `livlg` → ligne de commande · `mach`.

36 998 lignes vivantes depuis 2015 : c'est l'historique de ce qui a réellement
été vendu, par référence, rattaché à sa commande.

**`ecc_ech` / `ecc_reg` — échéances et règlements clients** · 43 644 / 2 ·
`nofac` → `vte_entete.numero` · `amje` date d'échéance · `mt` montant ·
`ligneech`, `nbech` échéancier · `sol` soldé · `numclt`.

### Achats et stock

**`cdf_entete` / `cdf_ligne` — commandes fournisseurs** · 4 572 / 9 214 ·
même structure que `cde_*`, avec `numfou` au lieu de `numclt`. `vref` porte
souvent la référence croisée (`Offre 240814356 - ARC Sifa 9932399`) qui relie
une commande de sous-traitance à la commande client d'origine — **texte libre,
non exploitable en jointure fiable**.

**`lif_ligne` — réceptions fournisseurs** · 8 949 · `numero` → `cdf_entete.numero` ·
`ref` **n° de BL fournisseur** · `amjl` date de réception · `qte` ·
**`lot` n° de lot** · `daa`.

**`stk_hist` — mouvements de stock produits finis** · 25 588 · **à la minute**
`code1`/`code2`/`code3` · `mvt` type de mouvement · `amjh` horodatage ·
`numfouclt` tiers · `numcde` → commande · `qte1` quantité mouvementée,
`qte2` stock résultant · `des1` libellé (`Livraison du 24/08/2026`) ·
`refbl` → n° de BL · `lot` · `depot`.

**`stm_hist` — mouvements de stock matière** · 18 040 ·
structure identique, `code3` portant la laize. `des1` explicite l'origine
(`Création automatique Laize suite cde fournisseur`).

Ces deux tables n'ont **pas** de colonne `corbeille` : tout est vivant.

### Technique et production

**`gpr_ff` — fiches de fabrication** · 584 vivantes sur 1 583 · 231 logiques /
302 physiques
`code1`/`code2` article · `nmac1..nmac5` machines · `m1cod1`/`m1cod2` …
`m5cod1`/`m5cod2` **matières** · `laimat`, `laimat2..5` laizes ·
`ndec1..ndec5` **→ `out_dec.numero`** · `laiout` · `nbcoul`, `coul[10]`,
`teint[10]`, `pms[10]` couleurs et Pantone · `vitmac1..5` vitesses ·
`c1_ner` étiquettes par rouleau · `c1_dmax` diamètre max · `c1_lm`, `c1_mlr` ·
`cartlarg`/`cartlong`/`carthaut`/`cartnbetiq`/`cartpds` carton ·
`cartcode1`/`cartcode2` article carton · `palcode1`/`palcode2` article palette ·
`pallargeur`/`pallongueur`/`palnbcart`/`palnbetage` palettisation ·
`nbelame`, `noportelame`, `perfotls`, `perfointer` · `repiquage`, `impdorsal`.

C'est l'équivalent RVGI des fiches techniques Access. **Question ouverte :
`sifa_fiches_techniques.mdb` est-il alimenté depuis là, ou saisi en
parallèle ?** Si parallèle, il y a deux vérités concurrentes et
`app/services/documents_verite.py` doit arbitrer une source de plus.

**`gpr_ff1` — détail impression par fiche** · 1 202 · 20 logiques / 229
physiques : `coul[20]`, `teint[20]`, `pms[20]`, `anilox[20]`, `descriptif[20]`,
`afaire[20]`, `ordremac[20]`.

**`cdi_entete` / `cdi_ligne` / `cdi_res` — ordonnancement** · 52 / 76 / 137 ·
**arrêté**
`cdi_entete.numero` séquence interne · `cdi_ligne.nocde` → `cde_entete.numero` ·
`machine`/`travail` sur cinq positions · `tpcm`/`tpsm`/`tpst` temps calage,
marche, total · `qte`, `laizem`, `nbcoul` · `amjp`/`amjr` dates prévue/réelle.
`cdi_res` porte les besoins matière calculés (`qte`, `qtehg`, `m2qte`).

**`gpr_gpr` — déclarations de production** · 2 804 · **arrêté**
`dos` → `cdi_entete.numero` · `pt` **code opération** (les mêmes `01`…`89` que
`operations.json`) · `mach` · `operateur` · `amj` · `qtef` quantité fabriquée ·
`service`.

**`gpr_mat` — sorties matière par dossier** · 243 · **arrêté**
`dos`, `ligne` · `code1`/`code2`, `lai` · `qtes` sortie, `qtev` ·
**`reflot[10]` numéros de lot** · `saipos`.

**`cpr_*` — calcul de prix de revient** · 502 lignes sur 11 tables ·
`cpr_pv` (168 colonnes logiques) est la tête, rattachée à un numéro de devis ;
`cpr_mat`, `cpr_mo`, `cpr_out`, `cpr_tr`, `cpr_st`, `cpr_lab`, `cpr_ax` en sont
les postes. Peu utilisé (dernière écriture 17/07/2026, 35 chiffrages).
À comparer au moteur de pricing MySifa avant d'en dépendre.

### Divers

**`gen_sala` — salariés** · 34 · `numero`, `nom`, `pre`, `service`, et une
cinquantaine de drapeaux de droits (`okpa`, `okpv`, `okregclt`…).
⚠ `mdp` en clair — ne pas lire.

**`col_ligne` — colisage** · 257 · `numero` commande, `colis`, `nbprod[5]`,
`nbsprod[5]`, `typp`.

**`fic_depot`** · 1 seul dépôt : Roubaix, 45 rue Rollin.

---

## 6. Contrainte d'architecture : le VPS ne voit pas le LAN

MySifa tourne sur un VPS public ; RVGI est sur `192.168.100.x`. **Aucune page
MySifa hébergée sur le VPS ne peut interroger RVGI en direct.** C'est la
contrainte structurante de tout ce qui suit.

Trois montages étaient possibles. **Le A est en place depuis le 25 août 2026** ;
les deux autres restent documentés pour qu'on ne les reproposent pas sans savoir
pourquoi ils ont été écartés.

**A — Miroir poussé. RETENU.** Une machine du réseau SIFA exporte l'ERP en CSV
(`scripts/export_rvgi_csv.ps1`), zippe, et pousse l'archive en HTTPS vers
`POST /api/bridge/erp/miroir` avec une clé `X-Api-Key` de portée `erp:write`.
C'est le **serveur** qui reconstruit le miroir, en tâche de fond : la machine du
LAN n'a donc besoin ni de Python ni de SQLite, PowerShell suffit. MySifa lit
ensuite son propre miroir SQLite : la page est rapide, fonctionne hors réseau
SIFA, et survit à une coupure de l'ERP. Prix à payer : la fraîcheur est celle de
la synchro — deux passages par jour, 5 h et 12 h 30.

**B — Agent local interrogé par le navigateur.** Le navigateur de
l'utilisateur, lui, *est* sur le LAN. Un petit agent local exposant du JSON en
lecture pourrait être appelé depuis la page. Le précédent existe : l'agent
d'impression (`app/routers/print.py`, options interprétées par SumatraPDF).
Obstacle : une page servie en HTTPS ne peut pas appeler un `http://192.168…`
(contenu mixte) — il faut un certificat sur l'agent, ou passer par
`localhost`.

**C — Tunnel VPS → LAN.** Live, mais c'est ouvrir une route permanente vers le
réseau industriel pour un confort d'affichage. À écarter sauf besoin avéré.

Quel que soit le montage : **le sens d'écriture est unique**. RVGI est la
source, MySifa lit. Aucun code MySifa n'écrit dans RVGI, et le compte de
connexion doit rendre ça structurellement impossible.

---

## 7. Ce que MySifa en tire

### Déjà en place

- `_erp_reference()` (`app/routers/reconciliation.py`) construit `code1/code2`
  au format `890/0112` — la clé article de RVGI, déjà parlée par MySifa.
- `_OF_RACINE_RE` (`app/routers/api_bridge.py`) reconnaît `99xxxxx` — le
  numéro de commande RVGI.
- La réconciliation stocks PF de MyStock consomme un **export xlsx** de RVGI
  déposé à la main. Même donnée que `stk_hist`, par un chemin manuel.

Depuis le 25 août 2026, l'essentiel :

- **Le miroir** `data/erp_mirror.db`, 61 tables et ~343 000 lignes, reconstruit
  par `scripts/import_rvgi_csv.py`. Jetable par construction : il vit dans son
  propre fichier, hors backups de production et hors migrations, et se
  reconstitue d'un export. Il n'est pas dans git.
- **L'app `/erp`** (super administrateur uniquement) : 27 écrans déclarés dans
  `app/services/erp_catalogue.py`, servis par un moteur générique
  (`app/services/erp_mirror.py`) et une API en lecture seule
  (`app/routers/erp.py`). Ajouter un écran, c'est ajouter une entrée au
  catalogue — pas écrire une page.
- **La synchro** `scripts/sync_rvgi.ps1`, planifiée à 5 h et 12 h 30 sur une
  machine du réseau SIFA. Elle exporte, zippe, pousse vers chaque instance, puis
  **efface les CSV** — ils portent des noms de clients, des adresses et des prix.
- **La lecture seule est garantie par le pilote**, pas par la discipline : la
  connexion au miroir est ouverte en `mode=ro`, une écriture échoue.

### Gisements identifiés, par ordre de valeur

1. **`out_dec.nbt` — le nombre de poses.** Le `CLAUDE.md` documente que
   `mod_nb_front` vaut 1 sur 878 fiches Access sur 909, et qu'un dossier est
   ressorti à 55 823 km de frontal. RVGI tient la valeur rattachée à l'outil
   physique (`nbl` × `nba` = `nbt`), reliée à la fiche par `ndec1`. C'est la
   seule source qui ne dépend pas d'une saisie.
2. **`cde_entete.amjc` + `amjl` — le carnet reconstituable.** Le `CLAUDE.md`
   note que la prévision de besoins matières attend novembre 2026 faute de
   savoir ce que le carnet contenait à une date passée. Une commande créée le
   12 mai et livrée le 30 juillet *était* au carnet entre les deux : p(k) se
   calcule sur l'historique en base au lieu de s'accumuler.
   **À vérifier avant d'y compter : `amjl` porte-t-il la date promise
   d'origine, ou est-il réécrit à chaque modification ?**
3. **`stk_hist` / `stm_hist` — les mouvements en continu.** La réconciliation
   MyStock passe du dépôt manuel d'un xlsx à une synchro. `stm_hist.lot` et
   `lif_ligne.lot` portent les numéros de lot côté réception : c'est la maille
   d'entrée de la chaîne FSC.
4. **Les prix.** `fic_artv`, `fic_arta`, `fic_artc`, `mat_mat.pafou*` — prix de
   vente, d'achat, négociés, par palier et par date de validité. Aujourd'hui
   ressaisis à la main dans MyStock.
5. **`fic_art` — le référentiel produits finis.** Format, libellés interne et
   client, conditionnements, code douane. Socle de la « fiche produit calculée »
   du chantier mémoire produit.
6. **`liv_*` → `vte_*` → `ecc_*`.** Colis / palettes / poids sur le BL,
   report BL → facture → échéance. MyExpé et MyCompta lisent la même chaîne
   chacun par un bout.

---

## 8. Questions ouvertes

À trancher avant de coder quoi que ce soit qui en dépende.

- **Le pont Access** — `of.mdb` et `sifa_fiches_techniques.mdb` sont-ils
  alimentés depuis RVGI, ou saisis en parallèle de `gpr_ff` ?
- **`amjl`** — date promise d'origine ou date recalculée ?
- **`corbeille` décimal** — simple marqueur, ou historique exploitable ?
- **`mvt` dans `stk_hist`/`stm_hist`** — la nomenclature des types de mouvement
  n'est pas documentée ; à relever sur les valeurs distinctes.
- **`type` et `pos`** — présents sur presque toutes les entêtes, sens non
  établi. Probablement type de pièce et statut.
- **`lab` sur `cde_ligne`** — prend 1, 2, 4, 32 et 255 dans les données
  réelles. Seul « 1 = Renouvellement » est relevé sur les écrans RVGI ; les
  autres s'affichent en clair faute de mieux.
- **`qtex`** — vaut 1 sur toutes les lignes de l'échantillon : c'est un
  drapeau, pas une quantité expédiée. La quantité à traiter est `qtep`. Le
  catalogue a été corrigé en conséquence.
- **Les codes 255** — sentinelle WinDev pour « octet non renseigné ».
  Neutralisée à l'affichage, jamais en base.

---

## 9. Régénérer ce relevé

```powershell
$env:HFSQL_CONN = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
$env:HFSQL_UID  = '<compte lecture>'
$env:HFSQL_PWD  = '<mot de passe>'

.\scripts\inventaire_rvgi.ps1                    # tout, corbeille exclue
.\scripts\inventaire_rvgi.ps1 -Motif "cde_|liv_" # un domaine
.\scripts\inventaire_rvgi.ps1 -SansExtrait       # sans aucune donnée réelle
```

Sorties : `docs/rvgi/rapport_rvgi.md` et `docs/rvgi/schema_rvgi.json`.

Pour reconstruire le **miroir** — et non le relevé — c'est l'autre chaîne :

```powershell
.\scripts\export_rvgi_csv.ps1        # ERP -> data\rvgi_export\*.csv
python scripts\import_rvgi_csv.py    # CSV -> data\erp_mirror.db
.\scripts\sync_rvgi.ps1              # les deux + envoi aux instances MySifa
```

Les deux contiennent des extraits de données réelles (clients, prix, adresses) :
usage interne SIFA, jamais dans un ticket, un prompt public ou une pièce jointe
sortante. `-SansExtrait` produit une version diffusable.
