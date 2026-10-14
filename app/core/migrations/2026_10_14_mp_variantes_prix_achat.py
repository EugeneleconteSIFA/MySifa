"""
Prix d'achat propre à chaque article fournisseur (variante).

Un même fournisseur peut livrer deux articles pour une matière (Avery Jetgloss
R5000 et R5050) à deux prix différents. Le prix de Coûts matières reste stocké
par fournisseur × laize ; l'article principal y pousse le sien, les autres
articles gardent leur prix pour comparaison.
"""

NOM = "mp_variantes_prix_achat"
DEPEND = ["mp_variantes_fournisseur"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(mp_variantes)").fetchall()}
    for col, typ in (("prix_achat", "REAL"), ("prix_maj_le", "TEXT"), ("prix_maj_par", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE mp_variantes ADD COLUMN {col} {typ}")
    conn.commit()
