"""MySifa — Router MyLearning (e-learning + habilitations).

Prefix : /api/learning
Accès  : tout utilisateur authentifié pour /formations, /progression,
         /habilitations. Endpoints d'administration réservés à superadmin
         (arrivent en étape 3 : édition de contenu).

État étape 1 (squelette) : les endpoints de lecture renvoient des listes
vides tant qu'aucune formation n'est publiée. Aucun endpoint d'écriture
n'est encore exposé — l'admin arrive en étape 3.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_LABELS,
    TRANCHE_1,
    TRANCHE_2,
    TRANCHE_3,
    is_known_permission,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/learning", tags=["learning"])


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _formation_row(row) -> dict[str, Any]:
    d = dict(row)
    return {
        "id": d["id"],
        "code": d["code"],
        "titre": d["titre"],
        "description": d.get("description") or "",
        "role_cible": d.get("role_cible") or "",
        "ordre": d.get("ordre") or 100,
        "actif": bool(d.get("actif", 1)),
    }


# ─── Lecture — accessible à tout utilisateur connecté ────────────────────
@router.get("/formations")
def list_formations(request: Request) -> dict:
    """Liste des parcours actifs. Renvoie [] tant qu'aucun contenu publié."""
    user = get_current_user(request)  # 401 si non connecté
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, titre, description, role_cible, ordre, actif "
            "FROM formations WHERE actif=1 ORDER BY ordre, titre"
        ).fetchall()
    return {"formations": [_formation_row(r) for r in rows], "user_id": user["id"]}


@router.get("/formations/{formation_id}")
def get_formation(formation_id: int, request: Request) -> dict:
    """Détail d'un parcours + ses modules + les permissions débloquées."""
    _ = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, code, titre, description, role_cible, ordre, actif "
            "FROM formations WHERE id=? LIMIT 1",
            (formation_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Formation introuvable")
        modules = conn.execute(
            "SELECT id, ordre, titre, description, youtube_id, duree_sec "
            "FROM formation_modules WHERE formation_id=? AND actif=1 "
            "ORDER BY ordre",
            (formation_id,),
        ).fetchall()
        perms = conn.execute(
            "SELECT permission_code FROM formation_permissions WHERE formation_id=?",
            (formation_id,),
        ).fetchall()
    return {
        "formation": _formation_row(row),
        "modules": [dict(m) for m in modules],
        "permissions": [p["permission_code"] for p in perms],
    }


@router.get("/progression")
def get_progression(request: Request) -> dict:
    """Progression de l'utilisateur courant sur tous les modules qu'il a
    déjà touchés. Renvoie {} tant qu'il n'a rien commencé."""
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT module_id, pct_vu, quiz_score, valide_le, updated_at "
            "FROM user_progression WHERE user_id=?",
            (user["id"],),
        ).fetchall()
    return {"progression": [dict(r) for r in rows]}


@router.get("/habilitations")
def get_habilitations(request: Request) -> dict:
    """Liste des permissions détenues par l'utilisateur courant.
    Le super admin renvoie l'ensemble du catalogue (bypass systématique)."""
    user = get_current_user(request)
    if user["role"] == "superadmin":
        codes = list(ALL_PERMISSIONS)
    else:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT permission_code FROM user_habilitations WHERE user_id=?",
                (user["id"],),
            ).fetchall()
        codes = [r["permission_code"] for r in rows]
    return {
        "user_id": user["id"],
        "role": user["role"],
        "permissions": codes,
    }


@router.get("/permissions/catalog")
def permissions_catalog(request: Request) -> dict:
    """Catalogue statique des permission_code (utile pour l'admin et le
    debugging). Accessible à tout utilisateur connecté."""
    _ = get_current_user(request)

    def _pack(codes):
        return [
            {"code": c, "label": PERMISSION_LABELS.get(c, c)}
            for c in codes
        ]

    return {
        "tranche_1": _pack(TRANCHE_1),
        "tranche_2": _pack(TRANCHE_2),
        "tranche_3": _pack(TRANCHE_3),
    }


# ─── Écriture progression (uniquement pour l'utilisateur courant) ────────
@router.post("/progression/{module_id}")
def upsert_progression(module_id: int, request: Request, payload: dict) -> dict:
    """Met à jour la progression de l'utilisateur courant sur un module.
    Payload : {"pct_vu": 0-100, "quiz_score": 0-100 | null}.

    Étape 1 : cet endpoint est fonctionnel mais aucune formation n'existe
    encore. Sert de test pour la table user_progression.
    """
    user = get_current_user(request)
    try:
        pct_vu = int(payload.get("pct_vu", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="pct_vu invalide")
    pct_vu = max(0, min(100, pct_vu))
    quiz_score = payload.get("quiz_score")
    if quiz_score is not None:
        try:
            quiz_score = int(quiz_score)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="quiz_score invalide")
        quiz_score = max(0, min(100, quiz_score))

    now = _now()
    valide = pct_vu >= 90 and (quiz_score is None or quiz_score >= 80)

    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM formation_modules WHERE id=? LIMIT 1", (module_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Module introuvable")

        existing = conn.execute(
            "SELECT id, valide_le FROM user_progression "
            "WHERE user_id=? AND module_id=? LIMIT 1",
            (user["id"], module_id),
        ).fetchone()
        valide_le = existing["valide_le"] if existing else None
        if valide and valide_le is None:
            valide_le = now

        if existing:
            conn.execute(
                "UPDATE user_progression SET pct_vu=?, quiz_score=?, "
                "valide_le=?, updated_at=? WHERE id=?",
                (pct_vu, quiz_score, valide_le, now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO user_progression "
                "(user_id, module_id, pct_vu, quiz_score, valide_le, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (user["id"], module_id, pct_vu, quiz_score, valide_le, now),
            )
        conn.commit()

        # Si module validé, on vérifie si TOUS les modules de la formation
        # sont validés → on insère les habilitations correspondantes.
        if valide_le:
            _recompute_habilitations_for_module(conn, user["id"], module_id)

    return {"ok": True, "pct_vu": pct_vu, "quiz_score": quiz_score, "valide_le": valide_le}


def _recompute_habilitations_for_module(conn, user_id: int, module_id: int) -> None:
    """Si tous les modules de la formation contenant module_id sont validés
    par user_id, alors on ajoute les permissions dans user_habilitations."""
    formation = conn.execute(
        "SELECT formation_id FROM formation_modules WHERE id=? LIMIT 1",
        (module_id,),
    ).fetchone()
    if formation is None:
        return
    fid = formation["formation_id"]
    total = conn.execute(
        "SELECT COUNT(*) FROM formation_modules WHERE formation_id=? AND actif=1",
        (fid,),
    ).fetchone()[0]
    valides = conn.execute(
        "SELECT COUNT(*) FROM user_progression up "
        "JOIN formation_modules fm ON fm.id=up.module_id "
        "WHERE up.user_id=? AND fm.formation_id=? AND fm.actif=1 "
        "AND up.valide_le IS NOT NULL",
        (user_id, fid),
    ).fetchone()[0]
    if total == 0 or valides < total:
        return
    # Toutes validées → insertion habilitations (ignore si déjà présente).
    now = _now()
    perms = conn.execute(
        "SELECT permission_code FROM formation_permissions WHERE formation_id=?",
        (fid,),
    ).fetchall()
    for row in perms:
        code = row["permission_code"]
        if not is_known_permission(code):
            # Code obsolète, on skip silencieusement.
            continue
        conn.execute(
            "INSERT OR IGNORE INTO user_habilitations "
            "(user_id, permission_code, formation_id, obtenu_le) "
            "VALUES (?,?,?,?)",
            (user_id, code, fid, now),
        )
    conn.commit()
