/*
 * MySifa — MyExpé : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * MyExpé est servie par le gabarit commun app/web/html.py, qui sert aussi le
 * portail et d'autres applis : ce fichier y est chargé partout mais ne fait
 * rien hors de /expe. Il ne fait que déclarer des fonctions ; S, T, N, Z,
 * set(), render()… appartiennent au script principal et ne sont lus qu'à
 * l'appel.
 *
 * Inventaire du 18/10/2026 (onglets, sous-onglets, filtres, objets, toutes
 * les fenêtres — expe_assets, expe_notes, expe_pilotage, expe_emails,
 * expe_carburant, mysifa_expe_carte.js) :
 *   onglet ; Départs : sous-onglet, jour, fenêtre de départ (édition,
 *   création, duplication), avis transporteur ; Palettes Europe : sous-onglet,
 *   client, statut, statut des contestations, tri, relevé de compte, saisie de
 *   mouvement, contestation ; Pilotage : filtre, mémo, réglages, transport à
 *   programmer ; Emails : filtre, réglages, email ouvert ; Comparateur : la
 *   question posée (poids, palettes, code postal, type) ; Zones : lieu ou
 *   région, type d'envoi ; Devis : nouvelle demande, détail, envoi, saisie
 *   d'une réponse, prospect, modification de demande, relance, suivi
 *   d'engagement ; Transporteurs : fiche et son onglet ; Taxe carburant :
 *   historique déplié, modification, demande ; carte des délais : ouverte,
 *   département sélectionné.
 * Hors adresse, volontairement : le calculateur de poids (lignes en cours de
 * saisie), les recherches texte, la pagination, le petit calendrier de date
 * limite d'un devis (une bulle, pas une fenêtre), la copie d'un texte.
 */
let _expeUrlPrete = false;
const _EXPE_ID = /^[0-9]+$/;
const _expeSurPage = () => location.pathname === '/expe';

// ── Fenêtres posées sur body par une fonction de la page ──────────────
// La fonction est enveloppée (expeEnvelopper) et la fenêtre retenue par
// l'élément qu'elle ajoute : fermée dès qu'il quitte la page, quel que soit
// le chemin (croix, fond, bouton « Annuler », fermeture après envoi).
let _expeSuivi = null;               // { cle, id, avant, el, essais }
function expeFenetreOuverte(cle, id) {
  _expeSuivi = { cle, id: String(id), el: null, essais: 0, avant: new Set(document.body.children) };
  expeSyncUrl();
}
function _expeSuiviVivant() {
  const f = _expeSuivi;
  if (!f) return null;
  if (!f.el) {
    const c = [...document.body.children].filter(n => !f.avant.has(n)
      && /overlay|modal/i.test(String(n.className || '')) && !/toast|tip/i.test(String(n.className || ''))).pop();
    if (c) { f.el = c; f.avant = null; return f; }
    if (++f.essais > 200) { _expeSuivi = null; return null; }
    return f;
  }
  if (!f.el.isConnected) { _expeSuivi = null; return null; }
  return f;
}
// Fenêtre de départ : création ou duplication ne se distinguent pas dans S.
let _expeDepartSource = null;        // { mode, id }
const _EXPE_OUVREURS = [
  // [fonction, clé, valeur(args)] — fenêtres posées sur body
  ['ouvrirEditionDemande',         'modifier_demande',  a => a[0] && a[0].id],
  ['ouvrirRelanceDevis',           'relance',           a => a[0] && a[0].id != null ? a[0].id + ':' + a[1] : null],
  ['ouvrirTimelineDevis',          'suivi_reponse',     a => a[0]],
  ['ouvrirJournalPalettes',        'releve_palettes',   a => a[0] && a[0].key],
  ['ouvrirSaisieMouvementPalettes','mouvement_palettes',a => (a[0] && a[0].key) || 'nouveau'],
  ['ouvrirSaisieContestation',     'contestation',      a => (a[0] && a[0].depart_id) || 'nouvelle'],
];
function expeEnvelopper() {
  _EXPE_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      let v = null;
      try { v = valeur(arguments); } catch (e) {}
      if (v !== null && v !== undefined && v !== '') expeFenetreOuverte(cle, v);
      return orig.apply(this, arguments);
    };
    env.__adresse = true;
    window[nom] = env;
  });
  const d = window.expeOpenDepartModal;
  if (typeof d === 'function' && !d.__adresse) {
    const env = function (prefill, mode) {
      _expeDepartSource = { mode: mode || 'new', id: prefill && prefill.id != null ? prefill.id : null };
      return d.apply(this, arguments);
    };
    env.__adresse = true;
    window.expeOpenDepartModal = env;
  }
}

// ── Fenêtre ouverte, quelle qu'elle soit ──────────────────────────────
function _expeModale() {
  const f = _expeSuiviVivant();               // empilée au-dessus : prioritaire
  if (f) return { cle: f.cle, id: f.id };
  if (S.expeDepartModalOpen) {
    if (S.expeDepartEditId) return { cle: 'depart', id: S.expeDepartEditId };
    const src = _expeDepartSource || {};
    if (src.mode === 'new' && src.id != null) return { cle: 'dupliquer_depart', id: src.id };
    return { cle: 'depart', id: 'nouveau' };
  }
  const dv = S.expeDevisModal;
  if (dv && dv.type) {
    if (dv.type === 'nouvelle') return { cle: 'demande', id: 'nouvelle' };
    if (dv.type === 'detail' && dv.demandeId) return { cle: 'demande', id: dv.demandeId };
    if (dv.type === 'envoi' && dv.demandeId) return { cle: 'envoi_demande', id: dv.demandeId };
    if (dv.type === 'saisie' && dv.demandeId) return { cle: 'reponse', id: (dv.reponseId || 'nouvelle') + ':' + dv.demandeId };
    if (dv.type === 'prospect') return { cle: 'prospect', id: dv.prospectId || 'nouveau' };
  }
  if (typeof N !== 'undefined' && N.avis && N.avis.depart_id) return { cle: 'avis', id: N.avis.depart_id + ':' + (N.avis.sens || 'appreciation') };
  if (S.expePilModal && S.expePilModal.cle) return { cle: 'transport', id: S.expePilModal.cle };
  if (S.expeEmModal && S.expeEmModal.id != null) return { cle: 'email', id: S.expeEmModal.id };
  if (typeof T !== 'undefined' && T.modalOpen) {
    return { cle: 'transporteur', id: T.editId != null ? T.editId : 'nouveau',
             extra: T.modalTab && T.modalTab !== 'fiche' ? { transporteur_onglet: T.modalTab } : null };
  }
  const cb = S.expeCarb;
  if (cb && cb.modal) return { cle: 'demande_taxe', id: 'envoi' };
  if (cb && cb.edit != null) return { cle: 'modifier_taxe', id: cb.edit };
  return null;
}

function expeParams() {
  const p = {};
  const tab = S.expeTab || 'suivi_departs';
  if (tab !== 'suivi_departs') p.onglet = tab;
  let nav = tab;
  if (tab === 'suivi_departs') {
    const sous = S.expeDepartSubTab || 'jour';
    if (sous !== 'jour') { p.sous = sous; nav += '/' + sous; }
    if (sous === 'jour' && S.expeDepartJourDate) p.jour = S.expeDepartJourDate;
  } else if (tab === 'palettes_europe') {
    const sous = S.expePalEurSubTab || 'transporteurs';
    if (sous !== 'transporteurs') { p.sous = sous; nav += '/' + sous; }
    if (S.expePalettesEuropeClientFilter) p.client = S.expePalettesEuropeClientFilter;
    if (S.expePalettesEuropeStatutFilter) p.statut = S.expePalettesEuropeStatutFilter;
    if (S.expePalContestStatut) p.contest_statut = S.expePalContestStatut;
    if (S.expePalSortKey) { p.tri = S.expePalSortKey; if (S.expePalSortDir === 'desc') p.sens = 'desc'; }
  } else if (tab === 'pilotage') {
    if (S.expePilFiltre && S.expePilFiltre !== 'a_faire') p.filtre = S.expePilFiltre;
    if (S.expePilMemoOuvert) p.memo = 'ouvert';
    if (S.expePilReglagesOuvert) { p.reglages = 'ouverts'; nav += '/reglages'; }
  } else if (tab === 'emails') {
    if (S.expeEmFiltre && S.expeEmFiltre !== 'ouverts') p.filtre = S.expeEmFiltre;
    if (S.expeEmReglagesOuvert) { p.reglages = 'ouverts'; nav += '/reglages'; }
  } else if (tab === 'comparateur') {
    const f = S.comparateur_form;
    if (f && f.code_postal_destination) {
      if (f.poids_total_kg) p.poids = String(f.poids_total_kg);
      if (f.nb_palette) p.palettes = String(f.nb_palette);
      p.cp = f.code_postal_destination;
      if (f.type_envoi && f.type_envoi !== 'messagerie') p.envoi = f.type_envoi;
    }
  } else if (tab === 'zones' && typeof Z !== 'undefined' && Z.data) {
    if (String(Z.saisie || '').trim()) p.lieu = String(Z.saisie).trim();
    else if (Z.region) p.region = Z.region;
    if (Z.typeEnvoi && Z.typeEnvoi !== 'affretement') p.envoi = Z.typeEnvoi;
  } else if (tab === 'carburant') {
    const cb = S.expeCarb;
    if (cb && cb.open != null) p.historique_taxe = String(cb.open);
  }
  // Carte des délais (panneau flottant de MyExpé)
  if (typeof C !== 'undefined' && C.panelOpen) {
    p.carte = 'ouverte'; nav += '/carte';
    if (C.selected) p.departement = String(C.selected);
  }
  const mo = _expeModale();
  if (mo) { p[mo.cle] = String(mo.id); nav += '/' + mo.cle; if (mo.extra) Object.assign(p, mo.extra); }
  return { params: p, nav };
}

function expeSyncUrl() {
  if (!_expeUrlPrete || !_expeSurPage() || !window.MySifaUrl || !S.user || S.app !== 'expe') return;
  try { const r = expeParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

function expeUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; expeSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

// ── Lecture ───────────────────────────────────────────────────────────
const _EXPE_ONGLETS = ['pilotage', 'emails', 'suivi_departs', 'palettes_europe', 'comparateur', 'devis', 'poids',
  'transporteurs', 'carburant', 'zones', 'prospects'];

// Onglet et filtres, posés AVANT le premier rendu de l'onglet (qui charge ses
// données avec). Ancienne forme « #devis » relue une fois.
function expeLireFiltres(u, complet) {
  const h = MySifaUrl.hashHerite();
  const tab = u.get('onglet', null, _EXPE_ONGLETS) || (_EXPE_ONGLETS.indexOf(h) !== -1 ? h : 'suivi_departs');
  S.expeTab = tab;
  const ou = (k, def) => (u.a(k) ? u.get(k, def) : (complet ? def : undefined));
  if (tab === 'suivi_departs') {
    const s = u.get('sous', 'jour', ['jour', 'historique']);
    if (u.a('sous') || complet) S.expeDepartSubTab = s;
    const j = ou('jour', ''); if (j !== undefined && (!j || /^\d{4}-\d{2}-\d{2}$/.test(j))) S.expeDepartJourDate = j;
  } else if (tab === 'palettes_europe') {
    const s = u.get('sous', 'transporteurs', ['transporteurs', 'suivi', 'contest', 'recap']);
    if (u.a('sous') || complet) S.expePalEurSubTab = s;
    const c = ou('client', ''); if (c !== undefined) S.expePalettesEuropeClientFilter = c;
    const st = ou('statut', ''); if (st !== undefined) S.expePalettesEuropeStatutFilter = st;
    const cs = ou('contest_statut', ''); if (cs !== undefined) S.expePalContestStatut = cs;
    const tri = ou('tri', ''); if (tri !== undefined) { S.expePalSortKey = tri || null; S.expePalSortDir = u.get('sens', 'asc') === 'desc' ? 'desc' : 'asc'; }
  } else if (tab === 'pilotage') {
    const f = ou('filtre', ''); if (f !== undefined && (!f || EXPE_PIL_FILTRES.some(x => x.key === f))) S.expePilFiltre = f || null;
    if (u.a('memo') || complet) S.expePilMemoOuvert = u.a('memo');
    if (u.a('reglages') || complet) S.expePilReglagesOuvert = u.a('reglages');
  } else if (tab === 'emails') {
    const f = ou('filtre', ''); if (f !== undefined && (!f || EXPE_EM_FILTRES.some(x => x.key === f))) S.expeEmFiltre = f || null;
    if (u.a('reglages') || complet) S.expeEmReglagesOuvert = u.a('reglages');
  }
}

// Attend une donnée chargée par l'onglet (10 s au plus).
function _expeAttendre(cond) {
  return new Promise(ok => {
    let n = 0;
    const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250);
  });
}
const _expeDeux = v => { const i = String(v).indexOf(':'); return i < 0 ? [String(v), ''] : [String(v).slice(0, i), String(v).slice(i + 1)]; };
const _expeDeparts = () => [].concat(S.expeDepartList || [], S.expeDepartHist || []);

const _EXPE_REOUVRIR = {
  depart: async v => {
    if (v === 'nouveau') return expeOpenDepartModal(null, 'new');
    if (!_EXPE_ID.test(v)) return;
    await _expeAttendre(() => _expeDeparts().some(r => String(r.id) === v));
    const r = _expeDeparts().find(x => String(x.id) === v); if (r) expeOpenDepartModal(r, 'edit');
  },
  dupliquer_depart: async v => {
    await _expeAttendre(() => _expeDeparts().some(r => String(r.id) === v));
    const r = _expeDeparts().find(x => String(x.id) === v); if (r) expeOpenDepartModal(r, 'new');
  },
  avis: async v => {
    const [id, sens] = _expeDeux(v);
    await _expeAttendre(() => _expeDeparts().some(r => String(r.id) === id));
    const r = _expeDeparts().find(x => String(x.id) === id); if (r) expeOuvrirAvis(r, sens || 'appreciation');
  },
  demande: v => (v === 'nouvelle' ? ouvrirModalNouvelleDemande() : (_EXPE_ID.test(v) ? ouvrirDetailDemande(Number(v)) : null)),
  envoi_demande: v => (_EXPE_ID.test(v) ? ouvrirModalEnvoi(Number(v)) : null),
  reponse: async v => {
    const [rid, did] = _expeDeux(v);
    if (!_EXPE_ID.test(did)) return;
    if (rid === 'nouvelle') return ouvrirSaisieReponse({}, Number(did));
    // La réponse se retrouve dans le détail de sa demande.
    try {
      const data = await api('/api/expe/devis/demandes/' + did);
      const r = (data.reponses || []).find(x => String(x.id) === rid);
      if (r) ouvrirSaisieReponse(r, Number(did));
    } catch (e) {}
  },
  prospect: async v => {
    if (v === 'nouveau') return ouvrirModalProspect(null);
    await _expeAttendre(() => Array.isArray(S.prospects));
    ouvrirModalProspect(Number(v));
  },
  modifier_demande: async v => {
    try { const data = await api('/api/expe/devis/demandes/' + v); if (data && data.demande) ouvrirEditionDemande(data.demande); } catch (e) {}
  },
  relance: async v => {
    const [rid, did] = _expeDeux(v);
    try {
      const data = await api('/api/expe/devis/demandes/' + did);
      const r = (data.reponses || []).find(x => String(x.id) === rid);
      if (r) ouvrirRelanceDevis(r, Number(did));
    } catch (e) {}
  },
  suivi_reponse: v => (_EXPE_ID.test(v) ? ouvrirTimelineDevis(Number(v)) : null),
  releve_palettes: async v => {
    await _expeAttendre(() => S.expePalettesEuropeData);
    const t = ((S.expePalettesEuropeData || {}).recap_transporteurs || []).find(x => String(x.key) === v);
    if (t) ouvrirJournalPalettes(t);
  },
  mouvement_palettes: async v => {
    if (v === 'nouveau') return ouvrirSaisieMouvementPalettes(null);
    await _expeAttendre(() => S.expePalettesEuropeData);
    const t = ((S.expePalettesEuropeData || {}).recap_transporteurs || []).find(x => String(x.key) === v);
    ouvrirSaisieMouvementPalettes(t || null);
  },
  contestation: async v => {
    if (v === 'nouvelle') return ouvrirSaisieContestation(null);
    await _expeAttendre(() => S.expePalettesEuropeData || _expeDeparts().length);
    const r = [].concat((S.expePalettesEuropeData || {}).departs || [], _expeDeparts()).find(x => String(x.id) === v);
    ouvrirSaisieContestation(r ? { transporteur_id: r.transporteur_id, transporteur: r.transporteur, depart_id: r.id,
      client: r.client, recepisse: r.arc || r.no_bl, nb_palette: r.nb_palette, date: (r.date_enlevement || '').slice(0, 10) } : null);
  },
  transport: async v => {
    await _expeAttendre(() => S.expePilotage && S.expePilotage.envois);
    const env = ((S.expePilotage || {}).envois || []).find(x => String(x.cle_envoi) === v);
    if (env) expePilOuvrirTransport(env);
  },
  email: v => expeEmOuvrir(v),
  transporteur: async (v, u) => {
    if (v !== 'nouveau') await _expeAttendre(() => (T.list || []).some(x => String(x.id) === v));
    openTransporteurModal(v === 'nouveau' ? null : Number(v));
    const o = u.get('transporteur_onglet', null);
    if (o && T.modalOpen) setTransporteurModalTab(o);
    render();
  },
  demande_taxe: async () => { await _expeAttendre(() => S.expeCarb && S.expeCarb.list); expeCarbOuvrirDemande(); },
  modifier_taxe: async v => { await _expeAttendre(() => S.expeCarb && S.expeCarb.list); S.expeCarb.edit = isNaN(Number(v)) ? v : Number(v); render(); },
};

function _expeFermerModale(mo) {
  if (!mo) return;
  if (_expeSuivi && mo.cle === _expeSuivi.cle) { const el = _expeSuivi.el; _expeSuivi = null; if (el) el.remove(); return; }
  if (mo.cle === 'depart' || mo.cle === 'dupliquer_depart') { if (typeof expeCloseDepartModal === 'function') expeCloseDepartModal(); else set({ expeDepartModalOpen: false }); }
  else if (['demande', 'envoi_demande', 'reponse', 'prospect'].indexOf(mo.cle) !== -1) fermerExpeDevisModal();
  else if (mo.cle === 'avis') expeFermerAvis();
  else if (mo.cle === 'transport') _expePilModalFermer();
  else if (mo.cle === 'email') set({ expeEmModal: null });
  else if (mo.cle === 'transporteur') { closeTransporteurModal(); render(); }
  else if (mo.cle === 'demande_taxe') { S.expeCarb.modal = null; render(); }
  else if (mo.cle === 'modifier_taxe') { S.expeCarb.edit = null; render(); }
}

async function expeModaleUrl(u) {
  let voulue = null;
  Object.keys(_EXPE_REOUVRIR).forEach(cle => { const v = u.get(cle, null); if (v && v.length <= 120) voulue = { cle, id: v }; });
  const cour = _expeModale();
  if (cour && (!voulue || cour.cle !== voulue.cle || String(cour.id) !== String(voulue.id))) _expeFermerModale(cour);
  if (voulue && !_expeModale()) { try { await _EXPE_REOUVRIR[voulue.cle](voulue.id, u); } catch (e) {} }
}

// Ce que l'onglet affiché demande en plus de ses filtres : la question du
// comparateur, la destination des zones, l'historique de taxe, la carte.
async function expeObjetsUrl(u, complet) {
  const tab = S.expeTab;
  if (tab === 'comparateur' && u.get('cp', null)) {
    await _expeAttendre(() => document.getElementById('cmp-cp'));
    const v = (id, x) => { const el = document.getElementById(id); if (el && x != null) el.value = x; };
    v('cmp-poids', u.get('poids', '')); v('cmp-pal', u.get('palettes', '')); v('cmp-cp', u.get('cp', ''));
    v('cmp-type', u.get('envoi', 'messagerie'));
    const f = S.comparateur_form || {};
    if (String(f.code_postal_destination || '') !== u.get('cp', '') || String(f.poids_total_kg || '') !== u.get('poids', '')
        || String(f.nb_palette || '') !== u.get('palettes', '')) lancerComparateur();
  }
  if (tab === 'zones' && (u.get('lieu', null) || u.get('region', null))) {
    Z.typeEnvoi = u.get('envoi', 'affretement');
    const lieu = u.get('lieu', null);
    if (lieu) { if (Z.saisie !== lieu || !Z.data) { Z.saisie = lieu; expeZonesRechercher(); } }
    else if (Z.region !== u.get('region') || !Z.data) expeZonesClicRegion(u.get('region'));
  }
  if (tab === 'carburant') {
    const h = u.get('historique_taxe', null);
    await _expeAttendre(() => S.expeCarb && S.expeCarb.list);
    const cb = S.expeCarb || {};
    if (h && String(cb.open) !== h) expeCarbToggleHist(isNaN(Number(h)) ? h : Number(h));
    else if (!h && complet && cb.open != null) expeCarbToggleHist(cb.open);
  }
  const carte = u.a('carte');
  if (typeof C !== 'undefined' && (carte !== !!C.panelOpen) && (carte || complet) && typeof setExpeCarteOpen === 'function') setExpeCarteOpen(carte);
  if (typeof C !== 'undefined' && carte && u.get('departement', null)) C.selected = u.get('departement');
  await expeModaleUrl(u);
}

// Démarrage : appelé par renderExpe() au premier rendu, à la place de
// l'ancienne lecture du hash. Les objets attendent leurs données, puis
// l'adresse suit l'écran.
let _expeDemarre = false;
function expeDemarrerUrl() {
  if (_expeDemarre || !_expeSurPage() || !window.MySifaUrl) return;
  _expeDemarre = true;
  const u = MySifaUrl.lire();
  expeLireFiltres(u, false);
  expeEnvelopper();
  setTimeout(async () => {
    try { await expeObjetsUrl(u, false); } catch (e) {}
    _expeUrlPrete = true;
    expeSyncUrl();
    expeUrlObserver();
  }, 0);
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async u => {
    if (!_expeUrlPrete || !_expeSurPage() || !S.user) return;
    expeLireFiltres(u, true);
    // Le rendu recharge l'onglet s'il a changé (renderExpe compare la clé de
    // chargement) ; sinon il redessine avec les filtres relus.
    render();
    await expeObjetsUrl(u, true);
  });
}
