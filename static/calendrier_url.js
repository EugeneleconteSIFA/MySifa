/*
 * MySifa — Calendrier (/calendrier) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/calendrier_page.py ; ne fait que déclarer
 * des fonctions. init() appelle calDemarrerUrl() une fois les événements
 * chargés.
 *
 * Inventaire du 20/10/2026, par nom d'état (S.…, préférences localStorage) :
 *   vue        month · week · day · agenda (toujours écrite : son défaut
 *              dépend de l'écran et de la dernière vue choisie)
 *   date       jour de référence (S.anchor), absent = aujourd'hui
 *   cal        calendriers cochés (S.visible), absent = choix par défaut
 *   collegue   agenda d'un collègue (S.collegue)
 *   fenêtres   ev (fiche d'un événement, clé du lien des rappels),
 *              nouveau, modifier, proposer (contre-proposition),
 *              reglages_cal (couleur d'un calendrier), abonnements,
 *              delegations
 * Hors adresse : recherche d'événements, glisser-déposer, sélection des
 * participants dans le formulaire.
 */
let _calUrlPrete = false;
let _calDemarre = false;
let _calReglages = null;      // calendrier dont les réglages sont ouverts
let _calProposition = null;   // événement de la contre-proposition ouverte

function calEnvelopper() {
  const env = (nom, avant) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    window[nom] = function () { try { avant.apply(null, arguments); } catch (e) {} return orig.apply(this, arguments); };
    window[nom].__adresse = true;
  };
  env('openCalSettingsModal', id => { _calReglages = String(id); });
  env('openPersoModal', () => { _calProposition = null; });
  env('openPropositionModal', ev => { _calProposition = ev && ev.id; });
  // La fiche d'un événement : on marque la bulle avec son identifiant.
  const op = window.openPop;
  if (typeof op === 'function' && !op.__adresse) {
    window.openPop = function (ev) {
      const r = op.apply(this, arguments);
      try { if (S.pop && ev && ev.id) S.pop.dataset.urlEv = String(ev.id); } catch (e) {}
      return r;
    };
    window.openPop.__adresse = true;
  }
}

const _calJour = d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
function _calVisiblesDefaut() {
  return accessibleCalDefs().filter(c => calDefautVisible(c)).map(c => String(c.id)).sort();
}
function _calVisibles() {
  return accessibleCalDefs().filter(c => S.visible[c.id]).map(c => String(c.id)).sort();
}

function calParams() {
  const p = { vue: S.view };
  let nav = S.view;
  if (S.anchor && _calJour(S.anchor) !== _calJour(new Date())) p.date = _calJour(S.anchor);
  const vis = _calVisibles(), def = _calVisiblesDefaut();
  if (vis.join(',') !== def.join(',')) p.cal = vis.length ? vis : ['aucun'];
  if (S.collegue) p.collegue = S.collegue;
  const delegRoot = document.getElementById('cal-deleg-modal-root');
  let f = null;
  if (S.createModal) {
    if (S.editingEv && S.editingEv.id) f = ['modifier', S.editingEv.id];
    else if (_calProposition) f = ['proposer', _calProposition];
    else f = ['nouveau', 1];
  } else if (S.colorModal && _calReglages) f = ['reglages_cal', _calReglages];
  else if (S.externModal) f = ['abonnements', 1];
  else if (delegRoot && delegRoot.childElementCount) f = ['delegations', 1];
  else if (S.pop && S.pop.isConnected && S.pop.dataset && S.pop.dataset.urlEv) f = ['ev', S.pop.dataset.urlEv];
  if (f) { p[f[0]] = f[1]; nav += '|' + f[0] + ':' + f[1]; }
  return { params: p, nav };
}

function calSyncUrl() {
  if (!_calUrlPrete || !window.MySifaUrl || !ME) return;
  try { const r = calParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function calUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  const planifier = () => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; calSyncUrl(); });
  };
  new MutationObserver(planifier).observe(document.body, { childList: true, subtree: true });
  // Cases des calendriers et choix du collègue : sans changement de DOM.
  document.addEventListener('change', planifier, true);
}

function _calFermerTout() {
  try { closePop(); } catch (e) {}
  try { closeCreateModal(); } catch (e) {}
  try { closeCalColorModal(); } catch (e) {}
  try { closeExternModal(); } catch (e) {}
  try { closeDelegModal(); } catch (e) {}
}

async function calAllerUrl(complet) {
  const u = MySifaUrl.lire();
  let recharger = false;
  // Vue et jour de référence.
  const vue = u.get('vue', null, VALID_VIEWS);
  if (vue && vue !== S.view) {
    S.view = vue;
    try { localStorage.setItem(LS_VIEW, vue); } catch (e) {}
    applyViewChrome(vue);
    recharger = true;
  }
  const d = u.a('date') ? parseDayStr(u.get('date')) : (complet ? new Date() : null);
  if (d && _calJour(d) !== _calJour(S.anchor)) { S.anchor = d; recharger = true; }
  // Calendriers cochés : préférence mémorisée, on l'enregistre comme un clic.
  if (u.a('cal') || complet) {
    const voulus = u.a('cal') ? u.tous('cal') : _calVisiblesDefaut();
    const avant = _calVisibles().join(',');
    accessibleCalDefs().forEach(c => { S.visible[c.id] = voulus.indexOf(String(c.id)) !== -1; });
    if (_calVisibles().join(',') !== avant) { saveVisible(); renderToggles(); recharger = true; }
  }
  if (u.a('collegue') || complet) {
    const c = u.get('collegue', '');
    if (c !== (S.collegue || '')) {
      S.collegue = c;
      try { localStorage.setItem(LS_COLLEGUE, c); } catch (e) {}
      const sel = document.getElementById('cal-collegue');
      if (sel) { sel.value = c; sel.classList.toggle('actif', !!c); }
      recharger = true;
    }
  }
  // Fenêtre voulue.
  const cles = ['ev', 'nouveau', 'modifier', 'proposer', 'reglages_cal', 'abonnements', 'delegations'];
  let voulue = null;
  cles.forEach(k => { const v = u.get(k, null); if (v && v.length <= 120) voulue = { cle: k, id: v }; });
  const actuelle = (calParams().nav.split('|')[1] || '');
  const cible = voulue ? voulue.cle + ':' + voulue.id : '';
  if (actuelle !== cible && (complet || voulue)) _calFermerTout();
  if (recharger) await fetchEvents();
  if (!voulue || actuelle === cible) return;
  const ev = () => (S.events || []).find(x => String(x.id) === voulue.id);
  if (voulue.cle === 'ev') { S.lienDirect = { id: voulue.id, action: '' }; consommerLienDirect(); }
  else if (voulue.cle === 'nouveau') openCreateModal({});
  else if (voulue.cle === 'modifier') { const e = ev(); if (e) openEditModal(e); }
  else if (voulue.cle === 'proposer') { const e = ev(); if (e) openPropositionModal(e); }
  else if (voulue.cle === 'reglages_cal') openCalSettingsModal(voulue.id);
  else if (voulue.cle === 'abonnements') await openExternModal();
  else if (voulue.cle === 'delegations') await openDelegationsModal();
}

async function calDemarrerUrl() {
  if (_calDemarre || !window.MySifaUrl) return;
  _calDemarre = true;
  calEnvelopper();
  try { await calAllerUrl(false); } catch (e) {}
  _calUrlPrete = true;
  calSyncUrl();
  calUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_calUrlPrete && ME) await calAllerUrl(true); });
}
