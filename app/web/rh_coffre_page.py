"""MySifa — Coffre RH (vue comptabilité).

Route : /rh/coffre — réservée aux rôles comptabilité et superadmin.
Dashboard mensuel des bulletins, upload ZIP, impression, validation NDF.

Shell MySifa standard : sidebar + topbar mobile + MySifaTheme + MySifaUserChip.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLE_COMPTABILITE, ROLE_SUPERADMIN
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/rh/coffre", response_class=HTMLResponse)
def rh_coffre_page(request: Request):
    try:
        u = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/rh/coffre", status_code=302)
        raise
    if u.get("role") not in {ROLE_COMPTABILITE, ROLE_SUPERADMIN}:
        return RedirectResponse(url="/coffre", status_code=302)
    return HTMLResponse(content=RH_COFFRE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


RH_COFFRE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Coffre RH — Comptabilité — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css?v=__V_LABEL__">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_sidebar.css?v=__V_LABEL__">
<style>
/* tokens : static/mysifa_theme.css — ici, seulement les écarts */
:root{--ok:#34d399;}
body.light{--muted:#64748b;--ok:#059669;}
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
.nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px color-mix(in srgb,var(--accent,#22d3ee) 25%,transparent),0 0 18px color-mix(in srgb,var(--accent,#22d3ee) 15%,transparent)}
body.palette-ambre .nav-btn:hover:not(.active):not(.back-mysifa),body.palette-forge .nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px rgba(240,165,0,.28),0 0 16px rgba(240,165,0,.14)}
body.palette-pivoine .nav-btn:hover:not(.active):not(.back-mysifa),body.palette-cocon .nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px rgba(240,56,136,.28),0 0 16px rgba(240,56,136,.14)}
body.palette-foret .nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px rgba(61,214,126,.28),0 0 16px rgba(61,214,126,.14)}
body.palette-cendre .nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px rgba(100,150,200,.28),0 0 16px rgba(100,150,200,.14)}
body.palette-braise .nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px rgba(240,112,48,.28),0 0 16px rgba(240,112,48,.14)}
body.light .nav-btn:hover:not(.active):not(.back-mysifa){box-shadow:0 0 0 1px color-mix(in srgb,var(--accent,#0891b2) 32%,transparent),0 0 16px color-mix(in srgb,var(--accent,#0891b2) 12%,transparent)}
.nav-badge{margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--accent);color:white;font-size:10px;font-weight:700;line-height:1.5}
/* Pied de sidebar : static/mysifa_sidebar.css (v3.3.0). La sidebar a ici 12px de marge
   latérale : le pied la déborde pour que son filet aille d'un bord à l'autre, comme sur MyStock. */
.sidebar>.msb-footer{margin-left:-12px;margin-right:-12px;padding-left:12px;padding-right:12px}

.main{flex:1;padding:28px;overflow:auto}
.container{max-width:1280px;margin:0 auto}
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

.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:16px}
.card h2{margin:0 0 14px;font-size:15px;font-weight:700}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
.toolbar select,.toolbar input{padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.toolbar select:focus,.toolbar input:focus{border-color:var(--accent)}
.btn{padding:9px 16px;border-radius:10px;border:none;background:var(--accent);color:white;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:6px}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:var(--danger);color:#fff}
.btn.ok{background:var(--ok);color:#0a0e17}
.btn.small{padding:5px 10px;font-size:11px;border-radius:7px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:1}
td{padding:10px 12px;border-bottom:1px solid var(--border);color:var(--text2)}
tr:hover td{background:var(--accent-bg)}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.b-manquant{background:rgba(148,163,184,.15);color:var(--muted)}
.b-depose{background:rgba(251,191,36,.15);color:var(--warn)}
.b-distribue{background:color-mix(in srgb,var(--accent,#22d3ee) 15%,transparent);color:var(--accent)}
.b-consulte{background:rgba(52,211,153,.15);color:var(--ok)}
tr.ndf-row{cursor:pointer}
.statut{display:inline-block;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;border:1px solid transparent}
.statut.brouillon{background:transparent;border:1px dashed var(--border);color:var(--muted)}
.statut.soumise{background:var(--accent-bg);border-color:color-mix(in srgb,var(--accent) 45%,transparent);color:var(--accent)}
.statut.validee{background:color-mix(in srgb,var(--success) 14%,transparent);border-color:color-mix(in srgb,var(--success) 40%,transparent);color:var(--success)}
.statut.payee{background:var(--success);color:white}
.statut.refusee{background:color-mix(in srgb,var(--danger) 12%,transparent);border-color:color-mix(in srgb,var(--danger) 40%,transparent);color:var(--danger)}
.montant{font-family:'SF Mono','Consolas',monospace;font-weight:700;color:var(--text);text-align:right}
.upload-zone{border:2px dashed var(--border);border-radius:12px;padding:24px;text-align:center;transition:all .15s;cursor:pointer;background:var(--bg);display:block}
.upload-zone:hover,.upload-zone.dragover{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.upload-zone .u-icon{font-size:32px;margin-bottom:8px;color:var(--accent)}
.upload-zone .u-hint{font-size:11px;color:var(--muted);margin-top:6px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.stat{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.stat-val{font-size:22px;font-weight:800;color:var(--text);margin-top:4px}
.stat.warn .stat-val{color:var(--warn)}
.stat.ok .stat-val{color:var(--ok)}
.stat.danger .stat-val{color:var(--danger)}
.upload-result{margin-top:14px;padding:14px;border-radius:10px;background:var(--bg);border:1px solid var(--border);font-size:12px;max-height:280px;overflow:auto}
.upload-result h4{margin:0 0 8px;font-size:12px;font-weight:700;color:var(--text)}
.upload-result ul{margin:0 0 12px;padding-left:20px}
.upload-result li{margin-bottom:3px;color:var(--text2)}
.actions-row{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px}
.actions-row h2{margin:0}

.preview-back{position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:500;display:flex;align-items:center;justify-content:center;padding:2.5vh 2vw;backdrop-filter:blur(4px)}
.preview-modal{width:100%;height:100%;max-width:1400px;background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.6)}
.preview-header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;background:var(--card);border-bottom:1px solid var(--border);gap:12px;flex-shrink:0}
.preview-title{font-size:13px;font-weight:600;color:var(--text);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.preview-actions{display:flex;gap:8px;flex-shrink:0;align-items:center}
.preview-body{flex:1;overflow:auto;display:flex;align-items:center;justify-content:center;padding:16px;background:var(--bg)}
.preview-body iframe{width:100%;height:100%;border:none;background:#fff;border-radius:8px}
.preview-body img{max-width:100%;max-height:100%;object-fit:contain;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.5)}
.preview-body .preview-unknown{color:var(--muted);font-size:13px;text-align:center;padding:30px}
@media(max-width:640px){.preview-back{padding:0}.preview-modal{border-radius:0;max-width:none;border:none}.preview-header{padding:10px 12px}.preview-title{font-size:12px}.preview-body{padding:8px}}
.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:400;display:flex;align-items:center;justify-content:center;padding:16px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px;max-width:520px;width:100%;max-height:90vh;overflow:auto}
.modal h3{margin:0 0 16px;font-size:16px;font-weight:700}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px}
.toast{position:fixed;top:24px;right:24px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 18px;font-size:13px;color:var(--text);z-index:1000;box-shadow:0 10px 24px rgba(0,0,0,.3)}
.toast.err{border-left-color:var(--danger)}
.toast.ok{border-left-color:var(--ok)}
@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:translateX(0);opacity:1}}
@media(max-width:768px){table{font-size:12px}th,td{padding:6px 8px}.row2{grid-template-columns:1fr}}
</style>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<script src="/static/mysifa_sidebar.js?v=__V_LABEL__"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="closeSidebar()"></div>

<div class="layout">
  <aside class="sidebar msb-nav">
    <div class="logo">
      <div class="logo-brand">My<span>Sifa</span></div>
      <div class="logo-sub">Coffre RH · Compta</div>
    </div>

    <button type="button" class="nav-btn active" id="nav-bulletins" onclick="showTab('bulletins')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      Bulletins
    </button>
    <button type="button" class="nav-btn" id="nav-ndf" onclick="showTab('ndf')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
      Notes de frais
      <span class="nav-badge" id="ndf-badge" style="display:none">0</span>
    </button>
    <button type="button" class="nav-btn" onclick="location.href='/coffre'">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
      Mon coffre
    </button>

    <!-- Pied commun (static/mysifa_sidebar.js), rempli au chargement. -->
    <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="Coffre RH" data-msb-version="__V_LABEL__"></div>
  </aside>

  <main class="main">
    <div class="container">

      <div class="mobile-topbar">
        <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div>
          <div class="mobile-topbar-title">Coffre RH</div>
          <div class="mobile-topbar-sub" id="mobile-sub">Bulletins</div>
        </div>
        <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
        </button>
      </div>

      <h1 id="page-title">Bulletins</h1>
      <p class="subtitle" id="page-sub">Dépôt mensuel, dashboard et impression groupée.</p>

      <div class="pane-tab active" id="pane-bulletins">
        <div class="card">
          <h2>Upload des bulletins mensuels</h2>
          <div class="toolbar">
            <label style="font-size:12px;color:var(--muted)">Année :</label>
            <select id="upl-annee"></select>
            <label style="font-size:12px;color:var(--muted)">Mois :</label>
            <select id="upl-mois"></select>
          </div>
          <label for="zip-file" class="upload-zone" id="zip-drop">
            <div class="u-icon">↑</div>
            <div><strong>Déposer un ZIP</strong> ou cliquer pour choisir</div>
            <div class="u-hint">Fichiers attendus : <code>Bulletin_YYYY_MM_NOM_Prenom.pdf</code></div>
          </label>
          <input type="file" id="zip-file" accept=".zip" style="display:none">
          <div id="upl-result"></div>
        </div>

        <div class="card">
          <div class="actions-row">
            <h2>Dashboard mensuel</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button type="button" class="btn ghost" onclick="openSingleUpload()">Upload individuel</button>
              <button type="button" class="btn ok" onclick="printAll(true)">Imprimer + marquer distribués</button>
              <button type="button" class="btn" onclick="printAll(false)">Imprimer tout</button>
            </div>
          </div>
          <div class="stats" id="dash-stats"></div>
          <div style="overflow-x:auto"><div id="dash-container"></div></div>
        </div>
      </div>

      <div class="pane-tab" id="pane-ndf">
        <div class="card" id="ndf-bloc" data-bloc="rh-coffre.ndf">
          <div class="toolbar" data-bloc-entete>
            <label style="font-size:12px;color:var(--muted)">Statut :</label>
            <select id="ndf-statut">
              <option value="">Tous</option>
              <option value="soumise" selected>Soumises (à traiter)</option>
              <option value="validee">Validées</option>
              <option value="payee">Payées</option>
              <option value="refusee">Refusées</option>
              <option value="brouillon">Brouillons</option>
            </select>
            <label style="font-size:12px;color:var(--muted)">Année :</label>
            <select id="ndf-annee"><option value="">Toutes</option></select>
            <button type="button" class="btn ghost" onclick="exportNdf()">Export CSV</button>
            <button type="button" class="btn ghost" onclick="ouvrirReglagesRh()">Réglages</button>
          </div>
          <div style="overflow-x:auto" id="ndf-container"></div>
        </div>
      </div>


    </div>
  </main>
</div>

<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_ndf_reglages.js?v=4"></script>
<script src="/static/mysifa_confirm.js?v=2"></script>
<script src="/static/mysifa_ndf_fiche.js?v=3"></script>
<script src="/static/mysifa_url.js?v=5"></script>
<script src="/static/rh_coffre_url.js?v=1"></script>
<script>window.__MYSIFA_APP__='rh_coffre';</script>
<script>
const MOIS_LABELS=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

let ME=null;let CURRENT_TAB='bulletins';
// Liste affichée et fenêtres ouvertes, lues par static/rh_coffre_url.js.
let NDF_RH=[];let NDF_OUVERTE=null;let APERCU=null;
const now=new Date();const curYear=now.getFullYear();const curMonth=now.getMonth()+1;

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtMontant(n){return (Number(n)||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' €';}
function fmtDate(s){if(!s)return '';const d=new Date(s.substr(0,10));return isNaN(d)?s:d.toLocaleDateString('fr-FR');}
function toast(msg,type){const t=document.createElement('div');t.className='toast '+(type==='err'?'err':'ok');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3500);}
async function api(url,opts){opts=opts||{};opts.credentials='include';const r=await fetch(url,opts);if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}return r.json();}

// ── Prévisualisation documents (PDF / image) ──
const PREVIEW_IMG_RE=/\.(png|jpe?g|gif|webp|heic|bmp|svg)$/i;
function previewDocument(url, filename){
  const back=document.createElement('div');
  back.className='preview-back';
  const isImg=PREVIEW_IMG_RE.test(filename||'');
  const sep=url.indexOf('?')>=0?'&':'?';
  const inlineUrl=url+sep+'inline=1';
  const safeName=esc(filename||'Document');
  const safeUrl=esc(url);
  const safeInline=esc(inlineUrl);
  back.innerHTML=`
    <div class="preview-modal">
      <div class="preview-header">
        <div class="preview-title">${safeName}</div>
        <div class="preview-actions">
          <a class="btn ghost small" href="${safeUrl}" target="_blank" rel="noopener">Télécharger</a>
          <button type="button" class="btn ghost small" id="preview-close">Fermer</button>
        </div>
      </div>
      <div class="preview-body">
        ${isImg
          ? `<img src="${safeInline}" alt="${safeName}">`
          : `<iframe src="${safeInline}" title="Aperçu"></iframe>`}
      </div>
    </div>`;
  document.body.appendChild(back);
  if(APERCU)APERCU.fermer(true);
  const close=(technique)=>{
    back.remove();document.removeEventListener('keydown',onKey,true);
    if(APERCU&&APERCU.el===back){APERCU=null;if(technique!==true)rhCoffreSyncUrl();}
  };
  const onKey=(e)=>{if(e.key==='Escape'){e.stopImmediatePropagation();close();}};
  document.addEventListener('keydown',onKey,true);
  back.querySelector('#preview-close').onclick=()=>close();
  back.addEventListener('click',(e)=>{if(e.target===back)close();});
  APERCU={url,el:back,fermer:close};
  rhCoffreSyncUrl();
}
document.addEventListener('click',(e)=>{
  const el=e.target.closest('[data-preview-url]');
  if(!el)return;
  e.preventDefault();
  previewDocument(el.dataset.previewUrl, el.dataset.previewName||'');
});

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const TAB_META={
  bulletins:{title:'Bulletins',sub:'Dépôt mensuel, dashboard et impression groupée.'},
  ndf:{title:'Notes de frais',sub:'Validation, marquage payées et export comptable.'},
};
var RH_COFFRE_VALID_TABS=['bulletins','ndf'];
function showTab(tab, opts){
  var silent=!!(opts&&opts.silent);
  CURRENT_TAB=tab;
  RH_COFFRE_VALID_TABS.forEach(id=>{
    const pane=document.getElementById('pane-'+id);
    const nav=document.getElementById('nav-'+id);
    if(pane)pane.classList.toggle('active',id===tab);
    if(nav)nav.classList.toggle('active',id===tab);
  });
  const meta=TAB_META[tab]||TAB_META.bulletins;
  const t=document.getElementById('page-title');if(t)t.textContent=meta.title;
  const s=document.getElementById('page-sub');if(s)s.textContent=meta.sub;
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=meta.title;
  if(tab==='ndf')loadNdf();
  closeSidebar();
  rhCoffreSyncUrl();
}

{
  const sel=document.getElementById('upl-annee');
  for(let y=curYear+1;y>=curYear-5;y--){sel.innerHTML+=`<option value="${y}" ${y===curYear?'selected':''}>${y}</option>`;}
}
{
  const sel=document.getElementById('upl-mois');
  for(let m=1;m<=12;m++){sel.innerHTML+=`<option value="${m}" ${m===curMonth?'selected':''}>${String(m).padStart(2,'0')} — ${MOIS_LABELS[m]}</option>`;}
}
{
  const sel=document.getElementById('ndf-annee');
  for(let y=curYear;y>=curYear-5;y--){sel.innerHTML+=`<option value="${y}">${y}</option>`;}
}

const dropZone=document.getElementById('zip-drop');
const fileInput=document.getElementById('zip-file');
dropZone.onclick=()=>fileInput.click();
['dragenter','dragover'].forEach(ev=>dropZone.addEventListener(ev,e=>{e.preventDefault();dropZone.classList.add('dragover');}));
['dragleave','drop'].forEach(ev=>dropZone.addEventListener(ev,e=>{e.preventDefault();dropZone.classList.remove('dragover');}));
dropZone.addEventListener('drop',e=>{if(e.dataTransfer.files.length){uploadZip(e.dataTransfer.files[0]);}});
fileInput.addEventListener('change',()=>{if(fileInput.files.length)uploadZip(fileInput.files[0]);});

async function uploadZip(file){
  if(!file.name.toLowerCase().endsWith('.zip')){toast('ZIP requis','err');return;}
  const res=document.getElementById('upl-result');
  res.innerHTML='<div class="upload-result">Traitement en cours…</div>';
  const fd=new FormData();fd.append('file',file);
  try{
    const r=await fetch('/api/rh-coffre/upload-zip',{method:'POST',credentials:'include',body:fd});
    if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
    const j=await r.json();
    res.innerHTML=`<div class="upload-result">
      <h4>Résultat : ${j.total_matched} bulletin(s) importé(s)${j.total_unmatched?' — '+j.total_unmatched+' non identifié(s)':''}</h4>
      ${j.matched.length?`<h4 style="margin-top:12px">Importés</h4><ul>${j.matched.map(x=>`<li>${esc(x.fichier)} → ${esc(x.employe)}</li>`).join('')}</ul>`:''}
      ${j.unmatched.length?`<h4 style="color:var(--warn)">Non identifiés (à uploader manuellement)</h4><ul>${j.unmatched.map(x=>`<li>${esc(x.fichier)} — ${esc(x.raison)}</li>`).join('')}</ul>`:''}
      ${j.skipped.length?`<h4 style="color:var(--muted)">Ignorés</h4><ul>${j.skipped.map(x=>`<li>${esc(x.fichier)} — ${esc(x.raison)}</li>`).join('')}</ul>`:''}
    </div>`;
    toast(`${j.total_matched} bulletin(s) importé(s)`);
    loadDashboard();
  }catch(e){res.innerHTML='<div class="upload-result" style="color:var(--danger)">Erreur : '+esc(e.message)+'</div>';toast(e.message,'err');}
  fileInput.value='';
}

async function loadDashboard(){
  const annee=document.getElementById('upl-annee').value;
  const mois=document.getElementById('upl-mois').value;
  try{
    const j=await api(`/api/rh-coffre/dashboard?annee=${annee}&mois=${mois}`);
    const stats={total:j.lignes.length,depose:0,distribue:0,consulte:0,manquant:0};
    j.lignes.forEach(l=>{stats[l.statut==='déposé'?'depose':l.statut==='distribué'?'distribue':l.statut==='consulté'?'consulte':'manquant']++;});
    document.getElementById('dash-stats').innerHTML=`
      <div class="stat"><div class="stat-lbl">Salariés</div><div class="stat-val">${stats.total}</div></div>
      <div class="stat ${stats.manquant?'danger':''}"><div class="stat-lbl">Manquants</div><div class="stat-val">${stats.manquant}</div></div>
      <div class="stat warn"><div class="stat-lbl">Déposés</div><div class="stat-val">${stats.depose}</div></div>
      <div class="stat"><div class="stat-lbl">Distribués</div><div class="stat-val">${stats.distribue}</div></div>
      <div class="stat ok"><div class="stat-lbl">Consultés</div><div class="stat-val">${stats.consulte}</div></div>`;
    const c=document.getElementById('dash-container');
    if(!j.lignes.length){c.innerHTML='<p style="color:var(--muted);text-align:center;padding:30px 0">Aucun salarié actif.</p>';return;}
    c.innerHTML=`<table>
      <thead><tr><th>Salarié</th><th>Matricule</th><th>Statut</th><th>Fichier</th><th>Déposé le</th><th>Distribué le</th><th></th></tr></thead>
      <tbody>${j.lignes.map(l=>{
        const badgeClass={'manquant':'b-manquant','déposé':'b-depose','distribué':'b-distribue','consulté':'b-consulte'}[l.statut]||'b-manquant';
        return `<tr>
          <td><strong>${esc(l.nom)}</strong></td>
          <td>${esc(l.matricule||'—')}</td>
          <td><span class="badge ${badgeClass}">${esc(l.statut)}</span></td>
          <td>${l.document?esc(l.document.fichier_nom):'—'}</td>
          <td>${l.document?esc(fmtDate(l.document.uploaded_at)):'—'}</td>
          <td>${l.document && l.document.distribue_at?esc(fmtDate(l.document.distribue_at)):'—'}</td>
          <td style="text-align:right;white-space:nowrap">${l.document?`<a class="btn ghost small" href="/api/coffre/documents/${l.document.id}/download" data-preview-url="/api/coffre/documents/${l.document.id}/download" data-preview-name="${esc(l.document.fichier_nom||'Bulletin.pdf')}">Voir</a> <button class="btn ghost small" onclick="delDoc(${l.document.id})">×</button>`:''}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>`;
  }catch(e){toast(e.message,'err');}
}
document.getElementById('upl-annee').addEventListener('change',()=>{loadDashboard();rhCoffreSyncUrl();});
document.getElementById('upl-mois').addEventListener('change',()=>{loadDashboard();rhCoffreSyncUrl();});

async function delDoc(id){
  const ok=await mysifaConfirm({title:'Supprimer le document',message:'Le document est retiré du coffre du salarié.',confirmLabel:'Supprimer',danger:true});
  if(!ok)return;
  try{await api('/api/rh-coffre/documents/'+id,{method:'DELETE'});toast('Document supprimé');loadDashboard();}catch(e){toast(e.message,'err');}
}

async function printAll(mark){
  const annee=document.getElementById('upl-annee').value;
  const mois=document.getElementById('upl-mois').value;
  if(mark){
    const ok=await mysifaConfirm({title:'Imprimer et marquer distribués',message:`Tous les bulletins de ${MOIS_LABELS[+mois]} ${annee} seront imprimés et marqués comme distribués.`,confirmLabel:'Imprimer'});
    if(!ok)return;
  }
  window.open(`/api/rh-coffre/print?annee=${annee}&mois=${mois}&mark_distribue=${mark?'1':'0'}`,'_blank');
  if(mark)setTimeout(loadDashboard,1500);
}

async function openSingleUpload(){
  let employes=[];
  try{const j=await api('/api/rh-coffre/employes');employes=j.employes;}catch(e){toast(e.message,'err');return;}
  const back=document.createElement('div');back.className='modal-back';
  back.innerHTML=`<div class="modal">
    <h3>Upload individuel</h3>
    <form id="s-form">
      <div class="field"><label>Salarié</label><select name="employe_user_id" required>${employes.map(e=>`<option value="${e.id}">${esc(e.nom)}${e.matricule?' — '+esc(e.matricule):''}</option>`).join('')}</select></div>
      <div class="field"><label>Type</label><select name="type" required>
        <option value="bulletin_paie">Bulletin de paie</option>
        <option value="contrat">Contrat</option>
        <option value="attestation">Attestation</option>
        <option value="autre">Autre</option>
      </select></div>
      <div class="row2">
        <div class="field"><label>Année</label><input type="number" name="annee" min="2000" max="2100" value="${curYear}"></div>
        <div class="field"><label>Mois</label><input type="number" name="mois" min="1" max="12" value="${curMonth}"></div>
      </div>
      <div class="field"><label>Libellé (optionnel)</label><input type="text" name="libelle" placeholder="ex. Avenant contrat"></div>
      <div class="field"><label>Fichier (25 Mo max)</label><input type="file" name="fichier" required accept=".pdf,image/*"></div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" onclick="this.closest('.modal-back').remove()">Annuler</button>
        <button type="submit" class="btn">Envoyer</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(back);
  back.querySelector('#s-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const fd=new FormData(e.target);
    try{
      const r=await fetch('/api/rh-coffre/upload-single',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      toast('Document ajouté');back.remove();loadDashboard();
    }catch(e){toast(e.message,'err');}
  });
}

async function loadNdf(){
  const statut=document.getElementById('ndf-statut').value;
  const annee=document.getElementById('ndf-annee').value;
  try{
    const j=await api(`/api/rh-coffre/ndf?statut=${statut}&annee=${annee}`);
    NDF_RH=j.notes||[];
    try{
      const all=await api('/api/rh-coffre/ndf?statut=soumise');
      // Widget d'accueil (app/services/blocs_registre.py) : notes à valider,
      // même lecture dans static/mysifa_blocs_sources.js (rh-coffre.ndf).
      const bloc=document.getElementById('ndf-bloc');
      if(bloc){
        const tot=all.notes.reduce((t,n)=>t+(Number(n.montant_ttc)||0),0);
        bloc.setAttribute('data-bloc-valeur-a-valider',String(all.notes.length));
        bloc.setAttribute('data-bloc-valeur-montant',fmtMontant(tot));
        bloc.setAttribute('data-bloc-nombre-montant',String(Math.round(tot*100)/100));
      }
      const badge=document.getElementById('ndf-badge');
      if(badge){if(all.notes.length>0){badge.style.display='';badge.textContent=String(all.notes.length);}else{badge.style.display='none';}}
    }catch(e){}
    const c=document.getElementById('ndf-container');
    if(!j.notes.length){c.innerHTML='<p style="color:var(--muted);text-align:center;padding:30px 0">Aucune note de frais.</p>';return;}
    c.innerHTML=`<table>
      <thead><tr><th>Salarié</th><th>Date</th><th>Catégorie</th><th>Description</th><th style="text-align:right">Montant</th><th>Statut</th><th>Actions</th></tr></thead>
      <tbody>${j.notes.map(n=>`
        <tr class="ndf-row" onclick="if(!event.target.closest('a,button'))ouvrirNoteRh(${n.id})" title="Consulter">
          <td><strong>${esc(n.employe_nom)}</strong><br><span style="font-size:11px;color:var(--muted)">${esc(n.matricule||'')}</span></td>
          <td>${esc(fmtDate(n.date_frais))}</td>
          <td>${esc(n.categorie||'—')}${ndfMeta(n)?`<div style="font-size:11px;color:var(--muted);margin-top:3px">${esc(ndfMeta(n))}</div>`:''}</td>
          <td style="max-width:260px">${esc((n.description||'').slice(0,90))}${(n.description||'').length>90?'…':''}${n.motif_refus?'<div style="font-size:11px;color:var(--danger);margin-top:3px">Refus : '+esc(n.motif_refus)+'</div>':''}</td>
          <td class="montant">${fmtMontant(n.montant_ttc)}${n.montant_tva?`<div style="font-size:10px;color:var(--muted);font-weight:400">TVA ${fmtMontant(n.montant_tva)}${n.montant_ht!=null?' · HT '+fmtMontant(n.montant_ht):''}</div>`:''}</td>
          <td><span class="statut ${esc(n.statut)}">${esc(MySifaNdfFiche.STATUTS[n.statut]||n.statut)}</span></td>
          <td style="white-space:nowrap;text-align:right">
            ${n.justificatif_nom?`<a class="btn ghost small" href="/api/coffre/notes-frais/${n.id}/justificatif" data-preview-url="/api/coffre/notes-frais/${n.id}/justificatif" data-preview-name="${esc(n.justificatif_nom||'Justificatif')}">Voir</a>`:''}
            ${n.statut==='soumise'||n.statut==='refusee'?`<button class="btn small" onclick="validerNdf(${n.id})">Valider</button>`:''}
            ${n.statut==='soumise'?`<button class="btn ghost small" onclick="refuserNdf(${n.id})">Refuser</button>`:''}
            ${n.statut==='validee'?`<button class="btn ok small" onclick="marquerPayee(${n.id})">Marquer payée</button>`:''}
          </td>
        </tr>
      `).join('')}</tbody>
    </table>`;
  }catch(e){document.getElementById('ndf-container').innerHTML='<p style="color:var(--danger)">Erreur : '+esc(e.message)+'</p>';}
}
document.getElementById('ndf-statut').addEventListener('change',()=>{loadNdf();rhCoffreSyncUrl();});
document.getElementById('ndf-annee').addEventListener('change',()=>{loadNdf();rhCoffreSyncUrl();});

// Les trois actions rendent true si elles ont abouti (la fiche se ferme alors).
async function validerNdf(id){
  const ok=await mysifaConfirm({title:'Valider la note',message:'La note passe au statut Validée, en attente de paiement.',confirmLabel:'Valider'});
  if(!ok)return false;
  try{await api('/api/rh-coffre/ndf/'+id+'/valider',{method:'POST'});toast('Note validée.');loadNdf();return true;}catch(e){toast(e.message,'err');return false;}
}
async function refuserNdf(id){
  const motif=await mysifaConfirm({title:'Refuser la note',message:'Le salarié verra le motif dans Mon coffre.',confirmLabel:'Refuser',danger:true,
    saisie:{label:'Motif du refus',placeholder:'ex. Justificatif illisible, dépense non professionnelle…',requis:true}});
  if(!motif)return false;
  try{
    await api('/api/rh-coffre/ndf/'+id+'/refuser',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motif})});
    toast('Note refusée.');loadNdf();return true;
  }catch(e){toast(e.message,'err');return false;}
}
async function marquerPayee(id){
  const ok=await mysifaConfirm({title:'Marquer la note payée',message:'À faire une fois le remboursement effectué.',confirmLabel:'Marquer payée'});
  if(!ok)return false;
  try{await api('/api/rh-coffre/ndf/'+id+'/marquer-payee',{method:'POST'});toast('Note marquée payée.');loadNdf();return true;}catch(e){toast(e.message,'err');return false;}
}

// ── Fiche d'une note (static/mysifa_ndf_fiche.js) ──
// La note demandée peut être hors du filtre affiché (lien, Retour) : on la
// cherche alors dans toutes les notes.
async function ouvrirNoteRh(id){
  let n=NDF_RH.find(x=>x.id===id);
  if(!n){try{const j=await api('/api/rh-coffre/ndf');n=(j.notes||[]).find(x=>x.id===id);}catch(e){}}
  if(!n){toast('Note introuvable.','err');return;}
  if(NDF_OUVERTE)NDF_OUVERTE.fermer(true);
  const actions=[];
  if(n.statut==='soumise')actions.push({cle:'refuser',label:'Refuser',style:'danger'});
  if(n.statut==='soumise'||n.statut==='refusee')actions.push({cle:'valider',label:'Valider',style:'primaire'});
  if(n.statut==='validee')actions.push({cle:'payer',label:'Marquer payée',style:'primaire'});
  const fiche=MySifaNdfFiche.ouvrir(n,{
    salarie:true,
    actions,
    surAction:async cle=>{
      if(cle==='valider')return await validerNdf(n.id);
      if(cle==='refuser')return await refuserNdf(n.id);
      if(cle==='payer')return await marquerPayee(n.id);
      return false;
    },
    surFermer:()=>{if(NDF_OUVERTE&&NDF_OUVERTE.id===n.id){NDF_OUVERTE=null;rhCoffreSyncUrl();}},
  });
  NDF_OUVERTE={id:n.id,fermer:technique=>{
    if(!NDF_OUVERTE||NDF_OUVERTE.id!==n.id)return;
    NDF_OUVERTE=null;fiche.fermer(true);
    if(technique!==true)rhCoffreSyncUrl();
  }};
  rhCoffreSyncUrl();
}

function ouvrirReglagesRh(){
  if(window.MySifaNdfReglages)MySifaNdfReglages.ouvrir({surAdresse:rhCoffreSyncUrl});
}

function fmtTaux(t){return String(t).replace('.',',')+' %';}
function ndfMeta(n){
  const p=[];
  if(n.distance_km!=null)p.push(String(n.distance_km).replace('.',',')+' km × '+String(n.taux_km).replace('.',',')+' €');
  else if(n.taux_tva!=null)p.push(n.taux_tva?'TVA '+fmtTaux(n.taux_tva):'Sans TVA');
  if(n.ville)p.push(n.ville);
  return p.join(' · ');
}

function exportNdf(){
  const statut=document.getElementById('ndf-statut').value;
  const annee=document.getElementById('ndf-annee').value;
  window.open(`/api/rh-coffre/ndf/export?statut=${statut}&annee=${annee}`,'_blank');
}

(async function init(){
  try{
    ME=await api('/api/auth/me');
    if(ME&&window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    // Pied commun : les préférences du compte peuvent changer le mode.
    if(window.MySifaSidebar){MySifaSidebar.setUser(ME);MySifaSidebar.refreshTheme();}
  }catch(e){}
  loadDashboard();
  try{
    const all=await api('/api/rh-coffre/ndf?statut=soumise');
    const badge=document.getElementById('ndf-badge');
    if(badge && all.notes.length>0){badge.style.display='';badge.textContent=String(all.notes.length);}
  }catch(e){}
  await rhCoffreDemarrerUrl();
})();
</script>
<script src="/static/mysifa_cal_rappel.js?v=9"></script>
</body>
</html>
"""
