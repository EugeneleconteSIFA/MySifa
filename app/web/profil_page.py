"""MySifa — Mon profil (application standalone)

Accès : /profil
Tout utilisateur authentifié, indépendamment de MyProd ou des autres apps.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/profil", response_class=HTMLResponse)
def profil_page(request: Request):
    try:
        _ = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/profil", status_code=302)
        raise
    return HTMLResponse(content=PROFIL_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


PROFIL_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Mon profil — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<style>
/* ── Variables : MySifa (défaut dark) ── */
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;
  --text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;
  --accent:#22d3ee;--accent-bg:rgba(34,211,238,0.12);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;
}
/* MySifa clair */
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;
  --text:#0f172a;--text2:#475569;--muted:#64748b;
  --accent:#0891b2;--accent-bg:rgba(8,145,178,0.10);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
/* Palette Forge */
body.palette-forge{
  --bg:#1A2332;--card:#243044;--border:#2D4163;
  --text:#f0f4fc;--text2:#b8c9e8;--muted:#64748B;
  --accent:#3A7BD5;--accent-bg:rgba(58,123,213,0.15);
  --ok:#34d399;--danger:#f87171;--warn:#F0A500;
}
body.palette-forge.light{
  --bg:#F4F6FA;--card:#ffffff;--border:#dce3ef;
  --text:#1A2332;--text2:#2D4163;--muted:#64748B;
  --accent:#3A7BD5;--accent-bg:rgba(58,123,213,0.10);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
/* Palette Cocon */
body.palette-cocon{
  --bg:#1f0e14;--card:#2e1620;--border:#4a2535;
  --text:#f5e8ed;--text2:#dbb8c8;--muted:#9e6a80;
  --accent:#e8729a;--accent-bg:rgba(232,114,154,0.12);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;
}
body.palette-cocon.light{
  --bg:#fdf8f5;--card:#fff9f7;--border:#f0ddd8;
  --text:#3d1a24;--text2:#7a4155;--muted:#b08090;
  --accent:#c4577a;--accent-bg:rgba(196,87,122,0.10);
  --ok:#2e7d32;--danger:#c0392b;--warn:#e6a817;
}
/* Style Compact */
body.style-mini{font-family:'Courier New','SF Mono',monospace}
body.style-mini .card,.style-mini input,.style-mini button,.style-mini .tab-btn{border-radius:4px!important}
/* Style Aéré */
body.style-round .card{border-radius:20px!important}
body.style-round input,body.style-round button,body.style-round .tab-btn{border-radius:14px!important}

*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;transition:background .2s,color .2s}
.shell{max-width:580px;margin:0 auto;padding:24px 20px 48px}

/* ── Topbar ── */
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:28px;flex-wrap:wrap}
.brand{font-size:20px;font-weight:800;letter-spacing:-.5px}
.brand span{color:var(--accent)}
.brand-sub{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-top:2px}
.top-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.btn-icon{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,background .15s}
.btn-icon:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.back-link{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:500;text-decoration:none;cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s}
.back-link:hover{border-color:var(--accent);color:var(--accent)}

/* ── Onglets ── */
.tabs{display:flex;gap:4px;margin-bottom:20px;border-bottom:1px solid var(--border);padding-bottom:0}
.tab-btn{background:transparent;border:none;border-bottom:2px solid transparent;padding:10px 16px;font-size:13px;font-weight:600;color:var(--text2);cursor:pointer;font-family:inherit;transition:color .15s,border-color .15s;margin-bottom:-1px;border-radius:0}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-btn:hover:not(.active){color:var(--text)}

/* ── Card ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px 22px;margin-bottom:16px}
.card h1{font-size:19px;font-weight:800;margin:0 0 5px}
.card .sub{font-size:13px;color:var(--muted);margin-bottom:20px}
.role-pill{display:inline-block;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--accent);background:var(--accent-bg);padding:4px 10px;border-radius:999px;margin-bottom:14px}
.field{margin-bottom:13px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.field input{width:100%;padding:10px 13px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus{border-color:var(--accent)}
hr{border:none;border-top:1px solid var(--border);margin:18px 0}
.btn-save{background:var(--accent);color:#0a0e17;border:none;border-radius:10px;padding:11px 20px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit;margin-top:4px;transition:filter .15s}
.btn-save:hover{filter:brightness(1.06)}
.btn-save:disabled{opacity:.6;cursor:not-allowed}
.meta{font-size:11px;color:var(--muted);margin-top:14px;line-height:1.6}

/* ── Toasts ── */
.toast{position:fixed;bottom:22px;right:22px;z-index:9999;padding:11px 16px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 10px 36px rgba(0,0,0,.4);border:1px solid var(--border);animation:toast-in .2s ease}
.toast.ok{background:rgba(52,211,153,.15);color:var(--ok)}
.toast.err{background:rgba(248,113,113,.15);color:var(--danger)}
@keyframes toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.loading{color:var(--muted);font-size:14px;padding:40px 0;text-align:center}

/* ── Sélecteurs de thème ── */
.pref-section{margin-bottom:24px}
.pref-section-title{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.7px;margin-bottom:10px}
.theme-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.theme-card{border:2px solid var(--border);border-radius:12px;padding:14px 12px;cursor:pointer;transition:border-color .15s,background .15s;background:var(--bg);text-align:center;position:relative}
.theme-card:hover{border-color:var(--accent);background:var(--accent-bg)}
.theme-card.selected{border-color:var(--accent);background:var(--accent-bg)}
.theme-card .tc-check{position:absolute;top:8px;right:8px;width:16px;height:16px;border-radius:50%;background:var(--accent);display:none;align-items:center;justify-content:center}
.theme-card.selected .tc-check{display:flex}
.theme-card .tc-preview{height:48px;border-radius:8px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;gap:4px;font-size:9px;font-weight:700;letter-spacing:.3px;overflow:hidden}
.theme-card .tc-name{font-size:12px;font-weight:700;color:var(--text)}
.theme-card .tc-sub{font-size:10px;color:var(--muted);margin-top:2px}

/* Previews palettes */
.prev-mysifa{background:#0a0e17;color:#22d3ee}
.prev-mysifa .dot{width:8px;height:8px;border-radius:50%;background:#22d3ee}
.prev-forge{background:#1A2332;color:#3A7BD5}
.prev-forge .dot{width:8px;height:8px;border-radius:50%;background:#3A7BD5}
.prev-cocon{background:#1f0e14;color:#e8729a}
.prev-cocon .dot{width:8px;height:8px;border-radius:50%;background:#e8729a}
.prev-mysifa-l{background:linear-gradient(135deg,#f1f5f9,#e2e8f0);color:#0891b2}
.prev-forge-l{background:linear-gradient(135deg,#F4F6FA,#dce3ef);color:#3A7BD5}
.prev-cocon-l{background:linear-gradient(135deg,#fdf8f5,#f0ddd8);color:#c4577a}

/* Previews styles */
.prev-defaut{background:var(--card);border-radius:8px;display:flex;gap:4px;padding:4px}
.prev-defaut .b{height:24px;flex:1;border-radius:6px;background:var(--border)}
.prev-mini{background:var(--card);border-radius:2px;display:flex;gap:3px;padding:4px}
.prev-mini .b{height:24px;flex:1;border-radius:2px;background:var(--border)}
.prev-round{background:var(--card);border-radius:14px;display:flex;gap:4px;padding:5px}
.prev-round .b{height:24px;flex:1;border-radius:12px;background:var(--border)}

/* Toggle mode */
.mode-toggle{display:flex;gap:10px}
.mode-card{flex:1;border:2px solid var(--border);border-radius:12px;padding:14px 12px;cursor:pointer;transition:border-color .15s,background .15s;background:var(--bg);text-align:center;display:flex;align-items:center;gap:10px;justify-content:center}
.mode-card:hover{border-color:var(--accent);background:var(--accent-bg)}
.mode-card.selected{border-color:var(--accent);background:var(--accent-bg)}
.mode-ico{font-size:22px}
.mode-label{font-size:13px;font-weight:700;color:var(--text)}
.mode-sub{font-size:10px;color:var(--muted)}

.btn-prefs-save{width:100%;background:var(--accent);color:#0a0e17;border:none;border-radius:10px;padding:12px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit;margin-top:8px;transition:filter .15s}
.btn-prefs-save:hover{filter:brightness(1.06)}
.pref-hint{font-size:11px;color:var(--muted);text-align:center;margin-top:10px;line-height:1.5}
</style>
</head>
<body>
<div class="shell">
  <div class="top">
    <div>
      <div class="brand">My<span>Sifa</span></div>
      <div class="brand-sub">Mon profil</div>
    </div>
    <div class="top-actions">
      <a class="back-link" href="/" title="Retour au portail">← Portail</a>
      <button type="button" class="btn-icon" id="btn-logout" title="Déconnexion" aria-label="Déconnexion">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </button>
    </div>
  </div>

  <!-- Onglets -->
  <div class="tabs">
    <button class="tab-btn active" id="tab-info" onclick="showTab('info')">Mes informations</button>
    <button class="tab-btn" id="tab-prefs" onclick="showTab('prefs')">Mes préférences</button>
  </div>

  <!-- Contenu onglets -->
  <div id="pane-info"><div class="loading">Chargement…</div></div>
  <div id="pane-prefs" style="display:none"></div>
</div>
<script src="/static/support_widget.js"></script>
<script>
const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};
let ME=null;

// ─── État préférences (depuis localStorage) ───────────────────────
let PREFS={palette:'mysifa',style:'defaut',mode:'dark'};

function loadPrefsFromStorage(){
  const p=localStorage.getItem('mysifa_palette');
  const s=localStorage.getItem('mysifa_style');
  const t=localStorage.getItem('theme');
  if(p)PREFS.palette=p;
  if(s)PREFS.style=s;
  PREFS.mode=(t==='light')?'light':'dark';
}

function applyPrefsToDOM(){
  const b=document.body;
  // Mode
  b.classList.toggle('light',PREFS.mode==='light');
  // Palette
  b.classList.remove('palette-forge','palette-cocon');
  if(PREFS.palette!=='mysifa')b.classList.add('palette-'+PREFS.palette);
  // Style
  b.classList.remove('style-mini','style-round');
  if(PREFS.style!=='defaut')b.classList.add('style-'+PREFS.style);
}

function savePrefsToStorage(){
  localStorage.setItem('mysifa_palette',PREFS.palette);
  localStorage.setItem('mysifa_style',PREFS.style);
  localStorage.setItem('theme',PREFS.mode);
}

// ─── UI helpers ───────────────────────────────────────────────────
function toast(msg,ok){
  const t=document.createElement('div');
  t.className='toast '+(ok?'ok':'err');
  t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),3200);
}

async function api(path,opts){
  const r=await fetch(path,{credentials:'include',...opts});
  if(r.status===401){location.href='/?next=/profil';throw new Error('auth');}
  if(!r.ok){
    let d='Erreur';
    try{const j=await r.json();d=(j&&j.detail)?(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail)):d;}catch(e){}
    throw new Error(d);
  }
  if(r.status===204)return null;
  const ct=r.headers.get('content-type')||'';
  if(ct.includes('application/json'))return r.json();
  return null;
}

function fD(iso){
  if(!iso)return '';
  try{return new Date(iso).toLocaleString('fr-FR',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});}catch(e){return iso;}
}

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}

// ─── Onglets ──────────────────────────────────────────────────────
function showTab(tab){
  document.getElementById('pane-info').style.display=tab==='info'?'':'none';
  document.getElementById('pane-prefs').style.display=tab==='prefs'?'':'none';
  document.getElementById('tab-info').classList.toggle('active',tab==='info');
  document.getElementById('tab-prefs').classList.toggle('active',tab==='prefs');
  if(tab==='prefs')renderPrefs();
}

// ─── Onglet Mes informations ──────────────────────────────────────
function field(label,id,type,val){
  return `<div class="field"><label for="${id}">${label}</label><input id="${id}" type="${type||'text'}" value="${esc(val)}"></div>`;
}

function renderInfo(){
  const u=ME||{};
  const role=ROLE_LABELS[u.role]||u.role||'';
  document.getElementById('pane-info').innerHTML=`
    <div class="card">
      <div class="role-pill">${esc(role)}</div>
      <h1>Mes informations</h1>
      <p class="sub">Modifiez vos informations personnelles et votre mot de passe.</p>
      <form id="profil-form" onsubmit="return false;">
        ${field('Nom complet','f-nom','text',u.nom)}
        ${field('Email','f-email','email',u.email)}
        ${field('Téléphone','f-tel','tel',u.telephone)}
        ${field('Adresse','f-addr','text',u.adresse)}
        ${field('Date de naissance','f-birth','date',u.date_naissance)}
        <hr>
        ${field('Mot de passe actuel','f-cur-pwd','password','')}
        ${field('Nouveau mot de passe','f-pwd','password','')}
        ${field('Confirmer le mot de passe','f-pwd2','password','')}
        <button type="button" class="btn-save" id="btn-save">Enregistrer</button>
        <div class="meta">
          ${u.created_at?`<div>Créé le ${esc(fD(u.created_at))}</div>`:''}
          ${u.last_login?`<div>Dernière connexion : ${esc(fD(u.last_login))}</div>`:''}
        </div>
      </form>
    </div>`;
  document.getElementById('btn-save').onclick=saveInfo;
}

async function saveInfo(){
  const btn=document.getElementById('btn-save');
  if(btn)btn.disabled=true;
  const body={
    nom:(document.getElementById('f-nom')?.value||'').trim(),
    email:(document.getElementById('f-email')?.value||'').trim(),
    telephone:(document.getElementById('f-tel')?.value||'').trim(),
    adresse:(document.getElementById('f-addr')?.value||'').trim(),
    date_naissance:(document.getElementById('f-birth')?.value||'').trim(),
  };
  const pwd=(document.getElementById('f-pwd')?.value||'');
  const pwd2=(document.getElementById('f-pwd2')?.value||'');
  const cur=(document.getElementById('f-cur-pwd')?.value||'');
  if(pwd){body.password=pwd;body.password_confirm=pwd2;body.current_password=cur;}
  try{
    await api('/api/auth/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    ME=await api('/api/auth/me');
    toast('Profil mis à jour',true);
    renderInfo();
  }catch(e){
    toast(e.message||'Enregistrement impossible',false);
  }finally{
    if(btn)btn.disabled=false;
  }
}

// ─── Onglet Mes préférences ───────────────────────────────────────
function checkMark(){
  return `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#0a0e17" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
}

function palCard(id,name,sub,prevClass,dotColor){
  const sel=PREFS.palette===id?'selected':'';
  return `<div class="theme-card ${sel}" onclick="selectPalette('${id}')">
    <div class="tc-check">${checkMark()}</div>
    <div class="tc-preview ${prevClass}">
      <div style="width:8px;height:8px;border-radius:50%;background:${dotColor}"></div>
      <div style="width:8px;height:8px;border-radius:50%;background:${dotColor};opacity:.5"></div>
      <div style="width:8px;height:8px;border-radius:50%;background:${dotColor};opacity:.25"></div>
    </div>
    <div class="tc-name">${name}</div>
    <div class="tc-sub">${sub}</div>
  </div>`;
}

function styleCard(id,name,sub,innerHtml){
  const sel=PREFS.style===id?'selected':'';
  return `<div class="theme-card ${sel}" onclick="selectStyle('${id}')">
    <div class="tc-check">${checkMark()}</div>
    <div class="tc-preview" style="background:var(--card);padding:6px;gap:3px;border-radius:8px">
      ${innerHtml}
    </div>
    <div class="tc-name">${name}</div>
    <div class="tc-sub">${sub}</div>
  </div>`;
}

function modeCard(id,ico,label,sub){
  const sel=PREFS.mode===id?'selected':'';
  return `<div class="mode-card ${sel}" onclick="selectMode('${id}')">
    <span class="mode-ico">${ico}</span>
    <div>
      <div class="mode-label">${label}</div>
      <div class="mode-sub">${sub}</div>
    </div>
  </div>`;
}

function renderPrefs(){
  const styleBlocks={
    defaut:`<div style="height:18px;flex:1;border-radius:6px;background:var(--border)"></div><div style="height:18px;flex:1;border-radius:6px;background:var(--border)"></div><div style="height:18px;flex:1;border-radius:6px;background:var(--border)"></div>`,
    mini:`<div style="height:18px;flex:1;border-radius:2px;background:var(--border);font-size:8px;font-family:monospace;display:flex;align-items:center;justify-content:center;color:var(--muted)">_</div><div style="height:18px;flex:1;border-radius:2px;background:var(--border)"></div><div style="height:18px;flex:1;border-radius:2px;background:var(--border)"></div>`,
    round:`<div style="height:18px;flex:1;border-radius:12px;background:var(--border)"></div><div style="height:18px;flex:1;border-radius:12px;background:var(--border)"></div><div style="height:18px;flex:1;border-radius:12px;background:var(--border)"></div>`
  };

  document.getElementById('pane-prefs').innerHTML=`
    <div class="card">
      <h1>Mes préférences</h1>
      <p class="sub">Personnalisez l'apparence de MySifa selon vos goûts.</p>

      <div class="pref-section">
        <div class="pref-section-title">Palette de couleurs</div>
        <div class="theme-grid" id="palette-grid">
          ${palCard('mysifa','MySifa','Cyan · défaut','prev-mysifa','#22d3ee')}
          ${palCard('forge','Forge','Bleu marine · ambre','prev-forge','#3A7BD5')}
          ${palCard('cocon','Cocon','Pivoine · rosé','prev-cocon','#e8729a')}
        </div>
      </div>

      <div class="pref-section">
        <div class="pref-section-title">Style de l'interface</div>
        <div class="theme-grid" id="style-grid">
          ${styleCard('defaut','Défaut','Équilibré · tech',`<div style="display:flex;gap:3px;width:100%">${styleBlocks.defaut}</div>`)}
          ${styleCard('mini','Compact','Serré · monospace',`<div style="display:flex;gap:2px;width:100%">${styleBlocks.mini}</div>`)}
          ${styleCard('round','Aéré','Doux · arrondi',`<div style="display:flex;gap:3px;width:100%">${styleBlocks.round}</div>`)}
        </div>
      </div>

      <div class="pref-section">
        <div class="pref-section-title">Mode d'affichage</div>
        <div class="mode-toggle" id="mode-toggle">
          ${modeCard('dark','🌙','Sombre','Fond foncé')}
          ${modeCard('light','☀','Clair','Fond blanc')}
        </div>
      </div>

      <button class="btn-prefs-save" onclick="savePrefs()">Appliquer les préférences</button>
      <p class="pref-hint">Les préférences s'appliquent immédiatement sur toutes les pages.</p>
    </div>`;
}

function selectPalette(id){
  PREFS.palette=id;
  renderPrefs();
  applyPrefsToDOM();
}

function selectStyle(id){
  PREFS.style=id;
  renderPrefs();
  applyPrefsToDOM();
}

function selectMode(id){
  PREFS.mode=id;
  renderPrefs();
  applyPrefsToDOM();
}

async function savePrefs(){
  savePrefsToStorage();
  applyPrefsToDOM();
  // Sync serveur
  try{
    await api('/api/auth/me',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({theme_prefs:{palette:PREFS.palette,style:PREFS.style,mode:PREFS.mode}})
    });
    toast('Préférences enregistrées',true);
  }catch(e){
    // Ne pas bloquer si serveur échoue — localStorage est déjà à jour
    toast('Préférences appliquées localement',true);
  }
}

// ─── Déconnexion ──────────────────────────────────────────────────
document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

// ─── Init ─────────────────────────────────────────────────────────
(async function init(){
  loadPrefsFromStorage();
  applyPrefsToDOM();

  try{
    ME=await api('/api/auth/me');
    // Sync depuis serveur si des préfs y sont sauvegardées
    if(ME&&ME.theme_prefs){
      try{
        const sp=typeof ME.theme_prefs==='string'?JSON.parse(ME.theme_prefs):ME.theme_prefs;
        if(sp&&typeof sp==='object'){
          if(sp.palette)PREFS.palette=sp.palette;
          if(sp.style)PREFS.style=sp.style;
          if(sp.mode)PREFS.mode=sp.mode;
          savePrefsToStorage();
          applyPrefsToDOM();
        }
      }catch(e){}
    }
    renderInfo();
  }catch(e){
    if(e.message!=='auth'){
      document.getElementById('pane-info').innerHTML='<div class="card"><p class="sub">Impossible de charger le profil.</p></div>';
    }
  }
})();
</script>
</body>
</html>
"""
