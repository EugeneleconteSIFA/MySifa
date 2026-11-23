/* MySifa — Rentabilité › Tableau de bord.
 *
 * Chaque COMMANDE terminée et rattachée à un devis validé est placée selon
 * ses deux indicateurs : marge brute (MB %) et coût horaire (MB par heure
 * machine). Une commande produite en plusieurs dossiers (une ligne par
 * article, un changement de cliché entre chaque) est jugée d'un bloc : sinon
 * le calage, porté par le premier dossier, le fausse et flatte les autres. Les barres d'erreur montrent la FOURCHETTE réelle, le rond creux
 * relié par un pointillé montre où le devis plaçait le dossier. Le quart en
 * haut à droite, au-dessus des deux seuils, est celui des dossiers réussis.
 *
 * Calcul serveur : `GET /api/rentabilite/tableau-de-bord` (service
 * `app/services/rentabilite_reel.py`, une fiche par dossier). Ce fichier ne
 * fait que dessiner. Le clic sur un dossier ouvre sa fenêtre du Pilotage,
 * où se lit la fiche détaillée.
 *
 * Données : textContent partout, jamais innerHTML.
 * API : MySifaRentTableau.monter(conteneur, {periode, machine, grain, courbe, progression, surFiltre, ouvrir})
 */
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var PERIODES = [['ouvres7', '7 jours ouvrés'], ['last30', '30 jours'], ['last90', '90 jours'], ['thisYear', 'Cette année'], ['all', 'Tout']];
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
  function nbDossiers(l) {
    return l.nb_dossiers > 1 ? l.nb_dossiers + ' dossiers' : '';
  }
  // Un écran vide dit pourquoi : rien de produit, ou rien encore de jugeable.
  function vide(d) {
    var c = d.comptes || {};
    var n = (d.dossiers || []).length;
    if (!n) return 'Aucune commande terminée avec un devis validé sur cette période.';
    var morceaux = [];
    if (c.attente) morceaux.push(nb(c.attente) + ' en attente de facture, de déstockage ou de fin de production');
    if (c.a_verifier) morceaux.push(nb(c.a_verifier) + ' à vérifier');
    return nb(n) + ' commande' + (n > 1 ? 's' : '') + ' sur la période, aucune complète'
      + (morceaux.length ? ' : ' + morceaux.join(', ') + '.' : '.');
  }
  function cle(o) { return (o.periode || 'ouvres7') + '|' + (o.machine || ''); }
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
      c.setAttribute('aria-pressed', String((o.periode || 'ouvres7') === p[0]));
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

  // ── Les deux chiffres de la période (bloc capturable) ──────────────
  /* Marge brute PONDÉRÉE et coût horaire MÉDIAN des dossiers complets, chacun
     coloré selon son seuil, avec l'écart au devisé. Le détail (seuil, devisé,
     nombre de dossiers) est en infobulle. Les comptes de verdicts restent
     portés par le bloc pour les widgets d'accueil déjà posés. */
  function compteurs(d) {
    var c = d.comptes || {};
    var S = d.seuils || {};
    var row = el('div', 'rt-kpis rt-kpis-forts');
    row.setAttribute('data-bloc', 'prod.rentabilite.verdicts');
    row.setAttribute('data-bloc-valeur-marge', d.mb_pct_pondere == null ? '' : String(Math.round(d.mb_pct_pondere * 10) / 10));
    row.setAttribute('data-bloc-valeur-cout-horaire', d.cout_horaire_median == null ? '' : String(Math.round(d.cout_horaire_median)));
    row.setAttribute('data-bloc-valeur-reussis', String(c.reussi || 0));
    row.setAttribute('data-bloc-valeur-limite', String(c.limite || 0));
    row.setAttribute('data-bloc-valeur-sous-seuil', String(c.sous_seuil || 0));
    row.setAttribute('data-bloc-valeur-attente', String(c.attente || 0));
    function tuile(k, v, unite, seuil, devis, dec, uniteEcart, note) {
      var etat = v == null ? '' : (v >= seuil ? 'rt-ok' : 'rt-bad');
      var t = el('div', 'rt-kpi rt-kpi-fort ' + etat);
      t.appendChild(el('span', 'rt-kpi-k', k));
      var ligne = el('div', 'rt-kpi-ligne');
      var val = el('span', 'rt-kpi-v', v == null ? '—' : nb(v, dec));
      if (v != null) val.appendChild(el('small', 'rt-kpi-u', unite));
      ligne.appendChild(val);
      if (v != null && devis != null) {
        var e = v - devis;
        ligne.appendChild(el('span', 'rt-kpi-ecart ' + (e >= 0 ? 'rt-ecart-ok' : 'rt-ecart-bad'),
          signe(e, dec) + ' ' + uniteEcart + ' vs devis'));
      }
      t.appendChild(ligne);
      bulle(t, {titre: k, note: note,
        lignes: [['Seuil', nb(seuil) + ' ' + unite], ['Devisé', devis != null ? nb(devis, dec) + ' ' + unite : ''],
                 ['Commandes complètes', nb(c.complets)]]});
      row.appendChild(t);
    }
    tuile('Marge brute', d.mb_pct_pondere, '%', S.mb_pct, d.devis_mb_pct_pondere, 1, 'pt',
      'Somme des marges ÷ somme des prix de vente des commandes complètes : une grosse commande pèse plus.');
    tuile('Coût horaire médian', d.cout_horaire_median, '€/h', S.cout_horaire, d.devis_cout_horaire_median, 0, '€/h',
      'Marge brute par heure machine de la commande complète du milieu.');
    return row;
  }

  // ── Nuage MB % × coût horaire ──────────────────────────────────────
  function nuage(d, o) {
    var carte = el('div', 'rt-carte');
    var tete = el('div', 'rt-carte-tete');
    tete.appendChild(el('b', '', 'Marge brute et coût horaire par commande'));
    var leg = el('div', 'rt-legende');
    [['ok', 'Réussi'], ['warn', 'À la limite'], ['bad', 'Sous un seuil'], ['devis', 'Devis']]
      .forEach(function (x) {
        var s = el('span', 'rt-leg');
        s.appendChild(el('i', 'rt-pt rt-pt-' + x[0]));
        s.appendChild(document.createTextNode(x[1]));
        leg.appendChild(s);
      });
    tete.appendChild(leg);
    carte.appendChild(tete);

    // Seuls les dossiers COMPLETS : produits, déstockés, facturés, sans
    // avertissement. Un provisoire ou un résultat douteux brouillerait le
    // nuage ; ils restent dans la liste, avec ce qui leur manque.
    var pts = (d.dossiers || []).filter(function (l) { return l.mb_pct && l.cout_horaire && l.etat === 'complet'; });
    var S = d.seuils || {mb_pct: 40, cout_horaire: 325};
    if (!pts.length) {
      carte.appendChild(el('div', 'rt-vide', vide(d)));
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
      'aria-label': pts.length + ' commandes placées selon leur marge brute et leur coût horaire'});
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
      var g = svg('g', {'class': 'rt-point', tabindex: '0',
        role: 'button', 'aria-label': (l.client || '') + ' ' + (l.reference || '')});
      var vd = VERDICT[v];
      bulle(g, {titre: l.client || '(client non renseigné)',
        sous: [l.reference, nbDossiers(l), l.machine].filter(Boolean).join(' · '),
        etat: vd ? vd.lib : '',
        ton: {ok: 'vert', warn: 'orange', bad: 'rouge'}[cls] || 'inconnu',
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
        {titre: titre, note: 'Moyenne par commande complète des cascades de ses dossiers.'}));
      if (!liste || !liste.length) {
        carte.appendChild(el('div', 'rt-vide', 'Aucune commande complète.'));
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
    var dates_vues = {};
    dates.forEach(function (x) { dates_vues[x] = true; });
    for (var garde = 0; garde < 2000; garde++) {
      // Jour par jour, un samedi ou un dimanche sans dossier n'est pas un
      // creux de production : il ne prend pas de colonne.
      var we = grain === 'jour' && [0, 6].indexOf(jourUTC(c).getUTCDay()) >= 0 && !dates_vues[c];
      if (!we) cles.push(c);
      if (c === fin) break;
      c = suivante(c, grain);
    }
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
    var grain = o.grain || 'jour', courbe = o.courbe || 'marge';
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
      carte.appendChild(el('div', 'rt-vide', 'Aucune commande datée sur cette période.'));
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
      'aria-label': 'Commandes par verdict et ' + (courbe === 'horaire' ? 'coût horaire' : 'marge brute')
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
        sous: tot ? nb(tot) + ' commande' + (tot > 1 ? 's' : '') + ' complète' + (tot > 1 ? 's' : '') : 'Aucune commande complète',
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
    ['Commande', 'Marge brute', 'Coût horaire', 'Verdict'].forEach(function (c) { tete.appendChild(el('span', '', c)); });
    carte.appendChild(tete);
    if (!lignes.length) {
      carte.appendChild(el('div', 'rt-vide', 'Aucune commande terminée avec un devis validé sur cette période.'));
      return carte;
    }
    var ehMax = Math.max.apply(null, lignes.map(function (l) {
      return Math.max((l.cout_horaire || {}).haut || 0, l.devis_cout_horaire || 0);
    }).concat([S.cout_horaire * 1.5]));
    function tag(l) {
      if (l.etat === 'complet') {
        var v = VERDICT[(l.verdict || {}).global];
        return el('span', 'rt-tag rt-tag-' + (v ? v.cls : 'neutre'), v ? v.lib : 'Non calculable');
      }
      if (l.etat === 'a_verifier') {
        return bulle(el('span', 'rt-tag rt-tag-bad', 'À vérifier'),
          (l.hors_norme && l.hors_norme.length)
            ? {titre: 'Résultat hors norme', note: l.hors_norme.join(', ')
              + ' : facture ou matière probablement rattachée au mauvais dossier.'}
            : {titre: 'Résultat incertain', note: (l.raisons || []).join(' ')});
      }
      if (l.etat === 'provisoire') {
        return bulle(el('span', 'rt-tag rt-tag-neutre', 'Provisoire'), {titre: 'Provisoire', note: l.manque && l.manque.length
          ? 'Il manque : ' + l.manque.join(', ') : 'Marché partiellement facturé'});
      }
      return el('span', 'rt-tag rt-tag-neutre', 'Non mesurable');
    }
    function ligne(l, enfant) {
      var r = el('button', 'rt-ligne' + (enfant ? ' rt-ligne-enfant' : ''));
      r.type = 'button';
      r.addEventListener('click', function () { o.ouvrir(l.planning_entry_id); });
      var qui = el('span', 'rt-qui');
      qui.appendChild(el('b', '', enfant ? (l.reference || '') : (l.client || '(client non renseigné)')));
      qui.appendChild(el('span', '', enfant ? [l.machine, l.date ? l.date.slice(8, 10) + '/' + l.date.slice(5, 7) : '']
        .filter(Boolean).join(' · ') : [l.reference, nbDossiers(l), l.machine].filter(Boolean).join(' · ')));
      if (!enfant && l.modifies && l.modifies.length) {
        bulle(qui.appendChild(el('span', 'rt-modifie', 'modifié')),
          {titre: 'Changé par rapport au devis', note: l.modifies.join(', ')});
      }
      r.appendChild(qui);
      r.appendChild(mini(l.mb_pct, enfant ? null : l.devis_mb_pct, S.mb_pct, Math.min(0, S.mb_pct - 30), S.mb_pct + 30, '%', 1));
      r.appendChild(mini(l.cout_horaire, enfant ? null : l.devis_cout_horaire, S.cout_horaire, 0, ehMax, '€/h', 0));
      r.appendChild(enfant ? el('span', 'rt-enfant-note', '') : tag(l));
      return r;
    }
    lignes.forEach(function (l) {
      carte.appendChild(ligne(l, false));
      // Les dossiers d'une commande, dessous : on y voit lequel a porté le calage.
      (l.membres || []).forEach(function (m) { carte.appendChild(ligne(m, true)); });
    });
    return carte;
  }

  // ── Progression au fil des m² produits ─────────────────────────────
  /* Axe horizontal : les m² cumulés depuis le début de l'historique, pas le
     calendrier ; ils avancent avec le travail fait. Chaque point est une
     moyenne pondérée glissante (calcul serveur), le tireté est la tendance. */
  var SERIES = [['combine', 'Combiné'], ['marge', 'Marge brute'], ['horaire', 'Coût horaire']];
  function m2(v) {
    v = Number(v) || 0;
    if (v >= 1e6) return nb(v / 1e6, 1) + ' M m²';
    if (v >= 1e4) return nb(Math.round(v / 1000)) + ' k m²';
    return nb(v) + ' m²';
  }
  function progressionCarte(d, o) {
    var choix = o.progression || 'combine';
    var P = d.progression || {};
    var S = d.seuils || {mb_pct: 40, cout_horaire: 325};
    var cleV = {combine: 'combine', marge: 'mb_pct', horaire: 'cout_horaire'}[choix];
    var seuil = {combine: 100, marge: S.mb_pct, horaire: S.cout_horaire}[choix];
    var unite = {combine: '', marge: ' %', horaire: ' €/h'}[choix];
    var dec = choix === 'marge' ? 1 : 0;
    var carte = el('div', 'rt-carte rt-temps rt-progression');
    var tete = el('div', 'rt-carte-tete');
    tete.appendChild(bulle(el('b', '', 'Progression'), {titre: 'Progression au fil des m² produits',
      note: 'Toutes les commandes complètes depuis le début, quelle que soit la période choisie. '
        + 'Moyenne pondérée sur le dernier sixième des m². Indice combiné : 100 = marge et coût horaire pile sur leurs seuils.'}));
    var grp = el('div', 'rt-chips');
    grp.setAttribute('role', 'group');
    grp.setAttribute('aria-label', 'Indicateur');
    SERIES.forEach(function (x) {
      var c = el('button', 'rt-chip rt-chip-petit', x[1]);
      c.type = 'button';
      c.setAttribute('aria-pressed', String(choix === x[0]));
      c.addEventListener('click', function () { o.surFiltre({progression: x[0]}); });
      grp.appendChild(c);
    });
    tete.appendChild(grp);
    carte.appendChild(tete);
    var pts = (P.points || []).filter(function (p) { return p[cleV] != null; });
    if (pts.length < 2) {
      carte.appendChild(el('div', 'rt-vide', 'Pas encore assez de commandes complètes pour tracer une progression.'));
      return carte;
    }
    var tend = (P.tendance || {})[cleV];
    if (tend) {
      var delta = tend.fin - tend.debut;
      var ecart = el('div', 'rt-prog-tendance ' + (delta >= 0 ? 'rt-ecart-ok' : 'rt-ecart-bad'),
        (delta >= 0 ? 'En progrès : ' : 'En recul : ') + signe(delta, dec) + ({marge: ' pt', horaire: ' €/h', combine: ' points d\'indice'}[choix])
        + ' sur ' + m2(tend.m2_fin - tend.m2_debut));
      bulle(ecart, {titre: 'Tendance', lignes: [['Au début', nb(tend.debut, dec) + unite], ['Aujourd\'hui', nb(tend.fin, dec) + unite],
        ['Commandes', nb(P.commandes)], ['Surface', m2(P.m2_total)]]});
      carte.appendChild(ecart);
    }
    var W = 1200, L = 56, R = 1186, T = 12, B = 250, H = 280;
    var xs = pts.map(function (p) { return p.m2; });
    var ys = pts.map(function (p) { return p[cleV]; }).concat([seuil]);
    var x0 = 0, x1 = Math.max.apply(null, xs) || 1;
    var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
    var pasY = pasNet(hi - lo || 1, 5);
    lo = Math.floor(lo / pasY) * pasY - pasY; hi = Math.ceil(hi / pasY) * pasY + pasY;
    if (choix !== 'marge') lo = Math.max(0, lo);
    var X = function (v) { return L + (v - x0) / (x1 - x0) * (R - L); };
    var Y = function (v) { return B - (v - lo) / (hi - lo) * (B - T); };
    var s = svg('svg', {viewBox: '0 0 ' + W + ' ' + H, 'class': 'rt-temps-svg', role: 'img',
      'aria-label': 'Progression de l\'indicateur au fil des m² produits'});
    for (var vy = lo; vy <= hi + 1e-9; vy += pasY) {
      s.appendChild(svg('line', {x1: L, x2: R, y1: Y(vy), y2: Y(vy), 'class': 'rt-grille'}));
      var ty = svg('text', {x: L - 8, y: Y(vy) + 4, 'text-anchor': 'end', 'class': 'rt-axe'});
      ty.textContent = nb(vy) + (choix === 'marge' ? ' %' : '');
      s.appendChild(ty);
    }
    var pasX = pasNet(x1 - x0, 8);
    for (var vx = pasX; vx <= x1 + 1e-9; vx += pasX) {
      var tx = svg('text', {x: X(vx), y: H - 6, 'text-anchor': 'middle', 'class': 'rt-axe'});
      tx.textContent = m2(vx);
      s.appendChild(tx);
    }
    s.appendChild(svg('line', {x1: L, x2: R, y1: Y(seuil), y2: Y(seuil), 'class': 'rt-seuil'}));
    var ls = svg('text', {x: R, y: Y(seuil) - 5, 'text-anchor': 'end', 'class': 'rt-seuil-lib'});
    ls.textContent = choix === 'combine' ? 'Seuils' : nb(seuil) + unite;
    s.appendChild(ls);
    if (tend) s.appendChild(svg('line', {x1: X(tend.m2_debut), y1: Y(tend.debut), x2: X(tend.m2_fin), y2: Y(tend.fin),
      'class': 'rt-tendance'}));
    for (var i = 1; i < pts.length; i++) {
      s.appendChild(svg('line', {x1: X(pts[i - 1].m2), y1: Y(pts[i - 1][cleV]), x2: X(pts[i].m2), y2: Y(pts[i][cleV]),
        'class': 'rt-courbe'}));
    }
    pts.forEach(function (p, i) {
      var v = p[cleV];
      s.appendChild(svg('circle', {cx: X(p.m2), cy: Y(v), r: pts.length > 80 ? 2.5 : 3.5,
        'class': 'rt-pt-svg rt-f-' + (v >= seuil ? 'ok' : 'bad')}));
      // Zone de survol : de la moitié du segment précédent à la moitié du suivant.
      var g = i ? (X(pts[i - 1].m2) + X(p.m2)) / 2 : L;
      var dr = i < pts.length - 1 ? (X(p.m2) + X(pts[i + 1].m2)) / 2 : R;
      var zone = svg('rect', {x: g, y: T, width: Math.max(1, dr - g), height: B - T, 'class': 'rt-temps-zone'});
      bulle(zone, {titre: m2(p.m2) + ' produits',
        sous: [p.client, p.commande, p.date ? p.date.slice(8, 10) + '/' + p.date.slice(5, 7) + '/' + p.date.slice(0, 4) : '']
          .filter(Boolean).join(' · '),
        lignes: [['Marge brute', p.mb_pct != null ? nb(p.mb_pct, 1) + ' %' : ''],
                 ['Coût horaire', p.cout_horaire != null ? nb(p.cout_horaire) + ' €/h' : ''],
                 ['Indice combiné', p.combine != null ? nb(p.combine) : ''],
                 ['Moyenne sur', nb(p.n) + ' commande' + (p.n > 1 ? 's' : '')]]});
      s.appendChild(zone);
    });
    carte.appendChild(s);
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
    conteneur.appendChild(progressionCarte(d, o));
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
      var url = '/api/rentabilite/tableau-de-bord?periode=' + encodeURIComponent(o.periode || 'ouvres7')
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
