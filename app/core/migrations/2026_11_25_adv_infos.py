"""
ADV : informations de suivi d'une ligne de commande.

L'ADV note sur une ligne ce qui explique où elle en est (« attente BAT client »,
« palette bloquée, transporteur relancé »…). Chaque info est datée et signée ;
la ligne en garde le fil, la plus récente en tête. Le carnet montre un « ? »
jaune sur la ligne, la fiche le fil complet.

Clé métier `(numero, ligne)` de la ligne de commande RVGI, comme les autres
tables ADV : l'id du miroir change à chaque synchro.
"""

NOM = "adv_infos"
DEPEND = ["adv_suivi_commandes"]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_infos (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            texte    TEXT    NOT NULL,
            cree_le  TEXT    NOT NULL,
            cree_par TEXT,
            user_id  INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_adv_infos_ligne ON adv_infos(numero, ligne)")
    conn.commit()
