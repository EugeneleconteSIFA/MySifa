"""Nouvel ERP — documents fournisseurs (BL, factures) déposés et lus par l'IA.

Un document est un fichier rangé sous les uploads, rattaché ou non à une
pièce. Son extraction (ce que l'IA a lu : fournisseur, numéro, date, n° de
notre commande, lignes, totaux) est gardée telle quelle en JSON : c'est une
proposition, jamais une écriture — la pièce se prépare en brouillon et se
valide à la main.
"""

NOM = "gc_documents"
DEPEND = ["gc_socle"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id INTEGER,                 -- pièce à laquelle le document est rattaché
            tiers_id INTEGER,                 -- fournisseur reconnu
            nature TEXT NOT NULL DEFAULT '',  -- bl | facture | autre (lue par l'IA)
            nom_fichier TEXT NOT NULL,
            chemin TEXT NOT NULL,
            mime TEXT NOT NULL DEFAULT '',
            taille INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'depose',   -- depose | analyse | erreur | traite
            extraction TEXT,                  -- JSON
            erreur TEXT,
            modele TEXT,
            cree_par TEXT, cree_le TEXT, analyse_le TEXT);
        CREATE INDEX IF NOT EXISTS idx_gc_documents_piece ON gc_documents(piece_id);
        """
    )
    conn.commit()
