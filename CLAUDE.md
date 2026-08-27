# MySifa — Instructions pour Claude / Cursor / Windsurf

> **Ce fichier est court volontairement.** Tout ce qui ne sert que dans un
> périmètre précis vit dans `.claude/rules/` et se charge tout seul quand on
> ouvre les fichiers concernés. Les procédures longues sont devenues des skills.
> Les règles qui ne doivent JAMAIS être enfreintes sont appliquées par des hooks,
> pas par ce texte. Voir l'index en fin de fichier.
>
> Règle de maintenance : une ligne n'a sa place ici que si la retirer ferait
> faire une erreur à l'IA. Sinon elle descend dans une règle path-scopée.

---

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

---

## Rien de spécifique à SIFA codé en dur

Aucune donnée qui décrit l'entreprise n'est écrite en dur dans le code.
Machines, opérations, terminologie, transporteurs, structure de coûts,
calendrier, rôles, plans d'emplacement, taux horaires, jours de fermeture :
tout vit en base et s'édite dans Paramètres. Le code lit un référentiel, il ne
le contient pas.

- **Scalaire** (nom, URL, seuil) → `os.getenv("XXX", "<valeur SIFA>")` dans `config.py`.
- **Petit référentiel figé** (statuts, sévérités) → constante dans `config.py`, lue via une fonction, jamais interpolée en dur dans un template.
- **Référentiel métier** (machines, opérations, transporteurs, types de NC, postes de coût) → table SQLite créée par migration, seedée avec les valeurs SIFA, exposée par un CRUD dans Paramètres.

Interdits : `if machine == "Cohésio 1":` — la logique métier dépend d'attributs
(`type`, `capacite`, `taux_horaire`) en base, jamais d'un identifiant machine.
Idem pour `"eleconte@sifa.pro"`, `"mysifa.com"` ou `"SIFA"` injectés dans un
template envoyé à un utilisateur : ces valeurs sont dans `config.py`.

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

---

## Déploiement — les règles absolues

Deux instances FastAPI indépendantes sur le VPS, avec chacune sa base :

| Service | Port | Domaine | Rôle |
|---|---|---|---|
| `mysifa` | 8000 | `www.mysifa.com` | **Prod** |
| `mysifa-v1` | 8002 | `v1.mysifa.com` | **Staging** (bandeau rouge) |

- **JAMAIS** de `git pull`, `git reset` ou `systemctl restart mysifa` à la main
  sur `/home/sifa/production-saas/` (v2). v2 ne bouge **que** via le bouton
  « Promouvoir » depuis v1 — tout autre chemin contourne le backup et le
  rollback automatique.
- **JAMAIS** de `git pull` manuel sur `/home/sifa/production-saas-v1/` : le cron
  s'en charge, sinon les permissions cassent.
- **JAMAIS** de push direct sur `main`. Feature branch → PR vers `staging` →
  test sur v1 → bouton « Promouvoir ».
- **JAMAIS** bumper `APP_VERSION` sans proposition explicite validée par Eugène.
- Si une IA dans une autre conversation suggère de « git pull dans le dossier
  prod » ou de « restart le service mysifa », elle ignore cette stratégie —
  corrige-la avant de suivre ses instructions.

Procédure complète de promotion et rédaction de l'annonce de MAJ :
**skill `/promotion`**.

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

---

## Ton et style éditorial

- **Pas d'emojis** dans les messages, toasts, labels, annonces ou release notes
- Icônes neutres acceptées : →, ·, ✓, ×, ▸ et SVG inline
- Ton **professionnel et direct** — pas de formules commerciales, pas de "Bonjour !", pas de "De belles nouveautés vous attendent"
- Les messages d'erreur sont **factuels et actionnables** : "Durée invalide — valeur entre 0.25 et 24h." plutôt que "Oups, quelque chose s'est mal passé."
- Les confirmations de succès sont **courtes** : "Saisie enregistrée." pas "Votre saisie a bien été enregistrée avec succès !"

---

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

---

## Sécurité — l'essentiel

- Toute clé (Anthropic, SMTP, Graph, DeepL…) vit dans `.env` sur le VPS.
  `.env.example` versionné liste les variables avec des placeholders — jamais
  une vraie clé, jamais une vraie URL de webhook.
- Ne jamais logger un token, un mot de passe même hashé, une session, une clé
  API. Filtrer avant `logger.info`.
- Un endpoint ne renvoie jamais un secret dans sa réponse, y compris à la
  création.
- Les erreurs d'authentification ne révèlent pas si un email existe : message
  générique « identifiants invalides ».
- Les uploads ne servent jamais de contenu exécutable — `Content-Disposition:
  attachment`.
- `escHtml()` / `escAttr()` obligatoires pour toute interpolation de donnée
  utilisateur dans du HTML. Côté JS, `textContent` plutôt que `innerHTML` dès
  qu'on affiche une saisie libre.

Audit trail, politique de mot de passe, 2FA, SSO : `.claude/rules/securite.md`.

---

## Propreté du repo et des bases

**Ce qui a le droit d'être à la racine** : `main.py`, `config.py`,
`database.py` (shim), `operations.json`, `requirements.txt`, `.env.example`,
`.gitignore`, `.gitattributes`, `README.md`, `CLAUDE.md`, et les dossiers
principaux. Aucun brouillon, aucune archive de prompt, aucun CSV de test,
aucun `.docx` de compte-rendu.

- Anciens prompts, roadmaps périmées, snapshots de brainstorming → `docs/archive/`.
- CSV d'exemple pour tests d'import → `tools/fixtures/`.
- `data/` : uniquement ce que l'app lit au runtime.
- **Ne JAMAIS tracker un `.db` dans git.** Un blob git écrase la DB à chaque
  `git reset --hard` — c'est déjà arrivé, diagnostic 502 en boucle.
- Toute modification de schéma passe par une migration fichier. Jamais d'`ALTER
  TABLE` à la main sur prod ni sur v1.
- Colonnes orphelines après un refactor : `grep` sur le nom dans `app/`, puis
  migration `DROP COLUMN` dans le lot suivant.

Purges, VACUUM, backups, audit trimestriel : `docs/archive/proprete-repo.md`.

---

## Index — où est passé le reste

Ces fichiers étaient dans ce CLAUDE.md avant le 27 août 2026. Rien n'a été
perdu : la version complète d'origine est dans
`docs/archive/CLAUDE.md.avant-decoupage-2026-08-27.md`.

**Comment lire ces règles selon l'outil.** Eugène travaille dans Cowork, où
rien ne se charge tout seul : commence par cet index, puis ouvre la règle du
sujet que tu touches — c'est le même principe qu'un chargement automatique,
fait à la main. Dans Claude Code, les règles se chargent seules quand tu ouvres
un fichier de leur périmètre. Dans les deux cas, n'ouvre que celles qui servent.

**Règles par sujet** (`.claude/rules/`) :

| Fichier | Se charge quand tu touches à… |
|---|---|
| `design-system.md` | `app/web/**`, `static/**.css` |
| `frontend-comportement.md` | `app/web/**`, `static/**.js` — mode éco, sidebar, searchbars, UX |
| `migrations.md` | `app/core/migrations/**`, `database.py` |
| `couts-matieres.md` | pricing, MyStock, `mystock_prix.py` |
| `of-fiches-techniques.md` | OF, fabrication, fiches, nombre de fronts |
| `besoins-matieres.md` | `besoins_matieres.py`, carnet |
| `erp-rvgi.md` | tout ce qui touche `/erp` et le miroir RVGI |
| `structure-fichiers.md` | `main.py`, routers, pages |
| `securite.md` | auth, `app/core/**`, `config.py` |
| `cycle-vie-client.md` | settings, auth, RGPD |
| `api-versioning.md` | `app/routers/**`, `main.py` |
| `emails-transactionnels.md` | services mail, `weekly_report.py` |
| `git-conflits.md` | scripts shell, `.githooks/**` |
| `ecriture-fichiers.md` | chargée à chaque session (concerne l'acte d'écrire) |

**Skills** — à invoquer explicitement :

| Skill | Quand |
|---|---|
| `/migration` | ajouter une colonne, une table, un seed |
| `/guide-inapp` | créer ou mettre à jour un tuto par onglet |
| `/promotion` | préparer une mise en production et son annonce |

**Garde-fous automatiques** — deux niveaux, et il faut savoir lequel s'applique.

`.githooks/pre-commit` tourne **à chaque commit, quel que soit l'outil** — c'est
le seul qui protège toujours. Il BLOQUE les marqueurs de conflit, les octets
nuls (troncature d'écriture) et la syntaxe Python ou JS cassée ; il AVERTIT sur
les couleurs en dur dans `app/web/` et les fichiers au-delà de 1 200 lignes.
La distinction est volontaire : un hook qui bloque sur une couleur se fait
contourner au `--no-verify`, et emporte la protection contre les vrais dégâts.
Installation sur un nouveau clone : `git config core.hooksPath .githooks`.

`.claude/hooks/` ne se déclenche **que dans Claude Code** (`proteger.py` refuse
d'écrire dans `.env` ou une base ; `garde_bash.py` refuse le git manuel en prod
et le push sur `main` ; `apres_edition.py` contrôle après chaque édition). Rien
à installer, mais rien ne s'exécute non plus hors de Claude Code.

La CI (`.github/workflows/ci.yml`) rejoue syntaxe et tests à chaque push vers
`staging`. Pour la relancer en local avant de pousser : `scripts/ci_local.sh`.

**Périmètre exclu de la lecture de l'agent** : `kernse/`, `_base2/`,
`_stg_base/`, `_to_delete/`, `_tmp_planning_v2/`, `docs/archive/`. Ces dossiers
contiennent des copies mortes ou des projets à l'arrêt — coder contre eux est
une erreur.
