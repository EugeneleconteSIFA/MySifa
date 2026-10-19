"""
Actions de production : une action n'appartient plus forcement a une reunion.

L'onglet Actions de MyProd ne sert plus qu'a suivre ce qui reste a faire : une
action s'y cree directement, sans point de production pour la porter. La
colonne `reunion_id` devient donc facultative. SQLite ne sait pas retirer un
NOT NULL : la table est reconstruite a l'identique, colonne relachee.

Les actions existantes gardent leur reunion d'origine.
"""

NOM = "reunion_actions_sans_reunion"
DEPEND = ["reunion_actions_statut"]


def appliquer(conn):
    infos = conn.execute("PRAGMA table_info(reunion_actions)").fetchall()
    if not infos:
        return  # table absente sur cette base : rien a faire
    col = next((r for r in infos if r[1] == "reunion_id"), None)
    if col is None or not col[3]:
        return  # deja facultative
    conn.execute("DROP TABLE IF EXISTS reunion_actions_nouv")
    conn.execute("""
        CREATE TABLE reunion_actions_nouv (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            reunion_id  INTEGER,
            texte       TEXT NOT NULL,
            responsable TEXT,
            echeance    TEXT,
            fait        INTEGER NOT NULL DEFAULT 0,
            fait_le     TEXT,
            fait_par    TEXT,
            created_at  TEXT NOT NULL,
            statut      TEXT NOT NULL DEFAULT 'a_faire'
        )""")
    nouv = {r[1] for r in conn.execute("PRAGMA table_info(reunion_actions_nouv)").fetchall()}
    communes = ", ".join(r[1] for r in infos if r[1] in nouv)
    conn.execute(f"INSERT INTO reunion_actions_nouv ({communes}) "
                 f"SELECT {communes} FROM reunion_actions")
    n = conn.execute("SELECT COUNT(*) FROM reunion_actions_nouv").fetchone()[0]
    conn.execute("DROP TABLE reunion_actions")
    conn.execute("ALTER TABLE reunion_actions_nouv RENAME TO reunion_actions")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_reunion_actions_reunion
                    ON reunion_actions(reunion_id, id)""")
    conn.commit()
    print(f"[MySifa] migration reunion_actions_sans_reunion : {n} action(s) reprise(s).")
