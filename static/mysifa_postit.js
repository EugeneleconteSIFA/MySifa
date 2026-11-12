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
      ')" title="Retirer de l\'écran — la note reste dans Mes notes">×</button></div></div>' +
      '<div class="postit-body" id="postit-body-' +
      p.id +
      '" data-postit="' +
      p.id +
      '"></div>' +
      '<div class="postit-footer" onmousedown="startPostitDrag(event, ' +
      p.id +
      ')">' +
      '<button type="button" class="postit-add-task-btn" onclick="postitOuvrirCommandes(' +
      p.id +
      ')" title="Ajouter un bloc — ou taper « / » dans le texte">/ Insérer</button>' +
      '<a class="postit-ouvrir-btn" href="/note?note=' +
      p.id +
      '" onmousedown="event.stopPropagation()" title="Ouvrir dans Mes notes, en pleine page">Ouvrir ↗</a>' +
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
      ' hidden' +
      '>Effacer cochées</button>' +
      '</div>';
    applyPostitColor(el, postitResolveColor(p));
    setupPostitColorDot(el, p.id);
    setupPostitInteractions(el, p);
    setupPostitResize(el, p);
    postitMonterEditeur(el.querySelector('.postit-body'), p);
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


  function renderPostits() {
    closePostitColorPalette();
    var layer = ensurePostitLayer();
    if (!layer) return;
    Object.keys(_editeurs).forEach(function (k) {
      _editeurs[k].detruire();
      delete _editeurs[k];
    });
    layer.querySelectorAll('.postit').forEach(function (el) {
      el.remove();
    });
    postitsForCurrentPage().forEach(function (p) {
      var el = buildPostitEl(p);
      layer.appendChild(el);
      if (_editeurs[p.id]) _editeurs[p.id].ajuster();
      applyPostitHiddenState(el, p, false);
    });
    layoutHiddenPostits();
  }

  async function loadPostits() {
    try {
      await postitChargerEditeur();
      var data = await postitApi('/api/postits?ecran=1');
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

  async function addPostit() {
    var blocs = [{ type: 'p', texte: '' }];
    closePostitDockMenu();
    try {
      await postitChargerEditeur();
      var p = await postitApi('/api/postits', {
        method: 'POST',
        body: JSON.stringify({ type: 'someday', title: 'Note', blocs: blocs, sur_ecran: 1 }),
      });
      if (!p) return;
      if (!Array.isArray(p.blocs) || !p.blocs.length) p.blocs = blocs;
      PostitState.items.push(p);
      renderPostits();
      requestAnimationFrame(function () {
        if (_editeurs[p.id]) _editeurs[p.id].focus(0, 0);
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
        '<button type="button" class="postit-dock-menu-btn someday" role="menuitem" data-action="note">Note libre</button>' +
        '<a class="postit-dock-menu-btn today" role="menuitem" href="/note" data-action="notes">Mes notes</a>' +
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
            if (b.dataset.action === 'notes') {
              closePostitDockMenu();
              return;
            }
            addPostit();
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

  /* × d'un post-it : il quitte l'écran, la note reste dans Mes notes (/note). */
  async function deletePostit(id) {
    if (_editeurs[id]) _editeurs[id].vider();
    try {
      await postitApi('/api/postits/' + id, {
        method: 'PATCH',
        body: JSON.stringify({ sur_ecran: false }),
      });
      PostitState.items = PostitState.items.filter(function (p) {
        return p.id !== id;
      });
      renderPostits();
      postitToast('Note rangée dans Mes notes.', 'success');
    } catch (e) {
      postitToast((e && e.message) || 'Modification impossible.', 'danger');
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

  /* ── Éditeur de blocs : static/mysifa_notes_editeur.js, commun avec /note ──
     Chargé à la demande : aucune page n'a à l'inclure. Changer l'éditeur
     impose d'incrémenter ces deux ?v= ET celui de mysifa_postit.js. */
  var NTED_JS = '/static/mysifa_notes_editeur.js?v=6';
  var NTED_CSS = '/static/mysifa_notes_editeur.css?v=3';
  var _edPret = null;
  var _editeurs = {};

  function postitChargerEditeur() {
    if (window.MySifaNotesEditeur) return Promise.resolve();
    if (_edPret) return _edPret;
    if (!document.querySelector('link[data-nted]')) {
      var l = document.createElement('link');
      l.rel = 'stylesheet';
      l.href = NTED_CSS;
      l.setAttribute('data-nted', '1');
      document.head.appendChild(l);
    }
    _edPret = new Promise(function (ok, ko) {
      var sc = document.createElement('script');
      sc.src = NTED_JS;
      sc.onload = function () {
        ok();
      };
      sc.onerror = function () {
        _edPret = null;
        ko(new Error('Éditeur de notes indisponible.'));
      };
      document.head.appendChild(sc);
    });
    return _edPret;
  }

  function postitMonterEditeur(body, p) {
    if (!body || !window.MySifaNotesEditeur) return;
    if (_editeurs[p.id]) _editeurs[p.id].detruire();
    _editeurs[p.id] = window.MySifaNotesEditeur.monter(body, p, {
      noteId: p.id,
      /* Note partagée : on suit en direct ce que les autres y écrivent. */
      flux: !!p.partagee,
      placeholder: 'Notes libres — « / » pour insérer un titre, une case…',
      recharger: function () {
        postitApi('/api/postits/' + p.id).then(function (n) {
          if (n && _editeurs[p.id]) _editeurs[p.id].remplacer(n);
        }).catch(function () {});
      },
      surChange: function (ed) {
        var el = document.querySelector('.postit[data-id="' + p.id + '"]');
        if (!el) return;
        var btn = el.querySelector('.postit-clear-btn');
        if (btn) btn.hidden = !ed.aCoche();
        if (el.classList.contains('is-hidden')) updatePostitPeekVar(el);
      },
      creerSousPage: function () {
        return postitApi('/api/postits', {
          method: 'POST',
          body: JSON.stringify({ type: 'someday', title: 'Sans titre', parent_id: p.id, sur_ecran: 0 }),
        }).catch(function (e) {
          postitToast((e && e.message) || 'Création impossible.', 'danger');
        });
      },
      signaler: function (msg, type) {
        postitToast(msg, type || 'danger');
      },
    });
    var btn = body.parentNode && body.parentNode.querySelector('.postit-clear-btn');
    if (btn) btn.hidden = !_editeurs[p.id].aCoche();
  }

  /* Bouton « / Insérer » du pied : un bloc vide en bas, menu ouvert dessus. */
  function postitOuvrirCommandes(pid) {
    if (_editeurs[pid]) _editeurs[pid].ouvrirCommandes();
  }

  function clearPostitDone(pid) {
    if (_editeurs[pid]) _editeurs[pid].effacerCochees();
  }

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
  window.layoutHiddenPostits = layoutHiddenPostits;
  window._postitDragCleanup = function () {
    if (!_postitDrag) return;
    document.removeEventListener('mousemove', onPostitDragMove);
    document.removeEventListener('mouseup', onPostitDragEnd);
    _postitDrag = null;
  };

  bindPostitColorPaletteDocClose();
})();
