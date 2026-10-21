"""Maintenance › alertes — assistant IA (créer ou modifier une alerte).

Mêmes droits que la gestion des alertes (`_require_alerts_admin`), même
validation que le formulaire (`_validate_alert_params`). Rien n'est
enregistré : la proposition revient au formulaire, que l'utilisateur relit
et enregistre par le chemin habituel (POST / PATCH /api/maintenance/alerts).

Service : app/services/alertes_ia.py.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.core.database import get_db
from app.routers.settings import _require_alerts_admin, _validate_alert_params
from app.services import alertes_ia
from app.services import ia_usage
from app.services.qualite_formulaires_ia import PIECE_MAX_OCTETS, PIECES_ACCEPTEES, PIECES_MAX

router = APIRouter(prefix="/api/maintenance/alerts/ia", tags=["maintenance_alertes_ia"])


def _machines(conn) -> list[str]:
    try:
        rows = conn.execute("SELECT nom FROM machines WHERE COALESCE(actif, 1) = 1 ORDER BY id").fetchall()
    except Exception:
        return []
    return [r["nom"] for r in rows if r["nom"]]


@router.get("/modeles")
def modeles(request: Request):
    _require_alerts_admin(request)
    return {"modeles": alertes_ia.alertes_ia_modeles(), "defaut": alertes_ia.choisir_modele(None)["id"]}


@router.post("/proposer")
async def proposer(
    request: Request,
    consigne: str = Form(""),
    nom: str = Form(""),
    params: str = Form(""),
    modele: Optional[str] = Form(None),
    fichiers: list[UploadFile] = File(default=[]),
):
    """`params` (JSON) = l'alerte telle qu'elle est dans le formulaire,
    enregistrée ou non ; vide = création."""
    user = _require_alerts_admin(request)
    consigne = (consigne or "").strip()[:6000]
    fichiers = [f for f in (fichiers or []) if f and f.filename]
    if not consigne and not fichiers:
        raise HTTPException(status_code=400, detail="Décrire l'alerte souhaitée ou joindre une fiche de contrôle.")
    if len(fichiers) > PIECES_MAX:
        raise HTTPException(status_code=400, detail=f"{PIECES_MAX} documents au plus.")
    pieces = []
    for f in fichiers:
        mime = (f.content_type or "").lower()
        if mime not in PIECES_ACCEPTEES:
            raise HTTPException(status_code=400, detail=f"« {f.filename} » : seuls les PDF et les images (PNG, JPG, WEBP, GIF) sont lus.")
        contenu = await f.read(PIECE_MAX_OCTETS + 1)
        if len(contenu) > PIECE_MAX_OCTETS:
            raise HTTPException(status_code=400, detail=f"« {f.filename} » dépasse 15 Mo.")
        pieces.append({"mime": mime, "contenu": contenu, "nom": f.filename[:120]})
    try:
        actuel = json.loads(params) if params else {}
    except ValueError:
        actuel = {}
    if not isinstance(actuel, dict):
        actuel = {}
    with get_db() as conn:
        machines = _machines(conn)
    try:
        with ia_usage.suivi(user, "alertes", "maintenance"):
            return alertes_ia.proposer(consigne, nom=(nom or "")[:120], params=actuel, machines=machines,
                                       valider=_validate_alert_params, pieces=pieces, modele=modele)
    except alertes_ia.AlerteIaErreur as exc:
        raise HTTPException(status_code=400, detail=str(exc))
