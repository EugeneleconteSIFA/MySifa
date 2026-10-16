"""Nouvel ERP — lien avec MyAO (demandes de prix fournisseurs de MySifa).

Une demande MyAO clôturée devient une commande fournisseur de l'ERP. Deux
correspondances sont retenues au premier passage pour ne plus être demandées :
- le fournisseur MyAO (`fournisseurs_fsc.id`) ↔ le tiers ERP
  (`gc_tiers.fournisseur_fsc_id`) ;
- le produit d'une ligne MyAO (produit du catalogue MyAO, ou à défaut sa
  référence libre) ↔ l'article ERP (`gc_correspondances_myao`).
"""

NOM = "gc_myao"
DEPEND = ["gc_socle"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_tiers)").fetchall()}
    if "fournisseur_fsc_id" not in cols:
        conn.execute("ALTER TABLE gc_tiers ADD COLUMN fournisseur_fsc_id INTEGER")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gc_correspondances_myao (
               cle TEXT PRIMARY KEY,            -- « produit:<ao_produits.id> » ou « ref:<référence> »
               article_id INTEGER NOT NULL,
               maj_le TEXT)""")
    conn.commit()
