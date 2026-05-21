/**
 * MySifa — Paysage recommandé sur mobile (planning, prod, db, expé…).
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

  function syncPortraitClass() {
    document.body.classList.toggle('mysifa-portrait', isMobile() && isPortrait());
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  function tryLockLandscape() {
    if (!isMobile()) return;
    var o = screen.orientation;
    if (o && typeof o.lock === 'function') {
      o.lock('landscape').catch(function () {});
    }
  }

  function enable() {
    document.body.classList.add('mysifa-landscape-required');
    syncPortraitClass();
    tryLockLandscape();
    window.addEventListener('orientationchange', syncPortraitClass);
    window.addEventListener('resize', syncPortraitClass);
    if (window.matchMedia('(orientation: portrait)').addEventListener) {
      window.matchMedia('(orientation: portrait)').addEventListener('change', syncPortraitClass);
    }
  }

  window.MySifaLandscape = { enable: enable };
})();
