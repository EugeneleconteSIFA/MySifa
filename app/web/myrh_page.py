"""MySifa — Page MyRH (standalone).

Suivi des nouveaux employés : l'Outil RH (formations, documents
administratifs, contrats), auparavant onglet de MyCompta.
Accès : application « myrh » (Paramètres › Accès) ; au lancement, les mêmes
rôles que MyCompta (config.ROLES_MYRH).
URL   : /rh
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontend.html import render_frontend_html
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response


router = APIRouter()


@router.get("/rh", response_class=HTMLResponse)
def myrh_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/rh", status_code=302)
        raise
    if not user_has_app_access(user, "myrh"):
        return access_denied_response("MyRH")
    return HTMLResponse(content=render_frontend_html("myrh"))
