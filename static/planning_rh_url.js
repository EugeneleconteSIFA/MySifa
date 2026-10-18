/*
 * MySifa — Planning RH : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé AVANT le script principal de /planning-rh : il ne fait que déclarer
 * des fonctions ; S, render(), loadData()… appartiennent au script principal.
 *
 * Inventaire du 18/10/2026, par nom d'état (S.*, set({}), localStorage) :
 *   vue (atelier / rh, aussi mémorisée par le navigateur), onglet, semaine
 *   affichée (semaine ISO, pas un décalage : un lien garde son sens), horizon,
 *   mode détail, année des congés ; fenêtres : ajout d'une personne, détail
 *   d'un jour, solde, configuration des équipes d'une machine, détail d'une
 *   maintenance ; formulaire de modification d'un congé existant.
 * Hors adresse : la recherche de personne (texte), le formulaire de nouveau
 * congé (saisie en cours).
 */
let _prhUrlPrete = false;
let _prhDefauts = null;              // horizons par défaut du compte, relevés au démarrage
const _PRH_SEM = /^\d{4}-W\d{2}$/;

function _prhOperateur() { return !S.isEditor && !S.isReadOnlyAdmin && !!S.user; }
function _prhDecalage() { return _prhOperateur() ? S.opOffset : S.baseOffset; }
function _prhCible(t) {               // cellule de grille → texte d'adresse
  return t ? [t.semaine, t.machineCode, t.poste, t.creneau].join('~') : null;
}
function _prhLireCible(v) {
  const [semaine, machineCode, poste, creneau] = String(v).split('~');
  if (!_PRH_SEM.test(semaine || '') || !machineCode || !creneau) return null;
  return { semaine, machineCode, poste, creneau, machineId: (typeof getMachineId === 'function' && getMachineId(machineCode)) || null };
}

function _prhModale() {
  if (S.modal === 'add_person' && S.modalTarget) return { cle: 'ajout_personne', id: _prhCible(S.modalTarget) };
  if (S.modal === 'day_detail' && S.dayDetailTarget) return { cle: 'jour_detail', id: _prhCible(S.dayDetailTarget) };
  if (S.modal === 'solde') return { cle: 'solde', id: (S.soldeForm && S.soldeForm.user_id) || 'nouveau' };
  if (S.modal === 'machine_config' && S.machineConfigSelected) return { cle: 'config_machine', id: S.machineConfigSelected };
  if (S.modal === 'my_maint_detail' && S.myMaintDetail && S.myMaintDetail.id != null) return { cle: 'maintenance', id: S.myMaintDetail.id };
  if (S.editConge && S.editConge.id != null) return { cle: 'modifier_conge', id: S.editConge.id };
  return null;
}

function prhParams() {
  const p = {};
  const defTab = S.view === 'rh' ? 'conges' : 'planning';
  if (S.view === 'rh') p.vue = 'rh';
  if (S.tab && S.tab !== defTab) p.onglet = S.tab;
  let nav = (S.view || 'atelier') + '/' + (S.tab || defTab);
  if (S.tab === 'planning') {
    const dec = _prhDecalage();
    if (dec) p.semaine = addWeeks(weekStr(new Date()), dec);
    const d = _prhDefauts || {};
    if (_prhOperateur()) { if (S.opViewRange !== d.op) p.horizon = String(S.opViewRange); }
    else if (S.viewRange !== d.vue) p.horizon = String(S.viewRange);
    if (S.detailMode) p.detail = 'jours';
  } else if (S.tab === 'conges') {
    if (S.annee && S.annee !== new Date().getFullYear()) p.annee = String(S.annee);
  }
  const mo = _prhModale();
  if (mo && mo.id != null && mo.id !== '') { p[mo.cle] = String(mo.id); nav += '/' + mo.cle; }
  return { params: p, nav };
}

function prhSyncUrl() {
  if (!_prhUrlPrete || !window.MySifaUrl || !S.user) return;
  try { const r = prhParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

function prhUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; prhSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

// Vue, onglet, semaine, horizon, détail, année. Appelée au démarrage après
// loadMe() et le choix de l'horizon par défaut, avant loadData(). Rend vrai
// si les données affichées sont à recharger.
function prhLireUrl(complet) {
  if (!window.MySifaUrl) return false;
  const u = MySifaUrl.lire();
  if (!_prhDefauts) _prhDefauts = { vue: S.viewRange, op: S.opViewRange };
  const avant = JSON.stringify([S.view, S.baseOffset, S.opOffset, S.viewRange, S.opViewRange, S.annee]);
  // Vue : seulement si le compte y a droit (la bascule mémorise le choix).
  const vue = u.get('vue', complet ? 'atelier' : null, ['atelier', 'rh']);
  if (vue && vue !== S.view && ((vue === 'rh' && S.hasRH) || (vue === 'atelier' && S.hasAtelier))) {
    S.view = vue;
    try { localStorage.setItem('mysifa.planning_rh.view', vue); } catch (e) {}
    if (typeof _applyViewPermissions === 'function') _applyViewPermissions();
  }
  const h = MySifaUrl.hashHerite();
  const defTab = S.view === 'rh' ? 'conges' : 'planning';
  let tab = u.get('onglet', null, ['planning', 'conges']) || (['planning', 'conges'].indexOf(h) !== -1 ? h : null);
  if (tab || complet) S.tab = (S.view === 'rh') ? 'conges' : (tab || defTab);
  // Semaine affichée → décalage depuis la semaine courante.
  const sem = u.get('semaine', null);
  let dec = complet ? 0 : null;
  if (sem && _PRH_SEM.test(sem)) dec = Math.round((weekMonday(sem) - weekMonday(weekStr(new Date()))) / (7 * 86400000));
  if (dec !== null) { if (_prhOperateur()) S.opOffset = dec; else S.baseOffset = dec; }
  const hz = u.get('horizon', null);
  if (hz && /^[0-9]{1,2}$/.test(hz)) { if (_prhOperateur()) S.opViewRange = Number(hz); else S.viewRange = Number(hz); }
  else if (complet) { S.viewRange = _prhDefauts.vue; S.opViewRange = _prhDefauts.op; }
  if (u.a('detail') || complet) S.detailMode = u.a('detail');
  const an = u.get('annee', null);
  if (an && /^\d{4}$/.test(an)) S.annee = Number(an); else if (complet) S.annee = new Date().getFullYear();
  return avant !== JSON.stringify([S.view, S.baseOffset, S.opOffset, S.viewRange, S.opViewRange, S.annee]);
}

const _PRH_REOUVRIR = {
  ajout_personne: v => { const t = _prhLireCible(v); if (t) openAddPersonModal(t); },
  jour_detail: v => { const t = _prhLireCible(v); if (t) openDayDetailModal(t); },
  solde: v => openSoldeModal(v === 'nouveau' ? undefined : (isNaN(Number(v)) ? v : Number(v))),
  config_machine: v => { S.machineConfigSelected = isNaN(Number(v)) ? v : Number(v); openMachineConfigModal(); },
  maintenance: v => openMyMaintDetail(v),
  modifier_conge: v => { if ((S.conges || []).some(c => String(c.id) === v)) editConge(isNaN(Number(v)) ? v : Number(v)); },
};

function _prhFermerModale(mo) {
  if (!mo) return;
  if (mo.cle === 'modifier_conge') cancelEditConge();
  else { S.modal = null; render(); }
}

async function prhModaleUrl(u) {
  let voulue = null;
  Object.keys(_PRH_REOUVRIR).forEach(cle => { const v = u.get(cle, null); if (v && v.length <= 120) voulue = { cle, id: v }; });
  const cour = _prhModale();
  if (cour && (!voulue || cour.cle !== voulue.cle || String(cour.id) !== String(voulue.id))) _prhFermerModale(cour);
  if (voulue && !_prhModale()) { try { await _PRH_REOUVRIR[voulue.cle](voulue.id); } catch (e) {} }
}

// Fin du démarrage : la fenêtre demandée, puis l'adresse suit l'écran.
async function prhDemarrerUrl() {
  if (!window.MySifaUrl) return;
  try { await prhModaleUrl(MySifaUrl.lire()); } catch (e) {}
  _prhUrlPrete = true;
  prhSyncUrl();
  prhUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async u => {
    if (!_prhUrlPrete || !S.user) return;
    const vueAvant = S.view, tabAvant = S.tab;
    const recharger = prhLireUrl(true);
    if (recharger || S.view !== vueAvant) {
      render();
      if (S.view !== 'rh') await loadMachines();
      await loadData();
      if (S.tab === 'conges') await loadSoldes();
    } else {
      if (S.tab === 'conges' && tabAvant !== 'conges' && !S.soldes.length) await loadSoldes();
      render();
    }
    await prhModaleUrl(u);
  });
}
