"""
Formations des employés suivis dans l'Outil RH (MyCompta).

- `rh_outil_formations` : le catalogue commun des formations, géré depuis
  l'onglet. Un intitulé n'y figure qu'une fois (sans tenir compte de la casse).
- `rh_outil_membre_formations` : les formations attribuées à chaque employé
  suivi, une case « fait » par formation. Un employé a sa propre liste.

Les clés étrangères ne sont pas appliquées par SQLite ici (PRAGMA
foreign_keys désactivé) : les suppressions en cascade sont faites par l'API.
"""

NOM = "rh_outil_formations"
DEPEND = ["rh_outil_membres"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_formations (
               id        INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle   TEXT NOT NULL,
               cree_le   TEXT NOT NULL,
               cree_par  TEXT
           )"""
    )
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS ux_rh_outil_formations_libelle
               ON rh_outil_formations(libelle COLLATE NOCASE)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_membre_formations (
               id            INTEGER PRIMARY KEY AUTOINCREMENT,
               membre_id     INTEGER NOT NULL REFERENCES rh_outil_membres(id) ON DELETE CASCADE,
               formation_id  INTEGER NOT NULL REFERENCES rh_outil_formations(id) ON DELETE CASCADE,
               fait          INTEGER NOT NULL DEFAULT 0,
               ajoute_le     TEXT NOT NULL,
               UNIQUE(membre_id, formation_id)
           )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS ix_rh_outil_membre_formations_formation
               ON rh_outil_membre_formations(formation_id)"""
    )
    conn.commit()
