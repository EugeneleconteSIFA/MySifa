/** Met à jour les badges [data-mysifa-chat-badge] via GET /api/chat/unread */
(function () {
  async function fetchUnread() {
    try {
      const r = await fetch('/api/chat/unread', { credentials: 'include' });
      if (r.status === 401) return 0;
      if (!r.ok) return 0;
      const j = await r.json();
      return Number(j.unread) || 0;
    } catch (e) {
      return 0;
    }
  }

  function applyBadge(n) {
    document.querySelectorAll('[data-mysifa-chat-badge]').forEach(function (el) {
      if (n > 0) {
        el.textContent = n > 99 ? '99+' : String(n);
        el.classList.remove('hidden');
      } else {
        el.textContent = '';
        el.classList.add('hidden');
      }
    });
  }

  async function refresh() {
    applyBadge(await fetchUnread());
  }

  window.MySifaChatBadge = { refresh: refresh };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', refresh);
  } else {
    refresh();
  }
})();
