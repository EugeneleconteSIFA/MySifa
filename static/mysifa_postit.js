/**
 * MySifa — Post-its (portail + toutes les pages applicatives si multi-page activé).
 * Prise de notes libre en blocs, menu « / » à la manière de Notion.
 * Compatible SPA html.py (S.app) et pages autonomes (window.__MYSIFA_APP__).
 */
(function () {
  'use strict';

  const PostitState = { items: [] };
  let _postitDrag = null;
  let _postitDockMenuOpen = false;
  let _postitDockBound = false;
  let _postitColorPaletteOpen = null;

  const POSTIT_DEFAULT_COLORS = { today: '#22d3ee', someday: '#fbbf24' };
  const POSTIT_COLOR_PALETTE = [
    '#22d3ee',
    '#0891b2',
    '#34d399',
    '#fbbf24',
    '#fb923c',
    '#f87171',
    '#a78bfa',
    '#60a5fa',
    '#f472b6',
    '#94a3b8',
  ];

  const POSTIT_WIDTH = 260;
  const POSTIT_DOCK_GAP = 10;
  const POSTIT_ANIM_MS = 360;
  /** Décalage vertical supplémentaire des post-its masqués (≈ moitié de l'en-tête). */
  const POSTIT_HIDDEN_LOWER_EXTRA = 21;
  /** Au-dessus des FAB dock actifs (8025) pour que les pastilles restent cliquables. */
  const POSTIT_COLOR_PALETTE_Z = 8030;

  function postitFindById(id) {
    var nid = Number(id);
    if (!nid) return null;
    return (
      PostitState.items.find(function (x) {
        return Number(x.id) === nid;
      }) || null
    );
  }

  const POSTIT_DOCK_ICON =
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M5 5h12l4 4v10H5V5z"/>' +
    '<path d="M17 5v4h4"/></svg>';

  const POSTIT_HIDE_ICON =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>';

  function postitCurrentApp() {
    if (typeof S !== 'undefined' && S && S.app) return S.app;
    return window.__MYSIFA_APP__ || '';
  }

  function postitUserLoggedIn() {
    if (typeof S !== 'undefined' && S && S.user) return true;
    return !!(window.__MYSIFA_UID__ && Number(window.__MYSIFA_UID__) > 0);
  }

  function postitDesktopEnabled() {
    return !!(postitUserLoggedIn() && window.matchMedia('(min-width:1024px)').matches);
  }

  function postitsForCurrentPage() {
    const items = Array.isArray(PostitState.items) ? PostitState.items : [];
    if (postitCurrentApp() === 'portal') return items;
    return items.filter(function (p) {
      return !!p.multi_page;
    });
  }

  function postitIsHidden(p) {
    return !!(p && (p.hidden === 1 || p.hidden === true));
  }

  function postitDefaultColor(type) {
    return POSTIT_DEFAULT_COLORS[type] || POSTIT_DEFAULT_COLORS.today;
  }

  function postitResolveColor(p) {
    var c = p && p.color ? String(p.color).trim() : '';
    if (/^#[0-9A-Fa-f]{6}$/.test(c)) return c.toLowerCase();
    return postitDefaultColor(p && p.type);
  }

  function applyPostitColor(el, color) {
    if (!el || !color) return;
    el.style.setProperty('--postit-color', color);
    var dot = el.querySelector('.postit-color-dot');
    if (dot) dot.style.background = color;
  }

  function bindPostitColorPaletteDocClose() {
    if (window._postitColorPaletteDocBound) return;
    window._postitColorPaletteDocBound = true;
    /* capture:true — avant le mousedown sur la pastille, sans fermer la palette en cours d'ouverture */
    document.addEventListener(
      'mousedown',
      function (e) {
        var pal = document.getElementById('postit-color-palette');
        if (!pal || !pal.classList.contains('open')) return;
        if (pal.contains(e.target) || e.target.closest('.postit-color-dot')) return;
        closePostitColorPalette();
      },
      true
    );
  }

  function fillPostitColorPalette(pal) {
    if (!pal) return;
    pal.querySelectorAll('.postit-color-swatch').forEach(function (btn) {
      btn.remove();
    });
    POSTIT_COLOR_PALETTE.forEach(function (hex) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'postit-color-swatch';
      btn.style.setProperty('--postit-swatch-bg', hex);
      btn.style.backgroundColor = hex;
      btn.title = hex;
      btn.dataset.color = hex;
      btn.addEventListener('mousedown', function (e) {
        e.stopPropagation();
      });
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        e.preventDefault();
        var pid = parseInt(pal.dataset.postitId, 10);
        if (pid) setPostitColor(pid, hex);
        closePostitColorPalette();
      });
      pal.appendChild(btn);
    });
  }

  function ensurePostitColorPalette() {
    bindPostitColorPaletteDocClose();
    var pal = document.getElementById('postit-color-palette');
    if (!pal) {
      pal = document.createElement('div');
      pal.id = 'postit-color-palette';
      pal.setAttribute('role', 'menu');
      pal.setAttribute('aria-label', 'Couleur du post-it');
      document.body.appendChild(pal);
    }
    pal.style.zIndex = String(POSTIT_COLOR_PALETTE_Z);
    if (!pal.querySelector('.postit-color-swatch')) fillPostitColorPalette(pal);
    return pal;
  }

  function closePostitColorPalette() {
    var pal = document.getElementById('postit-color-palette');
    if (pal) {
      pal.classList.remove('open');
      pal.style.display = '';
      pal.dataset.postitId = '';
    }
    _postitColorPaletteOpen = null;
  }

  function postitColorPaletteIsOpen(id) {
    return _postitColorPaletteOpen != null && Number(_postitColorPaletteOpen) === Number(id);
  }

  function openPostitColorPalette(id, dot) {
    var nid = Number(id);
    if (!nid) return;
    if (postitColorPaletteIsOpen(nid)) {
      closePostitColorPalette();
      return;
    }
    closePostitDockMenu();
    if (!dot) {
      var el = document.querySelector('.postit[data-id="' + nid + '"]');
      dot = el && el.querySelector('.postit-color-dot');
    }
    if (!dot) return;
    var p = postitFindById(nid);
    var pal = ensurePostitColorPalette();
    pal.dataset.postitId = String(nid);
    updatePostitColorPaletteActive(postitResolveColor(p));
    positionPostitColorPalette(dot);
    document.body.appendChild(pal);
    pal.classList.add('open');
    pal.style.display = 'flex';
    _postitColorPaletteOpen = nid;
  }

  function setupPostitColorDot(el, id) {
    var dot = el.querySelector('.postit-color-dot');
    if (!dot || dot._postitColorBound) return;
    dot._postitColorBound = true;
    dot.addEventListener('mousedown', function (e) {
      e.stopPropagation();
      e.preventDefault();
      openPostitColorPalette(id, dot);
    });
  }

  function positionPostitColorPalette(dot) {
    var pal = ensurePostitColorPalette();
    var rect = dot.getBoundingClientRect();
    var palW = 200;
    var left = rect.left;
    var top = rect.bottom + 6;
    if (left + palW > window.innerWidth - 12) left = window.innerWidth - palW - 12;
    if (left < 12) left = 12;
    if (top + 88 > window.innerHeight - 12) top = Math.max(12, rect.top - 88 - 6);
    pal.style.left = left + 'px';
    pal.style.top = top + 'px';
  }

  function updatePostitColorPaletteActive(color) {
    var pal = document.getElementById('postit-color-palette');
    if (!pal) return;
    var norm = String(color || '').toLowerCase();
    pal.querySelectorAll('.postit-color-swatch').forEach(function (btn) {
      btn.classList.toggle('active', String(btn.dataset.color || '').toLowerCase() === norm);
    });
  }

  function togglePostitColorPalette(e, id) {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    var el = document.querySelector('.postit[data-id="' + id + '"]');
    var dot = el && el.querySelector('.postit-color-dot');
    openPostitColorPalette(id, dot);
  }

  async function setPostitColor(id, color) {
    var hex = String(color || '').toLowerCase();
    if (!/^#[0-9a-f]{6}$/.test(hex)) return;
    var p = postitFindById(id);
    if (!p) return;
    try {
      var r = await postitApi('/api/postits/' + id, {
        method: 'PATCH',
        body: JSON.stringify({ color: hex }),
      });
      p.color = r && r.color ? r.color : hex;
      var el = document.querySelector('.postit[data-id="' + id + '"]');
      if (el) applyPostitColor(el, postitResolveColor(p));
    } catch (e) {
      postitToast((e && e.message) || 'Couleur non enregistrée.', 'danger');
    }
  }

  function postitEscHtml(s) {
    if (typeof escHtml === 'function') return escHtml(s);
    if (typeof esc === 'function') return esc(s);
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function postitEscAttr(s) {
    if (typeof escAttr === 'function') return escAttr(s);
    return postitEscHtml(s).replace(/"/g, '&quot;');
  }

  function postitToast(msg, type) {
    if (typeof showToast === 'function') return showToast(msg, type);
    if (typeof toast === 'function') {
      var isErr = type === 'danger' || type === 'error';
      var app = postitCurrentApp();
      if (app === 'profil') return toast(msg, !isErr);
      return toast(msg, isErr);
    }
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText =
      'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;' +
      'padding:10px 16px;border-radius:10px;font-size:13px;font-weight:600;' +
      'background:var(--card);border:1px solid var(--border);color:var(--text);';
    document.body.appendChild(t);
    setTimeout(function () {
      t.remove();
    }, 3200);
  }

  /** Appels post-its — toujours /api/postits (pas le api() local des pages planning, rh, stock…). */
  function postitApi(path, options) {
    options = options || {};
    var url = String(path || '');
    if (url.indexOf('http') !== 0) {
      if (url.indexOf('/') !== 0) url = '/' + url;
    }
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    var fetchOpts = Object.assign({}, options, { credentials: 'include', headers: headers });
    return fetch(url, fetchOpts).then(function (r) {
      if (r.status === 401) {
        try {
          window.location.href = '/';
        } catch (e) {}
        return Promise.reject(new Error('Session expirée'));
      }
      if (!r.ok) {
        return r.json().catch(function () {
          return {};
        }).then(function (j) {
          var d = j && j.detail;
          var msg =
            typeof d === 'string' ? d : d ? JSON.stringify(d) : 'Erreur ' + r.status;
          throw new Error(msg);
        });
      }
      if (r.status === 204) return null;
      var ct = r.headers.get('content-type') || '';
      if (ct.indexOf('application/json') >= 0) return r.json();
      return null;
    });
  }

  function dockLayout() {
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  function ensurePostitLayer() {
    var layer = document.getElementById('postitLayer');
    if (!layer) {
      layer = document.createElement('div');
      layer.className = 'postit-layer';
      layer.id = 'postitLayer';
      document.body.appendChild(layer);
    }
    layer.style.display = postitDesktopEnabled() ? 'block' : 'none';
    return layer;
  }

  function postitHeaderHeight(el) {
    var h = el && el.querySelector('.postit-header');
    return h ? h.offsetHeight : 42;
  }

  function measurePostitPeekUp(el) {
    if (!el) return 140;
    el.classList.add('is-peek');
    var full = el.scrollHeight;
    el.classList.remove('is-peek');
    var headerH = postitHeaderHeight(el);
    return Math.max(0, full - headerH);
  }

  function updatePostitPeekVar(el) {
    if (!el || !el.classList.contains('is-hidden')) return;
    el.style.setProperty('--postit-peek-up', measurePostitPeekUp(el) + 'px');
  }

  function getHiddenPostitBand() {
    if (window.MySifaDock && typeof window.MySifaDock.getHiddenPostitBand === 'function') {
      return window.MySifaDock.getHiddenPostitBand();
    }
    var vw = window.innerWidth || document.documentElement.clientWidth;
    var vh = window.innerHeight || document.documentElement.clientHeight;
    return {
      left: 16,
      right: vw - 220,
      top: vh - 66 - POSTIT_HIDDEN_LOWER_EXTRA,
      width: vw - 236,
    };
  }

  function layoutHiddenPostits() {
    if (!postitDesktopEnabled()) return;
    var hidden = [];
    document.querySelectorAll('.postit.is-hidden').forEach(function (el) {
      hidden.push(el);
    });
    if (!hidden.length) return;
    hidden.sort(function (a, b) {
      return (parseInt(a.dataset.id, 10) || 0) - (parseInt(b.dataset.id, 10) || 0);
    });
    var band = getHiddenPostitBand();
    var bandLeft = band.left;
    var bandRight = band.right;
    var top = band.top + POSTIT_HIDDEN_LOWER_EXTRA;
    var left = bandLeft;
    hidden.forEach(function (el) {
      var w = el.offsetWidth || POSTIT_WIDTH;
      if (left + w > bandRight) {
        left = bandLeft;
        top -= postitHeaderHeight(el) + POSTIT_DOCK_GAP;
      }
      el.style.left = left + 'px';
      el.style.top = top + 'px';
      updatePostitPeekVar(el);
      left += w + POSTIT_DOCK_GAP;
    });
  }

  function animatePostitPosition(el, left, top, onDone) {
    if (!el) {
      if (onDone) onDone();
      return;
    }
    el.classList.add('is-animating');
    el.style.left = left + 'px';
    el.style.top = top + 'px';
    window.setTimeout(function () {
      el.classList.remove('is-animating');
      if (onDone) onDone();
    }, POSTIT_ANIM_MS);
  }

  function applyPostitHiddenState(el, p, animate) {
    if (!el || !p) return;
    var hidden = postitIsHidden(p);
    if (hidden) {
      el.classList.add('is-hidden');
      if (animate) {
        el.classList.add('is-animating');
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            layoutHiddenPostits();
            window.setTimeout(function () {
              el.classList.remove('is-animating');
            }, POSTIT_ANIM_MS);
          });
        });
      } else {
        layoutHiddenPostits();
      }
    } else {
      el.classList.remove('is-hidden');
      el.style.transform = '';
      var x = p.pos_x != null ? p.pos_x : 100;
      var y = p.pos_y != null ? p.pos_y : 100;
      if (animate) {
        el.classList.add('is-animating');
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            animatePostitPosition(el, x, y, function () {
              el.classList.remove('is-animating');
            });
          });
        });
      } else {
        el.style.left = x + 'px';
        el.style.top = y + 'px';
      }
    }
  }

  function setupPostitInteractions(el, p) {
    el.addEventListener('mouseenter', function () {
      if (!el.classList.contains('is-hidden')) return;
      updatePostitPeekVar(el);
    });
    el.addEventListener('click', function (e) {
      if (!el.classList.contains('is-hidden')) return;
      if (e.target.closest('button, input, textarea, label, a')) return;
      restorePostitFromHidden(p.id);
    });
  }

  function buildPostitEl(p) {
    var el = document.createElement('div');
    el.className = 'postit' + (postitIsHidden(p) ? ' is-hidden' : '');
    el.dataset.id = String(p.id);
    el.dataset.type = p.type;
    if (!postitIsHidden(p)) {
      el.style.left = (p.pos_x != null ? p.pos_x : 100) + 'px';
      el.style.top = (p.pos_y != null ? p.pos_y : 100) + 'px';
    }
    var multiOn = !!p.multi_page;
    var hideTitle = postitIsHidden(p)
      ? 'Afficher à la position enregistrée'
      : 'Réduire en bas de l\'écran';
    el.innerHTML =
      '<div class="postit-header" onmousedown="startPostitDrag(event, ' +
      p.id +
      ')">' +
      '<button type="button" class="postit-color-dot" title="Changer la couleur" aria-label="Changer la couleur" aria-haspopup="menu"></button>' +
      '<input class="postit-title" value="' +
      postitEscAttr(p.title || '') +
      '" onchange="renamePostit(' +
      p.id +
      ', this.value)" onmousedown="event.stopPropagation()">' +
      '<div class="postit-header-actions">' +
      '<button type="button" class="postit-hide-btn" onclick="event.stopPropagation(); togglePostitHidden(' +
      p.id +
      ')" title="' +
      postitEscAttr(hideTitle) +
      '">' +
      POSTIT_HIDE_ICON +
      '</button>' +
      '<button type="button" class="postit-delete-btn" onclick="deletePostit(' +
      p.id +
      ')" title="Supprimer">×</button></div></div>' +
      '<div class="postit-body" id="postit-body-' +
      p.id +
      '" data-postit="' +
      p.id +
      '">' +
      edBlocsHtml(p) +
      '</div>' +
      '<div class="postit-footer" onmousedown="startPostitDrag(event, ' +
      p.id +
      ')">' +
      '<button type="button" class="postit-add-task-btn" onclick="postitOuvrirCommandes(' +
      p.id +
      ')" title="Ajouter un bloc — ou taper « / » dans le texte">/ Insérer</button>' +
      '<button type="button" class="postit-multipage-btn' +
      (multiOn ? ' on' : '') +
      '" onclick="togglePostitMultiPage(' +
      p.id +
      ')" title="' +
      (multiOn
        ? 'Visible sur toutes les pages — cliquer pour limiter au portail'
        : 'Visible sur le portail uniquement — cliquer pour afficher sur toutes les pages') +
      '">' +
      (multiOn ? 'Désactiver' : 'Activer') +
      ' <span class="postit-multipage-label">(multi-page)</span></button>' +
      '<button type="button" class="postit-clear-btn" onclick="clearPostitDone(' +
      p.id +
      ')"' +
      (edACoche(p) ? '' : ' hidden') +
      '>Effacer cochées</button>' +
      '</div>';
    applyPostitColor(el, postitResolveColor(p));
    setupPostitColorDot(el, p.id);
    setupPostitInteractions(el, p);
    setupPostitResize(el, p);
    edBrancher(el.querySelector('.postit-body'), p);
    return el;
  }

  function setupPostitResize(el, p) {
    if (!el || !window.MySifaResize) return;
    var pid = p && p.id;
    if (!pid) return;
    window.MySifaResize.attach(el, {
      storageKey: 'mysifa_postit_size_' + pid,
      minWidth: POSTIT_WIDTH,
      minHeight: 120,
      maxWidth: function () { return Math.max(POSTIT_WIDTH + 120, window.innerWidth * 0.5); },
      maxHeight: function () { return Math.max(220, window.innerHeight * 0.5); },
      onResize: function () {
        if (!el.classList.contains('is-resized')) el.classList.add('is-resized');
      },
      onResizeEnd: function (info) {
        if (!info || !info.moved) return;
        // Si le coin NW ou SW a déplacé la position, on persiste pos_x/pos_y.
        var nx = parseInt(el.style.left, 10);
        var ny = parseInt(el.style.top, 10);
        if (!isNaN(nx) && !isNaN(ny) && (nx !== p.pos_x || ny !== p.pos_y)) {
          p.pos_x = nx;
          p.pos_y = ny;
          postitApi('/api/postits/' + pid + '/pos', {
            method: 'PATCH',
            body: JSON.stringify({ x: nx, y: ny }),
          }).catch(function () {});
        }
      },
    });
    // Restaure la classe is-resized si une taille est déjà enregistrée.
    if (window.MySifaResize.readStored('mysifa_postit_size_' + pid)) {
      el.classList.add('is-resized');
    }
  }

  function autoResizePostitTask(el) {
    if (!el) return;
    el.style.height = '0';
    var lineH = parseFloat(getComputedStyle(el).lineHeight) || 18;
    var minH = Math.ceil(lineH);
    el.style.height = Math.max(minH, el.scrollHeight) + 'px';
  }

  function fitPostitTaskTextareas(root) {
    if (!root) return;
    root.querySelectorAll('.pb-txt').forEach(function (ta) {
      autoResizePostitTask(ta);
    });
  }

  function renderPostits() {
    closePostitColorPalette();
    var layer = ensurePostitLayer();
    if (!layer) return;
    layer.querySelectorAll('.postit').forEach(function (el) {
      el.remove();
    });
    postitsForCurrentPage().forEach(function (p) {
      var el = buildPostitEl(p);
      layer.appendChild(el);
      fitPostitTaskTextareas(el.querySelector('.postit-body'));
      applyPostitHiddenState(el, p, false);
    });
    layoutHiddenPostits();
  }

  async function loadPostits() {
    try {
      var data = await postitApi('/api/postits');
      if (data == null) return;
      PostitState.items = Array.isArray(data) ? data : [];
      renderPostits();
    } catch (e) {
      postitToast((e && e.message) || 'Chargement des post-its impossible.', 'danger');
    }
  }

  function clearPostitsUi() {
    closePostitColorPalette();
    closePostitDockMenu();
    PostitState.items = [];
    var layer = document.getElementById('postitLayer');
    if (layer) {
      layer.querySelectorAll('.postit').forEach(function (el) { el.remove(); });
      layer.style.display = 'none';
    }
    var dockRoot = document.getElementById('postit-dock-root');
    if (dockRoot) dockRoot.style.display = 'none';
  }

  function initPostitsApp() {
    bindPostitColorPaletteDocClose();
    if (!postitUserLoggedIn() || postitCurrentApp() === 'login') {
      // Après déconnexion ou sur l'écran de connexion : on purge les post-its résiduels.
      clearPostitsUi();
      return;
    }
    ensurePostitLayer();
    if (!postitDesktopEnabled()) return;
    loadPostits().catch(function () {});
  }

  function closePostitDockMenu() {
    _postitDockMenuOpen = false;
    var menu = document.getElementById('postit-dock-menu');
    var btn = document.getElementById('postit-dock-btn');
    if (menu) menu.classList.remove('open');
    if (btn) btn.classList.remove('mysifa-dock-fab-active');
    dockLayout();
  }

  function togglePostitDockMenu() {
    _postitDockMenuOpen = !_postitDockMenuOpen;
    var menu = document.getElementById('postit-dock-menu');
    var btn = document.getElementById('postit-dock-btn');
    if (menu) menu.classList.toggle('open', _postitDockMenuOpen);
    if (btn) btn.classList.toggle('mysifa-dock-fab-active', _postitDockMenuOpen);
    dockLayout();
  }

  async function addPostit(type) {
    var title = type === 'today' ? 'Aujourd\'hui' : 'Note';
    var blocs = type === 'today' ? [{ type: 'todo', texte: '', coche: false }] : [{ type: 'p', texte: '' }];
    closePostitDockMenu();
    try {
      var p = await postitApi('/api/postits', {
        method: 'POST',
        body: JSON.stringify({ type: type, title: title, blocs: blocs }),
      });
      if (!p) return;
      if (!Array.isArray(p.blocs) || !p.blocs.length) p.blocs = blocs;
      PostitState.items.push(p);
      renderPostits();
      requestAnimationFrame(function () {
        edFocus(p.id, 0, 0);
      });
    } catch (e) {
      postitToast((e && e.message) || 'Création impossible.', 'danger');
    }
  }

  function initPostitDock() {
    var root = document.getElementById('postit-dock-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'postit-dock-root';
      root.innerHTML =
        '<button type="button" id="postit-dock-btn" class="mysifa-dock-fab" aria-label="Post-its" title="Post-its">' +
        POSTIT_DOCK_ICON +
        '</button>' +
        '<div id="postit-dock-menu" class="mysifa-dock-panel" role="menu" aria-label="Créer un post-it">' +
        '<button type="button" class="postit-dock-menu-btn someday" role="menuitem">Note libre</button>' +
        '<button type="button" class="postit-dock-menu-btn today" role="menuitem">Liste du jour</button>' +
        '</div>';
      document.body.appendChild(root);
      var btn = root.querySelector('#postit-dock-btn');
      var menu = root.querySelector('#postit-dock-menu');
      if (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          togglePostitDockMenu();
        });
      }
      if (menu) {
        menu.querySelectorAll('.postit-dock-menu-btn').forEach(function (b) {
          b.addEventListener('click', function (e) {
            e.stopPropagation();
            var t = b.classList.contains('today') ? 'today' : 'someday';
            addPostit(t);
          });
        });
      }
      if (!_postitDockBound) {
        _postitDockBound = true;
        document.addEventListener('click', function (e) {
          if (_postitDockMenuOpen) {
            var r = document.getElementById('postit-dock-root');
            if (r && !r.contains(e.target)) closePostitDockMenu();
          }
        });
        window.addEventListener('resize', function () {
          if (postitUserLoggedIn() && postitCurrentApp() !== 'login') {
            initPostitDock();
            initPostitsApp();
            layoutHiddenPostits();
          }
        });
      }
    }
    root.style.display = postitDesktopEnabled() ? 'block' : 'none';
    if (!postitDesktopEnabled()) closePostitDockMenu();
    dockLayout();
  }

  function startPostitDrag(e, id) {
    if (e.button !== 0) return;
    if (e.target.closest('button, input, textarea, label, a')) return;
    var el = document.querySelector('.postit[data-id="' + id + '"]');
    if (!el || el.classList.contains('is-hidden')) return;
    var rect = el.getBoundingClientRect();
    _postitDrag = { el: el, id: id, ox: e.clientX - rect.left, oy: e.clientY - rect.top };
    el.style.zIndex = '500';
    document.addEventListener('mousemove', onPostitDragMove);
    document.addEventListener('mouseup', onPostitDragEnd);
  }

  function onPostitDragMove(e) {
    if (!_postitDrag) return;
    _postitDrag.el.style.left = e.clientX - _postitDrag.ox + 'px';
    _postitDrag.el.style.top = e.clientY - _postitDrag.oy + 'px';
  }

  function onPostitDragEnd() {
    if (!_postitDrag) return;
    var x = parseInt(_postitDrag.el.style.left, 10) || 0;
    var y = parseInt(_postitDrag.el.style.top, 10) || 0;
    _postitDrag.el.style.zIndex = '200';
    var pid = _postitDrag.id;
    _postitDrag = null;
    document.removeEventListener('mousemove', onPostitDragMove);
    document.removeEventListener('mouseup', onPostitDragEnd);
    postitApi('/api/postits/' + pid + '/pos', {
      method: 'PATCH',
      body: JSON.stringify({ x: x, y: y }),
    }).catch(function (e) {
      postitToast((e && e.message) || 'Position non enregistrée.', 'danger');
    });
    var p = PostitState.items.find(function (x) {
      return x.id === pid;
    });
    if (p) {
      p.pos_x = x;
      p.pos_y = y;
    }
  }

  async function setPostitHidden(id, hidden) {
    var p = PostitState.items.find(function (x) {
      return x.id === id;
    });
    if (!p) return;
    var el = document.querySelector('.postit[data-id="' + id + '"]');
    if (!el) return;

    if (hidden && !postitIsHidden(p)) {
      var x = parseInt(el.style.left, 10);
      var y = parseInt(el.style.top, 10);
      if (!isNaN(x) && !isNaN(y)) {
        p.pos_x = x;
        p.pos_y = y;
        postitApi('/api/postits/' + id + '/pos', {
          method: 'PATCH',
          body: JSON.stringify({ x: x, y: y }),
        }).catch(function () {});
      }
    }

    try {
      var r = await postitApi('/api/postits/' + id, {
        method: 'PATCH',
        body: JSON.stringify({ hidden: hidden }),
      });
      p.hidden = r && r.hidden != null ? (r.hidden ? 1 : 0) : hidden ? 1 : 0;
      var hideBtn = el.querySelector('.postit-hide-btn');
      if (hideBtn) {
        hideBtn.title = postitIsHidden(p)
          ? 'Afficher à la position enregistrée'
          : 'Réduire en bas de l\'écran';
      }
      dockLayout();
      applyPostitHiddenState(el, p, true);
    } catch (e) {
      postitToast((e && e.message) || 'Modification impossible.', 'danger');
    }
  }

  function togglePostitHidden(id) {
    var p = PostitState.items.find(function (x) {
      return x.id === id;
    });
    if (!p) return;
    setPostitHidden(id, !postitIsHidden(p));
  }

  function restorePostitFromHidden(id) {
    var p = PostitState.items.find(function (x) {
      return x.id === id;
    });
    if (!p || !postitIsHidden(p)) return;
    setPostitHidden(id, false);
  }

  async function togglePostitMultiPage(id) {
    var p = PostitState.items.find(function (x) {
      return x.id === id;
    });
    if (!p) return;
    var next = !p.multi_page;
    try {
      var r = await postitApi('/api/postits/' + id, {
        method: 'PATCH',
        body: JSON.stringify({ multi_page: next }),
      });
      if (r && r.multi_page != null) p.multi_page = r.multi_page ? 1 : 0;
      else p.multi_page = next ? 1 : 0;
      renderPostits();
      postitToast(
        next ? 'Post-it affiché sur toutes les pages.' : 'Post-it limité au portail.',
        'success'
      );
    } catch (e) {
      postitToast((e && e.message) || 'Modification impossible.', 'danger');
    }
  }

  async function deletePostit(id) {
    try {
      await postitApi('/api/postits/' + id, { method: 'DELETE' });
      PostitState.items = PostitState.items.filter(function (p) {
        return p.id !== id;
      });
      renderPostits();
    } catch (e) {
      postitToast((e && e.message) || 'Suppression impossible.', 'danger');
    }
  }

  async function renamePostit(id, title) {
    var t = String(title || '').trim();
    if (!t) {
      postitToast('Titre obligatoire.', 'danger');
      return;
    }
    try {
      await postitApi('/api/postits/' + id, {
        method: 'PATCH',
        body: JSON.stringify({ title: t }),
      });
      var p = PostitState.items.find(function (x) {
        return x.id === id;
      });
      if (p) p.title = t;
    } catch (e) {
      postitToast((e && e.message) || 'Renommage impossible.', 'danger');
    }
  }

  /* ── Éditeur libre : blocs et commandes « / » ──────────────────────────
     Un post-it est une suite de blocs { type, texte, coche, retrait }. Chaque
     bloc est un <textarea> : texte brut, annulation native, aucun HTML à
     assainir. La structure (découper, fusionner, changer de type) redessine
     le corps du post-it et replace le curseur ; la frappe simple ne redessine
     rien. Enregistrement groupé (PATCH { blocs }) après une courte pause. */

  var ED_TYPES = {
    p: { libelle: 'Texte', aide: 'Paragraphe simple', icone: 'Aa', ph: 'Écrire, ou « / » pour les commandes', mots: 'texte paragraphe normal' },
    h1: { libelle: 'Titre 1', aide: 'Grand titre', icone: 'H1', ph: 'Titre 1', mots: 'titre grand h1 #' },
    h2: { libelle: 'Titre 2', aide: 'Titre de section', icone: 'H2', ph: 'Titre 2', mots: 'titre moyen h2 ##' },
    h3: { libelle: 'Titre 3', aide: 'Petit titre', icone: 'H3', ph: 'Titre 3', mots: 'titre petit h3 ###' },
    todo: { libelle: 'Case à cocher', aide: 'Tâche à cocher', icone: '✓', ph: 'À faire', mots: 'tache case cocher todo checkbox liste []' },
    puce: { libelle: 'Liste à puces', aide: 'Liste simple', icone: '•', ph: 'Élément', mots: 'liste puce puces bullet -' },
    num: { libelle: 'Liste numérotée', aide: 'Liste 1, 2, 3', icone: '1.', ph: 'Élément', mots: 'liste numerotee numero ordonnee 1.' },
    citation: { libelle: 'Citation', aide: 'Propos rapporté', icone: '“', ph: 'Citation', mots: 'citation quote >' },
    encadre: { libelle: 'Encadré', aide: 'Texte mis en avant', icone: '!', ph: 'À retenir', mots: 'encadre important callout attention note !' },
    code: { libelle: 'Code', aide: 'Texte à chasse fixe', icone: '</>', ph: 'Code', mots: 'code mono commande ```' },
    sep: { libelle: 'Séparateur', aide: 'Ligne de séparation', icone: '—', ph: '', mots: 'separateur ligne trait diviseur ---' },
  };
  var ED_LISTES = { todo: 1, puce: 1, num: 1 };
  var ED_RETRAIT_MAX = 3;
  var ED_COMMANDES = Object.keys(ED_TYPES)
    .map(function (t) {
      var d = ED_TYPES[t];
      return { cle: t, type: t, libelle: d.libelle, aide: d.aide, icone: d.icone, mots: d.mots };
    })
    .concat([
      { cle: 'date', action: 'date', libelle: 'Date du jour', aide: 'Insère la date', icone: 'J', mots: 'date jour aujourdhui' },
      { cle: 'heure', action: 'heure', libelle: 'Heure', aide: 'Insère l\'heure', icone: 'h', mots: 'heure maintenant' },
      { cle: 'dupliquer', action: 'dupliquer', libelle: 'Dupliquer le bloc', aide: 'Copie juste en dessous', icone: '⧉', mots: 'dupliquer copier' },
      { cle: 'supprimer', action: 'supprimer', libelle: 'Supprimer le bloc', aide: 'Retire ce bloc', icone: '×', mots: 'supprimer effacer retirer' },
    ]);
  /* Raccourcis en début de bloc, validés par une espace. */
  var ED_RACCOURCIS = {
    '#': 'h1', '##': 'h2', '###': 'h3', '-': 'puce', '*': 'puce', '1.': 'num',
    '[]': 'todo', '[ ]': 'todo', '>': 'citation', '!': 'encadre',
  };

  var _edTimers = {};
  var _edSlash = null;
  var _edMesure = null;

  function edBlocs(p) {
    if (!Array.isArray(p.blocs)) p.blocs = [];
    if (!p.blocs.length) p.blocs.push({ type: 'p', texte: '' });
    return p.blocs;
  }

  function edACoche(p) {
    return edBlocs(p).some(function (b) {
      return b.type === 'todo' && b.coche;
    });
  }

  function edNumero(blocs, i) {
    var r = blocs[i].retrait || 0;
    var n = 1;
    for (var j = i - 1; j >= 0; j--) {
      var rj = blocs[j].retrait || 0;
      if (rj > r) continue;
      if (rj < r || blocs[j].type !== 'num') break;
      n++;
    }
    return n;
  }

  function edBlocHtml(p, blocs, i) {
    var b = blocs[i];
    var t = ED_TYPES[b.type] ? b.type : 'p';
    var r = Math.max(0, Math.min(ED_RETRAIT_MAX, b.retrait || 0));
    var cls = 'pb pb-' + t + (t === 'todo' && b.coche ? ' coche' : '');
    var h = '<div class="' + cls + '" data-i="' + i + '" style="--pb-r:' + r + '">';
    if (t === 'sep') return h + '<div class="pb-sep" tabindex="0" aria-label="Séparateur"></div></div>';
    if (t === 'todo') h += '<input type="checkbox" class="pb-case" tabindex="-1"' + (b.coche ? ' checked' : '') + '>';
    else if (t === 'puce') h += '<span class="pb-marque" aria-hidden="true">' + (r % 2 ? '◦' : '•') + '</span>';
    else if (t === 'num') h += '<span class="pb-marque pb-marque-num" aria-hidden="true">' + edNumero(blocs, i) + '.</span>';
    var ph = blocs.length === 1 && t === 'p' ? 'Notes libres — « / » pour insérer un titre, une case…' : ED_TYPES[t].ph;
    h +=
      '<textarea class="pb-txt" rows="1" spellcheck="true" placeholder="' +
      postitEscAttr(ph) +
      '">' +
      postitEscHtml(b.texte || '') +
      '</textarea>';
    return h + '</div>';
  }

  function edBlocsHtml(p) {
    var blocs = edBlocs(p);
    var out = '';
    for (var i = 0; i < blocs.length; i++) out += edBlocHtml(p, blocs, i);
    return out;
  }

  function edCorps(pid) {
    return document.getElementById('postit-body-' + pid);
  }

  function edRedessiner(pid, focusI, pos) {
    var p = postitFindById(pid);
    var body = edCorps(pid);
    if (!p || !body) return;
    body.innerHTML = edBlocsHtml(p);
    fitPostitTaskTextareas(body);
    edMajPied(pid);
    if (focusI != null) edFocus(pid, focusI, pos);
  }

  function edMajPied(pid) {
    var p = postitFindById(pid);
    var el = document.querySelector('.postit[data-id="' + pid + '"]');
    var btn = el && el.querySelector('.postit-clear-btn');
    if (p && btn) btn.hidden = !edACoche(p);
  }

  function edFocus(pid, i, pos) {
    var body = edCorps(pid);
    if (!body) return;
    var row = body.querySelector('.pb[data-i="' + i + '"]');
    if (!row) return;
    var ta = row.querySelector('.pb-txt');
    if (!ta) {
      var sep = row.querySelector('.pb-sep');
      if (sep) sep.focus();
      return;
    }
    ta.focus();
    var n = ta.value.length;
    var at = pos == null || pos < 0 || pos > n ? n : pos;
    try {
      ta.setSelectionRange(at, at);
    } catch (e) {}
  }

  function edCtx(node) {
    var row = node && node.closest && node.closest('.pb');
    var body = node && node.closest && node.closest('.postit-body');
    if (!row || !body) return null;
    var pid = Number(body.dataset.postit);
    var p = postitFindById(pid);
    if (!p) return null;
    var i = Number(row.dataset.i);
    var blocs = edBlocs(p);
    if (!blocs[i]) return null;
    return { pid: pid, p: p, i: i, blocs: blocs, b: blocs[i], row: row };
  }

  function edEnregistrer(pid, immediat) {
    if (_edTimers[pid]) clearTimeout(_edTimers[pid]);
    var envoyer = function () {
      delete _edTimers[pid];
      var p = postitFindById(pid);
      if (!p) return;
      var el = document.querySelector('.postit[data-id="' + pid + '"]');
      if (el && el.classList.contains('is-hidden')) updatePostitPeekVar(el);
      postitApi('/api/postits/' + pid, {
        method: 'PATCH',
        body: JSON.stringify({ blocs: edBlocs(p) }),
        keepalive: !!immediat,
      }).catch(function (e) {
        postitToast((e && e.message) || 'Note non enregistrée.', 'danger');
      });
    };
    if (immediat) envoyer();
    else _edTimers[pid] = setTimeout(envoyer, 700);
  }

  function edToutEnregistrer() {
    Object.keys(_edTimers).forEach(function (pid) {
      edEnregistrer(Number(pid), true);
    });
  }

  /* Ligne visuelle du curseur, mesurée sur un textarea fantôme de même largeur. */
  function edHauteur(ta, texte) {
    if (!_edMesure) {
      _edMesure = document.createElement('textarea');
      _edMesure.setAttribute('aria-hidden', 'true');
      _edMesure.tabIndex = -1;
      document.body.appendChild(_edMesure);
    }
    var cs = getComputedStyle(ta);
    var m = _edMesure.style;
    m.position = 'fixed';
    m.left = '-9999px';
    m.top = '0';
    m.visibility = 'hidden';
    m.overflow = 'hidden';
    m.height = '0';
    m.boxSizing = 'border-box';
    m.width = ta.offsetWidth + 'px';
    ['fontSize', 'fontFamily', 'fontWeight', 'lineHeight', 'letterSpacing', 'paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom', 'whiteSpace', 'wordBreak', 'overflowWrap', 'tabSize'].forEach(function (k) {
      m[k] = cs[k];
    });
    _edMesure.value = texte;
    return _edMesure.scrollHeight;
  }

  function edPremiereLigne(ta) {
    var lh = parseFloat(getComputedStyle(ta).lineHeight) || 18;
    return edHauteur(ta, ta.value.slice(0, ta.selectionStart)) <= edHauteur(ta, '') + lh / 2;
  }

  function edDerniereLigne(ta) {
    var lh = parseFloat(getComputedStyle(ta).lineHeight) || 18;
    return edHauteur(ta, ta.value.slice(0, ta.selectionEnd)) >= edHauteur(ta, ta.value) - lh / 2;
  }

  /* Ligne collée « - truc », « [x] fait », « ## Titre » → bloc typé. */
  function edBlocDepuisLigne(ligne) {
    var m = /^(\s*)(#{1,3}|[-*•]|\d+[.)]|\[[ xX]?\]|>)\s+(.*)$/.exec(ligne);
    if (!m) return { type: 'p', texte: ligne };
    var r = Math.min(ED_RETRAIT_MAX, Math.floor(m[1].replace(/\t/g, '  ').length / 2));
    var k = m[2];
    var b = { texte: m[3] };
    if (k.charAt(0) === '#') b.type = 'h' + k.length;
    else if (/^[-*•]$/.test(k)) b.type = 'puce';
    else if (/^\d/.test(k)) b.type = 'num';
    else if (k === '>') b.type = 'citation';
    else {
      b.type = 'todo';
      b.coche = /x/i.test(k);
    }
    if (r) b.retrait = r;
    return b;
  }

  function edSurCollage(e) {
    var ta = e.target;
    if (!ta.classList || !ta.classList.contains('pb-txt')) return;
    var c = edCtx(ta);
    if (!c || c.b.type === 'code') return;
    var txt = (e.clipboardData && e.clipboardData.getData('text/plain')) || '';
    if (txt.indexOf('\n') < 0) return;
    e.preventDefault();
    var lignes = txt.replace(/\r\n?/g, '\n').split('\n');
    while (lignes.length && !lignes[lignes.length - 1].trim()) lignes.pop();
    if (!lignes.length) return;
    var v = ta.value;
    var avant = v.slice(0, ta.selectionStart);
    var apres = v.slice(ta.selectionEnd);
    if (!avant && c.b.type === 'p') {
      var tete = edBlocDepuisLigne(lignes[0]);
      Object.keys(tete).forEach(function (k) {
        c.b[k] = tete[k];
      });
    } else {
      c.b.texte = avant + lignes[0];
    }
    var nouveaux = lignes.slice(1).map(edBlocDepuisLigne);
    if (nouveaux.length + c.blocs.length > 400) {
      postitToast('Post-it trop long — 400 blocs au plus.', 'danger');
      return;
    }
    var dernier = nouveaux.length ? nouveaux[nouveaux.length - 1] : c.b;
    var pos = dernier.texte.length;
    dernier.texte += apres;
    Array.prototype.splice.apply(c.blocs, [c.i + 1, 0].concat(nouveaux));
    edRedessiner(c.pid, c.i + nouveaux.length, pos);
    edEnregistrer(c.pid);
  }

  function edSurSaisie(e) {
    var ta = e.target;
    if (!ta.classList || !ta.classList.contains('pb-txt')) return;
    var c = edCtx(ta);
    if (!c) return;
    c.b.texte = ta.value;
    autoResizePostitTask(ta);
    var pos = ta.selectionStart;
    if (e.inputType === 'insertText' && e.data === ' ' && c.b.type === 'p') {
      var tete = ta.value.slice(0, pos - 1);
      var t = ED_RACCOURCIS[tete];
      if (t) {
        c.b.type = t;
        c.b.texte = ta.value.slice(pos);
        if (t === 'todo') c.b.coche = false;
        edFermerSlash();
        edRedessiner(c.pid, c.i, 0);
        edEnregistrer(c.pid);
        return;
      }
    }
    if (c.b.type === 'p' && (ta.value === '---' || ta.value === '```')) {
      if (ta.value === '---') {
        c.b.type = 'sep';
        c.b.texte = '';
        c.blocs.splice(c.i + 1, 0, { type: 'p', texte: '' });
        edRedessiner(c.pid, c.i + 1, 0);
      } else {
        c.b.type = 'code';
        c.b.texte = '';
        edRedessiner(c.pid, c.i, 0);
      }
      edEnregistrer(c.pid);
      return;
    }
    if (_edSlash && _edSlash.ta === ta) edMajSlash();
    else if (e.data === '/' && c.b.type !== 'code') {
      var precedent = ta.value.charAt(pos - 2);
      if (pos === 1 || /\s/.test(precedent)) edOuvrirSlash(ta, c.pid, pos - 1);
    }
    edEnregistrer(c.pid);
  }

  function edSurChangement(e) {
    var cb = e.target;
    if (!cb.classList || !cb.classList.contains('pb-case')) return;
    var c = edCtx(cb);
    if (!c) return;
    c.b.coche = !!cb.checked;
    c.row.classList.toggle('coche', c.b.coche);
    edMajPied(c.pid);
    edEnregistrer(c.pid);
  }

  function edSurToucheSep(e, c) {
    var k = e.key;
    if (k === 'Backspace' || k === 'Delete') {
      e.preventDefault();
      c.blocs.splice(c.i, 1);
      edRedessiner(c.pid, Math.max(0, c.i - (k === 'Backspace' ? 1 : 0)), k === 'Backspace' ? -1 : 0);
      edEnregistrer(c.pid);
    } else if (k === 'Enter') {
      e.preventDefault();
      c.blocs.splice(c.i + 1, 0, { type: 'p', texte: '' });
      edRedessiner(c.pid, c.i + 1, 0);
      edEnregistrer(c.pid);
    } else if (k === 'ArrowUp' && c.i > 0) {
      e.preventDefault();
      edFocus(c.pid, c.i - 1, -1);
    } else if (k === 'ArrowDown' && c.i < c.blocs.length - 1) {
      e.preventDefault();
      edFocus(c.pid, c.i + 1, 0);
    }
  }

  function edSurTouche(e) {
    if (e.isComposing) return;
    var t = e.target;
    var c = edCtx(t);
    if (!c) return;
    if (t.classList.contains('pb-sep')) return edSurToucheSep(e, c);
    if (!t.classList.contains('pb-txt')) return;
    if (_edSlash && _edSlash.ta === t && edToucheSlash(e)) return;
    var ta = t;
    var v = ta.value;
    var s = ta.selectionStart;
    var f = ta.selectionEnd;
    var b = c.b;
    var mod = e.metaKey || e.ctrlKey;

    if (e.key === 'Enter' && !e.shiftKey) {
      if (mod && b.type === 'todo') {
        e.preventDefault();
        b.coche = !b.coche;
        edRedessiner(c.pid, c.i, s);
        edEnregistrer(c.pid);
        return;
      }
      if (b.type === 'code' && !mod) return;
      e.preventDefault();
      if (v === '' && ED_LISTES[b.type]) {
        if (b.retrait) b.retrait--;
        else b.type = 'p';
        edRedessiner(c.pid, c.i, 0);
        edEnregistrer(c.pid);
        return;
      }
      var suite = {
        type: ED_LISTES[b.type] ? b.type : 'p',
        texte: v.slice(f),
      };
      if (b.retrait) suite.retrait = b.retrait;
      if (suite.type === 'todo') suite.coche = false;
      if (s === 0 && v !== '') {
        var vide = { type: suite.type, texte: '' };
        if (b.retrait) vide.retrait = b.retrait;
        c.blocs.splice(c.i, 0, vide);
        edRedessiner(c.pid, c.i + 1, 0);
      } else {
        b.texte = v.slice(0, s);
        c.blocs.splice(c.i + 1, 0, suite);
        edRedessiner(c.pid, c.i + 1, 0);
      }
      edEnregistrer(c.pid);
      return;
    }

    if (e.key === 'Backspace' && s === 0 && f === 0) {
      if (b.type !== 'p') {
        e.preventDefault();
        b.type = 'p';
        delete b.coche;
        edRedessiner(c.pid, c.i, 0);
        edEnregistrer(c.pid);
        return;
      }
      if (b.retrait) {
        e.preventDefault();
        b.retrait--;
        edRedessiner(c.pid, c.i, 0);
        edEnregistrer(c.pid);
        return;
      }
      if (c.i === 0) return;
      e.preventDefault();
      var prec = c.blocs[c.i - 1];
      if (prec.type === 'sep') {
        c.blocs.splice(c.i - 1, 1);
        edRedessiner(c.pid, c.i - 1, 0);
      } else {
        var pos = (prec.texte || '').length;
        prec.texte = (prec.texte || '') + v;
        c.blocs.splice(c.i, 1);
        edRedessiner(c.pid, c.i - 1, pos);
      }
      edEnregistrer(c.pid);
      return;
    }

    if (e.key === 'Delete' && s === v.length && f === s && c.i < c.blocs.length - 1) {
      e.preventDefault();
      var suiv = c.blocs[c.i + 1];
      if (suiv.type !== 'sep') b.texte = v + (suiv.texte || '');
      c.blocs.splice(c.i + 1, 1);
      edRedessiner(c.pid, c.i, s);
      edEnregistrer(c.pid);
      return;
    }

    if (e.key === 'Tab') {
      e.preventDefault();
      var r = (b.retrait || 0) + (e.shiftKey ? -1 : 1);
      r = Math.max(0, Math.min(ED_RETRAIT_MAX, r));
      if (r === (b.retrait || 0)) return;
      if (r) b.retrait = r;
      else delete b.retrait;
      edRedessiner(c.pid, c.i, s);
      edEnregistrer(c.pid);
      return;
    }

    if (e.key === 'ArrowUp' && !e.shiftKey && s === f && c.i > 0 && edPremiereLigne(ta)) {
      e.preventDefault();
      edFocus(c.pid, c.i - 1, -1);
      return;
    }
    if (e.key === 'ArrowDown' && !e.shiftKey && s === f && c.i < c.blocs.length - 1 && edDerniereLigne(ta)) {
      e.preventDefault();
      edFocus(c.pid, c.i + 1, 0);
      return;
    }
    if (e.key === 'Escape') ta.blur();
  }

  /* Clic sous le dernier bloc : on reprend l'écriture en bas, comme sur une page. */
  function edSurClicVide(e) {
    var body = e.currentTarget;
    if (e.target !== body) return;
    e.preventDefault();
    var pid = Number(body.dataset.postit);
    var p = postitFindById(pid);
    if (!p) return;
    var blocs = edBlocs(p);
    var der = blocs[blocs.length - 1];
    if (der.type === 'p' && !der.texte) {
      edFocus(pid, blocs.length - 1, 0);
      return;
    }
    blocs.push({ type: 'p', texte: '' });
    edRedessiner(pid, blocs.length - 1, 0);
  }

  function edBrancher(body, p) {
    if (!body) return;
    body.addEventListener('input', edSurSaisie);
    body.addEventListener('keydown', edSurTouche);
    body.addEventListener('change', edSurChangement);
    body.addEventListener('paste', edSurCollage);
    body.addEventListener('mousedown', function (e) {
      e.stopPropagation();
      edSurClicVide(e);
    });
    body.addEventListener('focusout', function (e) {
      var vers = e.relatedTarget;
      if (vers && body.contains(vers)) return;
      if (_edSlash && _edSlash.pid === p.id) edFermerSlash();
      if (_edTimers[p.id]) edEnregistrer(p.id, true);
    });
  }

  /* ── Menu « / » ── */

  function edSansAccent(s) {
    return String(s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '');
  }

  function edMenuSlash() {
    var m = document.getElementById('postit-slash');
    if (!m) {
      m = document.createElement('div');
      m.id = 'postit-slash';
      m.setAttribute('role', 'listbox');
      m.setAttribute('aria-label', 'Insérer un bloc');
      m.addEventListener('mousedown', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var item = e.target.closest('.postit-slash-item');
        if (item && _edSlash) edAppliquerSlash(_edSlash.items[Number(item.dataset.k)]);
      });
      m.addEventListener('mousemove', function (e) {
        var item = e.target.closest('.postit-slash-item');
        if (!item || !_edSlash) return;
        var k = Number(item.dataset.k);
        if (k !== _edSlash.sel) {
          _edSlash.sel = k;
          edDessinerSlash(false);
        }
      });
      document.body.appendChild(m);
    }
    return m;
  }

  function edOuvrirSlash(ta, pid, debut) {
    _edSlash = { ta: ta, pid: pid, debut: debut, sel: 0, items: ED_COMMANDES.slice(), q: '' };
    edMajSlash();
  }

  function edFermerSlash() {
    _edSlash = null;
    var m = document.getElementById('postit-slash');
    if (m) m.classList.remove('open');
  }

  function edMajSlash() {
    var st = _edSlash;
    if (!st) return;
    var ta = st.ta;
    var v = ta.value;
    var pos = ta.selectionStart;
    if (!document.body.contains(ta) || v.charAt(st.debut) !== '/' || pos <= st.debut) return edFermerSlash();
    var q = v.slice(st.debut + 1, pos);
    if (q.length > 24 || /\n/.test(q) || /\s\s/.test(q)) return edFermerSlash();
    var nq = edSansAccent(q.trim());
    st.q = q;
    st.items = ED_COMMANDES.filter(function (cmd) {
      if (!nq) return true;
      return edSansAccent(cmd.libelle + ' ' + cmd.mots).indexOf(nq) >= 0;
    });
    if (!st.items.length && / $/.test(q)) return edFermerSlash();
    if (st.sel >= st.items.length) st.sel = 0;
    edDessinerSlash(true);
  }

  function edDessinerSlash(placer) {
    var st = _edSlash;
    var m = edMenuSlash();
    if (!st) return;
    if (!st.items.length) {
      m.innerHTML = '<div class="postit-slash-vide">Aucune commande pour « ' + postitEscHtml(st.q.trim()) + ' »</div>';
    } else {
      m.innerHTML =
        '<div class="postit-slash-titre">Insérer</div>' +
        st.items
          .map(function (cmd, k) {
            return (
              '<div class="postit-slash-item' +
              (k === st.sel ? ' sel' : '') +
              '" role="option" data-k="' +
              k +
              '"' +
              (k === st.sel ? ' aria-selected="true"' : '') +
              '><span class="postit-slash-ico">' +
              postitEscHtml(cmd.icone) +
              '</span><span class="postit-slash-txt"><b>' +
              postitEscHtml(cmd.libelle) +
              '</b><small>' +
              postitEscHtml(cmd.aide) +
              '</small></span></div>'
            );
          })
          .join('');
    }
    m.classList.add('open');
    var sel = m.querySelector('.postit-slash-item.sel');
    if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest' });
    if (!placer) return;
    var rect = st.ta.getBoundingClientRect();
    var w = 250;
    var h = Math.min(300, m.scrollHeight || 300);
    var left = Math.min(rect.left, window.innerWidth - w - 12);
    var top = rect.bottom + 4;
    if (top + h > window.innerHeight - 12) top = Math.max(12, rect.top - h - 4);
    m.style.left = Math.max(12, left) + 'px';
    m.style.top = top + 'px';
  }

  function edToucheSlash(e) {
    var st = _edSlash;
    if (!st) return false;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!st.items.length) return false;
      e.preventDefault();
      var n = st.items.length;
      st.sel = (st.sel + (e.key === 'ArrowDown' ? 1 : -1) + n) % n;
      edDessinerSlash(false);
      return true;
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      if (!st.items.length) {
        edFermerSlash();
        return false;
      }
      e.preventDefault();
      edAppliquerSlash(st.items[st.sel]);
      return true;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      edFermerSlash();
      return true;
    }
    return false;
  }

  function edAppliquerSlash(cmd) {
    var st = _edSlash;
    if (!st || !cmd) return;
    var c = edCtx(st.ta);
    edFermerSlash();
    if (!c) return;
    var v = st.ta.value;
    var fin = Math.max(st.debut + 1, st.ta.selectionStart);
    var debut = st.debut;
    var reste = v.slice(0, debut) + v.slice(fin);
    var b = c.b;
    b.texte = reste;
    if (cmd.action === 'date' || cmd.action === 'heure') {
      var d = new Date();
      var ins =
        cmd.action === 'date'
          ? d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
          : d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
      b.texte = reste.slice(0, debut) + ins + reste.slice(debut);
      edRedessiner(c.pid, c.i, debut + ins.length);
    } else if (cmd.action === 'dupliquer') {
      c.blocs.splice(c.i + 1, 0, JSON.parse(JSON.stringify(b)));
      edRedessiner(c.pid, c.i + 1, -1);
    } else if (cmd.action === 'supprimer') {
      c.blocs.splice(c.i, 1);
      edRedessiner(c.pid, Math.max(0, c.i - 1), -1);
    } else if (cmd.type === 'sep') {
      if (!reste.trim()) {
        b.type = 'sep';
        b.texte = '';
        delete b.coche;
        c.blocs.splice(c.i + 1, 0, { type: 'p', texte: '' });
      } else {
        c.blocs.splice(c.i + 1, 0, { type: 'sep', texte: '' }, { type: 'p', texte: '' });
      }
      edRedessiner(c.pid, c.i + (reste.trim() ? 2 : 1), 0);
    } else {
      b.type = cmd.type;
      if (cmd.type === 'todo') b.coche = !!b.coche;
      else delete b.coche;
      edRedessiner(c.pid, c.i, debut);
    }
    edEnregistrer(c.pid);
  }

  /* Bouton « / Insérer » du pied : un bloc vide en bas, menu ouvert dessus. */
  function postitOuvrirCommandes(pid) {
    var p = postitFindById(pid);
    if (!p) return;
    var blocs = edBlocs(p);
    var der = blocs[blocs.length - 1];
    if (!(der.type === 'p' && !der.texte)) blocs.push({ type: 'p', texte: '' });
    var i = blocs.length - 1;
    blocs[i].texte = '/';
    edRedessiner(pid, i, 1);
    var ta = edCorps(pid) && edCorps(pid).querySelector('.pb[data-i="' + i + '"] .pb-txt');
    if (ta) edOuvrirSlash(ta, pid, 0);
  }

  async function clearPostitDone(pid) {
    var p = postitFindById(pid);
    if (!p) return;
    p.blocs = edBlocs(p).filter(function (b) {
      return !(b.type === 'todo' && b.coche);
    });
    edRedessiner(pid);
    edEnregistrer(pid, true);
  }

  window.addEventListener('pagehide', edToutEnregistrer);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') edToutEnregistrer();
  });
  window.addEventListener(
    'scroll',
    function () {
      if (_edSlash && !(e.target && e.target.id === 'postit-slash')) edFermerSlash();
    },
    true
  );

  window.PostitState = PostitState;
  window.clearPostitsUi = clearPostitsUi;
  window.initPostitsApp = initPostitsApp;
  window.initPostitDock = initPostitDock;
  window.loadPostits = loadPostits;
  window.renderPostits = renderPostits;
  window.startPostitDrag = startPostitDrag;
  window.togglePostitHidden = togglePostitHidden;
  window.togglePostitColorPalette = togglePostitColorPalette;
  window.openPostitColorPalette = openPostitColorPalette;
  window.setPostitColor = setPostitColor;
  window.closePostitColorPalette = closePostitColorPalette;
  window.restorePostitFromHidden = restorePostitFromHidden;
  window.togglePostitMultiPage = togglePostitMultiPage;
  window.deletePostit = deletePostit;
  window.renamePostit = renamePostit;
  window.postitOuvrirCommandes = postitOuvrirCommandes;
  window.clearPostitDone = clearPostitDone;
  window.autoResizePostitTask = autoResizePostitTask;
  window.layoutHiddenPostits = layoutHiddenPostits;
  window._postitDragCleanup = function () {
    if (!_postitDrag) return;
    document.removeEventListener('mousemove', onPostitDragMove);
    document.removeEventListener('mouseup', onPostitDragEnd);
    _postitDrag = null;
  };

  bindPostitColorPaletteDocClose();
})();
