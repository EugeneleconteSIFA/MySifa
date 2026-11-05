/*
 * Maintenance › Alertes › Historique des saisies — affichage « Analyse ».
 *
 * Bascule Historique / Analyse dans la carte « Historique des saisies ». Les
 * filtres sont ceux de l'historique (type, opérateur, machine, période) : à
 * chaque rendu de l'historique, la page appelle MaintAnalyse.surFiltres() et
 * l'analyse se recalcule. « Conformité » et les filtres par question sont
 * masqués en Analyse et n'y comptent pas : l'analyse porte sur toutes les
 * réponses.
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
  var A = { mode: 'analyse', graphes: [], timerTaille: null, data: null, cle: '', seq: 0, timer: null, erreur: '' };

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
    return q;
  }

  // ── Bascule ───────────────────────────────────────────────────────────
  function majBascule() {
    document.querySelectorAll('[data-ctrl-affichage]').forEach(function (b) {
      var on = b.getAttribute('data-ctrl-affichage') === A.mode;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    var vue = document.getElementById('ctrl-subview-historique');
    if (vue) vue.classList.toggle('an-mode-analyse', A.mode === 'analyse');
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
    if (A.mode === 'analyse') { charger(true); dessinerGraphes(); }
    if (!(opts && opts.sansRendu) && typeof window.renderCtrl === 'function') window.renderCtrl();
  }

  // Sans type choisi : le type réglé dans config.py, sinon le plus validé
  // parmi les saisies chargées. Rend false quand le filtre vient d'être posé (le rendu qui suit
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
    // Type réglé dans config.py (MAINTENANCE_ANALYSE_TYPE_DEFAUT), sinon le
    // plus validé parmi les saisies chargées.
    var regle = (document.body && document.body.getAttribute('data-analyse-type-defaut')) || '';
    var t = (regle && [].some.call(sel.options, function (o) { return o.value === regle; }))
      ? regle : Object.keys(n).sort(function (x, y) { return n[y] - n[x]; })[0];
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
    A.graphes = [];
    d.alertes.forEach(function (a) { h += rendreAlerte(a); });
    zone.innerHTML = h;
    dessinerGraphes();
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

  // ── Graphiques ────────────────────────────────────────────────────────
  // Dessinés APRÈS insertion, à la largeur réelle de leur bloc (en pixels) :
  // un SVG étiré par viewBox grossissait textes et barres avec la carte.
  // A.graphes garde les fonctions de dessin pour le redimensionnement.
  function graphe(fn) {
    A.graphes.push(fn);
    return '<div class="an-graph" data-g="' + (A.graphes.length - 1) + '"></div>';
  }
  function dessinerGraphes() {
    var zone = document.getElementById('ctrl-analyse');
    if (!zone || A.mode !== 'analyse') return;
    zone.querySelectorAll('.an-graph').forEach(function (el) {
      var fn = A.graphes[+el.getAttribute('data-g')];
      if (fn) el.innerHTML = fn(Math.max(220, Math.floor(el.clientWidth)));
    });
  }
  // Redessin quand la LARGEUR de la zone change (fenêtre, zoom, barre
  // latérale repliée) : la fenêtre seule ne voit pas tous ces cas.
  function suivreLargeur() {
    var zone = document.getElementById('ctrl-analyse');
    var redessiner = function () { clearTimeout(A.timerTaille); A.timerTaille = setTimeout(dessinerGraphes, 120); };
    if (zone && typeof ResizeObserver !== 'undefined') {
      var largeur = 0;
      new ResizeObserver(function (e) {
        var w = Math.round(e[0].contentRect.width);
        if (w && w !== largeur) { largeur = w; redessiner(); }
      }).observe(zone);
    } else {
      window.addEventListener('resize', redessiner);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', suivreLargeur, { once: true });
  else suivreLargeur();
  function svg(W, H, label) {
    return '<svg class="an-svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(label) + '">';
  }

  // Teinte d'une réponse : non conformes en rouge, les autres en accent,
  // de plus en plus claires dans l'ordre du questionnaire. Même teinte dans
  // la répartition, la légende et les barres par semaine.
  function teintes(q) {
    var t = {}, ok = 0, nc = 0;
    q.repartition.forEach(function (r) {
      t[r.reponse] = r.nc ? 'an-t-nc' + Math.min(nc++, 1) : 'an-t-ok' + Math.min(ok++, 2);
    });
    return t;
  }

  // Question à choix : répartition et réponses semaine par semaine.
  function carteChoix(q) {
    var h = '<div class="an-carte"><div class="an-carte-titre">' + esc(q.label) + '</div>'
      + '<div class="an-carte-sous">' + nb(q.repondants, 0) + ' réponse' + (q.repondants > 1 ? 's' : '') + '</div>';
    if (!q.repondants) return h + '<div class="an-vide-mini">Pas de réponse sur la période.</div></div>';
    var t = teintes(q);
    h += '<div class="an-corps an-corps-choix"><div>'
      + '<div class="an-sous-titre an-sous-titre-1">Répartition</div>'
      + '<div class="an-barres">' + q.repartition.map(function (r) {
        return '<div class="an-barre-ligne" title="' + esc(r.reponse + ' : ' + r.n + ' (' + pct(r.pct) + ')') + '">'
          + '<span class="an-barre-lib">' + esc(r.reponse) + (r.nc ? ' <em class="an-tag-nc">NC</em>' : '') + '</span>'
          + '<span class="an-barre-piste"><span class="an-barre ' + t[r.reponse] + '" style="width:' + Math.max(r.pct || 0, r.n ? 1 : 0) + '%"></span></span>'
          + '<span class="an-barre-val">' + pct(r.pct) + ' <span>· ' + nb(r.n, 0) + '</span></span></div>';
      }).join('') + '</div>';
    if (q.autres && q.autres.length) {
      h += '<div class="an-sous-titre">Précisions « Autre »</div><div class="an-autres">'
        + q.autres.map(function (o) { return '<span>' + esc(o.texte) + ' <b>×' + o.n + '</b></span>'; }).join('') + '</div>';
    }
    h += '</div>';
    if (q.evolution && q.evolution.length > 1) {
      h += '<div><div class="an-sous-titre an-sous-titre-1">Réponses par semaine</div>'
        + '<div class="an-legende">' + q.repartition.filter(function (r) { return r.n; }).map(function (r) {
          return '<span><i class="' + t[r.reponse] + '"></i>' + esc(r.reponse) + '</span>';
        }).join('') + '</div>'
        + graphe(function (W) { return semaines(q, t, W); }) + '</div>';
    }
    return h + '</div></div>';
  }

  // Barres empilées par semaine (non conformes en bas, sur l'axe), taux de
  // NC au-dessus. Une semaine sans réponse reste visible (tiret sur l'axe).
  function semaines(q, t, W) {
    var ev = q.evolution, n = ev.length, H = 170, HAUT = 16, BAS = 20;
    var slot = W / n, bw = Math.max(4, Math.min(44, slot - 6));
    var max = Math.max.apply(null, ev.map(function (e) { return e.n; }).concat([1]));
    var ordre = q.repartition.filter(function (r) { return r.nc; }).concat(q.repartition.filter(function (r) { return !r.nc; }));
    var pas = Math.max(1, Math.ceil(40 / slot));
    var s = svg(W, H, 'Réponses par semaine');
    var y0 = H - BAS, hUtile = y0 - HAUT;
    s += '<line class="an-axe" x1="0" x2="' + W + '" y1="' + y0 + '" y2="' + y0 + '"></line>';
    ev.forEach(function (e, i) {
      var x = i * slot + (slot - bw) / 2, y = y0;
      var detail = ['Semaine du ' + dateCourte(e.semaine) + ' : ' + (e.n ? e.n + ' réponse' + (e.n > 1 ? 's' : '') : 'aucune réponse')];
      var g = '';
      ordre.forEach(function (r) {
        var c = (e.reponses || {})[r.reponse] || 0;
        if (!c) return;
        var hh = c / max * hUtile;
        y -= hh;
        g += '<rect class="' + t[r.reponse] + '" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(1, hh - 1).toFixed(1) + '" rx="2"></rect>';
        detail.push(r.reponse + ' : ' + c);
      });
      if (!e.n) g += '<line class="an-vide-trait" x1="' + x.toFixed(1) + '" x2="' + (x + bw).toFixed(1) + '" y1="' + (y0 - 1) + '" y2="' + (y0 - 1) + '"></line>';
      if (e.nc && slot >= 26) g += '<text class="an-txt an-txt-nc" x="' + (x + bw / 2).toFixed(1) + '" y="' + (y - 4).toFixed(1) + '" text-anchor="middle">' + esc(nb(e.taux_nc, 0)) + ' %</text>';
      if (i % pas === 0) g += '<text class="an-txt" x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - 5) + '" text-anchor="middle">' + esc(dateCourte(e.semaine)) + '</text>';
      if (e.nc) detail.push('Non-conformité : ' + pct(e.taux_nc));
      s += '<g><title>' + esc(detail.join('\n')) + '</title><rect class="an-hit" x="' + (i * slot).toFixed(1) + '" y="0" width="' + slot.toFixed(1) + '" height="' + y0 + '"></rect>' + g + '</g>';
    });
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
    // Courbe large, histogramme à côté, puis l'écart entre mesures d'un même
    // contrôle (fronts) s'il y en a : trois colonnes de largeur fixe.
    var m = q.multiples;
    h += '<div class="an-corps an-corps-valeur' + (m ? ' an-avec-multiples' : '') + '">'
      + '<div><div class="an-sous-titre">Dans le temps</div>' + graphe(function (W) { return courbe(q, W); }) + '</div>'
      + '<div><div class="an-sous-titre">Répartition des valeurs</div>' + graphe(function (W) { return histogramme(q, W); }) + '</div>';
    if (m) {
      h += '<div><div class="an-sous-titre">Écart entre ' + esc(m.libelle.toLowerCase()) + 's d\'un même contrôle</div>'
        + '<div class="an-chiffres">' + chiffre('Écart moyen', nb(m.ecart.moyenne, 3) + u) + chiffre('Écart max', nb(m.ecart.max, 3) + u) + '</div>'
        + positions(m, u) + '</div>';
    }
    return h + '</div></div>';
  }

  function chiffre(lib, val, ton) {
    return '<div class="an-chiffre' + (ton ? ' an-' + ton : '') + '"><span>' + esc(lib) + '</span><b>' + val + '</b></div>';
  }

  function courbe(q, W) {
    var pts = q.serie || [];
    var H = 170, G = 44, D = 8, B = 20;
    var vals = pts.map(function (p) { return p.v; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    [q.min, q.max, q.cible].forEach(function (b) { if (b != null) { lo = Math.min(lo, b); hi = Math.max(hi, b); } });
    if (hi === lo) { hi += 1; lo -= 1; }
    var marge = (hi - lo) * 0.08; hi += marge; lo -= marge;
    var t0 = Date.parse(pts[0].t), t1 = Date.parse(pts[pts.length - 1].t);
    if (!(t1 > t0)) t1 = t0 + 1;
    function X(t) { return G + (Date.parse(t) - t0) / (t1 - t0) * (W - G - D); }
    function Y(v) { return 6 + (hi - v) / (hi - lo) * (H - 6 - B); }
    var s = svg(W, H, q.label + ' dans le temps');
    if (q.min != null || q.max != null) {
      var yh = Y(q.max != null ? q.max : hi), yb = Y(q.min != null ? q.min : lo);
      s += '<rect class="an-bande" x="' + G + '" y="' + yh.toFixed(1) + '" width="' + (W - G - D) + '" height="' + Math.max(0, yb - yh).toFixed(1) + '"><title>Tolérance</title></rect>';
    }
    [hi - marge, (hi + lo) / 2, lo + marge].forEach(function (v) {
      s += '<line class="an-grille" x1="' + G + '" x2="' + (W - D) + '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '"></line>'
        + '<text class="an-txt" x="' + (G - 6) + '" y="' + (Y(v) + 3).toFixed(1) + '" text-anchor="end">' + esc(nb(v, 2)) + '</text>';
    });
    if (q.cible != null) {
      s += '<line class="an-cible" x1="' + G + '" x2="' + (W - D) + '" y1="' + Y(q.cible).toFixed(1) + '" y2="' + Y(q.cible).toFixed(1) + '"><title>Cible ' + esc(nb(q.cible)) + '</title></line>';
    }
    if (pts.length > 1) {
      s += '<polyline class="an-ligne" points="' + pts.map(function (p) { return X(p.t).toFixed(1) + ',' + Y(p.v).toFixed(1); }).join(' ') + '"></polyline>';
    }
    var r = pts.length > 200 ? 2 : 3;
    pts.forEach(function (p) {
      var x = X(p.t), y = Y(p.v);
      var info = p.t.replace('T', ' ').slice(0, 16) + (p.machine ? ' · ' + p.machine : '') + ' : '
        + p.vals.map(function (v) { return nb(v, 3); }).join(' / ') + (q.unit ? ' ' + q.unit : '') + (p.nc ? ' · NC' : '');
      s += '<g><title>' + esc(info) + '</title><circle class="an-hit" cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="8"></circle>'
        + '<circle class="an-point' + (p.nc ? ' nc' : '') + '" cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + r + '"></circle></g>';
    });
    s += '<text class="an-txt" x="' + G + '" y="' + (H - 5) + '">' + esc(dateCourte(pts[0].t)) + '</text>'
      + '<text class="an-txt" x="' + (W - D) + '" y="' + (H - 5) + '" text-anchor="end">' + esc(dateCourte(pts[pts.length - 1].t)) + '</text>';
    return s + '</svg>';
  }

  function histogramme(q, W) {
    var cl = q.histogramme || [];
    if (!cl.length) return '';
    var H = 170, B = 20, HAUT = 6, n = cl.length, gap = 2, bw = (W - gap * (n - 1)) / n;
    var max = Math.max.apply(null, cl.map(function (c) { return c.n; }).concat([1]));
    var lo = cl[0].de, hi = cl[n - 1].a;
    function X(v) { return (v - lo) / ((hi - lo) || 1) * W; }
    var s = svg(W, H, 'Répartition des valeurs');
    cl.forEach(function (c, i) {
      var hh = c.n / max * (H - B - HAUT), x = i * (bw + gap);
      var hors = (q.min != null && c.a <= q.min) || (q.max != null && c.de >= q.max);
      s += '<g><title>' + esc(nb(c.de, 3) + ' – ' + nb(c.a, 3) + ' : ' + c.n + ' mesure' + (c.n > 1 ? 's' : '')) + '</title>'
        + '<rect class="an-hit" x="' + x.toFixed(1) + '" y="0" width="' + bw.toFixed(1) + '" height="' + (H - B) + '"></rect>'
        + '<rect class="an-col' + (hors ? ' nc' : '') + '" x="' + x.toFixed(1) + '" y="' + (H - B - hh).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(hh, c.n ? 1 : 0).toFixed(1) + '" rx="2"></rect></g>';
    });
    [q.min, q.max].forEach(function (b) {
      if (b == null) return;
      s += '<line class="an-borne" x1="' + X(b).toFixed(1) + '" x2="' + X(b).toFixed(1) + '" y1="0" y2="' + (H - B) + '"><title>Tolérance ' + esc(nb(b)) + '</title></line>';
    });
    s += '<line class="an-axe" x1="0" x2="' + W + '" y1="' + (H - B) + '" y2="' + (H - B) + '"></line>'
      + '<text class="an-txt" x="0" y="' + (H - 5) + '">' + esc(nb(lo, 3)) + '</text>'
      + '<text class="an-txt" x="' + W + '" y="' + (H - 5) + '" text-anchor="end">' + esc(nb(hi, 3)) + '</text>';
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
