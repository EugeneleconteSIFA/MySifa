"""
Mes notes : mentions dans les commentaires.

Une ligne par personne mentionnée (@Nom) dans un commentaire de note. Elle
alimente la liste « Mentions » de Mes notes et part en notification (web
push) ; `lu_le` est posé quand la personne ouvre les commentaires de la note.
"""

NOM = "notes_mentions"
DEPEND = ["notes_outils"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS note_mentions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          commentaire_id INTEGER NOT NULL,
          note_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          par_user_id INTEGER NOT NULL,
          cree_le TEXT NOT NULL,
          lu_le TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_note_mentions_user ON note_mentions(user_id, lu_le);
        """
    )
    conn.commit()
