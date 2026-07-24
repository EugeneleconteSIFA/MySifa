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
- **Migrations DB** : pattern `_migrate()` dans `app/core/database.py`, versionnées via la table `schema_migrations`

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
│   │   └── database.py       # Schéma DB, migrations, helpers get_db() — NE PAS DUPLIQUER
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
- Migrations DB : `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone()`
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

## Points d'attention critiques

**Base de données**
- `duree_heures` est `REAL` — toujours `parseFloat()` côté JS
- `date_operation` stocké en `"%Y-%m-%dT%H:%M:%S"` heure Paris (pas de timezone dans la chaîne)
- `TERMINE_KEEP = 2` : les 2 derniers dossiers terminés restent visibles dans la liste
- Toute nouvelle colonne doit être ajoutée via une migration numérotée dans `_migrate()`

**Frontend**
- La scroll position doit être préservée après tout `renderEntries()` ou drag & drop
- `_autoScrollKey` est basé uniquement sur l'ID du dossier `en_cours`
- Les slots timeline sont positionnés en absolu sur les jours travaillés uniquement (jours off filtrés)
- Ne jamais reconstruire le DOM d'une modal ouverte pendant un refresh automatique — vérifier `document.getElementById("mroot").firstElementChild` avant tout re-render global

**Routing**
- `frontend/` et `routers/` à la racine sont des **shims** — ne pas y ajouter de logique
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

**Conflits de numérotation de migration** :
- Toujours vérifier `origin/staging` avant de choisir un numéro de migration
  (`git fetch origin && git show origin/staging:app/core/database.py | grep -n "_record_schema_migration(conn, 1[6-9][0-9]"`).
- Si conflit détecté (deux branches ont utilisé le même numéro), renuméroter
  la nôtre côté staging local **avant** de merger `origin/staging`, pas après.

**PowerShell vs bash** :
- Les blocs bash du CLAUDE.md (`if [[ ]]`, `&& \`, `if/then/fi`) ne fonctionnent
  PAS en PowerShell — le terminal d'Eugène. Pour les scripts multi-étapes en
  interactif, envelopper dans `& { … }` avec `if ($LASTEXITCODE -ne 0) { return }`
  après chaque commande. Le `return` sort du scriptblock sans fermer la fenêtre
  (contrairement à `exit 1`).

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

- Toute modification de schéma passe par une migration numérotée dans
  `_migrate()` (racine `app/core/database.py`). Jamais de `ALTER TABLE`
  à la main sur prod ni sur v1.
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
