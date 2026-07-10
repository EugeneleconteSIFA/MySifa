"""
Kernse — helper d'accès à la DB plateforme.

Point d'entrée unique pour toutes les requêtes plateforme (clients, audit_log,
platform_settings). Utilisé par `kernse-admin` uniquement — `kernse-landing`
n'a pas besoin de la DB plateforme (site public statique côté data).

Chemin de la DB : lu depuis `KERNSE_PLATFORM_DB_PATH` (env), défaut
`kernse/admin/data/platform.db` relatif au repo.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterable, Sequence


_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = _REPO_ROOT / "kernse" / "admin" / "data" / "platform.db"
PLATFORM_DB_PATH = Path(os.getenv("KERNSE_PLATFORM_DB_PATH", str(DEFAULT_DB_PATH)))


def _dict_factory(cursor: sqlite3.Cursor, row: Sequence[Any]) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_platform_db() -> sqlite3.Connection:
    """Retourne une nouvelle connexion à la DB plateforme (WAL + row dict)."""
    PLATFORM_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(PLATFORM_DB_PATH))
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def platform_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager : commit auto si pas d'exception, rollback sinon."""
    conn = get_platform_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Audit log — helper unique ──────────────────────────────────────────
def log_audit(
    conn: sqlite3.Connection,
    *,
    actor_email: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    actor_ip: str | None = None,
    note: str | None = None,
) -> int:
    """Insère une entrée dans `audit_log`. Doit être appelé dans la MÊME
    transaction que la modif métier (pas d'audit best-effort).

    Retour : id de l'entrée créée.
    """
    from kernse.shared.db.schema import utcnow_iso

    cur = conn.execute(
        """
        INSERT INTO audit_log
            (at, actor_email, actor_ip, action, entity_type, entity_id,
             before_json, after_json, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            utcnow_iso(),
            actor_email,
            actor_ip,
            action,
            entity_type,
            entity_id,
            json.dumps(before, ensure_ascii=False) if before is not None else None,
            json.dumps(after, ensure_ascii=False) if after is not None else None,
            note,
        ),
    )
    return int(cur.lastrowid)


# ─── platform_settings — helper lecture / écriture ──────────────────────
def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute(
        "SELECT value_json FROM platform_settings WHERE key=? LIMIT 1", (key,)
    ).fetchone()
    if not row:
        return default
    return json.loads(row["value_json"])


def set_setting(
    conn: sqlite3.Connection, key: str, value: Any, *, actor_email: str
) -> None:
    from kernse.shared.db.schema import utcnow_iso

    now = utcnow_iso()
    conn.execute(
        """
        INSERT INTO platform_settings(key, value_json, updated_at, updated_by)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at,
            updated_by = excluded.updated_by
        """,
        (key, json.dumps(value, ensure_ascii=False), now, actor_email),
    )


# ─── Clients — helpers de lecture ───────────────────────────────────────
def list_active_clients(conn: sqlite3.Connection) -> list[dict]:
    """Clients non-résiliés (les suspendus sont inclus — la console les
    affiche avec un badge distinct pour permettre la réactivation)."""
    return conn.execute(
        """
        SELECT * FROM clients
        WHERE terminated_at IS NULL
        ORDER BY company_name COLLATE NOCASE
        """
    ).fetchall()


def list_promotable_clients(conn: sqlite3.Connection) -> list[dict]:
    """Clients éligibles à une promotion de masse : actifs et non-épinglés."""
    return conn.execute(
        """
        SELECT * FROM clients
        WHERE suspended = 0 AND terminated_at IS NULL AND pinned = 0
        ORDER BY company_name COLLATE NOCASE
        """
    ).fetchall()


def get_client_by_slug(conn: sqlite3.Connection, slug: str) -> dict | None:
    row = conn.execute("SELECT * FROM clients WHERE slug=? LIMIT 1", (slug,)).fetchone()
    return row if row else None


def get_client(conn: sqlite3.Connection, client_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM clients WHERE id=? LIMIT 1", (client_id,)).fetchone()
    return row if row else None
