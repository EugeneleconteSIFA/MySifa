"""
Mémo expédition du matin : réglages et historique des envois.

Les réglages (heure d'envoi, destinataires, activation) s'éditent dans
MyExpé › Pilotage. L'historique sert à deux choses : ne jamais envoyer deux
fois le mémo automatique le même jour, et pouvoir relire ce qui est parti.
"""

NOM = "expe_memo_matin"


def appliquer(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS expe_memo_reglages "
        "(cle TEXT PRIMARY KEY NOT NULL, valeur TEXT NOT NULL)"
    )
    for cle, valeur in (("actif", "0"), ("heure", "06:00"), ("destinataires", "")):
        conn.execute(
            "INSERT OR IGNORE INTO expe_memo_reglages (cle, valeur) VALUES (?, ?)",
            (cle, valeur),
        )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS expe_memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jour TEXT NOT NULL,
            cree_le TEXT NOT NULL,
            declencheur TEXT NOT NULL,
            destinataires TEXT NOT NULL,
            sujet TEXT NOT NULL,
            html TEXT NOT NULL,
            envoye INTEGER NOT NULL DEFAULT 0,
            erreur TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_expe_memos_jour ON expe_memos(jour)")
    conn.commit()
