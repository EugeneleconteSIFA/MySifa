/*
 * MySifa — MyQualité : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script principal de app/web/qualite_page.py : ne fait que
 * déclarer des fonctions. init() appelle qualiteDemarrerUrl() en dernier.
 *
 * Inventaire du 20/10/2026, par nom d'état (S.…, S.ged, S.fsc, S.eudr,
 * préférences localStorage) :
 *   vue        menu · audits · ressources · certifications · referentiel
 *              (liste des NC par défaut)
 *   objets     nc, audit, doc (certification), fiche (référentiel),
 *              fournisseur, groupe — chacun implique sa vue
 *   NC         statut, type, gravite ; fiche : onglet
 *   audits     statut ; fiche : onglet, dossier
 *   référentiel categorie, validation ; fiche : question, edition
 *   ressources categorie (multi), certif (multi), rangement, categories_visibles
 *   certifications section (explorateur, fsc, eudr) ;
 *              explorateur : dossier, fichier, corbeille ;
 *              FSC : sous (appro), filtre, debut, fin, eligible, certifies ;
 *              EUDR : filtre, bobines
 *   formulaires filtre (actifs par défaut) ; objet formulaire (éditeur) ;
 *              fenêtre ia_formulaire (nouveau | modifier)
 *   fenêtres   voir _QUAL_OUVREURS — toutes celles de #mroot et les deux
 *              modales fixes (création et import de NC).
 * Hors adresse : textes de recherche, confirmations (suppression), sous-
 * sélecteurs d'un geste (dossier d'une NC, pays manquants d'une génération),
 * visites guidées, fichiers ouverts dans un nouvel onglet.
 *
 * Ancienne forme « /qualite#audits-list » : lue au démarrage (liens du
 * portail, des Paramètres et des widgets), puis réécrite en query.
 */
let _qualUrlPrete = false;
let _qualDemarre = false;
let _qualFen = null;          // {cle, id, vu, depuis} — fenêtre ouverte
let _qualOuvrant = 0;         // ouverture en cours : une fenêtre qui en ouvre une autre ne compte qu'une fois
let _qualNcVisee = null;      // openDetail() passe en vue détail AVANT de charger la NC

const _QUAL_VUES = {
  menu: 'menu', audits: 'audits-list', ressources: 'ressources-list',
  certifications: 'sifa-docs-list', referentiel: 'ref-list',
  formulaires: 'formulaires-list',
};
const _QUAL_VUES_HASH = ['menu', 'list', 'audits-list', 'ressources-list', 'sifa-docs-list', 'ref-list', 'formulaires-list'];
const _QUAL_FORMU_FILTRES = ['actifs', 'brouillon', 'publie', 'archive'];
const _QUAL_SECTIONS = { explorateur: 'explorer', fsc: 'fsc', eudr: 'eudr' };

// [fonction, clé d'adresse, valeur tirée des arguments, conteneur fixe éventuel]
const _QUAL_OUVREURS = [
  ['openCreateModal',              'nouvelle_nc',        () => 'formulaire', 'create-modal'],
  ['openImportModal',              'import_nc',          () => 'formulaire', 'import-modal'],
  ['openCreateAuditModal',         'nouvel_audit',       () => 'formulaire'],
  ['openAddAuditeurPicker',        'ajout_auditeur',     () => (S.currentAudit && S.currentAudit.id)],
  ['openSifaDocGenerate',          'generation',         a => a[1] ? null : a[0]],
  ['openSifaDocEdit',              'version',            a => a[0]],
  ['openTemplateEditor',           'modele',             a => a[0]],
  ['openLinkAuditModal',           'lier_audit',         a => a[0]],
  ['openCreateRefModal',           'nouvelle_fiche',     () => 'formulaire'],
  ['openCertsZipModal',            'zip',                a => a[0]],
  ['openFournisseurSettingsModal', 'reglages',           a => a[0]],
  ['openCertModal',                'certificat',         a => a[0] || 'nouveau'],
  ['openGroupeCertModal',          'certificat_groupe',  a => a[0] || 'nouveau'],
  ['openAuditPickerFournisseurs',  'matrice_fournisseurs', () => (S.currentAudit && S.currentAudit.id)],
  ['openAuditPickerCertifs',       'matrice_certifs',    () => (S.currentAudit && S.currentAudit.id)],
  ['openMatriceCellEditor',        'matrice_case',       a => (a[0] && a[1]) ? a[0] + ':' + a[1] : null],
  ['gedPreview',                   'apercu',             a => a[0]],
  ['gedEditMeta',                  'proprietes',         a => a[0]],
  ['gedFolderProps',               'proprietes_dossier', a => a[0]],
  ['fscOuvrirAchats',              'achats_fsc',         a => a[0]],
  ['fscVoirCertificat',            'certificat_fsc',     a => a[0]],
  ['fscOuvrirControle',            'controle_fsc',       a => a[0]],
  ['fscOuvrirImport',              'import_controles',   () => 'formulaire'],
  ['fscApproRattacher',            'rattacher',          a => a[0]],
  ['fscApproJournal',              'journal',            a => a[0]],
  ['eudrOuvrirSaisie',             'saisie_eudr',        a => a[0]],
  ['eudrOuvrirLiensCommuns',       'liens_eudr',         () => 'liste'],
  ['eudrOuvrirPdf',                'pdf_eudr',           () => 'apercu'],
  ['eudrOuvrirEnvoi',              'envoi_eudr',         () => 'formulaire'],
  ['eudrVoirReponse',              'reponse_eudr',       a => a[0]],
  ['formuIaOuvrir',                'ia_formulaire',      a => a[0] === 'modifier' ? 'modifier' : 'nouveau'],
];
const _qualFixe = cle => { const o = _QUAL_OUVREURS.find(x => x[1] === cle); return o ? o[3] || null : null; };

function qualiteEnvelopper() {
  _QUAL_OUVREURS.forEach(([nom, cle, valeur, fixe]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      if (!_qualOuvrant) {
        let v = null;
        try { v = valeur(arguments); } catch (e) {}
        if (v !== null && v !== undefined && v !== '') {
          _qualFen = { cle, id: String(v), vu: false, depuis: Date.now(), fixe: fixe || null };
        }
      }
      _qualOuvrant++;
      try { return orig.apply(this, arguments); }
      finally { _qualOuvrant--; qualiteSyncUrl(); }
    };
    env.__adresse = true;
    window[nom] = env;
  });
  const od = window.openDetail;
  if (typeof od === 'function' && !od.__adresse) {
    window.openDetail = function (id) { _qualNcVisee = String(id); return od.apply(this, arguments); };
    window.openDetail.__adresse = true;
  }
}

// La fenêtre suivie est-elle toujours à l'écran ? Elle est « vue » dès que
// son conteneur est occupé, et close dès qu'il se vide. Une ouverture qui
// échoue (fiche introuvable) est oubliée au bout de cinq secondes.
function _qualFenetre() {
  const f = _qualFen;
  if (!f) return null;
  let ouverte;
  if (f.fixe) { const m = document.getElementById(f.fixe); ouverte = !!(m && m.style.display && m.style.display !== 'none'); }
  else { const m = document.getElementById('mroot'); ouverte = !!(m && m.childElementCount); }
  if (ouverte) { f.vu = true; return f; }
  if (f.vu || Date.now() - f.depuis > 5000) { _qualFen = null; return null; }
  return f;
}

function qualiteParams() {
  const p = {};
  const v = S.view;
  let nav = v;
  if (v === 'detail') {
    // NC précédente encore en mémoire pendant le chargement : rien à écrire.
    if (!S.current || (_qualNcVisee !== null && String(S.current.id) !== _qualNcVisee)) return null;
    p.nc = S.current.id; nav = 'nc:' + S.current.id;
    if (S.detailTab && S.detailTab !== 'fiche') { p.onglet = S.detailTab; nav += '/' + S.detailTab; }
  } else if (v === 'audits-detail' && S.currentAudit) {
    p.audit = S.currentAudit.id; nav = 'audit:' + S.currentAudit.id;
    if (S.auditDetailTab && S.auditDetailTab !== 'fichiers') { p.onglet = S.auditDetailTab; nav += '/' + S.auditDetailTab; }
    if (S.currentFolderId) { p.dossier = S.currentFolderId; nav += '/d' + S.currentFolderId; }
  } else if (v === 'sifa-docs-detail' && S.currentSifaDoc && S.currentSifaDoc.template) {
    p.doc = S.currentSifaDoc.template.code; nav = 'doc:' + p.doc;
  } else if (v === 'ref-detail' && S.currentRef) {
    p.fiche = S.currentRef.id; nav = 'fiche:' + S.currentRef.id;
    if (S.refOpenQaId) p.question = S.refOpenQaId;
    if (S.refEdit) { p.edition = 1; nav += '/edition'; }
  } else if (v === 'ressources-detail' && S.currentRes && S.currentRes.fournisseur) {
    p.fournisseur = S.currentRes.fournisseur.id; nav = 'fournisseur:' + p.fournisseur;
  } else if (v === 'ressources-group' && S.currentGroupe) {
    p.groupe = S.currentGroupe.groupe; nav = 'groupe:' + p.groupe;
  } else if (v === 'formulaire-edit' && S.formu && S.formu.courant) {
    p.formulaire = S.formu.courant.id; nav = 'formulaire:' + p.formulaire;
  } else {
    const vue = Object.keys(_QUAL_VUES).find(k => _QUAL_VUES[k] === v);
    if (vue) p.vue = vue;
  }
  if (v === 'list') {
    if (S.filterStatut !== 'all') p.statut = S.filterStatut;
    if (S.filterType !== 'all') p.type = S.filterType;
    if (S.filterGravite !== 'all') p.gravite = S.filterGravite;
  } else if (v === 'audits-list') {
    if (S.auditFilterStatut !== 'all') p.statut = S.auditFilterStatut;
  } else if (v === 'formulaires-list' && S.formu) {
    if (S.formu.filtre !== 'actifs') p.filtre = S.formu.filtre;
  } else if (v === 'ref-list') {
    if (S.refFilterCat !== 'all') p.categorie = S.refFilterCat;
    if (S.refFilterStatV !== 'all') p.validation = S.refFilterStatV;
  } else if (v === 'ressources-list') {
    p.categorie = (S.resFiltreCats || []).slice();
    p.certif = (S.resFiltreCertifs || []).slice();
    if (S.resRangement !== 'categorie') p.rangement = S.resRangement;
    if (S.resShowCats) p.categories_visibles = 1;
  } else if (v === 'sifa-docs-list' && S.ged) {
    const t = gedActiveTab();
    const sec = Object.keys(_QUAL_SECTIONS).find(k => _QUAL_SECTIONS[k] === t);
    if (sec) { p.section = sec; nav += '/' + sec; }
    if (t === 'explorer') {
      if (S.ged.mode === 'trash') { p.corbeille = 1; nav += '/corbeille'; }
      else {
        const d = gedCwd(); if (d) { p.dossier = d; nav += '/d' + d; }
        if (S.ged.detail && S.ged.detail.id) { p.fichier = S.ged.detail.id; nav += '/f' + S.ged.detail.id; }
      }
    } else if (t === 'fsc' && S.fsc) {
      if (S.fsc.sousOnglet === 'appro') {
        p.sous = 'appro'; nav += '/appro';
        const f = S.fsc.approFiltres || {};
        if (f.debut) p.debut = f.debut;
        if (f.fin) p.fin = f.fin;
        if (f.eligible) p.eligible = f.eligible;
        if (!f.certifies) p.certifies = 0;
      } else if (S.fsc.filtre && S.fsc.filtre !== 'tous') p.filtre = S.fsc.filtre;
    } else if (t === 'eudr' && S.eudr) {
      if (S.eudr.filtre && S.eudr.filtre !== 'tous') p.filtre = S.eudr.filtre;
      if (!S.eudr.bobines) p.bobines = 0;
    }
  }
  const f = _qualFenetre();
  if (f) { p[f.cle] = f.id; nav += '|' + f.cle + ':' + f.id; }
  return { params: p, nav };
}

function qualiteSyncUrl() {
  if (!_qualUrlPrete || !window.MySifaUrl) return;
  try { const r = qualiteParams(); if (r) MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function qualiteUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  const obs = new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; qualiteSyncUrl(); });
  });
  obs.observe(document.body, { childList: true, subtree: true });
  // Les deux modales fixes s'affichent par leur style, sans toucher au DOM.
  _QUAL_OUVREURS.forEach(o => {
    const m = o[3] && document.getElementById(o[3]);
    if (m) obs.observe(m, { attributes: true, attributeFilter: ['style'] });
  });
}

function _qualAttendre(cond) {
  return new Promise(ok => { let n = 0; const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250); });
}
const _qualNum = v => (/^\d+$/.test(String(v)) ? Number(v) : v);

// Réouverture d'une fenêtre, une fois la vue en place et ses données chargées.
const _QUAL_REOUVRIR = {
  nouvelle_nc:          () => openCreateModal(),
  import_nc:            () => openImportModal(),
  nouvel_audit:         () => openCreateAuditModal(),
  ajout_auditeur:       () => { if (S.currentAudit) openAddAuditeurPicker(); },
  generation:           v => openSifaDocGenerate(v),
  version:              async v => { await _qualAttendre(() => S.currentSifaDoc); openSifaDocEdit(_qualNum(v)); },
  modele:               v => openTemplateEditor(v),
  lier_audit:           v => openLinkAuditModal(_qualNum(v)),
  nouvelle_fiche:       () => openCreateRefModal(),
  zip:                  v => { if (['fournisseur', 'groupe'].indexOf(v) !== -1) openCertsZipModal(v); },
  reglages:             v => { if (S.currentRes) openFournisseurSettingsModal(_qualNum(v)); },
  certificat:           v => { if (S.currentRes) openCertModal(v === 'nouveau' ? null : _qualNum(v)); },
  certificat_groupe:    v => { if (S.currentGroupe) openGroupeCertModal(v === 'nouveau' ? null : _qualNum(v)); },
  matrice_fournisseurs: () => { if (S.currentAudit) openAuditPickerFournisseurs(); },
  matrice_certifs:      () => { if (S.currentAudit) openAuditPickerCertifs(); },
  matrice_case:         v => { const [a, b] = v.split(':'); if (S.currentAudit && a && b) openMatriceCellEditor(_qualNum(a), _qualNum(b)); },
  apercu:               v => gedPreview(_qualNum(v)),
  proprietes:           v => gedEditMeta(_qualNum(v)),
  proprietes_dossier:   v => gedFolderProps(_qualNum(v)),
  achats_fsc:           async v => { await _qualAttendre(() => S.fsc.data); fscOuvrirAchats(_qualNum(v)); },
  certificat_fsc:       async v => { await _qualAttendre(() => S.fsc.data); fscVoirCertificat(_qualNum(v)); },
  controle_fsc:         async v => { await _qualAttendre(() => S.fsc.data); fscOuvrirControle(_qualNum(v)); },
  import_controles:     () => fscOuvrirImport(),
  rattacher:            async v => { await _qualAttendre(() => S.fsc.appro); fscApproRattacher(_qualNum(v)); },
  journal:              async v => { await _qualAttendre(() => S.fsc.appro); fscApproJournal(_qualNum(v)); },
  saisie_eudr:          async v => { await _qualAttendre(() => S.eudr.data); eudrOuvrirSaisie(_qualNum(v)); },
  liens_eudr:           async () => { await _qualAttendre(() => S.eudr.data); eudrOuvrirLiensCommuns(); },
  pdf_eudr:             async () => { await _qualAttendre(() => S.eudr.data); eudrOuvrirPdf(); },
  envoi_eudr:           async () => { await _qualAttendre(() => S.eudr.data); eudrOuvrirEnvoi(); },
  reponse_eudr:         async v => { await _qualAttendre(() => S.eudr.data); eudrVoirReponse(_qualNum(v)); },
  ia_formulaire:        v => { if (v === 'modifier') { if (S.view === 'formulaire-edit') formuIaOuvrir('modifier'); } else formuIaOuvrir('nouveau'); },
};
const _QUAL_FERMER = {
  nouvelle_nc: () => closeCreateModal(),
  import_nc: () => closeImportModal(),
  nouvel_audit: () => closeAuditCreate(),
  generation: () => closeSifaDocGenerate(),
  version: () => closeSifaDocGenerate(),
  modele: () => closeTemplateEditor(),
};
function _qualFermer(f) {
  try { (_QUAL_FERMER[f.cle] || closeMroot)(); } catch (e) {}
  try { closeMroot(); } catch (e) {}
  _qualFen = null;
}

async function qualiteAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const ou = (k, def) => (u.a(k) ? u.get(k, def) : (complet ? def : undefined));
  const memes = (a, b) => String(a) === String(b);

  // Fenêtre voulue : on ferme d'abord celle qui ne l'est plus.
  let voulue = null;
  Object.keys(_QUAL_REOUVRIR).forEach(k => { const v = u.get(k, null); if (v && v.length <= 120) voulue = { cle: k, id: v }; });
  const ouverte = _qualFenetre();
  if (ouverte && !(voulue && ouverte.cle === voulue.cle && ouverte.id === voulue.id)) _qualFermer(ouverte);

  // Vue visée : un objet l'emporte sur « vue ».
  let vue = null;
  const h = MySifaUrl.hashHerite();
  if (u.a('nc')) vue = 'detail';
  else if (u.a('audit')) vue = 'audits-detail';
  else if (u.a('doc')) vue = 'sifa-docs-detail';
  else if (u.a('fiche')) vue = 'ref-detail';
  else if (u.a('fournisseur')) vue = 'ressources-detail';
  else if (u.a('groupe')) vue = 'ressources-group';
  else if (u.a('formulaire')) vue = 'formulaire-edit';
  else if (u.a('vue')) vue = _QUAL_VUES[u.get('vue')] || null;
  else if (h && _QUAL_VUES_HASH.indexOf(h) !== -1) vue = h;
  if (!vue && complet) vue = 'list';
  // Rôle sans accès aux NC : la page s'est déjà rangée sur le référentiel.
  if (!S.isQualiteAdmin && !S.isQualiteReadonly && vue && ['ref-list', 'ref-detail'].indexOf(vue) === -1) vue = null;

  if (vue === 'list') {
    const st = ou('statut', 'all'); if (st !== undefined) S.filterStatut = st;
    const ty = ou('type', 'all'); if (ty !== undefined) S.filterType = ty;
    const gr = ou('gravite', 'all'); if (gr !== undefined) S.filterGravite = gr;
    setView('list');
  } else if (vue === 'detail') {
    const id = u.get('nc');
    if (!(S.view === 'detail' && S.current && memes(S.current.id, id))) await openDetail(_qualNum(id));
    const t = u.get('onglet', 'fiche', ['fiche', 'fichiers', 'discussion']);
    if (S.current && memes(S.current.id, id) && S.detailTab !== t) setDetailTab(t);
  } else if (vue === 'audits-list') {
    const st = ou('statut', 'all'); if (st !== undefined) S.auditFilterStatut = st;
    setView('audits-list');
  } else if (vue === 'audits-detail') {
    const id = u.get('audit');
    if (!(S.view === 'audits-detail' && S.currentAudit && memes(S.currentAudit.id, id))) await openAudit(_qualNum(id));
    if (S.currentAudit && memes(S.currentAudit.id, id)) {
      const t = u.get('onglet', 'fichiers', ['fichiers', 'fiche', 'discussion', 'matrice']);
      const d = u.get('dossier', null);
      const dossier = d ? _qualNum(d) : null;
      if (S.currentFolderId !== dossier) S.currentFolderId = dossier;
      if (S.auditDetailTab !== t) setAuditTab(t); else renderAuditDetail();
    }
  } else if (vue === 'ref-list') {
    const c = ou('categorie', 'all'); if (c !== undefined) S.refFilterCat = c;
    const v = ou('validation', 'all'); if (v !== undefined) S.refFilterStatV = v;
    setView('ref-list');
  } else if (vue === 'ref-detail') {
    const id = u.get('fiche');
    if (!(S.view === 'ref-detail' && S.currentRef && memes(S.currentRef.id, id))) await openRef(_qualNum(id));
    if (S.currentRef && memes(S.currentRef.id, id)) {
      const q = u.get('question', null);
      S.refOpenQaId = q ? _qualNum(q) : null;
      const ed = u.get('edition', null) === '1';
      if (ed && !S.refEdit && S.isQualiteAdmin) startRefEdit();
      else { if (!ed && S.refEdit) { S.refEdit = false; S.refEditBuf = null; } renderRefDetail(); }
    }
  } else if (vue === 'ressources-list') {
    if (complet || u.a('categorie')) S.resFiltreCats = u.tous('categorie');
    if (complet || u.a('certif')) S.resFiltreCertifs = u.tous('certif').map(_qualNum);
    // Rangement et affichage des catégories sont des préférences mémorisées :
    // loadRessources() les relit, on les y range donc.
    const rg = ou('rangement', 'categorie');
    if (rg !== undefined && ['alpha', 'categorie'].indexOf(rg) !== -1) { S.resRangement = rg; try { localStorage.setItem('mysifa_res_rangement', rg); } catch (e) {} }
    const cv = ou('categories_visibles', '0');
    if (cv !== undefined) { S.resShowCats = cv === '1'; try { localStorage.setItem('mysifa_res_cats', cv === '1' ? '1' : '0'); } catch (e) {} }
    setView('ressources-list');
  } else if (vue === 'ressources-detail') {
    const id = u.get('fournisseur');
    if (!(S.view === 'ressources-detail' && S.currentRes && S.currentRes.fournisseur && memes(S.currentRes.fournisseur.id, id))) await openRessourceFournisseur(_qualNum(id));
  } else if (vue === 'ressources-group') {
    const g = u.get('groupe');
    if (!(S.view === 'ressources-group' && S.currentGroupe && S.currentGroupe.groupe === g)) await openRessourceGroupe(encodeURIComponent(g));
  } else if (vue === 'sifa-docs-detail') {
    const code = u.get('doc');
    if (!(S.view === 'sifa-docs-detail' && S.currentSifaDoc && S.currentSifaDoc.template && S.currentSifaDoc.template.code === code)) await openSifaDoc(code);
  } else if (vue === 'sifa-docs-list' && S.ged) {
    const sec = ou('section', '');
    if (sec !== undefined) {
      const t = _QUAL_SECTIONS[sec] || 'docs';
      S.ged.tab = t;
      try { localStorage.setItem('mysifa_sifa_tab', t); } catch (e) {}
    }
    const t = gedActiveTab();
    if (t === 'fsc' && S.fsc) {
      const so = ou('sous', 'fournisseurs');
      if (so !== undefined) { S.fsc.sousOnglet = so === 'appro' ? 'appro' : 'fournisseurs'; try { localStorage.setItem('mysifa_fsc_sous_onglet', S.fsc.sousOnglet); } catch (e) {} }
      const fi = ou('filtre', 'tous'); if (fi !== undefined) S.fsc.filtre = fi;
      const af = S.fsc.approFiltres;
      ['debut', 'fin', 'eligible'].forEach(k => { const x = ou(k, ''); if (x !== undefined) af[k] = x; });
      const ce = ou('certifies', '1'); if (ce !== undefined) af.certifies = ce === '0' ? 0 : 1;
    } else if (t === 'eudr' && S.eudr) {
      const fi = ou('filtre', 'tous'); if (fi !== undefined) S.eudr.filtre = fi;
      const bo = ou('bobines', '1');
      if (bo !== undefined) { S.eudr.bobines = bo !== '0'; try { localStorage.setItem('mysifa_eudr_bobines', S.eudr.bobines ? '1' : '0'); } catch (e) {} }
    }
    setView('sifa-docs-list');
    if (t === 'explorer') {
      await _qualAttendre(() => S.ged.cols.length);
      if (u.get('corbeille', null) === '1') { if (S.ged.mode !== 'trash') await gedOpenTrash(); }
      else {
        const d = _qualNum(u.get('dossier', '0'));
        if (S.ged.mode !== 'browse' || !memes(gedCwd(), d)) await gedOpen(d || 0);
        const fid = u.get('fichier', null);
        if (fid && !(S.ged.detail && memes(S.ged.detail.id, fid))) await gedOpenFile(_qualNum(fid));
        else if (!fid && S.ged.detail) gedCloseDetail();
      }
    }
  } else if (vue === 'formulaires-list' && S.formu) {
    const fi = ou('filtre', 'actifs');
    if (fi !== undefined) S.formu.filtre = _QUAL_FORMU_FILTRES.indexOf(fi) !== -1 ? fi : 'actifs';
    setView('formulaires-list');
  } else if (vue === 'formulaire-edit' && S.formu) {
    const id = u.get('formulaire');
    if (/^\d+$/.test(String(id)) && !(S.view === 'formulaire-edit' && S.formu.courant && memes(S.formu.courant.id, id))) await formuOuvrir(Number(id));
  } else if (vue === 'menu') {
    setView('menu');
  }

  if (voulue && !(_qualFenetre() && _qualFen.cle === voulue.cle && _qualFen.id === voulue.id)) {
    try { await _QUAL_REOUVRIR[voulue.cle](voulue.id); } catch (e) {}
  }
}

// Appelé à la fin de init(), une fois l'utilisateur et les listes chargés.
async function qualiteDemarrerUrl() {
  if (_qualDemarre || !window.MySifaUrl) return;
  _qualDemarre = true;
  qualiteEnvelopper();
  try { await qualiteAllerUrl(false); } catch (e) {}
  _qualUrlPrete = true;
  qualiteSyncUrl();
  qualiteUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_qualUrlPrete) await qualiteAllerUrl(true); });
}
