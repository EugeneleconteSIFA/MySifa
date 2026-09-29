"""
Première case de la checklist « Outil RH » : règlement intérieur signé.

Une colonne par point de la checklist, sur la ligne de l'employé suivi.
"""

NOM = "rh_outil_reglement_signe"
DEPEND = ["rh_outil_membres"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rh_outil_membres)").fetchall()}
    if "reglement_signe" not in cols:
        conn.execute(
            "ALTER TABLE rh_outil_membres ADD COLUMN reglement_signe INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()
