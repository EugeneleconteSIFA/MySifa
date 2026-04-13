"""Messagerie interne MySifa (support → super admin).

- Tout utilisateur connecté peut envoyer un message au support (super admin).
- Seul le super admin peut lire/traiter la messagerie.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from config import SUPERADMIN_EMAIL
from database import get_db
from services.auth_service import get_current_user, require_superadmin


router = APIRouter(tags=["messages"])


def _norm_email(s: str) -> str:
    return str(s or "").strip().lower()


@router.post("/api/messages/contact")
async def contact_support(request: Request):
    """Créer un message adressé au super admin."""
    user = get_current_user(request)
    body = await request.json()
    subject = (body.get("subject") or "").strip()
    text = (body.get("message") or "").strip()
    if not text:
        raise HTTPException(400, "Message obligatoire")
    if len(text) > 8000:
        raise HTTPException(400, "Message trop long")
    if subject and len(subject) > 240:
        raise HTTPException(400, "Objet trop long")

    now = datetime.now().isoformat()
    to_email = _norm_email(SUPERADMIN_EMAIL)
    from_email = _norm_email(user.get("email"))
    from_name = (user.get("nom") or "").strip() or None
    from_user_id = int(user.get("id")) if user.get("id") is not None else None

    with get_db() as conn:
        conn.execute(
            """INSERT INTO messages
               (from_user_id, from_email, from_name, to_email, subject, body, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (from_user_id, from_email, from_name, to_email, subject or None, text, now),
        )
        conn.commit()
    return {"success": True}


@router.get("/api/messages/unread-count")
def unread_count(request: Request):
    """Badge non-lus (super admin)."""
    require_superadmin(request)
    to_email = _norm_email(SUPERADMIN_EMAIL)
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as n
               FROM messages
               WHERE to_email=? AND deleted=0 AND (read_at IS NULL OR TRIM(read_at)='')""",
            (to_email,),
        ).fetchone()
    return {"count": int(row["n"] if row else 0)}


@router.get("/api/messages")
def list_messages(request: Request, limit: int = 200):
    """Liste messagerie (super admin)."""
    require_superadmin(request)
    limit = int(limit or 200)
    limit = max(1, min(limit, 500))
    to_email = _norm_email(SUPERADMIN_EMAIL)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, from_email, from_name, subject, body, created_at, read_at
               FROM messages
               WHERE to_email=? AND deleted=0
               ORDER BY created_at DESC
               LIMIT ?""",
            (to_email, limit),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/messages/{message_id}/mark-read")
def mark_read(message_id: int, request: Request):
    require_superadmin(request)
    now = datetime.now().isoformat()
    to_email = _norm_email(SUPERADMIN_EMAIL)
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE messages
               SET read_at=COALESCE(read_at, ?)
               WHERE id=? AND to_email=? AND deleted=0""",
            (now, int(message_id), to_email),
        )
        conn.commit()
    if cur.rowcount <= 0:
        raise HTTPException(404, "Message introuvable")
    return {"success": True}


@router.post("/api/messages/{message_id}/toggle-treated")
def toggle_treated(message_id: int, request: Request):
    """Bascule traité/non traité (super admin)."""
    require_superadmin(request)
    to_email = _norm_email(SUPERADMIN_EMAIL)
    now = datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT read_at FROM messages WHERE id=? AND to_email=? AND deleted=0",
            (int(message_id), to_email),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Message introuvable")
        cur_read = str(row["read_at"] or "").strip()
        new_read = None if cur_read else now
        conn.execute(
            "UPDATE messages SET read_at=? WHERE id=? AND to_email=?",
            (new_read, int(message_id), to_email),
        )
        conn.commit()
    return {"success": True, "read_at": new_read}


@router.post("/api/messages/mark-all-read")
def mark_all_read(request: Request):
    require_superadmin(request)
    now = datetime.now().isoformat()
    to_email = _norm_email(SUPERADMIN_EMAIL)
    with get_db() as conn:
        conn.execute(
            """UPDATE messages
               SET read_at=COALESCE(read_at, ?)
               WHERE to_email=? AND deleted=0 AND (read_at IS NULL OR TRIM(read_at)='')""",
            (now, to_email),
        )
        conn.commit()
    return {"success": True}


@router.delete("/api/messages/{message_id}")
def delete_message(message_id: int, request: Request):
    require_superadmin(request)
    to_email = _norm_email(SUPERADMIN_EMAIL)
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE messages
               SET deleted=1
               WHERE id=? AND to_email=?""",
            (int(message_id), to_email),
        )
        conn.commit()
    if cur.rowcount <= 0:
        raise HTTPException(404, "Message introuvable")
    return {"success": True}

