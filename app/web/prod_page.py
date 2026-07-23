"""MySifa - Page MyProd (standalone)

Acces : /prod

Strategie de migration (Phase 2 - extraction du monolithe html.py) :
- Par defaut depuis 2m : PROD_STANDALONE=True dans config.py - sert PROD_HTML.
- PROD_STANDALONE=0 dans .env force un rollback vers le monolithe (debug).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ENV_NAME, IS_STAGING, PROD_STANDALONE
from frontend.html import render_frontend_html
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response


router = APIRouter()


def _build_prod_html() -> str:
    """Construit le HTML standalone /prod en injectant les variables runtime
    (APP_VERSION, ENV_NAME). Le bandeau et son sélecteur d'impersonation sont
    injectés par /static/mysifa_impersonate.js — self-contained."""
    # En v1 on ajoute la classe pour le padding-top du body (le JS la maintient
    # de son côté, mais on la pose dès le HTML pour éviter le saut visuel).
    staging_class = "has-staging-bandeau" if IS_STAGING else ""
    return (
        _PROD_HTML_TEMPLATE
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__ENV_NAME_VALUE__", ENV_NAME)
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


# Template HTML brut, avec placeholders resolus par _build_prod_html().
# Cache-buster ?v=__V_LABEL__ sur tous les assets statiques : APP_VERSION
# change a chaque release, le browser recharge automatiquement le CSS/JS.
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
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/motion.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_myprod_shell.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_prod_core.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_print_modal.css?v=__V_LABEL__">
<script src="/static/motion.js?v=__V_LABEL__" defer></script>
</head>
<body class="__STAGING_BODY_CLASS__">
<script>window.__MYSIFA_ENV__="__ENV_NAME_VALUE__";window.__APP_VERSION__="__V_LABEL__";</script>
<div id="root">
  <div style="padding:40px;text-align:center;color:var(--text2);font-size:13px">
    Chargement...
  </div>
</div>
<script src="/static/mysifa_theme.js?v=__V_LABEL__"></script>
<script src="/static/mysifa_user_chip.js?v=__V_LABEL__"></script>
<script src="/static/mysifa_guides.js?v=__V_LABEL__"></script>
<script src="/static/mysifa_prod_core.js?v=__V_LABEL__"></script>
<script src="/static/mysifa_print_modal.js?v=__V_LABEL__"></script>
<script src="/static/mysifa_impersonate.js?v=__V_LABEL__"></script>
<!-- v2.3.42 : viewer partagé du détail d'un ack d'alerte (identique à Maintenance) -->
<script src="/static/mysifa_ack_viewer.js?v=__V_LABEL__"></script>
</body>
</html>"""
