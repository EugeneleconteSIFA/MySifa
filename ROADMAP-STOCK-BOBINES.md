# Chantier stock matières — la bobine devient un objet

Ouvert le 02/09/2026, cadré le 09/09/2026. Suite de `erp-rvgi.md` (réceptions) et
de `of-fiches-techniques.md` (déstockage).

---

## Ce qui existe déjà — ne pas le refaire

| Brique | Où | État |
|---|---|---|
| Réception scannée | `stock_receptions` + `stock_reception_items`, `POST /api/stock/receptions` | 14 réceptions, 25 bobines, la dernière le 29/06/2026 |
| Origine d'une bobine par son code-barres | `app/services/origine_bobine.py` | cascade réception → historique → signature → dossier, avec niveau de confiance |
| Scan matière à la machine | `fab_matieres_utilisees` | 113 lignes |
| Réception depuis l'ERP | `erp_article_matiere`, `erp_reception_integree`, `/api/stock/reception-rvgi` | codé le 04/09, **0 ligne intégrée** — pas encore mis en service |
| Déstockage fin de dossier | `/api/stock/destockage/{planning_id}` — preview / valider / annuler | opérationnel : verrou documentaire OF+FT validés, le réel prime sur le théorique, contre-passation propre |
| Bouton « Déstocker » dans les slots | `planning_entries.destockage` (todo ↔ done) | en place |
| Inventaire matière | `inventaires_matieres`, `/api/stock/matieres/{id}/inventaire` | par laize, avec unités de saisie (kg / carton / palette) |
| Traçabilité | `app/routers/traca.py` — `/api/traca/chaine` | remonte dossier → lots → bobines → réception |

## Ce qui manque, en une phrase

**Le stock matière est un compteur, pas un inventaire d'objets.** `mp_stock` et
`mp_stock_laize` tiennent une quantité par matière × laize. Il n'existe nulle
part de ligne « la bobine Y2606000506 ». Le code-barres n'apparaît que dans le
journal de réception et dans le journal de scan atelier — jamais dans le stock.

D'où tout ce qui suit : pas de métrage réel, pas de reliquat, pas de séparation
magasin / production, et une traçabilité qui s'arrête à la réception.

---

## Arbitrages du 09/09/2026

1. **La bobine porte un métrage restant.** En fin de dossier on désigne les
   bobines consommées et le reliquat retourne au stock.
2. **Le métrage vient de la packing list quand elle existe, du standard matière
   sinon.** Décision révisée en ouvrant `PZH260486` : la liste porte `length(M)`
   bobine par bobine, et sur la même référence les 49 bobines vont de 17 700 à
   18 200 m — 2,5 % d'écart. Le standard `metres_lineaires_par_bobine` aurait
   effacé exactement l'écart qu'un stock réel doit montrer. Le coût est nul : avec
   les reliquats la bobine porte déjà son métrage.
3. **Magasin / production se comptent, ils ne se suivent pas.** L'inventaire a
   deux colonnes ; aucun mouvement automatique entre les deux zones. Ça vaut pour
   toutes les matières — l'adhésif et les palettes ne se scannent pas.
4. **Chaque fournisseur a son format de packing list.** Le lecteur ne devine pas :
   il propose une correspondance de colonnes, l'humain valide, et le profil est
   mémorisé par fournisseur. Même principe que l'import des grilles transporteurs.

---

## Lot 1 — `stock_bobines`, l'objet qui manque

**Table nouvelle, pas une extension de `stock_reception_items`.** Les deux ne
disent pas la même chose : `stock_reception_items` est un ÉVÉNEMENT (« ce code a
été scanné à cette réception »), et c'est lui qui fait preuve d'origine pour
`origine_bobine.py` et pour la traçabilité FSC. `stock_bobines` est un ÉTAT
(« cette bobine est en stock, il lui reste tant »). Fusionner les deux, c'est
perdre la preuve le jour où l'état change.

```
stock_bobines
  id
  code_barre        TEXT UNIQUE       -- l'identité physique
  matiere_id, laize_id
  reception_id      -> stock_receptions
  lot_fournisseur   TEXT              -- « roll batch number » de la liste
  metrage_initial   REAL
  metrage_restant   REAL
  metrage_origine   TEXT              -- packing_list | standard | saisie
  etat              TEXT              -- stock | consommee | rebut
  planning_entry_id, no_dossier       -- le dossier qui l'a consommée
  created_at, created_by_name, consomme_at
```

- Migration `2026_09_XX_stock_bobines`, reprise des 25 lignes existantes de
  `stock_reception_items` (métrage = standard, `metrage_origine = 'standard'`).
- **Invariant à contrôler, pas à supposer** : pour une matière suivie à la bobine,
  `mp_stock_laize.quantite` doit égaler le nombre de bobines à l'état `stock`.
  Un endpoint de diagnostic le vérifie et liste les écarts — il ne les corrige pas.
- Drapeau `suivi_bobine` sur `matieres_premieres` : toutes les matières laizées ne
  passeront pas à la bobine le même jour.
- Écrans : une section « Bobines en stock » dans MyStock, et le même tableau dans
  MyProd › Traçabilité (filtre matière / laize / fournisseur / code-barres).

## Lot 2 — l'entrée par liste

« Ajouter à partir d'une liste » dans l'écran Réception, rattaché à un numéro de
réception (Br) — donc à une ligne RVGI déjà intégrée, ce que `erp_reception_integree`
permet depuis le 04/09.

- Lecteur générique : on dépose le fichier, on voit les colonnes détectées, on dit
  laquelle est le code, la laize, le métrage, le lot. `stock_packing_profils`
  garde le mapping par fournisseur — la deuxième livraison du même fournisseur ne
  redemande rien.
- Sur `PZH260486` : `roll batch number` → code, `width(MM)` → laize (5 laizes dans
  une seule livraison, à répartir sur les lignes RVGI correspondantes),
  `length(M)` → métrage.
- La liste crée les bobines **sans scan**. Un scan ultérieur RATTACHE (règle du
  04/09) : il ne crée jamais un doublon et n'ajoute jamais de quantité.
- Contrôle affiché, jamais bloquant : nombre de bobines de la liste contre
  quantité annoncée par l'ERP.

## Lot 3 — le scan, unitaire et en série

- Mode série : on scanne tout, l'écran empile, on envoie d'un coup. Un tampon
  local qui survit à un rechargement — un magasinier qui perd 40 scans ne
  rescanne pas, il retape à la main et le mécanisme est mort.
- À chaque code : reconnaissance immédiate (déjà en stock ? déjà consommé ? sur la
  liste attendue ?) et cascade `origine_bobine` pour le fournisseur.
- Amélioration de la cascade : la packing list donne des identifications
  CERTAINES en volume (49 codes d'un coup pour un fournisseur), ce dont
  l'apprentissage des signatures manquait — 25 bobines en tout jusqu'ici.

## Lot 4 — stock simplifié et stock réel

Deux nombres côte à côte, partout où le stock s'affiche.

| Catégorie | Simplifié | Réel |
|---|---|---|
| frontal / glassine / complexe | nb de bobines (déjà tenu) | Σ `metrage_restant` des bobines en stock — repli : nb × standard |
| adhésif | nb de palettes = kg ÷ kg_par_palette | kg (déjà tenu) |
| carton / mandrin / palette | nb de palettes (déjà tenu) | unités = palettes × `unites_par_palette` |

Le conditionnement existe déjà en base (`cartons_par_palette`, `kg_par_carton`,
`unites_par_palette`) et vient de RVGI ; il reste éditable dans MySifa. Rien de
nouveau à créer, sauf l'affichage et le calcul du réel côté bobines.

## Lot 5 — déstockage : vérifier, puis désigner les bobines

Le mécanisme est là et il est correct sur le papier. Ce qui reste :

1. **Audit avant tout** — rejouer les dossiers terminés récents et comparer ce que
   le déstockage aurait sorti à ce que l'inventaire dit. Le point aveugle connu
   est la couverture de `mp_fiche_mapping` (61 correspondances) : une valeur de
   fiche non rattachée sort un besoin nul en silence.
2. **Désignation des bobines** : la modale liste les bobines de la matière et de
   la laize, propose celles scannées sur le dossier (`fab_matieres_utilisees`),
   décrémente `metrage_restant` et passe à `consommee` ce qui est fini.
3. Le reliquat déclaré retourne au stock avec son métrage — c'est le seul geste
   atelier ajouté par tout le chantier, et il n'est demandé que sur la dernière
   bobine d'un dossier.

## Lot 6 — inventaire : magasin et production

- `inventaires_matieres` gagne `quantite_magasin` / `quantite_production` ; leur
  somme reste `quantite_comptee`, qui reste la valeur qui fait foi.
- `mp_stock` / `mp_stock_laize` gagnent les deux colonnes à titre indicatif,
  rafraîchies à chaque inventaire. `quantite` ne change pas de sens — rien
  ailleurs dans l'application ne casse.
- Pour une matière suivie à la bobine, l'écran de comptage part de la liste des
  bobines attendues : on coche ce qu'on trouve, et les manquantes sont l'écart.

---

## Ordre

1 → 2 → 3 → 4 → 6 → 5. Le lot 5 passe en dernier parce que désigner des bobines
suppose qu'il y en ait en base, et que son audit a plus de valeur une fois le
stock réel visible. Les lots 1 à 3 se livrent ensemble ou pas du tout : une base
bobines sans moyen de la remplir ne sert à rien.

## Prérequis hors code

- **Mettre en service la réception RVGI** (`PUT /api/stock/reception-rvgi/mise-en-service`).
  Elle est codée depuis le 04/09 et n'a jamais tourné : `erp_reception_integree`
  est vide. Le lot 2 s'appuie dessus.
- Rassembler 2 ou 3 packing lists d'autres fournisseurs, pour que le lecteur soit
  écrit contre plusieurs formats et pas contre un seul.
