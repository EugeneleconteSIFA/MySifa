"""
FSC — un code-barre de bobine porté par deux réceptions ne passe plus en
silence.

Le problème
-----------
Le rattachement d'une bobine consommée en production à sa réception se fait par
égalité de texte sur le code-barre, en retenant le scan de réception le plus
récent :

    LEFT JOIN stock_receptions sr ON sr.id = (
        SELECT i.reception_id FROM stock_reception_items i
         WHERE TRIM(i.code_barre) = TRIM(fmu.code_barre)
         ORDER BY i.scanned_at DESC, i.id DESC LIMIT 1)

Aucun index unique n'interdit qu'un même code existe dans deux réceptions. Si
deux fournisseurs utilisent la même numérotation, ou si un code est scanné deux
fois à des dates différentes, la bobine est attribuée à la DERNIÈRE réception —
donc potentiellement au mauvais fournisseur, au mauvais certificat et au mauvais
claim. Sans aucune alerte : la chaîne s'affiche complète et fausse.

Le risque est faible en volume, maximal en conséquence. C'est exactement le type
d'erreur qu'un auditeur cherche, parce qu'elle invalide le claim sans laisser de
trace.

Ce que fait cette migration
---------------------------
1. Un index sur `code_barre` (la requête ci-dessus le fait à chaque ligne de
   chaque rapport de traçabilité).
2. `doublon_note` sur `stock_reception_items` : quand un opérateur confirme
   sciemment un code déjà connu, sa raison est enregistrée.
3. Le comptage des codes déjà ambigus, sans les corriger.

Pourquoi pas de contrainte UNIQUE : elle ferait échouer la migration si le
stock historique en contient, et surtout elle ferait échouer une réception en
plein quai des semaines plus tard, loin de la cause. Le contrôle est fait à
l'écriture — un 409 que l'opérateur peut lever avec une justification — et le
traceur signale désormais l'ambiguïté au lieu de trancher tout seul.
"""

from __future__ import annotations

import sqlite3

NOM = "fsc_code_barre_ambigu"


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_recp_items_code_barre "
        "ON stock_reception_items(code_barre)"
    )

    if "doublon_note" not in _colonnes(conn, "stock_reception_items"):
        conn.execute("ALTER TABLE stock_reception_items ADD COLUMN doublon_note TEXT")

    # Un code présent deux fois dans la MÊME réception est un double scan
    # bénin : la bobine est attribuée au bon fournisseur dans les deux cas.
    # Ce qui compte, c'est le code partagé entre réceptions DIFFÉRENTES.
    ambigus = conn.execute(
        """SELECT COUNT(*) FROM (
               SELECT TRIM(code_barre) AS c
                 FROM stock_reception_items
                WHERE TRIM(COALESCE(code_barre,'')) <> ''
                GROUP BY c
               HAVING COUNT(DISTINCT reception_id) > 1)"""
    ).fetchone()[0]

    if ambigus:
        bobines = conn.execute(
            """SELECT COUNT(*) FROM fab_matieres_utilisees fmu
                WHERE TRIM(COALESCE(fmu.code_barre,'')) IN (
                      SELECT TRIM(code_barre) FROM stock_reception_items
                       WHERE TRIM(COALESCE(code_barre,'')) <> ''
                       GROUP BY TRIM(code_barre)
                      HAVING COUNT(DISTINCT reception_id) > 1)"""
        ).fetchone()[0]
        print(
            f"[MySifa] migration fsc_code_barre_ambigu : index posé. "
            f"ATTENTION — {ambigus} code(s)-barre présent(s) dans plusieurs réceptions, "
            f"dont {bobines} scan(s) de production concerné(s) : leur origine "
            f"fournisseur n'est pas démontrable en l'état. Le traceur les signale "
            f"désormais au lieu de choisir la réception la plus récente."
        )
    else:
        print(
            "[MySifa] migration fsc_code_barre_ambigu : index posé, "
            "aucun code-barre partagé entre réceptions."
        )
