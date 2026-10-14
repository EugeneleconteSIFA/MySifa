"""Nouvel ERP — historique des relances clients.

Une relance porte sur un client à une date, avec son niveau (1 rappel
courtois, 2 relance ferme, 3 mise en demeure) et le montant échu à ce jour.
Le niveau suivant se propose à partir de la dernière relance.
"""

NOM = "gc_relances"
DEPEND = ["gc_socle"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_relances (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tiers_id        INTEGER NOT NULL REFERENCES gc_tiers(id),
            date_relance    TEXT NOT NULL,
            niveau          INTEGER NOT NULL,
            montant_cents   INTEGER NOT NULL,
            factures        TEXT NOT NULL DEFAULT '',
            notes           TEXT NOT NULL DEFAULT '',
            cree_par        TEXT,
            cree_le         TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_gc_relance_tiers ON gc_relances(tiers_id, date_relance);
        """
    )
    conn.commit()
