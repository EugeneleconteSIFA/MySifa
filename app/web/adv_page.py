"""MySifa — ADV : le tableau de bord du service administration des ventes.

Route : /adv
  ?onglet=commandes (défaut)  le carnet RVGI, une ligne par ligne de commande,
                              stock MyStock et chaîne BAT → Prod → Stock →
                              Prépa → Départ
  ?onglet=prepa               les préparations à faire, dans l'ordre

Accès : ROLES_ADV pour le carnet, ROLES_ADV_PREPA (avec logistique et
expédition) pour l'onglet Prépa. Une personne qui n'a que la Prépa arrive
directement dessus. Le rendu est dans static/mysifa_adv.js.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import (ADV_ETAPES, ADV_ETATS, ADV_PREPA_HORIZON_JOURS, ADV_PREPA_STATUTS, ADV_REPIQUAGE_STATUTS,
                    APP_ORG_NAME, APP_VERSION, ROLES_ADV, ROLES_ADV_PREPA, ROLES_ERP)
from services.auth_service import effective_role, get_current_user
from app.services import adv_mise_en_forme as mef

router = APIRouter()

_SANS_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _json_script(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


@router.get("/adv", response_class=HTMLResponse)
def adv_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            suite = "/adv" + (("?" + request.url.query) if request.url.query else "")
            return RedirectResponse(url="/?next=" + suite, status_code=302)
        raise
    role = effective_role(user)
    if role not in ROLES_ADV_PREPA:
        return RedirectResponse(url="/", status_code=302)
    boot = {
        "user": {"id": user.get("id"), "nom": user.get("nom") or "", "role": role},
        "org": APP_ORG_NAME,
        "droits": {"adv": role in ROLES_ADV, "prepa": True},
        "etapes": [{"cle": k, "label": v} for k, v in ADV_ETAPES],
        "etats": [{"cle": k, "label": v} for k, v in ADV_ETATS],
        "statuts_prepa": [{"cle": k, "label": v} for k, v in ADV_PREPA_STATUTS],
        "statuts_repiquage": [{"cle": k, "label": v} for k, v in ADV_REPIQUAGE_STATUTS],
        "horizon": ADV_PREPA_HORIZON_JOURS,
        "mef": mef.referentiel(),
        # Le bouton « Mettre à jour » du miroir RVGI est ouvert aux rôles de l'ERP.
        "rvgi_demande": role in ROLES_ERP,
    }
    # Pour la logistique et l'expédition, l'appli s'appelle « Prépa » : elles
    # n'en voient que l'onglet des préparations.
    prepa_seule = role not in ROLES_ADV
    boot["appli"] = "Prépa" if prepa_seule else "ADV"
    html = (PAGE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
            .replace("__APPLI__", boot["appli"])
            .replace("__SECTION__", "Préparations" if prepa_seule else "Administration des ventes")
            .replace("__ACCUEIL__", "/adv?onglet=prepa" if prepa_seule else "/adv")
            .replace("__BOOT__", _json_script(boot)))
    return HTMLResponse(content=html, headers=_SANS_CACHE)


_ICONE_CARNET = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" '
                 'width="16" height="18" rx="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" '
                 'y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="12" y2="16"/></svg>')
_ICONE_PREPA = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l9-4 9 4-9 '
                '4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/><line x1="12" y1="11" x2="12" y2="21"/></svg>')

PAGE_HTML = (r"""<!DOCTYPE html>
<html lang="fr">
<head>
<title>__APPLI__ — MySifa</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17"><!-- hex-ok : barre système, avant le thème -->
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_sidebar.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_ia.css">
<link rel="stylesheet" href="/static/mysifa_adv.css?v=25">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_sidebar.js?v=__V_LABEL__"></script>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
<script>window.__ADV__ = __BOOT__;</script>
</head>
<body>
<div class="app">
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>
  <nav class="sidebar" id="sidebar">
    <div class="logo" onclick="location.href='__ACCUEIL__'" title="Menu __APPLI__" aria-label="Menu __APPLI__">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">__APPLI__</div>
    </div>
    <div class="msb-nav" id="adv-nav">
      <div class="nav-section-label msb-section"><span>__SECTION__</span></div>
      <button type="button" class="nav-btn" data-onglet="commandes">""" + _ICONE_CARNET + r"""<span>Commandes</span><span class="adv-nav-nb" id="adv-nb-commandes"></span></button>
      <button type="button" class="nav-btn" data-onglet="prepa">""" + _ICONE_PREPA + r"""<span>Prépa</span><span class="adv-nav-nb" id="adv-nb-prepa"></span></button>
    </div>
    <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="__APPLI__" data-msb-version="__V_LABEL__"></div>
  </nav>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">__APPLI__</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Commandes</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>
    <div class="content" id="content"><div class="adv-chargement">Chargement…</div></div>
  </main>
</div>
<div id="mroot"></div>
<div class="toast-wrap" id="toast-wrap"></div>
<script src="/static/mysifa_url.js?v=5"></script>
<script src="/static/mysifa_rvgi_synchro.js?v=1"></script>
<script src="/static/mysifa_adv.js?v=25"></script>
</body>
</html>
""")
