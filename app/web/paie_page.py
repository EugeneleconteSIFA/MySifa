"""MySifa — Page Gestion des Paies
Route : /paie
Accès : superadmin + direction + administration
Sécurité double : auth session MySifa + mot de passe "safir" côté client
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.auth_service import get_current_user, is_admin
from app.web.access_denied import access_denied_response

router = APIRouter()


@router.get("/paie", response_class=HTMLResponse)
def paie_page(request: Request):
    try:
        user = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/paie", status_code=302)
        raise
    if not is_admin(user):
        return access_denied_response("Gestion des Paies")
    return HTMLResponse(
        content=PAIE_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


PAIE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Gestion des Paies — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/support_widget.css">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;
  --muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.08);
  --ok:#34d399;--danger:#f87171;--warn:#fbbf24;--success:#34d399;
  --sidebar-w:280px;
}
body.light{
  --bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;
  --muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.08);
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;font-size:14px}

/* ── Password overlay ── */
#pw-overlay{
  position:fixed;inset:0;background:var(--bg);z-index:9999;
  display:flex;align-items:center;justify-content:center;
}
.pw-card{
  background:var(--card);border:1px solid var(--border);border-radius:20px;
  padding:40px 36px;width:360px;text-align:center;
  box-shadow:0 24px 80px rgba(0,0,0,.5);
}
.pw-logo{font-size:26px;font-weight:900;color:var(--accent);letter-spacing:-1px;margin-bottom:4px}
.pw-logo span{color:var(--text)}
.pw-sub{font-size:12px;color:var(--muted);margin-bottom:28px}
.pw-label{font-size:12px;font-weight:700;color:var(--text2);text-align:left;display:block;margin-bottom:6px}
.pw-input{
  width:100%;padding:12px 14px;background:var(--bg);border:1.5px solid var(--border);
  border-radius:10px;color:var(--text);font-size:15px;font-family:inherit;
  outline:none;letter-spacing:3px;text-align:center;
}
.pw-input:focus{border-color:var(--accent)}
.pw-btn{
  width:100%;margin-top:14px;padding:13px;border-radius:10px;border:none;
  background:var(--accent);color:#0a0e17;font-weight:800;font-size:14px;
  cursor:pointer;font-family:inherit;transition:opacity .15s;
}
.pw-btn:hover{opacity:.85}
.pw-err{color:var(--danger);font-size:12px;margin-top:10px;min-height:18px}
.pw-hint{font-size:11px;color:var(--muted);margin-top:16px}

/* ── Layout ── */
#app{display:grid;grid-template-columns:var(--sidebar-w) 1fr;height:100vh;overflow:hidden}

/* ── Sidebar ── */
.paie-sidebar{
  grid-column:1;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;
}
.paie-sidebar-head{
  padding:18px 16px 12px;border-bottom:1px solid var(--border);flex-shrink:0;
}
.paie-brand{font-size:18px;font-weight:900;letter-spacing:-.5px}
.paie-brand span{color:var(--accent)}
.paie-brand-sub{font-size:11px;color:var(--muted);margin-top:1px}
.paie-search{
  width:100%;padding:9px 12px;background:var(--bg);border:1.5px solid var(--border);
  border-radius:9px;color:var(--text);font-size:12px;font-family:inherit;
  outline:none;margin-top:12px;
}
.paie-search:focus{border-color:var(--accent)}
.paie-search-hint{font-size:10px;color:var(--muted);margin-top:5px;line-height:1.4}

.emp-list{flex:1;overflow-y:auto;padding:8px}
.emp-item{
  padding:10px 12px;border-radius:8px;cursor:pointer;
  border:1px solid transparent;transition:all .12s;margin-bottom:2px;
}
.emp-item:hover{background:var(--accent-bg);border-color:rgba(34,211,238,.2)}
.emp-item.active{background:var(--accent-bg);border-color:var(--accent)}
.emp-item-name{font-size:13px;font-weight:700;color:var(--text)}
.emp-item-sub{font-size:11px;color:var(--muted);margin-top:1px}
.emp-item.inactive .emp-item-name{opacity:.5}

.paie-sidebar-bottom{
  padding:12px;border-top:1px solid var(--border);flex-shrink:0;
  display:flex;flex-direction:column;gap:8px;
}
.paie-back-btn{
  display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:10px;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;font-size:12px;font-family:inherit;width:100%;
  transition:all .12s;
}
.paie-back-btn:hover{border-color:var(--accent);color:var(--accent)}
.paie-wm{font-weight:900;color:var(--text2)}
.paie-wm span{color:var(--accent)}

/* ── Main content ── */
.paie-main{
  grid-column:2;display:flex;flex-direction:column;overflow:hidden;
}

/* ── Top bar ── */
.paie-topbar{
  padding:14px 24px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:16px;flex-shrink:0;flex-wrap:wrap;
}
.paie-period-nav{display:flex;align-items:center;gap:8px}
.paie-period-btn{
  padding:7px 11px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:13px;
  font-family:inherit;transition:all .12s;
}
.paie-period-btn:hover{border-color:var(--accent);color:var(--accent)}
.paie-period-label{
  font-size:15px;font-weight:700;color:var(--accent);
  min-width:160px;text-align:center;
}
.paie-topbar-actions{display:flex;align-items:center;gap:10px;margin-left:auto}
.paie-export-btn{
  display:flex;align-items:center;gap:8px;padding:9px 16px;border-radius:9px;
  background:var(--accent);color:#0a0e17;font-weight:700;font-size:12px;
  border:none;cursor:pointer;font-family:inherit;transition:opacity .15s;
}
.paie-export-btn:hover{opacity:.85}
.paie-export-btn:disabled{opacity:.4;cursor:not-allowed}
.paie-save-all-btn{
  display:flex;align-items:center;gap:8px;padding:9px 16px;border-radius:9px;
  background:var(--ok);color:#0a0e17;font-weight:700;font-size:12px;
  border:none;cursor:pointer;font-family:inherit;transition:opacity .15s;
}
.paie-save-all-btn:hover{opacity:.85}

/* ── Form area ── */
.paie-form-area{flex:1;overflow-y:auto;padding:20px 24px}
.emp-placeholder{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100%;color:var(--muted);gap:12px;
}
.emp-placeholder svg{opacity:.3}
.emp-placeholder p{font-size:14px}

/* ── Employee header ── */
.emp-header{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:16px 20px;margin-bottom:20px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;
}
.emp-header-name{font-size:20px;font-weight:900;color:var(--text)}
.emp-header-meta{display:flex;gap:16px;flex-wrap:wrap}
.emp-badge{
  font-size:11px;font-weight:700;padding:3px 9px;border-radius:6px;
  background:var(--accent-bg);color:var(--accent);border:1px solid rgba(34,211,238,.3);
}
.emp-header-save{
  padding:8px 18px;border-radius:8px;background:var(--accent);color:#0a0e17;
  font-weight:700;font-size:12px;border:none;cursor:pointer;font-family:inherit;
  transition:opacity .15s;
}
.emp-header-save:hover{opacity:.85}
.emp-header-save.saved{background:var(--ok)}

/* ── Sections ── */
.paie-section{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  margin-bottom:16px;overflow:hidden;
}
.paie-section-title{
  padding:12px 18px;font-size:12px;font-weight:800;color:var(--accent);
  text-transform:uppercase;letter-spacing:.5px;background:rgba(34,211,238,.04);
  border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;
}
.paie-grid{
  display:grid;grid-template-columns:repeat(auto-fill, minmax(240px,1fr));
  gap:0;
}
.paie-field{
  padding:10px 14px;border-bottom:1px solid var(--border);
  display:flex;flex-direction:column;gap:4px;
  border-right:1px solid var(--border);
}
.paie-field:last-child{border-right:none}
.paie-field-label{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}
.paie-field input,.paie-field select,.paie-field textarea{
  background:var(--bg);border:1.5px solid var(--border);border-radius:7px;
  color:var(--text);font-size:13px;font-family:inherit;padding:7px 10px;
  outline:none;width:100%;transition:border-color .12s;
}
.paie-field input:focus,.paie-field select:focus,.paie-field textarea:focus{
  border-color:var(--accent);
}
.paie-field input[readonly]{color:var(--muted);cursor:default}
.paie-field textarea{resize:vertical;min-height:60px}
.paie-field select option{background:var(--card)}

/* ── Full-width note field ── */
.paie-field.full{grid-column:1/-1}

/* ── Toast ── */
.paie-toast{
  position:fixed;bottom:24px;right:24px;z-index:999;
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:12px 18px;font-size:13px;font-weight:600;
  box-shadow:0 8px 32px rgba(0,0,0,.4);display:flex;align-items:center;gap:10px;
  animation:toastIn .2s ease;
}
@keyframes toastIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

/* ── History panel ── */
.paie-history-btn{
  display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:9px;
  border:1px solid var(--border);background:transparent;color:var(--text2);
  font-size:12px;cursor:pointer;font-family:inherit;transition:all .12s;
}
.paie-history-btn:hover{border-color:var(--accent);color:var(--accent)}

.history-modal{
  position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:500;
  display:flex;align-items:center;justify-content:center;padding:18px;
}
.history-card{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:20px;width:460px;max-height:70vh;display:flex;flex-direction:column;
  box-shadow:0 24px 64px rgba(0,0,0,.45);
}
.history-title{font-size:15px;font-weight:800;margin-bottom:14px;color:var(--text)}
.history-list{overflow-y:auto;flex:1}
.history-item{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 14px;border-radius:8px;cursor:pointer;
  border:1px solid transparent;transition:all .12s;margin-bottom:4px;
}
.history-item:hover{background:var(--accent-bg);border-color:rgba(34,211,238,.2)}
.history-item.active{background:var(--accent-bg);border-color:var(--accent)}
.history-item-label{font-size:13px;font-weight:700;color:var(--accent)}
.history-item-sub{font-size:11px;color:var(--muted)}
.history-close{
  margin-top:14px;padding:10px;border-radius:9px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;
  font-size:12px;width:100%;transition:all .12s;
}
.history-close:hover{border-color:var(--accent);color:var(--accent)}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--muted)}

/* ── Unsaved indicator ── */
.unsaved-dot{
  width:7px;height:7px;border-radius:50%;background:var(--warn);
  display:inline-block;margin-left:6px;
}
</style>
</head>
<body>

<!-- ── Password overlay ── -->
<div id="pw-overlay">
  <div class="pw-card">
    <div class="pw-logo">My<span>Sifa</span></div>
    <div class="pw-brand-line" style="font-size:13px;font-weight:700;color:var(--text2);margin-bottom:4px">Gestion des Paies</div>
    <div class="pw-sub">Cette section est protégée. Entrez le mot de passe pour continuer.</div>
    <label class="pw-label" for="pw-input">Mot de passe</label>
    <input class="pw-input" type="password" id="pw-input" placeholder="••••••••" autocomplete="off">
    <button class="pw-btn" id="pw-btn" onclick="checkPassword()">Accéder →</button>
    <div class="pw-err" id="pw-err"></div>
    <div class="pw-hint">Accès réservé à la comptabilité et la direction.</div>
  </div>
</div>

<!-- ── App ── -->
<div id="app" style="display:none">
  <!-- Sidebar -->
  <nav class="paie-sidebar">
    <div class="paie-sidebar-head">
      <div class="paie-brand">My<span>Sifa</span> <span style="color:var(--text2);font-weight:400">Paies</span></div>
      <div class="paie-brand-sub">Gestion des paies</div>
      <input class="paie-search" type="search" id="emp-search" placeholder="Rechercher un employé…" oninput="filterEmployes()" autocomplete="off">
      <div class="paie-search-hint">Cherchez par nom, prénom ou contrat. Tous les employés MySifa sont listés.</div>
    </div>
    <div class="emp-list" id="emp-list"></div>
    <div class="paie-sidebar-bottom">
      <button class="support-btn" onclick="openSupport()">
        <span class="support-ico" id="support-ico-slot"></span>
        <span>Contacter le support</span>
      </button>
      <button class="paie-back-btn" onclick="window.location.href='/'">
        ← Retour <span class="paie-wm">My<span>Sifa</span></span>
      </button>
    </div>
  </nav>

  <!-- Main -->
  <main class="paie-main">
    <!-- Top bar -->
    <div class="paie-topbar">
      <div class="paie-period-nav">
        <button class="paie-period-btn" onclick="changePeriod(-1)">‹</button>
        <div class="paie-period-label" id="period-label">—</div>
        <button class="paie-period-btn" onclick="changePeriod(+1)">›</button>
      </div>
      <button class="paie-history-btn" onclick="showHistory()">📋 Historique</button>
      <div class="paie-topbar-actions">
        <button class="paie-export-btn" id="export-btn" onclick="exportXlsx()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Exporter Excel
        </button>
      </div>
    </div>

    <!-- Form area -->
    <div class="paie-form-area" id="form-area">
      <div class="emp-placeholder" id="emp-placeholder">
        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>
        <p>Sélectionnez un employé dans la liste</p>
      </div>
      <div id="emp-form" style="display:none"></div>
    </div>
  </main>
</div>

<!-- History modal -->
<div class="history-modal" id="history-modal" style="display:none" onclick="if(event.target===this)hideHistory()">
  <div class="history-card">
    <div class="history-title">📋 Historique des périodes</div>
    <div class="history-list" id="history-list"></div>
    <button class="history-close" onclick="hideHistory()">Fermer</button>
  </div>
</div>

<script src="/static/support_widget.js"></script>
<script>
'use strict';

/* ── Constants ── */
const MOIS_FR = ['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

const SECTIONS = [
  {
    title:'📋 Informations contractuelles',
    icon:'📋',
    fields:[
      {key:'matricule',         label:'Matricule',           type:'text',   fixed:true},
      {key:'contrat_type',      label:'Type de contrat',     type:'select', fixed:true, opts:['CDI','CDD','Intérim','Stage','Apprentissage']},
      {key:'date_debut',        label:'Date de début',       type:'date',   fixed:true},
      {key:'date_fin',          label:'Date de fin',         type:'date',   fixed:true},
      {key:'nb_heures_base',    label:'Nb heures de base',   type:'number', fixed:true},
      {key:'taux_horaire',      label:'Taux horaire (€)',    type:'number', fixed:true, step:'0.01'},
      {key:'salaire_mensuel',   label:'Salaire mensuel (€)', type:'number', fixed:true, step:'0.01'},
      {key:'mutuelle',          label:'Mutuelle',            type:'select', fixed:true, opts:['Oui','Non']},
      {key:'avantage_voiture',  label:'Avantage voiture (€)',type:'number', fixed:true, step:'0.01'},
      {key:'prime_anciennete',  label:'Prime ancienneté (%)',type:'number', fixed:true, step:'0.01'},
    ]
  },
  {
    title:'⏱ Heures & Compteurs',
    fields:[
      {key:'compteur_hs_m1',   label:'Compteur HS M-1',          type:'text'},
      {key:'nb_heures_payer',  label:'Nb heures à payer',         type:'number', step:'0.01'},
      {key:'heures_nuit',      label:'Heures de nuit',            type:'text'},
      {key:'heures_nuit_ferie',label:'dont Nuit férié',           type:'text'},
      {key:'heures_nuit_dimanche',label:'dont Nuit dimanche',     type:'text'},
      {key:'heures_nuit_dimanche_ferie',label:'dont Nuit dim. férié',type:'text'},
      {key:'heures_sup_25',    label:'Heures sup 25%',            type:'text'},
      {key:'heures_sup_50',    label:'Heures sup 50%',            type:'text'},
      {key:'heures_sup_nuit',  label:'Heures sup de nuit',        type:'text'},
      {key:'heures_ferie',     label:'Heures jour férié (+150%)', type:'text'},
    ]
  },
  {
    title:'💰 Primes & Commissions',
    fields:[
      {key:'augmentation_salaire',   label:'Augmentation de salaire (€)', type:'number', step:'0.01'},
      {key:'commissions_ventes',     label:'Commissions sur ventes (€)',  type:'number', step:'0.01'},
      {key:'prime_objectifs',        label:'Prime d\'objectifs (€)',      type:'number', step:'0.01'},
      {key:'prime_inflation',        label:'Prime inflation (€)',         type:'number', step:'0.01'},
      {key:'prime_exceptionnelle',   label:'Prime exceptionnelle (€)',    type:'number', step:'0.01'},
      {key:'prime_equipe',           label:'Prime équipe (€)',            type:'number', step:'0.01'},
      {key:'panier',                 label:'Panier (6,47€/jour)',         type:'number', step:'0.01'},
      {key:'solde_tout_compte',      label:'Solde de tout compte',        type:'select', opts:['','Oui','Non']},
    ]
  },
  {
    title:'🏖 Absences',
    fields:[
      {key:'absence_heures',         label:'Absence en heures',              type:'text'},
      {key:'absence_maladie_heures', label:'Maladie en heures',              type:'text'},
      {key:'absence_maladie_jours',  label:'Maladie en jours',               type:'text'},
      {key:'absence_deces_mariage',  label:'Décès familial / Mariage',       type:'text'},
      {key:'absence_cp_heures',      label:'Congés payés en heures',         type:'text'},
      {key:'absence_cp_jours',       label:'Congés payés en jours',          type:'text'},
      {key:'date_conges_payes',      label:'Date des congés payés',          type:'text'},
      {key:'absence_rtt',            label:'Absence RTT',                    type:'text'},
      {key:'absence_css_heures',     label:'Congés sans solde heures',       type:'text'},
      {key:'absence_css_jours',      label:'Congés sans solde jours',        type:'text'},
      {key:'absence_non_justifie_h', label:'Absence non justifiée (h)',      type:'text'},
      {key:'absence_non_justifie_j', label:'Absence non justifiée (j)',      type:'text'},
      {key:'absence_justifiee_np_h', label:'Justifiée non payée (h)',        type:'text'},
      {key:'absence_justifiee_np_j', label:'Justifiée non payée (j)',        type:'text'},
      {key:'absence_at_heures',      label:'AT en heures',                   type:'text'},
      {key:'absence_at_jours',       label:'AT en jours',                    type:'text'},
      {key:'mi_temps_therapeutique', label:'Mi-temps thérapeutique',         type:'text'},
      {key:'absence_chomage_partiel',label:'Chômage partiel',                type:'text'},
      {key:'absence_conge_parentale',label:'Congé parental',                 type:'text'},
    ]
  },
  {
    title:'💳 Frais & Divers',
    fields:[
      {key:'frais_pro',      label:'Frais professionnels (€)', type:'number', step:'0.01'},
      {key:'frais_transport',label:'Remboursement transport (€)',type:'number',step:'0.01'},
      {key:'pret_sifa',      label:'Prêt SIFA (€)',            type:'number', step:'0.01'},
      {key:'atd',            label:'ATD (€)',                  type:'number', step:'0.01'},
      {key:'acompte_exceptionnel',label:'Acompte exceptionnel (€)',type:'number',step:'0.01'},
    ]
  },
  {
    title:'📝 Informations complémentaires',
    fields:[
      {key:'information', label:'Information / note libre', type:'textarea', full:true},
    ]
  },
];

/* ── State ── */
let S = {
  employes: [],
  empSearch: '',
  currentEmpId: null,
  annee: new Date().getFullYear(),
  mois: new Date().getMonth() + 1,
  variablesCache: {},   // {annee_mois: {user_id: {data}}}
  dirtyEmpId: null,
  pendingFixed: {},     // {user_id: {...}}
  pendingVar: {},       // {user_id: {...}}
};

/* ── API ── */
async function api(path, opts={}) {
  const r = await fetch(path, {credentials:'include', ...opts});
  if (!r.ok) {
    let e = {}; try { e = await r.json(); } catch {}
    throw new Error(e.detail || ('Erreur ' + r.status));
  }
  return await r.json();
}

/* ── Password ── */
const PW_KEY = 'paie_auth_v1';
function checkPassword() {
  const val = document.getElementById('pw-input').value.trim().toLowerCase();
  if (val === 'safir') {
    sessionStorage.setItem(PW_KEY, '1');
    document.getElementById('pw-overlay').style.display = 'none';
    document.getElementById('app').style.display = 'grid';
    initApp();
  } else {
    const err = document.getElementById('pw-err');
    err.textContent = 'Mot de passe incorrect.';
    document.getElementById('pw-input').value = '';
    setTimeout(() => { err.textContent = ''; }, 3000);
  }
}
document.getElementById('pw-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') checkPassword();
});

/* ── Period ── */
function periodKey() { return S.annee + '_' + S.mois; }
function periodLabel() { return MOIS_FR[S.mois] + ' ' + S.annee; }

function updatePeriodLabel() {
  document.getElementById('period-label').textContent = periodLabel();
}

function changePeriod(delta) {
  let m = S.mois + delta;
  let y = S.annee;
  if (m < 1) { m = 12; y--; }
  if (m > 12) { m = 1; y++; }
  S.mois = m; S.annee = y;
  S.pendingVar = {};
  updatePeriodLabel();
  loadVariables().then(() => {
    if (S.currentEmpId) renderForm(S.currentEmpId);
  });
}

/* ── Employees ── */
async function loadEmployes() {
  const data = await api('/api/paie/employes');
  S.employes = data.employes || [];
}

function filterEmployes() {
  S.empSearch = document.getElementById('emp-search').value;
  renderEmpList();
}

function scoreMatch(hay, tokens) {
  if (!tokens.length) return 1;
  const h = (hay||'').toLowerCase();
  let score = 0;
  for (const t of tokens) {
    if (h.includes(t)) score += (h.startsWith(t) ? 2 : 1);
  }
  return score;
}

function renderEmpList() {
  const tokens = S.empSearch.toLowerCase().trim().split(/\s+/).filter(Boolean);
  let list = S.employes.filter(e => {
    if (!tokens.length) return true;
    const hay = [e.nom_complet, e.contrat_type, e.email].join(' ');
    return scoreMatch(hay, tokens) > 0;
  }).sort((a, b) => {
    if (!tokens.length) return (a.nom_complet||'').localeCompare(b.nom_complet||'', 'fr');
    const sa = scoreMatch([a.nom_complet,a.contrat_type].join(' '), tokens);
    const sb = scoreMatch([b.nom_complet,b.contrat_type].join(' '), tokens);
    return sb - sa || (a.nom_complet||'').localeCompare(b.nom_complet||'', 'fr');
  });

  const container = document.getElementById('emp-list');
  container.innerHTML = '';
  if (!list.length) {
    container.innerHTML = '<div style="padding:16px;font-size:12px;color:var(--muted);text-align:center">Aucun employé trouvé</div>';
    return;
  }
  list.forEach(emp => {
    const div = document.createElement('div');
    div.className = 'emp-item' + (emp.user_id === S.currentEmpId ? ' active' : '') + (!emp.actif ? ' inactive' : '');
    div.innerHTML = `
      <div class="emp-item-name">${esc(emp.nom_complet)}${S.pendingVar[emp.user_id] ? '<span class="unsaved-dot" title="Modifications non enregistrées"></span>' : ''}</div>
      <div class="emp-item-sub">${esc(emp.contrat_type||'CDI')} · ${emp.email||''}</div>
    `;
    div.onclick = () => selectEmp(emp.user_id);
    container.appendChild(div);
  });
}

/* ── Variables ── */
async function loadVariables() {
  const pk = periodKey();
  if (S.variablesCache[pk]) return; // already loaded
  try {
    const data = await api(`/api/paie/variables/${S.annee}/${S.mois}`);
    S.variablesCache[pk] = data.variables || {};
  } catch {
    S.variablesCache[pk] = {};
  }
}

function getVarForEmp(userId) {
  const pk = periodKey();
  const cached = (S.variablesCache[pk] || {})[String(userId)] || {};
  const pending = S.pendingVar[userId] || {};
  return { ...(cached.data || {}), ...pending };
}

function getFixedForEmp(userId) {
  const emp = S.employes.find(e => e.user_id === userId) || {};
  return {
    matricule: emp.matricule,
    contrat_type: emp.contrat_type,
    date_debut: emp.date_debut,
    date_fin: emp.date_fin,
    nb_heures_base: emp.nb_heures_base,
    taux_horaire: emp.taux_horaire,
    salaire_mensuel: emp.salaire_mensuel,
    prime_anciennete: emp.prime_anciennete,
    mutuelle: emp.mutuelle,
    avantage_voiture: emp.avantage_voiture,
  };
}

/* ── Select employee ── */
function selectEmp(userId) {
  S.currentEmpId = userId;
  renderEmpList();
  document.getElementById('emp-placeholder').style.display = 'none';
  document.getElementById('emp-form').style.display = 'block';
  renderForm(userId);
}

/* ── Render form ── */
function renderForm(userId) {
  const emp  = S.employes.find(e => e.user_id === userId);
  if (!emp) return;
  const varD = getVarForEmp(userId);
  const fixD = getFixedForEmp(userId);

  const form = document.getElementById('emp-form');
  form.innerHTML = '';

  // Header
  const hdr = document.createElement('div');
  hdr.className = 'emp-header';
  hdr.innerHTML = `
    <div>
      <div class="emp-header-name">${esc(emp.nom_complet)}</div>
      <div class="emp-header-meta" style="margin-top:8px">
        <span class="emp-badge">${esc(emp.contrat_type||'CDI')}</span>
        ${emp.date_debut ? `<span class="emp-badge">Depuis ${esc(emp.date_debut)}</span>` : ''}
        ${emp.salaire_mensuel ? `<span class="emp-badge">${Number(emp.salaire_mensuel).toLocaleString('fr-FR')} €</span>` : ''}
      </div>
    </div>
    <button class="emp-header-save" id="emp-save-btn" onclick="saveEmp(${userId})">
      💾 Enregistrer
    </button>
  `;
  form.appendChild(hdr);

  // Sections
  SECTIONS.forEach(section => {
    const sec = document.createElement('div');
    sec.className = 'paie-section';

    const title = document.createElement('div');
    title.className = 'paie-section-title';
    title.textContent = section.title;
    sec.appendChild(title);

    const grid = document.createElement('div');
    grid.className = 'paie-grid';

    section.fields.forEach(f => {
      const cell = document.createElement('div');
      cell.className = 'paie-field' + (f.full ? ' full' : '');

      const label = document.createElement('div');
      label.className = 'paie-field-label';
      label.textContent = f.label;
      cell.appendChild(label);

      const val = f.fixed ? (fixD[f.key] ?? '') : (varD[f.key] ?? '');
      let input;

      if (f.type === 'select') {
        input = document.createElement('select');
        (f.opts || []).forEach(opt => {
          const o = document.createElement('option');
          o.value = opt; o.textContent = opt;
          if (String(val) === opt) o.selected = true;
          input.appendChild(o);
        });
      } else if (f.type === 'textarea') {
        input = document.createElement('textarea');
        input.value = val || '';
      } else {
        input = document.createElement('input');
        input.type = f.type || 'text';
        if (f.step) input.step = f.step;
        input.value = val !== null && val !== undefined ? val : '';
      }

      input.dataset.key   = f.key;
      input.dataset.fixed = f.fixed ? '1' : '0';

      input.addEventListener('input', () => {
        const isFixed = input.dataset.fixed === '1';
        if (isFixed) {
          if (!S.pendingFixed[userId]) S.pendingFixed[userId] = {};
          S.pendingFixed[userId][f.key] = input.value;
        } else {
          if (!S.pendingVar[userId]) S.pendingVar[userId] = {};
          S.pendingVar[userId][f.key] = input.value;
        }
        markDirty(userId);
      });

      cell.appendChild(input);
      grid.appendChild(cell);
    });

    sec.appendChild(grid);
    form.appendChild(sec);
  });
}

/* ── Dirty tracking ── */
function markDirty(userId) {
  S.dirtyEmpId = userId;
  renderEmpList();
  const btn = document.getElementById('emp-save-btn');
  if (btn) btn.textContent = '💾 Enregistrer*';
}

/* ── Save ── */
async function saveEmp(userId) {
  const btn = document.getElementById('emp-save-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Enregistrement…'; }
  try {
    const varData = getVarForEmp(userId);
    const fixPending = S.pendingFixed[userId] || {};
    const emp = S.employes.find(e => e.user_id === userId) || {};

    // Save fixed
    const fixBody = {
      matricule:        fixPending.matricule        ?? emp.matricule,
      contrat_type:     fixPending.contrat_type     ?? emp.contrat_type,
      date_debut:       fixPending.date_debut       ?? emp.date_debut,
      date_fin:         fixPending.date_fin         ?? emp.date_fin,
      nb_heures_base:   fixPending.nb_heures_base   ?? emp.nb_heures_base,
      taux_horaire:     fixPending.taux_horaire     ?? emp.taux_horaire,
      salaire_mensuel:  fixPending.salaire_mensuel  ?? emp.salaire_mensuel,
      prime_anciennete: fixPending.prime_anciennete ?? emp.prime_anciennete,
      mutuelle:         fixPending.mutuelle         ?? emp.mutuelle,
      avantage_voiture: fixPending.avantage_voiture ?? emp.avantage_voiture,
    };
    await api(`/api/paie/employes/${userId}/fixed`, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(fixBody),
    });

    // Save variables
    await api(`/api/paie/variables/${S.annee}/${S.mois}/${userId}`, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({data: varData}),
    });

    // Update cache
    const pk = periodKey();
    if (!S.variablesCache[pk]) S.variablesCache[pk] = {};
    S.variablesCache[pk][String(userId)] = {data: varData};

    // Update employes list
    const idx = S.employes.findIndex(e => e.user_id === userId);
    if (idx >= 0) Object.assign(S.employes[idx], fixBody, {mutuelle: fixBody.mutuelle});
    delete S.pendingFixed[userId];
    delete S.pendingVar[userId];

    showToast('✅ Enregistré avec succès', 'ok');
    if (btn) { btn.disabled = false; btn.textContent = '✅ Enregistré'; btn.className = 'emp-header-save saved'; }
    setTimeout(() => { if(btn){btn.textContent='💾 Enregistrer';btn.className='emp-header-save';} }, 2500);
    renderEmpList();

  } catch(e) {
    showToast('❌ Erreur: ' + e.message, 'danger');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Enregistrer'; }
  }
}

/* ── Export ── */
async function exportXlsx() {
  const btn = document.getElementById('export-btn');
  btn.disabled = true; btn.textContent = 'Génération…';
  try {
    const url = `/api/paie/export/${S.annee}/${S.mois}`;
    const r = await fetch(url, {credentials:'include'});
    if (!r.ok) throw new Error('Erreur ' + r.status);
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `paie_${S.annee}_${String(S.mois).padStart(2,'0')}_${MOIS_FR[S.mois]}.xlsx`;
    a.click();
    showToast('✅ Export téléchargé', 'ok');
  } catch(e) {
    showToast('❌ Export échoué: ' + e.message, 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Exporter Excel`;
  }
}

/* ── History ── */
async function showHistory() {
  const modal = document.getElementById('history-modal');
  modal.style.display = 'flex';
  const list = document.getElementById('history-list');
  list.innerHTML = '<div style="padding:12px;color:var(--muted);font-size:12px">Chargement…</div>';
  try {
    const data = await api('/api/paie/historique');
    const periodes = data.periodes || [];
    if (!periodes.length) {
      list.innerHTML = '<div style="padding:12px;color:var(--muted);font-size:12px">Aucune donnée enregistrée.</div>';
      return;
    }
    list.innerHTML = '';
    periodes.forEach(p => {
      const active = p.annee === S.annee && p.mois === S.mois;
      const div = document.createElement('div');
      div.className = 'history-item' + (active ? ' active' : '');
      div.innerHTML = `
        <div>
          <div class="history-item-label">${esc(p.mois_label)} ${p.annee}</div>
          <div class="history-item-sub">${p.nb_employes} employé(s) · modifié ${esc(p.last_update?.slice(0,10)||'')}</div>
        </div>
        <span style="font-size:11px;color:var(--accent)">${active?'✓ Période actuelle':'→ Aller'}</span>
      `;
      div.onclick = () => {
        S.annee = p.annee; S.mois = p.mois;
        S.pendingVar = {};
        updatePeriodLabel();
        loadVariables().then(() => { if(S.currentEmpId) renderForm(S.currentEmpId); });
        hideHistory();
      };
      list.appendChild(div);
    });
  } catch(e) {
    list.innerHTML = `<div style="padding:12px;color:var(--danger);font-size:12px">Erreur: ${esc(e.message)}</div>`;
  }
}
function hideHistory() { document.getElementById('history-modal').style.display='none'; }

/* ── Support ── */
let _meUser = null;
function openSupport() {
  if (window.MySifaSupport && typeof window.MySifaSupport.open === 'function') {
    window.MySifaSupport.open({user:_meUser, page:'Gestion des Paies', notify:(m,t)=>showToast(m,t==='error'?'danger':'ok'), api});
  }
}
function initSupportIcon() {
  const slot = document.getElementById('support-ico-slot');
  if (slot && window.MySifaSupport && window.MySifaSupport.iconSvg) {
    try { slot.innerHTML = window.MySifaSupport.iconSvg(); } catch {}
  }
}

/* ── Toast ── */
let _toastTimer = null;
function showToast(msg, type='ok') {
  const existing = document.querySelector('.paie-toast');
  if (existing) existing.remove();
  if (_toastTimer) clearTimeout(_toastTimer);
  const d = document.createElement('div');
  d.className = 'paie-toast';
  const c = type === 'danger' ? 'var(--danger)' : type === 'warn' ? 'var(--warn)' : 'var(--ok)';
  d.style.borderLeft = '3px solid ' + c;
  d.style.color = c;
  d.textContent = msg;
  document.body.appendChild(d);
  _toastTimer = setTimeout(() => d.remove(), 3500);
}

/* ── Utils ── */
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

/* ── Init ── */
async function initApp() {
  initSupportIcon();
  updatePeriodLabel();
  try {
    _meUser = await api('/api/auth/me');
  } catch {}

  try {
    await loadEmployes();
    renderEmpList();
    await loadVariables();
  } catch(e) {
    showToast('Erreur de chargement: ' + e.message, 'danger');
  }
}

/* ── Auto-check session password ── */
if (sessionStorage.getItem(PW_KEY) === '1') {
  document.getElementById('pw-overlay').style.display = 'none';
  document.getElementById('app').style.display = 'grid';
  initApp();
} else {
  setTimeout(() => document.getElementById('pw-input').focus(), 100);
}
</script>
</body>
</html>"""
