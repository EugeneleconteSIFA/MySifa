"""
Paramétrage de prix porté par la déclinaison MyStock.

Jusqu'ici, seule une fiche de la base « Coûts matières » savait comment un prix
d'achat devient un coût au m² : poids, devise, base de prix, incidence des taxes,
transport d'import. Une déclinaison MyStock devait donc être appairée à une fiche
pour être devisée.

Ces réglages descendent sur la déclinaison elle-même. Une matière MyStock se
suffit à elle-même : son prix vient de son fournisseur principal, ses réglages
vivent ici, son coût se calcule sans passer par la base historique.

Reprise : une déclinaison déjà appairée hérite des réglages de sa fiche, pour que
personne ne perde son paramétrage. Les autres partent sur des valeurs déduites de
la catégorie (une matière laizée se tarife au m², un adhésif au kilo) et du
grammage déjà déclaré.
"""

NOM = "mp_declinaison_parametrage_prix"
DEPEND = ["mp_declinaisons_appairage"]

_LAIZEES = ("frontal", "glassine", "complexe")

_COLONNES = (
    ("weight_per_m2", "REAL NOT NULL DEFAULT 0"),
    ("weight_gsm", "INTEGER"),
    ("price_currency", "TEXT NOT NULL DEFAULT 'EUR'"),
    ("price_basis", "TEXT NOT NULL DEFAULT 'PER_KG'"),
    ("tax_incidence", "REAL NOT NULL DEFAULT 1"),
    ("is_imported", "INTEGER NOT NULL DEFAULT 0"),
    ("transport_mode", "TEXT NOT NULL DEFAULT 'AMOUNT'"),
    ("transport_unit_price", "REAL NOT NULL DEFAULT 0"),
    ("transport_pct", "REAL NOT NULL DEFAULT 0"),
    # 0 tant que personne n'a ouvert la page : sert à signaler « à paramétrer »
    # dans la liste, sans confondre avec un réglage volontairement à zéro.
    ("parametre", "INTEGER NOT NULL DEFAULT 0"),
    ("updated_at", "TEXT"),
    ("updated_by_name", "TEXT"),
)


def appliquer(conn):
    existantes = {r["name"] for r in conn.execute(
        "PRAGMA table_info(mp_matiere_declinaison)"
    ).fetchall()}
    for nom, ddl in _COLONNES:
        if nom not in existantes:
            conn.execute(f"ALTER TABLE mp_matiere_declinaison ADD COLUMN {nom} {ddl}")

    # 1. Les déclinaisons appairées héritent des réglages de leur fiche.
    #    On vérifie les colonnes avant de les lire : la reprise est un confort,
    #    elle ne doit pas empêcher la migration de passer sur une base dont la
    #    table mc_material serait plus ancienne.
    mc_cols = {r["name"] for r in conn.execute("PRAGMA table_info(mc_material)").fetchall()}
    base_reprise = {
        "weight_per_m2", "weight_gsm", "price_currency",
        "price_basis", "tax_incidence", "is_imported",
    }
    if base_reprise <= mc_cols:
        conn.execute(
            """UPDATE mp_matiere_declinaison SET
                   weight_per_m2  = COALESCE((SELECT m.weight_per_m2  FROM mc_material m WHERE m.id = mc_material_id), weight_per_m2),
                   weight_gsm     = COALESCE((SELECT m.weight_gsm     FROM mc_material m WHERE m.id = mc_material_id), weight_gsm),
                   price_currency = COALESCE((SELECT m.price_currency FROM mc_material m WHERE m.id = mc_material_id), price_currency),
                   price_basis    = COALESCE((SELECT m.price_basis    FROM mc_material m WHERE m.id = mc_material_id), price_basis),
                   tax_incidence  = COALESCE((SELECT m.tax_incidence  FROM mc_material m WHERE m.id = mc_material_id), tax_incidence),
                   is_imported    = COALESCE((SELECT m.is_imported    FROM mc_material m WHERE m.id = mc_material_id), is_imported),
                   parametre      = 1
                WHERE mc_material_id IS NOT NULL"""
        )
    if {"transport_mode", "transport_unit_price", "transport_pct"} <= mc_cols:
        conn.execute(
            """UPDATE mp_matiere_declinaison SET
                   transport_mode       = COALESCE((SELECT m.transport_mode       FROM mc_material m WHERE m.id = mc_material_id), transport_mode),
                   transport_unit_price = COALESCE((SELECT m.transport_unit_price FROM mc_material m WHERE m.id = mc_material_id), transport_unit_price),
                   transport_pct        = COALESCE((SELECT m.transport_pct        FROM mc_material m WHERE m.id = mc_material_id), transport_pct)
                WHERE mc_material_id IS NOT NULL"""
        )

    # 2. Les autres : base de prix déduite de la catégorie. Une matière laizée se
    #    tarife déjà au m², un adhésif au kilo — même postulat que
    #    mystock_price_for_row.
    marques = ",".join("?" for _ in _LAIZEES)
    conn.execute(
        f"""UPDATE mp_matiere_declinaison SET price_basis='PER_M2'
             WHERE mc_material_id IS NULL
               AND matiere_id IN (SELECT id FROM matieres_premieres
                                   WHERE LOWER(categorie) IN ({marques}))""",
        _LAIZEES,
    )

    # 3. Le grammage déjà déclaré vaut poids : 22 g/m² = 0,022 kg/m². Sans lui,
    #    un prix au kilo ne peut pas devenir un coût au m².
    conn.execute(
        """UPDATE mp_matiere_declinaison SET
               weight_gsm    = (SELECT g.valeur_gsm FROM mp_grammages g WHERE g.id = grammage_id),
               weight_per_m2 = ROUND((SELECT g.valeur_gsm FROM mp_grammages g WHERE g.id = grammage_id) / 1000.0, 6)
            WHERE grammage_id IS NOT NULL
              AND COALESCE(weight_per_m2, 0) = 0"""
    )

    conn.commit()
