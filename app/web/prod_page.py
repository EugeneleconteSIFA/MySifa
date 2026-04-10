"""MySifa — Page MyProd (standalone)

Accès : /prod
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from frontend.html import render_frontend_html
from services.auth_service import get_current_user


router = APIRouter()


@router.get("/prod", response_class=HTMLResponse)
def prod_page(request: Request):
    user = get_current_user(request)
    if user.get("role") not in {"direction", "administration", "fabrication"}:
        raise HTTPException(status_code=403, detail="Accès réservé à MyProd")
    return HTMLResponse(content=render_frontend_html("prod"))

