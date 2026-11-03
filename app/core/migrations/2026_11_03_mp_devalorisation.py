"""
Stock dévalorisé (`mp_devalorisation`) : une ligne de valorisation marquée
« à jeter » compte en négatif, soit (-1) × sa valorisation.

Une ligne par matière, et par laize pour les matières laizées (laize_id = 0
sinon) : une laize abîmée ne condamne pas les autres. Le marquage se retire
en passant `actif` à 0 — la ligne reste, avec qui l'a posé et quand.
"""

NOM = "mp_devalorisation"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mp_devalorisation (
               matiere_id INTEGER NOT NULL,
               laize_id INTEGER NOT NULL DEFAULT 0,
               actif INTEGER NOT NULL DEFAULT 1,
               updated_at TEXT,
               updated_by_name TEXT,
               PRIMARY KEY (matiere_id, laize_id)
           )"""
    )
    conn.commit()
