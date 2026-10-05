# Reprise des matières (octobre 2026) — suite et idées

Le chantier du 1er au 2 octobre 2026 est en production depuis la promotion du
02/10 au soir :
- reprise de l'inventaire physique du 01/10 ;
- variantes fournisseur, avec un seul fournisseur principal partagé avec Coûts matières ;
- fusion de 6 paires de fournisseurs en double ;
- déstockage résolu par la référence MyStock (`*_ref_id`) ;
- comparaison des stocks MySifa / RVGI par laize ;
- vues par fournisseur et par laize ;
- export de l'inventaire en Excel et PDF.

Ce document liste ce qui reste à faire, à la main ou en développement.

---

## 1. À corriger à la main dans MySifa

Ces trois points viennent du rapport de reprise, lu sur la production le 02/10/2026.

- **Couché fluo jaune 90 g/m²** (fiche 46) : une ligne de l'inventaire n'avait
  pas de laize et a été ignorée : 0,225 bobine en « A FOND », environ 2 700 m.
  → Retrouver la laize, puis passer un inventaire sur la fiche.
- **PP transparent adhésif permanent acrylique** (fiche 65, complexe) : 10
  bobines à l'« ATELIER » ignorées, faute de laize. Environ 35 000 m manquent :
  la fiche affiche 6,4 bobines au lieu d'environ 16,4.
  → Retrouver la laize de ces 10 bobines, puis passer un inventaire sur la fiche.
- **Adhésif thermofusible enlevable léger** (fiche 28) : deux prix sont chez
  Jaour alors que le fournisseur principal est Bostik. Le prix en vigueur dans
  Coûts matières n'est donc pas celui de Bostik sur ces deux déclinaisons.
  → Trancher le bon fournisseur et, au besoin, le choisir comme principal dans
  l'onglet Fournisseurs de la fiche.

## 2. Données matières à compléter

- 30 consommables sans conditionnement (`unites_par_palette`). Tant qu'il manque,
  le stock ne se convertit pas en unités : les mandrins restent en palettes au
  lieu de s'afficher en tubes, et les cartons ne passent pas en unités.
- 3 fiches sans métrage par bobine : le stock en mètres ne se calcule pas.
- Article RVGI **1109/0003** : 35 000 m par bobine, probablement 3 500. À
  vérifier sur la fiche fournisseur, puis à corriger dans RVGI ou sur la variante.
- Fiche **89** : faute de frappe « Thernique » dans la référence, et une
  sous-catégorie « Complexe » à revoir.

## 3. Points ouverts dans le code (constatés, non traités)

- **MyProd, sortie de matière (SM)** : refuse une quantité fractionnaire, alors
  que le stock se tient en bobines équivalentes (0,25 bobine).
- **MyProd, entrées et sorties de matière (EM/SM) sur une matière laizée** :
  le mouvement ne porte pas la laize, donc le stock par laize ne bouge pas.
- **Réceptions RVGI** : rien n'entre en stock automatiquement tant que la date de
  mise en service (`reception_rvgi_depuis`, dans les réglages) n'est pas choisie.
  C'est voulu, mais il faut décider de la date.
- **`appliquer_mouvement_mp`** : le `INSERT OR REPLACE` sur `mp_stock` remet à
  zéro les colonnes de zone (magasin / production).

## 4. Affichage : les consommables sur une seule ligne

Dans la liste des matières, vue **Fournisseur × laize**, un consommable
(carton, adhésif, mandrin, palette) s'affiche aujourd'hui sur deux lignes : un
bandeau avec le total, puis une ligne de détail qui répète les mêmes chiffres,
sans laize. C'est du bruit.

→ Pour ces catégories, **une seule ligne par référence**, qui porte :
- le nom ;
- le stock MySifa (unités de conditionnement : tubes, cartons, kg) ;
- le stock RVGI ;
- l'écart ;
- les fournisseurs.

Il n'y a pas de laize, donc pas de colonne Bobines. Le bandeau et la ligne de
détail ne restent que pour les matières en bobines (frontaux, glassines,
complexes). Même règle dans l'onglet Fournisseurs d'une fiche consommable.

## 5. Nouveau chantier : les encres

Eugène enverra les références d'encres et leurs stocks actuels.

**Ce qu'il faut**
- Une catégorie de matière « Encre », avec les références d'encres (une fiche
  par couleur ou référence fabricant), gérée au kilo.
- Le stock de départ = les stocks envoyés par Eugène, saisis par une migration
  de reprise, sur le modèle de `reprise_inventaire_mp_2026_10_01`.
- **Le stock se met à jour automatiquement à partir des stocks RVGI.**

**Ce que dit RVGI (relevé du 02/10/2026)**
- Les encres sont en type article **8** dans `mat_mat` (type d'achat 10) :
  17 articles, par exemple « UV - Flexocure Ancora 50 B3 - YELLOW ».
- Le type 808 en porte 16 autres : ce sont les doublons de variante que RVGI
  écrit à chaque réception, à ne pas compter.
- Le conditionnement est dans `libt2` (« Y5B8-0100-408N »). Il faudra voir s'il
  donne le poids d'un pot.
- Deux autres familles touchent à l'encre sans en être : les additifs
  (« Nutri-ADD Photoinitiator ») et le nettoyant LP 482 (type 15).

**À décider avant de coder**
1. **Qui fait foi pour le stock d'encre ?**
   - **Option A — RVGI fait foi :** à chaque synchronisation, le stock MySifa d'une
     encre est remplacé par le stock RVGI converti en kg, avec un mouvement
     « Synchro RVGI » tracé. Simple, mais toute saisie MySifa est écrasée.
   - **Option B — mouvements :** les réceptions RVGI entrent en stock comme les
     autres matières (régime « direct »), et les consommations sortent par
     MyProd ou le déstockage des dossiers. RVGI sert alors de contrôle, comme
     dans la comparaison des stocks.
   - Ce que demande Eugène (« se met à jour automatiquement en fonction des
     stocks RVGI ») correspond à l'option A.
2. **Unité de gestion** : le kilo, comme l'adhésif ? Ou le pot, avec un poids par pot ?
3. **Les additifs et le nettoyant** : à reprendre aussi ? Ils sont consommés
   avec les encres mais ne sont pas des encres.
4. **Les encres dans les besoins** : les fiches techniques portent-elles les
   couleurs utilisées ? Si oui, les encres pourraient entrer dans Besoins
   matières et dans le déstockage, ce qui demande une consommation estimée par
   dossier.

**Pistes techniques**
- Ajouter le type 10 au périmètre des réceptions RVGI (`reception_rvgi.PERIMETRE`),
  avec la catégorie « encre » au régime « direct ».
- Pour l'option A : un service de synchronisation qui lit le stock RVGI de chaque
  article encre apparié, avec les mêmes règles que `stock_compare` (dernier
  `qte2`, mouvement 0 et types >= 100 écartés). Il écrit l'écart par
  `appliquer_mouvement_mp` (type ajustement), ce qui laisse une trace. Il se
  déclenche à la synchronisation du miroir RVGI (`api_bridge`), comme les
  instantanés de comparaison.
- Apparier chaque article RVGI encre à sa fiche (`erp_article_matiere`) une
  fois pour toutes, au moment de la reprise.
