"""
Emplacements des matières premières (MyStock).

Les matières ne se géraient plus par emplacement : le stock est une quantité
par matière (ou par matière et laize). Cette table rend l'emplacement de
nouveau possible, sans le rendre obligatoire : elle dit OÙ se trouve une
partie du stock, elle ne le tient pas. Le total reste dans `mp_stock` /
`mp_stock_laize`, alimenté par les réceptions et le déstockage.

`laize_id` vaut 0 pour une matière non laizée — une clé unique ne voit pas
deux NULL comme égaux, et deux lignes « A121 sans laize » pour la même
matière seraient alors possibles.
"""

NOM = "mp_emplacements"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mp_emplacements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere_id      INTEGER NOT NULL REFERENCES matieres_premieres(id),
            laize_id        INTEGER NOT NULL DEFAULT 0,
            emplacement     TEXT    NOT NULL,
            quantite        REAL    NOT NULL DEFAULT 0,
            updated_at      TEXT,
            updated_by_name TEXT,
            UNIQUE(matiere_id, laize_id, emplacement)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mp_emplacements_matiere "
        "ON mp_emplacements(matiere_id)"
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : table mp_emplacements prête.")
