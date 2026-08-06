"""
Déclinaisons de matière et appairage au niveau de la déclinaison.

Extraite de app/core/database.py (ancienne v228) : une migration par fichier,
identifiée par son NOM, pour que deux chantiers parallèles ne se marchent pas dessus.
"""

NOM = "mp_declinaisons_appairage"
DEPEND = ["mp_matiere_prix_par_fournisseur"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mp_grammages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            valeur_gsm REAL NOT NULL UNIQUE,
            label      TEXT,
            ordre      INTEGER NOT NULL DEFAULT 0,
            actif      INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
                       DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS mp_matiere_grammages (
            matiere_id  INTEGER NOT NULL
                        REFERENCES matieres_premieres(id) ON DELETE CASCADE,
            grammage_id INTEGER NOT NULL REFERENCES mp_grammages(id) ON DELETE RESTRICT,
            PRIMARY KEY (matiere_id, grammage_id)
        );

        CREATE TABLE IF NOT EXISTS mp_matiere_declinaison (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere_id     INTEGER NOT NULL
                           REFERENCES matieres_premieres(id) ON DELETE CASCADE,
            laize_id       INTEGER REFERENCES mp_laizes(id) ON DELETE CASCADE,
            grammage_id    INTEGER REFERENCES mp_grammages(id) ON DELETE CASCADE,
            mc_material_id INTEGER REFERENCES mc_material(id) ON DELETE SET NULL,
            created_at     TEXT NOT NULL
                           DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mmd_unique
            ON mp_matiere_declinaison(matiere_id, COALESCE(laize_id,0), COALESCE(grammage_id,0));
        CREATE INDEX IF NOT EXISTS idx_mmd_matiere ON mp_matiere_declinaison(matiere_id);
        CREATE INDEX IF NOT EXISTS idx_mmd_mc ON mp_matiere_declinaison(mc_material_id);
        """
    )
    _prix228 = {r["name"] for r in conn.execute("PRAGMA table_info(mp_matiere_prix)").fetchall()}
    if _prix228 and "declinaison_id" not in _prix228:
        conn.execute("ALTER TABLE mp_matiere_prix ADD COLUMN declinaison_id INTEGER")
    if _prix228 and "grammage_id" not in _prix228:
        conn.execute("ALTER TABLE mp_matiere_prix ADD COLUMN grammage_id INTEGER")

    # Une déclinaison par couple (matière, laize) déjà présent dans les prix.
    _n_decl = 0
    for _r in conn.execute(
        "SELECT DISTINCT matiere_id, laize_id FROM mp_matiere_prix"
    ).fetchall():
        conn.execute(
            """INSERT OR IGNORE INTO mp_matiere_declinaison (matiere_id, laize_id)
               VALUES (?,?)""",
            (int(_r["matiere_id"]), _r["laize_id"]),
        )
        _n_decl += 1
    conn.execute(
        """UPDATE mp_matiere_prix SET declinaison_id = (
               SELECT d.id FROM mp_matiere_declinaison d
                WHERE d.matiere_id = mp_matiere_prix.matiere_id
                  AND COALESCE(d.laize_id,0) = COALESCE(mp_matiere_prix.laize_id,0)
                  AND d.grammage_id IS NULL)
            WHERE declinaison_id IS NULL"""
    )

    # L'unicité d'un prix se joue désormais sur (déclinaison, fournisseur) :
    # l'ancien index ignorait le grammage et refusait deux grammages du même
    # adhésif chez le même fournisseur.
    conn.execute("DROP INDEX IF EXISTS idx_mmp_unique")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mmp_decl_unique "
        "ON mp_matiere_prix(declinaison_id, COALESCE(fournisseur_id,0))"
    )

    # Reprise de l'appairage : il ne peut descendre sans ambiguïté que sur une
    # matière qui n'a qu'une seule déclinaison. Les autres sont à réappairer
    # à la main, déclinaison par déclinaison — c'est justement le point que
    # l'appairage au niveau matière ne savait pas exprimer.
    _n_pair, _n_ambigu = 0, 0
    for _m in conn.execute(
        "SELECT id, mc_material_id FROM matieres_premieres WHERE mc_material_id IS NOT NULL"
    ).fetchall():
        _decls = conn.execute(
            "SELECT id FROM mp_matiere_declinaison WHERE matiere_id=?", (int(_m["id"]),)
        ).fetchall()
        if len(_decls) == 1:
            conn.execute(
                "UPDATE mp_matiere_declinaison SET mc_material_id=? WHERE id=?",
                (int(_m["mc_material_id"]), int(_decls[0]["id"])),
            )
            _n_pair += 1
        elif len(_decls) > 1:
            _n_ambigu += 1

    conn.commit()
