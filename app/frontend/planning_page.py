"""SIFA — Page Planning v1.1 (standalone)

Ajouter dans main.py :
    from frontend.planning_page import router as planning_page_router
    app.include_router(planning_page_router)

Accès : /planning  ou  /planning?machine=<id SQLite réel>
"""

from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from services.auth_service import get_current_user
from config import APP_META_DESCRIPTION, APP_PLANNING_PAGE_TITLE, APP_VERSION, THEME_COLOR_META

router = APIRouter()


@router.get("/planning", response_class=HTMLResponse)
def planning_page(request: Request, machine: Optional[int] = None):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            nxt = "/planning"
            if machine is not None:
                nxt = f"/planning?machine={machine}"
            return RedirectResponse(url=f"/?next={nxt}", status_code=302)
        raise
    if user.get("role") not in {"direction", "administration", "fabrication"}:
        raise HTTPException(status_code=403, detail="Accès réservé au planning")
    # 0 = laisser le JS choisir l’id réel après /api/planning/machines (évite de forcer
    # ?machine=1 implicite alors que l’id SQLite « Cohésio 1 » n’est pas 1 en prod).
    ssr_mid = str(machine) if machine is not None else "0"
    html = (
        PLANNING_HTML.replace("__MACHINE_ID__", ssr_mid)
        .replace("__PLANNING_TITLE__", APP_PLANNING_PAGE_TITLE)
        .replace("__META_DESCRIPTION__", APP_META_DESCRIPTION)
        .replace("__THEME_COLOR__", THEME_COLOR_META)
        .replace("__V_LABEL__", f"v{APP_VERSION}")
    )
    return HTMLResponse(content=html)


PLANNING_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="__META_DESCRIPTION__">
<meta name="theme-color" content="__THEME_COLOR__">
<link rel="icon" type="image/png" sizes="512x512" href="/static/mys_icon_512.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<title>__PLANNING_TITLE__</title>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#94a3b8;
  --muted:#64748b;--accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --success:#34d399;--warn:#fbbf24;--danger:#f87171;
  --c1:#22d3ee;--c2:#a78bfa;--c3:#34d399;--c4:#fbbf24;--c5:#f87171;
  --blue:#38bdf8;--purple:#a78bfa;--mono:ui-monospace,'Cascadia Code',monospace;--sans:'Segoe UI',system-ui,sans-serif;
  --bg-dark:#080c12;--border2:#334155;--dim:#94a3b8;
  --green:var(--success);--red:var(--danger);--amber:var(--warn);
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#94a3b8;--accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --success:#059669;--warn:#d97706;--danger:#dc2626;
  --c1:#0891b2;--c2:#7c3aed;--c3:#059669;--c4:#d97706;--c5:#dc2626;
  --blue:#0ea5e9;--purple:#7c3aed;--bg-dark:#e2e8f0;--border2:#cbd5e1;--dim:#64748b;
}
body{font-family:var(--sans);background:var(--bg);color:var(--text);min-height:100vh}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.app{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}.sidebar{scrollbar-width:none}
.logo{padding:0 8px;margin-bottom:32px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:all .15s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.theme-btn .theme-ico{font-size:14px;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode: standalone), (max-width: 900px){
  .theme-btn .theme-label{display:none}
  .theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:28px;overflow-y:auto}
.planning-container{max-width:1400px;margin:0 auto}

.header{padding:0 0 20px;margin-bottom:4px;border-bottom:1px solid var(--border);display:flex;align-items:center;
  justify-content:space-between;flex-wrap:wrap;gap:12px}
.h-left{display:flex;align-items:center;gap:16px}
.m-title{font-size:22px;font-weight:700;color:var(--text)}
.m-sel{
  font-size:14px;font-weight:800;color:var(--text);
  font-family:var(--mono);
  background:var(--card);border:1px solid var(--border2);border-radius:12px;
  padding:10px 12px;cursor:pointer;outline:none;
  transition:all .15s;max-width:min(520px,72vw)
}
.m-sel:hover{border-color:var(--accent);background:var(--accent-bg)}
.m-sel:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.m-sel option{background:var(--card);color:var(--text)}
.m-sub{font-size:12px;color:var(--muted)}
.h-right{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.gear-btn{
  width:36px;height:36px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;
  border:1px solid var(--border2);background:var(--card);color:var(--dim);cursor:pointer;
  transition:all .15s;font-size:16px;line-height:1
}
.gear-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.back-top{
  display:flex;align-items:center;gap:8px;
  padding:8px 14px;border-radius:10px;
  border:none;
  color:var(--text2);text-decoration:none;
  font-size:12px;font-weight:400;font-family:var(--sans);
  transition:all .15s;
}
.back-top:hover{color:var(--text);background:transparent}
.back-top .wm{font-weight:800;color:var(--text);letter-spacing:-.2px}
.back-top .wm span{color:var(--accent)}

.sat-tog{display:flex;align-items:center;gap:10px;padding:8px 16px;border-radius:10px;cursor:pointer;
  border:1px solid var(--border2);background:var(--card);transition:all .3s;user-select:none}
.sat-tog.on{background:#1a1a3a;border-color:rgba(124,58,237,.4)}
.track{width:38px;height:20px;border-radius:10px;position:relative;background:#3a3a5a;transition:background .3s}
.sat-tog.on .track{background:var(--purple)}
.thumb{width:16px;height:16px;border-radius:50%;background:#fff;position:absolute;top:2px;left:2px;
  transition:left .3s;box-shadow:0 1px 4px rgba(0,0,0,.3)}
.sat-tog.on .thumb{left:20px}
.sat-lbl{font-size:12px;font-weight:600;font-family:var(--mono);color:#6b7280;transition:color .3s}
.sat-tog.on .sat-lbl{color:#c4b5fd}

.badge{padding:8px 16px;border-radius:10px;font-size:13px;font-family:var(--mono)}
.badge-run{background:#0f2a1a;border:1px solid #166534;color:#86efac;display:flex;align-items:center;gap:8px}
body.light .badge-run{background:rgba(16,185,129,.14);border-color:#059669;color:#047857}
.badge-run .dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
.badge-info{background:var(--card);border:1px solid var(--border2);color:var(--dim)}

.sec{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:28px}
.sec-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.sec-title{font-size:16px;font-weight:600;color:var(--text2)}

.wk-nav{display:flex;gap:0;align-items:center}
.wk-nav button{padding:6px 12px;background:var(--card);border:1px solid var(--border2);
  color:var(--dim);cursor:pointer;font-size:14px;font-family:var(--mono)}
.wk-nav button:first-child{border-radius:8px 0 0 8px}
.wk-nav button:last-child{border-radius:0 8px 8px 0}
.wk-nav button:hover{background:var(--border)}
.wk-nav .today{padding:6px 16px;font-size:12px}

.wk-lbl{font-size:13px;font-weight:600;font-family:var(--mono);margin-bottom:8px}
.wk-lbl.cur{color:var(--blue)}.wk-lbl.nxt{color:var(--dim)}
.tl-wrap{position:relative;margin-bottom:16px}
.dh{display:flex;margin-bottom:4px}
.dh-cell{text-align:center;padding:6px 0;font-size:12px;font-weight:600;font-family:var(--mono);
  color:var(--muted);border-bottom:1px solid var(--border)}
.dh-cell.today{color:var(--blue);border-bottom:2px solid var(--accent)}
.dh-cell.sat{color:#c084fc;border-bottom:2px solid rgba(124,58,237,.3)}
.dh-cell small{display:block;font-size:10px;opacity:.6;margin-top:2px}
.dh-hours-btn{display:block;margin:2px auto 0;padding:2px 8px;border-radius:6px;border:1px solid var(--border2);
  background:transparent;color:var(--muted);font-size:10px;font-family:var(--mono);cursor:pointer;opacity:.85;transition:all .15s}
.dh-hours-btn:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg);opacity:1}
.tl-bar{position:relative;height:56px;background:var(--bg-dark);border-radius:8px;
  border:1px solid var(--border);overflow:visible}
.d-sep{position:absolute;top:0;bottom:0;width:1px;background:var(--border2)}
.slot{position:absolute;top:6px;bottom:6px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;cursor:pointer;transition:all .15s;overflow:hidden;padding:2px 4px}
.slot:hover{top:4px;bottom:4px;z-index:20}
.slot-inner{display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.15;
  text-align:center;max-width:100%;pointer-events:none}
.slot .line1{font-size:11px;color:#fff;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.slot .line2{font-size:9px;font-weight:500;color:rgba(255,255,255,.88);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
body.light .slot .line1{color:#0f172a}body.light .slot .line2{color:#334155}
.now-l{position:absolute;top:0;bottom:0;width:2px;background:var(--red);z-index:15;box-shadow:0 0 8px var(--red)}
.now-d{position:absolute;top:-4px;left:-4px;width:10px;height:10px;border-radius:50%;background:var(--red)}

.tip{position:absolute;z-index:100;background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:14px 18px;
  min-width:240px;max-width:320px;pointer-events:none;animation:tipIn .15s ease;
  box-shadow:0 12px 40px rgba(0,0,0,.6)}
.tip-hdr{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.tip-bar{width:6px;height:32px;border-radius:3px;flex-shrink:0}
.tip-ref{font-size:13px;font-weight:700;color:var(--text);font-family:var(--mono)}
.tip-lbl{font-size:12px;color:var(--text2);margin-top:2px}
.tip-grid{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;font-size:11px;
  border-top:1px solid var(--border2);padding-top:10px}
.tip-grid .k{color:var(--muted)}.tip-grid .v{color:var(--text2);font-family:var(--mono)}

.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)}
.lg-i{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim)}
.lg-d{width:10px;height:10px;border-radius:3px}.lg-i span{font-family:var(--mono)}

.th{display:grid;grid-template-columns:22px 22px 14px minmax(96px,1.2fr) minmax(64px,.75fr) minmax(64px,.75fr) minmax(64px,.75fr) minmax(44px,.45fr) minmax(72px,.65fr) 40px minmax(110px,1.0fr) 74px;
  gap:6px;padding:10px 10px;background:var(--bg-dark);border-radius:10px 10px 0 0;
  font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600;font-family:var(--mono);align-items:center}
.th>span{min-width:0}
.th .act-c{text-align:right}
.tr{display:grid;grid-template-columns:22px 22px 14px minmax(96px,1.2fr) minmax(64px,.75fr) minmax(64px,.75fr) minmax(64px,.75fr) minmax(44px,.45fr) minmax(72px,.65fr) 40px minmax(110px,1.0fr) 74px;
  gap:6px;padding:10px 10px;border-bottom:1px solid var(--border);font-size:12px;align-items:center;
  cursor:grab;transition:background .2s;background:var(--bg-dark)}
.tr:first-child{background:var(--accent-bg)}
.tr.dov{background:var(--accent-bg);opacity:.95}.tr.dra{opacity:.5}
.tr.drop-before{box-shadow:0 -3px 0 0 var(--accent) inset}
.tr.drop-after{box-shadow:0 3px 0 0 var(--accent) inset}
.dh-handle{color:var(--muted);font-size:14px;cursor:grab;user-select:none}
body.light .tr{background:var(--card)}
body.light .tr:first-child{background:var(--accent-bg)}
body.light .th{background:var(--bg)}
.cd{width:8px;height:8px;border-radius:50%}
.ref{font-family:var(--mono);font-weight:600;color:var(--text2)}
.cell-mini{font-size:11px;color:var(--text2);font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ref.run{color:var(--blue)}
.lbl{overflow:hidden;max-width:100%}
.lbl-main{display:block;font-weight:600;color:var(--text);font-size:13px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
.lbl-sub{display:block;font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:2px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
.lbl-meta{display:block;font-size:11px;color:var(--text2);margin-top:2px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
.fmt{font-family:var(--mono);color:var(--dim);font-size:12px}
.dur{font-family:var(--mono);color:var(--dim)}
.st{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.st.run{background:#0f2a1a;color:var(--green);border:1px solid #166534}
.st.att{background:#1a1520;color:var(--amber);border:1px solid #78350f}
.st.ter{background:var(--card);color:#6b7280;border:1px solid var(--border2)}
.statut-select{width:100%;padding:6px 10px;background:var(--bg);border:1px solid var(--border2);
  border-radius:10px;color:var(--text2);font-size:11px;font-family:var(--mono);outline:none}
.statut-select:focus{border-color:var(--accent);color:var(--text)}
.acts{display:flex;gap:6px;justify-content:flex-end}
.ab{padding:4px 8px;background:transparent;border:1px solid var(--border2);color:var(--text2);
  cursor:pointer;font-size:11px;border-radius:6px;font-family:var(--mono)}
.ab:hover{background:var(--accent-bg);color:var(--accent)}
.ab.del{color:var(--red)}.ab.del:hover{background:rgba(248,113,113,.12)}
.ab.mov{width:28px;display:none;align-items:center;justify-content:center;padding:4px 0}
.ab.mov{display:none}
@media (max-width:900px){
  .ab.mov{display:inline-flex}
}
.ab:disabled{opacity:.45;cursor:not-allowed}
.ab:disabled:hover{background:transparent;color:var(--text2);border-color:var(--border2)}

.btn-p{padding:8px 20px;background:var(--accent);color:var(--bg);border:none;border-radius:8px;
  cursor:pointer;font-size:13px;font-weight:600;font-family:var(--mono);display:flex;align-items:center;gap:8px}
.btn-p:hover{filter:brightness(1.08)}
body.light .btn-p{color:#fff}

.mo{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;
  justify-content:center;z-index:1000;backdrop-filter:blur(4px)}
.md{background:var(--card);border:1px solid var(--border2);border-radius:16px;padding:32px;
  width:480px;max-width:90vw;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.md h3{color:var(--text);font-size:18px;font-family:var(--mono);margin-bottom:24px}
.fd{margin-bottom:16px}
.fd label{display:block;margin-bottom:6px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:1px}
.fd input,.fd select{width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border2);
  border-radius:8px;color:var(--text);font-size:14px;font-family:var(--mono);outline:none}
.fd select option{background:var(--card);color:var(--text)}
.dur-b{margin-top:6px;height:4px;border-radius:2px;background:var(--border);overflow:hidden}
.dur-f{height:100%;border-radius:2px;background:linear-gradient(90deg,#059669,#d97706,#dc2626);transition:width .2s}
.md-acts{display:flex;gap:12px;justify-content:flex-end;margin-top:28px}
.btn-s{padding:10px 24px;background:transparent;color:var(--dim);border:1px solid var(--border2);
  border-radius:8px;cursor:pointer;font-size:14px;font-family:var(--mono)}
.empty{text-align:center;padding:48px;color:var(--muted);font-size:14px;width:100%}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes tipIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>
<div id="app"></div>
<script>
// Handler d'erreurs installé *avant* le script principal (capte aussi les erreurs de parsing).
function showFatal(message, lineno, colno, extra){
  try{
    const msg = message ? String(message) : "Erreur inconnue";
    const loc = (lineno||colno) ? (`\\n\\nLigne: ${lineno||'?'}, Col: ${colno||'?'}`) : "";
    const more = extra ? (`\\n\\n${String(extra)}`) : "";
    const pre = document.createElement("pre");
    pre.style.cssText="position:fixed;inset:12px;z-index:9999;background:rgba(17,24,39,.96);color:#f1f5f9;border:1px solid rgba(148,163,184,.25);border-radius:14px;padding:14px;overflow:auto;font:12px/1.45 ui-monospace,Consolas,monospace;white-space:pre-wrap";
    pre.textContent="MySifa / Planning — erreur JS\\n\\n"+msg+loc+more+"\\n\\nOuvrez la console (F12) pour le détail.";
    document.body.appendChild(pre);
  }catch(e){}
}
window.addEventListener("error", (e)=>showFatal(e.message, e.lineno, e.colno, (e.error && e.error.stack) ? e.error.stack : ""));
window.addEventListener("unhandledrejection", (e)=>showFatal("Promise rejection", 0, 0, e.reason||""));
</script>
<script>
let MID=__MACHINE_ID__;
const DN=["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"];
const MIND=2,MAXD=30;
const CC=["#2563eb","#7c3aed","#059669","#d97706","#dc2626","#0891b2","#4f46e5","#65a30d","#c026d3","#ea580c"];
const MACHINE_ORDER=["Cohésio 1","Cohésio 2","DSI","Repiquage"];
const DEFAULTS_BY_KEY={
  "C1":{pair:{week:{s:5,e:20},fri:{s:7,e:19}},impair:{week:{s:5,e:20},fri:{s:7,e:19}}}, // Cohésio 1
  "C2":{pair:{week:{s:5,e:13},fri:{s:5,e:13}},impair:{week:{s:13,e:20},fri:{s:5,e:13}}}, // Cohésio 2
  "DSI":{pair:{week:{s:8,e:14},fri:{s:8,e:14}},impair:{week:{s:8,e:14},fri:{s:8,e:14}}}, // DSI
  "REP":{pair:{week:{s:6,e:20},fri:{s:7,e:19}},impair:{week:{s:6,e:20},fri:{s:7,e:19}}}, // Repiquage
};
const DAY_API={1:"lundi",2:"mardi",3:"mercredi",4:"jeudi",5:"vendredi",6:"samedi"};
const DAY_FIELD={1:"horaires_lundi",2:"horaires_mardi",3:"horaires_mercredi",4:"horaires_jeudi",5:"horaires_vendredi",6:"horaires_samedi"};
let S={machine:null,machines:[],entries:[],timeline:[],wo:0,loading:true,holidays:{},dayWorked:{}};
let ME=null;
let CAN_EDIT=false;

const api=(p,o={})=>fetch(`/api/planning${p}`,{credentials:"include",headers:{"Content-Type":"application/json",...(o.headers||{})},...o}).then(r=>{if(!r.ok)throw r;return r.json()});

async function load(){
  if(!MID){
    console.warn("Planning: aucune machine sélectionnée (MID=0)");
    S.loading=false;
    render();
    return;
  }
  S.loading=true;render();
  try{
    const[m,en,tl]=await Promise.all([api(`/machines/${MID}`),api(`/machines/${MID}/entries`),api(`/machines/${MID}/timeline`)]);
    S.machine=m;S.entries=en;S.timeline=tl.slots||[];
    await Promise.all([loadHolidays(),loadDayWorked()]);
  }catch(e){console.error(e)}
  S.loading=false;render();
}

async function loadDayWorked(){
  const mon=addD(getMon(new Date()),S.wo*7);
  const start=ymd(mon), end=ymd(addD(mon,13));
  const rows=await api(`/machines/${MID}/day-work?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const map={};
  (rows||[]).forEach(r=>{map[String(r.date)]=!!(+r.is_worked);});
  S.dayWorked=map;
}

async function loadHolidays(){
  const mon=addD(getMon(new Date()),S.wo*7);
  const start=ymd(mon);
  const end=ymd(addD(mon,13));
  const rows=await api(`/machines/${MID}/holidays?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const map={};
  (rows||[]).forEach(r=>{map[String(r.date)]=!!(+r.is_off);});
  S.holidays=map;
}

async function setDayNonTravail(dateStr,isSaturday,nonTravailChecked){
  if(!CAN_EDIT) return;
  if(isSaturday){
    await api(`/machines/${MID}/day-work`,{method:"PUT",body:JSON.stringify({date:dateStr,is_worked:nonTravailChecked?0:1})});
  }else{
    await api(`/machines/${MID}/holidays`,{method:"PUT",body:JSON.stringify({date:dateStr,is_off:nonTravailChecked?1:0})});
  }
  await load();
}

function colorForId(id){
  const n=(id*2654435761)>>>0;
  return CC[n%CC.length];
}

const pad=n=>String(n).padStart(2,"0");
function ymdate(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate());}
const ymd=ymdate;
function escAttr(s){return String(s??"").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");}
const fd=d=>`${pad(d.getDate())}/${pad(d.getMonth()+1)}`;
const fdt=d=>`${DN[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth()+1)} ${d.getHours()}h`;
function getMon(d){const x=new Date(d),dy=x.getDay();x.setDate(x.getDate()-dy+(dy===0?-6:1));x.setHours(0,0,0,0);return x}
function wkNum(d){const x=new Date(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate()));const n=x.getUTCDay()||7;
  x.setUTCDate(x.getUTCDate()+4-n);const y=new Date(Date.UTC(x.getUTCFullYear(),0,1));return Math.ceil(((x-y)/864e5+1)/7)}
function addD(d,n){const r=new Date(d);r.setDate(r.getDate()+n);return r}
function fmtDl(s){if(!s)return"—";const p=String(s).slice(0,10).split("-");return p.length===3?p[2]+"/"+p[1]+"/"+p[0]:s;}

function parseHorairesPair(raw,di){
  const fb=[5,21];
  const d=String(raw??"").trim();
  if(!d)return{s:fb[0],e:fb[1]};
  const parts=d.split(",");
  if(parts.length<2)return{s:fb[0],e:fb[1]};
  function toH(x){
    x=String(x).trim();
    if(x.indexOf(":")>=0){const hp=x.split(":");return(+hp[0]||0)+((+hp[1]||0)/60);}
    return parseInt(x,10)||0;
  }
  let s=toH(parts[0]),e=toH(parts[1]);
  if(!(e>s))return{s:fb[0],e:fb[1]};
  return{s,e};
}
function floatFromTimeInput(hm){
  const s=String(hm||"").trim();
  if(!s||s.indexOf(":")<0)return null;
  const [h,m]=s.split(":");
  const hh=+h,mm=+m;
  if(!isFinite(hh)||!isFinite(mm))return null;
  return hh+(mm/60);
}
function timeInputFromFloat(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60);
  const hh=h+(m>=60?1:0),mm=((m%60)+60)%60;
  return pad(hh)+":"+pad(mm);
}
function machineKey(){
  const m=S.machine||{};
  return (m.code||m.nom||String(MID));
}
function getMachineDefaults(){
  const mk=machineKey();
  const key=`mysifa.planning.defaults.${mk}`;
  try{
    const raw=localStorage.getItem(key);
    if(raw){
      const j=JSON.parse(raw);
      if(j&&j.pair&&j.impair)return j;
    }
  }catch(e){}
  return DEFAULTS_BY_KEY[mk]||DEFAULTS_BY_KEY["C1"];
}
function saveMachineDefaults(defs){
  const mk=machineKey();
  const key=`mysifa.planning.defaults.${mk}`;
  localStorage.setItem(key,JSON.stringify(defs));
}
function isWeekPair(d){
  const w=wkNum(d);
  return (w%2)===0;
}
function getWhForDate(di,dateObj){
  // Priorité: horaires “hebdo” stockés en base pour cette machine (si non vides)
  const m=S.machine,key=DAY_FIELD[di];
  const raw=m&&m[key]!=null?String(m[key]):"";
  if(raw && raw.trim()){
    return parseHorairesPair(raw||null,di);
  }

  // Fallback: défauts par machine (semaine paire/impair + vendredi)
  const defs=getMachineDefaults();
  const par=isWeekPair(dateObj)?"pair":"impair";
  const isFri=(di===5);
  const w=isFri?(defs[par].fri):(defs[par].week);
  return {s:w.s,e:w.e};
}
function fmtHm(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60);
  let mm=m,hh=h;
  if(mm>=60){hh+=Math.floor(mm/60);mm=mm%60;}
  if(mm<=0)return hh+"h";
  return pad(hh)+":"+pad(mm);
}
function fmtWindow(s,e){return fmtHm(s)+"–"+fmtHm(e);}
function fracToTimeInput(f){
  const h=Math.floor(f+1e-6),m=Math.round((f-h)*60)%60;
  return pad(h)+":"+pad(m);
}
function isHHMM(s){return /^\d{2}:\d{2}$/.test(String(s||"").trim());}

function isAdmin(u){return u&&(u.role==="direction"||u.role==="administration");}
function roleLabel(role){const R={direction:"👑 Direction",administration:"🔧 Administration",fabrication:"⚙ Fabrication"};return R[role]||role||"";}
function renderSidebar(){
  if(!ME){
    return `<nav class="sidebar"><div class="logo"><div class="logo-brand">My<span>Prod</span></div><div class="logo-sub">by SIFA</div></div>
      <div style="padding:10px 12px;color:var(--muted);font-size:12px">Chargement…</div>
      <div class="sidebar-bottom">
        <button type="button" class="nav-btn" onclick="location.href='/'">← Retour <span class="wm">My<span>Sifa</span></span></button>
        <div class="version">__V_LABEL__</div>
      </div></nav>`;
  }
  const admin=isAdmin(ME);
  const items=[
    {key:"historique",label:"Historique & Erreurs",icon:"⚠",href:"/prod?page=historique"},
    {key:"production",label:"Production",icon:"📊",href:"/prod?page=production"},
    {key:"saisies",label:"Saisies",icon:"✏",href:"/prod?page=saisies"},
    ...(admin?[
      {key:"import",label:"Import XLSX",icon:"↑",href:"/prod?page=import"},
      {key:"_planning",label:"Planning",icon:"🗓",href:"/planning"},
      {key:"rentabilite",label:"Rentabilité",icon:"📈",href:"/prod?page=rentabilite"},
      {key:"dossiers",label:"Dossiers",icon:"◫",href:"/prod?page=dossiers"},
      {key:"users",label:"Utilisateurs",icon:"👥",href:"/prod?page=users"},
    ]:[]),
  ];
  const isLight=document.body.classList.contains("light");
  return`<nav class="sidebar"><div class="logo"><div class="logo-brand">My<span>Prod</span></div><div class="logo-sub">by SIFA</div></div>${
    items.map(i=>`<button type="button" class="nav-btn${i.key==="_planning"?" active":""}" onclick="location.href='${i.href}'">${i.icon}  ${i.label}</button>`).join("")
  }<div class="sidebar-bottom"><button type="button" class="nav-btn" onclick="location.href='/'">← Retour <span class="wm">My<span>Sifa</span></span></button><div class="user-chip" onclick="location.href='/'" title="Retour à l'accueil MySifa"><div class="uc-name">${escAttr(ME.nom||"")}</div><div class="uc-role">${roleLabel(ME.role)}</div><div style="font-size:10px;color:var(--accent);margin-top:3px">✎ Mon profil</div></div><button type="button" class="theme-btn" onclick="toggleTheme()"><span class="theme-ico">${isLight?"☀":"🌙"}</span><span class="theme-label">${isLight?"Mode clair":"Mode sombre"}</span></button><button type="button" class="logout-btn" onclick="doLogout()">⎋  Déconnexion</button><div class="version">__V_LABEL__</div></div></nav>`;
}
function toggleTheme(){document.body.classList.toggle("light");localStorage.setItem("theme",document.body.classList.contains("light")?"light":"dark");render();}
async function doLogout(){try{await fetch("/api/auth/logout",{method:"POST",credentials:"include"});}catch(e){}location.href="/";}

function render(){
  const a=document.getElementById("app");
  if(S.loading){
    a.innerHTML=`<div class="app">${renderSidebar()}<main class="main"><div class="planning-container" style="display:flex;align-items:center;justify-content:center;min-height:50vh;color:var(--muted)">Chargement…</div></main></div><div id="mroot"></div>`;
    return;
  }
  const m=S.machine||{nom:"?"};
  CAN_EDIT = isAdmin(ME);
  const run=S.entries.find(e=>e.statut==="en_cours");
  const runLbl=run?(run.client||run.numero_of||run.reference||""):"";
  const totH=S.entries.filter(e=>e.statut!=="termine").reduce((s,e)=>s+e.duree_heures,0);
  const nb=S.entries.filter(e=>e.statut!=="termine").length;
  const sl=S.timeline;
  const m1=addD(getMon(new Date()),S.wo*7),m2=addD(m1,7);
  const w1=wkNum(m1),w2=wkNum(m2);

  a.innerHTML=`<div class="app">${renderSidebar()}<main class="main"><div class="planning-container">
  <header class="header">
    <div class="h-left">
      <div>
        <select class="m-sel" onchange="changeMachine(this.value)" aria-label="Sélection de la machine">
          ${(S.machines||[]).map(x=>`<option value="${x.id}" ${x.id===MID?"selected":""}>${escAttr(x.nom||'')}</option>`).join("")}
        </select>
        <div class="m-sub">Planning de production — MyProd by SIFA</div>
      </div>
    </div>
    <div class="h-right">
      <a class="back-top" href="/" title="Retour au portail">← Retour <span class="wm">My<span>Sifa</span></span></a>
      ${CAN_EDIT?`<button type="button" class="gear-btn" onclick="openDefaultsModal()" title="Réglages horaires par défaut" aria-label="Réglages">⚙</button>`:""}
      ${run?`<div class="badge badge-run"><div class="dot"></div>${escAttr(runLbl)}</div>`:""}
      <div class="badge badge-info">${totH}h · ${nb} dossiers</div>
    </div>
  </header>
    <section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Vue Planning</div>
        <div class="wk-nav">
          <button type="button" onclick="S.wo--;load()">◀</button>
          <button type="button" class="today" onclick="S.wo=0;load()">${S.wo===0?"actuelle":"S"+w1}</button>
          <button type="button" onclick="S.wo++;load()">▶</button>
        </div>
      </div>
      <div style="margin-bottom:16px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div class="wk-lbl cur">S${w1} — ${fd(m1)} au ${fd(addD(m1,5))}</div>
          <span style="font-size:11px;color:var(--muted);max-width:420px">Chaque jour : « non travaillé » est enregistré. Samedi affiché par défaut comme non travaillé ; décochez pour indiquer un samedi travaillé.</span>
        </div>
        ${mkTL(m1,sl)}
      </div>
      <div>
        <div class="wk-lbl nxt">S${w2} — ${fd(m2)} au ${fd(addD(m2,4))}</div>${mkTL(m2,sl)}
      </div>
      <div class="legend">${sl.slice(0,8).map(s=>{const co=colorForId(s.entry_id||0);const lb=escAttr(s.client||s.numero_of||s.reference||"—");return`<div class="lg-i"><div class="lg-d" style="background:${co}"></div><span>${lb}</span></div>`;}).join("")}</div>
    </section>
    <section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Dossiers de production</div>
        ${CAN_EDIT?`<button type="button" class="btn-p" onclick="openAdd()"><span style="font-size:18px;line-height:1">+</span> Ajouter</button>`:""}
      </div>
      <div class="th"><span></span><span>#</span><span></span><span>Client</span><span>Format prod.</span><span>Ref OF</span><span>Ref prod.</span><span>Laize</span><span>Livraison</span><span>Durée</span><span>Statut</span><span class="act-c">Actions</span></div>
      <div id="tbody">${S.entries.length===0?'<div class="empty">Aucun dossier au planning</div>':""}
        ${S.entries.map((e,i)=>mkRow(e,i,sl)).join("")}
      </div>
    </section>
  </div></main></div><div id="mroot"></div>`;
  setupDD();
  setupStatutSelects();
}

function mkTL(mon,slots){
  const we=addD(mon,7),HF=.42,days=[];
  for(let i=0;i<7;i++){
    const d=addD(mon,i),di=d.getDay();
    if(di===0)continue;
    const ds=ymd(d);
    const isSat=di===6;
    const w=getWhForDate(di,d);
    if(!w)continue;
    const off=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    const dayT=off?0:(w.e-w.s);
    const hourLbl=off?"—":fmtWindow(w.s,w.e);
    const nonTravail=isSat?!S.dayWorked[ds]:!!S.holidays[ds];
    days.push({date:d,di,ds,s:w.s,e:w.e,tWork:dayT,flex:off?HF:dayT,off,hourLbl,nonTravail,isSat});
  }
  if(!days.length)return'<div style="color:var(--dim);padding:8px;font-size:13px">Aucun jour ouvré</div>';
  const tot=days.reduce((s,d)=>s+d.tWork,0);
  if(tot<=0)return'<div style="color:var(--muted);padding:8px;font-size:13px">Aucun créneau calculable (semaine entièrement non travaillée ou fermée).</div>';
  let c=0;
  const cols=days.filter(d=>d.tWork>0).map(d=>{const cs=c;c+=d.tWork;return{...d,cs,ce:c}});
  const now=new Date(),ts=now.toDateString();
  const wkStart=new Date(mon);wkStart.setHours(0,0,0,0);
  function gp(dt){
    let acc=0,t=dt.getTime();
    if(t<wkStart.getTime())return 0;
    for(const col of cols){
      const sod=new Date(col.date);sod.setHours(0,0,0,0);
      const dStart=new Date(sod.getTime()+col.s*36e5);
      const dEnd=new Date(sod.getTime()+col.e*36e5);
      if(t>=dEnd.getTime()){acc+=col.tWork;continue;}
      if(t<dStart.getTime())return acc;
      const h=(dt-sod)/36e5;
      const hh=Math.max(col.s,Math.min(col.e,h));
      return acc+(hh-col.s);
    }
    return Math.min(acc,tot);
  }
  const ws=slots.filter(s=>{const ss=new Date(s.start),se=new Date(s.end);return ss<we&&se>mon});

  let h=`<div class="tl-wrap" data-mon="${mon.getTime()}"><div class="dh">`;
  days.forEach(d=>{
    const td=d.date.toDateString()===ts,sa=d.di===6;
    const off=d.off;
    h+=`<div class="dh-cell ${td?"today":""} ${sa?"sat":""}" style="flex:${d.flex};opacity:${off?0.45:1}">
      <div style="display:flex;flex-direction:column;align-items:center;gap:2px">
        <div>${DN[d.di]} ${fd(d.date)}</div>
        ${d.off?`<small>${d.hourLbl}</small>`:(CAN_EDIT?`<button type="button" class="dh-hours-btn" onclick="openHorairesModal(${d.di})">${escAttr(d.hourLbl)}</button>`:`<small>${escAttr(d.hourLbl)}</small>`)}
        <label style="display:flex;align-items:center;gap:6px;font-size:10px;opacity:.85;cursor:pointer;white-space:nowrap">
          <input type="checkbox" ${d.nonTravail?"checked":""} ${CAN_EDIT?"":"disabled"} onchange="setDayNonTravail('${d.ds}',${d.isSat},this.checked)"> non travaillé
        </label>
      </div>
    </div>`;
  });
  h+=`</div><div class="tl-bar">`;
  cols.slice(1).forEach(col=>{h+=`<div class="d-sep" style="left:${(col.cs/tot)*100}%"></div>`;});

  ws.forEach((s,idx)=>{
    const ss=new Date(s.start),se=new Date(s.end);
    const cs=ss<mon?mon:ss,ce=se>we?we:se;
    const sp=gp(cs),ep=gp(ce),l=(sp/tot)*100,w=Math.max(.5,((ep-sp)/tot)*100);
    const co=colorForId(s.entry_id||idx+1);
    const fm=s.format_l&&s.format_h?`${s.format_l} × ${s.format_h} mm`:"—";
    const st=s.statut==="en_cours"?"En cours":"En attente";
    const cli=(s.client||"").trim()||(s.numero_of||s.reference||"—");
    const subTxt=fm!=="—"?fm:"";
    const meta=[s.numero_of||s.reference,s.description].filter(Boolean).join(" · ");
    h+=`<div class="slot" style="left:${l}%;width:${w}%;background:${co}cc;border:1px solid ${co};box-shadow:0 2px 12px ${co}33"
      onmouseenter="showTip(event,this)" onmousemove="moveTip(event)" onmouseleave="hideTip()"
      data-ref="${escAttr(cli)}" data-lbl="${escAttr(meta)}" data-fmt="${escAttr(fm)}" data-dur="${escAttr(String(s.duree_heures)+"h")}"
      data-deb="${escAttr(fdt(ss))}" data-fin="${escAttr(fdt(se))}" data-st="${escAttr(st)}" data-co="${escAttr(co)}">
      ${w>5?`<div class="slot-inner"><span class="line1">${escAttr(cli)}</span>${subTxt?`<span class="line2">${escAttr(subTxt)}</span>`:""}</div>`:""}</div>`;
  });

  const np=gp(now);
  if(np>0&&np<tot)h+=`<div class="now-l" style="left:${(np/tot)*100}%"><div class="now-d"></div></div>`;
  h+=`</div></div>`;return h;
}

function mkRow(e,i,slots){
  const fm=e.format_l&&e.format_h?`${e.format_l}×${e.format_h}`:"—";
  const sc=e.statut==="en_cours"?"run":e.statut==="termine"?"ter":"att";
  const sl={run:"En cours",ter:"Terminé",att:"En attente"}[sc];
  const isLocked=(e.statut==="en_cours"||e.statut==="termine");
  const next = S.entries && S.entries[i+1] ? S.entries[i+1] : null;
  const nextLocked = !!(next && (next.statut==="en_cours" || next.statut==="termine"));
  const co=colorForId(e.id||i+1);
  const cli=(e.client||"").trim()||"—";
  const of=escAttr(e.numero_of||e.reference||"—");
  const rfp=escAttr(e.ref_produit||"")||"—";
  const lz=e.laize!=null&&e.laize!==""?escAttr(String(e.laize)):"—";
  const statutCell=(isLocked||!CAN_EDIT)
    ? `<span class="st ${sc}">${sc==="run"?'<span style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;display:inline-block"></span>':""}${sl} 🔒</span>`
    : `<select class="statut-select" data-eid="${e.id}">
         <option value="attente" ${e.statut==="attente"?"selected":""}>⏳ Attente</option>
         <option value="en_cours" ${e.statut==="en_cours"?"selected":""}>▶ En cours</option>
         <option value="termine" ${e.statut==="termine"?"selected":""}>✅ Terminé</option>
       </select>`;
  return`<div class="tr" draggable="true" data-eid="${e.id}" data-idx="${i}"
    data-statut="${escAttr(e.statut||'attente')}"
    style="animation:slideIn .3s ease ${i*.03}s both;${i===0?`border-left:3px solid ${co}`:"border-left:3px solid transparent"};${isLocked?"cursor:not-allowed;opacity:.9":""}">
    <span class="dh-handle">⠿</span>
    <span class="cell-mini">${i+1}</span>
    <div><div class="cd" style="background:${co}"></div></div>
    <span class="lbl-main">${escAttr(cli)}</span>
    <span class="cell-mini">${escAttr(fm)}${fm!=="—"?" mm":""}</span>
    <span class="cell-mini">${of}</span>
    <span class="cell-mini">${rfp}</span>
    <span class="cell-mini">${lz}</span>
    <span class="cell-mini">${escAttr(fmtDl(e.date_livraison||""))}</span>
    <span class="cell-mini">${e.duree_heures}h</span>
    ${statutCell}
    <div class="acts">
      ${CAN_EDIT?`
      <button type="button" class="ab mov" onclick="moveEntry(${e.id},-1)" title="Monter" ${i<=0||isLocked?"disabled":""}>▲</button>
      <button type="button" class="ab mov" onclick="moveEntry(${e.id},+1)" title="Descendre" ${i>=S.entries.length-1||isLocked?"disabled":""}>▼</button>
      <button type="button" class="ab" onclick="openInsert(${e.id})" title="${nextLocked?"⦸ Impossible : dossier En cours / Terminé juste après":"Insérer après"}" ${isLocked||nextLocked?"disabled":""}>${nextLocked?"⦸":"↳+"}</button>
      <button type="button" class="ab" onclick="openEdit(${e.id})" title="Modifier">✎</button>
      <button type="button" class="ab del" onclick="if(confirm('Supprimer ?'))delEntry(${e.id})" title="Supprimer">✕</button>`:""}
    </div></div>`;
}

async function moveEntry(entryId,delta){
  if(!CAN_EDIT) return;
  const idx = S.entries.findIndex(e=>e.id===entryId);
  if(idx<0) return;
  const cur = S.entries[idx];
  if(!cur || cur.statut==="en_cours" || cur.statut==="termine") return;
  const ni = idx + delta;
  if(ni<0 || ni>=S.entries.length) return;
  const target = S.entries[ni];
  if(target && (target.statut==="en_cours" || target.statut==="termine")) return;

  const ids=S.entries.map(e=>e.id);
  const [m]=ids.splice(idx,1);
  ids.splice(ni,0,m);
  try{
    await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
    await load();
  }catch(e){
    alert("Réordonnancement impossible");
    await load();
  }
}

// ── Tooltip ──
let tipEl=null;
function showTip(ev,el){hideTip();const d=el.dataset;tipEl=document.createElement("div");tipEl.className="tip";
  tipEl.style.borderColor=(d.co||"#888")+"55";
  const sub=d.lbl?`<div class="tip-lbl">${d.lbl}</div>`:"";
  tipEl.innerHTML=`<div class="tip-hdr"><div class="tip-bar" style="background:${d.co||"#888"}"></div><div><div class="tip-ref">${d.ref||"—"}</div>${sub}</div></div>
    <div class="tip-grid"><span class="k">Format</span><span class="v">${d.fmt||"—"}</span><span class="k">Durée</span><span class="v">${d.dur||""}</span>
    <span class="k">Début</span><span class="v">${d.deb||""}</span><span class="k">Fin</span><span class="v">${d.fin||""}</span>
    <span class="k">Statut</span><span class="v" style="color:${d.st==="En cours"?"var(--green)":"var(--amber)"};font-weight:600">${d.st||""}</span></div>`;
  el.closest(".tl-wrap").appendChild(tipEl);moveTip(ev)}
function moveTip(ev){if(!tipEl)return;const c=tipEl.parentElement.getBoundingClientRect();
  let x=ev.clientX-c.left+12,y=ev.clientY-c.top-tipEl.offsetHeight-12;
  if(x+tipEl.offsetWidth>c.width)x=c.width-tipEl.offsetWidth-8;if(x<0)x=8;if(y<0)y=ev.clientY-c.top+20;
  tipEl.style.left=x+"px";tipEl.style.top=y+"px"}
function hideTip(){if(tipEl){tipEl.remove();tipEl=null}}

// ── Drag & Drop ──
function setupDD(){
  if(!CAN_EDIT) return;
  const rows=document.querySelectorAll(".tr[draggable]");let di=null;
  let overEl=null, overPos=null;
  function clearOver(){
    if(overEl){overEl.classList.remove("drop-before","drop-after");}
    overEl=null;overPos=null;
  }
  rows.forEach(r=>{
    const st=(r.dataset.statut||"").toLowerCase();
    const locked=(st==="en_cours"||st==="termine");
    if(locked){
      r.removeAttribute("draggable");
      return;
    }
    r.addEventListener("dragstart",e=>{di=+r.dataset.idx;r.classList.add("dra");e.dataTransfer.effectAllowed="move"});
    r.addEventListener("dragover",e=>{
      e.preventDefault();
      r.classList.add("dov");
      const rect=r.getBoundingClientRect();
      const before = (e.clientY - rect.top) < rect.height/2;
      if(overEl!==r || overPos!==(before?"before":"after")){
        clearOver();
        overEl=r;overPos=before?"before":"after";
        r.classList.add(before?"drop-before":"drop-after");
      }
    });
    r.addEventListener("dragleave",()=>{
      r.classList.remove("dov");
      // Ne pas clearOver ici : le navigateur peut déclencher dragleave juste avant drop,
      // et on perdrait l'information "avant/après" (trait bleu).
    });
    r.addEventListener("drop", async (e)=>{
      e.preventDefault();
      r.classList.remove("dov");
      const ti = +r.dataset.idx;
      if(di===null){ clearOver(); return; }
      if(di===ti){ clearOver(); return; }
      const ids = S.entries.map(e=>e.id);
      const [m] = ids.splice(di, 1);
      let insertAt = ti;
      // si on dépose "après", et qu'on vient d'enlever un item avant ti, ajuster
      const rect=r.getBoundingClientRect();
      const before = (e.clientY - rect.top) < rect.height/2;
      const after = !before;
      if(after) insertAt = ti + 1;
      if(di < insertAt) insertAt -= 1;
      ids.splice(insertAt, 0, m);
      clearOver();
      try{
        await api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})});
      }finally{
        await load();
      }
    });
    r.addEventListener("dragend",()=>{
      r.classList.remove("dra");
      di=null;
      clearOver();
      rows.forEach(x=>x.classList.remove("dov"));
    })
  })
}

function setupStatutSelects(){
  if(!CAN_EDIT) return;
  document.querySelectorAll(".statut-select").forEach(sel=>{
    sel.addEventListener("change", async()=>{
      const eid=sel.dataset.eid;
      try{
        await api(`/machines/${MID}/entries/${eid}/statut`,{
          method:"PUT",
          body: JSON.stringify({statut: sel.value, force: true})
        });
        await load();
      }catch(e){
        alert("Erreur statut");
        await load();
      }
    });
  });
}

// ── API actions ──
async function delEntry(id){await api(`/machines/${MID}/entries/${id}`,{method:"DELETE"});load()}

// ── Modals ──
function durBar(v){return((v-MIND)/(MAXD-MIND)*100)+"%"}

function modalHTML(title,fields,submitLabel,onSubmitFn){
  return`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md"><h3>${title}</h3>
    ${fields}
    <div class="md-acts"><button class="btn-s" onclick="closeM()">Annuler</button>
    <button class="btn-p" onclick="${onSubmitFn}">${submitLabel}</button></div></div></div>`
}

function dossierFields(numero_of,client,ref_produit,laize,date_livraison,commentaire,fl,fh,dur,statut,showStatut){
  return`
    <div class="fd"><label>Numéro d'OF</label><input id="f-of" value="${numero_of}" placeholder="961/0001"></div>
    <div class="fd"><label>Client</label><input id="f-cli" value="${client}" placeholder="Nom du client"></div>
    <div class="fd"><label>Réf produit</label><input id="f-rp" value="${ref_produit}" placeholder="REF-PROD"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="fd"><label>Largeur (mm)</label><input type="number" id="f-fl" value="${fl}" placeholder="100"></div>
      <div class="fd"><label>Hauteur (mm)</label><input type="number" id="f-fh" value="${fh}" placeholder="70"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="fd"><label>Laize (mm)</label><input type="number" id="f-laize" value="${laize}" placeholder="510"></div>
      <div class="fd"><label>Date livraison</label><input type="date" id="f-dl" value="${date_livraison}"></div>
    </div>
    <div class="fd"><label>Commentaire</label><input id="f-com" value="${commentaire}" placeholder="Bobine, contraintes, etc."></div>
    <div class="fd"><label>Durée (${MIND}–${MAXD}h)</label>
      <input type="number" id="f-dur" min="${MIND}" max="${MAXD}" value="${dur}" oninput="document.getElementById('f-dur-fill').style.width=((Math.max(${MIND},Math.min(${MAXD},+this.value||${MIND}))-${MIND})/(${MAXD}-${MIND})*100)+'%'">
      <div class="dur-b"><div class="dur-f" id="f-dur-fill" style="width:${durBar(dur)}"></div></div>
    </div>
    ${showStatut?`<div class="fd"><label>Statut</label><select id="f-stat">
      <option value="attente" ${statut==="attente"?"selected":""}>En attente</option>
      <option value="en_cours" ${statut==="en_cours"?"selected":""}>En cours</option>
      <option value="termine" ${statut==="termine"?"selected":""}>Terminé</option>
    </select></div>`:""}`
}

function getFormData(withStatut){
  const d={
    numero_of:(document.getElementById("f-of").value||"").trim(),
    client:document.getElementById("f-cli").value||"",
    ref_produit:document.getElementById("f-rp").value||"",
    format_l:parseFloat(document.getElementById("f-fl").value)||null,
    format_h:parseFloat(document.getElementById("f-fh").value)||null,
    laize:parseFloat(document.getElementById("f-laize").value)||null,
    date_livraison:document.getElementById("f-dl").value||"",
    commentaire:document.getElementById("f-com").value||"",
    duree_heures:Math.max(MIND,Math.min(MAXD,parseInt(document.getElementById("f-dur").value)||8)),
  };
  if(withStatut)d.statut=document.getElementById("f-stat").value;
  return d;
}

function openAdd(){
  if(!CAN_EDIT) return;
  document.getElementById("mroot").innerHTML=modalHTML(
    "Ajouter un dossier",
    dossierFields("","","","","","","","",8,"attente",false),
    "Ajouter","submitAdd()"
  );
}
async function submitAdd(){
  const d=getFormData(false);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/entries`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

function openEdit(id){
  if(!CAN_EDIT) return;
  const e=S.entries.find(x=>x.id===id);if(!e)return;
  document.getElementById("mroot").innerHTML=modalHTML(
    `Modifier — ${(e.numero_of||e.reference)||''}`,
    dossierFields(e.numero_of||e.reference||"",e.client||"",e.ref_produit||"",e.laize||"",e.date_livraison||"",e.commentaire||"",e.format_l||"",e.format_h||"",e.duree_heures,e.statut,true),
    "Enregistrer",`submitEdit(${id})`
  );
}
async function submitEdit(id){
  const d=getFormData(true);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/entries/${id}`,{method:"PUT",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

function openInsert(afterId){
  if(!CAN_EDIT) return;
  try{
    const idx = S.entries.findIndex(e=>e.id===afterId);
    if(idx>=0){
      const nxt = S.entries[idx+1];
      if(nxt && (nxt.statut==="en_cours" || nxt.statut==="termine")){
        alert("⦸ Impossible d'insérer une ligne avant un dossier En cours / Terminé.");
        return;
      }
    }
  }catch(e){}
  document.getElementById("mroot").innerHTML=modalHTML(
    "Insérer un dossier après",
    dossierFields("","","","","","","","",8,"attente",false),
    "Insérer",`submitInsert(${afterId})`
  );
}
async function submitInsert(afterId){
  const d=getFormData(false);
  if(!d.numero_of)return alert("Numéro d'OF requis");
  await api(`/machines/${MID}/insert-after/${afterId}`,{method:"POST",body:JSON.stringify({reference:d.numero_of,...d})});
  closeM();load();
}

function closeM(){document.getElementById("mroot").innerHTML=""}

function changeMachine(v){
  const id=parseInt(v,10);
  if(!id||!isFinite(id))return;
  localStorage.setItem("mysifa.planning.lastMachine",String(id));
  location.href=`/planning?machine=${encodeURIComponent(String(id))}`;
}

function openHorairesModal(di){
  if(!CAN_EDIT) return;
  if(!S.machine)return;
  const {s,e}=getWhForDate(di,new Date());
  const dn={1:"Lundi",2:"Mardi",3:"Mercredi",4:"Jeudi",5:"Vendredi",6:"Samedi"}[di]||"Jour";
  document.getElementById("mroot").innerHTML=modalHTML(
    `Plage horaire — ${dn}`,
    `<p style="font-size:12px;color:var(--muted);margin:-8px 0 16px">Modèle hebdo pour cette machine (tous les ${dn.toLowerCase()}s).</p>
    <div class="fd"><label>Début (HH:MM)</label><input type="text" inputmode="numeric" placeholder="07:00" id="f-h-start" value="${fracToTimeInput(s)}"></div>
    <div class="fd"><label>Fin de journée (HH:MM)</label><input type="text" inputmode="numeric" placeholder="19:00" id="f-h-end" value="${fracToTimeInput(e)}"></div>`,
    "Enregistrer",
    `submitHoraires(${di})`
  );
}
async function submitHoraires(di){
  if(!CAN_EDIT) return;
  const st=(document.getElementById("f-h-start").value||"").trim();
  const en=(document.getElementById("f-h-end").value||"").trim();
  if(!st||!en)return void alert("Indiquez début et fin.");
  if(!isHHMM(st)||!isHHMM(en))return void alert("Format attendu : HH:MM (24h). Exemple : 07:00");
  try{
    await api(`/machines/${MID}/horaires`,{method:"PUT",body:JSON.stringify({day:DAY_API[di],start:st,end:en})});
    closeM();load();
  }catch(err){
    let msg="Modification impossible.";
    try{const j=await err.json();if(j&&j.detail)msg=typeof j.detail==="string"?j.detail:JSON.stringify(j.detail);}catch(x){}
    alert(msg);
  }
}

function openDefaultsModal(){
  const defs=getMachineDefaults();
  function row(lbl,id,val){
    return `<div class="fd"><label>${lbl} (HH:MM)</label><input type="text" inputmode="numeric" placeholder="07:00" id="${id}" value="${timeInputFromFloat(val)}"></div>`;
  }
  const f=`
    <p style="font-size:12px;color:var(--muted);margin:-8px 0 16px">
      Valeurs par défaut utilisées quand les horaires hebdo (base) sont vides. Elles impactent les fuseaux affichés sur le planning.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div style="border:1px solid var(--border2);border-radius:14px;padding:14px">
        <div style="font-family:var(--mono);font-size:12px;color:var(--text);margin-bottom:10px">Semaine paire</div>
        ${row("Semaine paire — début","dp-w-s",defs.pair.week.s)}
        ${row("Semaine paire — fin","dp-w-e",defs.pair.week.e)}
        ${row("Vendredi (paire) — début","dp-f-s",defs.pair.fri.s)}
        ${row("Vendredi (paire) — fin","dp-f-e",defs.pair.fri.e)}
      </div>
      <div style="border:1px solid var(--border2);border-radius:14px;padding:14px">
        <div style="font-family:var(--mono);font-size:12px;color:var(--text);margin-bottom:10px">Semaine impaire</div>
        ${row("Semaine impaire — début","di-w-s",defs.impair.week.s)}
        ${row("Semaine impaire — fin","di-w-e",defs.impair.week.e)}
        ${row("Vendredi (impaire) — début","di-f-s",defs.impair.fri.s)}
        ${row("Vendredi (impaire) — fin","di-f-e",defs.impair.fri.e)}
      </div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:14px">
      <button class="btn-s" onclick="resetDefaults()">Réinitialiser</button>
    </div>
  `;
  const lbl=(S.machine&&S.machine.nom)?S.machine.nom:("Machine "+MID);
  document.getElementById("mroot").innerHTML=modalHTML(
    `Réglages — ${escAttr(lbl)}`,
    f,
    "Enregistrer",
    "submitDefaults()"
  );
}
function resetDefaults(){
  const mk=machineKey();
  const d=DEFAULTS_BY_KEY[mk]||DEFAULTS_BY_KEY["C1"];
  saveMachineDefaults(d);
  closeM();render();
}
function submitDefaults(){
  function v(id){
    const raw=(document.getElementById(id).value||"").trim();
    if(!isHHMM(raw)) return null;
    const f=floatFromTimeInput(raw);
    return (f==null)?0:f;
  }
  const nd={
    pair:{week:{s:v("dp-w-s"),e:v("dp-w-e")},fri:{s:v("dp-f-s"),e:v("dp-f-e")}},
    impair:{week:{s:v("di-w-s"),e:v("di-w-e")},fri:{s:v("di-f-s"),e:v("di-f-e")}},
  };
  function okRange(r){return isFinite(r.s)&&isFinite(r.e)&&r.e>r.s&&r.s>=0&&r.e<=24;}
  if([nd.pair.week,nd.pair.fri,nd.impair.week,nd.impair.fri].some(r=>r.s==null||r.e==null)){
    return alert("Format attendu : HH:MM (24h). Exemple : 07:00");
  }
  if(!okRange(nd.pair.week)||!okRange(nd.pair.fri)||!okRange(nd.impair.week)||!okRange(nd.impair.fri)){
    return alert("Plages invalides (fin > début, entre 0 et 24).");
  }
  saveMachineDefaults(nd);
  closeM();render();
}

async function boot(){
  if(localStorage.getItem("theme")==="light")document.body.classList.add("light");
  try{ render(); }catch(e){}
  let r;
  try{r=await fetch("/api/auth/me",{credentials:"include"});}catch(e){location.href="/";return;}
  if(!r.ok){location.href="/";return;}
  ME=await r.json();
  try{
    const list=await api(`/machines`);
    const byName=new Map((list||[]).map(m=>[String(m.nom||""),m]));
    const ordered=[];
    MACHINE_ORDER.forEach(n=>{if(byName.has(n))ordered.push(byName.get(n));});
    (list||[]).forEach(m=>{if(!ordered.find(x=>x.id===m.id))ordered.push(m);});
    S.machines=ordered;

    const sp=new URLSearchParams(location.search||"");
    const raw=sp.get("machine");
    const num=raw?parseInt(raw,10):NaN;
    const ids=new Set(ordered.map(m=>m.id));
    const saved=parseInt(localStorage.getItem("mysifa.planning.lastMachine")||"",10);
    if(isFinite(num)&&ids.has(num)){
      MID=num;
    }else if(isFinite(num)&&num>=1&&num<=4){
      const wantedName=MACHINE_ORDER[num-1];
      const wanted=ordered.find(m=>String(m.nom||"")===wantedName);
      if(wanted) MID=wanted.id;
    }else if(isFinite(saved)&&ids.has(saved)){
      MID=saved;
    }else{
      const wanted=ordered[0];
      if(wanted) MID=wanted.id;
    }
  }catch(e){console.error(e)}
  await load();
}
boot();
</script>
</body>
</html>
"""
