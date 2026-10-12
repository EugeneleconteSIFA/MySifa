"""
Agent emails de commandes : boîte commandes@ relevée, triée et suivie.

`emails_commandes` garde une ligne par message Outlook (identifiant Graph
unique), ce que l'agent en a compris (catégorie, client, commandes RVGI,
résumé) et son suivi dans MySifa (statut, pris en charge par, note).
`emails_commandes_reglages` porte l'activation et la boîte relevée.

L'agent ne fait que lire la boîte : rien n'est écrit dans Outlook.
"""

NOM = "emails_commandes"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS emails_commandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            graph_id TEXT NOT NULL UNIQUE,
            conversation_id TEXT,
            recu_le TEXT NOT NULL,
            expediteur TEXT,
            expediteur_nom TEXT,
            sujet TEXT,
            apercu TEXT,
            corps TEXT,
            a_pj INTEGER NOT NULL DEFAULT 0,
            lien_outlook TEXT,
            categorie TEXT,
            client TEXT,
            commandes_rvgi TEXT,
            dossiers TEXT,
            date_souhaitee TEXT,
            urgence TEXT,
            resume TEXT,
            classe_le TEXT,
            erreur_classement TEXT,
            statut TEXT NOT NULL DEFAULT 'a_traiter',
            pris_par TEXT,
            note TEXT,
            maj_le TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_cmd_recu ON emails_commandes(recu_le)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_cmd_statut ON emails_commandes(statut)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS emails_commandes_reglages "
        "(cle TEXT PRIMARY KEY NOT NULL, valeur TEXT NOT NULL)"
    )
    for cle, valeur in (("actif", "0"), ("delai_relance_h", "24")):
        conn.execute(
            "INSERT OR IGNORE INTO emails_commandes_reglages (cle, valeur) VALUES (?, ?)",
            (cle, valeur),
        )
    conn.commit()
