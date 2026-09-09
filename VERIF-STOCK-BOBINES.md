# Vérifications — chantier stock bobines (09/09/2026)

Sept contrôles, dans l'ordre. À faire **sur v1**, pas en prod. Chacun dit ce qu'on
attend : si le résultat diffère, c'est un défaut, pas une variante.

---

## 1 · Les migrations passent au démarrage

Trois nouvelles migrations dans ce lot. Au démarrage de v1, les trois lignes de
bilan doivent sortir dans les logs :

```
[MySifa] migration stock_bobines : table en place, 0 bobine(s) suivie(s).
         25 ligne(s) de reception sans matiere laissees a l'historique.
[MySifa] migration stock_packing_profils : 0 format(s) de packing list memorise(s).
[MySifa] migration stock_zones_magasin_production : 6 colonne(s) ajoutee(s).
```

Puis **Paramètres → Promouvoir → Déployer → « Santé du dépôt »** : les trois en
*appliquées*, aucune en attente.

> `stock_bobines` a peut-être déjà tourné si v1 a redémarré depuis le push
> précédent — dans ce cas elle n'apparaît qu'en appliquée, sans reprint.

## 2 · Les tests

```
python3 tests/test_stock_bobines.py
python3 tests/test_packing_list.py
python3 tests/test_reception_rvgi.py
python3 tests/test_documents_verite.py
```

Attendu : « Tout est vert. » sur les quatre. Les deux derniers ne testent pas ce
chantier — ils sont là pour vérifier que je n'ai rien cassé à côté.

## 3 · L'onglet Traçabilité est au bon endroit

MyStock → sidebar → section **Outils** → **Traçabilité** (entre « Historique
mouvements » et « Étiquettes traça »). Plus rien sous Matières premières.

Attendu à l'ouverture : la liste est **vide**, avec le message qui explique
pourquoi (aucune reprise de l'historique), et la carte « Écarts au compteur » à
**0 · 0 ligne(s) contrôlée(s)**.

> Si elle affiche des lignes contrôlées dès l'ouverture, quelque chose a mis
> `suivi_bobine` à 1 sans qu'aucune bobine n'existe.

## 4 · L'import de la packing list — le contrôle qui compte

MyStock → **Réception matière** → sous-onglet **« Depuis une liste »**.
Dépose `roll batch number of 5677 PZH260486.xlsx` tel quel.

Attendu, sans que tu aies rien réglé :

| | |
|---|---|
| En-tête trouvé | ligne **2** (la ligne 1 est vide) |
| Colonnes proposées | `roll batch number` → code · `width(MM)` → laize · `length(M)` → métrage |
| Unités | **mm** et **m**, lues dans les parenthèses |
| Lot fournisseur | **vide** — et c'est voulu |
| Bobines lues | **48** |
| Métrage total | **865 440 m** |
| Refusées | **0** |
| Répartition | 440 × 7 · 470 × 9 · 510 × 7 · 530 × 18 · 570 × 7 |

Choisis ensuite une catégorie + une matière laizée, laisse « Nouveau lot de
réception », coche « Mémoriser ce format » et importe.

Après l'import, à vérifier :

- l'onglet **Traçabilité** montre les 48 bobines, avec chacune **son** métrage
  et le tag `liste` — pas un métrage identique partout ;
- la fiche de cette matière a gagné **48 bobines** réparties sur 5 laizes, et
  les laizes absentes ont été créées ;
- la carte **Écarts au compteur** reste à **0** ;
- **redépose le même fichier** : la correspondance doit revenir toute seule avec
  la mention « Format déjà validé pour ce fournisseur ». Si tu l'importes une
  seconde fois, les 48 bobines doivent être **rattachées** (0 créée) et le stock
  ne doit **pas** bouger — c'est le contrôle le plus important de la journée.

## 5 · Le scan en série survit à un rechargement

Réception matière → « Faire une réception ». Choisis matière + laize, scanne ou
tape 3 codes bidons. Puis **F5**.

Attendu : au retour, un message « 3 bobine(s) scannée(s) récupérée(s) —
réception non validée », et les 3 codes toujours dans la liste avec leur matière
et leur laize. Rien n'est entré en stock : le tampon est un brouillon.

Deuxième contrôle, dans la foulée : scanne un code **déjà entré au point 4**.
Un message rouge doit apparaître — « déjà en stock — elle sera rattachée, sans
nouvelle entrée de stock ».

Le brouillon s'efface tout seul à la validation, et se périme au bout de 12 h.

## 6 · Les deux stocks

Ouvre la fiche de la matière du point 4. Le bandeau doit porter **deux** chiffres
côte à côte :

- **Stock actuel** — 48 bobines (ce qu'on compte)
- **Stock réel** — 865 440 m, avec en dessous « somme des 48 bobine(s) en stock »
  (ce qu'on consomme)

Sur une matière **sans** bobines, le stock réel doit dire « métrage standard ×
nb de bobines ». Sur un **adhésif**, il doit être en kilos. La mention de la
source n'est pas de la décoration : elle distingue un relevé d'une
multiplication.

## 7 · L'audit du déstockage — il doit sortir une alerte

```
python3 scripts/audit_destockage.py --db data/production.db
```

**Attendu : il n'est pas vert, et c'est le résultat correct.** Voici ce que j'ai
trouvé en préparant ce script, sur la base de production :

| | |
|---|---|
| Dossiers marqués « déstocké » | **232** |
| Dossiers avec un mouvement de stock | **0** |
| Sorties de matière rattachées à un dossier | **0** sur 212 |

Le mécanisme de déstockage est écrit, testé et correct — mais **il ne tourne
pas**. Le bouton du planning ne bascule qu'un drapeau : la modale qui écrivait
les vraies sorties a été débranchée, et le code le dit lui-même
(`app/web/planning_page.py`, `toggleDestockage` — « débranchée le temps de revoir
la méthode de gestion des stocks »). Les 212 sorties existantes sont toutes
saisies à la main, sans lien avec un dossier : elles ne se comparent à aucun
besoin, donc ni écart, ni surconsommation, ni rentabilité matière.

C'est la décision qui t'attend, et je ne l'ai pas prise à ta place : **rebrancher
la modale de déstockage sur le bouton du planning**. Le socle est prêt des deux
côtés — les endpoints `/api/stock/destockage/{id}` (aperçu, valider, annuler)
n'ont jamais cessé de fonctionner, et les bobines existent maintenant pour être
désignées nommément. C'est un lot à part entière, à faire quand tu me le dis.

Le script contrôle aussi la couverture des correspondances fiche → matière : au
09/09, **7 valeurs de support** ne pointent aucune référence MyStock. Chacune
sort un besoin nul en silence.

---

## Ce qui n'est pas fait, et que je ne veux pas laisser croire fait

- **L'écran d'inventaire ne propose pas encore les deux colonnes magasin /
  production.** La base et l'API les acceptent (`quantite_magasin`,
  `quantite_production`, leur somme reste la quantité qui fait foi), l'écran
  actuel continue de fonctionner à l'identique — mais la saisie à deux colonnes
  reste à ajouter. Je ne l'ai pas fait à l'aveugle : la modale d'inventaire est
  un tableau à une colonne par ligne, et la casser aurait coûté plus cher que
  d'attendre.
- **Le déstockage ne désigne pas encore les bobines consommées.** `consommer()`
  et `remettre_en_stock()` existent dans le service et sont testés ; rien ne les
  appelle tant que la modale n'est pas rebranchée (point 7).
- **Aucune reprise de l'historique**, volontairement : les 25 codes scannés avant
  septembre n'étaient rattachés à aucune matière.

## Si tu ne fais qu'un seul contrôle

Le **point 4**, jusqu'au double import. Il exerce d'un coup le lecteur de
fichier, la création des bobines, le calcul du stock, le rattachement sans double
comptage et le contrôle de cohérence.
