"""
FSC — négoce de produit fini certifié (régimes A1 et A2).

Contexte métier
---------------
SIFA achète du produit fini à des partenaires certifiés FSC et le revend. Le
partenaire fournit TOUJOURS la matière : ce n'est donc pas de la sous-traitance
au sens FSC-STD-40-004, mais du négoce en **système de transfert** — le claim
entrant doit ressortir à l'identique, jamais modifié ni amélioré.

Deux routes de livraison, et une seule pose problème :

  A1 · transit  La marchandise passe par le stock SIFA. La preuve est la chaîne
                réception → lot → expédition, déjà outillée depuis la v2.7.0
                (`lots_stock.fsc`).

  A2 · direct   Le partenaire livre le client final. Rien ne transite, donc rien
                n'était enregistré — alors que SIFA facture avec un claim FSC.
                Ces ventes étaient purement indémontrables : ni réception, ni
                lot, ni mouvement. Le lien « BL partenaire ↔ départ client » est
                la SEULE preuve possible dans ce régime ; ces colonnes le
                rendent enregistrable.

Ce que fait cette migration
---------------------------
1. `expe_departs` : de quel partenaire vient la marchandise, sous quel BL, avec
   quel claim entrant et quel claim sortant.
2. `pf_receptions` : de quoi figer le verdict de validité du certificat au
   moment de la réception.

Aucune donnée existante n'est modifiée : uniquement des colonnes nullables.
"""

from __future__ import annotations

import sqlite3

NOM = "fsc_negoce_pf"


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _table_existe(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone() is not None


def _index(conn: sqlite3.Connection, nom: str, table: str, colonnes: list[str]) -> None:
    """Crée un index seulement si TOUTES ses colonnes existent.

    Une migration doit pouvoir tourner sur une base en retard sans exploser :
    indexer une colonne absente ferait échouer toute la migration, y compris
    les ALTER TABLE déjà réussis avant elle.
    """
    presentes = _colonnes(conn, table)
    if all(c in presentes for c in colonnes):
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS {nom} ON {table}({', '.join(colonnes)})"
        )


def appliquer(conn: sqlite3.Connection) -> None:
    # ── 1. Expéditions : origine partenaire et claims ────────────────────
    if _table_existe(conn, "expe_departs"):
        cols = _colonnes(conn, "expe_departs")

        if "fsc_fournisseur_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN fsc_fournisseur_id INTEGER "
                "REFERENCES fournisseurs_fsc(id)"
            )
        if "fsc_bl_fournisseur" not in cols:
            conn.execute("ALTER TABLE expe_departs ADD COLUMN fsc_bl_fournisseur TEXT")
        if "fsc_claim_entrant" not in cols:
            conn.execute("ALTER TABLE expe_departs ADD COLUMN fsc_claim_entrant TEXT")

        # Claim entrant ET claim sortant sont stockés séparément alors qu'ils
        # DOIVENT être identiques en système de transfert. C'est justement
        # parce qu'ils doivent l'être qu'on garde les deux : un écart est une
        # non-conformité, et on ne peut pas détecter un écart qu'on
        # n'enregistre pas. Une colonne unique rendrait la faute invisible.
        if "fsc_claim_sortant" not in cols:
            conn.execute("ALTER TABLE expe_departs ADD COLUMN fsc_claim_sortant TEXT")

        # 1 = le partenaire a livré directement le client (A2). Drapeau
        # explicite plutôt que déduit de l'absence de lot : une absence peut
        # aussi bien signifier « pas encore saisi », et confondre les deux
        # ferait passer un oubli de saisie pour une livraison directe.
        if "fsc_sans_transit" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN fsc_sans_transit "
                "INTEGER NOT NULL DEFAULT 0"
            )

        _index(conn, "idx_expe_fsc_fourn", "expe_departs", ["fsc_fournisseur_id"])
        # Les départs A2 sont ceux qu'un auditeur voudra lister : index dédié
        # plutôt qu'un balayage complet de la table à chaque contrôle.
        _index(conn, "idx_expe_fsc_direct", "expe_departs",
               ["fsc_sans_transit", "date_enlevement"])

    # ── 2. Réception de produit fini : verdict de certificat figé ────────
    #
    # Le schéma `pf_receptions` existe depuis les migrations 210-212 mais n'a
    # jamais été alimenté : ni routeur, ni service, ni écran. Il lui manquait
    # de quoi porter la vérification du certificat.
    #
    # La validité se juge À LA DATE DU BL, pas à la date du jour. Un partenaire
    # dont le certificat expire entre la commande et la livraison casse le
    # claim — et un contrôle fait « aujourd'hui » ne le verra jamais, puisque
    # la date d'expiration sera passée pour toutes les réceptions, anciennes
    # comme récentes. On fige donc le verdict au moment de la réception.
    if _table_existe(conn, "pf_receptions"):
        cols = _colonnes(conn, "pf_receptions")
        if "licence_fournisseur" not in cols:
            conn.execute("ALTER TABLE pf_receptions ADD COLUMN licence_fournisseur TEXT")
        if "certificat_valide" not in cols:
            conn.execute("ALTER TABLE pf_receptions ADD COLUMN certificat_valide INTEGER")
        if "certificat_expiration" not in cols:
            conn.execute("ALTER TABLE pf_receptions ADD COLUMN certificat_expiration TEXT")
        if "certificat_note" not in cols:
            conn.execute("ALTER TABLE pf_receptions ADD COLUMN certificat_note TEXT")

        _index(conn, "idx_pf_recep_fourn", "pf_receptions", ["fournisseur_id"])
        _index(conn, "idx_pf_recep_date", "pf_receptions", ["date_reception"])

    if _table_existe(conn, "pf_reception_items"):
        _index(conn, "idx_pf_recep_items_recep", "pf_reception_items", ["reception_id"])
        _index(conn, "idx_pf_recep_items_lot", "pf_reception_items", ["lot_stock_id"])
