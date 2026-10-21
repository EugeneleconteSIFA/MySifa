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
.nav-badge{margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--warn);color:#0a0e17;font-size:10px;font-weight:700;line-height:1.5}
/* Pied de sidebar : static/mysifa_sidebar.css (v3.3.0). La sidebar a ici 12px de marge
   latérale : le pied la déborde pour que son filet aille d'un bord à l'autre, comme sur MyStock. */
.sidebar>.msb-footer{margin-left:-12px;margin-right:-12px;padding-left:12px;padding-right:12px}

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
.btn{padding:10px 18px;border-radius:10px;border:none;background:var(--accent);color:white;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:8px}
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
.statut.validee{background:color-mix(in srgb,var(--accent,#22d3ee) 15%,transparent);color:var(--accent)}
.statut.payee{background:rgba(52,211,153,.15);color:var(--ok)}
.statut.refusee{background:rgba(248,113,113,.15);color:var(--danger)}
.montant{font-family:'SF Mono','Consolas',monospace;font-weight:700;color:var(--text)}
.filters{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.filters select{padding:7px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text2);font-size:12px;font-family:inherit;outline:none}
.filters select:focus{border-color:var(--accent)}

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
.modal{background:var(--card);border:1px solid var(--border);border-top:3px solid var(--accent);border-radius:14px;padding:0;max-width:520px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 24px 64px rgba(0,0,0,.35)}
.modal h3{margin:0;font-size:16px;font-weight:700;color:var(--text)}
.modal-head{display:flex;align-items:center;gap:12px;padding:18px 22px;background:var(--accent-bg);border-bottom:1px solid var(--border)}
.modal-head-ico{width:36px;height:36px;flex-shrink:0;border-radius:10px;background:var(--accent);color:white;display:flex;align-items:center;justify-content:center}
.modal-head-sub{font-size:12px;color:var(--text2);margin-top:2px}
.modal-body{padding:18px 22px 4px}
.ndf-section{border:1px solid var(--border);border-radius:12px;padding:14px 14px 0;margin-bottom:14px;background:var(--bg)}
.ndf-section.montants{background:color-mix(in srgb,var(--accent) 7%,var(--card));border-color:color-mix(in srgb,var(--accent) 30%,var(--border))}
.ndf-section-titre{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.6px;margin-bottom:12px}
.ndf-section-titre::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--accent)}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s;min-height:40px}
.field select{-webkit-appearance:none;appearance:none;padding-right:34px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center} /* hex-ok : flèche SVG */
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent,#22d3ee) 12%,transparent)}
.field textarea{min-height:64px;resize:vertical}
.cat-chips{display:flex;flex-wrap:wrap;gap:8px}
.field .cat-chip,.field .file-drop{text-transform:none;letter-spacing:0;margin:0}
.field .cat-chip{display:inline-block}
.cat-chip{position:relative;cursor:pointer}
.cat-chip input{position:absolute;opacity:0;pointer-events:none}
.cat-chip span{display:inline-flex;align-items:center;padding:8px 14px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--text2);font-size:13px;font-weight:600;transition:all .15s}
.cat-chip:hover span{border-color:var(--accent);color:var(--accent)}
.cat-chip input:checked+span{background:var(--accent);border-color:var(--accent);color:white}
.cat-chip input:focus-visible+span{box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent)}
.calc-val{padding:10px 12px;border:1px solid color-mix(in srgb,var(--accent) 30%,var(--border));border-radius:8px;background:var(--accent-bg);font-size:14px;color:var(--accent);font-family:'SF Mono','Consolas',monospace;font-weight:700;min-height:40px;display:flex;align-items:center}
.calc-hint{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.4}
.ndf-meta{font-size:11px;color:var(--muted);margin-top:3px}
.file-drop{display:flex;align-items:center;justify-content:center;gap:8px;border:1.5px dashed color-mix(in srgb,var(--accent) 40%,var(--border));border-radius:10px;padding:14px;text-align:center;font-size:12px;font-weight:600;color:var(--accent);background:var(--card);cursor:pointer;transition:all .15s}
.file-drop:hover{border-color:var(--accent);background:var(--accent-bg)}
.file-drop.has-file{border-style:solid;color:var(--text);background:var(--accent-bg)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;align-items:center;flex-wrap:wrap;padding:14px 22px;background:var(--bg);border-top:1px solid var(--border);position:sticky;bottom:0}
.modal-actions .btn.ghost{background:var(--card)}
.modal-actions .btn.ghost:hover{background:var(--bg)}
.modal-actions .sep{flex:1}
.toast{position:fixed;top:24px;right:24px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 18px;font-size:13px;color:var(--text);z-index:1000;box-shadow:0 10px 24px rgba(0,0,0,.3);animation:slideIn .2s}
.toast.err{border-left-color:var(--danger)}
.toast.ok{border-left-color:var(--ok)}
@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:translateX(0);opacity:1}}

@media(max-width:640px){.container{max-width:100%}.row2{grid-template-columns:1fr}table{font-size:12px}th,td{padding:8px}.doc-list{grid-template-columns:1fr}}
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
      <div class="logo-sub">Mon coffre RH</div>
    </div>

    <button type="button" class="nav-btn" id="nav-bulletins" onclick="showTab('bulletins')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      Mes bulletins
    </button>
    <button type="button" class="nav-btn" id="nav-documents" onclick="showTab('documents')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      Autres documents
    </button>
    <button type="button" class="nav-btn active" id="nav-ndf" onclick="showTab('ndf')">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
      Notes de frais
      <span class="nav-badge" id="ndf-badge" style="display:none">0</span>
    </button>

    <!-- Pied commun (static/mysifa_sidebar.js), rempli au chargement. -->
    <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="Mon coffre" data-msb-version="__V_LABEL__"></div>
  </aside>

  <main class="main">
    <div class="container">

      <div class="mobile-topbar">
        <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()" aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div>
          <div class="mobile-topbar-title">Mon coffre</div>
          <div class="mobile-topbar-sub" id="mobile-sub">Notes de frais</div>
        </div>
        <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
        </button>
      </div>

      <h1 id="page-title">Notes de frais</h1>
      <p class="subtitle" id="page-sub">Dépôt de justificatifs et suivi des remboursements.</p>

      <div class="info-banner">
        Coffre interne SIFA — le bulletin officiel reste celui remis en main propre par la comptabilité.
      </div>

      <div class="pane-tab" id="pane-bulletins">
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

      <div class="pane-tab active" id="pane-ndf">
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:10px">
            <h2 style="margin:0">Mes notes de frais</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button type="button" class="btn ghost" id="ndf-reglages-btn" style="display:none" onclick="ouvrirReglagesNdf()">Réglages</button>
              <button type="button" class="btn" onclick="openNdfModal()">+ Nouvelle note</button>
            </div>
          </div>
          <div id="ndf-container"><div class="empty">Chargement…</div></div>
        </div>
      </div>

    </div>
  </main>
</div>

<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_ndf_reglages.js?v=1"></script>
<script>window.__MYSIFA_APP__='coffre';</script>
<script>
const DOC_TYPE_LABELS={bulletin_paie:'Bulletin de paie',contrat:'Contrat',attestation:'Attestation',autre:'Autre'};
const MOIS_LABELS=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

let ME=null;let CURRENT_TAB='ndf';let NDF_CATS=[];let NDF_TAUX=[20,10,5.5,0];let bulData={documents:[],annees_disponibles:[]};

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
  const close=()=>{back.remove();document.removeEventListener('keydown',onKey);};
  const onKey=(e)=>{if(e.key==='Escape')close();};
  document.addEventListener('keydown',onKey);
  back.querySelector('#preview-close').onclick=close;
  back.addEventListener('click',(e)=>{if(e.target===back)close();});
}
// Délégation globale : tout élément avec data-preview-url déclenche l'aperçu.
document.addEventListener('click',(e)=>{
  const el=e.target.closest('[data-preview-url]');
  if(!el)return;
  e.preventDefault();
  previewDocument(el.dataset.previewUrl, el.dataset.previewName||'');
});

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

const TAB_META={
  bulletins:{title:'Mes bulletins',sub:'Bulletins de paie mis à disposition par la comptabilité.'},
  documents:{title:'Autres documents',sub:'Contrats, attestations et autres pièces RH.'},
  ndf:{title:'Notes de frais',sub:'Dépôt de justificatifs et suivi des remboursements.'},
};
var COFFRE_VALID_TABS=['bulletins','documents','ndf'];
function _readCoffreTab(){
  try{var h=(location.hash||'').replace(/^#/,'').trim();
    if(COFFRE_VALID_TABS.indexOf(h)!==-1)return h;}catch(e){}
  try{var u=new URLSearchParams(location.search).get('tab');
    if(u&&COFFRE_VALID_TABS.indexOf(u)!==-1)return u;}catch(e){}
  return 'ndf';
}
function showTab(tab, opts){
  var silent=!!(opts&&opts.silent);
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
  if(!silent){try{var target='#'+tab;if(location.hash!==target)history.replaceState(null,'',target);}catch(e){}}
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
          <a class="doc-item" href="/api/coffre/documents/${d.id}/download" data-preview-url="/api/coffre/documents/${d.id}/download" data-preview-name="${esc((MOIS_LABELS[d.mois]||d.libelle||'Bulletin')+' '+(d.annee||'')+'.pdf')}">
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
      <a class="doc-item" href="/api/coffre/documents/${d.id}/download" data-preview-url="/api/coffre/documents/${d.id}/download" data-preview-name="${esc((d.libelle||DOC_TYPE_LABELS[d.type]||d.type)+'.pdf')}">
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
          <td>${esc(n.categorie||'—')}<div class="ndf-meta">${esc(ndfMeta(n))}</div></td>
          <td style="max-width:280px">${esc((n.description||'').slice(0,80))}${(n.description||'').length>80?'…':''}${n.motif_refus?'<div style="font-size:11px;color:var(--danger);margin-top:3px">Refus : '+esc(n.motif_refus)+'</div>':''}</td>
          <td style="text-align:right" class="montant">${fmtMontant(n.montant_ttc)}</td>
          <td><span class="statut ${esc(n.statut)}">${esc(n.statut)}</span></td>
          <td style="text-align:right;white-space:nowrap">
            ${n.justificatif_nom?`<a class="btn ghost small" href="/api/coffre/notes-frais/${n.id}/justificatif" data-preview-url="/api/coffre/notes-frais/${n.id}/justificatif" data-preview-name="${esc(n.justificatif_nom||'Justificatif')}">Voir</a>`:''}
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

function fmtTaux(t){return String(t).replace('.',',')+' %';}
function fmtNombre(n){return (Number(n)||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:3});}
function ndfMeta(n){
  const p=[];
  if(n.distance_km!=null)p.push(fmtNombre(n.distance_km).replace(/,?0+$/,'')+' km × '+fmtNombre(n.taux_km)+' €');
  else if(n.taux_tva!=null)p.push(n.taux_tva?'TVA '+fmtTaux(n.taux_tva)+' · '+fmtMontant(n.montant_tva):'Sans TVA');
  if(n.ville)p.push(n.ville);
  return p.join(' · ');
}
async function loadNdfCategories(){
  try{const j=await api('/api/coffre/ndf-categories');NDF_CATS=j.categories||[];NDF_TAUX=j.taux_tva||NDF_TAUX;}catch(e){}
}
// Même calcul que ndf_montants() de app/routers/coffre.py.
function ndfCalcul(cat,ttc,taux,km){
  const r2=x=>Math.round(x*100)/100;
  if(cat&&cat.saisie==='km'){const t=r2((km||0)*(cat.taux_km||0));return {ttc:t,tva:0,ht:t};}
  const tva=r2(ttc-ttc/(1+taux/100));
  return {ttc:r2(ttc),tva,ht:r2(ttc-tva)};
}

// Réglages (barème km, catégories) : comptabilité et superadmin seulement,
// comme l'API /api/rh-coffre/ndf-categories.
function peutReglerNdf(){return !!(ME&&(ME.role==='comptabilite'||ME.role==='superadmin'));}
function ouvrirReglagesNdf(){
  if(window.MySifaNdfReglages)MySifaNdfReglages.ouvrir({surChange:loadNdfCategories});
}

function openNdfModal(){
  if(!NDF_CATS.length){toast('Aucune catégorie de note de frais — à créer par la comptabilité.','err');return;}
  const back=document.createElement('div');back.className='modal-back';
  const today=new Date().toISOString().slice(0,10);
  back.innerHTML=`<div class="modal">
    <div class="modal-head">
      <div class="modal-head-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg></div>
      <div><h3>Nouvelle note de frais</h3><div class="modal-head-sub">HT et TVA sont calculés à partir du montant TTC.</div></div>
    </div>
    <form id="ndf-form">
      <div class="modal-body">
        <div class="ndf-section">
          <div class="ndf-section-titre">Le frais</div>
          <div class="field"><label>Catégorie</label>
            <div class="cat-chips" id="ndf-cats">
              ${NDF_CATS.map((c,i)=>`<label class="cat-chip"><input type="radio" name="categorie_id" value="${c.id}"${i===0?' required':''}><span>${esc(c.libelle)}</span></label>`).join('')}
            </div>
          </div>
          <div class="row2">
            <div class="field"><label>Date du frais</label><input type="date" name="date_frais" value="${today}" required></div>
            <div class="field"><label>Ville</label><input type="text" name="ville" maxlength="80" placeholder="ex. Lyon"></div>
          </div>
        </div>
        <div class="ndf-section montants">
          <div class="ndf-section-titre">Montant</div>
          <div id="ndf-montant-zone">
            <div class="row2">
              <div class="field"><label>Montant TTC (€)</label><input type="number" step="0.01" min="0.01" name="montant_ttc" id="ndf-ttc" placeholder="0,00"></div>
              <div class="field"><label>Taux de TVA</label>
                <select name="taux_tva" id="ndf-taux">${NDF_TAUX.map(t=>`<option value="${t}">${t?fmtTaux(t):'Sans TVA'}</option>`).join('')}</select>
              </div>
            </div>
            <div class="row2">
              <div class="field"><label>TVA (€)</label><input type="number" step="0.01" min="0" name="montant_tva" id="ndf-tva" placeholder="0,00">
                <div class="calc-hint">Modifiable pour un ticket à plusieurs taux.</div></div>
              <div class="field"><label>Montant HT</label><div class="calc-val" id="ndf-ht">0,00 €</div></div>
            </div>
          </div>
          <div id="ndf-km-zone" style="display:none">
            <div class="row2">
              <div class="field"><label>Distance (km)</label><input type="number" step="0.1" min="0.1" name="distance_km" id="ndf-km" placeholder="0"></div>
              <div class="field"><label>Montant</label><div class="calc-val" id="ndf-km-total">0,00 €</div>
                <div class="calc-hint" id="ndf-km-hint"></div></div>
            </div>
          </div>
        </div>
        <div class="ndf-section">
          <div class="ndf-section-titre">Détails et justificatif</div>
          <div class="field"><label>Description</label><textarea name="description" placeholder="Détails, contexte, participants…" maxlength="1000"></textarea></div>
          <div class="field">
            <label class="file-drop" id="drop-label">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
              <span id="drop-txt">Joindre le justificatif (PDF, JPG, PNG — 10 Mo max)</span>
              <input type="file" name="justificatif" id="ndf-file" accept="application/pdf,image/*" style="display:none">
            </label>
          </div>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" id="ndf-cancel">Annuler</button>
        <span class="sep"></span>
        <button type="submit" class="btn ghost" name="soumettre" value="0">Enregistrer brouillon</button>
        <button type="submit" class="btn" name="soumettre" value="1">Soumettre à la compta</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(back);
  const $=s=>back.querySelector(s);
  const catsEl=$('#ndf-cats'),ttcEl=$('#ndf-ttc'),tauxEl=$('#ndf-taux'),tvaEl=$('#ndf-tva'),kmEl=$('#ndf-km');
  let tvaManuelle=false;
  const catCourante=()=>{const r=back.querySelector('input[name="categorie_id"]:checked');return r?NDF_CATS.find(c=>String(c.id)===r.value)||null:null;};
  function majCalcul(){
    const cat=catCourante();
    const km=!!(cat&&cat.saisie==='km');
    $('#ndf-montant-zone').style.display=km?'none':'';
    $('#ndf-km-zone').style.display=km?'':'none';
    ttcEl.required=!km;kmEl.required=km;
    if(km){
      const r=ndfCalcul(cat,0,0,parseFloat(kmEl.value)||0);
      $('#ndf-km-total').textContent=fmtMontant(r.ttc);
      $('#ndf-km-hint').textContent=cat.taux_km?'Barème : '+fmtNombre(cat.taux_km)+' € par km':'Taux kilométrique non défini — prévenir la comptabilité.';
      return;
    }
    const ttc=parseFloat(ttcEl.value)||0;
    const r=ndfCalcul(cat,ttc,parseFloat(tauxEl.value)||0,0);
    if(!tvaManuelle)tvaEl.value=ttc?r.tva.toFixed(2):'';
    const tva=parseFloat(tvaEl.value)||0;
    $('#ndf-ht').textContent=fmtMontant(ttc?ttc-tva:0);
  }
  catsEl.addEventListener('change',()=>{
    const cat=catCourante();
    if(cat&&cat.saisie!=='km')tauxEl.value=String(cat.taux_tva);
    tvaManuelle=false;majCalcul();
  });
  tauxEl.addEventListener('change',()=>{tvaManuelle=false;majCalcul();});
  ttcEl.addEventListener('input',majCalcul);
  kmEl.addEventListener('input',majCalcul);
  tvaEl.addEventListener('input',()=>{tvaManuelle=tvaEl.value!=='';majCalcul();});
  const fileEl=$('#ndf-file');
  const dropLbl=$('#drop-label');
  const dropTxt=$('#drop-txt');
  fileEl.addEventListener('change',()=>{
    if(fileEl.files.length){dropLbl.classList.add('has-file');dropTxt.textContent=fileEl.files[0].name;}
    else{dropLbl.classList.remove('has-file');dropTxt.textContent='Joindre le justificatif (PDF, JPG, PNG — 10 Mo max)';}
  });
  $('#ndf-cancel').onclick=()=>back.remove();
  back.onclick=(e)=>{if(e.target===back)back.remove();};
  const form=$('#ndf-form');
  form.addEventListener('submit',async(e)=>{
    e.preventDefault();
    const btn=e.submitter;
    const fd=new FormData(form);
    fd.set('soumettre',btn && btn.value==='1'?'1':'0');
    const cat=catCourante();
    if(cat&&cat.saisie==='km'){fd.delete('montant_ttc');fd.delete('montant_tva');fd.delete('taux_tva');}
    else fd.delete('distance_km');
    try{
      const r=await fetch('/api/coffre/notes-frais',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      toast(btn.value==='1'?'Note soumise.':'Brouillon enregistré.');
      back.remove();
      loadNdf();
    }catch(e){toast(e.message,'err');}
  });
}

(async function init(){
  try{
    ME=await api('/api/auth/me');
    if(ME&&window.MySifaTheme)MySifaTheme.mergeFromUser(ME);
    // Pied commun : les préférences du compte peuvent changer le mode.
    if(window.MySifaSidebar){MySifaSidebar.setUser(ME);MySifaSidebar.refreshTheme();}
  }catch(e){}
  loadBulletins();
  loadDocs();
  loadNdf();
  loadNdfCategories();
  if(peutReglerNdf()){
    const b=document.getElementById('ndf-reglages-btn');if(b)b.style.display='';
    if(window.MySifaNdfReglages)MySifaNdfReglages.depuisAdresse({surChange:loadNdfCategories});
  }
  showTab(_readCoffreTab(),{silent:false});
})();
window.addEventListener('hashchange',function(){try{showTab(_readCoffreTab(),{silent:true});}catch(e){}});
</script>
<script src="/static/mysifa_cal_rappel.js?v=9"></script>
</body>
</html>
"""
