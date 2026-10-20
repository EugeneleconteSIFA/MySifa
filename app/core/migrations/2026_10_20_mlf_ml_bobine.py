"""
Métrage par bobine d'un fournisseur sur une laize.

`matiere_laize_fournisseurs` dit quel fournisseur livre quelle laize d'une
matière. Un fournisseur ne livre pas toujours la même longueur sur toutes ses
laizes (6 000 m en 440, 12 000 m en 570) : la colonne `ml_bobine` porte ce
conditionnement propre à la laize. Vide, la longueur est celle de l'article
fournisseur (`mp_variantes.ml_bobine`), puis celle de la matière.

Information d'achat seulement : le stock MySifa reste compté avec le métrage
standard de la matière, faute de savoir de quel fournisseur vient une bobine.
"""

NOM = "mlf_ml_bobine"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matiere_laize_fournisseurs)").fetchall()}
    if cols and "ml_bobine" not in cols:
        conn.execute("ALTER TABLE matiere_laize_fournisseurs ADD COLUMN ml_bobine REAL")
    conn.commit()
