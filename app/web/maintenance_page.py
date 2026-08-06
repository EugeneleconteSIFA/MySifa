"""MySifa — Page Maintenance
Route : /maintenance

Contrôle d'accès multi-rôle :
- Admin (accès complet) : superadmin, direction, administration.
- Opérateur (vue « Mes tâches ») : rôle fabrication.
Le rôle effectif (admin / operator) est injecté dans le tag racine via
l'attribut data-maint-role, ce qui permet au CSS et au JS de la page de
basculer l'affichage entre les vues admin et opérateur sans deux templates
séparés.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from app.services.auth_service import get_current_user, effective_role
from app.web.access_denied import access_denied_response
from config import (
    APP_VERSION,
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_ADMINISTRATION_VENTES,
    ROLE_ADMINISTRATION_TECHNIQUE,
    ROLE_FABRICATION,
)

# v2.2.46 : inclut les 2 sous-rôles administration modernes (ventes/technique)
# qui manquaient et provoquaient un "Accès refusé" pour ces admins.
_MAINTENANCE_ADMIN_ROLES = {
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_ADMINISTRATION_VENTES,
    ROLE_ADMINISTRATION_TECHNIQUE,
}


def _get_maintenance_role(user: dict) -> Optional[str]:
    """Retourne 'admin', 'operator' ou None selon le rôle effectif de l'user.

    - 'admin'    : superadmin, direction, administration.
    - 'operator' : fabrication.
    - None       : pas d'accès (déclencher access_denied_response).

    Utilise `effective_role()` pour respecter l'impersonation : un superadmin
    qui simule un rôle `fabrication` doit voir la vue opérateur, pas celle
    d'admin.
    """
    if not user:
        return None
    role = effective_role(user)
    if role in _MAINTENANCE_ADMIN_ROLES:
        return "admin"
    if role == ROLE_FABRICATION:
        return "operator"
    return None


def _has_maintenance_access(user: dict) -> bool:
    """Compat : True dès que l'user a un rôle maintenance quelconque."""
    return _get_maintenance_role(user) is not None


router = APIRouter()


@router.get("/maintenance", response_class=HTMLResponse)
def maintenance_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/maintenance", status_code=302)
        raise
    maint_role = _get_maintenance_role(user)
    if maint_role is None:
        return access_denied_response("Maintenance")
    html = (
        MAINTENANCE_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
        .replace("__MAINT_ROLE__", maint_role)
    )
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
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
<link rel="stylesheet" href="/static/mysifa_timepicker.css?v=1.0">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<style>
/* ── Toggle Colonnes produit dans l'historique des contrôles ── */
.ctrl-extra-toggle{display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;transition:all .15s;user-select:none}
.ctrl-extra-toggle:hover{border-color:var(--accent);color:var(--text)}
.ctrl-extra-toggle-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--muted);transition:background .15s}
.ctrl-extra-toggle-on{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.ctrl-extra-toggle-on .ctrl-extra-toggle-dot{background:var(--accent)}
.ctrl-extra-toggle-state{font-weight:700;letter-spacing:.4px}

/* ── Colonne Dossier dans l'historique des contrôles ── */
.col-dossier{white-space:nowrap}
.col-nodos{white-space:nowrap}
.ctrl-row-nc td{background:rgba(248,113,113,0.06);border-top:1px solid rgba(248,113,113,0.18);border-bottom:1px solid rgba(248,113,113,0.18)}
.ctrl-row-nc td:first-child{border-left:3px solid var(--danger)}
.ctrl-row-nc:hover td{background:rgba(248,113,113,0.11)}
.ctrl-row-nc td:first-child::before{content:"⚠ ";color:var(--danger);font-weight:900;margin-right:4px}
.ctrl-dossier-pill{display:inline-block;padding:2px 8px;border-radius:5px;background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.2px;border:1px solid transparent;transition:border-color .15s}
tr:hover .ctrl-dossier-pill{border-color:var(--accent);cursor:pointer}
.ctrl-dossier-empty{color:var(--muted);font-size:12px}
/* ── Contexte dossier + fiche technique dans le détail d'un contrôle ── */
.ack-di-wrap{margin-top:6px}
.ack-di-head{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:8px}
.ack-di-badge{display:inline-block;padding:3px 9px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700;letter-spacing:.3px}
.ack-di-badge-sub{display:inline-block;padding:3px 9px;border-radius:6px;background:var(--bg);border:1px solid var(--border);color:var(--text2);font-size:11px;font-weight:600}
.ack-di-section{margin-top:8px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg)}
.ack-di-title{font-size:10px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.ack-di-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px 12px}
.ack-di-kv{display:flex;flex-direction:column;gap:1px;min-width:0}
.ack-di-k{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.3px}
.ack-di-v{font-size:12px;color:var(--text);font-weight:600;word-break:break-word}
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
.nav-sep{height:1px;background:var(--border);margin:10px 4px 12px}
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
.filter-input{background:#ffffff;border:1.5px solid var(--border);border-radius:10px;padding:10px 14px;color:#0f172a;font-size:13px;font-family:inherit;outline:none;min-height:40px;box-sizing:border-box;transition:border-color .15s,box-shadow .15s;min-width:132px}
.filter-input::placeholder{color:#64748b}
.filter-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.filters .filter-input[type=date]{min-width:128px;padding:9px 10px;font-size:12px;color:#0f172a}
.filters .filter-input[type=date]::-webkit-calendar-picker-indicator{filter:none;opacity:.6}
select.filter-input{appearance:none;background-color:#ffffff;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px;cursor:pointer;color:#0f172a}
select.filter-input option{background:#ffffff;color:#0f172a}
.filters-apply-btn{background:var(--accent);color:var(--accent-fg,var(--bg));border:none;border-radius:10px;padding:10px 18px;font-size:13px;font-weight:700;min-height:40px;cursor:pointer;font-family:inherit;align-self:flex-end;transition:filter .15s,box-shadow .15s,transform .05s;white-space:nowrap}
.filters-apply-btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px var(--accent-bg)}
.filters-apply-btn:active{transform:translateY(1px)}
.filters-date-presets{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:10px 0 0;margin-top:12px;border-top:1px dashed var(--border)}
.filters-date-presets-label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-right:4px;padding-top:8px}
/* v2.7.4 : background:transparent laissait remonter le fond de page (--bg),
   donc des puces bleues sur un fond bleu. var(--card) les detache : blanches
   en mode clair, gris fonce en mode sombre. L'etat .active garde sa teinte
   d'accent, c'est lui qui doit trancher avec les autres. */
.date-preset-chip{padding:5px 12px;font-size:11px;font-weight:600;border-radius:14px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;white-space:nowrap;transition:all 120ms;margin-top:6px}
.date-preset-chip:hover{border-color:var(--accent);color:var(--accent)}
.date-preset-chip.active{font-weight:700;border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
@media(max-width:560px){.filter-group{flex:1 1 100%}.filter-input,select.filter-input{min-width:0;width:100%}.filters-apply-btn{width:100%}}

/* ── Calendrier Planning (style MyProd) ──────────────────────────────── */
.cal-sec{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:28px}
.cal-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px}
.cal-title{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:700;color:var(--text);letter-spacing:.2px;text-transform:capitalize;font-family:"SFMono-Regular",ui-monospace,"Cascadia Mono",Menlo,Consolas,monospace}
.cal-controls{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.cal-view-tabs{display:flex;gap:0;align-items:center}
.cal-view-tab{padding:6px 14px;background:var(--card);border:1px solid var(--border);color:var(--muted);cursor:pointer;font-size:12px;font-family:inherit;font-weight:600;transition:all .15s}
.cal-view-tab:first-child{border-radius:8px 0 0 8px}
.cal-view-tab:last-child{border-radius:0 8px 8px 0}
.cal-view-tab:not(:first-child){margin-left:-1px}
.cal-view-tab.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);z-index:1;position:relative}
.cal-view-tab:hover:not(.active):not([disabled]){background:var(--border);color:var(--text2)}
.cal-view-tab[disabled]{opacity:.4;cursor:not-allowed}
.cal-nav{display:flex;gap:0;align-items:center}
.cal-nav button{padding:6px 12px;background:var(--card);border:1px solid var(--border);color:var(--muted);cursor:pointer;font-size:14px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;transition:background .15s,color .15s}
.cal-nav button:first-child{border-radius:8px 0 0 8px}
.cal-nav button:last-child{border-radius:0 8px 8px 0}
.cal-nav button:not(:first-child){margin-left:-1px}
.cal-nav button:hover{background:var(--accent-bg);color:var(--accent)}
.cal-nav .today{padding:6px 16px;font-size:12px;font-weight:600;font-family:inherit;color:var(--text2)}
.cal-week-head{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:8px}
.cal-wday{text-align:center;padding:8px 0;font-size:11px;font-weight:700;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;border-bottom:1px solid var(--border)}
.cal-wday.sat,.cal-wday.sun{color:#a78bfa}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);grid-auto-rows:minmax(110px,1fr);gap:6px}
.cal-cell{position:relative;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 10px 8px 14px;min-height:120px;display:flex;flex-direction:column;gap:6px;transition:background .15s,border-color .15s,box-shadow .15s;overflow:hidden}
.cal-cell:hover{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.cal-cell.cal-off{background:transparent;opacity:.55}
.cal-cell.cal-off .cal-day-num{color:var(--muted)}
.cal-cell.cal-weekend{background:rgba(167,139,250,.04)}
.cal-cell.cal-today{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.cal-day-num{font-size:13px;font-weight:700;color:var(--text);font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;line-height:1}
.cal-cell.cal-today .cal-day-num{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--accent);color:var(--accent-fg,#fff);font-size:12px}
.cal-day-events{display:flex;flex-direction:column;gap:4px;flex:1;overflow:hidden}
.cal-cell-clickable{cursor:copy}
.cal-cell-has-events{position:relative}
.cal-cell-has-events::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cal-cell-accent,var(--accent));border-radius:10px 0 0 10px;pointer-events:none}
.cal-day-event{display:flex;align-items:center;gap:6px;padding:4px 8px;border-radius:6px;font-size:11.5px;font-weight:700;line-height:1.2;cursor:pointer;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.18);transition:filter .12s,transform .08s}
.cal-day-event:hover{filter:brightness(1.10);transform:translateX(1px)}
.cal-day-event:active{transform:scale(.98)}
.cal-day-event-time{font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;font-size:10.5px;font-weight:800;opacity:.92;flex-shrink:0;letter-spacing:.2px}
.cal-day-event-machine{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:700;letter-spacing:.1px}
.cal-day-event-more{font-size:11px;color:var(--muted);font-weight:700;font-style:italic;padding:3px 8px;border-radius:5px;background:transparent;cursor:pointer;border:1px dashed var(--border);text-align:center;transition:all .12s}
.cal-day-event-more:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.cal-event-empty{font-size:10px;color:var(--muted);font-style:italic;opacity:.6}
.cal-legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:18px;padding-top:14px;border-top:1px solid var(--border)}
.cal-legend-item{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--muted);font-weight:600}
.cal-legend-dot{display:inline-block;width:10px;height:10px;border-radius:3px;border:1px solid var(--border);background:var(--bg)}
.cal-legend-dot.today{background:var(--accent);border-color:var(--accent)}
.cal-legend-dot.off{opacity:.4}
.cal-legend-dot.weekend{background:rgba(167,139,250,.18);border-color:rgba(167,139,250,.4)}
@media(max-width:720px){
  .cal-grid{grid-auto-rows:minmax(78px,1fr);gap:4px}
  .cal-cell{min-height:78px;padding:6px 7px}
  .cal-day-num{font-size:11px}
  .cal-title{font-size:15px}
  .cal-week-head{gap:4px}
  .cal-wday{font-size:10px;padding:6px 0}
}

/* ── v2.6.0 : etats de chargement du calendrier ─────────────────────── */
/* v2.6.1 : .cal-hide-hint masquait le bandeau d'aide pendant le chargement et en erreur ; le bandeau n'existe plus. La classe reste posee par _renderPlanningLoadState() (inoffensive) au cas ou un futur bandeau la reutiliserait. */
.cal-load-bar{display:flex;align-items:center;gap:10px;padding:10px 14px;margin-bottom:12px;border-radius:10px;font-size:12.5px;font-weight:600;letter-spacing:.2px}
.cal-load-bar.is-loading{background:var(--accent-bg);border:1px dashed var(--accent);color:var(--accent)}
.cal-load-bar.is-error{background:rgba(248,113,113,.10);border:1px solid var(--danger);color:var(--danger)}
.cal-load-bar-txt{flex:1;min-width:0}
.cal-load-spin{flex-shrink:0;width:14px;height:14px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:calLoadSpin .7s linear infinite}
@keyframes calLoadSpin{to{transform:rotate(360deg)}}
.cal-load-retry{flex-shrink:0;padding:6px 13px;border-radius:8px;border:1px solid var(--danger);background:var(--danger);color:#fff;font-family:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:filter .12s}
.cal-load-retry:hover{filter:brightness(1.1)}
/* Blocs fantomes pendant le tout premier chargement : la grille ne peut plus
   etre confondue avec un planning vide. Non cliquables, non selectionnables. */
.cal-skel{position:absolute;border-radius:7px;pointer-events:none;user-select:none;
  background:linear-gradient(90deg,rgba(148,163,184,.13) 25%,rgba(148,163,184,.24) 37%,rgba(148,163,184,.13) 63%);
  background-size:400% 100%;animation:calSkel 1.3s ease-in-out infinite}
body.light .cal-skel{background:linear-gradient(90deg,rgba(100,116,139,.11) 25%,rgba(100,116,139,.20) 37%,rgba(100,116,139,.11) 63%);background-size:400% 100%}
@keyframes calSkel{0%{background-position:100% 0}100%{background-position:0 0}}
.cal-skel-chip{height:16px;border-radius:5px;margin-bottom:4px;position:static}
@media (prefers-reduced-motion:reduce){
  .cal-skel{animation:none}
  .cal-load-spin{animation-duration:2s}
}
body.reduce-anim .cal-skel{animation:none}

/* ── Vue Semaine (emploi du temps) ──────────────────────────────────── */
.cal-week-view{overflow-x:auto}
/* v2.6.1 : .cal-wv-hint retire du HTML — regle de style supprimee. */
/* v2.6.1 : bandes de bascule de semaine pendant un glisser-deposer. Le liseré
   marque le bord vise ; la semaine change apres CAL_EDGE_DELAY_MS. box-shadow
   inset est peint sur la padding-box : il ne defile pas avec le contenu. */
.cal-wv-body{transition:box-shadow .12s}
.cal-wv-body.cal-edge-prev{box-shadow:inset 5px 0 0 var(--accent)}
.cal-wv-body.cal-edge-next{box-shadow:inset -5px 0 0 var(--accent)}
/* v2.7.1 : bord ROUGE = la bascule de periode est verrouillee pour l'occurrence
   en cours de deplacement (elle doit rester dans sa semaine / son mois). */
.cal-wv-body.cal-edge-blocked-prev{box-shadow:inset 5px 0 0 var(--danger,#f87171)}
.cal-wv-body.cal-edge-blocked-next{box-shadow:inset -5px 0 0 var(--danger,#f87171)}
/* v2.6.1 : colonnes de dates passees — ni creation ni depot. Trame legere pour
   que le refus soit lisible AVANT le geste, pas seulement apres. */
.cal-wv-day-col.is-past-col{background-image:repeating-linear-gradient(45deg,transparent,transparent 7px,rgba(128,128,128,.055) 7px,rgba(128,128,128,.055) 14px);cursor:not-allowed}
.cal-wv-day-col.cal-col-nodrop{box-shadow:inset 0 0 0 2px var(--danger,#f87171)}
.cal-wv-header{display:grid;grid-template-columns:78px repeat(7,minmax(0,1fr));gap:0;margin-bottom:0;border-bottom:1px solid var(--border);box-sizing:border-box}  /* v2.5.17 : min-width retire (dim clippe). v2.6.0 : scrollbar-gutter retire -- inerte ici, la propriete ne s'applique qu'aux conteneurs de scroll, donc les 7 colonnes 1fr etaient calculees sur une largeur superieure a celles du corps (derive cumulative vers Sam/Dim). L'alignement est desormais fait par _syncCalHeaderGutter() qui reporte la largeur reelle de la gouttiere du corps sur le padding-right du header. */
.cal-wv-corner{}
.cal-wv-dayhead{padding:11px 10px;text-align:center;border-left:1px solid var(--border);display:flex;flex-direction:column;align-items:center;gap:3px;background:var(--card)}
.cal-wv-dayhead.weekend{background:rgba(167,139,250,.06)}
.cal-wv-dayhead.today{background:var(--accent-bg)}
.cal-wv-dayname{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace}
.cal-wv-dayhead.weekend .cal-wv-dayname{color:#a78bfa}
.cal-wv-dayhead.today .cal-wv-dayname{color:var(--accent)}
.cal-wv-daydate{font-size:17px;font-weight:800;color:var(--text);font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;letter-spacing:.3px}
.cal-wv-dayhead.today .cal-wv-daydate{color:var(--accent)}
.cal-wv-body{display:grid;grid-template-columns:78px repeat(7,minmax(0,1fr));gap:0;position:relative;overflow:auto;max-height:calc(100vh - 330px);min-height:260px;scrollbar-gutter:stable}  /* v2.5.17. v2.6.1 : 75vh -> calc() comme valeur d'amorce avant que _fitCalWeekBody() ne pose la hauteur exacte en inline. 330px = ordre de grandeur de tout ce qui entoure la grille (en-tete de page, sous-onglets, bandeau, en-tete de grille, legende, paddings) : evite un flash de grille trop haute au premier rendu. */
.cal-wv-times-col{display:flex;flex-direction:column}
.cal-wv-time{height:62px;display:flex;align-items:flex-start;justify-content:flex-end;padding:3px 10px 0 0;font-size:12px;font-weight:700;color:var(--muted);font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;border-right:1px solid var(--border);border-top:1px solid var(--border)}
.cal-wv-time:first-child{border-top:none}
.cal-wv-day-col{position:relative;display:flex;flex-direction:column;border-left:1px solid var(--border);min-height:100%}
.cal-wv-day-col.weekend{background:rgba(167,139,250,.04)}
.cal-wv-day-col.today{background:var(--accent-bg)}
/* v2.2.53 : min-width:0 + overflow:hidden empêche les chips d'étirer la colonne */
.cal-wv-day-col{min-width:0}
/* v2.7.3 : puces des operations non planifiees. Le conteneur repliable qui les
   portait (absolu au sommet de chaque colonne de jour) a ete remplace par la
   bande .cal-wv-allday, hors zone de scroll. Seules les regles des puces
   restent : la bande les reutilise telles quelles. */
.cal-wv-nonpl-chip{display:block;padding:4px 8px;border-radius:5px;background:rgba(148,163,184,.15);color:var(--text2);border-left:3px solid var(--muted);font-size:11px;font-weight:600;cursor:pointer;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;max-width:100%;width:100%;box-sizing:border-box;transition:background .15s,color .15s}
.cal-wv-nonpl-chip:hover{background:rgba(148,163,184,.28);color:var(--text)}
.cal-wv-nonpl-chip[data-statut="termine"]{background:rgba(52,211,153,.15);color:var(--ok,#059669);border-left-color:var(--ok,#34d399)}
.cal-wv-nonpl-chip[data-statut="termine"]:hover{background:rgba(52,211,153,.28)}
.cal-wv-nonpl-chip .cal-wv-nonpl-icon{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--muted);margin-right:5px;vertical-align:middle;flex-shrink:0}
.cal-wv-nonpl-chip[data-statut="termine"] .cal-wv-nonpl-icon{background:var(--ok,#34d399)}
/* v2.7.3 : bande « non planifie ». Le bandeau precedent vivait en
   position:absolute au sommet de chaque colonne de jour, DANS la zone de
   defilement. Tant que la grille allait de 6h a 21h, « en haut » restait a
   portee ; depuis le passage en journee complete, le sommet de colonne est
   00:00, soit ~1490px au-dessus de la zone que le calendrier recentre — les
   operations non planifiees etaient invisibles sans remonter jusqu'a minuit.
   La bande est desormais un troisieme frere de .cal-wv-header /
   .cal-wv-body : meme grille de colonnes, mais HORS du conteneur de scroll,
   donc toujours a l'ecran. Elle ne peut pas etre simplement sticky dans la
   colonne : sticky implique d'etre dans le flux, ce qui decalerait les lignes
   horaires et casserait leur alignement avec la colonne des heures. */
.cal-wv-allday{display:grid;grid-template-columns:78px repeat(7,minmax(0,1fr));gap:0;box-sizing:border-box;border-bottom:1px solid var(--border);background:var(--card)}
.cal-wv-allday[hidden]{display:none}
.cal-wv-allday-corner{display:flex;flex-direction:column;align-items:flex-start;justify-content:center;gap:3px;padding:6px 6px 6px 8px;border:0;background:rgba(148,163,184,.05);color:var(--muted);font-family:inherit;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;line-height:1.15;text-align:left;cursor:pointer;user-select:none;transition:background .12s,color .12s}
.cal-wv-allday-corner:hover{background:rgba(148,163,184,.12);color:var(--text2)}
.cal-wv-allday-corner-top{display:flex;align-items:center;gap:4px;min-width:0}
.cal-wv-allday-chev{transition:transform .18s;flex-shrink:0}
.cal-wv-allday.is-open .cal-wv-allday-chev{transform:rotate(90deg)}
.cal-wv-allday-total{font-size:10px;font-weight:800;color:var(--accent);letter-spacing:0}
.cal-wv-allday-cell{display:flex;flex-direction:column;gap:3px;padding:5px 4px;border-left:1px solid var(--border);min-width:0;max-height:132px;overflow-y:auto;overflow-x:hidden}
/* Sans flex:0 0 auto, les puces se compriment quand le contenu depasse
   max-height : au lieu de defiler, la colonne ecrase 13 puces en bandes de
   10px illisibles (constate au harnais de rendu). */
.cal-wv-allday-cell > *{flex:0 0 auto}
.cal-wv-allday-cell.weekend{background:rgba(167,139,250,.04)}
.cal-wv-allday-cell.today{background:var(--accent-bg)}
/* Replie : les puces disparaissent, seule la pastille de comptage reste. */
.cal-wv-allday:not(.is-open) .cal-wv-allday-cell{max-height:none;overflow:visible;padding:4px}
.cal-wv-allday:not(.is-open) .cal-wv-nonpl-chip{display:none}
.cal-wv-allday-pill{display:none;align-self:flex-start;padding:2px 7px;border-radius:9px;background:rgba(148,163,184,.2);color:var(--text2);font-size:10px;font-weight:800;line-height:1.5;cursor:pointer;border:0;font-family:inherit}
.cal-wv-allday-pill:hover{background:rgba(148,163,184,.34);color:var(--text)}
.cal-wv-allday:not(.is-open) .cal-wv-allday-pill{display:inline-block}
/* Vue Jour : une seule colonne, on peut se permettre le rendu enrichi. */
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell{max-height:200px;padding:8px 10px;gap:6px}
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell .cal-wv-nonpl-chip{display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;font-size:13px;white-space:normal;line-height:1.4}
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell .cal-wv-nonpl-chip-main{flex:1;min-width:0;font-weight:700;color:var(--text)}
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell .cal-wv-nonpl-chip-sub{font-size:11px;color:var(--muted);font-weight:500;margin-top:2px}
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell .cal-wv-nonpl-chip-time{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;color:var(--text2);white-space:nowrap;flex-shrink:0}
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell .cal-wv-nonpl-chip-status{width:18px;height:18px;border-radius:50%;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;background:var(--bg);border:1.5px solid var(--border)}
.cal-week-view.cal-wv-mode-day .cal-wv-allday-cell .cal-wv-nonpl-chip[data-statut="termine"] .cal-wv-nonpl-chip-status{background:var(--ok,#34d399);border-color:var(--ok,#34d399);color:#fff}
/* v2.7.3 fix : les regles mode-jour ci-dessus pesent 4 classes, alors que la
   regle de masquage `.cal-wv-allday:not(.is-open) .cal-wv-nonpl-chip` n'en pese
   que 3 (:not() ne compte que son argument). En vue Jour, replier la bande ne
   masquait donc rien : le chevron tournait, la pastille de comptage
   apparaissait, mais les puces restaient affichees — etat visuellement
   contradictoire. On repose le masquage et la geometrie repliee au meme niveau
   de specificite que le mode jour, apres lui. */
.cal-week-view.cal-wv-mode-day .cal-wv-allday:not(.is-open) .cal-wv-allday-cell .cal-wv-nonpl-chip{display:none}
.cal-week-view.cal-wv-mode-day .cal-wv-allday:not(.is-open) .cal-wv-allday-cell{max-height:none;overflow:visible;padding:4px;gap:3px}
.cal-wv-hour-row{height:62px;border-top:1px solid var(--border);transition:background .12s}
.cal-wv-hour-row:first-child{border-top:none}
.cal-wv-day-col.drag-over{background:var(--accent-bg);outline:2px dashed var(--accent);outline-offset:-2px;z-index:1}
/* v2.5.14 : drag & drop planning maintenance */
.cal-event.is-closed{opacity:.72}
.cal-event-closed-badge{display:inline-block;font-size:9px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;padding:1px 6px;border-radius:4px;background:rgba(148,163,184,.22);color:var(--text2,var(--muted));margin-left:6px;vertical-align:middle}
.plan-det-closed{margin-top:14px;padding:12px 14px;border-radius:8px;background:rgba(148,163,184,.10);border:1px solid var(--border);color:var(--text2,var(--muted));font-size:13px;line-height:1.5}
.plan-det-closed strong{color:var(--text)}
.cal-event[data-draggable="1"]{cursor:grab}
.cal-event[data-draggable="1"]:active{cursor:grabbing}
.cal-event.is-past{cursor:not-allowed}
/* v2.5.28 : boutons quick-select operateurs. v2.6.0 : « Travaillant ce jour » retire. */
.case-op-quick-btn{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:6px 12px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .12s,transform .06s;white-space:nowrap}
.case-op-quick-btn:hover{filter:brightness(1.08)}
.case-op-quick-btn:active{transform:scale(.97)}
.case-op-quick-btn:disabled{opacity:.5;cursor:wait}
/* v2.5.26 : pictogramme triangle warning -- plus visible qu'un badge cercle */
/* v2.6.0 : couleurs FIXES, volontairement hors variables de theme.
   Le badge est pose sur un bloc dont le fond vient de CAL_MACHINE_PALETTE
   (#0891b2, #7c3aed, #ea580c, #059669), lui aussi code en dur et independant
   du theme : une couleur de theme n'a donc aucun moyen de garantir le
   contraste. C'est exactement ce qui clochait -- `var(--warn)` vaut #4A8FE8
   (bleu) sur le theme MyMaintenance, donc le badge sortait bleu sur violet.
   Blanc + triangle rouge plein : lisible sur les cinq fonds possibles. */
.cal-event .cal-event-noop{position:absolute;top:4px;left:4px;width:26px;height:26px;background:#ffffff;border:2px solid #dc2626;border-radius:7px;display:inline-flex;align-items:center;justify-content:center;box-shadow:0 2px 10px rgba(0,0,0,.5);cursor:help;z-index:6;padding:3px;transition:transform .15s,filter .15s;animation:calNoopPulse 1.8s ease-in-out infinite}
.cal-event .cal-event-noop svg{width:100%;height:100%;display:block}
/* Liseré rouge sur tout le bloc : le créneau se repère sans chercher le badge. */
.cal-event.has-no-op{outline:2px solid #dc2626;outline-offset:-2px}
/* Le contenu est centré : on lui réserve de la marge des deux côtés pour qu'il
   ne passe jamais sous le badge (cas des créneaux d'une heure ou moins). */
.cal-event.has-no-op{padding-left:32px;padding-right:32px}
.cal-event[data-mini="1"] .cal-event-noop{width:20px;height:20px;top:2px;left:2px;padding:2px;border-radius:5px}
.cal-event[data-mini="1"].has-no-op{padding-left:24px;padding-right:24px}
.cal-event .cal-event-noop:hover{transform:scale(1.15);filter:brightness(1.05);animation:none}
@keyframes calNoopPulse{0%,100%{box-shadow:0 2px 10px rgba(0,0,0,.5),0 0 0 0 rgba(220,38,38,.75)}50%{box-shadow:0 2px 10px rgba(0,0,0,.5),0 0 0 7px rgba(220,38,38,0)}}
.cal-event.is-past::before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(45deg,transparent,transparent 8px,rgba(255,255,255,.06) 8px,rgba(255,255,255,.06) 16px);pointer-events:none;border-radius:inherit}
/* v2.5.16 : drag live -- le bloc reste visible et bouge vraiment (comme Google Calendar).
   La bordure et l'ombre appuyees signalent l'etat 'drag actif'. */
.cal-event.is-dragging{pointer-events:none;box-shadow:0 12px 32px rgba(0,0,0,.45),0 0 0 2px var(--accent);z-index:10;filter:brightness(1.08)}
.cal-event .cal-event-resize-handle{position:absolute;left:6px;right:6px;height:6px;cursor:ns-resize;z-index:5}
.cal-event .cal-event-resize-handle.top{top:0}
.cal-event .cal-event-resize-handle.bottom{bottom:0}
.cal-event .cal-event-resize-handle:hover{background:rgba(255,255,255,.25)}
/* Ghost preview (suit le curseur) */
.cal-drag-ghost{position:fixed;pointer-events:none;background:var(--card);border:2px dashed var(--accent);border-radius:8px;padding:6px 10px;font-family:'Segoe UI',system-ui,sans-serif;font-size:12px;font-weight:700;color:var(--text);z-index:99999;box-shadow:0 8px 24px rgba(0,0,0,.35);white-space:nowrap;transition:transform .08s}
.cal-drag-ghost .cal-drag-ghost-time{display:block;font-family:'SFMono-Regular',ui-monospace,Consolas,monospace;color:var(--accent);font-size:13px;margin-top:2px}
/* Nav buttons highlighted comme drop zones cross-week */
.cal-nav button.cal-drop-target-nav{background:var(--accent);color:var(--accent-fg,#0a0e17);animation:calDropPulse .6s ease-in-out infinite alternate}
@keyframes calDropPulse{from{box-shadow:0 0 0 0 rgba(34,211,238,.6)}to{box-shadow:0 0 0 8px rgba(34,211,238,0)}}
/* v2.5.22 : container queries -- le contenu s'adapte a la taille reelle de la case */
.cal-event{position:absolute;background:var(--cal-ev-bg,var(--accent));color:var(--cal-ev-fg,#fff);border-radius:7px;padding:5px 8px;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;font-weight:700;line-height:1.25;cursor:pointer;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.24);border:1px solid rgba(255,255,255,.20);z-index:2;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:2px;transition:filter .12s,box-shadow .12s,transform .08s;container-type:size;container-name:calev}
/* Base : que le titre est visible, taille reduite. Les autres apparaissent progressivement. */
.cal-event .cal-event-title{font-weight:800;font-size:11.5px;letter-spacing:.1px;color:inherit;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;text-overflow:ellipsis;word-break:normal;overflow-wrap:break-word;line-height:1.2;width:100%;max-width:100%}
.cal-event .cal-event-sub,.cal-event .cal-event-time,.cal-event .cal-event-count{display:none;font-weight:600;color:inherit;opacity:.9;width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cal-event .cal-event-sub{font-size:11px;opacity:.85}
.cal-event .cal-event-time{font-size:11px;font-family:'SFMono-Regular',ui-monospace,Consolas,monospace;letter-spacing:.2px}
.cal-event .cal-event-count{font-size:10.5px;opacity:.75;font-style:italic}
/* Cases plus larges : nom un peu plus gros + une seule ligne si tres large */
@container calev (min-width: 90px){
  .cal-event .cal-event-title{font-size:13px}
}
@container calev (min-width: 130px){
  .cal-event .cal-event-title{font-size:14px}
}
/* Cases moyennes (assez hautes) : ajoute la machine en sous-titre */
@container calev (min-height: 60px) and (min-width: 90px){
  .cal-event .cal-event-sub{display:block}
}
/* Cases hautes : ajoute les horaires */
@container calev (min-height: 90px) and (min-width: 90px){
  .cal-event .cal-event-time{display:block}
}
/* Cases tres hautes : ajoute le compteur d'ops */
@container calev (min-height: 130px) and (min-width: 100px){
  .cal-event .cal-event-count{display:block}
}
/* v2.5.24 : cases etroites -> reduit encore la police pour eviter le wrap ugly.
   Plus la case est fine, plus la police baisse, avec ajustement du line-clamp
   pour autoriser plus de lignes quand la hauteur le permet. */
@container calev (max-width: 70px){
  .cal-event{padding:4px 5px;gap:1px}
  .cal-event .cal-event-title{font-size:10.5px;line-height:1.15;letter-spacing:0}
}
@container calev (max-width: 50px){
  .cal-event{padding:3px 4px}
  .cal-event .cal-event-title{font-size:9.5px;-webkit-line-clamp:3}
}
/* Case tres etroite ET tres haute : autorise 4 lignes pour maximiser lecture */
@container calev (max-width: 70px) and (min-height: 140px){
  .cal-event .cal-event-title{-webkit-line-clamp:4}
}
/* Fallback pour navigateurs sans container queries : les infos secondaires restent cachees
   -- le titre suffit largement dans ce cas. */
.cal-event:hover{filter:brightness(1.10);box-shadow:0 4px 14px rgba(0,0,0,.36);z-index:4}
.cal-event:active{transform:scale(.99)}
.cal-event-machine{font-size:12.5px;font-weight:700;opacity:.96;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:inline-flex;align-items:center;gap:4px}
/* v2.2.51 : ops list dans cal-event = scrollable + texte wrapable */
.cal-event-ops{display:flex;flex-direction:column;gap:2px;flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.35) transparent}
.cal-event-ops::-webkit-scrollbar{width:5px}
.cal-event-ops::-webkit-scrollbar-track{background:transparent}
.cal-event-ops::-webkit-scrollbar-thumb{background:rgba(255,255,255,.30);border-radius:3px}
.cal-event-ops::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.5)}
.cal-event-op{font-size:12.5px;font-weight:600;line-height:1.3;color:inherit;opacity:.96;white-space:normal;overflow-wrap:break-word;word-break:normal;letter-spacing:.1px;padding-right:2px}  /* v2.5.19 : preserve les mots entiers */
.cal-event-op-more{opacity:.75;font-style:italic;font-size:11.5px}
/* v2.5.20 : sous-titre "Afficher les details" -- discret, sous le titre */
.cal-event-op-more{font-size:11.5px;font-style:italic;opacity:.78;font-weight:600}
.cal-event[data-mini="1"]{padding:5px 7px;border-radius:6px;gap:2px}
.cal-event[data-mini="1"] .cal-event-title{font-size:12.5px;letter-spacing:.1px}
.cal-event[data-mini="1"] .cal-event-machine{font-size:11px}
.cal-event[data-mini="1"] .cal-event-time{font-size:11px}
.cal-event[data-mini="1"] .cal-event-op{font-size:11px;line-height:1.25}
.cal-event[data-niveau="1"]{background:#22d3ee;color:#062430}
.cal-event[data-niveau="2"]{background:#fbbf24;color:#3b2300}
.cal-event[data-niveau="3"]{background:#f87171;color:#3b0a0a}
/* Bloc fusionné (plusieurs opérations chevauchantes sur la même case) */
.cal-event.cal-event-merged{background:linear-gradient(180deg,var(--accent-bg) 0%,rgba(255,255,255,0) 100%),var(--card);color:var(--text);border:2px solid var(--accent);border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,.18);padding:8px 10px 10px;overflow:hidden;display:flex;flex-direction:column;gap:8px}
.cal-event-merged-head{display:flex;align-items:center;justify-content:center;gap:6px;font-size:11px;font-weight:800;color:var(--accent-fg,#fff);background:var(--accent);font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;padding:4px 9px;border-radius:6px;letter-spacing:.3px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 1px 3px rgba(0,0,0,.15)}
.cal-event-list{display:flex;flex-direction:column;gap:5px;overflow:auto;flex:1;min-height:0;padding-right:2px}
.cal-event-item{display:flex;flex-direction:column;gap:4px;padding:6px 9px;border-radius:7px;font-size:12px;line-height:1.3;background:var(--card);border:1px solid var(--border);border-left:4px solid var(--accent);cursor:pointer;transition:filter .12s,border-color .12s,transform .08s}
.cal-event-item:hover{filter:brightness(.97);border-color:var(--accent)}
.cal-event-item:active{transform:scale(.99)}
.cal-event-item-time{display:inline-flex;align-items:center;gap:4px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;font-weight:700;font-size:11px;color:var(--accent);background:var(--accent-bg);padding:2px 7px;border-radius:5px;width:fit-content;letter-spacing:.2px}
.cal-event-item-name{font-weight:700;font-size:12px;color:var(--text);white-space:normal;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-word;line-height:1.3}
.cal-event-item-niv-1{border-left-color:#22d3ee;background:linear-gradient(90deg,rgba(34,211,238,.08) 0%,var(--card) 60%)}
.cal-event-item-niv-1 .cal-event-item-time{background:rgba(34,211,238,.22);color:#0891b2}
.cal-event-item-niv-2{border-left-color:#fbbf24;background:linear-gradient(90deg,rgba(251,191,36,.10) 0%,var(--card) 60%)}
.cal-event-item-niv-2 .cal-event-item-time{background:rgba(251,191,36,.25);color:#b45309}
.cal-event-item-niv-3{border-left-color:#f87171;background:linear-gradient(90deg,rgba(248,113,113,.10) 0%,var(--card) 60%)}
.cal-event-item-niv-3 .cal-event-item-time{background:rgba(248,113,113,.22);color:#b91c1c}
body:not(.light) .cal-event-item-niv-1 .cal-event-item-time{color:#67e8f9}
body:not(.light) .cal-event-item-niv-2 .cal-event-item-time{color:#fcd34d}
body:not(.light) .cal-event-item-niv-3 .cal-event-item-time{color:#fca5a5}
/* Mode vue Jour : 1 colonne large */
.cal-week-view.cal-wv-mode-day .cal-wv-header,
.cal-week-view.cal-wv-mode-day .cal-wv-allday,
.cal-week-view.cal-wv-mode-day .cal-wv-body{grid-template-columns:70px 1fr}
.cal-week-view.cal-wv-mode-day .cal-event{font-size:14.5px;padding:10px 14px}
.cal-week-view.cal-wv-mode-day .cal-event-title{font-size:16px}
.cal-week-view.cal-wv-mode-day .cal-event-machine{font-size:13.5px}
.cal-week-view.cal-wv-mode-day .cal-event-time{font-size:13.5px}
.cal-week-view.cal-wv-mode-day .cal-event-op{font-size:13.5px}
.cal-week-view.cal-wv-mode-day .cal-wv-daydate{font-size:20px}
.cal-week-view.cal-wv-mode-day .cal-wv-dayname{font-size:13px}
/* Hauteur d'heure plus aérée en vue Jour */
.cal-week-view.cal-wv-mode-day .cal-wv-time,
.cal-week-view.cal-wv-mode-day .cal-wv-hour-row{height:72px}
.cal-week-view.cal-wv-mode-day .cal-wv-header,
.cal-week-view.cal-wv-mode-day .cal-wv-allday,
.cal-week-view.cal-wv-mode-day .cal-wv-body{grid-template-columns:90px 1fr;min-width:0}
/* Modale Créneau : section liste d'opérations */
.case-modal-card{max-width:640px;width:92vw;max-height:92vh;display:flex;flex-direction:column}
/* Le <form> est intercalé entre .modal-card et .modal-body → doit propager
   le flex column pour que .modal-body puisse scroll et .modal-foot rester
   collé en bas. Sans ça, le contenu déborde et les boutons Enregistrer/Annuler
   sortent de l'écran (bug observé v2.1.5). */
.case-modal-card > form{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.case-modal-card .modal-body{overflow-y:auto;flex:1;min-height:0}
.case-modal-card .modal-foot{flex-shrink:0}
.case-ops-list{max-height:none}
.case-ops-section{margin-top:16px;border-top:1px solid var(--border);padding-top:14px}
.case-ops-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.case-ops-add-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;border-radius:8px;border:1.5px solid var(--accent);background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;transition:all .12s;letter-spacing:.2px}
.case-ops-add-btn:hover{background:var(--accent);color:var(--accent-fg,#fff)}
.case-ops-list{display:flex;flex-direction:column;gap:8px;max-height:280px;overflow:auto;padding:2px}
.case-ops-empty{padding:18px 14px;border:1px dashed var(--border);border-radius:8px;color:var(--muted);font-size:12px;text-align:center;font-style:italic;background:var(--bg)}
.case-ops-row{display:flex;flex-direction:column;gap:8px;padding:12px;border:1px solid var(--border);border-radius:10px;background:var(--bg)}
.case-ops-row-top{display:flex;align-items:center;gap:8px}
.case-ops-row .ops-select{flex:1;min-width:0}
.case-ops-row-del{flex-shrink:0;width:38px;height:38px;display:inline-flex;align-items:center;justify-content:center;padding:0;border:1px solid var(--border);background:var(--card);border-radius:8px;cursor:pointer;color:var(--muted);transition:all .12s}
.case-ops-row-del:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.10)}
.case-ops-machines{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.case-ops-machines-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);margin-right:4px}
.case-mach-chip{display:inline-flex;align-items:center;gap:5px;padding:5px 10px;border-radius:16px;border:1.5px solid var(--border);background:var(--card);color:var(--text2);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;transition:all .12s;user-select:none}
.case-mach-chip:hover{border-color:var(--accent);color:var(--text)}
.case-mach-chip.active{border-color:var(--accent);background:var(--accent);color:var(--accent-fg,#fff)}
.case-mach-chip.active:hover{filter:brightness(1.06)}
/* Vue opérateur : en-tête de groupe machine */
.op-machine-group{margin-top:16px}
.op-machine-group:first-child{margin-top:0}
.op-machine-group-head{display:flex;align-items:center;gap:8px;padding:8px 12px;margin-bottom:8px;border-radius:8px;background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:800;letter-spacing:.3px;text-transform:uppercase}
.op-machine-group-head .op-machine-dot{width:9px;height:9px;border-radius:50%;background:var(--accent)}
/* Détails créneau : badges machine par op */
.plan-det-case-op-mach-wrap{display:inline-flex;flex-wrap:wrap;gap:4px}
.plan-det-case-op-mach{display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700}
.cal-sec{position:relative}
/* Badge « depuis un modèle » sur un créneau */
.tmpl-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:12px;background:var(--warn);color:#0a0e17;font-size:11px;font-weight:800;letter-spacing:.2px}
.tmpl-badge svg{flex-shrink:0}
/* Modal Templates : liste + éditeur */
.tmpl-modal-card{max-width:720px;width:94vw}
.tmpl-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
.tmpl-list{display:flex;flex-direction:column;gap:8px;max-height:420px;overflow:auto;padding:2px}
.tmpl-item{display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid var(--border);border-radius:10px;background:var(--card);transition:border-color .12s}
.tmpl-item:hover{border-color:var(--accent)}
.tmpl-item-main{flex:1;min-width:0}
.tmpl-item-name{font-size:14px;font-weight:700;color:var(--text);margin-bottom:2px}
.tmpl-item-desc{font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tmpl-item-count{flex-shrink:0;font-size:11px;color:var(--text2);font-weight:600;padding:3px 9px;border-radius:6px;background:var(--bg)}
.tmpl-item-actions{display:flex;gap:4px;flex-shrink:0}
.tmpl-item-btn{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;padding:0;border-radius:8px;border:1px solid transparent;background:transparent;color:var(--muted);cursor:pointer;transition:all .12s;font-family:inherit}
.tmpl-item-btn:hover{background:var(--bg);border-color:var(--border)}
.tmpl-item-btn.edit:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.tmpl-item-btn.del:hover{color:var(--danger);border-color:var(--danger);background:rgba(248,113,113,.10)}
/* v2.4.29 — Bloc récurrence dans la modale template + panel Gestion des modèles */
.tmpl-recur-block{margin-top:14px;padding:14px 16px;background:var(--bg);border:1px solid var(--border);border-radius:10px}
.tmpl-recur-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}
.tmpl-recur-title{font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.tmpl-recur-toggle{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text2);cursor:pointer;user-select:none}
.tmpl-recur-toggle input{margin:0;cursor:pointer}
.tmpl-recur-fields{display:none;gap:10px;flex-wrap:wrap}
.tmpl-recur-fields.open{display:flex}
.tmpl-recur-field{display:flex;flex-direction:column;gap:4px;min-width:130px;flex:1}
.tmpl-recur-field label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.tmpl-recur-field select,.tmpl-recur-field input{padding:7px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--text);font-family:inherit;font-size:13px}
.tmpl-recur-field select:focus,.tmpl-recur-field input:focus{border-color:var(--accent);outline:none}
/* v2.5.13 : toggle switch pour l'activation de la recurrence (remplace la checkbox) */
.tmpl-recur-switch{display:inline-flex;align-items:center;gap:10px;cursor:pointer;user-select:none;font-size:12px;color:var(--text2);font-weight:600}
.tmpl-recur-switch input{position:absolute;opacity:0;width:0;height:0}
.tmpl-recur-slider{position:relative;display:inline-block;width:38px;height:20px;background:var(--border);border-radius:20px;transition:background .18s}
.tmpl-recur-slider::before{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;background:var(--card);border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .18s,background .18s}
.tmpl-recur-switch input:checked ~ .tmpl-recur-slider{background:var(--accent)}
.tmpl-recur-switch input:checked ~ .tmpl-recur-slider::before{transform:translateX(18px);background:#fff}
.tmpl-recur-switch input:focus-visible ~ .tmpl-recur-slider{box-shadow:0 0 0 3px rgba(34,211,238,.25)}
.tmpl-recur-switch:hover .tmpl-recur-slider{filter:brightness(1.08)}
.tmpl-recur-switch-lbl{transition:color .12s}
.tmpl-recur-switch input:checked ~ .tmpl-recur-switch-lbl{color:var(--accent)}
/* Panel "Gestion des modèles" sous l'historique — style aligné sur Gestion des alertes */
/* v2.5.18 : layout inspire des .alert-row -- une seule ligne horizontale */
.tmpl-manage-panel .tmpl-manage-item{display:flex;align-items:center;gap:14px;padding:12px 14px;border:1px solid var(--border);border-radius:10px;background:var(--bg);margin-bottom:8px;transition:border-color .15s}
.tmpl-manage-panel .tmpl-manage-item:hover{border-color:var(--accent)}
.tmpl-manage-info{flex:1;min-width:0}
.tmpl-manage-name{font-size:14px;font-weight:700;color:var(--text)}
.tmpl-manage-desc{font-size:12px;color:var(--muted);margin-top:2px}
.tmpl-manage-meta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:11px;margin-top:6px}
.tmpl-manage-badge{padding:3px 9px;border-radius:6px;background:var(--card);color:var(--text2);font-weight:600;border:1px solid var(--border)}
.tmpl-manage-badge.recur-on{background:rgba(52,211,153,.15);color:var(--ok,#34d399);border:1px solid rgba(52,211,153,.35)}
.tmpl-manage-badge.recur-off{background:var(--card);color:var(--muted);border:1px solid var(--border)}
.tmpl-manage-badge.stat{background:var(--accent-bg);color:var(--accent);font-family:ui-monospace,monospace;border-color:transparent}
.tmpl-manage-toggle-wrap{flex-shrink:0;display:flex;align-items:center;justify-content:center;width:38px}
.tmpl-manage-toggle-placeholder{display:inline-block;width:38px;height:22px}  /* garde l'alignement quand pas de recurrence configuree */
.tmpl-manage-actions{display:flex;gap:6px;flex-wrap:wrap}
.tmpl-manage-actions button{padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:12px;font-weight:600;transition:all .12s;display:inline-flex;align-items:center;gap:5px}
.tmpl-manage-actions button:hover{border-color:var(--accent);color:var(--accent)}
.tmpl-manage-actions button.danger:hover{border-color:var(--danger);color:var(--danger)}
.tmpl-manage-actions button.primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.tmpl-manage-actions button.primary:hover{filter:brightness(1.08);color:var(--bg)}
/* v2.5.31 — Section pliable « Occurrences supprimées » dans la modale modèle */
.tmpl-del-block{margin-top:14px;border:1px solid var(--border);border-radius:10px;background:var(--bg);overflow:hidden}
.tmpl-del-head{display:flex;align-items:center;gap:9px;width:100%;padding:11px 14px;border:none;background:var(--bg);color:var(--text);font-family:inherit;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;text-align:left;cursor:pointer;transition:background .12s}
.tmpl-del-head:hover{background:var(--card)}
.tmpl-del-chev{width:14px;height:14px;flex-shrink:0;color:var(--muted);transition:transform .16s}
.tmpl-del-block.open .tmpl-del-chev{transform:rotate(90deg)}
.tmpl-del-count{padding:2px 8px;border-radius:6px;background:rgba(251,191,36,.16);border:1px solid rgba(251,191,36,.38);color:var(--warn);font-size:11px;font-weight:800;font-family:ui-monospace,monospace;text-transform:none;letter-spacing:0}
.tmpl-del-hint{margin-left:auto;font-size:11px;font-weight:500;color:var(--muted);text-transform:none;letter-spacing:0}
.tmpl-del-body{display:none;padding:0 14px 12px}
.tmpl-del-block.open .tmpl-del-body{display:block}
.tmpl-del-sub{margin:0 0 10px;font-size:12px;color:var(--muted);line-height:1.45}
.tmpl-del-row{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card);margin-bottom:6px}
.tmpl-del-row:last-child{margin-bottom:0}
.tmpl-del-row-main{flex:1;min-width:0}
.tmpl-del-row-when{font-size:13px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums}
.tmpl-del-row-meta{font-size:11.5px;color:var(--muted);margin-top:2px;line-height:1.4}
.tmpl-del-row-warn{margin-top:4px;font-size:11px;font-weight:700;color:var(--warn)}
.tmpl-del-restore{flex-shrink:0;padding:7px 14px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--bg);font-family:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:filter .12s}
.tmpl-del-restore:hover{filter:brightness(1.08)}
@media (max-width:640px){
  .tmpl-del-hint{display:none}
  .tmpl-del-row{flex-wrap:wrap}
  .tmpl-del-restore{width:100%}
}
/* Badge cliquable « N supprimée(s) » sur la carte du modèle -> ouvre l'édition
   directement sur la section. Sert de point d'entrée découvrable. */
.tmpl-manage-badge.del{background:rgba(251,191,36,.14);color:var(--warn);border-color:rgba(251,191,36,.36);cursor:pointer;font-family:inherit;font-size:11px;font-weight:700;transition:filter .12s}
.tmpl-manage-badge.del:hover{filter:brightness(1.12)}
/* Badge visuel sur créneaux calendrier issus d'un template */
.cal-event.is-from-template::after{content:"↻";position:absolute;top:2px;right:4px;font-size:11px;color:var(--accent);opacity:.8;font-weight:900;pointer-events:none}
.cal-event.is-from-template{border-left:3px solid var(--accent)}
/* v2.5.6 : historique des creneaux -- scrollbar bornee, alignee sur .ops-table-wrap */
.plan-hist-scroll{max-height:min(60vh,720px);overflow-y:auto;overflow-x:hidden;padding-right:4px;scrollbar-width:thin;scrollbar-color:var(--border) transparent}
.plan-hist-scroll::-webkit-scrollbar{width:8px}
.plan-hist-scroll::-webkit-scrollbar-track{background:transparent}
.plan-hist-scroll::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}
.plan-hist-scroll::-webkit-scrollbar-thumb:hover{background:var(--accent)}
.tmpl-item-btn svg{width:15px;height:15px}
.tmpl-empty{padding:24px 16px;border:1px dashed var(--border);border-radius:10px;color:var(--muted);font-size:13px;text-align:center;font-style:italic;background:var(--bg)}
/* Sélecteur de modèle dans le modal Nouveau créneau */
/* v2.6.1 : styles .case-tmpl-picker* supprimes — le bloc « Modèle » du haut de
   la modale et son bouton « Gérer » ont ete retires. L'import de modele se fait
   desormais depuis l'en-tete « Opérations à effectuer », et la gestion des
   modeles reste accessible par le menu « + » du calendrier ainsi que par
   l'onglet Créneaux. */
/* v2.6.1 : rappel des modeles deja importes dans le creneau en cours. */
.case-tmpl-applied{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:0 0 10px 0;font-size:12px;color:var(--muted)}
.case-tmpl-applied .case-tmpl-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.28);font-weight:700}
/* Mode opérateur : masque tous les éléments d'édition dans le calendrier */
body[data-maint-role="operator"] .cal-fab,
body[data-maint-role="operator"] .cal-fab-menu,
body[data-maint-role="operator"] .plan-det-case-actions{display:none !important}
/* v2.6.1 : le bandeau d'aide etait deja masque cote operateur ; il n'existe plus pour personne. */
/* Les cases vides du calendrier ne réagissent plus visuellement au hover */
body[data-maint-role="operator"] .cal-wv-day-col{cursor:default}
body[data-maint-role="operator"] .cal-wv-day-col:hover{background:transparent !important}
body[data-maint-role="operator"] .cal-cell{cursor:default}
body[data-maint-role="operator"] .cal-cell:hover{background:inherit !important}
/* Bandeau "lecture seule" au-dessus du calendrier dans l'onglet Général */
.op-cal-readonly-banner{display:flex;align-items:center;gap:10px;padding:10px 14px;margin-bottom:14px;border-radius:10px;background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.35);color:var(--warn);font-size:12.5px;font-weight:600;letter-spacing:.2px}
.op-cal-readonly-banner svg{flex-shrink:0}
body.light .op-cal-readonly-banner{background:rgba(217,119,6,.10);color:#b45309;border-color:rgba(217,119,6,.35)}
/* Surligne les créneaux où l'opérateur est dans le groupe */
body[data-maint-role="operator"] .cal-event.is-mine{outline:2px solid var(--warn);outline-offset:-2px}
body[data-maint-role="operator"] .cal-event:not(.is-mine){opacity:.55}
body[data-maint-role="operator"] .cal-event{cursor:pointer}
/* Bouton flottant « + » sur le calendrier */
.cal-fab{position:absolute;right:16px;bottom:16px;z-index:10;width:56px;height:56px;border-radius:50%;background:var(--accent);color:var(--accent-fg,#fff);border:none;box-shadow:0 6px 18px rgba(0,0,0,.25);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:transform .12s,filter .12s}
.cal-fab:hover{filter:brightness(1.08);transform:translateY(-1px)}
.cal-fab svg{width:24px;height:24px}
.cal-fab-menu{position:absolute;right:16px;bottom:82px;z-index:11;min-width:260px;max-width:340px;padding:8px;border-radius:12px;background:var(--card);border:1px solid var(--border);box-shadow:0 12px 32px rgba(0,0,0,.35);display:none}
.cal-fab-menu.open{display:block}
.cal-fab-menu-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;cursor:pointer;transition:background .12s;border:none;background:transparent;color:var(--text);font-family:inherit;font-size:13px;font-weight:600;width:100%;text-align:left}
.cal-fab-menu-item:hover{background:var(--bg)}
.cal-fab-menu-sep{height:1px;background:var(--border);margin:6px 0}
.cal-fab-menu-hint{font-size:11px;color:var(--muted);padding:4px 12px 8px;text-transform:uppercase;letter-spacing:.4px;font-weight:700}
/* Détails créneau */
.plan-det-case-head{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-top:14px}
.plan-det-case-machine{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:8px;background:var(--accent);color:var(--accent-fg,#fff);font-size:13px;font-weight:800;letter-spacing:.2px}
.plan-det-case-time{display:inline-flex;align-items:center;gap:5px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;font-weight:700;font-size:13px;color:var(--text)}
.plan-det-case-ops-label{margin-top:14px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:700}
.plan-det-case-ops-list{margin-top:8px;display:flex;flex-direction:column;gap:6px;max-height:38vh;overflow-y:auto;padding-right:4px}
/* v2.6.1 : la liste d'operations defile en interne. Avant, un creneau de 14
   operations poussait les boutons Modifier / Supprimer (.plan-det-case-actions)
   hors de la zone visible : il fallait faire defiler tout le corps du modal
   pour les atteindre, sans indice qu'ils existaient. */
.plan-det-case-op{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card);transition:border-color .12s}
.plan-det-case-op:hover{border-color:var(--accent)}
.plan-det-case-op-bullet{flex-shrink:0;width:8px;height:8px;border-radius:50%;background:var(--accent)}
.plan-det-case-op-name{flex:1;min-width:0;font-size:13px;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.plan-det-case-op-freq{font-size:11px;color:var(--muted);font-weight:600}
.plan-det-case-op-empty{padding:14px;border:1px dashed var(--border);border-radius:8px;color:var(--muted);font-style:italic;text-align:center;font-size:12px}
.plan-det-case-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:16px;flex-wrap:wrap}
.plan-det-case-actions .case-action-btn{display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:8px;font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;transition:all .12s;border:1px solid var(--border);background:var(--card);color:var(--text)}
.plan-det-case-actions .case-action-btn.edit{border-color:var(--accent);color:var(--accent)}
.plan-det-case-actions .case-action-btn.edit:hover{background:var(--accent);color:var(--accent-fg,#fff)}
.plan-det-case-actions .case-action-btn.del{border-color:var(--danger);color:var(--danger)}
.plan-det-case-actions .case-action-btn.del:hover{background:var(--danger);color:#fff}
/* Indicateur survol des colonnes (clic crée un créneau) */
.cal-wv-day-col{cursor:copy}
.cal-wv-day-col:hover .cal-wv-hour-row:hover{background:rgba(34,211,238,.08)}
.cal-wv-day-col.cal-wv-clickable-hint .cal-wv-hour-row:hover{background:var(--accent-bg)}
/* Listes du catalogue : retirer indices de drag (clic only) */
.js-cat-tbody tr{cursor:default}
.cal-event-item-machine{font-weight:600;color:var(--accent);opacity:.95;white-space:nowrap}
/* Modale Détails */
.plan-det-list{display:flex;flex-direction:column;gap:8px;margin-top:14px}
.plan-det-row{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:12px 14px;border:1px solid var(--border);border-radius:10px;background:var(--bg);transition:border-color .15s,box-shadow .15s}
.plan-det-row:hover{border-color:var(--accent)}
.plan-det-row-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:7px}
.plan-det-row-name{display:flex;align-items:center;gap:10px;font-size:14px;font-weight:700;color:var(--text);line-height:1.25}
.plan-det-row-name .niv-badge{flex-shrink:0}
.plan-det-row-meta{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:12px;color:var(--text2);align-items:center}
.plan-det-row-time{display:inline-flex;align-items:center;gap:5px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;font-weight:700;color:var(--accent)}
.plan-det-row-time svg{opacity:.85}
.plan-det-row-machine{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-weight:700;font-size:11px;letter-spacing:.2px}
.plan-det-row-freq{color:var(--muted);font-weight:600;font-size:11px}
.plan-det-row-actions{display:flex;gap:6px;flex-shrink:0;align-items:flex-start}
/* Lignes du catalogue rendues draggable */
.js-cat-tbody tr[draggable="true"]{cursor:grab}
.js-cat-tbody tr[draggable="true"]:active{cursor:grabbing}
.js-cat-tbody tr[draggable="true"].drag-source{opacity:.55}
@media(max-width:720px){
  .cal-wv-body{max-height:60vh}
  .cal-wv-time{font-size:9px;padding-right:5px}
  .cal-wv-header,.cal-wv-allday,.cal-wv-body{grid-template-columns:54px repeat(7,1fr)}
  .cal-wv-daydate{font-size:12px}
}

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
/* v2.6.1 : bandeau date + horaires des modales creneau. Le discret « Date :
   ... » en 12px gris pointille se confondait avec le fond ; date et horaires
   sont l'information la plus structurante d'un creneau. */
.ops-dt-banner{border-style:solid;border-color:var(--accent);background:var(--accent-bg);color:var(--text);font-size:14px;padding:12px 16px;gap:10px;flex-wrap:wrap}
.ops-dt-banner strong{font-size:15px;font-weight:800;color:var(--text)}
.ops-dt-banner .ops-dt-sep{color:var(--accent);font-weight:900;opacity:.55}
.ops-dt-banner .ops-dt-time{font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;font-size:15px;font-weight:800;color:var(--accent);letter-spacing:.02em}
.ops-dt-banner svg{color:var(--accent);flex-shrink:0}
.ops-saisi-par strong{color:var(--text);font-weight:600}
.ops-btn-add{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:10px;border:none;background:var(--accent);color:var(--accent-fg);font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;transition:filter .15s,background .15s,color .15s;white-space:nowrap}
.ops-btn-add:hover{filter:brightness(1.08)}
.ops-list{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:18px}
/* Cadres Maintenance : Couteaux / Contre-couteaux (vides pour l'instant) */
.maint-group{margin-top:8px}
.maint-group + .maint-group{margin-top:24px}
.maint-group-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.maint-group-title{margin:0;font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.8px}
.maint-group-count{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.maint-frames-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}
.maint-frame{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;min-height:180px;transition:border-color .15s,box-shadow .15s}
.maint-frame .maint-frame-stats{flex:1}
.maint-frame-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 20px;border-bottom:1px solid var(--border)}
.maint-frame-title{font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.4px;line-height:1.3}
.maint-frame-subtitle{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.maint-frame-badges{display:flex;flex-direction:row;align-items:center;gap:6px;flex-shrink:0;opacity:.72;transition:opacity .15s}
.maint-frame:hover .maint-frame-badges{opacity:1}
.maint-frame-cat-pill{display:inline-flex;align-items:center;padding:2px 7px;border-radius:999px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;border:1px solid transparent;white-space:nowrap}
.maint-frame-badges .niv-badge{font-size:9px;padding:2px 6px;font-weight:600}
.maint-frame-cat-pill.controles{color:var(--ok,#34d399);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.12)}
.maint-frame-cat-pill.interventions,
.maint-frame-cat-pill.entretien{color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.12)}
.maint-frame-cat-pill.remplacements{color:#fb923c;border-color:rgba(251,146,60,.4);background:rgba(251,146,60,.12)}
body.light .maint-frame-cat-pill.controles{color:var(--ok,#059669);background:rgba(5,150,105,.10)}
body.light .maint-frame-cat-pill.interventions,
body.light .maint-frame-cat-pill.entretien{color:#7c3aed;background:rgba(124,58,237,.10);border-color:rgba(124,58,237,.35)}
body.light .maint-frame-cat-pill.remplacements{color:#c2410c;background:rgba(234,88,12,.10);border-color:rgba(234,88,12,.35)}
.maint-frame-body{flex:1;display:flex;align-items:center;justify-content:center;padding:24px;color:var(--muted);font-size:12px;font-style:italic}
.maint-frames-empty{padding:32px;color:var(--muted);font-size:13px;text-align:center;background:var(--card);border:1px dashed var(--border);border-radius:14px}
.maint-frame-stats{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:20px 22px 16px}
.maint-frame-stat{display:flex;flex-direction:column;gap:6px;min-width:0}
.maint-frame-stat-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.6px}
.maint-frame-stat-value{font-size:22px;color:var(--accent);font-weight:700;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:-.2px}
.maint-frame-stat-value.muted{color:var(--muted);font-weight:500;font-style:italic;font-size:18px}
.maint-frame-progress{padding:0 20px 12px}
.maint-frame-progress-track{height:14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;overflow:hidden;position:relative}
/* v2.4.24 : classes .warn/.danger retirees (dead code) — la couleur du remplissage
   est TOUJOURS imposee inline par _ratioColor(ratio), meme systeme que les
   anneaux circulaires des pieces d'usure. */
.maint-frame-progress-fill{height:100%;border-radius:4px;transition:width .35s ease,background-color .15s;background:var(--ok,#34d399)}
.maint-frame-progress-label{display:flex;justify-content:space-between;gap:8px;margin-top:5px;font-size:11px;color:var(--muted);font-weight:500}
.maint-frame-progress-label .pct{color:var(--text2);font-weight:600}
.maint-frame-progress.is-empty .maint-frame-progress-track{opacity:.4}
.maint-frame-retard{padding:10px 20px 16px;display:flex;align-items:center;gap:8px;font-size:12px;border-top:1px solid var(--border)}
.maint-frame-retard-badge{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.3px}
.maint-frame-retard-badge.ok{background:rgba(52,211,153,.15);color:var(--ok,#34d399)}
.maint-frame-retard-badge.warn{background:rgba(251,191,36,.15);color:var(--warn,#fbbf24)}
.maint-frame-retard-badge.danger{background:rgba(248,113,113,.15);color:var(--danger,#f87171)}
.maint-frame-retard-badge.unknown{background:var(--bg);color:var(--muted)}
.maint-frame-retard-detail{color:var(--text2);font-size:11px}
.maint-frame.is-overdue{border-color:var(--danger,#f87171);box-shadow:0 0 0 1px var(--danger,#f87171),0 4px 12px rgba(248,113,113,.20)}
.maint-frame.is-overdue .maint-frame-head{border-bottom-color:rgba(248,113,113,.25)}
.maint-frame.is-overdue .maint-frame-title{color:var(--danger,#f87171)}
.maint-frame.is-overdue-critical{border-color:var(--danger,#dc2626);box-shadow:0 0 0 2px var(--danger,#dc2626),0 6px 16px rgba(220,38,38,.30);transform:scale(1.01);transform-origin:top center}
/* v2.4.23 : badge "Excès metrage" — informatif, pas une alerte */
.maint-wp-badge.maint-wp-badge-info{background:rgba(148,163,184,.15);color:var(--text2);border:1px solid var(--border)}
/* ── Bande de statut à gauche de chaque carte (v2.4.6) ─────────────── */
/* Une bande verticale de 4px teintée par statut : rouge (retard), orange (dû bientôt),
   vert (à jour), gris (jamais saisi ou intervalle inconnu). */
.maint-frame{position:relative}
.maint-frame::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:transparent;border-top-left-radius:14px;border-bottom-left-radius:14px;transition:background-color .15s}
.maint-frame[data-status="overdue"]::before{background:var(--danger,#f87171)}
.maint-frame[data-status="soon"]::before{background:#fb923c}
.maint-frame[data-status="ok"]::before{background:var(--ok,#34d399)}
.maint-frame[data-status="never"]::before{background:var(--muted)}
.maint-frame[data-status="unknown"]::before{background:var(--border)}
/* Statut "à jour" volontairement plus discret : opacity légère pour amplifier
   le contraste avec les cartes en alerte. */
.maint-frame[data-status="ok"]{opacity:.85}
.maint-frame[data-status="ok"]:hover{opacity:1}
/* ── Sous-toolbar Statut + Groupement (v2.4.6) ─────────────────────── */
.maint-subtoolbar{display:flex;align-items:center;gap:12px;margin:0 0 18px 0;flex-wrap:wrap}
.maint-subtoolbar-label{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
/* v2.4.19 : toolbar unifiee Machine + Categorie + Statut sur une ligne */
.maint-machine-toolbar{display:flex;flex-direction:column;align-items:stretch;gap:0;margin:8px 0 20px 0}
/* v2.5.10 : hierarchie des filtres. Niveau 1 = Machine (ligne du haut, isolee
   par un filet). Niveau 2 = Categorie + Statut, indentes sous la machine
   selectionnee pour montrer qu'ils s'appliquent DANS le perimetre machine. */
.maint-toolbar-row{display:flex;align-items:center;gap:12px;row-gap:10px;flex-wrap:wrap}
.maint-toolbar-row--primary{padding-bottom:12px;border-bottom:1px solid var(--border)}
.maint-toolbar-row--secondary{margin-top:12px;margin-left:3px;padding-left:15px;border-left:2px solid var(--border)}
.maint-toolbar-sep{width:1px;align-self:stretch;min-height:24px;background:var(--border);margin:0 2px}
.maint-toolbar-row--primary .maint-toolbar-label{color:var(--text2);font-size:11px;letter-spacing:.6px}
.maint-toolbar-row--primary .maint-machine-btn{font-size:14px;padding:9px 20px}
@media(max-width:720px){
  .maint-toolbar-row--secondary{margin-left:0;padding-left:10px}
  .maint-toolbar-sep{display:none}
}
.maint-toolbar-label{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.maint-machine-tabs,.maint-cat-tabs{display:inline-flex;gap:6px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:4px}
.maint-chip-group{display:inline-flex;gap:6px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:4px}
.maint-chip{border:none;background:transparent;color:var(--text2);padding:6px 12px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s,color .15s;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.maint-chip:hover{background:var(--bg);color:var(--text)}
.maint-chip.active{background:var(--accent);color:var(--bg);box-shadow:0 1px 4px rgba(0,0,0,.15)}
.maint-chip[data-status-filter="overdue"].active{background:var(--danger,#f87171);color:#fff}
.maint-chip[data-status-filter="soon"].active{background:#fb923c;color:#fff}
.maint-chip[data-status-filter="ok"].active{background:var(--ok,#34d399);color:#0a0e17}
.maint-chip[data-status-filter="never"].active{background:var(--muted);color:#fff}
/* ── Pastilles compteur sur onglets Machine et Catégorie (v2.4.6) ──── */
.maint-tab-badge{display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;padding:0 6px;margin-left:6px;border-radius:999px;background:var(--danger,#f87171);color:#fff;font-size:10px;font-weight:700;line-height:1;vertical-align:middle}
.maint-tab-badge.hidden{display:none}
.maint-machine-btn.active .maint-tab-badge,.maint-cat-btn.active .maint-tab-badge{background:#fff;color:var(--danger,#f87171)}
/* v2.4.27 : variante orange pour "Dû bientôt" — s'affiche à côté de la pastille rouge */
.maint-tab-badge.maint-tab-badge-soon{background:#fb923c;margin-left:4px}
.maint-machine-btn.active .maint-tab-badge.maint-tab-badge-soon,
.maint-cat-btn.active .maint-tab-badge.maint-tab-badge-soon{background:#fff;color:#fb923c}
/* v2.4.27 : pastille rouge sur l'item sidebar Maintenance = total retards toutes machines */
.nav-btn-badge{margin-left:auto;min-width:20px;height:18px;padding:0 6px;border-radius:999px;background:var(--danger,#f87171);color:#fff;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;line-height:1}
.nav-btn-badge.hidden{display:none}
.nav-btn.active .nav-btn-badge{background:#fff;color:var(--danger,#f87171)}
/* Petite pastille "count" à côté des chips statut (info neutre, non alerte) */
.maint-chip-count{display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:16px;padding:0 5px;margin-left:2px;border-radius:999px;background:var(--bg);color:var(--muted);font-size:10px;font-weight:700;line-height:1}
.maint-chip.active .maint-chip-count{background:rgba(255,255,255,.25);color:#fff}
.maint-chip[data-status-filter="ok"].active .maint-chip-count{background:rgba(10,14,23,.25);color:#0a0e17}
.ops-subtabs{display:flex;gap:0;margin-bottom:18px;border-bottom:1px solid var(--border)}
.ops-subtab{padding:10px 18px;background:transparent;border:none;border-bottom:2px solid transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;font-family:inherit;transition:all .15s;margin-bottom:-1px;display:inline-flex;align-items:center;gap:6px}
.ops-subtab:hover{color:var(--text);background:var(--accent-bg)}
.ops-subtab.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
.ops-readonly-notice{display:flex;align-items:flex-start;gap:10px;padding:11px 14px;margin-bottom:14px;background:var(--accent-bg);border:1px solid var(--accent);border-radius:10px;color:var(--text);font-size:13px;line-height:1.5}
.ops-readonly-notice svg{color:var(--accent);flex-shrink:0;margin-top:1px}
.ops-readonly-notice strong{color:var(--accent);font-weight:700}
.ops-row-warn-ico{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;margin-right:6px;color:var(--danger,#f87171);vertical-align:middle;flex-shrink:0}
.ops-row-warn-ico svg{width:18px;height:18px}
.maint-machine-btn{border:none;background:transparent;color:var(--text2);padding:7px 16px;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .15s}
.maint-machine-btn:hover{background:var(--bg);color:var(--text)}
.maint-machine-btn.active{background:var(--accent);color:var(--bg);box-shadow:0 1px 4px rgba(0,0,0,.15)}
.maint-machine-btn.active:hover{background:var(--accent);color:var(--bg);filter:brightness(1.05)}
.maint-cat-btn{border:none;background:transparent;color:var(--text2);padding:7px 16px;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .15s}
.maint-cat-btn:hover{background:var(--bg);color:var(--text)}
.maint-cat-btn[data-maint-cat="all"].active{background:var(--accent);color:var(--bg);box-shadow:0 1px 4px rgba(0,0,0,.15)}
.maint-cat-btn[data-maint-cat="entretien"].active{background:#a78bfa;color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.15)}
.maint-cat-btn[data-maint-cat="remplacements"].active{background:#fb923c;color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.15)}
.maint-cat-btn.active:hover{filter:brightness(1.05)}
.maint-wearparts-stack{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:14px}
.maint-wearpart{min-height:260px}
/* v2.6.1 : la severite visuelle de la carte piece d'usure suit EXACTEMENT la
   couleur de l'anneau (variable --wp-sev posee inline, calculee par
   _ratioColor cote JS) — plus de bordure rouge en face d'un anneau jaune.
   Fallback --danger si la variable n'est pas posee (carte non en retard). */
.maint-frame.maint-wearpart.is-overdue{border-color:var(--wp-sev,var(--danger,#f87171));box-shadow:0 0 0 1px var(--wp-sev,var(--danger,#f87171)),0 4px 12px var(--wp-sev-glow,rgba(248,113,113,.20))}
.maint-frame.maint-wearpart.is-overdue .maint-frame-head{border-bottom-color:var(--wp-sev-glow,rgba(248,113,113,.25))}
.maint-frame.maint-wearpart.is-overdue .maint-frame-title{color:var(--wp-sev,var(--danger,#f87171))}
.maint-frame.maint-wearpart.is-overdue-critical{border-color:var(--wp-sev,var(--danger,#dc2626));box-shadow:0 0 0 2px var(--wp-sev,var(--danger,#dc2626)),0 6px 16px var(--wp-sev-glow,rgba(220,38,38,.30))}
/* Badge "Retard X j" (temps) aligne lui aussi. Le badge "Exces" du metrage
   (.maint-wp-badge-info) garde son style neutre — le metrage est un supplement,
   pas une alarme (regle produit v2.4.23). */
.maint-frame.maint-wearpart.is-overdue .maint-wp-badge:not(.maint-wp-badge-info){background:var(--wp-sev-soft,rgba(248,113,113,.15));color:var(--wp-sev,var(--danger,#f87171))}
.maint-wp-tabs{display:inline-flex;gap:4px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:3px}
.maint-wp-btn{border:none;background:transparent;color:var(--text2);padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s,color .15s}
.maint-wp-btn:hover{background:var(--card);color:var(--text)}
.maint-wp-btn.active{background:var(--accent);color:var(--bg);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.maint-wp-btn.active:hover{filter:brightness(1.05)}
.maint-wp-sections{display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid var(--border)}
.maint-wp-section{padding:14px 18px;display:flex;flex-direction:column;gap:8px}
.maint-wp-section + .maint-wp-section{border-left:1px solid var(--border)}
.maint-wp-section-title{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}
.maint-wp-ref-row{display:flex;flex-direction:column;gap:4px}
.maint-wp-ref-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.maint-wp-ref-input{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 12px;color:var(--text);font-size:13px;font-family:inherit;width:100%;box-sizing:border-box;transition:border-color .15s,box-shadow .15s}
.maint-wp-ref-input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.maint-wp-ref-input::placeholder{color:var(--muted)}
.maint-wp-ref-value{font-size:14px;color:var(--text);font-weight:600;padding:4px 0;line-height:1.4;min-height:24px}
.maint-wp-ref-value.muted{color:var(--muted);font-weight:400;font-style:italic;font-size:12px}
.maint-wp-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,1fr);gap:18px;padding:18px 20px;align-items:center}
.maint-wp-info{display:flex;flex-direction:column;gap:10px;min-width:0}
.maint-wp-sec{display:flex;flex-direction:column;gap:4px;padding-left:10px;border-left:3px solid var(--border);min-width:0}
.maint-wp-sec-head{display:inline-flex;align-items:center;gap:7px;font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;margin-bottom:2px;color:var(--text2)}
.maint-wp-sec-tag{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:var(--text2);color:var(--bg);font-size:10px;font-weight:800;letter-spacing:0;text-transform:none}
.maint-wp-row{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;min-width:0}
.maint-wp-row .lbl{font-size:11px;color:var(--muted);font-weight:500}
.maint-wp-row .val{font-size:13px;color:var(--text);font-weight:600;word-break:break-word;min-width:0}
.maint-wp-row .val.muted{color:var(--muted);font-weight:400;font-style:italic;font-size:12px}
.maint-wp-row .sub{font-size:11px;color:var(--muted);font-weight:500}
.maint-wp-empty{flex:1;display:flex;flex-direction:column;justify-content:center;gap:6px;padding:18px 20px;border:1px dashed var(--border);border-radius:10px;background:rgba(148,163,184,.05)}
.maint-wp-empty-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.maint-wp-empty-txt{font-size:13px;color:var(--text2,var(--muted));line-height:1.55}
.maint-wp-empty-txt strong{color:var(--text);font-weight:600}
.maint-wp-badge{display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:2px 7px;border-radius:5px;background:rgba(248,113,113,.15);color:var(--danger,#f87171);text-transform:uppercase;letter-spacing:.3px;margin-left:4px}
.maint-wp-rings{display:flex;justify-content:center;align-items:center}
.maint-wp-rings svg{display:block;max-width:100%;height:auto}
@media (max-width:720px){
  .maint-wp-body{grid-template-columns:1fr;justify-items:start}
  .maint-wp-rings{justify-self:center}
}
.maint-wp-elapsed{margin-top:6px;padding-top:8px;border-top:1px dashed var(--border);display:flex;flex-direction:column;gap:3px}
@media (max-width:700px){
  .maint-wp-sections{grid-template-columns:1fr}
  .maint-wp-section + .maint-wp-section{border-left:none;border-top:1px solid var(--border)}
}
.ops-list-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 22px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.ops-list-head-right{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.ops-list-title{font-size:14px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.ops-list-count{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
.ops-table-wrap{overflow:auto;max-height:min(60vh,720px);border-radius:10px;border:1px solid var(--border);position:relative}
.ops-table-wrap .ops-table thead th{position:sticky;top:0;z-index:5;background:var(--card);box-shadow:inset 0 -1px 0 var(--border)}
.ops-table{width:100%;border-collapse:collapse;font-size:13px;color:var(--text2)}
.ops-table th{text-align:left;padding:12px 18px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);background:var(--bg);user-select:none;white-space:nowrap}
.ops-table th[data-sort],.ops-table th[data-sort-cat],.ops-table th[data-sort-ctrl],.ops-table th[data-sort-ctrl-cat]{cursor:pointer;transition:color .15s}
.ops-table th[data-sort]:hover,.ops-table th[data-sort-cat]:hover,.ops-table th[data-sort-ctrl]:hover,.ops-table th[data-sort-ctrl-cat]:hover{color:var(--accent)}
.ops-table th[data-sort].active,.ops-table th[data-sort-cat].active,.ops-table th[data-sort-ctrl].active,.ops-table th[data-sort-ctrl-cat].active{color:var(--accent)}
/* Colonne Dernière intervention */
.ops-table .col-last-intervention{min-width:170px;white-space:nowrap}
.last-intervention-wrap{display:flex;flex-direction:column;gap:4px}
.last-intervention-input{padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--text);font-size:12px;font-family:inherit;width:148px;transition:border-color .12s,box-shadow .12s}
.last-intervention-input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
.last-intervention-status{font-size:10.5px;font-weight:700;letter-spacing:.2px;display:inline-flex;align-items:center;gap:4px}
.last-intervention-status.ok{color:#16a34a}
body:not(.light) .last-intervention-status.ok{color:#4ade80}
.last-intervention-status.overdue{color:var(--danger,#dc2626)}
.last-intervention-status.unknown{color:var(--muted)}
/* Mise en valeur des lignes en retard */
.ops-table tr.row-overdue td{background:rgba(248,113,113,.10)}
.ops-table tr.row-overdue:hover td{background:rgba(248,113,113,.16)}
.ops-table tr.row-overdue td:first-child{position:relative;box-shadow:inset 4px 0 0 var(--danger,#dc2626)}
.ops-table tr.row-overdue td:first-child strong{color:var(--danger,#dc2626) !important}
.row-overdue-badge{display:inline-flex;align-items:center;gap:4px;margin-left:8px;padding:2px 7px;border-radius:5px;background:var(--danger,#dc2626);color:#fff;font-size:10px;font-weight:800;letter-spacing:.3px;text-transform:uppercase;vertical-align:middle}
.ops-table th .sort-ico{display:inline-block;margin-left:5px;opacity:.55;font-size:11px}
.ops-table th.active .sort-ico{opacity:1}
.ops-table td{padding:12px 18px;border-bottom:1px solid var(--border);vertical-align:top}
.ops-table tr:last-child td{border-bottom:none}
.ops-table tr:hover td{background:var(--bg)}
.ops-table .col-comment{max-width:340px;white-space:pre-wrap;color:var(--text2);font-size:12.5px;word-break:break-word}
.ops-table .col-duree{white-space:nowrap;color:var(--text2);font-size:12.5px;text-align:right;font-variant-numeric:tabular-nums}
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

.ctrl-src-badge{display:inline-block;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:3px 8px;border-radius:6px;background:var(--accent-bg);color:var(--accent);cursor:help}
.ctrl-actions-stack{display:inline-flex;align-items:center;gap:6px}

.ctrl-point-filters-row{display:flex;align-items:center;gap:10px;padding-top:10px;margin-top:10px;border-top:1px solid var(--border);flex-wrap:wrap}
.ctrl-point-filters-inputs{display:flex;flex-wrap:wrap;gap:8px;flex:1}
.ctrl-point-filters-inputs .pf-item{display:flex;align-items:center;gap:6px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:4px 8px}
.ctrl-point-filters-inputs .pf-label{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.3px}
.ctrl-point-filters-inputs .pf-input{padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--text);font-size:12px;font-family:inherit;min-width:80px}
.ctrl-point-filters-inputs .pf-num{width:60px}

/* ── Mode multi-rôle (admin / opérateur) ─────────────────────────────
   La page rend la même structure DOM pour tous ; le body porte
   data-maint-role="admin" ou "operator" et les règles ci-dessous
   masquent ce qui n'est pas pertinent pour le rôle courant. */
body[data-maint-role="admin"] .op-only:not(#view-op-tasks):not(#view-op-planning){display:none !important}
body[data-maint-role="operator"] .adm-only{display:none !important}
/* Bascule du contenu principal : admin voit .content, opérateur voit
   .op-main. Deux conteneurs distincts pour éviter toute interaction
   parasite entre les vues admin et les vues opérateur. */
body[data-maint-role="admin"] .op-main{display:none}
body[data-maint-role="admin"].admin-op-active .op-main{display:flex}
body[data-maint-role="admin"].admin-op-active .view.adm-only{display:none !important}
body[data-maint-role="admin"].admin-op-active .content{display:none}
body[data-maint-role="operator"] .content{display:none !important}

/* Conteneur opérateur : padding + colonne, prend toute la hauteur restante. */
.op-main{padding:28px 32px;max-width:1280px;width:100%;flex:1;display:flex;flex-direction:column;overflow-y:auto}
.op-page{display:none;flex-direction:column;flex:1}
.op-page.active{display:flex}

/* ── UI opérateur : conteneur actions dans .page-header ─────────── */
.op-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.op-date-picker{display:inline-flex;align-items:center;gap:8px;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:6px 12px;min-height:38px}
.op-date-picker label{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin:0}
.op-date-picker input[type="date"]{background:transparent;border:none;color:var(--text);font-family:inherit;font-size:13px;font-weight:600;outline:none;padding:0}
.btn.op-btn-accent{background:var(--accent);color:var(--accent-fg);border-color:var(--accent)}
.btn.op-btn-accent:hover{filter:brightness(1.08);border-color:var(--accent);color:var(--accent-fg)}
.btn.op-btn-accent .btn-ico{color:var(--accent-fg)}

/* ── Vue Mes tâches : 2 onglets Aujourd'hui / À venir ──────────── */
.op-tabs{display:flex;gap:4px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:5px;margin-bottom:18px}
.op-tab{flex:1;display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:11px 16px;border-radius:9px;background:transparent;border:none;color:var(--text2);font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;transition:background .15s,color .15s;letter-spacing:.2px}
.op-tab:hover{color:var(--text)}
.op-tab.active{background:var(--accent-bg);color:var(--accent)}
.op-tab-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--accent-bg)}
.op-tab.active .op-tab-dot{box-shadow:0 0 0 4px rgba(34,211,238,.2)}
.op-tab-count{background:var(--bg);border:1px solid var(--border);border-radius:999px;padding:2px 10px;font-size:12px;font-weight:700;color:var(--text2);min-width:26px;text-align:center}
.op-tab.active .op-tab-count{background:var(--accent);color:var(--accent-fg);border-color:transparent}
.op-tab-panel{display:none;flex:1}
.op-tab-panel.active{display:block}
/* ── Barre sélecteur machine + toggle terminées ─────────────────── */
.op-selector-bar{display:flex;align-items:center;justify-content:flex-end;gap:14px;margin-bottom:18px;padding:12px 14px;background:var(--card);border:1px solid var(--border);border-radius:12px;flex-wrap:wrap}
.op-selector-bar--toggle-only{justify-content:flex-end}
.op-toggle-termine{display:inline-flex;align-items:center;gap:10px;cursor:pointer;user-select:none}
.op-toggle-termine input{display:none}
.op-toggle-track{position:relative;display:inline-block;width:38px;height:22px;background:var(--bg);border:1px solid var(--border);border-radius:999px;transition:background .15s,border-color .15s}
.op-toggle-thumb{position:absolute;top:2px;left:2px;width:16px;height:16px;background:var(--muted);border-radius:50%;transition:left .18s,background .15s}
.op-toggle-termine input:checked ~ .op-toggle-track{background:rgba(52,211,153,.22);border-color:var(--success,#34d399)}
.op-toggle-termine input:checked ~ .op-toggle-track .op-toggle-thumb{left:18px;background:var(--success,#34d399)}
.op-toggle-label{font-size:13px;color:var(--text2);font-weight:600}
.op-toggle-count{background:rgba(52,211,153,.14);color:var(--success,#34d399);border-radius:999px;padding:2px 9px;font-size:11px;font-weight:800;min-width:24px;text-align:center}
body.light .op-toggle-count{background:rgba(5,150,105,.14);color:#059669}
/* ── Boîte englobante par créneau ────────────────────────────────── */
.op-event-box{background:transparent;border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-bottom:14px;position:relative;transition:border-color .15s}
.op-event-box.all-done{opacity:.75;background:linear-gradient(90deg,rgba(52,211,153,.05) 0%,transparent 100%)}
.op-event-box.event-non-planifie{border-style:dashed}
.op-event-box-nom{font-size:14px;font-weight:700;color:var(--text);margin-left:8px}
.op-event-box-head{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.op-event-box-head strong{font-size:13px;font-weight:800;letter-spacing:.3px;text-transform:uppercase;color:var(--text)}
.op-event-box-head .op-event-time{font-size:12px;color:var(--text2);font-weight:700}
.op-event-box-head .op-event-count{background:var(--bg);border:1px solid var(--border);color:var(--text2);font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px;text-transform:none;letter-spacing:0}
.op-event-box-head .op-event-mine{background:rgba(34,211,238,.14);color:var(--accent);font-size:10px;font-weight:800;padding:2px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:.4px}
.op-event-box-actions{margin-left:auto;display:inline-flex;gap:5px}
.op-event-box-actions button{width:28px;height:28px;padding:0;border-radius:7px;background:var(--bg);border:1px solid var(--border);color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:border-color .15s,color .15s}
.op-event-box-actions button:hover{color:var(--text);border-color:var(--accent)}
.op-event-box-actions button.danger:hover{color:var(--danger);border-color:var(--danger)}
.op-event-box-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
/* v2.2.62 : sous-sections machine à l'intérieur d'un créneau */
.op-creneau-machine-group{margin-top:14px}
.op-creneau-machine-group:first-of-type{margin-top:6px}
.op-creneau-machine-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;padding:5px 10px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.35px}
.op-creneau-machine-head .op-creneau-machine-dot{width:7px;height:7px;border-radius:50%;background:var(--accent)}
.op-creneau-machine-head .op-creneau-machine-count{margin-left:auto;background:var(--card);border:1px solid var(--border);color:var(--text2);font-size:10px;font-weight:700;padding:1px 8px;border-radius:999px;text-transform:none;letter-spacing:0}
/* Section "Opérations personnelles" (source=non_planifie) — visuel dégradé */
.op-perso-section{margin-top:28px;padding-top:18px;border-top:2px dashed var(--border)}
.op-perso-section-head{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding:10px 14px;border-radius:10px;background:var(--bg);color:var(--text2);border:1px dashed var(--border)}
.op-perso-section-head strong{font-size:13px;font-weight:800;letter-spacing:.3px;text-transform:uppercase;color:var(--text2)}
.op-perso-section-head .op-perso-section-count{background:var(--card);border:1px solid var(--border);color:var(--muted);font-size:11px;font-weight:700;padding:2px 10px;border-radius:999px}
.op-perso-section-head .op-perso-section-hint{margin-left:auto;font-size:11px;color:var(--muted);font-style:italic;font-weight:500;text-transform:none;letter-spacing:0}
/* v2.2.63 : badge machine dans les cards d'ops perso */
.op-op-card-machine{display:inline-flex;align-items:center;gap:6px;margin-top:6px;padding:4px 10px;background:var(--accent-bg);color:var(--accent);border-radius:5px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;align-self:flex-start;max-width:100%}
.op-op-card-machine .op-op-card-machine-dot{width:6px;height:6px;border-radius:50%;background:var(--accent);flex-shrink:0}
.op-op-card-machine .op-op-card-machine-lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
/* ── Carte d'op individuelle ────────────────────────────────────── */
.op-op-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:8px;transition:border-color .15s,transform .15s;position:relative}
.op-op-card:hover{border-color:var(--accent);transform:translateY(-1px)}
.op-op-card.is-done{opacity:.72;background:linear-gradient(90deg,rgba(52,211,153,.06) 0%,var(--card) 100%)}
.op-op-card-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.op-op-card-title{font-size:13px;font-weight:600;color:var(--text);line-height:1.4}
.op-op-card-status{font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;text-transform:uppercase;letter-spacing:.4px}
.op-op-card-cta{margin-top:auto;padding:8px 12px;border-radius:8px;background:var(--accent);color:var(--accent-fg);border:none;font-family:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:filter .15s;display:inline-flex;align-items:center;justify-content:center;gap:6px}
.op-op-card-cta:hover{filter:brightness(1.08)}
.op-op-card-cta.is-done{background:var(--bg);color:var(--text2);border:1px solid var(--border)}
.op-op-empty{background:var(--card);border:1px dashed var(--border);border-radius:12px;text-align:center;padding:48px 20px;color:var(--muted);font-size:14px}
.op-op-empty strong{display:block;color:var(--text2);font-size:15px;margin-bottom:6px}
/* ── Section top-level : une machine ─────────────────────────────── */
.op-machine-section{margin-bottom:26px}
.op-machine-section:last-child{margin-bottom:0}
.op-machine-section-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;padding:10px 14px;border-radius:10px;background:var(--accent-bg);color:var(--accent)}
.op-machine-section-head strong{font-size:14px;font-weight:800;letter-spacing:.3px;text-transform:uppercase;flex:1}
.op-machine-section-head .op-machine-section-count{background:var(--card);border:1px solid var(--border);color:var(--text2);font-size:11px;font-weight:700;padding:2px 10px;border-radius:999px}
.op-machine-section-head .op-machine-section-dot{width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.18)}
/* ── Modal single-op saisie ─────────────────────────────────────── */
.op-single-op-title{font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.op-single-op-name{font-size:15px;font-weight:700;color:var(--text);margin-bottom:16px}
/* Legacy compat pour l'ancienne classe (au cas où utilisée ailleurs) */
.btn-op-cancel-validation{background:transparent;color:var(--danger);border:1px solid var(--danger);font-weight:600}
.btn-op-cancel-validation:hover{background:var(--danger);color:#fff}
/* v2 : actions harmonisées du modal single-op (3 boutons alignés, même
   hauteur, hiérarchie visuelle claire) */
.op-single-actions{align-items:center;gap:8px}
/* v2 : croix de fermeture en haut à droite du modal single-op */
.op-modal-close{position:absolute;top:14px;right:14px;width:32px;height:32px;padding:0;border:none;border-radius:8px;background:transparent;color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:background .15s,color .15s}
.op-modal-close:hover{background:var(--bg);color:var(--text)}
.op-modal-close:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
/* padding supérieur du modal pour éviter que la croix chevauche le titre */
.op-modal[role="dialog"]{padding-top:24px}
.op-single-actions-spacer{flex:1}
.op-single-actions .btn{min-height:40px;padding:9px 16px;border-radius:8px;font-size:13px;font-weight:600;white-space:nowrap;transition:background .15s,color .15s,border-color .15s,filter .15s}
/* Bouton destructif : outline rouge, discret mais reconnaissable */
.btn-danger-outline{background:transparent;color:var(--danger);border:1px solid var(--danger)}
.btn-danger-outline:hover{background:var(--danger);color:#fff}
/* Bouton ghost : transparent, subtil (secondaire) */
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}
.btn-ghost:hover{background:var(--bg);color:var(--text);border-color:var(--muted)}
/* Bouton primaire : filled accent (déjà existant, on force la cohérence) */
.op-single-actions .btn.op-btn-accent{background:var(--accent);color:var(--accent-fg);border:1px solid var(--accent);font-weight:700}
.op-single-actions .btn.op-btn-accent:hover{filter:brightness(1.08)}
@media(max-width:520px){
  .op-single-actions{flex-wrap:wrap}
  .op-single-actions-spacer{display:none}
  .op-single-actions .btn{flex:1;min-width:0}
}
/* Actions Modifier/Supprimer sur cartes op individuelles (interventions non-programmées) */
.op-op-card-footer-actions{display:flex;justify-content:flex-end;gap:4px;margin-top:2px}
.op-op-card-mini-btn{width:24px;height:24px;padding:0;border-radius:6px;background:transparent;border:1px solid var(--border);color:var(--muted);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:border-color .15s,color .15s,background .15s}
.op-op-card-mini-btn:hover{color:var(--text);border-color:var(--accent);background:var(--bg)}
.op-op-card-mini-btn.danger:hover{color:var(--danger);border-color:var(--danger)}
/* v185 : chip Consignes de l'admin, cliquable, sous le titre de la carte op */
.op-op-consignes-chip{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.28);border-radius:8px;font-family:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:background .15s,color .15s,border-color .15s;align-self:flex-start;text-align:left}
.op-op-consignes-chip:hover{background:var(--accent);color:var(--accent-fg);border-color:var(--accent)}
body.light .op-op-consignes-chip{border-color:rgba(8,145,178,.28)}
/* v185 : label + panneau consignes (dans single-op modal) */
.op-consignes-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;margin-top:12px}
.op-consignes-panel{background:var(--bg);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;padding:10px 14px;color:var(--text2);font-size:13px;line-height:1.5;white-space:pre-wrap;margin-bottom:16px}
/* v185 : mini-modal consignes — plus compact que le single-op modal */
.op-consignes-modal{position:relative;max-width:420px;width:92vw;padding:18px 20px 20px 20px}
.op-consignes-modal .op-modal-close{position:absolute;top:10px;right:10px;width:28px;height:28px}
.op-consignes-modal-title{font-size:13px;font-weight:800;color:var(--text);text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px;padding-right:32px}
.op-consignes-modal-sub{font-size:12px;color:var(--muted);margin-bottom:12px;padding-right:32px}
.op-consignes-modal .op-consignes-panel{margin-bottom:0;font-size:14px}
.col-consignes{max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--text2)}
/* v2 : modal détails historique ops */
.ops-detail-modal .modal-body{padding:20px 22px 22px}
/* Hero : titre + icône accent */
.ops-detail-hero{display:flex;align-items:center;gap:14px;padding:14px 16px;margin-bottom:16px;background:linear-gradient(135deg,var(--accent-bg) 0%,transparent 100%);border:1px solid rgba(34,211,238,.22);border-radius:12px}
.ops-detail-hero-icon{flex-shrink:0;width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;background:var(--accent);color:var(--accent-fg);border-radius:12px;box-shadow:0 4px 12px rgba(34,211,238,.25)}
.ops-detail-hero-body{flex:1;min-width:0}
.ops-detail-hero-chips{margin-top:4px}
.ops-detail-title{font-size:17px;font-weight:800;color:var(--text);line-height:1.3}
body.light .ops-detail-hero{border-color:rgba(8,145,178,.22)}
/* Grille récap avec fond léger */
.ops-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:0;margin-bottom:16px;background:var(--bg);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.ops-detail-cell{display:flex;flex-direction:column;gap:4px;padding:12px 14px;border-right:1px solid var(--border)}
.ops-detail-cell:nth-child(2n){border-right:none}
.ops-detail-cell:nth-child(-n+2){border-bottom:1px solid var(--border)}
.ops-detail-cell-label{font-size:10px;font-weight:800;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.ops-detail-cell-value{font-size:14px;font-weight:600;color:var(--text)}
/* Blocs colorés distincts pour consignes / commentaires / pièces */
.ops-detail-block{margin-top:14px;border-radius:10px;overflow:hidden;border:1px solid transparent}
.ops-detail-block-head{display:flex;align-items:center;gap:8px;padding:10px 14px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.5px}
.ops-detail-block-body{padding:12px 14px;background:var(--card);font-size:13px;line-height:1.55;color:var(--text2);white-space:pre-wrap}
.ops-detail-block--consignes{border-color:rgba(34,211,238,.35)}
.ops-detail-block--consignes .ops-detail-block-head{background:rgba(34,211,238,.14);color:var(--accent)}
.ops-detail-block--comment{border-color:rgba(251,191,36,.35)}
.ops-detail-block--comment .ops-detail-block-head{background:rgba(251,191,36,.14);color:var(--warn)}
.ops-detail-block--pieces{border-color:rgba(167,139,250,.35)}
.ops-detail-block--pieces .ops-detail-block-head{background:rgba(167,139,250,.14);color:#8b5cf6}
body.light .ops-detail-block--pieces .ops-detail-block-head{color:#7c3aed}
body.light .ops-detail-block--comment .ops-detail-block-head{color:#b45309}
@media(max-width:560px){
  .ops-detail-grid{grid-template-columns:1fr}
  .ops-detail-cell{border-right:none !important;border-bottom:1px solid var(--border)}
  .ops-detail-cell:last-child{border-bottom:none}
}
/* Modal Modifier créneau : lignes ops déjà effectuées (read-only) */
.case-ops-row-done{background:linear-gradient(90deg,rgba(52,211,153,.06) 0%,transparent 100%);border-left:3px solid var(--success,#34d399);padding:10px 12px;border-radius:8px;margin-bottom:8px}
.case-ops-row-done .case-ops-row-done-label{display:flex;align-items:center;font-size:13px;font-weight:600;color:var(--text2);flex:1}
.case-ops-row-done-badge{margin-left:10px;background:rgba(52,211,153,.16);color:var(--success,#34d399);border-radius:5px;padding:2px 8px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.4px}
/* v2 : dropdown machine unique dans le modal case */
.case-ops-machine-select{min-width:180px;max-width:220px;padding:6px 10px;font-size:13px;font-weight:600}
/* v2 : ligne op mode Libre dans le picker admin */
.case-op-libre-wrap{position:relative;flex:1}
.case-op-libre-titre{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--text);font-family:inherit;font-size:13px}
.case-op-libre-titre:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.case-op-libre-autocomplete{position:absolute;top:100%;left:0;right:0;margin-top:4px;z-index:20;background:var(--card);border:1px solid var(--border);border-radius:8px;max-height:200px;overflow-y:auto;box-shadow:0 6px 20px rgba(0,0,0,.15)}
.case-op-mode-link{display:inline-block;margin-top:6px;color:var(--accent);font-size:12px;text-decoration:none;font-family:inherit}
.case-op-mode-link:hover{text-decoration:underline}
.case-ops-row-mode{padding-left:2px}
/* v185 : consignes admin sur les rows d'op */
.case-ops-consignes{margin-top:10px;padding-top:10px;border-top:1px dashed var(--border)}
.case-op-consignes-toggle{font-size:12px}
.case-op-consignes-textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-family:inherit;font-size:13px;line-height:1.5;resize:vertical;min-height:70px;margin-top:8px;transition:border-color .15s}
.case-op-consignes-textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.case-op-consignes-preview{margin-top:6px;padding:8px 12px;background:var(--bg);border-left:3px solid var(--accent);border-radius:0 6px 6px 0;color:var(--text2);font-size:12px;font-style:italic;line-height:1.4;white-space:pre-wrap}
body.light .case-ops-row-done{background:linear-gradient(90deg,rgba(5,150,105,.06) 0%,transparent 100%)}
body.light .case-ops-row-done-badge{background:rgba(5,150,105,.16);color:#059669}
/* v2.5.10 : statut invalidee (saisie mise de cote administrativement) */
.case-ops-row-done.is-invalidee{background:linear-gradient(90deg,rgba(148,163,184,.08) 0%,transparent 100%);border-left-color:var(--muted)}
.case-ops-row-done-badge.is-invalidee{background:rgba(148,163,184,.18);color:var(--muted)}
.case-ops-row-done-badge.is-mixed{background:rgba(245,158,11,.18);color:var(--warn,#f59e0b)}
body.light .case-ops-row-done.is-invalidee{background:linear-gradient(90deg,rgba(100,116,139,.08) 0%,transparent 100%)}
body.light .case-ops-row-done-badge.is-invalidee{background:rgba(100,116,139,.20);color:#475569}
body.light .case-ops-row-done-badge.is-mixed{background:rgba(217,119,6,.20);color:#b45309}
.op-col-cards{display:flex;flex-direction:column;gap:12px}
.op-col-empty{background:var(--card);border:1px dashed var(--border);border-radius:12px;text-align:center;padding:32px 20px;color:var(--muted);font-size:13px}
.op-col-empty strong{display:block;color:var(--text2);font-size:14px;margin-bottom:4px}
/* Regroupement par machine dans un panel */
.op-machine-block{margin-bottom:22px}
.op-machine-block:last-child{margin-bottom:0}
.op-machine-block-head{display:flex;align-items:center;gap:10px;padding:10px 14px;margin-bottom:12px;border-radius:10px;background:linear-gradient(90deg,var(--accent-bg) 0%,transparent 100%);border-left:3px solid var(--accent);color:var(--text);font-size:13px;font-weight:800;letter-spacing:.3px;text-transform:uppercase}
.op-machine-block-head .op-machine-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.op-machine-block-head .op-machine-badge{margin-left:auto;background:var(--bg);border:1px solid var(--border);color:var(--text2);font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px;text-transform:none;letter-spacing:0}
.op-machine-block-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
/* Sous-section "Terminées" dans un bloc machine */
.op-machine-subhead{display:flex;align-items:center;gap:8px;margin:14px 0 10px 4px;padding:6px 10px;border-radius:8px;background:rgba(52,211,153,.10);color:var(--success,#34d399);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;width:fit-content}
.op-machine-subhead-count{background:rgba(52,211,153,.22);color:var(--success,#34d399);border-radius:999px;padding:1px 8px;font-size:11px;font-weight:800}
body.light .op-machine-subhead{background:rgba(5,150,105,.12);color:#059669}
body.light .op-machine-subhead-count{background:rgba(5,150,105,.22);color:#059669}
.op-machine-block-cards-done{opacity:.85}
/* Carte d'op terminée — ton "acquis", check vert, bord gauche vert */
.op-card.is-done{border-left:3px solid var(--success,#34d399);background:linear-gradient(90deg,rgba(52,211,153,.08) 0%,var(--card) 100%)}
.op-card.is-done .op-card-head strong{color:var(--text2)}
body.light .op-card.is-done{background:linear-gradient(90deg,rgba(5,150,105,.06) 0%,var(--card) 100%)}
/* Actions Modifier / Supprimer sur la carte (opérateur propriétaire) */
.op-card-actions{position:absolute;bottom:14px;right:14px;display:inline-flex;gap:6px}
.op-card.owned-by-me{padding-bottom:52px}
.op-card-action-btn{width:32px;height:32px;padding:0;border-radius:8px;background:var(--bg);border:1px solid var(--border);color:var(--text2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:border-color .15s,color .15s,background .15s}
.op-card-action-btn:hover{color:var(--text);border-color:var(--accent)}
.op-card-action-btn.danger:hover{color:var(--danger);border-color:var(--danger)}
.op-card-badge-mine{display:inline-block;font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;background:rgba(34,211,238,.18);color:var(--accent);text-transform:uppercase;letter-spacing:.5px;margin-left:4px}

/* Bouton "Commencer la session" sur les cartes du jour */
.op-card-cta{width:100%;justify-content:center;margin-top:12px}

/* ── Cartes de tâches ───────────────────────────────────────────── */
.op-tasks-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.op-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;cursor:pointer;transition:border-color .15s,transform .15s;position:relative;display:flex;flex-direction:column;gap:10px}
.op-card:hover{border-color:var(--accent);transform:translateY(-1px)}
.op-card-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding-right:100px}
.op-code{display:inline-block;padding:3px 9px;border-radius:6px;background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:800;letter-spacing:.4px;font-family:monospace}
.op-cat{display:inline-block;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
/* v180 : chip "Libre" pour distinguer les interventions libres dans l'historique */
.libre-chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;background:rgba(96,165,250,.16);color:#3b82f6;margin-left:6px;vertical-align:middle}
/* v182 Lot 2 : petits boutons inline (renommer + docs) sur les lignes libres de l'historique */
.libre-inline-btn{display:inline-flex;align-items:center;justify-content:center;background:transparent;border:1px solid transparent;border-radius:5px;padding:3px 5px;color:var(--muted);cursor:pointer;transition:background .12s,color .12s,border-color .12s;vertical-align:middle;margin-left:4px}
.libre-inline-btn:hover{background:var(--bg);color:var(--accent);border-color:var(--border)}
body[data-maint-role="operator"] .libre-inline-btn{display:none}
body.light .libre-chip{color:#2563eb;background:rgba(37,99,235,.10)}
/* v2.7.1 — Codes archivés (catalogue maintenance).
   Un code archivé n'est ni actif ni supprimé : il est sorti du catalogue mais
   son libellé continue de résoudre dans l'historique. La ligne est donc
   estompée sans être barrée — barrer laisserait croire à une suppression. */
.maint-arch-chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;background:rgba(148,163,184,.18);color:var(--muted);margin-left:6px;vertical-align:middle}
.maint-row-archived td{opacity:.55}
.maint-row-archived:hover td{opacity:.85}
.maint-arch-bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:8px 12px;margin-bottom:10px;border:1px dashed var(--border);border-radius:8px;background:var(--card);color:var(--muted);font-size:12px}
/* v180 : mini-modal Intervention libre + autocomplete */
.libre-titre-wrap{position:relative}
.libre-autocomplete-panel{position:absolute;top:100%;left:0;right:0;background:var(--card);border:1px solid var(--border);border-radius:8px;max-height:220px;overflow-y:auto;z-index:100;margin-top:4px;box-shadow:0 6px 20px rgba(0,0,0,.18)}
.libre-suggestion{padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);transition:background .1s}
.libre-suggestion:last-child{border-bottom:none}
.libre-suggestion:hover{background:var(--bg)}
.libre-suggestion-label{color:var(--text);font-size:13px;font-weight:500}
.libre-suggestion-count{color:var(--muted);font-size:11px;white-space:nowrap;margin-left:12px}
.libre-duree-link{background:none;border:none;color:var(--accent);font-size:12px;cursor:pointer;padding:4px 0;text-align:left;font-family:inherit}
.libre-duree-link:hover{text-decoration:underline}
/* v2 : lien de switch entre modes Catalogue / Inhabituelle dans op-modal-new */
.op-new-mode-link{display:inline-block;margin-top:8px;color:var(--accent);font-size:12px;text-decoration:none;font-family:inherit}
.op-new-mode-link:hover{text-decoration:underline}
.op-cat-controles{background:rgba(52,211,153,.16);color:#10b981}
.op-cat-interventions,
.op-cat-entretien{background:rgba(167,139,250,.16);color:#8b5cf6}
.op-cat-remplacements{background:rgba(251,146,60,.16);color:#ea580c}
.op-cat-suivi{background:rgba(251,191,36,.16);color:#f59e0b}
.op-card-title{font-size:14px;font-weight:600;color:var(--text);line-height:1.4}
.op-card-meta{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--text2)}
.op-card-meta span{display:inline-flex;align-items:center;gap:5px}
.op-card-meta strong{color:var(--text);font-weight:600}
.op-status{position:absolute;top:14px;right:14px;font-size:10px;font-weight:800;padding:3px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:.5px}
.op-status-a_faire{background:rgba(148,163,184,.16);color:var(--muted)}
.op-status-en_cours{background:rgba(251,191,36,.16);color:#f59e0b}
.op-status-termine{background:rgba(52,211,153,.16);color:#10b981}
.op-status-reporte{background:rgba(248,113,113,.16);color:var(--danger)}
.op-badge-source{display:inline-block;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;background:rgba(251,191,36,.14);color:#f59e0b;text-transform:uppercase;letter-spacing:.4px}

/* ── État vide (aucune tâche) ───────────────────────────────────── */
.op-empty{background:var(--card);border:1px dashed var(--border);border-radius:12px;text-align:center;padding:60px 20px;color:var(--muted);font-size:14px}
.op-empty h3{font-size:18px;color:var(--text2);margin:0 0 8px 0;font-weight:600}

/* ── Sous-onglets (Planning personnel / Planning général) ──────── */
.op-subtabs{display:inline-flex;gap:0;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:4px;margin-bottom:18px}
.op-subtab{padding:8px 16px;border-radius:8px;background:transparent;border:none;color:var(--text2);font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;transition:background .15s,color .15s}
.op-subtab:hover{color:var(--text)}
.op-subtab.active{background:var(--accent-bg);color:var(--accent)}
.op-tab-content{flex:1}

/* ── Vue Planning opérateur : tableau read-only ──────────────────── */
.op-plan-table{width:100%;border-collapse:separate;border-spacing:0;background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;font-size:13px}
.op-plan-table thead th{background:var(--bg);text-align:left;padding:12px 14px;font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}
.op-plan-table tbody td{padding:12px 14px;border-bottom:1px solid var(--border);color:var(--text2)}
.op-plan-table tbody tr:last-child td{border-bottom:none}
.op-plan-table tbody tr.mine{background:var(--accent-bg)}
.op-plan-table tbody tr.mine td{color:var(--text)}
/* v2.2.70 : cartes créneau (header prominent au-dessus, puis mini-tableau) */
.op-plan-days-wrap{display:flex;flex-direction:column;gap:22px}
.op-plan-day-section-head{display:flex;align-items:center;gap:10px;font-size:12px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.op-plan-day-section-head .op-plan-day-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.op-plan-creneaux-list{display:flex;flex-direction:column;gap:14px}
.op-plan-creneau-card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,.10),0 1px 3px rgba(0,0,0,.06);cursor:pointer;transition:box-shadow .18s,transform .12s,border-color .15s}
.op-plan-creneau-card:hover{border-color:var(--accent);box-shadow:0 12px 32px rgba(0,0,0,.14),0 4px 10px rgba(34,211,238,.20);transform:translateY(-2px)}
.op-plan-creneau-card:active{transform:translateY(0);box-shadow:0 4px 14px rgba(0,0,0,.10),0 1px 3px rgba(0,0,0,.06)}
.op-plan-creneau-header{background:var(--accent-bg);color:var(--text);border-left:4px solid var(--accent);padding:12px 18px;cursor:pointer;display:flex;align-items:center;gap:12px;flex-wrap:wrap;transition:background .15s}
.op-plan-creneau-header:hover{background:rgba(34,211,238,.18)}
.op-plan-creneau-header .op-plan-ch-chev{color:var(--accent);font-size:16px;line-height:1}
.op-plan-creneau-header .op-plan-ch-time{font-family:'SFMono-Regular',ui-monospace,Consolas,monospace;font-weight:800;font-size:15px;color:var(--accent);letter-spacing:.3px}
.op-plan-creneau-header .op-plan-ch-nom{font-weight:700;font-size:14px;color:var(--text);padding-left:10px;border-left:1px solid var(--border)}
.op-plan-creneau-header .op-plan-ch-count{background:var(--card);border:1px solid var(--border);color:var(--text2);font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px}
.op-plan-creneau-header .op-plan-ch-status{padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;background:var(--card);color:var(--accent);border:1px solid var(--accent)}
.op-plan-creneau-header .op-plan-ch-status.done{background:var(--ok,#34d399);color:#fff;border-color:var(--ok,#34d399)}
.op-plan-creneau-header .op-plan-ch-status.progress{background:var(--warn,#fbbf24);color:#000;border-color:var(--warn,#fbbf24)}
.op-plan-creneau-header .op-plan-ch-team{margin-left:auto;font-size:12px;color:var(--muted);font-weight:500;font-style:italic}
.op-plan-creneau-table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px;background:transparent}
.op-plan-creneau-table thead th{background:var(--bg);text-align:left;padding:10px 16px;font-size:10.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}
.op-plan-creneau-table tbody td{padding:11px 16px;border-bottom:1px solid var(--border);color:var(--text2)}
.op-plan-creneau-table tbody tr:last-child td{border-bottom:none}
.op-plan-creneau-table tbody tr:hover{background:var(--bg)}
.op-plan-creneau-table tbody td.op-plan-cell-mac{font-weight:600;color:var(--text)}
.op-plan-creneau-table tbody td.op-plan-cell-lbl{color:var(--text)}
/* Modal détail créneau (op) */
.op-plan-detail-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:1400;padding:20px;animation:opPlanDetFade .15s}
.op-plan-detail-box{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:640px;width:100%;max-height:85vh;overflow-y:auto;padding:22px;position:relative;animation:opPlanDetSlide .18s}
.op-plan-detail-close{position:absolute;top:12px;right:12px;width:32px;height:32px;border-radius:8px;background:var(--bg);border:1px solid var(--border);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:border-color .15s,color .15s}
.op-plan-detail-close:hover{color:var(--danger);border-color:var(--danger)}
.op-plan-detail-title{font-size:17px;font-weight:800;color:var(--text);margin-bottom:4px;padding-right:36px;display:flex;align-items:center;gap:9px}
.op-plan-detail-sub{font-size:13px;color:var(--muted);margin-bottom:16px;text-transform:capitalize}
.op-plan-detail-info{background:var(--bg);border-radius:8px;padding:10px 12px;margin-bottom:8px;font-size:13px}
.op-plan-detail-info-lbl{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.op-plan-detail-info-val{color:var(--text);font-weight:600}
.op-plan-detail-ops-lbl{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:16px 0 8px}
.op-plan-detail-op-row{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;padding:9px 12px;background:var(--bg);border-left:3px solid var(--border);border-radius:6px;margin-bottom:5px;font-size:13px}
.op-plan-detail-op-row.is-done{background:rgba(52,211,153,.10);border-left-color:var(--ok,#34d399)}
.op-plan-detail-op-lbl{flex:1;min-width:0;font-weight:600;color:var(--text)}
.op-plan-detail-op-mac{font-size:11px;color:var(--muted);margin-top:2px}
.op-plan-detail-op-badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;flex-shrink:0}
.op-plan-detail-op-badge.done{background:var(--ok,#34d399);color:#fff}
.op-plan-detail-op-badge.todo{background:var(--card);color:var(--muted);border:1px solid var(--border)}
.op-plan-detail-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:18px;padding-top:14px;border-top:1px solid var(--border)}
.op-plan-detail-actions button{padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer;border:none;transition:filter .15s}
.op-plan-detail-actions .btn-close{background:var(--accent);color:#fff}
.op-plan-detail-actions .btn-close:hover{filter:brightness(1.08)}
@keyframes opPlanDetFade{from{opacity:0}to{opacity:1}}
@keyframes opPlanDetSlide{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}

/* ── Modal saisie / création (partagé opérateur & admin) ─────────── */
.op-modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:1000;align-items:center;justify-content:center;padding:20px}
.op-modal-overlay.active{display:flex}
.op-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:520px;width:100%;max-height:90vh;overflow-y:auto;padding:22px}
.op-modal-title{font-size:16px;font-weight:700;color:var(--text);margin-bottom:6px}
.op-modal-sub{font-size:12px;color:var(--muted);margin-bottom:18px}
.op-modal .op-form-row{margin-bottom:14px}
.op-modal label{display:block;font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.op-modal input, .op-modal select, .op-modal textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-family:inherit;font-size:14px;transition:border-color .15s}
.op-modal input:focus, .op-modal select:focus, .op-modal textarea:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.op-modal textarea{resize:vertical;min-height:80px;font-family:inherit}
/* v2.6.1 : lignes « préserver ce créneau » de la modale de confirmation.
   .op-modal input{width:100%} s'appliquait a la case a cocher, qui occupait
   toute la largeur et ejectait le texte hors du cadre ; .op-modal label impose
   en plus uppercase + letter-spacing. On neutralise les deux ici — selecteurs
   plus specifiques, donc prioritaires. */
.mys-keep-row{display:flex;gap:9px;align-items:flex-start;padding:9px 11px;border:1px solid var(--border);border-radius:9px;margin-bottom:6px;cursor:pointer;background:var(--card);text-transform:none;letter-spacing:normal;font-size:13px;color:var(--text);font-weight:400}
.mys-keep-row:hover{border-color:var(--accent)}
.mys-keep-row.is-grave{border-color:var(--danger)}
/* Geometrie seule : l'apparence (boite blanche + coche accent) vient de la
   regle commune « cases a cocher natives » plus bas dans cette feuille. */
.op-modal .mys-keep-row input[type=checkbox]{width:16px;min-width:16px;height:16px;flex:0 0 16px;margin:2px 0 0 0;padding:0;box-shadow:none}
.mys-keep-txt{flex:1;min-width:0}
.mys-keep-date{display:block;font-weight:700;color:var(--text);font-size:13px;text-transform:none;letter-spacing:normal}
.mys-keep-why{display:block;font-size:12px;color:var(--muted);margin-top:3px;text-transform:none;letter-spacing:normal;font-weight:400;line-height:1.4}
.mys-keep-row.is-grave .mys-keep-why{color:var(--danger)}
.mys-keep-list{max-height:34vh;overflow-y:auto;padding-right:4px;margin-top:4px}
.op-modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:20px}
.op-modal-context{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:16px;display:flex;flex-wrap:wrap;gap:8px 14px;font-size:12px;color:var(--text2)}
.op-modal-context strong{color:var(--text);font-weight:700}

/* ═══════════════════════════════════════════════════════════ */
/* v2.2.19 : panel Alertes maintenance (dup depuis settings_page) */
/* ═══════════════════════════════════════════════════════════ */
/* ── Onglet Alertes maintenance ───────────────────────────────────── */
.maint-subtab{display:block}
.alert-row{display:flex;align-items:center;gap:14px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:8px;transition:border-color .15s}
.alert-row:hover{border-color:var(--accent)}
.alert-row.is-active{border-left:3px solid var(--success)}
.alert-row.is-inactive{border-left:3px solid var(--border)}
.alert-info{flex:1;min-width:0}
.alert-nom{font-size:14px;font-weight:600;color:var(--text);margin:0 0 2px 0}
.alert-meta{font-size:11px;color:var(--muted)}
.alert-status{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.alert-status.on{color:var(--success)}
.alert-status.off{color:var(--muted)}
.alert-actions{display:grid;grid-template-columns:110px 92px 92px;gap:6px;align-items:center;flex-shrink:0}
.alert-actions .btn-sm{width:100%;text-align:center;white-space:nowrap}
@media(max-width:900px){.alert-actions{grid-template-columns:1fr 1fr 1fr;width:100%}}
/* Toggle switch */
.toggle{position:relative;display:inline-block;width:38px;height:22px;flex-shrink:0;cursor:pointer}
.toggle input{opacity:0;width:0;height:0;position:absolute}
.toggle-track{position:absolute;inset:0;background:var(--border);border-radius:22px;transition:background .18s}
.toggle-thumb{position:absolute;top:2px;left:2px;width:18px;height:18px;background:var(--card);border-radius:50%;transition:transform .18s;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.toggle input:checked + .toggle-track{background:var(--success)}
.toggle input:checked + .toggle-track .toggle-thumb{transform:translateX(16px)}
.toggle input:disabled + .toggle-track{opacity:.5;cursor:not-allowed}
/* Modal d'aperçu / édition alerte */
.alert-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px}
.alert-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:560px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 24px 64px rgba(0,0,0,.5)}
.alert-modal-head{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border)}
.alert-modal-head h3{margin:0;font-size:15px;color:var(--text)}
.alert-modal-body{padding:18px 20px}
.alert-modal-foot{display:flex;gap:8px;justify-content:flex-end;padding:14px 20px;border-top:1px solid var(--border)}
.alert-preview-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px;background:var(--bg);border-radius:10px;border:1px dashed var(--border)}
.alert-badge{display:inline-block;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:2px 7px;border-radius:6px;margin-left:6px;vertical-align:1px}
.alert-field{margin-bottom:14px}
.alert-field-label{display:block;font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.alert-field-input,.alert-field-select{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;box-sizing:border-box}
.alert-field-input:disabled{color:var(--muted);cursor:not-allowed}
.alert-field-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.alert-field-sub{margin-top:8px;padding:10px 12px;background:var(--bg);border:1px dashed var(--border);border-radius:8px}
.alert-field-help{font-size:11px;color:var(--muted);margin-top:4px;line-height:1.5}
@media(max-width:700px){.alert-field-row{grid-template-columns:1fr}}
.alert-badge.auto{background:var(--accent-bg);color:var(--accent)}
.alert-badge.todo{background:rgba(251,191,36,.18);color:var(--warn);margin-left:4px}
.alert-row.is-todo{border-left:3px solid var(--warn)}
.alerts-filter-btn.active{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.af-md-wrap{position:relative;width:100%}
.af-md-trigger{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;font-family:inherit;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:8px;box-sizing:border-box}
.af-md-trigger:hover{border-color:var(--accent)}
.af-md-trigger-label{flex:1 1 auto;min-width:0;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.af-md-trigger-caret{flex:0 0 auto;color:var(--muted);font-size:10px}
.af-md-panel{position:absolute;top:calc(100% + 4px);left:0;right:0;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:6px;z-index:100;max-height:280px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.35);display:none}
.af-md-panel.open{display:block}
.af-md-row{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;font-size:13px;color:var(--text);cursor:pointer;user-select:none}
.af-md-row:hover{background:var(--bg)}
.af-md-row input{flex:0 0 auto;width:16px;height:16px;margin:0;cursor:pointer}
.af-md-row-text{flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.af-md-row-hint{margin-left:6px;color:var(--muted);font-weight:400;font-size:11px}
.af-md-row.is-disabled{cursor:not-allowed;opacity:.55}
.af-md-row.is-disabled .af-md-row-text{color:var(--muted)}
.af-md-sep{height:1px;background:var(--border);margin:4px 6px}
/* ── Tester sur moi : simulation pure ────────────────────────────── */
/* Pattern always-flex : un seul wrapper full-screen ; le placement est piloté
   par align-items / justify-content. Évite les conflits entre inset:0 (backdrop)
   et top/right/bottom/left (positions de coin). */
.ta-sim{position:fixed;inset:0;display:flex;z-index:2000;pointer-events:none;padding:20px;box-sizing:border-box}
.ta-sim.ta-blocking{background:rgba(0,0,0,.45);pointer-events:auto;animation:taSimFade .15s ease-out}
.ta-sim.ta-pl-center{align-items:center;justify-content:center}
.ta-sim.ta-pl-top-right{align-items:flex-start;justify-content:flex-end}
.ta-sim.ta-pl-bottom-right{align-items:flex-end;justify-content:flex-end}
.ta-sim-alert{background:var(--card);border:2px solid var(--accent);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.5);padding:16px 18px;max-height:calc(100vh - 40px);overflow-y:auto;animation:taSimSlide .2s ease-out;pointer-events:auto}
.ta-sz-small .ta-sim-alert{max-width:260px;width:100%}
.ta-sz-medium .ta-sim-alert{max-width:340px;width:100%}
.ta-sz-large .ta-sim-alert{max-width:440px;width:100%}
.ta-sim-title{font-size:18px;font-weight:700;color:var(--text);margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--accent);line-height:1.3;letter-spacing:-0.01em}
.ta-sim-actions{display:flex;gap:6px;margin-top:10px}
.ta-sim-btn{flex:1;padding:9px;border-radius:8px;font-size:13px;font-weight:600;border:none;cursor:pointer;font-family:inherit;background:var(--accent);color:#fff}
.ta-sim-btn:hover{filter:brightness(1.05)}
.ta-sim-exit{position:fixed;top:12px;left:12px;z-index:2100;background:rgba(0,0,0,.7);color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-family:inherit;cursor:pointer;pointer-events:auto}
.ta-sim-exit:hover{background:rgba(0,0,0,.9)}
.af-cl-nc-lbl:has(input:checked){border-color:var(--danger);background:rgba(248,113,113,0.10);color:var(--danger)}
/* v2.5.21 : puce COM — « cette réponse exige un commentaire ». Reprend le
   gabarit de la puce NC, en accent au lieu de danger pour que les deux se
   distinguent d'un coup d'oeil quand elles sont cochées ensemble. */
.af-cl-com-lbl:has(input:checked){border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.ta-chip{display:inline-flex;align-items:center;padding:5px 11px;border-radius:999px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:background .12s ease,color .12s ease,border-color .12s ease;font-family:inherit;line-height:1.2}
.ta-chip input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.ta-chip:hover{border-color:var(--accent)}
.ta-chip:has(input:checked){background:var(--accent);color:#fff;border-color:var(--accent)}
.ta-chip span{white-space:nowrap}
@keyframes taSimFade{from{opacity:0}to{opacity:1}}
@keyframes taSimSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:600px){
  .ta-sim{padding:12px}
  .ta-sz-small .ta-sim-alert,.ta-sz-medium .ta-sim-alert,.ta-sz-large .ta-sim-alert{max-width:calc(100vw - 24px)}
}
@media(max-width:900px){
  .alert-row{flex-wrap:wrap}
  .alert-actions{width:100%;justify-content:flex-end}
}

/* ── Sidebar : scroll vertical propre + affordance visuelle ──────── */
.sidebar{scrollbar-width:thin;scrollbar-color:transparent transparent}


/* ═══════════════════════════════════════════════════════════ */
/* v2.2.21 : styles boutons scopés au panel Alertes (dup Paramètres) */
/* ═══════════════════════════════════════════════════════════ */
.alerts-panel-embed .card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.alerts-panel-embed .btn{background:var(--accent);color:var(--accent-fg,#fff);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.alerts-panel-embed .btn:hover{filter:brightness(1.08)}
/* v2.5.20 : contraste bouton / fond. Règle : un bouton ne porte jamais la
   couleur de la surface qui le contient. Inversion systématique —
     · surface blanche (.card, .alert-modal-body) -> bouton sur var(--bg)
     · surface teintee (.alert-row, .af-cl-card)  -> bouton sur var(--card)
   Les lueurs de survol passent des rgba() cyan en dur a var(--accent-bg),
   pour suivre la palette choisie (ambre, pivoine, foret, cendre, braise). */
.alerts-panel-embed .btn-sec{background:var(--bg);border:1px solid var(--border);color:var(--text2);transition:box-shadow .2s,border-color .15s,color .15s,background .15s}
.alerts-panel-embed .btn-sec:hover{background:var(--accent-bg);border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 1px var(--accent-bg)}
.alerts-panel-embed .btn-sm{padding:6px 12px;font-size:11px;font-weight:700;border-radius:8px}
.alerts-panel-embed .btn-ghost{background:var(--bg);border:1px solid var(--border);color:var(--text2);transition:border-color .15s,color .15s,box-shadow .15s,background .15s}
.alerts-panel-embed .btn-ghost:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg);filter:none;box-shadow:0 0 0 1px var(--accent-bg)}
.alerts-panel-embed .btn-ghost.danger:hover{border-color:var(--danger);color:var(--danger);background:var(--card);box-shadow:0 0 0 1px var(--border)}
/* .alert-row est peinte en var(--bg) : ses boutons repassent en var(--card) */
.alerts-panel-embed .alert-row .btn-sm,
.alerts-panel-embed .alert-row .btn-ghost,
.alerts-panel-embed .alert-row .btn-ghost:hover,
.alerts-panel-embed .alert-row .btn-ghost.danger:hover{background:var(--card)}
/* Historique des saisies (meme vue Alertes) : le bloc filtres est pose sur une
   carte blanche, les puces de periode etaient donc blanches sur blanc. Scope
   limite a #view-controles pour ne pas toucher les autres vues, ou ces memes
   puces vivent deja sur var(--bg). */
#view-controles .date-preset-chip{background:var(--bg)}
#view-controles .date-preset-chip:hover{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
#view-controles .date-preset-chip.active{background:var(--accent-bg)}

/* ═══════════════════════════════════════════════════════════ */
/* v2.2.30 : panel Codes maintenance — CSS scopé (re-extraction propre) */
/* ═══════════════════════════════════════════════════════════ */
.maint-codes-panel-embed .sidebar-overlay {display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
.maint-codes-panel-embed h1 {font-size:22px;margin:0 0 6px}
.maint-codes-panel-embed .sub {color:var(--muted);font-size:13px;margin-bottom:22px}
.maint-codes-panel-embed .card {background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.maint-codes-panel-embed .card h2 {font-size:15px;margin:0 0 14px}
.maint-codes-panel-embed .table-wrap {overflow:auto;border-radius:10px;border:1px solid var(--border)}
.maint-codes-panel-embed table {width:100%;border-collapse:collapse;font-size:12px}
.maint-codes-panel-embed th, .maint-codes-panel-embed td {padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}
.maint-codes-panel-embed th {background:rgba(15,23,42,.35);font-weight:700;color:var(--muted);position:sticky;top:0}
body.light .maint-codes-panel-embed th {background:#f1f5f9}
.maint-codes-panel-embed td.chk {text-align:center}
.maint-codes-panel-embed .dot {display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok)}
.maint-codes-panel-embed .dot.no {background:var(--border)}
.maint-codes-panel-embed .chk-edit {width:16px;height:16px;cursor:pointer;accent-color:var(--accent)}
.maint-codes-panel-embed .cell-ov {font-size:9px;color:var(--accent);font-weight:700;letter-spacing:.02em;margin-left:6px;text-transform:uppercase}
/* ── Cases a cocher natives du module ─────────────────────────────────────
   v2.7.4 : elles utilisaient le rendu natif du navigateur, donc un carre bleu.
   Sur le fond bleu clair du bloc « Piece d'usure », le contraste etait quasi
   nul ; dans la modale de confirmation, accent-color donnait une boite pleine
   d'une autre couleur encore. Rendu unique pour les deux : boite blanche,
   bordure discrete, coche a la couleur d'accent du module.

   Liste de selecteurs explicite, et NON un balayage de tous les
   input[type=checkbox] : les interrupteurs a bascule (.toggle des alertes et
   des modeles, .op-toggle-termine, .tmpl-recur-switch) et les chips .ta-chip
   masquent leur input pour dessiner un rail ou une pastille a la place. Un
   selecteur global reafficherait ces inputs par-dessus leur propre rendu.

   Cette regle ne fait que l'apparence ; les dimensions restent posees la ou
   elles l'etaient (inline pour le bloc piece d'usure, regle dediee pour la
   modale). */
#maint-usure-block input[type=checkbox],
.op-modal .mys-keep-row input[type=checkbox]{-webkit-appearance:none;appearance:none;box-sizing:border-box;border:1.5px solid var(--border);border-radius:4px;background:#fff;display:inline-grid;place-content:center;cursor:pointer;transition:border-color .12s,box-shadow .12s}
#maint-usure-block input[type=checkbox]::before,
.op-modal .mys-keep-row input[type=checkbox]::before{content:"";width:10px;height:10px;transform:scale(0);transition:transform .12s ease-out;background:var(--accent);clip-path:polygon(14% 44%,0 60%,39% 100%,100% 18%,84% 0,39% 68%)}
#maint-usure-block input[type=checkbox]:checked,
.op-modal .mys-keep-row input[type=checkbox]:checked{border-color:var(--accent)}
#maint-usure-block input[type=checkbox]:checked::before,
.op-modal .mys-keep-row input[type=checkbox]:checked::before{transform:scale(1)}
#maint-usure-block input[type=checkbox]:hover,
.op-modal .mys-keep-row input[type=checkbox]:hover{border-color:var(--accent)}
#maint-usure-block input[type=checkbox]:focus-visible,
.op-modal .mys-keep-row input[type=checkbox]:focus-visible{outline:none;box-shadow:0 0 0 3px var(--accent-bg)}
#maint-usure-block input[type=checkbox]:disabled,
.op-modal .mys-keep-row input[type=checkbox]:disabled{opacity:.5;cursor:not-allowed}
.maint-codes-panel-embed .acc-matrix {width:100%;border-collapse:separate;border-spacing:0;font-size:12px}
.maint-codes-panel-embed .acc-matrix th {padding:8px 10px}
.maint-codes-panel-embed .acc-matrix .acc-th-lbl {margin-right:6px}
.maint-codes-panel-embed .acc-matrix .acc-expand {background:var(--accent-bg);color:var(--accent);border:none;border-radius:6px;width:20px;height:20px;font-weight:700;font-size:14px;cursor:pointer;line-height:1}
.maint-codes-panel-embed .acc-matrix .acc-expand:hover {filter:brightness(1.15)}
.maint-codes-panel-embed .acc-matrix td.acc-cell {padding:6px 8px;vertical-align:middle}
.maint-codes-panel-embed .acc-matrix td.acc-cell.readonly {opacity:.75}
.maint-codes-panel-embed .acc-matrix .acc-lvl, .maint-codes-panel-embed .acc-matrix .rd-lvl {width:auto;min-width:130px;padding:4px 8px;font-size:11px;background:var(--bg);border:1px solid var(--border);border-radius:6px}
.maint-codes-panel-embed .acc-matrix .acc-lvl.is-ov {border-color:var(--accent);box-shadow:0 0 0 2px rgba(34,211,238,.15)}
.maint-codes-panel-embed .acc-matrix .lvl-badge {display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;border:1px solid var(--border);color:var(--text2)}
.maint-codes-panel-embed .acc-matrix .lvl-badge.lvl-admin {background:rgba(139,92,246,.15);color:#a78bfa;border-color:rgba(139,92,246,.4)}
.maint-codes-panel-embed .acc-matrix .lvl-badge.lvl-write {background:var(--accent-bg);color:var(--accent);border-color:rgba(34,211,238,.35)}
.maint-codes-panel-embed .acc-matrix .lvl-badge.lvl-read {background:rgba(34,197,94,.12);color:#4ade80;border-color:rgba(34,197,94,.3)}
.maint-codes-panel-embed .acc-matrix .lvl-badge.lvl-none {background:transparent;color:var(--muted)}
.maint-codes-panel-embed .acc-matrix .acc-sub-tr td {background:rgba(15,23,42,.25);border-top:1px dashed var(--border);padding:8px 10px}
body.light .maint-codes-panel-embed .acc-matrix .acc-sub-tr td {background:#f8fafc}
.maint-codes-panel-embed .acc-matrix .acc-sub-title {font-size:11px;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.maint-codes-panel-embed .acc-matrix td.acc-sub {padding:6px 10px}
.maint-codes-panel-embed .acc-matrix .acc-sub-row {display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px dotted rgba(148,163,184,.15)}
.maint-codes-panel-embed .acc-matrix .acc-sub-row:last-child {border-bottom:none}
.maint-codes-panel-embed .acc-matrix .acc-sub-label {font-size:11px;color:var(--text2);flex:1;min-width:120px}
.maint-codes-panel-embed .acc-matrix td.acc-sub-empty {background:transparent}
.maint-codes-panel-embed .acc-hint {padding:10px 12px;margin:0 0 14px;background:rgba(34,211,238,.08);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;color:var(--text2);font-size:12px;line-height:1.55}
.maint-codes-panel-embed .acc-matrix-defaults th.acc-app-col {min-width:220px;text-align:left}
.maint-codes-panel-embed .acc-matrix-defaults th.acc-role-th {min-width:130px;text-align:center;font-size:11px}
.maint-codes-panel-embed .acc-matrix-defaults th.acc-role-th span {display:inline-block}
.maint-codes-panel-embed .acc-matrix-defaults td.acc-app-cell {min-width:220px;background:rgba(15,23,42,.15);vertical-align:middle}
body.light .maint-codes-panel-embed .acc-matrix-defaults td.acc-app-cell {background:#f8fafc}
.maint-codes-panel-embed .acc-matrix-defaults td.acc-app-cell strong {font-weight:600;color:var(--text)}
.maint-codes-panel-embed .acc-matrix-defaults td.acc-sub-label-cell {padding-left:24px;font-size:11px;color:var(--text2);background:rgba(15,23,42,.08)}
body.light .maint-codes-panel-embed .acc-matrix-defaults td.acc-sub-label-cell {background:#fafbfc}
.maint-codes-panel-embed .acc-matrix-defaults tr.acc-sub-tr td.acc-sub-cell {background:rgba(15,23,42,.08)}
body.light .maint-codes-panel-embed .acc-matrix-defaults tr.acc-sub-tr td.acc-sub-cell {background:#fafbfc}
.maint-codes-panel-embed .acc-matrix-defaults .acc-cell {text-align:center;padding:6px 8px}
.maint-codes-panel-embed .acc-lock {font-size:11px;opacity:.6}
.maint-codes-panel-embed #matrix-table, .maint-codes-panel-embed #role-legend .table-wrap {max-width:100%;overflow-x:auto}
.maint-codes-panel-embed #matrix-table table.acc-matrix, .maint-codes-panel-embed #role-legend table.acc-matrix {min-width:max-content}
.maint-codes-panel-embed .form-grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:12px}
.maint-codes-panel-embed input, .maint-codes-panel-embed select {width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit}
.maint-codes-panel-embed .btn {background:var(--accent);color:var(--accent-fg);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit}
.maint-codes-panel-embed .btn:hover {filter:brightness(1.06)}
.maint-codes-panel-embed .btn-danger {background:var(--danger);color:var(--danger-fg)}
.maint-codes-panel-embed .btn-danger:hover {filter:brightness(1.08)}
.maint-codes-panel-embed .btn-ok {background:var(--ok);color:#fff}
.maint-codes-panel-embed .btn-ok:hover {filter:brightness(1.05)}
.maint-codes-panel-embed .btn-sec {background:transparent;border:1px solid var(--border);color:var(--muted);transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.maint-codes-panel-embed .btn-sec:hover {box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
body.light .maint-codes-panel-embed .btn-sec:hover {box-shadow:0 0 0 1px rgba(8,145,178,.35),0 0 18px rgba(8,145,178,.15);border-color:rgba(8,145,178,.4);color:var(--accent)}
.maint-codes-panel-embed .row-user {display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.maint-codes-panel-embed .row-user:last-child {border-bottom:none}
.maint-codes-panel-embed .prof-ring {position:relative;flex-shrink:0;width:34px;height:34px;cursor:default}
.maint-codes-panel-embed .prof-ring svg {display:block;width:34px;height:34px}
.maint-codes-panel-embed .prof-ring-track {stroke:var(--border)}
.maint-codes-panel-embed .prof-ring-bar {stroke:var(--accent);stroke-linecap:round;transition:stroke-dashoffset .25s ease}
.maint-codes-panel-embed .prof-ring[data-tier="low"] .prof-ring-bar {stroke:var(--danger)}
.maint-codes-panel-embed .prof-ring[data-tier="mid"] .prof-ring-bar {stroke:var(--warn)}
.maint-codes-panel-embed .prof-ring[data-tier="high"] .prof-ring-bar {stroke:var(--ok)}
.maint-codes-panel-embed .prof-ring-label {
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:9px;font-weight:800;color:var(--text);letter-spacing:-.02em;
  opacity:0;transition:opacity .15s;pointer-events:none;
}
.maint-codes-panel-embed .prof-ring:hover .prof-ring-label {opacity:1}
.maint-codes-panel-embed .op-toolbar {display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.maint-codes-panel-embed .op-filter {flex:1;min-width:200px;padding:10px 14px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.maint-codes-panel-embed .op-filter:focus {border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .maint-codes-panel-embed .op-filter:focus {box-shadow:0 0 0 3px rgba(8,145,178,.1)}
.maint-codes-panel-embed .maint-doc-add-btn {display:inline-flex;align-items:center;gap:8px;padding:9px 16px;background:var(--accent);color:var(--accent-fg);border:1px solid var(--accent);border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:filter .12s,transform .06s;font-family:inherit;user-select:none}
.maint-codes-panel-embed .maint-doc-add-btn:hover {filter:brightness(1.06)}
.maint-codes-panel-embed .maint-doc-add-btn:active {transform:translateY(1px)}
.maint-codes-panel-embed .maint-doc-add-btn:disabled {opacity:.55;cursor:not-allowed;filter:none}
.maint-codes-panel-embed .maint-doc-row {display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card)}
.maint-codes-panel-embed .maint-doc-row-info {flex:1;min-width:0}
.maint-codes-panel-embed .maint-doc-row-name {font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.maint-codes-panel-embed .maint-doc-row-meta {font-size:10px;color:var(--muted);margin-top:2px;display:block}
.maint-codes-panel-embed .maint-doc-row-link {padding:4px 10px;font-size:11px;font-weight:600;color:var(--accent);border:1px solid var(--border);border-radius:6px;text-decoration:none;transition:border-color .12s}
.maint-codes-panel-embed .maint-doc-row-link:hover {border-color:var(--accent)}
.maint-codes-panel-embed .maint-doc-row-del {padding:4px 8px;font-size:11px;color:var(--danger);border:1px solid transparent;border-radius:6px;background:transparent;cursor:pointer;font-family:inherit}
.maint-codes-panel-embed .maint-doc-row-del:hover {border-color:var(--danger);background:rgba(248,113,113,.08)}
.maint-codes-panel-embed .op-form-panel {margin-bottom:16px;padding:16px 18px;border:1px solid var(--border);border-radius:12px;background:var(--bg)}
.maint-codes-panel-embed .op-form-panel h3 {margin:0 0 12px;font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
/* v2.7.4 : les champs du formulaire de code etaient en background:var(--bg),
   exactement la couleur du panneau qui les contient (.op-form-panel, ligne
   au-dessus). Champs et fond se confondaient : en clair, des cases bleues sur
   un fond bleu, seule la bordure les distinguait. On les pose sur var(--card),
   la surface "au-dessus du fond" du theme : blanc en mode clair, gris fonce en
   mode sombre. Le champ de filtre du tableau, lui, est deja sur une carte
   blanche : il garde var(--bg), qui l'y detache correctement.
   Le selecteur est porte par .op-form-panel pour ne toucher QUE ce
   formulaire, pas les autres champs du panneau des codes. */
.maint-codes-panel-embed .op-form-panel input,
.maint-codes-panel-embed .op-form-panel select{background:var(--card)}
.maint-codes-panel-embed .op-form-panel input:focus,
.maint-codes-panel-embed .op-form-panel select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
/* Meme raison pour le bouton Annuler : il etait en background:transparent,
   donc de la couleur du panneau. Scope sur .op-form-panel pour ne pas
   toucher les autres boutons secondaires du panneau des codes, qui eux
   sont deja poses sur la carte blanche. */
.maint-codes-panel-embed .op-form-panel .btn-sec{background:var(--card)}
.maint-codes-panel-embed .op-table-wrap {margin-top:4px}
.maint-codes-panel-embed .op-table {font-size:12px}
.maint-codes-panel-embed .op-table th {font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:10px 12px;white-space:nowrap}
.maint-codes-panel-embed .op-table td {padding:10px 12px;vertical-align:middle}
.maint-codes-panel-embed .op-table tbody tr:hover td {background:rgba(34,211,238,.04)}
body.light .maint-codes-panel-embed .op-table tbody tr:hover td {background:rgba(8,145,178,.05)}
.maint-codes-panel-embed .op-table tr.op-cat-row td {
  padding:14px 12px 6px;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;
  color:var(--accent);background:rgba(34,211,238,.06);border-bottom:1px solid var(--border)
}
body.light .maint-codes-panel-embed .op-table tr.op-cat-row td {background:rgba(8,145,178,.06)}
.maint-codes-panel-embed .op-table tr.op-cat-row:first-child td {padding-top:8px}
.maint-codes-panel-embed .op-code-cell {font-family:ui-monospace,monospace;font-weight:800;font-size:13px;color:var(--accent);width:56px}
.maint-codes-panel-embed .op-lbl-cell {font-weight:600;color:var(--text);max-width:280px;white-space:normal}
.maint-codes-panel-embed .op-pill {
  display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px;
  border:1px solid var(--border);text-transform:uppercase;letter-spacing:.3px;line-height:1.3
}
.maint-codes-panel-embed .op-pill.info {color:var(--text2);border-color:rgba(148,163,184,.4);background:rgba(148,163,184,.1)}
.maint-codes-panel-embed .op-pill.attention {color:var(--warn);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.12)}
.maint-codes-panel-embed .op-pill.critique {color:var(--danger);border-color:rgba(248,113,113,.45);background:rgba(248,113,113,.12)}
.maint-codes-panel-embed .op-pill.calage {color:var(--ok);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.1)}
.maint-codes-panel-embed .op-pill.arret {color:var(--warn);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.1)}
.maint-codes-panel-embed .op-pill.production {color:#60a5fa;border-color:rgba(96,165,250,.4);background:rgba(96,165,250,.1)}
.maint-codes-panel-embed .op-pill.changement {color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.1)}
.maint-codes-panel-embed .op-pill.nettoyage {color:#c084fc;border-color:rgba(192,132,252,.4);background:rgba(192,132,252,.1)}
.maint-codes-panel-embed .op-pill.autre {color:var(--muted);border-color:var(--border);background:rgba(148,163,184,.08)}
.maint-codes-panel-embed .op-pill.controles {color:var(--ok,#34d399);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.12)}
.maint-codes-panel-embed .op-pill.interventions {color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.12)}
.maint-codes-panel-embed .op-pill.entretien {color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.12)}
.maint-codes-panel-embed .op-pill.remplacements {color:#fb923c;border-color:rgba(251,146,60,.4);background:rgba(251,146,60,.12)}
.maint-codes-panel-embed .op-req {font-size:11px;font-weight:600;color:var(--muted)}
.maint-codes-panel-embed .fsc-kpi-grid {display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.maint-codes-panel-embed .fsc-kpi-card {background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px}
.maint-codes-panel-embed .fsc-kpi-label {font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.maint-codes-panel-embed .fsc-kpi-val {font-size:28px;font-weight:800;color:var(--text);line-height:1}
.maint-codes-panel-embed .fsc-kpi-badge {display:inline-block;margin-top:8px;font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px}
.maint-codes-panel-embed .fsc-kpi-badge.accent {color:var(--accent);background:rgba(34,211,238,.12)}
.maint-codes-panel-embed .fsc-kpi-badge.ok {color:var(--ok);background:rgba(52,211,153,.12)}
.maint-codes-panel-embed .fsc-kpi-badge.danger {color:var(--danger);background:rgba(248,113,113,.12)}
.maint-codes-panel-embed .fsc-kpi-badge.muted {color:var(--muted);background:rgba(148,163,184,.12)}
.maint-codes-panel-embed .fsc-claim-badge {display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:3px 10px;border-radius:6px;line-height:1.3}
.maint-codes-panel-embed .fsc-section-title {font-size:13px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px;margin:0 0 10px}
.maint-codes-panel-embed .fsc-date-inp {background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;color:var(--text);font-size:12px;font-family:inherit}
.maint-codes-panel-embed .fsc-date-inp:focus {border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.maint-codes-panel-embed .fsc-toolbar {display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.maint-codes-panel-embed .fsc-toolbar-dates {display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.maint-codes-panel-embed .fsc-toolbar-dates .fsc-range-sep {color:var(--muted);font-size:12px}
.maint-codes-panel-embed .fsc-toolbar .btn-sec {font-size:12px;padding:7px 14px}
.maint-codes-panel-embed tr.fsc-row-alert td {background:rgba(248,113,113,.08)}
body.light .maint-codes-panel-embed tr.fsc-row-alert td {background:rgba(220,38,38,.06)}
.maint-codes-panel-embed .op-req.yes {color:var(--ok)}
.maint-codes-panel-embed .op-req.no {color:var(--muted)}
.maint-codes-panel-embed .op-table th:last-child, .maint-codes-panel-embed .op-table td:last-child {text-align:right}
.maint-codes-panel-embed .op-act {display:inline-flex;gap:6px;justify-content:flex-end;flex-wrap:nowrap}
.maint-codes-panel-embed .btn-sm {padding:6px 12px;font-size:11px;font-weight:700;border-radius:8px}
.maint-codes-panel-embed .btn-ghost {background:transparent;border:1px solid var(--border);color:var(--text2);transition:border-color .15s,color .15s,box-shadow .15s,filter .15s}
.maint-codes-panel-embed .btn-ghost:hover {border-color:var(--accent);color:var(--accent);filter:none;box-shadow:0 0 0 1px rgba(34,211,238,.28),0 0 14px rgba(34,211,238,.14)}
body.light .maint-codes-panel-embed .btn-ghost:hover {box-shadow:0 0 0 1px rgba(8,145,178,.3),0 0 12px rgba(8,145,178,.1)}
.maint-codes-panel-embed .btn-ghost.danger:hover {border-color:var(--danger);color:var(--danger);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 14px rgba(248,113,113,.12)}
.maint-codes-panel-embed .pill {font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;border:1px solid var(--border);display:inline-flex;align-items:center;gap:6px;line-height:1.4}
.maint-codes-panel-embed .empl-pill {display:inline-flex;align-items:center;gap:5px;padding:4px 8px 4px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);transition:border-color .15s,background .15s}
.maint-codes-panel-embed .empl-pill:hover {border-color:var(--accent);background:rgba(34,211,238,.06)}
body.light .maint-codes-panel-embed .empl-pill:hover {background:rgba(8,145,178,.06)}
.maint-codes-panel-embed .empl-pill-code {font-family:ui-monospace,monospace;font-size:12px;font-weight:700;color:var(--text);letter-spacing:.03em}
.maint-codes-panel-embed .empl-pill-del {display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border:none;background:transparent;color:var(--muted);cursor:pointer;border-radius:4px;padding:0;transition:color .15s,background .15s;flex-shrink:0}
.maint-codes-panel-embed .empl-pill-del:hover {color:var(--danger);background:rgba(248,113,113,.14)}
.maint-codes-panel-embed .empl-allee {flex:0 0 auto;width:fit-content;min-width:120px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;overflow:hidden}
.maint-codes-panel-embed .empl-allee-hd {display:flex;align-items:center;gap:10px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.maint-codes-panel-embed .empl-allee-letter {display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:rgba(34,211,238,.12);color:var(--accent);font-size:14px;font-weight:800;font-family:ui-monospace,monospace;flex-shrink:0}
body.light .maint-codes-panel-embed .empl-allee-letter {background:rgba(8,145,178,.12)}
.maint-codes-panel-embed .empl-allee-label {font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.maint-codes-panel-embed .empl-allee-body {display:flex;flex-direction:column;gap:5px}
.maint-codes-panel-embed .empl-rangee {display:flex;align-items:flex-start}
.maint-codes-panel-embed .empl-rangee-pills {display:flex;flex-wrap:nowrap;gap:4px}
.maint-codes-panel-embed .pill--direction {border-color:rgba(244,114,182,.35);color:#f472b6;background:rgba(244,114,182,.12)}
.maint-codes-panel-embed .pill--administration {border-color:rgba(167,139,250,.38);color:#a78bfa;background:rgba(167,139,250,.12)}
.maint-codes-panel-embed .pill--administration_ventes {border-color:rgba(167,139,250,.38);color:#a78bfa;background:rgba(167,139,250,.12)}
.maint-codes-panel-embed .pill--administration_technique {border-color:rgba(99,102,241,.38);color:#818cf8;background:rgba(99,102,241,.12)}
.maint-codes-panel-embed .pill--fabrication {border-color:rgba(52,211,153,.35);color:var(--ok);background:rgba(52,211,153,.12)}
.maint-codes-panel-embed .pill--logistique {border-color:rgba(96,165,250,.35);color:#60a5fa;background:rgba(96,165,250,.12)}
.maint-codes-panel-embed .pill--comptabilite {border-color:rgba(251,191,36,.38);color:#fbbf24;background:rgba(251,191,36,.12)}
.maint-codes-panel-embed .pill--expedition {border-color:rgba(249,115,22,.38);color:#fb923c;background:rgba(249,115,22,.12)}
.maint-codes-panel-embed .pill--commercial {border-color:rgba(202,138,4,.38);color:#eab308;background:rgba(202,138,4,.12)}
.maint-codes-panel-embed .pill--encadrement_atelier {border-color:rgba(20,184,166,.38);color:#2dd4bf;background:rgba(20,184,166,.12)}
.maint-codes-panel-embed .pill--superadmin {border-color:rgba(34,211,238,.45);color:var(--accent);background:rgba(34,211,238,.14)}
.maint-codes-panel-embed .pill--inactive {border-color:rgba(148,163,184,.35);color:var(--muted);background:rgba(148,163,184,.10)}
.maint-codes-panel-embed .users-head {display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.maint-codes-panel-embed .users-head h2 {margin:0}
.maint-codes-panel-embed .users-search {display:flex;align-items:center;gap:8px;min-width:min(520px,100%)}
.maint-codes-panel-embed .users-search input {flex:1;min-width:220px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.maint-codes-panel-embed .users-search input:focus {border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .maint-codes-panel-embed .users-search input:focus {box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.maint-codes-panel-embed .users-search .hint {font-size:11px;color:var(--muted);white-space:nowrap}
.maint-codes-panel-embed .users-search select {min-width:140px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.maint-codes-panel-embed .users-search select:focus {border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .maint-codes-panel-embed .users-search select:focus {box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.maint-codes-panel-embed .tabs {display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.maint-codes-panel-embed .tabs .btn {display:inline-flex;align-items:center;gap:8px;vertical-align:middle}
.maint-codes-panel-embed .tabs .btn svg {flex-shrink:0}
.maint-codes-panel-embed .nav-group-label {font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);padding:6px 10px 4px;opacity:.7;display:flex;align-items:center;justify-content:space-between;cursor:pointer;border-radius:6px;user-select:none;transition:opacity .15s,background .15s}
.maint-codes-panel-embed .nav-group-label:hover {opacity:1;background:rgba(148,163,184,.08)}
.maint-codes-panel-embed .nav-group-chevron {display:inline-flex;flex-shrink:0;transition:transform .2s;opacity:.6}
.maint-codes-panel-embed .nav-group-label.ngl-collapsed .nav-group-chevron {transform:rotate(-90deg)}
.maint-codes-panel-embed .nav-subgroup-label {font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);padding:4px 10px 2px 14px;opacity:.55;display:flex;align-items:center;justify-content:space-between;cursor:pointer;border-radius:6px;user-select:none;transition:opacity .15s,background .15s;margin-top:2px}
.maint-codes-panel-embed .nav-subgroup-label:hover {opacity:.85;background:rgba(148,163,184,.06)}
.maint-codes-panel-embed .nav-subgroup-chevron {display:inline-flex;flex-shrink:0;transition:transform .2s;opacity:.55}
.maint-codes-panel-embed .nav-subgroup-label.nsl-collapsed .nav-subgroup-chevron {transform:rotate(-90deg)}
.maint-codes-panel-embed .hidden {display:none}
.maint-codes-panel-embed .legend {display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.maint-codes-panel-embed .legend .item {padding:12px;border:1px solid var(--border);border-radius:10px;font-size:12px}
.maint-codes-panel-embed .legend .item strong {display:block;margin-bottom:6px;font-size:13px}
.maint-codes-panel-embed .toast {position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;box-shadow:0 8px 32px rgba(0,0,0,.35);z-index:900}
.maint-codes-panel-embed .toast.err {border-left:3px solid var(--danger)}
.maint-codes-panel-embed .card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.maint-codes-panel-embed .btn{background:var(--accent);color:var(--accent-fg,#fff);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.maint-codes-panel-embed .btn:hover{filter:brightness(1.08)}
.maint-codes-panel-embed .btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);transition:box-shadow .2s,border-color .15s,color .15s,filter .15s;padding:10px 18px;font-weight:700;font-size:13px;border-radius:10px;cursor:pointer;font-family:inherit}
.maint-codes-panel-embed .btn-sec:hover{border-color:rgba(34,211,238,.45);color:var(--accent)}
.maint-codes-panel-embed .btn-sm{padding:6px 12px;font-size:11px;font-weight:700;border-radius:8px;background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;font-family:inherit;transition:border-color .12s,color .12s}
.maint-codes-panel-embed .btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.maint-codes-panel-embed .btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.maint-codes-panel-embed .btn-ghost.danger:hover{border-color:var(--danger);color:var(--danger)}
.maint-codes-panel-embed .hidden{display:none}

/* ═══════════════════════════════════════════════════════════ */
/* v2.2.38 : CSS unscoped pour modal Documents (append au body) */
/* ═══════════════════════════════════════════════════════════ */
.alert-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px}
.alert-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:560px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 24px 64px rgba(0,0,0,.5)}
.alert-modal-head{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border)}
.alert-modal-head h3{margin:0;font-size:15px;color:var(--text);font-weight:700}
.alert-modal-body{padding:18px 20px}
.alert-modal-foot{display:flex;gap:8px;justify-content:flex-end;padding:14px 20px;border-top:1px solid var(--border)}
.alert-modal-overlay .btn{background:var(--accent);color:var(--accent-fg,#fff);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.alert-modal-overlay .btn:hover{filter:brightness(1.08)}
/* v2.5.20 : meme regle de contraste dans la modale. Le corps de la modale est
   en var(--card) -> les boutons secondaires prennent var(--bg). */
.alert-modal-overlay .btn-sec{background:var(--bg);border:1px solid var(--border);color:var(--text2);transition:box-shadow .2s,border-color .15s,color .15s,background .15s;padding:10px 18px;font-weight:700;font-size:13px;border-radius:10px;cursor:pointer;font-family:inherit}
.alert-modal-overlay .btn-sec:hover{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.alert-modal-overlay .btn-sm{padding:6px 12px;font-size:11px;font-weight:700;border-radius:8px;background:var(--bg);border:1px solid var(--border);color:var(--text2);cursor:pointer;font-family:inherit;text-decoration:none;display:inline-block;line-height:1.4;transition:border-color .12s,color .12s,background .12s}
.alert-modal-overlay .btn-ghost{background:var(--bg);border:1px solid var(--border);color:var(--text2)}
.alert-modal-overlay .btn-ghost:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.alert-modal-overlay .btn-ghost.danger:hover{border-color:var(--danger);color:var(--danger);background:var(--bg)}
/* .af-cl-card (point de controle) est peinte en var(--bg) : tout ce qui vit
   dedans — boutons, champs, puce NC — repasse en var(--card). */
.alert-modal-overlay .af-cl-card .btn-sm,
.alert-modal-overlay .af-cl-card .btn-ghost,
.alert-modal-overlay .af-cl-card .btn-ghost.danger:hover,
.alert-modal-overlay .af-cl-card .alert-field-input,
.alert-modal-overlay .af-cl-card .alert-field-select{background:var(--card)}
.alert-modal-overlay .af-cl-card .btn-ghost:hover{background:var(--accent-bg)}
.af-cl-nc-lbl,.af-cl-com-lbl{background:var(--card)}
/* Bandeau "Parametres" repliable : il porte deja var(--bg) sur fond blanc,
   on renforce juste la lisibilite du libelle. */
.alert-modal-overlay #af-settings-toggle{color:var(--text)}
.alert-modal-overlay #af-settings-toggle:hover{border-color:var(--accent)}
.alert-modal-overlay a.btn-sm{text-decoration:none}
.alert-modal-overlay .maint-doc-add-btn{display:inline-flex;align-items:center;gap:8px;padding:9px 16px;background:var(--accent);color:var(--accent-fg,#fff);border:1px solid var(--accent);border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:filter .12s,transform .06s;font-family:inherit;user-select:none}
.alert-modal-overlay .maint-doc-add-btn:hover{filter:brightness(1.06)}
.alert-modal-overlay .maint-doc-add-btn:disabled{opacity:.55;cursor:not-allowed;filter:none}
</style>
</head>
<body data-maint-role="__MAINT_ROLE__">
<div class="app">
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>

  <nav class="sidebar" id="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Maintenance</span></div>
      <div class="logo-sub">by SIFA</div>
    </div>
    <button type="button" class="nav-btn adm-only active" data-view="maintenance" onclick="switchView('maintenance')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
      Suivi machine
      <span class="nav-btn-badge hidden" id="nav-maint-badge" title="Retards toutes machines confondues">0</span>
    </button>
    <button type="button" class="nav-btn adm-only" data-view="operations" onclick="switchView('operations')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18M3 12h18M3 17h18"/></svg>
      Opérations de maintenance
    </button>
    <button type="button" class="nav-btn adm-only" data-view="planning" onclick="switchView('planning')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Planning
    </button>
    <!-- v2.2.45 : "Mes tâches" admin est réservée à Manuel Lesaffre. Cachée par défaut,
         révélée en JS après loadMe() si S.me.nom contient "lesaffre" (case-insensitive). -->
    <button type="button" id="nav-mes-taches-admin" class="nav-btn adm-only" data-view="op-tasks" onclick="switchView('op-tasks')" style="display:none">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      Mes tâches
    </button>
    <!-- Alertes isolée en bas de la nav admin (séparateur au-dessus). -->
    <div class="nav-sep adm-only"></div>
    <button type="button" class="nav-btn adm-only" data-view="controles" onclick="switchView('controles')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
      Alertes
    </button>
    <button type="button" class="nav-btn op-only active" data-view="op-tasks" onclick="switchView('op-tasks')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      Mes tâches
    </button>
    <button type="button" class="nav-btn op-only" data-view="op-planning" onclick="switchView('op-planning')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Planning
    </button>
    <button type="button" class="nav-btn op-only" onclick="opOpenNewModal()" style="border-top:1px solid var(--border);margin-top:6px;padding-top:14px;color:var(--accent)">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      Enregistrer une opération
    </button>
    <!-- v2 : bouton "Intervention libre" fusionné dans "Enregistrer une opération"
         (mode Inhabituelle accessible via lien dans le modal). -->
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
        <div class="mobile-topbar-title">Suivi machine</div>
        <div class="mobile-topbar-sub">En cours de développement</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'">⌂</button>
    </div>

    <div class="content">
      <!-- View : Maintenance -->
      <div class="view adm-only" id="view-maintenance">
        <div class="page-header">
          <div>
            <div class="page-title">My<span>Maintenance</span></div>
            <div class="page-subtitle">Suivi et planification de la maintenance</div>
          </div>
        </div>

        <!-- Sélecteur de machine pour la vue Maintenance.
             Détermine quelles cartes "code maintenance périodique" s'affichent
             (Cohésio 1 ou Cohésio 2). Les cartes sont vides pour l'instant et
             seront alimentées par les saisies opérations/contrôles. -->
        <!-- Toolbar unifiee (v2.4.19) : Machine + Categorie + Statut sur une seule
             ligne (wrap responsive). Labels harmonises, toggles avec style
             coherent (chips), pastilles compteurs sur machine/categorie. -->
        <div class="maint-machine-toolbar">
          <!-- Niveau 1 : perimetre machine -->
          <div class="maint-toolbar-row maint-toolbar-row--primary">
          <label class="maint-toolbar-label">Machine</label>
          <div class="maint-machine-tabs" id="maint-machine-tabs" role="tablist">
            <button type="button" class="maint-machine-btn" data-maint-machine="Cohésio 1" onclick="setMaintMachine('Cohésio 1')">Cohésio 1<span class="maint-tab-badge hidden" data-maint-machine-badge="Cohésio 1" title="Opérations en retard sur cette machine">0</span><span class="maint-tab-badge maint-tab-badge-soon hidden" data-maint-machine-badge-soon="Cohésio 1" title="Opérations dû bientôt sur cette machine">0</span></button>
            <button type="button" class="maint-machine-btn" data-maint-machine="Cohésio 2" onclick="setMaintMachine('Cohésio 2')">Cohésio 2<span class="maint-tab-badge hidden" data-maint-machine-badge="Cohésio 2" title="Opérations en retard sur cette machine">0</span><span class="maint-tab-badge maint-tab-badge-soon hidden" data-maint-machine-badge-soon="Cohésio 2" title="Opérations dû bientôt sur cette machine">0</span></button>
          </div>
          </div>
          <!-- Niveau 2 : filtres appliques dans le perimetre machine -->
          <div class="maint-toolbar-row maint-toolbar-row--secondary">
          <label class="maint-toolbar-label">Catégorie</label>
          <div class="maint-cat-tabs" id="maint-cat-tabs" role="tablist">
            <!-- v2.7.4 : troisieme etat « Tous ». Les deux categories etaient
                 mutuellement exclusives : impossible de voir l'entretien et les
                 interventions sur le meme ecran. Meme logique que la ligne Statut
                 juste a cote (selection unique parmi N, dont un « Tous »). -->
            <button type="button" class="maint-cat-btn" data-maint-cat="all" onclick="setMaintCatFilter('all')">Tous<span class="maint-tab-badge hidden" data-maint-cat-badge="all" title="Opérations en retard, toutes catégories">0</span><span class="maint-tab-badge maint-tab-badge-soon hidden" data-maint-cat-badge-soon="all" title="Opérations dû bientôt, toutes catégories">0</span></button>
            <button type="button" class="maint-cat-btn" data-maint-cat="entretien" onclick="setMaintCatFilter('entretien')">Entretien<span class="maint-tab-badge hidden" data-maint-cat-badge="entretien" title="Opérations en retard dans cette catégorie">0</span><span class="maint-tab-badge maint-tab-badge-soon hidden" data-maint-cat-badge-soon="entretien" title="Opérations dû bientôt dans cette catégorie">0</span></button>
            <button type="button" class="maint-cat-btn" data-maint-cat="remplacements" onclick="setMaintCatFilter('remplacements')">Interventions<span class="maint-tab-badge hidden" data-maint-cat-badge="remplacements" title="Opérations en retard dans cette catégorie">0</span><span class="maint-tab-badge maint-tab-badge-soon hidden" data-maint-cat-badge-soon="remplacements" title="Opérations dû bientôt dans cette catégorie">0</span></button>
          </div>
          <span class="maint-toolbar-sep" aria-hidden="true"></span>
          <label class="maint-toolbar-label">Statut</label>
          <div class="maint-chip-group" id="maint-status-chips" role="tablist">
            <button type="button" class="maint-chip active" data-status-filter="all" onclick="setMaintStatusFilter('all')">Tous<span class="maint-chip-count" data-status-count="all">0</span></button>
            <button type="button" class="maint-chip" data-status-filter="overdue" onclick="setMaintStatusFilter('overdue')">En retard<span class="maint-chip-count" data-status-count="overdue">0</span></button>
            <button type="button" class="maint-chip" data-status-filter="soon" onclick="setMaintStatusFilter('soon')">Dû bientôt<span class="maint-chip-count" data-status-count="soon">0</span></button>
            <button type="button" class="maint-chip" data-status-filter="ok" onclick="setMaintStatusFilter('ok')">À jour<span class="maint-chip-count" data-status-count="ok">0</span></button>
            <button type="button" class="maint-chip" data-status-filter="never" onclick="setMaintStatusFilter('never')">Jamais saisi<span class="maint-chip-count" data-status-count="never">0</span></button>
          </div>
          </div>
        </div>

        <!-- Cartes des opérations de maintenance périodiques.
             Une carte par code DB avec périodique=OUI, groupées par intervalle
             (Hebdomadaire, Mensuel, Trimestriel...). La grille est régénérée
             automatiquement quand les codes changent dans Paramètres → Maintenance,
             ou quand une nouvelle saisie d'opération / contrôle est enregistrée. -->
        <div id="maint-cards-grid"></div>
      </div>

      <!-- View : Planning -->
      <div class="view adm-only" id="view-planning" style="display:none">
        <div class="page-header">
          <div>
            <div class="page-title">Planning</div>
            <div class="page-subtitle">Calendrier de maintenance</div>
          </div>
        </div>
        <div class="ops-subtabs" role="tablist" style="margin-bottom:16px">
          <button type="button" class="ops-subtab active" data-plan-subtab="calendrier" onclick="setPlanSubtab('calendrier')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            Calendrier
          </button>
          <button type="button" class="ops-subtab" data-plan-subtab="historique" onclick="setPlanSubtab('historique')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/></svg>
            Créneaux
          </button>
        </div>
        <div id="plan-subview-historique" style="display:none">
          <!-- v2.5.6 : Gestion des modeles placee AU-DESSUS de l'historique des creneaux. -->
          <div class="tmpl-manage-panel" style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
              <h2 style="margin:0;font-size:15px;font-weight:700;color:var(--text)">Gestion des modèles</h2>
              <button type="button" class="btn" style="background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:10px 16px;font-weight:700;font-size:13px;cursor:pointer" onclick="openTemplateEditor(null)">+ Nouveau modèle</button>
            </div>
            <p class="sub" style="margin-top:-4px;margin-bottom:14px;font-size:13px;color:var(--muted)">Modèles de créneau réutilisables. Active la récurrence pour que les occurrences futures se génèrent automatiquement dans le calendrier (3 mois glissants).</p>
            <div id="tmpl-manage-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
          </div>
          <!-- v2.5.31 : le panel « Créneaux supprimés » a été déplacé dans la modale
               d'édition du modèle concerné (cas minoritaire — il n'a pas à occuper
               un panel entier de l'onglet Historique). Cf. #tmpl-ed-deleted-block. -->
          <!-- v2.5.6 : Historique des creneaux avec scrollbar (aligne sur .ops-table-wrap). -->
          <div style="margin-top:24px;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px">
            <h2 style="margin:0 0 4px;font-size:15px;font-weight:700;color:var(--text)">Historique des créneaux</h2>
            <p class="sub" style="margin-top:0;margin-bottom:16px;font-size:13px;color:var(--muted)">Créneaux planifiés passés — vérifie l'avancement, réutilise les tâches en modèle.</p>
            <div id="plan-hist-list" class="plan-hist-scroll"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
          </div>
        </div>
        <div id="plan-subview-calendrier">

        <section class="cal-sec">
          <div class="cal-hdr">
            <div class="cal-title">
              <span id="cal-month-label">—</span>
            </div>
            <div class="cal-controls">
              <div class="cal-view-tabs">
                <button type="button" class="cal-view-tab" data-cal-view="month" onclick="setCalView('month')">Mois</button>
                <button type="button" class="cal-view-tab active" data-cal-view="week" onclick="setCalView('week')">Semaine</button>
                <button type="button" class="cal-view-tab" data-cal-view="day" onclick="setCalView('day')">Jour</button>
              </div>
              <div class="cal-nav">
                <button type="button" onclick="calPrev()" aria-label="Précédent">◀</button>
                <button type="button" class="today" onclick="calToday()">Aujourd'hui</button>
                <button type="button" onclick="calNext()" aria-label="Suivant">▶</button>
              </div>
            </div>
          </div>
          <!-- v2.6.0 : bandeau d'etat du chargement des creneaux. Vide (donc
               invisible) quand tout va bien. Sert a ne JAMAIS laisser une grille
               vide passer pour un planning reellement vide. -->
          <div id="cal-load-state" aria-live="polite"></div>
          <!-- Vue Mois -->
          <div class="cal-month-view" id="cal-month-view" style="display:none">
            <div class="cal-week-head" id="cal-week-head"></div>
            <div class="cal-grid" id="cal-grid"></div>
          </div>
          <!-- Vue Semaine (emploi du temps) -->
          <div class="cal-week-view cal-wv-mode-week" id="cal-week-view">
            <!-- v2.6.1 : bandeau d'aide « Cliquez sur une plage horaire libre… »
                 retire. Il occupait ~54px (hauteur + marge) en permanence pour une
                 information apprise des la premiere utilisation ; la place va a la
                 grille. _fitCalWeekBody() mesure le haut du corps de grille au
                 runtime, la hauteur disponible s'ajuste donc toute seule. -->
            <div class="cal-wv-header" id="cal-wv-header"></div>
            <!-- v2.7.3 : bande des operations non planifiees, entre les en-tetes
                 de jours et la grille horaire. Hors du conteneur de scroll :
                 elle reste visible quelle que soit l'heure affichee. -->
            <div class="cal-wv-allday is-open" id="cal-wv-allday" hidden></div>
            <div class="cal-wv-body" id="cal-wv-body"></div>
          </div>

          <!-- FAB + menu de création (vierge / depuis modèle) — v163 -->
          <button type="button" class="cal-fab" onclick="toggleCalFabMenu()" aria-label="Créer un créneau" title="Créer un créneau">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <div class="cal-fab-menu" id="cal-fab-menu" role="menu" aria-hidden="true"></div>
          <div class="cal-legend">
            <span class="cal-legend-item"><span class="cal-legend-dot today"></span> Aujourd'hui</span>
            <span class="cal-legend-item"><span class="cal-legend-dot off"></span> Hors mois</span>
            <span class="cal-legend-item"><span class="cal-legend-dot weekend"></span> Week-end</span>
          </div>
        </section>

        </div><!-- /plan-subview-calendrier -->
      </div><!-- /view-planning -->

      <!-- View : Contrôles -->
      <div class="view adm-only" id="view-controles" style="display:none">
        <div class="page-header">
          <div>
            <div class="page-title">Alertes</div>
            <div class="page-subtitle">Gestion des alertes maintenance et historique des saisies</div>
          </div>
        </div>

        <!-- v2.2.18 : subtabs retirés (Liste des contrôles supprimé). L'onglet Historique reste seul et sans en-tête. -->

        <!-- v2.2.19 : panel Alertes maintenance (dup depuis settings_page) -->
        <div class="alerts-panel-embed">
        <div id="maint-subtab-alertes" class="maint-subtab">
          <div class="card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
              <h2 style="margin:0;font-size:15px;font-weight:700">Gestion des alertes</h2>
              <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
                <button type="button" class="btn btn-sec" onclick="openAlertSettingsModal()" title="Ajuster le délai minimum entre deux alertes affichées à l'opérateur.">Délai entre alertes</button>
                <button type="button" class="btn" onclick="disableAllAlerts()" title="Bascule toutes les alertes en inactif. Aucune n'est supprimée — c'est un kill switch d'urgence.">Désactiver toutes les alertes</button>
                <button type="button" class="btn" onclick="openNewAlertModal()">+ Nouvelle alerte</button>
              </div>
            </div>
            <p class="sub" style="margin-top:-4px;margin-bottom:14px">Messages et formulaires affichés aux opérateurs lors de tâches de maintenance (contrôles qualité, vérifications, rappels…). Chaque alerte est créée manuellement depuis « + Nouvelle alerte » puis paramétrée (déclencheur, cible, formulaire de validation).</p>
            <div id="alerts-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
          </div>
        </div>
        </div><!-- /alerts-panel-embed -->

        <!-- v2.2.25 : Historique dans card blanche pour équilibre visuel avec Gestion -->
        <div style="margin-top:24px;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px">
          <h2 style="margin:0 0 4px;font-size:15px;font-weight:700;color:var(--text)">Historique des saisies</h2>
          <p class="sub" style="margin-top:0;margin-bottom:16px;font-size:13px;color:var(--muted)">Toutes les validations d'alertes effectuées par les opérateurs (lecture seule).</p>
        <div id="ctrl-subview-historique">

        <!-- Filtres Historique des contrôles -->
        <div class="filters-panel">
          <div class="filters">
            <div class="filter-group">
              <label for="filt-controles-type">Type de contrôle</label>
              <select id="filt-controles-type" class="filter-input" onchange="ctrlAutoFilter({resetPoints:true})">
                <option value="">Tous les types</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-controles-operateur">Opérateur</label>
              <select id="filt-controles-operateur" class="filter-input" onchange="ctrlAutoFilter()">
                <option value="">Tous les opérateurs</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-controles-machine">Machine</label>
              <select id="filt-controles-machine" class="filter-input" onchange="ctrlAutoFilter()">
                <option value="">Toutes les machines</option>
                <option value="Cohésio 1">Cohésio 1</option>
                <option value="Cohésio 2">Cohésio 2</option>
                <option value="DSI">DSI</option>
                <option value="Repiquage">Repiquage</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-controles-conformite">Conformité</label>
              <select id="filt-controles-conformite" class="filter-input" onchange="ctrlAutoFilter()">
                <option value="">Toutes les réponses</option>
                <option value="nc">Non-conformes uniquement</option>
                <option value="ok">Conformes uniquement</option>
              </select>
            </div>
            <!-- v2.3.36 : Du/Au fusionnés — v2.3.37 : bouton Filtrer retiré, filtrage auto sur onchange -->
            <div class="filter-group" style="flex:1 1 220px">
              <label>Période</label>
              <div style="display:flex;gap:6px;align-items:center">
                <input type="date" id="filt-controles-date-from" class="filter-input" aria-label="Du" style="min-width:0;flex:1" onchange="ctrlAutoFilter()">
                <span style="color:var(--muted);font-size:14px">→</span>
                <input type="date" id="filt-controles-date-to" class="filter-input" aria-label="Au" style="min-width:0;flex:1" onchange="ctrlAutoFilter()">
              </div>
            </div>
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
          <div id="ctrl-point-filters-row" class="ctrl-point-filters-row" style="display:none">
            <span class="filters-date-presets-label">Réponses :</span>
            <div id="ctrl-point-filters-inputs" class="ctrl-point-filters-inputs"></div>
            <button type="button" class="date-preset-chip" onclick="resetPointFilters()">Réinitialiser</button>
          </div>
        </div>

        <!-- Historique des contrôles -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Historique des alertes</div>
            <div class="ops-list-head-right">
              <!-- v2.3.35 : toggle "Fermetures auto" relocalisé du panneau filtres vers ce header, style identique à "Colonnes produit" -->
              <button type="button" class="ctrl-extra-toggle" id="ctrl-autoclose-toggle" onclick="toggleAutoClose()" title="Afficher ou masquer les lignes 'Fermée auto' générées automatiquement quand une saisie non-productive (arrêt, fin de production…) clôt une alerte périodique.">
                <span class="ctrl-extra-toggle-label">Fermetures auto</span>
                <span class="ctrl-extra-toggle-dot" id="ctrl-autoclose-toggle-dot"></span>
                <span class="ctrl-extra-toggle-state" id="ctrl-autoclose-toggle-state">OFF</span>
              </button>
              <button type="button" class="ctrl-extra-toggle" id="ctrl-extra-toggle" onclick="toggleExtraCols()" title="Afficher ou masquer les colonnes extraites de la fiche technique (référence produit, adhésif, glassine)">
                <span class="ctrl-extra-toggle-label">Colonnes produit</span>
                <span class="ctrl-extra-toggle-dot" id="ctrl-extra-toggle-dot"></span>
                <span class="ctrl-extra-toggle-state" id="ctrl-extra-toggle-state">OFF</span>
              </button>
              <div class="ops-list-count" id="ctrl-count">0 contrôle</div>
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

        </div><!-- /ctrl-subview-historique -->
        </div><!-- /section historique séparée v2.2.23 -->

        <!-- v2.2.18 : sous-onglet Liste des contrôles supprimé -->

      </div>

      <!-- View : Opérations de maintenance -->
      <div class="view adm-only" id="view-operations" style="display:none">
        <div class="page-header">
          <div>
            <div class="page-title">Opérations de maintenance</div>
            <div class="page-subtitle">Saisie et suivi des opérations effectuées</div>
          </div>
        </div>

        <!-- Sous-onglets style MyProd : Historique / Liste -->
        <div class="ops-subtabs" role="tablist">
          <button type="button" class="ops-subtab active" data-ops-subtab="historique" onclick="setOpsSubtab('historique')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/></svg>
            Historique des opérations
          </button>
          <button type="button" class="ops-subtab" data-ops-subtab="liste" onclick="setOpsSubtab('liste')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            Gestion des opérations
          </button>
        </div>

        <!-- Sous-onglet : Historique -->
        <div class="ops-subview" id="ops-subview-historique">

        <!-- Filtres Historique des opérations -->
        <div class="filters-panel">
          <div class="filters">
            <div class="filter-group">
              <label for="filt-operations-kind">Type de saisie</label>
              <select id="filt-operations-kind" class="filter-input" onchange="renderOps()">
                <option value="all">Toutes</option>
                <option value="codes">Codes catalogue</option>
                <option value="libres">Interventions libres</option>
              </select>
            </div>
            <div class="filter-group">
              <label for="filt-operations-type">Nom de l'opération</label>
              <select id="filt-operations-type" class="filter-input">
                <option value="">Toutes les opérations</option>
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
              <!-- v2.2.13 : bouton unifié "Enregistrer une opération" (fusion Intervention libre + Nouvelle saisie) -->
              <button type="button" class="ops-btn-add" onclick="adminOpenRegisterOpModal()" title="Enregistrer une opération de maintenance déjà effectuée">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                Enregistrer une opération
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
                  <th data-sort="duree_reelle_min" onclick="sortOps('duree_reelle_min')" style="width:80px">Durée<span class="sort-ico">↕</span></th>
                  <th>Commentaires</th>
                  <th>Consignes</th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="ops-tbody"></tbody>
            </table>
          </div>
        </div>

        </div><!-- /ops-subview-historique -->

        <!-- v2.2.28 : Gestion des opérations (miroir Paramètres → Codes maintenance) -->
        <div class="ops-subview" id="ops-subview-liste" style="display:none">
        <div class="maint-codes-panel-embed">
        <div id="maint-subtab-codes" class="maint-subtab">
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
            <h2 style="margin:0;font-size:15px;font-weight:700">Gestion des opérations</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
              <button type="button" class="btn btn-sec" id="libres-merge-btn" disabled onclick="libresMergeSelected()" title="Fusionne les 2 titres sélectionnés en un seul (les saisies passées sont réaffectées)." style="display:none">Fusionner sélection</button>
              <span id="libres-selection-count" style="font-size:11px;color:var(--muted);display:none"></span>
              <button type="button" class="btn" id="maint-add-btn" onclick="openMaintForm()">+ Ajouter un code</button>
            </div>
          </div>
          <!-- v2.2.36 : tabs Récurrentes / Inhabituelles -->
          <div style="display:flex;gap:6px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:12px">
            <button type="button" id="maint-tab-recurrentes" onclick="switchMaintView('recurrentes')" style="padding:6px 14px;font-size:12px;background:var(--accent);color:var(--accent-fg,#fff);border:none;font-weight:700;border-radius:8px;cursor:pointer;font-family:inherit">Récurrentes</button>
            <button type="button" id="maint-tab-inhabituelles" onclick="switchMaintView('inhabituelles')" style="padding:6px 14px;font-size:12px;background:transparent;color:var(--muted);border:1px solid var(--border);font-weight:700;border-radius:8px;cursor:pointer;font-family:inherit">Inhabituelles</button>
          </div>
          <div id="maint-view-recurrentes">
          <p class="sub" style="margin-top:-4px;margin-bottom:14px">Référentiel des codes d'opérations de maintenance regroupés en trois catégories : Contrôles, Nettoyage et Interventions.</p>
          <div id="maint-form-wrap" class="hidden op-form-panel">
            <h3 id="maint-form-title">Nouveau code</h3>
            <div class="form-grid" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))">
              <input type="text" id="maint-code" placeholder="Code (ex. 10)" inputmode="numeric" maxlength="4">
              <input type="text" id="maint-label" placeholder="Libellé">
              <select id="maint-niveau">
                <option value="1">N1</option>
                <option value="2">N2</option>
                <option value="3">N3</option>
              </select>
              <select id="maint-categorie" onchange="_maintOnCategorieChange()">
                <option value="controles">Contrôles</option>
                <option value="entretien">Nettoyage</option>
                <option value="remplacements">Interventions</option>
              </select>
              <input type="text" id="maint-intervalle" placeholder="Intervalle (ex. Hebdo, 30 jours, 6 mois)" maxlength="80">
            </div>
            <div id="maint-usure-block" style="margin-top:10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg)">
              <label style="display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;cursor:pointer;color:var(--text);white-space:nowrap">
                <input type="checkbox" id="maint-usure-on" onchange="_maintOnUsureToggle()" style="width:16px;height:16px;flex:0 0 auto;margin:0;padding:0;cursor:pointer">
                Pièce d'usure
              </label>
              <div id="maint-usure-fields" style="display:none;align-items:center;gap:12px;flex-wrap:wrap">
                <select id="maint-usure-piece" onchange="_maintOnUsurePieceChange()" title="Pièce d'usure à laquelle ce code est rattaché" style="width:auto;min-width:150px;padding:6px 10px;font-size:12px">
                  <option value="">— Choisir —</option>
                </select>
                <label style="display:flex;align-items:center;gap:7px;font-size:12px;cursor:pointer;color:var(--text);white-space:nowrap">
                  <input type="checkbox" id="maint-usure-haspos" onchange="_maintOnUsureHasPosChange()" style="width:16px;height:16px;flex:0 0 auto;margin:0;padding:0;cursor:pointer">
                  Position particulière
                </label>
                <span id="maint-usure-pos-wrap" style="display:none">
                  <input type="text" id="maint-usure-position" list="maint-usure-position-list" placeholder="ex. bande" maxlength="40" oninput="_maintOnUsurePositionInput()" style="width:120px;padding:6px 10px;font-size:12px">
                  <datalist id="maint-usure-position-list"></datalist>
                </span>
                <input type="text" id="maint-metrage-ref" placeholder="Réf. métrage (ex. 5000 m)" maxlength="80" style="width:180px;padding:6px 10px;font-size:12px">
              </div>
            </div>
            <div id="maint-usure-hint" style="display:none;font-size:11px;color:var(--muted);margin-top:6px;line-height:1.5"></div>
            <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
              <button type="button" class="btn" onclick="saveMaintForm()">Enregistrer</button>
              <button type="button" class="btn btn-sec" onclick="closeMaintForm()">Annuler</button>
            </div>
            <div id="maint-form-docs" style="display:none;margin-top:18px;padding-top:16px;border-top:1px solid var(--border)">
              <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:12px;gap:12px">
                <div>
                  <div style="font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px">Documents attaches</div>
                  <div id="maint-form-docs-hint" style="font-size:11px;color:var(--muted);margin-top:2px">Fichiers explicatifs consultes par les operateurs.</div>
                </div>
                <span style="font-size:11px;color:var(--muted);white-space:nowrap">20 Mo max</span>
              </div>
              <input type="file" id="maint-form-doc-file" style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden" onchange="_maintOnDocFileChange()">
              <div id="maint-form-docs-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px">
                <p style="color:var(--muted);font-size:12px;font-style:italic">Chargement…</p>
              </div>
              <button type="button" class="maint-doc-add-btn" id="maint-form-doc-add-btn" onclick="_maintTriggerDocPicker()">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                <span>Ajouter un fichier</span>
              </button>
            </div>
          </div>
          <div class="op-toolbar">
            <input type="search" id="maint-filter" class="op-filter" placeholder="Filtrer (code, libellé, niveau, catégorie…)" oninput="renderMaintList()">
          </div>
          <div id="maint-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
          </div><!-- /maint-view-recurrentes -->
          <!-- Vue Inhabituelles (libres) — v2.2.35 -->
          <div id="maint-view-inhabituelles" style="display:none">
            <p class="sub" style="margin-top:-4px;margin-bottom:14px">Titres saisis ponctuellement par les opérateurs, hors catalogue. Coche 2 lignes pour les fusionner ; renomme depuis la ligne pour uniformiser la terminologie ; archive uniquement les titres sans saisie associée.</p>
            <div class="op-toolbar">
              <input type="search" id="libres-filter" class="op-filter" placeholder="Filtrer (titre, code…)" oninput="renderLibresList()">
            </div>
            <div id="libres-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
          </div>
        </div>
        </div>
        </div><!-- /maint-codes-panel-embed -->
        </div><!-- /ops-subview-liste -->
      </div>
    </div>

    <!-- Conteneur opérateur (visible uniquement quand data-maint-role="operator") -->
    <div class="op-main">
      <!-- View opérateur : Mes tâches, en 2 onglets (Aujourd'hui / À venir) -->
      <div class="op-page op-only active" id="view-op-tasks">
        <div class="page-header">
          <div>
            <div class="page-title">Mes tâches</div>
            <div class="page-subtitle" id="op-tasks-count">—</div>
          </div>
          <div class="op-actions">
            <!-- v2 : bouton "Nouvelle tâche" retiré. La création de tâches se
                 fait via "Enregistrer une opération" ou "Intervention libre"
                 dans la sidebar. Les créneaux planifiés sont gérés par l'admin. -->
          </div>
        </div>
        <div class="op-tabs" role="tablist">
          <button type="button" class="op-tab active" data-op-tab="today" onclick="opSetTab('today')">
            <span class="op-tab-dot"></span>
            <span>Aujourd'hui</span>
            <span class="op-tab-count" id="op-count-today">0</span>
          </button>
          <button type="button" class="op-tab" data-op-tab="upcoming" onclick="opSetTab('upcoming')">
            <span>À venir</span>
            <span class="op-tab-count" id="op-count-upcoming">0</span>
          </button>
        </div>
        <div class="op-selector-bar op-selector-bar--toggle-only">
          <label class="op-toggle-termine">
            <input type="checkbox" id="op-show-termine" onchange="opToggleShowTermine(this.checked)">
            <span class="op-toggle-track"><span class="op-toggle-thumb"></span></span>
            <span class="op-toggle-label">Afficher terminées</span>
            <span class="op-toggle-count" id="op-toggle-count">0</span>
          </label>
        </div>
        <div class="op-tab-panel active" id="op-panel-today">
          <div id="op-cards-today"></div>
        </div>
        <div class="op-tab-panel" id="op-panel-upcoming">
          <div id="op-cards-upcoming"></div>
        </div>
      </div>

      <!-- View opérateur : Planning avec 2 sous-onglets -->
      <div class="op-page op-only" id="view-op-planning">
        <div class="page-header">
          <div>
            <div class="page-title">Planning</div>
            <div class="page-subtitle">Personnel : mes tâches du jour · Général : calendrier atelier complet</div>
          </div>
          <div class="op-actions">
            <div class="op-date-picker">
              <label for="op-plan-date">Date</label>
              <input type="date" id="op-plan-date" onchange="opLoadPlanning()">
            </div>
          </div>
        </div>
        <div class="op-subtabs" role="tablist">
          <button type="button" class="op-subtab active" data-op-plan-tab="personnel" onclick="opSetPlanTab('personnel')">Planning personnel</button>
          <button type="button" class="op-subtab" data-op-plan-tab="general" onclick="opSetPlanTab('general')">Planning général</button>
        </div>
        <div class="op-tab-content" id="op-plan-personnel"></div>
        <div class="op-tab-content" id="op-plan-general" style="display:none"></div>
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
          <div class="ops-field">
            <label class="ops-field-label" for="ops-date">Date d'opération<span class="req">*</span></label>
            <input type="datetime-local" id="ops-date" class="ops-select" required>
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="ops-duree">Durée réelle (min)</label>
            <input type="number" id="ops-duree" class="ops-input" min="0" step="1" placeholder="Optionnel">
          </div>
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="ops-comment">Commentaires</label>
            <textarea id="ops-comment" class="ops-textarea" placeholder="Notes, anomalies, pièces remplacées…"></textarea>
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

<!-- Modal : Détails d'un type d'opération (info DB + notes locales modifiables) -->
<div class="modal-overlay" id="ops-type-details-modal" onclick="if(event.target===this) closeOpsTypeDetailsModal()" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="ops-type-details-title">
    <div class="modal-head">
      <div class="modal-title" id="ops-type-details-title">Détails de l'opération</div>
      <button type="button" class="modal-close" onclick="closeOpsTypeDetailsModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="ops-type-details-form" onsubmit="saveOpsTypeDetails(event)">
      <div class="modal-body">
        <!-- Bloc info DB (lecture seule) -->
        <div id="ops-type-details-info" style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px 18px;font-size:13px"></div>
        <!-- Notes locales modifiables -->
        <div class="ops-field ops-field--full">
          <label class="ops-field-label" for="ops-type-details-text">Détails / Notes</label>
          <textarea id="ops-type-details-text" class="ops-textarea" rows="6" placeholder="Notes libres : procédure, points d'attention, pièces concernées, contacts… (non stocké en base, propre à ce navigateur)"></textarea>
          <div style="font-size:11px;color:var(--muted);margin-top:6px;font-style:italic">Ces notes ne sont pas enregistrées en base de données — uniquement sur ce navigateur.</div>
        </div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeOpsTypeDetailsModal()">Annuler</button>
        <button type="submit" class="ops-btn-add">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          Enregistrer
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

<!-- Modal : Détails du créneau (lecture + actions Modifier/Supprimer) -->
<div class="modal-overlay" id="planning-details-modal" onclick="if(event.target===this) closePlanningDetailsModal()" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="plan-det-title">
    <div class="modal-head">
      <div class="modal-title" id="plan-det-title">Détails</div>
      <button type="button" class="modal-close" onclick="closePlanningDetailsModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="ops-saisi-par ops-dt-banner">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <strong id="plan-det-date">—</strong>
        <span class="ops-dt-sep">·</span>
        <span class="ops-dt-time" id="plan-det-time">—</span>
      </div>
      <div class="plan-det-list" id="plan-det-list"></div>
    </div>
    <div class="modal-foot">
      <button type="button" class="modal-btn-ghost" onclick="closePlanningDetailsModal()">Fermer</button>
    </div>
  </div>
</div>

<!-- Modal : Créneau de maintenance (création / édition) -->
<div class="modal-overlay" id="planning-case-modal" onclick="if(event.target===this) closeCaseModal()" aria-hidden="true">
  <div class="modal-card case-modal-card" role="dialog" aria-modal="true" aria-labelledby="case-mod-title">
    <div class="modal-head">
      <div class="modal-title" id="case-mod-title">Nouveau créneau de maintenance</div>
      <button type="button" class="modal-close" onclick="closeCaseModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="case-mod-form" onsubmit="submitCaseModal(event)">
      <div class="modal-body">
        <div class="ops-saisi-par ops-dt-banner">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <strong id="case-mod-date">—</strong>
          <span class="ops-dt-sep">·</span>
          <span class="ops-dt-time" id="case-mod-time-recap">—</span>
        </div>
        <div class="ops-field">
          <label class="ops-field-label" for="case-mod-nom">Nom du créneau <span style="color:var(--muted);font-weight:400;text-transform:none;letter-spacing:0">(optionnel)</span></label>
          <input type="text" id="case-mod-nom" class="ops-input" maxlength="120" placeholder="Ex : Nettoyage matinal · Grande révision · Contrôle mensuel…">
        </div>
        <div class="ops-form-grid">
          <div class="ops-field">
            <label class="ops-field-label" for="case-mod-start">Heure de début<span class="req">*</span></label>
            <input type="time" id="case-mod-start" class="ops-input" required data-mys-tp-pair="case-mod-end">
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="case-mod-end">Heure de fin<span class="req">*</span></label>
            <input type="time" id="case-mod-end" class="ops-input" required>
          </div>
        </div>
        <div class="case-ops-section">
          <div class="case-ops-head" style="flex-wrap:wrap;gap:8px">
            <label class="ops-field-label">Opérations à effectuer<span class="req">*</span></label>
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
              <!-- v2.6.1 : l'import de modele a quitte le haut de la modale pour
                   venir ici. Il AJOUTE et fusionne (plusieurs modeles possibles)
                   au lieu de remplacer. Le select se reinitialise apres chaque
                   import pour rester une action, pas un etat. -->
              <select id="case-mod-template" class="ops-select" style="width:auto;min-width:190px"
                      onchange="applyCaseTemplate(this.value); this.value='';"
                      title="Ajoute les opérations d'un modèle au créneau">
                <option value="">+ Importer un modèle…</option>
              </select>
              <button type="button" class="case-ops-add-btn" onclick="addCaseOp()">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Ajouter une opération
              </button>
            </div>
          </div>
          <div id="case-tmpl-applied" class="case-tmpl-applied" style="display:none"></div>
          <div class="case-ops-list" id="case-mod-ops-list"></div>
        </div>
        <div class="case-ops-section">
          <div class="case-ops-head" style="flex-wrap:wrap;gap:8px">
            <label class="ops-field-label">Opérateurs assignés<span class="req" title="Au moins un opérateur recommandé">*</span></label>
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
              <button type="button" class="case-op-quick-btn" onclick="caseAddAllOperators()" title="Sélectionne tous les opérateurs actifs">+ Tous</button>
              <select class="ops-select" id="case-mod-operator-picker" style="width:auto;min-width:200px" onchange="addCaseOperatorFromPicker(this)">
                <option value="">Ajouter un opérateur…</option>
              </select>
            </div>
          </div>
          <div class="case-ops-list" id="case-mod-operators-list"></div>
        </div>
      </div>
      <div class="modal-foot">
        <!-- v2.4.29 : bouton "Enregistrer comme modele" visible uniquement en edition (CASE_EDITING_ID non null) -->
        <button type="button" class="modal-btn-ghost" id="case-mod-save-as-tmpl" onclick="saveEventAsTemplate(CASE_EDITING_ID)" style="display:none;margin-right:auto">💾 Enregistrer comme modèle</button>
        <button type="button" class="modal-btn-ghost" onclick="closeCaseModal()">Annuler</button>
        <button type="submit" class="ops-btn-add">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          <span id="case-mod-submit-label">Créer</span>
        </button>
      </div>
    </form>
  </div>
</div>

<!-- Modal : Gérer les modèles de session -->
<div class="modal-overlay" id="templates-modal" onclick="if(event.target===this) closeTemplatesModal()" aria-hidden="true">
  <div class="modal-card tmpl-modal-card" role="dialog" aria-modal="true" aria-labelledby="tmpl-mod-title">
    <div class="modal-head">
      <div class="modal-title" id="tmpl-mod-title">Modèles de session</div>
      <button type="button" class="modal-close" onclick="closeTemplatesModal()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="tmpl-toolbar">
        <div style="font-size:12px;color:var(--muted)">Un modèle = ensemble prédéfini d'opérations + machines. Applique-le en un clic depuis « Nouveau créneau ».</div>
        <button type="button" class="case-ops-add-btn" onclick="openTemplateEditor(null)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Nouveau modèle
        </button>
      </div>
      <div class="tmpl-list" id="tmpl-list"></div>
    </div>
    <div class="modal-foot">
      <button type="button" class="modal-btn-ghost" onclick="closeTemplatesModal()">Fermer</button>
    </div>
  </div>
</div>

<!-- Modal : Éditer un modèle (création / édition) -->
<div class="modal-overlay" id="tmpl-editor-modal" onclick="if(event.target===this) closeTemplateEditor()" aria-hidden="true">
  <div class="modal-card case-modal-card" role="dialog" aria-modal="true" aria-labelledby="tmpl-ed-title">
    <div class="modal-head">
      <div class="modal-title" id="tmpl-ed-title">Nouveau modèle</div>
      <button type="button" class="modal-close" onclick="closeTemplateEditor()" aria-label="Fermer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="tmpl-ed-form" onsubmit="submitTemplateEditor(event)">
      <div class="modal-body">
        <div class="ops-form-grid">
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="tmpl-ed-name">Nom<span class="req">*</span></label>
            <input type="text" id="tmpl-ed-name" class="ops-input" required maxlength="80" placeholder="Ex. Nettoyage complet">
          </div>
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="tmpl-ed-desc">Description</label>
            <input type="text" id="tmpl-ed-desc" class="ops-input" maxlength="200" placeholder="Ex. Vidange bacs + graissage roulements">
          </div>
        </div>
        <!-- v2.4.29 : bloc récurrence — permet de planifier automatiquement des créneaux futurs -->
        <div class="tmpl-recur-block">
          <div class="tmpl-recur-head">
            <span class="tmpl-recur-title">Récurrence automatique</span>
            <label class="tmpl-recur-switch" title="Activer / désactiver la récurrence">
              <input type="checkbox" id="tmpl-ed-recur-active" onchange="onTmplRecurToggle(this)">
              <span class="tmpl-recur-slider" aria-hidden="true"></span>
              <span class="tmpl-recur-switch-lbl">Activer</span>
            </label>
          </div>
          <div class="tmpl-recur-fields" id="tmpl-ed-recur-fields">
            <div class="tmpl-recur-field">
              <label for="tmpl-ed-recur-type">Fréquence</label>
              <select id="tmpl-ed-recur-type" onchange="onTmplRecurTypeChange()">
                <option value="weekly">Hebdomadaire</option>
                <option value="monthly">Mensuelle</option>
                <option value="quarterly">Trimestrielle</option>
                <option value="yearly">Annuelle</option>
              </select>
            </div>
            <div class="tmpl-recur-field" id="tmpl-ed-recur-dow-wrap">
              <label for="tmpl-ed-recur-dow">Jour de la semaine</label>
              <select id="tmpl-ed-recur-dow">
                <option value="0">Lundi</option><option value="1">Mardi</option>
                <option value="2">Mercredi</option><option value="3">Jeudi</option>
                <option value="4">Vendredi</option><option value="5">Samedi</option>
                <option value="6">Dimanche</option>
              </select>
            </div>
            <div class="tmpl-recur-field" id="tmpl-ed-recur-dom-wrap" style="display:none">
              <label for="tmpl-ed-recur-dom">Jour du mois</label>
              <input type="number" id="tmpl-ed-recur-dom" min="1" max="31" value="1">
            </div>
            <div class="tmpl-recur-field" id="tmpl-ed-recur-month-wrap" style="display:none">
              <label for="tmpl-ed-recur-month">Mois</label>
              <select id="tmpl-ed-recur-month">
                <option value="1">Janvier</option><option value="2">Février</option>
                <option value="3">Mars</option><option value="4">Avril</option>
                <option value="5">Mai</option><option value="6">Juin</option>
                <option value="7">Juillet</option><option value="8">Août</option>
                <option value="9">Septembre</option><option value="10">Octobre</option>
                <option value="11">Novembre</option><option value="12">Décembre</option>
              </select>
            </div>
            <div class="tmpl-recur-field" style="min-width:100px;flex:0 0 100px">
              <label for="tmpl-ed-recur-start">Début</label>
              <input type="time" id="tmpl-ed-recur-start" value="08:00" data-mys-tp-pair="tmpl-ed-recur-end">
            </div>
            <div class="tmpl-recur-field" style="min-width:100px;flex:0 0 100px">
              <label for="tmpl-ed-recur-end">Fin</label>
              <input type="time" id="tmpl-ed-recur-end" value="09:00">
            </div>
          </div>
          <p style="margin:10px 0 0;font-size:11px;color:var(--muted);line-height:1.4">
            Les créneaux sont générés automatiquement pour les 3 prochains mois.
            Les weekends/fériés ne sont pas exclus (déplace manuellement si besoin).
          </p>
        </div>
        <div class="case-ops-section">
          <div class="case-ops-head">
            <label class="ops-field-label">Opérations du modèle<span class="req">*</span></label>
            <button type="button" class="case-ops-add-btn" onclick="addTmplOp()">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Ajouter une opération
            </button>
          </div>
          <div class="case-ops-list" id="tmpl-ed-ops-list"></div>
        </div>
        <!-- v2.5.25 : operateurs par defaut pour la recurrence.
             v2.6.0 : masquee hors recurrence -- la liste n'est consommee que par
             _generate_events_for_template(), qui ne tourne que si la recurrence
             est active. Hors recurrence, la demander n'avait aucun effet. -->
        <div class="case-ops-section" id="tmpl-ed-default-op-section" style="margin-top:14px;display:none">
          <div class="case-ops-head" style="flex-wrap:wrap;gap:8px">
            <label class="ops-field-label">Opérateurs par défaut <span style="font-size:11px;color:var(--muted);font-weight:500;text-transform:none;letter-spacing:normal">— appliqués automatiquement aux créneaux générés par la récurrence</span></label>
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
              <button type="button" class="case-op-quick-btn" onclick="tmplAddAllDefaultOps()" title="Sélectionne tous les opérateurs actifs">+ Tous</button>
              <select class="ops-select" id="tmpl-ed-default-op-picker" style="width:auto;min-width:200px" onchange="addTmplDefaultOpFromPicker(this)">
                <option value="">Ajouter un opérateur…</option>
              </select>
            </div>
          </div>
          <div class="case-ops-list" id="tmpl-ed-default-op-list"></div>
        </div>
        <!-- v2.5.31 : occurrences supprimées DE CE MODÈLE. Repliée par défaut,
             masquée entièrement s'il n'y en a aucune (cas normal). -->
        <div class="tmpl-del-block" id="tmpl-ed-deleted-block" style="display:none">
          <button type="button" class="tmpl-del-head" id="tmpl-ed-deleted-toggle" onclick="toggleTmplDeleted()" aria-expanded="false" aria-controls="tmpl-ed-deleted-body">
            <svg class="tmpl-del-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            <span>Occurrences supprimées</span>
            <span class="tmpl-del-count" id="tmpl-ed-deleted-count">0</span>
            <span class="tmpl-del-hint">Cliquer pour afficher / restaurer</span>
          </button>
          <div class="tmpl-del-body" id="tmpl-ed-deleted-body">
            <p class="tmpl-del-sub">Occurrences de ce modèle retirées du calendrier. Les restaurer les remet à leur date d'origine sans toucher aux autres créneaux générés.</p>
            <div id="tmpl-ed-deleted-list"></div>
          </div>
        </div>
        <div id="tmpl-ed-warning" style="display:none;margin-top:12px;padding:10px 12px;border-radius:8px;background:rgba(251,191,36,.12);border:1px solid var(--warn);color:var(--warn);font-size:12px;line-height:1.5"></div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeTemplateEditor()">Annuler</button>
        <button type="submit" class="ops-btn-add">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          <span id="tmpl-ed-submit-label">Créer</span>
        </button>
      </div>
    </form>
  </div>
</div>

<div class="toast-wrap" id="toast-wrap"></div>

<script>
'use strict';

// v179 fix : MAINT_ROLE hoiste tres tot, sinon init() (fin du 1er script)
// crash sur ReferenceError quand refreshPlanning est appelee via loadPlanning.
// La const originale plus bas devient une simple reassignation defensive.
var MAINT_ROLE = (typeof document !== 'undefined' && document.body && document.body.getAttribute)
  ? (document.body.getAttribute('data-maint-role') || 'admin')
  : 'admin';

const S = { me: null };

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const VIEW_META = {
  maintenance: { title: 'Suivi machine', sub: 'En cours de développement' },
  planning:    { title: 'Planning',    sub: 'Calendrier de maintenance' },
  controles:   { title: 'Contrôles',   sub: 'Saisie et suivi des contrôles' },
  operations:  { title: 'Opérations de maintenance', sub: 'Saisie et suivi' },
  'op-tasks':    { title: 'Mes tâches', sub: 'Tâches assignées du jour' },
  'op-planning': { title: 'Planning',    sub: 'Vue globale de la journée' }
};
// Sous-onglet actif dans la vue Opérations ('historique' | 'liste').
// Mémorisé en localStorage pour retrouver l'onglet d'avant à la prochaine visite.
const OPS_SUBTAB_KEY = 'mysifa_maint_ops_subtab_v1';
function _getOpsSubtab(){
  try{ return localStorage.getItem(OPS_SUBTAB_KEY) || 'historique'; }
  catch(e){ return 'historique'; }
}
function setOpsSubtab(name){
  if(name !== 'historique' && name !== 'liste') name = 'historique';
  try{ localStorage.setItem(OPS_SUBTAB_KEY, name); }catch(e){}
  document.querySelectorAll('[data-ops-subtab]').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-ops-subtab') === name);
  });
  document.querySelectorAll('.ops-subview').forEach(div => { div.style.display = 'none'; });
  const target = document.getElementById('ops-subview-' + name);
  if(target) target.style.display = '';
  // v2.2.28 : recharge les codes maintenance à l'ouverture de l'onglet Gestion
  if(name === 'liste' && typeof loadMaintCodes === 'function') loadMaintCodes();
  // v2.2.36 : force la vue Récurrentes à chaque arrivée sur l'onglet Gestion
  if(name === 'liste' && typeof switchMaintView === 'function') switchMaintView('recurrentes');
}
// Sous-onglet actif dans la vue Contrôles ('historique' | 'liste').
const CTRL_SUBTAB_KEY = 'mysifa_maint_ctrl_subtab_v1';
function _getCtrlSubtab(){
  try{ return localStorage.getItem(CTRL_SUBTAB_KEY) || 'historique'; }
  catch(e){ return 'historique'; }
}
function setCtrlSubtab(name){
  if(name !== 'historique' && name !== 'liste') name = 'historique';
  try{ localStorage.setItem(CTRL_SUBTAB_KEY, name); }catch(e){}
  document.querySelectorAll('[data-ctrl-subtab]').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-ctrl-subtab') === name);
  });
  document.querySelectorAll('.ctrl-subview').forEach(div => { div.style.display = 'none'; });
  const target = document.getElementById('ctrl-subview-' + name);
  if(target) target.style.display = '';
}

function switchView(name){
  if(!VIEW_META[name]) return;
  // v2.2.43 : quand admin bascule sur une vue op (op-tasks / op-planning),
  // afficher .op-main + masquer les vues admin via body.admin-op-active.
  const isOpView = (name === 'op-tasks' || name === 'op-planning');
  document.body.classList.toggle('admin-op-active', isOpView);
  // Vues admin (.view) : bascule via inline display comme historiquement.
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  const admTarget = document.getElementById('view-' + name);
  if(admTarget && admTarget.classList.contains('view')) admTarget.style.display = 'flex';
  // Vues opérateur (.op-page) : bascule via classe .active (CSS gère display).
  document.querySelectorAll('.op-page').forEach(p => p.classList.remove('active'));
  const opTarget = document.getElementById('view-' + name);
  if(opTarget && opTarget.classList.contains('op-page')) opTarget.classList.add('active');
  document.querySelectorAll('.nav-btn[data-view]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === name);
  });
  if(name === 'planning'){
    // v2.5.8 : restaure le sous-onglet Planning persiste (Calendrier / Historique).
    // ATTENTION : PLAN_SUBTAB_KEY est un `const` declare APRES cette IIFE init()
    // dans la source (~ligne 8263). Appeler _getPlanSubtab()/setPlanSubtab() ici
    // leve une ReferenceError TDZ silencieusement catchee -> defaut calendrier.
    // On lit et applique le sous-onglet en direct pour bypass le TDZ. Le vrai
    // helper reprend la main sur les clics utilisateur suivants.
    let _persistedSub = 'calendrier';
    try{ _persistedSub = localStorage.getItem('mysifa_maint_plan_subtab_v1') || 'calendrier'; }catch(e){}
    if(_persistedSub !== 'calendrier' && _persistedSub !== 'historique') _persistedSub = 'calendrier';
    // Applique l'affichage du sous-onglet manuellement (bypass setPlanSubtab TDZ).
    try{
      document.querySelectorAll('[data-plan-subtab]').forEach(function(btn){
        btn.classList.toggle('active', btn.getAttribute('data-plan-subtab') === _persistedSub);
      });
      var _cal  = document.getElementById('plan-subview-calendrier');
      var _hist = document.getElementById('plan-subview-historique');
      if(_cal)  _cal.style.display  = (_persistedSub === 'calendrier') ? '' : 'none';
      if(_hist) _hist.style.display = (_persistedSub === 'historique') ? '' : 'none';
    }catch(e){}
    // Si on demarre sur Historique, ne pas gaspiller les cycles sur le calendrier :
    // charger l'historique + les templates via setPlanSubtab (defer pour eviter TDZ).
    if(_persistedSub === 'historique'){
      setTimeout(function(){ try{ if(typeof setPlanSubtab === 'function') setPlanSubtab('historique'); }catch(e){} }, 0);
      return;
    }
    // Bascule sur la vue Semaine. setCalView appelle desormais
    // renderCalFromCacheThenRefresh : rendu immediat depuis le cache (aucune
    // frame vide en revenant sur l'onglet), refetch uniquement si la plage
    // affichee n'est pas couverte par le dernier chargement.
    if(typeof setCalView === 'function') setCalView('week');
    else renderCal();
    // v2.5.9 / v2.6.0 : le setTimeout(0) reste necessaire au boot -- refreshPlanning
    // utilise _fmtDateISO, declare dans un <script> SUIVANT. Tant que script1
    // (init) tourne, script2 n'est pas parse. On force un refresh a l'arrivee
    // pour refleter les modifs faites ailleurs, mais l'affichage ne depend plus
    // de ce fetch : les creneaux en cache sont deja a l'ecran, et un echec
    // conserve desormais l'affichage au lieu de le vider.
    // Les rerenders aveugles a 150 ms et 500 ms sont supprimes : ils masquaient
    // le symptome sans traiter la cause (grille vide pendant le fetch) et
    // provoquaient trois reconstructions completes du DOM par visite.
    setTimeout(function(){
      refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
    }, 0);
  }
  // Vues opérateur : recharge la liste à l'arrivée.
  if(name === 'op-tasks' && typeof opLoadTasks === 'function'){
    opLoadTasks();
  }
  if(name === 'op-planning' && typeof opLoadPlanning === 'function'){
    opLoadPlanning();
  }
  // À l'arrivée sur la vue Opérations, restaure le dernier sous-onglet utilisé.
  if(name === 'operations'){
    setOpsSubtab(_getOpsSubtab());
  }
  // Idem pour la vue Contrôles.
  if(name === 'controles'){
    setCtrlSubtab(_getCtrlSubtab());
  }
  // Recharge la liste des codes maintenance a chaque arrivee sur les vues qui
  // l'utilisent, pour refleter les changements faits dans Parametres -> Maintenance.
  if(name === 'maintenance' || name === 'operations'){
    // Invalide le cache wearparts pour forcer un nouveau fetch (sinon on garde
    // les dernieres dates / metrage en memoire alors que la DB a evolue).
    // v2.5.7 : invalidation COMPLETE. Avant on ne remettait que `machine` a
    // null en laissant _cacheKey en place — le fetch etait alors court-circuite
    // et les cartes restaient sur « Chargement… ».
    if(typeof _invalidateWearPartCache === 'function') _invalidateWearPartCache();
    if(typeof loadOpsTypes === 'function' && typeof renderOpsTypes === 'function'){
      loadOpsTypes().then(() => {
        renderOpsTypes();
        if(typeof renderMaintCards === 'function') renderMaintCards();
      }).catch(() => {});
    }
  }
  if(name === 'controles'){
    if(typeof loadCtrlTypes === 'function' && typeof renderCtrlTypes === 'function'){
      loadCtrlTypes().then(() => renderCtrlTypes()).catch(() => {});
    }
    // v2.2.19 : recharge alertes + réglages à chaque arrivée sur la vue Alertes
    if(typeof loadAlerts === 'function') loadAlerts();
    if(typeof loadAlertSettings === 'function') loadAlertSettings();
  }
  const meta = VIEW_META[name];
  const t = document.querySelector('.mobile-topbar-title');
  const s = document.querySelector('.mobile-topbar-sub');
  if(t) t.textContent = meta.title;
  if(s) s.textContent = meta.sub;
  try{ history.replaceState(null, '', '#' + name); }catch(e){}
  closeSidebar();
}

// =========================================================================
// Planning — calendrier mensuel + vue Semaine (style MyProd)
// =========================================================================
// v2.6.1 : journee complete. Avant 6h→21h, ce qui tronquait tout creneau
// debordant de la plage (ex. un nettoyage 19:00–23:00 s'arretait visuellement
// a 21:00) et rendait impossible la planification d'une intervention de nuit.
// Toutes les positions verticales sont calculees relativement a
// CAL_HOUR_START, donc changer ces deux constantes suffit : blocs d'evenement,
// clic sur cellule, glisser-deposer et redimensionnement suivent.
const CAL_HOUR_START = 0;
const CAL_HOUR_END   = 24;   // exclusif (affiche 00h → 23h)
const CAL_HOUR_PX    = 62;
// Marge laissee au-dessus du premier creneau lors du recentrage automatique.
const CAL_AUTOSCROLL_MARGIN = 28;
function _calWeekMondayOf(d){
  const r = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const off = (r.getDay() + 6) % 7;
  r.setDate(r.getDate() - off);
  return r;
}
const CAL_STATE = {
  view: 'week',
  year:  new Date().getFullYear(),
  month: new Date().getMonth(),
  weekStart: _calWeekMondayOf(new Date()),
  dayDate:   new Date(),
};
// Palette de couleurs unies pour différencier les types d'opérations
const CAL_EVENT_PALETTE = [
  { bg:'#0891b2', fg:'#ffffff' }, // cyan
  { bg:'#7c3aed', fg:'#ffffff' }, // violet
  { bg:'#db2777', fg:'#ffffff' }, // rose
  { bg:'#dc2626', fg:'#ffffff' }, // red
  { bg:'#ea580c', fg:'#ffffff' }, // orange
  { bg:'#ca8a04', fg:'#1a1207' }, // amber
  { bg:'#65a30d', fg:'#0e1a04' }, // lime
  { bg:'#059669', fg:'#ffffff' }, // emerald
  { bg:'#0d9488', fg:'#ffffff' }, // teal
  { bg:'#0284c7', fg:'#ffffff' }, // sky
  { bg:'#4f46e5', fg:'#ffffff' }, // indigo
  { bg:'#9333ea', fg:'#ffffff' }, // purple
];
function _opTypePalette(opTypeId){
  let hash = 0;
  const s = String(opTypeId || '');
  for(let i = 0; i < s.length; i++){
    hash = ((hash << 5) - hash) + s.charCodeAt(i);
    hash |= 0;
  }
  return CAL_EVENT_PALETTE[Math.abs(hash) % CAL_EVENT_PALETTE.length];
}
// État des opérations planifiées (drag & drop sur la vue Semaine).
// Depuis Commit B2, le calendrier est branché sur l'API /api/maintenance/events
// (au lieu du localStorage). Chaque event contient N ops et M opérateurs assignés.
// loadPlanning() lance le fetch en tâche de fond puis re-render : les callers
// peuvent rester synchrones. Pour un rafraîchissement AVANT rendu, utiliser
// refreshPlanning() (async, à await avant renderCal).
// v2.6.0 : PLANNING_STATE porte desormais l'etat de chargement, la fenetre de
// dates couverte par le dernier fetch reussi, et la promesse en vol.
//   status  : 'idle' | 'loading' | 'loaded' | 'error'
//   from/to : bornes ISO de la fenetre chargee -> permet de detecter qu'une
//             navigation calendrier sort des donnees en memoire (bug ou les
//             fleches ne refetchaient jamais : au-dela de +/-90 j, vide a vie).
//   _inflight : promesse partagee. Deux appels concurrents (init + switchView,
//             ou switchView + une action utilisateur) ne declenchent plus deux
//             GET /events identiques -- chaque requete relance _ensure_schema et
//             la generation des recurrences cote serveur, c'est le poste de
//             lenteur qui laissait la grille vide plusieurs secondes.
const PLANNING_STATE = {
  list: [], _lastLoad: 0,
  status: 'idle', from: null, to: null, _inflight: null, _everLoaded: false,
};

function _apiEventToClient(ev){
  // Convertit un event {id, machine, date_prevue, heure_debut, heure_fin,
  // ops:[{id, code, code_label, ...}], operators:[{id, nom}]} vers la
  // structure attendue par renderCalMonth/Week/Day (héritée du localStorage).
  const opsClient = (ev.ops || []).map(o => {
    const t = (typeof OPS_TYPES_STATE !== 'undefined' && OPS_TYPES_STATE && Array.isArray(OPS_TYPES_STATE.list))
      ? OPS_TYPES_STATE.list.find(x => x.id === o.code) : null;
    // machines : la liste renvoyée par l'API (fallback géré serveur).
    const machines = Array.isArray(o.machines) ? o.machines.slice() : [];
    return {
      _op_id: o.id,
      opTypeId: o.code,
      opName: (t && t.nom) || o.code_label || o.code,
      opNiveau: (t && t.niveau) || null,
      opFreq: (t && t.frequence) || '',
      machines: machines,
      statut: o.statut,
      duree_reelle_min: o.duree_reelle_min,
      pieces_changees: o.pieces_changees,
      observations: o.observations,
      done_at: o.done_at,
      done_by: o.done_by,
      done_by_nom: o.done_by_nom || null,
      updated_by: o.updated_by,
      invalidated_at: o.invalidated_at || null,
      invalidated_by: o.invalidated_by || null,
      invalidated_by_nom: o.invalidated_by_nom || null,
      consignes: o.consignes || '',
    };
  });
  return {
    id: ev.id,
    machine: ev.machine,
    nom: ev.nom || '',
    date: ev.date_prevue,
    start: ev.heure_debut || '',
    end: ev.heure_fin || '',
    operations: opsClient,
    operators: ev.operators || [],
    source: ev.source,
    template_id: ev.template_id || null,
    // v2.6.1 : discriminant entre les deux facons d'etre lie a un modele.
    // template_origin_date n'est pose QUE par _generate_events_for_template(),
    // c.-a-d. par la generation d'une recurrence. Un creneau ou l'on a
    // simplement importe un modele depuis la liste des operations porte un
    // template_id mais PAS d'origin_date.
    template_origin_date: ev.template_origin_date || null,
    created_at: ev.created_at,
    updated_at: ev.updated_at,
  };
}

// Date pivot de la fenetre a charger : la date reellement affichee, pas
// « aujourd'hui ». CAL_STATE n'a jamais eu de propriete `date`, donc l'ancien
// code retombait systematiquement sur new Date() -- d'ou le planning vide des
// qu'on naviguait a plus de 90 jours.
function _planningPivotDate(){
  if(!CAL_STATE) return new Date();
  if(CAL_STATE.view === 'week' && CAL_STATE.weekStart) return new Date(CAL_STATE.weekStart);
  if(CAL_STATE.view === 'day'  && CAL_STATE.dayDate)   return new Date(CAL_STATE.dayDate);
  if(CAL_STATE.view === 'month') return new Date(CAL_STATE.year, CAL_STATE.month, 15);
  return new Date();
}

// La plage visible a-t-elle besoin d'un nouveau fetch ? On garde une marge de
// 14 jours pour ne pas refetcher a chaque clic sur les fleches en bord de
// fenetre.
function _planningNeedsFetch(){
  if(PLANNING_STATE.status === 'idle' || !PLANNING_STATE.from || !PLANNING_STATE.to) return true;
  const pivot = _planningPivotDate();
  const lo = new Date(pivot); lo.setDate(pivot.getDate() - 14);
  const hi = new Date(pivot); hi.setDate(pivot.getDate() + 14);
  return _fmtDateISO(lo) < PLANNING_STATE.from || _fmtDateISO(hi) > PLANNING_STATE.to;
}

async function refreshPlanning(){
  // Pre-charge les templates en tache de fond (pour le badge "depuis modele").
  // v179 fix : TEMPLATES_STATE et loadTemplates sont definis dans un <script>
  // block ulterieur — ne pas crasher si pas encore disponibles au moment ou
  // init() appelle loadPlanning() puis refreshPlanning().
  if(MAINT_ROLE === 'admin'
     && typeof TEMPLATES_STATE !== 'undefined'
     && TEMPLATES_STATE && TEMPLATES_STATE.list === null
     && typeof loadTemplates === 'function'){
    loadTemplates().catch(() => {});
  }
  // v2.6.0 : dedup. Un fetch deja en vol -> on attend le meme au lieu d'en
  // lancer un second identique.
  if(PLANNING_STATE._inflight) return PLANNING_STATE._inflight;
  const pr = _doRefreshPlanning();
  PLANNING_STATE._inflight = pr;
  try{ await pr; }
  finally{ PLANNING_STATE._inflight = null; }
  return pr;
}

async function _doRefreshPlanning(){
  // _fmtDateISO vit dans un <script> ulterieur : au boot il peut ne pas etre
  // encore parse. On sort proprement en laissant le status a 'idle' pour qu'un
  // appel ulterieur retente, au lieu de vider la liste.
  if(typeof _fmtDateISO !== 'function') return;
  PLANNING_STATE.status = 'loading';
  try{ _renderPlanningLoadState(); }catch(_){}
  // Charge une fenêtre large autour de la date affichée : ±90 jours.
  const pivot = _planningPivotDate();
  const from = new Date(pivot); from.setDate(pivot.getDate() - 90);
  const to   = new Date(pivot); to.setDate(pivot.getDate() + 90);
  const fromIso = _fmtDateISO(from), toIso = _fmtDateISO(to);
  try{
    const url = '/api/maintenance/events?date_from=' + fromIso +
                '&date_to=' + toIso + '&_=' + Date.now();
    const r = await fetch(url, { credentials: 'include', cache: 'no-store' });
    if(!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    PLANNING_STATE.list = (d.events || []).map(_apiEventToClient);
    PLANNING_STATE.from = fromIso;
    PLANNING_STATE.to = toIso;
    PLANNING_STATE._lastLoad = Date.now();
    PLANNING_STATE.status = 'loaded';
    PLANNING_STATE._everLoaded = true;
  }catch(e){
    // v2.6.0 : NE PLUS VIDER la liste. Une grille vide est indiscernable d'un
    // planning reellement vide -- un utilisateur mal informe conclut qu'il n'y
    // a rien de planifie. On conserve le dernier etat connu et on l'annonce.
    PLANNING_STATE.status = 'error';
  }
  try{ _renderPlanningLoadState(); }catch(_){}
}

// ── v2.6.0 : rendu des etats de chargement du calendrier ──────────────
// Motif de blocs fantomes, deterministe (pas de Math.random : le skeleton ne
// doit pas sautiller entre deux rendus). Lun..Ven seulement, [heure, duree].
const _CAL_SKEL_PATTERN = [
  [[8,1],[13,2]], [[8,1],[16,1]], [[9,1],[14,1]],
  [[8,1],[11,1],[15,1]], [[8,2]], [], []
];

function _clearCalSkeletons(){
  document.querySelectorAll('.cal-skel').forEach(el => el.remove());
}

function _paintCalSkeletons(){
  _clearCalSkeletons();
  const px = (CAL_STATE && CAL_STATE.view === 'day') ? 72 : CAL_HOUR_PX;
  const cols = document.querySelectorAll('#cal-wv-body .cal-wv-day-col');
  cols.forEach((col, idx) => {
    // En vue Jour il n'y a qu'une colonne : on prend un motif fourni.
    const pattern = (cols.length === 1) ? _CAL_SKEL_PATTERN[3] : (_CAL_SKEL_PATTERN[idx] || []);
    pattern.forEach(([h, dur]) => {
      const el = document.createElement('div');
      el.className = 'cal-skel';
      el.style.top = ((h - CAL_HOUR_START) * px) + 'px';
      el.style.height = Math.max(22, dur * px - 2) + 'px';
      el.style.left = '3px';
      el.style.right = '3px';
      col.appendChild(el);
    });
  });
  // Vue Mois : quelques chips fantomes dans les cases de semaine.
  document.querySelectorAll('#cal-grid .cal-cell:not(.cal-cell-off) .cal-day-events')
    .forEach((box, idx) => {
      if(idx % 7 >= 5) return;           // pas de week-end
      if(box.children.length) return;    // deja des vrais creneaux
      const n = (idx % 3 === 0) ? 2 : 1;
      for(let k = 0; k < n; k++){
        const chip = document.createElement('div');
        chip.className = 'cal-skel cal-skel-chip';
        box.appendChild(chip);
      }
    });
}

function _renderPlanningLoadState(){
  const box = document.getElementById('cal-load-state');
  const st = PLANNING_STATE.status;
  // Premier chargement de la session : skeleton. Rafraichissements suivants :
  // silencieux, les creneaux deja affiches restent a l'ecran.
  const firstLoad = (st === 'loading' && !PLANNING_STATE._everLoaded);
  if(firstLoad) { try{ _paintCalSkeletons(); }catch(_){} }
  else { try{ _clearCalSkeletons(); }catch(_){} }
  try{
    document.getElementById('cal-week-view')
      ?.classList.toggle('cal-hide-hint', firstLoad || st === 'error');
  }catch(_){}
  if(!box) return;
  if(firstLoad){
    box.innerHTML = '<div class="cal-load-bar is-loading">' +
      '<span class="cal-load-spin" aria-hidden="true"></span>' +
      '<span class="cal-load-bar-txt">Chargement des cr\u00e9neaux\u2026</span></div>';
    return;
  }
  if(st === 'error'){
    // Message differencie : sans donnees en cache, l'utilisateur doit savoir
    // que le vide affiche n'est PAS un planning vide.
    const msg = PLANNING_STATE._everLoaded
      ? 'Cr\u00e9neaux non rafra\u00eechis \u2014 l\'affichage peut \u00eatre p\u00e9rim\u00e9.'
      : 'Impossible de charger les cr\u00e9neaux. Le calendrier ci-dessous n\'est pas \u00e0 jour \u2014 ne le consid\u00e8re pas comme vide.';
    box.innerHTML = '<div class="cal-load-bar is-error">' +
      '<span class="cal-load-bar-txt">\u26a0 ' + msg + '</span>' +
      '<button type="button" class="cal-load-retry" onclick="retryPlanningLoad()">R\u00e9essayer</button></div>';
    return;
  }
  box.innerHTML = '';
}

function retryPlanningLoad(){
  PLANNING_STATE.status = 'idle';
  refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
}

// ── v2.6.0 : alignement header / corps de la vue Semaine ───────────────
// .cal-wv-body est un conteneur de scroll (overflow:auto) : sa gouttiere de
// scrollbar retrecit sa boite de contenu. .cal-wv-header, lui, ne scrolle pas,
// donc `scrollbar-gutter:stable` y est inerte (la propriete ne s'applique qu'aux
// conteneurs de scroll). Les 7 colonnes 1fr du header etaient donc calculees sur
// une largeur plus grande que celles du corps -> derive cumulative vers la
// droite, visible surtout sur Sam/Dim. On reporte la largeur reelle de la
// gouttiere sur le padding droit du header.
function _syncCalHeaderGutter(){
  const body = document.getElementById('cal-wv-body');
  const head = document.getElementById('cal-wv-header');
  if(!body || !head) return;
  const gutter = Math.max(0, body.offsetWidth - body.clientWidth);
  head.style.paddingRight = gutter ? (gutter + 'px') : '';
  // v2.7.3 : la bande « non planifie » est un troisieme frere sur la meme
  // grille de colonnes et ne scrolle pas non plus -> meme correction.
  const band = document.getElementById('cal-wv-allday');
  if(band) band.style.paddingRight = gutter ? (gutter + 'px') : '';
}
// v2.6.1 : la grille horaire est bornee a la hauteur REELLEMENT disponible
// sous elle, pour que le cadre .cal-sec tienne entierement dans la fenetre.
//
// Avant : `max-height:75vh` en dur dans le CSS. S'y ajoutaient l'en-tete de
// page, les sous-onglets, le bandeau d'aide, l'en-tete de grille, la legende et
// les 24px de padding de la section — soit bien au-dela de 100vh. Le bas du
// cadre passait donc sous la ligne de flottaison et il fallait faire defiler la
// PAGE pour l'atteindre, au lieu de faire defiler les heures DANS la grille.
const CAL_WV_MIN_HEIGHT = 260;   // plancher : en dessous, la grille est inutilisable
const CAL_WV_BOTTOM_GAP = 8;     // respiration sous le cadre
function _fitCalWeekBody(){
  const body = document.getElementById('cal-wv-body');
  if(!body) return;
  const sec = body.closest('.cal-sec');
  if(!sec) return;
  // Section masquee (autre vue, autre sous-onglet) : les rects valent 0, on ne
  // calcule rien. Le prochain rendu rappellera cette fonction.
  if(sec.offsetHeight === 0) return;
  // Position du haut de la grille dans le DOCUMENT, pas dans le viewport : on
  // reajoute le scroll courant. Sans ca, mesurer alors que la page est deja
  // defilee donnerait une hauteur disponible surevaluee, la grille grandirait,
  // la page defilerait davantage — emballement a chaque appel.
  const scrolled = document.scrollingElement ? document.scrollingElement.scrollTop : 0;
  const top = body.getBoundingClientRect().top + scrolled;
  if(top <= 0) return;
  // Ce qui doit rester visible SOUS la grille : legende + padding + marge bas.
  const cs = getComputedStyle(sec);
  let below = (parseFloat(cs.paddingBottom) || 0) + (parseFloat(cs.marginBottom) || 0);
  const legend = sec.querySelector('.cal-legend');
  if(legend && legend.offsetHeight){
    below += legend.offsetHeight + (parseFloat(getComputedStyle(legend).marginTop) || 0);
  }
  const avail = window.innerHeight - top - below - CAL_WV_BOTTOM_GAP;
  body.style.maxHeight = Math.max(CAL_WV_MIN_HEIGHT, Math.round(avail)) + 'px';
}

// v2.6.1 : avec 24 heures affichees, la grille fait ~1490px pour une zone
// visible de ~360px. Sans recentrage, le planning s'ouvrirait sur 00:00 et il
// faudrait faire defiler jusqu'aux creneaux. On se cale donc sur le creneau le
// plus tot de la periode affichee ; a defaut (semaine vide) sur l'heure
// courante.
//
// Le drapeau est indispensable : le recentrage ne doit avoir lieu qu'apres un
// RENDU (changement de semaine, de vue, arrivee sur l'onglet), jamais sur un
// simple redimensionnement — sinon on ecraserait la position de defilement que
// l'utilisateur vient de choisir a la main.
let _calAutoScrollPending = false;
let _calSavedScrollTop = null;
// Le recentrage n'est arme que par un changement de CONTEXTE : navigation
// (semaine/jour precedent ou suivant, Aujourd'hui), changement de vue, arrivee
// sur l'onglet Calendrier.
//
// Il ne DOIT PAS l'etre par un simple re-rendu consecutif a une modification de
// donnees — creation, deplacement ou suppression d'un creneau repassent par
// renderCalWeek(), et rearmer ici ramenait l'utilisateur au premier creneau de
// la semaine juste apres qu'il ait cree le sien. C'est pour ca que l'appel a
// ete retire de la fin des fonctions de rendu.
function _requestCalAutoScroll(){
  // v2.6.1 : pendant un glisser-deposer inter-semaines, la navigation est
  // provoquee par le geste lui-meme. Recentrer ferait glisser les colonnes
  // sous le curseur en plein drop — on garde la position telle quelle.
  try{ if(_CAL_DRAG && _CAL_DRAG.active) return; }catch(_){}
  _calAutoScrollPending = true;
}
// A appeler juste avant `body.innerHTML = ...` : le remplacement du contenu
// remet scrollTop a 0, il faut donc memoriser la position avant, pour pouvoir
// la rendre a l'utilisateur apres un re-rendu sans changement de contexte.
function _saveCalScroll(){
  if(_calAutoScrollPending){ _calSavedScrollTop = null; return; }
  const body = document.getElementById('cal-wv-body');
  if(body && body.clientHeight) _calSavedScrollTop = body.scrollTop;
}
function _autoScrollCalWeekBody(){
  const body = document.getElementById('cal-wv-body');
  if(!body) return;
  // clientHeight nul = grille pas encore mesurable (section masquee) : on garde
  // l'etat en attente pour retenter au prochain passage.
  if(!body.clientHeight) return;
  if(_calAutoScrollPending){
    _calAutoScrollPending = false;
    _calSavedScrollTop = null;
    // On lit la position deja posee sur les blocs par _makeEventBlock plutot que
    // de recalculer depuis le modele : une seule source de verite.
    let target = null;
    body.querySelectorAll('.cal-event').forEach(el => {
      const t = parseFloat(el.style.top);
      if(!isNaN(t) && (target === null || t < target)) target = t;
    });
    if(target === null){
      const px = (CAL_STATE && CAL_STATE.view === 'day') ? 72 : CAL_HOUR_PX;
      target = (new Date().getHours() - CAL_HOUR_START) * px;
    }
    body.scrollTop = Math.max(0, target - CAL_AUTOSCROLL_MARGIN);
    return;
  }
  // Re-rendu sans changement de contexte : on restaure la position exacte que
  // l'utilisateur avait avant. La restauration a lieu dans le meme
  // requestAnimationFrame que le rendu, donc avant le paint : aucun saut visible.
  if(_calSavedScrollTop != null){
    body.scrollTop = _calSavedScrollTop;
    _calSavedScrollTop = null;
  }
}

let _calGutterRaf = 0;
function _scheduleCalHeaderGutterSync(){
  if(_calGutterRaf) return;
  _calGutterRaf = requestAnimationFrame(() => {
    _calGutterRaf = 0;
    // v2.6.1 : l'ajustement de hauteur passe AVANT la synchro de gouttiere —
    // changer la hauteur peut faire apparaitre ou disparaitre la scrollbar
    // verticale, donc modifier la largeur de gouttiere a reporter sur le header.
    try{ _fitCalWeekBody(); }catch(_){}
    try{ _syncCalHeaderGutter(); }catch(_){}
    // Apres la hauteur : scrollTop n'a de sens qu'une fois la zone visible connue.
    try{ _autoScrollCalWeekBody(); }catch(_){}
  });
}
window.addEventListener('resize', _scheduleCalHeaderGutterSync);

function loadPlanning(){
  // Sync façade : lance un refresh async en arrière-plan puis re-render à
  // l'arrivée. Les callers historiques ne changent pas de comportement.
  refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
}

// v2.6.0 : rafraichit uniquement si la plage visible n'est pas couverte par le
// dernier fetch. Rend d'abord depuis le cache (affichage instantane), puis
// refetch en tache de fond si necessaire -- plus aucune frame vide en revenant
// sur l'onglet Planning.
function renderCalFromCacheThenRefresh(force){
  try{ renderCal(); }catch(e){}
  if(!force && !_planningNeedsFetch()){
    try{ _renderPlanningLoadState(); }catch(_){}
    return;
  }
  refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
}

function savePlanning(){
  // No-op : toute écriture passe désormais par l'API (POST/PATCH/DELETE).
  // Cette fonction est conservée pour ne pas casser les callers historiques.
}
const CAL_WDAYS_FULL = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];
const CAL_WDAYS_SHORT = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];
const CAL_MONTHS = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

function setCalView(v){
  if(v !== 'month' && v !== 'week' && v !== 'day') return;
  CAL_STATE.view = v;
  document.querySelectorAll('[data-cal-view]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-cal-view') === v);
  });
  const mv = document.getElementById('cal-month-view');
  const wv = document.getElementById('cal-week-view');
  if(mv) mv.style.display = (v === 'month') ? '' : 'none';
  if(wv){
    wv.style.display = (v === 'month') ? 'none' : '';
    wv.classList.toggle('cal-wv-mode-week', v === 'week');
    wv.classList.toggle('cal-wv-mode-day',  v === 'day');
  }
  // v2.6.1 : changement de contexte -> recentrage legitime.
  _requestCalAutoScroll();
  renderCalFromCacheThenRefresh();
}
function calPrev(){
  if(CAL_STATE.view === 'month'){
    CAL_STATE.month -= 1;
    if(CAL_STATE.month < 0){ CAL_STATE.month = 11; CAL_STATE.year -= 1; }
  } else if(CAL_STATE.view === 'week'){
    const ws = CAL_STATE.weekStart;
    CAL_STATE.weekStart = new Date(ws.getFullYear(), ws.getMonth(), ws.getDate() - 7);
  } else if(CAL_STATE.view === 'day'){
    const d = CAL_STATE.dayDate;
    CAL_STATE.dayDate = new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1);
  }
  // v2.6.1 : changement de contexte -> recentrage legitime.
  _requestCalAutoScroll();
  renderCalFromCacheThenRefresh();
}
function calNext(){
  if(CAL_STATE.view === 'month'){
    CAL_STATE.month += 1;
    if(CAL_STATE.month > 11){ CAL_STATE.month = 0; CAL_STATE.year += 1; }
  } else if(CAL_STATE.view === 'week'){
    const ws = CAL_STATE.weekStart;
    CAL_STATE.weekStart = new Date(ws.getFullYear(), ws.getMonth(), ws.getDate() + 7);
  } else if(CAL_STATE.view === 'day'){
    const d = CAL_STATE.dayDate;
    CAL_STATE.dayDate = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1);
  }
  // v2.6.1 : changement de contexte -> recentrage legitime.
  _requestCalAutoScroll();
  renderCalFromCacheThenRefresh();
}
function calToday(){
  const now = new Date();
  if(CAL_STATE.view === 'month'){
    CAL_STATE.year = now.getFullYear();
    CAL_STATE.month = now.getMonth();
  } else if(CAL_STATE.view === 'week'){
    CAL_STATE.weekStart = _calWeekMondayOf(now);
  } else if(CAL_STATE.view === 'day'){
    CAL_STATE.dayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }
  // v2.6.1 : changement de contexte -> recentrage legitime.
  _requestCalAutoScroll();
  renderCalFromCacheThenRefresh();
}
function _calIsoYMD(d){
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}
function renderCal(){
  if(CAL_STATE.view === 'week') return renderCalWeek();
  if(CAL_STATE.view === 'day')  return renderCalDay();
  return renderCalMonth();
}
function renderCalMonth(){
  const lbl = document.getElementById('cal-month-label');
  if(lbl){
    lbl.textContent = CAL_MONTHS[CAL_STATE.month] + ' ' + CAL_STATE.year;
  }
  const wh = document.getElementById('cal-week-head');
  if(wh){
    wh.innerHTML = CAL_WDAYS_SHORT.map((d,i) => {
      const cls = 'cal-wday' + (i===5?' sat':'') + (i===6?' sun':'');
      return '<div class="' + cls + '" title="' + escAttr(CAL_WDAYS_FULL[i]) + '">' + escHtml(d) + '</div>';
    }).join('');
  }
  const grid = document.getElementById('cal-grid');
  if(!grid) return;
  const firstOfMonth = new Date(CAL_STATE.year, CAL_STATE.month, 1);
  const startOffset = (firstOfMonth.getDay() + 6) % 7;
  const gridStart = new Date(CAL_STATE.year, CAL_STATE.month, 1 - startOffset);
  const todayIso = _calIsoYMD(new Date());
  const cells = [];
  for(let i = 0; i < 42; i++){
    const d = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
    const isOff = (d.getMonth() !== CAL_STATE.month);
    const wd = (d.getDay() + 6) % 7;
    const isWeekend = (wd === 5 || wd === 6);
    const iso = _calIsoYMD(d);
    const isToday = (iso === todayIso);
    const classes = ['cal-cell','cal-cell-clickable'];
    if(isOff) classes.push('cal-off');
    if(isWeekend) classes.push('cal-weekend');
    if(isToday) classes.push('cal-today');
    // Récupérer les créneaux planifiés pour ce jour (triés par heure de début)
    const dayEvents = PLANNING_STATE.list
      .filter(ev => ev.date === iso)
      .slice()
      .sort((a,b) => (_hmToMins(a.start)||0) - (_hmToMins(b.start)||0));
    // Teinter discrètement la case si elle contient des opérations
    let cellStyle = '';
    if(dayEvents.length > 0){
      classes.push('cal-cell-has-events');
      // Bande latérale = couleur du premier événement (par machine)
      const firstPalette = _machinePalette(dayEvents[0].machine);
      cellStyle = ' style="--cal-cell-accent:' + firstPalette.bg + '"';
    }
    // Chips : couleur de la machine + heure + nom
    const MAX_CHIPS = 3;
    const shown = dayEvents.slice(0, MAX_CHIPS);
    const overflow = dayEvents.length - shown.length;
    let chips = '';
    shown.forEach(ev => {
      const palette = _machinePalette(ev.machine);
      const tip = (ev.machine || '') + ' · ' + ev.start + '–' + ev.end;
      chips += '<div class="cal-day-event" style="background:' + palette.bg + ';color:' + palette.fg + '" ' +
               'data-event-id="' + escAttr(ev.id) + '" ' +
               'onclick="onCalMonthEventClick(event,\'' + escAttr(ev.id) + '\')" ' +
               'title="' + escAttr(tip) + '">' +
               '<span class="cal-day-event-time">' + escHtml(ev.start) + '</span>' +
               '<span class="cal-day-event-machine">' + escHtml(ev.machine || '—') + '</span>' +
               '</div>';
    });
    if(overflow > 0){
      chips += '<div class="cal-day-event-more" onclick="onCalMonthCellClick(event)" title="Voir le jour en vue Semaine">+ ' + overflow + ' autre' + (overflow > 1 ? 's' : '') + '</div>';
    }
    cells.push(
      '<div class="' + classes.join(' ') + '" data-date="' + iso + '"' + cellStyle + ' onclick="onCalMonthCellClick(event)">' +
        '<div class="cal-day-num">' + d.getDate() + '</div>' +
        '<div class="cal-day-events">' + chips + '</div>' +
      '</div>'
    );
  }
  grid.innerHTML = cells.join('');
}
function onCalMonthCellClick(e){
  // Si le clic vient d'une chip-événement, son propre handler gère
  if(e.target.closest('.cal-day-event')) return;
  const cell = e.currentTarget && e.currentTarget.closest ? e.currentTarget.closest('.cal-cell') : null;
  const iso = (cell && cell.getAttribute('data-date')) || (e.currentTarget && e.currentTarget.getAttribute && e.currentTarget.getAttribute('data-date'));
  if(!iso) return;
  // v2.2.54 : bascule sur la vue Jour du jour cliqué (au lieu d'ouvrir la création)
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(m){
    CAL_STATE.dayDate = new Date(parseInt(m[1],10), parseInt(m[2],10) - 1, parseInt(m[3],10));
    if(typeof setCalView === 'function') setCalView('day');
  }
}
function onCalMonthEventClick(e, id){
  if(e && e.stopPropagation) e.stopPropagation();
  const ev = PLANNING_STATE.list.find(x => x.id === id);
  if(!ev) return;
  openPlanningDetailsModal([ev]);
}
function renderCalWeek(){
  const ws = CAL_STATE.weekStart;
  const we = new Date(ws.getFullYear(), ws.getMonth(), ws.getDate() + 6);
  // Libellé
  const lbl = document.getElementById('cal-month-label');
  if(lbl){
    const fmtD = d => String(d.getDate()).padStart(2,'0') + ' ' + CAL_MONTHS[d.getMonth()].toLowerCase();
    let s;
    if(ws.getFullYear() === we.getFullYear()){
      s = 'Semaine du ' + fmtD(ws) + ' au ' + fmtD(we) + ' ' + we.getFullYear();
    } else {
      s = 'Semaine du ' + fmtD(ws) + ' ' + ws.getFullYear() + ' au ' + fmtD(we) + ' ' + we.getFullYear();
    }
    lbl.textContent = s;
  }
  // En-tête : corner + 7 jours
  const head = document.getElementById('cal-wv-header');
  if(head){
    const todayIso = _calIsoYMD(new Date());
    const cells = ['<div class="cal-wv-corner"></div>'];
    for(let i=0;i<7;i++){
      const d = new Date(ws.getFullYear(), ws.getMonth(), ws.getDate()+i);
      const iso = _calIsoYMD(d);
      const isWeekend = (i >= 5);
      const isToday = (iso === todayIso);
      const cls = 'cal-wv-dayhead' + (isWeekend?' weekend':'') + (isToday?' today':'');
      cells.push('<div class="' + cls + '" data-date="' + iso + '">' +
        '<div class="cal-wv-dayname">' + escHtml(CAL_WDAYS_SHORT[i]) + '</div>' +
        '<div class="cal-wv-daydate">' + String(d.getDate()).padStart(2,'0') + '/' + String(d.getMonth()+1).padStart(2,'0') + '</div>' +
      '</div>');
    }
    head.innerHTML = cells.join('');
  }
  // Corps : colonne heures + 7 colonnes jours
  const body = document.getElementById('cal-wv-body');
  if(!body) return;
  const todayIso = _calIsoYMD(new Date());
  let html = '<div class="cal-wv-times-col">';
  for(let h=CAL_HOUR_START; h<CAL_HOUR_END; h++){
    html += '<div class="cal-wv-time">' + String(h).padStart(2,'0') + ':00</div>';
  }
  html += '</div>';
  for(let i=0;i<7;i++){
    const d = new Date(ws.getFullYear(), ws.getMonth(), ws.getDate()+i);
    const iso = _calIsoYMD(d);
    const isWeekend = (i >= 5);
    const isToday = (iso === todayIso);
    const colCls = 'cal-wv-day-col' + (isWeekend?' weekend':'') + (isToday?' today':'');
    html += '<div class="' + colCls + (_calIsPastIso(iso) ? ' is-past-col' : '') + '" data-date="' + iso + '" onclick="onCalCellClick(event)">';
    for(let h=CAL_HOUR_START; h<CAL_HOUR_END; h++){
      html += '<div class="cal-wv-hour-row" data-hour="' + h + '"></div>';
    }
    html += '</div>';
  }
  try{ _saveCalScroll(); }catch(_){}
  body.innerHTML = html;
  // Lane-packing : un bloc par opération, placé côte à côte lorsqu'il y a chevauchement
  document.querySelectorAll('.cal-wv-day-col').forEach(col => {
    const iso = col.getAttribute('data-date');
    const events = PLANNING_STATE.list.filter(ev => ev.date === iso  && !_isEventBeingDragged(ev));
    const packed = _packDayEvents(events);
    packed.forEach(item => {
      const block = _makeEventBlock(item);
      if(block) col.appendChild(block);
    });
  });
  // v2.7.3 : bande unique hors zone de scroll, alimentee par les 7 jours.
  try{
    const _isos = [];
    for(let k=0;k<7;k++){
      _isos.push(_calIsoYMD(new Date(ws.getFullYear(), ws.getMonth(), ws.getDate()+k)));
    }
    _renderNonPlanifBand(_isos, 'week');
  }catch(_){}
  // v2.6.0 : le corps vient d'etre reconstruit -> re-aligner le header sur la
  // gouttiere de scrollbar, et repeindre l'etat de chargement (le skeleton a
  // ete efface par le innerHTML ci-dessus).
  try{ _syncCalHeaderGutter(); _scheduleCalHeaderGutterSync(); }catch(_){}
  try{ _renderPlanningLoadState(); }catch(_){}
}
function renderCalDay(){
  const d = CAL_STATE.dayDate || new Date();
  // Libellé
  const lbl = document.getElementById('cal-month-label');
  if(lbl){
    const s = d.toLocaleDateString('fr-FR', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
    lbl.textContent = s.charAt(0).toUpperCase() + s.slice(1);
  }
  const wdIdx = (d.getDay() + 6) % 7;
  const isWeekend = (wdIdx >= 5);
  const iso = _calIsoYMD(d);
  const todayIso = _calIsoYMD(new Date());
  const isToday = (iso === todayIso);
  // En-tête : corner + 1 jour
  const head = document.getElementById('cal-wv-header');
  if(head){
    const cls = 'cal-wv-dayhead' + (isWeekend?' weekend':'') + (isToday?' today':'');
    head.innerHTML = '<div class="cal-wv-corner"></div>' +
      '<div class="' + cls + '" data-date="' + iso + '">' +
        '<div class="cal-wv-dayname">' + escHtml(CAL_WDAYS_FULL[wdIdx]) + '</div>' +
        '<div class="cal-wv-daydate">' + String(d.getDate()).padStart(2,'0') + '/' + String(d.getMonth()+1).padStart(2,'0') + '/' + d.getFullYear() + '</div>' +
      '</div>';
  }
  // Corps : colonne heures + 1 colonne jour
  const body = document.getElementById('cal-wv-body');
  if(!body) return;
  let html = '<div class="cal-wv-times-col">';
  for(let h=CAL_HOUR_START; h<CAL_HOUR_END; h++){
    html += '<div class="cal-wv-time">' + String(h).padStart(2,'0') + ':00</div>';
  }
  html += '</div>';
  const colCls = 'cal-wv-day-col' + (isWeekend?' weekend':'') + (isToday?' today':'');
  html += '<div class="' + colCls + (_calIsPastIso(iso) ? ' is-past-col' : '') + '" data-date="' + iso + '" onclick="onCalCellClick(event)">';
  for(let h=CAL_HOUR_START; h<CAL_HOUR_END; h++){
    html += '<div class="cal-wv-hour-row" data-hour="' + h + '"></div>';
  }
  html += '</div>';
  try{ _saveCalScroll(); }catch(_){}
  body.innerHTML = html;
  // Lane-packing
  document.querySelectorAll('.cal-wv-day-col').forEach(col => {
    const cIso = col.getAttribute('data-date');
    const events = PLANNING_STATE.list.filter(ev => ev.date === cIso && !_isEventBeingDragged(ev));
    const packed = _packDayEvents(events);
    packed.forEach(item => {
      const block = _makeEventBlock(item);
      if(block) col.appendChild(block);
    });
  });
  // v2.7.3 : meme bande qu'en vue Semaine, avec le rendu enrichi mono-colonne.
  try{ _renderNonPlanifBand([iso], 'day'); }catch(_){}
  try{ _syncCalHeaderGutter(); _scheduleCalHeaderGutterSync(); }catch(_){}
  try{ _renderPlanningLoadState(); }catch(_){}
}

// v2.7.3 : rendu des operations saisies hors creneau (source 'non_planifie').
//
// Avant : un bandeau absolu au sommet de CHAQUE colonne de jour, donc a
// l'interieur du conteneur de scroll. Avec la plage 0h-24h, ce sommet est a
// 00:00 : il fallait remonter d'environ 1490px pour voir ces operations.
// Maintenant : une bande unique entre les en-tetes de jours et la grille
// horaire, hors zone de defilement, donc toujours a l'ecran.
//
// L'etat de pliage est un module-level : il survit aux re-rendus (navigation,
// creation d'un creneau, refresh), sinon chaque repaint le remettrait a zero.
let _CAL_NONPL_OPEN = true;

function _nonPlanifOpsOf(iso){
  const evs = (PLANNING_STATE.list || []).filter(ev =>
    ev.date === iso && ev.source === 'non_planifie'
  );
  let n = 0;
  evs.forEach(ev => { n += (ev.operations || []).length; });
  return { iso: iso, evs: evs, n: n };
}

function _makeNonPlanifChip(ev, op, isDay){
  const chip = document.createElement('div');
  chip.className = 'cal-wv-nonpl-chip';
  chip.setAttribute('data-statut', op.statut || 'a_faire');
  chip.setAttribute('data-event-id', ev.id);
  const machine = (op.machines && op.machines[0]) || ev.machine || '';
  const _fmtHM = (iso2) => {
    if(!iso2) return '';
    const m = String(iso2).match(/T(\d{2}):(\d{2})/);
    return m ? (m[1] + ':' + m[2]) : '';
  };
  const timeStr = (op.statut === 'termine') ? _fmtHM(op.done_at) : '';
  chip.title = (op.opName || '') + (machine ? ' — ' + machine : '') +
               '\n(Non planifiée · cliquer pour voir le détail)';
  if(isDay){
    const statusIcon = (op.statut === 'termine')
      ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
      : '';
    chip.innerHTML =
      '<span class="cal-wv-nonpl-chip-status">' + statusIcon + '</span>' +
      '<div class="cal-wv-nonpl-chip-main">' +
        escHtml(op.opName || '—') +
        (machine ? '<div class="cal-wv-nonpl-chip-sub">' + escHtml(machine) + '</div>' : '') +
      '</div>' +
      (timeStr ? '<span class="cal-wv-nonpl-chip-time">' + escHtml(timeStr) + '</span>' : '');
  } else {
    chip.innerHTML = '<span class="cal-wv-nonpl-icon"></span>' + escHtml(op.opName || '—') +
                     (machine ? ' · ' + escHtml(machine) : '');
  }
  chip.addEventListener('click', e => {
    e.stopPropagation();
    openPlanningDetailsModal([ev]);
  });
  return chip;
}

function _setNonPlanifOpen(band, open){
  _CAL_NONPL_OPEN = !!open;
  band.classList.toggle('is-open', _CAL_NONPL_OPEN);
  // Plier/deplier change la hauteur de la bande, donc la hauteur restante pour
  // la grille : _fitCalWeekBody() mesure le haut du corps, il faut la relancer.
  try{ _scheduleCalHeaderGutterSync(); }catch(_){}
}

function _renderNonPlanifBand(isos, mode){
  const band = document.getElementById('cal-wv-allday');
  if(!band) return;
  band.innerHTML = '';
  const isDay = (mode === 'day');
  const days = (isos || []).map(_nonPlanifOpsOf);
  const total = days.reduce((a, d) => a + d.n, 0);
  // Aucune operation hors creneau sur la periode : la bande disparait plutot
  // que de laisser une ligne vide manger la hauteur de la grille.
  if(!total){ band.hidden = true; return; }
  band.hidden = false;
  band.classList.toggle('is-open', !!_CAL_NONPL_OPEN);

  const todayIso = _calIsoYMD(new Date());
  const corner = document.createElement('button');
  corner.type = 'button';
  corner.className = 'cal-wv-allday-corner';
  corner.title = 'Opérations saisies hors créneau — cliquer pour plier ou déplier';
  corner.innerHTML =
    '<span class="cal-wv-allday-corner-top">' +
      '<svg class="cal-wv-allday-chev" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>' +
      '<span>Non planifi\u00e9</span>' +
    '</span>' +
    '<span class="cal-wv-allday-total">' + total + ' op.</span>';
  corner.addEventListener('click', e => {
    e.stopPropagation();
    _setNonPlanifOpen(band, !_CAL_NONPL_OPEN);
  });
  band.appendChild(corner);

  days.forEach(d => {
    const dt = new Date(d.iso + 'T00:00:00');
    const wd = (dt.getDay() + 6) % 7;
    const cell = document.createElement('div');
    cell.className = 'cal-wv-allday-cell' + (wd >= 5 ? ' weekend' : '') +
                     (d.iso === todayIso ? ' today' : '');
    cell.setAttribute('data-date', d.iso);
    if(d.n){
      // Visible uniquement quand la bande est repliee (bascule CSS) : donne le
      // volume par jour sans deplier, et deplie au clic.
      const pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'cal-wv-allday-pill';
      pill.textContent = String(d.n);
      pill.title = d.n + ' op\u00e9ration' + (d.n > 1 ? 's' : '') +
                   ' non planifi\u00e9e' + (d.n > 1 ? 's' : '') + ' — cliquer pour d\u00e9plier';
      pill.addEventListener('click', e => { e.stopPropagation(); _setNonPlanifOpen(band, true); });
      cell.appendChild(pill);
      d.evs.forEach(ev => {
        (ev.operations || []).forEach(op => cell.appendChild(_makeNonPlanifChip(ev, op, isDay)));
      });
    }
    band.appendChild(cell);
  });
  try{ _syncCalHeaderGutter(); }catch(_){}
}

// ── Lane packing (Google-Calendar style) ──────────────────────────────
function _packDayEvents(events){
  const sorted = events.slice()
    .map(ev => ({ ev, s: _hmToMins(ev.start), e: _hmToMins(ev.end) }))
    .filter(o => o.s != null && o.e != null && o.e > o.s)
    .sort((a,b) => (a.s - b.s) || (b.e - a.e));
  if(!sorted.length) return [];
  // 1. Groupes transitivement chevauchants
  const groups = [];
  let cur = null;
  sorted.forEach(o => {
    if(!cur || o.s >= cur.maxEnd){
      cur = { maxEnd: o.e, items: [o] };
      groups.push(cur);
    } else {
      cur.maxEnd = Math.max(cur.maxEnd, o.e);
      cur.items.push(o);
    }
  });
  // 2. Dans chaque groupe, packer en lanes (greedy)
  groups.forEach(g => {
    const lanes = [];
    g.items.forEach(o => {
      let placed = false;
      for(let i = 0; i < lanes.length; i++){
        const last = lanes[i][lanes[i].length - 1];
        if(o.s >= last.e){
          lanes[i].push(o);
          o.lane = i;
          placed = true;
          break;
        }
      }
      if(!placed){
        lanes.push([o]);
        o.lane = lanes.length - 1;
      }
    });
    g.lanesCount = lanes.length;
    g.items.forEach(o => { o.lanesCount = lanes.length; });
  });
  return sorted;
}
// Palette par machine (couleur unie par équipement)
const CAL_MACHINE_PALETTE = {
  'Cohésio 1': { bg:'#0891b2', fg:'#ffffff' },
  'Cohésio 2': { bg:'#7c3aed', fg:'#ffffff' },
  'DSI':       { bg:'#ea580c', fg:'#ffffff' },
  'Repiquage': { bg:'#059669', fg:'#ffffff' },
};
function _machinePalette(machine){
  return CAL_MACHINE_PALETTE[machine] || { bg:'#475569', fg:'#ffffff' };
}
// v2.6.0 : le badge « aucun operateur » etait cree AVANT `div.innerHTML = ...`,
// qui detruit tous les enfants -- il n'a donc jamais ete visible depuis la
// v2.5.26 (idem sur la variante cluster). Ce helper doit imperativement etre
// appele APRES l'affectation de innerHTML.
function _appendNoOperatorBadge(div, ev){
  if(!div || !ev) return;
  if(MAINT_ROLE === 'operator') return;
  if(ev.operators && ev.operators.length) return;
  div.classList.add('has-no-op');
  const noop = document.createElement('div');
  noop.className = 'cal-event-noop';
  // Triangle plein rouge + « ! » blanc : bien plus lisible a 26 px qu'un
  // contour fin. Couleurs portees par le SVG, pas par le CSS de theme.
  noop.innerHTML = '<svg viewBox="0 0 24 24">' +
    '<path d="M10.29 3.86l-8.18 14.16A2 2 0 0 0 3.83 21h16.34a2 2 0 0 0 1.72-2.98L13.71 3.86a2 2 0 0 0-3.42 0z" ' +
      'fill="#dc2626" stroke="#dc2626" stroke-width="2.2" stroke-linejoin="round"/>' +
    '<line x1="12" y1="9.5" x2="12" y2="14" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round"/>' +
    '<line x1="12" y1="17.4" x2="12.01" y2="17.4" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round"/></svg>';
  noop.title = 'Aucun op\u00e9rateur assign\u00e9 \u2014 ce cr\u00e9neau ne peut pas \u00eatre r\u00e9alis\u00e9. Cliquer pour \u00e9diter.';
  noop.setAttribute('aria-label', 'Aucun op\u00e9rateur assign\u00e9');
  noop.addEventListener('click', function(e){
    e.stopPropagation();
    if(_CAL_DRAG && _CAL_DRAG._justFinished){ _CAL_DRAG._justFinished = false; return; }
    try{ editCase(ev.id); }catch(_){ openPlanningDetailsModal([ev]); }
  });
  div.appendChild(noop);
}

function _makeEventBlock(item){
  const ev = item.ev;
  const startMin = item.s, endMin = item.e;
  if(startMin == null || endMin == null || endMin <= startMin) return null;
  // v2.2.55 : la vue Jour a des rows plus hautes (72px vs 62px pour la semaine).
  // Sync avec le CSS pour éviter le décalage vertical cumulatif.
  const px = (CAL_STATE && CAL_STATE.view === 'day') ? 72 : CAL_HOUR_PX;
  const top = ((startMin - CAL_HOUR_START*60) / 60) * px;
  const height = Math.max(22, ((endMin - startMin) / 60) * px - 2);
  const lanesCount = item.lanesCount || 1;
  const lane = item.lane || 0;
  const div = document.createElement('div');
  // v2.7.2 : la pastille recurrence suivait template_id seul, donc elle
  // s'affichait aussi sur les creneaux composes a la main ayant simplement
  // importe un modele. Seul template_origin_date atteste d'une occurrence
  // reellement generee par une recurrence.
  div.className = 'cal-event' + (_calIsRecurOccurrence(ev) ? ' is-from-template' : '')
                              + (_calIsPastEvent(ev) ? ' is-closed' : '');  // v2.7.0
  div.style.top = top + 'px';
  div.style.height = height + 'px';
  div.style.left = 'calc(' + (lane * (100 / lanesCount)) + '% + 3px)';
  div.style.width = 'calc(' + (100 / lanesCount) + '% - 6px)';
  // Couleur unie par machine
  const palette = _machinePalette(ev.machine);
  div.style.background = palette.bg;
  div.style.color = palette.fg;
  if(height < 50) div.setAttribute('data-mini', '1');
  div.setAttribute('data-event-id', ev.id);
  // Marque les créneaux où l'opérateur courant est dans le groupe
  if(MAINT_ROLE === 'operator' && S && S.me){
    const mine = (ev.operators || []).some(o => o.id === S.me.id);
    if(mine) div.classList.add('is-mine');
  }
  // v2.7.0 : une operation invalidee est mise de cote — elle ne compte plus
  // dans le creneau. Le compteur de la tuile suit donc l'historique : invalider
  // une saisie depuis l'historique fait bien decroitre le nombre affiche ici
  // (refreshPlanning + renderCal sont deja rappeles par l'action).
  const ops = Array.isArray(ev.operations)
    ? ev.operations.filter(o => o && (o.opName || o.opTypeId) && o.statut !== 'invalidee')
    : [];
  const opsCount = ops.length;
  // v2.5.20 : rendu minimaliste -- juste le nom (ou le nom du modele lie, ou la
  // machine en fallback) + "Afficher les details". La liste des ops et l'horaire
  // sont visibles au clic dans la modale details -- pas de bruit visuel dans le
  // calendrier.
  // v2.5.22 : rendu adaptatif via container queries CSS.
  // On injecte TOUT dans le DOM (nom + machine + horaires + compteur ops),
  // et le CSS decide quoi afficher selon la taille reelle de la case.
  // Petit bloc : nom seul. Bloc large : tout.
  let title = (ev.nom || '').trim();
  let hasCustomName = !!title;
  if(!title && ev.template_id && typeof TEMPLATES_STATE !== 'undefined' && TEMPLATES_STATE && Array.isArray(TEMPLATES_STATE.list)){
    const tmpl = TEMPLATES_STATE.list.find(t => t.id === ev.template_id);
    if(tmpl && tmpl.name){ title = tmpl.name; hasCustomName = true; }
  }
  if(!title) title = ev.machine || '\u2014';
  let inner = '<div class="cal-event-title">' + escHtml(title) +
    (_calIsPastEvent(ev) ? '<span class="cal-event-closed-badge">Clôturé</span>' : '') +
    '</div>';
  // Machine en sous-titre (seulement si le titre principal n\'est pas deja la machine)
  if(hasCustomName && ev.machine){
    inner += '<div class="cal-event-sub">' + escHtml(ev.machine) + '</div>';
  }
  inner += '<div class="cal-event-time">' + escHtml(ev.start || '') + ' \u2013 ' + escHtml(ev.end || '') + '</div>';
  if(opsCount > 0){
    inner += '<div class="cal-event-count">' + opsCount + ' op\u00e9ration' + (opsCount > 1 ? 's' : '') + '</div>';
  }
  div.innerHTML = inner;
  // v2.5.26 / v2.6.0 : pictogramme « aucun operateur assigne ». APRES innerHTML.
  if(!_calIsPastEvent(ev)) _appendNoOperatorBadge(div, ev);  // v2.7.0
  div.title = (ev.machine || '') + '\n' + ev.start + ' – ' + ev.end +
    (ops.length ? '\n\n' + ops.map(o => '• ' + (o.opName||'—')).join('\n') : '') +
    '\n\nCliquer pour afficher les détails';
  div.addEventListener('click', e => {
    e.stopPropagation();
    // v2.5.14 : si un drag vient de se terminer, on avale le click de fin.
    if(_CAL_DRAG && _CAL_DRAG._justFinished){ _CAL_DRAG._justFinished = false; return; }
    openPlanningDetailsModal([ev]);
  });
  // v2.5.14 : attache le drag & drop (move + resize) sauf sur créneaux passés / opérateur.
  if(MAINT_ROLE === 'admin'){
    _attachCalEventDragHandlers(div, ev);
  }
  return div;
}

// v2.5.14 : drag & drop planning maintenance.
// - Move : drag corps -> nouvelle date + heure (durée conservée)
// - Resize : drag bordure haut/bas -> nouveau start/end (même date)
// - Snap 15 min
// - Cross-week : hover ~600 ms sur boutons ◀ / ▶ -> change de semaine
// - Guard 'past event' : créneau avec date < today = non draggable
// - Persist via PATCH, rollback visuel + toast si échec
const _CAL_SNAP_MIN = 15;
let _CAL_DRAG = null;

// v2.6.1 : une date ISO est-elle anterieure a aujourd'hui ? Aujourd'hui reste
// une date valide (on peut planifier pour le jour meme).
// v2.7.1 : miroir client de _period_key() (maintenance_events.py). Une
// occurrence de recurrence appartient a une periode — semaine ISO, mois,
// trimestre ou annee — et ne doit pas en sortir. Le serveur refuse en 403 ;
// ici on rend le refus visible AVANT le lacher, plutot qu'apres coup.
function _isoWeekKey(d){
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  // Jeudi de la semaine ISO : determine l'annee ISO (norme ISO-8601).
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  const y0 = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const w = Math.ceil(((t - y0) / 86400000 + 1) / 7);
  return t.getUTCFullYear() + '-W' + String(w).padStart(2, '0');
}
function _calPeriodKey(iso, rtype){
  const d = (typeof iso === 'string') ? new Date(iso + 'T00:00:00') : iso;
  if(!d || isNaN(d.getTime())) return null;
  if(rtype === 'monthly')   return d.getFullYear() + '-M' + String(d.getMonth() + 1).padStart(2, '0');
  if(rtype === 'quarterly') return d.getFullYear() + '-Q' + (Math.floor(d.getMonth() / 3) + 1);
  if(rtype === 'yearly')    return String(d.getFullYear());
  return _isoWeekKey(d);
}
// Type de recurrence du modele dont l'evenement est issu, ou null si ce n'est
// pas une occurrence generee (creneau compose a la main : aucune contrainte).
// v2.7.2 : un creneau n'est une occurrence de recurrence que s'il porte a la
// fois template_id ET template_origin_date. template_id seul signifie
// « un modele a ete importe dans la liste d'operations » : simple raccourci
// de saisie, sans lien de vie avec le modele.
function _calIsRecurOccurrence(ev){
  return !!(ev && ev.template_id && ev.template_origin_date);
}
function _calRecurTypeOf(ev){
  if(!ev || !ev.template_origin_date || !ev.template_id) return null;
  try{
    const t = (TEMPLATES_STATE.list || []).find(x => String(x.id) === String(ev.template_id));
    return (t && t.recurrence_type) || 'weekly';
  }catch(_){ return 'weekly'; }
}

function _calIsPastIso(iso){
  try{
    const s = String(iso || '');
    // Valeur absente : on ne conclut PAS au passe. La comparaison de chaines
    // ferait sinon '' < '2026-08-03' => true, et une colonne sans data-date
    // serait grisee et refuserait tout depot.
    if(!s) return false;
    return s < _calIsoYMD(new Date());
  }catch(_){ return false; }
}

function _calIsPastEvent(ev){
  try{
    const todayIso = _calIsoYMD(new Date());
    return String(ev.date || '') < todayIso;
  }catch(_){ return false; }
}

function _minsToHM(min){
  min = Math.max(0, Math.min(24*60 - 1, min|0));
  const h = Math.floor(min/60), m = min % 60;
  return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');
}

function _snap15(min){ return Math.round(min / _CAL_SNAP_MIN) * _CAL_SNAP_MIN; }

function _attachCalEventDragHandlers(div, ev){
  // Créneau passé = read-only pour les heures / date.
  if(_calIsPastEvent(ev)){
    div.classList.add('is-past');
    div.setAttribute('title', (div.getAttribute('title') || '') + '\n(Créneau passé — date/heures non modifiables)');
    return;
  }
  div.setAttribute('data-draggable', '1');
  // Handles de resize (top + bottom).
  const topH = document.createElement('div');
  topH.className = 'cal-event-resize-handle top';
  topH.setAttribute('data-drag-role', 'resize-top');
  const botH = document.createElement('div');
  botH.className = 'cal-event-resize-handle bottom';
  botH.setAttribute('data-drag-role', 'resize-bottom');
  div.appendChild(topH);
  div.appendChild(botH);
  // Mousedown attaché sur l'event -- détermine le mode selon la cible.
  div.addEventListener('mousedown', function(e){
    if(e.button !== 0) return;  // clic gauche uniquement
    // Refuse si l'event a bouge apres refetch (page state changed).
    const role = e.target && e.target.getAttribute && e.target.getAttribute('data-drag-role');
    const mode = (role === 'resize-top' || role === 'resize-bottom') ? role : 'move';
    _startCalDrag(e, div, ev, mode);
  });
}

function _startCalDrag(e, div, ev, mode){
  // Init l'état -- le drag ne démarre vraiment qu'après un mouvement > seuil.
  const origStart = _hmToMins(ev.start);
  const origEnd   = _hmToMins(ev.end);
  if(origStart == null || origEnd == null) return;
  _CAL_DRAG = {
    mode: mode,
    div: div,
    ev: ev,
    startX: e.clientX,
    startY: e.clientY,
    origDate: ev.date,
    origStartMin: origStart,
    origEndMin: origEnd,
    duration: origEnd - origStart,
    active: false,
    ghost: null,
    targetDate: ev.date,
    targetStartMin: origStart,
    targetEndMin: origEnd,
    _navHoverTimer: null,
    _navHoverDir: null,
    _justFinished: false,
  };
  document.addEventListener('mousemove', _onCalDragMove, true);
  document.addEventListener('mouseup', _onCalDragUp, true);
  e.preventDefault();
}

function _onCalDragMove(e){
  if(!_CAL_DRAG) return;
  const dx = e.clientX - _CAL_DRAG.startX;
  const dy = e.clientY - _CAL_DRAG.startY;
  // Seuil de démarrage du drag : au-delà de 4 px, on considère que c'est un vrai drag.
  if(!_CAL_DRAG.active){
    if(Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
    _CAL_DRAG.active = true;
    _CAL_DRAG.div.classList.add('is-dragging');
    const g = document.createElement('div');
    g.className = 'cal-drag-ghost';
    document.body.appendChild(g);
    _CAL_DRAG.ghost = g;
  }
  // Résout la colonne survolée (jour cible).
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const col = el ? el.closest('.cal-wv-day-col') : null;
  const rect = col ? col.getBoundingClientRect() : null;
  const px = (CAL_STATE && CAL_STATE.view === 'day') ? 72 : CAL_HOUR_PX;
  document.querySelectorAll('.cal-wv-day-col.drag-over, .cal-wv-day-col.cal-col-nodrop').forEach(function(c){ c.classList.remove('drag-over', 'cal-col-nodrop'); });
  _handleCrossWeekHover(el, e);
  // v2.6.1 : une colonne dont la date est passee n'accepte pas de depot. On ne
  // la marque pas 'drag-over' et on ne met pas a jour targetDate : le refus est
  // visible AVANT le lacher, plutot que par un message apres coup.
  if(col && _calIsPastIso(col.getAttribute('data-date'))){
    col.classList.add('cal-col-nodrop');
    col = null;
  }
  // v2.7.1 : hors de la periode d'une occurrence de recurrence -> depot refuse.
  if(col){
    const _rt = _calRecurTypeOf(_CAL_DRAG.ev);
    if(_rt){
      const _pFrom = _calPeriodKey(_CAL_DRAG.origDate, _rt);
      const _pTo   = _calPeriodKey(col.getAttribute('data-date'), _rt);
      if(_pFrom && _pTo && _pFrom !== _pTo){
        col.classList.add('cal-col-nodrop');
        col = null;
      }
    }
  }
  if(col && rect){
    col.classList.add('drag-over');
    const y = e.clientY - rect.top;
    const rawMin = CAL_HOUR_START * 60 + Math.max(0, y) * 60 / px;
    if(_CAL_DRAG.mode === 'move'){
      let ns = _snap15(rawMin);
      if(ns < CAL_HOUR_START*60) ns = CAL_HOUR_START*60;
      if(ns + _CAL_DRAG.duration > CAL_HOUR_END*60) ns = CAL_HOUR_END*60 - _CAL_DRAG.duration;
      _CAL_DRAG.targetStartMin = ns;
      _CAL_DRAG.targetEndMin = ns + _CAL_DRAG.duration;
      _CAL_DRAG.targetDate = col.getAttribute('data-date');
    } else if(_CAL_DRAG.mode === 'resize-top'){
      let ns = _snap15(rawMin);
      if(ns < CAL_HOUR_START*60) ns = CAL_HOUR_START*60;
      if(ns > _CAL_DRAG.origEndMin - 15) ns = _CAL_DRAG.origEndMin - 15;
      _CAL_DRAG.targetStartMin = ns;
      _CAL_DRAG.targetEndMin = _CAL_DRAG.origEndMin;
      _CAL_DRAG.targetDate = _CAL_DRAG.origDate;
    } else if(_CAL_DRAG.mode === 'resize-bottom'){
      let ne = _snap15(rawMin);
      if(ne < _CAL_DRAG.origStartMin + 15) ne = _CAL_DRAG.origStartMin + 15;
      if(ne > CAL_HOUR_END*60) ne = CAL_HOUR_END*60;
      _CAL_DRAG.targetStartMin = _CAL_DRAG.origStartMin;
      _CAL_DRAG.targetEndMin = ne;
      _CAL_DRAG.targetDate = _CAL_DRAG.origDate;
    }
  }
  // v2.5.16 : LIVE UPDATE du bloc lui-meme dans le DOM (comme Google Calendar).
  // - move : reparent vers la nouvelle colonne + repositionne top
  // - resize-top : deplace top + ajuste height
  // - resize-bottom : ajuste height uniquement
  const div = _CAL_DRAG.div;
  const startPx = ((_CAL_DRAG.targetStartMin - CAL_HOUR_START*60) / 60) * px;
  const heightPx = Math.max(22, ((_CAL_DRAG.targetEndMin - _CAL_DRAG.targetStartMin) / 60) * px - 2);
  if(_CAL_DRAG.mode === 'move' && col && col !== div.parentElement){
    // Reparenting : passe dans la nouvelle colonne, largeur pleine (lane packing sera recalcule au drop).
    col.appendChild(div);
    div.style.left = '3px';
    div.style.width = 'calc(100% - 6px)';
  }
  div.style.top = startPx + 'px';
  div.style.height = heightPx + 'px';
  // Ghost : simple label horaire qui suit le curseur (leger, non intrusif).
  if(_CAL_DRAG.ghost){
    _CAL_DRAG.ghost.style.left = (e.clientX + 14) + 'px';
    _CAL_DRAG.ghost.style.top  = (e.clientY + 14) + 'px';
    const dateFR = _fmtIsoDateFr(_CAL_DRAG.targetDate) || _CAL_DRAG.targetDate;
    _CAL_DRAG.ghost.innerHTML = '' +
      '<span>' + escHtml(dateFR) + '</span>' +
      '<span class="cal-drag-ghost-time">' +
        _minsToHM(_CAL_DRAG.targetStartMin) + ' – ' + _minsToHM(_CAL_DRAG.targetEndMin) +
      '</span>';
  }
}

// v2.6.1 : bascule de semaine par les BORDS de la grille, en plus du survol
// des fleches qui existait deja (et restait peu decouvrable — il fallait viser
// un petit bouton en haut a droite alors que le creneau peut etre en bas).
// Glisser au-dela du bord droit de dimanche = lundi suivant ; au-dela du bord
// gauche de lundi = dimanche precedent.
// v2.6.1 : pendant un glisser-deposer inter-semaines, le bloc en cours de
// deplacement est gere a la main (detache du DOM par le re-rendu, puis
// reinsere dans la colonne survolee). Il ne doit donc PAS etre redessine par
// renderCalWeek()/renderCalDay() depuis PLANNING_STATE : en revenant sur la
// semaine d'origine, le creneau apparaissait deux fois — celui qu'on deplace
// et sa copie a l'emplacement d'origine.
//
// Le filtre ne s'applique qu'a un drag ACTIF (seuil de mouvement franchi) :
// un simple clic ne doit pas faire disparaitre le creneau. Apres le drop,
// _CAL_DRAG est remis a null avant le re-rendu, le bloc revient normalement.
function _isEventBeingDragged(ev){
  try{
    return !!(_CAL_DRAG && _CAL_DRAG.active && _CAL_DRAG.ev && ev
              && String(_CAL_DRAG.ev.id) === String(ev.id));
  }catch(_){ return false; }
}

const CAL_EDGE_ZONE_PX  = 48;   // largeur des bandes sensibles
const CAL_EDGE_DELAY_MS = 450;  // survol requis avant de changer de semaine

function _calEdgeDirection(e){
  // Vue Jour exclue : la navigation y va de jour en jour, les bords n'ont pas
  // le sens « semaine precedente / suivante ».
  if(typeof CAL_STATE === 'undefined' || !CAL_STATE || CAL_STATE.view !== 'week') return null;
  const body = document.getElementById('cal-wv-body');
  if(!body) return null;
  const r = body.getBoundingClientRect();
  // Hors de la bande verticale de la grille : le geste vise autre chose.
  if(e.clientY < r.top || e.clientY > r.bottom) return null;
  if(e.clientX <= r.left  + CAL_EDGE_ZONE_PX) return 'prev';
  if(e.clientX >= r.right - CAL_EDGE_ZONE_PX) return 'next';
  return null;
}

// v2.7.1 : la bascule de periode (bandes de bord + fleches) doit-elle rester
// active pendant ce drag ? Non si la periode visee ne contient AUCUNE date
// atteignable pour l'occurrence en cours.
//
// La nuance compte : une occurrence HEBDOMADAIRE ne peut jamais sortir de sa
// semaine, donc toute navigation est inutile. Une occurrence MENSUELLE, elle,
// peut parfaitement traverser des semaines a l'interieur de son mois — on ne
// bloque alors que les semaines entierement hors du mois.
function _calWeekNavAllowed(dir){
  if(!_CAL_DRAG) return true;
  const rt = _calRecurTypeOf(_CAL_DRAG.ev);
  if(!rt) return true;                       // creneau libre : navigation libre
  const p = _calPeriodKey(_CAL_DRAG.origDate, rt);
  if(!p) return true;
  const step = (dir === 'prev') ? -1 : 1;
  let base;
  try{
    if(CAL_STATE.view === 'day'){
      const d = CAL_STATE.dayDate;
      base = new Date(d.getFullYear(), d.getMonth(), d.getDate() + step);
      return _calPeriodKey(base, rt) === p;
    }
    const ws = CAL_STATE.weekStart;
    base = new Date(ws.getFullYear(), ws.getMonth(), ws.getDate() + 7 * step);
  }catch(_){ return true; }
  // Au moins un jour de la semaine visee appartient-il a la meme periode ?
  for(let i = 0; i < 7; i++){
    const d = new Date(base.getFullYear(), base.getMonth(), base.getDate() + i);
    if(_calPeriodKey(d, rt) === p) return true;
  }
  return false;
}

function _clearCalEdgeCue(){
  const body = document.getElementById('cal-wv-body');
  if(body) body.classList.remove('cal-edge-prev', 'cal-edge-next',
                                 'cal-edge-blocked-prev', 'cal-edge-blocked-next');
  document.querySelectorAll('.cal-nav button.cal-drop-target-nav').forEach(function(b){
    b.classList.remove('cal-drop-target-nav');
  });
}

function _handleCrossWeekHover(el, e){
  if(!_CAL_DRAG) return;
  const btnPrev = el ? el.closest('button[onclick="calPrev()"]') : null;
  const btnNext = el ? el.closest('button[onclick="calNext()"]') : null;
  const btn = btnPrev || btnNext;
  let dir = btnPrev ? 'prev' : (btnNext ? 'next' : _calEdgeDirection(e));
  // v2.7.1 : navigation refusee -> on signale le blocage au lieu de laisser
  // croire que le depot sera possible de l'autre cote.
  if(dir && !_calWeekNavAllowed(dir)){
    const _b = document.getElementById('cal-wv-body');
    if(_b) _b.classList.add(dir === 'prev' ? 'cal-edge-blocked-prev' : 'cal-edge-blocked-next');
    dir = null;
  } else {
    const _b = document.getElementById('cal-wv-body');
    if(_b) _b.classList.remove('cal-edge-blocked-prev', 'cal-edge-blocked-next');
  }
  // Direction inchangee : le timer en cours court toujours, on ne le relance
  // pas. C'est aussi ce qui empeche d'enchainer les semaines sans relacher —
  // apres une bascule, _navHoverDir reste arme tant qu'on n'a pas quitte la
  // bande, il faut en sortir puis y revenir pour avancer d'une semaine de plus.
  if(dir === _CAL_DRAG._navHoverDir) return;
  if(_CAL_DRAG._navHoverTimer){
    clearTimeout(_CAL_DRAG._navHoverTimer);
    _CAL_DRAG._navHoverTimer = null;
  }
  _clearCalEdgeCue();
  _CAL_DRAG._navHoverDir = dir;
  if(!dir) return;
  if(btn) btn.classList.add('cal-drop-target-nav');
  else {
    const body = document.getElementById('cal-wv-body');
    if(body) body.classList.add(dir === 'prev' ? 'cal-edge-prev' : 'cal-edge-next');
  }
  _CAL_DRAG._navHoverTimer = setTimeout(function(){
    try{
      if(dir === 'prev' && typeof calPrev === 'function') calPrev();
      else if(dir === 'next' && typeof calNext === 'function') calNext();
    }catch(_){}
    _clearCalEdgeCue();
    if(_CAL_DRAG) _CAL_DRAG._navHoverTimer = null;
    // _navHoverDir volontairement CONSERVE : cf. commentaire ci-dessus.
  }, CAL_EDGE_DELAY_MS);
}

function _onCalDragUp(e){
  if(!_CAL_DRAG) return;
  const drag = _CAL_DRAG;
  // Nettoie handlers globaux.
  document.removeEventListener('mousemove', _onCalDragMove, true);
  document.removeEventListener('mouseup', _onCalDragUp, true);
  if(drag._navHoverTimer) clearTimeout(drag._navHoverTimer);
  _clearCalEdgeCue();
  document.querySelectorAll('.cal-wv-day-col.drag-over, .cal-wv-day-col.cal-col-nodrop').forEach(function(c){ c.classList.remove('drag-over', 'cal-col-nodrop'); });
  if(drag.ghost){ drag.ghost.remove(); drag.ghost = null; }
  drag.div.classList.remove('is-dragging');
  if(!drag.active){
    // Pas un drag, laisse le click passer normalement.
    _CAL_DRAG = null;
    return;
  }
  // Le drag était actif : bloque le prochain click, peu importe la cible
  // (peut arriver sur .cal-wv-day-col apres un resize, qui ouvrirait
  // sinon la modale 'Nouveau creneau' via onCalCellClick).
  drag._justFinished = true;
  const _swallowClick = function(ev){
    ev.stopPropagation();
    ev.preventDefault();
    document.removeEventListener('click', _swallowClick, true);
  };
  document.addEventListener('click', _swallowClick, true);
  // Filet de securite : si aucun click n'est emis (mouseup 'sec'), on retire le
  // listener au tick suivant pour ne pas avaler un click futur sans rapport.
  setTimeout(function(){ document.removeEventListener('click', _swallowClick, true); }, 0);
  // Rien changé ? Rien à faire.
  if(drag.targetDate === drag.origDate
     && drag.targetStartMin === drag.origStartMin
     && drag.targetEndMin === drag.origEndMin){
    _CAL_DRAG = null;
    return;
  }
  // v2.7.1 : hors periode -> message explicite. Le survol a deja refuse la
  // colonne, donc targetDate ne devrait plus sortir de la periode ; ce garde-fou
  // couvre les chemins ou le lacher se fait sans survol valide prealable.
  const _rtDrop = _calRecurTypeOf(drag.ev);
  if(_rtDrop){
    const _a = _calPeriodKey(drag.origDate, _rtDrop);
    const _b = _calPeriodKey(drag.targetDate, _rtDrop);
    if(_a && _b && _a !== _b){
      const _quoi = (_rtDrop === 'monthly') ? 'son mois'
                  : (_rtDrop === 'quarterly') ? 'son trimestre'
                  : (_rtDrop === 'yearly') ? 'son année' : 'sa semaine';
      if(typeof showToast === 'function'){
        showToast('Ce créneau vient d\'une récurrence : il doit rester dans ' + _quoi + '.', 'danger');
      }
      _CAL_DRAG = null;
      try{ refreshPlanning().then(function(){ try{ renderCal(); }catch(_){} }); }catch(_){}
      return;
    }
  }
  // Contrôle : si on déplace vers un jour passé, refuse.
  if(_calIsPastIso(drag.targetDate)){
    if(typeof showToast === 'function') showToast('Impossible de déplacer un créneau vers une date passée.', 'danger');
    _CAL_DRAG = null;
    // v2.6.1 : ROLLBACK VISUEL. Sans lui, le bloc restait a la position ou on
    // l'avait lache — le DOM ayant ete manipule pendant le drag — alors que la
    // donnee n'avait pas bouge. L'ecran affichait donc un creneau a une date
    // passee, avec un message d'erreur par dessus, jusqu'au prochain rendu.
    // Meme traitement que la branche d'echec serveur de _persistCalDrag().
    try{ refreshPlanning().then(function(){ try{ renderCal(); }catch(_){} }); }catch(_){}
    return;
  }
  // PATCH la nouvelle position.
  _persistCalDrag(drag);
  _CAL_DRAG = null;
}

async function _persistCalDrag(drag){
  const eventId = drag.ev.id;
  const body = {
    date_prevue: drag.targetDate,
    heure_debut: _minsToHM(drag.targetStartMin),
    heure_fin:   _minsToHM(drag.targetEndMin),
  };
  try{
    const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId), {
      method: 'PATCH', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if(!r.ok){
      let msg = 'Modification refus\u00e9e';
      try{ const j = await r.json(); msg = j.detail || msg; }catch(_){}
      if(typeof showToast === 'function') showToast('Erreur : ' + msg, 'danger');
      // Rollback visuel : refetch pour restaurer l'ancienne position.
      await refreshPlanning(); renderCal();
      return;
    }
    if(typeof showToast === 'function'){
      const dateChanged = drag.targetDate !== drag.origDate;
      const dateFR = _fmtIsoDateFr(drag.targetDate) || drag.targetDate;
      const hStr = _minsToHM(drag.targetStartMin) + ' \u2013 ' + _minsToHM(drag.targetEndMin);
      const label = dateChanged
        ? ('Cr\u00e9neau d\u00e9plac\u00e9 au ' + dateFR + ' \u00b7 ' + hStr)
        : ('Horaires mis \u00e0 jour : ' + hStr);
      showToast(label, 'info');
    }
    await refreshPlanning(); renderCal();
  }catch(err){
    if(typeof showToast === 'function') showToast('Erreur r\u00e9seau \u2014 modification annul\u00e9e.', 'danger');
    await refreshPlanning(); renderCal();
  }
}

function _clusterDayEvents(events){
  if(!events.length) return [];
  const sorted = events.slice()
    .map(ev => ({ ev, s: _hmToMins(ev.start), e: _hmToMins(ev.end) }))
    .filter(o => o.s != null && o.e != null && o.e > o.s)
    .sort((a,b) => a.s - b.s);
  const clusters = [];
  let cur = null;
  sorted.forEach(o => {
    if(!cur){
      cur = { startMin: o.s, endMin: o.e, items: [o.ev] };
    } else if(o.s < cur.endMin){
      cur.endMin = Math.max(cur.endMin, o.e);
      cur.items.push(o.ev);
    } else {
      clusters.push(cur);
      cur = { startMin: o.s, endMin: o.e, items: [o.ev] };
    }
  });
  if(cur) clusters.push(cur);
  // Trier les items à l'intérieur du cluster pour un affichage stable
  clusters.forEach(c => {
    c.items.sort((a,b) => (_hmToMins(a.start)||0) - (_hmToMins(b.start)||0));
  });
  return clusters;
}
function _makeClusterBlock(cluster){
  if(!cluster || !cluster.items.length) return null;
  const startMin = cluster.startMin;
  const endMin = cluster.endMin;
  const top = ((startMin - CAL_HOUR_START*60) / 60) * CAL_HOUR_PX;
  const height = Math.max(28, ((endMin - startMin) / 60) * CAL_HOUR_PX - 2);
  const div = document.createElement('div');
  const single = (cluster.items.length === 1);
  // v2.5.27 : hoiste ev pour l'usage ci-dessous (corrige aussi le bug pre-existant qui accede a ev.template_id).
  const _ev0 = single ? cluster.items[0] : null;
  div.className = 'cal-event' + (single ? '' : ' cal-event-merged') + (_calIsRecurOccurrence(_ev0) ? ' is-from-template' : '');  // v2.7.2
  div.style.top = top + 'px';
  div.style.height = height + 'px';
  if(single && cluster.items[0].opNiveau){
    div.setAttribute('data-niveau', String(cluster.items[0].opNiveau));
  }
  const fmtHM = mins => {
    const h = Math.floor(mins/60), m = mins%60;
    return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');
  };
  if(single){
    const ev = cluster.items[0];
    const machineSuffix = ev.machine ? ' · ' + ev.machine : '';
    div.innerHTML = '<div class="cal-event-title">' + escHtml((ev.opName || '—') + machineSuffix) + '</div>' +
                    '<div class="cal-event-time">' + escHtml(ev.start) + ' – ' + escHtml(ev.end) + '</div>';
    // v2.6.0 : idem -- APRES innerHTML, sinon le badge est efface.
    if(!_calIsPastEvent(ev)) _appendNoOperatorBadge(div, ev);  // v2.7.0
    div.title = 'Cliquer pour afficher les détails';
    div.addEventListener('click', e => {
      e.stopPropagation();
      openPlanningDetailsModal([ev]);
    });
  } else {
    let listHtml = '<div class="cal-event-list">';
    cluster.items.forEach(ev => {
      const nivCls = ev.opNiveau ? (' cal-event-item-niv-' + ev.opNiveau) : '';
      const machine = ev.machine ? '<span class="cal-event-item-machine"> · ' + escHtml(ev.machine) + '</span>' : '';
      listHtml += '<div class="cal-event-item' + nivCls + '" data-event-id="' + escAttr(ev.id) + '">' +
                  '<span class="cal-event-item-time">' + escHtml(ev.start) + ' – ' + escHtml(ev.end) + '</span>' +
                  '<span class="cal-event-item-name">' + escHtml(ev.opName || '—') + machine + '</span>' +
                  '</div>';
    });
    listHtml += '</div>';
    const headTxt = escHtml(fmtHM(startMin)) + ' → ' + escHtml(fmtHM(endMin)) + ' · ' + cluster.items.length + ' op.';
    div.innerHTML = '<div class="cal-event-merged-head">' + headTxt + '</div>' + listHtml;
    div.title = 'Cliquer pour afficher les détails';
    div.style.cursor = 'pointer';
    div.addEventListener('click', e => {
      e.stopPropagation();
      openPlanningDetailsModal(cluster.items);
    });
  }
  return div;
}
function _hmToMins(s){
  const m = String(s||'').match(/^(\d{1,2}):(\d{2})$/);
  if(!m) return null;
  return parseInt(m[1],10)*60 + parseInt(m[2],10);
}
async function deletePlanningEvent(id){
  try{
    await fetch('/api/maintenance/events/' + encodeURIComponent(id),
                { method: 'DELETE', credentials: 'include' });
  }catch(e){}
  await refreshPlanning();
  renderCal();
}

// ── Modale Détails (créneau) ──────────────────────────────────────────
let _PLAN_DET_CASE_ID = null;
function _fmtIsoDateFr(iso){
  if(!iso) return '';
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(!m) return iso;
  const d = new Date(parseInt(m[1],10), parseInt(m[2],10)-1, parseInt(m[3],10));
  return d.toLocaleDateString('fr-FR', {weekday:'long', day:'2-digit', month:'long', year:'numeric'});
}
function openPlanningDetailsModal(events){
  if(!events || !events.length) return;
  const ev = events[0]; // une case par clic
  _PLAN_DET_CASE_ID = ev.id;
  const m = document.getElementById('planning-details-modal');
  if(!m) return;
  const titleEl = document.getElementById('plan-det-title');
  const dtEl = document.getElementById('plan-det-date');
  const listEl = document.getElementById('plan-det-list');
  if(titleEl) titleEl.textContent = 'Détails du créneau';
  if(dtEl) dtEl.textContent = _fmtIsoDateFr(ev.date);
  // v2.6.1 : horaires dans le bandeau du haut, a cote de la date.
  const tmEl = document.getElementById('plan-det-time');
  if(tmEl) tmEl.textContent = (ev.start && ev.end) ? (ev.start + ' \u2013 ' + ev.end) : '—';
  if(listEl){
    const ops = Array.isArray(ev.operations) ? ev.operations : [];
    // Machines couvertes par le créneau (union des machines des ops).
    const machineUnion = [];
    ops.forEach(op => {
      (op.machines || []).forEach(m => { if(machineUnion.indexOf(m) < 0) machineUnion.push(m); });
    });
    const machinesLabel = machineUnion.length ? machineUnion.join(' · ') : (ev.machine || '—');
    // v2.2.48 : regroupe par code, préserve statut/done_by/done_at par machine.
    const _grouped = new Map();
    for(const op of ops){
      const key = op.opTypeId || op._op_id || op.opName || Math.random();
      if(!_grouped.has(key)){
        _grouped.set(key, { opName: op.opName || '—', machineData: [] });
      }
      const entry = _grouped.get(key);
      for(const m of (op.machines || [])){
        if(entry.machineData.find(x => x.machine === m)) continue;
        entry.machineData.push({
          machine: m,
          statut: op.statut || 'a_faire',
          done_at: op.done_at || null,
          done_by: op.done_by || null,
        });
      }
    }
    const opsListForNames = Array.isArray(ev.operators) ? ev.operators : [];
    const _resolveName = (uid) => {
      if(uid == null) return '';
      const u = opsListForNames.find(x => Number(x.id) === Number(uid));
      return u ? (u.nom || '') : '';
    };
    const _fmtDoneAt = (iso) => {
      if(!iso) return '';
      const m = String(iso).match(/^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})/);
      return m ? (m[1] + ':' + m[2]) : String(iso).slice(11,16);
    };
    const groupedOps = Array.from(_grouped.values());
    const opsHtml = groupedOps.length
      ? groupedOps.map(op => {
          const rows = op.machineData.map(md => {
            // v2.5.11 : 3 etats visuels distincts : termine (ok), invalidee (gris),
            // a_faire (defaut).
            // v2.6.1 : la machine est TOUJOURS nommee, meme quand l'operation
            // n'en concerne qu'une seule. Avant, `machineData.length === 1` la
            // masquait : sur un creneau couvrant Cohesio 1 ET Cohesio 2, une
            // operation mono-machine s'affichait « En attente » sans dire
            // laquelle des deux etait visee. Repli silencieux si la machine
            // est absente de la donnee (creneaux anciens).
            const mOn   = md.machine ? (' sur ' + escHtml(md.machine)) : '';
            const done = md.statut === 'termine';
            const invalidated = md.statut === 'invalidee';
            let icon, label, color;
            if(done){
              icon = '<span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:var(--ok);color:#fff;flex-shrink:0"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></span>';
              label = 'Effectu\u00e9e' + mOn +
                      (md.done_by ? ' \u00b7 par ' + escHtml(_resolveName(md.done_by) || 'op. inconnu') : '') +
                      (md.done_at ? ' \u00e0 ' + escHtml(_fmtDoneAt(md.done_at)) : '');
              color = 'var(--text2)';
            } else if(invalidated){
              icon = '<span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:var(--muted);color:#fff;flex-shrink:0" title="Saisie invalid\u00e9e administrativement"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="5" x2="19" y2="19"/><line x1="5" y1="19" x2="19" y2="5"/></svg></span>';
              const invBy = md.invalidated_by_nom ? ' \u00b7 par ' + escHtml(md.invalidated_by_nom) : '';
              const invAt = md.invalidated_at ? ' le ' + escHtml(_fmtDoneAt(md.invalidated_at)) : '';
              label = 'Invalid\u00e9e' + mOn + invBy + invAt;
              color = 'var(--muted)';
            } else if(_calIsPastEvent(ev)){
              // v2.7.1 : créneau clôturé -> l'opération ne sera jamais saisie.
              icon = '<span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;border:1.5px solid var(--danger,#f87171);color:var(--danger,#f87171);flex-shrink:0;font-size:11px;font-weight:800;line-height:1">!</span>';
              label = md.machine ? (escHtml(md.machine) + ' \u2014 non r\u00e9alis\u00e9e') : 'Non r\u00e9alis\u00e9e';
              color = 'var(--danger,#f87171)';
            } else {
              icon = '<span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;border:1.5px solid var(--border);flex-shrink:0"></span>';
              label = md.machine ? (escHtml(md.machine) + ' \u2014 en attente') : 'En attente';
              color = 'var(--muted)';
            }
            const extraStyle = invalidated ? ';text-decoration:line-through;text-decoration-color:var(--muted)' : '';
            return '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;color:' + color + extraStyle + '">' +
              icon + '<span>' + label + '</span>' +
            '</div>';
          }).join('');
          return '<div class="plan-det-case-op" style="flex-direction:column;align-items:stretch;gap:2px">' +
            '<div style="display:flex;align-items:center;gap:8px">' +
              '<span class="plan-det-case-op-bullet"></span>' +
              '<span class="plan-det-case-op-name" style="white-space:normal">' + escHtml(op.opName) + '</span>' +
            '</div>' +
            '<div style="margin-left:16px;margin-top:2px">' + rows + '</div>' +
          '</div>';
        }).join('')
      : '<div class="plan-det-case-op-empty">Aucune opération définie.</div>';
    // Badge « Depuis modèle » — v2.6.1 : réservé aux créneaux GÉNÉRÉS par la
    // récurrence d'un modèle. Un créneau où l'on a simplement importé un modèle
    // depuis la liste des opérations n'en est pas une occurrence : ses ops ont
    // pu être retouchées, complétées par d'autres modèles, et rien ne le
    // resynchronisera avec le modèle. Afficher « Depuis modèle » y était
    // trompeur, l'infobulle annonçant même que le modèle « écrasera ces
    // opérations » — ce qui ne se produit que pour les occurrences générées.
    let tmplBadge = '';
    if(ev.template_id && ev.template_origin_date){
      const tmpl = (typeof TEMPLATES_STATE !== 'undefined' && TEMPLATES_STATE ? (TEMPLATES_STATE.list || []) : []).find(t => t.id === ev.template_id);
      const label = tmpl ? tmpl.name : ('#' + ev.template_id);
      tmplBadge = '<span class="tmpl-badge" title="Créneau lié à un modèle. Les modifs futures du modèle écraseront ces opérations.">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>' +
        'Depuis modèle : ' + escHtml(label) +
      '</span>';
    }
    listEl.innerHTML =
      '<div class="plan-det-case-head">' +
        (tmplBadge ? '<div style="width:100%;margin-bottom:6px">' + tmplBadge + '</div>' : '') +
        '<div class="plan-det-case-machine">' +
          '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' +
          escHtml(machinesLabel) +
        '</div>' +
        '<div class="plan-det-case-time">' +
          '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          escHtml(ev.start) + ' \u2013 ' + escHtml(ev.end) +
        '</div>' +
      '</div>' +
      // v2.5.25 : bandeau warning si aucun operateur assigne (admin uniquement).
      (MAINT_ROLE !== 'operator' && !_calIsPastEvent(ev) && !(Array.isArray(ev.operators) && ev.operators.length)
        ? '<div style="margin-top:10px;padding:10px 14px;border-radius:8px;background:rgba(245,158,11,.12);border:1px solid var(--warn,#f59e0b);color:var(--warn,#f59e0b);font-size:13px;line-height:1.4;display:flex;align-items:center;gap:10px">' +
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86l-8.18 14.16A2 2 0 0 0 3.83 21h16.34a2 2 0 0 0 1.72-2.98L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>' +
            '<span style="flex:1"><strong>Aucun op\u00e9rateur assign\u00e9.</strong> Personne ne saura qu\'il y a une t\u00e2che.</span>' +
            '<button type="button" onclick="editCase(\'' + escAttr(ev.id) + '\')" style="background:var(--warn,#f59e0b);color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;flex-shrink:0">Assigner</button>' +
          '</div>'
        : '') +
      // Bloc op\u00e9rateurs (nouveau : groupe assign\u00e9 au cr\u00e9neau \u2014 partag\u00e9).
      '<div class="plan-det-case-ops-label">Op\u00e9rateurs assign\u00e9s (' +
        (Array.isArray(ev.operators) ? ev.operators.length : 0) + ')</div>' +
      '<div style="margin-top:6px;margin-bottom:6px">' +
        ((Array.isArray(ev.operators) && ev.operators.length)
          ? ev.operators.map(op => '<span style="display:inline-block;background:var(--accent-bg);color:var(--accent);border-radius:6px;padding:3px 9px;font-size:12px;font-weight:600;margin:0 6px 6px 0">' + escHtml(op.nom || '—') + '</span>').join('')
          : '<span style="color:var(--muted);font-style:italic;font-size:12px">Aucun opérateur assigné pour l\'instant.</span>'
        ) +
      '</div>' +
      '<div class="plan-det-case-ops-label">Opérations à effectuer (' + ops.length + ')</div>' +
      '<div class="plan-det-case-ops-list">' + opsHtml + '</div>' +
      // v2.7.0 : créneau clôturé -> plus d'actions de planification, un
      // bandeau qui dit pourquoi et où consigner une intervention faite.
      (_calIsPastEvent(ev)
        ? '<div class="plan-det-closed">' +
            '<strong>Créneau clôturé.</strong> Sa date est passée : il ne peut plus être ' +
            'déplacé, modifié ni supprimé. Pour consigner une intervention déjà ' +
            'réalisée, utilise l\'enregistrement d\'opération. Une saisie déjà ' +
            'enregistrée reste corrigeable depuis l\'historique des opérations.' +
          '</div>'
        : '<div class="plan-det-case-actions">' +
            '<button type="button" class="case-action-btn edit" onclick="editCase(\'' + escAttr(ev.id) + '\')">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
              ' Modifier' +
            '</button>' +
            '<button type="button" class="case-action-btn del" onclick="confirmDeleteCase(\'' + escAttr(ev.id) + '\')">' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
              ' Supprimer' +
            '</button>' +
          '</div>');
  }
  m.classList.add('open');
  m.setAttribute('aria-hidden','false');
  document.body.style.overflow = 'hidden';
}
function closePlanningDetailsModal(){
  const m = document.getElementById('planning-details-modal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden','true'); }
  document.body.style.overflow = '';
  _PLAN_DET_CASE_ID = null;
}
async function deletePlanningEvent(id){
  try{
    await fetch('/api/maintenance/events/' + encodeURIComponent(id),
                { method: 'DELETE', credentials: 'include' });
  }catch(e){}
  await refreshPlanning();
  renderCal();
}
// v2.5.2 : suppression créneau, un seul modal, deux modes.
//   - 'standard' : header neutre, liste des ops planifiées, boutons Annuler
//     / Supprimer. C'est le remplacement du confirm() natif moche.
//   - 'forced'   : header rouge, warning irréversible, liste UNIQUEMENT des
//     ops déjà 'termine' + méta (date + opérateur), boutons Annuler /
//     Supprimer quand même. Bascule automatique quand le backend renvoie 409.
//
// v2.4.19 : côté backend, DELETE /api/maintenance/events/{id} renvoie 409
// avec un confirm_token déterministe si des ops sont 'termine'. On rappelle
// DELETE avec ?confirm_token=<hash> pour finaliser.
async function confirmDeleteCase(id){
  const ev = PLANNING_STATE.list.find(e => String(e.id) === String(id));
  if(!ev){ showToast('Créneau introuvable.', 'danger'); return; }
  _openDeleteCaseModal({ mode: 'standard', ev: ev });
}

// Effectue le DELETE avec ou sans token. Sur 409, remplace le contenu du
// même modal (mode 'forced') sans fermeture visible. Sur succès, ferme
// tout et rafraîchit. Sur autre erreur, laisse le modal ouvert et débloque
// le bouton pour retenter.
async function _doDeletePlanningEvent(ev, token){
  const id = ev && ev.id;
  if(id == null){ showToast('Créneau introuvable.', 'danger'); return; }
  let url = '/api/maintenance/events/' + encodeURIComponent(id);
  if(token){ url += '?confirm_token=' + encodeURIComponent(token); }
  let r;
  try{
    r = await fetch(url, { method: 'DELETE', credentials: 'include' });
  }catch(e){
    showToast('Erreur réseau — suppression impossible.', 'danger');
    _unlockDeleteCaseConfirmBtn();
    return;
  }
  if(r.status === 409){
    let payload = null;
    try{ payload = await r.json(); }catch(_){}
    const detail = payload && payload.detail ? payload.detail : null;
    if(detail && detail.requires_confirmation && Array.isArray(detail.done_ops) && detail.confirm_token){
      // v2.5.3 : remplace le contenu du modal existant (pas de fermeture visible).
      _openDeleteCaseModal({ mode: 'forced', ev: ev, doneOps: detail.done_ops, token: detail.confirm_token });
      return;
    }
    showToast('Suppression refusée par le serveur.', 'danger');
    _unlockDeleteCaseConfirmBtn();
    return;
  }
  if(!r.ok){
    let msg = 'Erreur suppression.';
    try{ const j = await r.json(); if(j && j.detail){ msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } }catch(_){}
    showToast(msg, 'danger');
    _unlockDeleteCaseConfirmBtn();
    return;
  }
  _closeDeleteCaseModal();
  await refreshPlanning();
  closePlanningDetailsModal();
  renderCal();
  // v2.5.31 : recharge les modèles pour rafraîchir le badge « N supprimée(s) »
  // du panel Gestion des modèles (le panel dédié a été déplacé dans l'édition
  // du modèle). loadTemplates(true) déclenche renderTemplateManagePanel().
  try{ if(typeof loadTemplates === 'function') await loadTemplates(true); }catch(_){}
  showToast('Créneau supprimé.', 'info');
}

// v2.5.3 : ré-active le bouton "Supprimer" du modal (utilisé en cas d'erreur
// serveur pour permettre à l'admin de retenter sans devoir rouvrir le modal).
function _unlockDeleteCaseConfirmBtn(){
  const btn = document.getElementById('del-case-confirm-btn');
  if(!btn) return;
  btn.disabled = false;
  try{ delete btn.dataset._busy; }catch(_){ btn.dataset._busy = ''; }
}

// Le container statique #mroot n'existe pas sur maintenance_page — on crée
// le modal à la volée dans <body> et on le retire à la fermeture.
//
// v2.5.3 : idempotent. Si un modal est déjà ouvert (cas du switch
// standard → forced après un 409), on réutilise le wrap existant et on
// remplace juste son innerHTML — pas de fade out/in visible entre les
// deux étapes.
function _openDeleteCaseModal(opts){
  const ev = opts.ev || {};
  const mode = opts.mode || 'standard';
  const isForced = (mode === 'forced');
  const doneOps = Array.isArray(opts.doneOps) ? opts.doneOps : [];
  const token = opts.token || null;

  const _fmtDoneAt = (iso) => {
    if(!iso) return '';
    const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    return m ? (m[3]+'/'+m[2]+' à '+m[4]+':'+m[5]) : String(iso).slice(0,16).replace('T',' ');
  };

  // Bandeau récapitulatif du créneau (identique dans les 2 modes).
  const evHead = '<div style="font-size:12px;color:var(--muted);margin-bottom:12px">'
    + escHtml(ev.machine || '—') + ' · ' + escHtml(ev.date || '') + ' · '
    + escHtml(ev.start || '') + ' – ' + escHtml(ev.end || '')
    + '</div>';

  // Corps : en mode 'standard' on liste toutes les ops planifiées (puce +
  // libellé). En mode 'forced' on liste UNIQUEMENT les ops termine, avec la
  // coche verte + la date + le nom de l'opérateur.
  let bodyRows = '';
  if(isForced){
    bodyRows = doneOps.map(op => {
      const mach = Array.isArray(op.machines) && op.machines.length ? op.machines.join(' · ') : '';
      return '<div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;border-radius:8px;background:var(--bg);border:1px solid var(--border);margin-bottom:6px">'
        +   '<span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:var(--ok);color:#fff;flex-shrink:0;margin-top:1px">'
        +     '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
        +   '</span>'
        +   '<div style="flex:1;min-width:0">'
        +     '<div style="font-weight:600;color:var(--text);font-size:13px">' + escHtml(op.label || op.code) + (mach ? ' <span style="color:var(--muted);font-weight:400">— ' + escHtml(mach) + '</span>' : '') + '</div>'
        +     '<div style="font-size:12px;color:var(--text2);margin-top:2px">Effectuée' + (op.done_at ? ' le ' + escHtml(_fmtDoneAt(op.done_at)) : '') + (op.done_by_name ? ' par ' + escHtml(op.done_by_name) : '') + '</div>'
        +   '</div>'
        + '</div>';
    }).join('');
  } else {
    const ops = Array.isArray(ev.operations) ? ev.operations : [];
    if(ops.length){
      bodyRows = ops.map(op => {
        return '<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;background:var(--bg);border:1px solid var(--border);margin-bottom:6px">'
          +   '<span style="width:6px;height:6px;border-radius:50%;background:var(--accent);flex-shrink:0"></span>'
          +   '<span style="font-size:13px;color:var(--text)">' + escHtml(op.opName || '—') + '</span>'
          + '</div>';
      }).join('');
    } else {
      bodyRows = '<div style="font-size:12px;color:var(--muted);font-style:italic;margin-bottom:6px">Aucune opération sur ce créneau.</div>';
    }
  }

  // Header + phrase d'intro selon le mode.
  const titleColor = isForced ? 'var(--danger)' : 'var(--text)';
  const titleText  = isForced
    ? 'Créneau contenant des opérations effectuées'
    : 'Supprimer ce créneau ?';
  const n = doneOps.length;
  const introText = isForced
    ? ('<strong>' + n + ' opération' + (n>1?'s':'') + ' déjà saisie' + (n>1?'s':'') + '</strong> sur ce créneau. '
       + 'La suppression effacera <strong>définitivement</strong> la traçabilité de ' + (n>1?'ces interventions':'cette intervention')
       + ' (date, opérateur, observations, photos). Action irréversible.')
    : 'La suppression retire le créneau du planning. Cette action ne peut pas être annulée.';
  const confirmLabel = isForced ? 'Supprimer quand même' : 'Supprimer';

  // v2.5.3 : réutilise le wrap si déjà ouvert (switch standard → forced).
  let wrap = document.getElementById('del-case-modal-overlay');
  const isNew = !wrap;
  if(isNew){
    wrap = document.createElement('div');
    wrap.id = 'del-case-modal-overlay';
    wrap.className = 'op-modal-overlay';
    wrap.style.display = 'flex';
    wrap.style.position = 'fixed';
    wrap.style.top = '0';
    wrap.style.left = '0';
    wrap.style.width = '100%';
    wrap.style.height = '100%';
    wrap.style.background = 'rgba(0,0,0,0.55)';
    wrap.style.zIndex = '9999';
    wrap.style.alignItems = 'center';
    wrap.style.justifyContent = 'center';
    wrap.addEventListener('click', (e) => { if(e.target === wrap) _closeDeleteCaseModal(); });
    document.body.appendChild(wrap);
    // Escape ferme (une seule fois par ouverture, retiré au close).
    const _escHandler = (e) => { if(e.key === 'Escape'){ e.preventDefault(); _closeDeleteCaseModal(); } };
    document.addEventListener('keydown', _escHandler, true);
    wrap._escHandler = _escHandler;
  }

  wrap.innerHTML = ''
    + '<div class="op-modal" role="dialog" aria-modal="true" style="max-width:560px;width:calc(100% - 40px);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;box-shadow:0 20px 50px rgba(0,0,0,0.4)">'
    +   '<div class="op-modal-title" style="color:' + titleColor + ';font-size:16px;font-weight:700;margin-bottom:10px">' + escHtml(titleText) + '</div>'
    +   evHead
    +   '<div style="font-size:13px;color:var(--text);line-height:1.5;margin-bottom:12px">' + introText + '</div>'
    +   '<div style="max-height:280px;overflow-y:auto;margin-bottom:14px">' + bodyRows + '</div>'
    +   '<div style="display:flex;justify-content:flex-end;gap:10px">'
    +     '<button type="button" id="del-case-cancel-btn" class="btn" style="background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer">Annuler</button>'
    +     '<button type="button" id="del-case-confirm-btn" class="btn btn-danger" style="background:var(--danger);color:#fff;border:none;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer">' + escHtml(confirmLabel) + '</button>'
    +   '</div>'
    + '</div>';

  const cancelBtn  = document.getElementById('del-case-cancel-btn');
  const confirmBtn = document.getElementById('del-case-confirm-btn');
  if(cancelBtn)  cancelBtn.addEventListener('click', _closeDeleteCaseModal);
  if(confirmBtn) confirmBtn.addEventListener('click', () => {
    // Anti double-clic pendant que la requête part.
    if(confirmBtn.dataset._busy === '1') return;
    confirmBtn.dataset._busy = '1';
    confirmBtn.disabled = true;
    // v2.5.3 : NE PAS fermer ici. Le modal reste ouvert :
    //   - succès (200) → _closeDeleteCaseModal() dans _doDeletePlanningEvent
    //   - 409          → _openDeleteCaseModal() rebâtit le contenu (mode forced)
    //   - erreur       → bouton ré-activé par _unlockDeleteCaseConfirmBtn
    _doDeletePlanningEvent(ev, token);
  });
  // Focus par défaut sur Annuler (moindre risque).
  requestAnimationFrame(() => { if(cancelBtn) cancelBtn.focus(); });
}

function _closeDeleteCaseModal(){
  const w = document.getElementById('del-case-modal-overlay');
  if(!w) return;
  try{ if(w._escHandler) document.removeEventListener('keydown', w._escHandler, true); }catch(_){}
  w.remove();
}

function editCase(id){
  const ev = PLANNING_STATE.list.find(e => String(e.id) === String(id));
  if(!ev){ showToast('Créneau introuvable.', 'danger'); return; }
  // v2.7.0 : la modale de créneau EST le formulaire de planification. Sur un
  // créneau clôturé elle n'a plus d'objet — le serveur refuserait de toute
  // façon. La consultation reste ouverte via la modale de détails.
  if(_calIsPastEvent(ev)){
    showToast('Créneau passé : il est clôturé et n\'est plus modifiable.', 'info');
    return;
  }
  closePlanningDetailsModal();
  openCaseModal({
    editId: ev.id,
    iso: ev.date,
    start: ev.start,
    end: ev.end,
    operations: ev.operations || [],
  });
}

// ── Clic sur calendrier → ouverture modale "Nouveau créneau" ──────────
function onCalCellClick(e){
  // Ignore clicks on existing events (their own click handler ouvre les détails)
  if(e.target.closest('.cal-event')) return;
  // Mode opérateur : lecture seule, on n'ouvre pas le modal de création
  if(MAINT_ROLE === 'operator') return;
  const col = e.currentTarget;
  if(!col) return;
  const iso = col.getAttribute('data-date');
  if(!iso) return;
  // v2.6.1 : le planning sert a planifier — pas de creation dans le passe. Une
  // intervention deja realisee se consigne via l'enregistrement d'operation,
  // qui accepte les dates passees (source 'non_planifie').
  if(_calIsPastIso(iso)){
    if(typeof showToast === 'function'){
      showToast('Le planning ne permet pas de créer un créneau à une date passée. Utilise l\'enregistrement d\'opération.', 'danger');
    }
    return;
  }
  const rect = col.getBoundingClientRect();
  const y = e.clientY - rect.top;
  const hourFloat = CAL_HOUR_START + (y / CAL_HOUR_PX);
  let h = Math.floor(hourFloat);
  if(h < CAL_HOUR_START) h = CAL_HOUR_START;
  if(h > CAL_HOUR_END - 1) h = CAL_HOUR_END - 1;
  openCaseModal({ iso, defaultHour: h });
}

// ── Modale Créneau (création + édition) ──────────────────────────────
let _PENDING_CASE = null;
let _CASE_OPERATORS = [];  // [{id, nom}] : opérateurs assignés au créneau en cours d'édition
let _OPERATORS_CATALOG = null;  // cache : [{id, nom, ...}]

async function _loadOperatorsCatalog(){
  if(_OPERATORS_CATALOG) return _OPERATORS_CATALOG;
  try{
    const r = await fetch('/api/maintenance/operators', { credentials:'include' });
    if(!r.ok){ _OPERATORS_CATALOG = []; return _OPERATORS_CATALOG; }
    const d = await r.json();
    _OPERATORS_CATALOG = d.operators || [];
  }catch(e){ _OPERATORS_CATALOG = []; }
  return _OPERATORS_CATALOG;
}

function renderCaseOperators(){
  const list = document.getElementById('case-mod-operators-list');
  const picker = document.getElementById('case-mod-operator-picker');
  if(list){
    if(!_CASE_OPERATORS.length){
      // v2.5.25 : hint explicite en warning discret si vide.
      list.innerHTML = '<div style="font-size:12px;color:var(--warn,#f59e0b);padding:6px 0;display:flex;align-items:center;gap:6px"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><circle cx="12" cy="12" r="10"/></svg> Aucun op\u00e9rateur assign\u00e9 \u2014 personne ne saura qu\'il y a une t\u00e2che.</div>';
    } else {
      list.innerHTML = _CASE_OPERATORS.map(op =>
        `<div class="case-op-item" style="display:inline-flex;align-items:center;gap:6px;background:var(--accent-bg);color:var(--accent);border-radius:8px;padding:4px 10px;font-size:12px;font-weight:600;margin:4px 6px 0 0">${op.nom}<button type="button" onclick="removeCaseOperator(${op.id})" style="background:transparent;border:none;color:inherit;cursor:pointer;font-size:14px;line-height:1;padding:0 0 0 4px">×</button></div>`
      ).join('');
    }
  }
  if(picker){
    const assigned = new Set(_CASE_OPERATORS.map(o => o.id));
    const available = (_OPERATORS_CATALOG || []).filter(u => !assigned.has(u.id));
    picker.innerHTML = '<option value="">Ajouter un opérateur…</option>' +
      available.map(u => `<option value="${u.id}">${u.nom}</option>`).join('');
  }
}

// v2.5.28 : quick-select "Tous les operateurs" pour la modale case.
function caseAddAllOperators(){
  const all = _OPERATORS_CATALOG || [];
  let added = 0;
  for(const u of all){
    if(!_CASE_OPERATORS.find(o => o.id === u.id)){
      _CASE_OPERATORS.push({ id: u.id, nom: u.nom });
      added++;
    }
  }
  renderCaseOperators();
  if(typeof showToast === 'function' && added){
    showToast(added + ' op\u00e9rateur' + (added > 1 ? 's ajout\u00e9s' : ' ajout\u00e9') + '.', 'info');
  }
}

// v2.6.0 : caseAddOperatorsOnShift() retiree avec son bouton « + Travaillant ce
// jour ». L'endpoint GET /api/maintenance/operators/on-shift est conserve tel
// quel : il est isole et resservira si le croise avec le planning RH revient.

// v2.5.28 : quick-select "Tous" pour la modale template editor (operateurs par defaut).
function tmplAddAllDefaultOps(){
  const all = _OPERATORS_CATALOG || [];
  let added = 0;
  for(const u of all){
    if(!_TMPL_DEFAULT_OPS.find(o => o.id === u.id)){
      _TMPL_DEFAULT_OPS.push({ id: u.id, nom: u.nom });
      added++;
    }
  }
  renderTmplDefaultOps();
  if(typeof showToast === 'function' && added){
    showToast(added + ' op\u00e9rateur' + (added > 1 ? 's ajout\u00e9s' : ' ajout\u00e9') + '.', 'info');
  }
}

function addCaseOperatorFromPicker(sel){
  const id = parseInt(sel.value, 10);
  if(!id) return;
  const user = (_OPERATORS_CATALOG || []).find(u => u.id === id);
  if(!user) return;
  if(_CASE_OPERATORS.find(o => o.id === id)) return;
  _CASE_OPERATORS.push({ id: user.id, nom: user.nom });
  renderCaseOperators();
}

function removeCaseOperator(id){
  _CASE_OPERATORS = _CASE_OPERATORS.filter(o => o.id !== id);
  renderCaseOperators();
}

let _CASE_OPS = [];
async function openCaseModal(opts){
  _CASE_OPERATORS = [];
  let preselectedTemplateId = null;
  if(opts && opts.editId){
    const ev = PLANNING_STATE.list.find(e => String(e.id) === String(opts.editId));
    if(ev && Array.isArray(ev.operators)){
      _CASE_OPERATORS = ev.operators.map(o => ({ id: o.id, nom: o.nom }));
    }
    if(ev && ev.template_id) preselectedTemplateId = ev.template_id;
  }
  // Ouvre le modal immédiatement pour ne pas laisser l'utilisateur devant
  // un écran vide en cas de latence sur /api/maintenance/operators.
  const result = _openCaseModalInner(opts);
  renderCaseOperators();  // affiche déjà les opérateurs pré-remplis
  // Charge le catalogue en arrière-plan puis rerender le picker.
  _loadOperatorsCatalog().then(() => renderCaseOperators()).catch(() => {});
  // Charge les templates puis pré-sélectionne si le créneau en est issu
  loadTemplates().then(() => refreshCaseTemplatePicker()).catch(() => {});
  // v2.6.1 : en EDITION on preserve le lien existant (une occurrence de
  // recurrence doit rester rattachee a son modele) ; en CREATION il n'y a
  // jamais de lien, meme via « Créer depuis un modèle » — cf. applyCaseTemplate.
  if(_PENDING_CASE) _PENDING_CASE.template_id = opts.editId ? preselectedTemplateId : null;
  // v2.6.1 : le rappel des modeles importes repart de zero a chaque ouverture.
  // En EDITION d'un creneau deja issu d'un modele, on reaffiche son origine
  // sans reimporter ses ops (elles sont deja chargees depuis l'event).
  _CASE_TMPL_USED = [];
  if(preselectedTemplateId){
    loadTemplates().then(function(){
      const t = (TEMPLATES_STATE.list || []).find(x => String(x.id) === String(preselectedTemplateId));
      if(t){ _CASE_TMPL_USED = [{ id: t.id, name: t.name }]; }
      renderCaseTemplatesApplied();
    }).catch(function(){});
  } else {
    renderCaseTemplatesApplied();
  }
  return result;
}
function _openCaseModalInner(opts){
  opts = opts || {};
  if(!opts.iso){ showToast('Date manquante.', 'danger'); return; }
  _PENDING_CASE = { editId: opts.editId || null, iso: opts.iso };
  // v2 : merge des rows DB par code pour affichage groupé.
  //   Après le split per-machine, une op X sur [Coh1, Coh2] = 2 rows DB.
  //   Pour l'admin dans la modal, on regroupe : 1 seule ligne avec chips
  //   [Coh1] [Coh2] cochés. Le sync backend explode ensuite.
  //   _op_ids_by_machine et _statuts_by_machine : trackent l'origine DB
  //   de chaque machine pour DELETE ciblé + lock des chips termine.
  const rawOps = Array.isArray(opts.operations) ? opts.operations : [];
  const _byCode = new Map();
  const _emptyRows = [];
  for(const o of rawOps){
    if(!o.opTypeId){
      // Ligne vide fraîchement ajoutée via "+ Ajouter une opération"
      _emptyRows.push({
        _op_id: null,
        opTypeId: '',
        opName: '',
        opNiveau: null,
        opFreq: '',
        machines: [],
        _op_ids_by_machine: {},
        _statuts_by_machine: {},
      });
      continue;
    }
    const key = o.opTypeId;
    if(!_byCode.has(key)){
      // v2 : détecte les codes LIB-xxx pour pré-charger la row en mode Libre.
      //      _originalLibreCode / _originalLibreTitre permettent de savoir si
      //      le titre a été modifié au submit → PATCH /libres au lieu de POST.
      const isLibreCode = o.opTypeId && String(o.opTypeId).startsWith('LIB-');
      _byCode.set(key, {
        _op_id: null,  // legacy compat
        _mode: isLibreCode ? 'libre' : 'catalogue',
        _libreTitre: isLibreCode ? (o.opName || '') : '',
        _libreCodeResolved: isLibreCode ? o.opTypeId : null,
        _originalLibreCode: isLibreCode ? o.opTypeId : null,
        _originalLibreTitre: isLibreCode ? (o.opName || '') : '',
        opTypeId: o.opTypeId,
        opName:   o.opName   || '',
        opNiveau: o.opNiveau || null,
        opFreq:   o.opFreq   || '',
        machines: [],
        _op_ids_by_machine: {},
        _statuts_by_machine: {},
        // v185 : consignes admin (peut être vide). Prend la 1re rencontrée
        //   pour ce code (comportement raisonnable si machines multiples).
        //   Après édition, on PATCH toutes les rows du code avec la nouvelle valeur.
        consignes: (o.consignes || '').trim(),
        _consignes_original: (o.consignes || '').trim(),
        _consignes_open: !!((o.consignes || '').trim()),  // panel déplié si non vide
      });
    }
    const entry = _byCode.get(key);
    const m = (Array.isArray(o.machines) && o.machines.length) ? o.machines[0] : null;
    if(m && !entry.machines.includes(m)){
      entry.machines.push(m);
      entry._op_ids_by_machine[m] = o._op_id || null;
      entry._statuts_by_machine[m] = o.statut || o._statut || 'a_faire';
    }
  }
  _CASE_OPS = Array.from(_byCode.values()).concat(_emptyRows);
  const m = document.getElementById('planning-case-modal');
  if(!m) return;
  const dtEl = document.getElementById('case-mod-date');
  const sEl  = document.getElementById('case-mod-start');
  const eEl  = document.getElementById('case-mod-end');
  const nomEl = document.getElementById('case-mod-nom');
  const ttlEl = document.getElementById('case-mod-title');
  const lblEl = document.getElementById('case-mod-submit-label');
  // v2.4.29 : visibilite du bouton "Enregistrer comme modele" (edit only)
  const saveTmplBtn = document.getElementById('case-mod-save-as-tmpl');
  if(saveTmplBtn) saveTmplBtn.style.display = (typeof CASE_EDITING_ID !== 'undefined' && CASE_EDITING_ID) ? 'inline-block' : 'none';
  const isEdit = !!opts.editId;
  if(ttlEl) ttlEl.textContent = isEdit ? 'Modifier le créneau' : 'Nouveau créneau de maintenance';
  if(lblEl) lblEl.textContent = isEdit ? 'Enregistrer' : 'Créer';
  if(dtEl) dtEl.textContent = _fmtIsoDateFr(opts.iso);
  const h = Math.max(0, Math.min(23, opts.defaultHour || 8));
  if(sEl) sEl.value = opts.start || (String(h).padStart(2,'0') + ':00');
  if(eEl) eEl.value = opts.end   || (String(Math.min(h+1, 23)).padStart(2,'0') + ':00');
  // v2.6.1 : recap des horaires dans le bandeau du haut. Les champs de saisie
  // restent la source de verite ; le bandeau se contente de les refleter, pour
  // que date et horaires soient lisibles d'un coup d'oeil sans descendre.
  _syncCaseTimeRecap();
  [sEl, eEl].forEach(function(el){
    if(!el || el._dtRecapBound) return;
    el._dtRecapBound = true;
    el.addEventListener('input',  _syncCaseTimeRecap);
    el.addEventListener('change', _syncCaseTimeRecap);
  });
  // v2.5.14 : créneau passé -> horaires en lecture seule (même règle que le drag & drop).
  try{
    const _todayIso = _calIsoYMD(new Date());
    const _isPast = String(opts.iso || '') < _todayIso;
    if(isEdit && _isPast){
      if(sEl){ sEl.readOnly = true; sEl.title = 'Cr\u00e9neau pass\u00e9 \u2014 horaires non modifiables.'; sEl.style.opacity = '.55'; sEl.style.cursor = 'not-allowed'; }
      if(eEl){ eEl.readOnly = true; eEl.title = 'Cr\u00e9neau pass\u00e9 \u2014 horaires non modifiables.'; eEl.style.opacity = '.55'; eEl.style.cursor = 'not-allowed'; }
    } else {
      if(sEl){ sEl.readOnly = false; sEl.title = ''; sEl.style.opacity = ''; sEl.style.cursor = ''; }
      if(eEl){ eEl.readOnly = false; eEl.title = ''; eEl.style.opacity = ''; eEl.style.cursor = ''; }
    }
  }catch(_){}
  // En édition, pré-remplit le nom depuis l'event en cours.
  if(nomEl){
    let currentNom = '';
    if(isEdit){
      try{
        const ev = PLANNING_STATE.list.find(e => String(e.id) === String(opts.editId));
        currentNom = (ev && ev.nom) ? ev.nom : '';
      }catch(e){}
    }
    nomEl.value = currentNom;
  }
  renderCaseOpsList();
  m.classList.add('open');
  m.setAttribute('aria-hidden','false');
  document.body.style.overflow = 'hidden';
  // v2.6.1 : le focus allait sur le champ « Heure de début ». Or le timepicker
  // maison s'ouvre sur l'evenement focus (mysifa_timepicker.js) : le panneau
  // heures/minutes se depliait donc tout seul a chaque ouverture de modale, par
  // dessus le formulaire, alors que les horaires par defaut conviennent le plus
  // souvent. On donne le focus au premier champ de saisie reel — le nom du
  // creneau — qui n'ouvre aucun panneau flottant. Le clavier entre bien dans la
  // modale, sans rien deplier.
  setTimeout(() => { (nomEl || sEl)?.focus(); }, 60);
}
function closeCaseModal(){
  const m = document.getElementById('planning-case-modal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden','true'); }
  document.body.style.overflow = '';
  _PENDING_CASE = null;
  _CASE_OPS = [];
}
// Machines disponibles pour l'atelier (source unique pour le picker).
const CASE_MACHINES_LIST = ['Cohésio 1', 'Cohésio 2', 'DSI', 'Repiquage'];

function addCaseOp(){
  // v2 : mode Catalogue par défaut, avec possibilité de switch vers Libre.
  // On laisse ajouter même sans catalogue (l'admin pourra créer une libre).
  _CASE_OPS.push({
    _op_id: null,
    _mode: 'catalogue',        // 'catalogue' | 'libre'
    _libreTitre: '',           // titre saisi en mode libre
    _libreCodeResolved: null,  // LIB-xxx si résolu via autocomplete
    opTypeId: '',
    opName: '',
    opNiveau: null,
    opFreq: '',
    machines: [],
    _op_ids_by_machine: {},
    _statuts_by_machine: {},
    // v185 : consignes admin
    consignes: '',
    _consignes_original: '',
    _consignes_open: false,
  });
  renderCaseOpsList();
  // Focus le dernier select
  setTimeout(() => {
    const list = document.getElementById('case-mod-ops-list');
    if(list){
      const selects = list.querySelectorAll('select');
      if(selects.length) selects[selects.length - 1].focus();
    }
  }, 50);
}
function updateCaseOp(idx, opTypeId){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  const op = OPS_TYPES_STATE.list.find(t => t.id === opTypeId);
  if(op){
    _CASE_OPS[idx] = {
      _op_id:   cur._op_id || null,
      opTypeId: op.id,
      opName:   op.nom,
      opNiveau: op.niveau || null,
      opFreq:   op.frequence || '',
      // On préserve les machines déjà cochées.
      machines: Array.isArray(cur.machines) ? cur.machines.slice() : [],
    };
  } else {
    _CASE_OPS[idx] = { _op_id: cur._op_id || null, opTypeId: '', opName: '', opNiveau: null, opFreq: '', machines: Array.isArray(cur.machines) ? cur.machines.slice() : [] };
  }
}
function toggleCaseOpMachine(idx, machine){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  const list = Array.isArray(cur.machines) ? cur.machines : [];
  const pos = list.indexOf(machine);
  if(pos >= 0) list.splice(pos, 1); else list.push(machine);
  cur.machines = list;
  renderCaseOpsList();
}
// v2 : setter (une seule machine par op après le split 1:1) — remplace le
// toggle sur les 4 chips par un dropdown unique dans la modal.
function setCaseOpMachine(idx, machine){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  cur.machines = machine ? [machine] : [];
  renderCaseOpsList();
}
function removeCaseOp(idx){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  _CASE_OPS.splice(idx, 1);
  renderCaseOpsList();
}
// v2 : switch entre Catalogue et Libre pour une op de la modal case admin
function switchCaseOpMode(idx, mode){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  cur._mode = (mode === 'libre') ? 'libre' : 'catalogue';
  if(cur._mode === 'catalogue'){
    // Reset les champs libres, préserve les machines
    cur._libreTitre = '';
    cur._libreCodeResolved = null;
    cur.opTypeId = '';
    cur.opName = '';
    cur.opNiveau = null;
    cur.opFreq = '';
  } else {
    // Reset le catalogue si on switch en libre
    cur.opTypeId = '';
    cur.opName = '';
    cur.opNiveau = null;
    cur.opFreq = '';
  }
  renderCaseOpsList();
  // Focus le champ pertinent après re-render
  setTimeout(() => {
    const list = document.getElementById('case-mod-ops-list');
    if(!list) return;
    if(mode === 'libre'){
      const el = list.querySelector('.case-op-libre-titre[data-idx="' + idx + '"]');
      if(el) el.focus();
    } else {
      const el = list.querySelector('select.case-op-catalogue-select[data-idx="' + idx + '"]');
      if(el) el.focus();
    }
  }, 60);
}
// v2 : update titre libre d'une op (from oninput)
function updateCaseOpLibreTitre(idx, value){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  cur._libreTitre = value || '';
  cur._libreCodeResolved = null;  // reset la suggestion si l'user retape
  // opName reflète le titre libre pour affichage propre au submit
  cur.opName = cur._libreTitre;
}
// v2 : autocomplete pour le champ titre libre (per-row)
const _caseOpLibreTimers = {};
async function caseOpLibreAutocompleteInput(idx){
  updateCaseOpLibreTitre(idx, (document.querySelector('.case-op-libre-titre[data-idx="' + idx + '"]') || {}).value || '');
  clearTimeout(_caseOpLibreTimers[idx]);
  const panel = document.querySelector('.case-op-libre-autocomplete[data-idx="' + idx + '"]');
  const q = (_CASE_OPS[idx] && _CASE_OPS[idx]._libreTitre || '').trim();
  if(q.length < 2){
    if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
    return;
  }
  _caseOpLibreTimers[idx] = setTimeout(async () => {
    try{
      const r = await fetch('/api/maintenance/codes/libres/autocomplete?q=' + encodeURIComponent(q) + '&limit=8', { credentials:'include' });
      if(!r.ok){ if(panel){ panel.style.display='none'; } return; }
      const d = await r.json();
      const suggestions = Array.isArray(d.suggestions) ? d.suggestions : [];
      if(!suggestions.length){
        if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
        return;
      }
      panel.innerHTML = suggestions.map(s =>
        '<div class="libre-suggestion" onclick="caseOpLibreSelectSuggestion(' + idx + ', \'' + escAttr(s.code) + '\', \'' + escAttr(s.label) + '\')">' +
          '<span class="libre-suggestion-label">' + escHtml(s.label) + '</span>' +
          '<span class="libre-suggestion-count">' + escHtml(s.code) + '</span>' +
        '</div>'
      ).join('');
      panel.style.display = 'block';
    }catch(e){
      if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
    }
  }, 220);
}
// v185 : toggle affichage du bloc consignes pour une op de la modal case
function toggleCaseOpConsignes(idx){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  cur._consignes_open = !cur._consignes_open;
  renderCaseOpsList();
  if(cur._consignes_open){
    setTimeout(() => {
      const el = document.querySelector('.case-op-consignes-textarea[data-idx="' + idx + '"]');
      if(el) el.focus();
    }, 60);
  }
}
function updateCaseOpConsignes(idx, value){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  _CASE_OPS[idx].consignes = value || '';
}
function caseOpLibreSelectSuggestion(idx, code, label){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  const cur = _CASE_OPS[idx];
  cur._libreTitre = label;
  cur._libreCodeResolved = code;  // sera utilisé au submit sans re-créer
  cur.opName = label;
  const input = document.querySelector('.case-op-libre-titre[data-idx="' + idx + '"]');
  if(input) input.value = label;
  const panel = document.querySelector('.case-op-libre-autocomplete[data-idx="' + idx + '"]');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
}
function renderCaseOpsList(){
  const list = document.getElementById('case-mod-ops-list');
  if(!list) return;
  if(!_CASE_OPS.length){
    list.innerHTML = '<div class="case-ops-empty">Aucune opération ajoutée. Cliquez sur « Ajouter une opération » pour piocher dans la liste.</div>';
    return;
  }
  list.innerHTML = _CASE_OPS.map((op, idx) => {
    // v2 : détecte si au moins une machine de cette op (regroupée par code)
    // est termine ou invalidee → ligne entière read-only. On distingue les deux
    // dans le rendu (badge + couleur différents).
    const statuts = op._statuts_by_machine || {};
    const anyDone = Object.values(statuts).some(s => s === 'termine');
    const anyInvalidated = Object.values(statuts).some(s => s === 'invalidee');

    // Rendu READ-ONLY : op déjà saisie (termine) OU mise de côté (invalidee).
    if((anyDone || anyInvalidated) && op.opTypeId){
      const opName = op.opName || (OPS_TYPES_STATE.list.find(t => t.id === op.opTypeId) || {}).nom || op.opTypeId || '—';
      const nivBadge = op.opNiveau ? ' (N' + op.opNiveau + ')' : '';
      // v2.5.10 : color/badge/icone selon l'état dominant (invalidee prime : elle indique
      // une decision explicite de l'admin, alors que termine est le defaut).
      // v2.5.11 : le badge global n'est affiche QUE si toutes les machines de
      // l'op sont dans le meme etat solde. Sinon (mix invalidee+a_faire par ex.)
      // on laisse les chips par-machine parler d'elles-memes -- badge global
      // trompeur.
      const machineStatuses = (op.machines || []).map(m => statuts[m]).filter(s => s != null);
      const allInvalidated = machineStatuses.length > 0 && machineStatuses.every(s => s === 'invalidee');
      const allDone        = machineStatuses.length > 0 && machineStatuses.every(s => s === 'termine');
      const showGlobalBadge = allInvalidated || allDone;
      const isInvalid = allInvalidated;  // seule ce cas colore la ligne en gris
      const accentColor = allInvalidated ? 'var(--muted)' : (allDone ? 'var(--success,#34d399)' : 'var(--warn,#f59e0b)');
      const badgeText = allInvalidated ? 'Invalidée' : (allDone ? 'Effectué' : '');
      const badgeClass = allInvalidated ? 'case-ops-row-done-badge is-invalidee' : (allDone ? 'case-ops-row-done-badge' : 'case-ops-row-done-badge is-mixed');
      const headIcoPath = allInvalidated
        ? '<path d="M4.9 4.9l14.2 14.2"/><circle cx="12" cy="12" r="9"/>'
        : '<polyline points="20 6 9 17 4 12"/>';
      // Chips par machine : état individuel (termine / invalidee / a_faire).
      const chipsDone = (op.machines || []).map(m => {
        const st = statuts[m];
        const isMachDone = (st === 'termine');
        const isMachInv  = (st === 'invalidee');
        // v2.5.11 : chip invalidee tres visible -- fond gris fonce, bordure marquee,
        // X en gras, badge inline "invalidee" apres le nom pour lever tout doute.
        if(isMachInv){
          return '<span class="case-mach-chip is-invalidee" title="Saisie invalid\u00e9e administrativement" style="cursor:default;background:rgba(148,163,184,.25);color:var(--muted);border:1.5px solid var(--muted);text-decoration:line-through;text-decoration-color:var(--muted);text-decoration-thickness:1.5px;font-weight:600">' +
            '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px"><line x1="6" y1="6" x2="18" y2="18"/><line x1="6" y1="18" x2="18" y2="6"/></svg>' +
            escHtml(m) +
            '<span style="margin-left:6px;padding:1px 6px;border-radius:4px;background:var(--muted);color:var(--card);font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;text-decoration:none;display:inline-block">Invalid\u00e9e</span>' +
          '</span>';
        }
        const ico = isMachDone
          ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px;margin-right:3px"><polyline points="20 6 9 17 4 12"/></svg>'
          : '';
        return '<span class="case-mach-chip active" style="cursor:default;opacity:.85">' + ico + escHtml(m) + '</span>';
      }).join('');
      return '<div class="case-ops-row case-ops-row-done ' + (isInvalid ? 'is-invalidee' : '') + '" data-idx="' + idx + '">' +
        '<div class="case-ops-row-top">' +
          '<div class="case-ops-row-done-label">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:6px;color:' + accentColor + '">' + headIcoPath + '</svg>' +
            escHtml(opName) + nivBadge +
            (showGlobalBadge ? '<span class="' + badgeClass + '">' + badgeText + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<div class="case-ops-machines">' +
          '<span class="case-ops-machines-label">Machine(s)</span>' +
          chipsDone +
        '</div>' +
      '</div>';
    }

    // Rendu ÉDITABLE : distingue mode Catalogue et Libre.
    const mode = op._mode || 'catalogue';
    const machSet = new Set(Array.isArray(op.machines) ? op.machines : []);
    const chips = CASE_MACHINES_LIST.map(m => {
      const active = machSet.has(m);
      return '<button type="button" class="case-mach-chip' + (active ? ' active' : '') + '" onclick="toggleCaseOpMachine(' + idx + ', \'' + escAttr(m) + '\')" aria-pressed="' + (active ? 'true' : 'false') + '">' +
        escHtml(m) +
      '</button>';
    }).join('');
    const delBtn = '<button type="button" class="case-ops-row-del" onclick="removeCaseOp(' + idx + ')" title="Retirer cette opération" aria-label="Retirer">' +
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
    '</button>';

    let pickerHtml;
    if(mode === 'libre'){
      const libreTitre = op._libreTitre || '';
      pickerHtml =
        '<div class="case-op-libre-wrap" style="flex:1;position:relative">' +
          '<input type="text" class="ops-input case-op-libre-titre" data-idx="' + idx + '" ' +
            'value="' + escAttr(libreTitre) + '" maxlength="200" autocomplete="off" ' +
            'placeholder="Ex : Contrôle vibrations moteur — intervention ponctuelle" ' +
            'oninput="caseOpLibreAutocompleteInput(' + idx + ')">' +
          '<div class="libre-autocomplete-panel case-op-libre-autocomplete" data-idx="' + idx + '" style="display:none"></div>' +
        '</div>';
    } else {
      // v2.6.1 : une operation deja presente dans le creneau est GRISEE, avec le
      // motif. Avant, on pouvait la reselectionner et remplir toute la ligne
      // pour rien : la dedup (par code) la fusionnait a l'enregistrement et la
      // ligne « disparaissait », sans que l'utilisateur comprenne pourquoi.
      //
      // Deux precautions :
      //  - on exclut la ligne COURANTE du calcul (i !== idx), sinon l'option
      //    selectionnee serait elle-meme desactivee et le select perdrait sa
      //    valeur a chaque rendu ;
      //  - les operations deja effectuees ou invalidees, affichees en lecture
      //    seule plus haut, comptent comme presentes — sinon on pourrait
      //    rajouter une ligne pour une operation deja faite.
      const _usedElsewhere = new Set(
        _CASE_OPS.map((o, i) => (i !== idx && o.opTypeId) ? String(o.opTypeId) : null)
                 .filter(Boolean)
      );
      const options = '<option value="">Sélectionner une opération…</option>' +
        OPS_TYPES_STATE.list.map(t => {
          const taken = _usedElsewhere.has(String(t.id));
          return '<option value="' + escAttr(t.id) + '"' +
            (t.id === op.opTypeId ? ' selected' : '') +
            (taken ? ' disabled' : '') + '>' +
            escHtml(t.nom) + (t.niveau ? ' (N' + t.niveau + ')' : '') +
            (t.frequence ? ' · ' + escHtml(t.frequence) : '') +
            (taken ? ' — déjà dans le créneau' : '') +
          '</option>';
        }).join('');
      pickerHtml =
        '<select class="ops-select case-op-catalogue-select" data-idx="' + idx + '" onchange="updateCaseOp(' + idx + ', this.value)">' + options + '</select>';
    }
    const modeSwitchLink = (mode === 'libre')
      ? '<a href="javascript:void(0)" class="case-op-mode-link" onclick="switchCaseOpMode(' + idx + ', \'catalogue\')">← Choisir dans le catalogue</a>'
      : '<a href="javascript:void(0)" class="case-op-mode-link" onclick="switchCaseOpMode(' + idx + ', \'libre\')">Pas dans la liste ? Décrire une intervention libre</a>';
    // v185 : bloc consignes admin (collapsé par défaut)
    const consignesOpen = !!op._consignes_open;
    const consignesVal = op.consignes || '';
    const consignesHasContent = consignesVal.trim().length > 0;
    const consignesToggleLabel = consignesOpen
      ? '× Retirer les consignes'
      : (consignesHasContent ? '✎ Modifier les consignes' : '+ Ajouter des consignes');
    let consignesHtml = '<div class="case-ops-consignes">' +
      '<a href="javascript:void(0)" class="case-op-mode-link case-op-consignes-toggle" onclick="toggleCaseOpConsignes(' + idx + ')">' +
        consignesToggleLabel +
      '</a>';
    if(consignesOpen){
      consignesHtml +=
        '<textarea class="case-op-consignes-textarea" data-idx="' + idx + '" rows="3" ' +
          'placeholder="Instructions spécifiques pour cette opération (visibles par l\'opérateur avant validation)" ' +
          'oninput="updateCaseOpConsignes(' + idx + ', this.value)">' +
          escHtml(consignesVal) +
        '</textarea>';
    } else if(consignesHasContent){
      // Aperçu compact quand fermé mais rempli
      const preview = consignesVal.length > 100 ? (consignesVal.slice(0, 100) + '…') : consignesVal;
      consignesHtml += '<div class="case-op-consignes-preview">' + escHtml(preview) + '</div>';
    }
    consignesHtml += '</div>';
    return '<div class="case-ops-row" data-idx="' + idx + '">' +
      '<div class="case-ops-row-top">' +
        pickerHtml + delBtn +
      '</div>' +
      '<div class="case-ops-row-mode">' + modeSwitchLink + '</div>' +
      '<div class="case-ops-machines">' +
        '<span class="case-ops-machines-label">Machine(s)</span>' +
        chips +
      '</div>' +
      consignesHtml +
    '</div>';
  }).join('');
}
async function submitCaseModal(e){
  e.preventDefault();
  if(!_PENDING_CASE){ closeCaseModal(); return; }
  const start = (document.getElementById('case-mod-start')?.value || '').trim();
  const end = (document.getElementById('case-mod-end')?.value || '').trim();
  const nom = (document.getElementById('case-mod-nom')?.value || '').trim();
  if(!start || !end){ showToast('Indiquez les heures.', 'danger'); return; }
  const sm = _hmToMins(start), em = _hmToMins(end);
  if(sm == null || em == null){ showToast('Format heure invalide (HH:MM).', 'danger'); return; }
  if(em <= sm){ showToast('L\'heure de fin doit être après l\'heure de début.', 'danger'); return; }

  // v2 : Résolution des ops libres AVANT de construire wantedOps.
  //      Pour chaque _CASE_OPS en mode 'libre' sans code déjà résolu, on
  //      POST /api/maintenance/codes/libres avec le titre → récupère le code
  //      LIB-xxx (dedup exact-match backend). L'opTypeId est ensuite renseigné
  //      comme n'importe quel code catalogue pour le reste du flow.
  try{
    for(const op of _CASE_OPS){
      if((op._mode || 'catalogue') !== 'libre') continue;
      const titre = (op._libreTitre || '').trim();
      if(!titre) continue;  // skip vides
      if(op._originalLibreCode){
        // LIB préexistante (édition d'un créneau) : conserve le code, PATCH le
        // titre s'il a changé (impact rétroactif sur tous les événements
        // utilisant ce même code, comportement backend actuel).
        if(titre !== (op._originalLibreTitre || '')){
          const rPatch = await fetch('/api/maintenance/codes/libres/' + encodeURIComponent(op._originalLibreCode), {
            method:'PATCH', credentials:'include',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({label: titre}),
          });
          if(!rPatch.ok){
            const err = await rPatch.json().catch(()=>({}));
            showToast('Renommage libre échoué : ' + (err.detail || rPatch.status), 'danger');
            return;
          }
        }
        op.opTypeId = op._originalLibreCode;
        op.opName = titre;
      } else if(op._libreCodeResolved){
        // Autocomplete pick : code existant réutilisé, pas besoin de créer
        op.opTypeId = op._libreCodeResolved;
        op.opName = op.opName || titre;
      } else {
        // Nouvelle libre : POST /codes/libres (dedup exact-match backend)
        const rNew = await fetch('/api/maintenance/codes/libres', {
          method:'POST', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({label: titre}),
        });
        if(!rNew.ok){
          const err = await rNew.json().catch(()=>({}));
          showToast('Création code libre échouée : ' + (err.detail || rNew.status), 'danger');
          return;
        }
        const dNew = await rNew.json();
        op.opTypeId = dNew.code;
        op.opName = titre;
      }
    }
  }catch(e){
    showToast('Erreur résolution libre : ' + (e.message || e), 'danger');
    return;
  }

  // v2 : on inclut TOUTES les ops (y compris termine) dans wantedOps pour
  //      que _syncEventOpsAndOperators ne les supprime pas.
  const wantedOps = _CASE_OPS.filter(o => o.opTypeId).map(o => ({
    code: o.opTypeId,
    machines: Array.isArray(o.machines) ? o.machines.slice() : [],
    consignes: (o.consignes || '').trim(),  // v185
  }));
  if(!wantedOps.length){
    // Sépare le message si l'user avait des libres sans titre
    const hadUntitledLibres = _CASE_OPS.some(o => (o._mode === 'libre') && !(o._libreTitre || '').trim());
    if(hadUntitledLibres){
      showToast('Complète le titre des interventions libres avant de valider.', 'danger');
    } else {
      showToast('Ajoutez au moins une opération.', 'danger');
    }
    return;
  }
  // Chaque op doit être attribuée à au moins une machine.
  const missing = wantedOps.find(o => !o.machines.length);
  if(missing){
    const missName = (OPS_TYPES_STATE.list.find(t => t.id === missing.code) || {}).nom || missing.code;
    showToast('« ' + missName + ' » : sélectionne une machine avant de valider.', 'danger');
    return;
  }
  // Détection duplicate (op X + machine Y déjà présente dans le créneau).
  const seenPairs = new Map();  // key = "code@@machine" → name
  for(const w of wantedOps){
    for(const m of w.machines){
      const k = String(w.code) + '@@' + String(m);
      if(seenPairs.has(k)){
        const nm = (OPS_TYPES_STATE.list.find(t => t.id === w.code) || {}).nom || w.code;
        showToast('« ' + nm + ' » est déjà présente sur ' + m + ' dans ce créneau. Une même opération ne peut être ajoutée qu\'une seule fois par machine.', 'danger');
        return;
      }
      seenPairs.set(k, w.code);
    }
  }
  const operatorIds = (_CASE_OPERATORS || []).map(o => o.id);

  const editId = _PENDING_CASE.editId;
  try{
    if(editId){
      // PATCH horaires + sync ops + sync operators.
      // Sync operators/ops D'ABORD (indépendant des metas) — comme ça, même
      // si le PATCH meta échoue, les opérateurs assignés et les ops passent
      // quand même.
      let syncError = null;
      try{
        await _syncEventOpsAndOperators(editId, wantedOps, operatorIds);
      }catch(e){ syncError = e; }
      const rMeta = await fetch('/api/maintenance/events/' + encodeURIComponent(editId), {
        method:'PATCH', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ date_prevue: _PENDING_CASE.iso, heure_debut: start, heure_fin: end, nom }),
      });
      if(!rMeta.ok){
        const err = await rMeta.json().catch(() => ({}));
        throw new Error(err.detail || ('PATCH meta failed (' + rMeta.status + ')'));
      }
      if(syncError) throw syncError;
      showToast('Créneau mis à jour.', 'info');
    } else {
      // v2.2.49 : bloque côté client si aucun opérateur (double-guard avec backend)
      if(!operatorIds || !operatorIds.length){
        showToast('Sélectionne au moins un opérateur pour ce créneau.', 'danger');
        return;
      }
      const rNew = await fetch('/api/maintenance/events', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          date_prevue: _PENDING_CASE.iso,
          heure_debut: start, heure_fin: end, source: 'planifie',
          nom,
          ops: wantedOps, operators: operatorIds,
          template_id: _PENDING_CASE.template_id || null,
        }),
      });
      if(!rNew.ok){
        const err = await rNew.json().catch(()=>({}));
        throw new Error(err.detail || 'Création refusée');
      }
      showToast('Créneau créé.', 'info');
    }
  }catch(err){
    showToast('Erreur : ' + (err.message || err), 'danger');
    return;
  }
  closeCaseModal();
  await refreshPlanning();
  renderCal();
  // Côté opérateur : la tâche créée doit apparaître dans "Mes tâches" (si elle
  // inclut self dans le groupe) → refresh la liste.
  if(MAINT_ROLE === 'operator' && typeof opLoadTasks === 'function'){
    opLoadTasks();
  }
}

function _sameMachineSet(a, b){
  const A = (a || []).slice().sort();
  const B = (b || []).slice().sort();
  if(A.length !== B.length) return false;
  for(let i = 0; i < A.length; i++){ if(A[i] !== B[i]) return false; }
  return true;
}

async function _syncEventOpsAndOperators(eventId, wantedOps, wantedOperatorIds){
  // v179 : chaque row DB = 1 op × 1 machine (split per-machine).
  // wantedOps depuis le modal admin est encore au format {code, machines:[N]}.
  // On l'EXPLODE en entries {code, machine} pour comparer 1-pour-1 avec les
  // rows DB (chacune ayant 1 seule machine).
  const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '?_=' + Date.now(),
                       { credentials:'include', cache: 'no-store' });
  if(!r.ok) return;
  const d = await r.json();
  const ev = d.event || {};
  const currentOps = ev.ops || [];

  // EXPLODE : {code, machines:[Coh1, Coh2]} devient 2 entries {code, machine:"Coh1"} + {code, machine:"Coh2"}
  //   v185 : propage aussi consignes (partagées entre les machines d'un même code)
  const wantedExploded = [];
  for(const w of wantedOps){
    const ms = Array.isArray(w.machines) && w.machines.length ? w.machines : [null];
    for(const m of ms){
      wantedExploded.push({ code: w.code, machine: m, consignes: w.consignes || '' });
    }
  }

  // Clé unique = code + '@@' + machine (utilise '' si machine null)
  const keyOf = (code, machine) => String(code) + '@@' + (machine || '');
  const wantedKeys = new Set(wantedExploded.map(w => keyOf(w.code, w.machine)));

  // currentOps a machines:[singleMachine] après split. On dérive la clé pareil.
  const currentByKey = new Map();
  for(const op of currentOps){
    const machine = (Array.isArray(op.machines) && op.machines.length) ? op.machines[0] : null;
    currentByKey.set(keyOf(op.code, machine), op);
  }

  // Ops à ajouter (wanted mais pas current) → POST avec 1 seule machine + consignes
  for(const w of wantedExploded){
    const k = keyOf(w.code, w.machine);
    if(!currentByKey.has(k)){
      const postBody = { code: w.code, machines: w.machine ? [w.machine] : [] };
      if(w.consignes) postBody.consignes = w.consignes;
      await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/ops', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(postBody),
      });
    }
  }
  // Ops à supprimer (current mais pas wanted)
  for(const [k, op] of currentByKey){
    if(!wantedKeys.has(k)){
      await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/ops/' + op.id, {
        method:'DELETE', credentials:'include',
      });
    }
  }
  // v185 : PATCH consignes sur les rows existantes si elles ont changé
  //   (les rows nouvellement POST ont déjà les consignes intégrées ci-dessus)
  const currentConsignesByKey = new Map();
  for(const op of currentOps){
    const machine = (Array.isArray(op.machines) && op.machines.length) ? op.machines[0] : null;
    currentConsignesByKey.set(keyOf(op.code, machine), { opId: op.id, consignes: (op.consignes || '').trim() });
  }
  for(const w of wantedExploded){
    const k = keyOf(w.code, w.machine);
    const cur = currentConsignesByKey.get(k);
    if(!cur) continue;  // sera ajouté au prochain sync (ligne nouvelle)
    const wantedConsignes = (w.consignes || '').trim();
    if(wantedConsignes !== cur.consignes){
      await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/ops/' + cur.opId, {
        method:'PATCH', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ consignes: wantedConsignes }),
      });
    }
  }

  // Operators
  const currentOperators = ev.operators || [];
  const wantedOpIdsSet = new Set(wantedOperatorIds.map(Number));
  const currentOpIdsSet = new Set(currentOperators.map(o => o.id));
  for(const oid of wantedOperatorIds){
    if(!currentOpIdsSet.has(oid)){
      await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/operators', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ operator_id: oid }),
      });
    }
  }
  for(const op of currentOperators){
    if(!wantedOpIdsSet.has(op.id)){
      await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/operators/' + op.id, {
        method:'DELETE', credentials:'include',
      });
    }
  }
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
// État d'édition : id de l'opération en cours de modification, sinon null.
let _opsEditingId = null;

function openOpsModal(editId){
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
  // Si on est en mode édition, récupère l'opération existante.
  let editing = null;
  if(editId){
    editing = OPS_STATE.list.find(o => String(o.id) === String(editId));
    if(!editing){
      showToast('Opération introuvable.', 'danger');
      return;
    }
  }
  _opsEditingId = editing ? editing.id : null;

  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  refreshOpsTypeSelect();
  // v182 fix : pour un libre, on injecte son titre comme option syntetique
  // dans le dropdown Type afin que la validation passe (defensif : try/catch).
  try{
    const typeSel = document.getElementById('ops-type');
    if(editing && editing._libre && editing.type && typeSel){
      const has = Array.from(typeSel.options).some(o => o.value === editing.type);
      if(!has){
        const opt = document.createElement('option');
        opt.value = editing.type;
        opt.textContent = editing.type + ' (Libre)';
        try{ opt.dataset.libreSynth = '1'; }catch(e){}
        typeSel.appendChild(opt);
      }
    }
  }catch(e){ console.warn('[openOpsModal libre synth]', e); }
  // Titre & label bouton selon le mode (édition vs création)
  const titleEl = document.getElementById('ops-modal-title');
  if(titleEl) titleEl.textContent = editing ? 'Modifier l\'opération' : 'Nouvelle opération';
  const submitBtn = document.querySelector('#ops-form button[type="submit"]');
  if(submitBtn){
    const labelSpan = submitBtn.querySelector('span') || submitBtn;
    // Préserve l'icône SVG : on cible juste le texte
    submitBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' +
      (editing ? ' Enregistrer les modifications' : ' Enregistrer l\'opération');
  }
  const nameEl = document.getElementById('ops-saisi-par-name');
  if(nameEl) nameEl.textContent = editing ? (editing.operateur || currentUserName()) : currentUserName();
  // Pré-remplit la date (mode édition = date saisie ; mode création = maintenant)
  const dateEl = document.getElementById('ops-date');
  if(dateEl){
    const pad = n => (n < 10 ? '0' + n : '' + n);
    const sourceDate = editing && editing.date_saisie ? new Date(editing.date_saisie) : new Date();
    if(!isNaN(sourceDate.getTime())){
      dateEl.value = sourceDate.getFullYear() + '-' + pad(sourceDate.getMonth()+1) + '-' + pad(sourceDate.getDate())
                   + 'T' + pad(sourceDate.getHours()) + ':' + pad(sourceDate.getMinutes());
    }
  }
  // Pré-remplit machine / type / durée / commentaire en mode édition
  const machineEl = document.getElementById('ops-machine');
  const typeEl = document.getElementById('ops-type');
  const dureeEl = document.getElementById('ops-duree');
  const commentEl = document.getElementById('ops-comment');
  if(editing){
    if(machineEl) machineEl.value = editing.machine || '';
    if(typeEl) typeEl.value = editing.type || '';
    if(dureeEl) dureeEl.value = (editing.duree_reelle_min != null && editing.duree_reelle_min !== '') ? editing.duree_reelle_min : '';
    if(commentEl) commentEl.value = editing.commentaire || '';
  } else {
    if(machineEl) machineEl.value = '';
    if(typeEl) typeEl.value = '';
    if(dureeEl) dureeEl.value = '';
    if(commentEl) commentEl.value = '';
  }
  setTimeout(() => { const f = document.getElementById('ops-machine'); if(f) f.focus(); }, 50);
}
function closeOpsModal(){
  const m = document.getElementById('ops-modal');
  if(!m) return;
  _opsEditingId = null;
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

// Cache des items DB history — préservé entre appels loadOps() pour éviter
// que renderMaintCards() (qui rappelle loadOps en début) écrase l'état DB
// à chaque render → cards restaient à "Jamais" en boucle stérile.
let _OPS_HISTORY_DB_CACHE = [];
let _OPS_HISTORY_LAST_FETCH = 0;
const _OPS_HISTORY_TTL_MS = 15000;  // Recharge la DB toutes les 15s max
let _OPS_HISTORY_FETCHING = false;

function _rebuildOpsStateFromCaches(){
  // v2.2.8 : DB = seule source de vérité. Le merge localStorage est désactivé
  //   car les items pré-DB apparaissaient comme des saisies fantômes qui ne
  //   survivaient jamais au resync. La localStorage est purgée silencieusement
  //   à la première reconstruction pour laisser le navigateur propre.
  const seen = new Set();
  const key = it => (it.machine || '') + '|' + (it.type || '') + '|' + (it.date_saisie || '');
  const merged = [];
  for(const it of _OPS_HISTORY_DB_CACHE){
    const k = key(it);
    if(seen.has(k)) continue;
    seen.add(k);
    merged.push(it);
  }
  // Purge one-shot du localStorage legacy (une seule fois par session)
  if(!window._opsLegacyPurged){
    try{
      const raw = localStorage.getItem(OPS_STORAGE_KEY);
      if(raw){
        const arr = JSON.parse(raw);
        if(Array.isArray(arr) && arr.length){
          localStorage.removeItem(OPS_STORAGE_KEY);
          console.info('[MyMaintenance v2.2.8] localStorage legacy purgé (' + arr.length + ' items) — la DB est désormais la seule source de vérité.');
        }
      }
    }catch(e){}
    window._opsLegacyPurged = true;
  }
  OPS_STATE.list = merged;
}

function loadOps(){
  // 1. Reconstruit synchro OPS_STATE.list à partir des caches (DB + localStorage).
  //    Les items DB sont préservés entre appels — pas de reset à [] qui cassait
  //    la boucle render → loadOps → render.
  _rebuildOpsStateFromCaches();

  // 2. Si le cache DB est encore chaud, on ne re-fetch pas (évite les rafales
  //    de requêtes quand renderMaintCards enchaîne les loadOps).
  if(_OPS_HISTORY_FETCHING) return;
  if(Date.now() - _OPS_HISTORY_LAST_FETCH < _OPS_HISTORY_TTL_MS && _OPS_HISTORY_DB_CACHE.length){
    return;
  }

  // 3. Fetch history DB (async, une fois par TTL).
  _OPS_HISTORY_FETCHING = true;
  fetchHistoryFromDb().then(dbItems => {
    _OPS_HISTORY_FETCHING = false;
    _OPS_HISTORY_LAST_FETCH = Date.now();
    if(!Array.isArray(dbItems)) return;
    _OPS_HISTORY_DB_CACHE = dbItems;
    _rebuildOpsStateFromCaches();
    // Rerender toutes les vues qui dérivent de OPS_STATE.list.
    if(typeof renderOps === 'function') renderOps();
    if(typeof renderMaintCards === 'function') renderMaintCards();
    if(typeof renderOpsTypes === 'function') renderOpsTypes();
    if(typeof renderCtrlTypes === 'function') renderCtrlTypes();
  }).catch(() => { _OPS_HISTORY_FETCHING = false; });
}

// Bypass du cache — utilisé après une saisie/suppression pour rafraîchir tout de suite.
function refreshOpsHistoryNow(){
  _OPS_HISTORY_LAST_FETCH = 0;
  // v2.5.7 : le métrage parcouru des pièces d'usure est calculé côté serveur À
  // PARTIR de la date de dernière intervention. Une saisie change cette date :
  // sans invalidation ici, le métrage affiché resterait celui calculé depuis
  // l'intervention précédente.
  if(typeof _invalidateWearPartCache === 'function') _invalidateWearPartCache();
  loadOps();
}

async function fetchHistoryFromDb(){
  try{
    const r = await fetch('/api/maintenance/history?_=' + Date.now(),
                          { credentials:'include', cache:'no-store' });
    if(!r.ok) return [];
    const d = await r.json();
    // Normalise au format OPS_STATE (machine, operateur, type, date_saisie, commentaire, id, _source)
    return (d.history || []).map(h => ({
      id: 'db-' + h.op_id,
      machine: h.machine || '',
      operateur: h.operateur || '',
      type: h.type || '',
      commentaire: h.commentaire || '',
      consignes: h.consignes || '',
      date_saisie: h.date_saisie || '',
      duree_reelle_min: h.duree_reelle_min || null,
      _source: 'db',
      _event_id: h.event_id,
      _op_id: h.op_id,
      _code: h.code,
      _libre: !!h.libre,
      // v2 : contexte enrichi pour modal détails (double-clic)
      _event_nom: h.event_nom || '',
      _event_heure_debut: h.event_heure_debut || '',
      _event_heure_fin: h.event_heure_fin || '',
      _event_date_prevue: h.date_prevue || '',
      _event_source: h.source || '',
      _event_created_at: h.event_created_at || '',
      _done_at: h.done_at || '',
      _done_by: h.done_by || null,
      _done_by_nom: h.done_by_nom || '',
      _updated_at: h.updated_at || '',
      _updated_by: h.updated_by || null,
      _updated_by_nom: h.updated_by_nom || '',
      _created_by: h.created_by || null,
      _created_by_nom: h.created_by_nom || '',
      _pieces_changees: h.pieces_changees || '',
    }));
  }catch(e){ return []; }
}
function saveOps(){
  // v2.2.8 : no-op. La DB est la seule source, plus de miroir localStorage.
  //   Fonction gardée en no-op pour ne pas casser d'appels legacy.
}
function addOperation(e){
  e.preventDefault();
  const machine = (document.getElementById('ops-machine').value || '').trim();
  const type = (document.getElementById('ops-type').value || '').trim();
  const commentaire = (document.getElementById('ops-comment').value || '').trim();
  // v2.2.14 : durée réelle (optionnelle) — number en minutes
  const dureeStr = (document.getElementById('ops-duree')?.value || '').trim();
  const dureeMin = dureeStr === '' ? null : parseInt(dureeStr, 10);
  if(dureeStr !== '' && (Number.isNaN(dureeMin) || dureeMin < 0)){
    showToast('Durée invalide (entier positif attendu).', 'danger');
    return;
  }
  const operateur = currentUserName();
  if(!operateur){ showToast('Identité non chargée. Réessayez dans un instant.', 'danger'); return; }
  if(!machine || !type){ showToast('Machine et type sont requis.', 'danger'); return; }
  // Date d'opération : input datetime-local. Si vide ou invalide, fallback maintenant.
  const dateInput = (document.getElementById('ops-date')?.value || '').trim();
  let dateSaisie = new Date().toISOString();
  if(dateInput){
    const parsed = new Date(dateInput);
    if(!isNaN(parsed.getTime())) dateSaisie = parsed.toISOString();
  }
  // Mode édition : remplace l'opération existante en conservant son id et son
  // opérateur d'origine (date_modification est ajoutée pour traçabilité locale).
  // Mode création : push une nouvelle opération.
  const isEdit = !!_opsEditingId;
  if(isEdit){
    const idx = OPS_STATE.list.findIndex(o => String(o.id) === String(_opsEditingId));
    if(idx === -1){
      showToast('Opération introuvable — peut-être supprimée entre-temps.', 'danger');
      return;
    }
    const original = OPS_STATE.list[idx];
    // v2.2.6 : toute row d'origine DB (libre OU catalogue) est persistée en
    // DB via _dbEditPersist. Avant : seuls les libres l'étaient, les catalogue
    // updataient uniquement localStorage (donc disparaissaient au refresh).
    if(original._source === 'db' && original._event_id && original._op_id && original._code){
      _dbEditPersist(original, {machine, titre: type, commentaire, dateSaisie, dureeMin})
        .then(() => {
          closeOpsModal();
          showToast(original._libre ? 'Intervention libre mise à jour.' : 'Opération mise à jour.', 'success');
          if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
          else if(typeof loadOps === 'function') loadOps();
        })
        .catch(err => {
          const msg = (err && err.message) ? err.message : 'PATCH échoué';
          showToast('Erreur : ' + msg, 'danger');
        });
      return;
    }
    OPS_STATE.list[idx] = Object.assign({}, original, {
      machine, type, commentaire,
      duree_reelle_min: dureeMin,
      date_saisie: dateSaisie,
      date_modification: new Date().toISOString(),
      modifie_par: operateur,
    });
  } else {
    // v2.2.7 : CREATE persistée en DB (avant : localStorage-only → saisies
    //   perdues au resync nightly, ne remontent pas entre navigateurs).
    //   Le catalog dropdown utilise le LABEL comme value → lookup du code
    //   via OPS_TYPES_STATE. Puis POST /events + PATCH termine (même flow
    //   que libreSubmit).
    const opTypeEntry = (OPS_TYPES_STATE.list || []).find(t => t.nom === type);
    if(!opTypeEntry){
      showToast("Type d'opération introuvable dans le catalogue : " + type, 'danger');
      return;
    }
    const code = opTypeEntry.id;
    // Conversion date_saisie (ISO datetime) → date_prevue (YYYY-MM-DD)
    //   et done_at (ISO Paris local YYYY-MM-DDTHH:MM:SS).
    let datePrevue, doneAtIso;
    try{
      const d = new Date(dateSaisie);
      const pad = n => n < 10 ? '0' + n : '' + n;
      datePrevue = d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate());
      doneAtIso = datePrevue + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    }catch(e){
      datePrevue = _fmtDateISO(new Date());
    }
    (async () => {
      try{
        // 1. POST /events → crée un event non_planifie avec 1 op statut=a_faire
        const rEv = await fetch('/api/maintenance/events', {
          method:'POST', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({
            machine,
            date_prevue: datePrevue,
            source: 'non_planifie',
            ops: [code],
            operators: [],
          }),
        });
        if(!rEv.ok){
          const err = await rEv.json().catch(()=>({}));
          if(rEv.status === 502 || rEv.status === 503){
            throw new Error('Serveur temporairement indisponible, réessaye dans un instant.');
          }
          throw new Error(err.detail || 'Création event échouée (HTTP ' + rEv.status + ')');
        }
        const data = await rEv.json();
        const ev = data.event;
        const op = (ev.ops || [])[0];
        if(!ev || !op) throw new Error('Créneau incomplet retourné par l\'API');
        // 2. PATCH op → statut termine + observations + done_at (l'admin
        //    choisit la date/heure exacte de saisie).
        const patchBody = { statut: 'termine' };
        if(commentaire) patchBody.observations = commentaire;
        if(doneAtIso) patchBody.done_at = doneAtIso;
        if(dureeMin != null && !Number.isNaN(dureeMin)) patchBody.duree_reelle_min = dureeMin;
        const rOp = await fetch('/api/maintenance/events/' + ev.id + '/ops/' + op.id, {
          method:'PATCH', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(patchBody),
        });
        if(!rOp.ok){
          const err = await rOp.json().catch(()=>({}));
          throw new Error(err.detail || 'PATCH termine échoué (HTTP ' + rOp.status + ')');
        }
        showToast('Opération enregistrée en base.', 'success');
        closeOpsModal();
        // Aligne les sélecteurs machine pour cohérence
        try{ localStorage.setItem(OPS_CAT_MACHINE_KEY, machine); }catch(e){}
        try{ localStorage.setItem(MAINT_MACHINE_KEY, machine); }catch(e){}
        // Refresh depuis backend (bypass cache)
        if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
        else if(typeof loadOps === 'function') loadOps();
        if(typeof renderOpsTypes === 'function') renderOpsTypes();
        if(typeof renderMaintCards === 'function') renderMaintCards();
      }catch(e){
        showToast('Erreur : ' + e.message, 'danger');
      }
    })();
    return;
  }
  saveOps();
  renderOps();
  try{ localStorage.setItem(OPS_CAT_MACHINE_KEY, machine); }catch(e){}
  try{ localStorage.setItem(MAINT_MACHINE_KEY, machine); }catch(e){}
  if(typeof renderOpsTypes === 'function') renderOpsTypes();
  if(typeof renderMaintCards === 'function') renderMaintCards();
  closeOpsModal();
  showToast('Opération mise à jour.', 'info');
}
// v182 fix + v2.2.6 : persistance backend pour toute édition depuis l'historique
// (libre ET catalogue). Enchaîne :
//   1. PATCH /libres/{code} (titre) — uniquement pour les libres, skip si standard
//   2. PATCH /events/{event_id} (date + machine)
//   3. PATCH /events/{event_id}/ops/{op_id} (commentaire + done_at)
async function _dbEditPersist(original, changes){
  const eventId = original._event_id;
  const opId = original._op_id;
  const code = original._code;
  const isLibre = !!original._libre;
  const jsonHeaders = {'Content-Type':'application/json'};

  const _throwFromResp = async (r, defaultMsg) => {
    // v2.2.6 : messages plus clairs selon le status
    if(r.status === 502 || r.status === 503){
      throw new Error('Serveur temporairement indisponible (' + r.status + '), réessaye dans un instant.');
    }
    let err = {};
    try{ err = await r.json(); }catch(e){}
    throw new Error(err.detail || (defaultMsg + ' (HTTP ' + r.status + ')'));
  };

  // 1. Rename titre si libre + change effectif — skip si le nouveau titre
  // correspond à un code standard du catalogue.
  const newTitle = (changes.titre || '').trim();
  if(isLibre){
    const isStandardCode = (typeof OPS_TYPES_STATE === 'object' && Array.isArray(OPS_TYPES_STATE.list))
      ? OPS_TYPES_STATE.list.some(t => (t.nom || '') === newTitle)
      : false;
    if(newTitle && newTitle !== (original.type || '') && !isStandardCode){
      const r = await fetch('/api/maintenance/codes/libres/' + encodeURIComponent(code), {
        method:'PATCH', credentials:'include', headers: jsonHeaders,
        body: JSON.stringify({label: newTitle}),
      });
      if(!r.ok) await _throwFromResp(r, 'Renommage échoué');
    }
    // v2.5.13 : si le titre choisi correspond a un code du catalogue, ce n'est
    // pas un renommage mais un reclassement — traite plus bas via codeChange.
  }
  // v2.5.13 : le type EST modifiable depuis l'historique pour l'admin. La
  // saisie est deplacee vers le code choisi (PATCH op {code}) — utile quand un
  // operateur s'est trompe de ligne dans le catalogue. Avant, le changement
  // etait silencieusement ignore avec un simple avertissement.
  let codeChange = null;
  if(newTitle && newTitle !== (original.type || '')){
    const entry = (typeof OPS_TYPES_STATE === 'object' && Array.isArray(OPS_TYPES_STATE.list))
      ? OPS_TYPES_STATE.list.find(t => (t.nom || '') === newTitle)
      : null;
    if(entry && String(entry.id) !== String(code)){
      if(MAINT_ROLE === 'admin') codeChange = String(entry.id);
      else if(typeof showToast === 'function') showToast('Seul un admin peut changer le type d\'une opération.', 'warn');
    }
  }
  // 2. PATCH event : date + machine
  const evPatch = {};
  const newMachine = (changes.machine || '').trim();
  if(newMachine && newMachine !== (original.machine || '')) evPatch.machine = newMachine;
  // date_saisie est ISO datetime, event.date_prevue est YYYY-MM-DD → conversion
  const newDateIso = changes.dateSaisie;
  if(newDateIso){
    try{
      const d = new Date(newDateIso);
      if(!isNaN(d.getTime())){
        const pad = n => (n < 10 ? '0'+n : ''+n);
        const iso = d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate());
        // v2.5.13 fix : n'envoyer date_prevue QUE si la date a change. Avant,
        // elle partait systematiquement — et le garde-fou 'creneau passe' du
        // backend renvoyait 403 des que la saisie datait de la veille, ce qui
        // bloquait aussi la modification du commentaire ou de la duree.
        const evDate = (original._event_date_prevue || (original.date_saisie || '').slice(0, 10));
        if(iso !== evDate) evPatch.date_prevue = iso;
      }
    }catch(e){}
  }
  if(Object.keys(evPatch).length){
    const r2 = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId), {
      method:'PATCH', credentials:'include', headers: jsonHeaders,
      body: JSON.stringify(evPatch),
    });
    if(!r2.ok) await _throwFromResp(r2, 'PATCH event échoué');
  }
  // 3. PATCH op : commentaire (observations) + done_at (v2.2.5).
  //    Fix : la date_saisie affichée dans l'historique = done_at || date_prevue.
  //    Comme les libres sont marqués termine à la création, done_at est set →
  //    modifier seulement date_prevue est invisible. On PATCH aussi done_at.
  const newComment = (changes.commentaire || '').trim();
  const opPatch = {};
  if(newComment !== (original.commentaire || '')){
    opPatch.observations = newComment;
  }
  // v2.2.14 : durée réelle — permet à l'admin d'ajuster la durée après coup
  if(changes.dureeMin !== undefined){
    const newDuree = changes.dureeMin;
    const oldDuree = (original.duree_reelle_min != null && original.duree_reelle_min !== '') ? parseInt(original.duree_reelle_min, 10) : null;
    // Compare en null-safe : null vs '' vs number
    const changed = (newDuree === null && oldDuree !== null) ||
                    (newDuree !== null && newDuree !== oldDuree);
    if(changed){
      opPatch.duree_reelle_min = newDuree;
    }
  }
  if(newDateIso){
    // Convertit en ISO Paris (YYYY-MM-DDTHH:MM:SS local) — même format que
    // _now_paris_iso() côté backend.
    try{
      const d = new Date(newDateIso);
      if(!isNaN(d.getTime())){
        const pad = n => (n < 10 ? '0' + n : '' + n);
        const doneAtLocal = d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) +
          'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
        // Compare avec done_at déjà en DB : la trace originale reflète la
        // date_saisie affichée (done_at || date_prevue). On skip le PATCH si
        // pas de changement effectif.
        const originalDoneAt = (original._done_at || original.date_saisie || '').slice(0, 19);
        if(doneAtLocal !== originalDoneAt){
          opPatch.done_at = doneAtLocal;
        }
      }
    }catch(e){}
  }
  if(codeChange) opPatch.code = codeChange;
  if(Object.keys(opPatch).length){
    const r3 = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/ops/' + encodeURIComponent(opId), {
      method:'PATCH', credentials:'include', headers: jsonHeaders,
      body: JSON.stringify(opPatch),
    });
    if(!r3.ok) await _throwFromResp(r3, 'PATCH op échoué');
  }
}
// Alias pour compat éventuelle avec anciens callers
const _libreEditPersist = _dbEditPersist;

// v2 : modal read-only "Détails de l'opération" (double-clic sur ligne historique)
function openOpsHistoryDetail(id){
  const o = (OPS_STATE.list || []).find(x => String(x.id) === String(id));
  if(!o){ if(typeof showToast === 'function') showToast('Ligne introuvable.', 'danger'); return; }
  const overlay = document.createElement('div');
  overlay.className = 'op-modal-overlay active';
  overlay.style.zIndex = '1600';
  overlay.onclick = (e) => { if(e.target === overlay) overlay.remove(); };

  const isLibre = !!o._libre;
  const isPlanifie = o._event_source === 'planifie';
  const chipLibre = isLibre ? '<span class="libre-chip">Libre</span>' : '';

  // Consignes admin — bloc accent (cyan)
  const consignesBlock = (o.consignes || '').trim()
    ? '<div class="ops-detail-block ops-detail-block--consignes">' +
        '<div class="ops-detail-block-head">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>' +
          '<span>Consignes de l\'admin</span>' +
        '</div>' +
        '<div class="ops-detail-block-body">' + escHtml(o.consignes) + '</div>' +
      '</div>'
    : '';

  // Commentaires opérateur — bloc warn (jaune-orangé)
  const commentBlock = (o.commentaire || '').trim()
    ? '<div class="ops-detail-block ops-detail-block--comment">' +
        '<div class="ops-detail-block-head">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' +
          '<span>Commentaires de l\'opérateur</span>' +
        '</div>' +
        '<div class="ops-detail-block-body">' + escHtml(o.commentaire) + '</div>' +
      '</div>'
    : '';

  // Pièces changées — bloc violet (legacy)
  const piecesBlock = (o._pieces_changees || '').trim()
    ? '<div class="ops-detail-block ops-detail-block--pieces">' +
        '<div class="ops-detail-block-head">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>' +
          '<span>Pièces changées</span>' +
        '</div>' +
        '<div class="ops-detail-block-body">' + escHtml(o._pieces_changees) + '</div>' +
      '</div>'
    : '';

  // Ligne récap principale
  const dureeStr = (o.duree_reelle_min != null && o.duree_reelle_min !== '')
    ? escHtml(o.duree_reelle_min + ' min')
    : '<span style="color:var(--muted)">Non renseignée</span>';

  overlay.innerHTML =
    '<div class="modal-card ops-detail-modal" role="dialog" aria-modal="true" style="max-width:560px;width:92vw">' +
      '<div class="modal-head">' +
        '<div class="modal-title">Détails de l\'opération</div>' +
        '<button type="button" class="modal-close" aria-label="Fermer" onclick="this.closest(\'.op-modal-overlay\').remove()">' +
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="modal-body">' +
        '<div class="ops-detail-hero">' +
          '<div class="ops-detail-hero-icon">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>' +
          '</div>' +
          '<div class="ops-detail-hero-body">' +
            '<div class="ops-detail-title">' + escHtml(o.type || '—') + '</div>' +
            (chipLibre ? '<div class="ops-detail-hero-chips">' + chipLibre + '</div>' : '') +
          '</div>' +
        '</div>' +
        '<div class="ops-detail-grid">' +
          '<div class="ops-detail-cell"><span class="ops-detail-cell-label">Date de saisie</span><span class="ops-detail-cell-value">' + escHtml(fmtDate(o.date_saisie)) + '</span></div>' +
          '<div class="ops-detail-cell"><span class="ops-detail-cell-label">Machine</span><span class="ops-detail-cell-value">' + escHtml(o.machine || '—') + '</span></div>' +
          '<div class="ops-detail-cell"><span class="ops-detail-cell-label">Opérateur</span><span class="ops-detail-cell-value">' + escHtml(o.operateur || '—') + '</span></div>' +
          '<div class="ops-detail-cell"><span class="ops-detail-cell-label">Durée réelle</span><span class="ops-detail-cell-value">' + dureeStr + '</span></div>' +
        '</div>' +
        consignesBlock +
        commentBlock +
        piecesBlock +
      '</div>' +
      '<div class="modal-foot">' +
        '<button type="button" class="modal-btn-ghost" onclick="this.closest(\'.op-modal-overlay\').remove()">Fermer</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(overlay);
}

// v2.5.10 : suppression d'une ligne d'historique.
//   - Non_planifie (op ponctuelle enregistree hors creneau) : hard delete direct,
//     comportement historique (rien a preserver, l'op nait et meurt en 1 ligne).
//   - Planifie (op saisie lors d'un creneau) : modal avec 2 choix pour eviter la
//     cascade destructive (creneau vide + tache operateur disparue). Choix :
//        1. Invalider la saisie (statut=invalidee) : l'op reste sur le creneau,
//           grisee, ne compte plus, disparait de l'historique et de Mes taches.
//        2. Supprimer entierement (comportement historique, warning explicite).
async function deleteOp(id){
  const item = (OPS_STATE.list || []).find(o => o.id === id);
  if(!item){ if(typeof showToast === 'function') showToast('Ligne introuvable.', 'danger'); return; }
  // Non_planifie ou pas encore persiste en DB -> modale stylisee (pas d'invalidation
  // possible pour une op ponctuelle : elle n'existe pas dans un creneau, y a rien a preserver).
  if(item._source !== 'db' || item._event_source === 'non_planifie'){
    const summary =
      '<div style="font-size:14px;font-weight:700;color:var(--text)">' + escHtml(item.type || '\u2014') + '</div>' +
      '<div style="font-size:12px;color:var(--muted);margin-top:4px">' +
        escHtml(item.machine || '') + (item.date_saisie ? ' \u00b7 ' + escHtml(_fmtDateFRHistoric(item.date_saisie)) : '') +
        (item.operateur ? ' \u00b7 par ' + escHtml(item.operateur) : '') +
      '</div>';
    _openHistoryDeleteModal({
      title: 'Supprimer cette saisie ?',
      summary: summary,
      warning: 'Cette op\u00e9ration a \u00e9t\u00e9 enregistr\u00e9e hors cr\u00e9neau planifi\u00e9. Sa suppression est <strong>d\u00e9finitive</strong> et n\'affecte aucune t\u00e2che planifi\u00e9e.',
      confirmLabel: 'Supprimer',
      onConfirm: () => _hardDeleteOpFromHistory(item),
    });
    return;
  }
  // Planifie : offre le choix Invalider / Supprimer entierement.
  _openInvalidateOrDeleteOpModal(item);
}

function _openInvalidateOrDeleteOpModal(item){
  const existing = document.getElementById('inv-op-modal-overlay');
  if(existing) existing.remove();
  const wrap = document.createElement('div');
  wrap.id = 'inv-op-modal-overlay';
  wrap.className = 'op-modal-overlay';
  wrap.style.cssText = 'display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center';
  wrap.addEventListener('click', (e) => { if(e.target === wrap) _closeInvalidateOrDeleteOpModal(); });
  const escHandler = (e) => { if(e.key === 'Escape'){ e.preventDefault(); _closeInvalidateOrDeleteOpModal(); } };
  document.addEventListener('keydown', escHandler, true);
  wrap._escHandler = escHandler;

  const machine = escHtml(item.machine || '');
  const type = escHtml(item.type || '');
  const dateFR = escHtml(_fmtDateFRHistoric(item.date_saisie) || '');
  const doneBy = escHtml(item.operateur || '');

  wrap.innerHTML = ''
    + '<div class="op-modal" role="dialog" aria-modal="true" style="max-width:560px;width:calc(100% - 40px);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,0.4)">'
    +   '<div style="color:var(--text);font-size:16px;font-weight:700;margin-bottom:6px">Que faire de cette saisie ?</div>'
    +   '<div style="font-size:12px;color:var(--muted);margin-bottom:14px">Cette op\u00e9ration a \u00e9t\u00e9 saisie lors d\'un cr\u00e9neau planifi\u00e9. La suppression entraine des effets sur le cr\u00e9neau et l\'op\u00e9rateur.</div>'
    +   '<div style="padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:16px;font-size:13px">'
    +     '<div style="font-weight:700;color:var(--text)">' + type + '</div>'
    +     '<div style="color:var(--muted);margin-top:4px">' + machine + (dateFR ? ' \u00b7 ' + dateFR : '') + (doneBy ? ' \u00b7 par ' + doneBy : '') + '</div>'
    +   '</div>'
    +   '<div style="display:flex;flex-direction:column;gap:10px">'
    +     '<button type="button" id="inv-op-invalidate-btn" style="padding:14px 16px;text-align:left;border-radius:10px;border:1.5px solid var(--warn,#f59e0b);background:rgba(245,158,11,0.08);color:var(--text);cursor:pointer;font-family:inherit">'
    +       '<div style="font-weight:700;font-size:14px;color:var(--warn,#f59e0b)">Invalider la saisie <span style="font-weight:600;font-size:11px;color:var(--muted);letter-spacing:.3px;text-transform:uppercase;margin-left:6px">recommand\u00e9</span></div>'
    +       '<div style="font-size:12px;color:var(--text2);margin-top:6px;line-height:1.5">La saisie dispara\u00eet de l\'historique et de Mes t\u00e2ches. Le cr\u00e9neau conserve la ligne, gris\u00e9e avec badge \u00ab Invalid\u00e9e \u00bb (tra\u00e7abilit\u00e9 : qui/quand).</div>'
    +     '</button>'
    +     '<button type="button" id="inv-op-delete-btn" style="padding:14px 16px;text-align:left;border-radius:10px;border:1.5px solid var(--danger);background:rgba(248,113,113,0.08);color:var(--text);cursor:pointer;font-family:inherit">'
    +       '<div style="font-weight:700;font-size:14px;color:var(--danger)">Supprimer enti\u00e8rement</div>'
    +       '<div style="font-size:12px;color:var(--text2);margin-top:6px;line-height:1.5">Retire la ligne partout : historique, cr\u00e9neau (peut se retrouver vide), Mes t\u00e2ches de l\'op\u00e9rateur. Irr\u00e9versible.</div>'
    +     '</button>'
    +   '</div>'
    +   '<div style="display:flex;justify-content:flex-end;margin-top:16px">'
    +     '<button type="button" id="inv-op-cancel-btn" style="background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>'
    +   '</div>'
    + '</div>';

  document.body.appendChild(wrap);
  const invBtn = document.getElementById('inv-op-invalidate-btn');
  const delBtn = document.getElementById('inv-op-delete-btn');
  const cancelBtn = document.getElementById('inv-op-cancel-btn');
  if(cancelBtn) cancelBtn.addEventListener('click', _closeInvalidateOrDeleteOpModal);
  if(invBtn) invBtn.addEventListener('click', () => {
    if(invBtn.dataset._busy === '1') return;
    invBtn.dataset._busy = '1'; invBtn.disabled = true; if(delBtn) delBtn.disabled = true;
    _doInvalidateOpFromHistory(item, invBtn);
  });
  if(delBtn) delBtn.addEventListener('click', () => {
    if(delBtn.dataset._busy === '1') return;
    delBtn.dataset._busy = '1'; delBtn.disabled = true; if(invBtn) invBtn.disabled = true;
    _doHardDeleteFromModal(item, delBtn);
  });
  requestAnimationFrame(() => { if(invBtn) invBtn.focus(); });
}

function _closeInvalidateOrDeleteOpModal(){
  const w = document.getElementById('inv-op-modal-overlay');
  if(!w) return;
  try{ if(w._escHandler) document.removeEventListener('keydown', w._escHandler, true); }catch(_){}
  w.remove();
}

function _fmtDateFRHistoric(iso){
  if(!iso) return '';
  try{
    const d = new Date(iso);
    if(isNaN(d.getTime())) return '';
    return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth()+1)).slice(-2) + '/' + d.getFullYear();
  }catch(e){ return ''; }
}

async function _doInvalidateOpFromHistory(item, btn){
  try{
    const url = '/api/maintenance/events/' + encodeURIComponent(item._event_id) +
                '/ops/' + encodeURIComponent(item._op_id) + '/invalidate';
    const r = await fetch(url, { method: 'POST', credentials: 'include' });
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      throw new Error(err.detail || ('Invalidation refus\u00e9e (' + r.status + ')'));
    }
    if(Array.isArray(_OPS_HISTORY_DB_CACHE)){
      _OPS_HISTORY_DB_CACHE = _OPS_HISTORY_DB_CACHE.filter(x => x.id !== item.id);
    }
    OPS_STATE.list = OPS_STATE.list.filter(o => o.id !== item.id);
    renderOps();
    if(typeof showToast === 'function') showToast('Saisie invalid\u00e9e. Le cr\u00e9neau conserve la ligne.', 'info');
    _closeInvalidateOrDeleteOpModal();
    // Rafraichit le planning + Mes taches pour refleter le nouveau statut.
    if(typeof refreshPlanning === 'function') refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
    if(typeof opLoadTasks === 'function') opLoadTasks().catch(() => {});
    if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
    if(btn){ btn.dataset._busy = ''; btn.disabled = false; }
    const other = document.getElementById('inv-op-delete-btn');
    if(other) other.disabled = false;
  }
}

async function _doHardDeleteFromModal(item, btn){
  try{
    await _hardDeleteOpFromHistory(item);
    _closeInvalidateOrDeleteOpModal();
  }catch(e){
    if(btn){ btn.dataset._busy = ''; btn.disabled = false; }
    const other = document.getElementById('inv-op-invalidate-btn');
    if(other) other.disabled = false;
  }
}

// v2.5.12 : modale generique de confirmation de suppression pour toute ligne
// d'historique (ops, alertes, controles). Style aligne sur _openDeleteCaseModal.
// opts : { title, summary (HTML), warning (HTML), confirmLabel, onConfirm() }
function _openHistoryDeleteModal(opts){
  opts = opts || {};
  const existing = document.getElementById('hist-del-modal-overlay');
  if(existing) existing.remove();
  const wrap = document.createElement('div');
  wrap.id = 'hist-del-modal-overlay';
  wrap.className = 'op-modal-overlay';
  wrap.style.cssText = 'display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center';
  wrap.addEventListener('click', (e) => { if(e.target === wrap) _closeHistoryDeleteModal(); });
  const escHandler = (e) => { if(e.key === 'Escape'){ e.preventDefault(); _closeHistoryDeleteModal(); } };
  document.addEventListener('keydown', escHandler, true);
  wrap._escHandler = escHandler;

  const title       = opts.title       || 'Supprimer cette ligne ?';
  const summaryHtml = opts.summary     || '';
  const warningHtml = opts.warning     || '';
  const confirmLabel= opts.confirmLabel|| 'Supprimer';

  wrap.innerHTML = ''
    + '<div class="op-modal" role="dialog" aria-modal="true" style="max-width:520px;width:calc(100% - 40px);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,0.4)">'
    +   '<div style="color:var(--danger);font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px">'
    +     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>'
    +     title
    +   '</div>'
    +   (summaryHtml ? '<div style="padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:14px">' + summaryHtml + '</div>' : '')
    +   (warningHtml ? '<div style="font-size:13px;color:var(--text);line-height:1.5;margin-bottom:16px">' + warningHtml + '</div>' : '')
    +   '<div style="display:flex;justify-content:flex-end;gap:10px">'
    +     '<button type="button" id="hist-del-cancel-btn" style="background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>'
    +     '<button type="button" id="hist-del-confirm-btn" style="background:var(--danger);color:#fff;border:none;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">' + escHtml(confirmLabel) + '</button>'
    +   '</div>'
    + '</div>';

  document.body.appendChild(wrap);
  const cancelBtn  = document.getElementById('hist-del-cancel-btn');
  const confirmBtn = document.getElementById('hist-del-confirm-btn');
  if(cancelBtn)  cancelBtn.addEventListener('click', _closeHistoryDeleteModal);
  if(confirmBtn) confirmBtn.addEventListener('click', async () => {
    if(confirmBtn.dataset._busy === '1') return;
    confirmBtn.dataset._busy = '1';
    confirmBtn.disabled = true;
    if(cancelBtn) cancelBtn.disabled = true;
    try{
      if(typeof opts.onConfirm === 'function') await opts.onConfirm();
      _closeHistoryDeleteModal();
    }catch(e){
      confirmBtn.dataset._busy = '';
      confirmBtn.disabled = false;
      if(cancelBtn) cancelBtn.disabled = false;
    }
  });
  requestAnimationFrame(() => { if(cancelBtn) cancelBtn.focus(); });
}

function _closeHistoryDeleteModal(){
  const w = document.getElementById('hist-del-modal-overlay');
  if(!w) return;
  try{ if(w._escHandler) document.removeEventListener('keydown', w._escHandler, true); }catch(_){}
  w.remove();
}

async function _hardDeleteOpFromHistory(item){
  // v2.5.12 : DELETE avec gestion 409 (confirm_token requis quand un event
  // contient des ops termine -- toujours le cas pour un non_planifie puisqu'il
  // EST l'op saisie). On retry automatiquement avec le token retourne.
  if(item._source === 'db' && item._event_id && item._op_id){
    try{
      // Non_planifie = 1 op = 1 event -> DELETE l'event entier.
      // Planifie = creneau partage -> DELETE juste cette op.
      const baseUrl = (item._event_source === 'non_planifie')
        ? '/api/maintenance/events/' + encodeURIComponent(item._event_id)
        : '/api/maintenance/events/' + encodeURIComponent(item._event_id) + '/ops/' + encodeURIComponent(item._op_id);
      let r = await fetch(baseUrl, { method:'DELETE', credentials:'include' });
      if(r.status === 409){
        // Backend nous demande un confirm_token (protection anti-suppression
        // de traces d'ops termine). On l'extrait et on retry -- c'est deja
        // ce que l'admin a explicitement confirme via la modale.
        let payload = null;
        try{ payload = await r.json(); }catch(_){}
        const token = payload && payload.detail && payload.detail.confirm_token;
        if(token){
          const retryUrl = baseUrl + (baseUrl.includes('?') ? '&' : '?') + 'confirm_token=' + encodeURIComponent(token);
          r = await fetch(retryUrl, { method:'DELETE', credentials:'include' });
        }
      }
      if(!r.ok){
        if(r.status === 502 || r.status === 503){
          if(typeof showToast === 'function') showToast('Serveur temporairement indisponible, reessaye dans un instant.', 'danger');
          throw new Error('Serveur indisponible');
        }
        let msg = String(r.status);
        try{
          const err = await r.json();
          if(err && err.detail){
            msg = (typeof err.detail === 'string') ? err.detail : (err.detail.message || JSON.stringify(err.detail));
          }
        }catch(_){}
        if(typeof showToast === 'function') showToast('Erreur suppression : ' + msg, 'danger');
        throw new Error(msg);
      }
      if(Array.isArray(_OPS_HISTORY_DB_CACHE)){
        _OPS_HISTORY_DB_CACHE = _OPS_HISTORY_DB_CACHE.filter(x => x.id !== item.id);
      }
    }catch(e){
      // showToast deja emis a l'interieur -- on relance juste pour signaler.
      throw e;
    }
  }
  OPS_STATE.list = OPS_STATE.list.filter(o => o.id !== item.id);
  renderOps();
  if(typeof showToast === 'function') showToast('Operation supprimee.', 'success');
  if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
  if(typeof refreshPlanning === 'function') refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
  if(typeof opLoadTasks === 'function') opLoadTasks().catch(() => {});
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
    // v180 : filtre "kind" : tous / codes / libres (interventions libres)
    kind:     v('filt-operations-kind') || 'all',
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
    const cur  = typeSel.value;
    // v2.7.1 : le select "Nom de l'opération" liste les codes catalogue ET les
    // interventions libres présentes dans l'historique. Le filtre "Type de
    // saisie" restreint la liste au type sélectionné (codes / libres).
    const kind = (document.getElementById('filt-operations-kind')?.value || 'all');
    const sortFr = arr => arr.sort((a,b) => a.localeCompare(b, 'fr'));
    // Union catalogue + historique, et non le seul catalogue : un code archivé
    // (v2.7.1) sort de OPS_TYPES_STATE mais ses saisies restent dans le tableau.
    // Sans cette union, elles seraient visibles sans être filtrables.
    const codes  = sortFr(Array.from(new Set(
      OPS_TYPES_STATE.list.map(t => t.nom).filter(Boolean).concat(
        OPS_STATE.list.filter(o => !o._libre).map(o => o.type).filter(Boolean)
      )
    )));
    const libres = sortFr(Array.from(new Set(
      OPS_STATE.list.filter(o => o._libre).map(o => o.type).filter(Boolean)
    )));
    const opt = n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>';
    const grp = (label, items) => items.length
      ? '<optgroup label="' + escAttr(label) + '">' + items.map(opt).join('') + '</optgroup>'
      : '';
    let html = '<option value="">Toutes les opérations</option>';
    let allowed = [];
    if(kind === 'codes'){
      html += codes.map(opt).join('');
      allowed = codes;
    } else if(kind === 'libres'){
      html += libres.map(opt).join('');
      allowed = libres;
    } else {
      html += grp('Codes catalogue', codes) + grp('Interventions libres', libres);
      allowed = codes.concat(libres);
    }
    typeSel.innerHTML = html;
    // Si la sélection courante n'existe plus dans le jeu restreint, on repasse
    // sur "Toutes les opérations" plutôt que de laisser un filtre fantôme.
    typeSel.value = (cur && allowed.includes(cur)) ? cur : '';
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
    // v180 : filtre kind (all / codes / libres)
    if(f.kind === 'libres' && !o._libre) return false;
    if(f.kind === 'codes' && o._libre) return false;
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
  // v182 fix bug tri : pour date_saisie, on compare via Date.parse (les
  // valeurs mixent parfois ISO complet et YYYY-MM-DD selon done_at/date_prevue,
  // le sort string donne alors un ordre incorrect).
  filtered.sort((a,b) => {
    if(sf === 'date_saisie'){
      const ta = Date.parse(a[sf] || '') || 0;
      const tb = Date.parse(b[sf] || '') || 0;
      if(ta < tb) return -1*dir;
      if(ta > tb) return  1*dir;
      return 0;
    }
    if(sf === 'duree_reelle_min'){
      const na = a[sf] != null ? Number(a[sf]) : -Infinity;
      const nb = b[sf] != null ? Number(b[sf]) : -Infinity;
      if(na < nb) return -1*dir;
      if(na > nb) return  1*dir;
      return 0;
    }
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
      : 'Aucune opération enregistrée. Cliquez sur « Nouvelle saisie » pour commencer.';
    tbody.innerHTML = '<tr><td colspan="8" class="ops-empty">' + escHtml(msg) + '</td></tr>';
  } else {
    const rows = filtered.map(o => {
      // v185 : consignes admin — truncate visuel + tooltip si long
      const cons = (o.consignes || '').trim();
      const consTd = cons
        ? '<td class="col-consignes" title="' + escAttr(cons) + '">' + escHtml(cons.length > 60 ? cons.slice(0,60) + '…' : cons) + '</td>'
        : '<td class="col-consignes"><span style="color:var(--muted)">—</span></td>';
      // v2 : double-clic sur la ligne → modal détails (comme historique contrôles)
      const dblAttr = o._source === 'db'
        ? ' ondblclick="openOpsHistoryDetail(\'' + escAttr(String(o.id)) + '\')" style="cursor:pointer" title="Double-clic pour voir le détail complet"'
        : '';
      return '<tr' + dblAttr + '>' +
        '<td class="col-date">' + escHtml(fmtDate(o.date_saisie)) + '</td>' +
        '<td>' + escHtml(o.machine) + '</td>' +
        '<td>' + escHtml(o.operateur) + '</td>' +
        '<td>' + escHtml(o.type) + (o._libre ? ' <span class="libre-chip">Libre</span>' : '') + '</td>' +
        '<td class="col-duree">' + (o.duree_reelle_min != null ? escHtml(o.duree_reelle_min + ' min') : '<span style="color:var(--muted)">—</span>') + '</td>' +
        '<td class="col-comment">' + escHtml(o.commentaire || '') + '</td>' +
        consTd +
        '<td class="col-actions">' +
          '<button type="button" class="ops-row-btn edit" onclick="openOpsModal(\'' + escAttr(o.id) + '\')" title="Modifier">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
          '</button>' +
          '<button type="button" class="ops-row-btn del" onclick="deleteOp(\'' + escAttr(o.id) + '\')" title="Supprimer">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          '</button>' +
        '</td>' +
      '</tr>';
    });
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
// Catalogue des types d'opérations — source : Paramètres → Maintenance (DB)
// Filtre : "Interventions" (toutes) + "Contrôles" avec periodique=OUI.
// La "Dernière intervention" est dérivée des saisies réelles (OPS_STATE),
// filtrées par la machine sélectionnée au-dessus du catalogue.
// =========================================================================
const OPS_CAT_MACHINE_KEY = 'mysifa_maint_ops_cat_machine_v1';
const OPS_TYPES_STATE = { sortBy: 'nom', sortDir: 'asc', list: [] };

function getOpsCatMachine(){
  try{ return localStorage.getItem(OPS_CAT_MACHINE_KEY) || 'Cohésio 1'; }
  catch(e){ return 'Cohésio 1'; }
}
function setOpsCatMachine(m){
  try{ localStorage.setItem(OPS_CAT_MACHINE_KEY, m || ''); }catch(e){}
  // Synchronise tous les selects (le catalogue est dupliqué dans 2 vues)
  document.querySelectorAll('.js-ops-cat-machine').forEach(sel => { sel.value = m; });
  renderOpsTypes();
}
// Retourne la date ISO la plus récente d'une saisie sur (label, machine).
function _lastInterventionFor(label, machine, sourceList){
  if(!label || !machine || !Array.isArray(sourceList)) return null;
  const lblLc = String(label).toLowerCase().trim();
  const machLc = String(machine).toLowerCase().trim();
  let latest = null;
  for(const it of sourceList){
    if(!it) continue;
    const itType = String(it.type || '').toLowerCase().trim();
    const itMach = String(it.machine || '').toLowerCase().trim();
    // Machine peut être un CSV (ex: "Cohésio 1 · Cohésio 2") depuis la DB —
    // on considère un match si la machine ciblée est incluse dans la liste.
    const machineMatch = itMach === machLc
      || itMach.split('·').map(s => s.trim()).includes(machLc)
      || itMach.split(',').map(s => s.trim()).includes(machLc);
    if(itType === lblLc && machineMatch){
      const d = it.date_saisie;
      if(d && (!latest || d > latest)) latest = d;
    }
  }
  return latest;
}

// v229 — Variante par CODE, utilisée par les pièces d'usure. Le rattachement
// par libellé fonctionnait (l'historique fait un JOIN sur maintenance_codes et
// suit donc les renommages) mais restait indirect : deux codes homonymes se
// mélangeaient, et la comparaison portait sur du texte alors que chaque saisie
// porte déjà son code. Repli sur le libellé UNIQUEMENT si aucune entrée de la
// source ne porte de code (saisies locales legacy).
function _lastInterventionForCode(code, label, machine, sourceList){
  if(!code || !machine || !Array.isArray(sourceList)) return null;
  const codeStr = String(code);
  const machLc = String(machine).toLowerCase().trim();
  const machMatch = (m) => {
    const s = String(m || '').toLowerCase().trim();
    return s === machLc
      || s.split('·').map(x => x.trim()).includes(machLc)
      || s.split(',').map(x => x.trim()).includes(machLc);
  };
  let latest = null, sawAnyCode = false;
  for(const it of sourceList){
    if(!it || it._code == null || it._code === '') continue;
    sawAnyCode = true;
    if(String(it._code) !== codeStr) continue;
    if(!machMatch(it.machine)) continue;
    const d = it.date_saisie;
    if(d && (!latest || d > latest)) latest = d;
  }
  if(latest == null && !sawAnyCode) return _lastInterventionFor(label, machine, sourceList);
  return latest;
}

// Variante pour le catalogue "Liste de contrôles" : un contrôle peut être
// rempli soit manuellement (CTRL_STATE.list, matché par label === type), soit
// via une alerte opérateur (CTRL_STATE.acks, matché par code === _maint_code).
function _lastInterventionForCtrl(code, label, machine, manualList, ackList){
  if(!machine) return null;
  const lblLc = String(label || '').toLowerCase().trim();
  const machLc = String(machine).toLowerCase().trim();
  const machMatch = (itMach) => {
    const s = String(itMach || '').toLowerCase().trim();
    return s === machLc
      || s.split('·').map(x => x.trim()).includes(machLc)
      || s.split(',').map(x => x.trim()).includes(machLc);
  };
  let latest = null;
  if(Array.isArray(manualList)){
    for(const it of manualList){
      if(!it) continue;
      const itType = String(it.type || '').toLowerCase().trim();
      if(itType === lblLc && machMatch(it.machine)){
        const d = it.date_saisie;
        if(d && (!latest || d > latest)) latest = d;
      }
    }
  }
  if(Array.isArray(ackList) && code){
    for(const it of ackList){
      if(it && it._maint_code === code && machMatch(it.machine)){
        const d = it.date_saisie;
        if(d && (!latest || d > latest)) latest = d;
      }
    }
  }
  return latest;
}

async function loadOpsTypes(){
  try{
    const res = await fetch('/api/maintenance/codes', { credentials: 'include' });
    if(!res.ok){
      OPS_TYPES_STATE.list = [];
      return;
    }
    const data = await res.json();
    const items = Array.isArray(data && data.items) ? data.items : [];
    // Depuis v178 : 3 catégories ('controles', 'entretien', 'remplacements').
    // Les codes legacy ('interventions', 'suivi') sont remappés vers 'entretien'.
    const normCat = (c) => {
      if (c === 'remplacements') return 'remplacements';
      if (c === 'entretien' || c === 'interventions' || c === 'suivi') return 'entretien';
      return 'controles';
    };
    // Liste d'opérations : Entretien + Remplacements (toutes) + Contrôles avec periodique=OUI.
    OPS_TYPES_STATE.list = items
      .filter(it => {
        // v229 : un code rattaché à une pièce d'usure est TOUJOURS retenu,
        // quelle que soit sa catégorie — sinon _findWearPartCode ne le
        // trouverait pas et la carte se viderait sans explication.
        if(it.usure_piece_id != null) return true;
        const cn = normCat(it.categorie);
        return (cn === 'entretien') || (cn === 'remplacements') || (cn === 'controles' && !!it.periodique);
      })
      .map(it => ({
        id: it.code,
        nom: it.label,
        niveau: parseInt(it.niveau, 10) || 1,
        categorie: normCat(it.categorie),
        periodique: !!it.periodique,
        intervalle: (it.intervalle || '').toString(),
        metrage_ref: (it.metrage_ref || '').toString(),
        usure_piece_id: (it.usure_piece_id != null ? it.usure_piece_id : null),
        usure_position: (it.usure_position || '').toString(),
        frequence: (it.intervalle || '').toString(),  // alias compat _parseFrequenceDays
        detail: '',
        docs_count: parseInt(it.docs_count, 10) || 0,
        _readonly: true,
      }));
  }catch(e){
    OPS_TYPES_STATE.list = [];
  }
}

// v2.4.26 : couleur d'une barre de progression (opérations périodiques) ou
// d'un anneau (pièces d'usure) en fonction du ratio = jours_écoulés / intervalle.
// Système à 3 zones :
//   - 0 à 90 %   : vert franc constant (rien à signaler)
//   - 90 à 100 % : transition douce vert → début jaune (pré-alerte discrète)
//   - 100 à 200 %: dégradé jaune → orange → rouge (échéance dépassée, sévérité croissante)
//   - > 200 %    : rouge plein (clamp)
// Change par rapport à v1 : le vert restait "trop longtemps" un vert-jaune
// dès 50 % avant, maintenant il reste pur jusqu'à 90 %.
function _ratioColorRgb(ratio){
  // Stops en RATIO direct (pas de normalisation t=ratio/2 comme avant).
  const stops = [
    [0.00, [ 52, 211, 153]],   // vert franc
    [0.90, [ 52, 211, 153]],   // encore vert franc (fin de la zone safe)
    [1.00, [180, 208, 100]],   // transition vers jaune (léger warning à échéance)
    [1.33, [250, 204,  21]],   // jaune franc
    [1.66, [251, 146,  60]],   // orange
    [2.00, [220,  38,  38]],   // rouge
  ];
  const r = Math.max(0, Math.min(2, ratio || 0));  // clamp 0..2
  for(let i = 0; i < stops.length - 1; i++){
    const [ra, ca] = stops[i];
    const [rb, cb] = stops[i + 1];
    if(r <= rb){
      const lt = (rb === ra) ? 0 : (r - ra) / (rb - ra);
      const red   = Math.round(ca[0] + (cb[0] - ca[0]) * lt);
      const green = Math.round(ca[1] + (cb[1] - ca[1]) * lt);
      const blue  = Math.round(ca[2] + (cb[2] - ca[2]) * lt);
      return [red, green, blue];
    }
  }
  const last = stops[stops.length - 1][1];
  return [last[0], last[1], last[2]];
}
// Wrappers CSS. _ratioColor garde exactement la signature d'avant (rgb(...)),
// _ratioColorRgba sert a teinter bordure / titre / badge de la carte.
function _ratioColor(ratio){
  const c = _ratioColorRgb(ratio);
  return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')';
}
function _ratioColorRgba(ratio, alpha){
  const c = _ratioColorRgb(ratio);
  return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + alpha + ')';
}
// Compteur module-level pour générer des IDs uniques de paths SVG et filtres
// par carte (sinon les <textPath href="#..."> peuvent référencer un path d'une
// autre carte rendue avant, et les filtres se mélangent entre eux).
let _wpRingSvgCounter = 0;
// Génère le SVG de 2 anneaux concentriques (style Apple Watch).
// ratios : { temps: 0..∞ ou null, metres: 0..∞ ou null }
// Étiquettes "TEMPS" / "MÉTRAGE" droites à 12h (point de départ de chaque arc)
// et pourcentage actuel sur arc courbe à 6h. Longueur d'arc clampée à ~100%
// (au-delà : tour supplémentaire posé par-dessus, extrémité toujours visible).
function _renderWearPartRings(ratios){
  const size = 200, cx = 100, cy = 100, sw = 18;
  const rOuter = 86;                  // rayon anneau temps
  const rInner = rOuter - sw - 6;     // rayon anneau métrage
  const _arc = (r, ratio) => {
    const circ = 2 * Math.PI * r;
    const trackBg = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="var(--border)" stroke-width="' + sw + '" opacity="0.28"/>';
    if(ratio == null || !isFinite(ratio)) return trackBg;
    const color = _ratioColor(ratio);
    // < 100% : un seul arc partiel (comportement standard).
    if(ratio < 1){
      const offset = circ * (1 - ratio);
      const fg = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="' + sw +
        '" stroke-linecap="round" stroke-dasharray="' + circ.toFixed(2) + '" stroke-dashoffset="' + offset.toFixed(2) +
        '" transform="rotate(-90 ' + cx + ' ' + cy + ')" style="transition:stroke-dashoffset .35s ease,stroke .15s"/>';
      return trackBg + fg;
    }
    // >= 100% : rendu Apple Watch. Le tour precedent reste PLEIN et un nouveau
    // tour continu part de 12h jusqu'a la position d'avancement, pose par-dessus.
    // Les deux tours ont la meme couleur : c'est uniquement l'ombre portee sous
    // la tete arrondie qui revele la superposition (plus de "point volant").
    // Au-dela de 200% les tours s'empilent : on affiche la fraction du tour en
    // cours (ratio - floor(ratio)), la tete reste donc toujours a sa position
    // reelle sur le cadran.
    const baseLap = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="' + sw +
      '" style="transition:stroke .15s"/>';
    const frac = ratio - Math.floor(ratio);
    // Pile sur un tour complet (100%, 200%...) : cercle plein, pas de tete.
    if(frac <= 0.002) return trackBg + baseLap;
    const arcLen = circ * frac;
    // Segment court a la tete du tour en cours. Il n'est pas visible en propre
    // (meme couleur, meme geometrie que l'arc pose juste au-dessus) : son seul
    // role est de PROJETER l'ombre sur le tour du dessous. En limitant sa
    // longueur, on obtient un croissant d'ombre localise sous la tete au lieu
    // d'un halo sur tout l'anneau.
    const shadowLen = Math.min(arcLen, sw * 1.5);
    const shadowStyle = 'filter:'
      + 'drop-shadow(0 0 2px rgba(0,0,0,.40)) '
      + 'drop-shadow(1.5px 2.5px 3px rgba(0,0,0,.38))';
    const shadowSeg = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r +
      '" fill="none" stroke="' + color + '" stroke-width="' + sw +
      '" stroke-linecap="round" stroke-dasharray="' + shadowLen.toFixed(2) + ' ' + (circ - shadowLen).toFixed(2) +
      '" stroke-dashoffset="' + (-(arcLen - shadowLen)).toFixed(2) +
      '" transform="rotate(-90 ' + cx + ' ' + cy + ')" style="' + shadowStyle + '"/>';
    // Tour en cours : arc continu de 12h jusqu'a la position reelle, extremites
    // arrondies (le cap de depart se fond dans le tour du dessous).
    const lap = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="' + sw +
      '" stroke-linecap="round" stroke-dasharray="' + arcLen.toFixed(2) + ' ' + (circ - arcLen).toFixed(2) +
      '" transform="rotate(-90 ' + cx + ' ' + cy + ')" style="transition:stroke-dasharray .35s ease,stroke .15s"/>';
    return trackBg + baseLap + shadowSeg + lap;
  };
  // Étiquette titre à 12h (texte droit) sur chaque anneau.
  // Texte blanc, contour foncé paint-order:stroke pour rester lisible quel que
  // soit le fond (track gris, dégradé vert, jaune, orange ou rouge).
  const _textStyle = 'paint-order:stroke;stroke:rgba(15,23,42,.75);stroke-width:2.5px;pointer-events:none;text-transform:uppercase';
  const _textCommonAttr = 'fill="#ffffff" font-size="9" font-weight="700" letter-spacing="0.8" font-family="system-ui,-apple-system,Segoe UI,sans-serif"';
  const _topTag = (yPos, txt) =>
    '<text x="' + cx + '" y="' + yPos + '" text-anchor="middle" dominant-baseline="central" ' +
      _textCommonAttr + ' style="' + _textStyle + '">' + txt + '</text>';
  // % courbé sur arc inférieur (6h) — suit la courbure de l'anneau.
  const uid = ++_wpRingSvgCounter;
  const idTempsBot  = 'wpr-tb-' + uid;
  const idMetresBot = 'wpr-mb-' + uid;
  // Path = demi-cercle INFÉRIEUR de gauche à droite. En SVG (y-axe inversé),
  // sweep-flag=0 correspond à la trajectoire qui passe par le BAS du cercle.
  // À 6h, la tangente du path va dans le sens +x : les caractères du textPath
  // s'élèvent alors vers le centre du cercle (lecture upright normale).
  const _bottomPath = (id, r) =>
    '<path id="' + id + '" d="M ' + (cx - r) + ' ' + cy +
    ' A ' + r + ' ' + r + ' 0 0 0 ' + (cx + r) + ' ' + cy + '" fill="none"/>';
  const _bottomLabel = (pathId, ratio) => {
    if(ratio == null || !isFinite(ratio)) return '';
    const pct = Math.round(ratio * 100) + '%';
    return '<text ' + _textCommonAttr + ' style="' + _textStyle + '">' +
      '<textPath href="#' + pathId + '" startOffset="50%" text-anchor="middle">' +
        pct +
      '</textPath>' +
    '</text>';
  };
  return '<svg viewBox="0 0 ' + size + ' ' + size + '" width="200" height="200" aria-hidden="true">' +
           '<defs>' +
             _bottomPath(idTempsBot,  rOuter) +
             _bottomPath(idMetresBot, rInner) +
           '</defs>' +
           _arc(rOuter, ratios.temps) +
           _arc(rInner, ratios.metres) +
           _topTag(cy - rOuter, 'Temps') +
           _topTag(cy - rInner, 'Métrage') +
           _bottomLabel(idTempsBot,  ratios.temps) +
           _bottomLabel(idMetresBot, ratios.metres) +
         '</svg>';
}

// v229 — Retrouve le code maintenance rattaché à une pièce d'usure.
//
// Avant : on parcourait tous les codes en lisant leur LIBELLÉ à la recherche de
// 'couteaux' / 'contre' / 'bande' / 'rive' / 'landberg' / 'cutter'. Renommer un
// code détachait sa carte, et deux codes matchant la même position se masquaient
// l'un l'autre (premier arrivé, premier servi, en silence).
//
// Après : lecture directe de la relation posée en base. pieceId = la CLE de la
// pièce ('couteaux'…) ; pos = une position déclarée, ou 'single'.
function _findWearPartCode(pieceId, pos){
  const def = _wearPartDef(pieceId);
  if(!def) return null;
  const wantPos = def.no_position ? '' : String(pos || '');
  const t = (OPS_TYPES_STATE.list || []).find(x =>
    x.usure_piece_id != null
    && String(x.usure_piece_id) === String(def.pieceId)
    && String(x.usure_position || '') === wantPos
  );
  if(!t) return null;
  return {
    code: t.id,
    label: t.nom,
    intervalle: t.intervalle || '',
    metrage_ref: t.metrage_ref || '',
  };
}
// Conservé pour compat (no-op : géré dans Paramètres → Maintenance).
function saveOpsTypes(){ /* géré côté serveur via /api/maintenance/codes */ }

// =========================================================================
// Détails libres par code (notes locales, non stockées en base)
// =========================================================================
const OPS_TYPES_DETAILS_KEY = 'mysifa_maint_optypes_details_v1';
let _opsTypeDetailsEditingId = null;

function _loadOpsTypeDetailsMap(){
  try{
    const raw = localStorage.getItem(OPS_TYPES_DETAILS_KEY);
    const m = raw ? JSON.parse(raw) : {};
    return (m && typeof m === 'object') ? m : {};
  }catch(e){ return {}; }
}
function _saveOpsTypeDetailsMap(map){
  try{ localStorage.setItem(OPS_TYPES_DETAILS_KEY, JSON.stringify(map || {})); }catch(e){}
}
function getOpsTypeDetails(code){
  if(!code) return '';
  const map = _loadOpsTypeDetailsMap();
  return map[code] || '';
}
function openOpsTypeDetailsModal(code){
  const t = OPS_TYPES_STATE.list.find(x => String(x.id) === String(code));
  if(!t) return;
  _opsTypeDetailsEditingId = code;
  const modal = document.getElementById('ops-type-details-modal');
  const titleEl = document.getElementById('ops-type-details-title');
  const infoEl = document.getElementById('ops-type-details-info');
  const textEl = document.getElementById('ops-type-details-text');
  if(!modal || !infoEl || !textEl) return;
  if(titleEl) titleEl.textContent = t.nom || 'Détails de l\'opération';
  // Bloc info DB (lecture seule) : catégorie, niveau, intervalle, dernière intervention
  const machine = getOpsCatMachine();
  const lastDt = _lastInterventionFor(t.nom, machine, OPS_STATE.list);
  let lastDisplay = '—';
  if(lastDt){
    try{
      const d = new Date(lastDt);
      if(!isNaN(d.getTime())){
        const pad = n => (n < 10 ? '0' + n : '' + n);
        lastDisplay = pad(d.getDate()) + '/' + pad(d.getMonth()+1) + '/' + d.getFullYear()
                    + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
      }
    }catch(e){}
  }
  const catLabel = _maintCatLabelFront(t.categorie);
  const intervalleTxt = t.periodique
    ? (t.intervalle || 'À compléter (Paramètres → Maintenance)')
    : '— (non périodique)';
  const _kv = (lbl, val) =>
    '<div><div style="font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">' + lbl + '</div>' +
    '<div style="color:var(--text);font-weight:500">' + val + '</div></div>';
  infoEl.innerHTML = ''
    + _kv('Code', escHtml(String(t.id)))
    + _kv('Catégorie', '<span class="op-pill ' + _maintCatCssFront(t.categorie) + '">' + escHtml(catLabel) + '</span>')
    + _kv('Niveau', '<span class="niv-badge" data-niv="' + t.niveau + '">N' + t.niveau + '</span>')
    + _kv('Intervalle', escHtml(intervalleTxt))
    + _kv('Machine sélectionnée', escHtml(machine))
    + _kv('Dernière intervention', escHtml(lastDisplay));
  textEl.value = getOpsTypeDetails(code);
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  setTimeout(() => textEl.focus(), 50);
}
function closeOpsTypeDetailsModal(){
  const modal = document.getElementById('ops-type-details-modal');
  if(!modal) return;
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  _opsTypeDetailsEditingId = null;
}
function saveOpsTypeDetails(e){
  if(e && e.preventDefault) e.preventDefault();
  if(!_opsTypeDetailsEditingId) return;
  const textEl = document.getElementById('ops-type-details-text');
  if(!textEl) return;
  const val = (textEl.value || '').trim();
  const map = _loadOpsTypeDetailsMap();
  if(val){ map[_opsTypeDetailsEditingId] = val; }
  else { delete map[_opsTypeDetailsEditingId]; }
  _saveOpsTypeDetailsMap(map);
  showToast('Détails enregistrés.', 'info');
  closeOpsTypeDetailsModal();
}

// =========================================================================
// Vue Maintenance (accueil) : cartes par opération périodique, par machine
// =========================================================================
const MAINT_MACHINE_KEY = 'mysifa_maint_home_machine_v1';
// Filtre de catégorie de la vue Maintenance (v178, élargi en v2.7.4).
// Trois états : « Tous », « Entretien », « Interventions ».
// Les contrôles ne sont JAMAIS visibles dans cette vue.
const MAINT_CAT_FILTER_KEY = 'mysifa_maint_home_cat_filter_v1';

// v2.7.4 : trois etats desormais — 'all' (les deux categories), 'entretien',
// 'remplacements'. La valeur deja stockee chez les utilisateurs existants est
// l'une des deux anciennes : elle reste valide, aucune migration necessaire.
function getMaintCatFilter(){
  try{
    const v = localStorage.getItem(MAINT_CAT_FILTER_KEY);
    if(v === 'remplacements' || v === 'all') return v;
    return 'entretien';
  }catch(e){ return 'entretien'; }
}
function setMaintCatFilter(c){
  if(c !== 'all' && c !== 'entretien' && c !== 'remplacements') return;
  try{ localStorage.setItem(MAINT_CAT_FILTER_KEY, c); }catch(e){}
  renderMaintCards();
}

function getMaintMachine(){
  try{ return localStorage.getItem(MAINT_MACHINE_KEY) || 'Cohésio 1'; }
  catch(e){ return 'Cohésio 1'; }
}
function setMaintMachine(m){
  if(!m) return;
  try{ localStorage.setItem(MAINT_MACHINE_KEY, m); }catch(e){}
  // Invalide le cache des dates wearparts : nouvelle machine = nouveau fetch
  _invalidateWearPartCache();
  renderMaintCards();
}

// --- v2.4.6 : filtre par statut ---------------------------------------
// Statuts : 'all' (défaut) · 'overdue' · 'soon' · 'ok' · 'never'
// Le regroupement est fixe (par statut) — le toggle a été retiré car
// redondant avec le filtre statut et le sélecteur machine du haut.
const MAINT_STATUS_FILTER_KEY = 'mysifa_maint_home_status_filter_v1';

function getMaintStatusFilter(){
  try{
    const v = localStorage.getItem(MAINT_STATUS_FILTER_KEY);
    if(v === 'overdue' || v === 'soon' || v === 'ok' || v === 'never') return v;
    return 'all';
  }catch(e){ return 'all'; }
}
function setMaintStatusFilter(s){
  if(s !== 'all' && s !== 'overdue' && s !== 'soon' && s !== 'ok' && s !== 'never') return;
  try{ localStorage.setItem(MAINT_STATUS_FILTER_KEY, s); }catch(e){}
  renderMaintCards();
}
// Statut d'une opération à partir de son intervalle (jours) et du nombre de
// jours depuis la dernière saisie. Seuils :
//   - 'overdue' : ratio > 1 (retard, dès dépassement)
//   - 'soon'    : ratio >= 0.8 (dû dans les 20 % derniers de l'intervalle)
//   - 'ok'      : ratio < 0.8 (à jour)
//   - 'never'   : intervalle défini mais aucune saisie
//   - 'unknown' : intervalle non reconnu
function _maintComputeStatus(freqDays, daysSince){
  if(freqDays == null || freqDays <= 0) return 'unknown';
  if(daysSince == null) return 'never';
  const ratio = daysSince / freqDays;
  if(ratio > 1) return 'overdue';
  if(ratio >= 0.8) return 'soon';
  return 'ok';
}

// Libellés + ordre de tri des groupes "par statut" (retards en tête, jamais en bas).
const MAINT_STATUS_ORDER = ['overdue','soon','ok','unknown','never'];
const MAINT_STATUS_LABELS = {
  overdue: 'En retard',
  soon:    'Dû bientôt',
  ok:      'À jour',
  unknown: 'Intervalle non reconnu',
  never:   'Jamais saisi',
};
// Liste des machines exposées dans la vue Maintenance (accueil).
const MAINT_HOME_MACHINES = ['Cohésio 1', 'Cohésio 2'];

// v2.4.27 : refonte — pastilles Machine et Catégorie affichent maintenant
// 2 pastilles chacune (rouge = retards, orange = dû bientôt), et incluent les
// pièces d'usure (par POSITION, comme le comptage des chips Statut v2.4.25).
// En bonus : pastille rouge globale sur l'item sidebar "Maintenance" =
// somme des retards toutes machines confondues (visible depuis les autres
// vues internes Planning / Alertes / Opérations).
function _refreshMaintCounters(){
  const items = (OPS_TYPES_STATE.list || []).filter(it => !!it.periodique);
  // Helper : status d'un item périodique pour une machine donnée.
  const periodicStatus = (it, machine) => {
    const freqDays = _parseFrequenceDays(it.intervalle);
    if(freqDays == null || freqDays <= 0) return 'unknown';
    const last = _lastInterventionFor(it.nom, machine, OPS_STATE.list);
    if(!last) return 'never';
    try{
      const d = new Date(last);
      const today = new Date();
      const dMid = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      const tMid = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      const daysSince = Math.floor((tMid - dMid) / (1000 * 60 * 60 * 24));
      return _maintComputeStatus(freqDays, daysSince);
    }catch(e){ return 'unknown'; }
  };
  // Helper : maj DOM d'une pastille — text = count si >0, sinon hidden.
  const setBadge = (el, count) => {
    if(!el) return;
    if(count > 0){ el.textContent = String(count); el.classList.remove('hidden'); }
    else { el.classList.add('hidden'); }
  };
  let globalOverdue = 0;
  // ── Compteurs par MACHINE (toutes catégories + pièces d'usure) ─────
  MAINT_HOME_MACHINES.forEach(machine => {
    let overdue = 0, soon = 0;
    items.forEach(it => {
      const st = periodicStatus(it, machine);
      if(st === 'overdue') overdue++;
      else if(st === 'soon') soon++;
    });
    WEARPART_PIECES.forEach(p => {
      _wearPartPositionsOf(p).forEach(pos => {
        const st = _wearPartPositionStatus(p.id, pos, machine);
        if(st === 'overdue') overdue++;
        else if(st === 'soon') soon++;
      });
    });
    globalOverdue += overdue;
    const esc = machine.replace(/"/g, '\\"');
    setBadge(document.querySelector('[data-maint-machine-badge="' + esc + '"]'), overdue);
    setBadge(document.querySelector('[data-maint-machine-badge-soon="' + esc + '"]'), soon);
  });
  // ── Compteurs par CATÉGORIE (sur la machine active) ────────────────
  const machine = getMaintMachine();
  const cats = { entretien: {o:0, s:0}, remplacements: {o:0, s:0} };
  items.forEach(it => {
    const cat = it.categorie;
    let bucket = null;
    if(cat === 'controles' || cat === 'entretien' || cat === 'interventions' || cat === 'suivi') bucket = 'entretien';
    else if(cat === 'remplacements') bucket = 'remplacements';
    if(!bucket) return;
    const st = periodicStatus(it, machine);
    if(st === 'overdue') cats[bucket].o++;
    else if(st === 'soon') cats[bucket].s++;
  });
  // Pièces d'usure = catégorie "remplacements"
  WEARPART_PIECES.forEach(p => {
    _wearPartPositionsOf(p).forEach(pos => {
      const st = _wearPartPositionStatus(p.id, pos, machine);
      if(st === 'overdue') cats.remplacements.o++;
      else if(st === 'soon') cats.remplacements.s++;
    });
  });
  // v2.7.4 : le bouton « Tous » porte le cumul des deux categories.
  cats.all = { o: cats.entretien.o + cats.remplacements.o,
               s: cats.entretien.s + cats.remplacements.s };
  Object.keys(cats).forEach(cat => {
    setBadge(document.querySelector('[data-maint-cat-badge="' + cat + '"]'), cats[cat].o);
    setBadge(document.querySelector('[data-maint-cat-badge-soon="' + cat + '"]'), cats[cat].s);
  });
  // ── Pastille sidebar globale (retards toutes machines) ─────────────
  setBadge(document.getElementById('nav-maint-badge'), globalOverdue);
}

// Applique l'état actif visuel sur les chips statut + groupement.
function _refreshMaintChipState(){
  const status = getMaintStatusFilter();
  document.querySelectorAll('[data-status-filter]').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-status-filter') === status);
  });
}
// --- Dernières opérations couteaux/contre-couteaux (source : MyProd) ---
// On interroge /api/maintenance/wearparts/last qui scanne production_data
// pour la machine sélectionnée. Réponse : { items: { "couteaux_bande": {
// last_date, metrage_at_change, metrage_since }, ... }, current_metrage }.
// Cache invalidé sur changement de machine.
const WEARPART_LAST_DATES_STATE = {
  machine: null,
  items: {},          // { piece_pos: { last_date, metrage_at_change, metrage_since } }
  current_metrage: null,
  loading: false,
  _cacheKey: null,    // clé du dernier fetch REUSSI (machine + dates)
  _attemptKey: null,  // clé du dernier fetch TENTE (posée avant l'appel réseau)
};

// v2.5.7 : invalidation complète du cache wearparts. À appeler dès que la
// source des dates de dernière intervention peut avoir bougé (changement de
// machine, arrivée sur la vue, saisie/suppression d'une intervention).
// Réinitialiser _cacheKey ET _attemptKey est indispensable : sans ça
// loadWearPartLastDates court-circuite le fetch alors que `machine` vient
// d'être remis à null, et les cartes restent bloquées sur « Chargement… ».
function _invalidateWearPartCache(){
  if(typeof WEARPART_LAST_DATES_STATE !== 'object' || !WEARPART_LAST_DATES_STATE) return;
  WEARPART_LAST_DATES_STATE.machine = null;
  WEARPART_LAST_DATES_STATE.items = {};
  WEARPART_LAST_DATES_STATE.current_metrage = null;
  WEARPART_LAST_DATES_STATE._cacheKey = null;
  WEARPART_LAST_DATES_STATE._attemptKey = null;
}

async function loadWearPartLastDates(machine){
  if(!machine) return;
  // Récupère les dates des dernières saisies maintenance dans OPS_STATE (source
  // locale, navigateur) pour chaque combinaison pièce x position. Envoie ces
  // dates au backend qui retourne le métrage machine à chaque date.
  if(typeof loadOps === 'function') loadOps();
  const dates = {};
  WEARPART_PIECES.forEach(p => {
    if(p.no_position){
      const k = p.id + '_single';
      const c = _findWearPartCode(p.id, 'single');
      dates[k] = c ? _lastInterventionForCode(c.code, c.label, machine, OPS_STATE.list) : null;
    } else {
      _wearPartPositionsOf(p).forEach(pos => {
        const k = p.id + '_' + pos;
        const c = _findWearPartCode(p.id, pos);
        dates[k] = c ? _lastInterventionForCode(c.code, c.label, machine, OPS_STATE.list) : null;
      });
    }
  });
  // Clé de cache : machine + dates concaténées. Si rien n'a changé → skip fetch.
  // v2.5.7 : la garde porte sur _attemptKey, posée AVANT l'appel réseau et quel
  // que soit son issue. Avec _cacheKey seul (posée uniquement en cas de succès),
  // un fetch en échec relançait une requête à chaque render — le `finally`
  // déclenche renderMaintCards, qui rappelle cette fonction : boucle infinie.
  const cacheKey = machine + ':' + JSON.stringify(dates);
  if(WEARPART_LAST_DATES_STATE.loading) return;
  if(WEARPART_LAST_DATES_STATE._attemptKey === cacheKey
     && WEARPART_LAST_DATES_STATE.machine === machine) return;
  WEARPART_LAST_DATES_STATE._attemptKey = cacheKey;
  WEARPART_LAST_DATES_STATE.loading = true;
  try{
    const res = await fetch('/api/maintenance/wearparts/info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ machine, dates }),
    });
    if(res.ok){
      const data = await res.json();
      WEARPART_LAST_DATES_STATE.machine = machine;
      WEARPART_LAST_DATES_STATE.items = (data && data.items) ? data.items : {};
      WEARPART_LAST_DATES_STATE.current_metrage = (data && data.current_metrage != null) ? data.current_metrage : null;
      WEARPART_LAST_DATES_STATE._cacheKey = cacheKey;
    }
  }catch(e){
    // Conserve l'ancien cache en cas d'erreur
  }finally{
    WEARPART_LAST_DATES_STATE.loading = false;
    if(typeof renderMaintCards === 'function') renderMaintCards();
  }
}
function _getWearPartLastDateKey(pieceId, pos){
  return pieceId + '_' + pos;  // ex. "couteaux_bande", "contre_couteaux_rive"
}
function _getWearPartItem(pieceId, pos){
  const k = _getWearPartLastDateKey(pieceId, pos);
  return (WEARPART_LAST_DATES_STATE.items && WEARPART_LAST_DATES_STATE.items[k]) || null;
}
// Formate un nombre de mètres avec séparateurs d'espaces (style FR).
function _fmtMetres(m){
  if(m == null) return '—';
  const n = Math.round(Number(m));
  if(!isFinite(n)) return '—';
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' m';
}
// Parse une référence métrage en mètres. Accepte "5000", "5000 m", "5 km",
// "1.5 km", "5000m", "10 kms", etc. Renvoie un nombre de mètres, ou null
// si le texte n'est pas interprétable.
function _parseMetrageRef(text){
  if(!text) return null;
  const s = String(text).toLowerCase().trim();
  if(!s) return null;
  const m = s.match(/([0-9]+(?:[.,][0-9]+)?)\s*(km|kms|kilom\w*|m|mt|mtr|metres?|mètres?)?/);
  if(!m) return null;
  const n = parseFloat(m[1].replace(',', '.'));
  if(!isFinite(n) || n <= 0) return null;
  const unit = m[2] || '';
  if(unit.startsWith('km') || unit.startsWith('kilom')) return n * 1000;
  return n;  // par défaut : mètres
}
function _daysSinceFromIso(iso){
  if(!iso) return null;
  try{
    const d = new Date(iso);
    if(isNaN(d.getTime())) return null;
    const today = new Date();
    const dMid = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const tMid = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return Math.floor((tMid - dMid) / (1000 * 60 * 60 * 24));
  }catch(e){ return null; }
}
function _fmtDateOnly(iso){
  if(!iso) return '';
  try{
    const d = new Date(iso);
    if(isNaN(d.getTime())) return '';
    const pad = n => (n < 10 ? '0' + n : '' + n);
    return pad(d.getDate()) + '/' + pad(d.getMonth()+1) + '/' + d.getFullYear();
  }catch(e){ return ''; }
}

// --- Pièces d'usure (Couteaux / Contre-couteaux) avec position Bande/Rive ---
// Une carte par pièce, position mémorisée par machine + par pièce.
// État localStorage : { "<piece>": { "<machine>": "bande"|"rive" } }
const WEARPART_KEY = 'mysifa_maint_wearparts_v1';
// v229 : le référentiel vient de /api/maintenance/usure-pieces au lieu d'être
// figé ici. `id` reste la CLE de la pièce (couteaux, contre_couteaux…), la même
// qu'avant : le localStorage des utilisateurs (onglet Bande/Rive mémorisé par
// machine) reste donc valide. `pieceId` porte l'id numérique en base, seul
// utilisé pour retrouver le code rattaché.
let WEARPART_PIECES = [];
let _WP_PIECES_LOADED = false;
let _WP_PIECES_LOADING = false;

async function loadWearPartPieces(){
  if(_WP_PIECES_LOADING) return;
  _WP_PIECES_LOADING = true;
  try{
    const r = await fetch('/api/maintenance/usure-pieces', { credentials: 'include' });
    if(r.ok){
      const d = await r.json();
      WEARPART_PIECES = (d && Array.isArray(d.items) ? d.items : []).map(p => {
        const positions = Array.isArray(p.positions) ? p.positions : [];
        return {
          id: p.cle,
          pieceId: p.id,
          label: p.label,
          positions: positions,
          no_position: positions.length === 0,
        };
      });
    }
  }catch(e){
    // Non bloquant : sans référentiel, la section Pièces d'usure ne s'affiche
    // simplement pas — le reste de l'accueil Maintenance reste fonctionnel.
    WEARPART_PIECES = [];
  }finally{
    _WP_PIECES_LOADED = true;
    _WP_PIECES_LOADING = false;
    if(typeof renderMaintCards === 'function') renderMaintCards();
  }
}

// --- v2.4.21 : filtrage pieces d'usure par statut ("Tous" / "Jamais saisi") -
// Une position est "renseignee" si _lastInterventionFor renvoie une date non
// nulle pour son code+machine. Une piece a 1 ou 2 positions (bande/rive ou
// single). Le rendu doit :
//   - En 'all'   : montrer seulement les pieces avec >=1 position renseignee,
//                  et forcer la position affichee sur une renseignee.
//   - En 'never' : montrer seulement les pieces avec >=1 position vide,
//                  et forcer la position affichee sur une vide.
function _wearPartPositionsOf(piece){
  return piece.no_position ? ['single'] : (piece.positions || []).slice();
}
function _wearPartHasData(pieceId, pos, machine){
  const wpCode = _findWearPartCode(pieceId, pos);
  if(!wpCode) return false;
  const last = _lastInterventionForCode(wpCode.code, wpCode.label, machine, OPS_STATE.list);
  return last != null;
}
// Retourne pour chaque piece : positions renseignees / non renseignees.
function _wearPartStatusFor(pieceId, machine){
  const p = _wearPartDef(pieceId);
  if(!p) return { hasData: [], noData: [] };
  const hasData = [], noData = [];
  _wearPartPositionsOf(p).forEach(pos => {
    if(_wearPartHasData(pieceId, pos, machine)) hasData.push(pos);
    else noData.push(pos);
  });
  return { hasData, noData };
}
// Compte les pieces qualifiantes pour les filtres 'all' et 'never', pour
// alimenter les compteurs des chips statut de la sous-toolbar.
// Status d'une position (overdue/soon/ok/never/unknown), meme logique que
// _maintComputeStatus pour les operations periodiques mais sur le temps
// UNIQUEMENT — cf. regle produit v2.4.23 : metrage n'est pas un facteur retard.
function _wearPartPositionStatus(pieceId, pos, machine){
  const wpCode = _findWearPartCode(pieceId, pos);
  if(!wpCode) return 'unknown';
  const refDays = _parseFrequenceDays(wpCode.intervalle || '');
  const lastDate = _lastInterventionForCode(wpCode.code, wpCode.label, machine, OPS_STATE.list);
  const daysSince = _daysSinceFromIso(lastDate);
  return _maintComputeStatus(refDays, daysSince);
}
// Compte chaque POSITION comme une operation distincte, ventilee par statut.
// Une piece Couteaux avec Bande faite hier + Rive faite aujourd'hui = 2 dans .ok
// (et non 1 dans .all comme avant v2.4.25).
function _wearPartsCounts(machine){
  const c = { overdue: 0, soon: 0, ok: 0, never: 0, unknown: 0 };
  WEARPART_PIECES.forEach(p => {
    _wearPartPositionsOf(p).forEach(pos => {
      const st = _wearPartPositionStatus(p.id, pos, machine);
      if(c[st] !== undefined) c[st]++;
    });
  });
  return c;
}
// Retourne le descripteur d'une pièce d'usure par id (utile pour tester no_position)
function _wearPartDef(pieceId){
  return WEARPART_PIECES.find(p => p.id === pieceId) || null;
}
function _wearPartIsSingle(pieceId){
  const d = _wearPartDef(pieceId);
  return !!(d && d.no_position);
}

function _loadWearPartMap(){
  try{
    const m = JSON.parse(localStorage.getItem(WEARPART_KEY) || '{}');
    return (m && typeof m === 'object') ? m : {};
  }catch(e){ return {}; }
}
function _saveWearPartMap(m){
  try{ localStorage.setItem(WEARPART_KEY, JSON.stringify(m || {})); }catch(e){}
}
function getWearPartPos(pieceId, machine){
  if(_wearPartIsSingle(pieceId)) return 'single';
  const def = _wearPartDef(pieceId);
  const positions = def ? (def.positions || []) : [];
  const m = _loadWearPartMap();
  const saved = (m[pieceId] && m[pieceId][machine]) || '';
  // v229 : le défaut est la 1re position DÉCLARÉE, plus 'bande' en dur. Une
  // valeur mémorisée qui n'existe plus (position retirée de la pièce) retombe
  // sur ce défaut au lieu de sélectionner un onglet fantôme.
  if(saved && positions.indexOf(saved) !== -1) return saved;
  return positions[0] || '';
}
function setWearPartPos(pieceId, pos){
  const _def = _wearPartDef(pieceId);
  if(!_def || (_def.positions || []).indexOf(pos) === -1) return;
  const machine = getMaintMachine();
  const m = _loadWearPartMap();
  if(!m[pieceId]) m[pieceId] = {};
  m[pieceId][machine] = pos;
  _saveWearPartMap(m);
  // Mise a jour DOM DIRECTE des boutons — independante du re-render.
  // Garantit que le toggle visuel fonctionne meme si renderMaintCards
  // est bloque par une erreur ou une race async.
  try{
    document.querySelectorAll('.maint-wp-btn[data-wp="' + pieceId + '"]').forEach(function(b){
      b.classList.toggle('active', b.getAttribute('data-pos') === pos);
    });
    document.querySelectorAll('.maint-wearpart[data-wearpart="' + pieceId + '"]').forEach(function(s){
      s.setAttribute('data-wearpart-pos', pos);
    });
  }catch(e){ console.warn('[setWearPartPos direct DOM]', e); }
  renderMaintCards();
}
// Rend explicite l'export global pour l'inline onclick (défensif).
try{ window.setWearPartPos = setWearPartPos; }catch(e){}
// Event delegation de secours : si l'inline onclick est bloqué (CSP,
// extension navigateur, script injecté), la délégation prend le relais.
// Sur .maint-wp-btn avec data-wp + data-pos, on lit les attributs et on
// dispatch. Une seule fois, sur document, pour éviter les doublons.
// Event delegation robuste sur .maint-wp-btn (Bande/Rive des pieces d'usure).
// Handler en phase CAPTURE + BUBBLE pour maximiser la reception du click,
// meme si un autre listener tente de stopPropagation en amont.
// Log console explicite pour diagnostic si le click ne fonctionne pas.
(function _installWearPartDelegation(){
  if(window.__mysifa_wp_deleg_installed) return;
  window.__mysifa_wp_deleg_installed = true;
  const handler = function(e){
    const btn = e.target && e.target.closest ? e.target.closest('.maint-wp-btn') : null;
    if(!btn) return;
    const pieceId = btn.getAttribute('data-wp');
    const pos = btn.getAttribute('data-pos');
    console.log('[wearpart click]', pieceId, pos, 'phase:', e.eventPhase);
    if(!pieceId || !pos) return;
    e.preventDefault();
    try{ setWearPartPos(pieceId, pos); }catch(err){ console.error('[wearpart handler]', err); }
  };
  document.addEventListener('click', handler, true);
  document.addEventListener('click', handler, false);
})();
// Références d'usure (temps & métrage) — état localStorage :
//   { "<piece>": { "<machine>": { "<position>": { temps: "...", metrage: "..." } } } }
const WEARPART_REFS_KEY = 'mysifa_maint_wearparts_refs_v1';
function _loadWearPartRefs(){
  try{
    const m = JSON.parse(localStorage.getItem(WEARPART_REFS_KEY) || '{}');
    return (m && typeof m === 'object') ? m : {};
  }catch(e){ return {}; }
}
function _saveWearPartRefs(m){
  try{ localStorage.setItem(WEARPART_REFS_KEY, JSON.stringify(m || {})); }catch(e){}
}
function getWearPartRef(pieceId, machine, pos, kind){
  // kind = 'temps' | 'metrage'
  const m = _loadWearPartRefs();
  return ((m[pieceId] || {})[machine] || {})[pos] && m[pieceId][machine][pos][kind] || '';
}
function setWearPartRef(pieceId, kind, value){
  if(kind !== 'temps' && kind !== 'metrage') return;
  const machine = getMaintMachine();
  const pos = getWearPartPos(pieceId, machine);
  const m = _loadWearPartRefs();
  if(!m[pieceId]) m[pieceId] = {};
  if(!m[pieceId][machine]) m[pieceId][machine] = {};
  if(!m[pieceId][machine][pos]) m[pieceId][machine][pos] = {};
  m[pieceId][machine][pos][kind] = (value || '').toString().trim();
  _saveWearPartRefs(m);
  // Pas besoin de re-render : la valeur est déjà dans l'input. On évite ainsi
  // de perdre le focus pendant que l'utilisateur tape.
}

function _renderWearPartsGroup(machine, statusFilter){
  // v229 : le référentiel des pièces est distant. Tant qu'il n'est pas arrivé,
  // la section n'est pas rendue ; loadWearPartPieces rappelle renderMaintCards
  // en sortie, et le drapeau _WP_PIECES_LOADED empêche toute boucle.
  if(!_WP_PIECES_LOADED){ loadWearPartPieces(); return ''; }
  // Déclenche le fetch des dernières dates (asynchrone : le render initial
  // affiche "Chargement…", puis re-render au retour).
  //
  // v2.5.7 — BUG CORRIGE : l'appel était conditionné à un changement de MACHINE.
  // Or les dates viennent de OPS_STATE.list, alimenté par loadOps() qui est
  // *synchrone mais fetch en arrière-plan*. Au premier render OPS_STATE contient
  // encore l'historique périmé : on interrogeait donc le serveur avec la date de
  // l'intervention PRECEDENTE. Quand l'historique DB arrivait, renderMaintCards
  // recalculait `lastDate` en direct (date fraîche, correcte) mais la machine
  // n'ayant pas changé, aucun refetch n'avait lieu — le métrage restait celui
  // calculé depuis l'ancienne date. Résultat à l'écran : « Dernière intervention
  // aujourd'hui » à côté de « Parcouru 552 242 m ».
  //
  // L'appel est désormais inconditionnel : c'est loadWearPartLastDates qui
  // arbitre via _attemptKey (machine + dates). Si les dates n'ont pas bougé,
  // elle sort immédiatement — aucun trafic réseau supplémentaire.
  loadWearPartLastDates(machine);
  // v2.4.25 : filtre les positions par statut fin (overdue/soon/ok/never).
  // - 'all'   : positions renseignees (overdue + soon + ok)
  // - 'never' : positions jamais saisies + statut unknown
  // - autre   : positions dont le statut match exactement (ex. 'ok' → toutes
  //             les positions actuellement à jour, jamais celles en retard).
  // Les onglets Bande/Rive n'affichent que les positions matchantes.
  const eligible = [];
  WEARPART_PIECES.forEach(p => {
    const matchingPositions = _wearPartPositionsOf(p).filter(pos => {
      const st = _wearPartPositionStatus(p.id, pos, machine);
      if(statusFilter === 'all')   return (st !== 'never' && st !== 'unknown');
      if(statusFilter === 'never') return (st === 'never' || st === 'unknown');
      return st === statusFilter;
    });
    if(matchingPositions.length === 0) return;
    const currentPos = getWearPartPos(p.id, machine);
    const forcedPos = (matchingPositions.indexOf(currentPos) !== -1) ? currentPos : matchingPositions[0];
    eligible.push({ piece: p, pos: forcedPos, matchingPositions });
  });
  if(eligible.length === 0) return '';  // section vide → caller n'affiche rien
  const cards = eligible.map(({piece: p, pos, matchingPositions}) => {
    // Source des références : code Intervention en base, match par label
    // (ex. "Changement couteaux bande" → carte Couteaux + Bande).
    const wpCode = _findWearPartCode(p.id, pos);
    const refTemps   = wpCode ? (wpCode.intervalle  || '') : '';
    const refMetrage = wpCode ? (wpCode.metrage_ref || '') : '';
    // Source du dernier changement : OPS_STATE (= les saisies "Nouvelle saisie"
    // faites dans l'app Maintenance), filtrées par label de code + machine.
    // Le métrage parcouru depuis cette date est calculé côté serveur via le
    // cache WEARPART_LAST_DATES_STATE (clé piece_pos).
    const lastDate = wpCode
      ? _lastInterventionForCode(wpCode.code, wpCode.label, machine, OPS_STATE.list)
      : null;
    const wpItem = (WEARPART_LAST_DATES_STATE.machine === machine)
      ? _getWearPartItem(p.id, pos)
      : null;
    const metrageSince = wpItem ? wpItem.metrage_since : null;
    const daysSince = _daysSinceFromIso(lastDate);
    // Pour la compat avec le bloc d'affichage plus bas (qui utilise wpItem.last_date)
    if(wpItem){ wpItem.last_date = lastDate; }
    // v2.4.23 : mise en exergue déclenchée UNIQUEMENT par le dépassement de
    // temps. Le métrage reste informatif (visible via anneau + valeur) mais
    // n'est plus considéré comme un critère de retard — cf. règle produit :
    // "le facteur retard est le temps, le métrage est un supplément visuel".
    const refDays   = _parseFrequenceDays(refTemps);
    const refMetres = _parseMetrageRef(refMetrage);
    const timeOver     = (refDays   != null && refDays   > 0 && daysSince    != null && daysSince    > refDays);
    const timeCritical = (timeOver && daysSince > refDays * 2);
    // metresOver garde son sens local (utilisé pour afficher un badge d'excès
    // à côté de la valeur Parcouru), mais ne déclenche plus la bordure rouge.
    const metresOver     = (refMetres != null && refMetres > 0 && metrageSince != null && metrageSince > refMetres);
    const metresCritical = (metresOver && metrageSince > refMetres * 2);
    let frameClsExtra = '';
    if(timeOver){
      frameClsExtra = ' is-overdue';
      if(timeCritical) frameClsExtra += ' is-overdue-critical';
    }
    // v2.6.1 : la bordure / le titre / le badge de retard prennent la couleur
    // exacte de l'anneau Temps (fin du decalage "bordure rouge / anneau jaune").
    // Plancher a 1.2 : entre 100 et 120% _ratioColor renvoie encore un
    // vert-jaune trop clair pour lire comme une bordure d'alerte.
    let sevStyle = '';
    if(timeOver && refDays != null && refDays > 0 && daysSince != null){
      const _sev = Math.max(1.2, daysSince / refDays);
      sevStyle = ' style="--wp-sev:' + _ratioColor(_sev)
        + ';--wp-sev-soft:' + _ratioColorRgba(_sev, .15)
        + ';--wp-sev-glow:' + _ratioColorRgba(_sev, .22) + '"';
    }
    let elapsedHtml = '';
    if(WEARPART_LAST_DATES_STATE.machine !== machine){
      elapsedHtml = '<span style="font-size:11px;color:var(--muted);font-style:italic">Chargement…</span>';
    } else if(daysSince == null){
      elapsedHtml = '<span style="font-size:11px;color:var(--muted);font-style:italic">Aucune saisie de maintenance pour ce code</span>';
    } else {
      const lbl = daysSince === 0 ? 'Aujourd\'hui'
                : daysSince === 1 ? 'Hier (1 jour)'
                : daysSince + ' jours';
      // Badge "Retard" si on dépasse la référence
      let retardBadge = '';
      if(refDays != null && refDays > 0 && daysSince > refDays){
        const over = daysSince - refDays;
        retardBadge = ' <span style="font-size:10px;font-weight:700;padding:2px 7px;border-radius:5px;background:rgba(248,113,113,.15);color:var(--danger,#f87171);text-transform:uppercase;letter-spacing:.3px">Retard ' + over + ' j</span>';
      }
      elapsedHtml =
        '<div style="display:flex;align-items:baseline;gap:6px;flex-wrap:wrap">' +
          '<span style="font-size:14px;color:var(--text);font-weight:600">' + escHtml(lbl) + '</span>' +
          '<span style="font-size:11px;color:var(--muted)">depuis le ' + escHtml(_fmtDateOnly(lastDate)) + '</span>' +
          retardBadge +
        '</div>';
    }
    const _b = (label, value) => {
      const active = (pos === value) ? ' active' : '';
      return '<button type="button" class="maint-wp-btn' + active + '" data-wp="' + escAttr(p.id) + '" data-pos="' + escAttr(value) + '">' + label + '</button>';
    };
    // v2.4.22 : ne montrer que les onglets des positions qui matchent le filtre.
    // Cas typique : Couteaux avec seulement Rive renseigné en filtre "Tous" →
    // le bouton Bande disparait (avant il était visible mais menait a une vue vide).
    // Si les 2 positions matchent, on montre les 2 (choix reel entre bande/rive).
    // Si une seule matche, seul son bouton apparait (agit comme un badge de position).
    // v229 : les onglets sont générés depuis les positions DÉCLARÉES sur la
    // pièce, plus depuis 'bande'/'rive' en dur. Une pièce à 3 positions rend
    // 3 onglets sans toucher au code.
    const tabsHtml = p.no_position
      ? ''
      : ('<div class="maint-wp-tabs" role="tablist" aria-label="Position">' +
           matchingPositions.map(mp =>
             _b(escHtml(mp.charAt(0).toUpperCase() + mp.slice(1)), mp)
           ).join('') +
         '</div>');
    return '<section class="maint-frame maint-wearpart' + frameClsExtra + '" data-wearpart="' + escAttr(p.id) + '" data-wearpart-pos="' + escAttr(pos) + '" data-maint-machine="' + escAttr(machine) + '"' + sevStyle + '>' +
      '<div class="maint-frame-head">' +
        '<div class="maint-frame-title">' + escHtml(p.label) + '</div>' +
        tabsHtml +
      '</div>' +
      (function(){
        // Layout :
        //   - Gauche : 2 sections empilées TEMPS (cyan) et MÉTRAGE (ambre),
        //     chacune avec barre verticale colorée à gauche pour identifier
        //     l'anneau correspondant.
        //   - Droite : 2 anneaux concentriques. Extérieur cyan = temps,
        //     intérieur ambre = métrage. Couleurs assorties aux sections.
        // v229 : la position est déclarée sur la pièce mais aucun code ne la
        // porte (code supprimé, ou pièce configurée avant ses codes). On
        // affichait deux sections vides et « aucun code intervention », sans
        // dire quoi faire. On remplace le corps par un état vide qui NOMME la
        // position concernée et donne le chemin de correction.
        if(!wpCode){
          const _posLbl = p.no_position
            ? escHtml(p.label)
            : escHtml(p.label) + ' · ' + escHtml(pos.charAt(0).toUpperCase() + pos.slice(1));
          return '<div class="maint-wp-body">' +
            '<div class="maint-wp-empty">' +
              '<div class="maint-wp-empty-title">Aucun code rattaché</div>' +
              '<div class="maint-wp-empty-txt">Aucune opération de maintenance n\'est rattachée à <strong>' +
                _posLbl + '</strong>. Cette position ne peut donc ni afficher d\'échéance, ni recevoir de saisie.</div>' +
              '<div class="maint-wp-empty-txt">Rattachez-en une depuis <strong>Paramètres → Maintenance</strong>, ' +
                'champ « Pièce d\'usure » du code concerné — ou retirez la position de la pièce ' +
                'si elle n\'a plus lieu d\'être.</div>' +
            '</div>' +
          '</div>';
        }
        const _refVal = (v) => v
          ? '<span class="val">' + escHtml(v) + '</span>'
          : '<span class="val muted">à compléter</span>';
        // Section TEMPS
        let lastSub = '';
        let lastVal;
        if(WEARPART_LAST_DATES_STATE.machine !== machine){
          lastVal = '<span class="val muted">Chargement…</span>';
        } else if(daysSince == null){
          lastVal = '<span class="val muted">jamais</span>';
        } else {
          const lbl = daysSince === 0 ? 'aujourd\'hui'
                    : daysSince === 1 ? 'hier'
                    : 'il y a ' + daysSince + ' j';
          lastVal = '<span class="val">' + escHtml(_fmtDateOnly(lastDate)) + '</span>';
          lastSub = '<span class="sub">' + escHtml(lbl) + '</span>';
        }
        let timeBadge = '';
        if(timeOver){
          const over = daysSince - refDays;
          timeBadge = '<span class="maint-wp-badge">Retard ' + over + ' j</span>';
        }
        // Section MÉTRAGE
        let mVal;
        if(WEARPART_LAST_DATES_STATE.machine !== machine){
          mVal = '<span class="val muted">Chargement…</span>';
        } else if(!wpItem || wpItem.last_date == null){
          mVal = '<span class="val muted">—</span>';
        } else if(metrageSince == null){
          mVal = '<span class="val muted">non disponible</span>';
        } else {
          mVal = '<span class="val">' + escHtml(_fmtMetres(metrageSince)) + '</span>';
        }
        // v2.4.23 : badge metrage renomme "Excès" (au lieu de "Retard") pour
        // eviter la connotation alarme — cf. règle produit metrage = supplement.
        let metresBadge = '';
        if(metresOver){
          const overM = metrageSince - refMetres;
          metresBadge = '<span class="maint-wp-badge maint-wp-badge-info">Excès +' + escHtml(_fmtMetres(overM)) + '</span>';
        }
        // Ratios pour les anneaux (null si pas de référence ou pas de donnée)
        const ratios = {
          temps:  (refDays   != null && refDays   > 0 && daysSince    != null) ? (daysSince    / refDays  ) : null,
          metres: (refMetres != null && refMetres > 0 && metrageSince != null) ? (metrageSince / refMetres) : null,
        };
        return '<div class="maint-wp-body">' +
          '<div class="maint-wp-info">' +
            // Section TEMPS (anneau extérieur)
            '<div class="maint-wp-sec temps">' +
              '<div class="maint-wp-sec-head">Temps</div>' +
              '<div class="maint-wp-row">' +
                '<span class="lbl">Référence</span>' + _refVal(refTemps) +
              '</div>' +
              '<div class="maint-wp-row">' +
                '<span class="lbl">Dernière intervention</span>' + lastVal + lastSub +
                timeBadge +
              '</div>' +
            '</div>' +
            // Section MÉTRAGE (anneau intérieur)
            '<div class="maint-wp-sec metres">' +
              '<div class="maint-wp-sec-head">Métrage</div>' +
              '<div class="maint-wp-row">' +
                '<span class="lbl">Référence</span>' + _refVal(refMetrage) +
              '</div>' +
              '<div class="maint-wp-row">' +
                '<span class="lbl">Parcouru</span>' + mVal +
                metresBadge +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="maint-wp-rings">' +
            _renderWearPartRings(ratios) +
          '</div>' +
        '</div>' +
      '</section>';
      })();
  }).join('');
  const nb = eligible.length;
  return '<div class="maint-group">' +
           '<div class="maint-group-head">' +
             '<h3 class="maint-group-title">Pièces d\'usure</h3>' +
             '<span class="maint-group-count">' + nb + ' pièce' + (nb > 1 ? 's' : '') + '</span>' +
           '</div>' +
           '<div class="maint-wearparts-stack">' + cards + '</div>' +
         '</div>';
}

// Convertit un nombre de jours en libellé standard (Hebdomadaire, Mensuel, etc.)
function _freqDaysToLabel(d){
  if(d == null) return 'Sans intervalle reconnu';
  const map = {
    1: 'Quotidien',
    7: 'Hebdomadaire',
    14: 'Bi-hebdomadaire',
    30: 'Mensuel',
    60: 'Bi-mensuel',
    90: 'Trimestriel',
    180: 'Semestriel',
    365: 'Annuel',
    730: 'Bi-annuel',
  };
  if(map[d]) return map[d];
  if(d < 7) return 'Tous les ' + d + ' jours';
  if(d % 7 === 0 && d <= 56) return 'Toutes les ' + (d/7) + ' semaines';
  if(d % 30 === 0 && d <= 720) return 'Tous les ' + (d/30) + ' mois';
  return 'Tous les ' + d + ' jours';
}

function renderMaintCards(){
  const grid = document.getElementById('maint-cards-grid');
  if(!grid) return;
  // Recharge les historiques de saisies depuis localStorage avant de calculer la
  // dernière intervention — couvre les cas multi-onglets (saisie dans un autre
  // onglet) et garantit qu'on lit toujours l'état le plus à jour.
  if(typeof loadOps === 'function') loadOps();
  if(typeof loadCtrl === 'function') loadCtrl();
  // Met à jour l'état actif des boutons machine
  const machine = getMaintMachine();
  document.querySelectorAll('.maint-machine-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-maint-machine') === machine);
  });
  // Filtre de catégorie (v178, élargi en v2.7.4) : « Tous », « Entretien » ou
  // « Interventions ». Les contrôles ne sont JAMAIS visibles ici. Les pièces
  // d'usure apparaissent sur « Interventions » et sur « Tous ».
  const catFilter = getMaintCatFilter();
  document.querySelectorAll('.maint-cat-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-maint-cat') === catFilter);
  });
  // v2.4.6 : nouveau filtre statut + choix du regroupement.
  const statusFilter = getMaintStatusFilter();
  const grouping = 'status';  // v2.4.6 : toggle retire, groupement fixe par statut
  _refreshMaintChipState();
  _refreshMaintCounters();
  // v2.7.4 : les pieces d'usure appartiennent a la categorie Interventions ;
  // elles doivent donc rester visibles quand on affiche les deux categories.
  const showWearParts = (catFilter === 'remplacements' || catFilter === 'all');
  // v2.4.25 : les pieces d'usure sont maintenant comptees + affichees dans
  // TOUS les filtres statut (leur logique de retard temps est integree au
  // systeme unifie overdue/soon/ok/never). _renderWearPartsGroup renvoie ''
  // si aucune position ne matche → section entiere (titre inclus) masquee
  // automatiquement.
  const wearPartsHtml = showWearParts
    ? _renderWearPartsGroup(machine, statusFilter) : '';
  // Récupère les IDs des codes utilisés par les cartes Pièces d'usure pour les
  // exclure des sections par intervalle (sinon les changements couteaux/
  // contre-couteaux apparaîtraient deux fois). Utile seulement quand la
  // section Pièces d'usure est affichée.
  const wearPartCodeIds = new Set();
  if(showWearParts){
    WEARPART_PIECES.forEach(p => {
      const positions = _wearPartPositionsOf(p);
      positions.forEach(pos => {
        const c = _findWearPartCode(p.id, pos);
        if(c && c.code) wearPartCodeIds.add(String(c.code));
      });
    });
  }
  // Filtre les codes avec periodique=OUI, exclus ceux déjà affichés dans la
  // section Pièces d'usure.
  const baseItems = (OPS_TYPES_STATE.list || []).filter(it => {
    if(!it.periodique) return false;
    if(wearPartCodeIds.has(String(it.id))) return false;
    const cat = it.categorie;
    // Les codes legacy 'interventions' et 'suivi' sont ranges avec 'entretien',
    // comme partout ailleurs dans le module.
    const isEntretien = (cat === 'controles' || cat === 'entretien' ||
                         cat === 'interventions' || cat === 'suivi');
    const isRemplacement = (cat === 'remplacements');
    if(catFilter === 'all') return isEntretien || isRemplacement;
    if(catFilter === 'entretien') return isEntretien;
    return isRemplacement;
  });
  if(!baseItems.length){
    grid.innerHTML = wearPartsHtml +
      '<div class="maint-frames-empty" style="margin-top:24px">Aucune opération périodique configurée. Ajoutez des codes avec Périodique=OUI dans Paramètres → Maintenance.</div>';
    return;
  }
  // Enrichit chaque item pour une machine donnée : freqDays, last, daysSince,
  // daysOverdue, status. On extrait dans une fonction pour pouvoir enrichir
  // plusieurs machines à la fois quand grouping === 'machine'.
  const enrichFor = (machineName) => baseItems.map(it => {
    const freqDays = _parseFrequenceDays(it.intervalle);
    const last = _lastInterventionFor(it.nom, machineName, OPS_STATE.list);
    let daysSince = null;
    if(last){
      try{
        const d = new Date(last);
        const today = new Date();
        const dMid = new Date(d.getFullYear(), d.getMonth(), d.getDate());
        const tMid = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        daysSince = Math.floor((tMid - dMid) / (1000 * 60 * 60 * 24));
      }catch(e){}
    }
    const daysOverdue = (freqDays != null && daysSince != null) ? (daysSince - freqDays) : null;
    const overdue = (daysOverdue != null && daysOverdue > 0);
    const status = _maintComputeStatus(freqDays, daysSince);
    return { it, machine: machineName, freqDays, last, daysSince, daysOverdue, overdue, status };
  });

  // Selon le regroupement, on enrichit sur 1 machine (statut/fréquence) ou
  // sur toutes les machines de la vue (regroupement par machine).
  let enriched;
  if(grouping === 'machine'){
    enriched = [];
    MAINT_HOME_MACHINES.forEach(m => { enriched = enriched.concat(enrichFor(m)); });
  } else {
    enriched = enrichFor(machine);
  }

  // Compteurs par statut, calculés sur l'ensemble non filtré.
  // Règle produit (v2.4.20) : "Tous" exclut les jamais saisi + unknown pour
  // dédensifier la vue ; ces opérations restent accessibles via le chip
  // "Jamais saisi" (qui remonte à la fois never et unknown, sémantiquement
  // proches — les deux = "pas de donnée exploitable").
  const statusCounts = { overdue: 0, soon: 0, ok: 0, never: 0, unknown: 0 };
  enriched.forEach(e => { statusCounts[e.status] = (statusCounts[e.status] || 0) + 1; });
  // v2.4.25 : en categorie "Remplacements", chaque POSITION de piece d'usure
  // est une operation independante, comptee dans son statut propre. On ajoute
  // les 5 buckets aux compteurs avant de calculer neverAndUnknown / all.
  if(showWearParts){
    const wpc = _wearPartsCounts(machine);
    statusCounts.overdue += wpc.overdue;
    statusCounts.soon    += wpc.soon;
    statusCounts.ok      += wpc.ok;
    statusCounts.never   += wpc.never;
    statusCounts.unknown += wpc.unknown;
  }
  const neverAndUnknown = statusCounts.never + statusCounts.unknown;
  // Le compteur "Tous" reflète ce qui sera VU (donc sans never/unknown).
  statusCounts.all = statusCounts.overdue + statusCounts.soon + statusCounts.ok;
  document.querySelectorAll('[data-status-count]').forEach(el => {
    const key = el.getAttribute('data-status-count');
    if(key === 'never'){
      // Le chip "Jamais saisi" englobe never + unknown.
      el.textContent = String(neverAndUnknown);
    } else {
      el.textContent = String(statusCounts[key] != null ? statusCounts[key] : 0);
    }
  });

  // Applique le filtre statut.
  const filtered = enriched.filter(e => {
    if(statusFilter === 'all')   return (e.status !== 'never' && e.status !== 'unknown');
    if(statusFilter === 'never') return (e.status === 'never' || e.status === 'unknown');
    return e.status === statusFilter;
  });

  if(!filtered.length){
    // v2.4.21 : si les pieces d'usure remplissent la section (wearPartsHtml
    // non vide), on renvoie juste wearPartsHtml sans message vide — sinon on
    // afficherait "aucune op à afficher" avec des cartes visibles en dessous.
    if(wearPartsHtml){
      grid.innerHTML = wearPartsHtml;
      return;
    }
    let emptyMsg;
    if(statusFilter === 'all' && neverAndUnknown > 0){
      // Cas particulier : il y a des ops "jamais saisi" mais on les a masquées.
      // Explique le pourquoi + bouton implicite (le chip "Jamais saisi" est
      // déjà là, il suffit de basculer).
      const s = neverAndUnknown > 1 ? 's' : '';
      emptyMsg = neverAndUnknown + ' opération' + s + ' jamais saisie' + s +
                 ' masquée' + s + ' — bascule sur le filtre « Jamais saisi » pour les voir.';
    } else {
      const msgs = {
        overdue: 'Aucune opération en retard. 🎉',
        soon:    'Aucune opération à faire dans les prochains jours.',
        ok:      'Aucune opération à jour à afficher.',
        never:   'Toutes les opérations ont déjà été saisies au moins une fois.',
        all:     'Aucune opération à afficher.',
      };
      emptyMsg = msgs[statusFilter] || msgs.all;
    }
    grid.innerHTML = wearPartsHtml +
      '<div class="maint-frames-empty" style="margin-top:24px">' + emptyMsg + '</div>';
    return;
  }

  // Poids de tri par statut pour le tri par urgence (Jamais tout en bas).
  const statusWeight = { overdue: 0, soon: 1, ok: 2, unknown: 3, never: 4 };

  // Groupement dynamique.
  const groups = new Map();
  filtered.forEach(e => {
    let key;
    if(grouping === 'status') key = e.status;
    else if(grouping === 'machine') key = e.machine;
    else /* freq */             key = (e.freqDays == null) ? 'unknown' : e.freqDays;
    if(!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  });

  // Tri des clés de groupe selon le mode.
  let sortedKeys;
  if(grouping === 'status'){
    sortedKeys = Array.from(groups.keys()).sort((a, b) => {
      return (statusWeight[a] != null ? statusWeight[a] : 99)
           - (statusWeight[b] != null ? statusWeight[b] : 99);
    });
  } else if(grouping === 'machine'){
    sortedKeys = MAINT_HOME_MACHINES.filter(m => groups.has(m));
  } else {
    // freq : plus petit intervalle en premier, 'unknown' à la fin
    sortedKeys = Array.from(groups.keys()).sort((a, b) => {
      if(a === 'unknown') return 1;
      if(b === 'unknown') return -1;
      return a - b;
    });
  }

  // Tri intra-groupe : par urgence globale (statut asc puis retard décroissant
  // puis alphabétique). "Jamais" est ainsi toujours en bas, sauf dans son
  // propre groupe où il ne reste que du "never" — dans ce cas c'est l'alpha
  // qui départage.
  groups.forEach((arr) => {
    arr.sort((a, b) => {
      const wa = statusWeight[a.status] != null ? statusWeight[a.status] : 99;
      const wb = statusWeight[b.status] != null ? statusWeight[b.status] : 99;
      if(wa !== wb) return wa - wb;
      const oa = a.daysOverdue || 0;
      const ob = b.daysOverdue || 0;
      if(ob !== oa) return ob - oa;
      return (a.it.nom || '').localeCompare(b.it.nom || '', 'fr');
    });
  });

  const _fmtDateTime = (iso) => {
    if(!iso) return '—';
    try{
      const d = new Date(iso);
      if(isNaN(d.getTime())) return '—';
      const pad = n => (n < 10 ? '0' + n : '' + n);
      return pad(d.getDate()) + '/' + pad(d.getMonth()+1) + '/' + d.getFullYear() +
             ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }catch(e){ return '—'; }
  };

  // Libellé de groupe selon le mode.
  const groupLabelFor = (key) => {
    if(grouping === 'status') return MAINT_STATUS_LABELS[key] || String(key);
    if(grouping === 'machine') return String(key);
    return (key === 'unknown') ? 'Sans intervalle reconnu' : _freqDaysToLabel(key);
  };

  // Construit le HTML : pièces d'usure d'abord (si applicable), puis groupes.
  let html = wearPartsHtml;
  sortedKeys.forEach(key => {
    const groupItems = groups.get(key);
    const groupLabel = groupLabelFor(key);
    const cards = groupItems.map(({it, machine: itemMachine, freqDays, last, daysSince, daysOverdue, overdue, status}) => {
      const catLabel = _maintCatLabelFront(it.categorie);
      let frameCls = 'maint-frame';
      if(overdue) frameCls += ' is-overdue';
      // On garde is-overdue-critical uniquement quand on n'est pas en groupement
      // par statut (sinon toute la section "En retard" scale, ce qui casse le layout).
      if(overdue && grouping !== 'status'){
        // Recalcule maxOverdue à la volée sur les items filtrés
        let maxOverdue = 0;
        filtered.forEach(e => { if(e.daysOverdue && e.daysOverdue > maxOverdue) maxOverdue = e.daysOverdue; });
        if(maxOverdue > 0 && daysOverdue === maxOverdue) frameCls += ' is-overdue-critical';
      }
      const lastHtml = last
        ? '<span class="maint-frame-stat-value">' + escHtml(_fmtDateTime(last)) + '</span>'
        : '<span class="maint-frame-stat-value muted">Jamais</span>';
      // Badge textuel de retard (bas de carte).
      let badgeCls = 'unknown';
      let badgeLbl = '';
      let detailLbl = '';
      if(daysOverdue != null){
        if(daysOverdue > 0){
          badgeCls = 'danger';
          badgeLbl = 'Retard ' + daysOverdue + ' j';
          detailLbl = daysSince + 'j depuis la dernière (intervalle ' + freqDays + 'j)';
        } else {
          badgeCls = 'ok';
          const remaining = -daysOverdue;
          badgeLbl = (status === 'soon' ? 'Bientôt · J-' + remaining : 'OK · J-' + remaining);
          detailLbl = remaining + ' j avant prochaine échéance';
        }
      } else if(daysSince != null && freqDays == null){
        badgeCls = 'unknown';
        badgeLbl = 'Intervalle non reconnu';
        detailLbl = 'Saisie il y a ' + daysSince + ' j';
      } else if(last == null && freqDays != null){
        badgeCls = 'warn';
        badgeLbl = 'Jamais saisi';
        detailLbl = 'Intervalle ' + freqDays + ' j';
      } else {
        badgeCls = 'unknown';
        badgeLbl = 'Aucune donnée';
      }
      // Barre de progression : identique à l'existant.
      let progressHtml = '';
      if(freqDays != null && freqDays > 0 && daysSince != null){
        const ratio = daysSince / freqDays;
        const pct = Math.max(0, Math.min(100, ratio * 100));
        const fillStyleExtra = ';background:' + _ratioColor(ratio);
        const pctLbl = Math.round(ratio * 100) + '%';
        progressHtml =
          '<div class="maint-frame-progress" title="' + escAttr(daysSince + ' jour(s) depuis la dernière intervention sur un intervalle de ' + freqDays + ' jour(s)') + '">' +
            '<div class="maint-frame-progress-track"><div class="maint-frame-progress-fill" style="width:' + pct.toFixed(1) + '%' + fillStyleExtra + '"></div></div>' +
            '<div class="maint-frame-progress-label">' +
              '<span>' + daysSince + ' j sur ' + freqDays + ' j</span>' +
              '<span class="pct">' + escHtml(pctLbl) + '</span>' +
            '</div>' +
          '</div>';
      } else if(freqDays != null && freqDays > 0 && daysSince == null){
        progressHtml =
          '<div class="maint-frame-progress is-empty" title="' + escAttr('Aucune saisie pour cette opération sur cette machine. Intervalle prévu : ' + freqDays + ' jour(s).') + '">' +
            '<div class="maint-frame-progress-track"><div class="maint-frame-progress-fill" style="width:0%"></div></div>' +
            '<div class="maint-frame-progress-label">' +
              '<span>—</span>' +
              '<span class="pct">0 / ' + freqDays + ' j</span>' +
            '</div>' +
          '</div>';
      }
      const catCls = _maintCatCssFront(it.categorie);
      const nivNum = parseInt(it.niveau, 10) || 1;
      // Étiquette machine visible uniquement quand on regroupe par statut/fréquence
      // et qu'on affiche plusieurs machines simultanément (grouping=machine gère
      // ça via le titre du groupe).
      const machineChip = (grouping === 'machine')
        ? ''
        : '<span class="maint-frame-cat-pill" style="background:var(--bg);border-color:var(--border);color:var(--muted)">' + escHtml(itemMachine) + '</span>';
      return '<section class="' + frameCls + '" data-status="' + status + '" data-maint-code="' + escAttr(it.id) + '" data-maint-machine="' + escAttr(itemMachine) + '">' +
        '<div class="maint-frame-head">' +
          '<div class="maint-frame-title">' + escHtml(it.nom) + '</div>' +
          '<div class="maint-frame-badges">' +
            '<span class="maint-frame-cat-pill ' + catCls + '">' + escHtml(catLabel) + '</span>' +
            '<span class="niv-badge" data-niv="' + nivNum + '">N' + nivNum + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="maint-frame-stats" style="grid-template-columns:1fr">' +
          '<div class="maint-frame-stat">' +
            '<span class="maint-frame-stat-label">Dernière intervention</span>' +
            lastHtml +
          '</div>' +
        '</div>' +
        progressHtml +
        '<div class="maint-frame-retard">' +
          '<span class="maint-frame-retard-badge ' + badgeCls + '">' + escHtml(badgeLbl) + '</span>' +
          (detailLbl ? '<span class="maint-frame-retard-detail">' + escHtml(detailLbl) + '</span>' : '') +
        '</div>' +
      '</section>';
    }).join('');
    html += '<div class="maint-group">' +
              '<div class="maint-group-head">' +
                '<h3 class="maint-group-title">' + escHtml(groupLabel) + '</h3>' +
                '<span class="maint-group-count">' + groupItems.length + ' opération' + (groupItems.length > 1 ? 's' : '') + '</span>' +
              '</div>' +
              '<div class="maint-frames-grid">' + cards + '</div>' +
            '</div>';
  });
  grid.innerHTML = html;
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
// ── Maintenance préventive : fréquence → jours, retard d'intervention ──
function _normalizeFreqStr(s){
  return String(s || '').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .trim();
}
function _parseFrequenceDays(freq){
  const s = _normalizeFreqStr(freq);
  if(!s) return null;
  // Patterns mots-clés courants
  if(/quotid|journal|daily/.test(s)) return 1;
  if(/(bi[\s-]?hebdo|14\s*j|2\s*sem)/.test(s)) return 14;
  if(/hebdo|weekly|7\s*j/.test(s)) return 7;
  if(/(bi[\s-]?mensuel|2\s*mois)/.test(s)) return 60;
  if(/(trimestr|quarter|3\s*mois|90\s*j)/.test(s)) return 90;
  if(/(semestr|6\s*mois|180\s*j)/.test(s)) return 180;
  if(/(bi[\s-]?annuel|biennal|2\s*ans?|730\s*j)/.test(s)) return 730;
  if(/(annuel|annual|yearly|365\s*j|1\s*an)/.test(s)) return 365;
  if(/mensuel|monthly|30\s*j/.test(s)) return 30;
  // Patterns numériques explicites
  const m1 = s.match(/(\d+)\s*j(?:our)?/);
  if(m1) return parseInt(m1[1], 10);
  const m2 = s.match(/(\d+)\s*sem/);
  if(m2) return parseInt(m2[1], 10) * 7;
  const m3 = s.match(/(\d+)\s*mois/);
  if(m3) return parseInt(m3[1], 10) * 30;
  const m4 = s.match(/(\d+)\s*an/);
  if(m4) return parseInt(m4[1], 10) * 365;
  return null; // fréquence non interprétable
}
function _opOverdueInfo(opType){
  // → { overdue: bool, daysOverdue: number|null, daysSince: number|null, freqDays: number|null }
  const freqDays = _parseFrequenceDays(opType && opType.frequence);
  const dt = opType && opType.derniere_intervention;
  if(!dt) return { overdue:false, daysOverdue:null, daysSince:null, freqDays };
  const last = new Date(dt + 'T00:00:00');
  if(isNaN(last.getTime())) return { overdue:false, daysOverdue:null, daysSince:null, freqDays };
  const today = new Date();
  const todayMid = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const daysSince = Math.floor((todayMid - last) / (1000 * 60 * 60 * 24));
  if(freqDays == null) return { overdue:false, daysOverdue:null, daysSince, freqDays };
  const daysOverdue = daysSince - freqDays;
  return { overdue: daysOverdue > 0, daysOverdue, daysSince, freqDays };
}
function _fmtDateFr(iso){
  if(!iso) return '';
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if(!m) return iso;
  return m[3] + '/' + m[2] + '/' + m[1];
}
// Conservé en no-op pour rétro-compat : la "Dernière intervention" est désormais
// dérivée automatiquement des saisies réelles (OPS_STATE / CTRL_STATE), filtrées
// par la machine sélectionnée au-dessus de chaque catalogue.
function updateLastIntervention(id, val){ /* derive: see _lastInterventionFor */ }
function renderOpsTypes(){
  refreshOpsTypeSelect();
  refreshOpsFiltersOptions();
  const tbodies = document.querySelectorAll('.js-cat-tbody');
  if(!tbodies.length) return;
  // Synchronise les selects machine sur la valeur courante
  const machine = getOpsCatMachine();
  document.querySelectorAll('.js-ops-cat-machine').forEach(sel => {
    if(sel.value !== machine) sel.value = machine;
  });
  // Calcule la dernière intervention par code, filtrée par machine
  OPS_TYPES_STATE.list.forEach(t => {
    t.derniere_intervention = _lastInterventionFor(t.nom, machine, OPS_STATE.list);
  });
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
  // Partitionner : retards d'abord (les plus en retard en premier), puis le reste selon le tri courant
  const withInfo = sorted.map(t => ({ t, info: _opOverdueInfo(t) }));
  const overdueRows = withInfo.filter(x => x.info.overdue)
    .sort((a,b) => (b.info.daysOverdue||0) - (a.info.daysOverdue||0));
  const normalRows = withInfo.filter(x => !x.info.overdue);
  const finalRows = overdueRows.concat(normalRows);
  let html;
  if(!finalRows.length){
    html = '<tr><td colspan="6" class="ops-empty">Aucune opération périodique. Ajoutez des codes avec Périodique=OUI dans Paramètres → Maintenance.</td></tr>';
  } else {
    html = finalRows.map(({t, info}) => {
      const rowCls = info.overdue ? ' class="row-overdue"' : '';
      const dt = t.derniere_intervention || '';
      let statusHtml = '';
      if(info.overdue){
        statusHtml = '<span class="last-intervention-status overdue" title="' + escAttr('Retard de ' + info.daysOverdue + ' jour' + (info.daysOverdue>1?'s':'') + ' (' + info.daysSince + 'j depuis la dernière, fréquence ' + info.freqDays + 'j)') + '">⚠ Retard ' + info.daysOverdue + ' j</span>';
      } else if(info.daysSince != null && info.freqDays != null){
        const remaining = info.freqDays - info.daysSince;
        statusHtml = '<span class="last-intervention-status ok" title="Prochaine intervention recommandée dans ' + remaining + ' jour' + (remaining>1?'s':'') + '">✓ OK (J-' + Math.max(0, remaining) + ')</span>';
      } else if(!dt){
        statusHtml = '<span class="last-intervention-status unknown">Jamais enregistré</span>';
      }
      // Icône SVG rouge (triangle "attention") affichée au début de la cellule
      // Nom quand l'opération est en retard. Le tooltip détaille le nb de jours.
      const overdueIcon = info.overdue
        ? '<span class="ops-row-warn-ico" title="Intervention en retard de ' + info.daysOverdue + ' jour' + (info.daysOverdue > 1 ? 's' : '') + '" aria-label="En retard">'
          + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
          + '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
          + '<line x1="12" y1="9" x2="12" y2="13"/>'
          + '<line x1="12" y1="17" x2="12.01" y2="17"/>'
          + '</svg></span>'
        : '';
      // Badge texte "En retard" conservé en bout de ligne pour la lisibilité
      const overdueBadge = info.overdue
        ? '<span class="row-overdue-badge" title="Intervention en retard">En retard ' + info.daysOverdue + ' j</span>'
        : '';
      const catLabel = _maintCatLabelFront(t.categorie);
      const catCls = _maintCatCssFront(t.categorie);
      // dt est ici une date ISO (datetime) issue de la dernière saisie sur la
      // machine sélectionnée. On l'affiche au format JJ/MM/AAAA HH:MM.
      let dtDisplay = '—';
      if(dt){
        try{
          const d = new Date(dt);
          if(!isNaN(d.getTime())){
            const pad = n => (n < 10 ? '0' + n : '' + n);
            dtDisplay = pad(d.getDate()) + '/' + pad(d.getMonth()+1) + '/' + d.getFullYear()
                      + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
          }
        }catch(e){}
      }
      // Intervalle de temps : vide pour les non-périodiques (Interventions one-shot)
      const intervalleCell = t.periodique
        ? (t.intervalle ? escHtml(t.intervalle) : '<span style="color:var(--muted);font-style:italic">À compléter</span>')
        : '<span style="color:var(--muted)">—</span>';
      // Ligne entière cliquable (double-clic) pour ouvrir la modale d'édition
      // des détails (notes libres, stockées en localStorage par code).
      return '<tr' + rowCls + ' data-ops-type-row="' + escAttr(t.id) + '" style="cursor:pointer" title="Double-cliquez pour voir et modifier les détails">' +
        '<td>' + overdueIcon + '<strong style="color:var(--text);vertical-align:middle">' + escHtml(t.nom) + '</strong>' + overdueBadge + '</td>' +
        '<td><span class="niv-badge" data-niv="' + t.niveau + '">N' + t.niveau + '</span></td>' +
        '<td><span class="op-pill ' + catCls + '">' + escHtml(catLabel) + '</span></td>' +
        '<td>' + intervalleCell + '</td>' +
        '<td class="col-last-intervention">' +
          '<div class="last-intervention-wrap" style="display:flex;flex-direction:column;gap:4px">' +
            '<span style="font-size:13px;color:var(--text)">' + escHtml(dtDisplay) + '</span>' +
            statusHtml +
          '</div>' +
        '</td>' +
        '<td class="col-actions"></td>' +
      '</tr>';
    }).join('');
  }
  tbodies.forEach(tb => { tb.innerHTML = html; });
  // Double-clic sur une ligne -> modale d'édition des détails (notes locales)
  document.querySelectorAll('tr[data-ops-type-row]').forEach(tr => {
    tr.addEventListener('dblclick', () => {
      const code = tr.getAttribute('data-ops-type-row');
      if(code) openOpsTypeDetailsModal(code);
    });
  });
  const n = OPS_TYPES_STATE.list.length;
  const lbl = n + ' opération' + (n > 1 ? 's' : '');
  document.querySelectorAll('.js-cat-count').forEach(c => { c.textContent = lbl; });
}

// =========================================================================
// Historique des contrôles
// =========================================================================
const CTRL_STORAGE_KEY = 'mysifa_maint_controles_v1';
const CTRL_EXTRA_KEY = 'mysifa_ctrl_show_extra_v1';
const CTRL_STATE = { sortBy: 'date_saisie', sortDir: 'desc', list: [], acks: [], alerts_meta: {}, pointFilters: {}, page: 0, pageSize: 50 };
// v2.2.27 : navigation pagination
function ctrlPageGo(delta){
  CTRL_STATE.page = (CTRL_STATE.page || 0) + delta;
  if(CTRL_STATE.page < 0) CTRL_STATE.page = 0;
  if(typeof renderCtrl === 'function') renderCtrl();
}
function ctrlResetPage(){ CTRL_STATE.page = 0; }

// Toggle "Colonnes produit" : par defaut off, persistance localStorage.
function getShowExtraCols(){
  try { return localStorage.getItem(CTRL_EXTRA_KEY) === '1'; } catch(e){ return false; }
}
function setShowExtraCols(v){
  try { localStorage.setItem(CTRL_EXTRA_KEY, v ? '1' : '0'); } catch(e){}
}
function updateExtraToggleUI(){
  const on = getShowExtraCols();
  const state = document.getElementById('ctrl-extra-toggle-state');
  const btn = document.getElementById('ctrl-extra-toggle');
  if(state) state.textContent = on ? 'ON' : 'OFF';
  if(btn) btn.classList.toggle('ctrl-extra-toggle-on', on);
}
function toggleExtraCols(){
  setShowExtraCols(!getShowExtraCols());
  updateExtraToggleUI();
  if(typeof renderCtrl === 'function') renderCtrl();
}

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

function _formatAckComment(ack){
  const parts = [];
  if(ack.responses && typeof ack.responses === 'object'){
    Object.entries(ack.responses).forEach(([k, v]) => {
      if(Array.isArray(v)){
        if(v.length) parts.push(v.join(', '));
      } else if (v != null && String(v).trim() !== ''){
        parts.push(String(v));
      }
    });
  }
  if(ack.comment){ parts.push((parts.length ? '« ' + ack.comment + ' »' : ack.comment)); }
  return parts.join(' · ');
}

async function loadCtrlAcks(){
  try{
    const r = await fetch('/api/maintenance/alert-acks', { credentials: 'same-origin' });
    if(!r.ok){ CTRL_STATE.acks = []; return; }
    const data = await r.json();
    const items = Array.isArray(data && data.items) ? data.items : [];
    CTRL_STATE.acks = items.map(a => ({
      id: 'ack-' + a.id,
      machine: a.machine || '',
      operateur: a.operateur || '',
      type: a.alert_nom || '',
      commentaire: _formatAckComment(a),
      date_saisie: a.ack_at,
      _source: 'alert',
      _maint_code: a.linked_maint_code || '',
      _alert_id: a.alert_id,
      _responses: a.responses || {},
      _raw_comment: a.comment || '',
      _no_dossier: a.no_dossier || '',
      _dossier_info: a.dossier_info || null,
    }));
    CTRL_STATE.alerts_meta = data.alerts_meta || {};
    CTRL_STATE.known_alerts = Array.isArray(data.known_alerts) ? data.known_alerts : [];
  } catch(e){ CTRL_STATE.acks = []; }
  if(typeof renderCtrl === 'function') renderCtrl();
  if(typeof renderCtrlTypes === 'function') renderCtrlTypes();
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
  // Aligne le sélecteur du catalogue sur la machine de la saisie et re-render
  // pour que la "Dernière intervention" reflète immédiatement la nouvelle saisie.
  try{ localStorage.setItem(CTRL_CAT_MACHINE_KEY, machine); }catch(e){}
  // Aligne aussi la vue Maintenance (cartes) — un contrôle périodique fait partie
  // des cartes de la vue principale.
  try{ localStorage.setItem(MAINT_MACHINE_KEY, machine); }catch(e){}
  if(typeof renderCtrlTypes === 'function') renderCtrlTypes();
  if(typeof renderMaintCards === 'function') renderMaintCards();
  closeCtrlModal();
  showToast('Contrôle enregistré.', 'info');
}
function deleteCtrl(id){
  // v2.5.12 : modale MySifa au lieu du confirm() natif.
  const list = (typeof CTRL_STATE !== 'undefined' && CTRL_STATE && Array.isArray(CTRL_STATE.list)) ? CTRL_STATE.list : [];
  const c = list.find(x => x.id === id) || {};
  const dateFR = c.date_saisie ? _fmtDateFRHistoric(c.date_saisie) : '';
  const summary =
    '<div style="font-size:14px;font-weight:700;color:var(--text)">' + escHtml(c.type || 'Contr\u00f4le') + '</div>' +
    '<div style="font-size:12px;color:var(--muted);margin-top:4px">' +
      (c.machine ? escHtml(c.machine) : '') +
      (dateFR ? (c.machine ? ' \u00b7 ' : '') + escHtml(dateFR) : '') +
    '</div>';
  _openHistoryDeleteModal({
    title: 'Supprimer ce contr\u00f4le ?',
    summary: summary,
    warning: 'Cette action est d\u00e9finitive.',
    confirmLabel: 'Supprimer',
    onConfirm: () => {
      CTRL_STATE.list = CTRL_STATE.list.filter(x => x.id !== id);
      saveCtrl();
      renderCtrl();
      if(typeof showToast === 'function') showToast('Contr\u00f4le supprim\u00e9.', 'info');
    },
  });
}

function deleteAck(prefixedId){
  // v2.5.12 : remplace le confirm() natif par une modale MySifa.
  const m = String(prefixedId).match(/^ack-(\d+)$/);
  if(!m){ showToast('Identifiant invalide.', 'danger'); return; }
  const ackId = m[1];
  // Retrouve la ligne pour construire un resume lisible dans la modale.
  const list = (typeof CTRL_STATE !== 'undefined' && CTRL_STATE && Array.isArray(CTRL_STATE.list)) ? CTRL_STATE.list : [];
  const c = list.find(x => x.id === prefixedId) || {};
  const dateFR = c.date_saisie ? _fmtDateFRHistoric(c.date_saisie) : '';
  const summary =
    '<div style="font-size:14px;font-weight:700;color:var(--text)">' + escHtml(c.type || 'Alerte') + '</div>' +
    '<div style="font-size:12px;color:var(--muted);margin-top:4px">' +
      (c.machine ? escHtml(c.machine) : '') +
      (dateFR ? (c.machine ? ' \u00b7 ' : '') + escHtml(dateFR) : '') +
      (c.operateur ? ' \u00b7 par ' + escHtml(c.operateur) : '') +
    '</div>';
  _openHistoryDeleteModal({
    title: 'Supprimer cette ligne d\'historique ?',
    summary: summary,
    warning: 'Elle restera compt\u00e9e pour le dernier acquittement de l\'alerte associ\u00e9e si c\'est la plus r\u00e9cente.',
    confirmLabel: 'Supprimer',
    onConfirm: async () => {
      const r = await fetch('/api/maintenance/alert-acks/' + ackId, { method: 'DELETE', credentials: 'same-origin' });
      if(!r.ok){
        let msg = 'Suppression refus\u00e9e';
        try { const j = await r.json(); msg = j.detail || msg; } catch(e){}
        showToast(msg, 'danger');
        throw new Error(msg);
      }
      showToast('Ligne supprim\u00e9e.', 'info');
      await loadCtrlAcks();
    },
  });
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
// v2.3.29 : mémorise la préférence "afficher les fermetures auto"
// (par défaut masquées — elles polluent l'historique quotidien).
// v2.3.35 : localStorage = source de vérité (plus de checkbox DOM), et un
// toggle stylé dans le header "Historique des alertes" gère l'état.
const CTRL_SHOW_AUTO_KEY = 'mysifa_ctrl_show_auto_close';
function ctrlLoadShowAutoClose(){
  try { return localStorage.getItem(CTRL_SHOW_AUTO_KEY) === '1'; }
  catch(_) { return false; }
}
function ctrlSaveShowAutoClose(v){
  try { localStorage.setItem(CTRL_SHOW_AUTO_KEY, v ? '1' : '0'); } catch(_) {}
}
function updateAutoCloseToggleUI(){
  const on = ctrlLoadShowAutoClose();
  const state = document.getElementById('ctrl-autoclose-toggle-state');
  const btn = document.getElementById('ctrl-autoclose-toggle');
  if(state) state.textContent = on ? 'ON' : 'OFF';
  if(btn) btn.classList.toggle('ctrl-extra-toggle-on', on);
}
function toggleAutoClose(){
  ctrlSaveShowAutoClose(!ctrlLoadShowAutoClose());
  updateAutoCloseToggleUI();
  ctrlResetPage();
  if(typeof renderCtrl === 'function') renderCtrl();
}
function ctrlIsAutoClose(c){
  const raw = (c && c._raw_comment) || '';
  // Match tolérant : "Fermée auto" avec ou sans accents / espaces autour
  return /^\s*Ferm[eé]e\s+auto\b/i.test(raw);
}

// v2.3.37 : filtrage auto — plus de bouton Filtrer. Chaque champ appelle
// ctrlAutoFilter() à onchange.
// v2.3.38 : toast retiré à la demande de l'utilisateur (le re-render
// de la table est déjà un feedback suffisant).
function ctrlAutoFilter(opts){
  opts = opts || {};
  ctrlResetPage();
  if(opts.resetPoints) resetPointFilters();
  if(typeof renderCtrl === 'function') renderCtrl();
}

function getCtrlFilters(){
  const v = id => (document.getElementById(id)?.value || '').trim();
  return {
    type:      v('filt-controles-type'),
    operateur: v('filt-controles-operateur'),
    machine:   v('filt-controles-machine'),
    dateFrom:  v('filt-controles-date-from'),
    dateTo:    v('filt-controles-date-to'),
    conformite:v('filt-controles-conformite'),
    // v2.3.35 : lu directement depuis localStorage (plus de checkbox DOM)
    showAuto:  ctrlLoadShowAutoClose(),
  };
}
function resetCtrlFilters(){
  ['type','operateur','machine','date-from','date-to','conformite'].forEach(k => {
    const el = document.getElementById('filt-controles-' + k);
    if(el) el.value = '';
  });
  // v2.3.37 : passe par ctrlAutoFilter pour toast + reset page
  ctrlAutoFilter({resetPoints:true});
}
function applyCtrlDatePreset(key){
  const p = maintDatePresets()[key];
  if(!p) return;
  const from = document.getElementById('filt-controles-date-from');
  const to   = document.getElementById('filt-controles-date-to');
  if(from) from.value = p.from;
  if(to)   to.value   = p.to;
  // v2.3.37 : les chips preset déclenchent aussi le toast
  ctrlAutoFilter();
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
function _displayType(entry){
  // Nom canonique d'un contrôle pour l'UI : on préfère le label du code
  // maintenance (stable, lisible) plutôt que le nom prefixé de l'alerte auto
  // ("Contrôle : XX – label"). Fallback sur entry.type pour les alertes
  // manuelles sans code lié et pour les contrôles saisis manuellement.
  if(!entry) return '';
  if(entry._source === 'alert' && entry._maint_code){
    const codeItem = CTRL_TYPES_STATE.list.find(t => String(t.id) === String(entry._maint_code));
    if(codeItem && codeItem.nom) return codeItem.nom;
  }
  return entry.type || '';
}

function refreshCtrlFiltersOptions(){
  const typeSel = document.getElementById('filt-controles-type');
  const opeSel  = document.getElementById('filt-controles-operateur');
  if(typeSel){
    const cur = typeSel.value;
    const setTypes = new Set();
    // Base : labels du catalogue de codes (même sans saisie encore)
    CTRL_TYPES_STATE.list.forEach(t => { if(t.nom) setTypes.add(t.nom); });
    // Ajoute : chaque entrée (manuelle ou ack) via son nom d'affichage canonique
    // v2.2.18 : CTRL_STATE.list dropped — types alimentés par acks + known_alerts uniquement
    (CTRL_STATE.acks || []).forEach(a => { const n = _displayType(a); if(n) setTypes.add(n); });
    // Ajoute : les alertes autonomes (sans linked_maint_code) même sans ack.
    // Les alertes auto-générées à partir d'un code maintenance (préfixe
    // "Contrôle : XX – …") ne sont PAS ajoutées ici — le label du code est
    // déjà présent via CTRL_TYPES_STATE, ce qui créerait un doublon.
    (CTRL_STATE.known_alerts || []).forEach(a => {
      if(!a || !a.nom) return;
      if(a.linked_maint_code) return;  // évite le doublon avec le label du code
      setTypes.add(a.nom);
    });
    const types = Array.from(setTypes).sort((a,b) => a.localeCompare(b, 'fr'));
    typeSel.innerHTML = '<option value="">Tous les types</option>' +
      types.map(n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>').join('');
    if(cur && types.includes(cur)) typeSel.value = cur;
  }
  if(opeSel){
    const cur = opeSel.value;
    const opes = Array.from(new Set((CTRL_STATE.acks || []).map(c => c.operateur).filter(Boolean))).sort((a,b) => a.localeCompare(b, 'fr'));
    opeSel.innerHTML = '<option value="">Tous les opérateurs</option>' +
      opes.map(n => '<option value="' + escAttr(n) + '">' + escHtml(n) + '</option>').join('');
    if(cur && opes.includes(cur)) opeSel.value = cur;
  }
}
function _getCurrentTypeChecklistItems(){
  const sel = document.getElementById('filt-controles-type');
  const t = (sel && sel.value || '').trim();
  if(!t) return null;
  // Trouve le premier ack dont le nom canonique matche
  const ackMatch = (CTRL_STATE.acks || []).find(a => _displayType(a) === t);
  if(!ackMatch || ackMatch._alert_id == null) return null;
  const meta = (CTRL_STATE.alerts_meta || {})[String(ackMatch._alert_id)];
  if(!meta || !Array.isArray(meta.checklist_items)) return null;
  return meta.checklist_items;
}

function renderPointFilters(){
  const row = document.getElementById('ctrl-point-filters-row');
  const box = document.getElementById('ctrl-point-filters-inputs');
  if(!row || !box) return;
  const items = _getCurrentTypeChecklistItems();
  if(!items || !items.length){
    row.style.display = 'none';
    box.innerHTML = '';
    return;
  }
  row.style.display = '';
  const html = items.map((it, idx) => {
    const label = escHtml(it.label || ('Point ' + (idx+1)));
    if(it.type === 'value'){
      const cur = CTRL_STATE.pointFilters[idx] || {};
      const minV = (cur.min != null) ? cur.min : '';
      const maxV = (cur.max != null) ? cur.max : '';
      const unit = it.unit ? ' ' + escHtml(it.unit) : '';
      return '<div class="pf-item">'
        + '<span class="pf-label">' + label + unit + '</span>'
        + '<input type="number" step="any" class="pf-input pf-num" placeholder="min" value="' + escAttr(String(minV)) + '" onchange="_onPointFilterChange(' + idx + ', \'min\', this.value)">'
        + '<input type="number" step="any" class="pf-input pf-num" placeholder="max" value="' + escAttr(String(maxV)) + '" onchange="_onPointFilterChange(' + idx + ', \'max\', this.value)">'
        + '</div>';
    }
    // choice
    const cur = CTRL_STATE.pointFilters[idx] || {};
    const curVal = cur.value || '';
    const responses = Array.isArray(it.responses) ? it.responses : [];
    const opts = '<option value="">Toutes</option>' +
      responses.map(r => '<option value="' + escAttr(r) + '"' + (r === curVal ? ' selected' : '') + '>' + escHtml(r) + '</option>').join('');
    return '<div class="pf-item">'
      + '<span class="pf-label">' + label + '</span>'
      + '<select class="pf-input" onchange="_onPointFilterChange(' + idx + ', \'value\', this.value)">' + opts + '</select>'
      + '</div>';
  }).join('');
  box.innerHTML = html;
}

function _onPointFilterChange(idx, key, value){
  if(!CTRL_STATE.pointFilters[idx]) CTRL_STATE.pointFilters[idx] = {};
  if(value === '' || value == null){
    delete CTRL_STATE.pointFilters[idx][key];
    if(Object.keys(CTRL_STATE.pointFilters[idx]).length === 0){
      delete CTRL_STATE.pointFilters[idx];
    }
  } else {
    CTRL_STATE.pointFilters[idx][key] = value;
  }
  renderCtrl();
}

function resetPointFilters(){
  CTRL_STATE.pointFilters = {};
  renderCtrl();
}

function _matchPointFilters(ackRow){
  // ackRow n'est filtré que si _source === 'alert' avec des _responses.
  // Les entrées manuelles passent toujours à travers (pas de réponses structurées).
  if(!ackRow || ackRow._source !== 'alert') return true;
  const items = _getCurrentTypeChecklistItems();
  if(!items) return true;
  const filters = CTRL_STATE.pointFilters || {};
  const responses = ackRow._responses || {};
  for(const k of Object.keys(filters)){
    const idx = parseInt(k, 10);
    const filt = filters[k] || {};
    const it = items[idx];
    if(!it) continue;
    const r = responses[String(idx)];
    if(it.type === 'value'){
      const num = (r != null && r !== '') ? parseFloat(r) : NaN;
      if(filt.min != null && filt.min !== ''){
        const mn = parseFloat(filt.min);
        if(!isNaN(mn) && (isNaN(num) || num < mn)) return false;
      }
      if(filt.max != null && filt.max !== ''){
        const mx = parseFloat(filt.max);
        if(!isNaN(mx) && (isNaN(num) || num > mx)) return false;
      }
    } else {
      // choice : la réponse cochée doit inclure la valeur filtrée
      if(filt.value != null && filt.value !== ''){
        const arr = Array.isArray(r) ? r : (r != null ? [String(r)] : []);
        if(!arr.includes(filt.value)) return false;
      }
    }
  }
  return true;
}

function openAckDetail(prefixedId){
  const ack = (CTRL_STATE.acks || []).find(a => a.id === prefixedId);
  if(!ack) return;
  const meta = (CTRL_STATE.alerts_meta || {})[String(ack._alert_id)] || {};
  const items = Array.isArray(meta.checklist_items) ? meta.checklist_items : [];
  const responses = ack._responses || {};

  // Rendu de la checklist en mode lecture seule (cases pré-cochées / valeur saisie)
  let checklistHtml = '';
  if(items.length){
    checklistHtml = '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Points de contrôle</label>'
      + '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:10px">'
      +   items.map((it, idx) => {
            const r = responses[String(idx)];
            if(it.type === 'value'){
              const val = (r != null && r !== '') ? String(r) : '';
              const unit = it.unit ? '<span style="font-size:12px;color:var(--text2);font-weight:500;min-width:24px">' + escHtml(it.unit) + '</span>' : '';
              return '<div class="ta-cl-item" data-type="value">'
                + '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">' + escHtml(it.label || '') + '</div>'
                + '<div style="display:flex;align-items:center;gap:8px">'
                +   '<input type="text" disabled value="' + escAttr(val) + '" style="flex:1;padding:6px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;box-sizing:border-box;opacity:.85">'
                +   unit
                + '</div>'
                + '</div>';
            }
            // choice : cases à cocher pré-remplies selon les réponses stockées
            const selected = Array.isArray(r) ? r : (r != null ? [String(r)] : []);
            // On n'a pas la liste complète des réponses possibles dans l'ack ;
            // on n'affiche donc que les réponses réellement cochées (comme des
            // pills sélectionnées). C'est fidèle à la donnée enregistrée.
            const respHtml = selected.length
              ? selected.map(s => '<label class="ta-chip"><input type="checkbox" disabled checked><span>' + escHtml(s) + '</span></label>').join('')
              : '<span style="font-size:12px;color:var(--muted);font-style:italic">Aucune réponse cochée</span>';
            // Si "Autre" est coché et qu'une précision a été saisie, on l'affiche.
            const otherTxt = responses[String(idx) + '_other'];
            const otherHtml = (otherTxt != null && String(otherTxt).trim() !== '')
              ? '<div style="margin-top:6px;padding:6px 10px;border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 6px 6px 0;font-size:12px;color:var(--text2);white-space:pre-wrap">' + escHtml(String(otherTxt)) + '</div>'
              : '';
            // v2.5.21 : commentaire obligatoire déclenché par une réponse COM.
            // Liseré rouge et libellé explicite pour le distinguer d'une simple
            // précision « Autre » — c'est la justification d'un cas signalé.
            const comTxt = responses[String(idx) + '_comment'];
            const comHtml = (comTxt != null && String(comTxt).trim() !== '')
              ? '<div style="margin-top:6px;padding:6px 10px;border-left:3px solid var(--danger);background:rgba(220,38,38,.07);border-radius:0 6px 6px 0">'
                + '<div style="font-size:10px;font-weight:700;color:var(--danger);text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px">Commentaire obligatoire</div>'
                + '<div style="font-size:12px;color:var(--text2);white-space:pre-wrap">' + escHtml(String(comTxt)) + '</div>'
                + '</div>'
              : '';
            return '<div class="ta-cl-item" data-type="choice">'
              + '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">' + escHtml(it.label || '') + '</div>'
              + '<div style="display:flex;flex-wrap:wrap;gap:5px">' + respHtml + '</div>'
              + otherHtml
              + comHtml
              + '</div>';
          }).join('')
      + '</div>';
  }

  // Contexte : date, machine, opérateur
  const dt = fmtDate(ack.date_saisie);
  const contextLine = escHtml(ack.machine || '—') + ' · ' + escHtml(dt) + ' · ' + escHtml(ack.operateur || '—');
  const commentText = ack._raw_comment || '';

  // ── Contexte dossier + fiche technique ──
  const dosInfo = ack._dossier_info || null;
  const noDos = ack._no_dossier || '';
  let dossierHtml = '';
  if(noDos){
    const fmtVal = (v, suffix) => {
      if(v == null || v === '' || v === 0) return '';
      const s = String(v).trim();
      if(!s) return '';
      return escHtml(s) + (suffix ? ' ' + escHtml(suffix) : '');
    };
    const kv = (label, value) => {
      if(!value) return '';
      return '<div class="ack-di-kv"><span class="ack-di-k">' + escHtml(label) + '</span><span class="ack-di-v">' + value + '</span></div>';
    };
    const section = (title, kvs) => {
      const inner = kvs.filter(Boolean).join('');
      if(!inner) return '';
      return '<div class="ack-di-section"><div class="ack-di-title">' + escHtml(title) + '</div><div class="ack-di-grid">' + inner + '</div></div>';
    };
    let sections = '';
    if(dosInfo){
      const clientRef = [];
      if(dosInfo.ref_produit) clientRef.push(escHtml(dosInfo.ref_produit));
      else if(dosInfo.ref_produit_norm) clientRef.push(escHtml(dosInfo.ref_produit_norm));
      const dosSec = section('Dossier', [
        kv('Client', fmtVal(dosInfo.client)),
        kv('Désignation', fmtVal(dosInfo.description)),
        kv('Réf produit', clientRef.join(' ')),
        kv('Format', (dosInfo.format_l && dosInfo.format_h) ? escHtml(String(dosInfo.format_l)) + ' × ' + escHtml(String(dosInfo.format_h)) + ' mm' : (fmtVal(dosInfo.format_l, 'mm') || fmtVal(dosInfo.format_h, 'mm'))),
        kv('Laize dossier', fmtVal(dosInfo.pe_laize, 'mm')),
        kv('Dos', fmtVal(dosInfo.dos_rvgi)),
      ]);
      const bobSec = section('Bobine', [
        kv('Ø mandrin', fmtVal(dosInfo.mandrin_dia)),
        kv('Longueur mandrin', fmtVal(dosInfo.mandrin_longueur, 'mm')),
        kv('Enroulement', fmtVal(dosInfo.enroulement)),
        kv('Étiquettes / bobine', fmtVal(dosInfo.nb_etiq_bobin)),
        kv('Ø extérieur', fmtVal(dosInfo.dia_ext, 'mm')),
        kv('Poids', fmtVal(dosInfo.poids, 'kg')),
      ]);
      const matSec = section('Matière', [
        kv('Matière', fmtVal(dosInfo.matiere)),
        kv('Adhésif', fmtVal(dosInfo.adhesif)),
        kv('Support', fmtVal(dosInfo.support)),
        kv('Glassine', fmtVal(dosInfo.glassine)),
        kv('Épaisseur', fmtVal(dosInfo.epaisseur, 'µm')),
        kv('Laize fiche', fmtVal(dosInfo.ft_laize, 'mm')),
        kv('Laize optimale', fmtVal(dosInfo.laize_optimale, 'mm')),
      ]);
      const etiSec = section('Étiquette', [
        kv('Laize étiq.', fmtVal(dosInfo.eti_laize, 'mm')),
        kv('Longueur étiq.', fmtVal(dosInfo.eti_longueur, 'mm')),
        kv('Rayons', fmtVal(dosInfo.eti_rayons)),
        kv('Perforations', fmtVal(dosInfo.eti_perforations)),
      ]);
      const impSec = section('Impression', [
        kv('Anilox tête 1', fmtVal(dosInfo.tete1_anilox)),
        kv('Composition tête 1', fmtVal(dosInfo.tete1_composition)),
      ]);
      sections = dosSec + bobSec + matSec + etiSec + impSec;
    }
    const dosHeader = '<div class="ack-di-head"><span class="ack-di-badge">Dossier ' + escHtml(noDos) + '</span>' + (dosInfo && dosInfo.client ? '<span class="ack-di-badge-sub">' + escHtml(dosInfo.client) + '</span>' : '') + '</div>';
    // v2.3.44 : le bloc "Contexte dossier & fiche technique" est maintenant
    // dans un <details> fermé par défaut. Le badge Dossier reste visible
    // au-dessus du details pour garder l'info essentielle à l'œil.
    if(sections){
      dossierHtml = '<div class="ack-di-wrap" style="margin-top:12px">'
        + dosHeader
        + '<details style="margin-top:8px">'
        +   '<summary style="cursor:pointer;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;padding:6px 0;user-select:none;list-style:revert">Contexte dossier &amp; fiche technique</summary>'
        +   '<div style="margin-top:8px">' + sections + '</div>'
        + '</details>'
        + '</div>';
    } else {
      dossierHtml = '<div class="ack-di-wrap" style="margin-top:12px">'
        + dosHeader
        + '<div style="font-size:11px;color:var(--muted);font-style:italic;margin-top:6px">Aucune fiche technique associée à ce dossier.</div>'
        + '</div>';
    }
  }

  const overlay = document.createElement('div');
  overlay.className = 'ta-sim ta-pl-center ta-blocking';
  overlay.id = 'ack-detail-overlay';
  // v2.3.44 : hauteur limitée + scroll interne pour ne pas déborder de l'écran
  // quand la fiche technique est développée. Largeur ramenée à 480 pour rester
  // cohérent avec le viewer partagé (mysifa_ack_viewer.js).
  overlay.innerHTML = '<div class="ta-sim-alert" style="max-width:480px;width:480px;max-height:85vh;overflow-y:auto">'
    + '<div class="ta-sim-title">' + escHtml(ack.type || 'Contrôle') + '</div>'
    + '<div class="ta-sim-sub">' + contextLine + '</div>'
    + checklistHtml
    + dossierHtml
    + '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin:8px 0 4px 0">Commentaire</label>'
    + '<textarea disabled rows="2" placeholder="(aucun commentaire)" style="width:100%;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit;opacity:.85">' + escHtml(commentText) + '</textarea>'
    + '<div class="ta-sim-actions">'
    +   '<button type="button" class="ta-sim-btn" onclick="closeAckDetail()">Fermer</button>'
    + '</div>'
    + '</div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => {
    if(e.target === overlay) closeAckDetail();
  });
}

function closeAckDetail(){
  const el = document.getElementById('ack-detail-overlay');
  if(el) el.remove();
}

// Détecte une non-conformité : au moins une réponse choice de l'ack figure
// dans la liste nc_responses définie par l'admin lors de la création de
// l'alerte. Les items de type "value" et les clés "_other" (précision de la
// case Autre) ne sont pas évalués — l'admin cible explicitement quelles
// réponses signalent un problème.
function _ackHasNonConformite(c){
  if(!c || c._source !== 'alert') return false;
  const meta = (CTRL_STATE.alerts_meta || {})[String(c._alert_id)];
  if(!meta || !Array.isArray(meta.checklist_items)) return false;
  const resp = c._responses || {};
  for(let i = 0; i < meta.checklist_items.length; i++){
    const it = meta.checklist_items[i];
    if(!it || it.type === 'value') continue;
    const ncSet = Array.isArray(it.nc_responses) ? it.nc_responses.map(String) : [];
    const otherIsNc = !!it.other_is_nc;
    const r = resp[String(i)];
    if(!Array.isArray(r)) continue;
    for(const sel of r){
      const s = String(sel || '').trim();
      if(ncSet.indexOf(s) !== -1) return true;
      // "Autre" traité comme NC si l'admin l'a explicitement demandé
      if(otherIsNc && s === 'Autre') return true;
    }
  }
  return false;
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
  // Sync les filtres par point avec le type sélectionné
  renderPointFilters();
  // v2.2.18 : legacy CTRL_STATE.list dropped — historique = acks DB uniquement
  const merged = (CTRL_STATE.acks || []).slice();
  let filtered = merged.filter(c => {
    if(f.type && _displayType(c) !== f.type) return false;
    if(f.operateur && c.operateur !== f.operateur) return false;
    if(f.machine && c.machine !== f.machine) return false;
    if(f.dateFrom || f.dateTo){
      const d = (c.date_saisie || '').slice(0,10);
      if(f.dateFrom && d < f.dateFrom) return false;
      if(f.dateTo && d > f.dateTo) return false;
    }
    if(f.conformite){
      const isNc = _ackHasNonConformite(c);
      if(f.conformite === 'nc' && !isNc) return false;
      if(f.conformite === 'ok' && isNc)  return false;
    }
    // v2.3.29 : masque les fermetures automatiques par défaut
    if(!f.showAuto && ctrlIsAutoClose(c)) return false;
    if(!_matchPointFilters(c)) return false;
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
  // Colonnes adaptatives : si un seul type est sélectionné et qu'il correspond
  // à une alerte ayant une checklist, on affiche une colonne par point.
  let extraCols = [];
  const singleType = f.type || '';
  if(singleType){
    const ackMatch = merged.find(c => c._source === 'alert' && _displayType(c) === singleType);
    if(ackMatch && ackMatch._alert_id != null && CTRL_STATE.alerts_meta){
      const meta = CTRL_STATE.alerts_meta[String(ackMatch._alert_id)];
      if(meta && Array.isArray(meta.checklist_items)){
        extraCols = meta.checklist_items;
      }
    }
  }

  // Reconstruire le thead
  const showExtra = getShowExtraCols();
  const thead = document.querySelector('#ctrl-subview-historique .ops-table thead tr');
  if(thead){
    const sortIco = (col) => {
      if(sf !== col) return '<span class="sort-ico">↕</span>';
      return '<span class="sort-ico">' + (CTRL_STATE.sortDir === 'asc' ? '↑' : '↓') + '</span>';
    };
    const activeAttr = (col) => sf === col ? ' class="active"' : '';
    let h = '';
    h += '<th data-sort-ctrl="date_saisie"' + activeAttr('date_saisie') + ' onclick="sortCtrl(\'date_saisie\')">Date saisie' + sortIco('date_saisie') + '</th>';
    h += '<th data-sort-ctrl="machine"' + activeAttr('machine') + ' onclick="sortCtrl(\'machine\')">Machine' + sortIco('machine') + '</th>';
    h += '<th data-sort-ctrl="operateur"' + activeAttr('operateur') + ' onclick="sortCtrl(\'operateur\')">Opérateur' + sortIco('operateur') + '</th>';
    if(!singleType){
      h += '<th data-sort-ctrl="type"' + activeAttr('type') + ' onclick="sortCtrl(\'type\')">Type' + sortIco('type') + '</th>';
    }
    for(const col of extraCols){
      const unitSuffix = (col.type === 'value' && col.unit) ? ' (' + escHtml(col.unit) + ')' : '';
      h += '<th>' + escHtml(col.label || '') + unitSuffix + '</th>';
    }
    if(showExtra){
      h += '<th data-sort-ctrl="_no_dossier"' + activeAttr('_no_dossier') + ' onclick="sortCtrl(\'_no_dossier\')">Dossier' + sortIco('_no_dossier') + '</th>';
      h += '<th data-sort-ctrl="_ref_produit"' + activeAttr('_ref_produit') + ' onclick="sortCtrl(\'_ref_produit\')">Référence produit' + sortIco('_ref_produit') + '</th>';
      h += '<th data-sort-ctrl="_adhesif"' + activeAttr('_adhesif') + ' onclick="sortCtrl(\'_adhesif\')">Adhésif' + sortIco('_adhesif') + '</th>';
      h += '<th data-sort-ctrl="_glassine"' + activeAttr('_glassine') + ' onclick="sortCtrl(\'_glassine\')">Glassine' + sortIco('_glassine') + '</th>';
    }
    h += '<th>Commentaires</th>';
    h += '<th aria-label="Actions"></th>';
    thead.innerHTML = h;
  }

  const totalCols = 3 + (singleType ? 0 : 1) + extraCols.length + (showExtra ? 4 : 0) + 2;  // date+machine+operateur (+type?) + extra + (refprod+adhesif+glassine si toggle on) + commentaires + actions

  // v2.2.27 : pagination 50/page (pattern MyProd)
  const _totalFiltered = filtered.length;
  const _pageSize = CTRL_STATE.pageSize || 50;
  const _maxPage = Math.max(0, Math.ceil(_totalFiltered / _pageSize) - 1);
  if(CTRL_STATE.page > _maxPage) CTRL_STATE.page = _maxPage;
  if(CTRL_STATE.page < 0) CTRL_STATE.page = 0;
  const _pageStart = CTRL_STATE.page * _pageSize;
  const _pageEnd = Math.min(_pageStart + _pageSize, _totalFiltered);
  const _pagedRows = filtered.slice(_pageStart, _pageEnd);
  if(!filtered.length){
    const isFiltered = f.type || f.operateur || f.machine || f.dateFrom || f.dateTo;
    const msg = isFiltered
      ? 'Aucun contrôle ne correspond aux filtres.'
      : 'Aucun contrôle enregistré pour cette période.';
    tbody.innerHTML = '<tr><td colspan="' + totalCols + '" class="ops-empty">' + escHtml(msg) + '</td></tr>';
  } else {
    const rows = _pagedRows.map(c => {
      let cells = '';
      cells += '<td class="col-date">' + escHtml(fmtDate(c.date_saisie)) + '</td>';
      cells += '<td>' + escHtml(c.machine) + '</td>';
      cells += '<td>' + escHtml(c.operateur) + '</td>';
      if(!singleType){
        cells += '<td>' + escHtml(_displayType(c)) + '</td>';
      }
      for(let i = 0; i < extraCols.length; i++){
        let val = '';
        if(c._source === 'alert' && c._responses){
          const r = c._responses[String(i)];
          if(Array.isArray(r)){ val = r.join(', '); }
          else if(r != null && r !== ''){ val = String(r); }
          // Si "Autre" a été coché avec une précision, on l'ajoute au texte du cell.
          const otherTxt = c._responses[String(i) + '_other'];
          if(otherTxt != null && String(otherTxt).trim() !== ''){
            val = val ? val + ' — ' + String(otherTxt) : String(otherTxt);
          }
        }
        cells += '<td>' + escHtml(val) + '</td>';
      }
      if(showExtra){
        // Dossier (no_dossier) : pill accent si renseigné, tiret sinon.
        const _nd = c._no_dossier || '';
        const _ndCell = (c._source === 'alert' && _nd)
          ? '<span class="ctrl-dossier-pill" onclick="event.stopPropagation();openAckDetail(\'' + escAttr(c.id) + '\')" title="Voir la fiche technique">' + escHtml(_nd) + '</span>'
          : '<span class="ctrl-dossier-empty">—</span>';
        cells += '<td class="col-nodos">' + _ndCell + '</td>';
        // Colonnes produit (fiche technique associée)
        const _di = c._dossier_info || null;
        const _refP = _di ? (_di.ref_produit || _di.ref_produit_norm || '') : '';
        const _adh  = _di ? (_di.adhesif || '') : '';
        const _gla  = _di ? (_di.glassine || '') : '';
        const _refCell = (c._source === 'alert' && _refP)
          ? '<span class="ctrl-dossier-pill" onclick="event.stopPropagation();openAckDetail(\'' + escAttr(c.id) + '\')" title="Voir la fiche technique">' + escHtml(_refP) + '</span>'
          : '<span class="ctrl-dossier-empty">—</span>';
        cells += '<td class="col-dossier">' + _refCell + '</td>';
        cells += '<td class="col-adhesif">' + (_adh ? escHtml(_adh) : '<span class="ctrl-dossier-empty">—</span>') + '</td>';
        cells += '<td class="col-glassine">' + (_gla ? escHtml(_gla) : '<span class="ctrl-dossier-empty">—</span>') + '</td>';
      }
      // Commentaires : en mode single-type, on affiche seulement le vrai commentaire (pas les réponses formatées) ;
      // sinon, on garde le résumé condensé de _formatAckComment (utile en vue "Tous les types")
      const commentText = singleType
        ? (c._source === 'alert' ? (c._raw_comment || '') : (c.commentaire || ''))
        : (c.commentaire || '');
      cells += '<td class="col-comment">' + escHtml(commentText) + '</td>';
      // Actions
      let actionHtml = '';
      if(c._source === 'alert'){
        actionHtml = '<button type="button" class="ops-row-btn del" onclick="event.stopPropagation();deleteAck(\'' + escAttr(c.id) + '\')" title="Supprimer cette saisie (correction d\'erreur)">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
        '</button>';
      } else {
        actionHtml = '<button type="button" class="ops-row-btn del" onclick="event.stopPropagation();deleteCtrl(\'' + escAttr(c.id) + '\')" title="Supprimer">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
        '</button>';
      }
      cells += '<td class="col-actions">' + actionHtml + '</td>';
      const isNc = _ackHasNonConformite(c);
      const trClass = isNc ? ' class="ctrl-row-nc"' : '';
      const ncTitle = isNc ? ' title="Non-conformité — une réponse ne correspond pas à la valeur attendue"' : '';
      // v2.3.44 : simple clic (au lieu du double-clic) pour ouvrir le détail
      // d'une ack. La ligne reste sélectionnable via les cellules qui ont
      // event.stopPropagation() ailleurs (pill dossier, réponse cliquable).
      const dblAttr = (c._source === 'alert')
        ? ' onclick="openAckDetail(\'' + escAttr(c.id) + '\')" style="cursor:pointer"' + (isNc ? '' : ' title="Cliquer pour voir le détail"')
        : '';
      return '<tr' + trClass + dblAttr + ncTitle + '>' + cells + '</tr>';
    });
    tbody.innerHTML = rows.join('');
  }
  if(count){
    // v2.2.27 : compteur + pager (‹ X-Y/N ›)
    const n = (CTRL_STATE.acks || []).length;
    const visible = _totalFiltered;
    const from = visible === 0 ? 0 : _pageStart + 1;
    const to = _pageEnd;
    const label = visible !== n
      ? (from + '-' + to + ' / ' + visible + ' filtrés (' + n + ' total)')
      : (from + '-' + to + ' / ' + n + ' contrôle' + (n > 1 ? 's' : ''));
    const prevD = CTRL_STATE.page <= 0;
    const nextD = CTRL_STATE.page >= _maxPage;
    const btnStyle = 'border:1px solid var(--border);background:var(--card);color:var(--text2);padding:3px 9px;border-radius:6px;font-size:13px;line-height:1;font-family:inherit;transition:border-color .12s,color .12s';
    count.innerHTML = '<div style="display:inline-flex;align-items:center;gap:8px">' +
      '<button type="button" ' + (prevD ? 'disabled' : '') + ' onclick="ctrlPageGo(-1)" title="Page précédente" style="' + btnStyle + ';cursor:' + (prevD ? 'not-allowed' : 'pointer') + (prevD ? ';opacity:.35' : '') + '">‹</button>' +
      '<span style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;font-weight:600">' + escHtml(label) + '</span>' +
      '<button type="button" ' + (nextD ? 'disabled' : '') + ' onclick="ctrlPageGo(1)" title="Page suivante" style="' + btnStyle + ';cursor:' + (nextD ? 'not-allowed' : 'pointer') + (nextD ? ';opacity:.35' : '') + '">›</button>' +
      '</div>';
  }
}

// =========================================================================
// Catalogue des types de contrôles (Liste de contrôles)
// =========================================================================
// Source : table maintenance_codes (Paramètres → Maintenance).
// Filtre demandé : seuls les codes avec categorie="controles" et periodique=NON.
// La "Dernière intervention" est calculée à partir de CTRL_STATE filtré par machine.
const CTRL_CAT_MACHINE_KEY = 'mysifa_maint_ctrl_cat_machine_v1';
const CTRL_TYPES_STATE = { sortBy: 'nom', sortDir: 'asc', list: [] };

function getCtrlCatMachine(){
  try{ return localStorage.getItem(CTRL_CAT_MACHINE_KEY) || 'Cohésio 1'; }
  catch(e){ return 'Cohésio 1'; }
}
function setCtrlCatMachine(m){
  try{ localStorage.setItem(CTRL_CAT_MACHINE_KEY, m || ''); }catch(e){}
  document.querySelectorAll('.js-ctrl-cat-machine').forEach(sel => { sel.value = m; });
  renderCtrlTypes();
}

async function loadCtrlTypes(){
  try{
    const res = await fetch('/api/maintenance/codes', { credentials: 'include' });
    if(!res.ok){
      CTRL_TYPES_STATE.list = [];
      return;
    }
    const data = await res.json();
    const items = Array.isArray(data && data.items) ? data.items : [];
    CTRL_TYPES_STATE.list = items
      .filter(it => it.categorie === 'controles' && !it.periodique)
      .map(it => ({
        id: it.code,
        nom: it.label,
        niveau: parseInt(it.niveau, 10) || 1,
        detail: '',
        docs_count: parseInt(it.docs_count, 10) || 0,
        _readonly: true,
      }));
  }catch(e){
    CTRL_TYPES_STATE.list = [];
  }
}
// Conservé pour compat (no-op : gestion centralisée dans Paramètres → Maintenance).
function saveCtrlTypes(){ /* géré côté serveur via /api/maintenance/codes */ }
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
  const machine = getCtrlCatMachine();
  document.querySelectorAll('.js-ctrl-cat-machine').forEach(sel => {
    if(sel.value !== machine) sel.value = machine;
  });
  // Calcule la dernière intervention par code, filtrée par machine
  CTRL_TYPES_STATE.list.forEach(t => {
    t.derniere_intervention = _lastInterventionForCtrl(t.id, t.nom, machine, CTRL_STATE.list, CTRL_STATE.acks || []);
  });
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
    tbody.innerHTML = '<tr><td colspan="5" class="ops-empty">Aucun contrôle non périodique. Ajoutez des codes avec catégorie=Contrôles et Périodique=NON dans Paramètres → Maintenance.</td></tr>';
  } else {
    const rows = sorted.map(t => {
      let dtDisplay = '—';
      if(t.derniere_intervention){
        try{
          const d = new Date(t.derniere_intervention);
          if(!isNaN(d.getTime())){
            const pad = n => (n < 10 ? '0' + n : '' + n);
            dtDisplay = pad(d.getDate()) + '/' + pad(d.getMonth()+1) + '/' + d.getFullYear()
                      + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
          }
        }catch(e){}
      }
      const _dc = t.docs_count || 0;
      const docsBtn = _dc
        ? '<button type="button" class="ops-row-btn maint-view-docs" data-doc-code="' + escAttr(t.id) + '" title="Voir les documents attaches">' + _dc + ' doc' + (_dc>1?'s':'') + '</button>'
        : '<span style="color:var(--muted);font-size:12px">—</span>';
      return '<tr>' +
        '<td><strong style="color:var(--text)">' + escHtml(t.nom) + '</strong></td>' +
        '<td><span style="font-size:13px;color:var(--text)">' + escHtml(dtDisplay) + '</span></td>' +
        '<td>' + docsBtn + '</td>' +
        '<td class="col-comment">' + escHtml(t.detail || '') + '</td>' +
        '<td class="col-actions"></td>' +
      '</tr>';
    });
    tbody.innerHTML = rows.join('');
  }
  if(count){
    const n = CTRL_TYPES_STATE.list.length;
    count.textContent = n + ' contrôle' + (n > 1 ? 's' : '');
  }
  document.querySelectorAll('.maint-view-docs[data-doc-code]').forEach(b => {
    b.addEventListener('click', () => viewMaintDocs(b.getAttribute('data-doc-code')));
  });
}

// Modal read-only : liste les documents attaches a un code avec liens
// de telechargement. Pas d'upload ni suppression cote operateur.
async function viewMaintDocs(code){
  const overlay = document.createElement('div');
  overlay.className = 'ta-sim ta-pl-center ta-blocking';
  overlay.id = 'maint-docs-view-overlay';
  overlay.innerHTML = '<div class="ta-sim-alert" style="max-width:520px">'
    + '<div class="ta-sim-title">Documents · ' + escHtml(code) + '</div>'
    + '<div id="maint-docs-view-list" style="display:flex;flex-direction:column;gap:6px;margin:12px 0">'
    +   '<p style="color:var(--muted);font-size:12px">Chargement…</p>'
    + '</div>'
    + '<div class="ta-sim-actions">'
    +   '<button type="button" class="ta-sim-btn" onclick="closeMaintDocsView()">Fermer</button>'
    + '</div>'
    + '</div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', (e) => { if(e.target === overlay) closeMaintDocsView(); });
  try{
    const r = await fetch('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs', { credentials: 'same-origin' });
    if(!r.ok) throw new Error('Erreur ' + r.status);
    const d = await r.json();
    const items = Array.isArray(d.items) ? d.items : [];
    const list = document.getElementById('maint-docs-view-list');
    if(!list) return;
    if(!items.length){
      list.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document.</p>';
      return;
    }
    list.innerHTML = items.map(doc => {
      const sz = doc.size_bytes != null ? (Math.round(doc.size_bytes/1024) + ' Ko') : '';
      const dt = doc.uploaded_at ? escHtml(doc.uploaded_at.slice(0,16).replace('T',' ')) : '';
      return '<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card)">'
        +   '<div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escHtml(doc.filename) + '</div>'
        +   '<div style="font-size:10px;color:var(--muted)">' + sz + (dt ? ' · ' + dt : '') + '</div></div>'
        +   '<a href="/api/maintenance/docs/' + doc.id + '/download" target="_blank" rel="noopener" class="ta-sim-btn" style="text-decoration:none;padding:6px 12px;font-size:12px">Ouvrir</a>'
        + '</div>';
    }).join('');
  } catch(e){
    const list = document.getElementById('maint-docs-view-list');
    if(list) list.innerHTML = '<p style="color:var(--danger);font-size:12px">Erreur de chargement.</p>';
  }
}
function closeMaintDocsView(){
  const el = document.getElementById('maint-docs-view-overlay');
  if(el) el.remove();
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
    // v2.2.45 : révèle la nav-btn "Mes tâches" (côté admin) uniquement pour Manuel Lesaffre
    try {
      const nomLower = String((S.me && S.me.nom) || '').toLowerCase();
      if (nomLower.includes('lesaffre')) {
        const btn = document.getElementById('nav-mes-taches-admin');
        if (btn) btn.style.display = '';
      }
    } catch(e) {}
  }catch(e){}
}

(function init(){
  try{
    const t=localStorage.getItem('mysifa_theme');
    if(t==='light') document.body.classList.add('light');
    else document.body.classList.remove('light');
    updateThemeBtn();
  }catch(e){}
  // v2.5.5 : on garde la promise pour l'attendre avant switchView opérateur
  // (opLoadTasks / opLoadPlanning lisent S.me.id — sans ça, filtre vide au boot).
  const _initMePromise = loadMe();
  loadOps();
  // loadOpsTypes() et loadCtrlTypes() sont async (fetch /api/maintenance/codes).
  loadOpsTypes().then(() => {
    renderOpsTypes();
    if(typeof renderMaintCards === 'function') renderMaintCards();
  }).catch(() => {
    renderOpsTypes();
    if(typeof renderMaintCards === 'function') renderMaintCards();
  });
  loadCtrl();
  updateExtraToggleUI();
  // v2.3.35 : init du toggle "Fermetures auto" (relocalisé dans le header historique)
  updateAutoCloseToggleUI();
  loadCtrlAcks();
  loadCtrlTypes().then(() => renderCtrlTypes()).catch(() => renderCtrlTypes());
  loadPlanning();
  renderOps();
  renderCtrl();
  try{
    const h = (location.hash || '').replace('#','').trim();
    const target = (h === 'historique') ? 'controles' : h;
    const initialView = (target && VIEW_META[target]) ? target
                        : (MAINT_ROLE === 'operator' ? 'op-tasks' : null);
    if(initialView){
      if(MAINT_ROLE === 'operator'){
        // v2.5.5 : pour opérateur, attendre S.me avant switchView. opLoadTasks
        // et opLoadPlanning filtrent les events par S.me.id — appelées avant
        // que loadMe() résolve, elles produisent un state vide (bug v2.5.4).
        _initMePromise.finally(() => { try{ switchView(initialView); }catch(e){} });
      } else {
        switchView(initialView);
      }
    }
  }catch(e){}
})();

// ═══════════════════════════════════════════════════════════════════
// v2.2.48 : Sous-onglets Planning + Historique des créneaux
// ═══════════════════════════════════════════════════════════════════
const PLAN_SUBTAB_KEY = 'mysifa_maint_plan_subtab_v1';
function _getPlanSubtab(){
  try{ return localStorage.getItem(PLAN_SUBTAB_KEY) || 'calendrier'; }
  catch(e){ return 'calendrier'; }
}
function setPlanSubtab(name){
  if(name !== 'calendrier' && name !== 'historique') name = 'calendrier';
  try{ localStorage.setItem(PLAN_SUBTAB_KEY, name); }catch(e){}
  document.querySelectorAll('[data-plan-subtab]').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-plan-subtab') === name);
  });
  const cal = document.getElementById('plan-subview-calendrier');
  const hist = document.getElementById('plan-subview-historique');
  if(cal) cal.style.display = (name === 'calendrier') ? '' : 'none';
  if(hist) hist.style.display = (name === 'historique') ? '' : 'none';
  if(name === 'historique'){
    loadPlanningHistorique();
    // v2.4.30 : panel "Gestion des modeles" -- charge + rend explicitement.
    if(typeof loadTemplates === 'function' && typeof renderTemplateManagePanel === 'function'){
      loadTemplates(true).then(renderTemplateManagePanel).catch(function(){});
    }
  }
  else if(name === 'calendrier'){
    // v2.6.0 : rendu immediat depuis le cache, refetch seulement si besoin.
    try{ _requestCalAutoScroll(); }catch(_){}
    try { renderCalFromCacheThenRefresh(); } catch(e){ try{ renderCal(); }catch(_){} }
    // v2.6.1 : la section vient seulement d'etre affichee (display:none jusqu'a
    // cette ligne), donc _fitCalWeekBody n'a pas pu mesurer pendant le rendu.
    try{ _scheduleCalHeaderGutterSync(); }catch(_){}
  }
}
async function loadPlanningHistorique(){
  const listEl = document.getElementById('plan-hist-list');
  if(!listEl) return;
  const today = new Date();
  const past = new Date(); past.setDate(today.getDate() - 180);
  try{
    const r = await fetch('/api/maintenance/events?date_from=' + _fmtDateISO(past) + '&date_to=' + _fmtDateISO(today) + '&_=' + Date.now(),
      { credentials: 'include', cache: 'no-store' });
    if(!r.ok){ listEl.innerHTML = '<p style="color:var(--danger)">Erreur de chargement.</p>'; return; }
    const data = await r.json();
    const todayIso = _fmtDateISO(today);
    // v2.2.49 : inclut aujourd'hui (<=) — un créneau créé et validé le jour même
    // doit apparaître dans l'historique tout de suite.
    const events = (data.events || []).filter(ev =>
      ev.source === 'planifie' && ev.date_prevue && ev.date_prevue <= todayIso
    );
    events.sort((a,b) => (b.date_prevue || '').localeCompare(a.date_prevue || ''));
    renderPlanningHistorique(events);
  }catch(e){
    listEl.innerHTML = '<p style="color:var(--danger)">Erreur : ' + escHtml(e.message) + '</p>';
  }
}
// v2.2.50 : historique visuel enrichi avec double-clic → détail créneau
function _histInitials(nom){
  const parts = String(nom || '').trim().split(/\s+/);
  if(!parts.length) return '?';
  return (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase();
}
function _histColorForString(s){
  // hash simple → palette 6 couleurs stables
  const palette = ['#22d3ee','#fbbf24','#a78bfa','#f472b6','#34d399','#60a5fa'];
  let h = 0;
  for(const ch of String(s || '')) h = ((h << 5) - h + ch.charCodeAt(0)) | 0;
  return palette[Math.abs(h) % palette.length];
}
function _histMachineChipStyle(m){
  const bg = _histColorForString(m);
  return 'display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:12px;background:' + bg + '22;color:' + bg + ';border:1px solid ' + bg + '55;font-size:11px;font-weight:700;line-height:1.3';
}
function _histOperatorAvatarStyle(nom){
  const bg = _histColorForString(nom);
  return 'display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:' + bg + ';color:#fff;font-size:10px;font-weight:800;letter-spacing:.3px;margin-right:-6px;border:2px solid var(--card);flex-shrink:0';
}
function _histStatusColor(ratio){
  if(ratio >= 1) return 'var(--ok,#34d399)';       // tout fait — vert
  if(ratio > 0)  return 'var(--warn,#fbbf24)';     // partiel — orange
  return 'var(--danger,#f87171)';                  // rien — rouge
}
function renderPlanningHistorique(events){
  const listEl = document.getElementById('plan-hist-list');
  if(!listEl) return;
  if(!events.length){
    listEl.innerHTML = '<p style="color:var(--muted);font-style:italic;font-size:13px;text-align:center;padding:24px 0">Aucun créneau planifié dans les 6 derniers mois.</p>';
    return;
  }
  const rowsHtml = events.map(ev => {
    const machineUnion = [];
    (ev.ops || []).forEach(o => {
      (o.machines || []).forEach(m => { if(!machineUnion.includes(m)) machineUnion.push(m); });
    });
    // Progression : compter les op-machine faites vs total
    let total = 0, done = 0;
    (ev.ops || []).forEach(o => {
      const nMach = (o.machines || []).length || 1;
      total += nMach;
      if(o.statut === 'termine' || o.statut === 'invalidee') done += nMach;  // v2.5.10
    });
    const ratio = total > 0 ? (done / total) : 0;
    const statusColor = _histStatusColor(ratio);
    const pct = Math.round(ratio * 100);
    // Opérateurs présents : done_by unique, fallback assignés
    const doneBySet = new Set();
    (ev.ops || []).forEach(o => { if(o.done_by != null) doneBySet.add(Number(o.done_by)); });
    const opsList = Array.isArray(ev.operators) ? ev.operators : [];
    const doneByNames = Array.from(doneBySet).map(uid => {
      const u = opsList.find(x => Number(x.id) === uid);
      return u ? (u.nom || 'op. #' + uid) : ('op. #' + uid);
    });
    const opsPresents = doneByNames.length ? doneByNames : opsList.map(u => u.nom || '').filter(Boolean);
    const dateFr = _fmtIsoDateFr(ev.date_prevue);
    const horaires = (ev.heure_debut && ev.heure_fin) ? (ev.heure_debut + '–' + ev.heure_fin) : '';
    // Rendu
    const machineChips = machineUnion.length
      ? machineUnion.map(m => '<span style="' + _histMachineChipStyle(m) + '">' + escHtml(m) + '</span>').join('')
      : '<span style="color:var(--muted);font-size:11px;font-style:italic">Aucune machine</span>';
    const opAvatars = opsPresents.length
      ? '<div style="display:inline-flex;align-items:center">' + opsPresents.slice(0, 4).map(n =>
          '<span style="' + _histOperatorAvatarStyle(n) + '" title="' + escAttr(n) + '">' + escHtml(_histInitials(n)) + '</span>'
        ).join('') +
        (opsPresents.length > 4 ? '<span style="margin-left:8px;font-size:11px;color:var(--muted);font-weight:600">+' + (opsPresents.length - 4) + '</span>' : '') +
        '</div>'
      : '<span style="color:var(--muted);font-size:11px;font-style:italic">—</span>';
    return '<div data-hist-ev-id="' + escAttr(ev.id) + '" ondblclick="planHistOpenDetails(\'' + escAttr(ev.id) + '\')" ' +
        'style="padding:14px 16px;border:1px solid var(--border);border-left:4px solid ' + statusColor + ';border-radius:10px;background:var(--card);margin-bottom:10px;cursor:pointer;transition:box-shadow .15s,border-color .15s" ' +
        'title="Double-cliquez pour voir le détail" ' +
        'onmouseover="this.style.boxShadow=\'0 2px 12px rgba(0,0,0,0.08)\'" ' +
        'onmouseout="this.style.boxShadow=\'none\'">' +
      '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:14px">' +
        // Colonne 1 : Date + horaires + progress bar
        '<div style="flex:1;min-width:220px">' +
          '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="' + statusColor + '" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>' +
            '<span style="font-size:13px;font-weight:700;color:var(--text)">' + escHtml(dateFr) + '</span>' +
            (horaires ? '<span style="font-family:ui-monospace,monospace;font-size:12px;color:var(--text2);font-weight:600">· ' + escHtml(horaires) + '</span>' : '') +
          '</div>' +
          // Progress bar ops
          '<div style="display:flex;align-items:center;gap:8px">' +
            '<div style="flex:1;max-width:180px;height:6px;background:var(--bg);border-radius:3px;overflow:hidden;border:1px solid var(--border)">' +
              '<div style="height:100%;background:' + statusColor + ';width:' + pct + '%;transition:width .3s"></div>' +
            '</div>' +
            '<span style="font-size:11px;font-weight:700;color:' + statusColor + ';font-family:ui-monospace,monospace">' + done + ' / ' + total + '</span>' +
          '</div>' +
        '</div>' +
        // Colonne 2 : Machines chips
        '<div style="min-width:180px">' +
          '<div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;display:flex;align-items:center;gap:5px">' +
            '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"/></svg>' +
            'Machines' +
          '</div>' +
          '<div style="display:flex;flex-wrap:wrap;gap:4px">' + machineChips + '</div>' +
        '</div>' +
        // Colonne 3 : Opérateurs avatars
        '<div style="min-width:150px">' +
          '<div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;display:flex;align-items:center;gap:5px">' +
            '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>' +
            'Opérateurs présents' +
          '</div>' +
          opAvatars +
        '</div>' +
        // Bouton Reprogrammer
        '<button type="button" onclick="event.stopPropagation();planHistReprogrammer(\'' + escAttr(ev.id) + '\')" style="background:var(--accent);color:var(--accent-fg,#fff);border:none;border-radius:8px;padding:9px 16px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;transition:filter .12s;display:inline-flex;align-items:center;gap:6px">' +
          '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>' +
          'Reprogrammer' +
        '</button>' +
      '</div>' +
    '</div>';
  }).join('');
  listEl.innerHTML = rowsHtml;
}

// v2.2.50 : ouvre le modal Détails créneau depuis l'historique (converti au format calendar)
async function planHistOpenDetails(eventId){
  try{
    const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId), { credentials: 'include' });
    if(!r.ok){ showToast('Créneau introuvable.', 'danger'); return; }
    const data = await r.json();
    const ev = data.event || data;
    if(!ev){ showToast('Données manquantes.', 'danger'); return; }
    const clientEv = (typeof _apiEventToClient === 'function') ? _apiEventToClient(ev) : ev;
    openPlanningDetailsModal([clientEv]);
  }catch(e){
    showToast('Erreur : ' + e.message, 'danger');
  }
}
async function planHistReprogrammer(eventId){
  try{
    const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId), { credentials: 'include' });
    if(!r.ok){ showToast('Créneau introuvable.', 'danger'); return; }
    const data = await r.json();
    const ev = data.event || data;
    if(!ev || !ev.ops || !ev.ops.length){ showToast('Ce créneau n\'a pas d\'opération à copier.', 'danger'); return; }
    const defaultName = 'Modèle du ' + (ev.date_prevue || '');
    const name = prompt('Nom du modèle à créer depuis ce créneau :', defaultName);
    if(!name || !name.trim()) return;
    const opsMap = new Map();
    for(const o of ev.ops){
      if(!opsMap.has(o.code)) opsMap.set(o.code, { code: o.code, machines: [] });
      const entry = opsMap.get(o.code);
      for(const m of (o.machines || [])){
        if(!entry.machines.includes(m)) entry.machines.push(m);
      }
    }
    const ops = Array.from(opsMap.values()).filter(o => o.machines.length);
    const rNew = await fetch('/api/maintenance/templates', {
      method: 'POST', credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name: name.trim(), description: 'Créé depuis créneau du ' + (ev.date_prevue || ''), ops }),
    });
    if(!rNew.ok){
      const err = await rNew.json().catch(()=>({}));
      throw new Error(err.detail || 'Enregistrement refusé');
    }
    showToast('Modèle « ' + name.trim() + ' » créé — utilisable depuis Nouveau créneau.', 'info');
    if(typeof loadTemplates === 'function') loadTemplates(true);
  }catch(e){
    showToast('Erreur : ' + e.message, 'danger');
  }
}

// ═══════════════════════════════════════════════════════════════════
// v2.2.19 : Panel Alertes maintenance — duplication de settings_page.py
// Adapters : esc/toast/api pour matcher les conventions maintenance_page
// ═══════════════════════════════════════════════════════════════════
if (typeof esc !== 'function') { window.esc = function(s){ return escHtml(s); }; }
if (typeof toast !== 'function') { window.toast = function(msg, err){ if(typeof showToast==='function') showToast(msg, err?'danger':'info'); else console.log(msg); }; }
if (typeof api !== 'function') {
  window.api = async function(path, opt) {
    const r = await fetch(path, { credentials: 'include', ...(opt||{}) });
    if (r.status === 401) { location.href = '/?next=/maintenance'; return null; }
    const ct = r.headers.get('content-type') || '';
    const j = ct.includes('json') ? await r.json().catch(() => ({})) : {};
    if (!r.ok) {
      // v2.7.1 : cf. settings_page.py — un detail structuré ({message, ...})
      // doit rester lisible dans le toast.
      const d = j.detail;
      const msg = (d && typeof d === 'object') ? (d.message || JSON.stringify(d)) : d;
      const err = new Error(msg || ('Erreur ' + r.status));
      err.detail = d; err.status = r.status;
      throw err;
    }
    return j;
  };
}

// ── Alertes maintenance (gestion super admin) ──────────────────────
let _alertsData = [];

async function loadAlerts() {
  const box = document.getElementById('alerts-list');
  if (!box) return;
  try {
    const r = await api('/api/maintenance/alerts');
    _alertsData = (r && Array.isArray(r.items)) ? r.items : [];
  } catch (e) {
    box.innerHTML = '<p style="color:var(--danger);font-size:13px">Erreur de chargement : ' + esc(e && e.message ? e.message : String(e)) + '</p>';
    return;
  }
  renderAlertsList();
  // Re-render aussi la table des codes pour rafraîchir la colonne
  // "Dernière intervention" qui dépend des alertes liées.
  if (typeof renderMaintList === 'function') renderMaintList();
}

function _fmtAlertDate(s) {
  if (!s) return '';
  const t = String(s).replace('T', ' ').slice(0, 16);
  return t;
}

let _alertsFilterKind = 'all';

function renderAlertsList() {
  const box = document.getElementById('alerts-list');
  if (!box) return;
  if (!_alertsData.length) {
    box.innerHTML = '<div class="alert-preview-empty">Aucune alerte pour l\'instant. Clique sur « + Nouvelle alerte » pour en créer une.</div>';
    return;
  }
  const q = (document.getElementById('alerts-filter-q')?.value || '').trim().toLowerCase();
  const filtered = _alertsData.filter(a => {
    // v2.2.16 — Filtre Auto/Manuelles retiré. Seul le search reste actif.
    if (q) {
      const hay = (a.nom || '').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  if (!filtered.length) {
    box.innerHTML = '<div class="alert-preview-empty">Aucune alerte pour ce filtre.</div>';
    return;
  }
  const html = filtered.map(a => {
    const isAuto = !!a.linked_maint_code;
    const configured = _alertIsConfigured(a);
    let cls = a.active ? 'is-active' : 'is-inactive';
    if (!configured) cls += ' is-todo';
    const created = _fmtAlertDate(a.created_at);
    // v2.2.16 — Badge Auto retiré (système d'alertes auto supprimé).
    const autoBadge = '';
    const todoBadge = (!configured)
      ? '<span class="alert-badge todo" title="Cette alerte n\'a pas encore été configurée — cliquez sur Modifier pour renseigner ses paramètres.">À configurer</span>'
      : '';
    const badge = autoBadge + todoBadge;
    const lastAck = a.last_ack_at
      ? ' · Dernière intervention : ' + esc(_fmtAlertDate(a.last_ack_at))
      : (isAuto ? ' · Jamais effectuée' : '');
    const delBtn = isAuto
      ? ''
      : '<button type="button" class="btn-sm btn-ghost danger" data-alert-del="' + a.id + '">Supprimer</button>';
    return '<div class="alert-row ' + cls + '" data-alert-id="' + a.id + '">'
      + '<label class="toggle" title="' + (a.active ? 'Désactiver' : 'Activer') + '">'
      +   '<input type="checkbox" ' + (a.active ? 'checked' : '') + ' data-alert-toggle="' + a.id + '">'
      +   '<span class="toggle-track"><span class="toggle-thumb"></span></span>'
      + '</label>'
      + '<div class="alert-info">'
      +   '<p class="alert-nom">' + esc(a.nom) + ' ' + badge + '</p>'
      +   '<span class="alert-meta">Créée le ' + esc(created) + (a.created_by_display ? ' · ' + esc(a.created_by_display) : '') + lastAck + '</span>'
      + '</div>'
      + '<div class="alert-actions">'
      +   '<button type="button" class="btn-sm btn-ghost" data-alert-preview="' + a.id + '" title="Ouvre l\'alerte sur ton écran avec les vrais champs interactifs. Aucune donnée n\'est enregistrée.">Tester sur moi</button>'
      +   '<button type="button" class="btn-sm btn-ghost" data-alert-edit="' + a.id + '">Modifier</button>'
      +   delBtn
      + '</div>'
      + '</div>';
  }).join('');
  box.innerHTML = html;
  box.querySelectorAll('[data-alert-toggle]').forEach(el => {
    el.addEventListener('change', () => toggleAlert(parseInt(el.getAttribute('data-alert-toggle'), 10), el.checked));
  });
  box.querySelectorAll('[data-alert-preview]').forEach(btn => {
    btn.addEventListener('click', () => previewAlert(parseInt(btn.getAttribute('data-alert-preview'), 10)));
  });
  box.querySelectorAll('[data-alert-edit]').forEach(btn => {
    btn.addEventListener('click', () => openEditAlertModal(parseInt(btn.getAttribute('data-alert-edit'), 10)));
  });
  box.querySelectorAll('[data-alert-del]').forEach(btn => {
    btn.addEventListener('click', () => deleteAlert(parseInt(btn.getAttribute('data-alert-del'), 10)));
  });
}

function _taOnOtherChange(inp){
  const item = inp.closest('.ta-cl-item');
  if(!item) return;
  const txt = item.querySelector('.ta-cl-other-text');
  if(!txt) return;
  const isMulti = inp.type === 'checkbox';
  let show;
  if(isMulti){
    show = inp.checked;
  } else {
    // radio : Autre est le seul coché à cet instant
    show = inp.checked;
  }
  txt.style.display = show ? '' : 'none';
  if(show){ setTimeout(() => txt.focus(), 30); }
  else { txt.value = ''; }
}

function _taOnValueInput(inp) {
  // Feedback visuel en mode test : bordure rouge si valeur hors tolérance.
  // Aucun blocage — purement informatif.
  const item = inp.closest('.ta-cl-item');
  if (!item) return;
  const minAttr = item.getAttribute('data-min');
  const maxAttr = item.getAttribute('data-max');
  const v = parseFloat(inp.value);
  let outOfRange = false;
  if (!isNaN(v)) {
    if (minAttr !== null && minAttr !== '' && v < parseFloat(minAttr)) outOfRange = true;
    if (maxAttr !== null && maxAttr !== '' && v > parseFloat(maxAttr)) outOfRange = true;
  }
  inp.style.borderColor = outOfRange ? 'var(--danger)' : 'var(--border)';
  inp.style.color = outOfRange ? 'var(--danger)' : 'var(--text)';
}

// Bascule filtre Toutes / Auto / Manuelles
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('[data-alerts-filter]');
  if (!btn) return;
  _alertsFilterKind = btn.getAttribute('data-alerts-filter');
  document.querySelectorAll('[data-alerts-filter]').forEach(b => b.classList.toggle('active', b === btn));
  renderAlertsList();
});

// Référentiels pour les formulaires d'alerte
// v2.3.33 : bascule la section Paramètres (déclencheur / machines / affichage / …)
// Force l'ouverture de la section Paramètres — appelé par _afReadParams pour
// que les erreurs de validation portant sur des champs planqués soient visibles.
// v164 : toggle du bouton dismiss (fermeture sans saisie)
// v2.2.42 : no-op depuis le retrait du filtre produit.
// Fermeture du dropdown sur clic à l'extérieur (un seul listener global, idempotent)
if (!window._afMachinesDropdownInit) {
  window._afMachinesDropdownInit = true;
  document.addEventListener('click', (ev) => {
    const panel = document.getElementById('af-md-panel');
    if (!panel || !panel.classList.contains('open')) return;
    if (ev.target.closest('.af-md-wrap')) return;
    panel.classList.remove('open');
  });
}

function openNewAlertModal() {
  const overlay = document.createElement('div');
  overlay.className = 'alert-modal-overlay';
  overlay.innerHTML = '<div class="alert-modal">'
    + '<div class="alert-modal-head"><h3>Nouvelle alerte</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
    + '<div class="alert-modal-body">'
    +   _renderAlertFormFields(null, { nomReadonly: false, nomValue: '' })
    +   '<p style="font-size:11px;color:var(--muted);margin-top:10px">L\'alerte sera créée à l\'état <strong>inactif</strong>. Active-la via son interrupteur une fois prête.</p>'
    + '</div>'
    + '<div class="alert-modal-foot">'
    +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
    +   '<button type="button" class="btn" id="new-alert-confirm">Créer</button>'
    + '</div></div>';
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  _afOnTriggerChange();
  document.getElementById('new-alert-confirm').addEventListener('click', async () => {
    const nom = (document.getElementById('af-nom').value || '').trim();
    if (!nom) { toast('Titre obligatoire', true); return; }
    const params = _afReadParams();
    if (!params) return;
    try {
      await api('/api/maintenance/alerts', { method: 'POST', body: JSON.stringify({ nom, params }) });
      toast('Alerte créée');
      close();
      await loadAlerts();
    } catch (e) { toast(e && e.message ? e.message : 'Erreur', true); }
  });
  setTimeout(() => document.getElementById('af-nom')?.focus(), 30);
}

async function toggleAlert(id, active) {
  try {
    await api('/api/maintenance/alerts/' + id, { method: 'PATCH', body: JSON.stringify({ active: !!active }) });
    toast(active ? 'Alerte activée' : 'Alerte désactivée');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
  await loadAlerts();
}

async function deleteAlert(id) {
  const a = _alertsData.find(x => x.id === id);
  if (!a) return;
  if (!confirm('Supprimer définitivement l\'alerte « ' + a.nom + ' » ?')) return;
  try {
    await api('/api/maintenance/alerts/' + id, { method: 'DELETE' });
    toast('Alerte supprimée');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
    return;
  }
  await loadAlerts();
}

async function disableAllAlerts() {
  const nbActive = _alertsData.filter(a => a.active).length;
  if (nbActive === 0) { toast('Aucune alerte active actuellement', true); return; }
  if (!confirm('Désactiver les ' + nbActive + ' alerte(s) active(s) ? Aucune ne sera supprimée — c\'est un kill switch d\'urgence.')) return;
  try {
    const r = await api('/api/maintenance/alerts/disable-all', { method: 'POST' });
    toast((r?.disabled || 0) + ' alerte(s) désactivée(s)');
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
    return;
  }
  await loadAlerts();
}

let _alertGlobalSettings = { placement: 'top-right', size: 'medium', block_production: false, stack_mode: 'queue', min_gap_minutes: 5 };

async function loadAlertSettings() {
  try {
    const r = await api('/api/maintenance/alert-settings');
    let placement = r.placement || 'center';
    if (placement !== 'center' && placement !== 'top-right' && placement !== 'bottom-right') {
      placement = 'center';
    }
    let minGap = 5;
    if(r.min_gap_minutes != null){
      const parsed = parseInt(r.min_gap_minutes, 10);
      if(!isNaN(parsed) && parsed >= 0) minGap = parsed;
    }
    _alertGlobalSettings = {
      placement: placement,
      size: r.size || 'medium',
      block_production: !!r.block_production,
      stack_mode: 'queue',
      min_gap_minutes: minGap,
    };
  } catch (e) {
    // En cas d'erreur, on garde les valeurs par défaut.
  }
}

function openAlertSettingsModal() {
  loadAlertSettings().then(() => {
    const overlay = document.createElement('div');
    overlay.className = 'alert-modal-overlay';
    const placements = [
      { v: 'center',       l: 'Centre (modal)' },
      { v: 'top-right',    l: 'Coin haut droit' },
      { v: 'bottom-right', l: 'Coin bas droit' },
    ];
    const sizes = [
      { v: 'small',  l: 'Petite' },
      { v: 'medium', l: 'Moyenne' },
      { v: 'large',  l: 'Grande' },
    ];
const placementOpts = placements.map(p =>
      '<option value="' + p.v + '"' + (p.v === _alertGlobalSettings.placement ? ' selected' : '') + '>' + esc(p.l) + '</option>'
    ).join('');
    const sizeOpts = sizes.map(s =>
      '<option value="' + s.v + '"' + (s.v === _alertGlobalSettings.size ? ' selected' : '') + '>' + esc(s.l) + '</option>'
    ).join('');
    // v2.3.12 : modal simplifié — placement/size sont maintenant par alerte.
    overlay.innerHTML = '<div class="alert-modal">'
      + '<div class="alert-modal-head"><h3>Délai entre alertes</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
      + '<div class="alert-modal-body">'
      +   '<!-- v2.3.12 : placement/size retirés (par alerte maintenant) -->'
      +   '<div class="alert-field" style="display:none">'
      +     '<label class="alert-field-label">Placement à l\'écran</label>'
      +     '<select id="ags-placement" class="alert-field-input">' + placementOpts + '</select>'
      +   '</div>'
      +   '<div class="alert-field" style="display:none">'
      +     '<label class="alert-field-label">Taille</label>'
      +     '<select id="ags-size" class="alert-field-input">' + sizeOpts + '</select>'
      +   '</div>'
      +   '<div class="alert-field">'
      +     '<label class="alert-field-label">Délai minimum entre deux alertes (minutes)</label>'
      +     '<input type="number" id="ags-gap" class="alert-field-input" min="0" max="120" step="1" value="' + _alertGlobalSettings.min_gap_minutes + '">'
      +     '<div class="alert-field-help">Après chaque validation d\'alerte, aucune autre alerte n\'apparaît sur l\'écran de l\'opérateur pendant ce délai. Évite qu\'il soit surchargé quand plusieurs alertes deviennent dues en même temps (typiquement à la reprise de production). 0 = pas de délai.</div>'
      +   '</div>'

      + '</div>'
      + '<div class="alert-modal-foot">'
      +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
      +   '<button type="button" class="btn" id="ags-save">Enregistrer</button>'
      + '</div></div>';
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    document.getElementById('ags-save').addEventListener('click', async () => {
      // v2.3.27 : fix — depuis v2.3.12 le modal n'a plus qu'un champ (le
      // délai). L'ancien code référençait ags-block qui n'est jamais rendu
      // → getElementById(...).checked throw → toast d'erreur silencieux.
      // On lit maintenant depuis _alertGlobalSettings (déjà chargé au boot).
      const gapInput = document.getElementById('ags-gap');
      const gapVal = gapInput ? parseInt(gapInput.value, 10) : 5;
      const payload = {
        placement: _alertGlobalSettings.placement || 'top-right',
        size: _alertGlobalSettings.size || 'medium',
        block_production: !!_alertGlobalSettings.block_production,
        min_gap_minutes: (isNaN(gapVal) || gapVal < 0) ? 5 : Math.min(gapVal, 120),
      };
      try {
        await api('/api/maintenance/alert-settings', { method: 'PUT', body: JSON.stringify(payload) });
        _alertGlobalSettings.min_gap_minutes = payload.min_gap_minutes;
        toast('Délai enregistré');
        close();
      } catch (e) { toast(e && e.message ? e.message : 'Erreur', true); }
    });
  });
}

function _stripAutoPrefix(nom) {
  if (!nom) return '';
  return String(nom).replace(/^Contr[oôö]le\s*:\s*\d+\s*[–\-]\s*/i, '');
}

async function previewAlert(id) {
  // v2.3.13 : refactor — appelle directement MysifaAlerts.simulate() au lieu
  // de dupliquer la logique de rendu. Toute évolution du runtime bénéficie
  // automatiquement au bouton "Tester sur moi".
  const a = _alertsData.find(x => x.id === id);
  if (!a) return;
  await loadAlertSettings();
  if (!window.MysifaAlerts || typeof window.MysifaAlerts.simulate !== 'function') {
    toast('Runtime alertes non chargé — impossible de tester', true);
    return;
  }
  if (typeof window.MysifaAlerts.start === 'function') {
    try { await window.MysifaAlerts.start(); } catch(_){}
  }
  await window.MysifaAlerts.simulate({
    id: a.id,
    nom: a.nom,
    linked_maint_code: a.linked_maint_code || '',
    params: a.params || {},
  });
}


function openEditAlertModal(id) {
  const a = _alertsData.find(x => x.id === id);
  if (!a) return;
  const isAuto = !!a.linked_maint_code;
  const overlay = document.createElement('div');
  overlay.className = 'alert-modal-overlay';
  overlay.innerHTML = '<div class="alert-modal">'
    + '<div class="alert-modal-head"><h3>Modifier l\'alerte' + (isAuto ? ' (auto)' : '') + '</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
    + '<div class="alert-modal-body">'
    +   _renderAlertFormFields(a.params, { nomReadonly: isAuto, nomValue: a.nom })
    + '</div>'
    + '<div class="alert-modal-foot">'
    +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
    +   '<button type="button" class="btn" id="edit-alert-save">Enregistrer</button>'
    + '</div></div>';
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  _afOnTriggerChange();
  document.getElementById('edit-alert-save').addEventListener('click', async () => {
    const body = {};
    if (!isAuto) {
      const nom = (document.getElementById('af-nom').value || '').trim();
      if (!nom) { toast('Titre obligatoire', true); return; }
      body.nom = nom;
    }
    const params = _afReadParams();
    if (!params) return;
    body.params = params;
    try {
      await api('/api/maintenance/alerts/' + id, { method: 'PATCH', body: JSON.stringify(body) });
      toast('Alerte mise à jour');
      close();
      await loadAlerts();
    } catch (e) { toast(e && e.message ? e.message : 'Erreur', true); }
  });
  setTimeout(() => (document.getElementById('af-nom') || document.getElementById('af-trigger-type'))?.focus(), 30);
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


</script>
<script>window.__MYSIFA_APP__='maintenance';</script>
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_cmdk.js"></script>
<script>
if(typeof window.MySifaDock !== 'undefined' && typeof window.MySifaDock.bootPageWidgets === 'function'){
  window.MySifaDock.bootPageWidgets();
}
</script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=11"></script>
<script src="/static/chat_widget_v2.js?v=8"></script>
<script src="/static/mysifa_timepicker.js?v=1.0"></script>
<script src="/static/mysifa_alert_form.js?v=2.4.18"></script>
<script src="/static/mysifa_maint_form.js?v=2.7.4-usure"></script>
<script src="/static/mysifa_alert_runtime.js?v=2.4.18"></script>
<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_impersonate.js"></script>

<!-- Modal saisie créneau (opérateur : ouvre au clic sur une carte).
     Liste toutes les ops du créneau, chacune avec son propre bouton
     "Enregistrer cette opération" — le statut/saisie est partagé au groupe. -->
<div class="op-modal-overlay" id="op-modal-saisie" onclick="if(event.target===this) opCloseSaisie()">
  <div class="op-modal" role="dialog" aria-modal="true" style="max-width:640px">
    <div class="op-modal-title">Session de maintenance</div>
    <div class="op-modal-sub">Renseigne durée et commentaire pour chaque opération réalisée, puis clique « Marquer comme terminée ».</div>
    <div class="op-modal-context" id="op-modal-saisie-ctx"></div>
    <div id="op-modal-saisie-ops"></div>
    <div class="op-modal-actions">
      <button type="button" class="btn" onclick="opCloseSaisie()">Fermer</button>
    </div>
  </div>
</div>

<!-- Modal single-op : marquer UNE opération d'un créneau comme terminée
     (ou modifier / annuler une opération déjà validée) -->
<div class="op-modal-overlay" id="op-modal-single" onclick="if(event.target===this) opCloseSingleModal()">
  <div class="op-modal" role="dialog" aria-modal="true" style="max-width:520px;position:relative">
    <button type="button" class="op-modal-close" aria-label="Fermer" onclick="opCloseSingleModal()">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
    <div class="op-modal-title" id="op-single-title">Marquer comme terminée</div>
    <div class="op-modal-sub" id="op-single-sub">—</div>
    <div class="op-single-op-title" id="op-single-code-line">—</div>
    <div class="op-single-op-name" id="op-single-name">—</div>
    <div id="op-single-consignes-block" style="display:none">
      <div class="op-consignes-label">Consignes de l'admin</div>
      <div class="op-consignes-panel" id="op-single-consignes-text">—</div>
    </div>
    <div class="op-form-row">
      <label for="op-single-duree">Durée réelle (min)</label>
      <input type="number" id="op-single-duree" min="0" step="1" placeholder="Optionnel">
    </div>
    <div class="op-form-row">
      <label for="op-single-comment">Commentaires</label>
      <textarea id="op-single-comment" rows="3" placeholder="Pièces changées, observations, remarques…"></textarea>
    </div>
    <div class="op-modal-actions op-single-actions">
      <button type="button" class="btn btn-danger-outline" id="op-single-cancel-validation" onclick="opCancelValidation()" style="display:none">Annuler la validation</button>
      <span class="op-single-actions-spacer"></span>
      <button type="button" class="btn op-btn-accent" id="op-single-submit" onclick="opSubmitSingleOp()">Marquer comme terminée</button>
    </div>
  </div>
</div>

<!-- Modal Enregistrer une opération (opérateur : source=non_planifie, statut=termine) -->
<div class="op-modal-overlay" id="op-modal-new" onclick="if(event.target===this) opCloseNewModal()">
  <div class="op-modal" role="dialog" aria-modal="true">
    <div class="op-modal-title" id="op-modal-new-title">Enregistrer une opération</div>
    <div class="op-modal-sub" id="op-modal-new-sub">Enregistre une opération de maintenance déjà effectuée. Elle sera marquée « Terminée » et rattachée à la machine sélectionnée.</div>
    <div class="op-form-row">
      <label for="op-new-date">Date de l'intervention *</label>
      <input type="date" id="op-new-date">
    </div>
    <div class="op-form-row" id="op-new-machine-mono-row">
      <label for="op-new-machine">Machine *</label>
      <select id="op-new-machine">
        <option value="Cohésio 1">Cohésio 1</option>
        <option value="Cohésio 2">Cohésio 2</option>
        <option value="DSI">DSI</option>
        <option value="Repiquage">Repiquage</option>
      </select>
    </div>
    <!-- v2.2.13 : mode admin — multi-machines (chips style "Nouveau créneau"). Une op créée par chip active. -->
    <div class="op-form-row" id="op-new-machines-multi-row" style="display:none">
      <label>Machines * <span style="font-weight:400;color:var(--muted);font-size:11px;text-transform:none;letter-spacing:0">(clique une ou plusieurs — une opération sera créée par machine)</span></label>
      <div id="op-new-machines-chips" class="case-ops-machines" style="padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px">
        <button type="button" class="case-mach-chip" data-mach="Cohésio 1" onclick="adminToggleMachChip(this)" aria-pressed="false">Cohésio 1</button>
        <button type="button" class="case-mach-chip" data-mach="Cohésio 2" onclick="adminToggleMachChip(this)" aria-pressed="false">Cohésio 2</button>
        <button type="button" class="case-mach-chip" data-mach="DSI" onclick="adminToggleMachChip(this)" aria-pressed="false">DSI</button>
        <button type="button" class="case-mach-chip" data-mach="Repiquage" onclick="adminToggleMachChip(this)" aria-pressed="false">Repiquage</button>
      </div>
    </div>
    <div class="op-form-row" id="op-new-code-row">
      <label for="op-new-code">Code opération *</label>
      <select id="op-new-code"></select>
      <a href="javascript:void(0)" id="op-new-switch-libre" class="op-new-mode-link" onclick="opSwitchMode('inhabituelle')">Pas dans la liste ? Décrire une intervention inhabituelle</a>
    </div>
    <div class="op-form-row libre-titre-wrap" id="op-new-titre-libre-row" style="display:none">
      <label for="op-new-titre-libre">Titre de l'intervention *</label>
      <input type="text" id="op-new-titre-libre" autocomplete="off" maxlength="200" placeholder="Ex : Remplacement joint pompe hydraulique" oninput="opNewLibreOnInput()">
      <div class="libre-autocomplete-panel" id="op-new-libre-autocomplete-panel" style="display:none"></div>
      <a href="javascript:void(0)" id="op-new-switch-catalogue" class="op-new-mode-link" onclick="opSwitchMode('catalogue')">← Revenir au catalogue</a>
    </div>
    <div class="op-form-row">
      <label for="op-new-duree">Durée réelle (min)</label>
      <input type="number" id="op-new-duree" min="0" step="1" placeholder="Optionnel">
    </div>
    <div class="op-form-row">
      <label for="op-new-comment">Commentaires</label>
      <textarea id="op-new-comment" rows="3" placeholder="Pièces changées, observations, remarques…"></textarea>
    </div>
    <div class="op-modal-actions">
      <button type="button" class="btn" onclick="opCloseNewModal()">Annuler</button>
      <button type="button" class="btn op-btn-accent" id="op-modal-new-submit" onclick="opSubmitNew()">Enregistrer</button>
    </div>
  </div>
</div>

<!-- v180 : Modal Intervention libre (creation rapide sans passer par le catalogue) -->
<div class="op-modal-overlay" id="libre-modal" onclick="if(event.target===this) libreCloseModal()">
  <div class="op-modal" role="dialog" aria-modal="true">
    <div class="op-modal-title">Intervention libre</div>
    <div class="op-modal-sub">Enregistre une intervention ponctuelle sans creer de code du catalogue.</div>
    <div class="op-form-row">
      <label for="libre-date">Date de l'intervention *</label>
      <input type="date" id="libre-date">
    </div>
    <div class="op-form-row">
      <label for="libre-machine">Machine *</label>
      <select id="libre-machine">
        <option value="Cohésio 1">Cohésio 1</option>
        <option value="Cohésio 2">Cohésio 2</option>
        <option value="DSI">DSI</option>
        <option value="Repiquage">Repiquage</option>
      </select>
    </div>
    <div class="op-form-row libre-titre-wrap">
      <label for="libre-titre">Titre de l'intervention *</label>
      <input type="text" id="libre-titre" autocomplete="off" placeholder="Ex : Remplacement joint pompe hydraulique" oninput="libreOnTitreInput()">
      <div class="libre-autocomplete-panel" id="libre-autocomplete-panel" style="display:none"></div>
    </div>
    <div class="op-form-row">
      <label for="libre-duree">Durée (min)</label>
      <input type="number" id="libre-duree" min="0" step="1" placeholder="Optionnel — durée de l'intervention en minutes">
    </div>
    <div class="op-form-row">
      <label for="libre-comment">Commentaires</label>
      <textarea id="libre-comment" rows="3" placeholder="Optionnel — details, pieces changees, remarques..."></textarea>
    </div>
    <div class="op-modal-actions">
      <button type="button" class="btn" onclick="libreCloseModal()">Annuler</button>
      <button type="button" class="btn op-btn-accent" onclick="libreSubmit()">Enregistrer</button>
    </div>
  </div>
</div>


<script>
/* ── JS multi-rôle : Mes tâches / Planning / Nouvelle intervention / Admin create ──
   Chargé dans tous les cas, mais les fonctions ne sont utiles qu'au bon rôle.
   L'état des tâches côté page est stocké dans MAINT_STATE. */
'use strict';

// v179 : MAINT_ROLE deja defini au debut du 1er script (var hoiste).
// Reassignation defensive au cas ou body.data-maint-role aurait change.
MAINT_ROLE = (document.body.getAttribute('data-maint-role') || 'admin');
const MAINT_STATE = {
  tasks: [],
  codes: [],
  operators: [],
  saisieTaskId: null,
  newModalAdminMode: false,  // v2.2.13 : true si modal ouverte via adminOpenRegisterOpModal
};

function _fmtDateISO(d){
  const p = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + p(d.getMonth()+1) + '-' + p(d.getDate());
}
function _catClass(cat){ return 'op-cat-' + (cat || 'autre'); }
// Helpers unifiés pour la typologie 3 catégories (v178, renommage labels v179).
// Valeurs DB : 'controles', 'entretien', 'remplacements'.
// Labels UI : Contrôles, Nettoyage, Interventions.
// 'interventions' (legacy) et 'suivi' (legacy) sont remappés vers 'entretien'.
function _maintCatLabelFront(cat){
  if(cat === 'remplacements') return 'Interventions';
  if(cat === 'entretien' || cat === 'interventions' || cat === 'suivi') return 'Nettoyage';
  return 'Contrôles';
}
function _maintCatCssFront(cat){
  if(cat === 'remplacements') return 'remplacements';
  if(cat === 'entretien' || cat === 'interventions' || cat === 'suivi') return 'entretien';
  return 'controles';
}
function _statutLabel(s){
  // 'invalidee' manquait : le repli `|| s` affichait le libellé brut.
  return { a_faire:'À faire', en_cours:'En cours', termine:'Terminé',
           reporte:'Reporté', invalidee:'Invalidée' }[s] || s;
}

// v2.7.1 — Statut AFFICHÉ d'une opération, dérivé du créneau qui la porte.
//
// Une opération jamais saisie sur un créneau clôturé n'est pas « À faire » :
// elle ne le sera jamais. Elle s'affichait pourtant avec le même libellé et la
// même pastille grise qu'une opération d'un créneau de demain — impossible de
// distinguer « pas encore fait » de « jamais fait » sans aller lire la date.
//
// On le DÉRIVE plutôt que de l'écrire en base : aucune migration, aucun
// déclencheur à maintenir (ni job, ni écriture opportuniste au chargement), et
// rien à rétro-corriger le jour où la règle change. Le statut réel reste
// `a_faire` — une requête SQL ne verra donc pas « Non réalisé », c'est le prix
// assumé de la solution dérivée.
//
// `evOrDate` accepte un event ({date} côté calendrier, {date_prevue} côté
// serveur) ou directement une date ISO.
function _opStatutView(statut, evOrDate){
  const s = statut || 'a_faire';
  const d = (typeof evOrDate === 'string')
    ? evOrDate
    : ((evOrDate && (evOrDate.date || evOrDate.date_prevue)) || '');
  if((s === 'a_faire' || s === 'en_cours') && d && _calIsPastIso(d)){
    return { cls: 'reporte', label: 'Non réalisé' };
  }
  return { cls: s, label: _statutLabel(s) };
}

// v2.7.1 — Point d'invalidation unique des listes derivees du catalogue.
//
// Trois caches vivent en parallele dans la page et sont alimentes par
// /api/maintenance/codes : MAINT_STATE.codes (modal « Enregistrer une
// operation »), OPS_TYPES_STATE (filtres + selection d'operation) et
// CTRL_TYPES_STATE (controles ponctuels). Aucun n'etait purge apres une
// suppression : le code disparaissait du catalogue mais restait proposé à la
// saisie jusqu'au rechargement complet de la page.
//
// Tout ce qui modifie le catalogue (creation, modification, suppression,
// archivage, reactivation) appelle ce point d'entree — y compris depuis
// /settings et depuis le module partage, d'ou l'exposition sur window.
window.maintOnCatalogueChanged = async function(){
  MAINT_STATE.codes = [];  // cache de opFetchCodes(), purement local
  if(typeof loadOpsTypes === 'function'){
    try{ await loadOpsTypes(); }catch(e){}
  }
  if(typeof loadCtrlTypes === 'function'){
    try{ await loadCtrlTypes(); }catch(e){}
  }
  // Re-rendus defensifs : chaque vue n'existe que si son onglet a ete ouvert.
  try{ if(typeof renderOps === 'function') renderOps(); }catch(e){}
  try{ if(typeof renderOpsTypes === 'function') renderOpsTypes(); }catch(e){}
  try{ if(typeof renderCtrlTypes === 'function') renderCtrlTypes(); }catch(e){}
};

async function opFetchCodes(){
  if(MAINT_STATE.codes.length) return MAINT_STATE.codes;
  const r = await fetch('/api/maintenance/codes', { credentials:'include' });
  if(!r.ok){ MAINT_STATE.codes = []; return []; }
  const d = await r.json();
  // /api/maintenance/codes renvoie { items:[{code, label, categorie, niveau, periodique, ...}] }
  MAINT_STATE.codes = (d.items || d.codes || []).map(c => ({
    code: c.code, label: c.label, categorie: c.categorie,
    niveau: c.niveau, periodique: !!c.periodique,
    intervalle: c.intervalle || '',
  }));
  return MAINT_STATE.codes;
}

async function admFetchOperators(){
  if(MAINT_STATE.operators.length) return MAINT_STATE.operators;
  const r = await fetch('/api/maintenance/operators', { credentials:'include' });
  if(!r.ok){ MAINT_STATE.operators = []; return []; }
  const d = await r.json();
  MAINT_STATE.operators = d.operators || [];
  return MAINT_STATE.operators;
}

/* ── Vue Mes tâches ──────────────────────────────────────────────── */

async function opLoadTasks(){
  // v2.2.47 : autorise opérateur ET admin naviguant sur Mes tâches
  // (body.admin-op-active), sinon ne fetch pas inutilement.
  const isAdminOnOpView = (MAINT_ROLE !== 'operator' && document.body.classList.contains('admin-op-active'));
  if(MAINT_ROLE !== 'operator' && !isAdminOnOpView) return;
  const today = new Date();
  const in60 = new Date(); in60.setDate(today.getDate() + 60);
  const url = '/api/maintenance/events?date_from=' + _fmtDateISO(today) +
              '&date_to=' + _fmtDateISO(in60) + '&_=' + Date.now();
  const r = await fetch(url, { credentials:'include', cache: 'no-store' });
  if(!r.ok){
    // NE PAS wiper : garde la version en mémoire pour éviter que la vue
    // se vide brutalement si l'endpoint 500 temporairement (ex. schema DB
    // pas encore migré). Log pour diagnostic.
    console.warn('[opLoadTasks] fetch KO status=', r.status, '— MAINT_STATE.tasks conservé.');
    return;
  }
  const data = await r.json();
  const meRaw = (S && S.me) ? S.me.id : null;
  // Coerce en Number pour éviter les mismatches int/string entre session et
  // opérateurs renvoyés par le backend.
  const meId = meRaw != null ? Number(meRaw) : null;
  const events = data.events || [];
  // Filtre robuste : garde un event si l'user est dans le groupe (comparaison
  // via ==) OU s'il en est le créateur (fallback pour les cas où les operators
  // n'auraient pas été synchronisés côté serveur).
  MAINT_STATE.tasks = meId != null
    ? events.filter(ev => {
        const inGroup = (ev.operators || []).some(o => Number(o.id) === meId);
        const isCreator = Number(ev.created_by) === meId;
        return inGroup || isCreator;
      })
    : [];
  // Diagnostic : trace en console si un event a été filtré out alors qu'il
  // devrait apparaître (utile pour debug remote via DevTools).
  if(events.length && !MAINT_STATE.tasks.length){
    console.warn('[opLoadTasks] Tous les events filtrés out. meId=', meId,
                 'events=', events.map(ev => ({ id: ev.id, created_by: ev.created_by, operators: ev.operators })));
  }
  opRenderTasks();
}

// v2.2.47 : auto-refresh silencieux des tâches (poll 20s).
// Utile quand plusieurs opérateurs travaillent sur le même créneau : chacun
// voit l'avancement de l'autre en temps réel sans avoir à changer de section.
// Pause si tab en background ou modal ouvert (évite steal focus + fetch inutile).
let _opAutoRefreshInterval = null;
const _OP_AUTO_REFRESH_MS = 20000;
function _opShouldAutoRefresh(){
  // Actif seulement si l'onglet est visible
  if(document.visibilityState !== 'visible') return false;
  // Actif seulement si l'user est sur la vue Mes tâches (op-tasks)
  const onOpTasks = MAINT_ROLE === 'operator' ||
    (document.body.classList.contains('admin-op-active') &&
     document.getElementById('view-op-tasks') &&
     document.getElementById('view-op-tasks').classList.contains('active'));
  if(!onOpTasks) return false;
  // Pause si un modal opérateur est ouvert (single-op, saisie, new, etc.)
  const anyOpen = document.querySelector('.op-modal-overlay.active');
  if(anyOpen) return false;
  return true;
}
function _opAutoRefreshTick(){
  if(!_opShouldAutoRefresh()) return;
  try{
    // Silent : pas de spinner, pas de toast. En cas d'erreur, opLoadTasks
    // logue en console mais ne wipe pas la vue.
    if(typeof opLoadTasks === 'function') opLoadTasks();
  }catch(e){ console.warn('[opAutoRefresh]', e); }
}
function opAutoRefreshStart(){
  if(_opAutoRefreshInterval) return;
  _opAutoRefreshInterval = setInterval(_opAutoRefreshTick, _OP_AUTO_REFRESH_MS);
}
function opAutoRefreshStop(){
  if(_opAutoRefreshInterval){
    clearInterval(_opAutoRefreshInterval);
    _opAutoRefreshInterval = null;
  }
}
// Refresh immédiat quand l'user revient sur l'onglet (visibilitychange).
document.addEventListener('visibilitychange', () => {
  if(document.visibilityState === 'visible') _opAutoRefreshTick();
});
// Démarre le polling au chargement.
opAutoRefreshStart();

function _countRemainingOps(ev){
  return (ev.ops || []).filter(o => o.statut !== 'termine' && o.statut !== 'invalidee').length;  // v2.5.10 : invalidee = solde, ne compte pas
}

// Regroupe les ops d'un event par machine. Une op sans machine tombe dans un
// groupe "Sans machine". Une op multi-machines apparaît dans chaque groupe.
function _groupOpsByMachine(ev){
  const groups = new Map();
  const ops = (ev && ev.ops) ? ev.ops : [];
  for(const o of ops){
    let machines = Array.isArray(o.machines) ? o.machines.slice() : [];
    if(!machines.length){
      machines = ev.machine ? [ev.machine] : ['Sans machine'];
    }
    for(const m of machines){
      if(!groups.has(m)) groups.set(m, []);
      groups.get(m).push(o);
    }
  }
  // v2.2.64 : ordre canonique stable — _MACHINE_ORDER d'abord, puis alphabétique
  // pour les machines hors liste. Évite l'ordre non déterministe issu de la
  // première occurrence dans ev.ops.
  const canon = (typeof _MACHINE_ORDER !== 'undefined') ? _MACHINE_ORDER : [];
  const rank = new Map(canon.map((m, i) => [m, i]));
  const sortedMachines = [...groups.keys()].sort((a, b) => {
    const ra = rank.has(a) ? rank.get(a) : Infinity;
    const rb = rank.has(b) ? rank.get(b) : Infinity;
    if(ra !== rb) return ra - rb;
    return String(a).localeCompare(String(b), 'fr', {sensitivity:'base'});
  });
  return sortedMachines.map(m => ({ machine: m, ops: groups.get(m) }));
}

function _renderOpCard(ev, opts){
  opts = opts || {};
  const isToday = !!opts.isToday;
  const isDone = !!opts.isDone;
  const time = (ev.heure_debut && ev.heure_fin)
    ? (ev.heure_debut + ' – ' + ev.heure_fin)
    : '<em style="color:var(--muted);font-style:normal">Sans créneau horaire</em>';
  const remaining = _countRemainingOps(ev);
  const totalOps = (ev.ops || []).length;
  const doneAll = (remaining === 0 && totalOps > 0);
  const groups = _groupOpsByMachine(ev);
  const previewLines = [];
  let printedGroups = 0;
  let printedTruncated = false;
  const MAX_LINES = isToday ? Infinity : 5;
  // Purification : quand l'event ne contient qu'une seule op, le badge statut
  // du top-right (summary) est déjà éloquent → on masque le pill statut dans
  // la ligne op pour éviter le doublon visuel.
  const singleOp = totalOps === 1;
  for(const g of groups){
    if(previewLines.length + 2 > MAX_LINES){ printedTruncated = true; break; }
    let opsInThisGroup = 0;
    for(const o of g.ops){
      if(previewLines.length >= MAX_LINES){ printedTruncated = true; break; }
      const _sv = _opStatutView(o.statut, ev);
      const statusPill = singleOp
        ? ''
        : `<span class="op-status op-status-${_sv.cls}" style="position:static;font-size:9px;padding:2px 5px">${_sv.label}</span>`;
      previewLines.push(`<div style="display:flex;align-items:center;gap:6px;font-size:12px;margin-top:5px">
        <span class="op-code" style="font-size:11px;padding:2px 7px">${o.code}</span>
        <span style="color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${o.code_label || '—'}</span>
        ${statusPill}
      </div>`);
      opsInThisGroup++;
    }
    if(opsInThisGroup > 0) printedGroups++;
  }
  const opsPreview = previewLines.join('');
  const remainingOps = totalOps - printedGroups >= 0 ? Math.max(0, totalOps - previewLines.length) : 0;
  const more = (printedTruncated && remainingOps > 0)
    ? `<div style="font-size:11px;color:var(--muted);margin-top:6px">+ ${remainingOps} autre${remainingOps > 1 ? 's' : ''} opération${remainingOps > 1 ? 's' : ''}</div>`
    : '';
  const srcBadge = (ev.source === 'non_planifie') ? '<span class="op-badge-source">Non planifiée</span>' : '';
  const _cardClos = _calIsPastIso(ev.date_prevue || ev.date || '');
  const summary = doneAll
    ? '<span class="op-status op-status-termine" style="position:static">Terminé</span>'
    : (_cardClos
        ? '<span class="op-status op-status-reporte" style="position:static">Non réalisé</span>'
        : (remaining < totalOps
            ? `<span class="op-status op-status-en_cours" style="position:static">${remaining} restant${remaining > 1 ? 'es' : 'e'}</span>`
            : `<span class="op-status op-status-a_faire" style="position:static">À faire</span>`));
  const dateLine = isToday ? '' : `<div style="font-size:12px;color:var(--muted);margin-top:2px">${_fmtDateFrShort(ev.date_prevue)}</div>`;
  const cta = isToday
    ? `<button type="button" class="btn op-btn-accent op-card-cta" onclick="event.stopPropagation();opOpenSaisie(${ev.id})">
         <span class="btn-ico"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg></span>
         ${doneAll ? 'Voir la session' : 'Commencer la session'}
       </button>`
    : '';
  // Actions Modifier / Supprimer si l'opérateur est le créateur d'une non_planifie
  const meId = (S && S.me) ? S.me.id : null;
  const isMine = (ev.source === 'non_planifie' && meId != null && ev.created_by === meId);
  const mineBadge = isMine ? '<span class="op-card-badge-mine">Mienne</span>' : '';
  const actions = isMine
    ? `<div class="op-card-actions">
         <button type="button" class="op-card-action-btn" title="Modifier" onclick="event.stopPropagation();opOpenEditModal(${ev.id})">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
         </button>
         <button type="button" class="op-card-action-btn danger" title="Supprimer" onclick="event.stopPropagation();opDeleteEvent(${ev.id})">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>
         </button>
       </div>`
    : '';
  const clickHandler = isToday ? '' : `onclick="opOpenSaisie(${ev.id})"`;
  // Purification card head : la machine est déjà dans le bloc parent (block-head)
  // → on n'affiche dans le head que les badges informationnels. Si pas de badges,
  // on omet complètement le head pour un look plus propre.
  const headContent = `${mineBadge}`;
  const headHtml = headContent.trim() ? `<div class="op-card-head">${headContent}</div>` : '';
  return `
    <div class="op-card ${isMine ? 'owned-by-me' : ''} ${isDone ? 'is-done' : ''}" ${clickHandler}>
      <div class="op-status-wrap" style="position:absolute;top:14px;right:14px">${summary}</div>
      ${headHtml}
      ${dateLine}
      <div style="font-size:12px;color:var(--text2)">${time}</div>
      <div>${opsPreview}${more}</div>
      ${cta}
      ${actions}
    </div>`;
}

function _fmtDateFrShort(iso){
  if(!iso) return '';
  try{
    const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if(!m) return iso;
    const d = new Date(parseInt(m[1],10), parseInt(m[2],10)-1, parseInt(m[3],10));
    return d.toLocaleDateString('fr-FR', {weekday:'short', day:'2-digit', month:'short'});
  }catch(e){ return iso; }
}

// Ordre canonique des machines pour l'affichage stacked (top-level).
const _MACHINE_ORDER = ['Cohésio 1', 'Cohésio 2', 'DSI', 'Repiquage'];
const OP_TASKS_SHOW_TERMINE_KEY = 'mysifa_op_tasks_show_termine_v1';

function _getShowTermine(){
  try{ return localStorage.getItem(OP_TASKS_SHOW_TERMINE_KEY) === '1'; }
  catch(e){ return false; }
}
function opToggleShowTermine(on){
  try{ localStorage.setItem(OP_TASKS_SHOW_TERMINE_KEY, on ? '1' : '0'); }catch(e){}
  opRenderTasks();
}

// Retourne les machines couvertes par un op (fallback event.machine si op.machines vide).
function _opMachines(op, ev){
  let m = Array.isArray(op.machines) ? op.machines.slice() : [];
  if(!m.length && ev && ev.machine){
    m = String(ev.machine).split('·').map(s => s.trim()).filter(Boolean);
  }
  return m;
}

// Groupe les events d'une machine en 2 sacs :
//  - planifieEvents : events avec source='planifie', chacun devient une boîte créneau
//  - nonPlanifieOps : ops individuelles de tous les events source='non_planifie',
//                     regroupées dans un seul bloc "Interventions non-programmées"
function _bucketsForMachine(events, machine, showTermine){
  const planifie = [];
  const nonPlanifieOps = [];
  for(const ev of events){
    const ops = (ev.ops || []);
    const filtered = [];
    for(const op of ops){
      const machines = _opMachines(op, ev);
      if(!machines.includes(machine)) continue;
      if(op.statut === 'invalidee') continue;  // v2.5.11 : invalidee JAMAIS visible cote operateur
      if(!showTermine && op.statut === 'termine') continue;
      filtered.push(op);
    }
    if(!filtered.length) continue;
    if(ev.source === 'non_planifie'){
      // Chaque op non_planifie devient une carte à plat dans le bloc unique.
      for(const op of filtered){
        nonPlanifieOps.push({ op, ev });
      }
    } else {
      const allDone = filtered.every(o => o.statut === 'termine' || o.statut === 'invalidee');  // v2.5.10
      planifie.push({ ev, ops: filtered, allDone });
    }
  }
  // Tri des créneaux : chrono par heure_debut, tie-break par id.
  planifie.sort((a, b) => {
    const ha = a.ev.heure_debut || 'zz';
    const hb = b.ev.heure_debut || 'zz';
    if(ha !== hb) return ha.localeCompare(hb);
    return (a.ev.id || 0) - (b.ev.id || 0);
  });
  // Tri des ops non_planifie : par date_prevue puis id.
  nonPlanifieOps.sort((a, b) => {
    const da = a.ev.date_prevue || '';
    const db = b.ev.date_prevue || '';
    if(da !== db) return da.localeCompare(db);
    return (b.ev.id || 0) - (a.ev.id || 0);
  });
  return { planifie, nonPlanifieOps };
}

// Rendu d'une carte d'op individuelle (utilisé dans les créneaux ET dans le bloc non-programmées).
function _renderOpCardIndividual(op, ev, opts){
  opts = opts || {};
  const showMachine = !!opts.showMachine;
  const isDone = op.statut === 'termine';
  const statusLabel = _opStatutView(op.statut, ev).label;
  // Actions Modifier/Supprimer visibles uniquement sur les cartes d'ops
  // non_planifie créées par l'user courant (interventions déclarées via
  // "Enregistrer une opération").
  const meId = (S && S.me) ? S.me.id : null;
  const canManage = (ev.source === 'non_planifie') && (meId != null) && (ev.created_by === meId);
  const actionsHtml = canManage ? `
    <div class="op-op-card-footer-actions">
      <button type="button" class="op-op-card-mini-btn" title="Modifier l'intervention" onclick="event.stopPropagation();opOpenEditModal(${ev.id})">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
      </button>
      <button type="button" class="op-op-card-mini-btn danger" title="Supprimer l'intervention" onclick="event.stopPropagation();opDeleteEvent(${ev.id})">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>
      </button>
    </div>` : '';
  // v185 : chip consignes cliquable sous le titre, plus visible qu'une icône dans le head
  const consignes = (op.consignes || '').trim();
  const hasConsignes = consignes.length > 0;
  const consignesChip = hasConsignes
    ? `<button type="button" class="op-op-consignes-chip" onclick="event.stopPropagation();opShowConsignes(${ev.id}, ${op.id})">
         <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
         <span>Consignes de l'admin</span>
       </button>`
    : '';
  const machinesList = showMachine ? _opMachines(op, ev) : [];
  const machineChip = (showMachine && machinesList.length)
    ? `<div class="op-op-card-machine"><span class="op-op-card-machine-dot"></span><span class="op-op-card-machine-lbl">${machinesList.map(m => escHtml(m)).join(' · ')}</span></div>`
    : '';
  return `<div class="op-op-card ${isDone ? 'is-done' : ''}">
    <div class="op-op-card-head">
      <span class="op-code">${op.code}</span>
      <span class="op-op-card-status op-status op-status-${op.statut}">${statusLabel}</span>
    </div>
    <div class="op-op-card-title">${escHtml(op.code_label || '—')}</div>
    ${machineChip}
    ${consignesChip}
    <button type="button" class="op-op-card-cta ${isDone ? 'is-done' : ''}" onclick="opOpenSingleOpModal(${ev.id}, ${op.id})">
      ${isDone ? 'Voir / modifier' : 'Marquer comme terminée'}
    </button>
    ${actionsHtml}
  </div>`;
}

// v185 : affiche les consignes admin d'une op dans un mini-modal
function opShowConsignes(eventId, opId){
  const ev = (MAINT_STATE.tasks || []).find(x => x.id === eventId);
  if(!ev) return;
  const op = (ev.ops || []).find(o => o.id === opId);
  if(!op || !op.consignes) return;
  const overlay = document.createElement('div');
  overlay.className = 'op-modal-overlay active';
  overlay.style.zIndex = '1600';
  overlay.onclick = (e) => { if(e.target === overlay) overlay.remove(); };
  const machineLabel = (op.machines && op.machines[0]) || ev.machine || '';
  overlay.innerHTML =
    '<div class="op-modal op-consignes-modal" role="dialog" aria-modal="true">' +
      '<button type="button" class="op-modal-close" aria-label="Fermer" onclick="this.closest(\'.op-modal-overlay\').remove()">' +
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
      '</button>' +
      '<div class="op-consignes-modal-title">Consignes de l\'admin</div>' +
      '<div class="op-consignes-modal-sub">' + escHtml((op.code_label || op.code) + (machineLabel ? ' · ' + machineLabel : '')) + '</div>' +
      '<div class="op-consignes-panel">' + escHtml(op.consignes) + '</div>' +
    '</div>';
  document.body.appendChild(overlay);
}

// Rendu d'une boîte créneau (source=planifie).
function _renderEventBox(group){
  const ev = group.ev;
  const timeLabel = (ev.heure_debut && ev.heure_fin)
    ? (ev.heure_debut + ' – ' + ev.heure_fin)
    : 'Sans créneau';
  const nom = (ev.nom || '').trim();
  const meId = (S && S.me) ? S.me.id : null;
  const isMine = (meId != null && ev.created_by === meId);
  const isToday = ev.date_prevue === _fmtDateISO(new Date());
  const dateChip = isToday ? '' : `<span class="op-event-count">${_fmtDateFrShort(ev.date_prevue)}</span>`;
  const totalOpsInEvent = (ev.ops || []).length;
  const actionsHtml = isMine ? `
    <div class="op-event-box-actions">
      <button type="button" title="Modifier le créneau" onclick="opOpenEditModal(${ev.id})">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
      </button>
      <button type="button" class="danger" title="Supprimer" onclick="opDeleteEvent(${ev.id})">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>
      </button>
    </div>` : '';
  const opsHtml = group.ops.map(op => _renderOpCardIndividual(op, ev)).join('');
  const nomHtml = nom ? `<span class="op-event-box-nom">${escHtml(nom)}</span>` : '';
  return `<div class="op-event-box ${group.allDone ? 'all-done' : ''}">
    <div class="op-event-box-head">
      <strong>Créneau</strong>
      <span class="op-event-time">${escHtml(timeLabel)}</span>
      ${nomHtml}
      <span class="op-event-count">${totalOpsInEvent} op.</span>
      ${dateChip}
      ${isMine ? '<span class="op-event-mine">Mienne</span>' : ''}
      ${actionsHtml}
    </div>
    <div class="op-event-box-cards">${opsHtml}</div>
  </div>`;
}

// Rendu du bloc unique "Interventions non-programmées" (tous les source=non_planifie de la machine).
function _renderNonPlanifieBloc(items){
  if(!items.length) return '';
  const cards = items.map(({op, ev}) => _renderOpCardIndividual(op, ev)).join('');
  return `<div class="op-event-box event-non-planifie">
    <div class="op-event-box-head">
      <strong>Interventions non-programmées</strong>
      <span class="op-event-count">${items.length} op.</span>
    </div>
    <div class="op-event-box-cards">${cards}</div>
  </div>`;
}

function _isEventDone(ev){
  const ops = (ev && ev.ops) || [];
  if(!ops.length) return false;
  return ops.every(o => o.statut === 'termine' || o.statut === 'invalidee');  // v2.5.10 : invalidee = solde comme termine pour la completion
}

// Rendu d'une section machine (top-level).
function _renderMachineSection(machine, events, showTermine){
  const { planifie, nonPlanifieOps } = _bucketsForMachine(events, machine, showTermine);
  const totalOps = planifie.reduce((s, g) => s + g.ops.length, 0) + nonPlanifieOps.length;
  if(!totalOps) return '';  // machine sans contenu → skip
  const planifieHtml = planifie.map(_renderEventBox).join('');
  const nonPlanifieHtml = _renderNonPlanifieBloc(nonPlanifieOps);
  return `<section class="op-machine-section">
    <div class="op-machine-section-head">
      <span class="op-machine-section-dot"></span>
      <strong>${escHtml(machine)}</strong>
      <span class="op-machine-section-count">${totalOps} op.</span>
    </div>
    ${planifieHtml}
    ${nonPlanifieHtml}
  </section>`;
}

function opRenderTasks(){
  const listT = document.getElementById('op-cards-today');
  const listU = document.getElementById('op-cards-upcoming');
  const cntT = document.getElementById('op-count-today');
  const cntU = document.getElementById('op-count-upcoming');
  const summary = document.getElementById('op-tasks-count');
  const toggleCount = document.getElementById('op-toggle-count');
  if(!listT || !listU) return;

  const showTermine = _getShowTermine();
  const chk = document.getElementById('op-show-termine');
  if(chk) chk.checked = showTermine;

  const today = _fmtDateISO(new Date());
  const events = MAINT_STATE.tasks || [];
  const evToday = events.filter(ev => ev.date_prevue === today);
  const evUpcoming = events.filter(ev => ev.date_prevue > today);

  // Compte les ops visibles selon les nouvelles règles :
  // - Créneaux planifiés : ops filtrées par toggle (termine cachées si OFF)
  // - Ops perso (non_planifie) : uniquement si toggle ON, puis même filtre statut
  const _countVisibleOps = (evs) => {
    let n = 0;
    for(const ev of evs){
      const isPerso = (ev.source === 'non_planifie');
      if(isPerso && !showTermine) continue;
      for(const op of (ev.ops || [])){
        if(op.statut === 'invalidee') continue;  // v2.5.11 : invalidee JAMAIS visible cote operateur
        if(!showTermine && op.statut === 'termine') continue;
        n++;
      }
    }
    return n;
  };
  const visibleToday = _countVisibleOps(evToday);
  const visibleUpcoming = _countVisibleOps(evUpcoming);
  if(cntT) cntT.textContent = visibleToday;
  if(cntU) cntU.textContent = visibleUpcoming;
  if(summary){
    const total = visibleToday + visibleUpcoming;
    summary.textContent = total + (total > 1 ? ' opérations visibles' : ' opération visible');
  }

  // Compteur "terminées aujourd'hui" pour le toggle (créneaux + perso confondus)
  let doneTodayAll = 0;
  for(const ev of evToday){
    for(const op of (ev.ops || [])){
      if(op.statut === 'termine') doneTodayAll++;
    }
  }
  if(toggleCount) toggleCount.textContent = doneTodayAll;

  // Sépare créneaux planifiés / ops perso, trie les créneaux par heure_debut ASC.
  const _bucketEvents = (evs) => {
    const creneaux = [];
    const persos = [];
    for(const ev of evs){
      if(ev.source === 'non_planifie') persos.push(ev);
      else creneaux.push(ev);
    }
    creneaux.sort((a, b) => {
      const ha = a.heure_debut || 'zz';
      const hb = b.heure_debut || 'zz';
      if(ha !== hb) return ha.localeCompare(hb);
      return (a.id || 0) - (b.id || 0);
    });
    return { creneaux, persos };
  };

  const renderBucket = (evs, isToday) => {
    const { creneaux, persos } = _bucketEvents(evs);
    const creneauBoxes = creneaux
      .map(ev => _renderCreneauBox(ev, showTermine, isToday))
      .filter(Boolean);
    // v2.2.71 : la section perso est toujours affichée si des ops perso 'à faire'
    // existent. Le toggle contrôle uniquement l'inclusion des ops terminées (filtre
    // interne dans _renderPersoSection).
    const persoHtml = _renderPersoSection(persos, showTermine);
    return { creneauBoxes, persoHtml };
  };

  // Aujourd'hui
  const rT = renderBucket(evToday, true);
  if(!rT.creneauBoxes.length && !rT.persoHtml){
    const msg = showTermine
      ? '<strong>Aucune tâche aujourd\'hui</strong>Ta journée est vide.'
      : `<strong>Rien à faire aujourd\'hui</strong>${doneTodayAll ? 'Active « Afficher terminées » pour voir ce qui a été fait.' : 'Aucun créneau programmé.'}`;
    listT.innerHTML = '<div class="op-op-empty">' + msg + '</div>';
  } else {
    listT.innerHTML = rT.creneauBoxes.join('') + rT.persoHtml;
  }

  // À venir
  const rU = renderBucket(evUpcoming, false);
  if(!rU.creneauBoxes.length && !rU.persoHtml){
    listU.innerHTML = '<div class="op-op-empty"><strong>Aucun créneau à venir</strong>Ta liste est à jour.</div>';
  } else {
    listU.innerHTML = rU.creneauBoxes.join('') + rU.persoHtml;
  }
}

// v2.2.62 : rendu d'une grande case créneau (source=planifie), sous-sections par machine.
function _renderCreneauBox(ev, showTermine, isToday){
  const groups = _groupOpsByMachine(ev);
  // Filtre les ops par statut selon toggle, puis skip les machines devenues vides.
  const filteredGroups = groups.map(g => ({
    machine: g.machine,
    ops: g.ops.filter(o => showTermine || (o.statut !== 'termine' && o.statut !== 'invalidee'))  // v2.5.10
  })).filter(g => g.ops.length > 0);
  if(!filteredGroups.length) return '';

  const totalOps = filteredGroups.reduce((s, g) => s + g.ops.length, 0);
  const allOps = groups.reduce((arr, g) => arr.concat(g.ops), []);
  const totalAllOps = allOps.length;
  const doneAll = allOps.length > 0 && allOps.every(o => o.statut === 'termine' || o.statut === 'invalidee');  // v2.5.10

  const timeLabel = (ev.heure_debut && ev.heure_fin)
    ? (ev.heure_debut + ' – ' + ev.heure_fin)
    : 'Sans créneau';
  const nom = (ev.nom || '').trim();
  const dateChip = isToday ? '' : `<span class="op-event-count">${_fmtDateFrShort(ev.date_prevue)}</span>`;
  const nomHtml = nom ? `<span class="op-event-box-nom">${escHtml(nom)}</span>` : '';
  // Compteur : "X op." si tout visible, "X/Y op." si filtré
  const countLabel = (totalOps === totalAllOps)
    ? (totalOps + ' op.')
    : (totalOps + '/' + totalAllOps + ' op.');

  const groupsHtml = filteredGroups.map(g => {
    const cards = g.ops.map(op => _renderOpCardIndividual(op, ev)).join('');
    return `<div class="op-creneau-machine-group">
      <div class="op-creneau-machine-head">
        <span class="op-creneau-machine-dot"></span>${escHtml(g.machine)}
        <span class="op-creneau-machine-count">${g.ops.length} op.</span>
      </div>
      <div class="op-event-box-cards">${cards}</div>
    </div>`;
  }).join('');

  return `<div class="op-event-box ${doneAll ? 'all-done' : ''}">
    <div class="op-event-box-head">
      <strong>Créneau</strong>
      <span class="op-event-time">${escHtml(timeLabel)}</span>
      ${nomHtml}
      <span class="op-event-count">${countLabel}</span>
      ${dateChip}
    </div>
    ${groupsHtml}
  </div>`;
}

// v2.2.62 : section « Opérations personnelles » (source=non_planifie) — en bas, seulement si toggle ON.
function _renderPersoSection(evs, showTermine){
  if(!evs.length) return '';
  const items = [];
  for(const ev of evs){
    for(const op of (ev.ops || [])){
      if(op.statut === 'invalidee') continue;  // v2.5.11 : invalidee JAMAIS visible cote operateur
      if(!showTermine && op.statut === 'termine') continue;
      items.push({ op, ev });
    }
  }
  if(!items.length) return '';
  // Trie : date_prevue DESC (plus récent en premier), tie-break id DESC
  items.sort((a, b) => {
    const da = a.ev.date_prevue || '';
    const db = b.ev.date_prevue || '';
    if(da !== db) return db.localeCompare(da);
    return (b.ev.id || 0) - (a.ev.id || 0);
  });
  const cards = items.map(({op, ev}) => _renderOpCardIndividual(op, ev, {showMachine:true})).join('');
  return `<section class="op-perso-section">
    <div class="op-perso-section-head">
      <strong>Opérations personnelles</strong>
      <span class="op-perso-section-count">${items.length} op.</span>
      <span class="op-perso-section-hint">Enregistrées par toi, hors créneau planifié</span>
    </div>
    <div class="op-event-box-cards">${cards}</div>
  </section>`;
}

function opSetTab(name){
  document.querySelectorAll('[data-op-tab]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-op-tab') === name);
  });
  const panelT = document.getElementById('op-panel-today');
  const panelU = document.getElementById('op-panel-upcoming');
  if(panelT) panelT.classList.toggle('active', name === 'today');
  if(panelU) panelU.classList.toggle('active', name === 'upcoming');
}

/* ── Modal saisie ────────────────────────────────────────────────── */

function opOpenSaisie(eventId){
  const ev = MAINT_STATE.tasks.find(x => x.id === eventId);
  if(!ev) return;
  MAINT_STATE.saisieTaskId = eventId;
  const ctx = document.getElementById('op-modal-saisie-ctx');
  const time = (ev.heure_debut && ev.heure_fin) ? (ev.heure_debut + ' – ' + ev.heure_fin) : 'Sans créneau horaire';
  const groups = _groupOpsByMachine(ev);
  const machinesLabel = groups.map(g => g.machine).join(' · ') || (ev.machine || '—');
  ctx.innerHTML = `
    <span><strong>Machine${groups.length > 1 ? 's' : ''} :</strong> ${escHtml(machinesLabel)}</span>
    <span><strong>Date :</strong> ${ev.date_prevue}</span>
    <span><strong>Créneau :</strong> ${time}</span>
    ${ev.source === 'non_planifie' ? '<span class="op-badge-source">Non planifiée</span>' : ''}`;
  const wrap = document.getElementById('op-modal-saisie-ops');
  if(wrap){
    if(!groups.length){
      wrap.innerHTML = '<div style="text-align:center;color:var(--muted);padding:20px">Aucune opération.</div>';
    } else {
      // Un bloc par machine. Une op assignée à N machines apparaît dans N blocs
      // mais la saisie reste unique côté DB (opSubmitOpSaisie utilise op.id).
      wrap.innerHTML = groups.map(g => {
        const opsHtml = g.ops.map(op => {
          const catLbl = { controles:'Contrôle', interventions:'Nettoyage', entretien:'Nettoyage', remplacements:'Intervention', suivi:'Nettoyage' }[op.code_categorie] || op.code_categorie || '';
          const isDone = op.statut === 'termine';
          const isInvalid = op.statut === 'invalidee';
          // v2.5.10 : op invalidee → read-only, l'operateur ne peut pas la re-saisir.
          if(isInvalid){
            return '<div class="op-saisie-item" data-op-id="' + op.id + '" style="border:1px solid var(--border);border-left:3px solid var(--muted);border-radius:10px;padding:14px 16px;margin-top:12px;background:linear-gradient(90deg,rgba(148,163,184,.05) 0%,var(--card) 100%);opacity:.75">' +
              '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">' +
                '<span class="op-code">' + escHtml(op.code || '') + '</span>' +
                '<span class="op-cat ' + _catClass(op.code_categorie || 'autre') + '">' + escHtml(catLbl) + '</span>' +
                '<strong style="flex:1;font-size:13px;color:var(--text2);text-decoration:line-through;text-decoration-color:var(--muted)">' + escHtml(op.code_label || '\u2014') + '</strong>' +
                '<span style="padding:3px 9px;border-radius:6px;background:rgba(148,163,184,.18);color:var(--muted);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.4px">Invalid\u00e9e</span>' +
              '</div>' +
              '<div style="margin-top:10px;font-size:12px;color:var(--muted);line-height:1.5">Cette saisie a \u00e9t\u00e9 mise de c\u00f4t\u00e9 par un administrateur. Aucune action requise.</div>' +
            '</div>';
          }
          // Fusion pieces_changees + observations pour affichage : si les 2
          // étaient renseignées avant, on concatène pour ne rien perdre.
          const prevCommentaire = ((op.pieces_changees || '').trim() + '\n' + (op.observations || '').trim()).trim();
          return `
            <div class="op-saisie-item ${isDone ? 'is-done' : ''}" data-op-id="${op.id}" style="border:1px solid ${isDone ? 'var(--success,#34d399)' : 'var(--border)'};border-left-width:${isDone ? '3px' : '1px'};border-radius:10px;padding:14px 16px;margin-top:12px;background:${isDone ? 'linear-gradient(90deg,rgba(52,211,153,.06) 0%,var(--card) 100%)' : 'transparent'}">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
                <span class="op-code">${op.code}</span>
                <span class="op-cat ${_catClass(op.code_categorie || 'autre')}">${catLbl}</span>
                <strong style="flex:1;font-size:13px;color:var(--text)">${op.code_label || '—'}</strong>
                ${isDone ? '<span class="op-status op-status-termine" style="position:static">Terminé</span>' : ''}
              </div>
              <div class="op-form-row"><label>Durée réelle (min)</label>
                <input type="number" min="0" step="1" data-fld="duree_reelle_min" value="${op.duree_reelle_min || ''}" placeholder="Optionnel">
              </div>
              <div class="op-form-row"><label>Commentaires</label>
                <textarea data-fld="commentaire" rows="2" placeholder="Pièces changées, observations, remarques…">${prevCommentaire}</textarea>
              </div>
              <button type="button" class="btn op-btn-accent" style="width:100%;justify-content:center" onclick="opSubmitOpSaisie(${ev.id}, ${op.id}, this)">
                ${isDone ? 'Mettre à jour' : 'Marquer comme terminée'}
              </button>
            </div>`;
        }).join('');
        return `<div class="op-machine-group">
          <div class="op-machine-group-head"><span class="op-machine-dot"></span>${escHtml(g.machine)} · ${g.ops.length} opération${g.ops.length > 1 ? 's' : ''}</div>
          ${opsHtml}
        </div>`;
      }).join('');
    }
  }
  document.getElementById('op-modal-saisie').classList.add('active');
}

function opCloseSaisie(){
  MAINT_STATE.saisieTaskId = null;
  document.getElementById('op-modal-saisie').classList.remove('active');
}

async function opSubmitOpSaisie(eventId, opId, btnEl){
  // Le modal de session partage l'UI de "Enregistrer une opération" : statut
  // forcé à termine, commentaire unique. Une op multi-machines apparaît dans
  // plusieurs blocs de saisie — on cible le bloc du bouton cliqué.
  const item = (btnEl && btnEl.closest && btnEl.closest('.op-saisie-item'))
    || document.querySelector(`.op-saisie-item[data-op-id="${opId}"]`);
  if(!item) return;
  const val = (fld) => (item.querySelector(`[data-fld="${fld}"]`) || {}).value;
  const dureeStr = (val('duree_reelle_min') || '').trim();
  const dureeMin = dureeStr === '' ? null : parseInt(dureeStr, 10);
  if(dureeStr !== '' && (Number.isNaN(dureeMin) || dureeMin < 0)){
    if(typeof showToast === 'function') showToast('Durée invalide.', 'danger');
    return;
  }
  const comment = (val('commentaire') || '').trim() || null;
  const body = {
    statut: 'termine',
    duree_reelle_min: dureeMin,
    observations: comment,
  };
  const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/ops/' + encodeURIComponent(opId), {
    method:'PATCH', credentials:'include',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const err = await r.json().catch(()=>({}));
    if(typeof showToast === 'function') showToast('Erreur : ' + (err.detail || r.status), 'danger');
    else alert('Erreur : ' + (err.detail || r.status));
    return;
  }
  // Mise à jour in-place depuis la réponse — cohérent avec opSubmitSingleOp.
  try{
    const data = await r.json();
    if(data && data.event){
      const idx = (MAINT_STATE.tasks || []).findIndex(x => x.id === data.event.id);
      if(idx >= 0) MAINT_STATE.tasks[idx] = data.event;
      opRenderTasks();
    }
  }catch(e){}
  if(typeof showToast === 'function') showToast('Opération terminée.', 'success');
  opLoadTasks().catch(() => {});
  // Re-render du modal avec les données à jour (nouveau statut termine).
  opOpenSaisie(eventId);
}

// Ancien nom conservé pour compat (rien ne l'appelle en direct désormais).
async function opSubmitSaisie(){
  // No-op : la saisie se fait op par op via opSubmitOpSaisie.
}

/* ── Modal nouvelle intervention (opérateur) ──────────────────────── */

// État du modal : null = création, sinon id de l'event en cours d'édition
MAINT_STATE.editingEventId = null;

function _opResetModalFields(){
  const today = _fmtDateISO(new Date());
  const dateEl = document.getElementById('op-new-date');
  const machineEl = document.getElementById('op-new-machine');
  const codeEl = document.getElementById('op-new-code');
  const dureeEl = document.getElementById('op-new-duree');
  const commEl = document.getElementById('op-new-comment');
  if(dateEl) dateEl.value = today;
  if(machineEl) machineEl.value = 'Cohésio 1';
  if(codeEl && MAINT_STATE.codes && MAINT_STATE.codes.length) codeEl.value = MAINT_STATE.codes[0].code;
  if(dureeEl) dureeEl.value = '';
  if(commEl) commEl.value = '';
}

async function opOpenNewModal(){
  await opFetchCodes();
  MAINT_STATE.editingEventId = null;
  MAINT_STATE.editingIsLibre = false;
  MAINT_STATE.newModalMode = 'catalogue';  // v2 : mode par défaut
  MAINT_STATE.newLibreSelectedCode = null; // code catalogue si suggéré par autocomplete
  const sel = document.getElementById('op-new-code');
  sel.innerHTML = MAINT_STATE.codes.map(c =>
    `<option value="${c.code}">${c.code} — ${c.label}</option>`
  ).join('');
  document.getElementById('op-modal-new-title').textContent = 'Enregistrer une opération';
  document.getElementById('op-modal-new-sub').textContent = 'Choisis une opération dans le catalogue. Si elle ne s\'y trouve pas, décris une intervention inhabituelle.';
  document.getElementById('op-modal-new-submit').textContent = 'Enregistrer';
  _opResetModalFields();
  // Reset visibilité par mode Catalogue
  const codeRow = document.getElementById('op-new-code-row');
  const titreRow = document.getElementById('op-new-titre-libre-row');
  if(codeRow) codeRow.style.display = '';
  if(titreRow) titreRow.style.display = 'none';
  const titreEl = document.getElementById('op-new-titre-libre');
  if(titreEl) titreEl.value = '';
  const panel = document.getElementById('op-new-libre-autocomplete-panel');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
  // Pré-remplit avec la machine sélectionnée dans Mes tâches
  try{
    const currentMach = _getSelectedMachine();
    const machEl = document.getElementById('op-new-machine');
    if(machEl && currentMach) machEl.value = currentMach;
  }catch(e){}
  document.getElementById('op-modal-new').classList.add('active');
}

// v2.2.13 : entrée admin — ouvre la MÊME modal fusionnée que l'opérateur, avec :
//   - Machine multi-choix (checkboxes) au lieu du select mono
//   - Date d'intervention modifiable (déjà présente)
//   - Durée manuelle (déjà présente)
//   - Onglets Catalogue / Inhabituelle (déjà présents)
//   Une op créée par machine cochée. Opérateur = admin connecté (côté backend).
async function adminOpenRegisterOpModal(){
  await opFetchCodes();
  MAINT_STATE.editingEventId = null;
  MAINT_STATE.editingIsLibre = false;
  MAINT_STATE.newModalMode = 'catalogue';
  MAINT_STATE.newLibreSelectedCode = null;
  MAINT_STATE.newModalAdminMode = true;
  const sel = document.getElementById('op-new-code');
  sel.innerHTML = MAINT_STATE.codes.map(c =>
    `<option value="${c.code}">${c.code} — ${c.label}</option>`
  ).join('');
  document.getElementById('op-modal-new-title').textContent = 'Enregistrer une opération';
  document.getElementById('op-modal-new-sub').textContent = 'Choisis une opération dans le catalogue ou décris une intervention inhabituelle. Coche une ou plusieurs machines — une opération sera créée pour chaque machine.';
  document.getElementById('op-modal-new-submit').textContent = 'Enregistrer';
  _opResetModalFields();
  // Reset visibilité par mode Catalogue
  const codeRow = document.getElementById('op-new-code-row');
  const titreRow = document.getElementById('op-new-titre-libre-row');
  if(codeRow) codeRow.style.display = '';
  if(titreRow) titreRow.style.display = 'none';
  const titreEl = document.getElementById('op-new-titre-libre');
  if(titreEl) titreEl.value = '';
  const panel = document.getElementById('op-new-libre-autocomplete-panel');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
  // Bascule mono → multi-machines
  const monoRow = document.getElementById('op-new-machine-mono-row');
  const multiRow = document.getElementById('op-new-machines-multi-row');
  if(monoRow) monoRow.style.display = 'none';
  if(multiRow) multiRow.style.display = '';
  document.querySelectorAll('#op-new-machines-chips .case-mach-chip').forEach(ch => {
    ch.classList.remove('active');
    ch.setAttribute('aria-pressed', 'false');
  });
  // Date par défaut = aujourd'hui
  try{
    const dateEl = document.getElementById('op-new-date');
    if(dateEl && !dateEl.value){ dateEl.value = _fmtDateISO(new Date()); }
  }catch(e){}
  document.getElementById('op-modal-new').classList.add('active');
}

// v2.2.14 : toggle d'une chip machine dans la modal admin.
function adminToggleMachChip(btn){
  if(!btn) return;
  const active = btn.classList.toggle('active');
  btn.setAttribute('aria-pressed', active ? 'true' : 'false');
}

// v2 : switch entre modes Catalogue et Inhabituelle dans le modal fusionné.
function opSwitchMode(mode){
  MAINT_STATE.newModalMode = mode;
  MAINT_STATE.newLibreSelectedCode = null;
  const codeRow = document.getElementById('op-new-code-row');
  const titreRow = document.getElementById('op-new-titre-libre-row');
  if(mode === 'inhabituelle'){
    if(codeRow) codeRow.style.display = 'none';
    if(titreRow) titreRow.style.display = '';
    setTimeout(() => { const el = document.getElementById('op-new-titre-libre'); if(el) el.focus(); }, 60);
  } else {
    if(codeRow) codeRow.style.display = '';
    if(titreRow) titreRow.style.display = 'none';
    const panel = document.getElementById('op-new-libre-autocomplete-panel');
    if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
  }
}

// v2 : autocomplete côté modal fusionné (sur le champ titre libre).
//   Duplique la logique de libreOnTitreInput mais scopée sur op-new-* ids.
let _opNewLibreTimer = null;
async function opNewLibreOnInput(){
  const t = document.getElementById('op-new-titre-libre');
  const q = (t ? t.value : '').trim();
  MAINT_STATE.newLibreSelectedCode = null;
  clearTimeout(_opNewLibreTimer);
  const panel = document.getElementById('op-new-libre-autocomplete-panel');
  if(q.length < 2){
    if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
    return;
  }
  _opNewLibreTimer = setTimeout(async () => {
    try{
      const r = await fetch('/api/maintenance/codes/libres/autocomplete?q=' + encodeURIComponent(q) + '&limit=8', {credentials:'include'});
      if(!r.ok){ if(panel){ panel.style.display='none'; } return; }
      const d = await r.json();
      const suggestions = Array.isArray(d.suggestions) ? d.suggestions : [];
      if(!suggestions.length){
        if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
        return;
      }
      panel.innerHTML = suggestions.map(s =>
        '<div class="libre-suggestion" onclick="opNewLibreSelectSuggestion(\'' + escAttr(s.code) + '\', \'' + escAttr(s.label) + '\')">' +
          '<span class="libre-suggestion-label">' + escHtml(s.label) + '</span>' +
          '<span class="libre-suggestion-count">' + escHtml(s.code) + '</span>' +
        '</div>'
      ).join('');
      panel.style.display = 'block';
    }catch(e){
      if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
    }
  }, 220);
}

function opNewLibreSelectSuggestion(code, label){
  MAINT_STATE.newLibreSelectedCode = code;
  const t = document.getElementById('op-new-titre-libre');
  if(t) t.value = label;
  const panel = document.getElementById('op-new-libre-autocomplete-panel');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
}

async function opOpenEditModal(eventId){
  const ev = (MAINT_STATE.tasks || []).find(x => x.id === eventId);
  if(!ev){ alert('Créneau introuvable.'); return; }
  const meId = (S && S.me) ? S.me.id : null;
  if(ev.created_by !== meId){
    if(typeof showToast === 'function') showToast('Vous ne pouvez modifier que vos propres interventions.', 'danger');
    else alert('Vous ne pouvez modifier que vos propres interventions.');
    return;
  }
  // v2 : l'opérateur ne peut plus gérer les créneaux planifie (feature
  // "Nouvelle tâche" retirée). Les vieux planifie opérateurs ont été
  // nettoyés par la migration 184. Si un tel event apparaît encore
  // (edge case), on bloque avec un message clair.
  if(ev.source === 'planifie'){
    if(typeof showToast === 'function') showToast('Les créneaux planifiés sont gérés par l\'administrateur.', 'danger');
    else alert('Les créneaux planifiés sont gérés par l\'administrateur.');
    return;
  }
  // Créneau non_planifie → modal simple (édition d'une saisie rapide).
  const currentOp = (ev.ops && ev.ops[0]) ? ev.ops[0] : null;
  const isLibre = !!(currentOp && currentOp.code && String(currentOp.code).startsWith('LIB-'));
  MAINT_STATE.editingEventId = eventId;
  MAINT_STATE.editingIsLibre = isLibre;  // flag lu par opSubmitNew

  const codeRow = document.getElementById('op-new-code-row');
  const titreRow = document.getElementById('op-new-titre-libre-row');
  const sel = document.getElementById('op-new-code');
  const titreEl = document.getElementById('op-new-titre-libre');

  if(isLibre){
    // Mode libre : cache le dropdown code, montre le champ titre texte.
    if(codeRow) codeRow.style.display = 'none';
    if(titreRow) titreRow.style.display = '';
    if(titreEl) titreEl.value = currentOp.code_label || '';
  } else {
    // Mode code standard : dropdown code, cache titre.
    if(codeRow) codeRow.style.display = '';
    if(titreRow) titreRow.style.display = 'none';
    await opFetchCodes();
    sel.innerHTML = MAINT_STATE.codes.map(c =>
      `<option value="${c.code}">${c.code} — ${c.label}</option>`
    ).join('');
    if(currentOp && currentOp.code) sel.value = currentOp.code;
  }

  // Pré-remplit date/machine/durée/commentaires (communs)
  const dateEl = document.getElementById('op-new-date');
  if(dateEl) dateEl.value = ev.date_prevue || _fmtDateISO(new Date());
  const machineEl = document.getElementById('op-new-machine');
  if(machineEl && ev.machine) machineEl.value = ev.machine;
  const dureeEl = document.getElementById('op-new-duree');
  if(dureeEl) dureeEl.value = (currentOp && currentOp.duree_reelle_min != null) ? currentOp.duree_reelle_min : '';
  const commEl = document.getElementById('op-new-comment');
  if(commEl) commEl.value = (currentOp && currentOp.observations) ? currentOp.observations : '';
  document.getElementById('op-modal-new-title').textContent = isLibre ? 'Modifier l\'intervention libre' : 'Modifier l\'opération';
  document.getElementById('op-modal-new-sub').textContent = isLibre
    ? 'Ajuste le titre, la date, la machine ou les informations complémentaires.'
    : 'Ajuste la date, la machine, le code ou les informations complémentaires.';
  document.getElementById('op-modal-new-submit').textContent = 'Enregistrer les modifications';
  document.getElementById('op-modal-new').classList.add('active');
}

function opCloseNewModal(){
  MAINT_STATE.editingEventId = null;
  MAINT_STATE.editingIsLibre = false;
  MAINT_STATE.newModalMode = 'catalogue';
  MAINT_STATE.newLibreSelectedCode = null;
  MAINT_STATE.newModalAdminMode = false;  // v2.2.13
  // Reset visibilité par défaut : code visible, titre libre caché
  const codeRow = document.getElementById('op-new-code-row');
  const titreRow = document.getElementById('op-new-titre-libre-row');
  if(codeRow) codeRow.style.display = '';
  if(titreRow) titreRow.style.display = 'none';
  // v2.2.13 : reset multi-machines
  const monoRow = document.getElementById('op-new-machine-mono-row');
  const multiRow = document.getElementById('op-new-machines-multi-row');
  if(monoRow) monoRow.style.display = '';
  if(multiRow) multiRow.style.display = 'none';
  document.querySelectorAll('#op-new-machines-chips .case-mach-chip').forEach(ch => {
    ch.classList.remove('active');
    ch.setAttribute('aria-pressed', 'false');
  });
  const panel = document.getElementById('op-new-libre-autocomplete-panel');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
  document.getElementById('op-modal-new').classList.remove('active');
}

// Helper : PATCH le statut/durée/commentaires d'une op pour la marquer Terminée.
async function _patchOpTermine(eventId, opId, dureeMin, comment, doneAtIso){
  // v2.2.9 : doneAtIso optionnel — permet à l'admin de définir la date/heure
  //   exacte de saisie au moment de la création. Sinon backend pose now.
  const body = { statut: 'termine' };
  if(dureeMin != null && !Number.isNaN(dureeMin)) body.duree_reelle_min = dureeMin;
  if(comment) body.observations = comment;
  if(doneAtIso) body.done_at = doneAtIso;
  const r = await fetch('/api/maintenance/events/' + eventId + '/ops/' + opId, {
    method:'PATCH', credentials:'include',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const err = await r.json().catch(()=>({}));
    throw new Error(err.detail || r.status);
  }
}

// v2.2.9 : helper pour convertir une valeur date (YYYY-MM-DD) ou datetime en
// ISO Paris local YYYY-MM-DDTHH:MM:SS. Si seul une date est fournie (pas
// d'heure), on prend l'heure/minute/seconde actuelles pour tracer précisément.
function _toDoneAtIso(dateStr){
  if(!dateStr) return null;
  try{
    const pad = n => n < 10 ? '0' + n : '' + n;
    // Cas 1 : YYYY-MM-DD → complète avec heure actuelle
    if(/^\d{4}-\d{2}-\d{2}$/.test(dateStr)){
      const now = new Date();
      return dateStr + 'T' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
    }
    // Cas 2 : ISO datetime → convertit en local Paris
    const d = new Date(dateStr);
    if(isNaN(d.getTime())) return null;
    return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) +
      'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }catch(e){ return null; }
}

async function opSubmitNew(){
  // v2.2.13 : si admin mode, on route vers le flow multi-machines
  if(MAINT_STATE.newModalAdminMode && !MAINT_STATE.editingEventId){
    return adminSubmitRegisterOp();
  }
  const dateVal = document.getElementById('op-new-date').value;
  const machine = document.getElementById('op-new-machine').value;
  const isLibreEdit = !!MAINT_STATE.editingIsLibre;
  const titreLibre = (document.getElementById('op-new-titre-libre').value || '').trim();
  const code = document.getElementById('op-new-code').value;
  const dureeStr = document.getElementById('op-new-duree').value;
  const comment = (document.getElementById('op-new-comment').value || '').trim();
  const dureeMin = dureeStr === '' ? null : parseInt(dureeStr, 10);

  // v2 : mode création détecte MAINT_STATE.newModalMode.
  //      mode édition détecte MAINT_STATE.editingIsLibre.
  const editingIdForValid = MAINT_STATE.editingEventId;
  const isCreationInhabituelle = (editingIdForValid == null) && (MAINT_STATE.newModalMode === 'inhabituelle');
  const isCreationCatalogue    = (editingIdForValid == null) && !isCreationInhabituelle;

  // Validation champs obligatoires selon mode
  if(!dateVal || !machine){
    if(typeof showToast === 'function') showToast('Date et machine sont obligatoires.', 'danger');
    return;
  }
  if((isLibreEdit || isCreationInhabituelle) && !titreLibre){
    if(typeof showToast === 'function') showToast('Titre obligatoire.', 'danger');
    return;
  }
  if(isCreationCatalogue && !code){
    if(typeof showToast === 'function') showToast('Code opération obligatoire.', 'danger');
    return;
  }
  if(dureeStr !== '' && (Number.isNaN(dureeMin) || dureeMin < 0)){
    if(typeof showToast === 'function') showToast('Durée invalide.', 'danger');
    return;
  }

  const editingId = MAINT_STATE.editingEventId;
  if(editingId != null){
    // ─── Mode édition
    const ev = (MAINT_STATE.tasks || []).find(x => x.id === editingId);
    if(!ev){ opCloseNewModal(); return; }
    const currentOp = (ev.ops && ev.ops[0]) ? ev.ops[0] : null;
    const wasTermine = !!(currentOp && currentOp.statut === 'termine');
    try{
      // 1. PATCH /libres/{code} si titre libre change
      if(isLibreEdit && currentOp && currentOp.code){
        const currentTitre = (currentOp.code_label || '').trim();
        if(titreLibre !== currentTitre){
          const rTitre = await fetch('/api/maintenance/codes/libres/' + encodeURIComponent(currentOp.code), {
            method:'PATCH', credentials:'include',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({label: titreLibre}),
          });
          if(!rTitre.ok){ const err = await rTitre.json().catch(()=>({})); throw new Error(err.detail || 'Renommage titre échoué'); }
        }
      }

      // 2. PATCH event : machine et/ou date si changées
      const evPatch = {};
      if((ev.machine || '') !== machine) evPatch.machine = machine;
      if((ev.date_prevue || '') !== dateVal) evPatch.date_prevue = dateVal;
      if(Object.keys(evPatch).length){
        const r1 = await fetch('/api/maintenance/events/' + editingId, {
          method:'PATCH', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(evPatch),
        });
        if(!r1.ok){ const err = await r1.json().catch(()=>({})); throw new Error(err.detail || r1.status); }
      }

      // 3. Si code standard change (impossible en mode libre), replace op
      let opId = currentOp ? currentOp.id : null;
      if(!isLibreEdit && (!currentOp || currentOp.code !== code)){
        if(opId != null){
          const rDel = await fetch('/api/maintenance/events/' + editingId + '/ops/' + opId, {
            method:'DELETE', credentials:'include',
          });
          if(!rDel.ok){ const err = await rDel.json().catch(()=>({})); throw new Error(err.detail || rDel.status); }
        }
        const rAdd = await fetch('/api/maintenance/events/' + editingId + '/ops', {
          method:'POST', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({code, machines:[machine]}),
        });
        if(!rAdd.ok){ const err = await rAdd.json().catch(()=>({})); throw new Error(err.detail || rAdd.status); }
        const dataAdd = await rAdd.json();
        const newOp = (dataAdd.event && dataAdd.event.ops || []).find(o => o.code === code);
        opId = newOp ? newOp.id : opId;
      }

      // 4. PATCH op : durée + observations. Statut SEULEMENT si l'op était déjà termine
      //    (préserve statut a_faire pour les interventions modifiées avant validation).
      if(opId != null){
        if(wasTermine){
          // v2.2.9 : passe date_val comme done_at pour respect de la date saisie
          await _patchOpTermine(editingId, opId, dureeMin, comment, _toDoneAtIso(dateVal));
        } else {
          const patchBody = {};
          if(dureeMin != null && !Number.isNaN(dureeMin)) patchBody.duree_reelle_min = dureeMin;
          if(comment) patchBody.observations = comment;
          if(Object.keys(patchBody).length){
            const r4 = await fetch('/api/maintenance/events/' + editingId + '/ops/' + opId, {
              method:'PATCH', credentials:'include',
              headers:{'Content-Type':'application/json'},
              body: JSON.stringify(patchBody),
            });
            if(!r4.ok){ const err = await r4.json().catch(()=>({})); throw new Error(err.detail || r4.status); }
          }
        }
      }
      if(typeof showToast === 'function') showToast(isLibreEdit ? 'Intervention libre mise à jour.' : 'Opération mise à jour.', 'success');
      opCloseNewModal();
      await opLoadTasks();
      if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
    }catch(e){
      if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
      else alert('Erreur : ' + e.message);
    }
    return;
  }

  // ─── Mode création (Catalogue ou Inhabituelle)
  try{
    // 1. Résout le code final. En mode Inhabituelle, on crée (ou réutilise
    //    par dedup exact match backend) un LIB-xxx à partir du titre.
    let codeFinal = code;
    if(isCreationInhabituelle){
      // Si une suggestion catalogue a été cliquée → utilise ce code direct.
      if(MAINT_STATE.newLibreSelectedCode){
        codeFinal = MAINT_STATE.newLibreSelectedCode;
      } else {
        const rNew = await fetch('/api/maintenance/codes/libres', {
          method:'POST', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({label: titreLibre}),
        });
        if(!rNew.ok){ const err = await rNew.json().catch(()=>({})); throw new Error(err.detail || 'Création code libre échouée'); }
        const dNew = await rNew.json();
        codeFinal = dNew.code;
      }
    }
    // 2. POST /events → crée l'event non_planifie avec 1 op
    const body = {
      machine,
      date_prevue: dateVal,
      source: 'non_planifie',
      ops: [codeFinal],
      operators: [],  // Le serveur forcera l'user courant.
    };
    const r = await fetch('/api/maintenance/events', {
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    if(!r.ok){ const err = await r.json().catch(()=>({})); throw new Error(err.detail || r.status); }
    const data = await r.json();
    const ev = data.event;
    const op = (ev.ops || [])[0];
    if(!ev || !op){ throw new Error('Créneau incomplet retourné par l\'API.'); }
    // 3. PATCH op → statut termine + durée + observations + done_at (v2.2.9)
    await _patchOpTermine(ev.id, op.id, dureeMin, comment, _toDoneAtIso(dateVal));
    if(typeof showToast === 'function') showToast(isCreationInhabituelle ? 'Intervention libre enregistrée.' : 'Opération enregistrée.', 'success');
    opCloseNewModal();
    await opLoadTasks();
    if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
    else alert('Erreur : ' + e.message);
  }
}

// v2.2.13 : soumet la modal admin — boucle sur les machines cochées et crée
//   N events (source=non_planifie) marqués termine, un par machine.
async function adminSubmitRegisterOp(){
  const dateVal = document.getElementById('op-new-date').value;
  const machines = Array.from(document.querySelectorAll('#op-new-machines-chips .case-mach-chip.active'))
    .map(ch => ch.getAttribute('data-mach'));
  const titreLibre = (document.getElementById('op-new-titre-libre').value || '').trim();
  const code = document.getElementById('op-new-code').value;
  const dureeStr = document.getElementById('op-new-duree').value;
  const comment = (document.getElementById('op-new-comment').value || '').trim();
  const dureeMin = dureeStr === '' ? null : parseInt(dureeStr, 10);
  const isCreationInhabituelle = (MAINT_STATE.newModalMode === 'inhabituelle');

  // Validation
  if(!dateVal){ if(typeof showToast === 'function') showToast('Date obligatoire.', 'danger'); return; }
  if(machines.length === 0){ if(typeof showToast === 'function') showToast('Sélectionne au moins une machine.', 'danger'); return; }
  if(isCreationInhabituelle && !titreLibre){ if(typeof showToast === 'function') showToast('Titre obligatoire.', 'danger'); return; }
  if(!isCreationInhabituelle && !code){ if(typeof showToast === 'function') showToast('Code opération obligatoire.', 'danger'); return; }
  if(dureeStr !== '' && (Number.isNaN(dureeMin) || dureeMin < 0)){ if(typeof showToast === 'function') showToast('Durée invalide.', 'danger'); return; }

  try{
    // 1. Résout le code final (une seule fois — réutilisé pour toutes les machines).
    let codeFinal = code;
    if(isCreationInhabituelle){
      if(MAINT_STATE.newLibreSelectedCode){
        codeFinal = MAINT_STATE.newLibreSelectedCode;
      } else {
        const rNew = await fetch('/api/maintenance/codes/libres', {
          method:'POST', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({label: titreLibre}),
        });
        if(!rNew.ok){ const err = await rNew.json().catch(()=>({})); throw new Error(err.detail || 'Création code libre échouée'); }
        const dNew = await rNew.json();
        codeFinal = dNew.code;
      }
    }
    // 2. Boucle machines : POST /events + PATCH termine pour chacune
    let created = 0;
    for(const machine of machines){
      const body = { machine, date_prevue: dateVal, source: 'non_planifie', ops: [codeFinal], operators: [] };
      const r = await fetch('/api/maintenance/events', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      if(!r.ok){ const err = await r.json().catch(()=>({})); throw new Error(err.detail || r.status); }
      const data = await r.json();
      const ev = data.event;
      const op = (ev.ops || [])[0];
      if(!ev || !op){ throw new Error('Créneau incomplet retourné par l\'API.'); }
      // v2.7.2 : l'enregistrement est en deux temps — création du créneau, puis
      // solde de l'opération. Si le second échoue, le premier laissait derrière
      // lui un créneau « non planifié » jamais soldé, visible dans le planning
      // et absent de l'historique. Chaque nouvelle tentative en ajoutait un.
      // On annule donc la création avant de remonter l'erreur.
      try{
        await _patchOpTermine(ev.id, op.id, dureeMin, comment, _toDoneAtIso(dateVal));
      }catch(errPatch){
        try{
          await fetch('/api/maintenance/events/' + ev.id, {
            method:'DELETE', credentials:'include',
          });
        }catch(_){ /* nettoyage best-effort : l'erreur utile est celle du PATCH */ }
        throw errPatch;
      }
      created += 1;
    }
    const msg = created > 1
      ? `${created} opérations enregistrées (${machines.join(', ')}).`
      : (isCreationInhabituelle ? 'Intervention libre enregistrée.' : 'Opération enregistrée.');
    if(typeof showToast === 'function') showToast(msg, 'success');
    opCloseNewModal();
    if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
    if(typeof renderOps === 'function') renderOps();
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
    else alert('Erreur : ' + e.message);
  }
}

// ─── Intervention libre (v180) ────────────────────────────────────
// Modal minimaliste pour saisir une intervention ponctuelle sans creer
// de code du catalogue. Autocomplete sur les titres deja utilises pour
// encourager la reutilisation. Si l'user selectionne une suggestion, on
// reutilise le code existant ; sinon on cree un nouveau code libre LIB-xxx
// via POST /api/maintenance/codes/libres.
let _libreSelectedCode = null;
let _libreAutocompleteTimer = null;

function libreOpenModal(){
  _libreSelectedCode = null;
  const t = document.getElementById('libre-titre');
  const d = document.getElementById('libre-duree');
  const c = document.getElementById('libre-comment');
  const dateEl = document.getElementById('libre-date');
  if(t) t.value = '';
  if(d) d.value = '';
  if(c) c.value = '';
  // v182 Lot 2 : date pre-remplie a aujourd'hui, modifiable par l'operateur
  if(dateEl && typeof _fmtDateISO === 'function') dateEl.value = _fmtDateISO(new Date());
  const panel = document.getElementById('libre-autocomplete-panel');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
  // Pre-remplit machine avec la selection courante si disponible
  try{
    const m = (typeof getMaintMachine === 'function') ? getMaintMachine()
            : (typeof _getSelectedMachine === 'function') ? _getSelectedMachine()
            : 'Cohésio 1';
    const sel = document.getElementById('libre-machine');
    if(sel && m) sel.value = m;
  }catch(e){}
  document.getElementById('libre-modal').classList.add('active');
  setTimeout(() => { const el = document.getElementById('libre-titre'); if(el) el.focus(); }, 100);
}
function libreCloseModal(){
  const m = document.getElementById('libre-modal');
  if(m) m.classList.remove('active');
}
// v182ter : la duree est desormais toujours visible dans la modal.
// libreShowDuree conservee en no-op pour compat.
function libreShowDuree(){}

async function libreOnTitreInput(){
  const t = document.getElementById('libre-titre');
  const q = (t ? t.value : '').trim();
  _libreSelectedCode = null; // Reset quand l'user tape
  clearTimeout(_libreAutocompleteTimer);
  const panel = document.getElementById('libre-autocomplete-panel');
  if(q.length < 2){
    if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
    return;
  }
  _libreAutocompleteTimer = setTimeout(async () => {
    try{
      const r = await fetch('/api/maintenance/codes/libres/autocomplete?q=' + encodeURIComponent(q) + '&limit=8', {credentials:'include'});
      if(!r.ok) return;
      const d = await r.json();
      const items = d.items || [];
      if(!panel) return;
      if(!items.length){ panel.innerHTML = ''; panel.style.display = 'none'; return; }
      panel.innerHTML = items.map(it =>
        '<div class="libre-suggestion" data-libre-sug="' + escAttr(it.code) + '|' + escAttr(it.label) + '">' +
          '<span class="libre-suggestion-label">' + escHtml(it.label) + '</span>' +
          '<span class="libre-suggestion-count">' + it.usage_count + ' saisie' + (it.usage_count > 1 ? 's' : '') + '</span>' +
        '</div>'
      ).join('');
      panel.style.display = '';
      panel.querySelectorAll('[data-libre-sug]').forEach(el => {
        el.addEventListener('click', () => {
          const parts = (el.getAttribute('data-libre-sug') || '').split('|');
          if(parts.length >= 2) libreSelectSuggestion(parts[0], parts.slice(1).join('|'));
        });
      });
    }catch(e){}
  }, 220);
}

function libreSelectSuggestion(code, label){
  _libreSelectedCode = code;
  const t = document.getElementById('libre-titre');
  if(t) t.value = label;
  const panel = document.getElementById('libre-autocomplete-panel');
  if(panel){ panel.innerHTML = ''; panel.style.display = 'none'; }
}

let _libreSubmitInFlight = false;
async function libreSubmit(){
  // v182bis : anti-double-click. Un seul submit a la fois, sinon on cree
  // des LIB-xxx orphelins a chaque re-click pendant l'attente reseau.
  if(_libreSubmitInFlight) return;
  _libreSubmitInFlight = true;
  const submitBtn = document.querySelector('#libre-modal .op-btn-accent');
  if(submitBtn){
    submitBtn.disabled = true;
    submitBtn.style.opacity = '0.6';
    submitBtn.style.cursor = 'wait';
    submitBtn.textContent = 'Enregistrement...';
  }
  const _libreReset = () => {
    _libreSubmitInFlight = false;
    if(submitBtn){
      submitBtn.disabled = false;
      submitBtn.style.opacity = '';
      submitBtn.style.cursor = '';
      submitBtn.textContent = 'Enregistrer';
    }
  };
  const titre = (document.getElementById('libre-titre')?.value || '').trim();
  const machine = document.getElementById('libre-machine')?.value || '';
  const dateVal = (document.getElementById('libre-date')?.value || '').trim();
  const dureeStr = document.getElementById('libre-duree')?.value || '';
  const comment = (document.getElementById('libre-comment')?.value || '').trim();
  const dureeMin = dureeStr === '' ? null : parseInt(dureeStr, 10);
  if(!titre || !machine || !dateVal){
    if(typeof showToast === 'function') showToast('Date, titre et machine sont obligatoires.', 'danger');
    else alert('Date, titre et machine sont obligatoires.');
    _libreReset();
    return;
  }
  if(dureeStr !== '' && (Number.isNaN(dureeMin) || dureeMin < 0)){
    if(typeof showToast === 'function') showToast('Durée invalide.', 'danger');
    _libreReset();
    return;
  }
  try{
    let code = _libreSelectedCode;
    // Si aucune suggestion selectionnee, cree ou reutilise un code libre
    // (dedup exact-match cote backend depuis v182bis).
    if(!code){
      const rNew = await fetch('/api/maintenance/codes/libres', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({label: titre}),
      });
      if(!rNew.ok){ const err = await rNew.json().catch(()=>({})); throw new Error(err.detail || 'Creation code libre echouee'); }
      const dNew = await rNew.json();
      code = dNew.code;
    }
    // Cree l'event non_planifie + PATCH termine (meme flow que opSubmitNew).
    // v182 Lot 2 : date_prevue = dateVal saisie par l'operateur (defaut aujourd'hui).
    const rEv = await fetch('/api/maintenance/events', {
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        machine, date_prevue: dateVal, source: 'non_planifie',
        ops: [code], operators: [],
      }),
    });
    if(!rEv.ok){ const err = await rEv.json().catch(()=>({})); throw new Error(err.detail || rEv.status); }
    const dEv = await rEv.json();
    const ev = dEv.event;
    const op = (ev.ops || [])[0];
    if(!ev || !op) throw new Error('Creneau incomplet retourne par API.');
    if(typeof _patchOpTermine === 'function'){
      // v2.2.9 : passe la date saisie par l'admin pour override du done_at
      await _patchOpTermine(ev.id, op.id, dureeMin, comment, _toDoneAtIso(dateVal));
    }
    if(typeof showToast === 'function') showToast('Intervention libre enregistree.', 'success');
    libreCloseModal();
    // Refresh historique (force bypass cache pour voir la nouvelle entree)
    if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
    else if(typeof loadOps === 'function') loadOps();
    // Refresh tasks si operateur
    if(typeof opLoadTasks === 'function') opLoadTasks().catch(() => {});
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
    else alert('Erreur : ' + e.message);
  }finally{
    _libreReset();
  }
}

// ─── Lot 2c : renommer inline depuis l'historique ────────────────
async function libreRenameInline(code){
  const item = OPS_STATE.list.find(o => o._code === code && o._libre);
  const currentLabel = item ? item.type : '';
  const newLabel = prompt('Nouveau titre pour cette intervention libre :\nImpact retroactif sur toutes les saisies qui utilisent ce titre.', currentLabel || '');
  if(newLabel === null) return;
  const trimmed = (newLabel || '').trim();
  if(!trimmed){ if(typeof showToast === 'function') showToast('Titre obligatoire.', 'danger'); return; }
  if(trimmed === currentLabel) return;
  try{
    const r = await fetch('/api/maintenance/codes/libres/' + encodeURIComponent(code), {
      method:'PATCH', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({label: trimmed}),
    });
    if(!r.ok){ const err = await r.json().catch(()=>({})); throw new Error(err.detail || 'Renommage echoue'); }
    if(typeof showToast === 'function') showToast('Titre modifie.', 'success');
    if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
    else if(typeof loadOps === 'function') loadOps();
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
    else alert('Erreur : ' + e.message);
  }
}

// ─── Lot 2d : modal documents attaches a un code ─────────────────
function libreDocsOpen(code){
  let overlay = document.getElementById('libre-docs-overlay');
  if(overlay) overlay.remove();
  overlay = document.createElement('div');
  overlay.className = 'op-modal-overlay active';
  overlay.id = 'libre-docs-overlay';
  overlay.innerHTML = ''
    + '<div class="op-modal" role="dialog" aria-modal="true" style="max-width:560px">'
    +   '<div class="op-modal-title">Documents attaches</div>'
    +   '<div class="op-modal-sub">Code : ' + escHtml(code) + '. Fichiers explicatifs (photos avant/apres, schemas...). 20 Mo max par fichier.</div>'
    +   '<div id="libre-docs-list" style="display:flex;flex-direction:column;gap:8px;margin:14px 0;max-height:360px;overflow-y:auto">'
    +     '<p style="color:var(--muted);font-size:12px;text-align:center">Chargement...</p>'
    +   '</div>'
    +   '<input type="file" id="libre-docs-file" style="display:none">'
    +   '<div class="op-modal-actions">'
    +     '<button type="button" class="btn" onclick="libreDocsClose()">Fermer</button>'
    +     '<button type="button" class="btn op-btn-accent" id="libre-docs-add-btn">+ Ajouter un fichier</button>'
    +   '</div>'
    + '</div>';
  overlay.addEventListener('click', (e) => { if(e.target === overlay) libreDocsClose(); });
  document.body.appendChild(overlay);
  document.getElementById('libre-docs-add-btn').addEventListener('click', () => {
    document.getElementById('libre-docs-file').click();
  });
  document.getElementById('libre-docs-file').addEventListener('change', (e) => libreDocsUpload(code, e.target.files));
  libreDocsRefresh(code);
}
function libreDocsClose(){
  const el = document.getElementById('libre-docs-overlay');
  if(el) el.remove();
}
async function libreDocsRefresh(code){
  const list = document.getElementById('libre-docs-list');
  if(!list) return;
  try{
    const r = await fetch('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs', {credentials:'include'});
    if(!r.ok) throw new Error('Erreur ' + r.status);
    const d = await r.json();
    const items = Array.isArray(d.items) ? d.items : [];
    if(!items.length){
      list.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic;text-align:center">Aucun document attache pour l\u2019instant.</p>';
      return;
    }
    list.innerHTML = items.map(doc => {
      const sz = doc.size_bytes != null ? (Math.round(doc.size_bytes/1024) + ' Ko') : '';
      const dt = doc.uploaded_at ? escHtml(doc.uploaded_at.slice(0,16).replace('T',' ')) : '';
      return '<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card)">'
        +   '<div style="flex:1;min-width:0">'
        +     '<div style="font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escHtml(doc.filename) + '</div>'
        +     '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + sz + (dt ? ' - ' + dt : '') + '</div>'
        +   '</div>'
        +   '<a href="/api/maintenance/docs/' + doc.id + '/download" target="_blank" rel="noopener" class="btn btn-sec" style="padding:6px 12px;font-size:12px;text-decoration:none">Ouvrir</a>'
        +   '<button type="button" class="btn btn-sec" data-libre-doc-del="' + doc.id + '" style="padding:6px 12px;font-size:12px;color:var(--danger)">Supprimer</button>'
        + '</div>';
    }).join('');
    list.querySelectorAll('[data-libre-doc-del]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if(!confirm('Supprimer ce document ?')) return;
        const id = btn.getAttribute('data-libre-doc-del');
        try{
          const r = await fetch('/api/maintenance/docs/' + id, {method:'DELETE', credentials:'include'});
          if(!r.ok){ const err = await r.json().catch(()=>({})); throw new Error(err.detail || 'Suppression echouee'); }
          if(typeof showToast === 'function') showToast('Document supprime.', 'success');
          libreDocsRefresh(code);
        }catch(e){
          if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
        }
      });
    });
  }catch(e){
    list.innerHTML = '<p style="color:var(--danger);font-size:12px">Impossible de charger les documents.</p>';
  }
}
async function libreDocsUpload(code, files){
  if(!files || !files.length) return;
  const file = files[0];
  if(file.size > 20 * 1024 * 1024){
    if(typeof showToast === 'function') showToast('Fichier trop volumineux (max 20 Mo).', 'danger');
    return;
  }
  const btn = document.getElementById('libre-docs-add-btn');
  if(btn){ btn.disabled = true; btn.textContent = 'Envoi...'; }
  try{
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs', {
      method:'POST', credentials:'include', body: fd,
    });
    if(!r.ok){ const err = await r.json().catch(()=>({})); throw new Error(err.detail || 'Upload echoue'); }
    if(typeof showToast === 'function') showToast('Document ajoute.', 'success');
    document.getElementById('libre-docs-file').value = '';
    libreDocsRefresh(code);
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
  }finally{
    if(btn){ btn.disabled = false; btn.textContent = '+ Ajouter un fichier'; }
  }
}

async function opOpenNewTaskModal(){
  // v2 : fonctionnalité "Nouvelle tâche" retirée côté opérateur. La création
  // de tâches passe par "Enregistrer une opération" ou "Intervention libre".
  // Fonction gardée en no-op au cas où un onclick=... la référence encore.
  console.warn('[opOpenNewTaskModal] Fonctionnalité retirée. Utilise Enregistrer une opération ou Intervention libre.');
  if(typeof showToast === 'function'){
    showToast('La création de tâches se fait via "Enregistrer une opération" ou "Intervention libre".', 'info');
  }
}

// ── Modal single-op : marquer UNE op d'un créneau comme terminée ─────
MAINT_STATE.singleOpTarget = null;  // { eventId, opId }

function opOpenSingleOpModal(eventId, opId){
  const ev = (MAINT_STATE.tasks || []).find(x => x.id === eventId);
  if(!ev){ return; }
  const op = (ev.ops || []).find(o => o.id === opId);
  if(!op){ return; }
  MAINT_STATE.singleOpTarget = { eventId, opId, _wasDone: (op.statut === 'termine') };
  const timeLabel = (ev.heure_debut && ev.heure_fin)
    ? (ev.heure_debut + ' – ' + ev.heure_fin)
    : 'Sans créneau';
  document.getElementById('op-single-sub').textContent = 'Créneau ' + timeLabel + ' · ' + (ev.machine || '');
  document.getElementById('op-single-code-line').textContent = 'Code ' + op.code;
  document.getElementById('op-single-name').textContent = op.code_label || '—';
  // v185 : consignes admin affichées au-dessus des champs
  const consignesBlock = document.getElementById('op-single-consignes-block');
  if(consignesBlock){
    const c = (op.consignes || '').trim();
    if(c){
      consignesBlock.style.display = '';
      const panel = document.getElementById('op-single-consignes-text');
      if(panel) panel.textContent = c;
    } else {
      consignesBlock.style.display = 'none';
    }
  }
  document.getElementById('op-single-duree').value = op.duree_reelle_min || '';
  const prev = ((op.pieces_changees || '').trim() + '\n' + (op.observations || '').trim()).trim();
  document.getElementById('op-single-comment').value = prev;
  // Adapte le titre + submit + visibilité du bouton "Annuler la validation" selon statut
  const isDone = op.statut === 'termine';
  const titleEl = document.getElementById('op-single-title');
  const submitEl = document.getElementById('op-single-submit');
  const cancelValEl = document.getElementById('op-single-cancel-validation');
  if(titleEl) titleEl.textContent = isDone ? 'Opération terminée' : 'Marquer comme terminée';
  if(submitEl) submitEl.textContent = isDone ? 'Enregistrer les modifications' : 'Marquer comme terminée';
  // v2.2.75 : sur une op perso (non_planifie créée par l'user), le bouton
  // "Annuler la validation" fait doublon avec le bouton "Supprimer" qui est
  // plus intuitif — on le cache.
  const _meId = (S && S.me) ? S.me.id : null;
  const _isMinePerso = (ev.source === 'non_planifie') && (_meId != null) && (ev.created_by === _meId);
  if(cancelValEl) cancelValEl.style.display = (isDone && !_isMinePerso) ? '' : 'none';
  document.getElementById('op-modal-single').classList.add('active');
}

function opCloseSingleModal(){
  MAINT_STATE.singleOpTarget = null;
  document.getElementById('op-modal-single').classList.remove('active');
}

async function opSubmitSingleOp(){
  const tgt = MAINT_STATE.singleOpTarget;
  if(!tgt){ opCloseSingleModal(); return; }
  const dureeStr = (document.getElementById('op-single-duree').value || '').trim();
  const dureeMin = dureeStr === '' ? null : parseInt(dureeStr, 10);
  if(dureeStr !== '' && (Number.isNaN(dureeMin) || dureeMin < 0)){
    if(typeof showToast === 'function') showToast('Durée invalide.', 'danger');
    return;
  }
  const comment = (document.getElementById('op-single-comment').value || '').trim() || null;
  const body = { statut: 'termine', duree_reelle_min: dureeMin, observations: comment };
  const r = await fetch('/api/maintenance/events/' + tgt.eventId + '/ops/' + tgt.opId, {
    method:'PATCH', credentials:'include',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if(!r.ok){
    const err = await r.json().catch(()=>({}));
    if(typeof showToast === 'function') showToast('Erreur : ' + (err.detail || r.status), 'danger');
    else alert('Erreur : ' + (err.detail || r.status));
    return;
  }
  // Réponse : {event: updatedEv}. Update MAINT_STATE.tasks in-place AVANT
  // opLoadTasks — si opLoadTasks échoue, la vue reste cohérente.
  try{
    const data = await r.json();
    if(data && data.event){
      const idx = (MAINT_STATE.tasks || []).findIndex(x => x.id === data.event.id);
      if(idx >= 0) MAINT_STATE.tasks[idx] = data.event;
      opRenderTasks();
    }
  }catch(e){}
  if(typeof showToast === 'function') showToast('Opération terminée.', 'success');
  opCloseSingleModal();
  // Refresh en tâche de fond (best-effort) — si ça échoue, la vue est à jour.
  opLoadTasks().catch(() => {});
  if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
}

// ── Annule la saisie d'une op déjà terminée ────────────────────────
//   Statut termine -> a_faire. Efface done_at/by, durée, commentaires,
//   pièces changées. La ligne dans l'historique disparaît automatiquement
//   (get_history filtre sur statut='termine').
async function opCancelValidation(){
  const tgt = MAINT_STATE.singleOpTarget;
  if(!tgt){ opCloseSingleModal(); return; }
  if(!confirm("Annuler la validation de cette opération ?\n\nLa tâche reviendra dans la liste des tâches à faire et la ligne d'historique correspondante sera effacée. Cette action est définitive.")) return;
  const r = await fetch('/api/maintenance/events/' + tgt.eventId + '/ops/' + tgt.opId + '/reset', {
    method:'POST', credentials:'include',
  });
  if(!r.ok){
    const err = await r.json().catch(()=>({}));
    if(typeof showToast === 'function') showToast('Erreur : ' + (err.detail || r.status), 'danger');
    else alert('Erreur : ' + (err.detail || r.status));
    return;
  }
  try{
    const data = await r.json();
    if(data && data.event){
      const idx = (MAINT_STATE.tasks || []).findIndex(x => x.id === data.event.id);
      if(idx >= 0) MAINT_STATE.tasks[idx] = data.event;
      opRenderTasks();
    }
  }catch(e){}
  if(typeof showToast === 'function') showToast('Validation annulée. Tâche remise à faire.', 'info');
  opCloseSingleModal();
  opLoadTasks().catch(() => {});
  if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
}

async function opDeleteEvent(eventId){
  const ev = (MAINT_STATE.tasks || []).find(x => x.id === eventId);
  if(!ev){ return; }
  const meId = (S && S.me) ? S.me.id : null;
  if(ev.created_by !== meId){
    if(typeof showToast === 'function') showToast('Vous ne pouvez supprimer que vos propres interventions.', 'danger');
    return;
  }
  const label = ev.source === 'planifie'
    ? 'Supprimer ce créneau et toutes ses opérations ? Cette action est définitive.'
    : 'Supprimer cette opération ? Cette action est définitive.';
  if(!confirm(label)) return;
  const r = await fetch('/api/maintenance/events/' + eventId, {
    method:'DELETE', credentials:'include',
  });
  if(!r.ok){
    const err = await r.json().catch(()=>({}));
    if(typeof showToast === 'function') showToast('Erreur : ' + (err.detail || r.status), 'danger');
    else alert('Erreur : ' + (err.detail || r.status));
    return;
  }
  if(typeof showToast === 'function') showToast(ev.source === 'planifie' ? 'Créneau supprimé.' : 'Opération supprimée.', 'success');
  await opLoadTasks();
  if(typeof refreshOpsHistoryNow === 'function') refreshOpsHistoryNow();
}

/* ── Vue Planning opérateur (read-only) ──────────────────────────── */

function _opRenderPlanTable(events, meId){
  // v2.2.73 : regroupement par date puis par créneau. Aujourd'hui + 30 jours.
  // Les ops non-planifiées (source=non_planifie) sont exclues du Planning perso.
  const filtered = events.filter(ev => ev.source !== 'non_planifie');
  if(filtered.length === 0){
    return '<div class="op-empty"><h3>Aucun créneau programmé</h3>Pas d\'affectation aujourd\'hui ni dans les 30 prochains jours.</div>';
  }
  // Groupe par date (date_prevue)
  const byDate = new Map();
  for(const ev of filtered){
    const d = ev.date_prevue || '';
    if(!byDate.has(d)) byDate.set(d, []);
    byDate.get(d).push(ev);
  }
  // Tri des dates ascendant, puis dans chaque date par heure_debut
  const sortedDates = Array.from(byDate.keys()).sort();
  for(const d of sortedDates){
    byDate.get(d).sort((a, b) => {
      const ha = a.heure_debut || 'zz';
      const hb = b.heure_debut || 'zz';
      if(ha !== hb) return ha.localeCompare(hb);
      return (a.id || 0) - (b.id || 0);
    });
  }

  const todayIso = _fmtDateISO(new Date());
  const tomorrowD = new Date(); tomorrowD.setDate(tomorrowD.getDate() + 1);
  const tomorrowIso = _fmtDateISO(tomorrowD);
  const _dateLbl = (iso) => {
    const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if(!m) return iso;
    const d = new Date(parseInt(m[1],10), parseInt(m[2],10)-1, parseInt(m[3],10));
    const s = d.toLocaleDateString('fr-FR', {weekday:'long', day:'numeric', month:'long'});
    return s.charAt(0).toUpperCase() + s.slice(1);
  };
  const _daySectionHtml = (iso) => {
    let lbl;
    if(iso === todayIso) lbl = 'Aujourd\'hui · ' + _dateLbl(iso);
    else if(iso === tomorrowIso) lbl = 'Demain · ' + _dateLbl(iso);
    else lbl = _dateLbl(iso);
    return '<div class="op-plan-day-section-head"><span class="op-plan-day-dot"></span>' + escHtml(lbl) + '</div>';
  };

  const renderCreneauCard = (ev) => {
    // v2.2.71 : 1 ligne par op (pas par machine). Une op multi-machines
    // affiche la liste des machines séparées par ' · '.
    const rows = [];
    for(const op of (ev.ops || [])){
      let machines = Array.isArray(op.machines) && op.machines.length
        ? op.machines.slice()
        : (ev.machine ? [ev.machine] : ['—']);
      // Tri interne des machines de l'op selon _MACHINE_ORDER
      if(typeof _MACHINE_ORDER !== 'undefined'){
        const rank = new Map(_MACHINE_ORDER.map((mm, i) => [mm, i]));
        machines.sort((a, b) => {
          const ra = rank.has(a) ? rank.get(a) : Infinity;
          const rb = rank.has(b) ? rank.get(b) : Infinity;
          if(ra !== rb) return ra - rb;
          return String(a).localeCompare(String(b), 'fr');
        });
      }
      rows.push({ op, machines });
    }
    // Tri des ops par 1ère machine (rang canonique le plus bas)
    if(typeof _MACHINE_ORDER !== 'undefined'){
      const rank = new Map(_MACHINE_ORDER.map((mm, i) => [mm, i]));
      const minRank = (r) => Math.min.apply(null, r.machines.map(m => rank.has(m) ? rank.get(m) : Infinity));
      rows.sort((a, b) => {
        const ra = minRank(a), rb = minRank(b);
        if(ra !== rb) return ra - rb;
        return String(a.machines[0] || '').localeCompare(String(b.machines[0] || ''), 'fr');
      });
    }

    const timeLbl = (ev.heure_debut && ev.heure_fin) ? (ev.heure_debut + ' – ' + ev.heure_fin) : 'Sans horaire';
    const nom = (ev.nom || '').trim();
    const others = (ev.operators || []).filter(o => o.id !== meId).map(o => escHtml(o.nom));
    const teamLbl = others.length ? ('avec ' + others.join(', ')) : 'seul';
    const allDone = rows.length > 0 && rows.every(r => r.op.statut === 'termine' || r.op.statut === 'invalidee');  // v2.5.10
    const anyDone = rows.some(r => r.op.statut === 'termine');
    const statusCls = allDone ? 'done' : (anyDone ? 'progress' : '');
    const statusTxt = allDone
      ? '✓ Terminé'
      : (_calIsPastIso(ev.date_prevue || ev.date || '') ? 'Non réalisé'
                                                        : (anyDone ? 'En cours' : 'À faire'));

    const tbodyHtml = rows.map(r => `<tr>
      <td class="op-plan-cell-mac">${r.machines.map(m => escHtml(m)).join(' · ')}</td>
      <td><span class="op-code">${r.op.code}</span></td>
      <td class="op-plan-cell-lbl">${escHtml(r.op.code_label || '—')}</td>
      <td><span class="op-status op-status-${_opStatutView(r.op.statut, ev).cls}" style="position:static">${_opStatutView(r.op.statut, ev).label}</span></td>
    </tr>`).join('');

    return `<div class="op-plan-creneau-card" onclick="opOpenPlanDetail(${ev.id})" role="button" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();opOpenPlanDetail(${ev.id});}">
      <div class="op-plan-creneau-header">
        <span class="op-plan-ch-chev">▸</span>
        <span class="op-plan-ch-time">${escHtml(timeLbl)}</span>
        ${nom ? '<span class="op-plan-ch-nom">' + escHtml(nom) + '</span>' : ''}
        <span class="op-plan-ch-count">${rows.length} op.</span>
        <span class="op-plan-ch-status ${statusCls}">${statusTxt}</span>
        <span class="op-plan-ch-team">${teamLbl}</span>
      </div>
      <table class="op-plan-creneau-table">
        <thead><tr><th>Machine</th><th>Code</th><th>Opération</th><th>Statut</th></tr></thead>
        <tbody>${tbodyHtml}</tbody>
      </table>
    </div>`;
  };  // renderCreneauCard

  // Assemble : pour chaque date, une section-head + les cartes créneau
  const sectionsHtml = sortedDates.map(iso => {
    const cardsForDate = byDate.get(iso).map(renderCreneauCard).join('');
    return _daySectionHtml(iso) + '<div class="op-plan-creneaux-list">' + cardsForDate + '</div>';
  }).join('');
  return '<div class="op-plan-days-wrap">' + sectionsHtml + '</div>';
}

// v2.2.68 : modal détail créneau lecture seule (Planning personnel)
async function opOpenPlanDetail(eventId){
  try {
    const r = await fetch('/api/maintenance/events/' + eventId + '?_=' + Date.now(),
                          { credentials:'include', cache:'no-store' });
    if(!r.ok) throw new Error('Erreur ' + r.status);
    const d = await r.json();
    const ev = d.event || d;
    _opRenderPlanDetailModal(ev);
  } catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
  }
}

function _opRenderPlanDetailModal(ev){
  const ov = document.createElement('div');
  ov.className = 'op-plan-detail-ov';
  ov.addEventListener('click', e => { if(e.target === ov) ov.remove(); });
  const _dt = new Date(ev.date_prevue + 'T00:00:00');
  const _dLbl = _dt.toLocaleDateString('fr-FR', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
  const _hLbl = (ev.heure_debut && ev.heure_fin) ? (ev.heure_debut + ' – ' + ev.heure_fin) : 'Sans horaire';

  // v2.2.71 : 1 ligne par op (regroupe multi-machines), pas de code affiché.
  const opsFlat = [];
  for(const op of (ev.ops || [])){
    let machines = Array.isArray(op.machines) && op.machines.length
      ? op.machines.slice()
      : (ev.machine ? [ev.machine] : ['—']);
    if(typeof _MACHINE_ORDER !== 'undefined'){
      const rk = new Map(_MACHINE_ORDER.map((mm, i) => [mm, i]));
      machines.sort((a, b) => {
        const ra = rk.has(a) ? rk.get(a) : Infinity;
        const rb = rk.has(b) ? rk.get(b) : Infinity;
        if(ra !== rb) return ra - rb;
        return String(a).localeCompare(String(b), 'fr');
      });
    }
    opsFlat.push({ op, machines });
  }
  // Tri des ops par 1ère machine (rang canonique)
  if(typeof _MACHINE_ORDER !== 'undefined'){
    const rank = new Map(_MACHINE_ORDER.map((mm, i) => [mm, i]));
    const minRank = (r) => Math.min.apply(null, r.machines.map(m => rank.has(m) ? rank.get(m) : Infinity));
    opsFlat.sort((a, b) => {
      const ra = minRank(a), rb = minRank(b);
      if(ra !== rb) return ra - rb;
      return String(a.machines[0] || '').localeCompare(String(b.machines[0] || ''), 'fr');
    });
  }
  const opsHtml = opsFlat.map(({op, machines}) => {
    const isDone = op.statut === 'termine';
    return `<div class="op-plan-detail-op-row ${isDone ? 'is-done' : ''}">
      <div style="flex:1;min-width:0">
        <div class="op-plan-detail-op-lbl">${escHtml(op.code_label || '—')}</div>
        <div class="op-plan-detail-op-mac">${machines.map(m => escHtml(m)).join(' · ')}</div>
      </div>
      <span class="op-plan-detail-op-badge ${isDone ? 'done' : 'todo'}">${isDone ? '✓ Terminé' : 'À faire'}</span>
    </div>`;
  }).join('');
  const opsBlock = opsFlat.length
    ? opsHtml
    : '<div style="padding:10px;color:var(--muted);font-style:italic;font-size:12px">Aucune opération dans ce créneau.</div>';

  const operatorsList = (ev.operators || []).map(o => escHtml(o.nom || '?')).join(' · ') || '<em>Aucun</em>';
  const nomBlock = (ev.nom || '').trim() ? '<div class="op-plan-detail-info"><div class="op-plan-detail-info-lbl">Nom du créneau</div><div class="op-plan-detail-info-val">' + escHtml(ev.nom) + '</div></div>' : '';

  ov.innerHTML =
    '<div class="op-plan-detail-box">' +
      '<button type="button" class="op-plan-detail-close" onclick="this.closest(\'.op-plan-detail-ov\').remove()" aria-label="Fermer">' +
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
      '</button>' +
      '<div class="op-plan-detail-title">' +
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>' +
        'Créneau de maintenance' +
      '</div>' +
      '<div class="op-plan-detail-sub">' + escHtml(_dLbl) + ' · ' + escHtml(_hLbl) + '</div>' +
      nomBlock +
      '<div class="op-plan-detail-info"><div class="op-plan-detail-info-lbl">Machine(s)</div><div class="op-plan-detail-info-val">' + escHtml(ev.machine || '—') + '</div></div>' +
      '<div class="op-plan-detail-info"><div class="op-plan-detail-info-lbl">Opérateurs assignés</div><div class="op-plan-detail-info-val">' + operatorsList + '</div></div>' +
      '<div class="op-plan-detail-ops-lbl">Opérations (' + opsFlat.length + ')</div>' +
      opsBlock +
      '<div class="op-plan-detail-actions">' +
        '<button type="button" class="btn-close" onclick="this.closest(\'.op-plan-detail-ov\').remove()">Fermer</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(ov);
}

async function opLoadPlanning(){
  if(MAINT_ROLE !== 'operator') return;
  // v2.2.73 : fetch aujourd'hui + 30 jours à venir. Le date picker est
  // conservé pour l'onglet Planning général mais ignoré pour le Personnel
  // qui affiche systématiquement aujourd'hui → J+30 groupé par date.
  const today = _fmtDateISO(new Date());
  const _todayD = new Date();
  const _endD = new Date(_todayD); _endD.setDate(_endD.getDate() + 30);
  const _endIso = _fmtDateISO(_endD);
  const dateInput = document.getElementById('op-plan-date');
  if(dateInput && !dateInput.value) dateInput.value = today;
  const r = await fetch('/api/maintenance/events?date_from=' + encodeURIComponent(today) +
                       '&date_to=' + encodeURIComponent(_endIso) + '&_=' + Date.now(),
                       { credentials:'include', cache: 'no-store' });
  if(!r.ok){
    const persoEl = document.getElementById('op-plan-personnel');
    if(persoEl) persoEl.innerHTML = _opRenderPlanTable([], null);
    return;
  }
  const data = await r.json();
  const events = data.events || [];
  const meId = (S && S.me) ? S.me.id : null;
  const perso = events.filter(ev => (ev.operators || []).some(o => o.id === meId));
  const persoEl = document.getElementById('op-plan-personnel');
  if(persoEl) persoEl.innerHTML = _opRenderPlanTable(perso, meId);
}

function opSetPlanTab(name){
  document.querySelectorAll('[data-op-plan-tab]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-op-plan-tab') === name);
  });
  const perso = document.getElementById('op-plan-personnel');
  const gen = document.getElementById('op-plan-general');
  if(perso) perso.style.display = (name === 'personnel') ? '' : 'none';
  if(gen) gen.style.display = (name === 'general') ? '' : 'none';
}


/* ── Templates de session (v163) ─────────────────────────────────── */

const TEMPLATES_STATE = { list: null };  // null = pas encore chargé

async function loadTemplates(force){
  if(!force && TEMPLATES_STATE.list !== null) return TEMPLATES_STATE.list;
  if(MAINT_ROLE !== 'admin'){ TEMPLATES_STATE.list = []; _maybeRenderTmplPanel(); return []; }
  try{
    const r = await fetch('/api/maintenance/templates?_=' + Date.now(),
                          { credentials:'include', cache: 'no-store' });
    if(!r.ok){ TEMPLATES_STATE.list = []; _maybeRenderTmplPanel(); return []; }
    const d = await r.json();
    TEMPLATES_STATE.list = d.templates || [];
  }catch(e){ TEMPLATES_STATE.list = []; }
  _maybeRenderTmplPanel();
  return TEMPLATES_STATE.list;
}
// v2.4.31 : appelle renderTemplateManagePanel si dispo (safe si div absent).
function _maybeRenderTmplPanel(){
  try{ if(typeof renderTemplateManagePanel === 'function') renderTemplateManagePanel(); }catch(e){}
}

// v2.5.31 : les occurrences supprimees vivent desormais dans la modale
// d'edition du modele concerne (section pliable en bas), et non plus dans un
// panel dedie de l'onglet Historique -- c'est un cas minoritaire par nature.
// L'endpoint est filtre par template_id.
const TMPL_DELETED_STATE = { templateId: null, list: [] };

async function loadTmplDeletedOccurrences(templateId){
  TMPL_DELETED_STATE.templateId = templateId || null;
  TMPL_DELETED_STATE.list = [];
  if(MAINT_ROLE !== 'admin' || !templateId){ renderTmplDeletedOccurrences(); return; }
  try{
    const r = await fetch('/api/maintenance/events/deleted?template_id=' +
                          encodeURIComponent(templateId) + '&_=' + Date.now(),
                          { credentials:'include', cache: 'no-store' });
    if(r.ok){
      const d = await r.json();
      TMPL_DELETED_STATE.list = d.events || [];
    }
  }catch(_){ /* liste vide -- la section reste masquee */ }
  renderTmplDeletedOccurrences();
}

function renderTmplDeletedOccurrences(){
  const block = document.getElementById('tmpl-ed-deleted-block');
  const list  = document.getElementById('tmpl-ed-deleted-list');
  const cntEl = document.getElementById('tmpl-ed-deleted-count');
  if(!block || !list) return;
  const items = TMPL_DELETED_STATE.list || [];
  if(!items.length){
    // Aucun tombstone : la section disparait completement du modal.
    block.style.display = 'none';
    block.classList.remove('open');
    const head = document.getElementById('tmpl-ed-deleted-toggle');
    if(head) head.setAttribute('aria-expanded', 'false');
    list.innerHTML = '';
    return;
  }
  block.style.display = '';
  if(cntEl) cntEl.textContent = String(items.length);
  list.innerHTML = items.map(ev => {
    const dateFR  = _fmtIsoDateFr(ev.date_prevue) || ev.date_prevue || '\u2014';
    const hours   = (ev.heure_debut || '') + (ev.heure_fin ? ' \u2013 ' + ev.heure_fin : '');
    const machine = ev.machine || '\u2014';
    const ops     = (ev.operators || []).map(o => o.nom).join(', ');
    const delDay  = ev.deleted_at ? String(ev.deleted_at).slice(0,10) : '';
    const delTxt  = delDay ? ('supprim\u00e9e le ' + (_fmtIsoDateFr(delDay) || delDay)) : '';
    const meta    = [machine, ops || 'aucun op\u00e9rateur', delTxt].filter(Boolean).join(' \u00b7 ');
    const nDone   = (ev.ops || []).filter(o => o.statut === 'termine').length;
    const warn    = nDone
      ? '<div class="tmpl-del-row-warn">' + nDone + ' op\u00e9ration' + (nDone > 1 ? 's' : '') +
        ' d\u00e9j\u00e0 valid\u00e9e' + (nDone > 1 ? 's' : '') + ' \u2014 conserv\u00e9e' +
        (nDone > 1 ? 's' : '') + ' \u00e0 la restauration</div>'
      : '';
    return '<div class="tmpl-del-row">' +
      '<div class="tmpl-del-row-main">' +
        '<div class="tmpl-del-row-when">' + escHtml(dateFR) + (hours ? ' \u00b7 ' + escHtml(hours) : '') + '</div>' +
        '<div class="tmpl-del-row-meta">' + escHtml(meta) + '</div>' + warn +
      '</div>' +
      '<button type="button" class="tmpl-del-restore" onclick="restoreEvent(' + ev.id + ')">Restaurer</button>' +
    '</div>';
  }).join('');
}

function toggleTmplDeleted(){
  const block = document.getElementById('tmpl-ed-deleted-block');
  if(!block) return;
  const isOpen = block.classList.toggle('open');
  const head = document.getElementById('tmpl-ed-deleted-toggle');
  if(head) head.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

async function restoreEvent(eventId){
  try{
    const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/restore',
                          { method: 'POST', credentials: 'include' });
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      throw new Error(err.detail || 'Restauration refus\u00e9e');
    }
    if(typeof showToast === 'function') showToast('Cr\u00e9neau restaur\u00e9.', 'info');
    const wasOpen = document.getElementById('tmpl-ed-deleted-block')?.classList.contains('open');
    await loadTmplDeletedOccurrences(TMPL_DELETED_STATE.templateId);
    // Garde la section ouverte s'il reste des occurrences a restaurer.
    if(wasOpen && (TMPL_DELETED_STATE.list || []).length){
      document.getElementById('tmpl-ed-deleted-block')?.classList.add('open');
    }
    // Rafraichit le badge « N supprimee(s) » du panel Gestion des modeles.
    try{ await loadTemplates(true); }catch(_){}
    if(typeof refreshPlanning === 'function') await refreshPlanning();
    if(typeof renderCal === 'function') renderCal();
  }catch(e){
    if(typeof showToast === 'function') showToast('Erreur : ' + e.message, 'danger');
  }
}

function refreshCaseTemplatePicker(){
  const sel = document.getElementById('case-mod-template');
  if(!sel) return;
  const list = TEMPLATES_STATE.list || [];
  // v2.6.1 : le select est une ACTION d'import, plus un etat « modele du
  // creneau ». Il revient donc toujours sur son option neutre, et aucun
  // modele n'y est pre-selectionne — on peut en importer plusieurs de suite.
  sel.innerHTML = '<option value="">+ Importer un modèle…</option>' +
    list.map(t =>
      '<option value="' + escAttr(t.id) + '">' +
        escHtml(t.name) + ' (' + t.ops_count + ' op.)' +
      '</option>'
    ).join('');
  sel.value = '';
}

// v2.6.1 : modeles CUMULABLES sur un meme creneau.
// _CASE_TMPL_USED memorise les modeles importes dans la modale en cours :
//   - pour afficher le rappel sous la liste d'operations ;
//   - pour decider de l'etiquette template_id du creneau (cf. plus bas).
let _CASE_TMPL_USED = [];   // [{id, name}]

function _resetCaseTemplates(){ _CASE_TMPL_USED = []; renderCaseTemplatesApplied(); }

function renderCaseTemplatesApplied(){
  const box = document.getElementById('case-tmpl-applied');
  if(!box) return;
  if(!_CASE_TMPL_USED.length){ box.style.display = 'none'; box.innerHTML = ''; return; }
  box.style.display = '';
  box.innerHTML = 'Modèle(s) importé(s) : ' + _CASE_TMPL_USED.map(t =>
    '<span class="case-tmpl-chip">' + escHtml(t.name) + '</span>').join(' ');
}

// Fusionne les ops d'un modele dans _CASE_OPS.
//   - meme code deja present  -> UNION des machines (aucune n'est perdue)
//                              + consignes concatenees si elles different
//   - code absent             -> ajout en fin de liste
// Retourne {ajoutees, fusionnees} pour le message de confirmation.
function _mergeTemplateOps(tmplOps){
  let ajoutees = 0, fusionnees = 0;
  for(const o of (tmplOps || [])){
    const code = o.code;
    if(!code) continue;
    const machines = Array.isArray(o.machines) ? o.machines.slice() : [];
    const consignes = (o.consignes || '').trim();
    const existing = _CASE_OPS.find(c => c.opTypeId === code);
    if(existing){
      // Union des machines : c'est le point qui manquait. La dedup serveur
      // gardait les machines de la PREMIERE occurrence, donc importer deux
      // modeles portant la meme operation sur des machines differentes en
      // perdait une silencieusement.
      for(const m of machines){
        if(existing.machines.indexOf(m) === -1) existing.machines.push(m);
      }
      const cur = (existing.consignes || '').trim();
      if(consignes && cur.indexOf(consignes) === -1){
        existing.consignes = cur ? (cur + '\n' + consignes) : consignes;
      }
      fusionnees++;
    } else {
      _CASE_OPS.push({
        _op_id: null,
        opTypeId: code,
        opName: o.code_label || code,
        opNiveau: null,
        opFreq: '',
        machines: machines,
        consignes: consignes,
      });
      ajoutees++;
    }
  }
  // Réinjecte les infos riches depuis OPS_TYPES_STATE (nom, niveau, frequence).
  for(const co of _CASE_OPS){
    const t = OPS_TYPES_STATE.list.find(x => x.id === co.opTypeId);
    if(t){ co.opName = t.nom; co.opNiveau = t.niveau || null; co.opFreq = t.frequence || ''; }
  }
  return { ajoutees, fusionnees };
}

// v2.6.1 : reporte les horaires saisis dans le bandeau date du haut de modale.
function _syncCaseTimeRecap(){
  const el = document.getElementById('case-mod-time-recap');
  if(!el) return;
  const s = (document.getElementById('case-mod-start') || {}).value || '';
  const e = (document.getElementById('case-mod-end')   || {}).value || '';
  el.textContent = (s && e) ? (s + ' \u2013 ' + e) : (s || e || '—');
}

async function applyCaseTemplate(templateId){
  if(!templateId) return;   // option « + Importer un modele… » : aucune action
  try{
    const r = await fetch('/api/maintenance/templates/' + encodeURIComponent(templateId) +
                          '?_=' + Date.now(), { credentials:'include', cache: 'no-store' });
    if(!r.ok){ showToast('Modèle introuvable.', 'danger'); return; }
    const d = await r.json();
    const tmpl = d.template;
    if(!tmpl){ showToast('Modèle vide.', 'danger'); return; }
    if(_CASE_TMPL_USED.some(t => String(t.id) === String(tmpl.id))){
      showToast('Modèle « ' + tmpl.name + ' » déjà importé.', 'info');
      return;
    }
    const res = _mergeTemplateOps(tmpl.ops || []);
    _CASE_TMPL_USED.push({ id: tmpl.id, name: tmpl.name });
    // v2.6.1 : l'import NE CREE AUCUN LIEN avec le modele. C'est un simple
    // raccourci de saisie : il recopie des operations dans le formulaire, rien
    // de plus. Le creneau produit est autonome.
    //
    // Avant, un import unique laissait template_id sur le creneau, ce qui le
    // rendait solidaire du modele : modifier le modele ecrasait ses operations,
    // desactiver sa recurrence ou le supprimer effacait purement le creneau —
    // alors qu'il avait ete compose a la main. Le comportement dependait en
    // plus du NOMBRE de modeles importes, l'etiquette tombant des le second.
    // On ne pose donc plus rien : seules les occurrences generees par la
    // recurrence portent un lien (template_id + template_origin_date), et
    // elles sont creees cote serveur, jamais par ce chemin.
    renderCaseOpsList();
    renderCaseTemplatesApplied();
    let msg = 'Modèle « ' + tmpl.name + ' » importé';
    if(res.ajoutees && res.fusionnees)      msg += ' : ' + res.ajoutees + ' op. ajoutée(s), ' + res.fusionnees + ' fusionnée(s)';
    else if(res.ajoutees)                   msg += ' : ' + res.ajoutees + ' op. ajoutée(s)';
    else if(res.fusionnees)                 msg += ' : ' + res.fusionnees + ' op. déjà présente(s), machines fusionnées';
    showToast(msg + '.', 'info');
  }catch(e){ showToast('Erreur : ' + e.message, 'danger'); }
}

/* ── Modal « Gérer les modèles » ──────────────────────────────────── */

async function openTemplatesModal(){
  await loadTemplates(true);
  const m = document.getElementById('templates-modal');
  if(!m) return;
  renderTemplatesList();
  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeTemplatesModal(){
  const m = document.getElementById('templates-modal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden', 'true'); }
  document.body.style.overflow = '';
}

function renderTemplatesList(){
  const list = document.getElementById('tmpl-list');
  if(!list) return;
  const items = TEMPLATES_STATE.list || [];
  if(!items.length){
    list.innerHTML = '<div class="tmpl-empty">Aucun modèle pour l\'instant.<br>Clique sur « Nouveau modèle » pour en créer un.</div>';
    return;
  }
  list.innerHTML = items.map(t => `
    <div class="tmpl-item" data-tmpl-id="${escAttr(t.id)}">
      <div class="tmpl-item-main">
        <div class="tmpl-item-name">${escHtml(t.name)}</div>
        <div class="tmpl-item-desc">${escHtml(t.description || '—')}</div>
      </div>
      <div class="tmpl-item-count">${t.ops_count} op.</div>
      <div class="tmpl-item-actions">
        <button type="button" class="tmpl-item-btn edit" onclick="openTemplateEditor(${escAttr(t.id)})" title="Modifier" aria-label="Modifier">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button type="button" class="tmpl-item-btn del" onclick="confirmDeleteTemplate(${escAttr(t.id)})" title="Supprimer" aria-label="Supprimer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
        </button>
      </div>
    </div>`).join('');
}

// v2.4.32 : suppression modele -- modal stylise MySifa (remplace le confirm() natif).
async function confirmDeleteTemplate(templateId){
  const t = (TEMPLATES_STATE.list || []).find(x => x.id === templateId);
  if(!t) return;
  _openDeleteTemplateModal(t);
}

// v2.6.1 : confirmation au style MySifa, en remplacement de window.confirm().
// Rend une Promise<boolean> pour rester utilisable en await dans un flux async.
// Mise en forme alignee sur _openDeleteTemplateModal (overlay .op-modal-overlay
// + carte .op-modal), fermeture par Echap, clic hors carte ou bouton Annuler.
// v2.6.1 : ids coches dans la derniere confirmation (cases [data-keep]).
let _MYS_CONFIRM_LAST_KEEP = [];
function _mysConfirm(opts){
  opts = opts || {};
  return new Promise(function(resolve){
    const prev = document.getElementById('mys-confirm-overlay');
    if(prev) prev.remove();
    const wrap = document.createElement('div');
    wrap.id = 'mys-confirm-overlay';
    wrap.className = 'op-modal-overlay';
    wrap.style.cssText = 'display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:10000;align-items:center;justify-content:center';
    let done = false;
    function close(val){
      if(done) return;
      done = true;
      // v2.6.1 : les cases [data-keep] du corps sont lues AVANT le retrait du
      // DOM — apres, querySelectorAll ne trouverait plus rien. Le resultat est
      // expose via _MYS_CONFIRM_LAST_KEEP pour l'appelant.
      try{
        _MYS_CONFIRM_LAST_KEEP = Array.prototype.slice
          .call(wrap.querySelectorAll('[data-keep]'))
          .filter(function(cb){ return cb.checked; })
          .map(function(cb){ return parseInt(cb.getAttribute('data-keep'), 10); })
          .filter(function(v){ return !isNaN(v); });
      }catch(_){ _MYS_CONFIRM_LAST_KEEP = []; }
      document.removeEventListener('keydown', esc, true);
      try{ wrap.remove(); }catch(_){}
      resolve(val);
    }
    function esc(e){ if(e.key === 'Escape'){ e.preventDefault(); close(false); } }
    document.addEventListener('keydown', esc, true);
    wrap.addEventListener('click', function(e){ if(e.target === wrap) close(false); });

    const accent = opts.danger ? 'var(--danger)' : 'var(--warn,#f59e0b)';
    wrap.innerHTML = ''
      + '<div class="op-modal" role="dialog" aria-modal="true" style="max-width:520px;width:calc(100% - 40px);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,0.4)">'
      +   '<div style="color:' + accent + ';font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px">'
      +     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86l-8.18 14.16A2 2 0 0 0 3.83 21h16.34a2 2 0 0 0 1.72-2.98L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>'
      +     escHtml(opts.title || 'Confirmer ?')
      +   '</div>'
      +   (opts.highlightHtml
          ? '<div style="padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:14px">' + opts.highlightHtml + '</div>'
          : '')
      +   '<div style="font-size:13px;color:var(--text);line-height:1.55;margin-bottom:16px">' + (opts.bodyHtml || '') + '</div>'
      +   '<div style="display:flex;justify-content:flex-end;gap:10px">'
      +     '<button type="button" data-mys-cancel class="modal-btn-ghost">' + escHtml(opts.cancelLabel || 'Annuler') + '</button>'
      +     '<button type="button" data-mys-ok style="background:' + accent + ';color:#fff;border:none;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">' + escHtml(opts.okLabel || 'Continuer') + '</button>'
      +   '</div>'
      + '</div>';
    wrap.querySelector('[data-mys-cancel]').addEventListener('click', function(){ close(false); });
    wrap.querySelector('[data-mys-ok]').addEventListener('click', function(){ close(true); });
    document.body.appendChild(wrap);
    requestAnimationFrame(function(){ wrap.querySelector('[data-mys-cancel]').focus(); });
  });
}

function _openDeleteTemplateModal(t){
  const existing = document.getElementById('del-tmpl-modal-overlay');
  if(existing) existing.remove();
  const wrap = document.createElement('div');
  wrap.id = 'del-tmpl-modal-overlay';
  wrap.className = 'op-modal-overlay';
  wrap.style.cssText = 'display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center';
  wrap.addEventListener('click', (e) => { if(e.target === wrap) _closeDeleteTemplateModal(); });
  const escHandler = (e) => { if(e.key === 'Escape'){ e.preventDefault(); _closeDeleteTemplateModal(); } };
  document.addEventListener('keydown', escHandler, true);
  wrap._escHandler = escHandler;

  const opsCount = (t.ops_count != null ? t.ops_count : (t.ops ? t.ops.length : 0)) || 0;
  const evCount  = t.events_count || 0;
  const recurLine = t.recurrence_active
    ? '<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--warn);margin-top:6px"><span>\u26a0\ufe0f</span><span>Recurrence active -- les prochaines occurrences ne se genereront plus.</span></div>'
    : '';

  wrap.innerHTML = ''
    + '<div class="op-modal" role="dialog" aria-modal="true" style="max-width:520px;width:calc(100% - 40px);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,0.4)">'
    +   '<div style="color:var(--danger);font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px">'
    +     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>'
    +     'Supprimer le modele ?'
    +   '</div>'
    +   '<div style="padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:14px">'
    +     '<div style="font-size:14px;font-weight:700;color:var(--text)">' + escHtml(t.name) + '</div>'
    +     (t.description ? '<div style="font-size:12px;color:var(--muted);margin-top:4px">' + escHtml(t.description) + '</div>' : '')
    +     '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:11px">'
    +       '<span style="padding:3px 9px;border-radius:6px;background:var(--card);color:var(--text2);font-weight:600">' + opsCount + ' op.</span>'
    +       '<span style="padding:3px 9px;border-radius:6px;background:var(--card);color:var(--text2);font-weight:600">' + evCount + ' creneau' + (evCount > 1 ? 'x' : '') + ' cree' + (evCount > 1 ? 's' : '') + '</span>'
    +     '</div>'
    +     recurLine
    +   '</div>'
    +   '<div style="font-size:13px;color:var(--text);line-height:1.5;margin-bottom:16px">'
    +     'Cela supprime aussi <strong>tous les creneaux futurs</strong> (a partir d\'aujourd\'hui) crees depuis ce modele. Les creneaux passes seront conserves (mais detaches du modele).'
    +   '</div>'
    +   '<div style="display:flex;justify-content:flex-end;gap:10px">'
    +     '<button type="button" id="del-tmpl-cancel-btn" class="btn" style="background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>'
    +     '<button type="button" id="del-tmpl-confirm-btn" class="btn btn-danger" style="background:var(--danger);color:#fff;border:none;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">Supprimer</button>'
    +   '</div>'
    + '</div>';

  document.body.appendChild(wrap);
  const cancelBtn  = document.getElementById('del-tmpl-cancel-btn');
  const confirmBtn = document.getElementById('del-tmpl-confirm-btn');
  if(cancelBtn)  cancelBtn.addEventListener('click', _closeDeleteTemplateModal);
  if(confirmBtn) confirmBtn.addEventListener('click', () => {
    if(confirmBtn.dataset._busy === '1') return;
    confirmBtn.dataset._busy = '1';
    confirmBtn.disabled = true;
    _doDeleteTemplate(t.id, confirmBtn);
  });
  requestAnimationFrame(() => { if(cancelBtn) cancelBtn.focus(); });
}

function _closeDeleteTemplateModal(){
  const w = document.getElementById('del-tmpl-modal-overlay');
  if(!w) return;
  try{ if(w._escHandler) document.removeEventListener('keydown', w._escHandler, true); }catch(_){}
  w.remove();
}

async function _doDeleteTemplate(templateId, btn){
  try{
    const r = await fetch('/api/maintenance/templates/' + encodeURIComponent(templateId),
                          { method:'DELETE', credentials:'include' });
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      throw new Error(err.detail || 'Suppression refusee');
    }
    const d = await r.json();
    const n = d.deleted_future_events || 0;
    showToast('Modele supprime' + (n ? ' -- ' + n + ' creneau' + (n > 1 ? 'x' : '') + ' futur' + (n > 1 ? 's' : '') + ' nettoye' + (n > 1 ? 's' : '') + '.' : '.'), 'info');
    _closeDeleteTemplateModal();
    await loadTemplates(true);
    renderTemplatesList();
    refreshCaseTemplatePicker();
    await refreshPlanning(); renderCal();
  }catch(e){
    showToast('Erreur : ' + e.message, 'danger');
    if(btn){ btn.dataset._busy = ''; btn.disabled = false; }
  }
}

/* ── v2.4.29 : Helpers récurrence + panel Gestion des modèles ────── */

function onTmplRecurToggle(el){
  const wrap = document.getElementById('tmpl-ed-recur-fields');
  if(wrap) wrap.classList.toggle('open', !!el.checked);
  _syncTmplDefaultOpsVisibility(!!el.checked);
}

// v2.6.0 : la section « Operateurs par defaut » suit l'interrupteur de
// recurrence. On masque seulement l'affichage : _TMPL_DEFAULT_OPS et la valeur
// en base sont conservees, donc rallumer la recurrence retrouve la liste
// telle quelle sans ressaisie.
function _syncTmplDefaultOpsVisibility(active){
  const sec = document.getElementById('tmpl-ed-default-op-section');
  if(sec) sec.style.display = active ? '' : 'none';
}

function onTmplRecurTypeChange(){
  const type = document.getElementById('tmpl-ed-recur-type')?.value || 'weekly';
  document.getElementById('tmpl-ed-recur-dow-wrap').style.display   = (type === 'weekly') ? '' : 'none';
  document.getElementById('tmpl-ed-recur-dom-wrap').style.display   = (type === 'weekly') ? 'none' : '';
  document.getElementById('tmpl-ed-recur-month-wrap').style.display = (type === 'yearly') ? '' : 'none';
}

function _setRecurInForm(t){
  const cb = document.getElementById('tmpl-ed-recur-active');
  if(cb) cb.checked = !!t.recurrence_active;
  const wrap = document.getElementById('tmpl-ed-recur-fields');
  if(wrap) wrap.classList.toggle('open', !!t.recurrence_active);
  // v2.6.0 : idem a l'ouverture du modal (creation ou edition).
  _syncTmplDefaultOpsVisibility(!!t.recurrence_active);
  const typeEl = document.getElementById('tmpl-ed-recur-type');
  if(typeEl) typeEl.value = t.recurrence_type || 'weekly';
  const dowEl = document.getElementById('tmpl-ed-recur-dow');
  if(dowEl && t.recurrence_dow != null) dowEl.value = String(t.recurrence_dow);
  const domEl = document.getElementById('tmpl-ed-recur-dom');
  if(domEl && t.recurrence_dom != null) domEl.value = String(t.recurrence_dom);
  const monthEl = document.getElementById('tmpl-ed-recur-month');
  if(monthEl && t.recurrence_month != null) monthEl.value = String(t.recurrence_month);
  const startEl = document.getElementById('tmpl-ed-recur-start');
  if(startEl) startEl.value = t.recurrence_time_start || '08:00';
  const endEl = document.getElementById('tmpl-ed-recur-end');
  if(endEl) endEl.value = t.recurrence_time_end || '09:00';
  onTmplRecurTypeChange();
}

// v2.6.1 : empreinte des deux dimensions du modele. Le formulaire renvoie tout
// a chaque enregistrement ; sans comparaison on ne saurait pas si l'admin a
// touche au CONTENU (operations), a la PLANIFICATION (regle + horaires), ou
// seulement au nom. Or ces deux dimensions n'ont pas les memes consequences et
// ne concernent pas les memes creneaux.
let _TMPL_INITIAL = null;
function _snapshotTmplForm(){
  let recur = '';
  try{ recur = JSON.stringify(_readRecurFromForm()); }catch(_){}
  const ops = (_TMPL_OPS || [])
    .filter(function(o){ return o.opTypeId; })
    .map(function(o){ return o.opTypeId + ':' + (o.machines || []).slice().sort().join('|'); })
    .sort().join(';');
  return { recur: recur, ops: ops };
}

function _readRecurFromForm(){
  const active = !!document.getElementById('tmpl-ed-recur-active')?.checked;
  if(!active){
    return { recurrence_active: false };
  }
  const type = document.getElementById('tmpl-ed-recur-type')?.value || 'weekly';
  const out = {
    recurrence_active: true,
    recurrence_type: type,
    recurrence_time_start: document.getElementById('tmpl-ed-recur-start')?.value || '08:00',
    recurrence_time_end:   document.getElementById('tmpl-ed-recur-end')?.value || '09:00',
  };
  if(type === 'weekly'){
    out.recurrence_dow = parseInt(document.getElementById('tmpl-ed-recur-dow')?.value || '0', 10);
  } else {
    out.recurrence_dom = parseInt(document.getElementById('tmpl-ed-recur-dom')?.value || '1', 10);
    if(type === 'yearly'){
      out.recurrence_month = parseInt(document.getElementById('tmpl-ed-recur-month')?.value || '1', 10);
    }
  }
  return out;
}

// Format lisible d'une règle de récurrence pour l'affichage
function _fmtRecurRule(t){
  if(!t.recurrence_active || !t.recurrence_type) return '';
  const dowLbl = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];
  const monthLbl = ['','Janv.','Févr.','Mars','Avril','Mai','Juin','Juil.','Août','Sept.','Oct.','Nov.','Déc.'];
  const time = (t.recurrence_time_start || '') + '–' + (t.recurrence_time_end || '');
  if(t.recurrence_type === 'weekly'){
    return 'Hebdo · ' + (dowLbl[t.recurrence_dow] || '?') + ' · ' + time;
  }
  if(t.recurrence_type === 'monthly'){
    return 'Mensuel · le ' + (t.recurrence_dom || '?') + ' · ' + time;
  }
  if(t.recurrence_type === 'quarterly'){
    return 'Trimestriel · le ' + (t.recurrence_dom || '?') + ' (Jan/Avr/Jul/Oct) · ' + time;
  }
  if(t.recurrence_type === 'yearly'){
    return 'Annuel · ' + (t.recurrence_dom || '?') + ' ' + (monthLbl[t.recurrence_month] || '?') + ' · ' + time;
  }
  return '';
}

// Format date FR courte pour "prochaine occurrence" et "dernière utilisation"
function _fmtDateFR(iso){
  if(!iso) return '—';
  try{
    const d = new Date(iso);
    if(isNaN(d.getTime())) return '—';
    return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth()+1)).slice(-2) + '/' + d.getFullYear();
  }catch(e){ return '—'; }
}

// v2.5.18 : layout inspire des .alert-row -- toggle recurrence a gauche,
// info au milieu, actions a droite. Le toggle n'est actif que si le template
// a bien un recurrence_type configure (sinon placeholder aligné pour ne pas
// casser la grille -- l'admin doit passer par Editer pour le configurer).
function renderTemplateManagePanel(){
  const box = document.getElementById('tmpl-manage-list');
  if(!box) return;
  const items = TEMPLATES_STATE.list || [];
  if(!items.length){
    box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucun mod\u00e8le pour l\'instant. Clique sur \u00ab + Nouveau mod\u00e8le \u00bb pour en cr\u00e9er un.</p>';
    return;
  }
  box.innerHTML = items.map(t => {
    const recurLbl = _fmtRecurRule(t);
    const hasRecurConfig = !!t.recurrence_type;
    // Toggle a gauche : actif si recurrence configuree, placeholder sinon.
    const toggleHtml = hasRecurConfig
      ? '<label class="toggle" title="' + (t.recurrence_active ? 'D\u00e9sactiver la r\u00e9currence' : 'Activer la r\u00e9currence') + '">' +
          '<input type="checkbox" ' + (t.recurrence_active ? 'checked' : '') + ' data-tmpl-toggle="' + escAttr(t.id) + '">' +
          '<span class="toggle-track"><span class="toggle-thumb"></span></span>' +
        '</label>'
      : '<span class="tmpl-manage-toggle-placeholder" title="Aucune r\u00e9currence configur\u00e9e \u2014 passe par \u00c9diter pour la param\u00e9trer"></span>';
    // Badges meta
    const recurBadge = hasRecurConfig
      ? (t.recurrence_active
          ? '<span class="tmpl-manage-badge recur-on" title="' + escAttr(recurLbl) + '">\ud83d\udd01 ' + escHtml(recurLbl) + '</span>'
          : '<span class="tmpl-manage-badge recur-off" title="' + escAttr(recurLbl) + '">R\u00e9currence \u00e9teinte : ' + escHtml(recurLbl) + '</span>')
      : '<span class="tmpl-manage-badge recur-off">Non r\u00e9current</span>';
    // v2.6.0 : badges « Prochaine : ... » et « Dernier : ... » retires -- la regle
    // de recurrence juste a cote donne deja la cadence, et la date de derniere
    // utilisation n'aide a aucune decision. La ligne etait sursaturee.
    const stats = '<span class="tmpl-manage-badge stat">' + (t.events_count || 0) + ' cr\u00e9neau' +
                  ((t.events_count || 0) > 1 ? 'x' : '') + ' cr\u00e9\u00e9s</span>';
    const opsBadge = '<span class="tmpl-manage-badge">' + (t.ops_count || 0) + ' op.</span>';
    // v2.5.31 : point d'entree decouvrable vers les occurrences supprimees.
    // Cliquer ouvre l'edition du modele directement sur la section depliee.
    const nDel = t.deleted_count || 0;
    const delBadge = nDel
      ? '<button type="button" class="tmpl-manage-badge del" ' +
        'title="Occurrence' + (nDel > 1 ? 's' : '') + ' retir\u00e9e' + (nDel > 1 ? 's' : '') +
        ' du calendrier \u2014 cliquer pour les voir et les restaurer" ' +
        'onclick="event.stopPropagation();openTemplateEditor(' + escAttr(t.id) + ', true)">' +
        nDel + ' supprim\u00e9e' + (nDel > 1 ? 's' : '') + '</button>'
      : '';
    // v2.5.25 : badge nb d'operateurs par defaut (warning si 0 pour un recurrent actif)
    const defaultOps = Array.isArray(t.default_operators) ? t.default_operators : [];
    const defaultOpsBadge = defaultOps.length
      ? '<span class="tmpl-manage-badge" title="' + escAttr(defaultOps.map(u => u.nom).join(', ')) + '">\u{1F464} ' + defaultOps.length + ' op\u00e9rateur' + (defaultOps.length > 1 ? 's' : '') + ' par d\u00e9faut</span>'
      : (t.recurrence_active
          ? '<span class="tmpl-manage-badge" style="background:rgba(245,158,11,.18);color:var(--warn,#f59e0b);border-color:rgba(245,158,11,.35)" title="R\u00e9currence active mais aucun op\u00e9rateur par d\u00e9faut \u2014 les cr\u00e9neaux g\u00e9n\u00e9r\u00e9s seront orphelins.">\u26a0 Sans op\u00e9rateur</span>'
          : '');
    return '<div class="tmpl-manage-item" data-tmpl-id="' + escAttr(t.id) + '">' +
      '<div class="tmpl-manage-toggle-wrap">' + toggleHtml + '</div>' +
      '<div class="tmpl-manage-info">' +
        '<div class="tmpl-manage-name">' + escHtml(t.name) + '</div>' +
        (t.description ? '<div class="tmpl-manage-desc">' + escHtml(t.description) + '</div>' : '') +
        '<div class="tmpl-manage-meta">' + opsBadge + defaultOpsBadge + recurBadge + stats + delBadge + '</div>' +
      '</div>' +
      '<div class="tmpl-manage-actions">' +
        '<button type="button" onclick="openTemplateEditor(' + escAttr(t.id) + ')">\u00c9diter</button>' +
        '<button type="button" onclick="duplicateTemplate(' + escAttr(t.id) + ')">Dupliquer</button>' +
        '<button type="button" class="danger" onclick="confirmDeleteTemplate(' + escAttr(t.id) + ')">Supprimer</button>' +
      '</div>' +
    '</div>';
  }).join('');
  // Post-render : plug le change handler sur chaque toggle (pattern reutilise des alertes).
  box.querySelectorAll('[data-tmpl-toggle]').forEach(function(el){
    el.addEventListener('change', function(){
      const id = parseInt(el.getAttribute('data-tmpl-toggle'), 10);
      toggleTemplateRecurrence(id, el.checked);
    });
  });
}

async function toggleTemplateRecurrence(templateId, activate){
  try{
    const r = await fetch('/api/maintenance/templates/' + encodeURIComponent(templateId), {
      method:'PATCH', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ recurrence_active: !!activate }),
    });
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      // Le toggle a echoue -- reload pour restaurer l'etat visuel a la valeur DB.
      await loadTemplates(true); renderTemplatesList(); renderTemplateManagePanel();
      throw new Error(err.detail || 'Modification refus\u00e9e');
    }
    // v2.5.18 : lit le nombre d'events futurs nettoyes (retourne par le backend
    // quand la recurrence est desactivee, cf. v2.5.13).
    let toastMsg;
    if(activate){
      toastMsg = 'R\u00e9currence activ\u00e9e.';
    } else {
      let deletedFuture = 0;
      try{ const j = await r.json(); deletedFuture = (j && j.deleted_future_events) || 0; }catch(_){}
      toastMsg = deletedFuture
        ? 'R\u00e9currence d\u00e9sactiv\u00e9e \u2014 ' + deletedFuture + ' cr\u00e9neau' + (deletedFuture > 1 ? 'x' : '') + ' futur' + (deletedFuture > 1 ? 's' : '') + ' nettoy' + (deletedFuture > 1 ? '\u00e9s' : '\u00e9') + '.'
        : 'R\u00e9currence d\u00e9sactiv\u00e9e.';
    }
    showToast(toastMsg, 'info');
    await loadTemplates(true);
    renderTemplatesList();
    renderTemplateManagePanel();
    // Refresh calendrier dans les deux cas (activation OU purge desactivation modifient le planning).
    await refreshPlanning(); renderCal();
  }catch(e){ showToast('Erreur : ' + e.message, 'danger'); }
}

async function generateTemplateNow(templateId){
  try{
    const r = await fetch('/api/maintenance/templates/' + encodeURIComponent(templateId) +
                          '/generate-now', { method:'POST', credentials:'include' });
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      throw new Error(err.detail || 'Génération refusée');
    }
    const d = await r.json();
    showToast(`${d.created} créneau${d.created > 1 ? 'x' : ''} créé${d.created > 1 ? 's' : ''}.`, 'info');
    await loadTemplates(true);
    renderTemplateManagePanel();
    await refreshPlanning();
    renderCal();
  }catch(e){ showToast('Erreur : ' + e.message, 'danger'); }
}

async function duplicateTemplate(templateId){
  try{
    // Récupère le modèle source
    const r = await fetch('/api/maintenance/templates/' + encodeURIComponent(templateId), { credentials:'include' });
    if(!r.ok) throw new Error('Modèle introuvable');
    const d = await r.json();
    const src = d.template;
    // Duplique avec un nom incrémenté
    let newName = src.name + ' (copie)';
    // Envoie
    const r2 = await fetch('/api/maintenance/templates', {
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        name: newName,
        description: src.description,
        ops: (src.ops || []).map(o => ({ code: o.code, machines: o.machines || [] })),
        // Récurrence copiée mais DÉSACTIVÉE par défaut (l'utilisateur active si voulu)
        recurrence_type: src.recurrence_type,
        recurrence_dow: src.recurrence_dow,
        recurrence_dom: src.recurrence_dom,
        recurrence_month: src.recurrence_month,
        recurrence_time_start: src.recurrence_time_start,
        recurrence_time_end: src.recurrence_time_end,
        recurrence_active: false,
      }),
    });
    if(!r2.ok){
      const err = await r2.json().catch(()=>({}));
      throw new Error(err.detail || 'Duplication refusée');
    }
    showToast('Modèle dupliqué (récurrence désactivée).', 'info');
    await loadTemplates(true);
    renderTemplatesList();
    renderTemplateManagePanel();
  }catch(e){ showToast('Erreur : ' + e.message, 'danger'); }
}

async function saveEventAsTemplate(eventId){
  const name = prompt('Nom du nouveau modèle :');
  if(!name || !name.trim()) return;
  try{
    const r = await fetch('/api/maintenance/events/' + encodeURIComponent(eventId) + '/save-as-template', {
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name: name.trim() }),
    });
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      throw new Error(err.detail || 'Sauvegarde refusée');
    }
    const d = await r.json();
    showToast('Modèle « ' + d.name + ' » créé depuis ce créneau.', 'info');
    await loadTemplates(true);
    renderTemplateManagePanel();
    refreshCaseTemplatePicker();
  }catch(e){ showToast('Erreur : ' + e.message, 'danger'); }
}


/* ── Éditeur de modèle (création + édition) ──────────────────────── */

let _TMPL_EDIT_ID = null;
let _TMPL_OPS = [];
// v2.5.25 : opérateurs par défaut du template en cours d'édition [{id, nom}]
let _TMPL_DEFAULT_OPS = [];

// v2.5.31 : focusDeleted=true -> deplie la section « Occurrences supprimees »
// et la fait defiler dans la vue (utilise par le badge du panel Gestion).
async function openTemplateEditor(templateId, focusDeleted){
  _TMPL_EDIT_ID = templateId || null;
  _TMPL_OPS = [];
  _TMPL_DEFAULT_OPS = [];
  // v2.5.25 : charge le catalogue d'operateurs en arriere-plan pour le picker.
  try{ if(typeof _loadOperatorsCatalog === 'function') await _loadOperatorsCatalog(); }catch(_){}
  const m = document.getElementById('tmpl-editor-modal');
  const nameEl = document.getElementById('tmpl-ed-name');
  const descEl = document.getElementById('tmpl-ed-desc');
  const ttlEl = document.getElementById('tmpl-ed-title');
  const lblEl = document.getElementById('tmpl-ed-submit-label');
  const warnEl = document.getElementById('tmpl-ed-warning');
  if(nameEl) nameEl.value = '';
  if(descEl) descEl.value = '';
  if(warnEl){ warnEl.style.display = 'none'; warnEl.innerHTML = ''; }
  // v2.4.29 : reset recurrence fields
  _setRecurInForm({ recurrence_active:false, recurrence_type:'weekly',
                    recurrence_dow:0, recurrence_dom:1, recurrence_month:1,
                    recurrence_time_start:'08:00', recurrence_time_end:'09:00' });
  if(templateId){
    try{
      const r = await fetch('/api/maintenance/templates/' + encodeURIComponent(templateId) +
                            '?_=' + Date.now(), { credentials:'include', cache: 'no-store' });
      if(!r.ok) throw new Error('Modèle introuvable');
      const d = await r.json();
      const t = d.template;
      if(nameEl) nameEl.value = t.name || '';
      if(descEl) descEl.value = t.description || '';
      // v2.4.29 : populate recurrence fields depuis le template charge
      _setRecurInForm(t);
      _TMPL_OPS = (t.ops || []).map(o => {
        const meta = OPS_TYPES_STATE.list.find(x => x.id === o.code);
        return {
          opTypeId: o.code,
          opName: (meta && meta.nom) || o.code_label || o.code,
          opNiveau: (meta && meta.niveau) || null,
          opFreq: (meta && meta.frequence) || '',
          machines: Array.isArray(o.machines) ? o.machines.slice() : [],
        };
      });
      // v2.5.25 : charge les operateurs par defaut du template
      _TMPL_DEFAULT_OPS = (t.default_operators || []).map(u => ({ id: u.id, nom: u.nom }));
      if(ttlEl) ttlEl.textContent = 'Modifier le modèle';
      // v2.6.1 : empreinte de reference, prise une fois le formulaire rempli.
      _TMPL_INITIAL = _snapshotTmplForm();
      if(lblEl) lblEl.textContent = 'Enregistrer';
      // Avertissement resync
      if(warnEl){
        warnEl.innerHTML = '<strong>Attention :</strong> les modifications se répercutent sur les créneaux futurs issus de la récurrence de ce modèle. Changer la <strong>liste d\'opérations</strong> resynchronise leurs opérations, sans toucher aux dates ni aux horaires. Changer la <strong>règle de récurrence</strong> replace ces créneaux aux nouvelles dates. Les créneaux composés à la main, même après import de ce modèle, ne sont jamais touchés.';
        warnEl.style.display = 'block';
      }
    }catch(e){ showToast('Erreur : ' + e.message, 'danger'); return; }
  } else {
    if(ttlEl) ttlEl.textContent = 'Nouveau modèle';
    if(lblEl) lblEl.textContent = 'Créer';
  }
  renderTmplOpsList();
  renderTmplDefaultOps();
  // v2.5.31 : reset immediat de la section « Occurrences supprimees » (elle est
  // masquee tant que le fetch n'a rien renvoye), puis chargement en tache de
  // fond pour ne pas retarder l'ouverture du modal.
  TMPL_DELETED_STATE.templateId = templateId || null;
  TMPL_DELETED_STATE.list = [];
  renderTmplDeletedOccurrences();
  if(m){ m.classList.add('open'); m.setAttribute('aria-hidden', 'false'); }
  document.body.style.overflow = 'hidden';
  setTimeout(() => { nameEl?.focus(); }, 60);
  if(templateId){
    loadTmplDeletedOccurrences(templateId).then(() => {
      if(!focusDeleted) return;
      const block = document.getElementById('tmpl-ed-deleted-block');
      if(!block || block.style.display === 'none') return;
      block.classList.add('open');
      document.getElementById('tmpl-ed-deleted-toggle')?.setAttribute('aria-expanded', 'true');
      try{ block.scrollIntoView({ behavior: 'smooth', block: 'center' }); }catch(_){ block.scrollIntoView(); }
    });
  }
}

function closeTemplateEditor(){
  const m = document.getElementById('tmpl-editor-modal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden', 'true'); }
  document.body.style.overflow = '';
  _TMPL_EDIT_ID = null;
  _TMPL_OPS = [];
  _TMPL_DEFAULT_OPS = [];
  // v2.5.31 : referme la section « Occurrences supprimees » pour la prochaine
  // ouverture (sinon elle resterait depliee sur un autre modele).
  TMPL_DELETED_STATE.templateId = null;
  TMPL_DELETED_STATE.list = [];
  const delBlock = document.getElementById('tmpl-ed-deleted-block');
  if(delBlock){ delBlock.classList.remove('open'); delBlock.style.display = 'none'; }
}

// v2.5.25 : rendu du picker + de la liste d'operateurs par defaut du template.
function renderTmplDefaultOps(){
  const list = document.getElementById('tmpl-ed-default-op-list');
  const picker = document.getElementById('tmpl-ed-default-op-picker');
  if(list){
    if(!_TMPL_DEFAULT_OPS.length){
      list.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:6px 0;font-style:italic">Aucun op\u00e9rateur par d\u00e9faut \u2014 les cr\u00e9neaux g\u00e9n\u00e9r\u00e9s seront orphelins.</div>';
    } else {
      list.innerHTML = _TMPL_DEFAULT_OPS.map(op =>
        '<div style="display:inline-flex;align-items:center;gap:6px;background:var(--accent-bg);color:var(--accent);border-radius:8px;padding:4px 10px;font-size:12px;font-weight:600;margin:4px 6px 0 0">' +
          escHtml(op.nom || '') +
          '<button type="button" onclick="removeTmplDefaultOp(' + op.id + ')" style="background:transparent;border:none;color:inherit;cursor:pointer;font-size:14px;line-height:1;padding:0 0 0 4px">\u00d7</button>' +
        '</div>'
      ).join('');
    }
  }
  if(picker){
    const assigned = new Set(_TMPL_DEFAULT_OPS.map(o => o.id));
    const available = (_OPERATORS_CATALOG || []).filter(u => !assigned.has(u.id));
    picker.innerHTML = '<option value="">Ajouter un op\u00e9rateur\u2026</option>' +
      available.map(u => '<option value="' + u.id + '">' + escHtml(u.nom) + '</option>').join('');
  }
}

function addTmplDefaultOpFromPicker(sel){
  const id = parseInt(sel.value, 10);
  if(!id) return;
  const user = (_OPERATORS_CATALOG || []).find(u => u.id === id);
  if(!user) return;
  if(_TMPL_DEFAULT_OPS.find(o => o.id === id)) return;
  _TMPL_DEFAULT_OPS.push({ id: user.id, nom: user.nom });
  renderTmplDefaultOps();
}

function removeTmplDefaultOp(id){
  _TMPL_DEFAULT_OPS = _TMPL_DEFAULT_OPS.filter(o => o.id !== id);
  renderTmplDefaultOps();
}

function addTmplOp(){
  if(!OPS_TYPES_STATE.list.length){
    showToast('Aucune opération dans la liste. Ajoutez-en d\'abord dans "Liste d\'opérations de maintenance".', 'danger');
    return;
  }
  _TMPL_OPS.push({ opTypeId: '', opName: '', opNiveau: null, opFreq: '', machines: [] });
  renderTmplOpsList();
}

function updateTmplOp(idx, opTypeId){
  if(idx < 0 || idx >= _TMPL_OPS.length) return;
  const cur = _TMPL_OPS[idx];
  const op = OPS_TYPES_STATE.list.find(t => t.id === opTypeId);
  if(op){
    _TMPL_OPS[idx] = {
      opTypeId: op.id, opName: op.nom, opNiveau: op.niveau || null, opFreq: op.frequence || '',
      machines: Array.isArray(cur.machines) ? cur.machines.slice() : [],
    };
  } else {
    _TMPL_OPS[idx] = { opTypeId: '', opName: '', opNiveau: null, opFreq: '', machines: Array.isArray(cur.machines) ? cur.machines.slice() : [] };
  }
}

function toggleTmplOpMachine(idx, machine){
  if(idx < 0 || idx >= _TMPL_OPS.length) return;
  const cur = _TMPL_OPS[idx];
  const list = Array.isArray(cur.machines) ? cur.machines : [];
  const pos = list.indexOf(machine);
  if(pos >= 0) list.splice(pos, 1); else list.push(machine);
  cur.machines = list;
  renderTmplOpsList();
}

function removeTmplOp(idx){
  if(idx < 0 || idx >= _TMPL_OPS.length) return;
  _TMPL_OPS.splice(idx, 1);
  renderTmplOpsList();
}

function renderTmplOpsList(){
  const list = document.getElementById('tmpl-ed-ops-list');
  if(!list) return;
  if(!_TMPL_OPS.length){
    list.innerHTML = '<div class="case-ops-empty">Aucune opération. Cliquez sur « Ajouter une opération » pour construire le modèle.</div>';
    return;
  }
  list.innerHTML = _TMPL_OPS.map((op, idx) => {
    const options = '<option value="">Sélectionner une opération…</option>' +
      OPS_TYPES_STATE.list.map(t =>
        '<option value="' + escAttr(t.id) + '"' + (t.id === op.opTypeId ? ' selected' : '') + '>' +
          escHtml(t.nom) + (t.niveau ? ' (N' + t.niveau + ')' : '') +
          (t.frequence ? ' · ' + escHtml(t.frequence) : '') +
        '</option>'
      ).join('');
    const machSet = new Set(Array.isArray(op.machines) ? op.machines : []);
    const chips = CASE_MACHINES_LIST.map(m => {
      const active = machSet.has(m);
      return '<button type="button" class="case-mach-chip' + (active ? ' active' : '') + '" onclick="toggleTmplOpMachine(' + idx + ', \'' + escAttr(m) + '\')" aria-pressed="' + (active ? 'true' : 'false') + '">' +
        escHtml(m) + '</button>';
    }).join('');
    return '<div class="case-ops-row" data-idx="' + idx + '">' +
      '<div class="case-ops-row-top">' +
        '<select class="ops-select" onchange="updateTmplOp(' + idx + ', this.value)">' + options + '</select>' +
        '<button type="button" class="case-ops-row-del" onclick="removeTmplOp(' + idx + ')" title="Retirer" aria-label="Retirer">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="case-ops-machines">' +
        '<span class="case-ops-machines-label">Machine(s)</span>' +
        chips +
      '</div>' +
    '</div>';
  }).join('');
}

async function submitTemplateEditor(e){
  e.preventDefault();
  const name = (document.getElementById('tmpl-ed-name')?.value || '').trim();
  const desc = (document.getElementById('tmpl-ed-desc')?.value || '').trim();
  if(!name){ showToast('Nom requis.', 'danger'); return; }
  const ops = _TMPL_OPS.filter(o => o.opTypeId).map(o => ({
    code: o.opTypeId,
    machines: Array.isArray(o.machines) ? o.machines.slice() : [],
  }));
  if(!ops.length){ showToast('Ajoutez au moins une opération.', 'danger'); return; }
  const missing = ops.find(o => !o.machines.length);
  if(missing){ showToast('Attribuez au moins une machine à chaque opération.', 'danger'); return; }
  // v2.6.1 : avertissement AVANT enregistrement. La resynchronisation ecrase
  // integralement les operations des occurrences futures generees par la
  // recurrence (et leurs operateurs si le modele est recurrent). Elle se
  // declenche des que des ops sont envoyees, meme inchangees — il faut donc
  // que l'admin sache combien de creneaux il s'apprete a reinitialiser.
  let _TMPL_RESYNC_EXCLUDE = [];
  if(_TMPL_EDIT_ID){
    try{
      const ri = await fetch('/api/maintenance/templates/' + encodeURIComponent(_TMPL_EDIT_ID) +
                             '/resync-impact?_=' + Date.now(), { credentials:'include', cache:'no-store' });
      if(ri.ok){
        const imp = await ri.json();
        const n = (imp && imp.count) || 0;
        const snap = _snapshotTmplForm();
        // Si l'empreinte de reference manque (ouverture inhabituelle), on
        // considere les deux dimensions comme modifiees : mieux vaut demander
        // pour rien que d'ecraser en silence.
        const opsChanged   = !_TMPL_INITIAL || snap.ops   !== _TMPL_INITIAL.ops;
        const recurChanged = !_TMPL_INITIAL || snap.recur !== _TMPL_INITIAL.recur;
        // Chaque dimension a SA population de creneaux a risque :
        //  - operations modifiees -> ceux dont la liste d'ops a diverge ;
        //  - regle modifiee       -> ceux deplaces a la main, dont la position
        //    serait ecrasee. Un creneau reste a sa place theorique est replace
        //    sans consequence, inutile d'en parler.
        const div = opsChanged   ? ((imp && imp.diverged) || []) : [];
        const mov = recurChanged ? ((imp && imp.moved)    || []) : [];
        // v2.6.1 : on n'interroge l'admin QUE sur les creneaux personnalises.
        // Les copies conformes sont resynchronisees sans question — l'operation
        // est un no-op pour elles. Case cochee = « préserver ce créneau » :
        // le defaut protege ce qui a ete modifie a la main, il faut un geste
        // explicite pour ecraser.
        const _rows = function(items){
          return items.map(function(d){
            const grave = d.done_ops > 0;
            return '<label class="mys-keep-row' + (grave ? ' is-grave' : '') + '">' +
                   '<input type="checkbox" data-keep="' + escAttr(d.id) + '" checked>' +
                   '<span class="mys-keep-txt">' +
                     '<span class="mys-keep-date">' + escHtml(_fmtIsoDateFr(d.date)) + '</span>' +
                     '<span class="mys-keep-why">' + escHtml((d.reasons || []).join(' · ')) + '</span>' +
                   '</span></label>';
          }).join('');
        };
        if(div.length || mov.length){
          let body = '';
          if(mov.length){
            body += '<div style="margin-bottom:8px"><strong>Planification modifiée.</strong> ' +
                    'Ces créneaux ont été déplacés à la main ; les replacer écraserait leur position. ' +
                    'Les cases cochées restent où elles sont.</div>' +
                    '<div class="mys-keep-list">' + _rows(mov) + '</div>';
            if(imp.unmoved_count){
              body += '<div style="margin:8px 0 14px;color:var(--muted);font-size:12px">' + imp.unmoved_count +
                      ' autre(s) créneau(x) sont à leur place théorique : ils suivront la nouvelle règle, ' +
                      'sans perdre leurs opérations.</div>';
            }
          }
          if(div.length){
            body += '<div style="margin-bottom:8px' + (mov.length ? ';margin-top:14px;padding-top:14px;border-top:1px solid var(--border)' : '') + '">' +
                    '<strong>Opérations modifiées.</strong> ' +
                    'Ces créneaux ont une liste d\'opérations personnalisée. ' +
                    'Décoche ceux que tu veux réinitialiser ; les cases cochées seront préservées.</div>' +
                    '<div class="mys-keep-list">' + _rows(div) + '</div>';
            if(imp.identical_count){
              body += '<div style="margin-top:8px;color:var(--muted);font-size:12px">' + imp.identical_count +
                      ' autre(s) créneau(x) sont identiques au modèle : aucun changement visible pour eux.</div>';
            }
          }
          const total = div.length + mov.length;
          const ok = await _mysConfirm({
            title: total + ' créneau' + (total > 1 ? 'x' : '') + ' à confirmer',
            bodyHtml: body,
            okLabel: 'Enregistrer',
            cancelLabel: 'Annuler',
          });
          if(!ok) return;
          _TMPL_RESYNC_EXCLUDE = _MYS_CONFIRM_LAST_KEEP.slice();
        } else if(n > 0 && opsChanged){
          const plur = n > 1;
          let quand = '';
          if(imp.first && imp.last && imp.first !== imp.last){
            quand = ' (du ' + _fmtIsoDateFr(imp.first) + ' au ' + _fmtIsoDateFr(imp.last) + ')';
          } else if(imp.first){
            quand = ' (le ' + _fmtIsoDateFr(imp.first) + ')';
          }
          const ok = await _mysConfirm({
            title: 'Réinitialiser ' + n + ' créneau' + (plur ? 'x' : '') + ' à venir ?',
            highlightHtml:
              '<div style="font-size:14px;font-weight:700;color:var(--text)">' +
                n + ' créneau' + (plur ? 'x' : '') + ' généré' + (plur ? 's' : '') + ' par la récurrence' +
              '</div>' +
              (quand ? '<div style="font-size:12px;color:var(--muted);margin-top:4px">' + escHtml(quand.trim()) + '</div>' : ''),
            bodyHtml:
              'Leurs opérations seront <strong>remplacées par celles du modèle</strong>. ' +
              'Toute retouche faite directement sur ces créneaux (opération ajoutée, machine décochée, consignes) sera perdue.' +
              '<div style="margin-top:10px;color:var(--muted);font-size:12px">' +
                'Les créneaux passés et ceux composés à la main ne sont pas concernés.' +
              '</div>',
            okLabel: 'Enregistrer quand même',
            cancelLabel: 'Annuler',
          });
          if(!ok) return;
        }
      }
    }catch(_){ /* impact indisponible : on n'empeche pas l'enregistrement */ }
  }
  try{
    let r;
    // v2.4.29 : fusion avec les champs recurrence
    const recur = _readRecurFromForm();
    // v2.5.25 : inclut la liste des ids d'operateurs par defaut
    const defaultOpIds = (_TMPL_DEFAULT_OPS || []).map(u => u.id);
    const payload = Object.assign({ name, description: desc, ops, default_operators: defaultOpIds }, recur);
    if(_TMPL_RESYNC_EXCLUDE.length) payload.resync_exclude_ids = _TMPL_RESYNC_EXCLUDE;
    if(_TMPL_EDIT_ID){
      r = await fetch('/api/maintenance/templates/' + encodeURIComponent(_TMPL_EDIT_ID), {
        method:'PATCH', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload),
      });
    } else {
      r = await fetch('/api/maintenance/templates', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload),
      });
    }
    if(!r.ok){
      const err = await r.json().catch(()=>({}));
      throw new Error(err.detail || 'Enregistrement refusé');
    }
    const d = await r.json();
    const resynced = d.resynced_events || 0;
    // v2.6.1 : replacement du planning suite a un changement de regle.
    const replaced = d.recur_replaced_events || 0;
    const regen    = d.recur_regenerated_events || 0;
    // v2.5.13 : mention les creneaux futurs supprimes si la recurrence a ete desactivee.
    const deletedFuture = d && d.deleted_future_events ? d.deleted_future_events : 0;
    let toastMsg;
    if(!_TMPL_EDIT_ID){
      toastMsg = 'Mod\u00e8le cr\u00e9\u00e9.';
    } else {
      const parts = ['Mod\u00e8le enregistr\u00e9'];
      if(resynced) parts.push(resynced + ' cr\u00e9neau' + (resynced > 1 ? 'x' : '') + ' futur' + (resynced > 1 ? 's' : '') + ' resynchronis' + (resynced > 1 ? '\u00e9s' : '\u00e9'));
      if(deletedFuture) parts.push(deletedFuture + ' cr\u00e9neau' + (deletedFuture > 1 ? 'x' : '') + ' futur' + (deletedFuture > 1 ? 's' : '') + ' nettoy' + (deletedFuture > 1 ? '\u00e9s' : '\u00e9') + ' (r\u00e9currence d\u00e9sactiv\u00e9e)');
      if(replaced) parts.push('planning replac\u00e9 : ' + replaced + ' occurrence' + (replaced > 1 ? 's' : '') + ' remplac\u00e9' + (replaced > 1 ? 'es' : 'e') + ' par ' + regen + ' nouvelle' + (regen > 1 ? 's' : ''));
      toastMsg = parts.join(' \u2014 ') + '.';
    }
    showToast(toastMsg, 'info');
    closeTemplateEditor();
    await loadTemplates(true);
    renderTemplatesList();
    refreshCaseTemplatePicker();
    // v2.5.13 : refresh calendrier si des events ont bouge (resync OU purge desactivation)
    // v2.7.1 : le rechargement du calendrier ne tenait compte que des
    // operations resynchronisees et des creneaux supprimes. Un changement de
    // REGLE de recurrence deplace les occurrences sans rien resynchroniser ni
    // supprimer : la condition etait donc fausse, le planning restait affiche
    // avec les dates d'avant, et l'utilisateur croyait le replacement rate
    // alors qu'il avait bien eu lieu en base.
    if(resynced > 0 || deletedFuture > 0 || replaced > 0 || regen > 0
       || (d.recur_moved_events || 0) > 0 || (d.recur_removed_events || 0) > 0){
      await refreshPlanning();
      renderCal();
    }
  }catch(e){ showToast('Erreur : ' + e.message, 'danger'); }
}

/* ── Bouton flottant « + » du calendrier ─────────────────────────── */

function toggleCalFabMenu(){
  const m = document.getElementById('cal-fab-menu');
  if(!m) return;
  const willOpen = !m.classList.contains('open');
  if(willOpen){
    loadTemplates().then(() => renderCalFabMenu());
  }
  m.classList.toggle('open');
}

function closeCalFabMenu(){
  const m = document.getElementById('cal-fab-menu');
  if(m) m.classList.remove('open');
}

function renderCalFabMenu(){
  const m = document.getElementById('cal-fab-menu');
  if(!m) return;
  const list = TEMPLATES_STATE.list || [];
  const tmplItems = list.length
    ? list.map(t => `
        <button type="button" class="cal-fab-menu-item" onclick="startFromTemplate(${escAttr(t.id)})">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>
          <span>${escHtml(t.name)} <span style="color:var(--muted);font-weight:500">· ${t.ops_count} op.</span></span>
        </button>`).join('')
    : '<div class="cal-fab-menu-hint">Aucun modèle disponible</div>';
  m.innerHTML = `
    <button type="button" class="cal-fab-menu-item" onclick="startBlankCreneau()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      <span>Créneau vierge</span>
    </button>
    <div class="cal-fab-menu-sep"></div>
    <div class="cal-fab-menu-hint">Depuis un modèle</div>
    ${tmplItems}
    <div class="cal-fab-menu-sep"></div>
    <button type="button" class="cal-fab-menu-item" onclick="closeCalFabMenu();openTemplatesModal();">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/></svg>
      <span>Gérer les modèles…</span>
    </button>`;
}

function _defaultIsoAndHour(){
  return { iso: _fmtDateISO(new Date()), h: 8 };
}

function startBlankCreneau(){
  closeCalFabMenu();
  const { iso, h } = _defaultIsoAndHour();
  openCaseModal({ iso, defaultHour: h });
}

async function startFromTemplate(templateId){
  closeCalFabMenu();
  const { iso, h } = _defaultIsoAndHour();
  await openCaseModal({ iso, defaultHour: h });
  // v2.6.1 : pre-remplit les operations depuis le modele, sans creer de lien
  // (applyCaseTemplate ne pose plus template_id). Le select revient sur son
  // option neutre : c'est une action d'import, pas l'etat du creneau.
  await applyCaseTemplate(templateId);
  const sel = document.getElementById('case-mod-template');
  if(sel) sel.value = '';
}


// Ferme le menu FAB au clic en dehors
document.addEventListener('click', (e) => {
  const menu = document.getElementById('cal-fab-menu');
  if(!menu || !menu.classList.contains('open')) return;
  if(e.target.closest('.cal-fab') || e.target.closest('.cal-fab-menu')) return;
  menu.classList.remove('open');
});

// v163+ : pour l'opérateur, on déplace le calendrier admin dans l'onglet
// « Planning général » et on masque le date-picker + tabs redondants.
// Le calendrier reste 100% fonctionnel en navigation (mois/sem/jour, prev/next,
// clic sur créneau existant pour voir les détails) mais tous les points
// d'écriture sont neutralisés (voir onCalCellClick, onCalMonthCellClick,
// et .plan-det-case-actions masqué en CSS).
function _mountOperatorGeneralCalendar(){
  if(MAINT_ROLE !== 'operator') return;
  const src = document.querySelector('#view-planning .cal-sec');
  const dst = document.getElementById('op-plan-general');
  if(!src || !dst) return;
  if(!dst.querySelector('.cal-sec')){
    // 1er mount : vide le tableau read-only par défaut, déplace le calendrier
    // (déplacer plutôt que cloner : les listeners JS sur .cal-event / cellules
    // sont attachés au node, et renderCal() cible par ID unique — un clone
    // dupliquerait les IDs et casserait le rendu).
    dst.innerHTML = '';
    // Bandeau discret "lecture seule" au-dessus du calendrier
    const banner = document.createElement('div');
    banner.className = 'op-cal-readonly-banner';
    banner.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>' +
      '<span>Planning atelier (lecture seule) — clique sur un créneau pour voir le détail.</span>';
    dst.appendChild(banner);
    dst.appendChild(src);
  }
  // Masque le date-picker haut de page (le calendrier a sa propre nav)
  const datePicker = document.querySelector('#view-op-planning .op-date-picker');
  if(datePicker) datePicker.style.display = 'none';
}

// Wrapper autour de opSetPlanTab pour déclencher le rendu du calendrier
// à l'arrivée sur l'onglet Général — refresh systématique (pas seulement
// au premier clic) pour que la vue reflète les changements admin en direct.
const _origOpSetPlanTab = typeof opSetPlanTab === 'function' ? opSetPlanTab : null;
function opSetPlanTabWithCal(name){
  if(_origOpSetPlanTab) _origOpSetPlanTab(name);
  if(name === 'general' && MAINT_ROLE === 'operator'){
    _mountOperatorGeneralCalendar();
    refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
  }
}
// Remplace l'implémentation exposée sur window (utilisée par onclick)
window.opSetPlanTab = opSetPlanTabWithCal;

(function initMaintRole(){
  // Ajoute un attribut sur <body> pour le ciblage CSS role-based
  document.body.setAttribute('data-maint-role', MAINT_ROLE || 'operator');
  if(MAINT_ROLE === 'operator'){
    // L'opérateur arrive sur "Mes tâches" — on charge la liste du jour.
    const dateInput = document.getElementById('op-tasks-date');
    if(dateInput) dateInput.value = _fmtDateISO(new Date());
    const planInput = document.getElementById('op-plan-date');
    if(planInput) planInput.value = _fmtDateISO(new Date());
    opLoadTasks();
    // Monte le calendrier admin dans l'onglet Général AVANT opLoadPlanning
    // (le mount déplace .cal-sec dans #op-plan-general ; l'ordre garantit
    // qu'aucune écriture postérieure n'écrase le calendrier).
    _mountOperatorGeneralCalendar();
    // Pré-charge le planning (table Personnel + refresh du calendrier)
    opLoadPlanning();
    // Rendu initial du calendrier depuis les données admin (±90 jours).
    refreshPlanning().then(() => { try{ renderCal(); }catch(e){} });
  }
})();

// ═══════════════════════════════════════════════════════════════════
// v2.2.28 : Panel Codes maintenance — duplication de settings_page.py
// Réutilise les adapters esc/toast/api de v2.2.19 (déjà en place).
// ═══════════════════════════════════════════════════════════════════
// v2.2.29 fix : déclarations globales oubliées (lignes 4587-4588 de settings_page.py)

// ─── Interventions libres (Lot 2) ────────────────────────────────
// Curation admin des codes libre=1 : lister, renommer, archiver, fusionner.




function libresToggleSelection(code, checked) {
  if (checked) {
    _libresSelection.add(code);
    if (_libresSelection.size > 2) {
      const arr = Array.from(_libresSelection);
      _libresSelection = new Set(arr.slice(-2));
      renderLibresList();
    }
  } else {
    _libresSelection.delete(code);
  }
  _updateLibresSelectionUI();
}


async function libresRename(code, currentLabel) {
  const newLabel = prompt('Nouveau titre pour l\u2019intervention libre :', currentLabel || '');
  if (newLabel === null) return;
  const trimmed = (newLabel || '').trim();
  if (!trimmed) { toast('Titre obligatoire', true); return; }
  if (trimmed === currentLabel) return;
  try {
    await api('/api/maintenance/codes/libres/' + encodeURIComponent(code), {
      method: 'PATCH',
      body: JSON.stringify({ label: trimmed }),
    });
    toast('Titre modifie');
    await loadLibres();
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
}

async function libresDelete(code, label) {
  if (!confirm('Archiver definitivement "' + label + '" (' + code + ') ?\n\nCette action est reversible uniquement via SQL manuel.')) return;
  try {
    await api('/api/maintenance/codes/libres/' + encodeURIComponent(code), { method: 'DELETE' });
    toast('Titre archive');
    _libresSelection.delete(code);
    await loadLibres();
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
}

async function libresMergeSelected() {
  if (_libresSelection.size !== 2) return;
  const codes = Array.from(_libresSelection);
  const items = codes.map(c => _libresItems.find(x => x.code === c)).filter(Boolean);
  if (items.length !== 2) { toast('Selection invalide', true); return; }
  const opts = items.map((it, i) => (i + 1) + '. ' + it.label + ' (' + it.usage_count + ' saisie' + (it.usage_count > 1 ? 's' : '') + ')').join('\n');
  const choice = prompt(
    'Quel titre garder pour la fusion ?\n\n' + opts + '\n\nSaisis 1 ou 2 :',
    items[0].usage_count >= items[1].usage_count ? '1' : '2'
  );
  if (choice === null) return;
  const idx = parseInt(choice, 10) - 1;
  if (idx !== 0 && idx !== 1) { toast('Choix invalide (1 ou 2 attendu)', true); return; }
  const winner = items[idx];
  const loser = items[1 - idx];
  if (!confirm(
    'Fusionner "' + loser.label + '" (' + loser.usage_count + ' saisie' + (loser.usage_count > 1 ? 's' : '') + ') vers "' + winner.label + '" ?\n\n' +
    'Toutes les saisies passees de "' + loser.label + '" seront desormais attribuees a "' + winner.label + '".\n' +
    'Le titre "' + loser.label + '" (' + loser.code + ') sera supprime.'
  )) return;
  try {
    await api('/api/maintenance/codes/libres/merge', {
      method: 'POST',
      body: JSON.stringify({ winner_code: winner.code, loser_code: loser.code }),
    });
    toast('Fusion effectuee');
    _libresSelection.clear();
    await loadLibres();
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur', true);
  }
}


// ── Documents attaches aux codes maintenance ─────────────────────────────


// Clic sur le bouton "+ Ajouter un fichier" -> ouvre le picker natif cache.

// Compat : appele par openMaintForm, mais l'upload est declenche directement
// par onchange du <input type=file>. No-op.

// Picker onchange -> upload immediat (pas de bouton Envoyer intermediaire).

// Active/désactive Intervalle et Réf. métrage selon Périodique :
//   - Périodique = OUI : les deux champs sont actifs (l'utilisateur peut
//     remplir l'intervalle de temps et/ou la référence métrage).
//   - Périodique = NON : les deux champs sont vidés et grisés.
function closeMaintForm() {
  _maintEditCode = null;
  const wrap = document.getElementById('maint-form-wrap');
  if (wrap) wrap.classList.add('hidden');
}
async function saveMaintForm() {
  const code = (document.getElementById('maint-code').value || '').trim();
  const label = (document.getElementById('maint-label').value || '').trim();
  const niveau = parseInt(document.getElementById('maint-niveau').value, 10) || 1;
  const rawCat = (document.getElementById('maint-categorie')?.value || '').trim();
  // Depuis v178 : 3 catégories ('controles', 'entretien', 'remplacements').
  // Legacy 'interventions' est remappée vers 'entretien' pour rester compat.
  const categorie = (rawCat === 'entretien' || rawCat === 'remplacements' || rawCat === 'controles')
    ? rawCat
    : (rawCat === 'interventions' ? 'entretien' : 'controles');
  // v2.2.17 — periodique forcé à true (concept retiré côté UI).
  const periodique = true;
  const intervalle  = (document.getElementById('maint-intervalle')?.value  || '').trim();
  const metrage_ref = (document.getElementById('maint-metrage-ref')?.value || '').trim();
  if (!code) { toast('Code obligatoire', true); return; }
  if (!label) { toast('Libellé obligatoire', true); return; }
  if (niveau < 1 || niveau > 3) { toast('Niveau invalide (1-3)', true); return; }
  // v230 : l'état des 2 cases à cocher est traduit en payload par le module
  // partagé — une seule source de vérité pour les 2 pages hôtes.
  const _usure = (typeof _maintUsurePayload === 'function')
    ? _maintUsurePayload()
    : { usure_piece_id: null, usure_position: '' };
  if (document.getElementById('maint-usure-on')?.checked && !_usure.usure_piece_id) {
    toast('Choisis une pièce d\'usure, ou décoche la case.', true); return;
  }
  if (_usure.usure_piece_id && document.getElementById('maint-usure-haspos')?.checked
      && !_usure.usure_position) {
    toast('Renseigne le nom de la position, ou décoche « Position particulière ».', true); return;
  }
  const payload = { code, label, niveau, categorie, periodique, intervalle, metrage_ref,
                    usure_piece_id: _usure.usure_piece_id, usure_position: _usure.usure_position };
  try {
    if (_maintEditCode) {
      await api('/api/maintenance/codes/' + encodeURIComponent(_maintEditCode), {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      toast('Code mis à jour');
    } else {
      await api('/api/maintenance/codes', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      toast('Code ajouté');
    }
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur lors de l\'enregistrement', true);
    return;
  }
  closeMaintForm();
  await loadMaintCodes();
  // v2.7.1 : un code cree ou renomme doit apparaitre immediatement dans la
  // modal de saisie et les filtres — meme invalidation que la suppression.
  if(typeof window.maintOnCatalogueChanged === 'function'){
    try { await window.maintOnCatalogueChanged(); } catch(e) {}
  }
  // Sync côté Alertes : une création/modif de code peut créer, renommer
  // ou supprimer l'alerte auto-liée (via le hook backend _sync_alert_for_code).
  if(typeof loadAlerts === 'function') await loadAlerts();
}
async function deleteMaintCode(code) {
  // v2.7.1 : le serveur tranche entre suppression réelle et archivage selon
  // les saisies rattachées. On ne l'anticipe pas ici (ça ferait un aller-retour
  // de plus pour une information que la réponse porte déjà), mais le message
  // final doit dire ce qui s'est réellement passé : un utilisateur à qui on
  // annonce « supprimé » alors que le code est archivé le recréera.
  const _lbl = (Array.isArray(window._maintItems)
    ? (window._maintItems.find(x => String(x.code) === String(code)) || {}).label
    : '') || '';
  const _ask = (typeof window.maintConfirm === 'function')
    ? window.maintConfirm({
        title: 'Supprimer le code ' + code,
        message: _lbl ? '« ' + _lbl + ' »' : 'Ce code',
        detail: 'S\'il porte déjà des saisies ou des modèles de créneau, il sera '
              + 'archivé plutôt que supprimé : l\'historique doit rester lisible. '
              + 'Sinon, il est supprimé définitivement.',
        confirmLabel: 'Supprimer',
        danger: true,
      })
    : Promise.resolve(confirm('Supprimer le code ' + code + ' ?'));
  if (!(await _ask)) return;
  try {
    const res = await api('/api/maintenance/codes/' + encodeURIComponent(code),
                          { method: 'DELETE' });
    if (res && res.archived) {
      const u = res.usages || {};
      const bouts = [];
      if (u.saisies) bouts.push(u.saisies + ' saisie(s)');
      if (u.modeles) bouts.push(u.modeles + ' modèle(s) de créneau');
      toast('Code ' + code + ' archivé — ' + (bouts.join(' et ') || 'usages existants')
          + '. Il reste lisible dans l\'historique.');
    } else {
      toast('Code supprimé');
    }
  } catch (e) {
    toast(e && e.message ? e.message : 'Erreur lors de la suppression', true);
    return;
  }
  await loadMaintCodes();
  // v2.7.1 : le catalogue vient de changer. Sans cette invalidation, la modal
  // « Enregistrer une opération » continuait de proposer le code supprimé
  // jusqu'au prochain rechargement complet de la page — son cache
  // (MAINT_STATE.codes) n'était jamais purgé.
  if(typeof window.maintOnCatalogueChanged === 'function'){
    try { await window.maintOnCatalogueChanged(); } catch(e) {}
  }
  // La suppression d'un code déclenche la cascade DELETE de l'alerte liée
  // côté backend — on force le rechargement pour que la liste se mette à jour.
  if(typeof loadAlerts === 'function') await loadAlerts();
}


// v2.2.36 : bascule entre les 2 vues du panel Gestion des opérations
function switchMaintView(view) {
  if (view !== 'recurrentes' && view !== 'inhabituelles') view = 'recurrentes';
  const isRec = (view === 'recurrentes');
  const vRec = document.getElementById('maint-view-recurrentes');
  const vInh = document.getElementById('maint-view-inhabituelles');
  const tRec = document.getElementById('maint-tab-recurrentes');
  const tInh = document.getElementById('maint-tab-inhabituelles');
  const btnAdd = document.getElementById('maint-add-btn');
  const btnMerge = document.getElementById('libres-merge-btn');
  const spanCount = document.getElementById('libres-selection-count');
  if (vRec) vRec.style.display = isRec ? '' : 'none';
  if (vInh) vInh.style.display = isRec ? 'none' : '';
  const activeStyle = 'padding:6px 14px;font-size:12px;background:var(--accent);color:var(--accent-fg,#fff);border:none;font-weight:700;border-radius:8px;cursor:pointer;font-family:inherit';
  const inactiveStyle = 'padding:6px 14px;font-size:12px;background:transparent;color:var(--muted);border:1px solid var(--border);font-weight:700;border-radius:8px;cursor:pointer;font-family:inherit';
  if (tRec) tRec.setAttribute('style', isRec ? activeStyle : inactiveStyle);
  if (tInh) tInh.setAttribute('style', isRec ? inactiveStyle : activeStyle);
  if (btnAdd) btnAdd.style.display = isRec ? 'inline-flex' : 'none';
  if (btnMerge) btnMerge.style.display = isRec ? 'none' : '';
  if (spanCount) spanCount.style.display = isRec ? 'none' : '';
  if (!isRec && typeof loadLibres === 'function') loadLibres();
}

</script>

</body>
</html>"""
