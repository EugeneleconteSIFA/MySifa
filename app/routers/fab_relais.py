"""
« Passer la main » — relais d'un conducteur à un autre sur un dossier en cours.

Routes : /api/fabrication/relais/*

L'écran de saisie enchaîne six saisies ordinaires (`POST /api/fabrication/saisie`) :
89 « à reprendre plus tard » et 87 au nom du conducteur qui part, puis 86, 01
et la dernière opération en cours au nom de celui qui arrive. Ces routes ne
font que ce que l'écran ne peut pas faire seul :

1. `GET  /operateurs` — à qui passer la main.
2. `POST /verifier`   — contrôle le code de celui qui arrive, AVANT toute
   saisie : un code faux ne doit pas laisser un dossier arrêté et une machine
   sans conducteur. La session du nouveau conducteur est créée et posée dans un
   cookie httponly à part (`sifa_relais`), jamais renvoyée dans la réponse.
3. `POST /basculer`   — entre le 87 et le 86 : la session du conducteur qui
   part est fermée, celle du relais devient la session de la tablette, et le
   relais est noté dans `fab_relais` (il impose la machine à celui qui arrive).
4. `DELETE /`         — abandon : la session préparée est détruite.
"""

import logging
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from config import COOKIE_NAME, FAB_RELAIS_DELAI_SECONDES, session_hours_for_role
from database import get_db
from app.services.audit_service import log_action
from app.services.auth_service import (
    create_session,
    delete_session,
    get_current_user,
    get_user_by_token,
    is_admin,
    is_fabrication,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")
COOKIE_RELAIS = "sifa_relais"
ROLE_CONDUCTEUR = "fabrication"

# Codes faux : 5 essais par conducteur sortant et par fenêtre de 5 minutes.
_ESSAIS_MAX = 5
_ESSAIS_FENETRE = 300
_essais: dict = {}


def _check_acces(user: dict) -> None:
    if not (is_fabrication(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Accès réservé au service Fabrication")
    if user.get("is_impersonating"):
        raise HTTPException(status_code=400, detail="Impossible de passer la main en vue simulée.")


def _trop_d_essais(uid: int) -> bool:
    now = time.time()
    liste = [t for t in _essais.get(uid, []) if now - t < _ESSAIS_FENETRE]
    _essais[uid] = liste
    return len(liste) >= _ESSAIS_MAX


def _noter_echec(uid: int) -> None:
    _essais.setdefault(uid, []).append(time.time())


def _planifies_sur(conn, machine_id: Optional[int]) -> set:
    """Conducteurs planifiés aujourd'hui sur cette machine (Planning RH)."""
    if not machine_id:
        return set()
    from app.routers.fabrication import _rh_machines_du_jour  # import tardif : gros module

    now = datetime.now(_PARIS)
    ids = set()
    for r in conn.execute(
        "SELECT id FROM users WHERE actif=1 AND role=?", (ROLE_CONDUCTEUR,)
    ).fetchall():
        try:
            if any(int(m["machine_id"]) == int(machine_id) for m in _rh_machines_du_jour(conn, r["id"], now)):
                ids.add(int(r["id"]))
        except Exception:
            continue
    return ids


@router.get("/api/fabrication/relais/operateurs")
def relais_operateurs(request: Request, machine_id: Optional[int] = None):
    """Conducteurs à qui passer la main : comptes actifs du rôle fabrication,
    sauf soi-même. Ceux planifiés sur la machine aujourd'hui d'abord."""
    user = get_current_user(request)
    _check_acces(user)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, operateur_lie FROM users
                WHERE actif=1 AND role=? AND id<>?
             ORDER BY nom COLLATE NOCASE""",
            (ROLE_CONDUCTEUR, int(user.get("id") or 0)),
        ).fetchall()
        planifies = _planifies_sur(conn, machine_id)
    out = [
        {
            "id": int(r["id"]),
            "nom": (r["operateur_lie"] or r["nom"] or "").strip(),
            "planifie": int(r["id"]) in planifies,
        }
        for r in rows
    ]
    out.sort(key=lambda o: (not o["planifie"], o["nom"].lower()))
    return {"operateurs": out}


@router.post("/api/fabrication/relais/verifier")
async def relais_verifier(request: Request):
    user = get_current_user(request)
    _check_acces(user)
    body = await request.json()
    try:
        vers_id = int(body.get("vers_user_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Choisissez le conducteur qui reprend.")
    code = str(body.get("code") or "")
    if not code:
        raise HTTPException(status_code=400, detail="Code du conducteur requis.")
    uid = int(user.get("id") or 0)
    if vers_id == uid:
        raise HTTPException(status_code=400, detail="Choisissez un autre conducteur que vous.")
    if _trop_d_essais(uid):
        raise HTTPException(status_code=429, detail="Trop de codes erronés — réessayez dans quelques minutes.")

    with get_db() as conn:
        cible = conn.execute(
            "SELECT id, nom, operateur_lie, role, password_hash FROM users WHERE id=? AND actif=1",
            (vers_id,),
        ).fetchone()
    if not cible or cible["role"] != ROLE_CONDUCTEUR:
        raise HTTPException(status_code=400, detail="Conducteur introuvable.")
    try:
        ok = verify_password(code, cible["password_hash"] or "")
    except Exception:
        ok = False
    if not ok:
        _noter_echec(uid)
        # 400 et pas 401 : l'écran traite tout 401 comme une session expirée.
        raise HTTPException(status_code=400, detail="Code incorrect.")

    token = create_session(int(cible["id"]), cible["role"])
    nom = (cible["operateur_lie"] or cible["nom"] or "").strip()
    resp = JSONResponse({"success": True, "nom": nom})
    resp.set_cookie(
        key=COOKIE_RELAIS, value=token, httponly=True, samesite="lax", secure=False,
        max_age=FAB_RELAIS_DELAI_SECONDES,
    )
    return resp


@router.post("/api/fabrication/relais/basculer")
async def relais_basculer(request: Request):
    user = get_current_user(request)
    _check_acces(user)
    body = await request.json()
    token = request.cookies.get(COOKIE_RELAIS)
    nouveau = get_user_by_token(token) if token else None
    if not nouveau:
        raise HTTPException(status_code=400, detail="Relais expiré — le conducteur doit ressaisir son code.")
    try:
        machine_id = int(body.get("machine_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Machine manquante.")
    no_dossier = (body.get("no_dossier") or "").strip() or None
    compteur = body.get("compteur")
    try:
        compteur = float(compteur) if compteur not in (None, "") else None
    except (TypeError, ValueError):
        compteur = None

    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM machines WHERE id=?", (machine_id,)).fetchone():
            raise HTTPException(status_code=400, detail="Machine introuvable.")
        conn.execute(
            """INSERT INTO fab_relais
                   (machine_id, no_dossier, de_user_id, vers_user_id, compteur, created_at)
               VALUES (?,?,?,?,?,?)""",
            (machine_id, no_dossier, int(user.get("id") or 0) or None, int(nouveau["id"]),
             compteur, datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")),
        )
        conn.commit()

    ancien = request.cookies.get(COOKIE_NAME)
    if ancien:
        delete_session(ancien)
    nom_avant = (user.get("operateur_lie") or user.get("nom") or "").strip()
    nom_apres = (nouveau.get("operateur_lie") or nouveau.get("nom") or "").strip()
    log_action(
        user=user,
        action="UPDATE",
        module="fabrication",
        objet=f"Passage de main · {nom_avant} → {nom_apres}" + (f" · {no_dossier}" if no_dossier else ""),
    )
    resp = JSONResponse({"success": True, "nom": nom_apres})
    resp.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, samesite="lax", secure=False,
        max_age=session_hours_for_role(nouveau.get("role")) * 3600,
    )
    resp.delete_cookie(COOKIE_RELAIS)
    return resp


@router.delete("/api/fabrication/relais")
def relais_abandonner(request: Request):
    token = request.cookies.get(COOKIE_RELAIS)
    if token:
        delete_session(token)
    resp = JSONResponse({"success": True})
    resp.delete_cookie(COOKIE_RELAIS)
    return resp
