"""MySifa — ERP (page).

Route : /erp — super administrateur uniquement.

Lecture du miroir RVGI (`data/erp_mirror.db`) dans les codes de MySifa :
sidebar invariable, filtres persistants à gauche, grille dense, panneau de
détail. Aucune action d'écriture — l'ERP reste la source, cet écran regarde.

Le catalogue d'écrans vit dans `app/services/erp_catalogue.py` : ajouter un
écran ne demande pas de toucher à cette page.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLE_SUPERADMIN
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/erp", response_class=HTMLResponse)
def erp_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/erp", status_code=302)
        raise
    if user.get("role") != ROLE_SUPERADMIN:
        from app.web.access_denied import access_denied_response
        return access_denied_response(
            "ERP",
            detail="Cette application est réservée au super administrateur.",
        )
    html = ERP_HTML.replace("__V_LABEL__", f"v{APP_VERSION}")
    return HTMLResponse(content=html)


ERP_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>ERP — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<link rel="stylesheet" href="/static/mysifa_mobile_topbar.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--success:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--success:#059669;--danger:#dc2626;--warn:#d97706}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── Shell ── */
.layout{display:flex;min-height:100vh}
/* Tiroir : la sidebar ne mange plus 230 px en permanence. Elle s'ouvre par le
   bouton Menu, se referme dès qu'on choisit un écran. La grille récupère la
   largeur, c'est elle qui en a besoin. */
.sidebar{width:250px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;display:flex;flex-direction:column;flex-shrink:0;height:100vh;position:fixed;top:0;left:0;z-index:70;overflow-y:auto;scrollbar-width:none;transform:translateX(-105%);transition:transform .18s ease;box-shadow:0 0 32px rgba(0,0,0,.35)}
body.sb-open .sidebar{transform:translateX(0)}
.sidebar::-webkit-scrollbar{width:0}
.logo{padding:6px 8px;margin-bottom:18px;border-radius:8px;cursor:pointer;transition:background .15s,color .15s}
.logo:hover{background:var(--accent-bg)}
.logo:hover .logo-brand{color:var(--accent)}
.logo-brand{font-size:15px;font-weight:800;transition:color .15s}.logo-brand span{color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:2px}
.nav-groupe{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--muted);padding:14px 12px 6px}
.nav-btn{display:flex;align-items:center;gap:9px;width:100%;text-align:left;padding:8px 12px;border-radius:8px;border:none;background:transparent;color:var(--text2);font-size:12.5px;font-weight:500;cursor:pointer;font-family:inherit;transition:background .15s,color .15s;margin-bottom:1px}
.nav-btn:hover,.nav-btn.active{background:var(--accent-bg);color:var(--accent)}
.nav-badge{margin-left:auto;padding:1px 6px;border-radius:9px;background:var(--bg);color:var(--muted);font-size:10px;font-weight:700;font-variant-numeric:tabular-nums}
.nav-btn.active .nav-badge{background:var(--accent-bg);color:var(--accent)}
.back-mysifa{border:none!important;background:transparent!important;font-weight:400!important;color:var(--text2)!important;padding:8px 10px!important}
.back-mysifa:hover{color:var(--text)!important;background:transparent!important}
.back-mysifa .wm{font-weight:800;color:var(--text)}.back-mysifa .wm span{color:var(--accent)}
.sidebar-bottom{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-top:14px;padding-bottom:8px}
.user-chip{padding:10px 12px;border-radius:8px;background:var(--accent-bg);cursor:pointer}
.user-chip .uc-name{font-size:12px;font-weight:600;color:var(--text)}
.user-chip .uc-role{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.theme-btn,.logout-btn{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s,color .15s}
.theme-btn:hover{background:var(--card);color:var(--text)}
.logout-btn:hover{background:var(--danger);border-color:var(--danger);color:#fff}
.version{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;color:var(--muted);text-align:center;padding-top:4px}

.main{flex:1;min-width:0;display:flex;flex-direction:column}
.page-head{padding:18px 22px 12px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:14px;flex-wrap:wrap}
.btn-menu{flex-shrink:0;display:inline-flex;align-items:center;gap:8px;border:1px solid var(--border);background:var(--card);color:var(--text2);border-radius:10px;padding:9px 13px;font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;transition:background .15s,color .15s,border-color .15s}
.btn-menu:hover{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
@media (max-width:900px){.btn-menu{display:none}}
.page-head h1{margin:0;font-size:19px;font-weight:700}
.page-head .sous{font-size:12px;color:var(--muted);margin-top:4px;max-width:640px}
.head-droite{margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;font-size:11px;font-weight:600;background:var(--bg);border:1px solid var(--border);color:var(--text2)}
.pill.lecture{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.pill.vieux{background:rgba(251,191,36,.14);border-color:var(--warn);color:var(--warn)}

/* ── Menu (accueil du module) ── */
.menu-wrap{padding:22px 26px 40px;overflow:auto}
.domaine-titre{font-size:11px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:var(--muted);margin:22px 0 10px}
.cartes{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.carte{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;cursor:pointer;transition:border-color .15s,transform .12s}
.carte:hover{border-color:var(--accent);transform:translateY(-1px)}
.carte-titre{font-size:13.5px;font-weight:700;display:flex;align-items:center;gap:8px}
.carte-nb{margin-left:auto;font-size:11px;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums}
.carte-sous{font-size:11.5px;color:var(--muted);margin-top:6px;line-height:1.5}
.carte-table{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;color:var(--muted);margin-top:8px}

/* ── Écran : rail + grille ── */
.ecran{display:flex;flex:1;min-height:0}
.rail{width:236px;flex-shrink:0;border-right:1px solid var(--border);padding:16px 14px;overflow-y:auto;background:var(--card)}
.rail-titre{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.champ{margin-bottom:12px}
.champ label{display:block;font-size:10.5px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--muted);margin-bottom:5px}
.champ input,.champ select{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;transition:border-color .15s}
.champ input:focus,.champ select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.btn{border-radius:10px;padding:9px 14px;font-weight:700;font-size:12px;font-family:inherit;cursor:pointer;border:1px solid var(--border);background:var(--bg);color:var(--text2);transition:filter .15s,background .15s,color .15s}
.btn:hover{background:var(--card);color:var(--text)}
.btn-accent{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.btn-accent:hover{filter:brightness(1.05)}
.rail-info{font-size:11px;color:var(--muted);line-height:1.6;border-top:1px solid var(--border);margin-top:14px;padding-top:12px}

.grille-zone{flex:1;min-width:0;display:flex;flex-direction:column}
.grille-scroll{flex:1;overflow:auto;cursor:grab}
.grille-scroll.attrape{cursor:grabbing;user-select:none}
table.grille{border-collapse:separate;border-spacing:0;width:100%;font-size:12.5px}
table.grille th{position:sticky;top:0;z-index:2;background:var(--card);border-bottom:1px solid var(--border);padding:9px 10px;text-align:left;font-size:10.5px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:var(--muted);white-space:nowrap;cursor:pointer;user-select:none}
table.grille th:hover{color:var(--accent)}
table.grille th .fleche{color:var(--accent);margin-left:4px}
table.grille th.attrapee{opacity:.4}
table.grille th.cible{box-shadow:inset 3px 0 0 var(--accent)}
.th-boite{display:flex;align-items:center;gap:6px}
.th-poignee{cursor:grab;color:var(--muted);opacity:.45;flex-shrink:0}
.th-poignee:hover{opacity:1;color:var(--accent)}
.th-cadenas{border:none;background:transparent;padding:0;margin-left:auto;color:var(--muted);opacity:.35;cursor:pointer;display:inline-flex;flex-shrink:0}
.th-cadenas:hover{opacity:1;color:var(--accent)}
.th-cadenas.on{opacity:1;color:var(--accent)}
/* Colonnes épinglées : elles restent à gauche au défilement horizontal.
   Le décalage `left` est calculé après rendu, à la largeur réelle. */
table.grille th.epingle{z-index:4}
table.grille th.epingle,table.grille td.epingle{position:sticky;background:var(--card)}
table.grille td.epingle{z-index:1;background:var(--bg)}
table.grille tbody tr:hover td.epingle,table.grille tbody tr.sel td.epingle{background:var(--accent-bg)}
table.grille th.bord-epingle,table.grille td.bord-epingle{border-right:1px solid var(--accent)}
table.grille td{padding:7px 10px;border-bottom:1px solid var(--border);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:340px}
table.grille tbody tr{cursor:pointer}
table.grille tbody tr:hover td{background:var(--accent-bg)}
table.grille tbody tr.sel td{background:var(--accent-bg)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
td.of{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:var(--accent);font-weight:600}
td.vide{color:var(--muted)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:700;background:var(--accent-bg);color:var(--accent)}
.badge.n0{background:rgba(148,163,184,.16);color:var(--muted)}
.badge.n1{background:rgba(251,191,36,.16);color:var(--warn)}
.badge.n2{background:rgba(52,211,153,.16);color:var(--ok)}
.badge.n3{background:rgba(34,211,238,.14);color:var(--accent)}
.neg{color:var(--danger);font-weight:600}
.pied{display:flex;align-items:center;gap:12px;padding:10px 16px;border-top:1px solid var(--border);background:var(--card);font-size:12px;color:var(--muted)}
.pied .compte{font-variant-numeric:tabular-nums}
.pied .pager{margin-left:auto;display:flex;align-items:center;gap:6px}
.vide-msg{padding:40px 26px;color:var(--muted);font-size:13px}

/* ── Détail ── */
.detail{width:430px;flex-shrink:0;border-left:1px solid var(--border);background:var(--card);overflow-y:auto;display:none}
.detail.ouvert{display:block}
.detail-head{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--border);padding:14px 18px;display:flex;align-items:center;gap:10px;z-index:2}
.detail-head h2{margin:0;font-size:14px;font-weight:700}
.detail-fermer{margin-left:auto;border:none;background:var(--bg);color:var(--text2);border-radius:8px;width:28px;height:28px;cursor:pointer;font-size:16px;line-height:1}
.detail-fermer:hover{background:var(--danger);color:#fff}
.groupe{border-bottom:1px solid var(--border)}
.groupe-titre{padding:11px 18px;font-size:10.5px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--muted);cursor:pointer;display:flex;align-items:center;gap:8px}
.groupe-titre:hover{color:var(--accent)}
.groupe-corps{padding:0 18px 12px}
.groupe.replie .groupe-corps{display:none}
.ligne-champ{display:flex;gap:12px;padding:5px 0;font-size:12.5px;border-bottom:1px dashed transparent}
.ligne-champ .lab{color:var(--muted);flex:0 0 46%}
.ligne-champ .val{color:var(--text);word-break:break-word}
.ligne-champ .val.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}

/* ── Divers ── */
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:11px 18px;font-size:13px;z-index:80;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.toast.err{border-left-color:var(--danger)}
.skel{height:12px;border-radius:6px;background:linear-gradient(90deg,var(--border),var(--card),var(--border));background-size:200% 100%;animation:sk 1.2s linear infinite}
@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}
.sidebar-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:40}
body.sb-open .sidebar-overlay{display:block}
@media (max-width:900px){
  .ecran{flex-direction:column}
  .rail{width:auto;border-right:none;border-bottom:1px solid var(--border)}
  .detail{position:fixed;inset:0;width:auto;z-index:60}
}
@media (min-width:901px){.mobile-topbar{display:none}}
</style>
</head>
<body class="has-topbar">
<script src="/static/mysifa_theme.js"></script>
<script src="/static/mysifa_user_chip.js"></script>

<div class="sidebar-overlay" id="sb-ov" onclick="fermerSidebar()"></div>

<div class="layout">
  <aside class="sidebar">
    <div class="logo" onclick="ouvrirMenu()" title="Menu ERP">
      <div class="logo-brand">My<span>ERP</span></div>
      <div class="logo-sub">RVGI · lecture seule</div>
    </div>
    <button type="button" class="nav-btn" id="nav-menu" onclick="ouvrirMenu()">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
      Menu
    </button>
    <div id="nav-ecrans"></div>

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
      <div class="version">ERP · __V_LABEL__</div>
    </div>
  </aside>

  <main class="main">
    <div class="mobile-topbar">
      <button type="button" class="mobile-menu-btn" onclick="basculerSidebar()" aria-label="Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div>
        <div class="mobile-topbar-title">ERP</div>
        <div class="mobile-topbar-sub" id="mobile-sub">Menu</div>
      </div>
      <button type="button" class="mobile-home-btn" onclick="location.href='/'" aria-label="Accueil">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/></svg>
      </button>
    </div>

    <div class="page-head">
      <button type="button" class="btn-menu" onclick="basculerSidebar()" aria-label="Ouvrir le menu ERP">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        Menu
      </button>
      <div>
        <h1 id="titre">ERP</h1>
        <div class="sous" id="sous">Lecture du miroir de RVGI.</div>
      </div>
      <div class="head-droite" id="head-droite"></div>
    </div>

    <div id="corps" style="flex:1;min-height:0;display:flex;flex-direction:column"></div>
  </main>
</div>

<script>
// ══════════════════════════════════════════════════════════════════
// MyERP — lecture du miroir RVGI.
// Convention api() : retourne le JSON parsé, throw sur HTTP != 2xx.
// Le rail de filtres n'est JAMAIS reconstruit par un rafraîchissement de
// liste : seuls le corps de la grille et le pied changent. C'est ce qui
// garantit que la recherche ne perd pas le focus en cours de frappe.
// ══════════════════════════════════════════════════════════════════
const S = {
  meta: null,
  ecran: null,        // clé de l'écran courant
  def: null,          // sa définition (colonnes, filtres) telle que renvoyée par meta
  colonnes: [],
  lignes: [],
  total: 0,
  page: 1,
  taille: 100,
  tri: null,
  sens: 'asc',
  q: '',
  filtres: {},
  selection: null,
  epingles: [],       // colonnes figées à gauche, dans l'ordre d'épinglage
  colDrag: null,      // colonne en cours de déplacement
  glisse: false,      // un défilement à la souris vient d'avoir lieu
  jeton: 0,           // anti-course : seule la dernière requête lancée s'affiche
};

const ICO_SUN='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICO_MOON='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function toast(msg,type){const t=document.createElement('div');t.className='toast'+(type==='err'?' err':'');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3400);}
async function api(url){
  const r=await fetch(url,{credentials:'include'});
  if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}
  return r.json();
}

// ── Formats ──────────────────────────────────────────────────────
function fmtNb(v,dec){
  const n=Number(v);
  if(!isFinite(n))return esc(v);
  return n.toLocaleString('fr-FR',{minimumFractionDigits:dec||0,maximumFractionDigits:dec==null?2:dec});
}
function fmtDate(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(!m)return esc(s);
  return m[3]+'/'+m[2]+'/'+m[1];
}
function fmtDateHeure(s){
  const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
  if(!m)return fmtDate(s);
  return m[3]+'/'+m[2]+'/'+m[1]+' '+m[4]+':'+m[5];
}
function libelleEnum(nom,code){
  const t=(S.meta&&S.meta.enums&&S.meta.enums[nom])||null;
  const c=String(code==null?'':code);
  if(t&&t[c]!=null)return t[c];
  if(c==='255')return '—';   // sentinelle WinDev : octet non renseigné
  return c;   // un code inconnu s'affiche brut : on ne cache jamais une valeur
}

// Rendu d'une cellule : classe CSS + HTML. Une valeur absente est un tiret
// discret, jamais un vide — sinon on ne distingue pas « rien » de « pas chargé ».
function cellule(col,v){
  if(v==null||v==='')return{cls:'vide',html:'—'};
  const t=col.type||'texte';
  if(t==='date')     return {cls:'',     html:fmtDate(v)};
  if(t==='datetime') return {cls:'mono', html:fmtDateHeure(v)};
  if(t==='of')       return {cls:'of',   html:esc(v)};
  if(t==='ref'||t==='code') return {cls:'mono',html:esc(v)};
  if(t==='bool')     return {cls:'',     html:(String(v)==='1'||v===true)?'Oui':'—'};
  if(t==='enum'){
    const code=String(v);
    const cl=('n'+code).length<=3?('n'+code):'';
    return {cls:'',html:'<span class="badge '+cl+'">'+esc(libelleEnum(col.enum,code))+'</span>'};
  }
  if(t==='qte'||t==='nombre'){
    const n=Number(v);
    const neg=isFinite(n)&&n<0;
    return {cls:'num'+(neg?' neg':''),html:fmtNb(v,0)};
  }
  if(t==='prix')     return {cls:'num',  html:fmtNb(v,4)};
  if(t==='montant')  return {cls:'num',  html:fmtNb(v,2)};
  return {cls:'',html:esc(v)};
}

// ── Disposition des colonnes ─────────────────────────────────────
// Ordre et épinglages sont mémorisés par écran, dans le navigateur. C'est un
// confort d'affichage, pas une donnée : il n'a pas à voyager jusqu'au serveur,
// et il ne suit pas l'utilisateur d'un poste à l'autre — dit une fois ici pour
// que ce ne soit pas une surprise.
function cleLayout(){return 'mysifa_erp_cols_'+(S.ecran||'');}
function layoutCharger(){
  try{const b=localStorage.getItem(cleLayout());if(b)return JSON.parse(b)||{};}catch(e){}
  return {ordre:[],epingles:[]};
}
function layoutSauver(){
  try{
    localStorage.setItem(cleLayout(),JSON.stringify({
      ordre:S.colonnes.map(c=>c.nom), epingles:S.epingles
    }));
  }catch(e){}
}
function layoutOublier(){
  try{localStorage.removeItem(cleLayout());}catch(e){}
  S.epingles=[];
  charger();
  toast('Disposition des colonnes réinitialisée.');
}
// Les épinglées passent devant, dans l'ordre où elles ont été épinglées.
function reordonner(){
  const ep=[],reste=[];
  S.colonnes.forEach(c=>{(S.epingles.indexOf(c.nom)>=0?ep:reste).push(c);});
  ep.sort((a,b)=>S.epingles.indexOf(a.nom)-S.epingles.indexOf(b.nom));
  S.colonnes=ep.concat(reste);
}
function appliquerLayout(colonnes){
  const l=layoutCharger();
  const parNom={};colonnes.forEach(c=>{parNom[c.nom]=c;});
  const ordonnees=[];
  (l.ordre||[]).forEach(n=>{if(parNom[n]){ordonnees.push(parNom[n]);delete parNom[n];}});
  colonnes.forEach(c=>{if(parNom[c.nom])ordonnees.push(c);});   // colonnes nouvelles : à la fin
  S.colonnes=ordonnees;
  S.epingles=(l.epingles||[]).filter(n=>ordonnees.some(c=>c.nom===n));
  reordonner();
}
function basculerEpingle(nom){
  const i=S.epingles.indexOf(nom);
  if(i>=0)S.epingles.splice(i,1);else S.epingles.push(nom);
  reordonner();layoutSauver();renderTete();renderGrille();
}
function deplacerColonne(depuis,vers){
  if(depuis===vers)return;
  const i=S.colonnes.findIndex(c=>c.nom===depuis);
  const j=S.colonnes.findIndex(c=>c.nom===vers);
  if(i<0||j<0)return;
  const [c]=S.colonnes.splice(i,1);
  S.colonnes.splice(j,0,c);
  reordonner();layoutSauver();renderTete();renderGrille();
}
// Décalage `left` des colonnes épinglées : mesuré après rendu, parce que la
// largeur réelle dépend du contenu, pas de la largeur déclarée au catalogue.
function appliquerEpingles(){
  const table=document.querySelector('table.grille');
  if(!table)return;
  const ths=table.querySelectorAll('thead th');
  let x=0;
  S.colonnes.forEach((c,i)=>{
    const th=ths[i];
    if(!th)return;
    const cellules=table.querySelectorAll('tbody tr > td:nth-child('+(i+1)+')');
    const epingle=S.epingles.indexOf(c.nom)>=0;
    const suivante=S.colonnes[i+1];
    const dernier=epingle&&(!suivante||S.epingles.indexOf(suivante.nom)<0);
    if(epingle){
      th.style.left=x+'px';th.classList.add('epingle');
      th.classList.toggle('bord-epingle',dernier);
      cellules.forEach(td=>{
        td.style.left=x+'px';td.classList.add('epingle');
        td.classList.toggle('bord-epingle',dernier);
      });
      x+=th.offsetWidth;
    }else{
      th.style.left='';th.classList.remove('epingle','bord-epingle');
      cellules.forEach(td=>{td.style.left='';td.classList.remove('epingle','bord-epingle');});
    }
  });
}
// Défilement à la souris : la barre horizontale est en bas d'une grille haute,
// donc presque toujours hors de vue. On attrape la grille et on la tire.
function activerGlisserDefiler(){
  const z=document.querySelector('.grille-scroll');
  if(!z||z.dataset.glisse)return;
  z.dataset.glisse='1';
  let actif=false,bouge=false,x0=0,y0=0,g0=0,h0=0;
  z.addEventListener('mousedown',e=>{
    if(e.button!==0)return;
    if(e.target.closest('button, a, input, select, .th-poignee'))return;
    actif=true;bouge=false;x0=e.pageX;y0=e.pageY;g0=z.scrollLeft;h0=z.scrollTop;
  });
  z.addEventListener('mousemove',e=>{
    if(!actif)return;
    const dx=e.pageX-x0,dy=e.pageY-y0;
    if(!bouge){
      if(Math.abs(dx)<5&&Math.abs(dy)<5)return;
      bouge=true;z.classList.add('attrape');
    }
    e.preventDefault();
    z.scrollLeft=g0-dx;z.scrollTop=h0-dy;
  });
  function fin(){
    if(bouge)S.glisse=true;   // avale le clic qui suit, sinon on ouvre une ligne
    actif=false;bouge=false;z.classList.remove('attrape');
  }
  z.addEventListener('mouseleave',fin);
  window.addEventListener('mouseup',fin);
}

// ── Navigation ───────────────────────────────────────────────────
function renderNav(){
  const hote=document.getElementById('nav-ecrans');
  if(!S.meta||!S.meta.present){hote.innerHTML='';return;}
  let h='';
  (S.meta.domaines||[]).forEach(d=>{
    const ecrans=(S.meta.ecrans||[]).filter(e=>e.domaine===d.cle);
    if(!ecrans.length)return;
    h+='<div class="nav-groupe">'+esc(d.label)+'</div>';
    ecrans.forEach(e=>{
      const nb=(e.lignes==null)?'':('<span class="nav-badge">'+fmtNb(e.lignes,0)+'</span>');
      h+='<button type="button" class="nav-btn'+(S.ecran===e.cle?' active':'')+'" data-ecran="'+esc(e.cle)+'">'+esc(e.label)+nb+'</button>';
    });
  });
  hote.innerHTML=h;
  hote.querySelectorAll('[data-ecran]').forEach(b=>{
    b.addEventListener('click',()=>{location.hash='#/'+b.getAttribute('data-ecran');});
  });
  const nm=document.getElementById('nav-menu');
  if(nm)nm.classList.toggle('active',!S.ecran);
}

function renderFraicheur(){
  const hote=document.getElementById('head-droite');
  if(!S.meta){hote.innerHTML='';return;}
  if(!S.meta.present){hote.innerHTML='<span class="pill vieux">Miroir absent</span>';return;}
  const d=String(S.meta.importe_le||'');
  const j=(new Date()-new Date(d.replace(' ','T')))/86400000;
  const vieux=isFinite(j)&&j>2;
  hote.innerHTML='<span class="pill lecture">Lecture seule</span>'+
    '<span class="pill'+(vieux?' vieux':'')+'">Miroir du '+esc(fmtDateHeure(d))+'</span>';
}

// ── Vue menu ─────────────────────────────────────────────────────
function ouvrirMenu(){
  S.ecran=null;S.def=null;S.selection=null;S.colonnes=[];
  document.getElementById('titre').textContent='ERP';
  document.getElementById('sous').textContent=
    (S.meta&&S.meta.present)
      ? 'Miroir de RVGI : '+fmtNb(S.meta.lignes,0)+' lignes sur '+S.meta.tables+' tables.'
      : 'Le miroir de l\'ERP n\'a pas encore été construit.';
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent='Menu';
  renderNav();
  const corps=document.getElementById('corps');
  if(!S.meta||!S.meta.present){
    corps.innerHTML='<div class="vide-msg">'+esc((S.meta&&S.meta.message)||'Miroir indisponible.')+'</div>';
    return;
  }
  let h='<div class="menu-wrap">';
  (S.meta.domaines||[]).forEach(d=>{
    const ecrans=(S.meta.ecrans||[]).filter(e=>e.domaine===d.cle);
    if(!ecrans.length)return;
    h+='<div class="domaine-titre">'+esc(d.label)+'</div><div class="cartes">';
    ecrans.forEach(e=>{
      h+='<div class="carte" data-ecran="'+esc(e.cle)+'">'+
           '<div class="carte-titre">'+esc(e.label)+
             (e.lignes==null?'':'<span class="carte-nb">'+fmtNb(e.lignes,0)+'</span>')+'</div>'+
           '<div class="carte-sous">'+esc(e.resume||'')+'</div>'+
           '<div class="carte-table">'+esc(e.table)+'</div></div>';
    });
    h+='</div>';
  });
  corps.innerHTML=h+'</div>';
  corps.querySelectorAll('[data-ecran]').forEach(c=>{
    c.addEventListener('click',()=>{location.hash='#/'+c.getAttribute('data-ecran');});
  });
}

// ── Vue écran : rail + grille ────────────────────────────────────
function ouvrirEcran(cle){
  const def=((S.meta&&S.meta.ecrans)||[]).find(e=>e.cle===cle);
  if(!def){toast('Écran inconnu.','err');ouvrirMenu();return;}
  S.ecran=cle;S.def=def;S.page=1;S.tri=null;S.sens='asc';S.q='';S.filtres={};S.selection=null;S.colonnes=[];S.epingles=[];
  // Un écran s'ouvre sur ce qui est vivant : le filtre qui porte un défaut
  // (Position = En cours) est appliqué d'entrée, et reste effaçable.
  (def.filtres||[]).forEach(f=>{
    if(f.defaut!=null&&f.defaut!=='')S.filtres[f.nom]=String(f.defaut);
  });
  document.getElementById('titre').textContent=def.label;
  document.getElementById('sous').textContent=def.resume||'';
  const ms=document.getElementById('mobile-sub');if(ms)ms.textContent=def.label;
  renderNav();

  // Rail construit UNE fois par écran. Les rafraîchissements de liste ne le
  // touchent pas : le champ de recherche garde son focus et son curseur.
  let rail='<div class="rail"><div class="rail-titre">Recherche</div>'+
    '<div class="champ"><input type="text" id="q" placeholder="Rechercher..." autocomplete="off"></div>';
  if((def.filtres||[]).length){
    rail+='<div class="rail-titre">Filtres</div>';
    (def.filtres||[]).forEach(f=>{
      const id='f-'+f.nom;
      const lab='<label for="'+id+'">'+esc(f.label)+'</label>';
      const val=S.filtres[f.nom]!=null?String(S.filtres[f.nom]):'';
      if(f.type==='enum'&&S.meta.enums&&S.meta.enums[f.enum]){
        let o='<option value=""'+(val===''?' selected':'')+'>Tous</option>';
        Object.keys(S.meta.enums[f.enum]).forEach(k=>{
          o+='<option value="'+esc(k)+'"'+(val===String(k)?' selected':'')+'>'+esc(S.meta.enums[f.enum][k])+'</option>';
        });
        rail+='<div class="champ">'+lab+'<select id="'+id+'" data-filtre="'+esc(f.nom)+'">'+o+'</select></div>';
      }else if(f.type==='date_min'||f.type==='date_max'){
        rail+='<div class="champ">'+lab+'<input type="date" id="'+id+'" data-filtre="'+esc(f.nom)+'" value="'+esc(val)+'"></div>';
      }else{
        rail+='<div class="champ">'+lab+'<input type="text" id="'+id+'" data-filtre="'+esc(f.nom)+'" value="'+esc(val)+'" autocomplete="off"></div>';
      }
    });
  }
  rail+='<button type="button" class="btn" id="btn-reset" style="width:100%">Réinitialiser les filtres</button>'+
    '<button type="button" class="btn" id="btn-reset-cols" style="width:100%;margin-top:6px">Réinitialiser les colonnes</button>'+
    '<div class="rail-info">Glisser une en-tête pour déplacer sa colonne, le cadenas pour la figer à gauche. '+
    'Tirer la grille à la souris pour la faire défiler.<br><br>'+
    'Table <strong>'+esc(def.table)+'</strong><br>'+
    (def.lignes==null?'':(fmtNb(def.lignes,0)+' lignes dans le miroir<br>'))+
    'Corbeille RVGI exclue à l\'export.</div></div>';

  document.getElementById('corps').innerHTML='<div class="ecran">'+rail+
    '<div class="grille-zone">'+
      '<div class="grille-scroll"><table class="grille"><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>'+
      '<div class="pied" id="pied"></div></div>'+
    '<aside class="detail" id="detail"></aside></div>';

  const q=document.getElementById('q');
  let minuteur=null;
  q.addEventListener('input',()=>{
    S.q=q.value;clearTimeout(minuteur);
    minuteur=setTimeout(()=>{S.page=1;charger();},220);
  });
  q.addEventListener('keydown',ev=>{
    if(ev.key==='Escape'){q.value='';S.q='';S.page=1;charger();}
  });
  document.querySelectorAll('[data-filtre]').forEach(el=>{
    const ev=(el.tagName==='SELECT'||el.type==='date')?'change':'input';
    let m=null;
    el.addEventListener(ev,()=>{
      S.filtres[el.getAttribute('data-filtre')]=el.value;
      clearTimeout(m);
      m=setTimeout(()=>{S.page=1;charger();},ev==='change'?0:220);
    });
  });
  document.getElementById('btn-reset').addEventListener('click',()=>{
    S.q='';S.filtres={};S.page=1;
    (def.filtres||[]).forEach(f=>{
      if(f.defaut!=null&&f.defaut!=='')S.filtres[f.nom]=String(f.defaut);
    });
    const c=document.getElementById('q');if(c)c.value='';
    document.querySelectorAll('[data-filtre]').forEach(el=>{
      const nom=el.getAttribute('data-filtre');
      el.value=S.filtres[nom]!=null?String(S.filtres[nom]):'';
    });
    charger();if(c)c.focus();
  });
  const bc=document.getElementById('btn-reset-cols');
  if(bc)bc.addEventListener('click',layoutOublier);
  charger();
}

const ICO_POIGNEE='<svg class="th-poignee" width="10" height="14" viewBox="0 0 10 14" fill="currentColor" aria-hidden="true"><circle cx="2" cy="3" r="1.2"/><circle cx="8" cy="3" r="1.2"/><circle cx="2" cy="7" r="1.2"/><circle cx="8" cy="7" r="1.2"/><circle cx="2" cy="11" r="1.2"/><circle cx="8" cy="11" r="1.2"/></svg>';
const ICO_CADENAS_OUVERT='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.5-2"/></svg>';
const ICO_CADENAS_FERME='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';

function renderTete(){
  const t=document.getElementById('thead');
  if(!t)return;
  let h='<tr>';
  S.colonnes.forEach(c=>{
    const actif=S.tri===c.nom;
    const fl=actif?('<span class="fleche">'+(S.sens==='desc'?'▾':'▴')+'</span>'):'';
    const ep=S.epingles.indexOf(c.nom)>=0;
    h+='<th data-col="'+esc(c.nom)+'" draggable="true" style="'+(c.largeur?('min-width:'+c.largeur+'px'):'')+'">'+
         '<span class="th-boite">'+ICO_POIGNEE+
           '<span class="th-libelle">'+esc(c.label)+fl+'</span>'+
           '<button type="button" class="th-cadenas'+(ep?' on':'')+'" data-epingle="'+esc(c.nom)+'" '+
             'title="'+(ep?'Libérer la colonne':'Figer la colonne à gauche')+'" '+
             'aria-label="'+(ep?'Libérer la colonne':'Figer la colonne à gauche')+'">'+
             (ep?ICO_CADENAS_FERME:ICO_CADENAS_OUVERT)+
           '</button>'+
         '</span>'+
       '</th>';
  });
  t.innerHTML=h+'</tr>';

  t.querySelectorAll('[data-epingle]').forEach(b=>{
    b.addEventListener('click',ev=>{ev.stopPropagation();basculerEpingle(b.getAttribute('data-epingle'));});
  });

  t.querySelectorAll('[data-col]').forEach(th=>{
    const nom=th.getAttribute('data-col');
    th.addEventListener('click',ev=>{
      if(ev.target.closest('.th-cadenas'))return;
      if(S.tri===nom){S.sens=(S.sens==='asc')?'desc':'asc';}else{S.tri=nom;S.sens='asc';}
      S.page=1;charger();
    });
    th.addEventListener('dragstart',ev=>{
      S.colDrag=nom;th.classList.add('attrapee');
      try{ev.dataTransfer.effectAllowed='move';ev.dataTransfer.setData('text/plain',nom);}catch(e){}
    });
    th.addEventListener('dragend',()=>{
      S.colDrag=null;
      t.querySelectorAll('th').forEach(x=>x.classList.remove('attrapee','cible'));
    });
    th.addEventListener('dragover',ev=>{
      if(!S.colDrag||S.colDrag===nom)return;
      ev.preventDefault();th.classList.add('cible');
    });
    th.addEventListener('dragleave',()=>th.classList.remove('cible'));
    th.addEventListener('drop',ev=>{
      ev.preventDefault();th.classList.remove('cible');
      if(S.colDrag&&S.colDrag!==nom)deplacerColonne(S.colDrag,nom);
      S.colDrag=null;
    });
  });
  appliquerEpingles();
}

function urlListe(){
  const p=new URLSearchParams();
  if(S.q)p.set('q',S.q);
  if(S.tri){p.set('tri',S.tri);p.set('sens',S.sens);}
  p.set('page',String(S.page));
  p.set('taille',String(S.taille));
  Object.keys(S.filtres).forEach(k=>{if(S.filtres[k])p.set('f_'+k,S.filtres[k]);});
  return '/api/erp/'+encodeURIComponent(S.ecran)+'/lignes?'+p.toString();
}

async function charger(){
  const tb=document.getElementById('tbody');
  if(!tb)return;
  const jeton=++S.jeton;
  const nbCol=Math.max(S.colonnes.length,1);
  tb.innerHTML='<tr><td colspan="'+nbCol+'"><div class="skel"></div></td></tr>';
  let r;
  try{ r=await api(urlListe()); }
  catch(e){
    if(jeton!==S.jeton)return;
    tb.innerHTML='<tr><td colspan="'+nbCol+'" class="vide">'+esc(e.message)+'</td></tr>';
    return;
  }
  if(jeton!==S.jeton)return;   // une frappe plus récente a déjà relancé
  S.lignes=r.lignes;S.total=r.total;
  appliquerLayout(r.colonnes);
  renderTete();renderGrille();renderPied();
  activerGlisserDefiler();
}

function renderGrille(){
  const tb=document.getElementById('tbody');
  if(!tb)return;
  if(!S.lignes.length){
    const msg=S.q?('Aucun résultat pour « '+esc(S.q)+' »'):'Aucune ligne.';
    tb.innerHTML='<tr><td colspan="'+Math.max(S.colonnes.length,1)+'" class="vide">'+msg+'</td></tr>';
    return;
  }
  let h='';
  S.lignes.forEach(l=>{
    h+='<tr data-id="'+esc(l._id)+'"'+(String(S.selection)===String(l._id)?' class="sel"':'')+'>';
    S.colonnes.forEach(c=>{
      const r=cellule(c,l[c.nom]);
      h+='<td class="'+r.cls+'">'+r.html+'</td>';
    });
    h+='</tr>';
  });
  tb.innerHTML=h;
  tb.querySelectorAll('[data-id]').forEach(tr=>{
    tr.addEventListener('click',()=>{
      if(S.glisse){S.glisse=false;return;}   // c'était un défilement, pas un clic
      ouvrirDetail(tr.getAttribute('data-id'));
    });
  });
  appliquerEpingles();
}

function renderPied(){
  const p=document.getElementById('pied');
  if(!p)return;
  const debut=S.total?((S.page-1)*S.taille+1):0;
  const fin=Math.min(S.page*S.taille,S.total);
  const pages=Math.max(1,Math.ceil(S.total/S.taille));
  p.innerHTML='<span class="compte">'+fmtNb(debut,0)+'–'+fmtNb(fin,0)+' sur '+fmtNb(S.total,0)+'</span>'+
    '<span class="pager">'+
      '<button type="button" class="btn" id="prec"'+(S.page<=1?' disabled':'')+'>Précédent</button>'+
      '<span>page '+fmtNb(S.page,0)+' / '+fmtNb(pages,0)+'</span>'+
      '<button type="button" class="btn" id="suiv"'+(S.page>=pages?' disabled':'')+'>Suivant</button></span>';
  const a=document.getElementById('prec'),b=document.getElementById('suiv');
  if(a)a.addEventListener('click',()=>{if(S.page>1){S.page--;charger();}});
  if(b)b.addEventListener('click',()=>{if(S.page<pages){S.page++;charger();}});
}

// ── Détail ───────────────────────────────────────────────────────
function enteteDetail(titre){
  return '<div class="detail-head"><h2>'+esc(titre)+'</h2>'+
    '<button type="button" class="detail-fermer" onclick="fermerDetail()" title="Fermer">×</button></div>';
}
async function ouvrirDetail(id){
  S.selection=id;renderGrille();
  const d=document.getElementById('detail');
  if(!d)return;
  d.classList.add('ouvert');
  d.innerHTML=enteteDetail('Détail')+'<div style="padding:18px"><div class="skel"></div></div>';
  let r;
  try{ r=await api('/api/erp/'+encodeURIComponent(S.ecran)+'/detail/'+encodeURIComponent(id)); }
  catch(e){ d.innerHTML=enteteDetail('Détail')+'<div class="vide-msg">'+esc(e.message)+'</div>'; return; }
  let h=enteteDetail(S.def?S.def.label:'Détail');
  (r.groupes||[]).forEach((g,i)=>{
    h+='<div class="groupe'+(g.replie?' replie':'')+'" data-g="'+i+'">'+
       '<div class="groupe-titre">'+esc(g.titre)+'</div><div class="groupe-corps">';
    (g.champs||[]).forEach(c=>{
      const v=cellule(c,c.valeur);
      h+='<div class="ligne-champ"><span class="lab">'+esc(c.label)+'</span>'+
         '<span class="val '+(v.cls.indexOf('mono')>=0?'mono':'')+'">'+v.html+'</span></div>';
    });
    h+='</div></div>';
  });
  d.innerHTML=h;
  d.querySelectorAll('.groupe-titre').forEach(t=>{
    t.addEventListener('click',()=>t.parentNode.classList.toggle('replie'));
  });
}
function fermerDetail(){
  const d=document.getElementById('detail');
  if(d){d.classList.remove('ouvert');d.innerHTML='';}
  S.selection=null;renderGrille();
}

// ── Shell ────────────────────────────────────────────────────────
function basculerSidebar(){document.body.classList.toggle('sb-open');}
function fermerSidebar(){document.body.classList.remove('sb-open');}
function majTheme(){
  const clair=document.body.classList.contains('light');
  const i=document.getElementById('theme-ico'),l=document.getElementById('theme-label');
  if(i)i.innerHTML=clair?ICO_MOON:ICO_SUN;
  if(l)l.textContent=clair?'Mode sombre':'Mode clair';
}
function appliquerHash(){
  const m=String(location.hash||'').match(/^#\/([a-z_]+)$/);
  if(m&&S.meta&&S.meta.present){ouvrirEcran(m[1]);}else{ouvrirMenu();}
  fermerSidebar();
}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    if(document.body.classList.contains('sb-open')){fermerSidebar();return;}
    const d=document.getElementById('detail');
    if(d&&d.classList.contains('ouvert'))fermerDetail();
  }
});

async function boot(){
  try{if(localStorage.getItem('mysifa_theme')==='light')document.body.classList.add('light');}catch(e){}
  majTheme();
  const bt=document.getElementById('btn-theme');
  if(bt)bt.addEventListener('click',()=>{
    document.body.classList.toggle('light');
    try{localStorage.setItem('mysifa_theme',document.body.classList.contains('light')?'light':'dark');}catch(e){}
    majTheme();
  });
  const bl=document.getElementById('btn-logout');
  if(bl)bl.addEventListener('click',async()=>{
    try{await fetch('/api/logout',{method:'POST',credentials:'include'});}catch(e){}
    location.href='/';
  });
  try{
    const me=await api('/api/me');
    const n=document.getElementById('uc-name'),ro=document.getElementById('uc-role');
    if(n)n.textContent=me.nom||me.email||'—';
    if(ro)ro.textContent=me.role||'—';
  }catch(e){}
  try{ S.meta=await api('/api/erp/meta'); }
  catch(e){
    document.getElementById('corps').innerHTML='<div class="vide-msg">'+esc(e.message)+'</div>';
    return;
  }
  renderFraicheur();renderNav();appliquerHash();
  window.addEventListener('hashchange',appliquerHash);
}
boot();
</script>

</body>
</html>
"""
