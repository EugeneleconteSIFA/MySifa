"""Paramètres MySifa — super administrateur uniquement."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user, is_superadmin
from app.web.access_denied import access_denied_response
from app.web.traca_guide_js import TRACA_GUIDE_SCRIPT_BLOCK

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/settings", status_code=302)
        raise
    if not is_superadmin(user):
        return access_denied_response(
            "Paramètres (super admin)",
            detail=(
                "Cette application est réservée au super administrateur. "
                "Merci de contacter un administrateur en cas de besoin."
            ),
        )
    return HTMLResponse(
        content=SETTINGS_HTML.replace("__V_LABEL__", f"v{APP_VERSION}").replace(
            "/*__TRACA_GUIDE__*/", TRACA_GUIDE_SCRIPT_BLOCK
        )
    )


SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Paramètres — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--ok:#34d399;--danger:#f87171;}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--ok:#059669;--danger:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{font-size:15px;font-weight:800;margin-bottom:20px;padding:0 8px}.logo span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s,box-shadow .2s;margin-bottom:2px;position:relative;z-index:1}
.nav-btn:hover,.nav-btn.active{background:rgba(34,211,238,.12);color:var(--accent)}
.nav-btn:hover:not(.active){box-shadow:inset 0 0 0 1.5px rgba(34,211,238,.45),0 0 12px rgba(34,211,238,.2)}
body.light .nav-btn:hover:not(.active){box-shadow:inset 0 0 0 1.5px rgba(8,145,178,.5),0 0 10px rgba(8,145,178,.15)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:rgba(34,211,238,.12);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit;transition:background .15s,color .15s,border-color .15s,box-shadow .2s}
.theme-btn:hover{background:rgba(34,211,238,.12);color:var(--accent);border-color:var(--accent);box-shadow:0 0 0 1px rgba(34,211,238,.22),0 0 20px rgba(34,211,238,.14)}
body.light .theme-btn:hover{box-shadow:0 0 0 1px rgba(8,145,178,.28),0 0 18px rgba(8,145,178,.12)}
.theme-btn .theme-ico{font-size:14px;line-height:1;display:inline-flex;align-items:center}
@media (display-mode:standalone),(max-width:900px){
  .theme-btn .theme-label{display:none}.theme-btn{justify-content:center}
}
.logout-btn{border:none}.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1);box-shadow:0 0 0 1px rgba(248,113,113,.35),0 0 18px rgba(248,113,113,.12)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:24px 28px;overflow:auto}
.mobile-topbar{display:none;align-items:center;gap:10px;margin-bottom:14px}
.mobile-menu-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;flex-shrink:0}
.mobile-menu-btn:hover{border-color:var(--accent);color:var(--accent);background:rgba(34,211,238,.12)}
body.light .mobile-menu-btn:hover{background:rgba(8,145,178,.12)}
.mobile-home-btn{display:none;align-items:center;justify-content:center;width:40px;height:40px;border-radius:10px;
  border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;margin-left:auto;flex-shrink:0}
.mobile-home-btn:hover{border-color:var(--accent);color:var(--accent);background:rgba(34,211,238,.12)}
body.light .mobile-home-btn:hover{background:rgba(8,145,178,.12)}
.mobile-topbar-title{font-size:14px;font-weight:800}
.mobile-topbar-sub{font-size:11px;color:var(--muted);margin-top:2px}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
h1{font-size:22px;margin:0 0 6px}
.sub{color:var(--muted);font-size:13px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 14px}
.table-wrap{overflow:auto;border-radius:10px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}
th{background:rgba(15,23,42,.35);font-weight:700;color:var(--muted);position:sticky;top:0}
body.light th{background:#f1f5f9}
td.chk{text-align:center}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok)}.dot.no{background:var(--border)}
.chk-edit{width:16px;height:16px;cursor:pointer;accent-color:var(--accent)}
.cell-ov{font-size:9px;color:var(--accent);font-weight:700;letter-spacing:.02em}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:12px}
input,select{width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit}
.btn{background:var(--accent);color:var(--text);border:none;border-radius:10px;padding:10px 18px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit}
.btn:hover{filter:brightness(1.06)}
.btn-sec{background:transparent;border:1px solid var(--border);color:var(--muted);transition:box-shadow .2s,border-color .15s,color .15s,filter .15s}
.btn-sec:hover{box-shadow:0 0 0 1px rgba(34,211,238,.32),0 0 20px rgba(34,211,238,.2);border-color:rgba(34,211,238,.45);color:var(--accent)}
body.light .btn-sec:hover{box-shadow:0 0 0 1px rgba(8,145,178,.35),0 0 18px rgba(8,145,178,.15);border-color:rgba(8,145,178,.4);color:var(--accent)}
.row-user{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.row-user:last-child{border-bottom:none}
.pill{font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;border:1px solid var(--border);display:inline-flex;align-items:center;gap:6px;line-height:1.4}
.pill--direction{border-color:rgba(244,114,182,.35);color:#f472b6;background:rgba(244,114,182,.12)}
.pill--administration{border-color:rgba(167,139,250,.38);color:#a78bfa;background:rgba(167,139,250,.12)}
.pill--fabrication{border-color:rgba(52,211,153,.35);color:var(--ok);background:rgba(52,211,153,.12)}
.pill--logistique{border-color:rgba(96,165,250,.35);color:#60a5fa;background:rgba(96,165,250,.12)}
.pill--comptabilite{border-color:rgba(251,191,36,.38);color:#fbbf24;background:rgba(251,191,36,.12)}
.pill--expedition{border-color:rgba(248,113,113,.38);color:var(--danger);background:rgba(248,113,113,.12)}
.pill--superadmin{border-color:rgba(34,211,238,.45);color:var(--accent);background:rgba(34,211,238,.14)}
.pill--inactive{border-color:rgba(148,163,184,.35);color:var(--muted);background:rgba(148,163,184,.10)}
.users-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.users-head h2{margin:0}
.users-search{display:flex;align-items:center;gap:8px;min-width:min(520px,100%)}
.users-search input{flex:1;min-width:220px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.users-search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .users-search input:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.users-search .hint{font-size:11px;color:var(--muted);white-space:nowrap}
.users-search select{min-width:140px;padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);
  background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;outline:none}
.users-search select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
body.light .users-search select:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.nav-group-label{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);padding:8px 12px 2px;opacity:.7}
.hidden{display:none}
.legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.legend .item{padding:12px;border:1px solid var(--border);border-radius:10px;font-size:12px}
.legend .item strong{display:block;margin-bottom:6px;font-size:13px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;box-shadow:0 8px 32px rgba(0,0,0,.35);z-index:900}.toast.err{border-left:3px solid var(--danger)}
@media(max-width:900px){
  .mobile-topbar{display:flex;position:fixed;top:0;left:0;right:0;z-index:120;background:var(--bg);padding:10px 18px;border-bottom:1px solid var(--border)}
  .mobile-menu-btn{display:inline-flex}
  .mobile-home-btn{display:inline-flex}
  body.has-topbar .main{padding-top:74px}
  .main{padding:16px}
  .desktop-head{display:none}
  .sidebar{position:fixed;left:0;top:0;bottom:0;height:auto;max-height:100vh;z-index:300;
    transform:translateX(-105%);transition:transform .18s ease;
    box-shadow:0 16px 48px rgba(0,0,0,.55);padding:20px 12px}
  body.sb-open .sidebar{transform:translateX(0)}
  .layout{min-height:100vh}
}
</style>
</head>
<body>
<div class="sidebar-overlay" id="sb-ov"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">My<span>Sifa</span><div class="logo-sub">by SIFA</div></div>
    <div class="nav-scroll tabs" style="width:100%;margin:0">
      <div class="nav-group-label">Base</div>
      <button type="button" class="nav-btn active" data-tab="users">Utilisateurs</button>
      <button type="button" class="nav-btn" data-tab="fournisseurs">Fournisseurs</button>
      <div class="nav-group-label" style="margin-top:8px">Accès</div>
      <button type="button" class="nav-btn" data-tab="matrix">Matrice d'accès</button>
      <button type="button" class="nav-btn" data-tab="defaults">Référentiel rôles</button>
      <div class="nav-group-label" style="margin-top:8px">Communication</div>
      <button type="button" class="nav-btn" data-tab="updates">Mises à jour</button>
    </div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn back-mysifa" onclick="location.href='/'">
        ← Retour <span class="wm">My<span>Sifa</span></span>
      </button>
      <div class="user-chip" id="sb-user-chip" title="Modifier mon profil">
        <div class="uc-name" id="sb-uc-name">—</div>
        <div class="uc-role" id="sb-uc-role">—</div>
        <div style="font-size:10px;color:var(--accent);margin-top:3px;display:flex;align-items:center;gap:4px">
          <span id="sb-edit-ico"></span> Mon profil
        </div>
      </div>
      <button type="button" class="support-btn" id="sb-support" title="Contacter le support (email)">
        <span class="support-ico" id="sb-support-ico"></span>
        <span>Contacter le support</span>
      </button>
      <button type="button" class="theme-btn" id="theme-btn">
        <span class="theme-ico" id="theme-ico-slot"></span>
        <span class="theme-label" id="theme-label">Mode sombre</span>
      </button>
      <button type="button" class="logout-btn" id="logout-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Paramètres · MySifa __V_LABEL__</div>
    </div>
  </aside>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" id="sb-burger" aria-label="Menu">
        <span style="display: inline-flex; align-items: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </span>
      </button>
      <div>
        <div class="mobile-topbar-title">Paramètres</div>
        <div class="mobile-topbar-sub">Gestion des comptes et des accès</div>
      </div>
      <button type="button" class="mobile-home-btn" id="sb-home" aria-label="Accueil">
        <span style="display: inline-flex; align-items: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0"><path d="M3 10.5L12 3l9 7.5"></path><path d="M5 10v11h14V10"></path><path d="M10 21v-6h4v6"></path></svg>
        </span>
      </button>
    </div>
    <div class="desktop-head">
      <h1>Paramètres</h1>
      <p class="sub">Gestion des comptes et visualisation des accès applications — réservé au super administrateur.</p>
    </div>

    <section id="panel-users">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-list">Liste</button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-matrix">Matrice</button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-defaults">Référentiel</button>
    </div>
      <div class="card">
        <h2>Ajouter un utilisateur</h2>
        <div class="form-grid">
          <input type="text" id="cu-nom" placeholder="Nom complet" autocomplete="name">
          <input type="text" id="cu-ident" placeholder="Identifiant (auto si vide)" autocomplete="off">
          <input type="email" id="cu-email" placeholder="Email" autocomplete="off">
          <input type="password" id="cu-pwd" placeholder="Mot de passe (8+)" autocomplete="new-password">
          <select id="cu-role"></select>
          <select id="cu-op"><option value="">— Opérateur lié —</option></select>
          <select id="cu-mac"><option value="">— Machine (fabrication) —</option></select>
        </div>
        <button type="button" class="btn" id="cu-go">Créer le compte</button>
      </div>
      <div class="card">
        <div class="users-head">
          <h2>Utilisateurs</h2>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="users-search">
              <input type="search" id="users-q" placeholder="Rechercher (nom, email, rôle, opérateur, machine…)" autocomplete="off" spellcheck="false">
              <select id="users-role-filter"><option value="">Tous les services</option></select>
              <span class="hint" id="users-q-hint"></span>
            </div>
            <button type="button" class="btn btn-sec" onclick="downloadUsersCSV()" title="Télécharger la liste">Télécharger</button>
          </div>
        </div>
        <div id="users-list"></div>
      </div>
    </section>

    <section id="panel-matrix" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-list">Liste</button>
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-matrix">Matrice</button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-defaults">Référentiel</button>
    </div>
      <div class="card">
        <h2>Qui a accès à quoi</h2>
        <p class="sub" style="margin-top:-8px">Cases à cocher : accès effectif (héritage du rôle ou surcharges). « Perso » = différent du défaut du rôle. Paramètres reste réservé au rôle super admin. Les super admins ont tout ; la ligne est en lecture seule.</p>
        <div class="table-wrap" id="matrix-table"></div>
      </div>
    </section>

    <section id="panel-defaults" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-list">Liste</button>
      <button type="button" class="btn btn-sec sub-tab-btn" data-subtab="users-matrix">Matrice</button>
      <button type="button" class="btn btn-sec sub-tab-btn active" data-subtab="users-defaults">Référentiel</button>
    </div>
      <div class="card">
        <h2>Accès par défaut selon le rôle</h2>
        <p class="sub" style="margin-top:-8px">Chaque utilisateur hérite de ces accès selon son rôle assigné.</p>
        <div class="legend" id="role-legend"></div>
      </div>
    </section>

    <section id="panel-fournisseurs" class="hidden">
    <div class="tabs" style="margin-bottom:14px">
      <button type="button" class="btn btn-sec four-sub-btn active" data-foursub="four-certifs">Certifications</button>
      <button type="button" class="btn btn-sec four-sub-btn" data-foursub="four-hist">Historique</button>
    </div>
      <div id="four-certifs">
        <div class="card">
          <h2>Ajouter un fournisseur</h2>
          <div class="form-grid">
            <input type="text" id="cf-nom" placeholder="Nom du fournisseur" autocomplete="off">
            <input type="text" id="cf-licence" placeholder="Code Licence FSC (ex: FSC-C004451)" autocomplete="off">
            <input type="text" id="cf-certificat" placeholder="Code Certificat FSC (ex: CU-COC-807907)" autocomplete="off">
          </div>
          <button type="button" class="btn" id="cf-go">Ajouter</button>
        </div>
        <div class="card">
          <h2>Fournisseurs enregistrés</h2>
          <div class="table-wrap" id="four-table-wrap"></div>
        </div>
      </div>
      <div id="four-hist" class="hidden">
        <div class="card">
          <h2>Historique des réceptions par fournisseur</h2>
          <p class="sub" style="margin-top:-8px">Sélectionnez un fournisseur pour voir ses réceptions.</p>
          <div class="form-grid" style="margin-bottom:12px">
            <select id="fh-four"><option value="">— Choisir un fournisseur —</option></select>
          </div>
          <div id="fh-results"></div>
        </div>
      </div>
    </section>

    <section id="panel-updates" class="hidden">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:16px">
          <h2 style="margin:0">Annonces de mise à jour</h2>
          <button type="button" class="btn" id="upd-new-btn" onclick="openNewUpdateModal()">+ Nouvelle annonce</button>
        </div>
        <p class="sub" style="margin-top:-8px;margin-bottom:16px">Gérez les messages affichés aux utilisateurs lors de leur prochaine connexion. Cliquez sur une ligne pour voir qui l'a lu.</p>
        <div id="upd-list"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
      </div>
    </section>

    <!-- Modal nouvelle annonce -->
    <div id="upd-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:90vh;overflow:auto">
        <h2 style="margin:0 0 18px;font-size:17px">Nouvelle annonce</h2>
        <div class="form-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Page concernée</label>
            <select id="nm-scope" style="width:100%">
              <option value="planning">Planning de production</option>
              <option value="fabrication">Saisie de production</option>
              <option value="global">Toutes les pages</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Active</label>
            <select id="nm-active" style="width:100%">
              <option value="1">Oui — visible par les utilisateurs</option>
              <option value="0">Non — masquée</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Titre</label>
          <input type="text" id="nm-titre" placeholder="Ex : Mise à jour du 15 mai 2026 — Planning" style="width:100%">
        </div>
        <div style="margin-bottom:18px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Message (HTML autorisé)</label>
          <textarea id="nm-message" rows="8" placeholder="&lt;p&gt;Bonjour ! Voici les nouveautés…&lt;/p&gt;" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:monospace;resize:vertical"></textarea>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeNewUpdateModal()">Annuler</button>
          <button type="button" class="btn" onclick="submitNewUpdate()">Créer l'annonce</button>
        </div>
      </div>
    </div>

    <!-- Modal modifier annonce -->
    <div id="edit-upd-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:center;justify-content:center" class="hidden">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:90vh;overflow:auto">
        <h2 style="margin:0 0 18px;font-size:17px">Modifier l'annonce</h2>
        <div class="form-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Page concernée</label>
            <select id="edit-nm-scope" style="width:100%">
              <option value="planning">Planning de production</option>
              <option value="fabrication">Saisie de production</option>
              <option value="global">Toutes les pages</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Active</label>
            <select id="edit-nm-active" style="width:100%">
              <option value="1">Oui — visible par les utilisateurs</option>
              <option value="0">Non — masquée</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Titre</label>
          <input type="text" id="edit-nm-titre" placeholder="Ex : Mise à jour du 15 mai 2026 — Planning" style="width:100%">
        </div>
        <div style="margin-bottom:18px">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:4px">Message (HTML autorisé)</label>
          <textarea id="edit-nm-message" rows="8" placeholder="&lt;p&gt;Bonjour ! Voici les nouveautés…&lt;/p&gt;" style="width:100%;padding:10px 12px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:monospace;resize:vertical"></textarea>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button type="button" class="btn btn-sec" onclick="closeEditUpdateModal()">Annuler</button>
          <button type="button" class="btn" onclick="submitEditUpdate()">Enregistrer</button>
        </div>
      </div>
    </div>
  </main>
</div>
<script src="/static/support_widget.js"></script>
<script>
/*__TRACA_GUIDE__*/
const API = window.location.origin;
async function api(path, opt) {
  const r = await fetch(API + path, { credentials: 'include', ...opt });
  if (r.status === 401) { location.href = '/?next=/settings'; return null; }
  const ct = r.headers.get('content-type') || '';
  const j = ct.includes('json') ? await r.json().catch(() => ({})) : {};
  if (!r.ok) throw new Error(j.detail || ('Erreur ' + r.status));
  return j;
}
function toast(msg, err) {
  const t = document.createElement('div');
  t.className = 'toast' + (err ? ' err' : '');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
let assignableRoles = [];
let roleLabels = {};
let apps = [];
let operators = [];
let machines = [];
let matrixSnapshot = [];
let superadminEmailRef = '';
let usersAll = [];
let usersQuery = '';
let usersRoleFilter = '';

function _norm(s){
  return String(s||'')
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z0-9@._\- ]+/g,' ')
    .replace(/\s+/g,' ')
    .trim();
}

function userHaystack(u){
  const role = (u && u.role) ? String(u.role) : '';
  const roleLbl = (roleLabels && roleLabels[role]) ? String(roleLabels[role]) : role;
  return _norm([
    u && u.nom,
    u && u.email,
    role,
    roleLbl,
    u && u.operateur_lie,
    u && u.telephone,
    u && u.machine_nom,
    u && u.machine_id,
    (u && Number(u.actif)===1) ? 'actif' : 'inactif',
  ].filter(Boolean).join(' '));
}

function scoreMatch(hay, tokens){
  let score = 0;
  for(const t of tokens){
    const i = hay.indexOf(t);
    if(i < 0) return null;
    score += i;
    if(i === 0) score -= 6;
  }
  return score;
}

function setTab(id) {
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === id);
  });
  ['users', 'matrix', 'defaults', 'fournisseurs', 'updates'].forEach(p => {
    const el = document.getElementById('panel-' + p);
    if (el) el.classList.toggle('hidden', p !== id);
  });
  if (id === 'fournisseurs') loadFournisseurs();
  if (id === 'updates') loadUpdates();
}

document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
  b.addEventListener('click', () => setTab(b.dataset.tab));
});

function setSidebarOpen(open){
  document.body.classList.toggle('sb-open', !!open);
}
try{
  document.body.classList.add('has-topbar');
  const ov = document.getElementById('sb-ov');
  if(ov) ov.addEventListener('click', ()=>setSidebarOpen(false));
  const burger = document.getElementById('sb-burger');
  if(burger) burger.addEventListener('click', ()=>setSidebarOpen(!document.body.classList.contains('sb-open')));
  const home = document.getElementById('sb-home');
  if(home) home.addEventListener('click', ()=>{ window.location.href = '/'; });
  // Fermer le menu après clic sur un onglet (mobile)
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => {
    b.addEventListener('click', () => setSidebarOpen(false));
  });
}catch(e){}

function iconSvg(name, size) {
  const s = size || 16;
  const a = 'width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
  if (name === 'moon') return '<svg ' + a + '><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  if (name === 'sun') return '<svg ' + a + '><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  if (name === 'edit') return '<svg ' + a + '><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
  return '';
}
function syncThemeBtn() {
  const light = document.body.classList.contains('light');
  const slot = document.getElementById('theme-ico-slot');
  if (slot) slot.innerHTML = iconSvg(light ? 'sun' : 'moon', 16);
  const lb = document.getElementById('theme-label');
  if (lb) lb.textContent = light ? 'Mode clair' : 'Mode sombre';
}

document.getElementById('theme-btn').onclick = () => {
  document.body.classList.toggle('light');
  localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
  syncThemeBtn();
};
document.getElementById('logout-btn').onclick = async () => {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
  location.href = '/';
};
if (localStorage.getItem('theme') === 'light') document.body.classList.add('light');
syncThemeBtn();

document.getElementById('sb-user-chip').onclick = () => { location.href = '/prod?page=profil'; };

function initSupportSidebar() {
  const ico = document.getElementById('sb-support-ico');
  if (ico) {
    try {
      ico.innerHTML = (window.MySifaSupport && window.MySifaSupport.iconSvg) ? window.MySifaSupport.iconSvg() : '';
    } catch (e) { ico.innerHTML = ''; }
  }
  document.getElementById('sb-support').onclick = () => {
    try {
      if (window.MySifaSupport && typeof window.MySifaSupport.open === 'function') {
        window.MySifaSupport.open({
          user: window.__meUser,
          page: 'Paramètres',
          notify: (m, t) => toast(m, t === 'error'),
          api: api,
        });
      }
    } catch (e) {}
  };
}

async function refreshSidebarUser() {
  const me = await api('/api/auth/me');
  if (!me || typeof me !== 'object') return;
  window.__meUser = me;
  const nm = document.getElementById('sb-uc-name');
  const rr = document.getElementById('sb-uc-role');
  const ed = document.getElementById('sb-edit-ico');
  if (nm) nm.textContent = me.nom || '';
  if (rr) rr.textContent = roleLabels[me.role] || me.role || '';
  if (ed) ed.innerHTML = iconSvg('edit', 10);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

async function loadFilters() {
  try {
    const f = await api('/api/filters');
    if (f && f.operators) operators = f.operators;
  } catch (e) { operators = []; }
  const opSel = document.getElementById('cu-op');
  opSel.innerHTML = '<option value="">— Opérateur lié —</option>' +
    operators.map(o => '<option value="' + esc(o) + '">' + esc(o) + '</option>').join('');
}

async function loadMachines() {
  try {
    const m = await api('/api/planning/machines');
    machines = Array.isArray(m) ? m : [];
  } catch (e) { machines = []; }
  const ms = document.getElementById('cu-mac');
  ms.innerHTML = '<option value="">— Machine (fabrication) —</option>' +
    machines.map(x => '<option value="' + esc(x.id) + '">' + esc(x.nom) + '</option>').join('');
}

function fillRoleSelect() {
  const s = document.getElementById('cu-role');
  s.innerHTML = assignableRoles.map(r =>
    '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>'
  ).join('');
}

async function loadUsers() {
  const list = await api('/api/users');
  usersAll = Array.isArray(list) ? list.slice() : [];
  usersAll.sort((a,b)=>{
    // Tri par service (rôle) d'abord, puis par nom alphabétique
    const roleA = String(a && a.role || '').toLowerCase();
    const roleB = String(b && b.role || '').toLowerCase();
    if(roleA !== roleB) return roleA.localeCompare(roleB,'fr');
    const an = _norm(a && a.nom);
    const bn = _norm(b && b.nom);
    if(an !== bn) return an.localeCompare(bn,'fr');
    return _norm(a && a.email).localeCompare(_norm(b && b.email),'fr');
  });
  renderUsersList();
}

function renderUsersList(){
  const box = document.getElementById('users-list');
  const hint = document.getElementById('users-q-hint');
  if(!box) return;
  if(!usersAll.length){
    box.innerHTML = '<p class="sub">Aucun utilisateur.</p>';
    if(hint) hint.textContent = '';
    return;
  }

  const q = _norm(usersQuery);
  const tokens = q ? q.split(' ').filter(Boolean) : [];
  let list = usersAll;

  // Filtrage par service (rôle)
  if(usersRoleFilter && usersRoleFilter !== ''){
    list = list.filter(u => (u.role || '') === usersRoleFilter);
  }

  if(tokens.length){
    const scored = [];
    for(const u of list){
      const hay = userHaystack(u);
      const sc = scoreMatch(hay, tokens);
      if(sc != null) scored.push({u, sc});
    }
    scored.sort((a,b)=> (a.sc - b.sc) || _norm(a.u.nom).localeCompare(_norm(b.u.nom),'fr'));
    list = scored.map(x=>x.u);
  }
  if(hint) hint.textContent = (list.length + '/' + usersAll.length);

  box.innerHTML = list.map(u => {
    const act = Number(u.actif) === 1;
    const role = String(u.role || '').toLowerCase().trim();
    const pillCls = 'pill pill--' + esc(role || 'fabrication');
    const meta = [
      u.identifiant ? ('Id: ' + esc(u.identifiant)) : '',
      u.operateur_lie ? ('Op: ' + esc(u.operateur_lie)) : '',
      u.machine_nom ? ('Machine: ' + esc(u.machine_nom)) : '',
      u.telephone ? ('Tel: ' + esc(u.telephone)) : '',
    ].filter(Boolean).join(' · ');
    return '<div class="row-user">' +
      '<div style="display:flex;align-items:flex-start;gap:8px">' +
        '<div><strong>' + esc(u.nom) + '</strong> <span class="' + pillCls + '">' + esc(roleLabels[u.role] || u.role) + '</span>' +
        (act ? '' : ' <span class="pill pill--inactive">Inactif</span>') +
        '<div style="font-size:11px;color:var(--muted);margin-top:4px">' + esc(u.email) + (meta ? (' · ' + meta) : '') + '</div></div>' +
        '<button type="button" class="btn btn-sec copy-user-btn" data-copy="' + u.id + '" title="Copier les identifiants" style="padding:6px 8px">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' +
        '</button>' +
      '</div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">' +
      '<button type="button" class="btn btn-sec" data-edit="' + u.id + '">Modifier</button>' +
      '<button type="button" class="btn btn-sec" data-reset="' + u.id + '">Reset MDP</button>' +
      (act ? '<button type="button" class="btn btn-sec" data-off="' + u.id + '">Désactiver</button>'
        : '<button type="button" class="btn btn-sec" data-on="' + u.id + '">Réactiver</button>') +
      '<button type="button" class="btn btn-sec" data-del="' + u.id + '" title="Supprimer" style="color:var(--danger);padding:6px 8px">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>' +
      '</button>' +
      '</div></div>';
  }).join('');

  box.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => openEdit(Number(b.dataset.edit)));
  box.querySelectorAll('[data-reset]').forEach(b => b.onclick = () => resetPwd(Number(b.dataset.reset)));
  box.querySelectorAll('[data-off]').forEach(b => b.onclick = () => setActif(Number(b.dataset.off), 0));
  box.querySelectorAll('[data-on]').forEach(b => b.onclick = () => setActif(Number(b.dataset.on), 1));
  box.querySelectorAll('[data-copy]').forEach(b => b.onclick = () => copyUserCredentials(Number(b.dataset.copy)));
  box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => deleteUser(Number(b.dataset.del)));
}

async function deleteUser(id) {
  const u = usersAll.find(x => x.id === id);
  if (!u) return;
  const isAdmin = (u.email || '').toLowerCase().includes('admin') || (u.nom || '').toLowerCase() === 'administrateur';
  if (isAdmin) {
    toast('Impossible de supprimer un administrateur', 'error');
    return;
  }
  const hasLinkages = u.operateur_lie || u.identifiant || (u.machine_nom && u.machine_nom !== '—');
  const warningMsg = hasLinkages ? '\n\n⚠️ Cet utilisateur est lié à des données (opérateur, machine...). La suppression peut affecter l\'historique.' : '';
  if (!confirm('Supprimer définitivement l\'utilisateur "' + u.nom + '" (' + u.email + ') ?' + warningMsg + '\n\nCette action est irréversible.')) return;
  try {
    await api('/api/users/' + id, { method: 'DELETE' });
    toast('Utilisateur supprimé', 'success');
    await loadUsers();
    await loadMatrix();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function setActif(id, v) {
  try {
    await api('/api/users/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actif: v }) });
    toast(v ? 'Compte réactivé' : 'Compte désactivé');
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
}

async function resetPwd(id) {
  if (!confirm('Générer un mot de passe temporaire ?')) return;
  try {
    const r = await api('/api/users/' + id + '/reset-password', { method: 'POST' });
    if (r && r.temp_password) alert('Mot de passe temporaire : ' + r.temp_password);
    toast('Mot de passe régénéré');
  } catch (e) { toast(e.message, true); }
}

async function copyUserCredentials(id) {
  const u = usersAll.find(x => x.id === id);
  if (!u) return;
  const lines = [
    'Nom : ' + (u.nom || ''),
    'Email : ' + (u.email || ''),
    'Identifiant : ' + (u.identifiant || ''),
    'Rôle : ' + (roleLabels[u.role] || u.role || ''),
  ];
  if (u.operateur_lie) lines.push('Opérateur : ' + u.operateur_lie);
  if (u.machine_nom) lines.push('Machine : ' + u.machine_nom);
  if (u.telephone) lines.push('Téléphone : ' + u.telephone);
  const text = lines.join('\n');
  try {
    await navigator.clipboard.writeText(text);
    toast('Identifiants copiés');
  } catch (e) {
    toast('Erreur copie : ' + e.message, true);
  }
}

function downloadUsersCSV(){
  // Exporter tous les utilisateurs (pas seulement les filtrés)
  if(!usersAll || usersAll.length===0){
    toast('Aucun utilisateur à exporter', true);
    return;
  }
  const headers=['Nom','Email','Rôle','Actif','Dernière connexion','Opérateur lié','Machine'];
  const rows=usersAll.map(u=>{
    const nom=esc(u.nom||'');
    const email=esc(u.email||'');
    const role=esc(roleLabels[u.role]||u.role||'');
    const actif=u.actif?'Oui':'Non';
    const lastLogin=u.last_login?new Date(u.last_login).toLocaleString('fr-FR'):'Jamais';
    const op=esc(u.operateur||'');
    const mac=esc(u.machine_nom||'');
    return [nom,email,role,actif,lastLogin,op,mac].map(f=>'"'+f.replace(/"/g,'""')+'"').join(';');
  });
  const csv=[headers.join(';')].concat(rows).join('\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;
  a.download='utilisateurs_mysifa_'+new Date().toISOString().slice(0,10)+'.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast(usersAll.length+' utilisateurs exportés');
}

function syncCuRoleUI() {
  const r = document.getElementById('cu-role').value;
  // Cacher opérateur lié pour fabrication et les autres rôles hors production
  const hideOp = ['fabrication', 'direction', 'administration', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
  document.getElementById('cu-op').style.display = hideOp ? 'none' : '';
  document.getElementById('cu-mac').style.display = r === 'fabrication' ? '' : 'none';
}
document.getElementById('cu-role').addEventListener('change', syncCuRoleUI);

document.getElementById('cu-go').onclick = async () => {
  const nom = document.getElementById('cu-nom').value.trim();
  const identifiant = document.getElementById('cu-ident').value.trim();
  const email = document.getElementById('cu-email').value.trim();
  const password = document.getElementById('cu-pwd').value;
  const role = document.getElementById('cu-role').value;
  const operateur_lie = document.getElementById('cu-op').value || null;
  const mid = document.getElementById('cu-mac').value;
  const machine_id = mid ? Number(mid) : null;
  if (!nom || !email || !password || !role) return toast('Champs requis', true);
  try {
    await api('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, identifiant, email, password, role, operateur_lie, machine_id }) });
    toast('Utilisateur créé');
    document.getElementById('cu-nom').value = '';
    document.getElementById('cu-ident').value = '';
    document.getElementById('cu-email').value = '';
    document.getElementById('cu-pwd').value = '';
    await loadUsers();
    await loadMatrix();
  } catch (e) { toast(e.message, true); }
};

// Recherche utilisateurs (client-side, sur toutes les colonnes)
try{
  const uq = document.getElementById('users-q');
  if(uq){
    uq.addEventListener('input', ()=>{
      usersQuery = uq.value || '';
      renderUsersList();
    });
  }
}catch(e){}

// Filtre par service
function fillRoleFilterSelect() {
  const sel = document.getElementById('users-role-filter');
  if(!sel) return;
  sel.innerHTML = '<option value="">Tous les services</option>' +
    assignableRoles.map(r => '<option value="' + esc(r) + '">' + esc(roleLabels[r] || r) + '</option>').join('');
}
try{
  const rf = document.getElementById('users-role-filter');
  if(rf){
    rf.addEventListener('change', ()=>{
      usersRoleFilter = rf.value || '';
      renderUsersList();
    });
  }
}catch(e){}

async function openEdit(id) {
  let u;
  try { u = await api('/api/users/' + id); } catch (e) { toast(e.message, true); return; }
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto';
  const isDesignatedSup = superadminEmailRef && String(u.email || '').trim().toLowerCase() === superadminEmailRef && u.role === 'superadmin';
  const roleOpts = isDesignatedSup
    ? '<option value="superadmin" selected>Super admin</option>'
    : assignableRoles.map(r => '<option value="' + esc(r) + '"' + (u.role === r ? ' selected' : '') + '>' + esc(roleLabels[r] || r) + '</option>').join('');

  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:16px">Modifier</h3>' +
    '<label class="sub">Nom</label><input id="ed-nom" value="' + esc(u.nom) + '" style="margin-bottom:10px">' +
    '<label class="sub">Identifiant</label><input id="ed-ident" value="' + esc(u.identifiant || '') + '" style="margin-bottom:10px" placeholder="auto si vide">' +
    '<label class="sub">Email</label><input id="ed-email" type="email" value="' + esc(u.email) + '" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' +
    '<label class="sub">Rôle</label><select id="ed-role" style="margin-bottom:10px"' + (isDesignatedSup ? ' disabled' : '') + '>' + roleOpts + '</select>' +
    '<div id="ed-op-wrap"><label class="sub">Opérateur lié</label><select id="ed-op" style="margin-bottom:10px">' +
    '<option value="">—</option>' + operators.map(o => '<option value="' + esc(o) + '"' + (u.operateur_lie === o ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select></div>' +
    '<div id="ed-mac-wrap"><label class="sub">Machine</label><select id="ed-mac" style="margin-bottom:10px">' +
    '<option value="">—</option>' + machines.map(m => '<option value="' + esc(m.id) + '"' + (String(u.machine_id) === String(m.id) ? ' selected' : '') + '>' + esc(m.nom) + '</option>').join('') + '</select></div>' +
    '<label class="sub" style="display:flex;align-items:center;gap:8px"><input type="checkbox" id="ed-act" ' + (Number(u.actif) === 1 ? 'checked' : '') + '> Compte actif</label>' +
    '<label class="sub">Nouveau mot de passe (optionnel)</label><input id="ed-pwd" type="password" style="margin-bottom:10px">' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ed-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ed-save">Enregistrer</button></div>';

  function syncEd() {
    const r = dlg.querySelector('#ed-role').value;
    // Cacher opérateur lié pour fabrication et les autres rôles hors production
    const hideOp = ['fabrication', 'direction', 'administration', 'logistique', 'comptabilite', 'expedition', 'superadmin'].indexOf(r) >= 0;
    dlg.querySelector('#ed-op-wrap').style.display = hideOp ? 'none' : '';
    dlg.querySelector('#ed-mac-wrap').style.display = (r === 'fabrication') ? '' : 'none';
  }
  dlg.querySelector('#ed-role').addEventListener('change', syncEd);
  syncEd();

  dlg.querySelector('#ed-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ed-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#ed-nom').value.trim(),
      identifiant: dlg.querySelector('#ed-ident').value.trim(),
      email: dlg.querySelector('#ed-email').value.trim(),
      role: dlg.querySelector('#ed-role').value,
      operateur_lie: dlg.querySelector('#ed-op').value || null,
      machine_id: dlg.querySelector('#ed-mac').value ? Number(dlg.querySelector('#ed-mac').value) : null,
      actif: dlg.querySelector('#ed-act').checked ? 1 : 0,
    };
    const np = dlg.querySelector('#ed-pwd').value;
    if (np) body.password = np;
    try {
      await api('/api/users/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      toast('Utilisateur mis à jour');
      backdrop.remove();
      await loadUsers();
      await loadMatrix();
    } catch (e) { toast(e.message, true); }
  };

  backdrop.appendChild(dlg);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}

async function onAccessToggle(ev) {
  const t = ev.target;
  if (!t || !t.classList || !t.classList.contains('chk-edit')) return;
  const uid = Number(t.dataset.uid);
  const appId = t.dataset.app;
  const checked = t.checked;
  const row = matrixSnapshot.find(r => r.id === uid);
  if (!row || !row.access_default) return;
  const def = !!row.access_default[appId];
  const ov = Object.assign({}, row.access_overrides || {});
  if (checked === def) delete ov[appId];
  else ov[appId] = checked;
  try {
    await api('/api/users/' + uid, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ access_overrides: ov }),
    });
    toast('Accès mis à jour');
    await loadMatrix();
    await loadUsers();
  } catch (e) {
    toast(e.message, true);
    t.checked = !checked;
  }
}

async function loadMatrix() {
  const data = await api('/api/settings/access-matrix');
  if (!data) return;
  apps = data.apps || [];
  roleLabels = data.role_labels || roleLabels;
  const matrix = data.matrix || [];
  matrixSnapshot = matrix;

  const th = '<th>Utilisateur</th><th>Rôle</th>' + apps.map(a => '<th title="' + esc(a.hint || '') + '">' + esc(a.label) + '</th>').join('');
  const tr = matrix.map(row => {
    const isRowSuper = row.role === 'superadmin';
    const cells = apps.map(a => {
      const ok = row.access && row.access[a.id];
      const hasOv = row.access_overrides && Object.prototype.hasOwnProperty.call(row.access_overrides, a.id);
      if (a.id === 'settings' || isRowSuper) {
        return '<td class="chk"><span class="dot' + (ok ? '' : ' no') + '" title="Non modifiable ici"></span></td>';
      }
      const perso = hasOv ? '<span class="cell-ov">perso</span>' : '';
      return '<td class="chk"><label style="display:flex;flex-direction:column;align-items:center;gap:3px;cursor:pointer;margin:0">' +
        '<input type="checkbox" class="chk-edit" data-uid="' + row.id + '" data-app="' + esc(a.id) + '" ' + (ok ? 'checked' : '') + (Number(row.actif) !== 1 ? ' disabled' : '') + ' />' +
        perso + '</label></td>';
    }).join('');
    const dim = Number(row.actif) !== 1 ? 'opacity:.55' : '';
    return '<tr style="' + dim + '"><td><strong>' + esc(row.nom) + '</strong><div style="font-size:11px;color:var(--muted)">' + esc(row.email) + '</div></td><td>' + esc(row.role_label || row.role) + '</td>' + cells + '</tr>';
  }).join('');
  const wrap = document.getElementById('matrix-table');
  wrap.innerHTML = '<table><thead><tr>' + th + '</tr></thead><tbody>' + tr + '</tbody></table>';
  wrap.querySelectorAll('.chk-edit').forEach(cb => { cb.addEventListener('change', onAccessToggle); });

  const leg = document.getElementById('role-legend');
  leg.innerHTML = (data.role_defaults || []).map(d => {
    const bits = apps.map(a => {
      const ok = d.access && d.access[a.id];
      return '<span class="dot' + (ok ? '' : ' no') + '" style="margin-right:4px"></span>' + esc(a.label);
    }).join(' · ');
    return '<div class="item"><strong>' + esc(d.label) + '</strong> <code style="font-size:11px">' + esc(d.role) + '</code><div style="margin-top:8px;line-height:1.6">' + bits + '</div></div>';
  }).join('');
}

// ─── Fournisseurs FSC ──────────────────────────────────────────────

let fournisseursAll = [];

// Sub-tab navigation for fournisseurs
document.querySelectorAll('.four-sub-btn').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.four-sub-btn').forEach(x => x.classList.toggle('active', x.dataset.foursub === b.dataset.foursub));
    ['four-certifs', 'four-hist'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('hidden', id !== b.dataset.foursub);
    });
    if (b.dataset.foursub === 'four-hist') fillFourHistSelect();
  });
});

async function loadFournisseurs() {
  try {
    const data = await api('/api/fournisseurs');
    fournisseursAll = Array.isArray(data) ? data : [];
  } catch (e) { fournisseursAll = []; toast(e.message, true); }
  renderFournisseursTable();
  fillFourHistSelect();
}

function renderFournisseursTable() {
  const wrap = document.getElementById('four-table-wrap');
  if (!wrap) return;
  if (!fournisseursAll.length) {
    wrap.innerHTML = '<p class="sub" style="padding:12px">Aucun fournisseur enregistré.</p>';
    return;
  }
  wrap.innerHTML = '<table><thead><tr><th>Nom</th><th>Licence FSC</th><th>Certificat FSC</th><th>Code-barre traça</th><th></th></tr></thead><tbody>' +
    fournisseursAll.map(f => '<tr>' +
      '<td><strong>' + esc(f.nom) + '</strong></td>' +
      '<td><code>' + esc(f.licence || '—') + '</code></td>' +
      '<td><code>' + esc(f.certificat || '—') + '</code></td>' +
      '<td>' + (f.traca_photo_url || f.traca_explication || f.traca_exemple_code
        ? '<span style="color:var(--ok);font-size:12px">✓ Renseigné</span>'
        : '<span style="color:var(--muted);font-size:12px">— Non renseigné</span>') + '</td>' +
      '<td style="display:flex;gap:6px;justify-content:flex-end">' +
        '<button type="button" class="btn btn-sec" data-fedit="' + f.id + '">Modifier</button>' +
        '<button type="button" class="btn btn-sec" data-fdel="' + f.id + '" style="color:var(--danger)">Supprimer</button>' +
      '</td></tr>'
    ).join('') + '</tbody></table>';
  wrap.querySelectorAll('[data-fedit]').forEach(b => b.onclick = () => openEditFournisseur(Number(b.dataset.fedit)));
  wrap.querySelectorAll('[data-fdel]').forEach(b => b.onclick = () => deleteFournisseur(Number(b.dataset.fdel)));
}

document.getElementById('cf-go').onclick = async () => {
  const nom = document.getElementById('cf-nom').value.trim();
  const licence = document.getElementById('cf-licence').value.trim();
  const certificat = document.getElementById('cf-certificat').value.trim();
  if (!nom) return toast('Nom du fournisseur requis', true);
  try {
    await api('/api/fournisseurs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom, licence, certificat }),
    });
    toast('Fournisseur ajouté');
    document.getElementById('cf-nom').value = '';
    document.getElementById('cf-licence').value = '';
    document.getElementById('cf-certificat').value = '';
    await loadFournisseurs();
  } catch (e) { toast(e.message, true); }
};

async function openEditFournisseur(id) {
  const f = fournisseursAll.find(x => x.id === id);
  if (!f) return;
  const backdrop = document.createElement('div');
  backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:800;display:flex;align-items:center;justify-content:center;padding:16px';
  const dlg = document.createElement('div');
  dlg.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto';
  dlg.innerHTML = '<h3 style="margin:0 0 12px;font-size:16px">Modifier le fournisseur</h3>' +
    '<label class="sub">Nom</label><input id="ef-nom" value="' + esc(f.nom) + '" style="margin-bottom:10px">' +
    '<label class="sub">Licence FSC</label><input id="ef-licence" value="' + esc(f.licence || '') + '" style="margin-bottom:10px" placeholder="ex: FSC-C004451">' +
    '<label class="sub">Certificat FSC</label><input id="ef-certificat" value="' + esc(f.certificat || '') + '" style="margin-bottom:10px" placeholder="ex: CU-COC-807907">' +
    '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border)">' +
    '<p style="margin:0 0 10px;font-size:13px;font-weight:600;color:var(--text)">Code-barre de traçabilité</p>' +
    '<p style="margin:0 0 10px;font-size:12px;color:var(--text2)">Aide pour les opérateurs : quel code scanner sur les bobines de ce fournisseur.</p>' +
    '<label class="sub">Photo de l\'étiquette</label>' +
    '<div id="ef-photo-preview" style="margin-bottom:10px"></div>' +
    '<input type="file" id="ef-photo-input" accept="image/*" style="display:none">' +
    '<div style="display:flex;gap:8px;margin-bottom:12px">' +
    '<button type="button" class="btn btn-sec" id="ef-photo-pick" style="font-size:12px">Choisir une photo</button>' +
    '<button type="button" class="btn btn-sec" id="ef-photo-del" style="font-size:12px;color:var(--danger);display:none">Supprimer la photo</button></div>' +
    '<label class="sub">Explication (emplacement, description du code)</label>' +
    '<textarea id="ef-traca-exp" placeholder="Ex: Scanner le code en bas à gauche de l\'étiquette bobine — code EAN-13 commençant par 376" ' +
    'style="width:100%;min-height:72px;resize:vertical;margin-bottom:10px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:13px;box-sizing:border-box"></textarea>' +
    '<label class="sub">Exemple de code (scanner une vraie étiquette pour le remplir)</label>' +
    '<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">' +
    '<input type="text" id="ef-traca-code" placeholder="Ex: 3760123456789" style="flex:1;font-family:monospace">' +
    '<button type="button" class="btn btn-sec" id="ef-scan-example" style="font-size:12px;white-space:nowrap">Scanner</button></div>' +
    '<p class="sub" style="margin-top:4px;font-size:11px">Utilisez « Scanner » pour remplir automatiquement en scannant une vraie bobine.</p></div>' +
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
    '<button type="button" class="btn btn-sec" id="ef-cancel">Annuler</button>' +
    '<button type="button" class="btn" id="ef-save">Enregistrer</button></div>';

  const expEl = dlg.querySelector('#ef-traca-exp');
  const codeEl = dlg.querySelector('#ef-traca-code');
  const photoPreview = dlg.querySelector('#ef-photo-preview');
  const photoInput = dlg.querySelector('#ef-photo-input');
  const photoDelBtn = dlg.querySelector('#ef-photo-del');
  expEl.value = f.traca_explication || '';
  codeEl.value = f.traca_exemple_code || '';

  function refreshPhotoPreview(url) {
    if (url) {
      photoPreview.innerHTML = '<img src="' + esc(url) + '" alt="" style="max-width:100%;max-height:200px;border-radius:8px;border:1px solid var(--border);display:block;margin-bottom:4px">';
      photoDelBtn.style.display = '';
    } else {
      photoPreview.innerHTML = '<p class="sub" style="margin:0 0 8px;font-size:12px">Aucune photo</p>';
      photoDelBtn.style.display = 'none';
    }
  }
  refreshPhotoPreview(f.traca_photo_url || null);

  dlg.querySelector('#ef-photo-pick').onclick = () => photoInput.click();
  photoInput.onchange = async () => {
    const file = photoInput.files[0];
    photoInput.value = '';
    if (!file) return;
    const fd = new FormData();
    fd.append('photo', file);
    try {
      const res = await fetch(API + '/api/fournisseurs/' + id + '/traca-photo', { method: 'POST', credentials: 'include', body: fd });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = j.detail;
        const msg = typeof d === 'string' ? d : (Array.isArray(d) && d[0] && d[0].msg ? d[0].msg : 'Erreur upload');
        throw new Error(msg);
      }
      refreshPhotoPreview(j.url);
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) fi.traca_photo_url = j.url;
      toast('Photo enregistrée');
    } catch (e) { toast(e.message, true); }
  };

  photoDelBtn.onclick = async () => {
    if (!confirm('Supprimer la photo ?')) return;
    try {
      const res = await fetch(API + '/api/fournisseurs/' + id + '/traca-photo', { method: 'DELETE', credentials: 'include' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof j.detail === 'string' ? j.detail : 'Erreur');
      refreshPhotoPreview(null);
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) fi.traca_photo_url = null;
      toast('Photo supprimée');
    } catch (e) { toast(e.message, true); }
  };

  dlg.querySelector('#ef-scan-example').onclick = async () => {
    try {
      if (typeof startTracaExampleScan !== 'function') return;
      await startTracaExampleScan(function(code) { if (code) codeEl.value = code; });
    } catch (e) {}
  };

  dlg.querySelector('#ef-cancel').onclick = () => backdrop.remove();
  dlg.querySelector('#ef-save').onclick = async () => {
    const body = {
      nom: dlg.querySelector('#ef-nom').value.trim(),
      licence: dlg.querySelector('#ef-licence').value.trim(),
      certificat: dlg.querySelector('#ef-certificat').value.trim(),
      traca_explication: expEl.value.trim(),
      traca_exemple_code: codeEl.value.trim(),
    };
    if (!body.nom) return toast('Nom requis', true);
    try {
      await api('/api/fournisseurs/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const fi = fournisseursAll.find(x => x.id === id);
      if (fi) {
        fi.traca_explication = body.traca_explication || null;
        fi.traca_exemple_code = body.traca_exemple_code || null;
        fi.nom = body.nom;
        fi.licence = body.licence || null;
        fi.certificat = body.certificat || null;
      }
      toast('Fournisseur mis à jour');
      backdrop.remove();
      await loadFournisseurs();
    } catch (e) { toast(e.message, true); }
  };
  backdrop.appendChild(dlg);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
}

async function deleteFournisseur(id) {
  const f = fournisseursAll.find(x => x.id === id);
  if (!f) return;
  if (!confirm('Supprimer le fournisseur "' + f.nom + '" ?')) return;
  try {
    await api('/api/fournisseurs/' + id, { method: 'DELETE' });
    toast('Fournisseur supprimé');
    await loadFournisseurs();
  } catch (e) { toast(e.message, true); }
}

// Historique par fournisseur
function fillFourHistSelect() {
  const sel = document.getElementById('fh-four');
  if (!sel) return;
  const val = sel.value;
  sel.innerHTML = '<option value="">— Choisir un fournisseur —</option>' +
    fournisseursAll.map(f => '<option value="' + f.id + '">' + esc(f.nom) + '</option>').join('');
  sel.value = val;
}

document.getElementById('fh-four').addEventListener('change', async function() {
  const id = Number(this.value);
  const box = document.getElementById('fh-results');
  if (!id) { box.innerHTML = ''; return; }
  box.innerHTML = '<p class="sub">Chargement…</p>';
  try {
    const data = await api('/api/fournisseurs/' + id + '/receptions');
    const recs = data.receptions || [];
    if (!recs.length) {
      box.innerHTML = '<p class="sub">Aucune réception pour ce fournisseur.</p>';
      return;
    }
    box.innerHTML = '<div class="table-wrap"><table><thead><tr><th>Date</th><th>Opérateur</th><th>Bobines</th><th>Certificat FSC</th><th>Note</th></tr></thead><tbody>' +
      recs.map(r => '<tr>' +
        '<td style="font-family:monospace;font-size:12px">' + esc((r.created_at || '').slice(0, 16).replace('T', ' ')) + '</td>' +
        '<td>' + esc(r.created_by_name || '—') + '</td>' +
        '<td>' + esc(r.nb_bobines) + '</td>' +
        '<td><code>' + esc(r.certificat_fsc || '—') + '</code></td>' +
        '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">' + esc(r.note || '') + '</td>' +
      '</tr>').join('') + '</tbody></table></div>';
  } catch (e) { box.innerHTML = '<p class="sub" style="color:var(--danger)">' + esc(e.message) + '</p>'; }
});

(async function init() {
  try {
    const meta = await api('/api/settings/access-matrix');
    superadminEmailRef = String(meta.superadmin_email || '').trim().toLowerCase();
    assignableRoles = meta.assignable_roles || [];
    roleLabels = meta.role_labels || {};
    apps = meta.apps || [];
    fillRoleSelect();
    fillRoleFilterSelect();
    await refreshSidebarUser();
    initSupportSidebar();
    await loadFilters();
    await loadMachines();
    syncCuRoleUI();
    await loadUsers();
    await loadMatrix();
  } catch (e) {
    toast(e.message || 'Erreur chargement', true);
  }
})();

// ── Mises à jour ──────────────────────────────────────────────────────────────
const SCOPE_LABELS = { planning: '📋 Planning', fabrication: '⚙️ Saisie de prod.', global: '🌐 Global' };

let _updatesData = [];
let _openAckId = null;

async function loadUpdates() {
  const box = document.getElementById('upd-list');
  if (!box) return;
  try {
    _updatesData = await api('/api/updates') || [];
    renderUpdatesList();
  } catch(e) {
    box.innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
  }
}

function toParisTime(isoStr) {
  if (!isoStr) return '—';
  try {
    // acknowledged_at est stocké en UTC (datetime.now() côté serveur)
    const d = new Date(isoStr.includes('T') ? isoStr + 'Z' : isoStr);
    return d.toLocaleString('fr-FR', {
      timeZone: 'Europe/Paris',
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch(e) { return isoStr.slice(0, 16).replace('T', ' '); }
}

function renderUpdatesList() {
  const box = document.getElementById('upd-list');
  if (!_updatesData.length) {
    box.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune annonce pour le moment.</p>';
    return;
  }
  box.innerHTML = _updatesData.map(u => {
    const scopeLbl = SCOPE_LABELS[u.scope] || u.scope;
    const dt = u.created_at ? u.created_at.slice(0, 10).split('-').reverse().join('/') : '—';
    const activeTag = u.active
      ? '<span style="font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(52,211,153,.15);color:#34d399;border:1px solid rgba(52,211,153,.3);font-weight:700">Actif</span>'
      : '<span style="font-size:10px;padding:2px 7px;border-radius:999px;background:rgba(148,163,184,.12);color:var(--muted);border:1px solid var(--border);font-weight:700">Archivé</span>';
    const ackCount = u.nb_ack || 0;
    const isOpen = _openAckId === u.id;
    return `
<div style="border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:10px">
  <div style="display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;background:var(--card)" onclick="toggleAck(${u.id})">
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
        <span style="font-size:12px;color:var(--muted)">${esc(scopeLbl)}</span>
        <span style="font-size:11px;color:var(--muted)">·</span>
        <span style="font-size:12px;color:var(--muted)">${dt}</span>
        ${activeTag}
      </div>
      <div style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(u.titre)}</div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <div style="font-size:18px;font-weight:800;color:var(--accent)">${ackCount}</div>
      <div style="font-size:10px;color:var(--muted)">lecture(s)</div>
    </div>
    <button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();showUpdatePreview(${u.id})">Aperçu</button>
    ${ackCount === 0 ? `<button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();openEditUpdateModal(${u.id})">Modifier</button><button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px;color:var(--danger);border-color:var(--danger)" onclick="event.stopPropagation();deleteUpdate(${u.id})">Supprimer</button>` : ''}
    <button type="button" class="btn btn-sec" style="padding:5px 10px;font-size:11px" onclick="event.stopPropagation();toggleActive(${u.id},${u.active})">${u.active ? 'Archiver' : 'Réactiver'}</button>
    <span style="font-size:16px;color:var(--muted);transition:transform .2s;${isOpen ? 'transform:rotate(180deg)' : ''}">▾</span>
  </div>
  <div id="ack-panel-${u.id}" style="display:${isOpen ? 'block' : 'none'};border-top:1px solid var(--border);padding:14px 16px;background:rgba(0,0,0,.08)">
    <div id="ack-content-${u.id}"><em style="color:var(--muted);font-size:13px">Chargement…</em></div>
  </div>
</div>`;
  }).join('');
}

function showUpdatePreview(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  const ov = document.createElement('div');
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:900;display:flex;align-items:center;justify-content:center';
  ov.innerHTML = `<div style="background:var(--card);border:1px solid var(--border2);border-radius:16px;padding:28px;width:min(560px,95vw);max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.6)">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px">
      <div>
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:4px">${esc(SCOPE_LABELS[u.scope]||u.scope)}</div>
        <h2 style="font-size:16px;margin:0">${esc(u.titre)}</h2>
      </div>
      <button onclick="this.closest('[style*=fixed]').remove()" style="border:none;background:none;color:var(--muted);font-size:22px;cursor:pointer;padding:0 0 0 12px;line-height:1;flex-shrink:0">×</button>
    </div>
    <div style="font-size:13px;line-height:1.7;color:var(--text2)">${u.message}</div>
    <button class="btn" style="width:100%;margin-top:20px;padding:12px;font-size:14px" onclick="this.closest('[style*=fixed]').remove()">Fermer</button>
  </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function toggleAck(id) {
  if (_openAckId === id) {
    _openAckId = null;
    renderUpdatesList();
    return;
  }
  _openAckId = id;
  renderUpdatesList();
  const contentEl = document.getElementById('ack-content-' + id);
  if (!contentEl) return;
  try {
    const data = await api('/api/updates/' + id + '/acknowledgements');
    const acks = data.acknowledgements || [];
    if (!acks.length) {
      contentEl.innerHTML = '<p style="color:var(--muted);font-size:13px;margin:0">Personne n\'a encore lu cette annonce.</p>';
      return;
    }
    contentEl.innerHTML = '<div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">' + acks.length + ' lecture(s)</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:6px">' +
      acks.map(a => {
        const dt = toParisTime(a.acknowledged_at);
        return `<div style="padding:6px 10px;border-radius:8px;background:var(--bg);border:1px solid var(--border);font-size:12px">
          <strong>${esc(a.user_nom || a.email || '—')}</strong>
          ${a.email && a.user_nom ? '<span style="color:var(--muted);margin-left:4px">' + esc(a.email) + '</span>' : ''}
          <div style="font-size:10px;color:var(--muted);margin-top:2px">${esc(dt)}</div>
        </div>`;
      }).join('') + '</div>';
  } catch(e) {
    contentEl.innerHTML = '<p style="color:var(--danger);font-size:13px">' + esc(e.message) + '</p>';
  }
}

async function toggleActive(id, current) {
  try {
    await api('/api/updates/' + id, { method: 'PATCH', body: JSON.stringify({ active: !current }), headers: { 'Content-Type': 'application/json' } });
    toast(current ? 'Annonce archivée' : 'Annonce réactivée');
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

function openNewUpdateModal() {
  const ov = document.getElementById('upd-modal-overlay');
  if (ov) { ov.style.display = 'flex'; ov.classList.remove('hidden'); }
}
function closeNewUpdateModal() {
  const ov = document.getElementById('upd-modal-overlay');
  if (ov) { ov.style.display = 'none'; ov.classList.add('hidden'); }
}
async function submitNewUpdate() {
  const scope   = document.getElementById('nm-scope').value;
  const titre   = (document.getElementById('nm-titre').value || '').trim();
  const message = (document.getElementById('nm-message').value || '').trim();
  const active  = Number(document.getElementById('nm-active').value);
  if (!titre || !message) { toast('Titre et message sont requis', true); return; }
  try {
    await api('/api/updates', { method: 'POST', body: JSON.stringify({ scope, titre, message, active }), headers: { 'Content-Type': 'application/json' } });
    toast('Annonce créée ✅');
    closeNewUpdateModal();
    document.getElementById('nm-titre').value = '';
    document.getElementById('nm-message').value = '';
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

let _editingUpdateId = null;

function openEditUpdateModal(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  _editingUpdateId = id;
  document.getElementById('edit-nm-scope').value = u.scope || 'planning';
  document.getElementById('edit-nm-titre').value = u.titre || '';
  document.getElementById('edit-nm-message').value = u.message || '';
  document.getElementById('edit-nm-active').value = u.active ? '1' : '0';
  const ov = document.getElementById('edit-upd-modal-overlay');
  if (ov) { ov.style.display = 'flex'; ov.classList.remove('hidden'); }
}

function closeEditUpdateModal() {
  const ov = document.getElementById('edit-upd-modal-overlay');
  if (ov) { ov.style.display = 'none'; ov.classList.add('hidden'); }
  _editingUpdateId = null;
}

async function submitEditUpdate() {
  if (!_editingUpdateId) return;
  const scope   = document.getElementById('edit-nm-scope').value;
  const titre   = (document.getElementById('edit-nm-titre').value || '').trim();
  const message = (document.getElementById('edit-nm-message').value || '').trim();
  const active  = Number(document.getElementById('edit-nm-active').value);
  if (!titre || !message) { toast('Titre et message sont requis', true); return; }
  try {
    await api('/api/updates/' + _editingUpdateId, { method: 'PATCH', body: JSON.stringify({ scope, titre, message, active }), headers: { 'Content-Type': 'application/json' } });
    toast('Annonce modifiée ✅');
    closeEditUpdateModal();
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}

async function deleteUpdate(id) {
  const u = _updatesData.find(x => x.id === id);
  if (!u) return;
  if (u.nb_ack > 0) { toast('Impossible de supprimer une annonce déjà lue', true); return; }
  if (!confirm('Supprimer définitivement cette annonce ?')) return;
  try {
    await api('/api/updates/' + id, { method: 'DELETE' });
    toast('Annonce supprimée ✅');
    await loadUpdates();
  } catch(e) { toast(e.message, true); }
}
</script>
</body>
</html>
"""
