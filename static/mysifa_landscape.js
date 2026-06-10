/**
 * MySifa — Paysage désactivé : affichage vertical forcé sur mobile.
 * On garde l'API publique pour ne pas casser les appels existants,
 * mais enable() est désormais un no-op.
 */
(function () {
  'use strict';

  function enable() {
    // Affichage vertical (portrait) forcé sur toutes les pages, peu importe
    // la rotation physique du téléphone. On retire tout résidu de classes
    // ajoutées par d'anciennes versions.
    try {
      document.body.classList.remove('mysifa-landscape-required');
      document.body.classList.remove('mysifa-portrait');
    } catch (e) {}
  }

  window.MySifaLandscape = { enable: enable };
})();
