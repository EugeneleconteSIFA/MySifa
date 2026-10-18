/*
 * MySifa — MyCompta : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Servie par le gabarit commun app/web/html.py (comme MyExpé) : chargé sur
 * toutes ses applis, inactif hors de /compta. Ne fait que déclarer des
 * fonctions ; S, set(), render() et les chargeurs appartiennent au script
 * principal.
 *
 * Inventaire du 18/10/2026, par nom d'état (S.compta*, S.paie*, set({})) :
 *   onglet (factor, acheteurs, comptes, banques, cession, paie) ; mode de
 *   l'import Factor (fichier / collage) ; fenêtres de modification d'un
 *   acheteur, d'un compte, d'une banque ; Paie : période, employé
 *   sélectionné, historique des périodes.
 * Hors adresse : le résultat d'un import (il dépend d'un fichier), le texte
 * collé, la recherche d'employé, les variables de paie en cours de saisie.
 * Le « RH outil » embarqué dans le même code a déménagé vers /rh
 * (/compta#rhoutil y redirige déjà) : il ne relève pas de MyCompta.
 */
let _comptaUrlPrete = false;
let _comptaDemarre = false;
const _COMPTA_ONGLETS = ['factor', 'acheteurs', 'comptes', 'banques', 'cession', 'paie'];
const _comptaSurPage = () => location.pathname === '/compta';
const _comptaPeriodeCourante = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); };

function _comptaModale() {
  if (S.comptaEditAcheteurId != null) return { cle: 'acheteur', id: S.comptaEditAcheteurId };
  if (S.comptaEditCompteId != null) return { cle: 'compte', id: S.comptaEditCompteId };
  if (S.comptaEditBanqueId != null) return { cle: 'banque', id: S.comptaEditBanqueId };
  if ((S.comptaTab || 'factor') === 'paie' && S.paieShowHist) return { cle: 'historique', id: 'periodes' };
  return null;
}

function comptaParams() {
  const p = {};
  const tab = S.comptaTab || 'factor';
  if (tab !== 'factor') p.onglet = tab;
  let nav = tab;
  if (tab === 'factor' && S.comptaFactorMode === 'paste') p.mode = 'collage';
  if (tab === 'paie') {
    const per = S.paieAnnee + '-' + String(S.paieMois).padStart(2, '0');
    if (per !== _comptaPeriodeCourante()) p.periode = per;
    if (S.paieCurrentEmpId != null) { p.employe = String(S.paieCurrentEmpId); nav += '/employe:' + S.paieCurrentEmpId; }
  }
  const mo = _comptaModale();
  if (mo) { p[mo.cle] = String(mo.id); nav += '/' + mo.cle; }
  return { params: p, nav };
}

function comptaSyncUrl() {
  if (!_comptaUrlPrete || !_comptaSurPage() || !window.MySifaUrl || !S.user || S.app !== 'compta') return;
  try { const r = comptaParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

function comptaUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; comptaSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

function _comptaAttendre(cond) {
  return new Promise(ok => {
    let n = 0;
    const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250);
  });
}

// Onglet, mode, période, employé : posés avant le rendu ; puis chargement de
// l'onglet et fenêtre demandée.
async function comptaAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const tab = u.get('onglet', 'factor', _COMPTA_ONGLETS);
  const avantTab = S.comptaTab || 'factor';
  S.comptaTab = tab;
  if (u.a('mode') || complet) S.comptaFactorMode = u.get('mode', null) === 'collage' ? 'paste' : 'file';
  let periodeChangee = false;
  if (tab === 'paie') {
    const per = u.get('periode', complet ? _comptaPeriodeCourante() : null);
    if (per && /^\d{4}-\d{2}$/.test(per)) {
      const [y, m] = per.split('-').map(Number);
      if (m >= 1 && m <= 12 && (y !== S.paieAnnee || m !== S.paieMois)) { S.paieAnnee = y; S.paieMois = m; S.paiePendingVar = {}; periodeChangee = true; }
    }
    const emp = u.get('employe', null);
    if (emp && /^[0-9]+$/.test(emp)) S.paieCurrentEmpId = Number(emp);
    else if (complet) S.paieCurrentEmpId = null;
  }
  render();
  // Chargements de l'onglet (les mêmes que les boutons de la barre latérale).
  if (tab !== avantTab || !complet) {
    if (tab === 'acheteurs') loadComptaAcheteurs();
    else if (tab === 'comptes') loadComptaComptes();
    else if (tab === 'banques') loadComptaBanques();
  }
  if (tab === 'paie' && (tab !== avantTab || periodeChangee || !complet)) {
    if (!S.paieEmpLoaded) paieLoadEmployes();
    paieLoadVars().then(() => render());
  }
  // Fenêtre
  let voulue = null;
  ['acheteur', 'compte', 'banque', 'historique'].forEach(k => { const v = u.get(k, null); if (v) voulue = { cle: k, id: v }; });
  const cour = _comptaModale();
  if (cour && (!voulue || cour.cle !== voulue.cle || String(cour.id) !== String(voulue.id))) {
    if (cour.cle === 'acheteur') closeComptaAcheteurModal();
    else if (cour.cle === 'compte') closeComptaCompteModal();
    else if (cour.cle === 'banque') closeComptaBanqueModal();
    else { S.paieShowHist = false; render(); }
  }
  if (voulue && !_comptaModale()) {
    const id = /^[0-9]+$/.test(voulue.id) ? Number(voulue.id) : voulue.id;
    if (voulue.cle === 'acheteur') { await _comptaAttendre(() => (S.comptaAcheteurs || []).length); set({ comptaEditAcheteurId: id }); }
    else if (voulue.cle === 'compte') { await _comptaAttendre(() => (S.comptaComptes || []).length); set({ comptaEditCompteId: id }); }
    else if (voulue.cle === 'banque') { await _comptaAttendre(() => (S.comptaBanques || []).length); set({ comptaEditBanqueId: id }); }
    else if (voulue.cle === 'historique' && tab === 'paie') paieShowHistory();
  }
}

// Appelé par renderCompta() au premier rendu.
function comptaDemarrerUrl() {
  if (_comptaDemarre || !_comptaSurPage() || !window.MySifaUrl) return;
  _comptaDemarre = true;
  setTimeout(async () => {
    try { await comptaAllerUrl(false); } catch (e) {}
    _comptaUrlPrete = true;
    comptaSyncUrl();
    comptaUrlObserver();
  }, 0);
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => {
    if (!_comptaUrlPrete || !_comptaSurPage() || !S.user) return;
    await comptaAllerUrl(true);
  });
}
