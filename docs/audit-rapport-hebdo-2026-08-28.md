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

---

## 10. Septième passe — « Hier » (la vraie cause) et les points de production

### « Hier » : un piège de fuseau

Le correctif précédent était bien déployé et ne pouvait pas marcher. Le serveur
calculait sa propre veille avec `date.today()` et la renvoyait pour comparaison ;
le VPS tourne en UTC, le poste est à Paris, et un lundi matin les deux ne
désignent pas le même jour. La condition « le filtre est-il encore sur la
veille ? » ne tombait donc jamais juste, et le filtre restait sur son dimanche
vide.

**La veille est maintenant calculée par le navigateur et envoyée au serveur**,
qui ne répond plus qu'à une seule question : où est la dernière saisie avant
cette date. Plus aucune comparaison entre deux horloges.

Leçon générale : dès qu'un écran compare une date client à une date serveur,
c'est le client qui doit fournir la sienne — lui seul sait quel jour il est pour
l'utilisateur.

### Points de production (`/reunions`)

Migration `reunions_prod` : trois tables (`reunions`, `reunion_actions`,
`reunion_participants`). Une action et un participant sont des lignes, pas du
texte dans un champ — les compter, les cocher, les filtrer devient possible sans
rien reparser.

Le compte-rendu garde la plage de dates, le titre, les notes, les actions et les
participants. **Il ne garde pas les chiffres** : ils se recalculent à chaque
lecture depuis `rapport_dossier`. Choix assumé — plus léger, mais une réunion
rouverte dans trois mois montrera l'atelier tel qu'il apparaît ce jour-là, pas
tel qu'on le voyait pendant le point. Ce qui doit survivre intact, ce sont les
notes et les décisions, et celles-là sont bien figées.

Trois règles de comportement :

- **Une seule réunion ouverte par personne.** Rouvrir la page rend celle qui
  traîne plutôt que d'en empiler une seconde qui ferait perdre les notes de la
  première. Une réunion qu'on oublie de clore n'est pas une erreur, c'est une
  réunion qu'on reprend.
- **Clore ne verrouille pas.** On corrige toujours un compte-rendu après coup ;
  clore dit seulement que le point est passé, et se défait.
- **La liste s'ordonne sur la plage analysée**, pas sur l'heure de création :
  c'est la journée dont on a parlé qui situe une réunion.

L'écran de réunion met les chiffres à gauche et la prise de notes en colonne
fixe à droite — on parle en regardant, on ne bascule pas d'onglet pour noter.
Les notes s'enregistrent seules après une pause de frappe. Le rendu des chiffres
vient du module partagé : une réunion ne doit pas montrer un atelier différent
de celui qu'on regarde le reste du temps.

`tests/test_reunion.py` : 6 familles de cas, base sqlite en mémoire, aucun
import de l'app.


## 11. Reunions : un onglet de MyProd, plus une page a part (31/08/2026)

Demande : « il faudrait que /reunion soit une page tel qu'est vue d'ensemble,
retour de prod, saisie... ».

Ces trois ecrans ne sont pas des pages : ce sont les sous-onglets de
MyProd > Production. /reunions, lui, etait une page HTML autonome avec sa
propre barre du haut, sa propre feuille de style et son propre `<script>`. Il
lui manquait donc tout ce qui fait une page de MyProd : la barre laterale, le
titre, le sous-titre, la rangee de sous-onglets. Reponse : l'emboiter comme on
l'a fait pour Retour de prod.

### Ce qui change

`static/mysifa_reunions.js` (nouveau) porte tout l'ecran : liste des reunions,
reunion ouverte, notes, actions, impression. Il ne connait pas MyProd — il
recoit un contenant et s'y installe (`MySifaReunions.monter(racine, opts)`),
comme la memoire produit le fait pour les scans d'OF. Il garde son etat au
niveau du module : MyProd reconstruit son DOM a chaque rendu, une reference
gardee d'une passe a l'autre pointerait sur un noeud detache.

`static/mysifa_reunions.css` (nouveau) reprend la feuille de l'ancienne page,
integralement prefixee `reu-`. C'etait obligatoire : la page autonome utilisait
`.btn`, `.chip`, `.card`, `.modal`, `.split`, `#notes`, `#toast` — des noms qui,
dans la coquille MyProd, repeignent le reste de l'application.

`static/mysifa_prod_core.js` : `reunions` devient un sous-onglet reel
(`_PROD_SUB_TABS`, donc adressable par `#reunions`), plus une entree `lien` qui
faisait quitter la page. La branche `if(t.lien)` du gestionnaire de clic
disparait avec elle, plus aucun onglet ne navigue.

`app/web/reunions_page.py` : /reunions redirige vers `/prod#reunions`. Les
favoris et les liens existants continuent de fonctionner ; l'ancre est lue au
demarrage par `_readProdHash()`.

`app/web/html.py` (monolithe de repli, PROD_STANDALONE=0) recoit le meme
traitement, pour que les deux rendus ne divergent pas.

### Deux points de conception

**La barre de filtres ne s'affiche pas sur cet onglet.** Une reunion porte sa
propre periode analysee, celle qu'elle a enregistree et qu'on relit des mois
plus tard. Une barre de filtres au-dessus la contredirait a chaque ouverture.

**L'impression construit un document, elle ne masque pas la page.** Un onglet
s'imprime avec toute l'application autour. `#reu-doc` est rempli au moment
d'imprimer (identite de la reunion, notes en texte, actions, chiffres) et la
feuille de style masque tout le reste par `visibility` — meme technique que la
feuille d'atelier, pour que les deux impressions du module se comportent
pareil. Le nom du document reste `MySifa - Point de production JJ-MM-AAAA`.

### Verification

`node --check` sur `mysifa_reunions.js`, `mysifa_prod_core.js` et les blocs JS
de `html.py` ; `python3 -m compileall` et `pyflakes` sur les fichiers Python
touches ; les neuf suites de `tests/` restent vertes. APP_VERSION inchangee.
Le suffixe de cache `-reu1` est pose sur `mysifa_prod_core.js` : APP_VERSION ne
bougeant pas, sans lui le navigateur resservirait l'ancien coeur et l'onglet
resterait un lien mort.

**Le demarrage de l'application reste a verifier sur v1** : rien n'a pu etre
boote ici.

### Supprimer une reunion

Une corbeille par ligne dans le tableau. Elle reste a 35 % d'opacite tant qu'on
ne survole pas sa ligne : c'est une action destructrice, elle n'a pas a attirer
le clic. Le clic dessus ne peut pas ouvrir la reunion — la corbeille est testee
avant la ligne dans la delegation, et arrete la propagation.

La confirmation passe par une fenetre du module, pas par un `confirm()` natif
(qui n'a ni le theme ni la langue du reste), et elle nomme ce qu'on efface :
le titre de la reunion, plus le rappel que ses notes et ses actions partent
avec elle et que les remontees de production, elles, ne sont pas touchees.

Si la reunion supprimee est celle qui est ouverte a l'ecran, on repasse a la
liste : la laisser affichee avec un identifiant qui n'existe plus produirait une
404 au premier enregistrement.

L'endpoint `DELETE /api/reunions/{id}` existait deja (il supprime aussi
`reunion_actions` et `reunion_participants`) — rien de neuf cote serveur.

`tests/test_reunions_rendu.js` : 7 cas de plus (une corbeille par ligne,
identifiant et titre portes, intitule accessible, icone SVG et non emoji,
colonne distincte de l'etat, titre echappe dans l'attribut).

### Frise : le texte etait coupe, et l'ecran a moitie vide

Deux defauts signales sur la meme capture.

**« Ce n'est pas net »** — ce n'etait pas un probleme de rendu mais de place.
Le libelle d'un slot porte quatre lignes (dossier, client, reference + format,
quantite) dans une piste de 74 px dont 9 px sont pris par le ruban des phases :
61 px utiles. Aucune hauteur de ligne n'etait fixee, donc celle du theme
s'appliquait — a 1,35 les quatre lignes reclament 65 px. Elles debordaient, et
comme le bloc est centre verticalement, la coupe tombait en plein milieu des
lettres, en haut comme en bas. D'ou l'impression de flou.

Correction : hauteur de ligne fixee a 1,25 (elle decide de la mise en page, elle
ne doit pas etre subie) et piste portee a 92 px. Le calcul est refait : 66 px de
texte pour 75 px disponibles.

**Les slots etroits** rendaient quatre « … » superposes, ce qui n'apprend rien.
Le libelle a maintenant trois densites, posees selon la largeur du slot en
pourcentage de la piste — la meme unite que la geometrie qui arrive du serveur :
au-dela de 16 % les quatre lignes, entre 9 et 16 % la quantite tombe, en dessous
il ne reste que le numero de dossier. Au survol le slot s'ouvre et tout revient.

**La largeur** — le conteneur MyProd plafonne a 1200 px pour toute
l'application. Les Points de production sont le seul ecran qui pose une frise et
une colonne de notes cote a cote : a 1200 px la frise ecrase ses libelles alors
que la moitie droite de l'ecran est vide. La classe `.container.reu-large`
(1720 px) est posee par `render()` pour ce seul sous-onglet, et la colonne de
notes passe de 380 px figes a `clamp(340px, 24%, 440px)` : elle respire sur un
grand ecran sans manger la frise sur un petit.

La frise etant partagee, l'onglet Retour de prod beneficie des memes deux
premieres corrections.

`tests/test_retour_prod_rendu.js` : 7 cas de plus sur les seuils de densite
(bornes incluses, largeur absente traitee comme etroite, densite qui ne remplace
pas la classe de debordement).

### Participants : une recherche, pas un selecteur

Le selecteur de participants avait ete retire du lancement — au moment d'ouvrir
un point, on ne sait pas encore qui sera la. Il revient la ou il sert : dans la
colonne, pendant la reunion.

Le bloc ouvre la colonne, avant les notes et les actions. C'est l'ordre d'une
reunion : qui est la, ce qu'on se dit, ce qu'on decide.

L'annuaire (`personnes` de `/api/reunions/contexte`) est deja en memoire depuis
l'ouverture de l'onglet : la recherche filtre en local, elle ne part pas au
serveur a chaque touche. La comparaison se fait sans accent ni casse — dans un
atelier francais, taper « gregory » doit trouver « Grégory », sinon la recherche
ne sert a rien. La frappe est cherchee partout dans le nom — « lesaf » doit
trouver « Lesaffre » meme si c'est le nom de famille — mais un nom qui COMMENCE
par la frappe passe devant : taper « ma » propose Manuel et Marc avant
Desreumaux, ou le « ma » est au milieu. Huit resultats au plus.

Quand l'annuaire ne repond rien, la frappe est proposee telle quelle, marquee
« hors annuaire » : un point de production reunit parfois quelqu'un qui n'a pas
de compte, et la table `reunion_participants` stocke un nom, pas une cle
etrangere. Tant qu'il reste des noms a choisir, cette proposition n'apparait pas
— elle ne serait que du bruit sous la liste.

Deux details qui font la difference a l'usage : la frappe ne repeint que le bloc
participants et restaure la position du curseur — repeindre la colonne ferait
perdre le curseur a chaque lettre ; et `Entree` valide la premiere suggestion,
donc on tape trois lettres et on entre, sans toucher la souris. `Echap` vide la
recherche.

Cote serveur, rien de neuf : `POST /api/reunions/{id}` acceptait deja
`participants` et remplace la liste entiere. On lui envoie donc celle d'apres.
Les chiffres de production ne dependent pas des presents — le bloc se repeint
seul, sans recharger la reunion.

`tests/test_reunions_rendu.js` : 20 cas de plus (recherche au milieu du nom,
accents, casse, debuts de mot en tete, trait d'union qui coupe les mots,
exclusion des deja presents, plafond de huit, nom hors annuaire
propose seulement quand l'annuaire est muet, echappement du nom et de la frappe,
place du bloc avant les notes).

## 12. Les chiffres d'un point de production ne parlaient pas de sa journee (01/09/2026)

Signalement : « mes datas dans ma reunion du 1 septembre (analyse du 31/08) ne
sont pas correctes : vitesse de production, saisies (pour le dossier reliquat,
c'est essentiellement du "autre" alors que c'est faux) ».

L'export des saisies du 31/08 sur Cohesio 1 (29 lignes) a servi de banc d'essai :
le service passe dessus en base memoire, sans l'application.

### La preuve etait dans la capture

L'ecran annoncait 18 h 52 de production, 8 h 08 de calage et 1 h 16 d'arrets,
soit 28 h 16 d'activite. Sur la meme capture, l'axe de la frise dit que la
journee du lundi 31/08 dure 14,9 h. Une machine ne peut pas travailler 28 h en
15 h : le total ne pouvait pas venir de la seule journee analysee.

### Deux defauts, une racine

**1. La periode n'atteignait pas le calcul.** `retour_atelier` recevait bien les
bornes, les utilisait pour choisir les dossiers clotures dans la periode, puis
appelait `compte_rendu(conn, n)` — sans bornes. Or `compte_rendu` lit
`_saisies(conn, no_dossier)`, c'est-a-dire TOUTES les saisies du dossier, depuis
toujours. Un « Reliquat + Stock » qui revient toutes les semaines versait donc
chacune de ses passes dans le bilan d'une seule journee. Idem pour le metrage :
27 536 m affiches contre 17 717 m reellement produits le 31.

**2. Une saisie de fin de cycle durait.** La duree d'une saisie est l'ecart avec
la suivante du meme operateur. `89 - Fin de production` a 12 h 55 le 31/08 se
chainait donc a la saisie suivante du meme conducteur sur ce dossier — quatre
jours plus tard. Resultat : un intervalle de 1 004 minutes dans la categorie
`personnel`, dessine en gris sur la moitie de la frise. C'est le « essentiellement
du autre » du signalement. Le meme intervalle nourrissait `saisies_ouvertes` et
la vigilance, ce qui donnait une alerte permanente sur des dossiers sains.

Un troisieme effet decoulait du deuxieme : le rabotage anti-chevauchement de
`_slot` fixe une borne apres chaque segment. Un intervalle qui couvre toute la
fenetre pose cette borne a la fin de la journee, et TOUS les segments suivants
sont ecartes. Un long bloc gris pouvait donc effacer les vraies phases plutot que
de se poser a cote.

### Ce qui change

`intervalles(saisies, debut, fin, codes_fin)` porte les deux corrections :

- une saisie dont le code ferme un cycle (`89`, `90`) n'ouvre aucun intervalle.
  Un dossier repris plus tard repart par un code de debut, pas par la fin du
  cycle precedent ;
- avec une fenetre, chaque intervalle est ramene a l'interieur et ceux qui n'y
  mordent pas disparaissent. `minutes` est la duree retenue, `minutes_brutes` la
  duree reelle, `debut_brut`/`fin_brut` les bornes reelles — c'est sur elles que
  se jugent `douteuse` et les marqueurs de debordement de la frise, qui doivent
  continuer de dire qu'un dossier a commence avant la periode.

`temps_par_categorie`, `metrage_dossier` et `compte_rendu` acceptent la meme
fenetre ; `retour_atelier`, `comptes_rendus_periode` et `frise` la transmettent.
Pour le metrage, un cycle compte pour la periode ou il se CLOTURE : c'est la
cloture qui releve le compteur de fin.

**La fiche d'un dossier, elle, reste sur sa vie entiere** — c'est son role. Les
deux lectures cohabitent donc, et le compte-rendu affiche desormais laquelle il
montre (« Chiffres du 31/08/2026 » ou « Chiffres sur toute la vie du dossier »).
Sans cette ligne, ouvrir un dossier depuis la liste d'une periode donnait deux
metrages differents sans qu'on sache lequel repondait a quelle question.

### Mesure avant / apres

Meme jeu de saisies, dossiers ayant aussi tourne le 28/08 et le 01/09 :

| | avant | apres |
|---|---|---|
| production | 18 h 57 | 11 h 39 |
| calage | 7 h 00 | 2 h 00 |
| metrage | 97 022 m | 44 309 m |
| metrage du Reliquat | 27 536 m | 17 717 m |
| total sur une journee de 14,9 h | 26 h 49 (impossible) | 14 h 31 |
| ruban du Reliquat | 51 % de gris | 90 % de production, 9 % d'arret |

Les 27 536 m et les ~18 h 55 de production reproduits ici sont exactement les
chiffres de la capture : le scenario reconstitue bien ce qui se passait.

### Ce qui reste ouvert

`retour_atelier` ne retient que les dossiers CLOTURES dans la periode. Un dossier
qui a tourne toute la journee du 31 mais n'a ete cloture que le 01/09 ne compte
donc pas dans le point du 31 — il apparait sur la frise, pas dans les KPI. Le
total ne peut plus etre trop grand, mais il peut etre trop petit. Retenir les
dossiers ACTIFS dans la periode changerait le sens de « 2 dossiers » affiche en
sous-titre du metrage : a arbitrer.

### Verification

`tests/test_rapport_dossier.py` : trois familles de cas ajoutees — une periode ne
compte que ce qui s'y est passe (et le total tient dans la journee), une saisie
de fin de cycle ne dure pas, un intervalle a cheval est borne des deux cotes sans
perdre sa duree reelle. `tests/test_retour_prod_rendu.js` : 4 cas sur la portee
affichee. Les 41 suites du depot restent vertes.

### La section « Arrets » devient « Saisies »

Le classement des cinq arrets les plus couteux se lisait deja ailleurs : le KPI
« Arrets » donne le total et sa part du temps, la frise montre ou ils tombent.
Ce qui manquait, c'est le deroule de la journee — impossible a lire depuis un
point de production sans changer d'onglet.

La section liste donc les saisies de la periode : heure, pastille de statut aux
couleurs de Saisieprod, operation (sans son code), dossier et client en
sous-ligne, commentaire s'il y en a un, operateur, duree.

**Uniquement les saisies de production.** `/api/saisies` fusionne dans sa liste
les mouvements de stock (`kind: "stock"`) et les validations d'alerte
(`kind: "ack"`) ; `saisies_periode()` ne lit que `production_data`. Un point de
production regarde ce que la machine a fait, pas ce qui a transite par le
magasin. Les saisies annulees sont ecartees, et les codes de debut, de fin et de
pointage sont masques sur Repiquage — le meme masquage que l'onglet Saisies,
sinon les deux ecrans ne diraient pas la meme chose.

La duree est celle de partout ailleurs : l'ecart avec la saisie suivante du meme
operateur, bornee a la periode. Les voisines d'un jour avant et d'un jour apres
sont lues pour cela — sans la suivante, la derniere saisie de la journee n'aurait
pas de duree — mais elles ne figurent pas dans la liste.

Une journee fait vite trente lignes : la liste defile dans sa propre fenetre
(280 px) plutot que de repousser le reste de la feuille, et le bouton d'entete
l'ouvre a 72 % de la hauteur d'ecran. A l'impression, elle sort en entier, sans
ascenseur ni bouton. Plafond a 400 lignes, les plus recentes gardees.

`arrets_couteux` reste calcule et renvoye par l'API : l'information n'a rien
perdu de sa valeur, elle n'a simplement plus de section a elle. La remettre ne
coute qu'un bloc de rendu.

`tests/test_rapport_dossier.py` : deux familles de cas (le deroule d'une periode
et son bornage, les masquages Repiquage). `tests/test_retour_prod_rendu.js` :
16 cas sur le rendu de la section.

### Une reunion peut regarder plusieurs machines

L'en-tete n'offrait qu'un choix : une machine, ou toutes. Un point du matin
regarde souvent deux machines sur trois — il fallait alors ouvrir deux reunions,
ou tout regarder.

**Le stockage.** `reunions.machine` ne portait qu'un nom. Migration
`2026_09_01_reunion_machines` : une table `reunion_machines(reunion_id, machine)`,
meme forme que `reunion_participants`, qui se filtre et se compte sans reparser
un champ texte. Les perimetres des reunions deja tenues sont repris par un
`INSERT OR IGNORE` depuis l'ancienne colonne, qui reste en place et n'est plus
lue — sqlite ne retire pas une colonne sans reconstruire la table, et une
reunion ancienne n'a rien a perdre a garder la trace de ce qu'elle disait.

**Une reunion SANS ligne regarde tout l'atelier.** C'est le seul sens que
l'absence ait jamais eu, et c'est ce qui evite de stocker la liste complete des
machines — laquelle changerait a chaque machine ajoutee dans les Parametres.

**Le service.** `machines_demandees()` normalise une chaine, une liste ou rien
en une liste de noms, et `_filtre_machines()` rend le `IN (...)` correspondant,
insensible a la casse et aux blancs. `retour_atelier`, `frise`,
`saisies_periode`, `dossiers_clotures` et `comptes_rendus_periode` acceptent
donc indifferemment une machine, plusieurs ou rien. Les appelants qui n'en
passaient qu'une continuent de marcher sans changement.

**L'ecran.** Le menu deroulant devient une rangee de pastilles a cocher : un
menu ne sait dire qu'un choix. « Toutes » n'est pas une machine de plus dans la
liste — c'est l'etat par defaut, actif tant que rien n'est coche, et cocher tout
revient au meme. Decocher la derniere machine ramene a « Toutes » plutot que de
laisser un perimetre vide, qui ne montrerait rien.

L'onglet Retour de prod garde son selecteur unique : sa barre suit les filtres
de MyProd, qui ne parlent que d'une machine a la fois. Le service, lui, sait
deja faire les deux.

`tests/test_rapport_dossier.py` : 17 cas (normalisation, une/deux/toutes, casse
et blancs, propagation a la frise, aux comptes-rendus et au deroule des
saisies). `tests/test_reunion.py` : 9 cas sur la persistance du perimetre.
`tests/test_reunions_rendu.js` : 10 cas sur les pastilles.

### Le dossier prend sa propre colonne

Le tableau des saisies tenait en quatre colonnes, dossier et client glisses en
sous-ligne de l'operation. Resultat a l'ecran : « Marche 745 - Reliqua 3 -
Maitre C… » coupe a mi-mot, et une bande blanche de trois cents pixels entre
l'operation et l'operateur. La colonne Operation prenait toute la place restante
sans pouvoir la donner a son contenu.

Cinq colonnes maintenant — Heure, Operation, Dossier, Operateur, Duree — avec
`table-layout:fixed` et des largeurs posees : 56 px pour l'heure, 36 % pour
l'operation, 23 % pour l'operateur, 74 px pour la duree, le reste au dossier.
Le numero de dossier occupe sa premiere ligne, la reference produit et le client
la seconde. Le numero garde son `title` : certains font quarante caracteres et
l'ellipse est alors la seule mise en page possible.

La reference produit ne vit pas dans `production_data` — elle se lit par dossier
via `produit_series` ou `dossier_info_prod`. `saisies_periode()` la resout une
fois par dossier distinct, pas une fois par ligne.

Sous 1000 px on resserre au lieu de masquer : retirer une colonne ferait
disparaitre une information sans que personne ne sache qu'elle a existe, alors
qu'une ellipse se voit.

### Le repiquage : trois definitions des « machines de la periode »

Constat de depart : la frise donnait une ligne au Repiquage, mais le selecteur
ne savait pas le nommer. Un filtre incapable de designer ce qu'on affiche.

En cherchant pourquoi, on trouve trois definitions differentes du meme mot dans
le meme ecran :

| ou | ce qu'il appelait « les machines de la periode » |
|---|---|
| selecteur (`machines_periode`) | celles ayant CLOTURE un dossier (code `89`) |
| KPI (`dossiers_clotures`) | idem — donc aveugles au Repiquage |
| frise (`frise`) | toute machine ayant une saisie avec un dossier |

Le Repiquage n'a ni code de debut ni code de fin de dossier — ils y sont deja
masques dans l'onglet Saisies comme obsoletes. Pas de cycle, donc pas de
compteur, donc pas de metrage ni de cadence, et un slot de frise qui s'etale sur
toute la periode en un seul bloc. La capture le montre : cinq slots, « 4
dossiers » — le Xerox du Repiquage ne comptait dans aucun chiffre tout en
occupant une ligne entiere.

**Correction obligatoire** : `machines_periode()` liste desormais les machines
ayant TRAVAILLE sur la periode, cloture ou non. Le selecteur peut nommer ce que
la frise affiche.

**Choix arbitre** : une propriete `hors_production` sur la table `machines`,
cochee dans Parametres -> Machines, sur le modele exact de
`sans_matiere_premiere` que ce meme poste porte deja. Migration
`postes_hors_production`, qui coche le repiquage d'office par un LIKE sur le nom
— comme la migration de 2026-08-05.

Ce que la propriete fait : le poste est **decoche par defaut** dans le perimetre
d'une reunion. Sa pastille reste dans le selecteur, en pointille avec la mention
« hors prod », et un clic le ramene. On ne cache pas une machine, on arrete de
la compter par defaut.

**Ou la regle est appliquee.** Dans le routeur, pas dans le service : quand une
reunion n'a pas de perimetre explicite, le routeur resout « toutes » en la liste
des machines de production de la periode et la passe telle quelle. Le service ne
retire donc jamais rien en silence, et l'ecran affiche exactement le perimetre
qu'il a demande — l'en-tete de la feuille nomme les machines comptees au lieu
d'un « Toutes les machines » qui en cachait une.

Le jour ou le repiquage aura un vrai cycle cote Saisieprod, il suffira de
decocher la case.

`tests/test_rapport_dossier.py` : 6 cas (absence de table, absence de colonne,
colonne vide, poste coche, demande explicite qui repond quand meme, presence
dans le selecteur). `tests/test_reunions_rendu.js` : 7 cas sur la pastille en
retrait.

### Deux pieges de tableau, corriges ensemble

La colonne Operation s'est retrouvee ecrasee a cinquante pixels (« Arrive… »,
« Netto… », « Repris… ») avec un large vide a sa droite. Deux causes qui se
combinaient, toutes deux invisibles au test de rendu tant qu'on ne regarde que
la chaine produite :

1. **Un `<td>` en `display:flex` n'est plus une cellule de tableau.** Il sort de
   l'algorithme de mise en page, et plus aucune largeur ne le tient. La regle
   existait deja avant `table-layout:fixed` — elle passait inapercue parce que
   l'algorithme automatique repartissait quand meme. Le flex vit maintenant dans
   un conteneur INTERNE (`.rp-sa-opin`), la cellule reste une cellule.

2. **En `table-layout:fixed`, les largeurs se lisent sur la premiere rangee ou
   sur les `<col>`.** Les miennes etaient posees sur les `<td>` du corps : elles
   etaient purement et simplement ignorees. Un `<colgroup>` de cinq `<col>`
   nomme desormais chaque colonne, et c'est lui qui porte les largeurs.

L'intitule de l'operation gagne au passage son `title` au survol, comme le
numero de dossier : quand la colonne est etroite, l'ellipse est la seule mise en
page possible, mais le texte entier doit rester atteignable.

`tests/test_retour_prod_rendu.js` : 3 cas de plus qui verrouillent la structure
elle-meme (colgroup present, cinq colonnes declarees, flex a l'interieur de la
cellule et non sur elle). Ils ne remplacent pas un oeil sur l'ecran, mais ils
empechent la regression silencieuse.
