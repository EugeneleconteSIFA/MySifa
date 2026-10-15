"""
Notification « Écarts de cohérence » (pastille sur Paramètres).

Le détecteur `settings.coherence` vit dans `app/services/notifications.py` et
compte les écarts ouverts de `coherence_ecarts`. Cette migration lui donne sa
règle : active, pour la direction et le super administrateur, qui sont les
seuls à voir l'onglet Paramètres › Cohérence. Les destinataires se règlent
ensuite dans Paramètres › Notifications.
"""

import json
from datetime import datetime

NOM = "notif_coherence"
DEPEND = ["notifications_services", "coherence_ecarts"]


def appliquer(conn):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT OR IGNORE INTO notif_regles (code, actif, roles, push, updated_at, updated_by) "
        "VALUES (?, 1, ?, 0, ?, 'migration')",
        ("settings.coherence", json.dumps(["direction", "superadmin"]), now),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {cur.rowcount or 0} règle seedée.")
