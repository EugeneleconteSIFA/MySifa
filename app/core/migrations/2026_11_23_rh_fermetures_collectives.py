"""
Planning RH : fermetures collectives (fermeture annuelle de l'usine, pont…).

Une fermeture porte une période, un nombre de jours et un motif par défaut
(code de `rh_motifs_absence`, CP en général). L'appliquer crée un congé dans
`rh_conges` pour chaque employé actif, relié par `fermeture_id`. Chaque congé
reste un congé ordinaire : son motif se change un par un (sans solde pour
quelqu'un qui n'a plus de CP, par exemple), et les soldes le décomptent selon
ce motif.

`rh_fermetures_exclus` garde les personnes retirées d'une fermeture (elles
travaillent pendant la fermeture) : une nouvelle application ne les rajoute pas.
"""

NOM = "rh_fermetures_collectives"
DEPEND = ["rh_demandes_motifs"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_fermetures (
               id           INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle      TEXT NOT NULL,
               date_debut   TEXT NOT NULL,
               date_fin     TEXT NOT NULL,
               nb_jours     REAL NOT NULL,
               type_conge   TEXT NOT NULL DEFAULT 'CP',
               note         TEXT,
               cree_le      TEXT NOT NULL DEFAULT (datetime('now')),
               cree_par     TEXT,
               modifie_le   TEXT,
               modifie_par  TEXT
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_fermetures_exclus (
               fermeture_id INTEGER NOT NULL REFERENCES rh_fermetures(id) ON DELETE CASCADE,
               user_id      INTEGER NOT NULL REFERENCES users(id),
               cree_le      TEXT NOT NULL DEFAULT (datetime('now')),
               cree_par     TEXT,
               PRIMARY KEY (fermeture_id, user_id)
           )"""
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rh_conges)").fetchall()}
    if "fermeture_id" not in cols:
        conn.execute("ALTER TABLE rh_conges ADD COLUMN fermeture_id INTEGER REFERENCES rh_fermetures(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_conges_fermeture ON rh_conges(fermeture_id)")
    conn.commit()
