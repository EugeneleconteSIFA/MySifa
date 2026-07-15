"""MySifa — Suivi des guides in-app (tutos par onglet/vue).

Prefix : /api/guides
Table  : user_guide_progress (voir migration 181 dans app/core/database.py)

Endpoints utilisateur :
  GET  /api/guides/progress               → progression de l'utilisateur courant
  POST /api/guides/heartbeat              → marque une etape vue + delta temps
  POST /api/guides/ack                    → marque le guide comme "lu et compris"

Endpoints admin (superadmin/direction) :
  GET    /api/guides/admin/overview       → matrice utilisateurs x guides
  POST   /api/guides/admin/reset          → reset une progression (user + guide)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/guides", tags=["guides"])

ADMIN_ROLES = {"superadmin", "direction"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Reserve superadmin/direction")
    return user


# ─── Endpoints utilisateur ────────────────────────────────────────────────

@router.get("/progress")
def get_progress(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT guide_key, total_steps, steps_seen_bitmap, total_time_ms,
                      open_count, opened_at, completed_at, acknowledged_at
               FROM user_guide_progress WHERE user_id=?""",
            (user["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


class HeartbeatBody(BaseModel):
    guide_key: str
    step_idx: int          # index de l'etape actuellement vue (0-based)
    total_steps: int       # nombre total de steps dans ce guide
    delta_ms: int = 0      # temps ecoule depuis le dernier heartbeat


@router.post("/heartbeat")
def heartbeat(body: HeartbeatBody, request: Request):
    user = get_current_user(request)
    if body.step_idx < 0 or body.step_idx >= max(body.total_steps, 1):
        raise HTTPException(status_code=400, detail="step_idx invalide")
    if body.total_steps <= 0 or body.total_steps > 64:
        raise HTTPException(status_code=400, detail="total_steps invalide (1-64)")
    delta = max(0, min(int(body.delta_ms or 0), 60_000))  # cap 60s par heartbeat
    now = _now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_guide_progress WHERE user_id=? AND guide_key=?",
            (user["id"], body.guide_key),
        ).fetchone()
        bit = 1 << body.step_idx
        if row is None:
            conn.execute(
                """INSERT INTO user_guide_progress
                   (user_id, guide_key, total_steps, steps_seen_bitmap,
                    total_time_ms, open_count, opened_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (user["id"], body.guide_key, body.total_steps, bit, delta, 1, now),
            )
        else:
            new_bitmap = int(row["steps_seen_bitmap"] or 0) | bit
            new_time = int(row["total_time_ms"] or 0) + delta
            # Marquer completed_at si toutes les etapes sont vues
            full_mask = (1 << body.total_steps) - 1
            completed_at = row["completed_at"]
            if completed_at is None and (new_bitmap & full_mask) == full_mask:
                completed_at = now
            conn.execute(
                """UPDATE user_guide_progress SET
                   total_steps=?, steps_seen_bitmap=?, total_time_ms=?,
                   completed_at=COALESCE(completed_at, ?)
                   WHERE user_id=? AND guide_key=?""",
                (body.total_steps, new_bitmap, new_time, completed_at,
                 user["id"], body.guide_key),
            )
        conn.commit()
    return {"ok": True}


class AckBody(BaseModel):
    guide_key: str


@router.post("/ack")
def ack_guide(body: AckBody, request: Request):
    user = get_current_user(request)
    now = _now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_guide_progress WHERE user_id=? AND guide_key=?",
            (user["id"], body.guide_key),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail="Ouvrez le guide au moins une fois")
        total_steps = int(row["total_steps"] or 0)
        bitmap = int(row["steps_seen_bitmap"] or 0)
        full_mask = (1 << total_steps) - 1 if total_steps > 0 else 0
        if total_steps == 0 or (bitmap & full_mask) != full_mask:
            raise HTTPException(status_code=400, detail="Toutes les etapes doivent avoir ete vues avant")
        conn.execute(
            """UPDATE user_guide_progress SET
               acknowledged_at=COALESCE(acknowledged_at, ?),
               completed_at=COALESCE(completed_at, ?)
               WHERE user_id=? AND guide_key=?""",
            (now, now, user["id"], body.guide_key),
        )
        conn.commit()
    return {"ok": True, "acknowledged_at": now}


class OpenBody(BaseModel):
    guide_key: str
    total_steps: int


@router.post("/open")
def open_guide(body: OpenBody, request: Request):
    """Signale l'ouverture d'un guide (compte + timestamp)."""
    user = get_current_user(request)
    if body.total_steps <= 0 or body.total_steps > 64:
        raise HTTPException(status_code=400, detail="total_steps invalide")
    now = _now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_guide_progress WHERE user_id=? AND guide_key=?",
            (user["id"], body.guide_key),
        ).fetchone()
        if row is None:
            conn.execute(
                """INSERT INTO user_guide_progress
                   (user_id, guide_key, total_steps, open_count, opened_at)
                   VALUES (?,?,?,?,?)""",
                (user["id"], body.guide_key, body.total_steps, 1, now),
            )
        else:
            conn.execute(
                """UPDATE user_guide_progress SET
                   total_steps=?, open_count=open_count+1,
                   opened_at=COALESCE(opened_at, ?)
                   WHERE user_id=? AND guide_key=?""",
                (body.total_steps, now, user["id"], body.guide_key),
            )
        conn.commit()
    return {"ok": True}


# ─── Endpoints admin ──────────────────────────────────────────────────────

@router.get("/admin/overview")
def admin_overview(request: Request):
    """Matrice user x guide pour la table d'administration."""
    _require_admin(request)
    with get_db() as conn:
        users = [dict(r) for r in conn.execute(
            """SELECT id, nom, prenom, email, role FROM users
               WHERE (actif IS NULL OR actif=1)
               ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()]
        progress = [dict(r) for r in conn.execute(
            """SELECT p.user_id, p.guide_key, p.total_steps, p.steps_seen_bitmap,
                      p.total_time_ms, p.open_count, p.opened_at, p.completed_at,
                      p.acknowledged_at
               FROM user_guide_progress p"""
        ).fetchall()]
    # Calcul status
    for p in progress:
        ts = int(p["total_steps"] or 0)
        b = int(p["steps_seen_bitmap"] or 0)
        seen = bin(b).count("1") if b else 0
        full = ((1 << ts) - 1) if ts > 0 else 0
        if p["acknowledged_at"]:
            p["status"] = "acked"
        elif ts > 0 and (b & full) == full:
            p["status"] = "completed"
        elif seen > 0:
            p["status"] = "in_progress"
        else:
            p["status"] = "open"
        p["steps_seen"] = seen
    return {"users": users, "progress": progress}


class ResetBody(BaseModel):
    user_id: int
    guide_key: str


@router.post("/admin/reset")
def admin_reset(body: ResetBody, request: Request):
    admin = _require_admin(request)
    now = _now()
    with get_db() as conn:
        cur = conn.execute(
            "SELECT 1 FROM user_guide_progress WHERE user_id=? AND guide_key=?",
            (body.user_id, body.guide_key),
        ).fetchone()
        if not cur:
            raise HTTPException(status_code=404, detail="Aucune progression trouvee")
        conn.execute(
            """UPDATE user_guide_progress SET
               steps_seen_bitmap=0, total_time_ms=0, completed_at=NULL,
               acknowledged_at=NULL, reset_at=?, reset_by=?, open_count=0,
               opened_at=NULL
               WHERE user_id=? AND guide_key=?""",
            (now, admin["id"], body.user_id, body.guide_key),
        )
        conn.commit()
    return {"ok": True}
