"""Postes de déroulement, reconnaissance des bobines et bobines montées.

Trois lots du chantier « scan matière en production » (10/09/2026) :

1. le référentiel — postes par machine et règles de préfixe par fournisseur,
   édités dans Paramètres › Machines › Postes de déroulement ;
2. la reconnaissance du poste d'une bobine à partir de son code
   (`app/services/poste_bobine.py`) ;
3. l'état des postes de chaque machine (`app/services/bobines_montees.py`).

Le branchement sur le scan lui-même vit dans `fabrication.py`
(`POST /api/fabrication/matieres`) : ce routeur n'expose que ce qui se lit ou
se corrige à côté.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from config import CATEGORIES_BOBINE, postes_deroulement
from database import get_db
from app.services import bobines_montees as bm
from app.services import poste_bobine as pb
from app.services.audit_service import log_action
from app.services.auth_service import (
    get_current_user, is_admin, is_fabrication, require_admin, require_settings,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _ip(request: Request):
    return request.client.host if request.client else None


def _qui(user: dict) -> str:
    return user.get("operateur_lie") or user.get("nom") or user.get("login") or ""


def _check_fab_access(user: dict) -> None:
    if not (is_fabrication(user) or is_admin(user)):
        raise HTTPException(status_code=403, detail="Accès réservé au service Fabrication")


def _cats(raw):
    try:
        v = json.loads(raw or "[]")
        return [str(x) for x in v] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


# ══ Paramètres ═══════════════════════════════════════════════════════════════

@router.get("/api/settings/postes-deroulement")
def lire_referentiel(request: Request):
    """Tout l'écran Paramètres › Machines › Postes de déroulement en un appel."""
    require_settings(request)
    with get_db() as conn:
        machines = []
        for m in conn.execute(
            "SELECT id, nom, code, COALESCE(sans_matiere_premiere,0) AS smp "
            "FROM machines WHERE COALESCE(actif,1)=1 ORDER BY id"
        ).fetchall():
            machines.append({
                "id": m["id"], "nom": m["nom"], "code": m["code"],
                "sans_matiere_premiere": int(m["smp"]),
                "postes": pb.postes_machine(conn, m["id"], actifs_seulement=False),
            })
        fournisseurs = [
            {"id": f["id"], "nom": f["nom"], "categories": _cats(f["categories"])}
            for f in conn.execute(
                "SELECT id, nom, categories FROM fournisseurs_fsc "
                "WHERE COALESCE(actif,1)=1 ORDER BY lower(nom)"
            ).fetchall()
        ]
        return {
            "postes": postes_deroulement(),
            "categories": list(CATEGORIES_BOBINE),
            "places_max": pb.PLACES_MAX,
            "machines": machines,
            "regles": pb.regles_code(conn),
            "fournisseurs": fournisseurs,
            "diagnostic": pb.diagnostic(conn),
        }


@router.put("/api/settings/machines/{machine_id}/postes-deroulement")
async def enregistrer_postes(machine_id: int, request: Request):
    user = require_admin(request)
    body = await request.json()
    with get_db() as conn:
        m = conn.execute("SELECT id, nom FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not m:
            raise HTTPException(404, "Machine introuvable.")
        try:
            postes = pb.enregistrer_postes(conn, machine_id, body.get("postes") or [], _qui(user))
        except ValueError as e:
            raise HTTPException(400, str(e))
        conn.commit()
    log_action(user=user, action="UPDATE", module="settings",
               objet=f"Postes de déroulement · {m['nom']}",
               detail={"postes": [{k: p[k] for k in ("poste", "places", "actif")} for p in postes]},
               ip=_ip(request))
    return {"success": True, "postes": postes}


async def _ecrire_regle(request: Request, regle_id=None):
    user = require_admin(request)
    body = await request.json()
    with get_db() as conn:
        try:
            r = pb.enregistrer_regle(
                conn, body.get("fournisseur_id"), body.get("motif"), body.get("categorie"),
                body.get("note"), _qui(user), regle_id=regle_id, actif=body.get("actif", 1),
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except LookupError as e:
            raise HTTPException(404, str(e))
        conn.commit()
    log_action(user=user, action="UPDATE" if regle_id else "CREATE", module="settings",
               objet=f"Règle de code bobine · {r['fournisseur']} « {r['motif'] or 'tout autre code'} »",
               detail={"categorie": r["categorie"], "actif": r["actif"]}, ip=_ip(request))
    return {"success": True, "regle": r}


@router.post("/api/settings/regles-code")
async def creer_regle(request: Request):
    return await _ecrire_regle(request)


@router.put("/api/settings/regles-code/{regle_id}")
async def modifier_regle(regle_id: int, request: Request):
    return await _ecrire_regle(request, regle_id)


@router.delete("/api/settings/regles-code/{regle_id}")
def supprimer_regle(regle_id: int, request: Request):
    user = require_admin(request)
    with get_db() as conn:
        if not pb.supprimer_regle(conn, regle_id):
            raise HTTPException(404, "Règle introuvable.")
        conn.commit()
    log_action(user=user, action="DELETE", module="settings",
               objet=f"Règle de code bobine #{regle_id}", detail={}, ip=_ip(request))
    return {"success": True}


@router.post("/api/settings/postes-deroulement/reconstruire")
def reconstruire(request: Request):
    """Réapprend les natures depuis les scans passés — après correction d'une fiche fournisseur."""
    user = require_admin(request)
    with get_db() as conn:
        bilan = pb.reconstruire_categories(conn)
        conn.commit()
    log_action(user=user, action="UPDATE", module="settings",
               objet="Mémoire des natures de bobines reconstruite", detail=bilan, ip=_ip(request))
    return {"success": True, **bilan}


# ══ Atelier ══════════════════════════════════════════════════════════════════

@router.get("/api/fabrication/bobines/poste")
def poste_d_une_bobine(request: Request, code_barre: str, machine_id: int | None = None,
                       no_dossier: str | None = None):
    user = get_current_user(request)
    _check_fab_access(user)
    with get_db() as conn:
        return pb.resoudre(conn, code_barre, machine_id=machine_id,
                           no_dossier=(no_dossier or "").strip() or None)


@router.get("/api/fabrication/machines/{machine_id}/bobines-montees")
def bobines_montees(machine_id: int, request: Request):
    user = get_current_user(request)
    _check_fab_access(user)
    with get_db() as conn:
        return bm.etat_machine(conn, machine_id)


@router.post("/api/fabrication/matieres/{matiere_id}/poste")
async def fixer_poste(matiere_id: int, request: Request):
    """L'opérateur arrête la nature d'une bobine scannée : Frontal, Complexe ou Glassine."""
    user = get_current_user(request)
    _check_fab_access(user)
    body = await request.json()
    with get_db() as conn:
        try:
            res = bm.fixer_poste(conn, matiere_id, body.get("categorie"), par=_qui(user))
        except ValueError as e:
            raise HTTPException(400, str(e))
        except LookupError as e:
            raise HTTPException(404, str(e))
        try:
            code = conn.execute("SELECT code_barre FROM fab_matieres_utilisees WHERE id=?",
                                (matiere_id,)).fetchone()["code_barre"]
            pb.apprendre_categorie(conn, code, body.get("categorie"))
        except Exception:
            logger.warning("Apprentissage de la nature ignoré", exc_info=True)
        conn.commit()
    log_action(user=user, action="UPDATE", module="fabrication",
               objet=f"Poste de la bobine #{matiere_id}",
               detail={"categorie": body.get("categorie"), "action": res["action"]}, ip=_ip(request))
    return {"success": True, **res}


@router.post("/api/fabrication/bobines-montees/{montee_id}/demonter")
def demonter(montee_id: int, request: Request):
    user = get_current_user(request)
    _check_fab_access(user)
    with get_db() as conn:
        try:
            r = bm.demonter(conn, montee_id, par=_qui(user))
        except LookupError as e:
            raise HTTPException(404, str(e))
        conn.commit()
    log_action(user=user, action="UPDATE", module="fabrication",
               objet=f"Bobine démontée · {r['code_barre']}",
               detail={"machine_id": r["machine_id"], "poste": r["poste"]}, ip=_ip(request))
    return {"success": True, "montee": r}
