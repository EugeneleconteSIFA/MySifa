/**
 * MySifa — Widget Assistant IA (flottant).
 * Requiert : window.__MYSIFA_APP__, window.__MYSIFA_USER__ { nom, role }
 */
(function () {
  'use strict';

  var bound = false;
  var greeted = false;
  var open = false;
  var loading = false;
  var history = [];
  var AI_ROLES = ['superadmin', 'direction', 'administration'];

  var ICO_AI =
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' +
    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>';
  var ICO_CLOSE =
    '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">' +
    '<line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>';
  var ICO_SEND =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M22 2L11 13"/><path d="M22 2L15 22l-4-9-9-4 20-7z"/></svg>';

  function ensureDom() {
    if (document.getElementById('ai-chat-root')) return;
    var root = document.createElement('div');
    root.id = 'ai-chat-root';
    root.innerHTML =
      '<button id="ai-chat-btn" type="button" aria-label="Assistant IA" title="Assistant MySifa">' +
      ICO_AI +
      '</button>' +
      '<div id="ai-chat-panel" role="dialog" aria-label="Assistant MySifa">' +
      '<div id="ai-chat-header">' +
      '<span class="ai-dot"></span>' +
      '<div class="ai-title">Assistant MySifa<span class="ai-sub">Posez vos questions sur la production, le stock…</span></div>' +
      '<button id="ai-chat-close" type="button" aria-label="Fermer">' +
      ICO_CLOSE +
      '</button></div>' +
      '<div id="ai-messages"></div>' +
      '<div id="ai-typing"><span class="ai-dot-t"></span><span class="ai-dot-t"></span><span class="ai-dot-t"></span></div>' +
      '<div id="ai-input-area">' +
      '<textarea id="ai-input" placeholder="Votre question…" rows="1" aria-label="Message"></textarea>' +
      '<button id="ai-send" type="button" aria-label="Envoyer">' +
      ICO_SEND +
      '</button></div></div>';
    document.body.appendChild(root);
  }

  window.initAiChatWidget = function () {
    ensureDom();
    var user = window.__MYSIFA_USER__ || {};
    var app = window.__MYSIFA_APP__;
    var root = document.getElementById('ai-chat-root');
    if (!root) return;

    var show = AI_ROLES.indexOf(user.role) >= 0 && app && app !== 'login';
    root.classList.toggle('ai-on-portal', app === 'portal');
    root.style.display = show ? 'block' : 'none';
    if (!show) {
      open = false;
      var panelHide = document.getElementById('ai-chat-panel');
      if (panelHide) panelHide.classList.remove('open');
      if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
        window.MySifaDock.layout();
      }
      return;
    }

    var btn = document.getElementById('ai-chat-btn');
    var panel = document.getElementById('ai-chat-panel');
    var closeBtn = document.getElementById('ai-chat-close');
    var msgs = document.getElementById('ai-messages');
    var input = document.getElementById('ai-input');
    var send = document.getElementById('ai-send');
    var typing = document.getElementById('ai-typing');
    if (!btn || !panel || !closeBtn || !msgs || !input || !send || !typing) return;

    if (!bound) {
      bound = true;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        toggle();
      });
      closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        toggle();
      });
      document.addEventListener('click', onDocClick);
      input.addEventListener('keydown', onKey);
      input.addEventListener('input', onInput);
      send.addEventListener('click', handleSend);
    }

    if (!greeted) {
      greeted = true;
      var greetingsByApp = {
        stock: 'Stock, emplacements, mouvements — posez vos questions.',
        fabrication: 'Production du jour, état des machines — posez vos questions.',
        prod: 'Production du jour, état des machines — posez vos questions.',
        planning: 'Planning, dossiers en cours — posez vos questions.',
      };
      var greetingsByRole = {
        fabrication: 'Production du jour, état des machines — posez vos questions.',
        logistique: 'Stock, emplacements, expéditions à venir — posez vos questions.',
        direction: 'KPIs, synthèse production, planning, stock — posez vos questions.',
        administration: 'Congés, paie, expéditions — posez vos questions.',
      };
      var greeting =
        greetingsByApp[app] ||
        greetingsByRole[user.role] ||
        'Posez vos questions sur MySifa.';
      addBot(greeting, null);
    }

    function toggle() {
      open = !open;
      panel.classList.toggle('open', open);
      btn.classList.toggle('mysifa-dock-fab-active', open);
      if (open) setTimeout(function () { input.focus(); }, 200);
      if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
        window.MySifaDock.layout();
      }
    }
    function onDocClick(e) {
      if (!open) return;
      if (panel.contains(e.target) || btn.contains(e.target)) return;
      open = false;
      panel.classList.remove('open');
    }
    function onKey(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    }
    function onInput() {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 80) + 'px';
    }
    function fmt(t) {
      return String(t || '')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    }
    function scrollEnd() {
      setTimeout(function () {
        msgs.scrollTop = msgs.scrollHeight;
      }, 30);
    }
    function parseConfirmAction(text) {
      var raw = String(text || '');
      var m = raw.match(/\[CONFIRM_ACTION:(\{[\s\S]*\})\]/);
      if (!m) return { clean: raw, payload: null };
      try {
        return { clean: raw.replace(m[0], '').trim(), payload: JSON.parse(m[1]) };
      } catch (e) {
        return { clean: raw, payload: null };
      }
    }
    function sendConfirm() {
      input.value = 'oui, confirme';
      handleSend();
    }
    function addBot(text, status) {
      var parsed = parseConfirmAction(text);
      var w = document.createElement('div');
      w.className = 'ai-msg bot';
      w.innerHTML =
        '<div class="ai-label">MySifa</div><div class="ai-bubble">' + fmt(parsed.clean) + '</div>';
      if (parsed.payload) {
        if (typeof window.S !== 'undefined') window.S.pendingAction = parsed.payload;
        var actions = document.createElement('div');
        actions.className = 'ai-confirm-actions';
        var btnOk = document.createElement('button');
        btnOk.type = 'button';
        btnOk.className = 'ai-confirm-btn primary';
        btnOk.textContent = 'Confirmer';
        btnOk.addEventListener('click', function () {
          if (typeof window.S !== 'undefined') window.S.pendingAction = parsed.payload;
          sendConfirm();
        });
        var btnNo = document.createElement('button');
        btnNo.type = 'button';
        btnNo.className = 'ai-confirm-btn';
        btnNo.textContent = 'Annuler';
        btnNo.addEventListener('click', function () {
          if (typeof window.S !== 'undefined') window.S.pendingAction = null;
          addBot('Action annulée.', 'info');
        });
        actions.appendChild(btnOk);
        actions.appendChild(btnNo);
        w.appendChild(actions);
      }
      if (status) {
        var s = document.createElement('span');
        s.className = 'ai-status ' + status;
        s.textContent =
          status === 'ok' ? 'Action effectuée' : status === 'err' ? 'Erreur' : 'Info';
        w.appendChild(s);
      }
      msgs.appendChild(w);
      scrollEnd();
    }
    function addUser(text) {
      var w = document.createElement('div');
      w.className = 'ai-msg user';
      w.innerHTML =
        '<div class="ai-label">Vous</div><div class="ai-bubble">' +
        String(text).replace(/</g, '&lt;') +
        '</div>';
      msgs.appendChild(w);
      scrollEnd();
    }
    function setLoading(v) {
      loading = v;
      send.disabled = v;
      input.disabled = v;
      typing.classList.toggle('visible', v);
      if (v) scrollEnd();
    }
    async function handleSend() {
      var text = input.value.trim();
      if (!text || loading) return;
      addUser(text);
      history.push({ role: 'user', content: text });
      input.value = '';
      input.style.height = 'auto';
      setLoading(true);
      try {
        var res = await fetch('/api/ai/chat', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: history, module: app || null }),
        });
        var data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) {
          var detail = data.detail;
          var msg =
            typeof detail === 'string'
              ? detail
              : Array.isArray(detail)
                ? detail
                    .map(function (d) {
                      return d.msg || d;
                    })
                    .join(', ')
                : 'HTTP ' + res.status;
          throw new Error(msg);
        }
        addBot(data.reply || 'OK.', data.status || null);
        history.push({ role: 'assistant', content: data.reply || '' });
      } catch (err) {
        addBot('Erreur de connexion. Réessayez dans un instant.', 'err');
      } finally {
        setLoading(false);
      }
    }

    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  };
})();
