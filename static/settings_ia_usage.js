/* Paramètres › Usage IA — coût et utilisateurs des appels à Claude.
   Lecture seule. Données : GET /api/settings/ia-usage?jours=N */
(function () {
  'use strict';

  var S = { jours: 30, data: null, loading: false };

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function nb(n) { return (Number(n) || 0).toLocaleString('fr-FR'); }
  function usd(n) {
    n = Number(n) || 0;
    var dec = n > 0 && n < 0.01 ? 4 : 2;
    return n.toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + ' $';
  }
  function tokens(n) {
    n = Number(n) || 0;
    if (n >= 1e6) return (n / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' M';
    if (n >= 1e3) return (n / 1e3).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' k';
    return nb(n);
  }
  function dt(s) {
    if (!s) return '—';
    return s.slice(8, 10) + '/' + s.slice(5, 7) + ' ' + s.slice(11, 16);
  }

  var CARD = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:18px';
  var H = 'font-size:13px;font-weight:600;color:var(--text);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px';
  var TH = 'text-align:left;padding:8px 10px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap';
  var TD = 'padding:8px 10px;font-size:13px;color:var(--text);border-bottom:1px solid var(--border)';
  var NUM = ';text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap';

  function table(cols, rows) {
    if (!rows.length) {
      return '<div style="font-size:13px;color:var(--muted);padding:6px 0">Aucun appel sur la période.</div>';
    }
    var h = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse"><thead><tr>';
    cols.forEach(function (c) { h += '<th style="' + TH + (c.num ? NUM : '') + '">' + esc(c.label) + '</th>'; });
    h += '</tr></thead><tbody>';
    rows.forEach(function (r) {
      h += '<tr>';
      cols.forEach(function (c) { h += '<td style="' + TD + (c.num ? NUM : '') + '">' + c.cell(r) + '</td>'; });
      h += '</tr>';
    });
    return h + '</tbody></table></div>';
  }

  function kpi(label, value, sub) {
    return '<div style="flex:1;min-width:150px;' + CARD + ';margin-bottom:0">' +
      '<div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)">' + esc(label) + '</div>' +
      '<div style="font-size:24px;font-weight:700;color:var(--text);margin-top:6px;font-variant-numeric:tabular-nums">' + esc(value) + '</div>' +
      (sub ? '<div style="font-size:12px;color:var(--muted);margin-top:2px">' + esc(sub) + '</div>' : '') +
      '</div>';
  }

  function barres(jours) {
    if (!jours.length) return '';
    var max = Math.max.apply(null, jours.map(function (j) { return Number(j.cout_usd) || 0; })) || 1;
    var h = '<div style="display:flex;align-items:flex-end;gap:3px;height:120px;padding-top:8px">';
    jours.forEach(function (j) {
      var v = Number(j.cout_usd) || 0;
      var pct = Math.max(2, Math.round(v / max * 100));
      var titre = j.jour.slice(8, 10) + '/' + j.jour.slice(5, 7) + ' · ' + usd(v) + ' · ' + nb(j.actions) + ' action(s)';
      h += '<div title="' + esc(titre) + '" style="flex:1;min-width:4px;height:' + pct + '%;background:var(--accent);border-radius:3px 3px 0 0;opacity:.85"></div>';
    });
    h += '</div><div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:6px">' +
      '<span>' + esc(dt(jours[0].jour + 'T').slice(0, 5)) + '</span><span>' + esc(dt(jours[jours.length - 1].jour + 'T').slice(0, 5)) + '</span></div>';
    return h;
  }

  function periodes() {
    return [[7, '7 jours'], [30, '30 jours'], [90, '90 jours'], [365, '12 mois']].map(function (p) {
      var on = S.jours === p[0];
      var st = on
        ? 'background:var(--accent-bg);border:1px solid var(--accent);color:var(--accent)'
        : 'background:var(--card);border:1px solid var(--border);color:var(--text)';
      return '<button type="button" data-ia-jours="' + p[0] + '" style="' + st +
        ';border-radius:10px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit">' + p[1] + '</button>';
    }).join('');
  }

  function render() {
    var root = document.getElementById('ia-usage-root');
    if (!root) return;
    var d = S.data;
    var h = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px">' + periodes() + '</div>';
    if (S.loading && !d) { root.innerHTML = h + '<div style="color:var(--muted);font-size:13px">Chargement…</div>'; bind(root); return; }
    if (!d) { root.innerHTML = h; bind(root); return; }

    var t = d.total || {};
    var tok = (Number(t.tokens_entree) || 0) + (Number(t.tokens_sortie) || 0);
    h += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px">' +
      kpi('Coût', usd(t.cout_usd), 'depuis le ' + d.depuis.split('-').reverse().join('/')) +
      kpi('Actions', nb(t.actions), nb(t.appels) + ' appel(s) au modèle') +
      kpi('Utilisateurs', nb(t.utilisateurs), '') +
      kpi('Tokens', tokens(tok), tokens(t.tokens_entree) + ' entrée · ' + tokens(t.tokens_sortie) + ' sortie') +
      '</div>';

    h += '<div style="' + CARD + '"><div style="' + H + '">Coût par jour</div>' +
      (d.par_jour.length ? barres(d.par_jour) : table([], [])) + '</div>';

    h += '<div style="' + CARD + '"><div style="' + H + '">Par utilisateur</div>' + table([
      { label: 'Utilisateur', cell: function (r) { return esc(r.utilisateur || '—'); } },
      { label: 'Rôle', cell: function (r) { return '<span style="color:var(--muted)">' + esc(r.role || '—') + '</span>'; } },
      { label: 'Actions', num: 1, cell: function (r) { return nb(r.actions); } },
      { label: 'Tokens', num: 1, cell: function (r) { return tokens((+r.tokens_entree || 0) + (+r.tokens_sortie || 0)); } },
      { label: 'Coût', num: 1, cell: function (r) { return '<b>' + usd(r.cout_usd) + '</b>'; } },
      { label: 'Dernier usage', num: 1, cell: function (r) { return esc(dt(r.dernier)); } }
    ], d.par_utilisateur) + '</div>';

    h += '<div style="display:flex;gap:18px;flex-wrap:wrap">';
    h += '<div style="flex:1;min-width:300px;' + CARD + '"><div style="' + H + '">Par fonction</div>' + table([
      { label: 'Fonction', cell: function (r) { return esc(r.fonction_libelle); } },
      { label: 'Actions', num: 1, cell: function (r) { return nb(r.actions); } },
      { label: 'Coût', num: 1, cell: function (r) { return usd(r.cout_usd); } }
    ], d.par_fonction) + '</div>';
    h += '<div style="flex:1;min-width:300px;' + CARD + '"><div style="' + H + '">Par modèle</div>' + table([
      { label: 'Modèle', cell: function (r) { return '<code style="font-size:12px">' + esc(r.modele || '—') + '</code>'; } },
      { label: 'Appels', num: 1, cell: function (r) { return nb(r.appels); } },
      { label: 'Coût', num: 1, cell: function (r) { return usd(r.cout_usd); } }
    ], d.par_modele) + '</div>';
    h += '</div>';

    h += '<div style="' + CARD + '"><div style="' + H + '">Derniers appels</div>' + table([
      { label: 'Date', cell: function (r) { return esc(dt(r.cree_le)); } },
      { label: 'Utilisateur', cell: function (r) { return esc(r.utilisateur || '—'); } },
      { label: 'Fonction', cell: function (r) { return esc(r.fonction_libelle) + (r.module ? ' <span style="color:var(--muted)">· ' + esc(r.module) + '</span>' : ''); } },
      { label: 'Appels', num: 1, cell: function (r) { return nb(r.nb_appels); } },
      { label: 'Tokens', num: 1, cell: function (r) { return tokens(r.tokens_entree) + ' / ' + tokens(r.tokens_sortie); } },
      { label: 'Coût', num: 1, cell: function (r) { return usd(r.cout_usd); } },
      { label: 'Statut', cell: function (r) {
        return r.statut === 'err'
          ? '<span style="color:var(--danger)">× échec</span>'
          : '<span style="color:var(--success)">✓</span>';
      } }
    ], d.recents) + '</div>';

    h += '<div style="font-size:12px;color:var(--muted)">Coût estimé à partir des tokens et des tarifs publics Anthropic, en dollars. ' +
      'La facture Anthropic fait foi.</div>';

    root.innerHTML = h;
    bind(root);
  }

  function bind(root) {
    root.querySelectorAll('[data-ia-jours]').forEach(function (b) {
      b.addEventListener('click', function () {
        S.jours = parseInt(b.getAttribute('data-ia-jours'), 10) || 30;
        load();
      });
    });
  }

  function load() {
    S.loading = true;
    render();
    fetch('/api/settings/ia-usage?jours=' + S.jours, { credentials: 'include' })
      .then(function (r) {
        if (!r.ok) throw new Error('Erreur ' + r.status);
        return r.json();
      })
      .then(function (j) { S.data = j; })
      .catch(function (e) {
        var root = document.getElementById('ia-usage-root');
        if (root) root.innerHTML = '<div style="color:var(--danger);font-size:13px">Chargement impossible — ' + esc(e.message) + '.</div>';
        S.data = null;
      })
      .then(function () {
        S.loading = false;
        if (S.data) render();
      });
  }

  window.initIaUsagePanel = load;
})();
