"""Import de la grille magasin (CSV) vers la table SQLite emplacements_plan.

Utilisé par database._migrate et par le script tools/import_emplacements_plan.py.
"""
from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


def default_csv_path(project_root: Optional[Path] = None) -> Path:
    env = os.environ.get("EMPLACEMENTS_PLAN_CSV", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    root = project_root or Path(__file__).resolve().parent.parent
    return root / "data" / "emplacements_plan.csv"


def parse_emplacements_plan_csv(csv_path: Path) -> list[str]:
    """Grille CSV : ligne 1 = lettres de colonne (A,B,…), cellule = suffixe → code {Lettre}{suffixe}."""
    if not csv_path.is_file():
        return []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        return []
    headers: list[str] = []
    for h in rows[0]:
        t = (h or "").strip().upper()
        if t:
            headers.append(t)
    ncols = len(headers)
    codes: list[str] = []
    for row in rows[1:]:
        for i in range(ncols):
            if i >= len(row):
                continue
            cell = (row[i] or "").strip()
            if not cell:
                continue
            codes.append(f"{headers[i]}{cell}".upper())
    return sorted(set(codes))


def reload_emplacements_plan(conn: sqlite3.Connection, csv_path: Optional[Path] = None) -> int:
    """Crée la table si besoin, remplace les lignes. Retourne le nombre de codes (0 = fichier vide/absent, contenu inchangé)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS emplacements_plan (
            code TEXT PRIMARY KEY NOT NULL,
            imported_at TEXT NOT NULL
        )"""
    )
    path = csv_path if csv_path is not None else default_csv_path()
    codes = parse_emplacements_plan_csv(path)
    if not codes:
        return 0
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM emplacements_plan")
    conn.executemany(
        "INSERT INTO emplacements_plan (code, imported_at) VALUES (?, ?)",
        [(c, now) for c in codes],
    )
    return len(codes)


def sync_emplacements_plan_to_db(db_path: str, csv_path: Optional[Path] = None) -> int:
    conn = sqlite3.connect(db_path, timeout=5)
    try:
        n = reload_emplacements_plan(conn, csv_path)
        conn.commit()
        return n
    finally:
        conn.close()
