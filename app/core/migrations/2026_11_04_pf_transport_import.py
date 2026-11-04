"""
Transport d'un produit fini importé, ajouté à son prix de valorisation.

Un produit fini acheté à l'étranger arrive avec un coût de transport que le
prix d'achat ne porte pas. La valorisation l'ajoute, sur demande, en part du
prix HT (`config.PF_TRANSPORT_IMPORT_DIVISEUR` : 9 → transport = prix / 9).

`transport_import` (0/1) dit si la ligne en porte, `transport_maj_le` /
`transport_maj_par` qui l'a posé. Pas de ligne dans l'historique des prix :
la reconstitution à date y lit le prix en vigueur, et une ligne « transport »
y passerait pour un changement de prix.
"""

NOM = "pf_transport_import"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(pf_valorisation)").fetchall()}
    if not cols:
        return  # table absente : base qui n'a pas encore la valorisation PF
    if "transport_import" not in cols:
        conn.execute("ALTER TABLE pf_valorisation ADD COLUMN transport_import INTEGER NOT NULL DEFAULT 0")
    if "transport_maj_le" not in cols:
        conn.execute("ALTER TABLE pf_valorisation ADD COLUMN transport_maj_le TEXT")
    if "transport_maj_par" not in cols:
        conn.execute("ALTER TABLE pf_valorisation ADD COLUMN transport_maj_par TEXT")
    conn.commit()
