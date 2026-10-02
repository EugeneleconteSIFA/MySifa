"""MySifa — Maquette du futur site vitrine (/website)

Accès : /website
Tout utilisateur authentifié. La page sert à montrer la refonte du site public
aux commerciaux avant sa mise en ligne : elle reste derrière la connexion et
n'est pas indexée (meta robots + en-tête X-Robots-Tag).

Le contenu vit dans app/web/website/index.html, hors de /static, pour que la
page ne soit pas lisible sans session. Seules les images sont dans
static/website/.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from services.auth_service import get_current_user

router = APIRouter()

_PAGE = Path(__file__).with_name("website") / "index.html"


@router.get("/website", response_class=HTMLResponse)
def website_page(request: Request):
    try:
        _ = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/website", status_code=302)
        raise
    html = _PAGE.read_text(encoding="utf-8")
    return HTMLResponse(
        content=html,
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-cache"},
    )
