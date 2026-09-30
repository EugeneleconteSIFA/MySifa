"""
Outil RH (MyCompta) : catégories de formations et documents liés aux formations.

- `rh_outil_formation_categories` : référentiel des catégories, modifiable
  depuis l'onglet, prérempli avec les trois catégories SIFA. `ordre` fixe
  l'ordre d'affichage.
- `rh_outil_formations.categorie_id` : catégorie d'une formation (vide =
  « Sans catégorie »). Supprimer une catégorie laisse ses formations sans
  catégorie (géré par l'API).
- `rh_outil_formation_documents` : documents exigés avec une formation. Quand
  la formation est attribuée à un employé, ses documents le sont aussi.
  Rien n'est jamais retiré automatiquement.

Aucune formation existante n'est modifiée ni supprimée.
"""

from datetime import datetime

NOM = "rh_outil_categories_documents_lies"
DEPEND = ["rh_outil_formations", "rh_outil_documents"]

_SEED = ["Formation entreprise", "Formation métier", "Formation MySifa"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_formation_categories (
               id       INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle  TEXT NOT NULL,
               ordre    INTEGER NOT NULL DEFAULT 0,
               cree_le  TEXT NOT NULL
           )"""
    )
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS ux_rh_outil_formation_categories_libelle
               ON rh_outil_formation_categories(libelle COLLATE NOCASE)"""
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rh_outil_formations)").fetchall()}
    if "categorie_id" not in cols:
        conn.execute("ALTER TABLE rh_outil_formations ADD COLUMN categorie_id INTEGER "
                     "REFERENCES rh_outil_formation_categories(id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_formation_documents (
               formation_id  INTEGER NOT NULL REFERENCES rh_outil_formations(id) ON DELETE CASCADE,
               document_id   INTEGER NOT NULL REFERENCES rh_outil_documents(id) ON DELETE CASCADE,
               PRIMARY KEY (formation_id, document_id)
           )"""
    )
    conn.execute("""CREATE INDEX IF NOT EXISTS ix_rh_outil_formation_documents_doc
                        ON rh_outil_formation_documents(document_id)""")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    n = 0
    for i, libelle in enumerate(_SEED, start=1):
        n += conn.execute(
            """INSERT OR IGNORE INTO rh_outil_formation_categories (libelle, ordre, cree_le)
               VALUES (?,?,?)""",
            (libelle, i * 10, now),
        ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} catégorie(s) préremplie(s).")
