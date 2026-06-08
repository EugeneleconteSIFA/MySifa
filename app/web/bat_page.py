"""MySifa — Page MyBAT (Bons À Tirer)
Route : /bat
Accès : superadmin, direction, administration
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user
from app.web.access_denied import access_denied_response
from config import APP_VERSION

ROLES_BAT = {"superadmin", "direction", "administration"}

router = APIRouter()


@router.get("/bat", response_class=HTMLResponse)
def bat_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/bat", status_code=302)
        raise
    if user["role"] not in ROLES_BAT:
        return access_denied_response("MyBAT")
    html = BAT_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


BAT_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>MyBAT — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="apple-touch-icon" href="/static/mys_icon_180.png">
<link rel="stylesheet" href="/static/support_widget.css">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_dock.css">
<link rel="stylesheet" href="/static/mysifa_ai_chat.css">
<link rel="stylesheet" href="/static/mysifa_postit.css">
<script>try{if(localStorage.getItem('mysifa_theme')==='light')document.documentElement.classList.add('light-pre');}catch(e){}</script>
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.10);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;--success:#34d399;
  --sidebar-w:220px;
}
html.light-pre body,body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.08);
  --ok:#059669;--danger:#dc2626;--warn:#d97706;
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* ── Layout ── */
.app{display:flex;height:100vh;overflow:hidden}
.sidebar{width:var(--sidebar-w);background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;overflow-y:auto}
.sidebar::-webkit-scrollbar{width:0}.sidebar{scrollbar-width:none}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
@media(max-width:768px){
  .sidebar{position:fixed;left:0;top:0;bottom:0;z-index:9000;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 16px 48px rgba(0,0,0,.55)}
  body.sb-open .sidebar{transform:translateX(0)}
  .sidebar-overlay{z-index:8999}
  body.sb-open .sidebar-overlay{display:block}
  .main{height:100vh;overflow-y:auto}
}
.main{flex:1;overflow-y:auto;display:flex;flex-direction:column}

/* ── Sidebar elements ── */
.logo{padding:0 8px;margin-bottom:28px}
.logo-brand{font-size:15px;font-weight:800}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-btn{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);cursor:pointer;font-size:13px;font-weight:500;width:100%;text-align:left;font-family:inherit;transition:all .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-btn--mysifa-portal{align-items:baseline;flex-wrap:wrap;gap:4px 8px;line-height:1.35}
.nav-btn--mysifa-portal:hover{background:var(--accent-bg)}
.mysifa-back-preamble{font-size:13px;font-weight:500;color:var(--text2)}
.mysifa-back-brand{font-size:14px;font-weight:800;letter-spacing:-.5px;color:var(--text);white-space:nowrap}
.mysifa-back-accent{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;border:1px solid var(--border);cursor:pointer;transition:.15s;background:transparent}
.user-chip:hover{border-color:var(--accent)}
.uc-name{font-size:13px;font-weight:600;color:var(--text)}
.uc-role{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
.theme-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit;transition:.15s;width:100%}
.theme-btn:hover{border-color:var(--accent);color:var(--accent)}
.logout-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px;font-family:inherit;transition:.15s;width:100%}
.logout-btn:hover{border-color:var(--danger);color:var(--danger)}
.version{font-size:10px;color:var(--muted);padding:4px 12px;font-family:ui-monospace,monospace;opacity:.6}

/* ── Mobile topbar ── */
.mobile-topbar{display:none;align-items:center;gap:12px;padding:14px 16px;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
@media(max-width:768px){.mobile-topbar{display:flex}}
.mobile-menu-btn{background:none;border:none;color:var(--text2);cursor:pointer;padding:4px;border-radius:6px;display:flex;align-items:center;justify-content:center}
.mobile-topbar-title{font-size:14px;font-weight:700;color:var(--text)}
.mobile-topbar-sub{font-size:11px;color:var(--muted)}
.mobile-home-btn{margin-left:auto;background:none;border:none;color:var(--muted);cursor:pointer;font-size:20px;padding:4px;border-radius:6px;transition:.15s}
.mobile-home-btn:hover{color:var(--accent)}

/* ── Content ── */
.content{padding:28px 32px;max-width:1280px;width:100%}
@media(max-width:768px){.content{padding:16px}}

/* ── Page header ── */
.page-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:28px;flex-wrap:wrap}
.page-title{font-size:22px;font-weight:800;letter-spacing:-.5px}
.page-title span{color:var(--accent)}
.page-subtitle{font-size:13px;color:var(--muted);margin-top:3px}

/* ── Boutons ── */
.btn{display:inline-flex;align-items:center;gap:7px;padding:10px 18px;border-radius:10px;border:none;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.btn:hover{filter:brightness(1.08)}
.btn-accent{background:var(--accent);color:#0a0e17}
.btn-danger{background:var(--danger);color:#fff}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn-sm{padding:6px 13px;font-size:12px;border-radius:8px}

/* ── Searchbar + filtres ── */
.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:20px;flex-wrap:wrap}
.search-wrap{position:relative;flex:1;min-width:200px}
.search-input{width:100%;padding:10px 14px 10px 38px;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.search-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.10)}
.search-ico{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}

/* ── Status tabs ── */
.stat-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:20px}
.stat-tab{padding:7px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s;display:inline-flex;align-items:center;gap:6px}
.stat-tab:hover{border-color:var(--accent);color:var(--accent)}
.stat-tab.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.stat-count{background:var(--border);color:var(--muted);border-radius:999px;padding:1px 7px;font-size:11px;font-weight:700}
.stat-tab.active .stat-count{background:var(--accent);color:#0a0e17}

/* ── Table ── */
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.table-wrap table{width:100%;border-collapse:collapse}
.table-wrap th{padding:11px 16px;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap}
.table-wrap td{padding:13px 16px;font-size:13px;border-bottom:1px solid var(--border);vertical-align:middle}
.table-wrap tr:last-child td{border-bottom:none}
.table-wrap tr:hover td{background:rgba(255,255,255,.02)}
body.light .table-wrap tr:hover td{background:rgba(0,0,0,.02)}

/* ── Badges statut ── */
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.2px}
.badge-afaire{background:rgba(251,191,36,.14);color:var(--warn)}
.badge-attente{background:rgba(34,211,238,.12);color:var(--accent)}
.badge-valide{background:rgba(52,211,153,.12);color:var(--ok)}
.badge-clickable{cursor:pointer;transition:filter .15s}
.badge-clickable:hover{filter:brightness(1.2)}

/* ── Action group ── */
.action-group{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ico-btn{background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;border-radius:7px;padding:5px 8px;font-size:12px;display:inline-flex;align-items:center;gap:5px;font-family:inherit;transition:.15s}
.ico-btn:hover{border-color:var(--accent);color:var(--accent)}
.ico-btn.danger:hover{border-color:var(--danger);color:var(--danger)}
.ico-btn.ok:hover{border-color:var(--ok);color:var(--ok)}

/* ── Empty state ── */
.empty{text-align:center;padding:60px 20px;color:var(--muted)}
.empty-icon{font-size:40px;margin-bottom:12px;opacity:.5}
.empty-title{font-size:15px;font-weight:600;color:var(--text2);margin-bottom:6px}
.empty-sub{font-size:12px}

/* ── Modal overlay ── */
.modal-ov{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px 28px 24px;width:100%;max-width:460px;position:relative;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.modal-close{position:absolute;top:16px;right:16px;background:none;border:none;color:var(--muted);cursor:pointer;font-size:22px;line-height:1;padding:4px;border-radius:6px;transition:.15s}
.modal-close:hover{color:var(--danger)}
.modal-title{font-size:16px;font-weight:700;margin-bottom:20px}
.form-label{display:block;font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.form-input{width:100%;padding:11px 14px;background:var(--bg);border:1.5px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.form-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.10)}
.form-group{margin-bottom:16px}
.form-hint{font-size:11px;color:var(--muted);margin-top:5px}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:22px}
.form-select{width:100%;padding:11px 14px;background:var(--bg);border:1.5px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s;cursor:pointer;appearance:none;-webkit-appearance:none}
.form-select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.10)}

/* ── Upload zone ── */
.upload-zone{border:2px dashed var(--border);border-radius:10px;padding:28px 20px;text-align:center;cursor:pointer;transition:.15s;color:var(--muted)}
.upload-zone:hover,.upload-zone.drag{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.upload-zone input{display:none}
.upload-zone-label{font-size:13px;margin-top:8px}
.upload-zone-sub{font-size:11px;margin-top:4px;opacity:.7}
.upload-progress{font-size:12px;color:var(--accent);margin-top:10px;display:none}

/* ── Statut modal ── */
.statut-options{display:flex;flex-direction:column;gap:8px;margin-top:4px}
.statut-opt{display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:10px;border:1.5px solid var(--border);cursor:pointer;transition:.15s;background:transparent;width:100%;font-family:inherit;text-align:left}
.statut-opt:not([disabled]):hover{border-color:var(--accent);background:var(--accent-bg)}
.statut-opt[disabled]{opacity:.38;cursor:not-allowed}
.statut-opt.current{border-color:var(--accent);background:var(--accent-bg)}
.statut-opt-label{font-size:13px;font-weight:600;color:var(--text)}
.statut-opt-sub{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Toast ── */
.toast-wrap{position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:8px;z-index:2000}
.toast{padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 4px 24px rgba(0,0,0,.4);max-width:340px;animation:toastIn .2s ease}
@keyframes toastIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.toast.success{background:#064e3b;color:var(--ok);border:1px solid var(--ok)}
.toast.danger{background:#450a0a;color:var(--danger);border:1px solid var(--danger)}
.toast.info{background:var(--card);color:var(--text2);border:1px solid var(--border)}
body.light .toast.success{background:#d1fae5;color:#065f46}
body.light .toast.danger{background:#fee2e2;color:#991b1b}
body.light .toast.info{background:#f1f5f9;color:var(--text)}
</style>
</head>
<body>
<div class="app">
  <!-- Sidebar overlay mobile -->
  <div class="sidebar-overlay" onclick="closeSidebar()"></div>

  <!-- Sidebar -->
  <nav class="sidebar" id="sidebar">
    <div class="logo">
      <div class="logo-brand">My<span>BAT</span></div>
      <div class="logo-sub">by SIFA</div>
    </div>
    <button type="button" class="nav-btn active">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
      BAT
    </button>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn nav-btn--mysifa-portal" onclick="location.href='/'">
        <span class="mysifa-back-preamble">← Retour </span>
        <span class="mysifa-back-brand">My<span class="mysifa-back-accent">Sifa</span></span>
      </button>
      <div class="user-chip" id="user-chip" onclick="location.href='/profil'"></div>
      <button type="button" class="theme-btn" onclick="toggleTheme()">
        <svg id="theme-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        <span id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" onclick="doLogout()">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">__V_LABEL__</div>
    </div>
  </nav>

  <!-- Main -->
  <main class="main">
    <!-- Mobile topbar -->
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="toggleSidebar()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">MyBAT</div>
        <div class="mobile-topbar-sub">Bons À Tirer</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'">⌂</button>
    </div>

    <div class="content">
      <!-- En-tête -->
      <div class="page-header">
        <div>
          <div class="page-title">My<span>BAT</span></div>
          <div class="page-subtitle">Gestion des Bons À Tirer</div>
        </div>
        <button type="button" class="btn btn-accent" onclick="openCreateModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Nouveau BAT
        </button>
      </div>

      <!-- Onglets statut -->
      <div class="stat-tabs" id="stat-tabs"></div>

      <!-- Barre de recherche -->
      <div class="toolbar">
        <div class="search-wrap">
          <span class="search-ico">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </span>
          <input
            type="text"
            id="search-input"
            class="search-input"
            placeholder="Rechercher (description, article, notes…)"
            oninput="onSearch(this.value)"
            onkeydown="if(event.key==='Escape'){this.value='';onSearch('');}"
          >
        </div>
      </div>

      <!-- Table -->
      <div class="table-wrap" id="table-wrap"></div>
    </div>
  </main>
</div>

<!-- Modal création -->
<div class="modal-ov" id="create-modal" style="display:none" onclick="if(event.target===this)closeCreateModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeCreateModal()">×</button>
    <div class="modal-title">Nouveau BAT</div>
    <div class="form-group">
      <label class="form-label" for="inp-desc">Description</label>
      <input type="text" class="form-input" id="inp-desc" placeholder="ex : Etiquette boîte conserve client XYZ" autocomplete="off">
    </div>
    <div class="form-group">
      <label class="form-label" for="inp-article">Numéro article</label>
      <input type="text" class="form-input" id="inp-article" placeholder="ex : ART-2024-001" autocomplete="off">
    </div>
    <div class="form-group">
      <label class="form-label" for="inp-delai">Délai client (facultatif)</label>
      <input type="date" class="form-input" id="inp-delai">
    </div>
    <div class="form-group">
      <label class="form-label" for="inp-notes">Notes (facultatif)</label>
      <textarea class="form-input" id="inp-notes" rows="2" placeholder="Informations complémentaires…" style="resize:vertical"></textarea>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeCreateModal()">Annuler</button>
      <button type="button" class="btn btn-accent" id="create-btn" onclick="submitCreate()">Créer le BAT</button>
    </div>
  </div>
</div>

<!-- Modal upload PDF -->
<div class="modal-ov" id="upload-modal" style="display:none" onclick="if(event.target===this)closeUploadModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeUploadModal()">×</button>
    <div class="modal-title" id="upload-modal-title">Ajouter un PDF</div>
    <label class="upload-zone" id="upload-zone" for="file-input" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin:0 auto"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      <div class="upload-zone-label" id="upload-zone-label">Glisser-déposer un PDF ici, ou cliquer pour choisir</div>
      <div class="upload-zone-sub">Fichier PDF uniquement</div>
      <input type="file" id="file-input" accept=".pdf" onchange="onFileSelected(this)">
    </label>
    <div class="upload-progress" id="upload-progress">Import en cours…</div>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeUploadModal()">Annuler</button>
      <button type="button" class="btn btn-accent" id="upload-btn" onclick="submitUpload()" disabled>Importer</button>
    </div>
  </div>
</div>

<!-- Modal édition (description + article + délai + notes) -->
<div class="modal-ov" id="edit-modal" style="display:none" onclick="if(event.target===this)closeEditModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeEditModal()">×</button>
    <div class="modal-title" id="edit-modal-title">Modifier le BAT</div>
    <div class="form-group">
      <label class="form-label" for="edit-desc">Description</label>
      <input type="text" class="form-input" id="edit-desc" autocomplete="off">
    </div>
    <div class="form-group">
      <label class="form-label" for="edit-article">Numéro article</label>
      <input type="text" class="form-input" id="edit-article" autocomplete="off">
    </div>
    <div class="form-group">
      <label class="form-label" for="edit-delai">Délai client</label>
      <input type="date" class="form-input" id="edit-delai">
    </div>
    <div class="form-group">
      <label class="form-label" for="edit-notes">Notes</label>
      <textarea class="form-input" id="edit-notes" rows="2" style="resize:vertical"></textarea>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeEditModal()">Annuler</button>
      <button type="button" class="btn btn-accent" onclick="submitEdit()">Enregistrer</button>
    </div>
  </div>
</div>

<!-- Modal changement de statut -->
<div class="modal-ov" id="statut-modal" style="display:none" onclick="if(event.target===this)closeStatutModal()">
  <div class="modal" onclick="event.stopPropagation()" style="max-width:380px">
    <button type="button" class="modal-close" onclick="closeStatutModal()">×</button>
    <div class="modal-title" id="statut-modal-title">Changer le statut</div>
    <div class="statut-options" id="statut-options"></div>
    <div class="modal-actions" style="margin-top:18px">
      <button type="button" class="btn btn-ghost" onclick="closeStatutModal()">Annuler</button>
    </div>
  </div>
</div>

<!-- Modal suppression -->
<div class="modal-ov" id="del-modal" style="display:none" onclick="if(event.target===this)closeDelModal()">
  <div class="modal" onclick="event.stopPropagation()" style="max-width:380px">
    <button type="button" class="modal-close" onclick="closeDelModal()">×</button>
    <div class="modal-title">Supprimer ce BAT ?</div>
    <p id="del-modal-msg" style="font-size:13px;color:var(--text2);line-height:1.6"></p>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeDelModal()">Annuler</button>
      <button type="button" class="btn btn-danger" onclick="submitDelete()">Supprimer</button>
    </div>
  </div>
</div>

<!-- Modal PDF picker -->
<div class="modal-ov" id="pdf-picker-modal" style="display:none" onclick="if(event.target===this)closePdfPicker()">
  <div class="modal" onclick="event.stopPropagation()" style="max-width:500px">
    <button type="button" class="modal-close" onclick="closePdfPicker()">×</button>
    <div class="modal-title" id="pdf-picker-title">Fichiers PDF</div>
    <div id="pdf-picker-list"></div>
    <div class="modal-actions" style="margin-top:18px">
      <button type="button" class="btn btn-ghost btn-sm" onclick="openUploadFromPicker()">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Ajouter un PDF
      </button>
      <button type="button" class="btn btn-ghost" onclick="closePdfPicker()">Fermer</button>
    </div>
  </div>
</div>

<!-- Modal confirmation suppression PDF -->
<div class="modal-ov" id="pdf-del-modal" style="display:none" onclick="if(event.target===this)closePdfDelModal()">
  <div class="modal" onclick="event.stopPropagation()" style="max-width:380px">
    <button type="button" class="modal-close" onclick="closePdfDelModal()">×</button>
    <div class="modal-title">Supprimer ce PDF ?</div>
    <p id="pdf-del-modal-msg" style="font-size:13px;color:var(--text2);line-height:1.6"></p>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closePdfDelModal()">Annuler</button>
      <button type="button" class="btn btn-danger" onclick="submitPdfDelete()">Supprimer</button>
    </div>
  </div>
</div>

<!-- Toasts -->
<div class="toast-wrap" id="toast-wrap"></div>

<script>
'use strict';

// ── État central ───────────────────────────────────────────────────
const S = {
  entries: [],
  statut: 'all',
  search: '',
  me: null,
  uploadBatId: null,
  uploadFile: null,
  editBatId: null,
  statutBatId: null,
  delBatId: null,
  pdfPickerBatId: null,
  pdfDelId: null,
};

// ── Utilitaires ───────────────────────────────────────────────────
function escHtml(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

async function api(path, opts={}){
  const r=await fetch(path,{credentials:'include',...opts});
  if(r.status===401){location.href='/?next=/bat';throw new Error('unauth');}
  return r;
}

function showToast(msg, type='info'){
  const wrap=document.getElementById('toast-wrap');
  const el=document.createElement('div');
  el.className=`toast ${type}`;
  el.textContent=msg;
  wrap.appendChild(el);
  setTimeout(()=>el.remove(),3500);
}

function toggleSidebar(){document.body.classList.toggle('sb-open');}
function closeSidebar(){document.body.classList.remove('sb-open');}

function toggleTheme(){
  const l=document.body.classList.toggle('light');
  document.documentElement.classList.toggle('light-pre', l);
  try{localStorage.setItem('mysifa_theme',l?'light':'dark');}catch(e){}
  updateThemeBtn();
}
function updateThemeBtn(){
  const l=document.body.classList.contains('light');
  const ico=document.getElementById('theme-ico');
  const lbl=document.getElementById('theme-label');
  if(ico){
    ico.innerHTML=l
      ?'<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
      :'<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
  }
  if(lbl) lbl.textContent=l?'Mode clair':'Mode sombre';
}

async function doLogout(){
  try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(e){}
  location.href='/';
}

// ── Badges ────────────────────────────────────────────────────────
function statutLabel(s){return{a_faire:'À faire',en_attente:'En attente',valide:'Validé'}[s]||s;}
function statutBadge(e){
  const cls={a_faire:'badge-afaire',en_attente:'badge-attente',valide:'badge-valide'}[e.statut]||'';
  return `<span class="badge ${cls} badge-clickable" onclick="openStatutModal(${e.id})" title="Cliquer pour modifier le statut">${escHtml(statutLabel(e.statut))}</span>`;
}

// ── Filtrage ──────────────────────────────────────────────────────
function filteredEntries(){
  let list=S.entries;
  if(S.statut!=='all') list=list.filter(e=>e.statut===S.statut);
  if(S.search.trim()){
    const q=S.search.trim().toLowerCase();
    list=list.filter(e=>(
      (e.description||'').toLowerCase().includes(q)||
      (e.numero_article||'').toLowerCase().includes(q)||
      (e.reference||'').toLowerCase().includes(q)||
      (e.notes||'').toLowerCase().includes(q)
    ));
  }
  return list;
}

// ── Formatage date ─────────────────────────────────────────────────
function fmtDate(s){
  if(!s) return '—';
  // YYYY-MM-DD → JJ/MM/AAAA
  const m=s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(m) return `${m[3]}/${m[2]}/${m[1]}`;
  return s.slice(0,10);
}

// ── Rendu ─────────────────────────────────────────────────────────
function renderTabs(){
  const all=S.entries.length;
  const counts={a_faire:0,en_attente:0,valide:0};
  S.entries.forEach(e=>{if(counts[e.statut]!==undefined)counts[e.statut]++;});
  const tabs=[
    {key:'all',label:'Tous',count:all},
    {key:'a_faire',label:'À faire',count:counts.a_faire},
    {key:'en_attente',label:'En attente',count:counts.en_attente},
    {key:'valide',label:'Validé',count:counts.valide},
  ];
  const wrap=document.getElementById('stat-tabs');
  wrap.innerHTML=tabs.map(t=>`
    <button type="button" class="stat-tab${S.statut===t.key?' active':''}" onclick="setStatut('${t.key}')">
      ${escHtml(t.label)}<span class="stat-count">${t.count}</span>
    </button>`).join('');
}

function renderTable(){
  const ae=document.activeElement;
  const focusId=ae?.id;
  const cs=ae?.selectionStart;
  const ce=ae?.selectionEnd;

  const list=filteredEntries();
  const wrap=document.getElementById('table-wrap');

  if(!list.length){
    wrap.innerHTML=`<div class="empty">
      <div class="empty-icon">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
      </div>
      <div class="empty-title">${S.search?'Aucun résultat pour « '+escHtml(S.search)+' »':'Aucun BAT'}</div>
      <div class="empty-sub">${!S.search&&S.statut==='all'?'Créez votre premier BAT avec le bouton ci-dessus.':''}</div>
    </div>`;
  } else {
    const rows=list.map(e=>{
      const pdfLabel = e.pdf_count > 1 ? 'multi PDFs' : 'PDF';
      const pdfBtn=e.has_pdf
        ?`<button type="button" class="ico-btn ok" onclick="openPdfPicker(${e.id})" title="Voir les PDF (${e.pdf_count})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            ${pdfLabel}
          </button>`
        :'';
      const uploadBtn=`<button type="button" class="ico-btn" onclick="openUploadModal(${e.id},'${escHtml(e.reference)}')" title="Ajouter un PDF">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          + PDF
        </button>`;
      const editBtn=`<button type="button" class="ico-btn" onclick="openEditModal(${e.id})" title="Modifier">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>`;
      const delBtn=`<button type="button" class="ico-btn danger" onclick="openDelModal(${e.id},'${escHtml(e.description||e.numero_article)}')" title="Supprimer">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        </button>`;
      const updDate=e.updated_at?e.updated_at.slice(0,16).replace('T',' '):'—';
      const notesCell=e.notes?`<span title="${escHtml(e.notes)}" style="color:var(--text2);max-width:160px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(e.notes)}</span>`:'<span style="color:var(--muted)">—</span>';
      const descCell=`<span style="font-weight:600;max-width:220px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escHtml(e.description||'')}">${escHtml(e.description||'—')}</span>`;
      const delaiCell=e.delai_client?`<span style="font-family:ui-monospace,monospace;font-size:12px;color:var(--text2)">${escHtml(fmtDate(e.delai_client))}</span>`:'<span style="color:var(--muted)">—</span>';
      return `<tr>
        <td>${descCell}</td>
        <td><span style="font-weight:700;font-family:ui-monospace,monospace;font-size:12px;color:var(--accent)">${escHtml(e.numero_article)}</span></td>
        <td>${statutBadge(e)}</td>
        <td>${delaiCell}</td>
        <td>${notesCell}</td>
        <td style="color:var(--muted);font-size:12px;white-space:nowrap">${escHtml(updDate)}</td>
        <td>
          <div class="action-group">
            ${pdfBtn}
            ${uploadBtn}
            ${editBtn}
            ${delBtn}
          </div>
        </td>
      </tr>`;
    }).join('');
    wrap.innerHTML=`<table>
      <thead><tr>
        <th>Description</th><th>N° Article</th><th>Statut</th><th>Délai client</th><th>Notes</th><th>Mise à jour</th><th>Actions</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  if(focusId){
    const el=document.getElementById(focusId);
    if(el){el.focus();if(cs!=null){try{el.setSelectionRange(cs,ce);}catch(e){}}}
  }
}

function render(){
  renderTabs();
  renderTable();
}

function setStatut(s){S.statut=s;render();}
function onSearch(v){S.search=v;render();}

// ── Chargement ────────────────────────────────────────────────────
async function loadEntries(){
  try{
    const r=await api('/api/bat');
    if(!r.ok){showToast('Erreur de chargement','danger');return;}
    S.entries=await r.json();
    render();
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

async function loadMe(){
  try{
    const r=await fetch('/api/auth/me',{credentials:'include'});
    if(!r.ok) return;
    const d=await r.json();
    S.me=d.user||d;
    const chip=document.getElementById('user-chip');
    if(chip&&S.me){
      const roles={direction:'Direction',administration:'Administration',superadmin:'Super admin',fabrication:'Fabrication',logistique:'Logistique',comptabilite:'Comptabilité',expedition:'Expédition',commercial:'Commercial'};
      chip.innerHTML=`<div class="uc-name">${escHtml(S.me.nom||'')}</div><div class="uc-role">${escHtml(roles[S.me.role]||S.me.role||'')}</div>`;
    }
  }catch(e){}
}

// ── Modals — Création ──────────────────────────────────────────────
function openCreateModal(){
  document.getElementById('inp-desc').value='';
  document.getElementById('inp-article').value='';
  document.getElementById('inp-delai').value='';
  document.getElementById('inp-notes').value='';
  document.getElementById('create-modal').style.display='flex';
  requestAnimationFrame(()=>document.getElementById('inp-desc').focus());
}
function closeCreateModal(){document.getElementById('create-modal').style.display='none';}

async function submitCreate(){
  const desc=document.getElementById('inp-desc').value.trim();
  const article=document.getElementById('inp-article').value.trim();
  const delai=document.getElementById('inp-delai').value||null;
  const notes=document.getElementById('inp-notes').value.trim()||null;
  if(!desc||!article){showToast('Description et numéro article obligatoires','danger');return;}
  const btn=document.getElementById('create-btn');
  btn.disabled=true;btn.textContent='Création…';
  try{
    const r=await api('/api/bat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({description:desc,numero_article:article,delai_client:delai,notes})});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur lors de la création','danger');
    } else {
      const entry=await r.json();
      S.entries.unshift(entry);
      render();
      closeCreateModal();
      showToast(`BAT créé.`,'success');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
  btn.disabled=false;btn.textContent='Créer le BAT';
}

// ── Modals — Upload PDF ────────────────────────────────────────────
function openUploadModal(id,ref){
  S.uploadBatId=id;S.uploadFile=null;
  document.getElementById('upload-modal-title').textContent=ref?`Ajouter un PDF — ${ref}`:'Ajouter un PDF';
  document.getElementById('upload-zone-label').textContent='Glisser-déposer un PDF ici, ou cliquer pour choisir';
  document.getElementById('upload-zone').classList.remove('drag');
  document.getElementById('upload-btn').disabled=true;
  document.getElementById('upload-progress').style.display='none';
  document.getElementById('file-input').value='';
  document.getElementById('upload-modal').style.display='flex';
}
function closeUploadModal(){document.getElementById('upload-modal').style.display='none';S.uploadBatId=null;S.uploadFile=null;}

function onDragOver(e){e.preventDefault();document.getElementById('upload-zone').classList.add('drag');}
function onDragLeave(e){document.getElementById('upload-zone').classList.remove('drag');}
function onDrop(e){
  e.preventDefault();
  document.getElementById('upload-zone').classList.remove('drag');
  const f=e.dataTransfer.files[0];
  if(f&&f.name.toLowerCase().endsWith('.pdf')){setUploadFile(f);}
  else{showToast('Seuls les fichiers PDF sont acceptés','danger');}
}
function onFileSelected(inp){if(inp.files[0])setUploadFile(inp.files[0]);}
function setUploadFile(f){
  S.uploadFile=f;
  document.getElementById('upload-zone-label').textContent=f.name;
  document.getElementById('upload-btn').disabled=false;
}

async function submitUpload(){
  if(!S.uploadFile||!S.uploadBatId) return;
  const btn=document.getElementById('upload-btn');
  const prog=document.getElementById('upload-progress');
  btn.disabled=true;prog.style.display='block';
  const fd=new FormData();
  fd.append('file',S.uploadFile);
  try{
    const r=await fetch(`/api/bat/${S.uploadBatId}/upload`,{method:'POST',credentials:'include',body:fd});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||"Erreur lors de l'import",'danger');
    } else {
      const entry=await r.json();
      const idx=S.entries.findIndex(e=>e.id===entry.id);
      if(idx>=0)S.entries[idx]=entry; else S.entries.unshift(entry);
      render();
      closeUploadModal();
      showToast(`PDF ajouté${entry.pdf_count>1?' ('+entry.pdf_count+' PDFs)':''}.`,'success');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
  btn.disabled=false;prog.style.display='none';
}

// ── Modals — Édition ──────────────────────────────────────────────
function openEditModal(id){
  const e=S.entries.find(x=>x.id===id);
  if(!e) return;
  S.editBatId=id;
  document.getElementById('edit-modal-title').textContent=`Modifier — ${e.reference}`;
  document.getElementById('edit-desc').value=e.description||'';
  document.getElementById('edit-article').value=e.numero_article||'';
  document.getElementById('edit-delai').value=e.delai_client||'';
  document.getElementById('edit-notes').value=e.notes||'';
  document.getElementById('edit-modal').style.display='flex';
  requestAnimationFrame(()=>document.getElementById('edit-desc').focus());
}
function closeEditModal(){document.getElementById('edit-modal').style.display='none';S.editBatId=null;}

async function submitEdit(){
  if(!S.editBatId) return;
  const desc=document.getElementById('edit-desc').value.trim();
  const article=document.getElementById('edit-article').value.trim();
  const delai=document.getElementById('edit-delai').value||null;
  const notes=document.getElementById('edit-notes').value.trim()||null;
  if(!desc||!article){showToast('Description et numéro article obligatoires','danger');return;}
  try{
    const r=await api(`/api/bat/${S.editBatId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({description:desc,numero_article:article,delai_client:delai,notes})});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur de mise à jour','danger');
    } else {
      const entry=await r.json();
      const idx=S.entries.findIndex(e=>e.id===entry.id);
      if(idx>=0)S.entries[idx]=entry;
      render();
      closeEditModal();
      showToast('BAT mis à jour.','success');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Modals — Changement statut ────────────────────────────────────
function openStatutModal(id){
  const e=S.entries.find(x=>x.id===id);
  if(!e) return;
  S.statutBatId=id;

  document.getElementById('statut-modal-title').textContent=`Statut — ${e.description||e.numero_article}`;

  const opts=[
    {
      val:'a_faire',
      label:'À faire',
      sub:'BAT en attente de document.',
      disabled: e.statut==='a_faire',
    },
    {
      val:'en_attente',
      label:'En attente de validation',
      sub: e.has_pdf ? 'PDF présent — passage possible.' : 'Un PDF doit être importé au préalable.',
      disabled: !e.has_pdf || e.statut==='en_attente',
    },
    {
      val:'valide',
      label:'Validé',
      sub:'BAT approuvé définitivement.',
      disabled: e.statut==='valide',
    },
  ];

  const optHtml=opts.map(o=>`
    <button type="button" class="statut-opt${e.statut===o.val?' current':''}" ${o.disabled?'disabled':''} onclick="submitStatutChange('${o.val}')">
      <div style="flex:1">
        <div class="statut-opt-label">${escHtml(o.label)}</div>
        <div class="statut-opt-sub">${escHtml(o.sub)}</div>
      </div>
      ${e.statut===o.val?'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>':''}
    </button>`).join('');

  document.getElementById('statut-options').innerHTML=optHtml;
  document.getElementById('statut-modal').style.display='flex';
}
function closeStatutModal(){document.getElementById('statut-modal').style.display='none';S.statutBatId=null;}

async function submitStatutChange(newStatut){
  if(!S.statutBatId) return;
  const e=S.entries.find(x=>x.id===S.statutBatId);
  if(!e||e.statut===newStatut){closeStatutModal();return;}
  try{
    const r=await api(`/api/bat/${S.statutBatId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({statut:newStatut})});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur de mise à jour','danger');
    } else {
      const entry=await r.json();
      const idx=S.entries.findIndex(x=>x.id===entry.id);
      if(idx>=0)S.entries[idx]=entry;
      render();
      closeStatutModal();
      showToast(`Statut mis à jour : ${statutLabel(newStatut)}.`,'success');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Modals — Suppression ──────────────────────────────────────────
function openDelModal(id,ref){
  S.delBatId=id;
  document.getElementById('del-modal-msg').textContent=`Le BAT "${ref}" sera définitivement supprimé. Cette action est irréversible.`;
  document.getElementById('del-modal').style.display='flex';
}
function closeDelModal(){document.getElementById('del-modal').style.display='none';S.delBatId=null;}

async function submitDelete(){
  if(!S.delBatId) return;
  const id=S.delBatId;
  try{
    const r=await api(`/api/bat/${id}`,{method:'DELETE'});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur de suppression','danger');
    } else {
      S.entries=S.entries.filter(e=>e.id!==id);
      render();
      closeDelModal();
      showToast('BAT supprimé.','info');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── PDF Picker ────────────────────────────────────────────────────
function openPdfPicker(id){
  const e=S.entries.find(x=>x.id===id);
  if(!e) return;
  S.pdfPickerBatId=id;
  document.getElementById('pdf-picker-title').textContent=`PDF — ${e.reference}`;
  renderPdfPickerList(e);
  document.getElementById('pdf-picker-modal').style.display='flex';
}
function closePdfPicker(){
  document.getElementById('pdf-picker-modal').style.display='none';
  S.pdfPickerBatId=null;
}
function renderPdfPickerList(e){
  const list=e.pdfs||[];
  const el=document.getElementById('pdf-picker-list');
  if(!list.length){
    el.innerHTML='<div style="color:var(--muted);font-size:13px;padding:12px 0">Aucun PDF associé.</div>';
    return;
  }
  el.innerHTML=list.map(p=>{
    const dt=p.uploaded_at?p.uploaded_at.slice(0,16).replace('T',' '):'';
    return `<div style="display:flex;align-items:center;gap:10px;padding:11px 0;border-bottom:1px solid var(--border)">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <div style="flex:1;min-width:0">
        <div style="font-size:13px;font-weight:600;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escHtml(p.original_name)}">${escHtml(p.original_name)}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${escHtml(dt)}</div>
      </div>
      <a href="/api/bat/${e.id}/pdf/${p.id}" target="_blank" class="ico-btn ok btn-sm" style="text-decoration:none;flex-shrink:0">Ouvrir</a>
      <button type="button" class="ico-btn danger btn-sm" onclick="openPdfDelModal(${e.id},${p.id},'${escHtml(p.original_name)}')" title="Supprimer ce PDF" style="flex-shrink:0">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
      </button>
    </div>`;
  }).join('');
}
function openUploadFromPicker(){
  const id=S.pdfPickerBatId;
  if(!id) return;
  const e=S.entries.find(x=>x.id===id);
  closePdfPicker();
  openUploadModal(id, e?e.reference:'');
}

// ── PDF Delete (individuel) ───────────────────────────────────────
function openPdfDelModal(batId,pdfId,name){
  S.pdfPickerBatId=S.pdfPickerBatId||batId;
  S.pdfDelId={batId,pdfId};
  document.getElementById('pdf-del-modal-msg').textContent=`Le fichier "${name}" sera définitivement supprimé. Cette action est irréversible.`;
  document.getElementById('pdf-del-modal').style.display='flex';
}
function closePdfDelModal(){
  document.getElementById('pdf-del-modal').style.display='none';
  S.pdfDelId=null;
}
async function submitPdfDelete(){
  if(!S.pdfDelId) return;
  const {batId,pdfId}=S.pdfDelId;
  try{
    const r=await api(`/api/bat/${batId}/pdf/${pdfId}`,{method:'DELETE'});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur de suppression','danger');
    } else {
      // Mettre à jour l'entrée en mémoire
      const entry=S.entries.find(x=>x.id===batId);
      if(entry){
        entry.pdfs=(entry.pdfs||[]).filter(p=>p.id!==pdfId);
        entry.pdf_count=entry.pdfs.length;
        entry.has_pdf=entry.pdf_count>0;
      }
      render();
      closePdfDelModal();
      // Rouvrir le picker si l'entrée a encore des PDFs
      if(entry&&entry.pdf_count>0){
        S.pdfPickerBatId=batId;
        document.getElementById('pdf-picker-title').textContent=`PDF — ${entry.reference}`;
        renderPdfPickerList(entry);
        document.getElementById('pdf-picker-modal').style.display='flex';
      } else {
        closePdfPicker();
      }
      showToast('PDF supprimé.','info');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Init ──────────────────────────────────────────────────────────
(function init(){
  try{
    const t=localStorage.getItem('mysifa_theme');
    if(t==='light') document.body.classList.add('light');
    else document.body.classList.remove('light');
    updateThemeBtn();
  }catch(e){}

  loadMe();
  loadEntries();

  document.addEventListener('keydown', e=>{
    if(e.key==='Escape'){
      closeCreateModal();closeUploadModal();closeEditModal();closeStatutModal();closeDelModal();
      closePdfPicker();closePdfDelModal();
    }
  });
})();
</script>
<script>window.__MYSIFA_APP__='bat';</script>
<script src="/static/mysifa_dock.js"></script>
<script>
if(typeof window.MySifaDock !== 'undefined' && typeof window.MySifaDock.bootPageWidgets === 'function'){
  window.MySifaDock.bootPageWidgets();
}
</script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=5"></script>
<script src="/static/chat_widget_v2.js"></script>
<script src="/static/support_widget.js"></script>
</body>
</html>"""
ById('del-modal').style.display='flex';
}
function closeDelModal(){document.getElementById('del-modal').style.display='none';S.delBatId=null;}

async function submitDelete(){
  if(!S.delBatId) return;
  const id=S.delBatId;
  try{
    const r=await api(`/api/bat/${id}`,{method:'DELETE'});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur de suppression','danger');
    } else {
      S.entries=S.entries.filter(e=>e.id!==id);
      render();
      closeDelModal();
      showToast('BAT supprimé.','info');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── PDF Picker ────────────────────────────────────────────────────
function openPdfPicker(id){
  const e=S.entries.find(x=>x.id===id);
  if(!e) return;
  S.pdfPickerBatId=id;
  document.getElementById('pdf-picker-title').textContent=`PDF — ${e.reference}`;
  renderPdfPickerList(e);
  document.getElementById('pdf-picker-modal').style.display='flex';
}
function closePdfPicker(){
  document.getElementById('pdf-picker-modal').style.display='none';
  S.pdfPickerBatId=null;
}
function renderPdfPickerList(e){
  const list=e.pdfs||[];
  const el=document.getElementById('pdf-picker-list');
  if(!list.length){
    el.innerHTML='<div style="color:var(--muted);font-size:13px;padding:12px 0">Aucun PDF associé.</div>';
    return;
  }
  el.innerHTML=list.map(p=>{
    const dt=p.uploaded_at?p.uploaded_at.slice(0,16).replace('T',' '):'';
    return `<div style="display:flex;align-items:center;gap:10px;padding:11px 0;border-bottom:1px solid var(--border)">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <div style="flex:1;min-width:0">
        <div style="font-size:13px;font-weight:600;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escHtml(p.original_name)}">${escHtml(p.original_name)}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${escHtml(dt)}</div>
      </div>
      <a href="/api/bat/${e.id}/pdf/${p.id}" target="_blank" class="ico-btn ok btn-sm" style="text-decoration:none;flex-shrink:0">Ouvrir</a>
      <button type="button" class="ico-btn danger btn-sm" onclick="openPdfDelModal(${e.id},${p.id},'${escHtml(p.original_name)}')" title="Supprimer ce PDF" style="flex-shrink:0">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
      </button>
    </div>`;
  }).join('');
}
function openUploadFromPicker(){
  const id=S.pdfPickerBatId;
  if(!id) return;
  const e=S.entries.find(x=>x.id===id);
  closePdfPicker();
  openUploadModal(id, e?e.reference:'');
}

// ── PDF Delete (individuel) ───────────────────────────────────────
function openPdfDelModal(batId,pdfId,name){
  S.pdfPickerBatId=S.pdfPickerBatId||batId;
  S.pdfDelId={batId,pdfId};
  document.getElementById('pdf-del-modal-msg').textContent=`Le fichier "${name}" sera définitivement supprimé. Cette action est irréversible.`;
  document.getElementById('pdf-del-modal').style.display='flex';
}
function closePdfDelModal(){
  document.getElementById('pdf-del-modal').style.display='none';
  S.pdfDelId=null;
}
async function submitPdfDelete(){
  if(!S.pdfDelId) return;
  const {batId,pdfId}=S.pdfDelId;
  try{
    const r=await api(`/api/bat/${batId}/pdf/${pdfId}`,{method:'DELETE'});
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      showToast(d.detail||'Erreur de suppression','danger');
    } else {
      const entry=S.entries.find(x=>x.id===batId);
      if(entry){
        entry.pdfs=(entry.pdfs||[]).filter(p=>p.id!==pdfId);
        entry.pdf_count=entry.pdfs.length;
        entry.has_pdf=entry.pdf_count>0;
      }
      render();
      closePdfDelModal();
      if(entry&&entry.pdf_count>0){
        S.pdfPickerBatId=batId;
        document.getElementById('pdf-picker-title').textContent=`PDF — ${entry.reference}`;
        renderPdfPickerList(entry);
        document.getElementById('pdf-picker-modal').style.display='flex';
      } else {
        closePdfPicker();
      }
      showToast('PDF supprimé.','info');
    }
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau','danger');}
}

// ── Init ──────────────────────────────────────────────────────────
(function init(){
  try{
    const t=localStorage.getItem('mysifa_theme');
    if(t==='light') document.body.classList.add('light');
    else document.body.classList.remove('light');
    updateThemeBtn();
  }catch(e){}

  loadMe();
  loadEntries();

  document.addEventListener('keydown', e=>{
    if(e.key==='Escape'){
      closeCreateModal();closeUploadModal();closeEditModal();closeStatutModal();closeDelModal();
      closePdfPicker();closePdfDelModal();
    }
  });
})();
</script>
<script>window.__MYSIFA_APP__='bat';</script>
<script src="/static/mysifa_dock.js"></script>
<script>
if(typeof window.MySifaDock !== 'undefined' && typeof window.MySifaDock.bootPageWidgets === 'function'){
  window.MySifaDock.bootPageWidgets();
}
</script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=5"></script>
<script src="/static/chat_widget_v2.js"></script>
<script src="/static/support_widget.js"></script>
</body>
</html>"""
();
}
</script>
<script src="/static/chat_mentions.js"></script>
<script src="/static/chat_widget.js?v=5"></script>
<script src="/static/chat_widget_v2.js"></script>
<script src="/static/support_widget.js"></script>
</body>
</html>"""
tml>
"""
