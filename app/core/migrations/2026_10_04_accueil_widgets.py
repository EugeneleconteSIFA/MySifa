"""
Widgets d'accueil : la colonne « Mes widgets » du portail.

- accueil_widgets : les widgets de chaque utilisateur. Un widget pointe un bloc
  du registre (app/services/blocs_registre.py) par son nom stable, garde l'URL
  capturée (filtres compris) et la liste ordonnée des valeurs clés cochées,
  avec une alerte facultative par valeur (JSON, 4 valeurs au maximum).
- blocs_reglages : l'interrupteur de capture que le superadmin pose sur un
  bloc. Un bloc sans ligne ici est capturable, et « nouveau » pour l'écran de
  pilotage.
- accueil_prefs : la colonne repliée ou non, par utilisateur.

Les anciens tableaux de bord (tables dashboards / user_dashboards) restent en
place : ils seront retirés une fois le remplacement en service.
"""

NOM = "accueil_widgets_tables"


def appliquer(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS accueil_widgets ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER NOT NULL,"
        " bloc TEXT NOT NULL,"
        " objet TEXT,"
        " url_capture TEXT NOT NULL,"
        " nom TEXT NOT NULL,"
        " valeurs TEXT NOT NULL DEFAULT '[]',"
        " affichage TEXT NOT NULL DEFAULT 'bloc',"
        " hauteur TEXT NOT NULL DEFAULT 'm',"
        " ordre INTEGER NOT NULL DEFAULT 0,"
        " created_at TEXT,"
        " updated_at TEXT,"
        " FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_accueil_widgets_user"
        " ON accueil_widgets(user_id, ordre)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS blocs_reglages ("
        " bloc TEXT PRIMARY KEY,"
        " capturable INTEGER NOT NULL DEFAULT 1,"
        " updated_at TEXT,"
        " updated_by TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS accueil_prefs ("
        " user_id INTEGER PRIMARY KEY,"
        " colonne_repliee INTEGER NOT NULL DEFAULT 0,"
        " updated_at TEXT,"
        " FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"
    )
    conn.commit()
