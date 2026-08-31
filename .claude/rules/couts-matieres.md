---
paths:
  - "app/services/mystock_prix.py"
  - "app/services/pricing/**/*.py"
  - "app/routers/stock.py"
  - "app/routers/pricing.py"
  - "app/web/stock_page.py"
  - "static/pricing_app.js"
---
## Coûts matières — où vit le prix d'une matière

Deux bases cohabitent, et une seule fait foi.

**MyStock est la source.** Une matière MyStock se décline (`mp_matiere_declinaison`) :
par **laize** pour un frontal, une glassine ou un complexe, par **grammage** pour un
adhésif. La déclinaison porte tout ce qui fait un coût :

- son **prix d'achat** : une ligne par fournisseur dans `mp_matiere_prix`, celle
  marquée `principal = 1` est le prix en vigueur ;
- son **paramétrage** : poids, grammage, devise, base de prix, incidence des taxes,
  import et transport — des colonnes de `mp_matiere_declinaison` depuis le
  4 août 2026.

De là, `compute_material_price_per_m2` sort un coût au m² sans qu'aucune fiche de
la base historique n'intervienne. La page se trouve à `/pricing/mystock/<id>` —
c'est le lien sur le coût, dans l'onglet **Matières MyStock**.

**La base « Coûts matières » (`mc_material`) est l'ancêtre**, destinée à
disparaître. L'appairage d'une déclinaison à une fiche n'est plus proposé dans
l'interface ; la colonne `mc_material_id` et `mystock_price_for_row` restent le
temps que les fiches historiques finissent de vivre.

### Ce qui circule entre MyStock et Coûts matières : le sous-total d'achat

Coûts matières saisit un **prix d'achat** fournisseur. La valorisation MyStock
affiche ce que la matière coûte **rendue** : le **sous-total d'achat**, soit
`prix + transport + taxes`, dans la devise et la base d'achat.

C'est cette valeur-là qui circule entre les deux écrans, pas le prix nu — sinon
les deux applications montrent deux chiffres pour la même matière.
`sous_total_achat()` et `prix_depuis_sous_total()` sont l'inverse exacte l'une de
l'autre (test d'aller-retour sur cinq configurations). La seconde renvoie `None`
quand la décomposition n'a pas de solution positive — un sous-total inférieur au
seul transport : on refuse plutôt que d'écrire un prix d'achat négatif.

Changer transport ou taxes déplace le sous-total **sans toucher au prix d'achat** :
`set_parametrage` pousse alors le nouveau sous-total vers la valorisation.

**Historique** — `mp_prix_historique`, au niveau de la déclinaison, avec la date,
**l'écran d'origine**, l'auteur, le fournisseur, prix avant/après ET sous-total
avant/après. Les deux valeurs, parce qu'un changement de paramétrage fait bouger
la seconde seule. Affiché en bas de la fiche `/pricing/mystock/<id>`.
`mp_valorisation_historique` reste en place : elle trace au niveau de la matière,
pour les écrans MyStock.

**Les deux sens du prix sont branchés** :

- Coûts matières → MyStock : `_mirror_principal` recopie le prix principal dans les
  champs que la valorisation lit déjà ;
- MyStock → Coûts matières : `resync_depuis_mystock` fait redescendre un prix
  corrigé sur la valorisation, la fiche matière ou par le PMP.

Un prix à 0 côté MyStock veut dire « pas renseigné » : il n'écrase jamais un tarif.

### La liste des matières est un écran de SAISIE, pas de lecture

`/pricing` ouvre une ligne par matière, et le seul geste qu'on y fait est de
corriger un prix d'achat : champ bordé et crayon visibles au repos, saisie
enregistrée au `change`, tableau non reconstruit après coup pour ne pas perdre
le focus.

**La déclinaison n'y apparaît plus du tout** (31 août 2026). Le prix d'achat ne
varie ni par laize ni par grammage — un compteur « 2 décl. », une flèche
« dériver » et un « + » y laissaient croire le contraire. Créer une laize ou un
grammage reste un geste de MyStock, sur la fiche.

**Le coût €/m² non plus.** C'est un résultat de paramétrage (poids, devise,
taxes, transport), pas une donnée qu'on lit en survolant une liste, et sa
fourchette min–max poussait le prix — la vraie raison de venir ici — hors du
regard. Il se lit et se règle sur `/pricing/mystock/<id>`, que le bouton
**Fiche** ouvre depuis la ligne.

**Colonne « Dernier prix »** — la date de la dernière saisie du prix, et l'âge
en clair dessous (« il y a 4 mois »), parce que personne ne soustrait de tête
sur quarante lignes. Au-delà d'un an l'âge s'ambre, au-delà de deux ans la
ligne passe au rouge : un rappel, aucune règle de gestion derrière. La cellule
se réécrit après une saisie en place, sans reconstruire le tableau.

La date vient de `mp_prix_historique` (`_dernier_prix_par_matiere`), la seule
table qui date une SAISIE, avec repli sur `mp_matiere_prix.updated_at` — et
uniquement sur la ligne `principal = 1`, celle du prix affiché.

**Reprise de l'historique** — `scripts/reprise_historique_prix.py --simulation`
puis `--appliquer` pose les prix en vigueur comme première ligne d'historique
(`origine = 'reprise'`, `prix_avant = NULL`, `created_at = updated_at`). Sans
lui, une matière dont le prix n'a jamais bougé depuis la mise en service de
l'historique affiche « jamais revu », ce qui est faux. Idempotent : ni les
déclinaisons déjà reprises, ni celles qui ont un vrai mouvement.

Ce que la ligne garde : le camion (tarif du fournisseur pour cette matière),
Fiche, et MyStock ↗. Le champ se verrouille quand la matière a plusieurs
fournisseurs — un prix unique en écraserait un avec le tarif de l'autre — et la
ligne le dit.

Test : `node tests/test_pricing_vue_liste.js`.

### Le poids au m² appartient au PRODUIT, pas à la matière (31 août 2026)

La matière porte **ce qu'on paie**. Le composant du produit porte **ce qu'on
consomme**. Un adhésif ne s'achète pas plus cher en 22 g/m² qu'en 17 : le prix
est au kilo, et c'est la quantité posée qui change — une décision de produit.

- `mp_produit_composant.grammage_gsm` / `perte_pct` : les colonnes qui comptent.
  Migration `mp_grammage_sur_composant`, qui recopie les valeurs des
  déclinaisons pour qu'aucun coût ne bouge le jour du déploiement.
- `cout_produit` surcharge le `weight_per_m2` du `PricingMaterial` avec
  `poids_retenu(composant)`. Les colonnes côté déclinaison restent en base —
  retour en arrière possible — mais **n'entrent plus dans aucun calcul**.
- Un composant au kilo sans grammage coûte **0 €/m²**. On ne lève pas (une
  composition incomplète ne doit pas faire tomber la liste des produits), mais
  la fiche et le récapitulatif le disent : un total amputé passe sinon pour un
  prix bas.

Les fiches matière ont donc perdu la section « Caractéristiques » et tout
affichage en €/m² — prix de revient, marge, prix de vente, « ramené au m² ».
Un €/m² suppose de savoir quelle quantité on pose ; la matière ne le sait pas.
Il lui reste son **sous-total d'achat** (prix + transport + taxes), dans sa
devise et sa base d'achat. Exception : la fiche `mc_material` de la base
historique renvoie encore `grammage_gsm` inchangé — ses propres produits
calculent toujours en €/m² — mais le champ n'est plus saisissable.

L'aperçu du coût sur la fiche produit passe désormais par
`POST /api/pricing/mystock/produits/preview` : le refaire dans le navigateur
supposerait d'y réimplémenter transport, taxes et change.

**Le transport est nommé, plus fondu dans le résultat.** L'écran affichait
« 4,200 €/kg × 0,0240 kg/m² → 0,1098 €/m² » — une multiplication qui ne tombe
pas juste, parce que le transport (0,379 €/kg, 9 % ici) y entrait sans figurer
nulle part. Un chiffre qu'on ne peut pas refaire de tête passe pour un chiffre
faux, et il avait raison de le paraître : il manquait deux termes.

`_cout_produit_mystock` renvoie donc la `breakdown` de chaque composant, comme
le fait déjà la base CM. La chaîne s'écrit en entier —
`(prix + transport + taxes) = sous-total × poids × change → coût` — les termes
nuls omis. Le transport a aussi sa ligne « dont transport » dans le
récapitulatif, sa colonne dans le détail déplié de la liste, et un lien vers le
tarif du fournisseur : nommer un coût sans donner le chemin pour le corriger
n'avance personne.

### Fusion des déclinaisons : une matière, une ligne

Le grammage parti sur le produit, la déclinaison n'a plus rien à porter que le
prix — qui n'a jamais varié de l'une à l'autre.
`scripts/fusion_declinaisons.py --inventaire`, puis `--simulation`, puis
`--appliquer` ramène chaque matière à une seule ligne : prix déplacés (doublons
de fournisseur écartés), composants repointés, historique conservé. **À sens
unique — copier la base avant.** Les matières dont les déclinaisons portent des
prix ou des fournisseurs principaux différents sont laissées de côté et listées :
les fusionner reviendrait à choisir un prix à la place de quelqu'un.

### Comment un prix d'achat devient un coût au m²

    prix de revient €/m² = (prix d'achat + transport + taxes) × taux de change

Les mêmes réglages sur les deux fiches (base CM et MyStock) :

- **Grammage (g/m²) + perte (%)** — le poids n'est jamais saisi. Il découle du
  grammage majoré de la perte : on produit rarement au gramme près, la chute et
  le calage font qu'un frontal de 70 g/m² en consomme davantage. Perte par
  défaut : 9 % sur toute nouvelle matière.
  Sur un **adhésif**, ce grammage EST la valeur de la déclinaison : « 1225 en
  22 g/m² » ne peut pas peser autre chose. La ligne du tableau et la fiche
  écrivent au même endroit, dans les deux sens. Sur une matière **laizée**, la
  déclinaison vaut une laize et le grammage reste indépendant.
- **Taxes en %** (6 = +6 %), plus un multiplicateur. Elles vivent dans l'encadré
  « Matière importée » et **ne comptent que si la matière est importée** — une
  taxe invisible qui gonfle le prix d'une matière locale serait un piège.
- **Appliquer la marge** — décochée, la matière entre dans le prix de revient
  mais sort de l'assiette de marge. Utile pour ce qu'on refacture à l'euro près.

La colonne `tax_incidence` reste en base (multiplicateur historique) mais n'est
plus lue : le calcul passe par `taxe_pct`. Reprise faite par
`mc_taxe_pct_marge_grammage`, qui met la perte des matières existantes à **0** —
appliquer 9 % d'un coup aurait renchéri tout le catalogue sans le dire.

Tests : `python3 tests/test_pricing_engine.py`,
`node tests/test_pricing_reglages_matiere.js`.

### Produits devisés depuis MyStock

`mp_produit` + `mp_produit_composant` : un produit composé de **déclinaisons**,
l'équivalent MyStock de `mc_product`. Onglet **Produits → Produits MyStock**,
fiche à `/pricing/mystock/produit/<id>`.

MyStock ne connaît pas de catégorie « silicone » : les emplacements nommés sont
**frontal, adhésif, glassine**, et toute autre matière (complexe, autre) s'ajoute
en composant libre. Le calcul ne réécrit rien — les déclinaisons sont habillées en
`PricingMaterial` et passées à `compute_product_cost`, le même moteur que la base
CM. Une seule formule de prix de revient dans l'application.

Deux refus volontaires à la création : deux matières sur un même rôle, et la même
déclinaison deux fois. Dans les deux cas le coût serait faux sans que rien ne le
signale à l'écran.

Le module n'a **pas de tableau de bord** : `/pricing` ouvre directement les
matières. La page et son endpoint ont été retirés le 4 août 2026, ils
n'apportaient rien que les deux listes ne montrent déjà.

**Import en masse** — `scripts/import_catalogue_produits.py` crée les produits
depuis le catalogue commercial, en trois temps : `--inventaire` (propose les
correspondances de noms), `--simulation` (rejoue sans écrire), `--appliquer`.
Relançable sans doublon. Test : `python3 tests/test_import_catalogue.py`.

Tests : `python3 tests/test_mystock_declinaisons.py`,
`node tests/test_pricing_declinaison.js`,
`node tests/test_pricing_produits_mystock.js`.

---
