"""
Réunions — mode écoute : l'avancement de la transcription.

Une transcription dure à peu près la durée de la réunion : sans indication,
l'écran « Transcription en cours » ressemble à un écran figé. Le worker écrit
ici, toutes les quelques secondes, la part de l'audio déjà transcrite (0 à 1),
lue sur l'horodatage du dernier segment produit. La page en tire une barre et
une estimation du temps restant.
"""

NOM = "reunion_ecoutes_progression"
DEPEND = ["reunion_ecoutes"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reunion_ecoutes)").fetchall()}
    if cols and "progression" not in cols:
        conn.execute("ALTER TABLE reunion_ecoutes ADD COLUMN progression REAL NOT NULL DEFAULT 0")
    conn.commit()
