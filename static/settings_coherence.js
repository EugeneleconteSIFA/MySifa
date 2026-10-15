/* Paramètres › Cohérence — file des écarts relevés par les contrôleurs
   (app/services/coherence.py) et leurs réglages.
   API : /api/settings/coherence */
(function () {
  'use strict';

  var API = '/api/settings/coherence';
  var S = { famille: '', statut: 'ouvert', q: '', data: null, reglages: null, ouvert: null, loading: false, relance: false };

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function dt(s) {
    if (!s) return '—';
    return s.slice(8, 10) + '/' + s.slice(5, 7) + ' ' + s.slice(11, 16);
  }
  function req(path, opt) {
    return fetch(API + path, Object.assign({ credentials: 'include', headers: { 'Content-Type': 'application/json' } }, opt || {}))
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error((j && j.detail) || ('Erreur ' + r.status));
          return j;
        });
      });
  }
  function toastMsg(msg, err) {
    if (typeof window.toast === 'function') window.toast(msg, err);
  }

  var BTN = 'border-radius:10px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;';
  var BTN_CARD = BTN + 'background:var(--card);border:1px solid var(--border);color:var(--text)';
  var BTN_ON = BTN + 'background:var(--accent-bg);border:1px solid var(--accent);color:var(--accent)';
  var BTN_ACC = BTN + 'background:var(--accent);border:1px solid var(--accent);color:white';
  var CARD = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:14px';
  var GRAV = { haute: 'var(--danger)', moyenne: 'var(--warn)', basse: 'var(--muted)' };

  // ── Structure fixe : barre d'outils (jamais reconstruite) + liste ────────
  function squelette(root) {
    root.innerHTML =
      '<div id="coh-tete" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px"></div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px">' +
      '<div id="coh-familles" style="display:flex;gap:8px;flex-wrap:wrap"></div>' +
      '<select id="coh-statut" style="' + BTN_CARD + '">' +
      '<option value="ouvert">Ouverts</option><option value="explique">Expliqués</option>' +
      '<option value="resolu">Résolus</option><option value="tous">Tous</option></select>' +
      '<input id="coh-q" type="search" placeholder="Rechercher (dossier, BL, référence…)" ' +
      'style="flex:1;min-width:200px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none">' +
      '</div>' +
      '<div id="coh-liste"></div>' +
      '<div id="coh-reglages" style="margin-top:26px"></div>';
    document.getElementById('coh-statut').addEventListener('change', function (e) { S.statut = e.target.value; charger(); });
    var q = document.getElementById('coh-q');
    q.addEventListener('input', function () { S.q = q.value.trim().toLowerCase(); rendreListe(); });
    q.addEventListener('keydown', function (e) { if (e.key === 'Escape') { q.value = ''; S.q = ''; rendreListe(); } });
  }

  function rendreTete() {
    var el = document.getElementById('coh-tete');
    if (!el) return;
    var d = S.data || {};
    el.innerHTML =
      '<div style="flex:1;font-size:13px;color:var(--muted)">' +
      (d.dernier_passage ? 'Dernier passage des contrôleurs : ' + esc(dt(d.dernier_passage)) + ' · toutes les 30 minutes en production.'
                         : 'Les contrôleurs n\'ont pas encore tourné sur cette instance.') + '</div>' +
      '<button type="button" id="coh-relancer" style="' + BTN_CARD + '"' + (S.relance ? ' disabled' : '') + '>' +
      (S.relance ? 'Contrôles en cours…' : 'Relancer les contrôles') + '</button>';
    document.getElementById('coh-relancer').addEventListener('click', relancer);
  }

  function rendreFamilles() {
    var el = document.getElementById('coh-familles');
    if (!el || !S.data) return;
    var nb = S.data.ouverts_par_famille || {};
    var tot = Object.keys(nb).reduce(function (a, k) { return a + nb[k]; }, 0);
    var items = [['', 'Toutes', tot]].concat(Object.keys(S.data.familles).map(function (k) { return [k, S.data.familles[k], nb[k] || 0]; }));
    el.innerHTML = items.map(function (f) {
      return '<button type="button" data-fam="' + esc(f[0]) + '" style="' + (S.famille === f[0] ? BTN_ON : BTN_CARD) + '">' +
        esc(f[1]) + (f[2] ? ' <span style="opacity:.75">' + f[2] + '</span>' : '') + '</button>';
    }).join('');
    el.querySelectorAll('[data-fam]').forEach(function (b) {
      b.addEventListener('click', function () { S.famille = b.getAttribute('data-fam'); charger(); });
    });
  }

  function ecartsFiltres() {
    var l = (S.data && S.data.ecarts) || [];
    if (!S.q) return l;
    return l.filter(function (e) {
      return ((e.titre || '') + ' ' + (e.detail || '') + ' ' + (e.objet_ref || '')).toLowerCase().indexOf(S.q) >= 0;
    });
  }

  function ligne(e) {
    var ouvert = S.ouvert === e.id;
    var h = '<div style="display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-top:1px solid var(--border)">' +
      '<span title="Gravité ' + esc(e.gravite) + '" style="flex:none;width:8px;height:8px;border-radius:50%;margin-top:6px;background:' + (GRAV[e.gravite] || 'var(--muted)') + '"></span>' +
      '<div style="flex:1;min-width:0">' +
      '<div style="font-size:13px;font-weight:700;color:var(--text)">' + esc(e.titre) + '</div>' +
      '<div style="font-size:13px;color:var(--text2);margin-top:2px">' + esc(e.detail) + '</div>' +
      '<div style="font-size:11px;color:var(--muted);margin-top:4px">Relevé le ' + esc(dt(e.premiere_vue)) +
      (e.statut === 'resolu' ? ' · résolu le ' + esc(dt(e.resolu_le)) : '') + '</div>';
    if (e.statut === 'explique') {
      h += '<div style="font-size:12px;margin-top:6px;padding:6px 10px;border-left:3px solid var(--success);background:var(--bg);border-radius:0 8px 8px 0">' +
        esc(e.explication) + ' <span style="color:var(--muted)">· ' + esc(e.explique_par || '') + ', ' + esc(dt(e.explique_le)) + '</span></div>';
    }
    if (ouvert) {
      h += '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">' +
        '<input id="coh-expl" type="text" placeholder="Pourquoi cet écart est normal" maxlength="1000" ' +
        'style="flex:1;min-width:220px;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none">' +
        '<button type="button" data-act="valider" data-id="' + e.id + '" style="' + BTN_ACC + '">Enregistrer</button>' +
        '<button type="button" data-act="annuler" style="' + BTN_CARD + '">Annuler</button></div>';
    }
    h += '</div><div style="flex:none;display:flex;gap:6px">';
    if (e.lien) h += '<a href="' + esc(e.lien) + '" style="' + BTN_CARD + ';text-decoration:none">Ouvrir</a>';
    if (e.statut === 'ouvert' && !ouvert) h += '<button type="button" data-act="expliquer" data-id="' + e.id + '" style="' + BTN_CARD + '">Expliquer</button>';
    if (e.statut === 'explique') h += '<button type="button" data-act="rouvrir" data-id="' + e.id + '" style="' + BTN_CARD + '">Rouvrir</button>';
    return h + '</div></div>';
  }

  function rendreListe() {
    var el = document.getElementById('coh-liste');
    if (!el) return;
    if (S.loading && !S.data) { el.innerHTML = '<div style="color:var(--muted);font-size:13px">Chargement…</div>'; return; }
    var l = ecartsFiltres();
    if (!l.length) {
      el.innerHTML = '<div style="' + CARD + ';color:var(--muted);font-size:13px">' +
        (S.q ? 'Aucun résultat pour « ' + esc(S.q) + ' ».' : 'Aucun écart pour ces critères.') + '</div>';
      return;
    }
    var groupes = {}, ordre = [];
    l.forEach(function (e) {
      if (!groupes[e.regle]) { groupes[e.regle] = []; ordre.push(e.regle); }
      groupes[e.regle].push(e);
    });
    el.innerHTML = ordre.map(function (code) {
      var g = groupes[code];
      return '<div style="' + CARD + '">' +
        '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px">' +
        '<div style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text)">' + esc(g[0].regle_titre) + '</div>' +
        '<div style="font-size:12px;color:var(--muted)">' + g.length + '</div></div>' +
        g.map(ligne).join('') + '</div>';
    }).join('');
    el.querySelectorAll('[data-act]').forEach(function (b) {
      b.addEventListener('click', function () { action(b.getAttribute('data-act'), parseInt(b.getAttribute('data-id'), 10)); });
    });
    var inp = document.getElementById('coh-expl');
    if (inp) {
      inp.focus();
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') action('valider', S.ouvert);
        if (e.key === 'Escape') action('annuler');
      });
    }
  }

  function action(act, id) {
    if (act === 'expliquer') { S.ouvert = id; rendreListe(); return; }
    if (act === 'annuler') { S.ouvert = null; rendreListe(); return; }
    if (act === 'valider') {
      var txt = (document.getElementById('coh-expl') || {}).value || '';
      req('/' + id + '/expliquer', { method: 'POST', body: JSON.stringify({ explication: txt }) })
        .then(function () { S.ouvert = null; toastMsg('Écart expliqué.'); charger(); })
        .catch(function (e) { toastMsg(e.message, true); });
      return;
    }
    if (act === 'rouvrir') {
      req('/' + id + '/rouvrir', { method: 'POST' })
        .then(function () { toastMsg('Écart rouvert.'); charger(); })
        .catch(function (e) { toastMsg(e.message, true); });
    }
  }

  function relancer() {
    S.relance = true; rendreTete();
    req('/relancer', { method: 'POST' })
      .then(function (r) {
        var err = r.erreurs && Object.keys(r.erreurs).length;
        toastMsg(err ? 'Contrôles passés, ' + err + ' contrôleur(s) en échec.' : 'Contrôles passés : ' + (r.ouverts || 0) + ' écart(s) ouvert(s).', !!err);
      })
      .catch(function (e) { toastMsg(e.message, true); })
      .then(function () { S.relance = false; charger(); });
  }

  // ── Réglages ────────────────────────────────────────────────────────────
  function rendreReglages() {
    var el = document.getElementById('coh-reglages');
    if (!el || !S.reglages) return;
    var R = S.reglages;
    var h = '<div style="' + CARD + '"><div style="font-size:13px;font-weight:600;color:var(--text);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">Réglages</div>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;margin-bottom:16px">';
    R.seuils.forEach(function (s) {
      h += '<label style="display:block"><span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)">' + esc(s.libelle) + ' (' + esc(s.unite) + ')</span>' +
        '<input type="number" min="0" step="any" data-seuil="' + esc(s.cle) + '" value="' + esc(s.valeur) + '" ' +
        'style="display:block;width:100%;margin-top:6px;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none"></label>';
    });
    h += '</div>';
    Object.keys(R.familles).forEach(function (f) {
      h += '<div style="font-size:12px;font-weight:600;color:var(--muted);margin:10px 0 4px">' + esc(R.familles[f]) + '</div>';
      R.regles.filter(function (r) { return r.famille === f; }).forEach(function (r) {
        h += '<label style="display:flex;gap:10px;align-items:flex-start;padding:6px 0;cursor:pointer">' +
          '<input type="checkbox" data-regle="' + esc(r.code) + '"' + (r.actif ? ' checked' : '') + ' style="margin-top:3px">' +
          '<span><span style="font-size:13px;font-weight:600;color:var(--text)">' + esc(r.titre) + '</span>' +
          '<span style="display:block;font-size:12px;color:var(--muted)">' + esc(r.description) + '</span></span></label>';
      });
    });
    h += '<div style="margin-top:14px"><button type="button" id="coh-sauver" style="' + BTN_ACC + '">Enregistrer les réglages</button></div></div>';
    el.innerHTML = h;
    document.getElementById('coh-sauver').addEventListener('click', sauver);
  }

  function sauver() {
    var seuils = {}, regles = {};
    document.querySelectorAll('[data-seuil]').forEach(function (i) { seuils[i.getAttribute('data-seuil')] = parseFloat(i.value); });
    document.querySelectorAll('[data-regle]').forEach(function (i) { regles[i.getAttribute('data-regle')] = i.checked; });
    req('/reglages', { method: 'PUT', body: JSON.stringify({ seuils: seuils, regles: regles }) })
      .then(function (r) { S.reglages = r; rendreReglages(); toastMsg('Réglages enregistrés. Pris en compte au prochain passage.'); })
      .catch(function (e) { toastMsg(e.message, true); });
  }

  // ── Chargement ──────────────────────────────────────────────────────────
  function charger() {
    S.loading = true;
    var p = '?statut=' + encodeURIComponent(S.statut) + (S.famille ? '&famille=' + encodeURIComponent(S.famille) : '');
    req(p)
      .then(function (d) { S.data = d; })
      .catch(function (e) {
        var el = document.getElementById('coh-liste');
        if (el) el.innerHTML = '<div style="color:var(--danger);font-size:13px">Chargement impossible — ' + esc(e.message) + '.</div>';
      })
      .then(function () {
        S.loading = false;
        rendreTete(); rendreFamilles();
        if (S.data) rendreListe();
      });
  }

  window.initCoherencePanel = function () {
    var root = document.getElementById('coherence-root');
    if (!root) return;
    if (!document.getElementById('coh-liste')) squelette(root);
    charger();
    req('/reglages').then(function (r) { S.reglages = r; rendreReglages(); }).catch(function () {});
  };
})();
