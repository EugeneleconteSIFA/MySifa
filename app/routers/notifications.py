"""MySifa — Notifications par service (API des pastilles du portail + réglages).

Endpoints :
    GET  /api/notifications                 — ce qui attend l'utilisateur courant (pastilles du portail)
    POST /api/notifications/vu              — marque les notifications comme vues
    GET  /api/notifications/regles          — catalogue + réglages (Paramètres)
    PUT  /api/notifications/regles/{code}   — active / rôles / push d'un détecteur

Le catalogue des détecteurs est dans `app/services/notifications.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request

from config import ROLE_LABELS
from database import get_db
from app.services import notifications as N
from app.services.audit_service import log_action
from services.auth_service import (
    effective_role,
    get_current_user,
    require_settings_communication,
    user_has_app_access,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def mes_notifications(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        return N.pour_utilisateur(conn, user, a_acces=user_has_app_access,
                                  role=effective_role(user))


@router.post("/vu")
def marquer_vu(request: Request, body: dict = Body(default={})):
    """Body : { codes: [...] }. Les signatures sont relues côté serveur : le
    client ne peut pas marquer « vu » un état qu'il n'a pas eu sous les yeux
    plus récent que celui du cache."""
    user = get_current_user(request)
    codes = [c for c in (body or {}).get("codes") or [] if c in N.DETECTEURS]
    if not codes:
        return {"ok": True}
    with get_db() as conn:
        autorises = set(N.codes_pour(user, N.regles(conn), a_acces=user_has_app_access,
                                     role=effective_role(user)))
        sigs = {c: N.compter(conn, c)[1] for c in codes if c in autorises}
        if sigs:
            N.marquer_vu(conn, user["id"], sigs)
            conn.commit()
    return {"ok": True}


@router.get("/regles")
def lister_regles(request: Request):
    require_settings_communication(request)
    with get_db() as conn:
        rg = N.regles(conn)
        detecteurs = []
        for code, d in N.DETECTEURS.items():
            n, _ = N.compter(conn, code)
            detecteurs.append({
                "code": code, "app": d.app, "app_label": d.app_label,
                "titre": d.titre, "description": d.description, "lien": d.lien,
                "roles_suggeres": list(d.roles_suggeres),
                "en_cours": n, **rg[code],
            })
    roles = [{"code": k, "label": v} for k, v in ROLE_LABELS.items()
             if k != "administration"]  # rôle legacy, plus assignable
    return {"detecteurs": detecteurs, "roles": roles}


@router.put("/regles/{code}")
def modifier_regle(code: str, request: Request, body: dict = Body(...)):
    user = require_settings_communication(request)
    if code not in N.DETECTEURS:
        raise HTTPException(404, "Notification inconnue.")
    roles = body.get("roles")
    if not isinstance(roles, list):
        raise HTTPException(400, "Liste de rôles attendue.")
    auteur = user.get("nom") or user.get("email") or ""
    with get_db() as conn:
        avant = N.regles(conn)[code]
        apres = N.enregistrer_regle(conn, code, actif=bool(body.get("actif")),
                                    roles=roles, push=bool(body.get("push")), auteur=auteur)
        conn.commit()
    N.invalider_cache(code)

    def _txt(r):
        return "%s · rôles %s · push %s" % (
            "active" if r["actif"] else "inactive",
            ", ".join(r["roles"]) or "aucun", "oui" if r["push"] else "non")

    log_action(user=user, request=request, module="notifications", action="UPDATE",
               objet=f"Notification {N.DETECTEURS[code].titre}",
               detail=f"{_txt(avant)} → {_txt(apres)}")
    return {"code": code, **apres}
