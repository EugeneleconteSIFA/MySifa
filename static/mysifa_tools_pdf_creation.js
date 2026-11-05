/*
 * MyTools — éditeur PDF : créer un document de zéro.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   - « Nouveau document » : format, nombre de pages, en-tête de l'entreprise
 *     (nom passé par la page dans ctx.org, jamais écrit ici) ;
 *   - annotation « bloc » : texte multiligne avec retour à la ligne automatique ;
 *   - annotation « tableau » : lignes × colonnes, cellules éditables, largeur
 *     des colonnes ajustable, bordures, en-tête en gras.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  var MM = 72 / 25.4;
  var FORMATS = [
    ['a4', 'A4 portrait', 595.28, 841.89], ['a4p', 'A4 paysage', 841.89, 595.28], ['a3', 'A3 portrait', 841.89, 1190.55],
    ['a5', 'A5 portrait', 419.53, 595.28], ['letter', 'Letter', 612, 792], ['perso', 'Personnalisé (mm)', 0, 0]
  ];

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // Découpe un texte en lignes qui tiennent dans `largeur` ; mesure(str) -> largeur.
  function couperLignes(texte, largeur, mesure) {
    var out = [];
    String(texte == null ? '' : texte).split('\n').forEach(function (para) {
      var mots = para.split(/ +/), ligne = '';
      if (!para.trim()) { out.push(''); return; }
      mots.forEach(function (mot) {
        if (!mot) return;
        var essai = ligne ? ligne + ' ' + mot : mot;
        if (mesure(essai) <= largeur || !ligne && mesure(mot) <= largeur) { ligne = essai; return; }
        if (ligne) out.push(ligne);
        // Mot plus long que la largeur : coupé caractère par caractère.
        ligne = '';
        var morceau = '';
        for (var ch of mot) {
          if (morceau && mesure(morceau + ch) > largeur) { out.push(morceau); morceau = ch; }
          else morceau += ch;
        }
        ligne = morceau;
      });
      out.push(ligne);
    });
    return out;
  }
  // Géométrie d'un tableau : bords de colonnes et de lignes, lignes de texte par cellule.
  function geometrieTableau(a, mesure) {
    var xs = [a.x], acc = a.x, total = a.cols.reduce(function (s, f) { return s + f; }, 0) || 1;
    a.cols.forEach(function (f) { acc += a.w * f / total; xs.push(acc); });
    var pad = a.pad != null ? a.pad : 4, lh = a.taille * 1.25, ys = [a.y], lignes = [], y = a.y;
    a.cells.forEach(function (row, r) {
      var gras = a.entete && r === 0, max = 1, lr = [];
      row.forEach(function (txt, c) {
        var lw = Math.max(4, xs[c + 1] - xs[c] - 2 * pad);
        var l = couperLignes(txt, lw, function (s) { return mesure(s, a.taille, gras); });
        lr.push(l); max = Math.max(max, l.length);
      });
      lignes.push(lr);
      y += max * lh + 2 * pad; ys.push(y);
    });
    return { xs: xs, ys: ys, lignes: lignes, pad: pad, lh: lh };
  }
  // Redimensionne un tableau de lignes de cellules, contenu conservé.
  function retaillerCellules(cells, nl, nc) {
    var out = [];
    for (var r = 0; r < nl; r++) {
      var row = [];
      for (var c = 0; c < nc; c++) row.push(cells[r] && cells[r][c] != null ? cells[r][c] : '');
      out.push(row);
    }
    return out;
  }
  function retaillerColonnes(cols, nc) {
    var out = cols.slice(0, nc), moy = 1 / nc;
    while (out.length < nc) out.push(moy);
    var t = out.reduce(function (s, f) { return s + f; }, 0);
    return out.map(function (f) { return f / t; });
  }
  // Déplace le bord entre les colonnes i-1 et i à l'abscisse x (bornée).
  function deplacerBord(a, i, x, min) {
    var tot = a.cols.reduce(function (s, f) { return s + f; }, 0) || 1;
    var w = a.cols.map(function (f) { return a.w * f / tot; });
    var gauche = a.x + w.slice(0, i - 1).reduce(function (s, v) { return s + v; }, 0);
    var paire = w[i - 1] + w[i];
    var nw = Math.max(min, Math.min(paire - min, x - gauche));
    w[i - 1] = nw; w[i] = paire - nw;
    return w.map(function (v) { return v / a.w; });
  }
  function dimensionsFormat(id, lmm, hmm) {
    for (var i = 0; i < FORMATS.length; i++) {
      if (FORMATS[i][0] !== id) continue;
      if (id !== 'perso') return [FORMATS[i][2], FORMATS[i][3]];
      var l = parseFloat(lmm), h = parseFloat(hmm);
      if (!(l >= 20 && l <= 2000 && h >= 20 && h <= 2000)) throw new Error('Format invalide — largeur et hauteur entre 20 et 2000 mm.');
      return [l * MM, h * MM];
    }
    throw new Error('Format inconnu.');
  }

  M._interne = M._interne || {};
  M._interne.creation = { couperLignes: couperLignes, geometrieTableau: geometrieTableau, retaillerCellules: retaillerCellules,
    retaillerColonnes: retaillerColonnes, deplacerBord: deplacerBord, dimensionsFormat: dimensionsFormat };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    var _cm = null;
    function mesure(txt, taille, gras) {
      if (!_cm) _cm = document.createElement('canvas').getContext('2d');
      _cm.font = (gras ? 'bold ' : '') + taille + 'px ' + api.POLICE;
      return _cm.measureText(txt).width;
    }

    api.IC.nouveau = '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h4.5"/><path d="M13.5 3.5V9H19v2.5"/><path d="M17.5 14.5v6M14.5 17.5h6"/>';
    api.IC.bloc = '<path d="M4.5 6h15M4.5 10h15M4.5 14h15M4.5 18h9"/>';
    api.IC.tableau = '<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><path d="M3.5 9.5h17M3.5 14h17M9.5 5v14M15 5v14"/>';
    api.LIBELLES.bloc = 'Bloc de texte';
    api.LIBELLES.tableau = 'Tableau';
    api.AIDE_OUTIL.bloc = 'Cliquer-glisser pour fixer la largeur du bloc ; le texte revient à la ligne tout seul.';
    api.AIDE_OUTIL.tableau = 'Cliquer-glisser pour fixer la largeur du tableau.';
    EXT.boutons.push({ groupe: 'fichier', html: api.bouton('nouveau', 'nouveau', 'Nouveau document') });
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('bloc', 'bloc', 'Bloc de texte') + api.outilBtn('tableau', 'tableau', 'Tableau') });
    EXT.boutons.push({ groupe: 'vide', html: '<button type="button" class="tpdf-b" data-act="nouveau" data-bulle="Nouveau">' + api.ico('nouveau', 16) + '<span>Nouveau document</span></button>' });

    function palette(sec, a, cle, titre) {
      var pal = document.createElement('div'); pal.className = 'tpdf-palette';
      var actuel = a ? a[cle] : S().style.couleur;
      api.COULEURS.forEach(function (c) {
        var b = document.createElement('button'); b.type = 'button';
        b.className = 'tpdf-pastille' + (actuel && actuel.toLowerCase() === c ? ' tpdf-actif' : '');
        b.style.background = c; b.setAttribute('data-bulle', api.NOMS_COULEURS[c] || 'Couleur'); b.setAttribute('aria-label', 'Couleur ' + (api.NOMS_COULEURS[c] || c).toLowerCase());
        b.addEventListener('click', function () {
          api.majProp(cle, c, a); api.validerProp();
          pal.querySelectorAll('.tpdf-pastille').forEach(function (x) { x.classList.toggle('tpdf-actif', x === b); });
        });
        pal.appendChild(b);
      });
      sec.appendChild(api.champ(titre || 'Couleur', pal));
    }
    function nombre(sec, a, cle, titre, min, max, pas) {
      var n = document.createElement('input'); n.type = 'number'; n.min = min; n.max = max; n.step = pas || 1; n.className = 'tpdf-champ';
      n.value = a ? a[cle] : (S().style[cle] || min);
      n.addEventListener('input', function () { var v = parseFloat(n.value); if (v >= min && v <= max) api.majProp(cle, v, a); });
      n.addEventListener('change', api.validerProp);
      sec.appendChild(api.champ(titre, n));
      return n;
    }
    function coche(sec, a, cle, titre) {
      var l = document.createElement('label'); l.className = 'tpdf-case';
      var i = document.createElement('input'); i.type = 'checkbox'; i.checked = !!(a ? a[cle] : S().style[cle]);
      i.addEventListener('change', function () { api.majProp(cle, i.checked, a); api.validerProp(); });
      l.appendChild(i); l.appendChild(document.createTextNode(' ' + titre));
      sec.appendChild(l);
    }
    // Ne déborde pas à droite de la page.
    function borner(a) {
      var d = api.dims(api.pageCourante()), max = d.w - a.x - 10;
      if (a.w > max) a.w = Math.max(40, max);
      if (a.x + a.w > d.w) a.x = Math.max(0, d.w - a.w - 10);
    }
    // Largeur seule : la hauteur d'un bloc ou d'un tableau découle de son contenu.
    function redimLargeur(a, o, poignee, pt) {
      var gauche = poignee.indexOf('w') >= 0, fx = gauche ? o.x + o.w : o.x;
      var w = Math.max(40, Math.abs(pt.x - fx));
      a.x = gauche ? fx - w : fx; a.w = w;
    }

    /* ── Bloc de texte ────────────────────────────────────────────────── */
    function lignesBloc(a) { return couperLignes(a.texte, Math.max(10, a.w), function (s) { return mesure(s, a.taille, a.gras); }); }
    EXT.outils.bloc = {
      down: function (pt) {
        var st = S().style;
        return { t: 'bloc', x: pt.x, y: pt.y, w: 0, h: 0, texte: 'Texte du bloc', taille: st.tailleBloc || 11,
          couleur: st.couleur === api.COULEURS[0] ? '#1a1a1a' : st.couleur, align: 'gauche', gras: false };
      }
    };
    EXT.types.bloc = {
      tailleDefaut: function () { return [240, 0]; },
      apresCreation: function (a) { if (a.w < 40) a.w = 240; borner(a); api.choisirOutil('select', true); api.focaliserTexte(); },
      boite: function (a) { var n = Math.max(1, lignesBloc(a).length); return { x: a.x, y: a.y, w: a.w, h: n * a.taille * 1.3 }; },
      redim: redimLargeur,
      dessiner: function (a, g) {
        var b = this.boite(a);
        api.sv('rect', { x: b.x, y: b.y, width: b.w, height: b.h, fill: 'transparent' }, g);
        var anc = { gauche: 'start', centre: 'middle', droite: 'end' }[a.align] || 'start';
        var x = a.align === 'centre' ? a.x + a.w / 2 : a.align === 'droite' ? a.x + a.w : a.x;
        var t = api.sv('text', { 'font-size': a.taille, 'font-family': api.POLICE, 'font-weight': a.gras ? 'bold' : 'normal', fill: a.couleur, 'text-anchor': anc }, g);
        lignesBloc(a).forEach(function (l, i) {
          var ts = api.sv('tspan', { x: x, y: a.y + a.taille * api.ASC + i * a.taille * 1.3 }, t);
          ts.textContent = l || ' ';
        });
      },
      dblclic: function () { api.focaliserTexte(); },
      props: function (sec, a) {
        if (a) {
          var ta = document.createElement('textarea'); ta.className = 'tpdf-champ'; ta.rows = 5; ta.value = a.texte; ta.setAttribute('data-prop', 'texte');
          ta.addEventListener('input', function () { api.majProp('texte', ta.value, a); });
          ta.addEventListener('change', api.validerProp);
          sec.appendChild(api.champ('Texte', ta));
        }
        nombre(sec, a, 'taille', 'Taille (pt)', 5, 96);
        var seg = document.createElement('div'); seg.className = 'tpdf-seg';
        [['gauche', 'À gauche'], ['centre', 'Centré'], ['droite', 'À droite']].forEach(function (x) {
          var b = document.createElement('button'); b.type = 'button'; b.className = 'tpdf-btn' + ((a ? a.align : 'gauche') === x[0] ? ' tpdf-actif' : '');
          b.textContent = x[1];
          b.addEventListener('click', function () {
            api.majProp('align', x[0], a); api.validerProp();
            seg.querySelectorAll('button').forEach(function (y) { y.classList.toggle('tpdf-actif', y === b); });
          });
          seg.appendChild(b);
        });
        sec.appendChild(api.champ('Alignement', seg));
        coche(sec, a, 'gras', 'Gras');
        palette(sec, a, 'couleur');
      },
      exporter: async function (a, c) {
        var font = await c.pol.police(a.texte, { gras: a.gras }), col = api.hexRgb(a.couleur);
        lignesBloc(a).forEach(function (l, i) {
          if (!l) return;
          var txt = api.nettoyerTexte(font, l), w = font.widthOfTextAtSize(txt, a.taille);
          var u = a.align === 'centre' ? a.x + (a.w - w) / 2 : a.align === 'droite' ? a.x + a.w - w : a.x;
          var q = c.P(u, a.y + a.taille * api.ASC + i * a.taille * 1.3);
          c.pg.drawText(txt, { x: q[0], y: q[1], size: a.taille, font: font, color: c.L.rgb(col[0], col[1], col[2]), rotate: c.rot });
        });
      }
    };

    /* ── Tableau ──────────────────────────────────────────────────────── */
    function geo(a) { return geometrieTableau(a, mesure); }
    EXT.outils.tableau = {
      down: function (pt) {
        return { t: 'tableau', x: pt.x, y: pt.y, w: 0, h: 0, cols: [1 / 3, 1 / 3, 1 / 3],
          cells: [['Colonne 1', 'Colonne 2', 'Colonne 3'], ['', '', ''], ['', '', '']],
          entete: true, taille: 10, couleur: '#1a1a1a', bordure: '#1a1a1a', ep: 0.75 };
      }
    };
    EXT.types.tableau = {
      tailleDefaut: function () { return [320, 0]; },
      apresCreation: function (a) { if (a.w < 60) a.w = 320; borner(a); api.choisirOutil('select', true); },
      boite: function (a) { var g = geo(a); return { x: a.x, y: a.y, w: a.w, h: g.ys[g.ys.length - 1] - a.y }; },
      dessiner: function (a, g) {
        var G = geo(a), y1 = G.ys[G.ys.length - 1], x1 = G.xs[G.xs.length - 1];
        api.sv('rect', { x: a.x, y: a.y, width: a.w, height: y1 - a.y, fill: 'transparent', stroke: a.bordure, 'stroke-width': a.ep }, g);
        if (a.entete) api.sv('rect', { x: a.x, y: a.y, width: a.w, height: G.ys[1] - a.y, fill: a.bordure, 'fill-opacity': 0.08 }, g);
        G.xs.slice(1, -1).forEach(function (x) { api.sv('line', { x1: x, y1: a.y, x2: x, y2: y1, stroke: a.bordure, 'stroke-width': a.ep }, g); });
        G.ys.slice(1, -1).forEach(function (y) { api.sv('line', { x1: a.x, y1: y, x2: x1, y2: y, stroke: a.bordure, 'stroke-width': a.ep }, g); });
        G.lignes.forEach(function (lr, r) {
          lr.forEach(function (l, c) {
            if (!l.length || (l.length === 1 && !l[0])) return;
            var t = api.sv('text', { 'font-size': a.taille, 'font-family': api.POLICE, 'font-weight': a.entete && r === 0 ? 'bold' : 'normal', fill: a.couleur }, g);
            l.forEach(function (s, i) {
              var ts = api.sv('tspan', { x: G.xs[c] + G.pad, y: G.ys[r] + G.pad + a.taille * api.ASC + i * G.lh }, t);
              ts.textContent = s || ' ';
            });
          });
        });
      },
      decorations: function (a, cadre, z) {
        var G = geo(a), mid = (a.y + G.ys[G.ys.length - 1]) / 2, t = 8 / z;
        G.xs.slice(1, -1).forEach(function (x, i) {
          api.sv('rect', { x: x - t / 3, y: mid - t, width: t * 2 / 3, height: t * 2, rx: t / 4, 'class': 'tpdf-poignee tpdf-poignee-col', 'data-poignee': 'col:' + (i + 1), 'stroke-width': 1.5 / z }, cadre);
        });
      },
      redim: function (a, o, poignee, pt) {
        if (poignee.indexOf('col:') === 0) { a.cols = deplacerBord(o, parseInt(poignee.slice(4), 10), pt.x, 12); return; }
        redimLargeur(a, o, poignee, pt);
      },
      dblclic: function (a, pt) {
        var G = geo(a), c = -1, r = -1;
        for (var i = 0; i < G.xs.length - 1; i++) if (pt.x >= G.xs[i] && pt.x <= G.xs[i + 1]) c = i;
        for (var j = 0; j < G.ys.length - 1; j++) if (pt.y >= G.ys[j] && pt.y <= G.ys[j + 1]) r = j;
        if (c >= 0 && r >= 0) editerCellule(a, r, c);
      },
      props: function (sec, a) {
        if (!a) return;
        var aide = document.createElement('p'); aide.className = 'tpdf-aide';
        aide.textContent = 'Double-cliquer une cellule pour la modifier. Glisser les poignées entre colonnes pour les élargir.';
        sec.appendChild(aide);
        var ligne = document.createElement('div'); ligne.className = 'tpdf-ligne tpdf-ligne-esp';
        var nl = document.createElement('input'); nl.type = 'number'; nl.min = 1; nl.max = 60; nl.className = 'tpdf-champ'; nl.value = a.cells.length;
        var nc = document.createElement('input'); nc.type = 'number'; nc.min = 1; nc.max = 12; nc.className = 'tpdf-champ'; nc.value = a.cols.length;
        function appliquer() {
          var l = parseInt(nl.value, 10), c = parseInt(nc.value, 10);
          if (!(l >= 1 && l <= 60 && c >= 1 && c <= 12)) { api.toast('Tableau invalide — 1 à 60 lignes, 1 à 12 colonnes.', 'danger'); return; }
          var avant = api.snapshot();
          a.cells = retaillerCellules(a.cells, l, c);
          if (c !== a.cols.length) a.cols = retaillerColonnes(a.cols, c);
          api.pushHist(avant); api.dessinerCalque(); api.rendreBarre();
        }
        nl.addEventListener('change', appliquer); nc.addEventListener('change', appliquer);
        ligne.appendChild(api.champ('Lignes', nl)); ligne.appendChild(api.champ('Colonnes', nc));
        sec.appendChild(ligne);
        coche(sec, a, 'entete', 'Première ligne en-tête (gras)');
        nombre(sec, a, 'taille', 'Taille du texte (pt)', 5, 48);
        nombre(sec, a, 'ep', 'Épaisseur des bordures', 0, 4, 0.25);
        palette(sec, a, 'couleur', 'Couleur du texte');
        palette(sec, a, 'bordure', 'Couleur des bordures');
      },
      exporter: async function (a, c) {
        var G = geo(a), L = c.L, bc = api.hexRgb(a.bordure), tc = api.hexRgb(a.couleur);
        var bord = L.rgb(bc[0], bc[1], bc[2]), coul = L.rgb(tc[0], tc[1], tc[2]);
        var x1 = G.xs[G.xs.length - 1], y1 = G.ys[G.ys.length - 1];
        function trait(ax, ay, bx, by) {
          var p = c.P(ax, ay), q = c.P(bx, by);
          c.pg.drawLine({ start: { x: p[0], y: p[1] }, end: { x: q[0], y: q[1] }, thickness: a.ep, color: bord });
        }
        if (a.entete) {
          var h1 = c.P(a.x, a.y), h2 = c.P(x1, G.ys[1]);
          c.pg.drawRectangle({ x: Math.min(h1[0], h2[0]), y: Math.min(h1[1], h2[1]), width: Math.abs(h2[0] - h1[0]), height: Math.abs(h2[1] - h1[1]), color: bord, opacity: 0.08 });
        }
        if (a.ep > 0) {
          G.xs.forEach(function (x) { trait(x, a.y, x, y1); });
          G.ys.forEach(function (y) { trait(a.x, y, x1, y); });
        }
        var tout = a.cells.map(function (r) { return r.join(' '); }).join(' ');
        var fn = await c.pol.police(tout, {}), fg = await c.pol.police(tout, { gras: true });
        G.lignes.forEach(function (lr, r) {
          var f = a.entete && r === 0 ? fg : fn;
          lr.forEach(function (l, col) {
            l.forEach(function (s, i) {
              if (!s) return;
              var q = c.P(G.xs[col] + G.pad, G.ys[r] + G.pad + a.taille * api.ASC + i * G.lh);
              c.pg.drawText(api.nettoyerTexte(f, s), { x: q[0], y: q[1], size: a.taille, font: f, color: coul, rotate: c.rot });
            });
          });
        });
      }
    };

    function editerCellule(a, r, col) {
      var s = S(), p = api.pageCourante(), d = api.dims(p), z = s.zoomCourant || 1;
      if (d.R !== 0) { api.toast('Modifier les cellules sur la page à l\'endroit, ou dans un tableau non pivoté.', 'info'); }
      var G = geo(a);
      s.html.querySelectorAll('.tpdf-cell-edit').forEach(function (e) { e.remove(); });
      var ta = document.createElement('textarea');
      ta.className = 'tpdf-cell-edit'; ta.value = a.cells[r][col];
      ta.style.left = (G.xs[col] * z) + 'px'; ta.style.top = (G.ys[r] * z) + 'px';
      ta.style.width = ((G.xs[col + 1] - G.xs[col]) * z) + 'px';
      ta.style.minHeight = ((G.ys[r + 1] - G.ys[r]) * z) + 'px';
      ta.style.fontSize = (a.taille * z) + 'px';
      ta.style.fontWeight = a.entete && r === 0 ? '700' : '400';
      ta.style.padding = (G.pad * z) + 'px';
      ta.setAttribute('aria-label', 'Cellule ' + (r + 1) + ', ' + (col + 1));
      var fini = false;
      function finir(garder) {
        if (fini) return; fini = true;
        var v = ta.value; ta.remove();
        if (!garder || v === a.cells[r][col]) return;
        var avant = api.snapshot();
        a.cells[r][col] = v;
        api.pushHist(avant); api.dessinerCalque(); api.rendreBarre();
      }
      ta.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); finir(false); }
        else if (ev.key === 'Tab') {
          ev.preventDefault(); finir(true);
          var nc = col + (ev.shiftKey ? -1 : 1), nr = r;
          if (nc >= a.cols.length) { nc = 0; nr++; } else if (nc < 0) { nc = a.cols.length - 1; nr--; }
          if (nr >= 0 && nr < a.cells.length) editerCellule(a, nr, nc);
        } else if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); finir(true); }
      });
      ta.addEventListener('blur', function () { finir(true); });
      s.html.appendChild(ta);
      requestAnimationFrame(function () { ta.focus(); ta.select(); });
    }

    /* ── Nouveau document ─────────────────────────────────────────────── */
    EXT.actions.nouveau = { sansDoc: true, fn: modaleNouveau };
    function modaleNouveau() {
      var s = S(), org = String((s.ctx && s.ctx.org) || '').trim();
      var corps = document.createElement('div');
      var fmt = document.createElement('select'); fmt.className = 'tpdf-champ';
      FORMATS.forEach(function (f) { var o = document.createElement('option'); o.value = f[0]; o.textContent = f[1]; fmt.appendChild(o); });
      corps.appendChild(api.champ('Format', fmt));
      var perso = document.createElement('div'); perso.className = 'tpdf-ligne tpdf-ligne-esp'; perso.hidden = true;
      var lw = document.createElement('input'); lw.type = 'number'; lw.className = 'tpdf-champ'; lw.min = 20; lw.max = 2000; lw.value = 210;
      var lh = document.createElement('input'); lh.type = 'number'; lh.className = 'tpdf-champ'; lh.min = 20; lh.max = 2000; lh.value = 297;
      perso.appendChild(api.champ('Largeur (mm)', lw)); perso.appendChild(api.champ('Hauteur (mm)', lh));
      corps.appendChild(perso);
      fmt.addEventListener('change', function () { perso.hidden = fmt.value !== 'perso'; });
      var np = document.createElement('input'); np.type = 'number'; np.className = 'tpdf-champ'; np.min = 1; np.max = 200; np.value = 1;
      corps.appendChild(api.champ('Nombre de pages', np));
      var ent = null;
      if (org) {
        var l = document.createElement('label'); l.className = 'tpdf-case';
        ent = document.createElement('input'); ent.type = 'checkbox'; ent.checked = true;
        l.appendChild(ent); l.appendChild(document.createTextNode(' En-tête de l\'entreprise (« ' + org + ' »)'));
        corps.appendChild(l);
      }
      var rempl = null;
      if (s.pages.length) {
        var r1 = document.createElement('label'); r1.className = 'tpdf-case';
        rempl = document.createElement('input'); rempl.type = 'radio'; rempl.name = 'tpdf-nouv'; rempl.checked = true;
        r1.appendChild(rempl); r1.appendChild(document.createTextNode(' Remplacer le document ouvert (Ctrl+Z pour revenir)'));
        var r2 = document.createElement('label'); r2.className = 'tpdf-case';
        var aj = document.createElement('input'); aj.type = 'radio'; aj.name = 'tpdf-nouv';
        r2.appendChild(aj); r2.appendChild(document.createTextNode(' Ajouter les pages à la fin'));
        corps.appendChild(r1); corps.appendChild(r2);
      }
      api.ouvrirModale('Nouveau document', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Créer', plein: true, fn: creer }
      ]);
      requestAnimationFrame(function () { fmt.focus(); });
      async function creer() {
        var dimz, n = parseInt(np.value, 10);
        try { dimz = dimensionsFormat(fmt.value, lw.value, lh.value); } catch (e) { api.toast(e.message, 'danger'); return; }
        if (!(n >= 1 && n <= 200)) { api.toast('Nombre de pages invalide — entre 1 et 200.', 'danger'); np.focus(); return; }
        api.fermerModale();
        try {
          var L = await api.pdflib(), d = await L.PDFDocument.create();
          d.addPage(dimz);
          var src = await api.ajouterSource('Nouveau document', await d.save());
          var avant = api.snapshot(), pages = [];
          for (var i = 0; i < n; i++) {
            var p = api.nouvellePage(src.id, 0);
            if (ent && ent.checked) {
              p.annots.push({ id: api.nid('n'), t: 'bloc', x: 40, y: 34, w: dimz[0] - 80, texte: org, taille: 16, couleur: '#1a1a1a', align: 'gauche', gras: true });
              p.annots.push({ id: api.nid('n'), t: 'ligne', x1: 40, y1: 60, x2: dimz[0] - 40, y2: 60, couleur: '#1a1a1a', ep: 0.75 });
            }
            pages.push(p);
          }
          var remplacer = !rempl || rempl.checked;
          if (remplacer) { s.pages = pages; s.cur = 0; s.nom = 'nouveau-document'; }
          else { s.cur = s.pages.length; s.pages = s.pages.concat(pages); }
          s.sel = {}; s.sel[s.pages[s.cur].uid] = 1; s.ancre = s.pages[s.cur].uid; s.annSel = null;
          api.pushHist(avant);
          api.toutRendre(); api.notifier();
          api.toast(n > 1 ? n + ' pages créées.' : 'Page créée.', 'success');
        } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      }
    }
  });
})();
