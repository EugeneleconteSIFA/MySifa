"""
Départs : date de chargement, saisie à côté de la date de livraison prévue.
"""

NOM = "expe_departs_date_chargement"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
    if "date_chargement" not in cols:
        conn.execute("ALTER TABLE expe_departs ADD COLUMN date_chargement TEXT")
