/*
 * MySifa — MyStock : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Extrait de app/web/stock_page.py le 15/10/2026 pour ne pas rallonger la
 * page. Chargé AVANT le script principal de MyStock : il ne fait que déclarer
 * des fonctions et s'abonner au Retour du navigateur. S, goToTab(),
 * loadMatiere(), openPfDetailModal()… appartiennent au script principal ; ils
 * ne sont lus qu'à l'appel, une fois init() lancé (scripts classiques : les
 * `let` / `const` de premier niveau partagent la même portée globale).
 */
// ── Adresse de la page (static/mysifa_url.js, .claude/rules/url-etat.md) ──
// L'adresse porte tout ce qu'on regarde : onglet, sous-vue, filtres, tri,
// objet ouvert. Les clés déjà posées dans des liens (tab, sous, vue, cat,
// matiere, fiche, produit, ref, empl, poste) gardent leur nom.
//
// MyStock n'a pas de rendu central : chaque vue se redessine elle-même. Plutôt
// que d'appeler stockSyncUrl() depuis des dizaines d'endroits, un observateur
// sur #root la rappelle après tout changement d'affichage (une fois par image).
// Changer d'onglet, de sous-vue ou ouvrir un objet empile une entrée
// d'historique ; un filtre ou un tri la remplace.
let _stockUrlPrete = false;   // posé à la fin d'init() : avant, l'adresse porte
                              // encore les paramètres à lire.
const _STOCK_SOUS = {
  reception: ['nouvelle', 'liste', 'historique', 'rvgi', 'rvgi-historique'],
  monitoring: ['quantites', 'mouvements', 'ecarts-mp'],
  destockage: ['a_traiter', 'destockes', 'mouvements'],
};
const _STOCK_CLE = /^[A-Za-z0-9_.\-]{1,60}$/;
const _STOCK_JOUR = /^\d{4}-\d{2}-\d{2}$/;

function _stockSous() {
  const t = S.tab;
  if (t === 'reception') return S.recepSubTab || 'nouvelle';
  if (t === 'monitoring') return (S.monitoring && S.monitoring.monPage) || 'quantites';
  if (t === 'destockage') return (S.destockage && S.destockage.vue) || 'a_traiter';
  return null;
}

// Fenêtres de consultation et de réglages que l'adresse sait rouvrir, sur
// toute page. Les formulaires (mouvement, création) n'y sont pas.
const _STOCK_MODALES = {
  fiche_pf:        { ok: /^.{1,60}$/,        ouvrir: v => openPfDetailModal(v) },
  historique_prix: { ok: /^[0-9]+$/,         ouvrir: v => openValorisationHistorique(Number(v)) },
  historique_pf:   { ok: /^[0-9]+$/,         ouvrir: v => openPFHistorique(Number(v)) },
  besoins_dossier: { ok: /^.{1,60}$/,        ouvrir: v => openBesoinDocModal(v) },
  parametres_matiere: { ok: /^[0-9]+$/,      ouvrir: v => openValorisationParamsModal(Number(v)) },
  conditionnement: { ok: /^[0-9]+$/,         ouvrir: v => openValorisationConditionnementModal(Number(v)) },
  reglages:        { ok: /^(valorisation|matieres|correspondances)$/,
                     ouvrir: v => (v === 'valorisation' ? openValorisationSettingsModal()
                                  : v === 'matieres' ? openMatieresAdminDrawer()
                                  : openBesoinsMappingModal()) },
};
// ── Toutes les autres fenêtres, formulaires compris ────────────────────
// Inventaire du 15/10/2026 (grep des fonctions qui écrivent dans #mroot ou
// posent une surcouche sur body, stock_page.py + mysifa_stock_modals.js).
// Chaque fonction d'ouverture est ENVELOPPÉE au démarrage (stockEnvelopper-
// Ouvreurs) : elle déclare sa fenêtre puis s'exécute — aucune des quarante
// fonctions n'a à connaître l'adresse. `valeur(args)` tire de ses arguments
// ce qui suffit à la rouvrir ; `ouvrir(v)` retrouve les objets dans l'état.
//
// Hors adresse, volontairement : caméra (startCamera, recepStartCamera),
// choix d'imprimante et impression d'étiquettes après une réception
// (transitoires, liés à un geste qui vient d'avoir lieu), confirmation de
// sortie d'un produit fini (étape de la fenêtre de sortie), écart FSC (étape
// d'enregistrement d'un mouvement), modale de laizes de la tendance.
async function _stockMatiereParId(id) {
  if (!id) return undefined;
  const sm = S.selMatiere && S.selMatiere.matiere;
  if (sm && String(sm.id) === String(id)) return sm;
  if (!S.matieres) { try { const d = await api('/api/stock/matieres'); S.matieres = Array.isArray(d) ? d : []; } catch (e) {} }
  return (S.matieres || []).find(x => String(x.id) === String(id)) || undefined;
}
function _stockProduitCourant(id) {
  const p = S.selProduit && S.selProduit.produit;
  return (p && String(p.id) === String(id)) ? p : undefined;
}
function _stockLigneLot(pid, empl) {
  const e = ((S.selProduit && S.selProduit.emplacements) || []).find(x => String(x.emplacement) === String(empl));
  if (!e) return null;
  const p = (S.selProduit && S.selProduit.produit) || {};
  return { qLot: e.quantite_lot_fifo != null ? e.quantite_lot_fifo : e.quantite,
           unite: e.unite || p.unite || '', ref: e.reference || p.reference || '', row: e };
}
const _deux = v => { const i = String(v).indexOf(':'); return i < 0 ? [String(v), ''] : [String(v).slice(0, i), String(v).slice(i + 1)]; };

const _STOCK_OUVREURS = [
  // [fonction, clé, valeur(args)]
  ['openModalMouvement',       'mouvement_mp',   a => a[0] + (a[1] && a[1].id ? ':' + a[1].id : '')],
  ['openModalPfMouvement',     'mouvement_pf',   a => a[0] + (a[1] && a[1].id ? ':' + a[1].id : '')],
  ['openPfMvtModal',           'mouvement_produit_fini', a => a[0] || 'entree'],
  ['openNgMvtModal',           'mouvement_negoce', a => a[0] || 'entree'],
  ['openNgCatalogueModal',     'catalogue_negoce', a => a[0] || 'tout'],
  ['openPfExportCsvModal',     'export',         () => 'produits-finis'],
  ['openInvPfExportModal',     'export',         () => 'inventaire'],
  ['openStockSortieProdQuick', 'rapide',         () => 'sortie-prod'],
  ['openStockAExpedierQuick',  'rapide',         () => 'a-expedier'],
  ['openDashboardAddPfModal',  'rapide',         () => 'ajout-pf'],
  ['openEmplEntreeModal',      'entree_empl',    a => a[0]],
  ['openMvtModal',             'mouvement',      a => (a[3] || 'entree') + ':' + a[0] + ':' + (a[2] || '')],
  ['openMoveLotModal',         'deplacer_lot',   a => a[0] + ':' + a[1]],
  ['sortirLot',                'sortir_lot',     a => a[0] + ':' + a[1]],
  ['openEmplInventaireConfirm','inventaire_confirmer', a => a[0]],
  ['invV2OpenModifyModal',     'inv_modifier',   a => a[0]],
  ['invV2OpenCommentModal',    'inv_note',       a => a[0]],
  ['invV2OpenAddProductModal', 'inv_ajout',      () => 'produit'],
  ['openMatiereRefEditModal',  'modifier_matiere', a => a[0] && a[0].id],
  ['openMatiereCopyFromCard',  'copier_matiere', a => a[0] && a[0].id],
  ['openCondAjustModal',       'conditionnements', () => 'tous'],
  ['openMatiereCreateModal',   'nouvelle_matiere', () => 'oui'],
  ['openMpDeplacerModal',      'deplacer_variante', a => a[1] && a[1].id],
  ['openMpVarianteModal',      'variante',       a => (a[1] && a[1].id) || 'nouvelle'],
  ['openMpEmplacementModal',   'emplacement_matiere', a => (a[1] && (a[1].id || a[1].emplacement)) || 'nouveau'],
  ['openModalInventaireMatiere','inventaire_matiere', a => a[0] && a[0].id],
  ['openReceptionMatiereModal','reception_matiere', a => a[0] && a[0].id],
  ['openProductionEdit',       'production_modifier', a => a[0] && a[0].reference],
  ['openProductionAddTo',      'production_ajouter',  a => a[0] && a[0].reference],
  ['openTracaPrint',           'impression',     a => a[0] && a[0].id],
  ['openBesoinDocApercu',      'apercu_doc',     a => a[0] + ':' + (a[1] || '')],
  ['openDocEtatModal',         'etat_doc',       a => a[0] + ':' + a[1]],
  ['openBesoinAssocierModal',  'associer',       a => a[0] + ':' + a[1]],
  ['openBesoinCreerMatiere',   'creer_matiere',  a => a[0] + ':' + a[1]],
  ['openBesoinsHelpModal',     'aide',           () => 'besoins'],
  ['openValorisationConteneurModal', 'conteneur', a => a[0] && (a[0].id != null ? a[0].id : a[0].matiere_id)],
  ['openValorisationClotureModal',   'cloture',  () => 'valorisation'],
  // Module mysifa_destockage.js, ouvert par cette fonction de la page.
  ['dstOuvrirRelecture',       'controle',       a => a[0] && a[0].planning_id],
];

const _STOCK_REOUVRIR = {
  mouvement_mp: async v => { const [t, id] = _deux(v); openModalMouvement(t, await _stockMatiereParId(id)); },
  mouvement_pf: v => { const [t, id] = _deux(v); openModalPfMouvement(t, _stockProduitCourant(id)); },
  mouvement_produit_fini: v => openPfMvtModal(v),
  mouvement_negoce: v => openNgMvtModal(v),
  catalogue_negoce: v => openNgCatalogueModal(v === 'tout' ? undefined : v),
  export: v => (v === 'inventaire' ? openInvPfExportModal() : openPfExportCsvModal()),
  rapide: v => (v === 'sortie-prod' ? openStockSortieProdQuick() : v === 'a-expedier' ? openStockAExpedierQuick() : openDashboardAddPfModal()),
  entree_empl: v => openEmplEntreeModal(v),
  mouvement: v => {
    const [t, reste] = _deux(v); const [pid, empl] = _deux(reste);
    const p = _stockProduitCourant(pid);
    openMvtModal(Number(pid), p ? p.reference : '', empl, t);
  },
  deplacer_lot: v => {
    const [pid, empl] = _deux(v); const l = _stockLigneLot(pid, empl);
    if (l) openMoveLotModal(Number(pid), empl, l.qLot, l.unite, l.ref, l.row.nb_lots, { fsc: l.row.fsc });
  },
  sortir_lot: v => {
    const [pid, empl] = _deux(v); const l = _stockLigneLot(pid, empl);
    if (l) sortirLot(Number(pid), empl, l.qLot, l.unite, l.ref, l.row.nb_lots, { fsc: l.row.fsc });
  },
  inventaire_confirmer: v => openEmplInventaireConfirm(v),
  inv_modifier: v => {
    const r = ((S.invV2Detail && S.invV2Detail.refs) || []).find(x => String(x.produit_id) === String(v));
    if (r) invV2OpenModifyModal(r.produit_id, parseFloat(r.quantite) || 0, r.reference, r.designation, r.unite || '');
  },
  inv_note: v => {
    const r = ((S.invV2Detail && S.invV2Detail.refs) || []).find(x => String(x.produit_id) === String(v));
    if (r) invV2OpenCommentModal(r.produit_id, r.reference, r.designation);
  },
  inv_ajout: () => invV2OpenAddProductModal(),
  modifier_matiere: async v => { const m = await _stockMatiereParId(v); if (m) openMatiereRefEditModal(m); },
  copier_matiere: async v => { const m = await _stockMatiereParId(v); if (m) openMatiereCopyFromCard(m); },
  conditionnements: () => openCondAjustModal(),
  nouvelle_matiere: () => openMatiereCreateModal(),
  deplacer_variante: v => {
    const m = S.selMatiere && S.selMatiere.matiere;
    const vs = (S.selMatiere && S.selMatiere.variantes && S.selMatiere.variantes.variantes) || [];
    const x = vs.find(y => String(y.id) === String(v));
    if (m && x) openMpDeplacerModal(m, x);
  },
  variante: v => {
    const m = S.selMatiere && S.selMatiere.matiere; if (!m) return;
    const vs = (S.selMatiere.variantes && S.selMatiere.variantes.variantes) || [];
    openMpVarianteModal(m, v === 'nouvelle' ? null : (vs.find(y => String(y.id) === String(v)) || null));
  },
  emplacement_matiere: v => {
    const m = S.selMatiere && S.selMatiere.matiere; if (!m) return;
    const es = Array.isArray(m.emplacements) ? m.emplacements : [];
    openMpEmplacementModal(m, v === 'nouveau' ? null : (es.find(e => String(e.id || e.emplacement) === String(v)) || null));
  },
  inventaire_matiere: async v => { const m = await _stockMatiereParId(v); if (m) openModalInventaireMatiere(m); },
  reception_matiere: async v => { const m = await _stockMatiereParId(v); if (m) openReceptionMatiereModal(m); },
  production_modifier: v => { const r = ((S.productionZ1 && S.productionZ1.refs) || []).find(x => x.reference === v); if (r) openProductionEdit(r); },
  production_ajouter: v => { const r = ((S.productionZ1 && S.productionZ1.refs) || []).find(x => x.reference === v); if (r) openProductionAddTo(r); },
  impression: v => { const e = (typeof TRACA_ETIQUETTES !== 'undefined' ? TRACA_ETIQUETTES : []).find(x => String(x.id) === String(v)); if (e) openTracaPrint(e); },
  apercu_doc: v => { const [d, t] = _deux(v); openBesoinDocApercu(d, t); },
  etat_doc: v => { const [t, id] = _deux(v); openDocEtatModal(t, id, ''); },
  associer: v => { const [k, x] = _deux(v); openBesoinAssocierModal(k, x); },
  creer_matiere: v => { const [k, x] = _deux(v); openBesoinCreerMatiere(k, x); },
  aide: () => openBesoinsHelpModal(),
  conteneur: v => {
    const it = ((S.valorisation && S.valorisation.items) || []).find(x => String(x.id != null ? x.id : x.matiere_id) === String(v));
    if (it) openValorisationConteneurModal(it);
  },
  cloture: () => openValorisationClotureModal(),
  controle: v => {
    const lignes = (S.destockage && S.destockage.data && S.destockage.data.dossiers) || [];
    const x = lignes.find(l => String(l.planning_id) === String(v));
    dstOuvrirRelecture(x || { planning_id: Number(v) });
  },
  import: () => { S.importRefsOpen = true; S.importRefsPreview = null; render(); },
  unites: () => { S.unitModalOpen = true; S.unitNewLabel = ''; S.unitNewBase = 'cartons'; S.unitNewQty = ''; render(); },
};

// Enveloppe chaque fonction d'ouverture (appelé une fois, à la fin d'init()).
// Les fonctions de premier niveau d'un script classique sont des propriétés
// de window : réassigner window[nom] change aussi les appels internes.
function stockEnvelopperOuvreurs() {
  _STOCK_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      let v = null;
      try { v = valeur(arguments); } catch (e) {}
      if (v !== null && v !== undefined && v !== '' && String(v).length <= 120) stockModaleOuverte(cle, v);
      return orig.apply(this, arguments);
    };
    env.__adresse = true;
    window[nom] = env;
  });
  Object.keys(_STOCK_REOUVRIR).forEach(cle => {
    if (!_STOCK_MODALES[cle]) _STOCK_MODALES[cle] = { ok: /^.{1,120}$/, ouvrir: _STOCK_REOUVRIR[cle] };
  });
}

// Une fenêtre se déclare en s'ouvrant. Les fenêtres de MyStock se ferment par
// cinq chemins différents (closeMroot, retrait direct, fond cliqué…) : au lieu
// de les suivre un par un, on retient l'élément qu'elle a ajouté à la page, et
// la fenêtre est fermée dès qu'il n'y est plus.
function stockModaleOuverte(cle, id) {
  const m = document.getElementById('mroot');
  S.urlModale = { cle, id: String(id), el: null, essais: 0,
    avant: new Set([...document.body.children, ...(m ? m.children : [])]) };
  stockSyncUrl();
}
function _stockCandidatModale(avant) {
  const m = document.getElementById('mroot');
  const dansMroot = m ? [...m.children].filter(n => !avant || !avant.has(n)) : [];
  if (dansMroot.length) return dansMroot[dansMroot.length - 1];
  const surBody = [...document.body.children].filter(n => (!avant || !avant.has(n))
    && /overlay|modal|drawer|backdrop/i.test(String(n.className || '')) && !/toast/i.test(String(n.className || '')));
  return surBody.length ? surBody[surBody.length - 1] : null;
}
function _stockModaleVivante() {
  const mo = S.urlModale;
  if (!mo) return null;
  if (!mo.el) {
    const c = _stockCandidatModale(mo.avant);
    if (c) { const m = document.getElementById('mroot'); mo.el = c; mo.dansMroot = !!(m && m.contains(c)); mo.avant = null; }
    else if (++mo.essais > 200) { S.urlModale = null; return null; }   // jamais apparue
    return mo;                                                          // ouverture en cours
  }
  if (!mo.el.isConnected) {
    // Redessinée dans #mroot (onglet interne d'une fenêtre) : même fenêtre.
    const m = document.getElementById('mroot');
    if (mo.dansMroot && m && m.lastElementChild) { mo.el = m.lastElementChild; return mo; }
    S.urlModale = null;
    return null;
  }
  return mo;
}
function _stockFermerModale() {
  if (S.importRefsOpen || S.unitModalOpen) { S.importRefsOpen = false; S.unitModalOpen = false; render(); }
  const mo = S.urlModale;
  S.urlModale = null;
  if (!mo || !mo.el) return;
  const m = document.getElementById('mroot');
  if (m && m.contains(mo.el)) closeMroot(); else mo.el.remove();
}

function stockParams() {
  const r = _stockParamsBase();
  const mo = _stockModaleVivante();
  if (mo) { r.params[mo.cle] = mo.id; r.nav += '/' + mo.cle; }
  // Fenêtres décrites par un drapeau de S (rendues par render()).
  else if (S.importRefsOpen) { r.params.import = 'references'; r.nav += '/import'; }
  else if (S.unitModalOpen) { r.params.unites = 'nouvelle'; r.nav += '/unites'; }
  return r;
}

function _stockParamsBase() {
  const p = {};
  const tab = S.tab || 'dashboard';
  if (tab !== 'dashboard') p.tab = tab;
  let nav = tab;
  const sous = _stockSous();
  if (sous && _STOCK_SOUS[tab] && sous !== _STOCK_SOUS[tab][0]) p.sous = sous;
  if (tab === 'besoins-matieres' && S.besoinsView && S.besoinsView !== 'dossier') p.vue = S.besoinsView;
  nav += '/' + (p.sous || p.vue || '');

  // Détail ouvert par-dessus l'onglet (prioritaire, comme dans renderContent).
  if (S.selMatiere && S.selMatiere.matiere && S.selMatiere.matiere.id) {
    p.matiere = String(S.selMatiere.matiere.id);
    if (S.selMatiere.vue && S.selMatiere.vue !== 'stock') p.fiche = S.selMatiere.vue;
    if (S.mpVarGrain && S.mpVarGrain !== 'fournisseur') p.var_grain = S.mpVarGrain;
    if (S.mpVarFiltreFourn) p.var_fournisseur = S.mpVarFiltreFourn;
    if (S.mpVarFiltreLaize) p.var_laize = S.mpVarFiltreLaize;
    return { params: p, nav: nav + '/matiere:' + p.matiere + '/' + (p.fiche || '') };
  }
  // loadProduit() range la réponse de l'API telle quelle : l'id est dans
  // .produit, et loadEmplacement() met le code dans .emplacement. L'ancien
  // code lisait .id et .code, qui n'existent pas : ni la fiche produit ni
  // l'emplacement n'arrivaient dans l'adresse.
  const pid = S.selProduit && ((S.selProduit.produit && S.selProduit.produit.id) || S.selProduit.id);
  if (pid) {
    p.produit = String(pid);
    return { params: p, nav: nav + '/produit:' + p.produit };
  }
  const ecode = S.selEmpl && (S.selEmpl.emplacement || S.selEmpl.code);
  if (ecode) {
    p.empl = String(ecode);
    return { params: p, nav: nav + '/empl:' + p.empl };
  }

  if (tab === 'matieres') {
    const cat = mpCategorieCourante();
    if (cat) { p.cat = cat; nav += '/cat:' + cat; }
    if (S.mpTri && S.mpTri !== 'alpha') p.tri = S.mpTri;
    if (S.mpGrain && S.mpGrain !== 'matiere') p.grain = S.mpGrain;
    if (S.mpFiltreFourn) p.fournisseur = S.mpFiltreFourn;
    if (S.mpFiltreLaize) p.laize = S.mpFiltreLaize;
  } else if (tab === 'matieres-inventaire') {
    if (S.matInvCategorie) p.categorie = S.matInvCategorie;
    if (S.matInvStatut) p.statut = S.matInvStatut;
  } else if (tab === 'inventaire') {
    if (S.invV2Detail && S.invV2Code) { p.inventaire = S.invV2Code; nav += '/inv:' + S.invV2Code; }
  } else if (tab === 'bobines') {
    const b = S.bobines;
    if (b && b.etat && b.etat !== 'stock') p.etat = b.etat;
  } else if (tab === 'historique') {
    const f = S.historiqueFiltres || {};
    if (f.type_stock && f.type_stock !== 'tout') p.type_stock = f.type_stock;
    if (f.categorie) p.categorie = f.categorie;
    if (f.type_mouvement) p.mouvement = f.type_mouvement;
    if (f.date_debut) p.du = f.date_debut;
    if (f.date_fin) p.au = f.date_fin;
  } else if (tab === 'monitoring') {
    const m = S.monitoring;
    if (m && m.monPage === 'ecarts-mp') {
      // Écarts matières RVGI : période (heures, ou dates), « afficher aussi
      // ce qui concorde », onglet intérieur, matière dépliée.
      const st = S.ecartsRvgi;
      if (st) {
        if (st.heures) { if (Number(st.heures) !== 48) p.heures = String(st.heures); }
        else { p.heures = 'periode'; if (st.debut) p.du = st.debut; if (st.fin) p.au = st.fin; }
        if (st.tout) p.concorde = '1';
        if (st.onglet && st.onglet !== 'matieres') { p.onglet = st.onglet; nav += '/onglet:' + st.onglet; }
        if (st.detail != null && st.detail !== '') p.detail = String(st.detail);
      }
    } else if (m) {
      if (m.filterStatut) p.statut = m.filterStatut;
      if (m.sortColumn) { p.tri = m.sortColumn; if (m.sortDirection === 'desc') p.sens = 'desc'; }
    }
  } else if (tab === 'valorisation') {
    const v = S.valorisation;
    if (v) {
      if (v.filterCategorie) p.categorie = v.filterCategorie;
      // Sous-section : null = toutes ; '' = « non classés », écrit « ~ ».
      if (v.filterSousSection !== null && v.filterSousSection !== undefined) p.section = v.filterSousSection === '' ? '~' : v.filterSousSection;
      if (v.sortColumn) { p.tri = v.sortColumn; if (v.sortDirection === 'desc') p.sens = 'desc'; }
      if (v.snapshotDate) p.date = v.snapshotDate;
      const pf = v.pf;
      if (pf) {
        if (pf.filterSansPrix) p.pf_sans_prix = '1';
        if (pf.filterNegoce) p.pf_negoce = '1';
        if (pf.filterAvecStock) p.pf_avec_stock = '1';
      }
    }
  } else if (tab === 'negoce') {
    const f = S.ngFilters;
    if (f) {
      if (f.sort && f.sort !== 'ref') p.tri = f.sort;
      if (f.hideRupture) p.sans_rupture = '1';
      if (f.refs && f.refs.length) p.references = f.refs.slice();
      if (f.empls && f.empls.length) p.emplacements = f.empls.slice();
    }
    if ((S.ngSelDetail || S.ngSelDetailLoading) && S.ngSelRef) { p.negoce = S.ngSelRef; nav += '/negoce:' + S.ngSelRef; }
  } else if (tab === 'destockage') {
    const st = S.destockage;
    if (st && st.jours && Number(st.jours) !== 30) p.jours = String(st.jours);
  } else if (tab === 'reception') {
    if (S.recepExpandedId != null) p.lot = String(S.recepExpandedId);
  } else if (tab === 'plan-entrepot') {
    if (S.planBat != null) { p.batiment = String(S.planBat); nav += '/bat:' + S.planBat; }
    if (S.planSel != null) p.element = String(S.planSel);
  } else if (tab === 'traca') {
    if (S.tracaPoste) { p.poste = S.tracaPoste; nav += '/poste:' + S.tracaPoste; }
    // Étiquettes spécifiques : le module dit ce qu'il montre (vue, dossier,
    // étiquette ouverte dans l'éditeur, demande, fenêtre).
    const ad = S.tracaPoste === 'specifiques' && window.EtiqSpec && window.EtiqSpec.adresse;
    if (ad) {
      const e = ad.etat();
      if (e.dossier != null) p.dossier = String(e.dossier);
      if (e.modele) { p.modele = String(e.modele); nav += '/modele:' + e.modele; }
      else if (e.vue === 'demandes') { p.vue = 'demandes'; nav += '/demandes'; if (e.demande != null) p.demande = String(e.demande); }
      if (e.modale && e.modale.cle) { p[e.modale.cle] = String(e.modale.id); nav += '/' + e.modale.cle; }
    }
  }
  return { params: p, nav: nav };
}

// Appelée par les gestes historiques (12 endroits) ET par l'observateur.
function stockSyncUrl() {
  if (!_stockUrlPrete || !window.MySifaUrl || !S.user) return;
  try { const r = stockParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); }
  catch (e) { /* l'URL est un confort, jamais un blocage */ }
}

function stockUrlObserver() {
  // body, pas #root : #mroot et les fenêtres posées sur body sont hors de #root.
  const root = document.body;
  if (!root || typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; stockSyncUrl(); });
  }).observe(root, { childList: true, subtree: true });
}

// Filtres et sous-vues de l'onglet `tab` lus dans l'adresse. `complet`
// (Retour/Suivant) : une clé absente remet le défaut ; au démarrage elle
// laisse l'état tel quel (préférences locales, filtres d'un indicateur).
function stockLireFiltres(u, tab, complet) {
  const val = (k, def, admis) => u.get(k, def, admis);
  const ou = (k, def) => (u.a(k) ? u.get(k, def) : (complet ? def : undefined));
  const sous = val('sous', null);
  if (tab === 'reception') {
    if (sous && _STOCK_SOUS.reception.includes(sous)) S.recepSubTab = sous; else if (complet) S.recepSubTab = 'nouvelle';
    const lot = val('lot', null);
    if (lot && /^[0-9]+$/.test(lot)) S.recepExpandedId = Number(lot); else if (complet) S.recepExpandedId = null;
  }
  if (tab === 'besoins-matieres') {
    const v = val('vue', null);
    if (v && BESOINS_VUES.includes(v)) S.besoinsView = v; else if (complet) S.besoinsView = 'dossier';
  }
  if (tab === 'matieres') {
    const tri = ou('tri', 'alpha'); if (tri !== undefined && _STOCK_CLE.test(tri)) S.mpTri = tri;
    const gr = ou('grain', 'matiere'); if (gr !== undefined && _STOCK_CLE.test(gr)) S.mpGrain = gr;
    const fo = ou('fournisseur', ''); if (fo !== undefined) S.mpFiltreFourn = fo;
    const la = ou('laize', ''); if (la !== undefined) S.mpFiltreLaize = la;
  }
  if (u.a('matiere') || complet) {
    const vg = ou('var_grain', 'fournisseur'); if (vg !== undefined && _STOCK_CLE.test(vg)) S.mpVarGrain = vg;
    const vf = ou('var_fournisseur', ''); if (vf !== undefined) S.mpVarFiltreFourn = vf;
    const vl = ou('var_laize', ''); if (vl !== undefined) S.mpVarFiltreLaize = vl;
  }
  if (tab === 'matieres-inventaire') {
    const c = ou('categorie', ''); if (c !== undefined) S.matInvCategorie = c;
    const st = ou('statut', ''); if (st !== undefined) S.matInvStatut = ['', 'vert', 'orange', 'rouge'].includes(st) ? st : '';
  }
  if (tab === 'bobines') {
    const e = ou('etat', 'stock');
    if (e !== undefined && ['stock', 'consommee', 'rebut', 'tous'].includes(e)) { bobEnsureState().etat = e; bobEnsureState().page = 0; }
  }
  if (tab === 'historique') {
    const f = S.historiqueFiltres || (S.historiqueFiltres = {});
    const ts = ou('type_stock', 'tout'); if (ts !== undefined && _STOCK_CLE.test(ts)) f.type_stock = ts;
    const c = ou('categorie', ''); if (c !== undefined) f.categorie = c;
    const tm = ou('mouvement', ''); if (tm !== undefined) f.type_mouvement = tm;
    const du = ou('du', ''); if (du !== undefined) f.date_debut = _STOCK_JOUR.test(du) ? du : '';
    const au = ou('au', ''); if (au !== undefined) f.date_fin = _STOCK_JOUR.test(au) ? au : '';
  }
  if (tab === 'monitoring') {
    const m = monEnsureState();
    if (sous && _STOCK_SOUS.monitoring.includes(sous)) m.monPage = sous; else if (complet) m.monPage = 'quantites';
    if (m.monPage === 'ecarts-mp') {
      const st = ervEtat();
      const avant = JSON.stringify([st.heures, st.debut, st.fin]);
      const h = ou('heures', '48');
      if (h !== undefined) {
        if (h === 'periode') {
          st.heures = null;
          const du = u.get('du', ''), au = u.get('au', '');
          if (_STOCK_JOUR.test(du)) st.debut = du;
          if (_STOCK_JOUR.test(au)) st.fin = au;
        } else if (/^[0-9]{1,4}$/.test(h)) st.heures = Number(h);
      }
      if (u.a('concorde') || complet) st.tout = u.a('concorde');
      const o = ou('onglet', 'matieres');
      if (o !== undefined && ['matieres', 'dossiers', 'non_apparies'].includes(o)) st.onglet = o;
      const det = ou('detail', '');
      if (det !== undefined) st.detail = det || null;
      // Autre période : les chiffres sont à recharger (le rendu de la
      // sous-page relance la comparaison quand data est vide).
      if (avant !== JSON.stringify([st.heures, st.debut, st.fin])) st.data = null;
    }
    const st = ou('statut', ''); if (st !== undefined) m.filterStatut = st || null;
    const tri = ou('tri', ''); if (tri !== undefined) { m.sortColumn = (tri && _STOCK_CLE.test(tri)) ? tri : null; m.sortDirection = val('sens', 'asc') === 'desc' ? 'desc' : 'asc'; }
  }
  if (tab === 'valorisation') {
    const v = valEnsureState();
    const c = ou('categorie', ''); if (c !== undefined) v.filterCategorie = c || null;
    const se = ou('section', null); if (se !== undefined) v.filterSousSection = se === null ? null : (se === '~' ? '' : se);
    const tri = ou('tri', ''); if (tri !== undefined) { v.sortColumn = (tri && _STOCK_CLE.test(tri)) ? tri : null; v.sortDirection = val('sens', 'asc') === 'desc' ? 'desc' : 'asc'; }
    const d = ou('date', ''); if (d !== undefined && (!d || _STOCK_JOUR.test(d))) v.snapshotDate = d || null;
    if (u.a('pf_sans_prix') || u.a('pf_negoce') || u.a('pf_avec_stock') || complet) {
      const pf = valPFEnsureState();
      pf.filterSansPrix = u.a('pf_sans_prix'); pf.filterNegoce = u.a('pf_negoce'); pf.filterAvecStock = u.a('pf_avec_stock');
    }
  }
  if (tab === 'negoce') {
    if (!S.ngFilters) S.ngFilters = { refs: [], empls: [], q: '', sort: 'ref', hideRupture: false };
    const f = S.ngFilters;
    const tri = ou('tri', 'ref'); if (tri !== undefined && _STOCK_CLE.test(tri)) f.sort = tri;
    if (u.a('sans_rupture') || complet) f.hideRupture = u.a('sans_rupture');
    if (u.a('references') || complet) f.refs = u.tous('references');
    if (u.a('emplacements') || complet) f.empls = u.tous('emplacements');
  }
  if (tab === 'destockage') {
    const st = dstEtat();
    if (sous && _STOCK_SOUS.destockage.includes(sous)) st.vue = sous; else if (complet) st.vue = 'a_traiter';
    const j = ou('jours', '30'); if (j !== undefined && /^[0-9]{1,4}$/.test(j)) st.jours = Number(j);
  }
}

// Fenêtre demandée par l'adresse : ferme celle qui ne l'est plus, ouvre l'autre.
async function stockModaleUrl(u) {
  let voulue = null;
  Object.keys(_STOCK_MODALES).forEach(cle => {
    const v = u.get(cle, null);
    if (v && _STOCK_MODALES[cle].ok.test(v)) voulue = { cle, id: v };
  });
  // Fenêtres à drapeau (import du référentiel, unités de vente).
  const drapeau = voulue && (voulue.cle === 'import' || voulue.cle === 'unites');
  if ((S.importRefsOpen || S.unitModalOpen) && !drapeau) { S.importRefsOpen = false; S.unitModalOpen = false; render(); }
  if (drapeau) return void (_stockModaleVivante() || (S.importRefsOpen || S.unitModalOpen) || _STOCK_MODALES[voulue.cle].ouvrir(voulue.id));
  const cour = _stockModaleVivante();
  if (cour && (!voulue || cour.cle !== voulue.cle || cour.id !== voulue.id)) _stockFermerModale();
  if (voulue && !_stockModaleVivante()) { try { await _STOCK_MODALES[voulue.cle].ouvrir(voulue.id); } catch (e) {} }
}

// Objets à ouvrir une fois l'onglet chargé (démarrage et Retour/Suivant).
async function stockOuvrirObjetsUrl(u, complet) {
  const tab = S.tab;
  if (tab === 'inventaire') {
    const code = u.get('inventaire', null);
    if (code && code.length <= 60) { if (S.invV2Code !== code || !S.invV2Detail) await loadInventaireEmpl(code); }
    else if (complet && S.invV2Detail) { clearInventaireEmpl(); renderContent(); }
  }
  if (tab === 'negoce') {
    const ref = u.get('negoce', null);
    if (ref && ref.length <= 60) { if (S.ngSelRef !== ref || !S.ngSelDetail) await loadNgDetail(ref); }
    else if (complet && (S.ngSelDetail || S.ngSelDetailLoading)) closeNgDetail();
  }
  if (tab === 'plan-entrepot') {
    const bat = u.get('batiment', null), elt = u.get('element', null);
    const num = v => (/^[0-9]+$/.test(v) ? Number(v) : v);
    if (bat && _STOCK_CLE.test(bat)) { if (String(S.planBat) !== bat) ouvrirPlanBatiment(num(bat)); }
    else if (complet && S.planBat != null) { S.planBat = null; S.planSel = null; buildPlanEntrepot(); }
    if (elt && _STOCK_CLE.test(elt)) { try { selectionnerPlanElement(num(elt), true); } catch (e) {} }
  }
  if (tab === 'traca') {
    const poste = u.get('poste', null);
    const ok = poste && (TRACA_OUTILS.some(o => o.id === poste) || TRACA_POSTES.some(x => x.id === poste));
    const voulu = ok ? poste : null;
    if (voulu !== (S.tracaPoste || null) && (voulu || complet)) { S.tracaPoste = voulu; renderContent(); }
    const ad = voulu === 'specifiques' && window.EtiqSpec && window.EtiqSpec.adresse;
    if (ad) {
      const a = { vue: u.get('vue', null), dossier: u.get('dossier', null), demande: u.get('demande', null),
                  modele: u.get('modele', null), modale: null };
      (ad.cles || []).forEach(k => { const v = u.get(k, null); if (v && v.length <= 60) a.modale = { cle: k, id: v }; });
      try { await ad.aller(a); } catch (e) {}
    }
  }
  await stockModaleUrl(u);
}

// Retour / Suivant du navigateur : on va à l'endroit décrit par l'adresse.
async function stockAllerUrl() {
  const u = MySifaUrl.lire();
  // Seule la fenêtre change : on la ferme ou la rouvre, sans recharger.
  const sansModale = sp => { const c = Object.assign({}, sp); Object.keys(_STOCK_MODALES).forEach(k => delete c[k]); return JSON.stringify(c); };
  const voulu = {}; u.brut.forEach((v, k) => { if (!/^(bloc_|capture$|embed$|next$)/.test(k)) voulu[k] = voulu[k] === undefined ? v : [].concat(voulu[k], v); });
  const actuel = {}; const ap = _stockParamsBase().params;
  Object.keys(ap).forEach(k => { actuel[k] = Array.isArray(ap[k]) ? (ap[k].length === 1 ? ap[k][0] : ap[k]) : ap[k]; });
  if (sansModale(voulu) === sansModale(actuel)) { await stockModaleUrl(u); return; }
  const cible = u.get('tab', 'dashboard');
  const matiere = parseInt(u.get('matiere', '') || '', 10);
  const produit = parseInt(u.get('produit', '') || '', 10);
  const ref = u.get('ref', null);
  const empl = u.get('empl', null);
  let tab = (matiere > 0) ? 'matieres' : ((produit > 0 || ref) ? 'produits-finis' : cible);
  stockLireFiltres(u, tab, true);
  const objetOuvert = !!(S.selProduit || S.selEmpl || S.selMatiere);
  if (tab !== S.tab || objetOuvert) goToTab(tab);
  else renderContent();
  if (tab === 'matieres' && !(matiere > 0)) {
    const cat = u.get('cat', null);
    if (cat) {
      if (!S.matieres) { try { await loadMatieres(); } catch (e) {} }
      const def = mpPillDefs().find(d => d.id === cat);
      if (def) mpOuvrirCategorie(def);
    } else S.matieresAccueil = true;
    renderMatieresView();
  }
  if (matiere > 0) {
    if (!(S.selMatiere && S.selMatiere.matiere && S.selMatiere.matiere.id === matiere)) { try { await loadMatiere(matiere); } catch (e) {} }
    const fiche = u.get('fiche', 'stock', ['stock', 'fournisseurs', 'mouvements']);
    if (S.selMatiere && S.selMatiere.vue !== fiche) { S.selMatiere.vue = fiche; renderContent(); }
  } else if (produit > 0) {
    try { await loadProduit(produit); } catch (e) {}
  } else if (ref) {
    try { await openPfProduitPage(ref, null); } catch (e) {}
  } else if (empl) {
    try { await loadEmplacement(empl); } catch (e) {}
  }
  await stockOuvrirObjetsUrl(u, true);
}
if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_stockUrlPrete && S.user) await stockAllerUrl(); });
}
