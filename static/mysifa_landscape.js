/**
 * MySifa — Paysage forcé sur mobile (façon YouTube).
 *
 * Stratégie :
 *  1) On tente un screen.orientation.lock('landscape') — fonctionne sur Chrome
 *     Android en plein écran, échec silencieux sur iOS / autres.
 *  2) En complément, dès que l'orientation physique est "portrait" sur un
 *     écran mobile, on tourne tout l'affichage de 90° via CSS (voir
 *     mysifa_landscape.css). L'utilisateur voit toujours du paysage, peu
 *     importe qu'il tienne son téléphone en portrait ou en paysage.
 *
 * Aucun message "Tournez l'appareil" n'est affiché : la rotation est faite
 * pour l'utilisateur.
 */
(function () {
  'use strict';

  var BP = '(max-width: 900px)';

  function isMobile() {
    return window.matchMedia(BP).matches;
  }

  function isPortrait() {
    return window.matchMedia('(orientation: portrait)').matches;
  }

  function syncClasses() {
    var force = isMobile() && isPortrait();
    document.body.classList.toggle('mysifa-force-landscape', force);
    // On garde aussi 'mysifa-portrait' pour compatibilité (anciens hooks JS).
    document.body.classList.toggle('mysifa-portrait', force);
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      try { window.MySifaDock.layout(); } catch (e) {}
    }
  }

  function tryLockLandscape() {
    if (!isMobile()) return;
    var o = window.screen && window.screen.orientation;
    if (o && typeof o.lock === 'function') {
      try { o.lock('landscape').catch(function () {}); } catch (e) {}
    }
  }

  function enable() {
    document.body.classList.add('mysifa-landscape-required');
    syncClasses();
    tryLockLandscape();
    if (!enable._wired) {
      enable._wired = true;
      window.addEventListener('orientationchange', syncClasses);
      window.addEventListener('resize', syncClasses);
      try {
        window.matchMedia('(orientation: portrait)')
          .addEventListener('change', syncClasses);
      } catch (e) {}
    }
  }

  function disable() {
    document.body.classList.remove('mysifa-landscape-required');
    document.body.classList.remove('mysifa-portrait');
    document.body.classList.remove('mysifa-force-landscape');
  }

  window.MySifaLandscape = { enable: enable, disable: disable };
})();
