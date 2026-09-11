"""MySifa - Assets de l'onglet FSC (MyQualite > Certifications SIFA > FSC).

Uniquement du JS et du CSS, injectes dans la page /qualite via le placeholder
__FSC_ASSETS__, juste apres ceux de la GED. Meme motif que qualite_ged_assets.py :
qualite_page.py depasse 7 000 lignes, un onglet de plus ne s'y ajoute pas.

L'onglet repond a trois questions de l'audit FSC CoC :
- la liste des fournisseurs certifies (licence, certificat, expiration) et leurs
  certificats reunis dans un seul PDF ;
- la preuve du controle de chaque certificat sur la base publique FSC ;
- les categories FSC (claims) que chaque fournisseur peut livrer, rapprochees de
  ce que SIFA exige sur ses dossiers et de ce qu'elle a reellement recu.

API : app/routers/qualite_fsc.py.
"""

FSC_JS = r"""
// ══════════════════════════════════════════════════════════════════════
// Certifications SIFA - onglet 3 : FSC
// ══════════════════════════════════════════════════════════════════════

S.fsc = {
  data: null,          // reponse de /api/qualite/fsc/synthese
  q: '',               // recherche (fournisseur, licence, certificat)
  filtre: 'tous',      // tous | a_traiter | a_controler | expiration | sans_categorie
  lecture: null,       // {done, total} pendant la lecture des certificats
  ctrl: null,          // controle en cours de saisie {id, historique}
};

const FSC_STATUT_EXP = {
  valide:       {cls:'ok',   label:'Valide'},
  a_renouveler: {cls:'soon', label:'À renouveler'},
  expire:       {cls:'exp',  label:'Expiré'},
  sans_date:    {cls:'nod',  label:'Sans date'},
};

function fscEstAdmin(){ return !!(S.isQualiteAdmin && !S.isQualiteReadonly); }

async function fscEnter(){
  const root = document.getElementById('content');
  if(!root) return;
  if(!S.fsc.data){
    root.innerHTML = `${sifaTabsHtml('fsc')}
      <div class="fsc-hero"><div class="fsc-hero-txt"><h1>FSC</h1><p>Chargement des fournisseurs certifiés…</p></div></div>`;
  }
  await fscLoad();
}

async function fscLoad(){
  try{
    const r = await api('/api/qualite/fsc/synthese');
    if(!r.ok){ showToast('Chargement FSC impossible.','danger'); return; }
    S.fsc.data = await r.json();
    if(gedActiveTab() !== 'fsc') return;
    fscRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

// ─── Filtrage ────────────────────────────────────────────────────────
function fscLignesVisibles(){
  const d = S.fsc.data; if(!d) return [];
  const q = (S.fsc.q||'').trim().toLowerCase();
  return (d.fournisseurs||[]).filter(l => {
    if(q){
      const hay = [l.nom, l.groupe, l.branche, l.licence, l.certificat].join(' ').toLowerCase();
      if(hay.indexOf(q) === -1) return false;
    }
    if(S.fsc.filtre === 'a_traiter') return (l.alertes||[]).length > 0 || !l.dernier_controle || l.dernier_controle.a_refaire || !(l.claims||[]).length;
    if(S.fsc.filtre === 'a_controler') return !l.dernier_controle || l.dernier_controle.a_refaire;
    if(S.fsc.filtre === 'expiration') return l.statut === 'expire' || l.statut === 'a_renouveler' || l.statut === 'sans_date';
    if(S.fsc.filtre === 'sans_categorie') return !(l.claims||[]).length;
    return true;
  });
}

function fscSetFiltre(f){
  S.fsc.filtre = f;
  document.querySelectorAll('.fsc-filtre').forEach(b => b.classList.toggle('active', b.dataset.f === f));
  fscRenderList();
}

function fscOnSearch(v){ S.fsc.q = v; fscRenderList(); }
function fscOnSearchKey(ev){
  if(ev.key === 'Escape'){ ev.target.value = ''; S.fsc.q = ''; fscRenderList(); }
}

// ─── Rendu page ──────────────────────────────────────────────────────
function fscRender(){
  const root = document.getElementById('content');
  const d = S.fsc.data;
  if(!root || !d) return;
  const st = d.stats || {};
  const aLire = (d.documents_a_lire||[]).length;
  const lecture = S.fsc.lecture;

  const kpi = (val, label, cls, filtre) => `
    <button type="button" class="fsc-kpi ${cls||''}" onclick="fscSetFiltre('${filtre}')" title="Filtrer la liste">
      <span class="fsc-kpi-val">${val}</span><span class="fsc-kpi-lbl">${escHtml(label)}</span>
    </button>`;

  const couv = (d.couverture||[]).map(c => {
    const n = (c.fournisseurs_confirmes||[]).length;
    const np = (c.fournisseurs_proposes||[]).length;
    const usage = [c.n_dossiers ? `${c.n_dossiers} dossier${c.n_dossiers>1?'s':''} l'exige${c.n_dossiers>1?'nt':''}` : '',
                   c.n_receptions ? `${c.n_receptions} réception${c.n_receptions>1?'s':''}` : ''].filter(Boolean).join(' · ');
    const cls = n ? 'ok' : (np ? 'soon' : 'exp');
    const detail = n ? (c.fournisseurs_confirmes||[]).join(', ')
                     : (np ? 'Lu sur le certificat de : ' + (c.fournisseurs_proposes||[]).join(', ') + ' — à confirmer au contrôle'
                           : 'Aucun fournisseur confirmé pour cette catégorie');
    return `<div class="fsc-couv-card ${cls}">
      <div class="fsc-couv-hd"><span class="fsc-claim solid">${escHtml(c.label)}</span><span class="fsc-couv-usage">${escHtml(usage)}</span></div>
      <div class="fsc-couv-n"><b>${n}</b> fournisseur${n>1?'s':''} confirmé${n>1?'s':''}${np?` <span class="fsc-muted">· ${np} à confirmer</span>`:''}</div>
      <div class="fsc-couv-detail">${escHtml(detail)}</div>
    </div>`;
  }).join('');

  root.innerHTML = `
    ${sifaTabsHtml('fsc')}
    <div class="fsc-hero">
      <div class="fsc-hero-txt">
        <h1>FSC</h1>
        <p>Fournisseurs certifiés, leurs certificats et les catégories FSC qu'ils peuvent livrer.
        Chaque contrôle sur la base FSC est conservé avec sa date et son justificatif.${d.licence_sifa?` Licence SIFA : <span class="fsc-mono">${escHtml(d.licence_sifa)}</span>.`:''}</p>
      </div>
      <div class="fsc-hero-actions">
        ${aLire ? `<button type="button" class="fsc-btn qual-write" id="fsc-btn-lire" onclick="fscLireTout()" ${lecture?'disabled':''}
            title="Lit la licence, l'expiration et les catégories écrites sur chaque certificat. Rien n'est validé sans contrôle.">
            ${lecture ? `Lecture ${lecture.done}/${lecture.total}…` : `Lire les certificats (${aLire})`}
          </button>` : ''}
        <button type="button" class="btn btn-accent" onclick="fscOuvrirDossier()" title="Page de garde + tous les certificats retenus, un signet par fournisseur">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/></svg>
          <span id="fsc-dossier-lbl">Dossier PDF fusionné</span>
        </button>
      </div>
    </div>

    <div class="fsc-kpis">
      ${kpi(st.fournisseurs||0, 'fournisseurs certifiés', '', 'tous')}
      ${kpi((st.expires||0)+(st.a_renouveler||0), `expirés ou à renouveler (${d.alerte_jours} j)`, (st.expires||st.a_renouveler)?'exp':'', 'expiration')}
      ${kpi(st.non_controles||0, 'à contrôler sur la base FSC', st.non_controles?'soon':'', 'a_controler')}
      ${kpi(st.sans_categorie||0, 'sans catégorie confirmée', st.sans_categorie?'soon':'', 'sans_categorie')}
    </div>

    ${couv ? `<div class="fsc-section-title">Catégories dont SIFA a besoin</div><div class="fsc-couv">${couv}</div>` : ''}

    <div class="fsc-toolbar">
      <div class="fsc-search">
        <svg class="fsc-search-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="search" id="fsc-q" placeholder="Rechercher (fournisseur, licence, certificat…)" value="${escAttr(S.fsc.q)}"
          oninput="fscOnSearch(this.value)" onkeydown="fscOnSearchKey(event)">
      </div>
      <div class="fsc-filtres">
        ${[['tous','Tous'],['a_traiter','À traiter'],['a_controler','À contrôler'],['expiration','Expiration'],['sans_categorie','Sans catégorie']].map(([f,l]) =>
          `<button type="button" class="fsc-filtre${S.fsc.filtre===f?' active':''}" data-f="${f}" onclick="fscSetFiltre('${f}')">${l}</button>`).join('')}
      </div>
    </div>
    <div id="fsc-list"></div>
  `;
  fscRenderList();
}

function fscJours(l){
  if(l.jours === null || l.jours === undefined) return '';
  if(l.jours < 0) return `expiré depuis ${-l.jours} j`;
  if(l.jours === 0) return 'expire aujourd\'hui';
  return `dans ${l.jours} j`;
}

function fscRenderList(){
  const wrap = document.getElementById('fsc-list');
  const d = S.fsc.data;
  if(!wrap || !d) return;
  const lignes = fscLignesVisibles();
  const lbl = document.getElementById('fsc-dossier-lbl');
  const filtreActif = S.fsc.q || S.fsc.filtre !== 'tous';
  if(lbl) lbl.textContent = filtreActif ? `Dossier PDF fusionné (${lignes.length})` : 'Dossier PDF fusionné';

  if(!lignes.length){
    wrap.innerHTML = `<div class="fsc-empty">${S.fsc.q ? `Aucun résultat pour « ${escHtml(S.fsc.q)} »` : 'Aucun fournisseur dans ce filtre.'}</div>`;
    return;
  }
  const admin = fscEstAdmin();
  const libClaim = {};
  (d.claims_catalogue||[]).forEach(c => libClaim[c.code] = c.label);

  const rows = lignes.map(l => {
    const se = FSC_STATUT_EXP[l.statut] || FSC_STATUT_EXP.sans_date;
    const alertes = l.alertes || [];
    const ctrl = l.dernier_controle;
    const doc = l.document;

    const chips = (l.claims||[]).map(c => `<span class="fsc-claim solid">${escHtml(libClaim[c]||c)}</span>`).join('')
      + (l.claims_proposes||[]).map(c => `<span class="fsc-claim lu" title="Lu sur le certificat — à confirmer au contrôle">${escHtml(libClaim[c]||c)}</span>`).join('');
    const recus = (l.recus||[]).map(r => `${escHtml(r.label)} ×${r.n}`).join(' · ');
    // La note complète de la lecture est dans le contrôle ; la ligne n'en garde
    // que la conclusion.
    const lectureNote = doc && doc.lecture && !(doc.lecture.claims||[]).length && !(l.claims||[]).length
      ? (doc.lecture.methode === 'aucune' ? 'Certificat non lu' : 'Absentes du certificat · à lire sur la base FSC') : '';

    const ctrlHtml = ctrl
      ? `<div class="fsc-ctrl ${ctrl.a_refaire?'soon':(ctrl.statut_base==='valide'?'ok':'exp')}">
           <span class="fsc-dot"></span>${escHtml(ctrl.statut_label)} · ${fmtDate(ctrl.date_controle)}
         </div>
         <div class="fsc-sub">${ctrl.a_refaire?'À refaire · ':''}${escHtml(ctrl.created_by_nom||'')}${ctrl.justificatif?' · justificatif':''}</div>`
      : `<div class="fsc-ctrl soon"><span class="fsc-dot"></span>Jamais contrôlé</div>`;

    const docBtn = doc
      ? `<button type="button" class="fsc-btn sm" onclick="fscVoirCertificat(${l.id})" title="${escAttr(doc.original_name||'')}">Certificat</button>`
      : (admin ? `<button type="button" class="fsc-btn sm" onclick="openRessourceFournisseur(${l.id})" title="Déposer le certificat dans Ressources fournisseurs">Déposer</button>` : '');

    return `<div class="fsc-row">
      <div class="fsc-c-four">
        <div class="fsc-nom">${escHtml(l.nom)}</div>
        ${l.groupe ? `<div class="fsc-sub">${escHtml(l.groupe)}${l.branche?' · '+escHtml(l.branche):''}</div>` : ''}
        ${alertes.length ? `<div class="fsc-alertes">${alertes.map(a => `<span class="fsc-alerte">${escHtml(a)}</span>`).join('')}</div>` : ''}
      </div>
      <div class="fsc-c-lic">
        <div class="fsc-mono">${escHtml(l.licence||'—')}</div>
        <div class="fsc-sub fsc-mono">${escHtml(l.certificat||'')}</div>
      </div>
      <div class="fsc-c-exp">
        <span class="fsc-pill ${se.cls}">${l.expiration ? fmtDate(l.expiration) : se.label}</span>
        <div class="fsc-sub">${escHtml(fscJours(l))}</div>
        ${l.expiration_fiche && l.expiration && l.expiration_fiche !== l.expiration
          ? `<div class="fsc-sub warn" title="Date utilisée par MySifa pour valider les réceptions">Fiche : ${fmtDate(l.expiration_fiche)}</div>` : ''}
      </div>
      <div class="fsc-c-cat">
        <div class="fsc-chips">${chips || '<span class="fsc-muted">Non renseignées</span>'}</div>
        ${recus ? `<div class="fsc-sub">Reçu : ${recus}</div>` : ''}
        ${lectureNote ? `<div class="fsc-sub">${escHtml(lectureNote)}</div>` : ''}
      </div>
      <div class="fsc-c-ctrl">${ctrlHtml}</div>
      <div class="fsc-c-act">
        ${docBtn}
        <button type="button" class="fsc-btn sm primary qual-write" onclick="fscOuvrirControle(${l.id})">Contrôler</button>
      </div>
    </div>`;
  }).join('');

  wrap.innerHTML = `<div class="fsc-table">
    <div class="fsc-row fsc-head">
      <div>Fournisseur</div><div>Licence · certificat</div><div>Expiration</div>
      <div>Catégories FSC</div><div>Contrôle base FSC</div><div></div>
    </div>
    ${rows}
  </div>
  <div class="fsc-legende">
    <span class="fsc-claim solid">Catégorie</span> confirmée au contrôle
    <span class="fsc-claim lu">Catégorie</span> lue sur le certificat, à confirmer
  </div>`;
}

function fscLigne(id){ return ((S.fsc.data||{}).fournisseurs||[]).find(l => l.id === id); }

// ─── Dossier PDF ─────────────────────────────────────────────────────
function fscOuvrirDossier(){
  const filtreActif = S.fsc.q || S.fsc.filtre !== 'tous';
  let url = '/api/qualite/fsc/dossier.pdf?inline=1';
  if(filtreActif){
    const ids = fscLignesVisibles().map(l => l.id);
    if(!ids.length){ showToast('Aucun fournisseur à inclure.','info'); return; }
    url += '&ids=' + ids.join(',');
  }
  window.open(url, '_blank');
}

// ─── Certificat ──────────────────────────────────────────────────────
function fscVoirCertificat(id){
  const l = fscLigne(id); if(!l || !l.document) return;
  const doc = l.document;
  const src = '/api/qualite/ressources/certificats/' + doc.id + '/download';
  const isImg = /\.(png|jpe?g|gif|webp|bmp)$/i.test(doc.original_name||'') || /^image\//.test(doc.mime_type||'');
  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal fsc-modal-preview">
        <div class="modal-hd">
          <h3>${escHtml(l.nom)} · ${escHtml(doc.original_name||'Certificat')}</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button>
        </div>
        <div class="modal-bd fsc-preview-bd">
          ${isImg ? `<img src="${src}" alt="${escAttr(doc.original_name||'')}">` : `<iframe src="${src}" title="Certificat"></iframe>`}
        </div>
        <div class="modal-ft">
          <a class="fsc-btn" href="${src}" target="_blank">Ouvrir dans un onglet</a>
          <button type="button" class="btn btn-accent qual-write" onclick="fscOuvrirControle(${l.id})">Contrôler</button>
        </div>
      </div>
    </div>`;
}

// ─── Lecture des certificats ─────────────────────────────────────────
async function fscLireUn(certId){
  const r = await api('/api/qualite/fsc/certificats/' + certId + '/lecture', {method:'POST'});
  if(!r.ok){
    let msg = 'Lecture impossible.';
    try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
    throw new Error(msg);
  }
  return r.json();
}

async function fscLireTout(){
  const ids = ((S.fsc.data||{}).documents_a_lire||[]).slice();
  if(!ids.length || S.fsc.lecture) return;
  S.fsc.lecture = {done:0, total:ids.length};
  let erreurs = 0;
  for(const id of ids){
    const b = document.getElementById('fsc-btn-lire');
    if(b) b.textContent = `Lecture ${S.fsc.lecture.done}/${S.fsc.lecture.total}…`;
    try{ await fscLireUn(id); }catch(e){ if(e.message === 'unauth') return; erreurs++; }
    S.fsc.lecture.done++;
  }
  S.fsc.lecture = null;
  showToast(erreurs ? `Lecture terminée — ${erreurs} certificat(s) illisible(s).` : 'Certificats lus.', erreurs ? 'info' : 'success');
  await fscLoad();
}

// ─── Contrôle sur la base FSC ────────────────────────────────────────
async function fscOuvrirControle(id){
  const l = fscLigne(id); if(!l) return;
  S.fsc.ctrl = {id, historique: null};
  fscRenderControle();
  try{
    const r = await api('/api/qualite/fsc/fournisseurs/' + id + '/controles');
    if(r.ok && S.fsc.ctrl && S.fsc.ctrl.id === id){
      S.fsc.ctrl.historique = (await r.json()).controles || [];
      const h = document.getElementById('fsc-ctrl-histo');
      if(h) h.innerHTML = fscHistoriqueHtml(S.fsc.ctrl.historique);
    }
  }catch(e){}
}

function fscHistoriqueHtml(liste){
  if(liste === null) return '<div class="fsc-muted">Chargement…</div>';
  if(!liste.length) return '<div class="fsc-muted">Aucun contrôle enregistré pour ce fournisseur.</div>';
  return liste.map(c => `<div class="fsc-histo-row">
    <span class="fsc-mono">${fmtDate(c.date_controle)}</span>
    <span>${escHtml(c.statut_label)}</span>
    <span class="fsc-muted">${escHtml((c.claims_labels||[]).join(', ') || 'aucune catégorie')}</span>
    <span class="fsc-muted">${escHtml(c.created_by_nom||'')}</span>
    ${c.justificatif ? `<a href="/api/qualite/fsc/controles/${c.id}/justificatif" target="_blank">Justificatif</a>` : '<span></span>'}
  </div>`).join('');
}

function fscRenderControle(){
  const c = S.fsc.ctrl; if(!c) return;
  const d = S.fsc.data; const l = fscLigne(c.id); if(!l) return;
  const doc = l.document;
  const lec = doc && doc.lecture;
  const prev = l.dernier_controle;
  const today = new Date(); const iso = today.getFullYear()+'-'+String(today.getMonth()+1).padStart(2,'0')+'-'+String(today.getDate()).padStart(2,'0');
  const expDefaut = (prev && prev.date_expiration_lue) || (lec && lec.expiration) || l.expiration_document || l.expiration_fiche || '';
  const coches = new Set(prev ? (prev.claims||[]) : ((lec && lec.claims)||[]).map(x => x.code));
  const lus = new Set(((lec && lec.claims)||[]).map(x => x.code));

  const lectureHtml = !doc
    ? `<div class="fsc-note warn">Aucun certificat FSC déposé pour ce fournisseur. Le contrôle sur la base FSC reste possible ; déposez le certificat dans Ressources fournisseurs pour qu'il entre dans le dossier PDF.</div>`
    : (lec
      ? `<div class="fsc-lu">
          <div class="fsc-lu-hd">Lu sur le certificat <span class="fsc-muted">· ${escHtml(doc.original_name||'')} · ${escHtml(lec.methode==='ia'?'lecture IA':'lecture du fichier')} le ${fmtDate(lec.le)}</span></div>
          <div class="fsc-lu-grid">
            <span class="fsc-muted">Licence</span><span class="fsc-mono">${escHtml(lec.licence||'—')}</span>
            <span class="fsc-muted">Certificat</span><span class="fsc-mono">${escHtml(lec.certificat||'—')}</span>
            <span class="fsc-muted">Expiration</span><span>${lec.expiration?fmtDate(lec.expiration):'—'}</span>
          </div>
          ${(lec.claims||[]).map(x => `<div class="fsc-extrait"><span class="fsc-claim lu">${escHtml(x.label||x.code)}</span> <span class="fsc-muted">p.${escHtml(String(x.page||'?'))} ·</span> ${escHtml(x.extrait||'')}</div>`).join('')}
          ${lec.note ? `<div class="fsc-note">${escHtml(lec.note)}</div>` : ''}
        </div>`
      : `<div class="fsc-lu"><div class="fsc-lu-hd">Certificat non lu <span class="fsc-muted">· ${escHtml(doc.original_name||'')}</span></div>
          <button type="button" class="fsc-btn sm" id="fsc-ctrl-lire" onclick="fscLireDepuisControle(${doc.id})">Lire le certificat</button></div>`);

  const claimsHtml = (d.claims_catalogue||[]).map(x => `
    <label class="fsc-check${coches.has(x.code)?' on':''}">
      <input type="checkbox" name="fsc-claim" value="${escAttr(x.code)}" ${coches.has(x.code)?'checked':''}
        onchange="this.parentElement.classList.toggle('on', this.checked)">
      ${escHtml(x.label)}${lus.has(x.code)?' <span class="fsc-tag-lu">lu</span>':''}
    </label>`).join('');

  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal fsc-modal">
        <div class="modal-hd">
          <h3>Contrôle FSC · ${escHtml(l.nom)}</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button>
        </div>
        <div class="modal-bd">
          <div class="fsc-etape">
            <div class="fsc-etape-num">1</div>
            <div class="fsc-etape-bd">
              <div class="fsc-etape-t">Chercher la licence sur la base FSC</div>
              <div class="fsc-licence-box">
                <span class="fsc-mono fsc-licence">${escHtml(l.licence||'Licence non renseignée')}</span>
                ${l.licence ? `<button type="button" class="fsc-btn sm" onclick="fscCopier('${escAttr(l.licence)}')">Copier</button>` : ''}
                <a class="fsc-btn sm" href="${escAttr(d.base_recherche_url)}" target="_blank" rel="noopener">Ouvrir la base FSC</a>
              </div>
              <div class="fsc-hint">Vérifier le statut du certificat, sa date d'expiration, puis la colonne « FSC Claims » de la liste des produits. Une capture de la page sert de justificatif.</div>
            </div>
          </div>

          <div class="fsc-etape">
            <div class="fsc-etape-num">2</div>
            <div class="fsc-etape-bd">
              <div class="fsc-etape-t">Comparer avec le certificat déposé</div>
              ${lectureHtml}
            </div>
          </div>

          <div class="fsc-etape">
            <div class="fsc-etape-num">3</div>
            <div class="fsc-etape-bd">
              <div class="fsc-etape-t">Enregistrer ce que dit la base FSC</div>
              <div class="fsc-form">
                <label class="fsc-field"><span>Date du contrôle</span>
                  <input type="date" id="fsc-f-date" value="${iso}" max="${iso}"></label>
                <label class="fsc-field"><span>Statut sur la base FSC</span>
                  <select id="fsc-f-statut">${(d.statuts_base||[]).map(s => `<option value="${escAttr(s.code)}"${(prev?prev.statut_base:'valide')===s.code?' selected':''}>${escHtml(s.label)}</option>`).join('')}</select></label>
                <label class="fsc-field"><span>Date d'expiration affichée</span>
                  <input type="date" id="fsc-f-exp" value="${escAttr((expDefaut||'').slice(0,10))}" oninput="fscMajCaseFiche()"></label>
              </div>
              <label class="fsc-maj-fiche" id="fsc-maj-fiche-wrap">
                <input type="checkbox" id="fsc-f-majfiche">
                <span>Reporter cette date sur la fiche fournisseur <span class="fsc-muted">(actuellement ${l.expiration_fiche?fmtDate(l.expiration_fiche):'vide'}) — c'est elle qui valide les réceptions de matière.</span></span>
              </label>
              <div class="fsc-field-t">Catégories FSC affichées pour ce fournisseur</div>
              <div class="fsc-checks">${claimsHtml}</div>
              <div class="fsc-form">
                <label class="fsc-field grow"><span>Justificatif (capture ou PDF de la base FSC)</span>
                  <input type="file" id="fsc-f-file" accept=".pdf,.png,.jpg,.jpeg,.webp"></label>
              </div>
              <label class="fsc-field"><span>Note</span>
                <textarea id="fsc-f-note" rows="2" placeholder="Ex. certificat renouvelé, portée réduite, groupe de produits concerné…"></textarea></label>
            </div>
          </div>

          <div class="fsc-field-t">Contrôles précédents</div>
          <div id="fsc-ctrl-histo" class="fsc-histo">${fscHistoriqueHtml(c.historique)}</div>
        </div>
        <div class="modal-ft">
          <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
          <button type="button" class="btn btn-accent" id="fsc-f-save" onclick="fscEnregistrerControle(${l.id})">Enregistrer le contrôle</button>
        </div>
      </div>
    </div>`;
  fscMajCaseFiche();
}

function fscMajCaseFiche(){
  const l = S.fsc.ctrl && fscLigne(S.fsc.ctrl.id); if(!l) return;
  const inp = document.getElementById('fsc-f-exp');
  const wrap = document.getElementById('fsc-maj-fiche-wrap');
  const box = document.getElementById('fsc-f-majfiche');
  if(!inp || !wrap || !box) return;
  const differe = !!inp.value && inp.value !== (l.expiration_fiche||'');
  wrap.hidden = !differe;
  box.checked = differe;
}

function fscCopier(txt){
  try{
    navigator.clipboard.writeText(txt).then(() => showToast('Licence copiée.','success'),
                                            () => showToast('Copie impossible — sélectionnez la licence.','info'));
  }catch(e){ showToast('Copie impossible — sélectionnez la licence.','info'); }
}

async function fscLireDepuisControle(certId){
  const b = document.getElementById('fsc-ctrl-lire');
  if(b){ b.disabled = true; b.textContent = 'Lecture…'; }
  try{
    await fscLireUn(certId);
    const r = await api('/api/qualite/fsc/synthese');
    if(r.ok) S.fsc.data = await r.json();
    // Le contrôle se redessine avec la lecture ; l'historique déjà chargé est
    // gardé dans S.fsc.ctrl et réaffiché tel quel.
    fscRenderControle();
  }catch(e){
    if(e.message === 'unauth') return;
    showToast(e.message || 'Lecture impossible.','danger');
    if(b){ b.disabled = false; b.textContent = 'Lire le certificat'; }
  }
}

async function fscEnregistrerControle(id){
  const l = fscLigne(id); if(!l) return;
  const btn = document.getElementById('fsc-f-save');
  const fd = new FormData();
  fd.append('date_controle', (document.getElementById('fsc-f-date')||{}).value || '');
  fd.append('statut_base', (document.getElementById('fsc-f-statut')||{}).value || '');
  fd.append('date_expiration', (document.getElementById('fsc-f-exp')||{}).value || '');
  fd.append('claims', Array.from(document.querySelectorAll('input[name="fsc-claim"]:checked')).map(x => x.value).join(','));
  fd.append('note', (document.getElementById('fsc-f-note')||{}).value || '');
  fd.append('certificat_id', l.document ? String(l.document.id) : '');
  const maj = document.getElementById('fsc-f-majfiche');
  fd.append('maj_fiche', maj && maj.checked && !document.getElementById('fsc-maj-fiche-wrap').hidden ? '1' : '0');
  const f = document.getElementById('fsc-f-file');
  if(f && f.files && f.files[0]) fd.append('justificatif', f.files[0]);

  if(btn){ btn.disabled = true; btn.textContent = 'Enregistrement…'; }
  try{
    const r = await api('/api/qualite/fsc/fournisseurs/' + id + '/controles', {method:'POST', body: fd});
    if(!r.ok){
      let msg = 'Enregistrement impossible.';
      try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger');
      if(btn){ btn.disabled = false; btn.textContent = 'Enregistrer le contrôle'; }
      return;
    }
    const j = await r.json();
    closeMroot();
    S.fsc.ctrl = null;
    showToast(j.fiche_maj ? 'Contrôle enregistré · fiche fournisseur mise à jour.' : 'Contrôle enregistré.','success');
    await fscLoad();
  }catch(e){
    if(e.message !== 'unauth') showToast('Erreur réseau','danger');
    if(btn){ btn.disabled = false; btn.textContent = 'Enregistrer le contrôle'; }
  }
}

// ─── CSS ─────────────────────────────────────────────────────────────
(function injectFscCSS(){
  if(document.getElementById('fsc-css')) return;
  const st = document.createElement('style');
  st.id = 'fsc-css';
  st.textContent = `
  .fsc-hero{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin-bottom:14px;
    display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
  .fsc-hero-txt{flex:1;min-width:240px}
  .fsc-hero h1{margin:0 0 4px;font-size:22px;color:var(--text)}
  .fsc-hero p{margin:0;color:var(--text2);font-size:13px;line-height:1.55;max-width:760px}
  .fsc-hero-actions{display:flex;gap:8px;flex-wrap:wrap}
  .fsc-hero .btn-accent, .fsc-modal .btn-accent, .fsc-modal-preview .btn-accent{color:white}
  .fsc-mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}
  .fsc-muted{color:var(--muted)}

  .fsc-btn{display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border-radius:10px;font-weight:700;font-size:13px;
    background:var(--card);color:var(--text);border:1px solid var(--border);cursor:pointer;font-family:inherit;
    text-decoration:none;transition:background .15s,border-color .15s;white-space:nowrap}
  .fsc-btn:hover{background:var(--bg);border-color:var(--accent)}
  .fsc-btn:disabled{opacity:.6;cursor:default}
  .fsc-btn.sm{padding:6px 11px;font-size:12px;border-radius:8px}
  .fsc-row .fsc-btn, .modal .fsc-btn{background:var(--bg)}
  .fsc-row .fsc-btn:hover, .modal .fsc-btn:hover{background:var(--card)}
  .fsc-btn.primary{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
  .fsc-row .fsc-btn.primary:hover{background:var(--accent-bg);filter:brightness(1.08)}

  .fsc-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px}
  .fsc-kpi{display:flex;flex-direction:column;align-items:flex-start;gap:2px;background:var(--card);border:1px solid var(--border);
    border-radius:12px;padding:12px 14px;cursor:pointer;font-family:inherit;text-align:left;transition:border-color .15s}
  .fsc-kpi:hover{border-color:var(--accent)}
  .fsc-kpi-val{font-size:22px;font-weight:800;color:var(--text)}
  .fsc-kpi-lbl{font-size:12px;color:var(--muted)}
  .fsc-kpi.exp .fsc-kpi-val{color:var(--danger)}
  .fsc-kpi.soon .fsc-kpi-val{color:var(--warn)}

  .fsc-section-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:4px 0 8px}
  .fsc-couv{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-bottom:16px}
  .fsc-couv-card{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--border);border-radius:12px;padding:12px 14px}
  .fsc-couv-card.ok{border-left-color:var(--success)}
  .fsc-couv-card.soon{border-left-color:var(--warn)}
  .fsc-couv-card.exp{border-left-color:var(--danger)}
  .fsc-couv-hd{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;flex-wrap:wrap}
  .fsc-couv-usage{font-size:11px;color:var(--muted)}
  .fsc-couv-n{font-size:13px;color:var(--text2)}
  .fsc-couv-n b{color:var(--text)}
  .fsc-couv-detail{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.45}

  .fsc-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
  .fsc-search{position:relative;flex:1;min-width:220px}
  .fsc-search input{width:100%;padding:10px 12px 10px 34px;background:var(--card);border:1px solid var(--border);border-radius:10px;
    color:var(--text);font-size:13px;font-family:inherit;transition:border-color .15s}
  .fsc-search input:focus{border-color:var(--accent);outline:none;box-shadow:0 0 0 3px var(--accent-bg)}
  .fsc-search-ico{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
  .fsc-filtres{display:flex;gap:4px;padding:4px;background:var(--card);border:1px solid var(--border);border-radius:10px;flex-wrap:wrap}
  .fsc-filtre{padding:6px 12px;border-radius:7px;border:1px solid transparent;background:var(--card);color:var(--text2);
    font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
  .fsc-filtre:hover{background:var(--bg);color:var(--text)}
  .fsc-filtre.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}

  .fsc-table{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
  .fsc-row{display:grid;grid-template-columns:minmax(170px,1.3fr) 140px 130px minmax(190px,1.6fr) 160px 170px;
    gap:12px;padding:12px 16px;border-bottom:1px solid var(--border);align-items:start}
  .fsc-row:last-child{border-bottom:none}
  .fsc-head{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);background:var(--bg);padding:9px 16px}
  .fsc-nom{font-size:13px;font-weight:700;color:var(--text)}
  .fsc-sub{font-size:11px;color:var(--muted);margin-top:3px;line-height:1.4}
  .fsc-sub.warn{color:var(--warn)}
  .fsc-alertes{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
  .fsc-alerte{font-size:10.5px;padding:2px 7px;border-radius:999px;background:rgba(251,191,36,.14);color:var(--warn);font-weight:600}
  .fsc-pill{display:inline-flex;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:700}
  .fsc-pill.ok{background:rgba(52,211,153,.15);color:var(--success)}
  .fsc-pill.soon{background:rgba(251,191,36,.18);color:var(--warn)}
  .fsc-pill.exp{background:rgba(248,113,113,.18);color:var(--danger)}
  .fsc-pill.nod{background:var(--bg);color:var(--muted);border:1px solid var(--border)}
  .fsc-chips{display:flex;flex-wrap:wrap;gap:4px}
  .fsc-claim{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap}
  .fsc-claim.solid{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent)}
  .fsc-claim.lu{background:transparent;color:var(--text2);border:1px dashed var(--muted)}
  .fsc-ctrl{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:var(--text2)}
  .fsc-dot{width:8px;height:8px;border-radius:50%;background:var(--muted);flex:0 0 auto}
  .fsc-ctrl.ok .fsc-dot{background:var(--success)}
  .fsc-ctrl.soon .fsc-dot{background:var(--warn)}
  .fsc-ctrl.exp .fsc-dot{background:var(--danger)}
  .fsc-c-act{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
  .fsc-empty{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:28px;text-align:center;color:var(--muted);font-size:13px}
  .fsc-legende{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin:10px 2px 0}
  .fsc-legende .fsc-claim + .fsc-claim, .fsc-legende .fsc-claim.lu{margin-left:10px}

  .fsc-modal{max-width:760px}
  .fsc-modal-preview{max-width:1000px;width:94vw}
  .fsc-preview-bd{padding:0;height:70vh;display:flex;align-items:center;justify-content:center;background:var(--bg)}
  .fsc-preview-bd iframe{width:100%;height:100%;border:none}
  .fsc-preview-bd img{max-width:100%;max-height:100%;object-fit:contain}
  .fsc-etape{display:flex;gap:12px;margin-bottom:16px}
  .fsc-etape-num{flex:0 0 24px;height:24px;border-radius:50%;background:var(--accent-bg);color:var(--accent);
    display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800}
  .fsc-etape-bd{flex:1;min-width:0}
  .fsc-etape-t{font-size:13px;font-weight:700;color:var(--text);margin:2px 0 8px}
  .fsc-licence-box{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .fsc-licence{font-size:15px;font-weight:700;color:var(--text);padding:6px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px}
  .fsc-hint{font-size:11.5px;color:var(--muted);margin-top:6px;line-height:1.5}
  .fsc-lu{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
  .fsc-lu-hd{font-size:12px;font-weight:700;color:var(--text);margin-bottom:6px}
  .fsc-lu-grid{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:12px;margin-bottom:6px}
  .fsc-extrait{font-size:11.5px;color:var(--text2);margin-top:5px;line-height:1.45;word-break:break-word}
  .fsc-note{font-size:11.5px;color:var(--text2);margin-top:6px;line-height:1.45}
  .fsc-note.warn{color:var(--warn)}
  .fsc-form{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
  .fsc-field{display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px}
  .fsc-field.grow{flex:1 1 100%}
  .fsc-field > span, .fsc-field-t{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
  .fsc-field-t{margin:4px 0 6px}
  .fsc-field input, .fsc-field select, .fsc-field textarea{background:var(--bg);border:1px solid var(--border);border-radius:8px;
    padding:8px 10px;color:var(--text);font-family:inherit;font-size:13px;width:100%}
  .fsc-field input:focus, .fsc-field select:focus, .fsc-field textarea:focus{border-color:var(--accent);outline:none}
  .fsc-maj-fiche{display:flex;gap:8px;align-items:flex-start;font-size:12px;color:var(--text2);margin:-2px 0 10px;cursor:pointer}
  .fsc-maj-fiche input{margin-top:2px}
  .fsc-maj-fiche[hidden]{display:none}
  .fsc-checks{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
  .fsc-check{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:8px;border:1px solid var(--border);
    background:var(--bg);font-size:12px;font-weight:600;color:var(--text2);cursor:pointer}
  .fsc-check.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
  .fsc-check input{margin:0}
  .fsc-tag-lu{font-size:9.5px;font-weight:700;text-transform:uppercase;padding:1px 5px;border-radius:4px;border:1px dashed currentColor;opacity:.8}
  .fsc-histo{display:flex;flex-direction:column;gap:2px;font-size:12px}
  .fsc-histo-row{display:grid;grid-template-columns:90px 90px 1fr 120px 80px;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);align-items:center}
  .fsc-histo-row a{color:var(--accent);font-weight:600;text-decoration:none}

  @media(max-width:1100px){
    .fsc-row{grid-template-columns:minmax(160px,1.2fr) 130px 120px minmax(170px,1.4fr);}
    .fsc-c-ctrl{grid-column:1 / 3}
    .fsc-c-act{grid-column:3 / 5}
    .fsc-head > div:nth-child(5), .fsc-head > div:nth-child(6){display:none}
  }
  @media(max-width:720px){
    .fsc-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
    .fsc-head{display:none}
    .fsc-row{grid-template-columns:1fr 1fr;gap:8px 12px}
    .fsc-c-four, .fsc-c-cat{grid-column:1 / 3}
    .fsc-c-ctrl{grid-column:1 / 2}
    .fsc-c-act{grid-column:2 / 3}
    .fsc-hero-actions{width:100%}
    .fsc-hero-actions > *{flex:1;justify-content:center}
    .fsc-histo-row{grid-template-columns:80px 1fr;}
  }
  `;
  document.head.appendChild(st);
})();
"""
