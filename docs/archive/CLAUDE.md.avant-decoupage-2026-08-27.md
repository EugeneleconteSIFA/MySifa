# MySifa — Instructions pour Claude / Cursor / Windsurf

## Contexte projet

MySifa est un outil interne de gestion de production industrielle développé pour SIFA. Il est utilisé quotidiennement par des opérateurs, des responsables de production et des administrateurs. L'outil tourne sur un VPS Linux et est servi via FastAPI.

**Modules actifs :**

| Module | Route | Description |
|---|---|---|
| MyProd | `/prod` | Saisie de production opérateur |
| Planning machine | `/planning` | Planning atelier multi-machines |
| MyStock | `/stock` | Gestion des stocks et emplacements |
| MyCompta | `/compta` | Suivi comptable |
| MyExpé | `/expe` | Gestion des départs |
| Planning RH | `/planning-rh` | Planning du personnel |
| Paie | `/paie` | Module paie |
| Paramètres | `/settings` | Gestion comptes, rôles, annonces (super admin) |

---

## Kernse — commercialisation & paramétrage (règle stratégique)

MySifa est aussi le socle technique du produit commercial **Kernse**
(SaaS TPE/PME industrielles). Le code est unique : c'est le paramétrage qui
différencie une instance SIFA d'une instance client Kernse. Le dossier
`kernse/` à la racine héberge tout ce qui est spécifique à la
commercialisation (console plateforme, provisioning, onboarding, seeds
métier, design system Kernse, landing publique). Voir `kernse/CLAUDE.md`
pour les règles propres à ce dossier.

**Règle absolue applicable à tout le repo — paramétrable dès l'écriture,
SIFA reste défaut :**

Aucune donnée qui décrit une entreprise cliente n'est écrite en dur dans le
code. Machines, opérations, terminologie, transporteurs, structure de coûts,
calendrier, rôles, plans d'emplacement, taux horaires, jours de fermeture :
tout vit en base et s'édite dans Paramètres. Le code lit un référentiel, il
ne le contient pas.

Le pattern est celui du refactor `APP_NAME` : la valeur par défaut =
la valeur SIFA actuelle, aucune rupture pour la prod, la démo Kernse et les
futurs clients surchargent via `.env` (scalaires) ou via un seed (référentiels
métier). Concrètement :

- **Scalaire** (nom, URL, seuil, couleur d'accent) → variable dans `config.py`
  avec `os.getenv("XXX", "<valeur SIFA>")`.
- **Petit référentiel figé** (statuts, sévérités, codes techniques
  structurants) → constante Python dans `config.py`, mais lue via une
  fonction, jamais interpolée en dur dans un template.
- **Référentiel métier** (machines, opérations, transporteurs, types de NC,
  postes de coût, jours de fermeture) → table SQLite créée par migration,
  seedée avec les valeurs SIFA pour la prod (v2) et v1, laissée vide pour la
  démo Kernse et les futures instances clientes, exposée par un CRUD dans
  Paramètres.

**Anti-patterns interdits sur tout le repo :**

- Écrire `"Cohésio 1"`, `"Repiquage"`, `"Errepi"`, `"Bunsch"`, ou tout autre
  nom propre SIFA en dur dans un router, une page ou un composant JS.
- Coder un `if machine == "Cohésio 1":` — la logique métier ne dépend jamais
  d'une chaîne d'identifiant machine mais d'attributs (`type`, `capacite`,
  `taux_horaire`) qui sont en base.
- Injecter `"eleconte@sifa.pro"`, `"admin@sifa.fr"`, `"mysifa.com"`,
  `"sifa.pro"` dans un template envoyé à un utilisateur final. Ces valeurs
  existent dans `config.py` (via env) — on lit la variable, pas la chaîne.
- Ajouter un template email qui commence par « Bonjour, SIFA vous
  informe... » — c'est `APP_TITLE` qu'on interpole.
- Écrire une migration qui remplit une nouvelle table avec des valeurs SIFA
  sans conditionner ce seed à `ENV_NAME` ou à un flag « pas d'écrasement si
  déjà rempli ». Un client Kernse démarre avec une table vide que
  l'onboarding remplit, pas avec les codes SIFA à effacer.

**Question test à se poser avant chaque nouvelle valeur métier :** « un
client imprimerie de Lille qui installe Kernse demain matin, cette valeur
a-t-elle un sens pour lui ? ». Si non → paramètre obligatoire. En cas de
doute → paramètre obligatoire par défaut (on préfère un paramètre inutile à
une constante à refactoriser plus tard).

**Deux étages de paramétrage :**

- **Plateforme** (Kernse en tant qu'éditeur) : `platform_settings` + `.env` du
  VPS, éditée par le superadmin plateforme (Eugène). Exemples : nom de
  marque global, URL landing, clé Stripe, catalogue des plans, catalogue
  des jeux de départ métier.
- **Entreprise** (le client) : `client_settings` + tables métier (`machines`,
  `operations`, `transporteurs`, `nc_types`, `postes_cout`...), éditée par le
  superadmin de l'organisation cliente. Exemples : machines de l'atelier,
  codes opérations retenus, transporteurs utilisés, taux horaires,
  terminologie (« dossier » / « OF » / « commande »), rôles renommés.

**Existant SIFA-spécifique à généraliser progressivement** (chantier B du
brainstorm Kernse) : machines de `planning`, codes d'`operations.json`,
transporteurs et grilles tarifaires MyExpé, plan d'emplacements
`emplacements_plan.csv`, structure de coûts pricing v78, jours fériés + jours
off SIFA, noms de rôles (`ROLE_*` dans `config.py`), lexique (« dossier »
partout dans l'UI). Ordre de priorité : machines + opérations d'abord (dont
dépendent MyProd, Planning, Maintenance et rentabilité).

**Modules verticaux (imprimerie/façonnage) :** MyBAT, MyPrint, Appels d'offre
ne sont pas SIFA-spécifiques mais ne sont pas génériques non plus. Ils vivent
dans `app/` (comme aujourd'hui) mais sont marqués `module_optional=True` et
`vertical="imprimerie"` dans le catalogue de modules — désactivés par défaut
sur un plan Kernse Atelier générique, activables via un pack vertical.

---

## Stack technique

- **Backend** : Python 3 / FastAPI — point d'entrée `main.py` à la racine
- **Frontend** : HTML/CSS/JS vanilla, généré côté serveur en chaînes Python (dans `app/web/*.py`)
- **Base de données** : SQLite unique — fichier actif : `data/production.db` (chemin défini par `DB_PATH` dans `config.py`)
- **Auth** : sessions cookie (`sifa_token`), durée 6h
- **Migrations DB** : un fichier par migration dans `app/core/migrations/`, identifiée par son `NOM` (table `schema_migrations_fichiers`). Les migrations historiques 1→225 restent dans `_migrate()` de `app/core/database.py` — voir la section « Migrations de base de données »

**Rôles disponibles :**
`superadmin`, `direction`, `administration`, `fabrication`, `logistique`, `comptabilite`, `expedition`, `commercial`

---

## Stratégie de déploiement v1 / v2 — LIRE EN PREMIER

**Deux instances FastAPI tournent côte à côte sur le VPS, indépendantes**, sur des processus et ports séparés. C'est volontaire — ce n'est pas une erreur de configuration ni un reliquat à nettoyer.

| Service systemd | Chemin code | Port | Domaine | Rôle |
|---|---|---|---|---|
| `mysifa` | `/home/sifa/production-saas/` | 8000 | `www.mysifa.com` | **Prod** — utilisée par tous les utilisateurs |
| `mysifa-v1` | `/home/sifa/production-saas-v1/` | 8002 | `v1.mysifa.com` | **Staging** — réservée au super admin, bandeau rouge permanent en haut de chaque page |

Les deux instances ont chacune **leur propre base de données** (`DB_PATH` distinct dans chaque `.env`) : prod utilise `production.db`, v1 utilise `production-v1.db`. Un cron nightly à 02:00 UTC (`/etc/cron.d/mysifa-v1-resync` → `/usr/local/bin/mysifa-v1-resync-db.sh`) écrase la DB de v1 avec une copie fraîche et live-safe de la prod (via `sqlite3 .backup`), pour que les devs voient des données réelles tous les matins. Les 7 derniers backups pré-resync sont conservés dans `/home/sifa/backups/v1-db-rotation/`, log dans `/var/log/mysifa-v1-resync.log`. Toute écriture sur v1 reste donc locale à v1 jusqu'au prochain resync. Les migrations de schéma s'appliquent indépendamment sur chaque DB (`MIGRATIONS_DISABLED=0` partout) — v1 sert ainsi de banc d'essai aux migrations avant promotion en prod.

**Variables d'environnement clés** (déclarées dans `config.py`, lues depuis `.env`) :

- `ENV_NAME` : `"v2"` par défaut, `"v1"` sur l'instance staging. Pilote l'affichage du bandeau rouge dans `app/web/html.py` et le skip des seeds au boot dans `main.py`.
- `MIGRATIONS_DISABLED` : `0` partout. Comme chaque instance a sa propre DB depuis juin 2026, v1 joue ses migrations sur sa DB locale sans impact sur la prod. Mettre à `1` ponctuellement si tu veux geler temporairement le schéma.
- `PORT` : `8000` par défaut, `8002` sur v1.

**Workflow de déploiement (obligatoire)**

1. Tu codes en local sur une feature branch (`git checkout -b feature/xxx` depuis `staging`), tu pushes, tu ouvres une PR vers `staging`. En solo : tu peux merger directement. À plusieurs : PR review obligatoire (voir "Workflow multi-dev" plus bas).
2. Sur le VPS, le cron `/etc/cron.d/mysifa-v1-pull` exécute toutes les minutes `/usr/local/bin/mysifa-v1-pull.sh` qui pull `origin/staging` + restart `mysifa-v1` si la branche a bougé. v1 reflète donc les merges sur `staging` dans la minute.
3. Tu testes sur `https://v1.mysifa.com`. Le bandeau rouge confirme que tu es sur le staging. v1 ayant sa propre DB, tu peux tester librement (créer, modifier, supprimer) sans impact sur la prod.
4. Quand tu es satisfait, tu vas dans `/settings` sur v1 → onglet "Promouvoir v1 → v2" → tu remplis (optionnellement) les notes de release → clic.
5. Le bouton appelle `POST /api/promote` qui lance `sudo /home/sifa/production-saas-v1/scripts/promote_v2.sh "notes"`. Le script fait : backup DB, capture HEAD v2, `git pull` sur v2, chown, `systemctl restart mysifa`, healthcheck sur `/healthz` (15s timeout), **rollback auto complet si KO** (restore DB + git reset HEAD précédent + restart + annonce d'échec), annonce de release si notes fournies.

**Règles absolues — ne JAMAIS enfreindre**

- **JAMAIS** de `git pull`, `git reset`, ou `systemctl restart mysifa` à la main sur `/home/sifa/production-saas/` (v2). v2 ne bouge **que** via le bouton "Promouvoir" depuis v1. Tout autre chemin contourne le backup pré-promotion et le rollback automatique.
- **JAMAIS** de `git pull` manuel sur `/home/sifa/production-saas-v1/` (v1) — le cron s'en charge. Sinon les perms se cassent.
- **JAMAIS** de push direct sur `main` — tout passe par une PR depuis une feature branch vers `staging`, puis validation sur v1, puis bouton "Promouvoir" (qui s'occupe du merge `staging → main` et du déploiement). Pousser sur `main` à la main court-circuite le test sur v1, la review et le backup pré-promotion.
- Les migrations de schéma se testent sur v1 (DB isolée). Le resync nightly écrase la DB v1 avec celle de prod, donc la migration sera rejouée le lendemain à partir du code mergé sur `staging`. Avant chaque promotion, vérifier que la migration tourne proprement sur v1.
- Si une IA dans une autre conversation suggère de "git pull dans le dossier prod pour mettre à jour" ou de "restart le service mysifa", elle ignore cette stratégie — corrige-la avant de suivre ses instructions.

**Numéro de version (footer)**

`APP_VERSION` dans `config.py` ligne 31. Le script `promote_v2.sh` ne bump **pas** automatiquement. Pour incrémenter le numéro affiché en bas de page, édite la constante en local, commit, push, puis promu (la promotion utilisera la nouvelle valeur committée).

**Proposition automatique de bump** (règle pour Claude / Cursor / Windsurf) — dès qu'une conversation aboutit à une modif fonctionnelle prête à être poussée (nouvelle feature, fix visible, changement UI, migration DB, changement de comportement API), l'IA **doit systématiquement** :

1. Lire la valeur actuelle de `APP_VERSION` dans `config.py`.
2. Proposer explicitement une nouvelle valeur en respectant semver adapté au projet :
   - **patch** (`1.1.2 → 1.1.3`) : fix, ajustement mineur, correction UI, wording
   - **minor** (`1.1.2 → 1.2.0`) : nouvelle feature visible utilisateur, nouveau module, changement notable de comportement
   - **major** (`1.1.2 → 2.0.0`) : refonte structurelle, breaking change côté données, migration lourde
3. Formuler la proposition sous forme d'une phrase courte, par exemple : « Je propose de passer `APP_VERSION` de `1.1.2` à `1.1.3` (patch — fix bandeau login). Ok ? »
4. Attendre la validation d'Eugène avant d'éditer `config.py`.

Ne jamais bumper la version sans proposition explicite. Ne jamais bumper si la conversation portait uniquement sur de l'exploration, du debug non déployable, ou un travail non terminé.

**Endpoint santé**

`GET /healthz` (dans `main.py`) répond `{"status":"ok","env":"v2","version":"0.6.1"}` si la DB répond, 503 sinon. C'est ce que le script de promotion utilise pour valider la mise à jour avant de conclure ou de rollback.

**Backups et resync v1**

- DB de prod : `/home/sifa/production-saas/app/data/production.db`. Backup pré-promotion automatique par `promote_v2.sh`. Backups manuels libres dans `/home/sifa/backups/`.
- DB de v1 : `/home/sifa/production-saas-v1/app/data/production-v1.db`. Resync nightly à 02:00 UTC, log dans `/var/log/mysifa-v1-resync.log`. Rotation des 7 derniers backups dans `/home/sifa/backups/v1-db-rotation/`.
- Resync à la demande : `sudo /usr/local/bin/mysifa-v1-resync-db.sh` (stop v1 + clone live-safe depuis prod + restart + healthcheck).

**Workflow multi-dev (cible quand l'équipe grandit)**

- Chaque dev part d'une feature branch depuis `staging` (`git checkout staging && git pull && git checkout -b feature/xxx`).
- Une PR par feature, mergée dans `staging` après review. v1 la déploie automatiquement dans la minute.
- Promotion `staging → main` via le bouton `/settings` (déploie sur prod, rollback auto si KO).
- À configurer côté GitHub : protection de branche sur `main` (push direct interdit, PR review obligatoire), CI minimale (`ast.parse` sur les `.py` modifiés + `node --check` sur les `.js`).

**Conventions Git pour les scripts shell**

Tout fichier `.sh` créé depuis Windows doit être marqué exécutable dans Git via `git update-index --chmod=+x scripts/foo.sh`, sinon le bit `+x` saute à chaque pull sur Linux. Le `.gitattributes` à la racine force les `.sh` en fins de ligne LF (sinon `bash` ne reconnaît pas le shebang).

---

## Structure des fichiers

```
MySifa/
├── main.py                   # Point d'entrée FastAPI (lancer l'app depuis ici)
├── config.py                 # Configuration centrale (DB_PATH, rôles, constantes) — SOURCE DE VÉRITÉ
├── database.py               # Shim de compatibilité → pointe vers app/core/database.py
├── operations.json           # Référentiel codes opérations (severity, label, category)
├── requirements.txt
│
├── app/
│   ├── core/
│   │   ├── database.py       # Schéma DB, migrations historiques, get_db() — NE PAS DUPLIQUER
│   │   └── migrations/       # UNE MIGRATION = UN FICHIER (toute nouvelle migration va ici)
│   ├── routers/              # Tous les endpoints FastAPI (source réelle)
│   │   ├── auth.py
│   │   ├── fabrication.py    # API saisie de production
│   │   ├── planning.py       # API planning machine
│   │   ├── settings.py       # API paramètres + annonces MAJ
│   │   ├── stock.py, compta.py, expe_departs.py, paie.py, planning_rh.py …
│   ├── web/                  # Pages HTML/CSS/JS (source réelle)
│   │   ├── html.py           # Layout commun, login, portail, sidebar (~8700 lignes)
│   │   ├── planning_page.py  # Page planning (~3100 lignes)
│   │   ├── fabrication_page.py # Page saisie production (~2200 lignes)
│   │   ├── stock_page.py     # Page stock (~3200 lignes)
│   │   ├── settings_page.py  # Page paramètres admin (~1500 lignes)
│   │   └── …
│   ├── services/             # Logique métier réutilisable
│   └── models/               # Modèles Pydantic
│
├── frontend/                 # Shims de compatibilité → pointent vers app/web/ (ne pas modifier)
├── routers/                  # Shims de compatibilité → pointent vers app/routers/ (ne pas modifier)
│
├── data/
│   ├── production.db         # BASE ACTIVE — ne jamais supprimer ni écraser
│   ├── uploads/              # Fichiers uploadés par les utilisateurs
│   └── emplacements_plan.csv
│
├── scripts/                  # Scripts de maintenance one-shot (migrations, imports, repairs)
└── tools/                    # Utilitaires (backup, import CSV, deploy)
```

**Règle absolue sur la DB — CRITIQUE, NE JAMAIS ENFREINDRE :**

La base de données active sur le VPS est `/home/sifa/production-saas/app/data/production.db`.
Ce chemin est défini dans `.env` via `DB_PATH=/home/sifa/production-saas/app/data/production.db`.

- **Ne jamais modifier `DB_PATH` dans `.env`**, ni directement ni via `sed`, ni via un script
- **Ne jamais déplacer, renommer, remplacer ou créer un symlink** sur `app/data/production.db`
- **Ne jamais copier une autre DB par-dessus** sans backup explicite et confirmation de l'utilisateur
- Les fichiers `mysifa.db` (racine ou data/) sont des fantômes vides — les ignorer
- `production.db` à la racine est une ancienne archive — ne pas utiliser
- En local (Mac), la base active est `data/production.db` — les données à jour sont toujours sur le VPS

Ces règles ont été violées deux fois par des IA (Cursor puis Claude) et ont causé des pertes de données. Toute modification de chemin DB nécessite une confirmation explicite de l'utilisateur.

**Règle absolue sur config.py :** `config.py` à la racine est la source de vérité. `app/config.py` est une vieille copie incomplète. Tout import de configuration doit venir de `config.py` (racine).

---

## Conventions de code

**JavaScript (frontend)**
- État central dans un objet `S` — ne jamais stocker d'état dans des variables globales séparées
- Fonctions de rendu : `render()`, `renderEntries()`, `renderTL()` — elles reconstruisent le DOM
- Appels API via la fonction locale `api(path, options)` qui gère credentials et JSON
- Les modals sont injectés dans `document.getElementById("mroot").innerHTML = …`
- `escHtml()` et `escAttr()` obligatoires pour toute interpolation de données utilisateur dans le HTML
- `duree_heures` est `REAL` en DB — toujours `parseFloat()`, jamais `parseInt()`
- `date_operation` est stocké en `"%Y-%m-%dT%H:%M:%S"` heure Paris (pas de timezone dans la chaîne)

**Python (backend)**
- Migrations DB : un fichier dans `app/core/migrations/` avec `NOM` + `appliquer(conn)` — jamais de nouveau numéro dans `_migrate()`
- Seeds idempotents : toujours `INSERT OR IGNORE`
- Ne jamais bloquer une saisie pour une erreur de mise à jour planning : `try/except: pass`
- Imports de config toujours depuis `config` (racine), jamais depuis `app.config`

---

## Design system — règles à respecter absolument

### Thème et variables CSS

```css
/* Dark (défaut) */
--bg: #0a0e17
--card: #111827
--border: #1e293b
--text: #f1f5f9
--text2: #cbd5e1
--muted: #94a3b8
--accent: #22d3ee
--accent-bg: rgba(34,211,238,0.12)
--success: #34d399   /* alias --ok */
--warn: #fbbf24
--danger: #f87171

/* Light (body.light) */
--bg: #f1f5f9
--card: #ffffff
--border: #e2e8f0
--text: #0f172a
--accent: #0891b2
```

**Ne jamais utiliser de couleurs codées en dur** — toujours les variables CSS. Le thème light doit être testé systématiquement si on modifie des couleurs.

### Typographie
- Police : `'Segoe UI', system-ui, sans-serif`
- Tailles courantes : labels 12px / corps 13px / titres 15px / brand 32px
- Labels formulaires : uppercase, letter-spacing 0.5px, font-weight 600

### Composants communs

**Boutons**
```css
.btn { border-radius: 10px; padding: 10px 18px; font-weight: 700; transition: filter .15s }
.btn:hover { filter: brightness(1.05) }
/* Variantes : .btn-accent (fond --accent), .btn-danger (fond --danger), .btn-ghost (transparent) */
```

**Règles absolues sur les boutons — à respecter partout, sans exception**

1. **Pas de fond transparent au repos.** Un bouton avec `background: transparent`
   sur un fond de page `var(--bg)` est visuellement absent tant que le curseur
   n'est pas dessus — l'utilisateur ne voit pas l'affordance. Toujours donner
   un fond explicite :
   - Bouton posé **sur la page** (fond `var(--bg)`) → `background: var(--card)`
     (blanc en mode clair, sombre en mode dark) pour contraster avec le fond.
   - Bouton posé **à l'intérieur d'une card / modal** (fond `var(--card)`) →
     `background: var(--bg)` (gris clair / plus sombre) pour contraster avec
     la card.
   - Bouton **actif / sélectionné** → `background: var(--accent-bg)` +
     `border: 1px solid var(--accent)` + `color: var(--accent)`.
   - Bouton **danger / destructif** → fond `var(--danger)` + texte blanc.

   La variante `.btn-ghost` de la CSS globale reste tolérée uniquement pour
   des cas très localisés (ex. bouton "×" de fermeture posé sur un fond déjà
   coloré) — jamais comme choix par défaut pour un CTA visible dans la page.

2. **Cohérence hover.** Si le repos est `var(--card)`, le hover doit être
   `var(--bg)` (effet "s'assombrit" en mode clair, "s'éclaircit" en mode
   dark). Et **toujours définir le `mouseleave` symétrique** qui rétablit le
   fond de repos — sinon le bouton "reste" en état hover après un clic.
   Anti-pattern classique : `mouseleave` qui remet `transparent` alors que le
   repos est `var(--card)` → flash inversé au sortir du bouton.

3. **Boutons à fond coloré (accent, success, danger, warn) — la couleur du
   texte et de l'icône dépend du thème.** Un bouton `background: var(--accent)`
   (cyan) affiche du texte lisible en mode dark avec `color: #0a0e17` (le fond
   dark), mais en mode light il faut du texte foncé pour rester lisible sur
   le cyan. Pattern à adopter :
   ```css
   /* Sur fond --accent : texte foncé qui reste lisible dans les 2 thèmes */
   .btn-accent { background: var(--accent); color: var(--bg); }
   ```
   Le principe : `color: var(--bg)` produit **automatiquement** un texte
   contrasté (foncé sur clair, clair sur foncé) parce que `--bg` bascule
   avec le thème. Idem pour un bouton `background: var(--danger)` (rouge)
   qui reste toujours foncé → `color: #ffffff` est acceptable. Le point clé :
   **jamais** `color: var(--text)` ou `color: var(--text2)` sur un bouton à
   fond coloré — ces variables suivent le thème et vont produire du texte
   sombre sur fond sombre en mode dark, invisible.

   Bug historique : une IA a mis `color: var(--text2)` sur un badge cyan
   `background: var(--accent-bg)` — invisible en mode dark (text2 = clair
   sur accent-bg qui est déjà clair). Toujours tester dans les deux thèmes
   à chaque ajout de composant à fond coloré.

**Inputs / Champs**
```css
background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
padding: 12px 16px; color: var(--text); font-size: 14px;
transition: border-color .15s
input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(34,211,238,.12) }
```

**Cards**
```css
background: var(--card); border: 1px solid var(--border); border-radius: 12px;
```

**Toasts** : `showToast(message, type)` — `type` parmi `success`, `danger`, `info`. Jamais de popup `alert()`.

**Icônes** : SVG inline via la fonction `icon(name, size)` — pas d'emojis dans les icônes fonctionnelles.

---

## Fluidité des postes — mode éco automatique

Tous les postes de l'atelier ne se valent pas. `static/mysifa_perf.js`, chargé
dans le `<head>` de chaque page **sans `defer`**, compte les images réellement
affichées pendant une seconde après le chargement. Sous 30 images par seconde
(ou sur un faisceau d'indices : peu de cœurs, peu de RAM, rendu lent), il pose
`perf-eco` sur `<html>` et `<body>` — plus `reduce-anim`, que `motion.js` lit
déjà — et `static/mysifa_perf.css` coupe le fond animé, les `backdrop-filter`
et les transitions.

**Conséquences pour toute nouvelle page ou tout nouvel effet :**

- Un nouveau document HTML complet (un `app/web/*_page.py` de plus) doit
  inclure `mysifa_perf.css` **et** `mysifa_perf.js` dans son `<head>`, comme il
  inclut déjà `mysifa_theme.js`. Sans ça, la page reste lourde sur les postes
  lents alors que tout le reste de MySifa s'est allégé.
- Un effet coûteux (filtre SVG, `backdrop-filter`, animation d'un `filter` ou
  d'un `box-shadow`, animation plein écran) doit être écrit pour pouvoir
  disparaître : soit il tombe déjà sous une règle de `mysifa_perf.css`, soit on
  y ajoute la règle correspondante dans le même commit.
- Le verdict est **collant** : un poste passé en éco n'en ressort pas tout
  seul, puisqu'une nouvelle mesure se ferait effets coupés et serait bonne par
  construction. Le retour se fait dans Mon profil → « Fluidité de l'affichage »,
  bouton « Refaire la mesure ».
- L'utilisateur garde la main : Automatique / Complet / Allégé dans Mon profil
  (clé localStorage `mysifa_perf_mode`).

Côté serveur, chaque session remonte un relevé (`POST /api/perf/releve`, table
`perf_releves`). La vue `/perf-postes` (superadmin et direction, accessible depuis
Paramètres → Audit & qualité) classe les postes du plus lent au plus fluide et liste les pages les plus lourdes. Piège
de lecture : un poste déjà en éco mesure sans les effets, donc son FPS est bon
— c'est son passage en éco qui est le signal, pas son chiffre.

---

## Cohérence inter-applications — règle fondamentale

**Toutes les pages de MySifa partagent exactement la même sidebar et le même footer.** Quand on crée un nouvel onglet ou une nouvelle application, copier fidèlement la structure de `app/web/html.py` :

### Sidebar (structure invariable)
```
Logo MySifa (haut)
─────────────────
Liens de navigation (.nav-btn)
  → icône SVG + label + badge optionnel (.nav-badge)
  → état actif : class .active + background accent-bg + couleur accent
─────────────────
.sidebar-bottom (bas, collé au bas via margin-top:auto)
  → .user-chip (nom + rôle de l'utilisateur connecté)
  → .theme-btn (bascule dark/light)
  → .logout-btn (déconnexion)
  → .version (numéro de version monospace)
```

**Ne jamais omettre le `.sidebar-bottom`**. Ne jamais changer l'ordre des éléments du bas. Le bouton logout doit toujours être présent.

**Feedback cliquable sur le logo et tous les éléments interactifs de la
sidebar.** Le logo de chaque module (ex. `My<span>Qualité</span>`,
`My<span>Sifa</span>`, `My<span>Prod</span>`...) DOIT être cliquable pour
revenir au menu général du module — et cette cliquabilité DOIT être
visible :

- `cursor:pointer` sur le `.logo`
- Effet `:hover` cohérent avec les `.nav-btn` (fond `var(--accent-bg)`,
  couleur du texte principal qui bascule sur `var(--accent)`)
- `title=""` avec un texte explicite (ex. "Menu MyQualité")
- Handler `onclick="setView(\'menu\')"` ou équivalent

Règle générale : **tout élément cliquable de la sidebar (logo, cards,
badges, boutons)** doit avoir un état hover visible et un `cursor:pointer`.
Sans feedback visuel, l'utilisateur n'a aucun moyen de savoir qu'il
peut cliquer — bug rencontré sur le logo MyQualité (juillet 2026, ajouté
sans hover initialement).

### Topbar mobile
La topbar mobile (`.mobile-topbar`) est toujours présente et contient :
- Bouton menu hamburger (`.mobile-menu-btn`) → toggle classe `sb-open` sur `body`
- Titre de la page courante + sous-titre optionnel (`.mobile-topbar-sub`)
- Bouton retour portail (`.mobile-home-btn`) si pertinent

### Comportement sidebar mobile
- La sidebar est fixée, masquée via `translateX(-105%)` sur mobile
- `body.sb-open` l'affiche
- Un overlay `.sidebar-overlay` ferme la sidebar au clic en dehors

### Liens de navigation
Toujours inclure les liens vers les modules auxquels l'utilisateur a accès (vérifiés via le contexte de session). La cohérence des icônes entre pages est obligatoire — si un module utilise un certain SVG dans une page, il doit utiliser le même dans toutes les autres.

---

## UX — principes fondamentaux

**L'utilisateur d'abord.** Chaque fonctionnalité doit être immédiatement compréhensible sans explication. Si ça nécessite un guide, c'est que l'interface n'est pas assez claire.

**Visuel et direct.** Préférer les états visuels (couleurs, indicateurs, badges) aux messages texte. Un statut doit se lire en un coup d'œil, pas en lisant une phrase.

**Intuitif.** Les actions courantes (saisir, filtrer, chercher, valider) doivent être accessibles sans navigation. Les actions destructives demandent toujours une confirmation.

**Réactif.** Toute action utilisateur doit avoir un retour immédiat (toast, état de chargement, changement visuel). Ne jamais laisser l'utilisateur se demander si son action a été prise en compte.

**Cohérent.** Le même mot, la même couleur, le même geste doit signifier la même chose partout dans l'application. Si un bouton bleu confirme dans une page, il confirme partout.

---

## Searchbars — règles de comportement obligatoires

Les searchbars sont un point de friction fréquent. Règles à respecter impérativement :

### Ne jamais perdre le focus après un `render()`

Quand une searchbar déclenche un re-render du DOM (`renderEntries()`, `renderTL()`, etc.), le champ perd son focus si le DOM est reconstruit. **Pattern obligatoire :**

```javascript
// Avant le render, sauvegarder l'état du focus
function renderEntries() {
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;

  // … reconstruction du DOM …

  // Après le render, restaurer le focus ET la position du curseur
  if (focusId) {
    const el = document.getElementById(focusId);
    if (el) {
      el.focus();
      if (caretStart != null) {
        try { el.setSelectionRange(caretStart, caretEnd); } catch(e) {}
      }
    }
  }
}
```

### Ne jamais reconstruire le conteneur de la searchbar elle-même
La searchbar doit être dans un conteneur qui n'est pas re-rendu. Seule la liste de résultats est reconstruite.

### Comportement attendu d'une searchbar
- Filtre dès le premier caractère saisi (pas de bouton "Rechercher")
- Résultats en temps réel à chaque `oninput`
- Touche `Escape` vide le champ et restaure la liste complète
- Message explicite si aucun résultat : "Aucun résultat pour « [terme] »"
- Le placeholder décrit les champs cherchés : ex. `"Rechercher (client, OF, réf produit…)"`

### Searchbar dans un picker/modal
Autofocus automatique à l'ouverture :
```javascript
requestAnimationFrame(() => { document.getElementById("search-id")?.focus(); });
```
Les touches `ArrowUp` / `ArrowDown` / `Enter` naviguent dans les résultats sans soumettre le formulaire.

---

## Terminologie métier (à respecter partout, y compris dans les messages)

| Terme technique | Affiché / utilisé |
|---|---|
| `statut = attente` | En attente |
| `statut = en_cours` | En cours |
| `statut = termine` | Terminé |
| `statut_reel = reellement_en_saisie` | ⚙ en saisie |
| `statut_reel = reellement_termine` | ✓ saisie terminé |
| `operation_code = 01` | Début de production |
| `operation_code = 89` | Fin de production |
| `fin_dossier = true` | Dossier clôturé |
| `no_dossier` | Référence dossier |
| `planning_entries` | Dossiers au planning |
| `production_data` | Saisies de production |
| Machines | Cohésio 1, Cohésio 2, DSI, Repiquage |

---

## Ton et style éditorial

- **Pas d'emojis** dans les messages, toasts, labels, annonces ou release notes
- Icônes neutres acceptées : →, ·, ✓, ×, ▸ et SVG inline
- Ton **professionnel et direct** — pas de formules commerciales, pas de "Bonjour !", pas de "De belles nouveautés vous attendent"
- Les messages d'erreur sont **factuels et actionnables** : "Durée invalide — valeur entre 0.25 et 24h." plutôt que "Oups, quelque chose s'est mal passé."
- Les confirmations de succès sont **courtes** : "Saisie enregistrée." pas "Votre saisie a bien été enregistrée avec succès !"

---

## Annonces de mise à jour (MAJ importantes)

Quand une mise à jour significative est développée (nouvelle fonctionnalité, changement d'interface, correction majeure), **proposer systématiquement un message d'annonce** à insérer via l'API `POST /api/updates`.

Le message (`message` field) doit être en **HTML** et respecter les codes visuels de MySifa :

```html
<!-- Template annonce MAJ — à adapter -->
<div style="font-size:13px;line-height:1.7;color:var(--text2)">
  <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">
    Mise à jour — v0.X.Y
  </div>

  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;
       text-transform:uppercase;letter-spacing:.5px">Nouveautés</div>
  <ul style="margin:0 0 14px 0;padding-left:18px">
    <li style="margin-bottom:5px">Description précise et factuelle de la nouveauté.</li>
    <li style="margin-bottom:5px">Autre nouveauté.</li>
  </ul>

  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;
       text-transform:uppercase;letter-spacing:.5px">Corrections</div>
  <ul style="margin:0 0 14px 0;padding-left:18px">
    <li style="margin-bottom:5px">Correction décrite sobrement.</li>
  </ul>

  <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);
       font-size:11px;color:var(--muted);line-height:1.6">
    Dans l'optique d'améliorer constamment l'outil, vos retours sont les bienvenus.<br>
    Merci de votre confiance.<br>
    <span style="color:var(--text2);font-weight:600">Eugène</span>
  </div>
</div>
```

**Champs à renseigner :**
- `scope` : identifiant de la page concernée (`planning`, `prod`, `stock`, `global`, etc.)
- `titre` : titre court en style release notes, ex. `"Planning — Filtres et performances"`
- `message` : HTML ci-dessus
- `active` : `true`

---

## Migrations de base de données — une migration = un fichier

**Règle depuis le 3 août 2026 : toute NOUVELLE migration va dans un fichier de
`app/core/migrations/`, jamais dans `_migrate()`.** Les migrations historiques
numérotées 1 à 225 restent dans `app/core/database.py` et n'ont pas à bouger.

### Pourquoi ce changement

Deux chantiers menés en parallèle (deux conversations Claude, ou Claude + Cursor)
se marchaient systématiquement dessus :

1. **Collision de numéros.** Chacun choisit le même numéro de son côté. Après
   fusion, la seconde migration ne s'exécute **jamais** : son garde-fou voit le
   numéro de l'autre déjà enregistré. Cas réel : le doublon v195 — le bloc
   `imprimantes_type_connexion_windows_local` est resté muet pendant des mois sur
   toutes les bases où `backfill_libres_usage_count` était passé avant lui.
2. **Fichier partagé.** `database.py` fait ~9 000 lignes. Deux sessions qui y
   écrivent s'écrasent mutuellement, et git n'a aucun moyen de trancher. Cas réel
   (3 août 2026) : une migration entière effacée entre deux tours de
   conversation, découverte par une erreur 500 en production.

### Écrire une migration

Créer `app/core/migrations/AAAA_MM_JJ_sujet.py` :

```python
"""
Ce que fait la migration, et pourquoi.
"""

NOM = "sujet_explicite"              # clé unique et DÉFINITIVE
DEPEND = ["autre_migration"]         # facultatif — à passer avant celle-ci

def appliquer(conn):
    conn.execute("ALTER TABLE ... ")
    conn.commit()
```

- **`NOM` est la clé.** Il ne change JAMAIS une fois la migration partie en
  production — c'est lui qui dit si elle est déjà passée. Deux chantiers ne
  choisiront pas le même nom s'ils décrivent ce qu'ils font.
- **Le préfixe de date ne sert qu'à ordonner par défaut.** Ce n'est pas une clé :
  deux migrations datées du même jour ne se gênent pas.
- **`DEPEND` dès qu'une migration en attend une autre** (elle touche une table que
  l'autre crée). Ne jamais compter sur l'ordre alphabétique : le chantier voisin
  ne contrôle pas ton nom de fichier, et toi pas le sien.
- **Toujours rejouable.** `CREATE TABLE IF NOT EXISTS`, test de présence de
  colonne avant `ALTER TABLE`, `INSERT OR IGNORE` pour les seeds. Une migration
  doit pouvoir tourner deux fois sans rien casser.
- **Un `print()` de bilan** en fin de migration quand elle transforme des données
  (`f"[MySifa] migration X : {n} ligne(s) reprise(s)."`) — c'est ce qui permet de
  vérifier au démarrage que la reprise a bien eu lieu.

### Ce que fait le lanceur

`app/core/migrations/__init__.py`, appelé en fin de `_migrate()` :

- suit les migrations passées dans `schema_migrations_fichiers` (clé = `nom`) ;
- lit **aussi** l'ancienne table `schema_migrations` : une migration déplacée
  depuis `database.py` y est déjà enregistrée sous le même nom et n'est donc pas
  rejouée sur les bases existantes ;
- refuse de démarrer si deux fichiers portent le même `NOM`, si un `DEPEND` pointe
  vers une migration inexistante, ou si les dépendances tournent en rond.

Test associé : `python3 tests/test_migrations_fichiers.py` (application, absence
de rejeu, reprise d'une base migrée par l'ancien mécanisme, respect de `DEPEND`).

### Vérifier l'état sans ouvrir la base

**Paramètres → Promouvoir → Déployer → « Santé du dépôt »** (`GET /api/deploiement/sante`,
rendu par `static/mysifa_promote.js`) affiche, pour l'instance qui répond :

- une **note sur 100** (lettre A→E) en tête de panneau, avec le détail des points
  perdus par critère. Elle part de 100 et retire : 15 pts par numéro de migration
  en double (plafond 30), 8 pts par migration en attente (plafond 20), 1 pt par
  branche fusionnée dormante au-delà de 5 tolérées (plafond 25), 20 pts pour un
  verrou git, 2 pts par fichier modifié non commité (plafond 10), 0,2 pt par
  fichier non suivi (plafond 10). Les poids traduisent le risque réel : un
  doublon de migration est un piège silencieux, une branche morte n'est que du
  bruit. Le calcul vit dans `_note_sante()` (`app/routers/settings.py`) ;
- les migrations **appliquées** (numérotées et fichiers confondus) et celles
  **présentes dans le code mais pas encore jouées** ;
- les **numéros historiques en double** — deux migrations sur le même numéro : la
  seconde ne s'exécute jamais, c'est un piège silencieux ;
- les **branches distantes**, leur âge et leur état de fusion dans `staging`, avec
  un marqueur « à supprimer » pour celles fusionnées et dormantes depuis 15 jours ;
- la **propreté du dossier de travail** : fichiers modifiés, non suivis, verrou
  `.git/index.lock`.

La vue est en **consultation seule** : elle ne lance que des commandes git en
lecture (`for-each-ref`, `status`, `branch --merged`). Le ménage se fait au
terminal, avec `scripts/nettoyer_branches.sh` — simulation par défaut,
`--appliquer` pour supprimer, `--local` pour purger aussi les branches locales.
Il protège `main`, `staging` et la branche courante, ne propose jamais une
branche non fusionnée, et écrit le SHA de chaque branche supprimée dans
`.git/nettoyage-branches-<date>.txt` (restauration :
`git push origin <sha>:refs/heads/<nom>`). Le panneau propose la même commande
prête à copier. Test associé : `python3 tests/test_deploiement_sante.py`.

### Ce qu'il ne faut plus faire

- ❌ Ajouter un `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N")` dans `_migrate()`
- ❌ Choisir un numéro de migration, même « libre » sur `origin/staging`
- ❌ Renuméroter une migration déjà partie en production (le `NOM` la remplace)

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

## OF et fiches techniques — qui a le dernier mot

Deux sources écrivent dans `of_imports` et `fiches_techniques` : le pont Access
(`scripts/access_sync_of.py`, `scripts/access_sync_fiches.py` → `/api/bridge/*`)
et les humains (import d'un PDF d'OF, correction dans une modale MySifa). Le
déstockage de production lit ces deux tables. Un arbitrage faux ne se voit pas :
il sort à l'inventaire, des semaines plus tard.

**Deux règles, arbitrées au niveau du CHAMP.**

1. Le document le plus récent fait foi.
2. Sauf sur une valeur saisie par un humain.

Au niveau du document ces deux règles se contredisent, et c'est ce qui donnait
deux comportements opposés selon la table (avant le 7 août 2026) : un OF portant
un PDF était gelé en entier — une quantité corrigée dans Access n'arrivait
jamais — tandis qu'une fiche technique était intégralement écrasée à chaque
sync, correction atelier comprise, sans trace. Au niveau du champ, les deux
règles tiennent ensemble.

Tout passe désormais par **`app/services/documents_verite.py`**. Aucun autre
chemin ne doit écrire dans ces deux tables.

- `appliquer_maj(...)` — écriture arbitrée. `proteger_manuels` refuse
  d'écraser une colonne listée dans `champs_manuels` (JSON) et journalise le
  refus ; `marquer_manuels` ajoute les colonnes écrites à cette liste ;
  `seulement_vides` reproduit `enrich_if_exists` ; `autoriser_effacement` n'est
  vrai que pour une saisie humaine — un `None` venu d'Access est presque
  toujours une jointure vide, pas une décision.
- `constater_remplacement(...)` — pour l'import d'un PDF d'OF, qui réécrit la
  ligne d'un bloc. On n'arbitre pas ce geste, on en tire les conséquences.

**La validation se périme.** Toute écriture sur un champ de
`CHAMPS_CALCUL_OF` / `CHAMPS_CALCUL_FT` remet `valide` à 0, efface `valide_par`
et renseigne `invalide_motif`. Sans cela le verrou de déstockage atteste d'une
relecture qui a bien eu lieu — mais pas sur les valeurs qui serviront au calcul.
Corriger n'est pas relire : une correction humaine dévalide au même titre
qu'une modification Access.

`reference` et `machine` sont dans les champs de calcul bien qu'ils ne soient
pas des quantités : ce sont eux qui décident QUELLE fiche technique est
rapprochée du dossier.

**Tout est journalisé** dans `documents_valeurs_historique` (avant, après,
origine, auteur, `etait_valide`, `refuse`). Un mouvement de déstockage porte en
plus `mp_mouvements.of_import_id` et `.fiche_id` : le dossier seul ne suffit
pas, il change d'OF et une fiche se modifie.

**Ce qu'il ne faut pas faire**

- ❌ `UPDATE of_imports SET ...` ou `UPDATE fiches_techniques SET ...` en direct
- ❌ Rendre `valide` modifiable par un endpoint de mise à jour de données
- ❌ Ignorer un conflit en silence : un désaccord Access / MySifa se remonte

**Vérifier l'état d'une base**

```bash
python scripts/audit_documents_validation.py --db data/production.db
```

Sections 3 et 4 du rapport doivent rester vides. Une ligne en section 3 (document
validé malgré un changement postérieur) signale un chemin d'écriture qui
court-circuite le service.

Tests : `python3 tests/test_documents_verite.py` (arbitrage, péremption,
journal) et `python3 tests/test_besoins_verrou_documents.py` (SQL réelle de
Besoins matières + blocage du déstockage).

---

## Nombre de fronts — `outil1_nb_front`, jamais `mod_nb_front`

Le nombre de fronts est au **dénominateur** du métrage :

    métrage = qte_étiquettes ÷ nb_fronts × mod_longueur ÷ 1000

S'y tromper d'un facteur 18 multiplie le besoin en frontal par 18.

**Constat du 7 août 2026, base de production :** `mod_nb_front` vaut 1 sur
**878 fiches sur 909**. Ce n'est pas une valeur, c'est un champ que personne ne
remplit. Le vrai nombre de fronts est `outil1_nb_front` — les poses de l'outil
de découpe — confirmé par la géométrie sur **868 fiches sur 909**.

Conséquence avant correction : les 585 OF sans métrage (sur 745) passaient par
le repli géométrique et sortaient un besoin surestimé d'un facteur égal au vrai
nombre de fronts. Un dossier est ressorti à **55 823 km de frontal**, dix fois
le total d'un mois entier.

`app/services/coherence_fiche.py` porte les deux fonctions :

- `nb_fronts(ft, laize_of)` — la valeur à utiliser et sa provenance. Ordre :
  `outil1_nb_front`, puis `mod_nb_front` s'il est > 1, puis la géométrie.
- `controler(ft, laize_of)` — vérifie que la fiche boucle, et chiffre le
  facteur d'erreur.

**L'identité qui rend le contrôle possible**, et qui ne demande aucune source
extérieure :

    nb_fronts ≈ laize_bobine ÷ laize_module

La laize de l'OF prime sur celle de la fiche : c'est la bobine réellement
montée. `eti_laize` est la largeur de l'ÉTIQUETTE, jamais celle de la bobine —
les confondre redonne un nombre de fronts de 1.

`GET /api/stock/besoins-matieres/fiches-incoherentes` liste les fiches à
corriger, classées par facteur d'erreur puis par nombre de dossiers concernés.

**On ne corrige jamais d'office.** Une fiche fausse se répare dans Access, à la
source. Compenser en silence à chaque lecture cacherait le problème pendant que
les commandes continuent de partir de travers.

Test : `python3 tests/test_coherence_fiche.py` (fiches réelles relevées en
production).

---

## Prévision des besoins matières — pourquoi on photographie le carnet

**Ne pas supprimer `carnet_snapshots` sous prétexte qu'elle ne sert à rien.**
Elle ne servira à rien jusqu'à novembre 2026, et c'est exactement pourquoi elle
existe depuis août.

Prévoir la consommation matière à 3-4 mois ne consiste pas à extrapoler une
courbe. Sur cet horizon, une partie du besoin est déjà connue — les dossiers au
planning livrés dans la fenêtre, que Besoins matières chiffre exactement. Ce
qui reste à estimer, c'est le **remplissage** :

    prévision(M+k) = besoin_connu(M+k) ÷ p(k)

où p(k) est la part du volume final déjà visible k mois à l'avance.

p(k) se mesure — mais seulement si l'on sait ce que le carnet contenait à une
date passée. Or `planning_entries` ne garde que le présent : au 7 août 2026,
ses 295 dossiers avaient TOUS été créés dans les quatre mois précédents. Un
dossier terminé quitte la fenêtre et emporte la trace de ce qu'il pesait.

Diagnostic reproductible :

```bash
python scripts/diag_previsions_matieres.py --db data/production.db
```

D'où `app/services/carnet_snapshot.py` : une photo par jour du besoin calculé,
par mois de livraison et par matière. Déclenchée par la consultation de Besoins
matières (l'écran est ouvert chaque jour ouvré), idempotente, best-effort — son
échec ne doit jamais empêcher l'affichage.

Deux points de conception à ne pas défaire :

- **On stocke le besoin CALCULÉ, pas les dossiers.** C'est la grandeur à
  prédire, et elle survit à la suppression du dossier qui l'a produite.
- **`nb_incalculables` compte à part les besoins non chiffrables.** Un carnet
  dont les OF n'ont pas de métrage ressemble trait pour trait à un carnet vide ;
  sans ce compteur on calibrerait sur une pénurie de données en croyant
  calibrer sur une pénurie de commandes.

`GET /api/stock/besoins-matieres/carnet/couverture` dit où en est
l'accumulation et quels horizons sont calibrables. Tant que
`horizons_calibrables` est vide, aucun modèle fondé sur le remplissage n'est
honnête — l'écran doit le dire plutôt qu'afficher un chiffre.

L'historique antérieur (2022 → 2026) n'est pas dans la base : il vit dans le
classeur « Point Besoin des commandes ». Deux feuilles complémentaires dans le
temps — « analyse Eugene » (2022 et 2026) et « Controle dossier » (2023-09 à
2025-12) — à dédoublonner par numéro d'OF, avec deux définitions différentes du
métrage (théorique d'un côté, utilisé de l'autre, plus une colonne
`Surconsommation`).

Test : `python3 tests/test_carnet_snapshot.py`.

---

## RVGI — la base de l'ERP, en lecture seule

RVGI est l'ERP de SIFA. Sa base `sifa_cs` tourne sur un serveur HFSQL
Client/Serveur (PC SOFT / WinDev) : `192.168.100.199:4949`, encodage
ISO-8859-1, 183 tables utiles. On l'atteint par le provider OLE DB
`PCSoft.HFSQL` — celui qu'Excel utilise déjà, donc déjà installé sur les postes,
appelable en COM depuis PowerShell ou Python sans rien installer.

**Le détail vit dans `docs/rvgi/data_rvgi.md`** : carte des domaines, tables
qui comptent avec le sens de leurs colonnes, clés de jointure, gisements
identifiés. Le relevé brut est dans `docs/rvgi/rapport_rvgi.md` et
`docs/rvgi/schema_rvgi.json`, régénérés par
`scripts/inventaire_rvgi.ps1` (lecture seule, aucune écriture sur l'ERP).

**Règles absolues**

- **RVGI est une source, jamais une destination.** Aucun code MySifa n'écrit
  dans `sifa_cs`. La connexion se fait avec un compte de lecture seule dédié,
  pour que ce soit structurellement impossible et pas seulement conventionnel.
- **`corbeille = 0`, partout.** RVGI ne supprime pas, il marque. Toute autre
  valeur — `1`, `9`, mais aussi `2.1` ou `18.2` — est une ligne supprimée dont
  les valeurs ne veulent plus rien dire. Plus d'une ligne sur deux est dans ce
  cas (`mat_mat` : 1 536 vivantes sur 7 521). Le filtre porte sur les
  comptages, les agrégats, les extraits, et **des deux côtés d'une jointure**.
- **Le VPS ne voit pas le LAN.** `192.168.100.x` n'est pas joignable depuis
  `mysifa.com`. Toute synchro est un **push** depuis un poste du réseau vers
  `/api/bridge/*` avec une clé `X-Api-Key`, planifié côté Windows — le motif de
  `scripts/access_sync_of.py`. Jamais un pull depuis MySifa.
- **Trois colonnes à ne jamais lire** : `gen_sala.mdp`, `fic_clt.inftpmdp`,
  `fic_fou.inftpmdp` contiennent des mots de passe en clair. Pas de `SELECT *`
  paresseux sur ces tables, pas de journalisation de ligne entière, pas de
  recopie dans MySifa.

**Les deux clés**

- **`code1` / `code2` — l'article.** `code1` = numéro du client, `code2` = rang
  de l'article chez lui. `_erp_reference()` dans `app/routers/reconciliation.py`
  construit déjà `890/0112` à partir de ce couple : l'appeler, ne pas la
  réécrire. `code3` porte la laize sur les matières et les mouvements.
- **`cde_entete.numero` en `99xxxxx` — la commande**, soit le numéro d'OF que
  `_OF_RACINE_RE` reconnaît déjà. Il se reporte dans `liv_ligne.numcde`,
  `vte_ligne.livno`, `stk_hist.numcde`, `cdi_ligne.nocde`. Les autres domaines
  ont leur propre numérotation : **ne jamais joindre deux domaines sur `numero`
  seul**, toujours par la colonne de report explicite.

**Deux pièges de lecture qui ont déjà faussé un relevé**

- **Les tableaux WinDev sont dépilés en colonnes.** `mat_mat` déclare 76
  colonnes logiques et en expose 483 : `pafou1`, `pafou1_2`… Là où MySifa
  aurait une table fille, RVGI a des colonnes numérotées. Les replier vers un
  modèle relationnel est le gros du travail de mapping.
- **Des sentinelles à la place des nuls** : `30/11/1999` pour une date vide,
  `4710000000` pour un compte absent, `99999999999.99` pour « pas de maximum »,
  `0` sur un prix pour « non renseigné » — jamais « gratuit ».

**Le module production de RVGI est abandonné**

`cdi_*` et `gpr_gpr` / `gpr_mat` n'ont plus une écriture depuis avril 2026 :
SIFA a cessé de les alimenter parce que le module ne convenait pas, et c'est ce
qui a motivé la création de MySifa. Ces tables n'ont plus qu'une valeur
d'historique — ne rien construire dessus, ne pas les présenter comme un état
courant. `gpr_ff` (fiches de fabrication) fait exception et reste maintenue.

Conséquence pour la traçabilité : le lien dossier ↔ lot matière que portait
`gpr_mat.reflot` n'est plus alimenté côté ERP et doit exister dans MySifa.
Côté entrée, `lif_ligne.lot` et `stm_hist.lot` restent vivants.

---

## ERP RVGI — l'app `/erp` et son miroir

RVGI est l'ERP de SIFA (base HFSQL `sifa_cs`, serveur `192.168.100.199:4949`).
MySifa en expose une lecture dans l'app `/erp`, ouverte à **`ROLES_ADMIN`** —
direction, services administration et super administrateur. La documentation de la base elle-même est dans
`docs/rvgi/data_rvgi.md` — la lire avant de toucher à quoi que ce soit ici.

### MyERP est un MIROIR — rien d'autre

**Sauf contre-indication explicite d'Eugène, on ne crée dans `/erp` RIEN qui ne
soit pas un miroir de l'ERP** — ni donnée, ni outil de gestion.

Cela veut dire, concrètement :

- **Pas d'écran qui ne vienne pas du catalogue.** Les domaines et les écrans du
  menu sont ceux de `erp_catalogue.py`, qui décrit les tables de RVGI. On
  n'ajoute pas un domaine côté client, on n'invente pas d'écran de travail.
- **Pas de liste de tâches, pas de tableau de bord, pas d'outil de contrôle.**
  Une liste « à traiter », une comparaison entre les deux bases, un suivi
  d'écarts : tout cela est du travail MySifa. Sa place est dans l'app métier
  concernée — le monitoring de stock dans MyStock, les dossiers à rattacher
  dans MyProd, les départs dans MyExpé. Pas ici.
- **Pas de données saisies dans MyERP.** L'écran lit, il n'enregistre pas.

Ce qui est autorisé, parce que ça reste de la lecture posée sur du RVGI :
afficher, à côté d'une ligne de l'ERP, ce que MySifa en a fait — la colonne
« Dossier de fab » sur les commandes en est l'exemple, demandée explicitement.
La règle porte sur la création d'écrans et d'outils, pas sur l'enrichissement
d'une ligne existante.

**Historique de la règle.** Deux écrans avaient été ajoutés sans être demandés :
« À rattacher » (les dossiers MySifa sans pièce RVGI) et « Stocks RVGI ↔
MySifa ». Ils ont été retirés le 26/08/2026. Le premier n'avait rien à faire
dans un miroir ; le second existait déjà, à sa vraie place, dans le monitoring
de MyStock. En cas de doute sur un ajout à `/erp` : demander.

### Les trois règles absolues

1. **Le sens d'écriture est unique.** RVGI est la source, MySifa lit. Aucun code
   MySifa n'écrit dans l'ERP. Côté miroir, ce n'est pas une consigne mais un
   fait : `app/services/erp_mirror.py` ouvre la base en `mode=ro`, une écriture
   lève `attempt to write a readonly database`.
2. **`corbeille = 0`, partout.** RVGI ne supprime pas, il marque. Plus d'une
   ligne sur deux est morte (`fic_art` : 7 678 vivantes sur 41 389). Le filtre
   est appliqué à l'export, donc le miroir ne contient que du vivant — mais
   toute requête écrite directement contre l'ERP doit le porter, des deux côtés
   d'une jointure.
3. **Trois colonnes ne sont JAMAIS lues** : `gen_sala.mdp` et `pasmail`,
   `fic_clt.inftpmdp`, `fic_fou.inftpmdp` — mots de passe en clair côté ERP.
   `scripts/export_rvgi_csv.ps1` les retire de la liste des colonnes **avant**
   la requête (`$COLS_INTERDITES`) : leur valeur n'entre jamais en mémoire.
   Ne pas « simplifier » en `SELECT *`.

### Où vit quoi

| Fichier | Rôle |
|---|---|
| `scripts/export_rvgi_csv.ps1` | ERP → CSV, lecture seule, 61 tables. Lit le `.env`. |
| `scripts/import_rvgi_csv.py` | CSV → `data/erp_mirror.db`. stdlib seule, aucun import de `app.*`. |
| `scripts/sync_rvgi.ps1` | Export + zip + envoi HTTPS. Tâche planifiée, 5 h et 12 h 30. |
| `app/services/erp_mirror.py` | Connexion `mode=ro`, moteur de liste générique, sentinelles. |
| `app/services/erp_catalogue.py` | Les 27 écrans, en déclaratif. |
| `app/routers/erp.py` | API lecture seule, `ROLES_ADMIN`. Aucun verbe d'écriture. |
| `app/web/erp_page.py` | La page `/erp`. |
| `app/routers/api_bridge.py` | `POST /api/bridge/erp/miroir` — réception des exports. |
| `scripts/audit_liens_erp.py` | Vérifie les 59 liens du catalogue contre le miroir. |

Le miroir vit dans **son propre fichier** (`ERP_MIRROR_DB`, défaut
`data/erp_mirror.db`), pas dans `production.db`. C'est délibéré : il est
entièrement reconstructible depuis l'ERP, donc il n'a rien à faire dans les
backups de production ni dans les migrations, et il se purge d'un `rm`. Il n'est
pas dans git. Chaque instance a le sien — v1 et la prod ne le partagent pas.

### Ajouter un écran

On n'écrit pas de page : on ajoute une entrée à `ECRANS` dans
`app/services/erp_catalogue.py` — table, alias, jointures, colonnes, filtres,
groupes du panneau de détail. Le moteur fait le reste.

`adapter_ecran()` élague ensuite l'écran de ce que le miroir n'a pas : une
colonne absente disparaît au lieu de faire tomber la requête, un écran dont la
table manque n'est pas proposé. C'est ce qui permet d'écrire un catalogue à
partir du relevé sans avoir vu les données.

### Ajouter un lien entre écrans

`LIENS` (même fichier) déclare, écran par écran, les pièces rattachées :
`{"label", "ecran", "sur": {"<colonne cible>": "<champ source>"}}`. Le front
n'envoie jamais un nom de colonne — il envoie l'écran d'origine, l'identifiant
de la ligne et le **rang** du lien, et le serveur reconstruit la condition
depuis le catalogue. Ne pas réordonner `LIENS` sans y penser : le rang, c'est
l'index dans la liste.

**Après tout ajout ou modification, lancer `python scripts/audit_liens_erp.py`.**
Un lien branché sur une colonne que RVGI ne remplit jamais ne remonte rien et
ne le dit pas — le 25/08/2026, trois liens étaient dans ce cas : `col_ligne.numcde`
vaut 0 sur les 257 lignes de colisage, et `lot` est NULL partout dans
`lif_ligne` comme dans `stm_hist`. Le script les trouve en quelques secondes.

Deux pièges de typage, tous deux traités, à ne pas défaire :

- `code1` / `code2` / `code3` sont **toujours** stockés en TEXT. Sinon `code1`
  vaut `890` (INTEGER) dans `cde_ligne` et `« FR »` (TEXT) dans `fic_art`, et la
  jointure ne remonte rien — sans erreur.
- Les valeurs sentinelles de RVGI (`30/11/1999` = date vide, `99999999999.99` =
  pas de maximum, `0` sur un prix = non renseigné, `255` sur un octet = non
  renseigné) sont **conservées en base** et neutralisées à la lecture, dans
  `nettoyer()`. Corriger en base ferait mentir le miroir sur sa source.

### La synchro

Le VPS ne voit pas `192.168.100.x` : la synchro tourne sur une machine du
**réseau SIFA**, jamais sur le serveur. Elle exporte, zippe (~20 Mo pour 110 Mo
de CSV), et pousse vers chaque instance ; c'est le serveur qui reconstruit le
miroir en tâche de fond. La machine du LAN n'a donc besoin ni de Python ni de
SQLite — mais elle doit avoir le provider OLE DB `PCSoft.HFSQL` (celui du client
RVGI ou d'Excel).

Trois prérequis côté serveur, faciles à oublier :

- `client_max_body_size 64M;` dans les vhosts nginx — le défaut d'1 Mo rejette
  l'archive ;
- une clé API de portée `erp:write` **par instance** : v1 et la prod ont chacune
  leur base, et le resync nocturne de v1 écrase ses clés avec celles de prod. La
  clé à conserver est donc celle créée en prod. `MYSIFA_SYNC_URLS` accepte
  `url|clé` pour en donner une par cible ;
- `MYSIFA_SYNC_URLS` et `MYSIFA_API_KEY` dans le `.env` de la machine du LAN —
  le Planificateur de tâches Windows n'hérite d'aucune variable de terminal.

### Deux détails d'implémentation

**Jamais de WAL sur le miroir.** Une base ouverte en `mode=ro` ne peut pas créer
les fichiers `-wal` / `-shm` dont WAL a besoin, et certains montages réseau la
refusent carrément (`disk I/O error`). L'import construit un `.tmp` puis fait un
`os.replace` : l'app ne voit jamais un miroir à moitié construit, et un import
raté laisse le précédent en place.

**La disposition des colonnes** (ordre, colonnes verrouillées) est mémorisée
dans le `localStorage` du navigateur, par écran. C'est un confort d'affichage,
pas une donnée : elle ne suit pas l'utilisateur d'un poste à l'autre. Si ça doit
changer, c'est une table de préférences côté serveur.

---

## Points d'attention critiques

**Base de données**
- `duree_heures` est `REAL` — toujours `parseFloat()` côté JS
- `date_operation` stocké en `"%Y-%m-%dT%H:%M:%S"` heure Paris (pas de timezone dans la chaîne)
- `TERMINE_KEEP = 2` : les 2 derniers dossiers terminés restent visibles dans la liste
- Toute nouvelle colonne doit être ajoutée via une migration fichier dans `app/core/migrations/`

**Frontend**
- La scroll position doit être préservée après tout `renderEntries()` ou drag & drop
- `_autoScrollKey` est basé uniquement sur l'ID du dossier `en_cours`
- Les slots timeline sont positionnés en absolu sur les jours travaillés uniquement (jours off filtrés)
- Ne jamais reconstruire le DOM d'une modal ouverte pendant un refresh automatique — vérifier `document.getElementById("mroot").firstElementChild` avant tout re-render global

**Routing**
- `frontend/`, `routers/` et `database.py` à la racine sont des **shims** — ne pas y ajouter de logique
- **Script lancé à la main : importer `database` AVANT tout `app.*`.** Le shim
  `database.py` fait `from app.core.database import *`. Si un script importe
  `app.core.database` en premier, ce module exécute les migrations au
  chargement, ce qui réimporte le shim alors qu'il est à mi-parcours : le shim
  se retrouve sans `get_db` et Python garde cette version cassée en cache.
  Symptôme : `ImportError: cannot import name 'get_db' from 'database'` sur un
  code qui tourne parfaitement dans l'application. `main.py` n'est jamais
  touché parce qu'il charge le shim en premier.

  ```python
  import sys; sys.path.insert(0, '.')
  import database                      # d'abord, toujours
  from database import get_db
  from app.services.mon_service import ma_fonction
  ```
- Tout nouveau router doit être créé dans `app/routers/` et enregistré dans `main.py`
- Toute nouvelle page doit être créée dans `app/web/` et enregistrée dans `main.py`

---

## Outils — écriture de fichiers (drive réseau Windows)

Le dépôt local Windows (`C:\Users\eleconte\Documents\GitHub\MySifa`) et l'ancien backup
(`U:\ELECONTE\production-saas`, à ignorer) sont accessibles depuis l'IA mais via
un drive réseau qui **tronque silencieusement les écritures de gros fichiers**.

Observé concrètement (juin 2026, phase 2 du refactor MyProd) :
- Outil `Edit` (search/replace ciblé) : 3 cas de troncature constatés
  (`prod_page.py` tronqué à 818/4755 octets, `mysifa_prod_core.css` tronqué à
  `var(--bor`, idem sur d'autres fichiers > 50 Ko). Le `Read` postérieur affiche
  pourtant le contenu attendu — c'est le disque qui ne l'a pas.
- Outil `Write` (réécriture complète) : même symptôme sur les fichiers > ~2 Ko.
- Padding `\x00` parfois ajouté en fin de fichier après une réduction de taille
  (837 octets nuls observés sur `app/web/html.py`).

**Règle pratique** : pour toute modification de fichier > ~1 Ko (CSS, JS, gros
modules Python), **utiliser le shell sandbox bash** plutôt que `Edit` / `Write` :

```bash
# Réécriture complète (préférée pour les gros fichiers / refactor)
cat > /sessions/<session>/mnt/MySifa/static/foo.css << 'CSSEOF'
...contenu...
CSSEOF

# Append (très fiable, pas de troncature possible)
cat >> /sessions/<session>/mnt/MySifa/static/foo.css << 'CSSEOF'
/* nouveau bloc */
.foo { ... }
CSSEOF

# Modification chirurgicale via Python (sed reste OK aussi)
python3 << 'PYEOF'
p = '/sessions/<session>/mnt/MySifa/foo.py'
src = open(p, encoding='utf-8').read()
src = src.replace('ancien', 'nouveau')
open(p, 'w', encoding='utf-8', newline='\n').write(src)
PYEOF
```

`Edit` et `Write` restent acceptables pour les **petits fichiers de config**
(< 1 Ko : `.env`, snippets dans `config.py`, etc.).

**Conserver les fins de ligne du fichier d'origine.** `.gitattributes` force le
LF sur `.sh`, `.py`, `.js` et `.css`, mais **pas sur les `.md`** : `CLAUDE.md`
est en CRLF dans le dépôt. Un script Python qui réécrit un fichier avec
`newline='\n'` convertit tout en LF et produit un diff de la totalité du
fichier — 1 956 suppressions pour trois paragraphes ajoutés, illisible en
review et prêt à entrer en conflit avec n'importe quel autre chantier. Lire et
réécrire avec `newline=''` (Python conserve alors les fins de ligne telles
quelles), et vérifier avant de commiter :

```bash
git --no-optional-locks diff --numstat <fichier>
```

Un nombre de suppressions proche du nombre total de lignes = conversion
accidentelle, pas une vraie modification.

**Vérification systématique après toute modif** :
- `python3 -c "import ast; ast.parse(open('<path>').read())"` pour le Python
- `node --check <path>` pour le JS
- `python3 -c "print(open('<path>','rb').read().count(b'\x00'))"` doit renvoyer 0
- Pour les CSS, compter la balance des `{` / `}` :
  ```python
  import re
  css = open(p).read()
  no_c = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
  print(no_c.count('{'), no_c.count('}'))
  ```

Une troncature passe les vérifs Python `ast` si elle coupe entre deux blocs,
donc **toujours** afficher `tail -5 <path>` pour confirmer que le fichier se
termine bien par ce qu'on attend.

### git : la troncature frappe aussi les commandes git côté Windows

Observé (juillet 2026, split rôle admin + ack NC) : le même drive Windows tronque
les fichiers écrits par **git** lui-même. Concrètement, pendant un `git merge`,
`git checkout <sha> -- <path>`, `git pull`, etc., un fichier > ~5 000 lignes
peut se retrouver coupé au milieu — marqueurs de conflit `<<<<<<<` sans jamais
de `=======` ni `>>>>>>>`, ou fichier légitime tronqué à ~6 100 lignes au lieu
de 6 300. Le fichier tronqué casse ensuite l'AST Python, le merge reste bloqué,
et re-taper `git checkout` retronque à nouveau.

**Quand ça arrive** :
1. Ne pas insister avec Windows — chaque tentative `git checkout` / `git reset`
   retronque le même fichier.
2. **Basculer côté VM Linux** (shell sandbox) : les écritures via `cat > <path>`
   ou Python `open(p,'w').write(...)` sur le mount ne subissent pas la troncature.
3. Pattern qui marche : extraire le vrai contenu depuis les objets git
   (`git show <sha>:<path> > /tmp/…`) → manipuler dans `/tmp` → écrire dans le
   workspace via `cat /tmp/foo.py > <path>` → vérifier avec `wc -l` et
   `python3 -c "import ast; ast.parse(...)"`.
4. Le `.git/index.lock` qui reste après un `git merge --abort` interrompu
   ne peut pas être supprimé depuis Linux (Operation not permitted sur le
   mount) : demander à l'utilisateur de le supprimer depuis PowerShell avec
   `Remove-Item .git\index.lock -Force`.

**Conflits de migration** :
- Le problème est réglé à la source : une nouvelle migration est un fichier de
  `app/core/migrations/` identifié par son `NOM`, plus par un numéro. Deux
  chantiers parallèles ne se disputent ni un numéro, ni ce fichier.
- Si un fichier `database.py` en conflit contient encore une migration numérotée
  non partie en production, la déplacer vers un fichier plutôt que la renuméroter.

**Toucher un fichier de `static/` oblige à bumper son `?v=`.** Le middleware
`no_cache_planning` (`main.py`) sert tout `/static/` avec
`Cache-Control: public, max-age=86400` : pendant 24 h, le navigateur d'un
visiteur déjà venu ne redemande RIEN. La seule invalidation est le querystring
de version dans la balise qui l'inclut. Trois conventions coexistent :

| Bust | Fichiers | Se périme quand |
|---|---|---|
| `?v=<n>` figé | `mysifa_promote.js?v=4`, `chat_widget.js?v=11`… | **jamais** — à incrémenter à la main |
| `?v=__V_LABEL__` | `mysifa_prod_core.css` | `APP_VERSION` change |
| `?v=__ASSETS__` | `pricing_app.css/js` | le contenu du fichier change |

Modifier un fichier à bust figé **sans incrémenter le nombre** produit le pire
symptôme qui soit : « j'ai poussé, c'est déployé, et je vois toujours l'ancien ».
Vérifier avant de commiter :

```bash
grep -rn "<le fichier modifié>" --include=*.py app/web/
```

Corollaire : un fichier en `?v=__V_LABEL__` ne se rafraîchit que si `APP_VERSION`
bouge. Refuser le bump de version, c'est accepter que ce fichier reste périmé
24 h chez chaque visiteur.

**Jamais de commentaire `#` en fin de ligne dans un bloc à coller** :

Le terminal d'Eugène sur Mac est **zsh en interactif**, où l'option
`interactive_comments` est désactivée par défaut : un `#` n'ouvre PAS un
commentaire, il est passé tel quel à la commande. Un bloc du type
`./script.sh   # simulation` sort donc `Option inconnue : #`. Les annotations se
mettent **au-dessus** de la commande, en texte hors du bloc, jamais à droite.
Même prudence côté PowerShell, où le commentaire est bien `#` mais où le
copier-coller multi-lignes exécute chaque ligne séparément.

**`git update-index --chmod=+x` ne marche que sur un fichier déjà suivi** :
faire `git add <fichier>` d'abord, sinon git répond
`cannot add to the index - missing --add option?`.

**PowerShell vs bash** :
- Les blocs bash du CLAUDE.md (`if [[ ]]`, `&& \`, `if/then/fi`) ne fonctionnent
  PAS en PowerShell — le terminal d'Eugène. Pour les scripts multi-étapes en
  interactif, envelopper dans `& { … }` avec `if ($LASTEXITCODE -ne 0) { return }`
  après chaque commande. Le `return` sort du scriptblock sans fermer la fenêtre
  (contrairement à `exit 1`).

### git depuis le mount Linux : JAMAIS de commande qui écrit l'index

Observé (29 juillet 2026, session étiquettes bobines). Symptôme côté Eugène :

```
fatal: Unable to create '.../.git/index.lock': File exists.
Another git process seems to be running in this repository...
```

…avec 7 `git.exe` visibles dans `Get-Process`, et un `.git/index.lock` de
**0 octet vieux de deux heures**. Diagnostic initial erroné : « Cursor a planté ».
La vraie cause était l'IA elle-même.

**Le mécanisme** : `git status` et `git diff` rafraîchissent l'index et posent
donc `.git/index.lock`. Le mount Linux **interdit la suppression de fichiers**
(`Operation not permitted` sur `unlink`). Git crée le verrou, échoue à le
retirer, et le laisse en place indéfiniment. Toute commande git lancée ensuite
par Eugène depuis PowerShell se bloque derrière ce verrou fantôme — y compris
le `git add .` du workflow de push. Les processus `git.exe` qui s'accumulent ne
sont pas des zombies : ce sont ses propres commandes en attente, et elles se
terminent d'elles-mêmes dès que le verrou est supprimé.

Le piège est que le verrou est **invisible dans la sortie de la commande** : le
`git status` de l'IA affiche un résultat correct, l'avertissement `unable to
unlink` n'apparaît qu'au passage suivant. On peut donc en semer plusieurs sans
rien remarquer, et la panne ne se manifeste que côté utilisateur, bien plus tard.

**Règle** : depuis le mount, préfixer **toute** commande git de lecture par
`--no-optional-locks` (ou exporter `GIT_OPTIONAL_LOCKS=0`). Vérifié : aucun
verrou créé.

```bash
git --no-optional-locks status --short
git --no-optional-locks diff --stat
```

Commandes sûres sans précaution particulière (elles ne touchent pas à l'index) :
`git log`, `git show`, `git cat-file`, `git rev-parse`, `git branch`.

Commandes à **ne jamais lancer** depuis le mount — elles écrivent l'index et
laisseront un verrou irrécupérable : `git add`, `git commit`, `git stash`,
`git checkout`, `git reset`, `git merge`, `git pull`. Ces opérations
appartiennent au terminal d'Eugène, pas à l'IA.

**Réflexe de fin de session** : avant de donner le bloc git de push, vérifier
qu'aucun verrou ne traîne, et le signaler s'il y en a un.

```bash
ls -l .git/index.lock 2>/dev/null && echo "VERROU A SUPPRIMER" || echo "aucun verrou"
```

La suppression ne peut se faire que côté Windows :
`Remove-Item .git\index.lock -Force`.

**Ne jamais imputer un verrou à Cursor sans avoir d'abord vérifié l'horodatage
du fichier** et l'avoir comparé aux commandes git lancées par l'IA. Envoyer
l'utilisateur tuer des processus qui ne sont pas en cause lui fait perdre du
temps et, s'il supprime un verrou pendant qu'une écriture est réellement en
cours, expose son index à la corruption.

---

## Git — merges, conflits et cohabitation avec Cursor (leçons du 24 juillet 2026)

Cette section documente une panne qui a mis la v1 en 502 pendant plusieurs heures.
La cause n'était pas un bug applicatif : c'était un empilement d'erreurs de workflow
git + interférence d'éditeur pendant un `device_commit_files`. À éviter à tout prix.

### Ce qui s'est passé — schéma général

1. Un merge `feature/myao-improvements` → `staging` avait produit des marqueurs de
   conflit `<<<<<<< HEAD` / `>>>>>>>` dans plusieurs fichiers, jamais résolus.
2. Des commits `wip` ont été faits par-dessus **sans regarder le contenu** — les
   marqueurs ont été committés dans le repo, silencieux car cachés dans des raw
   strings Python (`SETTINGS_HTML = r"""..."""`) qui parsent quand même.
3. Claude a édité ces fichiers sans détecter les marqueurs (son `ast.parse` a
   validé, mais les marqueurs cassaient le JS émis au browser).
4. Cursor était ouvert avec MySifa. Entre le `device_commit_files` de Claude et
   le `git add`, Cursor a détecté le changement disque et réécrit le fichier
   avec sa vue interne (encore polluée par les marqueurs).
5. Le commit final contenait la version corrompue de Cursor, pas celle de Claude.

### Règles à suivre systématiquement

**Avant tout Edit / Write sur un fichier de code**, Claude DOIT :

1. Lancer `git status` et refuser d'éditer si `Unmerged paths` / `both modified`
   apparaît. Demander à Eugène de résoudre le merge (ou `git merge --abort`)
   avant de commencer.

2. Grep systématique des marqueurs de conflit sur chaque fichier cible :
   ```bash
   grep -cnE '^<<<<<<<|^=======$|^>>>>>>>' <fichier>
   ```
   Si le résultat est > 0 → STOP. Signaler les lignes à Eugène, ne pas éditer.

3. `ast.parse` (Python) n'est PAS un check suffisant : les marqueurs peuvent
   être piégés dans des raw strings et passer le parseur alors qu'ils cassent
   le JavaScript émis au client. Toujours combiner avec le grep marqueurs.

**Cursor / VS Code ouverts pendant un commit automatisé** — risque de réinjection :

- Quand Claude s'apprête à écrire un fichier via `device_commit_files` sur un
  fichier qu'un éditeur tient ouvert avec état "dirty" ou vue "merge en cours",
  l'éditeur peut écraser le fichier livré par sa vue interne.
- Avant tout gros push via bridge, Claude demande à Eugène de fermer complètement
  Cursor (`Cmd+Q`, pas juste la croix de fenêtre) et vérifie via
  `ps aux | grep -iE 'Cursor' | grep -v grep` que le process est bien mort.
- Après `device_commit_files`, faire calculer le MD5 côté Mac dans le même bloc
  bash que le `git add` — le hash doit matcher ce que Claude a livré.
- Revérifier le MD5 après `git add`. Il DOIT rester identique. Si divergence,
  un process a écrit entre-temps et il faut recommencer avec l'éditeur fermé.

**Commits « wip » et hygiène git** :

- Un `git commit -am 'wip'` sans regarder `git status` peut committer des
  marqueurs de conflit non résolus, des fichiers auto-générés (`nohup.out`,
  `__pycache__`, `.pyc`), ou du contenu d'un merge en cours.
- Toujours faire `git status` **et** `grep -rE '^<<<<<<<' .` avant tout commit
  qui vient d'un merge, avant de valider.
- Éviter `git add .` / `git add -A` sur un état incertain — préférer les
  fichiers explicites (`git add app/routers/settings.py`) pour ne pas embarquer
  des artefacts d'éditeur ou de venv.

### Récupérer d'un fichier corrompu committé

Si un commit corrompu a atteint `staging` (marqueurs de conflit dans le repo) :

1. Identifier le dernier commit sain :
   ```bash
   for c in $(git log --format=%H -10 -- <fichier>); do
     ok=$(git show $c:<fichier> 2>/dev/null | grep -cE '^<<<<<<<|^>>>>>>>')
     echo "$c → $ok marqueur(s)"
   done
   ```
2. Reconstruire le fichier propre en repartant de la dernière version saine +
   réintégration manuelle des changements légitimes des commits suivants
   (Claude peut faire ce travail depuis sa vue si le fichier existe encore
   dans son `/tmp/` de session).
3. Fermer Cursor, livrer via bridge, vérifier MD5, commit + push d'un trait.

---

## Guides in-app (tutos par onglet) — obligatoire pour chaque nouvelle app ou nouvel onglet

MySifa embarque un système de guides in-app qui explique chaque module à
l'utilisateur au sein même de l'interface. Le premier module équipé est
Qualité (voir `app/web/qualite_page.py`) — il sert de référence pour tous
les modules à venir.

**Règle absolue — pas de nouvelle app ni de nouvel onglet sans guide.**

Toute nouvelle application (au sens module — MyProd, MyStock, MyExpé…) et
tout nouvel onglet fonctionnel à l'intérieur d'un module doit être livré
avec son guide in-app. Sans guide, le PR n'est pas considéré comme fini,
au même titre qu'une page sans version mobile ou qu'un endpoint sans
gestion d'erreur.

**Règle proactive — proposer un guide quand il n'y en a pas.**

Si Eugène demande une modification sur un onglet existant qui n'a pas
encore de guide, l'IA doit systématiquement, **une fois le vrai travail
terminé**, proposer d'en ajouter un. Une ligne suffit à la fin de la
réponse : « Cet onglet n'a pas encore de guide in-app. Je te propose d'en
ajouter un — 4 à 6 étapes avec illustrations SVG et bullets par service.
Ok ? ». Ne pas attendre qu'Eugène le demande. Ne pas noyer la proposition
dans un paragraphe. Ne pas la formuler avant d'avoir fait le travail
demandé.

**Structure d'un guide**

Un guide est un dict de la forme `{ 'clé-guide': { steps: [...] } }`
retourné par une fonction locale au module (aujourd'hui `_qualiteGuides()`
dans `qualite_page.py`). Chaque `step` a la forme :

```javascript
{
  icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">…</svg>',
  title: 'Titre court de l\'étape',
  body: '<p>HTML autorisé : <strong>gras</strong>, <span class="qguide-tag">tag</span>.</p>',
  illu: '<svg viewBox="0 0 340 150">… mini-mockup de la page …</svg>',
  extra: '<p>Contenu optionnel affiché sous l\'illustration</p>'  // facultatif
}
```

- **Étape 1 (obligatoire)** — introduction courte à la page + bullets
  « Ce que vous avez à faire » adaptés au rôle courant. Titre = nom de
  l'onglet. Les bullets sont déclinés par service dans un dict du type
  `QUALITE_TASKS_BY_SERVICE = { direction: [...], administration: [...],
  fabrication: [...], commercial: [...] }`. La 1ère slide sélectionne le
  jeu de bullets en fonction de `S.userRole` (injecté par le template via
  `__USER_ROLE__`). Pour `superadmin` et `direction`, on affiche toutes
  les sections empilées.
- **Étapes 2 à N** — viser **4 à 6 étapes au total** (l'étape 1 comprise).
  Chacune couvre un aspect fonctionnel majeur : structure de données,
  action clé, workflow, alertes, astuces. Le `body` est court (2 à 4
  lignes maximum), factuel. L'`icon` est un SVG stroke
  (`stroke="currentColor"`, `stroke-width="1.6"` ou `"1.8"`) — jamais un
  emoji.

**Illustrations SVG — mini-mockups fidèles de la page**

Chaque étape porte une `illu` : un SVG placé sous le texte qui montre
visuellement l'élément de la page dont parle l'étape. Ce n'est **pas** une
icône décorative — un utilisateur qui regarde l'illustration doit
reconnaître le composant réel (grille de cartes, carte groupe, modal
radio, bandeau alertes, header page détail, etc.). Les illustrations du
module Qualité sont regroupées dans le dict `QUALITE_MOCKUPS` et servent
de modèle.

Contraintes techniques :

- `viewBox` typique : `0 0 340 150` (ajustable selon le composant).
- Couleurs : **uniquement** les variables CSS du design system —
  `var(--card)`, `var(--border)`, `var(--accent)`, `var(--accent-bg)`,
  `var(--text)`, `var(--text2)`, `var(--muted)`, `var(--ok)`,
  `var(--warn)`, `var(--danger)`, `var(--bg)`. Seule exception tolérée :
  `#fff` pour du texte posé sur un fond `var(--accent)` déjà saturé.
- Pas de couleur codée en dur. Pas d'`<image>` externe. Pas de police
  externe — laisser hériter la police système.

**Comment brancher un nouveau guide (4 points, pas plus)**

1. **Ajouter une entrée** dans le dict `_qualiteGuides()` (ou son
   équivalent pour un autre module — `settings_page.py`, `stock_page.py`,
   `planning_page.py` etc. n'ont pas encore leur propre dictionnaire de
   guides ; le jour où le premier guide y sera ajouté, dupliquer le
   pattern de `qualite_page.py`).
2. **Mapper la vue au guide** dans `VIEW_TO_GUIDE = { 'nom-de-vue':
   'clé-guide' }` pour l'auto-open lors du `setView(...)`. Une fois le
   guide acknowledged par un utilisateur, il ne se rouvre plus
   automatiquement — il reste accessible via le bouton `?`.
3. **Ajouter le bouton `?`** (icône livre ouvert) dans le header de la
   vue :
   ```html
   <button type="button" class="qual-help-btn" data-guide="ma-cle"
           onclick="openGuide('ma-cle')">…</button>
   ```
   Le badge pulse `.unread` s'affiche automatiquement tant que le guide
   n'a pas été acked.
4. **Mettre à jour `_FMT_GUIDES`** dans `settings_page.py` avec le label
   lisible du nouveau guide, pour qu'il apparaisse joliment dans la
   table admin des Formations (`/settings` → onglet « Formations &
   guides »).

**Contenu — règles éditoriales**

- **Pas d'emojis** (règle générale MySifa).
- Ton **direct, factuel, professionnel** — pas de « Bienvenue ! », pas de
  « Découvrez notre super module ».
- Les bullets par service dans l'étape 1 sont **précis et actionnables** :
  « Saisir les certificats matière reçus des fournisseurs », pas
  « Utiliser le module Qualité ».
- Le `body` d'une étape tient en 2 à 4 lignes. Si ça déborde, l'étape
  n'est pas assez ciblée — la découper.
- Les illustrations sont des **mini-mockups fidèles** de la page, pas des
  icônes abstraites.

**Pièges à éviter (retours d'expérience)**

Cinq bugs concrets rencontrés en construisant le premier guide, qu'il faut
éviter dans les modules suivants :

1. **`main.py` : import + `include_router` obligatoires.** L'import
   `from app.routers.guides import router as guides_api_router` **ne
   suffit pas**. Il faut aussi `app.include_router(guides_api_router)`
   sinon toutes les routes `/api/guides/*` renvoient un 404 silencieux
   côté front (aucune trace côté serveur, aucun message côté client).
   Vérifier les deux points à chaque nouveau router.

2. **Contenu JS entre `<script src="…">` et `</script>` : ignoré.**
   Un tag `<script>` avec attribut `src` ne peut pas contenir de code
   inline — le browser charge le fichier externe et ignore tout ce qu'il
   y a entre les balises. Si un patch insère des fonctions à cet
   endroit-là par erreur, elles ne seront jamais définies et un
   `ReferenceError` remontera quand elles seront appelées. Injecter le
   code inline **avant** ou **après** le tag `<script src=…>`, dans son
   propre bloc `<script>…</script>`.

3. **Le helper `api()` change selon le module.** Dans
   `qualite_page.py`, `api(path, opts)` retourne l'objet `Response` de
   `fetch` — le front doit tester `if (!r.ok)` puis appeler
   `await r.json()`. Dans `settings_page.py`, `api(path, opts)` retourne
   déjà **le JSON parsé** et **throw sur HTTP != 2xx** — le front doit
   faire `_var = await api(...)` dans un `try/catch`. Copier-coller un
   pattern d'un module à l'autre sans lire les 4 lignes de `async
   function api(...)` provoque un « erreur chargement » alors que le
   serveur renvoie 200. Vérifier `api()` à chaque changement de module.

4. **La table `users` n'a pas de colonne `prenom`.** Elle a `id`, `nom`
   (nom complet), `email`, `role`, `password_hash`, `operateur_lie`,
   `actif`, `created_at`, `last_login`. Un `SELECT ..., prenom, ...`
   fait planter la requête SQL en 500. Utiliser `nom` seul dans le
   backend, et côté front construire l'affichage en défensif
   (``${u.prenom||''} ${u.nom||''}``.trim() supporte les 2 formats).

5. **Ack robuste — envoyer bitmap ET total_steps depuis le front.** Les
   `heartbeats` du suivi de progression sont *fire-and-forget* (POST
   asynchrones sans `await`). Ils peuvent arriver au serveur **après**
   l'appel `/ack`. Pour éviter cette race condition, le front envoie
   toujours dans le body de `/ack` : `{guide_key, client_bitmap,
   client_total_steps}`. Le serveur fait `merged = server_bitmap |
   client_bmp` et fait confiance au `client_total_steps` (auto-heal
   d'une éventuelle row DB avec un `total_steps` stale d'une ancienne
   version du guide). Reproduire ce pattern pour tout nouveau système
   de progression : bitmap + total côté front, fusion côté serveur.

**Infra existante — rien à re-écrire**

Le système est complet côté infra ; ajouter un guide ne demande que du
contenu (steps + illustrations SVG + entrée dans le mapping). Rien à
brancher côté backend, rien à ajouter en DB. Ce qui existe déjà :

- **Migration DB 181** — table `user_guide_progress` (`user_id`,
  `guide_key`, `total_steps`, `steps_seen_bitmap`, `total_time_ms`,
  `open_count`, `opened_at`, `completed_at`, `acknowledged_at`,
  `reset_at`, `reset_by`). Une ligne par (utilisateur, guide).
- **Router `app/routers/guides.py`** — `GET /api/guides/progress`,
  `POST /api/guides/open`, `POST /api/guides/heartbeat`,
  `POST /api/guides/ack`, plus `GET /api/guides/admin/overview` et
  `POST /api/guides/admin/reset` (gated `superadmin | direction`).
- **Frontend générique** — modal avec transitions horizontales
  (`from-left` / `from-right` / `to-left` / `to-right`), barre de
  progression, dots cliquables, boutons Précédent / Suivant, et bouton
  « J'ai compris — clôturer » **désactivé tant que toutes les étapes
  n'ont pas été vues** (bitmap complet). Auto-open à la 1ère visite,
  jamais de re-open automatique après acknowledgement.
- **Admin `/settings` → « Formations & guides »** (groupe Audit &
  qualité) — tableau `Utilisateur × Guide` avec statut, étapes vues,
  temps passé, dates, et bouton Reset pour repasser un utilisateur à
  zéro sur un guide.

---

## Sécurité, secrets & audit trail

Ces règles s'appliquent dès le premier client Kernse payé, mais elles sont
utilisables tout de suite pour SIFA (aucune régression).

**Secrets — jamais dans le repo git**

- Toute clé (Stripe, Microsoft Graph client secret, Anthropic, DeepL, SMTP,
  etc.) vit dans `.env` sur le VPS. `.gitignore` bloque `.env`.
- `.env.example` (versionné) liste toutes les variables attendues avec des
  valeurs placeholder — jamais de vraie clé, jamais de vraie URL de webhook.
- Rotation semestrielle des secrets sensibles, documentée dans
  `docs/archives/rotations-YYYY.md` (date, portée, qui).
- Les secrets clients Kernse (clés Stripe par instance, si un jour on les
  isole) sont provisionnés par un script hors-repo, jamais tapés à la main.

**Anti-fuite — règles absolues**

- Ne jamais logger un token, un mot de passe (même hashé), une session, une
  clé API, un numéro de carte. Filtrer avant `logger.info`.
- Les endpoints ne renvoient jamais un secret dans la réponse, y compris à
  la création (ex. pas de réponse « voici la clé qu'on vient de générer,
  gardez-la précieusement » — on force un `GET /me/api-keys` séparé qui
  affiche les 4 derniers caractères seulement).
- Les erreurs d'authentification ne révèlent pas si un email existe :
  message générique « identifiants invalides », même sur un mauvais mot de
  passe pour un compte existant.
- Les uploads ne servent jamais de contenu exécutable (`text/html`,
  `application/javascript`) — servis avec `Content-Disposition: attachment`.

**Audit trail — table `audit_log`**

Obligatoire dès qu'une donnée sensible est modifiée : utilisateurs
(création, changement de rôle, désactivation), rôles/permissions,
paramètres plateforme, paramètres entreprise, factures/paiements, données
personnelles RGPD, suspensions/résiliations d'instance.

- Colonnes : `id`, `at` (UTC ISO), `user_id`, `user_email`, `ip`, `action`
  (verbe court), `entity_type`, `entity_id`, `before` (JSON), `after`
  (JSON).
- Rétention 12 mois minimum, 24 mois pour la facturation (obligation
  comptable).
- Consultable via la console plateforme (filtres : par client, par
  utilisateur, par action, par date).
- Écriture dans le même transaction que la modif — jamais d'audit
  « best-effort » qu'on peut oublier de committer.

**Auth — durcissement pour clients payants**

- Politique mot de passe : 12 caractères min, complexité, blocklist des
  mots de passe compromis (haveibeenpwned k-anonymity).
- 2FA obligatoire pour les rôles `superadmin` et `direction` dès qu'il y a
  des clients payants sur la plateforme (délai de grâce : 30 jours après
  activation d'une organisation).
- SSO Azure AD (OIDC) implémentable pour les clients qui le demandent —
  le maquettage existe déjà côté login.

---

## Cycle de vie client (suspension, résiliation, RGPD)

Aujourd'hui : un client se crée à la main. Demain : il doit pouvoir être
suspendu (impayé), résilié (fin de contrat), ré-activé, et exporté sans
qu'un développeur ait à écrire du SQL.

**Suspension — impayé, litige, autre**

- Chaque instance client a un flag `suspended` (dans la table `clients` de
  `platform_settings`).
- Quand `suspended=true` : le login renvoie « accès suspendu — contactez le
  support » sans révéler la raison. La DB reste intacte, les uploads
  restent en place, la facturation continue jusqu'au terme légal.
- Réactivation = flag remis à `false`, aucune migration ni restauration.
- La suspension est tracée dans l'audit log (qui a suspendu, quand,
  raison).

**Résiliation — fin de contrat**

- Après notification écrite (email + interface), l'instance passe en
  `terminated`, avec une date `terminated_at`.
- Pendant 30 jours à partir de `terminated_at` :
  - La DB passe en lecture seule (aucune écriture applicative acceptée).
  - Un bouton « Export final complet » est proposé dans Paramètres :
    dump SQLite + archive ZIP des uploads, téléchargeable par le
    superadmin de l'organisation.
  - Aucune facturation, aucun envoi automatique, aucune notification
    push.
- Une bannière rouge en tête de chaque page prévient l'utilisateur qu'il
  est en période de rétention.

**Suppression définitive — passé J+30**

- Un script `kernse/scripts/purge_client.sh` détruit :
  - La DB SQLite de l'instance et tous les uploads.
  - Le vhost nginx, le service systemd, le sous-domaine, le certificat.
- Un enregistrement minimal reste dans
  `platform_settings.clients_archived` : nom d'entreprise, dates de début
  et de fin, motif de résiliation. Pas de donnée personnelle.
- L'audit trail plateforme conserve la trace de la suppression 5 ans
  (obligation comptable — la donnée personnelle a disparu, l'événement
  « suppression » reste).

**RGPD — droit à l'effacement d'un utilisateur**

- Un utilisateur peut demander la suppression de ses données personnelles
  (email, nom, téléphone, avatar) sans que ça détruise l'historique de
  ses saisies de production (obligation métier + traçabilité qualité).
- Solution : **anonymisation**. L'utilisateur devient « Utilisateur
  supprimé #<hash court> ». Toutes les saisies restent, l'identité
  personnelle disparaît.
- Endpoint dédié dans Paramètres, sous 30 jours max après demande écrite,
  tracé dans l'audit log.

**RGPD — export de données à la demande**

- Un client peut demander l'export complet de ses données à tout moment
  (self-service dans Paramètres). Format : dump SQLite + archive ZIP des
  uploads. Livraison sous 72h max.
- Le fait qu'on assume « une instance = une DB dédiée » rend cet export
  trivial — c'est un argument commercial à exploiter.

---

## API versioning & compat descendante

Aujourd'hui (SIFA seul) : les endpoints sous `/api/*` peuvent bouger
librement — un seul consommateur, contrôlable. Cette liberté prend fin
**au premier client payé Kernse**.

**Règle Kernse — à appliquer dès qu'on commence à écrire des routes
publiques pour Kernse**

- Toute nouvelle route publique (utilisée par un front qu'on ne contrôle
  pas totalement, un partenaire, un intégrateur, un webhook Stripe) est
  préfixée `/api/v1/`. Les routes internes (`/healthz`, `/platform/admin/*`,
  `/api/internal/*`) restent hors versioning.
- Chaque route publique a un schéma Pydantic explicite en entrée et en
  sortie. Ne jamais renvoyer un objet DB brut avec tous ses champs. Ne
  jamais ajouter un champ **obligatoire** à un endpoint existant sans
  bump de version.

**Deprecation — 6 mois minimum**

Avant de retirer une route `/api/v1/` :

1. Ajouter `/api/v2/xxx` avec le nouveau contrat.
2. Marquer `/api/v1/xxx` comme dépréciée : header HTTP `Deprecation: true`,
   `Sunset: <date>`, plus une entrée dans `docs/api/deprecations.md`.
3. Attendre 6 mois minimum entre la publication de v2 et le retrait de
   v1.
4. Prévenir chaque client par email : une fois au démarrage de la
   période de déprecation, une fois 1 mois avant le retrait.

**Compatibilité côté client**

- Les instances Kernse supportent les 2 dernières versions majeures
  d'API en parallèle. La console plateforme affiche par instance quelle
  version le front consomme (`X-Api-Version` request header ou
  détection au niveau du reverse proxy).
- Le front interne (portail Kernse) migre vers la nouvelle version
  d'API dans le mois qui suit sa publication — pas en même temps qu'un
  autre chantier.

---

## Emails transactionnels & SLA

**Emails multi-instance**

- Chaque instance client Kernse envoie depuis son propre domaine
  expéditeur (`noreply@<domaine-client>`), configuré à l'onboarding. Le
  patron client renseigne SPF/DKIM/DMARC en suivant un guide dans
  `kernse/docs/email-setup.md`.
- **Fallback** : tant que le client n'a pas fini de configurer son
  domaine, envoi depuis `noreply@kernse.com` avec `Reply-To` = adresse
  support du client. Marqué comme « configuration email en attente »
  dans le cockpit du superadmin de l'organisation.
- Templates HTML paramétrables par instance : logo, wordmark, couleur
  d'accent, coordonnées support, mentions légales bas de mail — tirés
  de `client_settings.branding_email_*`.
- **Anti-pattern absolu** : jamais d'envoi depuis `noreply@sifa.pro` ou
  `noreply@mysifa.fr` pour une instance non-SIFA. Ce serait une fuite de
  branding et un problème de déliverabilité (le tenant Microsoft SIFA
  n'a pas à envoyer pour un client Kernse).
- Déliverabilité surveillée côté plateforme : taux de bounce et de
  plainte par instance, alerte au-dessus de 2 %.

**SLA**

- Engagement de disponibilité inscrit dans les CGV (proposé : **99,5 %
  mensuel hors maintenance planifiée** — à valider avec un juriste avant
  publication).
- Maintenances planifiées annoncées 72h à l'avance (email + bandeau
  in-app), toujours hors heures ouvrées (soir ou week-end).
- **Status page publique** : `status.kernse.com` (statique ou managée
  type Statuspage/Instatus). État de la plateforme, incidents en cours,
  historique des 90 derniers jours.

**Monitoring & alertes**

- Chaque instance a un `/healthz` (déjà en place sur MySifa). La console
  plateforme le sollicite toutes les minutes.
- Alerte email + SMS au superadmin plateforme dès qu'une instance est
  KO > 2 minutes, avec identification claire de l'instance concernée.
- **Playbook incident** : détection → communication client (email
  générique dans les 15 min) → correctif → postmortem écrit dans
  `kernse/docs/incidents/YYYY-MM-DD-<slug>.md`. Chaque incident majeur
  est référencé sur la status page.

---

## Propreté du repo et des bases de données

Un repo qui se salit tue la vitesse de dev et la confiance des repreneurs
(nouveaux devs, audit technique, due diligence en cas de rachat). Règle
générale : **si un fichier n'est pas référencé par le code ou par la doc
active, il ne reste pas à la racine**.

**Racine du repo — ce qui a le droit d'y être**

Uniquement : `main.py`, `config.py`, `database.py` (shim), `operations.json`,
`requirements.txt`, `.env.example`, `.gitignore`, `.gitattributes`,
`README.md`, `CLAUDE.md`, et les dossiers principaux (`app/`, `kernse/`,
`data/`, `docs/`, `scripts/`, `tools/`, `frontend/`, `routers/`, `static/`
si utilisés). Aucun brouillon, aucune archive de prompt, aucun CSV de test,
aucun `.docx` de compte-rendu.

**Où va quoi**

- `docs/archives/` : anciens prompts (`FSC_Cursor_Prompts*.md`,
  `PROMPT_TRACA_CODEBARRE.md`, `CURSOR_PROMPT_mystock_matieres.md`,
  `PROMPTS_CURSOR*.md`, `MySifa — Prompts Cursor MyAO*.md`), roadmaps
  périmées, snapshots de brainstorming, `SIFA_CONTEXT.md`.
- `tools/fixtures/` : CSVs d'exemple pour tests d'import
  (`Ceva_tarifs.csv`, `Coquelle_tarifs.csv`, `Coupe_tarifs.csv`).
- `data/` : uniquement les DB actives (`production.db`), `uploads/`,
  `emplacements_plan.csv` — bref, ce que l'app lit réellement au runtime.
- `docs/` (à la racine, actif) : la doc encore utile — features
  documentées, guides opérateurs, brainstorm en cours (`brainstorm-kernse.html`).

**Fichiers fantômes à surveiller / supprimer**

- `production.db` à la racine (ancienne archive) — à supprimer une fois
  confirmé qu'il n'est référencé nulle part.
- `mysifa.db` (racine ou `data/`) — fantôme vide, à supprimer.
- `__init__.py` vide à la racine — héritage inutile, à supprimer si
  aucun import ne le référence.
- `.DS_Store` — ignoré par `.gitignore`, ne doit jamais atterrir dans un
  commit.
- Dossier `.windsurf/` — si spécifique à un poste de dev, à ignorer.

**Dossier `kernse/` — mêmes règles**

Pas de brouillon à la racine de `kernse/`, pas de fichier `TODO.md` qui
traîne, pas de PDF de plaquette commerciale versionné. Un fichier n'a
sa place que s'il est référencé par le code ou par la doc active. Les
archives commerciales (anciennes versions de landing, vieux brainstorm)
vont dans `kernse/docs/archives/`.

**Base de données — hygiène**

- Toute modification de schéma passe par une migration fichier dans
  `app/core/migrations/`. Jamais de `ALTER TABLE` à la main sur prod ni sur v1,
  jamais de nouveau numéro dans `_migrate()`.
- **VACUUM + ANALYZE mensuel automatisé** via cron VPS
  (`/etc/cron.d/mysifa-db-maintenance`). Récupère l'espace, met à jour
  les stats de l'optimiseur.
- **Purge des données obsolètes** : sessions expirées > 30 jours,
  notifications lues > 90 jours, uploads sans référence > 180 jours,
  logs applicatifs > 90 jours. À industrialiser côté Kernse (job par
  instance).
- **Colonnes orphelines** (plus lues par le code après un refactor) :
  identifier lors de la review de PR (grep sur le nom de colonne dans
  `app/` et `kernse/`), planifier une migration de `DROP COLUMN` dans
  le lot suivant. Ne pas laisser accumuler.
- **Chaque instance à la même version de schéma que la référence** (v1
  et v2 déjà alignées). Une instance client Kernse en retard sur la
  version de schéma = bug, jamais une feature. La console plateforme
  affiche la version de schéma par instance.
- **Indexes** : monitorer les slow queries à mesure que le volume
  grandit (query log SQLite, EXPLAIN QUERY PLAN). Ajouter les indexes
  au fur et à mesure, jamais en anticipation massive.
- **Backups par instance** : rotation 7 jours automatique
  (`/home/kernse/backups/<client>/`), + snapshot mensuel gardé 12 mois.
  Test de restauration trimestriel documenté.

**Audit trimestriel**

Chaque trimestre : passe rapide de nettoyage documentée dans
`docs/archives/nettoyage-YYYY-QN.md` — fichiers déplacés, tables
purgées, colonnes orphelines droppées, dette technique tracée. Sans
cette discipline, le repo redevient un dépotoir en 12 mois.
