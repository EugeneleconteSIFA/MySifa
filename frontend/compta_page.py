"""MySifa — Page MyCompta (standalone)

Accès : direction, administration, comptabilite
URL   : /compta
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from frontend.html import render_frontend_html
from services.auth_service import get_current_user
from config import ROLES_COMPTA


router = APIRouter()


@router.get("/compta", response_class=HTMLResponse)
def compta_page(request: Request):
    user = get_current_user(request)
    if user.get("role") not in ROLES_COMPTA:
        raise HTTPException(status_code=403, detail="Accès réservé à MyCompta")
    return HTMLResponse(content=render_frontend_html("compta"))

