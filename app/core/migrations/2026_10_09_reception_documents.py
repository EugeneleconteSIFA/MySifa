"""
MyStock › Réception — BL et facture fournisseur joints à une réception.

Une réception porte ses pièces d'achat : le bon de livraison remis avec la
marchandise, la facture arrivée ensuite. Plusieurs fichiers par type sont
admis (BL en plusieurs pages scannées séparément, facture rectificative).

Le fichier vit sur disque sous UPLOADS_ROOT/receptions ; la table ne garde que
son nom de stockage, son nom d'origine et qui l'a déposé. Un retrait est
tracé (`supprime_le`, `supprime_par`), rien ne s'efface de la table.
"""

NOM = "reception_documents_fournisseur"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stock_reception_documents (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            reception_id   INTEGER NOT NULL,
            type_doc       TEXT    NOT NULL,
            nom_stockage   TEXT    NOT NULL,
            nom_origine    TEXT,
            taille         INTEGER,
            depose_le      TEXT    NOT NULL,
            depose_par     TEXT,
            supprime_le    TEXT,
            supprime_par   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_srd_reception
            ON stock_reception_documents(reception_id);
        """
    )
    conn.commit()
