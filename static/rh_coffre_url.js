/*
 * MySifa — Coffre RH (/rh/coffre) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/rh_coffre_page.py ; ne fait que déclarer
 * des fonctions. init() appelle rhCoffreDemarrerUrl() en dernier.
 *
 * Inventaire du 21/10/2026 :
 *   onglet     ndf (bulletins par défaut)
 *   annee      bulletins : année du tableau mensuel (année en cours par défaut)
 *              notes de frais : filtre d'année (toutes par défaut)
 *   mois       bulletins : mois du tableau mensuel (mois en cours par défaut)
 *   statut     notes de frais : soumise par défaut, « tous » pour aucun filtre
 *   note       fiche d'une note de frais ouverte
 *   apercu     bulletin ou justificatif affiché (chemin /api/coffre/…)
 *   reglages   ndf : réglages des notes de frais (static/mysifa_ndf_reglages.js)
 * Hors adresse : l'upload individuel (formulaire de création), l'import ZIP
 * et les confirmations (valider, refuser avec son motif, payer, supprimer,
 * imprimer). Les anciens liens « /rh/coffre#ndf » et « ?tab=… » restent lus
 * au démarrage.
 */
let _rhcUrlPrete = false;
const RHC_APERCU_RE = /^\/api\/coffre\/(documents|notes-frais)\/\d+\/(download|justificatif)$/;
const RHC_STATUTS = ['tous', 'soumise', 'validee', 'payee', 'refusee', 'brouillon'];

function rhCoffreParams() {
  const p = {};
  const v = id => (document.getElementById(id) || {}).value || '';
  let nav = CURRENT_TAB || 'bulletins';
  if (CURRENT_TAB === 'ndf') {
    p.onglet = 'ndf';
    const st = v('ndf-statut');
    if (st !== 'soumise') p.statut = st || 'tous';
    if (v('ndf-annee')) p.annee = v('ndf-annee');
  } else {
    if (v('upl-annee') && Number(v('upl-annee')) !== curYear) p.annee = v('upl-annee');
    if (v('upl-mois') && Number(v('upl-mois')) !== curMonth) p.mois = v('upl-mois');
  }
  if (NDF_OUVERTE) { p.note = NDF_OUVERTE.id; nav += '/note'; }
  if (window.MySifaNdfReglages && MySifaNdfReglages.estOuvert()) { p.reglages = 'ndf'; nav += '/reglages'; }
  if (APERCU) { p.apercu = APERCU.url; nav += '/apercu'; }
  return { params: p, nav: nav };
}
function rhCoffreSyncUrl() {
  if (!_rhcUrlPrete || !window.MySifaUrl) return;
  try { const r = rhCoffreParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

// Pose la valeur d'un select ; rend true si elle a changé.
function rhCoffreSelect(id, val) {
  const el = document.getElementById(id);
  if (!el || el.value === val) return false;
  if (!el.querySelector('option[value="' + val + '"]')) return false;
  el.value = val;
  return true;
}

async function rhCoffreAllerUrl() {
  const u = MySifaUrl.lire();
  const h = MySifaUrl.hashHerite();
  const onglet = u.get('onglet', null, RH_COFFRE_VALID_TABS)
    || (RH_COFFRE_VALID_TABS.indexOf(h) !== -1 ? h : null)
    || u.get('tab', null, RH_COFFRE_VALID_TABS)
    || 'bulletins';
  const annee = u.get('annee', '');
  const anneeOk = /^\d{4}$/.test(annee) ? annee : '';

  if (onglet === 'ndf') {
    const st = u.get('statut', 'soumise', RHC_STATUTS);
    const a = rhCoffreSelect('ndf-statut', st === 'tous' ? '' : st);
    const b = rhCoffreSelect('ndf-annee', anneeOk);
    if (onglet !== CURRENT_TAB) showTab('ndf', { silent: true });
    else if (a || b) await loadNdf();
  } else {
    const mois = u.get('mois', String(curMonth));
    const a = rhCoffreSelect('upl-annee', anneeOk || String(curYear));
    const b = rhCoffreSelect('upl-mois', /^\d{1,2}$/.test(mois) ? String(Number(mois)) : String(curMonth));
    if (onglet !== CURRENT_TAB) showTab('bulletins', { silent: true });
    if (a || b) loadDashboard();
  }

  // Fenêtres : fermer sans écrire ce que l'adresse ne porte plus, ouvrir ce
  // qu'elle demande (fiche, puis réglages, puis aperçu par-dessus).
  const vue = Number(u.get('note', 0)) || 0;
  const reg = u.get('reglages', '') === 'ndf';
  const ap = u.get('apercu', '');
  if (APERCU && APERCU.url !== ap) APERCU.fermer(true);
  if (window.MySifaNdfReglages && MySifaNdfReglages.estOuvert() && !reg) MySifaNdfReglages.fermer(true);
  if (NDF_OUVERTE && NDF_OUVERTE.id !== vue) NDF_OUVERTE.fermer(true);
  if (vue && !NDF_OUVERTE) await ouvrirNoteRh(vue);
  if (reg && window.MySifaNdfReglages && !MySifaNdfReglages.estOuvert()) ouvrirReglagesRh();
  if (ap && !APERCU && RHC_APERCU_RE.test(ap)) {
    const el = document.querySelector('[data-preview-url="' + ap + '"]');
    previewDocument(ap, (el && el.dataset.previewName) || ap.split('/').slice(-2, -1)[0]);
  }
}

async function rhCoffreDemarrerUrl() {
  if (!window.MySifaUrl) { showTab('bulletins', { silent: true }); return; }
  try { await rhCoffreAllerUrl(); } catch (e) {}
  _rhcUrlPrete = true;
  rhCoffreSyncUrl();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(() => { if (_rhcUrlPrete) return rhCoffreAllerUrl(); });
}
