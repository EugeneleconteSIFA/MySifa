"""MySifa — Coffre RH (vue salarié).

Route : /coffre — tout utilisateur authentifié voit ses propres bulletins,
contrats, attestations et gère ses notes de frais.

Utilise le shell MySifa standard (sidebar + topbar mobile + MySifaTheme +
MySifaUserChip) pour rester cohérent avec /profil, /paie, etc.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/coffre", response_class=HTMLResponse)
def coffre_page(request: Request):
    try:
        _ = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/coffre", status_code=302)
        raise
    return HTMLResponse(content=COFFRE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


COFFRE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Mon coffre RH — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--danger:#dc2626;--warn:#d97706}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:0 8px;margin-bottom:28px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(34,211,238,.25),0 0 18px rgba(34,211,238,.15)}
body.palette-ambre .nav-btn:hover:not(.active),body.palette-forge .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 16px rgba(240,165,0,.14)}
body.palette-pivoine .nav-btn:hover:not(.active),body.palette-cocon .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,56,136,.28),0 0 16px rgba(240,56,136,.14)}
body.palette-foret .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(61,214,126,.28),0 0 16px rgba(61,214,126,.14)}
body.palette-cendre .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(100,150,200,.28),0 0 16px rgba(100,150,200,.14)}
body.palette-braise .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(240,112,48,.28),0 0 16px rgba(240,112,48,.14)}
body.light .nav-btn:hover:not(.active){box-shadow:0 0 0 1px rgba(8,145,178,.32),0 0 16px rgba(8,145,178,.12)}
.nav-badge{margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--warn);color:#0a0e17;font-size:10px;font-weight:700;line-height:1.5}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 20px rgba(34,211,238,.14)}
body.palette-ambre .theme-btn:hover,body.palette-forge .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 18px rgba(240,165,0,.14)}
body.palette-pivoine .theme-btn:hover,body.palette-cocon .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,56,136,.24),0 0 18px rgba(240,56,136,.12)}
body.palette-foret .theme-btn:hover{box-shadow:0 0 0 1px rgba(61,214,126,.24),0 0 18px rgba(61,214,126,.12)}
body.palette-cendre .theme-btn:hover{box-shadow:0 0 0 1px rgba(100,150,200,.24),0 0 18px rgba(100,150,200,.12)}
body.palette-braise .theme-btn:hover{box-shadow:0 0 0 1px rgba(240,112,48,.24),0 0 18px rgba(240,112,48,.12)}
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{display:inline-flex;align-items:center;line-height:1}
.theme-btn .theme-label{white-space:nowrap}
@media (display-mode:standalone),(max-width:900px){.theme-btn .theme-label{display:none}.theme-btn{justify-content:center}}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}

.main{flex:1;padding:28px;overflow:auto}
.container{max-width:1000px;margin:0 auto}
h1{font-size:22px;font-weight:700;margin:0 0 4px}
.subtitle{font-size:13px;color:var(--muted);margin-bottom:22px}

.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media (max-width:900px){
  body.has-topbar .main{padding-top:74px}
  .main{padding:18px}
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
}

.pane-tab{display:none}
.pane-tab.active{display:block}

.info-banner{background:var(--accent-bg);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:12px 16px;font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:18px}

.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:16px}
.card h2{margin:0 0 14px;font-size:15px;font-weight:700}
.year-group{margin-bottom:20px}
.year-title{font-size:13px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.doc-list{display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(230px,1fr))}
.doc-item{display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;transition:all .15s;cursor:pointer;text-decoration:none;color:inherit}
.doc-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.doc-icon{width:32px;height:32px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--accent-bg);color:var(--accent);border-radius:8px}
.doc-info{flex:1;min-width:0}
.doc-title{font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.doc-meta{font-size:11px;color:var(--muted);margin-top:2px}
.empty{text-align:center;padding:40px 20px;color:var(--muted);font-size:13px}
.btn{padding:10px 18px;border-radius:10px;border:none;background:var(--accent);color:#0a0e17;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:8px}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:var(--danger);color:#fff}
.btn.small{padding:6px 10px;font-size:11px;border-radius:7px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}
td{padding:12px;border-bottom:1px solid var(--border);color:var(--text2)}
tr:hover td{background:var(--accent-bg)}
.statut{display:inline-block;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.statut.brouillon{background:rgba(148,163,184,.15);color:var(--muted)}
.statut.soumise{background:rgba(251,191,36,.15);color:var(--warn)}
.statut.validee{background:rgba(34,211,238,.15);color:var(--accent)}
.statut.payee{background:rgba(52,211,153,.15);color:var(--ok)}
.statut.refusee{background:rgba(248,113,113,.15);color:var(--danger)}
.montant{font-family:'SF Mono','Consolas',monospace;font-weight:700;color:var(--text)}
.filters{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.filters select{padding:7px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text2);font-size:12px;font-family:inherit;outline:none}
.filters select:focus{border-color:var(--accent)}

.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:400;display:flex;align-items:center;justify-content:center;padding:16px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px;max-width:480px;width:100%;max-height:90vh;overflow:auto}
.modal h3{margin:0 0 16px;font-size:16px;font-weight:700}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.field textarea{min-height:70px;resize:vertical}
.file-drop{border:1.5px dashed var(--border);border-radius:8px;padding:16px;text-align:center;font-size:12px;color:var(--muted);cursor:pointer;transition:all .15s}
.file-drop:hover{border-color:var(--accent);color:var(--accent)}
.file-drop.has-file{border-style:solid;color:var(--text2);background:var(--bg)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}
.toast{position:fixed;top:24px;right:24px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 18px;font-size:13px;color:var(--text);z-index:1000;box-shadow:0 10px 24px rgba(0,0,0,.3);animation:slideIn .2s}
.toast.err{border-left-color:var(--danger)}
.toast.ok{border-left-color:var(--ok)}
@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:translateX(0);opacity:1}}

@media(max-width:640px){.container{max-width:100%}.row2{grid-template-columns:1fr}table{font-size:12px}th,td{padding:8px}.doc-list{grid-template-columns:1fr}}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="closeSidebar()"></div>

<div class="layout">
  <aside class="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Mon coffre RH</div>
    </div>

    <button type="button" class="nav-btn active" id="nav-bulletins" onclick="showTab('bulletins')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      Mes bulletins
    </button>
    <button type="button" class="nav-btn" id="nav-documents" onclick="showTab('documents')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      Autres documents
    </button>
    <button type="button" class="nav-btn" id="nav-ndf" onclick="showTab('ndf')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
      Notes de frais
      <span class="nav-badge" id="ndf-badge" style="display:none">0</span>
    </button>

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
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Coffre RH · __V_LABEL__</div>
    </div>
  </aside>

  <main class="main">
    <div class="container">

      <div class="mobile-topbar">
        <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div>
          <div class="mobile-topbar-title">Mon coffre</div>
          <div class="mobile-topbar-sub" id="mobile-sub">Mes bulletins</div>
        </div>
        <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
        </button>
      </div>

      <h1 id="page-title">Mes bulletins</h1>
      <p class="subtitle" id="page-sub">Bulletins de paie mis à disposition par la comptabilité.</p>

      <div class="info-banner">
        Coffre interne SIFA — le bulletin officiel reste celui remis en main propre par la comptabilité.
      </div>

      <div class="pane-tab active" id="pane-bulletins">
        <div class="card">
          <div class="filters">
            <label style="font-size:12px;color:var(--muted)">Année :</label>
            <select id="filter-bul-annee"><option value="">Toutes</option></select>
          </div>
          <div id="bul-container"><div class="empty">Chargement…</div></div>
        </div>
      </div>

      <div class="pane-tab" id="pane-documents">
        <div class="card">
          <h2>Contrats, attestations et autres documents</h2>
          <div id="doc-container"><div class="empty">Chargement…</div></div>
        </div>
      </div>

      <div class="pane-tab" id="pane-ndf">
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:10px">
            <h2 style="margin:0">Mes notes de frais</h2>
            <button type="button" class="btn" onclick="openNdfModal()">+ Nouvelle note</button>
          </div>
          <div id="ndf-container"><div class="empty">Chargement…</div></div>
        </div>
      </div>

    </div>
  </main>
</div>

<script src="/static/support_widget.js"></script>
<script>window.__MYSIFA_APP__='coffre';</script>
<script>
const ROLE_LABELS={direction:'Direction',administration:'Administration',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial',superadmin:'Super admin'};
const DOC_TYPE_LABELS={bulletin_paie:'Bulletin de paie',contrat:'Contrat',attestation:'Attestation',autre:'Autre'};
const MOIS_LABELS=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];
const ICO_MOON=`<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
const ICO_SUN=`<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;

let ME=null;let CURRENT_TAB='bulletins';let bulData={documents:[],annees_disponibles:[]};

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtMontant(n){return (Number(n)||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' €';}
function fmtDate(s){if(!s)return '';const d=new Date(s.substr(0,10));return isNaN(d)?s:d.toLocaleDateString('fr-FR');}
function toast(msg,type){const t=document.createElement('div');t.className='toast '+(type==='err'?'err':'ok');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3500);}
async function api(url,opts){opts=opts||{};opts.credentials='include';const r=await fetch(url,opts);if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}return r.json();}

function getPrefs(){return window.MySifaTheme?MySifaTheme.loadPrefs():{palette:'mysifa',style:'defaut',mode:'dark',bgAnim:true};}
function syncThemeBtn(){
  const isLight=getPrefs().mode==='light';
  const ico=document.getElementById('theme-ico');
  const lbl=document.getElementById('theme-label');
  if(ico)ico.innerHTML=isLight?ICO_SUN:ICO_MOON;
  if(lbl)lbl.textContent=isLight?'Mode sombre':'Mode clair';
}

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const TAB_META={
  bulletins:{title:'Mes bulletins',sub:'Bulletins de paie mis à disposition par la comptabilité.'},
  documents:{title:'Autres documents',sub:'Contrats, attestations et autres pièces RH.'},
  ndf:{title:'Notes de frais',sub:'Dépôt de justificatifs et suivi des remboursements.'},
};
function showTab(tab){
  CURRENT_TAB=tab;
  ['bulletins','documents','ndf'].forEach(id=>{
    const pane=document.getElementById('pane-'+id);
    const nav=document.getElementById('nav-'+id);
    if(pane)pane.classList.toggle('active',id===tab);
    if(nav)nav.classList.toggle('active',id===tab);
  });
  const meta=TAB_META[tab]||TAB_META.bulletins;
  const t=document.getElementById('page-title');if(t)t.textContent=meta.title;
  const s=document.getElementById('page-sub');if(s)s.textContent=meta.sub;
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=meta.title;
  closeSidebar();
}

function updateUserChip(){
  if(!ME)return;
  const chip=document.querySelector('.user-chip');
  if(chip&&window.MySifaUserChip){MySifaUserChip.fill(chip,ME,{roleLabels:ROLE_LABELS,showProfil:false});return;}
  const n=document.getElementById('uc-name');if(n)n.textContent=ME.nom||'—';
  const r=document.getElementById('uc-role');if(r)r.textContent=ROLE_LABELS[ME.role]||ME.role||'—';
}

async function loadBulletins(){
  const annee=document.getElementById('filter-bul-annee').value;
  try{
    const url='/api/coffre/documents?type=bulletin_paie'+(annee?'&annee='+annee:'');
    bulData=await api(url);
    if(!annee){
      const sel=document.getElementById('filter-bul-annee');
      sel.innerHTML='<option value="">Toutes</option>'+bulData.annees_disponibles.map(a=>`<option value="${a}">${a}</option>`).join('');
    }
    renderBulletins();
  }catch(e){document.getElementById('bul-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}
function renderBulletins(){
  const c=document.getElementById('bul-container');
  if(!bulData.documents.length){c.innerHTML='<div class="empty">Aucun bulletin disponible pour l\'instant.</div>';return;}
  const byYear={};
  bulData.documents.forEach(d=>{const y=d.annee||'—';(byYear[y]=byYear[y]||[]).push(d);});
  c.innerHTML=Object.keys(byYear).sort((a,b)=>String(b).localeCompare(String(a))).map(y=>`
    <div class="year-group">
      <div class="year-title">${esc(y)}</div>
      <div class="doc-list">
        ${byYear[y].map(d=>`
          <a class="doc-item" href="/api/coffre/documents/${d.id}/download" target="_blank" rel="noopener">
            <div class="doc-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            </div>
            <div class="doc-info">
              <div class="doc-title">${esc(MOIS_LABELS[d.mois]||d.libelle||'Bulletin')} ${esc(d.annee||'')}</div>
              <div class="doc-meta">${d.consulte_at?'Consulté':'Non consulté'} · ${Math.round((d.taille_bytes||0)/1024)} Ko</div>
            </div>
          </a>
        `).join('')}
      </div>
    </div>
  `).join('');
}
document.getElementById('filter-bul-annee').addEventListener('change',loadBulletins);

async function loadDocs(){
  try{
    const j=await api('/api/coffre/documents');
    const docs=j.documents.filter(d=>d.type!=='bulletin_paie');
    const c=document.getElementById('doc-container');
    if(!docs.length){c.innerHTML='<div class="empty">Aucun autre document.</div>';return;}
    c.innerHTML='<div class="doc-list">'+docs.map(d=>`
      <a class="doc-item" href="/api/coffre/documents/${d.id}/download" target="_blank" rel="noopener">
        <div class="doc-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="doc-info">
          <div class="doc-title">${esc(d.libelle||DOC_TYPE_LABELS[d.type]||d.type)}</div>
          <div class="doc-meta">${esc(DOC_TYPE_LABELS[d.type]||d.type)} · ${esc(fmtDate(d.uploaded_at))}</div>
        </div>
      </a>
    `).join('')+'</div>';
  }catch(e){document.getElementById('doc-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}

async function loadNdf(){
  try{
    const j=await api('/api/coffre/notes-frais');
    const c=document.getElementById('ndf-container');
    const badge=document.getElementById('ndf-badge');
    const pending=j.notes.filter(n=>n.statut==='brouillon'||n.statut==='soumise').length;
    if(badge){if(pending>0){badge.style.display='';badge.textContent=String(pending);}else{badge.style.display='none';}}
    if(!j.notes.length){c.innerHTML='<div class="empty">Aucune note de frais. Cliquez sur « Nouvelle note » pour en créer une.</div>';return;}
    c.innerHTML=`<div style="overflow-x:auto"><table>
      <thead><tr><th>Date</th><th>Catégorie</th><th>Description</th><th style="text-align:right">Montant</th><th>Statut</th><th></th></tr></thead>
      <tbody>${j.notes.map(n=>`
        <tr>
          <td>${esc(fmtDate(n.date_frais))}</td>
          <td>${esc(n.categorie||'—')}</td>
          <td style="max-width:280px">${esc((n.description||'').slice(0,80))}${(n.description||'').length>80?'…':''}${n.motif_refus?'<div style="font-size:11px;color:var(--danger);margin-top:3px">Refus : '+esc(n.motif_refus)+'</div>':''}</td>
          <td style="text-align:right" class="montant">${fmtMontant(n.montant_ttc)}</td>
          <td><span class="statut ${esc(n.statut)}">${esc(n.statut)}</span></td>
          <td style="text-align:right;white-space:nowrap">
            ${n.justificatif_nom?`<a class="btn ghost small" href="/api/coffre/notes-frais/${n.id}/justificatif" target="_blank" rel="noopener">Voir</a>`:''}
            ${n.statut==='brouillon'?`
              <button class="btn small" onclick="submitNdf(${n.id})">Soumettre</button>
              <button class="btn ghost small" onclick="deleteNdf(${n.id})">×</button>
            `:''}
          </td>
        </tr>
      `).join('')}</tbody>
    </table></div>`;
  }catch(e){document.getElementById('ndf-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}
async function submitNdf(id){
  if(!confirm('Soumettre cette note de frais à la comptabilité ?\nUne fois soumise, elle ne pourra plus être modifiée.'))return;
  try{await api('/api/coffre/notes-frais/'+id+'/soumettre',{method:'POST'});toast('Note soumise');loadNdf();}catch(e){toast(e.message,'err');}
}
async function deleteNdf(id){
  if(!confirm('Supprimer ce brouillon ?'))return;
  try{await api('/api/coffre/notes-frais/'+id,{method:'DELETE'});toast('Brouillon supprimé');loadNdf();}catch(e){toast(e.message,'err');}
}

function openNdfModal(){
  const back=document.createElement('div');back.className='modal-back';
  const today=new Date().toISOString().slice(0,10);
  back.innerHTML=`<div class="modal">
    <h3>Nouvelle note de frais</h3>
    <form id="ndf-form">
      <div class="row2">
        <div class="field"><label>Date du frais</label><input type="date" name="date_frais" value="${today}" required></div>
        <div class="field"><label>Montant TTC (€)</label><input type="number" step="0.01" min="0.01" name="montant_ttc" required placeholder="0,00"></div>
      </div>
      <div class="row2">
        <div class="field"><label>Catégorie</label><input type="text" name="categorie" placeholder="ex. Repas client, train Paris…" maxlength="80"></div>
        <div class="field"><label>TVA (optionnel)</label><input type="number" step="0.01" min="0" name="montant_tva" placeholder="0,00"></div>
      </div>
      <div class="field"><label>Description</label><textarea name="description" placeholder="Détails, contexte, participants…" maxlength="1000"></textarea></div>
      <div class="field">
        <label>Justificatif (PDF, JPG, PNG — 10 Mo max)</label>
        <label class="file-drop" id="drop-label">
          <span id="drop-txt">Choisir un fichier ou glisser-déposer</span>
          <input type="file" name="justificatif" id="ndf-file" accept="application/pdf,image/*" style="display:none">
        </label>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" id="ndf-cancel">Annuler</button>
        <button type="submit" class="btn ghost" name="soumettre" value="0">Enregistrer brouillon</button>
        <button type="submit" class="btn" name="soumettre" value="1">Soumettre à la compta</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(back);
  const fileEl=back.querySelector('#ndf-file');
  const dropLbl=back.querySelector('#drop-label');
  const dropTxt=back.querySelector('#drop-txt');
  fileEl.addEventListener('change',()=>{
    if(fileEl.files.length){dropLbl.classList.add('has-file');dropTxt.textContent=fileEl.files[0].name;}
    else{dropLbl.classList.remove('has-file');dropTxt.textContent='Choisir un fichier ou glisser-déposer';}
  });
  back.querySelector('#ndf-cancel').onclick=()=>back.remove();
  back.onclick=(e)=>{if(e.target===back)back.remove();};
  const form=back.querySelector('#ndf-form');
  form.addEventListener('submit',async(e)=>{
    e.preventDefault();
    const btn=e.submitter;
    const fd=new FormData(form);
    fd.set('soumettre',btn && btn.value==='1'?'1':'0');
    try{
      const r=await fetch('/api/coffre/notes-frais',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      toast(btn.value==='1'?'Note soumise':'Brouillon enregistré');
      back.remove();
      loadNdf();
    }catch(e){toast(e.message,'err');}
  });
}

document.getElementById('btn-theme').onclick=()=>{
  if(window.MySifaTheme)MySifaTheme.toggleMode();
  syncThemeBtn();
};
document.getElementById('btn-logout').onclick=async()=>{
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
};

(async function init(){
  syncThemeBtn();
  try{
    ME=await api('/api/auth/me');
    if(ME&&window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    syncThemeBtn();
    updateUserChip();
  }catch(e){}
  loadBulletins();
  loadDocs();
  loadNdf();
  const tabParam=new URLSearchParams(location.search).get('tab');
  if(tabParam && TAB_META[tabParam])showTab(tabParam);
})();
</script>
</body>
</html>
"""
