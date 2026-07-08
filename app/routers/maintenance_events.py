"""MySifa — API Maintenance Events
Endpoints pour la gestion des créneaux de maintenance (multi-op + multi-opérateur).

Modèle : voir migration v158 dans app/core/database.py.

- `maintenance_events` (le créneau : machine, date, heures, source)
- `maintenance_event_ops` (les opérations : statut + saisie partagée par le groupe)
- `maintenance_event_operators` (les opérateurs assignés)

Contrôle d'accès :
- Admin (superadmin, direction, administration) : CRUD complet.
- Opérateur (fabrication) : accès uniquement si le flag global
  `MAINTENANCE_OPEN_BETA` est actif dans .env. Peut :
  - Lire les events où il est dans le groupe (endpoint `/my-tasks`).
  - Mettre à jour statut/saisie d'une op **si** il est dans le groupe.
  - Créer un event `source=non_planifie` avec lui-même comme seul opérateur.
"""
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user, effective_role
from config import (
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_FABRICATION,
    MAINTENANCE_OPEN_BETA,
)


router = APIRouter(tags=["maintenance-events"])


# ─── Constantes / helpers ─────────────────────────────────────────

_ADMIN_ROLES = {ROLE_SUPERADMIN, ROLE_DIRECTION, ROLE_ADMINISTRATION}
_PARIS = ZoneInfo("Europe/Paris")

_VALID_STATUTS = {"a_faire", "en_cours", "termine", "reporte"}
_VALID_SOURCES = {"planifie", "non_planifie"}


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _get_maintenance_role(user: dict) -> Optional[str]:
    if not user:
        return None
    role = effective_role(user)
    if role in _ADMIN_ROLES:
        return "admin"
    if role == ROLE_FABRICATION and MAINTENANCE_OPEN_BETA:
        return "operator"
    return None


def _require_access(request: Request) -> tuple[dict, str]:
    user = get_current_user(request)
    maint_role = _get_maintenance_role(user)
    if maint_role is None:
        raise HTTPException(status_code=403, detail="Accès maintenance non autorisé")
    return user, maint_role


def _require_admin(request: Request) -> dict:
    user, maint_role = _require_access(request)
    if maint_role != "admin":
        raise HTTPException(status_code=403, detail="Réservé aux admins maintenance")
    return user


def _user_in_group(conn, event_id: int, user_id: int) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM maintenance_event_operators WHERE event_id=? AND operator_id=? LIMIT 1",
        (event_id, user_id),
    ).fetchone())


def _validate_date(s: str) -> None:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"date attendue au format YYYY-MM-DD: {s!r}")


def _validate_time(s: Optional[str]) -> None:
    if s is None:
        return
    try:
        datetime.strptime(s, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"heure attendue au format HH:MM: {s!r}")


def _load_event_full(conn, event_id: int) -> Optional[dict]:
    """Retourne un dict enrichi {event, ops:[...], operators:[...]} ou None."""
    ev = conn.execute(
        """SELECT id, machine, date_prevue, heure_debut, heure_fin, source,
                  created_by, created_at, updated_at
           FROM maintenance_events WHERE id = ?""",
        (event_id,),
    ).fetchone()
    if not ev:
        return None
    ops = conn.execute(
        """SELECT o.id, o.code, o.statut, o.duree_reelle_min, o.pieces_changees,
                  o.observations, o.photos_json, o.done_at, o.done_by,
                  o.updated_by, o.updated_at,
                  c.label     AS code_label,
                  c.categorie AS code_categorie
           FROM maintenance_event_ops o
           LEFT JOIN maintenance_codes c ON c.code = o.code
           WHERE o.event_id = ?
           ORDER BY o.id""",
        (event_id,),
    ).fetchall()
    ops_rows = conn.execute(
        """SELECT u.id, u.nom
           FROM maintenance_event_operators eo
           JOIN users u ON u.id = eo.operator_id
           WHERE eo.event_id = ?
           ORDER BY u.nom""",
        (event_id,),
    ).fetchall()
    return {
        "id": ev["id"],
        "machine": ev["machine"],
        "date_prevue": ev["date_prevue"],
        "heure_debut": ev["heure_debut"],
        "heure_fin": ev["heure_fin"],
        "source": ev["source"],
        "created_by": ev["created_by"],
        "created_at": ev["created_at"],
        "updated_at": ev["updated_at"],
        "ops": [dict(r) for r in ops],
        "operators": [dict(r) for r in ops_rows],
    }


# ─── Body models ──────────────────────────────────────────────────

class EventCreateBody(BaseModel):
    machine: str
    date_prevue: str                         # YYYY-MM-DD
    heure_debut: Optional[str] = None        # HH:MM (nullable si non planifié)
    heure_fin: Optional[str] = None          # HH:MM
    source: str = "planifie"
    ops: List[str] = []                      # liste de codes (au moins 1)
    operators: List[int] = []                # liste d'ids user (peut être vide)


class EventUpdateBody(BaseModel):
    machine: Optional[str] = None
    date_prevue: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None


class OpAddBody(BaseModel):
    code: str


class OpUpdateBody(BaseModel):
    statut: Optional[str] = None
    duree_reelle_min: Optional[int] = None
    pieces_changees: Optional[str] = None
    observations: Optional[str] = None
    photos_json: Optional[str] = None


class OperatorAddBody(BaseModel):
    operator_id: int


# ─── Endpoints — codes & opérateurs (utilitaires pickers) ────────

@router.get("/api/maintenance/operators")
def list_operators(request: Request):
    """Liste des utilisateurs assignables (rôle fabrication + actifs).
    Admin only : un opérateur n'a pas à choisir qui assigner."""
    _require_admin(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, identifiant "
            "FROM users WHERE role = ? AND actif = 1 "
            "ORDER BY nom",
            (ROLE_FABRICATION,),
        ).fetchall()
    return {"operators": [dict(r) for r in rows]}


# ─── Endpoints — events ──────────────────────────────────────────

@router.get("/api/maintenance/events")
def list_events(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    machine: Optional[str] = None,
):
    """Liste des créneaux, filtres par plage de date et machine.

    - Admin voit tout.
    - Opérateur : voit tout aussi (le "Planning général" a besoin de la
      vue globale de la journée pour son onglet dédié).
    """
    _require_access(request)
    where, params = [], []
    if date_from:
        where.append("date_prevue >= ?"); params.append(date_from)
    if date_to:
        where.append("date_prevue <= ?"); params.append(date_to)
    if machine:
        where.append("machine = ?"); params.append(machine)
    sql = ("SELECT id FROM maintenance_events "
           + ("WHERE " + " AND ".join(where) if where else "")
           + " ORDER BY date_prevue ASC, heure_debut ASC, id ASC")
    with get_db() as conn:
        ids = [r["id"] for r in conn.execute(sql, params).fetchall()]
        events = [_load_event_full(conn, eid) for eid in ids]
    return {"events": events}


@router.get("/api/maintenance/events/{event_id}")
def get_event(event_id: int, request: Request):
    _require_access(request)
    with get_db() as conn:
        ev = _load_event_full(conn, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Créneau introuvable")
    return {"event": ev}


@router.post("/api/maintenance/events")
def create_event(body: EventCreateBody, request: Request):
    """Crée un créneau avec ses N ops et M opérateurs.

    - Admin : `source=planifie` (défaut), avec heures et opérateurs libres.
    - Opérateur : `source=non_planifie` forcé, sans heures, opérateur = self.
      1 seul code accepté (déclaration ponctuelle d'intervention).
    """
    user, maint_role = _require_access(request)
    _validate_date(body.date_prevue)
    _validate_time(body.heure_debut)
    _validate_time(body.heure_fin)

    src = body.source
    ops_codes = list(dict.fromkeys(body.ops))       # dedup, garde l'ordre
    operator_ids = list(dict.fromkeys(body.operators))

    if maint_role == "operator":
        src = "non_planifie"
        heure_debut = None
        heure_fin = None
        operator_ids = [user["id"]]
        if len(ops_codes) != 1:
            raise HTTPException(status_code=400, detail="Une intervention non planifiée doit contenir exactement 1 code")
    else:
        if src not in _VALID_SOURCES:
            raise HTTPException(status_code=400, detail=f"source invalide: {src}")
        heure_debut = body.heure_debut
        heure_fin = body.heure_fin
        if not ops_codes:
            raise HTTPException(status_code=400, detail="Au moins un code d'opération est requis")

    with get_db() as conn:
        # Vérif codes
        for code in ops_codes:
            if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code=?", (code,)).fetchone():
                raise HTTPException(status_code=400, detail=f"code inconnu: {code}")
        # Vérif opérateurs
        for oid in operator_ids:
            if not conn.execute("SELECT 1 FROM users WHERE id=?", (oid,)).fetchone():
                raise HTTPException(status_code=400, detail=f"opérateur inconnu: {oid}")

        now = _now_paris_iso()
        cur = conn.execute(
            """INSERT INTO maintenance_events
               (machine, date_prevue, heure_debut, heure_fin, source,
                created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (body.machine, body.date_prevue, heure_debut, heure_fin, src,
             user["id"], now),
        )
        event_id = cur.lastrowid
        for code in ops_codes:
            conn.execute(
                """INSERT INTO maintenance_event_ops (event_id, code, updated_at)
                   VALUES (?, ?, ?)""",
                (event_id, code, now),
            )
        for oid in operator_ids:
            conn.execute(
                "INSERT OR IGNORE INTO maintenance_event_operators (event_id, operator_id) VALUES (?, ?)",
                (event_id, oid),
            )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.patch("/api/maintenance/events/{event_id}")
def update_event(event_id: int, body: EventUpdateBody, request: Request):
    _require_admin(request)
    if body.date_prevue is not None: _validate_date(body.date_prevue)
    if body.heure_debut is not None: _validate_time(body.heure_debut)
    if body.heure_fin is not None:   _validate_time(body.heure_fin)

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_events WHERE id=?", (event_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        updates["updated_at"] = _now_paris_iso()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE maintenance_events SET {set_clause} WHERE id=?",
                     list(updates.values()) + [event_id])
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}")
def delete_event(event_id: int, request: Request):
    _require_admin(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_events WHERE id=?", (event_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        # CASCADE supprime ops et rattachements
        conn.execute("DELETE FROM maintenance_events WHERE id=?", (event_id,))
        conn.commit()
    return {"deleted": event_id}


# ─── Endpoints — event ops (les opérations du créneau) ───────────

@router.post("/api/maintenance/events/{event_id}/ops")
def add_op(event_id: int, body: OpAddBody, request: Request):
    _require_admin(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_events WHERE id=?", (event_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code=?", (body.code,)).fetchone():
            raise HTTPException(status_code=400, detail=f"code inconnu: {body.code}")
        if conn.execute("SELECT 1 FROM maintenance_event_ops WHERE event_id=? AND code=?",
                         (event_id, body.code)).fetchone():
            raise HTTPException(status_code=400, detail="Op déjà présente dans ce créneau")
        conn.execute(
            "INSERT INTO maintenance_event_ops (event_id, code, updated_at) VALUES (?, ?, ?)",
            (event_id, body.code, _now_paris_iso()),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.patch("/api/maintenance/events/{event_id}/ops/{op_id}")
def update_op(event_id: int, op_id: int, body: OpUpdateBody, request: Request):
    """Met à jour statut / saisie d'une op. Admin OU opérateur du groupe.
    Trace updated_by (dernier modifieur). Pose done_at + done_by au premier
    passage à termine."""
    user, maint_role = _require_access(request)

    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id, statut, done_at FROM maintenance_event_ops WHERE id=?",
            (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce créneau")

        if maint_role == "operator" and not _user_in_group(conn, event_id, user["id"]):
            raise HTTPException(status_code=403, detail="Vous n'êtes pas assigné à ce créneau")

        updates = {}
        for k, v in body.model_dump(exclude_unset=True).items():
            if v is None: continue
            if k == "statut" and v not in _VALID_STATUTS:
                raise HTTPException(status_code=400, detail=f"statut invalide: {v}")
            updates[k] = v
        if not updates:
            raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

        now = _now_paris_iso()
        updates["updated_by"] = user["id"]
        updates["updated_at"] = now
        # Pose done_at + done_by au moment où l'op passe à termine.
        if updates.get("statut") == "termine" and not row["done_at"]:
            updates["done_at"] = now
            updates["done_by"] = user["id"]

        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE maintenance_event_ops SET {set_clause} WHERE id=?",
                     list(updates.values()) + [op_id])
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}/ops/{op_id}")
def delete_op(event_id: int, op_id: int, request: Request):
    _require_admin(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id FROM maintenance_event_ops WHERE id=?", (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce créneau")
        conn.execute("DELETE FROM maintenance_event_ops WHERE id=?", (op_id,))
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


# ─── Endpoints — event operators (le groupe) ─────────────────────

@router.post("/api/maintenance/events/{event_id}/operators")
def add_operator(event_id: int, body: OperatorAddBody, request: Request):
    _require_admin(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_events WHERE id=?", (event_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (body.operator_id,)).fetchone():
            raise HTTPException(status_code=400, detail=f"opérateur inconnu: {body.operator_id}")
        conn.execute(
            "INSERT OR IGNORE INTO maintenance_event_operators (event_id, operator_id) VALUES (?, ?)",
            (event_id, body.operator_id),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}/operators/{operator_id}")
def remove_operator(event_id: int, operator_id: int, request: Request):
    _require_admin(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_events WHERE id=?", (event_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        conn.execute(
            "DELETE FROM maintenance_event_operators WHERE event_id=? AND operator_id=?",
            (event_id, operator_id),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


# ─── Endpoint spécifique opérateur ────────────────────────────────

@router.get("/api/maintenance/my-tasks")
def my_tasks(
    request: Request,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Liste des events où l'user courant est dans le groupe (fabrication).

    Renvoie les events enrichis (ops + operators) comme /events. Le rôle admin
    peut aussi l'appeler pour voir ses propres assignations éventuelles."""
    user, _maint_role = _require_access(request)
    where = ["eo.operator_id = ?"]
    params = [user["id"]]
    if date:
        where.append("e.date_prevue = ?"); params.append(date)
    if date_from:
        where.append("e.date_prevue >= ?"); params.append(date_from)
    if date_to:
        where.append("e.date_prevue <= ?"); params.append(date_to)
    sql = ("SELECT DISTINCT e.id FROM maintenance_events e "
           "JOIN maintenance_event_operators eo ON eo.event_id = e.id "
           "WHERE " + " AND ".join(where)
           + " ORDER BY e.date_prevue ASC, e.heure_debut ASC, e.id ASC")
    with get_db() as conn:
        ids = [r["id"] for r in conn.execute(sql, params).fetchall()]
        events = [_load_event_full(conn, eid) for eid in ids]
    return {"events": events}
