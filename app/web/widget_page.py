"""MyProd Widget — page HTML autonome servie à /widget"""

WIDGET_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyProd Widget</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#e2e8f0;--muted:#64748b;--accent:#38bdf8;
}
html,body{
  background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  width:340px;height:100vh;overflow:hidden;user-select:none;
}
/* ── Barre titre (déplaçable dans Electron) ── */
.tb{
  -webkit-app-region:drag;
  display:flex;align-items:center;justify-content:space-between;
  padding:0 12px;height:36px;
  background:var(--card);border-bottom:1px solid var(--border);
  flex-shrink:0;
}
.tb-title{font-size:12px;font-weight:700;color:var(--accent);letter-spacing:.4px;display:flex;align-items:center;gap:6px}
.tb-actions{-webkit-app-region:no-drag;display:flex;gap:4px}
.bi{
  background:none;border:none;color:var(--muted);cursor:pointer;
  padding:4px 7px;border-radius:5px;font-size:13px;line-height:1;
  transition:background .15s,color .15s;
}
.bi:hover{color:var(--text);background:rgba(255,255,255,.07)}
.bi.close:hover{color:#ef4444}
/* ── Grille cartes ── */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px}
.card{
  background:var(--card);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;transition:border-color .3s;
}
.card-head{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 11px;border-bottom:1px solid var(--border);
}
.card-nom{font-size:12px;font-weight:700}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted);transition:background .3s}
.card-body{padding:9px 11px;display:flex;flex-direction:column;gap:5px}
.statut{
  display:inline-flex;align-items:center;gap:5px;
  font-size:11px;font-weight:700;padding:3px 9px;
  border-radius:20px;width:fit-content;
}
.duree{font-size:10px;color:var(--muted)}
.dv{font-weight:700;color:var(--text)}
.op{font-size:10px;color:var(--muted)}
.dos{
  background:rgba(255,255,255,.04);border:1px solid var(--border);
  border-radius:6px;padding:6px 8px;display:flex;flex-direction:column;gap:2px;
}
.dos-ref{font-weight:700;color:var(--accent);font-family:monospace;font-size:10px}
.dos-cli{font-weight:600;font-size:11px}
.dos-des{color:var(--muted);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* couleurs statuts */
.s-production .dot,.s-production .pulse{background:#22c55e}
.s-production .statut{background:rgba(34,197,94,.12);color:#22c55e}
.s-calage .dot{background:#f97316}
.s-calage .statut{background:rgba(249,115,22,.12);color:#f97316}
.s-arret .dot{background:#ef4444}
.s-arret .statut{background:rgba(239,68,68,.12);color:#ef4444}
.s-changement .dot{background:#a78bfa}
.s-changement .statut{background:rgba(167,139,250,.12);color:#a78bfa}
.s-nettoyage .dot{background:#c084fc}
.s-nettoyage .statut{background:rgba(192,132,252,.12);color:#c084fc}
.s-eteinte .dot{background:#475569}
.s-eteinte .statut{background:rgba(71,85,105,.12);color:#94a3b8}
/* pulsation dot production */
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.s-production .dot{animation:pulse 2s infinite}
.s-arret .dot{animation:pulse 1s infinite}
/* footer */
.footer{padding:3px 12px;font-size:9px;color:var(--muted);text-align:right;border-top:1px solid var(--border)}
/* état hors-ligne / erreur */
.offline{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:calc(100vh - 36px);gap:10px;font-size:12px;color:var(--muted);
}
.offline a{color:var(--accent);text-decoration:none;font-size:11px;padding:5px 12px;border:1px solid var(--accent);border-radius:6px}
.offline a:hover{background:rgba(56,189,248,.1)}
/* spinner */
@keyframes spin{to{transform:rotate(360deg)}}
.spin{display:inline-block;animation:spin 1s linear infinite}
</style>
</head>
<body>
<div class="tb">
  <span class="tb-title">🏭 MyProd Widget</span>
  <div class="tb-actions">
    <button class="bi" id="btn-refresh" title="Actualiser">↺</button>
    <button class="bi close" id="btn-close" title="Fermer">✕</button>
  </div>
</div>
<div id="main"><div class="offline"><span class="spin">↺</span></div></div>
<div class="footer" id="footer"></div>

<script>
const ICONS={production:'▶',calage:'⚙',arret:'⛔',changement:'↻',nettoyage:'🧹',eteinte:'○',autre:'·'};
const DL={production:'En production depuis',calage:'En calage depuis',arret:'En arrêt depuis',
          changement:'En changement depuis',nettoyage:'En nettoyage depuis',eteinte:'Éteinte depuis',autre:'Depuis'};

function esc(t){return(t||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtDuree(min){
  if(min==null||min<0)return null;
  if(min<1)return 'à l\'instant';
  const h=Math.floor(min/60),m=min%60;
  if(h===0)return m+'min';
  return m===0?(h+'h'):(h+'h '+m+'min');
}
function mkCard(mkey,m){
  const sk=m?(m.statut_key||'eteinte'):'eteinte';
  const label=m?(m.statut_label||'Éteinte'):'Éteinte';
  const nom=m?m.nom:(mkey==='C1'?'Cohésio 1':'Cohésio 2');
  const op=m?(m.operateur||''):'';
  const dos=m?m.dossier:null;
  const icon=ICONS[sk]||'·';
  const ds=m?fmtDuree(m.duree_min):null;
  const dl=DL[sk]||'Depuis';
  let dosH='';
  if(dos&&dos.no_dossier){
    dosH=`<div class="dos">
      <div class="dos-ref">#${esc(dos.no_dossier)}</div>
      ${dos.client?`<div class="dos-cli">${esc(dos.client)}</div>`:''}
      ${dos.designation?`<div class="dos-des">${esc(dos.designation)}</div>`:''}
    </div>`;
  }
  return `<div class="card s-${esc(sk)}">
    <div class="card-head"><span class="card-nom">${esc(nom)}</span><span class="dot"></span></div>
    <div class="card-body">
      <div class="statut">${icon} ${esc(label)}</div>
      ${ds?`<div class="duree">${esc(dl)} <span class="dv">${esc(ds)}</span></div>`:''}
      ${op?`<div class="op">👤 ${esc(op)}</div>`:''}
      ${dosH}
    </div>
  </div>`;
}

let loadingFirst=true;
async function load(){
  const main=document.getElementById('main');
  const footer=document.getElementById('footer');
  try{
    const r=await fetch('/api/production/machine-status',{credentials:'include'});
    if(r.status===401||r.status===403){
      main.innerHTML=`<div class="offline">
        <div>🔒 Non connecté</div>
        <a href="/auth/login" target="_blank">Ouvrir MySifa →</a>
      </div>`;
      footer.textContent='';return;
    }
    if(!r.ok)throw new Error('HTTP '+r.status);
    const d=await r.json();
    main.innerHTML=`<div class="grid">${mkCard('C1',d.C1)}${mkCard('C2',d.C2)}</div>`;
    const n=new Date();
    footer.textContent='Actualisé à '+n.toLocaleTimeString('fr-FR');
    loadingFirst=false;
  }catch(e){
    if(loadingFirst){
      main.innerHTML=`<div class="offline"><div>⚠️ Connexion impossible</div></div>`;
      footer.textContent='';
    }
  }
}

load();
setInterval(load,30000);

document.getElementById('btn-refresh').onclick=()=>{
  const btn=document.getElementById('btn-refresh');
  btn.textContent='↺'; btn.classList.add('spin');
  load().finally(()=>{btn.classList.remove('spin');});
};
document.getElementById('btn-close').onclick=()=>{
  if(window.electronAPI)window.electronAPI.close();
  else window.close();
};
</script>
</body>
</html>"""
