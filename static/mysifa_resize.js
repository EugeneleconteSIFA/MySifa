/**
 * MySifa — Redimensionnement aux 4 coins (post-its + messagerie).
 * Usage : MySifaResize.attach(element, {
 *   storageKey: 'mysifa_postit_size_42',     // clé localStorage pour persister
 *   minWidth: 260, minHeight: 120,            // bornes plancher
 *   maxWidth: () => window.innerWidth * 0.5,  // bornes plafond (fn ou nombre)
 *   maxHeight: () => window.innerHeight * 0.5,
 *   onResize:   ({w,h}) => {},                // pendant le drag (chaque frame)
 *   onResizeEnd:({w,h,left,top,moved}) => {}, // à la fin
 *   repositionOnResize: true,                 // ajuste left/top pour ancrer le
 *                                             // coin opposé (true par défaut)
 *   anchorBottomLeft: false,                  // si true, applique 'bottom' au
 *                                             // lieu de 'top' (panneau ancré bas)
 * });
 */
(function () {
  'use strict';

  let ACTIVE = null;

  function readStored(key) {
    if (!key) return null;
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return null;
      const o = JSON.parse(raw);
      if (!o || typeof o !== 'object') return null;
      return o;
    } catch (e) {
      return null;
    }
  }

  function writeStored(key, w, h) {
    if (!key) return;
    try {
      localStorage.setItem(key, JSON.stringify({ w: w, h: h }));
    } catch (e) {}
  }

  function clearStored(key) {
    if (!key) return;
    try {
      localStorage.removeItem(key);
    } catch (e) {}
  }

  function clamp(v, lo, hi) {
    if (hi < lo) hi = lo;
    return Math.max(lo, Math.min(hi, v));
  }

  function readBound(b, fallback) {
    if (typeof b === 'function') return b();
    if (typeof b === 'number') return b;
    return fallback;
  }

  function getBounds(opts) {
    const minW = readBound(opts.minWidth, 100);
    const minH = readBound(opts.minHeight, 100);
    // Plafond plancher (au minimum aussi grand que le min) — évite les
    // contradictions sur petit écran.
    const maxW = Math.max(minW, readBound(opts.maxWidth, window.innerWidth));
    const maxH = Math.max(minH, readBound(opts.maxHeight, window.innerHeight));
    return { minW: minW, minH: minH, maxW: maxW, maxH: maxH };
  }

  function applyStoredSize(el, opts) {
    if (!opts.storageKey) return;
    const saved = readStored(opts.storageKey);
    if (!saved || !saved.w || !saved.h) return;
    const b = getBounds(opts);
    const w = clamp(saved.w, b.minW, b.maxW);
    const h = clamp(saved.h, b.minH, b.maxH);
    el.style.width = w + 'px';
    el.style.height = h + 'px';
    if (typeof opts.onResize === 'function') opts.onResize({ w: w, h: h });
  }

  function attach(el, opts) {
    if (!el) return;
    opts = opts || {};
    if (el._mysifaResizeBound) return;
    el._mysifaResizeBound = true;

    const dirs = ['nw', 'ne', 'sw', 'se'];
    dirs.forEach(function (d) {
      const h = document.createElement('div');
      h.className = 'mysifa-resize-handle rh-' + d;
      h.setAttribute('data-dir', d);
      h.setAttribute('role', 'separator');
      h.setAttribute('aria-label', 'Redimensionner');
      h.addEventListener('mousedown', function (e) {
        onStart(e, el, d, opts);
      });
      // Empêche la sélection texte au double-clic.
      h.addEventListener('dragstart', function (e) {
        e.preventDefault();
      });
      el.appendChild(h);
    });

    applyStoredSize(el, opts);
  }

  function onStart(e, el, dir, opts) {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    const rect = el.getBoundingClientRect();
    ACTIVE = {
      el: el,
      dir: dir,
      opts: opts,
      start: {
        x: e.clientX,
        y: e.clientY,
        w: rect.width,
        h: rect.height,
        left: rect.left,
        top: rect.top,
        bottom: window.innerHeight - rect.bottom,
      },
      moved: false,
    };
    const handle = el.querySelector('.mysifa-resize-handle.rh-' + dir);
    if (handle) handle.classList.add('is-active');
    document.body.style.userSelect = 'none';
    document.body.style.cursor = getComputedStyle(handle || el).cursor;
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onEnd);
  }

  function onMove(e) {
    if (!ACTIVE) return;
    const s = ACTIVE.start;
    const dx = e.clientX - s.x;
    const dy = e.clientY - s.y;
    if (dx !== 0 || dy !== 0) ACTIVE.moved = true;

    let w = s.w;
    let h = s.h;

    if (ACTIVE.dir === 'se') {
      w = s.w + dx;
      h = s.h + dy;
    } else if (ACTIVE.dir === 'sw') {
      w = s.w - dx;
      h = s.h + dy;
    } else if (ACTIVE.dir === 'ne') {
      w = s.w + dx;
      h = s.h - dy;
    } else if (ACTIVE.dir === 'nw') {
      w = s.w - dx;
      h = s.h - dy;
    }

    const b = getBounds(ACTIVE.opts);
    const cw = clamp(w, b.minW, b.maxW);
    const ch = clamp(h, b.minH, b.maxH);

    let left = s.left;
    let top = s.top;
    let bottom = s.bottom;
    if (ACTIVE.dir === 'sw' || ACTIVE.dir === 'nw') {
      // Le coin droit reste figé → left = startRight - cw
      left = s.left + s.w - cw;
    }
    if (ACTIVE.dir === 'ne' || ACTIVE.dir === 'nw') {
      // Le coin bas reste figé → top = startBottom - ch
      top = s.top + s.h - ch;
    }
    if (ACTIVE.dir === 'se' || ACTIVE.dir === 'sw') {
      // Le coin haut reste figé → bottom = startBottom - dh
      bottom = s.bottom - (ch - s.h);
    }

    ACTIVE.el.style.width = cw + 'px';
    ACTIVE.el.style.height = ch + 'px';

    if (ACTIVE.opts.repositionOnResize !== false) {
      if (ACTIVE.opts.anchorBottomLeft) {
        // Préserve l'ancrage bas (cw-mode-bar). On ne touche left que si
        // le coin gauche bouge ; on ajuste bottom pour préserver le haut.
        if (ACTIVE.dir === 'sw' || ACTIVE.dir === 'nw') {
          ACTIVE.el.style.left = left + 'px';
          ACTIVE.el.style.right = 'auto';
        }
        ACTIVE.el.style.bottom = Math.max(0, bottom) + 'px';
        ACTIVE.el.style.top = 'auto';
      } else {
        ACTIVE.el.style.left = left + 'px';
        ACTIVE.el.style.top = top + 'px';
        ACTIVE.el.style.right = 'auto';
        ACTIVE.el.style.bottom = 'auto';
      }
    }

    if (typeof ACTIVE.opts.onResize === 'function') {
      ACTIVE.opts.onResize({ w: cw, h: ch, left: left, top: top });
    }
  }

  function onEnd() {
    if (!ACTIVE) return;
    const el = ACTIVE.el;
    const opts = ACTIVE.opts;
    const moved = ACTIVE.moved;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    const rect = el.getBoundingClientRect();
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    document.querySelectorAll('.mysifa-resize-handle.is-active').forEach(function (n) {
      n.classList.remove('is-active');
    });
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onEnd);
    ACTIVE = null;
    if (moved && opts.storageKey) writeStored(opts.storageKey, w, h);
    if (typeof opts.onResizeEnd === 'function') {
      opts.onResizeEnd({ w: w, h: h, left: rect.left, top: rect.top, moved: moved });
    }
  }

  window.MySifaResize = {
    attach: attach,
    readStored: readStored,
    writeStored: writeStored,
    clearStored: clearStored,
    applyStored: applyStoredSize,
  };
})();
