"""MySifa — Réunions : l'espace commun et la page d'écoute.

Routes :
  /reunions          l'espace : réunions par type, compte-rendu, brief d'une
                     écoute à valider (static/mysifa_reunions_espace.js)
  /reunions/ecoute   enregistrer une réunion, page dépouillée pensée pour un
                     téléphone posé sur la table (static/mysifa_ecoute.js)

Accès : tout utilisateur connecté. Ce qu'il voit est filtré par l'API
(app/routers/reunions.py, rn.peut_voir) — la page ne filtre rien elle-même.

Jusqu'au 05/11/2026, /reunions redirigeait vers l'onglet Actions de MyProd
(/prod#reunions), qui reste en place pour le suivi des actions de l'atelier.

L'enregistrement a sa propre page parce que MySifa recharge la page à chaque
changement d'appli : un enregistrement lancé dans une page s'arrête quand on
la quitte. Le bouton flottant « Écouter » (static/mysifa_ecoute_fab.js) ouvre
donc cette page dans un onglet à part sur ordinateur, à la place sur
téléphone.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_ORG_NAME, APP_VERSION, ECOUTE_DUREE_MAX_H
from services.auth_service import effective_role, get_current_user

router = APIRouter()

_SANS_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _json_script(obj) -> str:
    # Sûr dans un <script> : aucune séquence « </ » ne peut fermer la balise.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _utilisateur(request: Request, retour: str):
    try:
        return get_current_user(request), None
    except HTTPException as e:
        if e.status_code == 401:
            suite = retour + (("?" + request.url.query) if request.url.query else "")
            return None, RedirectResponse(url="/?next=" + suite, status_code=302)
        raise


def _boot(user: dict) -> dict:
    return {
        "user": {"id": user.get("id"), "nom": user.get("nom") or "", "role": effective_role(user)},
        "org": APP_ORG_NAME,
        "version": APP_VERSION,
        "duree_max_h": ECOUTE_DUREE_MAX_H,
    }


@router.get("/reunions", response_class=HTMLResponse)
def reunions_page(request: Request):
    user, redirection = _utilisateur(request, "/reunions")
    if redirection:
        return redirection
    html = (ESPACE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
            .replace("__BOOT__", _json_script(_boot(user))))
    return HTMLResponse(content=html, headers=_SANS_CACHE)


@router.get("/reunions/ecoute", response_class=HTMLResponse)
def ecoute_page(request: Request):
    user, redirection = _utilisateur(request, "/reunions/ecoute")
    if redirection:
        return redirection
    html = (ECOUTE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
            .replace("__BOOT__", _json_script(_boot(user))))
    return HTMLResponse(content=html, headers=_SANS_CACHE)


_ICONE_MICRO = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                'stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2.5" width="6" height="11" rx="3"/>'
                '<path d="M5.5 10.5a6.5 6.5 0 0 0 13 0"/><line x1="12" y1="17" x2="12" y2="21"/>'
                '<line x1="8.5" y1="21" x2="15.5" y2="21"/></svg>')

_TETE = r"""<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17"><!-- hex-ok : barre système, avant le thème -->
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_sidebar.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_ia.css">
<link rel="stylesheet" href="/static/mysifa_reunions_espace.css?v=3">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_sidebar.js?v=__V_LABEL__"></script>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
<script>window.__REUNIONS__ = __BOOT__;</script>"""

_TOPBAR = r"""    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu" data-bulle="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Réunions</div>
        <div class="mobile-topbar-sub" id="mobile-sub">__SOUS_TITRE__</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil" data-bulle="Portail">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>"""

_SIDEBAR = r"""  <div class="sidebar-overlay" onclick="closeSidebar()"></div>
  <nav class="sidebar" id="sidebar">
    <div class="logo" onclick="location.href='/reunions'" data-bulle="Toutes les réunions" aria-label="Menu Réunions" title="Menu Réunions">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Réunions</div>
    </div>
    <div class="msb-nav" id="reu-nav">
      <a class="nav-btn reu-ecouter-btn" href="/reunions/ecoute" data-bulle="Enregistrer une réunion">""" + _ICONE_MICRO + r"""Écouter une réunion</a>
      <div class="nav-section-label msb-section"><span>Réunions</span></div>
      <div id="reu-nav-types"></div>
    </div>
    <!-- Pied commun (static/mysifa_sidebar.js), rempli au chargement. -->
    <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="Réunions" data-msb-version="__V_LABEL__"></div>
  </nav>"""

ESPACE_HTML = (r"""<!DOCTYPE html>
<html lang="fr">
<head>
<title>Réunions — MySifa</title>
""" + _TETE + r"""
</head>
<body>
<div class="app">
""" + _SIDEBAR + r"""
  <main class="main">
""" + _TOPBAR.replace("__SOUS_TITRE__", "Comptes-rendus") + r"""
    <div class="content" id="content"><div class="reu-chargement">Chargement…</div></div>
  </main>
</div>
<div id="mroot"></div>
<div class="toast-wrap" id="toast-wrap"></div>
<script src="/static/mysifa_url.js?v=5"></script>
<script src="/static/mysifa_reunions_espace.js?v=3"></script>
</body>
</html>
""")

ECOUTE_HTML = (r"""<!DOCTYPE html>
<html lang="fr">
<head>
<title>Écouter une réunion — MySifa</title>
""" + _TETE + r"""
</head>
<body class="reu-page-ecoute">
<div class="app">
""" + _SIDEBAR + r"""
  <main class="main">
""" + _TOPBAR.replace("__SOUS_TITRE__", "Écoute") + r"""
    <div class="content" id="content"><div class="reu-chargement">Chargement…</div></div>
  </main>
</div>
<div id="mroot"></div>
<div class="toast-wrap" id="toast-wrap"></div>
<script src="/static/mysifa_ecoute.js?v=2"></script>
</body>
</html>
""")
