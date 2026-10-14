"""Nouvel ERP — instructions du client (RVGI : onglets Livraison, Stockage,
Facturation de la fiche client).

Chaque onglet RVGI porte deux commentaires : interne (pour SIFA) et externe
(imprimé sur le document du client). Livraison → BL et ordre d'expédition,
stockage → commande, facturation → facture et avoir.
"""

NOM = "gc_instructions_tiers"
DEPEND = ["gc_socle"]

COLONNES = [f"instr_{e}_{s}" for e in ("livraison", "stockage", "facturation") for s in ("interne", "externe")]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_tiers)").fetchall()}
    for c in COLONNES:
        if c not in cols:
            conn.execute(f"ALTER TABLE gc_tiers ADD COLUMN {c} TEXT")
    conn.commit()
