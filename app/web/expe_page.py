"""MyExpé — page dédiée (v0)."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from config import ROLES_EXPE
from services.auth_service import get_current_user
from frontend.html import render_frontend_html

router = APIRouter()


@router.get("/expe", response_class=HTMLResponse)
def expe_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/expe", status_code=302)
        raise

    if user.get("role") not in ROLES_EXPE:
        raise HTTPException(status_code=403, detail="Accès réservé à MyExpé")

    return HTMLResponse(content=render_frontend_html("expe"))

