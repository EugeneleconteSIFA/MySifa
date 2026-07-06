/* MySifa — Impersonation "Simuler service"
 * Superadmin uniquement. En v1 et en prod. Le bandeau existe déjà dans le DOM ;
 * ce module y injecte le sélecteur + le bouton "Revenir superadmin".
 *
 * Backend : POST/DELETE /api/impersonate (cookie sifa_impersonate).
 * Après un changement, on recharge la page pour que toutes les vues repartent
 * proprement avec le nouveau rôle effectif.
 */
(function () {
  'use strict';

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
    'fabrication', 'logistique', 'commercial', 'administration',
    'direction', 'comptabilite', 'expedition'
  ];

  var state = {
    ready: false,
    env: (window.__MYSIFA_ENV__ || 'v2').toLowerCase(),
    machines: [],
    user: null // sera renseigné à l'init
  };

  function $(id) { return document.getElementById(id); }

  function isStaging() { return state.env === 'v1'; }

  function isRealSuperadmin(u) {
    if (!u) return false;
    // Le superadmin réel est toujours identifiable via real_role si présent,
    // sinon role (avant impersonation, ils sont égaux).
    return (u.real_role || u.role) === 'superadmin';
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
    // mode: 'staging' (rouge v1), 'prod' (indigo), 'impersonating' (ambre)
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

  function renderIdle(user) {
    // Superadmin non impersonnant : dropdowns + bouton "Simuler"
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
    // Impersonation active : message + bouton retour
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

  function clearSlot() {
    var slot = $('msf-impersonate-slot');
    if (slot) { slot.innerHTML = ''; slot.setAttribute('hidden', ''); }
  }

  function init(user) {
    state.user = user || null;
    if (!user) {
      // Pas de session : en v1 on garde le bandeau rouge par défaut, en prod caché.
      // On vide le sélecteur au cas où l'utilisateur vient de se déconnecter.
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
      // Non-superadmin : bandeau v1 reste tel quel, aucun sélecteur.
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
    // Superadmin réel : afficher le bandeau (rouge en v1, indigo en prod, ambre si impersonation)
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
        renderIdle(user);
      }
    });
  }

  function poll() {
    // On attend que S.user (rempli par checkAuth) soit disponible.
    // À défaut, on interroge /api/auth/me directement.
    if (window.S && window.S.user !== undefined) {
      init(window.S.user);
      return;
    }
    fetch('/api/auth/me', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) { init(u); })
      .catch(function () { init(null); });
  }

  // MySifaImpersonate.refresh() : à appeler après checkAuth si besoin de resync.
  window.MySifaImpersonate = { refresh: poll };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', poll);
  } else {
    poll();
  }
  // Petit retard pour attraper S.user une fois checkAuth exécuté.
  setTimeout(poll, 1500);

  // Watcher léger : re-init si S.user (id ou is_impersonating) change — login, logout,
  // basculement d'impersonation… évite un bandeau superadmin bloqué après logout.
  var _lastSig = '__init__';
  setInterval(function () {
    var u = (window.S && window.S.user) || null;
    var sig = u ? (String(u.id || 0) + ':' + (u.is_impersonating ? '1' : '0') + ':' + (u.real_role || u.role || '')) : 'null';
    if (sig !== _lastSig) {
      _lastSig = sig;
      init(u);
    }
  }, 800);
})();
