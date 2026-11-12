"""MySifa — Mes notes (/note) : l'espace de prise de notes personnelle.

Chaque utilisateur y retrouve toutes ses notes, y compris celles posées en
post-it sur l'écran : arborescence de pages et sous-pages, recherche, éditeur
en blocs avec menu « / » (static/mysifa_notes_editeur.js, commun avec les
post-its), corbeille. Les notes sont personnelles : l'API (app/routers/postit.py)
filtre tout sur l'utilisateur connecté.

Partage : une note (et ses sous-pages) se partage avec des collègues, en
lecture ou en écriture ; plusieurs personnes y écrivent en même temps, chacun
voit où écrivent les autres.

Panneau d'actions rapides à droite (insérer un bloc, mettre en forme,
raccourcis) : affiché ou masqué par un bouton de la barre de la note ou
Cmd/Ctrl + \ ; préférence d'affichage gardée dans le navigateur, hors adresse.

Adresse : `?note=<id>` (note ouverte) et `&partage=1` (fenêtre de partage),
`?vue=corbeille`, `?nouvelle=1`
(crée une note puis l'ouvre — lien « Nouvelle note » de l'explorateur
MyQualité).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
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


@router.get("/note", response_class=HTMLResponse)
def notes_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            suite = "/note" + (("?" + request.url.query) if request.url.query else "")
            return RedirectResponse(url="/?next=" + suite, status_code=302)
        raise
    boot = {
        "user": {"id": user.get("id"), "nom": user.get("nom") or "", "role": effective_role(user)},
        "version": APP_VERSION,
    }
    html = (NOTES_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
            .replace("__BOOT__", _json_script(boot)))
    return HTMLResponse(content=html, headers=_SANS_CACHE)


@router.get("/notes")
def notes_alias():
    return RedirectResponse(url="/note", status_code=302)


_ICONE_PLUS = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
               'stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>')
_ICONE_ACCUEIL = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                  'stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/>'
                  '<rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>'
                  '<rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>')
_ICONE_CORBEILLE = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                    'stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/>'
                    '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>')

NOTES_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<title>Mes notes — MySifa</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17"><!-- hex-ok : barre système, avant le thème -->
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_sidebar.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_notes_editeur.css?v=2" data-nted="1">
<link rel="stylesheet" href="/static/mysifa_notes.css?v=5">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_sidebar.js?v=__V_LABEL__"></script>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
<script>window.__NOTES__ = __BOOT__;</script>
</head>
<body>
<div class="app">
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>
  <nav class="sidebar" id="sidebar">
    <div class="logo" onclick="location.href='/note'" title="Accueil de Mes notes" aria-label="Accueil de Mes notes">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Mes notes</div>
    </div>
    <div class="msb-nav">
      <button type="button" class="nav-btn nt-nouvelle" id="nt-nouvelle">""" + _ICONE_PLUS + r"""Nouvelle note</button>
      <div class="nt-recherche">
        <input type="search" id="nt-q" placeholder="Rechercher (titre, contenu)" autocomplete="off" spellcheck="false">
      </div>
      <button type="button" class="nav-btn" id="nt-nav-accueil">""" + _ICONE_ACCUEIL + r"""Toutes les notes</button>
      <div class="nav-section-label msb-section nt-racine" id="nt-racine" title="Déposer ici pour ranger à la racine"><span>Pages</span></div>
      <div class="nt-arbre" id="nt-arbre"></div>
      <div class="nav-section-label msb-section" id="nt-label-partage" hidden><span>Partagées avec moi</span></div>
      <div class="nt-arbre" id="nt-arbre-partage"></div>
      <button type="button" class="nav-btn nt-nav-corbeille" id="nt-nav-corbeille">""" + _ICONE_CORBEILLE + r"""Corbeille<span class="nt-nb" id="nt-nb-corbeille"></span></button>
    </div>
    <!-- Pied commun (static/mysifa_sidebar.js), rempli au chargement. -->
    <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="Mes notes" data-msb-version="__V_LABEL__"></div>
  </nav>
  <main class="main" id="nt-main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Mes notes</div>
        <div class="mobile-topbar-sub" id="mobile-sub"></div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>
    <div class="content nt-content" id="content"><div class="nt-chargement">Chargement…</div></div>
  </main>
  <!-- Actions rapides de la note ouverte (static/mysifa_notes.js), masquable. -->
  <aside class="nt-panneau" id="nt-panneau" aria-label="Actions rapides" hidden></aside>
</div>
<div id="mroot"></div>
<div class="toast-wrap" id="toast-wrap"></div>
<script src="/static/mysifa_url.js?v=5"></script>
<script src="/static/mysifa_notes_editeur.js?v=5"></script>
<script src="/static/mysifa_notes.js?v=5"></script>
</body>
</html>
"""
