/**
 * MySifa — Widget chat flottant (barre portail / bulle apps).
 * Requiert : window.__MYSIFA_APP__ (optionnel, défaut 'unknown')
 * Lit l'utilisateur depuis window.__MYSIFA_UID__ ou GET /api/auth/me
 */
(function () {
  'use strict';

  const CW = {
    uid: 0,
    nom: '',
    role: '',
    isPortal: false,
    open: false,
    activeId: null,
    channels: [],
    lastMsgId: 0,
    pollTimer: null,
    badgeTimer: null,
    soundEnabled: localStorage.getItem('chat_sound') !== '0',
    _audioCtx: null,
    _inited: false,
  };

  const ICO_MSG =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  const ICO_SEND =
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';

  const CW_STYLES = `
@keyframes cwPulse{0%,100%{opacity:1}50%{opacity:.3}}
#cw-bar{position:fixed;bottom:24px;left:24px;z-index:8002;width:340px;max-width:calc(100vw - 48px);
  background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 16px;
  display:flex;align-items:center;gap:12px;cursor:pointer;transition:border-color .15s;font-family:inherit}
#cw-bar:hover{border-color:var(--accent)}
#cw-bar-icon{width:38px;height:38px;border-radius:50%;background:var(--accent-bg);
  display:flex;align-items:center;justify-content:center;flex-shrink:0;color:var(--accent)}
#cw-bar-text{flex:1;min-width:0}
#cw-bar-title{font-size:13px;font-weight:700;color:var(--text);display:flex;align-items:center;gap:8px}
#cw-bar-preview{font-size:11px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#cw-bar-badge,#cw-bubble-badge{background:var(--accent);color:#0a0e17;font-size:11px;font-weight:700;
  padding:1px 6px;border-radius:99px;line-height:1.4;display:none}
#cw-bar-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);flex-shrink:0;display:none;
  animation:cwPulse 1.4s ease-in-out infinite}
#cw-bubble{position:fixed;z-index:8002;
  bottom:calc(max(24px, env(safe-area-inset-bottom, 0px)) + 58px);
  right:max(84px, calc(env(safe-area-inset-right, 0px) + 24px));
  width:46px;height:46px;border-radius:50%;background:var(--card);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;cursor:pointer;
  transition:border-color .15s;color:var(--accent);box-shadow:0 4px 16px rgba(0,0,0,.25)}
#cw-bubble:hover{border-color:var(--accent)}
#cw-bubble-badge{position:absolute;top:-4px;right:-4px}
#cw-panel{position:fixed;z-index:8003;width:360px;height:480px;max-height:calc(100vh - 80px);
  background:var(--card);border:1px solid var(--border);border-radius:14px;display:flex;overflow:hidden;
  font-family:'Segoe UI',system-ui,sans-serif}
#cw-panel.cw-hidden{display:none!important}
#cw-panel.cw-mode-bar{bottom:80px;left:24px}
#cw-panel.cw-mode-bubble{
  bottom:calc(max(24px,env(safe-area-inset-bottom,0px)) + 120px);
  right:max(84px,calc(env(safe-area-inset-right,0px)+24px))}
#cw-panel-left{width:130px;flex-shrink:0;border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow-y:auto;min-height:0}
.cw-section-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;padding:10px 12px 4px}
.cw-channel-item{padding:7px 12px;font-size:12px;color:var(--text2);display:flex;align-items:center;
  gap:6px;cursor:pointer;transition:background .1s;border:none;background:transparent;width:100%;
  text-align:left;font-family:inherit}
.cw-channel-item:hover{background:rgba(255,255,255,.04)}
body.light .cw-channel-item:hover{background:rgba(0,0,0,.04)}
.cw-channel-item.cw-active{background:var(--accent-bg);color:var(--accent);font-weight:600}
.cw-unread-badge{margin-left:auto;background:var(--accent);color:#0a0e17;font-size:9px;font-weight:700;
  padding:1px 5px;border-radius:99px;flex-shrink:0}
.cw-chan-label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
#cw-new-dm{margin:8px 10px;padding:6px 10px;border-radius:8px;border:1px solid var(--border);
  background:transparent;color:var(--accent);font-size:11px;font-weight:700;cursor:pointer;font-family:inherit}
#cw-new-dm:hover{background:var(--accent-bg)}
#cw-panel-right{flex:1;display:flex;flex-direction:column;min-width:0}
#cw-panel-header{padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;
  font-size:13px;font-weight:600;color:var(--text);gap:8px}
#cw-panel-title{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#cw-close{margin-left:auto;background:none;border:none;color:var(--muted);font-size:18px;
  cursor:pointer;line-height:1;padding:0 4px;font-family:inherit}
#cw-close:hover{color:var(--text)}
#cw-messages{flex:1;overflow-y:auto;padding:10px 12px;display:flex;flex-direction:column;gap:8px;min-height:0}
.cw-msg-mine{align-self:flex-end;background:var(--accent-bg);border:1px solid rgba(34,211,238,.2);
  border-radius:10px 0 10px 10px;padding:6px 10px;font-size:12px;color:var(--text);max-width:80%;word-break:break-word}
.cw-msg-theirs{align-self:flex-start;background:rgba(255,255,255,.05);border:1px solid var(--border);
  border-radius:0 10px 10px 10px;padding:6px 10px;font-size:12px;color:var(--text);max-width:80%;word-break:break-word}
body.light .cw-msg-theirs{background:rgba(0,0,0,.04)}
.cw-msg-meta{font-size:10px;color:var(--muted);margin-bottom:2px}
#cw-input-row{padding:8px 10px;border-top:1px solid var(--border);display:flex;gap:6px;align-items:flex-end}
#cw-input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;
  font-size:12px;color:var(--text);resize:none;font-family:inherit;max-height:80px;overflow-y:auto;outline:none}
#cw-input:focus{border-color:var(--accent)}
#cw-send{background:var(--accent-bg);border:1px solid rgba(34,211,238,.3);border-radius:8px;padding:7px 10px;
  cursor:pointer;display:flex;align-items:center;color:var(--accent);flex-shrink:0}
#cw-send:hover{filter:brightness(1.05)}
#cw-send:disabled{opacity:.5;cursor:not-allowed}
#cw-dm-picker{position:absolute;inset:0;background:var(--card);z-index:2;display:flex;flex-direction:column}
#cw-dm-picker.cw-hidden{display:none}
#cw-dm-search{margin:10px;padding:8px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:12px;font-family:inherit}
#cw-dm-list{flex:1;overflow-y:auto}
.cw-dm-row{display:block;width:100%;text-align:left;padding:10px 12px;border:none;border-bottom:1px solid var(--border);
  background:transparent;color:var(--text);font-size:12px;cursor:pointer;font-family:inherit}
.cw-dm-row:hover{background:var(--accent-bg);color:var(--accent)}
#cw-empty-hint{flex:1;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:12px;padding:16px;text-align:center}
`;

  function escCW(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmtTime(iso) {
    if (!iso) return '';
    try {
      const s = String(iso).trim();
      const d = new Date(s.includes('T') ? s : s.replace(' ', 'T'));
      return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '';
    }
  }

  function jouerSon() {
    if (!CW.soundEnabled) return;
    try {
      if (!CW._audioCtx) CW._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = CW._audioCtx;
      if (ctx.state === 'suspended') ctx.resume();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g);
      g.connect(ctx.destination);
      o.type = 'sine';
      o.frequency.setValueAtTime(523, ctx.currentTime);
      o.frequency.setValueAtTime(659, ctx.currentTime + 0.12);
      g.gain.setValueAtTime(0, ctx.currentTime);
      g.gain.linearRampToValueAtTime(0.25, ctx.currentTime + 0.01);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
      o.start(ctx.currentTime);
      o.stop(ctx.currentTime + 0.45);
    } catch (e) {}
  }

  async function api(path, opts) {
    const r = await fetch(path, { credentials: 'include', ...(opts || {}) });
    if (r.status === 401) throw new Error('auth');
    if (!r.ok) {
      let d = 'Erreur';
      try {
        const j = await r.json();
        d = j.detail ? (typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)) : d;
      } catch (e) {}
      throw new Error(d);
    }
    if (r.status === 204) return null;
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('application/json')) return r.json();
    return null;
  }

  function syncFromWindow() {
    CW.uid = Number(window.__MYSIFA_UID__) || 0;
    CW.nom = window.__MYSIFA_NOM__ || '';
    CW.role = window.__MYSIFA_ROLE__ || '';
    CW.isPortal = window.__MYSIFA_APP__ === 'portal';
  }

  async function fetchMe() {
    try {
      const u = await api('/api/auth/me');
      if (u && u.id) {
        window.__MYSIFA_UID__ = u.id;
        window.__MYSIFA_NOM__ = u.nom || '';
        window.__MYSIFA_ROLE__ = u.role || '';
        syncFromWindow();
        return true;
      }
    } catch (e) {}
    return false;
  }

  function injectStyles() {
    if (document.getElementById('cw-styles')) return;
    const st = document.createElement('style');
    st.id = 'cw-styles';
    st.textContent = CW_STYLES;
    document.head.appendChild(st);
  }

  function buildDom() {
    const hasTrigger = CW.isPortal
      ? document.getElementById('cw-bar')
      : document.getElementById('cw-bubble');
    if (hasTrigger && document.getElementById('cw-panel')) return;
    if (document.getElementById('cw-bar')) document.getElementById('cw-bar').remove();
    if (document.getElementById('cw-bubble')) document.getElementById('cw-bubble').remove();
    if (document.getElementById('cw-panel')) document.getElementById('cw-panel').remove();

    if (CW.isPortal) {
      const bar = document.createElement('div');
      bar.id = 'cw-bar';
      bar.innerHTML =
        '<div id="cw-bar-icon">' +
        ICO_MSG +
        '</div><div id="cw-bar-text"><div id="cw-bar-title">Messagerie <span id="cw-bar-badge"></span></div>' +
        '<div id="cw-bar-preview">Aucun message</div></div><div id="cw-bar-dot"></div>';
      bar.addEventListener('click', () => togglePanel());
      document.body.appendChild(bar);
    } else {
      const bub = document.createElement('button');
      bub.type = 'button';
      bub.id = 'cw-bubble';
      bub.setAttribute('aria-label', 'Messagerie');
      bub.innerHTML = ICO_MSG + '<span id="cw-bubble-badge"></span>';
      bub.addEventListener('click', () => togglePanel());
      document.body.appendChild(bub);
    }

    const panel = document.createElement('div');
    panel.id = 'cw-panel';
    panel.className = 'cw-hidden ' + (CW.isPortal ? 'cw-mode-bar' : 'cw-mode-bubble');
    panel.innerHTML =
      '<div id="cw-panel-left">' +
      '<div class="cw-section-label">Canaux</div><div id="cw-channels"></div>' +
      '<div class="cw-section-label" style="margin-top:8px">Messages directs</div><div id="cw-dms"></div>' +
      '<button type="button" id="cw-new-dm">+ DM</button></div>' +
      '<div id="cw-panel-right" style="position:relative">' +
      '<div id="cw-dm-picker" class="cw-hidden">' +
      '<input type="search" id="cw-dm-search" placeholder="Rechercher un collègue…" autocomplete="off">' +
      '<div id="cw-dm-list"></div></div>' +
      '<div id="cw-panel-header"><span id="cw-panel-title">Messagerie</span>' +
      '<button type="button" id="cw-close" aria-label="Fermer">×</button></div>' +
      '<div id="cw-messages"><div id="cw-empty-hint">Sélectionnez un canal</div></div>' +
      '<div id="cw-input-row"><textarea id="cw-input" rows="1" placeholder="Message…"></textarea>' +
      '<button type="button" id="cw-send" aria-label="Envoyer">' +
      ICO_SEND +
      '</button></div></div>';
    document.body.appendChild(panel);

    document.getElementById('cw-close').addEventListener('click', () => togglePanel(false));
    document.getElementById('cw-send').addEventListener('click', () => sendMessage());
    document.getElementById('cw-new-dm').addEventListener('click', () => openNewDm());
    const inp = document.getElementById('cw-input');
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    inp.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 80) + 'px';
    });
  }

  function renderMsg(msg) {
    const mine = Number(msg.user_id) === Number(CW.uid);
    const metaEl = mine
      ? ''
      : '<div class="cw-msg-meta">' + escCW(msg.user_nom) + ' · ' + escCW(fmtTime(msg.created_at)) + '</div>';
    const div = document.createElement('div');
    div.className = mine ? 'cw-msg-mine' : 'cw-msg-theirs';
    div.dataset.id = String(msg.id);
    div.innerHTML = metaEl + escCW(msg.body);
    return div;
  }

  function isNearBottom(el, tol) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < (tol || 40);
  }

  function scrollMessagesBottom() {
    const box = document.getElementById('cw-messages');
    if (box) requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
  }

  function renderChannelItem(ch) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'cw-channel-item' + (ch.id === CW.activeId ? ' cw-active' : '');
    btn.dataset.id = String(ch.id);
    const unread = Number(ch.unread_count) || 0;
    btn.innerHTML =
      '<span class="cw-chan-label">' +
      escCW(ch.display_name || ch.name || 'Canal') +
      '</span>' +
      (unread > 0
        ? '<span class="cw-unread-badge">' + escCW(unread > 99 ? '99+' : unread) + '</span>'
        : '');
    btn.addEventListener('click', () => selectChannel(ch.id));
    return btn;
  }

  function renderChannelLists() {
    const chans = CW.channels.filter((c) => c.type === 'channel');
    const dms = CW.channels.filter((c) => c.type === 'direct');
    const chEl = document.getElementById('cw-channels');
    const dmEl = document.getElementById('cw-dms');
    if (!chEl || !dmEl) return;
    chEl.innerHTML = '';
    dmEl.innerHTML = '';
    chans.forEach((c) => chEl.appendChild(renderChannelItem(c)));
    dms.forEach((c) => dmEl.appendChild(renderChannelItem(c)));
    if (!chans.length) chEl.innerHTML = '<p style="padding:6px 12px;font-size:11px;color:var(--muted);margin:0">—</p>';
    if (!dms.length) dmEl.innerHTML = '<p style="padding:6px 12px;font-size:11px;color:var(--muted);margin:0">—</p>';
  }

  async function loadChannels() {
    CW.channels = (await api('/api/chat/channels')) || [];
    renderChannelLists();

    if (!CW.activeId && CW.channels.length) {
      let pick = CW.channels[0];
      let maxU = -1;
      CW.channels.forEach((c) => {
        const u = Number(c.unread_count) || 0;
        if (u > maxU) {
          maxU = u;
          pick = c;
        }
      });
      await selectChannel(pick.id);
    } else if (CW.activeId) {
      await selectChannel(CW.activeId);
    }
  }

  async function selectChannel(id) {
    CW.activeId = id;
    CW.lastMsgId = 0;
    renderChannelLists();
    const ch = CW.channels.find((c) => c.id === id);
    const title = document.getElementById('cw-panel-title');
    if (title) title.textContent = ch ? ch.display_name || ch.name || 'Canal' : 'Canal';

    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');

    const box = document.getElementById('cw-messages');
    if (!box) return;
    box.innerHTML = '<p style="text-align:center;color:var(--muted);font-size:11px;padding:12px">Chargement…</p>';

    try {
      const data = await api('/api/chat/channels/' + id + '/messages');
      const msgs = data.messages || [];
      box.innerHTML = '';
      msgs.forEach((m) => {
        box.appendChild(renderMsg(m));
        if (m.id > CW.lastMsgId) CW.lastMsgId = m.id;
      });
      if (!msgs.length) {
        box.innerHTML = '<div id="cw-empty-hint">Aucun message — soyez le premier.</div>';
      }
      scrollMessagesBottom();

      if (CW.pollTimer) clearInterval(CW.pollTimer);
      CW.pollTimer = setInterval(pollMessages, 5000);
    } catch (e) {
      box.innerHTML = '<div id="cw-empty-hint">Chargement impossible.</div>';
    }
  }

  async function pollMessages() {
    if (!CW.activeId || !CW.open) return;
    const box = document.getElementById('cw-messages');
    if (!box) return;
    const wasBottom = isNearBottom(box, 40);
    try {
      let path = '/api/chat/channels/' + CW.activeId + '/messages';
      if (CW.lastMsgId > 0) path += '?after=' + CW.lastMsgId;
      const data = await api(path);
      const incoming = data.messages || [];
      if (!incoming.length) return;
      const hint = box.querySelector('#cw-empty-hint');
      if (hint) hint.remove();
      let played = false;
      incoming.forEach((m) => {
        if (m.id <= CW.lastMsgId) return;
        if (Number(m.user_id) !== Number(CW.uid) && !played) {
          jouerSon();
          played = true;
        }
        box.appendChild(renderMsg(m));
        if (m.id > CW.lastMsgId) CW.lastMsgId = m.id;
      });
      if (wasBottom) scrollMessagesBottom();
      refreshBadge();
    } catch (e) {}
  }

  async function sendMessage() {
    if (!CW.activeId) return;
    const inp = document.getElementById('cw-input');
    const body = (inp && inp.value || '').trim();
    if (!body) return;
    const btn = document.getElementById('cw-send');
    if (btn) btn.disabled = true;
    try {
      const sent = await api('/api/chat/channels/' + CW.activeId + '/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body }),
      });
      if (inp) {
        inp.value = '';
        inp.style.height = 'auto';
      }
      const box = document.getElementById('cw-messages');
      if (box && sent && sent.id) {
        const hint = box.querySelector('#cw-empty-hint');
        if (hint) hint.remove();
        const m = {
          id: sent.id,
          user_id: CW.uid,
          user_nom: CW.nom,
          body: body,
          created_at: sent.created_at || new Date().toISOString().slice(0, 19).replace('T', ' '),
          is_mine: true,
        };
        box.appendChild(renderMsg(m));
        if (sent.id > CW.lastMsgId) CW.lastMsgId = sent.id;
      } else {
        await pollMessages();
      }
      scrollMessagesBottom();
      await loadChannels();
    } catch (e) {
      console.warn('[chat]', e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function refreshBadge() {
    try {
      const data = await api('/api/chat/unread');
      const total = Number(data.unread) || 0;
      const barBadge = document.getElementById('cw-bar-badge');
      const bubBadge = document.getElementById('cw-bubble-badge');
      const dot = document.getElementById('cw-bar-dot');
      const preview = document.getElementById('cw-bar-preview');

      if (barBadge) {
        if (total > 0) {
          barBadge.textContent = total > 99 ? '99+' : String(total);
          barBadge.style.display = '';
        } else barBadge.style.display = 'none';
      }
      if (bubBadge) {
        if (total > 0) {
          bubBadge.textContent = total > 99 ? '99+' : String(total);
          bubBadge.style.display = 'inline-flex';
        } else bubBadge.style.display = 'none';
      }
      if (dot) dot.style.display = total > 0 ? '' : 'none';

      if (preview && CW.isPortal) {
        const lm = data.last_message;
        if (lm && lm.body) {
          const who = lm.from_nom || lm.user_nom || 'Collègue';
          const prev = who + ' : ' + String(lm.body).slice(0, 48);
          preview.textContent = prev + (String(lm.body).length > 48 ? '…' : '');
        } else if (total > 0) {
          preview.textContent = total + ' message' + (total > 1 ? 's' : '') + ' non lu' + (total > 1 ? 's' : '');
        } else {
          preview.textContent = 'Aucun message non lu';
        }
      }

      if (window.MySifaChatBadge && typeof window.MySifaChatBadge.refresh === 'function') {
        window.MySifaChatBadge.refresh();
      }
    } catch (e) {}
  }

  async function openNewDm() {
    const picker = document.getElementById('cw-dm-picker');
    const list = document.getElementById('cw-dm-list');
    const search = document.getElementById('cw-dm-search');
    if (!picker || !list) return;
    picker.classList.remove('cw-hidden');
    let users = [];
    try {
      users = (await api('/api/chat/users')) || [];
    } catch (e) {
      list.innerHTML = '<p style="padding:12px;color:var(--muted);font-size:12px">Erreur chargement</p>';
      return;
    }
    function renderList(q) {
      const ql = (q || '').toLowerCase();
      const filtered = users.filter((u) => !ql || (u.nom || '').toLowerCase().includes(ql));
      if (!filtered.length) {
        list.innerHTML = '<p style="padding:12px;color:var(--muted);font-size:12px">Aucun résultat</p>';
        return;
      }
      list.innerHTML = '';
      filtered.forEach((u) => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = 'cw-dm-row';
        row.textContent = u.nom || 'Utilisateur';
        row.addEventListener('click', async () => {
          picker.classList.add('cw-hidden');
          try {
            const r = await api('/api/chat/channels', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ type: 'direct', user_id: u.id }),
            });
            await loadChannels();
            await selectChannel(r.id);
          } catch (e) {}
        });
        list.appendChild(row);
      });
    }
    renderList('');
    if (search) {
      search.value = '';
      search.oninput = () => renderList(search.value);
      requestAnimationFrame(() => search.focus());
    }
  }

  async function togglePanel(force) {
    const panel = document.getElementById('cw-panel');
    if (!panel) return;
    const next = typeof force === 'boolean' ? force : !CW.open;
    CW.open = next;
    if (CW.open) {
      panel.classList.remove('cw-hidden');
      try {
        await _getAudioCtx();
      } catch (e) {}
      if (!CW.channels.length) await loadChannels();
      else if (CW.activeId) await selectChannel(CW.activeId);
      else await loadChannels();
      refreshBadge();
    } else {
      panel.classList.add('cw-hidden');
      if (CW.pollTimer) {
        clearInterval(CW.pollTimer);
        CW.pollTimer = null;
      }
      const picker = document.getElementById('cw-dm-picker');
      if (picker) picker.classList.add('cw-hidden');
    }
  }

  function _getAudioCtx() {
    if (!CW._audioCtx) CW._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (CW._audioCtx.state === 'suspended') return CW._audioCtx.resume();
    return Promise.resolve();
  }

  CW.syncUser = function () {
    const wasPortal = CW.isPortal;
    syncFromWindow();
    if (!CW.uid) return;
    if (!CW._inited) {
      CW.init();
      return;
    }
    if (wasPortal !== CW.isPortal) {
      CW.destroy();
      CW.init();
      return;
    }
    refreshBadge();
  };

  CW.init = async function () {
    if (!window.__MYSIFA_APP__) window.__MYSIFA_APP__ = 'unknown';
    syncFromWindow();
    if (!CW.uid) {
      const ok = await fetchMe();
      if (!ok) return false;
    }
    const hasTrigger = CW.isPortal
      ? document.getElementById('cw-bar')
      : document.getElementById('cw-bubble');
    if (CW._inited && hasTrigger && document.getElementById('cw-panel')) return true;
    CW._inited = true;

    injectStyles();
    buildDom();
    refreshBadge();
    if (CW.badgeTimer) clearInterval(CW.badgeTimer);
    CW.badgeTimer = setInterval(refreshBadge, 30000);
    return true;
  };

  CW.ensureReady = async function () {
    syncFromWindow();
    if (!CW.uid) await fetchMe();
    if (!CW.uid) return false;
    return CW.init();
  };

  CW.destroy = function () {
    if (CW.pollTimer) clearInterval(CW.pollTimer);
    if (CW.badgeTimer) clearInterval(CW.badgeTimer);
    ['cw-bar', 'cw-bubble', 'cw-panel', 'cw-styles'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });
    CW._inited = false;
    CW.open = false;
  };

  function boot() {
    const run = () => CW.ensureReady();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', run);
    } else {
      run();
    }
    window.addEventListener('load', run);
    setTimeout(run, 1200);
  }

  boot();
  window._CW = CW;
})();
