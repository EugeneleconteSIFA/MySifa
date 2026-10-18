/*
 * MySifa — MyBAT : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé AVANT le script principal de /bat ; ne fait que déclarer des
 * fonctions. S, render(), les open…/close… appartiennent au script principal.
 *
 * Inventaire du 18/10/2026, par nom d'état : filtre de statut, tri (plusieurs
 * colonnes, aussi mémorisé par le navigateur) ; fenêtres : nouveau BAT, ajout
 * d'un PDF, modification, changement de statut, liste des PDF d'un BAT.
 * Hors adresse : la recherche texte, les deux confirmations de suppression.
 *
 * Les fenêtres de MyBAT sont des blocs fixes de la page, affichés en
 * changeant leur `style` : l'observateur suit donc aussi les attributs.
 */
let _batUrlPrete = false;
const _batVisible = id => { const el = document.getElementById(id); return !!(el && el.style.display && el.style.display !== 'none'); };
const _batDefautTri = () => (typeof DEFAULT_SORT !== 'undefined' ? DEFAULT_SORT : []).map(s => s.key + ':' + s.dir).join(',');

function _batModale() {
  if (_batVisible('create-modal')) return { cle: 'nouveau', id: 'bat' };
  if (_batVisible('upload-modal') && S.uploadBatId != null) return { cle: 'ajout_pdf', id: S.uploadBatId };
  if (_batVisible('edit-modal') && S.editBatId != null) return { cle: 'modifier', id: S.editBatId };
  if (_batVisible('statut-modal') && S.statutBatId != null) return { cle: 'statut_bat', id: S.statutBatId };
  if (_batVisible('pdf-picker-modal') && S.pdfPickerBatId != null) return { cle: 'pdfs', id: S.pdfPickerBatId };
  return null;
}

function batParams() {
  const p = {};
  if (S.statut && S.statut !== 'all') p.statut = S.statut;
  const tri = (S.sort || []).map(s => s.key + ':' + s.dir).join(',');
  if (tri && tri !== _batDefautTri()) p.tri = tri;
  let nav = 'liste';
  const mo = _batModale();
  if (mo) { p[mo.cle] = String(mo.id); nav += '/' + mo.cle; }
  return { params: p, nav };
}

function batSyncUrl() {
  if (!_batUrlPrete || !window.MySifaUrl) return;
  try { const r = batParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function batUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; batSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style'] });
}

function _batFermer(mo) {
  if (!mo) return;
  ({ nouveau: closeCreateModal, ajout_pdf: closeUploadModal, modifier: closeEditModal,
     statut_bat: closeStatutModal, pdfs: closePdfPicker })[mo.cle]();
}

async function batAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const st = u.get('statut', complet ? 'all' : null);
  let changer = false;
  if (st && /^[a-z_]{1,20}$/.test(st) && st !== S.statut) { S.statut = st; changer = true; }
  const tri = u.get('tri', null);
  if (tri && /^[a-z_]+:(asc|desc)(,[a-z_]+:(asc|desc))*$/.test(tri)) {
    S.sort = tri.split(',').map(x => { const [key, dir] = x.split(':'); return { key, dir }; });
    changer = true;
  } else if (complet && (S.sort || []).map(s => s.key + ':' + s.dir).join(',') !== _batDefautTri()) {
    S.sort = DEFAULT_SORT.map(s => ({ ...s })); changer = true;
  }
  if (changer) render();
  let voulue = null;
  ['nouveau', 'ajout_pdf', 'modifier', 'statut_bat', 'pdfs'].forEach(k => { const v = u.get(k, null); if (v) voulue = { cle: k, id: v }; });
  const cour = _batModale();
  if (cour && (!voulue || cour.cle !== voulue.cle || String(cour.id) !== String(voulue.id))) _batFermer(cour);
  if (voulue && !_batModale()) {
    const id = /^[0-9]+$/.test(voulue.id) ? Number(voulue.id) : voulue.id;
    const e = (S.entries || []).find(x => String(x.id) === String(voulue.id));
    if (voulue.cle === 'nouveau') openCreateModal();
    else if (!e) return;
    else if (voulue.cle === 'ajout_pdf') openUploadModal(id, e.reference);
    else if (voulue.cle === 'modifier') openEditModal(id);
    else if (voulue.cle === 'statut_bat') openStatutModal(id);
    else if (voulue.cle === 'pdfs') openPdfPicker(id);
  }
}

// Appelé à la fin de loadEntries() (la liste sert à rouvrir les fenêtres).
async function batDemarrerUrl() {
  if (_batUrlPrete || !window.MySifaUrl) return;
  try { await batAllerUrl(false); } catch (e) {}
  _batUrlPrete = true;
  batSyncUrl();
  batUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_batUrlPrete) await batAllerUrl(true); });
}
