"""MySifa — API Maintenance Tasks
Endpoints pour la gestion des tâches de maintenance assignées aux opérateurs.

Modèle : voir migration v155 dans app/core/database.py (table `maintenance_tasks`).

Contrôle d'accès :
- Admin (superadmin, direction, administration) : accès complet, voit et modifie
  toutes les tâches.
- Opérateur (fabrication) : accès uniquement si le flag global
  `MAINTENANCE_OPEN_BETA` est actif dans .env. Ne voit que ses propres tâches,
  ne peut créer que des tâches non planifiées (`source=non_planifie`) sur
  lui-même, ne peut modifier que ses propres tâches (statut + champs de saisie).

Endpoints :
- GET    /api/maintenance/tasks              → liste (filtres date/operator_id/machine)
- POST   /api/maintenance/tasks              → création
- PATCH  /api/maintenance/tasks/{id}         → mise à jour (statut, saisie)
- DELETE /api/maintenance/tasks/{id}         → suppression (admin only)
- GET    /api/maintenance/tasks/codes        → liste des codes actifs (picker admin)
- GET    /api/maintenance/tasks/operators    → liste des users fabrication (picker admin)
"""
from datetime import datetime
from typing import Optional
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


router = APIRouter(tags=["maintenance-tasks"])


# ─── Constantes ───────────────────────────────────────────────────

_ADMIN_ROLES = {ROLE_SUPERADMIN, ROLE_DIRECTION, ROLE_ADMINISTRATION}
_PARIS = ZoneInfo("Europe/Paris")

_VALID_STATUTS = {"a_faire", "en_cours", "termine", "reporte"}
_VALID_SOURCES = {"planifie", "non_planifie"}


# ─── Helpers ──────────────────────────────────────────────────────

def _now_paris_iso() -> str:
    """Timestamp `YYYY-MM-DDTHH:MM:SS` heure Paris — même format que le reste
    de MySifa (voir CLAUDE.md : `date_operation` sans timezone)."""
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _get_maintenance_role(user: dict) -> Optional[str]:
    """Rôle maintenance de l'user : 'admin', 'operator' ou None."""
    if not user:
        return None
    role = effective_role(user)
    if role in _ADMIN_ROLES:
        return "admin"
    if role == ROLE_FABRICATION and MAINTENANCE_OPEN_BETA:
        return "operator"
    return None


def _require_maintenance_access(request: Request) -> tuple[dict, str]:
    """Récupère l'user courant + son rôle maintenance.
    401 si pas connecté, 403 si pas d'accès."""
    user = get_current_user(request)
    maint_role = _get_maintenance_role(user)
    if maint_role is None:
        raise HTTPException(status_code=403, detail="Accès maintenance non autorisé")
    return user, maint_role


def _row_to_dict(row) -> dict:
    """Ligne sqlite → dict JSON-serializable pour l'API."""
    return {
        "id": row["id"],
        "date_prevue": row["date_prevue"],
        "heure_debut": row["heure_debut"] if "heure_debut" in row.keys() else None,
        "heure_fin": row["heure_fin"] if "heure_fin" in row.keys() else None,
        "code": row["code"],
        "code_label": row["code_label"],
        "code_categorie": row["code_categorie"],
        "machine": row["machine"],
        "operator_id": row["operator_id"],
        "operator_nom": row["operator_nom"],
        "statut": row["statut"],
        "source": row["source"],
        "duree_reelle_min": row["duree_reelle_min"],
        "pieces_changees": row["pieces_changees"],
        "observations": row["observations"],
        "photos_json": row["photos_json"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "done_at": row["done_at"],
    }


# SQL commune pour lister les tâches — jointure sur codes + users pour
# hydrater le libellé du code et le nom de l'opérateur d'un seul aller-retour.
_TASKS_SELECT = """
    SELECT
        t.id, t.date_prevue, t.heure_debut, t.heure_fin,
        t.code, t.machine, t.operator_id, t.statut,
        t.source, t.duree_reelle_min, t.pieces_changees, t.observations,
        t.photos_json, t.created_by, t.created_at, t.updated_at, t.done_at,
        c.label     AS code_label,
        c.categorie AS code_categorie,
        u.nom       AS operator_nom
    FROM maintenance_tasks t
    LEFT JOIN maintenance_codes c ON c.code = t.code
    LEFT JOIN users u             ON u.id   = t.operator_id
"""


# ─── Body models ──────────────────────────────────────────────────

class TaskCreateBody(BaseModel):
    date_prevue: str        # YYYY-MM-DD
    heure_debut: Optional[str] = None   # HH:MM (calendrier admin)
    heure_fin: Optional[str] = None     # HH:MM
    code: str
    machine: str
    operator_id: Optional[int] = None
    source: str = "planifie"


class TaskUpdateBody(BaseModel):
    date_prevue: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    code: Optional[str] = None
    machine: Optional[str] = None
    operator_id: Optional[int] = None
    statut: Optional[str] = None
    duree_reelle_min: Optional[int] = None
    pieces_changees: Optional[str] = None
    observations: Optional[str] = None
    photos_json: Optional[str] = None


# ─── Endpoints — lecture ─────────────────────────────────────────


@router.get("/api/maintenance/tasks")
def list_tasks(
    request: Request,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    operator_id: Optional[int] = None,
    machine: Optional[str] = None,
    statut: Optional[str] = None,
):
    """Liste les tâches de maintenance.

    Filtres (tous optionnels, cumulatifs) :
    - `date`       : YYYY-MM-DD, égalité exacte
    - `date_from`  : borne inférieure (inclus)
    - `date_to`    : borne supérieure (inclus)
    - `operator_id`: int (ignoré pour un opérateur, auto-forcé à self)
    - `machine`    : nom exact
    - `statut`     : a_faire / en_cours / termine / reporte

    Résultat trié par date_prevue croissante puis id.
    """
    user, maint_role = _require_maintenance_access(request)

    # Opérateur : on force operator_id à self, quels que soient les params.
    if maint_role == "operator":
        operator_id = user["id"]

    where = []
    params: list = []
    if date:
        where.append("t.date_prevue = ?"); params.append(date)
    if date_from:
        where.append("t.date_prevue >= ?"); params.append(date_from)
    if date_to:
        where.append("t.date_prevue <= ?"); params.append(date_to)
    if operator_id is not None:
        where.append("t.operator_id = ?"); params.append(int(operator_id))
    if machine:
        where.append("t.machine = ?"); params.append(machine)
    if statut:
        if statut not in _VALID_STATUTS:
            raise HTTPException(status_code=400, detail=f"statut invalide : {statut}")
        where.append("t.statut = ?"); params.append(statut)

    sql = _TASKS_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY t.date_prevue ASC, t.id ASC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    return {
        "tasks": [_row_to_dict(r) for r in rows],
        "role": maint_role,
    }


@router.get("/api/maintenance/tasks/codes")
def list_codes(request: Request):
    """Liste des codes de maintenance actifs (pour les pickers)."""
    _user, _maint_role = _require_maintenance_access(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT code, label, niveau, categorie, periodique, intervalle, metrage_ref "
            "FROM maintenance_codes ORDER BY categorie, code"
        ).fetchall()
    return {"codes": [dict(r) for r in rows]}


@router.get("/api/maintenance/tasks/operators")
def list_operators(request: Request):
    """Liste des utilisateurs assignables (rôle fabrication + actifs).
    Admin only : un opérateur n'a pas à choisir qui assigner."""
    _user, maint_role = _require_maintenance_access(request)
    if maint_role != "admin":
        raise HTTPException(status_code=403, detail="Liste réservée aux admins maintenance")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, identifiant "
            "FROM users WHERE role = ? AND actif = 1 "
            "ORDER BY nom",
            (ROLE_FABRICATION,),
        ).fetchall()
    return {"operators": [dict(r) for r in rows]}


# ─── Endpoints — écriture ────────────────────────────────────────


@router.post("/api/maintenance/tasks")
def create_task(body: TaskCreateBody, request: Request):
    """Crée une tâche de maintenance.

    - Admin : peut créer n'importe quelle tâche (planifiée ou non), pour
      n'importe quel opérateur (ou aucun, opérateur assigné plus tard).
    - Opérateur : forcé sur `source=non_planifie` et `operator_id=self`
      (déclaration d'intervention non planifiée en cours de session).
    """
    user, maint_role = _require_maintenance_access(request)

    # Validation date
    try:
        datetime.strptime(body.date_prevue, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date_prevue attendue au format YYYY-MM-DD")

    # Validation source
    src = body.source
    if maint_role == "operator":
        # On ignore ce que l'opérateur envoie — sécurité.
        src = "non_planifie"
        operator_id = user["id"]
    else:
        if src not in _VALID_SOURCES:
            raise HTTPException(status_code=400, detail=f"source invalide : {src}")
        operator_id = body.operator_id

    # Vérif code + operator
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code = ?", (body.code,)).fetchone():
            raise HTTPException(status_code=400, detail=f"code inconnu : {body.code}")
        if operator_id is not None:
            if not conn.execute("SELECT 1 FROM users WHERE id = ?", (operator_id,)).fetchone():
                raise HTTPException(status_code=400, detail=f"operator_id inconnu : {operator_id}")

        now = _now_paris_iso()
        cur = conn.execute(
            """INSERT INTO maintenance_tasks
               (date_prevue, heure_debut, heure_fin, code, machine, operator_id,
                statut, source, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'a_faire', ?, ?, ?)""",
            (body.date_prevue, body.heure_debut, body.heure_fin, body.code,
             body.machine, operator_id, src, user["id"], now),
        )
        task_id = cur.lastrowid
        conn.commit()

        row = conn.execute(_TASKS_SELECT + " WHERE t.id = ?", (task_id,)).fetchone()

    return {"task": _row_to_dict(row)}


@router.patch("/api/maintenance/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdateBody, request: Request):
    """Met à jour une tâche.

    - Admin : peut tout modifier (réassignation, date, statut, saisie).
    - Opérateur : peut modifier uniquement le statut et les champs de saisie
      (duree_reelle_min, pieces_changees, observations, photos_json) sur ses
      propres tâches.
    """
    user, maint_role = _require_maintenance_access(request)

    with get_db() as conn:
        existing = conn.execute(
            "SELECT operator_id FROM maintenance_tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Tâche introuvable")

        # Opérateur : uniquement ses propres tâches.
        if maint_role == "operator" and existing["operator_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Tâche assignée à un autre opérateur")

        # Champs autorisés selon le rôle.
        admin_fields = {"date_prevue", "heure_debut", "heure_fin",
                        "code", "machine", "operator_id"}
        common_fields = {"statut", "duree_reelle_min", "pieces_changees",
                         "observations", "photos_json"}
        allowed = admin_fields | common_fields if maint_role == "admin" else common_fields

        updates = {}
        for k, v in body.model_dump(exclude_unset=True).items():
            if v is None:
                continue
            if k not in allowed:
                # Champ non autorisé pour ce rôle — on ignore silencieusement
                # plutôt que d'échouer (frontend peut envoyer un payload uniforme).
                continue
            updates[k] = v

        if not updates:
            raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

        # Validation valeurs
        if "statut" in updates and updates["statut"] not in _VALID_STATUTS:
            raise HTTPException(status_code=400, detail=f"statut invalide : {updates['statut']}")
        if "date_prevue" in updates:
            try:
                datetime.strptime(updates["date_prevue"], "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="date_prevue au format YYYY-MM-DD attendu")
        if "code" in updates:
            if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code = ?", (updates["code"],)).fetchone():
                raise HTTPException(status_code=400, detail=f"code inconnu : {updates['code']}")
        if "operator_id" in updates and updates["operator_id"] is not None:
            if not conn.execute("SELECT 1 FROM users WHERE id = ?", (updates["operator_id"],)).fetchone():
                raise HTTPException(status_code=400, detail=f"operator_id inconnu : {updates['operator_id']}")

        # Timestamps automatiques
        now = _now_paris_iso()
        updates["updated_at"] = now
        # done_at posé quand on passe à termine (et pas encore posé).
        if updates.get("statut") == "termine":
            updates["done_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]
        conn.execute(f"UPDATE maintenance_tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()

        row = conn.execute(_TASKS_SELECT + " WHERE t.id = ?", (task_id,)).fetchone()

    return {"task": _row_to_dict(row)}


@router.delete("/api/maintenance/tasks/{task_id}")
def delete_task(task_id: int, request: Request):
    """Supprime une tâche. Admin uniquement."""
    _user, maint_role = _require_maintenance_access(request)
    if maint_role != "admin":
        raise HTTPException(status_code=403, detail="Suppression réservée aux admins maintenance")

    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_tasks WHERE id = ?", (task_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Tâche introuvable")
        conn.execute("DELETE FROM maintenance_tasks WHERE id = ?", (task_id,))
        conn.commit()

    return {"deleted": task_id}
