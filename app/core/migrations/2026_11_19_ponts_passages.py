"""
Chaque passage d'un pont Access → MySifa laisse une trace (19/11/2026).

Le pont des fiches techniques ne contacte MySifa que pour une fiche modifiée :
un passage sans changement était invisible, et personne ne pouvait dire si la
synchro tournait encore. Le script envoie désormais un compte rendu à chaque
exécution (`POST /api/bridge/passage`), affiché dans MyProd › Fiches
techniques. Aucune purge : quelques lignes par jour.
"""

NOM = "ponts_passages"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ponts_passages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pont        TEXT    NOT NULL,   -- 'fiches' | 'of' | 'scans'
            recu_le     TEXT    NOT NULL,   -- heure serveur (Paris) de réception
            debut       TEXT,
            fin         TEXT,
            lues        INTEGER,
            envoyees    INTEGER,
            creees      INTEGER,
            maj         INTEGER,
            identiques  INTEGER,
            conflits    INTEGER,
            erreurs     INTEGER,
            poste       TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ponts_passages ON ponts_passages(pont, recu_le)")
    conn.commit()
