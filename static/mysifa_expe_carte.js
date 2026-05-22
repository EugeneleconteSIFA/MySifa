/**
 * MyExpé — widget flottant « Carte de France » (FAB + panneau dock).
 * Logique carte dans EXPE_CARTE_FRANCE_JS (expe_assets) ; ce fichier gère le montage DOM.
 */
(function () {
  'use strict';

  var FAB_ID = 'expe-carte-fab';
  var PANEL_ID = 'expe-carte-panel';
  var BODY_ID = 'expe-carte-panel-body';

  var CARTE_ICO =
    '<span class="expe-carte-fab-icon" role="presentation" aria-hidden="true"></span>';

  function isExpeApp() {
    return (window.__MYSIFA_APP__ || '') === 'expe';
  }

  function panelOpen() {
    var p = document.getElementById(PANEL_ID);
    return !!(p && getComputedStyle(p).display !== 'none');
  }

  function setOpen(open) {
    if (typeof window.setExpeCarteOpen === 'function') {
      window.setExpeCarteOpen(open);
      return;
    }
    var panel = document.getElementById(PANEL_ID);
    var fab = document.getElementById(FAB_ID);
    if (panel) panel.style.display = open ? 'flex' : 'none';
    if (fab) fab.classList.toggle('expe-carte-fab-active', !!open);
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  function mount() {
    if (!isExpeApp()) return;
    if (document.getElementById(FAB_ID)) return;

    var fab = document.createElement('button');
    fab.id = FAB_ID;
    fab.type = 'button';
    fab.className = 'expe-carte-fab mysifa-dock-fab';
    fab.title = 'Carte de France — délais';
    fab.setAttribute('aria-label', 'Carte de France');
    fab.innerHTML = CARTE_ICO;
    fab.addEventListener('click', function () {
      setOpen(!panelOpen());
    });
    document.body.appendChild(fab);

    var panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.className = 'expe-carte-panel mysifa-dock-panel';
    panel.style.display = 'none';

    var head = document.createElement('div');
    head.className = 'mysifa-dock-panel-head';
    var title = document.createElement('span');
    title.className = 'mysifa-dock-panel-title';
    title.textContent = 'Carte de France — délais';
    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'mysifa-dock-panel-close';
    closeBtn.setAttribute('aria-label', 'Fermer');
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', function () {
      setOpen(false);
    });
    head.appendChild(title);
    head.appendChild(closeBtn);
    panel.appendChild(head);

    var body = document.createElement('div');
    body.id = BODY_ID;
    body.className = 'expe-carte-panel-body';
    panel.appendChild(body);

    document.body.appendChild(panel);
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  function unmount() {
    setOpen(false);
    var fab = document.getElementById(FAB_ID);
    var panel = document.getElementById(PANEL_ID);
    if (fab) fab.remove();
    if (panel) panel.remove();
    var tip = document.getElementById('expe-carte-tooltip');
    if (tip) tip.remove();
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  window._expe_carte_mount = mount;
  window._expe_carte_unmount = unmount;
  window.expeCartePanelOpen = panelOpen;
})();
