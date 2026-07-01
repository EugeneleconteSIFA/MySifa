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
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
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
.filter-input{background:#ffffff;border:1.5px solid var(--border);border-radius:10px;padding:10px 14px;color:#0f172a;font-size:13px;font-family:inherit;outline:none;min-height:40px;box-sizing:border-box;transition:border-color .15s,box-shadow .15s;min-width:168px}
.filter-input::placeholder{color:#64748b}
.filter-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.filters .filter-input[type=date]{min-width:148px;padding:9px 12px;font-size:12px;color:#0f172a}
.filters .filter-input[type=date]::-webkit-calendar-picker-indicator{filter:none;opacity:.6}
select.filter-input{appearance:none;background-color:#ffffff;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px;cursor:pointer;color:#0f172a}
select.filter-input option{background:#ffffff;color:#0f172a}
.filters-apply-btn{background:var(--accent);color:var(--accent-fg,var(--bg));border:none;border-radius:10px;padding:10px 22px;font-size:13px;font-weight:700;min-height:40px;cursor:pointer;font-family:inherit;align-self:flex-end;transition:filter .15s,box-shadow .15s,transform .05s}
.filters-apply-btn:hover{filter:brightness(1.05);box-shadow:0 0 0 4px var(--accent-bg)}
.filters-apply-btn:active{transform:translateY(1px)}
.filters-date-presets{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:10px 0 0;margin-top:12px;border-top:1px dashed var(--border)}
.filters-date-presets-label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-right:4px;padding-top:8px}
.date-preset-chip{padding:5px 12px;font-size:11px;font-weight:600;border-radius:14px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;white-space:nowrap;transition:all 120ms;margin-top:6px}
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

/* ── Vue Semaine (emploi du temps) ──────────────────────────────────── */
.cal-week-view{overflow-x:auto}
.cal-wv-hint{font-size:13px;color:var(--text2);background:var(--accent-bg);border:1px dashed var(--accent);border-radius:8px;padding:10px 14px;margin-bottom:14px;text-align:center;font-weight:600}
.cal-wv-header{display:grid;grid-template-columns:78px repeat(7,minmax(170px,1fr));gap:0;margin-bottom:0;border-bottom:1px solid var(--border);min-width:max-content}
.cal-wv-corner{}
.cal-wv-dayhead{padding:11px 10px;text-align:center;border-left:1px solid var(--border);display:flex;flex-direction:column;align-items:center;gap:3px;background:var(--card)}
.cal-wv-dayhead.weekend{background:rgba(167,139,250,.06)}
.cal-wv-dayhead.today{background:var(--accent-bg)}
.cal-wv-dayname{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace}
.cal-wv-dayhead.weekend .cal-wv-dayname{color:#a78bfa}
.cal-wv-dayhead.today .cal-wv-dayname{color:var(--accent)}
.cal-wv-daydate{font-size:17px;font-weight:800;color:var(--text);font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;letter-spacing:.3px}
.cal-wv-dayhead.today .cal-wv-daydate{color:var(--accent)}
.cal-wv-body{display:grid;grid-template-columns:78px repeat(7,minmax(170px,1fr));gap:0;position:relative;overflow:auto;max-height:75vh;min-width:max-content}
.cal-wv-times-col{display:flex;flex-direction:column}
.cal-wv-time{height:62px;display:flex;align-items:flex-start;justify-content:flex-end;padding:3px 10px 0 0;font-size:12px;font-weight:700;color:var(--muted);font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;border-right:1px solid var(--border);border-top:1px solid var(--border)}
.cal-wv-time:first-child{border-top:none}
.cal-wv-day-col{position:relative;display:flex;flex-direction:column;border-left:1px solid var(--border);min-height:100%}
.cal-wv-day-col.weekend{background:rgba(167,139,250,.04)}
.cal-wv-day-col.today{background:var(--accent-bg)}
.cal-wv-hour-row{height:62px;border-top:1px solid var(--border);transition:background .12s}
.cal-wv-hour-row:first-child{border-top:none}
.cal-wv-day-col.drag-over{background:var(--accent-bg);outline:2px dashed var(--accent);outline-offset:-2px;z-index:1}
.cal-event{position:absolute;background:var(--cal-ev-bg,var(--accent));color:var(--cal-ev-fg,#fff);border-radius:8px;padding:8px 11px;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;font-size:13px;font-weight:600;line-height:1.3;cursor:pointer;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.24);border:1px solid rgba(255,255,255,.20);z-index:2;display:flex;flex-direction:column;gap:4px;transition:filter .12s,box-shadow .12s,transform .08s}
.cal-event:hover{filter:brightness(1.10);box-shadow:0 4px 14px rgba(0,0,0,.36);z-index:4}
.cal-event:active{transform:scale(.99)}
.cal-event-title{font-weight:800;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:.2px;color:inherit}
.cal-event-machine{font-size:12.5px;font-weight:700;opacity:.96;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:inline-flex;align-items:center;gap:4px}
.cal-event-time{font-size:12px;font-weight:700;opacity:.92;font-family:'SFMono-Regular',ui-monospace,Consolas,monospace;letter-spacing:.2px;margin-top:auto}
.cal-event-ops{display:flex;flex-direction:column;gap:2px;flex:1;min-height:0;overflow:hidden}
.cal-event-op{font-size:12.5px;font-weight:600;line-height:1.3;color:inherit;opacity:.96;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:.1px}
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
.cal-week-view.cal-wv-mode-day .cal-wv-body{grid-template-columns:90px 1fr;min-width:0}
/* Modale Créneau : section liste d'opérations */
.case-modal-card{max-width:640px;width:92vw}
.case-ops-section{margin-top:16px;border-top:1px solid var(--border);padding-top:14px}
.case-ops-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.case-ops-add-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;border-radius:8px;border:1.5px solid var(--accent);background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;transition:all .12s;letter-spacing:.2px}
.case-ops-add-btn:hover{background:var(--accent);color:var(--accent-fg,#fff)}
.case-ops-list{display:flex;flex-direction:column;gap:8px;max-height:280px;overflow:auto;padding:2px}
.case-ops-empty{padding:18px 14px;border:1px dashed var(--border);border-radius:8px;color:var(--muted);font-size:12px;text-align:center;font-style:italic;background:var(--bg)}
.case-ops-row{display:flex;align-items:center;gap:8px}
.case-ops-row .ops-select{flex:1;min-width:0}
.case-ops-row-del{flex-shrink:0;width:38px;height:38px;display:inline-flex;align-items:center;justify-content:center;padding:0;border:1px solid var(--border);background:var(--card);border-radius:8px;cursor:pointer;color:var(--muted);transition:all .12s}
.case-ops-row-del:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.10)}
/* Détails créneau */
.plan-det-case-head{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-top:14px}
.plan-det-case-machine{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:8px;background:var(--accent);color:var(--accent-fg,#fff);font-size:13px;font-weight:800;letter-spacing:.2px}
.plan-det-case-time{display:inline-flex;align-items:center;gap:5px;font-family:"SFMono-Regular",ui-monospace,Consolas,monospace;font-weight:700;font-size:13px;color:var(--text)}
.plan-det-case-ops-label{margin-top:14px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:700}
.plan-det-case-ops-list{margin-top:8px;display:flex;flex-direction:column;gap:6px}
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
  .cal-wv-header,.cal-wv-body{grid-template-columns:54px repeat(7,1fr)}
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
.maint-frame-title{font-size:14px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}
.maint-frame-subtitle{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.maint-frame-badges{display:flex;flex-direction:column;align-items:flex-end;gap:5px;flex-shrink:0}
.maint-frame-cat-pill{display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border:1px solid transparent;white-space:nowrap}
.maint-frame-cat-pill.controles{color:var(--ok,#34d399);border-color:rgba(52,211,153,.4);background:rgba(52,211,153,.12)}
.maint-frame-cat-pill.interventions{color:#a78bfa;border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.12)}
body.light .maint-frame-cat-pill.controles{color:var(--ok,#059669);background:rgba(5,150,105,.10)}
body.light .maint-frame-cat-pill.interventions{color:#7c3aed;background:rgba(124,58,237,.10);border-color:rgba(124,58,237,.35)}
.maint-frame-body{flex:1;display:flex;align-items:center;justify-content:center;padding:24px;color:var(--muted);font-size:12px;font-style:italic}
.maint-frames-empty{padding:32px;color:var(--muted);font-size:13px;text-align:center;background:var(--card);border:1px dashed var(--border);border-radius:14px}
.maint-frame-stats{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:18px 20px}
.maint-frame-stat{display:flex;flex-direction:column;gap:4px;min-width:0}
.maint-frame-stat-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.maint-frame-stat-value{font-size:14px;color:var(--text);font-weight:600;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.maint-frame-stat-value.muted{color:var(--muted);font-weight:500;font-style:italic}
.maint-frame-progress{padding:0 20px 12px}
.maint-frame-progress-track{height:14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;overflow:hidden;position:relative}
.maint-frame-progress-fill{height:100%;border-radius:4px;transition:width .35s ease,background-color .15s;background:var(--ok,#34d399)}
.maint-frame-progress-fill.warn{background:var(--warn,#fbbf24)}
.maint-frame-progress-fill.danger{background:var(--danger,#f87171)}
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
.maint-wearparts-stack{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:14px}
.maint-wearpart{min-height:260px}
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
.ops-table-wrap{overflow-x:auto}
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
    <button type="button" class="nav-btn" data-view="planning" onclick="switchView('planning')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Planning
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
        </div>

        <!-- Sélecteur de machine pour la vue Maintenance.
             Détermine quelles cartes "code maintenance périodique" s'affichent
             (Cohésio 1 ou Cohésio 2). Les cartes sont vides pour l'instant et
             seront alimentées par les saisies opérations/contrôles. -->
        <div class="maint-machine-toolbar" style="display:flex;align-items:center;gap:12px;margin:8px 0 18px 0;flex-wrap:wrap">
          <label style="font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px">Machine</label>
          <div class="maint-machine-tabs" id="maint-machine-tabs" role="tablist" style="display:inline-flex;gap:6px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:4px">
            <button type="button" class="maint-machine-btn" data-maint-machine="Cohésio 1" onclick="setMaintMachine('Cohésio 1')">Cohésio 1</button>
            <button type="button" class="maint-machine-btn" data-maint-machine="Cohésio 2" onclick="setMaintMachine('Cohésio 2')">Cohésio 2</button>
          </div>
          <span style="font-size:12px;color:var(--muted)">Gestion des codes : Paramètres → Maintenance</span>
        </div>

        <!-- Cartes des opérations de maintenance périodiques.
             Une carte par code DB avec périodique=OUI, groupées par intervalle
             (Hebdomadaire, Mensuel, Trimestriel...). La grille est régénérée
             automatiquement quand les codes changent dans Paramètres → Maintenance,
             ou quand une nouvelle saisie d'opération / contrôle est enregistrée. -->
        <div id="maint-cards-grid"></div>
      </div>

      <!-- View : Planning -->
      <div class="view" id="view-planning" style="display:none">
        <div class="page-header">
          <div>
            <div class="page-title">Planning</div>
            <div class="page-subtitle">Calendrier de maintenance</div>
          </div>
        </div>

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
          <!-- Vue Mois -->
          <div class="cal-month-view" id="cal-month-view" style="display:none">
            <div class="cal-week-head" id="cal-week-head"></div>
            <div class="cal-grid" id="cal-grid"></div>
          </div>
          <!-- Vue Semaine (emploi du temps) -->
          <div class="cal-week-view cal-wv-mode-week" id="cal-week-view">
            <div class="cal-wv-hint">Cliquez sur une plage horaire libre pour créer un créneau de maintenance.</div>
            <div class="cal-wv-header" id="cal-wv-header"></div>
            <div class="cal-wv-body" id="cal-wv-body"></div>
          </div>
          <div class="cal-legend">
            <span class="cal-legend-item"><span class="cal-legend-dot today"></span> Aujourd'hui</span>
            <span class="cal-legend-item"><span class="cal-legend-dot off"></span> Hors mois</span>
            <span class="cal-legend-item"><span class="cal-legend-dot weekend"></span> Week-end</span>
          </div>
        </section>

        <!-- Liste d'opérations de maintenance (catalogue) — copie synchronisée avec l'onglet Opérations -->
        <!-- Source : table maintenance_codes (Paramètres → Maintenance), filtre periodique=OUI. -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Liste d'opérations de maintenance</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count js-cat-count">0 opération</div>
              <div style="display:flex;align-items:center;gap:6px">
                <label style="font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px">Machine</label>
                <select class="ops-select js-ops-cat-machine" onchange="setOpsCatMachine(this.value)" style="min-width:120px;font-size:13px;padding:6px 10px">
                  <option value="Cohésio 1">Cohésio 1</option>
                  <option value="Cohésio 2">Cohésio 2</option>
                  <option value="DSI">DSI</option>
                  <option value="Repiquage">Repiquage</option>
                </select>
              </div>
              <span class="ops-list-hint" style="font-size:12px;color:var(--muted)">Gestion : Paramètres → Maintenance</span>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort-cat="nom" onclick="sortOpsTypes('nom')">Nom<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="niveau" onclick="sortOpsTypes('niveau')">Niveau<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="categorie" onclick="sortOpsTypes('categorie')">Catégorie<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="intervalle" onclick="sortOpsTypes('intervalle')">Intervalle de temps<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="derniere_intervention" onclick="sortOpsTypes('derniere_intervention')">Dernière intervention<span class="sort-ico">↕</span></th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody class="js-cat-tbody"></tbody>
            </table>
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

        <!-- Sous-onglets style MyProd : Historique / Liste -->
        <div class="ops-subtabs" role="tablist">
          <button type="button" class="ops-subtab active" data-ctrl-subtab="historique" onclick="setCtrlSubtab('historique')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/></svg>
            Historique des contrôles
          </button>
          <button type="button" class="ops-subtab" data-ctrl-subtab="liste" onclick="setCtrlSubtab('liste')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            Liste des contrôles
          </button>
        </div>

        <!-- Sous-onglet : Historique -->
        <div class="ctrl-subview" id="ctrl-subview-historique">

        <!-- Filtres Historique des contrôles -->
        <div class="filters-panel">
          <div class="filters">
            <div class="filter-group">
              <label for="filt-controles-type">Type de contrôle</label>
              <select id="filt-controles-type" class="filter-input" onchange="resetPointFilters(); renderCtrl()">
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
          <div id="ctrl-point-filters-row" class="ctrl-point-filters-row" style="display:none">
            <span class="filters-date-presets-label">Réponses :</span>
            <div id="ctrl-point-filters-inputs" class="ctrl-point-filters-inputs"></div>
            <button type="button" class="date-preset-chip" onclick="resetPointFilters()">Réinitialiser</button>
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

        </div><!-- /ctrl-subview-historique -->

        <!-- Sous-onglet : Liste -->
        <div class="ctrl-subview" id="ctrl-subview-liste" style="display:none">

        <!-- Bandeau d'information : table en lecture seule -->
        <div class="ops-readonly-notice">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          <div>
            Ce tableau est <strong>en lecture seule</strong> et présenté à titre indicatif.
            Pour ajouter, modifier ou supprimer un code maintenance, rendez-vous dans
            <strong>Paramètres → Maintenance</strong>.
          </div>
        </div>

        <!-- Liste de contrôles (catalogue) -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Liste de contrôles</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count" id="ctrl-cat-count">0 contrôle</div>
              <div style="display:flex;align-items:center;gap:6px">
                <label style="font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px">Machine</label>
                <select class="ops-select js-ctrl-cat-machine" onchange="setCtrlCatMachine(this.value)" style="min-width:120px;font-size:13px;padding:6px 10px">
                  <option value="Cohésio 1">Cohésio 1</option>
                  <option value="Cohésio 2">Cohésio 2</option>
                  <option value="DSI">DSI</option>
                  <option value="Repiquage">Repiquage</option>
                </select>
              </div>
              <span class="ops-list-hint" style="font-size:12px;color:var(--muted)">Gestion : Paramètres → Maintenance</span>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort-ctrl-cat="nom" onclick="sortCtrlTypes('nom')">Nom<span class="sort-ico">↕</span></th>
                  <th data-sort-ctrl-cat="derniere_intervention" onclick="sortCtrlTypes('derniere_intervention')">Dernière intervention<span class="sort-ico">↕</span></th>
                  <th>Détail</th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="ctrl-cat-tbody"></tbody>
            </table>
          </div>
        </div>

        </div><!-- /ctrl-subview-liste -->
      </div>

      <!-- View : Opérations de maintenance -->
      <div class="view" id="view-operations" style="display:none">
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
            Liste des opérations
          </button>
        </div>

        <!-- Sous-onglet : Historique -->
        <div class="ops-subview" id="ops-subview-historique">

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
                Nouvelle saisie
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

        </div><!-- /ops-subview-historique -->

        <!-- Sous-onglet : Liste -->
        <div class="ops-subview" id="ops-subview-liste" style="display:none">

        <!-- Bandeau d'information : table en lecture seule -->
        <div class="ops-readonly-notice">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          <div>
            Ce tableau est <strong>en lecture seule</strong> et présenté à titre indicatif.
            Pour ajouter, modifier ou supprimer un code maintenance, rendez-vous dans
            <strong>Paramètres → Maintenance</strong>.
          </div>
        </div>

        <!-- Liste d'opérations de maintenance (catalogue) -->
        <!-- Source : table maintenance_codes (Paramètres → Maintenance), filtre periodique=OUI. -->
        <div class="ops-list">
          <div class="ops-list-head">
            <div class="ops-list-title">Liste d'opérations de maintenance</div>
            <div class="ops-list-head-right">
              <div class="ops-list-count js-cat-count" id="cat-count">0 opération</div>
              <div style="display:flex;align-items:center;gap:6px">
                <label style="font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px">Machine</label>
                <select class="ops-select js-ops-cat-machine" onchange="setOpsCatMachine(this.value)" style="min-width:120px;font-size:13px;padding:6px 10px">
                  <option value="Cohésio 1">Cohésio 1</option>
                  <option value="Cohésio 2">Cohésio 2</option>
                  <option value="DSI">DSI</option>
                  <option value="Repiquage">Repiquage</option>
                </select>
              </div>
              <span class="ops-list-hint" style="font-size:12px;color:var(--muted)">Gestion : Paramètres → Maintenance</span>
            </div>
          </div>
          <div class="ops-table-wrap">
            <table class="ops-table">
              <thead>
                <tr>
                  <th data-sort-cat="nom" onclick="sortOpsTypes('nom')">Nom<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="niveau" onclick="sortOpsTypes('niveau')">Niveau<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="categorie" onclick="sortOpsTypes('categorie')">Catégorie<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="intervalle" onclick="sortOpsTypes('intervalle')">Intervalle de temps<span class="sort-ico">↕</span></th>
                  <th data-sort-cat="derniere_intervention" onclick="sortOpsTypes('derniere_intervention')">Dernière intervention<span class="sort-ico">↕</span></th>
                  <th aria-label="Actions"></th>
                </tr>
              </thead>
              <tbody id="cat-tbody" class="js-cat-tbody"></tbody>
            </table>
          </div>
        </div>

        </div><!-- /ops-subview-liste -->
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
      <div class="ops-saisi-par">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span>Date : <strong id="plan-det-date">—</strong></span>
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
        <div class="ops-saisi-par">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span>Date : <strong id="case-mod-date">—</strong></span>
        </div>
        <div class="ops-form-grid">
          <div class="ops-field ops-field--full">
            <label class="ops-field-label" for="case-mod-machine">Machine<span class="req">*</span></label>
            <select id="case-mod-machine" class="ops-select" required>
              <option value="">Sélectionner une machine…</option>
              <option value="Cohésio 1">Cohésio 1</option>
              <option value="Cohésio 2">Cohésio 2</option>
              <option value="DSI">DSI</option>
              <option value="Repiquage">Repiquage</option>
            </select>
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="case-mod-start">Heure de début<span class="req">*</span></label>
            <input type="time" id="case-mod-start" class="ops-input" required>
          </div>
          <div class="ops-field">
            <label class="ops-field-label" for="case-mod-end">Heure de fin<span class="req">*</span></label>
            <input type="time" id="case-mod-end" class="ops-input" required>
          </div>
        </div>
        <div class="case-ops-section">
          <div class="case-ops-head">
            <label class="ops-field-label">Opérations à effectuer<span class="req">*</span></label>
            <button type="button" class="case-ops-add-btn" onclick="addCaseOp()">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Ajouter une opération
            </button>
          </div>
          <div class="case-ops-list" id="case-mod-ops-list"></div>
        </div>
      </div>
      <div class="modal-foot">
        <button type="button" class="modal-btn-ghost" onclick="closeCaseModal()">Annuler</button>
        <button type="submit" class="ops-btn-add">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          <span id="case-mod-submit-label">Créer</span>
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
  planning:    { title: 'Planning',    sub: 'Calendrier de maintenance' },
  controles:   { title: 'Contrôles',   sub: 'Saisie et suivi des contrôles' },
  operations:  { title: 'Opérations de maintenance', sub: 'Saisie et suivi' }
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
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  const target = document.getElementById('view-' + name);
  if(target) target.style.display = 'flex';
  document.querySelectorAll('.nav-btn[data-view]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === name);
  });
  if(name === 'planning'){
    // Toujours afficher la vue Semaine en arrivant dans Planning
    if(typeof setCalView === 'function') setCalView('week');
    else renderCal();
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
    if(typeof WEARPART_LAST_DATES_STATE === 'object' && WEARPART_LAST_DATES_STATE){
      WEARPART_LAST_DATES_STATE.machine = null;
    }
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
const CAL_HOUR_START = 6;
const CAL_HOUR_END   = 21;   // exclusif (affiche 6h → 20h)
const CAL_HOUR_PX    = 62;
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
const PLANNING_STORAGE_KEY = 'mysifa_maint_planning_v1';
const PLANNING_STATE = { list: [] };
function loadPlanning(){
  try{
    const raw = localStorage.getItem(PLANNING_STORAGE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    PLANNING_STATE.list = (Array.isArray(arr) ? arr : []).map(ev => {
      if(ev && ev.operations && Array.isArray(ev.operations)) return ev;
      // Migration : ancien format single-op (opTypeId/opName/...) → nouveau format multi-op
      const op = {
        opTypeId: (ev && ev.opTypeId) || '',
        opName:   (ev && ev.opName)   || '',
        opNiveau: (ev && ev.opNiveau) || null,
        opFreq:   (ev && ev.opFreq)   || '',
      };
      return {
        id: ev.id || (Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8)),
        machine: ev.machine || '',
        date: ev.date,
        start: ev.start,
        end: ev.end,
        operations: op.opTypeId ? [op] : [],
        created_at: ev.created_at || new Date().toISOString(),
      };
    });
  }catch(e){ PLANNING_STATE.list = []; }
}
function savePlanning(){
  try{ localStorage.setItem(PLANNING_STORAGE_KEY, JSON.stringify(PLANNING_STATE.list)); }catch(e){}
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
  renderCal();
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
  renderCal();
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
  renderCal();
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
  renderCal();
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
  openCaseModal({ iso: iso, defaultHour: 8 });
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
    html += '<div class="' + colCls + '" data-date="' + iso + '" onclick="onCalCellClick(event)">';
    for(let h=CAL_HOUR_START; h<CAL_HOUR_END; h++){
      html += '<div class="cal-wv-hour-row" data-hour="' + h + '"></div>';
    }
    html += '</div>';
  }
  body.innerHTML = html;
  // Lane-packing : un bloc par opération, placé côte à côte lorsqu'il y a chevauchement
  document.querySelectorAll('.cal-wv-day-col').forEach(col => {
    const iso = col.getAttribute('data-date');
    const events = PLANNING_STATE.list.filter(ev => ev.date === iso);
    const packed = _packDayEvents(events);
    packed.forEach(item => {
      const block = _makeEventBlock(item);
      if(block) col.appendChild(block);
    });
  });
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
  html += '<div class="' + colCls + '" data-date="' + iso + '" onclick="onCalCellClick(event)">';
  for(let h=CAL_HOUR_START; h<CAL_HOUR_END; h++){
    html += '<div class="cal-wv-hour-row" data-hour="' + h + '"></div>';
  }
  html += '</div>';
  body.innerHTML = html;
  // Lane-packing
  document.querySelectorAll('.cal-wv-day-col').forEach(col => {
    const cIso = col.getAttribute('data-date');
    const events = PLANNING_STATE.list.filter(ev => ev.date === cIso);
    const packed = _packDayEvents(events);
    packed.forEach(item => {
      const block = _makeEventBlock(item);
      if(block) col.appendChild(block);
    });
  });
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
function _makeEventBlock(item){
  const ev = item.ev;
  const startMin = item.s, endMin = item.e;
  if(startMin == null || endMin == null || endMin <= startMin) return null;
  const top = ((startMin - CAL_HOUR_START*60) / 60) * CAL_HOUR_PX;
  const height = Math.max(22, ((endMin - startMin) / 60) * CAL_HOUR_PX - 2);
  const lanesCount = item.lanesCount || 1;
  const lane = item.lane || 0;
  const div = document.createElement('div');
  div.className = 'cal-event';
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
  const ops = Array.isArray(ev.operations) ? ev.operations.filter(o => o && (o.opName || o.opTypeId)) : [];
  const opsCount = ops.length;
  // Lignes affichables selon hauteur disponible
  const showTitle   = height >= 26;
  const showOpsList = height >= 64 && opsCount > 0;
  const showTime    = height >= 80;
  let inner = '';
  if(showTitle){
    const sub = (opsCount > 0) ? ' · ' + opsCount + ' op.' : '';
    inner += '<div class="cal-event-title">' + escHtml(ev.machine || '—') + sub + '</div>';
  }
  if(showOpsList){
    // Lignes disponibles ≈ (height - 24px titre - 12px time) / 14px
    const lineH = 17;
    const reservedTitle = 28;
    const reservedTime = showTime ? 18 : 0;
    const available = Math.max(1, Math.floor((height - reservedTitle - reservedTime - 6) / lineH));
    const visible = ops.slice(0, available);
    inner += '<div class="cal-event-ops">';
    visible.forEach(op => {
      inner += '<div class="cal-event-op">• ' + escHtml(op.opName || '—') + '</div>';
    });
    if(opsCount > visible.length){
      inner += '<div class="cal-event-op cal-event-op-more">+ ' + (opsCount - visible.length) + ' autre' + ((opsCount - visible.length) > 1 ? 's' : '') + '</div>';
    }
    inner += '</div>';
  } else if(opsCount > 0 && height >= 32 && !showOpsList){
    // Trop court pour une liste : afficher la 1re op + "(+N)"
    const first = ops[0];
    const extra = opsCount > 1 ? ' (+' + (opsCount-1) + ')' : '';
    inner += '<div class="cal-event-machine">' + escHtml(first.opName || '') + extra + '</div>';
  }
  if(showTime){
    inner += '<div class="cal-event-time">' + escHtml(ev.start) + ' – ' + escHtml(ev.end) + '</div>';
  }
  div.innerHTML = inner;
  div.title = (ev.machine || '') + '\n' + ev.start + ' – ' + ev.end +
    (ops.length ? '\n\n' + ops.map(o => '• ' + (o.opName||'—')).join('\n') : '') +
    '\n\nCliquer pour afficher les détails';
  div.addEventListener('click', e => {
    e.stopPropagation();
    openPlanningDetailsModal([ev]);
  });
  return div;
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
  div.className = 'cal-event' + (single ? '' : ' cal-event-merged');
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
function deletePlanningEvent(id){
  PLANNING_STATE.list = PLANNING_STATE.list.filter(e => e.id !== id);
  savePlanning();
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
  if(listEl){
    const ops = Array.isArray(ev.operations) ? ev.operations : [];
    const opsHtml = ops.length
      ? ops.map(op =>
          '<div class="plan-det-case-op">' +
            '<span class="plan-det-case-op-bullet"></span>' +
            '<span class="plan-det-case-op-name">' + escHtml(op.opName || '—') + '</span>' +
            (op.opNiveau ? '<span class="niv-badge" data-niv="' + escAttr(String(op.opNiveau)) + '">N' + escHtml(String(op.opNiveau)) + '</span>' : '') +
            (op.opFreq ? '<span class="plan-det-case-op-freq">Fréquence : ' + escHtml(op.opFreq) + '</span>' : '') +
          '</div>'
        ).join('')
      : '<div class="plan-det-case-op-empty">Aucune opération définie.</div>';
    listEl.innerHTML =
      '<div class="plan-det-case-head">' +
        '<div class="plan-det-case-machine">' +
          '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' +
          escHtml(ev.machine || '—') +
        '</div>' +
        '<div class="plan-det-case-time">' +
          '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          escHtml(ev.start) + ' – ' + escHtml(ev.end) +
        '</div>' +
      '</div>' +
      '<div class="plan-det-case-ops-label">Opérations à effectuer (' + ops.length + ')</div>' +
      '<div class="plan-det-case-ops-list">' + opsHtml + '</div>' +
      '<div class="plan-det-case-actions">' +
        '<button type="button" class="case-action-btn edit" onclick="editCase(\'' + escAttr(ev.id) + '\')">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
          ' Modifier' +
        '</button>' +
        '<button type="button" class="case-action-btn del" onclick="confirmDeleteCase(\'' + escAttr(ev.id) + '\')">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          ' Supprimer' +
        '</button>' +
      '</div>';
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
function deletePlanningEvent(id){
  PLANNING_STATE.list = PLANNING_STATE.list.filter(e => e.id !== id);
  savePlanning();
  renderCal();
}
function confirmDeleteCase(id){
  const ev = PLANNING_STATE.list.find(e => e.id === id);
  if(!ev) return;
  const opsTxt = (ev.operations || []).map(o => '• ' + (o.opName||'—')).join('\n');
  if(!confirm('Supprimer ce créneau ?\n\n' + (ev.machine || '') + ' · ' + ev.date + '\n' + ev.start + ' – ' + ev.end + (opsTxt ? '\n\n' + opsTxt : ''))) return;
  PLANNING_STATE.list = PLANNING_STATE.list.filter(e => e.id !== id);
  savePlanning();
  closePlanningDetailsModal();
  renderCal();
  showToast('Créneau supprimé.', 'info');
}
function editCase(id){
  const ev = PLANNING_STATE.list.find(e => e.id === id);
  if(!ev) return;
  closePlanningDetailsModal();
  openCaseModal({
    editId: ev.id,
    iso: ev.date,
    machine: ev.machine || '',
    start: ev.start,
    end: ev.end,
    operations: ev.operations || [],
  });
}

// ── Clic sur calendrier → ouverture modale "Nouveau créneau" ──────────
function onCalCellClick(e){
  // Ignore clicks on existing events (their own click handler ouvre les détails)
  if(e.target.closest('.cal-event')) return;
  const col = e.currentTarget;
  if(!col) return;
  const iso = col.getAttribute('data-date');
  if(!iso) return;
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
let _CASE_OPS = [];
function openCaseModal(opts){
  opts = opts || {};
  if(!opts.iso){ showToast('Date manquante.', 'danger'); return; }
  _PENDING_CASE = { editId: opts.editId || null, iso: opts.iso };
  _CASE_OPS = (opts.operations || []).map(o => ({
    opTypeId: o.opTypeId || '',
    opName:   o.opName   || '',
    opNiveau: o.opNiveau || null,
    opFreq:   o.opFreq   || '',
  }));
  const m = document.getElementById('planning-case-modal');
  if(!m) return;
  const dtEl = document.getElementById('case-mod-date');
  const mEl  = document.getElementById('case-mod-machine');
  const sEl  = document.getElementById('case-mod-start');
  const eEl  = document.getElementById('case-mod-end');
  const ttlEl = document.getElementById('case-mod-title');
  const lblEl = document.getElementById('case-mod-submit-label');
  const isEdit = !!opts.editId;
  if(ttlEl) ttlEl.textContent = isEdit ? 'Modifier le créneau' : 'Nouveau créneau de maintenance';
  if(lblEl) lblEl.textContent = isEdit ? 'Enregistrer' : 'Créer';
  if(dtEl) dtEl.textContent = _fmtIsoDateFr(opts.iso);
  if(mEl) mEl.value = opts.machine || '';
  const h = Math.max(0, Math.min(23, opts.defaultHour || 8));
  if(sEl) sEl.value = opts.start || (String(h).padStart(2,'0') + ':00');
  if(eEl) eEl.value = opts.end   || (String(Math.min(h+1, 23)).padStart(2,'0') + ':00');
  renderCaseOpsList();
  m.classList.add('open');
  m.setAttribute('aria-hidden','false');
  document.body.style.overflow = 'hidden';
  setTimeout(() => { (mEl && !mEl.value ? mEl : sEl)?.focus(); }, 60);
}
function closeCaseModal(){
  const m = document.getElementById('planning-case-modal');
  if(m){ m.classList.remove('open'); m.setAttribute('aria-hidden','true'); }
  document.body.style.overflow = '';
  _PENDING_CASE = null;
  _CASE_OPS = [];
}
function addCaseOp(){
  if(!OPS_TYPES_STATE.list.length){
    showToast('Aucune opération dans la liste. Ajoutez-en d\'abord dans "Liste d\'opérations de maintenance".', 'danger');
    return;
  }
  _CASE_OPS.push({ opTypeId: '', opName: '', opNiveau: null, opFreq: '' });
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
  const op = OPS_TYPES_STATE.list.find(t => t.id === opTypeId);
  if(op){
    _CASE_OPS[idx] = { opTypeId: op.id, opName: op.nom, opNiveau: op.niveau || null, opFreq: op.frequence || '' };
  } else {
    _CASE_OPS[idx] = { opTypeId: '', opName: '', opNiveau: null, opFreq: '' };
  }
}
function removeCaseOp(idx){
  if(idx < 0 || idx >= _CASE_OPS.length) return;
  _CASE_OPS.splice(idx, 1);
  renderCaseOpsList();
}
function renderCaseOpsList(){
  const list = document.getElementById('case-mod-ops-list');
  if(!list) return;
  if(!_CASE_OPS.length){
    list.innerHTML = '<div class="case-ops-empty">Aucune opération ajoutée. Cliquez sur « Ajouter une opération » pour piocher dans la liste.</div>';
    return;
  }
  list.innerHTML = _CASE_OPS.map((op, idx) => {
    const options = '<option value="">Sélectionner une opération…</option>' +
      OPS_TYPES_STATE.list.map(t =>
        '<option value="' + escAttr(t.id) + '"' + (t.id === op.opTypeId ? ' selected' : '') + '>' +
          escHtml(t.nom) + (t.niveau ? ' (N' + t.niveau + ')' : '') +
          (t.frequence ? ' · ' + escHtml(t.frequence) : '') +
        '</option>'
      ).join('');
    return '<div class="case-ops-row" data-idx="' + idx + '">' +
      '<select class="ops-select" onchange="updateCaseOp(' + idx + ', this.value)">' + options + '</select>' +
      '<button type="button" class="case-ops-row-del" onclick="removeCaseOp(' + idx + ')" title="Retirer cette opération" aria-label="Retirer">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
      '</button>' +
    '</div>';
  }).join('');
}
function submitCaseModal(e){
  e.preventDefault();
  if(!_PENDING_CASE){ closeCaseModal(); return; }
  const machine = (document.getElementById('case-mod-machine')?.value || '').trim();
  const start = (document.getElementById('case-mod-start')?.value || '').trim();
  const end = (document.getElementById('case-mod-end')?.value || '').trim();
  if(!machine){ showToast('Sélectionnez une machine.', 'danger'); return; }
  if(!start || !end){ showToast('Indiquez les heures.', 'danger'); return; }
  const sm = _hmToMins(start), em = _hmToMins(end);
  if(sm == null || em == null){ showToast('Format heure invalide (HH:MM).', 'danger'); return; }
  if(em <= sm){ showToast('L\'heure de fin doit être après l\'heure de début.', 'danger'); return; }
  const validOps = _CASE_OPS.filter(o => o.opTypeId);
  if(!validOps.length){ showToast('Ajoutez au moins une opération.', 'danger'); return; }
  // Synchroniser les noms/niveaux/fréquences depuis le catalogue courant
  const synced = validOps.map(o => {
    const t = OPS_TYPES_STATE.list.find(x => x.id === o.opTypeId);
    if(!t) return o;
    return { opTypeId: t.id, opName: t.nom, opNiveau: t.niveau || null, opFreq: t.frequence || '' };
  });
  const editId = _PENDING_CASE.editId;
  if(editId){
    const idx = PLANNING_STATE.list.findIndex(x => x.id === editId);
    if(idx === -1){ showToast('Créneau introuvable.', 'danger'); closeCaseModal(); return; }
    PLANNING_STATE.list[idx] = Object.assign({}, PLANNING_STATE.list[idx], {
      machine, start, end,
      operations: synced,
      updated_at: new Date().toISOString(),
    });
    showToast('Créneau mis à jour.', 'info');
  } else {
    PLANNING_STATE.list.push({
      id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8),
      machine,
      date: _PENDING_CASE.iso,
      start, end,
      operations: synced,
      created_at: new Date().toISOString(),
    });
    showToast('Créneau créé.', 'info');
  }
  savePlanning();
  closeCaseModal();
  renderCal();
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
  // Pré-remplit machine / type / commentaire en mode édition
  const machineEl = document.getElementById('ops-machine');
  const typeEl = document.getElementById('ops-type');
  const commentEl = document.getElementById('ops-comment');
  if(editing){
    if(machineEl) machineEl.value = editing.machine || '';
    if(typeEl) typeEl.value = editing.type || '';
    if(commentEl) commentEl.value = editing.commentaire || '';
  } else {
    if(machineEl) machineEl.value = '';
    if(typeEl) typeEl.value = '';
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
    OPS_STATE.list[idx] = Object.assign({}, original, {
      machine, type, commentaire,
      date_saisie: dateSaisie,
      date_modification: new Date().toISOString(),
      modifie_par: operateur,
    });
  } else {
    OPS_STATE.list.push({
      id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,8),
      machine, operateur, type, commentaire,
      date_saisie: dateSaisie
    });
  }
  saveOps();
  renderOps();
  // Aligne le sélecteur du catalogue sur la machine de la saisie et re-render
  // pour que la "Dernière intervention" reflète immédiatement la modification.
  try{ localStorage.setItem(OPS_CAT_MACHINE_KEY, machine); }catch(e){}
  // Aligne aussi la vue Maintenance (cartes) sur la machine de la saisie.
  try{ localStorage.setItem(MAINT_MACHINE_KEY, machine); }catch(e){}
  if(typeof renderOpsTypes === 'function') renderOpsTypes();
  if(typeof renderMaintCards === 'function') renderMaintCards();
  closeOpsModal();
  showToast(isEdit ? 'Opération mise à jour.' : 'Opération enregistrée.', 'info');
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
      : 'Aucune opération enregistrée. Cliquez sur « Nouvelle saisie » pour commencer.';
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
          '<button type="button" class="ops-row-btn edit" onclick="openOpsModal(\'' + escAttr(o.id) + '\')" title="Modifier">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
          '</button>' +
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
  let latest = null;
  for(const it of sourceList){
    if(it && it.type === label && it.machine === machine){
      const d = it.date_saisie;
      if(d && (!latest || d > latest)) latest = d;
    }
  }
  return latest;
}

// Variante pour le catalogue "Liste de contrôles" : un contrôle peut être
// rempli soit manuellement (CTRL_STATE.list, matché par label === type), soit
// via une alerte opérateur (CTRL_STATE.acks, matché par code === _maint_code).
function _lastInterventionForCtrl(code, label, machine, manualList, ackList){
  if(!machine) return null;
  let latest = null;
  if(Array.isArray(manualList)){
    for(const it of manualList){
      if(it && it.type === label && it.machine === machine){
        const d = it.date_saisie;
        if(d && (!latest || d > latest)) latest = d;
      }
    }
  }
  if(Array.isArray(ackList) && code){
    for(const it of ackList){
      if(it && it._maint_code === code && it.machine === machine){
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
    // 'suivi' (catégorie supprimée côté UI) est remappée en 'interventions'
    // pour les codes legacy qui n'ont pas encore été corrigés en base.
    const normCat = (c) => (c === 'interventions' || c === 'suivi') ? 'interventions' : 'controles';
    // Liste d'opérations : Interventions (toutes) + Contrôles avec periodique=OUI.
    OPS_TYPES_STATE.list = items
      .filter(it => {
        const cn = normCat(it.categorie);
        return (cn === 'interventions') || (cn === 'controles' && !!it.periodique);
      })
      .map(it => ({
        id: it.code,
        nom: it.label,
        niveau: parseInt(it.niveau, 10) || 1,
        categorie: normCat(it.categorie),
        periodique: !!it.periodique,
        intervalle: (it.intervalle || '').toString(),
        metrage_ref: (it.metrage_ref || '').toString(),
        frequence: (it.intervalle || '').toString(),  // alias compat _parseFrequenceDays
        detail: '',
        _readonly: true,
      }));
  }catch(e){
    OPS_TYPES_STATE.list = [];
  }
}

// Couleur d'un anneau (ou d'une barre de progression) sur l'intervalle [0,200%].
// Dégradé multi-stops : vert -> jaune -> orange -> rouge.
// Au-delà de 200% : rouge plein (clamp).
function _ratioColor(ratio){
  // Stops fixés à t = 0 / 0.33 / 0.66 / 1, où t = ratio / 2 (clampé).
  const stops = [
    [0.00, [ 52, 211, 153]],   // vert    #34d399
    [0.33, [250, 204,  21]],   // jaune   #facc15
    [0.66, [251, 146,  60]],   // orange  #fb923c
    [1.00, [220,  38,  38]],   // rouge   #dc2626
  ];
  const t = Math.max(0, Math.min(1, (ratio || 0) / 2));
  for(let i = 0; i < stops.length - 1; i++){
    const [ta, ca] = stops[i];
    const [tb, cb] = stops[i + 1];
    if(t <= tb){
      const lt = (tb === ta) ? 0 : (t - ta) / (tb - ta);
      const r = Math.round(ca[0] + (cb[0] - ca[0]) * lt);
      const g = Math.round(ca[1] + (cb[1] - ca[1]) * lt);
      const b = Math.round(ca[2] + (cb[2] - ca[2]) * lt);
      return 'rgb(' + r + ',' + g + ',' + b + ')';
    }
  }
  const last = stops[stops.length - 1][1];
  return 'rgb(' + last[0] + ',' + last[1] + ',' + last[2] + ')';
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
    // >= 100% : tour de base + court segment de stroke à la position
    // d'avancement (longueur ~ stroke-width) avec stroke-linecap="round"
    // pour la tête arrondie style natif, et drop-shadow pour l'effet 3D.
    // Le départ à 12h n'est pas tracé (gap dans le dasharray) → pas de
    // cap visible au sommet.
    // Overflow plafonné à 0.97 pour garder le tip distinct du sommet si > 200%.
    const overflow = Math.min(0.97, ratio - 1);
    const baseLap = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="' + sw +
      '" style="transition:stroke .15s"/>';
    // Triple drop-shadow pour l'effet 3D : ombre dure proche, moyenne diffuse,
    // douce large.
    const shadowFilter = 'filter:'
      + 'drop-shadow(0 1px 1px rgba(0,0,0,.55)) '
      + 'drop-shadow(2px 4px 5px rgba(0,0,0,.45)) '
      + 'drop-shadow(0 0 8px rgba(0,0,0,.25))';
    const tipPos      = overflow * circ;
    const tipDashLen  = sw * 0.6;
    const dashStart   = tipPos - tipDashLen;
    const tip = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r +
      '" fill="none" stroke="' + color + '" stroke-width="' + sw +
      '" stroke-linecap="round" stroke-dasharray="' + tipDashLen.toFixed(2) + ' ' + (circ - tipDashLen).toFixed(2) +
      '" stroke-dashoffset="' + (-dashStart).toFixed(2) +
      '" transform="rotate(-90 ' + cx + ' ' + cy + ')" style="' + shadowFilter +
      ';transition:stroke-dashoffset .35s ease,stroke .15s"/>';
    return trackBg + baseLap + tip;
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

// Trouve le code Intervention correspondant à une pièce d'usure (par pattern
// sur le libellé). pieceId = 'couteaux' | 'contre_couteaux' ; pos = 'bande' | 'rive'.
// Cherche dans OPS_TYPES_STATE.list (qui contient toutes les Interventions).
// Normalise vers { label, intervalle, metrage_ref } pour rester compatible
// avec l'ancien retour de _findSuiviCodeForWearPart.
function _findWearPartCode(pieceId, pos){
  const list = OPS_TYPES_STATE.list || [];
  for(const t of list){
    if(t.categorie !== 'interventions') continue;
    const lbl = (t.nom || '').toLowerCase();
    if(!lbl.includes(pos)) continue;
    const hasContre = (lbl.indexOf('contre') !== -1);
    const isMatch = (pieceId === 'contre_couteaux')
      ? (hasContre && lbl.indexOf('couteaux') !== -1)
      : (!hasContre && lbl.indexOf('couteaux') !== -1);
    if(isMatch){
      return {
        code: t.id,
        label: t.nom,
        intervalle: t.intervalle || '',
        metrage_ref: t.metrage_ref || '',
      };
    }
  }
  return null;
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
  const catLabel = (t.categorie === 'interventions') ? 'Interventions' : 'Contrôles';
  const intervalleTxt = t.periodique
    ? (t.intervalle || 'À compléter (Paramètres → Maintenance)')
    : '— (non périodique)';
  const _kv = (lbl, val) =>
    '<div><div style="font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">' + lbl + '</div>' +
    '<div style="color:var(--text);font-weight:500">' + val + '</div></div>';
  infoEl.innerHTML = ''
    + _kv('Code', escHtml(String(t.id)))
    + _kv('Catégorie', '<span class="op-pill ' + ((t.categorie === 'interventions') ? 'interventions' : 'controles') + '">' + escHtml(catLabel) + '</span>')
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

function getMaintMachine(){
  try{ return localStorage.getItem(MAINT_MACHINE_KEY) || 'Cohésio 1'; }
  catch(e){ return 'Cohésio 1'; }
}
function setMaintMachine(m){
  if(!m) return;
  try{ localStorage.setItem(MAINT_MACHINE_KEY, m); }catch(e){}
  // Invalide le cache des dates wearparts : nouvelle machine = nouveau fetch
  WEARPART_LAST_DATES_STATE.machine = null;
  WEARPART_LAST_DATES_STATE.items = {};
  WEARPART_LAST_DATES_STATE._cacheKey = null;
  renderMaintCards();
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
};

async function loadWearPartLastDates(machine){
  if(!machine) return;
  // Récupère les dates des dernières saisies maintenance dans OPS_STATE (source
  // locale, navigateur) pour chaque combinaison pièce x position. Envoie ces
  // dates au backend qui retourne le métrage machine à chaque date.
  if(typeof loadOps === 'function') loadOps();
  const pieceIds = ['couteaux','contre_couteaux'];
  const positions = ['bande','rive'];
  const dates = {};
  pieceIds.forEach(pid => {
    positions.forEach(pos => {
      const k = pid + '_' + pos;
      const c = _findWearPartCode(pid, pos);
      dates[k] = c ? _lastInterventionFor(c.label, machine, OPS_STATE.list) : null;
    });
  });
  // Clé de cache : machine + dates concaténées. Si rien n'a changé → skip fetch.
  const cacheKey = machine + ':' + JSON.stringify(dates);
  if(WEARPART_LAST_DATES_STATE._cacheKey === cacheKey && !WEARPART_LAST_DATES_STATE.loading) return;
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
const WEARPART_PIECES = [
  { id: 'couteaux',         label: 'Couteaux' },
  { id: 'contre_couteaux',  label: 'Contre-couteaux' },
];

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
  const m = _loadWearPartMap();
  return (m[pieceId] && m[pieceId][machine]) || 'bande';
}
function setWearPartPos(pieceId, pos){
  if(pos !== 'bande' && pos !== 'rive') return;
  const machine = getMaintMachine();
  const m = _loadWearPartMap();
  if(!m[pieceId]) m[pieceId] = {};
  m[pieceId][machine] = pos;
  _saveWearPartMap(m);
  renderMaintCards();
}
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

function _renderWearPartsGroup(machine){
  // Déclenche le fetch des dernières dates si la machine a changé
  // (asynchrone : le render initial affiche "Chargement…", puis re-render au retour)
  if(WEARPART_LAST_DATES_STATE.machine !== machine){
    loadWearPartLastDates(machine);
  }
  const cards = WEARPART_PIECES.map(p => {
    const pos = getWearPartPos(p.id, machine);
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
      ? _lastInterventionFor(wpCode.label, machine, OPS_STATE.list)
      : null;
    const wpItem = (WEARPART_LAST_DATES_STATE.machine === machine)
      ? _getWearPartItem(p.id, pos)
      : null;
    const metrageSince = wpItem ? wpItem.metrage_since : null;
    const daysSince = _daysSinceFromIso(lastDate);
    // Pour la compat avec le bloc d'affichage plus bas (qui utilise wpItem.last_date)
    if(wpItem){ wpItem.last_date = lastDate; }
    // Mise en exergue : déclenchée par DÉPASSEMENT DE TEMPS ou DÉPASSEMENT DE
    // MÉTRAGE (peu importe lequel) par rapport à la référence. is-overdue dès
    // le dépassement, is-overdue-critical quand on est à >200%.
    const refDays   = _parseFrequenceDays(refTemps);
    const refMetres = _parseMetrageRef(refMetrage);
    const timeOver     = (refDays   != null && refDays   > 0 && daysSince    != null && daysSince    > refDays);
    const timeCritical = (timeOver && daysSince    > refDays   * 2);
    const metresOver     = (refMetres != null && refMetres > 0 && metrageSince != null && metrageSince > refMetres);
    const metresCritical = (metresOver && metrageSince > refMetres * 2);
    let frameClsExtra = '';
    if(timeOver || metresOver){
      frameClsExtra = ' is-overdue';
      if(timeCritical || metresCritical) frameClsExtra += ' is-overdue-critical';
    }
    let elapsedHtml = '';
    if(WEARPART_LAST_DATES_STATE.machine !== machine){
      elapsedHtml = '<span style="font-size:11px;color:var(--muted);font-style:italic">Chargement…</span>';
    } else if(daysSince == null){
      elapsedHtml = '<span style="font-size:11px;color:var(--muted);font-style:italic">Aucun changement enregistré dans MyProd</span>';
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
      return '<button type="button" class="maint-wp-btn' + active + '" data-wp="' + escAttr(p.id) + '" data-pos="' + value + '" onclick="setWearPartPos(\'' + escAttr(p.id) + '\',\'' + value + '\')">' + label + '</button>';
    };
    return '<section class="maint-frame maint-wearpart' + frameClsExtra + '" data-wearpart="' + escAttr(p.id) + '" data-wearpart-pos="' + escAttr(pos) + '" data-maint-machine="' + escAttr(machine) + '">' +
      '<div class="maint-frame-head">' +
        '<div class="maint-frame-title">' + escHtml(p.label) + '</div>' +
        '<div class="maint-wp-tabs" role="tablist" aria-label="Position">' +
          _b('Bande', 'bande') +
          _b('Rive', 'rive') +
        '</div>' +
      '</div>' +
      (function(){
        // Layout :
        //   - Gauche : 2 sections empilées TEMPS (cyan) et MÉTRAGE (ambre),
        //     chacune avec barre verticale colorée à gauche pour identifier
        //     l'anneau correspondant.
        //   - Droite : 2 anneaux concentriques. Extérieur cyan = temps,
        //     intérieur ambre = métrage. Couleurs assorties aux sections.
        const _refVal = (v) => v
          ? '<span class="val">' + escHtml(v) + '</span>'
          : (suiviCode
              ? '<span class="val muted">à compléter</span>'
              : '<span class="val muted">aucun code Suivi</span>'
            );
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
        let metresBadge = '';
        if(metresOver){
          const overM = metrageSince - refMetres;
          metresBadge = '<span class="maint-wp-badge">Retard ' + escHtml(_fmtMetres(overM)) + '</span>';
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
  return '<div class="maint-group">' +
           '<div class="maint-group-head">' +
             '<h3 class="maint-group-title">Pièces d\'usure</h3>' +
             '<span class="maint-group-count">' + WEARPART_PIECES.length + ' pièces</span>' +
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
  // La section "Pièces d'usure" est toujours rendue, indépendamment des codes
  // périodiques configurés en DB.
  const wearPartsHtml = _renderWearPartsGroup(machine);
  // Récupère les IDs des codes utilisés par les cartes Pièces d'usure pour les
  // exclure des sections par intervalle ci-dessous (sinon les changements
  // couteaux/contre-couteaux apparaîtraient deux fois).
  const wearPartCodeIds = new Set();
  ['couteaux','contre_couteaux'].forEach(pid => {
    ['bande','rive'].forEach(pos => {
      const c = _findWearPartCode(pid, pos);
      if(c && c.code) wearPartCodeIds.add(String(c.code));
    });
  });
  // Filtre les codes avec periodique=OUI (toutes catégories confondues),
  // en excluant ceux déjà affichés dans la section Pièces d'usure.
  const baseItems = (OPS_TYPES_STATE.list || []).filter(it =>
    !!it.periodique && !wearPartCodeIds.has(String(it.id))
  );
  if(!baseItems.length){
    grid.innerHTML = wearPartsHtml +
      '<div class="maint-frames-empty" style="margin-top:24px">Aucune opération périodique configurée. Ajoutez des codes avec Périodique=OUI dans Paramètres → Maintenance.</div>';
    return;
  }
  // Pour chaque carte, calcule : freqDays (depuis intervalle), dernière intervention
  // sur la machine sélectionnée, et infos de retard.
  //
  // Source des saisies : TOUJOURS OPS_STATE.
  // Les cartes affichent les codes periodique=OUI (interventions + controles).
  // Le select de la modale Contrôles ne propose que les controles periodique=NON,
  // donc un code controle periodique=OUI ne peut être saisi que via la modale
  // Opérations -> il atterrit dans OPS_STATE. Si on lit CTRL_STATE pour les
  // controles, on rate ces saisies (bug observé : cartes restant à "Jamais"
  // alors que des entrées existent dans l'historique des opérations).
  const enriched = baseItems.map(it => {
    const freqDays = _parseFrequenceDays(it.intervalle);
    const last = _lastInterventionFor(it.nom, machine, OPS_STATE.list);
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
    return { it, freqDays, last, daysSince, daysOverdue, overdue };
  });
  // Calcule le plus grand retard (toutes catégories) pour mettre en exergue
  let maxOverdue = 0;
  enriched.forEach(e => { if(e.daysOverdue && e.daysOverdue > maxOverdue) maxOverdue = e.daysOverdue; });
  // Groupement par intervalle (en jours). Items sans intervalle reconnu -> groupe "null".
  const groups = new Map();  // key = freqDays (number) ou 'unknown'
  enriched.forEach(e => {
    const key = (e.freqDays == null) ? 'unknown' : e.freqDays;
    if(!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  });
  // Tri des groupes : plus petit intervalle en premier, 'unknown' à la fin
  const sortedKeys = Array.from(groups.keys()).sort((a, b) => {
    if(a === 'unknown') return 1;
    if(b === 'unknown') return -1;
    return a - b;
  });
  // Tri à l'intérieur de chaque groupe : retard décroissant, puis alphabétique
  groups.forEach((arr) => {
    arr.sort((a, b) => {
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
  // Construit le HTML : pièces d'usure d'abord, puis sections par intervalle.
  let html = wearPartsHtml;
  sortedKeys.forEach(key => {
    const groupItems = groups.get(key);
    const groupLabel = (key === 'unknown') ? 'Sans intervalle reconnu' : _freqDaysToLabel(key);
    const cards = groupItems.map(({it, freqDays, last, daysSince, daysOverdue, overdue}) => {
      const catLabel = (it.categorie === 'interventions') ? 'Interventions' : 'Contrôles';
      let frameCls = 'maint-frame';
      if(overdue){
        frameCls += ' is-overdue';
        if(maxOverdue > 0 && daysOverdue === maxOverdue) frameCls += ' is-overdue-critical';
      }
      const lastHtml = last
        ? '<span class="maint-frame-stat-value">' + escHtml(_fmtDateTime(last)) + '</span>'
        : '<span class="maint-frame-stat-value muted">Jamais</span>';
      // Statut de retard
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
          badgeLbl = 'OK · J-' + remaining;
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
      // Barre de progression : pourcentage écoulé depuis la dernière intervention
      // sur l'intervalle. Largeur clampée à 100% visuellement. Couleur via
      // _ratioColor (dégradé vert -> jaune -> orange -> rouge sur [0, 200%]),
      // identique au code couleur des anneaux des pièces d'usure.
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
        // Intervalle défini mais jamais saisi : barre vide grisée
        progressHtml =
          '<div class="maint-frame-progress is-empty" title="' + escAttr('Aucune saisie pour cette opération sur cette machine. Intervalle prévu : ' + freqDays + ' jour(s).') + '">' +
            '<div class="maint-frame-progress-track"><div class="maint-frame-progress-fill" style="width:0%"></div></div>' +
            '<div class="maint-frame-progress-label">' +
              '<span>—</span>' +
              '<span class="pct">0 / ' + freqDays + ' j</span>' +
            '</div>' +
          '</div>';
      }
      // Si freqDays est null (intervalle non reconnu), pas de barre.
      const catCls = (it.categorie === 'interventions') ? 'interventions' : 'controles';
      const nivNum = parseInt(it.niveau, 10) || 1;
      return '<section class="' + frameCls + '" data-maint-code="' + escAttr(it.id) + '" data-maint-machine="' + escAttr(machine) + '">' +
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
      const catLabel = (t.categorie === 'interventions') ? 'Interventions' : 'Contrôles';
      const catCls = (t.categorie === 'interventions') ? 'interventions' : 'controles';
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
const CTRL_STATE = { sortBy: 'date_saisie', sortDir: 'desc', list: [], acks: [], alerts_meta: {}, pointFilters: {} };

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
    }));
    CTRL_STATE.alerts_meta = data.alerts_meta || {};
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
  if(!confirm('Supprimer ce contrôle ?')) return;
  CTRL_STATE.list = CTRL_STATE.list.filter(c => c.id !== id);
  saveCtrl();
  renderCtrl();
}

async function deleteAck(prefixedId){
  if(!confirm('Supprimer cette ligne d\'historique ?\n\nElle restera comptée pour le dernier acquittement de l\'alerte associée si c\'est la plus récente.')) return;
  // Format prefixedId : "ack-{numeric_id}"
  const m = String(prefixedId).match(/^ack-(\d+)$/);
  if(!m){ showToast('Identifiant invalide.', 'danger'); return; }
  const ackId = m[1];
  try{
    const r = await fetch('/api/maintenance/alert-acks/' + ackId, {
      method: 'DELETE',
      credentials: 'same-origin',
    });
    if(!r.ok){
      let msg = 'Suppression refusée';
      try { const j = await r.json(); msg = j.detail || msg; } catch(e){}
      showToast(msg, 'danger');
      return;
    }
    showToast('Ligne supprimée.', 'info');
    await loadCtrlAcks();
  } catch(e){
    showToast('Erreur réseau — réessaie.', 'danger');
  }
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
    const setTypes = new Set(
      CTRL_TYPES_STATE.list.map(t => t.nom).filter(Boolean)
    );
    (CTRL_STATE.acks || []).forEach(a => { if(a.type) setTypes.add(a.type); });
    const types = Array.from(setTypes).sort((a,b) => a.localeCompare(b, 'fr'));
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
function _getCurrentTypeChecklistItems(){
  const sel = document.getElementById('filt-controles-type');
  const t = (sel && sel.value || '').trim();
  if(!t) return null;
  // Trouve le premier ack qui matche ce type
  const ackMatch = (CTRL_STATE.acks || []).find(a => a.type === t);
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
            const chips = ['Nette'];  // placeholder, écrasé ci-dessous
            // On n'a pas la liste complète des réponses possibles dans l'ack ;
            // on n'affiche donc que les réponses réellement cochées (comme des
            // pills sélectionnées). C'est fidèle à la donnée enregistrée.
            const respHtml = selected.length
              ? selected.map(s => '<label class="ta-chip"><input type="checkbox" disabled checked><span>' + escHtml(s) + '</span></label>').join('')
              : '<span style="font-size:12px;color:var(--muted);font-style:italic">Aucune réponse cochée</span>';
            return '<div class="ta-cl-item" data-type="choice">'
              + '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">' + escHtml(it.label || '') + '</div>'
              + '<div style="display:flex;flex-wrap:wrap;gap:5px">' + respHtml + '</div>'
              + '</div>';
          }).join('')
      + '</div>';
  }

  // Contexte : date, machine, opérateur
  const dt = fmtDate(ack.date_saisie);
  const contextLine = escHtml(ack.machine || '—') + ' · ' + escHtml(dt) + ' · ' + escHtml(ack.operateur || '—');
  const commentText = ack._raw_comment || '';

  const overlay = document.createElement('div');
  overlay.className = 'ta-sim ta-pl-center ta-blocking';
  overlay.id = 'ack-detail-overlay';
  overlay.innerHTML = '<div class="ta-sim-alert">'
    + '<div class="ta-sim-title">' + escHtml(ack.type || 'Contrôle') + '</div>'
    + '<div class="ta-sim-sub">' + contextLine + '</div>'
    + checklistHtml
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
  const merged = CTRL_STATE.list.concat(CTRL_STATE.acks || []);
  let filtered = merged.filter(c => {
    if(f.type && c.type !== f.type) return false;
    if(f.operateur && c.operateur !== f.operateur) return false;
    if(f.machine && c.machine !== f.machine) return false;
    if(f.dateFrom || f.dateTo){
      const d = (c.date_saisie || '').slice(0,10);
      if(f.dateFrom && d < f.dateFrom) return false;
      if(f.dateTo && d > f.dateTo) return false;
    }
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
    const ackMatch = merged.find(c => c._source === 'alert' && c.type === singleType);
    if(ackMatch && ackMatch._alert_id != null && CTRL_STATE.alerts_meta){
      const meta = CTRL_STATE.alerts_meta[String(ackMatch._alert_id)];
      if(meta && Array.isArray(meta.checklist_items)){
        extraCols = meta.checklist_items;
      }
    }
  }

  // Reconstruire le thead
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
    h += '<th>Commentaires</th>';
    h += '<th aria-label="Actions"></th>';
    thead.innerHTML = h;
  }

  const totalCols = 3 + (singleType ? 0 : 1) + extraCols.length + 2;  // date+machine+operateur (+type?) + extra + commentaires + actions

  if(!filtered.length){
    const isFiltered = f.type || f.operateur || f.machine || f.dateFrom || f.dateTo;
    const msg = isFiltered
      ? 'Aucun contrôle ne correspond aux filtres.'
      : 'Aucun contrôle enregistré. Cliquez sur « Nouveau contrôle » pour commencer.';
    tbody.innerHTML = '<tr><td colspan="' + totalCols + '" class="ops-empty">' + escHtml(msg) + '</td></tr>';
  } else {
    const rows = filtered.map(c => {
      let cells = '';
      cells += '<td class="col-date">' + escHtml(fmtDate(c.date_saisie)) + '</td>';
      cells += '<td>' + escHtml(c.machine) + '</td>';
      cells += '<td>' + escHtml(c.operateur) + '</td>';
      if(!singleType){
        cells += '<td>' + escHtml(c.type) + '</td>';
      }
      for(let i = 0; i < extraCols.length; i++){
        let val = '';
        if(c._source === 'alert' && c._responses){
          const r = c._responses[String(i)];
          if(Array.isArray(r)){ val = r.join(', '); }
          else if(r != null && r !== ''){ val = String(r); }
        }
        cells += '<td>' + escHtml(val) + '</td>';
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
        actionHtml = '<div class="ctrl-actions-stack">' +
          '<span class="ctrl-src-badge" title="Validation issue d\'une alerte opérateur">Alerte</span>' +
          '<button type="button" class="ops-row-btn del" onclick="deleteAck(\'' + escAttr(c.id) + '\')" title="Supprimer cette saisie (correction d\'erreur)">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
          '</button>' +
        '</div>';
      } else {
        actionHtml = '<button type="button" class="ops-row-btn del" onclick="deleteCtrl(\'' + escAttr(c.id) + '\')" title="Supprimer">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>' +
        '</button>';
      }
      cells += '<td class="col-actions">' + actionHtml + '</td>';
      const dblAttr = (c._source === 'alert')
        ? ' ondblclick="openAckDetail(\'' + escAttr(c.id) + '\')" style="cursor:pointer" title="Double-clic pour voir le détail"'
        : '';
      return '<tr' + dblAttr + '>' + cells + '</tr>';
    });
    tbody.innerHTML = rows.join('');
  }
  if(count){
    const n = CTRL_STATE.list.length + (CTRL_STATE.acks || []).length;
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
    tbody.innerHTML = '<tr><td colspan="4" class="ops-empty">Aucun contrôle non périodique. Ajoutez des codes avec catégorie=Contrôles et Périodique=NON dans Paramètres → Maintenance.</td></tr>';
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
      return '<tr>' +
        '<td><strong style="color:var(--text)">' + escHtml(t.nom) + '</strong></td>' +
        '<td><span style="font-size:13px;color:var(--text)">' + escHtml(dtDisplay) + '</span></td>' +
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
  // loadOpsTypes() et loadCtrlTypes() sont async (fetch /api/maintenance/codes).
  loadOpsTypes().then(() => {
    renderOpsTypes();
    if(typeof renderMaintCards === 'function') renderMaintCards();
  }).catch(() => {
    renderOpsTypes();
    if(typeof renderMaintCards === 'function') renderMaintCards();
  });
  loadCtrl();
  loadCtrlAcks();
  loadCtrlTypes().then(() => renderCtrlTypes()).catch(() => renderCtrlTypes());
  loadPlanning();
  renderOps();
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
<script src="/static/mysifa_cmdk.js"></script>
<script>
if(typeof window.MySifaDock !== 'undefined' && typeof window.MySifaDock.bootPageWidgets === 'function'){
  window.MySifaDock.bootPageWidgets();
}
</script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=5"></script>
<script src="/static/chat_widget_v2.js"></script>
<script src="/static/mysifa_alert_runtime.js"></script>
<script src="/static/support_widget.js"></script>
</body>
</html>"""
