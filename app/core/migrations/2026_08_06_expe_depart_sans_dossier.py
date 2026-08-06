"""
FSC — un départ sans dossier doit être DÉCLARÉ comme tel.

Le constat qui motive cette migration
-------------------------------------
Après le rétablissement du lien expédition ↔ dossier, la mesure sur la base de
production a donné : 2783 départs, dont 19 rattachés. Le lien n'était pas
cassé — l'écran l'écrit correctement — il n'était simplement presque jamais
saisi, l'expéditionnaire passant directement à l'onglet « Saisie manuelle ».

Les tentatives de rattrapage sur l'historique ont toutes échoué :
`ref_sifa` est une référence PRODUIT (10 correspondances sur 2754), et le
rapprochement `arc` ↔ `numero_of` ne donne que 106 liens non ambigus sur 2644.
L'historique n'est pas récupérable. La chaîne ne peut se construire que sur les
départs à venir.

Ce que fait cette migration
---------------------------
Elle ouvre la seule alternative acceptable au rattachement : la déclaration.
Toutes les expéditions ne sortent pas d'une production — stock ancien,
sous-traitance, échantillons, palettes vides — et pour celles-là l'absence de
dossier est la situation normale, exactement comme pour les livraisons
directes du module négoce. Encore faut-il que ce soit DIT, et non déduit du
silence.

À partir de là, un départ est dans l'un de trois états, et non plus deux :

    rattaché              → la chaîne remonte à la matière
    non rattaché, déclaré → chaîne courte mais complète, motif à l'appui
    non rattaché, muet    → rupture

Les 2783 lignes existantes tombent dans le troisième état. C'est la vérité, et
c'est l'indicateur à faire descendre : `GET /api/fsc/controles` le compte.

`sans_dossier_par` / `sans_dossier_le` tracent QUI a déclaré et QUAND. Une
régularisation d'historique est une écriture sur le passé : non tracée, c'est
précisément ce qu'un auditeur cherche.
"""

from __future__ import annotations

import sqlite3

NOM = "expe_depart_sans_dossier"
DEPEND = ["fsc_expe_dossier_vivant"]


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    cols = _colonnes(conn, "expe_departs")

    if "sans_dossier" not in cols:
        conn.execute(
            "ALTER TABLE expe_departs ADD COLUMN sans_dossier INTEGER NOT NULL DEFAULT 0"
        )
    for col in ("sans_dossier_motif", "sans_dossier_note",
                "sans_dossier_par", "sans_dossier_le"):
        if col not in cols:
            conn.execute(f"ALTER TABLE expe_departs ADD COLUMN {col} TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_departs_sans_dossier "
        "ON expe_departs(sans_dossier)"
    )

    # Aucun backfill. Cocher la case à la place des expéditionnaires
    # transformerait 2783 lignes silencieuses en 2783 lignes affirmant
    # « envoi non lié à une production » — une affirmation que personne n'a
    # faite et que rien ne vérifie. C'est la seule chose pire que le silence.
    muets = conn.execute(
        """SELECT COUNT(*) FROM expe_departs
            WHERE TRIM(COALESCE(no_dossier,'')) = ''
              AND planning_entry_id IS NULL
              AND COALESCE(sans_dossier,0) = 0"""
    ).fetchone()[0]

    print(
        f"[MySifa] migration expe_depart_sans_dossier : déclaration activée. "
        f"{muets} départ(s) sans dossier ni déclaration — état de départ, "
        f"à faire descendre. Le rattachement devient obligatoire à la création."
    )
