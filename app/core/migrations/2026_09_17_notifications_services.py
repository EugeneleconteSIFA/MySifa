"""
Notifications par service — pastilles rouges sur les applis du portail.

Trois tables :

- `notif_regles` : une ligne par détecteur (le catalogue vit dans
  `app/services/notifications.py`). Le super admin y décide, depuis
  Paramètres › Notifications, si la notification est active, quels rôles la
  reçoivent et si elle part aussi en push. Le code définit CE QUI se détecte,
  la base définit QUI est prévenu.
- `notif_vues` : ce que chaque utilisateur a déjà vu, par détecteur. La
  signature (plus grand identifiant, empreinte…) permet de ne rallumer la
  pastille que s'il y a du nouveau.
- `notif_push_etat` : dernière signature poussée par détecteur, pour que la
  boucle de push n'envoie qu'une fois par nouveauté.

Seed : les trois notifications validées par Eugène le 17/09/2026, actives.
"""

import json
from datetime import datetime

NOM = "notifications_services"

SEED = [
    # (code, rôles destinataires)
    ("stock.receptions_rvgi", ["administration_technique"]),
    ("stock.seuil_alerte", ["administration_technique"]),
    ("expe.departs_a_valider", ["expedition"]),
]


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notif_regles (
            code        TEXT PRIMARY KEY,
            actif       INTEGER NOT NULL DEFAULT 1,
            roles       TEXT    NOT NULL DEFAULT '[]',
            push        INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT,
            updated_by  TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notif_vues (
            user_id     INTEGER NOT NULL,
            code        TEXT    NOT NULL,
            signature   TEXT,
            vu_at       TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notif_push_etat (
            code        TEXT PRIMARY KEY,
            signature   TEXT,
            updated_at  TEXT
        )
    """)
    now = datetime.now().isoformat(timespec="seconds")
    n = 0
    for code, roles in SEED:
        cur = conn.execute(
            "INSERT OR IGNORE INTO notif_regles (code, actif, roles, push, updated_at, updated_by) "
            "VALUES (?, 1, ?, 0, ?, 'migration')",
            (code, json.dumps(roles), now),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} règle(s) de notification seedée(s).")
