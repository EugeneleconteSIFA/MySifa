"""Changement d'outil : la même référence peut être démontée puis remontée.

Le constat (03/11/2026)
-----------------------
Le changement d'outil refusait un outil monté identique à l'outil démonté.
C'est juste pour une plaque ; pas pour un cliché : un même cliché porte
plusieurs tapis d'encrage (un amalgame, par exemple), et changer de tapis se
saisit en « Changement Cliché » sur la MÊME référence.

Ce que la migration installe
----------------------------
`outil_types.meme_reference` — la nature admet-elle de démonter et remonter
    la même référence ? Un attribut du référentiel, comme `au_demarrage`, pas
    une liste en dur dans le code. Seedé à 1 pour le cliché.
"""

from __future__ import annotations

import sqlite3

NOM = "outils_meme_reference"
DEPEND = ["outils_au_demarrage"]

TYPES_MEME_REFERENCE = ("cliche",)


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    cols = _colonnes(conn, "outil_types")
    if not cols:
        return
    n = 0
    if "meme_reference" not in cols:
        conn.execute(
            "ALTER TABLE outil_types ADD COLUMN meme_reference INTEGER NOT NULL DEFAULT 0"
        )
        for cle in TYPES_MEME_REFERENCE:
            n += conn.execute(
                "UPDATE outil_types SET meme_reference = 1 WHERE cle = ?", (cle,)
            ).rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} nature(s) d'outil remontable(s) sur la même référence.")
