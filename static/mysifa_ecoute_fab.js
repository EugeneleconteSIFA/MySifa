/* MySifa — Bouton flottant « Écouter une réunion », sur toutes les pages.
 *
 * Injecté par main.py avec les autres boutons flottants (clé « ecoute » de
 * app/services/boutons_flottants.py, réglable appli par appli). Il ouvre la
 * page d'écoute (/reunions/ecoute) : dans un onglet à part sur ordinateur,
 * pour que l'enregistrement continue pendant qu'on travaille ailleurs ; à la
 * place de la page sur téléphone, où un second onglet passerait en arrière-plan
 * et couperait le micro.
 *
 * Sous 900 px, mysifa_outils_mobile.js range ce bouton dans la feuille des
 * outils, avec son aria-label pour libellé : rien à faire ici.
 */
(function () {
  'use strict';
  if (window.top !== window) return;
  if (location.pathname === '/reunions/ecoute') return;
  if (document.getElementById('reu-ecoute-fab')) return;

  var ICONE = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 10.5a6.5 6.5 0 0 0 13 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8.5" y1="21" x2="15.5" y2="21"/></svg>';

  function avecDock() { return !!(window.MySifaDock && typeof window.MySifaDock.layout === 'function'); }
  function ranger(b) {
    if (avecDock()) { try { window.MySifaDock.layout(); } catch (e) { /* dock indisponible */ } return; }
    // Sans dock : en bas à droite, au-dessus des autres.
    b.style.position = 'fixed';
    b.style.right = '20px';
    b.style.bottom = '84px';
    b.style.zIndex = '8000';
  }

  function creer() {
    if (!document.body || document.getElementById('reu-ecoute-fab')) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.id = 'reu-ecoute-fab';
    b.className = 'mysifa-dock-fab mysifa-dock-extra';
    b.title = 'Écouter une réunion : MySifa l’enregistre et propose le compte-rendu';
    b.setAttribute('aria-label', 'Écouter une réunion');
    b.innerHTML = ICONE;
    b.addEventListener('click', function () {
      var tel = window.matchMedia && window.matchMedia('(max-width: 900px)').matches;
      if (tel) { location.href = '/reunions/ecoute'; return; }
      var w = window.open('/reunions/ecoute', 'mysifa-ecoute');
      if (!w) location.href = '/reunions/ecoute';
    });
    document.body.appendChild(b);
    ranger(b);
    window.addEventListener('resize', function () { ranger(b); });
    // Les autres boutons du dock arrivent souvent après nous.
    setTimeout(function () { ranger(b); }, 800);
    setTimeout(function () { ranger(b); }, 2500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', creer);
  else creer();
})();
