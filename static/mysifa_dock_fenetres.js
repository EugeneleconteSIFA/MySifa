/* MySifa — masque les boutons flottants quand une fenêtre est ouverte (téléphone).
 *
 * Sur un petit écran, la barre d'outils (messagerie, calculette, post-it,
 * assistant…) est posée sur une couche plus haute que les fenêtres des pages
 * et recouvre leurs boutons du bas. Plutôt que de corriger chaque fenêtre de
 * chaque appli, on observe la page : dès qu'une fenêtre est ouverte, la barre
 * s'efface, et revient à la fermeture.
 *
 * Une « fenêtre », c'est un élément fixe qui couvre l'écran avec un fond
 * semi-transparent (le voile sombre derrière une modale). Les panneaux des
 * outils eux-mêmes ont un fond opaque et ne comptent pas. Sur ordinateur rien
 * ne change : la barre reste dans son coin et sert pendant une saisie.
 *
 * Injecté par main.py avec les boutons flottants (_BOUTONS_JS), donc présent
 * sur toutes les pages qui ont la barre, sans rien ajouter page par page.
 */
(function () {
  'use strict';
  if (window.__mysifaDockFenetres) return;
  window.__mysifaDockFenetres = true;

  var CLASSE = 'mysifa-dock-sous-fenetre';
  var petitEcran = window.matchMedia ? window.matchMedia('(max-width: 900px), (pointer: coarse)') : null;

  var st = document.createElement('style');
  st.textContent =
    'body.' + CLASSE + ' .mysifa-dock-fab,' +
    'body.' + CLASSE + ' .calc-fab,' +
    'body.' + CLASSE + ' #cw-bubble,' +
    'body.' + CLASSE + ' #cw-bar,' +
    'body.' + CLASSE + ' #ai-chat-btn,' +
    'body.' + CLASSE + ' #postit-dock-root,' +
    'body.' + CLASSE + ' #mysifa-dock-toggle,' +
    'body.' + CLASSE + ' #mysifa-dock-barre{opacity:0!important;pointer-events:none!important;visibility:hidden!important}';
  document.head.appendChild(st);

  function alpha(couleur) {
    var m = /rgba?\(([^)]+)\)/.exec(couleur || '');
    if (!m) return 0;
    var p = m[1].split(',');
    return p.length > 3 ? parseFloat(p[3]) : 1;
  }

  function estVoile(el) {
    if (!el || el.nodeType !== 1) return false;
    var cs = getComputedStyle(el);
    if (cs.position !== 'fixed' || cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    if (r.width < innerWidth * 0.9 || r.height < innerHeight * 0.9) return false;
    var a = alpha(cs.backgroundColor);
    return a >= 0.15 && a < 0.98;
  }

  function fenetreOuverte() {
    // Les fenêtres sont ajoutées au <body> ou dans un conteneur dédié (#mroot,
    // #modal-root) : on regarde ces deux niveaux, pas toute la page.
    var candidats = Array.prototype.slice.call(document.body.children);
    ['mroot', 'modal-root'].forEach(function (id) {
      var r = document.getElementById(id);
      if (r) candidats = candidats.concat(Array.prototype.slice.call(r.children));
    });
    return candidats.some(estVoile);
  }

  var prevu = false;
  function maj() {
    prevu = false;
    var actif = !!(petitEcran && petitEcran.matches) && fenetreOuverte();
    document.body.classList.toggle(CLASSE, actif);
  }
  function planifier() {
    if (prevu) return;
    prevu = true;
    requestAnimationFrame(maj);
  }

  function demarrer() {
    new MutationObserver(planifier).observe(document.body, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'hidden']
    });
    if (petitEcran) {
      if (petitEcran.addEventListener) petitEcran.addEventListener('change', planifier);
      else if (petitEcran.addListener) petitEcran.addListener(planifier);
    }
    planifier();
  }
  if (document.body) demarrer();
  else document.addEventListener('DOMContentLoaded', demarrer);
})();
