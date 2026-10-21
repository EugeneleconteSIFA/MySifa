/* Paramètres › Usage IA — coût, origine et détail des appels à Claude.
   Lecture seule.
   Données : GET /api/settings/ia-usage?jours=N&utilisateur=&application=&fonction=&modele=&statut=
             GET /api/settings/ia-usage/appels/{id}   (fiche d'un appel)

   Coût affiché en euros au taux du réglage Coûts matières (mc_setting.eur_usd_rate),
   dollars en complément : les tarifs Anthropic sont en dollars.

   Adresse : la page Paramètres route ses onglets par le fragment (#…) ; les
   filtres de cet onglet vont dans la query sous des clés préfixées `ia_`
   (ia_jours, ia_utilisateur, ia_application, ia_fonction, ia_modele,
   ia_statut, ia_appel), en remplacement : un filtre essayé n'empile pas. */
(function () {
  'use strict';

  var FILTRES = ['utilisateur', 'application', 'fonction', 'modele', 'statut'];
  var S = { jours: 30, f: {}, appliPose: false, data: null, loading: false, fiche: null };

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function nb(n) { return (Number(n) || 0).toLocaleString('fr-FR'); }
  function argent(n, sym) {
    n = Number(n) || 0;
    var dec = n > 0 && n < 0.01 ? 4 : 2;
    return n.toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + ' ' + sym;
  }
  function taux() { return (S.data && Number(S.data.taux_usd_eur)) || 0.85; }
  function eur(usd) { return argent((Number(usd) || 0) * taux(), '€'); }
  function usd(n) { return argent(n, '$'); }
  function tokens(n) {
    n = Number(n) || 0;
    if (n >= 1e6) return (n / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' M';
    if (n >= 1e3) return (n / 1e3).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' k';
    return nb(n);
  }
  function duree(ms) {
    ms = Number(ms) || 0;
    if (!ms) return '—';
    return ms < 1000 ? ms + ' ms' : (ms / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' s';
  }
  function dt(s) {
    if (!s) return '—';
    return s.slice(8, 10) + '/' + s.slice(5, 7) + ' ' + s.slice(11, 16);
  }
  function origine(r) {
    var a = r.application || '', e = r.ecran || '';
    if (!a && !e) return '<span style="color:var(--muted)">Non renseignée</span>';
    return esc(a) + (e ? ' <span style="color:var(--muted)">› ' + esc(e) + '</span>' : '');
  }
  var FIN = { end_turn: 'Terminé', tool_use: 'Outil appelé', max_tokens: 'Réponse tronquée',
    refusal: 'Refus du modèle', stop_sequence: 'Arrêt demandé', pause_turn: 'En pause' };

  var CARD = 'background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:18px';
  var H = 'font-size:13px;font-weight:600;color:var(--text);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px';
  var TH = 'text-align:left;padding:8px 10px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap';
  var TD = 'padding:8px 10px;font-size:13px;color:var(--text);border-bottom:1px solid var(--border)';
  var NUM = ';text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap';
  var SEL = 'background:var(--card);border:1px solid var(--border);border-radius:10px;padding:7px 10px;font-size:13px;color:var(--text);font-family:inherit;min-width:150px;max-width:220px';

  // `clic(r)` → attributs data-* posés sur la ligne (filtre ou fiche).
  function table(cols, rows, clic) {
    if (!rows.length) {
      return '<div style="font-size:13px;color:var(--muted);padding:6px 0">Aucun appel sur la période.</div>';
    }
    var h = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse"><thead><tr>';
    cols.forEach(function (c) { h += '<th style="' + TH + (c.num ? NUM : '') + '">' + esc(c.label) + '</th>'; });
    h += '</tr></thead><tbody>';
    rows.forEach(function (r) {
      var a = clic ? clic(r) : '';
      h += '<tr' + (a ? ' class="ia-ligne" tabindex="0" ' + a : '') + '>';
      cols.forEach(function (c) { h += '<td style="' + TD + (c.num ? NUM : '') + '">' + c.cell(r) + '</td>'; });
      h += '</tr>';
    });
    return h + '</tbody></table></div>';
  }
  function filtreSur(cle, valeur, bulle) {
    return 'data-ia-filtre="' + esc(cle) + '" data-ia-valeur="' + esc(valeur == null ? '' : valeur) + '" data-bulle="' + esc(bulle || 'Filtrer') + '"';
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
      var bulle = j.jour.slice(8, 10) + '/' + j.jour.slice(5, 7) + ' · ' + eur(v) + ' · ' + nb(j.actions) + ' action(s)';
      h += '<div data-bulle="' + esc(bulle) + '" style="flex:1;min-width:4px;height:' + pct + '%;background:var(--accent);border-radius:3px 3px 0 0;opacity:.85"></div>';
    });
    h += '</div><div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:6px">' +
      '<span>' + esc(dt(jours[0].jour + 'T').slice(0, 5)) + '</span><span>' + esc(dt(jours[jours.length - 1].jour + 'T').slice(0, 5)) + '</span></div>';
    return h;
  }

  function bouton(attr, texte, actif, bulle) {
    var st = actif
      ? 'background:var(--accent-bg);border:1px solid var(--accent);color:var(--accent)'
      : 'background:var(--card);border:1px solid var(--border);color:var(--text)';
    return '<button type="button" ' + attr + (bulle ? ' data-bulle="' + esc(bulle) + '"' : '') + ' style="' + st +
      ';border-radius:10px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit">' + esc(texte) + '</button>';
  }

  function barreFiltres(d) {
    var o = (d && d.options) || {};
    function select(cle, label, liste) {
      var v = S.f[cle];
      var h = '<select data-ia-select="' + cle + '" aria-label="' + esc(label) + '" data-bulle="' + esc(label) + '" style="' + SEL +
        (v != null && (v !== '' || (cle === 'application' && S.appliPose)) ? ';border-color:var(--accent);background:var(--accent-bg)' : '') + '">' +
        '<option value="">' + esc(label) + ' : tous</option>';
      (liste || []).forEach(function (x) {
        var sel = cle === 'application'
          ? (S.appliPose && String(x.valeur) === String(v || ''))
          : (String(x.valeur) === String(v || '') && v !== '' && v != null);
        h += '<option value="' + esc(x.valeur === '' ? '__vide__' : x.valeur) + '"' + (sel ? ' selected' : '') + '>' + esc(x.libelle || x.valeur) + '</option>';
      });
      return h + '</select>';
    }
    var h = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">' +
      [[7, '7 jours'], [30, '30 jours'], [90, '90 jours'], [365, '12 mois']].map(function (p) {
        return bouton('data-ia-jours="' + p[0] + '"', p[1], S.jours === p[0], 'Période');
      }).join('') + '</div>';
    h += '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:18px">' +
      select('utilisateur', 'Utilisateur', o.utilisateurs) +
      select('application', 'Application', o.applications) +
      select('fonction', 'Fonction', o.fonctions) +
      select('modele', 'Modèle', o.modeles) +
      select('statut', 'Statut', [{ valeur: 'ok', libelle: 'Réussis' }, { valeur: 'err', libelle: 'Échecs' }]);
    if (aDesFiltres()) h += bouton('data-ia-effacer', 'Effacer les filtres', false, 'Tout afficher');
    return h + '</div>';
  }
  function aDesFiltres() { return S.appliPose || FILTRES.some(function (k) { return k !== 'application' && S.f[k]; }); }

  function render() {
    var root = document.getElementById('ia-usage-root');
    if (!root) return;
    var d = S.data;
    var h = barreFiltres(d);
    if (S.loading && !d) { root.innerHTML = h + '<div style="color:var(--muted);font-size:13px">Chargement…</div>'; return; }
    if (!d) { root.innerHTML = h; return; }

    var t = d.total || {};
    var tok = (Number(t.tokens_entree) || 0) + (Number(t.tokens_sortie) || 0);
    h += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px">' +
      kpi('Coût', eur(t.cout_usd), usd(t.cout_usd) + ' · depuis le ' + d.depuis.split('-').reverse().join('/')) +
      kpi('Actions', nb(t.actions), nb(t.appels) + ' appel(s) au modèle' + (Number(t.echecs) ? ' · ' + nb(t.echecs) + ' échec(s)' : '')) +
      kpi('Utilisateurs', nb(t.utilisateurs), '') +
      kpi('Tokens', tokens(tok), tokens(t.tokens_entree) + ' entrée · ' + tokens(t.tokens_sortie) + ' sortie') +
      kpi('Durée moyenne', duree(t.duree_moyenne), 'par action') +
      '</div>';

    h += '<div style="' + CARD + '"><div style="' + H + '">Coût par jour</div>' +
      (d.par_jour.length ? barres(d.par_jour) : table([], [])) + '</div>';

    h += '<div style="display:flex;gap:18px;flex-wrap:wrap">';
    h += '<div style="flex:1;min-width:300px;' + CARD + '"><div style="' + H + '">Par application</div>' + table([
      { label: 'Application', cell: function (r) { return r.application ? esc(r.application) : '<span style="color:var(--muted)">Non renseignée</span>'; } },
      { label: 'Actions', num: 1, cell: function (r) { return nb(r.actions); } },
      { label: 'Coût', num: 1, cell: function (r) { return '<b>' + eur(r.cout_usd) + '</b>'; } }
    ], d.par_application, function (r) { return filtreSur('application', r.application, 'Filtrer'); }) + '</div>';
    h += '<div style="flex:1.4;min-width:340px;' + CARD + '"><div style="' + H + '">Par écran</div>' + table([
      { label: 'Écran', cell: function (r) { return origine(r); } },
      { label: 'Actions', num: 1, cell: function (r) { return nb(r.actions); } },
      { label: 'Durée moy.', num: 1, cell: function (r) { return duree(r.duree_moyenne); } },
      { label: 'Coût', num: 1, cell: function (r) { return eur(r.cout_usd); } }
    ], d.par_ecran, function (r) { return filtreSur('application', r.application, 'Filtrer l\'application'); }) + '</div>';
    h += '</div>';

    h += '<div style="' + CARD + '"><div style="' + H + '">Par utilisateur</div>' + table([
      { label: 'Utilisateur', cell: function (r) { return esc(r.utilisateur || '—'); } },
      { label: 'Rôle', cell: function (r) { return '<span style="color:var(--muted)">' + esc(r.role || '—') + '</span>'; } },
      { label: 'Actions', num: 1, cell: function (r) { return nb(r.actions); } },
      { label: 'Tokens', num: 1, cell: function (r) { return tokens((+r.tokens_entree || 0) + (+r.tokens_sortie || 0)); } },
      { label: 'Coût', num: 1, cell: function (r) { return '<b>' + eur(r.cout_usd) + '</b>'; } },
      { label: 'Dernier usage', num: 1, cell: function (r) { return esc(dt(r.dernier)); } }
    ], d.par_utilisateur, function (r) { return filtreSur('utilisateur', r.user_id == null ? 'auto' : r.user_id, 'Filtrer'); }) + '</div>';

    h += '<div style="display:flex;gap:18px;flex-wrap:wrap">';
    h += '<div style="flex:1;min-width:300px;' + CARD + '"><div style="' + H + '">Par fonction</div>' + table([
      { label: 'Fonction', cell: function (r) { return esc(r.fonction_libelle); } },
      { label: 'Actions', num: 1, cell: function (r) { return nb(r.actions); } },
      { label: 'Coût', num: 1, cell: function (r) { return eur(r.cout_usd); } }
    ], d.par_fonction, function (r) { return filtreSur('fonction', r.fonction, 'Filtrer'); }) + '</div>';
    h += '<div style="flex:1;min-width:300px;' + CARD + '"><div style="' + H + '">Par modèle</div>' + table([
      { label: 'Modèle', cell: function (r) { return '<code style="font-size:12px">' + esc(r.modele || '—') + '</code>'; } },
      { label: 'Appels', num: 1, cell: function (r) { return nb(r.appels); } },
      { label: 'Coût', num: 1, cell: function (r) { return eur(r.cout_usd); } }
    ], d.par_modele, function (r) { return r.modele ? filtreSur('modele', r.modele, 'Filtrer') : ''; }) + '</div>';
    h += '</div>';

    h += '<div style="' + CARD + '"><div style="' + H + '">Appels <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--muted)">— cliquer une ligne pour le détail</span></div>' + table([
      { label: 'Date', cell: function (r) { return esc(dt(r.cree_le)); } },
      { label: 'Utilisateur', cell: function (r) { return esc(r.utilisateur || '—'); } },
      { label: 'Origine', cell: function (r) { return origine(r); } },
      { label: 'Fonction', cell: function (r) { return esc(r.fonction_libelle); } },
      { label: 'Modèle', cell: function (r) { return '<code style="font-size:12px">' + esc((r.modele || '—').replace(/^claude-/, '')) + '</code>'; } },
      { label: 'Durée', num: 1, cell: function (r) { return duree(r.duree_ms); } },
      { label: 'Tokens', num: 1, cell: function (r) { return tokens(r.tokens_entree) + ' / ' + tokens(r.tokens_sortie); } },
      { label: 'Coût', num: 1, cell: function (r) { return eur(r.cout_usd); } },
      { label: 'Statut', cell: function (r) {
        if (r.statut === 'err') return '<span style="color:var(--danger)" data-bulle="' + esc(r.erreur || 'Échec') + '">× échec</span>';
        if (r.fin_raison === 'max_tokens' || r.fin_raison === 'refusal') return '<span style="color:var(--warn)" data-bulle="' + esc(FIN[r.fin_raison]) + '">!</span>';
        return '<span style="color:var(--success)" data-bulle="Réussi">✓</span>';
      } }
    ], d.recents, function (r) { return 'data-ia-appel="' + r.id + '" data-bulle="Détail"'; }) +
      (d.recents.length >= 200 ? '<div style="font-size:12px;color:var(--muted);margin-top:8px">200 derniers appels affichés — filtrer pour cibler.</div>' : '') + '</div>';

    h += '<div style="font-size:12px;color:var(--muted)">Coût estimé à partir des tokens et des tarifs publics Anthropic, converti au taux du réglage ' +
      '<a href="/pricing/settings" style="color:var(--accent)">Coûts matières</a> (1 $ = ' + taux().toLocaleString('fr-FR', { maximumFractionDigits: 4 }) + ' €). ' +
      'La facture Anthropic fait foi.</div>';

    root.innerHTML = h;
  }

  // ── Fiche d'un appel ─────────────────────────────────────────────
  function ligne(label, valeur) {
    return '<div style="display:flex;justify-content:space-between;gap:16px;padding:7px 0;border-bottom:1px solid var(--border);font-size:13px">' +
      '<span style="color:var(--muted)">' + esc(label) + '</span><span style="text-align:right;color:var(--text);min-width:0;overflow-wrap:anywhere">' + valeur + '</span></div>';
  }
  function section(titre) {
    return '<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:16px 0 4px">' + esc(titre) + '</div>';
  }
  function renderFiche() {
    var ov = document.getElementById('ia-fiche');
    if (!S.fiche) { if (ov) ov.remove(); return; }
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'ia-fiche';
      ov.style.cssText = 'position:fixed;inset:0;z-index:1500;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px';
      ov.addEventListener('click', function (e) { if (e.target === ov) fermerFiche(); });
      document.body.appendChild(ov);
    }
    var a = S.fiche;
    var h = '<div role="dialog" aria-label="Détail de l\'appel" style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px 24px;width:100%;max-width:560px;max-height:90vh;overflow-y:auto">';
    if (a.chargement) {
      h += '<div style="color:var(--muted);font-size:13px">Chargement…</div></div>';
      ov.innerHTML = h; return;
    }
    if (a.erreurChargement) {
      h += '<div style="color:var(--danger);font-size:13px">' + esc(a.erreurChargement) + '</div></div>';
      ov.innerHTML = h; return;
    }
    var cd = a.cout_detail || {};
    h += '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:6px">' +
      '<div style="font-size:16px;font-weight:800;color:var(--text)">' + esc(a.fonction_libelle) + '</div>' +
      '<button type="button" data-ia-fermer data-bulle="Fermer" data-bulle-touche="Échap" aria-label="Fermer" style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:4px 10px;cursor:pointer;color:var(--text2);font-size:16px">×</button></div>' +
      '<div style="font-size:13px;color:var(--muted)">' + esc(dt(a.cree_le)) + ' · ' + esc(a.utilisateur || '—') + (a.role ? ' (' + esc(a.role) + ')' : '') + '</div>';
    h += section('Origine') +
      ligne('Application', a.application ? esc(a.application) : '<span style="color:var(--muted)">Non renseignée</span>') +
      ligne('Écran', a.ecran ? esc(a.ecran) : '—') +
      (a.module ? ligne('Contexte', esc(a.module)) : '') +
      ligne('Page', a.page ? '<a href="' + esc(a.page) + '" style="color:var(--accent)">' + esc(a.page) + '</a>' : '—') +
      ligne('API', a.api ? '<code style="font-size:12px">' + esc(a.api) + '</code>' : '—');
    h += section('Modèle') +
      ligne('Demandé', a.modele_demande ? '<code style="font-size:12px">' + esc(a.modele_demande) + '</code>' : '—') +
      ligne('A répondu', '<code style="font-size:12px">' + esc(a.modele || '—') + '</code>' + (a.repli ? ' <span style="color:var(--warn);font-weight:700">· repli</span>' : '')) +
      ligne('Appels au modèle', nb(a.nb_appels)) +
      ligne('Fichiers joints', nb(a.nb_fichiers)) +
      ligne('Fin de réponse', a.fin_raison ? esc(FIN[a.fin_raison] || a.fin_raison) : '—') +
      ligne('Durée', duree(a.duree_ms));
    h += section('Tokens et coût') +
      ligne('Entrée', nb(a.input_tokens) + ' · ' + eur(cd.entree)) +
      ligne('Sortie', nb(a.output_tokens) + ' · ' + eur(cd.sortie)) +
      ligne('Cache lu', nb(a.cache_lecture_tokens) + ' · ' + eur(cd.cache_lecture)) +
      ligne('Cache écrit', nb(a.cache_ecriture_tokens) + ' · ' + eur(cd.cache_ecriture)) +
      ligne('Total', '<b>' + eur(a.cout_usd) + '</b> <span style="color:var(--muted)">(' + usd(a.cout_usd) + ')</span>');
    h += section('Résultat') +
      ligne('Statut', a.statut === 'err' ? '<span style="color:var(--danger);font-weight:700">Échec</span>' : '<span style="color:var(--success);font-weight:700">Réussi</span>') +
      (a.erreur ? ligne('Erreur', '<span style="color:var(--danger)">' + esc(a.erreur) + '</span>') : '');
    h += '</div>';
    ov.innerHTML = h;
  }
  function ouvrirFiche(id) {
    S.fiche = { id: id, chargement: true };
    renderFiche(); ecrireUrl();
    fetch('/api/settings/ia-usage/appels/' + encodeURIComponent(id), { credentials: 'include' })
      .then(function (r) { if (!r.ok) throw new Error(r.status === 404 ? 'Appel introuvable.' : 'Erreur ' + r.status); return r.json(); })
      .then(function (j) { if (S.fiche && String(S.fiche.id) === String(id)) { S.fiche = j; renderFiche(); } })
      .catch(function (e) { if (S.fiche && String(S.fiche.id) === String(id)) { S.fiche = { id: id, erreurChargement: e.message }; renderFiche(); } });
  }
  function fermerFiche() { S.fiche = null; renderFiche(); ecrireUrl(); }

  // ── Adresse ──────────────────────────────────────────────────────
  function lireUrl() {
    var q = new URLSearchParams(location.search);
    var j = parseInt(q.get('ia_jours'), 10);
    S.jours = [7, 30, 90, 365].indexOf(j) !== -1 ? j : 30;
    S.f = {};
    FILTRES.forEach(function (k) { var v = q.get('ia_' + k); if (v != null && v !== '') S.f[k] = v.slice(0, 120); });
    S.appliPose = q.has('ia_application');
    if (S.appliPose) S.f.application = q.get('ia_application') || '';
    if (S.f.statut && ['ok', 'err'].indexOf(S.f.statut) === -1) delete S.f.statut;
    var a = q.get('ia_appel');
    return /^\d+$/.test(a || '') ? a : null;
  }
  function ecrireUrl() {
    try {
      var q = new URLSearchParams(location.search);
      ['jours', 'appel'].concat(FILTRES).forEach(function (k) { q.delete('ia_' + k); });
      if (S.jours !== 30) q.set('ia_jours', String(S.jours));
      FILTRES.forEach(function (k) {
        if (k === 'application') { if (S.appliPose) q.set('ia_application', S.f.application || ''); }
        else if (S.f[k]) q.set('ia_' + k, S.f[k]);
      });
      if (S.fiche && S.fiche.id) q.set('ia_appel', String(S.fiche.id));
      var qs = q.toString();
      history.replaceState(history.state, '', location.pathname + (qs ? '?' + qs : '') + location.hash);
    } catch (e) { /* l'adresse est un confort */ }
  }

  function poser(cle, valeur) {
    if (cle === 'application') { S.appliPose = valeur !== null; S.f.application = valeur || ''; }
    else if (valeur) S.f[cle] = valeur; else delete S.f[cle];
    load();
  }

  var branche = false;
  function brancher() {
    if (branche) return;
    branche = true;
    document.addEventListener('click', function (e) {
      if (!document.getElementById('ia-usage-root')) return;
      var t = e.target;
      if (t.closest('[data-ia-fermer]')) { fermerFiche(); return; }
      var b = t.closest('[data-ia-jours]');
      if (b) { S.jours = parseInt(b.getAttribute('data-ia-jours'), 10) || 30; load(); return; }
      if (t.closest('[data-ia-effacer]')) { S.f = {}; S.appliPose = false; load(); return; }
      var f = t.closest('[data-ia-filtre]');
      if (f && f.closest('#ia-usage-root')) { poser(f.getAttribute('data-ia-filtre'), f.getAttribute('data-ia-valeur')); return; }
      var a = t.closest('[data-ia-appel]');
      if (a && a.closest('#ia-usage-root')) ouvrirFiche(a.getAttribute('data-ia-appel'));
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && S.fiche) { fermerFiche(); return; }
      if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('ia-ligne')) e.target.click();
    });
    document.addEventListener('change', function (e) {
      var s = e.target.closest && e.target.closest('[data-ia-select]');
      if (!s) return;
      var cle = s.getAttribute('data-ia-select'), v = s.value;
      if (cle === 'application') poser('application', v === '' ? null : (v === '__vide__' ? '' : v));
      else poser(cle, v);
    });
    var st = document.createElement('style');
    st.textContent = '#ia-usage-root .ia-ligne{cursor:pointer}#ia-usage-root .ia-ligne:hover td,#ia-usage-root .ia-ligne:focus td{background:var(--accent-bg)}';
    document.head.appendChild(st);
  }

  function load() {
    S.loading = true;
    ecrireUrl();
    render();
    var q = new URLSearchParams({ jours: String(S.jours) });
    FILTRES.forEach(function (k) {
      if (k === 'application') { if (S.appliPose) q.set('application', S.f.application || ''); }
      else if (S.f[k]) q.set(k, S.f[k]);
    });
    fetch('/api/settings/ia-usage?' + q.toString(), { credentials: 'include' })
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

  window.initIaUsagePanel = function () {
    brancher();
    var appel = lireUrl();
    load();
    if (appel) ouvrirFiche(appel);
  };
})();
