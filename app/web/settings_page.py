"""Paramètres MySifa — super administrateur uniquement."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user, is_superadmin
from app.web.access_denied import access_denied_response
from app.web.traca_guide_js import TRACA_GUIDE_SCRIPT_BLOCK

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/settings", status_code=302)
        raise
    if not is_superadmin(user):
        return access_denied_response(
            "Paramètres (super admin)",
            detail=(
                "Cette application est réservée au super administrateur. "
                "Merci de contacter un administrateur en cas de besoin."
            ),
        )
    return HTMLResponse(
        content=SETTINGS_HTML.replace("__V_LABEL__", f"v{APP_VERSION}").replace(
            "/*__TRACA_GUIDE__*/", TRACA_GUIDE_SCRIPT_BLOCK
        )
    )


SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Paramètres — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--ok:#34d399;--warn:#fbbf24;--danger:#f87171;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--ok:#059669;--warn:#d97706;--danger:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{font-size:15px;font-weight:800;margin-bottom:20px;padding:0 8px}.logo span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px;position:relative;z-index:1}
.nav-btn:hover,.nav-btn.active{background:rgba(34,211,238,.12);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:inset 0 0 0 1.5px rgba(34,211,238,.45),0 0 12px rgba(34,211,238,.2)}
body.light .nav-btn:hover:not(.active){box-shadow:inset 0 0 0 1.5px rgba(8,145,178,.5),0 0 10px rgba(8,145,178,.15)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:rgba(34,211,238,.12);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.theme-btn:hover{background:rgba(34,211,238,.12);color:var(--accent);border-color:var(--accent);box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 20px rgba(34,211,238,.14)}
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{font-size:14px;line-height:1;display:inline-flex;align-items:center}
@media (display-mode:standalone),(max-width:900px){
  .theme-btn .theme-label{display:none}.theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:24px 28px;overflow:auto}
/* topbar mobile : mysifa_mobile_topbar.css */
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
h1{font-size:22px;margin:0 0 6px}
.sub{color:var(--muted);font-size:13px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 14px}
.table-wrap{overflow:auto;border-radius:10px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}
th{background:rgba(15,23,42,.35);font-weight:700;color:var(--muted);position:sticky;top:0}
body.light th{background:#f1f5f9}
td.chk{text-align:center}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok)}.dot.no{background:var(--border)}
.chk-edit{width:16px;height:16px;cursor:pointer;accent-color:var(--accent)}
.cell-ov{font-size:9px;color:var(--accent);font-weight:700;letter-spacing:.02em}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:12px}
input,select{width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit}
.btn{background:var(--accent);color:var(--text);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit}
.btn:hover{filter:brightness(1.06)}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.btn-sec:hover{box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
body.light .btn-sec:hover{box-shadow:0 0 0 1px rgba(8,145,178,.35),0 0 18px rgba(8,145,178,.15);border-color:rgba(8,145,178,.4);color:var(--accent)}
.row-user{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.row-user:last-child{border-bottom:none}
.prof-ring{position:relative;flex-shrink:0;width:34px;height:34px;cursor:default}
.prof-ring svg{display:block;width:34px;height:34px}
.prof-ring-track{stroke:var(--border)}
.prof-ring-bar{stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .25s ease}
.prof-ring[data-tier="low"] .prof-ring-bar{stroke:var(--danger)}
.prof-ring[data-tier="mid"] .prof-ring-bar{stroke:var(--warn)}
.prof-ring[data-tier="high"] .prof-ring-bar{stroke:var(--ok)}
.prof-ring-label{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:9px;font-weight:800;color:var(--text);letter-spacing:-.02em;
  opacity:0;transition:opacity .15s;pointer-events:none;
}
.prof-ring:hover .prof-ring-label{opacity:1}
.op-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.op-filter{flex:1;min-width:200px;padding:10px 14px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.op-filter:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .op-filter:focus{box-shadow:0 0 0 3px rgba(8,145,178,.1)}
.op-form-panel{margin-bottom:16px;padding:16px 18px;border:1px solid var(--border);border-radius:12px;background:var(--bg)}
.op-form-panel h3{margin:0 0 12px;font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.op-table-wrap{margin-top:4px}
.op-table{font-size:12px}
.op-table th{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:10px 12px;white-space:nowrap}
.op-table td{padding:10px 12px;vertical-align:middle}
.op-table tbody tr:hover td{background:rgba(34,211,238,.04)}
body.light .op-table tbody tr:hover td{background:rgba(8,145,178,.05)}
.op-table tr.op-cat-row td{
  padding:14px 12px 6px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
  color:var(--accent);background:rgba(34,211,238,.06);border-bottom:1px solid var(--border)
}
body.light .op-table tr.op-cat-row td{background:rgba(8,145,178,.06)}
.op-table tr.op-cat-row:first-child td{padding-top:8px}
.op-code-cell{font-family:ui-monospace,monospace;font-weight:800;font-size:13px;color:var(--accent);width:56px}
.op-lbl-cell{font-weight:600;color:var(--text);max-width:280px;white-space:normal}
.op-pill{
  display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px;
  border:1px solid var(--border);text-transform:uppercase;letter-spacing:.3px;line-height:1.3
}
.op-pill.info{color:var(--text2);border-color:rgba(148,163,184,.4);background:rgba(148,163,184,.1)}
.op-pill.attention{color:var(--warn);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.12)}
.op-pill.critique{color:var(--danger);border-color:rgba(248,113,113,.45);background:rgba(248,113,113,.12)}
.op-pill.calage{color:var(--ok);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.1)}
.op-pill.arret{color:var(--warn);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.1)}
.op-pill.production{color:#60a5fa;border-color:rgba(96,165,250,.4);background:rgba(96,165,250,.1)}
.op-pill.changement{color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.1)}
.op-pill.nettoyage{color:#c084fc;border-color:rgba(192,132,252,.4);background:rgba(192,132,252,.1)}
.op-pill.autre{color:var(--muted);border-color:var(--border);background:rgba(148,163,184,.08)}
.op-req{font-size:11px;font-weight:600;color:var(--muted)}
.fsc-kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
@media(max-width:1000px){.fsc-kpi-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.fsc-kpi-grid{grid-template-columns:1fr}}
.fsc-kpi-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px}
.fsc-kpi-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.fsc-kpi-val{font-size:28px;font-weight:800;color:var(--text);line-height:1}
.fsc-kpi-badge{display:inline-block;margin-top:8px;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px}
.fsc-kpi-badge.accent{color:var(--accent);background:rgba(34,211,238,.12)}
.fsc-kpi-badge.ok{color:var(--ok);background:rgba(52,211,153,.12)}
.fsc-kpi-badge.danger{color:var(--danger);background:rgba(248,113,113,.12)}
.fsc-kpi-badge.muted{color:var(--muted);background:rgba(148,163,184,.12)}
.fsc-claim-badge{display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:3px 10px;border-radius:6px;line-height:1.3}
.fsc-section-title{font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px;margin:0 0 10px}
.fsc-date-inp{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit}
.fsc-date-inp:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.fsc-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.fsc-toolbar-dates{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.fsc-toolbar-dates .fsc-range-sep{color:var(--muted);font-size:12px}
.fsc-toolbar .btn-sec{font-size:12px;padding:7px 14px}
body.settings-tab-fsc .desktop-head{display:none}
body.settings-tab-fsc .main{padding-top:20px}
body.settings-tab-fsc .fsc-kpi-grid{margin-bottom:14px}
@media(min-width:901px){
  body.settings-tab-fsc .main{padding-top:24px}
}
tr.fsc-row-alert td{background:rgba(248,113,113,.08)}
body.light tr.fsc-row-alert td{background:rgba(220,38,38,.06)}
.op-req.yes{color:var(--ok)}
.op-table th:last-child,.op-table td:last-child{text-align:right}
.op-act{display:inline-flex;gap:6px;justify-content:flex-end;flex-wrap:nowrap}
.btn-sm{padding:6px 12px;font-size:11px;font-weight:700;border-radius:8px}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2);transition:border-color .15s,color .15s,box-shadow .15s,filter .15s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent);filter:none;box-shadow:0 0 0 1px rgba(34,211,238,.28),0 0 14px rgba(34,211,238,.14)}
body.light .btn-ghost:hover{box-shadow:0 0 0 1px rgba(8,145,178,.3),0 0 12px rgba(8,145,178,.1)}
.btn-ghost.danger:hover{border-color:var(--danger);color:var(--danger);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 14px rgba(248,113,113,.12)}

.pill{font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;border:1px solid var(--border);display:inline-flex;align-items:center;gap:6px;line-height:1.4}
.pill--direction{border-color:rgba(244,114,182,.35);color:#f472b6;background:rgba(244,114,182,.12)}
.pill--administration{border-color:rgba(167,139,250,.38);color:#a78bfa;background:rgba(167,139,250,.12)}
.pill--fabrication{border-color:rgba(52,211,153,.35);color:var(--ok);background:rgba(52,211,153,.12)}
.pill--logistique{border-color:rgba(96,165,250,.35);color:#60a5fa;background:rgba(96,165,250,.12)}
.pill--comptabilite{border-color:rgba(251,191,36,.38);color:#fbbf24;background:rgba(251,191,36,.12)}
.pill--expedition{border-color:rgba(248,113,113,.38);color:var(--danger);background:rgba(248,113,113,.12)}
.pill--superadmin{border-color:rgba(34,211,238,.45);color:var(--accent);background:rgba(34,211,238,.14)}
.pill--inactive{border-color:rgba(148,163,184,.35);color:var(--muted);background:rgba(148,163,184,.10)}
.users-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.users-head h2{margin:0}
.users-search{display:flex;align-items:center;gap:8px;min-width:min(520px,100%)}
.users-search input{flex:1;min-width:220px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.users-search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .users-search input:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.users-search .hint{font-size:11px;color:var(--muted);white-space:nowrap}
.users-search select{min-width:140px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.users-search select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .users-search select:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.tabs .btn{display:inline-flex;align-items:center;gap:8px;vertical-align:middle}
.tabs .btn svg{flex-shrink:0}
.nav-group-label{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);padding:8px 12px 2px;opacity:.7}
.hidden{display:none}
.legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.legend .item{padding:12px;border:1px solid var(--border);border-radius:10px;font-size:12px}
.legend .item strong{display:block;margin-bottom:6px;font-size:13px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;box-shadow:0 8px 32px rgba(0,0,0,.35);z-index:900}.toast.err{border-left:3px solid var(--danger)}
@media(max-width:900px){
  body.has-topbar .main{padding-top:74px}
  .main{padding:12px 14px}
  .desktop-head{display:none}
  h1{font-size:18px}
  .sub{font-size:12px;margin-bottom:14px}
  .sidebar{width:min(280px,88vw);position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;
    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55);padding:16px 10px}
  body.sb-open .sidebar{transform:translateX(0)}
  .layout{min-height:100vh}
  .nav-btn{padding:12px 14px;font-size:14px}
  .nav-scroll{gap:4px}
  /* Masquer les sous-onglets Utilisateurs dupliqués (navigation = sidebar) */
  .main section>.tabs:has(.sub-tab-btn){display:none}
  .tabs{overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch;gap:6px;margin-bottom:12px}
  .tabs .btn{flex-shrink:0;font-size:12px;padding:8px 12px}
  .form-grid{grid-template-columns:1fr}
  .users-search{flex-direction:column;min-width:0;align-items:stretch;width:100%}
  .users-search input,.users-search select{min-width:0;width:100%}
  .users-head{flex-direction:column;align-items:stretch}
  .card{padding:14px 16px}
  .table-wrap{-webkit-overflow-scrolling:touch;max-width:100%}
  table{font-size:11px}
  th,td{padding:6px 8px}
  .op-act{flex-wrap:wrap}
  .op-lbl-cell{max-width:160px}
  .legend{grid-template-columns:1fr}
  .four-sub-btn,.mac-sub-btn,.sub-tab-btn{flex-shrink:0}
}
</style>
</head>
<body>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<div class="sidebar-overlay" id="sb-ov"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">My<span>Sifa</span><div class="logo-sub">by SIFA</div></div>
    <div class="nav-scroll tabs" style="width:100%;margin:0">
      <div class="nav-group-label">Base</div>
      <button type="button" class="nav-btn active" data-tab="users">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Utilisateurs
      </button>
      <button type="button" class="nav-btn" data-tab="fournisseurs">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
        Fournisseurs
      </button>
      <button type="button" class="nav-btn" data-tab="operations">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Opérations
      </button>
      <button type="button" class="nav-btn" data-tab="machines">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
        Machines
      </button>
      <div class="nav-group-label" style="margin-top:8px">Accès</div>
      <button type="button" class="nav-btn" data-tab="matrix">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice d'accès
      </button>
      <button type="button" class="nav-btn" data-tab="defaults">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel rôles
      </button>
      <div class="nav-group-label" style="margin-top:8px">Communication</div>
      <button type="button" class="nav-btn" data-tab="updates">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        Mises à jour
      </button>
      <div class="nav-group-label" style="margin-top:8px">Audit</div>
      <button type="button" class="nav-btn" data-tab="audit">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        Log
      </button>
      <button type="button" class="nav-btn" data-tab="fsc">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/>
          <path d="M2 21c0-3 2.5-5 5-5"/>
        </svg>
        Registre FSC
      </button>
    </div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="sb-user-chip" title="Modifier mon profil" onclick="location.href='/profil'"></div>
      <button type="button" class="support-btn" id="sb-support" title="Contacter le support (email)">
        <span class="support-ico" id="sb-support-ico"></span>
        <span>Contacter le support</span>
      </button>
      <button type="button" class="theme-btn" id="theme-btn">
        <span class="theme-ico" id="theme-ico-slot"></span>
        <span class="theme-label" id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" id="logout-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Paramètres · MySifa __V_LABEL__</div>
    </div>
  </aside>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" id="sb-burger" aria-label="Menu">
        <span style="display: inline-flex; align-items: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </span>
      </button>
      <div>
        <div class="mobile-topbar-title">Paramètres</div>
        <div class="mobile-topbar-sub">Gestion des comptes et des accès</div>
      </div>
      <button type="button" class="mobile-home-btn" id="sb-home" aria-label="Accueil">
        <span style="display: inline-flex; align-items: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"><path d="M3 10.5L12 3l9 7.5"></path><path d="M5 10v11h14V10"></path><path d="M10 21v-6h4v6"></path></svg>
        </span>
      </button>
    </div>
    <div class="desktop-head">
      <h1>Paramètres</h1>
      <p class="sub">Gestion des comptes et visualisation des accès applications — réservé au super administrateur.</p>
    </div>

    <section id="panel-users">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Liste
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-matrix">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-defaults">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel
      </button>
    </div>
      <div class="card">
        <h2>Ajouter un utilisateur</h2>
        <div class="form-grid">
          <input type="text" id="cu-nom" placeholder="Nom complet" autocomplete="name">
          <input type="text" id="cu-ident" placeholder="Identifiant (auto si vide)" autocomplete="off">
          <input type="email" id="cu-email" placeholder="Email" autocomplete="off">
          <input type="password" id="cu-pwd" placeholder="Mot de passe (8+)" autocomplete="new-password">
          <select id="cu-role"></select>
          <select id="cu-op"><option value="">— Opérateur lié —</option></select>
          <select id="cu-mac"><option value="">— Machine (fabrication) —</option></select>
        </div>
        <button type="button" class="btn" id="cu-go">Créer le compte</button>
      </div>
      <div class="card">
        <div class="users-head">
          <h2>Utilisateurs</h2>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="users-search">
              <input type="search" id="users-q" placeholder="Rechercher (nom, email, rôle, opérateur, machine…)" autocomplete="off" spellcheck="false">
              <select id="users-role-filter"><option value="">Tous les services</option></select>
              <span class="hint" id="users-q-hint"></span>
            </div>
            <button type="button" class="btn btn-sec" onclick="downloadUsersCSV()" title="Télécharger la liste">Télécharger</button>
          </div>
        </div>
        <div id="users-list"></div>
      </div>
    </section>

    <section id="panel-matrix" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Liste
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-matrix">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-defaults">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel
      </button>
    </div>
      <div class="card">
        <h2>Qui a accès à quoi</h2>
        <p class="sub" style="margin-top:-8px">Cases à cocher : accès effectif (héritage du rôle ou surcharges). « Perso » = différent du défaut du rôle. Paramètres reste réservé au rôle super admin. Les super admins ont tout ; la ligne est en lecture seule.</p>
        <div class="table-wrap" id="matrix-table"></div>
      </div>
    </section>

    <section id="panel-defaults" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Liste
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-matrix">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Matrice
      </button>
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-defaults">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
        Référentiel
      </button>
    </div>
      <div class="card">
        <h2>Accès par défaut selon le rôle</h2>
        <p class="sub" style="margin-top:-8px">Chaque utilisateur hérite de ces accès selon son rôle assigné.</p>
        <div class="legend" id="role-legend"></div>
      </div>
    </section>

    <section id="panel-fournisseurs" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec four-sub-btn active" data-foursub="four-certifs">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        Certifications
      </button>
      <button type="button" class="btn btn-sec four-sub-btn" data-foursub="four-hist">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        Historique
      </button>
    </div>
      <div id="four-certifs">
        <div class="card">
          <h2>Ajouter un fournisseur</h2>
          <div class="form-grid">
            <input type="text" id="cf-nom" placeholder="Nom du fournisseur" autocomplete="off">
            <input type="text" id="cf-licence" placeholder="Code Licence FSC (ex: FSC-C004451)" autocomplete="off">
            <input type="text" id="cf-certificat" placeholder="Code Certificat FSC (ex: CU-COC-807907)" autocomplete="off">
          </div>
          <button type="button" class="btn" id="cf-go">Ajouter</button>
        </div>
        <div class="card">
          <h2>Fournisseurs enregistrés</h2>
          <div class="table-wrap" id="four-table-wrap"></div>
        </div>
      </div>
      <div id="four-hist" class="hidden">
        <div class="card">
          <h2>Historique des réceptions par fournisseur</h2>
          <p class="sub" style="margin-top:-8px">Sélectionnez un fournisseur pour voir ses réceptions.</p>
          <div class="form-grid" style="margin-bottom:12px">
            <select id="fh-four"><option value="">— Choisir un fournisseur —</option></select>
          </div>
          <div id="fh-results"></div>
        </div>
      </div>
    </section>


    <section id="panel-machines" class="hidden">
      <div class="tabs" style="margin-bottom:14px">
        <button type="button" class="btn btn-sec mac-sub-btn active" data-macsub="mac-horaires">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Horaires
        </button>
        <button type="button" class="btn btn-sec mac-sub-btn" data-macsub="mac-metrage">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          Métrage total
        </button>
      </div>
      <div class="card">
        <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px">
          <div style="flex:1;min-width:200px">
            <label class="sub" style="display:block;margin-bottom:6px">Machine</label>
            <select id="mac-select" style="width:100%;max-width:320px"></select>
          </div>
          <span class="hint" id="mac-hint"></span>
        </div>
        <div id="mac-horaires-wrap">
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Horaires par défaut du planning de production (lun–sam). Cohésio 2 : semaines paires / impaires.</p>
          <div id="mac-horaires-weekly"></div>
          <div id="mac-horaires-parity" class="hidden" style="margin-top:16px"></div>
          <div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap">
            <button type="button" class="btn" id="mac-hor-save">Enregistrer les horaires</button>
            <button type="button" class="btn btn-sec" id="mac-hor-reset">Réinitialiser (défauts machine)</button>
          </div>
        </div>
        <div id="mac-metrage-wrap" class="hidden">
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Compteur machine utilisé à la saisie production (début / fin de dossier). Mis à jour automatiquement à chaque saisie ; correction manuelle en cas d'erreur.</p>
          <div style="max-width:360px">
            <label class="sub" style="display:block;margin-bottom:6px">Métrage total actuel (m)</label>
            <input type="text" id="mac-metrage-inp" inputmode="decimal" placeholder="Ex. 1254300" autocomplete="off"
              style="width:100%;font-family:ui-monospace,monospace;font-size:15px">
            <p class="hint" id="mac-metrage-hint" style="margin-top:8px"></p>
          </div>
          <button type="button" class="btn" id="mac-metr-save" style="margin-top:14px">Enregistrer le métrage</button>
        </div>
      </div>
    </section>

    <section id="panel-operations" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <h2 style="margin:0">Codes opération (calage, arrêt, production…)</h2>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button type="button" class="btn btn-sec" onclick="importOpsJson()">Sync. operations.json</button>
            <button type="button" class="btn" onclick="openOpForm()">+ Ajouter un code</button>
          </div>
        </div>
        <p class="sub" style="margin-top:-4px;margin-bottom:14px">Référentiel utilisé par la saisie production et les imports. Modifiable ici ou via Database Viewer → table <code>operation_codes</code>.</p>
        <div id="op-form-wrap" class="hidden op-form-panel">
          <h3 id="op-form-title">Nouveau code</h3>
          <div class="form-grid" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))">
            <input type="text" id="op-code" placeholder="Code (ex. 82)" inputmode="numeric" maxlength="3">
            <input type="text" id="op-label" placeholder="Libellé">
            <select id="op-severity"><option value="info">info</option><option value="attention">attention</option><option value="critique">critique</option></select>
            <select id="op-category"></select>
            <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)"><input type="checkbox" id="op-required"> Obligatoire</label>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
            <button type="button" class="btn" onclick="saveOpForm()">Enregistrer</button>
            <button type="button" class="btn btn-sec" onclick="closeOpForm()">Annuler</button>
          </div>
        </div>
        <div class="op-toolbar">
          <input type="search" id="op-filter" class="op-filter" placeholder="Filtrer (code, libellé, catégorie…)" oninput="renderOpList()">
        </div>
        <div id="op-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
      </div>
    </section>

    <section id="panel-updates" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:16px">
          <h2 style="margin:0">Annonces de mise à jour</h2>
          <button type="button" class="btn" id="upd-new-btn" onclick="openNewUpdateModal()">+ Nouvelle annonce</button>
        </div>
        <p class="sub" style="margin-top:-8px;margin-bottom:16px">Gérez les messages affichés aux utilisateurs lors de leur prochaine connexion. Cliquez sur une ligne pour voir qui l'a lu.</p>
        <div id="upd-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
      </div>
    </section>

    <section id="panel-audit" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;
                gap:12px;margin-bottom:16px;flex-wrap:wrap">
          <div style="font-size:15px;font-weight:700;color:var(--text)">Journal des actions</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <input type="text" id="audit-search"
                   placeholder="Rechercher (utilisateur, objet, requête Google…)"
                   style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                          padding:7px 12px;color:var(--text);font-size:12px;width:200px;
                          font-family:inherit;outline:none"
                   oninput="debouncedAuditSearch()">
            <select id="audit-filter-module" onchange="loadAuditLogs()"
                    style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                           padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit">
              <option value="">Tous les modules</option>
              <option value="planning">Planning</option>
              <option value="fabrication">Fabrication</option>
              <option value="stock">Stock</option>
              <option value="expe">Expéditions</option>
              <option value="rh">RH</option>
              <option value="settings">Paramètres</option>
              <option value="auth">Auth</option>
              <option value="portal">Portail</option>
            </select>
            <select id="audit-filter-action" onchange="loadAuditLogs()"
                    style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
                           padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit">
              <option value="">Toutes les actions</option>
              <option value="CREATE">Création</option>
              <option value="UPDATE">Modification</option>
              <option value="DELETE">Suppression</option>
              <option value="CLOSE">Clôture</option>
              <option value="VALIDATE">Validation</option>
              <option value="REORDER">Réorganisation</option>
              <option value="SEARCH">Recherche</option>
            </select>
          </div>
        </div>
        <div id="audit-table-wrap" style="overflow-x:auto">
          <div id="audit-loading" style="color:var(--muted);font-size:13px;padding:20px 0">
            Chargement…
          </div>
        </div>
        <div id="audit-pagination"
             style="display:flex;align-items:center;justify-content:space-between;
                    margin-top:12px;font-size:12px;color:var(--muted)"></div>
      </div>
    </section>

    <section id="panel-fsc" class="hidden">
      <div class="fsc-toolbar">
        <div class="fsc-toolbar-dates">
          <input type="date" id="fsc-du" class="fsc-date-inp" onchange="loadFscRegistre()" aria-label="Date de début">
          <span class="fsc-range-sep">au</span>
          <input type="date" id="fsc-au" class="fsc-date-inp" onchange="loadFscRegistre()" aria-label="Date de fin">
        </div>
        <button type="button" class="btn btn-sec" onclick="exportFscCsv()">Exporter CSV</button>
      </div>
      <div id="fsc-kpi-grid" class="fsc-kpi-grid"></div>
      <div class="card" style="margin-bottom:16px">
        <h2 class="fsc-section-title">Réceptions FSC certifiées</h2>
        <div id="fsc-recep-wrap" class="table-wrap">
          <p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>
        </div>
      </div>
      <div class="card">
        <h2 class="fsc-section-title">Dossiers de production FSC</h2>
        <div id="fsc-dossiers-wrap" class="table-wrap">
          <p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>
        </div>
      </div>
    </section>

    <!-- Modal nouvelle annonce -->
    <div id="upd-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:90vh;overflow:auto">
        <h2 style="margin:0 0 18px;font-size:17px">Nouvelle annonce</h2>
        <div class="form-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Application</label>
            <select id="nm-app" style="width:100%" onchange="onAppChange()">
              <option value="planning">Planning Production</option>
              <option value="fabrication">Saisie Production</option>
              <option value="stock">Stock & Inventaire</option>
              <option value="myexpe">MyExpé (Transport)</option>
              <option value="planning_rh">Planning RH</option>
              <option value="paie">Paie</option>
              <option value="global">Toutes les applications</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Page</label>
            <select id="nm-page" style="width:100%">
              <option value="">Toutes les pages</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Active</label>
          <select id="nm-active" style="width:100%">
            <option value="1">Oui — visible par les utilisateurs</option>
            <option value="0">Non — masquée</option>
          </select>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Titre</label>
          <input type="text" id="nm-titre" placeholder="Ex : Mise à jour du 15 mai 2026 — Planning" style="width:100%">
        </div>
        <div style="margin-bottom:18px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Message (HTML autorisé)</label>
          <textarea id="nm-message" rows="8" placeholder="&lt;p&gt;Bonjour ! Voici les nouveautés…&lt;/p&gt;" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:monospace;resize:vertical"></textarea>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeNewUpdateModal()">Annuler</button>
          <button type="button" class="btn" onclick="submitNewUpdate()">Créer l'annonce</button>
        </div>
      </div>
    </div>

    <!-- Modal modifier annonce -->
    <div id="edit-upd-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:90vh;overflow:auto">
        <h2 style="margin:0 0 18px;font-size:17px">Modifier l'annonce</h2>
        <div class="form-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Application</label>
            <select id="edit-nm-app" style="width:100%" onchange="onEditAppChange()">
              <option value="planning">Planning Production</option>
              <option value="fabrication">Saisie Production</option>
              <option value="stock">Stock & Inventaire</option>
              <option value="myexpe">MyExpé (Transport)</option>
              <option value="planning_rh">Planning RH</option>
              <option value="paie">Paie</option>
              <option value="global">Toutes les applications</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Page</label>
            <select id="edit-nm-page" style="width:100%">
              <option value="">Toutes les pages</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Active</label>
          <select id="edit-nm-active" style="width:100%">
            <option value="1">Oui — visible par les utilisateurs</option>
            <option value="0">Non — masquée</option>
          </select>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Titre</label>
          <input type="text" id="edit-nm-titre" placeholder="Ex : Mise à jour du 15 mai 2026 — Planning" style="width:100%">
        </div>
        <div style="margin-bottom:18px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Message (HTML autorisé)</label>
          <textarea id="edit-nm-message" rows="8" placeholder="&lt;p&gt;Bonjour ! Voici les nouveautés…&lt;/p&gt;" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:monospace;resize:vertical"></textarea>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeEditUpdateModal()">Annuler</button>
          <button type="button" class="btn" onclick="submitEditUpdate()">Enregistrer</button>
        </div>
      </div>
    </div>
  </main>
</div>
<script src="/static/support_widget.js"></script>
<script>window.__MYSIFA_APP__='settings';</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/chat_widget.js"></script>
<script>
/*__TRACA_GUIDE__*/
const API = window.location.origin;
async function api(path, opt) {
  const r = await fetch(API + path, { credentials: 'include', ...opt });
  if (r.status === 401) { location.href = '/?next=/settings'; return null; }
  const ct = r.headers.get('content-type') || '';
  const j = ct.includes('json') ? await r.json().catch(() => ({})) : {};
  if (!r.ok) throw new Error(j.detail || ('Erreur ' + r.status));
  return j;
}
function toast(msg, err) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
let assignableRoles = [];
let roleLabels = {};
let apps = [];
let operators = [];
let machines = [];
let matrixSnapshot = [];
let superadminEmailRef = '';
let usersAll = [];
let usersQuery = '';
let usersRoleFilter = '';

function _norm(s){
  return String(s||'')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z0-9@._\- ]+/g,' ')
    .replace(/\s+/g,' ')
    .trim();
}

function userHaystack(u){
  const role = (u && u.role) ? String(u.role) : '';
  const roleLbl = (roleLabels && roleLabels[role]) ? String(roleLabels[role]) : role;
  return _norm([
    u && u.nom,
    u && u.email,
    role,
    roleLbl,
    u && u.operateur_lie,
    u && u.telephone,
    u && u.machine_nom,
    u && u.machine_id,
    (u && Number(u.actif)===1) ? 'actif' : 'inactif',
  ].filter(Boolean).join(' '));
}

function scoreMatch(hay, tokens){
  let score = 0;
  for(const t of tokens){
    const i = hay.indexOf(t);
    if(i < 0) return null;
    score += i;
    if(i === 0) score -= 6;
  }
  return score;
}

function syncSettingsPageHead(tabId) {
  document.body.classList.toggle('settings-tab-fsc', tabId === 'fsc');
  const titleEl = document.querySelector('.mobile-topbar-title');
  const subEl = document.querySelector('.mobile-topbar-sub');
  if (titleEl) titleEl.textContent = tabId === 'fsc' ? 'Registre FSC' : 'Paramètres';
  if (subEl) {
    if (tabId === 'fsc') {
      subEl.textContent = '';
      subEl.style.display = 'none';
    } else {
      subEl.textContent = 'Gestion des comptes et des accès';
      subEl.style.display = '';
    }
  }
}

function setTab(id) {
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === id);
  });
  ['users', 'matrix', 'defaults', 'fournisseurs', 'operations', 'machines', 'updates', 'audit', 'fsc'].forEach(p => {
    const el = document.getElementById('panel-' + p);
    if (el) el.classList.toggle('hidden', p !== id);
  });
  syncSettingsPageHead(id);
  if (id === 'fournisseurs') loadFournisseurs();
  if (id === 'operations') loadOperationCodes();
  if (id === 'machines') initMachinesPanel();
  if (id === 'updates') loadUpdates();
  if (id === 'audit') loadAuditLogs();
  if (id === 'fsc') initFscPanel();
}

document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
  b.addEventListener('click', () => setTab(b.dataset.tab));
});

function setSidebarOpen(open){
  document.body.classList.toggle('sb-open', !!open);
}
try{
  document.body.classList.add('has-topbar');
  const ov = document.getElementById('sb-ov');
  if(ov) ov.addEventListener('click', ()=>setSidebarOpen(false));
  const burger = document.getElementById('sb-burger');
  if(burger) burger.addEventListener('click', ()=>setSidebarOpen(!document.body.classList.contains('sb-open')));
  const home = document.getElementById('sb-home');
  if(home) home.addEventListener('click', ()=>{ window.location.href = '/'; });
  // Fermer le menu après clic sur un onglet (mobile)
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.addEventListener('click', () => setSidebarOpen(false));
  });
}catch(e){}

function iconSvg(name, size) {
  const s = size || 16;
  const a = 'width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
  if (name === 'moon') return '<svg ' + a + '><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  if (name === 'sun') return '<svg ' + a + '><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  if (name === 'edit') return '<svg ' + a + '><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
  return '';
}
function syncThemeBtn() {
  const light = document.body.classList.contains('light');
  const slot = document.getElementById('theme-ico-slot');
  if (slot) slot.innerHTML = iconSvg(light ? 'sun' : 'moon', 16);
  const lb = document.getElementById('theme-label');
  if (lb) lb.textContent = light ? 'Mode clair' : 'Mode sombre';
}

document.getElementById('theme-btn').onclick = () => {
  if (window.MySifaTheme) MySifaTheme.toggleMode();
  syncThemeBtn();
};
document.getElementById('logout-btn').onclick = async () => {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
  location.href = '/';
};
syncThemeBtn();

document.getElementById('sb-user-chip').onclick = () => { location.href = '/profil'; };

function initSupportSidebar() {
  const ico = document.getElementById('sb-support-ico');
  if (ico) {
    try {
      ico.innerHTML = (window.MySifaSupport && window.MySifaSupport.iconSvg) ? window.MySifaSupport.iconSvg() : '';
    } catch (e) { ico.innerHTML = ''; }
  }
  document.getElementById('sb-support').onclick = () => {
    try {
      if (window.MySifaSupport && typeof window.MySifaSupport.open === 'function') {
        window.MySifaSupport.open({
          user: window.__meUser,
          page: 'Paramètres',
          notify: (m, t) => toast(m, t === 'error'),
          api: api,
        });
      }
    } catch (e) {}
  };
}

async function refreshSidebarUser() {
  const me = await api('/api/auth/me');
  if (!me || typeof me !== 'object') return;
  if (window.MySifaTheme) MySifaTheme.mergeFromUser(me);
  window.__meUser = me;
  const chip = document.getElementById('sb-user-chip');
  if (chip && window.MySifaUserChip) {
    MySifaUserChip.fill(chip, me, {
      roleLabels: roleLabels,
      editIconHtml: iconSvg('edit', 10),
    });
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

function escAttr(s) {
  return String(s || '').replace(/"/g, '&quot;');
}

async function loadFilters() {
  try {
    const f = await api('/api/filters');
    if (f && f.operators) operators = f.operators;
  } catch (e) { operators = []; }
  const opSel = document.getElementById('cu-op');
  opSel.innerHTML = '<option value="">— Opérateur lié —</option>' +
    operators.map(o => '<option value="' + esc(o) + '">' + esc(o) + '</option>').join('');
}

async function loadMachines() {
  try {
    const m = await api('/api/planning/machines');
    machines = Array.isArray(m) ? m : [];
  } catch (e) { machines = []; }
  const ms = document.getElementById('cu-mac');
  ms.innerHTML = '<option value="">— Machine (fabrication) —</option>' +
    machines.map(x => '<option value="' + esc(x.id) + '">' + esc(x.nom) + '</option>').join('');
  fillMacSelect();
}

// ── Machines (horaires planning + métrage total) ─────────────────────────────
const MAC_DAY_ROWS = [
  { key: 'horaires_lundi', label: 'Lundi' },
  { key: 'horaires_mardi', label: 'Mardi' },
  { key: 'horaires_mercredi', label: 'Mercredi' },
  { key: 'horaires_jeudi', label: 'Jeudi' },
  { key: 'horaires_vendredi', label: 'Vendredi' },
  { key: 'horaires_samedi', label: 'Samedi' },
];
const MAC_DEFAULTS_BY_KEY = {
  C1: { pair: { week: { s: 5, e: 20 }, fri: { s: 7, e: 19 } }, impair: { week: { s: 5, e: 20 }, fri: { s: 7, e: 19 } } },
  C2: { pair: { week: { s: 5, e: 13 }, fri: { s: 6, e: 13 } }, impair: { week: { s: 13, e: 20 }, fri: { s: 14, e: 20 } } },
  DSI: { pair: { week: { s: 8, e: 14 }, fri: { s: 8, e: 14 } }, impair: { week: { s: 8, e: 14 }, fri: { s: 8, e: 14 } } },
  REP: { pair: { week: { s: 6, e: 20 }, fri: { s: 7, e: 19 } }, impair: { week: { s: 6, e: 20 }, fri: { s: 7, e: 19 } } },
};
let macSubTab = 'mac-horaires';
let macMachine = null;
let _macPanelReady = false;

function macMachineKey(m) {
  const raw = String((m && (m.code || m.nom)) || '').trim();
  const norm = raw.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (norm.includes('cohesio 1') || norm === 'c1') return 'C1';
  if (norm.includes('cohesio 2') || norm === 'c2') return 'C2';
  if (norm.includes('repiquage') || norm === 'rep') return 'REP';
  if (norm.includes('dsi')) return 'DSI';
  return raw;
}

function macPad(n) { return String(n).padStart(2, '0'); }

function macFloatToHm(f) {
  if (!isFinite(f)) return '';
  const h = Math.floor(f + 1e-6);
  const m = Math.round((f - h) * 60);
  const hh = h + (m >= 60 ? 1 : 0);
  const mm = ((m % 60) + 60) % 60;
  return macPad(hh) + ':' + macPad(mm);
}

function macHmToFloat(raw) {
  const s = String(raw || '').trim();
  if (!/^\d{1,2}:\d{2}$/.test(s)) return null;
  const p = s.split(':');
  const hh = parseInt(p[0], 10);
  const mm = parseInt(p[1], 10);
  if (!isFinite(hh) || !isFinite(mm)) return null;
  return hh + mm / 60;
}

function macParseHorairesCol(val) {
  if (!val || !String(val).trim()) return { start: '', end: '' };
  const parts = String(val).trim().split(',');
  function toHm(x) {
    const t = String(x || '').trim();
    if (/^\d{1,2}:\d{2}$/.test(t)) return t;
    const f = parseFloat(t.replace(',', '.'));
    return isFinite(f) ? macFloatToHm(f) : '';
  }
  return { start: toHm(parts[0]), end: toHm(parts[1] || '') };
}

function macNormalizeParity(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const out = { pair: {}, impair: {} };
  for (const par of ['pair', 'impair']) {
    const block = raw[par];
    if (!block) return null;
    for (const slot of ['week', 'fri']) {
      const w = block[slot];
      let s, e;
      if (Array.isArray(w) && w.length >= 2) { s = +w[0]; e = +w[1]; }
      else if (w && typeof w === 'object') { s = +w.s; e = +w.e; }
      else return null;
      if (!isFinite(s) || !isFinite(e) || e <= s) return null;
      out[par][slot] = { s, e };
    }
  }
  return out;
}

function macGetParityDefaults(m) {
  if (m && m.horaires_parity) {
    try {
      const j = typeof m.horaires_parity === 'string' ? JSON.parse(m.horaires_parity) : m.horaires_parity;
      const norm = macNormalizeParity(j);
      if (norm) return norm;
    } catch (e) { /* ignore */ }
  }
  const mk = macMachineKey(m);
  return MAC_DEFAULTS_BY_KEY[mk] || MAC_DEFAULTS_BY_KEY.C1;
}

function fillMacSelect() {
  const sel = document.getElementById('mac-select');
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = machines.map(x =>
    '<option value="' + esc(x.id) + '">' + esc(x.nom) + '</option>'
  ).join('');
  if (prev && machines.some(x => String(x.id) === String(prev))) sel.value = prev;
  else if (machines.length) sel.value = String(machines[0].id);
}

function setMacSubTab(id) {
  macSubTab = id;
  document.querySelectorAll('.mac-sub-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.macsub === id);
  });
  const hor = document.getElementById('mac-horaires-wrap');
  const met = document.getElementById('mac-metrage-wrap');
  if (hor) hor.classList.toggle('hidden', id !== 'mac-horaires');
  if (met) met.classList.toggle('hidden', id !== 'mac-metrage');
}

function renderMacHorairesForm() {
  const m = macMachine;
  const weekly = document.getElementById('mac-horaires-weekly');
  const parityBox = document.getElementById('mac-horaires-parity');
  if (!weekly || !m) return;
  const mk = macMachineKey(m);
  const isC2 = mk === 'C2';
  if (parityBox) parityBox.classList.toggle('hidden', !isC2);

  let rows = '';
  MAC_DAY_ROWS.forEach(d => {
    const p = macParseHorairesCol(m[d.key]);
    rows += '<tr><td style="font-weight:600">' + esc(d.label) + '</td>' +
      '<td><input type="text" class="mac-h-start" data-field="' + esc(d.key) + '" value="' + esc(p.start) + '" placeholder="05:00" inputmode="numeric" style="width:100%"></td>' +
      '<td><input type="text" class="mac-h-end" data-field="' + esc(d.key) + '" value="' + esc(p.end) + '" placeholder="21:00" inputmode="numeric" style="width:100%"></td></tr>';
  });
  weekly.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Jour</th><th>Début (HH:MM)</th><th>Fin (HH:MM)</th></tr></thead><tbody>' + rows + '</tbody></table></div>';

  if (isC2 && parityBox) {
    const defs = macGetParityDefaults(m);
    function pr(lbl, id, val) {
      return '<div class="fd" style="margin-bottom:8px"><label class="sub" style="display:block;margin-bottom:4px">' + lbl + '</label>' +
        '<input type="text" id="' + id + '" value="' + esc(macFloatToHm(val)) + '" placeholder="07:00" inputmode="numeric" style="width:100%"></div>';
    }
    parityBox.innerHTML =
      '<div style="font-size:12px;font-weight:700;color:var(--text);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px">Semaines paires / impaires (Cohésio 2)</div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">' +
      '<div style="border:1px solid var(--border);border-radius:12px;padding:14px">' +
      '<div style="font-weight:600;margin-bottom:8px;font-size:13px">Semaine paire</div>' +
      pr('Lun–jeu début', 'mac-dp-w-s', defs.pair.week.s) +
      pr('Lun–jeu fin', 'mac-dp-w-e', defs.pair.week.e) +
      pr('Vendredi début', 'mac-dp-f-s', defs.pair.fri.s) +
      pr('Vendredi fin', 'mac-dp-f-e', defs.pair.fri.e) +
      '</div><div style="border:1px solid var(--border);border-radius:12px;padding:14px">' +
      '<div style="font-weight:600;margin-bottom:8px;font-size:13px">Semaine impaire</div>' +
      pr('Lun–jeu début', 'mac-di-w-s', defs.impair.week.s) +
      pr('Lun–jeu fin', 'mac-di-w-e', defs.impair.week.e) +
      pr('Vendredi début', 'mac-di-f-s', defs.impair.fri.s) +
      pr('Vendredi fin', 'mac-di-f-e', defs.impair.fri.e) +
      '</div></div>';
  } else if (parityBox) {
    parityBox.innerHTML = '';
  }
}

function renderMacMetrageForm() {
  const inp = document.getElementById('mac-metrage-inp');
  const hint = document.getElementById('mac-metrage-hint');
  if (!inp || !macMachine) return;
  const v = macMachine.dernier_metrage;
  inp.value = (v != null && isFinite(Number(v))) ? String(Math.round(Number(v))) : '';
  if (hint) {
    hint.textContent = v != null
      ? 'Valeur en base : ' + Math.round(Number(v)).toLocaleString('fr-FR') + ' m'
      : 'Aucune valeur enregistrée — la première saisie définira le compteur.';
  }
}

async function loadMacMachineDetail() {
  const sel = document.getElementById('mac-select');
  const hint = document.getElementById('mac-hint');
  if (!sel || !sel.value) {
    macMachine = null;
    return;
  }
  const id = Number(sel.value);
  try {
    macMachine = await api('/api/planning/machines/' + id);
    if (hint) hint.textContent = (macMachine && macMachine.code) ? ('Code ' + macMachine.code) : '';
    renderMacHorairesForm();
    renderMacMetrageForm();
  } catch (e) {
    macMachine = null;
    if (hint) hint.textContent = '';
    toast(e.message || 'Erreur chargement machine', true);
  }
}

function macCollectHorairesPayload() {
  const payload = {};
  document.querySelectorAll('.mac-h-start').forEach(inp => {
    const field = inp.dataset.field;
    const endInp = document.querySelector('.mac-h-end[data-field="' + field + '"]');
    const st = (inp.value || '').trim();
    const en = endInp ? (endInp.value || '').trim() : '';
    if (st && en) payload[field] = st + ',' + en;
  });
  return payload;
}

function macCollectParityPayload() {
  function v(id) {
    const f = macHmToFloat(document.getElementById(id) && document.getElementById(id).value);
    return f == null ? null : f;
  }
  return {
    pair: { week: { s: v('mac-dp-w-s'), e: v('mac-dp-w-e') }, fri: { s: v('mac-dp-f-s'), e: v('mac-dp-f-e') } },
    impair: { week: { s: v('mac-di-w-s'), e: v('mac-di-w-e') }, fri: { s: v('mac-di-f-s'), e: v('mac-di-f-e') } },
  };
}

async function saveMacHoraires() {
  if (!macMachine) return;
  const id = macMachine.id;
  const mk = macMachineKey(macMachine);
  const bulk = macCollectHorairesPayload();
  try {
    if (mk === 'C2') {
      const nd = macCollectParityPayload();
      function okR(r) { return r.s != null && r.e != null && r.e > r.s && r.s >= 0 && r.e <= 24; }
      if (![nd.pair.week, nd.pair.fri, nd.impair.week, nd.impair.fri].every(okR)) {
        toast('Plages paire/impair invalides (format HH:MM, fin > début)', true);
        return;
      }
      await api('/api/planning/machines/' + id + '/horaires-parity', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nd),
      });
    }
    if (Object.keys(bulk).length) {
      await api('/api/planning/machines/' + id + '/horaires-bulk', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bulk),
      });
    }
    if (mk !== 'C2' && !Object.keys(bulk).length) {
      toast('Renseignez au moins un créneau horaire.', true);
      return;
    }
    toast('Horaires enregistrés.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur enregistrement horaires', true);
  }
}

async function resetMacHoraires() {
  if (!macMachine || !confirm('Réinitialiser les horaires de cette machine aux valeurs par défaut ?')) return;
  const mk = macMachineKey(macMachine);
  const d = MAC_DEFAULTS_BY_KEY[mk] || MAC_DEFAULTS_BY_KEY.C1;
  const id = macMachine.id;
  try {
    if (mk === 'C2') {
      await api('/api/planning/machines/' + id + '/horaires-parity', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(d),
      });
    } else {
      const p = d.pair || d.impair;
      const week = p && p.week ? p.week : null;
      const fri = p && p.fri ? p.fri : null;
      const hs = week && isFinite(week.s) ? week.s : null;
      const he = week && isFinite(week.e) ? week.e : null;
      const fs = fri && isFinite(fri.s) ? fri.s : hs;
      const fe = fri && isFinite(fri.e) ? fri.e : he;
      function pair(a, b) {
        if (a == null || b == null) return null;
        return macFloatToHm(a) + ',' + macFloatToHm(b);
      }
      const payload = {
        horaires_lundi: pair(hs, he),
        horaires_mardi: pair(hs, he),
        horaires_mercredi: pair(hs, he),
        horaires_jeudi: pair(hs, he),
        horaires_vendredi: pair(fs, fe),
      };
      Object.keys(payload).forEach(k => { if (!payload[k]) delete payload[k]; });
      if (Object.keys(payload).length) {
        await api('/api/planning/machines/' + id + '/horaires-bulk', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }
    }
    toast('Horaires réinitialisés.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur réinitialisation', true);
  }
}

async function saveMacMetrage() {
  if (!macMachine) return;
  const raw = (document.getElementById('mac-metrage-inp').value || '').trim().replace(/\s/g, '').replace(',', '.');
  let val = null;
  if (raw !== '') {
    val = parseFloat(raw);
    if (!isFinite(val) || val < 0) {
      toast('Métrage invalide — valeur positive ou nulle attendue.', true);
      return;
    }
  }
  const lbl = macMachine.nom || ('Machine ' + macMachine.id);
  const msg = val == null
    ? 'Effacer le compteur de « ' + lbl + ' » ?'
    : 'Enregistrer le compteur à ' + Math.round(val).toLocaleString('fr-FR') + ' m pour « ' + lbl + ' » ?';
  if (!confirm(msg)) return;
  try {
    await api('/api/settings/machines/' + macMachine.id + '/dernier-metrage', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dernier_metrage: val }),
    });
    toast('Métrage enregistré.');
    await loadMacMachineDetail();
    await loadMachines();
  } catch (e) {
    toast(e.message || 'Erreur enregistrement métrage', true);
  }
}

function initMachinesPanel() {
  fillMacSelect();
  if (!_macPanelReady) {
    _macPanelReady = true;
    document.querySelectorAll('.mac-sub-btn').forEach(b => {
      b.addEventListener('click', () => setMacSubTab(b.dataset.macsub));
    });
    const sel = document.getElementById('mac-select');
    if (sel) sel.addEventListener('change', () => loadMacMachineDetail());
    const hs = document.getElementById('mac-hor-save');
    const hr = document.getElementById('mac-hor-reset');
    const ms = document.getElementById('mac-metr-save');
    if (hs) hs.addEventListener('click', saveMacHoraires);
    if (hr) hr.addEventListener('click', resetMacHoraires);
    if (ms) ms.addEventListener('click', saveMacMetrage);
  }
  setMacSubTab(macSubTab);
  loadMacMachineDetail();
}

function fillRoleSelect() {
  const s = document.getElementById('cu-role');
  s.innerHTML = assignableRoles.map(r =>
    '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>'
  ).join('');
}

const PROFILE_FIELDS = ['nom', 'email', 'telephone', 'adresse', 'date_naissance'];

function profileFieldFilled(val) {
  return String(val == null ? '' : val).trim().length > 0;
}

function profileCompletionPercent(u) {
  if (!u || typeof u !== 'object') return 0;
  let n = 0;
  PROFILE_FIELDS.forEach((k) => { if (profileFieldFilled(u[k])) n += 1; });
  return Math.round((n / PROFILE_FIELDS.length) * 100);
}

function profileRingTier(pct) {
  if (pct >= 80) return 'high';
  if (pct >= 40) return 'mid';
  return 'low';
}

function profileRingHtml(pct) {
  const p = Math.max(0, Math.min(100, Number(pct) || 0));
  const r = 14;
  const c = 2 * Math.PI * r;
  const off = c * (1 - p / 100);
  const tier = profileRingTier(p);
  return '<span class="prof-ring" data-tier="' + tier + '" title="Profil complété à ' + p + ' %">' +
    '<svg viewBox="0 0 34 34" aria-hidden="true">' +
    '<circle class="prof-ring-track" cx="17" cy="17" r="' + r + '" fill="none" stroke-width="3"/>' +
    '<circle class="prof-ring-bar" cx="17" cy="17" r="' + r + '" fill="none" stroke-width="3"' +
    ' stroke-dasharray="' + c.toFixed(2) + '" stroke-dashoffset="' + off.toFixed(2) + '"' +
    ' transform="rotate(-90 17 17)"/>' +
    '</svg>' +
    '<span class="prof-ring-label">' + p + '%</span>' +
    '</span>';
}

async function loadUsers() {
  const list = await api('/api/users');
  usersAll = Array.isArray(list) ? list.slice() : [];
  usersAll.sort((a,b)=>{
    // Tri par service (rôle) d'abord, puis par nom alphabétique
    const roleA = String(a && a.role || '').toLowerCase();
    const roleB = String(b && b.role || '').toLowerCase();
    if(roleA !== roleB) return roleA.localeCompare(roleB,'fr');
    const an = _norm(a && a.nom);
    const bn = _norm(b && b.nom);
    if(an !== bn) return an.localeCompare(bn,'fr');
    return _norm(a && a.email).localeCompare(_norm(b && b.email),'fr');
  });
  renderUsersList();
}

function renderUsersList(){
  const box = document.getElementById('users-list');
  const hint = document.getElementById('users-q-hint');
  if(!box) return;
  if(!usersAll.length){
    box.innerHTML = '<p class="sub">Aucun utilisateur.</p>';
    if(hint) hint.textContent = '';
    return;
  }

  const q = _norm(usersQuery);
  const tokens = q ? q.split(' ').filter(Boolean) : [];
  let list = usersAll;

  // Filtrage par service (rôle)
  if(usersRoleFilter && usersRoleFilter !== ''){
    list = list.filter(u => (u.role || '') === usersRoleFilter);
  }

  if(tokens.length){
    const scored = [];
    for(const u of list){
      const hay = userHaystack(u);
      const sc = scoreMatch(hay, tokens);
      if(sc != null) scored.push({u, sc});
    }
    scored.sort((a,b)=> (a.sc - b.sc) || _norm(a.u.nom).localeCompare(_norm(b.u.nom),'fr'));
    list = scored.map(x=>x.u);
  }
  if(hint) hint.textContent = (list.length + '/' + usersAll.length);

  box.innerHTML = list.map(u => {
    const act = Number(u.actif) === 1;
    const role = String(u.role || '').toLowerCase().trim();
    const pillCls = 'pill pill--' + esc(role || 'fabrication');
    const meta = [
      u.identifiant ? ('Id: ' + esc(u.identifiant)) : '',
      u.operateur_lie ? ('Op: ' + esc(u.operateur_lie)) : '',
      u.machine_nom ? ('Machine: ' + esc(u.machine_nom)) : '',
      u.telephone ? ('Tel: ' + esc(u.telephone)) : '',
    ].filter(Boolean).join(' · ');
    const profPct = profileCompletionPercent(u);
    return '<div class="row-user">' +
      '<div style="display:flex;align-items:center;gap:10px">' +
        profileRingHtml(profPct) +
        '<div><strong>' + esc(u.nom) + '</strong> <span class="' + pillCls + '">' + esc(roleLabels[u.role] || u.role) + '</span>' +
        (act ? '' : ' <span class="pill pill--inactive">Inactif</span>') +
        '<div style="font-size:11px;color:var(--muted);margin-top:4px">' + esc(u.email) + (meta ? (' · ' + meta) : '') + '</div></div>' +
        '<button type="button" class="btn btn-sec copy-user-btn" data-copy="' + u.id + '" title="Copier les identifiants" style="padding:6px 8px">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' +
        '</button>' +
      '</div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">' +
      '<button type="button" class="btn btn-sec" data-edit="' + u.id + '">Modifier</button>' +
      '<button type="button" class="btn btn-sec" data-reset="' + u.id + '">Reset MDP</button>' +
      (act ? '<button type="button" class="btn btn-sec" data-off="' + u.id + '">Désactiver</button>'
        : '<button type="button" class="btn btn-sec" data-on="' + u.id + '">Réactiver</button>') +
      '<button type="button" class="btn btn-sec" data-del="' + u.id + '" title="Supprimer" style="color:var(--danger);padding:6px 8px">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>' +
      '</button>' +
      '</div></div>';
  }).join('');

  box.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => openEdit(Number(b.dataset.edit)));
  box.querySelectorAll('[data-reset]').forEach(b => b.onclick = () => resetPwd(Number(b.dataset.reset)));
  box.querySelectorAll('[data-off]').forEach(b => b.onclick = () => setActif(Number(b.dataset.off), 0));
  box.querySelectorAll('[data-on]').forEach(b => b.onclick = () => setActif(Number(b.dataset.on), 1));
  box.querySelectorAll('[data-copy]').forEach(b => b.onclick = () => copyUserCredentials(Number(b.dataset.copy)));
  box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => deleteUser(Number(b.dataset.del)));
}

async function deleteUser(id) {
  const u = usersAll.find(x => x.id === id);
  if (!u) return;
  const isAdmin = (u.email || '').toLowerCase().includes('admin') || (u.nom || '').toLowerCase() === 'administrateur';
  if (isAdmin) {
    toast('Impossible de supprimer un administrateur', 'error');
    return;
  }
  const hasLinkages = u.operateur_lie || u.identifiant || (u.machine_nom && u.machine_nom !== '—');
  const warningMsg = hasLinkages ? '\n\n⚠️ Cet utilisateur est lié à des données (opérateur, machine...). La suppression peut affecter l\'historique.' : '';
  if (!confirm('Supprimer définitivement l\'utilisateur "' + u.nom + '" (' + u.email + ') ?' + warningMsg + '\n\nCette action est irréversible.')) return;
  try {
    await api('/api/users/' + id, { method: 'DELETE' });
    toast('Utilisateur supprimé', 'success');
    await loadUsers();
    await loadMatrix();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function setActif(id, v) {
  try {
    await api('/api/users/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actif: v }) });
    toast(v ? 'Compte réactivé' : 'Compte désactivé');
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
}

async function resetPwd(id) {
  if (!confirm('Générer un mot de passe temporaire ?')) return;
  try {
    const r = await api('/api/users/' + id + '/reset-password', { method: 'POST' });
    if (r && r.temp_password) alert('Mot de passe temporaire : ' + r.temp_password);
    toast('Mot de passe régénéré');
  } catch (e) { toast(e.message, true); }
}

async function copyUserCredentials(id) {
  const u = usersAll.find(x => x.id === id);
  if (!u) return;
  const lines = [
    'Nom : ' + (u.nom || ''),
    'Email : ' + (u.email || ''),
    'Identifiant : ' + (u.identifiant || ''),
    'Rôle : ' + (roleLabels[u.role] || u.role || ''),
  ];
  if (u.operateur_lie) lines.push('Opérateur : ' + u.operateur_lie);
  if (u.machine_nom) lines.push('Machine : ' + u.machine_nom);
  if (u.telephone) lines.push('Téléphone : ' + u.telephone);
  const text = lines.join('\n');
  try {
    await navigator.clipboard.writeText(text);
    toast('Identifiants copiés');
  } catch (e) {
    toast('Erreur copie : ' + e.message, true);
  }
}

function downloadUsersCSV(){
  // Exporter tous les utilisateurs (pas seulement les filtrés)
  if(!usersAll || usersAll.length===0){
    toast('Aucun utilisateur à exporter', true);
    return;
  }
  const headers=['Nom','Email','Rôle','Actif','Dernière connexion','Opérateur lié','Machine'];
  const rows=usersAll.map(u=>{
    const nom=esc(u.nom||'');
    const email=esc(u.email||'');
    const role=esc(roleLabels[u.role]||u.role||'');
    const actif=u.actif?'Oui':'Non';
    const lastLogin=u.last_login?new Date(u.last_login).toLocaleString('fr-FR'):'Jamais';
    const op=esc(u.operateur||'');
    const mac=esc(u.machine_nom||'');
    return [nom,email,role,actif,lastLogin,op,mac].map(f=>'"'+f.replace(/"/g,'""')+'"').join(';');
  });
  const csv=[headers.join(';')].concat(rows).join('\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;
  a.download='utilisateurs_mysifa_'+new Date().toISOString().slice(0,10)+'.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast(usersAll.length+' utilisateurs exportés');
}

function syncCuRoleUI() {
  const r = document.getElementById('cu-role').value;
  // Cacher opérateur lié pour fabrication et les autres rôles hors production
  const hideOp = ['fabrication', 'direction', 'administration', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
  document.getElementById('cu-op').style.display = hideOp ? 'none' : '';
  document.getElementById('cu-mac').style.display = r === 'fabrication' ? '' : 'none';
}
document.getElementById('cu-role').addEventListener('change', syncCuRoleUI);

document.getElementById('cu-go').onclick = async () => {
  const nom = document.getElementById('cu-nom').value.trim();
  const identifiant = document.getElementById('cu-ident').value.trim();
  const email = document.getElementById('cu-email').value.trim();
  const password = document.getElementById('cu-pwd').value;
  const role = document.getElementById('cu-role').value;
  const operateur_lie = document.getElementById('cu-op').value || null;
  const mid = document.getElementById('cu-mac').value;
  const machine_id = mid ? Number(mid) : null;
  if (!nom || !email || !password || !role) return toast('Champs requis', true);
  try {
    await api('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, identifiant, email, password, role, operateur_lie, machine_id }) });
    toast('Utilisateur créé');
    document.getElementById('cu-nom').value = '';
    document.getElementById('cu-ident').value = '';
    document.getElementById('cu-email').value = '';
    document.getElementById('cu-pwd').value = '';
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
};

// Recherche utilisateurs (client-side, sur toutes les colonnes)
try{
  const uq = document.getElementById('users-q');
  if(uq){
    uq.addEventListener('input', ()=>{
      usersQuery = uq.value || '';
      renderUsersList();
    });
  }
}catch(e){}

// Filtre par service
function fillRoleFilterSelect() {
  const sel = document.getElementById('users-role-filter');
  if(!sel) return;
  sel.innerHTML = '<option value="">Tous les services</option>' +
    assignableRoles.map(r => '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>').join('');
}
try{
  const rf = document.getElementById('users-role-filter');
  if(rf){
    rf.addEventListener('change', ()=>{
      usersRoleFilter = rf.value || '';
      renderUsersList();
    });
  }
}catch(e){}

async function openEdit(id) {
  let u;
  try { u = await api('/api/users/' + id); } catch (e) { toast(e.message, true); return; }
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto';
  const isDesignatedSup = superadminEmailRef && String(u.email || '').trim().toLowerCase() === superadminEmailRef && u.role === 'superadmin';
  const roleOpts = isDesignatedSup
    ? '<option value="superadmin" selected>Super admin</option>'
    : assignableRoles.map(r => '<option value="' + esc(r) + '"' + (u.role === r ? ' selected' : '') + '>' + esc(roleLabels[r] || r) + '</option>').join('');

  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:16px">Modifier</h3>' +
    '<label class="sub">Nom</label><input id="ed-nom" value="' + esc(u.nom) + '" style="margin-bottom:10px">' +
    '<label class="sub">Identifiant</label><input id="ed-ident" value="' + esc(u.identifiant || '') + '" style="margin-bottom:10px" placeholder="auto si vide">' +
    '<label class="sub">Email</label><input id="ed-email" type="email" value="' + esc(u.email) + '" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' +
    '<label class="sub">Téléphone</label><input id="ed-tel" value="' + esc(u.telephone || '') + '" style="margin-bottom:10px" placeholder="">' +
    '<label class="sub">Adresse</label><input id="ed-adr" value="' + esc(u.adresse || '') + '" style="margin-bottom:10px" placeholder="">' +
    '<label class="sub">Date de naissance</label><input id="ed-birth" type="date" value="' + esc(u.date_naissance || '') + '" style="margin-bottom:10px">' +
    '<label class="sub">Rôle</label><select id="ed-role" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' + roleOpts + '</select>' +
    '<div id="ed-op-wrap"><label class="sub">Opérateur lié</label><select id="ed-op" style="margin-bottom:10px">' +
    '<option value="">—</option>' + operators.map(o => '<option value="' + esc(o) + '"' + (u.operateur_lie === o ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select></div>' +
    '<div id="ed-mac-wrap"><label class="sub">Machine</label><select id="ed-mac" style="margin-bottom:10px">' +
    '<option value="">—</option>' + machines.map(m => '<option value="' + esc(m.id) + '"' + (String(u.machine_id) === String(m.id) ? ' selected' : '') + '>' + esc(m.nom) + '</option>').join('') + '</select></div>' +
    '<label class="sub" style="display:flex;align-items:center;gap:8px"><input type="checkbox" id="ed-act" ' + (Number(u.actif) === 1 ? 'checked' : '') + '> Compte actif</label>' +
    '<label class="sub">Nouveau mot de passe (optionnel)</label><input id="ed-pwd" type="password" style="margin-bottom:10px">' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ed-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ed-save">Enregistrer</button></div>';

  function syncEd() {
    const r = dlg.querySelector('#ed-role').value;
    // Cacher opérateur lié pour fabrication et les autres rôles hors production
    const hideOp = ['fabrication', 'direction', 'administration', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
    dlg.querySelector('#ed-op-wrap').style.display = hideOp ? 'none' : '';
    dlg.querySelector('#ed-mac-wrap').style.display = (r === 'fabrication') ? '' : 'none';
  }
  dlg.querySelector('#ed-role').addEventListener('change', syncEd);
  syncEd();

  dlg.querySelector('#ed-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ed-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#ed-nom').value.trim(),
      identifiant: dlg.querySelector('#ed-ident').value.trim(),
      email: dlg.querySelector('#ed-email').value.trim(),
      telephone: dlg.querySelector('#ed-tel').value.trim(),
      adresse: dlg.querySelector('#ed-adr').value.trim(),
      date_naissance: dlg.querySelector('#ed-birth').value.trim(),
      role: dlg.querySelector('#ed-role').value,
      operateur_lie: dlg.querySelector('#ed-op').value || null,
      machine_id: dlg.querySelector('#ed-mac').value ? Number(dlg.querySelector('#ed-mac').value) : null,
      actif: dlg.querySelector('#ed-act').checked ? 1 : 0,
    };
    const np = dlg.querySelector('#ed-pwd').value;
    if (np) body.password = np;
    try {
      await api('/api/users/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      toast('Utilisateur mis à jour');
      backdrop.remove();
      await loadUsers();
      await loadMatrix();
    } catch (e) { toast(e.message, true); }
  };

  backdrop.appendChild(dlg);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}

async function onAccessToggle(ev) {
  const t = ev.target;
  if (!t || !t.classList || !t.classList.contains('chk-edit')) return;
  const uid = Number(t.dataset.uid);
  const appId = t.dataset.app;
  const checked = t.checked;
  const row = matrixSnapshot.find(r => r.id === uid);
  if (!row || !row.access_default) return;
  const def = !!row.access_default[appId];
  const ov = Object.assign({}, row.access_overrides || {});
  if (checked === def) delete ov[appId];
  else ov[appId] = checked;
  try {
    await api('/api/users/' + uid, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ access_overrides: ov }),
    });
    toast('Accès mis à jour');
    await loadMatrix();
    await loadUsers();
  } catch (e) {
    toast(e.message, true);
    t.checked = !checked;
  }
}

async function loadMatrix() {
  const data = await api('/api/settings/access-matrix');
  if (!data) return;
  apps = data.apps || [];
  roleLabels = data.role_labels || roleLabels;
  const matrix = data.matrix || [];
  matrixSnapshot = matrix;

  const th = '<th>Utilisateur</th><th>Rôle</th>' + apps.map(a => '<th title="' + esc(a.hint || '') + '">' + esc(a.label) + '</th>').join('');
  const tr = matrix.map(row => {
    const isRowSuper = row.role === 'superadmin';
    const cells = apps.map(a => {
      const ok = row.access && row.access[a.id];
      const hasOv = row.access_overrides && Object.prototype.hasOwnProperty.call(row.access_overrides, a.id);
      if (a.id === 'settings' || isRowSuper) {
        return '<td class="chk"><span class="dot' + (ok ? '' : ' no') + '" title="Non modifiable ici"></span></td>';
      }
      const perso = hasOv ? '<span class="cell-ov">perso</span>' : '';
      return '<td class="chk"><label style="display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;margin:0">' +
        '<input type="checkbox" class="chk-edit" data-uid="' + row.id + '" data-app="' + esc(a.id) + '" ' + (ok ? 'checked' : '') + (Number(row.actif) !== 1 ? ' disabled' : '') + ' />' +
        perso + '</label></td>';
    }).join('');
    const dim = Number(row.actif) !== 1 ? 'opacity:.55' : '';
    return '<tr style="' + dim + '"><td><strong>' + esc(row.nom) + '</strong><div style="font-size:11px;color:var(--muted)">' + esc(row.email) + '</div></td><td>' + esc(row.role_label || row.role) + '</td>' + cells + '</tr>';
  }).join('');
  const wrap = document.getElementById('matrix-table');
  wrap.innerHTML = '<table><thead><tr>' + th + '</tr></thead><tbody>' + tr + '</tbody></table>';
  wrap.querySelectorAll('.chk-edit').forEach(cb => { cb.addEventListener('change', onAccessToggle); });

  const leg = document.getElementById('role-legend');
  leg.innerHTML = (data.role_defaults || []).map(d => {
    const bits = apps.map(a => {
      const ok = d.access && d.access[a.id];
      return '<span class="dot' + (ok ? '' : ' no') + '" style="margin-right:4px"></span>' + esc(a.label);
    }).join(' · ');
    return '<div class="item"><strong>' + esc(d.label) + '</strong> <code style="font-size:11px">' + esc(d.role) + '</code><div style="margin-top:8px;line-height:1.6">' + bits + '</div></div>';
  }).join('');
}

// ─── Fournisseurs FSC ──────────────────────────────────────────────

let fournisseursAll = [];

// Sub-tab navigation for fournisseurs
document.querySelectorAll('.four-sub-btn').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.four-sub-btn').forEach(x => x.classList.toggle('active', x.dataset.foursub === b.dataset.foursub));
    ['four-certifs', 'four-hist'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('hidden', id !== b.dataset.foursub);
    });
    if (b.dataset.foursub === 'four-hist') fillFourHistSelect();
  });
});

async function loadFournisseurs() {
  try {
    const data = await api('/api/fournisseurs');
    fournisseursAll = Array.isArray(data) ? data : [];
  } catch (e) { fournisseursAll = []; toast(e.message, true); }
  renderFournisseursTable();
  fillFourHistSelect();
}

function renderFournisseursTable() {
  const wrap = document.getElementById('four-table-wrap');
  if (!wrap) return;
  if (!fournisseursAll.length) {
    wrap.innerHTML = '<p class="sub" style="padding:12px">Aucun fournisseur enregistré.</p>';
    return;
  }
  wrap.innerHTML = '<table><thead><tr><th>Nom</th><th>Licence FSC</th><th>Certificat FSC</th><th>Code-barre traça</th><th></th></tr></thead><tbody>' +
    fournisseursAll.map(f => '<tr>' +
      '<td><strong>' + esc(f.nom) + '</strong></td>' +
      '<td><code>' + esc(f.licence || '—') + '</code></td>' +
      '<td><code>' + esc(f.certificat || '—') + '</code></td>' +
      '<td>' + (f.traca_photo_url || f.traca_explication || f.traca_exemple_code
        ? '<span style="color:var(--ok);font-size:12px">✓ Renseigné</span>'
        : '<span style="color:var(--muted);font-size:12px">— Non renseigné</span>') + '</td>' +
      '<td style="display:flex;gap:6px;justify-content:flex-end">' +
        '<button type="button" class="btn btn-sec" data-fedit="' + f.id + '">Modifier</button>' +
        '<button type="button" class="btn btn-sec" data-fdel="' + f.id + '" style="color:var(--danger)">Supprimer</button>' +
      '</td></tr>'
    ).join('') + '</tbody></table>';
  wrap.querySelectorAll('[data-fedit]').forEach(b => b.onclick = () => openEditFournisseur(Number(b.dataset.fedit)));
  wrap.querySelectorAll('[data-fdel]').forEach(b => b.onclick = () => deleteFournisseur(Number(b.dataset.fdel)));
}

document.getElementById('cf-go').onclick = async () => {
  const nom = document.getElementById('cf-nom').value.trim();
  const licence = document.getElementById('cf-licence').value.trim();
  const certificat = document.getElementById('cf-certificat').value.trim();
  if (!nom) return toast('Nom du fournisseur requis', true);
  try {
    await api('/api/fournisseurs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, licence, certificat }),
    });
    toast('Fournisseur ajouté');
    document.getElementById('cf-nom').value = '';
    document.getElementById('cf-licence').value = '';
    document.getElementById('cf-certificat').value = '';
    await loadFournisseurs();
  } catch (e) { toast(e.message, true); }
};

async function openEditFournisseur(id) {
  const f = fournisseursAll.find(x => x.id === id);
  if (!f) return;
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto';
  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:16px">Modifier le fournisseur</h3>' +
    '<label class="sub">Nom</label><input id="ef-nom" value="' + esc(f.nom) + '" style="margin-bottom:10px">' +
    '<label class="sub">Licence FSC</label><input id="ef-licence" value="' + esc(f.licence || '') + '" style="margin-bottom:10px" placeholder="ex: FSC-C004451">' +
    '<label class="sub">Certificat FSC</label><input id="ef-certificat" value="' + esc(f.certificat || '') + '" style="margin-bottom:10px" placeholder="ex: CU-COC-807907">' +
    '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border)">' +
    '<p style="margin:0 0 10px;font-size:13px;font-weight:600;color:var(--text)">Code-barre de traçabilité</p>' +
    '<p style="margin:0 0 10px;font-size:12px;color:var(--text2)">Aide pour les opérateurs : quel code scanner sur les bobines de ce fournisseur.</p>' +
    '<label class="sub">Photo de l\'étiquette</label>' +
    '<div id="ef-photo-preview" style="margin-bottom:10px"></div>' +
    '<input type="file" id="ef-photo-input" accept="image/*" style="display:none">' +
    '<div style="display:flex;gap:8px;margin-bottom:12px">' +
    '<button type="button" class="btn btn-sec" id="ef-photo-pick" style="font-size:12px">Choisir une photo</button>' +
    '<button type="button" class="btn btn-sec" id="ef-photo-del" style="font-size:12px;color:var(--danger);display:none">Supprimer la photo</button></div>' +
    '<label class="sub">Explication (emplacement, description du code)</label>' +
    '<textarea id="ef-traca-exp" placeholder="Ex: Scanner le code en bas à gauche de l\'étiquette bobine — code EAN-13 commençant par 376" ' +
    'style="width:100%;min-height:72px;resize:vertical;margin-bottom:10px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;box-sizing:border-box"></textarea>' +
    '<label class="sub">Exemple de code (scanner une vraie étiquette pour le remplir)</label>' +
    '<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">' +
    '<input type="text" id="ef-traca-code" placeholder="Ex: 3760123456789" style="flex:1;font-family:monospace">' +
    '<button type="button" class="btn btn-sec" id="ef-scan-example" style="font-size:12px;white-space:nowrap">Scanner</button></div>' +
    '<p class="sub" style="margin-top:4px;font-size:11px">Utilisez « Scanner » pour remplir automatiquement en scannant une vraie bobine.</p></div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ef-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ef-save">Enregistrer</button></div>';

  const expEl = dlg.querySelector('#ef-traca-exp');
  const codeEl = dlg.querySelector('#ef-traca-code');
  const photoPreview = dlg.querySelector('#ef-photo-preview');
  const photoInput = dlg.querySelector('#ef-photo-input');
  const photoDelBtn = dlg.querySelector('#ef-photo-del');
  expEl.value = f.traca_explication || '';
  codeEl.value = f.traca_exemple_code || '';

  function refreshPhotoPreview(url) {
    if (url) {
      photoPreview.innerHTML = '<img src="' + esc(url) + '" alt="" style="max-width:100%;max-height:200px;border-radius:8px;border:1px solid var(--border);display:block;margin-bottom:4px">';
      photoDelBtn.style.display = '';
    } else {
      photoPreview.innerHTML = '<p class="sub" style="margin:0 0 8px;font-size:12px">Aucune photo</p>';
      photoDelBtn.style.display = 'none';
    }
  }
  refreshPhotoPreview(f.traca_photo_url || null);

  dlg.querySelector('#ef-photo-pick').onclick = () => photoInput.click();
  photoInput.onchange = async () => {
    const file = photoInput.files[0];
    photoInput.value = '';
    if (!file) return;
    const fd = new FormData();
    fd.append('photo', file);
    try {
      const res = await fetch(API + '/api/fournisseurs/' + id + '/traca-photo', { method: 'POST', credentials: 'include', body: fd });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = j.detail;
        const msg = typeof d === 'string' ? d : (Array.isArray(d) && d[0] && d[0].msg ? d[0].msg : 'Erreur upload');
        throw new Error(msg);
      }
      refreshPhotoPreview(j.url);
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) fi.traca_photo_url = j.url;
      toast('Photo enregistrée');
    } catch (e) { toast(e.message, true); }
  };

  photoDelBtn.onclick = async () => {
    if (!confirm('Supprimer la photo ?')) return;
    try {
      const res = await fetch(API + '/api/fournisseurs/' + id + '/traca-photo', { method: 'DELETE', credentials: 'include' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof j.detail === 'string' ? j.detail : 'Erreur');
      refreshPhotoPreview(null);
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) fi.traca_photo_url = null;
      toast('Photo supprimée');
    } catch (e) { toast(e.message, true); }
  };

  dlg.querySelector('#ef-scan-example').onclick = async () => {
    try {
      if (typeof startTracaExampleScan !== 'function') return;
      await startTracaExampleScan(function(code) { if (code) codeEl.value = code; });
    } catch (e) {}
  };

  dlg.querySelector('#ef-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ef-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#ef-nom').value.trim(),
      licence: dlg.querySelector('#ef-licence').value.trim(),
      certificat: dlg.querySelector('#ef-certificat').value.trim(),
      traca_explication: expEl.value.trim(),
      traca_exemple_code: codeEl.value.trim(),
    };
    if (!body.nom) return toast('Nom requis', true);
    try {
      await api('/api/fournisseurs/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) {
        fi.traca_explication = body.traca_explication || null;
        fi.traca_exemple_code = body.traca_exemple_code || null;
        fi.nom = body.nom;
        fi.licence = body.licence || null;
        fi.certificat = body.certificat || null;
      }
      toast('Fournisseur mis à jour');
      backdrop.remove();
      await loadFournisseurs();
    } catch (e) { toast(e.message, true); }
  };
  backdrop.appendChild(dlg);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}

async function deleteFournisseur(id) {
  const f = fournisseursAll.find(x => x.id === id);
  if (!f) return;
  if (!confirm('Supprimer le fournisseur "' + f.nom + '" ?')) return;
  try {
    await api('/api/fournisseurs/' + id, { method: 'DELETE' });
    toast('Fournisseur supprimé');
    await loadFournisseurs();
  } catch (e) { toast(e.message, true); }
}

// Historique par fournisseur
function fillFourHistSelect() {
  const sel = document.getElementById('fh-four');
  if (!sel) return;
  const val = sel.value;
  sel.innerHTML = '<option value="">— Choisir un fournisseur —</option>' +
    fournisseursAll.map(f => '<option value="' + f.id + '">' + esc(f.nom) + '</option>').join('');
  sel.value = val;
}

document.getElementById('fh-four').addEventListener('change', async function() {
  const id = Number(this.value);
  const box = document.getElementById('fh-results');
  if (!id) { box.innerHTML = ''; return; }
  box.innerHTML = '<p class="sub">Chargement…</p>';
  try {
    const data = await api('/api/fournisseurs/' + id + '/receptions');
    const recs = data.receptions || [];
    if (!recs.length) {
      box.innerHTML = '<p class="sub">Aucune réception pour ce fournisseur.</p>';
      return;
    }
    box.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Date</th><th>Opérateur</th><th>Bobines</th><th>Certificat FSC</th><th>Note</th></tr></thead><tbody>' +
      recs.map(r => '<tr>' +
        '<td style="font-family:monospace;font-size:12px">' + esc((r.created_at || '').slice(0, 16).replace('T', ' ')) + '</td>' +
        '<td>' + esc(r.created_by_name || '—') + '</td>' +
        '<td>' + esc(r.nb_bobines) + '</td>' +
        '<td><code>' + esc(r.certificat_fsc || '—') + '</code></td>' +
        '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">' + esc(r.note || '') + '</td>' +
      '</tr>').join('') + '</tbody></table></div>';
  } catch (e) { box.innerHTML = '<p class="sub" style="color:var(--danger)">' + esc(e.message) + '</p>'; }
});

(async function init() {
  try {
    const meta = await api('/api/settings/access-matrix');
    superadminEmailRef = String(meta.superadmin_email || '').trim().toLowerCase();
    assignableRoles = meta.assignable_roles || [];
    roleLabels = meta.role_labels || {};
    apps = meta.apps || [];
    fillRoleSelect();
    fillRoleFilterSelect();
    await refreshSidebarUser();
    initSupportSidebar();
    await loadFilters();
    await loadMachines();
    syncCuRoleUI();
    await loadUsers();
    await loadMatrix();
  } catch (e) {
    toast(e.message || 'Erreur chargement', true);
  }
})();

// ── Mises à jour ──────────────────────────────────────────────────────────────
const SCOPE_LABELS = { planning: '📋 Planning', fabrication: '⚙️ Saisie de prod.', global: '🌐 Global' };

let _updatesData = [];
let _openAckId = null;

async function loadUpdates() {
  const box = document.getElementById('upd-list');
  if (!box) return;
  try {
    _updatesData = await api('/api/updates') || [];
    renderUpdatesList();
  } catch(e) {
    box.innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
  }
}

function toParisTime(isoStr) {
  if (!isoStr) return '—';
  try {
    // acknowledged_at est stocké en UTC (datetime.now() côté serveur)
    const d = new Date(isoStr.includes('T') ? isoStr + 'Z' : isoStr);
    return d.toLocaleString('fr-FR', {
      timeZone: 'Europe/Paris',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch(e) { return isoStr.slice(0, 16).replace('T', ' '); }
}

function renderUpdatesList() {
  const box = document.getElementById('upd-list');
  if (!_updatesData.length) {
    box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune annonce pour le moment.</p>';
    return;
  }
  box.innerHTML = _updatesData.map(u => {
    const scopeLbl = SCOPE_LABELS[u.scope] || u.scope;
    const dt = u.created_at ? u.created_at.slice(0, 10).split('-').reverse().join('/') : '—';
    const activeTag = u.active
      ? '<span style="font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(52,211,153,.15);color:#34d399;border:1px solid rgba(52,211,153,.3);font-weight:700">Actif</span>'
      : '<span style="font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(148,163,184,.12);color:var(--muted);border:1px solid var(--border);font-weight:700">Archivé</span>';
    const ackCount = u.nb_ack || 0;
    const isOpen = _openAckId === u.id;
    return `
<div style="border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:10px">
  <div style="display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;background:var(--card)" onclick="toggleAck(${u.id})">
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
        <span style="font-size:12px;color:var(--muted)">${esc(scopeLbl)}</span>
        <span style="font-size:11px;color:var(--muted)">·</span>
        <span style="font-size:12px;color:var(--muted)">${dt}</span>
        ${activeTag}
      </div>
      <div style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(u.titre)}</div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <div style="font-size:18px;font-weight:800;color:var(--accent)">${ackCount}</div>
      <div style="font-size:10px;color:var(--muted)">lecture(s)</div>
    </div>
    <button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();showUpdatePreview(${u.id})">Aperçu</button>
    ${ackCount === 0 ? `<button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();openEditUpdateModal(${u.id})">Modifier</button><button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px;color:var(--danger);border-color:var(--danger)" onclick="event.stopPropagation();deleteUpdate(${u.id})">Supprimer</button>` : ''}
    <button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();toggleActive(${u.id},${u.active})">${u.active ? 'Archiver' : 'Réactiver'}</button>
    <span style="font-size:16px;color:var(--muted);transition:transform .2s;${isOpen ? 'transform:rotate(180deg)' : ''}">▾</span>
  </div>
  <div id="ack-panel-${u.id}" style="display:${isOpen ? 'block' : 'none'};border-top:1px solid var(--border);padding:14px 16px;background:rgba(0,0,0,.08)">
    <div id="ack-content-${u.id}"><em style="color:var(--muted);font-size:13px">Chargement…</em></div>
  </div>
</div>`;
  }).join('');
}

function showUpdatePreview(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  const ov = document.createElement('div');
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:900;display:flex;align-items:center;justify-content:center';
  ov.innerHTML = `<div style="background:var(--card);border:1px solid var(--border2);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.6)">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px">
      <div>
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:4px">${esc(SCOPE_LABELS[u.scope]||u.scope)}</div>
        <h2 style="font-size:16px;margin:0">${esc(u.titre)}</h2>
      </div>
      <button onclick="this.closest('[style*=fixed]').remove()" style="border:none;background:none;color:var(--muted);font-size:22px;cursor:pointer;padding:0 0 0 12px;line-height:1;flex-shrink:0">×</button>
    </div>
    <div style="font-size:13px;line-height:1.7;color:var(--text2)">${u.message}</div>
    <button class="btn" style="width:100%;margin-top:20px;padding:12px;font-size:14px" onclick="this.closest('[style*=fixed]').remove()">Fermer</button>
  </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function toggleAck(id) {
  if (_openAckId === id) {
    _openAckId = null;
    renderUpdatesList();
    return;
  }
  _openAckId = id;
  renderUpdatesList();
  const contentEl = document.getElementById('ack-content-' + id);
  if (!contentEl) return;
  try {
    const data = await api('/api/updates/' + id + '/acknowledgements');
    const acks = data.acknowledgements || [];
    if (!acks.length) {
      contentEl.innerHTML = '<p style="color:var(--muted);font-size:13px;margin:0">Personne n\'a encore lu cette annonce.</p>';
      return;
    }
    contentEl.innerHTML = '<div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">' + acks.length + ' lecture(s)</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:6px">' +
      acks.map(a => {
        const dt = toParisTime(a.acknowledged_at);
        return `<div style="padding:6px 10px;border-radius:8px;background:var(--bg);border:1px solid var(--border);font-size:12px">
          <strong>${esc(a.user_nom || a.email || '—')}</strong>
          ${a.email && a.user_nom ? '<span style="color:var(--muted);margin-left:4px">' + esc(a.email) + '</span>' : ''}
          <div style="font-size:10px;color:var(--muted);margin-top:2px">${esc(dt)}</div>
        </div>`;
      }).join('') + '</div>';
  } catch(e) {
    contentEl.innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
  }
}

const APP_PAGES = {
  planning: [
    {value: '', label: 'Toutes les pages'},
    {value: 'planning', label: 'Planning'}
  ],
  fabrication: [
    {value: '', label: 'Toutes les pages'},
    {value: 'prod', label: 'Saisie Production'},
    {value: 'recap', label: 'Récapitulatif'},
    {value: 'tracabilite', label: 'Traçabilité'},
    {value: 'profil', label: 'Profil Opérateur'}
  ],
  stock: [
    {value: '', label: 'Toutes les pages'},
    {value: 'inventaire', label: 'Inventaire'},
    {value: 'alertes', label: 'Alertes de stock'},
    {value: 'reappro', label: 'Réapprovisionnement'},
    {value: 'mouvements', label: 'Mouvements'},
    {value: 'historique', label: 'Historique'},
    {value: 'parametres', label: 'Paramètres'}
  ],
  myexpe: [
    {value: '', label: 'Toutes les pages'},
    {value: 'suivi_departs', label: 'Suivi départs — départs du jour'},
    {value: 'historique_departs', label: 'Suivi départs — historique'},
    {value: 'comparateur', label: 'Comparateur tarifs'},
    {value: 'transporteurs', label: 'Transporteurs'},
    {value: 'poids', label: 'Poids envoi'}
  ],
  planning_rh: [
    {value: '', label: 'Toutes les pages'},
    {value: 'planning', label: 'Planning personnel'},
    {value: 'conges', label: 'Gestion des congés'},
    {value: 'soldes', label: 'Soldes congés'}
  ],
  paie: [
    {value: '', label: 'Toutes les pages'},
    {value: 'bulletins', label: 'Bulletins de paie'},
    {value: 'employes', label: 'Employés'},
    {value: 'parametres', label: 'Paramètres'}
  ],
  global: [
    {value: '', label: 'Toutes les pages'}
  ]
};

function populatePageSelect(appSelectId, pageSelectId, selectedPage) {
  const app = document.getElementById(appSelectId).value;
  const pageSelect = document.getElementById(pageSelectId);
  const pages = APP_PAGES[app] || [{value: '', label: 'Toutes les pages'}];
  pageSelect.innerHTML = pages.map(p => 
    `<option value="${p.value}"${p.value === (selectedPage || '') ? ' selected' : ''}>${p.label}</option>`
  ).join('');
}

function onAppChange() {
  populatePageSelect('nm-app', 'nm-page', '');
}

function onEditAppChange() {
  populatePageSelect('edit-nm-app', 'edit-nm-page', '');
}

function getScopeFromAppPage(appId, pageId) {
  const app = document.getElementById(appId).value;
  const page = document.getElementById(pageId).value;
  if (app === 'global') return 'global';
  if (!page) return app;
  return app + '_' + page;
}

function setAppPageFromScope(scope) {
  if (!scope || scope === 'global') {
    return { app: 'global', page: '' };
  }
  const parts = scope.split('_');
  const knownApps = Object.keys(APP_PAGES);
  // Check if first part is an app
  if (knownApps.includes(parts[0])) {
    const app = parts[0];
    const page = parts.slice(1).join('_');
    // Check if page exists for this app
    const pages = APP_PAGES[app] || [];
    const pageExists = pages.some(p => p.value === page);
    return { app: app, page: pageExists ? page : '' };
  }
  // Legacy scope (just app name)
  if (knownApps.includes(scope)) {
    return { app: scope, page: '' };
  }
  return { app: 'global', page: '' };
}

async function toggleActive(id, current) {
  try {
    await api('/api/updates/' + id, { method: 'PATCH', body: JSON.stringify({ active: !current }), headers: { 'Content-Type': 'application/json' } });
    toast(current ? 'Annonce archivée' : 'Annonce réactivée');
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

function openNewUpdateModal() {
  const ov = document.getElementById('upd-modal-overlay');
  if (ov) { 
    ov.style.display = 'flex'; 
    ov.classList.remove('hidden'); 
  }
  // Initialize page select based on current app
  onAppChange();
}
function closeNewUpdateModal() {
  const ov = document.getElementById('upd-modal-overlay');
  if (ov) { ov.style.display = 'none'; ov.classList.add('hidden'); }
}
async function submitNewUpdate() {
  const scope   = getScopeFromAppPage('nm-app', 'nm-page');
  const titre   = (document.getElementById('nm-titre').value || '').trim();
  const message = (document.getElementById('nm-message').value || '').trim();
  const active  = Number(document.getElementById('nm-active').value);
  if (!titre || !message) { toast('Titre et message sont requis', true); return; }
  try {
    await api('/api/updates', { method: 'POST', body: JSON.stringify({ scope, titre, message, active }), headers: { 'Content-Type': 'application/json' } });
    toast('Annonce créée ✅');
    closeNewUpdateModal();
    document.getElementById('nm-titre').value = '';
    document.getElementById('nm-message').value = '';
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

let _editingUpdateId = null;

function openEditUpdateModal(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  _editingUpdateId = id;
  const { app, page } = setAppPageFromScope(u.scope);
  document.getElementById('edit-nm-app').value = app;
  populatePageSelect('edit-nm-app', 'edit-nm-page', page);
  document.getElementById('edit-nm-titre').value = u.titre || '';
  document.getElementById('edit-nm-message').value = u.message || '';
  document.getElementById('edit-nm-active').value = u.active ? '1' : '0';
  const ov = document.getElementById('edit-upd-modal-overlay');
  if (ov) { ov.style.display = 'flex'; ov.classList.remove('hidden'); }
}

function closeEditUpdateModal() {
  const ov = document.getElementById('edit-upd-modal-overlay');
  if (ov) { ov.style.display = 'none'; ov.classList.add('hidden'); }
  _editingUpdateId = null;
}

async function submitEditUpdate() {
  if (!_editingUpdateId) return;
  const scope   = getScopeFromAppPage('edit-nm-app', 'edit-nm-page');
  const titre   = (document.getElementById('edit-nm-titre').value || '').trim();
  const message = (document.getElementById('edit-nm-message').value || '').trim();
  const active  = Number(document.getElementById('edit-nm-active').value);
  if (!titre || !message) { toast('Titre et message sont requis', true); return; }
  try {
    await api('/api/updates/' + _editingUpdateId, { method: 'PATCH', body: JSON.stringify({ scope, titre, message, active }), headers: { 'Content-Type': 'application/json' } });
    toast('Annonce modifiée ✅');
    closeEditUpdateModal();
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}


let _opItems = [];
let _opCategories = [];
let _opEditCode = null;

async function loadOperationCodes() {
  const el = document.getElementById('op-list');
  if (!el) return;
  try {
    const d = await api('/api/settings/operation-codes');
    _opItems = (d && d.items) ? d.items : [];
    _opCategories = (d && d.categories) ? d.categories : [];
    const sel = document.getElementById('op-category');
    if (sel) {
      sel.innerHTML = _opCategories.map(c => `<option value="${c}">${c}</option>`).join('');
    }
    renderOpList();
  } catch (e) {
    el.innerHTML = `<p style="color:var(--danger)">${esc(e.message)}</p>`;
  }
}

function renderOpList() {
  const el = document.getElementById('op-list');
  if (!el) return;
  const q = (document.getElementById('op-filter')?.value || '').trim().toLowerCase();
  let items = [..._opItems];
  if (q) {
    items = items.filter(o =>
      String(o.code).includes(q) ||
      (o.label || '').toLowerCase().includes(q) ||
      (o.category || '').toLowerCase().includes(q) ||
      (o.severity || '').toLowerCase().includes(q)
    );
  }
  const byCat = {};
  items.forEach(o => {
    const c = o.category || 'autre';
    if (!byCat[c]) byCat[c] = [];
    byCat[c].push(o);
  });
  const cats = Object.keys(byCat).sort((a, b) => a.localeCompare(b, 'fr'));
  if (!cats.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucun code' + (q ? ' pour ce filtre' : '') + '.</p>';
    return;
  }
  let body = '';
  cats.forEach(cat => {
    body += '<tr class="op-cat-row"><td colspan="6">' + esc(cat) + '</td></tr>';
    byCat[cat].forEach(o => {
      const c = esc(o.code);
      const sev = esc(o.severity || 'info');
      const reqCls = o.required ? 'op-req yes' : 'op-req';
      body += '<tr>'
        + '<td class="op-code-cell">' + c + '</td>'
        + '<td class="op-lbl-cell">' + esc(o.label) + '</td>'
        + '<td><span class="op-pill ' + sev + '">' + sev + '</span></td>'
        + '<td><span class="op-pill ' + esc(cat) + '">' + esc(cat) + '</span></td>'
        + '<td><span class="' + reqCls + '">' + (o.required ? 'Oui' : '—') + '</span></td>'
        + '<td><div class="op-act">'
        + '<button type="button" class="btn-sm btn-ghost" data-op-edit="' + c + '">Modifier</button>'
        + '<button type="button" class="btn-sm btn-ghost danger" data-op-del="' + c + '">Supprimer</button>'
        + '</div></td></tr>';
    });
  });
  el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
    + '<th>Code</th><th>Libellé</th><th>Sévérité</th><th>Catégorie</th><th>Obligatoire</th><th>Actions</th>'
    + '</tr></thead><tbody>' + body + '</tbody></table></div>';
  el.querySelectorAll('[data-op-edit]').forEach(btn => {
    btn.addEventListener('click', () => openOpForm(btn.getAttribute('data-op-edit')));
  });
  el.querySelectorAll('[data-op-del]').forEach(btn => {
    btn.addEventListener('click', () => deleteOpCode(btn.getAttribute('data-op-del')));
  });
}

function openOpForm(code) {
  _opEditCode = code || null;
  const wrap = document.getElementById('op-form-wrap');
  const title = document.getElementById('op-form-title');
  const codeInp = document.getElementById('op-code');
  if (!wrap) return;
  wrap.classList.remove('hidden');
  if (code) {
    const o = _opItems.find(x => String(x.code) === String(code));
    if (!o) return;
    title.textContent = 'Modifier le code ' + code;
    codeInp.value = o.code;
    codeInp.disabled = true;
    document.getElementById('op-label').value = o.label || '';
    document.getElementById('op-severity').value = o.severity || 'info';
    document.getElementById('op-category').value = o.category || 'autre';
    document.getElementById('op-required').checked = !!o.required;
  } else {
    title.textContent = 'Nouveau code';
    codeInp.value = '';
    codeInp.disabled = false;
    document.getElementById('op-label').value = '';
    document.getElementById('op-severity').value = 'info';
    document.getElementById('op-category').value = _opCategories[0] || 'autre';
    document.getElementById('op-required').checked = false;
  }
}

function closeOpForm() {
  _opEditCode = null;
  const wrap = document.getElementById('op-form-wrap');
  if (wrap) wrap.classList.add('hidden');
}

async function saveOpForm() {
  const body = {
    code: document.getElementById('op-code').value.trim(),
    label: document.getElementById('op-label').value.trim(),
    severity: document.getElementById('op-severity').value,
    category: document.getElementById('op-category').value,
    required: document.getElementById('op-required').checked,
  };
  try {
    if (_opEditCode) {
      await api('/api/settings/operation-codes/' + encodeURIComponent(_opEditCode), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      toast('Code mis à jour');
    } else {
      await api('/api/settings/operation-codes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      toast('Code ajouté');
    }
    closeOpForm();
    await loadOperationCodes();
  } catch (e) { toast(e.message, true); }
}

async function deleteOpCode(code) {
  if (!confirm('Supprimer le code ' + code + ' ?')) return;
  try {
    await api('/api/settings/operation-codes/' + encodeURIComponent(code), { method: 'DELETE' });
    toast('Code supprimé');
    await loadOperationCodes();
  } catch (e) { toast(e.message, true); }
}

async function importOpsJson() {
  if (!confirm('Importer / mettre à jour tous les codes depuis operations.json sur le serveur ?')) return;
  try {
    const r = await api('/api/settings/operation-codes/import-json', { method: 'POST' });
    toast('Sync. OK (' + (r.upserted || 0) + ' codes)');
    await loadOperationCodes();
  } catch (e) { toast(e.message, true); }
}

async function deleteUpdate(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  if (u.nb_ack > 0) { toast('Impossible de supprimer une annonce déjà lue', true); return; }
  if (!confirm('Supprimer définitivement cette annonce ?')) return;
  try {
    await api('/api/updates/' + id, { method: 'DELETE' });
    toast('Annonce supprimée ✅');
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

// ── Audit log ─────────────────────────────────────────────
let _auditOffset = 0;
const _auditLimit = 50;
let _auditSearchTimer = null;

function debouncedAuditSearch() {
  clearTimeout(_auditSearchTimer);
  _auditSearchTimer = setTimeout(() => { _auditOffset = 0; loadAuditLogs(); }, 300);
}

const ACTION_COLORS = {
  CREATE:   'var(--ok)',
  UPDATE:   'var(--accent)',
  DELETE:   'var(--danger)',
  CLOSE:    'var(--muted)',
  VALIDATE: 'var(--warn)',
  REORDER:  'var(--text2)',
  SEARCH:   'var(--accent)',
  LOGIN:    'var(--text2)',
  LOGOUT:   'var(--muted)',
};
const ACTION_LABELS = {
  CREATE:'Création', UPDATE:'Modification', DELETE:'Suppression',
  CLOSE:'Clôture', VALIDATE:'Validation', REORDER:'Réorganisation',
  SEARCH:'Recherche', LOGIN:'Connexion', LOGOUT:'Déconnexion',
};
const MODULE_LABELS = {
  planning:'Planning', fabrication:'Fabrication', stock:'Stock',
  expe:'Expéditions', rh:'RH', settings:'Paramètres', auth:'Auth',
  portal:'Portail',
};

async function loadAuditLogs() {
  const wrap = document.getElementById('audit-table-wrap');
  const pag  = document.getElementById('audit-pagination');
  const search = (document.getElementById('audit-search')?.value || '').trim();
  const module = document.getElementById('audit-filter-module')?.value || '';
  const action = document.getElementById('audit-filter-action')?.value || '';

  wrap.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px 0">Chargement…</div>';

  const params = new URLSearchParams({
    limit: _auditLimit,
    offset: _auditOffset,
    ...(module && { module }),
    ...(action && { action }),
    ...(search && { search }),
  });

  const res = await fetch('/api/settings/audit?' + params, { credentials: 'include' });
  if (!res.ok) { wrap.innerHTML = '<div style="color:var(--danger);font-size:13px">Erreur de chargement.</div>'; return; }
  const { total, logs } = await res.json();

  if (!logs.length) {
    wrap.innerHTML = '<div style="color:var(--muted);font-size:13px;padding:20px 0">Aucune action enregistrée.</div>';
    pag.innerHTML = '';
    return;
  }

  const rows = logs.map(l => {
    const color = ACTION_COLORS[l.action] || 'var(--text2)';
    const actionLabel = ACTION_LABELS[l.action] || l.action;
    const moduleLabel = MODULE_LABELS[l.module] || l.module;
    const dt = l.created_at_display != null && l.created_at_display !== ''
      ? l.created_at_display
      : (l.created_at ? l.created_at.replace('T', ' ').slice(0, 16) : '—');
    const detailHtml = l.detail
      ? `<span style="color:var(--muted);font-size:11px;display:block;margin-top:2px;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px"
               title="${escAttr(l.detail)}">${esc(l.detail)}</span>` : '';
    return `<tr>
      <td style="white-space:nowrap;font-family:monospace;font-size:11px;color:var(--muted)">${dt}</td>
      <td style="font-size:13px;font-weight:600;color:var(--text)">${esc(l.user_nom||'—')}</td>
      <td><span style="font-size:10px;font-weight:700;color:var(--bg);background:${color};
                       padding:2px 7px;border-radius:20px;text-transform:uppercase">${actionLabel}</span></td>
      <td><span style="font-size:11px;color:var(--text2);background:var(--accent-bg);
                       padding:2px 6px;border-radius:6px">${moduleLabel}</span></td>
      <td style="font-size:13px;color:var(--text);max-width:280px">
        ${esc(l.objet||'—')}${detailHtml}
      </td>
    </tr>`;
  }).join('');

  wrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="border-bottom:2px solid var(--border)">
          <th style="text-align:left;padding:8px 12px 8px 0;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap">Date</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Utilisateur</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Action</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Module</th>
          <th style="text-align:left;padding:8px 12px;font-size:11px;font-weight:700;
                     color:var(--muted);text-transform:uppercase;letter-spacing:.5px">Objet</th>
        </tr>
      </thead>
      <tbody>
        ${rows.replace(/<tr>/g, '<tr style="border-bottom:1px solid var(--border)">')}
      </tbody>
    </table>`;

  const from = _auditOffset + 1;
  const to   = Math.min(_auditOffset + logs.length, total);
  pag.innerHTML = `
    <span>${from}–${to} sur ${total} actions</span>
    <div style="display:flex;gap:6px">
      <button type="button" onclick="_auditOffset=Math.max(0,_auditOffset-_auditLimit);loadAuditLogs()"
              ${_auditOffset === 0 ? 'disabled' : ''}
              style="background:var(--card);border:1px solid var(--border);border-radius:6px;
                     padding:4px 10px;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px">
        ← Précédent
      </button>
      <button type="button" onclick="_auditOffset=Math.min(total-_auditLimit,_auditOffset+_auditLimit);loadAuditLogs()"
              ${to >= total ? 'disabled' : ''}
              style="background:var(--card);border:1px solid var(--border);border-radius:6px;
                     padding:4px 10px;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px">
        Suivant →
      </button>
    </div>`;
}

// ── Registre FSC ─────────────────────────────────────────────
const FSC_CLAIM_LABELS = {
  non_fsc: 'Non FSC',
  fsc_100: 'FSC 100%',
  fsc_mix_credit: 'FSC Mix Credit',
  fsc_mix: 'FSC Mix',
  fsc_recycled: 'FSC Recycled',
};
const FSC_STATUT_LABELS = {
  attente: 'En attente',
  en_cours: 'En cours',
  termine: 'Terminé',
};
let _fscDatesInit = false;

function initFscDates() {
  const duEl = document.getElementById('fsc-du');
  const auEl = document.getElementById('fsc-au');
  if (!duEl || !auEl) return;
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  if (!duEl.value) duEl.value = `${y}-01-01`;
  if (!auEl.value) auEl.value = `${y}-${m}-${d}`;
}

function initFscPanel() {
  initFscDates();
  if (!_fscDatesInit) {
    _fscDatesInit = true;
  }
  loadFscStats();
  loadFscRegistre();
}

function fscClaimBadgeHtml(claim) {
  const c = (claim || 'non_fsc').trim();
  const label = FSC_CLAIM_LABELS[c] || esc(c);
  let bg = 'rgba(148,163,184,.12)';
  let color = 'var(--muted)';
  if (c === 'fsc_100') {
    bg = 'rgba(52,211,153,.12)';
    color = 'var(--ok)';
  } else if (c === 'fsc_recycled' || c.startsWith('fsc_mix')) {
    bg = 'rgba(34,211,238,.12)';
    color = 'var(--accent)';
  }
  return `<span class="fsc-claim-badge" style="background:${bg};color:${color}">${esc(label)}</span>`;
}

async function loadFscStats() {
  const grid = document.getElementById('fsc-kpi-grid');
  if (!grid) return;
  try {
    const d = await api('/api/fsc/stats');
    if (!d) return;
    const alertBadge = (d.alertes_ecart_total || 0) > 0 ? 'danger' : 'muted';
    grid.innerHTML = `
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Réceptions FSC ce mois</div>
        <div class="fsc-kpi-val">${esc(String(d.recep_fsc_ce_mois ?? 0))}</div>
        <span class="fsc-kpi-badge accent">Mois en cours</span>
      </div>
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Dossiers FSC actifs</div>
        <div class="fsc-kpi-val">${esc(String(d.dossiers_fsc_actifs ?? 0))}</div>
        <span class="fsc-kpi-badge accent">Non terminés</span>
      </div>
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Dossiers FSC terminés</div>
        <div class="fsc-kpi-val">${esc(String(d.dossiers_termines_fsc ?? 0))}</div>
        <span class="fsc-kpi-badge ok">Historique</span>
      </div>
      <div class="fsc-kpi-card">
        <div class="fsc-kpi-label">Alertes écart total</div>
        <div class="fsc-kpi-val">${esc(String(d.alertes_ecart_total ?? 0))}</div>
        <span class="fsc-kpi-badge ${alertBadge}">Confirmées</span>
      </div>`;
  } catch (e) {
    grid.innerHTML = `<p style="color:var(--danger);font-size:13px">${esc(e.message || 'Erreur chargement KPIs')}</p>`;
  }
}

function renderFscReceptions(rows) {
  const wrap = document.getElementById('fsc-recep-wrap');
  if (!wrap) return;
  if (!rows.length) {
    wrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Aucune réception FSC sur la période.</p>';
    return;
  }
  const trs = rows.map(r => {
    const dt = (r.created_at || '').replace('T', ' ').slice(0, 10);
    return `<tr>
      <td style="font-family:monospace;font-size:11px;color:var(--muted)">${esc(dt)}</td>
      <td>${esc(r.fournisseur || '—')}</td>
      <td style="font-family:monospace;font-size:11px">${esc(r.fournisseur_licence || '—')}</td>
      <td>${esc(r.certificat_fsc || '—')}</td>
      <td>${fscClaimBadgeHtml(r.fsc_type_claim)}</td>
      <td style="text-align:center">${esc(String(r.nb_bobines ?? 0))}</td>
      <td>${esc(r.created_by_name || '—')}</td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `<table>
    <thead><tr>
      <th>Date</th><th>Fournisseur</th><th>Licence FSC</th><th>Certificat</th>
      <th>Type claim</th><th>Nb bobines</th><th>Réceptionné par</th>
    </tr></thead>
    <tbody>${trs}</tbody>
  </table>`;
}

function renderFscDossiers(rows) {
  const wrap = document.getElementById('fsc-dossiers-wrap');
  if (!wrap) return;
  if (!rows.length) {
    wrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Aucun dossier FSC sur la période.</p>';
    return;
  }
  const trs = rows.map(d => {
    const alertes = Number(d.nb_alertes) || 0;
    const rowCls = alertes > 0 ? ' class="fsc-row-alert"' : '';
    const statut = FSC_STATUT_LABELS[d.statut] || d.statut || '—';
    return `<tr${rowCls}>
      <td style="font-weight:700;color:var(--accent)">${esc(d.reference || '—')}</td>
      <td>${esc(d.client || '—')}</td>
      <td>${fscClaimBadgeHtml(d.fsc_type_requis)}</td>
      <td>${esc(statut)}</td>
      <td style="font-family:monospace;font-size:11px">${esc(d.date_livraison || '—')}</td>
      <td style="text-align:center">${esc(String(d.nb_bobines_scannees ?? 0))}</td>
      <td style="text-align:center;font-weight:700;color:${alertes > 0 ? 'var(--danger)' : 'var(--muted)'}">${esc(String(alertes))}</td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `<table>
    <thead><tr>
      <th>Référence</th><th>Client</th><th>Type FSC requis</th><th>Statut</th>
      <th>Date livraison</th><th>Bobines scannées</th><th>Alertes</th>
    </tr></thead>
    <tbody>${trs}</tbody>
  </table>`;
}

async function loadFscRegistre() {
  const du = document.getElementById('fsc-du')?.value || '';
  const au = document.getElementById('fsc-au')?.value || '';
  const recepWrap = document.getElementById('fsc-recep-wrap');
  const dossWrap = document.getElementById('fsc-dossiers-wrap');
  if (recepWrap) recepWrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>';
  if (dossWrap) dossWrap.innerHTML = '<p style="color:var(--muted);font-size:13px;padding:12px 0">Chargement…</p>';
  try {
    const params = new URLSearchParams();
    if (du) params.set('du', du);
    if (au) params.set('au', au);
    const d = await api('/api/fsc/registre?' + params.toString());
    if (!d) return;
    renderFscReceptions(d.receptions || []);
    renderFscDossiers(d.dossiers || []);
  } catch (e) {
    const msg = `<p style="color:var(--danger);font-size:13px;padding:12px 0">${esc(e.message || 'Erreur chargement')}</p>`;
    if (recepWrap) recepWrap.innerHTML = msg;
    if (dossWrap) dossWrap.innerHTML = msg;
  }
}

function exportFscCsv() {
  const du = document.getElementById('fsc-du')?.value || '';
  const au = document.getElementById('fsc-au')?.value || '';
  const params = new URLSearchParams({ format: 'csv' });
  if (du) params.set('du', du);
  if (au) params.set('au', au);
  window.location.href = '/api/fsc/registre?' + params.toString();
}
</script>
</body>
</html>
"""
