"""Outil confirmé au démarrage du dossier : la plaque qui tourne vraiment.

Le constat (22/10/2026)
-----------------------
Le formulaire de changement d'outil existe depuis le 22/09/2026 : un seul
code 60 saisi en un mois. La plaque se monte pendant le calage d'un nouveau
dossier, personne ne déclare un « changement ». Le métrage d'une plaque se
tient donc toujours à la main, ailleurs, avec les erreurs qui vont avec.

La fiche technique dit quelle plaque le dossier DEVAIT utiliser. Au démarrage
du dossier, le conducteur la confirme d'un appui, ou la change. Ce qu'il
choisit, et l'écart avec la fiche, sont gardés ici.

Ce que la migration installe
----------------------------
`outil_types.au_demarrage` — la nature d'outil se confirme-t-elle au
    démarrage d'un dossier ? Un attribut du référentiel, pas une liste en dur :
    l'atelier pourra y ajouter le magnétique sans release. Seedé à 1 pour la
    plaque.

`outils_demarrage` — une ligne par (saisie de démarrage, nature, rang) —
    une fiche peut prévoir deux plaques, `rang` suit l'outil 1, 2, 3 de la fiche :
    l'outil monté, l'outil prévu par la fiche (identifiant s'il est au
    référentiel, numéro sinon), et si les deux coïncident. Table à part plutôt
    que `production_data.outil_apres_id` : une saisie 01 peut confirmer
    plusieurs natures, et ces colonnes veulent dire « changement d'outil »
    partout où elles sont lues.
"""

from __future__ import annotations

import sqlite3

NOM = "outils_au_demarrage"
DEPEND = ["changement_outil_referentiel"]

TYPES_AU_DEMARRAGE = ("plaque",)


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    if "au_demarrage" not in _colonnes(conn, "outil_types"):
        conn.execute(
            "ALTER TABLE outil_types ADD COLUMN au_demarrage INTEGER NOT NULL DEFAULT 0"
        )
        for cle in TYPES_AU_DEMARRAGE:
            conn.execute("UPDATE outil_types SET au_demarrage = 1 WHERE cle = ?", (cle,))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS outils_demarrage (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            saisie_id      INTEGER NOT NULL,
            type_cle       TEXT    NOT NULL,
            rang           INTEGER NOT NULL DEFAULT 1,
            outil_id       INTEGER NOT NULL,
            outil_prevu_id INTEGER,
            numero_prevu   TEXT,
            conforme       INTEGER,
            machine        TEXT,
            no_dossier     TEXT,
            date_operation TEXT,
            cree_par       TEXT,
            created_at     TEXT
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_outils_demarrage_saisie "
        "ON outils_demarrage(saisie_id, type_cle, rang)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_outils_demarrage_outil "
        "ON outils_demarrage(outil_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_outils_demarrage_machine "
        "ON outils_demarrage(machine, date_operation)"
    )
