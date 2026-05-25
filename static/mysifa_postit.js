/**
 * MySifa — Post-its (portail + toutes les pages applicatives si multi-page activé).
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
    '<path d="M7 4h10a2 2 0 0 1 2 2v12l-4-4H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M15 4v5h5"/></svg>';

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
    document.addEventListener('click', function (e) {
      var pal = document.getElementById('postit-color-palette');
      if (
        pal &&
        pal.classList.contains('open') &&
        !pal.contains(e.target) &&
        !e.target.closest('.postit-color-dot')
      ) {
        closePostitColorPalette();
      }
    });
  }

  function ensurePostitColorPalette() {
    bindPostitColorPaletteDocClose();
    var pal = document.getElementById('postit-color-palette');
    if (pal) {
      pal.style.zIndex = String(POSTIT_COLOR_PALETTE_Z);
      return pal;
    }
    pal = document.createElement('div');
    pal.id = 'postit-color-palette';
    pal.style.zIndex = String(POSTIT_COLOR_PALETTE_Z);
    pal.setAttribute('role', 'menu');
    pal.setAttribute('aria-label', 'Couleur du post-it');
    POSTIT_COLOR_PALETTE.forEach(function (hex) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'postit-color-swatch';
      btn.style.background = hex;
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
    });
    document.body.appendChild(pal);
    return pal;
  }

  function closePostitColorPalette() {
    var pal = document.getElementById('postit-color-palette');
    if (pal) {
      pal.classList.remove('open');
      pal.dataset.postitId = '';
    }
    _postitColorPaletteOpen = null;
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
    e.stopPropagation();
    e.preventDefault();
    if (_postitColorPaletteOpen === id) {
      closePostitColorPalette();
      return;
    }
    closePostitDockMenu();
    var el = document.querySelector('.postit[data-id="' + id + '"]');
    if (!el) return;
    var dot = el.querySelector('.postit-color-dot');
    if (!dot) return;
    var p = PostitState.items.find(function (x) {
      return x.id === id;
    });
    var color = postitResolveColor(p);
    var pal = ensurePostitColorPalette();
    pal.dataset.postitId = String(id);
    updatePostitColorPaletteActive(color);
    positionPostitColorPalette(dot);
    pal.classList.add('open');
    _postitColorPaletteOpen = id;
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
    return { left: 16, right: vw - 220, top: vh - 66, width: vw - 236 };
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
    var top = band.top;
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

  function buildPostitTaskHtml(postitId, t) {
    var done = !!t.done;
    return (
      '<div class="postit-task' +
      (done ? ' done' : '') +
      '" data-task-id="' +
      t.id +
      '">' +
      '<input type="checkbox" ' +
      (done ? 'checked' : '') +
      ' onchange="togglePostitTask(' +
      postitId +
      ', ' +
      t.id +
      ', this.checked)">' +
      '<textarea class="postit-task-text" rows="1" onchange="editPostitTask(' +
      postitId +
      ', ' +
      t.id +
      ', this.value)" onmousedown="event.stopPropagation()" onfocus="autoResizePostitTask(this)" oninput="autoResizePostitTask(this)">' +
      postitEscHtml(t.text || '') +
      '</textarea>' +
      '<button type="button" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px;padding:0 2px" onclick="deletePostitTask(' +
      postitId +
      ', ' +
      t.id +
      ')" title="Supprimer">×</button></div>'
    );
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
    var tasks = Array.isArray(p.tasks) ? p.tasks : [];
    var hasDone = tasks.some(function (t) {
      return t.done;
    });
    var multiOn = !!p.multi_page;
    var hideTitle = postitIsHidden(p)
      ? 'Afficher à la position enregistrée'
      : 'Réduire en bas de l\'écran';
    el.innerHTML =
      '<div class="postit-header" onmousedown="startPostitDrag(event, ' +
      p.id +
      ')">' +
      '<button type="button" class="postit-color-dot" onmousedown="event.stopPropagation()" onclick="event.stopPropagation(); togglePostitColorPalette(event, ' +
      p.id +
      ')" title="Changer la couleur" aria-label="Changer la couleur"></button>' +
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
      '">' +
      tasks.map(function (t) {
        return buildPostitTaskHtml(p.id, t);
      }).join('') +
      '</div>' +
      '<div class="postit-footer">' +
      '<button type="button" class="postit-add-task-btn" onclick="addPostitTask(' +
      p.id +
      ')">+ Ajouter</button>' +
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
      (hasDone
        ? '<button type="button" class="postit-clear-btn" onclick="clearPostitDone(' +
          p.id +
          ')">Effacer terminées</button>'
        : '') +
      '</div>';
    applyPostitColor(el, postitResolveColor(p));
    setupPostitInteractions(el, p);
    return el;
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
    root.querySelectorAll('.postit-task-text').forEach(function (ta) {
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

  function initPostitsApp() {
    bindPostitColorPaletteDocClose();
    if (!postitUserLoggedIn() || postitCurrentApp() === 'login') return;
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
    var title = type === 'today' ? 'Post-it tâche quotidienne' : 'Post-it à faire';
    closePostitDockMenu();
    try {
      var p = await postitApi('/api/postits', {
        method: 'POST',
        body: JSON.stringify({ type: type, title: title }),
      });
      if (!p) return;
      PostitState.items.push(Object.assign({}, p, { tasks: [] }));
      renderPostits();
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
        '<button type="button" class="postit-dock-menu-btn someday" role="menuitem">Post-it à faire</button>' +
        '<button type="button" class="postit-dock-menu-btn today" role="menuitem">Post-it tâche quotidienne</button>' +
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

  async function addPostitTask(postitId) {
    try {
      var task = await postitApi('/api/postits/' + postitId + '/tasks', {
        method: 'POST',
        body: JSON.stringify({ text: '' }),
      });
      if (!task) return;
      var p = PostitState.items.find(function (x) {
        return x.id === postitId;
      });
      if (p) {
        if (!Array.isArray(p.tasks)) p.tasks = [];
        p.tasks.push(task);
      }
      renderPostits();
      requestAnimationFrame(function () {
        var body = document.getElementById('postit-body-' + postitId);
        if (!body) return;
        fitPostitTaskTextareas(body);
        var textareas = body.querySelectorAll('.postit-task-text');
        var last = textareas[textareas.length - 1];
        if (last) last.focus();
      });
    } catch (e) {
      postitToast((e && e.message) || 'Ajout de tâche impossible.', 'danger');
    }
  }

  async function togglePostitTask(postitId, taskId, done) {
    try {
      await postitApi('/api/postits/' + postitId + '/tasks/' + taskId, {
        method: 'PATCH',
        body: JSON.stringify({ done: done ? 1 : 0 }),
      });
      var p = PostitState.items.find(function (x) {
        return x.id === postitId;
      });
      var t = p && p.tasks && p.tasks.find(function (x) {
        return x.id === taskId;
      });
      if (t) t.done = done ? 1 : 0;
      renderPostits();
    } catch (e) {
      postitToast((e && e.message) || 'Mise à jour impossible.', 'danger');
    }
  }

  async function editPostitTask(postitId, taskId, text) {
    try {
      await postitApi('/api/postits/' + postitId + '/tasks/' + taskId, {
        method: 'PATCH',
        body: JSON.stringify({ text: text }),
      });
      var p = PostitState.items.find(function (x) {
        return x.id === postitId;
      });
      var t = p && p.tasks && p.tasks.find(function (x) {
        return x.id === taskId;
      });
      if (t) t.text = text;
      var el = document.querySelector('.postit[data-id="' + postitId + '"]');
      if (el && el.classList.contains('is-hidden')) updatePostitPeekVar(el);
    } catch (e) {
      postitToast((e && e.message) || 'Modification impossible.', 'danger');
    }
  }

  async function deletePostitTask(postitId, taskId) {
    try {
      await postitApi('/api/postits/' + postitId + '/tasks/' + taskId, { method: 'DELETE' });
      var p = PostitState.items.find(function (x) {
        return x.id === postitId;
      });
      if (p && p.tasks) {
        p.tasks = p.tasks.filter(function (t) {
          return t.id !== taskId;
        });
      }
      renderPostits();
    } catch (e) {
      postitToast((e && e.message) || 'Suppression impossible.', 'danger');
    }
  }

  async function clearPostitDone(postitId) {
    try {
      await postitApi('/api/postits/' + postitId + '/tasks/done/clear', { method: 'DELETE' });
      var p = PostitState.items.find(function (x) {
        return x.id === postitId;
      });
      if (p && p.tasks) {
        p.tasks = p.tasks.filter(function (t) {
          return !t.done;
        });
      }
      renderPostits();
    } catch (e) {
      postitToast((e && e.message) || 'Effacement impossible.', 'danger');
    }
  }

  window.PostitState = PostitState;
  window.initPostitsApp = initPostitsApp;
  window.initPostitDock = initPostitDock;
  window.loadPostits = loadPostits;
  window.renderPostits = renderPostits;
  window.startPostitDrag = startPostitDrag;
  window.togglePostitHidden = togglePostitHidden;
  window.togglePostitColorPalette = togglePostitColorPalette;
  window.setPostitColor = setPostitColor;
  window.closePostitColorPalette = closePostitColorPalette;
  window.restorePostitFromHidden = restorePostitFromHidden;
  window.togglePostitMultiPage = togglePostitMultiPage;
  window.deletePostit = deletePostit;
  window.renamePostit = renamePostit;
  window.addPostitTask = addPostitTask;
  window.togglePostitTask = togglePostitTask;
  window.editPostitTask = editPostitTask;
  window.deletePostitTask = deletePostitTask;
  window.clearPostitDone = clearPostitDone;
  window.autoResizePostitTask = autoResizePostitTask;
  window.layoutHiddenPostits = layoutHiddenPostits;
  window._postitDragCleanup = function () {
    if (!_postitDrag) return;
    document.removeEventListener('mousemove', onPostitDragMove);
    document.removeEventListener('mouseup', onPostitDragEnd);
    _postitDrag = null;
  };
})();
