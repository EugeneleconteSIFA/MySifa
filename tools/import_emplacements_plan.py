#!/usr/bin/env python3
"""Importe data/emplacements_plan.csv → table SQLite emplacements_plan.

Usage (depuis la racine du dépôt) :
  python tools/import_emplacements_plan.py
  EMPLACEMENTS_PLAN_CSV=/chemin/vers.csv python tools/import_emplacements_plan.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_PATH  # noqa: E402
from services.emplacements_plan import sync_emplacements_plan_to_db  # noqa: E402

if __name__ == "__main__":
    n = sync_emplacements_plan_to_db(DB_PATH)
    print(f"emplacements_plan : {n} code(s) importé(s).")
