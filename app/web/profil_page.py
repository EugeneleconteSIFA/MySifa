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
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--ok:#34d399;--danger:#f87171;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--ok:#059669;--danger:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.shell{max-width:560px;margin:0 auto;padding:24px 20px 48px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:28px;flex-wrap:wrap}
.brand{font-size:20px;font-weight:800;letter-spacing:-.5px}
.brand span{color:var(--accent)}
.brand-sub{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-top:2px}
.top-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.btn-icon{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;transition:border-color .15s,color .15s,background .15s}
.btn-icon:hover{border-color:var(--accent);color:var(--accent);background:rgba(34,211,238,.1)}
body.light .btn-icon:hover{background:rgba(8,145,178,.08)}
.back-link{display:inline-flex;align-items:center;gap:6px;padding:8px 12px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:500;text-decoration:none;cursor:pointer;font-family:inherit}
.back-link:hover{border-color:var(--accent);color:var(--accent)}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px 24px}
.card h1{font-size:20px;font-weight:800;margin:0 0 6px}
.card .sub{font-size:13px;color:var(--muted);margin-bottom:24px}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.field input{width:100%;padding:11px 14px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;font-family:inherit;outline:none}
.field input:focus{border-color:var(--accent)}
hr{border:none;border-top:1px solid var(--border);margin:22px 0}
.btn-save{background:var(--accent);color:#0a0e17;border:none;border-radius:10px;padding:12px 22px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit;margin-top:4px}
.btn-save:hover{filter:brightness(1.06)}
.btn-save:disabled{opacity:.6;cursor:not-allowed}
.meta{font-size:11px;color:var(--muted);margin-top:16px;line-height:1.6}
.toast{position:fixed;bottom:22px;right:22px;z-index:9999;padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 10px 36px rgba(0,0,0,.4);border:1px solid var(--border);animation:toast-in .2s ease}
.toast.ok{background:rgba(52,211,153,.15);color:var(--ok)}
.toast.err{background:rgba(248,113,113,.15);color:var(--danger)}
@keyframes toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.loading{color:var(--muted);font-size:14px;padding:40px 0;text-align:center}
.role-pill{display:inline-block;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--accent);background:rgba(34,211,238,.12);padding:4px 10px;border-radius:999px;margin-bottom:16px}
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
      <button type="button" class="btn-icon" id="btn-theme" title="Thème" aria-label="Thème">🌙</button>
      <button type="button" class="btn-icon" id="btn-logout" title="Déconnexion" aria-label="Déconnexion">⎋</button>
    </div>
  </div>
  <div id="root"><div class="loading">Chargement…</div></div>
</div>
<script src="/static/support_widget.js"></script>
<script>
const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',superadmin:'Super admin'};
let ME=null;

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

function field(label,id,type,val){
  return `<div class="field"><label for="${id}">${label}</label><input id="${id}" type="${type||'text'}" value="${esc(val)}"></div>`;
}

function esc(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
}

function renderForm(){
  const u=ME||{};
  const role=ROLE_LABELS[u.role]||u.role||'';
  document.getElementById('root').innerHTML=`
    <div class="card">
      <div class="role-pill">${esc(role)}</div>
      <h1>Mon profil</h1>
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
  document.getElementById('btn-save').onclick=saveProfil;
}

async function saveProfil(){
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
  if(pwd){
    body.password=pwd;
    body.password_confirm=pwd2;
    body.current_password=cur;
  }
  try{
    await api('/api/auth/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    ME=await api('/api/auth/me');
    toast('Profil mis à jour',true);
    renderForm();
  }catch(e){
    toast(e.message||'Enregistrement impossible',false);
  }finally{
    if(btn)btn.disabled=false;
  }
}

function applyTheme(){
  const light=localStorage.getItem('theme')==='light';
  document.body.classList.toggle('light',light);
  document.getElementById('btn-theme').textContent=light?'☀':'🌙';
}

document.getElementById('btn-theme').onclick=()=>{
  const light=!document.body.classList.contains('light');
  localStorage.setItem('theme',light?'light':'dark');
  applyTheme();
};

document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

(async function init(){
  applyTheme();
  try{
    ME=await api('/api/auth/me');
    renderForm();
  }catch(e){
    if(e.message!=='auth'){
      document.getElementById('root').innerHTML='<div class="card"><p class="sub">Impossible de charger le profil.</p></div>';
    }
  }
})();
</script>
</body>
</html>
"""
