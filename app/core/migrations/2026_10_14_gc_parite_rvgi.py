"""Nouvel ERP — champs relevés sur les écrans RVGI (captures du 14/10/2026).

En-tête de pièce : contact (« à l'attention de »), transporteur (« mode de
livraison », branché sur les transporteurs de MyExpé), jours et date
d'expédition, franco de port, escompte, acompte, représentant (un compte
MySifa) et sa commission ; pour un BL : récépissé, colis, palettes, poids,
emballage ; pour un marché : date d'ouverture.

Ligne : dates d'expédition et de livraison propres, origine (fabrication,
stock, sous-traitance), laboratoire (renouvellement, création, modification),
référence produit du client, nombre de livraisons prévues, adresse de
livraison propre.

Tiers : représentant, transporteur et jours d'expédition par défaut.
Article : référence produit client, format (laize × avance, dixièmes de mm),
conditionnement, désignation longue.

Numérotation : remise à zéro annuelle, mensuelle ou jamais (RVGI : commandes
et BL en compteur continu, devis en AAMM + compteur mensuel).
"""

NOM = "gc_parite_rvgi"
DEPEND = ["gc_socle", "gc_marches"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    for col, decl in (
        ("contact_id", "INTEGER"), ("transporteur_id", "INTEGER"), ("jours_expedition", "INTEGER NOT NULL DEFAULT 0"),
        ("date_expedition", "TEXT"), ("franco_cents", "INTEGER"), ("escompte_bp", "INTEGER NOT NULL DEFAULT 0"),
        ("acompte_cents", "INTEGER NOT NULL DEFAULT 0"), ("representant_id", "INTEGER"),
        ("commission_bp", "INTEGER NOT NULL DEFAULT 0"), ("recepisse", "TEXT NOT NULL DEFAULT ''"),
        ("nb_colis", "INTEGER"), ("nb_palettes", "INTEGER"), ("poids_g", "INTEGER"),
        ("emballage", "TEXT NOT NULL DEFAULT ''"), ("date_ouverture", "TEXT"),
    ):
        _col(conn, "gc_pieces", col, decl)
    for col, decl in (
        ("date_expedition", "TEXT"), ("origine_prod", "TEXT NOT NULL DEFAULT ''"),
        ("laboratoire", "TEXT NOT NULL DEFAULT ''"), ("ref_client", "TEXT NOT NULL DEFAULT ''"),
        ("nb_livraisons", "INTEGER NOT NULL DEFAULT 1"), ("adresse_livraison_id", "INTEGER"),
    ):
        _col(conn, "gc_pieces_lignes", col, decl)
    for col, decl in (
        ("representant_id", "INTEGER"), ("transporteur_id", "INTEGER"),
        ("jours_expedition", "INTEGER NOT NULL DEFAULT 0"),
    ):
        _col(conn, "gc_tiers", col, decl)
    for col, decl in (
        ("ref_client", "TEXT NOT NULL DEFAULT ''"), ("format_l_dmm", "INTEGER"), ("format_a_dmm", "INTEGER"),
        ("conditionnement", "TEXT NOT NULL DEFAULT ''"), ("designation", "TEXT NOT NULL DEFAULT ''"),
        ("origine_prod", "TEXT NOT NULL DEFAULT ''"),
    ):
        _col(conn, "gc_articles", col, decl)

    _col(conn, "gc_sequences", "reinit", "TEXT NOT NULL DEFAULT 'annuelle'")
    _col(conn, "gc_sequences", "mois", "INTEGER NOT NULL DEFAULT 0")
    # Formats relevés dans RVGI. Les compteurs eux-mêmes se recalent à la reprise.
    for code, fmt, reinit in (
        ("commande", "{N:07}", "jamais"), ("bl", "{N:07}", "jamais"),
        ("devis", "{AA}{MM}{N:03}", "mensuelle"), ("marche", "{N}", "jamais"),
    ):
        conn.execute("UPDATE gc_sequences SET format=?, reinit=? WHERE code=? AND format LIKE '%{AA}{N:05}%'",
                     (fmt, reinit, code))
    conn.execute("UPDATE gc_sequences SET reinit='annuelle' WHERE reinit='' OR reinit IS NULL")
    conn.commit()
