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
.cw-gif-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;max-height:260px;overflow-y:auto;margin-top:10px}
.cw-gif-item{border-radius:6px;overflow:hidden;cursor:pointer;aspect-ratio:1;background:var(--border)}
.cw-gif-item img{width:100%;height:100%;object-fit:cover}
#cw-notif-modal{position:fixed;inset:0;z-index:20000;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center;padding:20px}
.cw-notif-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px 24px;width:min(380px,100%);text-align:center}
.cw-modal-overlay{position:fixed;inset:0;z-index:8020;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px}
.cw-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;width:min(500px,100%);max-height:85vh;overflow-y:auto}
.cw-modal h3{margin:0 0 14px;font-size:15px;font-weight:700}
`;
    document.head.appendChild(s);
  }

  function patchInputRow(CW) {
    const row = document.getElementById('cw-input-row');
    if (!row || document.getElementById('cw-action-expand')) return;
    row.innerHTML =
      '<input type="file" id="cw-file-input" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip">' +
      '<button type="button" id="cw-action-expand" aria-label="Plus d\'options">+</button>' +
      '<div id="cw-action-btns">' +
      '<button type="button" id="cw-attach" aria-label="Pièce jointe" title="Pièce jointe">' +
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg></button>' +
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
    document.getElementById('cw-send')?.addEventListener('click', () => CW.sendMessage());
    const inp = document.getElementById('cw-input');
    if (inp) {
      inp.addEventListener('keydown', (e) => {
        if (handleMentionKeys(e, inp)) return;
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          CW.sendMessage();
        }
      });
      inp.addEventListener('input', function () {
        if (typeof resizeCwInput === 'function') resizeCwInput(this);
        const val = this.value;
        const cur = this.selectionStart;
        const before = val.substring(0, cur);
        const atMatch = before.match(/@(\w*)$/);
        if (atMatch) {
          mentionQuery = atMatch[1].toLowerCase();
          mentionStart = before.lastIndexOf('@');
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

  function renderMentionDd(CW) {
    const dd = document.getElementById('cw-mention-dd');
    if (!dd) return;
    const q = mentionQuery || '';
    const myUid = CW.uid;
    const candidates = [
      { id: 'all', nom: 'tous', role: 'Mentionner tout le canal' },
      ...channelMembers.filter((m) => (m.id || m.user_id) !== myUid),
    ].filter((m) => {
      const n = (m.nom || '').toLowerCase();
      return !q || n.indexOf(q) >= 0;
    });
    if (!candidates.length) {
      closeMentionDd();
      return;
    }
    mentionFocusIdx = -1;
    dd.style.display = 'block';
    dd.innerHTML = candidates
      .map((m, i) => {
        const nom = m.nom || '';
        return (
          '<div class="cw-mention-item" data-nom="' +
          CW.escCW(nom) +
          '" data-idx="' +
          i +
          '"><span style="font-weight:600">' +
          CW.escCW(nom) +
          '</span><span style="font-size:11px;color:var(--muted);margin-left:6px">' +
          CW.escCW(m.role || '') +
          '</span></div>'
        );
      })
      .join('');
    dd.querySelectorAll('.cw-mention-item').forEach((el) => {
      el.addEventListener('mousedown', (e) => {
        e.preventDefault();
        insertMention(el.dataset.nom || '');
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
    if (e.key === 'Enter' && mentionFocusIdx >= 0) {
      e.preventDefault();
      const nom = items[mentionFocusIdx]?.dataset.nom;
      if (nom) insertMention(nom);
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

  function patchRenderMsg(CW) {
    const orig = CW.renderMsg;
    CW.renderMsg = function (msg) {
      const wrap = orig(msg);
      if (!wrap) return wrap;
      const ch = CW.channels.find((c) => c.id === CW.activeId);
      const canPin = ch && ch.type === 'channel' && ADMIN.has(CW.role);
      if (msg.pinned_at) wrap.classList.add('cw-pinned');
      const bodyEl = wrap.querySelector('.cw-msg-mine, .cw-msg-theirs');
      if (bodyEl && msg.body) {
        const html = CW.escCW((msg.body || '').trim()).replace(
          /@(\w+)/g,
          '<span style="color:var(--accent);font-weight:700">@$1</span>'
        );
        const attach = bodyEl.querySelector('.cw-msg-attach');
        const meta = bodyEl.querySelector('.cw-msg-meta');
        bodyEl.innerHTML = (meta ? meta.outerHTML : '') + html + (attach ? attach.outerHTML : '');
      }
      if (canPin) {
        const pin = document.createElement('button');
        pin.type = 'button';
        pin.className = 'cw-msg-pin' + (msg.pinned_at ? ' pinned-active' : '');
        pin.title = msg.pinned_at ? 'Désépingler' : 'Épingler';
        pin.innerHTML =
          '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>';
        pin.onclick = () => togglePin(CW, msg.id, !!msg.pinned_at);
        wrap.style.position = 'relative';
        wrap.appendChild(pin);
      }
      return wrap;
    };
  }

  function patchSelectChannel(CW) {
    const orig = CW.selectChannel;
    CW.selectChannel = async function (id) {
      await orig(id);
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
    patchSelectChannel(CW);
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
