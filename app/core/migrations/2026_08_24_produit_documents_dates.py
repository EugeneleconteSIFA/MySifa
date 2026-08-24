"""
Dater un scan d'OF par sa production, pas par son import.

Tous les scans deposes le meme jour portaient la meme date — celle du depot.
Sept documents affichaient « 24/08/2026 » alors qu'ils couvrent plusieurs mois
de production : la liste ne s'ordonnait donc sur rien.

Deux colonnes reglent la question :

- `date_fichier` : date de derniere modification du fichier sur le partage,
  transmise par le navigateur (`File.lastModified`) ou par le script d'import.
  C'est la date du scan, pas celle de l'envoi.
- `date_document` : la meilleure date connue, resolue a l'enregistrement dans
  cet ordre — fin de la production rattachee, puis date de creation de l'OF,
  puis date du fichier, puis date d'import. On la STOCKE plutot que de la
  recalculer a chaque lecture : c'est elle qui trie la liste, et un tri qui
  change tout seul quand une donnee amont bouge est un tri qu'on ne comprend
  plus.

Reprise : les documents deja enregistres recuperent la date de creation de
leur OF quand ils en ont un. Les autres gardent leur date d'import — on ne
sait rien de mieux a leur sujet, et l'inventer serait pire.
"""

NOM = "produit_documents_dates"
DEPEND = ["produit_memoire_tables"]


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(produit_documents)").fetchall()}
    if not cols:
        return
    if "date_fichier" not in cols:
        conn.execute("ALTER TABLE produit_documents ADD COLUMN date_fichier TEXT")
    if "date_document" not in cols:
        conn.execute("ALTER TABLE produit_documents ADD COLUMN date_document TEXT")

    repris = conn.execute(
        """UPDATE produit_documents
           SET date_document = COALESCE(
               (SELECT s.date_fin FROM produit_series s
                 WHERE s.no_dossier = produit_documents.no_dossier),
               (SELECT o.date_creation FROM of_imports o
                 WHERE o.id = produit_documents.of_import_id),
               importe_le)
           WHERE date_document IS NULL"""
    ).rowcount
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_produit_documents_date "
        "ON produit_documents(ref_produit_norm, date_document DESC)"
    )
    conn.commit()
    print("[MySifa] migration produit_documents_dates : "
          "%d scan(s) redate(s) sur leur production." % (repris or 0))
