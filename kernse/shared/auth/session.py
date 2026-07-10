"""
Kernse — sessions superadmin plateforme.

Session = ligne dans `superadmin_sessions` + cookie signé côté client
contenant `session_id`. Le cookie est HTTP-only, Secure (en prod),
SameSite=Lax.

Rotation : à chaque login on crée une nouvelle session. À chaque succès
de 2FA on marque `twofa_ok=1`. On ne réutilise jamais une session déjà
existante.

Purge : les sessions expirées sont supprimées à la demande via
`purge_expired_sessions()` (à appeler périodiquement dans un job).
"""
from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from kernse.shared.db.schema import utcnow_iso


DEFAULT_SESSION_HOURS = 4
SESSION_ID_BYTES = 32  # 64 hex chars


def create_session(
    conn: sqlite3.Connection,
    *,
    email: str,
    ip: str | None = None,
    user_agent: str | None = None,
    hours: int = DEFAULT_SESSION_HOURS,
    twofa_ok: bool = False,
) -> str:
    """Crée une nouvelle session et retourne le `session_id` (à mettre en cookie)."""
    session_id = secrets.token_hex(SESSION_ID_BYTES)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=hours)
    conn.execute(
        """
        INSERT INTO superadmin_sessions
            (session_id, email, created_at, expires_at, ip, user_agent, twofa_ok)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            email.lower(),
            utcnow_iso(),
            expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            ip,
            (user_agent or "")[:400] or None,
            1 if twofa_ok else 0,
        ),
    )
    return session_id


def get_session(conn: sqlite3.Connection, session_id: str) -> dict | None:
    """Lit une session par son id. Retourne None si absente ou expirée."""
    if not session_id or len(session_id) != SESSION_ID_BYTES * 2:
        return None
    row = conn.execute(
        "SELECT * FROM superadmin_sessions WHERE session_id = ? LIMIT 1",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    expires = row["expires_at"]
    if expires < utcnow_iso():
        # Session expirée — on nettoie au vol.
        conn.execute("DELETE FROM superadmin_sessions WHERE session_id = ?", (session_id,))
        return None
    return dict(row)


def mark_2fa_ok(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute(
        "UPDATE superadmin_sessions SET twofa_ok = 1 WHERE session_id = ?",
        (session_id,),
    )


def destroy_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute(
        "DELETE FROM superadmin_sessions WHERE session_id = ?",
        (session_id,),
    )


def destroy_all_sessions_for(conn: sqlite3.Connection, email: str) -> int:
    """Détruit toutes les sessions d'un email (logout global). Renvoie le nb supprimé."""
    cur = conn.execute(
        "DELETE FROM superadmin_sessions WHERE email = ?",
        (email.lower(),),
    )
    return cur.rowcount


def purge_expired_sessions(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "DELETE FROM superadmin_sessions WHERE expires_at < ?",
        (utcnow_iso(),),
    )
    return cur.rowcount
