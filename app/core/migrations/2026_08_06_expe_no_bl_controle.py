"""
MyExpé / FSC — le numéro de bon de livraison devient contrôlable.

Le problème
-----------
`expe_departs.no_bl` est un texte libre : aucun index, aucune contrainte. Deux
départs peuvent porter le même numéro sans que rien ne le signale.

C'est le premier maillon d'un audit FSC — l'auditeur arrive avec un bon de
livraison papier et demande le départ correspondant. Si deux lignes répondent,
la chaîne qu'on lui montre est peut-être la mauvaise, et personne ne peut le
savoir. Un doublon de numéro n'est pas une faute de saisie anodine : c'est une
ambiguïté à la racine de toute la démonstration.

Ce que fait cette migration
---------------------------
Elle pose l'index (`no_bl` est interrogé à chaque entrée dans le traceur) et
elle COMPTE les doublons existants, sans les corriger.

Pourquoi pas de contrainte UNIQUE : le stock historique en contient
probablement, et une contrainte posée sur des données non conformes ferait
échouer la migration en production — ou pire, ferait échouer des créations de
départ légitimes des semaines plus tard, loin de la cause. Le contrôle est
donc fait à l'écriture (`_check_no_bl_unique()` dans
`app/routers/expe_departs.py`, un 409 que l'opérateur peut lever en
connaissance de cause) et les doublons déjà là remontent dans
`GET /api/fsc/controles` pour être traités à la main.
"""

from __future__ import annotations

import sqlite3

NOM = "expe_no_bl_controle"


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_departs_no_bl ON expe_departs(no_bl)"
    )

    # Comparaison normalisée : un BL saisi « bl-1001 » et un autre « BL 1001 »
    # désignent le même document. C'est la même normalisation que celle
    # appliquée à l'écriture.
    doublons = conn.execute(
        """SELECT COUNT(*) FROM (
               SELECT UPPER(REPLACE(REPLACE(TRIM(no_bl),' ',''),'-','')) AS cle
                 FROM expe_departs
                WHERE TRIM(COALESCE(no_bl,'')) <> ''
                GROUP BY cle
               HAVING COUNT(*) > 1)"""
    ).fetchone()[0]

    if doublons:
        print(
            f"[MySifa] migration expe_no_bl_controle : index posé. "
            f"ATTENTION — {doublons} numéro(s) de BL portés par plusieurs départs. "
            f"Liste dans GET /api/fsc/controles (clé `bl_doublons`) : à trancher "
            f"avant l'audit, chacun est une ambiguïté au premier maillon de la chaîne."
        )
    else:
        print("[MySifa] migration expe_no_bl_controle : index posé, aucun doublon de BL.")
