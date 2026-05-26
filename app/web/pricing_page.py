"""MySifa — Coûts matières (UI standalone, routing client /pricing/*)."""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLES_ADMIN
from services.auth_service import get_current_user, user_has_app_access
from app.web.access_denied import access_denied_response

router = APIRouter()

_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


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
    can_write = user.get("role") in ROLES_ADMIN
    html = (
        PRICING_SHELL.replace("__V__", f"v{APP_VERSION}")
        .replace("__CAN_WRITE__", "true" if can_write else "false")
        .replace(
            "__USER__",
            json.dumps(
                {"nom": user.get("nom") or "", "role": user.get("role") or ""},
                ensure_ascii=False,
            ),
        )
    )
    return HTMLResponse(content=html, headers=_NO_CACHE)


@router.get("/pricing", response_class=HTMLResponse)
@router.get("/pricing/materials", response_class=HTMLResponse)
@router.get("/pricing/materials/new", response_class=HTMLResponse)
@router.get("/pricing/products", response_class=HTMLResponse)
@router.get("/pricing/products/new", response_class=HTMLResponse)
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
<link rel="stylesheet" href="/static/pricing_app.css">
</head>
<body>
<div id="toast-root"></div>
<div id="modal-root"></div>
<div class="layout" id="app">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-logo">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Coûts matières</div>
    </div>
    <nav class="sidebar-nav" id="sidebar-nav"></nav>
    <div class="sidebar-bottom">
      <div class="user-chip" id="user-chip"></div>
      <button type="button" class="theme-btn" id="theme-btn">Thème</button>
      <button type="button" class="logout-btn" id="logout-btn">Déconnexion</button>
      <div class="version">__V__</div>
    </div>
  </aside>
  <div class="sidebar-overlay" id="sidebar-overlay"></div>
  <main class="main">
    <header class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" id="mobile-menu-btn" aria-label="Menu">☰</button>
      <div class="mobile-topbar-titles">
        <div class="mobile-topbar-title" id="mobile-title">Coûts matières</div>
        <div class="mobile-topbar-sub" id="mobile-sub"></div>
      </div>
      <a href="/" class="mobile-home-btn" title="Portail">⌂</a>
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
<script src="/static/pricing_app.js" defer></script>
</body>
</html>"""
