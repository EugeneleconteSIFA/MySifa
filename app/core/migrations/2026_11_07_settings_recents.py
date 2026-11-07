"""
Onglets des Paramètres ouverts récemment, par utilisateur.

Alimente la ligne « Ouverts récemment » de l'accueil des Paramètres. Une ligne
par (utilisateur, onglet), datée de la dernière ouverture : on la met à jour
plutôt que d'en ajouter une, et on ne garde que les plus récentes
(app/routers/settings_accueil.py).
"""

NOM = "settings_recents"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings_recents (
            user_id  INTEGER NOT NULL,
            onglet   TEXT    NOT NULL,
            ouvert_le TEXT   NOT NULL,
            PRIMARY KEY (user_id, onglet),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_settings_recents_user_date
            ON settings_recents(user_id, ouvert_le DESC);
        """
    )
    conn.commit()
