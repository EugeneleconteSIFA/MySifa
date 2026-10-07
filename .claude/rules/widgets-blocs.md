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

**Appli ouverte par rôle** (ERP RVGI : `ROLES_ERP`, pas d'app_id dans le
contrôle d'accès) : `acces="erp"`, que `_ACCES_PAR_ROLE` de
`accueil_widgets.py` traduit en liste de rôles. Une autre appli dans ce cas
s'y ajoute, plutôt que de laisser `acces=None` (bloc proposé à tous).

**Page rendue en chaînes HTML** (ERP) : le nom s'écrit en clair,
`'<div class="tdb-tuiles" data-bloc="erp.adv.kpis"'+tdbValeurs({...})+'>'`.
Un nom construit par concaténation échappe au test du registre.

**Valeurs clés** — un attribut par valeur sur l'élément racine, recalculé à
chaque rendu : `'data-bloc-valeur-lignes': String(rows.length)`. Une liste ou
un tableau déclare au minimum `lignes`. Une carte d'état déclare son état en
texte lisible (`En production`), jamais le code technique. **Un bloc sans
valeur clé n'est pas capturable** (le registre le refuse) : pour un graphique
ou une frise, déclarer au moins un chiffre qui le résume.

**Valeur texte** (état, nom d'opérateur, référence de dossier) : la déclarer
dans `textes=(…)` de son entrée au registre. Elle s'affiche, mais n'accepte
pas d'alerte — une alerte compare un nombre à un seuil numérique, serveur et
questionnaire refusent tout le reste.

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

**Bloc cliquable sur un objet** (tuile de catégorie, carte machine qui ouvre
une page) : déclarer où mène le clic, `lien="/stock?tab=matieres&cat={objet}"`
dans le registre. L'indicateur ouvre alors cette page, pas celle de la
capture — y compris pour les indicateurs créés avant. La page cible doit
savoir s'ouvrir sur l'objet par son adresse (ex. `?cat=` de MyStock, lu au
chargement et tenu à jour par `stockSyncUrl`). Un bloc qui ne mène nulle part
de plus précis n'a pas de `lien`.

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

**Calcul qui n'existe que dans la page** (aucune API ne renvoie le chiffre) :
ne pas le réécrire dans la source, ni laisser le widget charger la page. Le
porter côté serveur dans un service, l'exposer par un endpoint que la source
appelle, et rejouer les fonctions JS de la page contre leur traduction Python
dans un test. Modèle : Maintenance — `app/services/maintenance_statuts.py`,
`GET /api/maintenance/statuts`, `tests/test_maintenance_statuts.py`.

Une page dont les filtres ne vivent pas dans l'URL les déclare à la capture :
`window.mysifaBlocsContexte = () => ({bloc_periode: 'last7', bloc_machine: [...]})`.
Ils rejoignent l'URL capturée et la source les relit (`ctx.params`). Une
période se déclare en raccourci (`last7`, `thisMonth`…) pour rester glissante.

**La page relit ses filtres capturés à l'ouverture.** Un clic sur l'indicateur
rouvre l'adresse capturée : la page lit ses `bloc_…` à son démarrage, les
applique, pose `window.__mysifaFiltresLus = true` et appelle
`MySifaBlocs.retirerFiltres()` (sinon `mysifa_blocs.js` s'en charge à son
chargement). Déclarer un filtre dans `mysifaBlocsContexte` sans le relire au
démarrage = un clic qui ne retrouve pas les chiffres de l'indicateur. Les
tris ne sont pas capturés : ils ne changent aucun chiffre.

**Les filtres se voient et se modifient.** `static/mysifa_blocs_filtres.js`
décrit, bloc par bloc, chaque filtre `bloc_…` (libellé, type `periode` /
`choix` / `multi`, options et défaut, avec les libellés de la page). Il sert
au sous-titre de l'indicateur (« 7 derniers jours · Cohésio 2 ») et à la
section « Filtres » du questionnaire, à la capture comme dans « Modifier
l'indicateur » (le PATCH accepte alors `url_capture`). Un filtre ajouté à
`mysifaBlocsContexte` s'ajoute aussi là ; le test du registre vérifie que
chaque bloc décrit existe.

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
« Mes dashboards ») ont été retirés le 04/10/2026, leurs tables `dashboards`
et `user_dashboards` le 06/10/2026 (migration
`suppression_anciens_dashboards`). Ne pas les recréer.

Un indicateur existant se modifie depuis l'accueil (Personnaliser › curseurs) :
c'est le même questionnaire qu'à la capture, exposé par
`window.MySifaBlocs.questionnaire(o)` — ne pas en écrire un second.

**Demande de tableau de bord** : quand le bloc voulu n'existe pas, le lien en
bas de la colonne (et le toast « aucun bloc capturable ») ouvre
`MySifaBlocs.demander()`. `POST /api/accueil/demandes` crée une tâche
« évolution » au nom du demandeur, rattachée au module (= application) qu'il
a choisi dans la liste TACHES_MODULES, assignée à tous les
superadmins actifs, via `creer_tache_pour()` de `app/routers/taches.py` — seul
point d'écriture d'une tâche hors du gestionnaire. 5 demandes par jour et par
personne.

Une demande faite depuis une appli joint l'**écran concerné** (prérempli,
modifiable) et son adresse. Le libellé vient de `window.mysifaEcran()` si la
page le définit (MyStock : onglet, catégorie de matières, matière ouverte),
sinon du titre de l'onglet du navigateur (« Matières premières — MyStock —
MySifa » → « MyStock › Matières premières »). Une page dont la sous-vue
n'est ni dans son titre ni dans son URL doit définir `mysifaEcran`. Le
bandeau du mode capture propose aussi « Faire une demande ».

Guide in-app : `accueil-widgets`, défini dans `mysifa_accueil.js`
(moteur partagé `mysifa_guides.js`), bouton « ? » dans l'en-tête de la
colonne. Seul guide ouvert à **tous les rôles** (`tous: true`, décision du
06/10/2026) : les autres guides restent réservés aux superadmins. Toute
évolution visible des tableaux de bord (capture, questionnaire, colonne)
impose de relire ses 6 étapes et leurs illustrations.

### Pièges

- Une page en mode embarqué (`window.MySifaBlocs.embarque`) ne doit pas ouvrir
  de modale, de visite guidée ni d'annonce : elles seraient masquées mais
  pourraient marquer « vu » côté serveur.
- La colonne vit hors de `#root` : le portail ne la reconstruit pas, donc ne
  l'efface pas non plus. Déconnexion ou session expirée affichent l'écran de
  connexion **sans recharger la page** — `mysifa_accueil.js` surveille la
  présence de `.portal-page`, masque la colonne dès qu'elle disparaît et la
  démonte (DOM, état, minuteur) si `/api/accueil/prefs` répond 401. Tout
  nouvel élément affichant des données hors de `#root` doit suivre la même
  règle (fuite constatée en prod le 06/10/2026 : chiffres de l'utilisateur
  précédent visibles sur l'écran de connexion).
- Versions : `main.py` injecte `mysifa_blocs.js?v=APP_VERSION`, qui charge
  `mysifa_accueil.js` avec la même version. Aucun compteur manuel à tenir.
- Le bouton de capture est un bouton « extra » du dock
  (`.mysifa-dock-fab.mysifa-dock-extra`, rangé par `mysifa_dock.js`). Sur une
  page sans dock, il prend le même aspect et se place seul.
- `?capture=<nom du bloc>` sur n'importe quelle page ouvre la capture dès que
  le bloc est affiché, puis le paramètre est retiré de l'adresse. C'est ce
  qu'utilisent les liens « Essayer sur… » de la colonne vide (le seul mode
  d'emploi visible hors superadmins : les guides in-app leur sont réservés).
- Dans un widget, la page embarquée défile mais ne réagit pas aux clics : un
  clic demande à l'accueil d'ouvrir la page d'origine.
