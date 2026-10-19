"""
Machines dont les dossiers comptent dans les « devis à lier ».

Sur certaines machines (finition, repiquage…), savoir combien de dossiers
n'ont pas de devis n'intéresse personne : ils gonflaient le compteur « Sans
devis », la pastille Rentabilité et la notification `prod.devis_a_traiter`.
`machines.rent_suivi_devis` = 0 retire les dossiers de la machine de ces
compteurs ; ils restent visibles sur la timeline. Le réglage se bascule
depuis MyProd > Rentabilité > Pilotage, machine par machine.

Défaut 1 : toutes les machines restent comptées, rien ne change tant que
personne n'a basculé. Rejouable.
"""

NOM = "machines_suivi_devis"


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "machines" not in tables:
        print(f"[MySifa] migration {NOM} : table machines absente, rien à faire.")
        return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if "rent_suivi_devis" not in cols:
        conn.execute("ALTER TABLE machines ADD COLUMN rent_suivi_devis INTEGER NOT NULL DEFAULT 1")
    conn.commit()
