"""
Notification « Devis à traiter » (MyProd › Rentabilité), pour le superadmin.

Le détecteur `prod.devis_a_traiter` vit dans `app/services/notifications.py` :
devis rattachés à aucun dossier, ou datés après aujourd'hui. Cette migration
lui donne sa règle — active, destinée au superadmin (décision d'Eugène du
16/10/2026). Les destinataires se règlent ensuite dans Paramètres ›
Notifications.
"""

import json
from datetime import datetime

from config import ROLE_SUPERADMIN

NOM = "notif_devis_a_traiter"
DEPEND = ["notifications_services"]


def appliquer(conn):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT OR IGNORE INTO notif_regles (code, actif, roles, push, updated_at, updated_by) "
        "VALUES (?, 1, ?, 0, ?, 'migration')",
        ("prod.devis_a_traiter", json.dumps([ROLE_SUPERADMIN]), now),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {cur.rowcount or 0} règle seedée.")
