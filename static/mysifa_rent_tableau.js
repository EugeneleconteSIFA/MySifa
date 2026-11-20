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
 * API : MySifaRentTableau.monter(conteneur, {periode, machine, surFiltre, ouvrir})
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
    maj.addEventListener('click', function () { delete cache[cle(o)]; o.surFiltre({}); });
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

    var pts = (d.dossiers || []).filter(function (l) { return l.mb_pct && l.cout_horaire; });
    var S = d.seuils || {mb_pct: 40, cout_horaire: 325};
    if (!pts.length) {
      carte.appendChild(el('div', 'rt-vide', 'Aucun dossier mesurable sur cette période.'));
      return carte;
    }
    var xs = [S.cout_horaire], ys = [S.mb_pct];
    pts.forEach(function (l) {
      xs.push(l.cout_horaire.bas, l.cout_horaire.haut);
      ys.push(l.mb_pct.bas, l.mb_pct.haut);
      if (l.devis_cout_horaire != null) xs.push(l.devis_cout_horaire);
      if (l.devis_mb_pct != null) ys.push(l.devis_mb_pct);
    });
    var x0 = Math.max(0, Math.floor(Math.min.apply(null, xs) / 100) * 100 - 100);
    var x1 = Math.ceil(Math.max.apply(null, xs) / 100) * 100 + 100;
    var y0 = Math.floor(Math.min.apply(null, ys) / 5) * 5 - 5;
    var y1 = Math.ceil(Math.max.apply(null, ys) / 5) * 5 + 5;
    var L = 56, R = 624, T = 16, B = 352;
    var X = function (v) { return L + (v - x0) / (x1 - x0) * (R - L); };
    var Y = function (v) { return B - (v - y0) / (y1 - y0) * (B - T); };
    var s = svg('svg', {viewBox: '0 0 640 396', 'class': 'rt-nuage', role: 'img',
      'aria-label': pts.length + ' dossiers placés selon leur marge brute et leur coût horaire'});
    s.appendChild(svg('rect', {x: X(S.cout_horaire), y: T, width: R - X(S.cout_horaire),
      height: Math.max(0, Y(S.mb_pct) - T), 'class': 'rt-zone-ok'}));
    var tz = svg('text', {x: R - 6, y: T + 16, 'text-anchor': 'end', 'class': 'rt-zone-lib'});
    tz.textContent = 'Réussi';
    s.appendChild(tz);
    var pasX = (x1 - x0) > 1600 ? 400 : (x1 - x0) > 800 ? 200 : 100;
    for (var vx = Math.ceil(x0 / pasX) * pasX; vx <= x1; vx += pasX) {
      s.appendChild(svg('line', {x1: X(vx), x2: X(vx), y1: T, y2: B, 'class': 'rt-grille'}));
      var tx = svg('text', {x: X(vx), y: B + 16, 'text-anchor': 'middle', 'class': 'rt-axe'});
      tx.textContent = nb(vx);
      s.appendChild(tx);
    }
    var pasY = (y1 - y0) > 40 ? 10 : 5;
    for (var vy = Math.ceil(y0 / pasY) * pasY; vy <= y1; vy += pasY) {
      s.appendChild(svg('line', {x1: L, x2: R, y1: Y(vy), y2: Y(vy), 'class': 'rt-grille'}));
      var ty = svg('text', {x: L - 8, y: Y(vy) + 4, 'text-anchor': 'end', 'class': 'rt-axe'});
      ty.textContent = vy + ' %';
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
      g.appendChild(svg('circle', {cx: cx, cy: cy, r: 5.5, 'class': 'rt-pt-svg rt-f-' + cls}));
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
      var ca = a.etat === 'complet' ? 0 : 1, cb = b.etat === 'complet' ? 0 : 1;
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
    conteneur.appendChild(compteurs(d));
    var grille = el('div', 'rt-grille-haut');
    grille.appendChild(nuage(d, o));
    grille.appendChild(causes(d));
    conteneur.appendChild(grille);
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
        + (o.machine ? '&machine=' + encodeURIComponent(o.machine) : '');
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
