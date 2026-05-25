"""MySifa — Appels d'offre (page interne /ao)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, BASE_URL
from app.services.auth_service import get_current_user
from app.web.access_denied import access_denied_response

router = APIRouter()

_AO_ROLES = frozenset({"superadmin", "direction", "administration"})


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
.btn-accent{background:var(--accent);color:#0a0e17}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn-danger{background:var(--danger);color:#fff}
.btn-sm{padding:6px 12px;font-size:12px}
.filter-tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.filter-tab{padding:8px 14px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
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
.detail-tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}
.detail-tab{padding:8px 14px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.detail-tab.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.breadcrumb{font-size:12px;color:var(--muted);margin-bottom:12px}
.breadcrumb a{color:var(--accent);cursor:pointer;text-decoration:none}
.detail-hdr{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:8px}
.detail-hdr h2{font-size:18px;font-weight:800}
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
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}
.comp-table{width:100%;border-collapse:collapse;font-size:12px}
.comp-table th,.comp-table td{padding:10px 8px;border:1px solid var(--border);text-align:center}
.comp-table th{background:var(--bg);font-size:10px;text-transform:uppercase;color:var(--muted)}
.comp-table td.ref{text-align:left;font-weight:600}
.comp-cell-best{background:var(--accent-bg);color:var(--accent);font-weight:700}
.msg-list{display:flex;flex-direction:column;gap:10px;max-height:360px;overflow-y:auto;margin-bottom:16px}
.bubble{max-width:85%;padding:12px 14px;border-radius:12px;font-size:13px;line-height:1.5}
.bubble.interne{align-self:flex-end;margin-left:auto;background:var(--accent-bg);border:1px solid var(--accent)}
.bubble.fournisseur{align-self:flex-start;background:var(--card);border:1px solid var(--border)}
.bubble .meta{font-size:11px;color:var(--muted);margin-bottom:4px}
#toast{position:fixed;bottom:20px;right:20px;padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;z-index:999;display:none;max-width:360px}
#toast.show{display:block}
#toast.success{background:var(--success);color:#0a0e17}
#toast.danger{background:var(--danger);color:#fff}
#toast.info{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent)}
#toast.warn{background:rgba(251,191,36,.2);color:var(--warn);border:1px solid var(--warn)}
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
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<script>window.__MYSIFA_APP__='ao';</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js"></script>
<script src="/static/chat_widget_v2.js"></script>
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
  produits: [],
  produitsSearch: '',
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
    sun: '<circle cx="12" cy="12" r="5"/>',
    moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
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

function buildAoSidebarNavStructure() {
  const sec = S.section;
  return [
    {kind:'btn', section:'dashboard', icon:'grid', label:'Tableau de bord'},
    {kind:'btn', section:'ao', icon:'clipboard', label:'Appel d\'offre'},
    {kind:'sep', label:'Contact'},
    {kind:'btn', section:'contact_fournisseur', icon:'truck', label:'Fournisseur', sub:true},
    {kind:'btn', section:'produits', icon:'package', label:'Produits'},
  ].map(n => (n.kind === 'btn' ? {...n, active: sec === n.section} : n));
}

function aoMobileTitle() {
  const m = {
    dashboard: ['Tableau de bord', 'Vue d\'ensemble'],
    ao: S.view === 'detail' && S.ao ? [S.ao.reference, 'Appel d\'offre'] : ['Appels d\'offre', 'Appel d\'offre'],
    contact_fournisseur: ['Fournisseurs', 'Contacts'],
    produits: ['Produits', 'Référentiel'],
  };
  const x = m[S.section] || ['MyAO', 'Appels d\'offre'];
  return {title: x[0], sub: x[1]};
}

function goToAoSection(section) {
  if (S.section === section) { closeSidebar(); return; }
  if (S.polling) { clearInterval(S.polling); S.polling = null; }
  S.section = section;
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

function renderDashboard() {
  const aos = S.aos || [];
  const nb = (s) => aos.filter(a => a.statut === s).length;
  const recent = aos.slice(0, 8);
  let rows = '';
  recent.forEach(a => {
    rows += '<tr><td><strong>'+escHtml(a.reference)+'</strong></td><td>'+escHtml(a.titre)+'</td><td>'+statutBadge(a.statut)+'</td>'+
      '<td><button class="btn btn-ghost btn-sm btn-view" data-id="'+a.id+'">Voir</button></td></tr>';
  });
  return '<div class="page-hdr"><h1>Tableau de bord</h1></div>'+
    '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-bottom:20px">'+
    '<div class="card" style="margin:0"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600">Total</div><div style="font-size:24px;font-weight:800;margin-top:6px">'+aos.length+'</div></div>'+
    '<div class="card" style="margin:0"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600">Brouillon</div><div style="font-size:24px;font-weight:800;margin-top:6px">'+nb('brouillon')+'</div></div>'+
    '<div class="card" style="margin:0"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600">Envoyée</div><div style="font-size:24px;font-weight:800;margin-top:6px">'+nb('envoyee')+'</div></div>'+
    '<div class="card" style="margin:0"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600">Clôturée</div><div style="font-size:24px;font-weight:800;margin-top:6px">'+nb('cloturee')+'</div></div>'+
    '</div>'+
    '<div class="page-hdr" style="margin-bottom:12px"><h2 style="font-size:16px;font-weight:700">Appels d\'offre récents</h2></div>'+
    (recent.length ? '<div class="card"><table class="data-table"><thead><tr><th>Référence</th><th>Titre</th><th>Statut</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>' :
    '<div class="card empty-state"><strong>Aucun appel d\'offre</strong>Créez un premier appel d\'offre depuis l\'onglet Appel d\'offre.</div>');
}

function renderSectionPlaceholder(title, hint) {
  return '<div class="page-hdr"><h1>'+escHtml(title)+'</h1></div>'+
    '<div class="card empty-state"><strong>'+escHtml(title)+'</strong>'+escHtml(hint)+'</div>';
}

function renderCarnet() {
  const list = S.carnet || [];
  let rows = '';
  list.forEach(c => {
    rows += '<tr><td>'+escHtml(c.nom)+'</td><td>'+escHtml(c.email)+'</td><td>'+escHtml(c.pays||'—')+'</td><td>'+
      '<button class="btn btn-ghost btn-sm btn-edit-carnet" data-id="'+c.id+'">Modifier</button> '+
      '<button class="btn btn-ghost btn-sm btn-del-carnet" data-id="'+c.id+'">Supprimer</button></td></tr>';
  });
  const table = list.length
    ? '<div class="card"><table class="data-table"><thead><tr><th>Nom</th><th>Email</th><th>Pays</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>'
    : '<div class="card empty-state"><strong>Aucun fournisseur dans le carnet.</strong></div>';
  return '<div class="page-hdr"><h1>Carnet fournisseurs</h1>'+
    '<button class="btn btn-accent" type="button" id="btn-add-carnet">'+icon('plus',14)+' Ajouter</button></div>'+table;
}

function filteredProduits() {
  const q = (S.produitsSearch || '').trim().toLowerCase();
  if (!q) return S.produits || [];
  return (S.produits || []).filter(p => {
    const hay = ((p.ref || '') + ' ' + (p.designation || '')).toLowerCase();
    return hay.includes(q);
  });
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
      rows += '<tr><td>'+escHtml(p.ref)+'</td><td>'+escHtml(p.designation)+'</td><td>'+escHtml(p.unite||'unité')+'</td><td>'+
        '<button class="btn btn-ghost btn-sm btn-edit-produit" data-id="'+p.id+'">Modifier</button> '+
        '<button class="btn btn-ghost btn-sm btn-del-produit" data-id="'+p.id+'">Supprimer</button></td></tr>';
    });
    el.innerHTML = '<table class="data-table"><thead><tr><th>Référence</th><th>Désignation</th><th>Unité</th><th></th></tr></thead><tbody>'+rows+'</tbody></table>';
    el.querySelectorAll('.btn-edit-produit').forEach(b => {
      b.addEventListener('click', () => {
        const p = (S.produits||[]).find(x => String(x.id) === String(b.dataset.id));
        if (p) openModalProduit(p);
      });
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
    '<input type="search" id="produits-search" placeholder="Rechercher (référence, désignation…)" value="'+escAttr(S.produitsSearch||'')+'" style="width:100%;margin-bottom:14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px">'+
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
  document.getElementById('btn-add-produit')?.addEventListener('click', () => openModalProduit(null));
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
  S.modalData = edit ? {...edit} : {ref_produit:'',designation:'',quantite:'',unite:'unité',notes:''};
  renderModal();
}
function openModalFourni() {
  S.modal = 'fourni';
  S.modalData = {nom_fournisseur:'',email_contact:''};
  renderModal();
}
function openModalCarnetEntry(edit) {
  S.modal = 'carnet-entry';
  S.modalData = edit ? {...edit} : {nom:'', email:'', pays:'', notes:''};
  renderModal();
}
function openModalProduit(edit) {
  S.modal = 'produit-entry';
  S.modalData = edit ? {...edit} : {ref:'', designation:'', unite:'unité', notes:''};
  renderModal();
}
function openModalConfirmEnvoi(n) {
  S.modal = 'confirm-envoi';
  S.modalData = {n};
  renderModal();
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
      '<div class="form-row"><div class="field"><label>Quantité</label><input type="number" step="any" min="0" id="m-qte" value="'+escAttr(S.modalData.quantite)+'"></div>'+
      '<div class="field"><label>Unité</label><input id="m-unite" value="'+escAttr(S.modalData.unite||'unité')+'"></div></div>'+
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
          uniteEl.value = p.unite || 'unité';
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
            body: JSON.stringify({ref, designation, unite: body.unite, notes: body.notes})});
          await loadProduits();
        }
        closeModal(); showToast('Ligne enregistrée.', 'success');
        await loadDetail(S.ao.id); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'fourni') {
    let carnetOpts = '<option value="">— Saisie manuelle —</option>';
    (S.carnet||[]).forEach(c => {
      carnetOpts += '<option value="'+c.id+'">'+escHtml(c.nom)+' — '+escHtml(c.email)+'</option>';
    });
    box.innerHTML = '<h3>Ajouter un fournisseur</h3>'+
      '<div class="field"><label>Sélectionner depuis le carnet</label>'+
      '<select id="m-carnet-pick">'+carnetOpts+'</select></div>'+
      '<div id="m-fourni-form">'+
      '<div class="field"><label>Nom</label><input id="m-nom"></div>'+
      '<div class="field"><label>Email</label><input type="email" id="m-mail"></div></div>'+
      '<label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer;margin-bottom:14px">'+
      '<input type="checkbox" id="m-save-carnet"> Enregistrer dans le carnet</label>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Ajouter</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    const pickEl = document.getElementById('m-carnet-pick');
    const nomEl = document.getElementById('m-nom');
    const mailEl = document.getElementById('m-mail');
    const saveCb = document.getElementById('m-save-carnet');
    pickEl.onchange = () => {
      const id = pickEl.value;
      if (id) {
        const c = (S.carnet||[]).find(x => String(x.id) === String(id));
        if (c) {
          nomEl.value = c.nom || '';
          mailEl.value = c.email || '';
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
      if (!nom || !email) { showToast('Nom et email obligatoires.', 'danger'); return; }
      try {
        await api('/api/ao/'+S.ao.id+'/fournisseurs', {method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({nom_fournisseur: nom, email_contact: email})});
        const manual = !pickEl.value;
        if (manual && saveCb.checked) {
          await api('/api/ao/carnet-fournisseurs', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({nom, email})});
          await loadCarnet();
        }
        closeModal(); showToast('Fournisseur ajouté.', 'success');
        await loadDetail(S.ao.id); render();
      } catch(e) { showToast(e.message, 'danger'); }
    };
  } else if (S.modal === 'carnet-entry') {
    const editId = S.modalData.id;
    box.innerHTML = '<h3>'+(editId?'Modifier':'Ajouter')+' au carnet</h3>'+
      '<div class="field"><label>Nom</label><input id="m-c-nom" value="'+escAttr(S.modalData.nom||'')+'"></div>'+
      '<div class="field"><label>Email</label><input type="email" id="m-c-email" value="'+escAttr(S.modalData.email||'')+'"></div>'+
      '<div class="field"><label>Pays</label><input id="m-c-pays" value="'+escAttr(S.modalData.pays||'')+'"></div>'+
      '<div class="field"><label>Notes</label><textarea id="m-c-notes" rows="2">'+escHtml(S.modalData.notes||'')+'</textarea></div>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Enregistrer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const body = {
        nom: document.getElementById('m-c-nom').value.trim(),
        email: document.getElementById('m-c-email').value.trim(),
        pays: document.getElementById('m-c-pays').value.trim() || null,
        notes: document.getElementById('m-c-notes').value.trim() || null
      };
      if (!body.nom || !body.email) { showToast('Nom et email obligatoires.', 'danger'); return; }
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
  } else if (S.modal === 'produit-entry') {
    const editId = S.modalData.id;
    box.innerHTML = '<h3>'+(editId?'Modifier':'Ajouter')+' un produit</h3>'+
      '<div class="field"><label>Référence</label><input id="m-p-ref" value="'+escAttr(S.modalData.ref||'')+'"></div>'+
      '<div class="field"><label>Désignation</label><input id="m-p-des" value="'+escAttr(S.modalData.designation||'')+'"></div>'+
      '<div class="field"><label>Unité</label><input id="m-p-unite" value="'+escAttr(S.modalData.unite||'unité')+'"></div>'+
      '<div class="field"><label>Notes</label><textarea id="m-p-notes" rows="2">'+escHtml(S.modalData.notes||'')+'</textarea></div>'+
      '<div class="modal-actions"><button class="btn btn-ghost" id="m-cancel">Annuler</button><button class="btn btn-accent" id="m-ok">Enregistrer</button></div>';
    ov.appendChild(box); m.appendChild(ov);
    document.getElementById('m-cancel').onclick = closeModal;
    document.getElementById('m-ok').onclick = async () => {
      const body = {
        ref: document.getElementById('m-p-ref').value.trim(),
        designation: document.getElementById('m-p-des').value.trim(),
        unite: document.getElementById('m-p-unite').value.trim() || 'unité',
        notes: document.getElementById('m-p-notes').value.trim() || null
      };
      if (!body.ref || !body.designation) { showToast('Référence et désignation obligatoires.', 'danger'); return; }
      try {
        if (editId) {
          await api('/api/ao/produits/'+editId, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        } else {
          await api('/api/ao/produits', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        }
        closeModal(); showToast('Produit enregistré.', 'success');
        await loadProduits(); render();
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
  }
}

function renderList() {
  const list = filteredAos();
  let rows = '';
  list.forEach(a => {
    rows += '<tr><td><strong>'+escHtml(a.reference)+'</strong></td><td>'+escHtml(a.titre)+'</td><td>'+statutBadge(a.statut)+'</td>'+
      '<td>'+escHtml(a.date_limite||'—')+'</td><td>'+escHtml(a.nb_fournisseurs)+'</td><td>'+escHtml(a.nb_reponses)+'</td>'+
      '<td><button class="btn btn-ghost btn-sm btn-view" data-id="'+a.id+'">Voir</button></td></tr>';
  });
  return '<div class="page-hdr"><h1>Appels d\'offre</h1><button class="btn btn-accent" type="button" id="btn-new-ao">'+icon('plus',14)+' Nouvel appel d\'offre</button></div>'+
    '<div class="filter-tabs">'+
    ['tous','brouillon','envoyee','cloturee'].map(f=>'<button class="filter-tab'+(S.filtre===f?' active':'')+'" data-f="'+f+'">'+escHtml(f==='tous'?'Tous':f==='brouillon'?'Brouillon':f==='envoyee'?'Envoyée':'Clôturée')+'</button>').join('')+
    '</div>'+
    (list.length ? '<div class="card"><table class="data-table"><thead><tr><th>Référence</th><th>Titre</th><th>Statut</th><th>Date limite</th><th>Fournisseurs</th><th>Réponses</th><th></th></tr></thead><tbody>'+rows+'</tbody></table></div>' :
    '<div class="card empty-state"><strong>Aucun appel d\'offre</strong>Créez un premier appel d\'offre pour inviter vos fournisseurs.</div>');
}

function renderDetailHeader() {
  const ao = S.ao;
  const d = S.detail;
  const st = ao.statut;
  const lignes = (d.lignes||[]).length;
  const fournis = (d.fournisseurs||[]).length;
  let actions = '<button class="btn btn-ghost" type="button" id="btn-back">'+icon('arrow-left',14)+' Retour liste</button>';
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
  return '<div class="breadcrumb"><a href="#" id="bc-list">Appels d\'offre</a> &gt; '+escHtml(ao.reference)+' — '+escHtml(ao.titre)+'</div>'+
    '<div class="detail-hdr"><h2>'+escHtml(ao.reference)+'</h2>'+statutBadge(st)+'</div>'+
    '<div class="detail-meta">'+escHtml(ao.titre)+'<br>Date limite : '+escHtml(ao.date_limite||'—')+' · Responsable : '+escHtml(ao.responsable_email||'—')+' · Réponses : '+escHtml(d.nb_reponses)+'</div>'+
    '<div class="detail-actions">'+actions+'</div>'+
    '<div class="detail-tabs">'+
    (() => {
      const totalNonLus = Object.values(S.nonLus || {}).reduce((a, b) => a + b, 0);
      const labels = {
        lignes:'Lignes',fournisseurs:'Fournisseurs',comparaison:'Comparaison',
        messages:'Messagerie'+(totalNonLus > 0
          ? ' <span class="nav-badge" style="background:var(--danger);color:#fff;font-size:10px;padding:1px 6px;border-radius:999px;font-weight:700">'+escHtml(totalNonLus)+'</span>'
          : ''),
        documents:'Documents'
      };
      return ['lignes','fournisseurs','comparaison','messages','documents'].map(t =>
        '<button class="detail-tab'+(S.tab===t?' active':'')+'" data-tab="'+t+'">'+labels[t]+'</button>'
      ).join('');
    })()+'</div>';
}

function renderLignes() {
  const st = S.ao.statut;
  const lignes = S.detail.lignes || [];
  let rows = lignes.map(l => '<tr><td>'+escHtml(l.position)+'</td><td>'+escHtml(l.ref_produit)+'</td><td>'+escHtml(l.designation)+'</td>'+
    '<td>'+escHtml(l.quantite)+' '+escHtml(l.unite)+'</td><td>'+escHtml(l.notes||'')+'</td><td>'+
    (st==='brouillon'?'<button class="btn btn-ghost btn-sm btn-edit-ligne" data-id="'+l.id+'">Modifier</button> <button class="btn btn-ghost btn-sm btn-del-ligne" data-id="'+l.id+'">Supprimer</button>':'')+
    '</td></tr>').join('');
  return '<div class="card">'+(st==='brouillon'?'<button class="btn btn-accent btn-sm" type="button" id="btn-add-ligne" style="margin-bottom:12px">'+icon('plus',14)+' Ajouter une ligne</button>':'')+
    '<table class="data-table"><thead><tr><th>#</th><th>Réf.</th><th>Désignation</th><th>Qté</th><th>Notes</th><th></th></tr></thead><tbody>'+
    (rows||'<tr><td colspan="6" style="color:var(--muted)">Aucune ligne</td></tr>')+'</tbody></table></div>';
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
    if (f.statut !== 'repondu') act += ' <button class="btn btn-ghost btn-sm btn-del-f" data-id="'+f.id+'">Supprimer</button>';
    return '<tr><td>'+escHtml(f.nom_fournisseur)+'</td><td>'+escHtml(f.email_contact)+'</td><td>'+fourniBadge(f.statut)+unreadBadge+'</td>'+
      '<td>'+escHtml(f.date_envoi||'—')+'</td><td>'+escHtml(f.date_reponse||'—')+'</td><td>'+act+'</td></tr>';
  }).join('');
  return '<div class="card">'+(ao.statut!=='cloturee'?'<button class="btn btn-accent btn-sm" id="btn-add-f" style="margin-bottom:12px">'+icon('plus',14)+' Ajouter un fournisseur</button>':'')+
    '<table class="data-table"><thead><tr><th>Nom</th><th>Email</th><th>Statut</th><th>Envoi</th><th>Réponse</th><th></th></tr></thead><tbody>'+
    (rows||'<tr><td colspan="6" style="color:var(--muted)">Aucun fournisseur</td></tr>')+'</tbody></table></div>';
}

function renderComparaison() {
  const c = S.comparaison;
  if (!c) return '<div class="card" style="color:var(--muted)">Chargement…</div>';
  const fournis = c.fournisseurs || [];
  const lignes = c.lignes || [];
  let head = '<tr><th class="ref">Réf. · Désignation · Qté</th>';
  fournis.forEach(f => { head += '<th>'+escHtml(f.nom_fournisseur)+'<br>'+fourniBadge(f.statut)+'</th>'; });
  head += '</tr>';
  let body = '';
  lignes.forEach(ln => {
    const repMap = {};
    (ln.reponses||[]).forEach(r => { repMap[r.fourni_id] = r; });
    const summary = ln.prix_min != null
      ? '<br><span style="font-size:10px;color:var(--muted)">Min '+formatEur(ln.prix_min)+' · Max '+formatEur(ln.prix_max)+' · Moy. '+formatEur(ln.prix_moyen)+'</span>'
      : '';
    body += '<tr><td class="ref" style="text-align:left">'+escHtml(ln.ref_produit)+'<br><span style="color:var(--muted);font-weight:400">'+escHtml(ln.designation)+'</span><br>'+escHtml(ln.quantite)+' '+escHtml(ln.unite)+summary+'</td>';
    fournis.forEach(f => {
      const r = repMap[f.id];
      const cls = (ln.prix_min != null && r && r.prix_unitaire === ln.prix_min) ? ' comp-cell-best' : '';
      const cell = r && r.prix_unitaire != null ? formatEur(r.prix_unitaire)+(r.delai_jours!=null?' · '+r.delai_jours+' j':'') : '—';
      body += '<td class="'+cls.trim()+'">'+cell+(r&&r.commentaire?'<br><span style="font-size:10px;color:var(--muted)">'+escHtml(r.commentaire)+'</span>':'')+'</td>';
    });
    body += '</tr>';
  });
  return '<div class="card" style="overflow:auto"><table class="comp-table"><thead>'+head+'</thead><tbody>'+body+'</tbody></table></div>';
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
  document.getElementById('btn-new-ao')?.addEventListener('click', openModalCreate);
  document.querySelectorAll('.filter-tab').forEach(b => b.addEventListener('click', () => { S.filtre = b.dataset.f; render(); }));
  document.querySelectorAll('.btn-view').forEach(b => b.addEventListener('click', () => openDetail(parseInt(b.dataset.id,10))));
}

function bindDetailEvents() {
  document.getElementById('btn-back')?.addEventListener('click', backToList);
  document.getElementById('bc-list')?.addEventListener('click', e => { e.preventDefault(); backToList(); });
  document.querySelectorAll('.detail-tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
  document.getElementById('btn-envoyer')?.addEventListener('click', () => {
    const n = (S.detail.fournisseurs||[]).length;
    openModalConfirmEnvoi(n);
  });
  document.getElementById('btn-cloturer')?.addEventListener('click', async () => {
    if (!confirm('Clôturer cet appel d\'offre ?')) return;
    try {
      await api('/api/ao/'+S.ao.id+'/cloturer', {method:'PATCH'});
      showToast('Appel d\'offre clôturé.', 'success');
      await loadDetail(S.ao.id); render();
    } catch(e) { showToast(e.message, 'danger'); }
  });
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
  document.getElementById('btn-add-f')?.addEventListener('click', openModalFourni);
  document.querySelectorAll('.btn-copy').forEach(b => b.addEventListener('click', () => {
    const f = (S.detail.fournisseurs||[]).find(x => x.token === b.dataset.token);
    const url = (BASE_URL||location.origin).replace(/\/$/,'')+'/portail/ao/'+b.dataset.token;
    navigator.clipboard.writeText(url).then(() => showToast('Lien copié.', 'success')).catch(() => showToast('Copie impossible', 'danger'));
  }));
  document.querySelectorAll('.btn-msg').forEach(b => b.addEventListener('click', () => {
    S.messages_fourni = parseInt(b.dataset.id, 10);
    setTab('messages');
  }));
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
  if (S.section === 'dashboard') {
    area.innerHTML = renderDashboard();
    bindListEvents();
  } else if (S.section === 'contact_fournisseur') {
    area.innerHTML = renderCarnet();
    bindCarnetEvents();
  } else if (S.section === 'produits') {
    area.innerHTML = renderProduits();
    bindProduitsEvents();
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
  const loads = await Promise.allSettled([loadList(), loadCarnet(), loadProduits()]);
  const labels = ['appels d\'offre', 'carnet fournisseurs', 'produits'];
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
  }
  render();
})();
</script>
</body>
</html>"""
