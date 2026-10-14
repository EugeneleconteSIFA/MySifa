"""
Agent IA : actions proposées par l'agent, en attente de confirmation.

L'agent n'écrit jamais lui-même. Il propose un appel à un écran existant
(méthode, chemin, corps) ; la ligne attend ici que l'utilisateur clique
« Confirmer ». Une table plutôt qu'un dictionnaire en mémoire : la
confirmation peut arriver sur un autre processus du serveur, et la trace
reste (qui a proposé quoi, ce qui a été exécuté, la réponse de l'écran).

  statut   proposee | executee | echec | annulee | expiree
"""

NOM = "agent_ia_actions"


def appliquer(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS ai_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jeton TEXT NOT NULL UNIQUE,
        user_email TEXT NOT NULL,
        cle TEXT NOT NULL,
        libelle TEXT NOT NULL,
        resume TEXT,
        methode TEXT NOT NULL,
        chemin TEXT NOT NULL,
        corps_json TEXT,
        details_json TEXT,
        statut TEXT NOT NULL DEFAULT 'proposee',
        resultat_json TEXT,
        modele TEXT,
        created_at TEXT NOT NULL,
        traite_at TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_actions_user ON ai_actions(user_email, created_at DESC)")
    conn.commit()
