"""SIFA — Planning v1.1 (standalone)

Planning autonome : les dossiers sont saisis manuellement.
Pas de lien vers la table dossiers.

Ajouter dans main.py :
    from routers.planning import router as planning_router
    app.include_router(planning_router)
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from database import get_db
from services.auth_service import require_admin

router = APIRouter(prefix="/api/planning", tags=["planning"])


# ═══════════════════════════════════════════════════════════════
# MACHINES
# ═══════════════════════════════════════════════════════════════

@router.get("/machines")
def list_machines(request: Request):
    require_admin(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM machines WHERE actif=1 ORDER BY nom").fetchall()
    return [dict(r) for r in rows]


@router.get("/machines/{machine_id}")
def get_machine(machine_id: int, request: Request):
    require_admin(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Machine non trouvée")
    return dict(row)


# ═══════════════════════════════════════════════════════════════
# ENTRIES — CRUD
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/entries")
def list_entries(machine_id: int, request: Request):
    require_admin(request)
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM planning_entries
            WHERE machine_id = ?
            ORDER BY position ASC
        """, (machine_id,)).fetchall()
    return [dict(r) for r in rows]


@router.post("/machines/{machine_id}/entries")
async def add_entry(machine_id: int, request: Request):
    """Ajouter un dossier manuellement au planning."""
    require_admin(request)
    body = await request.json()

    reference = body.get("reference", "").strip()
    if not reference:
        raise HTTPException(400, "Référence requise")

    duree = body.get("duree_heures", 8)
    if duree < 2 or duree > 30:
        raise HTTPException(400, "Durée entre 2 et 30 heures")

    now = datetime.now().isoformat()
    with get_db() as conn:
        mac = conn.execute("SELECT id FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mac:
            raise HTTPException(404, "Machine non trouvée")

        # Position : spécifiée ou en fin de file
        position = body.get("position")
        if position is None:
            max_pos = conn.execute(
                "SELECT COALESCE(MAX(position),0) FROM planning_entries WHERE machine_id=?",
                (machine_id,)
            ).fetchone()[0]
            position = max_pos + 1
        else:
            conn.execute(
                "UPDATE planning_entries SET position=position+1 WHERE machine_id=? AND position>=?",
                (machine_id, position)
            )

        conn.execute("""
            INSERT INTO planning_entries
                (machine_id, position, reference, client, description, format_l, format_h,
                 duree_heures, statut, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            machine_id, position,
            reference,
            body.get("client", ""),
            body.get("description", ""),
            body.get("format_l"),
            body.get("format_h"),
            duree,
            body.get("statut", "attente"),
            body.get("notes", ""),
            now, now
        ))
        conn.commit()
    return {"success": True, "position": position}


@router.put("/machines/{machine_id}/entries/{entry_id}")
async def update_entry(machine_id: int, entry_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    now = datetime.now().isoformat()

    duree = body.get("duree_heures")
    if duree is not None and (duree < 2 or duree > 30):
        raise HTTPException(400, "Durée entre 2 et 30 heures")

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")

        conn.execute("""
            UPDATE planning_entries
            SET reference=?, client=?, description=?, format_l=?, format_h=?,
                duree_heures=?, statut=?, notes=?, updated_at=?
            WHERE id=?
        """, (
            body.get("reference", ex["reference"]),
            body.get("client", ex["client"]),
            body.get("description", ex["description"]),
            body.get("format_l", ex["format_l"]),
            body.get("format_h", ex["format_h"]),
            body.get("duree_heures", ex["duree_heures"]),
            body.get("statut", ex["statut"]),
            body.get("notes", ex["notes"]),
            now, entry_id
        ))
        conn.commit()
    return {"success": True}


@router.delete("/machines/{machine_id}/entries/{entry_id}")
def delete_entry(machine_id: int, entry_id: int, request: Request):
    require_admin(request)
    with get_db() as conn:
        ex = conn.execute(
            "SELECT position FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")
        conn.execute("DELETE FROM planning_entries WHERE id=?", (entry_id,))
        conn.execute(
            "UPDATE planning_entries SET position=position-1 WHERE machine_id=? AND position>?",
            (machine_id, ex["position"])
        )
        conn.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# RÉORDONNER (drag & drop)
# ═══════════════════════════════════════════════════════════════

@router.post("/machines/{machine_id}/reorder")
async def reorder_entries(machine_id: int, request: Request):
    """Body: {"entry_ids": [5, 3, 8, 1, ...]}"""
    require_admin(request)
    body = await request.json()
    entry_ids = body.get("entry_ids", [])
    if not entry_ids:
        raise HTTPException(400, "entry_ids requis")

    now = datetime.now().isoformat()
    with get_db() as conn:
        for pos, eid in enumerate(entry_ids, start=1):
            conn.execute(
                "UPDATE planning_entries SET position=?, updated_at=? WHERE id=? AND machine_id=?",
                (pos, now, eid, machine_id)
            )
        conn.commit()
    return {"success": True, "count": len(entry_ids)}


# ═══════════════════════════════════════════════════════════════
# INSÉRER APRÈS
# ═══════════════════════════════════════════════════════════════

@router.post("/machines/{machine_id}/insert-after/{after_entry_id}")
async def insert_after(machine_id: int, after_entry_id: int, request: Request):
    require_admin(request)
    body = await request.json()

    reference = body.get("reference", "").strip()
    if not reference:
        raise HTTPException(400, "Référence requise")

    duree = body.get("duree_heures", 8)
    if duree < 2 or duree > 30:
        raise HTTPException(400, "Durée entre 2 et 30 heures")

    now = datetime.now().isoformat()
    with get_db() as conn:
        ref_entry = conn.execute(
            "SELECT position FROM planning_entries WHERE id=? AND machine_id=?",
            (after_entry_id, machine_id)
        ).fetchone()
        if not ref_entry:
            raise HTTPException(404, "Entrée de référence non trouvée")

        new_pos = ref_entry["position"] + 1
        conn.execute(
            "UPDATE planning_entries SET position=position+1 WHERE machine_id=? AND position>=?",
            (machine_id, new_pos)
        )
        conn.execute("""
            INSERT INTO planning_entries
                (machine_id, position, reference, client, description, format_l, format_h,
                 duree_heures, statut, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'attente', ?, ?, ?)
        """, (
            machine_id, new_pos,
            reference,
            body.get("client", ""),
            body.get("description", ""),
            body.get("format_l"),
            body.get("format_h"),
            duree,
            body.get("notes", ""),
            now, now
        ))
        conn.commit()
    return {"success": True, "position": new_pos}


# ═══════════════════════════════════════════════════════════════
# CONFIG SEMAINE (samedi travaillé)
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/config")
def get_week_config(machine_id: int, request: Request, semaine: Optional[str] = None):
    require_admin(request)
    if not semaine:
        today = datetime.now()
        semaine = f"{today.year}-W{today.isocalendar()[1]:02d}"

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM planning_config WHERE machine_id=? AND semaine=?",
            (machine_id, semaine)
        ).fetchone()
    if row:
        return dict(row)
    return {"machine_id": machine_id, "semaine": semaine, "samedi_travaille": 0, "notes": ""}


@router.put("/machines/{machine_id}/config")
async def set_week_config(machine_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    semaine = body.get("semaine")
    if not semaine:
        today = datetime.now()
        semaine = f"{today.year}-W{today.isocalendar()[1]:02d}"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO planning_config (machine_id, semaine, samedi_travaille, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(machine_id, semaine)
            DO UPDATE SET samedi_travaille=excluded.samedi_travaille, notes=excluded.notes
        """, (machine_id, semaine, body.get("samedi_travaille", 0), body.get("notes", "")))
        conn.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# TIMELINE (calcul)
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/timeline")
def get_timeline(machine_id: int, request: Request):
    require_admin(request)

    with get_db() as conn:
        machine = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not machine:
            raise HTTPException(404, "Machine non trouvée")

        entries = conn.execute("""
            SELECT * FROM planning_entries
            WHERE machine_id = ? AND statut != 'termine'
            ORDER BY position ASC
        """, (machine_id,)).fetchall()

        configs = {}
        today = datetime.now()
        for w in range(8):
            d = today + timedelta(weeks=w)
            sw = f"{d.year}-W{d.isocalendar()[1]:02d}"
            cfg = conn.execute(
                "SELECT samedi_travaille FROM planning_config WHERE machine_id=? AND semaine=?",
                (machine_id, sw)
            ).fetchone()
            configs[sw] = cfg["samedi_travaille"] if cfg else 0

    m = dict(machine)
    base_hours = {}
    for day_idx, field in [(0,"horaires_lundi"),(1,"horaires_mardi"),
                           (2,"horaires_mercredi"),(3,"horaires_jeudi"),
                           (4,"horaires_vendredi")]:
        val = m.get(field, "5,21")
        parts = val.split(",")
        base_hours[day_idx] = (int(parts[0]), int(parts[1]))

    sat_val = m.get("horaires_samedi", "6,18")
    sat_parts = sat_val.split(",")
    sat_hours = (int(sat_parts[0]), int(sat_parts[1]))

    def get_hours_for_date(dt):
        wd = dt.weekday()
        if wd in base_hours:
            return base_hours[wd]
        if wd == 5:
            sw = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
            if configs.get(sw, 0):
                return sat_hours
        return None

    def advance(dt):
        for _ in range(14):
            h = get_hours_for_date(dt)
            if h:
                if dt.hour < h[0]: return dt.replace(hour=h[0], minute=0)
                if dt.hour < h[1]: return dt
            dt = (dt + timedelta(days=1)).replace(hour=5, minute=0)
        return dt

    slots = []
    cursor = advance(datetime.now().replace(minute=0, second=0, microsecond=0))

    for entry in entries:
        e = dict(entry)
        remaining = e["duree_heures"]
        slot_start = datetime(cursor.year, cursor.month, cursor.day, cursor.hour)

        while remaining > 0:
            h = get_hours_for_date(cursor)
            if not h:
                cursor = (cursor + timedelta(days=1)).replace(hour=5, minute=0)
                continue
            avail = max(0, h[1] - cursor.hour)
            used = min(remaining, avail)
            remaining -= used
            if remaining > 0:
                cursor = advance((cursor + timedelta(days=1)).replace(hour=5, minute=0))
            else:
                cursor = cursor.replace(hour=cursor.hour + int(used))
                cursor = advance(cursor)

        slots.append({
            "entry_id": e["id"],
            "reference": e["reference"],
            "client": e["client"],
            "description": e["description"],
            "format_l": e["format_l"],
            "format_h": e["format_h"],
            "duree_heures": e["duree_heures"],
            "statut": e["statut"],
            "notes": e["notes"],
            "start": slot_start.isoformat(),
            "end": datetime(cursor.year, cursor.month, cursor.day, cursor.hour).isoformat(),
        })

    return {"machine": dict(machine), "slots": slots, "configs": configs}
