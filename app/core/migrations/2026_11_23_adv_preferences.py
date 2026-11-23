"""
ADV : préférences d'affichage par utilisateur.

Aujourd'hui une seule : l'ordre des colonnes du carnet (/adv), que chacun range
en glissant les en-têtes. Gardé en base et non dans le navigateur : l'ordre
suit la personne d'un poste à l'autre. Une ligne par (utilisateur, clé), la
valeur en JSON.
"""

NOM = "adv_preferences"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_preferences (
            user_id  INTEGER NOT NULL,
            cle      TEXT    NOT NULL,
            valeur   TEXT    NOT NULL,
            maj_le   TEXT    NOT NULL,
            PRIMARY KEY (user_id, cle)
        )
    """)
    conn.commit()
