"""MySifa — Coûts matières (UI standalone, routing client /pricing/*)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLES_PRICING_WRITE
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response

router = APIRouter()

_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


_ASSETS_PRICING = ("static/pricing_app.css", "static/pricing_app.js")
_EMPREINTE_CACHE: dict[str, str] = {}


def _empreinte_assets() -> str:
    """
    Empreinte courte du CSS et du JS du module.

    Sans elle, un correctif d'affichage peut être en production sans que
    personne ne le voie : le navigateur ressert son fichier en cache et on
    cherche le bug dans le code. La date de modification suffit — on ne relit
    pas le contenu à chaque page.
    """
    try:
        marques = []
        for chemin in _ASSETS_PRICING:
            f = Path(__file__).resolve().parents[2] / chemin
            marques.append(f"{chemin}:{f.stat().st_mtime_ns}")
        cle = "|".join(marques)
    except OSError:
        # Fichier illisible : on ne bloque pas la page, on renonce au cache.
        return APP_VERSION
    if cle not in _EMPREINTE_CACHE:
        _EMPREINTE_CACHE.clear()
        _EMPREINTE_CACHE[cle] = hashlib.sha1(cle.encode()).hexdigest()[:10]
    return _EMPREINTE_CACHE[cle]


def _pricing_html_response(request: Request) -> HTMLResponse:
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(
                url=f"/?next={request.url.path}",
                status_code=302,
            )
        raise
    if not user_has_app_access(user, "pricing"):
        return access_denied_response("Coûts matières")
    can_write = user.get("role") in ROLES_PRICING_WRITE
    html = (
        PRICING_SHELL.replace("__V__", f"v{APP_VERSION}")
        # Empreinte des fichiers statiques : elle change dès qu'on touche au CSS
        # ou au JS, donc le navigateur recharge au lieu de servir son cache.
        .replace("__ASSETS__", _empreinte_assets())
        .replace("__CAN_WRITE__", "true" if can_write else "false")
        .replace(
            "__USER__",
            json.dumps(
                {
                    "id": user.get("id"),
                    "nom": user.get("nom") or "",
                    "role": user.get("role") or "",
                },
                ensure_ascii=False,
            ),
        )
    )
    return HTMLResponse(content=html, headers=_NO_CACHE)


# Le routage se fait côté client (`parseRoute` dans pricing_app.js) : la
# navigation interne passe par `history.pushState`, le serveur n'est pas
# sollicité. Un rechargement forcé, un favori ou un lien collé, eux, arrivent
# bien ici — et toute URL sans route déclarée renvoyait un
# `{"detail":"Not Found"}` sur fond noir. Chaque route cliente doit donc avoir
# sa route serveur, qui rend la même coquille : `tests/test_pricing_routes.py`
# compare les deux listes.
@router.get("/pricing", response_class=HTMLResponse)
@router.get("/pricing/materials", response_class=HTMLResponse)
@router.get("/pricing/materials/new", response_class=HTMLResponse)
@router.get("/pricing/products", response_class=HTMLResponse)
@router.get("/pricing/products/new", response_class=HTMLResponse)
@router.get("/pricing/mystock", response_class=HTMLResponse)
@router.get("/pricing/mystock/produit/new", response_class=HTMLResponse)
@router.get("/pricing/fournisseurs", response_class=HTMLResponse)
@router.get("/pricing/settings", response_class=HTMLResponse)
def pricing_shell(request: Request):
    return _pricing_html_response(request)


@router.get("/pricing/materials/{material_id}", response_class=HTMLResponse)
def pricing_material_edit(request: Request, material_id: str):
    if material_id == "new" or not re.fullmatch(r"\d+", material_id):
        return RedirectResponse(url="/pricing/materials", status_code=302)
    return _pricing_html_response(request)


@router.get("/pricing/products/{product_id}", response_class=HTMLResponse)
def pricing_product_edit(request: Request, product_id: str):
    if product_id == "new" or not re.fullmatch(r"\d+", product_id):
        return RedirectResponse(url="/pricing/products", status_code=302)
    return _pricing_html_response(request)


# Déclarée AVANT `/pricing/mystock/{declinaison_id}` : FastAPI retient la
# première route qui correspond, et `{declinaison_id}` avalerait « produit ».
@router.get("/pricing/mystock/produit/{produit_id}", response_class=HTMLResponse)
def pricing_mystock_produit_edit(request: Request, produit_id: str):
    if produit_id == "new" or not re.fullmatch(r"\d+", produit_id):
        return RedirectResponse(url="/pricing/products", status_code=302)
    return _pricing_html_response(request)


@router.get("/pricing/mystock/{declinaison_id}", response_class=HTMLResponse)
def pricing_mystock_declinaison(request: Request, declinaison_id: str):
    if not re.fullmatch(r"\d+", declinaison_id):
        return RedirectResponse(url="/pricing/materials", status_code=302)
    return _pricing_html_response(request)


@router.get("/pricing/fournisseurs/{fournisseur_id}", response_class=HTMLResponse)
def pricing_fournisseur_tarif(request: Request, fournisseur_id: str):
    if not re.fullmatch(r"\d+", fournisseur_id):
        return RedirectResponse(url="/pricing/fournisseurs", status_code=302)
    return _pricing_html_response(request)


PRICING_SHELL = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#0a0e17">
<title>Coûts matières — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/pricing_app.css?v=__ASSETS__">
</head>
<body class="has-topbar mysifa-app-pricing">
<div id="toast-root"></div>
<div id="modal-root"></div>
<div class="layout" id="app">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-logo">
      <div class="logo-brand">My<span>Coûts</span></div>
      <div class="logo-sub">by SIFA</div>
    </div>
    <nav class="sidebar-nav" id="sidebar-nav"></nav>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" id="btn-portal">← Retour <span class="wm">My<span>Sifa</span></span></button>
      <div class="user-chip" id="user-chip" title="Mon profil"></div>
      <button type="button" class="theme-btn" id="theme-btn" aria-label="Basculer le thème">
        <span class="theme-ico" id="theme-ico"></span>
        <span class="theme-label" id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" id="logout-btn">
        <span id="logout-ico"></span>
        <span>Déconnexion</span>
      </button>
      <div class="version">__V__</div>
    </div>
  </aside>
  <div class="sidebar-overlay" id="sidebar-overlay"></div>
  <main class="main">
    <header class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" id="mobile-menu-btn" aria-label="Menu"></button>
      <div class="mobile-topbar-titles">
        <div class="mobile-topbar-title" id="mobile-title">Coûts matières</div>
        <div class="mobile-topbar-sub" id="mobile-sub"></div>
      </div>
      <a href="/" class="mobile-home-btn" title="Portail" id="mobile-home-btn" aria-label="Portail"></a>
    </header>
    <div class="content" id="content">
      <div class="loading-state" id="loading-state">
        <div class="spinner"></div>
        <span>Chargement…</span>
      </div>
    </div>
  </main>
</div>
<script>window.__PRICING__={canWrite:__CAN_WRITE__,user:__USER__};</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/pricing_app.js?v=__ASSETS__" defer></script>
<script src="/static/mysifa_impersonate.js"></script>
</body>
</html>"""
