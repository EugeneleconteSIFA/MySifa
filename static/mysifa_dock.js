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
  const Z_FAB = 8002;
  const Z_PANEL = 8015;
  /** FAB au-dessus du panneau ouvert pour permettre le 2e clic (fermer). */
  const Z_FAB_ACTIVE = 8025;

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

  /** Décalage minimum des FAB (footer fixe saisie prod, etc.) */
  function minFabBaseBottom() {
    if (document.body.classList.contains('mysifa-app-fabrication')) return 88;
    return 0;
  }

  function isVisible(el) {
    if (!el) return false;
    if (el.id === 'ai-chat-root') return el.style.display !== 'none';
    return getComputedStyle(el).display !== 'none';
  }

  function calcPanelOpen() {
    var p = document.getElementById('_calc_panel');
    return !!(p && getComputedStyle(p).display !== 'none');
  }

  function chatPanelOpen() {
    var p = document.getElementById('cw-panel');
    return !!(p && !p.classList.contains('cw-hidden'));
  }

  function aiPanelOpen() {
    var p = document.getElementById('ai-chat-panel');
    return !!(p && p.classList.contains('open'));
  }

  function postitDockMenuOpen() {
    var m = document.getElementById('postit-dock-menu');
    return !!(m && m.classList.contains('open'));
  }

  function hasPostitDock() {
    var root = document.getElementById('postit-dock-root');
    return isVisible(root) && isDockFab(document.getElementById('postit-dock-btn'));
  }

  function expeCartePanelOpen() {
    if (typeof window.expeCartePanelOpen === 'function') return window.expeCartePanelOpen();
    var p = document.getElementById('expe-carte-panel');
    return !!(p && getComputedStyle(p).display !== 'none');
  }

  function raiseFabIfOpen(fab, open) {
    if (!fab) return;
    fab.style.zIndex = open ? String(Z_FAB_ACTIVE) : String(Z_FAB);
    fab.classList.toggle('mysifa-dock-fab-active', !!open);
  }

  function applyActiveFabZIndex() {
    raiseFabIfOpen(document.getElementById('_calc_fab'), calcPanelOpen());
    raiseFabIfOpen(document.getElementById('expe-carte-fab'), expeCartePanelOpen());
    raiseFabIfOpen(
      document.getElementById('cw-bubble') || document.getElementById('cw-bar'),
      chatPanelOpen()
    );
    raiseFabIfOpen(document.getElementById('ai-chat-btn'), aiPanelOpen());
    raiseFabIfOpen(document.getElementById('postit-dock-btn'), postitDockMenuOpen());
  }

  function layoutPostitDockMenu(btn, menu) {
    if (!btn || !menu || !menu.classList.contains('open')) return;
    menu.style.right = btn.style.right;
    menu.style.left = 'auto';
    menu.style.top = 'auto';
    menu.style.bottom = safeBottom(minFabBaseBottom() + FAB_SIZE + GAP);
    menu.style.boxShadow = SHADOW_PANEL;
    menu.style.zIndex = String(Z_FAB_ACTIVE);
  }

  function layoutExpeCartePanel(el, rightCol, bottom, zIndex) {
    if (!el || getComputedStyle(el).display === 'none') return;
    el.style.right = safeRight(rightCol);
    el.style.bottom = safeBottom(bottom);
    el.style.left = 'auto';
    el.style.top = 'auto';
    el.style.boxShadow = SHADOW_PANEL;
    el.style.zIndex = String(zIndex || Z_PANEL);
  }

  function isExpeApp() {
    return (window.__MYSIFA_APP__ || '') === 'expe';
  }

  /** MyExpé — grille 2×2 : bas [calc | carte], haut [messagerie | IA] */
  function layoutExpe2x2(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel) {
    const aiRoot = document.getElementById('ai-chat-root');
    const base = minFabBaseBottom();
    const step = FAB_SIZE + GAP;
    const gridH = step * 2;
    const mobile = isMobile();
    const landscape = isMobileLandscape();

    const hasCalc = isDockFab(calcFab);
    const hasCarte = isDockFab(carteFab);
    const hasAi = isVisible(aiRoot) && isDockFab(aiBtn);
    const chatFab =
      isDockFab(chatBubble) ? chatBubble : isDockFab(chatBar) ? chatBar : null;

    function placeFab(el, col, row) {
      if (!el) return;
      applyFab(el, safeRight(col * step), safeBottom(base + row * step));
      el.style.zIndex = String(Z_FAB);
      el.style.boxShadow = SHADOW_FAB;
    }

    function panelBottom(row) {
      return base + row * step + FAB_SIZE + 14;
    }

    if (chatBar && isDockFab(chatBar)) {
      chatBar.style.right = '';
      chatBar.style.bottom = '';
      chatBar.style.left = '';
      chatBar.style.top = '';
      chatBar.style.width = '';
      chatBar.style.maxWidth = '';
      chatBar.style.boxShadow = '';
    }
    if (chatBubble && isDockFab(chatBubble)) {
      chatBubble.style.left = '';
    }

    if (hasCalc) {
      placeFab(calcFab, 0, 0);
      if (calcPanel && getComputedStyle(calcPanel).display !== 'none') {
        calcPanel.style.right = safeRight(0);
        calcPanel.style.bottom = safeBottom(panelBottom(0));
        calcPanel.style.left = 'auto';
        calcPanel.style.top = 'auto';
        calcPanel.style.boxShadow = SHADOW_PANEL;
        calcPanel.style.zIndex = String(Z_PANEL);
      }
    }
    if (hasCarte) {
      placeFab(carteFab, 1, 0);
      layoutExpeCartePanel(cartePanel, step, panelBottom(0), Z_PANEL);
    }
    if (chatFab) placeFab(chatFab, 0, 1);
    if (hasAi) placeFab(aiBtn, 1, 1);

    const panelAboveGrid = base + gridH + 14;

    function layoutLandscapePanel(el, z) {
      if (!el) return;
      el.style.top = 'max(8px, env(safe-area-inset-top, 0px))';
      el.style.left = 'max(12px, env(safe-area-inset-left, 0px))';
      el.style.right = 'max(12px, env(safe-area-inset-right, 0px))';
      el.style.width = 'auto';
      el.style.maxWidth = 'none';
      el.style.marginLeft = '0';
      el.style.marginRight = '0';
      el.style.bottom = safeBottom(panelAboveGrid);
      const panelMaxH = 'calc(100dvh - ' + (panelAboveGrid + 12) + 'px)';
      el.style.height = panelMaxH;
      el.style.maxHeight = panelMaxH;
      el.style.minHeight = '0';
      el.style.borderRadius = '12px';
      el.style.boxShadow = SHADOW_PANEL;
      el.style.zIndex = String(z);
    }

    function layoutFloaterPanel(el, rightCol, row, z) {
      if (!el) return;
      const pb = panelBottom(row);
      el.style.top = 'auto';
      el.style.left = 'max(12px, env(safe-area-inset-left, 0px))';
      el.style.right = 'max(12px, env(safe-area-inset-right, 0px))';
      el.style.width = 'auto';
      el.style.maxWidth = rightCol === 0 ? 'min(420px, calc(100vw - 24px))' : 'none';
      el.style.marginLeft = 'auto';
      el.style.marginRight = 'auto';
      el.style.bottom = safeBottom(pb);
      const panelMaxH = 'calc(100dvh - ' + (pb + FAB_SIZE + 8) + 'px)';
      const panelMinH = 'min(560px, ' + panelMaxH + ')';
      el.style.height = panelMinH;
      el.style.maxHeight = panelMaxH;
      el.style.borderRadius = '14px';
      el.style.boxShadow = SHADOW_PANEL;
      el.style.zIndex = String(z);
    }

    if (mobile && landscape) {
      if (hasCarte && cartePanel && getComputedStyle(cartePanel).display !== 'none') {
        layoutLandscapePanel(cartePanel, 8017);
      }
      if (chatPanel && !chatPanel.classList.contains('cw-hidden')) {
        layoutChatLandscapePanel(chatPanel);
      }
      if (hasAi && aiPanel && aiPanel.classList.contains('open')) {
        layoutLandscapePanel(aiPanel, 8016);
      } else if (hasAi && aiPanel) {
        aiPanel.style.top = '';
        aiPanel.style.left = '';
        aiPanel.style.right = safeRight(step);
        aiPanel.style.bottom = safeBottom(base + step);
        aiPanel.style.width = '';
        aiPanel.style.maxWidth = '';
        aiPanel.style.height = '';
        aiPanel.style.maxHeight = '';
        aiPanel.style.minHeight = '';
        aiPanel.style.zIndex = '8002';
        aiPanel.style.boxShadow = '';
      }
    } else if (mobile) {
      if (hasCarte && cartePanel && getComputedStyle(cartePanel).display !== 'none') {
        layoutFloaterPanel(cartePanel, 1, 0, 8017);
        cartePanel.style.maxWidth = 'none';
      }
      if (chatPanel && !chatPanel.classList.contains('cw-hidden') && chatFab) {
        layoutFloaterPanel(chatPanel, 0, 1, 8015);
      }
      if (hasAi && aiPanel) {
        if (aiPanel.classList.contains('open')) {
          layoutFloaterPanel(aiPanel, 1, 1, 8016);
        } else {
          aiPanel.style.left = '';
          aiPanel.style.right = safeRight(step);
          aiPanel.style.bottom = safeBottom(base + step);
          aiPanel.style.width = '';
          aiPanel.style.maxWidth = '';
          aiPanel.style.height = '';
          aiPanel.style.maxHeight = '';
          aiPanel.style.zIndex = '8002';
          aiPanel.style.boxShadow = '';
        }
      }
    } else {
      if (chatPanel && !chatPanel.classList.contains('cw-hidden') && chatFab) {
        chatPanel.style.right = safeRight(0);
        chatPanel.style.bottom = safeBottom(panelBottom(1));
        chatPanel.style.left = 'auto';
        chatPanel.style.top = 'auto';
        chatPanel.style.boxShadow = SHADOW_PANEL;
        chatPanel.style.zIndex = String(Z_PANEL);
      }
      if (hasAi && aiPanel) {
        aiPanel.style.right = safeRight(step);
        aiPanel.style.bottom = safeBottom(panelBottom(1));
        aiPanel.style.left = 'auto';
        aiPanel.style.top = 'auto';
        aiPanel.style.boxShadow = SHADOW_PANEL;
        aiPanel.style.zIndex = String(Z_PANEL);
      }
    }

    applyActiveFabZIndex();
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

  /** Panneau messagerie paysage — même cadre vertical que l’assistant IA (8px haut, 62px bas). */
  function layoutChatLandscapePanel(el) {
    if (!el) return;
    el.style.top = 'max(8px, env(safe-area-inset-top, 0px))';
    el.style.left = 'max(12px, env(safe-area-inset-left, 0px))';
    el.style.right = 'max(12px, env(safe-area-inset-right, 0px))';
    el.style.bottom = 'max(62px, calc(env(safe-area-inset-bottom, 0px) + 62px))';
    el.style.width = 'auto';
    el.style.maxWidth = 'none';
    el.style.marginLeft = '0';
    el.style.marginRight = '0';
    el.style.height = 'calc(100dvh - 72px)';
    el.style.maxHeight = 'calc(100dvh - 72px)';
    el.style.minHeight = '0';
    el.style.display = 'flex';
    el.style.flexDirection = 'row';
    el.style.alignItems = 'stretch';
    el.style.borderRadius = '12px';
    el.style.boxShadow = SHADOW_PANEL;
    el.style.zIndex = '8015';
  }

  function layoutMobileLandscape(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel) {
    const aiRoot = document.getElementById('ai-chat-root');
    const fabRowH = FAB_SIZE + 14;
    let stackRight = 0;

    function placeFabRow(el) {
      if (!el) return;
      applyFab(el, safeRight(stackRight), safeBottom(minFabBaseBottom()));
      el.style.zIndex = '8002';
      el.style.boxShadow = SHADOW_FAB;
      stackRight += FAB_SIZE + GAP;
    }

    const hasCalc = isDockFab(calcFab);
    const hasCarte = isDockFab(carteFab);
    const hasAi = isVisible(aiRoot) && isDockFab(aiBtn);
    const chatFab =
      isDockFab(chatBubble) ? chatBubble : isDockFab(chatBar) ? chatBar : null;

    if (hasCalc) {
      placeFabRow(calcFab);
      if (calcPanel && getComputedStyle(calcPanel).display !== 'none') {
        calcPanel.style.right = safeRight(0);
        calcPanel.style.bottom = safeBottom(fabRowH);
        calcPanel.style.zIndex = String(Z_PANEL);
        calcPanel.style.boxShadow = SHADOW_PANEL;
      }
    }
    if (hasCarte) {
      const carteCol = stackRight;
      placeFabRow(carteFab);
      layoutExpeCartePanel(cartePanel, carteCol, fabRowH, 8017);
      if (cartePanel && getComputedStyle(cartePanel).display !== 'none') {
        layoutLandscapePanel(cartePanel, 8017);
      }
    }
    if (chatFab) placeFabRow(chatFab);
    if (hasAi) placeFabRow(aiBtn);

    const footerClear = minFabBaseBottom();
    const panelBottom = Math.max(fabRowH, footerClear + FAB_SIZE + GAP);
    const panelMaxH = 'calc(100dvh - ' + (panelBottom + 12) + 'px)';

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
      layoutChatLandscapePanel(chatPanel);
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
    applyActiveFabZIndex();
  }

  function layoutMobile(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel) {
    const aiRoot = document.getElementById('ai-chat-root');
    let stackBottom = minFabBaseBottom();

    function placeFab(el) {
      if (!el) return;
      applyFab(el, safeRight(0), safeBottom(stackBottom));
      el.style.zIndex = '8002';
      el.style.boxShadow = SHADOW_FAB;
      stackBottom += FAB_SIZE + GAP;
    }

    const hasCalc = isDockFab(calcFab);
    const hasCarte = isDockFab(carteFab);
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
    if (hasCarte) {
      placeFab(carteFab);
      layoutExpeCartePanel(cartePanel, 0, FAB_SIZE + 14, 8017);
      if (cartePanel && getComputedStyle(cartePanel).display !== 'none') {
        cartePanel.style.left = 'max(12px, env(safe-area-inset-left, 0px))';
        cartePanel.style.right = 'max(12px, env(safe-area-inset-right, 0px))';
        cartePanel.style.width = 'auto';
        cartePanel.style.maxWidth = 'none';
        cartePanel.style.maxHeight = 'calc(100dvh - ' + (stackBottom + FAB_SIZE + 20) + 'px)';
      }
    }
    if (chatFab) placeFab(chatFab);
    if (hasAi) placeFab(aiBtn);

    const fabStackH = stackBottom;
    const panelBottom = fabStackH + 12;
    const panelMaxH = 'calc(100dvh - ' + (panelBottom + FAB_SIZE + 8) + 'px)';
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

    if (hasCarte && cartePanel && getComputedStyle(cartePanel).display !== 'none') {
      layoutFloaterPanel(cartePanel, 8017);
      cartePanel.style.maxWidth = 'none';
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
    applyActiveFabZIndex();
  }

  function layout() {
    const calcFab = document.getElementById('_calc_fab');
    const calcPanel = document.getElementById('_calc_panel');
    const carteFab = document.getElementById('expe-carte-fab');
    const cartePanel = document.getElementById('expe-carte-panel');
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
    const hasCarte = isVisible(carteFab);
    const hasAi = isVisible(aiRoot) && isVisible(aiBtn);
    const hasChatBubble = isVisible(chatBubble);
    const hasChatBar = isVisible(chatBar);

    if (isExpeApp()) {
      layoutExpe2x2(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      return;
    }

    if (mobile) {
      if (landscape) {
        layoutMobileLandscape(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      } else {
        layoutMobile(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      }
      applyActiveFabZIndex();
      return;
    }

    if (hasChatBar) {
      chatBar.style.right = '';
      chatBar.style.bottom = '';
      chatBar.style.left = '';
      chatBar.style.top = '';
      chatBar.style.width = '';
      chatBar.style.maxWidth = '';
      chatBar.style.boxShadow = '';
    }
    if (hasChatBubble) {
      chatBubble.style.left = '';
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

    if (hasCarte) {
      applyFab(carteFab, safeRight(offsetRight), safeBottom(0));
      if (carteFab) carteFab.style.boxShadow = SHADOW_FAB;
      const carteCol = offsetRight;
      offsetRight += FAB_SIZE + GAP;
      bottomRowH = Math.max(bottomRowH, FAB_SIZE);
      layoutExpeCartePanel(cartePanel, carteCol, FAB_SIZE + 14, Z_PANEL);
    }

    if (hasAi) {
      applyFab(aiBtn, safeRight(offsetRight), safeBottom(0));
      if (aiBtn) aiBtn.style.boxShadow = SHADOW_FAB;
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

    if (hasPostitDock()) {
      const postitBtn = document.getElementById('postit-dock-btn');
      const postitMenu = document.getElementById('postit-dock-menu');
      applyFab(postitBtn, safeRight(offsetRight), safeBottom(0));
      if (postitBtn) postitBtn.style.boxShadow = SHADOW_FAB;
      layoutPostitDockMenu(postitBtn, postitMenu);
      offsetRight += FAB_SIZE + GAP;
    }

    function chatColumnOffset() {
      let chatCol = 0;
      if (hasCalc) chatCol += FAB_SIZE + GAP;
      if (hasCarte) chatCol += FAB_SIZE + GAP;
      if (hasAi && !hasCalc && !hasCarte) chatCol = 0;
      else if (hasAi && chatCol > 0) chatCol = Math.max(FAB_SIZE + GAP, chatCol - (FAB_SIZE + GAP));
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
    applyActiveFabZIndex();
  }

  var CALC_APPS = { stock: 1, prod: 1, compta: 1, expe: 1, fabrication: 1, planning: 1 };

  function bootPageWidgets() {
    var app = window.__MYSIFA_APP__ || '';
    if (CALC_APPS[app] && typeof window._calc_mount === 'function') window._calc_mount();
    if (app === 'expe' && typeof window._expe_carte_mount === 'function') window._expe_carte_mount();
    else if (typeof window._expe_carte_unmount === 'function') window._expe_carte_unmount();
    if (typeof window.initAiChatWidget === 'function') window.initAiChatWidget();
    layout();
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
    bootPageWidgets: bootPageWidgets,
    isMobileLandscape: isMobileLandscape,
    SHADOW_FAB: SHADOW_FAB,
    SHADOW_PANEL: SHADOW_PANEL,
  };
})();
