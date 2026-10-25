/*
 * Maintenance › Alertes › Historique des saisies — affichage « Analyse ».
 *
 * Bascule Historique / Analyse dans la carte « Historique des saisies ». Les
 * filtres sont ceux de l'historique (type, opérateur, machine, conformité,
 * période, filtres par question) : à chaque rendu de l'historique, la page
 * appelle MaintAnalyse.surFiltres() et l'analyse se recalcule.
 *
 * Les chiffres viennent du serveur (GET /api/maintenance/alertes/stats,
 * app/services/alertes_statistiques.py), sur toute la période : la liste de
 * l'historique ne charge que les 1 000 dernières validations. Les anciens
 * formulaires n'y entrent pas.
 *
 * Analyse par défaut, sur UN type de contrôle : sans type choisi, le plus
 * validé est posé dans le filtre (« Tous les types » est grisé en Analyse).
 *
 * Adresse (static/maintenance_url.js) : affichage=historique (l'Analyse est
 * le défaut, non écrit).
 * Chaque bandeau d'alerte est un bloc capturable (maintenance.alertes.synthese).
 *
 * Ce fichier ne lit les globales de la page (CTRL_STATE, getCtrlFilters,
 * _displayType…) qu'à l'appel.
 */
(function () {
  'use strict';
  if (window.MaintAnalyse) return;

  // Analyse par défaut ; un seul type de contrôle à la fois.
  var A = { mode: 'analyse', data: null, cle: '', seq: 0, timer: null, erreur: '' };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function nb(v, d) {
    if (v == null || !isFinite(v)) return '—';
    return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: d == null ? 2 : d });
  }
  function pct(v) { return v == null ? '—' : nb(v, 1) + ' %'; }
  function dateCourte(iso) {
    var s = String(iso || '');
    return s.length >= 10 ? s.slice(8, 10) + '/' + s.slice(5, 7) : s;
  }

  // CTRL_STATE est un `const` de premier niveau de la page : visible par son
  // nom depuis ce script, mais pas comme propriété de window.
  function etat() { return typeof CTRL_STATE !== 'undefined' ? CTRL_STATE : {}; }

  // ── Filtres de l'historique → requête ─────────────────────────────────
  // Le type affiché est un nom (label du code maintenance ou nom de l'alerte) :
  // on retrouve les alertes qui le portent.
  function alertesDuType(type) {
    var ids = {};
    var st = etat();
    (st.acks || []).forEach(function (a) {
      if (a._source === 'alert' && a._alert_id != null && window._displayType(a) === type) ids[a._alert_id] = 1;
    });
    var codes = (typeof CTRL_TYPES_STATE !== 'undefined' && CTRL_TYPES_STATE.list) || [];
    (st.known_alerts || []).forEach(function (a) {
      if (a.nom === type) ids[a.id] = 1;
      if (a.linked_maint_code) {
        var c = codes.filter(function (t) { return String(t.id) === String(a.linked_maint_code); })[0];
        if (c && c.nom === type) ids[a.id] = 1;
      }
    });
    return Object.keys(ids);
  }

  function requete() {
    var f = window.getCtrlFilters();
    var q = new URLSearchParams();
    var ids = f.type ? alertesDuType(f.type) : [];
    if (f.type && !ids.length) return null;
    ids.forEach(function (id) { q.append('alerte', id); });
    if (f.dateFrom) q.set('du', f.dateFrom);
    if (f.dateTo) q.set('au', f.dateTo);
    if (f.machine) q.set('machine', f.machine);
    if (f.operateur) q.set('operateur', f.operateur);
    if (f.conformite) q.set('conformite', f.conformite);
    var pts = etat().pointFilters || {};
    if (ids.length === 1 && Object.keys(pts).length) q.set('points', JSON.stringify(pts));
    return q;
  }

  // ── Bascule ───────────────────────────────────────────────────────────
  function majBascule() {
    document.querySelectorAll('[data-ctrl-affichage]').forEach(function (b) {
      var on = b.getAttribute('data-ctrl-affichage') === A.mode;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    var vide = document.querySelector('#filt-controles-type option[value=""]');
    if (vide) vide.disabled = A.mode === 'analyse';
    var liste = document.querySelector('#ctrl-subview-historique .ops-list');
    var zone = document.getElementById('ctrl-analyse');
    if (liste) liste.style.display = A.mode === 'analyse' ? 'none' : '';
    if (zone) zone.style.display = A.mode === 'analyse' ? '' : 'none';
  }

  function afficher(mode, opts) {
    A.mode = mode === 'analyse' ? 'analyse' : 'historique';
    majBascule();
    if (A.mode === 'analyse') charger(true);
    if (!(opts && opts.sansRendu) && typeof window.renderCtrl === 'function') window.renderCtrl();
  }

  // Sans type choisi : le type d'alerte le plus validé parmi les saisies
  // chargées. Rend false quand le filtre vient d'être posé (le rendu qui suit
  // relance l'analyse) ou quand il n'y a encore rien à choisir.
  function typeParDefaut() {
    var sel = document.getElementById('filt-controles-type');
    if (!sel || sel.value) return true;
    var n = {};
    (etat().acks || []).forEach(function (a) {
      if (a._source !== 'alert' || a._ancien || (window.ctrlIsAutoClose && window.ctrlIsAutoClose(a))) return;
      var t = window._displayType(a);
      if (t) n[t] = (n[t] || 0) + 1;
    });
    var t = Object.keys(n).sort(function (x, y) { return n[y] - n[x]; })[0];
    var zone = document.getElementById('ctrl-analyse');
    if (!t || ![].some.call(sel.options, function (o) { return o.value === t; })) {
      if (zone && !(etat().acks || []).length) zone.innerHTML = '<div class="an-vide">Chargement…</div>';
      else if (zone) zone.innerHTML = '<div class="an-vide">Aucune validation d\'alerte à analyser.</div>';
      return false;
    }
    sel.value = t;
    setTimeout(function () { window.ctrlAutoFilter({ resetPoints: true }); }, 0);
    return false;
  }

  function surFiltres() {
    majBascule();
    if (A.mode !== 'analyse') return;
    if (!typeParDefaut()) return;
    clearTimeout(A.timer);
    A.timer = setTimeout(function () { charger(false); }, 200);
  }

  function charger(force) {
    var zone = document.getElementById('ctrl-analyse');
    if (!zone) return;
    var q = requete();
    if (!q) {
      A.data = null; A.cle = '';
      zone.innerHTML = '<div class="an-vide">Ce type de contrôle n\'a pas de questionnaire d\'alerte à analyser.</div>';
      return;
    }
    var cle = q.toString();
    if (!force && cle === A.cle && A.data) return;
    A.cle = cle;
    var seq = ++A.seq;
    if (!A.data) zone.innerHTML = '<div class="an-vide">Calcul en cours…</div>';
    zone.classList.add('an-charge');
    fetch('/api/maintenance/alertes/stats?' + cle, { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) { if (seq !== A.seq) return; A.data = d; A.erreur = ''; rendre(); })
      .catch(function () {
        if (seq !== A.seq) return;
        A.erreur = 'Analyse indisponible — réessaie dans un instant.';
        rendre();
      })
      .then(function () { if (seq === A.seq) zone.classList.remove('an-charge'); });
  }

  // ── Rendu ─────────────────────────────────────────────────────────────
  function rendre() {
    var zone = document.getElementById('ctrl-analyse');
    if (!zone) return;
    if (A.erreur) { zone.innerHTML = '<div class="an-vide">' + esc(A.erreur) + '</div>'; return; }
    var d = A.data;
    if (!d || !d.alertes || !d.alertes.length) {
      zone.innerHTML = '<div class="an-vide">Aucune validation d\'alerte sur cette période.</div>';
      return;
    }
    var h = '<div class="an-tete">'
      + '<div class="an-periode">' + esc(d.du && d.au ? ('Du ' + dateCourte(d.du) + ' au ' + dateCourte(d.au)) : 'Toute la période')
      + ' · anciens formulaires exclus</div>'
      + '<div class="an-tete-droite">'
      +   '<a class="an-btn" href="/api/maintenance/alertes/stats?' + esc(A.cle) + (A.cle ? '&' : '') + 'format=csv" download>Exporter CSV</a>'
      + '</div></div>';
    d.alertes.forEach(function (a) { h += rendreAlerte(a); });
    zone.innerHTML = h;
  }

  function tuile(lib, val, sous, ton) {
    return '<div class="an-tuile' + (ton ? ' an-' + ton : '') + '"><div class="an-tuile-lib">' + esc(lib) + '</div>'
      + '<div class="an-tuile-val">' + val + '</div>' + (sous ? '<div class="an-tuile-sous">' + sous + '</div>' : '') + '</div>';
  }

  function tendance(actuel, avant, inverse) {
    if (actuel == null || avant == null) return '';
    var dlt = Math.round((actuel - avant) * 10) / 10;
    if (!dlt) return 'stable vs période précédente';
    var mauvais = inverse ? dlt > 0 : dlt < 0;
    return '<span class="' + (mauvais ? 'an-mauvais' : 'an-bon') + '">' + (dlt > 0 ? '+' : '−') + nb(Math.abs(dlt), 1)
      + ' pt</span> vs période précédente';
  }

  function rendreAlerte(a) {
    var s = a.synthese || {};
    var p = s.precedent || null;
    var h = '<section class="an-alerte">';
    h += '<div class="an-synthese" data-bloc="maintenance.alertes.synthese"'
      + ' data-bloc-objet="' + esc(a.id) + '" data-bloc-objet-libelle="' + esc(a.nom) + '"'
      + ' data-bloc-valeur-validations="' + esc(s.validations || 0) + '"'
      + ' data-bloc-valeur-taux-nc="' + esc(s.taux_nc == null ? '' : s.taux_nc) + '"'
      + ' data-bloc-valeur-remplissage="' + esc(s.remplissage == null ? '' : s.remplissage) + '">';
    h += '<h3 class="an-titre" data-bloc-entete>' + esc(a.nom) + '</h3><div class="an-tuiles">';
    h += tuile('Validations', nb(s.validations, 0),
      p ? (nb(p.validations, 0) + ' sur la période précédente') : '');
    var tnd = p ? tendance(s.taux_nc, p.taux_nc, true) : '';
    h += tuile('Non-conformité', pct(s.taux_nc),
      nb(s.nc, 0) + ' validation' + (s.nc > 1 ? 's' : '') + ' NC' + (tnd ? ' · ' + tnd : ''),
      s.nc ? 'danger' : '');
    h += tuile('Remplissage', pct(s.remplissage),
      nb(s.remplies, 0) + ' remplie' + (s.remplies > 1 ? 's' : '') + ' · ' + nb(s.fermetures_auto, 0) + ' fermeture' + (s.fermetures_auto > 1 ? 's' : '') + ' auto · '
      + nb(s.esquives, 0) + ' esquive' + (s.esquives > 1 ? 's' : ''));
    h += '</div>';
    if (s.anciens_exclus) h += '<div class="an-note">' + nb(s.anciens_exclus, 0) + ' validation' + (s.anciens_exclus > 1 ? 's' : '') + ' d\'un ancien formulaire écartée' + (s.anciens_exclus > 1 ? 's' : '') + '.</div>';
    h += '</div>';
    if (!s.validations) {
      h += '<div class="an-vide">Aucune validation remplie ne correspond aux filtres.</div></section>';
      return h;
    }
    h += '<div class="an-grille">' + (a.questions || []).map(function (q) {
      return q.type === 'value' ? carteValeur(q) : carteChoix(q);
    }).join('') + '</div>';
    return h + '</section>';
  }

  // Question à choix : répartition en barres, NC en rouge, évolution hebdo.
  function carteChoix(q) {
    var h = '<div class="an-carte"><div class="an-carte-titre">' + esc(q.label) + '</div>'
      + '<div class="an-carte-sous">' + nb(q.repondants, 0) + ' réponse' + (q.repondants > 1 ? 's' : '') + '</div>';
    if (!q.repondants) return h + '<div class="an-vide-mini">Pas de réponse sur la période.</div></div>';
    h += '<div class="an-barres">' + q.repartition.map(function (r) {
      return '<div class="an-barre-ligne" title="' + esc(r.reponse + ' : ' + r.n + ' (' + pct(r.pct) + ')') + '">'
        + '<span class="an-barre-lib">' + esc(r.reponse) + (r.nc ? ' <em class="an-tag-nc">NC</em>' : '') + '</span>'
        + '<span class="an-barre-piste"><span class="an-barre' + (r.nc ? ' nc' : '') + '" style="width:' + Math.max(r.pct || 0, r.n ? 1 : 0) + '%"></span></span>'
        + '<span class="an-barre-val">' + pct(r.pct) + ' <span>· ' + nb(r.n, 0) + '</span></span></div>';
    }).join('') + '</div>';
    var avecNc = q.repartition.some(function (r) { return r.nc; });
    if (avecNc && q.evolution && q.evolution.length > 1) {
      h += '<div class="an-sous-titre">Non-conformité par semaine</div>' + barresSemaines(q.evolution);
    }
    if (q.autres && q.autres.length) {
      h += '<div class="an-sous-titre">Précisions « Autre »</div><div class="an-autres">'
        + q.autres.map(function (o) { return '<span>' + esc(o.texte) + ' <b>×' + o.n + '</b></span>'; }).join('') + '</div>';
    }
    return h + '</div>';
  }

  function barresSemaines(ev) {
    var W = 320, H = 70, n = ev.length, gap = 2, bw = Math.max(3, (W - gap * (n - 1)) / n);
    var max = Math.max.apply(null, ev.map(function (e) { return e.taux_nc || 0; }).concat([1]));
    var s = '<svg class="an-svg" viewBox="0 0 ' + W + ' ' + (H + 14) + '" preserveAspectRatio="none" role="img" aria-label="Taux de non-conformité par semaine">';
    ev.forEach(function (e, i) {
      var hh = (e.taux_nc || 0) / max * H, x = i * (bw + gap);
      s += '<g><title>' + esc('Semaine du ' + dateCourte(e.semaine) + ' : ' + pct(e.taux_nc) + ' (' + e.nc + '/' + e.n + ')') + '</title>'
        + '<rect class="an-hit" x="' + x + '" y="0" width="' + bw + '" height="' + H + '"></rect>'
        + '<rect class="an-col nc" x="' + x + '" y="' + (H - hh) + '" width="' + bw + '" height="' + Math.max(hh, e.nc ? 1 : 0) + '" rx="2"></rect></g>';
    });
    s += '<line class="an-axe" x1="0" y1="' + H + '" x2="' + W + '" y2="' + H + '"></line>'
      + '<text class="an-txt" x="0" y="' + (H + 12) + '">' + esc(dateCourte(ev[0].semaine)) + '</text>'
      + '<text class="an-txt" x="' + W + '" y="' + (H + 12) + '" text-anchor="end">' + esc(dateCourte(ev[n - 1].semaine)) + '</text>';
    return s + '</svg>';
  }

  // Question à valeur : chiffres clés, courbe avec tolérances, histogramme.
  function carteValeur(q) {
    var u = q.unit ? ' ' + esc(q.unit) : '';
    var r = q.resume || {};
    var h = '<div class="an-carte"><div class="an-carte-titre">' + esc(q.label) + (q.unit ? ' <span>(' + esc(q.unit) + ')</span>' : '') + '</div>'
      + '<div class="an-carte-sous">' + nb(q.controles, 0) + ' contrôle' + (q.controles > 1 ? 's' : '')
      + (r.n > q.controles ? ' · ' + nb(r.n, 0) + ' mesures' : '')
      + (q.min != null || q.max != null ? ' · tolérance ' + (q.min != null ? nb(q.min) : '…') + ' – ' + (q.max != null ? nb(q.max) : '…') + u : '')
      + (q.cible != null ? ' · cible ' + nb(q.cible) + u : '') + '</div>';
    if (!r.n) return h + '<div class="an-vide-mini">Pas de mesure sur la période.</div></div>';
    h += '<div class="an-chiffres">'
      + chiffre('Moyenne', nb(r.moyenne, 3) + u) + chiffre('Médiane', nb(r.mediane, 3) + u)
      + chiffre('Écart-type', nb(r.ecart_type, 3)) + chiffre('Min – max', nb(r.min, 3) + ' – ' + nb(r.max, 3))
      + (q.pct_hors_tolerance != null ? chiffre('Hors tolérance', pct(q.pct_hors_tolerance), q.hors_tolerance ? 'danger' : '') : '')
      + '</div>';
    h += '<div class="an-sous-titre">Dans le temps</div>' + courbe(q);
    h += '<div class="an-sous-titre">Répartition des valeurs</div>' + histogramme(q);
    if (q.multiples) {
      var m = q.multiples;
      h += '<div class="an-sous-titre">Écart entre ' + esc(m.libelle.toLowerCase()) + 's d\'un même contrôle</div>'
        + '<div class="an-chiffres">' + chiffre('Écart moyen', nb(m.ecart.moyenne, 3) + u) + chiffre('Écart max', nb(m.ecart.max, 3) + u) + '</div>'
        + positions(m, u);
    }
    return h + '</div>';
  }

  function chiffre(lib, val, ton) {
    return '<div class="an-chiffre' + (ton ? ' an-' + ton : '') + '"><span>' + esc(lib) + '</span><b>' + val + '</b></div>';
  }

  function courbe(q) {
    var pts = q.serie || [];
    var W = 520, H = 150, G = 34, B = 18;
    var vals = pts.map(function (p) { return p.v; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    [q.min, q.max, q.cible].forEach(function (b) { if (b != null) { lo = Math.min(lo, b); hi = Math.max(hi, b); } });
    if (hi === lo) { hi += 1; lo -= 1; }
    var marge = (hi - lo) * 0.08; hi += marge; lo -= marge;
    var t0 = Date.parse(pts[0].t), t1 = Date.parse(pts[pts.length - 1].t);
    if (!(t1 > t0)) t1 = t0 + 1;
    function X(t) { return G + (Date.parse(t) - t0) / (t1 - t0) * (W - G - 6); }
    function Y(v) { return 4 + (hi - v) / (hi - lo) * (H - 4 - B); }
    var s = '<svg class="an-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(q.label) + ' dans le temps">';
    if (q.min != null || q.max != null) {
      var yh = Y(q.max != null ? q.max : hi), yb = Y(q.min != null ? q.min : lo);
      s += '<rect class="an-bande" x="' + G + '" y="' + yh + '" width="' + (W - G - 6) + '" height="' + Math.max(0, yb - yh) + '"><title>Tolérance</title></rect>';
    }
    [hi - marge, lo + marge].forEach(function (v) {
      s += '<line class="an-grille" x1="' + G + '" x2="' + (W - 6) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"></line>'
        + '<text class="an-txt" x="' + (G - 4) + '" y="' + (Y(v) + 3) + '" text-anchor="end">' + esc(nb(v, 2)) + '</text>';
    });
    if (q.cible != null) {
      s += '<line class="an-cible" x1="' + G + '" x2="' + (W - 6) + '" y1="' + Y(q.cible) + '" y2="' + Y(q.cible) + '"><title>Cible ' + esc(nb(q.cible)) + '</title></line>';
    }
    if (pts.length > 1) {
      s += '<polyline class="an-ligne" points="' + pts.map(function (p) { return X(p.t).toFixed(1) + ',' + Y(p.v).toFixed(1); }).join(' ') + '"></polyline>';
    }
    pts.forEach(function (p) {
      var x = X(p.t), y = Y(p.v);
      var info = p.t.replace('T', ' ').slice(0, 16) + (p.machine ? ' · ' + p.machine : '') + ' : '
        + p.vals.map(function (v) { return nb(v, 3); }).join(' / ') + (q.unit ? ' ' + q.unit : '') + (p.nc ? ' · NC' : '');
      s += '<g><title>' + esc(info) + '</title><circle class="an-hit" cx="' + x + '" cy="' + y + '" r="7"></circle>'
        + '<circle class="an-point' + (p.nc ? ' nc' : '') + '" cx="' + x + '" cy="' + y + '" r="' + (pts.length > 150 ? 2 : 3) + '"></circle></g>';
    });
    s += '<text class="an-txt" x="' + G + '" y="' + (H - 4) + '">' + esc(dateCourte(pts[0].t)) + '</text>'
      + '<text class="an-txt" x="' + (W - 6) + '" y="' + (H - 4) + '" text-anchor="end">' + esc(dateCourte(pts[pts.length - 1].t)) + '</text>';
    return s + '</svg>';
  }

  function histogramme(q) {
    var cl = q.histogramme || [];
    if (!cl.length) return '';
    var W = 520, H = 90, B = 16, n = cl.length, gap = 2, bw = (W - gap * (n - 1)) / n;
    var max = Math.max.apply(null, cl.map(function (c) { return c.n; }).concat([1]));
    var lo = cl[0].de, hi = cl[n - 1].a;
    function X(v) { return (v - lo) / ((hi - lo) || 1) * W; }
    var s = '<svg class="an-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Répartition des valeurs">';
    cl.forEach(function (c, i) {
      var hh = c.n / max * (H - B - 4), x = i * (bw + gap);
      var hors = (q.min != null && c.a <= q.min) || (q.max != null && c.de >= q.max);
      s += '<g><title>' + esc(nb(c.de, 3) + ' – ' + nb(c.a, 3) + ' : ' + c.n + ' mesure' + (c.n > 1 ? 's' : '')) + '</title>'
        + '<rect class="an-hit" x="' + x + '" y="0" width="' + bw + '" height="' + (H - B) + '"></rect>'
        + '<rect class="an-col' + (hors ? ' nc' : '') + '" x="' + x + '" y="' + (H - B - hh) + '" width="' + bw + '" height="' + Math.max(hh, c.n ? 1 : 0) + '" rx="2"></rect></g>';
    });
    [q.min, q.max].forEach(function (b) {
      if (b == null) return;
      s += '<line class="an-borne" x1="' + X(b) + '" x2="' + X(b) + '" y1="0" y2="' + (H - B) + '"><title>Tolérance ' + esc(nb(b)) + '</title></line>';
    });
    s += '<line class="an-axe" x1="0" x2="' + W + '" y1="' + (H - B) + '" y2="' + (H - B) + '"></line>'
      + '<text class="an-txt" x="0" y="' + (H - 3) + '">' + esc(nb(lo, 3)) + '</text>'
      + '<text class="an-txt" x="' + W + '" y="' + (H - 3) + '" text-anchor="end">' + esc(nb(hi, 3)) + '</text>';
    return s + '</svg>';
  }

  // Moyenne par position (Front 1, Front 2…) : un front qui pèse toujours
  // plus que les autres se voit d'un coup.
  function positions(m, u) {
    var pp = m.par_position || [];
    var vals = pp.map(function (p) { return p.moyenne; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    return '<div class="an-barres">' + pp.map(function (p) {
      var w = hi > lo ? 15 + (p.moyenne - lo) / (hi - lo) * 85 : 100;
      return '<div class="an-barre-ligne" title="' + esc(m.libelle + ' ' + p.position + ' : moyenne ' + nb(p.moyenne, 3) + ' sur ' + p.n + ' contrôles') + '">'
        + '<span class="an-barre-lib">' + esc(m.libelle + ' ' + p.position) + '</span>'
        + '<span class="an-barre-piste"><span class="an-barre" style="width:' + w + '%"></span></span>'
        + '<span class="an-barre-val">' + nb(p.moyenne, 3) + u + ' <span>· ' + nb(p.n, 0) + '</span></span></div>';
    }).join('') + '</div>';
  }

  // Filtres d'un indicateur d'accueil : période glissante et machine.
  function contexteBloc() {
    var f = window.getCtrlFilters ? window.getCtrlFilters() : {};
    var presets = window.maintDatePresets ? window.maintDatePresets() : {};
    var periode = '';
    Object.keys(presets).forEach(function (k) {
      if (presets[k].from === f.dateFrom && presets[k].to === f.dateTo) periode = k;
    });
    var out = { bloc_ctrl_machine: f.machine || '' };
    if (periode) out.bloc_periode = periode;
    else if (f.dateFrom) { out.bloc_periode = 'dates'; out.bloc_du = f.dateFrom; out.bloc_au = f.dateTo || f.dateFrom; }
    return out;
  }

  // Ouverture depuis un indicateur d'accueil : les filtres capturés (bloc_…)
  // font foi. Ils sont traduits en clés de l'historique AVANT que
  // maintenance_url.js lise l'adresse (au DOMContentLoaded), puis retirés.
  // Bornes : mêmes raccourcis que maintDatePresets() de la page, pas encore
  // chargée à ce stade.
  (function lireFiltresBloc() {
    try {
      var u = new URL(location.href), sp = u.searchParams;
      var per = sp.get('bloc_periode'), mach = sp.get('bloc_ctrl_machine');
      if (!per && mach === null) return;
      var now = new Date();
      function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
      function jour(n) { var d = new Date(now); d.setDate(now.getDate() + n); return d; }
      var b = {
        today: [now, now], yesterday: [jour(-1), jour(-1)], last7: [jour(-6), now], last30: [jour(-29), now],
        thisMonth: [new Date(now.getFullYear(), now.getMonth(), 1), now],
        prevMonth: [new Date(now.getFullYear(), now.getMonth() - 1, 1), new Date(now.getFullYear(), now.getMonth(), 0)]
      }[per];
      if (b) { sp.set('du', iso(b[0])); sp.set('au', iso(b[1])); }
      else if (per === 'dates' && sp.get('bloc_du')) { sp.set('du', sp.get('bloc_du')); sp.set('au', sp.get('bloc_au') || sp.get('bloc_du')); }
      if (mach) sp.set('machine', mach); else if (mach !== null) sp.delete('machine');
      ['bloc_periode', 'bloc_du', 'bloc_au', 'bloc_ctrl_machine'].forEach(function (k) { sp.delete(k); });
      sp.set('vue', 'controles');
      sp.delete('affichage');
      history.replaceState(history.state, '', u.pathname + '?' + sp.toString() + u.hash);
      window.__mysifaFiltresLus = true;
    } catch (e) { /* adresse illisible : la page s'ouvre avec ses défauts */ }
  })();

  // La liste des types est reconstruite par plusieurs chemins de la page
  // (chargement des alertes, des codes…) : « Tous les types » est regrisé à
  // chaque reconstruction tant que l'Analyse est affichée.
  function surveillerTypes() {
    var sel = document.getElementById('filt-controles-type');
    if (!sel || typeof MutationObserver === 'undefined') return;
    new MutationObserver(function () {
      var vide = sel.querySelector('option[value=""]');
      if (vide && vide.disabled !== (A.mode === 'analyse')) vide.disabled = A.mode === 'analyse';
    }).observe(sel, { childList: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', surveillerTypes, { once: true });
  else surveillerTypes();

  window.MaintAnalyse = {
    afficher: afficher,
    surFiltres: surFiltres,
    mode: function () { return A.mode; },
    // Lecture de l'adresse (maintenance_url.js) : pas de rendu, la page suit.
    appliquer: function (mode) {
      A.mode = mode === 'analyse' ? 'analyse' : 'historique';
      majBascule();
      if (A.mode === 'analyse') charger(true);
    },
    contexteBloc: contexteBloc,
  };
})();
