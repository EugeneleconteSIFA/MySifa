"""
Repair Planning machine_id references
=====================================

Fixes cases where planning tables contain machine_id values that don't exist
in the `machines` table (e.g. legacy IDs after adding machines later).

What it does:
- Creates a timestamped .bak copy of the SQLite DB
- Finds machine_id values referenced in planning tables that are missing in machines
- Remaps them to the correct machine id based on machine name/code
- Merges rows safely for tables with UNIQUE(machine_id, date) or UNIQUE(machine_id, semaine)

Run:
    python repair_planning_machine_ids.py
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime

from config import DB_PATH


PLANNING_TABLES = [
    "planning_entries",
    "planning_holidays",
    "planning_day_worked",
    "planning_config",
]


def _backup_db(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{path}.{ts}.bak"
    shutil.copy2(path, bak)
    return bak


def _get_machine_map(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Returns mapping from canonical keys -> machine.id
    Keys are machine codes when present, otherwise names.
    """
    rows = conn.execute("SELECT id, nom, code FROM machines WHERE actif=1").fetchall()
    out: dict[str, int] = {}
    for r in rows:
        mid = int(r["id"])
        nom = (r["nom"] or "").strip()
        code = (r["code"] or "").strip()
        if code:
            out[code] = mid
        if nom:
            out[nom] = mid
    return out


def _existing_machine_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute("SELECT id FROM machines").fetchall()
    return {int(r["id"]) for r in rows}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _count_by_machine(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(
        f"SELECT machine_id, COUNT(*) AS c FROM {table} GROUP BY machine_id ORDER BY machine_id"
    ).fetchall()
    return [{"machine_id": int(r["machine_id"]), "c": int(r["c"])} for r in rows]


def _remap_simple(conn: sqlite3.Connection, table: str, old: int, new: int) -> int:
    cur = conn.execute(
        f"UPDATE {table} SET machine_id=? WHERE machine_id=?",
        (new, old),
    )
    return int(cur.rowcount or 0)


def _remap_merge_by_date(conn: sqlite3.Connection, table: str, old: int, new: int) -> int:
    """
    For tables with UNIQUE(machine_id, date):
    - For each row of old, if target row exists for (new,date) => delete old row
      else update machine_id to new.
    """
    changed = 0
    rows = conn.execute(
        f"SELECT id, date FROM {table} WHERE machine_id=?",
        (old,),
    ).fetchall()
    for r in rows:
        rid = int(r["id"])
        d = str(r["date"])
        ex = conn.execute(
            f"SELECT id FROM {table} WHERE machine_id=? AND date=?",
            (new, d),
        ).fetchone()
        if ex:
            conn.execute(f"DELETE FROM {table} WHERE id=?", (rid,))
            changed += 1
        else:
            conn.execute(
                f"UPDATE {table} SET machine_id=? WHERE id=?",
                (new, rid),
            )
            changed += 1
    return changed


def _remap_merge_by_semaine(conn: sqlite3.Connection, table: str, old: int, new: int) -> int:
    """
    For planning_config with UNIQUE(machine_id, semaine):
    - If target exists for (new,semaine) => delete old row
      else update machine_id to new.
    """
    changed = 0
    rows = conn.execute(
        f"SELECT id, semaine FROM {table} WHERE machine_id=?",
        (old,),
    ).fetchall()
    for r in rows:
        rid = int(r["id"])
        s = str(r["semaine"])
        ex = conn.execute(
            f"SELECT id FROM {table} WHERE machine_id=? AND semaine=?",
            (new, s),
        ).fetchone()
        if ex:
            conn.execute(f"DELETE FROM {table} WHERE id=?", (rid,))
            changed += 1
        else:
            conn.execute(
                f"UPDATE {table} SET machine_id=? WHERE id=?",
                (new, rid),
            )
            changed += 1
    return changed


def main() -> None:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"DB introuvable: {DB_PATH}")

    bak = _backup_db(DB_PATH)
    print(f"Backup créé: {bak}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        existing_ids = _existing_machine_ids(conn)
        mm = _get_machine_map(conn)

        # Determine canonical targets (must exist)
        # Accept both correct 'Cohésio' and legacy 'Cohésion'
        targets = {
            1: mm.get("C1") or mm.get("Cohésio 1") or mm.get("Cohésion 1"),
            2: mm.get("C2") or mm.get("Cohésio 2") or mm.get("Cohésion 2"),
            3: mm.get("DSI"),
            4: mm.get("REP") or mm.get("Repiquage"),
        }
        if not all(targets.values()):
            missing = [k for k, v in targets.items() if not v]
            raise SystemExit(
                "Impossible de résoudre les machines cibles pour indices "
                + ",".join(map(str, missing))
                + ". Vérifie la table machines (nom/code)."
            )

        # Find machine_ids referenced in planning tables that are missing from machines
        referenced_missing: set[int] = set()
        for t in PLANNING_TABLES:
            if not _table_exists(conn, t):
                continue
            rows = conn.execute(f"SELECT DISTINCT machine_id FROM {t}").fetchall()
            for r in rows:
                mid = int(r["machine_id"])
                if mid not in existing_ids:
                    referenced_missing.add(mid)

        if not referenced_missing:
            print("OK: aucun machine_id orphelin trouvé dans les tables planning.")
            return

        print("Machine IDs orphelins trouvés:", sorted(referenced_missing))
        print("Avant:", {t: _count_by_machine(conn, t) for t in PLANNING_TABLES if _table_exists(conn, t)})

        # Apply remap for orphan IDs that match legacy indices 1..4 (most common)
        # Only touches orphan IDs (so it won't rewrite existing machine ids).
        changes: dict[str, int] = {t: 0 for t in PLANNING_TABLES}
        for old in sorted(referenced_missing):
            if old not in targets:
                print(f"SKIP: machine_id orphelin {old} non reconnu (attendu 1..4).")
                continue
            new = int(targets[old])
            if old == new:
                continue
            for t in PLANNING_TABLES:
                if not _table_exists(conn, t):
                    continue
                if t == "planning_holidays":
                    changes[t] += _remap_merge_by_date(conn, t, old, new)
                elif t == "planning_day_worked":
                    changes[t] += _remap_merge_by_date(conn, t, old, new)
                elif t == "planning_config":
                    changes[t] += _remap_merge_by_semaine(conn, t, old, new)
                else:
                    changes[t] += _remap_simple(conn, t, old, new)

        conn.commit()

        print("Changements:", {k: v for k, v in changes.items() if v})
        print("Après:", {t: _count_by_machine(conn, t) for t in PLANNING_TABLES if _table_exists(conn, t)})
        print("Terminé.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

