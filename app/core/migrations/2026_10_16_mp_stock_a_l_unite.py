"""
Matières tenues à l'unité (`matieres_premieres.stock_a_l_unite`).

Les bagues s'achètent à l'unité et les cartons du fournisseur de détail au lot,
un lot qui change d'une commande à l'autre : sans conditionnement fixe, la
réception RVGI restait « à compléter » et le déstockage bloquait. Une matière
tenue à l'unité a une palette d'une unité (voir `app/services/stock_a_l_unite.py`).

Reprise (16/10/2026, demande d'Eugène) : les mandrins de la sous-section
« Bague » ou dont la désignation commence par « Bague », et les cartons dont le
fournisseur principal est RAJA. Le stock en palettes est converti en unités par
le conditionnement en vigueur.
"""

NOM = "mp_stock_a_l_unite"
DEPEND = ["mp_variantes_fournisseur"]

FOURNISSEURS_AU_LOT = ("RAJA",)


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
    if "stock_a_l_unite" not in cols:
        conn.execute(
            "ALTER TABLE matieres_premieres ADD COLUMN stock_a_l_unite INTEGER NOT NULL DEFAULT 0")

    from app.services.stock_a_l_unite import passer_a_l_unite

    ids = [r[0] for r in conn.execute(
        """SELECT id FROM matieres_premieres
           WHERE COALESCE(stock_a_l_unite, 0) = 0
             AND LOWER(TRIM(categorie)) = 'mandrin'
             AND (TRIM(COALESCE(sous_section, '')) = 'Bague' OR designation LIKE 'Bague%')""")]
    marques = ",".join("?" * len(FOURNISSEURS_AU_LOT))
    ids += [r[0] for r in conn.execute(
        """SELECT DISTINCT m.id FROM matieres_premieres m
           JOIN mp_variantes v ON v.matiere_id = m.id AND v.actif = 1 AND v.principal = 1
           JOIN fournisseurs_fsc f ON f.id = v.fournisseur_id
           WHERE COALESCE(m.stock_a_l_unite, 0) = 0
             AND LOWER(TRIM(m.categorie)) = 'carton'
             AND UPPER(TRIM(f.nom)) IN (%s)""" % marques, FOURNISSEURS_AU_LOT)]

    sans_facteur = []
    for mid in ids:
        if passer_a_l_unite(conn, mid) is None:
            sans_facteur.append(mid)
    conn.commit()
    print(f"[MySifa] migration {NOM} : {len(ids)} matière(s) tenue(s) à l'unité"
          + (f", {len(sans_facteur)} sans conditionnement (stock laissé tel quel)" if sans_facteur else "")
          + ".")
