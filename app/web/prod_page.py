"""MySifa — Page MyProd (standalone)

Accès : /prod

Stratégie de migration (Phase 2 — extraction du monolithe html.py) :
- Par défaut (PROD_STANDALONE=0 dans .env, ou variable absente) : le rendu passe
  par render_frontend_html("prod") — comportement historique inchangé.
- Si PROD_STANDALONE=1 : sert PROD_HTML (coquille standalone, en cours de
  construction). Permet de tester la nouvelle page sur v1 sans impacter v2.

Découpage par étapes :
- 2c : coquille minimale (placeholder) ✓
- 2d : coquille avec <link>/<script> vers /static/mysifa_prod_core.{css,js} ← ICI
- 2e : socle JS (helpers + state S filtré) dans mysifa_prod_core.js
- 2f : auth + sidebar + render() squelette
- 2g/h : page Production (KPIs + statut machines + sanity + filtres)
- 2i/j/k/l : onglets Historique/Saisies/Import, Dossiers/Suivi/Rentabilité,
             Traçabilité, OF
- 2m : activation par défaut sur v1, tests croisés
- 2n : retrait du code prod du monolithe + suppression du flag
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import PROD_STANDALONE
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

    if PROD_STANDALONE:
        return HTMLResponse(
            content=PROD_HTML,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    # Fallback : rendu via le monolithe html.py (comportement historique)
    return HTMLResponse(content=render_frontend_html("prod"))


# ──────────────────────────────────────────────────────────────────────
# PROD_HTML — coquille standalone (étape 2d)
#
# Inclut les feuilles de style et le JS de boilerplate situés dans
# /static/mysifa_prod_core.{css,js}. Les étapes suivantes rempliront
# progressivement ces fichiers tout en gardant le flag PROD_STANDALONE
# désactivé en prod (= aucun impact tant qu'on n'a pas terminé).
# ──────────────────────────────────────────────────────────────────────
PROD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>MyProd — MySifa</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_prod_core.css">
</head>
<body>
<div id="root">
  <div class="prod-migration-placeholder">
    <div class="stage-badge">Étape 2d</div>
    <h1>My<span>Prod</span> — page standalone en migration</h1>
    <p>
      Cette page est servie par <code>app/web/prod_page.py</code> parce que
      <code>PROD_STANDALONE=1</code> est actif dans le <code>.env</code>.
    </p>
    <p>
      Les feuilles <code>/static/mysifa_prod_core.css</code> et
      <code>/static/mysifa_prod_core.js</code> sont chargées (vérifie la console
      du navigateur pour confirmation).
    </p>
    <p>
      Le contenu réel de MyProd sera ajouté progressivement par les étapes
      <strong>2e à 2l</strong>. Pour revenir au rendu via le monolithe, mets
      <code>PROD_STANDALONE=0</code> dans le <code>.env</code> puis redémarre l'app.
    </p>
    <p style="margin-top:8px"><a href="/">← Retour au portail</a></p>
  </div>
</div>
<script src="/static/mysifa_prod_core.js"></script>
</body>
</html>"""
