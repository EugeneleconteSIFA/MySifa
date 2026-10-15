"""Signalement d'un chiffrage incohérent à la clôture.

L'écran Calage de la clôture affiche les durées et les métrages que les
heures et les compteurs donnent. Quand ils ne collent pas avec ce que le
conducteur a vu, il le dit en une phrase : elle est gardée avec la
déclaration et remonte dans Retour de prod, où l'on revient dessus.
"""

NOM = "calage_signalement"
DEPEND = ["calage_declare_cloture"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(dossier_calages_declares)").fetchall()}
    if "signalement" not in cols:
        conn.execute("ALTER TABLE dossier_calages_declares ADD COLUMN signalement TEXT")
    conn.commit()
