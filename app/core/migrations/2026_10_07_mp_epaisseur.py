"""
Épaisseur d'une matière première (µm).

La fiche technique d'un produit annonce son épaisseur totale, somme de celles
de ses couches : il faut donc la connaître matière par matière. Elle se saisit
dans le détail de la matière MyStock, à côté du grammage et de la couleur.
"""

NOM = "mp_epaisseur_matiere"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
    if not cols:
        return
    if "epaisseur_um" not in cols:
        conn.execute("ALTER TABLE matieres_premieres ADD COLUMN epaisseur_um REAL")
    conn.commit()
