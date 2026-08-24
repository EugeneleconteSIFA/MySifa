"""
Empreinte de contenu sur les scans d'OF.

L'ingestion initiale balaie plusieurs annees de scans (U:\\Requia\\Scan\\OF
SCANNES, un sous-dossier par annee) et l'import quotidien repasse ensuite sur
les fichiers recents. Sans cle de deduplication, un fichier renomme, deplace
d'un dossier d'annee a l'autre, ou simplement rebalaye apres la perte de
l'index local, rentrerait une seconde fois.

`UNIQUE(fichier)` ne protege de rien : le nom stocke porte un horodatage, il
est unique par construction. La seule cle honnete est le CONTENU — deux scans
identiques sont le meme document, quel que soit leur nom.

L'index est partiel de fait : les documents anterieurs ont `empreinte` a NULL,
et SQLite n'oppose pas les NULL entre eux dans un index unique. Ils ne sont
donc pas re-dedupliques retroactivement, mais ils ne bloquent rien non plus.
"""

NOM = "produit_documents_empreinte"
DEPEND = ["produit_memoire_tables"]


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(produit_documents)").fetchall()}
    if not cols:
        return  # table absente (harnais de test) : rien a faire
    if "empreinte" not in cols:
        conn.execute("ALTER TABLE produit_documents ADD COLUMN empreinte TEXT")
    if "chemin_origine" not in cols:
        conn.execute("ALTER TABLE produit_documents ADD COLUMN chemin_origine TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_produit_documents_empreinte "
        "ON produit_documents(empreinte) WHERE empreinte IS NOT NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_produit_documents_of "
        "ON produit_documents(of_numero)"
    )
    conn.commit()
    print("[MySifa] migration produit_documents_empreinte : "
          "deduplication des scans par contenu en place.")
