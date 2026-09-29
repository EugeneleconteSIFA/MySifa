"""
Pièces jointes des documents de l'Outil RH (MyCompta).

Une pièce jointe est rattachée à un document d'un employé
(`rh_outil_membre_documents`). Le fichier vit sur disque sous
data/uploads/rh_outil/<attribution>/ avec un nom généré ; `nom` garde le nom
d'origine pour l'affichage et le téléchargement. Les suppressions (fichier et
ligne) sont faites par l'API.
"""

NOM = "rh_outil_pieces"
DEPEND = ["rh_outil_documents"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_pieces (
               id              INTEGER PRIMARY KEY AUTOINCREMENT,
               attribution_id  INTEGER NOT NULL REFERENCES rh_outil_membre_documents(id) ON DELETE CASCADE,
               nom             TEXT NOT NULL,
               fichier         TEXT NOT NULL,
               mime            TEXT NOT NULL,
               taille          INTEGER NOT NULL,
               ajoute_le       TEXT NOT NULL,
               ajoute_par      TEXT
           )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS ix_rh_outil_pieces_attribution
               ON rh_outil_pieces(attribution_id)"""
    )
    conn.commit()
