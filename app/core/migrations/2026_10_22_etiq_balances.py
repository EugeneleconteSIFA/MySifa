"""
Étiquettes spécifiques — profils de balance pour la pesée à l'impression.

La balance est lue sur le poste par Web Serial (navigateur Chrome / Edge),
jamais par le serveur. Un profil dit comment lui parler : vitesse, format de
trame, commande à envoyer pour demander un poids (vide = la balance émet en
continu), motif qui extrait le poids de la réponse, unité et décimales.

Seed : deux protocoles courants (demande « P » à 9 600 bauds, émission
continue), modifiables. Aucune balance n'est propre à SIFA ici.
"""

NOM = "etiq_balances"


def appliquer(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cle TEXT NOT NULL UNIQUE,
        nom TEXT NOT NULL,
        vitesse INTEGER NOT NULL DEFAULT 9600,
        bits INTEGER NOT NULL DEFAULT 8,
        parite TEXT NOT NULL DEFAULT 'none',
        stop INTEGER NOT NULL DEFAULT 1,
        commande TEXT NOT NULL DEFAULT '',
        motif TEXT NOT NULL DEFAULT '([-+]?\\d+[.,]?\\d*)\\s*kg',
        unite TEXT NOT NULL DEFAULT 'kg',
        decimales INTEGER NOT NULL DEFAULT 2,
        stable_seulement INTEGER NOT NULL DEFAULT 1,
        actif INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        updated_by TEXT
    )""")
    for cle, nom, cmd, motif in (
        ("demande_p", "Balance à la demande (commande P)", "P\\r\\n", r"([-+]?\d+[.,]?\d*)\s*kg"),
        ("continue", "Balance en émission continue", "", r"ST.*?([-+]?\d+[.,]?\d*)\s*kg"),
    ):
        conn.execute(
            "INSERT OR IGNORE INTO etiq_balances (cle,nom,commande,motif,created_at) VALUES (?,?,?,?,datetime('now'))",
            (cle, nom, cmd, motif))
    conn.commit()
