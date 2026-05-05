"""MySifa — MyStock v2.1 (standalone page /stock)
Fixes:
- appendChild error (null children)
- Search input cursor inversion (no re-render on input)
- Navigation / back button
- Add product/emplacement button restored
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request):
    user = get_current_user(request)
    if user.get("role") not in {"direction", "administration", "logistique"}:
        raise HTTPException(403, "Accès réservé à MyStock")
    return HTMLResponse(content=STOCK_HTML)


STOCK_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0a0e17">
<title>MyStock — MySifa</title>
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#94a3b8;
  --muted:#64748b;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;--c2:#a78bfa;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;--c2:#7c3aed;
}
html,body{height:100%}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);display:flex;flex-direction:column}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button:focus:not(:focus-visible){outline:none}
input,select{font-family:inherit}

/* ── Layout desktop / mobile ── */
.app-layout{display:flex;flex:1;overflow:hidden}

/* Sidebar desktop */
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;flex-shrink:0;overflow-y:auto;
  height:100vh;position:sticky;top:0}
.sidebar::-webkit-scrollbar{width:0}
.sidebar-logo{padding:20px 16px 8px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;
  border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;
  font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.sidebar-nav{padding:8px 8px;flex:1}
.sidebar-bottom{padding:12px 8px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:6px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg)}
.uc-name{font-size:12px;font-weight:600;color:var(--text)}
.uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;
  border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;
  font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}

/* Main area */
.main-area{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* Mobile topbar */
.mobile-topbar{display:none;align-items:center;gap:10px;padding:12px 16px;
  background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
.burger-btn{background:none;border:1px solid var(--border);border-radius:8px;
  width:36px;height:36px;display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--text2);font-size:18px;flex-shrink:0}
.burger-btn:hover{border-color:var(--accent);color:var(--accent)}
.mobile-title{font-size:15px;font-weight:800;flex:1}
.mobile-title span{color:var(--accent)}

/* Sidebar overlay mobile */
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:900px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:300;
    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-topbar{display:flex}
}

/* Scroll area */
.scroll-area{flex:1;overflow-y:auto}

/* ── Search bar ── */
.search-bar-wrap{padding:12px 16px;background:var(--bg);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:90}
.search-row{display:flex;gap:8px;align-items:center}
.search-input{flex:1;background:var(--card);border:1.5px solid var(--border);border-radius:12px;
  padding:12px 16px;color:var(--text);font-size:15px;font-family:inherit;outline:none;
  transition:border-color .15s;direction:ltr;unicode-bidi:normal}
.search-input:focus{border-color:var(--accent)}
.search-icon-btn{width:44px;height:44px;border-radius:12px;border:1.5px solid var(--border);
  background:var(--card);color:var(--text2);cursor:pointer;font-size:20px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .15s}
.search-icon-btn:hover,.search-icon-btn.active{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.search-icon-btn.listening{animation:pulse-ring 1s infinite}
@keyframes pulse-ring{0%,100%{box-shadow:0 0 0 0 rgba(34,211,238,.4)}50%{box-shadow:0 0 0 8px rgba(34,211,238,0)}}
.search-results{background:var(--card);border:1px solid var(--border);border-radius:12px;
  margin-top:8px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.search-section-title{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;padding:10px 14px 4px}
.search-item{padding:12px 14px;cursor:pointer;display:flex;justify-content:space-between;
  align-items:center;border-bottom:1px solid var(--border);transition:background .1s}
.search-item:last-child{border-bottom:none}
.search-item:hover{background:var(--accent-bg)}
.si-ref{font-family:monospace;font-weight:700;font-size:13px;color:var(--text)}
.si-des{font-size:11px;color:var(--muted);margin-top:1px}
.si-badge{font-family:monospace;font-size:11px;font-weight:700;color:var(--accent);
  background:var(--accent-bg);padding:3px 8px;border-radius:10px;white-space:nowrap}

/* ── Content ── */
.content{padding:16px;max-width:900px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:12px}
.card-header{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.card-title{font-size:14px;font-weight:700}
.card-empty{padding:32px 16px;text-align:center;color:var(--muted);font-size:13px}

/* ── Formulaire ajout produit ── */
.add-form{padding:16px;display:flex;flex-direction:column;gap:10px}
.add-form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.field-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;display:block}
.field-input{width:100%;background:var(--bg);border:1.5px solid var(--border);border-radius:10px;
  padding:10px 13px;color:var(--text);font-size:14px;font-family:inherit;outline:none;
  transition:border-color .15s;direction:ltr}
.field-input:focus{border-color:var(--accent)}
.btn{background:var(--accent);color:#0a0e17;border:none;border-radius:10px;padding:10px 20px;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:opacity .15s;white-space:nowrap}
.btn:hover{opacity:.85}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-sm{background:var(--accent);color:#0a0e17;border:none;border-radius:8px;padding:7px 14px;
  font-size:12px;font-weight:700;cursor:pointer;font-family:inherit}
.btn-danger{background:rgba(248,113,113,.15);color:var(--danger);border:1px solid rgba(248,113,113,.3);
  border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}

/* ── Scorecard ── */
.scorecard{background:var(--card);border:1.5px solid var(--border);border-radius:16px;padding:20px;margin-bottom:16px}
.sc-ref{font-family:monospace;font-size:13px;color:var(--muted);margin-bottom:4px}
.sc-des{font-size:17px;font-weight:800;margin-bottom:16px;line-height:1.2}
.sc-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}
.sc-stat{background:var(--bg);border-radius:10px;padding:12px}
.sc-stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:4px}
.sc-stat-value{font-size:22px;font-weight:800;font-family:monospace}
.sc-stat-sub{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Rows ── */
.empl-row{padding:12px 16px;display:flex;justify-content:space-between;align-items:center;
  border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}
.empl-row:last-child{border-bottom:none}
.empl-row:hover{background:var(--accent-bg)}
.empl-row.alerte{border-left:3px solid var(--warn)}
.empl-code{font-family:monospace;font-weight:800;font-size:14px;color:var(--accent)}
.empl-info{font-size:11px;color:var(--muted);margin-top:2px}
.empl-qte{font-family:monospace;font-weight:700;font-size:13px;text-align:right}
.empl-date{font-size:11px;color:var(--muted);text-align:right;margin-top:2px}

/* ── Action bar ── */
.action-bar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.action-btn{flex:1;min-width:90px;padding:12px 8px;border-radius:12px;border:none;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center;gap:5px;transition:opacity .15s}
.action-btn:active{opacity:.75}
.action-btn.entree{background:rgba(52,211,153,.2);color:var(--success)}
.action-btn.sortie{background:rgba(248,113,113,.2);color:var(--danger)}
.action-btn.inventaire{background:rgba(167,139,250,.2);color:var(--c2)}

/* ── Historique mouvements ── */
.mvt-row{padding:10px 16px;display:flex;gap:10px;align-items:flex-start;border-bottom:1px solid var(--border)}
.mvt-row:last-child{border-bottom:none}
.mvt-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.mvt-icon.entree{background:rgba(52,211,153,.15);color:var(--success)}
.mvt-icon.sortie{background:rgba(248,113,113,.15);color:var(--danger)}
.mvt-icon.inventaire{background:rgba(167,139,250,.15);color:var(--c2)}
.mvt-body{flex:1;min-width:0}
.mvt-line1{font-size:13px;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:8px}
.mvt-qte-entree{color:var(--success);font-family:monospace;font-weight:700}
.mvt-qte-sortie{color:var(--danger);font-family:monospace;font-weight:700}
.mvt-qte-inventaire{color:var(--c2);font-family:monospace;font-weight:700}
.mvt-line2{font-size:11px;color:var(--muted);margin-top:2px}
.mvt-note{font-size:11px;color:var(--text2);margin-top:2px;font-style:italic}

/* ── Stats dashboard ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:6px}
.stat-value{font-size:26px;font-weight:800;font-family:monospace}
.stat-value.accent{color:var(--accent)}
.stat-value.warn{color:var(--warn)}

/* ── Inventaire chaîne ── */
.inv-item{padding:13px 16px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}
.inv-item:last-child{border-bottom:none}
.inv-item:hover{background:var(--accent-bg)}
.inv-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.inv-dot.urgent{background:var(--danger)}
.inv-dot.attention{background:var(--warn)}
.inv-label{flex:1;min-width:0}
.inv-ref{font-family:monospace;font-weight:700;font-size:13px}
.inv-empl{font-size:11px;color:var(--muted);margin-top:2px}
.inv-days{font-size:12px;font-weight:700;white-space:nowrap}
.inv-days.urgent{color:var(--danger)}
.inv-days.attention{color:var(--warn)}

/* ── Modal mouvement (bottom sheet) ── */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:500;
  display:flex;flex-direction:column;justify-content:flex-end}
@media(min-width:600px){.modal-overlay{align-items:center;justify-content:center}}
.modal-sheet{background:var(--card);border-radius:20px 20px 0 0;padding:24px 20px;
  max-height:90vh;overflow-y:auto;width:100%}
@media(min-width:600px){.modal-sheet{border-radius:20px;max-width:480px}}
.modal-handle{width:40px;height:4px;background:var(--border);border-radius:2px;margin:0 auto 20px;display:block}
.modal-title{font-size:17px;font-weight:800;margin-bottom:6px}
.modal-sub{font-size:12px;color:var(--muted);margin-bottom:18px}
.mvt-type-btns{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:20px}
.mvt-type-btn{padding:13px 6px;border-radius:12px;border:1.5px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-weight:700;
  font-family:inherit;text-align:center;transition:all .15s}
.mvt-type-btn.sel-entree{background:rgba(52,211,153,.15);color:var(--success);border-color:var(--success)}
.mvt-type-btn.sel-sortie{background:rgba(248,113,113,.15);color:var(--danger);border-color:var(--danger)}
.mvt-type-btn.sel-inventaire{background:rgba(167,139,250,.15);color:var(--c2);border-color:var(--c2)}
.modal-field{margin-bottom:14px}
.empl-suggestions{background:var(--bg);border:1px solid var(--border);border-radius:8px;
  margin-top:4px;overflow:hidden;max-height:140px;overflow-y:auto}
.empl-sugg-item{padding:10px 14px;cursor:pointer;font-family:monospace;font-size:13px;
  font-weight:700;border-bottom:1px solid var(--border);transition:background .1s}
.empl-sugg-item:last-child{border-bottom:none}
.empl-sugg-item:hover{background:var(--accent-bg);color:var(--accent)}
.modal-actions{display:grid;grid-template-columns:1fr 2fr;gap:10px;margin-top:16px}
.btn-cancel{background:transparent;border:1.5px solid var(--border);border-radius:12px;
  padding:13px;font-size:14px;font-weight:700;color:var(--text2);cursor:pointer;font-family:inherit}
.btn-confirm{border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:700;
  cursor:pointer;font-family:inherit;color:#0a0e17}
.btn-confirm.entree{background:var(--success)}
.btn-confirm.sortie{background:var(--danger)}
.btn-confirm.inventaire{background:var(--c2)}

/* ── Toast ── */
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:600;
  background:var(--card);border-radius:12px;padding:12px 20px;font-size:14px;font-weight:600;
  box-shadow:0 8px 32px rgba(0,0,0,.4);animation:fadeUp .25s;white-space:nowrap;
  border-left:3px solid var(--accent)}
.toast.error{border-left-color:var(--danger);color:var(--danger)}
.toast.warn{border-left-color:var(--warn);color:var(--warn)}
@keyframes fadeUp{from{opacity:0;transform:translateX(-50%) translateY(10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}

/* ── FAB ── */
.fab{position:fixed;bottom:24px;right:24px;width:52px;height:52px;border-radius:26px;
  background:var(--accent);color:#0a0e17;border:none;font-size:22px;cursor:pointer;
  box-shadow:0 4px 20px rgba(34,211,238,.4);display:flex;align-items:center;justify-content:center;
  z-index:200;transition:transform .15s;font-weight:700}
.fab:active{transform:scale(.9)}

/* ── Caméra ── */
.camera-modal{position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:600;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:20px}
.camera-wrap{position:relative;width:100%;max-width:360px}
.camera-video{width:100%;border-radius:16px;display:block}
.camera-frame{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:200px;height:200px;border:2px solid var(--accent);border-radius:12px;
  box-shadow:0 0 0 2000px rgba(0,0,0,.5);pointer-events:none}
.camera-hint{font-size:13px;color:var(--text2);text-align:center;max-width:300px}
.camera-result{background:var(--accent-bg);border:1px solid var(--accent);border-radius:10px;
  padding:12px 20px;font-family:monospace;font-size:14px;color:var(--accent);text-align:center;min-width:200px}
.btn-close-cam{background:var(--danger);color:#fff;border:none;border-radius:12px;
  padding:12px 32px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}
</style>
</head>
<body>
<div id="root"></div>
<script>
const API = window.location.origin;

// ── State ───────────────────────────────────────────────────────
let S = {
  user: null,
  tab: 'dashboard',
  sidebarOpen: false,
  searchQuery: '',
  searchResults: null,
  selProduit: null,
  selEmpl: null,
  dashboard: null,
  inventaireList: [],
  modalMvt: null,
  modalType: 'entree',
  toast: null,
  listening: false,
  scanning: false,
  cameraStream: null,
  barcodeReader: null,
  emplSuggestions: [],
  showAddForm: false,
};

// ── API ─────────────────────────────────────────────────────────
async function api(p, o) {
  try {
    const r = await fetch(API + p, { credentials: 'include', ...o });
    if (r.status === 401) { window.location.href = '/'; return null; }
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Erreur ' + r.status); }
    return await r.json();
  } catch(e) {
    if (e.message && e.message.includes('Failed to fetch')) throw new Error('API non disponible');
    throw e;
  }
}

function showToast(m, t='success') {
  S.toast = { message: m, type: t };
  renderToast();
  setTimeout(() => { S.toast = null; renderToast(); }, 3000);
}

// ── Helpers ─────────────────────────────────────────────────────
const fN = n => n != null ? Number(n).toLocaleString('fr-FR') : '0';
const fD = d => d ? d.slice(0,10).split('-').reverse().join('/') : '—';
const joursDepuis = d => { if (!d) return null; return Math.round((Date.now() - new Date(d).getTime()) / 86400000); };

// ── DOM helper — safe contre null/false ─────────────────────────
function el(tag, attrs, ...children) {
  const e = document.createElement(tag);
  if (attrs) {
    const { cls, on, style: s, html, ...rest } = attrs;
    if (cls) e.className = cls;
    if (on) Object.entries(on).forEach(([ev,fn]) => e.addEventListener(ev, fn));
    if (s && typeof s === 'object') Object.assign(e.style, s);
    if (html) { e.innerHTML = html; }
    Object.entries(rest).forEach(([k,v]) => {
      if (v === null || v === undefined || v === false) return;
      if (k === 'disabled' && v) { e.disabled = true; return; }
      e.setAttribute(k, v);
    });
  }
  children.flat(Infinity).forEach(c => {
    if (c == null || c === false || c === undefined) return;
    if (c instanceof Node) { e.appendChild(c); return; }
    if (typeof c === 'string' || typeof c === 'number') {
      e.appendChild(document.createTextNode(String(c)));
    }
  });
  return e;
}

// ── Loaders ─────────────────────────────────────────────────────
let searchTimer = null;
function doSearch(q) {
  S.searchQuery = q;
  clearTimeout(searchTimer);
  if (!q || q.length < 1) { S.searchResults = null; updateSearchResults(); return; }
  searchTimer = setTimeout(async () => {
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=8');
      S.searchResults = r;
    } catch(e) {}
    updateSearchResults();
  }, 220);
}

async function loadProduit(id) {
  try {
    const d = await api('/api/stock/produits/' + id);
    if (d) { S.selProduit = d; S.selEmpl = null; S.searchResults = null; clearSearch(); render(); }
  } catch(e) { showToast(e.message, 'error'); }
}

async function loadEmplacement(empl) {
  try {
    const d = await api('/api/stock/emplacements/' + encodeURIComponent(empl));
    if (d) { S.selEmpl = d; S.selProduit = null; S.searchResults = null; clearSearch(); render(); }
  } catch(e) { showToast(e.message, 'error'); }
}

async function loadDashboard() {
  try { const d = await api('/api/stock/dashboard'); if (d) { S.dashboard = d; renderContent(); } } catch(e) {}
}

async function loadInventaireList() {
  try { const d = await api('/api/stock/inventaire/produits-a-inventorier'); if (d) { S.inventaireList = d; renderContent(); } } catch(e) {}
}

async function submitMouvement(body) {
  try {
    const r = await api('/api/stock/mouvement', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r) return;
    showToast('Stock mis à jour → ' + fN(r.quantite_apres));
    S.modalMvt = null;
    document.querySelector('.modal-overlay')?.remove();
    if (S.selProduit) await loadProduit(S.selProduit.produit.id);
    else if (S.selEmpl) await loadEmplacement(S.selEmpl.emplacement);
    else if (S.tab === 'dashboard') await loadDashboard();
    else if (S.tab === 'inventaire') await loadInventaireList();
  } catch(e) { showToast(e.message, 'error'); }
}

async function createProduit(ref, commentaire, quantite) {
  try {
    const body = { reference: ref };
    if (commentaire) body.commentaire = commentaire;
    if (quantite !== '' && quantite != null && !Number.isNaN(Number(quantite))) body.quantite = Number(quantite);
    await api('/api/stock/produits', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    showToast('Produit créé : ' + ref);
    S.showAddForm = false;
    renderContent();
  } catch(e) { showToast(e.message, 'error'); }
}

// ── Sidebar toggle ───────────────────────────────────────────────
function toggleSidebar() { S.sidebarOpen = !S.sidebarOpen; document.body.classList.toggle('sb-open', S.sidebarOpen); }
function closeSidebar() { S.sidebarOpen = false; document.body.classList.remove('sb-open'); }

// ── Navigation ──────────────────────────────────────────────────
function goToTab(tab) {
  S.tab = tab; S.selProduit = null; S.selEmpl = null; S.searchResults = null; S.showAddForm = false;
  clearSearch(); closeSidebar();
  updateNavActive();
  renderContent();
  if (tab === 'dashboard') loadDashboard();
  else if (tab === 'inventaire') loadInventaireList();
}

function updateNavActive() {
  document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === S.tab && !S.selProduit && !S.selEmpl);
  });
}

function clearSearch() {
  S.searchQuery = '';
  const inp = document.getElementById('main-search');
  if (inp) { inp.value = ''; }
  const res = document.getElementById('search-results-wrap');
  if (res) res.innerHTML = '';
}

// ── Micro ────────────────────────────────────────────────────────
function startVoiceSearch() {
  if (location.protocol !== 'https:') { showToast('Micro disponible sur mysifa.com (HTTPS)', 'warn'); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { showToast('Micro non supporté', 'error'); return; }
  const r = new SR(); r.lang = 'fr-FR'; r.interimResults = false;
  S.listening = true;
  const micBtn = document.getElementById('mic-btn');
  if (micBtn) { micBtn.classList.add('listening', 'active'); micBtn.textContent = '🔴'; }
  r.onresult = e => {
    const t = e.results[0][0].transcript;
    const inp = document.getElementById('main-search');
    if (inp) { inp.value = t; }
    S.listening = false;
    doSearch(t);
    if (micBtn) { micBtn.classList.remove('listening','active'); micBtn.textContent = '🎤'; }
  };
  r.onerror = r.onend = () => {
    S.listening = false;
    if (micBtn) { micBtn.classList.remove('listening','active'); micBtn.textContent = '🎤'; }
  };
  r.start();
}

// ── Caméra ───────────────────────────────────────────────────────
async function startCamera() {
  if (S.scanning) return;
  try {
    if (typeof ZXing === 'undefined') {
      showToast('Chargement scanner...', 'warn');
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/umd/index.min.js';
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
    }
  } catch(e) { showToast('Impossible de charger le scanner', 'error'); return; }

  S.scanning = true;
  const overlay = el('div', { cls:'camera-modal' });
  const wrap = el('div', { cls:'camera-wrap' });
  const video = el('video', { cls:'camera-video', autoplay:'', playsinline:'' });
  const frame = el('div', { cls:'camera-frame' });
  wrap.append(video, frame);
  const hint = el('p', { cls:'camera-hint' }, 'Pointez vers un code-barres ou emplacement (ex: B211)');
  const resultEl = el('div', { cls:'camera-result' }, 'En attente…');
  const closeBtn = el('button', { cls:'btn-close-cam', on:{ click: () => stopCamera(overlay) } }, '✕ Fermer');
  overlay.append(wrap, hint, resultEl, closeBtn);
  document.body.appendChild(overlay);

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    S.cameraStream = stream; video.srcObject = stream;
    const hints = new Map();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.CODE_128,ZXing.BarcodeFormat.EAN_13,ZXing.BarcodeFormat.QR_CODE]);
    const reader = new ZXing.BrowserMultiFormatReader(hints);
    S.barcodeReader = reader;
    reader.decodeFromVideoDevice(null, video, result => {
      if (!result) return;
      const text = result.getText().trim().toUpperCase();
      resultEl.textContent = '✅ ' + text; resultEl.style.color = 'var(--success)';
      setTimeout(() => { stopCamera(overlay); handleScan(text); }, 600);
    });
  } catch(e) { showToast('Accès caméra refusé', 'error'); stopCamera(overlay); }
}

function stopCamera(overlay) {
  if (S.cameraStream) { S.cameraStream.getTracks().forEach(t => t.stop()); S.cameraStream = null; }
  if (S.barcodeReader) { try { S.barcodeReader.reset(); } catch(e) {} S.barcodeReader = null; }
  S.scanning = false; overlay?.remove();
}

function handleScan(text) {
  if (/^[A-N]\d{3}$/i.test(text)) loadEmplacement(text);
  else { const inp = document.getElementById('main-search'); if(inp) inp.value = text; doSearch(text); }
}

// ── Modal mouvement ──────────────────────────────────────────────
function openMvtModal(produit_id, ref, emplacement, type='entree') {
  S.modalMvt = { produit_id, ref, emplacement: emplacement || '' };
  S.modalType = type;
  S.emplSuggestions = [];
  document.querySelector('.modal-overlay')?.remove();
  document.body.appendChild(buildMvtModal());
}

let emplTimer = null;
let emplInpRef = null;
function searchEmplSugg(q, suggWrap) {
  clearTimeout(emplTimer);
  if (!q) { suggWrap.innerHTML = ''; return; }
  emplTimer = setTimeout(async () => {
    try {
      const r = await api('/api/stock/search?q=' + encodeURIComponent(q) + '&limit=6');
      const list = (r?.emplacements || []).map(e => e.emplacement);
      suggWrap.innerHTML = '';
      list.forEach(emp => {
        const item = el('div', { cls:'empl-sugg-item', on:{ click: () => {
          emplInpRef.value = emp;
          suggWrap.innerHTML = '';
        }}}, emp);
        suggWrap.appendChild(item);
      });
    } catch(e) {}
  }, 180);
}

function buildMvtModal() {
  const { produit_id, ref, emplacement } = S.modalMvt;
  const type = S.modalType;

  const overlay = el('div', { cls:'modal-overlay', on:{ click: e => { if(e.target===overlay){S.modalMvt=null;overlay.remove();} }}});
  const sheet = el('div', { cls:'modal-sheet' });
  sheet.addEventListener('click', e => e.stopPropagation());

  const typeBtns = el('div', { cls:'mvt-type-btns' },
    ...['entree','sortie','inventaire'].map(t => {
      const labels = {entree:'↓ Entrée', sortie:'↑ Sortie', inventaire:'= Inventaire'};
      const b = el('button', { cls:'mvt-type-btn'+(S.modalType===t?' sel-'+t:''), on:{ click: () => {
        S.modalType = t;
        overlay.remove();
        document.body.appendChild(buildMvtModal());
      }}}, labels[t]);
      return b;
    })
  );

  const emplInp = el('input', { cls:'field-input', type:'text', placeholder:'ex: A123, B211…', value: emplacement, style:{textTransform:'uppercase',direction:'ltr'} });
  emplInpRef = emplInp;
  const suggWrap = el('div', { cls:'empl-suggestions' });
  emplInp.addEventListener('input', e => { emplInp.value = e.target.value.toUpperCase(); searchEmplSugg(emplInp.value, suggWrap); });

  const qteInp = el('input', { cls:'field-input', type:'number', placeholder:'0', min:'0', inputmode:'numeric', style:{direction:'ltr'} });

  const today = new Date().toISOString().slice(0,10);
  const dateInp = el('input', { cls:'field-input', type:'date', value:today });
  const dateField = el('div', { cls:'modal-field', style:{display: type==='sortie' ? 'none' : ''} }, el('label', { cls:'field-label' }, 'Date du stock'), dateInp);

  const noteInp = el('input', { cls:'field-input', type:'text', placeholder:'Réf BL, raison…', style:{direction:'ltr'} });

  const confirmBtn = el('button', { cls:'btn-confirm '+type, on:{ click: async () => {
    const qte = parseFloat(qteInp.value);
    const empl = emplInp.value.trim().toUpperCase();
    if (!empl) { showToast('Emplacement requis','error'); return; }
    if (!qte||qte<=0) { showToast('Quantité requise','error'); return; }
    await submitMouvement({ produit_id, emplacement:empl, type_mouvement:S.modalType, quantite:qte, date_entree:dateInp.value||today, note:noteInp.value.trim() });
  }}}, type==='entree'?'Valider entrée':type==='sortie'?'Valider sortie':'Valider inventaire');

  sheet.append(
    el('span',{cls:'modal-handle'}),
    el('div',{cls:'modal-title'}, '📦 '+ref),
    el('div',{cls:'modal-sub'}, 'Mouvement de stock'),
    typeBtns,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Emplacement'), emplInp, suggWrap),
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Quantité'), qteInp),
    dateField,
    el('div',{cls:'modal-field'}, el('label',{cls:'field-label'},'Commentaire (optionnel)'), noteInp),
    el('div',{cls:'modal-actions'},
      el('button',{cls:'btn-cancel', on:{click:()=>{S.modalMvt=null;overlay.remove();}}},'Annuler'),
      confirmBtn
    )
  );
  overlay.appendChild(sheet);
  return overlay;
}

function buildSearchBar() {
  const wrap = el('div', { cls:'search-bar-wrap', id:'search-bar-wrap' });
  const row = el('div', { cls:'search-row' });

  const inp = el('input', {
    cls:'search-input', type:'text', id:'main-search',
    placeholder:'Rechercher…',
    style:{direction:'ltr'}
  });
  inp.addEventListener('input', e => doSearch(e.target.value));
  inp.addEventListener('keydown', e => { if (e.key === 'Escape') clearSearch(); });

  const micBtn = el('button', { cls:'search-icon-btn', id:'mic-btn', on:{ click:startVoiceSearch } }, S.listening ? '🔴' : '🎤');
  const camBtn = el('button', { cls:'search-icon-btn', on:{ click:startCamera } }, '📷');

  row.append(inp, micBtn, camBtn);
  wrap.appendChild(row);
  wrap.appendChild(el('div', { id:'search-results-wrap' }));
  return wrap;
}

function updateSearchResults() {
  let wrap = document.getElementById('search-results-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';
  const q = S.searchQuery;
  const res = S.searchResults;
  if (!res || !q) return;
  const { produits=[], emplacements=[] } = res;
  if (!produits.length && !emplacements.length) {
    wrap.appendChild(el('div',{cls:'search-results'},el('div',{cls:'card-empty'},'Aucun résultat pour \"'+q+'\"')));
    return;
  }
  const box = el('div',{cls:'search-results'});
  if (produits.length) {
    box.appendChild(el('div',{cls:'search-section-title'},'📦 Produits'));
    produits.forEach(p => box.appendChild(
      el('div',{cls:'search-item',on:{click:()=>loadProduit(p.id)}},
        el('div',null,el('div',{cls:'si-ref'},p.reference),el('div',{cls:'si-des'},p.designation)),
        el('div',{cls:'si-badge'},fN(p.stock_total)+' '+p.unite)
      )
    ));
  }
  if (emplacements.length) {
    box.appendChild(el('div',{cls:'search-section-title'},'📍 Emplacements'));
    emplacements.forEach(e => box.appendChild(
      el('div',{cls:'search-item',on:{click:()=>loadEmplacement(e.emplacement)}},
        el('div',null,el('div',{cls:'si-ref'},e.emplacement),el('div',{cls:'si-des'},e.nb_refs+' référence'+(e.nb_refs>1?'s':''))),
        el('div',{cls:'si-badge'},fN(e.total_unites)+' u.')
      )
    ));
  }
  wrap.appendChild(box);
}

function renderToast() {
  document.querySelector('.toast')?.remove();
  if (!S.toast) return;
  const t = el('div', { cls:'toast'+(S.toast.type!=='success'?' '+S.toast.type:'') }, S.toast.message);
  document.body.appendChild(t);
}

function buildMvtHistory(mouvements, unite='u.') {
  return el('div',{cls:'card'},
    el('div',{cls:'card-header'},el('div',{cls:'card-title'},'🕐 Historique')),
    mouvements.length===0?el('div',{cls:'card-empty'},'Aucun mouvement'):
    el('div',null,...mouvements.slice(0,15).map(m=>{
      const icons={entree:'↓',sortie:'↑',inventaire:'='};
      const signe=m.type_mouvement==='entree'?'+':m.type_mouvement==='sortie'?'-':'=';
      return el('div',{cls:'mvt-row'},
        el('div',{cls:'mvt-icon '+m.type_mouvement},icons[m.type_mouvement]||'·'),
        el('div',{cls:'mvt-body'},
          el('div',{cls:'mvt-line1'},
            el('span',null,m.reference||m.emplacement||''),
            el('span',{cls:'mvt-qte-'+m.type_mouvement},signe+fN(m.quantite)+' '+unite)
          ),
          el('div',{cls:'mvt-line2'},fD(m.created_at)+' · '+(m.emplacement||'')+(m.created_by?' · '+m.created_by.split('@')[0]:'')),
          m.note?el('div',{cls:'mvt-note'},m.note):null
        )
      );
    }))
  );
}

function buildDashboard() {
  const d = S.dashboard;
  if (!d) return el('div',{cls:'content'},el('div',{cls:'card-empty'},'Chargement…'));
  const s = d.stats||{};
  return el('div',{cls:'content'},
    el('div',{cls:'stats-grid'},
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Références'),el('div',{cls:'stat-value accent'},s.nb_refs||0)),
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Emplacements occupés'),el('div',{cls:'stat-value accent'},s.nb_empl_occupes||0)),
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'Total unités'),el('div',{cls:'stat-value'},fN(s.total_unites||0))),
      el('div',{cls:'stat-card'},el('div',{cls:'stat-label'},'À inventorier'),el('div',{cls:'stat-value warn'},s.nb_a_inventorier||0))
    ),
    el('div',{cls:'card'},
      el('div',{cls:'card-header'},el('div',{cls:'card-title'},'➕ Nouveau produit')),
      el('div',{cls:'add-form'},
        (function(){
          const refI = el('input',{cls:'field-input',placeholder:'Référence obligatoire',autocomplete:'off',style:{direction:'ltr'}});
          const qtyI = el('input',{cls:'field-input',type:'text',inputmode:'decimal',placeholder:'0',autocomplete:'off',style:{direction:'ltr'}});
          const comI = el('input',{cls:'field-input',placeholder:'Commentaire (facultatif)',autocomplete:'off',style:{direction:'ltr'}});
          return el('div',null,
            el('div',{cls:'add-form-row'},
              el('div',null,el('label',{cls:'field-label'},'Référence *'),refI),
              el('div',null,el('label',{cls:'field-label'},'Quantité (sans unité)'),qtyI)
            ),
            el('div',null,el('label',{cls:'field-label'},'Commentaire'),comI),
            el('button',{cls:'btn',on:{click:async()=>{
              const raw = (refI.value||'').trim();
              const ref = raw.toUpperCase();
              if(!ref){showToast('Référence requise','error');return;}
              const q = (qtyI.value||'').trim();
              const com = (comI.value||'').trim();
              await createProduit(ref, com, q === '' ? null : q.replace(',','.'));
              refI.value=''; qtyI.value=''; comI.value='';
            }}},'Créer le produit')
          );
        })()
      )
    ),
    buildMvtHistory(d.derniers_mouvements||[])
  );
}

function buildInventaire() {
  const list = S.inventaireList||[];
  return el('div',{cls:'content'},
    el('div',{cls:'card',style:{marginBottom:'12px'}},
      el('div',{cls:'card-header'},
        el('div',{cls:'card-title'},'⚠ À inventorier ('+list.length+')'),
        el('button',{cls:'btn-sm',on:{click:()=>loadInventaireList()}},'↺ Rafraîchir')
      ),
      el('div',{style:{padding:'10px 16px 12px',fontSize:'12px',color:'var(--muted)'}},'Non inventoriés depuis plus de 6 mois. Cliquez pour inventorier.')
    ),
    list.length===0
      ? el('div',{cls:'card'},el('div',{cls:'card-empty'},'✅ Tous les stocks ont été inventoriés récemment'))
      : el('div',{cls:'card'},el('div',null,...list.slice(0,50).map(item=>{
          const j=item.jours_depuis;
          const cls=j>365?'urgent':'attention';
          return el('div',{cls:'inv-item',on:{click:()=>openMvtModal(item.id,item.reference,item.emplacement,'inventaire')}},
            el('div',{cls:'inv-dot '+cls}),
            el('div',{cls:'inv-label'},el('div',{cls:'inv-ref'},item.reference),el('div',{cls:'inv-empl'},item.emplacement+' · '+fN(item.quantite)+' '+item.unite)),
            el('div',{cls:'inv-days '+cls},j===9999?'Jamais':j+'j')
          );
        })))
  );
}

function renderContent() {
  const area = document.getElementById('scroll-area');
  if (!area) return;
  area.innerHTML = '';

  let content;
  if (S.tab === 'dashboard') content = buildDashboard();
  else if (S.tab === 'inventaire') content = buildInventaire();
  else content = buildDashboard();

  if (content) area.appendChild(content);
}

function render() {
  const root = document.getElementById('root');
  root.innerHTML = '';

  const overlay = el('div', { cls:'sidebar-overlay', on:{ click: closeSidebar } });
  root.appendChild(overlay);

  const layout = el('div', { cls:'app-layout' });

  const sidebar = el('div', { cls:'sidebar' },
    el('div', { cls:'sidebar-logo' },
      el('div', { cls:'logo-brand' }, 'My', el('span',null,'Stock')),
      el('div', { cls:'logo-sub' }, 'by SIFA')
    ),
    el('div', { cls:'sidebar-nav' },
      ...[
        { tab:'dashboard',  icon:'📊', label:'Dashboard' },
        { tab:'inventaire', icon:'📋', label:'Inventaire' },
      ].map(n => el('button', { cls:'nav-btn'+(S.tab===n.tab?' active':''), 'data-tab':n.tab, on:{ click:()=>goToTab(n.tab) } }, n.icon+'  '+n.label))
    ),
    el('div', { cls:'sidebar-bottom' },
      el('button', { cls:'nav-btn', on:{ click:()=>{ window.location.href='/'; } } }, '← MySifa'),
      S.user ? el('div', { cls:'user-chip' },
        el('div', { cls:'uc-name' }, S.user.nom||''),
        el('div', { cls:'uc-role' }, S.user.role||'')
      ) : null,
      el('button', { cls:'theme-btn', on:{ click:()=>{ document.body.classList.toggle('light'); localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark'); render(); } } }, document.body.classList.contains('light')?'🌙 Mode sombre':'☀ Mode clair'),
      el('button', { cls:'logout-btn', on:{ click: async ()=>{ await api('/api/auth/logout',{method:'POST'}); window.location.href='/'; } } }, '⎋  Déconnexion'),
      el('div', { cls:'version' }, 'MyStock v2.1')
    )
  );

  const main = el('div', { cls:'main-area' },
    el('div', { cls:'mobile-topbar' },
      el('button', { cls:'burger-btn', on:{ click:toggleSidebar } }, '☰'),
      el('div', { cls:'mobile-title' }, 'My', el('span',null,'Stock')),
      el('button', { cls:'burger-btn', on:{ click:()=>window.location.href='/' } }, '⌂')
    ),
    buildSearchBar(),
    el('div', { cls:'scroll-area', id:'scroll-area' })
  );

  layout.append(sidebar, main);
  root.appendChild(layout);

  renderContent();
}

async function init() {
  if (localStorage.getItem('theme')==='light') document.body.classList.add('light');
  const user = await api('/api/auth/me').catch(()=>null);
  if (!user) { window.location.href='/'; return; }
  S.user = user;
  render();
  await loadDashboard();
}

init();
</script>
</body>
</html>"""
