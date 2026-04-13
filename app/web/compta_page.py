"""MySifa — Page MyCompta (standalone)

Accès : direction, administration, comptabilite
URL   : /compta
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontend.html import render_frontend_html
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response


router = APIRouter()


@router.get("/compta", response_class=HTMLResponse)
def compta_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/compta", status_code=302)
        raise
    if not user_has_app_access(user, "compta"):
        return access_denied_response("MyCompta")
    return HTMLResponse(content=render_frontend_html("compta"))

