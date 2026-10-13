"""
Coût conteneur propre à la valorisation MyStock.

La valorisation doit pouvoir chiffrer le stock avec un autre coût de conteneur
que celui du tarif fournisseur (« et si le conteneur coûtait 8 000 ? ») sans
toucher au chiffre de Coûts matières. La surcharge vit donc dans sa propre
table, par déclinaison, et seule la valorisation la lit.
"""

NOM = "valo_surcharge_conteneur"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS valo_transport_surcharge (
               declinaison_id  INTEGER PRIMARY KEY,
               transport_cout  REAL NOT NULL,
               updated_at      TEXT,
               updated_by_name TEXT
           )"""
    )
    conn.commit()
