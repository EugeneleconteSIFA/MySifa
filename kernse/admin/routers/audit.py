"""
Kernse-admin — route /audit : consultation du journal d'audit plateforme.
"""
from __future__ import annotations

import json

from kernse.shared.auth.dependency import SuperadminContext, require_superadmin

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from kernse.shared.db.database import platform_db


router = APIRouter(prefix="/api/v1/audit", tags=["audit"])



@router.get("")
def list_audit(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None, max_length=64),
    entity_id: str | None = Query(None, max_length=64),
    actor_email: str | None = Query(None, max_length=120),
    _ctx: SuperadminContext = Depends(require_superadmin),
) -> dict:
    """Liste les entrées d'audit filtrées.

    Renvoie un objet `{items, total}` — total permet la pagination.
    """
    where_bits: list[str] = []
    params: list = []
    if action:
        where_bits.append("action = ?")
        params.append(action)
    if entity_id:
        where_bits.append("entity_id = ?")
        params.append(entity_id)
    if actor_email:
        where_bits.append("actor_email = ?")
        params.append(actor_email.lower())

    where = " WHERE " + " AND ".join(where_bits) if where_bits else ""

    with platform_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM audit_log{where}", params
        ).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT id, at, actor_email, actor_ip, action, entity_type, entity_id,
                   before_json, after_json, note
            FROM audit_log{where}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    items = []
    for r in rows:
        item = dict(r)
        for k in ("before_json", "after_json"):
            if item.get(k):
                try:
                    item[k[:-5]] = json.loads(item[k])
                except (TypeError, ValueError):
                    item[k[:-5]] = None
            else:
                item[k[:-5]] = None
            item.pop(k, None)
        items.append(item)

    return {"items": items, "total": total, "limit": limit, "offset": offset}
