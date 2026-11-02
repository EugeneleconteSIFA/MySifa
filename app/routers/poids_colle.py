"""Saisie prod › widget « Poids de colle ».

  GET /api/fabrication/poids-colle?no_dossier=…   référentiel des grammages
      + ce que le dossier en cours en dit (format, papier, glassine, anilox)

Lecture ouverte à tout utilisateur connecté : formats et grammages types, rien
de sensible. Les grammages se modifient par PUT /api/stock/metrage-epaisseurs
(perimetre « grammage »), réservé aux administrateurs matières.
Calcul et rapprochement : app/services/poids_colle.py.
"""
from fastapi import APIRouter, Request

from config import MATIERE_FAMILLES
from database import get_db
from app.routers.stock import _STOCK_MATIERES_ADMIN_ROLES, _metrage_epaisseurs
from app.services import poids_colle
from app.services.auth_service import get_current_user, user_has_app_access

router = APIRouter(prefix="/api/fabrication", tags=["poids_colle"])


@router.get("/poids-colle")
def poids_colle_contexte(request: Request, no_dossier: str = ""):
    user = get_current_user(request)
    with get_db() as conn:
        lignes = _metrage_epaisseurs(conn)
        ctx = poids_colle.contexte(conn, no_dossier, lignes)
    return {
        "referentiel": [l for l in lignes if l["grammage_gsm"] is not None],
        "familles": [{"code": c, "libelle": l} for c, l in MATIERE_FAMILLES],
        "dossier": ctx,
        "peut_modifier": user.get("role") in _STOCK_MATIERES_ADMIN_ROLES and user_has_app_access(user, "stock"),
    }
