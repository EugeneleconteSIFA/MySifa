/*
 * MySifa — Paramètres › Système › Fluidité des postes (onglet `perf`).
 *
 * Jusqu'au 07/11/2026, c'était une page à part (/perf-postes) sans la barre
 * latérale : on en sortait des Paramètres sans le vouloir. L'ancienne adresse
 * redirige maintenant ici. Données : GET /api/perf/postes (app/routers/perf.py).
 *
 * Lecture : c'est le FPS médian d'un poste qui compte, pas son dernier relevé.
 * Un poste déjà passé en éco mesure effets coupés, son FPS est donc bon : c'est
 * le passage en éco qui est le signal, pas le chiffre.
 *
 * Adresse (static/settings_url.js) : `jours` (30 par défaut).
 */
(function () {
  'use strict';
  var JOURS = [7, 30, 90];
  var S = { jours: 30, data: null, charge: false };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function ton(f) { return f == null ? '' : f < 30 ? 'pf-bas' : f < 50 ? 'pf-moy' : 'pf-ok'; }
  function dt(s) { return s ? String(s).replace('T', ' ').slice(0, 16) : ''; }
  function nb(v) { return v == null ? '—' : esc(v); }

  function squelette(root) {
    root.innerHTML =
      '<div class="pf-barre">' +
        '<select id="pf-jours" aria-label="Période">' +
          JOURS.map(function (j) { return '<option value="' + j + '">' + j + ' derniers jours</option>'; }).join('') +
        '</select>' +
        '<span class="pf-total" id="pf-total"></span>' +
      '</div>' +
      '<div class="pf-carte"><h3>Postes</h3><div id="pf-postes" class="pf-vide">Chargement…</div>' +
        '<p class="pf-note">« Éco » : le poste affiche déjà une version allégée. Son FPS est alors mesuré ' +
        'effets coupés et reste bon ; c\'est le passage en éco qui est le signal, pas le chiffre.</p></div>' +
      '<div class="pf-carte"><h3>Pages les plus lourdes</h3><div id="pf-pages" class="pf-vide">Chargement…</div>' +
        '<p class="pf-note">Médiane calculée sur les seules sessions en affichage complet.</p></div>';
    document.getElementById('pf-jours').addEventListener('change', function (e) {
      S.jours = parseInt(e.target.value, 10) || 30;
      charger();
    });
  }

  function rendre() {
    var d = S.data;
    var sel = document.getElementById('pf-jours');
    if (sel) sel.value = String(S.jours);
    if (!d) return;
    document.getElementById('pf-total').textContent = d.total_releves + ' relevé' + (d.total_releves > 1 ? 's' : '');
    document.getElementById('pf-postes').innerHTML = d.postes.length ? (
      '<div class="pf-defile"><table class="pf-table"><thead><tr><th>Poste</th><th>FPS médian</th><th>Pire</th>' +
      '<th>Rendu page</th><th>Mode</th><th>Machine</th><th>Utilisateurs</th><th>Sessions</th><th>Dernier relevé</th></tr></thead><tbody>' +
      d.postes.map(function (p) {
        return '<tr>' +
          '<td class="pf-mono">' + esc(p.poste) + '</td>' +
          '<td class="pf-fps ' + ton(p.fps_median) + '">' + nb(p.fps_median) + '</td>' +
          '<td class="' + ton(p.fps_pire) + '">' + nb(p.fps_pire) + '</td>' +
          '<td>' + (p.rendu_median == null ? '—' : Math.round(p.rendu_median) + ' ms') + '</td>' +
          '<td>' + (p.niveau === 'eco'
            ? '<span class="pf-tag pf-eco">éco' + (p.force_main ? ' (manuel)' : '') + '</span>'
            : '<span class="pf-tag">complet</span>') + '</td>' +
          '<td>' + esc(p.navigateur) + '<div class="pf-mono">' +
            [p.cores ? esc(p.cores) + ' cœurs' : '', p.memoire_go ? esc(p.memoire_go) + ' Go' : '', p.ecran ? esc(p.ecran) : '']
              .filter(Boolean).join(' · ') + '</div></td>' +
          '<td class="pf-mono">' + esc((p.utilisateurs || []).join(', ')) + '</td>' +
          '<td>' + esc(p.sessions) + '</td>' +
          '<td class="pf-mono">' + esc(dt(p.dernier)) + '</td></tr>';
      }).join('') + '</tbody></table></div>'
    ) : '<div class="pf-vide">Aucun relevé sur la période.</div>';
    document.getElementById('pf-pages').innerHTML = d.pages.length ? (
      '<div class="pf-defile"><table class="pf-table"><thead><tr><th>Page</th><th>FPS médian</th><th>Mesures</th></tr></thead><tbody>' +
      d.pages.map(function (p) {
        return '<tr><td class="pf-mono">' + esc(p.page) + '</td>' +
          '<td class="pf-fps ' + ton(p.fps_median) + '">' + nb(p.fps_median) + '</td>' +
          '<td>' + esc(p.mesures) + '</td></tr>';
      }).join('') + '</tbody></table></div>'
    ) : '<div class="pf-vide">Aucune mesure en affichage complet.</div>';
  }

  function charger() {
    if (typeof window.settingsPlanifierSync === 'function') window.settingsPlanifierSync();
    return fetch('/api/perf/postes?jours=' + S.jours, { credentials: 'include' })
      .then(function (r) {
        if (r.status === 403) throw new Error('Accès réservé à la direction et au super administrateur.');
        if (!r.ok) throw new Error('Chargement impossible (erreur ' + r.status + ').');
        return r.json();
      })
      .then(function (d) { S.data = d; rendre(); })
      .catch(function (e) {
        var el = document.getElementById('pf-postes');
        if (el) el.textContent = e.message;
        var pg = document.getElementById('pf-pages');
        if (pg) pg.textContent = '';
      });
  }

  function lireUrl() {
    var j = parseInt(new URLSearchParams(location.search).get('jours'), 10);
    S.jours = JOURS.indexOf(j) !== -1 ? j : 30;
  }

  window.SettingsPerf = {
    adresse: {
      etat: function () { return { params: S.jours !== 30 ? { jours: String(S.jours) } : {} }; },
      aller: function () { lireUrl(); return charger(); }
    }
  };

  window.initPerfPanel = function () {
    var root = document.getElementById('perf-root');
    if (!root) return;
    if (!document.getElementById('pf-postes')) squelette(root);
    lireUrl();
    rendre();
    charger();
  };
})();
