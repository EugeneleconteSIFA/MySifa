"""
Employés suivis dans l'onglet « Outil RH » de MyCompta.

Une ligne par employé ajouté depuis cet onglet : la liste est partagée entre
les utilisateurs de MyCompta et survit au rechargement. `user_id` est unique,
un employé ne peut figurer qu'une fois.
"""

NOM = "rh_outil_membres"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_membres (
               id           INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id      INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
               ajoute_le    TEXT NOT NULL,
               ajoute_par   TEXT
           )"""
    )
    conn.commit()
