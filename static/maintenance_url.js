/*
 * MySifa — Maintenance (/maintenance) : adresse de la page
 * (static/mysifa_url.js, .claude/rules/url-etat.md).
 *
 * Chargé avant les scripts de app/web/maintenance_page.py ; ne fait que
 * déclarer des fonctions. init() appelle maintenanceDemarrerUrl(), qui attend
 * la fin du document : une partie des fonctions (vues opérateur, modèles)
 * vit dans des <script> plus bas.
 *
 * Inventaire du 20/10/2026, par nom d'état (VIEW_META, CAL_STATE, OPS_STATE,
 * OPS_TYPES_STATE, CTRL_STATE, CTRL_TYPES_STATE, _alertsFilterKind, champs
 * filt-*, préférences localStorage) :
 *   vue          maintenance · planning · controles · operations · op-tasks ·
 *                op-planning (toujours écrite : le défaut dépend du rôle)
 *   Suivi        machine, categorie (entretien par défaut), statut,
 *                position.<pièce>=<position> (Bande / Rive… des pièces d'usure,
 *                écrite quand elle n'est pas la première déclarée)
 *   Planning     sous=historique ; calendrier : cal (month, week, day), date
 *   Opérations   sous=liste ; historique : type_op, operateur, machine, du,
 *                au, nature (kind), tri ; liste : machine, tri,
 *                gestion=inhabituelles
 *   Contrôles    sous=liste ; historique : type_ctrl, operateur, machine,
 *                conformite, du, au, points (filtres de checklist), page,
 *                tri, auto=1, anciens=1, affichage=analyse, comparer, alertes ;
 *                liste : machine, tri
 *   Mes tâches   termines=1
 *   fenêtres     voir _MT_OUVREURS (une clé chacune, empilables)
 * Les filtres d'historique écrits sont ceux APPLIQUÉS (au dernier rendu),
 * pas ce qui est en cours de saisie avant « Filtrer ».
 * Hors adresse : recherche dans les codes, colonnes produit (affichage),
 * confirmations de suppression ou d'invalidation, menu flottant du
 * calendrier, glisser-déposer, alertes bloquantes de production.
 */
let _mtPret = false;
let _mtDemarre = false;
let _mtVue = null;
let _mtPile = [];             // [{cle, id, el, avant, depuis}]
let _mtOuvrant = 0;
let _mtOps = null, _mtCtrl = null;   // filtres d'historique appliqués

const _MT_VISIBLE = '.open[id$="-modal"], [id^="op-modal-"].active, #libre-modal.active, .op-modal-overlay, ' +
  '.alert-modal-overlay, .op-plan-detail-ov, .mav-overlay, #libre-docs-overlay, #maint-docs-view-overlay, ' +
  '#maint-form-wrap:not(.hidden)';

// [fonction, clé, valeur tirée des arguments, fermeture]
const _MT_OUVREURS = [
  ['openPlanningDetailsModal', 'creneau_detail', a => a[0] && a[0][0] && a[0][0].id, () => closePlanningDetailsModal()],
  ['openCaseModal', 'creneau', a => (a[0] && a[0].editId) ? a[0].editId : ('nouveau' + (a[0] && a[0].iso ? ':' + a[0].iso : '')), () => closeCaseModal()],
  ['openOpsModal', 'operation', a => a[0] || 'nouvelle', () => closeOpsModal()],
  ['openCatModal', 'categorie_op', a => a[0] || 'nouvelle', () => closeCatModal()],
  ['openCtrlModal', 'controle', () => 'nouveau', () => closeCtrlModal()],
  ['openCtrlCatModal', 'categorie_ctrl', a => a[0] || 'nouvelle', () => closeCtrlCatModal()],
  ['openOpsHistoryDetail', 'saisie', a => a[0], null],
  ['openOpsTypeDetailsModal', 'type_detail', a => a[0], () => closeOpsTypeDetailsModal()],
  ['openAckDetail', 'acquittement', a => a[0], () => closeAckDetail()],
  ['openNewAlertModal', 'alerte', () => 'nouvelle', null],
  ['openEditAlertModal', 'alerte', a => a[0], null],
  ['openAlertSettingsModal', 'reglages_alertes', () => 1, null],
  ['opOpenSaisie', 'saisie_tache', a => a[0], () => opCloseSaisie()],
  ['opOpenNewModal', 'nouvelle_tache', () => 1, () => opCloseNewModal()],
  ['adminOpenRegisterOpModal', 'enregistrer_op', () => 1, () => opCloseNewModal()],
  ['opOpenEditModal', 'modifier_tache', a => a[0], () => opCloseNewModal()],
  ['libreOpenModal', 'intervention_libre', () => 1, () => libreCloseModal()],
  ['libreDocsOpen', 'docs_libre', a => a[0], () => libreDocsClose()],
  ['opOpenSingleOpModal', 'tache_op', a => (a[0] != null && a[1] != null) ? a[0] + ':' + a[1] : null, () => opCloseSingleModal()],
  ['opOpenPlanDetail', 'creneau_op', a => a[0], null],
  ['openTemplatesModal', 'modeles', () => 1, () => closeTemplatesModal()],
  ['openTemplateEditor', 'modele', a => a[0] || 'nouveau', () => closeTemplateEditor()],
  ['viewMaintDocs', 'docs_code', a => a[0], () => closeMaintDocsView()],
  ['openMaintForm', 'code', a => a[0] || 'nouveau', () => closeMaintForm()],
];
const _MT_CLES = [...new Set(_MT_OUVREURS.map(o => o[1]))];

// Pièces d'usure affichées (cartes du Suivi machine).
function _mtPieces() {
  return [...new Set([...document.querySelectorAll('.maint-wearpart[data-wearpart]')].map(el => el.getAttribute('data-wearpart')))];
}

function _mtVisibles() { return [...document.querySelectorAll(_MT_VISIBLE)]; }

function maintenanceEnvelopper() {
  _MT_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    window[nom] = function () {
      if (!_mtOuvrant) {
        let v = null;
        try { v = valeur(arguments); } catch (e) {}
        if (v !== null && v !== undefined && v !== '') {
          _mtPile.push({ cle, id: String(v), el: null, avant: new Set(_mtVisibles()), depuis: Date.now() });
        }
      }
      _mtOuvrant++;
      try { return orig.apply(this, arguments); } finally { _mtOuvrant--; }
    };
    window[nom].__adresse = true;
  });
  const sv = window.switchView;
  if (typeof sv === 'function' && !sv.__adresse) {
    window.switchView = function (name) { if (VIEW_META[name]) _mtVue = name; return sv.apply(this, arguments); };
    window.switchView.__adresse = true;
  }
  // Filtres d'historique : ceux du dernier rendu, c'est-à-dire appliqués.
  const ro = window.renderOps;
  if (typeof ro === 'function' && !ro.__adresse) {
    window.renderOps = function () { try { _mtOps = getOpsFilters(); } catch (e) {} return ro.apply(this, arguments); };
    window.renderOps.__adresse = true;
  }
  const rc = window.renderCtrl;
  if (typeof rc === 'function' && !rc.__adresse) {
    window.renderCtrl = function () { try { _mtCtrl = getCtrlFilters(); } catch (e) {} return rc.apply(this, arguments); };
    window.renderCtrl.__adresse = true;
  }
}

// Fenêtre du dessus : repère l'élément des fenêtres qui viennent de s'ouvrir,
// oublie celles qui sont fermées (ou dont l'ouverture a échoué).
function _mtDessus() {
  _mtPile.forEach(f => {
    if (!f.el) {
      const n = _mtVisibles().filter(x => !f.avant.has(x)).pop();
      if (n) { f.el = n; f.avant = null; } else if (Date.now() - f.depuis > 5000) f.mort = true;
    }
  });
  _mtPile = _mtPile.filter(f => !f.mort && (!f.el || (f.el.isConnected && f.el.matches(_MT_VISIBLE))));
  return _mtPile[_mtPile.length - 1] || null;
}

const _mtActif = sel => { const b = document.querySelector(sel + '.active'); return b ? b.getAttribute(sel.slice(1, -1)) : null; };
const _mtJour = d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');

function _mtVueCourante() {
  if (_mtVue) return _mtVue;
  const b = document.querySelector('.nav-btn[data-view].active');
  if (b) return b.getAttribute('data-view');
  const op = document.querySelector('.op-page.active[id^="view-"]');
  return op ? op.id.slice(5) : null;
}

function maintenanceParams() {
  const v = _mtVueCourante();
  const p = {};
  if (!v) return null;
  p.vue = v;
  let nav = v;
  if (v === 'maintenance') {
    p.machine = getMaintMachine();
    const c = getMaintCatFilter(); if (c !== 'entretien') p.categorie = c;
    const s = getMaintStatusFilter(); if (s !== 'all') p.statut = s;
    _mtPieces().forEach(pc => {
      const pos = getWearPartPos(pc, p.machine);
      const def = _wearPartDef(pc);
      const premiere = def && (def.positions || [])[0];
      if (pos && pos !== 'single' && pos !== premiere) p['position.' + pc] = pos;
    });
  } else if (v === 'planning') {
    const sous = _mtActif('[data-plan-subtab]') || 'calendrier';
    if (sous !== 'calendrier') { p.sous = sous; nav += '/' + sous; }
    else { p.cal = CAL_STATE.view; p.date = _mtJour(_planningPivotDate()); }
  } else if (v === 'operations') {
    const sous = _mtActif('[data-ops-subtab]') || 'historique';
    if (sous !== 'historique') {
      p.sous = sous; nav += '/' + sous;
      p.machine = getOpsCatMachine();
      if (OPS_TYPES_STATE.sortBy !== 'nom' || OPS_TYPES_STATE.sortDir !== 'asc') p.tri = OPS_TYPES_STATE.sortBy + ':' + OPS_TYPES_STATE.sortDir;
      const inh = document.getElementById('maint-view-inhabituelles');
      if (inh && inh.style.display !== 'none') p.gestion = 'inhabituelles';
    } else {
      const f = _mtOps || {};
      if (f.kind && f.kind !== 'all') p.nature = f.kind;
      if (f.type) p.type_op = f.type;
      if (f.operateur) p.operateur = f.operateur;
      if (f.machine) p.machine = f.machine;
      if (f.dateFrom) p.du = f.dateFrom;
      if (f.dateTo) p.au = f.dateTo;
      if (OPS_STATE.sortBy !== 'date_saisie' || OPS_STATE.sortDir !== 'desc') p.tri = OPS_STATE.sortBy + ':' + OPS_STATE.sortDir;
    }
  } else if (v === 'controles') {
    const sous = _mtActif('[data-ctrl-subtab]') || 'historique';
    if (sous !== 'historique') {
      p.sous = sous; nav += '/' + sous;
      p.machine = getCtrlCatMachine();
      if (CTRL_TYPES_STATE.sortBy !== 'nom' || CTRL_TYPES_STATE.sortDir !== 'asc') p.tri = CTRL_TYPES_STATE.sortBy + ':' + CTRL_TYPES_STATE.sortDir;
    } else {
      const f = _mtCtrl || {};
      if (f.type) p.type_ctrl = f.type;
      if (f.operateur) p.operateur = f.operateur;
      if (f.machine) p.machine = f.machine;
      if (f.conformite) p.conformite = f.conformite;
      if (f.dateFrom) p.du = f.dateFrom;
      if (f.dateTo) p.au = f.dateTo;
      const pts = CTRL_STATE.pointFilters || {};
      if (Object.keys(pts).some(k => pts[k] && Object.keys(pts[k]).some(x => pts[k][x] !== '' && pts[k][x] != null))) p.points = JSON.stringify(pts);
      if (CTRL_STATE.page > 0) p.page = CTRL_STATE.page + 1;
      if (CTRL_STATE.sortBy !== 'date_saisie' || CTRL_STATE.sortDir !== 'desc') p.tri = CTRL_STATE.sortBy + ':' + CTRL_STATE.sortDir;
      if (ctrlLoadShowAutoClose()) p.auto = 1;
      if (ctrlLoadShowAnciens()) p.anciens = 1;
      // Affichage Analyse (static/maintenance_analyse.js) : un endroit, il
      // s'empile ; l'axe de comparaison est un réglage, il remplace.
      if (window.MaintAnalyse && MaintAnalyse.mode() === 'analyse') {
        p.affichage = 'analyse'; nav += '/analyse';
        if (MaintAnalyse.comparer() !== 'machine') p.comparer = MaintAnalyse.comparer();
      }
      if (_alertsFilterKind && _alertsFilterKind !== 'all') p.alertes = _alertsFilterKind;
    }
  } else if (v === 'op-tasks') {
    if (_getShowTermine()) p.termines = 1;
  }
  const f = _mtDessus();
  if (f) { p[f.cle] = f.id; nav += '|' + f.cle + ':' + f.id; }
  return { params: p, nav };
}

function maintenanceSyncUrl() {
  if (!_mtPret || !window.MySifaUrl) return;
  try { const r = maintenanceParams(); if (r) MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function maintenanceUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  const planifier = () => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; maintenanceSyncUrl(); });
  };
  // Sous-onglets et modales fixes basculent par classe ou par style.
  new MutationObserver(planifier).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
  document.addEventListener('change', planifier, true);
  document.addEventListener('click', () => setTimeout(planifier, 0), true);
}

function _mtAttendre(cond, max) {
  return new Promise(ok => { let n = 0; const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > (max || 24)) { clearInterval(t); ok(v); } }, 250); });
}
const _mtNum = v => (/^\d+$/.test(String(v)) ? Number(v) : v);
function _mtTri(etat, v, defChamp, defSens) {
  const m = /^(\w+):(asc|desc)$/.exec(v || '') || [null, defChamp, defSens];
  if (etat.sortBy === m[1] && etat.sortDir === m[2]) return false;
  etat.sortBy = m[1]; etat.sortDir = m[2];
  return true;
}
// Pose une valeur dans un champ de filtre. Les listes « Nom de l'opération »,
// « Opérateur »… sont remplies à partir des saisies chargées : tant que la
// valeur n'y figure pas, on régénère les options (rafraichir) et on attend
// l'arrivée des données — posée trop tôt, la valeur se perdait.
async function _mtChamp(id, v, rafraichir) {
  const el = document.getElementById(id);
  if (!el) return false;
  v = v || '';
  if (el.value === v) return false;
  if (el.tagName === 'SELECT' && v) {
    await _mtAttendre(() => {
      if ([...el.options].some(o => o.value === v)) return true;
      try { if (rafraichir) rafraichir(); } catch (e) {}
      return [...el.options].some(o => o.value === v);
    }, 60);
  }
  el.value = v;
  return el.value === v;
}

const _MT_REOUVRIR = {
  creneau_detail: v => planHistOpenDetails(v),
  creneau: async v => {
    if (v.indexOf('nouveau') === 0) { const iso = v.split(':')[1]; return openCaseModal(iso ? { iso } : {}); }
    await _mtAttendre(() => PLANNING_STATE.list.length);
    return openCaseModal({ editId: _mtNum(v) });
  },
  operation: async v => { if (v !== 'nouvelle') await _mtAttendre(() => OPS_STATE.list.length); return openOpsModal(v === 'nouvelle' ? null : _mtNum(v)); },
  categorie_op: v => openCatModal(v === 'nouvelle' ? null : _mtNum(v)),
  controle: () => openCtrlModal(),
  categorie_ctrl: v => openCtrlCatModal(v === 'nouvelle' ? null : _mtNum(v)),
  saisie: async v => { await _mtAttendre(() => (OPS_STATE.list || []).length || (_OPS_HISTORY_DB_CACHE || []).length); return openOpsHistoryDetail(_mtNum(v)); },
  type_detail: async v => { await _mtAttendre(() => OPS_TYPES_STATE.list.length); return openOpsTypeDetailsModal(v); },
  acquittement: async v => { await _mtAttendre(() => (CTRL_STATE.acks || []).length); return openAckDetail(v); },
  alerte: async v => { if (v === 'nouvelle') return openNewAlertModal(); await _mtAttendre(() => _alertsData.length); return openEditAlertModal(_mtNum(v)); },
  reglages_alertes: () => openAlertSettingsModal(),
  saisie_tache: async v => { await _mtAttendre(() => S.me); return opOpenSaisie(_mtNum(v)); },
  nouvelle_tache: () => opOpenNewModal(),
  enregistrer_op: () => adminOpenRegisterOpModal(),
  modifier_tache: async v => { await _mtAttendre(() => S.me); return opOpenEditModal(_mtNum(v)); },
  intervention_libre: () => libreOpenModal(),
  docs_libre: v => libreDocsOpen(v),
  tache_op: async v => { const [e, o] = v.split(':'); await _mtAttendre(() => S.me); return opOpenSingleOpModal(_mtNum(e), _mtNum(o)); },
  creneau_op: v => opOpenPlanDetail(_mtNum(v)),
  modeles: () => openTemplatesModal(),
  modele: v => openTemplateEditor(v === 'nouveau' ? null : _mtNum(v)),
  docs_code: v => viewMaintDocs(v),
  code: v => openMaintForm(v === 'nouveau' ? undefined : v),
};
function _mtFermer(f) {
  const o = _MT_OUVREURS.find(x => x[1] === f.cle && x[3]);
  try { if (o) o[3](); else if (f.el) f.el.remove(); } catch (e) { try { if (f.el) f.el.remove(); } catch (_) {} }
}

async function maintenanceAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const ou = (k, def) => (u.a(k) ? u.get(k, def) : (complet ? def : undefined));
  // Fenêtre voulue : on referme d'abord celles du dessus qui ne le sont plus.
  let voulue = null;
  _MT_CLES.forEach(k => { const v = u.get(k, null); if (v && v.length <= 200) voulue = { cle: k, id: v }; });
  let d = _mtDessus();
  while (d && !(voulue && d.cle === voulue.cle && d.id === voulue.id) && (complet || voulue)) {
    _mtPile.pop(); _mtFermer(d); d = _mtDessus();
  }

  // Vue.
  let vue = u.get('vue', null, Object.keys(VIEW_META));
  if (vue && MAINT_ROLE === 'operator' && vue.indexOf('op-') !== 0) vue = null;
  if (vue && vue !== _mtVueCourante()) switchView(vue);
  const v = _mtVueCourante();

  if (v === 'maintenance') {
    const m = u.get('machine', null); if (m && m !== getMaintMachine()) setMaintMachine(m);
    const c = ou('categorie', 'entretien'); if (c !== undefined && c !== getMaintCatFilter()) setMaintCatFilter(c);
    const s = ou('statut', 'all'); if (s !== undefined && s !== getMaintStatusFilter()) setMaintStatusFilter(s);
    // Positions des pièces d'usure, une fois les cartes dessinées.
    const voulues = {};
    u.brut.forEach((val, k) => { if (k.indexOf('position.') === 0) voulues[k.slice(9)] = val; });
    if (Object.keys(voulues).length || complet) {
      await _mtAttendre(() => _mtPieces().length, 20);
      const machine = getMaintMachine();
      _mtPieces().forEach(pc => {
        const def = _wearPartDef(pc);
        if (!def || def.no_position) return;
        const pos = voulues[pc] || (complet ? (def.positions || [])[0] : null);
        if (pos && pos !== getWearPartPos(pc, machine)) setWearPartPos(pc, pos);
      });
    }
  } else if (v === 'planning') {
    const sous = ou('sous', 'calendrier');
    if (sous !== undefined && sous !== (_mtActif('[data-plan-subtab]') || 'calendrier')) setPlanSubtab(sous);
    if ((_mtActif('[data-plan-subtab]') || 'calendrier') === 'calendrier') {
      const cv = u.get('cal', null, ['month', 'week', 'day']);
      const dt = /^\d{4}-\d{2}-\d{2}$/.test(u.get('date', '')) ? new Date(u.get('date') + 'T12:00:00') : (complet ? new Date() : null);
      if (cv || dt) {
        const vv = cv || CAL_STATE.view;
        const piv = dt || _planningPivotDate();
        const memeJour = _mtJour(piv) === _mtJour(_planningPivotDate());
        if (vv !== CAL_STATE.view || !memeJour) {
          CAL_STATE.year = piv.getFullYear(); CAL_STATE.month = piv.getMonth();
          CAL_STATE.weekStart = _calWeekMondayOf(piv);
          CAL_STATE.dayDate = new Date(piv.getFullYear(), piv.getMonth(), piv.getDate());
          setCalView(vv);
        }
      }
    }
  } else if (v === 'operations') {
    const sous = ou('sous', 'historique');
    if (sous !== undefined && sous !== (_mtActif('[data-ops-subtab]') || 'historique')) setOpsSubtab(sous);
    if ((_mtActif('[data-ops-subtab]') || 'historique') === 'liste') {
      const m = u.get('machine', null); if (m && m !== getOpsCatMachine()) setOpsCatMachine(m);
      if (u.a('tri') || complet) { if (_mtTri(OPS_TYPES_STATE, u.get('tri'), 'nom', 'asc')) renderOpsTypes(); }
      const g = ou('gestion', 'recurrentes'); if (g !== undefined) switchMaintView(g);
    } else {
      let ch = false;
      const champs = [['filt-operations-kind', 'nature', 'all'], ['filt-operations-type', 'type_op', ''], ['filt-operations-operateur', 'operateur', ''],
                      ['filt-operations-machine', 'machine', ''], ['filt-operations-date-from', 'du', ''], ['filt-operations-date-to', 'au', '']];
      for (const [id, k, def] of champs) { const x = ou(k, def); if (x !== undefined && await _mtChamp(id, x, refreshOpsFiltersOptions)) ch = true; }
      if (u.a('tri') || complet) { if (_mtTri(OPS_STATE, u.get('tri'), 'date_saisie', 'desc')) ch = true; }
      if (ch) renderOps();
    }
  } else if (v === 'controles') {
    const sous = ou('sous', 'historique');
    if (sous !== undefined && sous !== (_mtActif('[data-ctrl-subtab]') || 'historique')) setCtrlSubtab(sous);
    if ((_mtActif('[data-ctrl-subtab]') || 'historique') === 'liste') {
      const m = u.get('machine', null); if (m && m !== getCtrlCatMachine()) setCtrlCatMachine(m);
      if (u.a('tri') || complet) { if (_mtTri(CTRL_TYPES_STATE, u.get('tri'), 'nom', 'asc')) renderCtrlTypes(); }
    } else {
      let ch = false;
      const champs = [['filt-controles-type', 'type_ctrl'], ['filt-controles-operateur', 'operateur'], ['filt-controles-machine', 'machine'],
                      ['filt-controles-conformite', 'conformite'], ['filt-controles-date-from', 'du'], ['filt-controles-date-to', 'au']];
      for (const [id, k] of champs) { const x = ou(k, ''); if (x !== undefined && await _mtChamp(id, x, refreshCtrlFiltersOptions)) ch = true; }
      const auto = ou('auto', '0');
      if (auto !== undefined && (auto === '1') !== ctrlLoadShowAutoClose()) { ctrlSaveShowAutoClose(auto === '1'); updateAutoCloseToggleUI(); ch = true; }
      const anciens = ou('anciens', '0');
      if (anciens !== undefined && (anciens === '1') !== ctrlLoadShowAnciens()) { ctrlSaveShowAnciens(anciens === '1'); updateAnciensToggleUI(); ch = true; }
      if (u.a('tri') || complet) { if (_mtTri(CTRL_STATE, u.get('tri'), 'date_saisie', 'desc')) ch = true; }
      const pts = ou('points', '');
      if (pts !== undefined) {
        let o = {}; try { o = pts ? JSON.parse(pts) || {} : {}; } catch (e) { o = {}; }
        if (JSON.stringify(o) !== JSON.stringify(CTRL_STATE.pointFilters || {})) { CTRL_STATE.pointFilters = o; ch = true; }
      }
      const pg = ou('page', '1');
      if (pg !== undefined) { const n = Math.max(0, (parseInt(pg, 10) || 1) - 1); if (n !== CTRL_STATE.page) { CTRL_STATE.page = n; ch = true; } }
      if (window.MaintAnalyse) {
        const aff = ou('affichage', 'historique'), cmp = ou('comparer', 'machine');
        const m2 = aff === undefined ? MaintAnalyse.mode() : (aff === 'analyse' ? 'analyse' : 'historique');
        const c2 = cmp === undefined ? MaintAnalyse.comparer() : cmp;
        if (m2 !== MaintAnalyse.mode() || c2 !== MaintAnalyse.comparer()) { MaintAnalyse.appliquer(m2, c2); ch = true; }
      }
      if (ch) { try { renderPointFilters(); } catch (e) {} renderCtrl(); }
      const al = ou('alertes', 'all');
      if (al !== undefined && al !== _alertsFilterKind) {
        _alertsFilterKind = al;
        document.querySelectorAll('[data-alerts-filter]').forEach(b => b.classList.toggle('active', b.getAttribute('data-alerts-filter') === al));
        renderAlertsList();
      }
    }
  } else if (v === 'op-tasks') {
    const t = ou('termines', '0');
    if (t !== undefined && (t === '1') !== _getShowTermine()) opToggleShowTermine(t === '1');
  }

  if (voulue && !((d = _mtDessus()) && d.cle === voulue.cle && d.id === voulue.id)) {
    try { await _MT_REOUVRIR[voulue.cle](voulue.id); } catch (e) {}
  }
}

// Appelé par init() ; attend la fin du document et l'utilisateur (les vues
// opérateur filtrent par S.me).
async function maintenanceDemarrerUrl(attenteMoi) {
  if (_mtDemarre || !window.MySifaUrl) return;
  _mtDemarre = true;
  if (document.readyState === 'loading') await new Promise(ok => document.addEventListener('DOMContentLoaded', ok, { once: true }));
  try { await attenteMoi; } catch (e) {}
  maintenanceEnvelopper();
  try { _mtOps = getOpsFilters(); _mtCtrl = getCtrlFilters(); } catch (e) {}
  try { await maintenanceAllerUrl(false); } catch (e) {}
  _mtPret = true;
  maintenanceSyncUrl();
  maintenanceUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_mtPret) await maintenanceAllerUrl(true); });
}
