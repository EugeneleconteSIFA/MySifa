"""
Journal d'usage de l'IA : un enregistrement par action qui a appelé Claude.

Une question à l'agent peut déclencher plusieurs appels au modèle (boucle
d'outils) : ils sont additionnés sur une seule ligne, `nb_appels` dit combien.
`cout_usd` est calculé à l'écriture avec la grille de `config.py` et n'est
plus recalculé ensuite. `utilisateur` garde le nom tel qu'il était : un compte
supprimé laisse une ligne lisible.

`fonction` : agent (assistant IA), devis (lecture de devis), fsc (lecture de
certificat), tarif_transport (grille transporteur), sql (requête en langage
naturel du DB Viewer).
"""

NOM = "ia_usage"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ia_usage (
               id                     INTEGER PRIMARY KEY AUTOINCREMENT,
               cree_le                TEXT NOT NULL,
               user_id                INTEGER,
               utilisateur            TEXT,
               role                   TEXT,
               fonction               TEXT NOT NULL,
               module                 TEXT,
               modele                 TEXT,
               nb_appels              INTEGER NOT NULL DEFAULT 0,
               input_tokens           INTEGER NOT NULL DEFAULT 0,
               output_tokens          INTEGER NOT NULL DEFAULT 0,
               cache_lecture_tokens   INTEGER NOT NULL DEFAULT 0,
               cache_ecriture_tokens  INTEGER NOT NULL DEFAULT 0,
               cout_usd               REAL NOT NULL DEFAULT 0,
               duree_ms               INTEGER,
               statut                 TEXT
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ia_usage_date ON ia_usage(cree_le)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ia_usage_user ON ia_usage(user_id, cree_le)")
    conn.commit()
