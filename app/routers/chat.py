"""MySifa — Chat interne (DMs + canaux d'équipe).

Routes : /api/chat/*
Accès  : tout utilisateur authentifié.
"""
from __future__ import annotations

import re
import time
import unicodedata
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
_MSG_SELECT = """m.id, m.user_id, m.user_nom, m.body, m.created_at, m.edited_at,
                   m.pinned_at, m.pinned_by, m.deleted_at,
                   m.reply_to_id, m.is_forwarded, m.forwarded_from_nom,
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


def _mention_slug(nom: str) -> str:
    """Identifiant de mention sans espaces ni accents (ex. Jean Dupont → Jean_Dupont)."""
    s = unicodedata.normalize("NFD", str(nom or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    parts = re.findall(r"[A-Za-z0-9]+", s)
    return "_".join(parts)


def _record_mentions_from_body(
    conn, msg_id: int, channel_id: int, body: str, author_id: int, now_m: str
) -> None:
    """Enregistre les mentions @tous et @SlugNom dans chat_mentions."""
    members = conn.execute(
        """SELECT u.id, u.nom FROM chat_members cm
           JOIN users u ON u.id = cm.user_id
           WHERE cm.channel_id = ? AND u.id != ?""",
        (channel_id, author_id),
    ).fetchall()
    if re.search(r"@(tous|all)\b", body, re.IGNORECASE):
        for m in members:
            conn.execute(
                """INSERT INTO chat_mentions
                   (message_id, channel_id, mentioned_user_id, is_all, created_at)
                   VALUES (?,?,?,1,?)""",
                (msg_id, channel_id, m["id"], now_m),
            )
        return

    tokens = {t.lower() for t in re.findall(r"@([A-Za-z0-9_]+)", body)}
    tokens.discard("tous")
    tokens.discard("all")
    mentioned_ids: set[int] = set()
    for token in tokens:
        for m in members:
            mid = int(m["id"])
            if mid in mentioned_ids:
                continue
            slug = _mention_slug(m["nom"] or "")
            if slug and slug.lower() == token:
                conn.execute(
                    """INSERT INTO chat_mentions
                       (message_id, channel_id, mentioned_user_id, is_all, created_at)
                       VALUES (?,?,?,0,?)""",
                    (msg_id, channel_id, mid, now_m),
                )
                mentioned_ids.add(mid)
                break
            nom = (m["nom"] or "").strip()
            for word in nom.split():
                if word.lower().startswith(token) and len(token) >= 2:
                    conn.execute(
                        """INSERT INTO chat_mentions
                           (message_id, channel_id, mentioned_user_id, is_all, created_at)
                           VALUES (?,?,?,0,?)""",
                        (msg_id, channel_id, mid, now_m),
                    )
                    mentioned_ids.add(mid)
                    break
            if mid in mentioned_ids:
                break


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


def _message_dict(
    row, uid: int, reactions: Optional[list] = None, reply_to: Optional[dict] = None
) -> dict:
    is_deleted = bool(row["deleted_at"])
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "user_nom": row["user_nom"],
        "body": "" if is_deleted else (row["body"] or ""),
        "is_soft_deleted": is_deleted,
        "created_at": row["created_at"],
        "edited_at": "" if is_deleted else (row["edited_at"] or ""),
        "pinned_at": row["pinned_at"] or "",
        "pinned_by": row["pinned_by"] or None,
        "avatar_url": row["avatar_url"] or "",
        "attachment_url": "" if is_deleted else (row["attachment_url"] or ""),
        "attachment_name": "" if is_deleted else (row["attachment_name"] or ""),
        "attachment_mime": "" if is_deleted else (row["attachment_mime"] or ""),
        "attachment_size": row["attachment_size"] or 0,
        "reply_to_id": row["reply_to_id"] if row["reply_to_id"] else None,
        "reply_to": reply_to,
        "is_forwarded": bool(row["is_forwarded"]),
        "forwarded_from_nom": row["forwarded_from_nom"] or "",
        "is_mine": row["user_id"] == uid,
        "reactions": [] if is_deleted else (reactions if reactions is not None else []),
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
    user_rows = conn.execute(
        f"""SELECT message_id, emoji, user_nom
            FROM chat_reactions
            WHERE message_id IN ({placeholders})
            ORDER BY message_id, emoji, created_at ASC""",
        msg_ids,
    ).fetchall()
    users_by_key: dict[tuple[int, str], list] = {}
    for ur in user_rows:
        key = (ur["message_id"], ur["emoji"])
        name = (ur["user_nom"] or "").strip() or "Utilisateur"
        users_by_key.setdefault(key, []).append(name)
    for rx in rx_rows:
        key = (rx["message_id"], rx["emoji"])
        reactions_map[rx["message_id"]].append({
            "emoji": rx["emoji"],
            "count": rx["count"],
            "reacted_by_me": bool(rx["reacted_by_me"]),
            "users": users_by_key.get(key, []),
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
            """SELECT c.id, c.type, c.name, c.description, c.emoji, c.created_at, c.created_by,
                      cm.last_read_at,
                      (SELECT COUNT(*) FROM chat_mentions mn
                       WHERE mn.channel_id = c.id
                         AND mn.mentioned_user_id = ?
                         AND mn.read_at IS NULL
                      ) as mention_count,
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
            (uid, uid, uid),
        ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            if d["type"] == "direct":
                other = conn.execute(
                    """SELECT u.nom, u.id, u.avatar_url, u.humeur_active, u.humeur_valeur, u.humeur_date FROM chat_members cm2
                       JOIN users u ON u.id = cm2.user_id
                       WHERE cm2.channel_id = ? AND cm2.user_id != ?
                       LIMIT 1""",
                    (d["id"], uid),
                ).fetchone()
                d["display_name"] = other["nom"] if other else "Utilisateur inconnu"
                d["other_user_id"] = other["id"] if other else None
                d["other_user_avatar_url"] = (other["avatar_url"] or "") if other else ""
                today = datetime.now().strftime("%Y-%m-%d")
                if other and other["humeur_active"] and other["humeur_valeur"] and other["humeur_date"] == today:
                    d["other_user_humeur"] = other["humeur_valeur"]
                else:
                    d["other_user_humeur"] = ""
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


@router.patch("/channels/{channel_id}")
async def update_channel(channel_id: int, request: Request):
    """Mettre à jour nom, description et emoji d'un canal. Réservé admins ou créateur."""
    user = _require(request)
    data = await request.json()
    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type, created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(status_code=400, detail="Impossible de modifier un DM")
        if not _can_manage_channel(user, ch):
            raise HTTPException(status_code=403, detail="Action réservée aux administrateurs ou au créateur")
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip() or None
        emoji = (data.get("emoji") or "").strip() or None
        if not name:
            raise HTTPException(status_code=400, detail="Nom requis")
        if len(name) > 60:
            raise HTTPException(status_code=400, detail="Nom trop long (max 60 caractères)")
        if emoji and len(emoji) > 4:
            raise HTTPException(status_code=400, detail="Emoji invalide")
        conn.execute(
            "UPDATE chat_channels SET name=?, description=?, emoji=? WHERE id=?",
            (name, description, emoji, channel_id),
        )
        conn.commit()
    return {"updated": True}


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


def _can_manage_channel(user: dict, ch) -> bool:
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    return is_admin or ch["created_by"] == user["id"]


@router.post("/channels/{channel_id}/members")
async def add_member(channel_id: int, request: Request):
    """Ajouter un membre à un canal (admin, direction, administration ou créateur)."""
    user = _require(request)
    data = await request.json()
    target_id = data.get("user_id")
    if target_id is None:
        raise HTTPException(status_code=400, detail="user_id requis")
    target_id = int(target_id)

    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type, created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(status_code=403, detail="Impossible d'ajouter un membre à un DM")
        if not _can_manage_channel(user, ch):
            raise HTTPException(
                status_code=403,
                detail="Action réservée aux administrateurs ou au créateur du canal",
            )
        _assert_member(conn, channel_id, user["id"])
        target = conn.execute(
            "SELECT id FROM users WHERE id=? AND actif=1 LIMIT 1",
            (target_id,),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        existing = conn.execute(
            "SELECT 1 FROM chat_members WHERE channel_id=? AND user_id=? LIMIT 1",
            (channel_id, target_id),
        ).fetchone()
        if existing:
            return {"added": False, "already_member": True}
        conn.execute(
            "INSERT INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
            (channel_id, target_id, _now_iso()),
        )
        conn.commit()
    return {"added": True}


@router.get("/channels/{channel_id}/members")
def channel_members(channel_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        rows = conn.execute(
            """SELECT u.id, u.nom, u.role, u.avatar_url, u.humeur_active, u.humeur_valeur, u.humeur_date, cm.joined_at, cm.last_read_at
               FROM chat_members cm JOIN users u ON u.id = cm.user_id
               WHERE cm.channel_id = ?
               ORDER BY u.nom""",
            (channel_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/channels/{channel_id}/members/{target_user_id}")
def remove_member(channel_id: int, target_user_id: int, request: Request):
    """Retire un membre d'un canal (admin, direction, administration ou créateur du canal)."""
    user = _require(request)

    with get_db() as conn:
        ch = conn.execute(
            "SELECT id, type, created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Canal introuvable")
        if ch["type"] == "direct":
            raise HTTPException(status_code=403, detail="Impossible de retirer un membre d'un DM")

        if not _can_manage_channel(user, ch):
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
                   WHERE m.channel_id=? AND m.id > ?
                   ORDER BY m.created_at ASC""",
                (channel_id, after_id),
            ).fetchall()
        elif before:
            rows = conn.execute(
                f"""SELECT {_MSG_SELECT}
                   FROM chat_messages m
                   LEFT JOIN users u ON u.id = m.user_id
                   WHERE m.channel_id=? AND m.created_at < ?
                   ORDER BY m.created_at DESC LIMIT ?""",
                (channel_id, before, _PAGE_SIZE),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {_MSG_SELECT}
                   FROM chat_messages m
                   LEFT JOIN users u ON u.id = m.user_id
                   WHERE m.channel_id=?
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

        # Fetch reply_to messages (non-deleted only, lightweight)
        reply_ids = list({r["reply_to_id"] for r in ordered if r["reply_to_id"]})
        reply_map: dict[int, dict] = {}
        if reply_ids:
            ph = ",".join("?" * len(reply_ids))
            rrows = conn.execute(
                f"""SELECT m.id, m.user_nom, m.body, m.deleted_at
                    FROM chat_messages m WHERE m.id IN ({ph})""",
                reply_ids,
            ).fetchall()
            for rr in rrows:
                reply_map[rr["id"]] = {
                    "id": rr["id"],
                    "user_nom": rr["user_nom"] or "",
                    "body": "" if rr["deleted_at"] else (rr["body"] or ""),
                    "is_soft_deleted": bool(rr["deleted_at"]),
                }

        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (_now_iso(), channel_id, user["id"]),
        )
        conn.commit()

    messages = [
        _message_dict(r, uid, reactions_map.get(r["id"], []),
                      reply_map.get(r["reply_to_id"]) if r["reply_to_id"] else None)
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
    gif_url = ""
    reply_to_id_raw = None
    att_url, att_name, att_mime, att_size = "", "", "", 0
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
        gif_url = (data.get("gif_url") or "").strip()
        reply_to_id_raw = data.get("reply_to_id")
        if gif_url:
            allowed_prefixes = (
                "https://media.giphy.com/",
                "https://media0.giphy.com/",
                "https://media1.giphy.com/",
                "https://media2.giphy.com/",
                "https://media3.giphy.com/",
                "https://media4.giphy.com/",
            )
            if not any(gif_url.startswith(p) for p in allowed_prefixes):
                raise HTTPException(status_code=400, detail="URL GIF non autorisée")
            att_url = gif_url
            att_name = "GIF"
            att_mime = "image/gif"
            att_size = 0

    if not body and not upload and not gif_url:
        raise HTTPException(status_code=400, detail="Message vide")
    if body and len(body) > _MAX_BODY:
        raise HTTPException(status_code=400, detail=f"Message trop long (max {_MAX_BODY} caractères)")

    if upload is not None and (upload.filename or ""):
        with get_db() as conn:
            _assert_member(conn, channel_id, user["id"])
        att_url, att_name, att_mime, att_size = await _save_chat_attachment(channel_id, upload)

    now = _now_iso()
    reply_to_id: Optional[int] = None
    if reply_to_id_raw is not None:
        try:
            reply_to_id = int(reply_to_id_raw)
        except (TypeError, ValueError):
            reply_to_id = None

    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        # Validate reply_to_id belongs to this channel
        if reply_to_id is not None:
            rcheck = conn.execute(
                "SELECT id FROM chat_messages WHERE id=? AND channel_id=? LIMIT 1",
                (reply_to_id, channel_id),
            ).fetchone()
            if not rcheck:
                reply_to_id = None
        cur = conn.execute(
            """INSERT INTO chat_messages
               (channel_id, user_id, user_nom, body, created_at,
                attachment_url, attachment_name, attachment_mime, attachment_size,
                reply_to_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
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
                reply_to_id,
            ),
        )
        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (now, channel_id, user["id"]),
        )
        conn.commit()
        try:
            if body:
                now_m = _now_iso()
                msg_id = cur.lastrowid
                _record_mentions_from_body(
                    conn, msg_id, channel_id, body, user["id"], now_m
                )
                conn.commit()
        except Exception:
            pass
    return {
        "id": cur.lastrowid,
        "created_at": now,
        "body": body,
        "attachment_url": att_url,
        "attachment_name": att_name,
        "attachment_mime": att_mime,
        "attachment_size": att_size,
    }


@router.patch("/channels/{channel_id}/messages/{msg_id}")
async def edit_message(channel_id: int, msg_id: int, request: Request):
    """Modifier un message (auteur uniquement, 15 min max après envoi)."""
    user = _require(request)
    data = await request.json()
    new_body = (data.get("body") or "").strip()
    if not new_body:
        raise HTTPException(status_code=400, detail="Message vide")
    if len(new_body) > _MAX_BODY:
        raise HTTPException(status_code=400, detail=f"Message trop long (max {_MAX_BODY} caractères)")
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, created_at, deleted_at FROM chat_messages WHERE id=? AND channel_id=? LIMIT 1",
            (msg_id, channel_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Message introuvable")
        if row["deleted_at"]:
            raise HTTPException(status_code=410, detail="Message supprimé")
        if row["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres messages")
        try:
            sent = datetime.fromisoformat(row["created_at"])
            age = (datetime.now(_PARIS).replace(tzinfo=None) - sent).total_seconds()
            if age > 900:
                raise HTTPException(status_code=403, detail="Modification impossible après 15 minutes")
        except HTTPException:
            raise
        except Exception:
            pass
        conn.execute(
            "UPDATE chat_messages SET body=?, edited_at=? WHERE id=?",
            (new_body, _now_iso(), msg_id),
        )
        conn.commit()
    return {"edited": True, "body": new_body}


@router.get("/channels/{channel_id}/pinned")
def pinned_messages(channel_id: int, request: Request):
    """Messages épinglés du canal (max 10)."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        _assert_member(conn, channel_id, uid)
        rows = conn.execute(
            f"""SELECT {_MSG_SELECT}
               FROM chat_messages m
               LEFT JOIN users u ON u.id = m.user_id
               WHERE m.channel_id=? AND m.pinned_at IS NOT NULL AND m.deleted_at IS NULL
               ORDER BY m.pinned_at DESC LIMIT 10""",
            (channel_id,),
        ).fetchall()
        reactions_map = _fetch_reactions_map(conn, [r["id"] for r in rows], uid)
    return [_message_dict(r, uid, reactions_map.get(r["id"], [])) for r in rows]


@router.post("/channels/{channel_id}/messages/{msg_id}/pin")
def pin_message(channel_id: int, msg_id: int, request: Request):
    """Épingler un message. Réservé admins ou créateur du canal."""
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    with get_db() as conn:
        ch = conn.execute(
            "SELECT created_by FROM chat_channels WHERE id=? AND archived_at IS NULL LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Canal introuvable")
        if not is_admin and ch["created_by"] != user["id"]:
            raise HTTPException(status_code=403, detail="Réservé aux administrateurs ou au créateur du canal")
        msg = conn.execute(
            "SELECT id FROM chat_messages WHERE id=? AND channel_id=? AND deleted_at IS NULL LIMIT 1",
            (msg_id, channel_id),
        ).fetchone()
        if not msg:
            raise HTTPException(status_code=404, detail="Message introuvable")
        conn.execute(
            "UPDATE chat_messages SET pinned_at=?, pinned_by=? WHERE id=?",
            (_now_iso(), user["id"], msg_id),
        )
        conn.commit()
    return {"pinned": True}


@router.delete("/channels/{channel_id}/messages/{msg_id}/pin")
def unpin_message(channel_id: int, msg_id: int, request: Request):
    """Retirer l'épingle d'un message."""
    user = _require(request)
    is_admin = user.get("role") in {"superadmin", "direction", "administration"}
    with get_db() as conn:
        ch = conn.execute(
            "SELECT created_by FROM chat_channels WHERE id=? LIMIT 1",
            (channel_id,),
        ).fetchone()
        if not is_admin and (not ch or ch["created_by"] != user["id"]):
            raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
        conn.execute(
            "UPDATE chat_messages SET pinned_at=NULL, pinned_by=NULL WHERE id=? AND channel_id=?",
            (msg_id, channel_id),
        )
        conn.commit()
    return {"unpinned": True}


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


@router.post("/channels/{channel_id}/messages/{msg_id}/forward")
async def forward_message(channel_id: int, msg_id: int, request: Request):
    """Transférer un message vers un ou plusieurs utilisateurs (DMs).

    Body: { "user_ids": [1, 2, 3] }
    Crée un DM avec chaque utilisateur cible (ou réutilise l'existant)
    et y envoie le message avec is_forwarded=1.
    """
    user = _require(request)
    uid = user["id"]
    data = await request.json()
    target_user_ids: list[int] = [int(x) for x in (data.get("user_ids") or []) if x]
    if not target_user_ids:
        raise HTTPException(status_code=400, detail="Au moins un destinataire requis")
    if len(target_user_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 destinataires")

    now = _now_iso()
    with get_db() as conn:
        _assert_member(conn, channel_id, uid)
        # Fetch original message
        orig = conn.execute(
            "SELECT id, user_nom, body, deleted_at, attachment_url, attachment_name, attachment_mime, attachment_size FROM chat_messages WHERE id=? AND channel_id=? LIMIT 1",
            (msg_id, channel_id),
        ).fetchone()
        if not orig:
            raise HTTPException(status_code=404, detail="Message introuvable")
        if orig["deleted_at"]:
            raise HTTPException(status_code=410, detail="Impossible de transférer un message supprimé")

        forwarded_from_nom = orig["user_nom"] or ""
        body = orig["body"] or ""
        att_url = orig["attachment_url"] or ""
        att_name = orig["attachment_name"] or ""
        att_mime = orig["attachment_mime"] or ""
        att_size = orig["attachment_size"] or 0

        created_channel_ids: list[int] = []

        for target_uid in target_user_ids:
            if target_uid == uid:
                continue
            # Check user exists
            tuser = conn.execute(
                "SELECT id FROM users WHERE id=? AND actif=1 LIMIT 1", (target_uid,)
            ).fetchone()
            if not tuser:
                continue
            # Find or create DM
            existing_dm = conn.execute(
                """SELECT c.id FROM chat_channels c
                   JOIN chat_members cm1 ON cm1.channel_id = c.id AND cm1.user_id = ?
                   JOIN chat_members cm2 ON cm2.channel_id = c.id AND cm2.user_id = ?
                   WHERE c.type = 'direct' AND c.archived_at IS NULL LIMIT 1""",
                (uid, target_uid),
            ).fetchone()
            if existing_dm:
                dm_id = existing_dm["id"]
            else:
                cur_dm = conn.execute(
                    "INSERT INTO chat_channels (type, created_by, created_at) VALUES ('direct', ?, ?)",
                    (uid, now),
                )
                dm_id = cur_dm.lastrowid
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (dm_id, uid, now),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO chat_members (channel_id, user_id, joined_at) VALUES (?,?,?)",
                    (dm_id, target_uid, now),
                )
            # Insert forwarded message
            conn.execute(
                """INSERT INTO chat_messages
                   (channel_id, user_id, user_nom, body, created_at,
                    attachment_url, attachment_name, attachment_mime, attachment_size,
                    is_forwarded, forwarded_from_nom)
                   VALUES (?,?,?,?,?,?,?,?,?,1,?)""",
                (
                    dm_id,
                    uid,
                    user.get("nom") or user.get("email", ""),
                    body,
                    now,
                    att_url or None,
                    att_name or None,
                    att_mime or None,
                    att_size or None,
                    forwarded_from_nom,
                ),
            )
            conn.execute(
                "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
                (now, dm_id, uid),
            )
            created_channel_ids.append(dm_id)

        conn.commit()

    return {"forwarded": True, "channel_ids": created_channel_ids}


@router.post("/channels/{channel_id}/messages/{msg_id}/reactions")
async def toggle_reaction(channel_id: int, msg_id: int, request: Request):
    """
    Réaction emoji — une seule par utilisateur et par message.
    Même emoji : retire la réaction.
    Autre emoji : remplace la réaction précédente.
    """
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

        mine = conn.execute(
            "SELECT id, emoji FROM chat_reactions WHERE message_id=? AND user_id=?",
            (msg_id, user["id"]),
        ).fetchall()

        for row in mine:
            if row["emoji"] == emoji:
                conn.execute("DELETE FROM chat_reactions WHERE id=?", (row["id"],))
                conn.commit()
                return {"added": False, "emoji": emoji, "replaced": None}

        for row in mine:
            conn.execute("DELETE FROM chat_reactions WHERE id=?", (row["id"],))

        replaced = mine[0]["emoji"] if mine else None
        conn.execute(
            "INSERT INTO chat_reactions (message_id, user_id, user_nom, emoji, created_at) VALUES (?,?,?,?,?)",
            (msg_id, user["id"], user.get("nom") or user.get("email", ""), emoji, now),
        )
        conn.commit()
    return {"added": True, "emoji": emoji, "replaced": replaced}


# ─── Mentions, GIPHY, préférences ────────────────────────────────────────────

@router.get("/mentions/unread")
def unread_mentions(request: Request):
    """Nombre total de mentions non lues pour l'utilisateur connecté."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as n FROM chat_mentions WHERE mentioned_user_id=? AND read_at IS NULL",
            (uid,),
        ).fetchone()
    return {"count": int(row["n"] if row else 0)}


def _fmt_gif(g: dict) -> dict:
    images = g.get("images", {})
    preview = (
        images.get("fixed_height", {}).get("url", "")
        or images.get("fixed_height_small", {}).get("url", "")
    )
    original = images.get("original", {}).get("url", "")
    downsized = images.get("downsized", {}).get("url", original)
    return {
        "id": g.get("id", ""),
        "title": g.get("title", ""),
        "url": downsized or original,
        "preview_url": preview or downsized or original,
    }


@router.get("/giphy/search")
def giphy_search(request: Request, q: str = "", limit: int = 24):
    """Proxy GIPHY search. Nécessite GIPHY_API_KEY dans config.py."""
    _require(request)
    from config import GIPHY_API_KEY
    if not GIPHY_API_KEY:
        return {"data": [], "disabled": True}
    limit = max(1, min(int(limit), 48))
    try:
        import httpx
        r = httpx.get(
            "https://api.giphy.com/v1/gifs/search",
            params={"api_key": GIPHY_API_KEY, "q": q, "limit": limit, "rating": "pg", "lang": "fr"},
            timeout=8.0,
        )
        r.raise_for_status()
        gifs = r.json().get("data", [])
    except Exception:
        raise HTTPException(status_code=502, detail="Erreur GIPHY")
    return {"data": [_fmt_gif(g) for g in gifs], "disabled": False}


@router.get("/giphy/trending")
def giphy_trending(request: Request, limit: int = 24):
    """Proxy GIPHY trending."""
    _require(request)
    from config import GIPHY_API_KEY
    if not GIPHY_API_KEY:
        return {"data": [], "disabled": True}
    limit = max(1, min(int(limit), 48))
    try:
        import httpx
        r = httpx.get(
            "https://api.giphy.com/v1/gifs/trending",
            params={"api_key": GIPHY_API_KEY, "limit": limit, "rating": "pg"},
            timeout=8.0,
        )
        r.raise_for_status()
        gifs = r.json().get("data", [])
    except Exception:
        raise HTTPException(status_code=502, detail="Erreur GIPHY")
    return {"data": [_fmt_gif(g) for g in gifs], "disabled": False}


@router.patch("/notif-prefs")
async def update_notif_prefs(request: Request):
    """Enregistre la préférence notifications navigateur."""
    user = _require(request)
    data = await request.json()
    browser_notif = 1 if data.get("browser_notif") else 0
    now = _now_iso()
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET notif_browser=?, notif_asked_at=? WHERE id=?",
            (browser_notif, now, user["id"]),
        )
        conn.commit()
    return {"ok": True}


# ─── Utilitaires ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(request: Request, q: str = ""):
    """Liste des utilisateurs actifs (pour démarrer un DM ou ajouter à un canal)."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role, avatar_url, humeur_active, humeur_valeur, humeur_date FROM users WHERE actif=1 ORDER BY nom",
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
