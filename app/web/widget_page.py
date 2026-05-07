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
  width:340px;overflow:hidden;user-select:none;
}
body.light{
  --bg:#f1f5f9;--card:#ffffff;--border:#e2e8f0;
  --text:#0f172a;--muted:#64748b;--accent:#0891b2;
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
  padding:14px 12px;gap:10px;font-size:12px;color:var(--muted);
}
.offline a{color:var(--accent);text-decoration:none;font-size:11px;padding:5px 12px;border:1px solid var(--accent);border-radius:6px}
.offline a:hover{background:rgba(56,189,248,.1)}

/* login */
.login{
  display:flex;flex-direction:column;gap:10px;
  width:100%;max-width:260px;
}
.login-title{font-weight:800;color:var(--text);font-size:12px;letter-spacing:.3px}
.login-row{display:flex;flex-direction:column;gap:6px}
.login-row label{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.3px;text-transform:uppercase}
.login-row input{
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;color:var(--text);font-size:12px;outline:none;
}
.login-row input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(56,189,248,.12)}
.login-actions{display:flex;gap:8px;align-items:center}
.btn{
  border-radius:10px;padding:9px 12px;font-weight:800;cursor:pointer;border:1px solid transparent;
  font-size:12px;transition:filter .15s;user-select:none;
}
.btn:hover{filter:brightness(1.05)}
.btn-accent{background:var(--accent);color:var(--bg)}
.btn-ghost{background:transparent;color:var(--text);border-color:var(--border)}
.login-err{
  display:none;
  background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);
  border-radius:10px;padding:8px 10px;font-size:11px;color:rgba(248,113,113,1);
}
.login-err.show{display:block}
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
    <button class="bi" id="btn-theme" title="Thème">◐</button>
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
let loginSubmitting=false;

function renderLogin(message){
  const main=document.getElementById('main');
  main.innerHTML=`<div class="offline">
    <div class="login">
      <div class="login-title">Connexion MySifa</div>
      <div class="login-err" id="login-err"></div>
      <div class="login-row">
        <label for="login-email">Adresse e-mail</label>
        <input id="login-email" type="email" autocomplete="username" placeholder="votre@email.fr">
      </div>
      <div class="login-row">
        <label for="login-password">Mot de passe</label>
        <input id="login-password" type="password" autocomplete="current-password" placeholder="••••••••">
      </div>
      <div class="login-actions">
        <button class="btn btn-accent" id="login-submit">${loginSubmitting?'Connexion…':'Se connecter'}</button>
        <button class="btn btn-ghost" id="login-open" title="Ouvrir MySifa dans le navigateur">Ouvrir MySifa</button>
      </div>
    </div>
  </div>`;

  const errEl=document.getElementById('login-err');
  if(message){
    errEl.textContent=message;
    errEl.classList.add('show');
  }

  const emailEl=document.getElementById('login-email');
  const passEl=document.getElementById('login-password');
  requestAnimationFrame(()=>emailEl?.focus());

  function setErr(msg){
    if(!msg){errEl.textContent='';errEl.classList.remove('show');return;}
    errEl.textContent=msg;errEl.classList.add('show');
  }

  async function submit(){
    if(loginSubmitting)return;
    const email=(emailEl?.value||'').trim();
    const password=(passEl?.value||'');
    if(!email||!password){setErr('Identifiants requis.');return;}
    setErr(null);
    loginSubmitting=true;
    const sb=document.getElementById('login-submit');
    if(sb)sb.textContent='Connexion…';
    try{
      const r=await fetch('/api/auth/login',{
        method:'POST',
        credentials:'include',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email,password})
      });
      const d=await r.json().catch(()=>null);
      if(!r.ok){
        setErr((d&&d.detail)||'Connexion impossible.');
        return;
      }
      await load();
    }catch(e){
      setErr('Connexion impossible.');
    }finally{
      loginSubmitting=false;
      const b=document.getElementById('login-submit');
      if(b)b.textContent='Se connecter';
    }
  }

  document.getElementById('login-submit')?.addEventListener('click', (e)=>{e.preventDefault();submit();});
  passEl?.addEventListener('keydown', (e)=>{ if(e.key==='Enter'){e.preventDefault();submit();} });
  emailEl?.addEventListener('keydown', (e)=>{ if(e.key==='Enter'){e.preventDefault();passEl?.focus();} });
  document.getElementById('login-open')?.addEventListener('click', (e)=>{
    e.preventDefault();
    window.open('/', '_blank');
  });

  requestFit();
}

async function load(){
  const main=document.getElementById('main');
  const footer=document.getElementById('footer');
  try{
    const r=await fetch('/api/production/machine-status',{credentials:'include'});
    if(r.status===401||r.status===403){
      footer.textContent='';
      renderLogin(null);
      return;
    }
    if(!r.ok)throw new Error('HTTP '+r.status);
    const d=await r.json();
    main.innerHTML=`<div class="grid">${mkCard('C1',d.C1)}${mkCard('C2',d.C2)}</div>`;
    const n=new Date();
    footer.textContent='Actualisé à '+n.toLocaleTimeString('fr-FR');
    loadingFirst=false;
    requestFit();
  }catch(e){
    if(loadingFirst){
      main.innerHTML=`<div class="offline"><div>⚠️ Connexion impossible</div></div>`;
      footer.textContent='';
      requestFit();
    }
  }
}

load();
setInterval(load,30000);

function applyTheme(mode){
  const light = mode === 'light';
  document.body.classList.toggle('light', light);
  try{ localStorage.setItem('mysifa_widget_theme', light ? 'light' : 'dark'); }catch(_){}
}
function toggleTheme(){
  const isLight = document.body.classList.contains('light');
  applyTheme(isLight ? 'dark' : 'light');
}
try{
  const saved = localStorage.getItem('mysifa_widget_theme');
  if(saved === 'light' || saved === 'dark') applyTheme(saved);
}catch(_){}

document.getElementById('btn-refresh').onclick=()=>{
  const btn=document.getElementById('btn-refresh');
  btn.textContent='↺'; btn.classList.add('spin');
  load().finally(()=>{btn.classList.remove('spin');});
};
document.getElementById('btn-theme').onclick=()=>{ toggleTheme(); };
document.getElementById('btn-close').onclick=()=>{
  if(window.electronAPI)window.electronAPI.close();
  else window.close();
};

function requestFit(){
  if(!window.electronAPI || !window.electronAPI.resizeTo) return;
  // Double rAF : garantit que le layout est complètement calculé avant la mesure
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    const h = document.documentElement.scrollHeight;
    const target = Math.max(160, Math.min(520, h));
    window.electronAPI.resizeTo(340, target);
  }));
}

// ResizeObserver : ajuste la fenêtre automatiquement si le contenu change de taille
if(window.electronAPI?.resizeTo && typeof ResizeObserver !== 'undefined'){
  new ResizeObserver(()=>requestFit()).observe(document.body);
}
</script>
</body>
</html>"""
