/**
 * MySifa — Disposition flexible des widgets flottants (calculette, messagerie, IA).
 * Recalcule les positions selon les widgets réellement visibles.
 */
(function () {
  'use strict';

  const GAP = 12;
  const FAB_SIZE = 48;
  const SHADOW_FAB = '0 4px 16px rgba(34,211,238,0.35)';
  const SHADOW_PANEL = '0 12px 48px rgba(0,0,0,0.5)';

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
    return el.offsetParent !== null || getComputedStyle(el).display !== 'none';
  }

  function applyFab(el, right, bottom) {
    if (!el) return;
    el.style.right = right;
    el.style.bottom = bottom;
  }

  function layout() {
    const calcFab = document.getElementById('_calc_fab');
    const calcPanel = document.getElementById('_calc_panel');
    const aiRoot = document.getElementById('ai-chat-root');
    const aiBtn = document.getElementById('ai-chat-btn');
    const aiPanel = document.getElementById('ai-chat-panel');
    const chatBubble = document.getElementById('cw-bubble');
    const chatPanel = document.getElementById('cw-panel');

    const hasCalc = isVisible(calcFab);
    const hasAi = isVisible(aiRoot) && isVisible(aiBtn);
    const hasChatBubble = isVisible(chatBubble);

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

    if (hasChatBubble) {
      let chatCol = 0;
      if (hasCalc && hasAi) chatCol = FAB_SIZE + GAP;
      else if (hasCalc) chatCol = FAB_SIZE + GAP;
      else if (hasAi) chatCol = 0;
      const stackH = bottomRowH > 0 ? bottomRowH + GAP : 0;
      applyFab(chatBubble, safeRight(chatCol), safeBottom(stackH));
      if (chatBubble) chatBubble.style.boxShadow = SHADOW_FAB;
      if (chatPanel && !chatPanel.classList.contains('cw-hidden')) {
        chatPanel.style.right = safeRight(chatCol);
        chatPanel.style.bottom = safeBottom(stackH + FAB_SIZE + GAP);
        chatPanel.style.boxShadow = SHADOW_PANEL;
      }
    }

    if (chatPanel && chatPanel.classList.contains('cw-mode-bubble')) {
      if (chatPanel.classList.contains('cw-hidden')) {
        chatPanel.style.boxShadow = '';
      } else if (hasChatBubble) {
        const stackH =
          (bottomRowH > 0 ? bottomRowH + GAP : 0) + FAB_SIZE + GAP;
        let chatCol = 0;
        if (hasCalc && hasAi) chatCol = FAB_SIZE + GAP;
        else if (hasCalc) chatCol = FAB_SIZE + GAP;
        chatPanel.style.right = safeRight(chatCol);
        chatPanel.style.bottom = safeBottom(stackH);
        chatPanel.style.boxShadow = SHADOW_PANEL;
      }
    }
  }

  window.MySifaDock = { layout: layout, SHADOW_FAB: SHADOW_FAB, SHADOW_PANEL: SHADOW_PANEL };
})();
