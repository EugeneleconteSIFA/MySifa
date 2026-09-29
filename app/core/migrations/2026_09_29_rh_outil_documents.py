"""
Documents vérifiés des employés suivis dans l'Outil RH (MyCompta).

Même principe que les formations (migration `rh_outil_formations`) :
- `rh_outil_documents` : le catalogue commun des documents, géré depuis
  l'onglet. Un intitulé n'y figure qu'une fois (sans tenir compte de la casse).
- `rh_outil_membre_documents` : les documents attendus pour chaque employé
  suivi, une case « vérifié » par document.

Les suppressions en cascade sont faites par l'API (PRAGMA foreign_keys
désactivé).
"""

NOM = "rh_outil_documents"
DEPEND = ["rh_outil_membres"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_documents (
               id        INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle   TEXT NOT NULL,
               cree_le   TEXT NOT NULL,
               cree_par  TEXT
           )"""
    )
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS ux_rh_outil_documents_libelle
               ON rh_outil_documents(libelle COLLATE NOCASE)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_membre_documents (
               id           INTEGER PRIMARY KEY AUTOINCREMENT,
               membre_id    INTEGER NOT NULL REFERENCES rh_outil_membres(id) ON DELETE CASCADE,
               document_id  INTEGER NOT NULL REFERENCES rh_outil_documents(id) ON DELETE CASCADE,
               fait         INTEGER NOT NULL DEFAULT 0,
               ajoute_le    TEXT NOT NULL,
               UNIQUE(membre_id, document_id)
           )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS ix_rh_outil_membre_documents_document
               ON rh_outil_membre_documents(document_id)"""
    )
    conn.commit()
