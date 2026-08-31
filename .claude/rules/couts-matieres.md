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

Ce que la ligne garde : le camion (tarif du fournisseur pour cette matière),
Fiche, et MyStock ↗. Le champ se verrouille quand la matière a plusieurs
fournisseurs — un prix unique en écraserait un avec le tarif de l'autre — et la
ligne le dit.

Test : `node tests/test_pricing_vue_liste.js`.

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
