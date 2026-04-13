"""MySifa — Page MyProd (standalone)

Accès : /prod
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontend.html import render_frontend_html
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response


router = APIRouter()


@router.get("/prod", response_class=HTMLResponse)
def prod_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/prod", status_code=302)
        raise
    if not user_has_app_access(user, "prod"):
        return access_denied_response("MyProd")
    return HTMLResponse(content=render_frontend_html("prod"))

