"""MySifa — Page /rapports-prod : retour atelier et comptes-rendus de dossier.

Deux onglets, deux usages :

- « Retour atelier » : une feuille par machine et par periode, concue pour etre
  imprimee et affichee a la machine. Par machine, jamais par personne — voir la
  note de conception dans `app/services/rapport_dossier.retour_atelier`.
- « Comptes-rendus » : la liste des dossiers clotures sur la periode, plus une
  recherche qui atteint n'importe quel dossier, et le detail au clic.

Le rendu n'est pas ici : il vit dans `static/mysifa_retour_prod.js` et
`static/mysifa_retour_prod.css`, partages avec l'onglet « Retour de prod » de
MyProd. Cette page ne porte que sa coquille et son aiguillage — sinon les deux
ecrans divergent, et un dossier finit par afficher deux chiffres selon l'endroit
ou on le regarde.
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
    if effective_role(user) not in ROLES_PROD:
        return access_denied_response(
            "Retour de production",
            detail="Ce module est reserve aux services de production.",
        )
    return HTMLResponse(
        content=RAPPORTS_PROD_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
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
<link rel="stylesheet" href="/static/mysifa_retour_prod.css?v=__V_LABEL__">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_retour_prod.js?v=__V_LABEL__"></script>
<script>try{ if(window.MySifaTheme){ MySifaTheme.initFromStorage(); } }catch(e){}</script>
<style>
/* tokens : static/mysifa_theme.css — rendu : static/mysifa_retour_prod.css.
   Ici, seulement la coquille de la page. */
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
.chips{display:flex;gap:6px}
.chip{background:transparent;border:1px solid var(--border);color:var(--text2);border-radius:999px;padding:7px 13px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.tab-panel{display:none}
.tab-panel.active{display:block}
.loading{color:var(--muted);font-size:13px;text-align:center;padding:40px 0}
.modal-ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:800;align-items:flex-start;justify-content:center;padding:40px 16px;overflow:auto}
.modal-ov.open{display:flex}
.modal-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px 26px;width:min(920px,96vw)}
#toast{position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:10px;color:#fff;font-size:13px;font-weight:600;z-index:9999;display:none;box-shadow:0 6px 24px rgba(0,0,0,.35)}
#toast.danger{background:var(--danger)}
#toast.info{background:var(--accent);color:var(--bg)}
.mobile-topbar{display:none}
@media (max-width:900px){
  .sidebar{width:min(280px,88vw);position:fixed;left:0;top:0;bottom:0;z-index:300;transform:translateX(-105%);transition:transform .2s}
  body.sb-open .sidebar{transform:translateX(0)}
  .mobile-topbar{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card);border-bottom:1px solid var(--border)}
  .mobile-menu-btn{background:transparent;border:none;color:var(--text);cursor:pointer}
  .main{padding:16px}
}
@media print{
  @page{size:A4;margin:12mm}
  .sidebar,.sidebar-overlay,.mobile-topbar,.toolbar,#toast,.modal-ov,h1,.sub{display:none !important}
  body,.layout,.main{background:#fff !important;color:#000 !important;display:block;padding:0;margin:0}
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
      <button type="button" class="nav-btn" onclick="location.href='/prod'">← Retour <b>MyProd</b></button>
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
    <div class="sub" id="page-sub">Chargement…</div>

    <div class="toolbar">
      <div>
        <label for="mode-select">Période</label>
        <select id="mode-select">
          <option value="jour">Jour</option>
          <option value="semaine">Semaine</option>
        </select>
      </div>
      <div id="jour-wrap">
        <label for="jour-input">Date</label>
        <input type="date" id="jour-input">
      </div>
      <div id="wk-wrap" style="display:none">
        <label for="wk-input">Semaine ISO</label>
        <input type="week" id="wk-input">
      </div>
      <div>
        <label>Raccourcis</label>
        <div class="chips">
          <button type="button" class="chip" data-raccourci="hier">Hier</button>
          <button type="button" class="chip" data-raccourci="aujourdhui">Aujourd'hui</button>
          <button type="button" class="chip" data-raccourci="semaine-passee">Semaine passée</button>
        </div>
      </div>
      <div>
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
      <div class="rp-recherche">
        <label for="q-input">Ouvrir le compte-rendu de n'importe quel dossier</label>
        <input type="search" id="q-input" autocomplete="off"
               placeholder="N° de dossier, client ou désignation — même hors période">
        <div class="rp-note" style="margin-top:7px">La liste ci-dessous ne montre que les dossiers
          clôturés sur la période. La recherche, elle, atteint tous les dossiers ayant des saisies,
          clôturés ou en cours.</div>
        <div id="q-res"></div>
      </div>
      <div id="liste"><div class="loading">Chargement…</div></div>
    </div>
  </main>
</div>
<div class="modal-ov" id="mov"><div class="modal-card" id="mroot"></div></div>
<div id="toast"></div>
<script>
const RP = window.MySifaRetourProd;
const S = { mode:"jour", jour:null, year:null, week:null,
            machine:"", machines:[], periode:null, qTimer:null, dossierOuvert:null };

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

/* ── Période ─────────────────────────────────────────────────── */

function iso2(n){ return String(n).padStart(2, "0"); }
function dateISO(d){ return d.getFullYear() + "-" + iso2(d.getMonth()+1) + "-" + iso2(d.getDate()); }
function hier(){ const d = new Date(); d.setDate(d.getDate()-1); return dateISO(d); }

function semainePrecedente(){
  const d = new Date(); d.setDate(d.getDate() - 7);
  const jeudi = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  jeudi.setUTCDate(jeudi.getUTCDate() + 4 - (jeudi.getUTCDay() || 7));
  const debutAnnee = new Date(Date.UTC(jeudi.getUTCFullYear(), 0, 1));
  return { year: jeudi.getUTCFullYear(),
           week: Math.ceil((((jeudi - debutAnnee) / 86400000) + 1) / 7) };
}

function majVisibilitePeriode(){
  const jour = S.mode !== "semaine";
  document.getElementById("jour-wrap").style.display = jour ? "" : "none";
  document.getElementById("wk-wrap").style.display = jour ? "none" : "";
}

function lirePeriode(){
  S.mode = document.getElementById("mode-select").value || "jour";
  if(S.mode === "semaine"){
    const v = (document.getElementById("wk-input").value || "").trim();
    const m = v.match(/^(\d{4})-W(\d{2})$/);
    const d = m ? { year: parseInt(m[1],10), week: parseInt(m[2],10) } : semainePrecedente();
    S.year = d.year; S.week = d.week; S.jour = null;
  } else {
    S.jour = (document.getElementById("jour-input").value || "").trim() || hier();
    S.year = null; S.week = null;
  }
  majVisibilitePeriode();
}

function qsPeriode(){
  return S.mode === "semaine"
    ? "mode=semaine&year=" + S.year + "&week=" + S.week
    : "mode=jour&jour=" + encodeURIComponent(S.jour);
}

function majChips(){
  const h = hier(), a = dateISO(new Date());
  const actif = S.mode === "semaine" ? "semaine-passee"
              : (S.jour === h ? "hier" : (S.jour === a ? "aujourdhui" : ""));
  document.querySelectorAll(".chip[data-raccourci]").forEach(c => {
    c.classList.toggle("active", c.getAttribute("data-raccourci") === actif);
  });
}

/* ── Chargement ──────────────────────────────────────────────── */

async function loadPeriode(){
  lirePeriode();
  const d = await api('/api/rapports-prod/periode?' + qsPeriode());
  S.periode = d;
  S.machines = d.machines || [];
  const sel = document.getElementById("machine-select");
  const avant = S.machine;
  sel.innerHTML = S.machines.length
    ? S.machines.map(m => '<option value="' + RP.escAttr(m) + '">' + RP.escHtml(m) + '</option>').join("")
    : '<option value="">Aucune machine sur la période</option>';
  if(S.machines.indexOf(avant) >= 0) sel.value = avant;
  S.machine = sel.value || "";
  majChips();
  document.getElementById("page-sub").textContent =
    d.label + (d.mode === "semaine" ? " (du " + d.du + " au " + d.au + ")" : "")
    + " — ce qui est sorti des machines, et ce que les conducteurs en ont écrit.";
}

async function loadFeuille(){
  const box = document.getElementById("feuille");
  if(!S.machine){
    box.innerHTML = '<div class="rp-feuille"><div class="rp-vide">'
      + 'Aucun dossier clôturé sur cette période.<br>Choisissez une autre date, '
      + 'ou vérifiez que les fins de production ont été saisies.</div></div>';
    return;
  }
  box.innerHTML = '<div class="loading">Chargement…</div>';
  try {
    const d = await api('/api/rapports-prod/retour-atelier?machine='
                        + encodeURIComponent(S.machine) + '&' + qsPeriode());
    box.innerHTML = RP.renderFeuille(d);
  } catch(e){
    box.innerHTML = '<div class="rp-feuille"><div class="rp-vide">' + RP.escHtml(e.message) + '</div></div>';
  }
}

async function loadListe(){
  const box = document.getElementById("liste");
  box.innerHTML = '<div class="loading">Chargement…</div>';
  try {
    const d = await api('/api/rapports-prod/comptes-rendus?' + qsPeriode()
                        + '&machine=' + encodeURIComponent(S.machine || ""));
    box.innerHTML = RP.renderListe(d.lignes || []);
    box.querySelectorAll("tr[data-dossier]").forEach(tr => {
      tr.onclick = () => openCR(tr.getAttribute("data-dossier"));
    });
  } catch(e){
    box.innerHTML = '<div class="rp-vide">' + RP.escHtml(e.message) + '</div>';
  }
}

async function lancerRecherche(){
  const q = (document.getElementById("q-input").value || "").trim();
  const box = document.getElementById("q-res");
  if(q.length < 2){ box.innerHTML = ""; return; }
  try {
    const d = await api('/api/rapports-prod/recherche?q=' + encodeURIComponent(q));
    box.innerHTML = RP.renderRecherche(d.dossiers || [], q);
    box.querySelectorAll(".rp-rech-item").forEach(el => {
      el.onclick = () => openCR(el.getAttribute("data-dossier"));
    });
  } catch(e){
    box.innerHTML = '<div class="rp-note" style="margin-top:10px">' + RP.escHtml(e.message) + '</div>';
  }
}

/* ── Compte-rendu ────────────────────────────────────────────── */

async function openCR(no){
  const mov = document.getElementById("mov"), root = document.getElementById("mroot");
  S.dossierOuvert = no;
  root.innerHTML = '<div class="loading">Chargement…</div>';
  mov.classList.add("open");
  try {
    const cr = await api('/api/rapports-prod/dossier/' + encodeURIComponent(no));
    root.innerHTML = RP.renderCR(cr);
    document.getElementById("rp-close").onclick = closeCR;
    RP.brancher(no, {
      racine: root,
      toast: showToast,
      onSaved: () => { openCR(no); rechargerOngletActif(); }
    });
  } catch(e){
    root.innerHTML = '<button class="rp-btn-mini" id="rp-close" style="float:right">Fermer</button>'
                   + '<div class="rp-vide">' + RP.escHtml(e.message) + '</div>';
    document.getElementById("rp-close").onclick = closeCR;
  }
}
function closeCR(){
  document.getElementById("mov").classList.remove("open");
  S.dossierOuvert = null;
}

/* ── Navigation ──────────────────────────────────────────────── */

function ongletActif(){
  return document.getElementById("tab-feuille").classList.contains("active") ? "feuille" : "liste";
}
function switchTab(nom){
  ["feuille","liste"].forEach(n => {
    document.getElementById("tab-" + n).classList.toggle("active", n === nom);
    document.getElementById("nav-" + n).classList.toggle("active", n === nom);
  });
  try { location.hash = nom; } catch(e){}
  if(nom === "feuille") loadFeuille(); else loadListe();
}
function rechargerOngletActif(){
  if(ongletActif() === "feuille") loadFeuille(); else loadListe();
}
async function tout(){
  try { await loadPeriode(); }
  catch(e){ showToast(e.message, "danger"); return; }
  rechargerOngletActif();
}

document.getElementById("btn-refresh").onclick = tout;
document.getElementById("mode-select").onchange = () => { majVisibilitePeriode(); tout(); };
document.getElementById("jour-input").onchange = tout;
document.getElementById("wk-input").onchange = tout;
document.getElementById("machine-select").onchange = () => {
  S.machine = document.getElementById("machine-select").value || "";
  rechargerOngletActif();
};
document.querySelectorAll(".chip[data-raccourci]").forEach(c => {
  c.onclick = () => {
    const r = c.getAttribute("data-raccourci");
    if(r === "semaine-passee"){
      const sp = semainePrecedente();
      document.getElementById("mode-select").value = "semaine";
      document.getElementById("wk-input").value = sp.year + "-W" + iso2(sp.week);
    } else {
      document.getElementById("mode-select").value = "jour";
      document.getElementById("jour-input").value = (r === "hier") ? hier() : dateISO(new Date());
    }
    majVisibilitePeriode(); tout();
  };
});
document.getElementById("btn-print").onclick = () => {
  if(ongletActif() !== "feuille") switchTab("feuille");
  setTimeout(() => window.print(), 150);
};
document.getElementById("q-input").oninput = () => {
  clearTimeout(S.qTimer);
  S.qTimer = setTimeout(lancerRecherche, 250);
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
      '<div class="uc-name">' + RP.escHtml(u.nom || u.email || "Utilisateur") + '</div>'
      + '<div class="uc-role">' + RP.escHtml(u.role || "") + '</div>';
    try { if(window.MySifaTheme) MySifaTheme.mergeFromUser(u); } catch(e){}
  } catch(e){}
})();

(function init(){
  // Par defaut : la veille. C'est la vue du point de production du matin.
  const sp = semainePrecedente();
  document.getElementById("jour-input").value = hier();
  document.getElementById("wk-input").value = sp.year + "-W" + iso2(sp.week);
  document.getElementById("mode-select").value = "jour";
  majVisibilitePeriode();

  const params = new URLSearchParams(location.search);
  const dossier = params.get("dossier");
  const h = (location.hash || "").replace("#", "");
  if(h === "liste" || dossier){
    document.getElementById("tab-feuille").classList.remove("active");
    document.getElementById("nav-feuille").classList.remove("active");
    document.getElementById("tab-liste").classList.add("active");
    document.getElementById("nav-liste").classList.add("active");
  }
  tout();
  if(dossier) openCR(dossier);   // /rapports-prod?dossier=D-501
})();
</script>
</body>
</html>
"""
