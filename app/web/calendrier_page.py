"""MySifa — MyCalendrier."""

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import can_access_calendrier, get_current_user
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/calendrier", response_class=HTMLResponse)
def calendrier_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/calendrier", status_code=302)
        raise
    if not can_access_calendrier(user):
        return access_denied_response(
            "MyCalendrier",
            detail="Vous n'avez pas les droits d'accès à MyCalendrier.",
        )
    role = str(user.get("role") or "")
    html = CALENDRIER_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    html = html.replace("__USER_ROLE__", json.dumps(role))
    return HTMLResponse(content=html)


CALENDRIER_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Calendrier — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);--ok:#34d399;--warn:#fbbf24;--danger:#f87171;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);--ok:#059669;--warn:#d97706;--danger:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:20px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s;margin-bottom:2px}
.nav-btn svg{flex-shrink:0}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.sidebar hr{border:none;border-top:1px solid var(--border);margin:12px 0}
.cal-cals-section{margin-bottom:4px}
.cal-cals-head{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;padding:4px 12px 8px;border:none;background:transparent;cursor:pointer;font-family:inherit;transition:color .15s}
.cal-cals-head:hover .cal-cals-head-label,.cal-cals-head:hover .cal-cals-chevron{color:var(--accent)}
.cal-cals-head-label{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted)}
.cal-cals-chevron{flex-shrink:0;color:var(--muted);transition:transform .15s,color .15s}
.cal-cals-section.collapsed .cal-cals-chevron{transform:rotate(-90deg)}
.cal-cals-section.collapsed #cal-toggles{display:none}
.cal-toggle{display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:12px;color:var(--text2);user-select:none}
.cal-toggle:hover{background:var(--accent-bg)}
.cal-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;background:var(--cal-c)}
.cal-toggle span.flex1{flex:1}
.cal-toggle input{appearance:none;width:16px;height:16px;border:2px solid var(--border);border-radius:4px;background:var(--bg);cursor:pointer;position:relative;flex-shrink:0}
.cal-toggle input:checked{background:var(--cal-c);border-color:var(--cal-c)}
.cal-toggle input:checked::after{content:'';position:absolute;left:4px;top:1px;width:4px;height:8px;border:solid #0a0e17;border-width:0 2px 2px 0;transform:rotate(45deg)}
.cal-gear-btn{
  flex-shrink:0;display:flex;align-items:center;justify-content:center;width:26px;height:26px;
  border:none;border-radius:6px;background:transparent;color:var(--muted);cursor:pointer;padding:0;
  transition:color .15s,background .15s;
}
.cal-gear-btn:hover{color:var(--accent);background:var(--accent-bg)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}
.mobile-topbar{display:none;align-items:center;gap:10px;padding:10px 18px;border-bottom:1px solid var(--border);background:var(--bg);flex-shrink:0}
.mobile-menu-btn,.mobile-home-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;flex-shrink:0}
.mobile-home-btn{margin-left:auto}
.mobile-topbar-title{font-size:14px;font-weight:800}
.mobile-topbar-sub{font-size:11px;color:var(--muted);margin-top:2px}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
.cal-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:10px;padding:16px 20px;border-bottom:1px solid var(--border);background:var(--card);flex-shrink:0}
.cal-nav{display:flex;align-items:center;gap:8px}
.cal-btn{padding:8px 14px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,background .15s}
.cal-btn:hover{border-color:var(--accent);color:var(--accent)}
.cal-btn.primary{background:var(--accent);color:#0a0e17;border-color:var(--accent)}
.cal-title{font-size:16px;font-weight:800;min-width:180px;text-align:center;color:var(--text)}
.cal-view-tabs{display:flex;gap:6px;margin-left:auto}
.cal-body{flex:1;overflow:auto;padding:16px 20px 24px;position:relative}
.cal-loading{font-size:13px;color:var(--muted);padding:20px 0}
/* Month */
:root{--cal-ferie-bg:color-mix(in srgb, var(--danger) 7%, transparent)}
body.light{--cal-ferie-bg:color-mix(in srgb, var(--danger) 9%, transparent)}
.cal-month{display:flex;flex-direction:column;gap:0;min-width:748px}
.cal-month-head{display:grid;grid-template-columns:28px repeat(7,1fr);gap:1px;margin-bottom:4px}
.cal-month-head div{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);text-align:center;padding:6px 4px}
.cal-month-head .cal-week-num-head{background:transparent}
.cal-week-row{display:grid;grid-template-columns:28px 1fr;gap:0;margin-bottom:8px}
.cal-week-num{
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-family:monospace;color:var(--muted);text-align:center;
  background:transparent;user-select:none;padding:4px 2px;
}
.cal-week-inner{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:var(--card)}
.cal-week-bars{position:relative;min-height:0;display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:var(--border)}
.cal-week-bars:empty{display:none}
.cal-mbar{margin:2px 3px 0;padding:2px 8px;font-size:10px;font-weight:700;border-radius:4px;border-width:1px;border-style:solid;color:#0a0e17;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;grid-row:1;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.cal-days{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:var(--border)}
.cal-day{min-height:100px;background:var(--bg);padding:6px;display:flex;flex-direction:column;gap:4px}
.cal-day.other{opacity:.45}
.cal-day.today{box-shadow:inset 0 0 0 2px var(--accent)}
.cal-day--ferie{background:var(--cal-ferie-bg)}
.cal-day-num{font-size:12px;font-weight:700;color:var(--text2);flex-shrink:0}
.cal-day.other .cal-day-num{color:var(--muted)}
.cal-day-events{flex:1;display:flex;flex-direction:column;gap:3px;min-height:0}
.cal-day-ferie-label{
  margin-top:auto;font-size:10px;color:var(--danger);opacity:.7;line-height:1.2;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0;
}
.cal-pill{font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;border-width:1px;border-style:solid;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#0a0e17;line-height:1.35;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.cal-more{font-size:10px;color:var(--muted);font-weight:700;padding:0 4px;cursor:pointer}
/* Agenda */
.cal-agenda{background:var(--bg);padding:16px;min-height:120px}
.cal-agenda-empty{text-align:center;color:var(--muted);font-size:14px;padding:48px 16px;margin:0}
.cal-agenda-day{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:12px}
.cal-agenda-day-head{
  display:flex;align-items:center;flex-wrap:wrap;gap:8px;
  font-weight:600;color:var(--text);border-bottom:1px solid var(--border);
  padding-bottom:8px;margin-bottom:8px;
}
.cal-agenda-day-title{flex:1;min-width:0}
.cal-agenda-day-iso{font-size:11px;font-family:monospace;color:var(--muted);font-weight:500}
.cal-agenda-today{
  font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;
  color:var(--accent);background:var(--accent-bg);padding:2px 8px;border-radius:6px;
}
.cal-agenda-evs{display:flex;flex-direction:column;gap:6px}
.cal-agenda-ev-row{display:flex;align-items:center;gap:8px;min-width:0}
.cal-agenda-time{flex-shrink:0;font-size:10px;font-weight:700;color:var(--text2);font-variant-numeric:tabular-nums;min-width:42px}
.cal-agenda-ev-row .cal-pill{flex:1;min-width:0}
/* Week / Day time grid */
.cal-time-wrap{display:flex;min-width:640px;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--card)}
.cal-time-gutter{width:48px;flex-shrink:0;border-right:1px solid var(--border);background:var(--bg)}
.cal-time-gutter .tg-hour{height:48px;font-size:10px;color:var(--muted);text-align:right;padding:4px 6px;border-top:1px solid var(--border)}
.cal-time-gutter .tg-hour:first-child{border-top:none}
.cal-time-grid{flex:1;display:flex;flex-direction:column;min-width:0}
.cal-allday-row{display:flex;border-bottom:1px solid var(--border);min-height:32px;background:rgba(15,23,42,.35)}
body.light .cal-allday-row{background:#f8fafc}
.cal-allday-label{width:48px;flex-shrink:0;font-size:9px;font-weight:700;color:var(--muted);display:flex;align-items:center;justify-content:flex-end;padding:4px;border-right:1px solid var(--border)}
.cal-allday-cols{flex:1;display:grid;position:relative;min-height:28px}
.cal-allday-pill{font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;border-width:1px;border-style:solid;margin:2px 3px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#0a0e17;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.cal-cols-row{flex:1;display:grid;position:relative}
.cal-col{border-left:1px solid var(--border);position:relative}
.cal-col:first-child{border-left:none}
.cal-col-head{text-align:center;font-size:11px;font-weight:700;padding:8px 4px;border-bottom:1px solid var(--border);background:var(--bg)}
.cal-col-head.today{color:var(--accent)}
.cal-col--ferie .cal-col-slots{background:var(--cal-ferie-bg)}
.cal-col-slots{position:relative;width:100%;overflow:visible}
.cal-col-ferie-label{
  position:absolute;left:4px;right:4px;bottom:4px;z-index:2;pointer-events:none;
  font-size:10px;color:var(--danger);opacity:.7;line-height:1.2;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:center;
}
.cal-col{min-width:0;overflow:visible}
.cal-slot-line{position:absolute;left:0;right:0;height:1px;background:var(--border)}
.cal-ev{
  position:absolute;border-radius:6px;padding:4px 8px;font-size:10px;font-weight:700;color:#0a0e17;
  border-width:1px;border-style:solid;overflow:hidden;cursor:pointer;line-height:1.3;box-sizing:border-box;
  box-shadow:0 1px 3px rgba(0,0,0,.2);
}
.cal-day-single .cal-cols-row{grid-template-columns:1fr}
/* Popover */
.cal-pop{position:fixed;z-index:8000;min-width:240px;max-width:320px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 16px 48px rgba(0,0,0,.45)}
.cal-pop-title{font-size:14px;font-weight:800;margin-bottom:6px;line-height:1.35}
.cal-pop-meta{font-size:12px;color:var(--text2);line-height:1.6;margin-bottom:10px}
.cal-pop a{font-size:12px;font-weight:700;color:var(--accent);text-decoration:none}
.cal-pop a:hover{text-decoration:underline}
.cal-pop-close{position:absolute;top:8px;right:10px;border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:18px;line-height:1;padding:4px}
.cal-pop--sheet{max-width:none;width:auto}
.cal-color-modal-backdrop{position:fixed;inset:0;z-index:8500;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px}
.cal-color-modal{
  position:relative;width:100%;max-width:420px;max-height:min(88vh,640px);overflow:auto;
  background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 18px 16px;
  box-shadow:0 16px 48px rgba(0,0,0,.45);
}
.cal-color-modal h2{font-size:15px;font-weight:800;margin:0 0 6px;color:var(--text)}
.cal-color-modal-desc{font-size:12px;color:var(--text2);line-height:1.55;margin:0 0 14px}
.cal-color-list{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
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
.cal-color-modal-foot{display:flex;gap:10px;justify-content:flex-end;padding-top:4px}
.cal-color-modal-foot .cal-btn{min-width:96px}
.cal-color-modal-close{
  position:absolute;top:10px;right:12px;border:none;background:transparent;color:var(--muted);
  cursor:pointer;font-size:20px;line-height:1;padding:4px;
}
.cal-color-modal-close:hover{color:var(--text)}
.cal-create-modal-backdrop{position:fixed;inset:0;z-index:8600;background:rgba(0,0,0,.55);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;padding:16px}
.cal-create-modal{
  position:relative;width:100%;max-width:440px;max-height:min(90vh,560px);overflow:auto;
  background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 18px 16px;
  box-shadow:0 16px 48px rgba(0,0,0,.45);
}
.cal-create-modal h2{font-size:15px;font-weight:800;margin:0 0 14px;color:var(--text)}
.cal-create-field{margin-bottom:12px}
.cal-create-field label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px}
.cal-create-field input[type=text],.cal-create-field input[type=date],.cal-create-field input[type=datetime-local],.cal-create-field textarea{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;color:var(--text);font-size:14px;font-family:inherit;transition:border-color .15s;
}
.cal-create-field input:focus,.cal-create-field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none}
.cal-create-field textarea{min-height:72px;resize:vertical}
.cal-create-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cal-create-toggle{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text2);cursor:pointer;user-select:none;margin-bottom:12px}
.cal-create-toggle input{width:16px;height:16px;accent-color:var(--accent)}
.cal-create-modal-foot{display:flex;gap:10px;justify-content:flex-end;margin-top:4px}
.cal-create-modal-foot .cal-btn{min-width:96px}
.cal-create-modal-close{
  position:absolute;top:10px;right:12px;border:none;background:transparent;color:var(--muted);
  cursor:pointer;font-size:20px;line-height:1;padding:4px;
}
.cal-create-modal-close:hover{color:var(--text)}
.cal-day[data-day]{cursor:pointer}
.cal-col-slots[data-day]{cursor:pointer}
.cal-pop-del{
  display:block;width:100%;margin-top:10px;padding:8px 12px;border-radius:8px;
  border:1px solid var(--danger);background:color-mix(in srgb, var(--danger) 12%, transparent);
  color:var(--danger);font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;
}
.cal-pop-del:hover{filter:brightness(1.05)}
.cal-shortcuts-wrap{position:relative;margin-left:8px;flex-shrink:0}
.cal-shortcuts-btn{
  width:28px;height:28px;border-radius:8px;border:1px solid var(--border);background:var(--bg);
  color:var(--muted);font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;
  transition:border-color .15s,color .15s;
}
.cal-shortcuts-btn:hover{border-color:var(--accent);color:var(--accent)}
.cal-shortcuts-tip{
  display:none;position:absolute;right:0;top:calc(100% + 6px);min-width:240px;padding:10px 12px;
  background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:12px;
  color:var(--text2);z-index:200;line-height:1.65;box-shadow:0 8px 24px rgba(0,0,0,.35);pointer-events:none;
}
.cal-shortcuts-wrap:hover .cal-shortcuts-tip,.cal-shortcuts-wrap:focus-within .cal-shortcuts-tip{display:block}
.cal-shortcuts-tip kbd{
  display:inline-block;min-width:1.4em;padding:1px 5px;border-radius:4px;
  border:1px solid var(--border);background:var(--bg);font-family:monospace;font-size:11px;color:var(--text);
}
.cal-mini-wrap{margin:12px 8px 14px;padding:10px;border:1px solid var(--border);border-radius:10px;background:var(--bg)}
.cal-mini-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:6px}
.cal-mini-head span{font-size:11px;font-weight:700;color:var(--text);text-transform:capitalize;flex:1;text-align:center}
.cal-mini-nav{
  width:24px;height:24px;border:1px solid var(--border);border-radius:6px;background:var(--card);
  color:var(--text2);font-size:12px;cursor:pointer;font-family:inherit;padding:0;line-height:1;
}
.cal-mini-nav:hover{border-color:var(--accent);color:var(--accent)}
.cal-mini-grid{display:grid;grid-template-columns:repeat(7,24px);gap:2px;justify-content:center}
.cal-mini-dow{font-size:9px;font-weight:700;color:var(--muted);text-align:center;line-height:18px;font-family:monospace}
.cal-mini-day{
  width:24px;height:24px;border:none;border-radius:50%;background:transparent;color:var(--text2);
  font-size:11px;font-family:monospace;cursor:pointer;padding:0;line-height:24px;
}
.cal-mini-day:hover{background:var(--accent-bg);color:var(--accent)}
.cal-mini-day.other{opacity:.35}
.cal-mini-day.today{background:var(--accent);color:var(--bg);font-weight:700}
.cal-mini-day.today:hover{background:var(--accent);color:var(--bg)}
.cal-mini-day.in-range{background:var(--accent-bg);color:var(--accent);font-weight:600}
.cal-mini-day.today.in-range{box-shadow:0 0 0 2px var(--accent-bg)}
.toast{position:fixed;bottom:22px;right:22px;z-index:9999;padding:11px 16px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 10px 36px rgba(0,0,0,.4);border:1px solid var(--border)}
.toast.success{background:rgba(52,211,153,.15);color:var(--ok)}
.toast.danger{background:rgba(248,113,113,.15);color:var(--danger)}
.cal-print-title{display:none}
@media print{
  body{background:#fff!important;color:#000!important}
  .sidebar,.sidebar-overlay,.cal-toolbar,.mobile-topbar,.cal-shortcuts-wrap,
  .cal-color-modal-backdrop,.cal-create-modal-backdrop,.cal-pop,.toast,
  #cal-color-modal-root,#cal-create-modal-root{display:none!important}
  .layout,.main{display:block!important;width:100%!important}
  .cal-body{
    overflow:visible!important;padding:0!important;width:100%!important;
    background:#fff!important;color:#000!important;
  }
  .cal-print-title{
    display:block!important;font-size:18px;font-weight:800;text-align:center;
    margin:0 0 16px;padding:0 0 12px;border-bottom:2px solid #000;color:#000;
  }
  .cal-month,.cal-time-wrap,.cal-agenda{background:#fff!important;color:#000!important}
  .cal-day,.cal-week-inner,.cal-col,.cal-agenda-day{
    background:#fff!important;border:1px solid #333!important;color:#000!important;
    page-break-inside:avoid;break-inside:avoid;
  }
  .cal-day-num,.cal-col-head,.cal-pill,.cal-ev,.cal-mbar,.cal-allday-pill{
    color:#000!important;border-color:#333!important;
  }
  .cal-pill,.cal-ev,.cal-mbar,.cal-allday-pill{box-shadow:none!important}
  .cal-day--ferie,.cal-col--ferie .cal-col-slots{background:#f5f5f5!important}
  .cal-week-num,.cal-mini-wrap,.cal-toggle,.cal-gear-btn{display:none!important}
}
@media(max-width:900px){
  .mobile-topbar{display:flex}
  .mobile-menu-btn,.mobile-home-btn{display:inline-flex}
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  body.has-topbar .main{padding-top:0}
  .cal-title{font-size:14px;min-width:120px}
}
@media(max-width:767px){
  .cal-toolbar{flex-wrap:nowrap;align-items:center;gap:8px;padding:12px 14px}
  .cal-nav{display:contents}
  .cal-nav #btn-export-ics,.cal-nav #btn-print{display:none!important}
  #btn-prev{order:1}
  .cal-title{order:2;flex:1;min-width:0;font-size:14px;text-align:center}
  #btn-next{order:3}
  #btn-today{order:4}
  .cal-view-tabs,.cal-shortcuts-wrap{display:none!important}
  .nav-btn[data-view="month"],.nav-btn[data-view="week"],
  .cal-view-tabs .cal-btn[data-view="month"],.cal-view-tabs .cal-btn[data-view="week"]{display:none!important}
  .cal-body{padding:0}
  .cal-agenda{width:100%;box-sizing:border-box;padding:12px}
  .cal-agenda-ev-row .cal-pill{
    min-height:32px;font-size:13px;line-height:1.4;padding:6px 10px;
    white-space:normal;overflow:hidden;text-overflow:ellipsis;
  }
  .cal-pop--sheet{
    top:auto!important;left:0!important;right:0!important;bottom:0!important;
    width:auto;max-width:none;border-radius:12px 12px 0 0;max-height:60vh;overflow-y:auto;
  }
}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_calendar.js"></script>
<script>window.__MYSIFA_APP__='calendrier';</script>
<script src="/static/chat_widget.js"></script>
<div class="sidebar-overlay" id="sb-ov"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Calendrier</div>
    </div>
    <button type="button" class="nav-btn active" data-view="month" id="nav-month">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      Vue mensuelle
    </button>
    <button type="button" class="nav-btn" data-view="week" id="nav-week">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="18" rx="1"/></svg>
      Vue hebdomadaire
    </button>
    <button type="button" class="nav-btn" data-view="day" id="nav-day">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      Vue journalière
    </button>
    <button type="button" class="nav-btn" data-view="agenda" id="nav-agenda">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
      Vue agenda
    </button>
    <hr>
    <div class="cal-cals-section" id="cal-cals-section">
      <button type="button" class="cal-cals-head" id="cal-cals-head" aria-expanded="true" aria-controls="cal-toggles">
        <span class="cal-cals-head-label">Calendriers</span>
        <svg class="cal-cals-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div id="cal-toggles"></div>
    </div>
    <div id="cal-mini-root"></div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="sb-user-chip" onclick="location.href='/profil'" title="Mon profil"></div>
      <button type="button" class="theme-btn" id="btn-theme">
        <span class="theme-ico" id="theme-ico"></span>
        <span class="theme-label" id="theme-label">Mode clair</span>
      </button>
      <button type="button" class="logout-btn" id="btn-logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Calendrier · __V_LABEL__</div>
    </div>
  </aside>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" id="sb-burger" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Calendrier</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Vue mensuelle</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/></svg>
      </button>
    </div>
    <div class="cal-toolbar">
      <div class="cal-nav">
        <button type="button" class="cal-btn" id="btn-prev">← Précédent</button>
        <button type="button" class="cal-btn primary" id="btn-today">Aujourd'hui</button>
        <button type="button" class="cal-btn" id="btn-next">Suivant →</button>
        <button type="button" class="cal-btn" id="btn-export-ics">Exporter .ics</button>
        <button type="button" class="cal-btn" id="btn-print">Imprimer</button>
      </div>
      <div class="cal-title" id="cal-title">—</div>
      <div class="cal-view-tabs">
        <button type="button" class="cal-btn" data-view="month">Mois</button>
        <button type="button" class="cal-btn" data-view="week">Semaine</button>
        <button type="button" class="cal-btn" data-view="day">Jour</button>
        <button type="button" class="cal-btn" data-view="agenda">Agenda</button>
      </div>
      <div class="cal-shortcuts-wrap">
        <button type="button" class="cal-shortcuts-btn" aria-label="Raccourcis clavier" title="Raccourcis clavier">?</button>
        <div class="cal-shortcuts-tip" role="tooltip">
          <div><kbd>T</kbd> Aujourd'hui</div>
          <div><kbd>←</kbd> <kbd>→</kbd> Période préc. / suiv.</div>
          <div><kbd>M</kbd> Mois · <kbd>W</kbd> Semaine · <kbd>D</kbd> Jour · <kbd>A</kbd> Agenda</div>
          <div><kbd>Esc</kbd> Fermer la popup</div>
        </div>
      </div>
    </div>
    <h1 class="cal-print-title" id="cal-print-title"></h1>
    <div class="cal-body" id="cal-body">
      <div class="cal-loading" id="cal-loading">Chargement…</div>
    </div>
  </main>
</div>
<div id="cal-color-modal-root"></div>
<div id="cal-create-modal-root"></div>
<script>
const USER_ROLE=__USER_ROLE__;
const CAL_DEFS=window.MySifaCalendar?MySifaCalendar.CAL_DEFS:[];
const CAL_IDS_FULL=CAL_DEFS.map(c=>c.id);
const CAL_IDS_ADMIN=['conges','anniversaires','feries','paie','expeditions','perso'];
const CAL_IDS_BASIC=['conges','feries','perso'];
function calIdsForRole(role){
  if(role==='superadmin'||role==='direction')return CAL_IDS_FULL;
  if(role==='administration')return CAL_IDS_ADMIN;
  return CAL_IDS_BASIC;
}
function accessibleCalDefs(){
  const allowed=new Set(calIdsForRole(USER_ROLE));
  return CAL_DEFS.filter(c=>allowed.has(c.id));
}
const ICO_CAL_GEAR='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
const PROD_CAL_IDS=['production_1','production_2','production_3','production_4'];
const LS_VISIBLE='mysifa_cal_visible';
const LS_CAL_LIST='mysifa_cal_list_open';
const MOIS=['','janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
const JOURS=['lun','mar','mer','jeu','ven','sam','dim'];
const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};

const PX_PER_HOUR=48;
const CAL_SLOT_PAD_X=3;
const DEFAULT_DAY_WIN={hStart:5,hEnd:21};
const LS_VIEW='mysifa_cal_view';
const VALID_VIEWS=['month','week','day','agenda'];
const MINI_DOW=['L','M','M','J','V','S','D'];
const MOBILE_BREAKPOINT=768;
let S={view:'month',anchor:new Date(),events:[],dayWindows:{},feriesMap:{},loading:false,visible:{},pop:null,colorModal:null,createModal:null,miniCalY:null,miniCalM:null,_touchStartX:null,_touchStartY:null};
let ME=null;

function isMobileViewport(){return window.innerWidth<MOBILE_BREAKPOINT;}
function hasSavedView(){
  try{
    const v=localStorage.getItem(LS_VIEW);
    return VALID_VIEWS.includes(v);
  }catch(e){}
  return false;
}
function loadSavedView(){
  if(hasSavedView()){
    try{
      const v=localStorage.getItem(LS_VIEW);
      if(VALID_VIEWS.includes(v))return v;
    }catch(e){}
  }
  if(isMobileViewport())return 'agenda';
  return 'month';
}
function applyMobileDefaultView(){
  if(!hasSavedView()&&isMobileViewport())S.view='agenda';
}
function applyViewChrome(v){
  document.querySelectorAll('.nav-btn[data-view]').forEach(b=>{
    b.classList.toggle('active',b.dataset.view===v);
  });
  document.querySelectorAll('.cal-view-tabs .cal-btn[data-view]').forEach(b=>{
    b.classList.toggle('primary',b.dataset.view===v);
  });
  const subs={month:'Vue mensuelle',week:'Vue hebdomadaire',day:'Vue journalière',agenda:'Vue agenda'};
  const sub=document.getElementById('mobile-sub');
  if(sub)sub.textContent=subs[v]||'';
}
function isTypingTarget(el){
  if(!el)return false;
  const tag=el.tagName;
  if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT')return true;
  if(el.isContentEditable)return true;
  return false;
}
function syncMiniCalMonthFromAnchor(){
  const a=new Date(S.anchor);
  S.miniCalY=a.getFullYear();
  S.miniCalM=a.getMonth();
}
function isMiniDayInRange(day){
  const d=startOfDay(day);
  if(S.view==='day')return ymd(d)===ymd(startOfDay(S.anchor));
  if(S.view==='week'){
    const ws=startOfWeekMon(S.anchor),we=addDays(ws,6);
    return d>=ws&&d<=we;
  }
  if(S.view==='month'){
    return d.getMonth()===S.anchor.getMonth()&&d.getFullYear()===S.anchor.getFullYear();
  }
  if(S.view==='agenda'){
    const start=startOfDay(new Date(S.anchor)),end=addDays(start,29);
    return d>=start&&d<=end;
  }
  return false;
}
function shiftMiniCalMonth(delta){
  if(S.miniCalY==null)syncMiniCalMonthFromAnchor();
  let m=S.miniCalM+delta,y=S.miniCalY;
  while(m<0){m+=12;y--;}
  while(m>11){m-=12;y++;}
  S.miniCalM=m;S.miniCalY=y;
  renderMiniCal();
}
function renderMiniCal(){
  const root=document.getElementById('cal-mini-root');
  if(!root)return;
  if(S.miniCalY==null)syncMiniCalMonthFromAnchor();
  const y=S.miniCalY,m=S.miniCalM;
  const first=new Date(y,m,1);
  const gridStart=startOfWeekMon(first);
  const last=new Date(y,m+1,0);
  let html='<div class="cal-mini-wrap"><div class="cal-mini-head">';
  html+='<button type="button" class="cal-mini-nav" id="cal-mini-prev" aria-label="Mois précédent">←</button>';
  html+='<span>'+MOIS[m+1]+' '+y+'</span>';
  html+='<button type="button" class="cal-mini-nav" id="cal-mini-next" aria-label="Mois suivant">→</button>';
  html+='</div><div class="cal-mini-grid">';
  MINI_DOW.forEach(dow=>{html+='<div class="cal-mini-dow">'+dow+'</div>';});
  let cur=new Date(gridStart);
  for(let i=0;i<42;i++){
    const other=cur.getMonth()!==m;
    const today=isToday(cur);
    const inRange=!other&&isMiniDayInRange(cur);
    let cls='cal-mini-day';
    if(other)cls+=' other';
    if(today)cls+=' today';
    if(inRange)cls+=' in-range';
    html+='<button type="button" class="'+cls+'" data-day="'+ymd(cur)+'">'+cur.getDate()+'</button>';
    cur=addDays(cur,1);
  }
  html+='</div></div>';
  root.innerHTML=html;
  root.querySelector('#cal-mini-prev').onclick=()=>shiftMiniCalMonth(-1);
  root.querySelector('#cal-mini-next').onclick=()=>shiftMiniCalMonth(1);
  root.querySelectorAll('.cal-mini-day').forEach(btn=>{
    btn.onclick=()=>{
      S.anchor=parseDayStr(btn.dataset.day);
      fetchEvents();
    };
  });
}
function goToToday(){
  S.anchor=new Date();
  syncMiniCalMonthFromAnchor();
  fetchEvents();
}

function pad2(n){return String(n).padStart(2,'0');}
function ymd(d){return d.getFullYear()+'-'+pad2(d.getMonth()+1)+'-'+pad2(d.getDate());}
function parseEvDt(s){
  if(!s)return null;
  const t=String(s).trim().replace(' ','T').replace(/Z$/i,'').split('+')[0];
  const m=t.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if(m)return new Date(+m[1],+m[2]-1,+m[3],+(m[4]||0),+(m[5]||0),+(m[6]||0));
  const d=new Date(t);
  return isNaN(d.getTime())?null:d;
}
function startOfDay(d){const x=new Date(d);x.setHours(0,0,0,0);return x;}
function addDays(d,n){const x=new Date(d);x.setDate(x.getDate()+n);return x;}
function startOfWeekMon(d){const x=startOfDay(d);const w=(x.getDay()+6)%7;x.setDate(x.getDate()-w);return x;}
/** Numéro de semaine ISO (1–53), semaine commençant le lundi. */
function getISOWeek(d){
  const date=startOfDay(new Date(d));
  const thu=new Date(date);
  thu.setDate(date.getDate()+3-((date.getDay()+6)%7));
  const week1=new Date(thu.getFullYear(),0,4);
  return 1+Math.round(((thu-week1)/86400000-3+((week1.getDay()+6)%7))/7);
}
function isFerieEvent(ev){return ev&&ev.calendrier==='feries';}
function buildFeriesMap(){
  const map={};
  S.events.forEach(ev=>{
    if(!evVisible(ev)||!isFerieEvent(ev))return;
    const label=String(ev.titre||'').trim()||'Jour férié';
    let c=startOfDay(evStart(ev)||new Date());
    const end=startOfDay(evEnd(ev)||c);
    while(c<=end){
      const dk=ymd(c);
      if(!map[dk])map[dk]=label;
      c=addDays(c,1);
    }
  });
  return map;
}
function sameDay(a,b){return a&&b&&ymd(a)===ymd(b);}
function isToday(d){return sameDay(d,new Date());}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}

function showToast(msg,type){
  const t=document.createElement('div');
  t.className='toast '+(type==='danger'?'danger':'success');
  t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),3200);
}

function applyTheme(){
  if(window.MySifaTheme){
    MySifaTheme.initFromStorage();
  }else{
    const mode=localStorage.getItem('theme')||'dark';
    document.body.classList.toggle('light',mode==='light');
  }
  syncThemeBtn();
}

function syncThemeBtn(){
  const isLight=document.body.classList.contains('light');
  const ico=document.getElementById('theme-ico');
  const lbl=document.getElementById('theme-label');
  if(ico)ico.innerHTML=isLight
    ?'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
    :'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  if(lbl)lbl.textContent=isLight?'Mode sombre':'Mode clair';
}

function loadVisible(){
  try{
    const raw=localStorage.getItem(LS_VISIBLE);
    if(raw){
      const o=JSON.parse(raw);
      if(o&&typeof o==='object'){
        if(o.production!==undefined&&o.production_1===undefined){
          const v=o.production!==false;
          PROD_CAL_IDS.forEach(k=>{o[k]=v;});
        }
        accessibleCalDefs().forEach(c=>{S.visible[c.id]=o[c.id]!==false;});
        return;
      }
    }
  }catch(e){}
  accessibleCalDefs().forEach(c=>{S.visible[c.id]=true;});
}
function saveVisible(){
  try{localStorage.setItem(LS_VISIBLE,JSON.stringify(S.visible));}catch(e){}
}

function loadCalListOpen(){
  try{return localStorage.getItem(LS_CAL_LIST)!=='0';}catch(e){return true;}
}
function saveCalListOpen(open){
  try{localStorage.setItem(LS_CAL_LIST,open?'1':'0');}catch(e){}
}
function applyCalListOpen(open){
  const sec=document.getElementById('cal-cals-section');
  const head=document.getElementById('cal-cals-head');
  if(sec)sec.classList.toggle('collapsed',!open);
  if(head)head.setAttribute('aria-expanded',open?'true':'false');
}
function toggleCalList(){
  const sec=document.getElementById('cal-cals-section');
  const willOpen=!!(sec&&sec.classList.contains('collapsed'));
  applyCalListOpen(willOpen);
  saveCalListOpen(willOpen);
}

function calColorModalRow(c,focusId){
  const col=(window.MySifaCalendar?MySifaCalendar.loadColorsMap():{})[c.id]||c.color;
  const hi=focusId===c.id?' highlight':'';
  return `<div class="cal-color-row${hi}" id="cal-mrow-${esc(c.id)}">
    <span class="cal-color-dot" style="background:${esc(col)}"></span>
    <span class="cal-color-label">${esc(c.label)}</span>
    <input type="color" value="${esc(col)}" aria-label="Couleur ${esc(c.label)}"
      oninput="onCalColorModalInput('${esc(c.id)}',this.value)">
    <button type="button" class="cal-color-reset" onclick="resetCalColorModal('${esc(c.id)}')">Défaut</button>
  </div>`;
}
function closeCalColorModal(){
  if(S.colorModal){S.colorModal.remove();S.colorModal=null;}
  document.removeEventListener('keydown',onCalColorModalKey);
}
function onCalColorModalKey(e){if(e.key==='Escape')closeCalColorModal();}
function syncCalToggleColors(){
  document.querySelectorAll('.cal-toggle').forEach(lbl=>{
    const inp=lbl.querySelector('input[data-cal]');
    if(inp)lbl.style.setProperty('--cal-c',calColor(inp.dataset.cal));
  });
}
function onCalColorModalInput(calId,hex){
  if(!window.MySifaCalendar||!MySifaCalendar.validHex(hex))return;
  MySifaCalendar.setColor(calId,hex);
  const row=document.getElementById('cal-mrow-'+calId);
  const dot=row&&row.querySelector('.cal-color-dot');
  if(dot)dot.style.background=hex;
  syncCalToggleColors();
}
function resetCalColorModal(calId){
  if(!window.MySifaCalendar)return;
  MySifaCalendar.resetColor(calId);
  const row=document.getElementById('cal-mrow-'+calId);
  if(!row)return;
  const hex=MySifaCalendar.colorFor(calId);
  const dot=row.querySelector('.cal-color-dot');
  const inp=row.querySelector('input[type=color]');
  if(dot)dot.style.background=hex;
  if(inp)inp.value=hex;
  syncCalToggleColors();
}
async function saveCalColorsModal(){
  const prefs=window.MySifaTheme?MySifaTheme.loadPrefs():{palette:'mysifa',style:'defaut',mode:'dark'};
  const tp=window.MySifaTheme&&MySifaTheme.themePrefsPayload
    ?MySifaTheme.themePrefsPayload(prefs)
    :(window.MySifaCalendar?MySifaCalendar.buildThemePrefsPayload(prefs):prefs);
  try{
    await api('/api/auth/me',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({theme_prefs:tp})
    });
    showToast('Couleurs enregistrées','success');
  }catch(e){
    showToast('Couleurs appliquées localement','success');
  }
  renderToggles();
  renderCalendar();
  closeCalColorModal();
}
function openCalColorModal(focusId){
  closeCalColorModal();
  const root=document.getElementById('cal-color-modal-root');
  if(!root||!window.MySifaCalendar)return;
  const calDefs=accessibleCalDefs();
  const wrap=document.createElement('div');
  wrap.className='cal-color-modal-backdrop';
  wrap.innerHTML=`<div class="cal-color-modal" role="dialog" aria-labelledby="cal-color-modal-title">
    <button type="button" class="cal-color-modal-close" aria-label="Fermer" onclick="closeCalColorModal()">×</button>
    <h2 id="cal-color-modal-title">Couleurs des calendriers</h2>
    <p class="cal-color-modal-desc">Choisissez une couleur par calendrier. Les changements sont visibles immédiatement.</p>
    <div class="cal-color-list">${calDefs.map(c=>calColorModalRow(c,focusId)).join('')}</div>
    <div class="cal-color-modal-foot">
      <button type="button" class="cal-btn" onclick="closeCalColorModal()">Fermer</button>
      <button type="button" class="cal-btn primary" onclick="saveCalColorsModal()">Enregistrer</button>
    </div>
  </div>`;
  wrap.onclick=e=>{if(e.target===wrap)closeCalColorModal();};
  wrap.querySelector('.cal-color-modal').onclick=e=>e.stopPropagation();
  root.appendChild(wrap);
  S.colorModal=wrap;
  document.addEventListener('keydown',onCalColorModalKey);
  if(focusId){
    requestAnimationFrame(()=>{
      const row=document.getElementById('cal-mrow-'+focusId);
      if(row){row.scrollIntoView({block:'nearest'});row.classList.add('highlight');}
    });
  }
}
function renderToggles(){
  const box=document.getElementById('cal-toggles');
  if(!box)return;
  box.innerHTML=accessibleCalDefs().map(c=>`<label class="cal-toggle" style="--cal-c:${calColor(c.id)}">
      <span class="cal-dot"></span>
      <span class="flex1">${esc(c.label)}</span>
      <button type="button" class="cal-gear-btn" title="Couleur du calendrier" aria-label="Réglage couleur ${esc(c.label)}"
        onclick="event.preventDefault();event.stopPropagation();openCalColorModal('${esc(c.id)}')">${ICO_CAL_GEAR}</button>
      <input type="checkbox" data-cal="${c.id}" ${S.visible[c.id]?'checked':''}>
    </label>`).join('');
  box.querySelectorAll('input[data-cal]').forEach(inp=>{
    inp.onchange=()=>{
      S.visible[inp.dataset.cal]=inp.checked;
      saveVisible();
      fetchEvents();
    };
  });
}

function activeCalList(){
  const allowed=new Set(calIdsForRole(USER_ROLE));
  return CAL_DEFS.filter(c=>allowed.has(c.id)&&S.visible[c.id]).map(c=>c.id);
}
function exportIcs(){
  const p=getPeriod();
  const cals=activeCalList();
  if(!cals.length){showToast('Aucun calendrier sélectionné.','danger');return;}
  const q=new URLSearchParams({
    date_debut:ymd(p.start),
    date_fin:ymd(p.end),
    calendriers:cals.join(',')
  });
  window.location.href='/api/calendrier/export.ics?'+q;
}
function calColor(id){
  if(window.MySifaCalendar)return MySifaCalendar.colorFor(id);
  const c=CAL_DEFS.find(x=>x.id===id);
  return c?c.color:'var(--accent)';
}
function darkenHex(hex,f){
  const m=String(hex||'').trim().match(/^#([0-9a-f]{6})$/i);
  if(!m)return '#0f172a';
  const k=1-Math.min(0.5,Math.max(0,f==null?0.32:f));
  const r=Math.min(255,Math.max(0,Math.round(parseInt(m[1].slice(0,2),16)*k)));
  const g=Math.min(255,Math.max(0,Math.round(parseInt(m[1].slice(2,4),16)*k)));
  const b=Math.min(255,Math.max(0,Math.round(parseInt(m[1].slice(4,6),16)*k)));
  return '#'+[r,g,b].map(x=>pad2(x.toString(16))).join('');
}
function calSlotStyle(calId){
  const fill=calColor(calId);
  if(String(fill).indexOf('var(')===0)return 'background:'+fill+';border-color:var(--border)';
  return 'background:'+fill+';border-color:'+darkenHex(fill);
}

function getPeriod(){
  const a=new Date(S.anchor);
  if(S.view==='month'){
    const y=a.getFullYear(),m=a.getMonth();
    const gridStart=startOfWeekMon(new Date(y,m,1));
    const last=new Date(y,m+1,0);
    const gridEnd=addDays(startOfWeekMon(last),6);
    return{start:gridStart,end:gridEnd,title:MOIS[m+1]+' '+y};
  }
  if(S.view==='week'){
    const ws=startOfWeekMon(a);
    const we=addDays(ws,6);
    return{start:ws,end:we,title:ymd(ws)+' → '+ymd(we)};
  }
  if(S.view==='agenda'){
    const start=startOfDay(new Date(S.anchor));
    const end=addDays(start,29);
    return{start,end,title:'30 prochains jours'};
  }
  const d=startOfDay(a);
  return{start:d,end:d,title:d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'})};
}

function evVisible(ev){return !!S.visible[ev.calendrier];}
function evStart(ev){return parseEvDt(ev.debut);}
function evEnd(ev){return parseEvDt(ev.fin)||evStart(ev);}
function layoutKey(ev){return String(ev.calendrier)+'|'+String(ev.id);}
function clipsOverlap(a,b){return a.start<b.end&&b.start<a.end;}
function evOverlapsDay(ev,day){
  const s=evStart(ev),e=evEnd(ev)||s;
  if(!s)return false;
  const dk=ymd(day);
  return ymd(startOfDay(s))<=dk&&ymd(startOfDay(e))>=dk;
}
function getDayWindow(day){
  const w=S.dayWindows[ymd(day)];
  if(!w)return DEFAULT_DAY_WIN;
  return{
    hStart:Number(w.h_start)||DEFAULT_DAY_WIN.hStart,
    hEnd:Number(w.h_end)||DEFAULT_DAY_WIN.hEnd,
    off:!!(w.off)
  };
}
/** Plage commune pour aligner les colonnes (semaine). */
function weekTimeRange(days){
  let hStart=24,hEnd=0;
  days.forEach(day=>{
    const w=getDayWindow(day);
    hStart=Math.min(hStart,w.hStart);
    hEnd=Math.max(hEnd,w.hEnd);
  });
  if(hStart>=24)return DEFAULT_DAY_WIN;
  return{hStart,hEnd:Math.max(hEnd,hStart+1)};
}
function workBoundsMs(day,range){
  const d0=startOfDay(day);
  const r=range||getDayWindow(day);
  return{
    start:d0.getTime()+r.hStart*3600000,
    end:d0.getTime()+r.hEnd*3600000
  };
}
/** Intervalle [début, fin] d'un événement sur un jour (ms), borné aux horaires machines. */
function evClipOnDay(ev,day){
  const s=evStart(ev),e=evEnd(ev)||s;
  if(!s||!evOverlapsDay(ev,day))return null;
  const d0=startOfDay(day);
  const dEnd=new Date(d0);dEnd.setHours(23,59,59,999);
  let clipS=s<d0?d0:s;
  let clipE=e>dEnd?dEnd:e;
  if(clipE<=clipS)return null;
  const wb=workBoundsMs(day);
  clipS=new Date(Math.max(clipS.getTime(),wb.start));
  clipE=new Date(Math.min(clipE.getTime(),wb.end));
  if(clipE<=clipS)return null;
  return{start:clipS.getTime(),end:clipE.getTime()};
}
/** Tranche horaire d'un événement (vues semaine / jour), relative à la plage affichée. */
function timedSliceOnDay(ev,day,range){
  const clip=evClipOnDay(ev,day);
  if(!clip)return null;
  const r=range||getDayWindow(day);
  const ws=workBoundsMs(day,r).start;
  const topMin=(clip.start-ws)/60000;
  const endMin=(clip.end-ws)/60000;
  return{top:topMin/60*PX_PER_HOUR,h:Math.max(18,(endMin-topMin)/60*PX_PER_HOUR)};
}
function evDayKey(d){return ymd(d);}
function daysBetweenInclusive(s,e){
  const out=[];let c=startOfDay(s);const end=startOfDay(e);
  while(c<=end){out.push(new Date(c));c=addDays(c,1);}
  return out;
}
function spanDays(ev){
  const s=evStart(ev),e=evEnd(ev);
  if(!s)return 1;
  const d0=startOfDay(s),d1=startOfDay(e||s);
  return Math.max(1,Math.round((d1-d0)/86400000)+1);
}
function isMultiDay(ev){return ev.all_day&&spanDays(ev)>1;}

async function api(path,opts){
  const r=await fetch(path,{credentials:'include',...opts});
  if(r.status===401){location.href='/?next=/calendrier';throw new Error('auth');}
  if(r.status===403){showToast('Accès non autorisé à MyCalendrier.','danger');throw new Error('auth');}
  if(!r.ok){
    let d='Erreur';
    try{const j=await r.json();d=j.detail?(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail)):d;}catch(e){}
    throw new Error(d);
  }
  const ct=r.headers.get('content-type')||'';
  if(ct.includes('application/json'))return r.json();
  return null;
}

async function fetchEvents(){
  const p=getPeriod();
  const cals=activeCalList();
  const body=document.getElementById('cal-body');
  const loading=document.getElementById('cal-loading');
  if(!cals.length){
    S.events=[];
    S.dayWindows={};
    if(loading)loading.style.display='none';
    if(body)body.innerHTML='<p class="cal-loading">Aucun calendrier sélectionné.</p>';
    return;
  }
  S.loading=true;
  if(loading){loading.style.display='block';loading.textContent='Chargement…';}
  try{
    const q=new URLSearchParams({
      date_debut:ymd(p.start),
      date_fin:ymd(p.end),
      calendriers:cals.join(',')
    });
    const res=await api('/api/calendrier/events?'+q);
    if(Array.isArray(res)){
      S.events=res;
      S.dayWindows={};
    }else{
      S.events=(res&&res.events)||[];
      S.dayWindows=(res&&res.day_windows)||{};
    }
    if(loading)loading.style.display='none';
    renderCalendar();
  }catch(e){
    if(e.message!=='auth')showToast(e.message||'Chargement impossible','danger');
    if(loading)loading.textContent='Erreur de chargement.';
  }finally{S.loading=false;}
}


function parseDayStr(dayStr){
  const p=String(dayStr||'').split('-').map(Number);
  if(p.length<3||!p[0])return new Date();
  return new Date(p[0],p[1]-1,p[2]);
}
function toDatetimeLocalValue(d){
  return ymd(d)+'T'+pad2(d.getHours())+':'+pad2(d.getMinutes());
}
function defaultPersoRange(opts){
  const day=parseDayStr(opts.day);
  if(opts.allDay){
    return{debut:ymd(day)+'T00:00',fin:ymd(day)+'T23:59',all_day:true};
  }
  const h=typeof opts.hour==='number'?opts.hour:9;
  const h0=Math.floor(h);
  const m=Math.round((h-h0)*60);
  const start=new Date(day);
  start.setHours(h0,m,0,0);
  const end=new Date(start);
  end.setHours(start.getHours()+1);
  return{debut:toDatetimeLocalValue(start),fin:toDatetimeLocalValue(end),all_day:false};
}
function closeCreateModal(){
  if(S.createModal){S.createModal.remove();S.createModal=null;}
  document.removeEventListener('keydown',onCreateModalKey);
}
function onCreateModalKey(e){if(e.key==='Escape')closeCreateModal();}
function syncCreateModalAllDay(){
  const allDay=!!document.getElementById('cp-allday')?.checked;
  const d0=document.getElementById('cp-debut');
  const d1=document.getElementById('cp-fin');
  if(!d0||!d1)return;
  const v0=(d0.value||'').slice(0,10);
  const v1=(d1.value||'').slice(0,10);
  d0.type=allDay?'date':'datetime-local';
  d1.type=allDay?'date':'datetime-local';
  if(allDay){
    if(v0)d0.value=v0;
    if(v1)d1.value=v1||v0;
  }else{
    if(v0&&v0.length===10)d0.value=v0+'T09:00';
    if(v1&&v1.length===10)d1.value=(v1||v0)+'T10:00';
  }
}
function readCreateModalPayload(){
  const titre=(document.getElementById('cp-titre')?.value||'').trim();
  const all_day=!!document.getElementById('cp-allday')?.checked;
  let date_debut=document.getElementById('cp-debut')?.value||'';
  let date_fin=document.getElementById('cp-fin')?.value||'';
  if(all_day){
    if(date_debut.length===10)date_debut+='T00:00';
    if(date_fin.length===10)date_fin+='T23:59';
  }else{
    if(date_debut.length===10)date_debut+='T09:00';
    if(date_fin.length===10)date_fin+='T10:00';
  }
  const note=(document.getElementById('cp-note')?.value||'').trim()||null;
  return{titre,date_debut,date_fin,all_day,note};
}
function openCreateModal(opts){
  closeCreateModal();
  closePop();
  const root=document.getElementById('cal-create-modal-root');
  if(!root)return;
  const defs=defaultPersoRange(opts||{});
  const wrap=document.createElement('div');
  wrap.className='cal-create-modal-backdrop';
  wrap.innerHTML=`<div class="cal-create-modal" role="dialog" aria-labelledby="cp-title-h">
    <button type="button" class="cal-create-modal-close" aria-label="Fermer">×</button>
    <h2 id="cp-title-h">Nouvel événement personnel</h2>
    <div class="cal-create-field"><label for="cp-titre">Titre</label>
      <input type="text" id="cp-titre" required maxlength="500" placeholder="Titre de l'événement"></div>
    <label class="cal-create-toggle"><input type="checkbox" id="cp-allday" ${defs.all_day?'checked':''}> Journée entière</label>
    <div class="cal-create-row">
      <div class="cal-create-field"><label for="cp-debut">Début</label>
        <input id="cp-debut" type="${defs.all_day?'date':'datetime-local'}" value="${defs.all_day?defs.debut.slice(0,10):defs.debut}"></div>
      <div class="cal-create-field"><label for="cp-fin">Fin</label>
        <input id="cp-fin" type="${defs.all_day?'date':'datetime-local'}" value="${defs.all_day?defs.fin.slice(0,10):defs.fin}"></div>
    </div>
    <div class="cal-create-field"><label for="cp-note">Note (optionnel)</label>
      <textarea id="cp-note" maxlength="4000" placeholder="Détails…"></textarea></div>
    <div class="cal-create-modal-foot">
      <button type="button" class="cal-btn" id="cp-cancel">Annuler</button>
      <button type="button" class="cal-btn primary" id="cp-submit">Créer</button>
    </div>
  </div>`;
  root.appendChild(wrap);
  S.createModal=wrap;
  wrap.onclick=e=>{if(e.target===wrap)closeCreateModal();};
  wrap.querySelector('.cal-create-modal').onclick=e=>e.stopPropagation();
  wrap.querySelector('.cal-create-modal-close').onclick=closeCreateModal;
  wrap.querySelector('#cp-cancel').onclick=closeCreateModal;
  document.getElementById('cp-allday').onchange=syncCreateModalAllDay;
  wrap.querySelector('#cp-submit').onclick=submitCreatePerso;
  document.addEventListener('keydown',onCreateModalKey);
  setTimeout(()=>document.getElementById('cp-titre')?.focus(),0);
}
async function submitCreatePerso(){
  const payload=readCreateModalPayload();
  if(!payload.titre){showToast('Titre requis.','danger');return;}
  if(!payload.date_debut||!payload.date_fin){showToast('Dates invalides.','danger');return;}
  try{
    await api('/api/calendrier/events/perso',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    });
    closeCreateModal();
    showToast('Événement créé.','success');
    if(!S.visible.perso)S.visible.perso=true;
    saveVisible();
    fetchEvents();
  }catch(e){
    showToast(e.message||'Création impossible','danger');
  }
}
function bindBodySwipe(){
  const body=document.getElementById('cal-body');
  if(!body||body.dataset.swipeBound)return;
  body.dataset.swipeBound='1';
  body.addEventListener('touchstart',e=>{
    if(e.touches.length!==1)return;
    S._touchStartX=e.touches[0].clientX;
    S._touchStartY=e.touches[0].clientY;
  },{passive:true});
  body.addEventListener('touchend',e=>{
    if(S._touchStartX==null)return;
    const t=e.changedTouches[0];
    if(!t)return;
    const dx=t.clientX-S._touchStartX;
    const dy=t.clientY-(S._touchStartY||0);
    S._touchStartX=null;
    S._touchStartY=null;
    if(Math.abs(dx)<50)return;
    if(Math.abs(dy)>Math.abs(dx))return;
    if(dx<-50)shiftAnchor(1);
    else if(dx>50)shiftAnchor(-1);
  },{passive:true});
}
function bindCalendarBodyClicks(){
  const body=document.getElementById('cal-body');
  if(!body||body.dataset.createBound)return;
  body.dataset.createBound='1';
  bindBodySwipe();
  body.addEventListener('click',e=>{
    if(e.target.closest('[data-ev-id],.cal-more'))return;
    const dayEl=e.target.closest('.cal-day[data-day]');
    if(dayEl){
      openCreateModal({day:dayEl.dataset.day,allDay:true});
      return;
    }
    const slots=e.target.closest('.cal-col-slots[data-day]');
    if(slots){
      if(e.target.closest('.cal-col-ferie-label'))return;
      const h0=parseFloat(slots.dataset.hStart);
      const h1=parseFloat(slots.dataset.hEnd);
      const rect=slots.getBoundingClientRect();
      const y=e.clientY-rect.top;
      const ratio=rect.height?(y/rect.height):0.5;
      const hour=h0+ratio*(h1-h0);
      openCreateModal({day:slots.dataset.day,hour,allDay:false});
    }
  });
}

function closePop(){if(S.pop){S.pop.remove();S.pop=null;}}

function openPop(ev,anchorEl){
  closePop();
  const s=evStart(ev),e=evEnd(ev);
  let per='—';
  if(s){
    if(ev.all_day)per=ymd(s)+(spanDays(ev)>1?' → '+ymd(e):'');
    else per=s.toLocaleString('fr-FR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})+
      (e?' → '+e.toLocaleString('fr-FR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}):'');
  }
  const stat=ev.meta&&ev.meta.statut?('<div><strong>Statut :</strong> '+esc(ev.meta.statut)+'</div>'):'';
  const noteBlk=ev.calendrier==='perso'&&ev.meta&&ev.meta.note
    ?'<div style="margin-top:8px;font-size:12px;color:var(--text2);line-height:1.5">'+esc(ev.meta.note)+'</div>':'';
  let link='';
  if(ev.calendrier.startsWith('production_'))link='<a href="/planning">Ouvrir le planning production</a>';
  else if(ev.calendrier==='conges')link='<a href="/planning-rh">Ouvrir le planning RH</a>';
  else if(ev.calendrier==='expeditions')link='<a href="/expe">Ouvrir MyExpé</a>';
  const delBtn=ev.calendrier==='perso'
    ?'<button type="button" class="cal-pop-del">Supprimer</button>':'';
  const pop=document.createElement('div');
  pop.className='cal-pop';
  pop.innerHTML='<button type="button" class="cal-pop-close" aria-label="Fermer">×</button>'+
    '<div class="cal-pop-title">'+esc(ev.titre)+'</div>'+
    '<div class="cal-pop-meta">'+esc(CAL_DEFS.find(c=>c.id===ev.calendrier)?.label||ev.calendrier)+'<br>'+per+stat+noteBlk+'</div>'+
    (link?'<div>'+link+'</div>':'')+delBtn;
  document.body.appendChild(pop);
  S.pop=pop;
  pop.querySelector('.cal-pop-close').onclick=closePop;
  const delEl=pop.querySelector('.cal-pop-del');
  if(delEl)delEl.onclick=async e=>{
    e.stopPropagation();
    const raw=String(ev.id||'').replace(/^perso-/,'');
    if(!raw)return;
    try{
      await api('/api/calendrier/events/perso/'+encodeURIComponent(raw),{method:'DELETE'});
      closePop();
      showToast('Événement supprimé.','success');
      fetchEvents();
    }catch(err){
      showToast(err.message||'Suppression impossible','danger');
    }
  };
  if(isMobileViewport()){
    pop.classList.add('cal-pop--sheet');
  }else{
    const rect=anchorEl.getBoundingClientRect();
    let top=rect.bottom+8,left=rect.left;
    if(left+pop.offsetWidth>window.innerWidth-12)left=window.innerWidth-pop.offsetWidth-12;
    if(top+pop.offsetHeight>window.innerHeight-12)top=rect.top-pop.offsetHeight-8;
    pop.style.top=Math.max(8,top)+'px';
    pop.style.left=Math.max(8,left)+'px';
  }
  setTimeout(()=>{
    document.addEventListener('click',function h(e){
      if(!pop.contains(e.target)&&e.target!==anchorEl){
        closePop();
        document.removeEventListener('click',h);
      }
    });
  },0);
}

function onEvClick(ev,e){e.stopPropagation();openPop(ev,e.currentTarget);}

function renderCalendar(){
  S.feriesMap=buildFeriesMap();
  const p=getPeriod();
  document.getElementById('cal-title').textContent=p.title;
  const printTitle=document.getElementById('cal-print-title');
  if(printTitle)printTitle.textContent=p.title;
  const body=document.getElementById('cal-body');
  if(S.view==='month')body.innerHTML=renderMonth(p);
  else if(S.view==='week')body.innerHTML=renderTimeGrid(p,7);
  else if(S.view==='agenda')body.innerHTML=renderAgenda(p);
  else body.innerHTML=renderTimeGrid(p,1);
  bindRenderedEvents();
  bindCalendarBodyClicks();
  renderMiniCal();
}

function bindRenderedEvents(){
  document.querySelectorAll('[data-ev-id]').forEach(el=>{
    const id=el.dataset.evId;
    const ev=S.events.find(x=>x.id===id);
    if(ev)el.onclick=e=>onEvClick(ev,e);
  });
}

function eventsOnDay(day){
  const dk=ymd(day);
  return S.events.filter(ev=>{
    if(!evVisible(ev)||isFerieEvent(ev))return false;
    const s=evStart(ev),e=evEnd(ev);
    if(!s)return false;
    return ymd(startOfDay(s))<=dk&&ymd(startOfDay(e||s))>=dk;
  });
}
function ferieLabelForDay(day){
  return S.feriesMap[ymd(day)]||'';
}


function formatAgendaDayHeader(day){
  const s=day.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  return s.charAt(0).toUpperCase()+s.slice(1);
}
function agendaEventsOnDay(day){
  const dk=ymd(day);
  return S.events.filter(ev=>{
    if(!evVisible(ev))return false;
    const s=evStart(ev),e=evEnd(ev);
    if(!s)return false;
    if(ymd(startOfDay(s))>dk||ymd(startOfDay(e||s))<dk)return false;
    return true;
  }).sort((a,b)=>{
    if(!!a.all_day!==!!b.all_day)return a.all_day?-1:1;
    const sa=evStart(a),sb=evStart(b);
    if(!sa&&!sb)return 0;
    if(!sa)return 1;
    if(!sb)return -1;
    return sa.getTime()-sb.getTime();
  });
}
function evTimeLabelOnDay(ev,day){
  if(ev.all_day)return '';
  const s=evStart(ev);
  if(!s)return '';
  if(ymd(s)!==ymd(day))return '';
  return s.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
}
function renderAgenda(p){
  let cur=startOfDay(p.start);
  const end=startOfDay(p.end);
  let html='<div class="cal-agenda">';
  let any=false;
  while(cur<=end){
    const evs=agendaEventsOnDay(cur);
    if(evs.length){
      any=true;
      const today=isToday(cur);
      html+='<div class="cal-agenda-day">';
      html+='<div class="cal-agenda-day-head">';
      html+='<span class="cal-agenda-day-title">'+esc(formatAgendaDayHeader(cur))+'</span>';
      html+='<span class="cal-agenda-day-iso">S '+getISOWeek(cur)+'</span>';
      if(today)html+='<span class="cal-agenda-today">Aujourd\'hui</span>';
      html+='</div><div class="cal-agenda-evs">';
      evs.forEach(ev=>{
        const time=evTimeLabelOnDay(ev,cur);
        html+='<div class="cal-agenda-ev-row">';
        if(time)html+='<span class="cal-agenda-time">'+esc(time)+'</span>';
        html+='<div class="cal-pill" data-ev-id="'+esc(ev.id)+'" style="'+calSlotStyle(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
        html+='</div>';
      });
      html+='</div></div>';
    }
    cur=addDays(cur,1);
  }
  if(!any)html+='<p class="cal-agenda-empty">Aucun événement à venir.</p>';
  html+='</div>';
  return html;
}

function renderMonth(p){
  const weeks=[];
  let cur=startOfWeekMon(p.start);
  const end=p.end;
  while(cur<=end){
    const days=[];
    for(let i=0;i<7;i++)days.push(addDays(cur,i));
    weeks.push(days);
    cur=addDays(cur,7);
  }
  const month=S.anchor.getMonth();
  let html='<div class="cal-month"><div class="cal-month-head">';
  html+='<div class="cal-week-num-head"></div>';
  JOURS.forEach(j=>{html+='<div>'+j+'</div>';});
  html+='</div>';
  weeks.forEach(days=>{
    const isoW=getISOWeek(days[0]);
    html+='<div class="cal-week-row">';
    html+='<div class="cal-week-num">'+isoW+'</div>';
    html+='<div class="cal-week-inner">';
    html+=renderWeekBars(days);
    html+='<div class="cal-days">';
    days.forEach(day=>{
      const other=day.getMonth()!==month;
      const fl=ferieLabelForDay(day);
      const evs=eventsOnDay(day);
      const singles=evs.filter(e=>!isMultiDay(e));
      const show=singles.slice(0,3);
      const more=singles.length-show.length;
      html+='<div class="cal-day'+(other?' other':'')+(isToday(day)?' today':'')+(fl?' cal-day--ferie':'')+'" data-day="'+ymd(day)+'">';
      html+='<div class="cal-day-num">'+day.getDate()+'</div>';
      html+='<div class="cal-day-events">';
      show.forEach(ev=>{
        html+='<div class="cal-pill" data-ev-id="'+esc(ev.id)+'" style="'+calSlotStyle(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
      });
      if(more)html+='<div class="cal-more">+'+more+'</div>';
      html+='</div>';
      if(fl)html+='<div class="cal-day-ferie-label">'+esc(fl)+'</div>';
      html+='</div>';
    });
    html+='</div></div></div>';
  });
  html+='</div>';
  return html;
}

/** Colonnes côte à côte pour les événements qui se chevauchent (tranche du jour). */
function buildOverlapLayout(events,day){
  const items=[];
  for(const ev of events){
    const clip=evClipOnDay(ev,day);
    if(clip)items.push({ev,clip});
  }
  const layout=new Map();
  const n=items.length;
  if(!n)return layout;

  const parent=Array.from({length:n},(_,i)=>i);
  function find(i){return parent[i]===i?i:(parent[i]=find(parent[i]));}
  function unite(i,j){const ri=find(i),rj=find(j);if(ri!==rj)parent[ri]=rj;}

  for(let i=0;i<n;i++){
    for(let j=i+1;j<n;j++){
      if(clipsOverlap(items[i].clip,items[j].clip))unite(i,j);
    }
  }

  const groups=new Map();
  for(let i=0;i<n;i++){
    const r=find(i);
    if(!groups.has(r))groups.set(r,[]);
    groups.get(r).push(items[i]);
  }

  for(const group of groups.values()){
    group.sort((a,b)=>a.clip.start-b.clip.start||a.clip.end-b.clip.end);
    const colEnds=[];
    const placed=[];
    for(const it of group){
      let col=0;
      while(col<colEnds.length&&colEnds[col]>it.clip.start)col++;
      if(col===colEnds.length)colEnds.push(it.clip.end);
      else colEnds[col]=Math.max(colEnds[col],it.clip.end);
      placed.push({it,col});
    }
    const total=colEnds.length;
    for(const {it,col} of placed){
      layout.set(layoutKey(it.ev),{col,total});
    }
  }
  return layout;
}

function timedEvStyle(ev,top,h,col,total){
  const c=Number(col)||0;
  const t=Math.max(1,Number(total)||1);
  const pctW=(100/t).toFixed(4);
  const pctL=((c*100)/t).toFixed(4);
  const px=CAL_SLOT_PAD_X;
  const inset=px*2;
  return 'top:'+top+'px;height:'+h+'px;left:calc('+pctL+'% + '+px+'px);width:calc('+pctW+'% - '+inset+'px);'+
    'z-index:'+(1+c)+';'+calSlotStyle(ev.calendrier);
}

function renderDayTimedHtml(dayTimed,day,range){
  const layout=buildOverlapLayout(dayTimed,day);
  let html='';
  for(const ev of dayTimed){
    const slice=timedSliceOnDay(ev,day,range);
    if(!slice)continue;
    const lay=layout.get(layoutKey(ev))||{col:0,total:1};
    html+='<div class="cal-ev" data-ev-id="'+esc(ev.id)+'" data-col="'+lay.col+'" data-tot="'+lay.total+'" '+
      'style="'+timedEvStyle(ev,slice.top,slice.h,lay.col,lay.total)+'">'+esc(ev.titre)+'</div>';
  }
  return html;
}

function renderWeekBars(days){
  const dk0=ymd(days[0]),dk6=ymd(days[6]);
  const bars=S.events.filter(ev=>{
    if(!evVisible(ev)||isFerieEvent(ev)||!isMultiDay(ev))return false;
    const s=ymd(startOfDay(evStart(ev))),e=ymd(startOfDay(evEnd(ev)));
    return s<=dk6&&e>=dk0;
  });
  if(!bars.length)return '<div class="cal-week-bars"></div>';
  let html='<div class="cal-week-bars" style="grid-template-rows:repeat('+bars.length+',18px)">';
  bars.forEach((ev,ri)=>{
    const s=ymd(startOfDay(evStart(ev))),e=ymd(startOfDay(evEnd(ev)));
    let colStart=0,colEnd=0;
    for(let i=0;i<7;i++){
      const dk=ymd(days[i]);
      if(dk>=s&&dk<=e){
        if(!colStart)colStart=i+1;
        colEnd=i+1;
      }
    }
    if(!colStart)return;
    const span=colEnd-colStart+1;
    html+='<div class="cal-mbar" data-ev-id="'+esc(ev.id)+'" style="grid-column:'+colStart+' / span '+span+';grid-row:'+(ri+1)+';'+calSlotStyle(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
  });
  html+='</div>';
  return html;
}

function renderTimeGrid(p,colCount){
  const days=[];
  if(colCount===1)days.push(startOfDay(p.start));
  else{for(let i=0;i<7;i++)days.push(addDays(p.start,i));}
  const allDay=[];
  const timed=[];
  S.events.forEach(ev=>{
    if(!evVisible(ev)||isFerieEvent(ev))return;
    if(ev.all_day)allDay.push(ev);
    else timed.push(ev);
  });
  const range=colCount===1?getDayWindow(days[0]):weekTimeRange(days);
  const h0=Math.floor(range.hStart);
  const h1=Math.ceil(range.hEnd);
  const span=Math.max(1,h1-h0);
  const gridH=span*PX_PER_HOUR;
  let html='<div class="cal-time-wrap'+(colCount===1?' cal-day-single':'')+'">';
  html+='<div class="cal-time-gutter"><div style="height:32px;border-bottom:1px solid var(--border)"></div>';
  for(let h=h0;h<h1;h++)html+='<div class="tg-hour">'+pad2(h)+':00</div>';
  html+='</div><div class="cal-time-grid">';
  html+='<div class="cal-allday-row"><div class="cal-allday-label">Journée</div>';
  html+='<div class="cal-allday-cols" style="grid-template-columns:repeat('+colCount+',1fr)">';
  days.forEach((day,ci)=>{
    const dk=ymd(day);
    allDay.filter(ev=>{
      const s=ymd(startOfDay(evStart(ev))),e=ymd(startOfDay(evEnd(ev)));
      return s<=dk&&e>=dk;
    }).forEach(ev=>{
      html+='<div class="cal-allday-pill" data-ev-id="'+esc(ev.id)+'" style="'+calSlotStyle(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
    });
  });
  html+='</div></div>';
  html+='<div class="cal-cols-row" style="grid-template-columns:repeat('+colCount+',1fr)">';
  days.forEach(day=>{
    const fl=ferieLabelForDay(day);
    html+='<div class="cal-col'+(fl?' cal-col--ferie':'')+'"><div class="cal-col-head'+(isToday(day)?' today':'')+'">'+
      day.toLocaleDateString('fr-FR',{weekday:'short',day:'numeric',month:'short'})+'</div>';
    html+='<div class="cal-col-slots" data-day="'+ymd(day)+'" data-h-start="'+h0+'" data-h-end="'+h1+'" style="height:'+gridH+'px">';
    for(let h=h0;h<h1;h++)html+='<div class="cal-slot-line" style="top:'+((h-h0)*PX_PER_HOUR)+'px"></div>';
    html+=renderDayTimedHtml(timed.filter(ev=>evOverlapsDay(ev,day)),day,range);
    if(fl)html+='<div class="cal-col-ferie-label">'+esc(fl)+'</div>';
    html+='</div></div>';
  });
  html+='</div></div></div>';
  return html;
}

function setView(v,opts){
  if(!VALID_VIEWS.includes(v))v='month';
  S.view=v;
  if(v==='agenda'&&!(opts&&opts.skipAnchorReset))S.anchor=new Date();
  try{localStorage.setItem(LS_VIEW,v);}catch(e){}
  applyViewChrome(v);
  fetchEvents();
}

function shiftAnchor(delta){
  const a=new Date(S.anchor);
  if(S.view==='month')a.setMonth(a.getMonth()+delta);
  else if(S.view==='week')a.setDate(a.getDate()+delta*7);
  else if(S.view==='agenda')a.setDate(a.getDate()+delta*30);
  else a.setDate(a.getDate()+delta);
  S.anchor=a;
  fetchEvents();
}

document.getElementById('btn-prev').onclick=()=>shiftAnchor(-1);
document.getElementById('btn-next').onclick=()=>shiftAnchor(1);
document.getElementById('btn-today').onclick=()=>goToToday();
document.getElementById('btn-export-ics').onclick=()=>exportIcs();
document.getElementById('btn-print').onclick=()=>window.print();
document.querySelectorAll('.nav-btn[data-view],.cal-view-tabs .cal-btn[data-view]').forEach(b=>{
  b.onclick=()=>setView(b.dataset.view);
});
document.getElementById('sb-burger').onclick=()=>document.body.classList.toggle('sb-open');
document.getElementById('sb-ov').onclick=()=>document.body.classList.remove('sb-open');
document.getElementById('btn-theme').onclick=()=>{
  if(window.MySifaTheme)MySifaTheme.toggleMode();
  else{
    const next=document.body.classList.contains('light')?'dark':'light';
    localStorage.setItem('theme',next);
    document.body.classList.toggle('light',next==='light');
  }
  syncThemeBtn();
};
document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

document.addEventListener('keydown',e=>{
  if(isTypingTarget(document.activeElement))return;
  const k=e.key;
  if(k==='Escape'){
    if(S.pop){closePop();e.preventDefault();return;}
    if(S.createModal){closeCreateModal();e.preventDefault();return;}
    if(S.colorModal){closeCalColorModal();e.preventDefault();}
    return;
  }
  if(k==='t'||k==='T'){e.preventDefault();goToToday();return;}
  if(k==='ArrowLeft'){e.preventDefault();shiftAnchor(-1);return;}
  if(k==='ArrowRight'){e.preventDefault();shiftAnchor(1);return;}
  if(k==='m'||k==='M'){e.preventDefault();setView('month');return;}
  if(k==='w'||k==='W'){e.preventDefault();setView('week');return;}
  if(k==='d'||k==='D'){e.preventDefault();setView('day');return;}
  if(k==='a'||k==='A'){e.preventDefault();setView('agenda');return;}
});

function bootCalendrier(){
  S.view=loadSavedView();
  applyMobileDefaultView();
}

document.addEventListener('DOMContentLoaded',bootCalendrier);

(async function init(){
  try{
    bootCalendrier();
    applyTheme();
    loadVisible();
    applyCalListOpen(loadCalListOpen());
    const calHead=document.getElementById('cal-cals-head');
    if(calHead)calHead.addEventListener('click',toggleCalList);
    renderToggles();
    applyViewChrome(S.view);
    ME=await api('/api/auth/me');
    if(!ME){
      location.href='/?next=/calendrier';
      return;
    }
    if(window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    else if(window.MySifaCalendar)MySifaCalendar.mergeFromUser(ME);
    renderToggles();
    const chip=document.getElementById('sb-user-chip');
    if(chip&&window.MySifaUserChip){
      const editIco='<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
      MySifaUserChip.fill(chip,ME,{roleLabels:ROLE_LABELS,editIconHtml:editIco});
    }
    syncThemeBtn();
    bindCalendarBodyClicks();
    await fetchEvents();
  }catch(e){
    if(e.message!=='auth')showToast(e.message||'Initialisation impossible','danger');
  }
})();
</script>
</body>
</html>
"""
