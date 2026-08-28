---
paths:
  - "main.py"
  - "config.py"
  - "app/routers/**/*.py"
  - "app/web/**/*.py"
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
