"""
ADV : préparations marquées « urgente » à la main.

Une préparation est urgente par le calcul (préparable, expédition passée,
aujourd'hui ou demain) ou parce que l'ADV l'a marquée (table ci-dessous). La
bulle rouge de la tuile « Prépa » du portail compte les deux ; la ligne
marquée passe en tête de son groupe et reçoit le stock avant les autres.

Clé métier `(numero, ligne)` de la ligne de commande RVGI, comme les autres
tables ADV.
"""

NOM = "adv_urgences"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_urgences (
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            maj_le   TEXT    NOT NULL,
            maj_par  TEXT,
            PRIMARY KEY (numero, ligne)
        )
    """)
    conn.commit()
