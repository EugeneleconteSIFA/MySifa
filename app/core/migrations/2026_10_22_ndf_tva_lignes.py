"""
Ventilation de la TVA d'une note de frais par taux.

Un ticket de restaurant porte souvent deux taux (10 % sur la nourriture, 20 %
sur l'alcool). La note n'avait qu'un taux et un montant de TVA : la compta
recevait une approximation. `notes_de_frais_tva` porte une ligne par taux
(TTC, TVA, HT), telle qu'imprimée sur le ticket ; les montants de la note en
sont la somme. Une note à un seul taux a une seule ligne. Les indemnités
kilométriques n'en ont pas (pas de TVA).

Reprise : chaque note en montant existante reçoit sa ligne unique, tirée de ses
colonnes taux_tva / montant_tva / montant_ht. Rejouable : une note qui a déjà
des lignes n'est pas reprise.
"""

NOM = "ndf_tva_lignes"
DEPEND = ["ndf_categories"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notes_de_frais_tva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            ordre INTEGER NOT NULL DEFAULT 0,
            taux_tva REAL NOT NULL,
            montant_ttc REAL NOT NULL,
            montant_tva REAL NOT NULL,
            montant_ht REAL NOT NULL,
            FOREIGN KEY (note_id) REFERENCES notes_de_frais(id) ON DELETE CASCADE
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ndf_tva_note ON notes_de_frais_tva(note_id)")

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    n = 0
    if "notes_de_frais" in tables:
        rows = conn.execute(
            """SELECT id, montant_ttc, montant_tva, montant_ht, taux_tva
               FROM notes_de_frais n
               WHERE distance_km IS NULL AND montant_ttc > 0
                 AND NOT EXISTS (SELECT 1 FROM notes_de_frais_tva t WHERE t.note_id = n.id)"""
        ).fetchall()
        for r in rows:
            ttc = float(r[1] or 0)
            tva = float(r[2] or 0)
            ht = float(r[3]) if r[3] is not None else round(ttc - tva, 2)
            taux = float(r[4]) if r[4] is not None else 0.0
            conn.execute(
                """INSERT INTO notes_de_frais_tva
                   (note_id, ordre, taux_tva, montant_ttc, montant_tva, montant_ht)
                   VALUES (?,?,?,?,?,?)""",
                (r[0], 0, taux, round(ttc, 2), round(tva, 2), round(ht, 2)),
            )
            n += 1
    conn.commit()
    if n:
        print(f"[MySifa] migration {NOM} : {n} note(s) reprise(s) en une ligne de TVA.")
