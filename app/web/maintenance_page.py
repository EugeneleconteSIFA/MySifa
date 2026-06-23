"""MySifa — Page Maintenance
Route : /maintenance
Accès strict : superadmin + utilisateur d'identifiant `loic.gognau`
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user
from app.web.access_denied import access_denied_response
from config import APP_VERSION

MAINTENANCE_ALLOWED_IDENTS = {"loic.gognau"}


def _has_maintenance_access(user: dict) -> bool:
    if not user:
        return False
    if user.get("role") == "superadmin":
        return True
    ident = str(user.get("identifiant") or "").strip().lower()
    return ident in MAINTENANCE_ALLOWED_IDENTS


router = APIRouter()


@router.get("/maintenance", response_class=HTMLResponse)
def maintenance_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/maintenance", status_code=302)
        raise
    if not _has_maintenance_access(user):
        return access_denied_response("Maintenance")
    html = MAINTENANCE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


MAINTENANCE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Maintenance — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.10);
  --accent-fg:#0a0e17;
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;--success:#34d399;
  --sidebar-w:220px;
}
html.light-pre body,body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.08);
  --accent-fg:#ffffff;
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

.app{display:flex;height:100vh;overflow:hidden}
.sidebar{width:var(--sidebar-w);background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}.sidebar{scrollbar-width:none}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:768px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:9000;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .sidebar-overlay{z-index:8999}
  .main{height:100vh;overflow-y:auto}
}
.main{flex:1;overflow-y:auto;display:flex;flex-direction:column}

.logo{padding:0 8px;margin-bottom:28px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn--mysifa-portal{align-items:baseline;flex-wrap:wrap;gap:4px 8px;line-height:1.35}
.nav-btn--mysifa-portal:hover{background:var(--accent-bg)}
.mysifa-back-preamble{font-size:13px;font-weight:500;color:var(--text2)}
.mysifa-back-brand{font-size:14px;font-weight:800;letter-spacing:-.5px;color:var(--text);white-space:nowrap}
.mysifa-back-accent{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;border:1px solid var(--border);cursor:pointer;transition:.15s;background:transparent}
.user-chip:hover{border-color:var(--accent)}
.uc-name{font-size:13px;font-weight:600;color:var(--text)}
.uc-role{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit;transition:.15s;width:100%}
.theme-btn:hover{border-color:var(--accent);color:var(--accent)}
.logout-btn{color:var(--muted)}
.logout-btn:hover{border-color:var(--danger);color:var(--danger)}
.version{font-size:10px;color:var(--muted);padding:4px 12px;font-family:ui-monospace,monospace;opacity:.6}

.mobile-topbar{display:none;align-items:center;gap:12px;padding:14px 16px;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
@media(max-width:768px){.mobile-topbar{display:flex}}
.mobile-menu-btn{background:none;border:none;color:var(--text2);cursor:pointer;padding:4px;border-radius:6px;display:flex;align-items:center;justify-content:center}
.mobile-topbar-title{font-size:14px;font-weight:700;color:var(--text)}
.mobile-topbar-sub{font-size:11px;color:var(--muted)}
.mobile-home-btn{margin-left:auto;background:none;border:none;color:var(--muted);cursor:pointer;font-size:20px;padding:4px;border-radius:6px;transition:.15s}
.mobile-home-btn:hover{color:var(--accent)}

.content{padding:28px 32px;max-width:1280px;width:100%;flex:1;display:flex;flex-direction:column}
@media(max-width:768px){.content{padding:16px}}
.page-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:28px;flex-wrap:wrap}
.page-title{font-size:22px;font-weight:800;letter-spacing:-.5px}
.page-title span{color:var(--accent)}
.page-subtitle{font-size:13px;color:var(--muted);margin-top:3px}

.wip-wrap{flex:1;display:flex;align-items:center;justify-content:center;padding:40px 20px}
.wip-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:48px 44px;max-width:520px;width:100%;text-align:center;box-shadow:0 12px 40px rgba(0,0,0,.18)}
.wip-icon{display:inline-flex;align-items:center;justify-content:center;width:64px;height:64px;border-radius:50%;background:var(--accent-bg);color:var(--accent);margin-bottom:22px}
.wip-title{font-size:18px;font-weight:800;color:var(--text);margin-bottom:10px;letter-spacing:-.3px}
.wip-sub{font-size:13px;color:var(--text2);line-height:1.65;margin-bottom:6px}
.wip-meta{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-top:18px}

.page-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:10px;padding:10px 16px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;transition:filter .15s,border-color .15s}
.btn:hover{filter:brightness(1.05);border-color:var(--accent)}
.btn[disabled]{cursor:not-allowed;opacity:.7;color:var(--text2)}
.btn[disabled]:hover{filter:none;border-color:var(--border)}
.btn .btn-ico{display:inline-flex;align-items:center;color:var(--accent)}
.badge-dev{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;background:var(--accent-bg);color:var(--accent);font-size:10px;font-weight:700;letter-spacing:.4px;text-transform:uppercase}

.view{display:flex;flex-direction:column;flex:1}

/* Filtres en bandeau — style aligné sur MyProd / Production */
.filters-panel{margin-bottom:18px}
.filters{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
.filter-group{display:flex;flex-direction:column;gap:6px;min-width:0}
.filter-group label{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.filter-input{background:var(--bg);border:1.5px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;outline:none;min-height:40px;box-sizing:border-box;transition:border-color .15s,box-shadow .15s;min-width:168px}
.filter-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.filters .filter-input[type=date]{min-width:148px;padding:9px 12px;font-size:12px}
select.filter-input{appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px;cursor:pointer}
.filters-apply-btn{background:var(--accent);color:var(--accent-fg,var(--bg));border:none;border-radius:10px;padding:10px 22px;font-size:13px;font-weight:700;min-height:40px;cursor:pointer;font-family:inherit;align-self:flex-end;transition:filter .15s,box-shadow .15s,transform .05s}
.filters-apply-btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px var(--accent-bg)}
.filters-apply-btn:active{transform:translateY(1px)}
.filters-date-presets{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:10px 0 0;margin-top:12px;border-top:1px dashed var(--border)}
.filters-date-presets-label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-right:4px;padding-top:8px}
.date-preset-chip{padding:5px 12px;font-size:11px;font-weight:600;border-radius:14px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;white-space:nowrap;transition:all 120ms;margin-top:6px}
.date-preset-chip:hover{border-color:var(--accent);color:var(--accent)}
.date-preset-chip.active{font-weight:700;border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
@media(max-width:560px){.filter-group{flex:1 1 100%}.filter-input,select.filter-input{min-width:0;width:100%}.filters-apply-btn{width:100%}}

.ops-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:14px}
.ops-field{display:flex;flex-direction:column;gap:5px;min-width:0}
.ops-field--full{grid-column:1/-1}
.ops-field-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.ops-field-label .req{color:var(--danger);margin-left:3px}
.ops-input,.ops-select,.ops-textarea{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;transition:border-color .15s;width:100%}
.ops-textarea{resize:vertical;min-height:70px;font-family:inherit}
.ops-input:focus,.ops-select:focus,.ops-textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.ops-input:disabled,.ops-select:disabled{opacity:.55;cursor:not-allowed}
.ops-select{appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px}
.ops-field-hint{font-size:11px;color:var(--muted);line-height:1.45}
.ops-saisi-par{display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px dashed var(--border);border-radius:10px;color:var(--muted);font-size:12px;margin-bottom:14px}
.ops-saisi-par strong{color:var(--text);font-weight:600}
.ops-btn-add{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:10px;border:none;background:var(--accent);color:var(--accent-fg);font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;transition:filter .15s,background .15s,color .15s;white-space:nowrap}
.ops-btn-add:hover{filter:brightness(1.08)}
.ops-list{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:18px}
.ops-list-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 22px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.ops-list-head-right{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.ops-list-title{font-size:14px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.ops-list-count{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
.ops-table-wrap{overflow-x:auto}
.ops-table{width:100%;border-collapse:collapse;font-size:13px;color:var(--text2)}
.ops-table th{text-align:left;padding:12px 18px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);background:var(--bg);user-select:none;white-space:nowrap}
.ops-table th[data-sort],.ops-table th[data-sort-cat],.ops-table th[data-sort-ctrl],.ops-table th[data-sort-ctrl-cat]{cursor:pointer;transition:color .15s}
.ops-table th[data-sort]:hover,.ops-table th[data-sort-cat]:hover,.ops-table th[data-sort-ctrl]:hover,.ops-table th[data-sort-ctrl-cat]:hover{color:var(--accent)}
.ops-table th[data-sort].active,.ops-table th[data-sort-cat].active,.ops-table th[data-sort-ctrl].active,.ops-table th[data-sort-ctrl-cat].active{color:var(--accent)}
.ops-table th .sort-ico{display:inline-block;margin-left:5px;opacity:.55;font-size:11px}
.ops-table th.active .sort-ico{opacity:1}
.ops-table td{padding:12px 18px;border-bottom:1px solid var(--border);vertical-align:top}
.ops-table tr:last-child td{border-bottom:none}
.ops-table tr:hover td{background:var(--bg)}
.ops-table .col-comment{max-width:340px;white-space:pre-wrap;color:var(--text2);font-size:12.5px;word-break:break-word}
.ops-table .col-date{color:var(--muted);font-size:12px;white-space:nowrap}
.ops-table .col-actions{white-space:nowrap;text-align:right}
.ops-row-btn{background:transparent;border:none;color:var(--muted);cursor:pointer;padding:4px;border-radius:6px;transition:.15s;display:inline-flex;align-items:center;margin-left:2px}
.ops-row-btn:hover{background:var(--bg)}
.ops-row-btn.edit:hover{color:var(--accent)}
.ops-row-btn.del:hover{color:var(--danger)}
.ops-empty{padding:32px 22px;text-align:center;color:var(--muted);font-size:13px}
.niv-badge{display:inline-flex;align-items:center;justify-content:center;min-width:32px;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;background:var(--accent-bg);color:var(--accent);letter-spacing:.3px}
.niv-badge[data-niv="1"]{background:rgba(52,211,153,.15);color:var(--ok)}
.niv-badge[data-niv="2"]{background:rgba(251,191,36,.18);color:var(--warn)}
.niv-badge[data-niv="3"]{background:rgba(248,113,113,.18);color:var(--danger)}
body.light .niv-badge[data-niv="1"]{background:rgba(5,150,105,.14)}
body.light .niv-badge[data-niv="2"]{background:rgba(217,119,6,.14)}
body.light .niv-badge[data-niv="3"]{background:rgba(220,38,38,.14)}

/* Modal */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1500;display:none;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(2px)}
.modal-overlay.open{display:flex}
.modal-card{background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:640px;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.45);overflow:hidden}
.modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 22px;border-bottom:1px solid var(--border)}
.modal-title{font-size:14px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.modal-close{background:transparent;border:none;color:var(--muted);cursor:pointer;padding:6px;border-radius:8px;display:inline-flex;align-items:center;transition:.15s}
.modal-close:hover{color:var(--danger);background:var(--bg)}
.modal-body{padding:20px 22px;overflow-y:auto;flex:1}
.modal-foot{display:flex;justify-content:flex-end;gap:8px;padding:14px 22px;border-top:1px solid var(--border);background:var(--bg)}
.modal-btn-ghost{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;transition:.15s}
.modal-btn-ghost:hover{border-color:var(--accent);color:var(--accent)}

.toast-wrap{position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:8px;z-index:2000}
.toast{padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 4px 24px rgba(0,0,0,.4);max-width:340px;transition:opacity .3s}
.toast.info{background:var(--card);color:var(--text2);border:1px solid var(--border)}
.toast.success{background:var(--success);color:var(--accent-fg);border:1px solid var(--success)}
.toast.danger{background:var(--danger);color:var(--accent-fg);border:1px solid var(--danger)}
body.light .toast.info{background:#fff;color:var(--text)}
</style>
</head>
<body>
<div class="app">
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>

  <nav class="sidebar" id="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Maintenance</span></div>
      <div class="logo-sub">by SIFA</div>
    </div>
    <button type="button" class="nav-btn active" data-view="maintenance" onclick="switchView('maintenance')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
      Maintenance
    </button>
    <button type="button" class="nav-btn" data-view="controles" onclick="switchView('controles')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      Contrôles
    </button>
    <button type="button" class="nav-btn" data-view="operations" onclick="switchView('operations')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18M3 12h18M3 17h18"/></svg>
      Opérations de maintenance
    </button>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn nav-btn--mysifa-portal" onclick="location.href='/'">
        <span class="mysifa-back-preamble">← Retour </span>
        <span class="mysifa-back-brand">My<span class="mysifa-back-accent">Sifa</span></span>
      </button>
      <div class="user-chip" id="user-chip" onclick="location.href='/profil'"></div>
      <button type="button" class="theme-btn" onclick="toggleTheme()">
        <svg id="theme-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        <span id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" onclick="doLogout()">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">__V_LABEL__</div>
    </div>
  </nav>

  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Maintenance</div>
        <div class="mobile-topbar-sub">En cours de développement</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'">⌂</button>
    </div>

    <div class="content">
      <!-- View : Maintenance -->
      <div class="view" id="view-maintenance">
        <div class="page-header">
          <div>
            <div class="page-title">My<span>Maintenance</span></div>
            <div class="page-subtitle">Suivi et planification de la maintenance</div>
          </div>
          <div class="page-actions">
            <button type="button" class="btn" disabled aria-disabled="true" title="Fonctionnalité en cours de développement">
              <span class="btn-ico"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span>
              Créer une alerte
              <span class="badge-dev">En développement</span>
            </button>
          </div>
        </div>
        <div class="wip-wrap">
          <div class="wip-card">
            <div class="wip-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
            </div>
            <div class="wip-title">Application en cours de développement</div>
            <div class="wip-sub">Le module Maintenance arrive prochainement. Les fonctionnalités seront ajoutées progressivement.</div>
            <div class="wip-meta">Accès restreint — version préliminaire</div>
          </div>
        </div>
      </div>

      <!-- View : Contrôles -->
      <div class="view" id="view-controles" style="display:none">
        <div class="page-header">
          <div>
            <div class="page-title">Contrôles</div>
            <div class="page-subtitle">Saisie et suivi des contrôles de maintenance</div>
          </div>
        </div>

        <!-- Filtres Historique des contrôles -->
        <div class="filters-panel">
          <div class="filters">
            <div class="filter-group">
              <label for="filt-controles-type">Type de contrôle</label>
              <select id="filt-controles-type" class="filter-input">
                <option value="">Tous les types</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-controles-operateur">Opérateur</label>
              <select id="filt-controles-operateur" class="filter-input">
                <option value="">Tous les opérateurs</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-controles-machine">Machine</label>
              <select id="filt-controles-machine" class="filter-input">
                <option value="">Toutes les machines</option>
                <option value="Cohésio 1">Cohésio 1</option>
                <option value="Cohésio 2">Cohésio 2</option>
                <option value="DSI">DSI</option>
                <option value="Repiquage">Repiquage</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-controles-date-from">Du</label>
              <input type="date" id="filt-controles-date-from" class="filter-input" aria-label="Du">
            </div>
            <div class="filter-group">
              <label for="filt-controles-date-to">Au</label>
              <input type="date" id="filt-controles-date-to" class="filter-input" aria-label="Au">
            </div>
            <button type="button" class="filters-apply-btn" onclick="renderCtrl()">Filtrer</button>
          </div>
          <div class="filters-date-presets" id="ctrl-date-presets">
            <span class="filters-date-presets-label">Période :</span>
            <button type="button" class="date-preset-chip" data-preset="today" onclick="applyCtrlDatePreset('today')">Aujourd'hui</button>
            <button type="button" class="date-preset-chip" data-preset="yesterday" onclick="applyCtrlDatePreset('yesterday')">Hier</button>
            <button type="button" class="date-preset-chip" data-preset="last7" onclick="applyCtrlDatePreset('last7')">7 derniers jours</button>
            <button type="button" class="date-preset-chip" data-preset="last30" onclick="applyCtrlDatePreset('last30')">30 derniers jours</button>
            <button type="button" class="date-preset-chip" data-preset="thisMonth" onclick="applyCtrlDatePreset('thisMonth')">Mois en cours</button>
            <button type="button" class="date-preset-chip" data-preset="prevMonth" onclick="applyCtrlDatePreset('prevMonth')">Mois dernier</button>
          </div>
        </div>

        <!-- Historique des contrôles -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Historique des contrôles</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count" id="ctrl-count">0 contrôle</div>
              <button type="button" class="ops-btn-add" onclick="openCtrlModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Nouveau contrôle
              </button>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort-ctrl="date_saisie" onclick="sortCtrl('date_saisie')">Date saisie<span class="sort-ico">↕</span></th>
                  <th data-sort-ctrl="machine" onclick="sortCtrl('machine')">Machine<span class="sort-ico">↕</span></th>
                  <th data-sort-ctrl="operateur" onclick="sortCtrl('operateur')">Opérateur<span class="sort-ico">↕</span></th>
                  <th data-sort-ctrl="type" onclick="sortCtrl('type')">Type<span class="sort-ico">↕</span></th>
                  <th>Commentaires</th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="ctrl-tbody"></tbody>
            </table>
          </div>
        </div>

        <!-- Liste de contrôles (catalogue) -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Liste de contrôles</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count" id="ctrl-cat-count">0 contrôle</div>
              <button type="button" class="ops-btn-add" onclick="openCtrlCatModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Ajouter un contrôle à la liste
              </button>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort-ctrl-cat="nom" onclick="sortCtrlTypes('nom')">Nom<span class="sort-ico">↕</span></th>
                  <th>Détail</th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="ctrl-cat-tbody"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- View : Opérations de maintenance -->
      <div class="view" id="view-operations" style="display:none">
        <div class="page-header">
          <div>
            <div class="page-title">Opérations de maintenance</div>
            <div class="page-subtitle">Saisie et suivi des opérations effectuées</div>
          </div>
        </div>

        <!-- Filtres Historique des opérations -->
        <div class="filters-panel">
          <div class="filters">
            <div class="filter-group">
              <label for="filt-operations-type">Type d'opération</label>
              <select id="filt-operations-type" class="filter-input">
                <option value="">Tous les types</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-operations-operateur">Opérateur</label>
              <select id="filt-operations-operateur" class="filter-input">
                <option value="">Tous les opérateurs</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-operations-machine">Machine</label>
              <select id="filt-operations-machine" class="filter-input">
                <option value="">Toutes les machines</option>
                <option value="Cohésio 1">Cohésio 1</option>
                <option value="Cohésio 2">Cohésio 2</option>
                <option value="DSI">DSI</option>
                <option value="Repiquage">Repiquage</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-operations-date-from">Du</label>
              <input type="date" id="filt-operations-date-from" class="filter-input" aria-label="Du">
            </div>
            <div class="filter-group">
              <label for="filt-operations-date-to">Au</label>
              <input type="date" id="filt-operations-date-to" class="filter-input" aria-label="Au">
            </div>
            <button type="button" class="filters-apply-btn" onclick="renderOps()">Filtrer</button>
          </div>
          <div class="filters-date-presets" id="ops-date-presets">
            <span class="filters-date-presets-label">Période :</span>
            <button type="button" class="date-preset-chip" data-preset="today" onclick="applyOpsDatePreset('today')">Aujourd'hui</button>
            <button type="button" class="date-preset-chip" data-preset="yesterday" onclick="applyOpsDatePreset('yesterday')">Hier</button>
            <button type="button" class="date-preset-chip" data-preset="last7" onclick="applyOpsDatePreset('last7')">7 derniers jours</button>
            <button type="button" class="date-preset-chip" data-preset="last30" onclick="applyOpsDatePreset('last30')">30 derniers jours</button>
            <button type="button" class="date-preset-chip" data-preset="thisMonth" onclick="applyOpsDatePreset('thisMonth')">Mois en cours</button>
            <button type="button" class="date-preset-chip" data-preset="prevMonth" onclick="applyOpsDatePreset('prevMonth')">Mois dernier</button>
          </div>
        </div>

        <!-- Historique des opérations -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Historique des opérations</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count" id="ops-count">0 opération</div>
              <button type="button" class="ops-btn-add" onclick="openOpsModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Nouvelle opération
              </button>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort="date_saisie" onclick="sortOps('date_saisie')">Date saisie<span class="sort-ico">↕</span></th>
                  <th data-sort="machine" onclick="sortOps('machine')">Machine<span class="sort-ico">↕</span></th>
                  <th data-sort="operateur" onclick="sortOps('operateur')">Opérateur<span class="sort-ico">↕</span></th>
                  <th data-sort="type" onclick="sortOps('type')">Type<span class="sort-ico">↕</span></th>
                  <th>Commentaires</th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="ops-tbody"></tbody>
            </table>
          </div>
        </div>

        <!-- Liste d'opérations de maintenance (catalogue) -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Liste d'opérations de maintenance</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count" id="cat-count">0 opération</div>
              <button type="button" class="ops-btn-add" onclick="openCatModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Ajouter une opération à la liste
              </button>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort-cat="nom" onclick="sortOpsTypes('nom')">Nom<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="niveau" onclick="sortOpsTypes('niveau')">Niveau<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="frequence" onclick="sortOpsTypes('frequence')">Fréquence<span class="sort-ico">↕</span></th>
                  <th>Détail</th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="cat-tbody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </main>
</div>

<!-- Modal : Nouvelle opération -->
<div class="modal-overlay" id="ops-modal" onclick="if(event.target===this) closeOpsModal()" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="ops-modal-title">
    <div class="modal-head">
      <div class="modal-title" id="ops-modal-title">Nouvelle opération</div>
      <button type="button" class="modal-close" onclick="closeOpsModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="ops-form" onsubmit="addOperation(event)">
      <div class="modal-body">
        <div class="ops-saisi-par">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <span>Saisi par : <strong id="ops-saisi-par-name">…</strong></span>
        </div>
        <div class="ops-form-grid">
          <div class="ops-field">
            <label class="ops-field-label" for="ops-machine">Machine<span class="req">*</span></label>
            <select id="ops-machine" class="ops-select" required>
              <option value="">Sélectionner…</option>
              <option value="Cohésio 1">Cohésio 1</option>
              <option value="Cohésio 2">Cohésio 2</option>
              <option value="DSI">DSI</option>
              <option value="Repiquage">Repiquage</option>
            </select>
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="ops-type">Type d'opération<span class="req">*</span></label>
            <select id="ops-type" class="ops-select" required>
              <option value="">Aucun type défini…</option>
            </select>
            <div class="ops-field-hint" id="ops-type-hint" style="display:none">
              Aucun type défini. Ajoutez-en dans « Liste d'opérations de maintenance ».
            </div>
          </div>
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="ops-comment">Commentaires</label>
            <textarea id="ops-comment" class="ops-textarea" placeholder="Notes, anomalies, durée, pièces remplacées…"></textarea>
          </div>
        </div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeOpsModal()">Annuler</button>
        <button type="submit" class="ops-btn-add">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Enregistrer l'opération
        </button>
      </div>
    </form>
  </div>
</div>

<!-- Modal : Catalogue opérations -->
<div class="modal-overlay" id="cat-modal" onclick="if(event.target===this) closeCatModal()" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="cat-modal-title">
    <div class="modal-head">
      <div class="modal-title" id="cat-modal-title">Ajouter une opération à la liste</div>
      <button type="button" class="modal-close" onclick="closeCatModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="cat-form" onsubmit="submitOpsType(event)">
      <div class="modal-body">
        <div class="ops-form-grid">
          <div class="ops-field">
            <label class="ops-field-label" for="cat-nom">Nom de l'opération<span class="req">*</span></label>
            <input type="text" id="cat-nom" class="ops-input" placeholder="Ex : Vidange hydraulique" required autocomplete="off">
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="cat-niveau">Niveau de maintenance<span class="req">*</span></label>
            <select id="cat-niveau" class="ops-select" required>
              <option value="">Sélectionner…</option>
              <option value="1">Niveau 1</option>
              <option value="2">Niveau 2</option>
              <option value="3">Niveau 3</option>
            </select>
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="cat-frequence">Fréquence conseillée<span class="req">*</span></label>
            <input type="text" id="cat-frequence" class="ops-input" placeholder="Ex : Tous les 6 mois, 500h, Hebdomadaire" required autocomplete="off">
          </div>
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="cat-detail">Détail</label>
            <textarea id="cat-detail" class="ops-textarea" placeholder="Description, étapes clés, points d'attention…"></textarea>
          </div>
        </div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeCatModal()">Annuler</button>
        <button type="submit" class="ops-btn-add" id="cat-submit-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span id="cat-submit-label">Ajouter à la liste</span>
        </button>
      </div>
    </form>
  </div>
</div>

<!-- Modal : Nouveau contrôle -->
<div class="modal-overlay" id="ctrl-modal" onclick="if(event.target===this) closeCtrlModal()" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="ctrl-modal-title">
    <div class="modal-head">
      <div class="modal-title" id="ctrl-modal-title">Nouveau contrôle</div>
      <button type="button" class="modal-close" onclick="closeCtrlModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="ctrl-form" onsubmit="addControle(event)">
      <div class="modal-body">
        <div class="ops-saisi-par">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <span>Saisi par : <strong id="ctrl-saisi-par-name">…</strong></span>
        </div>
        <div class="ops-form-grid">
          <div class="ops-field">
            <label class="ops-field-label" for="ctrl-machine">Machine<span class="req">*</span></label>
            <select id="ctrl-machine" class="ops-select" required>
              <option value="">Sélectionner…</option>
              <option value="Cohésio 1">Cohésio 1</option>
              <option value="Cohésio 2">Cohésio 2</option>
              <option value="DSI">DSI</option>
              <option value="Repiquage">Repiquage</option>
            </select>
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="ctrl-type">Type de contrôle<span class="req">*</span></label>
            <select id="ctrl-type" class="ops-select" required>
              <option value="">Aucun type défini…</option>
            </select>
            <div class="ops-field-hint" id="ctrl-type-hint" style="display:none">
              Aucun type défini. Ajoutez-en dans « Liste de contrôles ».
            </div>
          </div>
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="ctrl-comment">Commentaires</label>
            <textarea id="ctrl-comment" class="ops-textarea" placeholder="Constatations, anomalies, mesures…"></textarea>
          </div>
        </div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeCtrlModal()">Annuler</button>
        <button type="submit" class="ops-btn-add">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Enregistrer le contrôle
        </button>
      </div>
    </form>
  </div>
</div>

<!-- Modal : Catalogue contrôles -->
<div class="modal-overlay" id="ctrl-cat-modal" onclick="if(event.target===this) closeCtrlCatModal()" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="ctrl-cat-modal-title">
    <div class="modal-head">
      <div class="modal-title" id="ctrl-cat-modal-title">Ajouter un contrôle à la liste</div>
      <button type="button" class="modal-close" onclick="closeCtrlCatModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="ctrl-cat-form" onsubmit="submitCtrlType(event)">
      <div class="modal-body">
        <div class="ops-form-grid">
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="ctrl-cat-nom">Nom du contrôle<span class="req">*</span></label>
            <input type="text" id="ctrl-cat-nom" class="ops-input" placeholder="Ex : Vérification niveau d'huile" required autocomplete="off">
          </div>
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="ctrl-cat-detail">Détail</label>
            <textarea id="ctrl-cat-detail" class="ops-textarea" placeholder="Description, méthode, critères d'acceptation…"></textarea>
          </div>
        </div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeCtrlCatModal()">Annuler</button>
        <button type="submit" class="ops-btn-add" id="ctrl-cat-submit-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span id="ctrl-cat-submit-label">Ajouter à la liste</span>
        </button>
      </div>
    </form>
  </div>
</div>

<div class="toast-wrap" id="toast-wrap"></div>

<script>
'use strict';

const S = { me: null };

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const VIEW_META = {
  maintenance: { title: 'Maintenance', sub: 'En cours de développement' },
  controles:   { title: 'Contrôles',   sub: 'Saisie et suivi des contrôles' },
  operations:  { title: 'Opérations de maintenance', sub: 'Saisie et suivi' }
};
function switchView(name){
  if(!VIEW_META[name]) return;
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  const target = document.getElementById('view-' + name);
  if(target) target.style.display = 'flex';
  document.querySelectorAll('.nav-btn[data-view]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === name);
  });
  const meta = VIEW_META[name];
  const t = document.querySelector('.mobile-topbar-title');
  const s = document.querySelector('.mobile-topbar-sub');
  if(t) t.textContent = meta.title;
  if(s) s.textContent = meta.sub;
  try{ history.replaceState(null, '', '#' + name); }catch(e){}
  closeSidebar();
}

// --- Toast ---
function showToast(msg, type){
  const wrap = document.getElementById('toast-wrap');
  if(!wrap) return;
  const t = document.createElement('div');
  t.className = 'toast ' + (type || 'info');
  t.textContent = msg;
  wrap.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; }, 2400);
  setTimeout(() => { try{ t.remove(); }catch(e){} }, 2800);
}

// --- Helper : nom de l'utilisateur courant ---
function currentUserName(){
  if(!S.me) return '';
  return (S.me.nom || S.me.identifiant || S.me.email || '').trim();
}

function escHtml(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function escAttr(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}

function fmtDate(iso){
  if(!iso) return '';
  try{
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'});
  }catch(e){ return String(iso); }
}

// --- Modales ---
function openOpsModal(){
  const m = document.getElementById('ops-modal');
  if(!m) return;
  if(!OPS_TYPES_STATE.list.length){
    showToast('Définissez d\'abord au moins un type dans « Liste d\'opérations de maintenance ».', 'danger');
    return;
  }
  if(!currentUserName()){
    showToast('Identité non chargée. Réessayez dans un instant.', 'danger');
    return;
  }
  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  refreshOpsTypeSelect();
  const nameEl = document.getElementById('ops-saisi-par-name');
  if(nameEl) nameEl.textContent = currentUserName();
  setTimeout(() => { const f = document.getElementById('ops-machine'); if(f) f.focus(); }, 50);
}
function closeOpsModal(){
  const m = document.getElementById('ops-modal');
  if(!m) return;
  m.classList.remove('open');
  m.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  const f = document.getElementById('ops-form');
  if(f) f.reset();
}

let CAT_EDITING_ID = null;
function openCatModal(idToEdit){
  const m = document.getElementById('cat-modal');
  if(!m) return;
  const titleEl = document.getElementById('cat-modal-title');
  const lblEl = document.getElementById('cat-submit-label');
  const form = document.getElementById('cat-form');
  if(form) form.reset();
  CAT_EDITING_ID = null;
  if(idToEdit){
    const t = OPS_TYPES_STATE.list.find(x => x.id === idToEdit);
    if(t){
      CAT_EDITING_ID = idToEdit;
      document.getElementById('cat-nom').value = t.nom || '';
      document.getElementById('cat-niveau').value = String(t.niveau || '');
      document.getElementById('cat-frequence').value = t.frequence || '';
      document.getElementById('cat-detail').value = t.detail || '';
      if(titleEl) titleEl.textContent = 'Modifier l\'opération';
      if(lblEl) lblEl.textContent = 'Enregistrer les modifications';
    }
  } else {
    if(titleEl) titleEl.textContent = 'Ajouter une opération à la liste';
    if(lblEl) lblEl.textContent = 'Ajouter à la liste';
  }
  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  setTimeout(() => { const f = document.getElementById('cat-nom'); if(f) f.focus(); }, 50);
}
function closeCatModal(){
  const m = document.getElementById('cat-modal');
  if(!m) return;
  m.classList.remove('open');
  m.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  const f = document.getElementById('cat-form');
  if(f) f.reset();
  CAT_EDITING_ID = null;
}

function openCtrlModal(){
  const m = document.getElementById('ctrl-modal');
  if(!m) return;
  if(!CTRL_TYPES_STATE.list.length){
    showToast('Définissez d\'abord au moins un type dans « Liste de contrôles ».', 'danger');
    return;
  }
  if(!currentUserName()){
    showToast('Identité non chargée. Réessayez dans un instant.', 'danger');
    return;
  }
  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  refreshCtrlTypeSelect();
  const nameEl = document.getElementById('ctrl-saisi-par-name');
  if(nameEl) nameEl.textContent = currentUserName();
  setTimeout(() => { const f = document.getElementById('ctrl-machine'); if(f) f.focus(); }, 50);
}
function closeCtrlModal(){
  const m = document.getElementById('ctrl-modal');
  if(!m) return;
  m.classList.remove('open');
  m.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  const f = document.getElementById('ctrl-form');
  if(f) f.reset();
}

let CTRL_CAT_EDITING_ID = null;
function openCtrlCatModal(idToEdit){
  const m = document.getElementById('ctrl-cat-modal');
  if(!m) return;
  const titleEl = document.getElementById('ctrl-cat-modal-title');
  const lblEl = document.getElementById('ctrl-cat-submit-label');
  const form = document.getElementById('ctrl-cat-form');
  if(form) form.reset();
  CTRL_CAT_EDITING_ID = null;
  if(idToEdit){
    const t = CTRL_TYPES_STATE.list.find(x => x.id === idToEdit);
    if(t){
      CTRL_CAT_EDITING_ID = idToEdit;
      document.getElementById('ctrl-cat-nom').value = t.nom || '';
      document.getElementById('ctrl-cat-detail').value = t.detail || '';
      if(titleEl) titleEl.textContent = 'Modifier le contrôle';
      if(lblEl) lblEl.textContent = 'Enregistrer les modifications';
    }
  } else {
    if(titleEl) titleEl.textContent = 'Ajouter un contrôle à la liste';
    if(lblEl) lblEl.textContent = 'Ajouter à la liste';
  }
  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  setTimeout(() => { const f = document.getElementById('ctrl-cat-nom'); if(f) f.focus(); }, 50);
}
function closeCtrlCatModal(){
  const m = document.getElementById('ctrl-cat-modal');
  if(!m) return;
  m.classList.remove('open');
  m.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  const f = document.getElementById('ctrl-cat-form');
  if(f) f.reset();
  CTRL_CAT_EDITING_ID = null;
}

function closeAnyOpenModal(){
  ['ops-modal', 'cat-modal', 'ctrl-modal', 'ctrl-cat-modal'].forEach(id => {
    const m = document.getElementById(id);
    if(m && m.classList.contains('open')){
      if(id === 'ops-modal') closeOpsModal();
      else if(id === 'cat-modal') closeCatModal();
      else if(id === 'ctrl-modal') closeCtrlModal();
      else closeCtrlCatModal();
    }
  });
}
document.addEventListener('keydown', function(e){
  if(e.key === 'Escape') closeAnyOpenModal();
});

// =========================================================================
// Historique des opérations
// =========================================================================
const OPS_STORAGE_KEY = 'mysifa_maint_operations_v1';
const OPS_STATE = { sortBy: 'date_saisie', sortDir: 'desc', list: [] };

function loadOps(){
  try{
    const raw = localStorage.getItem(OPS_STORAGE_KEY);
    OPS_STATE.list = raw ? JSON.parse(raw) : [];
    if(!Array.isArray(OPS_STATE.list)) OPS_STATE.list = [];
  }catch(e){ OPS_STATE.list = []; }
}
function saveOps(){
  try{ localStorage.setItem(OPS_STORAGE_KEY, JSON.stringify(OPS_STATE.list)); }catch(e){}
}
function addOperation(e){
  e.preventDefault();
  const machine = (document.getElementById('ops-machine').value || '').trim();
  const type = (document.getElementById('ops-type').value || '').trim();
  const commentaire = (document.getElementById('ops-comment').value || '').trim();
  const operateur = currentUserName();
  if(!operateur){ showToast('Identité non chargée. Réessayez dans un instant.', 'danger'); return; }
  if(!machine || !type){ showToast('Machine et type sont requis.', 'danger'); return; }
  OPS_STATE.list.push({
    id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8),
    machine, operateur, type, commentaire,
    date_saisie: new Date().toISOString()
  });
  saveOps();
  renderOps();
  closeOpsModal();
  showToast('Opération enregistrée.', 'info');
}
function deleteOp(id){
  if(!confirm('Supprimer cette opération ?')) return;
  OPS_STATE.list = OPS_STATE.list.filter(o => o.id !== id);
  saveOps();
  renderOps();
}
function sortOps(field){
  if(OPS_STATE.sortBy === field){
    OPS_STATE.sortDir = OPS_STATE.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    OPS_STATE.sortBy = field;
    OPS_STATE.sortDir = field === 'date_saisie' ? 'desc' : 'asc';
  }
  renderOps();
}
function getOpsFilters(){
  const v = id => (document.getElementById(id)?.value || '').trim();
  return {
    type:     v('filt-operations-type'),
    operateur:v('filt-operations-operateur'),
    machine:  v('filt-operations-machine'),
    dateFrom: v('filt-operations-date-from'),
    dateTo:   v('filt-operations-date-to'),
  };
}
function resetOpsFilters(){
  ['type','operateur','machine','date-from','date-to'].forEach(k => {
    const el = document.getElementById('filt-operations-' + k);
    if(el) el.value = '';
  });
  renderOps();
}
// ── Date presets partagés ─────────────────────────────────────────────
function maintDatePresets(){
  const now = new Date();
  const fmt = d => d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
  const today = new Date(now);
  const yesterday = new Date(now); yesterday.setDate(now.getDate()-1);
  const last7Start = new Date(now); last7Start.setDate(now.getDate()-6);
  const last30Start = new Date(now); last30Start.setDate(now.getDate()-29);
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const prevMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
  const prevMonthStart = new Date(now.getFullYear(), now.getMonth()-1, 1);
  return {
    today:     {from:fmt(today),         to:fmt(today)},
    yesterday: {from:fmt(yesterday),     to:fmt(yesterday)},
    last7:     {from:fmt(last7Start),    to:fmt(today)},
    last30:    {from:fmt(last30Start),   to:fmt(today)},
    thisMonth: {from:fmt(monthStart),    to:fmt(today)},
    prevMonth: {from:fmt(prevMonthStart),to:fmt(prevMonthEnd)},
  };
}
function applyOpsDatePreset(key){
  const p = maintDatePresets()[key];
  if(!p) return;
  const from = document.getElementById('filt-operations-date-from');
  const to   = document.getElementById('filt-operations-date-to');
  if(from) from.value = p.from;
  if(to)   to.value   = p.to;
  renderOps();
}
function updateOpsDatePresetChips(){
  const presets = maintDatePresets();
  const from = (document.getElementById('filt-operations-date-from')?.value || '').trim();
  const to   = (document.getElementById('filt-operations-date-to')?.value   || '').trim();
  document.querySelectorAll('#ops-date-presets .date-preset-chip').forEach(chip => {
    const key = chip.getAttribute('data-preset');
    const p = presets[key];
    chip.classList.toggle('active', !!(p && p.from === from && p.to === to));
  });
}
function refreshOpsFiltersOptions(){
  const typeSel = document.getElementById('filt-operations-type');
  const opeSel  = document.getElementById('filt-operations-operateur');
  if(typeSel){
    const cur = typeSel.value;
    const types = OPS_TYPES_STATE.list.map(t => t.nom).filter(Boolean).sort((a,b) => a.localeCompare(b, 'fr'));
    typeSel.innerHTML = '<option value="">Tous les types</option>' +
      types.map(n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>').join('');
    if(cur && types.includes(cur)) typeSel.value = cur;
  }
  if(opeSel){
    const cur = opeSel.value;
    const opes = Array.from(new Set(OPS_STATE.list.map(o => o.operateur).filter(Boolean))).sort((a,b) => a.localeCompare(b, 'fr'));
    opeSel.innerHTML = '<option value="">Tous les opérateurs</option>' +
      opes.map(n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>').join('');
    if(cur && opes.includes(cur)) opeSel.value = cur;
  }
}
function renderOps(){
  refreshOpsFiltersOptions();
  updateOpsDatePresetChips();
  const tbody = document.getElementById('ops-tbody');
  const count = document.getElementById('ops-count');
  if(!tbody) return;
  const f = getOpsFilters();
  // Auto-correction si dateFrom > dateTo
  if(f.dateFrom && f.dateTo && f.dateFrom > f.dateTo){
    const to = document.getElementById('filt-operations-date-to');
    if(to){ to.value = f.dateFrom; f.dateTo = f.dateFrom; }
  }
  // Filter
  let filtered = OPS_STATE.list.filter(o => {
    if(f.type && o.type !== f.type) return false;
    if(f.operateur && o.operateur !== f.operateur) return false;
    if(f.machine && o.machine !== f.machine) return false;
    if(f.dateFrom || f.dateTo){
      const d = (o.date_saisie || '').slice(0,10);
      if(f.dateFrom && d < f.dateFrom) return false;
      if(f.dateTo && d > f.dateTo) return false;
    }
    return true;
  });
  // Sort
  const dir = OPS_STATE.sortDir === 'asc' ? 1 : -1;
  const sf = OPS_STATE.sortBy;
  filtered.sort((a,b) => {
    const av = (a[sf] != null ? a[sf] : '').toString().toLowerCase();
    const bv = (b[sf] != null ? b[sf] : '').toString().toLowerCase();
    if(av < bv) return -1*dir;
    if(av > bv) return  1*dir;
    return 0;
  });
  document.querySelectorAll('.ops-table th[data-sort]').forEach(th => {
    const isActive = th.getAttribute('data-sort') === sf;
    th.classList.toggle('active', isActive);
    const ico = th.querySelector('.sort-ico');
    if(ico) ico.textContent = isActive ? (OPS_STATE.sortDir === 'asc' ? '↑' : '↓') : '↕';
  });
  if(!filtered.length){
    const isFiltered = f.type || f.operateur || f.machine || f.dateFrom || f.dateTo;
    const msg = isFiltered
      ? 'Aucune opération ne correspond aux filtres.'
      : 'Aucune opération enregistrée. Cliquez sur « Nouvelle opération » pour commencer.';
    tbody.innerHTML = '<tr><td colspan="6" class="ops-empty">' + escHtml(msg) + '</td></tr>';
  } else {
    const rows = filtered.map(o =>
      '<tr>' +
        '<td class="col-date">' + escHtml(fmtDate(o.date_saisie)) + '</td>' +
        '<td>' + escHtml(o.machine) + '</td>' +
        '<td>' + escHtml(o.operateur) + '</td>' +
        '<td>' + escHtml(o.type) + '</td>' +
        '<td class="col-comment">' + escHtml(o.commentaire || '') + '</td>' +
        '<td class="col-actions">' +
          '<button type="button" class="ops-row-btn del" onclick="deleteOp(\'' + escAttr(o.id) + '\')" title="Supprimer">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          '</button>' +
        '</td>' +
      '</tr>'
    );
    tbody.innerHTML = rows.join('');
  }
  if(count){
    const n = OPS_STATE.list.length;
    const visible = filtered.length;
    if(visible !== n){
      count.textContent = visible + ' / ' + n + ' opération' + (n > 1 ? 's' : '');
    } else {
      count.textContent = n + ' opération' + (n > 1 ? 's' : '');
    }
  }
}

// =========================================================================
// Catalogue des types d'opérations
// =========================================================================
const OPS_TYPES_STORAGE_KEY = 'mysifa_maint_optypes_v1';
const OPS_TYPES_STATE = { sortBy: 'nom', sortDir: 'asc', list: [] };

function loadOpsTypes(){
  try{
    const raw = localStorage.getItem(OPS_TYPES_STORAGE_KEY);
    OPS_TYPES_STATE.list = raw ? JSON.parse(raw) : [];
    if(!Array.isArray(OPS_TYPES_STATE.list)) OPS_TYPES_STATE.list = [];
  }catch(e){ OPS_TYPES_STATE.list = []; }
}
function saveOpsTypes(){
  try{ localStorage.setItem(OPS_TYPES_STORAGE_KEY, JSON.stringify(OPS_TYPES_STATE.list)); }catch(e){}
}
function submitOpsType(e){
  e.preventDefault();
  const nom = (document.getElementById('cat-nom').value || '').trim();
  const niveau = parseInt(document.getElementById('cat-niveau').value, 10);
  const frequence = (document.getElementById('cat-frequence').value || '').trim();
  const detail = (document.getElementById('cat-detail').value || '').trim();
  if(!nom || !niveau || !frequence){ showToast('Nom, niveau et fréquence sont requis.', 'danger'); return; }
  if(niveau < 1 || niveau > 3){ showToast('Niveau doit être entre 1 et 3.', 'danger'); return; }
  const dup = OPS_TYPES_STATE.list.find(t =>
    (t.nom || '').toLowerCase() === nom.toLowerCase() && t.id !== CAT_EDITING_ID
  );
  if(dup){ showToast('Un autre type avec ce nom existe déjà.', 'danger'); return; }
  let oldName = null;
  if(CAT_EDITING_ID){
    const cur = OPS_TYPES_STATE.list.find(t => t.id === CAT_EDITING_ID);
    if(cur && cur.nom !== nom) oldName = cur.nom;
  }
  if(CAT_EDITING_ID){
    OPS_TYPES_STATE.list = OPS_TYPES_STATE.list.map(t =>
      t.id === CAT_EDITING_ID
        ? Object.assign({}, t, {nom, niveau, frequence, detail, date_modification: new Date().toISOString()})
        : t
    );
  } else {
    OPS_TYPES_STATE.list.push({
      id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8),
      nom, niveau, frequence, detail,
      date_creation: new Date().toISOString()
    });
  }
  saveOpsTypes();
  let renameApplied = false;
  if(oldName){
    const affected = OPS_STATE.list.filter(o => o.type === oldName).length;
    if(affected > 0 && confirm(affected + ' opération' + (affected>1?'s':'') + ' enregistrée' + (affected>1?'s':'') + ' utilise' + (affected>1?'nt':'') + ' encore le nom « ' + oldName + ' ».\n\nMettre à jour ces opérations vers « ' + nom + ' » ?')){
      OPS_STATE.list = OPS_STATE.list.map(o =>
        o.type === oldName ? Object.assign({}, o, {type: nom}) : o
      );
      saveOps();
      renameApplied = true;
    }
  }
  renderOpsTypes();
  if(renameApplied) renderOps();
  closeCatModal();
  showToast(CAT_EDITING_ID ? 'Modifications enregistrées.' : 'Type ajouté à la liste.', 'info');
}
function deleteOpsType(id){
  const t = OPS_TYPES_STATE.list.find(x => x.id === id);
  if(!t) return;
  if(!confirm('Supprimer le type « ' + t.nom + ' » ?\n\nLes opérations déjà enregistrées avec ce nom restent inchangées.')) return;
  OPS_TYPES_STATE.list = OPS_TYPES_STATE.list.filter(x => x.id !== id);
  saveOpsTypes();
  renderOpsTypes();
}
function editOpsType(id){ openCatModal(id); }
function sortOpsTypes(field){
  if(OPS_TYPES_STATE.sortBy === field){
    OPS_TYPES_STATE.sortDir = OPS_TYPES_STATE.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    OPS_TYPES_STATE.sortBy = field;
    OPS_TYPES_STATE.sortDir = 'asc';
  }
  renderOpsTypes();
}
function refreshOpsTypeSelect(){
  const sel = document.getElementById('ops-type');
  const hint = document.getElementById('ops-type-hint');
  if(!sel) return;
  const cur = sel.value;
  if(!OPS_TYPES_STATE.list.length){
    sel.innerHTML = '<option value="">Aucun type défini…</option>';
    sel.disabled = true;
    if(hint) hint.style.display = 'block';
    return;
  }
  sel.disabled = false;
  if(hint) hint.style.display = 'none';
  const sorted = OPS_TYPES_STATE.list.slice().sort((a,b) => (a.nom || '').localeCompare(b.nom || '', 'fr'));
  sel.innerHTML = '<option value="">Sélectionner un type…</option>' +
    sorted.map(t => '<option value="' + escAttr(t.nom) + '">' + escHtml(t.nom) + '</option>').join('');
  if(cur && sorted.some(t => t.nom === cur)) sel.value = cur;
}
function renderOpsTypes(){
  refreshOpsTypeSelect();
  refreshOpsFiltersOptions();
  const tbody = document.getElementById('cat-tbody');
  const count = document.getElementById('cat-count');
  if(!tbody) return;
  const dir = OPS_TYPES_STATE.sortDir === 'asc' ? 1 : -1;
  const f = OPS_TYPES_STATE.sortBy;
  const sorted = OPS_TYPES_STATE.list.slice().sort((a,b) => {
    const av = a[f] != null ? a[f] : '';
    const bv = b[f] != null ? b[f] : '';
    if(typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
    const as = av.toString().toLowerCase();
    const bs = bv.toString().toLowerCase();
    if(as < bs) return -1 * dir;
    if(as > bs) return  1 * dir;
    return 0;
  });
  document.querySelectorAll('.ops-table th[data-sort-cat]').forEach(th => {
    const isActive = th.getAttribute('data-sort-cat') === f;
    th.classList.toggle('active', isActive);
    const ico = th.querySelector('.sort-ico');
    if(ico) ico.textContent = isActive ? (OPS_TYPES_STATE.sortDir === 'asc' ? '↑' : '↓') : '↕';
  });
  if(!sorted.length){
    tbody.innerHTML = '<tr><td colspan="5" class="ops-empty">Aucune opération dans la liste. Cliquez sur « Ajouter une opération à la liste » pour en créer une.</td></tr>';
  } else {
    const rows = sorted.map(t =>
      '<tr>' +
        '<td><strong style="color:var(--text)">' + escHtml(t.nom) + '</strong></td>' +
        '<td><span class="niv-badge" data-niv="' + t.niveau + '">N' + t.niveau + '</span></td>' +
        '<td>' + escHtml(t.frequence) + '</td>' +
        '<td class="col-comment">' + escHtml(t.detail || '') + '</td>' +
        '<td class="col-actions">' +
          '<button type="button" class="ops-row-btn edit" onclick="editOpsType(\'' + escAttr(t.id) + '\')" title="Modifier">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
          '</button>' +
          '<button type="button" class="ops-row-btn del" onclick="deleteOpsType(\'' + escAttr(t.id) + '\')" title="Supprimer">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          '</button>' +
        '</td>' +
      '</tr>'
    );
    tbody.innerHTML = rows.join('');
  }
  if(count){
    const n = OPS_TYPES_STATE.list.length;
    count.textContent = n + ' opération' + (n > 1 ? 's' : '');
  }
}

// =========================================================================
// Historique des contrôles
// =========================================================================
const CTRL_STORAGE_KEY = 'mysifa_maint_controles_v1';
const CTRL_STATE = { sortBy: 'date_saisie', sortDir: 'desc', list: [] };

function loadCtrl(){
  try{
    const raw = localStorage.getItem(CTRL_STORAGE_KEY);
    CTRL_STATE.list = raw ? JSON.parse(raw) : [];
    if(!Array.isArray(CTRL_STATE.list)) CTRL_STATE.list = [];
  }catch(e){ CTRL_STATE.list = []; }
}
function saveCtrl(){
  try{ localStorage.setItem(CTRL_STORAGE_KEY, JSON.stringify(CTRL_STATE.list)); }catch(e){}
}
function addControle(e){
  e.preventDefault();
  const machine = (document.getElementById('ctrl-machine').value || '').trim();
  const type = (document.getElementById('ctrl-type').value || '').trim();
  const commentaire = (document.getElementById('ctrl-comment').value || '').trim();
  const operateur = currentUserName();
  if(!operateur){ showToast('Identité non chargée. Réessayez dans un instant.', 'danger'); return; }
  if(!machine || !type){ showToast('Machine et type sont requis.', 'danger'); return; }
  CTRL_STATE.list.push({
    id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8),
    machine, operateur, type, commentaire,
    date_saisie: new Date().toISOString()
  });
  saveCtrl();
  renderCtrl();
  closeCtrlModal();
  showToast('Contrôle enregistré.', 'info');
}
function deleteCtrl(id){
  if(!confirm('Supprimer ce contrôle ?')) return;
  CTRL_STATE.list = CTRL_STATE.list.filter(c => c.id !== id);
  saveCtrl();
  renderCtrl();
}
function sortCtrl(field){
  if(CTRL_STATE.sortBy === field){
    CTRL_STATE.sortDir = CTRL_STATE.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    CTRL_STATE.sortBy = field;
    CTRL_STATE.sortDir = field === 'date_saisie' ? 'desc' : 'asc';
  }
  renderCtrl();
}
function getCtrlFilters(){
  const v = id => (document.getElementById(id)?.value || '').trim();
  return {
    type:     v('filt-controles-type'),
    operateur:v('filt-controles-operateur'),
    machine:  v('filt-controles-machine'),
    dateFrom: v('filt-controles-date-from'),
    dateTo:   v('filt-controles-date-to'),
  };
}
function resetCtrlFilters(){
  ['type','operateur','machine','date-from','date-to'].forEach(k => {
    const el = document.getElementById('filt-controles-' + k);
    if(el) el.value = '';
  });
  renderCtrl();
}
function applyCtrlDatePreset(key){
  const p = maintDatePresets()[key];
  if(!p) return;
  const from = document.getElementById('filt-controles-date-from');
  const to   = document.getElementById('filt-controles-date-to');
  if(from) from.value = p.from;
  if(to)   to.value   = p.to;
  renderCtrl();
}
function updateCtrlDatePresetChips(){
  const presets = maintDatePresets();
  const from = (document.getElementById('filt-controles-date-from')?.value || '').trim();
  const to   = (document.getElementById('filt-controles-date-to')?.value   || '').trim();
  document.querySelectorAll('#ctrl-date-presets .date-preset-chip').forEach(chip => {
    const key = chip.getAttribute('data-preset');
    const p = presets[key];
    chip.classList.toggle('active', !!(p && p.from === from && p.to === to));
  });
}
function refreshCtrlFiltersOptions(){
  const typeSel = document.getElementById('filt-controles-type');
  const opeSel  = document.getElementById('filt-controles-operateur');
  if(typeSel){
    const cur = typeSel.value;
    const types = CTRL_TYPES_STATE.list.map(t => t.nom).filter(Boolean).sort((a,b) => a.localeCompare(b, 'fr'));
    typeSel.innerHTML = '<option value="">Tous les types</option>' +
      types.map(n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>').join('');
    if(cur && types.includes(cur)) typeSel.value = cur;
  }
  if(opeSel){
    const cur = opeSel.value;
    const opes = Array.from(new Set(CTRL_STATE.list.map(c => c.operateur).filter(Boolean))).sort((a,b) => a.localeCompare(b, 'fr'));
    opeSel.innerHTML = '<option value="">Tous les opérateurs</option>' +
      opes.map(n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>').join('');
    if(cur && opes.includes(cur)) opeSel.value = cur;
  }
}
function renderCtrl(){
  refreshCtrlFiltersOptions();
  updateCtrlDatePresetChips();
  const tbody = document.getElementById('ctrl-tbody');
  const count = document.getElementById('ctrl-count');
  if(!tbody) return;
  const f = getCtrlFilters();
  // Auto-correction si dateFrom > dateTo
  if(f.dateFrom && f.dateTo && f.dateFrom > f.dateTo){
    const to = document.getElementById('filt-controles-date-to');
    if(to){ to.value = f.dateFrom; f.dateTo = f.dateFrom; }
  }
  // Filter
  let filtered = CTRL_STATE.list.filter(c => {
    if(f.type && c.type !== f.type) return false;
    if(f.operateur && c.operateur !== f.operateur) return false;
    if(f.machine && c.machine !== f.machine) return false;
    if(f.dateFrom || f.dateTo){
      const d = (c.date_saisie || '').slice(0,10);
      if(f.dateFrom && d < f.dateFrom) return false;
      if(f.dateTo && d > f.dateTo) return false;
    }
    return true;
  });
  // Sort
  const dir = CTRL_STATE.sortDir === 'asc' ? 1 : -1;
  const sf = CTRL_STATE.sortBy;
  filtered.sort((a,b) => {
    const av = (a[sf] != null ? a[sf] : '').toString().toLowerCase();
    const bv = (b[sf] != null ? b[sf] : '').toString().toLowerCase();
    if(av < bv) return -1 * dir;
    if(av > bv) return  1 * dir;
    return 0;
  });
  document.querySelectorAll('.ops-table th[data-sort-ctrl]').forEach(th => {
    const isActive = th.getAttribute('data-sort-ctrl') === sf;
    th.classList.toggle('active', isActive);
    const ico = th.querySelector('.sort-ico');
    if(ico) ico.textContent = isActive ? (CTRL_STATE.sortDir === 'asc' ? '↑' : '↓') : '↕';
  });
  if(!filtered.length){
    const isFiltered = f.type || f.operateur || f.machine || f.dateFrom || f.dateTo;
    const msg = isFiltered
      ? 'Aucun contrôle ne correspond aux filtres.'
      : 'Aucun contrôle enregistré. Cliquez sur « Nouveau contrôle » pour commencer.';
    tbody.innerHTML = '<tr><td colspan="6" class="ops-empty">' + escHtml(msg) + '</td></tr>';
  } else {
    const rows = filtered.map(c =>
      '<tr>' +
        '<td class="col-date">' + escHtml(fmtDate(c.date_saisie)) + '</td>' +
        '<td>' + escHtml(c.machine) + '</td>' +
        '<td>' + escHtml(c.operateur) + '</td>' +
        '<td>' + escHtml(c.type) + '</td>' +
        '<td class="col-comment">' + escHtml(c.commentaire || '') + '</td>' +
        '<td class="col-actions">' +
          '<button type="button" class="ops-row-btn del" onclick="deleteCtrl(\'' + escAttr(c.id) + '\')" title="Supprimer">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          '</button>' +
        '</td>' +
      '</tr>'
    );
    tbody.innerHTML = rows.join('');
  }
  if(count){
    const n = CTRL_STATE.list.length;
    const visible = filtered.length;
    if(visible !== n){
      count.textContent = visible + ' / ' + n + ' contrôle' + (n > 1 ? 's' : '');
    } else {
      count.textContent = n + ' contrôle' + (n > 1 ? 's' : '');
    }
  }
}

// =========================================================================
// Catalogue des types de contrôles (Liste de contrôles)
// =========================================================================
const CTRL_TYPES_STORAGE_KEY = 'mysifa_maint_ctrltypes_v1';
const CTRL_TYPES_STATE = { sortBy: 'nom', sortDir: 'asc', list: [] };

function loadCtrlTypes(){
  try{
    const raw = localStorage.getItem(CTRL_TYPES_STORAGE_KEY);
    CTRL_TYPES_STATE.list = raw ? JSON.parse(raw) : [];
    if(!Array.isArray(CTRL_TYPES_STATE.list)) CTRL_TYPES_STATE.list = [];
  }catch(e){ CTRL_TYPES_STATE.list = []; }
}
function saveCtrlTypes(){
  try{ localStorage.setItem(CTRL_TYPES_STORAGE_KEY, JSON.stringify(CTRL_TYPES_STATE.list)); }catch(e){}
}
function submitCtrlType(e){
  e.preventDefault();
  const nom = (document.getElementById('ctrl-cat-nom').value || '').trim();
  const detail = (document.getElementById('ctrl-cat-detail').value || '').trim();
  if(!nom){ showToast('Le nom est requis.', 'danger'); return; }
  const dup = CTRL_TYPES_STATE.list.find(t =>
    (t.nom || '').toLowerCase() === nom.toLowerCase() && t.id !== CTRL_CAT_EDITING_ID
  );
  if(dup){ showToast('Un autre contrôle avec ce nom existe déjà.', 'danger'); return; }
  let oldName = null;
  if(CTRL_CAT_EDITING_ID){
    const cur = CTRL_TYPES_STATE.list.find(t => t.id === CTRL_CAT_EDITING_ID);
    if(cur && cur.nom !== nom) oldName = cur.nom;
  }
  if(CTRL_CAT_EDITING_ID){
    CTRL_TYPES_STATE.list = CTRL_TYPES_STATE.list.map(t =>
      t.id === CTRL_CAT_EDITING_ID
        ? Object.assign({}, t, {nom, detail, date_modification: new Date().toISOString()})
        : t
    );
  } else {
    CTRL_TYPES_STATE.list.push({
      id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8),
      nom, detail,
      date_creation: new Date().toISOString()
    });
  }
  saveCtrlTypes();
  let renameApplied = false;
  if(oldName){
    const affected = CTRL_STATE.list.filter(c => c.type === oldName).length;
    if(affected > 0 && confirm(affected + ' contrôle' + (affected>1?'s':'') + ' enregistré' + (affected>1?'s':'') + ' utilise' + (affected>1?'nt':'') + ' encore le nom « ' + oldName + ' ».\n\nMettre à jour ces contrôles vers « ' + nom + ' » ?')){
      CTRL_STATE.list = CTRL_STATE.list.map(c =>
        c.type === oldName ? Object.assign({}, c, {type: nom}) : c
      );
      saveCtrl();
      renameApplied = true;
    }
  }
  renderCtrlTypes();
  if(renameApplied) renderCtrl();
  closeCtrlCatModal();
  showToast(CTRL_CAT_EDITING_ID ? 'Modifications enregistrées.' : 'Contrôle ajouté à la liste.', 'info');
}
function deleteCtrlType(id){
  const t = CTRL_TYPES_STATE.list.find(x => x.id === id);
  if(!t) return;
  if(!confirm('Supprimer le contrôle « ' + t.nom + ' » de la liste ?\n\nLes contrôles déjà enregistrés avec ce nom restent inchangés.')) return;
  CTRL_TYPES_STATE.list = CTRL_TYPES_STATE.list.filter(x => x.id !== id);
  saveCtrlTypes();
  renderCtrlTypes();
}
function editCtrlType(id){ openCtrlCatModal(id); }
function sortCtrlTypes(field){
  if(CTRL_TYPES_STATE.sortBy === field){
    CTRL_TYPES_STATE.sortDir = CTRL_TYPES_STATE.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    CTRL_TYPES_STATE.sortBy = field;
    CTRL_TYPES_STATE.sortDir = 'asc';
  }
  renderCtrlTypes();
}
function refreshCtrlTypeSelect(){
  const sel = document.getElementById('ctrl-type');
  const hint = document.getElementById('ctrl-type-hint');
  if(!sel) return;
  const cur = sel.value;
  if(!CTRL_TYPES_STATE.list.length){
    sel.innerHTML = '<option value="">Aucun type défini…</option>';
    sel.disabled = true;
    if(hint) hint.style.display = 'block';
    return;
  }
  sel.disabled = false;
  if(hint) hint.style.display = 'none';
  const sorted = CTRL_TYPES_STATE.list.slice().sort((a,b) => (a.nom || '').localeCompare(b.nom || '', 'fr'));
  sel.innerHTML = '<option value="">Sélectionner un type…</option>' +
    sorted.map(t => '<option value="' + escAttr(t.nom) + '">' + escHtml(t.nom) + '</option>').join('');
  if(cur && sorted.some(t => t.nom === cur)) sel.value = cur;
}
function renderCtrlTypes(){
  refreshCtrlTypeSelect();
  refreshCtrlFiltersOptions();
  const tbody = document.getElementById('ctrl-cat-tbody');
  const count = document.getElementById('ctrl-cat-count');
  if(!tbody) return;
  const dir = CTRL_TYPES_STATE.sortDir === 'asc' ? 1 : -1;
  const f = CTRL_TYPES_STATE.sortBy;
  const sorted = CTRL_TYPES_STATE.list.slice().sort((a,b) => {
    const av = (a[f] != null ? a[f] : '').toString().toLowerCase();
    const bv = (b[f] != null ? b[f] : '').toString().toLowerCase();
    if(av < bv) return -1 * dir;
    if(av > bv) return  1 * dir;
    return 0;
  });
  document.querySelectorAll('.ops-table th[data-sort-ctrl-cat]').forEach(th => {
    const isActive = th.getAttribute('data-sort-ctrl-cat') === f;
    th.classList.toggle('active', isActive);
    const ico = th.querySelector('.sort-ico');
    if(ico) ico.textContent = isActive ? (CTRL_TYPES_STATE.sortDir === 'asc' ? '↑' : '↓') : '↕';
  });
  if(!sorted.length){
    tbody.innerHTML = '<tr><td colspan="3" class="ops-empty">Aucun contrôle dans la liste. Cliquez sur « Ajouter un contrôle à la liste » pour en créer un.</td></tr>';
  } else {
    const rows = sorted.map(t =>
      '<tr>' +
        '<td><strong style="color:var(--text)">' + escHtml(t.nom) + '</strong></td>' +
        '<td class="col-comment">' + escHtml(t.detail || '') + '</td>' +
        '<td class="col-actions">' +
          '<button type="button" class="ops-row-btn edit" onclick="editCtrlType(\'' + escAttr(t.id) + '\')" title="Modifier">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
          '</button>' +
          '<button type="button" class="ops-row-btn del" onclick="deleteCtrlType(\'' + escAttr(t.id) + '\')" title="Supprimer">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          '</button>' +
        '</td>' +
      '</tr>'
    );
    tbody.innerHTML = rows.join('');
  }
  if(count){
    const n = CTRL_TYPES_STATE.list.length;
    count.textContent = n + ' contrôle' + (n > 1 ? 's' : '');
  }
}

function toggleTheme(){
  const l=document.body.classList.toggle('light');
  document.documentElement.classList.toggle('light-pre', l);
  try{localStorage.setItem('mysifa_theme',l?'light':'dark');}catch(e){}
  updateThemeBtn();
}
function updateThemeBtn(){
  const l=document.body.classList.contains('light');
  const ico=document.getElementById('theme-ico');
  const lbl=document.getElementById('theme-label');
  if(ico){
    ico.innerHTML=l
      ?'<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
      :'<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
  }
  if(lbl) lbl.textContent=l?'Mode clair':'Mode sombre';
}

async function doLogout(){
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
}

async function loadMe(){
  try{
    const r=await fetch('/api/auth/me',{credentials:'include'});
    if(!r.ok) return;
    const d=await r.json();
    S.me=d&&d.user?d.user:d;
    const chip=document.getElementById('user-chip');
    if(chip&&S.me){
      const roles={direction:'Direction',administration:'Administration',superadmin:'Super admin',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial'};
      chip.innerHTML='<div class="uc-name">'+escHtml(S.me.nom||'')+'</div><div class="uc-role">'+escHtml(roles[S.me.role]||S.me.role||'')+'</div>';
    }
  }catch(e){}
}

(function init(){
  try{
    const t=localStorage.getItem('mysifa_theme');
    if(t==='light') document.body.classList.add('light');
    else document.body.classList.remove('light');
    updateThemeBtn();
  }catch(e){}
  loadMe();
  loadOps();
  loadOpsTypes();
  loadCtrl();
  loadCtrlTypes();
  renderOpsTypes();
  renderOps();
  renderCtrlTypes();
  renderCtrl();
  try{
    const h = (location.hash || '').replace('#','').trim();
    const target = (h === 'historique') ? 'controles' : h;
    if(target && VIEW_META[target]) switchView(target);
  }catch(e){}
})();
</script>
<script>window.__MYSIFA_APP__='maintenance';</script>
<script src="/static/mysifa_dock.js"></script>
<script>
if(typeof window.MySifaDock !== 'undefined' && typeof window.MySifaDock.bootPageWidgets === 'function'){
  window.MySifaDock.bootPageWidgets();
}
</script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=5"></script>
<script src="/static/chat_widget_v2.js"></script>
<script src="/static/support_widget.js"></script>
</body>
</html>"""
