"""
Notification « Dossiers à déstocker » (MyStock).

Le détecteur `stock.a_destocker` vit dans `app/services/notifications.py` :
dossiers terminés depuis moins de 15 jours et pas encore sortis du stock.
Cette migration ne fait que lui donner sa règle — active, destinée à
l'administration technique comme les deux autres notifications MyStock. Les
destinataires se règlent ensuite dans Paramètres › Notifications.
"""

import json
from datetime import datetime

NOM = "notif_a_destocker"
DEPEND = ["notifications_services"]


def appliquer(conn):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT OR IGNORE INTO notif_regles (code, actif, roles, push, updated_at, updated_by) "
        "VALUES (?, 1, ?, 0, ?, 'migration')",
        ("stock.a_destocker", json.dumps(["administration_technique"]), now),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {cur.rowcount or 0} règle seedée.")
