"""
Accès à la nouvelle application MyRH (suivi des nouveaux employés).

L'Outil RH quitte MyCompta pour sa propre application. Pour que personne ne
gagne ni ne perde l'accès au déménagement, MyRH reprend exactement les droits
de MyCompta, aux trois endroits où ils vivent :
- role_access_defaults : niveau par rôle (Paramètres › Accès) ;
- user_access_overrides : exceptions par personne ;
- users.access_overrides : ancienne forme JSON des exceptions, encore lue par
  le portail pour afficher les tuiles.
Rien n'est écrasé : une ligne MyRH déjà présente est conservée (INSERT OR
IGNORE, clé JSON ajoutée seulement si absente).
"""

import json

NOM = "myrh_acces"


def _table(conn, nom):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)).fetchone()


def appliquer(conn):
    n_roles = n_pers = n_json = 0
    if _table(conn, "role_access_defaults"):
        n_roles = conn.execute(
            """INSERT OR IGNORE INTO role_access_defaults (role, app_id, module_id, level, updated_at, updated_by)
               SELECT role, 'myrh', '_app', level, updated_at, 'migration myrh_acces'
                 FROM role_access_defaults WHERE app_id = 'compta' AND module_id = '_app'"""
        ).rowcount
    if _table(conn, "user_access_overrides"):
        n_pers = conn.execute(
            """INSERT OR IGNORE INTO user_access_overrides (user_id, app_id, module_id, level, updated_at, updated_by)
               SELECT user_id, 'myrh', '_app', level, updated_at, 'migration myrh_acces'
                 FROM user_access_overrides WHERE app_id = 'compta' AND module_id = '_app'"""
        ).rowcount
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "access_overrides" in cols:
        for r in conn.execute(
            "SELECT id, access_overrides FROM users WHERE access_overrides IS NOT NULL AND access_overrides != ''"
        ).fetchall():
            try:
                data = json.loads(r[1])
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(data, dict) and "compta" in data and "myrh" not in data:
                data["myrh"] = data["compta"]
                conn.execute("UPDATE users SET access_overrides=? WHERE id=?", (json.dumps(data), r[0]))
                n_json += 1
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n_roles} rôle(s), {n_pers} exception(s), "
          f"{n_json} ancienne(s) exception(s) recopiée(s) de MyCompta vers MyRH.")
