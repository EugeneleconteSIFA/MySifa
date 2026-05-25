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

  const POSTIT_DOCK_ICON =
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M7 4h10a2 2 0 0 1 2 2v12l-4-4H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M15 4v5h5"/></svg>';

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

  function postitApi(path, options) {
    if (typeof api !== 'function') {
      return Promise.reject(new Error('API indisponible sur cette page.'));
    }
    return api(path, options);
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
    el.className = 'postit';
    el.dataset.id = String(p.id);
    el.dataset.type = p.type;
    el.style.left = (p.pos_x != null ? p.pos_x : 100) + 'px';
    el.style.top = (p.pos_y != null ? p.pos_y : 100) + 'px';
    var tasks = Array.isArray(p.tasks) ? p.tasks : [];
    var hasDone = tasks.some(function (t) {
      return t.done;
    });
    var multiOn = !!p.multi_page;
    var typeLabel = p.type === 'today' ? 'Tâche quotidienne' : 'À faire';
    el.innerHTML =
      '<div class="postit-header" onmousedown="startPostitDrag(event, ' +
      p.id +
      ')">' +
      '<span class="postit-type-label">' +
      postitEscHtml(typeLabel) +
      '</span>' +
      '<input class="postit-title" value="' +
      postitEscAttr(p.title || '') +
      '" onchange="renamePostit(' +
      p.id +
      ', this.value)" onmousedown="event.stopPropagation()">' +
      '<button type="button" class="postit-delete-btn" onclick="deletePostit(' +
      p.id +
      ')" title="Supprimer">×</button></div>' +
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
    return el;
  }

  function renderPostits() {
    var layer = ensurePostitLayer();
    if (!layer) return;
    layer.querySelectorAll('.postit').forEach(function (el) {
      el.remove();
    });
    postitsForCurrentPage().forEach(function (p) {
      layer.appendChild(buildPostitEl(p));
    });
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
          if (!_postitDockMenuOpen) return;
          var r = document.getElementById('postit-dock-root');
          if (r && !r.contains(e.target)) closePostitDockMenu();
        });
        window.addEventListener('resize', function () {
          if (postitUserLoggedIn() && postitCurrentApp() !== 'login') {
            initPostitDock();
            initPostitsApp();
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
    if (!el) return;
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
        var textareas = body && body.querySelectorAll('.postit-task-text');
        var last = textareas && textareas[textareas.length - 1];
        if (last) {
          last.focus();
          autoResizePostitTask(last);
        }
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

  function autoResizePostitTask(el) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  window.PostitState = PostitState;
  window.initPostitsApp = initPostitsApp;
  window.initPostitDock = initPostitDock;
  window.loadPostits = loadPostits;
  window.renderPostits = renderPostits;
  window.startPostitDrag = startPostitDrag;
  window.togglePostitMultiPage = togglePostitMultiPage;
  window.deletePostit = deletePostit;
  window.renamePostit = renamePostit;
  window.addPostitTask = addPostitTask;
  window.togglePostitTask = togglePostitTask;
  window.editPostitTask = editPostitTask;
  window.deletePostitTask = deletePostitTask;
  window.clearPostitDone = clearPostitDone;
  window.autoResizePostitTask = autoResizePostitTask;
  window._postitDragCleanup = function () {
    if (!_postitDrag) return;
    document.removeEventListener('mousemove', onPostitDragMove);
    document.removeEventListener('mouseup', onPostitDragEnd);
    _postitDrag = null;
  };
})();
