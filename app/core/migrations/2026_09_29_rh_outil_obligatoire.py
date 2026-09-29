"""
Case « Obligatoire » dans les catalogues de l'Outil RH (formations, documents).

Un élément obligatoire est attribué d'office à chaque employé suivi : à tous
ceux déjà présents au moment où on coche la case, puis à chaque employé
ajouté ensuite. Décocher ne retire rien. L'attribution est faite par l'API.
"""

NOM = "rh_outil_obligatoire"
DEPEND = ["rh_outil_formations", "rh_outil_documents"]


def appliquer(conn):
    for table in ("rh_outil_formations", "rh_outil_documents"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "obligatoire" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN obligatoire INTEGER NOT NULL DEFAULT 0")
    conn.commit()
