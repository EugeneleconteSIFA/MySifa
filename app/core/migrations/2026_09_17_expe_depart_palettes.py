"""
MyExpé — un départ peut partir sur plusieurs types de palettes.

Pourquoi
--------
Un même lot part couramment sur des palettes Europe ET des palettes perdues.
`expe_departs` ne portait qu'un type (`type_palette_matiere_id`) et un nombre
(`nb_palette`) : l'expéditionnaire devait choisir, et le suivi des palettes
Europe comptait alors soit trop, soit rien.

Ce que fait la migration
------------------------
- Table `expe_depart_palettes` : le détail du colisage, une ligne par type.
  Elle n'est remplie que pour un départ multi-types (2 lignes ou plus) ; un
  départ mono-type reste décrit par ses colonnes historiques, inchangées.
- Colonne `expe_departs.nb_palette_europe` : le nombre de palettes Europe d'un
  départ multi-types. NULL sinon — le suivi Europe retombe alors sur
  `nb_palette`, comme avant.

`nb_palette` reste le TOTAL du départ (tarification, pilotage, portail) et
`type_palette_matiere_id` le type de la première ligne : aucune requête
existante n'a à changer de sens.
"""

from __future__ import annotations

import sqlite3

NOM = "expe_depart_palettes"


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS expe_depart_palettes (
               id                      INTEGER PRIMARY KEY AUTOINCREMENT,
               depart_id               INTEGER NOT NULL
                                       REFERENCES expe_departs(id) ON DELETE CASCADE,
               ordre                   INTEGER NOT NULL DEFAULT 0,
               type_palette_matiere_id INTEGER NOT NULL
                                       REFERENCES matieres_premieres(id),
               nb_palette              REAL
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_dp_depart ON expe_depart_palettes(depart_id)"
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
    if "nb_palette_europe" not in cols:
        conn.execute("ALTER TABLE expe_departs ADD COLUMN nb_palette_europe REAL")
    conn.commit()
    print(
        "[MySifa] migration expe_depart_palettes : un départ peut désormais "
        "porter plusieurs types de palettes."
    )
