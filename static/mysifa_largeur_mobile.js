/* MySifa — sur téléphone, une page ne déborde jamais en largeur.
 *
 * Les écrans ont été écrits pour un ordinateur : une rangée de boutons, une bande
 * d'onglets ou un tableau suffit à élargir toute la zone de page, qui se met alors
 * à glisser sur le côté. Sous 900 px :
 *
 * - la page elle-même ne défile plus en largeur ;
 * - une rangée de boutons trop longue passe à la ligne ;
 * - un tableau ou une bande d'onglets trop large défile dans son propre bloc.
 *
 * Plutôt qu'une correction par écran, qui en oublierait, la page est surveillée :
 * dès qu'une zone de page déborde, ce qui la déborde est contenu. Le contrôle ne
 * coûte qu'une comparaison de largeurs tant que rien ne déborde.
 *
 * Injecté par main.py dans toutes les pages connectées. Sur ordinateur, ce fichier
 * ne change rien.
 */
(function () {
  'use strict';
  if (window.__mysifaLargeurMobile) return;
  window.__mysifaLargeurMobile = true;

  var ecran = window.matchMedia('(max-width: 900px)');
  var ZONES = 'main,.main,.content,#content,.scroll-area,#root,.app,.rh-content,.prod-main-scroll';
  // Éléments flottants et zones qui défilent déjà en largeur par construction.
  var IGNORES = '.msf-outils-feuille,.staging-bandeau,#mysifa-accueil';

  var st = document.createElement('style');
  st.textContent =
    '@media (max-width: 900px){' +
    'html,body{overflow-x:clip}' +
    '.msf-defile-x{overflow-x:auto!important;max-width:100%;min-width:0;-webkit-overflow-scrolling:touch}' +
    '.msf-tableau-defile{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}' +
    '.msf-rangee-souple{flex-wrap:wrap!important;max-width:100%}' +
    '.msf-rangee-souple>*{max-width:100%;min-width:0}' +
    '}';
  document.head.appendChild(st);

  function defileDeja(el) {
    var o = getComputedStyle(el).overflowX;
    return o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip';
  }

  // Ce qui dépasse : le plus haut élément qui sort de la zone alors que son parent y
  // tient. Ce qui se trouve dans un bloc qui défile et qui tient à l'écran est normal.
  function debordements(zone, limite) {
    var out = [];
    var noeuds = zone.querySelectorAll('*');
    for (var i = 0; i < noeuds.length; i++) {
      var el = noeuds[i];
      var r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || r.right <= limite + 2) continue;
      var parent = el.parentElement;
      if (parent !== zone && parent.getBoundingClientRect().right > limite + 2) continue;
      var cs = getComputedStyle(el);
      if (cs.position === 'fixed' || cs.visibility === 'hidden') continue;
      if (el.closest(IGNORES)) continue;
      var dedans = false;
      for (var p = parent; p && p !== zone; p = p.parentElement) {
        if (defileDeja(p) && p.getBoundingClientRect().right <= limite + 2) { dedans = true; break; }
      }
      if (!dedans) out.push(el);
    }
    return out;
  }

  function contenir(el) {
    var parent = el.parentElement;
    var pcs = getComputedStyle(parent);
    var cs = getComputedStyle(el);
    if (el.tagName === 'TABLE') {
      var enveloppe = document.createElement('div');
      enveloppe.className = 'msf-tableau-defile';
      parent.insertBefore(enveloppe, el);
      enveloppe.appendChild(el);
      return;
    }
    // Des frères dans une rangée : elle passe à la ligne, sauf une bande d'onglets
    // (son élément est lui-même une rangée qui déborde), qui défile.
    var rangee = pcs.display.indexOf('flex') >= 0 && pcs.flexDirection.indexOf('row') === 0;
    if (rangee && parent.children.length > 1 && el.scrollWidth <= el.clientWidth + 2) {
      parent.classList.add('msf-rangee-souple');
      return;
    }
    el.classList.add('msf-defile-x');
    if (rangee) el.style.flexShrink = '1';
    if (cs.display === 'inline-flex') el.style.display = 'flex';
  }

  function controler() {
    if (!ecran.matches || window.__MYSIFA_IMPRESSION__) return;
    var zones = document.querySelectorAll(ZONES);
    for (var i = 0; i < zones.length; i++) {
      var z = zones[i];
      if (z.scrollWidth <= z.clientWidth + 2 || z.clientWidth === 0) continue;
      var limite = z.getBoundingClientRect().left + z.clientWidth;
      debordements(z, limite).forEach(contenir);
      // Rien de ce qui reste (ombre, décalage de quelques pixels) ne fait glisser la page.
      if (getComputedStyle(z).overflowX !== 'visible') z.style.overflowX = 'hidden';
    }
  }

  var prevu = null;
  function planifier() {
    if (prevu) return;
    prevu = setTimeout(function () {
      prevu = null;
      controler();
    }, 250);
  }

  function demarrer() {
    controler();
    new MutationObserver(planifier).observe(document.body, { childList: true, subtree: true });
    window.addEventListener('resize', planifier);
  }

  if (document.body) demarrer();
  else document.addEventListener('DOMContentLoaded', demarrer);
})();
