/**
 * MySifa — Calculette flottante (style aligné messagerie / agent IA).
 */
(function () {
  'use strict';

  var _open = false;
  var _expr = '';
  var _val = '0';
  var _justEq = false;

  var CALC_ICO =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<rect x="4" y="2" width="16" height="20" rx="2"/>' +
    '<line x1="8" y1="6" x2="16" y2="6"/>' +
    '<circle cx="8.5" cy="11" r=".8" fill="currentColor" stroke="none"/>' +
    '<circle cx="12" cy="11" r=".8" fill="currentColor" stroke="none"/>' +
    '<circle cx="15.5" cy="11" r=".8" fill="currentColor" stroke="none"/>' +
    '<circle cx="8.5" cy="15" r=".8" fill="currentColor" stroke="none"/>' +
    '<circle cx="12" cy="15" r=".8" fill="currentColor" stroke="none"/>' +
    '<circle cx="15.5" cy="15" r=".8" fill="currentColor" stroke="none"/>' +
    '<line x1="8" y1="19" x2="16" y2="19"/></svg>';

  var KEYS = [
    ['C', '⌫', '%', '÷'],
    ['7', '8', '9', '×'],
    ['4', '5', '6', '−'],
    ['1', '2', '3', '+'],
    ['0', '.', '='],
  ];

  function press(k) {
    if (k === 'C') {
      _expr = '';
      _val = '0';
      _justEq = false;
      return;
    }
    if (k === '⌫') {
      _val = _val.length > 1 ? _val.slice(0, -1) : '0';
      return;
    }
    if (k === '±') {
      _val = _val.startsWith('-') ? _val.slice(1) : '-' + _val;
      return;
    }
    if (k === '%') {
      try {
        _val = String(parseFloat(_val) / 100);
      } catch (e) {}
      return;
    }
    if (k === '=') {
      try {
        var expr = (_justEq ? _val : _expr + _val)
          .replace(/÷/g, '/')
          .replace(/×/g, '*')
          .replace(/−/g, '-');
        var r = Function('"use strict";return (' + expr + ')')();
        _expr = expr + '=';
        _val = String(Math.round(r * 1e10) / 1e10);
        _justEq = true;
      } catch (e) {
        _val = 'Err';
        _expr = '';
        _justEq = false;
      }
      return;
    }
    if (['+', '-', '×', '÷', '−'].indexOf(k) >= 0) {
      if (_justEq) {
        _expr = _val + k;
        _val = '0';
        _justEq = false;
        return;
      }
      _expr += _val + k;
      _val = '0';
      return;
    }
    if (_justEq) {
      _expr = '';
      _justEq = false;
    }
    if (k === '.') {
      if (_val.indexOf('.') >= 0) return;
      _val += '.';
      return;
    }
    _val = _val === '0' || _val === '-0' ? (_val.startsWith('-') ? '-' + k : k) : _val + k;
  }

  function render() {
    var panel = document.getElementById('_calc_panel');
    if (!panel) return;
    panel.style.display = _open ? '' : 'none';
    var cv = panel.querySelector('._cv');
    var ce = panel.querySelector('._ce');
    if (cv) cv.textContent = _val;
    if (ce) ce.textContent = _expr;
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  function setOpen(v) {
    _open = !!v;
    var fab = document.getElementById('_calc_fab');
    if (fab) fab.classList.toggle('calc-fab-active', _open);
    render();
  }

  function mount() {
    if (document.getElementById('_calc_fab')) return;

    var fab = document.createElement('button');
    fab.id = '_calc_fab';
    fab.type = 'button';
    fab.className = 'calc-fab mysifa-dock-fab';
    fab.title = 'Calculette';
    fab.setAttribute('aria-label', 'Calculette');
    fab.innerHTML = CALC_ICO;
    fab.addEventListener('click', function () {
      setOpen(!_open);
    });
    document.body.appendChild(fab);

    var panel = document.createElement('div');
    panel.id = '_calc_panel';
    panel.className = 'calc-panel mysifa-dock-panel';
    panel.style.display = 'none';

    var head = document.createElement('div');
    head.className = 'mysifa-dock-panel-head';
    var title = document.createElement('span');
    title.className = 'mysifa-dock-panel-title';
    title.textContent = 'Calculette';
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
    body.className = 'calc-panel-body';

    var disp = document.createElement('div');
    disp.className = 'calc-display';
    var ce = document.createElement('div');
    ce.className = 'calc-expr _ce';
    var cv = document.createElement('div');
    cv.className = 'calc-val _cv';
    cv.textContent = '0';
    disp.appendChild(ce);
    disp.appendChild(cv);
    body.appendChild(disp);

    var grid = document.createElement('div');
    grid.className = 'calc-grid';
    KEYS.forEach(function (row) {
      row.forEach(function (k) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className =
          'calc-key' +
          (k === '='
            ? ' eq'
            : ['+', '-', '×', '÷', '−'].indexOf(k) >= 0
              ? ' op'
              : ['C', '⌫', '%', '±'].indexOf(k) >= 0
                ? ' fn'
                : '');
        btn.textContent = k;
        if (k === '0') btn.style.gridColumn = 'span 2';
        btn.addEventListener('click', function () {
          press(k);
          render();
        });
        grid.appendChild(btn);
      });
    });
    body.appendChild(grid);
    panel.appendChild(body);
    document.body.appendChild(panel);

    document.addEventListener('keydown', function (e) {
      if (!_open) return;
      if (e.key >= '0' && e.key <= '9') {
        press(e.key);
        render();
      } else if (e.key === '.') {
        press('.');
        render();
      } else if (e.key === '+' || e.key === '-') {
        press(e.key === '+' ? '+' : '−');
        render();
      } else if (e.key === '*') {
        press('×');
        render();
      } else if (e.key === '/') {
        e.preventDefault();
        press('÷');
        render();
      } else if (e.key === 'Enter' || e.key === '=') {
        press('=');
        render();
      } else if (e.key === 'Escape') {
        setOpen(false);
      } else if (e.key === 'Backspace') {
        press('⌫');
        render();
      }
    });
  }

  function unmount() {
    var fab = document.getElementById('_calc_fab');
    var panel = document.getElementById('_calc_panel');
    if (fab) fab.remove();
    if (panel) panel.remove();
    _open = false;
    if (window.MySifaDock && typeof window.MySifaDock.layout === 'function') {
      window.MySifaDock.layout();
    }
  }

  window._calc_mount = mount;
  window._calc_unmount = unmount;
})();
