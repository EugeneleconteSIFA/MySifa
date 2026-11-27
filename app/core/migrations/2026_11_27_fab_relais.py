"""
Saisie de production : « Passer la main » à un autre conducteur.

Un relais enchaîne, sur la même machine et le même dossier, la fin de
production (« à reprendre plus tard ») et le départ du conducteur qui part,
puis l'arrivée, le démarrage du dossier et la reprise de la dernière opération
pour celui qui arrive. Les six saisies vont dans `production_data` comme si
elles avaient été faites à la main ; cette table garde le geste lui-même :
qui a passé la main à qui, sur quelle machine, pour quel dossier.

Elle sert aussi à la résolution de machine : le conducteur qui reprend peut
ne pas être planifié sur cette machine au Planning RH du jour. Sans le relais,
ses saisies partiraient sur la machine de son planning.
"""

NOM = "fab_relais"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS fab_relais (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               machine_id  INTEGER NOT NULL REFERENCES machines(id),
               no_dossier  TEXT,
               de_user_id  INTEGER REFERENCES users(id),
               vers_user_id INTEGER NOT NULL REFERENCES users(id),
               compteur    REAL,
               created_at  TEXT NOT NULL
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fab_relais_vers ON fab_relais(vers_user_id, created_at)"
    )
    conn.commit()
