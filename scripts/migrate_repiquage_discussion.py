"""MySifa - Script one-shot migration 115 : table repiquage_discussion.

Cree la table du fil de discussion par dossier (Repiquage) :
- repiquage_discussion (id, no_dossier, user_id, user_nom, type, message, created_at)
- types autorises : 'observation', 'dysfonctionnement', 'commentaire'

Idempotent : enregistre la migration version=115 dans schema_migrations.

Utilisation sur le VPS (v1 ou prod) :
    cd /home/sifa/production-saas-v1
    python3 scripts/migrate_repiquage_discussion.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import DB_PATH  # noqa: E402


def main() -> int:
    print(f"DB : {DB_PATH}")
    if not Path(DB_PATH).exists():
        print("ERREUR : fichier DB introuvable", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  version INTEGER PRIMARY KEY,"
            "  name TEXT NOT NULL,"
            "  applied_at TEXT NOT NULL)"
        )

        deja = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=115 LIMIT 1"
        ).fetchone()
        if deja:
            print("Migration 115 deja appliquee, rien a faire.")
            return 0

        conn.execute(
            "CREATE TABLE IF NOT EXISTS repiquage_discussion ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  no_dossier TEXT NOT NULL,"
            "  user_id INTEGER,"
            "  user_nom TEXT NOT NULL,"
            "  type TEXT NOT NULL CHECK(type IN ('observation','dysfonctionnement','commentaire')),"
            "  message TEXT NOT NULL,"
            "  created_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rep_disc_dossier "
            "ON repiquage_discussion(no_dossier)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rep_disc_date "
            "ON repiquage_discussion(created_at)"
        )
        print("  + table repiquage_discussion")

        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations "
            "(version, name, applied_at) VALUES (?, ?, ?)",
            (115, "repiquage_discussion", datetime.now().isoformat()),
        )
        conn.commit()
        print("Migration 115 enregistree. OK.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
