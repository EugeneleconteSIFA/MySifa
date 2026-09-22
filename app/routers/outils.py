"""Référentiel des outils montables — API atelier et API Paramètres.

Atelier (`/api/fabrication/outils`) : le conducteur lit la liste de sa nature
d'outil au moment d'un changement, et peut y ajouter le numéro qui manque
plutôt que de rester bloqué devant une liste incomplète. L'outil créé au poste
sort marqué « à valider ».

Paramètres (`/api/settings/outils`) : l'administrateur relit ces ajouts,
corrige un numéro, retire de la liste un outil qui ne tourne plus. Rien ne se
supprime — les saisies passées pointent sur ces lignes.

La saisie du changement elle-même vit dans `fabrication.py`
(`POST /api/fabrication/saisie`) : ce routeur n'expose que le référentiel.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from app.services import outils as ref
from app.services.audit_service import log_action
from app.services.auth_service import (
    get_current_user, is_admin, is_fabrication, require_settings,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _check_fab_access(user: dict) -> None:
    if not (is_fabrication(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Accès réservé au service Fabrication")


def _qui(user: dict) -> str:
    return user.get("operateur_lie") or user.get("nom") or user.get("login") or ""


def _bool(v, defaut: bool = False) -> bool:
    if v is None:
        return defaut
    return str(v).strip().lower() in ("1", "true", "oui", "on", "yes")


# ══ Atelier ══════════════════════════════════════════════════════════════════

@router.get("/api/fabrication/outils")
def fab_list_outils(request: Request, type: str = "", q: str = ""):
    """Liste des outils actifs d'une nature, pour le sélecteur du conducteur."""
    user = get_current_user(request)
    _check_fab_access(user)
    type_cle = (type or "").strip()
    with get_db() as conn:
        if type_cle and not ref.type_existe(conn, type_cle):
            raise HTTPException(status_code=404, detail="Nature d'outil inconnue.")
        return {
            "types": ref.list_types(conn),
            "outils": ref.list_outils(conn, type_cle=type_cle or None, q=q),
        }


@router.post("/api/fabrication/outils")
async def fab_creer_outil(request: Request):
    """Ajout d'un numéro absent de la liste, depuis le poste. Marqué à valider."""
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()
    type_cle = str(body.get("type") or body.get("type_cle") or "").strip()
    with get_db() as conn:
        try:
            outil = ref.creer_outil(
                conn,
                type_cle=type_cle,
                numero=body.get("numero"),
                label=body.get("label"),
                cree_par=_qui(user),
                a_valider=True,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        log_action(
            user=user, request=request, action="CREATE", module="outils",
            objet=f"{ref.label_type(conn, type_cle)} {outil['numero']}",
            detail={"origine": "poste atelier", "a_valider": outil["a_valider"]},
        )
        return outil


# ══ Paramètres ═══════════════════════════════════════════════════════════════

@router.get("/api/settings/outil-types")
def settings_list_types(request: Request):
    require_settings(request)
    with get_db() as conn:
        codes = ref.codes_par_type(conn)
        types = ref.list_types(conn, inclure_inactifs=True)
        for t in types:
            t["codes"] = sorted(c for c, k in codes.items() if k == t["cle"])
            t["nb_outils"] = len(ref.list_outils(conn, type_cle=t["cle"], limite=2000))
            t["nb_a_valider"] = ref.compter_a_valider(conn, t["cle"])
        return {"types": types}


@router.get("/api/settings/outils")
def settings_list_outils(request: Request, type: str = "", q: str = "", inactifs: str = ""):
    require_settings(request)
    with get_db() as conn:
        return {
            "types": ref.list_types(conn, inclure_inactifs=True),
            "outils": ref.list_outils(
                conn,
                type_cle=(type or "").strip() or None,
                q=q,
                inclure_inactifs=_bool(inactifs),
                limite=2000,
            ),
            "nb_a_valider": ref.compter_a_valider(conn),
        }


@router.post("/api/settings/outils")
async def settings_creer_outil(request: Request):
    user = require_settings(request)
    body = await request.json()
    type_cle = str(body.get("type") or body.get("type_cle") or "").strip()
    with get_db() as conn:
        try:
            outil = ref.creer_outil(
                conn,
                type_cle=type_cle,
                numero=body.get("numero"),
                label=body.get("label"),
                cree_par=_qui(user),
                a_valider=False,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        log_action(
            user=user, request=request, action="CREATE", module="outils",
            objet=f"{ref.label_type(conn, type_cle)} {outil['numero']}",
        )
        return outil


@router.put("/api/settings/outils/{outil_id}")
async def settings_maj_outil(outil_id: int, request: Request):
    user = require_settings(request)
    body = await request.json()
    with get_db() as conn:
        avant = ref.get_outil(conn, outil_id)
        if not avant:
            raise HTTPException(status_code=404, detail="Outil introuvable.")
        try:
            outil = ref.maj_outil(
                conn, outil_id,
                numero=body.get("numero"),
                label=body.get("label"),
                actif=body.get("actif"),
                a_valider=body.get("a_valider"),
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        log_action(
            user=user, request=request, action="UPDATE", module="outils",
            objet=f"{ref.label_type(conn, outil['type_cle'])} {outil['numero']}",
            detail={"avant": avant, "apres": outil},
        )
        return outil


@router.delete("/api/settings/outils/{outil_id}")
def settings_retirer_outil(outil_id: int, request: Request):
    """Retire l'outil de la liste. Désactivation, jamais suppression : des
    saisies de changement pointent dessus."""
    user = require_settings(request)
    with get_db() as conn:
        outil = ref.get_outil(conn, outil_id)
        if not outil:
            raise HTTPException(status_code=404, detail="Outil introuvable.")
        outil = ref.maj_outil(conn, outil_id, actif=False, a_valider=False)
        log_action(
            user=user, request=request, action="ARCHIVE", module="outils",
            objet=f"{ref.label_type(conn, outil['type_cle'])} {outil['numero']}",
        )
        return {"success": True, "outil": outil}
