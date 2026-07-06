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
    var links = document.querySelectorAll(
      'link[rel="icon"], link[rel="apple-touch-icon"], link[rel="shortcut icon"]'
    );
    links.forEach(function (link) {
      var href = link.getAttribute('href') || '';
      // Remplace uniquement les icônes MySifa "mys_icon_XXX.png" et "favicon-XX.png"
      // par leur variante -light. Laisse tel quel les favicons spécifiques aux modules
      // (stock_favicon, expe_favicon, planning_rh_favicon).
      var m1 = href.match(/^(.*\/)mys_icon(_\d+\.png)(\?.*)?$/);
      if (m1) {
        link.setAttribute('href', m1[1] + 'mys_icon-light' + m1[2] + (m1[3] || ''));
        return;
      }
      var m2 = href.match(/^(.*\/)favicon(-\d+\.png)(\?.*)?$/);
      if (m2) {
        link.setAttribute('href', m2[1] + 'favicon-light' + m2[2] + (m2[3] || ''));
      }
    });
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
