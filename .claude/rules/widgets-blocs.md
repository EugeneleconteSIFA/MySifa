---
paths:
  - "app/web/**/*.py"
  - "static/**/*.js"
  - "app/services/blocs_registre.py"
---
## Blocs capturables — tout bloc visible peut devenir un widget d'accueil

Décision du 03/10/2026 : l'accueil a une colonne « Mes widgets », et
l'utilisateur y épingle **n'importe quel bloc** qu'il voit dans une appli
(compteur, liste, tableau, carte machine…). Le widget charge la vraie page
dans une iframe, n'en garde que le bloc, et le rafraîchit chaque minute. Rien
n'est recalculé : droits, filtres et chiffres sont ceux de la page.

Pièces : `app/services/blocs_registre.py` (registre),
`app/routers/accueil_widgets.py` (API), `static/mysifa_blocs.js` (mode
embarqué + capture, injecté dans toutes les pages par `main.py`),
`static/mysifa_accueil.js` (colonne de l'accueil).

### Créer un bloc = le nommer

Tout nouveau bloc d'écran (une section avec un titre, une carte, un compteur,
un tableau) reçoit, **dans le même commit** :

1. un attribut sur son élément racine :
   ```js
   h('div', {className:'card', 'data-bloc':'appli.onglet.bloc'}, …)
   ```
2. une entrée dans `BLOCS` de `blocs_registre.py` : appli, libellé, URL de son
   emplacement (`/stock?tab=dashboard`, `/expe#suivi_departs`), type, valeurs
   clés, `acces` (app_id de `user_has_app_access`, ou `None`).

Le nom suit `appli.onglet.bloc`, en minuscules, et **ne change jamais**.

**Valeurs clés** — un attribut par valeur sur l'élément racine, recalculé à
chaque rendu : `'data-bloc-valeur-lignes': String(rows.length)`. Une liste ou
un tableau déclare au minimum `lignes`. Une carte d'état déclare son état en
texte lisible (`En production`), jamais le code technique. Un graphique, une
frise ou une fiche n'ont pas de valeur clé : le bloc s'affiche en entier.

**Objet suivi** (une machine, un dossier, un article) : `data-bloc-objet` avec
l'id en base, `data-bloc-objet-libelle` avec le nom lisible, et `objet="…"`
dans le registre. Jamais un nom de machine en dur.

**Bloc à ne pas rendre capturable** (formulaire de saisie, écran de
paramétrage) : ne pas poser de `data-bloc`. C'est une décision, pas un oubli —
le pre-commit avertit quand un titre de section apparaît sans `data-bloc`.

### Déplacer ou renommer un bloc

- **Déplacer** (autre onglet, autre page) : changer l'`url` de son entrée. Les
  widgets suivent tout seuls, filtres capturés compris.
- **Renommer** : nouveau nom dans `BLOCS`, l'ancien dans `alias=(…)`. Le code
  utilise toujours le nouveau.
- **Supprimer** : retirer l'entrée. Les widgets existants sont retirés à la
  prochaine ouverture de l'accueil, avec un avis.

`tests/test_blocs_registre.py` (CI) bloque : un bloc du registre absent du
code, un `data-bloc` absent du registre, un nom porté par deux fichiers.

### Rafraîchissement léger

Sans rien faire, le widget recharge la page chaque minute. Une page lourde
peut fournir un crochet qui recharge seulement ses données :

```js
window.mysifaBlocsRafraichir = function () {
  if (S.tab === 'dashboard') return loadDashboard();
  location.reload();
};
```

### Pièges

- Une page en mode embarqué (`window.MySifaBlocs.embarque`) ne doit pas ouvrir
  de modale, de visite guidée ni d'annonce : elles seraient masquées mais
  pourraient marquer « vu » côté serveur.
- `mysifa_blocs.js` et `mysifa_accueil.js` ont un `?v=` figé : l'incrémenter à
  chaque modification (dans `main.py` pour le premier, dans
  `VERSION_ACCUEIL` de `mysifa_blocs.js` pour le second).
