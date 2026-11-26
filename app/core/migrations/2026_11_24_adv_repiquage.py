"""
ADV : statut du repiquage d'une ligne de commande, réglable à la main.

L'étape « Prod » du carnet (/adv) intègre le repiquage quand la production de
la ligne est cochée « pour repiquage ». Son état se déduit du dossier de
repiquage du planning ; l'ADV peut le fixer à la main (à faire, en cours,
terminé) — un repiquage sous-traité ou suivi hors planning existe aussi.
Clé métier `(numero, ligne)` de la ligne RVGI, comme les autres tables ADV.
"""

NOM = "adv_repiquage"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_repiquages (
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            statut   TEXT    NOT NULL,
            maj_le   TEXT    NOT NULL,
            maj_par  TEXT,
            PRIMARY KEY (numero, ligne)
        )
    """)
    conn.commit()
