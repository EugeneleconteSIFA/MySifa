"""
ADV : jour de préparation fixé à la main dans le planning de prépa.

Par défaut, une préparation se fait le jour ouvré qui précède son
enlèvement (ou, sans enlèvement prévu, son expédition) ; un retard tombe
sur aujourd'hui. L'ADV peut la déplacer sur un autre jour en la glissant
dans la frise de l'onglet Prépa : ce jour-là est enregistré ici.

Clé métier `(numero, ligne)` de la ligne de commande RVGI, comme les autres
tables ADV.
"""

NOM = "adv_prepa_jours"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_prepa_jours (
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            jour     TEXT    NOT NULL,
            maj_le   TEXT    NOT NULL,
            maj_par  TEXT,
            PRIMARY KEY (numero, ligne)
        )
    """)
    conn.commit()
