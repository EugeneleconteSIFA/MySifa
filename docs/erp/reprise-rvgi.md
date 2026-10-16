# Reprise RVGI → nouvel ERP (`gc_*`) — spécification de mapping

Spécification du script de reprise **rejouable** miroir RVGI (`data/erp_mirror.db`, `ERP_MIRROR_DB`)
→ tables `gc_*` de `production.db`. Rien n'est codé ici : ce document dit quoi lire, quoi écrire, et
ce qui piège.

Relevé du 16/10/2026 sur le miroir synchronisé le 15/10 (61 tables). Les comptages cités ont été
obtenus par les requêtes données dans chaque section ; les relancer avant la bascule. Lire d'abord
`.claude/rules/erp-rvgi.md` et `docs/rvgi/data_rvgi.md`.

---

## 0. Règles communes

**Source et filtre.** Le miroir ne contient en principe que des lignes `corbeille = 0` (filtre
appliqué à l'export), mais le script le **répète** partout, des deux côtés de chaque jointure
(`corbeille` est un INTEGER dans le miroir ; toute valeur ≠ 0 est une ligne morte). `stk_hist` et
`stm_hist` n'ont pas la colonne. Une ligne de document sans son entête n'est pas une pièce :
toujours `JOIN` sur l'entête (cf. les 744 lignes orphelines du 28/08/2026). Jamais de `SELECT *` sur
`fic_clt` / `fic_fou` : lister les colonnes.

**Identité et rejeu.** Chaque ligne écrite porte `origine = 'rvgi'` et un `origine_ref` stable. Le
script fait un *upsert* sur `(origine, origine_ref)` : relancé, il met à jour au lieu de dupliquer ;
il ne supprime jamais. Une pièce modifiée dans l'ERP depuis son import n'est plus réécrite — elle
est signalée au rapport d'écarts.

| Objet | `origine_ref` |
|---|---|
| client / fournisseur | `clt:<numero>` / `fou:<numero>` |
| produit fini, prestation | `art:<code1>/<code2>` (via `_erp_reference`) |
| matière | `mat:<code1>/<code2>/<type>` |
| pièce | `<table entête>:<numero>` (ex. `cde_entete:9932399`) |
| mouvement d'ouverture | `commentaire = 'Ouverture RVGI'`, `cree_par = 'reprise'` |

Les lignes de pièce n'ont pas d'`origine_ref` : `rang` = n° de ligne RVGI (`ligne`), unique dans la
pièce, suffit à les retrouver.

**Conversions** (via `Decimal`, arrondi au plus proche, jamais `int(float)`) :

| Grandeur | Règle | Exemple |
|---|---|---|
| montant € → `*_cents` | `round(x × 100)` | 23,78 → 2378 |
| quantité → `*_milli` | `round(q × 1000)` | 1 500 000 étiquettes → 1 500 000 000 |
| taux % → `*_bp` | `round(p × 100)` | 20 → 2000 ; `comrep` 0,3 → 30 |
| longueur mm → `*_dmm` | `round(mm × 10)` | laize 470 → 4700 |
| date | `substr(x, 1, 10)` | `2026-10-14 00:00:00` → `2026-10-14` |

**Sentinelles → NULL** (neutralisées à la lecture, comme `nettoyer()` de `erp_mirror.py`) :

| Valeur | Sens | Traitement |
|---|---|---|
| `1999-11-30` | date vide | NULL |
| `1899-12-30` | date « zéro » (fiche de réappro `mvt = 0`) | ligne ignorée |
| `2099-12-31` | sans fin de validité | `fin` NULL |
| `99999999999.99`, `9999999999.99` | pas de maximum | NULL |
| `4710000000` | compte comptable vide | `''` |
| `255` sur un octet | non renseigné | NULL / défaut |
| `0` sur un prix | non renseigné, **jamais gratuit** | pas de tarif, prix NULL |
| année aberrante (`cde_entete.amjc` 2040, `liv_entete.amje` 2027) | faute de frappe | conservée, signalée |

**Typage.** `code1/code2/code3` en TEXT ; `code2` complété à 4 chiffres s'il est numérique — appeler
`_erp_reference()` (`app/routers/reconciliation.py`), ne pas la réécrire. Codes d'unité en
majuscules (`cuv = 'u'`, `'c'` existent). Booléens WinDev : **1 = non, 2 = oui** sur `m1_film` /
`m1_syn` (les films PE portent 2). `bloq` : 1 = actif, 2 = inactif, 3 = état inconnu (démontré dans
`app/core/migrations/2026_08_26_rvgi_tiers.py`).

**Date de bascule.** Un paramètre `DATE_BASCULE` fixe la date des mouvements d'ouverture et le seuil
des documents « ouverts ».

---

## 1. Référentiels

### 1.1 `gc_tva` ← `fic_tva` (3 lignes)

| `fic_tva.code` | taux | usage relevé (lignes de facture 2025+) | → `gc_tva.code` |
|---|---|---|---|
| 1 | 20 % | 5 799, clients `fis = 1` | `N` |
| 9 | 0 % | 267, clients `fis = 4` (UE) | `UE` |
| 8 | 0 % | 285, clients `fis = 2` (5 clients FR/IT) | **à créer**, Q1 |

`compte_deductible ← ach`, `compte_collecte ← vte`. RVGI écrit les comptes sur **10 chiffres
complétés de zéros** (`4457120100`, `4456600000`) : règle proposée, retirer les zéros de droite puis
compléter à 6 (`445660`, `44571201`) — Q2. `4710000000` → `''`.

Régime du tiers `fic_clt.fis` → `gc_tiers.tva_code` : 1 → NULL (taux de l'article), 4 → `UE`, 3 →
`EX` (CH, US, CA), 2 → code de Q1.

### 1.2 `gc_modes_paiement` ← `fic_reg` (13 lignes)

`numero` est le mode ; `fic_reg` ne porte **aucun** délai.

| `numero` | `lib` | → code |
|---|---|---|
| 1, 3 | Virement (deux fois) | `VIR` (fusion, Q3) |
| 2 | Effet | `LCR` ? (Q3) |
| 4 | Prélèvement | `PRLV` |
| 5 / 6 | LCR acceptée / non acceptée | `LCR` / `LCRNA` (à créer) |
| 7 | BOR | `BOR` (à créer) |
| 8 | Mandat administratif | `MANDAT` (à créer) |
| 9, 13 | Virement 8 j avant expédition / sur proforma | `VIRAV` (à créer) |
| 10 | Comptant | `COMPT` (à créer) |
| 11 | Chèque avec escompte 2 % | `CHQ` (+ `escompte_bp` sur le tiers) |
| 12 | Carte VISA | `CB` |

Correspondance tenue **dans le script** (décision de reprise, pas un référentiel), validée par le
métier.

### 1.3 `gc_conditions_paiement` ← triplet `(del, de1, de2)`

RVGI ne nomme pas les conditions : tiers et pièces portent un triplet. On crée **une condition par
triplet distinct** utilisé par un tiers actif ou une pièce reprise (50 triplets sur `fic_clt`).
Décodage vérifié en recalculant `ecc_ech.amje` depuis `vte_entete.amjf` (factures depuis 05/2026) :

| `de1` | règle RVGI | exemple vérifié | → (`jours`, `fin_de_mois`, `jour_du_mois`) |
|---|---|---|---|
| 1 | date + `del` (`de2` ignoré) | 04/05 + 30 → 03/06 | (`del`, 0, 0) |
| 3 | date + `del`, puis fin de mois | 05/05 + 45 → 30/06 | (`del`, 1, 0) |
| 2 | date + `del`, puis le `de2` (30/31 = fin de mois) | 05/05 + 45, le 30 → 30/06 | `de2 ≥ 28` : (`del`, 1, 0) ; sinon Q4 |
| 5 | date + `del`, fin de mois, puis le `de2` du mois suivant | 04/05 + 30, le 15 → 15/07 | (`del`, 1, `de2`) ; `de2 = 31` → (`del`, 1, 0) |
| 4 | **fin de mois, puis + `del`** | 05/05 → 31/05 + 45 → 15/07 | **non représentable** (Q4) |

Le cas 4 touche 412 clients dont 88 actifs (« 45 jours fin de mois » au sens fin de mois puis + 45)
; `de1 = 255` (3 clients actifs) = non renseigné : `calculs.date_echeance()` applique les jours
**avant** la fin de mois. Il faut une colonne de plus (ex. `jours_apres_fdm`) avant la reprise.
Codes proposés : `{del}J`, `{del}FM`, `{del}FM{de2}`, `FM+{del}`.

```sql
SELECT reg, del, de1, de2, count(*) n FROM fic_clt
 WHERE corbeille = 0 GROUP BY 1,2,3,4 ORDER BY n DESC;
-- observé : 3/60/1/0 = 180, 7/45/4/0 = 175, 3/30/1/0 = 158, 1/30/1/0 = 108…
```

### 1.4 `gc_pays` ← `fic_pays` (241)

`code` (ISO-2) → `code`, `pays` → `libelle` (capitalisé). `ue` n'existe pas dans RVGI : garder le
seed `gc_bases`, 0 pour les nouveaux. `INSERT OR IGNORE`. 16 clients ont `cpays` NULL → `FR`,
signalés.

### 1.5 `gc_unites` ← `fic_uv` (35) ∪ `fic_ua` (46) ∪ `fic_uc` (138)

Les trois tables partagent les codes (`11` = Mille, `10` = M²…) ; `nombre` est le **diviseur de
prix**. Une unité RVGI se replie en (`gc_unites.code`, `base_prix`) :

| codes RVGI | libellé | → unité | `base_prix` |
|---|---|---|---|
| `11` | Mille | `ETQ` | 1000 |
| `25` | Mille planches | `PL` (à créer) | 1000 |
| `19` | Cent | `U` | 100 |
| `15`, `U` | Unité | `U` | 1 |
| `5`, `BOB` | Bobine | `BOB` | 1 |
| `1`, `C` | Carton | `CART` (à créer) | 1 |
| `14` | Rouleau | `ROUL` (à créer) | 1 |
| `10`, `M²` | Mètre carré | `M2` | 1 |
| `22` | 100 m² | `M2` | 100 |
| `12` | Mètre linéaire | `ML` | 1 |
| `8`, `KG` | Kilogramme | `KG` | 1 |
| `T` | Tonne | Q5 | |
| `26` | Forfait | `FORF` | 1 (`nombre = 0`) |
| `9`, `LITRE` | Litre | `L` (à créer) | 1 |
| `2`, `3`, `6`, `7`, `16`, `23`, `29`, `30`… | boîtes, ramettes, paravents, carnets | une unité par code | 1 |

Piège : `nombre` est incohérent d'une table à l'autre (`21` « Mille A4 » vaut 1000 dans `fic_ua`, 1
dans `fic_uv` ; `24` « Mille ml » vaut 1). Le `base_prix` se **vérifie** sur les lignes de commande
: `htn = qte × pun / vuv` tient sur 2 999 / 2 999 lignes au mille de 2025+ (`vuv = 1000`) ; `suv =
3` = forfait (`vuv = 0`, `htn = pun`).

### 1.6 `gc_familles`

- **Matières** : `mat_mat.type` → familles semées par `gc_menu_fichiers`, dont l'ordre est celui des
  libellés de `fic_para` (bloc `15TTPP`, suffixe majoritaire, cf. `erp_types.py`) : 1 `CPX`, 2
  `GLA`, 3 `VEL`, 4 `COU`, 5 `THE`, 6 `SYN`, 7 `ADH`, 8 `ENC`, 9 `CLI`, 13 `MAN`, 14 `EMB`, 15
  `DIV`, 16 `BOI`, 17 `CAR`, 18 `PAL`, 19 `PMA`. `compte_achat ← mat_fmat.atva` (même conversion
  qu'en 1.1 : `6011100000` → `601110`). `mat_fmat.libsfam` (sous-familles : Permanent, Enlevable,
  Congélation…) → `sous_famille`.
- **Produits finis** : RVGI n'a **pas** de famille de produit. `fic_art.fam` (1 à 6) est le **type
  du support** (complexe, glassine…) → `sous_famille`. La famille se déduit de `code1` : numérique →
  `ETQ` ; `TT` (rubans TTR, négoce) → `NEG` (à créer, `pf`) ; `FA`, `FB` (fournitures) → `CONSO` (à
  créer) ; `FR`, `DI`, `COM` → `PREST`.

### 1.7 `gc_depots` ← `fic_depot` (1 ligne : `RBX`, rue Rollin, Roubaix)

Un seul dépôt : renommer `PRINC` en « Roubaix — rue Rollin » plutôt que créer `RBX`.
`stk_hist.depot` (« Bâtiment2 »…) est un **emplacement**, pas un dépôt : ignoré.

### 1.8 Représentants et ADV — tables de correspondance manuelles

`gc_tiers.representant_id` et `adv_id` pointent des **comptes MySifa**. `fic_rep` (5 : Direction,
TASSART, GRANGER P., GRANGER G., MOUCHERON) se rapproche à la main d'un utilisateur ; `fic_rep.pca`
→ `commission_bp`. `fic_clt.adv` est un numéro de `gen_sala` (absente du miroir, mots de passe) :
correspondance fournie par le métier. `numrep = 52` (1 client actif) n'existe pas dans `fic_rep` →
NULL + rapport.

---

## 2. Tiers

### 2.1 Clients ← `fic_clt` (1 276 : 550 `bloq = 1`, ≈ 712 `bloq = 2`, 14 `bloq = 3`)

Tout reprendre : un client inactif reste référencé par les articles (`fic_art.code1`) et
l'historique.

| `gc_tiers` | source | règle |
|---|---|---|
| `code` | `numero` | en clair (`890`) : c'est le `code1` des articles |
| `origine_ref` | `numero` | `clt:890` |
| `est_client` | — | 1 |
| `nom_court` | `code` | mnémonique RVGI (13 doublons : pas d'unicité) |
| `raison_sociale` | `rs` | trim |
| `siret`, `tva_intra`, `rcs`, `ean`, `nif` | `siret`, `ntva`, `rcs`, `ean`, `nif` | trim, espaces retirés du SIRET |
| `email`, `telephone`, `fax`, `site_web` | `mail`, `tel`, `fax`, `http` | `mail` rempli sur 127 fiches |
| `condition_paiement` | `del`, `de1`, `de2` | 1.3 |
| `mode_paiement` | `reg` | 1.2 |
| `tva_code` | `fis` | 1.1 |
| `remise_bp` | `remise` × 100 | 0 partout |
| `escompte_bp` | `escompte` × 100 | 1 fiche à 2 % |
| `franco_cents` | `franco` | 0 → NULL ; 189 fiches à 250 € |
| `encours_max_cents` | `ecmt` | 0 partout → NULL |
| `en_compte` | `encompt` | vaut 2 partout : sens à confirmer (Q6) |
| `actif` / `etat` / `bloque` | `bloq` | 1 → actif ; 2 → `actif = 0` ; 3 → actif, `etat = 'a_qualifier'` ; `bloque = 0` (pas de blocage crédit dans RVGI) |
| `groupe_id` | `groupe` | 2ᵉ passe, si `groupe ∉ {0, numero}` (345 fiches, 0 orphelin) |
| `representant_id`, `adv_id` | `numrep`, `adv` | 1.8 |
| `commission_bp` | `comrep` × 100 | |
| `categorie1..3` | `cat1..3` | quasi vides (2 fiches) ; libellés absents du miroir |
| `langue` | `lang` | `F` → `fr` (100 %) |
| `devise` | `dev` | `EUR` |
| `transporteur_id` | `modeliv` | `expe_transporteurs`, table manuelle (1 = 1 245 fiches, 3 = 27) |
| `jours_expedition` | `nbjliv` | |
| `facturation_auto` | `rgpbl` | 1/2/3/4/5 = 5/317/949/1/4 fiches, sens à confirmer (Q7) |
| `bat_chaque_cde` | `bat` | booléen 1/2 |
| `marge_brute_bp`, `marge_nette_bp` | `dmargeb`, `dmargen` | 0 partout → NULL |
| `compte_auxiliaire` | `codcpt` | `C` + code (`CSONELOGFLEURY`) ; `cltcpt` (6 fiches) en note |
| `texte_devis/arc/bl/facture` | `texd`, `texc`, `texl`, `texf` | n° de texte RVGI, table absente du miroir (Q8) |
| `cree_le`, `modifie_le` | `amj`, `dtem` | |

Non repris : `inftpok` (et jamais `inftpmdp`), `edspe*`, `nbdev/nbarc/nbfac/nbbl` (exemplaires, sans
champ côté client), `expdev/exparc/expbl/expfac` (→ cases `envoi_*` du contact principal si Q8 le
confirme).

**Adresses** ← `fic_clta` (6 260), une ligne par `(numclt, numadr)` : `typeadr` 1 = principale (1
284, une par client), 2 = livraison (3 668), 3 = facturation (1 307), 4 = 1 ligne à classer. →
`gc_tiers_adresses` : `type` ← `principale | livraison | facturation`, `raison_sociale ← rs`,
`adresse1 ← adr1`, `adresse2 ← adr2` (+ `bp`), `code_postal ← cp`, `ville ← vil`, `pays ← cpays`,
`telephone ← tel`, `email ← mail`, `siret ← siret`, `par_defaut` = 1 pour la plus petite `numadr` du
type. Les pièces citent `numadr` (`cde_entete.dest`, `adrf`) : il faut le garder — ajouter
`origine_ref` à `gc_tiers_adresses` (`clta:<numclt>:<numadr>`), à défaut `libelle = 'RVGI
<numadr>'`.

**Contacts** : `fic_clta.i_*` ne porte que 256 interlocuteurs (rattachés à une adresse). La table
des interlocuteurs clients de RVGI n'est **pas** dans le miroir (seule `fic_foui`, côté
fournisseurs, l'est) : l'ajouter à `scripts/export_rvgi_csv.ps1` (Q9). À défaut : `nom ← i_pre + ' '
+ i_nom`, `civilite ← i_civ`, `service ← i_service`, `telephone ← i_tel`, `gsm ← i_gsm`, `email ←
i_mail`.

### 2.2 Fournisseurs ← `fic_fou` (1 217, 199 actifs) et `fic_foui` (264)

Même mapping que les clients, avec : `code ← 'F' || numero` (les numéros clients et fournisseurs se
chevauchent : 1–1 409 et 1–1 222), `origine_ref = fou:<numero>`, `est_fournisseur = 1`,
`compte_auxiliaire ← codcpt` (`F…`), `journal ← journal`, `texte_aof ← texa`, `texte_cde ← texc`,
`nb_ex_aof ← nbaof`, `nb_ex_cde ← nbcdf`, `envoi_auto_aof/cde ← expaof/expcdf`, `traite ← typcpt`
(Q8), `escompte_bp ← escompte × 100` (REAL ici). Adresse : une `principale` depuis `adr1, adr2, bp,
cp, vil, cpays`. `fournisseur_fsc_id ← fournisseurs_fsc.id WHERE rvgi_numero = numero` (lien déjà
posé côté MySifa par `rvgi_tiers`).

Contacts ← `fic_foui` : `nom ← pre + nom`, `civilite ← civ`, `service ← service`, `telephone ← tel`,
`gsm ← gsm`, `email ← mail`, `envoi_aof ← mailaof`, `envoi_cde ← mailcdf` (`def` vaut 0 partout).

**Client et fournisseur à la fois** : 9 SIREN et 46 raisons sociales en commun. Par défaut deux
fiches ; la fusion (un `gc_tiers` aux deux drapeaux) se fait sur une liste validée (Q10), jamais
automatiquement.

```sql
SELECT bloq, count(*) FROM fic_clt WHERE corbeille = 0 GROUP BY bloq;  -- 1:550  2:~712  3:14
SELECT count(*) FROM fic_fou WHERE corbeille = 0 AND bloq = 1;        -- 199
SELECT typeadr, count(*) FROM fic_clta WHERE corbeille = 0 GROUP BY 1; -- 1:1284 2:3668 3:1307 4:1
```

---

## 3. Articles

### 3.1 Produits finis et prestations ← `fic_art` (7 727 : 4 546 actifs, 3 181 `bloq = 2`)

Tout reprendre (`actif = (bloq = 1)`) : les inactifs portent historique et tarifs. Clé `(code1,
code2)` ; `type` vaut 1 partout.

| `gc_articles` | source | règle |
|---|---|---|
| `code` | `code1`, `code2` | `_erp_reference()` : `890/0112`, `FR/FRAIS_DE_PORT`, `TT/0002` |
| `nature` | `code1` | numérique, `TT` → `pf` ; `FA`, `FB` → `mp` ; `FR`, `DI`, `COM` → `service` |
| `famille`, `sous_famille` | `code1`, `fam` | 1.6 |
| `client_id` | `numclt` | `clt:<numclt>` si > 0 (= `code1` sur 4 510 fiches ; 0 sur les codes alpha) |
| `libelle` | `libc1` | |
| `designation` | `libc1..libc4` | jointes par saut de ligne |
| `libelle_client` | `cltd1..cltd4` | jointes (3 780 actifs ont `cltd1`) |
| `ref_client`, `ref_client2`, `ref_client3` | `cltc2`, `cltc2b`, `cltc2c` | `cltc1` est vide partout |
| `format_l_dmm`, `format_a_dmm` | `ftl`, `fth` (mm, REAL) | × 10 ; 89 formats décimaux ; max 9 000 mm à vérifier |
| `unite`, `base_prix` | `cuv` | 1.5 |
| `unite_achat`, `unite_conditionnement` | `cua`, `cuc` | code traduit |
| `tva_code` | `ctva` | 1 → `N` ; 9 → exonéré (14 articles, interventions à l'étranger) |
| `prix_vente_cents` | `fic_artv` | 1er palier valide (§ 4) |
| `prix_achat_cents`, `fournisseur_id` | `fic_arta` | ligne `def = 1`, sinon l'unique (sous-traitance) |
| `prix_stock_cents` | `pstk` | 39 fiches |
| `stock_mini_milli`, `stock_maxi_milli` | `mini`, `maxi` | sentinelle `maxi` (4 478 fiches) → NULL |
| `gere_stock` | `stk` | 1/2 (indicateur, pas une quantité — cf. `erp_stock.py`) ; `service` → 0 |
| `couleur`, `poids_g`, `ean`, `code_douane`, `cliche` | `coul`, `pdsn`, `bar1`, `douane`, `cliche` | `pdsn` REAL : unité à confirmer |
| `taxe_eco_cents`, `zone`, `code3` | `teco`, `rang`, `code3` | |
| `remplacement_id` | `remp1`/`remp2` | 2ᵉ passe (4 fiches) |
| `cree_le`, `modifie_le` | `amj`, `dtem` | |

Absents de RVGI : `fsc_requis` (à reprendre de MySifa), `bat_id` (lien `bat_entries` par la
référence `890/0112`), `origine_prod` (porté par la ligne de commande, `orig`).

### 3.2 Matières ← `mat_mat` (1 547 dont **1 284 de type < 100**, 1 245 actives)

Clé = **triplet** `(code1, code2, type)` : 71 couples portent plusieurs types. Types > 100 (802,
807, 817…) = variantes, **exclus**. `code1` est le n° du fournisseur principal (1 235 / 1 284), pas
un client — et 112 couples existent aussi dans `fic_art` : le code doit être préfixé.

| `gc_articles` | source | règle |
|---|---|---|
| `code` | triplet | `MP<type:02>-<code1>/<code2>` (ex. `MP02-1183/0001`) |
| `origine_ref` | triplet | `mat:1183/0001/2` |
| `nature` | `type` | `mp` ; clichés (type 9, 483 fiches) Q11 |
| `famille`, `sous_famille` | `type`, `sfam` | 1.6 (`mat_fmat.libsfam`) |
| `libelle`, `designation` | `libc1`, `libc2` | |
| `libelle_technique`, `libelle_technique2` | `libt2`, `libt2_2..10` | `libt1` est un **chemin réseau** de fiche technique → `notes` |
| `ml_par_bobine_milli` | `libt2` | parsé (« Bobine 16.000 ml », « Roll 18 000 ml », « 2.000 meters ») ; ≈ 105 des 229 laizées l'annoncent |
| `adhesif`, `protecteur` | `m1_adh`, `m1_pro` | 1er élément non vide (tableaux de 10) |
| `film`, `synthetique` | `m1_film`, `m1_syn` | `= 2` |
| `epaisseur_milli` | `m1_epais` (µm) | × 1000 ; une valeur à 13 515 µm à corriger |
| `poids_g` | `pds` | c'est un **grammage g/m²** : confirmer le sens de la colonne cible |
| `format_l_dmm` | `m1_lai` | laize par défaut ; `m1_lai_2..30` sans table cible (Q12) |
| `unite`, `base_prix` | `cua` | Q13 (ML ou M2) |
| `prix_achat_cents` | `pa` | 0 → NULL |
| `prix_stock_m2_cents` | `pa` si `cua` est un m² | matières laizées |
| `fournisseur_id` | `numfou` | `fou:<numfou>` |
| `stock_mini_milli`, `stock_maxi_milli` | `mini`, `maxi` | ou `stm_hist.mvt = 0` (`qte1` = mini, `qte2` = maxi, 1 851 lignes) |
| `couleur`, `code3` | `coul`, `code3` | |

FSC : aucun champ dans RVGI (seulement « FSC certified » dans `libc1`). `fsc_allegation`, `fsc_pct`,
`fsc_bois` viennent de MyStock via `mp_variantes (rvgi_code1, rvgi_code2, rvgi_type_code)` →
`matieres_premieres`. **Vérifier** si `rvgi_type_code` y est le type matière ou le type de ligne
d'achat (`cdf_ligne.type = mat_mat.type + 2`).

```sql
SELECT type, count(*), sum(bloq = 1) FROM mat_mat
 WHERE corbeille = 0 GROUP BY type ORDER BY type;
-- 1:146 2:19 3:10 4:11 5:33 6:10 7:62 8:60 9:483 13:107 14:41 15:113 16:43 17:108 18:7 19:31 ; 8xx : 263
```

### 3.3 Prestations, frais, commentaires

Les `fic_art` à `code1` alpha (≈ 295 fiches) : `FR/*` (frais de port, frais de clichés, prestation
diverse, non-conformité), `DI/REMISE_EX`, `DI/SERIALISATION`, `COM/0001` (ligne de commentaire).
`nature = 'service'`, `gere_stock = 0`, `unite` selon `cuv` (souvent `15` ou `26` forfait).
`COM/0001` ne devient pas un article : ses lignes deviennent du texte libre (`article_id` NULL).

---

## 4. Tarifs → `gc_tarifs`

Dépiler les tableaux : **une ligne `gc_tarifs` par palier renseigné**. Un palier est retenu si `prix
> 0` et `qtemin` strictement croissant (RVGI laisse des coquilles : `qtemin_2 = 0` avec un prix,
`qtemin_3 = 28.93` qui recopie un prix). `qtemin` en `x.01` (convention « strictement supérieur ») →
arrondi à l'unité inférieure. `qtemax` ignoré (déduit du palier suivant). `fin ← amjv` (2099 →
NULL), `debut ← amj` / `amjd`. Tarif expiré : repris `actif = 0`. `prix_cents` s'entend pour
`base_prix` unités de **l'unité de la ligne tarifaire** (`cuv`/`cua`) : si elle diffère de celle de
l'article, convertir ou écarter et signaler.

| Source | sens | `tiers_id` | indices | volume |
|---|---|---|---|---|
| `fic_artv` | vente | NULL (tarif général) | palier `k = 1..30` : `qtemin_k`, `pv_k` | 3 221, dont 763 encore valides ; `grille` 1 (3 219) / 99 (2) |
| `fic_artc` | vente | `clt:<numclt>` | idem | 692 (690 valides) ; `numclt ≠ code1` sur 370 |
| `fic_arta` | achat | `fou:<numfou>` | `qtemin_k`, `pa_k` ; `ref → ref_fournisseur` | 2 754 ; jusqu'à 9 fournisseurs par article |
| `mat_mat` | achat | `fou:<numfou_k>` | **palier N = `pafouN_k`, fournisseur k** | 1 284 matières |
| `fic_tar` | — | — | — | **à écarter** : 551 « grilles » où `pv_k = qtemin_k` (gabarit) |

Les quantités de `fic_artv` sont en **unités** (étiquettes) et le prix au mille (`cuv = 11`) :
`qte_min_milli = qtemin × 1000`, `prix_cents = pv × 100` pour `base_prix = 1000`.

**Piège `mat_mat` : les indices sont inversés par rapport à `fic_art*`.** `pafouN_k` = palier N du
fournisseur k (`numfou_k`, `ref_k`, `cua_k`, `amjv_k`). Vérifié : `pafou1_2 > 0` n'existe que si
`numfou_2 ≠ 0` (42 / 42) et `qtemin1 < qtemin2 < qtemin3` sur une même fiche. N'itérer que les `k`
où `numfou_k ≠ 0` (2ᵉ fournisseur : 45 matières, 3ᵉ : 2). `laize_dmm` NULL (prix au m², toutes
laizes), `ml_par_bobine_milli ← libt2`, `ref_fournisseur ← ref_k`. L'unité varie **par fournisseur**
: `cua = 11` (au mille) chez l'un, à l'unité chez l'autre (cartons `1058/0007` : 692 €/mille contre
0,68 €/u).

**Piège de précision** : les prix RVGI ont 3–4 décimales (0,842 €, 13,427 €, 1,22 €/m²). En centimes
pour `base_prix = 1`, 0,842 € devient 84 c (−0,2 %). Pour tout article dont un prix a plus de 2
décimales, passer `base_prix` à 100 ou 1000 (Q14).

```sql
SELECT sum(pv > 0), sum(pv_2 > 0), sum(amjv >= date('now'))
  FROM fic_artv WHERE corbeille = 0;              -- 3177 / 322 / 763
SELECT sum(numfou_2 <> 0), sum(numfou_2 <> 0 AND pafou1_2 > 0)
  FROM mat_mat WHERE corbeille = 0 AND type < 100; -- 45 / 42
```

---

## 5. Documents ouverts (pas d'historique)

Principes communs :

- Pièce reprise `statut = 'valide'`, `numero` = numéro RVGI **tel quel** (texte), `origine_ref =
  <table>:<numero>`. `ux_gc_piece_numero (type, numero)` suffit : commandes et BL sont tous deux en
  `99xxxxx` mais de types distincts.
- Entête : `tiers_id ← numclt/numfou`, `date_piece ← amjc/amjd/amje`, `date_livraison ← amjl`,
  `date_expedition ← amje`, `ref_tiers ← vref`, `condition_paiement ← (del, de1, de2)`,
  `mode_paiement ← reg`, `franco_cents ← franco`, `escompte_bp ← escompte`, `acompte_cents ←
  acompte`, `remise_bp ← rem` (si `trem` = pourcentage), `representant_id ← numrep`,
  `transporteur_id ← modliv`, `jours_expedition ← nbjliv`, `adresse_livraison_id ← dest`
  (`cde_exped` pour les adresses ponctuelles), `adresse_facturation_id ← adrf`, `contact_id ←
  numint`, `notes_internes` = « Reprise RVGI du <date> ». Totaux **recalculés** par le moteur des
  pièces puis comparés à `htn`/`ttcn` (écart > 1 c → rapport).
- Ligne : `rang ← ligne`, `article_id ← (code1, code2)` (ou triplet, type − 2, pour l'achat),
  `libelle ← des1..des4`, `unite`/`base_prix ← cuv, vuv` (`suv = 3` → forfait), `prix_cents ← pun`,
  `remise_bp ← rem`, `tva_code ← ctva`, `date_livraison ← amjl`, `date_expedition ← amje`,
  `ref_client ← vref`, `origine_prod ← orig` (1 fabrication, 2 stock, 3 sous-traitance, 255 → ''),
  `laboratoire ← lab` (1 = renouvellement ; 2, 4, 32 non documentés), `laize_dmm ← code3 × 10`
  (achat).
- **Reliquat** : il se déduit des lignes aval (`ligne_amont_id`, `qte_aval()`). Les livraisons
  passées n'étant pas reprises, la ligne est reprise pour son **reste** (`quantite_milli = qte −
  déjà livré/reçu`), quantité d'origine et déjà livré en `notes`.
- **Aucun mouvement de stock** n'est généré par une pièce reprise (BL, réception) : le stock
  d'ouverture (§ 6) l'a déjà compté.
- Après reprise : `gc_sequences.prochain` recalé au-delà du max RVGI — commande 9 932 743, BL 9 939
  107, devis 2 610 006 (AAMM + 3, mensuel), facture 26 100 065 (AAMM + 4, mensuel), cde fournisseur
  6 176, marché 770, facture fournisseur 4 335.

### 5.1 Devis en cours ← `dev_entete` / `dev_ligne`

« Ouvert » = `lpos = 0` (1 = transformé) **et** `amjv ≥ DATE_BASCULE`. Observé : 9 lignes ; 53
lignes `lpos = 0` en 2026 sans validité future (Q15). `date_validite ← max(amjv)` des lignes.

```sql
SELECT count(*), count(DISTINCT l.numero) FROM dev_ligne l
  JOIN dev_entete e ON e.numero = l.numero AND e.corbeille = 0
 WHERE l.corbeille = 0 AND l.lpos = 0 AND l.amjv >= date('now');   -- 9 lignes
```

### 5.2 Marchés ouverts ← `cdm_entete` / `cdm_ligne` (`type = 'marche'`)

« Ouvert » = `lpos IN (0, 1)` et (`amjf ≥ DATE_BASCULE` ou `amjf` vide). Observé : 50 lignes / 39
marchés (`lpos` 0 : 18, 1 : 32), plus 47 lignes `lpos` 0/1 échues à trier. `date_ouverture ← amjo`,
`date_validite ← amjf`. `cdm_appel` (167 lignes) est quasi inutilisé — aucun appel sur les marchés
de 2026 —, et `qtep` dépasse parfois `qte` (marché 750 : 10 M en `qte`, 81 M en `qtep`) : sens à
établir (Q16). RVGI ne porte pas le lien commande → marché : les commandes reprises n'ont pas de
`ligne_amont_id` vers le marché.

### 5.3 Commandes clients non soldées ← `cde_entete` / `cde_ligne`

« Ouvert » = `COALESCE(lpos, 0) = 0` (en cours), plus `lpos = 1` (partielle) **créées depuis 2025**
: les 81 partielles de 2015–2024 sont des reliquats morts (`orig`/`prod` = 255, aucun BL) — même
définition que le carnet de `erp_tdb.py`. Livré = `Σ liv_ligne.qte` sur `(numcde, lignecde)`.

```sql
SELECT c.lpos, count(*), count(DISTINCT c.numero) FROM cde_ligne c
  JOIN cde_entete e ON e.numero = c.numero AND e.corbeille = 0
 WHERE c.corbeille = 0 AND COALESCE(c.lpos,0) IN (0,1) AND e.amjc >= '2025'
 GROUP BY 1;   -- lpos 0 : 189 lignes / 122 cdes ; lpos 1 : 7 / 7 (2 partiellement livrées)
```

Champs propres : `bat`/`amjb` (BAT et sa date) → lien `bat_entries` ou `notes` ; `qtep` = quantité à
produire (`qtex` est un drapeau) ; `type_ligne` : `livrer_facturer` par défaut, prix 0 →
`livrer_sans_facture` ? (Q17). Les rattachements MySifa (`rvgi_rattachements`,
`planning_entries.dos_rvgi`) sont à repointer vers la ligne `gc_*` reprise.

### 5.4 BL non facturés ← `liv_entete` / `liv_ligne`

`liv_ligne.lpos` : 1 = facturée (`fac_no` renseigné, 35 062 lignes), 0 = non facturée, 2 sans
`fac_no` = close sans facture (104). Ouvert = `lpos = 0 AND fac_no = 0` : **908 lignes, dont 831
antérieures à juin 2026** et beaucoup à prix 0 (échantillons) ; 141 en 2026. Ne reprendre que la
fenêtre validée par la comptabilité (Q18). Ligne : `quantite_milli ← qte − qtefac`, `ligne_amont_id`
→ ligne de commande reprise si la commande l'est (sinon NULL, prix lu sur la `cde_ligne` d'origine).
Entête : `nb_colis ← col`, `nb_palettes ← pal`, `poids_g ← pds × 1000`, `recepisse ← nrec`,
`emballage ← emb` ; frais `femb` / `fport` → lignes `FR/*`.

### 5.5 Commandes fournisseurs non soldées ← `cdf_entete` / `cdf_ligne`

« Ouvert » = `lpos IN (0, 1)` et `amjc ≥ 2025-10` : 131 + 7 lignes, ≈ 69 commandes (6 lignes plus
anciennes à trier). Reçu = `Σ lif_ligne.qte` sur le **couple** `(numero, ligne)`. Article : `type` 1
→ `fic_art` (sous-traitance), 2 → outil de découpe (`out_dec`, pas d'article `gc` : texte libre,
Q19), sinon matière `(code1, code2, type − 2)`. `cua`/`vua` = unité **de prix** ; `dteconf` →
`dates_confirmees`.

### 5.6 Réceptions non facturées ← `lif_ligne`

Pas d'entête : une pièce `reception` par `(numero de commande, ref BL fournisseur, amjl)`. Ouvert =
`lpos = 0` (non facturée) : 36 lignes de 2026 ; 35 lignes `lpos = 1` sans `fac_no`, antérieures à
2026, à écarter. `ligne_amont_id` → ligne de commande fournisseur reprise. **Piège** : `qte` est en
**mètres linéaires** pour les bobines, quel que soit `cua` ; `lot` est vide partout.

---

## 6. Stock d'ouverture → `gc_mouvements` (`type = 'inventaire'`)

Un mouvement par `(article, dépôt, laize)` daté `DATE_BASCULE`, `quantite_milli` signé.

**Le stock RVGI n'est pas une somme** : chaque mouvement porte `qte1` (non signée) et `qte2`, le
stock **résultant**. Stock = `qte2` du dernier mouvement, départagé par `(amjh, id)` — la règle de
`app/services/erp_stock.py`. Ignorer `mvt = 0` (fiche de réappro datée 1899-12-30). Sens de `mvt`,
établi par `qte2 − qte2 précédent` :

| `mvt` | `stk_hist` (PF) | `stm_hist` (MP) |
|---|---|---|
| 1 | entrée manuelle (+) | entrée, 1er inventaire (+) |
| 2 | sortie manuelle (−) | sortie, consommation OF (−) |
| 3 | réception (+) | réception (+) |
| 4 | annulation de réception (−) | correction de quantité (−) |
| 5 | livraison (−) | pointage (absolu) |
| 6 | annulation de BL (+) | — |
| 10 / 99 | pointage / inventaire comptable (**absolu**) | 99 : inventaire comptable (absolu) |

**PF** ← `stk_hist`, clé `(code1, code2)` (`code3` vide, dépôt unique) : 2 067 articles ont bougé,
**451 en stock positif**, 25 négatifs (RVGI les autorise : les reprendre tels quels et les
signaler).

**MP** ← `stm_hist`, clé `(code1, code2, type, code3)`, `code3` = laize en mm → `laize_dmm`. **Piège
majeur : exclure `type ≥ 100`.** Les types 9xx (jusqu'à mars 2026) et 11xx (depuis) ne portent que
des `mvt = 3` : ce sont des cumuls de réceptions, pas du stock (1 165 clés « positives » fantômes).
Après filtre : 1 301 clés, **854 positives** (dont 165 laizées), 0 négative ; 53 clés positives sans
fiche `mat_mat` vivante → rapport. `qte2` est en **ML** pour les matières laizées : écrit tel quel
si l'unité est `ML`, × laize / 1000 si `M2` (Q13). Clichés (type 9, 476 clés positives) : exclus si
`gere_stock = 0` (Q11).

```sql
WITH d AS (SELECT code1, code2, type, code3, qte2,
                  ROW_NUMBER() OVER (PARTITION BY code1, code2, type, code3
                                     ORDER BY amjh DESC, id DESC) rn
             FROM stm_hist WHERE mvt <> 0 AND type < 100)
SELECT count(*), sum(qte2 > 0), sum(qte2 < 0) FROM d WHERE rn = 1;  -- 1301 / 854 / 0
-- PF : même requête sur stk_hist, PARTITION BY code1, code2 → 2067 / 451 / 25
```

`valeur_cents` NULL : la valorisation lit `prix_stock_cents` / `prix_stock_m2_cents` (historisés par
la migration `gc_valorisation`).

**Contrôles** avant validation :
1. Totaux PF / MP par famille comparés au dernier **inventaire comptable** RVGI (`mvt = 99`,
   30/06/2026) + mouvements depuis.
2. Article par article contre MyStock : `stock_compare.py` lit déjà `index_stock()` — l'écart doit
   être celui du dernier monitoring.
3. `Σ gc_mouvements` par article et laize = `qte2` RVGI, à zéro près.
4. Valorisation ERP à `DATE_BASCULE` (Stocks › Valorisation) contre celle de MyStock.

---

## 7. Créances et dettes ouvertes

**Constat bloquant : RVGI ne lettre plus.** `ecc_ech` porte deux lignes par facture : `pos = 0`
(`ligneech = 0`, `nbech` = nombre d'échéances : l'entête de l'échéancier) et `pos = 1` (`ligneech ≥
1` : les échéances). N'utiliser que `pos = 1`. Or `sol = 2` (soldée) s'arrête aux échéances de
janvier 2026 : **1 941 échéances / 1 910 factures restent `sol = 0` pour 7,85 M€ TTC**, soit à peu
près tout ce qui a été facturé depuis novembre 2025. `vte_entete.sol` dit la même chose (1 651
factures et avoirs 2026 non soldés). Côté fournisseurs, `vtf_entete.sol` vaut 0 sur **toutes** les
factures depuis 2024 : RVGI n'a jamais tenu les dettes. `ecc_reg` a 2 lignes.

**Conséquence** : l'encours ne peut pas venir de RVGI. Source : la **balance âgée** clients et
fournisseurs du logiciel comptable à `DATE_BASCULE` (Q20). RVGI sert à retrouver la facture, sa date
et son échéancier.

**Représentation proposée** : chaque facture ouverte de la balance âgée devient une pièce `facture`
(ou `facture_fournisseur`) **validée, entête seul** : `numero` RVGI (`vte_entete.numero` /
`vtf_entete.facf`), `date_piece ← amjf`, `tiers_id`, une ligne unique « Reprise du solde »
(`article_id` NULL, montant HT, taux de TVA de la facture) pour que les totaux `htn`/`tva`/`ttcn` se
recalculent à l'identique, `comptabilise_le` renseigné (déjà en compta : l'export FEC ne doit
**pas** la réémettre), `notes_internes` « Reprise RVGI ». Puis `gc_echeances` : `date_echeance ←
ecc_ech.amje` (`pos = 1`), `montant_cents ← mt`, `regle_cents` = mt − reste dû de la balance âgée.
Avoir non imputé → pièce `avoir` (`vte_entete.type = 2`). Une pièce unique « solde de reprise » par
tiers serait plus simple mais perdrait le numéro de facture que le client cite en payant : écartée.

```sql
SELECT count(*), count(DISTINCT nofac), round(sum(mt)) FROM ecc_ech
 WHERE corbeille = 0 AND pos = 1 AND sol = 0;   -- 1941 / 1910 / 7 847 448 €
SELECT substr(amjf,1,4), sol, count(*) FROM vte_entete
 WHERE corbeille = 0 AND amjf >= '2025' GROUP BY 1,2;  -- 2026 : sol 0 → 1615 factures + 36 avoirs
```

---

## 8. Questions ouvertes (métier)

1. **Q1** TVA code 8 (0 %, clients `fis = 2`, 5 clients FR/IT) : quel régime ?
2. **Q2** Longueur des comptes comptables (10 chiffres RVGI → 6 ou 8 ?).
3. **Q3** Modes 1 et 3 « Virement » : fusion ? « Effet » = LCR ?
4. **Q4** Condition `de1 = 4` (fin de mois puis + jours, 88 clients actifs) et `de1 = 2` avec `de2 <
   28` : étendre `gc_conditions_paiement` ?
5. **Q5** Prix à la tonne : convertir au kg ou unité `T` ?
6. **Q6** `encompt = 2` sur tous les clients : « en compte » oui ou non ?
7. **Q7** `rgpbl` (1–5) : quel mode de facturation (par BL, groupée, manuelle) ?
8. **Q8** Textes automatiques (`texd/texc/texl/texf`, `texa`), `typcpt` (traite), `exp*` : où sont
   leurs libellés ? (absents du miroir)
9. **Q9** Ajouter la table des interlocuteurs clients à l'export RVGI.
10. **Q10** Liste des tiers à fusionner client + fournisseur.
11. **Q11** Clichés (483 fiches, 476 « en stock ») : article géré en stock ou outillage MySifa ?
12. **Q12** Laizes disponibles d'une matière (`m1_lai_*`) : table à créer ?
13. **Q13** Unité des matières laizées : `ML` (stock RVGI, valorisation) ou `M2` (prix d'achat,
    `conditionnement_bobines`) ? Les deux chemins de l'ERP n'utilisent pas la même aujourd'hui.
14. **Q14** `base_prix` 100 / 1000 pour garder les prix à 3–4 décimales ?
15. **Q15** Devis : validité future seulement (9 lignes) ou tout `lpos = 0` de l'année (53) ?
16. **Q16** Marchés : sens de `qtep`, et rattachement d'un appel à sa commande ?
17. **Q17** Lignes de commande à prix 0 : « livrer sans facture » ?
18. **Q18** BL non facturés : quelle fenêtre (141 en 2026, 908 au total) ?
19. **Q19** Lignes d'achat d'outils de découpe : article ERP ou outil MySifa ?
20. **Q20** Balance âgée clients et fournisseurs à la bascule : quel export du logiciel comptable ?

---

## 9. Ordre d'implémentation recommandé

Chaque étape est un module du script, rejouable seul, avec son rapport d'écarts. On ne passe à la
suivante que si la précédente est propre.

| # | Étape | Volume (lignes) | Taille |
|---|---|---|---|
| 1 | Pays, TVA, modes, conditions, unités, familles, dépôt | 241 + 3 + 13 + ≈ 40 + ≈ 30 + ≈ 20 + 1 | XS |
| 2 | Tables manuelles : représentants, ADV, transporteurs | 5 + ≈ 10 + ≈ 3 | XS (saisie métier) |
| 3 | Clients + adresses + contacts | 1 276 + 6 260 + ≈ 256 | S |
| 4 | Fournisseurs + adresses + contacts | 1 217 + 1 217 + 264 | S |
| 5 | Articles PF et prestations (2 passes : remplacement) | 7 727 | S |
| 6 | Matières (triplet, types < 100) | 1 284 | M (parsing `libt2`, tableaux) |
| 7 | Tarifs dépilés (vente, client, achat PF, achat MP) | ≈ 3 500 + ≈ 950 + ≈ 2 200 + ≈ 1 800 | M |
| 8 | Stock d'ouverture | 451 PF + ≈ 380 MP (854 clés, clichés compris) | S, contrôles lourds |
| 9 | Commandes fournisseurs ouvertes + réceptions non facturées | ≈ 70 pièces / 138 lignes + 36 lignes | S |
| 10 | Commandes clients ouvertes + BL non facturés | ≈ 129 pièces / 196 lignes + fenêtre Q18 | S |
| 11 | Devis et marchés ouverts | 9 à 53 + 50 lignes | XS |
| 12 | Factures ouvertes (balance âgée) + échéances | ≈ 1 900 factures / 1 941 échéances, à recaler sur la compta | M (dépend de Q20) |
| 13 | Séquences, liens MySifa (OF, BAT, FSC) | 8 compteurs | XS |

Répétition générale : rejouer 1 → 13 sur une copie de `production.db` avec le miroir du jour et
comparer les rapports d'écarts d'une répétition à l'autre ; la bascule réelle est la dernière
répétition, sur le miroir de la veille au soir.
