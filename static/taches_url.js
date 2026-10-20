/*
 * MySifa — Gestionnaire des tâches (/taches) : adresse de la page
 * (static/mysifa_url.js, .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/taches_page.py ; ne fait que déclarer
 * des fonctions. init() appelle tachesDemarrerUrl() à la place de la lecture
 * du « #vue ».
 *
 * Inventaire du 20/10/2026, par nom d'état (S.…, préférences localStorage) :
 *   vue        liste · archives (Kanban par défaut)
 *   filtres    moi (bascule « Mes tâches », mémorisée), assigne, createur,
 *              priorite, type, module, service, rapide (raccourcis des
 *              compteurs : `statut:<code>`, `retard`, `non_assignees`)
 *   liste      sous=0 (sous-tâches masquées, mémorisé), tri (`champ:sens`,
 *              `ordre:asc` par défaut)
 *   objet      tache (tiroir de détail) + onglet (detail par défaut)
 *   fenêtre    nouvelle=formulaire|<statut> (création, depuis une colonne)
 * Hors adresse : recherche, confirmations, cartes dépliées du Kanban,
 * carte visée au clavier.
 *
 * Ancienne forme « /taches#liste » (volets du portail) : lue au démarrage.
 */
let _tacUrlPrete = false;
let _tacDemarre = false;
let _tacNouvelle = null;      // fenêtre de création ouverte : 'formulaire' ou statut de sa colonne
// La fiche chargée est {tache, commentaires, fichiers…} : l'identifiant est dans `tache`.
const _tacOuverte = () => (S.detail && S.detail.tache && S.detail.tache.id) || null;
const _TAC_FILTRES = ['assigne', 'createur', 'priorite', 'type', 'module', 'service'];
const _TAC_ONGLETS = ['detail', 'commentaires', 'fichiers', 'activite'];

function tachesEnvelopper() {
  const orig = window.openTacheModal;
  if (typeof orig !== 'function' || orig.__adresse) return;
  window.openTacheModal = function (_i, defauts) {
    _tacNouvelle = (defauts && defauts.statut) ? String(defauts.statut) : 'formulaire';
    return orig.apply(this, arguments);
  };
  window.openTacheModal.__adresse = true;
}

function tachesParams() {
  const p = {};
  let nav = S.view;
  if (S.view !== 'kanban') p.vue = S.view;
  const f = S.filtres || {};
  if (f.moi) p.moi = 1;
  _TAC_FILTRES.forEach(k => { if (f[k] && !(k === 'assigne' && f.moi)) p[k] = f[k]; });
  if (f.rapide) p.rapide = f.rapide;
  if (S.view !== 'kanban') {
    if (!S.sousTaches) p.sous = 0;
    if (S.tri && !(S.tri.champ === 'ordre' && S.tri.sens === 'asc')) p.tri = S.tri.champ + ':' + S.tri.sens;
  }
  const ouverte = _tacOuverte();
  if (ouverte) {
    p.tache = ouverte; nav += '/tache:' + ouverte;
    if (S.detailTab && S.detailTab !== 'detail') { p.onglet = S.detailTab; nav += '/' + S.detailTab; }
  }
  const m = document.getElementById('modal-root');
  if (_tacNouvelle && m && m.firstElementChild) { p.nouvelle = _tacNouvelle; nav += '|nouvelle'; }
  else if (m && !m.firstElementChild) _tacNouvelle = null;
  return { params: p, nav };
}

function tachesSyncUrl() {
  if (!_tacUrlPrete || !window.MySifaUrl) return;
  try { const r = tachesParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function tachesUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  const planifier = () => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; tachesSyncUrl(); });
  };
  new MutationObserver(planifier).observe(document.body, { childList: true, subtree: true });
  document.addEventListener('change', planifier, true);
}

// Applique filtres et préférences de l'adresse. Rend la vue voulue (ou null).
function _tacFiltres(u, complet) {
  const ou = (k, def) => (u.a(k) ? u.get(k, def) : (complet ? def : undefined));
  let change = false;
  const f = S.filtres;
  const moi = ou('moi', '0');
  if (moi !== undefined && (moi === '1') !== !!f.moi) {
    f.moi = moi === '1'; change = true;
    try { localStorage.setItem('mysifa_taches_moi', f.moi ? '1' : '0'); } catch (e) {}
    syncMoi();
  }
  _TAC_FILTRES.forEach(k => {
    const v = ou(k, '');
    if (v === undefined || v === (f[k] || '')) return;
    f[k] = v; change = true;
    const el = document.getElementById('f-' + k);
    if (el) { el.value = v; el.classList.toggle('on', !!v); }
  });
  const r = ou('rapide', '');
  if (r !== undefined && r !== (f.rapide || '')) { f.rapide = r; change = true; }
  const s = ou('sous', '1');
  if (s !== undefined && (s !== '0') !== !!S.sousTaches) {
    const b = document.getElementById('btn-sous');
    if (b) b.click(); else S.sousTaches = s !== '0';
  }
  const t = ou('tri', 'ordre:asc');
  if (t !== undefined) {
    const m = /^(\w+):(asc|desc)$/.exec(t) || [null, 'ordre', 'asc'];
    if (S.tri.champ !== m[1] || S.tri.sens !== m[2]) { S.tri = { champ: m[1], sens: m[2] }; change = true; }
  }
  let vue = u.get('vue', null, VALID_VIEWS);
  if (!vue && !u.a('vue')) {
    const h = MySifaUrl.hashHerite();
    if (h === 'mes') { if (!f.moi) { f.moi = true; syncMoi(); change = true; } vue = 'kanban'; }
    else if (VALID_VIEWS.indexOf(h) !== -1) vue = h;
  }
  if (!vue && complet) vue = 'kanban';
  return { vue, change };
}

async function _tacObjet(u, complet) {
  const id = u.get('tache', null);
  if (id && /^\d+$/.test(id)) {
    const onglet = u.get('onglet', 'detail', _TAC_ONGLETS);
    if (String(_tacOuverte()) !== id) {
      S.detailTab = onglet;
      await openDetail(Number(id), { silent: true });
    } else if (S.detailTab !== onglet) { S.detailTab = onglet; renderDrawer(); }
  } else if (complet && S.detail) closeDetail();
  const n = u.get('nouvelle', null);
  const m = document.getElementById('modal-root');
  const ouverte = !!(_tacNouvelle && m && m.firstElementChild);
  if (n && !ouverte && typeof PEUT_ECRIRE !== 'undefined' && PEUT_ECRIRE) {
    openTacheModal(null, n === 'formulaire' ? {} : { statut: n });
  } else if (!n && ouverte && complet) { fermerModal(); _tacNouvelle = null; }
}

// Démarrage : appelé par init() à la place de showView(readView()).
async function tachesDemarrerUrl() {
  if (_tacDemarre || !window.MySifaUrl) { showView(readView(), { silent: true }); return; }
  _tacDemarre = true;
  tachesEnvelopper();
  const u = MySifaUrl.lire();
  let r = { vue: null };
  try { r = _tacFiltres(u, false); } catch (e) {}
  showView(r.vue || readView(), { silent: true });
  try { await _tacObjet(u, false); } catch (e) {}
  _tacUrlPrete = true;
  tachesSyncUrl();
  tachesUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => {
    if (!_tacUrlPrete) return;
    const u = MySifaUrl.lire();
    const r = _tacFiltres(u, true);
    if (r.vue && r.vue !== S.view) showView(r.vue, { silent: true });
    else if (r.change) { syncMoi(); renderStats(); chargerTaches(); }
    await _tacObjet(u, true);
  });
}
