"""
Source de vérité des OF et des fiches techniques.

La validation posée le 5 août verrouille le déstockage : tant que l'OF et la
fiche technique n'ont pas été relus, aucune matière ne sort du stock. Le verrou
tenait, mais la validation ne se périmait jamais. Un OF validé lundi sur
18 000 étiquettes, dont Access corrigeait la quantité mardi, restait affiché
« validé par X » et déstockait 22 000 étiquettes que personne n'avait relues.
La validation portait sur la ligne, pas sur son contenu.

Trois manques à combler, et cette migration pose les colonnes des trois.

1. `invalide_at` / `invalide_motif` — quand la validation est retirée
   automatiquement parce qu'un chiffre a bougé, il faut pouvoir dire lequel.
   Une pastille qui repasse au rouge sans explication sera recochée sans être
   relue, et on aura fabriqué une case à cocher de plus.

2. `champs_manuels` — la liste JSON des colonnes dont la valeur vient d'un
   humain (saisie dans MySifa, ou lecture d'un vrai PDF d'OF). Access n'a plus
   le droit de les écraser. Jusqu'ici la protection existait au niveau du
   DOCUMENT côté OF (un PDF gelait tout l'OF, y compris les colonnes vides) et
   n'existait pas du tout côté fiches techniques, où chaque sync écrasait
   intégralement la ligne — correction atelier de la veille comprise. Au niveau
   du CHAMP, les deux règles d'Eugène tiennent ensemble : le document le plus
   récent fait foi, sauf sur ce qu'un humain a saisi.

3. `documents_valeurs_historique` — qui a changé quoi, quand, et depuis quelle
   source. Sans ce journal, un stock faux ne s'explique pas : on voit la
   quantité d'aujourd'hui, jamais celle qui a servi au calcul.

Enfin `mp_mouvements` reçoit `of_import_id` et `fiche_id` : un mouvement de
déstockage disait de quel dossier il venait, pas sur quels documents il avait
été calculé.

Reprise des données existantes
------------------------------
`champs_manuels` est rempli pour les OF qui portent déjà un PDF ou un
`imported_by` humain : leurs colonnes renseignées deviennent protégées, ce qui
reproduit exactement le comportement actuel (`_of_purement_access`) sans
geler les colonnes vides, que le pont pourra désormais compléter.

Les fiches techniques ne reçoivent rien : aucune colonne ne permet de savoir
lesquelles ont été corrigées à la main avant aujourd'hui — l'upsert Access
écrasait tout sans laisser de trace. Elles partent donc sans protection, et
c'est le journal qui rendra visible ce qu'Access modifie à partir de
maintenant. Inventer une protection rétroactive figerait des valeurs dont on
ne sait pas si elles sont bonnes.
"""
import json

NOM = "documents_source_verite"
DEPEND = ["validation_of_et_fiches", "destockage_production_mouvements"]

# Colonnes ajoutées aux deux tables de documents.
_COLONNES_DOC = (
    ("champs_manuels", "TEXT"),
    ("invalide_at", "TEXT"),
    ("invalide_motif", "TEXT"),
)

_TABLES_DOC = ("of_imports", "fiches_techniques")

# Champs de l'OF qui alimentent le calcul de déstockage, figés à la date de
# cette migration. La liste vivante est dans app/services/documents_verite.py :
# une migration ne doit pas changer de comportement parce que le service a
# évolué six mois plus tard.
_CALCUL_OF_A_CE_JOUR = (
    "reference", "machine", "format", "laize", "matiere", "glassine",
    "adhesif_label", "ref_adhesif", "qte_adhesif_g", "qte_adhesif_kg",
    "qte_au_mille", "qte_etiquettes", "qte_bobines", "metrage",
    "conditionnement", "nb_cartons", "nb_mandrins", "nb_tubes",
    "mandrins_dia", "mandrin_longueur", "cartons_type",
)


def _colonnes(conn, table) -> set:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    # ── 1. Colonnes sur les deux tables de documents ──────────────────
    for table in _TABLES_DOC:
        cols = _colonnes(conn, table)
        if not cols:
            continue  # table absente sur cette base : rien à faire
        for nom, ddl in _COLONNES_DOC:
            if nom not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {ddl}")
        # `imported_by` existe sur of_imports depuis l'origine ; le pont l'écrit
        # déjà sur les fiches, mais rien ne garantit la colonne sur une base
        # ancienne où aucune fiche n'est encore passée par Access.
        if "imported_by" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN imported_by TEXT")

    # ── 2. Journal des valeurs ────────────────────────────────────────
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents_valeurs_historique (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            table_nom   TEXT    NOT NULL,   -- 'of_imports' | 'fiches_techniques'
            doc_id      INTEGER NOT NULL,
            champ       TEXT    NOT NULL,
            avant       TEXT,
            apres       TEXT,
            origine     TEXT    NOT NULL,   -- 'access_bridge' | 'manuel' | 'import_pdf'
            auteur      TEXT,
            at          TEXT    NOT NULL,
            -- Le document était-il validé au moment du changement ? C'est la
            -- seule colonne qui distingue une correction anodine d'un chiffre
            -- modifié sous une validation déjà acquise.
            etait_valide INTEGER NOT NULL DEFAULT 0,
            -- Renseigné quand le changement a été REFUSÉ parce que la valeur
            -- vient d'un humain : le conflit reste visible au lieu d'être
            -- ignoré en silence comme aujourd'hui.
            refuse      INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_doc_valeurs_hist_doc "
        "ON documents_valeurs_historique(table_nom, doc_id, at)"
    )

    # ── 3. Documents sources d'un mouvement de déstockage ─────────────
    cols_mvt = _colonnes(conn, "mp_mouvements")
    if cols_mvt:
        for nom in ("of_import_id", "fiche_id"):
            if nom not in cols_mvt:
                conn.execute(f"ALTER TABLE mp_mouvements ADD COLUMN {nom} INTEGER")

    # ── 4. Reprise : protéger les OF déjà touchés par un humain ───────
    repris = 0
    cols_of = _colonnes(conn, "of_imports")
    if cols_of and "champs_manuels" in cols_of:
        calcul = [c for c in _CALCUL_OF_A_CE_JOUR if c in cols_of]
        rows = conn.execute(
            "SELECT * FROM of_imports WHERE champs_manuels IS NULL"
        ).fetchall()
        for row in rows:
            a_un_pdf = bool((row["pdf_filename"] or "").strip())
            par_le_pont = (row["imported_by"] or "").strip() == "access_bridge"
            if not a_un_pdf and par_le_pont:
                continue  # OF purement Access : rien à protéger
            proteges = [
                c for c in calcul
                if row[c] is not None and str(row[c]).strip() != ""
            ]
            if not proteges:
                continue
            conn.execute(
                "UPDATE of_imports SET champs_manuels=? WHERE id=?",
                (json.dumps(proteges), row["id"]),
            )
            repris += 1

    conn.commit()
    print(
        "[MySifa] migration documents_source_verite : journal des valeurs créé, "
        f"{repris} OF déjà relus par un humain protégés champ par champ."
    )
