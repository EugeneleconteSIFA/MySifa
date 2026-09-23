"""Où chaque nature d'outil va chercher sa liste dans le miroir RVGI.

Le constat (22/09/2026, essai atelier)
---------------------------------------
Le référentiel local seedé depuis les fiches techniques ne couvrait que les
plaques. Magnétique, contre-partie et cliché ouvraient un sélecteur vide alors
que les listes existent déjà — dans RVGI, depuis toujours :

- `out_dec`   : 2 668 outils de découpe. C'est le numéro de plaque.
- `out_cyl`   : 124 cylindres, séparés par leur colonne `type` — 2 et 3 les
                magnétiques (identifiés par leur nombre de dents), 4 les
                contre-parties (codes « CP… »), 5 les anilox, 7 les sheeters.
- `mat_mat`   : les matières, dont le type 9 est la famille « Clichés »
                (478 lignes, référencées `code1/code2`).

Ce que la migration installe
----------------------------
Deux colonnes sur `outil_types`, et rien d'autre :

`source_table`  — la table du miroir où chercher. Vide = on ne cherche que
                  dans le référentiel local et les fiches techniques.
`source_types`  — les valeurs de la colonne `type` à retenir, séparées par des
                  virgules. Vide = pas de filtre sur le type.

C'est de la configuration, pas du code : le jour où l'atelier ajoute une
nature (anilox, couteaux), personne n'a à rouvrir un fichier Python pour lui
dire où chercher. Et aucun nom de table RVGI n'est écrit en dur ailleurs —
seul ce seed en contient, comme un référentiel métier le doit.
"""

from __future__ import annotations

import sqlite3

NOM = "changement_outil_sources_rvgi"
DEPEND = ["changement_outil_referentiel"]

# (cle de nature, table du miroir, valeurs de `type` retenues)
SOURCES_SEED = [
    ("plaque",        "out_dec", ""),
    ("magnetique",    "out_cyl", "2,3"),
    ("contre_partie", "out_cyl", "4"),
    ("cliche",        "mat_mat", "9"),
]


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    cols = _colonnes(conn, "outil_types")
    if not cols:
        return  # table absente : la migration dont on dépend n'a rien fait
    if "source_table" not in cols:
        conn.execute("ALTER TABLE outil_types ADD COLUMN source_table TEXT")
    if "source_types" not in cols:
        conn.execute("ALTER TABLE outil_types ADD COLUMN source_types TEXT")

    n = 0
    for cle, table, types in SOURCES_SEED:
        cur = conn.execute(
            """UPDATE outil_types
               SET source_table = ?, source_types = ?
               WHERE cle = ? AND COALESCE(source_table, '') = ''""",
            (table, types, cle),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} nature(s) d'outil rattachée(s) à sa source RVGI.")
