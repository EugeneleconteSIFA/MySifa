"""MySifa — Post-its draggables (portail + pages applicatives si multi-page)."""

import re

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from services.auth_service import get_current_user

router = APIRouter(tags=["postits"])

_POSTIT_COLS = "id, user_id, type, title, pos_x, pos_y, width, multi_page, hidden, color, created_at"
_POSTIT_DEFAULT_COLORS = {"today": "#22d3ee", "someday": "#fbbf24"}
_COLOR_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _default_postit_color(ptype: str) -> str:
    return _POSTIT_DEFAULT_COLORS.get(ptype, "#22d3ee")


def _normalize_postit_color(value, ptype: str | None = None) -> str:
    if value is None or (isinstance(value, str) and not str(value).strip()):
        if ptype in _POSTIT_DEFAULT_COLORS:
            return _default_postit_color(ptype)
        raise HTTPException(400, "Couleur invalide — format #RRGGBB")
    s = str(value).strip()
    if not _COLOR_HEX_RE.match(s):
        raise HTTPException(400, "Couleur invalide — format #RRGGBB")
    return s.lower()


def _user_id(request: Request) -> int:
    return int(get_current_user(request)["id"])


def _get_postit_or_404(conn, postit_id: int, user_id: int) -> dict:
    row = conn.execute(
        f"SELECT {_POSTIT_COLS} FROM postits WHERE id=? AND user_id=?",
        (postit_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Post-it introuvable")
    return dict(row)


@router.get("/api/postits")
def list_postits(request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {_POSTIT_COLS} FROM postits WHERE user_id=? ORDER BY id",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            p = dict(r)
            tasks = conn.execute(
                """SELECT id, postit_id, text, done, order_index
                   FROM postit_tasks WHERE postit_id=? ORDER BY order_index, id""",
                (p["id"],),
            ).fetchall()
            p["tasks"] = [dict(t) for t in tasks]
            out.append(p)
    return out


@router.post("/api/postits")
async def create_postit(request: Request):
    user_id = _user_id(request)
    body = await request.json()
    ptype = str(body.get("type") or "").strip()
    title = str(body.get("title") or "").strip()
    if ptype not in ("today", "someday"):
        raise HTTPException(400, "Type invalide — today ou someday")
    if not title:
        raise HTTPException(400, "Titre obligatoire")
    color = _normalize_postit_color(body.get("color"), ptype)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO postits (user_id, type, title, color) VALUES (?,?,?,?)",
            (user_id, ptype, title, color),
        )
        pid = cur.lastrowid
        row = conn.execute(
            f"SELECT {_POSTIT_COLS} FROM postits WHERE id=?",
            (pid,),
        ).fetchone()
        conn.commit()
    return dict(row)


@router.delete("/api/postits/{postit_id}")
def delete_postit(postit_id: int, request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        conn.execute("DELETE FROM postits WHERE id=?", (postit_id,))
        conn.commit()
    return {"ok": True}


@router.patch("/api/postits/{postit_id}")
async def patch_postit(postit_id: int, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    updates = []
    params = []
    if "title" in body:
        title = str(body.get("title") or "").strip()
        if not title:
            raise HTTPException(400, "Titre obligatoire")
        updates.append("title=?")
        params.append(title)
    if "multi_page" in body:
        updates.append("multi_page=?")
        params.append(1 if body.get("multi_page") else 0)
    if "hidden" in body:
        updates.append("hidden=?")
        params.append(1 if body.get("hidden") else 0)
    if "color" in body:
        updates.append("color=?")
        params.append(_normalize_postit_color(body.get("color")))
    if not updates:
        raise HTTPException(400, "Aucune modification")
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        params.append(postit_id)
        conn.execute(
            f"UPDATE postits SET {', '.join(updates)} WHERE id=?",
            params,
        )
        row = conn.execute(
            f"SELECT {_POSTIT_COLS} FROM postits WHERE id=?",
            (postit_id,),
        ).fetchone()
        conn.commit()
    out = dict(row)
    out["ok"] = True
    return out


@router.patch("/api/postits/{postit_id}/pos")
async def update_postit_pos(postit_id: int, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    try:
        x = int(body.get("x", 0))
        y = int(body.get("y", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "Position invalide")
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        conn.execute("UPDATE postits SET pos_x=?, pos_y=? WHERE id=?", (x, y, postit_id))
        conn.commit()
    return {"ok": True}


@router.post("/api/postits/{postit_id}/tasks")
async def add_task(postit_id: int, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    text = str(body.get("text") if body.get("text") is not None else "")
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        row_max = conn.execute(
            "SELECT COALESCE(MAX(order_index), -1) AS m FROM postit_tasks WHERE postit_id=?",
            (postit_id,),
        ).fetchone()
        order_index = int(row_max["m"]) + 1
        cur = conn.execute(
            "INSERT INTO postit_tasks (postit_id, text, order_index) VALUES (?,?,?)",
            (postit_id, text, order_index),
        )
        tid = cur.lastrowid
        row = conn.execute(
            "SELECT id, postit_id, text, done, order_index FROM postit_tasks WHERE id=?",
            (tid,),
        ).fetchone()
        conn.commit()
    return dict(row)


@router.delete("/api/postits/{postit_id}/tasks/done/clear")
def clear_done_tasks(postit_id: int, request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        conn.execute(
            "DELETE FROM postit_tasks WHERE postit_id=? AND done=1",
            (postit_id,),
        )
        conn.commit()
    return {"ok": True}


@router.patch("/api/postits/{postit_id}/tasks/{task_id}")
async def patch_task(postit_id: int, task_id: int, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        row = conn.execute(
            "SELECT id FROM postit_tasks WHERE id=? AND postit_id=?",
            (task_id, postit_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Tâche introuvable")
        updates = []
        params = []
        if "done" in body:
            updates.append("done=?")
            params.append(1 if body.get("done") else 0)
        if "text" in body:
            updates.append("text=?")
            params.append(str(body.get("text") if body.get("text") is not None else ""))
        if not updates:
            raise HTTPException(400, "Aucune modification")
        params.extend([task_id, postit_id])
        conn.execute(
            f"UPDATE postit_tasks SET {', '.join(updates)} WHERE id=? AND postit_id=?",
            params,
        )
        conn.commit()
        out = conn.execute(
            "SELECT id, postit_id, text, done, order_index FROM postit_tasks WHERE id=?",
            (task_id,),
        ).fetchone()
    return dict(out)


@router.delete("/api/postits/{postit_id}/tasks/{task_id}")
def delete_task(postit_id: int, task_id: int, request: Request):
    user_id = _user_id(request)
    with get_db() as conn:
        _get_postit_or_404(conn, postit_id, user_id)
        row = conn.execute(
            "SELECT id FROM postit_tasks WHERE id=? AND postit_id=?",
            (task_id, postit_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Tâche introuvable")
        conn.execute(
            "DELETE FROM postit_tasks WHERE id=? AND postit_id=?",
            (task_id, postit_id),
        )
        conn.commit()
    return {"ok": True}
