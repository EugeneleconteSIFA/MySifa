/** Favicon badge dynamique (pattern Gmail) — GET /api/alerts/count
 *
 * Le favicon de base est le vrai logo MyS (favicon-32.png ou sa variante light
 * en staging v1). Le badge de comptage est superposé en canvas.
 */
(function () {
  var ENV = (typeof window !== 'undefined' && window.__MYSIFA_ENV__) || 'v2';
  var IS_STAGING = (ENV === 'v1');
  // Suffix des icônes MySifa : dark par défaut, -light en staging v1.
  var BASE_SRC = '/static/favicon' + (IS_STAGING ? '-light' : '') + '-32.png';

  // Précharge l'image de base une fois — réutilisée à chaque refresh.
  var baseImg = new Image();
  var baseReady = false;
  baseImg.onload = function () { baseReady = true; refreshAlertsBadge(); };
  baseImg.onerror = function () { baseReady = false; };
  baseImg.src = BASE_SRC;

  function updateFaviconBadge(count) {
    var canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    var ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (baseReady) {
      // Dessine le vrai logo MyS.
      try { ctx.drawImage(baseImg, 0, 0, 32, 32); }
      catch (e) { drawFallback(ctx); }
    } else {
      drawFallback(ctx);
    }

    if (count > 0) {
      // Pastille rouge — visible sur fond clair (v1) comme sur fond foncé (v2).
      ctx.fillStyle = '#f87171';
      ctx.beginPath();
      ctx.arc(24, 8, 7, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(count > 9 ? '9+' : String(count), 24, 8);
    }

    // Remplace le <link rel="icon"> — tous les navigateurs modernes acceptent data URL.
    var link = document.querySelector('link[rel="icon"]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = canvas.toDataURL();
  }

  // Fallback si l'image PNG n'a pas pu charger : "M" simple, couleurs env-dépendantes.
  function drawFallback(ctx) {
    var bg = IS_STAGING ? '#f1f5f9' : '#0a0e17';
    var fg = IS_STAGING ? '#0f172a' : '#f1f5f9';
    ctx.fillStyle = bg;
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(0, 0, 32, 32, 6);
    } else {
      ctx.rect(0, 0, 32, 32);
    }
    ctx.fill();
    ctx.fillStyle = fg;
    ctx.font = 'bold 20px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('M', 16, 17);
  }

  async function refreshAlertsBadge() {
    try {
      const r = await fetch('/api/alerts/count', { credentials: 'include' });
      if (r.status === 401) return;
      if (!r.ok) return;
      const data = await r.json();
      if (data && typeof data.total === 'number') {
        if (window.S && typeof window.S === 'object') {
          window.S.alertsCount = data.total;
        }
        updateFaviconBadge(data.total);
      }
    } catch (e) {}
  }

  function shouldRefreshAfterFetch(url, init) {
    const method = String((init && init.method) || 'GET').toUpperCase();
    if (method === 'GET') return false;
    const u = String(url || '');
    if (u.includes('/api/alerts/count')) return false;
    return (
      /\/api\/messages/.test(u) ||
      /\/api\/expe\/departs\/.+\/valider/.test(u) ||
      /\/api\/dossiers\//.test(u) ||
      /\/api\/planning\/.+\/statut/.test(u)
    );
  }

  if (!window.__mysifaFetchPatched) {
    window.__mysifaFetchPatched = true;
    const nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      const p = nativeFetch(input, init);
      try {
        const url = typeof input === 'string' ? input : input && input.url;
        if (shouldRefreshAfterFetch(url, init)) {
          p.then(function (res) {
            if (res && res.ok) refreshAlertsBadge();
          }).catch(function () {});
        }
      } catch (e) {}
      return p;
    };
  }

  let intervalId = null;
  function startPolling() {
    refreshAlertsBadge();
    if (intervalId) return;
    intervalId = setInterval(refreshAlertsBadge, 60000);
  }

  window.MySifaFaviconBadge = {
    update: updateFaviconBadge,
    refresh: refreshAlertsBadge,
    start: startPolling,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startPolling);
  } else {
    startPolling();
  }
})();
