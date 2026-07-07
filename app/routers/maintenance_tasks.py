"""MySifa — API Maintenance Tasks
Endpoints pour la gestion des tâches de maintenance assignées aux opérateurs.

Modèle : voir migration v151 dans app/core/database.py (table `maintenance_tasks`).

Contrôle d'accès :
- Admin (superadmin, direction, administration) : accès complet, voit et modifie
  toutes les tâches.
- Opérateur (fabrication) : accès uniquement si le flag global
  `MAINTENANCE_OPEN_BETA` est actif dans .env. Ne voit que ses propres tâches,
  ne peut créer que des tâches non planifiées (`source=non_planifie`) sur
  lui-même, ne peut modifier que ses propres tâches (statut + champs de saisie).

Ce fichier est le SQUELETTE de la branche `feature/maintenance-tasks-db` :
- Les endpoints existent et gèrent le contrôle d'accès.
- Les GET retournent [] pour l'instant.
- Les POST/PATCH/DELETE retournent 501 Not Implemented.
- L'implémentation métier viendra dans la branche `feature/maintenance-roles-ui`.
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from app.services.auth_service import get_current_user, effective_role
from config import (
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_FABRICATION,
    MAINTENANCE_OPEN_BETA,
)


router = APIRouter(tags=["maintenance-tasks"])


# ─── Helpers ──────────────────────────────────────────────────────

_ADMIN_ROLES = {ROLE_SUPERADMIN, ROLE_DIRECTION, ROLE_ADMINISTRATION}


def _get_maintenance_role(user: dict) -> Optional[str]:
    """Retourne 'admin', 'operator' ou None selon le rôle effectif de l'user
    et l'état du flag MAINTENANCE_OPEN_BETA.
    """
    if not user:
        return None
    role = effective_role(user)
    if role in _ADMIN_ROLES:
        return "admin"
    if role == ROLE_FABRICATION and MAINTENANCE_OPEN_BETA:
        return "operator"
    return None


def _require_maintenance_access(request: Request) -> tuple[dict, str]:
    """Récupère l'user courant et son rôle maintenance. 401 si pas connecté,
    403 si pas d'accès maintenance.
    """
    user = get_current_user(request)  # peut lever 401
    maint_role = _get_maintenance_role(user)
    if maint_role is None:
        raise HTTPException(status_code=403, detail="Accès maintenance non autorisé")
    return user, maint_role


# ─── Endpoints ────────────────────────────────────────────────────


@router.get("/api/maintenance/tasks")
def list_tasks(
    request: Request,
    date: Optional[str] = None,
    operator_id: Optional[int] = None,
    machine: Optional[str] = None,
):
    """Liste les tâches de maintenance.

    - Admin : voit toutes les tâches, peut filtrer librement.
    - Opérateur : voit uniquement ses propres tâches (operator_id forcé à
      l'user courant, quel que soit le paramètre).

    Filtres :
    - `date` : YYYY-MM-DD, défaut = pas de filtre (à cadrer à l'usage).
    - `operator_id` : int, ignoré pour les opérateurs (auto-forcé).
    - `machine` : nom de machine (Cohésio 1 / 2 / DSI / Repiquage).

    Retourne pour l'instant une liste vide — l'implémentation viendra dans la
    branche `feature/maintenance-roles-ui`.
    """
    user, maint_role = _require_maintenance_access(request)

    # Opérateur : on force operator_id à self, quels que soient les paramètres.
    if maint_role == "operator":
        operator_id = user["id"]

    # Squelette : pas de lecture DB pour l'instant.
    _ = (date, operator_id, machine)
    return {"tasks": [], "role": maint_role}


@router.post("/api/maintenance/tasks")
def create_task(request: Request):
    """Crée une tâche de maintenance.

    - Admin : peut créer n'importe quelle tâche (planifiée ou non), pour
      n'importe quel opérateur.
    - Opérateur : peut uniquement créer une tâche `source=non_planifie` sur
      lui-même (déclaration d'intervention non planifiée en cours de session).

    Body attendu à terme :
      {
        "date_prevue": "YYYY-MM-DD",
        "code": "01",
        "machine": "Cohésio 1",
        "operator_id": 12,           # ignoré si opérateur, forcé à self
        "source": "planifie"          # forcé à "non_planifie" si opérateur
      }
    """
    _user, _maint_role = _require_maintenance_access(request)
    raise HTTPException(status_code=501, detail="Non implémenté (branche db-only)")


@router.patch("/api/maintenance/tasks/{task_id}")
def update_task(task_id: int, request: Request):
    """Met à jour une tâche.

    - Admin : peut tout modifier (réassignation, date, statut, saisie).
    - Opérateur : peut modifier le statut et les champs de saisie
      (duree_reelle_min, pieces_changees, observations, photos_json, done_at)
      uniquement sur ses propres tâches.
    """
    _user, _maint_role = _require_maintenance_access(request)
    _ = task_id
    raise HTTPException(status_code=501, detail="Non implémenté (branche db-only)")


@router.delete("/api/maintenance/tasks/{task_id}")
def delete_task(task_id: int, request: Request):
    """Supprime une tâche. Admin uniquement."""
    user, maint_role = _require_maintenance_access(request)
    if maint_role != "admin":
        raise HTTPException(status_code=403, detail="Suppression réservée aux admins maintenance")
    _ = (task_id, user)
    raise HTTPException(status_code=501, detail="Non implémenté (branche db-only)")
