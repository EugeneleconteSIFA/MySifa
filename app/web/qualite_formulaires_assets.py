"""MySifa - Assets de l'onglet Formulaires (MyQualité > Formulaires).

JS et CSS injectés dans /qualite par le placeholder __FORMULAIRES_ASSETS__.
Reprend les classes de l'onglet FSC (fsc-hero, fsc-btn) pour l'en-tête.

Deux vues :
  formulaires-list  liste des formulaires (filtre brouillons / publiés / archivés)
  formulaire-edit   éditeur (static/mysifa_formulaire_editeur.js) à gauche,
                    aperçu destinataire (static/mysifa_formulaire.js) à droite,
                    enregistrement automatique 2 s après la dernière frappe.

API : app/routers/qualite_formulaires.py. Adresse : static/qualite_url.js
(`vue=formulaires`, `filtre`, `formulaire=<id>`).
"""

FORMULAIRES_JS = r"""
// ══════════════════════════════════════════════════════════════════════
// MyQualité - Formulaires
// ══════════════════════════════════════════════════════════════════════

S.formu = {
  liste: null,         // /api/qualite/formulaires
  filtre: 'actifs',    // actifs | brouillon | publie | archive
  q: '',
  courant: null,       // formulaire ouvert (détail complet)
  ed: null,            // éditeur monté
  etat: '',            // '' | 'attente' | 'envoi' | 'ok' | 'erreur'
  timer: null,
  enCours: null,       // promesse d'enregistrement en vol
  iaModeles: null,     // /api/qualite/formulaires/ia/modeles
  iaNote: null,        // {id, resume, remarques, modele} — dernière proposition appliquée
  iaAvant: null,       // {id, titre, description, schema} — pour « Annuler la modification »
  onglet: 'questions', // questions | suivi
  envois: null,        // /api/qualite/formulaires/{id}/envois (formulaire ouvert)
  envoiType: 'fournisseur',
  envoiQ: '',
  envoiCandidats: [],
  envoiSel: new Map(), // email → destinataire choisi
};
// Nom de l'entreprise (config.APP_ORG_NAME), injecté par qualite_page.py.
const FORMU_ORG = __ORG_NAME_JS__;
const FORMU_TYPES_DEST = [
  {v:'fournisseur', l:'Fournisseurs'},
  {v:'client',      l:'Clients'},
  {v:'personnel',   l:'Personnel'},
  {v:'libre',       l:'Adresse libre'},
];
const FORMU_STATUTS_DEST = {envoye:'Envoyé', ouvert:'Ouvert', repondu:'Répondu'};

const FORMU_FILTRES = [
  {v:'actifs',    l:'En cours'},
  {v:'brouillon', l:'Brouillons'},
  {v:'publie',    l:'Publiés'},
  {v:'archive',   l:'Archivés'},
];

(function injectFormuCss(){
  if(document.getElementById('formu-css')) return;
  const st = document.createElement('style'); st.id = 'formu-css';
  st.textContent = `
.formu-filtres{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:12px}
.formu-pill{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.formu-pill:hover{border-color:var(--accent);color:var(--accent)}
.formu-pill.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.formu-pill b{font-weight:800}
.formu-search{flex:1 1 220px;min-width:180px;max-width:340px;margin-left:auto;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-family:inherit;font-size:13px}
.formu-search:focus{outline:none;border-color:var(--accent)}
.formu-liste{display:flex;flex-direction:column;gap:8px}
.formu-row{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;cursor:pointer;transition:border-color .15s}
.formu-row:hover{border-color:var(--accent)}
.formu-row:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.formu-row-main{flex:1;min-width:0}
.formu-row-titre{font-size:14px;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.formu-row-meta{font-size:12px;color:var(--muted);margin-top:2px}
.formu-row-actions{display:flex;gap:6px;flex-wrap:wrap}
.formu-row .fsc-btn{background:var(--bg)}
.formu-row .fsc-btn:hover{background:var(--card)}
.formu-badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid var(--border);color:var(--text2);background:var(--bg);white-space:nowrap}
.formu-badge.publie{border-color:var(--success);color:var(--success);background:transparent}
.formu-badge.modif{border-color:var(--warn);color:var(--warn);background:transparent}
.formu-badge.archive{color:var(--muted)}
.formu-vide{background:var(--card);border:1px dashed var(--border);border-radius:12px;padding:28px;text-align:center;color:var(--muted);font-size:13px}
.formu-barre{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.formu-barre .formu-etat{font-size:12px;color:var(--muted);margin-right:auto}
.formu-etat.erreur{color:var(--danger);font-weight:600}
.formu-entete{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.formu-entete input,.formu-entete textarea{width:100%;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-family:inherit;font-size:13px}
.formu-entete input.formu-titre{font-size:18px;font-weight:700}
.formu-entete input:focus,.formu-entete textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.formu-entete textarea{resize:vertical}
.formu-version{font-size:12px;color:var(--muted)}
.formu-grille{display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,420px);gap:18px;align-items:start}
.formu-apercu{position:sticky;top:12px;background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:12px;max-height:calc(100vh - 40px);overflow:auto}
.formu-apercu-lbl{font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.formu-apercu-carte{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
.formu-apercu-carte h2{margin:0 0 6px;font-size:18px;color:var(--text)}
.formu-apercu-carte .formu-apercu-desc{font-size:13px;color:var(--text2);white-space:pre-wrap;line-height:1.5;margin:0 0 14px}
.formu-apercu-note{font-size:11px;color:var(--muted);margin-top:8px}
.formu-lecture{max-width:720px}
.formu-ia-note{background:var(--iav-bg,var(--accent-bg));border:1px solid var(--iav-bord,var(--accent));border-radius:12px;padding:12px 14px;margin-bottom:14px;display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}
.formu-ia-note-txt{flex:1;min-width:240px;font-size:13px;color:var(--text);line-height:1.5}
.formu-ia-note-txt b{color:var(--iav-1,var(--accent))}
.formu-ia-note ul{margin:6px 0 0;padding-left:18px;color:var(--text2);font-size:12px}
.formu-ia-note .fsc-btn{background:var(--card)}
.formu-ia-ex{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 12px}
.formu-ia-ex button{padding:5px 10px;border-radius:999px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;cursor:pointer;font-family:inherit;text-align:left}
.formu-ia-ex button:hover{border-color:var(--accent);color:var(--accent)}
.formu-ia-f{display:flex;flex-direction:column;gap:5px;margin-bottom:12px}
.formu-ia-f>span{font-size:12px;font-weight:600;color:var(--text2)}
.formu-ia-f textarea,.formu-ia-f select,.formu-ia-f input[type=file]{width:100%;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-family:inherit;font-size:13px}
.formu-ia-f textarea{resize:vertical;min-height:110px}
.formu-ia-aide{font-size:11px;color:var(--muted)}
.formu-onglets{display:flex;gap:4px;border-bottom:1px solid var(--border);margin-bottom:14px}
.formu-onglet{padding:9px 14px;border:none;border-bottom:2px solid transparent;background:none;color:var(--text2);font:inherit;font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-1px}
.formu-onglet:hover{color:var(--accent)}
.formu-onglet.active{color:var(--accent);border-bottom-color:var(--accent)}
.formu-export{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.formu-export-lbl{font-size:12px;color:var(--muted);margin-right:auto}
.formu-envoi{background:var(--card);border:1px solid var(--border);border-radius:12px;margin-bottom:12px;overflow:hidden}
.formu-envoi-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px 14px;border-bottom:1px solid var(--border)}
.formu-envoi-hd b{font-size:14px;color:var(--text)}
.formu-envoi-meta{font-size:12px;color:var(--muted);flex:1;min-width:200px}
.formu-envoi .fsc-btn{background:var(--bg)}
.formu-envoi .fsc-btn:hover{background:var(--card)}
.formu-dest{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px}
.formu-dest:last-child{border-bottom:none}
.formu-dest.retire{opacity:.5}
.formu-dest-qui{flex:1;min-width:200px}
.formu-dest-qui b{color:var(--text)}
.formu-dest-qui span{display:block;font-size:12px;color:var(--muted);overflow-wrap:anywhere}
.formu-dest-actions{display:flex;gap:6px;flex-wrap:wrap}
.formu-badge.ouvert{border-color:var(--accent);color:var(--accent);background:transparent}
.formu-badge.nc{border-color:var(--danger);color:var(--danger);background:transparent}
.formu-env-types{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.formu-env-liste{border:1px solid var(--border);border-radius:10px;max-height:280px;overflow:auto;background:var(--card)}
.formu-env-ligne{display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:1px solid var(--border);cursor:pointer;font-size:13px}
.formu-env-ligne:last-child{border-bottom:none}
.formu-env-ligne:hover{background:var(--accent-bg)}
.formu-env-ligne input{width:15px;height:15px;accent-color:var(--accent);margin:0}
.formu-env-ligne span{flex:1;min-width:0}
.formu-env-ligne small{display:block;color:var(--muted);overflow-wrap:anywhere}
.formu-env-sel{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.formu-env-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 6px 4px 10px;border-radius:999px;background:var(--accent-bg);border:1px solid var(--accent);color:var(--accent);font-size:12px;max-width:100%}
.formu-env-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.formu-env-chip button{border:none;background:none;color:inherit;cursor:pointer;font-size:14px;line-height:1;padding:0 2px}
.formu-env-2{display:grid;grid-template-columns:minmax(0,1fr) 180px;gap:10px}
@media(max-width:600px){.formu-env-2{grid-template-columns:minmax(0,1fr)}}
@media(max-width:980px){.formu-grille{grid-template-columns:minmax(0,1fr)}.formu-apercu{position:static;max-height:none}}
@media(max-width:600px){.formu-row{flex-wrap:wrap}.formu-row-actions{width:100%}}
`;
  document.head.appendChild(st);
})();

function formuEstAdmin(){ return !!S.isQualiteAdmin; }

function formuDate(s){
  if(!s) return '';
  const d = String(s).slice(0,10).split('-');
  return d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0] : String(s);
}

function formuBadges(f){
  const b = [];
  if(f.statut === 'archive') b.push('<span class="formu-badge archive">Archivé</span>');
  else if(f.version_courante) b.push('<span class="formu-badge publie">Publié · v' + f.version_courante + '</span>');
  else b.push('<span class="formu-badge">Brouillon</span>');
  if(f.a_publier && f.statut !== 'archive') b.push('<span class="formu-badge modif" title="Le brouillon diffère de la dernière version publiée">Modifications non publiées</span>');
  return b.join(' ');
}

// ── Liste ──────────────────────────────────────────────────────────────

async function formuEnter(){
  const root = document.getElementById('content');
  if(!root) return;
  if(!S.formu.liste){
    root.innerHTML = '<div class="fsc-hero"><div class="fsc-hero-txt"><h1>Formulaires</h1><p>Chargement…</p></div></div>';
  }
  await formuCharger();
}

async function formuCharger(){
  try{
    const r = await api('/api/qualite/formulaires');
    if(!r.ok){ showToast('Chargement des formulaires impossible.','danger'); return; }
    S.formu.liste = (await r.json()).formulaires || [];
    if(S.view === 'formulaires-list') formuRenderListe();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

function formuFiltrer(liste){
  const q = (S.formu.q || '').trim().toLowerCase();
  return liste.filter(f => {
    if(S.formu.filtre === 'actifs' && f.statut === 'archive') return false;
    if(S.formu.filtre === 'brouillon' && (f.statut === 'archive' || f.version_courante)) return false;
    if(S.formu.filtre === 'publie' && (f.statut === 'archive' || !f.version_courante)) return false;
    if(S.formu.filtre === 'archive' && f.statut !== 'archive') return false;
    if(q && (f.titre + ' ' + (f.description || '')).toLowerCase().indexOf(q) === -1) return false;
    return true;
  });
}

function formuRenderListe(){
  const root = document.getElementById('content');
  const all = S.formu.liste;
  if(!root || !all) return;
  const nb = {
    actifs: all.filter(f => f.statut !== 'archive').length,
    brouillon: all.filter(f => f.statut !== 'archive' && !f.version_courante).length,
    publie: all.filter(f => f.statut !== 'archive' && f.version_courante).length,
    archive: all.filter(f => f.statut === 'archive').length,
  };
  const admin = formuEstAdmin();
  const pills = FORMU_FILTRES.map(x =>
    `<button type="button" class="formu-pill${S.formu.filtre===x.v?' active':''}" onclick="formuSetFiltre('${x.v}')">${escHtml(x.l)} <b>${nb[x.v]}</b></button>`).join('');
  root.innerHTML = `
    <div class="fsc-hero">
      <div class="fsc-hero-txt">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <h1>Formulaires</h1>
          <button type="button" class="qual-help-btn" data-guide="formulaires" onclick="openGuide('formulaires')" title="Guide Formulaires" aria-label="Guide Formulaires">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
          </button>
        </div>
        <p>Questionnaires à faire remplir aux fournisseurs, au personnel ou aux clients : enquêtes, autoévaluations, contrôles. Chaque publication fige une version ; c'est elle qui sera envoyée.</p>
      </div>
      ${admin ? `<div class="fsc-hero-actions"><button type="button" class="fsc-btn ia-btn" data-bulle="Utilise l'IA" onclick="formuIaOuvrir('nouveau')">Créer avec l'IA</button><button type="button" class="fsc-btn primary" onclick="formuNouveau()">+ Nouveau formulaire</button></div>` : ''}
    </div>
    <div class="formu-filtres">${pills}
      <input type="search" id="formu-q" class="formu-search" placeholder="Rechercher (titre, description)" value="${escAttr(S.formu.q)}" oninput="formuSetQ(this.value)" onkeydown="if(event.key==='Escape'){this.value='';formuSetQ('');}">
    </div>
    <div class="formu-liste" id="formu-liste"></div>`;
  formuRenderLignes();
  _refreshHelpBadges();
}

function formuRenderLignes(){
  const box = document.getElementById('formu-liste');
  if(!box) return;
  const lignes = formuFiltrer(S.formu.liste || []);
  const admin = formuEstAdmin();
  if(!lignes.length){
    const q = (S.formu.q || '').trim();
    box.innerHTML = '<div class="formu-vide">' + (q ? 'Aucun résultat pour « ' + escHtml(q) + ' ».'
      : (S.formu.liste.length ? 'Aucun formulaire dans cette catégorie.' : (admin ? 'Aucun formulaire. Créez le premier avec « + Nouveau formulaire ».' : 'Aucun formulaire.'))) + '</div>';
    return;
  }
  box.innerHTML = lignes.map(f => {
    const meta = [f.nb_questions + ' question' + (f.nb_questions > 1 ? 's' : ''),
                  f.nb_destinataires ? f.nb_reponses + ' / ' + f.nb_destinataires + ' réponse' + (f.nb_reponses > 1 ? 's' : '') : '',
                  'modifié le ' + formuDate(f.modifie_le) + (f.modifie_par ? ' par ' + f.modifie_par : '')].filter(Boolean).join(' · ');
    let actions = '';
    if(admin){
      actions += `<button type="button" class="fsc-btn sm" onclick="event.stopPropagation();formuDupliquer(${f.id})">Dupliquer</button>`;
      if(f.statut === 'archive') actions += `<button type="button" class="fsc-btn sm" onclick="event.stopPropagation();formuRestaurer(${f.id})">Restaurer</button>`;
      else if(f.version_courante) actions += `<button type="button" class="fsc-btn sm" onclick="event.stopPropagation();formuArchiver(${f.id})">Archiver</button>`;
      else actions += `<button type="button" class="fsc-btn sm" onclick="event.stopPropagation();formuSupprimer(${f.id})">Supprimer</button>`;
    }
    return `<div class="formu-row" role="button" tabindex="0" onclick="formuOuvrir(${f.id})" onkeydown="if(event.key==='Enter')formuOuvrir(${f.id})">
      <div class="formu-row-main">
        <div class="formu-row-titre">${escHtml(f.titre)}</div>
        <div class="formu-row-meta">${escHtml(meta)}</div>
      </div>
      <div>${formuBadges(f)}</div>
      ${actions ? `<div class="formu-row-actions">${actions}</div>` : ''}
    </div>`;
  }).join('');
}

function formuSetFiltre(v){
  S.formu.filtre = FORMU_FILTRES.some(x => x.v === v) ? v : 'actifs';
  formuRenderListe();
}
function formuSetQ(v){ S.formu.q = v; formuRenderLignes(); }

async function formuNouveau(){
  try{
    const r = await api('/api/qualite/formulaires', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({titre:'Formulaire sans titre'})});
    if(!r.ok){ showToast(await formuErreur(r, 'Création impossible.'),'danger'); return; }
    const f = await r.json();
    S.formu.liste = null;
    await formuOuvrir(f.id, f);
    setTimeout(() => { const t = document.getElementById('formu-titre'); if(t){ t.focus(); t.select(); } }, 30);
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

async function formuErreur(r, def){
  try{ const j = await r.json(); return (j && j.detail) ? String(j.detail) : def; }catch(e){ return def; }
}

async function formuAction(id, chemin, msg, opts){
  try{
    const r = await api('/api/qualite/formulaires/' + id + chemin, Object.assign({method:'POST'}, opts || {}));
    if(!r.ok){ showToast(await formuErreur(r, 'Action impossible.'),'danger'); return null; }
    if(msg) showToast(msg,'success');
    return await r.json();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); return null; }
}

async function formuDupliquer(id){
  await formuEnregistrerMaintenant();
  const f = await formuAction(id, '/dupliquer', 'Copie créée.');
  if(f){ S.formu.liste = null; await formuOuvrir(f.id, f); }
}
async function formuArchiver(id){
  if(!confirm('Archiver ce formulaire ? Il ne pourra plus être envoyé ; ses versions et réponses restent consultables.')) return;
  await formuEnregistrerMaintenant();
  if(await formuAction(id, '/archiver', 'Formulaire archivé.')) formuApresAction(id);
}
async function formuRestaurer(id){
  if(await formuAction(id, '/restaurer', 'Formulaire restauré.')) formuApresAction(id);
}
async function formuSupprimer(id){
  const f = (S.formu.liste || []).find(x => x.id === id) || S.formu.courant;
  if(!confirm('Supprimer définitivement « ' + (f ? f.titre : 'ce formulaire') + ' » ?')) return;
  if(await formuAction(id, '', 'Formulaire supprimé.', {method:'DELETE'})){
    if(S.formu.courant && S.formu.courant.id === id){ S.formu.courant = null; S.formu.ed = null; }
    S.formu.liste = null;
    setView('formulaires-list');
  }
}
async function formuApresAction(id){
  if(S.view === 'formulaire-edit' && S.formu.courant && S.formu.courant.id === id){ await formuOuvrir(id); }
  else { S.formu.liste = null; await formuCharger(); }
}

// ── Édition ────────────────────────────────────────────────────────────

async function formuOuvrir(id, deja){
  await formuEnregistrerMaintenant();
  let f = deja || null;
  if(!f){
    try{
      const r = await api('/api/qualite/formulaires/' + id);
      if(!r.ok){ showToast(await formuErreur(r, 'Formulaire introuvable.'),'danger'); return; }
      f = await r.json();
    }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); return; }
  }
  if(!S.formu.courant || S.formu.courant.id !== f.id){ S.formu.onglet = 'questions'; S.formu.envois = null; }
  S.formu.courant = f;
  S.formu.etat = '';
  setView('formulaire-edit');
}

function formuModifiable(){
  const f = S.formu.courant;
  return formuEstAdmin() && f && f.statut !== 'archive';
}

function formuRenderEdition(){
  const root = document.getElementById('content');
  const f = S.formu.courant;
  if(!root || !f) return;
  const edit = formuModifiable();
  const version = f.version_courante
    ? 'Version publiée : v' + f.version_courante + (f.versions && f.versions[0] ? ' le ' + formuDate(f.versions[0].publie_le) + (f.versions[0].publie_par ? ' par ' + f.versions[0].publie_par : '') : '')
    : 'Jamais publié';
  let boutons = '';
  if(formuEstAdmin()){
    if(f.statut === 'archive') boutons += `<button type="button" class="fsc-btn sm" onclick="formuRestaurer(${f.id})">Restaurer</button>`;
    else {
      boutons += `<button type="button" class="fsc-btn sm" onclick="formuDupliquer(${f.id})">Dupliquer</button>`;
      boutons += f.version_courante
        ? `<button type="button" class="fsc-btn sm" onclick="formuArchiver(${f.id})">Archiver</button>`
        : `<button type="button" class="fsc-btn sm" onclick="formuSupprimer(${f.id})">Supprimer</button>`;
      boutons += `<button type="button" class="fsc-btn sm ia-btn" data-bulle="Utilise l'IA" onclick="formuIaOuvrir('modifier')">Modifier avec l'IA</button>`;
      boutons += `<button type="button" class="fsc-btn sm" id="formu-publier" onclick="formuPublier()">Publier</button>`;
      boutons += `<button type="button" class="fsc-btn sm primary" onclick="formuEnvoiOuvrir(${f.id})"${f.version_courante ? '' : ' disabled title="Publier le formulaire avant de l\'envoyer"'}>Envoyer</button>`;
    }
  }
  const entete = edit
    ? `<div class="formu-entete">
        <input type="text" id="formu-titre" class="formu-titre" maxlength="200" placeholder="Titre du formulaire" value="${escAttr(f.titre)}" oninput="formuSurEntete()">
        <textarea id="formu-desc" rows="2" maxlength="2000" placeholder="Description affichée en tête du formulaire (optionnel)" oninput="formuSurEntete()">${escHtml(f.description || '')}</textarea>
        <div class="formu-version" id="formu-version">${escHtml(version)}</div>
      </div>`
    : `<div class="formu-entete"><div class="formu-version">${escHtml(version)}${f.statut === 'archive' ? ' · archivé, en lecture seule' : ''}</div></div>`;
  const bandeauIaHtml = formuIaNoteHtml(f);
  root.innerHTML = `
    <div class="formu-barre">
      <button type="button" class="fsc-btn sm" onclick="setView('formulaires-list')">← Formulaires</button>
      <span>${formuBadges(f)}</span>
      <span class="formu-etat" id="formu-etat"></span>
      ${boutons}
    </div>
    ${bandeauIaHtml}
    ${entete}
    <div class="formu-onglets">
      <button type="button" class="formu-onglet${S.formu.onglet !== 'suivi' ? ' active' : ''}" onclick="formuSetOnglet('questions')">Questions</button>
      <button type="button" class="formu-onglet${S.formu.onglet === 'suivi' ? ' active' : ''}" onclick="formuSetOnglet('suivi')">Envois et réponses${f.nb_destinataires ? ' (' + (f.nb_reponses || 0) + ' / ' + f.nb_destinataires + ')' : ''}</button>
    </div>
    ${S.formu.onglet === 'suivi' ? '<div id="formu-suivi"><div class="formu-vide">Chargement…</div></div>' : edit
      ? `<div class="formu-grille"><div id="formu-editeur"></div>
           <aside class="formu-apercu"><div class="formu-apercu-lbl">Aperçu destinataire</div><div id="formu-apercu"></div>
           <div class="formu-apercu-note">Se met à jour pendant la saisie. Les réponses tapées ici ne sont pas enregistrées.</div></aside></div>`
      : `<div class="formu-lecture"><div id="formu-apercu"></div></div>`}`;
  if(S.formu.onglet === 'suivi'){
    S.formu.ed = null;
    formuMajEtat();
    formuSuiviCharger();
    return;
  }
  if(edit && window.MysifaFormulaireEditeur){
    S.formu.ed = MysifaFormulaireEditeur.monter(document.getElementById('formu-editeur'), f.schema, {onChange: formuSurChangement});
  } else {
    S.formu.ed = null;
  }
  formuMajEtat();
  formuApercu();
}

// Le schéma de l'éditeur est recopié dans le formulaire avant de quitter
// l'onglet Questions : l'enregistrement automatique le relit.
function formuSetOnglet(o){
  const f = S.formu.courant;
  if(!f) return;
  if(S.formu.ed) f.schema = S.formu.ed.schema();
  S.formu.onglet = o === 'suivi' ? 'suivi' : 'questions';
  formuRenderEdition();
}

let _formuApercuT = null;
function formuApercu(){
  clearTimeout(_formuApercuT);
  _formuApercuT = setTimeout(() => {
    const zone = document.getElementById('formu-apercu');
    const f = S.formu.courant;
    if(!zone || !f || !window.MysifaFormulaire) return;
    const titre = (document.getElementById('formu-titre')?.value ?? f.titre) || 'Formulaire sans titre';
    const desc = (document.getElementById('formu-desc')?.value ?? f.description) || '';
    zone.innerHTML = '<div class="formu-apercu-carte"><h2></h2><p class="formu-apercu-desc"></p><div class="formu-apercu-corps"></div></div>';
    zone.querySelector('h2').textContent = titre;
    const p = zone.querySelector('.formu-apercu-desc');
    if(desc) p.textContent = desc; else p.remove();
    MysifaFormulaire.rendre(S.formu.ed ? S.formu.ed.schema() : f.schema, zone.querySelector('.formu-apercu-corps'));
  }, 120);
}

function formuSurEntete(){ formuSurChangement(); }

function formuSurChangement(){
  formuApercu();
  S.formu.etat = 'attente';
  formuMajEtat();
  clearTimeout(S.formu.timer);
  S.formu.timer = setTimeout(formuEnregistrer, 2000);
}

function formuMajEtat(){
  const el = document.getElementById('formu-etat');
  if(!el) return;
  const e = S.formu.etat;
  el.classList.toggle('erreur', e === 'erreur');
  el.textContent = e === 'attente' ? 'Modifications en attente…'
    : e === 'envoi' ? 'Enregistrement…'
    : e === 'ok' ? 'Enregistré.'
    : e === 'erreur' ? 'Échec de l\'enregistrement — nouvel essai à la prochaine modification.'
    : '';
}

async function formuEnregistrer(){
  clearTimeout(S.formu.timer); S.formu.timer = null;
  const f = S.formu.courant;
  if(!f || S.formu.etat !== 'attente' || !formuModifiable()) return;
  if(S.formu.enCours) await S.formu.enCours;
  const corps = {
    titre: document.getElementById('formu-titre')?.value ?? f.titre,
    description: document.getElementById('formu-desc')?.value ?? f.description,
    schema: S.formu.ed ? S.formu.ed.schema() : f.schema,
  };
  S.formu.etat = 'envoi'; formuMajEtat();
  S.formu.enCours = (async () => {
    try{
      const r = await api('/api/qualite/formulaires/' + f.id, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(corps)});
      if(!r.ok){ S.formu.etat = 'erreur'; showToast(await formuErreur(r, 'Enregistrement impossible.'),'danger'); return; }
      const d = await r.json();
      // On garde le schéma de l'éditeur (la frappe a pu continuer) ; seules
      // les métadonnées du serveur sont reprises.
      if(S.formu.courant && S.formu.courant.id === d.id){
        Object.assign(S.formu.courant, {titre: d.titre, description: d.description, a_publier: d.a_publier,
          modifie_le: d.modifie_le, modifie_par: d.modifie_par, nb_questions: d.nb_questions});
      }
      if(S.formu.etat === 'envoi') S.formu.etat = 'ok';
      S.formu.liste = null;
    }catch(e){ S.formu.etat = 'erreur'; }
    finally{ S.formu.enCours = null; formuMajEtat(); }
  })();
  await S.formu.enCours;
}

async function formuEnregistrerMaintenant(){
  if(S.formu.etat === 'attente') await formuEnregistrer();
  else if(S.formu.enCours) await S.formu.enCours;
}

// Appelé par setView avant de quitter l'éditeur.
function formuQuitter(){
  if(S.formu.etat === 'attente') formuEnregistrer();
}
window.addEventListener('beforeunload', (ev) => {
  if(S.formu && (S.formu.etat === 'attente' || S.formu.etat === 'envoi')){ formuEnregistrer(); ev.preventDefault(); ev.returnValue = ''; }
});

async function formuPublier(){
  const f = S.formu.courant;
  if(!f) return;
  await formuEnregistrerMaintenant();
  if(S.formu.etat === 'erreur'){ showToast('Enregistrer d\'abord le formulaire.','danger'); return; }
  const btn = document.getElementById('formu-publier');
  if(btn) btn.disabled = true;
  const d = await formuAction(f.id, '/publier', null);
  if(btn) btn.disabled = false;
  if(d){
    showToast('Version ' + d.version_courante + ' publiée.','success');
    S.formu.liste = null;
    S.formu.courant = d;
    formuRenderEdition();
  }
}


// ── Assistant IA ───────────────────────────────────────────────────────

const FORMU_IA_EXEMPLES = {
  nouveau: [
    "Enquête de satisfaction client : qualité, délais, service, une note de 1 à 5 par thème et un commentaire libre",
    "Autoévaluation fournisseur : certifications (FSC, ISO), traçabilité des lots, engagements environnementaux",
    "Contrôle produits finis : centrage étiquette, poids de l'étiquette en début, milieu et fin de production",
  ],
  modifier: [
    "Ajoute une section « Sécurité » avec trois questions oui / non",
    "Rends obligatoires toutes les questions de la première section",
    "Pour chaque question oui / non, la réponse « Non » est une non-conformité",
  ],
};

function formuIaNoteHtml(f){
  const n = S.formu.iaNote;
  if(!n || !f || n.id !== f.id) return '';
  const rem = (n.remarques || []).length
    ? '<ul>' + n.remarques.map(r => '<li>' + escHtml(r) + '</li>').join('') + '</ul>' : '';
  const annuler = (S.formu.iaAvant && S.formu.iaAvant.id === f.id && formuModifiable())
    ? '<button type="button" class="fsc-btn sm" onclick="formuIaAnnuler()">Annuler la modification</button>' : '';
  return `<div class="formu-ia-note">
    <div class="formu-ia-note-txt"><b>Proposition de l'IA</b> (${escHtml(n.modele || '')}) — à relire avant publication.<br>${escHtml(n.resume || '')}${rem}</div>
    ${annuler}
    <button type="button" class="fsc-btn sm" onclick="formuIaMasquer()">Masquer</button>
  </div>`;
}
function formuIaMasquer(){ S.formu.iaNote = null; S.formu.iaAvant = null; formuRenderEdition(); }

async function formuIaModeles(){
  if(S.formu.iaModeles) return S.formu.iaModeles;
  try{
    const r = await api('/api/qualite/formulaires/ia/modeles');
    if(r.ok) S.formu.iaModeles = await r.json();
  }catch(e){}
  return S.formu.iaModeles || {modeles: [], defaut: ''};
}

async function formuIaOuvrir(mode){
  mode = mode === 'modifier' ? 'modifier' : 'nouveau';
  if(mode === 'modifier' && !(S.view === 'formulaire-edit' && formuModifiable())) return;
  const m = await formuIaModeles();
  const opts = (m.modeles || []).map(x => `<option value="${escAttr(x.id)}"${x.id === m.defaut ? ' selected' : ''}>${escHtml(x.libelle)}</option>`).join('');
  const aide = (m.modeles || []).find(x => x.id === m.defaut);
  const ex = FORMU_IA_EXEMPLES[mode].map((t, i) => `<button type="button" onclick="formuIaExemple('${mode}', ${i})">${escHtml(t)}</button>`).join('');
  const titre = mode === 'nouveau' ? "Créer un formulaire avec l'IA" : "Modifier le formulaire avec l'IA";
  const intro = mode === 'nouveau'
    ? "Décrivez le formulaire voulu, ou joignez un formulaire existant (fiche papier photographiée, PDF) à reproduire. Le résultat s'ouvre en brouillon dans l'éditeur."
    : "Décrivez la modification. Les questions que la consigne ne vise pas restent telles quelles ; la modification s'annule en un clic.";
  formuMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg ia-zone" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>${escHtml(titre)} <span class="ia-badge">IA</span></h3></div>
      <div class="modal-bd">
        <p class="ia-texte" style="margin:0 0 6px">Fait appel à l'IA (Claude) : le résultat est à relire avant publication.</p>
        <p style="margin:0 0 4px">${escHtml(intro)}</p>
        <div class="formu-ia-ex">${ex}</div>
        <label class="formu-ia-f"><span>Consigne</span>
          <textarea id="formu-ia-consigne" maxlength="6000" placeholder="Ex. ${escAttr(FORMU_IA_EXEMPLES[mode][0])}"></textarea></label>
        ${mode === 'nouveau' ? `<label class="formu-ia-f"><span>Formulaire existant à reproduire (optionnel)</span>
          <input type="file" id="formu-ia-fichiers" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.gif">
          <span class="formu-ia-aide">PDF ou photo, 5 documents de 15 Mo au plus.</span></label>` : ''}
        <label class="formu-ia-f"><span>Modèle</span>
          <select id="formu-ia-modele" onchange="formuIaAideModele()">${opts}</select>
          <span class="formu-ia-aide" id="formu-ia-modele-aide">${escHtml(aide ? aide.aide : '')}</span></label>
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
        <button type="button" class="btn ia-btn" id="formu-ia-go" onclick="formuIaGenerer('${mode}')">Générer</button>
      </div>
    </div>
  </div>`;
  requestAnimationFrame(() => document.getElementById('formu-ia-consigne')?.focus());
}

function formuMroot(){
  return document.getElementById('mroot') || (function(){
    const d = document.createElement('div'); d.id = 'mroot'; document.body.appendChild(d); return d;
  })();
}

function formuIaExemple(mode, i){
  const t = document.getElementById('formu-ia-consigne');
  if(t){ t.value = FORMU_IA_EXEMPLES[mode][i]; t.focus(); }
}
function formuIaAideModele(){
  const id = document.getElementById('formu-ia-modele')?.value;
  const m = ((S.formu.iaModeles || {}).modeles || []).find(x => x.id === id);
  const el = document.getElementById('formu-ia-modele-aide');
  if(el) el.textContent = m ? m.aide : '';
}

async function formuIaGenerer(mode){
  const consigne = (document.getElementById('formu-ia-consigne')?.value || '').trim();
  const fichiers = Array.from(document.getElementById('formu-ia-fichiers')?.files || []);
  if(!consigne && !fichiers.length){ showToast('Décrire le formulaire souhaité ou joindre un document.','danger'); return; }
  if(fichiers.length > 5){ showToast('5 documents au plus.','danger'); return; }
  const trop = fichiers.find(f => f.size > 15 * 1024 * 1024);
  if(trop){ showToast('« ' + trop.name + ' » dépasse 15 Mo.','danger'); return; }
  const fd = new FormData();
  fd.append('consigne', consigne);
  fd.append('modele', document.getElementById('formu-ia-modele')?.value || '');
  fichiers.forEach(f => fd.append('fichiers', f));
  const f = S.formu.courant;
  if(mode === 'modifier' && f){
    fd.append('etat', JSON.stringify({
      titre: document.getElementById('formu-titre')?.value ?? f.titre,
      description: document.getElementById('formu-desc')?.value ?? f.description,
      schema: S.formu.ed ? S.formu.ed.schema() : f.schema,
    }));
  }
  const go = document.getElementById('formu-ia-go');
  if(go){ go.disabled = true; go.textContent = "Claude prépare le formulaire…"; go.classList.add('ia-travail'); }
  let p = null;
  try{
    const r = await api('/api/qualite/formulaires/ia/proposer', {method:'POST', body: fd});
    if(!r.ok){ showToast(await formuErreur(r, 'Génération impossible.'),'danger'); }
    else p = await r.json();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
  if(!p){ if(go){ go.disabled = false; go.textContent = 'Générer'; go.classList.remove('ia-travail'); } return; }
  closeMroot();
  const note = {resume: p.resume, remarques: p.remarques, modele: p.modele_libelle || p.modele};
  if(mode === 'nouveau'){
    try{
      const r = await api('/api/qualite/formulaires', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({titre: p.titre, description: p.description, schema: p.schema})});
      if(!r.ok){ showToast(await formuErreur(r, 'Création impossible.'),'danger'); return; }
      const nf = await r.json();
      S.formu.liste = null;
      S.formu.iaNote = Object.assign({id: nf.id}, note);
      S.formu.iaAvant = null;
      showToast('Brouillon créé — à relire.','success');
      await formuOuvrir(nf.id, nf);
    }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
    return;
  }
  // Modification : l'éditeur reprend la proposition, l'état précédent est
  // gardé pour « Annuler la modification ».
  if(!f) return;
  S.formu.iaAvant = {id: f.id,
    titre: document.getElementById('formu-titre')?.value ?? f.titre,
    description: document.getElementById('formu-desc')?.value ?? f.description,
    schema: S.formu.ed ? S.formu.ed.schema() : f.schema};
  S.formu.iaNote = Object.assign({id: f.id}, note);
  formuIaAppliquer({titre: p.titre, description: p.description, schema: p.schema});
  showToast('Modification appliquée — à relire.','success');
}

function formuIaAppliquer(etat){
  const f = S.formu.courant;
  if(!f) return;
  f.titre = etat.titre; f.description = etat.description; f.schema = etat.schema;
  formuRenderEdition();
  formuSurChangement();
}

function formuIaAnnuler(){
  const a = S.formu.iaAvant;
  if(!a || !S.formu.courant || a.id !== S.formu.courant.id) return;
  S.formu.iaAvant = null;
  S.formu.iaNote = null;
  formuIaAppliquer(a);
  showToast('Modification annulée.','success');
}


// ── Envois et réponses ─────────────────────────────────────────────────

async function formuSuiviCharger(){
  const f = S.formu.courant;
  if(!f) return;
  try{
    const r = await api('/api/qualite/formulaires/' + f.id + '/envois');
    if(!r.ok){ showToast(await formuErreur(r, 'Chargement des envois impossible.'),'danger'); return; }
    S.formu.envois = (await r.json()).envois || [];
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); return; }
  formuSuiviRender();
}

function formuSuiviRender(){
  const box = document.getElementById('formu-suivi');
  const f = S.formu.courant;
  if(!box || !f) return;
  const envois = S.formu.envois || [];
  const admin = formuEstAdmin() && f.statut !== 'archive';
  if(!envois.length){
    box.innerHTML = '<div class="formu-vide">' + (f.version_courante
      ? 'Pas encore envoyé.' + (admin ? ' Le bouton « Envoyer » choisit les destinataires : fournisseurs, clients, personnel ou adresse libre.' : '')
      : 'Publier le formulaire, puis l\'envoyer.') + '</div>';
    return;
  }
  const nbRep = envois.reduce((n, e) => n + (e.nb_repondus || 0), 0);
  const exportHtml = `<div class="formu-export">
      <span class="formu-export-lbl">${nbRep} réponse${nbRep > 1 ? 's' : ''} au total</span>
      <button type="button" class="fsc-btn sm" onclick="formuExporter('csv')"${nbRep ? '' : ' disabled'} title="Une ligne par destinataire, une colonne par question — s'ouvre dans Excel">Exporter en CSV</button>
      <button type="button" class="fsc-btn sm" onclick="formuExporter('csv', null, true)" title="Ajoute les destinataires qui n'ont pas répondu">CSV avec les sans réponse</button>
      <button type="button" class="fsc-btn sm" onclick="formuExporter('pdf')"${nbRep ? '' : ' disabled'} title="Synthèse par question, puis chaque réponse">Exporter en PDF</button>
    </div>`;
  box.innerHTML = exportHtml + envois.map(e => {
    const meta = ['v' + e.version, 'par ' + (e.cree_par || '—'), e.echeance ? 'réponse attendue avant le ' + formuDate(e.echeance) : '',
                  e.nb_repondus + ' / ' + e.nb + ' réponse' + (e.nb_repondus > 1 ? 's' : ''), e.nb_ouverts + ' ouvert' + (e.nb_ouverts > 1 ? 's' : '')]
      .filter(Boolean).join(' · ');
    const enAttente = e.nb - e.nb_repondus;
    const lignes = e.destinataires.map(d => {
      const st = d.actif ? `<span class="formu-badge ${d.statut === 'repondu' ? 'publie' : (d.statut === 'ouvert' ? 'ouvert' : '')}">${escHtml(FORMU_STATUTS_DEST[d.statut] || d.statut)}${d.statut === 'repondu' && d.repondu_le ? ' le ' + escHtml(formuDate(d.repondu_le)) : ''}</span>`
                         : '<span class="formu-badge archive">Retiré</span>';
      const nc = d.nb_nc ? `<span class="formu-badge nc">${d.nb_nc} NC</span>` : '';
      let act = '';
      if(d.statut === 'repondu') act += `<button type="button" class="fsc-btn sm" onclick="formuReponseVoir(${d.id})">Voir la réponse</button>`;
      if(admin && d.actif && d.statut !== 'repondu') act += `<button type="button" class="fsc-btn sm" onclick="formuRelancer(${d.id})">Relancer</button>`;
      if(admin && d.actif) act += `<button type="button" class="fsc-btn sm" onclick="formuRetirer(${d.id})">Retirer</button>`;
      const perso = d.type === 'personnel';
      const qui = (perso ? d.nom : d.organisation) || d.nom || d.email;
      const sous = [!perso && d.organisation && d.nom ? d.nom : '', d.email, d.nb_envois > 1 ? (d.nb_envois - 1) + ' relance' + (d.nb_envois > 2 ? 's' : '') : ''].filter(Boolean).join(' · ');
      return `<div class="formu-dest${d.actif ? '' : ' retire'}">
        <div class="formu-dest-qui"><b>${escHtml(qui)}</b><span>${escHtml(sous)}</span></div>
        ${st} ${nc}
        <div class="formu-dest-actions">${act}</div>
      </div>`;
    }).join('');
    return `<div class="formu-envoi">
      <div class="formu-envoi-hd"><b>Envoi du ${escHtml(formuDate(e.cree_le))}</b><span class="formu-envoi-meta">${escHtml(meta)}</span>
        ${e.nb_repondus ? `<button type="button" class="fsc-btn sm" onclick="formuExporter('csv', ${e.id})">CSV</button><button type="button" class="fsc-btn sm" onclick="formuExporter('pdf', ${e.id})">PDF</button>` : ''}
        ${admin && enAttente > 0 ? `<button type="button" class="fsc-btn sm" onclick="formuRelancerEnvoi(${e.id}, ${enAttente})">Relancer (${enAttente} sans réponse)</button>` : ''}
      </div>
      ${lignes}
    </div>`;
  }).join('');
}

async function formuApresEnvoi(){
  const f = S.formu.courant;
  if(!f) return;
  try{
    const r = await api('/api/qualite/formulaires/' + f.id);
    if(r.ok){ const d = await r.json(); f.nb_destinataires = d.nb_destinataires; f.nb_reponses = d.nb_reponses; }
  }catch(e){}
  S.formu.liste = null;
  if(S.formu.onglet === 'suivi') formuRenderEdition(); else formuSetOnglet('suivi');
}

function formuResultatEnvoi(res, quoi){
  if(!res) return;
  const n = (res.envoyes || []).length, ko = res.echecs || [];
  if(ko.length) showToast(n + ' ' + quoi + ', ' + ko.length + ' en échec : ' + ko.slice(0, 3).join(', ') + (ko.length > 3 ? '…' : ''),'danger');
  else showToast(n + ' ' + quoi + '.','success');
}

async function formuRelancer(did){
  formuResultatEnvoi(await formuAction('destinataires/' + did, '/relancer', null, null, true), 'relance envoyée');
  formuSuiviCharger();
}
async function formuRelancerEnvoi(eid, n){
  if(!confirm('Relancer les ' + n + ' destinataire(s) sans réponse ?')) return;
  formuResultatEnvoi(await formuAction('envois/' + eid, '/relancer', null, null, true), 'relance(s) envoyée(s)');
  formuSuiviCharger();
}
async function formuRetirer(did){
  if(!confirm('Retirer ce destinataire ? Le formulaire disparaît de son espace ; sa réponse éventuelle reste consultable ici.')) return;
  if(await formuAction('destinataires/' + did, '/retirer', 'Destinataire retiré.', null, true)) formuApresEnvoi();
}

// ── Fenêtre d'envoi ────────────────────────────────────────────────────

async function formuEnvoiOuvrir(fid){
  const f = S.formu.courant;
  if(!f || f.id !== fid || !formuEstAdmin()) return;
  if(!f.version_courante){ showToast('Publier le formulaire avant de l\'envoyer.','danger'); return; }
  await formuEnregistrerMaintenant();
  S.formu.envoiSel = new Map();
  S.formu.envoiQ = '';
  const avert = f.a_publier
    ? `<p class="formu-ia-aide" style="color:var(--warn);font-size:12px;margin:0 0 10px">Des modifications ne sont pas publiées : c'est la version v${f.version_courante} qui sera envoyée. Publier d'abord pour les inclure.</p>` : '';
  formuMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>Envoyer « ${escHtml(f.titre)} »</h3></div>
      <div class="modal-bd">
        ${avert}
        <p style="margin:0 0 10px">Chaque destinataire reçoit un email avec le lien de son espace ${escHtml(FORMU_ORG)}, où il retrouve ce formulaire et toutes les autres demandes qui lui sont adressées. Le personnel reçoit aussi une tâche dans MySifa.</p>
        <div class="formu-env-types" id="formu-env-types"></div>
        <div id="formu-env-zone"></div>
        <div class="formu-env-sel" id="formu-env-sel"></div>
        <div class="formu-env-2">
          <label class="formu-ia-f"><span>Message (optionnel)</span><textarea id="formu-env-message" maxlength="2000" style="min-height:70px" placeholder="Affiché en tête du formulaire et dans l'email."></textarea></label>
          <label class="formu-ia-f"><span>Réponse attendue avant le</span><input type="date" id="formu-env-echeance" style="width:100%;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 11px;color:var(--text);font-family:inherit"></label>
        </div>
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
        <button type="button" class="btn btn-accent" id="formu-env-go" onclick="formuEnvoiValider()" disabled>Envoyer</button>
      </div>
    </div>
  </div>`;
  formuEnvoiType(S.formu.envoiType || 'fournisseur');
}

function formuEnvoiType(t){
  S.formu.envoiType = FORMU_TYPES_DEST.some(x => x.v === t) ? t : 'fournisseur';
  const types = document.getElementById('formu-env-types');
  if(types) types.innerHTML = FORMU_TYPES_DEST.map(x => `<button type="button" class="formu-pill${S.formu.envoiType === x.v ? ' active' : ''}" onclick="formuEnvoiType('${x.v}')">${escHtml(x.l)}</button>`).join('');
  const zone = document.getElementById('formu-env-zone');
  if(!zone) return;
  if(S.formu.envoiType === 'libre'){
    zone.innerHTML = `<label class="formu-ia-f"><span>Adresses email (une par ligne, ou séparées par des virgules)</span>
      <textarea id="formu-env-libres" style="min-height:90px" placeholder="prenom.nom@exemple.com"></textarea></label>
      <button type="button" class="fsc-btn sm" onclick="formuEnvoiAjouterLibres()">Ajouter à la sélection</button>`;
    requestAnimationFrame(() => document.getElementById('formu-env-libres')?.focus());
  } else {
    zone.innerHTML = `<input type="search" id="formu-env-q" class="formu-search" style="max-width:none;width:100%;margin:0 0 8px" placeholder="Rechercher (nom, contact, email)" value="${escAttr(S.formu.envoiQ)}" oninput="formuEnvoiChercher(this.value)" onkeydown="if(event.key==='Escape'){this.value='';formuEnvoiChercher('');}">
      <div class="formu-env-liste" id="formu-env-liste"><div class="formu-vide" style="border:none">Chargement…</div></div>`;
    requestAnimationFrame(() => document.getElementById('formu-env-q')?.focus());
    formuEnvoiCharger();
  }
  formuEnvoiMajSel();
}

let _formuEnvT = null;
function formuEnvoiChercher(q){
  S.formu.envoiQ = q;
  clearTimeout(_formuEnvT);
  _formuEnvT = setTimeout(formuEnvoiCharger, 200);
}

async function formuEnvoiCharger(){
  const t = S.formu.envoiType, q = S.formu.envoiQ || '';
  try{
    const r = await api('/api/qualite/formulaires/destinataires?type=' + encodeURIComponent(t) + '&q=' + encodeURIComponent(q));
    if(!r.ok){ showToast(await formuErreur(r, 'Chargement des destinataires impossible.'),'danger'); return; }
    if(t !== S.formu.envoiType || q !== (S.formu.envoiQ || '')) return;
    S.formu.envoiCandidats = (await r.json()).destinataires || [];
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); return; }
  formuEnvoiListe();
}

function formuEnvoiListe(){
  const box = document.getElementById('formu-env-liste');
  if(!box) return;
  const c = S.formu.envoiCandidats || [];
  if(!c.length){
    const q = (S.formu.envoiQ || '').trim();
    box.innerHTML = '<div class="formu-vide" style="border:none">' + (q ? 'Aucun résultat pour « ' + escHtml(q) + ' ».' : 'Aucun contact avec une adresse email.') + '</div>';
    return;
  }
  box.innerHTML = c.map((d, i) => `<label class="formu-env-ligne">
      <input type="checkbox" ${S.formu.envoiSel.has(d.email) ? 'checked' : ''} onchange="formuEnvoiCocher(${i}, this.checked)">
      <span><b>${escHtml(d.organisation || d.nom || d.email)}</b><small>${escHtml([d.organisation && d.nom ? d.nom : '', d.email].filter(Boolean).join(' · '))}</small></span>
    </label>`).join('');
}

function formuEnvoiCocher(i, on){
  const d = (S.formu.envoiCandidats || [])[i];
  if(!d) return;
  if(on) S.formu.envoiSel.set(d.email, d); else S.formu.envoiSel.delete(d.email);
  formuEnvoiMajSel();
}

function formuEnvoiAjouterLibres(){
  const t = document.getElementById('formu-env-libres');
  if(!t) return;
  const ok = [], ko = [];
  t.value.split(/[\s,;]+/).map(x => x.trim()).filter(Boolean).forEach(e => {
    if(/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e)){ const m = e.toLowerCase(); ok.push(m); if(!S.formu.envoiSel.has(m)) S.formu.envoiSel.set(m, {type:'libre', email:m, nom:'', organisation:''}); }
    else ko.push(e);
  });
  t.value = ko.join('\n');
  if(ko.length) showToast(ko.length + ' adresse(s) invalide(s) laissée(s) dans le champ.','danger');
  else if(ok.length) showToast(ok.length + ' adresse(s) ajoutée(s).','success');
  formuEnvoiMajSel();
}

function formuEnvoiRetirerSel(email){
  S.formu.envoiSel.delete(email);
  formuEnvoiMajSel();
  formuEnvoiListe();
}

function formuEnvoiMajSel(){
  const box = document.getElementById('formu-env-sel');
  const go = document.getElementById('formu-env-go');
  const sel = Array.from(S.formu.envoiSel.values());
  if(box) box.innerHTML = sel.length
    ? sel.map(d => `<span class="formu-env-chip" title="${escAttr(d.email)}"><span>${escHtml(d.organisation || d.nom || d.email)}</span><button type="button" aria-label="Retirer" onclick='formuEnvoiRetirerSel(${JSON.stringify(d.email).replace(/'/g, '&#39;')})'>×</button></span>`).join('')
    : '<span class="formu-ia-aide">Aucun destinataire sélectionné.</span>';
  if(go){ go.disabled = !sel.length; go.textContent = sel.length ? 'Envoyer à ' + sel.length + ' destinataire' + (sel.length > 1 ? 's' : '') : 'Envoyer'; }
}

async function formuEnvoiValider(){
  const f = S.formu.courant;
  const sel = Array.from(S.formu.envoiSel.values());
  if(!f || !sel.length) return;
  const go = document.getElementById('formu-env-go');
  if(go){ go.disabled = true; go.textContent = 'Envoi en cours…'; }
  const res = await formuAction(f.id, '/envois', null, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({destinataires: sel, message: document.getElementById('formu-env-message')?.value || '',
                          echeance: document.getElementById('formu-env-echeance')?.value || ''})});
  if(!res){ formuEnvoiMajSel(); return; }
  closeMroot();
  formuResultatEnvoi(res, 'email(s) envoyé(s)');
  formuApresEnvoi();
}

// ── Exports ────────────────────────────────────────────────────────────

function formuExporter(format, envoiId, avecSansReponse){
  const f = S.formu.courant;
  if(!f) return;
  const p = new URLSearchParams();
  if(envoiId) p.set('envoi', envoiId);
  if(avecSansReponse) p.set('tous', '1');
  const q = p.toString();
  formuTelecharger('/api/qualite/formulaires/' + f.id + '/reponses.' + (format === 'pdf' ? 'pdf' : 'csv') + (q ? '?' + q : ''));
}

// Téléchargement par fetch : une erreur du serveur (aucune réponse…) s'affiche
// en toast au lieu d'ouvrir une page JSON.
async function formuTelecharger(url){
  try{
    const r = await api(url);
    if(!r.ok){ showToast(await formuErreur(r, 'Export impossible.'),'danger'); return; }
    const dispo = r.headers.get('Content-Disposition') || '';
    const m = dispo.match(/filename="([^"]+)"/);
    const blob = await r.blob();
    const lien = document.createElement('a');
    lien.href = URL.createObjectURL(blob);
    lien.download = m ? m[1] : 'export';
    document.body.appendChild(lien);
    lien.click();
    setTimeout(() => { URL.revokeObjectURL(lien.href); lien.remove(); }, 1000);
    showToast('Export téléchargé.','success');
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

// ── Consultation d'une réponse ─────────────────────────────────────────

async function formuReponseVoir(did){
  let d;
  try{
    const r = await api('/api/qualite/formulaires/destinataires/' + did + '/reponse');
    if(!r.ok){ showToast(await formuErreur(r, 'Réponse introuvable.'),'danger'); return; }
    d = await r.json();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); return; }
  const dest = d.destinataire, rep = d.reponse;
  const qui = (dest.type === 'personnel' ? dest.nom : dest.organisation) || dest.nom || dest.email;
  const meta = ['Réponse du ' + formuDate(rep.soumis_le) + ' à ' + String(rep.soumis_le || '').slice(11, 16),
                rep.repondant_nom ? 'par ' + rep.repondant_nom : '', dest.email, 'version v' + d.version,
                rep.nb_versions > 1 ? 'modifiée ' + (rep.nb_versions - 1) + ' fois' : ''].filter(Boolean).join(' · ');
  formuMroot().innerHTML = `
  <div class="modal-ov" style="display:flex" onclick="if(event.target===this)closeMroot()">
    <div class="modal lg" onclick="event.stopPropagation()">
      <button type="button" class="modal-close" onclick="closeMroot()">×</button>
      <div class="modal-hd"><h3>${escHtml(qui)} — ${escHtml(d.titre)}</h3></div>
      <div class="modal-bd">
        <p class="formu-ia-aide" style="font-size:12px;margin:0 0 6px">${escHtml(meta)}</p>
        ${d.nc.length ? `<p style="margin:0 0 12px;color:var(--danger);font-weight:600;font-size:13px">${d.nc.length} réponse${d.nc.length > 1 ? 's' : ''} non conforme${d.nc.length > 1 ? 's' : ''}.</p>` : ''}
        <div id="formu-reponse-corps"></div>
      </div>
      <div class="modal-ft">
        <button type="button" class="fsc-btn" onclick="formuTelecharger('/api/qualite/formulaires/destinataires/${Number(did)}/reponse.pdf')">Télécharger le PDF</button>
        <button type="button" class="fsc-btn" onclick="closeMroot()">Fermer</button>
      </div>
    </div>
  </div>`;
  MysifaFormulaire.rendre(d.schema, document.getElementById('formu-reponse-corps'), {valeurs: rep.reponses, lectureSeule: true, nc: d.nc});
}

// ── Guide in-app « formulaires » (branché dans _qualiteGuides) ──────────

QUALITE_TASKS_MODULES.formulaires = {
  direction: {
    label: "Direction",
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 12l4-4 4 4 6-6"/></svg>`,
    tasks: [
      "Valider le contenu des questionnaires avant publication",
      "Décider à qui chaque formulaire est envoyé (fournisseurs, personnel, clients)",
    ]
  },
  administration: {
    label: "Administration",
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
    tasks: [
      "Créer un formulaire : sections, questions, réponses non conformes",
      "Vérifier le rendu dans l'aperçu destinataire",
      "Publier une version, puis l'archiver quand elle n'est plus utilisée",
    ]
  },
  commercial: {
    label: "Commercial",
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
    tasks: [
      "Consulter les formulaires publiés avant de les proposer à un client",
    ]
  },
};

const FORMU_MOCKUPS = {
  liste: `<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg">
    <rect x="8" y="8" width="56" height="16" rx="8" fill="var(--accent-bg)" stroke="var(--accent)"/>
    <text x="36" y="19" font-size="8" text-anchor="middle" fill="var(--accent)" font-weight="700">En cours 4</text>
    <rect x="70" y="8" width="56" height="16" rx="8" fill="var(--card)" stroke="var(--border)"/>
    <text x="98" y="19" font-size="8" text-anchor="middle" fill="var(--text2)">Brouillons 1</text>
    <rect x="132" y="8" width="50" height="16" rx="8" fill="var(--card)" stroke="var(--border)"/>
    <text x="157" y="19" font-size="8" text-anchor="middle" fill="var(--text2)">Publiés 3</text>
    <rect x="8" y="34" width="324" height="32" rx="7" fill="var(--card)" stroke="var(--border)"/>
    <text x="18" y="48" font-size="9" fill="var(--text)" font-weight="700">Enquête satisfaction client</text>
    <text x="18" y="59" font-size="7" fill="var(--muted)">12 questions · modifié le 20/10</text>
    <rect x="236" y="43" width="60" height="14" rx="7" fill="none" stroke="var(--ok)"/>
    <text x="266" y="53" font-size="7" text-anchor="middle" fill="var(--ok)" font-weight="700">Publié · v2</text>
    <rect x="8" y="72" width="324" height="32" rx="7" fill="var(--card)" stroke="var(--border)"/>
    <text x="18" y="86" font-size="9" fill="var(--text)" font-weight="700">Autoévaluation fournisseur</text>
    <text x="18" y="97" font-size="7" fill="var(--muted)">8 questions · modifié le 18/10</text>
    <rect x="252" y="81" width="44" height="14" rx="7" fill="var(--bg)" stroke="var(--border)"/>
    <text x="274" y="91" font-size="7" text-anchor="middle" fill="var(--text2)" font-weight="700">Brouillon</text>
    <rect x="236" y="116" width="96" height="22" rx="7" fill="var(--accent-bg)" stroke="var(--accent)"/>
    <text x="284" y="130" font-size="8" text-anchor="middle" fill="var(--accent)" font-weight="700">+ Nouveau formulaire</text>
  </svg>`,
  editeur: `<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg">
    <rect x="8" y="6" width="324" height="138" rx="9" fill="var(--card)" stroke="var(--border)"/>
    <text x="18" y="20" font-size="7" fill="var(--accent)" font-weight="700">SECTION 1 / 2</text>
    <rect x="18" y="26" width="304" height="58" rx="7" fill="var(--bg)" stroke="var(--border)"/>
    <circle cx="27" cy="38" r="1.3" fill="var(--muted)"/><circle cx="31" cy="38" r="1.3" fill="var(--muted)"/>
    <circle cx="27" cy="43" r="1.3" fill="var(--muted)"/><circle cx="31" cy="43" r="1.3" fill="var(--muted)"/>
    <rect x="38" y="32" width="150" height="16" rx="5" fill="var(--card)" stroke="var(--border)"/>
    <text x="44" y="43" font-size="8" fill="var(--text)" font-weight="600">Poids de l'étiquette</text>
    <rect x="194" y="32" width="52" height="16" rx="5" fill="var(--card)" stroke="var(--border)"/>
    <text x="200" y="43" font-size="8" fill="var(--text2)">Nombre</text>
    <rect x="252" y="32" width="16" height="16" rx="4" fill="var(--card)" stroke="var(--border)"/>
    <rect x="272" y="32" width="16" height="16" rx="4" fill="var(--card)" stroke="var(--border)"/>
    <rect x="292" y="32" width="16" height="16" rx="4" fill="var(--card)" stroke="var(--border)"/>
    <text x="38" y="62" font-size="6.5" fill="var(--muted)">UNITÉ      MIN       CIBLE      MAX</text>
    <rect x="38" y="65" width="60" height="12" rx="4" fill="var(--card)" stroke="var(--border)"/>
    <rect x="102" y="65" width="60" height="12" rx="4" fill="var(--card)" stroke="var(--border)"/>
    <rect x="166" y="65" width="60" height="12" rx="4" fill="var(--card)" stroke="var(--accent)"/>
    <rect x="230" y="65" width="60" height="12" rx="4" fill="var(--card)" stroke="var(--border)"/>
    <text x="18" y="100" font-size="7" fill="var(--muted)">Ajouter :</text>
    <rect x="50" y="92" width="34" height="13" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="67" y="101" font-size="6.5" text-anchor="middle" fill="var(--text2)">Texte</text>
    <rect x="88" y="92" width="38" height="13" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="107" y="101" font-size="6.5" text-anchor="middle" fill="var(--text2)">Nombre</text>
    <rect x="130" y="92" width="34" height="13" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="147" y="101" font-size="6.5" text-anchor="middle" fill="var(--text2)">Choix</text>
    <rect x="168" y="92" width="44" height="13" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="190" y="101" font-size="6.5" text-anchor="middle" fill="var(--text2)">Oui / Non</text>
    <rect x="216" y="92" width="30" height="13" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="231" y="101" font-size="6.5" text-anchor="middle" fill="var(--text2)">Date</text>
    <rect x="250" y="92" width="30" height="13" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="265" y="101" font-size="6.5" text-anchor="middle" fill="var(--text2)">Note</text>
    <rect x="18" y="116" width="100" height="16" rx="5" fill="var(--bg)" stroke="var(--border)"/>
    <text x="68" y="127" font-size="7" text-anchor="middle" fill="var(--text2)">+ Ajouter une section</text>
  </svg>`,
  apercu: `<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg">
    <rect x="8" y="6" width="190" height="138" rx="9" fill="var(--card)" stroke="var(--border)"/>
    <rect x="18" y="16" width="170" height="10" rx="3" fill="var(--bg)"/>
    <rect x="18" y="32" width="170" height="10" rx="3" fill="var(--bg)"/>
    <rect x="18" y="48" width="170" height="30" rx="5" fill="var(--bg)" stroke="var(--accent)"/>
    <rect x="18" y="84" width="120" height="10" rx="3" fill="var(--bg)"/>
    <rect x="18" y="100" width="170" height="10" rx="3" fill="var(--bg)"/>
    <rect x="206" y="6" width="126" height="138" rx="9" fill="var(--bg)" stroke="var(--border)"/>
    <text x="214" y="19" font-size="6.5" fill="var(--text2)" font-weight="700">APERÇU DESTINATAIRE</text>
    <rect x="212" y="25" width="114" height="112" rx="7" fill="var(--card)" stroke="var(--border)"/>
    <text x="218" y="38" font-size="8" fill="var(--text)" font-weight="700">Poids de l'étiquette *</text>
    <text x="218" y="52" font-size="6.5" fill="var(--text2)">Début</text>
    <rect x="244" y="45" width="46" height="11" rx="3" fill="var(--card)" stroke="var(--border)"/>
    <text x="296" y="53" font-size="6" fill="var(--muted)">écart +0,05</text>
    <text x="218" y="67" font-size="6.5" fill="var(--text2)">Fin</text>
    <rect x="244" y="60" width="46" height="11" rx="3" fill="var(--card)" stroke="var(--danger)"/>
    <text x="296" y="68" font-size="6" fill="var(--danger)">écart +0,4</text>
    <text x="218" y="84" font-size="8" fill="var(--text)" font-weight="700">Centrage</text>
    <rect x="218" y="89" width="34" height="12" rx="6" fill="var(--accent)"/>
    <text x="235" y="98" font-size="6.5" text-anchor="middle" fill="white">Conforme</text>
    <rect x="256" y="89" width="36" height="12" rx="6" fill="var(--card)" stroke="var(--border)"/>
    <text x="274" y="98" font-size="6.5" text-anchor="middle" fill="var(--text2)">Décentré</text>
  </svg>`,
  publier: `<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg">
    <rect x="8" y="10" width="324" height="26" rx="7" fill="var(--card)" stroke="var(--border)"/>
    <rect x="16" y="16" width="64" height="14" rx="5" fill="var(--bg)" stroke="var(--border)"/>
    <text x="48" y="26" font-size="7" text-anchor="middle" fill="var(--text2)">← Formulaires</text>
    <rect x="86" y="16" width="56" height="14" rx="7" fill="none" stroke="var(--ok)"/>
    <text x="114" y="26" font-size="7" text-anchor="middle" fill="var(--ok)" font-weight="700">Publié · v2</text>
    <rect x="146" y="16" width="96" height="14" rx="7" fill="none" stroke="var(--warn)"/>
    <text x="194" y="26" font-size="7" text-anchor="middle" fill="var(--warn)" font-weight="700">Modifications non publiées</text>
    <rect x="282" y="16" width="44" height="14" rx="5" fill="var(--accent-bg)" stroke="var(--accent)"/>
    <text x="304" y="26" font-size="7" text-anchor="middle" fill="var(--accent)" font-weight="700">Publier</text>
    <text x="16" y="56" font-size="7" fill="var(--muted)">Enregistré.</text>
    <rect x="16" y="70" width="90" height="62" rx="7" fill="var(--card)" stroke="var(--border)"/>
    <text x="61" y="88" font-size="9" text-anchor="middle" fill="var(--text)" font-weight="700">v1</text>
    <text x="61" y="102" font-size="7" text-anchor="middle" fill="var(--muted)">figée le 02/10</text>
    <rect x="124" y="70" width="90" height="62" rx="7" fill="var(--card)" stroke="var(--ok)"/>
    <text x="169" y="88" font-size="9" text-anchor="middle" fill="var(--text)" font-weight="700">v2</text>
    <text x="169" y="102" font-size="7" text-anchor="middle" fill="var(--muted)">figée le 20/10</text>
    <rect x="232" y="70" width="90" height="62" rx="7" fill="var(--bg)" stroke="var(--border)" stroke-dasharray="4 3"/>
    <text x="277" y="88" font-size="9" text-anchor="middle" fill="var(--text2)" font-weight="700">Brouillon</text>
    <text x="277" y="102" font-size="7" text-anchor="middle" fill="var(--muted)">en cours d'édition</text>
  </svg>`,
};

function formuGuide(){
  const ico = (d) => `<svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  return {
    steps: [
      {
        icon: ico('<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>'),
        title: "Formulaires",
        body: "Questionnaires à faire remplir aux <strong>fournisseurs</strong>, au <strong>personnel</strong> ou aux <strong>clients</strong> : enquêtes, autoévaluations, contrôles. Les pastilles filtrent les formulaires <span class=\"qguide-tag\">En cours</span>, <span class=\"qguide-tag\">Brouillons</span>, <span class=\"qguide-tag\">Publiés</span> et <span class=\"qguide-tag\">Archivés</span>.",
        illu: FORMU_MOCKUPS.liste,
        extra: _renderTaskSectionsFor('formulaires')
      },
      {
        icon: ico('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>'),
        title: "Sections et questions",
        body: "Six boutons ajoutent une question : <strong>Texte</strong>, <strong>Nombre</strong>, <strong>Choix</strong>, <strong>Oui / Non</strong>, <strong>Date</strong>, <strong>Note</strong>. La poignée ou les flèches réordonnent, l'icône copie duplique. Une réponse de choix cochée <strong>NC</strong> signale une non-conformité. L'aperçu à droite montre le formulaire tel que le destinataire le remplira.",
        illu: FORMU_MOCKUPS.editeur
      },
      {
        icon: ico('<path d="M3 3v18h18"/><path d="M7 15l3-3 3 3 5-6"/>'),
        title: "Mesures, tolérance et cible",
        body: "Une question <strong>Nombre</strong> prend une unité, un min, une cible et un max. L'écart à la cible s'affiche à côté de la mesure. <strong>Plusieurs valeurs</strong> demande une mesure par libellé (début, milieu, fin de production). Une valeur hors tolérance peut compter comme NC.",
        illu: FORMU_MOCKUPS.apercu
      },
      {
        icon: ico('<path d="M12 3l1.9 5.8H20l-4.9 3.6 1.9 5.8L12 14.6l-4.9 3.6 1.9-5.8L4 8.8h6.1z"/>'),
        title: "Créer ou modifier avec l'IA",
        body: "<strong>Créer avec l'IA</strong> part d'une consigne ou d'un formulaire existant (fiche papier photographiée, PDF) et ouvre un brouillon. <strong>Modifier avec l'IA</strong> retouche le formulaire ouvert ; <strong>Annuler la modification</strong> le remet en l'état. Les remarques de l'IA disent ce qu'il reste à vérifier."
      },
      {
        icon: ico('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>'),
        title: "Envoyer et suivre les réponses",
        body: "<strong>Envoyer</strong> choisit les destinataires : fournisseurs, clients (contacts de l'ERP), personnel ou adresse libre. Chacun reçoit le lien de son <strong>espace " + escHtml(FORMU_ORG) + "</strong>, où il retrouve tout ce que " + escHtml(FORMU_ORG) + " lui adresse. L'onglet <strong>Envois et réponses</strong> suit qui a ouvert et répondu, relance et affiche chaque réponse, non-conformités en rouge. Les réponses s'exportent en CSV (Excel) ou en PDF avec une synthèse par question."
      },
      {
        icon: ico('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'),
        title: "Enregistrement et publication",
        body: "L'édition est enregistrée automatiquement deux secondes après la dernière frappe. <strong>Publier</strong> fige une version numérotée : c'est elle qui sera envoyée. Le badge <span class=\"qguide-tag\">Modifications non publiées</span> rappelle qu'un brouillon attend. Un formulaire publié s'archive ; seul un brouillon jamais publié se supprime.",
        illu: FORMU_MOCKUPS.publier
      },
    ]
  };
}
"""
