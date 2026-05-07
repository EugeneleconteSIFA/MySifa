"""MySifa — Page Profil (standalone)

Accès : /profil

Note: cette page réutilise l'app frontend "prod" (renderProfil).
Elle doit rester accessible à tout utilisateur authentifié, même sans accès MyProd.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontend.html import render_frontend_html
from services.auth_service import get_current_user


router = APIRouter()


@router.get("/profil", response_class=HTMLResponse)
def profil_page(request: Request):
    try:
        _ = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/profil", status_code=302)
        raise
    return HTMLResponse(content=render_frontend_html("prod"))

