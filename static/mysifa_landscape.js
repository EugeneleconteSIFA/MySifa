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
 *  3) Touch handler : dans le body rotaté, un swipe vertical visuel se
 *     mappe naturellement sur l'axe X du body (bloqué par overflow-x:hidden).
 *     On intercepte le geste et on convertit le delta Y visuel en scroll
 *     body-Y manuel — ce qui équivaut, après rotation, à un scroll
 *     vertical visuel pour l'utilisateur.
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

  /* ── Conversion swipe vertical visuel → scroll body-Y ──────────────
     Le body est tourné 90° clockwise. Le browser mappe naturellement
     un swipe visuel HORIZONTAL vers l'axe Y du body (overflow-y:auto)
     — donc swipe horizontal = scroll. Pour autoriser AUSSI un swipe
     visuel VERTICAL à scroller, on intercepte touchmove et on applique
     manuellement le delta visuel-Y sur scrollTop du conteneur
     scrollable (body, .main, ou un parent scrollable).
  */
  var touchState = null;

  function findScrollable(target) {
    var el = target;
    while (el && el !== document.body && el !== document.documentElement) {
      try {
        var cs = window.getComputedStyle(el);
        var oy = cs.overflowY;
        if ((oy === 'auto' || oy === 'scroll') &&
            el.scrollHeight > el.clientHeight + 1) {
          return el;
        }
      } catch (e) {}
      el = el.parentElement;
    }
    // Fallback : body (qui a overflow-y:auto en mode rotaté)
    return document.body;
  }

  function isLandscaped() {
    return document.body.classList.contains('mysifa-force-landscape');
  }

  function onTouchStart(e) {
    if (!isLandscaped()) { touchState = null; return; }
    if (!e.touches || e.touches.length !== 1) { touchState = null; return; }
    var t = e.touches[0];
    var el = findScrollable(e.target);
    touchState = {
      startX: t.clientX,
      startY: t.clientY,
      lastX: t.clientX,
      lastY: t.clientY,
      el: el,
      scrollStart: el.scrollTop,
      decided: false,
      vertical: false
    };
  }

  function onTouchMove(e) {
    if (!touchState) return;
    if (!isLandscaped()) { touchState = null; return; }
    if (!e.touches || e.touches.length !== 1) return;
    var t = e.touches[0];
    var dx = t.clientX - touchState.startX;
    var dy = t.clientY - touchState.startY;
    if (!touchState.decided) {
      if (Math.abs(dx) + Math.abs(dy) < 6) return; // pas encore décidé
      touchState.decided = true;
      touchState.vertical = Math.abs(dy) > Math.abs(dx);
    }
    if (touchState.vertical) {
      // Swipe visuel vertical : on scroll manuellement le conteneur en Y.
      // Convention : swipe vers le haut (dy < 0) → scrollTop augmente
      // (on découvre du contenu plus bas).
      var el = touchState.el;
      var maxScroll = el.scrollHeight - el.clientHeight;
      var next = touchState.scrollStart - dy;
      if (next < 0) next = 0;
      if (next > maxScroll) next = maxScroll;
      el.scrollTop = next;
      try { e.preventDefault(); } catch (err) {}
    }
    // Si swipe horizontal visuel : on laisse le browser gérer
    // (le scroll natif body-Y se déclenche tout seul).
  }

  function onTouchEnd() {
    touchState = null;
  }

  function wireTouchHandlers() {
    if (wireTouchHandlers._done) return;
    wireTouchHandlers._done = true;
    document.addEventListener('touchstart', onTouchStart, { passive: true });
    document.addEventListener('touchmove', onTouchMove, { passive: false });
    document.addEventListener('touchend', onTouchEnd, { passive: true });
    document.addEventListener('touchcancel', onTouchEnd, { passive: true });
  }

  function enable() {
    document.body.classList.add('mysifa-landscape-required');
    syncClasses();
    tryLockLandscape();
    wireTouchHandlers();
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
