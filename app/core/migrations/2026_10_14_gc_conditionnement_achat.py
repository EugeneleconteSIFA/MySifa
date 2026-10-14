"""Nouvel ERP — le prix d'achat dépend du conditionnement (Eugène, 14/10/2026).

Une matière s'achète en plusieurs conditionnements (laize, longueur de
bobine), chacun avec son prix : le conditionnement est porté par le tarif
d'achat et par la ligne de pièce, pas seulement par la fiche matière (qui
garde un conditionnement par défaut).
"""

NOM = "gc_conditionnement_achat"
DEPEND = ["gc_socle", "gc_bobine_longueur"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    for t in ("gc_tarifs", "gc_pieces_lignes"):
        _col(conn, t, "laize_dmm", "INTEGER")
        _col(conn, t, "ml_par_bobine_milli", "INTEGER")
    _col(conn, "gc_tarifs", "ref_fournisseur", "TEXT NOT NULL DEFAULT ''")
    conn.commit()
