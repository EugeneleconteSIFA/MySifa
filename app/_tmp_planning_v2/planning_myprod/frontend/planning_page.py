"""SIFA — Page Planning v1.1 (standalone)

Ajouter dans main.py :
    from frontend.planning_page import router as planning_page_router
    app.include_router(planning_page_router)

Accès : /planning  ou  /planning?machine=1
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/planning", response_class=HTMLResponse)
def planning_page(machine: int = 1):
    return HTMLResponse(content=PLANNING_HTML.replace("__MACHINE_ID__", str(machine)))


PLANNING_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Planning — MyProd by SIFA</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a1a;--bg-card:#11112a;--bg-dark:#0d0d1a;--border:#1e1e3a;--border2:#2a2a4a;
  --text:#e0e0e0;--dim:#8888aa;--blue:#60a5fa;--accent:#2563eb;
  --green:#22c55e;--red:#ef4444;--amber:#f59e0b;--purple:#7c3aed;
  --mono:'JetBrains Mono',monospace;--sans:'Space Grotesk','Segoe UI',system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}

.header{padding:20px 32px;border-bottom:1px solid var(--border);display:flex;align-items:center;
  justify-content:space-between;flex-wrap:wrap;gap:12px;background:linear-gradient(180deg,#0f0f25,var(--bg))}
.h-left{display:flex;align-items:center;gap:16px}
.m-icon{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,var(--accent),var(--purple));
  display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#fff;
  box-shadow:0 4px 20px rgba(37,99,235,.3)}
.m-title{font-size:22px;font-weight:700;font-family:var(--sans);
  background:linear-gradient(135deg,var(--blue),#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.m-sub{font-size:12px;color:#6b7280}
.h-right{display:flex;align-items:center;gap:12px;flex-wrap:wrap}

.sat-tog{display:flex;align-items:center;gap:10px;padding:8px 16px;border-radius:10px;cursor:pointer;
  border:1px solid var(--border2);background:var(--bg-card);transition:all .3s;user-select:none}
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
.badge-run .dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
.badge-info{background:var(--bg-card);border:1px solid var(--border2);color:var(--dim)}

.content{padding:24px 32px;max-width:1400px;margin:0 auto}
.sec{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:28px}
.sec-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.sec-title{font-size:16px;font-weight:600;color:#c0c0d0}

.wk-nav{display:flex;gap:0;align-items:center}
.wk-nav button{padding:6px 12px;background:var(--bg-card);border:1px solid var(--border2);
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
  color:#6b7280;border-bottom:1px solid var(--border)}
.dh-cell.today{color:var(--blue);border-bottom:2px solid var(--accent)}
.dh-cell.sat{color:#c084fc;border-bottom:2px solid rgba(124,58,237,.3)}
.dh-cell small{display:block;font-size:10px;opacity:.6;margin-top:2px}
.tl-bar{position:relative;height:56px;background:var(--bg-dark);border-radius:8px;
  border:1px solid var(--border);overflow:visible}
.d-sep{position:absolute;top:0;bottom:0;width:1px;background:var(--border2)}
.slot{position:absolute;top:6px;bottom:6px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;cursor:pointer;transition:all .15s;overflow:hidden}
.slot:hover{top:4px;bottom:4px;z-index:20}
.slot span{font-size:11px;color:#fff;font-weight:700;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;padding:0 6px;font-family:var(--mono)}
.now-l{position:absolute;top:0;bottom:0;width:2px;background:var(--red);z-index:15;box-shadow:0 0 8px var(--red)}
.now-d{position:absolute;top:-4px;left:-4px;width:10px;height:10px;border-radius:50%;background:var(--red)}

.tip{position:absolute;z-index:100;background:#1a1a2e;border-radius:12px;padding:14px 18px;
  min-width:240px;max-width:320px;pointer-events:none;animation:tipIn .15s ease;
  box-shadow:0 12px 40px rgba(0,0,0,.6)}
.tip-hdr{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.tip-bar{width:6px;height:32px;border-radius:3px;flex-shrink:0}
.tip-ref{font-size:13px;font-weight:700;color:var(--text);font-family:var(--mono)}
.tip-lbl{font-size:12px;color:#a0a0b0;margin-top:2px}
.tip-grid{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;font-size:11px;
  border-top:1px solid var(--border2);padding-top:10px}
.tip-grid .k{color:#6b7280}.tip-grid .v{color:#c0c0d0;font-family:var(--mono)}

.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)}
.lg-i{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim)}
.lg-d{width:10px;height:10px;border-radius:3px}.lg-i span{font-family:var(--mono)}

.th{display:grid;grid-template-columns:36px 40px 130px 1fr 100px 80px 100px 140px;
  padding:10px 12px;background:var(--bg-dark);border-radius:10px 10px 0 0;
  font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;font-weight:600;font-family:var(--mono)}
.th .act-c{text-align:right}
.tr{display:grid;grid-template-columns:36px 40px 130px 1fr 100px 80px 100px 140px;
  padding:12px;border-bottom:1px solid #1a1a30;font-size:13px;align-items:center;
  cursor:grab;transition:background .2s;background:#0f0f20}
.tr:first-child{background:#0f1a2a}
.tr.dov{background:#1a1a40}.tr.dra{opacity:.5}
.dh-handle{color:#3a3a5a;font-size:14px;cursor:grab;user-select:none}
.cd{width:8px;height:8px;border-radius:50%}
.ref{font-family:var(--mono);font-weight:600;color:#c0c0d0}
.ref.run{color:var(--blue)}
.lbl{color:#a0a0b0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fmt{font-family:var(--mono);color:var(--dim);font-size:12px}
.dur{font-family:var(--mono);color:var(--dim)}
.st{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.st.run{background:#0f2a1a;color:var(--green);border:1px solid #166534}
.st.att{background:#1a1520;color:var(--amber);border:1px solid #78350f}
.st.ter{background:var(--bg-card);color:#6b7280;border:1px solid var(--border2)}
.acts{display:flex;gap:6px;justify-content:flex-end}
.ab{padding:4px 8px;background:transparent;border:1px solid var(--border2);color:#6b7280;
  cursor:pointer;font-size:12px;border-radius:6px;font-family:var(--mono)}
.ab:hover{background:var(--border);color:var(--text)}
.ab.del{color:var(--red)}.ab.del:hover{background:#2a1020}

.btn-p{padding:8px 20px;background:var(--accent);color:#fff;border:none;border-radius:8px;
  cursor:pointer;font-size:13px;font-weight:600;font-family:var(--mono);display:flex;align-items:center;gap:8px}
.btn-p:hover{background:#1d4ed8}

.mo{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;
  justify-content:center;z-index:1000;backdrop-filter:blur(4px)}
.md{background:#1a1a2e;border:1px solid var(--border2);border-radius:16px;padding:32px;
  width:480px;max-width:90vw;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.md h3{color:var(--text);font-size:18px;font-family:var(--mono);margin-bottom:24px}
.fd{margin-bottom:16px}
.fd label{display:block;margin-bottom:6px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:1px}
.fd input,.fd select{width:100%;padding:10px 14px;background:#0f0f23;border:1px solid var(--border2);
  border-radius:8px;color:var(--text);font-size:14px;font-family:var(--mono);outline:none}
.fd select option{background:#0f0f23;color:var(--text)}
.dur-b{margin-top:6px;height:4px;border-radius:2px;background:#1a1a30;overflow:hidden}
.dur-f{height:100%;border-radius:2px;background:linear-gradient(90deg,#059669,#d97706,#dc2626);transition:width .2s}
.md-acts{display:flex;gap:12px;justify-content:flex-end;margin-top:28px}
.btn-s{padding:10px 24px;background:transparent;color:var(--dim);border:1px solid var(--border2);
  border-radius:8px;cursor:pointer;font-size:14px;font-family:var(--mono)}
.empty{text-align:center;padding:48px;color:#4a4a6a;font-size:14px}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes tipIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>
<div id="app"></div>
<script>
const MID=__MACHINE_ID__;
const DN=["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"];
const MIND=2,MAXD=30;
const CC=["#2563eb","#7c3aed","#059669","#d97706","#dc2626","#0891b2","#4f46e5","#65a30d","#c026d3","#ea580c"];
const WH={1:[5,21],2:[5,21],3:[5,21],4:[5,21],5:[6,20],6:[6,18]};
let S={machine:null,entries:[],timeline:[],wo:0,sat:false,loading:true};

const api=(p,o={})=>fetch(`/api/planning${p}`,{headers:{"Content-Type":"application/json",...(o.headers||{})},...o}).then(r=>{if(!r.ok)throw r;return r.json()});

async function load(){
  S.loading=true;render();
  try{
    const[m,en,tl]=await Promise.all([api(`/machines/${MID}`),api(`/machines/${MID}/entries`),api(`/machines/${MID}/timeline`)]);
    S.machine=m;S.entries=en;S.timeline=tl.slots||[];
    const cfg=await api(`/machines/${MID}/config`);
    S.sat=!!cfg.samedi_travaille;
  }catch(e){console.error(e)}
  S.loading=false;render();
}

async function togSat(){
  S.sat=!S.sat;const t=new Date(),w=wkNum(t);
  await api(`/machines/${MID}/config`,{method:"PUT",body:JSON.stringify({semaine:`${t.getFullYear()}-W${String(w).padStart(2,'0')}`,samedi_travaille:S.sat?1:0})});
  await load();
}

const pad=n=>String(n).padStart(2,"0");
const fd=d=>`${pad(d.getDate())}/${pad(d.getMonth()+1)}`;
const fdt=d=>`${DN[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth()+1)} ${d.getHours()}h`;
function getMon(d){const x=new Date(d),dy=x.getDay();x.setDate(x.getDate()-dy+(dy===0?-6:1));x.setHours(0,0,0,0);return x}
function wkNum(d){const x=new Date(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate()));const n=x.getUTCDay()||7;
  x.setUTCDate(x.getUTCDate()+4-n);const y=new Date(Date.UTC(x.getUTCFullYear(),0,1));return Math.ceil(((x-y)/864e5+1)/7)}
function addD(d,n){const r=new Date(d);r.setDate(r.getDate()+n);return r}
function whFor(di){if(di===6&&!S.sat)return null;if(di===0)return null;return WH[di]||null}

function render(){
  const a=document.getElementById("app");
  if(S.loading){a.innerHTML=`<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--dim)">Chargement...</div>`;return}
  const m=S.machine||{nom:"?",code:"?"};
  const run=S.entries.find(e=>e.statut==="en_cours");
  const totH=S.entries.filter(e=>e.statut!=="termine").reduce((s,e)=>s+e.duree_heures,0);
  const nb=S.entries.filter(e=>e.statut!=="termine").length;
  const sl=S.timeline;
  const m1=addD(getMon(new Date()),S.wo*7),m2=addD(m1,7);
  const w1=wkNum(m1),w2=wkNum(m2);

  a.innerHTML=`
  <header class="header">
    <div class="h-left">
      <div class="m-icon">${m.code}</div>
      <div><div class="m-title">${m.nom}</div><div class="m-sub">Planning de production — MyProd by SIFA</div></div>
    </div>
    <div class="h-right">
      <div class="sat-tog ${S.sat?'on':''}" onclick="togSat()">
        <div class="track"><div class="thumb"></div></div><span class="sat-lbl">Samedi travaillé</span>
      </div>
      ${run?`<div class="badge badge-run"><div class="dot"></div>${run.reference}</div>`:""}
      <div class="badge badge-info">${totH}h · ${nb} dossiers</div>
    </div>
  </header>
  <div class="content">
    <section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Vue Planning</div>
        <div class="wk-nav">
          <button onclick="S.wo--;render()">◀</button>
          <button class="today" onclick="S.wo=0;render()">Aujourd'hui</button>
          <button onclick="S.wo++;render()">▶</button>
        </div>
      </div>
      <div style="margin-bottom:16px">
        <div class="wk-lbl cur">S${w1} — ${fd(m1)} au ${fd(addD(m1,4))}</div>${mkTL(m1,sl)}
      </div>
      <div>
        <div class="wk-lbl nxt">S${w2} — ${fd(m2)} au ${fd(addD(m2,4))}</div>${mkTL(m2,sl)}
      </div>
      <div class="legend">${sl.slice(0,8).map((s,i)=>`<div class="lg-i"><div class="lg-d" style="background:${CC[i%CC.length]}"></div><span>${s.reference}</span></div>`).join("")}</div>
    </section>
    <section class="sec">
      <div class="sec-hdr">
        <div class="sec-title">Dossiers de production</div>
        <button class="btn-p" onclick="openAdd()"><span style="font-size:18px;line-height:1">+</span> Ajouter</button>
      </div>
      <div class="th"><span></span><span>#</span><span>Référence</span><span>Libellé</span><span>Format</span><span>Durée</span><span>Statut</span><span class="act-c">Actions</span></div>
      <div id="tbody">${S.entries.length===0?'<div class="empty">Aucun dossier au planning</div>':""}
        ${S.entries.map((e,i)=>mkRow(e,i,sl)).join("")}
      </div>
    </section>
  </div><div id="mroot"></div>`;
  setupDD();
}

function mkTL(mon,slots){
  const we=addD(mon,7),days=[];
  for(let i=0;i<7;i++){const d=addD(mon,i),w=whFor(d.getDay());if(!w)continue;days.push({date:d,di:d.getDay(),s:w[0],e:w[1],t:w[1]-w[0]})}
  if(!days.length)return'<div style="color:var(--dim);padding:8px;font-size:13px">Aucun jour ouvré</div>';
  const tot=days.reduce((s,d)=>s+d.t,0);let c=0;
  const cols=days.map(d=>{const cs=c;c+=d.t;return{...d,cs,ce:c}});
  const now=new Date(),ts=now.toDateString();
  function gp(dt){for(const c of cols){if(dt.toDateString()===c.date.toDateString()){const h=Math.max(c.s,Math.min(c.e,dt.getHours()+dt.getMinutes()/60));return c.cs+(h-c.s)}}return dt<mon?0:tot}
  const ws=slots.filter(s=>{const ss=new Date(s.start),se=new Date(s.end);return ss<we&&se>mon});

  let h=`<div class="tl-wrap" data-mon="${mon.toISOString()}"><div class="dh">`;
  cols.forEach(c=>{const td=c.date.toDateString()===ts,sa=c.di===6;
    h+=`<div class="dh-cell ${td?'today':''} ${sa?'sat':''}" style="flex:${c.t}">${DN[c.di]} ${fd(c.date)}<small>${c.s}h–${c.e}h</small></div>`});
  h+=`</div><div class="tl-bar">`;
  cols.slice(1).forEach(c=>{h+=`<div class="d-sep" style="left:${(c.cs/tot)*100}%"></div>`});

  ws.forEach((s,idx)=>{
    const ss=new Date(s.start),se=new Date(s.end);
    const cs=ss<mon?mon:ss,ce=se>we?we:se;
    const sp=gp(cs),ep=gp(ce),l=(sp/tot)*100,w=Math.max(.5,((ep-sp)/tot)*100);
    const co=CC[idx%CC.length];
    const fm=s.format_l&&s.format_h?`${s.format_l} x ${s.format_h} mm`:"—";
    const st=s.statut==="en_cours"?"En cours":"En attente";
    h+=`<div class="slot" style="left:${l}%;width:${w}%;background:${co}cc;border:1px solid ${co};box-shadow:0 2px 12px ${co}33"
      onmouseenter="showTip(event,this)" onmousemove="moveTip(event)" onmouseleave="hideTip()"
      data-ref="${s.reference}" data-lbl="${s.client||''} ${s.description?'— '+s.description:''}"
      data-fmt="${fm}" data-dur="${s.duree_heures}h" data-deb="${fdt(ss)}" data-fin="${fdt(se)}" data-st="${st}" data-co="${co}">
      ${w>4?`<span>${s.reference}</span>`:""}</div>`});

  const np=gp(now);
  if(np>0&&np<tot)h+=`<div class="now-l" style="left:${(np/tot)*100}%"><div class="now-d"></div></div>`;
  h+=`</div></div>`;return h;
}

function mkRow(e,i,slots){
  const fm=e.format_l&&e.format_h?`${e.format_l} x ${e.format_h}`:"—";
  const sc=e.statut==="en_cours"?"run":e.statut==="termine"?"ter":"att";
  const sl={run:"En cours",ter:"Terminé",att:"En attente"}[sc];
  const co=CC[i%CC.length];
  const slot=slots.find(s=>s.entry_id===e.id);
  const per=slot?`${fdt(new Date(slot.start))} → ${fdt(new Date(slot.end))}`:"";
  return`<div class="tr" draggable="true" data-eid="${e.id}" data-idx="${i}"
    style="animation:slideIn .3s ease ${i*.03}s both;${i===0?`border-left:3px solid ${co}`:'border-left:3px solid transparent'}">
    <span class="dh-handle">⠿</span>
    <div><div class="cd" style="background:${co}"></div></div>
    <span class="ref ${sc}">${e.reference}</span>
    <span class="lbl">${e.client||""} ${e.description?"— "+e.description:""}</span>
    <span class="fmt">${fm}</span><span class="dur">${e.duree_heures}h</span>
    <span class="st ${sc}">${sc==="run"?'<span style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;display:inline-block"></span>':""}${sl}</span>
    <div class="acts">
      <button class="ab" onclick="openInsert(${e.id})" title="Insérer après">↳+</button>
      <button class="ab" onclick="openEdit(${e.id})" title="Modifier">✎</button>
      <button class="ab del" onclick="if(confirm('Supprimer ?'))delEntry(${e.id})" title="Supprimer">✕</button>
    </div></div>`
}

// ── Tooltip ──
let tipEl=null;
function showTip(ev,el){hideTip();const d=el.dataset;tipEl=document.createElement("div");tipEl.className="tip";
  tipEl.style.borderColor=d.co+"55";
  tipEl.innerHTML=`<div class="tip-hdr"><div class="tip-bar" style="background:${d.co}"></div><div><div class="tip-ref">${d.ref}</div><div class="tip-lbl">${d.lbl}</div></div></div>
    <div class="tip-grid"><span class="k">Format</span><span class="v">${d.fmt}</span><span class="k">Durée</span><span class="v">${d.dur}</span>
    <span class="k">Début</span><span class="v">${d.deb}</span><span class="k">Fin</span><span class="v">${d.fin}</span>
    <span class="k">Statut</span><span class="v" style="color:${d.st==='En cours'?'var(--green)':'var(--amber)'};font-weight:600">${d.st}</span></div>`;
  el.closest(".tl-wrap").appendChild(tipEl);moveTip(ev)}
function moveTip(ev){if(!tipEl)return;const c=tipEl.parentElement.getBoundingClientRect();
  let x=ev.clientX-c.left+12,y=ev.clientY-c.top-tipEl.offsetHeight-12;
  if(x+tipEl.offsetWidth>c.width)x=c.width-tipEl.offsetWidth-8;if(x<0)x=8;if(y<0)y=ev.clientY-c.top+20;
  tipEl.style.left=x+"px";tipEl.style.top=y+"px"}
function hideTip(){if(tipEl){tipEl.remove();tipEl=null}}

// ── Drag & Drop ──
function setupDD(){
  const rows=document.querySelectorAll(".tr[draggable]");let di=null;
  rows.forEach(r=>{
    r.addEventListener("dragstart",e=>{di=+r.dataset.idx;r.classList.add("dra");e.dataTransfer.effectAllowed="move"});
    r.addEventListener("dragover",e=>{e.preventDefault();r.classList.add("dov")});
    r.addEventListener("dragleave",()=>r.classList.remove("dov"));
    r.addEventListener("drop",e=>{e.preventDefault();r.classList.remove("dov");
      const ti=+r.dataset.idx;if(di!==null&&di!==ti){const ids=S.entries.map(e=>e.id);const[m]=ids.splice(di,1);ids.splice(ti,0,m);
        api(`/machines/${MID}/reorder`,{method:"POST",body:JSON.stringify({entry_ids:ids})}).then(()=>load())}});
    r.addEventListener("dragend",()=>{r.classList.remove("dra");di=null})
  })
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

function dossierFields(ref,client,desc,fl,fh,dur,statut,showStatut){
  return`
    <div class="fd"><label>Référence</label><input id="f-ref" value="${ref}" placeholder="DOS-2026-XXX"></div>
    <div class="fd"><label>Client</label><input id="f-cli" value="${client}" placeholder="Nom du client"></div>
    <div class="fd"><label>Description</label><input id="f-desc" value="${desc}" placeholder="Étiquettes, stickers..."></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="fd"><label>Largeur (mm)</label><input type="number" id="f-fl" value="${fl}" placeholder="100"></div>
      <div class="fd"><label>Hauteur (mm)</label><input type="number" id="f-fh" value="${fh}" placeholder="70"></div>
    </div>
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
    reference:(document.getElementById("f-ref").value||"").trim(),
    client:document.getElementById("f-cli").value||"",
    description:document.getElementById("f-desc").value||"",
    format_l:parseFloat(document.getElementById("f-fl").value)||null,
    format_h:parseFloat(document.getElementById("f-fh").value)||null,
    duree_heures:Math.max(MIND,Math.min(MAXD,parseInt(document.getElementById("f-dur").value)||8)),
  };
  if(withStatut)d.statut=document.getElementById("f-stat").value;
  return d;
}

function openAdd(){
  document.getElementById("mroot").innerHTML=modalHTML(
    "Ajouter un dossier",
    dossierFields("","","","","",8,"attente",false),
    "Ajouter","submitAdd()"
  );
}
async function submitAdd(){
  const d=getFormData(false);
  if(!d.reference)return alert("Référence requise");
  await api(`/machines/${MID}/entries`,{method:"POST",body:JSON.stringify(d)});
  closeM();load();
}

function openEdit(id){
  const e=S.entries.find(x=>x.id===id);if(!e)return;
  document.getElementById("mroot").innerHTML=modalHTML(
    `Modifier — ${e.reference}`,
    dossierFields(e.reference,e.client||"",e.description||"",e.format_l||"",e.format_h||"",e.duree_heures,e.statut,true),
    "Enregistrer",`submitEdit(${id})`
  );
}
async function submitEdit(id){
  const d=getFormData(true);
  if(!d.reference)return alert("Référence requise");
  await api(`/machines/${MID}/entries/${id}`,{method:"PUT",body:JSON.stringify(d)});
  closeM();load();
}

function openInsert(afterId){
  document.getElementById("mroot").innerHTML=modalHTML(
    "Insérer un dossier après",
    dossierFields("","","","","",8,"attente",false),
    "Insérer",`submitInsert(${afterId})`
  );
}
async function submitInsert(afterId){
  const d=getFormData(false);
  if(!d.reference)return alert("Référence requise");
  await api(`/machines/${MID}/insert-after/${afterId}`,{method:"POST",body:JSON.stringify(d)});
  closeM();load();
}

function closeM(){document.getElementById("mroot").innerHTML=""}

load();
</script>
</body>
</html>
"""
