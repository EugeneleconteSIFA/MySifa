"""
ADV : règles de mise en forme conditionnelle du carnet de commandes.

Une règle colore une cellule du carnet (/adv) quand sa valeur remplit une
condition : « À fabriquer > 0 » en orange, « Fin de prod après Expédition » en
rouge, « BAT est Non » en rouge… Les règles sont communes au service : l'ADV et
la direction les règlent depuis l'engrenage du carnet, tout le monde voit les
mêmes couleurs. La première règle qui s'applique à une cellule l'emporte
(`ordre`).

Colonnes, opérateurs et couleurs admis : `ADV_MEF_*` dans config.py.
"""

NOM = "adv_mises_en_forme"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_mises_en_forme (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ordre     INTEGER NOT NULL DEFAULT 0,
            colonne   TEXT    NOT NULL,
            operateur TEXT    NOT NULL,
            cible     TEXT    NOT NULL DEFAULT 'valeur',
            valeur    TEXT,
            ton       TEXT    NOT NULL,
            maj_le    TEXT    NOT NULL,
            maj_par   TEXT
        )
    """)
    conn.commit()
