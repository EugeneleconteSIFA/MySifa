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

**État en badge coloré** (état machine, appréciation d'un score) : la clé va
dans `tons=(…)` du registre (elle doit déjà être dans `textes`). La page pose
`data-bloc-ton-<cle>` et la source rend un troisième argument à `r()`
(`{etat: m.statut_ton}`), avec une valeur parmi `ok`, `warn`, `danger`,
`neutre` (`TONS_ETAT` de `config.py`). Le ton vient **toujours d'un champ de
l'API** (`statut_ton` de `/api/production/machine-status`, `ton` de
`/api/portail/atelier`, `sanity.ton`), calculé côté serveur par
`ton_statut_machine()` & co. Jamais déduit du libellé affiché. Un arrêt est
`danger`, pas `warn` : `--warn` est un bleu dans Ambre. Le test du registre
vérifie que page et source fournissent le ton déclaré.

**Appli du bloc** : chaque `appli` du registre a son entrée dans `APPLIS`
(libellé, icône, teinte `accent` / `c1`…`c4` du thème). L'indicateur en tire
son filet de couleur et sa pastille. Une appli nouvelle s'y ajoute avec son
icône dans `ICONES_APPLI` de `mysifa_accueil.js` ; le test échoue sinon.

**Unité** : l'indicateur la lit dans le libellé de la valeur, entre
parenthèses (`("metrage", "Métrage (m)")` → « 37 112 m »). Six caractères au
plus. Une valeur déjà mise en forme avec son unité (« 42 min », « 12 k€ »)
n'en reçoit pas une seconde.

**Taille de l'indicateur** (décision du 11/10/2026) : colonne `hauteur` de
`accueil_widgets`, `s` compact (une ligne : nom, valeur, tendance), `m`
standard, `l` grand. Elle se règle dans Personnaliser (trois boutons sous la
carte). Le grand format n'existe que pour un bloc qui déclare :

- `series=(("metrage", "+"), …)` : une série **qui s'additionne jour par jour**
  (métrage, minutes), jamais une moyenne ou une vitesse, ni un compte de
  dossiers (un dossier sur deux jours compterait deux fois). Le sens `+` / `-`
  dit si une hausse est bonne ; il colore la tendance. La source va dans
  `SERIES` de `mysifa_blocs_sources.js` et rend `{jours, quotidien,
  tendances}` : la période capturée comparée à la précédente de même durée
  (jour travaillé précédent pour « hier »), calculée sur la même série des
  deux côtés. Grand format = barres sur 30 jours, seuil d'alerte en pointillé
  quand la période est d'un jour ; standard = mini-courbe sur 14 jours.
- `liste=True` : la source va dans `LISTES` et rend `{lignes: [{libelle,
  detail, ratio}], total}`, avec les libellés et mises en forme de la page.
  Grand format = les 5 premières lignes, les plus urgentes d'abord.

Le serveur refuse `hauteur="l"` sur un bloc qui n'a ni l'un ni l'autre. Dans
la colonne de 220 px, le grand format s'affiche en standard. Le test du
registre vérifie que chaque `series=` / `liste=True` a sa source.

**Relevés quotidiens** (décision du 11/10/2026) : un bloc dont la valeur est
un état à l'instant n'a pas d'historique. `app/services/accueil_releves.py`
le photographie toutes les 30 minutes (boucle `_boucle_releves_accueil` de
`main.py`, **prod uniquement** — v1 reçoit les relevés par la copie nocturne)
dans `accueil_releves`, une ligne par (bloc, objet, filtres, jour). La
**valeur du jour** est celle du premier passage à partir de
`RELEVES_HEURE_FIGEE` (`config.py`, 18 h : fin de journée de travail, décision
du 13/10/2026) ; avant, elle suit l'état courant, après elle ne bouge plus. Le
**minimum** et le **maximum** de toute la journée sont gardés à côté
(`minimums`, `maximums`). `maj_le` = heure de la valeur retenue, `vu_le` =
dernier passage (c'est lui qui dit si la boucle tourne). Un serveur arrêté à
18 h fige la valeur au premier passage qui suit son redémarrage. Rien ne les
affiche encore ; ils serviront aux courbes des blocs sans série.

- Un relevé **appelle la fonction de la route** que la source interroge, sous
  `en_tant_que_systeme()` (`auth_service.py` : utilisateur superadmin
  interne, id 0, posé dans une variable de contexte, inatteignable depuis une
  requête HTTP), puis applique **le même décompte que la source JS**. Changer
  le décompte d'une source impose de le reporter dans son relevé.
- Les valeurs personnelles ne sont pas relevées (« mes tâches », messages non
  lus, NC non lues, agenda).
- **Tout bloc nouveau** va dans une seule de trois tables :
  `RELEVEURS` (relevé), `RECONSTITUABLES` (historique déjà en base, à
  recalculer plutôt qu'à relever : séries MyProd, synthèses, états de machine
  tirés des saisies horodatées) ou `NON_RELEVES` (personnel uniquement), avec
  sa raison. `tests/test_accueil_releves.py`
  échoue sinon, et exécute chaque relevé contre une base neuve.
- **Bloc sur un objet** (catégorie, machine, transporteur) : tous ses objets
  existants sont relevés, suivis par un indicateur ou non, via `OBJETS`
  (décision du 13/10/2026) — l'historique est là le jour où quelqu'un
  l'épingle. Les identifiants sont ceux du `data-bloc-objet` de la page.
- La valorisation du stock est **relevée** bien que reconstituable
  (`/api/stock/valorisation/trend`) : le recalcul ne rend que le total, sur
  90 jours au plus, aux prix connus après coup.
- **Aucune purge** (décision du 12/10/2026) : tout est conservé, y compris
  les relevés d'un bloc retiré. Ne pas ajouter de durée de conservation sans
  nouvelle décision.
- Contrôle en prod : `GET /api/accueil/blocs/admin/releves` (superadmin).
- Consultation : dans Paramètres › Widgets et tableaux de bord, la pastille
  « Relevé · N j » d'un bloc déplie ses relevés jour par jour (90 jours, une
  série par objet ou jeu de filtres suivi, avec le nom des indicateurs
  concernés) et les exporte en CSV.
  `GET /api/accueil/blocs/admin/releves/{nom}?jours=90` (superadmin, 400 j max).

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
`choix` / `multi` / `jour`, options et défaut, avec les libellés de la page). Il sert
au sous-titre de l'indicateur (« 7 derniers jours · Cohésio 2 ») et à la
section « Filtres » du questionnaire, à la capture comme dans « Modifier
l'indicateur » (le PATCH accepte alors `url_capture`). Un filtre ajouté à
`mysifaBlocsContexte` s'ajoute aussi là ; le test du registre vérifie que
chaque bloc décrit existe. Une date figée (valorisation MyStock « au 17/09 »)
est un filtre comme un autre : capturable, et modifiable ensuite.

### Rafraîchissement léger (blocs sans source)

Sans rien faire, le widget recharge la page chaque minute. Une page lourde
peut fournir un crochet qui recharge seulement ses données :

```js
window.mysifaBlocsRafraichir = function () {
  if (S.tab === 'dashboard') return loadDashboard();
  location.reload();
};
```

### Boutons flottants par application

Les boutons en bas à droite (messagerie, post-it, assistant IA, calculette,
capture, tâche rapide Option+T) ne s'incluent plus page par page :
`main.py` (`_boutons_flottants`, dans le middleware `inject_tache_quick`)
les injecte dans toute page connectée qui ne les a pas déjà, puis
`static/mysifa_boutons.js` les démarre si la page ne l'a pas fait. Une
nouvelle page n'a rien à faire, à condition que son adresse soit déclarée dans
`APPLIS` de `app/services/boutons_flottants.py`. Une adresse absente de cette
liste, comme une page publique, ne reçoit rien.

Le superadmin coupe un bouton appli par appli (même écran, section « Boutons
flottants par application », table `boutons_flottants_reglages`). Le réglage
part dans le `<head>` de la page : `window.__MYSIFA_BOUTONS__` et une règle
CSS qui masque le bouton. Un bouton sans icône (raccourci clavier) lit
`window.MySifaBoutons.actif(cle)`.

Nouveau bouton flottant : l'ajouter à `BOUTONS` avec le sélecteur de ses
éléments. S'il dépend du code d'une seule page, le déclarer `appli="…"` : il
ne se règle que là.

### Pilotage (superadmin)

Paramètres › Audit › **Widgets et tableaux de bord**, section « Blocs capturables » (`renderSettingsBlocsCapturables` dans
`settings_page.py`, visibilité `blocs` = superadmin réel) liste les blocs du
registre, le nombre de widgets créés sur chacun, l'étiquette « Nouveau », et
un interrupteur de capture (`blocs_reglages`). Couper un bloc masque ses
widgets sans les supprimer. On n'y crée ni ne renomme aucun bloc.

Depuis le 12/10/2026, la même section dit aussi, bloc par bloc, ce qu'il sait
faire (`GET /api/accueil/blocs/admin`) : grand format (graphique ou liste),
historique (série en base, relevé quotidien avec son nombre de jours, ou la
raison de `NON_RELEVES`), mode de lecture (API, ou page chargée hors écran —
déduit de la table `SOURCES` de `mysifa_blocs_sources.js`), répartition des
indicateurs par taille et alertes posées. Deux tuiles en tête : « Formats » et
« Relevés », qui passe en avertissement si la boucle n'a pas tourné depuis une
heure. Filtres : sans grand format, sans historique, page chargée — les listes
de travail du chantier. Les noms et teintes d'applis viennent d'`APPLIS` du
registre, plus d'une liste propre à la page.

Deuxième section, **Par utilisateur** (`renderSettingsUsages`,
`GET /api/accueil/blocs/admin/usages`) : qui a épinglé quels indicateurs,
avec valeurs et alertes. Dans la liste des blocs, le nombre d'indicateurs se
déplie sur les mêmes noms. Réservé au superadmin : les tableaux de bord
restent personnels, aucun autre écran ne montre ceux d'un collègue.

Les anciens tableaux de bord flottants (router `dashboards.py`, onglet profil
« Mes dashboards ») ont été retirés le 04/10/2026, leurs tables `dashboards`
et `user_dashboards` le 06/10/2026 (migration
`suppression_anciens_dashboards`). Ne pas les recréer.

Un indicateur existant se modifie depuis l'accueil (Personnaliser › curseurs) :
c'est le même questionnaire qu'à la capture, exposé par
`window.MySifaBlocs.questionnaire(o)` — ne pas en écrire un second.

**Taille et aperçu à la création** (décision du 14/10/2026) : le
questionnaire propose la taille (compact, standard, grand si le bloc a une
série ou une liste) et, à la capture (`o.apercu`), montre en tête du panneau
(accroché pendant le défilement, juste au-dessus des réglages — retour du
14/10 : centré sur la page, il paraissait perdu) l'indicateur tel qu'il
apparaîtra : même carte, rendue par
`MySifaAccueil.apercu()` de `mysifa_accueil.js` (chargé hors de l'accueil avec
`window.__mysifaAccueilApercuSeul`, sans colonne), valeurs lues sur la page,
série et liste par les sources. Ne pas écrire un second rendu de carte pour
l'aperçu. Le questionnaire est redessiné à chaque réglage : l'aperçu est un
élément durable, replacé dans `.cap-apercu-ici` après chaque dessin, jamais
recréé. Sa largeur est celle d'une carte dans la colonne de l'utilisateur,
bornée par le panneau (pleine largeur sur téléphone).

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
