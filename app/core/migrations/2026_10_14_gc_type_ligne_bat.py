"""Nouvel ERP — type de ligne et lien article ↔ BAT.

Type de ligne (réponse d'Eugène du 14/10/2026, C2) :
- `livrer_facturer` : le cas normal ;
- `livrer_sans_facture` : la ligne se livre mais ne passe jamais en facture ;
- `stocker` : la ligne se fabrique pour le stock, elle ne se livre pas — elle
  est soldée quand l'OF a produit la quantité.

Laboratoire (C1) : sert à gérer les BAT. Une ligne en création ou en
modification exige un BAT validé ; le BAT vit dans le module BAT de MySifa
(`bat_entries`), l'article de l'ERP y pointe par `bat_id`.
"""

NOM = "gc_type_ligne_bat"
DEPEND = ["gc_socle"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    _col(conn, "gc_pieces_lignes", "type_ligne", "TEXT NOT NULL DEFAULT 'livrer_facturer'")
    _col(conn, "gc_articles", "bat_id", "INTEGER")
    conn.commit()
