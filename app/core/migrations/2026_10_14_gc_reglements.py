"""Nouvel ERP — règlements clients et fournisseurs.

Un règlement (virement reçu, chèque, LCR…) s'affecte à une ou plusieurs
échéances : c'est le lettrage. `gc_echeances.regle_cents` est la somme des
affectations, tenue par app/services/gc/compta.py — jamais saisie à la main.
"""

NOM = "gc_reglements"
DEPEND = ["gc_socle"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_reglements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tiers_id        INTEGER NOT NULL REFERENCES gc_tiers(id),
            sens            TEXT NOT NULL,              -- encaissement | decaissement
            date_reglement  TEXT NOT NULL,
            mode_paiement   TEXT REFERENCES gc_modes_paiement(code),
            montant_cents   INTEGER NOT NULL,
            reference       TEXT NOT NULL DEFAULT '',
            notes           TEXT NOT NULL DEFAULT '',
            origine         TEXT NOT NULL DEFAULT 'erp',
            origine_ref     TEXT,
            cree_par        TEXT,
            cree_le         TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_gc_regl_tiers ON gc_reglements(tiers_id);

        CREATE TABLE IF NOT EXISTS gc_reglements_affectations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            reglement_id    INTEGER NOT NULL REFERENCES gc_reglements(id),
            echeance_id     INTEGER NOT NULL REFERENCES gc_echeances(id),
            montant_cents   INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_gc_aff_regl ON gc_reglements_affectations(reglement_id);
        CREATE INDEX IF NOT EXISTS idx_gc_aff_ech ON gc_reglements_affectations(echeance_id);
        """
    )
    conn.commit()
