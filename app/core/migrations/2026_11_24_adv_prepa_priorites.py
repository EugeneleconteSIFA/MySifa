"""
ADV : ordre des préparations fixé à la main.

L'onglet Prépa (/adv?onglet=prepa) range les préparations par date
d'expédition. L'administration et la direction peuvent imposer un autre ordre
(glisser une ligne, ou ↑ ↓) : une ligne qui a un rang passe avant celles qui
n'en ont pas, et le stock MyStock lui est attribué en priorité. L'ordre est
commun : la logistique le voit tel que l'ADV l'a fixé.

Clé métier `(numero, ligne)` de la ligne de commande RVGI, comme les autres
tables ADV.
"""

NOM = "adv_prepa_priorites"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_prepa_priorites (
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            rang     INTEGER NOT NULL,
            maj_le   TEXT    NOT NULL,
            maj_par  TEXT,
            PRIMARY KEY (numero, ligne)
        )
    """)
    conn.commit()
