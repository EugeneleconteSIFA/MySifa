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
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
/* tokens : static/mysifa_theme.css — ici, seulement les écarts */
:root{--ok:#34d399;--sur-accent:#0a0e17;}
body.light{--muted:#64748b;--ok:#059669;--sur-accent:#ffffff;}
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
/* Reunions : invites, reponses, evenement annule ou refuse. */
.cal-pop-reunion{margin-top:10px;padding-top:10px;border-top:1px solid var(--border)}
.cal-pop-reunion-head{font-size:11px;font-weight:700;color:var(--text2)}
.cal-pop-reunion-compte{font-size:11px;color:var(--muted);margin-top:2px}
.cal-pop-parts{list-style:none;margin:6px 0 0;padding:0;max-height:132px;overflow-y:auto}
.cal-pop-parts li{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2);padding:2px 0}
.cal-part-pastille{width:8px;height:8px;border-radius:50%;flex-shrink:0;background:var(--muted)}
.cal-part-pastille.st-accepte{background:var(--success)}
.cal-part-pastille.st-refuse{background:var(--danger)}
.cal-part-pastille.st-peut_etre{background:var(--warn)}
.cal-pop-reponse{display:flex;gap:6px;margin-top:10px}
.cal-rep-btn{flex:1;padding:7px 4px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text2);font-family:inherit;font-size:11px;font-weight:600;cursor:pointer;transition:border-color .15s,color .15s}
.cal-rep-btn:hover{border-color:var(--accent);color:var(--accent)}
.cal-rep-btn.actif{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.cal-prop{display:flex;gap:8px;align-items:flex-start;justify-content:space-between;
  margin-top:8px;padding:8px 9px;border:1px solid var(--border);border-radius:8px;background:var(--bg)}
.cal-prop-txt{font-size:11px;color:var(--text2);line-height:1.45}
.cal-prop-msg{color:var(--muted);margin-top:3px}
.cal-prop-actions{display:flex;gap:6px;flex-shrink:0}
.cal-prop-actions .cal-rep-btn{padding:5px 8px;font-size:10px;flex:none}
.cal-pop-annule{margin-top:10px;padding:7px 9px;border-radius:8px;background:rgba(248,113,113,.12);color:var(--danger);font-size:11px;font-weight:600}
/* Invites : la recherche seule, les personnes retenues en pastilles. */
.cal-part-box{position:relative}
.cal-part-res{position:absolute;left:0;right:0;top:calc(100% + 4px);z-index:20;max-height:184px;overflow-y:auto;
  border:1px solid var(--border);border-radius:8px;background:var(--card);box-shadow:0 12px 28px rgba(0,0,0,.28)}
.cal-part-res[hidden]{display:none}
.cal-part-row{display:flex;align-items:center;gap:8px;width:100%;padding:8px 10px;font-size:12px;color:var(--text2);
  background:transparent;border:none;font-family:inherit;text-align:left;cursor:pointer}
.cal-part-row:hover,.cal-part-row.actif{background:var(--accent-bg);color:var(--accent)}
.cal-part-row .cal-part-nom{flex:1}
.cal-part-occupe{font-size:10px;font-weight:700;color:var(--warn);text-transform:uppercase;letter-spacing:.6px}
.cal-part-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.cal-part-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 6px 4px 10px;border-radius:999px;
  border:1px solid var(--border);background:var(--bg);font-size:11px;color:var(--text2)}
.cal-part-chip.occupe{border-color:var(--warn);color:var(--warn)}
.cal-part-chip button{width:16px;height:16px;display:flex;align-items:center;justify-content:center;padding:0;
  border:none;border-radius:50%;background:transparent;color:inherit;font-size:13px;line-height:1;cursor:pointer}
.cal-part-chip button:hover{background:var(--border)}
.cal-part-dispo{font-size:11px;color:var(--muted);margin-top:6px;min-height:15px}
.cal-part-dispo.alerte{color:var(--warn)}
.cal-part-vide{padding:10px;font-size:11px;color:var(--muted)}
/* Repetition. */
.cal-recur-box{margin:-2px 0 10px;padding:9px;border:1px solid var(--border);border-radius:8px;background:var(--bg)}
.cal-recur-box[hidden]{display:none}
.cal-recur-row{display:flex;gap:10px;flex-wrap:wrap}
.cal-recur-row .cal-create-field{flex:1 1 140px;min-width:0;margin:0}
.cal-recur-hint{font-size:11px;color:var(--muted);margin:8px 0 0}
.cal-serie-choix{display:flex;gap:8px;margin:-2px 0 10px}
.cal-serie-choix label{flex:1;display:flex;align-items:center;gap:7px;padding:8px 10px;border:1px solid var(--border);
  border-radius:8px;background:var(--bg);font-size:12px;color:var(--text2);cursor:pointer}
.cal-serie-choix label:hover{border-color:var(--accent)}
.cal-serie-choix input{accent-color:var(--accent);flex-shrink:0}
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
.mobile-topbar{flex-shrink:0}
.cal-mobile-view-sel{margin-left:auto}
.cal-mobile-view-sel{
  display:none;flex:1;min-width:0;max-width:148px;margin-left:auto;
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:8px 32px 8px 12px;color:var(--text);font-size:12px;font-weight:600;
  font-family:inherit;cursor:pointer;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
}
.cal-mobile-view-sel:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
.cal-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:10px;padding:16px 20px;border-bottom:1px solid var(--border);background:var(--card);flex-shrink:0}
.cal-nav{display:flex;align-items:center;gap:8px}
.cal-btn{padding:8px 14px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,background .15s}
.cal-btn:hover{border-color:var(--accent);color:var(--accent)}
.cal-collegue-sel{padding:8px 10px;border-radius:10px;border:1px solid var(--border);
  background:var(--bg);color:var(--text2);font-size:12px;font-family:inherit;font-weight:600;
  max-width:190px;cursor:pointer}
.cal-collegue-sel:focus{border-color:var(--accent);outline:none}
.cal-collegue-sel.actif{border-color:var(--accent);color:var(--accent)}
@media print{.cal-collegue-sel{display:none}}
.cal-search-wrap{position:relative;min-width:190px}
.cal-search-wrap input{width:100%;padding:8px 12px;border-radius:10px;border:1px solid var(--border);
  background:var(--bg);color:var(--text);font-size:12px;font-family:inherit}
.cal-search-wrap input:focus{border-color:var(--accent);outline:none}
.cal-search-res{position:absolute;top:calc(100% + 5px);left:0;right:0;z-index:60;max-height:300px;
  overflow-y:auto;background:var(--card);border:1px solid var(--border);border-radius:10px;
  box-shadow:0 14px 34px rgba(0,0,0,.3)}
.cal-search-res[hidden]{display:none}
.cal-search-row{display:block;width:100%;text-align:left;padding:9px 11px;border:none;background:transparent;
  color:var(--text2);font-family:inherit;font-size:12px;cursor:pointer;border-bottom:1px solid var(--border)}
.cal-search-row:last-child{border-bottom:none}
.cal-search-row:hover{background:var(--accent-bg);color:var(--accent)}
.cal-search-row .cal-search-quand{display:block;font-size:10px;color:var(--muted);margin-top:2px}
.cal-search-row.barre .cal-search-titre{text-decoration:line-through;opacity:.7}
.cal-search-vide{padding:11px;font-size:11px;color:var(--muted)}
@media print{.cal-search-wrap{display:none}}
.cal-btn.primary{background:var(--accent);color:var(--sur-accent);border-color:var(--accent)}
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
.cal-agenda-day-empty{font-size:12px;color:var(--muted);font-style:italic;margin:0;padding:4px 0}
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
.cal-time-wrap{display:flex;flex-direction:column;min-width:640px;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--card)}
/* La gouttiere des heures vit sous le bandeau « Journee », dans la meme ligne
   que les colonnes : son entete fantome (.tg-head) a exactement la hauteur de
   l'entete de colonne, ce qui garantit que 06:00 tombe sur le trait de 06:00. */
.cal-time-body{display:flex;min-width:0}
.cal-time-gutter{width:48px;flex-shrink:0;border-right:1px solid var(--border);background:var(--bg)}
.cal-time-gutter .tg-head{color:transparent;user-select:none;pointer-events:none}
.cal-time-gutter .tg-hour{height:48px;font-size:10px;color:var(--muted);text-align:right;padding:4px 6px;border-top:1px solid var(--border)}
.cal-time-gutter .tg-hour:first-child{border-top:none}
.cal-time-grid{flex:1;display:flex;flex-direction:column;min-width:0}
.cal-allday-row{display:flex;border-bottom:1px solid var(--border);min-height:32px;background:rgba(15,23,42,.35)}
body.light .cal-allday-row{background:#f8fafc}
.cal-allday-label{width:48px;flex-shrink:0;font-size:9px;font-weight:700;color:var(--muted);display:flex;align-items:center;justify-content:flex-end;padding:4px;border-right:1px solid var(--border)}
.cal-allday-cols{flex:1;display:grid;position:relative;min-height:28px}
.cal-allday-cell{min-width:0;display:flex;flex-direction:column;justify-content:center;
  border-left:1px solid var(--border);padding:1px 0}
.cal-allday-cell:first-child{border-left:none}
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
/* Contenu d'un creneau : titre, puis lignes secondaires que renderDayTimedHtml
   n'ajoute que si la hauteur le permet. */
.cal-ev-t{display:block;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cal-ev-l{display:block;font-weight:600;font-size:9px;line-height:1.35;opacity:.72;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:1px}
.cal-ev-flag{display:inline-flex;align-items:center;justify-content:center;width:13px;height:13px;
  margin-right:4px;border-radius:50%;background:rgba(10,14,23,.2);color:inherit;
  font-size:9px;font-weight:800;line-height:1;vertical-align:1px;flex-shrink:0}
.cal-ev-flag--peut{background:rgba(10,14,23,.34)}
.cal-pill--agenda{display:flex;flex-direction:column;align-items:flex-start;white-space:normal}
.cal-pill-sec{display:block;font-size:9px;font-weight:600;opacity:.72;margin-top:1px}
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
.cal-settings-section{margin-top:16px;padding-top:14px;border-top:1px solid var(--border)}
.cal-settings-section-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:10px}
.cal-settings-export-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.cal-settings-hint{font-size:11px;color:var(--muted);margin:8px 0 0;line-height:1.5}
.cal-create-modal-backdrop{position:fixed;inset:0;z-index:8600;background:rgba(0,0,0,.55);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;padding:16px}
.cal-create-modal{
  position:relative;width:100%;max-width:440px;max-height:92vh;
  overflow-y:auto;overflow-x:hidden;
  background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 18px 16px;
  box-shadow:0 16px 48px rgba(0,0,0,.45);
}
/* Formulaire d'evenement : deux colonnes des qu'il y a la place, pour que le
   creneau, les invites et la repetition tiennent dans un ecran sans defilement. */
.cal-create-modal--large{max-width:780px;padding:16px 18px 14px}
.cal-create-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:0 20px;align-items:start}
@media(max-width:780px){
  .cal-create-grid{grid-template-columns:1fr}
  .cal-create-modal--large{max-width:440px}
}
@media(max-height:640px){
  .cal-create-modal--large .cal-create-field textarea{min-height:52px}
}
.cal-create-modal h2{font-size:15px;font-weight:800;margin:0 0 12px;color:var(--text)}
.cal-create-field{margin-bottom:10px}
.cal-create-field label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px}
.cal-create-field input[type=text],.cal-create-field input[type=date],.cal-create-field input[type=datetime-local],.cal-create-field select,.cal-create-field textarea{
  width:100%;min-width:0;background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;color:var(--text);font-size:14px;font-family:inherit;transition:border-color .15s;
}
.cal-create-field input:focus,.cal-create-field select:focus,.cal-create-field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none}
.cal-create-field textarea{min-height:60px;resize:vertical}
.cal-create-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px}
@media(max-width:520px){.cal-create-row{grid-template-columns:1fr}}
.cal-create-toggle{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text2);cursor:pointer;user-select:none;margin-bottom:12px}
.cal-create-toggle input{width:16px;height:16px;accent-color:var(--accent)}
.cal-create-modal-foot{display:flex;gap:10px;justify-content:flex-end;margin-top:6px}
.cal-create-modal-foot .cal-btn{min-width:96px}
.cal-create-modal-close{
  position:absolute;top:10px;right:12px;border:none;background:transparent;color:var(--muted);
  cursor:pointer;font-size:20px;line-height:1;padding:4px;
}
.cal-create-modal-close:hover{color:var(--text)}
.cal-day[data-day]{cursor:pointer}
.cal-col-slots[data-day]{cursor:pointer}
/* Trace de selection pendant qu'on tire un nouveau creneau sur la grille. */
.cal-ghost{position:absolute;left:2px;right:2px;border-radius:6px;pointer-events:none;
  background:var(--accent-bg);border:1px dashed var(--accent);color:var(--accent);
  font-size:10px;font-weight:700;padding:3px 6px;overflow:hidden;z-index:3}
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
  .cal-mobile-view-sel{display:block}
  .mobile-topbar-sub{display:none}
  .cal-view-tabs,.cal-shortcuts-wrap{display:none!important}
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  body.has-topbar .main{padding-top:74px}
  .cal-title{font-size:14px;min-width:120px}
}
@media(max-width:767px){
  .cal-toolbar{flex-wrap:nowrap;align-items:center;gap:8px;padding:12px 14px}
  .cal-nav{display:contents}
  .cal-nav #btn-export-ics,.cal-nav #btn-print{display:none!important}
  #btn-prev{order:1;padding:8px 10px;min-width:36px;font-size:16px}
  #btn-next{order:3;padding:8px 10px;min-width:36px;font-size:16px}
  .cal-title{order:2;flex:1;min-width:0;font-size:12px;text-align:center;line-height:1.3}
  #btn-today{order:4;padding:8px 10px;font-size:11px;white-space:nowrap}
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
/* --- Edition des creneaux personnels (drag & drop / etirement) --- */
.cal-ev--own,.cal-pill--own,.cal-mbar--own,.cal-allday-pill--own{cursor:grab}
.cal-ev--own:active,.cal-pill--own:active,.cal-mbar--own:active{cursor:grabbing}
.cal-pill,.cal-mbar,.cal-allday-pill{position:relative}
.cal-ev-rs{position:absolute;left:0;right:0;height:7px;cursor:ns-resize;z-index:3}
.cal-ev-rs-top{top:-1px}
.cal-ev-rs-bot{bottom:-1px}
.cal-ev-rs::after{content:'';position:absolute;left:50%;transform:translateX(-50%);width:22px;height:2px;border-radius:2px;background:rgba(10,14,23,.4);opacity:0;transition:opacity .12s}
.cal-ev-rs-top::after{top:2px}
.cal-ev-rs-bot::after{bottom:2px}
.cal-ev--own:hover .cal-ev-rs::after{opacity:1}
.cal-rs-x{position:absolute;top:0;bottom:0;right:-1px;width:8px;cursor:ew-resize;z-index:3}
.cal-ev--dragging,.cal-pill--dragging,.cal-mbar--dragging,.cal-allday-pill--dragging{opacity:.78;box-shadow:0 6px 18px rgba(0,0,0,.35);pointer-events:none}
body.cal-dragging{user-select:none}
.cal-drag-badge{position:fixed;z-index:9000;pointer-events:none;background:var(--card);border:1px solid var(--accent);color:var(--text);font-size:11px;font-weight:700;padding:5px 9px;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.35);white-space:nowrap}
.cal-ev--busy,.cal-pill--busy,.cal-allday-pill--busy,.cal-mbar--busy{background-image:repeating-linear-gradient(45deg,rgba(10,14,23,.16) 0 5px,transparent 5px 10px)}
/* --- Calendriers externes --- */
.cal-extern-btn{display:flex;align-items:center;gap:8px;width:100%;margin-top:6px;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,border-color .15s}
.cal-extern-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.cal-cals-section.collapsed #btn-cal-extern{display:none}
.cal-create-modal--lg{max-width:580px}
.cal-extern-sec{margin-top:18px;padding-top:14px;border-top:1px solid var(--border)}
.cal-extern-sec.first{margin-top:0;padding-top:0;border-top:none}
.cal-extern-h{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin:0 0 8px}
.cal-extern-p{font-size:12px;color:var(--text2);line-height:1.6;margin:0 0 10px}
.cal-extern-hint{font-size:11px;color:var(--muted);line-height:1.6;margin:8px 0 0}
.cal-feed-cals{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.cal-feed-cal{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border:1px solid var(--border);border-radius:999px;background:var(--bg);font-size:11px;font-weight:600;color:var(--text2);cursor:pointer;user-select:none;transition:border-color .15s,color .15s}
.cal-feed-cal:hover{border-color:var(--accent);color:var(--accent)}
.cal-feed-cal input{width:14px;height:14px;accent-color:var(--accent);cursor:pointer;margin:0}
.cal-feed-cal .cal-dot{width:8px;height:8px}
.cal-url-row{display:flex;gap:8px;align-items:center}
.cal-url-row input{flex:1;min-width:0;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:9px 11px;color:var(--text2);font-size:11px;font-family:monospace}
.cal-sub-row{display:flex;align-items:center;gap:9px;padding:9px 10px;border:1px solid var(--border);border-radius:10px;background:var(--bg);margin-bottom:8px}
.cal-sub-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.cal-sub-main{flex:1;min-width:0}
.cal-sub-nom{font-size:12px;font-weight:700;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cal-sub-meta{font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cal-sub-meta.err{color:var(--danger)}
.cal-mini-btn{border:1px solid var(--border);background:var(--card);color:var(--text2);border-radius:8px;padding:5px 9px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;flex-shrink:0;transition:border-color .15s,color .15s}
.cal-mini-btn:hover{border-color:var(--accent);color:var(--accent)}
.cal-mini-btn.danger:hover{border-color:var(--danger);color:var(--danger)}
.cal-extern-form{display:grid;grid-template-columns:1fr 120px;gap:8px;margin-top:10px}
.cal-extern-form input[type=text],.cal-extern-form input[type=url]{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:9px 11px;color:var(--text);font-size:13px;font-family:inherit;min-width:0}
.cal-extern-form input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);outline:none}
.cal-extern-form .full{grid-column:1 / -1}
.cal-extern-form input[type=color]{width:100%;height:38px;border:1px solid var(--border);border-radius:10px;background:var(--bg);padding:3px;cursor:pointer}
</style>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_favicon_badge.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_calendar.js"></script>
<script>window.__MYSIFA_APP__='calendrier';</script>
<link rel="stylesheet" href="/static/mysifa_dock.css?v=2">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<link rel="stylesheet" href="/static/mysifa_cmdk.css">
<script src="/static/mysifa_dock.js"></script>
<script src="/static/mysifa_postit.js"></script>
<script src="/static/mysifa_cmdk.js"></script>
<script src="/static/mysifa_ai_chat.js"></script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=11"></script>
<script src="/static/chat_widget_v2.js?v=9"></script>
<script src="/static/mysifa_cal_rappel.js?v=8"></script>
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
      <div id="cal-toggles-mien"></div>
      <button type="button" class="cal-cals-head" id="cal-cals-head" aria-expanded="false" aria-controls="cal-toggles">
        <span class="cal-cals-head-label">Autres calendriers</span>
        <svg class="cal-cals-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div id="cal-toggles"></div>
      <button type="button" class="cal-extern-btn" id="btn-cal-extern" title="Connecter un calendrier externe">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
        Calendriers externes
      </button>
      <button type="button" class="cal-extern-btn" id="btn-cal-deleg" title="Qui peut écrire dans mon calendrier">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Délégations
      </button>
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
    <div class="mobile-topbar mobile-topbar--home-end">
      <button type="button" class="mobile-menu-btn" id="sb-burger" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">Calendrier</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Vue agenda</div>
      </div>
      <select id="mobile-view-sel" class="cal-mobile-view-sel" aria-label="Vue du calendrier">
        <option value="month">Mois</option>
        <option value="week">Semaine</option>
        <option value="day">Jour</option>
        <option value="agenda" selected>Agenda</option>
      </select>
      <button type="button" class="mobile-home-btn" onclick="window.location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>
    <div class="cal-toolbar">
      <div class="cal-nav">
        <button type="button" class="cal-btn" id="btn-prev" title="Période précédente" aria-label="Période précédente">‹</button>
        <button type="button" class="cal-btn primary" id="btn-today">Aujourd'hui</button>
        <button type="button" class="cal-btn" id="btn-next" title="Période suivante" aria-label="Période suivante">›</button>
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
      <select id="cal-collegue" class="cal-collegue-sel" aria-label="Voir l'agenda d'un collègue">
        <option value="">Tous les collègues</option>
      </select>
      <div class="cal-search-wrap">
        <input type="search" id="cal-search" placeholder="Rechercher un événement…"
          autocomplete="off" aria-label="Rechercher un événement">
        <div class="cal-search-res" id="cal-search-res" hidden></div>
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
<div id="cal-extern-modal-root"></div>
<div id="cal-deleg-modal-root"></div>
<script>
const USER_ROLE=__USER_ROLE__;
const CAL_DEFS=window.MySifaCalendar?MySifaCalendar.CAL_DEFS:[];
const CAL_IDS_FULL=CAL_DEFS.map(c=>c.id);
const CAL_IDS_ADMIN=['conges','anniversaires','feries','paie','expeditions','perso','collegues'];
const CAL_IDS_BASIC=['conges','feries','perso','collegues'];
function calIdsForRole(role){
  if(role==='superadmin'||role==='direction')return CAL_IDS_FULL;
  if(role==='administration'||role==='administration_ventes'||role==='administration_technique')return CAL_IDS_ADMIN;
  return CAL_IDS_BASIC;
}
function accessibleCalDefs(){
  const allowed=new Set(calIdsForRole(USER_ROLE));
  return CAL_DEFS.filter(c=>allowed.has(c.id)||c.externe);
}
function isSubCal(id){return /^sub_\d+$/.test(String(id||''));}
function calDefsMien(){return accessibleCalDefs().filter(c=>c.mien===true);}
function calDefsAutres(){return accessibleCalDefs().filter(c=>c.mien!==true);}
function isOwnPerso(ev){
  return !!(ev&&ev.calendrier==='perso'&&ev.meta&&ev.meta.own===true);
}
function isBusyPerso(ev){
  return !!(ev&&ev.calendrier==='collegues'&&ev.meta&&ev.meta.prive===true);
}
function isCreneauHumain(ev){
  return !!(ev&&(ev.calendrier==='perso'||ev.calendrier==='collegues'));
}
/* Une reunion refusee ou annulee reste au calendrier, mais grisee et barree :
   elle ne doit plus se lire comme un engagement. */
function evEstBarre(ev){
  const m=(ev&&ev.meta)||{};
  return !!(m.annule||m.mon_statut==='refuse');
}
const STATUT_LABEL={accepte:'Accepter',peut_etre:'Peut-être',refuse:'Refuser'};
const RAPPELS=[
  {v:'',l:'Par défaut (10 min avant)'},
  {v:'0',l:'Aucun rappel'},
  {v:'5',l:'5 minutes avant'},
  {v:'10',l:'10 minutes avant'},
  {v:'15',l:'15 minutes avant'},
  {v:'30',l:'30 minutes avant'},
  {v:'60',l:'1 heure avant'},
  {v:'120',l:'2 heures avant'},
  {v:'1440',l:'La veille'},
];
const EMAIL_RE=/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;
const STATUT_MOT={accepte:'accepté',peut_etre:'peut-être',refuse:'refusé',en_attente:'en attente'};
const ICO_CAL_GEAR='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
const LS_VISIBLE='mysifa_cal_visible_v2';
const LS_CAL_LIST='mysifa_cal_autres_open';
const LS_COLLEGUE='mysifa_cal_collegue';
const MOIS=['','janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
const JOURS=['lun','mar','mer','jeu','ven','sam','dim'];
const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};

const PX_PER_HOUR=48;
const CAL_SLOT_PAD_X=3;
const DEFAULT_DAY_WIN={hStart:5,hEnd:21};
const LS_VIEW='mysifa_cal_view';
const VALID_VIEWS=['month','week','day','agenda'];
const MINI_DOW=['L','M','M','J','V','S','D'];
const MOBILE_BREAKPOINT=900;
let S={view:'month',anchor:new Date(),events:[],dayWindows:{},feriesMap:{},loading:false,visible:{},pop:null,colorModal:null,createModal:null,externModal:null,miniCalY:null,miniCalM:null,_touchStartX:null,_touchStartY:null,subs:[],feed:null,drag:null,editingEv:null,lienDirect:null,collegue:'',_suppressClickUntil:0,_clickTimer:null,invitables:null,partSel:null,partNoms:null,partExt:null,partOccupes:null,_partTimer:null,delegations:null};
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
  if(isMobileViewport())return 'agenda';
  if(hasSavedView()){
    try{
      const v=localStorage.getItem(LS_VIEW);
      if(VALID_VIEWS.includes(v))return v;
    }catch(e){}
  }
  return 'month';
}
function applyMobileDefaultView(){
  if(isMobileViewport()){
    S.view='agenda';
    S.anchor=new Date();
  }
}
function applyViewChrome(v){
  document.querySelectorAll('.nav-btn[data-view]').forEach(b=>{
    b.classList.toggle('active',b.dataset.view===v);
  });
  document.querySelectorAll('.cal-view-tabs .cal-btn[data-view]').forEach(b=>{
    b.classList.toggle('primary',b.dataset.view===v);
  });
  const msel=document.getElementById('mobile-view-sel');
  if(msel&&msel.value!==v)msel.value=v;
  const subs={month:'Vue mensuelle',week:'Vue hebdomadaire',day:'Vue journalière',agenda:'Vue agenda'};
  const sub=document.getElementById('mobile-sub');
  if(sub&&!isMobileViewport())sub.textContent=subs[v]||'';
}
function formatAgendaPeriodTitle(start,end){
  const d0=start.getDate(),d1=end.getDate();
  const m0=MOIS[start.getMonth()+1],m1=MOIS[end.getMonth()+1];
  const y0=start.getFullYear(),y1=end.getFullYear();
  if(y0===y1&&start.getMonth()===end.getMonth())return d0+' — '+d1+' '+m1+' '+y1;
  if(y0===y1)return d0+' '+m0+' — '+d1+' '+m1+' '+y1;
  return d0+' '+m0+' '+y0+' — '+d1+' '+m1+' '+y1;
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

function calDefautVisible(c){
  if(window.MySifaCalendar&&MySifaCalendar.visibleParDefaut)return MySifaCalendar.visibleParDefaut(c.id);
  return c.defaut!==false;
}
/* Les plannings machines, la paie et les expeditions sont decoches a la
   premiere ouverture. La cle localStorage est versionnee : sans cela, un poste
   qui avait deja une preference enregistree n'aurait jamais vu le nouveau
   defaut s'appliquer. */
function loadVisible(){
  accessibleCalDefs().forEach(c=>{S.visible[c.id]=calDefautVisible(c);});
  try{
    const raw=localStorage.getItem(LS_VISIBLE);
    if(raw){
      const o=JSON.parse(raw);
      if(o&&typeof o==='object'){
        // On reprend toutes les cles memorisees, y compris les calendriers
        // externes (sub_N) qui ne sont charges qu'apres cet appel.
        Object.keys(o).forEach(k=>{
          if(typeof o[k]==='boolean')S.visible[k]=o[k];
        });
      }
    }
  }catch(e){}
}
function saveVisible(){
  try{localStorage.setItem(LS_VISIBLE,JSON.stringify(S.visible));}catch(e){}
}

function loadCalListOpen(){
  try{return localStorage.getItem(LS_CAL_LIST)==='1';}catch(e){return false;}
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

function calDefById(calId){
  return accessibleCalDefs().find(c=>c.id===calId)||null;
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
function openCalSettingsModal(calId){
  if(isSubCal(calId)){openExternModal();return;}
  closeCalColorModal();
  const root=document.getElementById('cal-color-modal-root');
  if(!root||!window.MySifaCalendar)return;
  const c=calDefById(calId);
  if(!c)return;
  const col=(MySifaCalendar.loadColorsMap()[c.id]||c.color);
  const period=getPeriod();
  const wrap=document.createElement('div');
  wrap.className='cal-color-modal-backdrop';
  wrap.innerHTML=`<div class="cal-color-modal" role="dialog" aria-labelledby="cal-settings-title">
    <button type="button" class="cal-color-modal-close" aria-label="Fermer" onclick="closeCalColorModal()">×</button>
    <h2 id="cal-settings-title">${esc(c.label)}</h2>
    <p class="cal-color-modal-desc">Couleur d'affichage et export des événements de ce calendrier.</p>
    <div class="cal-color-row" id="cal-mrow-${esc(c.id)}">
      <span class="cal-color-dot" style="background:${esc(col)}"></span>
      <span class="cal-color-label">Couleur</span>
      <input type="color" value="${esc(col)}" aria-label="Couleur ${esc(c.label)}"
        oninput="onCalColorModalInput('${esc(c.id)}',this.value)">
      <button type="button" class="cal-color-reset" onclick="resetCalColorModal('${esc(c.id)}')">Défaut</button>
    </div>
    <div class="cal-settings-section">
      <div class="cal-settings-section-label">Export</div>
      <div class="cal-settings-export-row">
        <button type="button" class="cal-btn" onclick="exportCalIcs('${esc(c.id)}')">Exporter .ics</button>
      </div>
      <p class="cal-settings-hint">Période affichée : ${esc(period.title)}</p>
    </div>
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
}
function calToggleHtml(c){
  return `<label class="cal-toggle" style="--cal-c:${calColor(c.id)}">
      <span class="cal-dot"></span>
      <span class="flex1">${esc(c.label)}</span>
      <button type="button" class="cal-gear-btn" title="Réglages du calendrier" aria-label="Réglages ${esc(c.label)}"
        onclick="event.preventDefault();event.stopPropagation();openCalSettingsModal('${esc(c.id)}')">${ICO_CAL_GEAR}</button>
      <input type="checkbox" data-cal="${c.id}" ${S.visible[c.id]?'checked':''}>
    </label>`;
}
/* « Mon calendrier » reste toujours visible en tete ; tout le reste vit sous le
   chevron « Autres calendriers ». */
function renderToggles(){
  const mien=document.getElementById('cal-toggles-mien');
  const box=document.getElementById('cal-toggles');
  if(mien)mien.innerHTML=calDefsMien().map(calToggleHtml).join('');
  if(box)box.innerHTML=calDefsAutres().map(calToggleHtml).join('');
  [mien,box].forEach(el=>{
    if(!el)return;
    el.querySelectorAll('input[data-cal]').forEach(inp=>{
      inp.onchange=()=>{
        S.visible[inp.dataset.cal]=inp.checked;
        saveVisible();
        fetchEvents();
      };
    });
  });
}

function activeCalList(){
  return accessibleCalDefs().filter(c=>S.visible[c.id]).map(c=>c.id);
}
function exportIcsUrl(dateStart,dateEnd,calIds){
  const q=new URLSearchParams({
    date_debut:ymd(dateStart),
    date_fin:ymd(dateEnd),
    calendriers:calIds.join(',')
  });
  return '/api/calendrier/export.ics?'+q;
}
function exportCalIcs(calId){
  if(!calDefById(calId)){showToast('Calendrier introuvable.','danger');return;}
  const p=getPeriod();
  window.location.href=exportIcsUrl(p.start,p.end,[calId]);
}
function exportIcs(){
  const p=getPeriod();
  const cals=activeCalList();
  if(!cals.length){showToast('Aucun calendrier sélectionné.','danger');return;}
  window.location.href=exportIcsUrl(p.start,p.end,cals);
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
function slotStyleFromColor(fill){
  if(String(fill).indexOf('var(')===0)return 'background:'+fill+';border-color:var(--border)';
  return 'background:'+fill+';border-color:'+darkenHex(fill);
}
function calSlotStyle(calId){
  return slotStyleFromColor(calColor(calId));
}
/* Une couleur stable par utilisateur : l'angle d'or sur l'id garantit des
   teintes bien réparties, identiques sur tous les postes, sans réglage. */
const PERSON_HUE_STEP=137.508;
const PERSON_SAT=62;
const PERSON_LUM=82;
function hslToHex(h,s,l){
  s=s/100;l=l/100;
  const k=n=>(n+h/30)%12;
  const a=s*Math.min(l,1-l);
  const f=n=>l-a*Math.max(-1,Math.min(k(n)-3,Math.min(9-k(n),1)));
  const to=x=>pad2(Math.round(255*x).toString(16));
  return '#'+to(f(0))+to(f(8))+to(f(4));
}
function relLum(hex){
  const v=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255)
    .map(x=>x<=0.03928?x/12.92:Math.pow((x+0.055)/1.055,2.4));
  return 0.2126*v[0]+0.7152*v[1]+0.0722*v[2];
}
const SLOT_TEXT_LUM=relLum('#0a0e17');
const SLOT_MIN_CONTRAST=4.6;
/* Le libellé d'un créneau est écrit en #0a0e17 : on éclaircit la teinte
   jusqu'à repasser au-dessus du seuil de contraste AA. */
function personColor(userId){
  const id=parseInt(userId,10);
  if(!id)return calColor('perso');
  const hue=(id*PERSON_HUE_STEP)%360;
  let l=PERSON_LUM;
  let hex=hslToHex(hue,PERSON_SAT,l);
  while(l<92&&(relLum(hex)+0.05)/(SLOT_TEXT_LUM+0.05)<SLOT_MIN_CONTRAST){
    l+=3;
    hex=hslToHex(hue,PERSON_SAT,l);
  }
  return hex;
}
/* Un « ? » sur les invitations sans reponse ou repondues « peut-etre » :
   le coup d'oeil au planning doit suffire a voir ce qui reste a trancher. */
function evFlagHtml(ev){
  const st=(ev&&ev.meta&&ev.meta.mon_statut)||'';
  if(st==='en_attente')
    return '<span class="cal-ev-flag" title="Invitation sans réponse">?</span>';
  if(st==='peut_etre')
    return '<span class="cal-ev-flag cal-ev-flag--peut" title="Vous avez répondu « peut-être »">?</span>';
  return '';
}
function evDureeTxt(ev){
  const s=evStart(ev),e=evEnd(ev);
  if(!s||!e)return '';
  const min=Math.round((e-s)/60000);
  if(min<=0)return '';
  const h=Math.floor(min/60),m=min%60;
  return (h?h+' h':'')+(m?(h?' ':'')+m+' min':'');
}
function evAuteurTxt(ev){
  const meta=(ev&&ev.meta)||{};
  if(meta.cree_par_nom)return meta.cree_par_nom;
  if(meta.organisateur_nom&&meta.own===false)return meta.organisateur_nom;
  return '';
}
function evParticipantsTxt(ev){
  const meta=(ev&&ev.meta)||{};
  const parts=(meta.participants||[]).concat(meta.invites_externes||[]);
  if(!parts.length)return '';
  const noms=parts.slice(0,3)
    .map(p=>String(p.nom||p.email||'').split(/[\s@]/)[0])
    .filter(Boolean);
  return noms.join(', ')+(parts.length>3?' +'+(parts.length-3):'');
}
/* Les lignes secondaires n'apparaissent que si le creneau est assez haut :
   ecrire par-dessus un creneau de 20 minutes le rendrait illisible. */
function evLignesHtml(ev,hPx){
  let out='';
  if(hPx>=34){
    const duree=evDureeTxt(ev);
    const s=evStart(ev);
    const heure=s?(pad2(s.getHours())+':'+pad2(s.getMinutes())):'';
    const txt=[heure,duree].filter(Boolean).join(' · ');
    if(txt)out+='<span class="cal-ev-l">'+esc(txt)+'</span>';
  }
  if(hPx>=48){
    const auteur=evAuteurTxt(ev);
    if(auteur)out+='<span class="cal-ev-l">Par '+esc(auteur)+'</span>';
    else if(ev.meta&&ev.meta.lieu)out+='<span class="cal-ev-l">'+esc(ev.meta.lieu)+'</span>';
  }
  if(hPx>=64){
    const parts=evParticipantsTxt(ev);
    if(parts)out+='<span class="cal-ev-l">'+esc(parts)+'</span>';
  }
  return out;
}

function evSlotStyle(ev){
  const base=(isCreneauHumain(ev)&&ev.meta&&ev.meta.user_id)
    ?personColor(ev.meta.user_id)
    :calColor(ev&&ev.calendrier);
  // Refusee ou annulee : la teinte reste (on reconnait le calendrier) mais
  // s'efface, et le libelle est barre. Un aplat gris disparaissait en sombre.
  if(evEstBarre(ev)){
    return slotStyleFromColor(base)+';opacity:.42;text-decoration:line-through';
  }
  return slotStyleFromColor(base);
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
    return{start,end,title:formatAgendaPeriodTitle(start,end)};
  }
  const d=startOfDay(a);
  return{start:d,end:d,title:d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'})};
}

/* « Agenda de X » : on garde son calendrier et ceux qu'on a coches, mais parmi
   les collegues on ne montre plus que la personne demandee. */
function evVisible(ev){
  if(!S.visible[ev.calendrier])return false;
  if(S.collegue&&ev.calendrier==='collegues'){
    return String((ev.meta&&ev.meta.user_id)||'')===String(S.collegue);
  }
  return true;
}
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
    consommerLienDirect();
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
  if(typeof opts.hourFin==='number'&&opts.hourFin>h){
    // Creneau trace a la souris sur la grille : on respecte la hauteur tiree.
    end.setHours(Math.floor(opts.hourFin),Math.round((opts.hourFin%1)*60),0,0);
  }else{
    end.setHours(start.getHours()+1);
  }
  return{debut:toDatetimeLocalValue(start),fin:toDatetimeLocalValue(end),all_day:false};
}
function closeCreateModal(){
  if(S.createModal){S.createModal.remove();S.createModal=null;}
  S.editingEv=null;
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
  const prive=!!document.getElementById('cp-prive')?.checked;
  const participants=S.partSel?Array.from(S.partSel):[];
  const invites_externes=S.partExt?Array.from(S.partExt):[];
  const lieu=(document.getElementById('cp-lieu')?.value||'').trim()||null;
  const visio=(document.getElementById('cp-visio')?.value||'').trim()||null;
  const rappelBrut=document.getElementById('cp-rappel')?.value;
  const rappel_minutes=(rappelBrut===''||rappelBrut==null)?null:parseInt(rappelBrut,10);
  const auNomDe=document.getElementById('cp-au-nom-de')?.value;
  const au_nom_de=auNomDe?parseInt(auNomDe,10):null;
  const recurOn=!!document.getElementById('cp-recur')?.checked;
  const recurrence=recurOn?(document.getElementById('cp-recur-regle')?.value||'hebdo'):null;
  const recurrence_fin=recurOn?(document.getElementById('cp-recur-fin')?.value||null):null;
  const radioSerie=document.querySelector('input[name="cp-serie"]:checked');
  const serie=!!(radioSerie&&radioSerie.value==='1');
  return{titre,date_debut,date_fin,all_day,note,prive,participants,invites_externes,
         lieu,visio,rappel_minutes,au_nom_de,recurrence,recurrence_fin,serie};
}
function persoRawId(ev){return String((ev&&ev.id)||'').replace(/^perso-/,'');}
function openEditModal(ev){
  if(!isOwnPerso(ev))return;
  openPersoModal({ev});
}
function openPersoModal(opts){
  closeCreateModal();
  closePop();
  const root=document.getElementById('cal-create-modal-root');
  if(!root)return;
  const ev=(opts&&opts.ev)||null;
  const edit=!!ev;
  let allDay,debut,fin,titre,note,prive,lieu,visio,rappel;
  if(edit){
    allDay=!!ev.all_day;
    debut=String(ev.debut||'').slice(0,16);
    fin=String(ev.fin||'').slice(0,16);
    titre=(ev.meta&&ev.meta.titre_brut)||ev.titre||'';
    note=(ev.meta&&ev.meta.note)||'';
    prive=!!(ev.meta&&ev.meta.prive);
    lieu=(ev.meta&&ev.meta.lieu)||'';
    visio=(ev.meta&&ev.meta.visio)||'';
    rappel=(ev.meta&&ev.meta.rappel_minutes!=null)?String(ev.meta.rappel_minutes):'';
  }else{
    const defs=defaultPersoRange(opts||{});
    allDay=defs.all_day;debut=defs.debut;fin=defs.fin;titre='';note='';prive=false;
    lieu='';visio='';rappel='';
  }
  S.editingEv=ev;
  S.partSel=new Set(((edit&&ev.meta&&ev.meta.participants)||[]).map(p=>Number(p.user_id)));
  S.partNoms=new Map(((edit&&ev.meta&&ev.meta.participants)||[])
    .map(p=>[Number(p.user_id),String(p.nom||'')]));
  S.partExt=new Set(((edit&&ev.meta&&ev.meta.invites_externes)||[]).map(p=>String(p.email||'')));
  S.partOccupes=new Set();
  const dejaReunion=!!(edit&&ev.meta&&ev.meta.reunion);
  const serieId=(edit&&ev.meta&&ev.meta.serie_id)||'';
  // Trois mois de répétition par défaut : assez pour une réunion hebdo, assez
  // court pour ne pas remplir le calendrier de quelqu'un jusqu'en 2028.
  const finRecurDefaut=(function(){
    const d=new Date((debut||'').slice(0,10)||Date.now());
    d.setMonth(d.getMonth()+3);
    return ymd(d);
  })();
  const wrap=document.createElement('div');
  wrap.className='cal-create-modal-backdrop';
  wrap.innerHTML=`<div class="cal-create-modal cal-create-modal--large" role="dialog" aria-labelledby="cp-title-h">
    <button type="button" class="cal-create-modal-close" aria-label="Fermer">×</button>
    <h2 id="cp-title-h">${edit?'Modifier l\'événement':'Nouvel événement personnel'}</h2>
    <div class="cal-create-grid">
    <div>
    ${edit?'':'<div class="cal-create-field" id="cp-nom-de-box" hidden><label for="cp-au-nom-de">Calendrier</label>'+
      '<select id="cp-au-nom-de"><option value="">Mon calendrier</option></select></div>'}
    <div class="cal-create-field"><label for="cp-titre">Titre</label>
      <input type="text" id="cp-titre" required maxlength="500" placeholder="Titre de l'événement" value="${esc(titre)}"></div>
    <label class="cal-create-toggle"><input type="checkbox" id="cp-allday" ${allDay?'checked':''}> Journée entière</label>
    <div class="cal-create-row">
      <div class="cal-create-field"><label for="cp-debut">Début</label>
        <input id="cp-debut" type="${allDay?'date':'datetime-local'}" value="${allDay?esc(debut.slice(0,10)):esc(debut)}"></div>
      <div class="cal-create-field"><label for="cp-fin">Fin</label>
        <input id="cp-fin" type="${allDay?'date':'datetime-local'}" value="${allDay?esc(fin.slice(0,10)):esc(fin)}"></div>
    </div>
    <div class="cal-create-row">
      <div class="cal-create-field"><label for="cp-lieu">Lieu (optionnel)</label>
        <input type="text" id="cp-lieu" maxlength="300" placeholder="Salle, adresse…" value="${esc(lieu)}"></div>
      <div class="cal-create-field"><label for="cp-rappel">Rappel</label>
        <select id="cp-rappel">
          ${RAPPELS.map(r=>`<option value="${r.v}"${String(r.v)===String(rappel)?' selected':''}>${esc(r.l)}</option>`).join('')}
        </select></div>
    </div>
    <div class="cal-create-field"><label for="cp-visio">Lien de visioconférence (optionnel)</label>
      <input type="text" id="cp-visio" maxlength="500" placeholder="https://…" value="${esc(visio)}"></div>
    <div class="cal-create-field"><label for="cp-note">Note (optionnel)</label>
      <textarea id="cp-note" maxlength="4000" placeholder="Détails…">${esc(note)}</textarea></div>
    </div>
    <div>
    <div class="cal-create-field cal-part-box"><label for="cp-part-filtre">Participants (optionnel)</label>
      <input type="text" id="cp-part-filtre" placeholder="Nom d'un collègue ou adresse e-mail…" autocomplete="off"
        role="combobox" aria-expanded="false" aria-controls="cp-part-res">
      <div class="cal-part-res" id="cp-part-res" role="listbox" hidden></div>
      <div class="cal-part-chips" id="cp-part-chips"></div>
      <div class="cal-part-dispo" id="cp-part-dispo"></div></div>
    ${edit
      ? (serieId?`<div class="cal-serie-choix">
          <label><input type="radio" name="cp-serie" value="0" checked> Cette occurrence</label>
          <label><input type="radio" name="cp-serie" value="1"> Toute la série à venir</label>
        </div>`:'')
      : `<label class="cal-create-toggle"><input type="checkbox" id="cp-recur"> Rendre récurrent</label>
    <div class="cal-recur-box" id="cp-recur-box" hidden>
      <div class="cal-recur-row">
        <div class="cal-create-field"><label for="cp-recur-regle">Répéter</label>
          <select id="cp-recur-regle">
            <option value="hebdo">Toutes les semaines</option>
            <option value="bihebdo">Toutes les deux semaines</option>
            <option value="mensuel">Tous les mois</option>
            <option value="ouvres">Tous les jours ouvrés</option>
            <option value="quotidien">Tous les jours</option>
          </select></div>
        <div class="cal-create-field"><label for="cp-recur-fin">Jusqu'au</label>
          <input type="date" id="cp-recur-fin" value="${esc(finRecurDefaut)}"></div>
      </div>
      <p class="cal-recur-hint" id="cp-recur-hint"></p>
    </div>`}
    <label class="cal-create-toggle" style="margin-bottom:6px"><input type="checkbox" id="cp-prive" ${prive?'checked':''}> Ne pas faire apparaître</label>
    <p class="cal-extern-hint" style="margin:0 0 4px">Coché, les autres voient « Occupé » — sans titre ni note.</p>
    </div>
    </div>
    <div class="cal-create-modal-foot">
      ${edit?'<button type="button" class="cal-btn" id="cp-delete" style="margin-right:auto;border-color:var(--danger);color:var(--danger)">'+(dejaReunion?'Annuler la réunion':'Supprimer')+'</button>':''}
      <button type="button" class="cal-btn" id="cp-cancel">Annuler</button>
      <button type="button" class="cal-btn primary" id="cp-submit">${edit?'Enregistrer':'Créer'}</button>
    </div>
  </div>`;
  root.appendChild(wrap);
  S.createModal=wrap;
  wrap.onclick=e=>{if(e.target===wrap)closeCreateModal();};
  wrap.querySelector('.cal-create-modal').onclick=e=>{
    e.stopPropagation();
    if(!e.target.closest('.cal-part-box'))masquerResultats();
  };
  wrap.querySelector('.cal-create-modal-close').onclick=closeCreateModal;
  wrap.querySelector('#cp-cancel').onclick=closeCreateModal;
  document.getElementById('cp-allday').onchange=()=>{syncCreateModalAllDay();planifierDispos();};
  wrap.querySelector('#cp-submit').onclick=submitPersoModal;
  ['cp-debut','cp-fin'].forEach(id=>{
    const el=document.getElementById(id);
    if(el)el.addEventListener('change',()=>{planifierDispos();majRecurrence();});
  });
  const filtre=wrap.querySelector('#cp-part-filtre');
  if(filtre){
    filtre.addEventListener('input',()=>renderResultats(filtre.value));
    filtre.addEventListener('focus',()=>renderResultats(filtre.value));
    filtre.addEventListener('keydown',e=>{
      if(e.key==='Escape'){masquerResultats();e.stopPropagation();}
      if(e.key==='Enter'){
        const prem=wrap.querySelector('.cal-part-row');
        if(prem){e.preventDefault();prem.click();}
      }
    });
  }
  const recur=wrap.querySelector('#cp-recur');
  if(recur)recur.onchange=majRecurrence;
  const regle=wrap.querySelector('#cp-recur-regle');
  if(regle)regle.onchange=majRecurrence;
  const recurFin=wrap.querySelector('#cp-recur-fin');
  if(recurFin)recurFin.onchange=majRecurrence;
  renderChips();
  chargerInvitables().then(()=>{planifierDispos();});
  if(!edit)chargerDelegations().then(majSelecteurCalendrier);
  const delBtn=wrap.querySelector('#cp-delete');
  if(delBtn)delBtn.onclick=()=>deletePersoEvent(ev,{fromModal:true});
  document.addEventListener('keydown',onCreateModalKey);
  setTimeout(()=>document.getElementById('cp-titre')?.focus(),0);
}
/* ---------------------------------------------------------------------
   Invites d'une reunion : liste, disponibilites et reponses.
   --------------------------------------------------------------------- */
/* « Au nom de » : n'apparait que si quelqu'un a delegue son calendrier — un
   selecteur vide serait du bruit pour les 95 % de cas normaux. */
async function chargerDelegations(){
  if(S.delegations)return S.delegations;
  try{
    S.delegations=await api('/api/calendrier/delegations');
  }catch(e){
    S.delegations={mes_delegues:[],calendriers_delegues:[]};
  }
  return S.delegations;
}
function majSelecteurCalendrier(){
  const box=document.getElementById('cp-nom-de-box');
  const sel=document.getElementById('cp-au-nom-de');
  if(!box||!sel)return;
  const dels=(S.delegations&&S.delegations.calendriers_delegues)||[];
  if(!dels.length){box.hidden=true;return;}
  sel.innerHTML='<option value="">Mon calendrier</option>'+
    dels.map(d=>'<option value="'+d.id+'">Calendrier de '+esc(d.nom)+'</option>').join('');
  box.hidden=false;
}

async function chargerInvitables(){
  if(S.invitables)return S.invitables;
  try{
    const r=await api('/api/calendrier/invitables');
    S.invitables=(r&&r.utilisateurs)||[];
  }catch(e){
    S.invitables=[];
  }
  return S.invitables;
}
/* La liste complete des collegues n'a pas sa place dans le formulaire : on ne
   propose que ce qui est cherche, et ce qui est retenu passe en pastilles. */
function masquerResultats(){
  const box=document.getElementById('cp-part-res');
  const inp=document.getElementById('cp-part-filtre');
  if(box){box.hidden=true;box.innerHTML='';}
  if(inp)inp.setAttribute('aria-expanded','false');
}
function renderResultats(filtre){
  const box=document.getElementById('cp-part-res');
  const inp=document.getElementById('cp-part-filtre');
  if(!box)return;
  const q=String(filtre||'').trim();
  const ql=q.toLowerCase();
  if(!ql){masquerResultats();return;}
  const gens=(S.invitables||[])
    .filter(u=>!S.partSel.has(u.id)&&String(u.nom||'').toLowerCase().includes(ql))
    .slice(0,8);
  // Une adresse e-mail complete ouvre la porte aux invites sans compte MySifa
  // (client, fournisseur) : ils repondront depuis le lien recu par mail.
  const mailPropose=EMAIL_RE.test(ql)&&!S.partExt.has(ql)
    &&!(S.invitables||[]).some(u=>String(u.email||'').toLowerCase()===ql);
  let html='';
  if(mailPropose){
    html+='<button type="button" class="cal-part-row" role="option" data-mail="'+esc(ql)+'">'+
      '<span class="cal-part-nom">Inviter '+esc(ql)+'</span>'+
      '<span class="cal-part-occupe" style="color:var(--muted)">externe</span></button>';
  }
  if(gens.length){
    html+=gens.map(u=>{
      const occupe=S.partOccupes&&S.partOccupes.has(u.id);
      return '<button type="button" class="cal-part-row" role="option" data-part="'+u.id+'">'+
        '<span class="cal-part-nom">'+esc(u.nom)+'</span>'+
        (occupe?'<span class="cal-part-occupe">occupé</span>':'')+
      '</button>';
    }).join('');
  }
  if(!html){
    html='<div class="cal-part-vide">Aucun résultat. Tapez une adresse e-mail '+
      'complète pour inviter quelqu\'un hors MySifa.</div>';
  }
  box.innerHTML=html;
  const apres=()=>{
    if(inp){inp.value='';inp.focus();}
    masquerResultats();
    renderChips();
    planifierDispos();
  };
  box.querySelectorAll('[data-part]').forEach(btn=>{
    btn.onclick=()=>{
      const id=Number(btn.dataset.part);
      const u=(S.invitables||[]).find(x=>x.id===id);
      S.partSel.add(id);
      if(u)S.partNoms.set(id,u.nom||'');
      apres();
    };
  });
  box.querySelectorAll('[data-mail]').forEach(btn=>{
    btn.onclick=()=>{S.partExt.add(btn.dataset.mail);apres();};
  });
  box.hidden=false;
  if(inp)inp.setAttribute('aria-expanded','true');
}
function renderChips(){
  const box=document.getElementById('cp-part-chips');
  if(!box)return;
  const ids=S.partSel?Array.from(S.partSel):[];
  const mails=S.partExt?Array.from(S.partExt):[];
  const chip=(cle,nom,occupe,externe)=>
    '<span class="cal-part-chip'+(occupe?' occupe':'')+'">'+esc(nom)+
    (externe?'<span style="opacity:.7;font-size:10px">externe</span>':'')+
    '<button type="button" data-retirer="'+esc(cle)+'" aria-label="Retirer '+esc(nom)+'">×</button></span>';
  box.innerHTML=
    ids.map(id=>chip(String(id),(S.partNoms&&S.partNoms.get(id))||'Utilisateur',
                     S.partOccupes&&S.partOccupes.has(id),false)).join('')+
    mails.map(m=>chip(m,m,false,true)).join('');
  box.querySelectorAll('[data-retirer]').forEach(b=>{
    b.onclick=()=>{
      const cle=b.dataset.retirer;
      if(S.partExt.has(cle))S.partExt.delete(cle);
      else S.partSel.delete(Number(cle));
      renderChips();
      planifierDispos();
    };
  });
}
/* Combien de créneaux la répétition va réellement créer — annoncé avant de
   valider, pas découvert après coup dans le calendrier. */
function majRecurrence(){
  const box=document.getElementById('cp-recur-box');
  const coche=document.getElementById('cp-recur');
  if(!box||!coche)return;
  box.hidden=!coche.checked;
  const hint=document.getElementById('cp-recur-hint');
  if(!hint)return;
  if(!coche.checked){hint.textContent='';return;}
  const p=readCreateModalPayload();
  const n=compterOccurrences(p.date_debut,p.recurrence,p.recurrence_fin);
  hint.textContent=n>0
    ?(n+' créneau'+(n>1?'x':'')+' seront créés. Chacun peut ensuite être déplacé ou annulé seul.')
    :'Choisissez une date de fin postérieure au créneau.';
}
/* Meme regle que le serveur (app/services/cal_recurrence.py) : le mensuel se
   calcule depuis le premier creneau, sinon un 31 janvier ramene au 28 fevrier
   resterait bloque au 28 les mois suivants. */
function ajouterMoisDepuis(base,n){
  const d=new Date(base.getFullYear(),base.getMonth()+n,1);
  const dernier=new Date(d.getFullYear(),d.getMonth()+1,0).getDate();
  d.setDate(Math.min(base.getDate(),dernier));
  return d;
}
function compterOccurrences(debut,regle,fin){
  if(!debut||!regle||!fin)return 0;
  const d0=new Date(String(debut).slice(0,10));
  const dF=new Date(String(fin).slice(0,10));
  if(isNaN(d0)||isNaN(dF)||dF<d0)return 0;
  let n=0,rang=0;
  let cur=new Date(d0);
  while(cur<=dF&&n<260){
    n++;rang++;
    if(regle==='quotidien')cur.setDate(cur.getDate()+1);
    else if(regle==='ouvres'){do{cur.setDate(cur.getDate()+1);}while(cur.getDay()===0||cur.getDay()===6);}
    else if(regle==='hebdo')cur.setDate(cur.getDate()+7);
    else if(regle==='bihebdo')cur.setDate(cur.getDate()+14);
    else if(regle==='mensuel')cur=ajouterMoisDepuis(d0,rang);
    else break;
  }
  return n;
}

function planifierDispos(){
  if(S._partTimer)clearTimeout(S._partTimer);
  S._partTimer=setTimeout(()=>{chargerDispos().catch(()=>{});},250);
}
/* Qui est deja pris sur le creneau choisi — la question qui evite trois
   allers-retours par reunion. */
async function chargerDispos(){
  const info=document.getElementById('cp-part-dispo');
  if(!info)return;
  const ids=S.partSel?Array.from(S.partSel):[];
  if(!ids.length){
    S.partOccupes=new Set();
    info.textContent='';
    info.classList.remove('alerte');
    renderChips();
    return;
  }
  const p=readCreateModalPayload();
  if(!p.date_debut||!p.date_fin)return;
  try{
    const q=new URLSearchParams({
      date_debut:p.date_debut,
      date_fin:p.date_fin,
      utilisateurs:ids.join(',')
    });
    const r=await api('/api/calendrier/disponibilites?'+q);
    S.partOccupes=new Set(((r&&r.occupes)||[]).map(Number));
  }catch(e){
    S.partOccupes=new Set();
  }
  const n=S.partOccupes.size;
  info.textContent=n
    ?(n+' participant'+(n>1?'s':'')+' déjà pris sur ce créneau.')
    :(ids.length+' participant'+(ids.length>1?'s':'')+' — tout le monde est libre.');
  info.classList.toggle('alerte',n>0);
  renderChips();
}
/* Recherche : la barre du calendrier interroge le serveur, le clic amene la
   periode sur la date trouvee. On cherche aussi dans le passe, avec les
   creneaux a venir en tete. */
let _rechTimer=null;
async function initSelecteurCollegue(){
  const sel=document.getElementById('cal-collegue');
  if(!sel)return;
  const gens=await chargerInvitables();
  sel.innerHTML='<option value="">Tous les collègues</option>'+
    (gens||[]).map(u=>'<option value="'+u.id+'">Agenda de '+esc(u.nom)+'</option>').join('');
  try{
    const memo=localStorage.getItem(LS_COLLEGUE)||'';
    if(memo&&(gens||[]).some(u=>String(u.id)===memo)){sel.value=memo;S.collegue=memo;}
  }catch(e){}
  sel.classList.toggle('actif',!!S.collegue);
  sel.onchange=()=>{
    S.collegue=sel.value||'';
    sel.classList.toggle('actif',!!S.collegue);
    try{localStorage.setItem(LS_COLLEGUE,S.collegue);}catch(e){}
    // Demander l'agenda de quelqu'un implique d'afficher le calendrier qui le
    // porte : sinon le choix reste sans effet visible.
    if(S.collegue&&!S.visible.collegues){
      S.visible.collegues=true;
      saveVisible();
      renderToggles();
    }
    fetchEvents();
  };
  if(S.collegue&&!S.visible.collegues){
    S.visible.collegues=true;
    saveVisible();
    renderToggles();
  }
}

function bindRecherche(){
  const inp=document.getElementById('cal-search');
  const box=document.getElementById('cal-search-res');
  if(!inp||!box||inp.dataset.bound)return;
  inp.dataset.bound='1';
  inp.addEventListener('input',()=>{
    clearTimeout(_rechTimer);
    const q=inp.value.trim();
    if(q.length<2){box.hidden=true;box.innerHTML='';return;}
    _rechTimer=setTimeout(()=>lancerRecherche(q),260);
  });
  inp.addEventListener('keydown',e=>{
    if(e.key==='Escape'){box.hidden=true;inp.blur();}
  });
  document.addEventListener('click',e=>{
    if(!e.target.closest('.cal-search-wrap')){box.hidden=true;}
  });
}
async function lancerRecherche(q){
  const box=document.getElementById('cal-search-res');
  if(!box)return;
  let res=[];
  try{
    const r=await api('/api/calendrier/recherche?q='+encodeURIComponent(q));
    res=(r&&r.resultats)||[];
  }catch(e){
    res=[];
  }
  if(!res.length){
    box.innerHTML='<div class="cal-search-vide">Aucun événement trouvé.</div>';
  }else{
    box.innerHTML=res.map(r=>{
      const quand=r.all_day
        ?new Date(String(r.debut).slice(0,10)).toLocaleDateString('fr-FR',
            {weekday:'short',day:'2-digit',month:'short',year:'numeric'})+' · journée'
        :fmtCreneauCourt(r.debut,r.fin);
      return '<button type="button" class="cal-search-row'+(r.annule?' barre':'')+
        '" data-jour="'+esc(String(r.debut).slice(0,10))+'">'+
        '<span class="cal-search-titre">'+esc(r.titre)+'</span>'+
        '<span class="cal-search-quand">'+esc(quand)+(r.lieu?' · '+esc(r.lieu):'')+'</span>'+
      '</button>';
    }).join('');
    box.querySelectorAll('[data-jour]').forEach(b=>{
      b.onclick=()=>{
        box.hidden=true;
        const d=parseDayStr(b.dataset.jour);
        if(!d)return;
        S.anchor=d;
        fetchEvents();
      };
    });
  }
  box.hidden=false;
}

/* Delegation : je choisis qui peut poser un creneau dans mon calendrier. Le
   delegue voit alors « Mon calendrier / Calendrier de X » a la creation. */
function closeDelegModal(){
  const root=document.getElementById('cal-deleg-modal-root');
  if(root)root.innerHTML='';
}
async function openDelegationsModal(){
  const root=document.getElementById('cal-deleg-modal-root');
  if(!root)return;
  S.delegations=null;
  await Promise.all([chargerDelegations(),chargerInvitables()]);
  const wrap=document.createElement('div');
  wrap.className='cal-create-modal-backdrop';
  root.innerHTML='';
  root.appendChild(wrap);
  function rendre(){
    const mes=(S.delegations&&S.delegations.mes_delegues)||[];
    const pour=(S.delegations&&S.delegations.calendriers_delegues)||[];
    const dejaIds=new Set(mes.map(d=>d.id));
    const options=(S.invitables||[]).filter(u=>!dejaIds.has(u.id));
    wrap.innerHTML=`<div class="cal-create-modal" role="dialog" aria-labelledby="cdel-h">
      <button type="button" class="cal-create-modal-close" aria-label="Fermer">×</button>
      <h2 id="cdel-h">Délégations</h2>
      <p class="cal-extern-hint" style="margin:-6px 0 16px">Une personne déléguée peut créer des créneaux dans votre calendrier. Elle ne voit pas vos créneaux privés.</p>
      <div class="cal-create-field"><label>Qui peut écrire chez moi</label>
        <div class="cal-part-chips">${mes.length
          ?mes.map(d=>`<span class="cal-part-chip">${esc(d.nom)}<button type="button" data-retirer-deleg="${d.id}" aria-label="Retirer ${esc(d.nom)}">×</button></span>`).join('')
          :'<span style="font-size:11px;color:var(--muted)">Personne pour l\'instant.</span>'}</div>
      </div>
      <div class="cal-create-row" style="align-items:flex-end">
        <div class="cal-create-field" style="flex:1"><label for="cdel-sel">Ajouter</label>
          <select id="cdel-sel">${options.map(u=>`<option value="${u.id}">${esc(u.nom)}</option>`).join('')}</select></div>
        <div class="cal-create-field" style="margin-bottom:12px">
          <button type="button" class="cal-btn primary" id="cdel-add"${options.length?'':' disabled'}>Ajouter</button></div>
      </div>
      ${pour.length?`<div class="cal-create-field"><label>Calendriers où je peux écrire</label>
        <div class="cal-part-chips">${pour.map(d=>`<span class="cal-part-chip">${esc(d.nom)}</span>`).join('')}</div></div>`:''}
      <div class="cal-create-modal-foot">
        <button type="button" class="cal-btn" id="cdel-fermer">Fermer</button>
      </div>
    </div>`;
    wrap.querySelector('.cal-create-modal').onclick=e=>e.stopPropagation();
    wrap.querySelector('.cal-create-modal-close').onclick=closeDelegModal;
    wrap.querySelector('#cdel-fermer').onclick=closeDelegModal;
    const add=wrap.querySelector('#cdel-add');
    if(add)add.onclick=async()=>{
      const sel=wrap.querySelector('#cdel-sel');
      if(!sel||!sel.value)return;
      try{
        await api('/api/calendrier/delegations',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({delegue_id:parseInt(sel.value,10)})
        });
        S.delegations=null;
        await chargerDelegations();
        rendre();
        showToast('Délégation ajoutée.','success');
      }catch(e){showToast(e.message||'Ajout impossible','danger');}
    };
    wrap.querySelectorAll('[data-retirer-deleg]').forEach(b=>{
      b.onclick=async()=>{
        try{
          await api('/api/calendrier/delegations/'+encodeURIComponent(b.dataset.retirerDeleg),
            {method:'DELETE'});
          S.delegations=null;
          await chargerDelegations();
          rendre();
        }catch(e){showToast(e.message||'Suppression impossible','danger');}
      };
    });
  }
  wrap.onclick=e=>{if(e.target===wrap)closeDelegModal();};
  rendre();
}

/* Lien direct depuis la pop-up de rappel : /calendrier?ev=perso-12&jour=…
   ouvre la periode sur le bon jour puis la fiche (ou la contre-proposition). */
function lireLienDirect(){
  try{
    const q=new URLSearchParams(location.search);
    const id=q.get('ev');
    if(!id)return;
    S.lienDirect={id:id,action:q.get('action')||''};
    const jour=parseDayStr(q.get('jour')||'');
    if(jour)S.anchor=jour;
    history.replaceState(null,'',location.pathname);
  }catch(e){}
}
function consommerLienDirect(){
  const lien=S.lienDirect;
  if(!lien)return;
  S.lienDirect=null;
  const ev=(S.events||[]).find(x=>x.id===lien.id);
  if(!ev){showToast('Événement introuvable — il a peut-être été déplacé.','danger');return;}
  if(lien.action==='proposer'&&ev.meta&&ev.meta.mon_statut&&ev.meta.mon_statut!=='organisateur'){
    openPropositionModal(ev);
    return;
  }
  const el=document.querySelector('[data-ev-id="'+cssEscape(ev.id)+'"]');
  if(el)openPop(ev,el);
}
function cssEscape(v){
  return String(v||'').replace(/["\\]/g,'\\$&');
}

function libelleRappel(m){
  const n=Number(m);
  if(n===0)return 'aucun';
  if(n===1440)return 'la veille';
  if(n>=60)return (n/60)+' h avant';
  return n+' min avant';
}
/* Proposer un autre horaire plutot que refuser sec : l'organisateur recoit la
   proposition sur la fiche de la reunion et deplace d'un clic. */
function openPropositionModal(ev){
  closePop();
  const root=document.getElementById('cal-create-modal-root');
  if(!root)return;
  closeCreateModal();
  const debut=String(ev.debut||'').slice(0,16);
  const fin=String(ev.fin||'').slice(0,16);
  const wrap=document.createElement('div');
  wrap.className='cal-create-modal-backdrop';
  wrap.innerHTML=`<div class="cal-create-modal" role="dialog" aria-labelledby="cprop-h">
    <button type="button" class="cal-create-modal-close" aria-label="Fermer">×</button>
    <h2 id="cprop-h">Proposer un autre horaire</h2>
    <p class="cal-extern-hint" style="margin:-6px 0 14px">${esc(ev.titre||'')} — l'organisateur décide.</p>
    <div class="cal-create-row">
      <div class="cal-create-field"><label for="cprop-debut">Début</label>
        <input id="cprop-debut" type="datetime-local" value="${esc(debut)}"></div>
      <div class="cal-create-field"><label for="cprop-fin">Fin</label>
        <input id="cprop-fin" type="datetime-local" value="${esc(fin)}"></div>
    </div>
    <div class="cal-create-field"><label for="cprop-msg">Message (optionnel)</label>
      <textarea id="cprop-msg" maxlength="500" placeholder="Je suis en clientèle ce matin-là…"></textarea></div>
    <div class="cal-create-modal-foot">
      <button type="button" class="cal-btn" id="cprop-annuler">Annuler</button>
      <button type="button" class="cal-btn primary" id="cprop-ok">Proposer</button>
    </div>
  </div>`;
  root.appendChild(wrap);
  S.createModal=wrap;
  wrap.onclick=e=>{if(e.target===wrap)closeCreateModal();};
  wrap.querySelector('.cal-create-modal').onclick=e=>e.stopPropagation();
  wrap.querySelector('.cal-create-modal-close').onclick=closeCreateModal;
  wrap.querySelector('#cprop-annuler').onclick=closeCreateModal;
  wrap.querySelector('#cprop-ok').onclick=async()=>{
    const d=document.getElementById('cprop-debut')?.value||'';
    const f=document.getElementById('cprop-fin')?.value||'';
    if(!d||!f||f<=d){showToast('Créneau invalide.','danger');return;}
    try{
      await api('/api/calendrier/events/perso/'+encodeURIComponent(persoRawId(ev))+'/proposition',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({date_debut:d,date_fin:f,
          message:(document.getElementById('cprop-msg')?.value||'').trim()||null})
      });
      closeCreateModal();
      showToast('Proposition envoyée à l\'organisateur.','success');
      fetchEvents();
    }catch(e){
      showToast(e.message||'Proposition impossible','danger');
    }
  };
  document.addEventListener('keydown',onCreateModalKey);
}
async function arbitrerProposition(ev,propId,accepter){
  try{
    const r=await api('/api/calendrier/events/perso/'+encodeURIComponent(persoRawId(ev))+
      '/proposition/'+encodeURIComponent(propId)+'?accepter='+(accepter?'true':'false'),
      {method:'POST'});
    closePop();
    showToast(r&&r.deplacee
      ?'Réunion déplacée — chacun doit reconfirmer.'
      :'Proposition écartée.','success');
    fetchEvents();
  }catch(e){
    showToast(e.message||'Action impossible','danger');
  }
}

async function repondreInvitation(ev,statut){
  const raw=persoRawId(ev);
  if(!raw)return;
  try{
    await api('/api/calendrier/events/perso/'+encodeURIComponent(raw)+'/reponse',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({statut})
    });
    closePop();
    showToast('Réponse enregistrée : '+(STATUT_MOT[statut]||statut)+'.','success');
    fetchEvents();
    if(window.MySifaCalRappel&&MySifaCalRappel.rafraichir)MySifaCalRappel.rafraichir();
  }catch(e){
    showToast(e.message||'Réponse impossible','danger');
  }
}

function openCreateModal(opts){openPersoModal(opts||{});}
async function submitPersoModal(){
  const payload=readCreateModalPayload();
  if(!payload.titre){showToast('Titre requis.','danger');return;}
  if(!payload.date_debut||!payload.date_fin){showToast('Dates invalides.','danger');return;}
  const ev=S.editingEv;
  // Chaque endpoint ne reçoit que ses champs : la répétition ne se définit qu'à
  // la création, le choix « toute la série » ne vaut qu'à la modification.
  if(ev){delete payload.recurrence;delete payload.recurrence_fin;delete payload.au_nom_de;}
  else{delete payload.serie;}
  try{
    let r;
    if(ev){
      r=await api('/api/calendrier/events/perso/'+encodeURIComponent(persoRawId(ev)),{
        method:'PUT',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload)
      });
    }else{
      r=await api('/api/calendrier/events/perso',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload)
      });
    }
    closeCreateModal();
    const nbOcc=Number((r&&r.meta&&r.meta.occurrences)||0);
    showToast(
      nbOcc>1
        ?(ev?('Série mise à jour — '+nbOcc+' créneaux.')
             :('Série créée — '+nbOcc+' créneaux.'))
        :(ev?'Événement modifié.':'Événement créé.'),
      'success');
    if(!S.visible.perso)S.visible.perso=true;
    saveVisible();
    fetchEvents();
  }catch(e){
    showToast(e.message||(ev?'Modification impossible':'Création impossible'),'danger');
  }
}
async function deletePersoEvent(ev,opts){
  if(!isOwnPerso(ev))return;
  const raw=persoRawId(ev);
  if(!raw)return;
  opts=opts||{};
  // Depuis la modale, le choix « cette occurrence / toute la série » vaut aussi
  // pour la suppression : c'est le même geste dans la tête de l'utilisateur.
  let serie=!!opts.serie;
  if(opts.fromModal){
    const radio=document.querySelector('input[name=\"cp-serie\"]:checked');
    serie=!!(radio&&radio.value==='1');
  }
  try{
    const r=await api('/api/calendrier/events/perso/'+encodeURIComponent(raw)+(serie?'?serie=1':''),
      {method:'DELETE'});
    if(opts.fromModal)closeCreateModal();
    closePop();
    const nb=Number((r&&r.occurrences)||1);
    const suffixe=nb>1?(' — '+nb+' créneaux'):'';
    showToast(r&&r.annule
      ?('Réunion annulée — les participants la voient barrée'+suffixe+'.')
      :('Événement supprimé'+suffixe+'.'),'success');
    fetchEvents();
  }catch(err){
    showToast(err.message||'Suppression impossible','danger');
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
/* Tirer sur une plage vide de la grille cree un creneau a la bonne heure et a
   la bonne duree — le clic simple reste, il ouvre une heure par defaut. */
function bindGridDragCreate(){
  const body=document.getElementById('cal-body');
  if(!body||body.dataset.dragCreateBound)return;
  body.dataset.dragCreateBound='1';
  body.addEventListener('pointerdown',e=>{
    if(e.button!==0||e.pointerType==='touch')return;
    if(e.target.closest('[data-ev-id],.cal-more,.cal-col-ferie-label'))return;
    const slots=e.target.closest('.cal-col-slots[data-day]');
    if(!slots)return;
    const h0=parseFloat(slots.dataset.hStart);
    const h1=parseFloat(slots.dataset.hEnd);
    if(!(h1>h0))return;
    const rect=slots.getBoundingClientRect();
    const heureA=cy=>{
      const ratio=Math.min(1,Math.max(0,(cy-rect.top)/rect.height));
      return Math.round((h0+ratio*(h1-h0))*4)/4;
    };
    const depart=heureA(e.clientY);
    const y0=e.clientY;
    let ghost=null,bouge=false,plage=[depart,depart];
    const libelle=h=>pad2(Math.floor(h))+':'+pad2(Math.round((h%1)*60));
    function onMove(ev2){
      if(!bouge&&Math.abs(ev2.clientY-y0)<6)return;
      bouge=true;
      const cur=heureA(ev2.clientY);
      const a=Math.min(depart,cur),b=Math.max(depart,cur);
      plage=[a,b];
      if(!ghost){
        ghost=document.createElement('div');
        ghost.className='cal-ghost';
        slots.appendChild(ghost);
      }
      ghost.style.top=(((a-h0)/(h1-h0))*rect.height)+'px';
      ghost.style.height=Math.max(8,((b-a)/(h1-h0))*rect.height)+'px';
      ghost.textContent=libelle(a)+' – '+libelle(b);
    }
    function onUp(){
      document.removeEventListener('pointermove',onMove);
      document.removeEventListener('pointerup',onUp);
      if(ghost)ghost.remove();
      if(!bouge)return;
      S._suppressClickUntil=Date.now()+400;
      let [a,b]=plage;
      if(b-a<0.25)b=a+0.5;
      openCreateModal({day:slots.dataset.day,hour:a,hourFin:b,allDay:false});
    }
    document.addEventListener('pointermove',onMove);
    document.addEventListener('pointerup',onUp);
  });
}

function bindCalendarBodyClicks(){
  const body=document.getElementById('cal-body');
  if(!body||body.dataset.createBound)return;
  body.dataset.createBound='1';
  bindBodySwipe();
  bindGridDragCreate();
  body.addEventListener('click',e=>{
    if(dragJustEnded())return;
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

/* Qui vient, qui a repondu quoi — lisible d'un coup d'oeil par tous les
   invites, pas seulement par l'organisateur. */
function blocReunionHtml(meta){
  if(!meta||!meta.reunion)return '';
  const parts=(meta.participants||[]).concat(meta.invites_externes||[]);
  const n={accepte:0,refuse:0,peut_etre:0,en_attente:0};
  parts.forEach(p=>{if(n[p.statut]!=null)n[p.statut]++;});
  const compte=[
    n.accepte+' accepté'+(n.accepte>1?'s':''),
    n.peut_etre+' peut-être',
    n.refuse+' refusé'+(n.refuse>1?'s':''),
    n.en_attente+' en attente'
  ].join(' · ');
  const liste=parts.length
    ?'<ul class="cal-pop-parts">'+parts.map(p=>
        '<li><span class="cal-part-pastille st-'+esc(p.statut||'en_attente')+'"></span>'+
        esc(p.nom||p.email||'')+
        (p.externe?'<span style="font-size:10px;color:var(--muted)">externe</span>':'')+
        '</li>').join('')+'</ul>'
    :'';
  const org=meta.organisateur_nom
    ?('Réunion · organisée par '+esc(meta.organisateur_nom))
    :'Réunion';
  return '<div class="cal-pop-reunion">'+
    '<div class="cal-pop-reunion-head">'+org+'</div>'+
    '<div class="cal-pop-reunion-compte">'+compte+'</div>'+liste+'</div>';
}
/* Contre-propositions : l'organisateur arbitre depuis la fiche, les autres
   voient simplement qu'un autre horaire est sur la table. */
function blocPropositionsHtml(meta,own){
  const props=meta.propositions||[];
  if(!props.length)return '';
  return '<div class="cal-pop-reunion">'+
    '<div class="cal-pop-reunion-head">Autre horaire proposé</div>'+
    props.map(p=>{
      const quand=fmtCreneauCourt(p.debut,p.fin);
      return '<div class="cal-prop">'+
        '<div class="cal-prop-txt"><strong>'+esc(p.nom)+'</strong> — '+esc(quand)+
        (p.message?'<div class="cal-prop-msg">'+esc(p.message)+'</div>':'')+'</div>'+
        (own
          ?'<div class="cal-prop-actions">'+
             '<button type="button" class="cal-rep-btn" data-prop-ok="'+p.id+'">Déplacer</button>'+
             '<button type="button" class="cal-rep-btn" data-prop-non="'+p.id+'">Écarter</button>'+
           '</div>'
          :'')+
      '</div>';
    }).join('')+'</div>';
}
function fmtCreneauCourt(debut,fin){
  const d=new Date(String(debut||'').replace(' ','T'));
  const f=new Date(String(fin||'').replace(' ','T'));
  if(isNaN(d))return String(debut||'');
  const jour=d.toLocaleDateString('fr-FR',{weekday:'short',day:'2-digit',month:'short'});
  const h=x=>pad2(x.getHours())+':'+pad2(x.getMinutes());
  return jour+' '+h(d)+(isNaN(f)?'':' – '+h(f));
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
  const meta=ev.meta||{};
  const noteBlk=meta.note
    ?'<div style="margin-top:8px;font-size:12px;color:var(--text2);line-height:1.5">'+esc(meta.note)+'</div>':'';
  const srcBlk=meta.source
    ?'<div style="margin-top:6px;font-size:11px;color:var(--muted)">Source : '+esc(meta.source)+'</div>':'';
  const lieuBlk=meta.lieu
    ?'<div style="margin-top:6px;font-size:11px;color:var(--muted)">Lieu : '+esc(meta.lieu)+'</div>':'';
  const visioBlk=meta.visio
    ?'<div style="margin-top:6px;font-size:11px"><a href="'+esc(meta.visio)+
      '" target="_blank" rel="noopener">Rejoindre la visioconférence</a></div>':'';
  const rappelBlk=(meta.rappel_minutes!=null&&meta.rappel_minutes!==10)
    ?'<div style="margin-top:6px;font-size:11px;color:var(--muted)">Rappel : '+
      (Number(meta.rappel_minutes)===0?'aucun':libelleRappel(meta.rappel_minutes))+'</div>':'';
  const auteurBlk=meta.cree_par_nom
    ?'<div style="margin-top:6px;font-size:11px;color:var(--muted)">Créé par '+
      esc(meta.cree_par_nom)+'</div>':'';
  const busyBlk=isBusyPerso(ev)
    ?'<div style="margin-top:6px;font-size:11px;color:var(--muted)">Créneau masqué par son auteur.</div>':'';
  let link='';
  if(ev.calendrier.startsWith('production_'))link='<a href="/planning">Ouvrir le planning production</a>';
  else if(ev.calendrier==='conges')link='<a href="/planning-rh">Ouvrir le planning RH</a>';
  else if(ev.calendrier==='expeditions')link='<a href="/expe">Ouvrir MyExpé</a>';
  const recurBlk=meta.recurrence_libelle
    ?'<div style="margin-top:6px;font-size:11px;color:var(--muted)">Se répète '+
      esc(meta.recurrence_libelle)+'</div>':'';
  const reunionBlk=blocReunionHtml(meta);
  const propsBlk=blocPropositionsHtml(meta,isOwnPerso(ev));
  const annuleBlk=meta.annule
    ?'<div class="cal-pop-annule">Réunion annulée par l\'organisateur.</div>':'';
  const repBlk=(meta.reunion&&meta.mon_statut&&meta.mon_statut!=='organisateur'&&!meta.annule)
    ?'<div class="cal-pop-reponse">'+['accepte','peut_etre','refuse'].map(st=>
        '<button type="button" class="cal-rep-btn'+(meta.mon_statut===st?' actif':'')+
        '" data-rep="'+st+'">'+STATUT_LABEL[st]+'</button>').join('')+'</div>'+
      '<button type="button" class="cal-btn cal-pop-proposer" style="width:100%;margin-top:8px">'+
      'Proposer un autre horaire</button>'
    :'';
  const own=isOwnPerso(ev);
  const editBtn=own
    ?'<button type="button" class="cal-btn cal-pop-edit" style="width:100%;margin-top:10px">Modifier</button>':'';
  const delBtn=own
    ?(meta.serie_id
        ?'<button type="button" class="cal-pop-del" data-serie="0">Supprimer cette occurrence</button>'+
         '<button type="button" class="cal-pop-del" data-serie="1">Supprimer la série à venir</button>'
        :'<button type="button" class="cal-pop-del">Supprimer</button>')
    :'';
  const pop=document.createElement('div');
  pop.className='cal-pop';
  pop.innerHTML='<button type="button" class="cal-pop-close" aria-label="Fermer">×</button>'+
    '<div class="cal-pop-title">'+esc(ev.titre)+'</div>'+
    '<div class="cal-pop-meta">'+esc(CAL_DEFS.find(c=>c.id===ev.calendrier)?.label||ev.calendrier)+'<br>'+per+stat+noteBlk+srcBlk+lieuBlk+visioBlk+rappelBlk+auteurBlk+recurBlk+busyBlk+'</div>'+
    (link?'<div>'+link+'</div>':'')+annuleBlk+reunionBlk+propsBlk+repBlk+editBtn+delBtn;
  document.body.appendChild(pop);
  S.pop=pop;
  pop.querySelector('.cal-pop-close').onclick=closePop;
  const editEl=pop.querySelector('.cal-pop-edit');
  if(editEl)editEl.onclick=e=>{e.stopPropagation();openEditModal(ev);};
  pop.querySelectorAll('.cal-pop-del').forEach(b=>{
    b.onclick=e=>{
      e.stopPropagation();
      deletePersoEvent(ev,{serie:b.dataset.serie==='1'});
    };
  });
  pop.querySelectorAll('.cal-rep-btn[data-rep]').forEach(b=>{
    b.onclick=e=>{e.stopPropagation();repondreInvitation(ev,b.dataset.rep);};
  });
  pop.querySelectorAll('[data-prop-ok],[data-prop-non]').forEach(b=>{
    b.onclick=e=>{
      e.stopPropagation();
      const id=b.dataset.propOk||b.dataset.propNon;
      arbitrerProposition(ev,id,!!b.dataset.propOk);
    };
  });
  const propBtn=pop.querySelector('.cal-pop-proposer');
  if(propBtn)propBtn.onclick=e=>{e.stopPropagation();openPropositionModal(ev);};
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

/* ---------------------------------------------------------------------
   Interactions sur les créneaux : clic, double-clic (édition),
   déplacement et étirement des créneaux personnels dont on est l'auteur.
   --------------------------------------------------------------------- */
function dragJustEnded(){
  return !!(S._suppressClickUntil&&Date.now()<S._suppressClickUntil);
}
const DRAG_SNAP_MIN=15;
const DRAG_THRESHOLD_PX=4;
const DRAG_MIN_MINUTES=15;

function bindRenderedEvents(){
  document.querySelectorAll('[data-ev-id]').forEach(el=>{
    const id=el.dataset.evId;
    const ev=S.events.find(x=>x.id===id);
    if(!ev)return;
    const own=isOwnPerso(ev);
    el.onclick=e=>{
      if(e.target.closest&&e.target.closest('.cal-ev-rs,.cal-rs-x')){e.stopPropagation();return;}
      if(dragJustEnded()){e.stopPropagation();return;}
      if(!own){onEvClick(ev,e);return;}
      e.stopPropagation();
      const cur=e.currentTarget;
      clearTimeout(S._clickTimer);
      S._clickTimer=setTimeout(()=>{openPop(ev,cur);},240);
    };
    if(own){
      el.ondblclick=e=>{
        e.preventDefault();e.stopPropagation();
        clearTimeout(S._clickTimer);
        closePop();
        openEditModal(ev);
      };
      el.addEventListener('pointerdown',e=>startEventDrag(ev,el,e));
    }
  });
}

function colSlotsAt(x,y){
  const el=document.elementFromPoint(x,y);
  const col=el&&el.closest?el.closest('.cal-col-slots[data-day]'):null;
  if(col)return col;
  const cols=document.querySelectorAll('.cal-col-slots[data-day]');
  for(const c of cols){
    const r=c.getBoundingClientRect();
    if(x>=r.left&&x<=r.right)return c;
  }
  return null;
}
function dayCellAt(x,y){
  const el=document.elementFromPoint(x,y);
  const cell=el&&el.closest?el.closest('.cal-day[data-day]'):null;
  if(cell)return cell;
  const row=el&&el.closest?el.closest('.cal-week-row'):null;
  const cells=(row||document).querySelectorAll('.cal-day[data-day]');
  for(const c of cells){
    const r=c.getBoundingClientRect();
    if(x>=r.left&&x<=r.right)return c;
  }
  return null;
}
function daysDiff(a,b){
  return Math.round((startOfDay(a)-startOfDay(b))/86400000);
}
function shiftDt(d,days,mins){
  const x=new Date(d);
  if(days)x.setDate(x.getDate()+days);
  if(mins)x.setMinutes(x.getMinutes()+mins);
  return x;
}
function fmtLocalDt(d){
  return ymd(d)+'T'+pad2(d.getHours())+':'+pad2(d.getMinutes());
}
function fmtHm(d){return pad2(d.getHours())+':'+pad2(d.getMinutes());}
function fmtDayShort(d){
  return d.toLocaleDateString('fr-FR',{weekday:'short',day:'numeric',month:'short'});
}
function snapMinutes(m){return Math.round(m/DRAG_SNAP_MIN)*DRAG_SNAP_MIN;}

function ensureDragBadge(){
  let b=document.getElementById('cal-drag-badge');
  if(!b){
    b=document.createElement('div');
    b.id='cal-drag-badge';
    b.className='cal-drag-badge';
    document.body.appendChild(b);
  }
  return b;
}
function moveDragBadge(x,y,text){
  const b=ensureDragBadge();
  b.textContent=text;
  b.style.left=Math.min(window.innerWidth-b.offsetWidth-8,x+14)+'px';
  b.style.top=Math.max(8,y-34)+'px';
}
function removeDragBadge(){
  const b=document.getElementById('cal-drag-badge');
  if(b)b.remove();
}

function startEventDrag(ev,el,e){
  if(S.drag)return;
  if(e.pointerType==='touch')return;
  if(e.button!==undefined&&e.button!==0)return;
  const s0=evStart(ev);
  const e0=evEnd(ev)||s0;
  if(!s0)return;
  const handle=e.target.closest?e.target.closest('.cal-ev-rs,.cal-rs-x'):null;
  const timedCol=el.closest('.cal-col-slots[data-day]');
  const monthCell=el.closest('.cal-day[data-day]');
  const barsRow=el.closest('.cal-week-bars');
  let kind=null;
  if(timedCol)kind='timed';
  else if(monthCell)kind='monthPill';
  else if(barsRow)kind='monthBar';
  if(!kind)return;
  let mode='move';
  if(handle){
    if(handle.classList.contains('cal-ev-rs-top'))mode='top';
    else if(handle.classList.contains('cal-ev-rs-bot'))mode='bot';
    else if(handle.classList.contains('cal-rs-x'))mode='end-day';
  }
  e.preventDefault();
  const originDay=kind==='timed'
    ?parseDayStr(timedCol.dataset.day)
    :(kind==='monthPill'?parseDayStr(monthCell.dataset.day):startOfDay(s0));
  S.drag={
    ev,el,kind,mode,
    s0,e0,
    startX:e.clientX,startY:e.clientY,
    originDay,
    originCol:timedCol||null,
    origTop:parseFloat(el.style.top)||0,
    origH:parseFloat(el.style.height)||0,
    dayDelta:0,minDelta:0,targetDay:null,
    started:false,
    newStart:s0,newEnd:e0
  };
  window.addEventListener('pointermove',onDragMove,true);
  window.addEventListener('pointerup',onDragEnd,true);
  window.addEventListener('pointercancel',cancelDrag,true);
}

function computeDragDates(st){
  let ns=st.s0,ne=st.e0;
  if(st.kind==='timed'){
    if(st.mode==='move'){
      ns=shiftDt(st.s0,st.dayDelta,st.minDelta);
      ne=shiftDt(st.e0,st.dayDelta,st.minDelta);
    }else if(st.mode==='top'){
      const maxUp=(st.e0-st.s0)/60000-DRAG_MIN_MINUTES;
      const d=Math.min(st.minDelta,maxUp);
      ns=shiftDt(st.s0,0,d);
    }else{
      const maxDown=-((st.e0-st.s0)/60000-DRAG_MIN_MINUTES);
      const d=Math.max(st.minDelta,maxDown);
      ne=shiftDt(st.e0,0,d);
    }
  }else{
    if(st.mode==='end-day'){
      const target=st.targetDay?new Date(st.targetDay):startOfDay(st.e0);
      ne=new Date(target);
      ne.setHours(st.e0.getHours(),st.e0.getMinutes(),0,0);
      if(ne<st.s0)ne=new Date(st.e0);
    }else{
      ns=shiftDt(st.s0,st.dayDelta,0);
      ne=shiftDt(st.e0,st.dayDelta,0);
    }
  }
  return{ns,ne};
}

function onDragMove(e){
  const st=S.drag;
  if(!st)return;
  const dx=e.clientX-st.startX;
  const dy=e.clientY-st.startY;
  if(!st.started){
    if(Math.abs(dx)<DRAG_THRESHOLD_PX&&Math.abs(dy)<DRAG_THRESHOLD_PX)return;
    st.started=true;
    clearTimeout(S._clickTimer);
    closePop();
    document.body.classList.add('cal-dragging');
    st.el.classList.add(
      st.kind==='timed'?'cal-ev--dragging'
        :(st.kind==='monthBar'?'cal-mbar--dragging':'cal-pill--dragging')
    );
  }
  e.preventDefault();

  if(st.kind==='timed'){
    st.minDelta=(st.mode==='move'||st.mode==='top'||st.mode==='bot')
      ?snapMinutes(dy/PX_PER_HOUR*60):0;
    if(st.mode==='move'){
      const col=colSlotsAt(e.clientX,e.clientY);
      if(col){
        st.dayDelta=daysDiff(parseDayStr(col.dataset.day),st.originDay);
        if(col!==st.el.parentNode)col.appendChild(st.el);
      }
    }
  }else{
    const cell=dayCellAt(e.clientX,e.clientY);
    if(cell){
      const target=parseDayStr(cell.dataset.day);
      st.targetDay=target;
      st.dayDelta=daysDiff(target,st.originDay);
    }
  }

  const {ns,ne}=computeDragDates(st);
  st.newStart=ns;st.newEnd=ne;

  if(st.kind==='timed'){
    const dpx=(ns-st.s0-(st.dayDelta*86400000))/60000/60*PX_PER_HOUR;
    const hpx=Math.max(18,(ne-ns)/60000/60*PX_PER_HOUR);
    if(st.mode==='bot'){
      st.el.style.height=hpx+'px';
    }else{
      st.el.style.top=(st.origTop+dpx)+'px';
      st.el.style.height=hpx+'px';
    }
    const sameDay=ymd(ns)===ymd(st.s0);
    moveDragBadge(e.clientX,e.clientY,
      (sameDay?'':fmtDayShort(ns)+' · ')+fmtHm(ns)+' → '+fmtHm(ne));
  }else{
    const multi=ymd(ns)!==ymd(ne);
    moveDragBadge(e.clientX,e.clientY,
      multi?(fmtDayShort(ns)+' → '+fmtDayShort(ne)):fmtDayShort(ns));
  }
}

function releaseDrag(){
  window.removeEventListener('pointermove',onDragMove,true);
  window.removeEventListener('pointerup',onDragEnd,true);
  window.removeEventListener('pointercancel',cancelDrag,true);
  document.body.classList.remove('cal-dragging');
  removeDragBadge();
  const st=S.drag;
  S.drag=null;
  return st;
}
function cancelDrag(){
  const st=releaseDrag();
  if(st&&st.started){S._suppressClickUntil=Date.now()+400;renderCalendar();}
}
async function onDragEnd(e){
  const st=releaseDrag();
  if(!st)return;
  if(!st.started)return;
  S._suppressClickUntil=Date.now()+400;
  const ns=st.newStart,ne=st.newEnd;
  const unchanged=fmtLocalDt(ns)===fmtLocalDt(st.s0)&&fmtLocalDt(ne)===fmtLocalDt(st.e0);
  if(unchanged){renderCalendar();return;}
  const ev=st.ev;
  const payload=ev.all_day
    ?{date_debut:ymd(ns)+'T00:00',date_fin:ymd(ne)+'T23:59'}
    :{date_debut:fmtLocalDt(ns),date_fin:fmtLocalDt(ne)};
  try{
    await api('/api/calendrier/events/perso/'+encodeURIComponent(persoRawId(ev)),{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    });
    showToast('Créneau déplacé.','success');
  }catch(err){
    showToast(err.message||'Déplacement impossible','danger');
  }
  fetchEvents();
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
    any=true;
    const today=isToday(cur);
    html+='<div class="cal-agenda-day">';
    html+='<div class="cal-agenda-day-head">';
    html+='<span class="cal-agenda-day-title">'+esc(formatAgendaDayHeader(cur))+'</span>';
    html+='<span class="cal-agenda-day-iso">S '+getISOWeek(cur)+'</span>';
    if(today)html+='<span class="cal-agenda-today">Aujourd\'hui</span>';
    html+='</div><div class="cal-agenda-evs">';
    if(evs.length){
      evs.forEach(ev=>{
        const time=evTimeLabelOnDay(ev,cur);
        html+='<div class="cal-agenda-ev-row">';
        if(time)html+='<span class="cal-agenda-time">'+esc(time)+'</span>';
        const sec=[evDureeTxt(ev),evAuteurTxt(ev)?('par '+evAuteurTxt(ev)):'',evParticipantsTxt(ev)]
          .filter(Boolean).join(' · ');
        html+='<div class="cal-pill cal-pill--agenda" data-ev-id="'+esc(ev.id)+'" style="'+evSlotStyle(ev)+'">'+
          evFlagHtml(ev)+esc(ev.titre)+
          (sec?'<span class="cal-pill-sec">'+esc(sec)+'</span>':'')+'</div>';
        html+='</div>';
      });
    }else{
      html+='<p class="cal-agenda-day-empty">Rien de prévu ce jour-là</p>';
    }
    html+='</div></div>';
    cur=addDays(cur,1);
  }
  if(!any)html+='<p class="cal-agenda-empty">Aucune date dans la période.</p>';
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
        const own=isOwnPerso(ev);
        const cls='cal-pill'+(own?' cal-pill--own':'')+(isBusyPerso(ev)?' cal-pill--busy':'');
        html+='<div class="'+cls+'" data-ev-id="'+esc(ev.id)+'" '+
          (own?'title="Glisser pour changer de jour · double-clic pour modifier" ':'')+
          'style="'+evSlotStyle(ev)+'">'+evFlagHtml(ev)+esc(ev.titre)+
          (own?'<span class="cal-rs-x"></span>':'')+'</div>';
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
    'z-index:'+(1+c)+';'+evSlotStyle(ev);
}

function renderDayTimedHtml(dayTimed,day,range){
  const layout=buildOverlapLayout(dayTimed,day);
  let html='';
  for(const ev of dayTimed){
    const slice=timedSliceOnDay(ev,day,range);
    if(!slice)continue;
    const lay=layout.get(layoutKey(ev))||{col:0,total:1};
    const own=isOwnPerso(ev);
    const cls='cal-ev'+(own?' cal-ev--own':'')+(isBusyPerso(ev)?' cal-ev--busy':'');
    const handles=own
      ?'<span class="cal-ev-rs cal-ev-rs-top"></span><span class="cal-ev-rs cal-ev-rs-bot"></span>':'';
    html+='<div class="'+cls+'" data-ev-id="'+esc(ev.id)+'" data-col="'+lay.col+'" data-tot="'+lay.total+'" '+
      (own?'title="Glisser pour déplacer · double-clic pour modifier" ':'')+
      'style="'+timedEvStyle(ev,slice.top,slice.h,lay.col,lay.total)+'">'+
      '<span class="cal-ev-t">'+evFlagHtml(ev)+esc(ev.titre)+'</span>'+
      evLignesHtml(ev,slice.h)+handles+'</div>';
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
    const own=isOwnPerso(ev);
    const cls='cal-mbar'+(own?' cal-mbar--own':'')+(isBusyPerso(ev)?' cal-mbar--busy':'');
    html+='<div class="'+cls+'" data-ev-id="'+esc(ev.id)+'" style="grid-column:'+colStart+' / span '+span+';grid-row:'+(ri+1)+';'+evSlotStyle(ev)+'">'+evFlagHtml(ev)+esc(ev.titre)+
      (own?'<span class="cal-rs-x"></span>':'')+'</div>';
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
  // Bandeau « Journée » sur toute la largeur : son libellé de gauche sert de
  // repère à la gouttière, et chaque jour a sa propre cellule (deux événements
  // le même jour ne débordaient pas sur le voisin).
  html+='<div class="cal-allday-row"><div class="cal-allday-label">Journée</div>';
  html+='<div class="cal-allday-cols" style="grid-template-columns:repeat('+colCount+',1fr)">';
  days.forEach(day=>{
    const dk=ymd(day);
    html+='<div class="cal-allday-cell">';
    allDay.filter(ev=>{
      const s=ymd(startOfDay(evStart(ev))),e=ymd(startOfDay(evEnd(ev)));
      return s<=dk&&e>=dk;
    }).forEach(ev=>{
      html+='<div class="cal-allday-pill'+(isBusyPerso(ev)?' cal-allday-pill--busy':'')+'" data-ev-id="'+esc(ev.id)+'" style="'+evSlotStyle(ev)+'">'+evFlagHtml(ev)+esc(ev.titre)+'</div>';
    });
    html+='</div>';
  });
  html+='</div></div>';
  html+='<div class="cal-time-body">';
  html+='<div class="cal-time-gutter"><div class="cal-col-head tg-head">&nbsp;</div>';
  for(let h=h0;h<h1;h++)html+='<div class="tg-hour">'+pad2(h)+':00</div>';
  html+='</div><div class="cal-time-grid">';
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
  html+='</div></div></div></div>';
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
document.getElementById('btn-cal-extern').onclick=()=>openExternModal();
document.querySelectorAll('.nav-btn[data-view],.cal-view-tabs .cal-btn[data-view]').forEach(b=>{
  b.onclick=()=>setView(b.dataset.view);
});
const mobileViewSel=document.getElementById('mobile-view-sel');
if(mobileViewSel)mobileViewSel.onchange=()=>setView(mobileViewSel.value);
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
    if(S.drag){cancelDrag();e.preventDefault();return;}
    if(S.externModal){closeExternModal();e.preventDefault();return;}
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

/* ---------------------------------------------------------------------
   Calendriers externes : flux ICS sortant (abonnement Outlook / Google /
   Apple) et abonnements ICS entrants affichés dans MyCalendrier.
   --------------------------------------------------------------------- */
const SUB_COLOR_DEFAULT='#38bdf8';

function applySubCalDefs(){
  for(let i=CAL_DEFS.length-1;i>=0;i--){
    if(!CAL_DEFS[i].externe)continue;
    const still=S.subs.some(s=>('sub_'+s.id)===CAL_DEFS[i].id&&s.actif);
    if(!still){
      delete S.visible[CAL_DEFS[i].id];
      CAL_DEFS.splice(i,1);
    }
  }
  S.subs.forEach(s=>{
    if(!s.actif)return;
    const id='sub_'+s.id;
    let def=CAL_DEFS.find(c=>c.id===id);
    if(!def){
      CAL_DEFS.push({id,label:s.nom,color:s.couleur||SUB_COLOR_DEFAULT,externe:true});
    }else{
      def.label=s.nom;
      def.color=s.couleur||def.color;
    }
    if(S.visible[id]===undefined)S.visible[id]=true;
  });
  saveVisible();
}
async function loadSubs(){
  try{
    const res=await api('/api/calendrier/subscriptions');
    S.subs=(res&&res.subscriptions)||[];
  }catch(e){
    S.subs=[];
    return;
  }
  applySubCalDefs();
}
async function loadFeed(){
  try{S.feed=await api('/api/calendrier/feed');}
  catch(e){S.feed=null;}
}

function closeExternModal(){
  if(S.externModal){S.externModal.remove();S.externModal=null;}
}
function fmtSyncMeta(s){
  if(s.last_status==='erreur')return{cls:'err',txt:s.last_error||'Flux injoignable.'};
  if(!s.last_sync_at)return{cls:'',txt:'Jamais synchronisé'};
  const d=parseEvDt(s.last_sync_at);
  const when=d?d.toLocaleString('fr-FR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}):s.last_sync_at;
  return{cls:'',txt:s.nb_events+' événement(s) · maj '+when};
}
function externModalBodyHtml(){
  const feed=S.feed;
  let html='<div class="cal-extern-sec first">';
  html+='<h3 class="cal-extern-h">Abonner un agenda externe à MySifa</h3>';
  html+='<p class="cal-extern-p">Collez cette adresse dans Outlook, Google Agenda ou Apple Calendrier '+
    '(« S\'abonner à un calendrier depuis le web »). Vos calendriers MySifa apparaîtront chez eux, '+
    'en lecture seule, et se mettront à jour automatiquement.</p>';
  if(feed){
    const sel=new Set(String(feed.calendriers||'').split(',').map(s=>s.trim()).filter(Boolean));
    html+='<div class="cal-feed-cals" id="cal-feed-cals">';
    accessibleCalDefs().filter(c=>!c.externe).forEach(c=>{
      html+='<label class="cal-feed-cal" style="--cal-c:'+calColor(c.id)+'">'+
        '<input type="checkbox" data-feed-cal="'+esc(c.id)+'"'+(sel.has(c.id)?' checked':'')+'>'+
        '<span class="cal-dot" style="background:'+calColor(c.id)+'"></span>'+esc(c.label)+'</label>';
    });
    html+='</div>';
    html+='<div class="cal-url-row"><input type="text" id="cal-feed-url" readonly value="'+esc(feed.url)+'">'+
      '<button type="button" class="cal-mini-btn" id="cal-feed-copy">Copier</button></div>';
    html+='<div class="cal-extern-actions">'+
      '<button type="button" class="cal-mini-btn" id="cal-feed-open">Ouvrir dans mon agenda</button>'+
      '<button type="button" class="cal-mini-btn danger" id="cal-feed-rotate">Régénérer l\'adresse</button>'+
      '</div>';
    html+='<p class="cal-extern-hint">Fenêtre publiée : '+feed.fenetre.passe_jours+
      ' jours passés / '+feed.fenetre.futur_jours+' jours à venir. « Mon calendrier » ne publie que vos créneaux et vos réunions.'+
      '<br>Cette adresse vaut mot de passe — ne la partagez pas. Régénérer coupe immédiatement les abonnements existants.</p>';
  }else{
    html+='<p class="cal-extern-hint">Adresse indisponible pour le moment.</p>';
  }
  html+='</div>';

  html+='<div class="cal-extern-sec">';
  html+='<h3 class="cal-extern-h">Afficher un agenda externe dans MySifa</h3>';
  html+='<p class="cal-extern-p">Ajoutez l\'adresse ICS d\'un agenda publié (Outlook, Google, Apple, '+
    'agenda partagé d\'un fournisseur). Ses événements apparaissent dans MyCalendrier, en lecture seule, '+
    'rafraîchis automatiquement.</p>';
  if(S.subs.length){
    S.subs.forEach(s=>{
      const m=fmtSyncMeta(s);
      html+='<div class="cal-sub-row">'+
        '<span class="cal-sub-dot" style="background:'+esc(s.couleur||SUB_COLOR_DEFAULT)+'"></span>'+
        '<div class="cal-sub-main"><div class="cal-sub-nom">'+esc(s.nom)+(s.actif?'':' · masqué')+'</div>'+
        '<div class="cal-sub-meta '+m.cls+'">'+esc(m.txt)+'</div></div>'+
        '<button type="button" class="cal-mini-btn" data-sub-refresh="'+s.id+'">Actualiser</button>'+
        '<button type="button" class="cal-mini-btn" data-sub-toggle="'+s.id+'">'+(s.actif?'Masquer':'Afficher')+'</button>'+
        '<button type="button" class="cal-mini-btn danger" data-sub-del="'+s.id+'">Retirer</button>'+
        '</div>';
    });
  }else{
    html+='<p class="cal-extern-hint">Aucun agenda externe pour l\'instant.</p>';
  }
  html+='<div class="cal-extern-form">'+
    '<input type="text" id="cal-sub-nom" maxlength="200" placeholder="Nom affiché (ex. Outlook perso)">'+
    '<input type="color" id="cal-sub-couleur" value="'+SUB_COLOR_DEFAULT+'" aria-label="Couleur">'+
    '<input class="full" type="text" id="cal-sub-url" maxlength="2000" placeholder="https://… .ics ou webcal://…">'+
    '</div>';
  html+='<div class="cal-extern-actions"><button type="button" class="cal-btn primary" id="cal-sub-add">Ajouter l\'agenda</button></div>';
  html+='<p class="cal-extern-hint">Dans Outlook : Paramètres → Calendrier → Calendriers partagés → Publier un calendrier → copier le lien ICS. '+
    'Dans Google Agenda : Paramètres du calendrier → Adresse secrète au format iCal.</p>';
  html+='</div>';
  return html;
}
function renderExternModalBody(){
  const box=S.externModal&&S.externModal.querySelector('#cal-extern-body');
  if(!box)return;
  box.innerHTML=externModalBodyHtml();
  bindExternModalBody();
}
function bindExternModalBody(){
  const wrap=S.externModal;
  if(!wrap)return;
  const copy=wrap.querySelector('#cal-feed-copy');
  if(copy)copy.onclick=copyFeedUrl;
  const open=wrap.querySelector('#cal-feed-open');
  if(open)open.onclick=()=>{
    if(S.feed&&S.feed.webcal_url)window.location.href=S.feed.webcal_url;
  };
  const rot=wrap.querySelector('#cal-feed-rotate');
  if(rot)rot.onclick=rotateFeedUrl;
  wrap.querySelectorAll('[data-feed-cal]').forEach(inp=>{
    inp.onchange=()=>saveFeedCalendars(inp);
  });
  const add=wrap.querySelector('#cal-sub-add');
  if(add)add.onclick=addSubscription;
  wrap.querySelectorAll('[data-sub-refresh]').forEach(b=>{
    b.onclick=()=>refreshSubscription(parseInt(b.dataset.subRefresh,10));
  });
  wrap.querySelectorAll('[data-sub-toggle]').forEach(b=>{
    b.onclick=()=>toggleSubscription(parseInt(b.dataset.subToggle,10));
  });
  wrap.querySelectorAll('[data-sub-del]').forEach(b=>{
    b.onclick=()=>removeSubscription(parseInt(b.dataset.subDel,10));
  });
}
async function openExternModal(){
  closeExternModal();
  closePop();
  const root=document.getElementById('cal-extern-modal-root');
  if(!root)return;
  const wrap=document.createElement('div');
  wrap.className='cal-create-modal-backdrop';
  wrap.innerHTML='<div class="cal-create-modal cal-create-modal--lg" role="dialog" aria-labelledby="cal-extern-title">'+
    '<button type="button" class="cal-create-modal-close" aria-label="Fermer">×</button>'+
    '<h2 id="cal-extern-title">Calendriers externes</h2>'+
    '<div id="cal-extern-body"><p class="cal-extern-hint">Chargement…</p></div>'+
    '<div class="cal-create-modal-foot"><button type="button" class="cal-btn" id="cal-extern-close">Fermer</button></div>'+
    '</div>';
  root.appendChild(wrap);
  S.externModal=wrap;
  wrap.onclick=e=>{if(e.target===wrap)closeExternModal();};
  wrap.querySelector('.cal-create-modal').onclick=e=>{
    e.stopPropagation();
    if(!e.target.closest('.cal-part-box'))masquerResultats();
  };
  wrap.querySelector('.cal-create-modal-close').onclick=closeExternModal;
  wrap.querySelector('#cal-extern-close').onclick=closeExternModal;
  await Promise.all([loadFeed(),loadSubs()]);
  if(!S.externModal)return;
  renderExternModalBody();
  renderToggles();
}
function copyFeedUrl(){
  const inp=document.getElementById('cal-feed-url');
  if(!inp)return;
  const txt=inp.value;
  const fallback=()=>{
    try{inp.select();document.execCommand('copy');showToast('Adresse copiée.','success');}
    catch(e){showToast('Copie impossible — sélectionnez l\'adresse manuellement.','danger');}
  };
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(()=>showToast('Adresse copiée.','success')).catch(fallback);
  }else fallback();
}
async function saveFeedCalendars(changed){
  const boxes=Array.from(document.querySelectorAll('[data-feed-cal]'));
  const cals=boxes.filter(b=>b.checked).map(b=>b.dataset.feedCal);
  if(!cals.length){
    if(changed)changed.checked=true;
    showToast('Au moins un calendrier doit être publié.','danger');
    return;
  }
  boxes.forEach(b=>{b.disabled=true;});
  try{
    S.feed=await api('/api/calendrier/feed',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({calendriers:cals.join(',')})
    });
    showToast('Flux mis à jour.','success');
  }catch(e){
    showToast(e.message||'Mise à jour impossible','danger');
  }
  renderExternModalBody();
}
async function rotateFeedUrl(){
  if(!window.confirm('Régénérer l\'adresse ? Les agendas déjà abonnés cesseront de se mettre à jour.'))return;
  try{
    S.feed=await api('/api/calendrier/feed/rotate',{method:'POST'});
    renderExternModalBody();
    showToast('Nouvelle adresse générée.','success');
  }catch(e){
    showToast(e.message||'Régénération impossible','danger');
  }
}
async function addSubscription(){
  const nom=(document.getElementById('cal-sub-nom')?.value||'').trim();
  const url=(document.getElementById('cal-sub-url')?.value||'').trim();
  const couleur=document.getElementById('cal-sub-couleur')?.value||SUB_COLOR_DEFAULT;
  if(!nom){showToast('Nom requis.','danger');return;}
  if(!url){showToast('Adresse ICS requise.','danger');return;}
  try{
    const res=await api('/api/calendrier/subscriptions',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({nom,url,couleur})
    });
    await loadSubs();
    renderExternModalBody();
    renderToggles();
    fetchEvents();
    if(res&&res.warning)showToast('Agenda ajouté — '+res.warning,'danger');
    else showToast('Agenda ajouté.','success');
  }catch(e){
    showToast(e.message||'Ajout impossible','danger');
  }
}
async function refreshSubscription(id){
  if(!id)return;
  try{
    await api('/api/calendrier/subscriptions/'+id+'/refresh',{method:'POST'});
    await loadSubs();
    renderExternModalBody();
    fetchEvents();
    showToast('Agenda actualisé.','success');
  }catch(e){
    await loadSubs();
    renderExternModalBody();
    showToast(e.message||'Actualisation impossible','danger');
  }
}
async function toggleSubscription(id){
  const sub=S.subs.find(s=>s.id===id);
  if(!sub)return;
  try{
    await api('/api/calendrier/subscriptions/'+id,{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({actif:!sub.actif})
    });
    await loadSubs();
    renderExternModalBody();
    renderToggles();
    fetchEvents();
  }catch(e){
    showToast(e.message||'Modification impossible','danger');
  }
}
async function removeSubscription(id){
  const sub=S.subs.find(s=>s.id===id);
  if(!sub)return;
  if(!window.confirm('Retirer « '+sub.nom+' » de MyCalendrier ?'))return;
  try{
    await api('/api/calendrier/subscriptions/'+id,{method:'DELETE'});
    await loadSubs();
    renderExternModalBody();
    renderToggles();
    fetchEvents();
    showToast('Agenda retiré.','success');
  }catch(e){
    showToast(e.message||'Suppression impossible','danger');
  }
}

function bootCalendrier(){
  S.view=loadSavedView();
  applyMobileDefaultView();
}

document.addEventListener('DOMContentLoaded',bootCalendrier);
let _calResizeTimer=null;
window.addEventListener('resize',()=>{
  clearTimeout(_calResizeTimer);
  _calResizeTimer=setTimeout(()=>{
    if(!isMobileViewport())return;
    if(S.view==='agenda')return;
    setView('agenda');
  },180);
});

(async function init(){
  try{
    bootCalendrier();
    applyTheme();
    loadVisible();
    await loadSubs();
    applyCalListOpen(loadCalListOpen());
    const calHead=document.getElementById('cal-cals-head');
    if(calHead)calHead.addEventListener('click',toggleCalList);
    const delegBtn=document.getElementById('btn-cal-deleg');
    if(delegBtn)delegBtn.addEventListener('click',()=>{openDelegationsModal().catch(()=>{});});
    renderToggles();
    bindRecherche();
    lireLienDirect();
    applyViewChrome(S.view);
    ME=await api('/api/auth/me');
    if(!ME){
      location.href='/?next=/calendrier';
      return;
    }
    window.__MYSIFA_UID__=ME.id;
    window.__MYSIFA_NOM__=ME.nom||'';
    window.__MYSIFA_ROLE__=ME.role||'';
    window.__MYSIFA_USER__={nom:ME.nom||'',role:ME.role||''};
    if(window._CW&&typeof window._CW.ensureReady==='function')await window._CW.ensureReady();
    else if(window._CW&&typeof window._CW.syncUser==='function')window._CW.syncUser();
    if(window.MySifaDock&&typeof window.MySifaDock.bootPageWidgets==='function'){
      window.MySifaDock.bootPageWidgets();
    }else if(typeof initAiChatWidget==='function'){
      initAiChatWidget();
      if(window.MySifaDock&&typeof window.MySifaDock.layout==='function')window.MySifaDock.layout();
    }
    if(window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    else if(window.MySifaCalendar)MySifaCalendar.mergeFromUser(ME);
    renderToggles();
    initSelecteurCollegue().catch(()=>{});
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
<script src="/static/mysifa_impersonate.js"></script>
</body>
</html>
"""
