"""Écarts de saisie de production : notification MyProd et suivi des calages.

- Règle de notification `prod.ecarts` (pastille sur la tuile MyProd, l'onglet
  Production et le sous-onglet Erreurs & Qualité) : active, pour la direction
  et le super administrateur. Les destinataires se règlent ensuite dans
  Paramètres › Notifications.
- `dossier_calages_declares.traite_le` / `traite_par` : un chiffrage signalé
  ou des heures non reportées, une fois corrigés ou validés dans MyProd, ne
  doivent plus revenir dans la file au passage suivant des contrôleurs.
"""

import json
from datetime import datetime

NOM = "prod_ecarts"
DEPEND = ["notifications_services", "calage_signalement"]


def appliquer(conn):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT OR IGNORE INTO notif_regles (code, actif, roles, push, updated_at, updated_by) "
        "VALUES (?, 1, ?, 0, ?, 'migration')",
        ("prod.ecarts", json.dumps(["direction", "superadmin"]), now),
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(dossier_calages_declares)").fetchall()}
    if "traite_le" not in cols:
        conn.execute("ALTER TABLE dossier_calages_declares ADD COLUMN traite_le TEXT")
    if "traite_par" not in cols:
        conn.execute("ALTER TABLE dossier_calages_declares ADD COLUMN traite_par TEXT")
    conn.commit()
    print(f"[MySifa] migration {NOM} : {cur.rowcount or 0} règle de notification seedée.")
