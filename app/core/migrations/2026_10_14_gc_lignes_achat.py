"""Nouvel ERP — ligne d'achat comme RVGI (captures du 14/10/2026).

Commande d'achat : « dates confirmées » par le fournisseur (oui / non).
Réception : zone de rangement et zone douane de la ligne.
"""

NOM = "gc_lignes_achat"
DEPEND = ["gc_socle"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_pieces_lignes)").fetchall()}
    for col, decl in (("dates_confirmees", "INTEGER NOT NULL DEFAULT 0"), ("zone_rangement", "TEXT"), ("zone_douane", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE gc_pieces_lignes ADD COLUMN {col} {decl}")
    conn.commit()
