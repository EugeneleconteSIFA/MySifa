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

  const SVG_EYE = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const SVG_CHEVRON_DOWN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  // Colonne repliée : quatre carrés arrondis, la boîte à outils.
  const SVG_OUTILS = '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>';
  const SVG_EYE_OFF = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

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

  /**
   * Widgets propres à une page : un bouton `.mysifa-dock-fab.mysifa-dock-extra`
   * dont `data-dock-panel` donne l'id du panneau. Le dock les range à la suite
   * des widgets communs, sans avoir à connaître chacun d'eux.
   */
  function dockExtras() {
    return Array.prototype.filter.call(document.querySelectorAll('.mysifa-dock-extra'), isDockFab);
  }

  function extraPanelOpen(fab) {
    var id = fab && fab.getAttribute('data-dock-panel');
    var p = id ? document.getElementById(id) : null;
    return p && getComputedStyle(p).display !== 'none' ? p : null;
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
    dockExtras().forEach(function (f) { raiseFabIfOpen(f, !!extraPanelOpen(f)); });
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
    // Boutons propres à une page (capture de bloc…) : à gauche de la grille.
    dockExtras().forEach(function (f, i) { placeFab(f, 2 + i, 0); });

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

  var DOCK_WIDGET_FAB_IDS = ['_calc_fab', 'expe-carte-fab', 'ai-chat-btn', 'postit-dock-btn'];

  function getChatDockFab() {
    var bubble = document.getElementById('cw-bubble');
    if (isDockFab(bubble)) return bubble;
    var bar = document.getElementById('cw-bar');
    if (isVisible(bar)) return bar;
    return null;
  }

  /** Zone horizontale pour les post-its masqués : à droite de la messagerie, à gauche des widgets. */
  function getHiddenPostitBand() {
    var bandGap = 10;
    var vw = window.innerWidth || document.documentElement.clientWidth;
    var vh = window.innerHeight || document.documentElement.clientHeight;
    var bandLeft = 16;
    var bandRight = vw - 24;
    var rowTop = vh - minFabBaseBottom() - FAB_SIZE - 24;

    var chatEl = getChatDockFab();
    var widgetLeft = vw;
    var widgetTop = vh;

    DOCK_WIDGET_FAB_IDS.map(function (id) { return document.getElementById(id); })
      .concat(dockExtras()).forEach(function (el) {
      if (!isDockFab(el)) return;
      var r = el.getBoundingClientRect();
      if (r.left < widgetLeft) widgetLeft = r.left;
      if (r.top < widgetTop) widgetTop = r.top;
    });

    if (widgetLeft < vw) bandRight = widgetLeft - bandGap;

    if (chatEl) {
      var cr = chatEl.getBoundingClientRect();
      if (cr.top < widgetTop) widgetTop = cr.top;
      if (cr.right + bandGap < widgetLeft - bandGap) {
        bandLeft = Math.max(16, cr.right + bandGap);
        bandRight = widgetLeft - bandGap;
      } else {
        bandLeft = 16;
        bandRight = Math.min(bandRight, widgetLeft - bandGap);
      }
    }

    if (bandRight <= bandLeft + 60) {
      bandRight = Math.max(bandLeft + 120, (widgetLeft < vw ? widgetLeft : vw - 72) - bandGap);
    }

    if (widgetTop < vh) rowTop = widgetTop;

    return {
      left: Math.round(bandLeft),
      right: Math.round(bandRight),
      top: Math.round(rowTop),
      width: Math.max(0, Math.round(bandRight - bandLeft)),
    };
  }

  function layoutHiddenPostitsDock() {
    if (typeof window.layoutHiddenPostits === 'function') window.layoutHiddenPostits();
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
    const extras = dockExtras();
    extras.forEach(placeFabRow);
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
    extras.forEach(function (f) {
      var p = extraPanelOpen(f);
      if (p) layoutLandscapePanel(p, 8017);
    });

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
    const extras = dockExtras();
    extras.forEach(placeFab);
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
    extras.forEach(function (f) {
      var p = extraPanelOpen(f);
      if (p) layoutFloaterPanel(p, 8017);
    });

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

  /* ── Colonne d'outils (ordinateur) ─────────────────────────────────────
     La même « pilule » que la barre du portail (Paramètres, profil, ERP… :
     .portal-corner-stack dans app/web/portal_assets.py) : une carte
     verticale qui contient des boutons transparents de 44 px, icône grise,
     couleur du thème au survol et sur l'outil ouvert. Messagerie en bas (le
     coin, là où l'œil cherche le compteur de non-lus), outils au-dessus, et
     en tête un bouton qui replie la pilule en un seul bouton « outils ».
     Les boutons gardent leur position fixe, calculée un par un ; la carte est
     un fond dessiné derrière eux (#mysifa-dock-barre). Les panneaux
     s'ouvrent à gauche, calés sur le bas. Style : mysifa_dock.css. */
  var PIL_BTN = 44;
  var PIL_ECART = 2;
  var PIL_PAD_V = 8;
  var PIL_PAD_H = 6;
  var PIL_BORD = 1;
  var PIL_LARGEUR = PIL_BTN + 2 * (PIL_PAD_H + PIL_BORD);
  var PIL_REPLI = 28;   // hauteur du bouton de repli, pilule dépliée

  function panneauBarre(el, base, z) {
    if (!el) return;
    el.style.left = 'auto';
    el.style.top = 'auto';
    el.style.right = safeRight(PIL_LARGEUR + 12);
    el.style.bottom = safeBottom(base);
    el.style.boxShadow = SHADOW_PANEL;
    el.style.zIndex = String(z || Z_PANEL);
  }

  function layoutBarre(calcFab, calcPanel, carteFab, cartePanel, aiRoot, aiBtn, aiPanel, chatBubble, chatPanel) {
    document.body.classList.add('mysifa-dock-barre');
    var base = minFabBaseBottom();
    var replie = document.body.classList.contains('mysifa-dock-hidden');
    var postitBtn = document.getElementById('postit-dock-btn');
    var chat = isDockFab(chatBubble) ? chatBubble : null;

    // Du bas vers le haut. Sur le portail ordinateur, la messagerie reste sa
    // barre du bas à gauche (#cw-bar), hors de la pilule.
    var boutons = [];
    if (chat) boutons.push(chat);
    if (isVisible(aiRoot) && isDockFab(aiBtn)) boutons.push(aiBtn);
    if (hasPostitDock()) boutons.push(postitBtn);
    if (isDockFab(calcFab)) boutons.push(calcFab);
    if (isDockFab(carteFab)) boutons.push(carteFab);
    dockExtras().forEach(function (f) { boutons.push(f); });

    var fond = document.getElementById('mysifa-dock-barre');
    if (!fond) {
      fond = document.createElement('div');
      fond.id = 'mysifa-dock-barre';
      fond.setAttribute('aria-hidden', 'true');
      document.body.appendChild(fond);
    }
    var dedans = PIL_PAD_H + PIL_BORD;
    var y = base + PIL_BORD + PIL_PAD_V;
    if (!replie) {
      boutons.forEach(function (el) {
        applyFab(el, safeRight(dedans), safeBottom(y));
        el.style.top = 'auto';
        el.style.boxShadow = '';
        y += PIL_BTN + PIL_ECART;
      });
    }
    var bascule = document.getElementById('mysifa-dock-toggle');
    var hBascule = replie ? PIL_BTN : PIL_REPLI;
    if (bascule) {
      bascule.style.display = boutons.length ? '' : 'none';
      bascule.style.right = safeRight(dedans);
      bascule.style.bottom = safeBottom(y);
      bascule.style.left = 'auto';
      bascule.style.top = 'auto';
      y += hBascule;
    } else if (boutons.length) {
      y -= PIL_ECART;
    }
    fond.style.display = boutons.length ? '' : 'none';
    fond.style.right = safeRight(0);
    fond.style.bottom = safeBottom(base);
    fond.style.width = PIL_LARGEUR + 'px';
    fond.style.height = (y - base + PIL_PAD_V + PIL_BORD) + 'px';

    // Panneaux : à gauche de la pilule, calés sur son bas.
    if (calcPanel && getComputedStyle(calcPanel).display !== 'none') panneauBarre(calcPanel, base);
    if (cartePanel && getComputedStyle(cartePanel).display !== 'none') panneauBarre(cartePanel, base);
    if (aiPanel) panneauBarre(aiPanel, base);
    if (chatPanel && !chatPanel.classList.contains('cw-hidden') && chat) panneauBarre(chatPanel, base);
    var menu = document.getElementById('postit-dock-menu');
    if (menu && menu.classList.contains('open')) panneauBarre(menu, base, Z_FAB_ACTIVE);
    dockExtras().forEach(function (f) { panneauBarre(extraPanelOpen(f), base); });
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

    // Ordinateur : une barre verticale unique, la même dans toutes les applis
    // (MyExpé compris). Le téléphone garde ses dispositions ci-dessous.
    if (!mobile) {
      layoutBarre(calcFab, calcPanel, carteFab, cartePanel, aiRoot, aiBtn, aiPanel, chatBubble, chatPanel);
      layoutHiddenPostitsDock();
      return;
    }
    document.body.classList.remove('mysifa-dock-barre');
    var fond = document.getElementById('mysifa-dock-barre');
    if (fond) fond.style.display = 'none';
    var sep = document.getElementById('mysifa-dock-sep');
    if (sep) sep.style.display = 'none';

    if (isExpeApp()) {
      layoutExpe2x2(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      layoutHiddenPostitsDock();
      return;
    }

    if (mobile) {
      if (landscape) {
        layoutMobileLandscape(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      } else {
        layoutMobile(calcFab, calcPanel, carteFab, cartePanel, aiBtn, aiPanel, chatBubble, chatBar, chatPanel);
      }
      applyActiveFabZIndex();
      layoutHiddenPostitsDock();
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
      bottomRowH = Math.max(bottomRowH, FAB_SIZE); // postit occupe la rangée basse → messagerie monte au-dessus
    }

    dockExtras().forEach(function (fab) {
      applyFab(fab, safeRight(offsetRight), safeBottom(0));
      fab.style.boxShadow = SHADOW_FAB;
      var p = extraPanelOpen(fab);
      if (p) {
        p.style.left = 'auto';
        p.style.top = 'auto';
        p.style.right = safeRight(offsetRight);
        p.style.bottom = safeBottom(FAB_SIZE + 14);
        p.style.zIndex = String(Z_PANEL);
        p.style.boxShadow = SHADOW_PANEL;
      }
      offsetRight += FAB_SIZE + GAP;
      bottomRowH = Math.max(bottomRowH, FAB_SIZE);
    });

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
    layoutHiddenPostitsDock();
  }

  var CALC_APPS = { stock: 1, prod: 1, compta: 1, expe: 1, fabrication: 1, planning: 1 };

  function initDockToggle() {
    if (document.getElementById('mysifa-dock-toggle')) return;

    var hidden = false;
    try { hidden = localStorage.getItem('mysifa_dock_hidden') === '1'; } catch (e) {}
    if (hidden) document.body.classList.add('mysifa-dock-hidden');

    var btn = document.createElement('button');
    btn.id = 'mysifa-dock-toggle';
    btn.type = 'button';
    // Ordinateur : flèche de la barre ; téléphone : l'œil d'origine.
    function icone(h) {
      if (isMobile()) return h ? SVG_EYE_OFF : SVG_EYE;
      return h ? SVG_OUTILS : SVG_CHEVRON_DOWN;
    }
    function maj(h) {
      btn.title = h ? 'Afficher les outils' : 'Replier les outils';
      btn.setAttribute('aria-label', btn.title);
      btn.innerHTML = icone(h);
    }
    maj(hidden);

    btn.addEventListener('click', function () {
      var isHidden = document.body.classList.toggle('mysifa-dock-hidden');
      try { localStorage.setItem('mysifa_dock_hidden', isHidden ? '1' : ''); } catch (e) {}
      maj(isHidden);
      layout();
    });
    window.addEventListener('resize', function () {
      maj(document.body.classList.contains('mysifa-dock-hidden'));
    });

    // Colonne repliée : le compteur de messages non lus passe sur le bouton
    // « outils », sinon un nouveau message passerait inaperçu.
    var pastille = document.createElement('span');
    pastille.id = 'mysifa-dock-toggle-badge';
    btn.appendChild(pastille);
    var majCompteur = function () {
      var src = document.getElementById('cw-bubble-badge');
      var n = src && getComputedStyle(src).display !== 'none' ? (src.textContent || '').trim() : '';
      // N'écrire que si ça change : l'observateur ci-dessous verrait sinon
      // ses propres écritures et tournerait en boucle.
      if (pastille.textContent !== n) pastille.textContent = n;
      var d = n ? '' : 'none';
      if (pastille.style.display !== d) pastille.style.display = d;
      if (pastille.parentNode !== btn) btn.appendChild(pastille);
    };
    var prevMaj = maj;
    maj = function (h) { prevMaj(h); majCompteur(); };
    majCompteur();
    if (window.MutationObserver) {
      new MutationObserver(majCompteur).observe(document.body, {
        subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['style', 'class'],
      });
    }

    document.body.appendChild(btn);
  }

  function bootPageWidgets() {
    var app = window.__MYSIFA_APP__ || '';
    if (CALC_APPS[app] && typeof window._calc_mount === 'function') window._calc_mount();
    if (app === 'expe' && typeof window._expe_carte_mount === 'function') window._expe_carte_mount();
    else if (typeof window._expe_carte_unmount === 'function') window._expe_carte_unmount();
    if (typeof window.initAiChatWidget === 'function') window.initAiChatWidget();
    if (typeof window.initPostitDock === 'function') window.initPostitDock();
    if (typeof window.initPostitsApp === 'function') window.initPostitsApp();
    layout();
    initDockToggle();
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
    getHiddenPostitBand: getHiddenPostitBand,
    SHADOW_FAB: SHADOW_FAB,
    SHADOW_PANEL: SHADOW_PANEL,
  };
})();
