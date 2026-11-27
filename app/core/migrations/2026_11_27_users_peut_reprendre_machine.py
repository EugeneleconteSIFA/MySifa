"""
Comptes qui peuvent reprendre une machine (« Passer la main ») sans être
conducteurs au Planning RH.

La liste du relais se lit au Planning RH (poste `conducteur`). Quelqu'un qui
n'y est pas planifié mais remplace un conducteur au besoin — un responsable
technique, par exemple — se déclare par cette case, cochée dans
Paramètres › Utilisateurs. Personne n'est coché par la migration.
"""

NOM = "users_peut_reprendre_machine"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "peut_reprendre_machine" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN peut_reprendre_machine INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()
