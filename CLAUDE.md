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
