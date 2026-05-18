"""Référentiel des codes opération (ex-operations.json) — stockage SQLite."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from config import BASE_DIR, validate_operations_config

TABLE = "operation_codes"
_JSON_PATH = os.path.join(BASE_DIR, "operations.json")
_ALLOWED_CATEGORIES = frozenset(
    {
        "calage",
        "arret",
        "production",
        "personnel",
        "appro",
        "nettoyage",
        "pause",
        "technique",
        "annulation",
        "autre",
    }
)


def operations_json_path() -> str:
    return _JSON_PATH


def read_operations_json_file() -> Dict[str, Dict[str, Any]]:
    try:
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"Fichier manquant : {_JSON_PATH}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON invalide : {_JSON_PATH} — {e}") from e
    validate_operations_config(data)
    return data


def _row_to_entry(row) -> Dict[str, Any]:
    return {
        "severity": row["severity"],
        "label": row["label"],
        "category": row["category"],
        "required": bool(row["required"]),
    }


def load_operations_dict(conn=None) -> Dict[str, Dict[str, Any]]:
    """Charge depuis la table SQLite ; repli sur operations.json si table absente ou vide."""
    close = False
    if conn is None:
        from database import get_db

        cm = get_db()
        conn = cm.__enter__()
        close = True
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (TABLE,)
        ).fetchone()
        if exists:
            rows = conn.execute(
                f"""SELECT code, severity, label, category, required
                    FROM {TABLE} ORDER BY CAST(code AS INTEGER), code"""
            ).fetchall()
            if rows:
                return {str(r["code"]): _row_to_entry(r) for r in rows}
    except Exception:
        pass
    finally:
        if close:
            conn.close()
    return read_operations_json_file()


def refresh_operations_cache() -> Dict[str, Dict[str, Any]]:
    """Met à jour config.OPERATION_SEVERITY depuis la base."""
    import config as cfg

    data = load_operations_dict()
    cfg.OPERATION_SEVERITY = data
    return data


def seed_operation_codes_if_empty(conn) -> int:
    """Importe operations.json si la table est vide. Retourne le nombre de lignes insérées."""
    n = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    if n:
        return 0
    data = read_operations_json_file()
    now = datetime.now().isoformat()
    for code, entry in data.items():
        conn.execute(
            f"""INSERT INTO {TABLE} (code, severity, label, category, required, updated_at)
                VALUES (?,?,?,?,?,?)""",
            (
                str(code).strip(),
                entry["severity"],
                entry["label"],
                entry["category"],
                1 if entry.get("required") else 0,
                now,
            ),
        )
    return len(data)


def upsert_operation_codes_from_json(conn, codes: Optional[list] = None) -> int:
    """Met à jour des codes précis depuis operations.json (déploiement / migration)."""
    data = read_operations_json_file()
    keys = [str(c) for c in codes] if codes else list(data.keys())
    now = datetime.now().isoformat()
    n = 0
    for code in keys:
        entry = data.get(code)
        if not entry:
            continue
        conn.execute(
            f"""INSERT INTO {TABLE} (code, severity, label, category, required, updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(code) DO UPDATE SET
                  severity=excluded.severity,
                  label=excluded.label,
                  category=excluded.category,
                  required=excluded.required,
                  updated_at=excluded.updated_at""",
            (
                code,
                entry["severity"],
                entry["label"],
                entry["category"],
                1 if entry.get("required") else 0,
                now,
            ),
        )
        n += 1
    return n


def normalize_code(code: str) -> str:
    c = str(code or "").strip()
    if not c or not re.match(r"^\d+$", c):
        raise ValueError("Le code doit être numérique (ex. 12, 58).")
    return c


def validate_operation_payload(body: dict, *, for_create: bool = True) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Corps JSON invalide.")
    code = normalize_code(body.get("code", ""))
    label = str(body.get("label") or "").strip()
    severity = str(body.get("severity") or "").strip()
    category = str(body.get("category") or "").strip().lower()
    required = bool(body.get("required"))
    if not label:
        raise ValueError("Le libellé est requis.")
    if severity not in ("info", "attention", "critique"):
        raise ValueError("Sévérité invalide (info, attention, critique).")
    if category not in _ALLOWED_CATEGORIES:
        raise ValueError(f"Catégorie invalide. Valeurs : {', '.join(sorted(_ALLOWED_CATEGORIES))}")
    validate_operations_config({code: {"severity": severity, "label": label, "category": category}})
    return {
        "code": code,
        "label": label,
        "severity": severity,
        "category": category,
        "required": required,
    }


def list_operation_codes(conn) -> list:
    rows = conn.execute(
        f"""SELECT code, severity, label, category, required, updated_at
            FROM {TABLE} ORDER BY CAST(code AS INTEGER), code"""
    ).fetchall()
    return [
        {
            "code": r["code"],
            "severity": r["severity"],
            "label": r["label"],
            "category": r["category"],
            "required": bool(r["required"]),
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def categories_for_ui() -> list:
    return sorted(_ALLOWED_CATEGORIES)
