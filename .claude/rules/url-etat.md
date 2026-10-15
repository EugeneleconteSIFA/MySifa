---
paths:
  - "app/web/**/*.py"
  - "static/**/*.js"
---
## L'adresse dit ce qu'on regarde

Décision du 15/10/2026 : l'URL d'une page de MySifa doit suffire à retrouver
l'écran exact — onglet, sous-onglet, **filtres**, **tri** et **objet ouvert**
(dossier, fiche, compte-rendu, utilisateur). Rafraîchir, partager un lien,
ouvrir dans un nouvel onglet ou revenir en arrière ramène au même endroit.
Le texte des barres de recherche n'y va pas : c'est une saisie en cours, pas
un endroit.

### Forme

`/<appli>?<onglet>&sous=<sous-onglet>&<filtres>&tri=<col>&sens=desc&<objet>=<id>`

- Tout l'état va dans la **query**. Plus de nouveau `#onglet` : le hash
  reste lu pour les liens anciens (`MySifaUrl.hashHerite()`), puis réécrit.
  Seul l'ERP garde son routage `#/ecran?…`, cohérent et complet.
- Clés en français, en minuscules : `sous`, `periode` (raccourci glissant :
  `last7`, `thisMonth`… — les mêmes que les indicateurs d'accueil) ou
  `du` + `au` pour des dates fixes, `machine`, `operateur`, `statut`, `filtre`,
  `tri`, `sens`. Un filtre multiple répète sa clé (`machine=A&machine=B`).
- Une clé déjà en usage dans des liens (`page` de MyProd, `tab` de MyStock,
  `vue` du Planning) **garde son nom** : renommer casse tous les liens posés
  dans le registre des blocs, les annonces et les favoris.
- **Une valeur égale au défaut n'est pas écrite.** L'adresse reste courte, et
  la page sans paramètre reste la page par défaut.
- Machines, opérateurs : leur nom ou leur id tel que l'API le prend, jamais
  un libellé reconstruit.

### Le helper commun : `static/mysifa_url.js`

À inclure avant le script de la page (`?v=` figé : l'incrémenter à chaque
modification, cf. ecriture-fichiers.md).

```js
MySifaUrl.ecrire(params, {navigation: cle});  // après chaque rendu
MySifaUrl.lire().get('sous', 'kpis', ['kpis','saisies'])  // valeur validée
MySifaUrl.lire().tous('machine')               // filtre multiple
MySifaUrl.surRetour(async u => { …réappliquer, recharger… });
```

- `navigation` = ce qui fait un « endroit » : page, sous-onglet, objet ouvert.
  Quand elle change, l'adresse **s'empile** (Retour y ramène). Un filtre ou
  un tri **remplace** : dix filtres essayés ne font pas dix retours.
- Pendant `surRetour`, toute écriture remplace.
- **Fermer recule.** Revenir exactement à l'adresse qu'on avait quittée
  (fermer une fiche, « ← Retour à la liste ») fait `history.back()` au lieu
  d'empiler : sinon Retour, juste après, rouvrirait la fiche fermée.
- Une page embarquée (widget d'accueil, iframe) n'empile jamais : l'historique
  d'un iframe se mêle à celui de l'accueil.
- `bloc_…`, `capture`, `embed`, `next` sont préservés : ils appartiennent à
  `mysifa_blocs.js` et à la connexion, pas à l'état de la page.

### Comment brancher une page (modèle : MyProd, `mysifa_prod_core.js`)

1. **Une fonction qui dérive l'adresse de l'état** (`_prodParams`) : elle
   lit `S`, rend `{params, nav}`. Appelée **à la fin de `render()`** — aucun
   gestionnaire de clic n'a à penser à l'URL, un nouveau filtre ne peut pas
   l'oublier.
2. **Une fonction qui applique l'adresse à l'état** (`prodLireUrl(complet)`),
   appelée au démarrage AVANT le premier chargement de données, puis dans
   `surRetour`. Au démarrage (`complet=false`) une clé absente ne touche à
   rien — les filtres d'un indicateur d'accueil viennent d'y être posés. Au
   retour (`complet=true`) elle remet le défaut.
3. **Toute valeur lue est validée** contre la liste admise (onglet,
   sous-onglet, vue) ou un motif (`tri`) : une adresse est une saisie libre.
4. **Le chargement suit l'adresse** : une arrivée directe sur
   `?sous=retour&cr=24-1187` doit charger le compte-rendu, pas afficher
   « Chargement… ». Tester chaque sous-onglet par une adresse tapée à la main.

### Un nouvel onglet, filtre, tri ou panneau = une clé d'URL

Dans le même commit que l'onglet ou le filtre : l'ajouter à la fonction de
dérivation ET à la fonction de lecture. Un état visible qui n'est pas dans
l'adresse est un oubli, sauf exceptions assumées : recherche texte,
pagination, sections repliées, formulaire de CRÉATION en cours.

**Les fenêtres de détail en font partie** (décision du 15/10/2026) : un devis,
un OF, une fiche technique, une ligne de synthèse ouverts par-dessus la page
sont des objets ouverts comme les autres. Modèle : `_MODALES_URL` de
`mysifa_prod_core.js` — par clé, la page qui la porte, comment la rouvrir
(après chargement des données) et la fermer. Une fenêtre DOM (hors de `S`) se
déclare dans `S.urlModale` à l'ouverture et s'en retire à la fermeture ; sa
fonction de fermeture prend un `sansAdresse` pour les fermetures techniques
(réouverture, Retour du navigateur) — et ne doit donc jamais être passée nue
en `onClick` (l'événement serait pris pour `sansAdresse`). La clé de
navigation ne porte pas l'id : passer d'un détail au suivant remplace.
Fermer ou rouvrir une fenêtre au Retour ne recharge pas la page.

### Lien avec les indicateurs d'accueil

Une page dont les filtres sont dans l'adresse n'a, à terme, plus besoin de
`mysifaBlocsContexte` : l'adresse capturée les porte déjà. Tant que les deux
coexistent, les `bloc_…` font foi au démarrage : si `window.__mysifaFiltresLus`
est posé, la lecture de l'adresse **ignore ses propres filtres**. L'adresse
capturée garde le `machine=` du jour de la capture, que « Modifier
l'indicateur » ne réécrit pas (il ne touche qu'aux `bloc_…`) : le relire
rendrait les anciens filtres.

### Avancement

| Appli | État |
|---|---|
| MyProd | Fait le 15/10/2026 : page, sous-onglets, période, machines, opérateurs, dossiers, tris (saisies, traçabilité, rentabilité), Retour de prod (vue, machine, compte-rendu ouvert), fiche dossier de Traçabilité (`dossier`), entrée de rentabilité ouverte, Pilotage de rentabilité (`machine`, `semaines`, `semaine`), fenêtres de détail (`devis`, `rattachement`, `of`, `fiche`, `synthese`) |
| ERP RVGI | Déjà conforme (`#/ecran?filtres`) |
| MyStock | Partiel (`?tab=&vue=&cat=&matiere=…`) : filtres de listes et tris à ajouter, passer au helper |
| Planning, MyExpé, Paramètres, Qualité, Maintenance, RH, Compta, Tâches | À faire |
