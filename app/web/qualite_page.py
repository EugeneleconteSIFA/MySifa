"""MySifa — Page Qualité (Non-conformités)
Route : /qualite
Accès : superadmin, direction, administration
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user
from app.web.access_denied import access_denied_response
from config import APP_VERSION

ROLES_QUALITE = {"superadmin", "direction", "administration"}
ROLES_QUALITE_READONLY = {"commercial"}

router = APIRouter()


@router.get("/qualite", response_class=HTMLResponse)
def qualite_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/qualite", status_code=302)
        raise
    # Acces module Qualite :
    # - Roles ROLES_QUALITE (superadmin/direction/administration) : acces complet
    #   (NC, Canaux NC, Audits client, Referentiel RSE).
    # - Roles ROLES_QUALITE_READONLY (commercial) : lecture seule NC/Canaux/Audits,
    #   pas d'ecriture. Les boutons sont masques via IS_QUALITE_READONLY cote JS.
    # - Autres roles connectes : acces limite au Referentiel en lecture/proposition.
    #   Les tabs NC / Canaux / Audits sont masques via le flag IS_QUALITE_ADMIN cote JS.
    is_admin = user["role"] in ROLES_QUALITE
    is_readonly = user["role"] in ROLES_QUALITE_READONLY
    html = (
        QUALITE_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__IS_QUALITE_ADMIN__", "true" if is_admin else "false")
        .replace("__IS_QUALITE_READONLY__", "true" if is_readonly else "false")
    )
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


QUALITE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Qualité — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.10);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;--success:#34d399;
  --btn-fg:#0a0e17;
  --sidebar-w:220px;
}
html.light-pre body,body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.08);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
  --btn-fg:#ffffff;
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}
::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* ── Layout ── */
.app{display:flex;height:100vh;overflow:hidden}
.sidebar{width:var(--sidebar-w);background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}.sidebar{scrollbar-width:none}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:768px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:9000;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .sidebar-overlay{z-index:8999}
  body.sb-open .sidebar-overlay{display:block}
  .main{height:100vh;overflow-y:auto}
}
.main{flex:1;overflow-y:auto;display:flex;flex-direction:column;position:relative}

/* ── Sidebar elements ── */
.logo{padding:0 8px;margin-bottom:28px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px;position:relative}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-badge{margin-left:auto;background:var(--accent);color:var(--btn-fg);font-size:10px;font-weight:800;border-radius:999px;padding:1px 7px;min-width:18px;text-align:center}
.nav-btn.active .nav-badge{background:var(--accent);color:var(--btn-fg)}
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
.theme-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit;transition:.15s;width:100%}
.theme-btn:hover{border-color:var(--accent);color:var(--accent)}
.logout-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px;font-family:inherit;transition:.15s;width:100%}
.logout-btn:hover{border-color:var(--danger);color:var(--danger)}
.version{font-size:10px;color:var(--muted);padding:4px 12px;font-family:ui-monospace,monospace;opacity:.6}

/* ── Mobile topbar ── */
.mobile-topbar{display:none;align-items:center;gap:12px;padding:14px 16px;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
@media(max-width:768px){.mobile-topbar{display:flex}}
.mobile-menu-btn{background:none;border:none;color:var(--text2);cursor:pointer;padding:4px;border-radius:6px;display:flex;align-items:center;justify-content:center}
.mobile-topbar-title{font-size:14px;font-weight:700;color:var(--text)}
.mobile-topbar-sub{font-size:11px;color:var(--muted)}
.mobile-home-btn{margin-left:auto;background:none;border:none;color:var(--muted);cursor:pointer;font-size:20px;padding:4px;border-radius:6px;transition:.15s}
.mobile-home-btn:hover{color:var(--accent)}

/* ── Content ── */
.content{padding:28px 32px;max-width:1280px;width:100%}
@media(max-width:768px){.content{padding:16px}}

/* ── Page header ── */
.page-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:22px;flex-wrap:wrap}
.page-title{font-size:22px;font-weight:800;letter-spacing:-.5px}
.page-title span{color:var(--accent)}
.page-subtitle{font-size:13px;color:var(--muted);margin-top:3px}
.header-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}

/* ── Boutons ── */
.btn{display:inline-flex;align-items:center;gap:7px;padding:10px 18px;border-radius:10px;border:none;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.btn:hover{filter:brightness(1.08)}
.btn-accent{background:var(--accent);color:var(--btn-fg)}
.btn-danger{background:var(--danger);color:#fff}
.btn-ok{background:var(--ok);color:var(--btn-fg)}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-sm{padding:6px 13px;font-size:12px;border-radius:8px}

/* ── Toolbar + filtres ── */
.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:18px;flex-wrap:wrap}
.search-wrap{position:relative;flex:1;min-width:220px}
.search-input{width:100%;padding:10px 14px 10px 38px;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.search-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.10)}
.search-ico{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
.filter-select{padding:9px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:12px;font-family:inherit;cursor:pointer;outline:none}
.filter-select:focus{border-color:var(--accent)}

/* ── Status tabs ── */
.stat-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px}
.stat-tab{padding:7px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s;display:inline-flex;align-items:center;gap:6px}
.stat-tab:hover{border-color:var(--accent);color:var(--accent)}
.stat-tab.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.stat-count{background:var(--border);color:var(--muted);border-radius:999px;padding:1px 7px;font-size:11px;font-weight:700}
.stat-tab.active .stat-count{background:var(--accent);color:var(--btn-fg)}

/* ── Table ── */
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.table-wrap table{width:100%;border-collapse:collapse}
.table-wrap th{padding:11px 16px;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap}
.table-wrap td{padding:12px 16px;font-size:13px;border-bottom:1px solid var(--border);vertical-align:middle}
.table-wrap tr:last-child td{border-bottom:none}
.table-wrap tbody tr{cursor:pointer;transition:background .12s}
.table-wrap tbody tr:hover td{background:rgba(255,255,255,.02)}
body.light .table-wrap tbody tr:hover td{background:rgba(0,0,0,.02)}

/* ── Badges ── */
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.2px;white-space:nowrap}
.badge-stat-ouverte{background:rgba(251,191,36,.14);color:var(--warn)}
.badge-stat-en_analyse{background:rgba(34,211,238,.12);color:var(--accent)}
.badge-stat-action_corrective{background:rgba(167,139,250,.14);color:#a78bfa}
.badge-stat-en_verification{background:rgba(96,165,250,.14);color:#60a5fa}
.badge-stat-cloturee{background:rgba(52,211,153,.14);color:var(--ok)}
.badge-grav-mineure{background:rgba(148,163,184,.18);color:var(--text2)}
.badge-grav-majeure{background:rgba(251,191,36,.16);color:var(--warn)}
.badge-grav-critique{background:rgba(248,113,113,.18);color:var(--danger)}
.badge-type{background:var(--accent-bg);color:var(--accent);font-weight:600}
.unread-dot{display:inline-block;width:8px;height:8px;border-radius:999px;background:var(--accent);margin-right:6px;vertical-align:middle;box-shadow:0 0 0 2px rgba(34,211,238,.25)}
.unread-pill{display:inline-flex;align-items:center;justify-content:center;background:var(--accent);color:var(--btn-fg);font-size:10px;font-weight:800;border-radius:999px;padding:1px 7px;min-width:18px;margin-left:6px}

/* ── Empty state ── */
.empty{text-align:center;padding:60px 20px;color:var(--muted)}
.empty-icon{font-size:40px;margin-bottom:12px;opacity:.5}
.empty-title{font-size:15px;font-weight:600;color:var(--text2);margin-bottom:6px}
.empty-sub{font-size:12px}

/* ── Détail NC ── */
.detail-header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:18px;flex-wrap:wrap}
.detail-back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);background:transparent;border:none;cursor:pointer;font-size:13px;font-family:inherit;padding:6px 0;margin-bottom:8px;transition:color .15s}
.detail-back:hover{color:var(--accent)}
.detail-title{font-size:20px;font-weight:800;color:var(--text);margin-bottom:4px}
.detail-num{font-family:ui-monospace,monospace;font-size:13px;color:var(--accent);margin-right:10px;font-weight:700}
.detail-meta{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:6px}
.detail-actions{display:flex;gap:8px;flex-wrap:wrap}

.detail-tabs{display:flex;gap:4px;border-bottom:1px solid var(--border);margin-bottom:18px;flex-wrap:wrap}
.detail-tab{padding:10px 16px;background:transparent;border:none;color:var(--text2);font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;border-bottom:2px solid transparent;margin-bottom:-1px;display:inline-flex;align-items:center;gap:8px;transition:.15s}
.detail-tab:hover{color:var(--accent)}
.detail-tab.active{color:var(--accent);border-bottom-color:var(--accent)}

/* ── Fiche technique form ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;margin-bottom:16px}
.card-title{font-size:13px;font-weight:700;color:var(--text);margin-bottom:14px;text-transform:uppercase;letter-spacing:.5px}
.form-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px 16px}
.form-grid.cols-3{grid-template-columns:repeat(3,1fr)}
.form-grid.cols-1{grid-template-columns:1fr}
.form-grid .col-2{grid-column:span 2}
.form-grid .col-3{grid-column:1 / -1}
@media(max-width:780px){.form-grid,.form-grid.cols-3{grid-template-columns:1fr}.form-grid .col-2{grid-column:auto}}

.form-label{display:block;font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.form-input,.form-select,.form-textarea{width:100%;padding:10px 12px;background:var(--bg);border:1.5px solid var(--border);border-radius:9px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.form-input:focus,.form-select:focus,.form-textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.10)}
.form-textarea{resize:vertical;min-height:80px;line-height:1.5}
.form-input[readonly]{background:transparent;cursor:default;color:var(--muted)}
/* Rôle « commercial » : lecture seule sur NC/Canaux/Audits — on masque tout ce qui écrit,
   on rend les champs de saisie non modifiables (curseur classique, pas de focus visuel). */
body.qualite-readonly .qual-write{display:none !important}
body.qualite-readonly .form-input,
body.qualite-readonly .form-select,
body.qualite-readonly .form-textarea{background:transparent;color:var(--text2);cursor:default;pointer-events:none;border-color:var(--border)}
body.qualite-readonly .chip{cursor:default;pointer-events:none;opacity:.85}
body.qualite-readonly .badge-clickable{cursor:default}
body.qualite-readonly .aud-aud-chip .x{display:none}
.form-hint{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.4}
.chips-row{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;background:var(--bg);border:1px solid var(--border);border-radius:999px;font-size:12px;color:var(--text2);cursor:pointer;transition:.15s;font-family:inherit}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent);font-weight:600}

/* ── Validations ── */
.valid-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:680px){.valid-grid{grid-template-columns:1fr}}
.valid-box{padding:14px;border:1px dashed var(--border);border-radius:10px;background:var(--bg)}
.valid-box.signed{border-style:solid;border-color:var(--ok);background:rgba(52,211,153,.06)}
.valid-box-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:8px}
.valid-box-name{font-size:14px;font-weight:700;color:var(--text)}
.valid-box-date{font-size:11px;color:var(--muted);margin-top:3px}
.valid-box-actions{margin-top:10px;display:flex;gap:6px}

/* ── Fichiers ── */
.file-row{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid var(--border);border-radius:10px;margin-bottom:8px;background:var(--bg)}
.file-icon{width:36px;height:36px;border-radius:8px;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.file-name{font-weight:600;color:var(--text);font-size:13px;word-break:break-all}
.file-meta{font-size:11px;color:var(--muted);margin-top:2px}
.file-actions{margin-left:auto;display:flex;gap:6px}
.upload-zone{border:2px dashed var(--border);border-radius:12px;padding:24px 20px;text-align:center;cursor:pointer;transition:.15s;color:var(--muted);background:var(--bg);display:block}
.upload-zone:hover,.upload-zone.drag{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.upload-zone input{display:none}
.upload-zone svg{flex-shrink:0;width:34px !important;height:34px !important;max-width:34px;max-height:34px}

/* ── Discussion ── */
.msg-list{display:flex;flex-direction:column;gap:14px;max-height:60vh;overflow-y:auto;padding:4px 4px 12px}
.msg{display:flex;gap:10px;align-items:flex-start}
.msg-avatar{width:34px;height:34px;border-radius:999px;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;text-transform:uppercase}
.msg-body{flex:1;min-width:0}
.msg-head{display:flex;align-items:baseline;gap:8px;margin-bottom:3px;flex-wrap:wrap}
.msg-author{font-weight:700;color:var(--text);font-size:13px}
.msg-role{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
.msg-time{font-size:11px;color:var(--muted)}
.msg-text{font-size:13px;line-height:1.55;color:var(--text2);white-space:pre-wrap;word-wrap:break-word}
.msg-attach{margin-top:6px;display:inline-flex;align-items:center;gap:6px;padding:6px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--text2);text-decoration:none;transition:.15s}
.msg-attach:hover{border-color:var(--accent);color:var(--accent)}
.msg-input-wrap{display:flex;gap:8px;align-items:flex-end;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}
.msg-input{flex:1;padding:10px 12px;background:var(--bg);border:1.5px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit;resize:vertical;min-height:42px;max-height:160px;outline:none}
.msg-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.10)}

/* ── Canaux panel ── */
.canaux-fab{position:fixed;bottom:24px;right:24px;width:54px;height:54px;border-radius:999px;background:var(--accent);color:var(--btn-fg);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 28px rgba(34,211,238,.35);z-index:300;transition:transform .15s}
.canaux-fab:hover{transform:scale(1.06)}
.canaux-fab .fab-badge{position:absolute;top:-4px;right:-4px;background:var(--danger);color:#fff;font-size:10px;font-weight:800;border-radius:999px;padding:2px 6px;min-width:18px;text-align:center}
.canaux-panel{position:fixed;top:0;right:0;bottom:0;width:360px;max-width:92vw;background:var(--card);border-left:1px solid var(--border);z-index:9500;transform:translateX(105%);transition:transform .2s ease;display:flex;flex-direction:column;box-shadow:-12px 0 32px rgba(0,0,0,.3)}
.canaux-panel.open{transform:translateX(0)}
.canaux-head{padding:18px 18px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.canaux-title{font-size:15px;font-weight:800;color:var(--text)}
.canaux-title span{color:var(--accent)}
.canaux-sub{font-size:11px;color:var(--muted);margin-top:2px}
.canaux-close{background:transparent;border:none;color:var(--muted);cursor:pointer;padding:6px;border-radius:6px;font-size:20px;line-height:1;transition:.15s}
.canaux-close:hover{color:var(--danger)}
.canaux-list{flex:1;overflow-y:auto;padding:10px}
.canal-item{padding:12px 12px;border-radius:10px;cursor:pointer;transition:.12s;border:1px solid transparent;margin-bottom:4px}
.canal-item:hover{background:var(--accent-bg);border-color:var(--accent)}
.canal-item.unread{background:var(--accent-bg)}
.canal-num{font-family:ui-monospace,monospace;font-size:11px;color:var(--accent);font-weight:700}
.canal-titre{font-size:13px;font-weight:600;color:var(--text);margin-top:2px;display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.canal-time{font-size:10px;color:var(--muted);margin-top:4px;display:flex;justify-content:space-between}

/* ── Modal ── */
.modal-ov{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:26px 26px 22px;width:100%;max-width:520px;position:relative;max-height:92vh;overflow-y:auto;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.modal.lg{max-width:720px}
.modal-close{position:absolute;top:14px;right:14px;background:none;border:none;color:var(--muted);cursor:pointer;font-size:22px;line-height:1;padding:4px;border-radius:6px;transition:.15s}
.modal-close:hover{color:var(--danger)}
.modal-title{font-size:16px;font-weight:800;margin-bottom:18px}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px;flex-wrap:wrap}

/* ── Picker dossier ── */
.picker-list{max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:10px}
.picker-item{padding:10px 12px;border-bottom:1px solid var(--border);cursor:pointer;transition:.12s}
.picker-item:last-child{border-bottom:none}
.picker-item:hover{background:var(--accent-bg);color:var(--accent)}
.picker-item-ref{font-family:ui-monospace,monospace;font-size:12px;font-weight:700;color:var(--accent)}
.picker-item-meta{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Toast ── */
.toast-wrap{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;gap:8px;z-index:9999;align-items:center}
.toast{padding:11px 18px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 4px 24px rgba(0,0,0,.4);max-width:90vw;animation:toastIn .2s ease}
@keyframes toastIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.toast.success{background:#064e3b;color:var(--ok);border:1px solid var(--ok)}
.toast.danger{background:#450a0a;color:var(--danger);border:1px solid var(--danger)}
.toast.info{background:var(--card);color:var(--text2);border:1px solid var(--border)}
body.light .toast.success{background:#d1fae5;color:#065f46}
body.light .toast.danger{background:#fee2e2;color:#991b1b}
body.light .toast.info{background:#f1f5f9;color:var(--text)}

.spin{display:inline-block;width:14px;height:14px;border:2px solid var(--muted);border-top-color:var(--accent);border-radius:999px;animation:sp 0.8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="app">
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>

  <nav class="sidebar" id="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Qualité</span></div>
      <div class="logo-sub">by SIFA</div>
    </div>
    <button type="button" class="nav-btn active" id="nav-nc" onclick="setView('list')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 12l2 2 4-4"/><path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z"/></svg>
      Non-conformités
      <span class="nav-badge" id="sb-unread" style="display:none">0</span>
    </button>
    <button type="button" class="nav-btn" id="nav-canaux" onclick="toggleCanaux()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
      Canaux NC
      <span class="nav-badge" id="sb-unread2" style="display:none">0</span>
    </button>
    <button type="button" class="nav-btn" id="nav-audits" onclick="setView('audits-list')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>
      Audits client
      <span class="nav-badge" id="sb-audits" style="display:none">0</span>
    </button>
    <button type="button" class="nav-btn" id="nav-ref" onclick="setView('ref-list')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
      Référentiel RSE
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
        <div class="mobile-topbar-title">Qualité</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Non-conformités</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'">⌂</button>
    </div>

    <div class="content" id="content"></div>
  </main>
</div>

<!-- Panneau Canaux -->
<div class="canaux-panel" id="canaux-panel">
  <div class="canaux-head">
    <div>
      <div class="canaux-title">My<span>Qualité</span> · Canaux</div>
      <div class="canaux-sub">NC ouvertes avec discussion</div>
    </div>
    <button class="canaux-close" onclick="closeCanaux()">×</button>
  </div>
  <div class="canaux-list" id="canaux-list"></div>
</div>

<button class="canaux-fab" onclick="toggleCanaux()" title="Canaux NC">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
  <span class="fab-badge" id="fab-badge" style="display:none">0</span>
</button>

<!-- Modal création NC -->
<div class="modal-ov" id="create-modal" style="display:none" onclick="if(event.target===this)closeCreateModal()">
  <div class="modal lg" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeCreateModal()">×</button>
    <div class="modal-title">Nouvelle non-conformité</div>
    <div class="form-grid">
      <div>
        <label class="form-label" for="c-titre">Titre court</label>
        <input type="text" class="form-input" id="c-titre" placeholder="ex : Étiquettes décollées sur cartons">
      </div>
      <div>
        <label class="form-label" for="c-ar">N° de commande (AR) — optionnel</label>
        <input type="text" class="form-input" id="c-ar" placeholder="ex : 9930854">
        <div class="form-hint">Si vide, un numéro NC-{ANNÉE}-{n°} sera attribué automatiquement.</div>
      </div>
      <div>
        <label class="form-label">Type de NC</label>
        <select class="form-select" id="c-type">
          <option value="interne">Interne (production)</option>
          <option value="client">Client (réclamation)</option>
          <option value="fournisseur">Fournisseur</option>
          <option value="logistique">Logistique / expédition</option>
        </select>
      </div>
      <div>
        <label class="form-label">Gravité</label>
        <select class="form-select" id="c-gravite">
          <option value="mineure">Mineure</option>
          <option value="majeure">Majeure</option>
          <option value="critique">Critique</option>
        </select>
      </div>
      <div>
        <label class="form-label" for="c-date">Date de la NC</label>
        <input type="date" class="form-input" id="c-date">
      </div>
      <div>
        <label class="form-label" for="c-service">Service concerné</label>
        <input type="text" class="form-input" id="c-service" placeholder="ex : Production, ADV…">
      </div>
      <div class="col-2">
        <label class="form-label" for="c-client">Nom client / fournisseur</label>
        <input type="text" class="form-input" id="c-client" placeholder="ex : VOLAILLES REMI RAMON">
      </div>
      <div>
        <label class="form-label" for="c-refclient">Référence client</label>
        <input type="text" class="form-input" id="c-refclient">
      </div>
      <div>
        <label class="form-label" for="c-dossier">Référence SIFA (dossier)</label>
        <div style="display:flex;gap:6px">
          <input type="text" class="form-input" id="c-dossier" placeholder="ex : 1153/0030">
          <button type="button" class="btn btn-ghost btn-sm" onclick="openDossierPicker('c-dossier')">Rechercher</button>
        </div>
      </div>
      <div class="col-2">
        <label class="form-label" for="c-desc">Description</label>
        <textarea class="form-textarea" id="c-desc" rows="3" placeholder="Description détaillée de la non-conformité…"></textarea>
      </div>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeCreateModal()">Annuler</button>
      <button type="button" class="btn btn-accent" id="create-btn" onclick="submitCreate()">Créer la NC</button>
    </div>
  </div>
</div>

<!-- Modal import xlsx -->
<div class="modal-ov" id="import-modal" style="display:none" onclick="if(event.target===this)closeImportModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeImportModal()">×</button>
    <div class="modal-title">Importer une NC depuis xlsx</div>
    <p style="font-size:12px;color:var(--text2);line-height:1.55;margin-bottom:14px">
      Déposez une fiche au format SIFA (modèle « Fiche NON CONFORMITE »). Les champs détectés (n° AR, n° historique, date, client, dossier, descriptif, quantité, services impliqués, analyse, actions, pilote…) seront pré-remplis. Le fichier original sera attaché en pièce jointe.
    </p>
    <label class="upload-zone" id="import-zone" ondragover="onImportDragOver(event)" ondragleave="onImportDragLeave(event)" ondrop="onImportDrop(event)">
      <div style="display:flex;justify-content:center;margin-bottom:10px">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:block">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <div id="import-zone-label" style="font-size:13px">Glisser-déposer le fichier xlsx, ou cliquer pour choisir</div>
      <div style="font-size:11px;margin-top:4px;opacity:.7">Format .xlsx ou .xlsm</div>
      <input type="file" id="import-file" accept=".xlsx,.xlsm" onchange="onImportFile(event)">
    </label>
    <div id="import-progress" style="font-size:12px;color:var(--accent);margin-top:10px;display:none">
      <span class="spin"></span> Import en cours…
    </div>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeImportModal()">Annuler</button>
    </div>
  </div>
</div>

<!-- Modal picker dossier -->
<div class="modal-ov" id="dp-modal" style="display:none" onclick="if(event.target===this)closeDossierPicker()">
  <div class="modal" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeDossierPicker()">×</button>
    <div class="modal-title">Rechercher un dossier</div>
    <input type="text" class="form-input" id="dp-search" placeholder="Recherche (n° dossier, client, désignation…)" oninput="searchDossiers(this.value)" style="margin-bottom:12px">
    <div class="picker-list" id="dp-list"></div>
  </div>
</div>

<!-- Modal suppression -->
<div class="modal-ov" id="del-modal" style="display:none" onclick="if(event.target===this)closeDelModal()">
  <div class="modal" onclick="event.stopPropagation()" style="max-width:420px">
    <button type="button" class="modal-close" onclick="closeDelModal()">×</button>
    <div class="modal-title">Supprimer cette NC ?</div>
    <p style="font-size:13px;color:var(--text2);line-height:1.6" id="del-msg"></p>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeDelModal()">Annuler</button>
      <button type="button" class="btn btn-danger" onclick="confirmDelete()">Supprimer</button>
    </div>
  </div>
</div>

<div class="toast-wrap" id="toast-wrap"></div>

<script>
'use strict';

// ── État central ───────────────────────────────────────────────────
const S = {
  view: 'list',          // 'list' | 'detail' | 'audits-list' | 'audits-detail'
  detailTab: 'fiche',    // 'fiche' | 'fichiers' | 'discussion'
  ncs: [],
  current: null,         // NC complet quand en détail
  currentFiles: [],
  currentMessages: [],
  canaux: [],
  unread: 0,
  filterStatut: 'all',
  filterType: 'all',
  filterGravite: 'all',
  search: '',
  me: null,
  users: [],
  dpTarget: null,
  dpResults: [],
  delId: null,
  pendingSaveTimer: null,
  // ── Audits client ─────────────────────────────────────────────
  audits: [],
  currentAudit: null,
  currentAuditFiles: [],
  currentAuditFolders: [],
  currentAuditMessages: [],
  currentFolderId: null,        // null = racine ; sinon id du sous-dossier visité
  auditFilterStatut: 'all',     // 'all' | 'ouvert' | 'cloture'
  auditSearch: '',
  auditDetailTab: 'fichiers',   // 'fichiers' | 'fiche' | 'discussion'
  auditeursCandidats: [],
  clientsResults: [],
  audUnread: 0,
  // ── Référentiel RSE ───────────────────────────────────────────
  refMeta: null,             // {categories, statuts_sifa, statuts_validation}
  refFiches: [],
  currentRef: null,
  refSearch: '',
  refFilterCat: 'all',       // 'all' | 'environnement' | 'social' | 'tracabilite' | 'securite'
  refFilterStatV: 'all',     // 'all' | 'brouillon' | 'en_revue' | 'valide'
  refFilterStatS: 'all',     // 'all' | 'conforme' | 'partiel' | 'en_cours' | 'non_applicable' | 'a_evaluer'
  refValideOnly: false,      // filtre "valides uniquement"
  refEdit: false,            // mode édition dans la vue détail
  refEditBuf: null,          // buffer d'édition
  refSuggests: null,         // {questions:[], fiches:[]}
  refSuggestIx: -1,          // index sélectionné dans le dropdown
  refAuditsPicker: [],       // audits pour le picker de lien
  refOpenQaId: null,         // ID de la question ouverte dans l'accordéon
  refEditQaId: null,         // ID de la question en cours d'édition inline
  isQualiteAdmin: __IS_QUALITE_ADMIN__,
  isQualiteReadonly: __IS_QUALITE_READONLY__,
};

const STATUTS = [
  {k:'ouverte',label:'Ouverte'},
  {k:'en_analyse',label:'En analyse'},
  {k:'action_corrective',label:'Action corrective'},
  {k:'en_verification',label:'En vérification'},
  {k:'cloturee',label:'Clôturée'},
];
const TYPES = [
  {k:'interne',label:'Interne'},
  {k:'client',label:'Client'},
  {k:'fournisseur',label:'Fournisseur'},
  {k:'logistique',label:'Logistique'},
];
const GRAVITES = [
  {k:'mineure',label:'Mineure'},
  {k:'majeure',label:'Majeure'},
  {k:'critique',label:'Critique'},
];
const SERVICES_5M = ['ADV','Mécanique','Qualité','Production','Logistique','Autre'];

// ── Utilitaires ───────────────────────────────────────────────────
function escHtml(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function escAttr(s){return escHtml(s);}

async function api(path, opts={}){
  const r=await fetch(path,{credentials:'include',...opts});
  if(r.status===401){location.href='/?next=/qualite';throw new Error('unauth');}
  return r;
}
function showToast(msg, type='info'){
  const wrap=document.getElementById('toast-wrap');
  const el=document.createElement('div');
  el.className=`toast ${type}`;
  el.textContent=msg;
  wrap.appendChild(el);
  setTimeout(()=>el.remove(),3200);
}
function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}
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
function fmtDate(s){
  if(!s) return '—';
  const m=String(s).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(m) return `${m[3]}/${m[2]}/${m[1]}`;
  return s.slice(0,10);
}
function fmtDateTime(s){
  if(!s) return '—';
  const m=String(s).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if(m) return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`;
  return s.slice(0,16).replace('T',' ');
}
function relTime(s){
  if(!s) return '';
  const d=new Date(s.replace(' ','T'));
  if(isNaN(d.getTime())) return s.slice(0,16);
  const diff=(Date.now()-d.getTime())/1000;
  if(diff<60) return 'à l\'instant';
  if(diff<3600) return `il y a ${Math.floor(diff/60)} min`;
  if(diff<86400) return `il y a ${Math.floor(diff/3600)} h`;
  if(diff<604800) return `il y a ${Math.floor(diff/86400)} j`;
  return fmtDateTime(s);
}
function initials(name){
  if(!name) return '?';
  return name.trim().split(/\s+/).slice(0,2).map(p=>p[0]).join('').toUpperCase();
}
function statutLabel(k){const it=STATUTS.find(x=>x.k===k);return it?it.label:k;}
function typeLabel(k){const it=TYPES.find(x=>x.k===k);return it?it.label:k;}
function gravLabel(k){const it=GRAVITES.find(x=>x.k===k);return it?it.label:k;}
function statutBadge(k){return `<span class="badge badge-stat-${escAttr(k)}">${escHtml(statutLabel(k))}</span>`;}
function gravBadge(k){return `<span class="badge badge-grav-${escAttr(k)}">${escHtml(gravLabel(k))}</span>`;}
function typeBadge(k){return `<span class="badge badge-type">${escHtml(typeLabel(k))}</span>`;}

// ── Chargement initial ─────────────────────────────────────────────
async function loadMe(){
  try{
    const r=await fetch('/api/auth/me',{credentials:'include'});
    if(!r.ok) return;
    const d=await r.json();
    S.me=d.user||d;
    const chip=document.getElementById('user-chip');
    if(chip&&S.me){
      const roles={direction:'Direction',administration:'Administration',superadmin:'Super admin',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial'};
      chip.innerHTML=`<div class="uc-name">${escHtml(S.me.nom||'')}</div><div class="uc-role">${escHtml(roles[S.me.role]||S.me.role||'')}</div>`;
    }
  }catch(e){}
}
async function loadUsers(){
  try{
    const r=await api('/api/qualite/users');
    if(r.ok) S.users=await r.json();
  }catch(e){}
}
async function loadNCs(){
  try{
    const r=await api('/api/qualite/nc');
    if(!r.ok){showToast('Erreur de chargement','danger');return;}
    S.ncs=await r.json();
    if(S.view==='list') renderList();
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}
async function loadCanaux(){
  try{
    const r=await api('/api/qualite/canaux');
    if(r.ok){S.canaux=await r.json();renderCanaux();}
  }catch(e){}
}
async function loadUnread(){
  // Compteur agrege Qualite : NC unread + audits unread (+ affectations)
  try{
    const r=await api('/api/qualite/badges');
    if(r.ok){
      const d=await r.json();
      S.unread=d.nc_unread||0;
      S.audUnread=(d.audits_unread||0)+(d.audits_assigned_open||0);
      updateUnreadBadges();
    }
  }catch(e){}
}
function updateUnreadBadges(){
  const ncEls=['sb-unread','sb-unread2','fab-badge'].map(id=>document.getElementById(id));
  ncEls.forEach(el=>{
    if(!el)return;
    if(S.unread>0){el.style.display='inline-block';el.textContent=S.unread>99?'99+':String(S.unread);}
    else el.style.display='none';
  });
  const audEl=document.getElementById('sb-audits');
  if(audEl){
    if(S.audUnread>0){audEl.style.display='inline-block';audEl.textContent=S.audUnread>99?'99+':String(S.audUnread);}
    else audEl.style.display='none';
  }
}

// ── Vue Liste ──────────────────────────────────────────────────────
function setView(v){
  S.view=v;
  document.querySelectorAll('.sidebar .nav-btn').forEach(b=>b.classList.remove('active'));
  if(v==='list'){
    const first=document.querySelector('.sidebar .nav-btn');
    if(first) first.classList.add('active');
    document.getElementById('mobile-sub').textContent='Non-conformités';
    renderList();
  } else if(v==='detail'){
    document.getElementById('mobile-sub').textContent=S.current?S.current.numero:'Détail';
    renderDetail();
  } else if(v==='audits-list'){
    const navAud=document.getElementById('nav-audits'); if(navAud) navAud.classList.add('active');
    document.getElementById('mobile-sub').textContent='Audits client';
    if(typeof loadAudits==='function') loadAudits();
    else renderAuditsList();
  } else if(v==='audits-detail'){
    const navAud=document.getElementById('nav-audits'); if(navAud) navAud.classList.add('active');
    document.getElementById('mobile-sub').textContent=S.currentAudit?S.currentAudit.numero:'Audit';
    renderAuditDetail();
  } else if(v==='ref-list'){
    const nav=document.getElementById('nav-ref'); if(nav) nav.classList.add('active');
    document.getElementById('mobile-sub').textContent='Référentiel RSE';
    if(typeof loadRefFiches==='function') loadRefFiches();
    else renderRefList();
  } else if(v==='ref-detail'){
    const nav=document.getElementById('nav-ref'); if(nav) nav.classList.add('active');
    document.getElementById('mobile-sub').textContent=S.currentRef?S.currentRef.nom:'Fiche';
    renderRefDetail();
  }
  closeSidebar();
}

function filteredNCs(){
  let list=S.ncs;
  if(S.filterStatut!=='all') list=list.filter(n=>n.statut===S.filterStatut);
  if(S.filterType!=='all') list=list.filter(n=>n.type_nc===S.filterType);
  if(S.filterGravite!=='all') list=list.filter(n=>n.gravite===S.filterGravite);
  if(S.search.trim()){
    const q=S.search.trim().toLowerCase();
    list=list.filter(n=>(
      (n.numero||'').toLowerCase().includes(q)||
      (n.titre||'').toLowerCase().includes(q)||
      (n.numero_ar||'').toLowerCase().includes(q)||
      (n.numero_historique||'').toLowerCase().includes(q)||
      (n.client_fournisseur||'').toLowerCase().includes(q)||
      (n.no_dossier||'').toLowerCase().includes(q)||
      (n.description||'').toLowerCase().includes(q)
    ));
  }
  return list;
}

function renderList(){
  const ae=document.activeElement;const fid=ae?.id;const cs=ae?.selectionStart;const ce=ae?.selectionEnd;
  const counts={all:S.ncs.length};
  STATUTS.forEach(s=>{counts[s.k]=S.ncs.filter(n=>n.statut===s.k).length;});
  const list=filteredNCs();

  const tabsHtml=`
    <button type="button" class="stat-tab${S.filterStatut==='all'?' active':''}" onclick="setStatutFilter('all')">Tous<span class="stat-count">${counts.all}</span></button>
    ${STATUTS.map(s=>`<button type="button" class="stat-tab${S.filterStatut===s.k?' active':''}" onclick="setStatutFilter('${s.k}')">${escHtml(s.label)}<span class="stat-count">${counts[s.k]||0}</span></button>`).join('')}
  `;

  let body;
  if(!list.length){
    body=`<div class="empty">
      <div class="empty-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg></div>
      <div class="empty-title">${S.search?'Aucun résultat pour « '+escHtml(S.search)+' »':'Aucune non-conformité'}</div>
      <div class="empty-sub">${(!S.search&&S.filterStatut==='all'&&S.filterType==='all'&&S.filterGravite==='all')?'Créez la première NC avec le bouton ci-dessus.':''}</div>
    </div>`;
  } else {
    const rows=list.map(n=>{
      const unreadBadge=n.unread_count>0?`<span class="unread-pill">${n.unread_count}</span>`:'';
      const dot=n.unread_count>0?'<span class="unread-dot"></span>':'';
      const ref=[n.numero_ar?'AR '+n.numero_ar:'',n.numero_historique?'N° '+n.numero_historique:''].filter(Boolean).join(' · ');
      return `<tr onclick="openDetail(${n.id})">
        <td><div style="font-family:ui-monospace,monospace;font-weight:700;color:var(--accent);font-size:12px">${dot}${escHtml(n.numero||'')}</div>${ref?`<div style="font-size:10px;color:var(--muted);margin-top:2px">${escHtml(ref)}</div>`:''}</td>
        <td><div style="font-weight:600;color:var(--text);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escAttr(n.titre||'')}">${escHtml(n.titre||'—')}</div>${n.client_fournisseur?`<div style="font-size:11px;color:var(--muted);margin-top:2px">${escHtml(n.client_fournisseur)}</div>`:''}</td>
        <td>${typeBadge(n.type_nc)}</td>
        <td>${gravBadge(n.gravite)}</td>
        <td>${statutBadge(n.statut)}</td>
        <td><span style="color:var(--text2);font-size:12px">${escHtml(n.pilote_nom||'—')}</span></td>
        <td><span style="font-family:ui-monospace,monospace;font-size:12px;color:var(--text2)">${escHtml(fmtDate(n.date_nc))}</span></td>
        <td style="color:var(--muted);font-size:11px;white-space:nowrap">${escHtml(relTime(n.updated_at))}${unreadBadge}</td>
      </tr>`;
    }).join('');
    body=`<div class="table-wrap"><table>
      <thead><tr><th>N°</th><th>Titre / Client</th><th>Type</th><th>Gravité</th><th>Statut</th><th>Pilote</th><th>Date NC</th><th>Activité</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  }

  document.getElementById('content').innerHTML=`
    <div class="page-header">
      <div>
        <div class="page-title">Non-<span>conformités</span></div>
        <div class="page-subtitle">Suivi des NC internes, clients, fournisseurs et logistiques</div>
      </div>
      <div class="header-actions qual-write">
        <button type="button" class="btn btn-ghost" onclick="openImportModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          Importer xlsx
        </button>
        <button type="button" class="btn btn-accent" onclick="openCreateModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Nouvelle NC
        </button>
      </div>
    </div>
    <div class="stat-tabs">${tabsHtml}</div>
    <div class="toolbar">
      <div class="search-wrap">
        <span class="search-ico"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
        <input type="text" id="search-input" class="search-input" placeholder="Rechercher (n°, AR, titre, client, description…)" value="${escAttr(S.search)}" oninput="onSearch(this.value)" onkeydown="if(event.key==='Escape'){this.value='';onSearch('');}">
      </div>
      <select class="filter-select" onchange="setTypeFilter(this.value)">
        <option value="all"${S.filterType==='all'?' selected':''}>Tous types</option>
        ${TYPES.map(t=>`<option value="${t.k}"${S.filterType===t.k?' selected':''}>${escHtml(t.label)}</option>`).join('')}
      </select>
      <select class="filter-select" onchange="setGraviteFilter(this.value)">
        <option value="all"${S.filterGravite==='all'?' selected':''}>Toutes gravités</option>
        ${GRAVITES.map(g=>`<option value="${g.k}"${S.filterGravite===g.k?' selected':''}>${escHtml(g.label)}</option>`).join('')}
      </select>
    </div>
    ${body}
  `;

  if(fid){const el=document.getElementById(fid);if(el){el.focus();if(cs!=null){try{el.setSelectionRange(cs,ce);}catch(e){}}}}
}

function setStatutFilter(s){S.filterStatut=s;renderList();}
function setTypeFilter(t){S.filterType=t;renderList();}
function setGraviteFilter(g){S.filterGravite=g;renderList();}
function onSearch(v){S.search=v;renderList();}

// ── Vue Détail ─────────────────────────────────────────────────────
async function openDetail(id){
  S.view='detail';S.detailTab='fiche';
  try{
    const r=await api('/api/qualite/nc/'+id);
    if(!r.ok){showToast('NC introuvable','danger');return;}
    S.current=await r.json();
    document.getElementById('mobile-sub').textContent=S.current.numero||'Détail';
    renderDetail();
    await Promise.all([loadFiles(id),loadMessages(id)]);
    renderDetail();
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}
async function loadFiles(id){
  try{const r=await api('/api/qualite/nc/'+id+'/fichiers');if(r.ok) S.currentFiles=await r.json();}catch(e){}
}
async function loadMessages(id){
  try{const r=await api('/api/qualite/nc/'+id+'/messages');if(r.ok){S.currentMessages=await r.json();loadUnread();}}catch(e){}
}

function setDetailTab(t){S.detailTab=t;renderDetail();}

function renderDetail(){
  if(!S.current){document.getElementById('content').innerHTML='<div class="empty"><div class="spin"></div></div>';return;}
  const ae=document.activeElement;const fid=ae?.id;const cs=ae?.selectionStart;const ce=ae?.selectionEnd;
  const n=S.current;
  const filesCount=S.currentFiles.length;
  const msgsCount=S.currentMessages.length;

  let tabBody='';
  if(S.detailTab==='fiche') tabBody=renderFicheTab(n);
  else if(S.detailTab==='fichiers') tabBody=renderFichiersTab(n);
  else if(S.detailTab==='discussion') tabBody=renderDiscussionTab(n);

  document.getElementById('content').innerHTML=`
    <button type="button" class="detail-back" onclick="setView('list')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      Retour à la liste
    </button>
    <div class="detail-header">
      <div>
        <div class="detail-title"><span class="detail-num">${escHtml(n.numero||'')}</span>${escHtml(n.titre||'')}</div>
        <div class="detail-meta">
          ${typeBadge(n.type_nc)} ${gravBadge(n.gravite)} ${statutBadge(n.statut)}
          ${n.numero_ar?`<span style="font-size:11px;color:var(--muted)">AR ${escHtml(n.numero_ar)}</span>`:''}
          ${n.numero_historique?`<span style="font-size:11px;color:var(--muted)">N° historique : ${escHtml(n.numero_historique)}</span>`:''}
          ${n.no_dossier?`<span style="font-size:11px;color:var(--muted)">Dossier ${escHtml(n.no_dossier)}</span>`:''}
        </div>
      </div>
      <div class="detail-actions">
        <a class="btn btn-ghost btn-sm" href="/api/qualite/nc/${n.id}/pdf" target="_blank" rel="noopener">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Exporter PDF
        </a>
        <button type="button" class="btn btn-ghost btn-sm qual-write" onclick="openDelModal(${n.id})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
          Supprimer
        </button>
      </div>
    </div>
    <div class="detail-tabs">
      <button type="button" class="detail-tab${S.detailTab==='fiche'?' active':''}" onclick="setDetailTab('fiche')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        Fiche technique
      </button>
      <button type="button" class="detail-tab${S.detailTab==='fichiers'?' active':''}" onclick="setDetailTab('fichiers')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        Fichiers ${filesCount?`<span class="stat-count">${filesCount}</span>`:''}
      </button>
      <button type="button" class="detail-tab${S.detailTab==='discussion'?' active':''}" onclick="setDetailTab('discussion')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
        Discussion ${msgsCount?`<span class="stat-count">${msgsCount}</span>`:''}
      </button>
    </div>
    ${tabBody}
  `;

  if(fid){const el=document.getElementById(fid);if(el){el.focus();if(cs!=null){try{el.setSelectionRange(cs,ce);}catch(e){}}}}
}

function renderFicheTab(n){
  const services=Array.isArray(n.services_impliques)?n.services_impliques:[];
  const userOpts=S.users.map(u=>`<option value="${u.id}"${n.pilote_id==u.id?' selected':''}>${escHtml(u.nom)}</option>`).join('');
  const emetteurOpts=S.users.map(u=>`<option value="${u.id}"${n.emetteur_id==u.id?' selected':''}>${escHtml(u.nom)}</option>`).join('');
  const meIsAdmin = S.me && ['administration','direction','superadmin'].includes(S.me.role);
  return `
    <div class="card">
      <div class="card-title">Identification</div>
      <div class="form-grid">
        <div>
          <label class="form-label">Titre</label>
          <input type="text" class="form-input" data-field="titre" value="${escAttr(n.titre||'')}" onchange="saveField('titre',this.value)">
        </div>
        <div>
          <label class="form-label">N° de commande (AR)</label>
          <input type="text" class="form-input" data-field="numero_ar" value="${escAttr(n.numero_ar||'')}" onchange="saveField('numero_ar',this.value)">
          <div class="form-hint">N° généré : <strong>${escHtml(n.numero||'')}</strong></div>
        </div>
        <div>
          <label class="form-label">N° interne historique</label>
          <input type="text" class="form-input" data-field="numero_historique" value="${escAttr(n.numero_historique||'')}" onchange="saveField('numero_historique',this.value)" placeholder="ex : 668608">
        </div>
        <div>
          <label class="form-label">Type de NC</label>
          <select class="form-select" data-field="type_nc" onchange="saveField('type_nc',this.value)">
            ${TYPES.map(t=>`<option value="${t.k}"${n.type_nc===t.k?' selected':''}>${escHtml(t.label)}</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="form-label">Gravité</label>
          <select class="form-select" data-field="gravite" onchange="saveField('gravite',this.value)">
            ${GRAVITES.map(g=>`<option value="${g.k}"${n.gravite===g.k?' selected':''}>${escHtml(g.label)}</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="form-label">Statut</label>
          <select class="form-select" data-field="statut" onchange="saveField('statut',this.value)">
            ${STATUTS.map(s=>`<option value="${s.k}"${n.statut===s.k?' selected':''}>${escHtml(s.label)}</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="form-label">Date de la NC</label>
          <input type="date" class="form-input" data-field="date_nc" value="${escAttr(n.date_nc||'')}" onchange="saveField('date_nc',this.value)">
        </div>
        <div>
          <label class="form-label">Service concerné</label>
          <input type="text" class="form-input" data-field="service_concerne" value="${escAttr(n.service_concerne||'')}" onchange="saveField('service_concerne',this.value)" placeholder="ex : Production, ADV…">
        </div>
        <div>
          <label class="form-label">Émetteur</label>
          <select class="form-select" data-field="emetteur_id" onchange="saveField('emetteur_id',this.value?parseInt(this.value):null)">
            <option value="">—</option>
            ${emetteurOpts}
          </select>
        </div>
        <div>
          <label class="form-label">Pilote</label>
          <select class="form-select" data-field="pilote_id" onchange="saveField('pilote_id',this.value?parseInt(this.value):null)">
            <option value="">—</option>
            ${userOpts}
          </select>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Objet</div>
      <div class="form-grid">
        <div>
          <label class="form-label">Nom client / fournisseur</label>
          <input type="text" class="form-input" data-field="client_fournisseur" value="${escAttr(n.client_fournisseur||'')}" onchange="saveField('client_fournisseur',this.value)">
        </div>
        <div>
          <label class="form-label">Référence client</label>
          <input type="text" class="form-input" data-field="ref_client" value="${escAttr(n.ref_client||'')}" onchange="saveField('ref_client',this.value)">
        </div>
        <div>
          <label class="form-label">Référence SIFA (dossier)</label>
          <div style="display:flex;gap:6px">
            <input type="text" class="form-input" id="detail-dossier" data-field="no_dossier" value="${escAttr(n.no_dossier||'')}" onchange="saveField('no_dossier',this.value)" placeholder="ex : 1153/0030">
            <button type="button" class="btn btn-ghost btn-sm" onclick="openDossierPicker('detail-dossier')">Rechercher</button>
          </div>
        </div>
        <div>
          <label class="form-label">Descriptif produit</label>
          <input type="text" class="form-input" data-field="descriptif_produit" value="${escAttr(n.descriptif_produit||'')}" onchange="saveField('descriptif_produit',this.value)">
        </div>
        <div>
          <label class="form-label">Quantité concernée</label>
          <input type="text" class="form-input" data-field="quantite_concernee" value="${escAttr(n.quantite_concernee||'')}" onchange="saveField('quantite_concernee',this.value)" placeholder="ex : 150 000 ex">
        </div>
        <div>
          <label class="form-label">Coût estimé (€)</label>
          <input type="number" step="0.01" class="form-input" data-field="cout_estime" value="${escAttr(n.cout_estime!=null?n.cout_estime:'')}" onchange="saveField('cout_estime',this.value===''?null:parseFloat(this.value))">
        </div>
        <div class="col-2">
          <label class="form-label">Description de la non-conformité</label>
          <textarea class="form-textarea" data-field="description" rows="3" onchange="saveField('description',this.value)">${escHtml(n.description||'')}</textarea>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Analyse & actions</div>
      <div style="margin-bottom:14px">
        <label class="form-label">Services impliqués</label>
        <div class="chips-row">
          ${SERVICES_5M.map(s=>`<button type="button" class="chip${services.includes(s)?' active':''}" onclick="toggleService('${escAttr(s)}')">${escHtml(s)}</button>`).join('')}
        </div>
      </div>
      <div class="form-grid cols-1">
        <div>
          <label class="form-label">Analyse des causes (cause racine)</label>
          <textarea class="form-textarea" data-field="analyse_causes" rows="3" onchange="saveField('analyse_causes',this.value)">${escHtml(n.analyse_causes||'')}</textarea>
        </div>
        <div>
          <label class="form-label">Action corrective</label>
          <textarea class="form-textarea" data-field="action_corrective" rows="3" onchange="saveField('action_corrective',this.value)">${escHtml(n.action_corrective||'')}</textarea>
        </div>
        <div>
          <label class="form-label">Action préventive à mettre en place</label>
          <textarea class="form-textarea" data-field="action_preventive" rows="3" onchange="saveField('action_preventive',this.value)">${escHtml(n.action_preventive||'')}</textarea>
        </div>
      </div>
      <div class="form-grid" style="margin-top:14px">
        <div>
          <label class="form-label">Délai cible</label>
          <input type="date" class="form-input" data-field="delai_cible" value="${escAttr(n.delai_cible||'')}" onchange="saveField('delai_cible',this.value)">
        </div>
        <div>
          <label class="form-label">Date de clôture</label>
          <input type="text" class="form-input" value="${escAttr(fmtDate(n.date_cloture))}" readonly>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Validations</div>
      <div class="valid-grid">
        ${validBox('Direction Qualité', n.validation_qualite_nom, n.validation_qualite_at, 'qualite', meIsAdmin)}
        ${validBox('Direction Industrielle', n.validation_industrielle_nom, n.validation_industrielle_at, 'industrielle', meIsAdmin)}
      </div>
    </div>
  `;
}

function validBox(label, name, at, kind, canSign){
  const signed=!!name;
  return `<div class="valid-box${signed?' signed':''}">
    <div class="valid-box-title">${escHtml(label)}</div>
    ${signed?`<div class="valid-box-name">${escHtml(name)}</div><div class="valid-box-date">Signé le ${escHtml(fmtDateTime(at))}</div>`:'<div style="font-size:12px;color:var(--muted)">En attente de signature</div>'}
    ${canSign?`<div class="valid-box-actions">${signed?`<button type="button" class="btn btn-ghost btn-sm" onclick="revokeValid('${kind}')">Retirer la signature</button>`:`<button type="button" class="btn btn-ok btn-sm" onclick="signValid('${kind}')">Signer</button>`}</div>`:''}
  </div>`;
}

function toggleService(s){
  if(!S.current) return;
  const cur=Array.isArray(S.current.services_impliques)?S.current.services_impliques.slice():[];
  const idx=cur.indexOf(s);
  if(idx>=0) cur.splice(idx,1); else cur.push(s);
  S.current.services_impliques=cur;
  saveField('services_impliques', cur);
  renderDetail();
}

let _saveTimers = {};
function saveField(field, value){
  if(S.isQualiteReadonly) return;
  if(!S.current) return;
  // Optimistic update
  S.current[field]=value;
  clearTimeout(_saveTimers[field]);
  _saveTimers[field]=setTimeout(async()=>{
    try{
      const body={};body[field]=value;
      const r=await api('/api/qualite/nc/'+S.current.id,{
        method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
      });
      if(!r.ok){
        const d=await r.json().catch(()=>({}));
        showToast(d.detail||'Erreur de sauvegarde','danger');
        return;
      }
      S.current=await r.json();
      // Mise à jour discrète sans re-render complet pour ne pas perdre le focus
      const idx=S.ncs.findIndex(x=>x.id===S.current.id);
      if(idx>=0){
        // Recharger la liste à la prochaine occasion
        loadNCs();
      }
      // Si statut changé en cloturee, refresh canaux/unread
      if(field==='statut') loadCanaux();
    }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
  }, 350);
}

async function signValid(kind){
  if(S.isQualiteReadonly) return;
  if(!S.current) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/valider',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,revoke:false})
    });
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Erreur','danger');return;}
    S.current=await r.json();renderDetail();showToast('Signature enregistrée.','success');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}
async function revokeValid(kind){
  if(S.isQualiteReadonly) return;
  if(!S.current) return;
  if(!confirm('Retirer la signature ?')) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/valider',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,revoke:true})
    });
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Erreur','danger');return;}
    S.current=await r.json();renderDetail();showToast('Signature retirée.','info');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Fichiers tab ───────────────────────────────────────────────────
function renderFichiersTab(n){
  const list=S.currentFiles||[];
  const filesHtml=list.length?list.map(f=>{
    const ext=(f.original_name||'').split('.').pop().toUpperCase();
    const sizeKB=f.size_bytes?Math.round(f.size_bytes/1024):0;
    return `<div class="file-row">
      <div class="file-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
      <div style="flex:1;min-width:0">
        <div class="file-name">${escHtml(f.original_name||'')}</div>
        <div class="file-meta">${escHtml(ext)} · ${sizeKB} ko · Ajouté par ${escHtml(f.uploaded_by_nom||'?')} le ${escHtml(fmtDateTime(f.uploaded_at))}</div>
      </div>
      <div class="file-actions">
        <a class="btn btn-ghost btn-sm" href="/api/qualite/nc/${n.id}/fichiers/${f.id}" target="_blank" rel="noopener">Ouvrir</a>
        <button type="button" class="btn btn-ghost btn-sm qual-write" onclick="delFichier(${f.id})">Supprimer</button>
      </div>
    </div>`;
  }).join(''):'<div class="empty" style="padding:30px"><div class="empty-title">Aucun fichier</div><div class="empty-sub">Ajoutez les pièces jointes (emails, PDF, photos, xlsx…) via la zone ci-dessus.</div></div>';

  return `<div class="card">
    <div class="card-title">Pièces jointes</div>
    <label class="upload-zone qual-write" id="upload-zone" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event, ${n.id})">
      <div style="display:flex;justify-content:center;margin-bottom:10px">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="display:block">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <div style="font-size:13px">Glisser-déposer un fichier ici, ou cliquer pour choisir</div>
      <div style="font-size:11px;margin-top:4px;opacity:.7">Email, PDF, image, Excel, Word…</div>
      <input type="file" id="file-input" onchange="onFileInput(event, ${n.id})" multiple>
    </label>
    <div style="margin-top:16px">${filesHtml}</div>
  </div>`;
}

function onDragOver(e){e.preventDefault();e.currentTarget.classList.add('drag');}
function onDragLeave(e){e.currentTarget.classList.remove('drag');}
async function onDrop(e, ncId){
  e.preventDefault();e.currentTarget.classList.remove('drag');
  const files=Array.from(e.dataTransfer.files||[]);
  for(const f of files) await uploadFile(ncId, f);
}
async function onFileInput(e, ncId){
  const files=Array.from(e.target.files||[]);
  for(const f of files) await uploadFile(ncId, f);
  e.target.value='';
}
async function uploadFile(ncId, file){
  if(S.isQualiteReadonly) return;
  try{
    const fd=new FormData();fd.append('file', file);
    const r=await api('/api/qualite/nc/'+ncId+'/fichiers',{method:'POST',body:fd});
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Échec import','danger');return;}
    S.currentFiles=await r.json();
    renderDetail();
    showToast('Fichier ajouté.','success');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}
async function delFichier(fileId){
  if(S.isQualiteReadonly) return;
  if(!S.current) return;
  if(!confirm('Supprimer ce fichier ?')) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/fichiers/'+fileId,{method:'DELETE'});
    if(!r.ok){showToast('Erreur','danger');return;}
    await loadFiles(S.current.id);renderDetail();showToast('Fichier supprimé.','info');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Discussion tab ─────────────────────────────────────────────────
function renderDiscussionTab(n){
  const list=S.currentMessages||[];
  const messagesHtml=list.length?list.map(m=>{
    const author=m.author_nom||'?';
    const role=m.author_role||'';
    const attach=m.attachment_id&&m.attachment_name?
      `<a class="msg-attach" href="/api/qualite/nc/${n.id}/fichiers/${m.attachment_id}" target="_blank" rel="noopener">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        ${escHtml(m.attachment_name)}
      </a>`:'';
    return `<div class="msg">
      <div class="msg-avatar">${escHtml(initials(author))}</div>
      <div class="msg-body">
        <div class="msg-head">
          <span class="msg-author">${escHtml(author)}</span>
          ${role?`<span class="msg-role">${escHtml(role)}</span>`:''}
          <span class="msg-time">${escHtml(relTime(m.created_at))}</span>
        </div>
        <div class="msg-text">${escHtml(m.body||'')}</div>
        ${attach}
      </div>
    </div>`;
  }).join(''):'<div class="empty" style="padding:30px"><div class="empty-title">Démarrez la discussion</div><div class="empty-sub">Notez les échanges, partagez le contexte et les décisions.</div></div>';

  return `<div class="card">
    <div class="card-title">Fil de discussion</div>
    <div class="msg-list" id="msg-list">${messagesHtml}</div>
    <div class="msg-input-wrap qual-write">
      <textarea id="msg-input" class="msg-input" placeholder="Écrire un message…" onkeydown="if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){event.preventDefault();sendMessage();}"></textarea>
      <button type="button" class="btn btn-accent" onclick="sendMessage()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        Envoyer
      </button>
    </div>
    <div class="form-hint">Astuce : Ctrl + Entrée pour envoyer.</div>
  </div>`;
}

async function sendMessage(){
  if(S.isQualiteReadonly) return;
  if(!S.current) return;
  const inp=document.getElementById('msg-input');
  const text=(inp?.value||'').trim();
  if(!text){showToast('Message vide','danger');return;}
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/messages',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({body:text})
    });
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Erreur envoi','danger');return;}
    const msg=await r.json();
    S.currentMessages.push(msg);
    if(inp) inp.value='';
    renderDetail();
    setTimeout(()=>{const l=document.getElementById('msg-list');if(l) l.scrollTop=l.scrollHeight;},10);
    loadCanaux();
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Canaux ─────────────────────────────────────────────────────────
function openCanaux(){
  loadCanaux();
  document.getElementById('canaux-panel').classList.add('open');
  closeSidebar();
}
function closeCanaux(){document.getElementById('canaux-panel').classList.remove('open');}
function toggleCanaux(){
  const p=document.getElementById('canaux-panel');
  if(p.classList.contains('open')){closeCanaux();}
  else{openCanaux();}
}

function renderCanaux(){
  const list=document.getElementById('canaux-list');
  if(!list) return;
  const cs=S.canaux.filter(c=>c.messages_count>0||c.unread_count>0).concat(S.canaux.filter(c=>!c.messages_count&&!c.unread_count));
  if(!cs.length){
    list.innerHTML='<div class="empty" style="padding:30px"><div class="empty-title">Aucune NC ouverte</div><div class="empty-sub">Les canaux apparaissent ici dès qu\'une NC reçoit des messages.</div></div>';
    return;
  }
  list.innerHTML=cs.map(c=>{
    const unread=c.unread_count>0;
    return `<div class="canal-item${unread?' unread':''}" onclick="closeCanaux();openDetail(${c.id});setTimeout(()=>setDetailTab('discussion'),50);">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <span class="canal-num">${escHtml(c.numero||'')}</span>
        ${unread?`<span class="unread-pill">${c.unread_count}</span>`:''}
      </div>
      <div class="canal-titre">${escHtml(c.titre||'')}</div>
      <div class="canal-time">
        <span>${typeLabel(c.type_nc)} · ${gravLabel(c.gravite)}</span>
        <span>${c.last_message_at?escHtml(relTime(c.last_message_at)):'Pas encore de message'}</span>
      </div>
    </div>`;
  }).join('');
}

// ── Création NC ────────────────────────────────────────────────────
function openCreateModal(){
  if(S.isQualiteReadonly) return;
  document.getElementById('c-titre').value='';
  document.getElementById('c-ar').value='';
  document.getElementById('c-type').value='interne';
  document.getElementById('c-gravite').value='mineure';
  document.getElementById('c-date').value=new Date().toISOString().slice(0,10);
  document.getElementById('c-service').value='';
  document.getElementById('c-client').value='';
  document.getElementById('c-refclient').value='';
  document.getElementById('c-dossier').value='';
  document.getElementById('c-desc').value='';
  document.getElementById('create-modal').style.display='flex';
  requestAnimationFrame(()=>document.getElementById('c-titre').focus());
}
function closeCreateModal(){document.getElementById('create-modal').style.display='none';}

async function submitCreate(){
  if(S.isQualiteReadonly) return;
  const titre=document.getElementById('c-titre').value.trim();
  if(!titre){showToast('Titre obligatoire','danger');return;}
  const body={
    titre,
    numero_ar:document.getElementById('c-ar').value.trim()||null,
    type_nc:document.getElementById('c-type').value,
    gravite:document.getElementById('c-gravite').value,
    date_nc:document.getElementById('c-date').value||null,
    service_concerne:document.getElementById('c-service').value.trim()||null,
    client_fournisseur:document.getElementById('c-client').value.trim()||null,
    ref_client:document.getElementById('c-refclient').value.trim()||null,
    no_dossier:document.getElementById('c-dossier').value.trim()||null,
    description:document.getElementById('c-desc').value.trim()||null,
  };
  const btn=document.getElementById('create-btn');
  btn.disabled=true;btn.textContent='Création…';
  try{
    const r=await api('/api/qualite/nc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Erreur','danger');btn.disabled=false;btn.textContent='Créer la NC';return;}
    const nc=await r.json();
    closeCreateModal();
    showToast('NC créée : '+nc.numero,'success');
    await loadNCs();
    openDetail(nc.id);
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
  btn.disabled=false;btn.textContent='Créer la NC';
}

// ── Import xlsx ────────────────────────────────────────────────────
function openImportModal(){
  if(S.isQualiteReadonly) return;
  document.getElementById('import-file').value='';
  document.getElementById('import-zone-label').textContent='Glisser-déposer le fichier xlsx, ou cliquer pour choisir';
  document.getElementById('import-progress').style.display='none';
  document.getElementById('import-modal').style.display='flex';
}
function closeImportModal(){document.getElementById('import-modal').style.display='none';}
function onImportDragOver(e){e.preventDefault();e.currentTarget.classList.add('drag');}
function onImportDragLeave(e){e.currentTarget.classList.remove('drag');}
function onImportDrop(e){
  e.preventDefault();e.currentTarget.classList.remove('drag');
  const files=Array.from(e.dataTransfer.files||[]);
  if(files.length) submitImport(files[0]);
}
function onImportFile(e){
  const files=Array.from(e.target.files||[]);
  if(files.length) submitImport(files[0]);
}
async function submitImport(file){
  if(S.isQualiteReadonly) return;
  const name=(file.name||'').toLowerCase();
  if(!name.endsWith('.xlsx')&&!name.endsWith('.xlsm')){
    showToast('Format requis : .xlsx ou .xlsm','danger');return;
  }
  const prog=document.getElementById('import-progress');
  prog.style.display='block';
  const label=document.getElementById('import-zone-label');
  label.textContent=file.name;
  try{
    const fd=new FormData();fd.append('file',file);
    const r=await api('/api/qualite/import-xlsx',{method:'POST',body:fd});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Échec import','danger');
      prog.style.display='none';
      return;
    }
    const nc=await r.json();
    closeImportModal();
    showToast('NC importée : '+nc.numero,'success');
    await loadNCs();
    openDetail(nc.id);
  }catch(e){
    if(e.message!=='unauth')showToast('Erreur réseau','danger');
    prog.style.display='none';
  }
}

// ── Dossier picker ─────────────────────────────────────────────────
function openDossierPicker(targetId){
  S.dpTarget=targetId;S.dpResults=[];
  document.getElementById('dp-search').value='';
  document.getElementById('dp-list').innerHTML='<div style="padding:30px;text-align:center;color:var(--muted)">Saisir pour rechercher…</div>';
  document.getElementById('dp-modal').style.display='flex';
  searchDossiers('');
  requestAnimationFrame(()=>document.getElementById('dp-search').focus());
}
function closeDossierPicker(){document.getElementById('dp-modal').style.display='none';}
async function searchDossiers(q){
  try{
    const r=await api('/api/qualite/dossiers-search?q='+encodeURIComponent(q));
    if(!r.ok) return;
    const list=await r.json();S.dpResults=list;
    const dpList=document.getElementById('dp-list');
    if(!list.length){dpList.innerHTML='<div style="padding:20px;text-align:center;color:var(--muted)">Aucun dossier trouvé</div>';return;}
    dpList.innerHTML=list.map(d=>`<div class="picker-item" onclick="pickDossier('${escAttr(d.no_dossier||'')}')">
      <div class="picker-item-ref">${escHtml(d.no_dossier||'')}</div>
      <div class="picker-item-meta">${escHtml(d.client||'')}${d.designation?' · '+escHtml(d.designation):''}</div>
    </div>`).join('');
  }catch(e){}
}
function pickDossier(no){
  if(S.dpTarget){
    const el=document.getElementById(S.dpTarget);
    if(el){el.value=no;el.dispatchEvent(new Event('change'));}
  }
  closeDossierPicker();
}

// ── Suppression ────────────────────────────────────────────────────
function openDelModal(id){
  if(S.isQualiteReadonly) return;
  S.delId=id;
  const nc=S.current||S.ncs.find(n=>n.id===id);
  document.getElementById('del-msg').textContent=`La NC ${nc?nc.numero:''} sera définitivement supprimée, ainsi que tous ses fichiers et messages. Cette action est irréversible.`;
  document.getElementById('del-modal').style.display='flex';
}
function closeDelModal(){document.getElementById('del-modal').style.display='none';S.delId=null;}
async function confirmDelete(){
  if(S.isQualiteReadonly) return;
  if(!S.delId) return;
  try{
    const r=await api('/api/qualite/nc/'+S.delId,{method:'DELETE'});
    if(!r.ok){showToast('Erreur de suppression','danger');return;}
    closeDelModal();showToast('NC supprimée.','info');
    await loadNCs();setView('list');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ══════════════════════════════════════════════════════════════════
// ── Module Audits client ──────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════

// CSS spécifique injecté au démarrage
(function injectAuditCss(){
  if(document.getElementById('audit-css')) return;
  const st=document.createElement('style'); st.id='audit-css';
  st.textContent = `
    .aud-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
    .aud-toolbar .search-wrap{flex:1;min-width:240px;max-width:480px}
    .aud-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:0;overflow:hidden}
    .aud-emp{padding:60px 20px;text-align:center;color:var(--muted)}
    .aud-emp .emp-icon{font-size:32px;margin-bottom:12px;color:var(--text2)}
    .aud-emp .emp-title{font-size:15px;font-weight:700;color:var(--text);margin-bottom:6px}
    .aud-emp .emp-sub{font-size:12px;color:var(--muted)}
    .aud-row-num{font-family:ui-monospace,monospace;font-weight:700;color:var(--accent);font-size:12px}
    .aud-row-client{font-weight:600;color:var(--text);max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .aud-row-desc{font-size:11px;color:var(--muted);margin-top:2px;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .aud-stat-ouvert{background:rgba(34,211,238,.12);color:var(--accent);border:1px solid rgba(34,211,238,.35)}
    .aud-stat-cloture{background:rgba(52,211,153,.12);color:var(--success);border:1px solid rgba(52,211,153,.35)}
    .aud-stat-pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700}
    .aud-aud-chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--accent-bg);
      color:var(--accent);font-size:10px;font-weight:700;margin:1px 2px;border:1px solid rgba(34,211,238,.25)}
    .aud-aud-chip .x{margin-left:5px;cursor:pointer;opacity:.7}
    .aud-aud-chip .x:hover{opacity:1;color:var(--danger)}
    .aud-bc{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:10px 14px;
      background:var(--bg);border-bottom:1px solid var(--border);font-size:12px}
    .aud-bc-item{padding:3px 8px;border-radius:6px;cursor:pointer;color:var(--text2);transition:.12s}
    .aud-bc-item:hover{background:var(--accent-bg);color:var(--accent)}
    .aud-bc-item.cur{color:var(--text);font-weight:700;cursor:default}
    .aud-bc-sep{color:var(--muted)}
    .aud-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;padding:14px}
    .aud-tile{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;
      padding:18px 12px;border:1px solid var(--border);border-radius:10px;background:var(--bg);
      cursor:pointer;transition:.15s;text-align:center;min-height:108px}
    .aud-tile:hover{border-color:var(--accent);background:var(--accent-bg);transform:translateY(-1px)}
    .aud-tile-ico{color:var(--accent);margin-bottom:8px}
    .aud-tile-name{font-size:12px;font-weight:600;color:var(--text);word-break:break-word;max-width:100%;
      line-height:1.3}
    .aud-tile-meta{font-size:10px;color:var(--muted);margin-top:4px}
    .aud-tile-actions{position:absolute;top:6px;right:6px;display:none;gap:4px}
    .aud-tile:hover .aud-tile-actions{display:flex}
    .aud-tile-act{width:22px;height:22px;display:flex;align-items:center;justify-content:center;
      border-radius:6px;background:var(--card);color:var(--text2);border:1px solid var(--border);
      cursor:pointer;transition:.12s}
    .aud-tile-act:hover{color:var(--accent);border-color:var(--accent)}
    .aud-tile-act.del:hover{color:var(--danger);border-color:var(--danger)}
    .aud-empty-folder{grid-column:1/-1;padding:40px 16px;text-align:center;color:var(--muted);font-size:12px}
    .aud-tab-content{padding:18px}
    .aud-info-row{display:flex;gap:16px;margin-bottom:14px;flex-wrap:wrap}
    .aud-info-cell{flex:1;min-width:200px}
    .aud-info-label{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
      font-weight:700;margin-bottom:4px}
    .aud-info-val{color:var(--text);font-size:13px;line-height:1.5;word-break:break-word}
    .aud-info-val textarea, .aud-info-val input[type=date], .aud-info-val input[type=text]{
      width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;
      padding:8px 10px;color:var(--text);font-family:inherit;font-size:13px;transition:.15s}
    .aud-info-val textarea:focus, .aud-info-val input:focus{border-color:var(--accent);outline:none;
      box-shadow:0 0 0 3px rgba(34,211,238,.12)}
    .aud-info-val textarea{min-height:80px;resize:vertical}
    .aud-msg-list{display:flex;flex-direction:column;gap:10px;max-height:520px;overflow-y:auto;padding:6px 2px 16px}
    .aud-msg{display:flex;gap:10px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px}
    .aud-msg .av{flex:0 0 32px;height:32px;border-radius:999px;background:var(--accent-bg);color:var(--accent);
      display:flex;align-items:center;justify-content:center;font-weight:800;font-size:11px}
    .aud-msg .bd{flex:1;min-width:0}
    .aud-msg .hd{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:4px}
    .aud-msg .nm{font-weight:700;color:var(--text);font-size:12px}
    .aud-msg .tm{font-size:10px;color:var(--muted);white-space:nowrap}
    .aud-msg .tx{font-size:13px;color:var(--text2);line-height:1.5;white-space:pre-wrap;word-break:break-word}
    .aud-msg-form{display:flex;gap:8px;margin-top:12px;align-items:flex-end}
    .aud-msg-form textarea{flex:1;min-height:46px;max-height:160px;background:var(--bg);border:1px solid var(--border);
      border-radius:10px;padding:10px 12px;color:var(--text);font-family:inherit;font-size:13px;resize:vertical}
    .aud-msg-form textarea:focus{border-color:var(--accent);outline:none}
    .aud-chip-row{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
    .aud-picker-list{display:flex;flex-direction:column;gap:4px;max-height:280px;overflow-y:auto;
      padding:6px;border:1px solid var(--border);border-radius:8px;background:var(--bg)}
    .aud-picker-item{padding:8px 12px;border-radius:6px;cursor:pointer;color:var(--text2);font-size:13px;
      display:flex;justify-content:space-between;align-items:center;gap:8px;transition:.12s}
    .aud-picker-item:hover{background:var(--accent-bg);color:var(--accent)}
    .aud-picker-item .meta{font-size:11px;color:var(--muted)}
    .aud-picker-item.sel{background:var(--accent-bg);color:var(--accent)}
    .aud-drop-hint{padding:14px 18px;border:2px dashed var(--border);border-radius:10px;text-align:center;
      color:var(--muted);font-size:12px;margin:8px 14px 0;transition:.12s}
    .aud-drop-hint.over{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
  
/* Badge Source officielle : mis en avant avec fond accent */
.ref-source-btn{
  display:inline-flex;align-items:center;gap:6px;
  background:var(--accent-bg);
  border:1px solid var(--accent);
  color:var(--accent);
  border-radius:20px;padding:5px 12px;
  font-size:11.5px;font-weight:600;
  text-decoration:none;
  transition:all .15s;
  white-space:nowrap
}
.ref-source-btn:hover{
  background:var(--accent);
  color:var(--btn-fg);
  transform:translateY(-1px);
  box-shadow:0 4px 12px rgba(34,211,238,.25)
}
.ref-source-btn svg{opacity:.85}
`;
  document.head.appendChild(st);
})();

async function loadAudits(){
  try{
    let url='/api/qualite/audits';
    const qs=[];
    if(S.auditFilterStatut!=='all') qs.push('statut='+encodeURIComponent(S.auditFilterStatut));
    if(S.auditSearch.trim()) qs.push('q='+encodeURIComponent(S.auditSearch.trim()));
    if(qs.length) url+='?'+qs.join('&');
    const r=await api(url);
    if(!r.ok){showToast('Erreur chargement audits','danger');return;}
    S.audits=await r.json();
    if(S.view==='audits-list') renderAuditsList();
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

function renderAuditsList(){
  const ae=document.activeElement;const fid=ae?.id;const cs=ae?.selectionStart;const ce=ae?.selectionEnd;
  const root=document.getElementById('content');
  const list=S.audits||[];
  const counts={all:list.length,ouvert:list.filter(a=>a.statut==='ouvert').length,cloture:list.filter(a=>a.statut==='cloture').length};

  const tabsHtml=`
    <button type="button" class="stat-tab${S.auditFilterStatut==='all'?' active':''}" onclick="setAuditFilter('all')">Tous<span class="stat-count">${counts.all}</span></button>
    <button type="button" class="stat-tab${S.auditFilterStatut==='ouvert'?' active':''}" onclick="setAuditFilter('ouvert')">Ouverts<span class="stat-count">${counts.ouvert}</span></button>
    <button type="button" class="stat-tab${S.auditFilterStatut==='cloture'?' active':''}" onclick="setAuditFilter('cloture')">Clôturés<span class="stat-count">${counts.cloture}</span></button>
  `;

  let body;
  if(!list.length){
    body=`<div class="aud-emp">
      <div class="emp-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
      <div class="emp-title">${S.auditSearch?'Aucun résultat pour « '+escHtml(S.auditSearch)+' »':'Aucun audit client'}</div>
      <div class="emp-sub">${(!S.auditSearch&&S.auditFilterStatut==='all')?'Créez le premier audit avec le bouton ci-dessus.':''}</div>
    </div>`;
  } else {
    const rows=list.map(a=>{
      const audits=(a.auditeurs||[]).map(u=>escHtml(u.nom||'')).join(' · ')||'—';
      const unreadBadge=a.unread_count>0?`<span class="unread-pill">${a.unread_count}</span>`:'';
      return `<tr onclick="openAudit(${a.id})">
        <td><div class="aud-row-num">${escHtml(a.numero||'')}</div></td>
        <td>
          <div class="aud-row-client" title="${escAttr(a.client_nom||'')}">${escHtml(a.client_nom||'—')}</div>
          <div class="aud-row-desc" title="${escAttr(a.description||'')}">${escHtml((a.description||'').slice(0,140))}</div>
        </td>
        <td><span class="aud-stat-pill aud-stat-${escAttr(a.statut)}">${a.statut==='ouvert'?'Ouvert':'Clôturé'}</span></td>
        <td><span style="font-family:ui-monospace,monospace;font-size:12px;color:var(--text2)">${escHtml(fmtDate(a.date_audit))}</span></td>
        <td><span style="color:var(--text2);font-size:12px">${audits}</span></td>
        <td style="color:var(--muted);font-size:11px;white-space:nowrap">${escHtml(relTime(a.updated_at))}${unreadBadge}</td>
      </tr>`;
    }).join('');
    body=`<div class="table-wrap"><table>
      <thead><tr>
        <th>N°</th><th>Client / Description</th><th>Statut</th><th>Date</th><th>Auditeurs</th><th>Maj</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  }

  root.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:10px">
      <h2 style="margin:0;font-size:18px;color:var(--text)">Audits client</h2>
      <button type="button" class="btn btn-accent qual-write" onclick="openCreateAuditModal()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;vertical-align:-2px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouvel audit
      </button>
    </div>
    <div class="stat-tabs">${tabsHtml}</div>
    <div class="aud-toolbar">
      <div class="search-wrap" style="position:relative">
        <input type="search" id="aud-search" placeholder="Rechercher (client, description, N°...)" value="${escAttr(S.auditSearch)}" oninput="onAuditSearch(this.value)" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-family:inherit;font-size:13px">
      </div>
    </div>
    ${body}
  `;

  if(fid){const el=document.getElementById(fid);if(el){el.focus();if(cs!=null){try{el.setSelectionRange(cs,ce);}catch(e){}}}}
}

function setAuditFilter(s){S.auditFilterStatut=s;loadAudits();}
let _audSearchTm=null;
function onAuditSearch(v){
  S.auditSearch=v;
  clearTimeout(_audSearchTm);
  _audSearchTm=setTimeout(loadAudits,250);
}

async function openAudit(id){
  try{
    const r=await api('/api/qualite/audits/'+id);
    if(!r.ok){showToast('Audit introuvable','danger');return;}
    S.currentAudit=await r.json();
    S.currentFolderId=null;
    S.auditDetailTab='fichiers';
    await Promise.all([loadAuditFolders(id), loadAuditFiles(id)]);
    setView('audits-detail');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}
async function loadAuditFolders(id){
  try{const r=await api('/api/qualite/audits/'+id+'/folders');
    if(r.ok) S.currentAuditFolders=await r.json();
  }catch(e){}
}
async function loadAuditFiles(id){
  try{const r=await api('/api/qualite/audits/'+id+'/fichiers');
    if(r.ok) S.currentAuditFiles=await r.json();
  }catch(e){}
}
async function loadAuditMessages(id){
  try{const r=await api('/api/qualite/audits/'+id+'/messages');
    if(r.ok){S.currentAuditMessages=await r.json();}
  }catch(e){}
}

function folderPath(folderId){
  if(folderId==null) return [];
  const byId={};
  S.currentAuditFolders.forEach(f=>{byId[f.id]=f;});
  const path=[];
  let cur=byId[folderId];
  let guard=0;
  while(cur && guard<50){path.unshift(cur);cur=cur.parent_id?byId[cur.parent_id]:null;guard++;}
  return path;
}

function renderAuditDetail(){
  const root=document.getElementById('content');
  const a=S.currentAudit;
  if(!a){root.innerHTML='<div class="aud-emp"><div class="emp-title">Audit introuvable</div></div>';return;}
  const auditeursChips=(a.auditeurs||[]).map(u=>`<span class="aud-aud-chip">${escHtml(u.nom||'')}<span class="x" onclick="removeAuditeur(${u.user_id})" title="Retirer">×</span></span>`).join('');

  root.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:14px">
      <div>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button class="btn btn-ghost" onclick="setView('audits-list')" style="padding:6px 10px;font-size:12px">← Retour</button>
          <div style="font-family:ui-monospace,monospace;font-weight:700;color:var(--accent);font-size:14px">${escHtml(a.numero)}</div>
          <span class="aud-stat-pill aud-stat-${escAttr(a.statut)}">${a.statut==='ouvert'?'Ouvert':'Clôturé'}</span>
        </div>
        <h2 style="margin:8px 0 4px;font-size:18px;color:var(--text)">${escHtml(a.client_nom||'—')}</h2>
        <div style="font-size:12px;color:var(--muted)">Audit du ${escHtml(fmtDate(a.date_audit))} · ${(a.auditeurs||[]).length} auditeur(s)</div>
      </div>
      <div class="qual-write" style="display:flex;gap:8px;flex-wrap:wrap">
        ${a.statut==='ouvert'?`<button class="btn btn-accent" onclick="cloturerAudit()" style="padding:8px 14px;font-size:12px">Clôturer</button>`:`<button class="btn btn-ghost" onclick="rouvrirAudit()" style="padding:8px 14px;font-size:12px">Rouvrir</button>`}
        <button class="btn btn-danger" onclick="deleteAudit()" style="padding:8px 14px;font-size:12px">Supprimer</button>
      </div>
    </div>

    <div class="detail-tabs">
      <button class="detail-tab${S.auditDetailTab==='fichiers'?' active':''}" onclick="setAuditTab('fichiers')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        Fichiers
      </button>
      <button class="detail-tab${S.auditDetailTab==='fiche'?' active':''}" onclick="setAuditTab('fiche')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        Informations
      </button>
      <button class="detail-tab${S.auditDetailTab==='discussion'?' active':''}" onclick="setAuditTab('discussion')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
        Échanges
      </button>
    </div>

    <div id="aud-tab-body"></div>
  `;
  renderAuditTab();
}

function setAuditTab(t){
  S.auditDetailTab=t;
  if(t==='discussion'){
    loadAuditMessages(S.currentAudit.id).then(()=>{document.querySelectorAll('.detail-tab').forEach(b=>b.classList.remove('active'));const btns=Array.from(document.querySelectorAll('.detail-tab'));btns.forEach(b=>{if(b.textContent.trim().startsWith('Échanges'))b.classList.add('active');});renderAuditTab();});
  } else {
    renderAuditDetail();
  }
}

function renderAuditTab(){
  const body=document.getElementById('aud-tab-body');
  if(!body) return;
  if(S.auditDetailTab==='fichiers') body.innerHTML=renderAuditFichiersHTML();
  else if(S.auditDetailTab==='fiche') body.innerHTML=renderAuditFicheHTML();
  else if(S.auditDetailTab==='discussion') body.innerHTML=renderAuditDiscussionHTML();
  if(S.auditDetailTab==='discussion'){
    const scroll=document.getElementById('aud-msg-scroll');
    if(scroll){scroll.scrollTop=scroll.scrollHeight;}
  }
}

function renderAuditFichiersHTML(){
  const a=S.currentAudit;
  const path=folderPath(S.currentFolderId);
  const subfolders=S.currentAuditFolders.filter(f=>(f.parent_id||null)===(S.currentFolderId||null));
  const files=S.currentAuditFiles.filter(f=>(f.folder_id||null)===(S.currentFolderId||null));

  const bcItems=[`<span class="aud-bc-item ${S.currentFolderId===null?'cur':''}" onclick="navFolder(null)">${escHtml(a.client_nom||'Audit')}</span>`];
  path.forEach((f,i)=>{
    bcItems.push(`<span class="aud-bc-sep">›</span>`);
    const cls=(i===path.length-1)?'aud-bc-item cur':'aud-bc-item';
    bcItems.push(`<span class="${cls}" onclick="navFolder(${f.id})">${escHtml(f.nom)}</span>`);
  });

  let grid='';
  if(!subfolders.length && !files.length){
    grid=`<div class="aud-empty-folder">Ce dossier est vide. Crée un sous-dossier ou glisse-dépose un fichier ici.</div>`;
  } else {
    grid+=subfolders.map(f=>`
      <div class="aud-tile" ondblclick="navFolder(${f.id})" onclick="navFolder(${f.id})">
        <div class="aud-tile-actions">
          <button class="aud-tile-act" title="Renommer" onclick="event.stopPropagation();renameFolder(${f.id})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="aud-tile-act del" title="Supprimer" onclick="event.stopPropagation();deleteFolderConfirm(${f.id})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg>
          </button>
        </div>
        <div class="aud-tile-ico"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></div>
        <div class="aud-tile-name">${escHtml(f.nom)}</div>
      </div>`).join('');
    grid+=files.map(f=>`
      <div class="aud-tile" ondblclick="openFile(${f.id})">
        <div class="aud-tile-actions">
          <button class="aud-tile-act" title="Ouvrir" onclick="event.stopPropagation();openFile(${f.id})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          </button>
          <button class="aud-tile-act del" title="Supprimer" onclick="event.stopPropagation();deleteAuditFile(${f.id})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg>
          </button>
        </div>
        <div class="aud-tile-ico"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
        <div class="aud-tile-name" title="${escAttr(f.original_name||'')}">${escHtml((f.original_name||'').slice(0,40))}</div>
        <div class="aud-tile-meta">${fmtSize(f.size_bytes)}</div>
      </div>`).join('');
  }

  return `
    <div class="aud-card">
      <div class="aud-bc">${bcItems.join('')}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;padding:10px 14px 0">
        <button class="btn btn-ghost" onclick="createSubfolder()" style="padding:7px 12px;font-size:12px">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:-2px;margin-right:4px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Nouveau sous-dossier
        </button>
        <button class="btn btn-accent" onclick="document.getElementById('aud-file-input').click()" style="padding:7px 12px;font-size:12px">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:-2px;margin-right:4px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          Envoyer des fichiers
        </button>
        <input type="file" id="aud-file-input" multiple style="display:none" onchange="uploadAuditFiles(this.files);this.value='';">
      </div>
      <div id="aud-drop" class="aud-drop-hint" ondragover="event.preventDefault();this.classList.add('over');" ondragleave="this.classList.remove('over');" ondrop="onAuditDrop(event)">Glisser-déposer des fichiers ici</div>
      <div class="aud-grid">${grid}</div>
    </div>
  `;
}

function fmtSize(b){
  if(!b) return '';
  if(b<1024) return b+' o';
  if(b<1048576) return (b/1024).toFixed(1)+' Ko';
  return (b/1048576).toFixed(1)+' Mo';
}

function renderAuditFicheHTML(){
  const a=S.currentAudit;
  return `
    <div class="aud-card" style="padding:18px">
      <div class="aud-info-row">
        <div class="aud-info-cell" style="flex:2">
          <div class="aud-info-label">Client</div>
          <div class="aud-info-val"><input type="text" id="ed-client" value="${escAttr(a.client_nom||'')}" onchange="saveAuditField('client_nom',this.value)"></div>
        </div>
        <div class="aud-info-cell">
          <div class="aud-info-label">Date d'audit</div>
          <div class="aud-info-val"><input type="date" id="ed-date" value="${escAttr(a.date_audit||'')}" onchange="saveAuditField('date_audit',this.value)"></div>
        </div>
      </div>
      <div class="aud-info-row">
        <div class="aud-info-cell" style="flex:1 0 100%">
          <div class="aud-info-label">Description</div>
          <div class="aud-info-val"><textarea id="ed-desc" onchange="saveAuditField('description',this.value)">${escHtml(a.description||'')}</textarea></div>
        </div>
      </div>
      <div class="aud-info-row">
        <div class="aud-info-cell" style="flex:1 0 100%">
          <div class="aud-info-label">Auditeurs</div>
          <div class="aud-info-val">
            <div class="aud-chip-row">${(a.auditeurs||[]).map(u=>`<span class="aud-aud-chip">${escHtml(u.nom||'')}<span class="x" onclick="removeAuditeur(${u.user_id})" title="Retirer">×</span></span>`).join('')||'<span style="color:var(--muted);font-size:12px">Aucun auditeur</span>'}</div>
            <button class="btn btn-ghost" onclick="openAddAuditeurPicker()" style="margin-top:8px;padding:6px 10px;font-size:12px">+ Ajouter un auditeur</button>
          </div>
        </div>
      </div>
      <div class="aud-info-row" style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border)">
        <div class="aud-info-cell">
          <div class="aud-info-label">Numéro</div>
          <div class="aud-info-val" style="font-family:ui-monospace,monospace">${escHtml(a.numero)}</div>
        </div>
        <div class="aud-info-cell">
          <div class="aud-info-label">Créé le</div>
          <div class="aud-info-val">${escHtml(fmtDateTime(a.created_at))} · ${escHtml(a.created_by_nom||'')}</div>
        </div>
        <div class="aud-info-cell">
          <div class="aud-info-label">Dernière modification</div>
          <div class="aud-info-val">${escHtml(fmtDateTime(a.updated_at))} · ${escHtml(a.updated_by_nom||'')}</div>
        </div>
      </div>
    </div>
  `;
}

function renderAuditDiscussionHTML(){
  const msgs=S.currentAuditMessages||[];
  return `
    <div class="aud-card" style="padding:14px 18px">
      <div class="aud-msg-list" id="aud-msg-scroll">
        ${msgs.length?msgs.map(m=>{
          const ini=initials(m.author_nom||'');
          return `<div class="aud-msg">
            <div class="av">${escHtml(ini)}</div>
            <div class="bd">
              <div class="hd"><span class="nm">${escHtml(m.author_nom||'—')}</span><span class="tm">${escHtml(relTime(m.created_at))}</span></div>
              <div class="tx">${escHtml(m.body||'')}</div>
              ${m.attachment_name?`<div style="margin-top:6px;font-size:11px"><a href="/api/qualite/audits/${S.currentAudit.id}/fichiers/${m.attachment_id}" target="_blank" style="color:var(--accent)">📎 ${escHtml(m.attachment_name)}</a></div>`:''}
            </div>
          </div>`;
        }).join(''):'<div style="color:var(--muted);font-size:12px;padding:16px;text-align:center">Aucun échange pour cet audit.</div>'}
      </div>
      <div class="aud-msg-form">
        <textarea id="aud-msg-input" placeholder="Écrire un message..." rows="2"></textarea>
        <button class="btn btn-accent" onclick="sendAuditMessage()" style="padding:10px 18px">Envoyer</button>
      </div>
    </div>
  `;
}

function navFolder(id){S.currentFolderId=id;renderAuditTab();}

async function createSubfolder(){
  if(S.isQualiteReadonly) return;
  const nom=prompt('Nom du sous-dossier :');
  if(!nom||!nom.trim()) return;
  try{
    const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/folders',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({nom:nom.trim(),parent_id:S.currentFolderId})
    });
    if(!r.ok){showToast('Erreur création sous-dossier','danger');return;}
    await loadAuditFolders(S.currentAudit.id);
    renderAuditTab();
    showToast('Sous-dossier créé.','success');
  }catch(e){showToast('Erreur réseau','danger');}
}

async function renameFolder(fid){
  const f=S.currentAuditFolders.find(x=>x.id===fid);
  if(!f) return;
  const nom=prompt('Nouveau nom :',f.nom);
  if(!nom||!nom.trim()||nom===f.nom) return;
  try{
    const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/folders/'+fid,{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({nom:nom.trim()})
    });
    if(!r.ok){showToast('Erreur renommage','danger');return;}
    await loadAuditFolders(S.currentAudit.id);
    renderAuditTab();
  }catch(e){showToast('Erreur réseau','danger');}
}

async function deleteFolderConfirm(fid){
  if(S.isQualiteReadonly) return;
  const f=S.currentAuditFolders.find(x=>x.id===fid);
  if(!f) return;
  if(!confirm('Supprimer le sous-dossier « '+f.nom+' » et tout son contenu ?')) return;
  try{
    const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/folders/'+fid,{method:'DELETE'});
    if(!r.ok){showToast('Erreur suppression','danger');return;}
    await Promise.all([loadAuditFolders(S.currentAudit.id),loadAuditFiles(S.currentAudit.id)]);
    renderAuditTab();
    showToast('Sous-dossier supprimé.','info');
  }catch(e){showToast('Erreur réseau','danger');}
}

async function uploadAuditFiles(files){
  if(S.isQualiteReadonly) return;
  if(!files||!files.length) return;
  const id=S.currentAudit.id;
  for(const f of files){
    const fd=new FormData(); fd.append('file',f);
    let url='/api/qualite/audits/'+id+'/fichiers';
    if(S.currentFolderId!=null) url+='?folder_id='+S.currentFolderId;
    try{
      const r=await api(url,{method:'POST',body:fd});
      if(!r.ok){showToast('Erreur upload : '+f.name,'danger');}
    }catch(e){showToast('Erreur réseau : '+f.name,'danger');}
  }
  await loadAuditFiles(id);
  renderAuditTab();
  showToast(files.length+' fichier(s) envoyé(s).','success');
}

function onAuditDrop(ev){
  ev.preventDefault();
  document.getElementById('aud-drop')?.classList.remove('over');
  if(ev.dataTransfer && ev.dataTransfer.files) uploadAuditFiles(ev.dataTransfer.files);
}

function openFile(fid){
  window.open('/api/qualite/audits/'+S.currentAudit.id+'/fichiers/'+fid,'_blank','noopener');
}

async function deleteAuditFile(fid){
  if(S.isQualiteReadonly) return;
  if(!confirm('Supprimer ce fichier ?')) return;
  try{
    const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/fichiers/'+fid,{method:'DELETE'});
    if(!r.ok){showToast('Erreur suppression','danger');return;}
    await loadAuditFiles(S.currentAudit.id);
    renderAuditTab();
  }catch(e){showToast('Erreur réseau','danger');}
}

async function saveAuditField(field,val){
  if(S.isQualiteReadonly) return;
  try{
    const body={};body[field]=val;
    const r=await api('/api/qualite/audits/'+S.currentAudit.id,{
      method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
    });
    if(!r.ok){showToast('Erreur sauvegarde','danger');return;}
    S.currentAudit=await r.json();
    showToast('Modifié.','success');
  }catch(e){showToast('Erreur réseau','danger');}
}

async function cloturerAudit(){
  if(S.isQualiteReadonly) return;
  if(!confirm('Clôturer cet audit ?')) return;
  const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/cloturer',{method:'POST'});
  if(!r.ok){showToast('Erreur','danger');return;}
  S.currentAudit=await r.json();
  renderAuditDetail();
  showToast('Audit clôturé.','info');
  loadUnread();
}
async function rouvrirAudit(){
  if(S.isQualiteReadonly) return;
  const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/rouvrir',{method:'POST'});
  if(!r.ok){showToast('Erreur','danger');return;}
  S.currentAudit=await r.json();
  renderAuditDetail();
  showToast('Audit rouvert.','info');
  loadUnread();
}
async function deleteAudit(){
  if(S.isQualiteReadonly) return;
  if(!confirm('Supprimer définitivement cet audit et tous ses fichiers ?')) return;
  const r=await api('/api/qualite/audits/'+S.currentAudit.id,{method:'DELETE'});
  if(!r.ok){showToast('Erreur suppression','danger');return;}
  showToast('Audit supprimé.','info');
  S.currentAudit=null;
  await loadAudits();
  setView('audits-list');
}

async function sendAuditMessage(
  if(S.isQualiteReadonly) return;){
  const inp=document.getElementById('aud-msg-input');
  if(!inp) return;
  const text=inp.value.trim();
  if(!text){showToast('Message vide','danger');return;}
  try{
    const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/messages',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({body:text})
    });
    if(!r.ok){showToast('Erreur envoi','danger');return;}
    inp.value='';
    await loadAuditMessages(S.currentAudit.id);
    renderAuditTab();
  }catch(e){showToast('Erreur réseau','danger');}
}

async function removeAuditeur(
  if(S.isQualiteReadonly) return;uid){
  if(!confirm('Retirer cet auditeur ?')) return;
  const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/auditeurs/'+uid,{method:'DELETE'});
  if(!r.ok){showToast('Erreur','danger');return;}
  S.currentAudit=await r.json();
  renderAuditDetail();
}

// ── Modal création audit ────────────────────────────────────────
function openCreateAuditModal(){
  if(S.isQualiteReadonly) return;
  const wrap=document.getElementById('mroot')||(function(){
    const d=document.createElement('div');d.id='mroot';document.body.appendChild(d);return d;
  })();
  wrap.innerHTML=`
  <div class="modal-ov" id="aud-create-ov" style="display:flex" onclick="if(event.target===this)closeAuditCreate()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeAuditCreate()">×</button>
      <h3 style="margin:0 0 14px;font-size:16px;color:var(--text)">Nouvel audit client</h3>
      <div style="display:grid;gap:12px">
        <div>
          <label style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Client *</label>
          <input type="text" id="ac-client" placeholder="Rechercher un client ou saisir librement..." oninput="searchClientsForAudit(this.value)" autocomplete="off" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px">
          <div id="ac-client-results" style="margin-top:6px;max-height:160px;overflow-y:auto"></div>
          <input type="hidden" id="ac-client-id" value="">
        </div>
        <div style="display:grid;grid-template-columns:1fr;gap:12px">
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Date de l'audit *</label>
            <input type="date" id="ac-date" value="${(new Date()).toISOString().slice(0,10)}" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px">
          </div>
        </div>
        <div>
          <label style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Description *</label>
          <textarea id="ac-desc" rows="4" placeholder="Objet de l'audit, points à examiner, contexte..." style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;resize:vertical;min-height:90px;font-family:inherit"></textarea>
        </div>
        <div>
          <label style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:6px">Auditeurs *</label>
          <div id="ac-aud-chips" class="aud-chip-row" style="min-height:24px;margin-bottom:6px"></div>
          <input type="text" id="ac-aud-search" placeholder="Rechercher un auditeur..." oninput="filterAuditeurs(this.value)" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--text);font-size:13px">
          <div id="ac-aud-list" class="aud-picker-list" style="margin-top:6px;max-height:200px"></div>
        </div>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px">
        <button type="button" class="btn btn-ghost" onclick="closeAuditCreate()">Annuler</button>
        <button type="button" class="btn btn-accent" id="ac-submit" onclick="submitCreateAudit()">Créer l'audit</button>
      </div>
    </div>
  </div>`;
  S._acAuditeurs=[];
  loadAuditeursCandidats().then(()=>renderAuditeursPicker(''));
  searchClientsForAudit('');
}

function closeAuditCreate(){
  const ov=document.getElementById('aud-create-ov');
  if(ov) ov.remove();
  S._acAuditeurs=[];
}

async function loadAuditeursCandidats(){
  try{const r=await api('/api/qualite/auditeurs');
    if(r.ok) S.auditeursCandidats=await r.json();
  }catch(e){}
}

function filterAuditeurs(q){renderAuditeursPicker(q||'');}

function renderAuditeursPicker(q){
  const list=document.getElementById('ac-aud-list');
  if(!list) return;
  const ql=(q||'').trim().toLowerCase();
  const items=S.auditeursCandidats.filter(u=>!ql||(u.nom||'').toLowerCase().includes(ql));
  const selIds=new Set(S._acAuditeurs.map(u=>u.id));
  list.innerHTML=items.length?items.map(u=>{
    const sel=selIds.has(u.id);
    const roleLbl={direction:'Direction',administration:'Administration',superadmin:'Super admin'}[u.role]||u.role;
    return `<div class="aud-picker-item ${sel?'sel':''}" onclick="toggleAuditeur(${u.id},'${escAttr(u.nom||'')}')">
      <span>${escHtml(u.nom||'')}</span>
      <span class="meta">${escHtml(roleLbl)}${sel?' · sélectionné':''}</span>
    </div>`;
  }).join(''):'<div style="padding:12px;color:var(--muted);font-size:12px;text-align:center">Aucun candidat</div>';
}

function toggleAuditeur(uid,nom){
  const idx=S._acAuditeurs.findIndex(u=>u.id===uid);
  if(idx>=0) S._acAuditeurs.splice(idx,1);
  else S._acAuditeurs.push({id:uid,nom:nom});
  renderChosenAuditeurs();
  renderAuditeursPicker(document.getElementById('ac-aud-search')?.value||'');
}

function renderChosenAuditeurs(){
  const chips=document.getElementById('ac-aud-chips');
  if(!chips) return;
  chips.innerHTML=S._acAuditeurs.length?S._acAuditeurs.map(u=>`<span class="aud-aud-chip">${escHtml(u.nom)}<span class="x" onclick="toggleAuditeur(${u.id},'${escAttr(u.nom)}')" title="Retirer">×</span></span>`).join(''):'<span style="color:var(--muted);font-size:12px">Aucun auditeur sélectionné</span>';
}

let _acClientTm=null;
async function searchClientsForAudit(q){
  clearTimeout(_acClientTm);
  _acClientTm=setTimeout(async()=>{
    try{
      const url='/api/qualite/clients-search'+(q?('?q='+encodeURIComponent(q)):'');
      const r=await api(url);
      if(r.ok){S.clientsResults=await r.json();renderClientsResults();}
    }catch(e){}
  },200);
}

function renderClientsResults(){
  const el=document.getElementById('ac-client-results');
  if(!el) return;
  const items=S.clientsResults||[];
  const inp=document.getElementById('ac-client');
  const cur=inp?inp.value.trim():'';
  el.innerHTML=items.length?
    '<div class="aud-picker-list">'+items.slice(0,8).map(c=>`<div class="aud-picker-item" onclick="pickClient(${c.id},'${escAttr(c.raison_sociale||'')}')"><span>${escHtml(c.raison_sociale||'')}</span><span class="meta">${escHtml(c.code||'')}${c.ville?' · '+escHtml(c.ville):''}</span></div>`).join('')+'</div>':
    (cur?`<div style="font-size:11px;color:var(--muted);padding:6px 4px">Aucun client trouvé — le nom « ${escHtml(cur)} » sera utilisé en texte libre.</div>`:'');
}

function pickClient(id,nom){
  document.getElementById('ac-client').value=nom;
  document.getElementById('ac-client-id').value=String(id);
  document.getElementById('ac-client-results').innerHTML='';
}

async function submitCreateAudit(){
  if(S.isQualiteReadonly) return;
  const client=(document.getElementById('ac-client').value||'').trim();
  const clientIdRaw=(document.getElementById('ac-client-id').value||'').trim();
  const clientId=clientIdRaw?parseInt(clientIdRaw,10):null;
  const date=(document.getElementById('ac-date').value||'').trim();
  const desc=(document.getElementById('ac-desc').value||'').trim();
  if(!client){showToast('Nom du client obligatoire','danger');return;}
  if(!date){showToast('Date obligatoire','danger');return;}
  if(!desc){showToast('Description obligatoire','danger');return;}
  if(!S._acAuditeurs.length){showToast('Au moins un auditeur obligatoire','danger');return;}
  const btn=document.getElementById('ac-submit');
  if(btn){btn.disabled=true;btn.textContent='Création...';}
  try{
    const r=await api('/api/qualite/audits',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        client_nom:client,
        client_id:(clientId&&client===document.getElementById('ac-client').value)?clientId:null,
        date_audit:date,
        description:desc,
        auditeur_ids:S._acAuditeurs.map(u=>u.id)
      })
    });
    if(!r.ok){
      let msg='Erreur création';
      try{const d=await r.json();if(d.detail)msg=d.detail;}catch(e){}
      showToast(msg,'danger');
      if(btn){btn.disabled=false;btn.textContent='Créer l\'audit';}
      return;
    }
    const created=await r.json();
    closeAuditCreate();
    showToast('Audit créé.','success');
    await loadAudits();
    openAudit(created.id);
  }catch(e){
    showToast('Erreur réseau','danger');
    if(btn){btn.disabled=false;btn.textContent='Créer l\'audit';}
  }
}

// ── Picker ajouter auditeur (depuis détail) ─────────────────────
function openAddAuditeurPicker(){
  const wrap=document.getElementById('mroot')||(function(){
    const d=document.createElement('div');d.id='mroot';document.body.appendChild(d);return d;
  })();
  const curIds=new Set((S.currentAudit.auditeurs||[]).map(u=>u.user_id));
  wrap.innerHTML=`
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeAddAuditeur()">
    <div class="modal" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeAddAuditeur()">×</button>
      <h3 style="margin:0 0 12px;font-size:15px;color:var(--text)">Ajouter un auditeur</h3>
      <input type="text" placeholder="Rechercher..." oninput="renderAddAuditeurList(this.value)" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;margin-bottom:8px" id="add-aud-search">
      <div id="add-aud-list" class="aud-picker-list"></div>
    </div>
  </div>`;
  if(!S.auditeursCandidats.length){loadAuditeursCandidats().then(()=>renderAddAuditeurList(''));}
  else renderAddAuditeurList('');
}
function closeAddAuditeur(){const m=document.getElementById('mroot');if(m)m.innerHTML='';}
function renderAddAuditeurList(q){
  const list=document.getElementById('add-aud-list');
  if(!list) return;
  const curIds=new Set((S.currentAudit.auditeurs||[]).map(u=>u.user_id));
  const ql=(q||'').toLowerCase();
  const items=S.auditeursCandidats.filter(u=>!curIds.has(u.id)&&(!ql||(u.nom||'').toLowerCase().includes(ql)));
  list.innerHTML=items.length?items.map(u=>`<div class="aud-picker-item" onclick="addAuditeurNow(${u.id})">
    <span>${escHtml(u.nom||'')}</span><span class="meta">${escHtml(u.role||'')}</span>
  </div>`).join(''):'<div style="padding:12px;color:var(--muted);font-size:12px;text-align:center">Aucun candidat</div>';
}
async function addAuditeurNow(uid){
  if(S.isQualiteReadonly) return;
  const r=await api('/api/qualite/audits/'+S.currentAudit.id+'/auditeurs',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_id:uid})
  });
  if(!r.ok){showToast('Erreur ajout','danger');return;}
  S.currentAudit=await r.json();
  closeAddAuditeur();
  renderAuditDetail();
  showToast('Auditeur ajouté.','success');
}


// ── Init ───────────────────────────────────────────────────────────
async function init(){
  updateThemeBtn();
  await loadMe();
  // Rôle sans droits Qualite ni lecture seule : on masque NC/Canaux/Audits et on bascule sur le référentiel
  if(!S.isQualiteAdmin && !S.isQualiteReadonly){
    ['nav-nc','nav-canaux','nav-audits'].forEach(id=>{
      const el=document.getElementById(id); if(el) el.style.display='none';
    });
    // Basculer directement sur le referentiel
    setView('ref-list');
    // Charger meta + fiches
    await loadRefMeta();
    await loadRefFiches();
    return;
  }
  // Rôle lecture seule (commercial) : masquer le tab Référentiel (édition ref réservée aux admin qualité)
  if(S.isQualiteReadonly && !S.isQualiteAdmin){
    const refBtn=document.getElementById('nav-ref');
    if(refBtn) refBtn.style.display='none';
    // Marquer le body pour masquer via CSS les boutons d'écriture
    document.body.classList.add('qualite-readonly');
  }
  await loadUsers();
  await Promise.all([loadNCs(),loadCanaux(),loadUnread(),loadRefMeta()]);
  // Précharger les candidats auditeurs (utile dès l'ouverture de la modal création audit)
  if(typeof loadAuditeursCandidats==='function') loadAuditeursCandidats();
  setInterval(()=>{loadUnread();if(document.getElementById('canaux-panel').classList.contains('open'))loadCanaux();},30000);
}

// ═══════════════════════════════════════════════════════════════════════════
// MODULE RÉFÉRENTIEL RSE / NORMES & CERTIFICATIONS
// ═══════════════════════════════════════════════════════════════════════════
(function injectRefCss(){
  if(document.getElementById('ref-css')) return;
  const st=document.createElement('style'); st.id='ref-css';
  st.textContent = `
.ref-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-bottom:16px}
.ref-search-wrap{position:relative;flex:1 1 320px;min-width:240px}
.ref-search-wrap input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:11px 14px 11px 40px;color:var(--text);font-family:inherit;font-size:13px;transition:border-color .15s}
.ref-search-wrap input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none}
.ref-search-wrap .ic{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted)}
.ref-search-wrap .kbd{position:absolute;right:10px;top:50%;transform:translateY(-50%);font-size:10px;color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:2px 6px;background:var(--card)}
.ref-sugg{position:absolute;left:0;right:0;top:calc(100% + 4px);background:var(--card);border:1px solid var(--border);border-radius:10px;z-index:40;max-height:320px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.ref-sugg-group{padding:6px 12px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-top:1px solid var(--border)}
.ref-sugg-group:first-child{border-top:none}
.ref-sugg-item{padding:9px 12px;cursor:pointer;font-size:13px;color:var(--text2);display:flex;align-items:center;justify-content:space-between;gap:8px}
.ref-sugg-item:hover,.ref-sugg-item.hl{background:var(--accent-bg);color:var(--text)}
.ref-sugg-item .tag{font-size:10px;color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:1px 6px}

.ref-filters{display:flex;flex-wrap:wrap;gap:6px}
.ref-filter{border:1px solid var(--border);background:var(--card);color:var(--text2);border-radius:20px;padding:6px 12px;font-size:12px;cursor:pointer;transition:all .15s;font-family:inherit}
.ref-filter:hover{border-color:var(--accent);color:var(--text)}
.ref-filter.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent);font-weight:600}
.ref-filter .cnt{margin-left:6px;font-size:10px;opacity:.7}

.ref-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.ref-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;cursor:pointer;transition:border-color .15s,transform .15s;display:flex;flex-direction:column;gap:10px}
.ref-card:hover{border-color:var(--accent);transform:translateY(-1px)}
.ref-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.ref-card-title{font-weight:700;color:var(--text);font-size:15px;line-height:1.3}
.ref-card-acr{font-size:11px;color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin-top:2px}
.ref-card-def{font-size:12.5px;color:var(--text2);line-height:1.5;flex:1;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.ref-card-foot{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:11px;color:var(--muted)}
.ref-cat{border-radius:6px;padding:2px 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.ref-cat--environnement{background:rgba(52,211,153,.12);color:var(--ok);border:1px solid rgba(52,211,153,.3)}
.ref-cat--social{background:rgba(34,211,238,.12);color:var(--accent);border:1px solid rgba(34,211,238,.3)}
.ref-cat--tracabilite{background:rgba(251,191,36,.12);color:var(--warn);border:1px solid rgba(251,191,36,.3)}
.ref-cat--securite{background:rgba(248,113,113,.12);color:var(--danger);border:1px solid rgba(248,113,113,.3)}

.ref-dot{display:inline-block;width:8px;height:8px;border-radius:99px;margin-right:4px;vertical-align:middle}
.ref-dot--conforme{background:var(--ok)}
.ref-dot--partiel{background:var(--warn)}
.ref-dot--en_cours{background:var(--accent)}
.ref-dot--non_applicable{background:var(--muted)}
.ref-dot--a_evaluer{background:var(--muted);opacity:.5}

.ref-badge{border-radius:6px;padding:2px 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.ref-badge--brouillon{background:rgba(148,163,184,.15);color:var(--muted);border:1px solid var(--border)}
.ref-badge--en_revue{background:rgba(251,191,36,.15);color:var(--warn);border:1px solid rgba(251,191,36,.3)}
.ref-badge--valide{background:rgba(52,211,153,.15);color:var(--ok);border:1px solid rgba(52,211,153,.3)}

.ref-detail-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:20px 24px;background:var(--card);border:1px solid var(--border);border-radius:12px;margin-bottom:16px;flex-wrap:wrap}
.ref-detail-title{font-size:22px;font-weight:700;color:var(--text);margin:0;line-height:1.2}
.ref-detail-sub{font-size:12px;color:var(--muted);margin-top:6px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.ref-block{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 22px;margin-bottom:14px}
.ref-block h3{font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px;margin:0 0 10px 0}
.ref-block p{color:var(--text2);font-size:13.5px;line-height:1.6;margin:0;white-space:pre-wrap}
.ref-block textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-family:inherit;font-size:13px;resize:vertical;min-height:80px;transition:border-color .15s}
.ref-block textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none}
.ref-block input[type=text],.ref-block input[type=url],.ref-block select{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-family:inherit;font-size:13px;transition:border-color .15s}
.ref-block input:focus,.ref-block select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none}
.ref-field{margin-bottom:12px}
.ref-field label{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:6px}

.ref-questions-list{display:flex;flex-direction:column;gap:6px}
.ref-question-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:13px;color:var(--text2)}
.ref-question-item:hover{border-color:var(--accent)}
.ref-question-item .x{cursor:pointer;color:var(--muted);opacity:.6;font-size:16px}
.ref-question-item .x:hover{color:var(--danger);opacity:1}

.ref-audits-list{display:flex;flex-direction:column;gap:8px}
.ref-audit-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;cursor:pointer;transition:border-color .15s}
.ref-audit-item:hover{border-color:var(--accent)}
.ref-audit-item .num{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--muted)}
.ref-audit-item .client{color:var(--text);font-weight:600;font-size:13px}
.ref-audit-item .date{font-size:11px;color:var(--muted)}

.ref-files-list{display:flex;flex-direction:column;gap:6px}
.ref-file-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px}
.ref-file-item a{color:var(--accent);text-decoration:none;font-size:13px;flex:1;display:flex;align-items:center;gap:8px}
.ref-file-item a:hover{text-decoration:underline}
.ref-file-item .sz{font-size:11px;color:var(--muted)}
.ref-file-item .x{cursor:pointer;color:var(--muted);opacity:.6;font-size:14px}
.ref-file-item .x:hover{color:var(--danger);opacity:1}

.ref-tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.ref-tag{background:var(--bg);color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:2px 8px;font-size:10.5px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

.ref-empty{padding:60px 20px;text-align:center;color:var(--muted)}
.ref-empty .emp-title{font-size:15px;color:var(--text);font-weight:600;margin-bottom:6px}
.ref-empty .emp-sub{font-size:12px;line-height:1.5}

/* Fix : styles des inputs dans le bandeau d edition (etaient sans theme) */
.ref-detail-head input[type=text],
.ref-detail-head input[type=url],
.ref-detail-head select{
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 14px;color:var(--text);font-family:inherit;font-size:13px;
  transition:border-color .15s
}
.ref-detail-head input:focus,
.ref-detail-head select:focus{
  border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none
}

/* Bloc DEFINITION mis en avant : hero card avec bord accent, typo forte */
.ref-def-hero{
  background:linear-gradient(135deg, var(--accent-bg) 0%, transparent 60%);
  border:1px solid var(--border);
  border-left:4px solid var(--accent);
  border-radius:14px;padding:22px 26px;margin-bottom:18px;
  position:relative;overflow:hidden
}
.ref-def-hero::before{
  content:"";position:absolute;top:0;right:0;width:120px;height:120px;
  background:radial-gradient(circle at top right, var(--accent-bg) 0%, transparent 70%);
  pointer-events:none
}
.ref-def-hero--environnement{border-left-color:var(--ok);background:linear-gradient(135deg,rgba(52,211,153,.10) 0%,transparent 60%)}
.ref-def-hero--environnement::before{background:radial-gradient(circle at top right, rgba(52,211,153,.14) 0%, transparent 70%)}
.ref-def-hero--social{border-left-color:var(--accent)}
.ref-def-hero--tracabilite{border-left-color:var(--warn);background:linear-gradient(135deg,rgba(251,191,36,.10) 0%,transparent 60%)}
.ref-def-hero--tracabilite::before{background:radial-gradient(circle at top right, rgba(251,191,36,.14) 0%, transparent 70%)}
.ref-def-hero--securite{border-left-color:var(--danger);background:linear-gradient(135deg,rgba(248,113,113,.10) 0%,transparent 60%)}
.ref-def-hero--securite::before{background:radial-gradient(circle at top right, rgba(248,113,113,.14) 0%, transparent 70%)}
.ref-def-hero-label{
  font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
  color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px
}
.ref-def-hero-label svg{opacity:.7}
.ref-def-hero-text{
  font-size:17px;line-height:1.55;color:var(--text);font-weight:500;
  position:relative;z-index:1
}
.ref-def-hero-text .acr{
  display:inline-block;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  background:var(--card);border:1px solid var(--border);border-radius:6px;
  padding:2px 10px;font-size:13px;color:var(--accent);font-weight:600;margin-right:6px;
  vertical-align:1px
}

/* Accordeon Q/R */
.ref-qa-list{display:flex;flex-direction:column;gap:6px}
.ref-qa-item{
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  overflow:hidden;transition:border-color .15s
}
.ref-qa-item:hover{border-color:var(--accent)}
.ref-qa-item.open{border-color:var(--accent);background:var(--card)}
.ref-qa-q{
  display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer;
  font-size:13px;color:var(--text);font-weight:500;user-select:none
}
.ref-qa-q .chev{
  display:inline-block;transition:transform .18s;color:var(--muted);flex-shrink:0
}
.ref-qa-item.open .ref-qa-q .chev{transform:rotate(90deg);color:var(--accent)}
.ref-qa-q .q-text{flex:1}
.ref-qa-q .actions{display:flex;gap:4px;opacity:0;transition:opacity .15s}
.ref-qa-item:hover .ref-qa-q .actions{opacity:1}
.ref-qa-q .actions .btn-mini{
  background:none;border:none;color:var(--muted);cursor:pointer;padding:3px 6px;
  border-radius:6px;font-size:12px;transition:.15s
}
.ref-qa-q .actions .btn-mini:hover{background:var(--card);color:var(--text)}
.ref-qa-q .actions .btn-mini.del:hover{color:var(--danger)}
.ref-qa-r{
  padding:0 14px 12px 34px;font-size:13px;color:var(--text2);line-height:1.6;
  white-space:pre-wrap;border-top:1px solid var(--border);padding-top:12px;margin-top:2px
}
.ref-qa-r-empty{color:var(--muted);font-style:italic;font-size:12px}

/* Formulaire ajout Q/R : deux champs */
.ref-qa-add{
  display:flex;flex-direction:column;gap:8px;margin-top:12px;
  padding:12px;background:var(--bg);border:1px dashed var(--border);border-radius:10px
}
.ref-qa-add input,.ref-qa-add textarea{
  background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:9px 12px;color:var(--text);font-family:inherit;font-size:13px;
  transition:border-color .15s;width:100%
}
.ref-qa-add textarea{min-height:60px;resize:vertical}
.ref-qa-add input:focus,.ref-qa-add textarea:focus{
  border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none
}
.ref-qa-add-actions{display:flex;justify-content:flex-end;gap:8px}

/* Edition inline d une question */
.ref-qa-edit-form{padding:12px 14px;background:var(--card);border-top:1px solid var(--border)}
.ref-qa-edit-form input,.ref-qa-edit-form textarea{
  background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:9px 12px;color:var(--text);font-family:inherit;font-size:13px;
  transition:border-color .15s;width:100%;margin-bottom:8px
}
.ref-qa-edit-form textarea{min-height:80px;resize:vertical}
.ref-qa-edit-form input:focus,.ref-qa-edit-form textarea:focus{
  border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none
}
.ref-qa-edit-actions{display:flex;justify-content:flex-end;gap:6px}
`;
  document.head.appendChild(st);
})();

// ─── Chargement méta et fiches ────────────────────────────────────────────
async function loadRefMeta(){
  try{
    const r = await api('/api/qualite/ref/meta');
    if(r.ok) S.refMeta = await r.json();
  }catch(e){}
}

async function loadRefFiches(){
  try{
    const qs = [];
    if(S.refSearch.trim()) qs.push('q='+encodeURIComponent(S.refSearch.trim()));
    if(S.refFilterCat!=='all') qs.push('categorie='+S.refFilterCat);
    if(S.refFilterStatV!=='all') qs.push('statut_validation='+S.refFilterStatV);
    if(S.refFilterStatS!=='all') qs.push('statut_sifa='+S.refFilterStatS);
    if(S.refValideOnly) qs.push('valide_only=1');
    const url = '/api/qualite/ref/fiches' + (qs.length?'?'+qs.join('&'):'');
    const r = await api(url);
    if(!r.ok){ showToast('Erreur chargement fiches','danger'); return; }
    S.refFiches = await r.json();
    if(S.view==='ref-list') renderRefList();
  }catch(e){}
}

// ─── Rendu liste ──────────────────────────────────────────────────────────
function _refCatLabel(k){
  if(!S.refMeta) return k;
  const c = S.refMeta.categories.find(x=>x.key===k); return c?c.label:k;
}
function _refStatSLabel(k){
  if(!S.refMeta) return k;
  const s = S.refMeta.statuts_sifa.find(x=>x.key===k); return s?s.label:k;
}
function _refStatVLabel(k){
  if(!S.refMeta) return k;
  const s = S.refMeta.statuts_validation.find(x=>x.key===k); return s?s.label:k;
}

function renderRefList(){
  const root = document.getElementById('content');
  // Sauvegarder focus et curseur (searchbar)
  const ae = document.activeElement;
  const focusId = ae ? ae.id : null;
  const caretS = ae ? ae.selectionStart : null;
  const caretE = ae ? ae.selectionEnd : null;

  const cats = (S.refMeta && S.refMeta.categories) || [];
  // Compteurs par catégorie (basé sur la liste actuellement filtrée par statut/search)
  const countBy = {all: S.refFiches.length};
  cats.forEach(c=>{ countBy[c.key] = S.refFiches.filter(f=>f.categorie===c.key).length; });

  const filtersHtml = `
    <button type="button" class="ref-filter${S.refFilterCat==='all'?' active':''}" onclick="setRefCat('all')">Toutes<span class="cnt">${countBy.all}</span></button>
    ${cats.map(c=>`<button type="button" class="ref-filter${S.refFilterCat===c.key?' active':''}" onclick="setRefCat('${c.key}')">${escHtml(c.label)}<span class="cnt">${countBy[c.key]||0}</span></button>`).join('')}
  `;

  const shown = S.refFilterCat==='all' ? S.refFiches : S.refFiches.filter(f=>f.categorie===S.refFilterCat);

  let body;
  if(!shown.length){
    body = `<div class="ref-empty">
      <div class="emp-title">${S.refSearch?'Aucun résultat pour « '+escHtml(S.refSearch)+' »':'Aucune fiche'}</div>
      <div class="emp-sub">${S.refSearch?'Essayez un autre terme ou effacez le filtre.':'Créez la première fiche avec le bouton ci-dessus.'}</div>
    </div>`;
  } else {
    body = `<div class="ref-grid">${shown.map(f=>{
      const acr = f.acronyme ? `<div class="ref-card-acr">${escHtml(f.acronyme)}</div>` : '';
      const dot = `<span class="ref-dot ref-dot--${escAttr(f.statut_sifa)}" title="${escAttr(_refStatSLabel(f.statut_sifa))}"></span>`;
      const badgeV = `<span class="ref-badge ref-badge--${escAttr(f.statut_validation)}">${escHtml(_refStatVLabel(f.statut_validation))}</span>`;
      const cat = `<span class="ref-cat ref-cat--${escAttr(f.categorie)}">${escHtml(_refCatLabel(f.categorie))}</span>`;
      const meta = [];
      if(f.audits_count) meta.push(f.audits_count+' audit'+(f.audits_count>1?'s':''));
      if(f.files_count) meta.push(f.files_count+' PJ');
      if(f.questions_count) meta.push(f.questions_count+' Q');
      return `<div class="ref-card" onclick="openRef(${f.id})">
        <div class="ref-card-head">
          <div>
            <div class="ref-card-title">${escHtml(f.nom)}</div>
            ${acr}
          </div>
          ${badgeV}
        </div>
        <div class="ref-card-def">${escHtml(f.definition||'')}</div>
        <div class="ref-card-foot">
          ${cat}
          <span title="Statut SIFA">${dot}${escHtml(_refStatSLabel(f.statut_sifa))}</span>
          ${meta.length?'<span style="margin-left:auto">'+meta.join(' · ')+'</span>':''}
        </div>
      </div>`;
    }).join('')}</div>`;
  }

  root.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0;font-size:20px;color:var(--text)">Référentiel RSE</h2>
        <div style="font-size:12px;color:var(--muted);margin-top:2px">Normes, certifications et questions clients type</div>
      </div>
      <button type="button" class="btn btn-accent" onclick="openCreateRefModal()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:6px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Nouvelle fiche
      </button>
    </div>
    <div class="ref-toolbar">
      <div class="ref-search-wrap">
        <span class="ic"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
        <input type="search" id="ref-search" autocomplete="off" placeholder="Rechercher une norme, une question client, un mot-clé…" value="${escAttr(S.refSearch)}"
          oninput="onRefSearch(this.value)" onfocus="loadRefSuggests()"
          onkeydown="onRefSearchKey(event)" onblur="setTimeout(closeRefSuggests,150)">
        <span class="kbd">/</span>
        <div id="ref-sugg" class="ref-sugg" style="display:none"></div>
      </div>
      <div class="ref-filters">${filtersHtml}</div>
    </div>
    <div class="ref-toolbar" style="margin-top:-8px;margin-bottom:16px">
      <div class="ref-filters">
        <button type="button" class="ref-filter${S.refFilterStatV==='all'?' active':''}" onclick="setRefStatV('all')">Tous statuts</button>
        <button type="button" class="ref-filter${S.refFilterStatV==='brouillon'?' active':''}" onclick="setRefStatV('brouillon')">Brouillons</button>
        <button type="button" class="ref-filter${S.refFilterStatV==='en_revue'?' active':''}" onclick="setRefStatV('en_revue')">En revue</button>
        <button type="button" class="ref-filter${S.refFilterStatV==='valide'?' active':''}" onclick="setRefStatV('valide')">Validées</button>
      </div>
    </div>
    ${body}
  `;

  // Restaurer focus/curseur
  if(focusId){
    const el = document.getElementById(focusId);
    if(el){ el.focus(); if(caretS!=null){ try{ el.setSelectionRange(caretS, caretE); }catch(e){} } }
  }
}

// ─── Filtres ──────────────────────────────────────────────────────────────
function setRefCat(k){ S.refFilterCat = k; renderRefList(); }
function setRefStatV(k){ S.refFilterStatV = k; loadRefFiches(); }

let _refSearchTm = null;
function onRefSearch(v){
  S.refSearch = v;
  clearTimeout(_refSearchTm);
  _refSearchTm = setTimeout(()=>{ loadRefFiches(); loadRefSuggests(); }, 220);
}
function onRefSearchKey(ev){
  const box = document.getElementById('ref-sugg');
  if(!box || box.style.display==='none'){
    if(ev.key==='Escape'){ ev.target.value=''; onRefSearch(''); }
    return;
  }
  const items = box.querySelectorAll('.ref-sugg-item');
  if(ev.key==='ArrowDown'){ ev.preventDefault(); S.refSuggestIx = Math.min(items.length-1, S.refSuggestIx+1); _hlSugg(items); }
  else if(ev.key==='ArrowUp'){ ev.preventDefault(); S.refSuggestIx = Math.max(-1, S.refSuggestIx-1); _hlSugg(items); }
  else if(ev.key==='Enter' && S.refSuggestIx>=0){ ev.preventDefault(); items[S.refSuggestIx].click(); }
  else if(ev.key==='Escape'){ closeRefSuggests(); }
}
function _hlSugg(items){ items.forEach((it,i)=>it.classList.toggle('hl', i===S.refSuggestIx)); }

async function loadRefSuggests(){
  const q = S.refSearch.trim();
  if(q.length<2){ closeRefSuggests(); return; }
  try{
    const r = await api('/api/qualite/ref/suggestions?q='+encodeURIComponent(q));
    if(!r.ok) return;
    S.refSuggests = await r.json();
    S.refSuggestIx = -1;
    renderRefSuggests();
  }catch(e){}
}
function renderRefSuggests(){
  const box = document.getElementById('ref-sugg'); if(!box) return;
  const s = S.refSuggests; if(!s){ box.style.display='none'; return; }
  const hasQ = s.questions && s.questions.length;
  const hasF = s.fiches && s.fiches.length;
  if(!hasQ && !hasF){ box.style.display='none'; return; }
  let html = '';
  if(hasQ){
    html += '<div class="ref-sugg-group">Questions clients</div>';
    html += s.questions.map(q=>`<div class="ref-sugg-item" onclick="openRef(${q.fiche_id})"><span>${escHtml(q.texte)}</span><span class="tag">${escHtml(q.acronyme||q.fiche_nom)}</span></div>`).join('');
  }
  if(hasF){
    html += '<div class="ref-sugg-group">Fiches</div>';
    html += s.fiches.map(f=>`<div class="ref-sugg-item" onclick="openRef(${f.fiche_id})"><span>${escHtml(f.fiche_nom)}</span><span class="tag">${escHtml(f.acronyme||'')}</span></div>`).join('');
  }
  box.innerHTML = html;
  box.style.display = 'block';
}
function closeRefSuggests(){ const b=document.getElementById('ref-sugg'); if(b){ b.style.display='none'; } S.refSuggestIx=-1; }

// ─── Ouverture / rendu détail ─────────────────────────────────────────────
async function openRef(id){
  try{
    const r = await api('/api/qualite/ref/fiches/'+id);
    if(!r.ok){ showToast('Fiche introuvable','danger'); return; }
    S.currentRef = await r.json();
    S.refEdit = false;
    S.refEditBuf = null;
    closeRefSuggests();
    setView('ref-detail');
  }catch(e){}
}

function renderRefDetail(){
  const root = document.getElementById('content');
  const f = S.currentRef;
  if(!f){ root.innerHTML='<div class="ref-empty"><div class="emp-title">Fiche introuvable</div></div>'; return; }

  const cats = (S.refMeta && S.refMeta.categories) || [];
  const statsS = (S.refMeta && S.refMeta.statuts_sifa) || [];
  const badge = `<span class="ref-badge ref-badge--${escAttr(f.statut_validation)}">${escHtml(_refStatVLabel(f.statut_validation))}</span>`;
  const cat = `<span class="ref-cat ref-cat--${escAttr(f.categorie)}">${escHtml(_refCatLabel(f.categorie))}</span>`;
  const dot = `<span class="ref-dot ref-dot--${escAttr(f.statut_sifa)}"></span>`;

  const isAdmin = S.isQualiteAdmin;
  const canValidate = isAdmin && f.statut_validation==='en_revue';
  const canReject = isAdmin && f.statut_validation==='en_revue';
  const canSubmit = f.statut_validation==='brouillon';
  const canDelete = isAdmin;

  // Actions en tête
  const actions = [];
  if(!S.refEdit){
    actions.push(`<button class="btn btn-ghost" onclick="startRefEdit()">Modifier</button>`);
    if(canSubmit) actions.push(`<button class="btn btn-accent" onclick="submitRef(${f.id})">Soumettre en revue</button>`);
    if(canValidate) actions.push(`<button class="btn btn-accent" onclick="validateRef(${f.id})">Valider</button>`);
    if(canReject) actions.push(`<button class="btn btn-ghost" onclick="rejectRef(${f.id})">Rejeter</button>`);
    if(canDelete) actions.push(`<button class="btn btn-ghost" style="color:var(--danger)" onclick="deleteRef(${f.id})">Supprimer</button>`);
  } else {
    actions.push(`<button class="btn btn-ghost" onclick="cancelRefEdit()">Annuler</button>`);
    actions.push(`<button class="btn btn-accent" onclick="saveRefEdit()">Enregistrer</button>`);
  }

  // Bloc "Position SIFA"
  const positionHtml = S.refEdit
    ? `<textarea id="ref-position">${escHtml(S.refEditBuf.position_sifa||'')}</textarea>`
    : (f.position_sifa
        ? `<p>${escHtml(f.position_sifa)}</p>`
        : `<p style="color:var(--muted);font-style:italic">Notre position n'a pas encore été renseignée.</p>`);

  // Bloc "Détails"
  const detailsHtml = S.refEdit
    ? `<textarea id="ref-details" style="min-height:120px">${escHtml(S.refEditBuf.details||'')}</textarea>`
    : (f.details
        ? `<p>${escHtml(f.details)}</p>`
        : `<p style="color:var(--muted);font-style:italic">Pas de détails complémentaires.</p>`);

  // Bloc DÉFINITION mis en avant (hero card, couleur selon catégorie)
  const defHtml = S.refEdit
    ? `<div class="ref-block"><h3>Définition</h3><textarea id="ref-def">${escHtml(S.refEditBuf.definition||'')}</textarea></div>`
    : `<div class="ref-def-hero ref-def-hero--${escAttr(f.categorie)}">
        <div class="ref-def-hero-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          Définition
        </div>
        <div class="ref-def-hero-text">${f.acronyme?`<span class="acr">${escHtml(f.acronyme)}</span>`:''}${escHtml(f.definition||'')}</div>
      </div>`;

  // Bandeau haut
  const headHtml = S.refEdit
    ? `<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;width:100%">
        <input type="text" id="ref-nom" value="${escAttr(S.refEditBuf.nom||'')}" placeholder="Nom" style="flex:1 1 220px;font-size:16px;font-weight:700">
        <input type="text" id="ref-acr" value="${escAttr(S.refEditBuf.acronyme||'')}" placeholder="Acronyme" style="flex:0 1 120px">
        <select id="ref-cat">${cats.map(c=>`<option value="${c.key}"${c.key===S.refEditBuf.categorie?' selected':''}>${escHtml(c.label)}</option>`).join('')}</select>
        <select id="ref-stat-sifa">${statsS.map(s=>`<option value="${s.key}"${s.key===S.refEditBuf.statut_sifa?' selected':''}>${escHtml(s.label)}</option>`).join('')}</select>
      </div>`
    : `<div>
        <h2 class="ref-detail-title">${escHtml(f.nom)}${f.acronyme?` <span style="font-size:14px;color:var(--muted);font-family:ui-monospace,monospace;font-weight:400">${escHtml(f.acronyme)}</span>`:''}</h2>
        <div class="ref-detail-sub">
          ${cat} ${badge}
          <span title="Statut SIFA">${dot}${escHtml(_refStatSLabel(f.statut_sifa))}</span>
          ${f.source_url?`<a class="ref-source-btn" href="${escAttr(f.source_url)}" target="_blank" rel="noopener" title="${escAttr(f.source_url)}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>Source officielle</a>`:''}
        </div>
      </div>`;

  // Tags
  const tagsList = (f.tags||'').split(',').map(t=>t.trim()).filter(Boolean);
  const tagsHtml = S.refEdit
    ? `<div class="ref-block"><div class="ref-field"><label>Mots-clés (séparés par virgule)</label><input type="text" id="ref-tags" style="width:100%" value="${escAttr(S.refEditBuf.tags||'')}"></div></div>`
    : (tagsList.length?`<div class="ref-tags" style="margin:-6px 0 14px 4px">${tagsList.map(t=>`<span class="ref-tag">${escHtml(t)}</span>`).join('')}</div>`:'');

  const sourceHtml = S.refEdit
    ? `<div class="ref-block"><div class="ref-field"><label>Source officielle (URL)</label><input type="url" id="ref-src" style="width:100%" value="${escAttr(S.refEditBuf.source_url||'')}" placeholder="https://..."></div></div>`
    : '';

  // Questions clients type (accordéon : clic sur Q → révèle R)
  const chevSvg = '<span class="chev"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg></span>';
  const questionsHtml = `
    <div class="ref-block">
      <h3>Questions clients type <span style="font-weight:400;color:var(--muted);text-transform:none;letter-spacing:0">(${(f.questions||[]).length}) — cliquer pour voir la réponse</span></h3>
      <div class="ref-qa-list">
        ${(f.questions||[]).map(q=>{
          const isOpen = S.refOpenQaId === q.id;
          const isEdit = S.refEditQaId === q.id;
          if(isEdit){
            return `<div class="ref-qa-item open">
              <div class="ref-qa-q">${chevSvg}<span class="q-text">Modifier la question</span></div>
              <div class="ref-qa-edit-form">
                <input type="text" id="ref-qa-edit-q-${q.id}" value="${escAttr(q.texte)}" placeholder="Question">
                <textarea id="ref-qa-edit-r-${q.id}" placeholder="Réponse SIFA (facultative)">${escHtml(q.reponse||'')}</textarea>
                <div class="ref-qa-edit-actions">
                  <button class="btn btn-ghost" onclick="cancelEditRefQa()">Annuler</button>
                  <button class="btn btn-accent" onclick="saveEditRefQa(${f.id},${q.id})">Enregistrer</button>
                </div>
              </div>
            </div>`;
          }
          return `<div class="ref-qa-item${isOpen?' open':''}">
            <div class="ref-qa-q" onclick="toggleRefQa(${q.id})">
              ${chevSvg}
              <span class="q-text">${escHtml(q.texte)}</span>
              <span class="actions">
                <button class="btn-mini" title="Modifier" onclick="event.stopPropagation();startEditRefQa(${q.id})">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                </button>
                <button class="btn-mini del" title="Retirer" onclick="event.stopPropagation();deleteRefQuestion(${f.id},${q.id})">×</button>
              </span>
            </div>
            ${isOpen?`<div class="ref-qa-r">${q.reponse?escHtml(q.reponse):'<span class="ref-qa-r-empty">Aucune réponse enregistrée. Cliquer sur le crayon pour en ajouter une.</span>'}</div>`:''}
          </div>`;
        }).join('')||'<div style="font-size:12px;color:var(--muted);padding:6px 0">Aucune question enregistrée.</div>'}
      </div>
      <div class="ref-qa-add">
        <input type="text" id="ref-newq" placeholder="Question : Ex. vos produits sont-ils conformes REACH ?">
        <textarea id="ref-newr" placeholder="Réponse type (facultative) : Ex. Oui, SIFA vérifie annuellement…"></textarea>
        <div class="ref-qa-add-actions">
          <button class="btn btn-accent" onclick="addRefQuestion(${f.id})">Ajouter</button>
        </div>
      </div>
    </div>`;

  // Audits liés
  const auditsHtml = `
    <div class="ref-block">
      <h3>Audits client liés <span style="font-weight:400;color:var(--muted);text-transform:none;letter-spacing:0">(${(f.audits||[]).length})</span></h3>
      <div class="ref-audits-list">
        ${(f.audits||[]).map(a=>`<div class="ref-audit-item" onclick="location.href='/qualite?audit=${a.id}'">
            <div>
              <div class="num">${escHtml(a.numero)}</div>
              <div class="client">${escHtml(a.client_nom)}</div>
              ${a.note?`<div style="font-size:12px;color:var(--text2);margin-top:4px">${escHtml(a.note)}</div>`:''}
            </div>
            <div style="display:flex;align-items:center;gap:10px">
              <div class="date">${escHtml(a.date_audit||'')}</div>
              <span class="x" onclick="event.stopPropagation();unlinkRefAudit(${f.id},${a.id})" title="Délier">×</span>
            </div>
          </div>`).join('')||'<div style="font-size:12px;color:var(--muted);padding:6px 0">Aucun audit client lié.</div>'}
      </div>
      <button class="btn btn-ghost" style="margin-top:10px" onclick="openLinkAuditModal(${f.id})">+ Lier un audit</button>
    </div>`;

  // Fichiers
  const filesHtml = `
    <div class="ref-block">
      <h3>Pièces jointes <span style="font-weight:400;color:var(--muted);text-transform:none;letter-spacing:0">(${(f.fichiers||[]).length})</span></h3>
      <div class="ref-files-list">
        ${(f.fichiers||[]).map(fi=>`<div class="ref-file-item">
            <a href="/api/qualite/ref/fichiers/${fi.id}/download" target="_blank">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              ${escHtml(fi.original_name)}
            </a>
            <span class="sz">${Math.round((fi.size_bytes||0)/1024)} Ko</span>
            <span class="x" onclick="deleteRefFile(${fi.id})" title="Supprimer">×</span>
          </div>`).join('')||'<div style="font-size:12px;color:var(--muted);padding:6px 0">Aucune pièce jointe.</div>'}
      </div>
      <label class="btn btn-ghost" style="margin-top:10px;display:inline-flex;align-items:center;gap:6px">
        <input type="file" style="display:none" onchange="uploadRefFile(${f.id}, this)">
        + Ajouter une pièce jointe
      </label>
    </div>`;

  // Métadonnées bas
  const metaFoot = `<div style="font-size:11px;color:var(--muted);margin-top:14px;padding-top:12px;border-top:1px solid var(--border)">
    Créé le ${escHtml(f.created_at||'')} ${f.created_by_nom?'par '+escHtml(f.created_by_nom):''}
    · Mis à jour le ${escHtml(f.updated_at||'')} ${f.updated_by_nom?'par '+escHtml(f.updated_by_nom):''}
    ${f.validated_at?' · Validé le '+escHtml(f.validated_at)+(f.validated_by_nom?' par '+escHtml(f.validated_by_nom):''):''}
  </div>`;

  root.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:10px">
      <button class="btn btn-ghost" onclick="setView('ref-list')" style="padding:6px 12px;font-size:12px">← Retour</button>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${actions.join('')}</div>
    </div>
    <div class="ref-detail-head">${headHtml}</div>
    ${defHtml}${tagsHtml}${sourceHtml}
    <div class="ref-block"><h3>Notre position (SIFA)</h3>${positionHtml}</div>
    <div class="ref-block"><h3>Détails</h3>${detailsHtml}</div>
    ${questionsHtml}
    ${auditsHtml}
    ${filesHtml}
    ${metaFoot}
  `;
}

// ─── Edition ──────────────────────────────────────────────────────────────
function startRefEdit(){
  const f = S.currentRef;
  S.refEditBuf = {
    nom: f.nom, acronyme: f.acronyme||'', categorie: f.categorie,
    definition: f.definition||'', position_sifa: f.position_sifa||'',
    details: f.details||'', statut_sifa: f.statut_sifa,
    source_url: f.source_url||'', tags: f.tags||'',
  };
  S.refEdit = true;
  renderRefDetail();
}
function cancelRefEdit(){ S.refEdit=false; S.refEditBuf=null; renderRefDetail(); }
async function saveRefEdit(){
  const g = (id) => document.getElementById(id);
  const body = {
    nom: g('ref-nom').value.trim(),
    acronyme: g('ref-acr').value.trim(),
    categorie: g('ref-cat').value,
    definition: g('ref-def').value.trim(),
    position_sifa: g('ref-position').value,
    details: g('ref-details').value,
    statut_sifa: g('ref-stat-sifa').value,
    source_url: g('ref-src').value.trim(),
    tags: g('ref-tags').value,
  };
  if(!body.nom){ showToast('Nom obligatoire','danger'); return; }
  if(!body.definition){ showToast('Définition obligatoire','danger'); return; }
  const r = await api('/api/qualite/ref/fiches/'+S.currentRef.id, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  if(!r.ok){ showToast('Erreur enregistrement','danger'); return; }
  showToast('Fiche enregistrée.','success');
  S.refEdit = false; S.refEditBuf = null;
  await openRef(S.currentRef.id);
}

// ─── Workflow validation ──────────────────────────────────────────────────
async function submitRef(id){
  const r = await api('/api/qualite/ref/fiches/'+id+'/submit', {method:'POST'});
  if(!r.ok){ showToast('Erreur soumission','danger'); return; }
  showToast('Fiche soumise en revue.','success');
  await openRef(id);
}
async function validateRef(id){
  const r = await api('/api/qualite/ref/fiches/'+id+'/validate', {method:'POST'});
  if(!r.ok){ showToast('Erreur validation','danger'); return; }
  showToast('Fiche validée.','success');
  await openRef(id);
}
async function rejectRef(id){
  const r = await api('/api/qualite/ref/fiches/'+id+'/reject', {method:'POST'});
  if(!r.ok){ showToast('Erreur rejet','danger'); return; }
  showToast('Fiche repassée en brouillon.','info');
  await openRef(id);
}
async function deleteRef(id){
  if(!confirm('Supprimer définitivement cette fiche et ses pièces jointes ?')) return;
  const r = await api('/api/qualite/ref/fiches/'+id, {method:'DELETE'});
  if(!r.ok){ showToast('Erreur suppression','danger'); return; }
  showToast('Fiche supprimée.','success');
  S.currentRef = null;
  await loadRefFiches();
  setView('ref-list');
}

// ─── Questions type ───────────────────────────────────────────────────────
async function addRefQuestion(fid){
  const inp = document.getElementById('ref-newq');
  const inpR = document.getElementById('ref-newr');
  const t = (inp.value||'').trim();
  const rep = (inpR ? inpR.value : '');
  if(!t){ inp.focus(); return; }
  const r = await api('/api/qualite/ref/fiches/'+fid+'/questions', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({texte:t, reponse:rep})});
  if(!r.ok){ showToast('Erreur ajout','danger'); return; }
  inp.value = ''; if(inpR) inpR.value = '';
  await openRef(fid);
}

// Toggle accordéon Q/R
function toggleRefQa(qid){
  S.refOpenQaId = (S.refOpenQaId === qid) ? null : qid;
  S.refEditQaId = null;
  renderRefDetail();
}

// Édition inline d une question
function startEditRefQa(qid){
  S.refEditQaId = qid;
  S.refOpenQaId = qid;
  renderRefDetail();
  requestAnimationFrame(()=>{ const el=document.getElementById('ref-qa-edit-q-'+qid); if(el){ el.focus(); el.select(); } });
}
function cancelEditRefQa(){
  S.refEditQaId = null;
  renderRefDetail();
}
async function saveEditRefQa(fid, qid){
  const q = document.getElementById('ref-qa-edit-q-'+qid).value.trim();
  const r = document.getElementById('ref-qa-edit-r-'+qid).value;
  if(!q){ showToast('Question vide','danger'); return; }
  const resp = await api('/api/qualite/ref/fiches/'+fid+'/questions/'+qid, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({texte:q, reponse:r})});
  if(!resp.ok){ showToast('Erreur enregistrement','danger'); return; }
  S.refEditQaId = null;
  showToast('Question enregistrée.','success');
  await openRef(fid);
}
async function deleteRefQuestion(fid, qid){
  const r = await api('/api/qualite/ref/fiches/'+fid+'/questions/'+qid, {method:'DELETE'});
  if(!r.ok){ showToast('Erreur','danger'); return; }
  await openRef(fid);
}

// ─── Fichiers ─────────────────────────────────────────────────────────────
async function uploadRefFile(fid, inputEl){
  const file = inputEl.files[0]; if(!file) return;
  const fd = new FormData(); fd.append('file', file);
  const r = await fetch('/api/qualite/ref/fiches/'+fid+'/fichiers', {method:'POST', credentials:'include', body: fd});
  if(!r.ok){ showToast('Erreur upload','danger'); return; }
  showToast('Fichier ajouté.','success');
  inputEl.value = '';
  await openRef(fid);
}
async function deleteRefFile(id){
  if(!confirm('Supprimer ce fichier ?')) return;
  const r = await api('/api/qualite/ref/fichiers/'+id, {method:'DELETE'});
  if(!r.ok){ showToast('Erreur','danger'); return; }
  await openRef(S.currentRef.id);
}

// ─── Audits liés ──────────────────────────────────────────────────────────
async function openLinkAuditModal(fid){
  const wrap = _refMroot();
  wrap.innerHTML = `
    <div class="modal-ov" onclick="if(event.target===this)closeMroot()">
      <div class="modal" onclick="event.stopPropagation()">
        <button type="button" class="modal-close" onclick="closeMroot()">×</button>
        <h3 style="margin:0 0 14px;font-size:16px;color:var(--text)">Lier un audit client</h3>
        <input type="search" id="ref-aud-search" placeholder="Rechercher (client, N° audit…)" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-family:inherit;font-size:13px" oninput="loadRefAuditsPicker(this.value)">
        <div id="ref-aud-picker" style="margin-top:12px;max-height:340px;overflow-y:auto"></div>
      </div>
    </div>`;
  requestAnimationFrame(()=>{ const el=document.getElementById('ref-aud-search'); if(el) el.focus(); });
  await loadRefAuditsPicker('');
  window._refLinkFid = fid;
}
async function loadRefAuditsPicker(q){
  const url = '/api/qualite/ref/audits-picker' + (q?'?q='+encodeURIComponent(q):'');
  const r = await api(url);
  if(!r.ok) return;
  const list = await r.json();
  S.refAuditsPicker = list;
  const cont = document.getElementById('ref-aud-picker'); if(!cont) return;
  cont.innerHTML = list.length ? list.map(a=>`<div class="ref-audit-item" onclick="confirmLinkAudit(${a.id})">
    <div>
      <div class="num">${escHtml(a.numero)}</div>
      <div class="client">${escHtml(a.client_nom)}</div>
    </div>
    <div class="date">${escHtml(a.date_audit||'')}</div>
  </div>`).join('') : '<div style="text-align:center;color:var(--muted);padding:20px;font-size:13px">Aucun audit trouvé.</div>';
}
async function confirmLinkAudit(aid){
  const fid = window._refLinkFid;
  const note = prompt("Note optionnelle sur ce lien (contexte, question posée…) :", "");
  const r = await api('/api/qualite/ref/fiches/'+fid+'/audits', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({audit_id: aid, note: note||null})});
  if(!r.ok){ showToast('Erreur','danger'); return; }
  showToast('Audit lié.','success');
  closeMroot();
  await openRef(fid);
}
async function unlinkRefAudit(fid, aid){
  if(!confirm('Retirer ce lien avec l\'audit ?')) return;
  const r = await api('/api/qualite/ref/fiches/'+fid+'/audits/'+aid, {method:'DELETE'});
  if(!r.ok){ showToast('Erreur','danger'); return; }
  await openRef(fid);
}
function _refMroot(){
  return document.getElementById('mroot') || (function(){
    const d=document.createElement('div'); d.id='mroot'; document.body.appendChild(d); return d;
  })();
}
function closeMroot(){
  const m=document.getElementById('mroot'); if(m) m.innerHTML='';
}

// ─── Création d'une fiche (modal) ─────────────────────────────────────────
function openCreateRefModal(){
  const cats = (S.refMeta && S.refMeta.categories) || [];
  const statsS = (S.refMeta && S.refMeta.statuts_sifa) || [];
  const wrap = _refMroot();
  wrap.innerHTML = `
    <div class="modal-ov" onclick="if(event.target===this)closeMroot()">
      <div class="modal lg" onclick="event.stopPropagation()">
        <button type="button" class="modal-close" onclick="closeMroot()">×</button>
        <h3 style="margin:0 0 14px;font-size:16px;color:var(--text)">Nouvelle fiche référentiel</h3>
        <div class="ref-field"><label>Nom</label><input type="text" id="new-nom" style="width:100%" placeholder="Ex : ISO 14001"></div>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <div class="ref-field" style="flex:0 1 160px"><label>Acronyme</label><input type="text" id="new-acr" style="width:100%" placeholder="Ex : REACH"></div>
          <div class="ref-field" style="flex:1 1 200px"><label>Catégorie</label><select id="new-cat" style="width:100%">${cats.map(c=>`<option value="${c.key}">${escHtml(c.label)}</option>`).join('')}</select></div>
          <div class="ref-field" style="flex:1 1 200px"><label>Statut SIFA</label><select id="new-stat" style="width:100%">${statsS.map(s=>`<option value="${s.key}">${escHtml(s.label)}</option>`).join('')}</select></div>
        </div>
        <div class="ref-field"><label>Définition (1-2 lignes)</label><textarea id="new-def" style="min-height:70px" placeholder="Définition courte et concrète"></textarea></div>
        <div class="ref-field"><label>Notre position (SIFA) — optionnel</label><textarea id="new-pos" style="min-height:70px" placeholder="Ce que nous avons mis en place, procédures internes…"></textarea></div>
        <div class="ref-field"><label>Mots-clés (séparés par virgule)</label><input type="text" id="new-tags" style="width:100%" placeholder="ex : chimie,ue,substances"></div>
        <div class="ref-field"><label>Source officielle (URL) — optionnel</label><input type="url" id="new-src" style="width:100%" placeholder="https://..."></div>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px">
          <button class="btn btn-ghost" onclick="closeMroot()">Annuler</button>
          <button class="btn btn-accent" onclick="submitCreateRef()">Créer en brouillon</button>
        </div>
      </div>
    </div>`;
  requestAnimationFrame(()=>{ const el=document.getElementById('new-nom'); if(el) el.focus(); });
}
async function submitCreateRef(){
  const g = (id)=>document.getElementById(id);
  const body = {
    nom: g('new-nom').value.trim(),
    acronyme: g('new-acr').value.trim(),
    categorie: g('new-cat').value,
    definition: g('new-def').value.trim(),
    position_sifa: g('new-pos').value,
    statut_sifa: g('new-stat').value,
    source_url: g('new-src').value.trim(),
    tags: g('new-tags').value,
  };
  if(!body.nom){ showToast('Nom obligatoire','danger'); return; }
  if(!body.definition){ showToast('Définition obligatoire','danger'); return; }
  const r = await api('/api/qualite/ref/fiches', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  if(!r.ok){ showToast('Erreur création','danger'); return; }
  const j = await r.json();
  closeMroot();
  showToast('Fiche créée en brouillon.','success');
  await loadRefFiches();
  openRef(j.id);
}

// ─── Raccourci clavier "/" pour focus recherche ───────────────────────────
document.addEventListener('keydown', function(ev){
  if(ev.key !== '/') return;
  const t = ev.target;
  if(t && (t.tagName==='INPUT' || t.tagName==='TEXTAREA' || t.isContentEditable)) return;
  const el = document.getElementById('ref-search');
  if(el && S.view==='ref-list'){ ev.preventDefault(); el.focus(); el.select(); }
});

init();
</script>
</body>
</html>
"""
