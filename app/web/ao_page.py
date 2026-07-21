"""MySifa — Appels d'offre (page interne /ao)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, BASE_URL
from app.services.auth_service import get_current_user
from app.web.access_denied import access_denied_response
from app.web.ao_produit_form import AO_PRODUIT_FORM_CSS, AO_PRODUIT_FORM_JS

router = APIRouter()

_AO_ROLES = frozenset({"superadmin", "direction"})


@router.get("/ao", response_class=HTMLResponse)
def ao_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/ao", status_code=302)
        raise
    if user.get("role") not in _AO_ROLES:
        return access_denied_response("Appels d'offre")
    html = AO_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    html = html.replace("__BASE_URL__", json.dumps(BASE_URL))
    html = html.replace("__USER_JSON__", json.dumps({
        "id": user.get("id"),
        "nom": user.get("nom"),
        "email": user.get("email"),
        "role": user.get("role"),
        "app_access": user.get("app_access"),
    }))
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


AO_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Appels d'offre — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/support_widget.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--success:#34d399;--warn:#fbbf24;--danger:#f87171;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.1);--success:#059669;--warn:#d97706;--danger:#dc2626;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}
.app{display:flex;height:100vh;width:100%;overflow:hidden}
.sidebar{width:220px;flex-shrink:0;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:24px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;text-align:left;margin-bottom:2px;transition:background .15s,color .15s}
.nav-btn svg{flex-shrink:0}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-section-label{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);font-weight:600;padding:14px 12px 4px;user-select:none;pointer-events:none}
.nav-btn-sub{padding-left:28px;font-size:12px}
.sidebar-nav{padding:4px 0;flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch}
.sidebar-nav::-webkit-scrollbar{width:4px}
.sidebar-nav::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding:12px 8px;border-top:1px solid var(--border);flex-shrink:0;background:var(--card)}
.support-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.support-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.support-ico{display:inline-flex;align-items:center;justify-content:center}
.back-mysifa{font-weight:400!important;color:var(--text2)!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;width:100%;cursor:pointer;font-family:inherit}
.theme-btn:hover,.logout-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}
.mobile-topbar{display:none;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border);background:var(--card);flex-shrink:0}
.mobile-menu-btn,.mobile-home-btn{width:40px;height:40px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);cursor:pointer;display:flex;align-items:center;justify-content:center}
.mobile-topbar-title{font-size:15px;font-weight:700}
.mobile-topbar-sub{font-size:11px;color:var(--muted)}
.scroll-area{flex:1;overflow:auto;padding:20px 24px 32px}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:900px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .18s ease;height:100vh}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-topbar{display:flex}
}
.page-hdr{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:20px;flex-wrap:wrap}
.page-hdr h1{font-size:20px;font-weight:800}
.btn{padding:10px 18px;border-radius:10px;border:none;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.btn:hover{filter:brightness(1.05)}
.btn-accent{background:var(--accent);color:var(--bg)}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn-danger{background:var(--danger);color:#fff}
.btn-sm{padding:6px 12px;font-size:12px}
.btn-icon{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;vertical-align:middle;transition:all .15s}
.btn-icon:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.btn-icon.btn-del-ao:hover{background:rgba(248,113,113,.12);color:var(--danger);border-color:var(--danger)}
.ao-actions-cell{text-align:right;white-space:nowrap}
.ao-actions-cell .btn{vertical-align:middle}
.ao-params-panel{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:6px 12px;margin-left:auto;box-shadow:0 1px 2px rgba(0,0,0,.04);display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px}
.ao-params-panel h3{margin:0;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--accent)}
.ao-params-panel .app-group{display:flex;flex-direction:column;gap:2px}
.ao-params-panel .app-group .app-row{margin:0;display:flex;align-items:center;gap:6px}
.ao-params-panel .app-group .app-row label{flex:0 0 auto;font-size:11px}
.ao-params-panel .app-group .app-row input[type=number]{width:80px;flex:0 0 auto;padding:4px 8px;font-size:12px}
.ao-params-panel .app-group .app-help{margin:0;font-size:10px;line-height:1.3;font-style:italic;color:var(--muted)}
@media(max-width:820px){.ao-params-panel{margin-left:0;width:100%}}
.ao-params-panel .app-row{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.ao-params-panel .app-row:last-child{margin-bottom:0}
.ao-params-panel label{flex:0 0 130px;font-size:12px;font-weight:600;color:var(--text2)}
.ao-params-panel input[type=number]{flex:1;padding:6px 10px;font-size:13px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit}
.ao-params-panel .app-suffix{font-size:12px;color:var(--muted);min-width:20px}
.ao-params-panel .app-help{font-size:11px;color:var(--muted);line-height:1.4;margin-top:6px;font-style:italic}
.ao-list-ref-link{color:var(--accent);text-decoration:none;font-weight:700}
.ao-list-ref-link:hover{text-decoration:underline}
.filter-tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.filter-tab{padding:8px 14px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.filter-tab.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.data-table{width:100%;border-collapse:collapse;font-size:13px}
.data-table th,.data-table td{padding:12px 10px;border-bottom:1px solid var(--border);text-align:left}
.data-table th{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.3px}
.badge-muted{background:rgba(148,163,184,.15);color:var(--muted)}
.badge-warn{background:rgba(251,191,36,.15);color:var(--warn)}
.badge-success{background:rgba(52,211,153,.15);color:var(--success)}
.empty-state{padding:48px 24px;text-align:center;color:var(--muted)}
.empty-state strong{display:block;color:var(--text2);font-size:15px;margin-bottom:8px}
.detail-tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap;align-items:center}
.detail-tab{padding:8px 14px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.detail-tab.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.breadcrumb{font-size:12px;color:var(--muted);margin-bottom:12px}
.breadcrumb a{color:var(--accent);cursor:pointer;text-decoration:none}
.detail-hdr{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:8px}
.detail-hdr h2{font-size:18px;font-weight:800}
.detail-hdr .nav-pager{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.detail-hdr .nav-pager .nav-pos{padding:0 6px;font-weight:600;color:var(--text2);white-space:nowrap}
.nav-pager .btn-icon{width:32px;height:32px}
.nav-pager .btn-icon[disabled]{opacity:.35;cursor:not-allowed;pointer-events:none}
.detail-meta{font-size:13px;color:var(--text2);line-height:1.6}
.detail-actions{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
input,select,textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit}
input:focus,select:focus,textarea:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
.field{margin-bottom:14px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:600px){.form-row{grid-template-columns:1fr}}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:500;display:flex;align-items:center;justify-content:center;padding:20px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;max-width:480px;width:100%;max-height:90vh;overflow:auto}
.modal h3{font-size:16px;font-weight:700;margin-bottom:16px}
.modal.modal-wide{max-width:560px}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}
.comp-table{width:100%;border-collapse:collapse;font-size:12px}
.comp-table th,.comp-table td{padding:10px 8px;border:1px solid var(--border);text-align:center;vertical-align:middle}
.comp-table th{background:var(--bg);font-size:10px;text-transform:uppercase;color:var(--muted);white-space:nowrap}
.comp-table td.ref{text-align:left;font-weight:600}
.comp-table td.txt-left{text-align:left}
.comp-cell-best{background:var(--accent-bg);color:var(--accent);font-weight:700}
.comp-table input[type=number],.comp-table select{font-size:12px;padding:6px 8px;min-width:0}
.comp-table .inp-coef{max-width:72px}
.comp-table .inp-dev-devis{max-width:80px}
.msg-list{display:flex;flex-direction:column;gap:10px;max-height:360px;overflow-y:auto;margin-bottom:16px}
.bubble{max-width:85%;padding:12px 14px;border-radius:12px;font-size:13px;line-height:1.5}
.bubble.interne{align-self:flex-end;margin-left:auto;background:var(--accent-bg);border:1px solid var(--accent)}
.bubble.fournisseur{align-self:flex-start;background:var(--card);border:1px solid var(--border)}
.bubble .meta{font-size:11px;color:var(--muted);margin-bottom:4px}
#toast{position:fixed;bottom:max(20px,env(safe-area-inset-bottom,0px));right:max(20px,env(safe-area-inset-right,0px));padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;z-index:12050;display:none;max-width:min(420px,calc(100vw - 32px));box-shadow:0 8px 32px rgba(0,0,0,.45);pointer-events:none}
#toast.show{display:block;pointer-events:auto}
#toast.success{background:var(--success);color:var(--bg)}
#toast.danger{background:var(--danger);color:#fff}
#toast.info{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent)}
#toast.warn{background:rgba(251,191,36,.2);color:var(--warn);border:1px solid var(--warn)}
.prod-list-table .prod-ref-cell{font-family:ui-monospace,monospace;font-size:14px;font-weight:700;color:var(--text)}
.prod-list-table .prod-info-cell{font-size:12px;color:var(--text2);line-height:1.5}
.prod-list-table .prod-info-cell strong{color:var(--text);font-weight:700}
.prod-list-table .prod-actions-cell{text-align:right;white-space:nowrap}
""" + AO_PRODUIT_FORM_CSS + r"""
</style>
</head>
<body>
<div class="app" id="root"></div>
<div id="mroot"></div>
<div id="toast"></div>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/support_widget.js"></script>
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<script>window.__MYSIFA_APP__='ao';</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_cmdk.js"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=11"></script>
<script src="/static/chat_widget_v2.js?v=8"></script>
<script>
const BASE_URL = __BASE_URL__;
const S = {
  section: 'ao',
  view: 'list',
  tab: 'lignes',
  aos: [],
  filtre: 'tous',
  ao: null,
  detail: null,
  comparaison: null,
  messages: [],
  messages_fourni: null,
  polling: null,
  sidebarOpen: false,
  user: __USER_JSON__,
  modal: null,
  modalData: {},
  carnet: [],
  carnetClients: [],
  produits: [],
  produitsSearch: '',
  produitView: 'list',
  produitForm: null,
  matieres: {},
  nonLus: {}
};

const ROLE_LABELS = {direction:'Direction',administration:'Administration',commercial:'Commercial',superadmin:'Super admin'};

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}
function escAttr(s) { return escHtml(s).replace(/"/g, '&quot;'); }

function icon(name, size) {
  size = size || 16;
  const p = {
    clipboard: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
    wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    package: '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
    calculator: '<rect x="6" y="2.5" width="12" height="19" rx="2"/><line x1="8" y1="7" x2="16" y2="7"/>',
    truck: '<path d="M3 7h11v10H3z"/><path d="M14 10h4l3 3v4h-7z"/><circle cx="7.5" cy="17" r="2"/><circle cx="17.5" cy="17" r="2"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    menu: '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    home: '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    sun: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    'arrow-right': '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    mail: '<path d="M4 6h16v12H4z"/><path d="M4 7l8 6 8-6"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/>',
    grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    'building-2': '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>'
  };
  return '<svg width="'+size+'" height="'+size+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">'+(p[name]||'')+'</svg>';
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show ' + (type || 'info');
  clearTimeout(showToast._tm);
  showToast._tm = setTimeout(() => { t.className = ''; }, 3500);
}

async function api(path, options) {
  const r = await fetch(path, { credentials: 'include', ...options });
  if (!r.ok) {
    let d = 'Erreur ' + r.status;
    try { const j = await r.json(); d = j.detail || d; } catch(e) {}
    const err = new Error(typeof d === 'string' ? d : JSON.stringify(d));
    err.status = r.status;
    throw err;
  }
  if (r.status === 204) return null;
  return r.json();
}

function redirectToLogin() {
  location.href = '/?next=/ao';
}

function statutBadge(s) {
  const m = {brouillon:['badge-muted','Brouillon'],envoyee:['badge-warn','Envoyée'],cloturee:['badge-success','Clôturée']};
  const x = m[s] || ['badge-muted', s || ''];
  return '<span class="badge '+x[0]+'">'+escHtml(x[1])+'</span>';
}
function fourniBadge(s) {
  const m = {invite:['badge-muted','Invité'],ouvert:['badge-warn','Ouvert'],repondu:['badge-success','Répondu'],decline:['badge-muted','Décliné']};
  const x = m[s] || ['badge-muted', s || ''];
  return '<span class="badge '+x[0]+'">'+escHtml(x[1])+'</span>';
}
function formatEur(n) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toLocaleString('fr-FR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' €';
}
function formatMoney(n, devise) {
  if (n == null || isNaN(n)) return '—';
  const d = (devise || 'EUR').toUpperCase();
  const sym = d === 'USD' ? '$' : '€';
  return Number(n).toLocaleString('fr-FR', {minimumFractionDigits:2, maximumFractionDigits:4}) + ' ' + sym;
}
function formatUniteQuot(u) {
  const m = {mille: 'Au mille', bobine: 'Par bobine'};
  return m[(u || '').toLowerCase()] || (u || '—');
}
function formatInt(n) {
  if (n == null || n === '' || isNaN(n)) return '—';
  return Number(n).toLocaleString('fr-FR', {maximumFractionDigits:0});
}

function buildAoSidebarNavStructure() {
  const sec = S.section;
  return [
    {kind:'btn', section:'ao', icon:'clipboard', label:'Appel d\'offre'},
    {kind:'btn', section:'produits', icon:'package', label:'Produits'},
  ].map(n => (n.kind === 'btn' ? {...n, active: sec === n.section} : n));
}

function aoMobileTitle() {
  const m = {
    ao: S.view === 'detail' && S.ao ? [S.ao.reference, 'Appel d\'offre'] : ['Appels d\'offre', 'Appel d\'offre'],
    produits: ['Produits', 'Référentiel'],
  };
  const x = m[S.section] || ['MyAO', 'Appels d\'offre'];
  return {title: x[0], sub: x[1]};
}

function goToAoSection(section) {
  if (S.section === section) { closeSidebar(); return; }
  if (S.polling) { clearInterval(S.polling); S.polling = null; }
  S.section = section;
  if (section !== 'produits') {
    S.produitView = 'list';
    S.produitForm = null;
  }
  if (section !== 'ao') {
    S.view = 'list';
    S.ao = null;
    S.detail = null;
  }
  closeSidebar();
  render();
}

function openSupport() {
  if (window.MySifaSupport && typeof window.MySifaSupport.open === 'function') {
    window.MySifaSupport.open({
      user: S.user,
      page: 'MyAO',
      notify: (m, t) => showToast(m, t === 'error' ? 'danger' : (t || 'info')),
      api
    });
  } else {
    showToast('Support indisponible.', 'danger');
  }
}

function renderAoSidebarNavHtml() {
  let html = '';
  buildAoSidebarNavStructure().forEach(n => {
    if (n.kind === 'sep') {
      html += '<div class="nav-section-label">'+escHtml(n.label)+'</div>';
      return;
    }
    const cls = 'nav-btn'+(n.sub?' nav-btn-sub':'')+(n.active?' active':'');
    html += '<button type="button" class="'+cls+'" data-section="'+escAttr(n.section)+'">'+icon(n.icon,16)+'<span>'+escHtml(n.label)+'</span></button>';
  });
  return html;
}

function renderUserChipHtml() {
  if (!S.user) return '';
  if (window.MySifaUserChip && typeof window.MySifaUserChip.innerHtml === 'function') {
    return '<div class="user-chip" id="user-chip" style="cursor:pointer" title="Modifier mon profil">'+
      window.MySifaUserChip.innerHtml(S.user, {roleLabels: ROLE_LABELS})+'</div>';
  }
  return '<div class="user-chip" id="user-chip" style="cursor:pointer" title="Modifier mon profil">'+
    '<div class="uc-name">'+escHtml(S.user.nom)+'</div>'+
    '<div class="uc-role">'+escHtml(ROLE_LABELS[S.user.role]||S.user.role)+'</div></div>';
}

function renderSectionPlaceholder(title, hint) {
  return '<div class="page-hdr"><h1>'+escHtml(title)+'</h1></div>'+
    '<div class="card empty-state"><strong>'+escHtml(title)+'</strong>'+escHtml(hint)+'</div>';
}

function langueBadge(l) {
  const lang = (l === 'en') ? 'en' : 'fr';
  const lbl = lang === 'en' ? 'EN' : 'FR';
  return '<span style="display:inline-block;padding:2px 8px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;letter-spacing:.5px">'+lbl+'</span>';
}

function renderCarnet() {
  const list = S.carnet || [];
  let rows = '';
  list.forEach(c => {
    rows += '<tr><td>'+escHtml(c.societe||'—')+'</td><td>'+escHtml(c.nom)+'</td><td>'+escHtml(c.email||'—')+'</td><td>'+escHtml(c.adresse||'—')+'</td><td>'+langueBadge(c.langue)+'</td><td>'+
      '<button class="btn btn-ghost btn-sm btn-edit-carnet" data-id="'+c.id+'">Modifier</button> '+
      '<button class="btn btn-ghost btn-sm btn-del-carnet" data-id="'+c.id+'">Supprimer</button></td></tr>';
  });
  const table = list.length
    ? '<div class="card"><table class="data-table"><thead><tr><th>Société</th><th>Nom</th><th>Email</th><th>Adresse</th><th>Langue</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>'
    : '<div class="card empty-state"><strong>Aucun fournisseur dans le carnet.</strong></div>';
  return '<div class="page-hdr"><h1>Carnet fournisseurs</h1>'+
    '<button class="btn btn-accent" type="button" id="btn-add-carnet">'+icon('plus',14)+' Ajouter</button></div>'+table;
}

function renderCarnetClients() {
  const list = S.carnetClients || [];
  let rows = '';
  list.forEach(c => {
    rows += '<tr><td>'+escHtml(c.nom)+'</td><td>'+escHtml(c.notes||'—')+'</td><td>'+
      '<button class="btn btn-ghost btn-sm btn-edit-carnet-client" data-id="'+c.id+'">Modifier</button> '+
      '<button class="btn btn-ghost btn-sm btn-del-carnet-client" data-id="'+c.id+'">Supprimer</button></td></tr>';
  });
  const table = list.length
    ? '<div class="card"><table class="data-table"><thead><tr><th>Nom</th><th>Notes</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>'
    : '<div class="card empty-state"><strong>Aucun client dans le carnet.</strong></div>';
  return '<div class="page-hdr"><h1>Carnet clients</h1>'+
    '<button class="btn btn-accent" type="button" id="btn-add-carnet-client">'+icon('plus',14)+' Ajouter</button></div>'+table;
}

function filteredProduits() {
  const q = (S.produitsSearch || '').trim().toLowerCase();
  if (!q) return S.produits || [];
  return (S.produits || []).filter(p => {
    return (p.ref || '').toLowerCase().includes(q);
  });
}

function formatProduitImpressions(p) {
  const f = (p && p.fiche) || {};
  if (!f.impressions) {
    return '<span style="color:var(--muted)">Non</span>';
  }
  const imp = f.impressions_detail || {};
  const recto = parseInt(imp.recto, 10) || 0;
  const verso = parseInt(imp.verso, 10) || 0;
  if (!recto && !verso) {
    return '<span style="color:var(--muted)">—</span>';
  }
  const parts = [];
  if (recto) parts.push('<strong>'+recto+'</strong> recto');
  if (verso) parts.push('<strong>'+verso+'</strong> verso');
  if (imp.aplat) {
    const pct = (imp.aplat_pourcent !== '' && imp.aplat_pourcent != null) ? (' '+imp.aplat_pourcent+'%') : '';
    parts.push('<span style="color:var(--muted)">aplat'+escHtml(pct)+'</span>');
  }
  return parts.join(' · ');
}

function formatProduitConditionnement(p) {
  const f = (p && p.fiche) || {};
  const bob = f.bobines || {};
  const cond = f.conditionnement || {};
  const cart = cond.carton || {};
  const pal = cond.palette || {};
  const nbEt = parseInt(bob.nb_etiquettes, 10);
  const diam = parseFloat(bob.diametre_bobine);
  const bpc = parseInt(cart.bobines_carton, 10);
  const cpp = parseInt(pal.cartons_palette, 10);
  const parts = [];
  if (!isNaN(diam) && diam > 0) parts.push('Ø '+formatInt(diam)+' mm');
  if (!isNaN(nbEt) && nbEt > 0) parts.push('<strong>'+formatInt(nbEt)+'</strong> étiq./bobine');
  if (!isNaN(bpc) && bpc > 0) parts.push('<strong>'+formatInt(bpc)+'</strong> bob./carton');
  if (!isNaN(cpp) && cpp > 0) parts.push('<strong>'+formatInt(cpp)+'</strong> cartons/palette');
  if (!parts.length) return '<span style="color:var(--muted)">—</span>';
  return parts.join(' · ');
}

function matiereNameById(cat, id) {
  if (!id) return '<span style="color:var(--muted)">\u2014</span>';
  const list = (S.matieres && S.matieres[cat]) || [];
  const m = list.find(x => String(x.id) === String(id));
  if (!m) return '#' + id;
  const ref = m.reference || '';
  const des = m.designation || '';
  return escHtml(ref + (des ? (ref ? ' \u2014 ' : '') + des : ''));
}

function renderProduitsRows() {
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const el = document.getElementById('produits-list');
  if (!el) return;
  const q = (S.produitsSearch || '').trim();
  const list = filteredProduits();
  if (!list.length) {
    el.innerHTML = q
      ? '<div class="empty-state" style="padding:32px 16px"><strong>Aucun résultat pour « '+escHtml(q)+' »</strong></div>'
      : '<div class="empty-state" style="padding:32px 16px"><strong>Aucun produit dans le catalogue.</strong></div>';
  } else {
    let rows = '';
    list.forEach(p => {
      const mat = (p.fiche && p.fiche.matiere) || {};
      const clientTxt = p.client_nom ? escHtml(p.client_nom) : '<span style="color:var(--muted)">\u2014</span>';
      const frontalTxt = matiereNameById('frontal', mat.frontal_id);
      const adhesifTxt = matiereNameById('adhesif', mat.adhesif_id);
      rows += '<tr>'+
        '<td class="prod-ref-cell">'+escHtml(p.ref)+'</td>'+
        '<td>'+clientTxt+'</td>'+
        '<td>'+frontalTxt+'</td>'+
        '<td>'+adhesifTxt+'</td>'+
        '<td class="prod-info-cell">'+formatProduitImpressions(p)+'</td>'+
        '<td class="prod-info-cell">'+formatProduitConditionnement(p)+'</td>'+
        '<td class="prod-actions-cell">'+
        '<button class="btn btn-ghost btn-sm btn-edit-produit" data-id="'+p.id+'">Modifier</button> '+
        '<button class="btn btn-ghost btn-sm btn-dup-produit" data-id="'+p.id+'" data-ref="'+escAttr(p.ref||'')+'">Dupliquer</button> '+
        '<button class="btn btn-ghost btn-sm btn-export-produit" data-id="'+p.id+'">PDF</button> '+
        '<button class="btn btn-ghost btn-sm btn-del-produit" data-id="'+p.id+'">Supprimer</button></td></tr>';
    });
    el.innerHTML = '<table class="data-table prod-list-table">'+
      '<thead><tr>'+
      '<th>Référence</th>'+
      '<th>Client</th>'+
      '<th>Frontal</th>'+
      '<th>Adhésif</th>'+
      '<th>Impressions</th>'+
      '<th>Conditionnement bobine</th>'+
      '<th></th>'+
      '</tr></thead><tbody>'+rows+'</tbody></table>';
    el.querySelectorAll('.btn-edit-produit').forEach(b => {
      b.addEventListener('click', () => {
        const p = (S.produits||[]).find(x => String(x.id) === String(b.dataset.id));
        if (p) openProduitForm(p);
      });
    });
    el.querySelectorAll('.btn-dup-produit').forEach(b => {
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          const dup = await api('/api/ao/produits/'+b.dataset.id+'/dupliquer', {method:'POST'});
          showToast('Produit dupliqué — '+dup.ref, 'success');
          await loadProduits();
          renderProduitsRows();
        } catch(e) {
          showToast(e.message || 'Erreur à la duplication.', 'danger');
        } finally {
          b.disabled = false;
        }
      });
    });
    el.querySelectorAll('.btn-export-produit').forEach(b => {
      b.addEventListener('click', () => window.open('/api/ao/produits/'+b.dataset.id+'/export', '_blank'));
    });
    el.querySelectorAll('.btn-del-produit').forEach(b => {
      b.addEventListener('click', async () => {
        if (!confirm('Supprimer ce produit du catalogue ?')) return;
        try {
          await api('/api/ao/produits/'+b.dataset.id, {method:'DELETE'});
          showToast('Produit supprimé.', 'success');
          await loadProduits();
          renderProduitsRows();
        } catch(e) { showToast(e.message, 'danger'); }
      });
    });
  }
  if (focusId) {
    const foc = document.getElementById(focusId);
    if (foc) {
      foc.focus();
      if (caretStart != null) try { foc.setSelectionRange(caretStart, caretEnd); } catch(e) {}
    }
  }
}

function renderProduits() {
  return '<div class="page-hdr"><h1>Catalogue produits</h1>'+
    '<button class="btn btn-accent" type="button" id="btn-add-produit">'+icon('plus',14)+' Ajouter un produit</button></div>'+
    '<div class="card">'+
    '<input type="search" id="produits-search" placeholder="Rechercher une référence…" value="'+escAttr(S.produitsSearch||'')+'" style="width:100%;margin-bottom:14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px">'+
    '<div id="produits-list"></div></div>';
}

function bindProduitsEvents() {
  renderProduitsRows();
  const search = document.getElementById('produits-search');
  search?.addEventListener('input', () => {
    S.produitsSearch = search.value;
    renderProduitsRows();
  });
  search?.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      S.produitsSearch = '';
      search.value = '';
      renderProduitsRows();
      search.focus();
    }
  });
  document.getElementById('btn-add-produit')?.addEventListener('click', () => openProduitForm(null));
}

function bindCarnetEvents() {
  document.getElementById('btn-add-carnet')?.addEventListener('click', () => openModalCarnetEntry(null));
  document.querySelectorAll('.btn-edit-carnet').forEach(b => {
    b.addEventListener('click', () => {
      const c = (S.carnet||[]).find(x => String(x.id) === String(b.dataset.id));
      if (c) openModalCarnetEntry(c);
    });
  });
  document.querySelectorAll('.btn-del-carnet').forEach(b => {
    b.addEventListener('click', async () => {
      if (!confirm('Supprimer cette entrée du carnet ?')) return;
      try {
        await api('/api/ao/carnet-fournisseurs/'+b.dataset.id, {method:'DELETE'});
        showToast('Entrée supprimée.', 'success');
        await loadCarnet();
        render();
      } catch(e) { showToast(e.message, 'danger'); }
    });
  });
}

function bindCarnetClientsEvents() {
  document.getElementById('btn-add-carnet-client')?.addEventListener('click', () => openModalCarnetClientEntry(null));
  document.querySelectorAll('.btn-edit-carnet-client').forEach(b => {
    b.addEventListener('click', () => {
      const c = (S.carnetClients||[]).find(x => String(x.id) === String(b.dataset.id));
      if (c) openModalCarnetClientEntry(c);
    });
  });
  document.querySelectorAll('.btn-del-carnet-client').forEach(b => {
    b.addEventListener('click', async () => {
      if (!confirm('Supprimer cette entrée du carnet ?')) return;
      try {
        await api('/api/ao/carnet-clients/'+b.dataset.id, {method:'DELETE'});
        showToast('Entrée supprimée.', 'success');
        await loadCarnetClients();
        render();
      } catch(e) { showToast(e.message, 'danger'); }
    });
  });
}

function toggleSidebar() {
  S.sidebarOpen = !S.sidebarOpen;
  document.body.classList.toggle('sb-open', S.sidebarOpen);
}
function closeSidebar() { S.sidebarOpen = false; document.body.classList.remove('sb-open'); }

async function loadList() {
  S.aos = await api('/api/ao');
}

async function loadCarnet() {
  S.carnet = await api('/api/ao/carnet-fournisseurs');
}

async function loadCarnetClients() {
  S.carnetClients = await api('/api/ao/carnet-clients');
}

async function loadProduits() {
  S.produits = await api('/api/ao/produits');
}

async function loadDetail(id) {
  S.detail = await api('/api/ao/' + id);
  S.ao = S.detail.ao;
  try {
    S.nonLus = await api('/api/ao/' + id + '/non-lus');
  } catch(e) {
    S.nonLus = {};
  }
  if (S.tab === 'comparaison') await loadComparaison(id);
  if (S.tab === 'messages' && S.messages_fourni) await loadMessages(id, S.messages_fourni);
}

async function loadComparaison(id) {
  S.comparaison = await api('/api/ao/' + id + '/comparaison');
}

async function loadMessages(aoId, fourniId) {
  S.messages = await api('/api/ao/' + aoId + '/fournisseurs/' + fourniId + '/messages');
}

function filteredAos() {
  const f = S.filtre;
  if (f === 'tous') return S.aos;
  return S.aos.filter(a => a.statut === f);
}

function openDetail(id) {
  S.section = 'ao';
  S.view = 'detail';
  S.tab = 'lignes';
  S.messages_fourni = null;
  S.comparaison = null;
  loadDetail(id).then(() => render());
}

function backToList() {
  if (S.polling) { clearInterval(S.polling); S.polling = null; }
  S.view = 'list';
  S.ao = null;
  S.detail = null;
  loadList().then(() => render());
}

function setTab(tab) {
  S.tab = tab;
  if (S.view === 'detail' && S.ao) {
    const id = S.ao.id;
    if (tab === 'comparaison') loadComparaison(id).then(() => render());
    else if (tab === 'messages') {
      const fournis = S.detail.fournisseurs || [];
      if (!S.messages_fourni && fournis.length) S.messages_fourni = fournis[0].id;
      if (S.messages_fourni) {
        loadMessages(id, S.messages_fourni).then(async () => {
          try {
            S.nonLus = await api('/api/ao/' + id + '/non-lus');
          } catch(e) {
            S.nonLus = {};
          }
          startMsgPolling();
          render();
        });
      } else render();
    } else {
      if (S.polling) { clearInterval(S.polling); S.polling = null; }
      render();
    }
  } else render();
}

function startMsgPolling() {
  if (S.polling) clearInterval(S.polling);
  S.polling = setInterval(() => {
    if (S.view === 'detail' && S.tab === 'messages' && S.ao && S.messages_fourni) {
      loadMessages(S.ao.id, S.messages_fourni).then(() => {
        const el = document.querySelector('.msg-list');
        if (el) {
          const st = el.scrollTop;
          renderMessagerieContent(el.parentElement);
          const el2 = document.querySelector('.msg-list');
          if (el2) el2.scrollTop = st;
        }
      }).catch(() => {});
    }
  }, 30000);
}

function closeModal() { S.modal = null; S.modalData = {}; document.getElementById('mroot').innerHTML = ''; }

function openModalCreate() {
  S.modal = 'create';
  S.modalData = {titre:'',description:'',date_limite:'',responsable_email: S.user?.email || ''};
  renderModal();
}
function openModalLigne(edit) {
  S.modal = 'ligne';
  S.modalData = edit ? {...edit} : {ref_produit:'',designation:'',quantite:'',unite:'étiquettes',notes:''};
  renderModal();
}
function openModalFourni() {
  S.modal = 'fourni';
  S.modalData = {nom_fournisseur:'',email_contact:''};
  renderModal();
}
function openModalCarnetEntry(edit) {
  S.modal = 'carnet-entry';
  S.modalData = edit ? {...edit} : {nom:'', societe:'', email:'', adresse:'', notes:'', langue:'fr'};
  renderModal();
}
function openModalCarnetClientEntry(edit) {
  S.modal = 'carnet-client-entry';
  S.modalData = edit ? {...edit} : {nom:'', notes:''};
  renderModal();
}
function openModalConfirmEnvoi(n) {
  S.modal = 'confirm-envoi';
  S.modalData = {n};
  renderModal();
}
function openModalConfirmDelete(id, ref, statut) {
  S.modal = 'confirm-delete-ao';
  S.modalData = {id, ref, statut};
  renderModal();
}
async function openModalDuplicate(id, ref, titre) {
  S.modal = 'duplicate-ao';
  S.modalData = {id, ref, titre, with_fournisseurs: true, with_pieces_jointes: false, fournisseurs: [], _loading: true};
  renderModal();
  try {
    const det = await api('/api/ao/' + id);
    S.modalData.fournisseurs = (det && det.fournisseurs) || [];
    // Par defaut : tous coches
    S.modalData.selectedFourniIds = new Set(S.modalData.fournisseurs.map(f => f.id));
    S.modalData._loading = false;
    renderModal();
  } catch (e) {
    S.modalData._loading = false;
    S.modalData.fournisseurs = [];
    renderModal();
  }
}
function openModalPickClient(onPick) {
  S.modal = 'pick-client';
  S.modalData = {search: '', results: [], loading: true, onPick};
  renderModal();
  pickClientFetch('');
}
function openModalCreateClient(onCreated) {
  S.modal = 'create-client';
  S.modalData = {
    tab: 'identite', onCreated,
    raison_sociale:'', code:'', numero:'', etat:'Normal', siret:'', tva:'',
    adresse1:'', adresse2:'', cp:'', ville:'', pays:'', code_pays:'',
    telephone:'', email:'', contact_nom:'', contact_fonction:'', contact_email:'', contact_tel:'',
    representant:'', notes:''
  };
  renderModal();
}
async function pickClientFetch(q) {
  if (!S.modalData) return;
  S.modalData.search = q || '';
  S.modalData.loading = true;
  pickClientRenderList();
  try {
    const params = new URLSearchParams({search: q || '', limit: '40'});
    const res = await api('/api/ao/picker/clients?' + params.toString());
    if (S.modal === 'pick-client') {
      S.modalData.results = res || [];
      S.modalData.loading = false;
      pickClientRenderList();
    }
  } catch(e) {
    if (S.modal === 'pick-client') {
      S.modalData.loading = false;
      S.modalData.results = [];
      pickClientRenderList();
      showToast(e.message || 'Erreur de recherche.', 'danger');
    }
  }
}
function pickClientRenderList() {
  const el = document.getElementById('m-pick-cli-list');
  if (!el) return;
  if (S.modalData.loading && !(S.modalData.results || []).length) {
    el.innerHTML = '<div class="pf-pick-empty">Chargement…</div>';
    return;
  }
  const list = S.modalData.results || [];
  if (!list.length) {
    const q = (S.modalData.search || '').trim();
    el.innerHTML = q
      ? '<div class="pf-pick-empty">Aucun résultat pour « '+escHtml(q)+' »</div>'
      : '<div class="pf-pick-empty">Aucun client dans le référentiel.</div>';
    return;
  }
  let h = '';
  list.forEach(c => {
    const meta = [c.code, c.ville, c.pays].filter(Boolean).map(escHtml).join(' · ');
    h += '<div class="pf-pick-item" data-id="'+c.id+'">'+
      '<div class="pi-main">'+escHtml(c.raison_sociale || 'Sans raison sociale')+'</div>'+
      (meta ? '<div class="pi-meta">'+meta+'</div>' : '')+
      '</div>';
  });
  el.innerHTML = h;
  el.querySelectorAll('.pf-pick-item').forEach(it => {
    it.addEventListener('click', () => {
      const id = it.dataset.id;
      const cli = (S.modalData.results || []).find(x => String(x.id) === String(id));
      const cb = S.modalData.onPick;
      closeModal();
      if (cli && typeof cb === 'function') cb(cli);
    });
  });
}

function renderModal() {
  const m = document.getElementById('mroot');
  m.innerHTML = '';
  if (!S.modal) return;
  const ov = document.createElement('div');
  ov.className = 'modal-overlay';
  ov.onclick = e => { if (e.target === ov) closeModal(); };
  const box = document.createElement('div');
  box.className = 'modal';
  if (S.modal === 'create') {
    box.innerHTML = '<h3>Nouvel appel d\'offre</h3>'+
      '<div class="field"><label>Titre</label><input id="m-titre" value="'+escAttr(S.modalData.titre)+'"></div>'+
      '<div class="field"><label>Description</label><textarea id="m-desc" rows="3">'+escHtml(S.modalData.description)+'</textarea></div>'+
      '<div class="form-row"><div class="field"><label>Date limite</label><input type="date" id="m-limite" value="'+escAttr(S.modalData.date_limite)+'"></div>'+
      '<div class="field"><label>Email responsable</label><input type="email" id="m-email" value="'+escAttr(S.modalData.responsable_email)+'"></div></div>'+
      '<div class="modal-actions"><button class="btn btn-ghost" type="button" id="m-cancel">Annuler</button><button class="btn btn-accent" type="button" id="m-ok">Créer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const titre = document.getElementById('m-titre').value.trim();
      const email = document.getElementById('m-email').value.trim();
      if (!titre || !email) { showToast('Titre et email responsable obligatoires.', 'danger'); return; }
      try {
        const ao = await api('/api/ao', {method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({titre, description: document.getElementById('m-desc').value.trim() || null,
            date_limite: document.getElementById('m-limite').value || null, responsable_email: email})});
        closeModal();
        showToast('Appel d\'offre créé.', 'success');
        openDetail(ao.id);
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'ligne') {
    const editId = S.modalData.id;
    let prodOpts = '<option value="">— Saisie manuelle —</option>';
    (S.produits||[]).forEach(p => {
      prodOpts += '<option value="'+p.id+'">'+escHtml(p.ref)+' — '+escHtml(p.designation)+'</option>';
    });
    const saveCatHtml = editId ? '' :
      '<label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer;margin-bottom:14px">'+
      '<input type="checkbox" id="m-save-produit"> Enregistrer dans le catalogue</label>';
    box.innerHTML = '<h3>'+(editId?'Modifier':'Ajouter')+' une ligne</h3>'+
      '<div class="field"><label>Produit du catalogue</label><select id="m-produit-pick">'+prodOpts+'</select></div>'+
      '<div class="field"><label>Réf. produit</label><input id="m-ref" value="'+escAttr(S.modalData.ref_produit||'')+'"></div>'+
      '<div class="field"><label>Désignation</label><input id="m-des" value="'+escAttr(S.modalData.designation||'')+'"></div>'+
      '<div class="form-row"><div class="field"><label>Quantité d\'étiquettes</label><input type="number" step="1" min="0" id="m-qte" value="'+escAttr(S.modalData.quantite)+'"></div>'+
      '<div class="field"><label>Unité (interne)</label><input id="m-unite" value="'+escAttr(S.modalData.unite||'étiquettes')+'"></div></div>'+
      '<div class="field"><label>Notes</label><input id="m-notes" value="'+escAttr(S.modalData.notes||'')+'"></div>'+
      saveCatHtml+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Enregistrer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    const pickEl = document.getElementById('m-produit-pick');
    const refEl = document.getElementById('m-ref');
    const desEl = document.getElementById('m-des');
    const uniteEl = document.getElementById('m-unite');
    const notesEl = document.getElementById('m-notes');
    const saveCb = document.getElementById('m-save-produit');
    pickEl.onchange = () => {
      const id = pickEl.value;
      if (id) {
        const p = (S.produits||[]).find(x => String(x.id) === String(id));
        if (p) {
          refEl.value = p.ref || '';
          desEl.value = p.designation || '';
          uniteEl.value = p.unite || 'étiquettes';
          if (p.notes) notesEl.value = p.notes;
        }
        if (saveCb) { saveCb.checked = false; saveCb.disabled = true; }
      } else if (saveCb) {
        saveCb.disabled = false;
      }
    };
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const ref = refEl.value.trim();
      const designation = desEl.value.trim();
      if (!ref || !designation) { showToast('Référence et désignation obligatoires.', 'danger'); return; }
      const body = {ref_produit: ref, designation,
        quantite: parseFloat(document.getElementById('m-qte').value), unite: uniteEl.value.trim(),
        notes: notesEl.value.trim() || null};
      try {
        const path = '/api/ao/'+S.ao.id+'/lignes'+(editId?'/'+editId:'');
        await api(path, {method: editId?'PUT':'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        if (!editId && !pickEl.value && saveCb && saveCb.checked) {
          await api('/api/ao/produits', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ref, designation, fiche: defaultProduitFiche()})});
          await loadProduits();
        }
        closeModal(); showToast('Ligne enregistrée.', 'success');
        await loadDetail(S.ao.id); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'fourni') {
    box.className = 'modal modal-wide';
    let carnetOpts = '<option value="">— Saisie manuelle —</option>';
    (S.carnet||[]).forEach(c => {
      const lbl = (c.societe ? escHtml(c.societe)+' — ' : '')+escHtml(c.nom);
      carnetOpts += '<option value="'+c.id+'">'+lbl+'</option>';
    });
    box.innerHTML = '<h3>Ajouter un fournisseur</h3>'+
      '<div class="field"><label>Sélectionner depuis le carnet</label>'+
      '<select id="m-carnet-pick">'+carnetOpts+'</select></div>'+
      '<div id="m-fourni-form">'+
      '<div class="field"><label>Société</label><input id="m-societe"></div>'+
      '<div class="field"><label>Nom</label><input id="m-nom"></div>'+
      '<div class="field"><label>Email</label><input type="email" id="m-mail"></div>'+
      '<div class="field"><label>Langue de l\'email d\'invitation</label>'+
      '<select id="m-langue"><option value="fr">Français</option><option value="en">English</option></select></div>'+
      '<div class="field"><label>Adresse</label><textarea id="m-adresse" rows="2"></textarea></div></div>'+
      '<label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer;margin-bottom:14px">'+
      '<input type="checkbox" id="m-save-carnet"> Enregistrer dans le carnet</label>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Ajouter</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    const pickEl = document.getElementById('m-carnet-pick');
    const societeEl = document.getElementById('m-societe');
    const nomEl = document.getElementById('m-nom');
    const mailEl = document.getElementById('m-mail');
    const adresseEl = document.getElementById('m-adresse');
    const langueEl = document.getElementById('m-langue');
    const saveCb = document.getElementById('m-save-carnet');
    pickEl.onchange = () => {
      const id = pickEl.value;
      if (id) {
        const c = (S.carnet||[]).find(x => String(x.id) === String(id));
        if (c) {
          societeEl.value = c.societe || '';
          nomEl.value = c.nom || '';
          mailEl.value = c.email || '';
          adresseEl.value = c.adresse || '';
          langueEl.value = (c.langue === 'en') ? 'en' : 'fr';
        }
        saveCb.checked = false;
        saveCb.disabled = true;
      } else {
        saveCb.disabled = false;
      }
    };
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const nom = nomEl.value.trim();
      const email = mailEl.value.trim();
      const langue = (langueEl.value === 'en') ? 'en' : 'fr';
      if (!nom || !email) { showToast('Nom et email obligatoires.', 'danger'); return; }
      const label = societeEl.value.trim() || nom;
      try {
        await api('/api/ao/'+S.ao.id+'/fournisseurs', {method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({nom_fournisseur: label, email_contact: email, langue})});
        const manual = !pickEl.value;
        if (manual && saveCb.checked) {
          await api('/api/ao/carnet-fournisseurs', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
              nom,
              email: email,
              societe: societeEl.value.trim() || null,
              adresse: adresseEl.value.trim() || null,
              langue
            })});
          await loadCarnet();
        }
        closeModal(); showToast('Fournisseur ajouté.', 'success');
        await loadDetail(S.ao.id); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'carnet-entry') {
    const editId = S.modalData.id;
    const curLang = (S.modalData.langue === 'en') ? 'en' : 'fr';
    box.className = 'modal modal-wide';
    box.innerHTML = '<h3>'+(editId?'Modifier':'Ajouter')+' au carnet</h3>'+
      '<div class="field"><label>Société</label><input id="m-c-societe" value="'+escAttr(S.modalData.societe||'')+'"></div>'+
      '<div class="field"><label>Nom</label><input id="m-c-nom" value="'+escAttr(S.modalData.nom||'')+'"></div>'+
      '<div class="field"><label>Email</label><input type="email" id="m-c-email" value="'+escAttr(S.modalData.email||'')+'"></div>'+
      '<div class="field"><label>Langue de l\'email d\'invitation</label>'+
      '<select id="m-c-langue">'+
        '<option value="fr"'+(curLang==='fr'?' selected':'')+'>Français</option>'+
        '<option value="en"'+(curLang==='en'?' selected':'')+'>English</option>'+
      '</select></div>'+
      '<div class="field"><label>Adresse</label><textarea id="m-c-adresse" rows="2">'+escHtml(S.modalData.adresse||'')+'</textarea></div>'+
      '<div class="field"><label>Notes</label><textarea id="m-c-notes" rows="2">'+escHtml(S.modalData.notes||'')+'</textarea></div>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Enregistrer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const body = {
        societe: document.getElementById('m-c-societe').value.trim() || null,
        nom: document.getElementById('m-c-nom').value.trim(),
        email: document.getElementById('m-c-email').value.trim() || null,
        adresse: document.getElementById('m-c-adresse').value.trim() || null,
        notes: document.getElementById('m-c-notes').value.trim() || null,
        langue: (document.getElementById('m-c-langue').value === 'en') ? 'en' : 'fr'
      };
      if (!body.nom) { showToast('Nom obligatoire.', 'danger'); return; }
      try {
        if (editId) {
          await api('/api/ao/carnet-fournisseurs/'+editId, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        } else {
          await api('/api/ao/carnet-fournisseurs', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        }
        closeModal(); showToast('Carnet enregistré.', 'success');
        await loadCarnet(); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'carnet-client-entry') {
    const editId = S.modalData.id;
    box.innerHTML = '<h3>'+(editId?'Modifier':'Ajouter')+' au carnet</h3>'+
      '<div class="field"><label>Nom</label><input id="m-cc-nom" value="'+escAttr(S.modalData.nom||'')+'"></div>'+
      '<div class="field"><label>Notes</label><textarea id="m-cc-notes" rows="2">'+escHtml(S.modalData.notes||'')+'</textarea></div>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Enregistrer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const body = {
        nom: document.getElementById('m-cc-nom').value.trim(),
        notes: document.getElementById('m-cc-notes').value.trim() || null
      };
      if (!body.nom) { showToast('Nom obligatoire.', 'danger'); return; }
      try {
        if (editId) {
          await api('/api/ao/carnet-clients/'+editId, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        } else {
          await api('/api/ao/carnet-clients', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        }
        closeModal(); showToast('Carnet enregistré.', 'success');
        await loadCarnetClients(); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'confirm-envoi') {
    box.innerHTML = '<h3>Confirmer l\'envoi</h3><p style="font-size:14px;color:var(--text2);line-height:1.6">Cette action enverra les emails aux '+S.modalData.n+' fournisseur(s). Confirmer ?</p>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Envoyer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      try {
        const r = await api('/api/ao/'+S.ao.id+'/envoyer', {method:'POST'});
        closeModal();
        showToast('Envoyés : '+r.envoyes+(r.erreurs?' — Erreurs : '+r.erreurs:''), r.erreurs?'warn':'success');
        await loadDetail(S.ao.id); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'confirm-delete-ao') {
    const st = S.modalData.statut;
    const stLabel = st === 'brouillon' ? 'Brouillon' : st === 'envoyee' ? 'Envoyée' : st === 'cloturee' ? 'Clôturée' : st;
    const warn = (st === 'envoyee' || st === 'cloturee')
      ? '<div style="background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.3);border-radius:8px;padding:12px;margin-bottom:14px;font-size:12px;color:var(--danger);line-height:1.5">'+
        '<strong>Attention</strong> — cet appel d\'offre est au statut « '+escHtml(stLabel)+' ». La suppression effacera aussi tous les fournisseurs, leurs réponses, messages et documents associés. Cette action est irréversible.</div>'
      : '';
    box.innerHTML = '<h3>Supprimer l\'appel d\'offre</h3>'+
      '<p style="font-size:14px;color:var(--text2);line-height:1.6;margin-bottom:14px">Supprimer <strong>'+escHtml(S.modalData.ref)+'</strong> ?</p>'+
      warn+
      '<div class="modal-actions"><button class="btn btn-ghost" type="button" id="m-cancel">Annuler</button><button class="btn btn-danger" type="button" id="m-ok">Supprimer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      try {
        await api('/api/ao/'+S.modalData.id, {method:'DELETE'});
        closeModal();
        showToast('Appel d\'offre supprimé.', 'success');
        await loadList(); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'duplicate-ao') {
    const md = S.modalData;
    const defaultTitre = (md.titre || '') + ' (copie)';
    const fournis = md.fournisseurs || [];
    const selected = md.selectedFourniIds || new Set();
    let fourniSection = '';
    if (md._loading) {
      fourniSection = '<p class="sub" style="color:var(--muted);font-size:12px">Chargement des fournisseurs…</p>';
    } else if (fournis.length === 0) {
      fourniSection = '<p class="sub" style="color:var(--muted);font-size:12px">Aucun fournisseur invite sur l\'AO source.</p>';
    } else {
      fourniSection = '<label style="font-size:12px;color:var(--text2);font-weight:600;margin-bottom:6px;display:block">Fournisseurs a recopier</label>' +
        '<div style="max-height:200px;overflow:auto;border:1px solid var(--border);border-radius:8px;padding:6px 8px;margin-bottom:14px">' +
        fournis.map(f => 
          '<label style="display:flex;align-items:center;gap:8px;padding:3px 0;cursor:pointer;font-size:12px">' +
          '<input type="checkbox" class="m-dup-fid" value="' + f.id + '"' + (selected.has(f.id) ? ' checked' : '') + '>' +
          escHtml(f.nom_fournisseur) + ' <span style="color:var(--muted)">· ' + escHtml(f.email_contact || '') + '</span>' +
          '</label>'
        ).join('') +
        '</div>';
    }
    box.innerHTML = '<h3>Dupliquer l\'appel d\'offre</h3>'+
      '<p style="font-size:13px;color:var(--muted);line-height:1.5;margin-bottom:14px">Source : <strong style="color:var(--text2)">'+escHtml(md.ref)+'</strong></p>'+
      '<div class="field"><label>Titre du nouvel appel d\'offre</label>'+
      '<input id="m-dup-titre" value="'+escAttr(defaultTitre)+'"></div>'+
      fourniSection +
      '<label style="font-size:12px;color:var(--text2);display:flex;align-items:center;gap:8px;cursor:pointer;margin-bottom:14px">'+
      '<input type="checkbox" id="m-dup-pj"> Recopier les documents joints</label>'+
      '<p style="font-size:11px;color:var(--muted);line-height:1.5;margin-bottom:14px">Le nouvel appel d\'offre sera cree en <strong style="color:var(--text2)">brouillon</strong>. Les reponses fournisseurs ne sont jamais recopiees.</p>'+
      '<div class="modal-actions"><button class="btn btn-ghost" type="button" id="m-cancel">Annuler</button><button class="btn btn-accent" type="button" id="m-ok">Dupliquer et ouvrir</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const titre = document.getElementById('m-dup-titre').value.trim();
      if (!titre) { showToast('Titre obligatoire.', 'danger'); return; }
      const selected_ids = Array.from(document.querySelectorAll('.m-dup-fid:checked')).map(cb => parseInt(cb.value, 10));
      const body = {
        titre,
        with_fournisseurs: selected_ids.length > 0,
        fournisseur_ids: fournis.length ? selected_ids : null,
        with_pieces_jointes: document.getElementById('m-dup-pj').checked,
      };
      try {
        const ao = await api('/api/ao/'+md.id+'/dupliquer',
          {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        closeModal();
        showToast('Appel d\'offre dupliqué — '+ao.reference, 'success');
        await loadList();
        openDetail(ao.id);
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'pick-client') {
    box.className = 'modal modal-wide';
    box.innerHTML = '<h3>Sélectionner un client</h3>'+
      '<div class="field"><input type="search" id="m-pick-cli-search" placeholder="Rechercher (raison sociale, code, ville, email…)" autocomplete="off"></div>'+
      '<div class="pf-pick-list" id="m-pick-cli-list"><div class="pf-pick-empty">Chargement…</div></div>'+
      '<div class="modal-actions" style="justify-content:space-between">'+
      '<button class="btn btn-ghost" type="button" id="m-pick-cli-create">+ Nouveau client</button>'+
      '<button class="btn btn-ghost" type="button" id="m-cancel">Annuler</button>'+
      '</div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    pickClientRenderList();
    const inp = document.getElementById('m-pick-cli-search');
    let tm = null;
    inp.addEventListener('input', () => {
      clearTimeout(tm);
      tm = setTimeout(() => pickClientFetch(inp.value), 180);
    });
    inp.addEventListener('keydown', e => {
      if (e.key === 'Escape') { inp.value=''; pickClientFetch(''); }
    });
    requestAnimationFrame(() => { inp.focus(); });
    document.getElementById('m-pick-cli-create').onclick = () => {
      const onPick = S.modalData.onPick;
      openModalCreateClient((cli) => {
        if (typeof onPick === 'function') onPick(cli);
      });
    };
  } else if (S.modal === 'create-client') {
    box.className = 'modal modal-wide';
    const d = S.modalData;
    const tab = d.tab || 'identite';
    const tabs = [
      ['identite','Identité'],
      ['adresse','Adresse'],
      ['contact','Contact'],
      ['notes','Notes']
    ];
    const tabsHtml = '<div class="pf-tabs-cli">'+tabs.map(t =>
      '<button type="button" data-tab="'+t[0]+'" class="'+(tab===t[0]?'active':'')+'">'+escHtml(t[1])+'</button>'
    ).join('')+'</div>';

    let body = '';
    if (tab === 'identite') {
      body = '<div class="pf-cli-grid">'+
        '<div class="full"><label>Raison sociale *</label><input id="m-cli-raison" value="'+escAttr(d.raison_sociale||'')+'"></div>'+
        '<div><label>Code</label><input id="m-cli-code" value="'+escAttr(d.code||'')+'"></div>'+
        '<div><label>N°</label><input type="number" id="m-cli-numero" value="'+escAttr(d.numero||'')+'"></div>'+
        '<div><label>État</label><select id="m-cli-etat">'+
          ['Normal','Bloqué','Inactif'].map(s => '<option value="'+s+'"'+(d.etat===s?' selected':'')+'>'+s+'</option>').join('')+
          '</select></div>'+
        '<div><label>SIRET</label><input id="m-cli-siret" value="'+escAttr(d.siret||'')+'"></div>'+
        '<div class="full"><label>N° TVA</label><input id="m-cli-tva" value="'+escAttr(d.tva||'')+'"></div>'+
        '</div>';
    } else if (tab === 'adresse') {
      body = '<div class="pf-cli-grid">'+
        '<div class="full"><label>Adresse 1</label><input id="m-cli-adresse1" value="'+escAttr(d.adresse1||'')+'"></div>'+
        '<div class="full"><label>Adresse 2</label><input id="m-cli-adresse2" value="'+escAttr(d.adresse2||'')+'"></div>'+
        '<div><label>Code postal</label><input id="m-cli-cp" value="'+escAttr(d.cp||'')+'"></div>'+
        '<div><label>Ville</label><input id="m-cli-ville" value="'+escAttr(d.ville||'')+'"></div>'+
        '<div><label>Code pays</label><input id="m-cli-code-pays" maxlength="3" value="'+escAttr(d.code_pays||'')+'"></div>'+
        '<div><label>Pays</label><input id="m-cli-pays" value="'+escAttr(d.pays||'')+'"></div>'+
        '</div>';
    } else if (tab === 'contact') {
      body = '<div class="pf-cli-grid">'+
        '<div><label>Téléphone</label><input id="m-cli-tel" value="'+escAttr(d.telephone||'')+'"></div>'+
        '<div><label>Email</label><input type="email" id="m-cli-email" value="'+escAttr(d.email||'')+'"></div>'+
        '<div class="full" style="font-size:11px;color:var(--muted);margin-top:4px">Contact principal</div>'+
        '<div><label>Nom du contact</label><input id="m-cli-contact-nom" value="'+escAttr(d.contact_nom||'')+'"></div>'+
        '<div><label>Fonction</label><input id="m-cli-contact-fonction" value="'+escAttr(d.contact_fonction||'')+'"></div>'+
        '<div><label>Email contact</label><input type="email" id="m-cli-contact-email" value="'+escAttr(d.contact_email||'')+'"></div>'+
        '<div><label>Téléphone contact</label><input id="m-cli-contact-tel" value="'+escAttr(d.contact_tel||'')+'"></div>'+
        '</div>';
    } else if (tab === 'notes') {
      body = '<div class="pf-cli-grid">'+
        '<div class="full"><label>Représentant</label><input id="m-cli-rep" value="'+escAttr(d.representant||'')+'"></div>'+
        '<div class="full"><label>Notes internes</label><textarea id="m-cli-notes" rows="6" placeholder="Remarques, conditions particulières…">'+escHtml(d.notes||'')+'</textarea></div>'+
        '</div>';
    }

    box.innerHTML = '<h3>Nouveau client</h3>'+tabsHtml+body+
      '<div class="modal-actions">'+
      '<button class="btn btn-ghost" type="button" id="m-cancel">Annuler</button>'+
      '<button class="btn btn-accent" type="button" id="m-ok">Créer le client</button>'+
      '</div>';
    ov.appendChild(box); m.appendChild(ov);

    function persistCurrentTab() {
      const get = id => document.getElementById(id)?.value;
      if (tab === 'identite') {
        d.raison_sociale = get('m-cli-raison')||'';
        d.code = get('m-cli-code')||'';
        d.numero = get('m-cli-numero')||'';
        d.etat = get('m-cli-etat')||'Normal';
        d.siret = get('m-cli-siret')||'';
        d.tva = get('m-cli-tva')||'';
      } else if (tab === 'adresse') {
        d.adresse1 = get('m-cli-adresse1')||'';
        d.adresse2 = get('m-cli-adresse2')||'';
        d.cp = get('m-cli-cp')||'';
        d.ville = get('m-cli-ville')||'';
        d.code_pays = get('m-cli-code-pays')||'';
        d.pays = get('m-cli-pays')||'';
      } else if (tab === 'contact') {
        d.telephone = get('m-cli-tel')||'';
        d.email = get('m-cli-email')||'';
        d.contact_nom = get('m-cli-contact-nom')||'';
        d.contact_fonction = get('m-cli-contact-fonction')||'';
        d.contact_email = get('m-cli-contact-email')||'';
        d.contact_tel = get('m-cli-contact-tel')||'';
      } else if (tab === 'notes') {
        d.representant = get('m-cli-rep')||'';
        d.notes = get('m-cli-notes')||'';
      }
    }

    document.querySelectorAll('.pf-tabs-cli button').forEach(b => {
      b.addEventListener('click', () => {
        persistCurrentTab();
        d.tab = b.dataset.tab;
        renderModal();
      });
    });
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      persistCurrentTab();
      if (!(d.raison_sociale||'').trim()) {
        d.tab = 'identite';
        renderModal();
        showToast('Raison sociale obligatoire.', 'danger');
        return;
      }
      const body = {
        raison_sociale: d.raison_sociale.trim(),
        code: d.code?.trim() || null,
        numero: d.numero ? Number(d.numero) : null,
        etat: d.etat || 'Normal',
        siret: d.siret?.trim() || null,
        tva: d.tva?.trim() || null,
        adresse1: d.adresse1?.trim() || null,
        adresse2: d.adresse2?.trim() || null,
        cp: d.cp?.trim() || null,
        ville: d.ville?.trim() || null,
        pays: d.pays?.trim() || null,
        code_pays: d.code_pays?.trim() || null,
        telephone: d.telephone?.trim() || null,
        email: d.email?.trim() || null,
        contact_nom: d.contact_nom?.trim() || null,
        contact_fonction: d.contact_fonction?.trim() || null,
        contact_email: d.contact_email?.trim() || null,
        contact_tel: d.contact_tel?.trim() || null,
        representant: d.representant?.trim() || null,
        notes: d.notes?.trim() || null,
      };
      try {
        const cli = await api('/api/ao/picker/clients', {
          method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
        });
        const cb = d.onCreated;
        closeModal();
        showToast('Client créé.', 'success');
        if (typeof cb === 'function') cb(cli);
      } catch(e) { showToast(e.message || 'Erreur à la création.', 'danger'); }
    };
  }
}

function renderList() {
  const list = filteredAos();
  let rows = '';
  list.forEach(a => {
    const ref = escAttr(a.reference||'');
    const titre = escAttr(a.titre||'');
    const cliTxt = a.clients ? escHtml(a.clients) : '<span style="color:var(--muted)">—</span>';
    const refsTxt = a.refs_produits ? escHtml(a.refs_produits) : '<span style="color:var(--muted)">—</span>';
    const actions =
      '<button class="btn btn-ghost btn-sm btn-view" data-id="'+a.id+'">Voir</button> '+
      '<button class="btn-icon btn-dup-ao" data-id="'+a.id+'" data-ref="'+ref+'" data-titre="'+titre+'" title="Dupliquer">'+icon('copy',14)+'</button> '+
      '<button class="btn-icon btn-del-ao" data-id="'+a.id+'" data-ref="'+ref+'" data-statut="'+escAttr(a.statut||'')+'" title="Supprimer">'+icon('trash',14)+'</button>';
    rows += '<tr><td><a href="#" class="ao-list-ref-link btn-view" data-id="'+a.id+'">'+escHtml(a.reference)+'</a></td>'+
      '<td>'+escHtml(a.titre)+'</td>'+
      '<td>'+cliTxt+'</td>'+
      '<td>'+refsTxt+'</td>'+
      '<td>'+statutBadge(a.statut)+'</td>'+
      '<td>'+escHtml(a.date_limite||'—')+'</td>'+
      '<td>'+escHtml(a.nb_fournisseurs)+'</td>'+
      '<td>'+escHtml(a.nb_reponses)+'</td>'+
      '<td class="ao-actions-cell">'+actions+'</td></tr>';
  });
  return '<div class="page-hdr"><h1>Appels d\'offre</h1><button class="btn btn-accent" type="button" id="btn-new-ao">'+icon('plus',14)+' Nouvel appel d\'offre</button></div>'+
    '<div class="filter-tabs">'+
    ['tous','brouillon','envoyee','cloturee'].map(f=>'<button class="filter-tab'+(S.filtre===f?' active':'')+'" data-f="'+f+'">'+escHtml(f==='tous'?'Tous':f==='brouillon'?'Brouillon':f==='envoyee'?'Envoyée':'Clôturée')+'</button>').join('')+
    '</div>'+
    (list.length ? '<div class="card"><table class="data-table"><thead><tr><th>Référence</th><th>Titre</th><th>Client</th><th>Références produits</th><th>Statut</th><th>Date limite</th><th>Fournisseurs</th><th>Réponses</th><th style="text-align:right">Actions</th></tr></thead><tbody>'+rows+'</tbody></table></div>' :
    '<div class="card empty-state"><strong>Aucun appel d\'offre</strong>Créez un premier appel d\'offre pour inviter vos fournisseurs.</div>');
}

function buildNavPagerHtml(list, currentId, labelSingular) {
  const arr = Array.isArray(list) ? list : [];
  const total = arr.length;
  if (total <= 1) return '';
  const idx = arr.findIndex(x => String(x.id) === String(currentId));
  if (idx < 0) return '';
  const prevDis = idx <= 0 ? ' disabled' : '';
  const nextDis = idx >= total - 1 ? ' disabled' : '';
  const titlePrev = labelSingular ? ('Précédent — '+labelSingular) : 'Précédent';
  const titleNext = labelSingular ? ('Suivant — '+labelSingular) : 'Suivant';
  return '<div class="nav-pager">'+
    '<button type="button" class="btn-icon btn-nav-prev"'+prevDis+' title="'+escAttr(titlePrev)+'">'+icon('arrow-left',14)+'</button>'+
    '<span class="nav-pos">'+(idx+1)+' / '+total+'</span>'+
    '<button type="button" class="btn-icon btn-nav-next"'+nextDis+' title="'+escAttr(titleNext)+'">'+icon('arrow-right',14)+'</button>'+
    '</div>';
}

function formatTransportHelper(pct) {
  const p = parseFloat(pct) || 0;
  const base = 50000;
  const t = base * p / 100;
  const fmt = v => v.toLocaleString('fr-FR', {maximumFractionDigits: 0});
  return 'Pour ' + fmt(base) + ' EUR de marchandise : ' + fmt(t) + ' EUR de transport';
}

async function saveAoTransport(aoId, pct) {
  try {
    await api('/api/ao/' + aoId + '/params', {
      method: 'PATCH', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({prix_transport_pct: pct})
    });
    if (S.ao) S.ao.prix_transport_pct = pct;
    if (S.view === 'detail' && S.tab === 'comparaison' && S.ao) {
      await loadComparaison(S.ao.id);
      render();
    }
  } catch(e) { showToast(e.message || 'Erreur transport.', 'danger'); }
}

async function loadEurUsdRate() {
  try {
    const r = await api('/api/ao/config/eur-usd');
    const el = document.getElementById('app-eur-usd');
    if (el && r && typeof r.eur_usd_rate === 'number') el.value = r.eur_usd_rate || '';
  } catch(e) { /* silencieux */ }
}

async function saveEurUsdRate(rate) {
  try {
    await api('/api/ao/config/eur-usd', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({eur_usd_rate: rate})
    });
    showToast('Taux EUR/USD mis a jour.', 'success');
    if (S.view === 'detail' && S.tab === 'comparaison' && S.ao) {
      await loadComparaison(S.ao.id);
      render();
    }
  } catch(e) { showToast(e.message || 'Erreur EUR/USD.', 'danger'); }
}

function renderDetailHeader() {
  const ao = S.ao;
  const d = S.detail;
  const st = ao.statut;
  const lignes = (d.lignes||[]).length;
  const fournis = (d.fournisseurs||[]).length;
  let actions = '<button class="btn btn-ghost" type="button" id="btn-back">'+icon('arrow-left',14)+' Retour liste</button>' +
    ' <a class="btn btn-ghost" href="/api/ao/'+ao.id+'/export.pdf" target="_blank" title="Exporter en PDF">'+icon('file-text',14)+' Export PDF</a>';
  if (st === 'brouillon') {
    const dis = (lignes < 1 || fournis < 1) ? ' disabled' : '';
    actions += '<button class="btn btn-accent" type="button" id="btn-envoyer"'+dis+'>Envoyer aux fournisseurs</button>';
  } else if (st === 'envoyee') {
    // Fournisseurs ajoutés après le premier envoi (date_envoi IS NULL, statut='invite')
    const nonenvoyes = (d.fournisseurs||[]).filter(f => !f.date_envoi && f.statut === 'invite').length;
    if (nonenvoyes > 0) {
      actions += '<button class="btn btn-accent" type="button" id="btn-envoyer">Envoyer aux nouveaux ('+nonenvoyes+')</button>';
    }
  }
  if (st === 'envoyee') actions += '<button class="btn btn-accent" type="button" id="btn-cloturer">Clôturer l\'AO</button>';
  const navPager = buildNavPagerHtml(filteredAos(), ao.id, 'appel d\'offre');
  return '<div class="breadcrumb"><a href="#" id="bc-list">Appels d\'offre</a> &gt; '+escHtml(ao.reference)+' — '+escHtml(ao.titre)+'</div>'+
    '<div class="detail-hdr"><h2>'+escHtml(ao.reference)+'</h2>'+statutBadge(st)+navPager+'</div>'+
    '<div class="detail-meta">'+escHtml(ao.titre)+'<br>Date limite : '+escHtml(ao.date_limite||'—')+' · Responsable : '+escHtml(ao.responsable_email||'—')+' · Réponses : '+escHtml(d.nb_reponses)+'</div>'+
    '<div class="detail-actions">'+actions+'</div>'+
    '<div class="detail-tabs">'+
    (() => {
      const totalNonLus = Object.values(S.nonLus || {}).reduce((a, b) => a + b, 0);
      const labels = {
        lignes:'Lignes',fournisseurs:'Fournisseurs',comparaison:'Demandes de prix',
        messages:'Messagerie'+(totalNonLus > 0
          ? ' <span class="nav-badge" style="background:var(--danger);color:#fff;font-size:10px;padding:1px 6px;border-radius:999px;font-weight:700">'+escHtml(totalNonLus)+'</span>'
          : ''),
        documents:'Documents'
      };
      return ['lignes','fournisseurs','comparaison','messages','documents'].map(t =>
        '<button class="detail-tab'+(S.tab===t?' active':'')+'" data-tab="'+t+'">'+labels[t]+'</button>'
      ).join('');
    })()+'<div class="ao-params-panel">'+
      '<div class="app-group">'+
        '<div class="app-row"><label for="app-transport">Prix transport</label>'+
          '<input type="number" id="app-transport" step="0.1" min="0" max="100" value="'+escAttr(ao.prix_transport_pct||0)+'">'+
          '<span class="app-suffix">%</span></div>'+
        '<div class="app-help" id="app-transport-help">'+formatTransportHelper(ao.prix_transport_pct||0)+'</div>'+
      '</div>'+
      '<div class="app-group">'+
        '<div class="app-row"><label for="app-eur-usd">Taux EUR/USD</label>'+
          '<input type="number" id="app-eur-usd" step="0.0001" min="0" placeholder="1.0850">'+
          '<span class="app-suffix"></span></div>'+
      '</div>'+
    '</div>'+'</div>';
}

function renderLignes() {
  const st = S.ao.statut;
  const lignes = S.detail.lignes || [];
  let rows = lignes.map(l => '<tr><td>'+escHtml(l.position)+'</td><td>'+escHtml(l.ref_produit)+'</td>'+
    '<td>'+escHtml(l.client_nom||'—')+'</td><td>'+formatInt(l.etiquettes_par_bobine)+'</td>'+
    '<td>'+escHtml(l.quantite)+' '+escHtml(l.unite)+'</td><td>'+escHtml(l.notes||'')+'</td><td>'+
    (st==='brouillon'?'<button class="btn btn-ghost btn-sm btn-edit-ligne" data-id="'+l.id+'">Modifier</button> <button class="btn btn-ghost btn-sm btn-del-ligne" data-id="'+l.id+'">Supprimer</button>':'')+
    '</td></tr>').join('');
  return '<div class="card">'+(st==='brouillon'?'<button class="btn btn-accent btn-sm" type="button" id="btn-add-ligne" style="margin-bottom:12px">'+icon('plus',14)+' Ajouter une ligne</button>':'')+
    '<table class="data-table"><thead><tr><th>#</th><th>Réf.</th><th>Client</th><th>Étiq. / bobine</th><th>Qté</th><th>Notes</th><th></th></tr></thead><tbody>'+
    (rows||'<tr><td colspan="7" style="color:var(--muted)">Aucune ligne</td></tr>')+'</tbody></table></div>';
}

function renderFournisseurs() {
  const ao = S.ao;
  const fournis = S.detail.fournisseurs || [];
  const base = (BASE_URL || window.location.origin).replace(/\/$/,'');
  let rows = fournis.map(f => {
    const lien = base+'/portail/ao/'+f.token;
    const nb = S.nonLus[String(f.id)] || 0;
    const unreadBadge = nb > 0
      ? ' <span style="background:var(--danger);color:#fff;font-size:10px;padding:1px 6px;border-radius:999px;font-weight:700;display:inline-block">'+escHtml(nb)+' msg</span>'
      : '';
    let act = '<button class="btn btn-ghost btn-sm btn-copy" data-token="'+escAttr(f.token)+'">Copier lien</button> '+
      '<button class="btn btn-ghost btn-sm btn-msg" data-id="'+f.id+'">Messagerie</button>';
    if (f.statut !== 'repondu') act += ' <button class="btn btn-ghost btn-sm btn-edit-f" data-id="'+f.id+'">Modifier</button>';
    if (f.statut !== 'repondu') act += ' <button class="btn btn-ghost btn-sm btn-del-f" data-id="'+f.id+'">Supprimer</button>';
    return '<tr><td>'+escHtml(f.nom_fournisseur)+'</td><td>'+escHtml(f.email_contact)+'</td><td>'+fourniBadge(f.statut)+unreadBadge+'</td>'+
      '<td>'+escHtml(f.date_envoi||'—')+'</td><td>'+escHtml(f.date_reponse||'—')+'</td><td>'+act+'</td></tr>';
  }).join('');
  return '<div class="card">'+(ao.statut!=='cloturee'?'<button class="btn btn-accent btn-sm" id="btn-add-f" style="margin-bottom:12px">'+icon('plus',14)+' Ajouter un fournisseur</button>':'')+
    '<table class="data-table"><thead><tr><th>Nom</th><th>Email</th><th>Statut</th><th>Envoi</th><th>Réponse</th><th></th></tr></thead><tbody>'+
    (rows||'<tr><td colspan="6" style="color:var(--muted)">Aucun fournisseur</td></tr>')+'</tbody></table></div>';
}






// ── Cloture AO avec picker fournisseur retenu ──
async function openCloturerAoModal() {
  const ao = S.ao;
  const d = S.detail;
  const fournis = (d && d.fournisseurs) || [];
  const rep = fournis.filter(f => f.statut === 'repondu');
  const m = document.getElementById('mroot');
  if (!m) return;
  m.innerHTML = '';
  const ov = document.createElement('div'); ov.className = 'modal-overlay';
  const box = document.createElement('div'); box.className = 'modal';
  const hasReponses = rep.length > 0;
  let html = '<h3>Cloturer l\'appel d\'offre</h3>' +
    '<p style="font-size:12px;color:var(--muted);margin-bottom:14px">Cloture le AO et notifie optionnellement le fournisseur retenu par email.</p>';
  if (hasReponses) {
    html += '<div class="field"><label>Fournisseur retenu (optionnel)</label>' +
      '<select id="m-retenu"><option value="">— Aucun (juste cloturer) —</option>';
    rep.forEach(f => {
      html += '<option value="' + f.id + '">' + escHtml(f.nom_fournisseur) + ' &lt;' + escHtml(f.email_contact) + '&gt;</option>';
    });
    html += '</select></div>' +
      '<div class="field"><label>Message personnalise (optionnel)</label>' +
      '<textarea id="m-msg" rows="3" placeholder="Ajoute un message qui sera insere dans l\'email au fournisseur retenu."></textarea></div>';
  } else {
    html += '<p class="sub" style="color:var(--muted)">Aucun fournisseur n\'a repondu pour l\'instant — la cloture ne notifiera personne.</p>';
  }
  html += '<div class="modal-actions">' +
    '<button class="btn btn-ghost" id="m-cancel">Annuler</button>' +
    '<button class="btn btn-accent" id="m-ok">Cloturer</button></div>';
  box.innerHTML = html;
  ov.appendChild(box); m.appendChild(ov);
  document.getElementById('m-cancel').onclick = closeModal;
  document.getElementById('m-ok').onclick = async () => {
    const retenu = hasReponses ? (document.getElementById('m-retenu').value || null) : null;
    const msg = hasReponses ? (document.getElementById('m-msg').value.trim() || null) : null;
    try {
      await api('/api/ao/' + ao.id + '/cloturer', {
        method: 'PATCH', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({fournisseur_retenu_id: retenu ? parseInt(retenu, 10) : null, message_perso: msg})
      });
      closeModal();
      showToast('AO cloture' + (retenu ? ' — email envoye au fournisseur retenu' : '') + '.', 'success');
      await loadDetail(ao.id); render();
    } catch (e) { showToast(e.message || 'Erreur', 'danger'); }
  };
}

// ── Wizard creation AO en 3 etapes ──
function openQuickProduitModal(onCreated) {
  // Modal nestable qui se pose sur tout (wizard inclus) via z-index eleve
  const existing = document.getElementById('quick-produit-modal');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'quick-produit-modal';
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.55);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding-top:80px;overflow-y:auto';

  const modal = document.createElement('div');
  modal.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px 24px;width:min(520px,92vw);box-shadow:0 20px 60px rgba(0,0,0,.35);color:var(--text)';
  modal.innerHTML = '<h3 style="margin:0 0 14px 0;font-size:16px;font-weight:700">Nouveau produit</h3>'+
    '<div style="margin-bottom:12px"><label style="font-size:12px;font-weight:600;color:var(--text2);display:block;margin-bottom:4px">Reference *</label>'+
    '<input id="qp-ref" type="text" placeholder="Ex: 1145/0050" style="width:100%;padding:8px 10px;font-size:14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);box-sizing:border-box;font-family:inherit" autocomplete="off"></div>'+
    '<div style="margin-bottom:12px"><label style="font-size:12px;font-weight:600;color:var(--text2);display:block;margin-bottom:4px">Designation</label>'+
    '<input id="qp-des" type="text" placeholder="Ex: Etiquettes 101,6x152,4mm" style="width:100%;padding:8px 10px;font-size:14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);box-sizing:border-box;font-family:inherit" autocomplete="off"></div>'+
    '<div style="margin-bottom:12px"><label style="font-size:12px;font-weight:600;color:var(--text2);display:block;margin-bottom:4px">Client (optionnel)</label>'+
    '<div style="position:relative">'+
    '<input id="qp-client-search" type="text" placeholder="Tape un nom (min 2 lettres)..." autocomplete="off" style="width:100%;padding:8px 10px;font-size:14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);box-sizing:border-box;font-family:inherit">'+
    '<div id="qp-client-results" style="display:none;position:absolute;left:0;right:0;top:100%;background:var(--card);border:1px solid var(--border);border-radius:0 0 8px 8px;max-height:180px;overflow:auto;z-index:2"></div>'+
    '<div id="qp-client-selected" style="display:none;margin-top:6px;padding:6px 10px;background:var(--accent-bg,rgba(34,211,238,.08));border:1px solid var(--border);border-radius:8px;font-size:13px"></div>'+
    '</div></div>'+
    '<div style="margin-bottom:16px"><label style="font-size:12px;font-weight:600;color:var(--text2);display:block;margin-bottom:4px">Unite</label>'+
    '<select id="qp-unite" style="width:100%;padding:8px 10px;font-size:14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit">'+
    '<option value="unite">unite</option><option value="etiquettes">etiquettes</option><option value="bobine">bobine</option><option value="palette">palette</option>'+
    '</select></div>'+
    '<div style="display:flex;justify-content:flex-end;gap:8px">'+
    '<button type="button" id="qp-cancel" class="btn btn-ghost">Annuler</button>'+
    '<button type="button" id="qp-save" class="btn btn-accent">Creer</button>'+
    '</div>';
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  let selectedClient = null;
  const cleanup = () => overlay.remove();

  document.getElementById('qp-cancel').onclick = () => { cleanup(); };
  overlay.onclick = (e) => { if (e.target === overlay) cleanup(); };

  // Client picker inline
  const searchInp = document.getElementById('qp-client-search');
  const resultsDiv = document.getElementById('qp-client-results');
  const selectedDiv = document.getElementById('qp-client-selected');
  let searchTimer = null;
  searchInp.addEventListener('input', () => {
    const q = searchInp.value.trim();
    clearTimeout(searchTimer);
    if (q.length < 2) { resultsDiv.style.display = 'none'; return; }
    searchTimer = setTimeout(async () => {
      try {
        const rows = await api('/api/ao/picker/clients?search=' + encodeURIComponent(q) + '&limit=15');
        if (!rows || !rows.length) {
          resultsDiv.innerHTML = '<div style="padding:8px 10px;color:var(--muted);font-size:12px">Aucun client</div>';
          resultsDiv.style.display = 'block';
          return;
        }
        resultsDiv.innerHTML = rows.map(c => {
          const label = c.raison_sociale || c.nom || ('Client #' + c.id);
          return '<div class="qp-cli-row" data-cid="'+c.id+'" data-label="'+escAttr(label)+'" style="padding:8px 10px;cursor:pointer;font-size:12px;border-bottom:1px solid var(--border)"><strong>'+escHtml(label)+'</strong></div>';
        }).join('');
        resultsDiv.style.display = 'block';
        resultsDiv.querySelectorAll('.qp-cli-row').forEach(row => {
          row.onclick = () => {
            selectedClient = {id: parseInt(row.dataset.cid, 10), label: row.dataset.label};
            selectedDiv.innerHTML = '<strong>' + escHtml(selectedClient.label) + '</strong> <button type="button" id="qp-cli-clear" style="border:none;background:transparent;color:var(--danger);cursor:pointer;padding:0 4px">x</button>';
            selectedDiv.style.display = 'block';
            searchInp.style.display = 'none';
            resultsDiv.style.display = 'none';
            document.getElementById('qp-cli-clear').onclick = () => {
              selectedClient = null;
              selectedDiv.style.display = 'none';
              searchInp.style.display = '';
              searchInp.value = '';
            };
          };
        });
      } catch(e) {
        resultsDiv.innerHTML = '<div style="padding:8px 10px;color:var(--danger);font-size:12px">Erreur: '+escHtml(e.message||String(e))+'</div>';
        resultsDiv.style.display = 'block';
      }
    }, 220);
  });

  document.getElementById('qp-save').onclick = async () => {
    const ref = (document.getElementById('qp-ref').value || '').trim();
    const designation = (document.getElementById('qp-des').value || '').trim();
    const unite = document.getElementById('qp-unite').value || 'unite';
    if (!ref) { showToast('Reference obligatoire.', 'danger'); return; }
    const saveBtn = document.getElementById('qp-save');
    saveBtn.disabled = true;
    try {
      const body = {ref: ref, designation: designation || ref, unite: unite};
      if (selectedClient) body.client_id = selectedClient.id;
      const created = await api('/api/ao/produits', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      try { await loadProduits(); } catch(e) {}
      showToast('Produit ' + (created.ref || ref) + ' cree.', 'success');
      cleanup();
      if (typeof onCreated === 'function') onCreated(created);
    } catch(e) {
      showToast(e.message || 'Erreur creation produit.', 'danger');
      saveBtn.disabled = false;
    }
  };

  // Focus ref field
  setTimeout(() => document.getElementById('qp-ref')?.focus(), 50);
}

async function openCreateAoWizard(initialState) {
  const m = document.getElementById('mroot');
  if (!m) return;
  m.innerHTML = '';
  const ov = document.createElement('div'); ov.className = 'modal-overlay';
  const box = document.createElement('div'); box.className = 'modal modal-wide wizard-ao';
  box.style.maxWidth = '760px';
  box.style.width = '92vw';

  let state;
  if (initialState) {
    state = initialState;
    if (typeof state.step !== 'number') state.step = 2;
  } else {
    state = {
    step: 1,
    info: {
      titre: '',
      description: '',
      date_limite: '',
      responsable_email: (S.user && S.user.email) || '',
      client_id: null,
      client_label: '',
    },
    lignes: [{ ref_produit: '', designation: '', quantite: '', unite: 'etiquettes', notes: '' }],
    // fournisseurs: liste d'objets ajoutes {nom_fournisseur, email_contact, langue, fournisseur_id?, fournisseur_contact_id?}
    fournisseurs: [],
    availableFournisseurs: [],
    availableProduits: S.produits || [],
    selectedContactKeys: new Set(),
    manualFourni: { nom: '', email: '', langue: 'fr' },
    _autoP: false,
    };
  }

  // Charge fournisseurs+contacts et produits en parallele (skip si etat existant)
  if (!initialState) {
    try {
      const [fours] = await Promise.all([
        api('/api/ao/picker/fournisseurs-with-contacts'),
      ]);
      state.availableFournisseurs = fours || [];
    } catch (e) {
      showToast('Erreur chargement donnees: ' + (e.message || e), 'danger');
    }
    // Auto-preselect contacts principaux
    state.availableFournisseurs.forEach(f => (f.contacts || []).forEach(c => {
      if (c.is_principal) state.selectedContactKeys.add(f.id + ':' + c.id);
    }));
  }

  function renderStepIndicator() {
    const steps = ['Infos AO', 'Produits', 'Fournisseurs'];
    // Style breadcrumb avec fleches (chevron) — pas de bordures type boutons
    let html = '<div style="display:flex;align-items:center;margin-bottom:20px;font-size:14px;user-select:none">';
    steps.forEach((label, i) => {
      const n = i + 1;
      const isActive = state.step === n;
      const isDone = state.step > n;
      const color = isActive ? 'var(--accent)' : (isDone ? 'var(--ok)' : 'var(--muted)');
      const weight = isActive ? '700' : (isDone ? '600' : '500');
      const badge = isDone
        ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--ok);color:#fff;font-size:11px;margin-right:8px">✓</span>'
        : '<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:' + (isActive ? 'var(--accent)' : 'transparent') + ';color:' + (isActive ? '#fff' : color) + ';border:' + (isActive ? 'none' : '1.5px solid ' + color) + ';font-size:11px;font-weight:700;margin-right:8px">' + n + '</span>';
      html += '<span style="display:inline-flex;align-items:center;color:' + color + ';font-weight:' + weight + '">' + badge + label + '</span>';
      if (i < steps.length - 1) {
        html += '<span style="margin:0 12px;color:var(--muted);font-size:16px">›</span>';
      }
    });
    html += '</div>';
    return html;
  }

  function renderStep1() {
    const info = state.info;
    const clientBtn = info.client_id
      ? '<div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px"><strong>' + escHtml(info.client_label || '') + '</strong>' +
        '<button type="button" class="btn btn-ghost btn-sm" id="w-client-clear" style="padding:2px 8px">×</button></div>'
      : '<div style="position:relative">' +
        '<input type="text" id="w-client-search" placeholder="Tape un nom de client (min 2 lettres)..." autocomplete="off" style="width:100%">' +
        '<div id="w-client-results" style="display:none;position:absolute;left:0;right:0;top:100%;background:var(--card);border:1px solid var(--border);border-radius:0 0 8px 8px;max-height:200px;overflow:auto;z-index:20"></div>' +
        '</div>';
    return '<div class="field"><label>Titre de l\'appel d\'offre *</label>' +
      '<input id="w-titre" value="' + escAttr(info.titre) + '" placeholder="Ex: RFQ etiquettes lot 12345"></div>' +
      '<div class="field"><label>Client (optionnel)</label>' + clientBtn + '</div>' +
      '<div class="field"><label>Description</label>' +
      '<textarea id="w-desc" rows="3" placeholder="Contexte, contraintes...">' + escHtml(info.description) + '</textarea></div>' +
      '<div class="form-row">' +
      '<div class="field"><label>Date limite</label>' +
      '<input type="date" id="w-limite" value="' + escAttr(info.date_limite) + '"></div>' +
      '<div class="field"><label>Email responsable *</label>' +
      '<input type="email" id="w-email" value="' + escAttr(info.responsable_email) + '"></div>' +
      '</div>';
  }

  function renderStep2() {
    const prodOpts = '<option value="">— saisie manuelle —</option>' +
      '<option value="__CREATE__">+ Creer un nouveau produit</option>' +
      (state.availableProduits || []).map(p =>
        '<option value="' + p.id + '">' + escHtml(p.ref) + ' — ' + escHtml(p.designation) + '</option>'
      ).join('');
    let html = '<p style="font-size:13px;color:var(--muted);margin-bottom:10px">Ajoute une ou plusieurs lignes produits. Le champ <strong>Ref produit</strong> et la <strong>quantite</strong> sont obligatoires.</p>' +
      '<div style="overflow-x:auto"><table style="width:100%;font-size:12px">' +
      '<thead><tr>' +
      '<th style="text-align:left;padding:4px;color:var(--muted)">Catalogue</th>' +
      '<th style="text-align:left;padding:4px;color:var(--muted)">Ref *</th>' +
      '<th style="text-align:left;padding:4px;color:var(--muted)">Designation</th>' +
      '<th style="text-align:left;padding:4px;color:var(--muted)">Qte *</th>' +
      '<th style="text-align:left;padding:4px;color:var(--muted)">Notes</th>' +
      '<th></th></tr></thead><tbody>';
    state.lignes.forEach((ln, i) => {
      html += '<tr class="w-ligne-row" data-idx="' + i + '">' +
        '<td style="padding:2px"><select class="w-l-pick" style="width:100%;font-size:11px">' + prodOpts + '</select></td>' +
        '<td style="padding:2px"><input class="w-l-ref" value="' + escAttr(ln.ref_produit) + '" style="width:100%;font-size:11px"></td>' +
        '<td style="padding:2px"><input class="w-l-des" value="' + escAttr(ln.designation) + '" style="width:100%;font-size:11px"></td>' +
        '<td style="padding:2px"><input class="w-l-qte" type="number" step="1" min="0" value="' + escAttr(ln.quantite) + '" style="width:80px;font-size:11px"></td>' +
        '<td style="padding:2px"><input class="w-l-notes" value="' + escAttr(ln.notes || '') + '" style="width:100%;font-size:11px"></td>' +
        '<td style="padding:2px"><button type="button" class="btn btn-ghost btn-sm w-l-del" style="font-size:11px;padding:2px 8px" title="Supprimer">×</button></td>' +
        '</tr>';
    });
    html += '</tbody></table></div>' +
      '<button type="button" class="btn btn-ghost btn-sm" id="w-l-add" style="margin-top:8px">+ Ajouter une ligne</button>';
    return html;
  }

  function renderStep3() {
    const fours = state.availableFournisseurs;
    const nManualAdded = state.fournisseurs.filter(f => !f.fournisseur_id).length;
    let html = '<p style="font-size:13px;color:var(--muted);margin-bottom:10px">Selectionne au moins un contact fournisseur.</p>' +
      '<div style="max-height:300px;overflow:auto;border:1px solid var(--border);border-radius:8px;padding:6px">';
    if (!fours.length) {
      html += '<div style="padding:20px;color:var(--muted);text-align:center">Aucun fournisseur enregistre en base. Utilise la saisie manuelle ci-dessous.</div>';
    } else {
      fours.forEach(f => {
        const contacts = f.contacts || [];
        html += '<div style="padding:6px 8px;border-bottom:1px solid var(--border)">' +
          '<div style="font-weight:600;font-size:12px">' + escHtml(f.nom) +
          (f.ville ? ' <span style="font-size:10px;color:var(--muted)">' + escHtml(f.ville) + '</span>' : '') +
          '</div>';
        if (!contacts.length) {
          html += '<div style="font-size:11px;color:var(--muted);margin:2px 0">Aucun contact enregistre.</div>';
        } else {
          contacts.forEach(c => {
            const key = f.id + ':' + c.id;
            const emails = (c.emails || []).join(', ');
            const principal = c.is_principal ? ' <span style="font-size:10px;color:var(--accent)">★</span>' : '';
            html += '<label style="display:flex;align-items:center;gap:6px;padding:2px 0;font-size:11px;cursor:pointer">' +
              '<input type="checkbox" class="w-fc" data-key="' + escAttr(key) + '"' + (state.selectedContactKeys.has(key) ? ' checked' : '') + '>' +
              '<span><strong>' + escHtml(c.nom || '—') + '</strong>' + principal +
              (emails ? ' <span style="color:var(--muted)">· ' + escHtml(emails) + '</span>' : '') + '</span></label>';
          });
        }
        html += '</div>';
      });
    }
    html += '</div>';
    html += '<div style="margin-top:12px;padding:10px;border:1px dashed var(--border);border-radius:8px">' +
      '<div style="font-size:12px;font-weight:600;margin-bottom:8px">Ou ajouter un contact manuel</div>' +
      '<div class="form-row">' +
      '<div class="field"><label style="font-size:11px">Nom / societe</label><input class="w-mf-nom" value="' + escAttr(state.manualFourni.nom) + '" placeholder="Nom fournisseur"></div>' +
      '<div class="field"><label style="font-size:11px">Email</label><input type="email" class="w-mf-email" value="' + escAttr(state.manualFourni.email) + '"></div>' +
      '</div>' +
      '<div class="form-row" style="align-items:end">' +
      '<div class="field"><label style="font-size:11px">Langue</label>' +
      '<select class="w-mf-langue"><option value="fr"' + (state.manualFourni.langue === 'fr' ? ' selected' : '') + '>FR</option>' +
      '<option value="en"' + (state.manualFourni.langue === 'en' ? ' selected' : '') + '>EN</option></select></div>' +
      '<div class="field"><button type="button" class="btn btn-ghost btn-sm" id="w-mf-add">+ Ajouter ce contact</button></div>' +
      '</div>';
    if (nManualAdded > 0) {
      html += '<ul style="font-size:11px;color:var(--muted);margin:8px 0 0;padding-left:18px">' +
        state.fournisseurs.filter(f => !f.fournisseur_id).map(f =>
          '<li>' + escHtml(f.nom_fournisseur) + ' — ' + escHtml(f.email_contact) + '</li>'
        ).join('') + '</ul>';
    }
    html += '</div>';
    return html;
  }

  function commitStep1FromDOM() {
    state.info.titre = (document.getElementById('w-titre')?.value || '').trim();
    state.info.description = (document.getElementById('w-desc')?.value || '').trim();
    state.info.date_limite = document.getElementById('w-limite')?.value || '';
    state.info.responsable_email = (document.getElementById('w-email')?.value || '').trim();
  }
  function commitStep2FromDOM() {
    const rows = box.querySelectorAll('.w-ligne-row');
    state.lignes = [];
    rows.forEach(row => {
      state.lignes.push({
        ref_produit: (row.querySelector('.w-l-ref')?.value || '').trim(),
        designation: (row.querySelector('.w-l-des')?.value || '').trim(),
        quantite: (row.querySelector('.w-l-qte')?.value || '').trim(),
        unite: 'etiquettes',
        notes: (row.querySelector('.w-l-notes')?.value || '').trim(),
      });
    });
  }
  function commitStep3ManualFromDOM() {
    const nom = (box.querySelector('.w-mf-nom')?.value || '').trim();
    const email = (box.querySelector('.w-mf-email')?.value || '').trim();
    const langue = box.querySelector('.w-mf-langue')?.value || 'fr';
    state.manualFourni = { nom, email, langue };
  }

  function validateStep(n) {
    if (n === 1) {
      if (!state.info.titre) return 'Titre obligatoire.';
      if (!state.info.responsable_email) return 'Email responsable obligatoire.';
    }
    if (n === 2) {
      const valid = state.lignes.filter(l => l.ref_produit && l.quantite);
      if (!valid.length) return 'Ajoute au moins une ligne avec ref produit et quantite.';
    }
    if (n === 3) {
      if (!state.selectedContactKeys.size && !state.fournisseurs.length) {
        return 'Selectionne au moins un contact fournisseur ou ajoute-en un manuellement.';
      }
    }
    return null;
  }

  function render() {
    // Style scope au wizard : inputs et polices plus grandes
    let content = '<style>' +
      '.wizard-ao h3{font-size:18px;margin-bottom:6px}' +
      '.wizard-ao .field label{font-size:13px;color:var(--text);font-weight:600;margin-bottom:4px;display:block}' +
      '.wizard-ao .field input,.wizard-ao .field select,.wizard-ao .field textarea{width:100%;padding:9px 12px;font-size:14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;box-sizing:border-box}' +
      '.wizard-ao .field textarea{min-height:64px;resize:vertical}' +
      '.wizard-ao .field{margin-bottom:12px}' +
      '.wizard-ao .form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}' +
      '.wizard-ao table input,.wizard-ao table select{padding:6px 8px;font-size:13px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;box-sizing:border-box;width:100%}' +
      '.wizard-ao table th{padding:8px 6px !important;font-size:11px;text-transform:uppercase;letter-spacing:.5px}' +
      '.wizard-ao table td{padding:4px 6px !important;vertical-align:middle}' +
      '.wizard-ao .w-l-del{color:var(--danger)}' +
      '.wizard-ao p{font-size:13px;line-height:1.5}' +
      '.wizard-ao label{font-size:13px}' +
      '.wizard-ao .modal-actions button{padding:10px 16px;font-size:14px}' +
      '</style>' +
      '<h3>Nouvel appel d\'offre</h3>' + renderStepIndicator();
    if (state.step === 1) content += renderStep1();
    else if (state.step === 2) content += renderStep2();
    else if (state.step === 3) content += renderStep3();
    const isLast = state.step === 3;
    content += '<div class="modal-actions" style="margin-top:16px;justify-content:space-between">' +
      '<div>' +
      (state.step > 1 ? '<button type="button" class="btn btn-ghost" id="w-prev">← Precedent</button>' : '') +
      '</div><div style="display:flex;gap:6px">' +
      '<button type="button" class="btn btn-ghost" id="w-cancel">Annuler</button>' +
      (isLast
        ? '<button type="button" class="btn btn-accent" id="w-submit">Creer l\'AO</button>'
        : '<button type="button" class="btn btn-accent" id="w-next">Suivant →</button>') +
      '</div></div>';
    box.innerHTML = content;

    // Step 1 client picker inline autocomplete
    if (state.step === 1) {
      const searchInp = document.getElementById('w-client-search');
      const resultsDiv = document.getElementById('w-client-results');
      let searchTimer = null;
      if (searchInp && resultsDiv) {
        searchInp.addEventListener('input', () => {
          const q = searchInp.value.trim();
          clearTimeout(searchTimer);
          if (q.length < 2) {
            resultsDiv.style.display = 'none';
            return;
          }
          searchTimer = setTimeout(async () => {
            try {
              const rows = await api('/api/ao/picker/clients?search=' + encodeURIComponent(q) + '&limit=20');
              if (!rows || !rows.length) {
                resultsDiv.innerHTML = '<div style="padding:8px 10px;color:var(--muted);font-size:12px">Aucun client trouve.</div>';
                resultsDiv.style.display = 'block';
                return;
              }
              resultsDiv.innerHTML = rows.map(c => {
                const label = c.raison_sociale || c.nom || ('Client #' + c.id);
                const meta = [c.code, c.ville, c.pays].filter(Boolean).join(' · ');
                return '<div class="w-client-row" data-cid="' + c.id + '" data-clabel="' + escAttr(label) + '" style="padding:8px 10px;cursor:pointer;font-size:12px;border-bottom:1px solid var(--border)">' +
                  '<strong>' + escHtml(label) + '</strong>' +
                  (meta ? '<div style="color:var(--muted);font-size:10px">' + escHtml(meta) + '</div>' : '') +
                  '</div>';
              }).join('');
              resultsDiv.style.display = 'block';
              resultsDiv.querySelectorAll('.w-client-row').forEach(row => {
                row.onclick = () => {
                  commitStep1FromDOM();
                  state.info.client_id = parseInt(row.dataset.cid, 10);
                  state.info.client_label = row.dataset.clabel;
                  render();
                };
                row.onmouseenter = () => { row.style.background = 'var(--accent-bg, rgba(34,211,238,.08))'; };
                row.onmouseleave = () => { row.style.background = ''; };
              });
            } catch (e) {
              resultsDiv.innerHTML = '<div style="padding:8px 10px;color:var(--danger);font-size:12px">Erreur: ' + escHtml(e.message || String(e)) + '</div>';
              resultsDiv.style.display = 'block';
            }
          }, 220);
        });
      }
      const clr = document.getElementById('w-client-clear');
      if (clr) clr.onclick = () => { commitStep1FromDOM(); state.info.client_id = null; state.info.client_label = ''; render(); };
    }

    // Step 2 : add / delete row + prefill from catalogue
    if (state.step === 2) {
      document.getElementById('w-l-add').onclick = () => {
        commitStep2FromDOM();
        state.lignes.push({ ref_produit: '', designation: '', quantite: '', unite: 'etiquettes', notes: '' });
        render();
      };
      box.querySelectorAll('.w-l-del').forEach((btn, idx) => {
        btn.onclick = () => {
          commitStep2FromDOM();
          state.lignes.splice(idx, 1);
          if (!state.lignes.length) state.lignes.push({ ref_produit: '', designation: '', quantite: '', unite: 'etiquettes', notes: '' });
          render();
        };
      });
      box.querySelectorAll('.w-l-pick').forEach((sel, idx) => {
        sel.onchange = async () => {
          const pid = sel.value;
          if (pid === '__CREATE__') {
            sel.value = '';
            commitStep2FromDOM();
            // Save wizard state + hook, close modal, switch to full produit form
            S._pendingWizardHook = {
              lineIdx: idx,
              onSaved: (created) => {
                state.availableProduits = S.produits || [];
                state.lignes[idx].ref_produit = created.ref;
                state.lignes[idx].designation = created.designation || '';
                openCreateAoWizard(state);
              },
              onCanceled: () => {
                openCreateAoWizard(state);
              }
            };
            // Close wizard modal (mroot)
            m.innerHTML = '';
            // Switch to produits section + open produit form
            S.section = 'produits';
            await openProduitForm(null);
            return;
          }
          if (!pid) return;
          const p = (state.availableProduits || []).find(x => String(x.id) === String(pid));
          if (!p) return;
          const row = box.querySelectorAll('.w-ligne-row')[idx];
          row.querySelector('.w-l-ref').value = p.ref || '';
          row.querySelector('.w-l-des').value = p.designation || '';
          if (!row.querySelector('.w-l-qte').value) row.querySelector('.w-l-qte').value = '';
        };
      });
      // Auto-select des selects w-l-pick base sur state.lignes[idx].ref_produit
      box.querySelectorAll('.w-l-pick').forEach((sel, idx) => {
        const ref = state.lignes[idx] && state.lignes[idx].ref_produit;
        if (ref) {
          const p = (state.availableProduits || []).find(x => x.ref === ref);
          if (p) sel.value = String(p.id);
        }
      });
    }

    // Step 3 : contact checkboxes + manual add
    if (state.step === 3) {
      box.querySelectorAll('.w-fc').forEach(cb => {
        cb.onchange = () => {
          const k = cb.dataset.key;
          if (cb.checked) state.selectedContactKeys.add(k);
          else state.selectedContactKeys.delete(k);
        };
      });
      document.getElementById('w-mf-add').onclick = () => {
        commitStep3ManualFromDOM();
        const mf = state.manualFourni;
        if (!mf.nom || !mf.email) { showToast('Nom et email obligatoires.', 'danger'); return; }
        state.fournisseurs.push({
          nom_fournisseur: mf.nom, email_contact: mf.email, langue: mf.langue,
        });
        state.manualFourni = { nom: '', email: '', langue: 'fr' };
        render();
      };
    }

    // Nav
    document.getElementById('w-cancel').onclick = closeModal;
    if (state.step > 1) {
      document.getElementById('w-prev').onclick = () => {
        if (state.step === 1) commitStep1FromDOM();
        if (state.step === 2) commitStep2FromDOM();
        if (state.step === 3) commitStep3ManualFromDOM();
        state.step -= 1;
        render();
      };
    }
    const nextBtn = document.getElementById('w-next');
    if (nextBtn) {
      nextBtn.onclick = () => {
        if (state.step === 1) commitStep1FromDOM();
        if (state.step === 2) commitStep2FromDOM();
        if (state.step === 3) commitStep3ManualFromDOM();
        const err = validateStep(state.step);
        if (err) { showToast(err, 'danger'); return; }
        state.step += 1;
        render();
      };
    }
    const submitBtn = document.getElementById('w-submit');
    if (submitBtn) {
      submitBtn.onclick = async () => {
        commitStep3ManualFromDOM();
        // Recheck all steps
        for (let s = 1; s <= 3; s++) {
          const err = validateStep(s);
          if (err) { showToast('Etape ' + s + ' : ' + err, 'danger'); state.step = s; render(); return; }
        }
        submitBtn.disabled = true;
        try {
          // 1. Create AO
          const aoBody = {
            titre: state.info.titre,
            description: state.info.description || null,
            date_limite: state.info.date_limite || null,
            responsable_email: state.info.responsable_email,
            client_id: state.info.client_id || null,
          };
          const ao = await api('/api/ao', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(aoBody)});
          // 2. Add lignes
          for (const ln of state.lignes.filter(l => l.ref_produit && l.quantite)) {
            await api('/api/ao/' + ao.id + '/lignes', {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                ref_produit: ln.ref_produit, designation: ln.designation || ln.ref_produit,
                quantite: parseFloat(ln.quantite), unite: ln.unite || 'etiquettes', notes: ln.notes || null,
              })
            });
          }
          // 3. Add fournisseurs from selected contacts
          for (const key of state.selectedContactKeys) {
            const [fId, cId] = key.split(':').map(Number);
            const f = state.availableFournisseurs.find(x => x.id === fId); if (!f) continue;
            const c = (f.contacts || []).find(x => x.id === cId); if (!c) continue;
            const email = (c.emails && c.emails[0]) || ''; if (!email) continue;
            await api('/api/ao/' + ao.id + '/fournisseurs', {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                nom_fournisseur: f.nom + ' — ' + (c.nom || ''), email_contact: email,
                langue: c.langue || f.langue_default || 'fr',
                fournisseur_id: fId, fournisseur_contact_id: cId,
              })
            });
          }
          // 4. Add manual fournisseurs
          for (const mf of state.fournisseurs) {
            await api('/api/ao/' + ao.id + '/fournisseurs', {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                nom_fournisseur: mf.nom_fournisseur, email_contact: mf.email_contact, langue: mf.langue,
              })
            });
          }
          closeModal();
          showToast('AO cree — ' + ao.reference, 'success');
          await openDetail(ao.id);
        } catch (e) {
          submitBtn.disabled = false;
          showToast(e.message || 'Erreur creation AO', 'danger');
        }
      };
    }
  }

  ov.appendChild(box); m.appendChild(ov);
  render();
}


// ── Phase 3 v2 : modal picker fournisseurs (avec quick-add contact) ──
async function _reloadFournisseursCache(state) {
  try {
    state.fournisseurs = await api('/api/ao/picker/fournisseurs-with-contacts');
  } catch (e) {
    state.fournisseurs = [];
    showToast('Erreur chargement fournisseurs: ' + (e.message || e), 'danger');
  }
}

async function _quickAddContact(fournisseurId, box, onDone) {
  // Mini modal inline pour ajouter un contact rapidement
  const wrap = document.createElement('div');
  wrap.style.cssText = 'position:absolute;left:0;right:0;top:0;bottom:0;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;z-index:10;border-radius:12px';
  wrap.innerHTML = '<div style="background:var(--card);padding:16px;border-radius:10px;border:1px solid var(--border);min-width:320px;max-width:400px">' +
    '<h4 style="margin:0 0 12px;font-size:14px">Ajouter un contact rapide</h4>' +
    '<div class="field"><label>Nom du contact</label><input id="qac-nom" placeholder="Prenom Nom" style="width:100%"></div>' +
    '<div class="field"><label>Email</label><input type="email" id="qac-email" placeholder="contact@..." style="width:100%"></div>' +
    '<div class="field"><label>Langue</label>' +
    '<select id="qac-langue"><option value="fr">Francais</option><option value="en">English</option></select></div>' +
    '<label style="display:flex;align-items:center;gap:6px;font-size:12px;margin-bottom:10px;cursor:pointer">' +
    '<input type="checkbox" id="qac-principal" checked> Contact principal</label>' +
    '<div style="display:flex;gap:6px;justify-content:flex-end">' +
    '<button class="btn btn-ghost btn-sm" id="qac-cancel">Annuler</button>' +
    '<button class="btn btn-accent btn-sm" id="qac-ok">Creer</button>' +
    '</div></div>';
  box.style.position = 'relative';
  box.appendChild(wrap);
  const cleanup = () => wrap.remove();
  wrap.querySelector('#qac-cancel').onclick = cleanup;
  wrap.querySelector('#qac-ok').onclick = async () => {
    const nom = wrap.querySelector('#qac-nom').value.trim();
    const email = wrap.querySelector('#qac-email').value.trim();
    if (!nom || !email) { showToast('Nom et email obligatoires.', 'danger'); return; }
    const payload = {
      nom,
      emails: [email],
      langue: wrap.querySelector('#qac-langue').value,
      is_principal: wrap.querySelector('#qac-principal').checked,
    };
    try {
      await api('/api/fournisseurs/' + fournisseurId + '/contacts', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      showToast('Contact ajoute.', 'success');
      cleanup();
      if (onDone) await onDone();
    } catch (e) { showToast(e.message || 'Erreur', 'danger'); }
  };
  wrap.querySelector('#qac-nom').focus();
}

async function openAddFournisseurModalV2() {
  const m = document.getElementById('mroot');
  if (!m) return;
  m.innerHTML = '';
  const ov = document.createElement('div'); ov.className = 'modal-overlay';
  const box = document.createElement('div'); box.className = 'modal modal-wide';

  const state = {
    search: '',
    selectedContacts: new Set(),
    manualTab: false,
    _autoP: false,
    fournisseurs: [],
    expandedFour: new Set(),
  };

  await _reloadFournisseursCache(state);

  function render() {
    if (!state._autoP && !state.selectedContacts.size) {
      state._autoP = true;
      state.fournisseurs.forEach(f => (f.contacts || []).forEach(c => {
        if (c.is_principal) state.selectedContacts.add(f.id + ':' + c.id);
      }));
    }
    const filtered = state.search
      ? state.fournisseurs.filter(f => {
          const q = state.search.toLowerCase();
          return (f.nom || '').toLowerCase().includes(q)
            || (f.ville || '').toLowerCase().includes(q)
            || (f.contacts || []).some(c => (c.nom || '').toLowerCase().includes(q));
        })
      : state.fournisseurs;

    let html = '<h3>Ajouter un fournisseur</h3>' +
      '<div style="display:flex;gap:6px;margin-bottom:12px">' +
      '<button type="button" class="btn ' + (state.manualTab ? 'btn-ghost' : 'btn-accent') + ' btn-sm" id="tab-base">Depuis la base</button>' +
      '<button type="button" class="btn ' + (state.manualTab ? 'btn-accent' : 'btn-ghost') + ' btn-sm" id="tab-manual">Saisie manuelle</button>' +
      '</div>';

    if (state.manualTab) {
      html += '<div class="field"><label>Nom fournisseur / societe</label><input id="m-nom-manual"></div>' +
        '<div class="field"><label>Email</label><input type="email" id="m-mail-manual"></div>' +
        '<div class="field"><label>Langue AO</label>' +
        '<select id="m-langue-manual"><option value="fr">Francais</option><option value="en">English</option></select></div>';
    } else {
      html += '<div class="field"><input id="m-search" placeholder="Rechercher fournisseur, ville, contact..." value="' + escAttr(state.search) + '" autocomplete="off"></div>' +
        '<div style="max-height:400px;overflow:auto;border:1px solid var(--border);border-radius:10px;padding:6px" id="m-list">';
      if (!filtered.length) {
        html += '<div style="padding:20px;color:var(--muted);text-align:center">Aucun fournisseur.</div>';
      } else {
        filtered.forEach(f => {
          const contacts = f.contacts || [];
          const fscBadge = f.has_fsc ? '<span style="font-size:10px;background:rgba(52,211,153,.15);color:var(--ok);padding:1px 6px;border-radius:6px;margin-left:6px">FSC</span>' : '';
          const villeBadge = f.ville ? '<span style="font-size:10px;color:var(--muted);margin-left:8px">' + escHtml(f.ville) + '</span>' : '';
          html += '<div class="four-row" style="padding:8px 10px;border-bottom:1px solid var(--border)">' +
            '<div style="display:flex;align-items:center;justify-content:space-between">' +
            '<div style="font-weight:600">' + escHtml(f.nom) + fscBadge + villeBadge + '</div>' +
            '<button type="button" class="btn btn-ghost btn-sm" data-quickadd="' + f.id + '" style="font-size:11px;padding:2px 8px" title="Ajouter un contact rapidement">+ Contact</button>' +
            '</div>';
          if (!contacts.length) {
            html += '<div style="font-size:11px;color:var(--muted);margin:4px 0 2px">Aucun contact enregistre — clique + Contact pour en ajouter.</div>';
          } else {
            contacts.forEach(c => {
              const key = f.id + ':' + c.id;
              const emails = (c.emails || []).join(', ');
              const principal = c.is_principal ? '<span style="font-size:10px;background:rgba(34,211,238,.15);color:var(--accent);padding:1px 6px;border-radius:6px;margin-left:4px">★</span>' : '';
              html += '<label style="display:flex;align-items:center;gap:8px;padding:5px 0;cursor:pointer;font-size:12px">' +
                '<input type="checkbox" data-contact-key="' + escAttr(key) + '"' + (state.selectedContacts.has(key) ? ' checked' : '') + ' style="width:14px;height:14px">' +
                '<span><strong>' + escHtml(c.nom || '—') + '</strong>' + principal +
                (emails ? ' <span style="color:var(--muted)">· ' + escHtml(emails) + '</span>' : '') +
                ' <span style="color:var(--muted)">· ' + (c.langue || 'fr').toUpperCase() + '</span></span></label>';
            });
          }
          html += '</div>';
        });
      }
      html += '</div>';
      html += '<p style="font-size:11px;color:var(--muted);margin-top:8px">Astuce : cliquer <strong>+ Contact</strong> sur un fournisseur pour lui ajouter un contact sans passer par Parametres.</p>';
    }

    html += '<div class="modal-actions" style="margin-top:14px">' +
      '<button class="btn btn-ghost" id="m-cancel">Annuler</button>' +
      '<button class="btn btn-accent" id="m-ok">Ajouter</button></div>';

    box.innerHTML = html;

    document.getElementById('tab-base').onclick = () => { state.manualTab = false; render(); };
    document.getElementById('tab-manual').onclick = () => { state.manualTab = true; render(); };

    if (!state.manualTab) {
      const s = document.getElementById('m-search');
      if (s) s.addEventListener('input', () => { state.search = s.value; render(); });
      box.querySelectorAll('[data-contact-key]').forEach(cb => {
        cb.onchange = () => {
          const k = cb.dataset.contactKey;
          if (cb.checked) state.selectedContacts.add(k);
          else state.selectedContacts.delete(k);
        };
      });
      box.querySelectorAll('[data-quickadd]').forEach(btn => {
        btn.onclick = () => {
          const fid = parseInt(btn.dataset.quickadd, 10);
          _quickAddContact(fid, box, async () => {
            await _reloadFournisseursCache(state);
            render();
          });
        };
      });
    }

    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      if (state.manualTab) {
        const nom = document.getElementById('m-nom-manual').value.trim();
        const email = document.getElementById('m-mail-manual').value.trim();
        const langue = document.getElementById('m-langue-manual').value;
        if (!nom || !email) { showToast('Nom et email obligatoires.', 'danger'); return; }
        try {
          await api('/api/ao/' + S.ao.id + '/fournisseurs', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nom_fournisseur: nom, email_contact: email, langue })
          });
          closeModal();
          await loadDetail(S.ao.id);
          showToast('Fournisseur ajoute', 'success');
        } catch (e) { showToast(e.message || 'Erreur', 'danger'); }
      } else {
        if (!state.selectedContacts.size) { showToast('Selectionne au moins un contact.', 'danger'); return; }
        let ok = 0, ko = 0;
        for (const key of state.selectedContacts) {
          const [fId, cId] = key.split(':').map(Number);
          const f = state.fournisseurs.find(x => x.id === fId); if (!f) continue;
          const c = (f.contacts || []).find(x => x.id === cId); if (!c) continue;
          const email = (c.emails && c.emails[0]) || '';
          if (!email) { ko++; continue; }
          const label = f.nom + ' — ' + (c.nom || '');
          const langue = c.langue || f.langue_default || 'fr';
          try {
            await api('/api/ao/' + S.ao.id + '/fournisseurs', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                nom_fournisseur: label, email_contact: email, langue,
                fournisseur_id: fId, fournisseur_contact_id: cId
              })
            });
            ok++;
          } catch (e) { ko++; }
        }
        closeModal();
        await loadDetail(S.ao.id);
        showToast(ok + ' ajoute(s)' + (ko ? ', ' + ko + ' en echec' : ''), ok ? 'success' : 'danger');
      }
    };
  }
  ov.appendChild(box); m.appendChild(ov);
  render();
}

async function openEditFournisseurAoModal(fourniId) {
  const f = (S.detail && S.detail.fournisseurs || []).find(x => x.id === fourniId);
  if (!f) return;
  const m = document.getElementById('mroot'); if (!m) return;
  m.innerHTML = '';
  const ov = document.createElement('div'); ov.className = 'modal-overlay';
  const box = document.createElement('div'); box.className = 'modal';
  box.innerHTML = '<h3>Modifier ' + escHtml(f.nom_fournisseur) + '</h3>' +
    '<p style="font-size:12px;color:var(--muted);margin-top:-6px;margin-bottom:12px">Ne concerne que cet AO. Pour éditer globalement, va dans Paramètres.</p>' +
    '<div class="field"><label>Nom / société affiché</label><input id="me-nom" value="' + escAttr(f.nom_fournisseur || '') + '"></div>' +
    '<div class="field"><label>Email</label><input type="email" id="me-mail" value="' + escAttr(f.email_contact || '') + '"></div>' +
    '<div class="field"><label>Langue</label>' +
    '<select id="me-langue"><option value="fr"' + (f.langue !== 'en' ? ' selected' : '') + '>Français</option>' +
    '<option value="en"' + (f.langue === 'en' ? ' selected' : '') + '>English</option></select></div>' +
    '<div class="modal-actions"><button class="btn btn-ghost" id="me-cancel">Annuler</button>' +
    '<button class="btn btn-accent" id="me-ok">Enregistrer</button></div>';
  ov.appendChild(box); m.appendChild(ov);
  document.getElementById('me-cancel').onclick = closeModal;
  document.getElementById('me-ok').onclick = async () => {
    const body = {
      nom_fournisseur: document.getElementById('me-nom').value.trim(),
      email_contact: document.getElementById('me-mail').value.trim(),
      langue: document.getElementById('me-langue').value,
    };
    if (!body.nom_fournisseur || !body.email_contact) {
      showToast('Nom et email obligatoires.', 'danger'); return;
    }
    try {
      await api('/api/ao/' + S.ao.id + '/fournisseurs/' + fourniId, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      closeModal();
      await loadDetail(S.ao.id);
      showToast('Modifié', 'success');
    } catch (e) { showToast(e.message || 'Erreur', 'danger'); }
  };
}


async function saveReponsePricing(reponseId, patch) {
  const aoId = S.ao && S.ao.id;
  if (!aoId || !reponseId) return null;
  const updated = await api('/api/ao/'+aoId+'/reponses/'+reponseId, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(patch)
  });
  if (S.comparaison && S.comparaison.rows) {
    const row = S.comparaison.rows.find(x => String(x.reponse_id) === String(reponseId));
    if (row) {
      Object.assign(row, {
        coef: updated.coef,
        devise_prix_devis: updated.devise_prix_devis,
        prix_vente: updated.prix_vente,
        prix_au_mille: updated.prix_au_mille,
        prix_calcule: updated.prix_calcule
      });
      const pvCell = document.querySelector('[data-pv="'+reponseId+'"]');
      if (pvCell) pvCell.textContent = formatMoney(updated.prix_vente, updated.devise_prix_devis);
    }
  }
  return updated;
}

function renderComparaison() {
  const c = S.comparaison;
  if (!c) return '<div class="card" style="color:var(--muted)">Chargement…</div>';
  const rows = c.rows || [];
  if (!rows.length) {
    const nLignes = (c.lignes || []).length;
    const nFournis = (c.fournisseurs || []).length;
    let msg = 'Ajoutez des lignes et des fournisseurs à cet appel d\'offre.';
    if (!nLignes) msg = 'Ajoutez des lignes produit à cet appel d\'offre.';
    else if (!nFournis) msg = 'Ajoutez des fournisseurs invités.';
    return '<div class="card empty-state"><strong>Demandes de prix</strong>'+escHtml(msg)+'</div>';
  }
  let bestMille = null;
  rows.forEach(r => {
    if (r.prix_au_mille != null && (bestMille == null || r.prix_au_mille < bestMille)) bestMille = r.prix_au_mille;
  });
  const head = '<tr>'+
    '<th>Client</th><th>Réf. produit</th><th>Frontal</th><th>Adhésif</th>'+
    '<th>Étiq. / bobine</th><th>Qté étiquettes</th><th>Fournisseur</th>'+
    '<th>Quotation</th><th>Devise</th><th>Unité quot.</th>'+
    '<th>Prix calculé</th><th>Prix / mille</th><th>Coef</th>'+
    '<th>Devise devis</th><th>Prix de vente</th></tr>';
  let body = '';
  rows.forEach(r => {
    const best = bestMille != null && r.prix_au_mille === bestMille;
    const cls = best ? ' comp-cell-best' : '';
    const devF = (r.devise || 'EUR').toUpperCase();
    const devD = (r.devise_prix_devis || 'EUR').toUpperCase();
    const rid = r.reponse_id;
    const noRep = rid == null || rid === '';
    const dis = noRep ? ' disabled' : '';
    body += '<tr data-reponse-id="'+escAttr(rid||'')+'">'+
      '<td class="txt-left">'+escHtml(r.client_nom||'—')+'</td>'+
      '<td class="ref">'+escHtml(r.ref_produit)+'</td>'+
      '<td class="txt-left" style="font-size:11px;color:var(--text2)">'+escHtml(r.frontal||'—')+'</td>'+
      '<td class="txt-left" style="font-size:11px;color:var(--text2)">'+escHtml(r.adhesif||'—')+'</td>'+
      '<td>'+formatInt(r.etiquettes_par_bobine)+'</td>'+
      '<td>'+formatInt(r.quantite_etiquettes)+'</td>'+
      '<td class="txt-left">'+escHtml(r.nom_fournisseur||'')+'</td>'+
      '<td class="'+cls.trim()+'">'+formatMoney(r.quotation, devF)+'</td>'+
      '<td>'+escHtml(devF)+'</td>'+
      '<td>'+'<select class="inp-unite-quot" data-rep="'+escAttr(rid||'')+'"'+dis+' style="font-size:11px;padding:2px 4px">'+'<option value="mille"'+(r.unite_quotation==='mille'?' selected':'')+'>Mille</option>'+'<option value="bobine"'+(r.unite_quotation==='bobine'?' selected':'')+'>Bobine</option>'+'</select>'+(r.unite_manuel ? ' <span style="font-size:9px;padding:1px 5px;background:var(--warning-bg,rgba(234,179,8,.15));color:var(--warning,#a16207);border-radius:4px;font-weight:600">manuel</span>' : '')+'</td>'+
      '<td>'+formatMoney(r.prix_calcule, devF)+'</td>'+
      '<td class="'+cls.trim()+'">'+formatMoney(r.prix_au_mille, devF)+'</td>'+
      '<td><input type="number" step="0.01" min="0.01" class="inp-coef" data-rep="'+escAttr(rid||'')+'" value="'+escAttr(r.coef != null ? r.coef : 1)+'"'+dis+'></td>'+
      '<td><select class="inp-dev-devis" data-rep="'+escAttr(rid||'')+'"'+dis+'>'+
        '<option value="EUR"'+(devD==='EUR'?' selected':'')+'>EUR</option>'+
        '<option value="USD"'+(devD==='USD'?' selected':'')+'>USD</option>'+
      '</select></td>'+
      '<td class="'+cls.trim()+'" data-pv="'+escAttr(rid)+'">'+formatMoney(r.prix_vente, devD)+'</td>'+
      '</tr>';
  });
  const fxNote = c.eur_usd_rate
    ? '<p style="font-size:11px;color:var(--muted);margin-top:10px">Taux EUR/USD : '+Number(c.eur_usd_rate).toLocaleString('fr-FR', {maximumFractionDigits:4})+' — conversion appliquée sur le prix de vente si les devises diffèrent.</p>'
    : '';
  return '<div class="card" style="overflow:auto"><table class="comp-table"><thead>'+head+'</thead><tbody>'+body+'</tbody></table>'+fxNote+'</div>';
}

function renderMessagerieContent(container) {
  const fournis = S.detail.fournisseurs || [];
  let sel = '<select id="msg-fourni-sel"><option value="">— Fournisseur —</option>';
  fournis.forEach(f => {
    sel += '<option value="'+f.id+'"'+(S.messages_fourni==f.id?' selected':'')+'>'+escHtml(f.nom_fournisseur)+'</option>';
  });
  sel += '</select>';
  let bubbles = '';
  (S.messages||[]).forEach(m => {
    const cls = m.expediteur === 'interne' ? 'interne' : 'fournisseur';
    bubbles += '<div class="bubble '+cls+'"><div class="meta">'+escHtml(m.auteur_nom||m.expediteur)+' · '+escHtml(m.date)+'</div>'+escHtml(m.message)+'</div>';
  });
  container.innerHTML = '<div class="card"><div class="field"><label>Fournisseur</label>'+sel+'</div>'+
    '<div class="msg-list" style="display:flex;flex-direction:column">'+bubbles+'</div>'+
    '<div class="field"><label>Message</label><textarea id="msg-body" rows="3"></textarea></div>'+
    '<button class="btn btn-accent" type="button" id="btn-send-msg">Envoyer</button></div>';
}

function renderMessagerie() {
  return '<div id="tab-messages"></div>';
}

function renderDocuments() {
  const aoId = S.ao.id;
  return api('/api/ao/'+aoId+'/pieces-jointes').then(pjs => {
    let rows = (pjs||[]).map(pj => '<tr><td>'+escHtml(pj.filename)+'</td><td>'+Math.round((pj.taille_octets||0)/1024)+' Ko</td><td>'+escHtml(pj.date)+'</td>'+
      '<td><a class="btn btn-ghost btn-sm" href="/api/ao/'+aoId+'/pieces-jointes/'+pj.id+'/download">Télécharger</a> '+
      '<button class="btn btn-ghost btn-sm btn-del-pj" data-id="'+pj.id+'">Supprimer</button></td></tr>').join('');
    return '<div class="card"><p style="font-size:12px;color:var(--muted);margin-bottom:12px">Taille max. 10 Mo par fichier.</p>'+
      '<input type="file" id="pj-file" style="margin-bottom:10px"><button class="btn btn-accent btn-sm" id="btn-pj-upload">Ajouter un document</button>'+
      '<table class="data-table" style="margin-top:16px"><thead><tr><th>Fichier</th><th>Taille</th><th>Date</th><th></th></tr></thead><tbody>'+
      (rows||'<tr><td colspan="4" style="color:var(--muted)">Aucun document</td></tr>')+'</tbody></table></div>';
  });
}

function bindListEvents() {
  document.getElementById('btn-new-ao')?.addEventListener('click', openCreateAoWizard);
  document.querySelectorAll('.filter-tab').forEach(b => b.addEventListener('click', () => { S.filtre = b.dataset.f; render(); }));
  document.querySelectorAll('.btn-view').forEach(b => b.addEventListener('click', () => openDetail(parseInt(b.dataset.id,10))));
  document.querySelectorAll('.btn-del-ao').forEach(b => b.addEventListener('click', (e) => {
    e.stopPropagation();
    openModalConfirmDelete(parseInt(b.dataset.id,10), b.dataset.ref, b.dataset.statut);
  }));
  document.querySelectorAll('.btn-dup-ao').forEach(b => b.addEventListener('click', (e) => {
    e.stopPropagation();
    openModalDuplicate(parseInt(b.dataset.id,10), b.dataset.ref, b.dataset.titre);
  }));
}

function bindDetailEvents() {
  document.getElementById('btn-back')?.addEventListener('click', backToList);
  document.getElementById('bc-list')?.addEventListener('click', e => { e.preventDefault(); backToList(); });
  document.querySelectorAll('.detail-tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
  // AO params panel : transport % + EUR/USD
  (function bindAoParamsPanel(){
    const inpT = document.getElementById('app-transport');
    const help = document.getElementById('app-transport-help');
    if (inpT) {
      inpT.addEventListener('input', () => { if (help) help.textContent = formatTransportHelper(inpT.value); });
      inpT.addEventListener('change', () => {
        const v = Math.max(0, Math.min(100, parseFloat(inpT.value) || 0));
        inpT.value = v;
        if (S.ao) saveAoTransport(S.ao.id, v);
      });
    }
    const inpU = document.getElementById('app-eur-usd');
    if (inpU) {
      loadEurUsdRate();
      inpU.addEventListener('change', () => {
        const v = parseFloat(inpU.value);
        if (!isNaN(v) && v > 0) saveEurUsdRate(v);
      });
    }
  })();
  document.querySelectorAll('.detail-hdr .btn-nav-prev, .detail-hdr .btn-nav-next').forEach(btn => {
    btn.addEventListener('click', () => {
      const arr = filteredAos();
      const idx = arr.findIndex(x => String(x.id) === String(S.ao.id));
      if (idx < 0) return;
      const target = btn.classList.contains('btn-nav-prev') ? arr[idx-1] : arr[idx+1];
      if (target) openDetail(target.id);
    });
  });
  document.getElementById('btn-envoyer')?.addEventListener('click', () => {
    const n = (S.detail.fournisseurs||[]).length;
    openModalConfirmEnvoi(n);
  });
  document.getElementById('btn-cloturer')?.addEventListener('click', openCloturerAoModal);
  document.getElementById('btn-add-ligne')?.addEventListener('click', () => openModalLigne(null));
  document.querySelectorAll('.btn-edit-ligne').forEach(b => {
    b.addEventListener('click', () => {
      const l = (S.detail.lignes||[]).find(x => x.id == b.dataset.id);
      if (l) openModalLigne(l);
    });
  });
  document.querySelectorAll('.btn-del-ligne').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Supprimer cette ligne ?')) return;
    try {
      await api('/api/ao/'+S.ao.id+'/lignes/'+b.dataset.id, {method:'DELETE'});
      showToast('Ligne supprimée.', 'success');
      await loadDetail(S.ao.id); render();
    } catch(e) { showToast(e.message, 'danger'); }
  }));
  document.getElementById('btn-add-f')?.addEventListener('click', openAddFournisseurModalV2);
  document.querySelectorAll('.btn-copy').forEach(b => b.addEventListener('click', () => {
    const f = (S.detail.fournisseurs||[]).find(x => x.token === b.dataset.token);
    const url = (BASE_URL||location.origin).replace(/\/$/,'')+'/portail/ao/'+b.dataset.token;
    navigator.clipboard.writeText(url).then(() => showToast('Lien copié.', 'success')).catch(() => showToast('Copie impossible', 'danger'));
  }));
  document.querySelectorAll('.btn-msg').forEach(b => b.addEventListener('click', () => {
    S.messages_fourni = parseInt(b.dataset.id, 10);
    setTab('messages');
  }));
  document.querySelectorAll('.btn-edit-f').forEach(b => {
    b.onclick = () => openEditFournisseurAoModal(parseInt(b.dataset.id, 10));
  });
  document.querySelectorAll('.btn-del-f').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Supprimer ce fournisseur ?')) return;
    try {
      await api('/api/ao/'+S.ao.id+'/fournisseurs/'+b.dataset.id, {method:'DELETE'});
      showToast('Fournisseur supprimé.', 'success');
      await loadDetail(S.ao.id); render();
    } catch(e) { showToast(e.message, 'danger'); }
  }));
  document.getElementById('msg-fourni-sel')?.addEventListener('change', e => {
    S.messages_fourni = parseInt(e.target.value, 10) || null;
    if (S.messages_fourni) loadMessages(S.ao.id, S.messages_fourni).then(() => render());
  });
  document.getElementById('btn-send-msg')?.addEventListener('click', async () => {
    const msg = document.getElementById('msg-body').value.trim();
    if (!msg) return;
    try {
      await api('/api/ao/'+S.ao.id+'/fournisseurs/'+S.messages_fourni+'/messages',
        {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: msg})});
      document.getElementById('msg-body').value = '';
      showToast('Message envoyé.', 'success');
      await loadMessages(S.ao.id, S.messages_fourni); render();
    } catch(e) { showToast(e.message, 'danger'); }
  });
  document.getElementById('btn-pj-upload')?.addEventListener('click', async () => {
    const f = document.getElementById('pj-file').files[0];
    if (!f) { showToast('Choisissez un fichier.', 'danger'); return; }
    if (f.size > 10*1024*1024) { showToast('Fichier trop volumineux (max 10 Mo).', 'danger'); return; }
    const fd = new FormData();
    fd.append('file', f);
    try {
      await api('/api/ao/'+S.ao.id+'/pieces-jointes', {method:'POST', body: fd});
      showToast('Document ajouté.', 'success');
      render();
    } catch(e) { showToast(e.message, 'danger'); }
  });
  document.querySelectorAll('.btn-del-pj').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Supprimer ce document ?')) return;
    try {
      await api('/api/ao/'+S.ao.id+'/pieces-jointes/'+b.dataset.id, {method:'DELETE'});
      showToast('Document supprimé.', 'success');
      render();
    } catch(e) { showToast(e.message, 'danger'); }
  }));
  document.querySelectorAll('.inp-unite-quot').forEach(sel => {
    sel.addEventListener('change', async () => {
      const rid = sel.dataset.rep;
      if (!rid) return;
      try {
        await saveReponsePricing(rid, {unite_quotation: sel.value});
        // refetch entire comparaison pour recalculer les prix
        if (S.ao) { await loadComparaison(S.ao.id); render(); }
      } catch(e) { showToast(e.message || 'Erreur unite.', 'danger'); }
    });
  });
  document.querySelectorAll('.inp-coef').forEach(inp => {
    inp.addEventListener('change', async () => {
      const rid = inp.dataset.rep;
      const v = parseFloat(inp.value);
      if (!rid || isNaN(v) || v <= 0) { showToast('Coefficient invalide.', 'danger'); return; }
      try {
        await saveReponsePricing(rid, {coef: v});
        showToast('Coefficient enregistré.', 'success');
      } catch(e) { showToast(e.message, 'danger'); }
    });
  });
  document.querySelectorAll('.inp-dev-devis').forEach(sel => {
    sel.addEventListener('change', async () => {
      const rid = sel.dataset.rep;
      if (!rid) return;
      try {
        await saveReponsePricing(rid, {devise_prix_devis: sel.value});
        showToast('Devise enregistrée.', 'success');
      } catch(e) { showToast(e.message, 'danger'); }
    });
  });
}

function render() {
  const ae = document.activeElement;
  const focusId = ae?.id;
  const caretStart = ae?.selectionStart;
  const caretEnd = ae?.selectionEnd;
  const scrollEl = document.getElementById('scroll-area');
  const scrollTop = scrollEl ? scrollEl.scrollTop : 0;

  const root = document.getElementById('root');
  const isLight = document.body.classList.contains('light');
  const mob = aoMobileTitle();
  const navHtml = renderAoSidebarNavHtml();

  root.innerHTML =
    '<div class="sidebar-overlay" id="sb-overlay"></div>'+
    '<nav class="sidebar"><div class="logo"><div class="logo-brand">My<span>AO</span></div><div class="logo-sub">by SIFA</div></div>'+
    '<div class="sidebar-nav">'+navHtml+'</div>'+
    '<div class="sidebar-bottom">'+
    '<button type="button" class="nav-btn back-mysifa" id="btn-home">← Retour <span class="wm">My<span>Sifa</span></span></button>'+
    renderUserChipHtml()+
    '<button type="button" class="support-btn" id="btn-support"><span class="support-ico" id="support-ico"></span><span>Contacter le support</span></button>'+
    '<button type="button" class="theme-btn" id="btn-theme">'+icon(isLight?'sun':'moon',16)+' '+(isLight?'Mode clair':'Mode sombre')+'</button>'+
    '<button type="button" class="logout-btn" id="btn-logout">'+icon('log-out',14)+' Déconnexion</button>'+
    '<div class="version">MyAO __V_LABEL__</div></div></nav>'+
    '<div class="main"><div class="mobile-topbar">'+
    '<button type="button" class="mobile-menu-btn" id="btn-menu">'+icon('menu',20)+'</button>'+
    '<div><div class="mobile-topbar-title">'+escHtml(mob.title)+'</div><div class="mobile-topbar-sub">'+escHtml(mob.sub)+'</div></div>'+
    '<button type="button" class="mobile-home-btn" id="btn-home-m">'+icon('home',20)+'</button></div>'+
    '<div class="scroll-area" id="scroll-area"></div></div>';

  document.getElementById('sb-overlay').onclick = closeSidebar;
  document.getElementById('btn-menu').onclick = toggleSidebar;
  document.getElementById('btn-home').onclick = () => location.href = '/';
  document.getElementById('btn-home-m').onclick = () => location.href = '/';
  document.getElementById('btn-theme').onclick = () => { if (window.MySifaTheme) MySifaTheme.toggleMode(); render(); };
  document.getElementById('btn-logout').onclick = async () => { await api('/api/auth/logout', {method:'POST'}); location.href = '/'; };
  document.getElementById('btn-support').onclick = openSupport;
  const supportIco = document.getElementById('support-ico');
  if (supportIco && window.MySifaSupport && window.MySifaSupport.iconSvg) {
    try { supportIco.innerHTML = window.MySifaSupport.iconSvg(); } catch(e) {}
  }
  document.getElementById('user-chip')?.addEventListener('click', () => location.href = '/profil');
  document.querySelectorAll('.sidebar .nav-btn[data-section]').forEach(b => {
    b.onclick = () => goToAoSection(b.dataset.section);
  });

  const area = document.getElementById('scroll-area');
  if (S.section === 'produits') {
    if (S.produitView === 'form' && S.produitForm) {
      area.innerHTML = renderProduitForm();
      bindProduitFormEvents();
    } else {
      area.innerHTML = renderProduits();
      bindProduitsEvents();
    }
  } else if (S.view === 'list') {
    area.innerHTML = renderList();
    bindListEvents();
  } else if (S.detail && S.ao) {
    let tabHtml = renderDetailHeader();
    if (S.tab === 'lignes') tabHtml += renderLignes();
    else if (S.tab === 'fournisseurs') tabHtml += renderFournisseurs();
    else if (S.tab === 'comparaison') tabHtml += renderComparaison();
    else if (S.tab === 'messages') tabHtml += '<div id="tab-messages-wrap"></div>';
    else if (S.tab === 'documents') tabHtml += '<div id="tab-docs">Chargement…</div>';
    area.innerHTML = tabHtml;
    bindDetailEvents();
    if (S.tab === 'messages') {
      const wrap = document.getElementById('tab-messages-wrap');
      if (wrap) renderMessagerieContent(wrap);
      bindDetailEvents();
    } else if (S.tab === 'documents') {
      renderDocuments().then(html => {
        const el = document.getElementById('tab-docs');
        if (el) { el.outerHTML = html; bindDetailEvents(); }
      });
    }
  } else {
    area.innerHTML = '<div class="card empty-state"><strong>Chargement…</strong></div>';
  }

  const newScroll = document.getElementById('scroll-area');
  if (newScroll) newScroll.scrollTop = scrollTop;
  if (focusId) {
    const el = document.getElementById(focusId);
    if (el) {
      el.focus();
      if (caretStart != null) try { el.setSelectionRange(caretStart, caretEnd); } catch(e) {}
    }
  }
}

""" + AO_PRODUIT_FORM_JS + r"""
(async function init() {
  const embedded = S.user && S.user.id;
  try {
    const me = await api('/api/auth/me');
    if (me && me.id) {
      S.user = me;
    } else if (!embedded) {
      redirectToLogin();
      return;
    }
  } catch (e) {
    if (e.status === 401 || !embedded) {
      redirectToLogin();
      return;
    }
  }
  const u = S.user || {};
  if (u.id) {
    window.__MYSIFA_UID__ = u.id;
    window.__MYSIFA_NOM__ = u.nom || '';
    window.__MYSIFA_ROLE__ = u.role || '';
    window.__MYSIFA_USER__ = { nom: u.nom || '', role: u.role || '' };
  }
  if (window._CW && typeof window._CW.syncUser === 'function') window._CW.syncUser();
  if (window.MySifaDock && typeof window.MySifaDock.bootPageWidgets === 'function') {
    window.MySifaDock.bootPageWidgets();
  }
  const loads = await Promise.allSettled([loadList(), loadCarnet(), loadProduits(), loadMatieresForProduit()]);
  const labels = ['appels d\'offre', 'carnet fournisseurs', 'produits', 'matières'];
  const errors = [];
  loads.forEach((res, i) => {
    if (res.status === 'rejected') {
      if (res.reason && res.reason.status === 401) errors.push({ auth: true });
      else errors.push({ msg: (res.reason && res.reason.message) || labels[i] });
    }
  });
  if (errors.some(x => x.auth)) {
    redirectToLogin();
    return;
  }
  if (errors.length) {
    showToast('Chargement partiel : ' + errors.map(x => x.msg).join(' · '), 'danger');
    if (!S.aos) S.aos = [];
    if (!S.carnet) S.carnet = [];
    if (!S.produits) S.produits = [];
    if (!S.matieres) S.matieres = {};
  }
  render();
})();
</script>
<script src="/static/mysifa_impersonate.js"></script>
</body>
</html>"""
