"""Portail — volets de navigation.

  GET /api/portail/volets    le catalogue des sous-menus, déjà filtré par le
                             rôle. Le front n'en connaît rien d'autre : une
                             entrée absente de la réponse n'existe pas pour ce
                             navigateur.

Ce module a porté un temps la reprise de navigation (« Reprendre où j'en
étais »). Elle a été retirée le 28 août — le rendu ne convainquait pas, et une
barre permanente en haut de page coûte 38 px sur tous les écrans. La table
`portail_recents` est supprimée par une migration dédiée.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.services import portail_volets
from app.services.auth_service import get_current_user

router = APIRouter(tags=["portail"])


def _role_effectif(user: dict) -> str:
    """Le rôle simulé quand le superadmin est en impersonation, sinon le sien.

    Même choix que `/api/auth/me` : ce que voit le front doit correspondre à ce
    que verrait vraiment l'utilisateur simulé, volets compris.
    """
    return str(user.get("effective_role") or user.get("role") or "")


@router.get("/api/portail/volets")
def volets(request: Request):
    user = get_current_user(request)
    return {"volets": portail_volets.volets_pour(_role_effectif(user))}
