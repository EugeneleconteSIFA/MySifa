/*
 * MySifa — Mon coffre (/coffre) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/coffre_page.py ; ne fait que déclarer des
 * fonctions. init() appelle coffreDemarrerUrl() une fois les notes chargées.
 *
 * Inventaire du 21/10/2026 :
 *   onglet     bulletins, documents (ndf par défaut)
 *   annee      filtre des bulletins (toutes par défaut)
 *   note       fiche d'une note de frais ouverte
 *   modifier   brouillon ouvert en modification
 *   apercu     document ou justificatif affiché (chemin /api/coffre/…)
 * Hors adresse : le formulaire de CRÉATION d'une note (saisie en cours) et
 * les confirmations (soumettre, supprimer).
 * Les anciens liens « /coffre#ndf » et « ?tab=… » restent lus au démarrage.
 */
let _cofUrlPrete = false;
const COFFRE_APERCU_RE = /^\/api\/coffre\/(documents|notes-frais)\/\d+\/(download|justificatif)$/;

function coffreParams() {
  const p = {};
  if (CURRENT_TAB && CURRENT_TAB !== 'ndf') p.onglet = CURRENT_TAB;
  const an = document.getElementById('filter-bul-annee');
  if (CURRENT_TAB === 'bulletins' && an && an.value) p.annee = an.value;
  let nav = CURRENT_TAB || 'ndf';
  // Fiche et modification d'une même note sont un seul endroit : passer de
  // l'une à l'autre remplace, et fermer revient à la liste en reculant.
  if (NDF_EDITION) { p.modifier = NDF_EDITION.id; nav += '/note'; }
  else if (NDF_OUVERTE) { p.note = NDF_OUVERTE.id; nav += '/note'; }
  if (APERCU) { p.apercu = APERCU.url; nav += '/apercu'; }
  return { params: p, nav: nav };
}
function coffreSyncUrl() {
  if (!_cofUrlPrete || !window.MySifaUrl) return;
  try { const r = coffreParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

function coffreOngletLu(u) {
  const h = MySifaUrl.hashHerite();
  return u.get('onglet', null, COFFRE_VALID_TABS)
    || (COFFRE_VALID_TABS.indexOf(h) !== -1 ? h : null)
    || u.get('tab', null, COFFRE_VALID_TABS)
    || 'ndf';
}

async function coffreAllerUrl() {
  const u = MySifaUrl.lire();
  const onglet = coffreOngletLu(u);
  if (onglet !== CURRENT_TAB) showTab(onglet, { silent: true });

  const an = document.getElementById('filter-bul-annee');
  const annee = u.get('annee', '');
  if (an && /^\d{4}$|^$/.test(annee) && an.value !== annee) {
    if (annee && !an.querySelector('option[value="' + annee + '"]')) {
      const o = document.createElement('option'); o.value = annee; o.textContent = annee; an.appendChild(o);
    }
    an.value = annee;
    loadBulletins();
  }

  // Fenêtres : on ferme sans toucher à l'adresse ce qui n'y est plus, puis on
  // ouvre ce qu'elle demande.
  const mod = Number(u.get('modifier', 0)) || 0;
  const vue = Number(u.get('note', 0)) || 0;
  const ap = u.get('apercu', '');
  if (APERCU && APERCU.url !== ap) APERCU.fermer(true);
  if (NDF_EDITION && NDF_EDITION.id !== mod) NDF_EDITION.fermer(true);
  if (NDF_OUVERTE && (NDF_OUVERTE.id !== vue || mod)) NDF_OUVERTE.fermer(true);
  if (mod && !NDF_EDITION && NDF_NOTES.some(n => n.id === mod && n.statut === 'brouillon')) openNdfModal(mod);
  else if (vue && !mod && !NDF_OUVERTE && NDF_NOTES.some(n => n.id === vue)) ouvrirNote(vue);
  if (ap && !APERCU && COFFRE_APERCU_RE.test(ap)) {
    const el = document.querySelector('[data-preview-url="' + ap + '"]');
    previewDocument(ap, (el && el.dataset.previewName) || ap.split('/').slice(-2, -1)[0]);
  }
}

async function coffreDemarrerUrl() {
  if (!window.MySifaUrl) { showTab('ndf', { silent: true }); return; }
  try { await coffreAllerUrl(); } catch (e) {}
  _cofUrlPrete = true;
  coffreSyncUrl();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(() => { if (_cofUrlPrete) return coffreAllerUrl(); });
}
