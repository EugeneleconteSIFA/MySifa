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
};

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
      ${admin ? `<div class="fsc-hero-actions"><button type="button" class="fsc-btn primary" onclick="formuNouveau()">+ Nouveau formulaire</button></div>` : ''}
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
                  'modifié le ' + formuDate(f.modifie_le) + (f.modifie_par ? ' par ' + f.modifie_par : '')].join(' · ');
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
      boutons += `<button type="button" class="fsc-btn sm primary" id="formu-publier" onclick="formuPublier()">Publier</button>`;
    }
  }
  const entete = edit
    ? `<div class="formu-entete">
        <input type="text" id="formu-titre" class="formu-titre" maxlength="200" placeholder="Titre du formulaire" value="${escAttr(f.titre)}" oninput="formuSurEntete()">
        <textarea id="formu-desc" rows="2" maxlength="2000" placeholder="Description affichée en tête du formulaire (optionnel)" oninput="formuSurEntete()">${escHtml(f.description || '')}</textarea>
        <div class="formu-version" id="formu-version">${escHtml(version)}</div>
      </div>`
    : `<div class="formu-entete"><div class="formu-version">${escHtml(version)}${f.statut === 'archive' ? ' · archivé, en lecture seule' : ''}</div></div>`;
  root.innerHTML = `
    <div class="formu-barre">
      <button type="button" class="fsc-btn sm" onclick="setView('formulaires-list')">← Formulaires</button>
      <span>${formuBadges(f)}</span>
      <span class="formu-etat" id="formu-etat"></span>
      ${boutons}
    </div>
    ${entete}
    ${edit
      ? `<div class="formu-grille"><div id="formu-editeur"></div>
           <aside class="formu-apercu"><div class="formu-apercu-lbl">Aperçu destinataire</div><div id="formu-apercu"></div>
           <div class="formu-apercu-note">Se met à jour pendant la saisie. Les réponses tapées ici ne sont pas enregistrées.</div></aside></div>`
      : `<div class="formu-lecture"><div id="formu-apercu"></div></div>`}`;
  if(edit && window.MysifaFormulaireEditeur){
    S.formu.ed = MysifaFormulaireEditeur.monter(document.getElementById('formu-editeur'), f.schema, {onChange: formuSurChangement});
  } else {
    S.formu.ed = null;
  }
  formuMajEtat();
  formuApercu();
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
  if(!f || !S.formu.ed || S.formu.etat !== 'attente') return;
  if(S.formu.enCours) await S.formu.enCours;
  const corps = {
    titre: document.getElementById('formu-titre')?.value ?? f.titre,
    description: document.getElementById('formu-desc')?.value ?? f.description,
    schema: S.formu.ed.schema(),
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
        body: "Six boutons ajoutent une question : <strong>Texte</strong>, <strong>Nombre</strong>, <strong>Choix</strong>, <strong>Oui / Non</strong>, <strong>Date</strong>, <strong>Note</strong>. La poignée ou les flèches réordonnent, l'icône copie duplique. Une réponse de choix cochée <strong>NC</strong> signale une non-conformité.",
        illu: FORMU_MOCKUPS.editeur
      },
      {
        icon: ico('<path d="M3 3v18h18"/><path d="M7 15l3-3 3 3 5-6"/>'),
        title: "Mesures, tolérance et cible",
        body: "Une question <strong>Nombre</strong> prend une unité, un min, une cible et un max. L'écart à la cible s'affiche à côté de la mesure. <strong>Plusieurs valeurs</strong> demande une mesure par libellé (début, milieu, fin de production). Une valeur hors tolérance peut compter comme NC.",
        illu: FORMU_MOCKUPS.apercu
      },
      {
        icon: ico('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'),
        title: "Aperçu destinataire",
        body: "La colonne de droite montre le formulaire tel que le destinataire le remplira, et suit chaque frappe. On peut y tester les réponses : rien n'est enregistré."
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
