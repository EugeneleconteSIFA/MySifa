"""MySifa — Page MyProd (standalone)

Accès : /prod

Stratégie de migration (Phase 2 — extraction du monolithe html.py) :
- Par défaut (PROD_STANDALONE=0 dans .env, ou variable absente) : le rendu passe
  par render_frontend_html("prod") — comportement historique inchangé.
- Si PROD_STANDALONE=1 : sert PROD_HTML (coquille standalone, en cours de
  construction). Permet de tester la nouvelle page sur v1 sans impacter v2.
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
    # Fallback : ancien rendu via le monolithe html.py
    return HTMLResponse(content=render_frontend_html("prod"))


# ──────────────────────────────────────────────────────────────────────
# PROD_HTML — coquille standalone (étape 2c)
#
# Pour l'instant : minimal — sidebar absente, contenu vide. Les étapes 2d-2h
# rempliront le CSS, le state S filtré "/prod", les helpers JS et les fonctions
# render*/load* propres à MyProd. Tant que le flag PROD_STANDALONE n'est pas
# activé, cette coquille n'est jamais servie en production.
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
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.placeholder{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  min-height:100vh;padding:40px;text-align:center;gap:16px;
}
.placeholder h1{font-size:22px;font-weight:700;color:var(--text)}
.placeholder p{font-size:13px;color:var(--text2);max-width:480px;line-height:1.6}
.placeholder code{
  font-family:monospace;background:var(--card);border:1px solid var(--border);
  padding:2px 8px;border-radius:6px;color:var(--accent);font-size:12px;
}
.placeholder a{color:var(--accent);text-decoration:none;font-weight:600}
.placeholder a:hover{text-decoration:underline}
</style>
</head>
<body>
<div id="root">
  <div class="placeholder">
    <h1>MyProd — coquille standalone</h1>
    <p>
      Cette page est servie par <code>app/web/prod_page.py</code> parce que
      <code>PROD_STANDALONE=1</code> est actif dans le <code>.env</code>.
      Le contenu réel de MyProd sera migré progressivement depuis
      <code>app/web/html.py</code> dans les étapes 2d à 2h du refactor.
    </p>
    <p>
      Désactive le flag (<code>PROD_STANDALONE=0</code>) puis redémarre l'app
      pour revenir au rendu actuel via le monolithe.
    </p>
    <p>
      <a href="/">← Retour au portail</a>
    </p>
  </div>
</div>
</body>
</html>"""
