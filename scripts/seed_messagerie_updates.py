#!/usr/bin/env python3
"""Insère l'annonce de mise à jour messagerie si absente (idempotent).

Usage local :
  python scripts/seed_messagerie_updates.py

Sur le VPS (après deploy du code) :
  cd /home/sifa/production-saas && python scripts/seed_messagerie_updates.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import get_db  # noqa: E402

TITRE = "Messagerie — GIFs, mentions et notifications"
SCOPE = "messages"

MESSAGE = (
    '<div style="font-size:13px;line-height:1.7;color:var(--text2)">'
    '<div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">'
    "Mise à jour — Messagerie</div>"
    '<div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;'
    'text-transform:uppercase;letter-spacing:.5px">Nouveautés</div>'
    '<ul style="margin:0 0 14px 0;padding-left:18px">'
    '<li style="margin-bottom:5px">Envoi de GIFs — bouton + dans la barre de saisie, puis GIF.</li>'
    '<li style="margin-bottom:5px">Mentions — taper @ pour taguer un collègue. @tous pour tout le canal.</li>'
    '<li style="margin-bottom:5px">Notifications navigateur — demande d\'activation au premier usage.</li>'
    '<li style="margin-bottom:5px">Emoji de canal — les administrateurs peuvent personnaliser l\'icône depuis les réglages du canal.</li>'
    '<li style="margin-bottom:5px">Réactions emoji sur les messages.</li>'
    '<li style="margin-bottom:5px">Modification d\'un message (15 min, texte seul).</li>'
    '<li style="margin-bottom:5px">Épinglage de messages — bouton dans l\'en-tête du canal.</li>'
    "</ul>"
    '<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);'
    'font-size:11px;color:var(--muted);line-height:1.6">'
    "Dans l'optique d'améliorer constamment l'outil, vos retours sont les bienvenus.<br>"
    "Merci de votre confiance.<br>"
    '<span style="color:var(--text2);font-weight:600">Eugène</span></div></div>'
)


def main() -> None:
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, active FROM update_announcements WHERE scope=? AND titre=? LIMIT 1",
            (SCOPE, TITRE),
        ).fetchone()
        if row:
            if not row["active"]:
                conn.execute(
                    "UPDATE update_announcements SET active=1 WHERE id=?",
                    (row["id"],),
                )
                conn.commit()
                print(f"Annonce id={row['id']} réactivée.")
            else:
                print(f"Annonce déjà présente (id={row['id']}, active=1).")
            return
        conn.execute(
            "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
            (SCOPE, TITRE, MESSAGE, ts, "système"),
        )
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        print(f"Annonce créée (id={new_id}, scope={SCOPE}).")


if __name__ == "__main__":
    main()
