"""MySifa — Page /rapports-prod : retour atelier et comptes-rendus de dossier.

Deux onglets, deux publics :

- « Retour atelier » : une feuille par machine et par semaine, concue pour etre
  imprimee et affichee a la machine. Par machine, jamais par personne — voir
  la note de conception dans `app/services/rapport_dossier.retour_atelier`.
- « Comptes-rendus » : la liste centralisee des dossiers clotures sur la
  periode, une ligne par dossier, ouverte au clic sur le detail complet.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLES_PROD
from services.auth_service import effective_role, get_current_user
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/rapports-prod", response_class=HTMLResponse)
def rapports_prod_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/rapports-prod", status_code=302)
        raise
    role = effective_role(user)
    if role not in ROLES_PROD:
        return access_denied_response(
            "Retour de production",
            detail="Ce module est reserve aux services de production.",
        )
    return HTMLResponse(
        content=RAPPORTS_PROD_HTML
        .replace("__V_LABEL__", f"v{APP_VERSION}")
    )


RAPPORTS_PROD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Retour de production — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<script src="/static/mysifa_theme.js"></script>
<script>try{ if(window.MySifaTheme){ MySifaTheme.initFromStorage(); } }catch(e){}</script>
<style>
/* tokens : static/mysifa_theme.css — ici, seulement les écarts */
:root{--ok:#34d399;}
body.light{--muted:#64748b;--ok:#059669;}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.layout{display:flex;min-height:100vh}
.sidebar{width:220px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:sticky;top:0;overflow-y:auto;scrollbar-width:none}
.sidebar::-webkit-scrollbar{width:0}
.logo{font-size:15px;font-weight:800;margin-bottom:20px;padding:0 8px}
.logo span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-scroll{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s;margin-bottom:2px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px;width:100%;font-family:inherit}
.theme-btn:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.logout-btn{border:none}
.logout-btn:hover{color:var(--danger);background:rgba(248,113,113,.1)}
.version{font-size:10px;color:var(--muted);font-family:monospace;padding:4px 12px}
.main{flex:1;padding:24px 28px;overflow:auto}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200}
body.sb-open .sidebar-overlay{display:block}
h1{font-size:22px;margin:0 0 6px}
.sub{color:var(--muted);font-size:13px;margin-bottom:22px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:20px;padding:14px 16px;background:var(--card);border:1px solid var(--border);border-radius:12px}
.toolbar label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.toolbar input,.toolbar select{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit}
.toolbar input:focus,.toolbar select:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.btn{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:9px 16px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}
.btn:hover{filter:brightness(1.06)}
.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.tab-panel{display:none}
.tab-panel.active{display:block}
.loading{color:var(--muted);font-size:13px;text-align:center;padding:40px 0}
.vide{color:var(--muted);font-size:13px;padding:28px 0;text-align:center;line-height:1.6}

/* ── Feuille atelier ─────────────────────────────────────────── */
.feuille{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px 26px}
.f-tete{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;
  border-bottom:2px solid var(--border);padding-bottom:14px;margin-bottom:18px}
.f-machine{font-size:26px;font-weight:800;color:var(--text);line-height:1.1}
.f-periode{font-size:13px;color:var(--muted);margin-top:4px}
.f-equipe{font-size:12px;color:var(--text2);max-width:340px;text-align:right;line-height:1.5}
.f-equipe b{color:var(--text)}
.f-bloc{margin-bottom:22px}
.f-titre{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--accent);margin-bottom:10px}
.kpis{display:flex;flex-wrap:wrap;gap:26px}
.kpi .k-lbl{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.kpi .k-val{font-size:24px;font-weight:800;color:var(--text);line-height:1.2}
.kpi .k-sub{font-size:11px;color:var(--muted)}
table.grille{width:100%;border-collapse:collapse;font-size:13px}
table.grille th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  font-weight:700;padding:6px 8px;border-bottom:1px solid var(--border)}
table.grille td{padding:8px;border-bottom:1px solid var(--border);color:var(--text2)}
table.grille td.num{text-align:right;font-variant-numeric:tabular-nums}
table.grille tr:last-child td{border-bottom:none}
.ecart{font-weight:700;font-variant-numeric:tabular-nums}
.ecart.up{color:var(--ok)}
.ecart.down{color:var(--warn,#fbbf24)}
.ecart.none{color:var(--muted);font-weight:500}
.mot{border-left:2px solid var(--accent);padding:8px 12px;margin-bottom:10px;background:var(--bg);border-radius:0 8px 8px 0}
.mot .m-txt{font-size:13px;color:var(--text);line-height:1.55}
.mot .m-meta{font-size:11px;color:var(--muted);margin-top:5px}
.mot .m-tag{display:inline-block;font-size:10px;text-transform:uppercase;letter-spacing:.5px;
  padding:1px 7px;border-radius:999px;border:1px solid var(--border);margin-right:6px;color:var(--text2)}
.vig{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--text2);
  padding:8px 0;border-bottom:1px solid var(--border);line-height:1.5}
.vig:last-child{border-bottom:none}
.vig .v-nb{flex-shrink:0;font-weight:800;color:var(--warn,#fbbf24);min-width:22px}
.f-pied{border-top:1px solid var(--border);margin-top:20px;padding-top:12px;font-size:11px;color:var(--muted);text-align:center}

/* ── Liste des comptes-rendus ────────────────────────────────── */
table.cr{width:100%;border-collapse:collapse;font-size:13px;background:var(--card);
  border:1px solid var(--border);border-radius:12px;overflow:hidden}
table.cr th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  font-weight:700;padding:10px;background:var(--bg);border-bottom:1px solid var(--border)}
table.cr td{padding:10px;border-bottom:1px solid var(--border);color:var(--text2)}
table.cr tbody tr{cursor:pointer}
table.cr tbody tr:hover{background:var(--accent-bg)}
table.cr td.num{text-align:right;font-variant-numeric:tabular-nums}
.pastille{display:inline-block;font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;
  border:1px solid var(--border);color:var(--muted);white-space:nowrap}
.pastille.on{color:var(--ok);border-color:var(--ok)}
.pastille.att{color:var(--warn,#fbbf24);border-color:var(--warn,#fbbf24)}

/* ── Modal detail ────────────────────────────────────────────── */
.modal-ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;
  align-items:flex-start;justify-content:center;padding:40px 16px;overflow:auto}
.modal-ov.open{display:flex}
.modal-card{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:24px 26px;width:min(920px,96vw)}
.modal-card h3{margin:0 0 4px;font-size:19px;color:var(--text)}
.m-close{float:right;background:transparent;border:1px solid var(--border);color:var(--text2);
  border-radius:8px;padding:5px 11px;cursor:pointer;font-family:inherit;font-size:13px}
#toast{position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:10px;color:#fff;font-size:13px;
  font-weight:600;z-index:9999;display:none;box-shadow:0 6px 24px rgba(0,0,0,.35)}
#toast.danger{background:var(--danger)}
#toast.info{background:var(--accent);color:var(--bg)}
.mobile-topbar{display:none}
@media (max-width:900px){
  .sidebar{width:min(280px,88vw);position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .2s}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-topbar{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card);border-bottom:1px solid var(--border)}
  .mobile-menu-btn{background:transparent;border:none;color:var(--text);cursor:pointer}
  .main{padding:16px}
  .f-equipe{text-align:left;max-width:none}
}

/* ── Impression : la feuille seule, en noir sur blanc ────────── */
@media print{
  @page{size:A4;margin:12mm}
  .sidebar,.sidebar-overlay,.mobile-topbar,.toolbar,#toast,.modal-ov,h1,.sub{display:none !important}
  body,.layout,.main{background:#fff !important;color:#000 !important;display:block;padding:0;margin:0}
  .feuille{border:none;border-radius:0;padding:0;background:#fff !important;color:#000 !important}
  .f-machine,.kpi .k-val,.mot .m-txt,table.grille td{color:#000 !important}
  .f-titre{color:#000 !important;border-bottom:1px solid #000;padding-bottom:3px}
  .f-periode,.kpi .k-lbl,.kpi .k-sub,.mot .m-meta,table.grille th,.f-pied{color:#444 !important}
  .f-tete,table.grille th,table.grille td,.vig{border-color:#bbb !important}
  .mot{background:#f5f5f5 !important;border-left:2px solid #000}
  .ecart.up,.ecart.down,.vig .v-nb{color:#000 !important}
  .f-bloc{break-inside:avoid}
  .tab-panel{display:none !important}
  .tab-panel.active{display:block !important}
}
</style>
<link rel="stylesheet" href="/static/mysifa_perf.css">
<script src="/static/mysifa_perf.js"></script>
</head>
<body>
<div class="sidebar-overlay" id="sb-ov"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="logo">My<span>Sifa</span><div class="logo-sub">Retour de prod</div></div>
    <div class="nav-scroll">
      <button type="button" class="nav-btn active" id="nav-feuille" onclick="switchTab('feuille')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></svg>
        Retour atelier
      </button>
      <button type="button" class="nav-btn" id="nav-liste" onclick="switchTab('liste')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
        Comptes-rendus
      </button>
    </div>
    <div class="sidebar-bottom">
      <button type="button" class="nav-btn" onclick="location.href='/'">← Retour <b>MySifa</b></button>
      <div class="user-chip" id="sb-user-chip" onclick="location.href='/profil'"></div>
      <button type="button" class="theme-btn" id="theme-btn"><span>Changer de mode</span></button>
      <button type="button" class="logout-btn" id="logout-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Déconnexion
      </button>
      <div class="version">Retour de prod · MySifa __V_LABEL__</div>
    </div>
  </aside>
  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="document.body.classList.toggle('sb-open')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div><b>Retour de production</b></div>
    </div>
    <h1>Retour de production</h1>
    <div class="sub" id="page-sub">Ce qui est sorti des machines la semaine passée, et ce que les conducteurs en ont écrit.</div>

    <div class="toolbar">
      <div>
        <label for="wk-input">Semaine ISO</label>
        <input type="week" id="wk-input">
      </div>
      <div id="machine-wrap">
        <label for="machine-select">Machine</label>
        <select id="machine-select"><option value="">—</option></select>
      </div>
      <div style="flex:1"></div>
      <button class="btn btn-ghost" id="btn-refresh">Actualiser</button>
      <button class="btn" id="btn-print">Imprimer la feuille</button>
    </div>

    <div id="tab-feuille" class="tab-panel active">
      <div id="feuille"><div class="loading">Chargement…</div></div>
    </div>

    <div id="tab-liste" class="tab-panel">
      <div id="liste"><div class="loading">Chargement…</div></div>
    </div>
  </main>
</div>
<div class="modal-ov" id="mov"><div class="modal-card" id="mroot"></div></div>
<div id="toast"></div>
<script>
const S = { year:null, week:null, machine:"", machines:[], semaine:null };

function escHtml(s){
  if(s===null||s===undefined) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
                  .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}
function escAttr(s){ return escHtml(s).replace(/"/g,"&quot;"); }

async function api(path){
  const r = await fetch(path, { credentials:"include" });
  if(!r.ok){
    let msg = "Erreur " + r.status;
    try { const j = await r.json(); if(j && j.detail) msg = j.detail; } catch(e){}
    throw new Error(msg);
  }
  return r.json();
}

function showToast(msg, type){
  const t = document.getElementById("toast");
  t.textContent = msg; t.className = type || "info"; t.style.display = "block";
  setTimeout(() => { t.style.display = "none"; }, 4000);
}

function fnum(v, digits){
  if(v === null || v === undefined || isNaN(v)) return "—";
  const s = Number(v).toFixed(digits || 0);
  return s.replace(/\B(?=(\d{3})+(?!\d))/g, " ").replace(".", ",");
}
function minutesTxt(m){
  if(m === null || m === undefined || isNaN(m)) return "—";
  const t = Math.round(Number(m));
  if(t < 60) return t + " min";
  const h = Math.floor(t/60), r = t%60;
  return r === 0 ? h + " h" : h + " h " + String(r).padStart(2,"0");
}
function ecartHtml(pct){
  if(pct === null || pct === undefined || isNaN(pct))
    return '<span class="ecart none">pas de repère</span>';
  const v = Number(pct);
  const cls = v >= 0 ? "up" : "down";
  const signe = v >= 0 ? "+" : "";
  return '<span class="ecart ' + cls + '">' + signe + v.toFixed(0).replace(".", ",") + ' %</span>';
}
function dateFr(iso){
  if(!iso) return "";
  const d = String(iso).slice(0,10).split("-");
  return d.length === 3 ? d[2] + "/" + d[1] + "/" + d[0] : String(iso);
}

/* ── Semaine ─────────────────────────────────────────────────── */

function isoSemainePrecedente(){
  const d = new Date();
  d.setDate(d.getDate() - 7);
  const jeudi = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  jeudi.setUTCDate(jeudi.getUTCDate() + 4 - (jeudi.getUTCDay() || 7));
  const debutAnnee = new Date(Date.UTC(jeudi.getUTCFullYear(), 0, 1));
  const num = Math.ceil((((jeudi - debutAnnee) / 86400000) + 1) / 7);
  return { year: jeudi.getUTCFullYear(), week: num };
}

function lireSemaineInput(){
  const v = (document.getElementById("wk-input").value || "").trim();
  const m = v.match(/^(\d{4})-W(\d{2})$/);
  if(!m) return isoSemainePrecedente();
  return { year: parseInt(m[1], 10), week: parseInt(m[2], 10) };
}

function ecrireSemaineInput(year, week){
  document.getElementById("wk-input").value = year + "-W" + String(week).padStart(2, "0");
}

/* ── Chargement ──────────────────────────────────────────────── */

async function loadSemaine(){
  const s = lireSemaineInput();
  S.year = s.year; S.week = s.week;
  const d = await api('/api/rapports-prod/semaine?year=' + S.year + '&week=' + S.week);
  S.semaine = d;
  S.machines = d.machines || [];
  const sel = document.getElementById("machine-select");
  const avant = S.machine;
  sel.innerHTML = S.machines.length
    ? S.machines.map(m => '<option value="' + escAttr(m) + '">' + escHtml(m) + '</option>').join("")
    : '<option value="">Aucune machine sur la semaine</option>';
  if(S.machines.indexOf(avant) >= 0) sel.value = avant;
  S.machine = sel.value || "";
  document.getElementById("page-sub").textContent =
    "Semaine " + d.week + " (" + d.year + "), du " + d.du + " au " + d.au
    + " — ce qui est sorti des machines, et ce que les conducteurs en ont écrit.";
}

async function loadFeuille(){
  const box = document.getElementById("feuille");
  if(!S.machine){
    box.innerHTML = '<div class="feuille"><div class="vide">Aucun dossier clôturé sur cette semaine.<br>'
      + 'Choisissez une autre semaine, ou vérifiez que les fins de production ont été saisies.</div></div>';
    return;
  }
  box.innerHTML = '<div class="loading">Chargement…</div>';
  try {
    const d = await api('/api/rapports-prod/retour-atelier?machine=' + encodeURIComponent(S.machine)
                        + '&year=' + S.year + '&week=' + S.week);
    box.innerHTML = renderFeuille(d);
  } catch(e){
    box.innerHTML = '<div class="feuille"><div class="vide">' + escHtml(e.message) + '</div></div>';
  }
}

async function loadListe(){
  const box = document.getElementById("liste");
  box.innerHTML = '<div class="loading">Chargement…</div>';
  try {
    const d = await api('/api/rapports-prod/comptes-rendus?year=' + S.year + '&week=' + S.week
                        + '&machine=' + encodeURIComponent(S.machine || ""));
    box.innerHTML = renderListe(d.lignes || []);
    document.querySelectorAll("tr[data-dossier]").forEach(tr => {
      tr.onclick = () => openCR(tr.getAttribute("data-dossier"));
    });
  } catch(e){
    box.innerHTML = '<div class="vide">' + escHtml(e.message) + '</div>';
  }
}

/* ── Rendu : feuille atelier ─────────────────────────────────── */

const LIB_VIGILANCE = {
  info_prod_absente:      "dossier clôturé sans info prod",
  seuils_sans_explication:"dossier avec un seuil d'arrêt non expliqué",
  saisie_ouverte:         "dossier avec une saisie restée ouverte d'un jour à l'autre",
  metrage_non_fiable:     "dossier sans métrage exploitable",
  arrets_eleves:          "dossier passé à plus de 30 % d'arrêts"
};
const LIB_ORIGINE = {
  info_prod:  "Info prod",
  arret:      "Arrêt expliqué",
  commentaire:"Commentaire de saisie",
  annulation: "Motif d'annulation"
};

function renderFeuille(d){
  const p = d.production || {};
  const sem = d.semaine || {};

  if(!d.dossiers){
    return '<div class="feuille">'
      + '<div class="f-tete"><div><div class="f-machine">' + escHtml(d.machine) + '</div>'
      + '<div class="f-periode">Semaine ' + escHtml(sem.week) + ' — du ' + escHtml(sem.du)
      + ' au ' + escHtml(sem.au) + '</div></div></div>'
      + '<div class="vide">Aucun dossier clôturé sur cette machine cette semaine.</div></div>';
  }

  let h = '<div class="feuille">';

  h += '<div class="f-tete">'
     + '<div><div class="f-machine">' + escHtml(d.machine) + '</div>'
     + '<div class="f-periode">Semaine ' + escHtml(sem.week) + ' — du ' + escHtml(sem.du)
     + ' au ' + escHtml(sem.au) + '</div></div>';
  if((d.conducteurs || []).length){
    h += '<div class="f-equipe"><b>Aux commandes cette semaine</b><br>'
       + d.conducteurs.map(escHtml).join(" · ") + '</div>';
  }
  h += '</div>';

  /* Ce qui est sorti de la machine */
  h += '<div class="f-bloc"><div class="f-titre">Ce qui est sorti de la machine</div><div class="kpis">'
     + kpi(fnum(p.metrage) + ' m', "Métrage produit", d.dossiers + (d.dossiers > 1 ? " dossiers" : " dossier"))
     + kpi(minutesTxt(p.minutes_production), "Temps de production",
           p.vitesse_m_h ? fnum(p.vitesse_m_h) + " m/h en moyenne" : "")
     + kpi(minutesTxt(p.minutes_calage), "Calage et changements", "")
     + kpi(minutesTxt(p.minutes_arret), "Arrêts et attentes",
           p.part_arret_pct ? fnum(p.part_arret_pct, 1) + " % du temps passé" : "")
     + '</div></div>';

  /* Références, comparées à leur propre historique */
  if((d.references || []).length){
    h += '<div class="f-bloc"><div class="f-titre">Cadence, comparée aux fois précédentes</div>'
       + '<div style="font-size:11.5px;color:var(--muted);margin-bottom:8px">'
       + 'Cadence = métrage rapporté au temps de production et d\'arrêt, arrêts compris — '
       + 'même calcul des deux côtés, pour que la comparaison ait un sens.</div>'
       + '<table class="grille"><thead><tr><th>Dossier</th><th>Référence</th>'
       + '<th style="text-align:right">Métrage</th><th style="text-align:right">Cette fois</th>'
       + '<th style="text-align:right">D\'habitude</th><th style="text-align:right">Écart</th></tr></thead><tbody>';
    d.references.forEach(r => {
      const hab = r.cadence_reference_m_h
        ? fnum(r.cadence_reference_m_h) + ' m/h<div style="font-size:10.5px;color:var(--muted)">sur '
          + r.series_passees + (r.series_passees > 1 ? ' productions' : ' production') + '</div>'
        : '<span style="color:var(--muted)">1re production</span>';
      h += '<tr><td><b>' + escHtml(r.no_dossier) + '</b></td>'
         + '<td>' + escHtml(r.ref_produit_norm || r.designation || "—") + '</td>'
         + '<td class="num">' + fnum(r.metrage) + ' m</td>'
         + '<td class="num">' + fnum(r.cadence_m_h) + ' m/h'
         + '<div style="font-size:10.5px;color:var(--muted)">' + fnum(r.vitesse_m_h)
         + ' m/h hors arrêts</div></td>'
         + '<td class="num">' + hab + '</td>'
         + '<td class="num">' + ecartHtml(r.ecart_pct) + '</td></tr>';
    });
    h += '</tbody></table></div>';
  }

  /* Ce qui a coûté du temps */
  if((d.arrets_couteux || []).length){
    h += '<div class="f-bloc"><div class="f-titre">Ce qui a coûté le plus de temps</div>'
       + '<table class="grille"><thead><tr><th>Code</th><th>Opération</th>'
       + '<th style="text-align:right">Occurrences</th><th style="text-align:right">Temps</th></tr></thead><tbody>';
    d.arrets_couteux.forEach(a => {
      h += '<tr><td><b>' + escHtml(a.code) + '</b></td>'
         + '<td>' + escHtml(a.operation || "—") + '</td>'
         + '<td class="num">' + a.occurrences + '</td>'
         + '<td class="num">' + escHtml(a.minutes_txt) + '</td></tr>';
    });
    h += '</tbody></table></div>';
  }

  /* Le retour proprement dit : ce que les conducteurs ont écrit */
  if((d.ecrits || []).length){
    h += '<div class="f-bloc"><div class="f-titre">Ce que vous avez écrit cette semaine</div>';
    d.ecrits.forEach(e => {
      h += '<div class="mot"><div class="m-txt">' + escHtml(e.texte) + '</div>'
         + '<div class="m-meta"><span class="m-tag">'
         + escHtml(LIB_ORIGINE[e.origine] || e.origine) + '</span>'
         + 'dossier ' + escHtml(e.no_dossier)
         + (e.operation ? ' · ' + escHtml(e.operation) : '')
         + (e.auteur ? ' · ' + escHtml(e.auteur) : '')
         + (e.date ? ' · ' + escHtml(dateFr(e.date)) : '')
         + '</div></div>';
    });
    h += '</div>';
  }

  /* Points de vigilance, comptés, jamais nominatifs */
  const vig = d.vigilance || {};
  const clesVig = Object.keys(vig).filter(k => vig[k] > 0);
  if(clesVig.length){
    h += '<div class="f-bloc"><div class="f-titre">À reprendre au point de production</div>';
    clesVig.forEach(k => {
      h += '<div class="vig"><div class="v-nb">' + vig[k] + '</div><div>'
         + escHtml(LIB_VIGILANCE[k] || k) + (vig[k] > 1 ? " (×" + vig[k] + ")" : "")
         + '</div></div>';
    });
    h += '</div>';
  }

  if(d.nb_nc){
    h += '<div class="f-bloc"><div class="f-titre">Qualité</div>'
       + '<div style="font-size:13px;color:var(--text2)">' + d.nb_nc
       + (d.nb_nc > 1 ? ' non-conformités rattachées' : ' non-conformité rattachée')
       + ' aux dossiers de la semaine.</div></div>';
  }

  h += '<div class="f-pied">MySifa · Retour de production · établi le '
     + escHtml(new Date().toLocaleDateString("fr-FR")) + '</div>';
  return h + '</div>';
}

function kpi(val, lbl, sub){
  return '<div class="kpi"><div class="k-lbl">' + escHtml(lbl) + '</div>'
       + '<div class="k-val">' + val + '</div>'
       + (sub ? '<div class="k-sub">' + escHtml(sub) + '</div>' : '') + '</div>';
}

/* ── Rendu : liste des comptes-rendus ────────────────────────── */

function renderListe(rows){
  if(!rows.length){
    return '<div class="vide">Aucun dossier clôturé sur cette période.<br>'
         + 'La liste se remplit à partir des saisies de fin de production.</div>';
  }
  let h = '<table class="cr"><thead><tr><th>Dossier</th><th>Client</th><th>Machine</th>'
        + '<th style="text-align:right">Métrage</th><th style="text-align:right">Vitesse</th>'
        + '<th style="text-align:right">Écart cadence</th><th>Info prod</th><th>Écrits</th>'
        + '<th>Seuils</th><th>NC</th></tr></thead><tbody>';
  rows.forEach(r => {
    const info = r.info_prod_substantielle
      ? '<span class="pastille on">renseignée</span>'
      : (r.info_prod ? '<span class="pastille">R.A.S.</span>'
                     : '<span class="pastille att">absente</span>');
    const seuils = r.nb_seuils
      ? (r.nb_seuils_sans_explication
          ? '<span class="pastille att">' + r.nb_seuils_sans_explication + ' sans mot</span>'
          : '<span class="pastille on">' + r.nb_seuils + ' expliqué' + (r.nb_seuils>1?'s':'') + '</span>')
      : '<span class="pastille">—</span>';
    h += '<tr data-dossier="' + escAttr(r.no_dossier) + '">'
       + '<td><b>' + escHtml(r.no_dossier) + '</b>'
       + '<div style="font-size:10.5px;color:var(--muted)">' + escHtml(dateFr(r.date_fin)) + '</div></td>'
       + '<td>' + escHtml(r.client || "—") + '</td>'
       + '<td>' + escHtml(r.machine || "—") + '</td>'
       + '<td class="num">' + fnum(r.metrage_reel) + ' m</td>'
       + '<td class="num">' + (r.vitesse_m_h ? fnum(r.vitesse_m_h) + ' m/h' : '—') + '</td>'
       + '<td class="num">' + ecartHtml(r.ecart_cadence_pct) + '</td>'
       + '<td>' + info + '</td>'
       + '<td class="num">' + (r.nb_commentaires || 0) + '</td>'
       + '<td>' + seuils + '</td>'
       + '<td class="num">' + (r.nb_nc || 0) + '</td></tr>';
  });
  return h + '</tbody></table>';
}

/* ── Rendu : compte-rendu complet ────────────────────────────── */

async function openCR(no){
  const mov = document.getElementById("mov");
  const root = document.getElementById("mroot");
  root.innerHTML = '<div class="loading">Chargement…</div>';
  mov.classList.add("open");
  try {
    const cr = await api('/api/rapports-prod/dossier/' + encodeURIComponent(no));
    root.innerHTML = renderCR(cr);
    document.getElementById("m-close").onclick = closeCR;
  } catch(e){
    root.innerHTML = '<button class="m-close" id="m-close">Fermer</button>'
                   + '<div class="vide">' + escHtml(e.message) + '</div>';
    document.getElementById("m-close").onclick = closeCR;
  }
}
function closeCR(){ document.getElementById("mov").classList.remove("open"); }

function renderCR(cr){
  const id = cr.identite || {}, t = cr.temps || {}, m = cr.metrage || {};
  let h = '<button class="m-close" id="m-close">Fermer</button>'
        + '<h3>' + escHtml(cr.no_dossier) + '</h3>'
        + '<div style="font-size:13px;color:var(--muted);margin-bottom:18px">'
        + escHtml(id.client || "—") + ' · ' + escHtml(id.designation || "—")
        + ' · ' + escHtml(id.machine || "—")
        + (id.ref_produit_norm ? ' · réf ' + escHtml(id.ref_produit_norm) : '')
        + '</div>';

  h += '<div class="f-bloc"><div class="kpis">'
     + kpi(fnum(m.reel) + ' m', "Métrage",
           m.prevu ? "prévu " + fnum(m.prevu) + " m" : (m.fiable ? "" : "non exploitable"))
     + kpi(cr.vitesse_m_h ? fnum(cr.vitesse_m_h) + ' m/h' : '—', "Vitesse de production", "hors arrêts")
     + kpi(cr.cadence_m_h ? fnum(cr.cadence_m_h) + ' m/h' : '—', "Cadence", "arrêts compris")
     + kpi(minutesTxt(t.total_minutes), "Temps passé", id.nb_saisies + " saisies")
     + kpi(escHtml((id.conducteurs || []).join(", ") || "—"), "Conducteurs", "")
     + '</div></div>';

  if((t.categories || []).length){
    h += '<div class="f-bloc"><div class="f-titre">Répartition du temps</div>'
       + '<table class="grille"><thead><tr><th>Poste</th><th style="text-align:right">Temps</th>'
       + '<th style="text-align:right">Part</th><th style="text-align:right">Occurrences</th>'
       + '</tr></thead><tbody>';
    t.categories.forEach(c => {
      h += '<tr><td>' + escHtml(c.label) + '</td>'
         + '<td class="num">' + minutesTxt(c.minutes) + '</td>'
         + '<td class="num">' + fnum(c.part_pct, 1) + ' %</td>'
         + '<td class="num">' + c.occurrences + '</td></tr>';
    });
    h += '</tbody></table></div>';
  }

  const info = (cr.ecrits || {}).info_prod;
  if(info){
    h += '<div class="f-bloc"><div class="f-titre">Info prod de clôture</div>'
       + '<div class="mot"><div class="m-txt">' + escHtml(info.texte) + '</div>'
       + '<div class="m-meta">' + escHtml(info.auteur || "") + ' · '
       + escHtml(dateFr(info.created_at)) + '</div></div></div>';
  }

  if((cr.seuils || []).length){
    h += '<div class="f-bloc"><div class="f-titre">Seuils d\'arrêt franchis</div>';
    cr.seuils.forEach(s => {
      h += '<div class="mot"><div class="m-txt">'
         + (s.explication_texte
             ? escHtml(s.explication_texte)
             : '<span style="color:var(--warn,#fbbf24)">Sans explication — à poser au point de production</span>')
         + '</div><div class="m-meta"><span class="m-tag">' + escHtml(s.operation_code) + '</span>'
         + escHtml(s.operation || "") + ' · ' + escHtml(s.duree_saisie_txt || "")
         + (s.operateur ? ' · ' + escHtml(s.operateur) : '') + '</div></div>';
    });
    h += '</div>';
  }

  const coms = (cr.ecrits || {}).commentaires || [];
  if(coms.length){
    h += '<div class="f-bloc"><div class="f-titre">Commentaires de saisie</div>';
    coms.forEach(c => {
      h += '<div class="mot"><div class="m-txt">' + escHtml(c.texte) + '</div>'
         + '<div class="m-meta"><span class="m-tag">'
         + escHtml(LIB_ORIGINE[c.origine] || c.origine) + '</span>'
         + escHtml(c.operateur || "") + ' · ' + escHtml(dateFr(c.date)) + '</div></div>';
    });
    h += '</div>';
  }

  if((cr.non_conformites || []).length){
    h += '<div class="f-bloc"><div class="f-titre">Non-conformités</div>'
       + '<table class="grille"><thead><tr><th>Numéro</th><th>Titre</th><th>Gravité</th>'
       + '<th>Statut</th></tr></thead><tbody>';
    cr.non_conformites.forEach(n => {
      h += '<tr><td><b>' + escHtml(n.numero) + '</b></td><td>' + escHtml(n.titre) + '</td>'
         + '<td>' + escHtml(n.gravite || "—") + '</td><td>' + escHtml(n.statut || "—") + '</td></tr>';
    });
    h += '</tbody></table></div>';
  }

  if((cr.vigilance || []).length){
    h += '<div class="f-bloc"><div class="f-titre">À reprendre</div>';
    cr.vigilance.forEach(v => {
      h += '<div class="vig"><div class="v-nb">·</div><div>' + escHtml(v.texte) + '</div></div>';
    });
    h += '</div>';
  }
  return h;
}

/* ── Navigation ──────────────────────────────────────────────── */

function switchTab(nom){
  ["feuille","liste"].forEach(n => {
    document.getElementById("tab-" + n).classList.toggle("active", n === nom);
    document.getElementById("nav-" + n).classList.toggle("active", n === nom);
  });
  try { location.hash = nom; } catch(e){}
  if(nom === "feuille") loadFeuille(); else loadListe();
}

async function tout(){
  try { await loadSemaine(); }
  catch(e){ showToast(e.message, "danger"); return; }
  const actif = document.getElementById("tab-feuille").classList.contains("active")
    ? "feuille" : "liste";
  if(actif === "feuille") loadFeuille(); else loadListe();
}

document.getElementById("btn-refresh").onclick = tout;
document.getElementById("wk-input").onchange = tout;
document.getElementById("machine-select").onchange = () => {
  S.machine = document.getElementById("machine-select").value || "";
  const actif = document.getElementById("tab-feuille").classList.contains("active")
    ? "feuille" : "liste";
  if(actif === "feuille") loadFeuille(); else loadListe();
};
document.getElementById("btn-print").onclick = () => {
  if(!document.getElementById("tab-feuille").classList.contains("active")) switchTab("feuille");
  setTimeout(() => window.print(), 150);
};
document.getElementById("mov").onclick = (e) => { if(e.target.id === "mov") closeCR(); };
document.addEventListener("keydown", (e) => { if(e.key === "Escape") closeCR(); });

document.getElementById("theme-btn").onclick = () => {
  try {
    if(window.MySifaTheme){ MySifaTheme.toggleMode(); }
    else { document.body.classList.toggle("light"); }
  } catch(e){ document.body.classList.toggle("light"); }
};
document.getElementById("logout-btn").onclick = async () => {
  try { await fetch("/api/auth/logout", { method:"POST", credentials:"include" }); } catch(e){}
  location.href = "/";
};
document.getElementById("sb-ov").onclick = () => document.body.classList.remove("sb-open");

(async () => {
  try {
    const r = await fetch("/api/auth/me", { credentials:"include" });
    if(!r.ok) return;
    const u = await r.json();
    document.getElementById("sb-user-chip").innerHTML =
      '<div class="uc-name">' + escHtml(u.nom || u.email || "Utilisateur") + '</div>'
      + '<div class="uc-role">' + escHtml(u.role || "") + '</div>';
    try { if(window.MySifaTheme) MySifaTheme.mergeFromUser(u); } catch(e){}
  } catch(e){}
})();

(function init(){
  const s = isoSemainePrecedente();
  ecrireSemaineInput(s.year, s.week);
  const h = (location.hash || "").replace("#", "");
  if(h === "liste"){
    document.getElementById("tab-feuille").classList.remove("active");
    document.getElementById("nav-feuille").classList.remove("active");
    document.getElementById("tab-liste").classList.add("active");
    document.getElementById("nav-liste").classList.add("active");
  }
  tout();
})();
</script>
</body>
</html>
"""
