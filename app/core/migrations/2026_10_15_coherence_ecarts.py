"""
Contrôleurs de cohérence : les écarts trouvés et leurs réglages.

`coherence_ecarts` est une file de travail, pas un journal. Un contrôleur
repasse toutes les 30 minutes : un écart qu'il retrouve reste ouvert, un écart
qu'il ne retrouve plus passe « résolu » de lui-même. `cle` identifie l'écart
d'un passage à l'autre (règle + objet) : c'est elle qui évite les doublons.

Statuts : ouvert, explique (quelqu'un a donné la raison, l'écart reste visible
mais ne compte plus dans la pastille), resolu.

`coherence_reglages` porte les seuils et l'activation de chaque règle
(`regle.<code>` = 0/1). Une clé absente prend la valeur par défaut du code.
"""

NOM = "coherence_ecarts"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS coherence_ecarts (
               id             INTEGER PRIMARY KEY AUTOINCREMENT,
               cle            TEXT NOT NULL UNIQUE,
               regle          TEXT NOT NULL,
               famille        TEXT NOT NULL,
               objet_type     TEXT,
               objet_ref      TEXT,
               titre          TEXT NOT NULL,
               detail         TEXT,
               donnees_json   TEXT,
               gravite        TEXT NOT NULL DEFAULT 'moyenne',
               statut         TEXT NOT NULL DEFAULT 'ouvert',
               premiere_vue   TEXT NOT NULL,
               derniere_vue   TEXT NOT NULL,
               resolu_le      TEXT,
               explication    TEXT,
               explique_par   TEXT,
               explique_le    TEXT
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_coherence_ecarts_statut ON coherence_ecarts(statut, famille)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_coherence_ecarts_objet ON coherence_ecarts(objet_ref)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS coherence_reglages (
               cle     TEXT PRIMARY KEY,
               valeur  TEXT
           )"""
    )
    conn.commit()
