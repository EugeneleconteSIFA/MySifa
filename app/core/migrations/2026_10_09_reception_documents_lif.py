"""
Pièces fournisseur (BL, facture) attachables à une ligne de réception RVGI.

Les cartons, palettes, mandrins et adhésifs entrent en stock directement depuis
RVGI, sans `stock_receptions` : une pièce doit pouvoir se rattacher à la ligne
ERP elle-même (`lif_id`). `reception_id` devient donc facultatif — l'un des
deux est renseigné. La table vient d'être créée : on la reconstruit, en
recopiant ce qu'elle contient.
"""

NOM = "reception_documents_lif"
DEPEND = ["reception_documents_fournisseur"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_reception_documents)")}
    if "lif_id" in cols:
        return
    conn.executescript(
        """
        CREATE TABLE stock_reception_documents_n (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            reception_id   INTEGER,
            lif_id         INTEGER,
            type_doc       TEXT    NOT NULL,
            nom_stockage   TEXT    NOT NULL,
            nom_origine    TEXT,
            taille         INTEGER,
            depose_le      TEXT    NOT NULL,
            depose_par     TEXT,
            supprime_le    TEXT,
            supprime_par   TEXT
        );
        INSERT INTO stock_reception_documents_n
            (id, reception_id, type_doc, nom_stockage, nom_origine, taille,
             depose_le, depose_par, supprime_le, supprime_par)
        SELECT id, reception_id, type_doc, nom_stockage, nom_origine, taille,
               depose_le, depose_par, supprime_le, supprime_par
          FROM stock_reception_documents;
        DROP TABLE stock_reception_documents;
        ALTER TABLE stock_reception_documents_n RENAME TO stock_reception_documents;
        CREATE INDEX IF NOT EXISTS idx_srd_reception
            ON stock_reception_documents(reception_id);
        CREATE INDEX IF NOT EXISTS idx_srd_lif
            ON stock_reception_documents(lif_id);
        """
    )
    conn.commit()
