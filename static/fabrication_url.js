/*
 * MySifa — Saisie Prod : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé AVANT le script principal de /fabrication : il ne fait que déclarer
 * des fonctions et s'abonner au Retour du navigateur. S, set(), render(),
 * switchFabTab()… appartiennent au script principal ; ils ne sont lus qu'à
 * l'appel (scripts classiques : les `let` de premier niveau partagent la même
 * portée globale).
 *
 * Périmètre (décision du 18/10/2026, voir la règle) — l'écran de saisie est
 * piloté par le SERVEUR (machine du jour, dossier en cours, état calage /
 * production / arrêt) : l'adresse ne le porte pas. Elle porte la navigation
 * et la consultation :
 *   onglet, sous-onglet OF, vue admin + machine choisie par l'admin,
 *   repiquage (dossier ouvert, son onglet),
 *   fenêtres : fiche technique, OF, import d'OF, traçabilité d'un dossier,
 *   commentaire d'une saisie ou d'une bobine ouvert depuis la liste,
 *   correction d'une bobine scannée, correction d'une saisie de repiquage,
 *   mémoire produit, mouvements de stock de l'onglet Stock (entrée / sortie
 *   MP, entrée / sortie Z1 — formulaires indépendants de la saisie).
 * Hors adresse, volontairement : les étapes d'une saisie en cours (choix du
 * dossier à démarrer, début, fin, compteur, commentaire imposé par un seuil,
 * changement d'outil, annulation, dossier fictif, tête de sortie), les
 * confirmations de la traçabilité au scan, l'impression (fenêtre séparée du
 * navigateur) et les annonces de mise à jour. Rouvrir l'une d'elles au
 * rafraîchissement d'une tablette ferait saisir sur un état périmé.
 */
let _fabUrlPrete = false;          // posé à la fin d'init()
const _FAB_ONGLETS = ['saisie', 'print', 'traca', 'of', 'stats'];
const _FAB_ID = /^[0-9]+$/;

// Fenêtre de traçabilité (DOM, hors de S) : retenue avec son élément, fermée
// dès qu'il quitte la page — elle se ferme par la croix, le fond, ou une
// autre fenêtre posée dans #mroot.
let _fabTraca = null;              // { ref, el }
function fabTracaOuverte(ref) {
  const mr = document.getElementById('mroot');
  _fabTraca = { ref: String(ref), el: mr ? mr.firstElementChild : null };
}
function _fabTracaVivante() {
  if (_fabTraca && _fabTraca.el && _fabTraca.el.isConnected) return _fabTraca;
  _fabTraca = null;
  return null;
}

// Fenêtres ouvertes par une fonction de la page puis rendues par un module
// partagé (mysifa_stock_modals.js, mysifa_bobine_edit.js) : la fonction est
// enveloppée au démarrage (fabEnvelopper) et la fenêtre retenue par l'élément
// qu'elle ajoute à la page — fermée dès qu'il n'y est plus.
let _fabSuivi = null;              // { cle, id, avant, el, essais }
function fabFenetreOuverte(cle, id) {
  const m = document.getElementById('mroot');
  _fabSuivi = { cle, id: String(id), el: null, essais: 0,
    avant: new Set([...document.body.children, ...(m ? m.children : [])]) };
  fabSyncUrl();
}
function _fabSuiviVivant() {
  const f = _fabSuivi;
  if (!f) return null;
  if (!f.el) {
    const m = document.getElementById('mroot');
    const dansMroot = m ? [...m.children].filter(n => !f.avant.has(n)) : [];
    const surBody = [...document.body.children].filter(n => !f.avant.has(n)
      && /overlay|modal|drawer|backdrop|fond/i.test(String(n.className || '')) && !/toast/i.test(String(n.className || '')));
    const c = dansMroot[dansMroot.length - 1] || surBody[surBody.length - 1];
    if (c) { f.el = c; f.avant = null; return f; }
    if (++f.essais > 200) { _fabSuivi = null; return null; }   // jamais apparue
    return f;                                                    // ouverture en cours
  }
  if (!f.el.isConnected) { _fabSuivi = null; return null; }
  return f;
}
const _FAB_OUVREURS = [
  // [fonction de la page, clé, valeur(args)]
  ['_stockGoTo', 'mouvement', a => (a[0] || '') + (a[1] && a[1].id != null ? ':' + a[1].id : '')],
  ['tracaOuvrirEditBobine', 'bobine', a => a[0] && a[0].id],
];
function fabEnvelopper() {
  _FAB_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      let v = null;
      try { v = valeur(arguments); } catch (e) {}
      if (v !== null && v !== undefined && v !== '') fabFenetreOuverte(cle, v);
      return orig.apply(this, arguments);
    };
    env.__adresse = true;
    window[nom] = env;
  });
}

// Mémoire produit (mysifa_produit_memoire.js, surcouche) : elle signale ce
// qu'elle montre. Branchée au premier rendu (module chargé avant, mais
// l'abonnement attend que la page soit prête).
let _fabPmem = null;               // { cle, id, onglet }
let _fabPmemSilence = false;
function _fabPmemBrancher() {
  const M = window.MySifaProduitMemoire;
  if (!M || !M.surAdresse || M.__fabBranche) return;
  M.__fabBranche = true;
  M.surAdresse(e => { if (_fabPmemSilence) return; _fabPmem = e || null; fabSyncUrl(); });
}

function _fabModale() {
  if (S.ficheEditModal && S.ficheEditModal.id) return { cle: 'fiche', id: S.ficheEditModal.id };
  if (S.ofEditModal && S.ofEditModal.id) return { cle: 'of', id: S.ofEditModal.id };
  if (S.ofImportModal) return { cle: 'import_of', id: 'fichier' };
  // Commentaire : seulement celui qu'on ouvre depuis une liste. Celui qu'un
  // dépassement de seuil impose après une saisie est une étape de la saisie.
  if (S.showCommentModal && !S.explicationSeuil && S.commentSaisieId) return { cle: 'commentaire', id: S.commentSaisieId };
  if (S.showTracaCommentModal && S.tracaCommentId) return { cle: 'commentaire_bobine', id: S.tracaCommentId };
  if (S.showRepiquageEditModal && S.repiquageEditSaisie && S.repiquageEditSaisie.id) return { cle: 'repiquage_modifier', id: S.repiquageEditSaisie.id };
  const f = _fabSuiviVivant();
  if (f) return { cle: f.cle, id: f.id };
  const t = _fabTracaVivante();
  if (t) return { cle: 'tracabilite', id: t.ref };
  if (_fabPmem && document.getElementById('pmem-overlay')) {
    return { cle: _fabPmem.cle, id: _fabPmem.id,
             extra: (_fabPmem.onglet && _fabPmem.onglet !== 'series') ? { produit_onglet: _fabPmem.onglet } : null };
  }
  return null;
}

function fabParams() {
  const p = {};
  const onglet = S.fabTab || 'saisie';
  if (onglet !== 'saisie') p.onglet = onglet;
  let nav = onglet;
  if (onglet === 'of' && S.ofSubTab && S.ofSubTab !== 'of') { p.sous = S.ofSubTab; nav += '/' + S.ofSubTab; }
  if (S.saisieViewMode === 'admin') { p.vue = 'admin'; nav += '/admin'; }
  if (S.adminMachineId) p.machine = String(S.adminMachineId);
  if (onglet === 'saisie' && S.repiquageView === 'dossier' && S.repiquageDossierActif) {
    p.repiquage = String(S.repiquageDossierActif);
    nav += '/rep:' + S.repiquageDossierActif;
    if (S.repiquageDossierTab && S.repiquageDossierTab !== 'saisie') { p.repiquage_onglet = S.repiquageDossierTab; nav += '/' + S.repiquageDossierTab; }
  }
  const mo = _fabModale();
  if (mo) { p[mo.cle] = String(mo.id); nav += '/' + mo.cle; if (mo.extra) Object.assign(p, mo.extra); }
  return { params: p, nav };
}

function fabSyncUrl() {
  _fabPmemBrancher();
  if (!_fabUrlPrete || !window.MySifaUrl || !S.user) return;
  try { const r = fabParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

// Recalcul à chaque changement d'affichage : render(), mais aussi les
// fenêtres posées hors de render() (traçabilité, mémoire produit).
function fabUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; fabSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

// Onglet, sous-onglet, vue admin et machine lus dans l'adresse. Ancienne
// forme « #traca » relue une fois, puis réécrite.
function fabLireNavigation(u) {
  const h = MySifaUrl.hashHerite();
  const onglet = u.get('onglet', null, _FAB_ONGLETS) || (_FAB_ONGLETS.indexOf(h) !== -1 ? h : 'saisie');
  const sous = u.get('sous', 'of', ['of', 'fiche']);
  const admin = u.get('vue', null) === 'admin';
  const m = u.get('machine', null);
  return { onglet, sous, admin, machine: (m && _FAB_ID.test(m)) ? Number(m) : null,
           repiquage: u.get('repiquage', null),
           repOnglet: u.get('repiquage_onglet', 'saisie', ['saisie', 'historique', 'discussion']) };
}

function _fabTrouver(id, ...listes) {
  for (const l of listes) {
    const arr = Array.isArray(l) ? l : (l && (Array.isArray(l.rows) ? l.rows : (Array.isArray(l.saisies) ? l.saisies : null)));
    const x = (arr || []).find(r => r && String(r.id) === String(id));
    if (x) return x;
  }
  return null;
}

const _FAB_REOUVRIR = {
  fiche: async v => {
    if (!_FAB_ID.test(v)) return;
    if (!(S.fiches || []).length && typeof loadFiches === 'function') await loadFiches();
    const r = _fabTrouver(v, S.fiches); if (r) openFicheEditModal(r);
  },
  of: v => { const r = _fabTrouver(v, S.ofImports); if (r) openOfEditModal(r); },
  import_of: () => openOfImportModal(),
  tracabilite: v => openTracabiliteModal(v),
  commentaire: v => {
    const s = _fabTrouver(v, S.saisies, S.saisiesAdmin, S.lastSaisie ? [S.lastSaisie] : []);
    set({ showCommentModal: true, explicationSeuil: null, commentSaisieId: Number(v), commentText: (s && s.commentaire) || '' });
  },
  commentaire_bobine: v => {
    const m = _fabTrouver(v, S.tracaMatieres);
    set({ showTracaCommentModal: true, tracaCommentId: Number(v), tracaCommentText: (m && m.commentaire) || '' });
  },
  mouvement: v => {
    const i = v.indexOf(':');
    const action = i < 0 ? v : v.slice(0, i), pid = i < 0 ? null : v.slice(i + 1);
    if (['entree-mp', 'sortie-mp', 'entree-z1', 'sortie-z1'].indexOf(action) === -1) return;
    const r = pid ? _fabTrouver(pid, S.stockProdZ1 && S.stockProdZ1.refs) : null;
    _stockGoTo(action, r ? _z1Produit(r) : undefined);
  },
  bobine: v => { const m = _fabTrouver(v, S.tracaMatieres); if (m) tracaOuvrirEditBobine(m); },
  repiquage_modifier: v => { const r = _fabTrouver(v, S.repiquageHistorique, S.repiquageEtat, S.saisies); if (r) openRepiquageEditModal(r); },
  produit: (v, u) => { const M = window.MySifaProduitMemoire; if (M) M.openFiche(v, { onglet: u.get('produit_onglet', null) }); },
  historique: (v, u) => { const M = window.MySifaProduitMemoire; if (M) M.openHistorique(v, { onglet: u.get('produit_onglet', null) }); },
  produits: () => { const M = window.MySifaProduitMemoire; if (M) M.openListe(); },
};

// Ferme la fenêtre ouverte sans toucher à l'adresse (Retour du navigateur).
function _fabFermerModale(mo) {
  if (!mo) return;
  if (_fabSuivi && mo.cle === _fabSuivi.cle) {
    const el = _fabSuivi.el, m = document.getElementById('mroot');
    _fabSuivi = null;
    if (el) { if (m && m.contains(el)) m.innerHTML = ''; else el.remove(); }
    return;
  }
  if (mo.cle === 'fiche') closeFicheEditModal();
  else if (mo.cle === 'of') closeOfEditModal();
  else if (mo.cle === 'import_of') closeOfImportModal();
  else if (mo.cle === 'tracabilite') { closeTracabiliteModal(); _fabTraca = null; }
  else if (mo.cle === 'commentaire') set({ showCommentModal: false, commentSaisieId: null });
  else if (mo.cle === 'commentaire_bobine') set({ showTracaCommentModal: false, tracaCommentId: null });
  else if (mo.cle === 'repiquage_modifier') set({ showRepiquageEditModal: false, repiquageEditSaisie: null });
  else if (window.MySifaProduitMemoire) {
    _fabPmemSilence = true;
    try { window.MySifaProduitMemoire.fermer(); } finally { _fabPmemSilence = false; }
    _fabPmem = null;
  }
}

async function fabModaleUrl(u) {
  let voulue = null;
  Object.keys(_FAB_REOUVRIR).forEach(cle => {
    const v = u.get(cle, null);
    if (v && v.length <= 120) voulue = { cle, id: v };
  });
  const cour = _fabModale();
  if (cour && (!voulue || cour.cle !== voulue.cle || String(cour.id) !== String(voulue.id))) _fabFermerModale(cour);
  if (voulue && !_fabModale()) { try { await _FAB_REOUVRIR[voulue.cle](voulue.id, u); } catch (e) {} }
}

// Applique l'adresse : au démarrage (après loadSession) et au Retour.
async function fabAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const n = fabLireNavigation(u);
  const isAdm = !!(S.user && ['superadmin', 'administration', 'administration_ventes', 'administration_technique', 'direction']
    .indexOf(S.user.role) !== -1);
  if (isAdm) {
    // Au démarrage, init() a déjà posé et chargé la vue admin demandée.
    const vue = n.admin ? 'admin' : 'operator';
    if (complet && vue !== S.saisieViewMode) setSaisieViewMode(vue);
    if (n.machine !== S.adminMachineId && (n.machine || complet) && (!n.machine || (S.machines || []).some(m => m.id === n.machine))) {
      set({ adminMachineId: n.machine });
      await loadSession();
    }
  }
  if (n.onglet !== (S.fabTab || 'saisie')) await switchFabTab(n.onglet);
  if (n.onglet === 'of' && n.sous !== (S.ofSubTab || 'of')) {
    set({ ofSubTab: n.sous });
    if (n.sous === 'fiche') { await loadFiches(); render(); }
  }
  if (n.onglet === 'saisie') {
    if (n.repiquage) {
      if (!(S.repiquageView === 'dossier' && String(S.repiquageDossierActif) === n.repiquage)) openRepiquageDossier(n.repiquage);
      if (n.repOnglet !== (S.repiquageDossierTab || 'saisie')) repiquageSwitchDossierTab(n.repOnglet);
    } else if (complet && S.repiquageView === 'dossier') {
      closeRepiquageDossier();
    }
  }
  await fabModaleUrl(u);
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_fabUrlPrete && S.user) await fabAllerUrl(true); });
}
