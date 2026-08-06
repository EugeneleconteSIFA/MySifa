"""
FSC — la réception de matière pointe son fournisseur par clé, et fige le
verdict de son certificat.

Deux problèmes, même maillon
----------------------------
1. `stock_receptions.fournisseur` est un TEXTE, et tous les modules FSC
   joignent `fournisseurs_fsc ON ff.nom = sr.fournisseur`. Renommer un
   fournisseur dans l'annuaire — corriger une faute de frappe, passer de
   « UPM » à « UPM Raflatac » — détache silencieusement toutes ses réceptions
   passées de leur licence et de leur certificat. La chaîne ne casse pas avec
   fracas : elle affiche un fournisseur sans licence, ce qui se lit comme un
   fournisseur non certifié.

2. La création d'une réception exige un numéro de certificat mais ne vérifie
   jamais s'il était VALIDE ce jour-là. Le service qui sait le faire existe
   (`app/services/fsc_certificat.py`, qui juge à la date du document et
   distingue « inconnu » de « valide ») mais n'est appelé que par le module
   négoce. Côté matière première, rien.

Ce que fait cette migration
---------------------------
1. `fournisseur_id` sur `stock_receptions`, backfillée par correspondance
   exacte de nom (insensible à la casse et aux espaces). Le texte est conservé
   tel quel : c'est ce qui figurait sur le bon de livraison, et une chaîne de
   contrôle ne réécrit pas ses pièces.

2. `certificat_valide` / `certificat_expiration` / `certificat_note` — mêmes
   colonnes que `pf_receptions`, même rôle : figer le verdict au moment de la
   réception.

Ce qu'elle ne fait PAS
----------------------
Aucun backfill des verdicts. Évaluer aujourd'hui la validité d'un certificat
pour une réception de l'an dernier utiliserait la date d'expiration ACTUELLE —
possiblement renouvelée depuis. Le verdict produit serait faux dans les deux
sens : il déclarerait valides des livraisons qui ne l'étaient pas, et
inversement. C'est précisément ce que le module de contrôle interdit dans son
propre en-tête. Les réceptions passées restent donc sans verdict, ce qui est la
vérité : personne ne l'a établi à l'époque.
"""

from __future__ import annotations

import sqlite3

NOM = "fsc_reception_fournisseur_id"


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    cols = _colonnes(conn, "stock_receptions")

    if "fournisseur_id" not in cols:
        conn.execute(
            "ALTER TABLE stock_receptions ADD COLUMN fournisseur_id "
            "INTEGER REFERENCES fournisseurs_fsc(id)"
        )
    for col, typ in (
        ("certificat_valide", "TEXT"),
        ("certificat_expiration", "TEXT"),
        ("certificat_note", "TEXT"),
    ):
        if col not in cols:
            conn.execute(f"ALTER TABLE stock_receptions ADD COLUMN {col} {typ}")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_recep_fournisseur "
        "ON stock_receptions(fournisseur_id)"
    )

    # Correspondance exacte uniquement. Un rapprochement approchant
    # (« UPM » ↔ « UPM Raflatac ») pourrait attribuer à une réception le
    # certificat d'un autre fournisseur : dans une chaîne de contrôle, un faux
    # lien coûte plus cher qu'un lien absent.
    rattaches = conn.execute(
        """UPDATE stock_receptions
              SET fournisseur_id = (
                    SELECT ff.id FROM fournisseurs_fsc ff
                     WHERE UPPER(TRIM(ff.nom)) = UPPER(TRIM(stock_receptions.fournisseur))
                     LIMIT 1)
            WHERE fournisseur_id IS NULL
              AND TRIM(COALESCE(fournisseur,'')) <> ''
              AND EXISTS (
                    SELECT 1 FROM fournisseurs_fsc ff2
                     WHERE UPPER(TRIM(ff2.nom)) = UPPER(TRIM(stock_receptions.fournisseur)))"""
    ).rowcount

    orphelines = conn.execute(
        """SELECT COUNT(*) FROM stock_receptions
            WHERE fournisseur_id IS NULL
              AND TRIM(COALESCE(fournisseur,'')) <> ''"""
    ).fetchone()[0]

    message = (
        f"[MySifa] migration fsc_reception_fournisseur_id : {rattaches} réception(s) "
        f"rattachée(s) à leur fournisseur par clé."
    )
    if orphelines:
        message += (
            f" ATTENTION — {orphelines} réception(s) portent un nom de fournisseur "
            f"absent de l'annuaire FSC : leur licence et leur certificat ne sont pas "
            f"opposables en l'état. Liste dans GET /api/fsc/controles."
        )
    print(message)
