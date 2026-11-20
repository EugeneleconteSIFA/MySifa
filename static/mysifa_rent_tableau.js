/* MySifa — Rentabilité › Tableau de bord.
 *
 * Chaque dossier terminé et rattaché à un devis validé est placé selon ses
 * deux indicateurs : marge brute (MB %) et coût horaire (MB par heure
 * machine). Les barres d'erreur montrent la FOURCHETTE réelle, le rond creux
 * relié par un pointillé montre où le devis plaçait le dossier. Le quart en
 * haut à droite, au-dessus des deux seuils, est celui des dossiers réussis.
 *
 * Calcul serveur : `GET /api/rentabilite/tableau-de-bord` (service
 * `app/services/rentabilite_reel.py`, une fiche par dossier). Ce fichier ne
 * fait que dessiner. Le clic sur un dossier ouvre sa fenêtre du Pilotage,
 * où se lit la fiche détaillée.
 *
 * Données : textContent partout, jamais innerHTML.
 * API : MySifaRentTableau.monter(conteneur, {periode, machine, grain, courbe, surFiltre, ouvrir})
 */
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var PERIODES = [['last30', '30 jours'], ['last90', '90 jours'], ['thisYear', 'Cette année'], ['all', 'Tout']];
  var VERDICT = {
    reussi: {lib: 'Réussi', cls: 'ok'},
    limite: {lib: 'À la limite', cls: 'warn'},
    sous_seuil: {lib: 'Sous un seuil', cls: 'bad'}
  };
  // Une réponse par couple période × machine, gardée le temps de la page :
  // le rendu global de MyProd reconstruit l'onglet à chaque `set()`, il ne
  // doit pas relancer un calcul de plusieurs secondes à chaque fois.
  var cache = {};
  var enCours = {};
  var forcer = {};
  var relance = null;

  // Pas d'axe « rond » pour au plus `n` graduations, quelle que soit l'étendue.
  function pasNet(etendue, n) {
    var brut = Math.max(etendue, 1e-9) / (n || 6), mag = Math.pow(10, Math.floor(Math.log10(brut)));
    var r = brut / mag;
    return (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag;
  }
  // Quantile simple : borne les axes sur le gros des dossiers, un seul
  // dossier aberrant ne doit pas écraser tous les autres.
  function quantile(vals, q) {
    if (!vals.length) return null;
    var v = vals.slice().sort(function (a, b) { return a - b; });
    return v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = String(txt);
    return e;
  }
  function svg(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function nb(v, dec) {
    if (v === null || v === undefined || v === '' || !isFinite(Number(v))) return '—';
    return Number(v).toLocaleString('fr-FR', {minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0});
  }
  function signe(v, dec) {
    var n = Number(v);
    return (n > 0 ? '+' : n < 0 ? '−' : '') + nb(Math.abs(n), dec);
  }
  function api(path) {
    var core = window.__prodCore;
    if (core && typeof core.api === 'function') return core.api(path);
    return fetch(path, {credentials: 'same-origin'}).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }
  // Infobulle instantanée partagée avec la fiche (mysifa_rent_fiche.js).
  function bulle(cible, texte) {
    var F = window.MySifaRentFiche;
    if (F && F.infobulle) F.infobulle(cible, texte); else if (cible) cible.title = typeof texte === 'string' ? texte : (texte.titre || '');
    return cible;
  }
  function cle(o) { return (o.periode || 'last30') + '|' + (o.machine || ''); }
  function position(f, seuil) {
    if (!f) return 'neutre';
    return f.bas >= seuil ? 'ok' : (f.haut < seuil ? 'bad' : 'warn');
  }

  // ── Barre d'outils ─────────────────────────────────────────────────
  function barre(d, o) {
    var b = el('div', 'rt-outils');
    var gp = el('div', 'rt-chips');
    gp.setAttribute('role', 'group');
    gp.setAttribute('aria-label', 'Période');
    PERIODES.forEach(function (p) {
      var c = el('button', 'rt-chip', p[1]);
      c.type = 'button';
      c.setAttribute('aria-pressed', String((o.periode || 'last30') === p[0]));
      c.addEventListener('click', function () { o.surFiltre({periode: p[0]}); });
      gp.appendChild(c);
    });
    b.appendChild(gp);
    var machines = (d && d.machines) || [];
    if (machines.length > 1) {
      var gm = el('div', 'rt-chips');
      gm.setAttribute('role', 'group');
      gm.setAttribute('aria-label', 'Machine');
      [''].concat(machines).forEach(function (m) {
        var c = el('button', 'rt-chip', m || 'Toutes machines');
        c.type = 'button';
        c.setAttribute('aria-pressed', String((o.machine || '') === m));
        c.addEventListener('click', function () { o.surFiltre({machine: m}); });
        gm.appendChild(c);
      });
      b.appendChild(gm);
    }
    var maj = el('button', 'rt-chip rt-rafraichir', 'Recalculer');
    maj.type = 'button';
    bulle(maj, {titre: 'Recalculer', note: 'Relit saisies, déstockages et factures.'});
    maj.addEventListener('click', function () { delete cache[cle(o)]; forcer[cle(o)] = true; o.surFiltre({}); });
    b.appendChild(maj);
    return b;
  }

  // ── Compteurs (bloc capturable) ────────────────────────────────────
  function compteurs(d) {
    var c = d.comptes || {};
    var row = el('div', 'rt-kpis');
    row.setAttribute('data-bloc', 'prod.rentabilite.verdicts');
    row.setAttribute('data-bloc-valeur-reussis', String(c.reussi || 0));
    row.setAttribute('data-bloc-valeur-limite', String(c.limite || 0));
    row.setAttribute('data-bloc-valeur-sous-seuil', String(c.sous_seuil || 0));
    row.setAttribute('data-bloc-valeur-attente', String(c.attente || 0));
    function tuile(cls, k, v, s) {
      var t = el('div', 'rt-kpi ' + cls);
      t.appendChild(el('span', 'rt-kpi-k', k));
      t.appendChild(el('span', 'rt-kpi-v', v));
      bulle(t, {titre: k, note: s});
      row.appendChild(t);
    }
    var S = d.seuils || {};
    tuile('rt-ok', 'Réussis', nb(c.reussi), 'Sur ' + nb(c.complets) + ' dossiers complets : MB ≥ '
      + nb(S.mb_pct) + ' % et coût horaire ≥ ' + nb(S.cout_horaire) + ' €/h sur toute la fourchette');
    tuile('rt-warn', 'À la limite', nb(c.limite), 'La fourchette est à cheval sur un seuil : la précision des saisies ne permet pas de trancher');
    tuile('rt-bad', 'Sous un seuil', nb(c.sous_seuil), 'Marge brute ou coût horaire entièrement sous son seuil');
    tuile('', 'En attente', nb(c.attente), 'Dossiers terminés sans facture, sans déstockage ou sans 89 : pas encore jugés');
    if (c.a_verifier) tuile('rt-bad', 'À vérifier', nb(c.a_verifier),
      'Résultat hors norme : facture ou matière probablement rattachée au mauvais dossier. Exclus des compteurs et du nuage.');
    tuile('', 'Écart MB', d.ecart_mb_pts == null ? '—' : signe(d.ecart_mb_pts, 1) + ' pt',
      'Marge brute réelle moins marge devisée, moyenne par dossier complet');
    tuile('', '€/h médian', d.cout_horaire_median == null ? '—' : nb(d.cout_horaire_median),
      'Coût horaire réel médian des dossiers complets · seuil ' + nb(S.cout_horaire) + ' €/h');
    return row;
  }

  // ── Nuage MB % × coût horaire ──────────────────────────────────────
  function nuage(d, o) {
    var carte = el('div', 'rt-carte');
    var tete = el('div', 'rt-carte-tete');
    tete.appendChild(el('b', '', 'Marge brute et coût horaire par dossier'));
    var leg = el('div', 'rt-legende');
    [['ok', 'Réussi'], ['warn', 'À la limite'], ['bad', 'Sous un seuil'], ['devis', 'Devis'], ['prov', 'Provisoire']]
      .forEach(function (x) {
        var s = el('span', 'rt-leg');
        s.appendChild(el('i', 'rt-pt rt-pt-' + x[0]));
        s.appendChild(document.createTextNode(x[1]));
        leg.appendChild(s);
      });
    tete.appendChild(leg);
    carte.appendChild(tete);

    var pts = (d.dossiers || []).filter(function (l) { return l.mb_pct && l.cout_horaire && l.etat !== 'a_verifier'; });
    var S = d.seuils || {mb_pct: 40, cout_horaire: 325};
    if (!pts.length) {
      carte.appendChild(el('div', 'rt-vide', 'Aucun dossier mesurable sur cette période.'));
      return carte;
    }
    // Axes calés sur le gros des dossiers (5e – 95e centile, seuils compris) ;
    // un point au-delà est épinglé au bord, sa vraie valeur au survol.
    var px = pts.map(function (l) { return l.cout_horaire.probable; });
    var py = pts.map(function (l) { return l.mb_pct.probable; });
    var xa = [S.cout_horaire, quantile(px, 0.05), quantile(px, 0.95)];
    var ya = [S.mb_pct, quantile(py, 0.05), quantile(py, 0.95)];
    var x0 = Math.max(0, Math.min.apply(null, xa) * 0.8), x1 = Math.max.apply(null, xa) * 1.2;
    var y0 = Math.min.apply(null, ya) - 5, y1 = Math.max.apply(null, ya) + 5;
    var pasX = pasNet(x1 - x0, 6), pasY = pasNet(y1 - y0, 6);
    x0 = Math.floor(x0 / pasX) * pasX; x1 = Math.ceil(x1 / pasX) * pasX;
    y0 = Math.floor(y0 / pasY) * pasY; y1 = Math.ceil(y1 / pasY) * pasY;
    var L = 56, R = 624, T = 16, B = 352;
    var X = function (v) { return L + (Math.max(x0, Math.min(x1, v)) - x0) / (x1 - x0) * (R - L); };
    var Y = function (v) { return B - (Math.max(y0, Math.min(y1, v)) - y0) / (y1 - y0) * (B - T); };
    var s = svg('svg', {viewBox: '0 0 640 396', 'class': 'rt-nuage', role: 'img',
      'aria-label': pts.length + ' dossiers placés selon leur marge brute et leur coût horaire'});
    s.appendChild(svg('rect', {x: X(S.cout_horaire), y: T, width: R - X(S.cout_horaire),
      height: Math.max(0, Y(S.mb_pct) - T), 'class': 'rt-zone-ok'}));
    var tz = svg('text', {x: R - 6, y: T + 16, 'text-anchor': 'end', 'class': 'rt-zone-lib'});
    tz.textContent = 'Réussi';
    s.appendChild(tz);
    for (var vx = x0; vx <= x1 + 1e-9; vx += pasX) {
      s.appendChild(svg('line', {x1: X(vx), x2: X(vx), y1: T, y2: B, 'class': 'rt-grille'}));
      var tx = svg('text', {x: X(vx), y: B + 16, 'text-anchor': 'middle', 'class': 'rt-axe'});
      tx.textContent = nb(vx);
      s.appendChild(tx);
    }
    for (var vy = y0; vy <= y1 + 1e-9; vy += pasY) {
      s.appendChild(svg('line', {x1: L, x2: R, y1: Y(vy), y2: Y(vy), 'class': 'rt-grille'}));
      var ty = svg('text', {x: L - 8, y: Y(vy) + 4, 'text-anchor': 'end', 'class': 'rt-axe'});
      ty.textContent = nb(vy) + ' %';
      s.appendChild(ty);
    }
    s.appendChild(svg('line', {x1: X(S.cout_horaire), x2: X(S.cout_horaire), y1: T, y2: B, 'class': 'rt-seuil'}));
    s.appendChild(svg('line', {x1: L, x2: R, y1: Y(S.mb_pct), y2: Y(S.mb_pct), 'class': 'rt-seuil'}));
    var ls = svg('text', {x: X(S.cout_horaire) + 5, y: B - 6, 'class': 'rt-seuil-lib'});
    ls.textContent = nb(S.cout_horaire) + ' €/h';
    s.appendChild(ls);
    var lm = svg('text', {x: R - 4, y: Y(S.mb_pct) - 5, 'text-anchor': 'end', 'class': 'rt-seuil-lib'});
    lm.textContent = nb(S.mb_pct) + ' %';
    s.appendChild(lm);
    var ax = svg('text', {x: (L + R) / 2, y: B + 38, 'text-anchor': 'middle', 'class': 'rt-axe-titre'});
    ax.textContent = 'Coût horaire réel (€/h)';
    s.appendChild(ax);
    var ay = svg('text', {x: 14, y: (T + B) / 2, 'text-anchor': 'middle', 'class': 'rt-axe-titre',
      transform: 'rotate(-90 14 ' + ((T + B) / 2) + ')'});
    ay.textContent = 'Marge brute réelle';
    s.appendChild(ay);

    pts.forEach(function (l) {
      var v = (l.verdict || {}).global, cls = (VERDICT[v] || {cls: 'neutre'}).cls;
      var cx = X(l.cout_horaire.probable), cy = Y(l.mb_pct.probable);
      var g = svg('g', {'class': 'rt-point' + (l.etat !== 'complet' ? ' rt-provisoire' : ''), tabindex: '0',
        role: 'button', 'aria-label': (l.client || '') + ' ' + (l.reference || '')});
      var vd = VERDICT[v];
      bulle(g, {titre: l.client || '(client non renseigné)',
        sous: [l.reference, l.machine].filter(Boolean).join(' · '),
        etat: l.etat !== 'complet' ? 'Provisoire' : (vd ? vd.lib : ''),
        ton: l.etat !== 'complet' ? 'inconnu' : ({ok: 'vert', warn: 'orange', bad: 'rouge'}[cls] || 'inconnu'),
        lignes: [['Marge brute', nb(l.mb_pct.bas, 1) + ' – ' + nb(l.mb_pct.haut, 1) + ' %'],
                 ['Marge devisée', l.devis_mb_pct != null ? nb(l.devis_mb_pct, 1) + ' %' : ''],
                 ['Coût horaire', nb(l.cout_horaire.bas) + ' – ' + nb(l.cout_horaire.haut) + ' €/h'],
                 ['Coût horaire devisé', l.devis_cout_horaire != null ? nb(l.devis_cout_horaire) + ' €/h' : '']]});
      if (l.devis_cout_horaire != null && l.devis_mb_pct != null) {
        var dx = X(l.devis_cout_horaire), dy = Y(l.devis_mb_pct);
        g.appendChild(svg('line', {x1: dx, y1: dy, x2: cx, y2: cy, 'class': 'rt-lien-devis'}));
        g.appendChild(svg('circle', {cx: dx, cy: dy, r: 3.5, 'class': 'rt-devis'}));
      }
      g.appendChild(svg('line', {x1: X(l.cout_horaire.bas), x2: X(l.cout_horaire.haut), y1: cy, y2: cy,
        'class': 'rt-err rt-c-' + cls}));
      g.appendChild(svg('line', {x1: cx, x2: cx, y1: Y(l.mb_pct.bas), y2: Y(l.mb_pct.haut),
        'class': 'rt-err rt-c-' + cls}));
      var dehors = l.cout_horaire.probable > x1 || l.cout_horaire.probable < x0
        || l.mb_pct.probable > y1 || l.mb_pct.probable < y0;
      g.appendChild(svg('circle', {cx: cx, cy: cy, r: 5.5,
        'class': 'rt-pt-svg rt-f-' + cls + (dehors ? ' rt-hors-axe' : '')}));
      var go = function () { o.ouvrir(l.planning_entry_id); };
      g.addEventListener('click', go);
      g.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
      s.appendChild(g);
    });
    carte.appendChild(s);
    return carte;
  }

  // ── Causes agrégées ────────────────────────────────────────────────
  function causes(d) {
    var carte = el('div', 'rt-carte rt-causes');
    function bloc(titre, liste, unite, dec) {
      carte.appendChild(bulle(el('b', '', titre),
        {titre: titre, note: 'Moyenne par dossier complet des cascades de chaque fiche.'}));
      if (!liste || !liste.length) {
        carte.appendChild(el('div', 'rt-vide', 'Aucun dossier complet.'));
        return;
      }
      var maxi = Math.max.apply(null, liste.map(function (c) { return Math.abs(c.valeur); }).concat([0.01]));
      var g = el('div', 'rt-cause-liste');
      liste.forEach(function (c) {
        var r = el('div', 'rt-cause');
        r.appendChild(el('span', 'rt-cause-lib', c.cause));
        var piste = el('span', 'rt-cause-piste');
        var b = el('span', 'rt-cause-barre rf-nat-' + (c.valeur >= 0 ? 'gain' : c.nature));
        b.style.width = Math.max(2, Math.abs(c.valeur) / maxi * 100) + '%';
        piste.appendChild(b);
        r.appendChild(piste);
        r.appendChild(el('span', 'rt-cause-val', signe(c.valeur, dec) + ' ' + unite));
        g.appendChild(r);
      });
      carte.appendChild(g);
    }
    bloc('Écart de marge', d.causes_marge, 'pt', 1);
    bloc('Écart de coût horaire', d.causes_cout_horaire, '€/h', 0);
    return carte;
  }

  // ── Dans le temps ──────────────────────────────────────────────────
  /* Les dossiers de la période, rangés par jour, semaine (lundi) ou mois de
     fin de production. En haut, combien de dossiers par verdict ; en bas, la
     marge brute ou le coût horaire de la période, PONDÉRÉS (Σ MB ÷ Σ PV,
     Σ MB ÷ Σ heures) sur les seuls dossiers complets. Les périodes vides
     restent à leur place : un creux de production se voit. */
  var GRAINS = [['jour', 'Jour'], ['semaine', 'Semaine'], ['mois', 'Mois']];
  var COURBES = [['marge', 'Marge brute'], ['horaire', 'Coût horaire']];
  var MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];

  function jourUTC(iso) { var p = iso.split('-'); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); }
  function iso(dt) { return dt.toISOString().slice(0, 10); }
  function lundi(dt) { var d = new Date(dt); d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7)); return d; }
  function numSemaine(dt) {
    var d = new Date(Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()));
    d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
    var debut = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil(((d - debut) / 86400000 + 1) / 7);
  }
  function cleDe(dateIso, grain) {
    if (grain === 'mois') return dateIso.slice(0, 7);
    if (grain === 'semaine') return iso(lundi(jourUTC(dateIso)));
    return dateIso;
  }
  function suivante(cle, grain) {
    if (grain === 'mois') {
      var a = +cle.slice(0, 4), m = +cle.slice(5, 7);
      return m === 12 ? (a + 1) + '-01' : a + '-' + String(m + 1).padStart(2, '0');
    }
    var d = jourUTC(cle);
    d.setUTCDate(d.getUTCDate() + (grain === 'semaine' ? 7 : 1));
    return iso(d);
  }
  function libelleCourt(cle, grain) {
    if (grain === 'mois') return MOIS[+cle.slice(5, 7) - 1];
    if (grain === 'semaine') return 'S' + numSemaine(jourUTC(cle));
    return cle.slice(8, 10) + '/' + cle.slice(5, 7);
  }
  function libelleLong(cle, grain) {
    if (grain === 'mois') return MOIS[+cle.slice(5, 7) - 1] + ' ' + cle.slice(0, 4);
    if (grain === 'semaine') {
      var fin = jourUTC(cle); fin.setUTCDate(fin.getUTCDate() + 6);
      return 'Semaine ' + numSemaine(jourUTC(cle)) + ' · ' + cle.slice(8, 10) + '/' + cle.slice(5, 7)
        + ' – ' + iso(fin).slice(8, 10) + '/' + iso(fin).slice(5, 7);
    }
    return cle.slice(8, 10) + '/' + cle.slice(5, 7) + '/' + cle.slice(0, 4);
  }

  function periodes(dossiers, grain) {
    var dates = dossiers.map(function (l) { return l.date; }).filter(Boolean).sort();
    if (!dates.length) return [];
    var fin = cleDe(dates[dates.length - 1], grain), cles = [], c = cleDe(dates[0], grain);
    for (var garde = 0; garde < 2000; garde++) { cles.push(c); if (c === fin) break; c = suivante(c, grain); }
    var parCle = {};
    cles.forEach(function (k) {
      parCle[k] = {cle: k, reussi: 0, limite: 0, sous_seuil: 0, attente: 0, mb: 0, pv: 0, heures: 0, complets: 0};
    });
    dossiers.forEach(function (l) {
      if (!l.date) return;
      var p = parCle[cleDe(l.date, grain)];
      if (!p) return;
      var g = (l.verdict || {}).global;
      if (l.etat === 'complet' && l.mb_pct && l.cout_horaire && p[g] !== undefined) {
        p[g] += 1;
        p.complets += 1;
        p.mb += Number(l.marge_brute) || 0;
        p.pv += Number(l.prix_vente) || 0;
        p.heures += Number(l.heures) || 0;
      } else if (l.etat === 'provisoire') {
        p.attente += 1;
      }
    });
    return cles.map(function (k) {
      var p = parCle[k];
      p.mb_pct = p.pv > 0 ? p.mb / p.pv * 100 : null;
      p.cout_horaire = p.heures > 0 ? p.mb / p.heures : null;
      return p;
    });
  }

  function temporel(d, o) {
    var grain = o.grain || 'semaine', courbe = o.courbe || 'marge';
    var carte = el('div', 'rt-carte rt-temps');
    var tete = el('div', 'rt-carte-tete');
    tete.appendChild(el('b', '', 'Dans le temps'));
    var outils = el('div', 'rt-temps-outils');
    [[GRAINS, 'grain', grain, 'Regrouper par'], [COURBES, 'courbe', courbe, 'Courbe']].forEach(function (g) {
      var grp = el('div', 'rt-chips');
      grp.setAttribute('role', 'group');
      grp.setAttribute('aria-label', g[3]);
      g[0].forEach(function (x) {
        var c = el('button', 'rt-chip rt-chip-petit', x[1]);
        c.type = 'button';
        c.setAttribute('aria-pressed', String(g[2] === x[0]));
        c.addEventListener('click', function () { var p = {}; p[g[1]] = x[0]; o.surFiltre(p); });
        grp.appendChild(c);
      });
      outils.appendChild(grp);
    });
    tete.appendChild(outils);
    carte.appendChild(tete);

    var ps = periodes(d.dossiers || [], grain);
    if (!ps.length) {
      carte.appendChild(el('div', 'rt-vide', 'Aucun dossier daté sur cette période.'));
      return carte;
    }
    var S = d.seuils || {mb_pct: 40, cout_horaire: 325};
    // Dessinée pour la pleine largeur de l'onglet : un viewBox étroit étiré
    // sur 1 200 px grossissait le texte d'autant.
    var W = 1200, L = 56, R = 1186, T1 = 10, B1 = 130, T2 = 158, B2 = 290, H = 314;
    var n = ps.length, pas = (R - L) / n, bw = Math.max(2, Math.min(28, pas * 0.68));
    var X = function (i) { return L + pas * i + pas / 2; };
    var maxN = Math.max.apply(null, ps.map(function (p) { return p.reussi + p.limite + p.sous_seuil + p.attente; }).concat([1]));
    var Yn = function (v) { return B1 - v / maxN * (B1 - T1); };

    var cleV = courbe === 'horaire' ? 'cout_horaire' : 'mb_pct';
    var seuil = courbe === 'horaire' ? S.cout_horaire : S.mb_pct;
    var unite = courbe === 'horaire' ? '€/h' : '%';
    var vals = ps.map(function (p) { return p[cleV]; }).filter(function (v) { return v != null; });
    var lo, hi;
    if (courbe === 'horaire') {
      lo = 0; hi = Math.ceil(Math.max.apply(null, vals.concat([seuil])) * 1.15 / 100) * 100;
    } else {
      lo = Math.floor(Math.min.apply(null, vals.concat([seuil])) / 5) * 5 - 5;
      hi = Math.ceil(Math.max.apply(null, vals.concat([seuil])) / 5) * 5 + 5;
    }
    var Yv = function (v) { return B2 - (v - lo) / (hi - lo) * (B2 - T2); };

    var s = svg('svg', {viewBox: '0 0 ' + W + ' ' + H, 'class': 'rt-temps-svg', role: 'img',
      'aria-label': 'Dossiers par verdict et ' + (courbe === 'horaire' ? 'coût horaire' : 'marge brute')
        + ' par ' + grain});
    // Repères : compte de dossiers en haut, valeur de la courbe en bas.
    [[T1, maxN], [B1, 0]].forEach(function (r) {
      s.appendChild(svg('line', {x1: L, x2: R, y1: r[0], y2: r[0], 'class': 'rt-grille'}));
      var t = svg('text', {x: L - 8, y: r[0] + 4, 'text-anchor': 'end', 'class': 'rt-axe'});
      t.textContent = r[1];
      s.appendChild(t);
    });
    [lo, hi].forEach(function (v) {
      s.appendChild(svg('line', {x1: L, x2: R, y1: Yv(v), y2: Yv(v), 'class': 'rt-grille'}));
      var t = svg('text', {x: L - 8, y: Yv(v) + 4, 'text-anchor': 'end', 'class': 'rt-axe'});
      t.textContent = nb(v) + (courbe === 'horaire' ? '' : ' %');
      s.appendChild(t);
    });
    s.appendChild(svg('line', {x1: L, x2: R, y1: Yv(seuil), y2: Yv(seuil), 'class': 'rt-seuil'}));
    var ls = svg('text', {x: R, y: Yv(seuil) - 5, 'text-anchor': 'end', 'class': 'rt-seuil-lib'});
    ls.textContent = nb(seuil) + ' ' + unite;
    s.appendChild(ls);

    // Barres empilées par verdict.
    ps.forEach(function (p, i) {
      var y = B1;
      [['reussi', 'ok'], ['limite', 'warn'], ['sous_seuil', 'bad'], ['attente', 'neutre']].forEach(function (k) {
        if (!p[k[0]]) return;
        var h = p[k[0]] / maxN * (B1 - T1);
        s.appendChild(svg('rect', {x: X(i) - bw / 2, y: y - h, width: bw, height: Math.max(1, h - 1),
          rx: 2, 'class': 'rt-f-' + k[1] + (k[0] === 'attente' ? ' rt-provisoire' : '')}));
        y -= h;
      });
    });

    // Courbe : segments entre périodes voisines qui ont toutes deux une valeur.
    var prec = null;
    ps.forEach(function (p, i) {
      var v = p[cleV];
      if (v == null) { prec = null; return; }
      if (prec) s.appendChild(svg('line', {x1: X(prec.i), y1: Yv(prec.v), x2: X(i), y2: Yv(v), 'class': 'rt-courbe'}));
      prec = {i: i, v: v};
    });
    ps.forEach(function (p, i) {
      var v = p[cleV];
      if (v == null) return;
      s.appendChild(svg('circle', {cx: X(i), cy: Yv(v), r: n > 60 ? 2.5 : 4,
        'class': 'rt-pt-svg rt-f-' + (v >= seuil ? 'ok' : 'bad')}));
    });

    // Étiquettes d'axe, éclaircies pour ne jamais se chevaucher.
    var tous = Math.max(1, Math.ceil(56 / pas));
    ps.forEach(function (p, i) {
      if (i % tous !== 0) return;
      var t = svg('text', {x: X(i), y: H - 6, 'text-anchor': 'middle', 'class': 'rt-axe'});
      t.textContent = libelleCourt(p.cle, grain);
      s.appendChild(t);
    });

    // Une colonne de survol par période, toute la hauteur.
    ps.forEach(function (p, i) {
      var zone = svg('rect', {x: L + pas * i, y: T1, width: pas, height: B2 - T1, 'class': 'rt-temps-zone'});
      var tot = p.reussi + p.limite + p.sous_seuil;
      bulle(zone, {titre: libelleLong(p.cle, grain),
        sous: tot ? nb(tot) + ' dossier' + (tot > 1 ? 's' : '') + ' complet' + (tot > 1 ? 's' : '') : 'Aucun dossier complet',
        lignes: [['Réussis', p.reussi ? nb(p.reussi) : ''], ['À la limite', p.limite ? nb(p.limite) : ''],
                 ['Sous un seuil', p.sous_seuil ? nb(p.sous_seuil) : ''], ['En attente', p.attente ? nb(p.attente) : ''],
                 ['Marge brute', p.mb_pct != null ? nb(p.mb_pct, 1) + ' %' : ''],
                 ['Coût horaire', p.cout_horaire != null ? nb(p.cout_horaire) + ' €/h' : ''],
                 ['Marge dégagée', p.complets ? nb(p.mb) + ' €' : '']]});
      s.appendChild(zone);
    });
    carte.appendChild(s);
    return carte;
  }

  // ── Liste des dossiers ─────────────────────────────────────────────
  function mini(f, devis, seuil, a, b, unite, dec) {
    var w = el('div', 'rt-mini');
    if (!f) { w.appendChild(el('span', 'rt-mini-lib', '—')); return w; }
    var p = function (v) { return Math.max(0, Math.min(100, (v - a) / (b - a) * 100)); };
    var t = el('div', 'rt-mini-piste');
    var band = el('div', 'rt-mini-bande rt-b-' + position(f, seuil));
    band.style.left = p(f.bas) + '%';
    band.style.width = Math.max(1.5, p(f.haut) - p(f.bas)) + '%';
    t.appendChild(band);
    var x = el('div', 'rt-mini-seuil');
    x.style.left = p(seuil) + '%';
    t.appendChild(x);
    if (devis != null) {
      var g = el('div', 'rt-mini-devis');
      g.style.left = p(devis) + '%';
      t.appendChild(g);
    }
    w.appendChild(t);
    w.appendChild(el('span', 'rt-mini-lib', nb(f.probable, dec)));
    bulle(w, {lignes: [['Fourchette', nb(f.bas, dec) + ' – ' + nb(f.haut, dec) + ' ' + unite],
                       ['Devisé', devis != null ? nb(devis, dec) + ' ' + unite : ''],
                       ['Seuil', nb(seuil, dec) + ' ' + unite]]});
    return w;
  }

  function liste(d, o) {
    var carte = el('div', 'rt-carte');
    var lignes = (d.dossiers || []).slice();
    var rang = {sous_seuil: 0, limite: 1, reussi: 2};
    lignes.sort(function (a, b) {
      var ordre = {a_verifier: 0, complet: 1, provisoire: 2};
      var ca = ordre[a.etat] == null ? 3 : ordre[a.etat], cb = ordre[b.etat] == null ? 3 : ordre[b.etat];
      if (ca !== cb) return ca - cb;
      var ra = rang[(a.verdict || {}).global], rb = rang[(b.verdict || {}).global];
      ra = ra == null ? 3 : ra; rb = rb == null ? 3 : rb;
      if (ra !== rb) return ra - rb;
      return ((a.mb_pct || {}).bas || 0) - ((b.mb_pct || {}).bas || 0);
    });
    var S = d.seuils || {mb_pct: 40, cout_horaire: 325};
    var tete = el('div', 'rt-ligne rt-ligne-tete');
    ['Dossier', 'Marge brute', 'Coût horaire', 'Verdict'].forEach(function (c) { tete.appendChild(el('span', '', c)); });
    carte.appendChild(tete);
    if (!lignes.length) {
      carte.appendChild(el('div', 'rt-vide', 'Aucun dossier terminé avec un devis validé sur cette période.'));
      return carte;
    }
    var ehMax = Math.max.apply(null, lignes.map(function (l) {
      return Math.max((l.cout_horaire || {}).haut || 0, l.devis_cout_horaire || 0);
    }).concat([S.cout_horaire * 1.5]));
    lignes.forEach(function (l) {
      var r = el('button', 'rt-ligne');
      r.type = 'button';
      r.addEventListener('click', function () { o.ouvrir(l.planning_entry_id); });
      var qui = el('span', 'rt-qui');
      qui.appendChild(el('b', '', l.client || '(client non renseigné)'));
      qui.appendChild(el('span', '', [l.reference, l.machine].filter(Boolean).join(' · ')));
      if (l.modifies && l.modifies.length) {
        bulle(qui.appendChild(el('span', 'rt-modifie', 'modifié')),
          {titre: 'Changé par rapport au devis', note: l.modifies.join(', ')});
      }
      r.appendChild(qui);
      r.appendChild(mini(l.mb_pct, l.devis_mb_pct, S.mb_pct, Math.min(0, S.mb_pct - 30), S.mb_pct + 30, '%', 1));
      r.appendChild(mini(l.cout_horaire, l.devis_cout_horaire, S.cout_horaire, 0, ehMax, '€/h', 0));
      if (l.etat === 'complet') {
        var v = VERDICT[(l.verdict || {}).global];
        r.appendChild(el('span', 'rt-tag rt-tag-' + (v ? v.cls : 'neutre'), v ? v.lib : 'Non calculable'));
      } else if (l.etat === 'a_verifier') {
        r.appendChild(bulle(el('span', 'rt-tag rt-tag-bad', 'À vérifier'),
          {titre: 'Résultat hors norme', note: (l.hors_norme || []).join(', ')
            + ' : facture ou matière probablement rattachée au mauvais dossier.'}));
      } else if (l.etat === 'provisoire') {
        var t = el('span', 'rt-tag rt-tag-neutre', 'Provisoire');
        bulle(t, {titre: 'Provisoire', note: l.manque && l.manque.length
          ? 'Il manque : ' + l.manque.join(', ') : 'Marché partiellement facturé'});
        r.appendChild(t);
      } else {
        r.appendChild(el('span', 'rt-tag rt-tag-neutre', 'Non mesurable'));
      }
      carte.appendChild(r);
    });
    return carte;
  }

  // ── Montage ────────────────────────────────────────────────────────
  function dessiner(conteneur, d, o) {
    conteneur.textContent = '';
    conteneur.appendChild(barre(d, o));
    var lec = d.lecture_devis || {};
    if (lec.en_cours) {
      conteneur.appendChild(bulle(el('div', 'rt-lecture',
        'Lecture des montants de ' + nb(lec.restants) + ' devis en cours — le tableau se complète tout seul.'),
        {note: 'Ces devis ont été importés avant la lecture des montants. Leurs dossiers apparaissent dès leur lecture.'}));
      // Une seule relance à la fois, et seulement si l'onglet est encore là.
      clearTimeout(relance);
      relance = setTimeout(function () {
        if (!conteneur.isConnected) return;
        delete cache[cle(o)];
        monter(conteneur, o);
      }, 20000);
    }
    conteneur.appendChild(compteurs(d));
    var grille = el('div', 'rt-grille-haut');
    grille.appendChild(nuage(d, o));
    grille.appendChild(causes(d));
    conteneur.appendChild(grille);
    conteneur.appendChild(temporel(d, o));
    conteneur.appendChild(liste(d, o));
  }

  function monter(conteneur, o) {
    if (!conteneur) return;
    o = o || {};
    var k = cle(o);
    if (cache[k]) { dessiner(conteneur, cache[k], o); return; }
    conteneur.textContent = '';
    conteneur.appendChild(barre(null, o));
    conteneur.appendChild(el('div', 'rt-attente', 'Calcul en cours…'));
    if (!enCours[k]) {
      var url = '/api/rentabilite/tableau-de-bord?periode=' + encodeURIComponent(o.periode || 'last30')
        + (o.machine ? '&machine=' + encodeURIComponent(o.machine) : '')
        + (forcer[k] ? '&force=1' : '');
      delete forcer[k];
      enCours[k] = api(url).then(function (d) { cache[k] = d; return d; })
        .finally(function () { delete enCours[k]; });
    }
    enCours[k].then(function (d) {
      if (conteneur.isConnected) dessiner(conteneur, d, o);
    }).catch(function () {
      if (!conteneur.isConnected) return;
      conteneur.textContent = '';
      conteneur.appendChild(barre(null, o));
      conteneur.appendChild(el('div', 'rt-vide', 'Tableau de bord indisponible — cliquer sur Recalculer.'));
    });
  }

  window.MySifaRentTableau = {monter: monter, dessiner: dessiner, vider: function () { cache = {}; }};
})();
