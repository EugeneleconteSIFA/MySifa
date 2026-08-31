# Rapport hebdomadaire — état des lieux et propositions

Audit du 28/08/2026. Aucune ligne de code modifiée à ce stade.
Périmètre lu : `app/services/weekly_report.py` (1904 l.), `app/routers/reports.py`,
`app/web/reports_page.py`, `app/services/arret_seuils.py`, `app/services/produit_memoire.py`,
`app/core/database.py` (migration v166), `config.py`.

---

## 0. Points d'environnement à trancher avant toute écriture

- **La branche `feature/seuils-arret` n'existe pas.** Le dépôt est sur
  `feature/portail-sous-menus`, avec un working tree qui porte déjà une trentaine
  de fichiers modifiés non commités (règles `.claude/`, CLAUDE.md, roadmaps).
  Le travail « seuils d'arrêt » est bien présent dans l'arbre de travail
  (`app/services/arret_seuils.py`, `tests/test_arret_seuils.py`,
  migration `2026_08_27_arret_seuils.py`) mais pas sur une branche à ce nom.
- **`data/production.db` fait 0 octet** : pas de base locale exploitable.
  Combiné au `.venv` macOS, ni le boot ni un test sur données réelles ne sont
  possibles depuis ce poste. Toute vérification se fera en logique isolée
  (sqlite en mémoire, stubs `_color` / `_esc` / `_section_title`) —
  **le boot reste à faire sur v1.**

---

## 1. Ce que fait le rapport aujourd'hui

Chaîne complète, sans surprise :

`collect_week_data(year, week)` ouvre une seule connexion, calcule les KPI de la
semaine, ceux de S-1, la moyenne S-2..S-5, puis remplit un dict à 13 clés
(`summary`, `prod_by_machine`, `arrets_expliques`, `dossiers_fab_detail`,
`top_dossiers`, `flop_dossiers`, `sanity_global`, `sanity_by_operateur`,
`stock_freshness`, `stock_from_prod`, `repiquage`, `expes`, `alerts`).
`render_report_html(data, role, email)` sélectionne les sections via
`ROLE_SECTIONS` et les assemble par un dispatch en fin de fichier.

Le double mode de rendu (`_color(name, email)` → hex ou `var(--x)`) tient bien :
aucune couleur en dur hors `EMAIL_COLORS`. La contrainte design-system est
respectée.

`sections_pour_role()` est la source unique du sommaire, et l'endpoint
`/sections` la sert à la page. Bonne décision : la page ne peut plus mentir sur
son contenu — sauf sur un point, traité en §2.1.

---

## 2. Défauts confirmés

### 2.1 — `administration_ventes` et `administration_technique` ne reçoivent RIEN

**C'est plus grave que « ils reçoivent la vue direction ».**

La migration v166 (`app/core/database.py:6246`) exécute :

```sql
UPDATE users SET role='administration_ventes' WHERE role='administration'
```

Donc plus aucun utilisateur ne porte le rôle `administration`, seul rôle
administratif présent dans `ROLE_SECTIONS`. Or `_target_recipients()`
(`app/routers/reports.py`) filtre :

```python
if role not in ROLE_SECTIONS:
    continue
```

**Conséquence : tout le service administration est exclu de l'envoi.**
Pas de vue dégradée — pas d'email du tout. L'entrée `ROLE_ADMINISTRATION` de
`ROLE_SECTIONS` est du code mort qui donne l'illusion de la couverture.

Et les trois écrans se contredisent :

| Chemin | Comportement pour `administration_ventes` |
|---|---|
| `GET /preview?role=administration_ventes` | **HTTP 400** « Rôle inconnu » |
| `GET /sections?role=administration_ventes` | 200, `connu: false`, sections direction |
| Pastille « Contenu » de la page | affiche « ce rôle reçoit la vue direction » |
| `POST /send` | l'utilisateur est **ignoré** |

Le sélecteur de rôle de `reports_page.py` propose les 10 rôles en dur, dont
`administration` (qui n'existe plus en base) et les deux qui plantent l'aperçu.

### 2.2 — Aucun planificateur

Confirmé par recherche exhaustive : ni `APScheduler`, ni `fastapi_utils.repeat_every`,
ni `BackgroundScheduler`, ni thread lancé dans le `lifespan` de `main.py`, ni
crontab versionné. Le pied de page de l'email annonce pourtant
« Rapport automatique du mercredi matin » — c'est faux.

Le rapport ne part que si quelqu'un clique sur « Envoyer maintenant », et le
bouton n'est visible que pour le superadmin (`_SEND_ROLES = {ROLE_SUPERADMIN}`).

**Deux risques structurels à traiter avant d'automatiser quoi que ce soit :**

1. **Il n'existe aucun garde-fou anti-double-envoi.** Rien en base ne mémorise
   qu'une semaine a été envoyée. Deux clics = deux emails à tout le monde.
   Le seul témoin est le fichier d'archive `data/weekly_reports/YYYY-WW-role.html`,
   qui n'est ni consulté ni verrouillé avant envoi.
2. **v1 et v2 partagent le même code.** Un planificateur dans le `lifespan`
   s'exécuterait aussi sur `mysifa-v1` (port 8002), qui a sa propre base mais
   potentiellement les mêmes adresses email. Un envoi de staging à tout le
   personnel est un incident réel, pas théorique.

### 2.3 — L'annonce `scope="weekly-report"` est invisible

Confirmé. `_publish_announcement()` insère avec `scope="weekly-report"`,
`active=1`. Côté lecture, `/api/updates/pending` accepte un paramètre `scope`
et filtre `WHERE a.scope=? OR a.scope='global'`. Les seuls appelants du front :

| Fichier | Scope demandé |
|---|---|
| `app/web/html.py:2401` | `global` |
| `app/web/fabrication_page.py:8029` | `fabrication` |
| `app/web/planning_page.py:5735` | `planning` |
| `app/web/messages_page.py:765` | `messages` |

`weekly-report` n'est demandé nulle part. L'annonce n'est donc jamais affichée,
jamais acquittée, jamais désactivée : elle s'empile en base à chaque envoi et
n'apparaît que dans la liste des annonces des Paramètres.

### 2.4 — La mémoire produit est ignorée alors que la donnée existe

Trois gisements alimentés à chaque clôture de dossier et affichés nulle part
dans le rapport :

| Source | Contenu | Alimentation |
|---|---|---|
| `dossier_info_prod.texte` | l'info prod obligatoire à la clôture (« R.A.S. » si rien) | 1 ligne par dossier, `PRIMARY KEY (no_dossier)` |
| `produit_series.commentaires` | JSON : liste `{saisie_id, date, operateur, operation, texte, origine}` — commentaires de saisie **et** motifs d'annulation | figé au snapshot de série |
| `produit_series.nb_nc` | nombre de NC rattachées au dossier | `COUNT(*)` sur `nc_dossiers` |

C'est la matière la plus qualitative du système : du texte écrit par des
opérateurs, sur un dossier identifié. Le rapport hebdo est le seul endroit où
elle pourrait remonter à la direction.

### 2.5 — Le sanity score par opérateur

`_render_sanity_operateurs()` produit une grille de chips
`nom · heures · mention`, triée par heures d'activité décroissantes. Le score
numérique est déjà masqué au profit d'une mention — quelqu'un a vu le problème
et l'a atténué.

**L'atténuation ne suffit pas.** Le sanity score mesure la complétude et la
cohérence de la saisie : trous, chevauchements, codes manquants. C'est un
indicateur de *moyens* — ergonomie de Saisieprod, formation, charge, qualité du
réseau à l'atelier. Le présenter nominativement, trié, dans un email adressé à
la direction, à l'administration et à la fabrication, le transforme en classement
de personnes. Le premier usage qui en sera fait ne sera pas « où faut-il aider ».

Et c'est un doublon : `sanity_global` porte déjà l'information utile, et le
problème de vocabulaire remonté par les opérateurs (« Début de production » /
« Production » / « Fin de production ») est une cause connue et documentée de
trous de saisie. Un opérateur mal noté par cette section l'est pour un défaut
d'interface.

**Recommandation : retirer `sanity_by_operateur` des trois vues.** Si le besoin
sous-jacent — « où la saisie décroche-t-elle ? » — doit être servi, il l'est
mieux par un agrégat non nominatif : par machine et par créneau horaire.

### 2.6 — Sections sans garde à vide

Cinq renderers sur onze construisent leur carte sans vérifier qu'il y a
quelque chose à dire. Une semaine creuse (fermeture d'août, semaine à 2 jours)
produit des cartes de zéros :

| Renderer | Comportement à vide |
|---|---|
| `_render_sanity_global` | affiche « 0/100 » et une pastille vide |
| `_render_stock_freshness` | 4 KPI à 0 |
| `_render_stock_from_prod` | affiche le message de succès (« aucun dossier sans stock ») alors qu'il n'y a eu aucun dossier |
| `_render_repiquage` | 4 KPI à 0, opérateurs « — » |
| `_render_expes` | 3 KPI à 0 |

`_render_stock_from_prod` est le cas le plus trompeur : à vide il affirme que
tout va bien.

Les six autres (`prod_by_machine`, `arrets_expliques`, `dossiers_fab_detail`,
`dossiers_table`, `sanity_operateurs`, `alerts`) retournent bien `""`.

### 2.7 — Deux scories mineures

- `collect_week_data` appelle `_franchissements(conn, wstart, wend + "T23:59:59")`.
  Or `_week_str_bounds` renvoie déjà `wend` suffixé : la borne devient
  `2026-08-23T23:59:59T23:59:59`. Sans conséquence (en comparaison lexicographique
  `'T' > '9'`, la borne reste dans le bon dimanche), mais c'est faux et ça se
  cassera au premier changement de format de date. Un caractère à retirer.
- `loadDernierEnvoi()` trie l'archive par `(year, week)` décroissant, donc affiche
  la **semaine la plus récente rapportée**, pas le **dernier envoi effectué**.
  Un rattrapage d'une semaine ancienne n'apparaît jamais comme le dernier envoi.
- Hors périmètre mais relevé : `reports_page.py:455` fait
  `chip.innerHTML = \`...${u.nom}...\`` sans échappement.

---

## 3. Propositions, classées par valeur

### Rang 1 — Verrou d'envoi + journal des envois
*Prérequis de tout le reste. Corrige 2.2 (garde-fou), 2.7 (dernier envoi).*

Migration fichier créant `weekly_report_envois` :
`(year, week, sent_at, declenche_par, mode, count_sent, count_failed)` avec
`UNIQUE(year, week)`. `POST /send` réserve la semaine (`INSERT` en amont, refus
si déjà prise) **avant** la boucle d'envoi, puis complète la ligne.
Un paramètre `force=true` explicite autorise le renvoi, tracé comme tel.

Effet immédiat : deux clics ne peuvent plus produire deux vagues d'emails, et la
page affiche enfin une vraie date d'envoi. Rien n'est automatisé.

**Testable en isolation** (sqlite en mémoire) → `tests/test_weekly_envois.py`.

### Rang 2 — Couverture des rôles administration
*Corrige 2.1. Petit coût, corrige un service entier privé de rapport.*

Trois arbitrages à trancher (§4, questions 1 et 2) puis :
`ROLE_SECTIONS` reçoit `administration_ventes` et `administration_technique`,
le sélecteur de la page est généré depuis `ROLES_*` de `config.py` plutôt
qu'écrit en dur, et `/preview` cesse de renvoyer 400 sur un rôle que
`/sections` accepte (fallback direction annoncé, cohérent avec la pastille).

### Rang 3 — Section « Mémoire produit »
*Répond à 2.4. C'est le seul poste qui ajoute de la matière plutôt que de
réparer.*

Une section, trois blocs, chacun s'effaçant s'il est vide :

1. **Infos prod de la semaine** — `dossier_info_prod` des dossiers clôturés,
   « R.A.S. » exclus. Une ligne = dossier, référence, auteur, texte.
2. **Ce que les opérateurs ont écrit** — commentaires de saisie et motifs
   d'annulation extraits du JSON `produit_series.commentaires`, plafonnés
   (10 ? 15 ?), origine affichée (`commentaire` / `annulation`).
3. **Non-conformités** — `SUM(nb_nc)` de la semaine, et le détail par référence
   au-delà de 0.

Le comptage et le tri sont de la logique de calcul → test dédié sur base en
mémoire, sur le modèle de `test_arret_seuils.py`.

Vues concernées : direction / administration / superadmin, et fabrication pour
les blocs 2 et 3.

### Rang 4 — Retrait du sanity par opérateur
*Répond à 2.5. Coût quasi nul, décision produit.*

Retrait de `sanity_by_operateur` des trois `ROLE_SECTIONS` qui le portent.
Le collecteur et le renderer restent en place — même traitement que
`top_dossiers` / `flop_dossiers`, déjà retirés pour un motif voisin.

### Rang 5 — Gardes à vide
*Répond à 2.6. Hygiène, exigée par la consigne « une section vide ne doit pas
afficher une carte vide ».*

Cinq gardes, dont une nuance pour `stock_from_prod` : à zéro dossier terminé,
la section disparaît au lieu d'annoncer un succès.

### Rang 6 — Destination de l'annonce hebdomadaire
*Répond à 2.3. Petit, mais à trancher avant d'automatiser : un envoi
automatique sans annonce visible, c'est un rapport que personne ne sait lu.*

Trois options, à arbitrer (§4, question 4) :

| Option | Effet | Coût |
|---|---|---|
| **a.** Publier en `scope="global"` | reprend le bandeau du portail déjà en place, acquittement inclus | 1 ligne |
| **b.** Ajouter `?scope=weekly-report` au fetch du portail | conserve un scope propre, filtrable | 2 fichiers |
| **c.** Ne plus publier d'annonce | l'email suffit, la page reste le point d'entrée | 1 suppression |

Quelle que soit l'option, désactiver l'annonce de la semaine précédente à la
publication de la nouvelle (`UPDATE ... SET active=0 WHERE scope='weekly-report'`)
— sinon l'empilement continue.

### Rang 7 — Automatisation de l'envoi
*Le défaut principal, volontairement placé en dernier : il n'est raisonnable
qu'une fois le rang 1 en place, et il demande une validation explicite.*

**Ne sera pas mis en œuvre sans accord écrit.** Trois voies :

| Voie | Mécanique | Avantages | Risques |
|---|---|---|---|
| **A. Cron VPS → endpoint à clé API** | même schéma que la synchro RVGI (clé, portée `reports:send`) | rien dans le processus applicatif ; v1 n'envoie jamais ; se coupe sans redéploiement | crontab non versionné, à documenter |
| **B. Thread dans le `lifespan`** | boucle horaire, déclenche si mercredi 07:00 et semaine non réservée | tout dans le dépôt | **s'exécute aussi sur v1** ; exige un garde `WEEKLY_REPORT_AUTO` |
| **C. Semi-auto** | mercredi 07:00, le rapport est archivé et une notification part au superadmin, qui confirme l'envoi | aucun email de masse non supervisé | reste un geste humain |

Recommandation : **A**, avec `WEEKLY_REPORT_AUTO=0` par défaut dans `config.py`
et à `1` uniquement dans le `.env` de prod. **C** si le sujet doit rester sous
contrôle humain une saison de plus.

---

## 4. Questions ouvertes

1. `administration_ventes` et `administration_technique` : une vue commune
   identique à direction, ou deux vues distinctes ? (ventes → expéditions,
   stock PF, dossiers clients ; technique → fabrication, arrêts, fiches/OF).
2. Faut-il conserver l'entrée `ROLE_ADMINISTRATION` dans `ROLE_SECTIONS` comme
   filet pour un compte non migré, ou la supprimer ?
3. Section mémoire produit : plafonner à combien de commentaires par semaine ?
   Faut-il exclure les motifs d'annulation, déjà visibles au planning ?
4. Annonce hebdomadaire : option a, b ou c du rang 6 ?
5. Automatisation : voie A, B ou C — et le mercredi 07:00 du pied de page
   est-il la bonne heure ?

---

## 5. Ajout du 28/08/2026 — module « Retour de prod » (`/rapports-prod`)

Livré hors de la liste d'arbitrage ci-dessus, sur demande directe : rendre
quelque chose aux opérateurs, et centraliser les comptes-rendus de dossier.

**Fichiers**

| Fichier | Rôle |
|---|---|
| `app/services/rapport_dossier.py` | Service pur (connexion sqlite seule, aucun import applicatif) : assemble le compte-rendu d'un dossier et l'agrège par machine et par semaine |
| `app/routers/rapports_prod.py` | 4 endpoints : `/semaine`, `/comptes-rendus`, `/dossier/{no}`, `/retour-atelier` |
| `app/web/rapports_prod_page.py` | Page `/rapports-prod`, deux onglets, feuille imprimable A4 |
| `tests/test_rapport_dossier.py` | 13 cas, base sqlite en mémoire |

Aucune migration : tout est lu dans les tables existantes.
Entrées : tuile portail (rôles production) et palette de commandes.

**Deux décisions de conception à connaître**

1. **Le retour est par machine, jamais par personne.** Même raisonnement qu'au
   §2.5 : la complétude d'une saisie mesure l'ergonomie et la charge autant que
   le conducteur. La feuille crédite l'équipe (« Aux commandes cette semaine »)
   sans jamais rattacher un chiffre à un nom, et les points de vigilance sont
   comptés, pas attribués. Un cas de test verrouille cette propriété.
2. **Le repère est la référence, pas l'atelier.** « Cette référence tourne
   d'habitude à 15 000 m/h sur 3 productions » se discute à la machine ; une
   moyenne d'atelier ne se discute pas.

**Piège de définition rencontré, et corrigé**

`produit_series.vitesse_m_min` est calculé par `app/services/dossier_stats.py`
comme `métrage / (production + arrêt)`. Or `weekly_report.py` appelle
« vitesse » `métrage / production`. Ce sont deux grandeurs différentes sous le
même mot, et comparer l'une à l'autre — ce que faisait la première version de
la feuille — surestimait systématiquement la semaine en cours : sur le jeu
d'essai, +66 % au lieu de −42 %.

Le module expose donc deux valeurs nommées séparément :

- `vitesse_m_h` — métrage / production seule, alignée sur `weekly_report` ;
- `cadence_m_h` — métrage / (production + arrêt), **seule** valeur comparée au
  repère historique, calculée des deux côtés de la même façon.

`tests/test_rapport_dossier.py::test_cadence_comparable_au_repere` verrouille
ce point précis.

**Trois constats sur l'existant, à arbitrer**

1. `weekly_report._dossiers_fab_detail` intitule « calage » le seul code `02`,
   alors que le référentiel compte 9 codes de catégorie `calage` (`10`, `11`,
   `12`, `58` changement bobines, `59`, `60`, `74`, `75`). Un changement de
   bobine ou de cliché n'est donc pas compté dans le calage du rapport hebdo.
   Le nouveau module nomme sa ligne « calage et changements » et couvre toute
   la catégorie — le nom diffère parce que la mesure diffère.
2. Deux définitions de « vitesse » coexistent dans le dépôt (voir ci-dessus).
   Tant qu'elles coexistent, tout écran qui les rapproche doit le dire.
3. `weekly_report` ne plafonne pas l'écart entre deux saisies : une journée
   terminée sans code `89` compte jusqu'à la première saisie du lendemain. Le
   nouveau module conserve ce calcul pour ne pas contredire le rapport hebdo,
   mais isole ces écarts (`minutes_douteuses`) et les remonte comme point de
   vigilance sur la feuille atelier, là où c'est actionnable.

**Reste à faire sur v1** : le boot. Le `.venv` du dépôt est un venv macOS et
`data/production.db` fait 0 octet — ni FastAPI ni données réelles ici. Le
service, ses calculs et le JS sont vérifiés (`compileall`, `node --check`,
13 cas de test), le rendu réel des deux onglets ne l'est pas.

### 5 bis. Deuxième passe — période jour et recherche libre

Retour d'usage : le module était invisible depuis l'écran réellement utilisé
(MyProd → Production → Rapport hebdo), la maille semaine ne couvrait pas le
point de production du matin, et la liste ne donnait accès qu'aux dossiers
clôturés dans la période.

- **Sélecteur de période** `jour` / `semaine`, avec raccourcis Hier /
  Aujourd'hui / Semaine passée. **Le jour « hier » est le défaut** : c'est la
  vue du point de production du matin. La maille semaine reste à un clic pour
  la feuille affichée à la machine.
- **Recherche libre** (`/api/rapports-prod/recherche`) sur numéro de dossier,
  client ou désignation. Elle atteint **tout dossier portant des saisies**,
  sans condition de date ni de clôture — donc aussi un dossier en cours ou clos
  il y a trois mois, ce qui est le cas le plus utile quand on reprend une
  référence. La liste de période reste, elle, limitée aux dossiers clôturés :
  les deux usages sont distincts et l'écran le dit.
- **Lien direct** : `/rapports-prod?dossier=D-501` ouvre le compte-rendu.
- **Accès depuis MyProd** : bouton « Comptes-rendus par dossier et retour
  atelier → » dans la barre de l'onglet Rapport hebdo. Le rapport hebdo agrège,
  le compte-rendu détaille : les deux se lisent ensemble.

Un dossier non clôturé ne déclenche pas le point de vigilance « info prod
absente » — la note n'est due qu'à la clôture. Cas de test dédié.

`tests/test_rapport_dossier.py` couvre maintenant 14 cas.

---

## 6. Troisième passe — le rapport hebdo est remplacé

Décision d'Eugène, 28/08/2026 : le retour de production devient le seul objet.
Le rapport hebdomadaire disparaît entièrement — onglet, page, archive et envoi
email compris. La liste d'arbitrage des §1 à §4 devient donc caduque sur ses
rangs 1 à 6 : ils portaient sur un module qui n'existe plus.

### Ce qui a été supprimé

| Fichier | Contenu |
|---|---|
| `app/services/weekly_report.py` | 1904 lignes — collecte, `ROLE_SECTIONS`, 11 renderers |
| `app/routers/reports.py` | `/preview`, `/sections`, `/list`, `/send` |
| `app/web/reports_page.py` | page `/reports/weekly` |

Plus le désenregistrement dans `main.py`, l'onglet « Rapport hebdo » de MyProd
(dans les deux copies : `static/mysifa_prod_core.js`, servi, et `app/web/html.py`,
monolithe de secours), et l'entrée `reports_page.py` du snapshot
`tests/theme_resolu.json`.

Les archives déjà écrites dans `data/weekly_reports/` sont laissées en place :
c'est de l'historique, plus personne n'écrit dedans.

**Conséquence assumée, à ne pas perdre de vue : plus aucun email de production
ne part.** Direction, administration, fabrication, logistique, comptabilité,
expédition et commercial recevaient un rapport hebdomadaire ; ils ne reçoivent
plus rien. Rebâtir un envoi sur le nouveau module est le prochain chantier
naturel — et il devra reprendre le garde-fou anti-double-envoi du rang 1, qui
n'a jamais été implémenté.

### Ce qui remplace

L'onglet MyProd → Production s'appelle désormais **« Retour de prod »** et
consomme `/api/rapports-prod`. Il n'est plus réservé au superadmin : il s'ouvre
aux services de production, l'API filtrant sur `ROLES_PROD`.

Le rendu ne vit ni dans la page ni dans l'onglet, mais dans
`static/mysifa_retour_prod.js` + `static/mysifa_retour_prod.css`, chargés par
les deux. C'était la seule façon de tenir la règle « deux écrans ne doivent
jamais donner deux chiffres pour le même dossier » : tant que le rendu est
écrit deux fois, il finit par diverger. La page `/rapports-prod` est passée de
885 à 484 lignes en perdant sa copie.

`brancher()` accepte une racine DOM, ce qui permet à MyProd de câbler les
éditions **avant** insertion — son `render()` remplace l'arbre à chaque passe,
un binding posé sur `document` ne survivrait pas.

### Édition directe

Deux écritures, sans migration, en réutilisant ce qui existait :

| Ce qu'on corrige | Endpoint | Service réutilisé |
|---|---|---|
| Info prod d'un dossier | `POST /api/rapports-prod/dossier/{no}/info-prod` | `produit_memoire.enregistrer_info_prod` |
| Explication d'un seuil d'arrêt | `POST /api/rapports-prod/seuil/{saisie_id}/explication` | `arret_seuils.enregistrer_explication` |

Ce sont exactement les deux manques que l'écran signale (« info prod absente »,
« sans explication — à poser au point de production »). Le compte-rendu est
l'endroit où le trou se voit : c'est donc là qu'il doit se combler, sans
renvoyer vers la Traçabilité. `enregistrer_explication` ne committait pas —
l'endpoint s'en charge.

### Deux pièges rencontrés

1. **Un mot parasite invisible à `node --check`.** Une concaténation contenant
   un identifiant égaré passait la vérification syntaxique : l'insertion
   automatique de point-virgule coupait le `return` en deux, et la fonction ne
   rendait plus que sa balise ouvrante. Seul un appel réel le montre — d'où
   `tests/test_retour_prod_rendu.js`, qui exécute le module (rendu à vide,
   lignes complètes, échappement, formats).
2. **`api()` de MyProd lève sur toute réponse non-OK.** Un dossier sans saisie
   (404) aurait cassé l'onglet entier. Chaque appel est isolé, le message est
   gardé en état et affiché à sa place.

### Vérification

`compileall` sur `app/` et `main.py` · `node --check` sur les 5 blocs JS
(module partagé, `mysifa_prod_core.js`, `mysifa_cmdk.js`, et les scripts
extraits de `rapports_prod_page.py` et `html.py`) · 9 suites Python + la suite
JS au vert. **Le boot reste à faire sur v1.**

---

## 7. Quatrième passe — emboîtement dans MyProd, unités, lisibilité

### L'onglet devient le seul foyer

La page autonome `/rapports-prod` est supprimée, ainsi que la tuile portail.
Le module vit désormais dans **MyProd › Production › Retour de prod**
(`/prod#retour`), et nulle part ailleurs. L'entrée de la palette de commandes
pointe l'onglet.

### Ce qui n'était pas emboîté

L'onglet portait ses propres sélecteurs de période et de machine, alors que la
page Production a déjà une barre de filtres (période avec ses raccourcis
Aujourd'hui / Hier / 7 jours / 30 jours / mois, machines, opérateurs, dossier).
Deux jeux de commandes pour la même chose : l'utilisateur ne sait plus lequel
fait foi.

L'onglet lit maintenant `S.fv.date_from` / `S.fv.date_to` et `S.fv.machines`.
`applyF()` le recharge comme les autres onglets. Il ne garde que ce qui lui est
propre : de quelle machine est la feuille, feuille ou comptes-rendus, imprimer.

L'API a gagné un mode `plage` (deux dates libres) à côté de `jour` et
`semaine` — sans lui, l'onglet aurait dû retraduire une plage quelconque en
journée ou en semaine ISO, c'est-à-dire mentir sur ce qu'il affiche.

Si le filtre machines ne recoupe aucune machine de la période (nom canonique
différent de celui des saisies), l'onglet rend toutes celles de la période
plutôt qu'un écran vide sans explication.

### L'unité était fausse

`vitesse_m_h` et `cadence_m_h` affichaient des mètres par **heure** : « 1 789
m/h ». Or une machine se règle en **m/min**, `produit_series.vitesse_m_min` est
en m/min, l'ancien rapport hebdo affichait « 57 m/min », et
`app/web/html.py:7269` calcule déjà `métrage / (temps_prod + temps_arrêt)` en
m/min — c'est-à-dire exactement la cadence, dans la bonne unité.

Le service ne convertit plus rien : `vitesse_m_min` et `cadence_m_min`, la
médiane de référence lue telle quelle dans `produit_series`. Un `×60` retiré,
c'est une classe d'erreur en moins. 1 789 m/h se lit maintenant 29,8 m/min.

### Texte au minimum, texte lisible

Titres et libellés resserrés (« Ce qui est sorti de la machine » → « Production »,
« Ce qui a coûté le plus de temps » → « Temps perdu », « À reprendre au point de
production » → « À reprendre »), paragraphe explicatif de la cadence remplacé
par une infobulle sur le titre, points de vigilance sans le mot « dossier »
répété à chaque ligne.

Une redondance visible sur la capture est corrigée : la colonne Code affichait
`66` et la colonne Opération `66 - Attente matière`. `sansCode()` retire le
préfixe quand le code est déjà à côté.

Rien ne descend plus sous 12 px — la feuille se lit debout devant une machine.
Valeurs de KPI à 32 px, corps de texte à 15 px, méta à 12,5 px.

### Animation au survol

Reprise des tokens de `static/motion.css` (`--mo-fast`, `--ease-out`) plutôt
qu'inventer des durées : KPI qui se soulève, ligne de tableau qui prend un
liseré d'accent, citation dont la barre s'épaissit, compteur de vigilance qui
grossit légèrement, boutons et champs. Tout est neutralisé sous
`prefers-reduced-motion: reduce` et `body.reduce-anim`, comme le reste.

L'impression depuis MyProd masque la page par `visibility` et laisse sortir la
seule `.rp-feuille` — le flux est conservé, donc la feuille ne se reconstruit
pas.

`tests/test_retour_prod_rendu.js` couvre désormais l'unité (aucun `m/h` dans la
sortie), le retrait du code dupliqué et le formatage m/min.

---

## 8. Cinquième passe — le métrage manquant, et le suivi des remontées

### Pourquoi un dossier affichait 0 m

Cohésio 2 du 27/08 : 4 h 17 de production, 0 m. Ce n'était pas un cas limite,
c'était une reconstruction fausse.

`app/services/dossier_stats.py::_enrich_metrage` — qui alimente
`produit_series.metrage_m` et la liste des saisies que les opérateurs relisent
chaque jour — pose trois règles, déjà corrigées une fois pour ce même genre de
bug :

1. Les compteurs vivent dans `metrage_total_debut` / `metrage_total_fin` ;
   `metrage_prevu` / `metrage_reel` ne sont que **le repli** des lignes
   antérieures.
2. Le compteur de début appartient au **dossier**, pas à l'opérateur : l'équipe
   qui clôture n'a pas forcément posé le code de début.
3. Sans compteur de début connu, **il n'y a pas de métrage** — on ne prend pas 0
   pour origine, sinon c'est le compteur machine entier qui sort.

Le module lisait uniquement l'ancien couple, sur les seules lignes de fin, avec
un `MAX − MIN` et un seuil à 1 000 000 pour écarter les compteurs bruts —
héritage de l'ancien rapport hebdomadaire. Un dossier dont le compteur est dans
les nouvelles colonnes sortait donc à 0, et `_saisies()` ne sélectionnait même
pas ces colonnes.

La règle canonique est désormais reproduite à l'identique, le seuil heuristique
a disparu, et huit cas la verrouillent : repli, priorité des nouvelles colonnes,
deux cycles, début posé par un autre conducteur, annulation bornant un cycle,
clôture orpheline.

**Effet de bord assumé :** la notion de « métrage prévu » est retirée. Elle
lisait `metrage_prevu`, c'est-à-dire un compteur de début — un objectif
reconstitué à partir d'une valeur qui n'en est pas un.

### Suivi des remontées

Migration `2026_08_28_retour_prod_suivi.py`, deux tables, aucune colonne ajoutée
ailleurs. Une remontée peut venir de quatre sources ; une **clé stable** les
réconcilie (`saisie:<id>`, `infoprod:<no>`, `seuil:<id>`, `note:<id>`), ce qui
permet un seul mécanisme de suivi.

Trois gestes sur chaque remontée : **valider** (c'est traité), **modifier** (le
texte part vers sa source d'origine), **commenter** (une note rattachée à la
clé). Plus un commentaire libre sur le dossier.

Deux décisions : valider n'efface pas — ce qui disparaît de l'écran n'est jamais
relu, donc la remontée reste affichée, marquée, et se dévalide. Et un motif
d'annulation se valide mais ne se corrige pas : c'est la trace d'un geste, pas
une remontée qu'on complète après coup.

### Le reste

Colonne **Client** dans la cadence · section « Temps perdu » renommée
**Arrêts**, colonne Code retirée (elle répétait le libellé) · **Toutes les
machines** dans le sélecteur de feuille · champs et boutons sortis du fond de
page (`.rp-seg`, `.rp-select`, `.rp-recherche` : le bloc prend le fond de page,
le champ garde celui des cartes).

`tests/test_rapport_dossier.py` : 14 cas dont le métrage canonique et le suivi.
`tests/test_retour_prod_rendu.js` : les trois gestes, la remontée traitée, le
motif d'annulation non corrigeable, la colonne client, la section Arrêts.

---

## 9. Sixième passe — « Hier », la frise, et la reprise des commentaires

### « Hier » désigne la dernière journée travaillée

Un lundi matin, le raccourci pointait un dimanche vide. Le navigateur sait quel
jour on est, pas où se trouve la dernière saisie : le calcul est donc passé au
serveur (`GET /api/production/dernier-jour-saisi`), qui renvoie le dernier jour
portant une saisie non annulée **jusqu'à la veille incluse** — la journée en
cours n'est jamais retenue.

La puce garde son libellé « Hier » quand la dernière journée travaillée *est* la
veille, et devient « Dernier jour » sinon, avec la date en infobulle. Une puce
marquée « Hier » qui charge un vendredi serait un mensonge gratuit.

Ça vaut pour toute la page Production, pas seulement le Retour de prod : c'est
la barre de filtres qui est corrigée.

### Frise de production

Quatre arbitrages retenus : dans la feuille **et** dans le compte-rendu ;
segments colorés par phase ; réel seul ; axe en heures ouvrées, nuits repliées.

L'axe ne montre que les journées travaillées, chacune large à proportion de sa
durée réelle — une demi-journée et une journée de douze heures ne doivent pas se
ressembler. Les journées sans saisie se replient en un trait.

**Les saisies restées ouvertes d'un jour à l'autre ne commandent pas l'axe.** Une
ligne oubliée un soir couvre la nuit entière et déplierait précisément ce qu'on
cherche à replier ; elle reste dessinée dans son slot, mais ne définit plus les
heures travaillées. Sans cette règle, une seule saisie oubliée faisait passer le
jeudi de 8 h à 18 h.

Un dossier commencé avant la période ou non terminé porte un bord ouvert de
chaque côté : le tronquer sans le dire ferait croire à une production plus
courte qu'elle ne fut.

**Les positions sont calculées côté serveur, en pourcentage.** Une géométrie
calculée dans le navigateur serait invisible aux tests, et c'est exactement le
genre de calcul qui dérape en silence. `intervalles()` est devenue la brique
commune au calcul des temps et au tracé : les calculer deux fois, c'est se
donner deux chronologies pour un même dossier.

Un clic sur un slot ouvre le compte-rendu de son dossier.

### Commentaires : citation, masquage

« Commenter » ajoutait une remontée de plus, qui noyait celle qu'elle commentait.
Une réponse se range désormais **sous** sa remontée, en citation ; seules les
notes libres restent des entrées à part entière.

Nouvel état **masqué**, distinct de validé (migration `retour_prod_masque`).
Toutes les remontées ne parlent pas de la qualité de production : « 10h »,
« 5h25 », un mot laissé à l'équipe suivante. Les valider serait mentir — elles
n'ont pas été traitées, il n'y avait rien à traiter. Elles quittent la liste
principale et restent derrière un bouton « Commentaires masqués (n) », en face
de « Vos écrits ». Rien n'est effacé : une remontée jugée hors sujet un jour
peut se révéler utile le lendemain.

La migration est séparée de `retour_prod_suivi` : une migration déjà passée en
production ne rejoue pas, et son NOM ne doit jamais changer.

`tests/test_rapport_dossier.py` : 20 cas. `tests/test_retour_prod_rendu.js` :
axe, débordements, phases, citations, masquage.
