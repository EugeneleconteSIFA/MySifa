"""Ancienne route MyDevis — redirige vers Coûts matières (/pricing)."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/devis")
def devis_redirect(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/pricing", status_code=302)
        raise

    if not user_has_app_access(user, "pricing"):
        return access_denied_response("Coûts matières")

    return RedirectResponse(url="/pricing", status_code=302)
