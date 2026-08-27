# Cursor Prompt 01 — DB Migrations : Matières premières

## Contexte

Tu travailles sur MySifa. La DB est SQLite. Les migrations sont dans `app/core/database.py`, dans la fonction `_migrate()`. Chaque migration suit ce pattern :

```python
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():
    conn.execute("CREATE TABLE IF NOT EXISTS ...")
    conn.execute("INSERT INTO schema_migrations(version) VALUES(N)")
```

**Avant de commencer :** inspecte `app/core/database.py` et trouve le numéro de migration le plus élevé déjà présent. Utilise les 3 numéros suivants pour les nouvelles migrations.

## Tâche

Ajouter 3 nouvelles migrations dans `_migrate()`, dans l'ordre.

---

### Migration N — Table `matieres_premieres`

Référentiel des matières (Mandrins, Palettes, Adhésifs, Cartons). Les références sont gérées via l'interface.

```sql
CREATE TABLE IF NOT EXISTS matieres_premieres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categorie TEXT NOT NULL CHECK(categorie IN ('mandrin','palette','adhesif','carton')),
    reference TEXT NOT NULL,
    designation TEXT NOT NULL,
    seuil_alerte REAL DEFAULT 0,
    actif INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    UNIQUE(categorie, reference)
);
```

---

### Migration N+1 — Table `mp_stock`

Stock courant par matière (en palettes).

```sql
CREATE TABLE IF NOT EXISTS mp_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matiere_id INTEGER NOT NULL UNIQUE REFERENCES matieres_premieres(id),
    quantite REAL DEFAULT 0,
    updated_at TEXT,
    updated_by_name TEXT
);
```

---

### Migration N+2 — Table `mp_mouvements`

Historique de tous les mouvements matières premières.

```sql
CREATE TABLE IF NOT EXISTS mp_mouvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id),
    type_mouvement TEXT NOT NULL CHECK(type_mouvement IN ('entree','sortie','ajustement','transfert')),
    quantite REAL NOT NULL,
    quantite_avant REAL,
    quantite_apres REAL,
    ref_bl TEXT,
    note TEXT,
    emplacement_source TEXT,
    emplacement_dest TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    created_by INTEGER,
    created_by_name TEXT
);
```

---

## Vérification

Après avoir ajouté les migrations, lance l'app (`uvicorn main:app` ou équivalent) et vérifie en SQLite :

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('matieres_premieres','mp_stock','mp_mouvements');
SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 5;
```

Les 3 tables doivent apparaître. Aucune table existante ne doit être modifiée.
