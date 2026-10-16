"""MySifa — Paramètres › Cohérence : la file des écarts et ses réglages.

  GET  /api/settings/coherence                     écarts (filtres famille, statut, regle, q)
  POST /api/settings/coherence/{id}/expliquer      l'écart est normal : il sort de la pastille
  POST /api/settings/coherence/{id}/rouvrir
  GET  /api/settings/coherence/reglages
  PUT  /api/settings/coherence/reglages
  POST /api/settings/coherence/relancer            passage immédiat des contrôleurs

Les contrôleurs eux-mêmes vivent dans app/services/coherence.py. Accès :
direction et super administrateur, comme le reste de la section Audit & qualité.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from app.services import coherence
from app.services.audit_service import log_action
from services.auth_service import require_settings_audit

router = APIRouter(prefix="/api/settings/coherence", tags=["coherence"])


class ExplicationIn(BaseModel):
    explication: str


class ReglagesIn(BaseModel):
    seuils: Optional[dict] = None
    regles: Optional[dict] = None


@router.get("")
def lister(request: Request, famille: Optional[str] = None, statut: str = "ouvert",
           regle: Optional[str] = None, q: Optional[str] = None, limite: int = 300):
    require_settings_audit(request)
    if famille and famille not in coherence.FAMILLES:
        raise HTTPException(400, detail="Famille inconnue.")
    if statut not in coherence.STATUTS + ("tous",):
        raise HTTPException(400, detail="Statut inconnu.")
    with get_db() as conn:
        res = coherence.lister(conn, famille, statut, regle, q, limite)
        res["ouverts_par_famille"] = {
            r["famille"]: r["n"] for r in conn.execute(
                "SELECT famille, COUNT(*) AS n FROM coherence_ecarts WHERE statut='ouvert' GROUP BY famille")}
    res["familles"] = coherence.FAMILLES
    res["regles"] = {c: {"titre": r.titre, "famille": r.famille} for c, r in coherence.REGLES.items()}
    return res


@router.post("/{ecart_id}/expliquer")
def expliquer(ecart_id: int, body: ExplicationIn, request: Request):
    user = require_settings_audit(request)
    qui = user.get("nom") or user.get("email") or ""
    with get_db() as conn:
        try:
            ligne = coherence.expliquer(conn, ecart_id, body.explication, qui)
        except LookupError as e:
            raise HTTPException(404, detail=str(e))
        except ValueError as e:
            raise HTTPException(400, detail=str(e))
    log_action(user=user, action="VALIDATE", module="settings",
               objet=f"Écart de cohérence · {ligne['titre']}",
               detail={"regle": ligne["regle"], "explication": ligne["explication"]}, request=request)
    return {"ok": True, "statut": ligne["statut"]}


@router.post("/{ecart_id}/rouvrir")
def rouvrir(ecart_id: int, request: Request):
    user = require_settings_audit(request)
    with get_db() as conn:
        coherence.rouvrir(conn, ecart_id)
    log_action(user=user, action="UPDATE", module="settings",
               objet=f"Écart de cohérence #{ecart_id} rouvert", request=request)
    return {"ok": True}


def _reglages_vue(conn) -> dict:
    reg = coherence.charger_reglages(conn)
    return {
        "seuils": [{"cle": c, "libelle": l, "unite": u, "valeur": reg["seuils"][c], "defaut": d}
                   for c, (d, l, u) in coherence.SEUILS.items()],
        "regles": [{"code": c, "titre": r.titre, "description": r.description, "famille": r.famille,
                    "gravite": r.gravite, "actif": reg["regles"][c]} for c, r in coherence.REGLES.items()],
        "familles": coherence.FAMILLES,
    }


@router.get("/reglages")
def lire_reglages(request: Request):
    require_settings_audit(request)
    with get_db() as conn:
        return _reglages_vue(conn)


@router.put("/reglages")
def ecrire_reglages(body: ReglagesIn, request: Request):
    user = require_settings_audit(request)
    with get_db() as conn:
        try:
            coherence.enregistrer_reglages(conn, {"seuils": body.seuils or {}, "regles": body.regles or {}})
        except ValueError as e:
            raise HTTPException(400, detail=str(e))
        vue = _reglages_vue(conn)
    log_action(user=user, action="UPDATE", module="settings", objet="Réglages des contrôles de cohérence",
               detail={"seuils": body.seuils, "regles": body.regles}, request=request)
    return vue


@router.post("/relancer")
def relancer(request: Request):
    require_settings_audit(request)
    return coherence.tour(get_db)
