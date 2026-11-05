"""MyTools › Calculs bobine — référentiels lus dans MyStock.

  GET /api/tools/cartons   cartons MyStock avec dimensions en mm, et ceux écartés
  GET /api/tools/couches   frontaux, adhésifs, glassines et leur épaisseur (µm)

Lecture seule, ouverte à tout utilisateur connecté comme l'outil (dimensions
de carton, épaisseurs et grammages de matière : aucun prix, rien de sensible).
Les calculs se font dans le navigateur.
"""
from fastapi import APIRouter, Request

from database import get_db
from app.services import cartons, couches_matieres
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/cartons")
def liste_cartons(request: Request):
    get_current_user(request)
    with get_db() as conn:
        return cartons.liste(conn)


@router.get("/couches")
def liste_couches(request: Request):
    get_current_user(request)
    with get_db() as conn:
        return couches_matieres.liste(conn)
