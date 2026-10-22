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
.nav-badge{margin-left:auto;padding:1px 7px;border-radius:9px;background:var(--accent);color:white;font-size:10px;font-weight:700;line-height:1.5}
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
.statut{display:inline-block;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;border:1px solid transparent}
.statut.brouillon{background:transparent;border:1px dashed var(--border);color:var(--muted)}
.statut.soumise{background:var(--accent-bg);border-color:color-mix(in srgb,var(--accent) 45%,transparent);color:var(--accent)}
.statut.validee{background:color-mix(in srgb,var(--success) 14%,transparent);border-color:color-mix(in srgb,var(--success) 40%,transparent);color:var(--success)}
.statut.payee{background:var(--success);color:white}
.statut.refusee{background:color-mix(in srgb,var(--danger) 12%,transparent);border-color:color-mix(in srgb,var(--danger) 40%,transparent);color:var(--danger)}
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
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:0;max-width:520px;width:100%;max-height:90vh;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;box-shadow:0 24px 64px rgba(0,0,0,.35)}
/* Sur téléphone, un champ à 100 % plus son padding débordait et laissait
   « étirer » la fenêtre de côté : tout est compté bordure comprise, et la
   page derrière ne défile plus tant qu'une fenêtre est ouverte. */
.modal *,.modal *::before,.modal *::after{box-sizing:border-box}
.modal-back{overscroll-behavior:contain;touch-action:pan-y}
html:has(.modal-back),html:has(.modal-back) body{overflow:hidden}
.modal h3{margin:0;font-size:16px;font-weight:700;color:var(--text)}
.modal-head{display:flex;align-items:center;gap:12px;padding:18px 22px 14px;border-bottom:1px solid var(--border)}
.modal-head-ico{width:34px;height:34px;flex-shrink:0;border-radius:9px;background:var(--bg);border:1px solid var(--border);color:var(--text2);display:flex;align-items:center;justify-content:center}
.modal-head-sub{font-size:12px;color:var(--muted);margin-top:2px}
.modal-body{padding:18px 22px 4px}
.ndf-section{padding:0;margin-bottom:4px}
.ndf-section+.ndf-section{border-top:1px solid var(--border);padding-top:16px}
.ndf-section-titre{font-size:13px;font-weight:700;color:var(--text);margin-bottom:12px}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s;min-height:40px}
.field select{-webkit-appearance:none;appearance:none;padding-right:34px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center} /* hex-ok : flèche SVG */
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent,#22d3ee) 12%,transparent)}
.field textarea{min-height:64px;resize:vertical}
.ndf-calcule{padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);font-size:13px;line-height:1.4;color:var(--text);font-weight:700;font-variant-numeric:tabular-nums;min-height:40px;display:flex;align-items:center}
.ndf-ht{font-size:12px;color:var(--muted);margin-top:-6px;margin-bottom:14px;font-variant-numeric:tabular-nums}
.calc-hint{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.4}
.ndf-meta{font-size:11px;color:var(--muted);margin-top:3px}
tr.ndf-row{cursor:pointer}
.ndf-cartes{display:none}
.ndf-mois+.ndf-mois{margin-top:16px}
.ndf-mois-tete{display:flex;justify-content:space-between;gap:8px;padding:0 2px 6px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.ndf-carte{display:flex;flex-direction:column;gap:6px;width:100%;text-align:left;padding:12px;margin-bottom:8px;border:1px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);font-family:inherit;cursor:pointer}
.ndf-carte:active{border-color:var(--accent)}
.ndf-carte-l1,.ndf-carte-l2{display:flex;justify-content:space-between;align-items:center;gap:10px}
.ndf-carte-cat{font-size:14px;font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ndf-carte-mt{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.ndf-carte-l2{font-size:12px;color:var(--muted)}
.ndf-carte-refus{font-size:12px;color:var(--danger)}
@media(max-width:640px){.ndf-tableau{display:none}.ndf-cartes{display:block}}
.file-drop{display:flex;align-items:center;justify-content:center;gap:8px;border:1.5px dashed var(--border);border-radius:8px;padding:14px;text-align:center;font-size:12px;font-weight:500;color:var(--muted);background:var(--card);cursor:pointer;transition:border-color .15s,color .15s}
.field .file-drop{display:flex;text-transform:none;letter-spacing:0;margin:0}
.file-drop.grand{flex-direction:column;gap:6px;padding:22px 16px;font-size:13px;font-weight:600;color:var(--text2)}
.file-drop.grand svg{color:var(--accent)}
.drop-mobile{display:none;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:6px}
.file-drop.tactile{cursor:default}
.file-drop.tactile .drop-mobile{display:flex}
.file-drop.tactile .drop-ico-fichier{display:none}
.drop-mobile .btn svg{color:currentColor}
.file-drop.survol{border-color:var(--accent);background:var(--accent-bg)}
.drop-sub{font-size:11px;font-weight:400;color:var(--muted)}
.justif-apercu{display:flex;align-items:center;gap:12px;margin-top:8px;padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--card)}
.justif-apercu[hidden]{display:none}
.justif-apercu img,.justif-doc{width:56px;height:56px;flex-shrink:0;border-radius:6px;border:1px solid var(--border);object-fit:cover;background:var(--bg)}
.justif-doc{display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--muted)}
.justif-nom{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;font-size:13px}
.justif-nom strong{font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.justif-nom span{font-size:11px;color:var(--muted)}
.scan-etat{margin-top:8px;font-size:12px;line-height:1.45;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text2)}
.scan-etat.encours{color:var(--accent)}
.scan-etat.ok{border-color:color-mix(in srgb,var(--success) 40%,var(--border));color:var(--text)}
.scan-etat.err{border-color:color-mix(in srgb,var(--danger) 40%,var(--border));color:var(--danger)}
.field label .lu{display:inline-block;margin-left:6px;padding:0 6px;border-radius:5px;background:var(--accent-bg);text-transform:none;letter-spacing:0;font-weight:600;font-size:10px;line-height:16px;color:var(--accent)}
#scan-manuel{margin-top:6px}
.file-drop:hover{border-color:var(--accent);color:var(--accent)}
.file-drop.has-file{border-style:solid;color:var(--text)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.row3{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:10px}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;align-items:center;flex-wrap:wrap;padding:14px 22px;background:var(--card);border-top:1px solid var(--border);position:sticky;bottom:0}
.modal-actions .btn.ghost{background:var(--bg)}
.modal-actions .btn.ghost:hover{background:var(--card)}
.modal-actions .sep{flex:1}
.toast{position:fixed;top:24px;right:24px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 18px;font-size:13px;color:var(--text);z-index:1000;box-shadow:0 10px 24px rgba(0,0,0,.3);animation:slideIn .2s}
.toast.err{border-left-color:var(--danger)}
.toast.ok{border-left-color:var(--ok)}
@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:translateX(0);opacity:1}}

@media(max-width:640px){.container{max-width:100%}.row2,.row3{grid-template-columns:1fr}table{font-size:12px}th,td{padding:8px}.doc-list{grid-template-columns:1fr}
  .modal-back{padding:10px}
  .modal-head,.modal-body,.modal-actions{padding-left:16px;padding-right:16px}
  /* Boutons du bas : l'action principale sur toute la largeur, les deux
     autres côte à côte en dessous. */
  .modal-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .modal-actions .sep{display:none}
  .modal-actions .btn{justify-content:center;width:100%;white-space:nowrap;padding:11px 8px}
  .modal-actions .btn:not(.ghost){grid-column:1/-1;order:-1}}
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
            <button type="button" class="btn" onclick="openNdfModal()">+ Nouvelle note</button>
          </div>
          <div id="ndf-container"><div class="empty">Chargement…</div></div>
        </div>
      </div>

    </div>
  </main>
</div>

<script src="/static/support_widget.js"></script>
<script src="/static/mysifa_confirm.js?v=2"></script>
<script src="/static/mysifa_ndf_fiche.js?v=2"></script>
<script src="/static/mysifa_url.js?v=5"></script>
<script src="/static/coffre_url.js?v=1"></script>
<script>window.__MYSIFA_APP__='coffre';</script>
<script>
const DOC_TYPE_LABELS={bulletin_paie:'Bulletin de paie',contrat:'Contrat',attestation:'Attestation',autre:'Autre'};
const MOIS_LABELS=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

let ME=null;let CURRENT_TAB='ndf';let NDF_CATS=[];let NDF_TAUX=[20,10,5.5,0];let NDF_NOTES=[];
// Fenêtres ouvertes, lues par static/coffre_url.js : {id|url, fermer(technique)}.
let NDF_OUVERTE=null;let NDF_EDITION=null;let APERCU=null;let bulData={documents:[],annees_disponibles:[]};

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtMontant(n){return (Number(n)||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' €';}
function fmtDate(s){if(!s)return '';const d=new Date(s.substr(0,10));return isNaN(d)?s:d.toLocaleDateString('fr-FR');}
function toast(msg,type){const t=document.createElement('div');t.className='toast '+(type==='err'?'err':'ok');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3500);}
async function api(url,opts){opts=opts||{};opts.credentials='include';const r=await fetch(url,opts);if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}return r.json();}

// ── Prévisualisation documents (PDF / image) ──
const PREVIEW_IMG_RE=/\.(png|jpe?g|gif|webp|heic|bmp|svg)$/i;
// `local` : fichier choisi dans le formulaire et pas encore envoyé (adresse
// blob:). Il n'entre pas dans l'adresse de la page et ne se télécharge pas.
function previewDocument(url, filename, local){
  const back=document.createElement('div');
  back.className='preview-back';
  const isImg=PREVIEW_IMG_RE.test(filename||'');
  const sep=url.indexOf('?')>=0?'&':'?';
  const inlineUrl=local?url:url+sep+'inline=1';
  const safeName=esc(filename||'Document');
  const safeUrl=esc(url);
  const safeInline=esc(inlineUrl);
  back.innerHTML=`
    <div class="preview-modal">
      <div class="preview-header">
        <div class="preview-title">${safeName}</div>
        <div class="preview-actions">
          ${local?'':`<a class="btn ghost small" href="${safeUrl}" target="_blank" rel="noopener">Télécharger</a>`}
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
    if(APERCU&&APERCU.el===back){APERCU=null;if(technique!==true)coffreSyncUrl();}
  };
  const onKey=(e)=>{if(e.key==='Escape'){e.stopImmediatePropagation();close();}};
  document.addEventListener('keydown',onKey,true);
  back.querySelector('#preview-close').onclick=()=>close();
  back.addEventListener('click',(e)=>{if(e.target===back)close();});
  if(local)return;
  APERCU={url,el:back,fermer:close};
  coffreSyncUrl();
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
  coffreSyncUrl();
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
document.getElementById('filter-bul-annee').addEventListener('change',()=>{loadBulletins();coffreSyncUrl();});

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
    NDF_NOTES=j.notes||[];
    const c=document.getElementById('ndf-container');
    const badge=document.getElementById('ndf-badge');
    const pending=j.notes.filter(n=>n.statut==='brouillon'||n.statut==='soumise').length;
    if(badge){if(pending>0){badge.style.display='';badge.textContent=String(pending);}else{badge.style.display='none';}}
    if(!j.notes.length){c.innerHTML='<div class="empty">Aucune note de frais. Cliquez sur « Nouvelle note » pour en créer une.</div>';return;}
    const cartes=ndfCartes(NDF_NOTES);
    c.innerHTML=`<div class="ndf-tableau" style="overflow-x:auto"><table>
      <thead><tr><th>Date</th><th>Catégorie</th><th>Description</th><th style="text-align:right">Montant</th><th>Statut</th><th></th></tr></thead>
      <tbody>${j.notes.map(n=>`
        <tr class="ndf-row" onclick="if(!event.target.closest('a,button'))ouvrirNote(${n.id})" title="Consulter">
          <td>${esc(fmtDate(n.date_frais))}</td>
          <td>${esc(n.categorie||'—')}<div class="ndf-meta">${esc(ndfMeta(n))}</div></td>
          <td style="max-width:280px">${esc((n.description||'').slice(0,80))}${(n.description||'').length>80?'…':''}${n.motif_refus?'<div style="font-size:11px;color:var(--danger);margin-top:3px">Refus : '+esc(n.motif_refus)+'</div>':''}</td>
          <td style="text-align:right" class="montant">${fmtMontant(n.montant_ttc)}</td>
          <td><span class="statut ${esc(n.statut)}">${esc(NDF_STATUTS[n.statut]||n.statut)}</span></td>
          <td style="text-align:right;white-space:nowrap">
            ${n.justificatif_nom?`<a class="btn ghost small" href="/api/coffre/notes-frais/${n.id}/justificatif" data-preview-url="/api/coffre/notes-frais/${n.id}/justificatif" data-preview-name="${esc(n.justificatif_nom||'Justificatif')}">Voir</a>`:''}
            ${n.statut==='brouillon'?`
              <button class="btn ghost small" onclick="openNdfModal(${n.id})">Modifier</button>
              <button class="btn small" onclick="submitNdf(${n.id})">Soumettre</button>
              <button class="btn ghost small" onclick="deleteNdf(${n.id})">×</button>
            `:''}
          </td>
        </tr>
      `).join('')}</tbody>
    </table></div>${cartes}`;
  }catch(e){document.getElementById('ndf-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}
const NDF_STATUTS={brouillon:'Brouillon',soumise:'Soumise',validee:'Validée',payee:'Payée',refusee:'Refusée'};
async function submitNdf(id){
  const ok=await mysifaConfirm({title:'Soumettre la note',message:'La note part à la comptabilité pour validation.',detail:'Une fois soumise, elle ne pourra plus être modifiée.',confirmLabel:'Soumettre'});
  if(!ok)return false;
  try{await api('/api/coffre/notes-frais/'+id+'/soumettre',{method:'POST'});toast('Note soumise.');loadNdf();return true;}catch(e){toast(e.message,'err');return false;}
}
async function deleteNdf(id){
  const ok=await mysifaConfirm({title:'Supprimer le brouillon',message:'Le brouillon et son justificatif seront retirés de vos notes de frais.',confirmLabel:'Supprimer',danger:true});
  if(!ok)return false;
  try{await api('/api/coffre/notes-frais/'+id,{method:'DELETE'});toast('Brouillon supprimé.');loadNdf();return true;}catch(e){toast(e.message,'err');return false;}
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
// Téléphone : une carte par note, regroupées par mois avec leur total. Le
// tableau, trop large pour un petit écran, est alors masqué (CSS). Les actions
// (Modifier, Soumettre, Supprimer) sont dans la fiche qu'ouvre la carte.
function ndfCartes(liste){
  const mois=[];
  liste.forEach(n=>{
    const cle=(n.date_frais||'').slice(0,7);
    let g=mois.find(x=>x.cle===cle);
    if(!g){g={cle,lignes:[],total:0};mois.push(g);}
    g.lignes.push(n);g.total+=Number(n.montant_ttc)||0;
  });
  return '<div class="ndf-cartes">'+mois.map(g=>{
    const [a,m]=g.cle.split('-');
    const titre=m?(MOIS_LABELS[Number(m)]||m)+' '+a:'Sans date';
    const resume=g.lignes.length+(g.lignes.length>1?' notes · ':' note · ')+fmtMontant(g.total);
    return `<div class="ndf-mois">
      <div class="ndf-mois-tete"><span>${esc(titre)}</span><span>${esc(resume)}</span></div>
      ${g.lignes.map(n=>`
        <button type="button" class="ndf-carte" onclick="ouvrirNote(${n.id})">
          <span class="ndf-carte-l1"><span class="ndf-carte-cat">${esc(n.categorie||'Note de frais')}</span><span class="ndf-carte-mt">${fmtMontant(n.montant_ttc)}</span></span>
          <span class="ndf-carte-l2"><span>${esc([fmtDate(n.date_frais),n.ville].filter(Boolean).join(' · '))}</span><span class="statut ${esc(n.statut)}">${esc(NDF_STATUTS[n.statut]||n.statut)}</span></span>
          ${n.motif_refus?`<span class="ndf-carte-refus">Refus : ${esc(n.motif_refus)}</span>`:''}
        </button>`).join('')}
    </div>`;
  }).join('')+'</div>';
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

// ── Consultation d'une note (tous statuts) : static/mysifa_ndf_fiche.js ──
function ouvrirNote(id){
  const n=NDF_NOTES.find(x=>x.id===id);
  if(!n){toast('Note introuvable.','err');return;}
  if(NDF_OUVERTE)NDF_OUVERTE.fermer(true);
  const actions=n.statut==='brouillon'?[
    {cle:'supprimer',label:'Supprimer',style:'danger'},
    {cle:'modifier',label:'Modifier',style:'secondaire'},
    {cle:'soumettre',label:'Soumettre à la compta',style:'primaire'},
  ]:[];
  const fiche=MySifaNdfFiche.ouvrir(n,{
    actions,
    surAction:async cle=>{
      if(cle==='modifier'){fermerFiche(true);openNdfModal(n.id);return false;}
      if(cle==='soumettre')return await submitNdf(n.id);
      if(cle==='supprimer')return await deleteNdf(n.id);
      return false;
    },
    surFermer:()=>{if(NDF_OUVERTE&&NDF_OUVERTE.id===n.id){NDF_OUVERTE=null;coffreSyncUrl();}},
  });
  function fermerFiche(technique){
    if(!NDF_OUVERTE||NDF_OUVERTE.id!==n.id)return;
    NDF_OUVERTE=null;fiche.fermer(true);
    if(!technique)coffreSyncUrl();
  }
  NDF_OUVERTE={id:n.id,fermer:fermerFiche};
  coffreSyncUrl();
}

// Sans argument : nouvelle note. Avec l'id d'un brouillon : modification.
function openNdfModal(noteId){
  if(!NDF_CATS.length){toast('Aucune catégorie de note de frais — à créer par la comptabilité.','err');return;}
  const edite=noteId?NDF_NOTES.find(n=>n.id===noteId&&n.statut==='brouillon'):null;
  if(noteId&&!edite){toast('Brouillon introuvable — il a peut-être déjà été soumis.','err');return;}
  const titre=edite?'Modifier le brouillon':'Nouvelle note de frais';
  // Téléphone ou tablette : on photographie le ticket. Ordinateur : on dépose un fichier.
  const tactile=window.matchMedia&&matchMedia('(pointer: coarse)').matches;
  const back=document.createElement('div');back.className='modal-back';
  const today=new Date().toISOString().slice(0,10);
  back.innerHTML=`<div class="modal">
    <div class="modal-head">
      <div class="modal-head-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg></div>
      <div><h3>${titre}</h3><div class="modal-head-sub">Joignez le justificatif : les champs se remplissent seuls.</div></div>
    </div>
    <form id="ndf-form">
      <div class="modal-body">
        <div class="ndf-section">
          <div class="ndf-section-titre">Justificatif</div>
          <div class="field">
            <div class="file-drop grand${tactile?' tactile':''}" id="drop-label" role="button" tabindex="0">
              <svg class="drop-ico-fichier" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span id="drop-txt"></span>
              <span class="drop-sub">PDF, JPG ou PNG — 10 Mo max. Les champs marqués « lu » viennent du ticket.</span>
              <div class="drop-mobile">
                <button type="button" class="btn small" id="btn-photo">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                  Prendre une photo</button>
                <button type="button" class="btn ghost small" id="btn-fichier">Choisir un fichier</button>
              </div>
            </div>
            <input type="file" id="ndf-file" accept="application/pdf,image/*" hidden>
            <input type="file" id="ndf-photo" accept="image/*" capture="environment" hidden>
            <div class="justif-apercu" id="justif-apercu" hidden></div>
            <div class="scan-etat" id="scan-etat" hidden></div>
            <div class="calc-hint" id="scan-manuel">Pas de justificatif ? Remplissez directement les champs ci-dessous.</div>
          </div>
        </div>
        <div class="ndf-section">
          <div class="ndf-section-titre">Le frais</div>
          <div class="field"><label>Catégorie</label>
            <select name="categorie_id" id="ndf-cats" required>
              <option value="">Choisir…</option>
              ${NDF_CATS.map(c=>`<option value="${c.id}">${esc(c.libelle)}</option>`).join('')}
            </select>
          </div>
          <div class="row2">
            <div class="field"><label>Date du frais</label><input type="date" name="date_frais" value="${today}" required></div>
            <div class="field"><label>Ville</label><input type="text" name="ville" maxlength="80" placeholder="ex. Lyon"></div>
          </div>
        </div>
        <div class="ndf-section montants">
          <div class="ndf-section-titre">Montant</div>
          <div id="ndf-montant-zone">
            <div class="row3">
              <div class="field"><label>Montant TTC (€)</label><input type="number" step="0.01" min="0.01" name="montant_ttc" id="ndf-ttc" placeholder="0,00"></div>
              <div class="field"><label>Taux de TVA</label>
                <select name="taux_tva" id="ndf-taux">${NDF_TAUX.map(t=>`<option value="${t}">${t?fmtTaux(t):'Sans TVA'}</option>`).join('')}</select>
              </div>
              <div class="field"><label>TVA (€)</label><input type="number" step="0.01" min="0" name="montant_tva" id="ndf-tva" placeholder="0,00"></div>
            </div>
            <div class="ndf-ht">Soit <span id="ndf-ht">0,00 €</span> HT · la TVA se corrige à la main pour un ticket à plusieurs taux.</div>
          </div>
          <div id="ndf-km-zone" style="display:none">
            <div class="row2">
              <div class="field"><label>Distance (km)</label><input type="number" step="0.1" min="0.1" name="distance_km" id="ndf-km" placeholder="0"></div>
              <div class="field"><label>Montant</label><div class="ndf-calcule" id="ndf-km-total">0,00 €</div>
                <div class="calc-hint" id="ndf-km-hint"></div></div>
            </div>
          </div>
        </div>
        <div class="ndf-section">
          <div class="ndf-section-titre">Détails</div>
          <div class="field"><label>Description</label><textarea name="description" placeholder="Détails, contexte, participants…" maxlength="1000"></textarea></div>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" id="ndf-cancel">Annuler</button>
        <span class="sep"></span>
        <button type="submit" class="btn ghost" name="soumettre" value="0">${edite?'Enregistrer':'Enregistrer brouillon'}</button>
        <button type="submit" class="btn" name="soumettre" value="1">Soumettre à la compta</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(back);
  const $=s=>back.querySelector(s);
  const form=$('#ndf-form');
  const catsEl=$('#ndf-cats'),ttcEl=$('#ndf-ttc'),tauxEl=$('#ndf-taux'),tvaEl=$('#ndf-tva'),kmEl=$('#ndf-km');
  let tvaManuelle=false;
  const catCourante=()=>NDF_CATS.find(c=>String(c.id)===catsEl.value)||null;
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
  if(edite){
    form.elements.date_frais.value=(edite.date_frais||'').slice(0,10);
    form.elements.ville.value=edite.ville||'';
    form.elements.description.value=edite.description||'';
    if(NDF_CATS.some(c=>c.id===edite.categorie_id))catsEl.value=String(edite.categorie_id);
    const cat=catCourante();
    if(cat&&cat.saisie==='km'){kmEl.value=edite.distance_km!=null?edite.distance_km:'';}
    else{
      ttcEl.value=edite.montant_ttc!=null?Number(edite.montant_ttc).toFixed(2):'';
      tauxEl.value=String(edite.taux_tva!=null?edite.taux_tva:(cat?cat.taux_tva:20));
      if(edite.montant_tva!=null){
        const calc=ndfCalcul(cat,Number(edite.montant_ttc)||0,parseFloat(tauxEl.value)||0,0);
        tvaEl.value=Number(edite.montant_tva).toFixed(2);
        tvaManuelle=Math.abs(calc.tva-Number(edite.montant_tva))>0.005;
      }
    }
  }
  majCalcul();
  // ── Justificatif et lecture automatique (POST /api/coffre/notes-frais/scan) ──
  const fileEl=$('#ndf-file');
  const photoEl=$('#ndf-photo');
  // Fichier retenu, d'où qu'il vienne (sélecteur, appareil photo, dépôt).
  let justif=null;
  const dropLbl=$('#drop-label');
  const dropTxt=$('#drop-txt');
  const scanEtat=$('#scan-etat');
  const boutons=[...back.querySelectorAll('button[type=submit]')];
  // Champs touchés à la main : la lecture ne les écrase jamais.
  const manuels=new Set();
  form.addEventListener('input',e=>{const n=e.target.name;if(n){manuels.add(n);marquerLu(e.target,false);}});
  form.addEventListener('change',e=>{const n=e.target.name;if(n&&e.isTrusted){manuels.add(n);marquerLu(e.target,false);}});
  function marquerLu(el,oui){
    const lbl=el&&el.closest('.field')&&el.closest('.field').querySelector('label');
    if(!lbl)return;
    let m=lbl.querySelector('.lu');
    if(oui&&!m){m=document.createElement('span');m.className='lu';m.textContent='lu';m.title='Lu sur le justificatif : vérifiez';lbl.appendChild(m);}
    if(!oui&&m)m.remove();
  }
  function etat(texte,type){
    scanEtat.hidden=!texte;scanEtat.className='scan-etat'+(type?' '+type:'');scanEtat.textContent=texte||'';
  }
  function poser(nom,valeur){
    const el=form.elements[nom];
    if(!el||valeur==null||manuels.has(nom))return false;
    el.value=String(valeur);marquerLu(el,true);return true;
  }
  async function lire(fichier){
    const cat=catCourante();
    if(cat&&cat.saisie==='km')return;
    etat('Lecture du justificatif…','encours');
    boutons.forEach(b=>b.disabled=true);
    try{
      const fd=new FormData();fd.append('justificatif',fichier);
      const r=await fetch('/api/coffre/notes-frais/scan',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Lecture impossible — complétez à la main.';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      const j=await r.json();
      if(justif!==fichier)return;
      if(!j.ok){etat(j.erreur||'Lecture impossible — complétez à la main.','err');return;}
      const c=j.champs||{};
      if(c.categorie_id!=null&&!manuels.has('categorie_id')&&NDF_CATS.some(x=>x.id===c.categorie_id)){
        catsEl.value=String(c.categorie_id);marquerLu(catsEl,true);
        const cc=catCourante();if(cc&&cc.saisie!=='km'&&!manuels.has('taux_tva'))tauxEl.value=String(cc.taux_tva);
      }
      if(c.taux_tva!=null)poser('taux_tva',c.taux_tva);
      if(c.montant_ttc!=null)poser('montant_ttc',Number(c.montant_ttc).toFixed(2));
      if(c.montant_tva!=null&&poser('montant_tva',Number(c.montant_tva).toFixed(2)))tvaManuelle=true;
      else if(!manuels.has('montant_tva'))tvaManuelle=false;
      poser('date_frais',c.date_frais);
      poser('ville',c.ville);
      if(c.description&&!form.elements.description.value.trim())poser('description',c.description);
      majCalcul();
      etat(j.remarque?'Justificatif lu. '+j.remarque+' Vérifiez avant d\'envoyer.':'Justificatif lu — vérifiez les champs avant d\'envoyer.','ok');
    }catch(e){etat(e.message,'err');}
    finally{boutons.forEach(b=>b.disabled=false);}
  }
  // Vignette du justificatif : le fichier qu'on vient de choisir, sinon celui
  // déjà joint au brouillon. « Voir » l'ouvre en grand par-dessus le formulaire.
  let urlLocale=null;
  function majApercu(){
    const zone=$('#justif-apercu');
    if(urlLocale){URL.revokeObjectURL(urlLocale);urlLocale=null;}
    const f=justif;
    zone.innerHTML='';
    if(f){
      urlLocale=URL.createObjectURL(f);
      const image=(f.type||'').startsWith('image/');
      zone.innerHTML=(image?`<img alt="" src="${esc(urlLocale)}">`:'<div class="justif-doc">PDF</div>')+
        `<div class="justif-nom"><strong></strong><span>Nouveau justificatif</span></div>`+
        `<button type="button" class="btn ghost small" id="justif-voir">Voir</button>`;
      zone.querySelector('strong').textContent=f.name;
      zone.querySelector('#justif-voir').onclick=()=>previewDocument(urlLocale,f.name,true);
      zone.hidden=false;
    }else if(edite&&edite.justificatif_nom){
      const url='/api/coffre/notes-frais/'+edite.id+'/justificatif';
      const image=PREVIEW_IMG_RE.test(edite.justificatif_nom);
      zone.innerHTML=(image?`<img alt="" src="${esc(url)}?inline=1">`:'<div class="justif-doc">PDF</div>')+
        `<div class="justif-nom"><strong></strong><span>Justificatif joint</span></div>`+
        `<button type="button" class="btn ghost small" data-preview-url="${esc(url)}" data-preview-name="${esc(edite.justificatif_nom)}">Voir</button>`;
      zone.querySelector('strong').textContent=edite.justificatif_nom;
      zone.hidden=false;
    }else zone.hidden=true;
  }
  function texteZone(){
    if(justif)return 'Remplacer le justificatif';
    if(edite&&edite.justificatif_nom)return 'Remplacer le justificatif joint';
    return tactile?'Photographiez le ticket':'Déposez le justificatif ici ou cliquez pour le choisir';
  }
  function fichierChoisi(f){
    justif=f||null;
    majApercu();
    dropTxt.textContent=texteZone();
    dropLbl.classList.toggle('has-file',!!justif);
    $('#scan-manuel').hidden=!!justif;
    if(justif)lire(justif);else etat('');
  }
  dropTxt.textContent=texteZone();
  fileEl.addEventListener('change',e=>{e.stopPropagation();if(fileEl.files[0])fichierChoisi(fileEl.files[0]);fileEl.value='';});
  photoEl.addEventListener('change',e=>{e.stopPropagation();if(photoEl.files[0])fichierChoisi(photoEl.files[0]);photoEl.value='';});
  $('#btn-photo').onclick=e=>{e.stopPropagation();photoEl.click();};
  $('#btn-fichier').onclick=e=>{e.stopPropagation();fileEl.click();};
  // Sur ordinateur, toute la zone ouvre le sélecteur ; sur téléphone, les deux boutons.
  dropLbl.addEventListener('click',()=>{if(!tactile)fileEl.click();});
  dropLbl.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fileEl.click();}});
  ['dragenter','dragover'].forEach(ev=>dropLbl.addEventListener(ev,e=>{e.preventDefault();dropLbl.classList.add('survol');}));
  ['dragleave','drop'].forEach(ev=>dropLbl.addEventListener(ev,e=>{e.preventDefault();dropLbl.classList.remove('survol');}));
  dropLbl.addEventListener('drop',e=>{
    if(e.dataTransfer&&e.dataTransfer.files.length)fichierChoisi(e.dataTransfer.files[0]);
  });
  majApercu();
  const fermer=(technique)=>{
    if(urlLocale)URL.revokeObjectURL(urlLocale);
    back.remove();
    if(edite&&NDF_EDITION&&NDF_EDITION.id===edite.id){NDF_EDITION=null;if(technique!==true)coffreSyncUrl();}
  };
  if(edite){NDF_EDITION={id:edite.id,fermer};coffreSyncUrl();}
  $('#ndf-cancel').onclick=()=>fermer();
  back.onclick=(e)=>{if(e.target===back)fermer();};
  form.addEventListener('submit',async(e)=>{
    e.preventDefault();
    const btn=e.submitter;
    const fd=new FormData(form);
    fd.set('soumettre',btn && btn.value==='1'?'1':'0');
    if(justif)fd.set('justificatif',justif,justif.name||'justificatif.jpg');
    const cat=catCourante();
    if(cat&&cat.saisie==='km'){fd.delete('montant_ttc');fd.delete('montant_tva');fd.delete('taux_tva');}
    else fd.delete('distance_km');
    try{
      const r=await fetch(edite?'/api/coffre/notes-frais/'+edite.id:'/api/coffre/notes-frais',{method:edite?'PUT':'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      toast(btn.value==='1'?'Note soumise.':'Brouillon enregistré.');
      fermer();
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
  loadDocs();
  await Promise.all([loadBulletins(),loadNdf(),loadNdfCategories()]);
  await coffreDemarrerUrl();
})();
</script>
<script src="/static/mysifa_cal_rappel.js?v=9"></script>
</body>
</html>
"""
