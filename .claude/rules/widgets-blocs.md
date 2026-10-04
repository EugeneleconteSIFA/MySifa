---
paths:
  - "app/web/**/*.py"
  - "static/**/*.js"
  - "app/services/blocs_registre.py"
---
## Blocs capturables — tout bloc visible peut devenir un widget d'accueil

Décision du 03/10/2026 : l'accueil a une colonne « Mes widgets », et
l'utilisateur y épingle **n'importe quel bloc** qu'il voit dans une appli
(compteur, liste, tableau, carte machine…). Depuis le 04/10/2026, un widget
n'affiche que des **valeurs** (1 à 4) : la page est chargée hors écran, seules
ses valeurs clés remontent. Rien n'est recalculé : droits, filtres et chiffres
sont ceux de la page.

Pièces : `app/services/blocs_registre.py` (registre),
`app/routers/accueil_widgets.py` (API), `static/mysifa_blocs.js` (mode
embarqué + capture, injecté dans toutes les pages par `main.py`),
`static/mysifa_accueil.js` (colonne de l'accueil),
`static/mysifa_blocs_sources.js` (lecture des valeurs par API).

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
texte lisible (`En production`), jamais le code technique. **Un bloc sans
valeur clé n'est pas capturable** (le registre le refuse) : pour un graphique
ou une frise, déclarer au moins un chiffre qui le résume.

**Nombre distinct du texte** : quand la valeur affichée n'est pas un nombre
(« 1h 57min »), poser aussi `data-bloc-nombre-<cle>` (`117`) : c'est lui que
l'alerte compare.

**En-tête et contenu** : le widget porte déjà le nom du bloc. Marquer
`data-bloc-entete` sur le titre du bloc et ses commandes (« Masquer »,
« + Ajouter », filtres) : il est masqué dans le widget. Marquer
`data-bloc-contenu` sur une partie que l'utilisateur peut replier dans la
page : elle reste affichée dans le widget.

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

### Source des valeurs (à écrire pour chaque bloc)

Un widget ne charge plus la page s'il existe une **source** pour son bloc dans
`static/mysifa_blocs_sources.js` : il appelle directement l'API que la page
utilise déjà et en extrait les valeurs. C'est 1 petite requête au lieu
d'environ 400 Ko et 50 requêtes. Sans source, le widget retombe sur le
chargement de la page hors écran.

Règle d'or : la source **reprend** le calcul et la mise en forme de la page
(même API, mêmes champs, même `fN` / `fMin`). Modifier ce calcul dans la page
impose de le reporter dans la source — sinon le widget et la page affichent
deux chiffres différents. Les regroupements calculés côté page (synthèses par
opérateur…) restent sans source plutôt que d'être réécrits à moitié.

Une page dont les filtres ne vivent pas dans l'URL les déclare à la capture :
`window.mysifaBlocsContexte = () => ({bloc_periode: 'last7', bloc_machine: [...]})`.
Ils rejoignent l'URL capturée et la source les relit (`ctx.params`). Une
période se déclare en raccourci (`last7`, `thisMonth`…) pour rester glissante.

### Rafraîchissement léger (blocs sans source)

Sans rien faire, le widget recharge la page chaque minute. Une page lourde
peut fournir un crochet qui recharge seulement ses données :

```js
window.mysifaBlocsRafraichir = function () {
  if (S.tab === 'dashboard') return loadDashboard();
  location.reload();
};
```

### Pilotage (superadmin)

Paramètres › Audit › **Blocs capturables** (`renderSettingsBlocs` dans
`settings_page.py`, visibilité `blocs` = superadmin réel) liste les blocs du
registre, le nombre de widgets créés sur chacun, l'étiquette « Nouveau », et
un interrupteur de capture (`blocs_reglages`). Couper un bloc masque ses
widgets sans les supprimer. On n'y crée ni ne renomme aucun bloc.

Les anciens tableaux de bord flottants (router `dashboards.py`, onglet profil
« Mes dashboards ») ont été retirés le 04/10/2026. Leurs tables `dashboards`
et `user_dashboards` restent en base jusqu'à la migration de suppression du
lot suivant.

Guide in-app : `accueil-widgets`, défini dans `mysifa_accueil.js`
(moteur partagé `mysifa_guides.js`), bouton « ? » dans l'en-tête de la
colonne.

### Pièges

- Une page en mode embarqué (`window.MySifaBlocs.embarque`) ne doit pas ouvrir
  de modale, de visite guidée ni d'annonce : elles seraient masquées mais
  pourraient marquer « vu » côté serveur.
- Versions : `main.py` injecte `mysifa_blocs.js?v=APP_VERSION`, qui charge
  `mysifa_accueil.js` avec la même version. Aucun compteur manuel à tenir.
- Le bouton de capture est un bouton « extra » du dock
  (`.mysifa-dock-fab.mysifa-dock-extra`, rangé par `mysifa_dock.js`). Sur une
  page sans dock, il prend le même aspect et se place seul.
- Dans un widget, la page embarquée défile mais ne réagit pas aux clics : un
  clic demande à l'accueil d'ouvrir la page d'origine.
