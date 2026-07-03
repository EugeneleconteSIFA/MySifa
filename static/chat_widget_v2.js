/**
 * MySifa — Extensions messagerie v2 pour le widget chat (GIF, @mentions, épinglage).
 * Chargé après chat_widget.js ; nécessite window._CW.
 */
(function () {
  'use strict';

  const ADMIN = new Set(['superadmin', 'direction', 'administration']);
  const NOTIF_KEY = 'mysifa_notif_asked_v1';

  let channelMembers = [];
  let mentionQuery = null;
  let mentionStart = 0;
  let mentionFocusIdx = -1;
  let v2Patched = false;
  let cwReplyTo = null; // { id, user_nom, body }

  function waitCW() {
    return new Promise((resolve) => {
      const t = setInterval(() => {
        if (window._CW && window._CW.renderMsg) {
          clearInterval(t);
          resolve(window._CW);
        }
      }, 50);
      setTimeout(() => {
        clearInterval(t);
        resolve(window._CW || null);
      }, 8000);
    });
  }

  function injectV2Styles() {
    if (document.getElementById('cw-v2-styles')) return;
    const s = document.createElement('style');
    s.id = 'cw-v2-styles';
    s.textContent = `
#cw-action-expand{width:38px;height:38px;border-radius:10px;background:transparent;border:1px solid var(--border);
  cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;color:var(--text2);font-size:22px;font-weight:300;line-height:1;font-family:inherit}
#cw-action-expand.open,#cw-action-expand:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
#cw-action-btns{display:none;align-items:center;gap:6px;flex-shrink:0}
#cw-action-btns.show{display:flex}
#cw-gif-btn{font-size:11px;font-weight:800;padding:0 8px;color:var(--accent);border:1px solid var(--accent);
  border-radius:10px;height:38px;background:transparent;cursor:pointer;font-family:inherit}
#cw-gif-btn:hover{background:var(--accent-bg)}
#cw-input-wrap{flex:1;min-width:0;position:relative}
#cw-mention-dd{position:absolute;bottom:calc(100% + 4px);left:0;right:0;background:var(--card);border:1px solid var(--border);
  border-radius:10px;max-height:200px;overflow-y:auto;z-index:200;box-shadow:0 8px 32px rgba(0,0,0,.35);display:none}
.cw-mention-item{display:flex;align-items:center;gap:8px;padding:9px 12px;cursor:pointer;font-size:13px;
  border-bottom:1px solid var(--border);color:var(--text)}
.cw-mention-item:last-child{border-bottom:none}
.cw-mention-item:hover,.cw-mention-item.focused{background:var(--accent-bg);color:var(--accent)}
.cw-msg-wrap.cw-pinned .cw-msg-mine,.cw-msg-wrap.cw-pinned .cw-msg-theirs{border-top:2px solid var(--warn)}
.cw-msg-pin,.cw-msg-edit,.cw-msg-del{position:absolute;top:2px;background:var(--card);border:1px solid var(--border);
  border-radius:6px;width:22px;height:22px;cursor:pointer;display:none;align-items:center;justify-content:center;
  color:var(--muted);font-size:11px;padding:0}
.cw-msg-wrap:hover .cw-msg-pin,.cw-msg-wrap:hover .cw-msg-edit,.cw-msg-wrap:hover .cw-msg-del{display:flex}
.cw-msg-pin.pinned-active{color:var(--warn);border-color:var(--warn)}
.cw-gif-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:4px;max-height:min(70vh,480px);overflow-y:auto;margin-top:10px;padding:2px}
.cw-gif-item{cursor:pointer;padding:0;margin:0;border:none;background:transparent;display:block;line-height:0}
.cw-gif-item img{width:100%;height:auto;display:block;object-fit:contain;vertical-align:top;border-radius:3px}
.cw-gif-item:hover img{opacity:.88;outline:2px solid var(--accent);outline-offset:1px}
#cw-notif-modal{position:fixed;inset:0;z-index:20000;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center;padding:20px}
.cw-notif-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px 24px;width:min(380px,100%);text-align:center}
.cw-modal-overlay{position:fixed;inset:0;z-index:8020;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px}
.cw-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;width:min(500px,100%);max-height:85vh;overflow-y:auto}
.cw-modal h3{margin:0 0 14px;font-size:15px;font-weight:700}
/* Styles du bouton ⋮ et du menu déroulant définis dans chat_widget.js
   (anciennes règles ici retirées car elles écrasaient le nouveau design). */
/* ── Reply context ──────────────────────────────────────── */
.cw-msg-reply-ctx{padding:5px 9px;margin-bottom:5px;border-left:3px solid var(--accent);
  background:var(--accent-bg);border-radius:6px;opacity:.7;cursor:pointer;font-size:11px}
.cw-reply-name{font-weight:700;color:var(--text);margin-bottom:1px}
.cw-reply-body{color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
/* ── Forwarded ──────────────────────────────────────────── */
.cw-msg-fwd-tag{font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:4px;display:flex;align-items:center;gap:4px}
.cw-msg-fwd{border-left:3px solid var(--muted)!important;padding-left:9px!important}
/* ── Deleted ────────────────────────────────────────────── */
.cw-msg-deleted{font-style:italic;color:var(--muted)!important;
  background:transparent!important;border-style:dashed!important}
/* ── Edited label ───────────────────────────────────────── */
.cw-msg-edited-lbl{font-size:10px;color:var(--muted);font-style:italic;margin-left:5px}
/* ── Date separator ─────────────────────────────────────── */
.cw-date-sep{display:flex;align-items:center;gap:10px;margin:4px 0 2px;flex-shrink:0}
.cw-date-sep::before,.cw-date-sep::after{content:'';flex:1;height:1px;background:var(--border)}
.cw-date-sep-lbl{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.5px;
  text-transform:uppercase;white-space:nowrap;padding:0 4px}
/* ── Reply bar (above input) ────────────────────────────── */
#cw-reply-bar{padding:6px 12px;background:var(--card);border-top:1px solid var(--border);
  display:none;align-items:center;gap:8px;flex-shrink:0}
#cw-reply-bar.cw-show{display:flex}
.cw-reply-preview{flex:1;min-width:0;padding:5px 9px;border-left:3px solid var(--accent);
  background:var(--accent-bg);border-radius:6px;font-size:12px}
.cw-reply-preview-name{font-weight:700;color:var(--text)}
.cw-reply-preview-body{color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cw-reply-cancel{width:24px;height:24px;border-radius:6px;border:1px solid var(--border);
  background:transparent;color:var(--muted);cursor:pointer;font-size:16px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0}
.cw-reply-cancel:hover{border-color:var(--danger);color:var(--danger)}
/* ── Edit area ──────────────────────────────────────────── */
.cw-edit-area{width:100%;background:var(--bg);border:1px solid var(--accent);border-radius:8px;
  padding:7px 10px;color:var(--text);font-size:13px;font-family:inherit;
  resize:none;outline:none;min-height:36px;max-height:100px;line-height:1.4}
.cw-edit-acts{display:flex;gap:6px;margin-top:6px;justify-content:flex-end}
.cw-edit-acts button{padding:4px 12px;border-radius:7px;font-size:12px;font-weight:700;
  cursor:pointer;font-family:inherit;border:1px solid var(--border);background:transparent;color:var(--text2)}
.cw-edit-acts .primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
`;
    document.head.appendChild(s);
  }

  function patchInputRow(CW) {
    const row = document.getElementById('cw-input-row');
    if (!row || document.getElementById('cw-action-expand')) return;
    // Inject reply bar before input row
    if (!document.getElementById('cw-reply-bar')) {
      const rb = document.createElement('div');
      rb.id = 'cw-reply-bar';
      rb.innerHTML = '<div class="cw-reply-preview"><div class="cw-reply-preview-name" id="cw-reply-pname"></div><div class="cw-reply-preview-body" id="cw-reply-pbody"></div></div><button type="button" class="cw-reply-cancel" aria-label="Annuler">×</button>';
      row.parentNode.insertBefore(rb, row);
      rb.querySelector('.cw-reply-cancel').addEventListener('click', cwCancelReply);
    }
    row.innerHTML =
      '<input type="file" id="cw-file-input" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip">' +
      '<button type="button" id="cw-action-expand" aria-label="Plus d\'options">+</button>' +
      '<div id="cw-action-btns">' +
      '<button type="button" id="cw-attach" aria-label="Pièce jointe" title="Pièce jointe">' +
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg></button>' +
      '<button type="button" id="cw-poll-btn" aria-label="Sondage" title="Sondage">' +
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 8 8 4"/><line x1="12" y1="6" x2="21" y2="6"/><rect x="3" y="10" width="6" height="4" rx="1"/><line x1="12" y1="12" x2="21" y2="12"/><rect x="3" y="16" width="6" height="4" rx="1"/><line x1="12" y1="18" x2="21" y2="18"/></svg></button>' +
      '<button type="button" id="cw-gif-btn" aria-label="GIF">GIF</button></div>' +
      '<div id="cw-input-wrap"><div id="cw-mention-dd"></div><textarea id="cw-input" rows="1" placeholder="Message…"></textarea></div>' +
      '<button type="button" id="cw-send" aria-label="Envoyer">' +
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button>';

    document.getElementById('cw-attach')?.addEventListener('click', () => document.getElementById('cw-file-input')?.click());
    const fileInp = document.getElementById('cw-file-input');
    if (fileInp) {
      fileInp.addEventListener('change', () => {
        const f = fileInp.files && fileInp.files[0];
        CW.pendingFile = f || null;
        const row = document.getElementById('cw-pending-row');
        if (row) {
          if (!f) {
            row.classList.remove('cw-show');
            row.innerHTML = '';
          } else {
            row.classList.add('cw-show');
            row.innerHTML =
              '<div class="cw-pending-chip"><span>' +
              CW.escCW(f.name) +
              '</span><button type="button" aria-label="Retirer">×</button></div>';
            row.querySelector('button')?.addEventListener('click', () => {
              CW.pendingFile = null;
              row.classList.remove('cw-show');
              row.innerHTML = '';
            });
          }
        }
        fileInp.value = '';
      });
    }
    document.getElementById('cw-action-expand')?.addEventListener('click', toggleActions);
    document.getElementById('cw-gif-btn')?.addEventListener('click', () => {
      closeActions();
      openGifPicker(CW);
    });
    document.getElementById('cw-poll-btn')?.addEventListener('click', () => {
      closeActions();
      if (typeof CW.openPollModal === 'function') CW.openPollModal();
      else if (window._CW && typeof window._CW.openPollModal === 'function') window._CW.openPollModal();
    });
    document.getElementById('cw-send')?.addEventListener('click', () => CW.sendMessage());
    const inp = document.getElementById('cw-input');
    if (inp) {
      inp.addEventListener('keydown', (e) => {
        const CM = window.ChatMentions;
        if (CM && CM.handleEnterKey) {
          CM.handleEnterKey(e, inp, () => CW.sendMessage(), (ev, el) => handleMentionKeys(ev, el));
          return;
        }
        if (handleMentionKeys(e, inp)) return;
        if (e.key === 'Enter' && (e.shiftKey || e.ctrlKey || e.altKey)) {
          e.preventDefault();
          const start = inp.selectionStart;
          const end = inp.selectionEnd;
          inp.value =
            inp.value.slice(0, start) + '\n' + inp.value.slice(end);
          inp.setSelectionRange(start + 1, start + 1);
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          return;
        }
        if (e.key === 'Enter') {
          e.preventDefault();
          CW.sendMessage();
        }
      });
      inp.addEventListener('input', function () {
        if (typeof resizeCwInput === 'function') resizeCwInput(this);
        const val = this.value;
        const cur = this.selectionStart;
        const before = val.substring(0, cur);
        const CM = window.ChatMentions;
        const tok = CM ? CM.mentionTokenFromBefore(before) : null;
        if (tok) {
          mentionQuery = tok.query;
          mentionStart = tok.start;
          renderMentionDd(CW);
        } else {
          closeMentionDd();
        }
      });
      inp.addEventListener('focus', closeActions);
    }
  }

  function toggleActions() {
    const btns = document.getElementById('cw-action-btns');
    const btn = document.getElementById('cw-action-expand');
    if (!btns || !btn) return;
    const open = btns.classList.contains('show');
    if (open) closeActions();
    else {
      btns.classList.add('show');
      btn.classList.add('open');
    }
  }
  function closeActions() {
    document.getElementById('cw-action-btns')?.classList.remove('show');
    document.getElementById('cw-action-expand')?.classList.remove('open');
  }

  function closeMentionDd() {
    mentionQuery = null;
    const dd = document.getElementById('cw-mention-dd');
    if (dd) {
      dd.style.display = 'none';
      dd.innerHTML = '';
    }
  }

  async function renderMentionDd(CW) {
    const dd = document.getElementById('cw-mention-dd');
    if (!dd) return;
    const CM = window.ChatMentions;
    if (!CM) return;
    if (!channelMembers.length && CW.activeId) {
      try {
        channelMembers =
          (await CW.api('/api/chat/channels/' + CW.activeId + '/members')) || [];
      } catch (e) {
        channelMembers = [];
      }
    }
    const candidates = CM.filterCandidates(channelMembers, mentionQuery, CW.uid);
    if (!candidates.length) {
      closeMentionDd();
      return;
    }
    mentionFocusIdx = -1;
    dd.style.display = 'block';
    dd.innerHTML = candidates
      .map((m, i) => {
        const insertVal = CM.mentionInsertValue(m);
        const label = m.id === 'all' ? '@tous' : '@' + (m.nom || insertVal);
        return (
          '<div class="cw-mention-item" data-insert="' +
          CW.escCW(insertVal) +
          '" data-idx="' +
          i +
          '"><span style="font-weight:600">' +
          CW.escCW(label) +
          '</span><span style="font-size:11px;color:var(--muted);margin-left:6px">' +
          CW.escCW(m.role || '') +
          '</span></div>'
        );
      })
      .join('');
    dd.querySelectorAll('.cw-mention-item').forEach((el) => {
      el.addEventListener('mousedown', (e) => {
        e.preventDefault();
        insertMention(el.dataset.insert || '');
      });
    });
  }

  function insertMention(nom) {
    const inp = document.getElementById('cw-input');
    if (!inp) return;
    const val = inp.value;
    const before = val.substring(0, mentionStart);
    const after = val.substring(inp.selectionStart);
    inp.value = before + '@' + nom + ' ' + after;
    const pos = before.length + nom.length + 2;
    inp.focus();
    inp.setSelectionRange(pos, pos);
    closeMentionDd();
  }

  function handleMentionKeys(e, inp) {
    const dd = document.getElementById('cw-mention-dd');
    if (!dd || dd.style.display === 'none') return false;
    const items = dd.querySelectorAll('.cw-mention-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      mentionFocusIdx = Math.min(mentionFocusIdx + 1, items.length - 1);
      items.forEach((el, i) => el.classList.toggle('focused', i === mentionFocusIdx));
      return true;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      mentionFocusIdx = Math.max(mentionFocusIdx - 1, 0);
      items.forEach((el, i) => el.classList.toggle('focused', i === mentionFocusIdx));
      return true;
    }
    if (e.key === 'Enter' && mentionFocusIdx >= 0 && !e.shiftKey && !e.ctrlKey) {
      e.preventDefault();
      const val = items[mentionFocusIdx]?.dataset.insert;
      if (val) insertMention(val);
      return true;
    }
    if (e.key === 'Escape') {
      closeMentionDd();
      return true;
    }
    return false;
  }

  function ensureNotifModal() {
    if (document.getElementById('cw-notif-modal')) return;
    const m = document.createElement('div');
    m.id = 'cw-notif-modal';
    m.innerHTML =
      '<div class="cw-notif-card"><h2 style="font-size:15px;margin:0 0 10px">Notifications</h2>' +
      '<p style="font-size:13px;color:var(--text2);line-height:1.6;margin:0 0 16px">Recevoir des alertes pour les messages et mentions, même si l\'onglet est en arrière-plan ?</p>' +
      '<div style="display:flex;gap:8px;justify-content:center">' +
      '<button type="button" id="cw-notif-no" style="padding:9px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit">Non merci</button>' +
      '<button type="button" id="cw-notif-yes" style="padding:9px 14px;border-radius:8px;border:none;background:var(--accent);color:var(--bg);font-weight:700;cursor:pointer;font-family:inherit">Activer</button>' +
      '</div></div>';
    document.body.appendChild(m);
    document.getElementById('cw-notif-no').onclick = () => dismissNotif(false);
    document.getElementById('cw-notif-yes').onclick = () => dismissNotif(true);
  }

  async function dismissNotif(enable) {
    const CW = window._CW;
    if (!CW) return;
    document.getElementById('cw-notif-modal').style.display = 'none';
    localStorage.setItem(NOTIF_KEY, '1');
    if (enable && typeof Notification !== 'undefined') {
      try {
        const perm = await Notification.requestPermission();
        await CW.api('/api/chat/notif-prefs', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ browser_notif: perm === 'granted' }),
        });
      } catch (e) {}
    } else {
      try {
        await CW.api('/api/chat/notif-prefs', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ browser_notif: false }),
        });
      } catch (e) {}
    }
  }

  function checkNotifPerm() {
    if (localStorage.getItem(NOTIF_KEY)) return;
    if (typeof Notification !== 'undefined' && Notification.permission !== 'default') return;
    ensureNotifModal();
    setTimeout(() => {
      const m = document.getElementById('cw-notif-modal');
      if (m) m.style.display = 'flex';
    }, 3500);
  }

  function openGifPicker(CW) {
    const overlay = document.createElement('div');
    overlay.className = 'cw-modal-overlay';
    overlay.onclick = (e) => {
      if (e.target === overlay) overlay.remove();
    };
    overlay.innerHTML =
      '<div class="cw-modal" role="dialog"><h3>GIF</h3>' +
      '<input type="search" id="cw-gif-search" placeholder="Rechercher un GIF…" autocomplete="off" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;margin-bottom:8px">' +
      '<div id="cw-gif-grid" class="cw-gif-grid"><p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:16px 0">Chargement…</p></div></div>';
    document.body.appendChild(overlay);
    const search = document.getElementById('cw-gif-search');
    let deb = null;
    const load = (q) => loadGifs(CW, q);
    load('');
    if (search) {
      search.focus();
      search.oninput = function () {
        clearTimeout(deb);
        deb = setTimeout(() => load(this.value.trim()), 400);
      };
    }
  }

  async function loadGifs(CW, q) {
    const grid = document.getElementById('cw-gif-grid');
    if (!grid) return;
    try {
      const ep = q ? '/api/chat/giphy/search?q=' + encodeURIComponent(q) : '/api/chat/giphy/trending';
      const res = await CW.api(ep);
      if (res.disabled) {
        grid.innerHTML =
          '<p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:16px 0">GIFs non activés — configurer GIPHY_API_KEY sur le serveur.</p>';
        return;
      }
      const gifs = res.data || [];
      if (!gifs.length) {
        grid.innerHTML =
          '<p style="grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding:16px 0">Aucun résultat.</p>';
        return;
      }
      grid.innerHTML = gifs
        .map(
          (g) =>
            '<div class="cw-gif-item" data-url="' +
            CW.escCW(g.url) +
            '"><img src="' +
            CW.escCW(g.preview_url || g.url) +
            '" alt="" loading="lazy"></div>'
        )
        .join('');
      grid.querySelectorAll('.cw-gif-item').forEach((el) => {
        el.addEventListener('click', () => selectGif(CW, el.dataset.url || ''));
      });
    } catch (e) {
      grid.innerHTML =
        '<p style="grid-column:1/-1;text-align:center;color:var(--danger);font-size:12px">Erreur de chargement.</p>';
    }
  }

  async function selectGif(CW, url) {
    document.querySelector('.cw-modal-overlay')?.remove();
    if (!CW.activeId || !url) return;
    try {
      await CW.api('/api/chat/channels/' + CW.activeId + '/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: '', gif_url: url }),
      });
      await CW.selectChannel(CW.activeId);
    } catch (e) {
      console.warn('[chat-v2]', e);
    }
  }

  async function togglePin(CW, msgId, isPinned) {
    if (!CW.activeId) return;
    try {
      await CW.api(
        '/api/chat/channels/' + CW.activeId + '/messages/' + msgId + '/pin',
        { method: isPinned ? 'DELETE' : 'POST' }
      );
      await CW.selectChannel(CW.activeId);
    } catch (e) {
      console.warn('[chat-v2]', e);
    }
  }

  // ── Date separators ─────────────────────────────────────
  function msgDateKey(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso.replace(' ', 'T'));
      return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
    } catch (e) { return ''; }
  }
  function fmtDateSep(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso.replace(' ', 'T'));
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const msgDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      const diff = Math.round((today - msgDay) / 86400000);
      if (diff === 0) return "Aujourd'hui";
      if (diff === 1) return 'Hier';
      return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    } catch (e) { return ''; }
  }
  function buildDateSepEl(iso) {
    const div = document.createElement('div');
    div.className = 'cw-date-sep';
    div.dataset.dateKey = msgDateKey(iso);
    const span = document.createElement('span');
    span.className = 'cw-date-sep-lbl';
    span.textContent = fmtDateSep(iso);
    div.appendChild(span);
    return div;
  }
  function addDateSeparators() {
    const box = document.getElementById('cw-messages');
    if (!box) return;
    const wraps = Array.from(box.querySelectorAll('.cw-msg-wrap'));
    let lastDk = '';
    wraps.forEach((w) => {
      const at = w.dataset.at || '';
      if (!at) return;
      const dk = msgDateKey(at);
      if (dk && dk !== lastDk) {
        lastDk = dk;
        const existingSep = w.previousElementSibling;
        if (existingSep && existingSep.classList.contains('cw-date-sep') && existingSep.dataset.dateKey === dk) return;
        box.insertBefore(buildDateSepEl(at), w);
      }
    });
  }
  function scrollToMsg(id) {
    const box = document.getElementById('cw-messages');
    const el = box && box.querySelector('.cw-msg-wrap[data-id="' + id + '"]');
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.style.outline = '2px solid var(--accent)';
    setTimeout(() => { el.style.outline = ''; }, 1200);
  }
  // ── Reply ────────────────────────────────────────────────
  function cwStartReply(msg) {
    cwReplyTo = { id: msg.id, user_nom: msg.user_nom, body: msg.body || '' };
    const bar = document.getElementById('cw-reply-bar');
    const pname = document.getElementById('cw-reply-pname');
    const pbody = document.getElementById('cw-reply-pbody');
    if (bar) bar.classList.add('cw-show');
    if (pname) pname.textContent = msg.user_nom || '';
    if (pbody) pbody.textContent = (msg.body || '(pièce jointe)').substring(0, 80);
    const inp = document.getElementById('cw-input');
    if (inp) inp.focus();
  }
  function cwCancelReply() {
    cwReplyTo = null;
    const bar = document.getElementById('cw-reply-bar');
    if (bar) bar.classList.remove('cw-show');
  }
  // ── Delete ───────────────────────────────────────────────
  async function cwDeleteMsg(CW, msgId) {
    if (!CW.activeId) return;
    try {
      await CW.api('/api/chat/channels/' + CW.activeId + '/messages/' + msgId, { method: 'DELETE' });
      // Update DOM — replace bubble with deleted placeholder
      const wrap = document.querySelector('.cw-msg-wrap[data-id="' + msgId + '"]');
      if (wrap) {
        const mine = wrap.classList.contains('cw-mine');
        const bubble = wrap.querySelector('.cw-msg-mine, .cw-msg-theirs');
        if (bubble) {
          bubble.innerHTML = 'Message supprimé.';
          bubble.className = (mine ? 'cw-msg-mine' : 'cw-msg-theirs') + ' cw-msg-deleted';
        }
        // Remove reactions, reply context, fwd tag, menu
        wrap.querySelectorAll('.cw-msg-reply-ctx,.cw-msg-fwd-tag,.cw-reaction-pill,.cw-msg-menu-btn,.cw-msg-menu').forEach(e => e.remove());
      }
    } catch (e) { console.warn('[chat-v2]', e); }
  }
  // ── Edit ─────────────────────────────────────────────────
  function cwStartEdit(CW, msg) {
    const wrap = document.querySelector('.cw-msg-wrap[data-id="' + msg.id + '"]');
    if (!wrap) return;
    const bubble = wrap.querySelector('.cw-msg-mine, .cw-msg-theirs');
    if (!bubble) return;
    const origHtml = bubble.innerHTML;
    bubble.innerHTML =
      '<textarea class="cw-edit-area" rows="2">' + (msg.body || '').replace(/</g, '&lt;') + '</textarea>' +
      '<div class="cw-edit-acts">' +
      '<button type="button">Annuler</button>' +
      '<button type="button" class="primary">Enregistrer</button></div>';
    const ta = bubble.querySelector('.cw-edit-area');
    const [cancelBtn, saveBtn] = bubble.querySelectorAll('.cw-edit-acts button');
    if (ta) { ta.focus(); ta.style.height = ta.scrollHeight + 'px'; }
    cancelBtn.addEventListener('click', () => { bubble.innerHTML = origHtml; });
    saveBtn.addEventListener('click', async () => {
      const newBody = (ta.value || '').trim();
      if (!newBody) return;
      try {
        await CW.api('/api/chat/channels/' + CW.activeId + '/messages/' + msg.id, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ body: newBody }),
        });
        // Reload the channel to reflect changes
        await CW.selectChannel(CW.activeId);
      } catch (e) { console.warn('[chat-v2]', e); }
    });
  }
  // ── Forward ──────────────────────────────────────────────
  async function cwStartForward(CW, msg) {
    let users = [];
    try { users = (await CW.api('/api/chat/users')) || []; } catch (e) { return; }
    const overlay = document.createElement('div');
    overlay.className = 'cw-modal-overlay';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    let selected = new Set();
    function renderList(q) {
      const ql = (q || '').toLowerCase();
      const list = users.filter(u => Number(u.id) !== Number(CW.uid) && (!ql || (u.nom || '').toLowerCase().includes(ql)));
      const el = overlay.querySelector('#cw-fwd-list');
      if (!el) return;
      el.innerHTML = list.map(u => {
        const sel = selected.has(u.id);
        return '<button type="button" class="cw-dm-row" data-uid="' + u.id + '" style="' + (sel ? 'color:var(--accent);background:var(--accent-bg)' : '') + '">' +
          (CW.escCW || ((s) => s))(u.nom || '') +
          (sel ? ' <span style="margin-left:auto">✓</span>' : '') + '</button>';
      }).join('') || '<p style="padding:12px;color:var(--muted);font-size:12px;margin:0">Aucun résultat</p>';
      el.querySelectorAll('.cw-dm-row').forEach(btn => {
        btn.addEventListener('click', () => {
          const uid = parseInt(btn.dataset.uid, 10);
          if (selected.has(uid)) selected.delete(uid); else selected.add(uid);
          const sendBtn = overlay.querySelector('#cw-fwd-send');
          if (sendBtn) sendBtn.disabled = selected.size === 0;
          renderList(overlay.querySelector('#cw-fwd-search').value);
        });
      });
    }
    const preview = (msg.body || '(pièce jointe)').substring(0, 60);
    overlay.innerHTML =
      '<div class="cw-modal"><h3>Transférer le message</h3>' +
      '<div style="padding:5px 9px;margin-bottom:12px;border-left:3px solid var(--muted);background:var(--accent-bg);border-radius:6px;font-size:12px;color:var(--text2)">' + (CW.escCW || ((s) => s))(preview) + '</div>' +
      '<input type="search" id="cw-fwd-search" placeholder="Rechercher…" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;margin-bottom:8px;box-sizing:border-box">' +
      '<div id="cw-fwd-list" style="max-height:200px;overflow-y:auto;border:1px solid var(--border);border-radius:8px"></div>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">' +
      '<button type="button" class="cw-btn-ghost" onclick="this.closest(\'.cw-modal-overlay\').remove()">Annuler</button>' +
      '<button type="button" id="cw-fwd-send" class="cw-btn-primary" disabled>Transférer</button></div></div>';
    document.body.appendChild(overlay);
    renderList('');
    overlay.querySelector('#cw-fwd-search').addEventListener('input', function () { renderList(this.value); });
    overlay.querySelector('#cw-fwd-send').addEventListener('click', async () => {
      if (!selected.size) return;
      try {
        await CW.api('/api/chat/channels/' + CW.activeId + '/messages/' + msg.id + '/forward', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_ids: [...selected] }),
        });
        overlay.remove();
        // Refresh channel list
        if (CW.loadChannels) await CW.loadChannels(); else if (CW.syncChatState) await CW.syncChatState(true);
      } catch (e) { console.warn('[chat-v2]', e); }
    });
    setTimeout(() => overlay.querySelector('#cw-fwd-search').focus(), 50);
  }
  // ── Close all menus on click outside ────────────────────
  function setupMenuClose() {
    if (document._cwMenuClose) return;
    document._cwMenuClose = true;
    document.addEventListener('click', () => {
      document.querySelectorAll('.cw-msg-menu.cw-open').forEach(m => m.classList.remove('cw-open'));
    });
  }

  function patchRenderMsg(CW) {
    const orig = CW.renderMsg;
    CW.renderMsg = function (msg) {
      const mine = Number(msg.user_id) === Number(CW.uid) || msg.is_mine;

      // ── Deleted message placeholder ──────────────────────
      if (msg.is_soft_deleted) {
        const wrap = document.createElement('div');
        wrap.className = 'cw-msg-wrap ' + (mine ? 'cw-mine' : 'cw-theirs');
        wrap.dataset.id = String(msg.id);
        if (msg.created_at) wrap.dataset.at = String(msg.created_at);
        wrap.innerHTML = '<div class="cw-msg-bubble-wrap"><div class="' +
          (mine ? 'cw-msg-mine' : 'cw-msg-theirs') + ' cw-msg-deleted">Message supprimé.</div></div>';
        return wrap;
      }

      const wrap = orig(msg);
      if (!wrap) return wrap;
      wrap.style.position = 'relative';

      const ch = CW.channels.find((c) => c.id === CW.activeId);
      const canPin = ch && ch.type === 'channel' && ADMIN.has(CW.role);
      const msgAge = Date.now() - new Date((msg.created_at || '').replace(' ', 'T')).getTime();
      const canEdit = mine && !msg.attachment_url && msgAge < 900000;
      const canDel = mine;

      if (msg.pinned_at) wrap.classList.add('cw-pinned');

      // ── Format body with mentions ────────────────────────
      const bodyEl = wrap.querySelector('.cw-msg-mine, .cw-msg-theirs');
      if (bodyEl && msg.body) {
        const CM = window.ChatMentions;
        const html = CM
          ? CM.formatBodyHtml((msg.body || '').trim(), channelMembers, CW.escCW)
          : CW.escCW((msg.body || '').trim()).replace(/\r\n/g, '\n').replace(/\n/g, '<br>')
              .replace(/@([A-Za-z0-9_]+)/g, '<span style="color:var(--accent);font-weight:700">@$1</span>');
        const attach = bodyEl.querySelector('.cw-msg-attach');
        const meta = bodyEl.querySelector('.cw-msg-meta');
        bodyEl.innerHTML = (meta ? meta.outerHTML : '') + html + (attach ? attach.outerHTML : '');
      }

      // ── Edited label ─────────────────────────────────────
      if (msg.edited_at && bodyEl) {
        try {
          const ed = new Date(msg.edited_at.replace(' ', 'T'));
          const d = ed.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
          const lbl = document.createElement('span');
          lbl.className = 'cw-msg-edited-lbl';
          lbl.textContent = 'modifié le ' + d;
          const meta = bodyEl.querySelector('.cw-msg-meta');
          if (meta) meta.appendChild(lbl); else bodyEl.appendChild(lbl);
        } catch (e) {}
      }

      const bwrap = wrap.querySelector('.cw-msg-bubble-wrap');
      if (bwrap) {
        // ── Forwarded indicator ──────────────────────────────
        if (msg.is_forwarded) {
          const tag = document.createElement('div');
          tag.className = 'cw-msg-fwd-tag';
          tag.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 10 20 15 15 20"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/></svg>' +
            'Transféré' + (msg.forwarded_from_nom ? ' · ' + CW.escCW(msg.forwarded_from_nom) : '');
          bwrap.insertBefore(tag, bwrap.firstChild);
          const bbl = bwrap.querySelector('.cw-msg-mine,.cw-msg-theirs');
          if (bbl) bbl.classList.add('cw-msg-fwd');
        }
        // ── Reply context ────────────────────────────────────
        if (msg.reply_to) {
          const ctx = document.createElement('div');
          ctx.className = 'cw-msg-reply-ctx';
          const rb = msg.reply_to.is_soft_deleted
            ? '<em>Message supprimé</em>'
            : CW.escCW((msg.reply_to.body || '').substring(0, 80));
          ctx.innerHTML = '<div class="cw-reply-name">' + CW.escCW(msg.reply_to.user_nom || '') + '</div>' +
            '<div class="cw-reply-body">' + rb + '</div>';
          ctx.addEventListener('click', () => scrollToMsg(msg.reply_to.id));
          bwrap.insertBefore(ctx, bwrap.firstChild);
        }
      }

      // Le bouton ⋮ et le menu déroulant sont déjà créés par renderMsg
      // dans chat_widget.js (appelé via orig(msg) ci-dessus).
      // Ne PAS recréer ici sinon on a deux boutons superposés.
      return wrap;
    };
  }

  function patchSendMessage(CW) {
    const orig = CW.sendMessage;
    CW.sendMessage = async function () {
      // Inject reply_to_id if replying
      if (cwReplyTo) {
        const origApi = CW.api;
        const replyId = cwReplyTo.id;
        const patchedApi = async function (path, opts) {
          if (opts && opts.method === 'POST' && path.includes('/messages') && !path.includes('/forward') && !path.includes('/pin') && !path.includes('/reactions')) {
            if (opts.headers && opts.headers['Content-Type'] === 'application/json' && opts.body) {
              try {
                const data = JSON.parse(opts.body);
                if (data && !data.gif_url) {
                  data.reply_to_id = replyId;
                  opts = { ...opts, body: JSON.stringify(data) };
                }
              } catch (e) {}
            }
          }
          return origApi.call(this, path, opts);
        };
        CW.api = patchedApi;
        try {
          await orig.apply(this, arguments);
        } finally {
          CW.api = origApi;
          cwCancelReply();
        }
      } else {
        await orig.apply(this, arguments);
      }
    };
  }

  function patchSelectChannel(CW) {
    const orig = CW.selectChannel;
    CW.selectChannel = async function (id) {
      cwCancelReply();
      await orig(id);
      // Add date separators after messages are rendered
      setTimeout(addDateSeparators, 50);
      try {
        channelMembers = (await CW.api('/api/chat/channels/' + id + '/members')) || [];
      } catch (e) {
        channelMembers = [];
      }
      const ch = CW.channels.find((c) => c.id === id);
      let pinBtn = document.getElementById('cw-pinned-btn');
      if (!pinBtn) {
        const hdr = document.getElementById('cw-panel-header');
        const closeBtn = document.getElementById('cw-close');
        if (hdr && closeBtn) {
          pinBtn = document.createElement('button');
          pinBtn.type = 'button';
          pinBtn.id = 'cw-pinned-btn';
          pinBtn.className = 'cw-header-btn cw-hidden';
          pinBtn.title = 'Messages épinglés';
          pinBtn.innerHTML =
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>';
          pinBtn.onclick = () => openPinned(CW);
          hdr.insertBefore(pinBtn, closeBtn);
        }
      }
      if (pinBtn) pinBtn.classList.toggle('cw-hidden', !(ch && ch.type === 'channel'));
    };
  }

  async function openPinned(CW) {
    if (!CW.activeId) return;
    let pinned = [];
    try {
      pinned = (await CW.api('/api/chat/channels/' + CW.activeId + '/pinned')) || [];
    } catch (e) {
      return;
    }
    const overlay = document.createElement('div');
    overlay.className = 'cw-modal-overlay';
    overlay.onclick = (e) => {
      if (e.target === overlay) overlay.remove();
    };
    const list = pinned.length
      ? pinned
          .map(
            (m) =>
              '<div style="padding:10px 0;border-bottom:1px solid var(--border)"><div style="font-size:10px;color:var(--muted)">' +
              CW.escCW(m.user_nom) +
              ' · ' +
              CW.escCW(CW.fmtTime(m.created_at)) +
              '</div><div style="font-size:13px;margin-top:4px">' +
              CW.escCW((m.body || '').trim() || '(pièce jointe)') +
              '</div></div>'
          )
          .join('')
      : '<p style="color:var(--muted);font-size:13px">Aucun message épinglé.</p>';
    overlay.innerHTML =
      '<div class="cw-modal"><h3>Messages épinglés</h3>' + list + '<button type="button" style="margin-top:12px;padding:9px 16px;border-radius:8px;background:var(--accent);color:var(--bg);border:none;font-weight:700;cursor:pointer;font-family:inherit" onclick="this.closest(\'.cw-modal-overlay\').remove()">Fermer</button></div>';
    document.body.appendChild(overlay);
  }

  function applyV2(CW) {
    if (v2Patched) return;
    v2Patched = true;
    injectV2Styles();
    const origInit = CW.init;
    CW.init = async function () {
      const ok = await origInit.apply(this, arguments);
      if (ok) {
        patchInputRow(CW);
        checkNotifPerm();
      }
      return ok;
    };
    patchRenderMsg(CW);
    patchSendMessage(CW);
    patchSelectChannel(CW);
    setupMenuClose();
    if (CW._inited) {
      patchInputRow(CW);
      checkNotifPerm();
    }
  }

  async function boot() {
    const CW = await waitCW();
    if (!CW) return;
    applyV2(CW);
    const origDestroy = CW.destroy;
    CW.destroy = function () {
      v2Patched = false;
      channelMembers = [];
      return origDestroy.apply(this, arguments);
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
