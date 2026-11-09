"""
MyCompta — Comparaison factures : chaque comparaison est conservée.

Le résultat d'une comparaison (analyse des ventes RVGI / grand-livre CW) ne
vivait que dans la page : un rechargement le perdait. Il est enregistré à sa
création, rouvert par son identifiant (`/compta?onglet=comparaison&comparaison=<id>`)
et listé dans l'historique de l'onglet. Les PDF ne sont pas conservés, seuls
leurs noms et le résultat calculé.
"""

NOM = "compta_comparaisons"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compta_comparaisons (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cree_le     TEXT NOT NULL,
            cree_par    INTEGER,
            fichiers    TEXT NOT NULL DEFAULT '[]',
            periode_du  TEXT,
            periode_au  TEXT,
            nb_ecarts   INTEGER NOT NULL DEFAULT 0,
            resultat    TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compta_comparaisons_cree_le "
        "ON compta_comparaisons(cree_le)"
    )
    conn.commit()
