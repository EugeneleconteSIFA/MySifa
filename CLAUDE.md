# MySifa — Instructions pour Claude

## Contexte projet

MySifa (by SIFA) est un outil interne de gestion de production industrielle. Il comprend :
- **MyProd** — saisie de production opérateur (fabrication)
- **Planning machine** — planning atelier multi-machines (Cohésio 1, Cohésio 2, DSI, Repiquage)
- **MyStock** — gestion des stocks et emplacements
- **Paramètres** — gestion des comptes, rôles, matrices d'accès (super admin)
- Modules secondaires : MyCompta, MyExpé, Planning RH, Paie

## Stack technique

- **Backend** : Python / FastAPI, SQLite (via `database.py` à la racine du projet runtime)
- **Frontend** : HTML/CSS/JS vanilla servi en tant que chaîne Python (dans `app/web/*.py`)
- **Auth** : sessions cookie, rôles (`superadmin`, `direction`, `administration`, `fabrication`, `logistique`, `comptabilite`, `expedition`, `commercial`)
- **DB migrations** : pattern `_migrate()` dans `app/core/database.py`, versionnées via `schema_migrations`
- **Routing** : `frontend/` contient des ponts `from app/web/*.py import *` — les fichiers réels sont dans `app/web/`

## Conventions de code

- Le frontend est du JS vanilla avec un état central `S` et une fonction `render()` / `renderEntries()` / `renderTL()`
- Les appels API utilisent la fonction locale `api(path, options)` qui gère les credentials et le JSON
- Les modals sont injectés via `document.getElementById("mroot").innerHTML = ...`
- Les migrations DB suivent le pattern `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone()`
- Toujours utiliser `INSERT OR IGNORE` pour les seeds idempotents
- Ne jamais bloquer une saisie pour une erreur de mise à jour planning — utiliser `try/except: pass`

## Terminologie métier (à respecter)

| Terme technique | Terme métier affiché |
|---|---|
| `statut = attente` | En attente |
| `statut = en_cours` | En cours |
| `statut = termine` | Terminé |
| `statut_reel = reellement_en_attente` | (non affiché) |
| `statut_reel = reellement_en_saisie` | ⚙ en saisie |
| `statut_reel = reellement_termine` | ✓ saisie terminé |
| `operation_code = 01` | Début de production |
| `operation_code = 89` | Fin de production |
| `fin_dossier = true` | Dossier clôturé |
| `no_dossier` | Référence dossier |
| `planning_entries` | Dossiers au planning |
| `production_data` | Saisies de production |

## UI / UX — règles à respecter

- **Pas d'emojis** dans les messages, toasts, labels ou annonces. L'usage d'icônes SVG ou de caractères iconiques neutres (→, ·, ✓, ×) est apprécié.
- Ton **professionnel et direct** — pas de formules commerciales ("De belles nouveautés vous attendent", "Bonjour !", etc.)
- Les messages de mise à jour doivent ressembler à des **notes de version** (release notes) : précises, factuelles, bien structurées
- Les toasts utilisent `showToast(message, type)` avec `type` parmi `success`, `danger`, `info`
- Le thème est dark par défaut avec support light via `body.light`
- Les variables CSS principales : `--bg`, `--card`, `--border`, `--text`, `--text2`, `--muted`, `--accent`, `--ok`, `--danger`

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `app/core/database.py` | Schéma DB, migrations, helpers |
| `app/routers/fabrication.py` | API saisie de production |
| `app/routers/planning.py` | API planning machine |
| `app/routers/settings.py` | API paramètres + annonces MAJ |
| `app/web/planning_page.py` | Page planning (HTML/CSS/JS ~2300 lignes) |
| `app/web/fabrication_page.py` | Page saisie production |
| `app/web/settings_page.py` | Page paramètres admin |
| `operations.json` | Référentiel codes opérations |

## Points d'attention

- `duree_heures` est `REAL` en DB — toujours utiliser `parseFloat` côté JS, jamais `parseInt`
- `date_operation` est stocké en format `"%Y-%m-%dT%H:%M:%S"` heure de Paris (pas de timezone dans la chaîne)
- Les slots timeline sont positionnés en absolu basé sur les jours travaillés uniquement (jours off filtrés)
- `TERMINE_KEEP = 2` : les 2 derniers dossiers terminés restent visibles dans la liste
- La scroll position doit être préservée après tout `renderEntries()` ou drag & drop
- `_autoScrollKey` est basé uniquement sur l'ID du dossier `en_cours` (pas sur le hash de la liste)
