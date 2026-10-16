"""
Unité de comptage d'une matière tenue à l'unité (`matieres_premieres.unite_comptage`).

Une bague se compte en bagues, pas en tubes : la catégorie « mandrin » ne dit
pas ce qu'on compte. L'unité se choisit sur la fiche parmi
`config.STOCK_UNITES_COMPTAGE` ; vide, c'est la première de la catégorie.

Reprise : les mandrins tenus à l'unité de la sous-section « Bague » ou dont la
désignation commence par « Bague » se comptent en bagues.
"""

NOM = "mp_unite_comptage"
DEPEND = ["mp_stock_a_l_unite"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
    if "unite_comptage" not in cols:
        conn.execute("ALTER TABLE matieres_premieres ADD COLUMN unite_comptage TEXT")
    n = conn.execute(
        """UPDATE matieres_premieres SET unite_comptage = 'bague'
           WHERE unite_comptage IS NULL AND COALESCE(stock_a_l_unite, 0) = 1
             AND LOWER(TRIM(categorie)) = 'mandrin'
             AND (TRIM(COALESCE(sous_section, '')) = 'Bague' OR designation LIKE 'Bague%')"""
    ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} matière(s) comptée(s) en bagues.")
