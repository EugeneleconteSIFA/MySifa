"""
Prix d'achat par fournisseur (et par laize quand la matière est laizée).

Extraite de app/core/database.py (ancienne v227) : une migration par fichier,
identifiée par son NOM, pour que deux chantiers parallèles ne se marchent pas dessus.
"""

NOM = "mp_matiere_prix_par_fournisseur"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mp_matiere_prix (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere_id      INTEGER NOT NULL
                            REFERENCES matieres_premieres(id) ON DELETE CASCADE,
            laize_id        INTEGER REFERENCES mp_laizes(id) ON DELETE CASCADE,
            fournisseur_id  INTEGER REFERENCES fournisseurs_fsc(id) ON DELETE SET NULL,
            prix            REAL NOT NULL DEFAULT 0,
            principal       INTEGER NOT NULL DEFAULT 0,
            note            TEXT,
            updated_at      TEXT NOT NULL
                            DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            updated_by_name TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mmp_unique
            ON mp_matiere_prix(matiere_id, COALESCE(laize_id,0), COALESCE(fournisseur_id,0));
        CREATE INDEX IF NOT EXISTS idx_mmp_matiere ON mp_matiere_prix(matiere_id);
        CREATE INDEX IF NOT EXISTS idx_mmp_principal
            ON mp_matiere_prix(matiere_id, principal);
        """
    )

    _LAIZEES227 = ("frontal", "glassine", "complexe")
    _n_prix227 = 0

    def _ins227(mat_id, laize_id, fournisseur_id, prix, principal):
        conn.execute(
            """INSERT OR IGNORE INTO mp_matiere_prix
               (matiere_id, laize_id, fournisseur_id, prix, principal, note, updated_by_name)
               VALUES (?,?,?,?,?,?,?)""",
            (mat_id, laize_id, fournisseur_id, float(prix or 0), 1 if principal else 0,
             "Reprise de l'existant", "migration"),
        )

    # Fournisseurs déjà connus, par (matière, laize).
    _fourn227 = {}
    for _r in conn.execute(
        "SELECT matiere_id, laize_id, fournisseur_id FROM matiere_laize_fournisseurs"
    ).fetchall():
        _fourn227.setdefault((int(_r["matiere_id"]), int(_r["laize_id"])), []).append(
            int(_r["fournisseur_id"])
        )

    for _m in conn.execute(
        """SELECT mp.id, mp.categorie, COALESCE(mp.prix_eur_m2,0) AS prix_m2,
                  COALESCE(mp.prix_par_laize,0) AS par_laize,
                  COALESCE(v.prix_unitaire,0) AS prix_unit
             FROM matieres_premieres mp
             LEFT JOIN mp_valorisation v ON v.matiere_id = mp.id"""
    ).fetchall():
        _mid = int(_m["id"])
        _cat = (_m["categorie"] or "").strip().lower()
        if _cat in _LAIZEES227:
            _laizes = [
                (int(_l["laize_id"]), _l["prix_eur_m2"])
                for _l in conn.execute(
                    "SELECT laize_id, prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=?",
                    (_mid,),
                ).fetchall()
            ]
            if _laizes and int(_m["par_laize"] or 0):
                # Un prix par laize : une ligne par laize et par fournisseur.
                for _lid, _lprix in _laizes:
                    _fs = _fourn227.get((_mid, _lid)) or [None]
                    for _i, _fid in enumerate(_fs):
                        _ins227(_mid, _lid, _fid, _lprix, _i == 0)
                        _n_prix227 += 1
                continue
            # Prix unique toutes laizes : une seule ligne sans laize, avec
            # l'ensemble des fournisseurs connus sur les laizes de la matière.
            _fs = []
            for _lid, _ in _laizes:
                for _fid in _fourn227.get((_mid, _lid)) or []:
                    if _fid not in _fs:
                        _fs.append(_fid)
            for _i, _fid in enumerate(_fs or [None]):
                _ins227(_mid, None, _fid, _m["prix_m2"], _i == 0)
                _n_prix227 += 1
        else:
            _ins227(_mid, None, None, _m["prix_unit"], True)
            _n_prix227 += 1

    conn.commit()
