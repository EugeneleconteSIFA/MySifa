"""MySifa — Mon profil (application standalone)

Accès : /profil
Tout utilisateur authentifié, indépendamment de MyProd ou des autres apps.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/profil", response_class=HTMLResponse)
def profil_page(request: Request):
    try:
        _ = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/profil", status_code=302)
        raise
    return HTMLResponse(content=PROFIL_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


PROFIL_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Mon profil — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
/* ── Variables MySifa (dark défaut) ── */
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;
  --accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--muted:#64748b;
  --accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
/* ── Reset & base ── */
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;}

/* ── Layout ── */
.layout{display:flex;min-height:100vh}

/* ── Sidebar ── */
.sidebar{
  width:220px;background:var(--card);border-right:1px solid var(--border);
  padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;
  height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none;
}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:28px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{
  display:flex;align-items:center;gap:10px;width:100%;text-align:left;
  padding:10px 12px;border-radius:8px;border:none;background:transparent;
  color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;
  font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px;
}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(34,211,238,.25),0 0 18px rgba(34,211,238,.15)}
body.palette-ambre .nav-btn:hover:not(.active),body.palette-forge .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 16px rgba(240,165,0,.14)}
body.palette-pivoine .nav-btn:hover:not(.active),body.palette-cocon .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,56,136,.28),0 0 16px rgba(240,56,136,.14)}
body.palette-foret .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(61,214,126,.28),0 0 16px rgba(61,214,126,.14)}
body.palette-cendre .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(100,150,200,.28),0 0 16px rgba(100,150,200,.14)}
body.palette-braise .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,112,48,.28),0 0 16px rgba(240,112,48,.14)}
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
.back-mysifa{
  border:none!important;background:transparent!important;
  font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important;
}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{
  display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;font-size:12px;width:100%;font-family:inherit;
  transition:background .15s,color .15s,border-color .15s,box-shadow .2s;
}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);
  box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 20px rgba(34,211,238,.14)}
body.palette-ambre .theme-btn:hover,body.palette-forge .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 18px rgba(240,165,0,.14)}
body.palette-pivoine .theme-btn:hover,body.palette-cocon .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,56,136,.24),0 0 18px rgba(240,56,136,.12)}
body.palette-foret .theme-btn:hover{box-shadow:0 0 0 1px rgba(61,214,126,.24),0 0 18px rgba(61,214,126,.12)}
body.palette-cendre .theme-btn:hover{box-shadow:0 0 0 1px rgba(100,150,200,.24),0 0 18px rgba(100,150,200,.12)}
body.palette-braise .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,112,48,.24),0 0 18px rgba(240,112,48,.12)}
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{display:inline-flex;align-items:center;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode:standalone),(max-width:900px){
  .theme-btn .theme-label{display:none}.theme-btn{justify-content:center}
}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);
  box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}

/* ── Main ── */
.main{flex:1;padding:28px;overflow:auto}
.container{max-width:680px;margin:0 auto}
h1{font-size:22px;font-weight:700;margin:0 0 4px}
.subtitle{font-size:13px;color:var(--muted);margin-bottom:22px}

/* ── Mobile topbar ── */
.mobile-topbar{display:none;align-items:center;gap:10px;margin-bottom:14px}
.mobile-menu-btn,.mobile-home-btn{
  display:none;align-items:center;justify-content:center;
  width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);
  color:var(--text2);cursor:pointer;font-family:inherit;flex-shrink:0;
}
.mobile-menu-btn:hover,.mobile-home-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.mobile-home-btn{margin-left:auto}
.mobile-topbar-title{font-size:14px;font-weight:800}
.mobile-topbar-sub{font-size:11px;color:var(--muted);margin-top:2px}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media (max-width:900px){
  .mobile-topbar{display:flex;position:fixed;top:0;left:0;right:0;z-index:120;
    background:var(--bg);padding:10px 18px;border-bottom:1px solid var(--border)}
  .mobile-menu-btn{display:inline-flex}
  .mobile-home-btn{display:inline-flex}
  body.has-topbar .main{padding-top:74px}
  .main{padding:18px}
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;
    transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
}

/* ── Tabs (nav dans sidebar) ── */
.pane-tab{display:none}
.pane-tab.active{display:block}

/* ── Formulaire profil ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 20px;margin-bottom:16px}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}
.card h2{font-size:15px;font-weight:700;margin:0}
.prof-ring{position:relative;flex-shrink:0;width:40px;height:40px}
.prof-ring svg{display:block;width:40px;height:40px}
.prof-ring-track{stroke:var(--border)}
.prof-ring-bar{stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .25s ease}
.prof-ring[data-tier="low"] .prof-ring-bar{stroke:var(--danger)}
.prof-ring[data-tier="mid"] .prof-ring-bar{stroke:var(--warn)}
.prof-ring[data-tier="high"] .prof-ring-bar{stroke:var(--ok)}
.prof-ring-label{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:800;color:var(--text);letter-spacing:-.02em;
}
.prof-modal-overlay{
  position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.55);
  display:flex;align-items:center;justify-content:center;padding:20px;
}
.prof-modal-card{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:26px 24px 20px;width:min(400px,100%);box-shadow:0 24px 64px rgba(0,0,0,.45);
  text-align:center;
}
.prof-modal-title{font-size:16px;font-weight:700;color:var(--text);margin-bottom:8px}
.prof-modal-text{font-size:13px;color:var(--text2);line-height:1.6;margin-bottom:18px}
.prof-modal-ok{
  width:100%;padding:12px;border-radius:10px;border:none;background:var(--accent);
  color:#0a0e17;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;
  transition:filter .15s;
}
.prof-modal-ok:hover{filter:brightness(1.06)}
.role-pill{display:inline-block;font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.5px;color:var(--accent);background:var(--accent-bg);
  padding:4px 10px;border-radius:999px;margin-bottom:14px}
.field{margin-bottom:12px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.field input{width:100%;padding:10px 13px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:14px;font-family:inherit;outline:none;
  transition:border-color .15s}
.field input:focus{border-color:var(--accent)}
.field input[type=date]{max-width:min(220px,100%);width:100%;box-sizing:border-box}
hr{border:none;border-top:1px solid var(--border);margin:16px 0}
.btn-save{background:var(--accent);color:#0a0e17;border:none;border-radius:10px;
  padding:11px 20px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit;
  margin-top:4px;transition:filter .15s}
.btn-save:hover{filter:brightness(1.06)}
.btn-save:disabled{opacity:.6;cursor:not-allowed}
.meta{font-size:11px;color:var(--muted);margin-top:14px;line-height:1.6}

/* ── Photo de profil ── */
.prof-avatar-wrap{display:flex;align-items:center;gap:16px;margin-bottom:18px;padding-bottom:18px;border-bottom:1px solid var(--border)}
.prof-avatar-box{position:relative;flex-shrink:0;width:80px;height:80px}
.prof-avatar,.prof-avatar-ph{
  width:80px;height:80px;border-radius:50%;border:2px solid var(--border);
  object-fit:cover;display:block;background:var(--bg);
}
.prof-avatar-ph{
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;color:var(--accent);background:var(--accent-bg);
}
.prof-avatar-actions{display:flex;flex-direction:column;gap:8px;flex:1;min-width:0}
.prof-avatar-hint{font-size:11px;color:var(--muted);line-height:1.5;margin:0}
.btn-avatar{
  align-self:flex-start;padding:8px 14px;border-radius:10px;border:1px solid var(--border);
  background:transparent;color:var(--text2);font-size:12px;font-weight:600;
  cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,background .15s;
}
.btn-avatar:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.btn-avatar-danger:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.1)}
/* ── Toast ── */
.toast{position:fixed;bottom:22px;right:22px;z-index:9999;padding:11px 16px;
  border-radius:10px;font-size:13px;font-weight:600;
  box-shadow:0 10px 36px rgba(0,0,0,.4);border:1px solid var(--border);
  animation:toast-in .2s ease}
.toast.ok{background:rgba(52,211,153,.15);color:var(--ok)}
.toast.err{background:rgba(248,113,113,.15);color:var(--danger)}
@keyframes toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.loading{color:var(--muted);font-size:14px;padding:40px 0;text-align:center}

/* ── Préférences : sélecteurs visuels ── */
.pref-section{margin-bottom:22px}
.pref-section-title{font-size:11px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.7px;margin-bottom:10px}
.theme-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;
  background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:10px}
@media (max-width:480px){.theme-grid{grid-template-columns:1fr 1fr}}
.theme-card{border:2px solid var(--border);border-radius:12px;padding:14px 10px;
  cursor:pointer;transition:border-color .15s,background .15s;
  background:transparent;text-align:center;position:relative}
.theme-card:hover:not(.selected){border-color:var(--accent);background:var(--accent-bg)}
.theme-card.selected{border-color:var(--accent);background:var(--card)}
.tc-check{position:absolute;top:7px;right:7px;width:16px;height:16px;border-radius:50%;
  background:var(--accent);display:none;align-items:center;justify-content:center}
.theme-card.selected .tc-check{display:flex}
.tc-preview{height:44px;border-radius:8px;margin-bottom:8px;
  display:flex;align-items:center;justify-content:center;gap:4px;overflow:hidden}
.tc-name{font-size:12px;font-weight:700;color:var(--text)}
.tc-sub{font-size:10px;color:var(--muted);margin-top:2px}
.mode-toggle{display:flex;gap:10px;
  background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:10px}
.mode-card{flex:1;border:2px solid var(--border);border-radius:12px;padding:14px 12px;
  cursor:pointer;transition:border-color .15s,background .15s;
  background:transparent;display:flex;align-items:center;gap:10px;justify-content:center}
.mode-card:hover:not(.selected){border-color:var(--accent);background:var(--accent-bg)}
.mode-card.selected{border-color:var(--accent);background:var(--card)}
.mode-ico{display:inline-flex;align-items:center}
.mode-label{font-size:13px;font-weight:700;color:var(--text)}
.mode-sub{font-size:10px;color:var(--muted)}
.btn-prefs-save{width:100%;background:var(--accent);color:#0a0e17;border:none;
  border-radius:10px;padding:12px;font-weight:700;font-size:14px;cursor:pointer;
  font-family:inherit;margin-top:4px;transition:filter .15s}
.btn-prefs-save:hover{filter:brightness(1.06)}
.pref-hint{font-size:11px;color:var(--muted);text-align:center;margin-top:10px;line-height:1.5}
.cal-color-list{display:flex;flex-direction:column;gap:8px;margin-bottom:4px}
.cal-color-row{
  display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;
  border:1px solid var(--border);background:var(--bg);transition:box-shadow .25s;
}
.cal-color-row.highlight{box-shadow:0 0 0 2px var(--accent);background:var(--accent-bg)}
.cal-color-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0;border:1px solid rgba(0,0,0,.15)}
.cal-color-label{flex:1;font-size:13px;font-weight:600;color:var(--text)}
.cal-color-row input[type=color]{
  width:40px;height:30px;padding:2px;border:1px solid var(--border);border-radius:8px;
  background:var(--card);cursor:pointer;flex-shrink:0;
}
.cal-color-reset{
  font-size:11px;font-weight:600;color:var(--muted);border:none;background:transparent;
  cursor:pointer;font-family:inherit;padding:4px 6px;border-radius:6px;flex-shrink:0;
}
.cal-color-reset:hover{color:var(--accent);background:var(--accent-bg)}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_calendar.js"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="closeSidebar()"></div>

<div class="layout">

  <!-- ── Sidebar ── -->
  <aside class="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Mon profil</div>
    </div>

    <button type="button" class="nav-btn active" id="nav-info" onclick="showTab('info')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      Mes informations
    </button>
    <button type="button" class="nav-btn" id="nav-prefs" onclick="showTab('prefs')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2"/></svg>
      Thème et apparence
    </button>
    <button type="button" class="nav-btn" id="nav-calendrier" onclick="showTab('calendrier')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Calendrier
    </button>

    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" onclick="location.href='/profil'" title="Mon profil">
        <div class="uc-name" id="uc-name">—</div>
        <div class="uc-role" id="uc-role">—</div>
      </div>
      <button type="button" class="theme-btn" id="btn-theme">
        <span class="theme-ico" id="theme-ico">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        </span>
        <span class="theme-label" id="theme-label">Mode clair</span>
      </button>
      <button type="button" class="logout-btn" id="btn-logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Mon profil · __V_LABEL__</div>
    </div>
  </aside>

  <!-- ── Main ── -->
  <main class="main">
    <div class="container">

      <!-- Topbar mobile -->
      <div class="mobile-topbar">
        <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div>
          <div class="mobile-topbar-title">Mon profil</div>
          <div class="mobile-topbar-sub" id="mobile-sub">Mes informations</div>
        </div>
        <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
        </button>
      </div>

      <h1>Mon profil</h1>
      <p class="subtitle" id="page-sub">Vos informations personnelles.</p>

      <!-- Onglet Mes informations -->
      <div class="pane-tab active" id="pane-info">
        <div class="loading">Chargement…</div>
      </div>

      <!-- Onglet Mes préférences -->
      <div class="pane-tab" id="pane-prefs"></div>
      <div class="pane-tab" id="pane-calendrier"></div>

    </div>
  </main>
</div>

<script src="/static/support_widget.js"></script>
<script>window.__MYSIFA_APP__='profil';</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/chat_widget.js"></script>
<script>
const ROLE_LABELS={
  direction:'Direction',administration:'Administration',fabrication:'Fabrication',
  logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',
  commercial:'Commercial',superadmin:'Super admin'
};

let ME=null;
let CURRENT_TAB='info';

function getPrefs(){ return window.MySifaTheme ? MySifaTheme.loadPrefs() : {palette:'mysifa',style:'defaut',mode:'dark'}; }
function setPrefs(partial){ return window.MySifaTheme ? MySifaTheme.setPrefs(partial) : null; }

// ── SVG helpers ───────────────────────────────────────────────────
const ICO_MOON=`<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
const ICO_SUN=`<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const ICO_CHECK=`<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#0a0e17" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

// ── Préférences (MySifaTheme partagé) ─────────────────────────────
function syncThemeBtn(){
  const isLight=getPrefs().mode==='light';
  const ico=document.getElementById('theme-ico');
  const lbl=document.getElementById('theme-label');
  if(ico)ico.innerHTML=isLight?ICO_SUN:ICO_MOON;
  if(lbl)lbl.textContent=isLight?'Mode sombre':'Mode clair';
}

// ── Sidebar mobile ────────────────────────────────────────────────
function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

// ── Toast ─────────────────────────────────────────────────────────
function toast(msg,ok){
  const t=document.createElement('div');
  t.className='toast '+(ok?'ok':'err');
  t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),3200);
}

// ── API ───────────────────────────────────────────────────────────
async function api(path,opts){
  const r=await fetch(path,{credentials:'include',...opts});
  if(r.status===401){location.href='/?next=/profil';throw new Error('auth');}
  if(!r.ok){
    let d='Erreur';
    try{const j=await r.json();d=(j&&j.detail)?(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail)):d;}catch(e){}
    throw new Error(d);
  }
  if(r.status===204)return null;
  const ct=r.headers.get('content-type')||'';
  if(ct.includes('application/json'))return r.json();
  return null;
}

function fD(iso){
  if(!iso)return '';
  try{return new Date(iso).toLocaleString('fr-FR',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});}catch(e){return iso;}
}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}

function avatarInitials(nom){
  const p=String(nom||'').trim().split(/\s+/).filter(Boolean);
  if(!p.length)return '?';
  if(p.length===1)return p[0].slice(0,2).toUpperCase();
  return (p[0][0]+p[p.length-1][0]).toUpperCase();
}
function avatarPreviewHtml(u,size){
  const sz=size||80;
  const url=(u&&u.avatar_url)?String(u.avatar_url).trim():'';
  if(url){
    return '<img class="prof-avatar" src="'+esc(url)+'" alt="" width="'+sz+'" height="'+sz+'">';
  }
  return '<div class="prof-avatar-ph" aria-hidden="true">'+esc(avatarInitials(u&&u.nom))+'</div>';
}
function avatarChipHtml(u){
  const url=(u&&u.avatar_url)?String(u.avatar_url).trim():'';
  if(url){
    return '<img class="uc-avatar" src="'+esc(url)+'" alt="">';
  }
  return '<div class="uc-avatar-ph" aria-hidden="true">'+esc(avatarInitials(u&&u.nom))+'</div>';
}
function refreshAvatarPreview(){
  const box=document.getElementById('prof-avatar-box');
  if(box)box.innerHTML=avatarPreviewHtml(ME,80);
  const del=document.getElementById('btn-avatar-del');
  if(del)del.style.display=(ME&&ME.avatar_url)?'':'none';
}

// ── Onglets ───────────────────────────────────────────────────────
function showTab(tab){
  CURRENT_TAB=tab;
  ['info','prefs','calendrier'].forEach(id=>{
    const pane=document.getElementById('pane-'+id);
    const nav=document.getElementById('nav-'+id);
    if(pane)pane.classList.toggle('active',id===tab);
    if(nav)nav.classList.toggle('active',id===tab);
  });
  const subLabels={
    info:'Informations personnelles',
    prefs:'Thème et apparence',
    calendrier:'Couleurs MyCalendrier'
  };
  const sub=document.getElementById('mobile-sub');
  if(sub)sub.textContent=subLabels[tab]||'';
  const pageSub=document.getElementById('page-sub');
  if(pageSub){
    if(tab==='info')pageSub.textContent='Vos informations personnelles et mot de passe.';
    else if(tab==='calendrier')pageSub.textContent='Couleurs des calendriers affichés dans MyCalendrier.';
    else pageSub.textContent='Personnalisez l\'apparence de MySifa.';
  }
  if(tab==='prefs')renderPrefs();
  if(tab==='calendrier')renderCalendrier();
  closeSidebar();
}

// ── Complétion profil ─────────────────────────────────────────────
const PROFILE_FIELDS=['nom','email','telephone','adresse','date_naissance'];
function profileFieldFilled(val){return String(val==null?'':val).trim().length>0;}
function profileCompletionPercent(u){
  if(!u||typeof u!=='object')return 0;
  let n=0;
  PROFILE_FIELDS.forEach(k=>{if(profileFieldFilled(u[k]))n+=1;});
  return Math.round((n/PROFILE_FIELDS.length)*100);
}
function profileRingTier(pct){
  if(pct>=80)return 'high';
  if(pct>=40)return 'mid';
  return 'low';
}
function profileRingHtml(pct){
  const p=Math.max(0,Math.min(100,Number(pct)||0));
  const r=14;const c=2*Math.PI*r;const off=c*(1-p/100);
  const tier=profileRingTier(p);
  return '<span class="prof-ring" data-tier="'+tier+'" title="Profil complété à '+p+' %">'+
    '<svg viewBox="0 0 34 34" aria-hidden="true">'+
    '<circle class="prof-ring-track" cx="17" cy="17" r="'+r+'" fill="none" stroke-width="3"/>'+
    '<circle class="prof-ring-bar" cx="17" cy="17" r="'+r+'" fill="none" stroke-width="3"'+
    ' stroke-dasharray="'+c.toFixed(2)+'" stroke-dashoffset="'+off.toFixed(2)+'"'+
    ' transform="rotate(-90 17 17)"/>'+
    '</svg>'+
    '<span class="prof-ring-label">'+p+'%</span>'+
    '</span>';
}
function profileCompleteStorageKey(){
  return 'mysifa.profil.complete100.'+(ME&&ME.id?ME.id:'');
}
function showProfileCompleteModal(){
  const old=document.getElementById('prof-complete-modal');
  if(old)old.remove();
  const overlay=document.createElement('div');
  overlay.id='prof-complete-modal';
  overlay.className='prof-modal-overlay';
  overlay.innerHTML=
    '<div class="prof-modal-card" role="dialog" aria-labelledby="prof-modal-title">'+
    '<div class="prof-modal-title" id="prof-modal-title">Profil complété</div>'+
    '<p class="prof-modal-text">Merci d\'avoir complété votre profil.</p>'+
    '<button type="button" class="prof-modal-ok">OK</button>'+
    '</div>';
  overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.remove();});
  overlay.querySelector('.prof-modal-ok').onclick=()=>overlay.remove();
  document.body.appendChild(overlay);
}
function maybeShowProfileCompleteModal(prevPct,newPct){
  const key=profileCompleteStorageKey();
  if(newPct<100){
    try{localStorage.removeItem(key);}catch(e){}
    return;
  }
  if(prevPct>=100)return;
  try{
    if(localStorage.getItem(key))return;
    localStorage.setItem(key,'1');
  }catch(e){}
  showProfileCompleteModal();
}
// ── Onglet Mes informations ───────────────────────────────────────
function fieldHtml(label,id,type,val){
  return `<div class="field"><label for="${id}">${label}</label><input id="${id}" type="${type||'text'}" value="${esc(val)}"></div>`;
}

function renderInfo(){
  const u=ME||{};
  const role=ROLE_LABELS[u.role]||u.role||'';
  const ring=profileRingHtml(profileCompletionPercent(u));
  const hasAvatar=!!(u.avatar_url&&String(u.avatar_url).trim());
  document.getElementById('pane-info').innerHTML=`
    <div class="card">
      <div class="role-pill">${esc(role)}</div>
      <div class="card-head">
        <h2>Informations personnelles</h2>
        ${ring}
      </div>
      <div class="prof-avatar-wrap">
        <div class="prof-avatar-box" id="prof-avatar-box">${avatarPreviewHtml(u,80)}</div>
        <div class="prof-avatar-actions">
          <p class="prof-avatar-hint">Photo de profil — jpg, png, webp ou gif, 4 Mo max.</p>
          <input type="file" id="prof-avatar-input" accept="image/jpeg,image/png,image/webp,image/gif" style="display:none">
          <button type="button" class="btn-avatar" id="btn-avatar-pick">Choisir une photo</button>
          <button type="button" class="btn-avatar btn-avatar-danger" id="btn-avatar-del" style="display:${hasAvatar?'':'none'}">Supprimer la photo</button>
        </div>
      </div>
      <form id="profil-form" onsubmit="return false;">
        ${fieldHtml('Nom complet','f-nom','text',u.nom)}
        ${fieldHtml('Email','f-email','email',u.email)}
        ${fieldHtml('Téléphone','f-tel','tel',u.telephone)}
        ${fieldHtml('Adresse','f-addr','text',u.adresse)}
        ${fieldHtml('Date de naissance','f-birth','date',u.date_naissance)}
        <hr>
        ${fieldHtml('Mot de passe actuel','f-cur-pwd','password','')}
        ${fieldHtml('Nouveau mot de passe','f-pwd','password','')}
        ${fieldHtml('Confirmer','f-pwd2','password','')}
        <button type="button" class="btn-save" id="btn-save">Enregistrer</button>
        <div class="meta">
          ${u.created_at?`<div>Créé le ${esc(fD(u.created_at))}</div>`:''}
          ${u.last_login?`<div>Dernière connexion : ${esc(fD(u.last_login))}</div>`:''}
        </div>
      </form>
    </div>`;
  document.getElementById('btn-save').onclick=saveInfo;
  document.getElementById('btn-avatar-pick').onclick=()=>document.getElementById('prof-avatar-input')?.click();
  document.getElementById('prof-avatar-input').onchange=uploadAvatar;
  document.getElementById('btn-avatar-del').onclick=deleteAvatar;
}

async function uploadAvatar(){
  const inp=document.getElementById('prof-avatar-input');
  const file=inp&&inp.files&&inp.files[0];
  if(inp)inp.value='';
  if(!file)return;
  const fd=new FormData();
  fd.append('photo',file);
  try{
    const r=await fetch('/api/auth/me/avatar',{method:'POST',credentials:'include',body:fd});
    if(r.status===401){location.href='/?next=/profil';return;}
    if(!r.ok){
      let msg='Enregistrement impossible';
      try{const j=await r.json();msg=(j&&j.detail)?(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail)):msg;}catch(e){}
      throw new Error(msg);
    }
    const j=await r.json();
    if(ME)ME.avatar_url=j.url||'';
    refreshAvatarPreview();
    updateUserChip();
    toast('Photo enregistrée',true);
  }catch(e){
    toast(e.message||'Enregistrement impossible',false);
  }
}

async function deleteAvatar(){
  if(!confirm('Supprimer la photo de profil ?'))return;
  try{
    const r=await fetch('/api/auth/me/avatar',{method:'DELETE',credentials:'include'});
    if(r.status===401){location.href='/?next=/profil';return;}
    if(!r.ok)throw new Error('Suppression impossible');
    if(ME)ME.avatar_url='';
    refreshAvatarPreview();
    updateUserChip();
    toast('Photo supprimée',true);
  }catch(e){
    toast(e.message||'Suppression impossible',false);
  }
}

async function saveInfo(){
  const btn=document.getElementById('btn-save');
  if(btn)btn.disabled=true;
  const prevPct=profileCompletionPercent(ME);
  const body={
    nom:(document.getElementById('f-nom')?.value||'').trim(),
    email:(document.getElementById('f-email')?.value||'').trim(),
    telephone:(document.getElementById('f-tel')?.value||'').trim(),
    adresse:(document.getElementById('f-addr')?.value||'').trim(),
    date_naissance:(document.getElementById('f-birth')?.value||'').trim(),
  };
  const pwd=(document.getElementById('f-pwd')?.value||'');
  const pwd2=(document.getElementById('f-pwd2')?.value||'');
  const cur=(document.getElementById('f-cur-pwd')?.value||'');
  if(pwd){body.password=pwd;body.password_confirm=pwd2;body.current_password=cur;}
  try{
    await api('/api/auth/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    ME=await api('/api/auth/me');
    const newPct=profileCompletionPercent(ME);
    const completedNow=prevPct<100&&newPct===100;
    if(!completedNow)toast('Profil mis à jour',true);
    renderInfo();
    updateUserChip();
    maybeShowProfileCompleteModal(prevPct,newPct);
  }catch(e){
    toast(e.message||'Enregistrement impossible',false);
  }finally{
    if(btn)btn.disabled=false;
  }
}

// ── Onglet Mes préférences ────────────────────────────────────────
const PALETTE_DEF=[
  {id:'mysifa', name:'Cyan',   sub:'défaut',
    prev:`<div style="background:#0a0e17;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
      <div style="width:9px;height:9px;border-radius:50%;background:#22d3ee"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#22d3ee;opacity:.5"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#22d3ee;opacity:.25"></div>
    </div>`},
  {id:'ambre',  name:'Ambre',   sub:'Doré · navy',
    prev:`<div style="background:#0c1422;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
      <div style="width:9px;height:9px;border-radius:50%;background:#F0A500"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#4A8FE8;opacity:.8"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#F0A500;opacity:.4"></div>
    </div>`},
  {id:'pivoine', name:'Pivoine', sub:'Rose vif · quasi-noir',
    prev:`<div style="background:#0e040c;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
      <div style="width:9px;height:9px;border-radius:50%;background:#f03888"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#7a9cc8;opacity:.85"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#b888a4;opacity:.55"></div>
    </div>`},
  {id:'foret',  name:'Forêt',   sub:'Vert vif · quasi-noir',
    prev:`<div style="background:#060d08;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
      <div style="width:9px;height:9px;border-radius:50%;background:#3dd67e"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#c8a86a;opacity:.85"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#8fa898;opacity:.6"></div>
    </div>`},
  {id:'cendre', name:'Cendre',  sub:'Bleu acier · nuit froide',
    prev:`<div style="background:#080a0f;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
      <div style="width:9px;height:9px;border-radius:50%;background:#6496c8"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#c8a070;opacity:.85"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#848ea8;opacity:.65"></div>
    </div>`},
  {id:'braise', name:'Braise',  sub:'Orange brûlé · quasi-noir',
    prev:`<div style="background:#0e0500;width:100%;height:100%;border-radius:6px;display:flex;align-items:center;justify-content:center;gap:5px">
      <div style="width:9px;height:9px;border-radius:50%;background:#f07030"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#6a90b0;opacity:.85"></div>
      <div style="width:9px;height:9px;border-radius:50%;background:#b8907a;opacity:.65"></div>
    </div>`},
];

const STYLE_DEF=[
  {id:'defaut', name:'Défaut',   sub:'Équilibré · tech',
    prev:`<div style="display:flex;gap:3px;width:100%">
      <div style="height:18px;flex:1;border-radius:6px;background:var(--border)"></div>
      <div style="height:18px;flex:1;border-radius:6px;background:var(--border)"></div>
      <div style="height:18px;flex:1;border-radius:6px;background:var(--border)"></div>
    </div>`},
  {id:'mini',   name:'Compact',  sub:'Serré · monospace',
    prev:`<div style="display:flex;gap:2px;width:100%;font-family:monospace">
      <div style="height:18px;flex:1;border-radius:2px;background:var(--border);display:flex;align-items:center;justify-content:center;font-size:7px;color:var(--muted)">_</div>
      <div style="height:18px;flex:1;border-radius:2px;background:var(--border)"></div>
      <div style="height:18px;flex:1;border-radius:2px;background:var(--border)"></div>
    </div>`},
  {id:'round',  name:'Aéré',     sub:'Doux · arrondi',
    prev:`<div style="display:flex;gap:3px;width:100%">
      <div style="height:18px;flex:1;border-radius:12px;background:var(--border)"></div>
      <div style="height:18px;flex:1;border-radius:12px;background:var(--border)"></div>
      <div style="height:18px;flex:1;border-radius:12px;background:var(--border)"></div>
    </div>`},
];

function palCard(p){
  const sel=getPrefs().palette===p.id?'selected':'';
  return `<div class="theme-card ${sel}" onclick="selectPalette('${p.id}')">
    <div class="tc-check">${ICO_CHECK}</div>
    <div class="tc-preview">${p.prev}</div>
    <div class="tc-name">${p.name}</div>
    <div class="tc-sub">${p.sub}</div>
  </div>`;
}

function styleCard(s){
  const sel=getPrefs().style===s.id?'selected':'';
  return `<div class="theme-card ${sel}" onclick="selectStyle('${s.id}')">
    <div class="tc-check">${ICO_CHECK}</div>
    <div class="tc-preview" style="background:var(--card);padding:6px;border-radius:6px">${s.prev}</div>
    <div class="tc-name">${s.name}</div>
    <div class="tc-sub">${s.sub}</div>
  </div>`;
}

function modeCard(id,icoSvg,label,sub){
  const sel=getPrefs().mode===id?'selected':'';
  return `<div class="mode-card ${sel}" onclick="selectMode('${id}')">
    <span class="mode-ico">${icoSvg}</span>
    <div>
      <div class="mode-label">${label}</div>
      <div class="mode-sub">${sub}</div>
    </div>
  </div>`;
}

function calColorRow(c){
  const col=(window.MySifaCalendar?MySifaCalendar.loadColorsMap():{})[c.id]||c.color;
  return `<div class="cal-color-row" id="cal-row-${esc(c.id)}">
    <span class="cal-color-dot" style="background:${esc(col)}"></span>
    <span class="cal-color-label">${esc(c.label)}</span>
    <input type="color" value="${esc(col)}" aria-label="Couleur ${esc(c.label)}"
      oninput="onCalColorInput('${esc(c.id)}',this.value)">
    <button type="button" class="cal-color-reset" onclick="resetCalColor('${esc(c.id)}')">Défaut</button>
  </div>`;
}

function onCalColorInput(calId,hex){
  if(!window.MySifaCalendar||!MySifaCalendar.validHex(hex))return;
  MySifaCalendar.setColor(calId,hex);
  const row=document.getElementById('cal-row-'+calId);
  const dot=row&&row.querySelector('.cal-color-dot');
  if(dot)dot.style.background=hex;
}

function resetCalColor(calId){
  if(!window.MySifaCalendar)return;
  MySifaCalendar.resetColor(calId);
  const row=document.getElementById('cal-row-'+calId);
  if(!row)return;
  const hex=MySifaCalendar.colorFor(calId);
  const dot=row.querySelector('.cal-color-dot');
  const inp=row.querySelector('input[type=color]');
  if(dot)dot.style.background=hex;
  if(inp)inp.value=hex;
}

function openCalColorFromHash(){
  const h=location.hash||'';
  if(!h.startsWith('#cal-'))return;
  const id=decodeURIComponent(h.slice(5));
  showTab('calendrier');
  requestAnimationFrame(()=>{
    const row=document.getElementById('cal-row-'+id);
    if(row){
      row.scrollIntoView({behavior:'smooth',block:'center'});
      row.classList.add('highlight');
      setTimeout(()=>row.classList.remove('highlight'),2500);
    }
  });
}

function themePrefsBody(){
  const prefs=getPrefs();
  const tp={palette:prefs.palette,style:prefs.style,mode:prefs.mode};
  if(window.MySifaTheme&&MySifaTheme.themePrefsPayload)return MySifaTheme.themePrefsPayload(prefs);
  if(window.MySifaCalendar)return MySifaCalendar.buildThemePrefsPayload(tp);
  return tp;
}

function renderCalendrier(){
  const calDefs=window.MySifaCalendar?MySifaCalendar.CAL_DEFS:[];
  document.getElementById('pane-calendrier').innerHTML=`
    <div class="card">
      <h2>Couleurs des calendriers</h2>
      <p class="pref-hint" style="text-align:left;margin:0 0 14px">Personnalisez la couleur de chaque calendrier dans MyCalendrier.</p>
      <div class="pref-section">
        <div class="cal-color-list">${calDefs.map(calColorRow).join('')}</div>
      </div>
      <button class="btn-prefs-save" onclick="saveCalColors()">Enregistrer</button>
    </div>`;
}

function renderPrefs(){
  document.getElementById('pane-prefs').innerHTML=`
    <div class="card">
      <h2>Palette de couleurs</h2>
      <div class="pref-section">
        <div class="theme-grid">${PALETTE_DEF.map(palCard).join('')}</div>
      </div>
      <h2 style="margin-top:20px">Style de l'interface</h2>
      <div class="pref-section">
        <div class="theme-grid">${STYLE_DEF.map(styleCard).join('')}</div>
      </div>
      <h2 style="margin-top:20px">Mode d'affichage</h2>
      <div class="pref-section">
        <div class="mode-toggle">
          ${modeCard('dark', ICO_MOON, 'Sombre', 'Fond foncé')}
          ${modeCard('light', ICO_SUN,  'Clair',  'Fond blanc')}
        </div>
      </div>
      <button class="btn-prefs-save" onclick="savePrefs()">Appliquer</button>
      <p class="pref-hint">Les préférences s'appliquent sur toutes les pages MySifa.</p>
    </div>`;
}

function selectPalette(id){setPrefs({palette:id});renderPrefs();syncThemeBtn();}
function selectStyle(id){setPrefs({style:id});renderPrefs();syncThemeBtn();}
function selectMode(id){setPrefs({mode:id});renderPrefs();syncThemeBtn();}

async function saveThemePrefs(){
  try{
    await api('/api/auth/me',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({theme_prefs:themePrefsBody()})
    });
    toast('Préférences enregistrées',true);
  }catch(e){
    toast('Préférences appliquées localement',true);
  }
}
async function saveCalColors(){
  try{
    await api('/api/auth/me',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({theme_prefs:themePrefsBody()})
    });
    toast('Couleurs enregistrées',true);
  }catch(e){
    toast('Couleurs appliquées localement',true);
  }
}
async function savePrefs(){return saveThemePrefs();}

// ── Sidebar bottom : user chip + theme toggle + logout ────────────
function updateUserChip(){
  if(!ME)return;
  const chip=document.querySelector('.user-chip');
  if(chip&&window.MySifaUserChip){
    MySifaUserChip.fill(chip,ME,{roleLabels:ROLE_LABELS,showProfil:false});
    return;
  }
  const n=document.getElementById('uc-name');
  const r=document.getElementById('uc-role');
  if(n)n.textContent=ME.nom||'—';
  if(r)r.textContent=ROLE_LABELS[ME.role]||ME.role||'—';
}

document.getElementById('btn-theme').onclick=()=>{
  if(window.MySifaTheme)MySifaTheme.toggleMode();
  syncThemeBtn();
  if(CURRENT_TAB==='prefs')renderPrefs();
  if(CURRENT_TAB==='calendrier')renderCalendrier();
};

document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

// ── Init ──────────────────────────────────────────────────────────
(async function init(){
  syncThemeBtn();

  try{
    ME=await api('/api/auth/me');
    if(ME&&window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    else if(ME&&window.MySifaCalendar)MySifaCalendar.mergeFromUser(ME);
    syncThemeBtn();
    updateUserChip();
    renderInfo();
    const tabParam=new URLSearchParams(location.search).get('tab');
    if(tabParam==='prefs')showTab('prefs');
    else if(tabParam==='calendrier')showTab('calendrier');
    if(location.hash.startsWith('#cal-'))openCalColorFromHash();
  }catch(e){
    if(e.message!=='auth'){
      document.getElementById('pane-info').innerHTML='<div class="card"><p style="color:var(--muted);font-size:13px">Impossible de charger le profil.</p></div>';
    }
  }
})();
</script>
</body>
</html>
"""
