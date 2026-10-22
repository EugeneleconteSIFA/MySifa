/*
 * MyTools — éditeur PDF : mesure à l'échelle (distance, périmètre, surface)
 * et pipette (RVB + CMJN).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Une mesure est une annotation : ses points sont en points PDF, l'échelle
 * (« 1 mm sur la page = N mm réels ») est rangée avec elle. Exportée comme le
 * reste (traits et étiquette dessinés dans la page).
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  var MM = 25.4 / 72;
  /* ── Fonctions pures (tests) ──────────────────────────────────────── */
  function longueur(pts, ferme) {
    var s = 0;
    for (var i = 1; i < pts.length; i++) s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (ferme && pts.length > 2) s += Math.hypot(pts[0][0] - pts[pts.length - 1][0], pts[0][1] - pts[pts.length - 1][1]);
    return s;
  }
  function aire(pts) {
    var s = 0;
    for (var i = 0; i < pts.length; i++) { var a = pts[i], b = pts[(i + 1) % pts.length]; s += a[0] * b[1] - b[0] * a[1]; }
    return Math.abs(s) / 2;
  }
  // Valeur réelle (mm ou mm²) à partir des points PDF et du rapport d'échelle.
  function valeurMesure(mode, pts, echelle) {
    var k = MM * (echelle || 1);
    if (mode === 'surface') return aire(pts) * k * k;
    return longueur(pts, mode === 'perimetre') * k;
  }
  function libelleMesure(mode, v) {
    function n(x, d) { return x.toLocaleString('fr-FR', { maximumFractionDigits: d, minimumFractionDigits: d }); }
    if (mode === 'surface') return v >= 1e6 ? n(v / 1e6, 3) + ' m²' : v >= 100 ? n(v / 100, 2) + ' cm²' : n(v, 1) + ' mm²';
    return v >= 1000 ? n(v / 1000, 3) + ' m' : v >= 100 ? n(v / 10, 1) + ' cm' : n(v, 1) + ' mm';
  }
  // RVB 0–255 -> CMJN 0–100 (conversion naïve, sans profil ICC).
  function rvbVersCmjn(r, g, b) {
    var R = r / 255, G = g / 255, B = b / 255, K = 1 - Math.max(R, G, B);
    if (K >= 0.9999) return [0, 0, 0, 100];
    return [(1 - R - K) / (1 - K), (1 - G - K) / (1 - K), (1 - B - K) / (1 - K), K].map(function (x) { return Math.round(x * 100); });
  }

  M._interne = M._interne || {};
  M._interne.mesure = { longueur: longueur, aire: aire, valeurMesure: valeurMesure, libelleMesure: libelleMesure, rvbVersCmjn: rvbVersCmjn };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

    Object.assign(api.IC, {
      mesure: '<path d="M3.5 15.5l12-12 5 5-12 12z"/><path d="M7 12l2 2M10 9l2 2M13 6l2 2"/>',
      pipette: '<path d="M14.5 4.5l5 5-1.8 1.8-5-5z"/><path d="M15.2 9.8L7 18l-3 1 1-3 8.2-8.2"/>'
    });
    api.BULLES.mesure = 'Mesurer'; api.BULLES.pipette = 'Pipette';
    api.LIBELLES.mesure = 'Mesure'; api.LIBELLES.pipette = 'Pipette';
    api.AIDE_OUTIL.mesure = 'Distance : cliquer le départ puis l\'arrivée. Périmètre et surface : cliquer chaque sommet, double-cliquer pour finir.';
    api.AIDE_OUTIL.pipette = 'Cliquer sur la page pour lire la couleur.';
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('mesure', 'mesure', 'Mesurer à l\'échelle') + api.outilBtn('pipette', 'pipette', 'Pipette de couleur') });

    function reglage() { var s = S().style; return { mode: s.mesureMode || 'distance', echelle: s.mesureEchelle || 1 }; }
    var enCours = null; // polygone en construction

    EXT.outils.mesure = {
      down: function (pt, p, ev, avant) {
        var r = reglage();
        // Un clic = un point. Distance : fin au 2e point ; périmètre et surface : double-clic.
        var a = enCours && api.trouverAnnot(enCours);
        if (!a) {
          a = { id: api.nid('n'), t: 'mesure', mode: r.mode, echelle: r.echelle, pts: [[pt.x, pt.y]] };
          p.annots.push(a); enCours = a.id; S().annSel = a.id; api.pushHist(avant);
        } else if (ev.detail >= 2) {
          enCours = null; api.choisirOutil('select', true);
        } else {
          a.pts.push([pt.x, pt.y]);
          if (a.mode === 'distance') { enCours = null; }
        }
        api.dessinerCalque(); api.rendreProps();
        return true;
      },
      props: function (sec) { propsMesure(sec, null); }
    };
    function bornes(a) {
      var xs = a.pts.map(function (q) { return q[0]; }), ys = a.pts.map(function (q) { return q[1]; });
      var x = Math.min.apply(null, xs), y = Math.min.apply(null, ys);
      return { x: x, y: y, w: Math.max.apply(null, xs) - x, h: Math.max.apply(null, ys) - y };
    }
    EXT.types.mesure = {
      boite: function (a) { return bornes(a); },
      // Distance : extrémités déplaçables comme une ligne (x1, y1, x2, y2).
      redim: function (a, o, poignee, pt) { var b = bornes(o), s = Math.max(0.05, (pt.x - b.x) / (b.w || 1)); a.pts = o.pts.map(function (q) { return [b.x + (q[0] - b.x) * s, b.y + (q[1] - b.y) * s]; }); },
      dessiner: function (a, g, z) {
        var d = a.pts.map(function (q, i) { return (i ? 'L' : 'M') + q[0] + ' ' + q[1]; }).join(' ') + (a.mode !== 'distance' && a.pts.length > 2 ? ' Z' : '');
        api.sv('path', { d: d, fill: a.mode === 'surface' ? 'rgba(25,113,194,.12)' : 'none', stroke: 'transparent', 'stroke-width': 10 / z }, g);
        api.sv('path', { d: d, fill: a.mode === 'surface' ? 'rgba(25,113,194,.12)' : 'none', stroke: '#1971c2', 'stroke-width': 1.2 / z, 'stroke-dasharray': (4 / z) + ' ' + (2 / z) }, g);
        a.pts.forEach(function (q) { api.sv('circle', { cx: q[0], cy: q[1], r: 2.2 / z, fill: '#1971c2' }, g); });
        var b = bornes(a), t = api.sv('text', { x: b.x + b.w / 2, y: b.y - 4 / z, 'font-size': 10 / z, 'text-anchor': 'middle', 'font-family': api.POLICE, 'class': 'tpdf-mesure-txt' }, g);
        t.textContent = libelleMesure(a.mode, valeurMesure(a.mode, a.pts, a.echelle));
      },
      props: function (sec, a) { propsMesure(sec, a); },
      exporter: async function (a, c) {
        var L = c.L, bleu = L.rgb(0.1, 0.44, 0.76), P = a.pts.map(function (q) { return c.P(q[0], q[1]); });
        var seg = P.slice(); if (a.mode !== 'distance' && P.length > 2) seg.push(P[0]);
        for (var i = 1; i < seg.length; i++) c.pg.drawLine({ start: { x: seg[i - 1][0], y: seg[i - 1][1] }, end: { x: seg[i][0], y: seg[i][1] }, thickness: 0.8, color: bleu, dashArray: [3, 2] });
        var b = bornes(a), txt = libelleMesure(a.mode, valeurMesure(a.mode, a.pts, a.echelle));
        var f = await c.pol.police(txt, {}), w = f.widthOfTextAtSize(api.nettoyerTexte(f, txt), 8), q = c.P(b.x + b.w / 2 - w / 2, b.y - 3);
        c.pg.drawText(api.nettoyerTexte(f, txt), { x: q[0], y: q[1], size: 8, font: f, color: bleu, rotate: c.rot });
      }
    };
    function propsMesure(sec, a) {
      var s = S(), r = a || reglage();
      var mode = el('select', 'tpdf-champ');
      [['distance', 'Distance'], ['perimetre', 'Périmètre'], ['surface', 'Surface']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; mode.appendChild(o); });
      mode.value = r.mode; mode.disabled = !!a;
      mode.addEventListener('change', function () { s.style.mesureMode = mode.value; enCours = null; });
      sec.appendChild(api.champ('Mesurer', mode));
      var ech = el('input', 'tpdf-champ'); ech.type = 'number'; ech.min = 0.001; ech.step = 'any'; ech.value = r.echelle;
      ech.addEventListener('change', function () {
        var v = parseFloat(ech.value);
        if (!(v > 0)) { api.toast('Échelle invalide — nombre positif.', 'danger'); return; }
        s.style.mesureEchelle = v; if (a) { api.majProp('echelle', v, a); api.validerProp(); }
      });
      sec.appendChild(api.champ('Échelle : 1 mm sur la page = … mm réels', ech));
      if (a) {
        var v = el('p', 'tpdf-resultat', libelleMesure(a.mode, valeurMesure(a.mode, a.pts, a.echelle)));
        sec.appendChild(v);
      } else sec.appendChild(el('p', 'tpdf-aide', 'Plan au 1:50 → échelle 50. Mesure sur l\'épreuve à taille réelle → 1.'));
    }

    /* ── Pipette ──────────────────────────────────────────────────────── */
    var derniere = null;
    EXT.outils.pipette = {
      down: function (pt) {
        var s = S(), cv = s.feuille.querySelector('canvas'), p = api.pageCourante();
        if (!cv || !p) return true;
        var d = api.dims(p), k = cv.width / d.w, x = Math.floor(pt.x * k), y = Math.floor(pt.y * k);
        var px = cv.getContext('2d', { willReadFrequently: true }).getImageData(Math.max(0, x - 1), Math.max(0, y - 1), 3, 3).data, r = 0, g = 0, b = 0, n = 0;
        for (var i = 0; i < px.length; i += 4) { r += px[i]; g += px[i + 1]; b += px[i + 2]; n++; }
        r = Math.round(r / n); g = Math.round(g / n); b = Math.round(b / n);
        derniere = { r: r, g: g, b: b, cmjn: rvbVersCmjn(r, g, b) };
        api.rendreProps();
        return true;
      },
      props: function (sec) {
        if (!derniere) { sec.appendChild(el('p', 'tpdf-aide', 'Aucune couleur lue.')); return; }
        var hex = '#' + [derniere.r, derniere.g, derniere.b].map(function (v) { return ('0' + v.toString(16)).slice(-2); }).join('');
        var ech = el('div', 'tpdf-pipette-ech'); ech.style.background = hex;
        sec.appendChild(ech);
        [['RVB', derniere.r + ', ' + derniere.g + ', ' + derniere.b], ['Hexadécimal', hex.toUpperCase()],
          ['CMJN (approché)', 'C ' + derniere.cmjn[0] + ' · M ' + derniere.cmjn[1] + ' · J ' + derniere.cmjn[2] + ' · N ' + derniere.cmjn[3]]].forEach(function (x) {
          var l = el('div', 'tpdf-ligne tpdf-ligne-esp'); l.appendChild(el('span', 'tpdf-lab', x[0])); var v = el('b', null, x[1]); l.appendChild(v);
          var c = el('button', 'tpdf-btn tpdf-btn-mini'); c.type = 'button'; c.innerHTML = api.ico('dupliquer', 12); c.setAttribute('data-bulle', 'Copier'); c.setAttribute('aria-label', 'Copier ' + x[0]);
          c.addEventListener('click', function () { try { navigator.clipboard.writeText(x[1]); api.toast('Copié.', 'success'); } catch (e) { api.toast('Copie impossible.', 'danger'); } });
          l.appendChild(c); sec.appendChild(l);
        });
        sec.appendChild(el('p', 'tpdf-aide', 'Couleur lue sur le rendu à l\'écran (RVB). Le CMJN est calculé sans profil : pour les valeurs d\'encre réelles, voir Prépresse › Séparations.'));
      }
    };
  });
})();
