/** Favicon badge dynamique (pattern Gmail) — GET /api/alerts/count
 *
 * Le favicon de base est le vrai logo MyS (favicon-32.png ou sa variante light
 * en staging v1). Le badge de comptage est superposé en canvas.
 */
(function () {
  // Détection env : priorité à window.__MYSIFA_ENV__ (défini sur le portail),
  // fallback sur le hostname pour les pages qui ne définissent pas la variable
  // (stock, planning, calendrier, paie, profil, fabrication, messages, etc.).
  var _envVar = (typeof window !== 'undefined' && window.__MYSIFA_ENV__) || null;
  var _host = (typeof window !== 'undefined' && window.location && window.location.hostname) || '';
  var IS_STAGING = (_envVar === 'v1') || /^v1\./i.test(_host);
  var ENV = IS_STAGING ? 'v1' : 'v2';
  // Base : PNG "MyS" 192px (dark ou light), downscalé net sur un canvas 64×64.
  var BASE_SRC = '/static/mys_icon' + (IS_STAGING ? '-light' : '') + '_192.png';

  // Précharge l'image de base une fois — réutilisée à chaque refresh.
  var baseImg = new Image();
  var baseReady = false;
  baseImg.onload = function () { baseReady = true; refreshAlertsBadge(); };
  baseImg.onerror = function () { baseReady = false; };
  baseImg.src = BASE_SRC;

  function updateFaviconBadge(count) {
    var canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    var ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (baseReady) {
      try { ctx.drawImage(baseImg, 0, 0, 64, 64); }
      catch (e) { drawFallback(ctx); }
    } else {
      drawFallback(ctx);
    }

    if (count > 0) {
      // Contour blanc en v2 / foncé en v1 pour contraster avec le fond du favicon.
      ctx.fillStyle = IS_STAGING ? '#0f172a' : '#ffffff';
      ctx.beginPath();
      ctx.arc(48, 16, 17, 0, Math.PI * 2);
      ctx.fill();
      // Pastille rouge.
      ctx.fillStyle = '#dc2626';
      ctx.beginPath();
      ctx.arc(48, 16, 15, 0, Math.PI * 2);
      ctx.fill();
      // Chiffre.
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 20px system-ui,-apple-system,Segoe UI,sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(count > 9 ? '9+' : String(count), 48, 17);
    }

    var link = document.querySelector('link[rel="icon"]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = canvas.toDataURL();
  }

  function drawFallback(ctx) {
    var bg = IS_STAGING ? '#f1f5f9' : '#0a0e17';
    var fg = IS_STAGING ? '#0f172a' : '#f1f5f9';
    ctx.fillStyle = bg;
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(0, 0, 64, 64, 12);
    } else {
      ctx.rect(0, 0, 64, 64);
    }
    ctx.fill();
    ctx.fillStyle = fg;
    ctx.font = 'bold 40px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('M', 32, 34);
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
