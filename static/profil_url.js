/*
 * MySifa — Mon profil (/profil) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé avant le script de app/web/profil_page.py ; ne fait que déclarer
 * des fonctions. init() appelle profilDemarrerUrl() en dernier.
 *
 * Inventaire du 20/10/2026 : `onglet` (prefs, calendrier, notifs ;
 * informations par défaut). Rien d'autre ne décrit ce qu'on regarde : thème,
 * palette, fluidité, couleurs et notifications sont des réglages du compte,
 * enregistrés, pas un état de l'écran.
 * Hors adresse : l'accusé « Profil complété » (s'affiche une fois, se ferme
 * d'un clic). Les liens « /profil?tab=calendrier#cal-<id> » (Calendrier) et
 * « /profil#prefs » (volets du portail) restent lus au démarrage ; l'ancre
 * #cal-<id> ne fait que surligner une ligne, elle n'est pas réécrite.
 */
let _profUrlPrete = false;
let _profDemarre = false;

function profilParams() {
  const p = {};
  if (CURRENT_TAB && CURRENT_TAB !== 'info') p.onglet = CURRENT_TAB;
  return { params: p, nav: CURRENT_TAB || 'info' };
}
function profilSyncUrl() {
  if (!_profUrlPrete || !window.MySifaUrl) return;
  try { const r = profilParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function profilAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const t = u.get('onglet', null, PROFIL_VALID_TABS);
  const voulu = t || (complet ? 'info' : null);
  if (voulu && voulu !== CURRENT_TAB) showTab(voulu, { silent: true });
}

function profilDemarrerUrl() {
  if (_profDemarre || !window.MySifaUrl) return;
  _profDemarre = true;
  // showTab() est la seule porte d'entrée d'un onglet : on écrit après elle.
  const orig = window.showTab;
  if (typeof orig === 'function' && !orig.__adresse) {
    window.showTab = function () { const r = orig.apply(this, arguments); profilSyncUrl(); return r; };
    window.showTab.__adresse = true;
  }
  try { profilAllerUrl(false); } catch (e) {}
  _profUrlPrete = true;
  profilSyncUrl();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(() => { if (_profUrlPrete) profilAllerUrl(true); });
}
