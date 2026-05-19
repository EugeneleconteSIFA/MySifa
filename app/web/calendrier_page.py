"""MySifa — MyCalendrier (super administrateur)."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user, is_superadmin
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
    if not is_superadmin(user):
        return access_denied_response(
            "MyCalendrier",
            detail="Cette application est réservée au super administrateur.",
        )
    return HTMLResponse(content=CALENDRIER_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


CALENDRIER_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Calendrier — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
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
.cal-section-label{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);padding:4px 12px 8px}
.cal-toggle{display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:12px;color:var(--text2);user-select:none}
.cal-toggle:hover{background:var(--accent-bg)}
.cal-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;background:var(--cal-c)}
.cal-toggle span.flex1{flex:1}
.cal-toggle input{appearance:none;width:16px;height:16px;border:2px solid var(--border);border-radius:4px;background:var(--bg);cursor:pointer;position:relative;flex-shrink:0}
.cal-toggle input:checked{background:var(--cal-c);border-color:var(--cal-c)}
.cal-toggle input:checked::after{content:'';position:absolute;left:4px;top:1px;width:4px;height:8px;border:solid #0a0e17;border-width:0 2px 2px 0;transform:rotate(45deg)}
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
.cal-month{display:flex;flex-direction:column;gap:0;min-width:720px}
.cal-month-head{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;margin-bottom:4px}
.cal-month-head div{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);text-align:center;padding:6px 4px}
.cal-week{border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:8px;background:var(--card)}
.cal-week-bars{position:relative;min-height:0;display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:var(--border)}
.cal-week-bars:empty{display:none}
.cal-mbar{margin:2px 2px 0;padding:2px 6px;font-size:10px;font-weight:700;border-radius:4px;color:#0a0e17;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;grid-row:1}
.cal-days{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:var(--border)}
.cal-day{min-height:100px;background:var(--bg);padding:6px;display:flex;flex-direction:column;gap:4px}
.cal-day.other{opacity:.45}
.cal-day.today{box-shadow:inset 0 0 0 2px var(--accent)}
.cal-day-num{font-size:12px;font-weight:700;color:var(--text2);flex-shrink:0}
.cal-day.other .cal-day-num{color:var(--muted)}
.cal-day-events{flex:1;display:flex;flex-direction:column;gap:3px;min-height:0}
.cal-pill{font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#0a0e17;line-height:1.35}
.cal-more{font-size:10px;color:var(--muted);font-weight:700;padding:0 4px;cursor:pointer}
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
.cal-allday-pill{font-size:10px;font-weight:600;padding:2px 6px;border-radius:4px;margin:2px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#0a0e17}
.cal-cols-row{flex:1;display:grid;position:relative}
.cal-col{border-left:1px solid var(--border);position:relative}
.cal-col:first-child{border-left:none}
.cal-col-head{text-align:center;font-size:11px;font-weight:700;padding:8px 4px;border-bottom:1px solid var(--border);background:var(--bg)}
.cal-col-head.today{color:var(--accent)}
.cal-col-slots{position:relative;height:1152px;width:100%;overflow:visible}
.cal-col{min-width:0;overflow:visible}
.cal-slot-line{position:absolute;left:0;right:0;height:1px;background:var(--border)}
.cal-ev{
  position:absolute;border-radius:6px;padding:4px 6px;font-size:10px;font-weight:700;color:#0a0e17;
  overflow:hidden;cursor:pointer;line-height:1.3;box-sizing:border-box;
}
.cal-day-single .cal-cols-row{grid-template-columns:1fr}
/* Popover */
.cal-pop{position:fixed;z-index:8000;min-width:240px;max-width:320px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 16px 48px rgba(0,0,0,.45)}
.cal-pop-title{font-size:14px;font-weight:800;margin-bottom:6px;line-height:1.35}
.cal-pop-meta{font-size:12px;color:var(--text2);line-height:1.6;margin-bottom:10px}
.cal-pop a{font-size:12px;font-weight:700;color:var(--accent);text-decoration:none}
.cal-pop a:hover{text-decoration:underline}
.cal-pop-close{position:absolute;top:8px;right:10px;border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:18px;line-height:1;padding:4px}
.toast{position:fixed;bottom:22px;right:22px;z-index:9999;padding:11px 16px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 10px 36px rgba(0,0,0,.4);border:1px solid var(--border)}
.toast.success{background:rgba(52,211,153,.15);color:var(--ok)}
.toast.danger{background:rgba(248,113,113,.15);color:var(--danger)}
@media(max-width:900px){
  .mobile-topbar{display:flex}
  .mobile-menu-btn,.mobile-home-btn{display:inline-flex}
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  body.has-topbar .main{padding-top:0}
  .cal-title{font-size:14px;min-width:120px}
}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
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
    <hr>
    <div class="cal-section-label">Calendriers</div>
    <div id="cal-toggles"></div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" onclick="location.href='/profil'" title="Mon profil">
        <div class="uc-name" id="uc-name">—</div>
        <div class="uc-role" id="uc-role">—</div>
      </div>
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
      </div>
      <div class="cal-title" id="cal-title">—</div>
      <div class="cal-view-tabs">
        <button type="button" class="cal-btn" data-view="month">Mois</button>
        <button type="button" class="cal-btn" data-view="week">Semaine</button>
        <button type="button" class="cal-btn" data-view="day">Jour</button>
      </div>
    </div>
    <div class="cal-body" id="cal-body">
      <div class="cal-loading" id="cal-loading">Chargement…</div>
    </div>
  </main>
</div>
<script>
const CAL_DEFS=[
  {id:'production_1',label:'Cohésio 1',color:'#22d3ee'},
  {id:'production_2',label:'Cohésio 2',color:'#3A7BD5'},
  {id:'production_3',label:'DSI',color:'#a78bfa'},
  {id:'production_4',label:'Repiquage',color:'#34d399'},
  {id:'conges',label:'Congés',color:'#fbbf24'},
  {id:'anniversaires',label:'Anniversaires',color:'#34d399'},
  {id:'feries',label:'Jours fériés',color:'#f87171'},
  {id:'paie',label:'Paie',color:'#a78bfa'},
  {id:'expeditions',label:'Expéditions',color:'#f97316'}
];
const PROD_CAL_IDS=['production_1','production_2','production_3','production_4'];
const LS_VISIBLE='mysifa_cal_visible';
const MOIS=['','janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
const JOURS=['lun','mar','mer','jeu','ven','sam','dim'];
const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};

let S={view:'month',anchor:new Date(),events:[],loading:false,visible:{},pop:null};
let ME=null;

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
        CAL_DEFS.forEach(c=>{S.visible[c.id]=o[c.id]!==false;});
        return;
      }
    }
  }catch(e){}
  CAL_DEFS.forEach(c=>{S.visible[c.id]=true;});
}
function saveVisible(){
  try{localStorage.setItem(LS_VISIBLE,JSON.stringify(S.visible));}catch(e){}
}

function renderToggles(){
  const box=document.getElementById('cal-toggles');
  if(!box)return;
  box.innerHTML=CAL_DEFS.map(c=>`
    <label class="cal-toggle" style="--cal-c:${c.color}">
      <span class="cal-dot"></span>
      <span class="flex1">${esc(c.label)}</span>
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
  return CAL_DEFS.filter(c=>S.visible[c.id]).map(c=>c.id);
}
function calColor(id){const c=CAL_DEFS.find(x=>x.id===id);return c?c.color:'var(--accent)';}

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
/** Intervalle [début, fin] d'un événement sur un jour donné (ms). */
function evClipOnDay(ev,day){
  const s=evStart(ev),e=evEnd(ev)||s;
  if(!s||!evOverlapsDay(ev,day))return null;
  const d0=startOfDay(day);
  const dEnd=new Date(d0);dEnd.setHours(23,59,59,999);
  const clipS=s<d0?d0:s;
  const clipE=e>dEnd?dEnd:e;
  if(clipE<=clipS)return null;
  return{start:clipS.getTime(),end:clipE.getTime()};
}
/** Tranche horaire d'un événement sur un jour (vues semaine / jour). */
function timedSliceOnDay(ev,day){
  const clip=evClipOnDay(ev,day);
  if(!clip)return null;
  const d0=startOfDay(day);
  const topMin=(clip.start-d0.getTime())/60000;
  const endMin=(clip.end-d0.getTime())/60000;
  return{top:topMin/60*48,h:Math.max(18,(endMin-topMin)/60*48)};
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

async function api(path){
  const r=await fetch(path,{credentials:'include'});
  if(r.status===401){location.href='/?next=/calendrier';throw new Error('auth');}
  if(r.status===403){showToast('Accès réservé au super administrateur.','danger');throw new Error('auth');}
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
    S.events=(await api('/api/calendrier/events?'+q))||[];
    if(loading)loading.style.display='none';
    renderCalendar();
  }catch(e){
    if(e.message!=='auth')showToast(e.message||'Chargement impossible','danger');
    if(loading)loading.textContent='Erreur de chargement.';
  }finally{S.loading=false;}
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
  let link='';
  if(ev.calendrier.startsWith('production_'))link='<a href="/planning">Ouvrir le planning production</a>';
  else if(ev.calendrier==='conges')link='<a href="/planning-rh">Ouvrir le planning RH</a>';
  else if(ev.calendrier==='expeditions')link='<a href="/expe">Ouvrir MyExpé</a>';
  const pop=document.createElement('div');
  pop.className='cal-pop';
  pop.innerHTML='<button type="button" class="cal-pop-close" aria-label="Fermer">×</button>'+
    '<div class="cal-pop-title">'+esc(ev.titre)+'</div>'+
    '<div class="cal-pop-meta">'+esc(CAL_DEFS.find(c=>c.id===ev.calendrier)?.label||ev.calendrier)+'<br>'+per+stat+'</div>'+
    (link?'<div>'+link+'</div>':'');
  document.body.appendChild(pop);
  S.pop=pop;
  pop.querySelector('.cal-pop-close').onclick=closePop;
  const rect=anchorEl.getBoundingClientRect();
  let top=rect.bottom+8,left=rect.left;
  if(left+pop.offsetWidth>window.innerWidth-12)left=window.innerWidth-pop.offsetWidth-12;
  if(top+pop.offsetHeight>window.innerHeight-12)top=rect.top-pop.offsetHeight-8;
  pop.style.top=Math.max(8,top)+'px';
  pop.style.left=Math.max(8,left)+'px';
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
  const p=getPeriod();
  document.getElementById('cal-title').textContent=p.title;
  const body=document.getElementById('cal-body');
  if(S.view==='month')body.innerHTML=renderMonth(p);
  else if(S.view==='week')body.innerHTML=renderTimeGrid(p,7);
  else body.innerHTML=renderTimeGrid(p,1);
  bindRenderedEvents();
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
    if(!evVisible(ev))return false;
    const s=evStart(ev),e=evEnd(ev);
    if(!s)return false;
    return ymd(startOfDay(s))<=dk&&ymd(startOfDay(e||s))>=dk;
  });
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
  JOURS.forEach(j=>{html+='<div>'+j+'</div>';});
  html+='</div>';
  weeks.forEach(days=>{
    html+='<div class="cal-week">';
    html+=renderWeekBars(days);
    html+='<div class="cal-days">';
    days.forEach(day=>{
      const other=day.getMonth()!==month;
      const evs=eventsOnDay(day);
      const singles=evs.filter(e=>!isMultiDay(e));
      const show=singles.slice(0,3);
      const more=singles.length-show.length;
      html+='<div class="cal-day'+(other?' other':'')+(isToday(day)?' today':'')+'">';
      html+='<div class="cal-day-num">'+day.getDate()+'</div>';
      html+='<div class="cal-day-events">';
      show.forEach(ev=>{
        html+='<div class="cal-pill" data-ev-id="'+esc(ev.id)+'" style="background:'+calColor(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
      });
      if(more)html+='<div class="cal-more">+'+more+'</div>';
      html+='</div></div>';
    });
    html+='</div></div>';
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
  return 'top:'+top+'px;height:'+h+'px;left:'+pctL+'%;width:'+pctW+'%;'+
    'z-index:'+(1+c)+';background:'+calColor(ev.calendrier);
}

function renderDayTimedHtml(dayTimed,day){
  const layout=buildOverlapLayout(dayTimed,day);
  let html='';
  for(const ev of dayTimed){
    const slice=timedSliceOnDay(ev,day);
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
    if(!evVisible(ev)||!isMultiDay(ev))return false;
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
    html+='<div class="cal-mbar" data-ev-id="'+esc(ev.id)+'" style="grid-column:'+colStart+' / span '+span+';grid-row:'+(ri+1)+';background:'+calColor(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
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
    if(!evVisible(ev))return;
    if(ev.all_day)allDay.push(ev);
    else timed.push(ev);
  });
  let html='<div class="cal-time-wrap'+(colCount===1?' cal-day-single':'')+'">';
  html+='<div class="cal-time-gutter"><div style="height:32px;border-bottom:1px solid var(--border)"></div>';
  for(let h=0;h<24;h++)html+='<div class="tg-hour">'+pad2(h)+':00</div>';
  html+='</div><div class="cal-time-grid">';
  html+='<div class="cal-allday-row"><div class="cal-allday-label">Journée</div>';
  html+='<div class="cal-allday-cols" style="grid-template-columns:repeat('+colCount+',1fr)">';
  days.forEach((day,ci)=>{
    const dk=ymd(day);
    allDay.filter(ev=>{
      const s=ymd(startOfDay(evStart(ev))),e=ymd(startOfDay(evEnd(ev)));
      return s<=dk&&e>=dk;
    }).forEach(ev=>{
      html+='<div class="cal-allday-pill" data-ev-id="'+esc(ev.id)+'" style="background:'+calColor(ev.calendrier)+'">'+esc(ev.titre)+'</div>';
    });
  });
  html+='</div></div>';
  html+='<div class="cal-cols-row" style="grid-template-columns:repeat('+colCount+',1fr)">';
  days.forEach(day=>{
    html+='<div class="cal-col"><div class="cal-col-head'+(isToday(day)?' today':'')+'">'+
      day.toLocaleDateString('fr-FR',{weekday:'short',day:'numeric',month:'short'})+'</div>';
    html+='<div class="cal-col-slots">';
    for(let h=0;h<24;h++)html+='<div class="cal-slot-line" style="top:'+(h*48)+'px"></div>';
    html+=renderDayTimedHtml(timed.filter(ev=>evOverlapsDay(ev,day)),day);
    html+='</div></div>';
  });
  html+='</div></div></div>';
  return html;
}

function setView(v){
  S.view=v;
  document.querySelectorAll('.nav-btn[data-view]').forEach(b=>{
    b.classList.toggle('active',b.dataset.view===v);
  });
  document.querySelectorAll('.cal-view-tabs .cal-btn[data-view]').forEach(b=>{
    b.classList.toggle('primary',b.dataset.view===v);
  });
  const subs={month:'Vue mensuelle',week:'Vue hebdomadaire',day:'Vue journalière'};
  const sub=document.getElementById('mobile-sub');
  if(sub)sub.textContent=subs[v]||'';
  fetchEvents();
}

function shiftAnchor(delta){
  const a=new Date(S.anchor);
  if(S.view==='month')a.setMonth(a.getMonth()+delta);
  else if(S.view==='week')a.setDate(a.getDate()+delta*7);
  else a.setDate(a.getDate()+delta);
  S.anchor=a;
  fetchEvents();
}

document.getElementById('btn-prev').onclick=()=>shiftAnchor(-1);
document.getElementById('btn-next').onclick=()=>shiftAnchor(1);
document.getElementById('btn-today').onclick=()=>{S.anchor=new Date();fetchEvents();};
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

(async function init(){
  try{
    applyTheme();
    loadVisible();
    renderToggles();
    document.querySelectorAll('.cal-view-tabs .cal-btn[data-view="month"]')[0]?.classList.add('primary');
    ME=await api('/api/auth/me');
    if(!ME){
      location.href='/?next=/calendrier';
      return;
    }
    if(window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    const ucName=document.getElementById('uc-name');
    const ucRole=document.getElementById('uc-role');
    if(ucName)ucName.textContent=ME.nom||'—';
    if(ucRole)ucRole.textContent=ROLE_LABELS[ME.role]||ME.role||'—';
    syncThemeBtn();
    await fetchEvents();
  }catch(e){
    if(e.message!=='auth')showToast(e.message||'Initialisation impossible','danger');
  }
})();
</script>
</body>
</html>
"""
