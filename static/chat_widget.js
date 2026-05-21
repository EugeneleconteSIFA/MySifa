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
  const ICO_PLUS =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  const ICO_SETTINGS =
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';

  const ADMIN_ROLES = new Set(['superadmin', 'direction', 'administration']);
  const ROLE_LABELS = {
    direction: 'Direction',
    administration: 'Administration',
    fabrication: 'Fabrication',
    logistique: 'Logistique',
    comptabilite: 'Comptabilité',
    expedition: 'Expédition',
    commercial: 'Commercial',
    superadmin: 'Super admin',
  };

  const CW_STYLES = `
@keyframes cwPulse{0%,100%{opacity:1}50%{opacity:.3}}
#cw-bar{position:fixed;bottom:24px;left:24px;z-index:8002;width:340px;max-width:calc(100vw - 48px);
  background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 16px;
  display:flex;align-items:center;gap:12px;cursor:pointer;transition:border-color .15s,box-shadow .18s,transform .18s;
  font-family:inherit;box-shadow:0 4px 16px rgba(0,0,0,.2)}
#cw-bar:hover{border-color:var(--accent);box-shadow:0 6px 20px rgba(0,0,0,.28)}
#cw-bar.cw-portal-accent{background:var(--accent);border:none;
  box-shadow:0 4px 16px rgba(34,211,238,0.35)}
#cw-bar.cw-portal-accent:hover{box-shadow:0 6px 24px rgba(34,211,238,0.5);transform:scale(1.01)}
#cw-bar.cw-portal-accent.cw-bar-active{box-shadow:0 6px 24px rgba(34,211,238,0.5)}
#cw-bar.cw-portal-accent #cw-bar-icon{background:rgba(10,14,23,.18);color:var(--bg)}
#cw-bar.cw-portal-accent #cw-bar-icon svg{color:var(--bg)}
body.light #cw-bar.cw-portal-accent #cw-bar-icon{background:rgba(255,255,255,.22)}
#cw-bar.cw-portal-accent #cw-bar-title,#cw-bar.cw-portal-accent #cw-bar-preview{color:var(--bg)}
#cw-bar.cw-portal-accent #cw-bar-preview{opacity:.88}
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
  width:48px;height:48px;border-radius:50%;background:var(--accent);border:none;
  display:flex;align-items:center;justify-content:center;cursor:pointer;
  transition:transform .18s,box-shadow .18s;color:var(--bg);
  box-shadow:0 4px 16px rgba(34,211,238,0.35)}
#cw-bubble:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(34,211,238,0.5)}
#cw-bubble svg{color:var(--bg)}
#cw-bubble-badge{position:absolute;top:-4px;right:-4px}
#cw-panel{position:fixed;z-index:8003;width:440px;height:580px;max-height:calc(100vh - 64px);
  background:var(--card);border:1px solid var(--border);border-radius:14px;display:flex;overflow:hidden;
  font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;
  box-shadow:0 12px 48px rgba(0,0,0,0.5)}
#cw-panel.cw-hidden{display:none!important}
#cw-panel.cw-mode-bar{left:max(24px,env(safe-area-inset-left,0px));bottom:110px}
#cw-panel.cw-mode-bubble{bottom:auto;right:auto}
#cw-panel-left{width:168px;flex-shrink:0;border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow-y:auto;min-height:0}
.cw-section-row{display:flex;align-items:center;justify-content:space-between;padding:12px 12px 6px;gap:6px}
.cw-section-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;flex:1;min-width:0}
.cw-section-add{width:26px;height:26px;border-radius:8px;border:1px solid var(--border);background:transparent;
  color:var(--accent);cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0}
.cw-section-add:hover{background:var(--accent-bg);border-color:var(--accent)}
.cw-section-add.cw-hidden{display:none}
.cw-channel-item{padding:9px 12px;font-size:13px;color:var(--text2);display:flex;align-items:center;
  gap:6px;cursor:pointer;transition:background .1s;border:none;background:transparent;width:100%;
  text-align:left;font-family:inherit}
.cw-channel-item:hover{background:rgba(255,255,255,.04)}
body.light .cw-channel-item:hover{background:rgba(0,0,0,.04)}
.cw-channel-item.cw-active{background:var(--accent-bg);color:var(--accent);font-weight:600}
.cw-unread-badge{margin-left:auto;background:var(--accent);color:#0a0e17;font-size:10px;font-weight:700;
  padding:2px 6px;border-radius:99px;flex-shrink:0}
.cw-chan-label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
#cw-panel-right{flex:1;display:flex;flex-direction:column;min-width:0;position:relative}
#cw-panel-header{padding:12px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;
  font-size:14px;font-weight:600;color:var(--text);gap:8px;min-height:48px}
#cw-panel-title{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cw-header-btn{background:none;border:1px solid var(--border);border-radius:8px;color:var(--muted);
  cursor:pointer;display:flex;align-items:center;justify-content:center;width:32px;height:32px;padding:0;flex-shrink:0}
.cw-header-btn:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.cw-header-btn.cw-hidden{display:none}
#cw-close{background:none;border:none;color:var(--muted);font-size:20px;
  cursor:pointer;line-height:1;padding:0 4px;font-family:inherit;flex-shrink:0}
#cw-close:hover{color:var(--text)}
#cw-messages{flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px;min-height:0}
.cw-msg-mine{align-self:flex-end;background:var(--accent-bg);border:1px solid rgba(34,211,238,.2);
  border-radius:10px 0 10px 10px;padding:8px 12px;font-size:13px;color:var(--text);max-width:82%;word-break:break-word}
.cw-msg-theirs{align-self:flex-start;background:rgba(255,255,255,.05);border:1px solid var(--border);
  border-radius:0 10px 10px 10px;padding:8px 12px;font-size:13px;color:var(--text);max-width:82%;word-break:break-word}
body.light .cw-msg-theirs{background:rgba(0,0,0,.04)}
.cw-msg-meta{font-size:11px;color:var(--muted);margin-bottom:3px}
#cw-input-row{padding:10px 12px;border-top:1px solid var(--border);display:flex;gap:8px;align-items:center}
#cw-input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 12px;
  font-size:13px;line-height:1.3;color:var(--text);resize:none;font-family:inherit;
  height:38px;min-height:38px;max-height:96px;box-sizing:border-box;overflow-y:auto;outline:none}
#cw-input:focus{border-color:var(--accent)}
#cw-send{width:38px;height:38px;box-sizing:border-box;background:var(--accent-bg);
  border:1px solid rgba(34,211,238,.3);border-radius:10px;padding:0;
  cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--accent);flex-shrink:0}
#cw-send:hover{filter:brightness(1.05)}
#cw-send:disabled{opacity:.5;cursor:not-allowed}
#cw-dm-picker{position:absolute;inset:0;background:var(--card);z-index:2;display:flex;flex-direction:column}
#cw-dm-picker.cw-hidden{display:none}
#cw-dm-search{margin:12px;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;
  color:var(--text);font-size:13px;font-family:inherit}
#cw-dm-list{flex:1;overflow-y:auto}
.cw-dm-row{display:block;width:100%;text-align:left;padding:12px 14px;border:none;border-bottom:1px solid var(--border);
  background:transparent;color:var(--text);font-size:13px;cursor:pointer;font-family:inherit}
.cw-dm-row:hover{background:var(--accent-bg);color:var(--accent)}
#cw-empty-hint{flex:1;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;padding:16px;text-align:center}
#cw-overlay{position:absolute;inset:0;background:var(--card);z-index:3;display:flex;flex-direction:column;overflow:hidden}
#cw-overlay.cw-hidden{display:none}
.cw-overlay-head{padding:12px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
.cw-overlay-head h3{margin:0;font-size:14px;font-weight:700;color:var(--text);flex:1}
.cw-overlay-back{background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;padding:0 4px}
.cw-overlay-back:hover{color:var(--text)}
.cw-overlay-body{flex:1;overflow-y:auto;padding:12px 14px}
.cw-overlay-body label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin:10px 0 6px}
.cw-overlay-body label:first-child{margin-top:0}
.cw-overlay-body input,.cw-overlay-body textarea{width:100%;box-sizing:border-box;background:var(--bg);
  border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit}
.cw-overlay-body textarea{resize:vertical;min-height:56px}
.cw-member-row{padding:10px 0;border-bottom:1px solid var(--border);font-size:13px;color:var(--text)}
.cw-member-row:last-child{border-bottom:none}
.cw-member-role{font-size:11px;color:var(--muted);margin-top:2px}
.cw-member-chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.cw-member-chip{display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:8px;
  background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:600}
.cw-member-chip button{background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px;padding:0 2px}
.cw-user-pick{max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:10px}
.cw-user-pick .cw-dm-row:last-child{border-bottom:none}
.cw-overlay-actions{padding:10px 14px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end}
.cw-btn-ghost,.cw-btn-primary{padding:9px 16px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.cw-btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.cw-btn-primary{background:var(--accent);border:none;color:#0a0e17}
.cw-btn-primary:disabled{opacity:.5;cursor:not-allowed}
.cw-overlay-err{font-size:12px;color:var(--danger);margin-top:8px}
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
      bar.className = 'cw-portal-accent';
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
      '<div class="cw-section-row"><span class="cw-section-label">Canaux</span>' +
      '<button type="button" class="cw-section-add cw-hidden" id="cw-add-channel" title="Nouveau canal" aria-label="Nouveau canal">' +
      ICO_PLUS +
      '</button></div><div id="cw-channels"></div>' +
      '<div class="cw-section-row"><span class="cw-section-label">Discussion</span>' +
      '<button type="button" class="cw-section-add" id="cw-add-dm" title="Nouvelle discussion" aria-label="Nouvelle discussion">' +
      ICO_PLUS +
      '</button></div><div id="cw-dms"></div></div>' +
      '<div id="cw-panel-right">' +
      '<div id="cw-overlay" class="cw-hidden"></div>' +
      '<div id="cw-dm-picker" class="cw-hidden">' +
      '<input type="search" id="cw-dm-search" placeholder="Rechercher un collègue…" autocomplete="off">' +
      '<div id="cw-dm-list"></div></div>' +
      '<div id="cw-panel-header"><span id="cw-panel-title">Messagerie</span>' +
      '<button type="button" class="cw-header-btn cw-hidden" id="cw-channel-info" title="Membres du canal" aria-label="Membres du canal">' +
      ICO_SETTINGS +
      '</button>' +
      '<button type="button" id="cw-close" aria-label="Fermer">×</button></div>' +
      '<div id="cw-messages"><div id="cw-empty-hint">Sélectionnez un canal</div></div>' +
      '<div id="cw-input-row"><textarea id="cw-input" rows="1" placeholder="Message…"></textarea>' +
      '<button type="button" id="cw-send" aria-label="Envoyer">' +
      ICO_SEND +
      '</button></div></div>';
    document.body.appendChild(panel);

    document.getElementById('cw-close').addEventListener('click', () => togglePanel(false));
    document.getElementById('cw-send').addEventListener('click', () => sendMessage());
    document.getElementById('cw-add-dm').addEventListener('click', () => openNewDm());
    document.getElementById('cw-add-channel').addEventListener('click', () => openNewChannel());
    document.getElementById('cw-channel-info').addEventListener('click', () => openChannelMembers());
    syncAdminButtons();
    const inp = document.getElementById('cw-input');
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    inp.addEventListener('input', function () {
      resizeCwInput(this);
    });
    dockLayout();
  }

  const CW_INPUT_MIN_H = 38;

  function resizeCwInput(el) {
    if (!el) return;
    el.style.height = CW_INPUT_MIN_H + 'px';
    if (!el.value) return;
    el.style.height = 'auto';
    el.style.height = Math.min(Math.max(CW_INPUT_MIN_H, el.scrollHeight), 96) + 'px';
  }

  function dockLayout() {
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  /** Panneau portail : au-dessus de la barre Messagerie avec un léger décalage. */
  function positionPortalPanel() {
    if (!CW.isPortal) return;
    const bar = document.getElementById('cw-bar');
    const panel = document.getElementById('cw-panel');
    if (!bar || !panel || panel.classList.contains('cw-hidden')) return;
    const gap = 14;
    const barTop = bar.getBoundingClientRect().top;
    panel.style.bottom = window.innerHeight - barTop + gap + 'px';
    panel.style.left = getComputedStyle(bar).left;
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
    if (!chans.length) chEl.innerHTML = '<p style="padding:8px 12px;font-size:12px;color:var(--muted);margin:0">—</p>';
    if (!dms.length) dmEl.innerHTML = '<p style="padding:8px 12px;font-size:12px;color:var(--muted);margin:0">—</p>';
  }

  function syncAdminButtons() {
    const btn = document.getElementById('cw-add-channel');
    if (!btn) return;
    btn.classList.toggle('cw-hidden', !ADMIN_ROLES.has(CW.role));
  }

  function updateChannelHeader() {
    const ch = CW.channels.find((c) => c.id === CW.activeId);
    const title = document.getElementById('cw-panel-title');
    const infoBtn = document.getElementById('cw-channel-info');
    if (title) title.textContent = ch ? ch.display_name || ch.name || 'Canal' : 'Messagerie';
    if (infoBtn) {
      const show = !!(ch && ch.type === 'channel');
      infoBtn.classList.toggle('cw-hidden', !show);
    }
  }

  function closeOverlay() {
    const ov = document.getElementById('cw-overlay');
    if (ov) {
      ov.classList.add('cw-hidden');
      ov.innerHTML = '';
    }
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
    closeOverlay();
    updateChannelHeader();

    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');

    const box = document.getElementById('cw-messages');
    if (!box) return;
    box.innerHTML = '<p style="text-align:center;color:var(--muted);font-size:13px;padding:12px">Chargement…</p>';

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
        resizeCwInput(inp);
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

  async function openChannelMembers() {
    if (!CW.activeId) return;
    const ch = CW.channels.find((c) => c.id === CW.activeId);
    if (!ch || ch.type !== 'channel') return;
    closeOverlay();
    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');
    const ov = document.getElementById('cw-overlay');
    if (!ov) return;
    ov.classList.remove('cw-hidden');
    ov.innerHTML =
      '<div class="cw-overlay-head"><button type="button" class="cw-overlay-back" id="cw-ov-back" aria-label="Retour">×</button>' +
      '<h3>Membres — ' +
      escCW(ch.display_name || ch.name || 'Canal') +
      '</h3></div>' +
      '<div class="cw-overlay-body" id="cw-ov-body"><p style="color:var(--muted);font-size:13px;margin:0">Chargement…</p></div>';
    document.getElementById('cw-ov-back').addEventListener('click', closeOverlay);
    try {
      const members = (await api('/api/chat/channels/' + CW.activeId + '/members')) || [];
      const body = document.getElementById('cw-ov-body');
      if (!body) return;
      if (!members.length) {
        body.innerHTML = '<p style="color:var(--muted);font-size:13px;margin:0">Aucun membre.</p>';
        return;
      }
      body.innerHTML = members
        .map((m) => {
          const rl = ROLE_LABELS[m.role] || m.role || '';
          return (
            '<div class="cw-member-row"><div>' +
            escCW(m.nom || 'Utilisateur') +
            '</div><div class="cw-member-role">' +
            escCW(rl) +
            '</div></div>'
          );
        })
        .join('');
    } catch (e) {
      const body = document.getElementById('cw-ov-body');
      if (body) body.innerHTML = '<p class="cw-overlay-err">Chargement impossible.</p>';
    }
  }

  async function openNewChannel() {
    if (!ADMIN_ROLES.has(CW.role)) return;
    closeOverlay();
    const picker = document.getElementById('cw-dm-picker');
    if (picker) picker.classList.add('cw-hidden');
    let users = [];
    try {
      users = (await api('/api/chat/users')) || [];
    } catch (e) {
      return;
    }
    const ov = document.getElementById('cw-overlay');
    if (!ov) return;
    let picked = [];
    ov.classList.remove('cw-hidden');
    ov.innerHTML =
      '<div class="cw-overlay-head"><button type="button" class="cw-overlay-back" id="cw-ov-back" aria-label="Retour">×</button>' +
      '<h3>Nouveau canal</h3></div>' +
      '<div class="cw-overlay-body">' +
      '<label for="cw-ch-name">Nom</label><input type="text" id="cw-ch-name" maxlength="60" placeholder="ex. commercial">' +
      '<label for="cw-ch-desc">Description</label><textarea id="cw-ch-desc" rows="2" placeholder="Optionnel"></textarea>' +
      '<label for="cw-ch-member-search">Membres</label>' +
      '<div class="cw-member-chips" id="cw-ch-chips"></div>' +
      '<input type="search" id="cw-ch-member-search" placeholder="Ajouter un collègue…">' +
      '<div class="cw-user-pick" id="cw-ch-user-pick"></div>' +
      '<p class="cw-overlay-err cw-hidden" id="cw-ch-err"></p></div>' +
      '<div class="cw-overlay-actions">' +
      '<button type="button" class="cw-btn-ghost" id="cw-ch-cancel">Annuler</button>' +
      '<button type="button" class="cw-btn-primary" id="cw-ch-create">Créer</button></div>';
    document.getElementById('cw-ov-back').addEventListener('click', closeOverlay);
    document.getElementById('cw-ch-cancel').addEventListener('click', closeOverlay);

    function renderChips() {
      const el = document.getElementById('cw-ch-chips');
      if (!el) return;
      el.innerHTML = picked
        .map(
          (m) =>
            '<span class="cw-member-chip">' +
            escCW(m.nom) +
            '<button type="button" data-id="' +
            m.id +
            '" title="Retirer">×</button></span>'
        )
        .join('');
      el.querySelectorAll('.cw-member-chip button').forEach((b) => {
        b.addEventListener('click', () => {
          const mid = parseInt(b.getAttribute('data-id'), 10);
          picked = picked.filter((x) => x.id !== mid);
          renderChips();
          renderPick(document.getElementById('cw-ch-member-search').value);
        });
      });
    }

    function renderPick(q) {
      const el = document.getElementById('cw-ch-user-pick');
      if (!el) return;
      const ql = (q || '').toLowerCase();
      const pickedIds = new Set(picked.map((m) => m.id));
      const list = users.filter(
        (u) => u.id !== CW.uid && !pickedIds.has(u.id) && (!ql || (u.nom || '').toLowerCase().includes(ql))
      );
      if (!list.length) {
        el.innerHTML = '<p style="padding:10px;margin:0;font-size:12px;color:var(--muted)">—</p>';
        return;
      }
      el.innerHTML = '';
      list.forEach((u) => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = 'cw-dm-row';
        row.textContent = u.nom || 'Utilisateur';
        row.addEventListener('click', () => {
          picked.push({ id: u.id, nom: u.nom || 'Utilisateur' });
          renderChips();
          renderPick(document.getElementById('cw-ch-member-search').value);
        });
        el.appendChild(row);
      });
    }

    renderChips();
    renderPick('');
    const search = document.getElementById('cw-ch-member-search');
    if (search) search.oninput = () => renderPick(search.value);

    document.getElementById('cw-ch-create').addEventListener('click', async () => {
      const errEl = document.getElementById('cw-ch-err');
      const name = (document.getElementById('cw-ch-name').value || '').trim();
      if (!name) {
        if (errEl) {
          errEl.textContent = 'Nom requis.';
          errEl.classList.remove('cw-hidden');
        }
        return;
      }
      const description = (document.getElementById('cw-ch-desc').value || '').trim();
      const btn = document.getElementById('cw-ch-create');
      if (btn) btn.disabled = true;
      try {
        const r = await api('/api/chat/channels', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'channel',
            name,
            description,
            member_ids: picked.map((m) => m.id),
          }),
        });
        closeOverlay();
        await loadChannels();
        await selectChannel(r.id);
      } catch (e) {
        if (errEl) {
          errEl.textContent = e.message || 'Création impossible.';
          errEl.classList.remove('cw-hidden');
        }
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    requestAnimationFrame(() => document.getElementById('cw-ch-name')?.focus());
  }

  async function openNewDm() {
    closeOverlay();
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
    const bar = document.getElementById('cw-bar');
    if (CW.open) {
      panel.classList.remove('cw-hidden');
      if (bar) bar.classList.add('cw-bar-active');
      try {
        await _getAudioCtx();
      } catch (e) {}
      if (!CW.channels.length) await loadChannels();
      else if (CW.activeId) await selectChannel(CW.activeId);
      else await loadChannels();
      refreshBadge();
      if (CW.isPortal) {
        requestAnimationFrame(() => {
          positionPortalPanel();
          requestAnimationFrame(positionPortalPanel);
        });
      }
    } else {
      panel.classList.add('cw-hidden');
      if (bar) bar.classList.remove('cw-bar-active');
      if (CW.pollTimer) {
        clearInterval(CW.pollTimer);
        CW.pollTimer = null;
      }
      const picker = document.getElementById('cw-dm-picker');
      if (picker) picker.classList.add('cw-hidden');
      closeOverlay();
    }
    dockLayout();
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
    syncAdminButtons();
    refreshBadge();
    dockLayout();
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
    syncAdminButtons();
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
    dockLayout();
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

  window.addEventListener('resize', () => {
    if (CW.open && CW.isPortal) positionPortalPanel();
  });

  boot();
  window._CW = CW;
})();
