"""Bobines laissées sur la machine mais NON rattachées à un dossier.

Lot 5 du chantier « scan matière en production » (10/09/2026). Quand le poste
frontal ne porte que des complexes, la glassine restée en place ne sert pas au
dossier : elle n'est pas rattachée (lot 4). Mais « pas rattachée » et « oubliée »
auraient la même allure en traçabilité — une glassine présente sur la machine
pendant le dossier et absente du rapport. Cette table garde la décision et sa
raison, pour que le rapport puisse la montrer.
"""

from __future__ import annotations

import sqlite3

NOM = "bobines_non_rattachees"
DEPEND = ["bobines_heritees"]


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dossier_bobines_non_rattachees (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            no_dossier      TEXT    NOT NULL,
            machine_id      INTEGER NOT NULL,
            code_barre      TEXT    NOT NULL,
            poste           TEXT,
            fab_matiere_id  INTEGER,      -- le dernier scan de la bobine avant ce dossier
            motif           TEXT    NOT NULL,   -- 'complexe_seul'
            created_at      TEXT    NOT NULL,
            created_by      TEXT,
            UNIQUE(no_dossier, machine_id, code_barre)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bob_non_rattachees_dossier "
        "ON dossier_bobines_non_rattachees(no_dossier)"
    )
    conn.commit()
