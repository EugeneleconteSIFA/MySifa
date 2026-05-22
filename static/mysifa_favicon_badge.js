/** Favicon badge dynamique (pattern Gmail) — GET /api/alerts/count */
(function () {
  function updateFaviconBadge(count) {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#0a0e17';
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(0, 0, 32, 32, 6);
    } else {
      ctx.rect(0, 0, 32, 32);
    }
    ctx.fill();

    ctx.fillStyle = '#f1f5f9';
    ctx.font = 'bold 20px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('M', 16, 17);

    if (count > 0) {
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

    let link = document.querySelector('link[rel="icon"]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = canvas.toDataURL();
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
