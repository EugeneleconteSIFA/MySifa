"""MyExpé — page dédiée (v0)."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from services.auth_service import get_current_user, user_has_app_access
from frontend.html import render_frontend_html
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/expe", response_class=HTMLResponse)
def expe_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/expe", status_code=302)
        raise

    if not user_has_app_access(user, "expe"):
        return access_denied_response("MyExpé")

    return HTMLResponse(content=render_frontend_html("expe"))

