#!/usr/bin/env python3
"""Copie la base SQLite (DB_PATH) vers data/backups/production.db.<horodatage>.bak

Usage (racine du dépôt) :
  python tools/backup_mysifa_data.py
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_PATH, DATA_DIR  # noqa: E402


def main() -> Path:
    src = Path(DB_PATH)
    if not src.is_file():
        raise SystemExit(f"Base introuvable : {src}")
    backup_dir = Path(DATA_DIR) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"production.db.{stamp}.bak"
    shutil.copy2(src, dest)
    print(f"Copié : {dest}")
    return dest


if __name__ == "__main__":
    main()
