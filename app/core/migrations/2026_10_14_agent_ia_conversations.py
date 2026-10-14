"""
Agent IA : conversations enregistrées, pour les rouvrir depuis le widget.

Une ligne par conversation et par utilisateur. `messages_json` est l'état
du widget tel quel (messages, cartes d'action et leur résultat). Personne
d'autre que l'auteur ne les lit : aucune route d'administration ne les
expose, et le module « ai » est aveugle au contenu dans le journal.
"""

NOM = "agent_ia_conversations"


def appliquer(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS ai_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        titre TEXT NOT NULL,
        messages_json TEXT NOT NULL DEFAULT '[]',
        nb_messages INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_email, updated_at DESC)")
    conn.commit()
