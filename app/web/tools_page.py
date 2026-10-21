"""MySifa — MyTools : la boîte à outils transverse.
Route : /tools
Accès : tout utilisateur connecté ; chaque outil a ses droits (calculés ici,
servis à la page dans window.__MYTOOLS__, et revérifiés par chaque API).

  etiquettes   ROLES_MYPRINT (config.py) — ex-MyPrint, ex-onglet traça de MyStock
  formulaires  rôles qualité (app/routers/qualite.py) — ex-MyQualité › Formulaires
  pdf          tous — rien ne quitte le poste
  traduction   tous — API /api/translate (DeepL)
  calculs      tous — calculs bobine, rien n'est enregistré côté serveur

Le code des outils vit dans static/ : mysifa_tools.js (navigation, adresse),
mysifa_tools_etiquettes.js, mysifa_tools_traduction.js, mysifa_tools_pdf.js
(chargé à la demande). Le module Formulaires reste FORMULAIRES_JS
(app/web/qualite_formulaires_assets.py), injecté ici.
"""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_ORG_NAME, APP_VERSION, ROLES_MYPRINT
from app.routers.qualite import ROLES_QUALITE, ROLES_QUALITE_VIEW
from app.services.auth_service import get_current_user, is_superadmin
from app.web.components import asset
from app.web.qualite_formulaires_assets import FORMULAIRES_JS

router = APIRouter()


def droits_outils(user: dict) -> dict:
    """Ce que l'utilisateur peut ouvrir dans MyTools. Sert aussi au portail."""
    role = user.get("role") or ""
    sup = is_superadmin(user)
    return {
        "etiquettes": sup or role in ROLES_MYPRINT,
        "formulaires": sup or role in ROLES_QUALITE_VIEW,
        "formulaires_admin": sup or role in ROLES_QUALITE,
        "pdf": True,
        "traduction": True,
        "calculs": True,
    }


def _json_script(obj) -> str:
    # Sûr dans un <script> : aucune séquence « </ » ne peut fermer la balise.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


@router.get("/tools", response_class=HTMLResponse)
def tools_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            suite = "/tools" + (("?" + request.url.query) if request.url.query else "")
            return RedirectResponse(url="/?next=" + suite, status_code=302)
        raise
    droits = droits_outils(user)
    boot = {
        "droits": droits,
        "user": {"nom": user.get("nom") or "", "role": user.get("role") or ""},
        "org": APP_ORG_NAME,
        "version": APP_VERSION,
    }
    formulaires = ""
    if droits["formulaires"]:
        formulaires = "<script>\n" + FORMULAIRES_JS.replace("__ORG_NAME_JS__", json.dumps(APP_ORG_NAME)) + "\n</script>"
    html = (
        TOOLS_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__BOOT__", _json_script(boot))
        .replace("__FORMULAIRES__", formulaires)
    )
    for chemin in _ASSETS:
        html = html.replace('"' + chemin + '"', '"' + asset(chemin) + '"')
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# Assets versionnés par asset() : remplacés dans le gabarit à la volée.
_ASSETS = (
    "/static/mysifa_tools.css",
    "/static/mysifa_etiq_specifiques.css",
    "/static/mysifa_scanner.js",
    "/static/mysifa_tools_etiquettes.js",
    "/static/mysifa_etiq_specifiques.js",
    "/static/mysifa_etiq_editeur.js",
    "/static/mysifa_formulaire.js",
    "/static/mysifa_formulaire_editeur.js",
    "/static/mysifa_tools_traduction.js",
    "/static/mysifa_tools_calculs.js",
    "/static/mysifa_tools.js",
)

_NAV = [
    ("etiquettes", "Étiquettes",
     '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>'),
    ("formulaires", "Formulaires",
     '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>'),
    ("pdf", "Éditeur PDF",
     '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15l2 2 4-4"/>'),
    ("calculs", "Calculs bobine",
     '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v6"/>'),
    ("traduction", "Traducteur",
     '<path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/>'),
]


def _nav_html() -> str:
    lignes = []
    for cle, label, svg in _NAV:
        lignes.append(
            f'      <button type="button" class="nav-btn" data-outil="{cle}" onclick="toolsAller(\'{cle}\')">'
            f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{svg}</svg>{label}</button>'
        )
    return "\n".join(lignes)


TOOLS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17"><!-- hex-ok : barre système, avant le thème -->
<title>MyTools — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_sidebar.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_tools.css">
<link rel="stylesheet" href="/static/mysifa_etiq_specifiques.css">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_sidebar.js?v=__V_LABEL__"></script>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
<script>window.__MYTOOLS__ = __BOOT__;</script>
</head>
<body>
<div class="app">
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>

  <nav class="sidebar" id="sidebar">
    <div class="logo" onclick="toolsAller('accueil')" title="Menu MyTools">
      <div class="logo-brand">My<span>Tools</span></div>
      <div class="logo-sub">Boîte à outils</div>
    </div>
    <div class="msb-nav">
__NAV__
    </div>
    <!-- Pied commun (static/mysifa_sidebar.js), rempli au chargement. -->
    <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="MyTools" data-msb-version="__V_LABEL__"></div>
  </nav>

  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">MyTools</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Boîte à outils</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>
    <div class="content" id="content"></div>
  </main>
</div>
<div id="mroot"></div>
<div class="toast-wrap" id="toast-wrap"></div>

<script src="/static/mysifa_url.js?v=4"></script>
<script src="/static/mysifa_scanner.js"></script>
<script src="/static/mysifa_tools_etiquettes.js"></script>
<script src="/static/mysifa_etiq_specifiques.js"></script>
<script src="/static/mysifa_etiq_editeur.js"></script>
<script src="/static/mysifa_formulaire.js"></script>
<script src="/static/mysifa_formulaire_editeur.js"></script>
<script src="/static/mysifa_tools_traduction.js"></script>
<script src="/static/mysifa_tools_calculs.js"></script>
<script src="/static/mysifa_tools.js"></script>
__FORMULAIRES__
</body>
</html>
""".replace("__NAV__", _nav_html())
