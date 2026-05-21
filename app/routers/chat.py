"""MySifa — Chat interne (DMs + canaux d'équipe).

Routes : /api/chat/*
Accès  : tout utilisateur authentifié.
"""
from __future__ import annotations

import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from config import BASE_DIR, ROLE_SUPERADMIN
from database import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

_PARIS = ZoneInfo("Europe/Paris")
_MAX_BODY = 4000
_PAGE_SIZE = 50
_MAX_ATTACHMENT = 10 * 1024 * 1024
_ALLOWED_EMOJIS = {"👍", "✅", "👀", "⚠️", "🔧", "❌"}
_MSG_SELECT = """m.id, m.user_id, m.user_nom, m.body, m.created_at,
                   m.attachment_url, m.attachment_name, m.attachment_mime, m.attachment_size,
                   u.avatar_url"""
_ALLOWED_ATTACHMENT_EXT = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".zip",
}
_ALLOWED_ATTACHMENT_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "text/plain", "text/csv",
    "application/zip", "application/x-zip-compressed",
}

_typing_lock = Lock()
_typing_state: dict[int, dict[int, dict]] = {}
_TYPING_TTL = 6.0


def _typing_cleanup(channel_id: int) -> None:
    """Supprime les entrées expirées pour un canal."""
    now = time.time()
    with _typing_lock:
        if channel_id not in _typing_state:
            return
        expired = [
            uid for uid, v in _typing_state[channel_id].items() if v["expires"] < now
        ]
        for uid in expired:
            del _typing_state[channel_id][uid]


_DEFAULT_CHANNELS = [
    ("général", "Canal général — toute l'équipe", None),
    (
        "fabrication",
        "Équipe fabrication",
        ["fabrication", "direction", "administration", "superadmin"],
    ),
    (
        "logistique",
        "Équipe logistique",
        ["logistique", "direction", "administration", "superadmin"],
    ),
]


def _now_iso() -> str:
    return datetime.now(_PARIS).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _require(request: Request) -> dict:
    return get_current_user(request)


def _message_dict(row, uid: int, reactions: Optional[list] = None) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "user_nom": row["user_nom"],
        "body": row["body"] or "",
        "created_at": row["created_at"],
        "avatar_url": row["avatar_url"] or "",
        "attachment_url": row["attachment_url"] or "",
        "attachment_name": row["attachment_name"] or "",
        "attachment_mime": row["attachment_mime"] or "",
        "attachment_size": row["attachment_size"] or 0,
        "is_mine": row["user_id"] == uid,
        "reactions": reactions if reactions is not None else [],
    }


def _fetch_reactions_map(conn, msg_ids: List[int], uid: int) -> dict[int, list]:
    reactions_map: dict[int, list] = {mid: [] for mid in msg_ids}
    if not msg_ids:
        return reactions_map
    placeholders = ",".join("?" * len(msg_ids))
    rx_rows = conn.execute(
        f"""SELECT r.message_id, r.emoji, COUNT(*) as count,
                   MAX(CASE WHEN r.user_id=? THEN 1 ELSE 0 END) as reacted_by_me
            FROM chat_reactions r
            WHERE r.message_id IN ({placeholders})
            GROUP BY r.message_id, r.emoji
            ORDER BY r.message_id, MIN(r.created_at) ASC""",
        [uid] + msg_ids,
    ).fetchall()
    for rx in rx_rows:
        reactions_map[rx["message_id"]].append({
            "emoji": rx["emoji"],
            "count": rx["count"],
            "reacted_by_me": bool(rx["reacted_by_me"]),
        })
    return reactions_map


def _safe_attachment_name(name: str) -> str:
    base = Path(name or "fichier").name
    base = re.sub(r"[^\w.\- ]", "_", base, flags=re.UNICODE).strip("._ ") or "fichier"
    return base[:120]


async def _save_chat_attachment(channel_id: int, upload: UploadFile) -> tuple[str, str, str, int]:
    raw_name = upload.filename or "fichier"
    safe = _safe_attachment_name(raw_name)
    ext = Path(safe).suffix.lower()
    if ext not in _ALLOWED_ATTACHMENT_EXT:
        raise HTTPException(
            status_code=400,
            detail="Type de fichier non accepté (images, PDF, Office, texte, zip).",
        )
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime and mime not in _ALLOWED_ATTACHMENT_MIMES:
        raise HTTPException(status_code=400, detail="Type de fichier non accepté.")
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(content) > _MAX_ATTACHMENT:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 Mo).")
    dest_dir = Path(BASE_DIR) / "uploads" / "chat" / str(channel_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex[:12]}{ext}"
    dest = dest_dir / stored
    with open(dest, "wb") as f:
        f.write(content)
    url = f"/uploads/chat/{channel_id}/{stored}"
    return url, safe, mime or "application/octet-stream", len(content)


def _seed_default_channels(conn, created_by: Optional[int]) -> List[str]:
    """Crée les canaux par défaut si absents. Retourne les noms créés."""
    now = _now_iso()
    created: List[str] = []
    for name, desc, roles in _DEFAULT_CHANNELS:
        existing = conn.execute(
            """SELECT id FROM chat_channels
               WHERE type='channel' AND lower(name)=lower(?) AND archived_at IS NULL LIMIT 1""",
            (name,),
        ).fetchone()
        if existing:
            continue
        cur = conn.execute(
            """INSERT INTO chat_channels (type, name, description, created_by, created_at)
               VALUES ('channel', ?, ?, ?, ?)""",
            (name, desc, created_by, now),
        )
        ch_id = cur.lastrowid
        if roles:
            members = conn.execute(
                f"SELECT id FROM users WHERE actif=1 AND role IN ({','.join('?' * len(roles))})",
                roles,
            ).fetchall()
        else:
            members = conn.execute("SELECT id FROM users WHERE actif=1").fetchall()
        for m in members:
            conn.execute(
                "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                (ch_id, m["id"], now),
            )
        created.append(name)
    return created


def seed_default_channels_on_startup() -> None:
    """Idempotent — appelé au démarrage de l'application."""
    with get_db() as conn:
        admin = conn.execute(
            "SELECT id FROM users WHERE role=? AND actif=1 LIMIT 1",
            (ROLE_SUPERADMIN,),
        ).fetchone()
        created_by = admin["id"] if admin else None
        created = _seed_default_channels(conn, created_by)
        conn.commit()
    if created:
        print(f"[MySifa] chat : canaux créés — {', '.join(created)}")


# ─── Canaux ──────────────────────────────────────────────────────────────────

@router.get("/channels")
def list_channels(request: Request):
    """Liste les canaux dont l'utilisateur est membre, avec compte de non-lus."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.id, c.type, c.name, c.description, c.created_at, c.created_by,
                      cm.last_read_at,
                      (SELECT COUNT(*) FROM chat_messages m
                       WHERE m.channel_id = c.id AND m.deleted_at IS NULL
                         AND m.user_id != ?
                         AND (cm.last_read_at IS NULL OR m.created_at > cm.last_read_at)
                      ) as unread_count,
                      (SELECT MAX(m2.created_at) FROM chat_messages m2
                       WHERE m2.channel_id = c.id AND m2.deleted_at IS NULL
                      ) as last_message_at,
                      (SELECT m3.body FROM chat_messages m3
                       WHERE m3.channel_id = c.id AND m3.deleted_at IS NULL
                       ORDER BY m3.created_at DESC LIMIT 1
                      ) as last_message_body,
                      (SELECT m4.user_nom FROM chat_messages m4
                       WHERE m4.channel_id = c.id AND m4.deleted_at IS NULL
                       ORDER BY m4.created_at DESC LIMIT 1
                      ) as last_message_from
               FROM chat_channels c
               JOIN chat_members cm ON cm.channel_id = c.id AND cm.user_id = ?
               WHERE c.archived_at IS NULL
               ORDER BY last_message_at DESC NULLS LAST""",
            (uid, uid),
        ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            if d["type"] == "direct":
                other = conn.execute(
                    """SELECT u.nom, u.id, u.avatar_url FROM chat_members cm2
                       JOIN users u ON u.id = cm2.user_id
                       WHERE cm2.channel_id = ? AND cm2.user_id != ?
                       LIMIT 1""",
                    (d["id"], uid),
                ).fetchone()
                d["display_name"] = other["nom"] if other else "Utilisateur inconnu"
                d["other_user_id"] = other["id"] if other else None
                d["other_user_avatar_url"] = (other["avatar_url"] or "") if other else ""
            else:
                d["display_name"] = d["name"] or "Canal sans nom"
                d["other_user_id"] = None
            result.append(d)

    return result


@router.post("/channels")
async def create_channel(request: Request):
    """
    Créer un canal ou démarrer un DM.
    DM : { type: 'direct', user_id: 42 }
    Canal : { type: 'channel', name: 'fabrication', description: '...', member_ids: [1,2,3] }
    """
    user = _require(request)
    uid = user["id"]
    data = await request.json()
    ch_type = (data.get("type") or "channel").strip()
    if ch_type not in ("channel", "direct"):
        raise HTTPException(status_code=400, detail="type doit être 'channel' ou 'direct'")

    now = _now_iso()

    with get_db() as conn:
        if ch_type == "direct":
            other_id = data.get("user_id")
            if not other_id:
                raise HTTPException(status_code=400, detail="user_id requis pour un DM")
            other_id = int(other_id)
            if other_id == uid:
                raise HTTPException(status_code=400, detail="Impossible de créer un DM avec soi-même")
            other = conn.execute(
                "SELECT id FROM users WHERE id=? AND actif=1 LIMIT 1",
                (other_id,),
            ).fetchone()
            if not other:
                raise HTTPException(status_code=404, detail="Utilisateur introuvable")

            existing = conn.execute(
                """SELECT c.id FROM chat_channels c
                   JOIN chat_members cm1 ON cm1.channel_id = c.id AND cm1.user_id = ?
                   JOIN chat_members cm2 ON cm2.channel_id = c.id AND cm2.user_id = ?
                   WHERE c.type = 'direct' AND c.archived_at IS NULL
                   LIMIT 1""",
                (uid, other_id),
            ).fetchone()
            if existing:
                return {"id": existing["id"], "existing": True}

            cur = conn.execute(
                "INSERT INTO chat_channels (type, created_by, created_at) VALUES ('direct',?,?)",
                (uid, now),
            )
            ch_id = cur.lastrowid
            for member_id in (uid, other_id):
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (ch_id, member_id, now),
                )

        else:
            name = (data.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="name requis pour un canal")
            if len(name) > 60:
                raise HTTPException(status_code=400, detail="Nom de canal trop long (max 60 caractères)")
            dupe = conn.execute(
                """SELECT id FROM chat_channels
                   WHERE type='channel' AND lower(name)=lower(?) AND archived_at IS NULL LIMIT 1""",
                (name,),
            ).fetchone()
            if dupe:
                raise HTTPException(status_code=409, detail=f"Un canal '{name}' existe déjà")

            description = (data.get("description") or "").strip() or None
            cur = conn.execute(
                """INSERT INTO chat_channels (type, name, description, created_by, created_at)
                   VALUES ('channel', ?, ?, ?, ?)""",
                (name, description, uid, now),
            )
            ch_id = cur.lastrowid

            member_ids = list({uid} | {int(m) for m in (data.get("member_ids") or [])})
            for mid in member_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (ch_id, mid, now),
                )

        conn.commit()

    return {"id": ch_id, "existing": False}


@router.post("/channels/{channel_id}/join")
def join_channel(channel_id: int, request: Request):
    """Rejoindre un canal existant (canaux publics uniquement — pas les DMs)."""
    user = _require(request)
    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(status_code=403, detail="Impossible de rejoindre un DM")
        conn.execute(
            "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
            (channel_id, user["id"], _now_iso()),
        )
        conn.commit()
    return {"joined": True}


@router.get("/channels/{channel_id}/members")
def channel_members(channel_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        rows = conn.execute(
            """SELECT u.id, u.nom, u.role, u.avatar_url, cm.joined_at, cm.last_read_at
               FROM chat_members cm JOIN users u ON u.id = cm.user_id
               WHERE cm.channel_id = ?
               ORDER BY u.nom""",
            (channel_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/channels/{channel_id}/members/{target_user_id}")
def remove_member(channel_id: int, target_user_id: int, request: Request):
    """Retire un membre d'un canal (admin, direction ou créateur du canal)."""
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction"}

    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type, created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(status_code=403, detail="Impossible de retirer un membre d'un DM")

        is_creator = ch["created_by"] == user["id"]
        if not is_admin and not is_creator:
            raise HTTPException(
                status_code=403,
                detail="Action réservée aux administrateurs ou au créateur du canal",
            )

        if target_user_id == user["id"]:
            raise HTTPException(
                status_code=400,
                detail="Utilisez 'Quitter le canal' pour vous retirer vous-même",
            )

        member = conn.execute(
            "SELECT 1 FROM chat_members WHERE channel_id=? AND user_id=? LIMIT 1",
            (channel_id, target_user_id),
        ).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Utilisateur non membre de ce canal")

        count = conn.execute(
            "SELECT COUNT(*) as c FROM chat_members WHERE channel_id=?",
            (channel_id,),
        ).fetchone()["c"]
        if count <= 1:
            raise HTTPException(status_code=400, detail="Impossible de retirer le dernier membre")

        conn.execute(
            "DELETE FROM chat_members WHERE channel_id=? AND user_id=?",
            (channel_id, target_user_id),
        )
        conn.commit()

    return {"removed": True}


@router.post("/channels/{channel_id}/typing")
def set_typing(channel_id: int, request: Request):
    """Signale que l'utilisateur est en train d'écrire (expire après _TYPING_TTL s)."""
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
    now = time.time()
    with _typing_lock:
        if channel_id not in _typing_state:
            _typing_state[channel_id] = {}
        _typing_state[channel_id][user["id"]] = {
            "nom": user.get("nom") or user.get("email", ""),
            "expires": now + _TYPING_TTL,
        }
    return {"ok": True}


@router.get("/channels/{channel_id}/typing")
def get_typing(channel_id: int, request: Request):
    """Utilisateurs en train d'écrire dans le canal (hors soi-même)."""
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
    _typing_cleanup(channel_id)
    now = time.time()
    with _typing_lock:
        entries = dict(_typing_state.get(channel_id, {}))
    typists = [
        v["nom"]
        for uid, v in entries.items()
        if uid != user["id"] and v["expires"] > now
    ]
    return {"typists": typists}


# ─── Messages ────────────────────────────────────────────────────────────────

@router.get("/channels/{channel_id}/messages")
def get_messages(
    channel_id: int,
    request: Request,
    before: Optional[str] = None,
    after: Optional[int] = None,
):
    """Messages d'un canal (récents, pagination `before`, ou nouveautés `after`)."""
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])

        if after is not None:
            after_id = int(after)
            rows = conn.execute(
                f"""SELECT {_MSG_SELECT}
                   FROM chat_messages m
                   LEFT JOIN users u ON u.id = m.user_id
                   WHERE m.channel_id=? AND m.deleted_at IS NULL AND m.id > ?
                   ORDER BY m.created_at ASC""",
                (channel_id, after_id),
            ).fetchall()
        elif before:
            rows = conn.execute(
                f"""SELECT {_MSG_SELECT}
                   FROM chat_messages m
                   LEFT JOIN users u ON u.id = m.user_id
                   WHERE m.channel_id=? AND m.deleted_at IS NULL AND m.created_at < ?
                   ORDER BY m.created_at DESC LIMIT ?""",
                (channel_id, before, _PAGE_SIZE),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {_MSG_SELECT}
                   FROM chat_messages m
                   LEFT JOIN users u ON u.id = m.user_id
                   WHERE m.channel_id=? AND m.deleted_at IS NULL
                   ORDER BY m.created_at DESC LIMIT ?""",
                (channel_id, _PAGE_SIZE),
            ).fetchall()

        uid = user["id"]
        if after is not None:
            ordered = list(rows)
        else:
            ordered = list(reversed(rows))
        msg_ids = [r["id"] for r in ordered]
        reactions_map = _fetch_reactions_map(conn, msg_ids, uid)

        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (_now_iso(), channel_id, user["id"]),
        )
        conn.commit()

    messages = [
        _message_dict(r, uid, reactions_map.get(r["id"], []))
        for r in ordered
    ]
    has_more = len(rows) == _PAGE_SIZE if before else False
    return {"messages": messages, "has_more": has_more}


@router.post("/channels/{channel_id}/messages")
async def send_message(
    channel_id: int,
    request: Request,
    file: Optional[UploadFile] = File(None),
):
    """Envoyer un message (JSON ou multipart avec pièce jointe)."""
    user = _require(request)
    body = ""
    upload = file
    content_type = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in content_type:
        form = await request.form()
        raw_body = form.get("body")
        body = (raw_body if isinstance(raw_body, str) else "").strip()
        if upload is None:
            f = form.get("file")
            if isinstance(f, UploadFile):
                upload = f
    else:
        data = await request.json()
        body = (data.get("body") or "").strip()

    if not body and not upload:
        raise HTTPException(status_code=400, detail="Message vide")
    if body and len(body) > _MAX_BODY:
        raise HTTPException(status_code=400, detail=f"Message trop long (max {_MAX_BODY} caractères)")

    att_url, att_name, att_mime, att_size = "", "", "", 0
    if upload is not None and (upload.filename or ""):
        with get_db() as conn:
            _assert_member(conn, channel_id, user["id"])
        att_url, att_name, att_mime, att_size = await _save_chat_attachment(channel_id, upload)

    now = _now_iso()
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        cur = conn.execute(
            """INSERT INTO chat_messages
               (channel_id, user_id, user_nom, body, created_at,
                attachment_url, attachment_name, attachment_mime, attachment_size)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                channel_id,
                user["id"],
                user.get("nom") or user.get("email", ""),
                body,
                now,
                att_url or None,
                att_name or None,
                att_mime or None,
                att_size or None,
            ),
        )
        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (now, channel_id, user["id"]),
        )
        conn.commit()
    return {
        "id": cur.lastrowid,
        "created_at": now,
        "body": body,
        "attachment_url": att_url,
        "attachment_name": att_name,
        "attachment_mime": att_mime,
        "attachment_size": att_size,
    }


@router.delete("/channels/{channel_id}/messages/{msg_id}")
def delete_message(channel_id: int, msg_id: int, request: Request):
    """Soft-delete (auteur ou admin)."""
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, deleted_at FROM chat_messages WHERE id=? AND channel_id=? LIMIT 1",
            (msg_id, channel_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Message introuvable")
        if row["deleted_at"]:
            raise HTTPException(status_code=410, detail="Message déjà supprimé")
        if not is_admin and row["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres messages")
        conn.execute(
            "UPDATE chat_messages SET deleted_at=? WHERE id=?",
            (_now_iso(), msg_id),
        )
        conn.commit()
    return {"deleted": True}


@router.post("/channels/{channel_id}/messages/{msg_id}/reactions")
async def toggle_reaction(channel_id: int, msg_id: int, request: Request):
    """Toggle une réaction emoji sur un message."""
    user = _require(request)
    data = await request.json()
    emoji = (data.get("emoji") or "").strip()
    if emoji not in _ALLOWED_EMOJIS:
        raise HTTPException(status_code=400, detail="Emoji non autorisé")

    now = _now_iso()
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        msg = conn.execute(
            "SELECT id FROM chat_messages WHERE id=? AND channel_id=? AND deleted_at IS NULL LIMIT 1",
            (msg_id, channel_id),
        ).fetchone()
        if not msg:
            raise HTTPException(status_code=404, detail="Message introuvable")

        existing = conn.execute(
            "SELECT id FROM chat_reactions WHERE message_id=? AND user_id=? AND emoji=? LIMIT 1",
            (msg_id, user["id"], emoji),
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM chat_reactions WHERE id=?", (existing["id"],))
            conn.commit()
            return {"added": False, "emoji": emoji}

        conn.execute(
            "INSERT INTO chat_reactions (message_id, user_id, user_nom, emoji, created_at) VALUES (?,?,?,?,?)",
            (msg_id, user["id"], user.get("nom") or user.get("email", ""), emoji, now),
        )
        conn.commit()
    return {"added": True, "emoji": emoji}


# ─── Utilitaires ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(request: Request, q: str = ""):
    """Liste des utilisateurs actifs (pour démarrer un DM ou ajouter à un canal)."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role, avatar_url FROM users WHERE actif=1 ORDER BY nom",
        ).fetchall()
    users = [dict(r) for r in rows if r["id"] != uid]
    if q:
        ql = q.lower()
        users = [u for u in users if ql in (u.get("nom") or "").lower()]
    return users


@router.get("/unread")
def unread_total(request: Request):
    """Total non-lus + dernier message (preview barre portail)."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as c
               FROM chat_messages m
               JOIN chat_members cm ON cm.channel_id = m.channel_id AND cm.user_id = ?
               WHERE m.deleted_at IS NULL AND m.user_id != ?
                 AND (cm.last_read_at IS NULL OR m.created_at > cm.last_read_at)""",
            (uid, uid),
        ).fetchone()
        last = conn.execute(
            """SELECT m.body, m.user_nom, m.created_at, ch.name AS channel_name, ch.type AS channel_type
               FROM chat_messages m
               JOIN chat_members cm ON cm.channel_id = m.channel_id AND cm.user_id = ?
               JOIN chat_channels ch ON ch.id = m.channel_id
               WHERE m.deleted_at IS NULL AND m.user_id != ?
                 AND (cm.last_read_at IS NULL OR m.created_at > cm.last_read_at)
               ORDER BY m.created_at DESC LIMIT 1""",
            (uid, uid),
        ).fetchone()
    last_msg = None
    if last:
        last_msg = dict(last)
        last_msg["from_nom"] = last["user_nom"]
    return {"unread": row["c"], "last_message": last_msg}


@router.post("/channels/seed-defaults")
def seed_default_channels(request: Request):
    """Crée les canaux par défaut si absents. Réservé au superadmin. Idempotent."""
    user = _require(request)
    if user.get("role") != ROLE_SUPERADMIN:
        raise HTTPException(status_code=403, detail="Réservé au superadmin")

    with get_db() as conn:
        created = _seed_default_channels(conn, user["id"])
        conn.commit()
    return {"created": created}


# ─── Helpers privés ──────────────────────────────────────────────────────────

def _assert_member(conn, channel_id: int, user_id: int) -> None:
    row = conn.execute(
        "SELECT 1 FROM chat_members WHERE channel_id=? AND user_id=? LIMIT 1",
        (channel_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="Accès refusé à ce canal")
