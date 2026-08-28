# Proprete du repo et des bases — version longue

Extrait du CLAUDE.md avant decoupage du 27 aout 2026. L'essentiel est
reste dans le CLAUDE.md racine ; ce fichier garde le detail (purges,
VACUUM, backups, audit trimestriel).

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
