"""Nouvel ERP — longueur de bobine d'une matière (bon de commande d'achat RVGI).

Une matière s'achète au m² mais se conditionne en mètres linéaires : la
commande indique « Laize 470 — 10 bobines de 12 000 soit 120 000 ML ». La
laize est `format_l_dmm` ; il manquait la longueur d'une bobine.
"""

NOM = "gc_bobine_longueur"
DEPEND = ["gc_socle"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_articles)").fetchall()}
    if "ml_par_bobine_milli" not in cols:
        conn.execute("ALTER TABLE gc_articles ADD COLUMN ml_par_bobine_milli INTEGER")
    conn.commit()
