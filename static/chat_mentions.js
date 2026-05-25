/**
 * MySifa — Utilitaires @mentions (noms avec espaces / accents).
 * Expose window.ChatMentions
 */
(function () {
  'use strict';

  function mentionSlug(nom) {
    return String(nom || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-zA-Z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  function mentionTokenFromBefore(before) {
    const m = String(before || '').match(/@([A-Za-z0-9_]*)$/);
    if (!m) return null;
    return { query: m[1].toLowerCase(), start: before.lastIndexOf('@') };
  }

  function filterCandidates(members, query, myUid) {
    const q = (query || '').toLowerCase();
    const uid = Number(myUid);
    const list = [
      { id: 'all', nom: 'tous', role: 'Mentionner tout le canal' },
      ...(members || []).filter((m) => Number(m.id) !== uid),
    ];
    return list
      .filter((m) => {
        if (m.id === 'all') {
          return !q || 'tous'.startsWith(q) || 'all'.startsWith(q);
        }
        const nom = m.nom || '';
        const slug = mentionSlug(nom).toLowerCase();
        const nl = nom.toLowerCase();
        if (!q) return true;
        if (slug && (slug.startsWith(q) || slug.includes(q))) return true;
        return nl.split(/\s+/).some((w) => w && w.startsWith(q));
      })
      .slice(0, 10);
  }

  function mentionInsertValue(m) {
    if (m.id === 'all') return 'tous';
    return mentionSlug(m.nom) || (m.nom || '').replace(/\s+/g, '_');
  }

  function bodyMentionsUser(body, userNom) {
    const b = String(body || '').toLowerCase();
    if (/@(tous|all)\b/.test(b)) return true;
    const slug = mentionSlug(userNom).toLowerCase();
    if (slug && b.includes('@' + slug)) return true;
    const compact = String(userNom || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, '');
    return !!(compact && b.includes('@' + compact));
  }

  function trimChatBody(text) {
    return String(text || '').replace(/^\s+|\s+$/g, '');
  }

  function insertNewline(inp) {
    if (!inp) return;
    const start = inp.selectionStart != null ? inp.selectionStart : inp.value.length;
    const end = inp.selectionEnd != null ? inp.selectionEnd : start;
    const val = inp.value || '';
    inp.value = val.slice(0, start) + '\n' + val.slice(end);
    const pos = start + 1;
    inp.setSelectionRange(pos, pos);
    inp.dispatchEvent(new Event('input', { bubbles: true }));
  }

  /** Entrée = envoyer ; Maj/Ctrl/Alt + Entrée = nouvelle ligne (insertion explicite). */
  function handleEnterKey(e, inp, onSend, onMentionKeys) {
    if (e.key !== 'Enter' || e.isComposing) return false;
    if (onMentionKeys && onMentionKeys(e, inp)) return true;
    if (e.shiftKey || e.ctrlKey || e.altKey) {
      e.preventDefault();
      insertNewline(inp);
      return true;
    }
    e.preventDefault();
    if (onSend) onSend();
    return true;
  }

  function formatBodyHtml(body, members, escFn) {
    const esc = escFn || ((s) => String(s || ''));
    let safe = esc(String(body || '').replace(/\r\n/g, '\n'));
    safe = safe.replace(/\n/g, '<br>');
    safe = safe.replace(
      /@(tous|all)\b/gi,
      '<span style="color:var(--accent);font-weight:700">@$1</span>'
    );
    (members || []).forEach((m) => {
      const slug = mentionSlug(m.nom);
      if (!slug) return;
      const re = new RegExp('@' + slug.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
      safe = safe.replace(
        re,
        '<span style="color:var(--accent);font-weight:700">@' + esc(m.nom) + '</span>'
      );
    });
    return safe;
  }

  window.ChatMentions = {
    mentionSlug,
    mentionTokenFromBefore,
    filterCandidates,
    mentionInsertValue,
    bodyMentionsUser,
    formatBodyHtml,
    trimChatBody,
    insertNewline,
    handleEnterKey,
  };
})();
