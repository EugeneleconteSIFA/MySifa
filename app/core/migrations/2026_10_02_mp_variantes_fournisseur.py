"""
Variantes fournisseur d'une matière MyStock.

Une matière MyStock porte le LIBELLÉ COMMERCIAL : nature du support, grammage,
type de colle, protecteur, FSC — sans aucune référence. La même matière peut
être livrée par plusieurs fournisseurs, et par un même fournisseur sous
plusieurs articles. Chacune de ces déclinaisons est une VARIANTE : elle porte
le LIBELLÉ TECHNIQUE (le même, avec les références de colle, de glassine,
d'article fournisseur), sa référence RVGI et sa longueur de bobine.

Une seule variante est PRINCIPALE par matière. Ce principal n'est pas une
seconde vérité à côté de Coûts matières : il pilote `mp_matiere_prix.principal`
(le prix en vigueur), et un changement de principal dans Coûts matières le
met à jour en retour. Voir `app/services/mp_variantes.py`.

`erp_article_matiere.variante_id` dit quelle variante un article RVGI désigne :
une réception sait ainsi quel fournisseur a livré.

Reprise : une variante par couple (matière, fournisseur) déjà présent dans les
prix, et une par article RVGI déjà apparié. Le principal reprend celui des prix.
Libellé technique initial = désignation de la matière, à compléter.
"""

from datetime import datetime

NOM = "mp_variantes_fournisseur"
DEPEND = ["reception_rvgi_socle"]


def _colonnes(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mp_variantes (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere_id         INTEGER NOT NULL,
            fournisseur_id     INTEGER,
            libelle_technique  TEXT    NOT NULL,
            ref_fournisseur    TEXT,
            rvgi_code1         TEXT,
            rvgi_code2         TEXT,
            rvgi_type_code     INTEGER,
            ml_bobine          REAL,
            principal          INTEGER NOT NULL DEFAULT 0,
            actif              INTEGER NOT NULL DEFAULT 1,
            note               TEXT,
            created_at         TEXT,
            created_by_name    TEXT,
            updated_at         TEXT,
            updated_by_name    TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mp_variantes_matiere ON mp_variantes(matiere_id);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_mp_variantes_principal
            ON mp_variantes(matiere_id) WHERE principal = 1 AND actif = 1;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_mp_variantes_rvgi
            ON mp_variantes(rvgi_code1, rvgi_code2, rvgi_type_code)
            WHERE rvgi_code1 IS NOT NULL AND actif = 1;
        """
    )
    if "variante_id" not in _colonnes(conn, "erp_article_matiere"):
        conn.execute("ALTER TABLE erp_article_matiere ADD COLUMN variante_id INTEGER")

    deja = conn.execute("SELECT COUNT(*) FROM mp_variantes").fetchone()[0]
    if deja:
        conn.commit()
        return

    now = datetime.now().isoformat(timespec="seconds")
    designation = {
        r[0]: (r[1] or r[2] or "").strip()
        for r in conn.execute("SELECT id, designation, reference FROM matieres_premieres").fetchall()
    }

    # 1. Une variante par (matière, fournisseur) présent dans les prix.
    #    Principal = le fournisseur principal sur le plus grand nombre de déclinaisons.
    couples = conn.execute(
        """SELECT matiere_id, fournisseur_id, SUM(principal) AS n_principal
             FROM mp_matiere_prix
            WHERE fournisseur_id IS NOT NULL
            GROUP BY matiere_id, fournisseur_id"""
    ).fetchall()
    meilleur = {}
    for mid, fid, n in couples:
        if n and (mid not in meilleur or n > meilleur[mid][1]):
            meilleur[mid] = (fid, n)
    crees = 0
    for mid, fid, _n in couples:
        if mid not in designation:
            continue
        conn.execute(
            """INSERT INTO mp_variantes
                   (matiere_id, fournisseur_id, libelle_technique, principal, actif,
                    created_at, created_by_name, note)
               VALUES (?,?,?,?,1,?,?,?)""",
            (mid, fid, designation[mid], 1 if meilleur.get(mid, (None,))[0] == fid else 0,
             now, "Migration", "Reprise des prix fournisseur : libellé technique à compléter."),
        )
        crees += 1

    # 2. Les articles RVGI déjà appariés : rattachés à la variante de leur
    #    fournisseur (code1 = numéro fournisseur RVGI), créée au besoin.
    num_fou = {
        int(r[1]): r[0]
        for r in conn.execute(
            "SELECT id, rvgi_numero FROM fournisseurs_fsc WHERE rvgi_numero IS NOT NULL"
        ).fetchall()
    }
    rattaches = 0
    for code1, code2, type_code, mid in conn.execute(
        "SELECT code1, code2, type_code, matiere_id FROM erp_article_matiere"
    ).fetchall():
        if mid not in designation:
            continue
        fid = num_fou.get(int(code1)) if str(code1).isdigit() and str(code1) != "1" else None
        v = conn.execute(
            """SELECT id FROM mp_variantes
                WHERE matiere_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)
                  AND rvgi_code1 IS NULL
                ORDER BY principal DESC, id LIMIT 1""",
            (mid, fid),
        ).fetchone()
        if v:
            vid = v[0]
            conn.execute(
                "UPDATE mp_variantes SET rvgi_code1=?, rvgi_code2=?, rvgi_type_code=? WHERE id=?",
                (code1, code2, type_code, vid),
            )
        else:
            vid = conn.execute(
                """INSERT INTO mp_variantes
                       (matiere_id, fournisseur_id, libelle_technique, rvgi_code1, rvgi_code2,
                        rvgi_type_code, principal, actif, created_at, created_by_name, note)
                   VALUES (?,?,?,?,?,?,0,1,?,?,?)""",
                (mid, fid, designation[mid], code1, code2, type_code, now, "Migration",
                 "Reprise de l'appariement RVGI : libellé technique à compléter."),
            ).lastrowid
            crees += 1
        conn.execute(
            "UPDATE erp_article_matiere SET variante_id=? WHERE code1=? AND code2=? AND type_code=?",
            (vid, code1, code2, type_code),
        )
        rattaches += 1

    # 3. Une matière à variante unique a ce fournisseur pour principal.
    for (mid,) in conn.execute(
        """SELECT matiere_id FROM mp_variantes WHERE actif=1
            GROUP BY matiere_id HAVING COUNT(*)=1 AND SUM(principal)=0"""
    ).fetchall():
        conn.execute("UPDATE mp_variantes SET principal=1 WHERE matiere_id=? AND actif=1", (mid,))

    conn.commit()
    print(f"[MySifa] migration {NOM} : {crees} variante(s) créée(s), "
          f"{rattaches} article(s) RVGI rattaché(s).")
