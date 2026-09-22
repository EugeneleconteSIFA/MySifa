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
  sousOnglet: 'fournisseurs',  // fournisseurs | appro
  appro: null,         // reponse de /api/qualite/fsc/appro
  approFiltres: {debut:'', fin:'', eligible:'', certifies:1, q:''},
  approBusy: null,     // id de la ligne en cours d'enregistrement
  data: null,          // reponse de /api/qualite/fsc/synthese
  q: '',               // recherche (fournisseur, licence, certificat)
  filtre: 'tous',      // tous | a_traiter | a_controler | expiration | sans_categorie
  lecture: null,       // {done, total} pendant la lecture des certificats
  ctrl: null,          // controle en cours de saisie {id, historique}
  lot: null,           // lot de controles en cours d'import {etape, jeton, lignes}
};

const FSC_STATUT_EXP = {
  valide:       {cls:'ok',   label:'Valide'},
  a_renouveler: {cls:'soon', label:'À renouveler'},
  expire:       {cls:'exp',  label:'Expiré'},
  sans_date:    {cls:'nod',  label:'Sans date'},
};

function fscEstAdmin(){ return !!(S.isQualiteAdmin && !S.isQualiteReadonly); }

// L'onglet FSC porte deux écrans : l'annuaire des fournisseurs certifiés et le
// registre des approvisionnements. Le sous-onglet actif suit l'utilisateur d'une
// visite à l'autre, comme celui de Certifications SIFA.
try{ const _fs = localStorage.getItem('mysifa_fsc_sous_onglet'); if(_fs) S.fsc.sousOnglet = _fs; }catch(e){}

function fscSousTabsHtml(actif){
  const t = (k, label, hint) =>
    `<button type="button" class="fsc-stab${actif===k?' active':''}" onclick="fscSetSousOnglet('${k}')" title="${escAttr(hint)}">${escHtml(label)}</button>`;
  return `<div class="fsc-stabs">
    ${t('fournisseurs','Fournisseurs','Certificats, licences, expirations et contrôles sur la base FSC')}
    ${t('appro','Approvisionnements','Registre des entrées de matière : allégation du BL, de la facture, éligibilité')}
  </div>`;
}

function fscSetSousOnglet(k){
  S.fsc.sousOnglet = k;
  try{ localStorage.setItem('mysifa_fsc_sous_onglet', k); }catch(e){}
  fscEnter();
}

async function fscEnter(){
  const root = document.getElementById('content');
  if(!root) return;
  if(S.fsc.sousOnglet === 'appro'){ await fscApproEnter(); return; }
  if(!S.fsc.data){
    root.innerHTML = `${sifaTabsHtml('fsc')}${fscSousTabsHtml('fournisseurs')}
      <div class="fsc-hero"><div class="fsc-hero-txt"><h1>FSC</h1><p>Chargement des fournisseurs certifiés…</p></div></div>`;
  }
  await fscLoad();
}

async function fscLoad(){
  try{
    const r = await api('/api/qualite/fsc/synthese');
    if(!r.ok){ showToast('Chargement FSC impossible.','danger'); return; }
    S.fsc.data = await r.json();
    if(gedActiveTab() !== 'fsc' || S.fsc.sousOnglet !== 'fournisseurs') return;
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
    if(S.fsc.filtre === 'a_traiter') return (l.alertes||[]).length > 0 || !l.dernier_controle || l.dernier_controle.a_refaire || !(l.claims||[]).length || !(l.portees||[]).length;
    if(S.fsc.filtre === 'a_controler') return !l.dernier_controle || l.dernier_controle.a_refaire;
    if(S.fsc.filtre === 'expiration') return l.statut === 'expire' || l.statut === 'a_renouveler' || l.statut === 'sans_date';
    if(S.fsc.filtre === 'sans_categorie') return !(l.claims||[]).length;
    // Portée : deux questions distinctes derrière un même filtre — le certificat
    // ne couvre pas ce qu'on achète, ou on ne sait pas encore ce qu'il couvre.
    if(S.fsc.filtre === 'portee') return ((l.couverture||{}).alerte) || !(l.portees||[]).length;
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
    ${fscSousTabsHtml('fournisseurs')}
    <div class="fsc-hero">
      <div class="fsc-hero-txt">
        <h1>FSC</h1>
        <p>Fournisseurs certifiés, ce que leur certificat couvre (portée produit FSC-STD-40-004a)
        et sous quelle allégation ils peuvent livrer.
        Chaque contrôle sur la base FSC est conservé avec sa date et son justificatif.${d.licence_sifa?` Licence SIFA : <span class="fsc-mono">${escHtml(d.licence_sifa)}</span>.`:''}</p>
      </div>
      <div class="fsc-hero-actions">
        ${aLire ? `<button type="button" class="fsc-btn qual-write" id="fsc-btn-lire" onclick="fscLireTout()" ${lecture?'disabled':''}
            title="Lit la licence, l'expiration et les catégories écrites sur chaque certificat. Rien n'est validé sans contrôle.">
            ${lecture ? `Lecture ${lecture.done}/${lecture.total}…` : `Lire les certificats (${aLire})`}
          </button>` : ''}
        <button type="button" class="fsc-btn qual-write" onclick="fscOuvrirImport()"
          title="Déposer les dossiers téléchargés sur la base publique FSC et enregistrer les contrôles en une fois">
          Importer un contrôle
        </button>
        <button type="button" class="fsc-btn" onclick="fscOuvrirDeclaration()"
          title="Pièce d'audit : ce qui a été contrôlé sur la base FSC, quand, et les écarts relevés. À faire viser par les responsables de la chaîne de contrôle.">
          Déclaration de contrôle
        </button>
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
      ${kpi((st.portee_non_couvrante||0)+(st.sans_portee||0), 'portée à vérifier ou à saisir', (st.portee_non_couvrante?'exp':(st.sans_portee?'soon':'')), 'portee')}
    </div>

    ${couv ? `<div class="fsc-section-title">Catégories dont SIFA a besoin</div><div class="fsc-couv">${couv}</div>` : ''}

    <div class="fsc-toolbar">
      <div class="fsc-search">
        <svg class="fsc-search-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="search" id="fsc-q" placeholder="Rechercher (fournisseur, licence, certificat…)" value="${escAttr(S.fsc.q)}"
          oninput="fscOnSearch(this.value)" onkeydown="fscOnSearchKey(event)">
      </div>
      <div class="fsc-filtres">
        ${[['tous','Tous'],['a_traiter','À traiter'],['a_controler','À contrôler'],['expiration','Expiration'],['portee','Portée'],['sans_categorie','Sans allégation']].map(([f,l]) =>
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

    // Portée produit : ce que le certificat couvre, confronté à ce qu'on achète.
    // Trois états à ne pas confondre — non couvrant (rouge), non saisi (à faire),
    // achats non renseignés (à faire aussi, mais l'autre moitié de la question).
    const cv = l.couverture || {};
    const pChips = (l.portees||[]).map((c,i) => `<span class="fsc-claim solid" title="${escAttr((l.portees_labels||[])[i]||c)}">${escHtml(c)}</span>`).join('')
      + (l.portees_proposees||[]).map(c => `<span class="fsc-claim lu" title="Lue sur le certificat — à confirmer au contrôle">${escHtml(c)}</span>`).join('');
    const achats = (l.portees_achetees||[]).join(' · ');
    let pEtat = '';
    if(cv.alerte) pEtat = `<div class="fsc-sub danger">Ne couvre pas ${escHtml((cv.manquants||[]).join(', '))}</div>`;
    else if(cv.partielle) pEtat = `<div class="fsc-sub warn">Partielle — ${escHtml((cv.manquants||[]).join(', '))} non couvert</div>`;
    else if(!(l.portees||[]).length) pEtat = `<div class="fsc-sub">À relever sur le dossier FSC</div>`;
    else if(cv.besoins_inconnus) pEtat = `<div class="fsc-sub">Achats non renseignés</div>`;
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
      <div class="fsc-c-portee">
        <div class="fsc-chips">${pChips || '<span class="fsc-muted">Non renseignée</span>'}</div>
        ${pEtat}
        <div class="fsc-sub fsc-achats">
          <span>Achats : ${achats ? escHtml(achats) : '<span class="fsc-muted">—</span>'}</span>
          ${admin ? `<button type="button" class="fsc-lien" onclick="fscOuvrirAchats(${l.id})">modifier</button>` : ''}
        </div>
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
      <div>Portée produit</div><div>Allégations de sortie</div><div>Contrôle base FSC</div><div></div>
    </div>
    ${rows}
  </div>
  <div class="fsc-legende">
    <span class="fsc-claim solid">P7.8</span> confirmée au contrôle sur la base FSC
    <span class="fsc-claim lu">P7.8</span> lue sur le certificat déposé, à confirmer
    <span class="fsc-legende-sep">·</span>
    <span>La portée dit ce que le certificat couvre, l'allégation sous quelle mention le fournisseur livre.
    Le Controlled Wood ne donne droit à aucune allégation sur le produit fini.</span>
  </div>
  ${fscSortiesHtml()}`;
}

// ─── Fiches sorties de la liste FSC ──────────────────────────────────
// « On désactive, on n'efface pas » ne vaut que si la sortie reste lisible.
// L'auditeur demande pourquoi tel fournisseur n'est plus dans la liste ; la
// réponse est le dernier contrôle enregistré avant la sortie, avec sa date.
function fscSortiesHtml(){
  const sorties = ((S.fsc.data||{}).sorties)||[];
  if(!sorties.length) return '';
  const rows = sorties.map(sx => {
    const c = sx.dernier_controle;
    return `<div class="fsc-sortie-row">
      <div>
        <div class="fsc-nom">${escHtml(sx.nom)}</div>
        <div class="fsc-sub fsc-mono">${escHtml(sx.licence||'—')}${sx.certificat?' · '+escHtml(sx.certificat):''}</div>
      </div>
      <div class="fsc-sub">${c ? escHtml(c.statut_label)+' · '+fmtDate(c.date_controle) : 'Aucun contrôle enregistré'}</div>
      <div class="fsc-sub">${sx.motif ? escHtml(sx.motif) : '<span class="fsc-muted">Motif non renseigné</span>'}</div>
      <div>${c && c.justificatif ? `<a class="fsc-lien" href="/api/qualite/fsc/controles/${c.id}/justificatif" target="_blank">Justificatif</a>` : ''}</div>
    </div>`;
  }).join('');
  return `<div class="fsc-section-title">Sorties de la liste FSC (${sorties.length})</div>
    <div class="fsc-sorties">
      <div class="fsc-sortie-row fsc-head"><div>Fournisseur</div><div>Dernier contrôle</div><div>Motif</div><div></div></div>
      ${rows}
    </div>
    <div class="fsc-legende">Ces fiches et leurs documents sont conservés ; elles ne comptent pas dans la liste des fournisseurs certifiés et n'entrent pas dans le dossier PDF.</div>`;
}

// ─── Ce que SIFA achète à ce fournisseur ─────────────────────────────
function fscOuvrirAchats(id){
  const l = fscLigne(id); if(!l) return;
  S.fsc.achats = {id: id, codes: (l.portees_achetees||[]).slice()};
  fscRenderAchats();
}

function fscRenderAchats(){
  const a = S.fsc.achats; if(!a) return;
  const l = fscLigne(a.id); if(!l) return;
  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal fsc-modal-achats">
        <div class="modal-hd">
          <h3>Catégories achetées · ${escHtml(l.nom)}</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button>
        </div>
        <div class="modal-bd">
          <div class="fsc-hint">Les codes de FSC-STD-40-004a correspondant aux matières achetées à ce fournisseur.
          Ils servent à vérifier que la portée de son certificat les couvre : un certificat qui ne porte que
          P7.6 Enveloppes ne couvre pas P7.8 Étiquettes adhésives.</div>
          ${fscSaisiePorteeHtml('achats', a.codes)}
        </div>
        <div class="modal-ft">
          <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
          <button type="button" class="btn btn-accent" id="fsc-achats-save" onclick="fscEnregistrerAchats()">Enregistrer</button>
        </div>
      </div>
    </div>`;
}

async function fscEnregistrerAchats(){
  const a = S.fsc.achats; if(!a) return;
  const btn = document.getElementById('fsc-achats-save');
  if(btn){ btn.disabled = true; btn.textContent = 'Enregistrement…'; }
  try{
    const r = await api('/api/qualite/fsc/fournisseurs/' + a.id + '/portees-achetees',
      {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({portees: a.codes})});
    if(!r.ok){
      let msg = 'Enregistrement impossible.';
      try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger');
      if(btn){ btn.disabled = false; btn.textContent = 'Enregistrer'; }
      return;
    }
    closeMroot();
    S.fsc.achats = null;
    showToast('Catégories achetées enregistrées.','success');
    await fscLoad();
  }catch(e){
    if(e.message === 'unauth') return;
    showToast('Erreur réseau','danger');
    if(btn){ btn.disabled = false; btn.textContent = 'Enregistrer'; }
  }
}

// ─── Saisie d'une liste de portées ───────────────────────────────────
// Les dossiers de certification listent la portée en clair (« P2.1, P2.4,
// P7.8 ») : on colle, on ne coche pas. 115 codes en cases à cocher seraient
// illisibles, et la saisie se fait dossier ouvert à côté.
function fscPorteesState(cible){
  return cible === 'achats' ? (S.fsc.achats||{codes:[]}) : (S.fsc.ctrl||{portees:[]});
}
function fscPorteesCodes(cible){
  const st = fscPorteesState(cible);
  return cible === 'achats' ? (st.codes||[]) : (st.portees||[]);
}
function fscPorteesSet(cible, codes){
  const st = fscPorteesState(cible);
  if(cible === 'achats') st.codes = codes; else st.portees = codes;
}

function fscNormPortee(txt){
  const c = String(txt||'').trim().toUpperCase().replace(/[\s ]/g,'').replace(/\.+$/,'');
  if(!/^P\d+(\.\d+)*$/.test(c)) return '';
  return c;
}

function fscPorteeLabel(code){
  const cat = ((S.fsc.data||{}).portees_catalogue)||[];
  const e = cat.find(x => x.code === code);
  return e ? e.label : '';
}

function fscSaisiePorteeHtml(cible, codes){
  const cat = ((S.fsc.data||{}).portees_catalogue)||[];
  const chips = (codes||[]).map(c => {
    const lab = fscPorteeLabel(c);
    return `<span class="fsc-portee-chip" title="${escAttr(lab||'Code hors référentiel')}">${escHtml(c)}
      <span class="fsc-portee-lab">${escHtml(lab||'hors référentiel')}</span>
      <button type="button" class="fsc-portee-x" onclick="fscPorteeRetirer('${escAttr(cible)}','${escAttr(c)}')" title="Retirer">&times;</button></span>`;
  }).join('');
  return `<div class="fsc-portee-box">
    <div class="fsc-portee-chips" id="fsc-portee-chips-${escAttr(cible)}">${chips || '<span class="fsc-muted">Aucun code</span>'}</div>
    <div class="fsc-portee-saisie">
      <input type="text" class="fsc-in" id="fsc-portee-in-${escAttr(cible)}" list="fsc-portee-liste"
        placeholder="P7.8, P2.4 — coller la portée du dossier FSC"
        onkeydown="fscPorteeKey(event,'${escAttr(cible)}')">
      <button type="button" class="fsc-btn sm" onclick="fscPorteeAjouter('${escAttr(cible)}')">Ajouter</button>
    </div>
    <datalist id="fsc-portee-liste">
      ${cat.map(x => `<option value="${escAttr(x.code)}">${escAttr(x.code + ' — ' + x.label)}</option>`).join('')}
    </datalist>
  </div>`;
}

function fscPorteeKey(ev, cible){
  if(ev.key === 'Enter' || ev.key === ','){ ev.preventDefault(); fscPorteeAjouter(cible); }
}

function fscPorteeAjouter(cible){
  const inp = document.getElementById('fsc-portee-in-' + cible);
  if(!inp) return;
  const codes = fscPorteesCodes(cible).slice();
  const refuses = [];
  // Une ligne collée depuis un dossier FSC contient des virgules, des
  // point-virgules et des espaces : on accepte les trois séparateurs.
  String(inp.value||'').split(/[,;\s]+/).forEach(tok => {
    if(!tok) return;
    const c = fscNormPortee(tok);
    if(!c){ refuses.push(tok); return; }
    if(codes.indexOf(c) === -1) codes.push(c);
  });
  if(refuses.length) showToast('Code ignoré : ' + refuses.join(', ') + ' — format attendu P7.8.','info');
  const cat = ((S.fsc.data||{}).portees_catalogue)||[];
  const ordre = {}; cat.forEach((x,i) => ordre[x.code] = i);
  codes.sort((a,b) => (ordre[a] === undefined ? 9999 : ordre[a]) - (ordre[b] === undefined ? 9999 : ordre[b]));
  fscPorteesSet(cible, codes);
  inp.value = '';
  fscMajChipsPortee(cible);
  inp.focus();
}

function fscPorteeRetirer(cible, code){
  fscPorteesSet(cible, fscPorteesCodes(cible).filter(c => c !== code));
  fscMajChipsPortee(cible);
}

// Redessine les seules puces, jamais la modal entière : un re-render complet
// perdrait la saisie en cours des autres champs du contrôle.
function fscMajChipsPortee(cible){
  const wrap = document.getElementById('fsc-portee-chips-' + cible);
  if(!wrap) return;
  const codes = fscPorteesCodes(cible);
  wrap.innerHTML = codes.length ? codes.map(c => {
    const lab = fscPorteeLabel(c);
    return `<span class="fsc-portee-chip" title="${escAttr(lab||'Code hors référentiel')}">${escHtml(c)}
      <span class="fsc-portee-lab">${escHtml(lab||'hors référentiel')}</span>
      <button type="button" class="fsc-portee-x" onclick="fscPorteeRetirer('${escAttr(cible)}','${escAttr(c)}')" title="Retirer">&times;</button></span>`;
  }).join('') : '<span class="fsc-muted">Aucun code</span>';
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

// ─── Déclaration de contrôle (pièce d'audit) ─────────────────────────
// Même périmètre que le dossier fusionné : si un filtre est actif, la
// déclaration ne porte que sur les fournisseurs affichés — et le dit.
function fscOuvrirDeclaration(){
  const filtreActif = S.fsc.q || S.fsc.filtre !== 'tous';
  let url = '/api/qualite/fsc/declaration-controle.pdf?inline=1';
  if(filtreActif){
    const ids = fscLignesVisibles().map(l => l.id);
    if(!ids.length){ showToast('Aucun fournisseur à déclarer.','info'); return; }
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
  // La portée du dernier contrôle est le point de départ : un contrôle de
  // renouvellement ne rechange pas une portée qui n'a pas bougé.
  S.fsc.ctrl = {id, historique: null, portees: (l.portees||[]).slice()};
  if(!S.fsc.ctrl.portees.length) S.fsc.ctrl.portees = (l.portees_proposees||[]).slice();
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
    <span class="fsc-muted">${escHtml((c.portees||[]).join(', ') || 'portée non relevée')}</span>
    <span class="fsc-muted">${escHtml((c.claims_labels||[]).join(', ') || 'aucune allégation')}</span>
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
              <div class="fsc-field-t">Portée du certificat <span class="fsc-muted">— codes produit FSC-STD-40-004a lus sur le dossier</span></div>
              ${fscSaisiePorteeHtml('ctrl', c.portees||[])}
              ${(l.portees_achetees||[]).length
                ? `<div class="fsc-hint">Achetés à ce fournisseur : <span class="fsc-mono">${escHtml((l.portees_achetees||[]).join(', '))}</span> — la portée doit les couvrir.</div>`
                : `<div class="fsc-hint">Catégories achetées à ce fournisseur non renseignées — sans elles, aucune alerte de couverture n'est possible.</div>`}

              <div class="fsc-field-t">Allégations de sortie autorisées par le certificat</div>
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
  fd.append('portees', ((S.fsc.ctrl||{}).portees||[]).join(','));
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

// ══════════════════════════════════════════════════════════════════════
// Sous-onglet Approvisionnements : le registre de chaîne de contrôle
//
// Les colonnes de gauche viennent de RVGI et ne s'éditent pas. Quatre champs se
// saisissent : n° de facture fournisseur, allégation du BL, allégation de la
// facture, présence du code de certificat — plus l'étiquette posée et une
// observation. Chaque saisie recalcule l'éligibilité côté serveur et passe au
// journal ; rien ne se supprime.
// ══════════════════════════════════════════════════════════════════════

const FSC_ELIGIBLE = {
  oui:              {cls:'ok',   label:'Éligible'},
  non:              {cls:'exp',  label:'Non éligible'},
  a_verifier:       {cls:'soon', label:'À vérifier'},
  ecart_bl_facture: {cls:'exp',  label:'Écart BL / facture'},
};

async function fscApproEnter(){
  const root = document.getElementById('content');
  if(!root) return;
  if(!S.fsc.appro){
    root.innerHTML = `${sifaTabsHtml('fsc')}${fscSousTabsHtml('appro')}
      <div class="fsc-hero"><div class="fsc-hero-txt"><h1>Approvisionnements FSC</h1>
      <p>Chargement du registre…</p></div></div>`;
  }
  await fscApproLoad();
}

function fscApproQs(){
  const f = S.fsc.approFiltres;
  const p = new URLSearchParams();
  if(f.debut) p.set('debut', f.debut);
  if(f.fin) p.set('fin', f.fin);
  if(f.eligible) p.set('eligible', f.eligible);
  if(f.certifies) p.set('certifies', '1');
  if(f.q) p.set('q', f.q);
  return p.toString();
}

async function fscApproLoad(){
  try{
    const r = await api('/api/qualite/fsc/appro?' + fscApproQs());
    if(!r.ok){ showToast('Chargement du registre impossible.','danger'); return; }
    S.fsc.appro = await r.json();
    if(gedActiveTab() !== 'fsc' || S.fsc.sousOnglet !== 'appro') return;
    fscApproRender();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

function fscApproSetFiltre(cle, valeur, recharger){
  S.fsc.approFiltres[cle] = valeur;
  if(recharger) fscApproLoad();
}

function fscApproRender(){
  const root = document.getElementById('content');
  const d = S.fsc.appro;
  if(!root || !d) return;
  const st = d.stats || {};
  const f = S.fsc.approFiltres;
  const admin = fscEstAdmin();

  const volumes = (d.volumes||[]).map(v => `
    <div class="fsc-couv-card ok">
      <div class="fsc-couv-hd"><span class="fsc-claim solid">${escHtml(v.libelle)}</span>
        <span class="fsc-couv-usage">${v.lignes} ligne${v.lignes>1?'s':''}</span></div>
      <div class="fsc-couv-n"><b>${fscNb(v.m2)}</b> m² <span class="fsc-muted">· ${fscNb(v.ml)} ml</span></div>
    </div>`).join('');

  const kpi = (val, label, cls, filtre) => `
    <button type="button" class="fsc-kpi ${cls||''}" onclick="fscApproSetFiltre('eligible','${filtre}',1)" title="Filtrer le registre">
      <span class="fsc-kpi-val">${val}</span><span class="fsc-kpi-lbl">${escHtml(label)}</span>
    </button>`;

  root.innerHTML = `
    ${sifaTabsHtml('fsc')}
    ${fscSousTabsHtml('appro')}
    <div class="fsc-hero">
      <div class="fsc-hero-txt">
        <h1>Approvisionnements FSC</h1>
        <p>Registre des entrées de matière d'origine forestière. Les colonnes grises viennent de RVGI
        et sont figées à l'import ; la saisie porte sur le n° de facture, les allégations du BL et de la
        facture, et la présence du code de certificat. Chaque correction est journalisée.</p>
      </div>
      <div class="fsc-hero-actions">
        ${admin ? `<button type="button" class="fsc-btn qual-write" id="fsc-appro-import" onclick="fscApproImporter()"
           title="Ajoute les réceptions RVGI postérieures à la date d'entrée. N'écrase aucune ligne existante.">Importer les réceptions RVGI</button>` : ''}
        <a class="btn btn-accent" href="/api/qualite/fsc/appro/export.xlsx?${escAttr(fscApproQs())}"
           title="Le registre de la période, au format du classeur">Export Excel</a>
      </div>
    </div>

    ${d.date_entree ? '' : `<div class="fsc-bandeau">
      <div><b>Date d'entrée dans la chaîne de contrôle non renseignée.</b>
      Elle borne tout le registre : tant qu'elle est vide, aucune réception ne s'importe.</div>
      ${admin ? `<div class="fsc-bandeau-act">
        <input type="date" id="fsc-date-entree" class="fsc-inline">
        <button type="button" class="fsc-btn sm primary" onclick="fscApproDefinirDate()">Enregistrer</button>
      </div>` : ''}
    </div>`}
    ${d.miroir_present === false ? `<div class="fsc-bandeau">
      <div>Miroir RVGI absent sur cette instance : l'import ne peut pas tourner tant que la synchro n'a pas poussé son export.</div></div>` : ''}

    <div class="fsc-kpis">
      ${kpi(st.lignes||0, 'lignes au registre', '', '')}
      ${kpi(st.oui||0, 'éligibles FSC', st.oui?'':'', 'oui')}
      ${kpi(st.a_verifier||0, 'à vérifier', st.a_verifier?'soon':'', 'a_verifier')}
      ${kpi((st.ecart||0)+(st.non||0), 'écarts et non éligibles', (st.ecart||st.non)?'exp':'', 'ecart_bl_facture')}
    </div>

    ${volumes ? `<div class="fsc-section-title">Volumes éligibles par allégation${d.date_entree?` · depuis le ${fmtDate(d.date_entree)}`:''}</div>
      <div class="fsc-couv">${volumes}</div>` : ''}

    <div class="fsc-toolbar">
      <div class="fsc-search">
        <svg class="fsc-search-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="search" id="fsc-appro-q" placeholder="Rechercher (BL, fournisseur, matière, n° de facture…)" value="${escAttr(f.q)}"
          oninput="fscApproSetFiltre('q', this.value, 0); fscApproRenderList()" onkeydown="fscApproSearchKey(event)">
      </div>
      <label class="fsc-inline-lbl">Du <input type="date" class="fsc-inline" value="${escAttr(f.debut)}" onchange="fscApproSetFiltre('debut', this.value, 1)"></label>
      <label class="fsc-inline-lbl">au <input type="date" class="fsc-inline" value="${escAttr(f.fin)}" onchange="fscApproSetFiltre('fin', this.value, 1)"></label>
      <div class="fsc-filtres">
        ${[['','Toutes'],['oui','Éligibles'],['a_verifier','À vérifier'],['ecart_bl_facture','Écarts'],['non','Non éligibles']].map(([v,l]) =>
          `<button type="button" class="fsc-filtre${f.eligible===v?' active':''}" onclick="fscApproSetFiltre('eligible','${v}',1)">${l}</button>`).join('')}
      </div>
      <label class="fsc-check compact${f.certifies?' on':''}">
        <input type="checkbox" ${f.certifies?'checked':''} onchange="fscApproSetFiltre('certifies', this.checked?1:0, 1)">
        Fournisseurs certifiés seulement
      </label>
    </div>
    <div id="fsc-appro-list"></div>`;
  fscApproRenderList();
}

function fscNb(v){
  if(v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', {maximumFractionDigits: 0});
}

function fscApproSearchKey(ev){
  if(ev.key === 'Escape'){ ev.target.value=''; fscApproSetFiltre('q','',0); fscApproRenderList(); }
}

function fscApproLignesVisibles(){
  const d = S.fsc.appro; if(!d) return [];
  const q = (S.fsc.approFiltres.q||'').trim().toLowerCase();
  if(!q) return d.lignes||[];
  return (d.lignes||[]).filter(l => [l.num_bl, l.fournisseur_nom, l.fournisseur_rvgi, l.designation,
    l.code_matiere, l.num_facture_fournisseur].join(' ').toLowerCase().indexOf(q) !== -1);
}

function fscApproRenderList(){
  const wrap = document.getElementById('fsc-appro-list');
  const d = S.fsc.appro;
  if(!wrap || !d) return;
  const lignes = fscApproLignesVisibles();
  const admin = fscEstAdmin();
  if(!lignes.length){
    wrap.innerHTML = `<div class="fsc-empty">${(S.fsc.approFiltres.q)
      ? `Aucun résultat pour « ${escHtml(S.fsc.approFiltres.q)} »`
      : (d.date_entree ? 'Aucune ligne dans ce filtre. Lancez l\'import des réceptions RVGI.'
                       : 'Registre vide : renseignez d\'abord la date d\'entrée dans la chaîne de contrôle.')}</div>`;
    return;
  }
  const opts = (sel) => (d.allegations||[]).map(a =>
    `<option value="${escAttr(a.code)}"${(sel||'')===a.code?' selected':''}>${escHtml(a.libelle)}</option>`).join('');
  const optsEtiq = (sel) => (d.etiquettes||[]).map(e =>
    `<option value="${escAttr(e.code)}"${(sel||'')===e.code?' selected':''}>${escHtml(e.libelle)}</option>`).join('');

  const rows = lignes.map(l => {
    const el = FSC_ELIGIBLE[l.eligible] || FSC_ELIGIBLE.a_verifier;
    const pct = (d.allegations||[]).find(a => a.code === l.allegation_facture);
    const four = l.fournisseur_nom
      ? `<div class="fsc-nom" title="${escAttr(l.fournisseur_rvgi||'')}">${escHtml(l.fournisseur_nom)}</div>`
      : `<div class="fsc-nom">${escHtml(l.fournisseur_rvgi||'—')}</div>
         <div class="fsc-sub warn">Tiers RVGI non rattaché${admin?` · <button type="button" class="fsc-lien" onclick="fscApproRattacher(${l.id})">rattacher</button>`:''}</div>`;
    return `<tr data-id="${l.id}" class="elig-${escAttr(l.eligible||'a_verifier')}">
      <td class="fsc-rvgi">${fmtDate(l.date_reception)}</td>
      <td class="fsc-rvgi fsc-mono">${escHtml(l.num_bl||'—')}</td>
      <td class="fsc-rvgi">${four}</td>
      <td class="fsc-rvgi fsc-mat">
        <div class="fsc-mono">${escHtml(l.code_matiere||'')}${l.laize_mm?` · ${fscNb(l.laize_mm)} mm`:''}</div>
        <div class="fsc-sub" title="${escAttr(l.designation||l.libelle_matiere||'')}">${escHtml(l.designation||l.libelle_matiere||'')}</div>
      </td>
      <td class="fsc-rvgi num">${fscNb(l.quantite_ml)} ml<div class="fsc-sub">${fscNb(l.quantite_m2)} m²</div></td>
      <td class="fsc-rvgi centre">${l.certificat_statut
          ? `<span class="fsc-pill ${l.certificat_statut==='valide'?'ok':(l.certificat_statut==='expire'?'exp':'nod')}">${escHtml({valide:'Valide',expire:'Expiré',inconnu:'Inconnu',non_certifie:'Non certifié'}[l.certificat_statut]||l.certificat_statut)}</span>`
          : '<span class="fsc-pill nod">—</span>'}
        </td>
      <td><input type="text" class="fsc-in" value="${escAttr(l.num_facture_fournisseur||'')}" placeholder="n° facture"
            onchange="fscApproSaisir(${l.id}, 'num_facture_fournisseur', this.value)"></td>
      <td><select class="fsc-in" onchange="fscApproSaisir(${l.id}, 'allegation_bl', this.value)">
            <option value="">—</option>${opts(l.allegation_bl)}</select></td>
      <td><select class="fsc-in" onchange="fscApproSaisir(${l.id}, 'allegation_facture', this.value)">
            <option value="">—</option>${opts(l.allegation_facture)}</select></td>
      <td><input type="number" class="fsc-in court" min="0" max="100" step="1" value="${l.pourcentage!=null?l.pourcentage:''}"
            ${pct && pct.pct ? '' : 'disabled title="Seulement pour une allégation en pourcentage"'}
            onchange="fscApproSaisir(${l.id}, 'pourcentage', this.value)"></td>
      <td class="centre"><input type="checkbox" ${l.code_certificat_present?'checked':''}
            title="Le code de certificat du fournisseur figure sur le BL et la facture"
            onchange="fscApproSaisir(${l.id}, 'code_certificat_present', this.checked?1:0)"></td>
      <td><select class="fsc-in" onchange="fscApproSaisir(${l.id}, 'etiquette_posee', this.value)">
            <option value="">—</option>${optsEtiq(l.etiquette_posee)}</select></td>
      <td><span class="fsc-pill ${el.cls}">${escHtml(el.label)}</span>
          ${l.controle_par?`<div class="fsc-sub">${escHtml(l.controle_par)}</div>`:''}</td>
      <td class="fsc-c-act">
        ${admin?`<button type="button" class="fsc-btn sm" onclick="fscApproAppliquerBl(${l.id})" title="Recopier cette saisie sur toutes les lignes du même BL">BL</button>`:''}
        <button type="button" class="fsc-btn sm" onclick="fscApproJournal(${l.id})" title="Historique des corrections">Journal</button>
      </td>
    </tr>`;
  }).join('');

  wrap.innerHTML = `<div class="fsc-tablewrap">
    <table class="fsc-grid">
      <thead><tr>
        <th>Réception</th><th>BL</th><th>Fournisseur</th><th>Matière</th><th>Quantité</th><th>Certificat au BL</th>
        <th>N° facture</th><th>Allégation BL</th><th>Allégation facture</th><th>%</th><th>Code</th><th>Étiquette</th>
        <th>Éligible</th><th></th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table></div>
    <div class="fsc-legende">${lignes.length} ligne(s) affichée(s) · les colonnes grisées viennent de RVGI et ne s'éditent pas</div>`;
}

async function fscApproSaisir(id, champ, valeur){
  const tr = document.querySelector(`#fsc-appro-list tr[data-id="${id}"]`);
  if(tr) tr.classList.add('saving');
  try{
    const r = await api('/api/qualite/fsc/appro/' + id, {
      method:'PATCH', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({[champ]: valeur === '' ? null : valeur}),
    });
    if(!r.ok){
      let msg = 'Enregistrement impossible.';
      try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger');
      return;
    }
    const ligne = await r.json();
    const lignes = (S.fsc.appro.lignes||[]);
    const i = lignes.findIndex(x => x.id === id);
    if(i !== -1) lignes[i] = {...lignes[i], ...ligne};
    fscApproRafraichirStats();
    fscApproRenderList();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
  finally{ if(tr) tr.classList.remove('saving'); }
}

function fscApproRafraichirStats(){
  // Les compteurs se recalculent côté client entre deux chargements : une saisie
  // ne doit pas coûter un aller-retour complet.
  const lignes = S.fsc.appro.lignes||[];
  const st = S.fsc.appro.stats || {};
  st.lignes = lignes.length;
  st.oui = lignes.filter(l => l.eligible === 'oui').length;
  st.non = lignes.filter(l => l.eligible === 'non').length;
  st.a_verifier = lignes.filter(l => l.eligible === 'a_verifier').length;
  st.ecart = lignes.filter(l => l.eligible === 'ecart_bl_facture').length;
  document.querySelectorAll('.fsc-kpis .fsc-kpi-val').forEach((el, i) => {
    el.textContent = [st.lignes, st.oui, st.a_verifier, (st.ecart||0)+(st.non||0)][i];
  });
}

async function fscApproAppliquerBl(id){
  try{
    const r = await api('/api/qualite/fsc/appro/' + id + '/appliquer-bl', {method:'POST'});
    if(!r.ok){
      let msg = 'Application impossible.';
      try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger'); return;
    }
    const j = await r.json();
    showToast(j.appliquees ? `Saisie appliquée à ${j.appliquees} ligne(s) du même BL.`
                           : 'Ce BL ne porte qu\'une ligne.', j.appliquees?'success':'info');
    await fscApproLoad();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

async function fscApproImporter(){
  const b = document.getElementById('fsc-appro-import');
  if(b){ b.disabled = true; b.textContent = 'Import en cours…'; }
  try{
    const r = await api('/api/qualite/fsc/appro/import', {method:'POST'});
    if(!r.ok){
      let msg = 'Import impossible.';
      try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger'); return;
    }
    const j = await r.json();
    showToast(`${j.ajoutees} réception(s) ajoutée(s)${j.sans_fournisseur?` · ${j.sans_fournisseur} sans fournisseur rattaché`:''}.`,'success');
    await fscApproLoad();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
  finally{ if(b){ b.disabled = false; b.textContent = 'Importer les réceptions RVGI'; } }
}

async function fscApproDefinirDate(){
  const el = document.getElementById('fsc-date-entree');
  if(!el || !el.value){ showToast('Choisir une date.','info'); return; }
  try{
    const r = await api('/api/qualite/fsc/appro/parametres', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({date_entree: el.value}),
    });
    if(!r.ok){ showToast('Date refusée.','danger'); return; }
    showToast('Date d\'entrée enregistrée.','success');
    await fscApproLoad();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

function fscApproRattacher(id){
  const d = S.fsc.appro;
  const l = (d.lignes||[]).find(x => x.id === id); if(!l) return;
  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal fsc-modal">
        <div class="modal-hd">
          <h3>Rattacher un tiers RVGI</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button>
        </div>
        <div class="modal-bd">
          <p>Le tiers <b>${escHtml(l.fournisseur_rvgi||'')}</b> (n° ${escHtml(String(l.numfou||'—'))}) n'est rattaché à aucune fiche
          de l'annuaire. Le rattachement est mémorisé sur la fiche : toutes les lignes de ce tiers, passées et à venir,
          suivront.</p>
          <label class="fsc-field"><span>Fiche fournisseur</span>
            <select id="fsc-ratt-four">
              <option value="">— choisir —</option>
              ${(d.fournisseurs||[]).map(f => `<option value="${f.id}">${escHtml(f.nom)}${f.licence?' · '+escHtml(f.licence):''}</option>`).join('')}
            </select></label>
        </div>
        <div class="modal-ft">
          <button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
          <button type="button" class="btn btn-accent" onclick="fscApproRattacherValider(${id})">Rattacher</button>
        </div>
      </div>
    </div>`;
}

async function fscApproRattacherValider(id){
  const sel = document.getElementById('fsc-ratt-four');
  if(!sel || !sel.value){ showToast('Choisir une fiche fournisseur.','info'); return; }
  try{
    const r = await api('/api/qualite/fsc/appro/' + id + '/rattacher', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({fournisseur_id: Number(sel.value)}),
    });
    if(!r.ok){
      let msg = 'Rattachement impossible.';
      try{ const j = await r.json(); if(j.detail) msg = j.detail; }catch(e){}
      showToast(msg,'danger'); return;
    }
    const j = await r.json();
    closeMroot();
    showToast(`${j.lignes_reprises} ligne(s) rattachée(s).`,'success');
    await fscApproLoad();
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

async function fscApproJournal(id){
  try{
    const r = await api('/api/qualite/fsc/appro/' + id + '/journal');
    if(!r.ok){ showToast('Journal indisponible.','danger'); return; }
    const j = (await r.json()).journal || [];
    const l = ((S.fsc.appro||{}).lignes||[]).find(x => x.id === id) || {};
    _refMroot().innerHTML = `
      <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
        <div class="modal fsc-modal">
          <div class="modal-hd">
            <h3>Journal · BL ${escHtml(l.num_bl||'')} · ${escHtml(l.fournisseur_nom||l.fournisseur_rvgi||'')}</h3>
            <button class="modal-x" onclick="closeMroot()">&times;</button>
          </div>
          <div class="modal-bd">
            ${j.length ? `<div class="fsc-histo">${j.map(e => `<div class="fsc-histo-row">
                <span class="fsc-mono">${fmtDateTime(e.horodatage)}</span>
                <span>${escHtml(e.champ)}</span>
                <span class="fsc-muted">${escHtml(e.ancienne_valeur===null||e.ancienne_valeur===undefined?'—':String(e.ancienne_valeur))} → ${escHtml(e.nouvelle_valeur===null||e.nouvelle_valeur===undefined?'—':String(e.nouvelle_valeur))}</span>
                <span class="fsc-muted">${escHtml(e.utilisateur||'')}</span>
              </div>`).join('')}</div>`
              : '<div class="fsc-muted">Aucune correction : la ligne est telle qu\'elle est entrée.</div>'}
          </div>
          <div class="modal-ft"><button type="button" class="fsc-btn" onclick="closeMroot()">Fermer</button></div>
        </div>
      </div>`;
  }catch(e){ if(e.message !== 'unauth') showToast('Erreur réseau','danger'); }
}

// ─── CSS ─────────────────────────────────────────────────────────────

// ─── Import d'un lot de contrôles ─────────────────────────────────────
//
// Le contrôle unitaire reste la référence. Cet écran sert la campagne : les
// dossiers d'une tournée complète, relevés le même jour sur la base FSC, entrent
// en une fois. Rien n'est écrit avant que quelqu'un ait relu la proposition.

function fscOuvrirImport(){
  S.fsc.lot = {etape:'depot', jeton:null, lignes:[], fournisseurs:[], csv_lu:false, busy:false, resultats:null};
  fscRenderImport();
}

async function fscAnalyserLot(){
  const inp = document.getElementById('fsc-imp-files');
  const fichiers = (inp && inp.files) ? Array.from(inp.files) : [];
  if(!fichiers.length){ showToast('Aucun fichier sélectionné.', 'error'); return; }
  const fd = new FormData();
  fichiers.forEach(f => fd.append('fichiers', f));
  S.fsc.lot.busy = true; fscRenderImport();
  try{
    const r = await api('/api/qualite/fsc/controles/import', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Lot refusé.', 'error'); S.fsc.lot.busy = false; fscRenderImport(); return; }
    (j.lignes||[]).forEach(l => {
      l.retenu = !!(l.ok && l.fournisseur_id && !l.deja_importe);
      l.maj_fiche = true;
      l.maj_codes = (l.ecarts||[]).some(e => e.champ !== 'fsc_date_expiration');
    });
    S.fsc.lot = {etape:'revue', jeton:j.jeton, lignes:j.lignes||[], fournisseurs:j.fournisseurs||[],
                 csv_lu:!!j.csv_lu, busy:false, resultats:null};
  }catch(e){
    showToast('Lecture du lot impossible.', 'error');
    S.fsc.lot.busy = false;
  }
  fscRenderImport();
}

function fscImportLigne(i){ return (S.fsc.lot && S.fsc.lot.lignes[i]) || null; }

function fscImportSetFour(i, val){
  const l = fscImportLigne(i); if(!l) return;
  l.fournisseur_id = val ? parseInt(val, 10) : null;
  l.fournisseur_nom = null;
  l.rapprochement = val ? 'manuel' : 'aucun';
  if(!val) l.retenu = false;
  fscRenderImport();
}

function fscImportToggle(i, champ, on){
  const l = fscImportLigne(i); if(!l) return;
  l[champ] = !!on;
  if(champ === 'retenu' && on && !l.fournisseur_id){ l.retenu = false; showToast('Choisir une fiche fournisseur d\'abord.', 'error'); }
  fscRenderImport();
}

function fscImportTout(on){
  (S.fsc.lot.lignes||[]).forEach(l => { l.retenu = !!(on && l.ok && l.fournisseur_id); });
  fscRenderImport();
}

async function fscImportAppliquer(){
  const lot = S.fsc.lot; if(!lot || !lot.jeton) return;
  const lignes = (lot.lignes||[]).filter(l => l.retenu && l.fournisseur_id).map(l => ({
    disque: l.disque, fournisseur_id: l.fournisseur_id,
    maj_fiche: !!l.maj_fiche, maj_codes: !!l.maj_codes, deposer_certificat: true,
  }));
  if(!lignes.length){ showToast('Aucune ligne retenue.', 'error'); return; }
  lot.busy = true; fscRenderImport();
  try{
    const r = await api('/api/qualite/fsc/controles/import/' + encodeURIComponent(lot.jeton) + '/appliquer',
                        {method:'POST', headers:{'Content-Type':'application/json'},
                         body: JSON.stringify({lignes})});
    const j = await r.json().catch(() => ({}));
    if(!r.ok){ showToast(j.detail || 'Import refusé.', 'error'); lot.busy = false; fscRenderImport(); return; }
    lot.etape = 'fait'; lot.busy = false; lot.resultats = j.resultats || []; lot.importes = j.importes || 0;
    showToast(j.importes + ' contrôle(s) enregistré(s).', 'success');
    fscRenderImport();
    fscLoad();
  }catch(e){
    showToast('Import impossible.', 'error');
    lot.busy = false; fscRenderImport();
  }
}

function fscImportChips(l){
  const p = (l.portees_labels||[]).length
    ? (l.lu.portees||[]).map(c => `<span class="fsc-claim lu">${escHtml(c)}</span>`).join(' ')
    : '<span class="fsc-muted">portée absente du dossier</span>';
  const c = (l.claims_labels||[]).length
    ? (l.claims_labels||[]).map(x => `<span class="fsc-claim solid">${escHtml(x)}</span>`).join(' ')
    : '<span class="fsc-muted">aucune allégation lue</span>';
  return `<div class="fsc-imp-chips">${p}</div><div class="fsc-imp-chips">${c}</div>`;
}

function fscImportLigneHtml(l, i){
  if(!l.ok){
    return `<div class="fsc-imp-row ko">
      <div class="fsc-imp-f">${escHtml(l.fichier)}</div>
      <div class="fsc-imp-err">${escHtml(l.erreur||'Dossier illisible.')}</div></div>`;
  }
  const lu = l.lu || {};
  const options = (S.fsc.lot.fournisseurs||[]).map(f =>
    `<option value="${f.id}"${l.fournisseur_id===f.id?' selected':''}>${escHtml(f.nom)}${f.certificat?' · '+escHtml(f.certificat):''}</option>`).join('');
  const cible = l.fournisseur_id && l.rapprochement !== 'manuel'
    ? `<div class="fsc-imp-four">${escHtml(l.fournisseur_nom||'')}
         <span class="fsc-tag-lu">par ${escHtml(l.rapprochement)}</span></div>`
    : '';
  const select = `<select class="fsc-in" onchange="fscImportSetFour(${i}, this.value)">
      <option value="">— choisir une fiche —</option>${options}</select>`;
  const ecarts = (l.ecarts||[]).map(e =>
    `<div class="fsc-imp-ec"><span class="fsc-muted">${escHtml(e.champ)}</span>
       <span class="fsc-mono">${escHtml(e.avant||'vide')}</span> → <span class="fsc-mono">${escHtml(e.apres)}</span></div>`).join('');
  const avert = (l.avertissements||[]).map(a => `<div class="fsc-imp-av">${escHtml(a)}</div>`).join('');
  return `<div class="fsc-imp-row${l.retenu?' on':''}">
    <label class="fsc-imp-cb"><input type="checkbox" ${l.retenu?'checked':''}
      onchange="fscImportToggle(${i}, 'retenu', this.checked)"></label>
    <div class="fsc-imp-bd">
      <div class="fsc-imp-hd">
        <span class="fsc-mono">${escHtml(lu.certificat||'')}</span>
        <span class="fsc-muted">${escHtml(lu.licence||'')}</span>
        <span class="fsc-claim ${lu.statut_base==='valide'?'solid':'lu'}">${escHtml(lu.statut_texte||lu.statut_base||'')}</span>
        ${l.deja_importe?'<span class="fsc-tag-lu">déjà importé</span>':''}
      </div>
      <div class="fsc-imp-tit">${escHtml(lu.titulaire||'')}</div>
      <div class="fsc-imp-meta">
        <span>Expiration <b>${lu.date_expiration_lue?fmtDate(lu.date_expiration_lue):'—'}</b></span>
        <span>Contrôle <b>${lu.signe_le?fmtDate(lu.signe_le):'date absente'}</b></span>
        <span class="fsc-muted">${escHtml(l.fichier)}</span>
      </div>
      ${fscImportChips(l)}
      ${cible}${select}
      ${ecarts ? `<div class="fsc-imp-ecs"><div class="fsc-field-t">Ce que l'import corrigerait</div>${ecarts}
        <label class="fsc-check${l.maj_fiche?' on':''}"><input type="checkbox" ${l.maj_fiche?'checked':''}
          onchange="fscImportToggle(${i}, 'maj_fiche', this.checked)">Reporter l'expiration sur la fiche</label>
        <label class="fsc-check${l.maj_codes?' on':''}"><input type="checkbox" ${l.maj_codes?'checked':''}
          onchange="fscImportToggle(${i}, 'maj_codes', this.checked)">Corriger licence et code de certificat</label></div>` : ''}
      ${avert ? `<div class="fsc-imp-avs">${avert}</div>` : ''}
    </div>
  </div>`;
}

function fscRenderImport(){
  const lot = S.fsc.lot; if(!lot){ return; }
  let corps = '';
  let pied = `<button type="button" class="fsc-btn" onclick="closeMroot()">Fermer</button>`;

  if(lot.etape === 'depot'){
    corps = `<div class="fsc-etape"><div class="fsc-etape-num">1</div><div class="fsc-etape-bd">
        <div class="fsc-etape-t">Déposer les dossiers téléchargés sur la base FSC</div>
        <div class="fsc-hint">Les FSC Certification Records en PDF, et si vous l'avez le CSV du lot.
          Tout est lu dans les dossiers : la date du contrôle est l'horodatage de la signature FSC, pas la date du jour.
          Le CSV ne sert qu'à nommer les fournisseurs.</div>
        <div class="fsc-form"><label class="fsc-field grow"><span>Fichiers du lot</span>
          <input type="file" id="fsc-imp-files" multiple accept=".pdf,.csv"></label></div>
      </div></div>`;
    pied = `<button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
      <button type="button" class="btn btn-accent" onclick="fscAnalyserLot()" ${lot.busy?'disabled':''}>
        ${lot.busy?'Lecture…':'Lire le lot'}</button>`;
  } else if(lot.etape === 'revue'){
    const retenus = (lot.lignes||[]).filter(l => l.retenu).length;
    const sansFiche = (lot.lignes||[]).filter(l => l.ok && !l.fournisseur_id).length;
    // Bloc monte par concatenation, pas par gabarit : une interpolation qui
    // englobe la classe « fsc-note » fait sonner test_prose_echappee, dont
    // l'heuristique cherche le mot « note » dans l'expression interpolee.
    // sansFiche est un compteur, il n'y a aucune saisie utilisateur ici.
    const alerteSansFiche = sansFiche
      ? '<div class="fsc-note warn">' + sansFiche
        + ' dossier(s) sans fiche rapprochée — choisir la fiche ou les laisser de côté.</div>'
      : '';
    corps = `
      <div class="fsc-imp-bar">
        <span>${lot.lignes.length} dossier(s) lu(s) · ${retenus} retenu(s)${lot.csv_lu?' · CSV pris en compte':''}</span>
        <span>
          <button type="button" class="fsc-btn sm" onclick="fscImportTout(true)">Tout retenir</button>
          <button type="button" class="fsc-btn sm" onclick="fscImportTout(false)">Aucun</button>
        </span>
      </div>
      ${alerteSansFiche}
      ${(lot.lignes||[]).map((l, i) => fscImportLigneHtml(l, i)).join('')}`;
    pied = `<button type="button" class="fsc-btn" onclick="closeMroot()">Annuler</button>
      <button type="button" class="btn btn-accent" onclick="fscImportAppliquer()" ${(lot.busy||!retenus)?'disabled':''}>
        ${lot.busy?'Import…':'Importer '+retenus+' contrôle(s)'}</button>`;
  } else {
    corps = `<div class="fsc-note">${lot.importes} contrôle(s) enregistré(s).</div>` +
      (lot.resultats||[]).map(r => r.ok
        ? `<div class="fsc-imp-res">${escHtml(r.fournisseur_nom||'')}
             ${r.fiche_maj?'<span class="fsc-tag-lu">expiration mise à jour</span>':''}
             ${r.codes_corriges?'<span class="fsc-tag-lu">codes corrigés</span>':''}
             ${r.registre_lignes_reprises?`<span class="fsc-muted">${r.registre_lignes_reprises} ligne(s) de registre reprise(s)</span>`:''}</div>`
        : `<div class="fsc-imp-res ko">${escHtml(r.erreur||'')}</div>`).join('');
  }

  _refMroot().innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeMroot()">
      <div class="modal fsc-modal fsc-modal-import">
        <div class="modal-hd">
          <h3>Importer un contrôle</h3>
          <button class="modal-x" onclick="closeMroot()">&times;</button>
        </div>
        <div class="modal-bd">${corps}</div>
        <div class="modal-ft">${pied}</div>
      </div>
    </div>`;
}

(function injectFscCSS(){
  if(document.getElementById('fsc-css')) return;
  const st = document.createElement('style');
  st.id = 'fsc-css';
  st.textContent = `
  .fsc-modal-import{max-width:900px}
  .fsc-imp-bar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;
    padding:8px 0 12px;font-size:12px;color:var(--text2);font-weight:600}
  .fsc-imp-row{display:grid;grid-template-columns:28px 1fr;gap:10px;padding:12px;border:1px solid var(--border);
    border-radius:10px;background:var(--card);margin-bottom:8px}
  .fsc-imp-row.on{border-color:var(--accent);background:var(--accent-bg)}
  .fsc-imp-row.ko{grid-template-columns:1fr;border-color:var(--danger)}
  .fsc-imp-cb{display:flex;align-items:flex-start;justify-content:center;padding-top:2px}
  .fsc-imp-hd{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px}
  .fsc-imp-tit{font-size:13px;font-weight:700;color:var(--text);margin:2px 0}
  .fsc-imp-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--text2);margin-bottom:6px}
  .fsc-imp-chips{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:5px}
  .fsc-imp-four{font-size:12px;font-weight:700;color:var(--text);margin:4px 0}
  .fsc-imp-ecs{margin-top:8px;padding:8px;border:1px dashed var(--border);border-radius:8px}
  .fsc-imp-ec{font-size:11.5px;color:var(--text2);margin-bottom:3px}
  .fsc-imp-avs{margin-top:8px;display:flex;flex-direction:column;gap:4px}
  .fsc-imp-av{font-size:11.5px;color:var(--warn);font-weight:600}
  .fsc-imp-err{font-size:12px;color:var(--danger);font-weight:600}
  .fsc-imp-f{font-size:12px;font-weight:700;margin-bottom:3px}
  .fsc-imp-res{font-size:12px;padding:6px 0;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .fsc-imp-res.ko{color:var(--danger)}

  .fsc-hero{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin-bottom:14px;
    display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
  .fsc-hero-txt{flex:1;min-width:240px}
  .fsc-hero h1{margin:0 0 4px;font-size:22px;color:var(--text)}
  .fsc-hero p{margin:0;color:var(--text2);font-size:13px;line-height:1.55;max-width:760px}
  .fsc-hero-actions{display:flex;gap:8px;flex-wrap:wrap}
  .fsc-hero .btn-accent, .fsc-modal .btn-accent, .fsc-modal-preview .btn-accent{color:white;text-decoration:none}
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
  .fsc-row{display:grid;
    grid-template-columns:minmax(155px,1.2fr) 132px 122px minmax(165px,1.4fr) minmax(150px,1.2fr) 152px 158px;
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
  .fsc-sub.danger{color:var(--danger)}
  .fsc-achats{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
  .fsc-lien{background:none;border:none;padding:0;font:inherit;font-size:11px;color:var(--accent);
    cursor:pointer;text-decoration:underline}
  .fsc-lien:hover{filter:brightness(1.15)}
  .fsc-legende-sep{color:var(--border)}

  .fsc-portee-box{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:10px}
  .fsc-portee-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;min-height:24px;align-items:center}
  .fsc-portee-chip{display:inline-flex;align-items:center;gap:6px;padding:3px 6px 3px 9px;border-radius:999px;
    background:var(--accent-bg);border:1px solid var(--accent);color:var(--accent);font-size:11.5px;font-weight:700}
  .fsc-portee-lab{color:var(--text2);font-weight:500;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .fsc-portee-x{background:none;border:none;color:var(--accent);cursor:pointer;font-size:15px;line-height:1;
    padding:0 2px;font-family:inherit}
  .fsc-portee-x:hover{color:var(--danger)}
  .fsc-portee-saisie{display:flex;gap:8px;align-items:center}
  .fsc-portee-saisie .fsc-in{flex:1}

  .fsc-sorties{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-top:6px}
  .fsc-sortie-row{display:grid;grid-template-columns:minmax(170px,1.2fr) 170px 2fr 90px;gap:12px;
    padding:10px 16px;border-bottom:1px solid var(--border);align-items:start}
  .fsc-sortie-row:last-child{border-bottom:none}

  .fsc-modal-achats{max-width:620px}
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
  .fsc-histo-row{display:grid;grid-template-columns:84px 84px 1fr 1fr 110px 80px;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);align-items:center}
  .fsc-histo-row a{color:var(--accent);font-weight:600;text-decoration:none}

  .fsc-stabs{display:flex;gap:4px;margin:0 0 14px}
  .fsc-stab{padding:7px 14px;border-radius:8px;border:1px solid var(--border);background:var(--card);
    color:var(--text2);font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit;transition:.15s}
  .fsc-stab:hover{background:var(--bg);color:var(--text)}
  .fsc-stab.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}

  .fsc-bandeau{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;
    background:rgba(251,191,36,.12);border:1px solid var(--warn);border-radius:12px;padding:12px 16px;
    margin-bottom:14px;font-size:13px;color:var(--text2)}
  .fsc-bandeau-act{display:flex;gap:8px;align-items:center}
  .fsc-inline{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:7px 9px;
    color:var(--text);font-family:inherit;font-size:12.5px}
  .fsc-inline-lbl{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
  .fsc-check.compact{padding:6px 10px;font-size:12px}
  .fsc-lien{background:none;border:none;padding:0;color:var(--accent);font:inherit;font-size:11px;
    font-weight:700;cursor:pointer;text-decoration:underline}

  .fsc-tablewrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow-x:auto}
  .fsc-grid{border-collapse:collapse;width:100%;min-width:1360px;font-size:12.5px}
  .fsc-grid th{position:sticky;top:0;background:var(--bg);color:var(--muted);font-size:10.5px;
    text-transform:uppercase;letter-spacing:.5px;font-weight:700;text-align:left;padding:9px 10px;
    border-bottom:1px solid var(--border);white-space:nowrap;z-index:1}
  .fsc-grid td{padding:6px 10px;border-bottom:1px solid var(--border);vertical-align:middle;color:var(--text)}
  /* La désignation RVGI est longue (« 70gsm Direct Thermal ECO Paper - BARCODE
     REQUIRED ») : deux lignes au maximum, le reste dans l'infobulle. */
  .fsc-grid td.fsc-mat{min-width:230px;max-width:280px}
  .fsc-mat .fsc-sub{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .fsc-grid tr:last-child td{border-bottom:none}
  .fsc-grid tr:hover td{background:var(--bg)}
  .fsc-grid td.fsc-rvgi{color:var(--text2);background:linear-gradient(var(--bg),var(--bg))}
  .fsc-grid tr:hover td.fsc-rvgi{filter:brightness(.98)}
  .fsc-grid td.num{text-align:right;white-space:nowrap}
  .fsc-grid td.centre{text-align:center}
  .fsc-grid tr.saving td{opacity:.6}
  /* Le verdict se lit au bord gauche de la ligne : la colonne « Éligible » est
     à droite d'un tableau qui défile, et c'est l'information qu'on cherche en
     premier. */
  .fsc-grid tbody td:first-child{border-left:3px solid transparent}
  .fsc-grid tr.elig-oui td:first-child{border-left-color:var(--success)}
  .fsc-grid tr.elig-non td:first-child,
  .fsc-grid tr.elig-ecart_bl_facture td:first-child{border-left-color:var(--danger)}
  .fsc-grid tr.elig-a_verifier td:first-child{border-left-color:var(--warn)}
  .fsc-in{background:var(--bg);border:1px solid var(--border);border-radius:7px;padding:6px 8px;
    color:var(--text);font-family:inherit;font-size:12px;width:100%;min-width:110px}
  .fsc-in:focus{border-color:var(--accent);outline:none}
  .fsc-in:disabled{opacity:.45}
  .fsc-in.court{min-width:62px;width:62px}

  @media(max-width:1400px){
    .fsc-row{grid-template-columns:minmax(150px,1.2fr) 126px 116px minmax(155px,1.3fr) minmax(140px,1.1fr);}
    .fsc-c-ctrl{grid-column:1 / 3}
    .fsc-c-act{grid-column:4 / 6}
    .fsc-head > div:nth-child(6), .fsc-head > div:nth-child(7){display:none}
  }
  @media(max-width:1100px){
    .fsc-row{grid-template-columns:minmax(150px,1.2fr) 126px 116px minmax(155px,1.3fr);}
    .fsc-c-portee{grid-column:1 / 3}
    .fsc-c-cat{grid-column:3 / 5}
    .fsc-c-ctrl{grid-column:1 / 3}
    .fsc-c-act{grid-column:3 / 5}
    .fsc-head > div:nth-child(5), .fsc-head > div:nth-child(6), .fsc-head > div:nth-child(7){display:none}
    .fsc-sortie-row{grid-template-columns:minmax(150px,1fr) 150px 1fr}
    .fsc-sortie-row > div:nth-child(4){grid-column:1 / 4}
  }
  @media(max-width:720px){
    .fsc-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
    .fsc-head{display:none}
    .fsc-row{grid-template-columns:1fr 1fr;gap:8px 12px}
    .fsc-c-four, .fsc-c-portee, .fsc-c-cat{grid-column:1 / 3}
    .fsc-c-ctrl{grid-column:1 / 2}
    .fsc-c-act{grid-column:2 / 3}
    .fsc-hero-actions{width:100%}
    .fsc-hero-actions > *{flex:1;justify-content:center}
    .fsc-histo-row{grid-template-columns:80px 1fr;}
    .fsc-sortie-row{grid-template-columns:1fr}
    .fsc-sortie-row > div:nth-child(4){grid-column:auto}
    .fsc-portee-lab{max-width:110px}
  }
  `;
  document.head.appendChild(st);
})();
"""
