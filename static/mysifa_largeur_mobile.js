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
 * dès qu'une zone de page déborde, ce qui la déborde est contenu avant que l'image
 * suivante ne soit peinte, pour ne pas voir l'écran large puis se resserrer. Le
 * contrôle ne coûte qu'une comparaison de largeurs tant que rien ne déborde.
 *
 * Injecté par main.py en tête du <head> de toutes les pages, pour observer la page
 * dès sa construction. Sur ordinateur, ce fichier ne change rien.
 */
(function () {
  'use strict';
  if (window.__mysifaLargeurMobile) return;
  window.__mysifaLargeurMobile = true;

  var ecran = window.matchMedia('(max-width: 900px)');
  // Une fenêtre de saisie est une zone comme une autre : elle ne doit pas glisser non plus.
  var ZONES = 'main,.main,.content,#content,.scroll-area,#root,.app,.rh-content,.prod-main-scroll,' +
    '[class*="modal"],[class*="overlay"],[class*="-ov"],[class*="-back"],[id$="-modal"]';
  // Éléments flottants et zones qui défilent déjà en largeur par construction.
  var IGNORES = '.msf-outils-feuille,.staging-bandeau,#mysifa-accueil';

  var st = document.createElement('style');
  st.textContent =
    '@media (max-width: 900px){' +
    'html,body{overflow-x:clip}' +
    // Sur iPhone, un champ de date impose sa largeur (le calendrier natif) et pousse tout
    // son formulaire hors de l'écran. appearance:none et min-width:0 lèvent cette largeur.
    'input,select,textarea{max-width:100%;box-sizing:border-box}' +
    'input[type=date],input[type=time],input[type=datetime-local],input[type=month],input[type=week]' +
    '{-webkit-appearance:none;appearance:none;min-width:0!important;max-width:100%;text-align:left}' +
    'input::-webkit-date-and-time-value{text-align:left;min-height:1.2em}' +
    ':has(>input[type=date]),:has(>input[type=time]),:has(>input[type=datetime-local]){min-width:0}' +
    // Réunions : le width:100% des champs de la fenêtre touche aussi les cases à cocher,
    // et les rôles ne s'alignaient plus. Deux colonnes égales, case à gauche du libellé.
    '.reu-roles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 12px}' +
    '.reu-roles label{display:flex;align-items:center;gap:8px;min-width:0;font-size:14px;line-height:1.2}' +
    '.reu-roles input[type=checkbox]{flex:0 0 20px;width:20px!important;height:20px;min-height:0;margin:0;padding:0}' +
    // Une fenêtre ouverte passe devant les barres et le bandeau. Dans la page, elle reste
    // sous eux quel que soit son z-index : la barre du bas masquait ses boutons.
    'body.mysifa-dock-sous-fenetre .mobile-topbar{z-index:1!important}' +
    'body.mysifa-dock-sous-fenetre #mobile-navbar-root{display:none}' +
    'body.mysifa-dock-sous-fenetre .staging-bandeau{z-index:0!important}' +
    // Formulaire plus haut que l'écran : centré, son début et ses boutons étaient hors
    // d'atteinte. La fenêtre défile, et le formulaire repart du haut.
    '.msf-fenetre-defile{overflow-y:auto!important;align-items:flex-start!important;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}' +
    '.msf-defile-x{overflow-x:auto!important;max-width:100%;min-width:0;-webkit-overflow-scrolling:touch}' +
    '.msf-tableau-defile{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}' +
    '.msf-rangee-souple{flex-wrap:wrap!important;max-width:100%}' +
    '.msf-rangee-souple>*{max-width:100%;min-width:0}' +
    // Rangées connues : à la bonne largeur dès la première image.
    '.maint-chip-group,.recep-subtabs,.sifa-tabs{flex-wrap:wrap;max-width:100%;min-width:0}' +
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

  var examines = new WeakMap();

  function fenetreTropHaute(z) {
    if (z.clientHeight === 0 || z.scrollHeight <= z.clientHeight + 2) return;
    if (z.classList.contains('msf-fenetre-defile')) return;
    var cs = getComputedStyle(z);
    if (cs.position === 'fixed' && cs.overflowY === 'visible') z.classList.add('msf-fenetre-defile');
  }

  function controler() {
    if (!ecran.matches || window.__MYSIFA_IMPRESSION__) return;
    var zones = document.querySelectorAll(ZONES);
    for (var i = 0; i < zones.length; i++) {
      var z = zones[i];
      fenetreTropHaute(z);
      var large = z.scrollWidth;
      if (large <= z.clientWidth + 2 || z.clientWidth === 0) continue;
      // Reste déjà examiné (un texte sans espace…) : pas de nouveau parcours de la
      // page à chaque image tant que sa largeur ne bouge pas.
      if (examines.get(z) === large) continue;
      var limite = z.getBoundingClientRect().left + z.clientWidth;
      debordements(z, limite).forEach(contenir);
      examines.set(z, z.scrollWidth);
      // Rien de ce qui reste (ombre, décalage de quelques pixels) ne fait glisser la page.
      if (getComputedStyle(z).overflowX !== 'visible') z.style.overflowX = 'hidden';
    }
  }

  var prevu = null;
  var dernier = 0;
  function planifier() {
    // Page en construction : l'écran de chargement la cache, et mesurer à chaque image
    // la ralentirait. Le contrôle se fait à la fin de la construction.
    if (prevu || document.readyState === 'loading') return;
    var attente = Math.max(0, 120 - (Date.now() - dernier));
    var lancer = function () {
      // Juste avant que le navigateur peigne ce qui vient de changer.
      prevu = requestAnimationFrame(function () {
        prevu = null;
        dernier = Date.now();
        controler();
      });
    };
    if (attente) { prevu = -1; setTimeout(function () { prevu = null; lancer(); }, attente); }
    else lancer();
  }

  new MutationObserver(planifier).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener('DOMContentLoaded', planifier);
  window.addEventListener('resize', planifier);
})();
