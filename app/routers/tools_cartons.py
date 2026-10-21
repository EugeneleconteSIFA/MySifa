"""MyTools › Calculs bobine › Carton — références carton lisibles.

  GET /api/tools/cartons   cartons MyStock avec dimensions en mm, et ceux écartés

Lecture seule, ouverte à tout utilisateur connecté (des dimensions de carton,
rien de sensible). Le calcul de rangement se fait dans le navigateur.
"""
from fastapi import APIRouter, Request

from database import get_db
from app.services import cartons
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/tools/cartons", tags=["tools"])


@router.get("")
def liste_cartons(request: Request):
    get_current_user(request)
    with get_db() as conn:
        return cartons.liste(conn)
