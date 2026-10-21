"""
Catégories de notes de frais, taux de TVA et indemnités kilométriques.

La catégorie d'une note de frais était un texte libre. Elle devient un
référentiel `ndf_categories`, éditable par la comptabilité dans Coffre RH ›
Catégories, seedé avec les natures de la feuille de frais Excel de SIFA
(Repas, Déplacement, Divers, KM). Le taux de TVA y est un défaut : la note
porte son propre taux, puisqu'un même repas peut être à 10 % ou à 20 %.

Une catégorie `saisie='km'` se saisit en kilomètres ; le montant vaut
distance × `taux_km`. Le taux seedé est celui du barème fiscal 5 CV jusqu'à
5 000 km, à confirmer par la comptabilité.

Sur `notes_de_frais` : `categorie_id`, `taux_tva`, `montant_ht`,
`distance_km`, `taux_km` (le taux appliqué, figé à la saisie) et `ville`.
`categorie` reste le libellé au moment de la saisie : les anciennes notes à
texte libre s'affichent telles quelles. Rejouable.
"""

NOM = "ndf_categories"

_SEED = (
    # code, libelle, saisie, taux_tva, taux_km, ordre
    ("repas", "Repas", "montant", 10.0, None, 10),
    ("deplacement", "Déplacement", "montant", 20.0, None, 20),
    ("divers", "Divers", "montant", 20.0, None, 30),
    ("km", "Indemnités kilométriques", "km", 0.0, 0.636, 40),
)


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ndf_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            libelle TEXT NOT NULL,
            saisie TEXT NOT NULL DEFAULT 'montant',
            taux_tva REAL NOT NULL DEFAULT 20,
            taux_km REAL,
            ordre INTEGER NOT NULL DEFAULT 100,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )"""
    )
    for code, libelle, saisie, taux_tva, taux_km, ordre in _SEED:
        conn.execute(
            """INSERT OR IGNORE INTO ndf_categories
               (code, libelle, saisie, taux_tva, taux_km, ordre)
               VALUES (?,?,?,?,?,?)""",
            (code, libelle, saisie, taux_tva, taux_km, ordre),
        )

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "notes_de_frais" in tables:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(notes_de_frais)").fetchall()}
        for col, decl in (
            ("categorie_id", "INTEGER"),
            ("taux_tva", "REAL"),
            ("montant_ht", "REAL"),
            ("distance_km", "REAL"),
            ("taux_km", "REAL"),
            ("ville", "TEXT"),
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE notes_de_frais ADD COLUMN {col} {decl}")
    conn.commit()
