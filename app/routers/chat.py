"""MySifa — Chat interne (DMs + canaux d'équipe).

Routes : /api/chat/*
Accès  : tout utilisateur authentifié.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request

from config import ROLE_SUPERADMIN
from database import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

_PARIS = ZoneInfo("Europe/Paris")
_MAX_BODY = 4000
_PAGE_SIZE = 50

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
            """SELECT c.id, c.type, c.name, c.description, c.created_at,
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
                    """SELECT u.nom, u.id FROM chat_members cm2
                       JOIN users u ON u.id = cm2.user_id
                       WHERE cm2.channel_id = ? AND cm2.user_id != ?
                       LIMIT 1""",
                    (d["id"], uid),
                ).fetchone()
                d["display_name"] = other["nom"] if other else "Utilisateur inconnu"
                d["other_user_id"] = other["id"] if other else None
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
            """SELECT u.id, u.nom, u.role, cm.joined_at
               FROM chat_members cm JOIN users u ON u.id = cm.user_id
               WHERE cm.channel_id = ?
               ORDER BY u.nom""",
            (channel_id,),
        ).fetchall()
    return [dict(r) for r in rows]


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
                """SELECT id, user_id, user_nom, body, created_at
                   FROM chat_messages
                   WHERE channel_id=? AND deleted_at IS NULL AND id > ?
                   ORDER BY created_at ASC""",
                (channel_id, after_id),
            ).fetchall()
        elif before:
            rows = conn.execute(
                """SELECT id, user_id, user_nom, body, created_at
                   FROM chat_messages
                   WHERE channel_id=? AND deleted_at IS NULL AND created_at < ?
                   ORDER BY created_at DESC LIMIT ?""",
                (channel_id, before, _PAGE_SIZE),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, user_id, user_nom, body, created_at
                   FROM chat_messages
                   WHERE channel_id=? AND deleted_at IS NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (channel_id, _PAGE_SIZE),
            ).fetchall()

        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (_now_iso(), channel_id, user["id"]),
        )
        conn.commit()

    uid = user["id"]
    if after is not None:
        ordered = list(rows)
    else:
        ordered = list(reversed(rows))
    messages = [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "user_nom": r["user_nom"],
            "body": r["body"],
            "created_at": r["created_at"],
            "is_mine": r["user_id"] == uid,
        }
        for r in ordered
    ]
    has_more = len(rows) == _PAGE_SIZE if before else False
    return {"messages": messages, "has_more": has_more}


@router.post("/channels/{channel_id}/messages")
async def send_message(channel_id: int, request: Request):
    """Envoyer un message dans un canal."""
    user = _require(request)
    data = await request.json()
    body = (data.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message vide")
    if len(body) > _MAX_BODY:
        raise HTTPException(status_code=400, detail=f"Message trop long (max {_MAX_BODY} caractères)")

    now = _now_iso()
    with get_db() as conn:
        _assert_member(conn, channel_id, user["id"])
        cur = conn.execute(
            """INSERT INTO chat_messages (channel_id, user_id, user_nom, body, created_at)
               VALUES (?,?,?,?,?)""",
            (channel_id, user["id"], user.get("nom") or user.get("email", ""), body, now),
        )
        conn.execute(
            "UPDATE chat_members SET last_read_at=? WHERE channel_id=? AND user_id=?",
            (now, channel_id, user["id"]),
        )
        conn.commit()
    return {"id": cur.lastrowid, "created_at": now}


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


# ─── Utilitaires ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(request: Request, q: str = ""):
    """Liste des utilisateurs actifs (pour démarrer un DM ou ajouter à un canal)."""
    user = _require(request)
    uid = user["id"]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role FROM users WHERE actif=1 ORDER BY nom",
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
