/* ============================================================
   MySifa — Time picker partagé  (v1.0)
   ------------------------------------------------------------
   Remplace l'<input type="time"> natif, qui affiche « 08:00 AM »
   selon la locale du navigateur, avec un spinner minuscule et
   aucune maîtrise du style.

   Ce composant :
     - garde la valeur au format « HH:MM » (24 h) → el.value
       continue de fonctionner à l'identique côté code appelant ;
     - ouvre un popover 2 colonnes (heures / minutes) + raccourcis ;
     - accepte la saisie clavier libre (« 8 », « 830 », « 8:30 »,
       « 0830 » → 08:30) et normalise au blur / Entrée ;
     - se positionne en position:fixed dans <body> pour ne jamais
       être rogné par l'overflow d'un .modal-body scrollable ;
     - enrichit automatiquement tout input[type="time"] présent ou
       injecté dynamiquement dans le DOM.

   Attributs optionnels sur l'input :
     data-mys-tp-step="15"                → pas de la colonne minutes (défaut 5)
     data-mys-tp-presets="08:00,13:30"    → raccourcis (défaut 08:00,12:00,14:00,17:00)
     data-mys-tp-pair="id-de-l-heure-fin" → sur un champ « début » : décale
                                            automatiquement l'heure de fin en
                                            conservant la durée précédente.

   API : MysTimePicker.enhance(el) / .autoInit(root) / .close()
   ============================================================ */
(function () {
  'use strict';
  if (window.MysTimePicker) return;

  var DEFAULT_STEP = 5;
  var DEFAULT_PRESETS = ['08:00', '12:00', '14:00', '17:00'];
  var ICON = '<span class="mys-tp-ico" aria-hidden="true">' +
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></span>';

  var _pop = null;      // popover unique, réutilisé pour tous les champs
  var _active = null;   // input actuellement rattaché au popover
  var _rafId = 0;

  /* ── Helpers valeur ─────────────────────────────────────── */

  function pad2(n) { n = String(n); return n.length < 2 ? '0' + n : n; }

  /* Parse une saisie humaine en {h, m}, ou null si vide/illisible. */
  function parse(raw) {
    if (raw == null) return null;
    var s = String(raw).trim();
    if (!s) return null;
    var h, mi;
    var m = s.match(/^(\d{1,2})\s*[:hH.,]\s*(\d{0,2})$/);
    if (m) {
      h = parseInt(m[1], 10);
      mi = m[2] === '' ? 0 : parseInt(m[2], 10);
    } else {
      var d = s.replace(/\D/g, '');
      if (!d) return null;
      if (d.length <= 2) { h = parseInt(d, 10); mi = 0; }
      else if (d.length === 3) { h = parseInt(d.slice(0, 1), 10); mi = parseInt(d.slice(1), 10); }
      else { h = parseInt(d.slice(0, 2), 10); mi = parseInt(d.slice(2, 4), 10); }
    }
    if (isNaN(h) || isNaN(mi)) return null;
    if (h > 23) h = 23;
    if (mi > 59) mi = 59;
    return { h: h, m: mi };
  }

  function fmt(o) { return o ? pad2(o.h) + ':' + pad2(o.m) : ''; }
  function norm(raw) { return fmt(parse(raw)); }
  function toMin(o) { return o ? o.h * 60 + o.m : null; }
  function fromMin(t) { t = ((t % 1440) + 1440) % 1440; return pad2(Math.floor(t / 60)) + ':' + pad2(t % 60); }

  function stepOf(el) {
    var s = parseInt(el.getAttribute('data-mys-tp-step') || '', 10);
    return (s >= 1 && s <= 30 && 60 % s === 0) ? s : DEFAULT_STEP;
  }
  function presetsOf(el) {
    var raw = el.getAttribute('data-mys-tp-presets');
    if (!raw) return DEFAULT_PRESETS;
    var out = raw.split(',').map(function (x) { return norm(x); }).filter(Boolean);
    return out.length ? out : DEFAULT_PRESETS;
  }

  /* ── Écriture de la valeur (+ événements + champ apparié) ── */

  /* Pose la valeur et notifie le reste de l'app (input + change),
     exactement comme une saisie utilisateur l'aurait fait. */
  function setValue(el, val, silent) {
    el.value = val;
    el.classList.remove('mys-tp-invalid');
    if (silent) return;
    try {
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (_) { /* navigateurs anciens : pas bloquant */ }
  }

  /* Applique une nouvelle valeur. Sur un champ « début » porteur de
     data-mys-tp-pair, l'heure de fin suit en conservant la durée du créneau
     — même comportement qu'un agenda : déplacer le début déplace la fin.
     Si la fin était vide ou incohérente, on retombe sur 1 h. */
  function commit(el, val) {
    var pairId = el.getAttribute('data-mys-tp-pair');
    var other = pairId ? document.getElementById(pairId) : null;
    var span = 60;
    if (other) {
      var prev = toMin(parse(el.value));
      var pb = toMin(parse(other.value));
      if (prev != null && pb != null && pb - prev > 0) span = pb - prev;
    }
    setValue(el, val);
    if (other) {
      var a = toMin(parse(val));
      if (a != null) setValue(other, fromMin(a + span));
    }
  }

  /* ── Popover ────────────────────────────────────────────── */

  function buildPop() {
    var p = document.createElement('div');
    p.className = 'mys-tp-pop';
    p.setAttribute('role', 'dialog');
    p.setAttribute('aria-label', "Choix de l'heure");
    p.innerHTML =
      '<div class="mys-tp-presets" data-tp="presets"></div>' +
      '<div class="mys-tp-cols">' +
        '<div class="mys-tp-col"><div class="mys-tp-col-hd">Heures</div>' +
          '<div class="mys-tp-scroll" data-tp="h" role="listbox" aria-label="Heures"></div></div>' +
        '<div class="mys-tp-col"><div class="mys-tp-col-hd">Minutes</div>' +
          '<div class="mys-tp-scroll" data-tp="m" role="listbox" aria-label="Minutes"></div></div>' +
      '</div>' +
      '<div class="mys-tp-foot">' +
        '<span class="mys-tp-preview" data-tp="preview">--:--</span>' +
        '<button type="button" class="mys-tp-act" data-tp="clear">Effacer</button>' +
        '<button type="button" class="mys-tp-act primary" data-tp="ok">OK</button>' +
      '</div>';
    // mousedown neutralisé : le focus reste dans l'input, donc pas de
    // blur → pas de fermeture parasite entre le mousedown et le click.
    p.addEventListener('mousedown', function (e) { e.preventDefault(); });
    p.addEventListener('click', onPopClick);
    document.body.appendChild(p);
    return p;
  }

  function renderPop() {
    if (!_pop || !_active) return;
    var cur = parse(_active.value);
    var step = stepOf(_active);
    var q = function (sel) { return _pop.querySelector('[data-tp="' + sel + '"]'); };

    q('presets').innerHTML = presetsOf(_active).map(function (v) {
      var isCur = cur && v === fmt(cur);
      return '<button type="button" class="mys-tp-preset' + (isCur ? ' is-cur' : '') +
             '" data-tp-set="' + v + '">' + v + '</button>';
    }).join('');

    var hs = [];
    for (var h = 0; h < 24; h++) {
      hs.push('<button type="button" class="mys-tp-cell' + (cur && cur.h === h ? ' is-sel' : '') +
              '" role="option" aria-selected="' + (cur && cur.h === h) + '" data-tp-h="' + h + '">' +
              pad2(h) + '</button>');
    }
    q('h').innerHTML = hs.join('');

    var ms = [];
    for (var mi = 0; mi < 60; mi += step) {
      // La cellule est marquée sélectionnée pour l'intervalle qu'elle
      // représente : une valeur tapée « 08:07 » surligne « 05 » sans
      // altérer la valeur réelle du champ.
      var sel = cur && cur.m >= mi && cur.m < mi + step;
      ms.push('<button type="button" class="mys-tp-cell' + (sel ? ' is-sel' : '') +
              '" role="option" aria-selected="' + !!sel + '" data-tp-m="' + mi + '">' +
              pad2(mi) + '</button>');
    }
    q('m').innerHTML = ms.join('');

    q('preview').textContent = cur ? fmt(cur) : '--:--';
    scrollSelIntoView();
  }

  function scrollSelIntoView() {
    if (!_pop) return;
    ['h', 'm'].forEach(function (u) {
      var box = _pop.querySelector('[data-tp="' + u + '"]');
      if (!box) return;
      var sel = box.querySelector('.is-sel');
      if (!sel) { box.scrollTop = 0; return; }
      box.scrollTop = Math.max(0, sel.offsetTop - (box.clientHeight / 2) + (sel.offsetHeight / 2));
    });
  }

  function place() {
    if (!_pop || !_active) return;
    if (!_active.isConnected) { close(); return; }
    var r = _active.getBoundingClientRect();
    var pw = _pop.offsetWidth || 246;
    var ph = _pop.offsetHeight || 300;
    var left = Math.min(Math.max(8, r.left), Math.max(8, window.innerWidth - pw - 8));
    var top = r.bottom + 6;
    if (top + ph > window.innerHeight - 8) {
      var above = r.top - ph - 6;
      top = above >= 8 ? above : Math.max(8, window.innerHeight - ph - 8);
    }
    _pop.style.left = Math.round(left) + 'px';
    _pop.style.top = Math.round(top) + 'px';
  }

  function open(el) {
    if (_active === el && _pop && _pop.classList.contains('open')) return;
    _active = el;
    if (!_pop) _pop = buildPop();
    renderPop();
    _pop.style.visibility = 'hidden';
    _pop.classList.add('open');
    place();
    _pop.style.visibility = '';
    el.closest('.mys-tp')?.classList.add('is-open');
    el.setAttribute('aria-expanded', 'true');
  }

  function close() {
    if (_pop) { _pop.classList.remove('open'); _pop.style.top = '-9999px'; }
    if (_active) {
      try { _active.closest('.mys-tp')?.classList.remove('is-open'); } catch (_) {}
      _active.setAttribute('aria-expanded', 'false');
    }
    _active = null;
  }

  function onPopClick(e) {
    var el = _active;
    if (!el) return;
    var t = e.target.closest('[data-tp-set],[data-tp-h],[data-tp-m],[data-tp="clear"],[data-tp="ok"]');
    if (!t) return;
    e.preventDefault();

    if (t.getAttribute('data-tp') === 'ok') { close(); el.focus(); return; }
    if (t.getAttribute('data-tp') === 'clear') { setValue(el, ''); renderPop(); return; }

    var preset = t.getAttribute('data-tp-set');
    if (preset) { commit(el, preset); renderPop(); close(); el.focus(); return; }

    var cur = parse(el.value) || { h: 8, m: 0 };
    var hAttr = t.getAttribute('data-tp-h');
    if (hAttr !== null) {
      // On reste ouvert après le choix de l'heure : l'utilisateur
      // enchaîne naturellement sur les minutes.
      commit(el, pad2(parseInt(hAttr, 10)) + ':' + pad2(cur.m));
      renderPop();
      return;
    }
    var mAttr = t.getAttribute('data-tp-m');
    if (mAttr !== null) {
      commit(el, pad2(cur.h) + ':' + pad2(parseInt(mAttr, 10)));
      renderPop();
      close();
      el.focus();
    }
  }

  /* ── Clavier / saisie dans le champ ─────────────────────── */

  function onKeyDown(e) {
    var el = e.currentTarget;
    var step = stepOf(el);

    if (e.key === 'Escape') {
      if (_active === el) { e.stopPropagation(); close(); }
      return;
    }
    if (e.key === 'Tab') { close(); return; }
    if (e.key === 'Enter') {
      // Normalise et ferme au lieu de soumettre le formulaire avec une
      // saisie partielle du type « 8 ».
      e.preventDefault();
      var v = norm(el.value);
      if (v !== el.value) commit(el, v);
      close();
      return;
    }
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      e.preventDefault();
      var cur = parse(el.value);
      var base = cur ? toMin(cur) : (e.key === 'ArrowUp' ? 8 * 60 - step : 8 * 60 + step);
      var delta = (e.shiftKey ? 60 : step) * (e.key === 'ArrowUp' ? 1 : -1);
      commit(el, fromMin(base + delta));
      open(el);
      renderPop();
      return;
    }
  }

  function onInput(e) {
    var el = e.currentTarget;
    // Filtre : chiffres, « : » et le « h » de la notation française, 5
    // caractères max. Aucun reformatage pendant la frappe — la normalisation
    // se fait au blur, à Entrée ou à la soumission (« 830 », « 8h30 » → 08:30).
    var clean = String(el.value).replace(/[^\dhH:]/g, '').slice(0, 5);
    if (clean !== el.value) el.value = clean;
    el.classList.toggle('mys-tp-invalid', !!clean && !parse(clean));
    if (_active === el) renderPop();
  }

  function onBlur(e) {
    var el = e.currentTarget;
    var v = norm(el.value);
    if (v !== el.value) {
      if (v) commit(el, v); else setValue(el, '');
    }
    el.classList.remove('mys-tp-invalid');
  }

  /* ── Enrichissement d'un input ──────────────────────────── */

  function enhance(input) {
    if (!input || input.getAttribute('data-mys-tp') === '1') return input;
    if (input.tagName !== 'INPUT') return input;

    var initial = norm(input.value);   // lu AVANT le changement de type
    input.setAttribute('data-mys-tp', '1');

    var wrap = document.createElement('span');
    wrap.className = 'mys-tp';
    if (input.parentNode) input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    wrap.insertAdjacentHTML('beforeend', ICON);

    try { input.type = 'text'; } catch (_) {}
    input.value = initial;
    input.classList.add('mys-tp-input');
    input.setAttribute('inputmode', 'numeric');
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('spellcheck', 'false');
    input.setAttribute('maxlength', '5');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    if (!input.getAttribute('placeholder')) input.setAttribute('placeholder', '--:--');

    input.addEventListener('keydown', onKeyDown);
    input.addEventListener('input', onInput);
    input.addEventListener('blur', onBlur);
    input.addEventListener('focus', function () { open(input); });
    input.addEventListener('click', function () { open(input); });

    // Filet de sécurité : normalise avant soumission, au cas où le champ
    // n'aurait jamais perdu le focus (« 8 » → « 08:00 »).
    var form = input.form || input.closest('form');
    if (form && !form.getAttribute('data-mys-tp-form')) {
      form.setAttribute('data-mys-tp-form', '1');
      form.addEventListener('submit', function () {
        form.querySelectorAll('input[data-mys-tp="1"]').forEach(function (i) {
          var v = norm(i.value);
          if (v !== i.value) setValue(i, v, true);
        });
      }, true);
    }
    return input;
  }

  function autoInit(root) {
    var scope = root || document;
    if (!scope.querySelectorAll) return;
    scope.querySelectorAll('input[type="time"]:not([data-mys-tp])').forEach(enhance);
    // Le scope lui-même peut être l'input (cas d'un nœud ajouté seul).
    if (scope.matches && scope.matches('input[type="time"]:not([data-mys-tp])')) enhance(scope);
  }

  /* ── Handlers globaux ───────────────────────────────────── */

  document.addEventListener('mousedown', function (e) {
    if (!_active) return;
    if (_pop && _pop.contains(e.target)) return;
    if (e.target.closest && e.target.closest('.mys-tp')) return;
    close();
  }, true);

  document.addEventListener('keydown', function (e) {
    // Escape sur le popover ouvert ne doit pas fermer la modale derrière.
    if (e.key === 'Escape' && _active) { e.stopPropagation(); close(); }
  }, true);

  function schedulePlace() {
    if (!_active) return;
    if (_rafId) return;
    _rafId = requestAnimationFrame(function () { _rafId = 0; place(); });
  }
  window.addEventListener('scroll', schedulePlace, true);
  window.addEventListener('resize', schedulePlace);

  /* Enrichit aussi les champs injectés après coup (modales construites
     en innerHTML, formulaires d'alerte, etc.). */
  function startObserver() {
    if (!window.MutationObserver || !document.body) return;
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var added = muts[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var n = added[j];
          if (n.nodeType === 1) autoInit(n);
        }
      }
    }).observe(document.body, { childList: true, subtree: true });
  }

  function boot() { autoInit(document); startObserver(); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  window.MysTimePicker = {
    enhance: enhance,
    autoInit: autoInit,
    close: close,
    parse: parse,
    format: fmt,
    normalize: norm
  };
})();
