"""
MyExpé — API de l'agent emails de commandes.

Monté sous `/api/expe/emails`. Le relevé et le tri vivent dans
`app/services/emails_commandes.py` ; ce fichier expose la liste, le suivi
(statut, catégorie, note) et les réglages de l'agent.

La boîte est lue en lecture seule : aucune route ne modifie Outlook.
"""

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request

from app.services import emails_commandes as em
from app.services import graph_mail
from app.services.audit_service import log_action
from config import ROLES_EXPE_EMAILS
from database import get_db
from services.auth_service import (
    effective_role,
    get_current_user,
    user_can_write_expe,
    user_has_app_access,
)

router = APIRouter()


def _require(request: Request) -> dict:
    """MyExpé, plus un rôle habilité pendant le rodage (`ROLES_EXPE_EMAILS`)."""
    user = get_current_user(request)
    if not user_has_app_access(user, "expe"):
        raise HTTPException(status_code=403, detail="Accès MyExpé requis")
    if effective_role(user) not in ROLES_EXPE_EMAILS:
        raise HTTPException(status_code=403,
                            detail="Emails commandes — accès réservé pendant le rodage.")
    return user


def _require_write(request: Request) -> dict:
    user = _require(request)
    if not user_can_write_expe(user):
        raise HTTPException(status_code=403, detail="Accès MyExpé en lecture seule")
    return user


def _qui(user: dict) -> str:
    return (user.get("nom") or user.get("email") or user.get("identifiant") or "").strip()


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("/emails")
def liste(request: Request, statut: str = "ouverts", jours: int = 30):
    _require(request)
    with get_db() as conn:
        return em.lister(conn, statut, max(1, min(jours, 365)))


@router.get("/emails/reglages")
def lire_reglages(request: Request):
    _require(request)
    with get_db() as conn:
        return {"reglages": em.charger_reglages(conn)}


@router.put("/emails/reglages")
def ecrire_reglages(request: Request, body: dict = Body(...)):
    user = _require_write(request)
    with get_db() as conn:
        try:
            reg = em.enregistrer_reglages(conn, body or {})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="expe",
               objet="Emails commandes · réglages", ip=_ip(request))
    return {"reglages": reg}


@router.post("/emails/tester")
def tester(request: Request):
    """Vérifie que l'application Graph peut lire la boîte."""
    _require(request)
    with get_db() as conn:
        boite = em.charger_reglages(conn)["boite"]
    try:
        r = graph_mail.tester_acces(boite)
    except graph_mail.GraphErreur as e:
        return {"ok": False, "boite": boite, "message": str(e)}
    return {"ok": True, "boite": boite,
            "message": f"Accès confirmé — {r.get('messages')} message(s) dans la boîte de réception."}


@router.post("/emails/relever")
def relever(request: Request):
    """Relève et trie maintenant, sans attendre le tour automatique."""
    user = _require_write(request)
    with get_db() as conn:
        try:
            n = em.relever(conn)
        except graph_mail.GraphErreur as e:
            raise HTTPException(status_code=502, detail=str(e))
        c = em.classer_en_attente(conn)
    log_action(user=user, action="UPDATE", module="expe",
               objet="Emails commandes · relevé manuel", ip=_ip(request))
    return {"nouveaux": n, "classes": c}


@router.get("/emails/{email_id}")
def lire(request: Request, email_id: int):
    _require(request)
    with get_db() as conn:
        d = em.detail(conn, email_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Email introuvable.")
    return d


@router.patch("/emails/{email_id}")
def suivre(request: Request, email_id: int, body: dict = Body(...)):
    user = _require_write(request)
    with get_db() as conn:
        try:
            d = em.mettre_a_jour(conn, email_id, body or {}, _qui(user))
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    log_action(user=user, action="UPDATE", module="expe",
               objet=f"Email commande #{email_id} · {', '.join(sorted(body or {}))}",
               ip=_ip(request))
    return d


@router.post("/emails/{email_id}/reclasser")
def reclasser(request: Request, email_id: int):
    user = _require_write(request)
    with get_db() as conn:
        try:
            em.classer(conn, email_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        d = em.detail(conn, email_id)
    log_action(user=user, action="UPDATE", module="expe",
               objet=f"Email commande #{email_id} · reclassé", ip=_ip(request))
    return d
