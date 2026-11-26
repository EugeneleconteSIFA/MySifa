/* MySifa — la page derrière une fenêtre ouverte ne défile pas.
   ------------------------------------------------------------
   Retour du 26/11/2026 : dans le planning comme dans MyProd, la molette sur
   une fenêtre (dossier, OF, choix des commandes…) faisait défiler la page
   en dessous. Les pages défilent souvent dans un bloc à elles (`.main`) que
   l'overflow du document n'arrête pas, et chaque fenêtre a son propre voile :
   corriger fenêtre par fenêtre en oublierait toujours une.

   Règle, pour toutes les pages (injecté par main.py) : un défilement dont la
   cible est dans un voile plein écran (élément fixe qui couvre la hauteur et
   l'essentiel de la largeur) ne sort jamais de ce voile. Un bloc défilant de la fenêtre
   défile normalement ; en butée, ou hors de tout bloc défilant, rien ne
   bouge. Hors de toute fenêtre, rien ne change. */
(function () {
  'use strict';
  if (window.__mysifaFondFige) return;
  window.__mysifaFondFige = true;

  function defilable(el) {
    var st = getComputedStyle(el).overflowY;
    return (st === 'auto' || st === 'scroll') && el.scrollHeight > el.clientHeight + 1;
  }
  function voile(el) {
    if (getComputedStyle(el).position !== 'fixed') return false;
    var r = el.getBoundingClientRect();
    // Un voile laisse parfois la barre latérale visible (guides : 78 % de la
    // largeur) ; un panneau latéral (messagerie, assistant) reste sous 50 %.
    return r.width >= window.innerWidth * 0.6 && r.height >= window.innerHeight * 0.85;
  }
  // true : le défilement doit être retenu (il sortirait d'une fenêtre).
  function retenir(cible, versLeBas) {
    var el = cible && cible.nodeType === 1 ? cible : (cible && cible.parentElement);
    var bloc = null;
    while (el && el !== document.body && el !== document.documentElement) {
      if (!bloc && defilable(el)) {
        var peut = versLeBas ? el.scrollTop + el.clientHeight < el.scrollHeight - 1 : el.scrollTop > 0;
        if (peut) return false;
        bloc = el;
      }
      if (voile(el)) return true;
      el = el.parentElement;
    }
    return false;
  }

  document.addEventListener('wheel', function (e) {
    if (e.ctrlKey || !e.deltaY) return;   // zoom au pavé, défilement horizontal
    if (retenir(e.target, e.deltaY > 0)) e.preventDefault();
  }, { passive: false, capture: true });

  var y0 = null;
  document.addEventListener('touchstart', function (e) {
    y0 = e.touches && e.touches.length === 1 ? e.touches[0].clientY : null;
  }, { passive: true, capture: true });
  document.addEventListener('touchmove', function (e) {
    if (y0 == null || !e.touches || e.touches.length !== 1) return;
    var dy = y0 - e.touches[0].clientY;
    if (!dy) return;
    if (retenir(e.target, dy > 0)) e.preventDefault();
  }, { passive: false, capture: true });
})();
