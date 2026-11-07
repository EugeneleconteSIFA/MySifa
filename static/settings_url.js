/*
 * MySifa — Paramètres (/settings) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/settings_page.py ; ne fait que déclarer
 * des fonctions. La page appelle settingsEnvelopper() en tête de son script
 * (toutes ses fonctions sont alors déclarées, aucune n'est encore liée à un
 * bouton), puis settingsDemarrerUrl() une fois l'onglet initial ouvert.
 *
 * La page n'a pas de rendu central : comme MyStock, un MutationObserver
 * recalcule l'adresse après tout changement d'affichage (regroupé sur 30 ms).
 *
 * Inventaire du 07/11/2026 (onglet = `onglet`, Vue d'ensemble par défaut) :
 *   users         role
 *   fournisseurs  ffsc fgrp fcat fcert ftra fact fview (clés déjà en usage,
 *                 conservées), f (fiche) + fonglet, fgroupe (fiche groupe)
 *   clients       etat
 *   machines      sous (horaires|metrage|nom|postes), machine
 *   operations    retires
 *   maintenance   sous (codes|alertes|libres|usure), alertes (type d'alerte)
 *   audit         module, action
 *   fsc           du, au (1er janvier → aujourd'hui par défaut)
 *   printers      sous ; promote : sous ; encres : sous
 *   blocs         section (blocs|boutons|usages)
 *   formations    statut
 *   coherence     famille, statut (module settings_coherence.js)
 *   iausage       ia_* (module settings_ia_usage.js, clés conservées)
 *   perf          jours (module settings_perf.js, 30 par défaut)
 * Fenêtres (SET_FENETRES) : utilisateur, fusion, doublons, contact, groupe,
 *   annonce, apercu_maj, seuil, operation, code, piece, documents, rattacher,
 *   promouvoir, alerte, apercu_alerte, reglages=alertes, appairer, couverture,
 *   client (+ client_onglet), imprimante, modele, assistant, couleur.
 * Hors adresse : recherches texte, pagination du journal, formulaires de
 * création toujours visibles (nouvel utilisateur, nouveau fournisseur),
 * import de clients (étape d'un geste : il part d'un fichier), confirmations,
 * explication d'un écart de cohérence (écart à justifier), requête SQL.
 */
let _setUrlPret = false;
let _setSyncPrevue = false;
const _setOuvertures = {};   // cle -> { val, t, el }
let _setHorloge = 0;

function _setVisible(el) {
  if (!el || !el.isConnected) return false;
  if (el.classList.contains('hidden') || el.classList.contains('f2-hide')) return false;
  const st = getComputedStyle(el);
  return st.display !== 'none' && st.visibility !== 'hidden';
}

function _setAttendre(cond, delai) {
  return new Promise(resolve => {
    const fin = Date.now() + (delai || 6000);
    (function tour() {
      let ok = false;
      try { ok = !!cond(); } catch (e) { ok = false; }
      if (ok || Date.now() > fin) return resolve(ok);
      setTimeout(tour, 80);
    })();
  });
}

function _setOnglet() {
  const b = document.querySelector('.nav-btn[data-tab].active');
  return (b && b.dataset.tab) || 'menu';
}

// ── Filtres simples : un champ, une clé ──────────────────────────────────
function _setAujourdhui() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
const SET_FILTRES = {
  users:      [{ cle: 'role', id: 'users-role-filter' }],
  clients:    [{ cle: 'etat', id: 'cli-filter-etat' }],
  machines:   [{ cle: 'machine', id: 'mac-select', defaut: el => (el.options[0] || {}).value || '' }],
  operations: [{ cle: 'retires', id: 'outil-inactifs', type: 'case' }],
  audit:      [{ cle: 'module', id: 'audit-filter-module' }, { cle: 'action', id: 'audit-filter-action' }],
  fsc:        [{ cle: 'du', id: 'fsc-du', defaut: () => new Date().getFullYear() + '-01-01', motif: /^\d{4}-\d{2}-\d{2}$/ },
               { cle: 'au', id: 'fsc-au', defaut: _setAujourdhui, motif: /^\d{4}-\d{2}-\d{2}$/ }],
  formations: [{ cle: 'statut', id: 'fmt-filter-status' }],
};

// ── Sous-onglets : boutons dont l'un porte .active ───────────────────────
const SET_SOUS = {
  machines:    { sel: '[data-macsub]', attr: 'macsub', prefixe: 'mac-' },
  maintenance: { sel: '[data-maintsub]', attr: 'maintsub', prefixe: 'maint-subtab-' },
  printers:    { sel: '[data-prsub]', attr: 'prsub', prefixe: '' },
  promote:     { sel: '[data-pmsub]', attr: 'pmsub', prefixe: '' },
  encres:      { sel: '[data-encsub]', attr: 'encsub', prefixe: '' },
};
function _setSousActif(d) {
  const tous = Array.from(document.querySelectorAll(d.sel));
  if (!tous.length) return null;
  const actif = tous.find(b => b.classList.contains('active') || b.getAttribute('aria-selected') === 'true');
  const v = actif ? actif.dataset[d.attr] : null;
  const premier = tous[0].dataset[d.attr];
  return { v: v, premier: premier };
}

// ── Fenêtres ─────────────────────────────────────────────────────────────
// fn : fonction globale qui ouvre ; val(args) : valeur écrite ; el : élément
// affiché (sinon, l'élément que l'ouverture a ajouté à <body>) ; rouvrir(v) ;
// fermer() pour un Retour du navigateur (sinon l'élément est retiré/masqué).
const _SET_ID = v => (v === null || v === undefined || v === '') ? 'nouveau' : String(v);
const _SET_NUM = v => (v === 'nouveau' || v === 'nouvelle') ? null : Number(v);
const SET_FENETRES = [
  { onglet: 'users', cle: 'utilisateur', fn: 'openEdit', val: a => a[0],
    rouvrir: v => openEdit(Number(v)) },
  { onglet: 'fournisseurs', cle: 'fusion', fn: 'openMergeFournisseurModal', val: a => a[0],
    rouvrir: async v => { await _setAttendre(() => fournisseursAll.length); openMergeFournisseurModal(Number(v)); } },
  { onglet: 'fournisseurs', cle: 'doublons', fn: 'openDoublonsModal', val: () => '1',
    rouvrir: () => openDoublonsModal() },
  { onglet: 'fournisseurs', cle: 'contact', fn: 'openContactSubModal', val: a => _SET_ID(a[1]),
    rouvrir: async v => {
      await _setAttendre(() => f2Id && f2Cache[f2Id]);
      if (!f2Id) return;
      const fid = f2Id;
      openContactSubModal(fid, _SET_NUM(v), async () => { delete f2Cache[fid]; await openFournisseurFiche(fid, true); });
    } },
  { onglet: 'updates', cle: 'annonce', fn: 'openNewUpdateModal', el: '#upd-modal-overlay', val: () => 'nouvelle',
    rouvrir: async v => { if (v === 'nouvelle') return openNewUpdateModal();
      await _setAttendre(() => typeof _updatesData !== 'undefined' && _updatesData.length); openEditUpdateModal(Number(v)); },
    fermer: () => closeNewUpdateModal() },
  { onglet: 'updates', cle: 'annonce', fn: 'openEditUpdateModal', el: '#edit-upd-modal-overlay', val: a => a[0],
    rouvrir: async v => { if (v === 'nouvelle') return openNewUpdateModal();
      await _setAttendre(() => typeof _updatesData !== 'undefined' && _updatesData.length); openEditUpdateModal(Number(v)); },
    fermer: () => closeEditUpdateModal() },
  { onglet: 'updates', cle: 'apercu_maj', fn: 'showUpdatePreview', val: a => a[0],
    rouvrir: async v => { await _setAttendre(() => typeof _updatesData !== 'undefined' && _updatesData.length); showUpdatePreview(Number(v)); } },
  { onglet: 'seuils', cle: 'seuil', fn: 'openSeuilForm', el: '#seuil-form-wrap', val: a => _SET_ID(a[0]),
    rouvrir: async v => { if (v !== 'nouveau') await _setAttendre(() => document.querySelector('#seuils-list, #panel-seuils table')); openSeuilForm(_SET_NUM(v)); },
    fermer: () => closeSeuilForm() },
  { onglet: 'operations', cle: 'operation', fn: 'openOpForm', el: '#op-form-wrap', val: a => _SET_ID(a[0]),
    rouvrir: async v => { if (v !== 'nouveau') await _setAttendre(() => document.querySelector('#panel-operations .op-row, #panel-operations tr')); openOpForm(v === 'nouveau' ? null : v); },
    fermer: () => closeOpForm() },
  { onglet: 'maintenance', cle: 'code', fn: 'openMaintForm', el: '#maint-form-wrap', val: a => _SET_ID(a[0]),
    rouvrir: async v => { await _setAttendre(() => (window._maintItems || []).length || v === 'nouveau'); openMaintForm(v === 'nouveau' ? null : v); },
    fermer: () => closeMaintForm() },
  { onglet: 'maintenance', cle: 'piece', fn: 'openUsurePieceForm', el: '#usure-form-wrap', val: a => _SET_ID(a[0]),
    rouvrir: async v => { await _setAttendre(() => (window._usurePiecesAdmin || []).length || v === 'nouveau'); openUsurePieceForm(_SET_NUM(v)); },
    fermer: () => window.closeUsurePieceForm && closeUsurePieceForm() },
  { onglet: 'maintenance', cle: 'documents', fn: 'openMaintDocsModal', val: a => a[0],
    rouvrir: v => openMaintDocsModal(v) },
  { onglet: 'maintenance', cle: 'rattacher', fn: 'openLibreAttachModal', val: a => a[0],
    rouvrir: async v => { await _setAttendre(() => (window._libresItems || []).length); openLibreAttachModal(v); } },
  { onglet: 'maintenance', cle: 'promouvoir', fn: 'openLibrePromoteModal', val: a => a[0],
    rouvrir: async v => { await _setAttendre(() => (window._libresItems || []).length); openLibrePromoteModal(v); } },
  { onglet: 'maintenance', cle: 'alerte', fn: 'openNewAlertModal', val: () => 'nouvelle',
    rouvrir: v => v === 'nouvelle' ? openNewAlertModal() : openEditAlertModal(Number(v)) },
  { onglet: 'maintenance', cle: 'alerte', fn: 'openEditAlertModal', val: a => a[0],
    rouvrir: v => v === 'nouvelle' ? openNewAlertModal() : openEditAlertModal(Number(v)) },
  { onglet: 'maintenance', cle: 'apercu_alerte', fn: 'previewAlert', val: a => a[0],
    rouvrir: v => previewAlert(Number(v)) },
  { onglet: 'maintenance', cle: 'reglages', fn: 'openAlertSettingsModal', val: () => 'alertes',
    rouvrir: () => openAlertSettingsModal() },
  { onglet: 'bridge', cle: 'appairer', fn: 'openBridgeSuggestModal', el: '#bridge-modal-overlay', val: a => a[0] && a[0].id,
    rouvrir: async v => {
      await _setAttendre(() => _bridgeCache);
      const mp = ((_bridgeCache && _bridgeCache.mp) || []).find(x => String(x.id) === String(v));
      if (mp) openBridgeSuggestModal(mp);
    } },
  { onglet: 'audit', cle: 'couverture', fn: 'openAuditCouverture', el: '#audit-couv-overlay', val: () => '1',
    rouvrir: () => openAuditCouverture(), fermer: () => closeAuditCouverture() },
  { onglet: 'clients', cle: 'client', fn: 'openCliModal', el: '#cli-modal-overlay', val: a => _SET_ID(a[0]),
    rouvrir: async v => { if (v !== 'nouveau') await _setAttendre(() => document.querySelector('#panel-clients tbody tr')); openCliModal(_SET_NUM(v)); },
    fermer: () => closeCliModal() },
  { onglet: 'printers', cle: 'imprimante', fn: 'prEditImprimante', el: '#pr-imp-modal', val: a => a[0] ? String(a[0]) : 'nouvelle',
    rouvrir: async v => { if (v !== 'nouvelle') await _setAttendre(() => document.querySelector('#panel-printers table, #panel-printers .pr-card')); prEditImprimante(v === 'nouvelle' ? null : Number(v)); },
    fermer: () => prCloseModal() },
  { onglet: 'printers', cle: 'modele', fn: 'prEditTemplate', el: '#pr-tpl-modal', val: a => a[0],
    rouvrir: v => _setRouvrirModele(v), fermer: () => prCloseTplModal() },
  // Nouveau modèle : rattaché à une imprimante (« nouveau:<id imprimante> »).
  { onglet: 'printers', cle: 'modele', fn: 'prNewTemplate', el: '#pr-tpl-modal', val: a => 'nouveau' + (a[0] ? ':' + a[0] : ''),
    rouvrir: v => _setRouvrirModele(v), fermer: () => prCloseTplModal() },
  { onglet: 'printers', cle: 'assistant', fn: 'prWizardStart', el: '#pr-wiz-modal', val: () => '1',
    rouvrir: () => prWizardStart(), fermer: () => prWizClose() },
  { onglet: 'encres', cle: 'couleur', fn: 'encOpenForm', el: '#enc-form-wrap', val: a => a[0] ? String(a[0]) : 'nouvelle',
    rouvrir: async v => { await _setAttendre(() => document.querySelector('#panel-encres tbody tr') || v === 'nouvelle'); encOpenForm(v === 'nouvelle' ? null : Number(v)); },
    fermer: () => window.encCloseForm && encCloseForm() },
];

async function _setRouvrirModele(v) {
  await _setAttendre(() => typeof PR !== 'undefined' && PR.usages && PR.usages.length);
  const m = /^nouveau(?::(\d+))?$/.exec(v);
  if (m) return prNewTemplate(m[1] ? Number(m[1]) : undefined);
  await _setAttendre(() => typeof PR !== 'undefined' && (PR.templates || []).length);
  return prEditTemplate(Number(v));
}

// Une fenêtre sans élément nommé est un voile plein écran ajouté à <body> :
// le dock, la messagerie ou un toast, montés au même moment, n'en sont pas.
function _setEstVoile(c) {
  if (!c || c.tagName === 'SCRIPT' || !c.isConnected) return false;
  const st = getComputedStyle(c);
  return st.position === 'fixed' && c.offsetWidth >= window.innerWidth * 0.9 && c.offsetHeight >= window.innerHeight * 0.9;
}

function settingsEnvelopper() {
  SET_FENETRES.forEach(f => {
    const orig = window[f.fn];
    if (typeof orig !== 'function' || orig.__setUrl) return;
    const enveloppe = function () {
      const args = Array.prototype.slice.call(arguments);
      const avant = new Set(Array.from(document.body.children));
      const r = orig.apply(this, args);
      const noter = () => {
        let el = null;
        if (f.el) el = document.querySelector(f.el);
        else el = Array.from(document.body.children).reverse().find(c => !avant.has(c) && _setEstVoile(c)) || null;
        if (!el) return;
        let v = '1';
        try { v = f.val ? f.val(args) : '1'; } catch (e) { v = '1'; }
        _setOuvertures[f.cle] = { val: (v === undefined || v === null) ? '1' : String(v), t: ++_setHorloge, el: el, f: f };
        settingsPlanifierSync();
      };
      // Certaines fenêtres n'apparaissent qu'après un chargement que la
      // fonction ne rend pas (réglages des alertes) : on les attend un peu.
      const trouve = () => f.el ? _setVisible(document.querySelector(f.el))
        : Array.from(document.body.children).some(c => !avant.has(c) && _setEstVoile(c));
      const suivre = () => { if (trouve()) noter(); else _setAttendre(trouve, 4000).then(ok => { if (ok) noter(); }); };
      if (r && typeof r.then === 'function') r.then(suivre, () => {});
      else suivre();
      return r;
    };
    enveloppe.__setUrl = true;
    window[f.fn] = enveloppe;
  });
}

// Fenêtre ouverte au premier plan : la plus récente encore affichée. Une
// fenêtre à élément fixe ouverte sans passer par l'enveloppe compte aussi.
function _setFenetreOuverte() {
  let meilleure = null;
  Object.keys(_setOuvertures).forEach(cle => {
    const o = _setOuvertures[cle];
    if (!_setVisible(o.el)) { delete _setOuvertures[cle]; return; }
    if (!meilleure || o.t > meilleure.t) meilleure = Object.assign({ cle: cle }, o);
  });
  if (meilleure) return meilleure;
  for (const f of SET_FENETRES) {
    if (!f.el) continue;
    const el = document.querySelector(f.el);
    if (_setVisible(el) && _setOnglet() === f.onglet) return { cle: f.cle, val: f.cle === 'couverture' || f.cle === 'assistant' ? '1' : 'nouveau', el: el, f: f, t: 0 };
  }
  return null;
}

// ── Modules autonomes (adresse exposée par le module lui-même) ───────────
function _setModule(nom) { return window[nom] && window[nom].adresse ? window[nom].adresse : null; }

// ── Adresse dérivée de l'état ────────────────────────────────────────────
function settingsParams() {
  const onglet = _setOnglet();
  const p = {};
  let nav = onglet;
  if (onglet !== 'menu') p.onglet = onglet;

  (SET_FILTRES[onglet] || []).forEach(d => {
    const el = document.getElementById(d.id);
    if (!el) return;
    if (d.type === 'case') { if (el.checked) p[d.cle] = '1'; return; }
    const v = el.value || '';
    const def = d.defaut ? d.defaut(el) : '';
    if (v && v !== def) p[d.cle] = v;
  });

  const ds = SET_SOUS[onglet];
  if (ds) {
    const s = _setSousActif(ds);
    if (s && s.v && s.v !== s.premier) {
      p.sous = s.v.slice(ds.prefixe.length);
      nav += '/' + p.sous;
    }
  }
  if (onglet === 'maintenance' && typeof _alertsFilterKind !== 'undefined' && _alertsFilterKind && _alertsFilterKind !== 'all') {
    p.alertes = _alertsFilterKind;
  }
  if (onglet === 'blocs' && typeof _widgetsSection !== 'undefined' && _widgetsSection !== 'blocs') {
    p.section = _widgetsSection;
    nav += '/' + _widgetsSection;
  }

  if (onglet === 'fournisseurs' && typeof fourViewMode !== 'undefined') {
    if (fourFilterFsc) p.ffsc = fourFilterFsc;
    if (fourFilterGroupe) p.fgrp = fourFilterGroupe;
    if (fourFilterCat) p.fcat = fourFilterCat;
    if (fourFilterCert) p.fcert = fourFilterCert;
    if (fourFilterTraca) p.ftra = fourFilterTraca;
    if (fourFilterActif !== '1') p.fact = fourFilterActif || 'all';
    if (fourViewMode !== 'flat') p.fview = fourViewMode;
    if (f2Id) {
      p.f = f2Id; nav += '/fiche';
      if (f2Tab && f2Tab !== 'synthese') p.fonglet = f2Tab;
    } else if (f2Groupe) {
      p.fgroupe = f2Groupe; nav += '/groupe';
    }
  }

  if (onglet === 'clients') {
    const ov = document.getElementById('cli-modal-overlay');
    if (_setVisible(ov)) {
      const b = ov.querySelector('[data-clisub].active');
      const sous = b ? b.dataset.clisub.replace('cli-tab-', '') : 'info';
      if (sous !== 'info') p.client_onglet = sous;
    }
  }

  const mod = { coherence: 'SettingsCoherence', iausage: 'IaUsage', perf: 'SettingsPerf' }[onglet];
  const ad = mod && _setModule(mod);
  if (ad) {
    try {
      const e = ad.etat();
      Object.assign(p, e.params || {});
      if (e.ouvert) nav += '/' + e.ouvert;
    } catch (e) { /* module pas encore prêt */ }
  }

  const fen = _setFenetreOuverte();
  if (fen && (!fen.f || fen.f.onglet === onglet)) {
    p[fen.cle] = fen.val;
    nav += '/' + fen.cle;
  }
  return { params: p, nav: nav };
}

function settingsSyncUrl() {
  if (!_setUrlPret || !window.MySifaUrl) return;
  try { const r = settingsParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) { /* confort */ }
}
function settingsPlanifierSync() {
  if (_setSyncPrevue) return;
  _setSyncPrevue = true;
  // setTimeout plutôt que requestAnimationFrame : ce dernier ne tourne pas
  // dans un onglet en arrière-plan, et l'adresse resterait en retard.
  setTimeout(() => { _setSyncPrevue = false; settingsSyncUrl(); }, 30);
}

// ── Adresse appliquée à l'état ───────────────────────────────────────────
function settingsOngletLu(u) {
  const tabs = typeof VALID_TABS !== 'undefined' ? VALID_TABS : [];
  const h = MySifaUrl.hashHerite();
  const o = u.get('onglet', null, tabs) || (tabs.indexOf(h) !== -1 ? h : null) || 'menu';
  return o;
}

function _setPoserChamp(el, v, type) {
  if (type === 'case') {
    const on = v === '1';
    if (el.checked !== on) { el.checked = on; el.dispatchEvent(new Event('change', { bubbles: true })); }
    return;
  }
  if (el.value === v) return;
  if (el.tagName === 'SELECT' && v && !Array.from(el.options).some(o => o.value === v)) return;
  el.value = v;
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

async function settingsAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const onglet = settingsOngletLu(u);
  if (onglet !== _setOnglet()) setTab(onglet, { silent: true });

  // Filtres : on attend que le champ existe (options chargées par l'API).
  for (const d of (SET_FILTRES[onglet] || [])) {
    const brut = u.get(d.cle, null);
    if (brut === null && !complet) continue;
    await _setAttendre(() => {
      const el = document.getElementById(d.id);
      if (!el) return false;
      if (el.tagName === 'SELECT' && brut) return Array.from(el.options).some(o => o.value === brut);
      return true;
    }, 4000);
    const el = document.getElementById(d.id);
    if (!el) continue;
    let v = brut;
    if (v !== null && d.motif && !d.motif.test(v)) v = null;
    if (v === null) v = d.type === 'case' ? '' : (d.defaut ? d.defaut(el) : '');
    _setPoserChamp(el, v, d.type);
  }

  const ds = SET_SOUS[onglet];
  if (ds) {
    await _setAttendre(() => document.querySelector(ds.sel), 4000);
    const s = _setSousActif(ds);
    const voulu = u.get('sous', null);
    const cible = voulu && /^[a-z0-9_-]+$/.test(voulu) ? ds.prefixe + voulu : (s && s.premier);
    if (s && cible && s.v !== cible) {
      const b = Array.from(document.querySelectorAll(ds.sel)).find(x => x.dataset[ds.attr] === cible);
      if (b) b.click();
    }
  }
  if (onglet === 'maintenance') {
    const k = u.get('alertes', 'all');
    if (typeof _alertsFilterKind !== 'undefined' && /^[a-z_]+$/.test(k) && k !== _alertsFilterKind) {
      await _setAttendre(() => document.querySelector('[data-alerts-filter="' + k + '"]'), 4000);
      const b = document.querySelector('[data-alerts-filter="' + k + '"]');
      if (b) b.click();
    }
  }
  if (onglet === 'blocs' && typeof _widgetsSection !== 'undefined') {
    const s = u.get('section', 'blocs', ['blocs', 'boutons', 'usages']);
    if (s !== _widgetsSection) {
      await _setAttendre(() => document.querySelector('[data-wsec="' + s + '"]'), 4000);
      const b = document.querySelector('[data-wsec="' + s + '"]');
      if (b) b.click();
    }
  }

  if (onglet === 'fournisseurs' && typeof _fourReadURL === 'function' && !complet) {
    // Au démarrage, loadFournisseurs() relit l'adresse une fois la liste
    // chargée : on pose tout de suite les filtres dans l'état, sinon la
    // première écriture de l'adresse les effacerait avant cette relecture.
    _fourReadURL();
  }
  if (onglet === 'fournisseurs' && typeof _fourReadURL === 'function' && complet) {
    await _setAttendre(() => fournisseursAll.length, 6000);
    const fid = Number(u.get('f', 0)) || null;
    const fg = u.get('fgroupe', null);
    const fo = u.get('fonglet', 'synthese');
    {
      f2Id = null; f2Groupe = null;
      _fourReadURL();
      if (fid && fournisseursAll.some(x => x.id === fid)) {
        f2Tab = /^[a-z]+$/.test(fo) ? fo : 'synthese';
        await openFournisseurFiche(fid, true);
      } else if (fg) {
        await openGroupeFiche(fg, true);
      } else {
        f2Id = null; f2Groupe = null; _f2Show('list'); renderFournisseursTable();
      }
    }
  }

  const mod = { coherence: 'SettingsCoherence', iausage: 'IaUsage', perf: 'SettingsPerf' }[onglet];
  const ad = mod && _setModule(mod);
  if (ad && complet) { try { await ad.aller(); } catch (e) { /* module */ } }

  // Fenêtres : fermer ce que l'adresse ne porte plus, ouvrir ce qu'elle demande.
  const ouverte = _setFenetreOuverte();
  const demandee = SET_FENETRES.find(f => f.onglet === onglet && u.get(f.cle, null) !== null);
  const valDemandee = demandee ? u.get(demandee.cle, '') : null;
  if (ouverte && (!demandee || ouverte.cle !== demandee.cle || ouverte.val !== valDemandee)) {
    const f = ouverte.f;
    try {
      if (f && f.fermer) f.fermer();
      else if (ouverte.el) ouverte.el.remove();
    } catch (e) { /* déjà fermée */ }
    delete _setOuvertures[ouverte.cle];
  }
  if (demandee && !(ouverte && ouverte.cle === demandee.cle && ouverte.val === valDemandee)) {
    if (/^[A-Za-z0-9_.:-]{1,80}$/.test(valDemandee)) {
      try {
        await demandee.rouvrir(valDemandee);
        await _setAttendre(() => _setOuvertures[demandee.cle], 4000);
      } catch (e) { /* objet introuvable */ }
    }
  }
  if (onglet === 'clients') {
    const co = u.get('client_onglet', null);
    if (co && /^[a-z]+$/.test(co)) {
      await _setAttendre(() => _setVisible(document.getElementById('cli-modal-overlay')), 4000);
      const b = document.querySelector('#cli-modal-overlay [data-clisub="cli-tab-' + co + '"]');
      if (b) b.click();
    }
  }
}

async function settingsDemarrerUrl() {
  if (!window.MySifaUrl) return;
  settingsEnvelopper();
  try { await settingsAllerUrl(false); } catch (e) { /* adresse illisible */ }
  _setUrlPret = true;
  settingsSyncUrl();
  try {
    new MutationObserver(settingsPlanifierSync).observe(document.body, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style']
    });
  } catch (e) { /* sans observateur, les gestes appellent settingsSyncUrl */ }
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(() => {
    if (!_setUrlPret) return;
    return settingsAllerUrl(true).finally(() => settingsSyncUrl());
  });
}
