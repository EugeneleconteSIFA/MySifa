"""
Relier les champs matière d'un OF et d'une fiche technique aux RÉFÉRENCES de
MyStock, au lieu de les laisser en texte libre.

Le problème que ça règle
------------------------
« Carton 385 x 385 x 260 mm », « Tube 1500x40 », « THERMIQUE ECO » : ces
valeurs sont tapées à la main depuis toujours, et le déstockage de production
doit ensuite deviner à quelle référence MyStock elles correspondent. C'est le
rôle de `mp_fiche_mapping` — 61 correspondances aujourd'hui, tenues à jour à la
main, et qui listent en creux tout ce qui n'est PAS rattaché. Une frappe près
(« ITASA KA » vs « ITASA jaune KA ») suffit à faire sortir un besoin matière
faux, et l'erreur se voit à l'inventaire, pas à l'écran.

Rattacher à la SAISIE plutôt qu'après coup supprime la devinette : on choisit
une référence, et le texte imprimé sur l'OF est sa désignation. Une seule
vérité. `mp_fiche_mapping` reste — il continue de servir aux documents venus
d'Access, qui eux n'ont que du texte.

Six familles, les mêmes que `mp_fiche_mapping._KINDS` : support, glassine,
adhesif, carton, mandrin, palette.

Trois choix à ne pas défaire
----------------------------
1. **La colonne texte reste.** Elle porte la désignation de la référence
   choisie, et c'est elle qu'impriment l'OF et la fiche. La supprimer casserait
   les lecteurs qui joignent en texte (Besoins matières lit `ft_support`,
   `ft_cartons`…) et priverait les documents Access de leur seule valeur.

2. **La palette tient dans UN champ.** `palette_europe` et `palette_perdues`,
   posées le matin même par la migration `of_fiches_creation_mysifa`, faisaient
   du type de palette deux compteurs — alors que c'est un choix parmi des
   références (« Pallet Europe », « Pallet Perdue », « Anti-bactérienne »).
   Elles restent en base, vides et inutilisées, plutôt que d'être supprimées :
   une colonne qu'on retire ne revient pas si un déploiement traîne.

3. **`brouillon` sur `matieres_premieres`.** L'ADV qui saisit un OF doit
   pouvoir créer la référence qui manque sans attendre — sinon elle retape du
   texte libre, et on revient au point de départ. Mais une matière sans prix ni
   laize fausserait la valorisation en silence : le drapeau la fait remonter
   dans « matières à compléter » jusqu'à ce que MyStock la renseigne.
"""

NOM = "of_fiche_references_matiere"
DEPEND = ["of_fiches_creation_mysifa", "rvgi_rattachements"]


# (colonne d'id, colonne texte, kind du référentiel)
_LIENS_OF = [
    ("matiere_ref_id",  "matiere",      "support"),
    ("glassine_ref_id", "glassine",     "glassine"),
    ("adhesif_ref_id",  "adhesif_label", "adhesif"),
    ("carton_ref_id",   "cartons_type", "carton"),
    ("mandrin_ref_id",  "mandrins_dia", "mandrin"),
    ("palette_ref_id",  "palette_type", "palette"),
]

_LIENS_FT = [
    ("support_ref_id",  "support",      "support"),
    ("glassine_ref_id", "glassine",     "glassine"),
    ("adhesif_ref_id",  "adhesif",      "adhesif"),
    ("carton_ref_id",   "cartons",      "carton"),
    ("mandrin_ref_id",  "mandrin_dia",  "mandrin"),
    ("palette_ref_id",  "palette_type", "palette"),
]


def _colonnes(conn, table):
    return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}


def _ajouter(conn, table, colonnes):
    presentes = _colonnes(conn, table)
    n = 0
    for nom, typ in colonnes:
        if nom in presentes:
            continue
        conn.execute('ALTER TABLE "%s" ADD COLUMN %s %s' % (table, nom, typ))
        n += 1
    return n


def _rattacher_existant(conn, table, liens):
    """Pose les `*_ref_id` des documents déjà en base, via `mp_fiche_mapping`.

    C'est un cadeau : les correspondances existent déjà, personne ne les a
    encore vues appliquées sur un document. On ne touche que les lignes dont
    l'id est vide — une reprise ne doit jamais défaire un choix humain.
    """
    if "mp_fiche_mapping" not in {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return 0
    cols = _colonnes(conn, table)
    total = 0
    for col_id, col_txt, kind in liens:
        if col_id not in cols or col_txt not in cols:
            continue
        total += conn.execute(
            'UPDATE "%s" SET %s = ('
            "   SELECT m.matiere_id FROM mp_fiche_mapping m"
            "    WHERE m.kind = ?"
            "      AND LOWER(TRIM(m.source_value)) = LOWER(TRIM(%s))"
            "    LIMIT 1)"
            " WHERE %s IS NULL"
            "   AND %s IS NOT NULL AND TRIM(%s) <> ''"
            "   AND EXISTS (SELECT 1 FROM mp_fiche_mapping m2"
            "                WHERE m2.kind = ?"
            "                  AND LOWER(TRIM(m2.source_value)) = LOWER(TRIM(%s)))"
            % (table, col_id, col_txt, col_id, col_txt, col_txt, col_txt),
            (kind, kind),
        ).rowcount
    return total


def appliquer(conn):
    n_of = _ajouter(conn, "of_imports", [
        ("matiere_ref_id",  "INTEGER"),
        ("glassine_ref_id", "INTEGER"),
        ("adhesif_ref_id",  "INTEGER"),
        ("carton_ref_id",   "INTEGER"),
        ("mandrin_ref_id",  "INTEGER"),
        ("palette_ref_id",  "INTEGER"),
        ("palette_type",    "TEXT"),
        ("nb_palettes",     "INTEGER"),
    ])
    n_ft = _ajouter(conn, "fiches_techniques", [
        ("support_ref_id",  "INTEGER"),
        ("glassine_ref_id", "INTEGER"),
        ("adhesif_ref_id",  "INTEGER"),
        ("carton_ref_id",   "INTEGER"),
        ("mandrin_ref_id",  "INTEGER"),
        ("palette_ref_id",  "INTEGER"),
        # Le grammage de la matière (149 g sur la fiche 623/0014). La fiche le
        # portait à l'impression mais pas en base : le générateur PDF écrivait
        # `qte_au_mille` dans la case « Grammage », en millilitres.
        ("grammage",        "REAL"),
    ])
    n_mp = _ajouter(conn, "matieres_premieres", [
        ("brouillon",     "INTEGER"),
        ("brouillon_par", "TEXT"),
        ("brouillon_le",  "TEXT"),
    ])
    conn.execute(
        "UPDATE matieres_premieres SET brouillon = 0 WHERE brouillon IS NULL"
    )

    # Les deux compteurs de palettes posés le matin même deviennent un type.
    # Ils sont normalement vides ; s'ils ne le sont pas, on ne perd rien.
    cols_of = _colonnes(conn, "of_imports")
    if {"palette_europe", "palette_perdues"} <= cols_of:
        conn.execute(
            "UPDATE of_imports "
            "   SET palette_type = CASE WHEN COALESCE(palette_europe,0) > 0 "
            "                          THEN 'EUROPE' ELSE 'PERDUE' END,"
            "       nb_palettes  = COALESCE(palette_europe, palette_perdues) "
            " WHERE palette_type IS NULL "
            "   AND (COALESCE(palette_europe,0) > 0 OR COALESCE(palette_perdues,0) > 0)"
        )

    for col, cols_idx in (
        ("of_imports", ["matiere_ref_id", "carton_ref_id", "palette_ref_id"]),
        ("fiches_techniques", ["support_ref_id", "carton_ref_id", "palette_ref_id"]),
    ):
        for c in cols_idx:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_%s_%s ON %s(%s)"
                         % (col, c, col, c))
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mp_brouillon ON matieres_premieres(brouillon)"
    )

    repris_of = _rattacher_existant(conn, "of_imports", _LIENS_OF)
    repris_ft = _rattacher_existant(conn, "fiches_techniques", _LIENS_FT)

    conn.commit()
    print("[MySifa] migration of_fiche_references_matiere : "
          "%d colonne(s) sur of_imports, %d sur fiches_techniques, %d sur "
          "matieres_premieres ; %d lien(s) posé(s) sur les OF et %d sur les "
          "fiches depuis les correspondances existantes."
          % (n_of, n_ft, n_mp, repris_of, repris_ft))
