/** Favicon manager — pastilles de notification désactivées.
 *
 * Rôle restreint : sur v1 (staging), patche le href des <link rel="icon">
 * pour pointer vers les variantes "-light" du logo MySifa. Sur v2 : no-op.
 *
 * Historique : ce script gérait aussi une pastille rouge de comptage d'alertes
 * (pattern Gmail) directement sur le favicon en canvas. Retirée en juillet 2026 —
 * les alertes sont visibles ailleurs dans l'UI, la pastille était parasite.
 */
(function () {
  // Détection env : window.__MYSIFA_ENV__ (défini sur le portail) sinon fallback
  // sur le hostname pour les pages qui ne définissent pas la variable.
  var _envVar = (typeof window !== 'undefined' && window.__MYSIFA_ENV__) || null;
  var _host = (typeof window !== 'undefined' && window.location && window.location.hostname) || '';
  var IS_STAGING = (_envVar === 'v1') || /^v1\./i.test(_host);

  function patchIcons() {
    if (!IS_STAGING) return;
    // Sur v1, on force le MyS light comme favicon de TOUTES les pages, y compris
    // celles qui ont normalement un favicon spécifique (stock_favicon,
    // expe_favicon, planning_rh_favicon, etc.). L'onglet Chrome doit toujours
    // être MyS light — impossible de confondre avec la prod.
    var LIGHT_PNG_192 = '/static/mys_icon-light_192.png';
    var LIGHT_PNG_180 = '/static/mys_icon-light_180.png';
    var links = document.querySelectorAll(
      'link[rel="icon"], link[rel="apple-touch-icon"], link[rel="shortcut icon"]'
    );
    links.forEach(function (link) {
      var rel = (link.getAttribute('rel') || '').toLowerCase();
      var href = rel === 'apple-touch-icon' ? LIGHT_PNG_180 : LIGHT_PNG_192;
      link.setAttribute('href', href);
      link.setAttribute('type', 'image/png');
      // Retire sizes/type explicites qui pourraient forcer un autre asset.
      link.removeAttribute('sizes');
    });
    // Si aucun <link rel="icon"> n'était présent, on en ajoute un.
    if (!document.querySelector('link[rel="icon"]')) {
      var l = document.createElement('link');
      l.rel = 'icon';
      l.type = 'image/png';
      l.href = LIGHT_PNG_192;
      document.head.appendChild(l);
    }
  }

  // Shim rétrocompat au cas où d'autres scripts appellent MySifaFaviconBadge.
  window.MySifaFaviconBadge = {
    update: function () {},
    refresh: function () { return Promise.resolve(); },
    start: function () {},
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', patchIcons);
  } else {
    patchIcons();
  }
})();
