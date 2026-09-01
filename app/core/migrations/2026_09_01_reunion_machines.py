"""
Points de production : une reunion peut regarder plusieurs machines.

`reunions.machine` ne portait qu'un nom : soit une machine, soit rien (« toutes
les machines »). Un point du matin regarde souvent deux machines sur trois — il
fallait alors ouvrir deux reunions, ou tout regarder.

Une table plutot qu'une liste encodee dans le champ texte : c'est la meme forme
que `reunion_participants`, et elle se filtre et se compte sans reparser quoi
que ce soit. Une reunion SANS ligne ici regarde tout l'atelier — c'est le seul
sens que l'absence ait jamais eu.

`reunions.machine` reste en place et n'est plus lu : sqlite ne retire pas une
colonne sans reconstruire la table, et une reunion ancienne n'a rien a perdre
a garder la trace de ce qu'elle disait. Les valeurs existantes sont reprises
ici pour que les reunions deja tenues gardent leur perimetre.
"""

NOM = "reunion_machines"
DEPEND = ["reunions_prod"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reunion_machines (
            reunion_id INTEGER NOT NULL,
            machine    TEXT NOT NULL,
            PRIMARY KEY (reunion_id, machine)
        );
        CREATE INDEX IF NOT EXISTS idx_reunion_machines_reunion
            ON reunion_machines(reunion_id);
        """
    )
    # Reprise du perimetre des reunions deja tenues. INSERT OR IGNORE : la
    # migration se rejoue sans rien casser ni rien dupliquer.
    conn.execute(
        """INSERT OR IGNORE INTO reunion_machines (reunion_id, machine)
           SELECT id, TRIM(machine) FROM reunions
            WHERE TRIM(COALESCE(machine, '')) <> ''"""
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) AS c FROM reunion_machines").fetchone()["c"]
    print(f"[MySifa] migration reunion_machines : table en place, {n} perimetre(s) repris.")
