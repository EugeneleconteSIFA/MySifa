/* MySifa — Bandeau "Simuler service" & retour prod
 * Module self-contained : injecte lui-même son CSS et son markup si absents.
 * Suffit d'inclure <script src="/static/mysifa_impersonate.js"></script> sur
 * n'importe quelle page (portail, MyProd standalone, MyStock, planning, etc.)
 *
 * Comportement :
 *  - v1 : bandeau rouge visible pour tous, avec bouton "Aller sur MySifa - prod"
 *  - v1 + superadmin : sélecteur de rôle/machine à droite
 *  - prod + superadmin : bandeau indigo léger avec sélecteur
 *  - prod + utilisateur normal : rien
 *  - Impersonation active : bandeau ambre + bouton "Revenir superadmin"
 *
 * Backend : POST/DELETE /api/impersonate (cookie sifa_impersonate).
 * Recharge la page après un changement pour repartir sur le rôle effectif.
 */
(function () {
  'use strict';

  var PROD_URL = 'https://www.mysifa.com';

  var ROLE_LABELS = {
    fabrication: 'Fabrication',
    logistique: 'Logistique',
    commercial: 'Commercial',
    administration: 'Administration',
    direction: 'Direction',
    comptabilite: 'Comptabilité',
    expedition: 'Expédition'
  };
  var ROLES_ORDER = [
    'fabrication', 'logistique', 'commercial', 'administration', 'administration_ventes', 'administration_technique',
    'direction', 'comptabilite', 'expedition'
  ];

  // ── Détection env (URL + variable serveur) ─────────────────────────
  function detectEnv() {
    var v = (typeof window !== 'undefined' && window.__MYSIFA_ENV__) || null;
    if (v) return String(v).toLowerCase();
    var host = (typeof window !== 'undefined' && window.location && window.location.hostname) || '';
    return /^v1\./i.test(host) ? 'v1' : 'v2';
  }

  var state = {
    env: detectEnv(),
    machines: [],
    user: null
  };

  function isStaging() { return state.env === 'v1'; }

  function isRealSuperadmin(u) {
    if (!u) return false;
    return (u.real_role || u.role) === 'superadmin';
  }

  function $(id) { return document.getElementById(id); }

  // ── Injection CSS (idempotent) ─────────────────────────────────────
  function ensureCss() {
    if (document.getElementById('msf-imp-css')) return;
    var css = ''
      + '.staging-bandeau{position:fixed;top:0;left:0;right:0;height:24px;background:#dc2626;color:#fff;'
      +   'font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;'
      +   'display:flex;align-items:center;justify-content:center;gap:10px;'
      +   'z-index:9999;font-family:"Segoe UI",system-ui,sans-serif;'
      +   'box-shadow:0 1px 6px rgba(220,38,38,.4);padding:0 12px}'
      + '.staging-bandeau::before{content:"●";color:#fef2f2;font-size:9px;line-height:1}'
      + '.staging-bandeau[hidden]{display:none}'
      + '.staging-bandeau.env-prod{background:#4f46e5;box-shadow:0 1px 6px rgba(79,70,229,.4)}'
      + '.staging-bandeau.env-prod::before{content:"●";color:#e0e7ff}'
      + '.staging-bandeau.impersonating{background:#d97706;box-shadow:0 1px 6px rgba(217,119,6,.4)}'
      + '.staging-bandeau.impersonating::before{content:"●";color:#fef3c7}'
      + '.staging-bandeau .msf-imp-msg{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
      + '.staging-bandeau .msf-imp-actions{margin-left:auto;display:flex;align-items:center;gap:6px;text-transform:none;letter-spacing:0;font-weight:600}'
      + '.staging-bandeau .msf-imp-slot{display:flex;align-items:center;gap:6px}'
      + '.staging-bandeau .msf-imp-actions a,.staging-bandeau .msf-imp-actions button{background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.45);'
      +   'border-radius:6px;padding:2px 10px;font-size:11px;font-family:inherit;font-weight:700;line-height:16px;height:20px;cursor:pointer;text-transform:uppercase;letter-spacing:.5px;text-decoration:none;display:inline-flex;align-items:center}'
      + '.staging-bandeau .msf-imp-actions a:hover,.staging-bandeau .msf-imp-actions button:hover{background:rgba(255,255,255,.32)}'
      + '.staging-bandeau .msf-imp-slot select{background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.35);'
      +   'border-radius:6px;padding:2px 6px;font-size:11px;font-family:inherit;font-weight:600;line-height:16px;height:20px;cursor:pointer}'
      + '.staging-bandeau .msf-imp-slot select option{color:#111827;background:#fff}'
      + '.staging-bandeau .msf-imp-actions .msf-imp-stop{background:#fff;color:#b45309}'
      + '.staging-bandeau .msf-imp-actions .msf-imp-stop:hover{background:#fef3c7}'
      + '@media (max-width:640px){'
      +   '.staging-bandeau{font-size:10px;gap:6px;padding:0 6px}'
      +   '.staging-bandeau .msf-imp-slot select{max-width:110px}'
      + '}'
      + 'body.has-staging-bandeau{padding-top:24px}'
      + 'body.has-staging-bandeau .sidebar{height:calc(100vh - 24px);top:24px}'
      + 'body.has-staging-bandeau .mobile-topbar{top:24px}';
    var s = document.createElement('style');
    s.id = 'msf-imp-css';
    s.textContent = css;
    document.head.appendChild(s);
  }

  // ── Injection du markup bandeau si absent ──────────────────────────
  function ensureBandeauDom() {
    if ($('msf-staging-bandeau')) return;
    var div = document.createElement('div');
    div.className = 'staging-bandeau';
    div.id = 'msf-staging-bandeau';
    div.setAttribute('hidden', '');
    div.innerHTML =
      '<span class="msf-imp-msg" id="msf-staging-msg"></span>' +
      '<span class="msf-imp-actions" id="msf-impersonate-actions">' +
      '  <span class="msf-imp-slot" id="msf-impersonate-slot" hidden></span>' +
      '  <a href="' + PROD_URL + '" id="msf-back-to-prod" hidden>Aller sur MySifa · prod</a>' +
      '</span>';
    if (document.body) document.body.insertBefore(div, document.body.firstChild);
    else document.documentElement.appendChild(div);
  }

  function clearSlot() {
    var slot = $('msf-impersonate-slot');
    if (slot) { slot.innerHTML = ''; slot.setAttribute('hidden', ''); }
  }

  function showBandeau(show) {
    var b = $('msf-staging-bandeau');
    if (!b) return;
    if (show) {
      b.removeAttribute('hidden');
      document.body.classList.add('has-staging-bandeau');
    } else {
      b.setAttribute('hidden', '');
      document.body.classList.remove('has-staging-bandeau');
    }
  }

  function setBandeauMode(mode) {
    var b = $('msf-staging-bandeau');
    if (!b) return;
    b.classList.remove('env-prod', 'impersonating');
    if (mode === 'prod') b.classList.add('env-prod');
    else if (mode === 'impersonating') b.classList.add('impersonating');
  }

  function setMsg(html) {
    var m = $('msf-staging-msg');
    if (m) m.innerHTML = html;
  }

  function showBackToProd(show) {
    var a = $('msf-back-to-prod');
    if (!a) return;
    if (show) a.removeAttribute('hidden');
    else a.setAttribute('hidden', '');
  }

  function isLoginScreen() {
    return !!(window.S && window.S.app === 'login');
  }

  // ── Machines list (pour le sélecteur) ──────────────────────────────
  function fetchMachines() {
    return fetch('/api/fabrication/machines', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : { machines: [] }; })
      .then(function (j) { state.machines = (j && j.machines) || []; })
      .catch(function () { state.machines = []; });
  }

  function optionsHtml(current) {
    var out = ['<option value="">— rôle —</option>'];
    for (var i = 0; i < ROLES_ORDER.length; i++) {
      var r = ROLES_ORDER[i];
      var sel = (r === current) ? ' selected' : '';
      out.push('<option value="' + r + '"' + sel + '>' + (ROLE_LABELS[r] || r) + '</option>');
    }
    return out.join('');
  }

  function machinesHtml(current) {
    var out = ['<option value="">— machine —</option>'];
    for (var i = 0; i < state.machines.length; i++) {
      var m = state.machines[i];
      var sel = (current && String(m.id) === String(current)) ? ' selected' : '';
      out.push('<option value="' + m.id + '"' + sel + '>' + (m.nom || m.code || ('#' + m.id)) + '</option>');
    }
    return out.join('');
  }

  function renderIdle() {
    var slot = $('msf-impersonate-slot');
    if (!slot) return;
    slot.removeAttribute('hidden');
    slot.innerHTML =
      '<span>Simuler :</span>' +
      '<select id="msf-imp-role">' + optionsHtml('') + '</select>' +
      '<select id="msf-imp-machine">' + machinesHtml('') + '</select>' +
      '<button type="button" id="msf-imp-start">Lancer</button>';
    var btn = $('msf-imp-start');
    if (btn) btn.addEventListener('click', onStart);
  }

  function renderActive(user) {
    var slot = $('msf-impersonate-slot');
    if (!slot) return;
    slot.removeAttribute('hidden');
    var role = user.effective_role || '?';
    var machineName = '';
    if (user.effective_machine_id) {
      for (var i = 0; i < state.machines.length; i++) {
        if (String(state.machines[i].id) === String(user.effective_machine_id)) {
          machineName = state.machines[i].nom || state.machines[i].code || '';
          break;
        }
      }
    }
    var label = (ROLE_LABELS[role] || role);
    if (machineName) label += ' · ' + machineName;
    setMsg('Simulation : ' + label);
    slot.innerHTML = '<button type="button" id="msf-imp-stop" class="msf-imp-stop">Revenir superadmin</button>';
    var btn = $('msf-imp-stop');
    if (btn) btn.addEventListener('click', onStop);
  }

  function onStart() {
    var roleSel = $('msf-imp-role');
    var machSel = $('msf-imp-machine');
    var role = roleSel ? roleSel.value : '';
    var mid = machSel ? machSel.value : '';
    if (!role) { alert('Choisis un rôle à simuler'); return; }
    var body = { role: role };
    if (mid) body.machine_id = parseInt(mid, 10);
    fetch('/api/impersonate', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error((j && j.detail) || 'Erreur'); });
      return r.json();
    }).then(function () { window.location.reload(); })
      .catch(function (e) { alert('Impossible de simuler : ' + (e && e.message || e)); });
  }

  function onStop() {
    fetch('/api/impersonate', { method: 'DELETE', credentials: 'include' })
      .then(function (r) {
        if (!r.ok) throw new Error('Erreur');
        return r.json();
      })
      .then(function () { window.location.reload(); })
      .catch(function () { alert('Impossible de revenir au superadmin'); });
  }

  // ── Rendu principal en fonction de l'utilisateur ───────────────────
  function init(user) {
    ensureCss();
    ensureBandeauDom();
    state.user = user || null;

    // Bouton "Aller sur MySifa · prod" : visible dès qu'on est en v1, indépendamment
    // de la session. Permet à n'importe qui de sauter en prod sans jongler l'URL.
    showBackToProd(isStaging());

    if (isLoginScreen() || !user) {
      // Écran de connexion / pas de session : pas de sélecteur.
      clearSlot();
      if (isStaging()) {
        showBandeau(true);
        setBandeauMode('staging');
        setMsg('v1 — Environnement de test — DB partagée avec la prod');
      } else {
        showBandeau(false);
      }
      return;
    }
    if (!isRealSuperadmin(user)) {
      // Utilisateur non-superadmin : bandeau v1 seul, pas de sélecteur.
      clearSlot();
      if (isStaging()) {
        showBandeau(true);
        setBandeauMode('staging');
        setMsg('v1 — Environnement de test — DB partagée avec la prod');
      } else {
        showBandeau(false);
      }
      return;
    }
    // Superadmin réel : bandeau visible + sélecteur
    showBandeau(true);
    fetchMachines().then(function () {
      if (user.is_impersonating) {
        setBandeauMode('impersonating');
        renderActive(user);
      } else {
        setBandeauMode(isStaging() ? 'staging' : 'prod');
        if (isStaging()) {
          setMsg('v1 — Environnement de test — DB partagée avec la prod');
        } else {
          setMsg('Mode superadmin — prod');
        }
        renderIdle();
      }
    });
  }

  function poll() {
    if (window.S && window.S.user !== undefined) {
      init(window.S.user);
      return;
    }
    fetch('/api/auth/me', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) { init(u); })
      .catch(function () { init(null); });
  }

  window.MySifaImpersonate = { refresh: poll };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', poll);
  } else {
    poll();
  }
  setTimeout(poll, 1500);

  // Watcher : re-init dès que S.user (id, is_impersonating, real_role) ou S.app change.
  var _lastSig = '__init__';
  setInterval(function () {
    var u = (window.S && window.S.user) || null;
    var app = (window.S && window.S.app) || '';
    var sig = u
      ? (app + ':' + String(u.id || 0) + ':' + (u.is_impersonating ? '1' : '0') + ':' + (u.real_role || u.role || ''))
      : (app + ':null');
    if (sig !== _lastSig) {
      _lastSig = sig;
      init(u);
    }
  }, 800);
})();
