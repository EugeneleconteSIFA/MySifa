/**
 * MySifa — Disposition flexible des widgets flottants (calculette, messagerie, IA).
 * Recalcule les positions selon les widgets réellement visibles.
 */
(function () {
  'use strict';

  const GAP = 12;
  const FAB_SIZE = 48;
  const MOBILE_BP = '(max-width: 900px)';
  const MOBILE_LANDSCAPE_BP = '(max-width: 900px) and (orientation: landscape)';
  const SHADOW_FAB = '0 4px 16px rgba(34,211,238,0.35)';
  const SHADOW_PANEL = '0 12px 48px rgba(0,0,0,0.5)';

  function isMobile() {
    return window.matchMedia(MOBILE_BP).matches;
  }

  function isMobileLandscape() {
    return window.matchMedia(MOBILE_LANDSCAPE_BP).matches;
  }

  function syncDockBodyClass() {
    document.body.classList.toggle('mysifa-dock-mobile', isMobile());
    document.body.classList.toggle('mysifa-dock-landscape', isMobileLandscape());
  }

  function safeRight(extraPx) {
    const x = extraPx || 0;
    return x
      ? 'calc(max(24px, env(safe-area-inset-right, 0px)) + ' + x + 'px)'
      : 'max(24px, env(safe-area-inset-right, 0px))';
  }

  function safeBottom(extraPx) {
    const x = extraPx || 0;
    return x
      ? 'calc(max(24px, env(safe-area-inset-bottom, 0px)) + ' + x + 'px)'
      : 'max(24px, env(safe-area-inset-bottom, 0px))';
  }

  function isVisible(el) {
    if (!el) return false;
    if (el.id === 'ai-chat-root') return el.style.display !== 'none';
    return getComputedStyle(el).display !== 'none';
  }

  function isDockFab(el) {
    if (!el) return false;
    return isVisible(el);
  }

  function applyFab(el, right, bottom) {
    if (!el) return;
    el.style.right = right;
    el.style.bottom = bottom;
    el.style.left = 'auto';
  }

  function layoutChatFab(el, chatCol, stackH) {
    if (!el) return;
    applyFab(el, safeRight(chatCol), safeBottom(stackH));
    el.style.boxShadow = SHADOW_FAB;
  }

  function layoutMobileLandscape(calcFab, calcPanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel) {
    const aiRoot = document.getElementById('ai-chat-root');
    const fabRowH = FAB_SIZE + 14;
    let stackRight = 0;

    function placeFabRow(el) {
      if (!el) return;
      applyFab(el, safeRight(stackRight), safeBottom(0));
      el.style.zIndex = '8002';
      el.style.boxShadow = SHADOW_FAB;
      stackRight += FAB_SIZE + GAP;
    }

    const hasCalc = isDockFab(calcFab);
    const hasAi = isVisible(aiRoot) && isDockFab(aiBtn);
    const chatFab =
      isDockFab(chatBubble) ? chatBubble : isDockFab(chatBar) ? chatBar : null;

    if (hasCalc) {
      placeFabRow(calcFab);
      if (calcPanel && getComputedStyle(calcPanel).display !== 'none') {
        calcPanel.style.right = safeRight(0);
        calcPanel.style.bottom = safeBottom(fabRowH);
        calcPanel.style.zIndex = '8014';
        calcPanel.style.boxShadow = SHADOW_PANEL;
      }
    }
    if (chatFab) placeFabRow(chatFab);
    if (hasAi) placeFabRow(aiBtn);

    const panelBottom = fabRowH;
    const panelMaxH = 'calc(100dvh - ' + (fabRowH + 12) + 'px)';

    function layoutLandscapePanel(el, z) {
      if (!el) return;
      el.style.top = 'max(8px, env(safe-area-inset-top, 0px))';
      el.style.left = 'max(12px, env(safe-area-inset-left, 0px))';
      el.style.right = 'max(12px, env(safe-area-inset-right, 0px))';
      el.style.width = 'auto';
      el.style.maxWidth = 'none';
      el.style.marginLeft = '0';
      el.style.marginRight = '0';
      el.style.bottom = safeBottom(panelBottom);
      el.style.height = panelMaxH;
      el.style.maxHeight = panelMaxH;
      el.style.minHeight = '0';
      el.style.borderRadius = '12px';
      el.style.boxShadow = SHADOW_PANEL;
      el.style.zIndex = String(z);
    }

    if (chatPanel && !chatPanel.classList.contains('cw-hidden')) {
      layoutLandscapePanel(chatPanel, 8015);
    }

    if (hasAi && aiPanel) {
      if (aiPanel.classList.contains('open')) {
        layoutLandscapePanel(aiPanel, 8016);
      } else {
        aiPanel.style.top = '';
        aiPanel.style.left = '';
        aiPanel.style.right = safeRight(0);
        aiPanel.style.bottom = safeBottom(0);
        aiPanel.style.width = '';
        aiPanel.style.maxWidth = '';
        aiPanel.style.height = '';
        aiPanel.style.maxHeight = '';
        aiPanel.style.minHeight = '';
        aiPanel.style.zIndex = '8002';
        aiPanel.style.boxShadow = '';
      }
    }
  }

  function layoutMobile(calcFab, calcPanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel) {
    const aiRoot = document.getElementById('ai-chat-root');
    let stackBottom = 0;

    function placeFab(el) {
      if (!el) return;
      applyFab(el, safeRight(0), safeBottom(stackBottom));
      el.style.zIndex = '8002';
      el.style.boxShadow = SHADOW_FAB;
      stackBottom += FAB_SIZE + GAP;
    }

    const hasCalc = isDockFab(calcFab);
    const hasAi = isVisible(aiRoot) && isDockFab(aiBtn);
    const chatFab =
      isDockFab(chatBubble) ? chatBubble : isDockFab(chatBar) ? chatBar : null;

    if (hasCalc) {
      placeFab(calcFab);
      if (calcPanel && getComputedStyle(calcPanel).display !== 'none') {
        calcPanel.style.right = safeRight(0);
        calcPanel.style.bottom = safeBottom(FAB_SIZE + 14);
        calcPanel.style.zIndex = '8014';
        calcPanel.style.boxShadow = SHADOW_PANEL;
      }
    }
    if (chatFab) placeFab(chatFab);
    if (hasAi) placeFab(aiBtn);

    const fabStackH = stackBottom;
    const panelBottom = fabStackH + 12;
    const panelMaxH = 'calc(100dvh - ' + (fabStackH + 20) + 'px)';
    const panelMinH = 'min(560px, ' + panelMaxH + ')';

    function layoutFloaterPanel(el, z) {
      if (!el) return;
      el.style.top = 'auto';
      el.style.left = 'max(12px, env(safe-area-inset-left, 0px))';
      el.style.right = 'max(12px, env(safe-area-inset-right, 0px))';
      el.style.width = 'auto';
      el.style.maxWidth = 'min(420px, calc(100vw - 24px))';
      el.style.marginLeft = 'auto';
      el.style.marginRight = 'auto';
      el.style.bottom = safeBottom(panelBottom);
      el.style.height = panelMinH;
      el.style.maxHeight = panelMaxH;
      el.style.borderRadius = '14px';
      el.style.boxShadow = SHADOW_PANEL;
      el.style.zIndex = String(z);
    }

    if (chatPanel && !chatPanel.classList.contains('cw-hidden')) {
      layoutFloaterPanel(chatPanel, 8015);
    }

    if (hasAi && aiPanel) {
      if (aiPanel.classList.contains('open')) {
        layoutFloaterPanel(aiPanel, 8016);
      } else {
        aiPanel.style.left = '';
        aiPanel.style.right = safeRight(0);
        aiPanel.style.bottom = safeBottom(fabStackH);
        aiPanel.style.width = '';
        aiPanel.style.maxWidth = '';
        aiPanel.style.height = '';
        aiPanel.style.maxHeight = '';
        aiPanel.style.zIndex = '8002';
        aiPanel.style.boxShadow = '';
      }
    }
  }

  function layout() {
    const calcFab = document.getElementById('_calc_fab');
    const calcPanel = document.getElementById('_calc_panel');
    const aiRoot = document.getElementById('ai-chat-root');
    const aiBtn = document.getElementById('ai-chat-btn');
    const aiPanel = document.getElementById('ai-chat-panel');
    const chatBubble = document.getElementById('cw-bubble');
    const chatBar = document.getElementById('cw-bar');
    const chatPanel = document.getElementById('cw-panel');
    const mobile = isMobile();
    const landscape = isMobileLandscape();

    syncDockBodyClass();

    const hasCalc = isVisible(calcFab);
    const hasAi = isVisible(aiRoot) && isVisible(aiBtn);
    const hasChatBubble = isVisible(chatBubble);
    const hasChatBar = isVisible(chatBar);

    if (mobile) {
      if (landscape) {
        layoutMobileLandscape(calcFab, calcPanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      } else {
        layoutMobile(calcFab, calcPanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      }
      return;
    }

    if (hasChatBar) {
      chatBar.style.right = '';
      chatBar.style.bottom = '';
      chatBar.style.left = '';
      chatBar.style.boxShadow = '';
    }

    let offsetRight = 0;
    let bottomRowH = 0;

    if (hasCalc) {
      applyFab(calcFab, safeRight(0), safeBottom(0));
      if (calcFab) calcFab.style.boxShadow = SHADOW_FAB;
      offsetRight = FAB_SIZE + GAP;
      bottomRowH = FAB_SIZE;
      if (calcPanel) {
        calcPanel.style.right = safeRight(0);
        calcPanel.style.bottom = safeBottom(FAB_SIZE + 14);
        calcPanel.style.boxShadow = SHADOW_PANEL;
      }
    }

    if (hasAi) {
      applyFab(aiBtn, safeRight(offsetRight), safeBottom(0));
      if (!hasCalc) bottomRowH = FAB_SIZE;
      else bottomRowH = Math.max(bottomRowH, FAB_SIZE);
      const aiCol = offsetRight;
      offsetRight += FAB_SIZE + GAP;
      if (aiPanel) {
        const onPortal = aiRoot && aiRoot.classList.contains('ai-on-portal');
        aiPanel.style.right = safeRight(onPortal && !hasCalc ? 0 : aiCol);
        aiPanel.style.bottom = safeBottom(hasCalc ? 62 : 62);
        aiPanel.style.boxShadow = SHADOW_PANEL;
      }
    }

    function chatColumnOffset() {
      let chatCol = 0;
      if (hasCalc && hasAi) chatCol = FAB_SIZE + GAP;
      else if (hasCalc) chatCol = FAB_SIZE + GAP;
      else if (hasAi) chatCol = 0;
      return chatCol;
    }

    const stackH = bottomRowH > 0 ? bottomRowH + GAP : 0;
    const chatCol = chatColumnOffset();

    if (hasChatBubble) {
      layoutChatFab(chatBubble, chatCol, stackH);
    }

    if (chatPanel && !chatPanel.classList.contains('cw-hidden')) {
      if (chatPanel.classList.contains('cw-mode-bubble') && (hasChatBubble || hasChatBar)) {
        const stackPanel = stackH + FAB_SIZE + GAP;
        chatPanel.style.right = safeRight(chatCol);
        chatPanel.style.bottom = safeBottom(stackPanel);
        chatPanel.style.boxShadow = SHADOW_PANEL;
      }
    }
  }

  window.addEventListener('resize', layout);
  window.addEventListener('orientationchange', function () {
    setTimeout(layout, 80);
  });
  if (typeof window.matchMedia === 'function') {
    ['(max-width: 900px)', MOBILE_LANDSCAPE_BP, '(orientation: landscape)', '(orientation: portrait)'].forEach(
      function (q) {
        var mq = window.matchMedia(q);
        if (mq.addEventListener) mq.addEventListener('change', layout);
        else if (mq.addListener) mq.addListener(layout);
      }
    );
  }

  window.MySifaDock = {
    layout: layout,
    isMobileLandscape: isMobileLandscape,
    SHADOW_FAB: SHADOW_FAB,
    SHADOW_PANEL: SHADOW_PANEL,
  };
})();
