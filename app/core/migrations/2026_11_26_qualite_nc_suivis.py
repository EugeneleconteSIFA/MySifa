"""
MyQualité, non-conformités : fil de suivi et accusé de réception client.

- `nc_suivis` : les étapes d'avancement d'une NC, ajoutées au fur et à mesure
  (« Échantillons reçus », « Relance du client »…). La date de la dernière
  étape dit si la NC avance : au-delà de `NC_RELANCE_JOURS` (config.py), la
  liste la signale.
- `ar_client_envoye` (+ date) : case « Accusé de réception NC client envoyé ».

Les messages de l'ancien onglet Discussion sont repris comme étapes de suivi,
avec leur auteur et leur date : c'est la même information (où on en est), et
l'onglet disparaît. `nc_messages` reste en place, rien n'est supprimé.
"""

NOM = "qualite_nc_suivis"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(nc_dossiers)").fetchall()}
    if not cols:
        return
    if "ar_client_envoye" not in cols:
        conn.execute("ALTER TABLE nc_dossiers ADD COLUMN ar_client_envoye INTEGER NOT NULL DEFAULT 0")
    if "ar_client_envoye_at" not in cols:
        conn.execute("ALTER TABLE nc_dossiers ADD COLUMN ar_client_envoye_at TEXT")

    conn.execute(
        """CREATE TABLE IF NOT EXISTS nc_suivis (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               nc_id       INTEGER NOT NULL REFERENCES nc_dossiers(id) ON DELETE CASCADE,
               date_action TEXT NOT NULL,
               texte       TEXT NOT NULL,
               auteur_id   INTEGER REFERENCES users(id),
               message_id  INTEGER,
               created_at  TEXT NOT NULL
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_suivis_nc ON nc_suivis(nc_id, date_action)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_nc_suivis_message ON nc_suivis(message_id)")

    n = 0
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='nc_messages'").fetchone():
        cur = conn.execute(
            """INSERT OR IGNORE INTO nc_suivis (nc_id, date_action, texte, auteur_id, message_id, created_at)
               SELECT nc_id, substr(created_at, 1, 10), body, author_id, id, created_at
                 FROM nc_messages
                WHERE trim(COALESCE(body, '')) <> ''"""
        )
        n = cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} message(s) repris en étapes de suivi.")
