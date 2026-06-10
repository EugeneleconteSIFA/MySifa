"""MySifa - Page MyProd (standalone)

Acces : /prod

Strategie de migration (Phase 2 - extraction du monolithe html.py) :
- Par defaut (PROD_STANDALONE=0 dans .env, ou variable absente) : le rendu passe
  par render_frontend_html("prod") - comportement historique inchange.
- Si PROD_STANDALONE=1 : sert PROD_HTML (coquille standalone, en cours de
  construction). Permet de tester la nouvelle page sur v1 sans impacter v2.

Decoupage par etapes :
- 2c : coquille minimale (placeholder) OK
- 2d : coquille avec <link>/<script> vers /static/mysifa_prod_core.{css,js} OK
- 2e : socle JS (helpers + state S filtre) dans mysifa_prod_core.js OK
- 2f : auth + sidebar + render squelette <- ICI
- 2g/h : page Production (KPIs + statut machines + sanity + filtres)
- 2i/j/k/l : onglets Historique/Saisies/Import, Dossiers/Suivi/Rentabilite,
             Tracabilite, OF
- 2m : activation par defaut sur v1, tests croises
- 2n : retrait du code prod du monolithe + suppression du flag
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, IS_STAGING, PROD_STANDALONE
from frontend.html import render_frontend_html
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response


router = APIRouter()


def _build_prod_html() -> str:
    """Construit le HTML standalone /prod en injectant les variables runtime
    (APP_VERSION, bandeau staging). Appele a chaque requete pour rester
    aligne sur la config en cours."""
    if IS_STAGING:
        staging_html = (
            '<div class="staging-bandeau">'
            'v1 - Environnement de test - DB partagee avec la prod'
            '</div>'
        )
        staging_class = "has-staging-bandeau"
    else:
        staging_html = ""
        staging_class = ""
    return (
        _PROD_HTML_TEMPLATE
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__STAGING_BANDEAU_HTML__", staging_html)
        .replace("__STAGING_BODY_CLASS__", staging_class)
    )


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

    if PROD_STANDALONE:
        return HTMLResponse(
            content=_build_prod_html(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    # Fallback : rendu via le monolithe html.py (comportement historique)
    return HTMLResponse(content=render_frontend_html("prod"))


# Template HTML brut, avec placeholders __V_LABEL__, __STAGING_BANDEAU_HTML__,
# __STAGING_BODY_CLASS__ resolus par _build_prod_html().
_PROD_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>MyProd - MySifa</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_prod_core.css">
</head>
<body class="__STAGING_BODY_CLASS__">
__STAGING_BANDEAU_HTML__
<div id="root">
  <div style="padding:40px;text-align:center;color:var(--text2);font-size:13px">
    Chargement...
  </div>
</div>
<script>window.__APP_VERSION__ = "__V_LABEL__";</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_prod_core.js"></script>
</body>
</html>"""
