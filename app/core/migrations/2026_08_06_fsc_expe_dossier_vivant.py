"""
FSC — le lien expédition ↔ dossier redevient vivant.

Le problème
-----------
`expe_departs.no_dossier` a été créée par la migration historique 222
(`fsc_expe_departs_dossier`), remplie une seule fois par backfill depuis
`ref_sifa`, puis plus jamais écrite : ni l'INSERT de création d'un départ, ni
le PUT de modification, ni aucune page de MyExpé ne la touchent. Tout départ
créé depuis cette migration arrive donc avec le champ vide.

Conséquence pour un audit FSC : le traceur (`app/routers/traca.py`) et la
mention à porter sur le document de vente (`app/routers/fsc_negoce.py`)
remontent au dossier par ce champ. Un auditeur qui part d'un bon de livraison
récent obtient « Cette expédition n'est rattachée à aucun dossier » — la chaîne
de contrôle casse au deuxième maillon, alors que la matière, elle, est bien
tracée jusqu'au certificat fournisseur.

Le lien existait pourtant déjà. Le formulaire d'expédition écrit
`planning_entry_id`, une vraie clé étrangère vers `planning_entries`, et il est
correctement alimenté depuis sa création. Simplement, aucun des modules FSC ne
le lisait.

Ce que fait cette migration
---------------------------
Elle rattrape l'historique : tout départ qui pointe vers un dossier par
`planning_entry_id` mais dont `no_dossier` est vide reçoit la référence de ce
dossier, marquée `no_dossier_source = 'saisi'`.

Pourquoi 'saisi' et non 'reconstitue' : `planning_entry_id` n'est pas une
déduction. C'est le dossier que l'utilisateur a désigné lui-même dans le
formulaire. La seule chose que cette migration reconstitue, c'est la copie
textuelle de la référence — pas le rattachement. Marquer ces lignes
« reconstitué » ferait afficher en dégradé, à l'auditeur, un lien qui est en
réalité une donnée d'origine.

Les rattachements réellement déduits (backfill de la 222 depuis `ref_sifa`)
gardent leur `no_dossier_source = 'reconstitue'` et ne sont pas touchés.

Le maintien à l'écriture est assuré par `_sync_no_dossier()` dans
`app/routers/expe_departs.py`, appelé à la création et à la modification d'un
départ. Cette migration ne sert qu'à reprendre le passé.
"""

from __future__ import annotations

import sqlite3

NOM = "fsc_expe_dossier_vivant"
DEPEND = ["fsc_negoce_pf"]


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    cols = _colonnes(conn, "expe_departs")

    # Rejouabilité : sur une base où la migration historique 222 n'est jamais
    # passée (base neuve montée directement sur le schéma courant), les colonnes
    # peuvent manquer. On ne suppose pas, on vérifie.
    if "no_dossier" not in cols:
        conn.execute("ALTER TABLE expe_departs ADD COLUMN no_dossier TEXT")
    if "no_dossier_source" not in cols:
        conn.execute("ALTER TABLE expe_departs ADD COLUMN no_dossier_source TEXT")
    if "planning_entry_id" not in cols:
        # Rien à reprendre : le lien n'existe pas sur cette base.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expe_departs_dossier "
            "ON expe_departs(no_dossier)"
        )
        print("[MySifa] migration fsc_expe_dossier_vivant : planning_entry_id absent, rien à reprendre.")
        return

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_departs_dossier ON expe_departs(no_dossier)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_departs_planning "
        "ON expe_departs(planning_entry_id)"
    )

    # `reference` d'abord, `numero_of` en repli : c'est l'ordre que retiennent
    # déjà le traceur et le rapport de traçabilité par dossier.
    repris = conn.execute(
        """UPDATE expe_departs
              SET no_dossier = (
                    SELECT COALESCE(
                             NULLIF(TRIM(COALESCE(pe.reference, '')), ''),
                             NULLIF(TRIM(COALESCE(pe.numero_of, '')), ''))
                      FROM planning_entries pe
                     WHERE pe.id = expe_departs.planning_entry_id),
                  no_dossier_source = 'saisi'
            WHERE TRIM(COALESCE(no_dossier, '')) = ''
              AND planning_entry_id IS NOT NULL
              AND EXISTS (
                    SELECT 1 FROM planning_entries pe2
                     WHERE pe2.id = expe_departs.planning_entry_id
                       AND (TRIM(COALESCE(pe2.reference, '')) <> ''
                         OR TRIM(COALESCE(pe2.numero_of, '')) <> ''))"""
    ).rowcount

    # Diagnostic : ce qui reste sans dossier après reprise. Ce n'est pas une
    # anomalie en soi (une expédition peut ne concerner aucun OF), mais c'est
    # le chiffre que l'audit à blanc regardera en premier.
    orphelins = conn.execute(
        """SELECT COUNT(*) FROM expe_departs
            WHERE TRIM(COALESCE(no_dossier, '')) = ''
              AND planning_entry_id IS NULL"""
    ).fetchone()[0]

    print(
        f"[MySifa] migration fsc_expe_dossier_vivant : {repris} départ(s) "
        f"rattaché(s) à leur dossier depuis planning_entry_id, "
        f"{orphelins} départ(s) restent sans dossier."
    )
