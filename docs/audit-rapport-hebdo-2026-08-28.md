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
