/*
 * MyTools — éditeur PDF : modifier un texte déjà imprimé dans le PDF.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Le texte d'origine n'est pas retiré du flux de contenu : il est recouvert
 * par un rectangle de la couleur du fond (échantillonnée sur le rendu), puis
 * le nouveau texte est écrit avec la police standard la plus proche et la
 * couleur échantillonnée sur le texte d'origine. Ce n'est donc pas un outil
 * de caviardage, et l'interface le dit.
 *
 * Une correction est une annotation « remplace » rangée dans le repère de la
 * page NON pivotée (repere: 'pdf0') : elle reste collée à son texte quand la
 * page tourne, et s'exporte sans rotation.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // Élément de texte pdf.js -> boîte et ligne de base dans la page non pivotée.
  function boiteItem(tr, largeur, view) {
    var h = Math.abs(tr[3]) || Math.hypot(tr[2], tr[3]) || 10;
    var x = tr[4] - view[0], base = view[3] - tr[5];
    return { x: x, y: base - h * 0.9, w: Math.max(largeur, h * 0.3), h: h * 1.15, bx: x, by: base, taille: h };
  }
  function estHorizontal(tr) { return tr[0] > 0 && Math.abs(tr[1]) < 1e-3 && Math.abs(tr[2]) < 1e-3; }
  // Nom de police PDF + indices pdf.js -> famille standard, gras, italique.
  function correspondancePolice(info) {
    info = info || {};
    var nom = String(info.nom || '').replace(/^[A-Z]{6}\+/, '').toLowerCase();
    var css = String(info.famille || '').toLowerCase();
    var mono = !!info.mono || /courier|mono|consol|menlo|inconsolata|fixed/.test(nom) || css === 'monospace';
    var serif = !mono && (!!info.serif || css === 'serif' ||
      (/times|georgia|garamond|cambria|minion|book|roman|palatino|baskerville|bodoni|caslon|century|serif/.test(nom) && !/sans/.test(nom)));
    return {
      famille: mono ? 'mono' : serif ? 'serif' : 'sans',
      gras: !!info.gras || /bold|black|heavy|semibold|demi|[-,]bd\b/.test(nom),
      italique: !!info.italique || /italic|oblique|[-,]it\b/.test(nom)
    };
  }
  function cssPolice(p) {
    return p.famille === 'mono' ? '"Courier New", Courier, monospace' : p.famille === 'serif' ? '"Times New Roman", Times, serif' : 'Helvetica, Arial, sans-serif';
  }
  function hex2(n) { return ('0' + Math.max(0, Math.min(255, Math.round(n))).toString(16)).slice(-2); }
  function rgbHex(c) { return '#' + hex2(c[0]) + hex2(c[1]) + hex2(c[2]); }
  // interieur, anneau : RGBA à plat (Uint8ClampedArray ou tableau).
  // Fond = couleur la plus fréquente de l'anneau ; texte = moyenne des pixels
  // intérieurs les plus éloignés du fond.
  function echantillonner(interieur, anneau) {
    var seaux = {}, meilleur = null;
    for (var i = 0; i + 3 < anneau.length; i += 4) {
      if (anneau[i + 3] < 8) continue;
      var k = (anneau[i] >> 4) + ',' + (anneau[i + 1] >> 4) + ',' + (anneau[i + 2] >> 4);
      var b = seaux[k] || (seaux[k] = { n: 0, r: 0, g: 0, b: 0 });
      b.n++; b.r += anneau[i]; b.g += anneau[i + 1]; b.b += anneau[i + 2];
      if (!meilleur || b.n > meilleur.n) meilleur = b;
    }
    var fond = meilleur ? [meilleur.r / meilleur.n, meilleur.g / meilleur.n, meilleur.b / meilleur.n] : [255, 255, 255];
    var px = [];
    for (var j = 0; j + 3 < interieur.length; j += 4) {
      var dr = interieur[j] - fond[0], dg = interieur[j + 1] - fond[1], db = interieur[j + 2] - fond[2];
      px.push([dr * dr + dg * dg + db * db, interieur[j], interieur[j + 1], interieur[j + 2]]);
    }
    px.sort(function (a, b) { return b[0] - a[0]; });
    var n = Math.max(1, Math.floor(px.length * 0.15)), s = [0, 0, 0], m = 0;
    for (var q = 0; q < n && q < px.length; q++) { if (px[q][0] < 900) break; s[0] += px[q][1]; s[1] += px[q][2]; s[2] += px[q][3]; m++; }
    var texte = m ? [s[0] / m, s[1] / m, s[2] / m] : (fond[0] + fond[1] + fond[2] > 384 ? [0, 0, 0] : [255, 255, 255]);
    return { fond: rgbHex(fond), texte: rgbHex(texte) };
  }

  M._interne = M._interne || {};
  M._interne.texte = { boiteItem: boiteItem, estHorizontal: estHorizontal, correspondancePolice: correspondancePolice, echantillonner: echantillonner, rgbHex: rgbHex };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    var AVERTISSEMENT = 'Le texte d\'origine est recouvert, pas supprimé : ne pas s\'en servir pour caviarder.';

    api.IC.editerTexte = '<path d="M4 6.5V4.5h11v2"/><path d="M9.5 4.5v12"/><path d="M7.5 16.5h4"/><path d="M14 19.5l1-3.4 5-5a1.6 1.6 0 0 1 2.3 2.3l-5 5z"/>';
    api.LIBELLES.editer = 'Modifier le texte';
    api.LIBELLES.remplace = 'Texte modifié';
    api.AIDE_OUTIL.editer = 'Survoler le texte de la page, cliquer un bloc pour le corriger. Entrée valide, Échap annule.';
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('editer', 'editerTexte', 'Modifier le texte existant') });

    function avertir(sec) {
      var p = document.createElement('p'); p.className = 'tpdf-aide tpdf-avert'; p.textContent = AVERTISSEMENT;
      sec.appendChild(p);
    }
    EXT.outils.editer = { props: avertir };

    /* ── Zones cliquables sur le texte de la page ─────────────────────── */
    var _zonesPour = null, _prevenu = {};
    function vider() { var s = S(); if (s) s.html.querySelectorAll('.tpdf-tx,.tpdf-tx-edit').forEach(function (e) { e.remove(); }); _zonesPour = null; }
    function contenu(src, idx) {
      src._tx = src._tx || {};
      if (!src._tx[idx]) {
        src._tx[idx] = src.pdf.getPage(idx + 1).then(function (pg) {
          return pg.getTextContent().then(function (tc) { return { pg: pg, items: tc.items, styles: tc.styles || {} }; });
        }).catch(function () { return { pg: null, items: [], styles: {} }; });
      }
      return src._tx[idx];
    }
    function zones(p, d, z) {
      var s = S(); vider();
      if (!s || s.outil !== 'editer' || !p) return;
      var cle = p.uid + ':' + z + ':' + d.R;
      _zonesPour = cle;
      if (d.R !== 0) {
        if (!_prevenu['r' + p.uid]) { _prevenu['r' + p.uid] = 1; api.toast('Remettre la page à l\'endroit pour modifier son texte.', 'info'); }
        return;
      }
      var src = s.sources[p.src];
      contenu(src, p.idx).then(function (tc) {
        if (S() !== s || _zonesPour !== cle || api.pageCourante() !== p) return;
        var n = 0;
        tc.items.forEach(function (it, ii) {
          if (!it.str || !it.str.trim() || !estHorizontal(it.transform)) return;
          var b = boiteItem(it.transform, it.width, d.meta.view);
          var z0 = document.createElement('div');
          z0.className = 'tpdf-tx';
          var deja = trouverRemplace(p, ii);
          if (deja) z0.classList.add('tpdf-tx-fait');
          z0.style.left = (b.x * z) + 'px'; z0.style.top = (b.y * z) + 'px';
          z0.style.width = (b.w * z) + 'px'; z0.style.height = (b.h * z) + 'px';
          z0.setAttribute('data-bulle', deja ? 'Reprendre' : 'Modifier');
          z0.addEventListener('click', function (ev) { ev.stopPropagation(); ouvrir(p, d, z, it, ii, b, tc); });
          s.html.appendChild(z0); n++;
        });
        if (!n && !_prevenu['v' + p.uid]) { _prevenu['v' + p.uid] = 1; api.toast('Pas de texte modifiable sur cette page (scan ?)', 'info'); }
      });
    }
    EXT.hooks.page = (EXT.hooks.page || []).concat(zones);
    EXT.hooks.barre = (EXT.hooks.barre || []).concat(function () {
      var s = S(); if (!s) return;
      var p = api.pageCourante();
      if (s.outil !== 'editer') { if (_zonesPour) vider(); return; }
      if (!p) return;
      var d = api.dims(p), z = s.zoomCourant || 1;
      if (_zonesPour !== p.uid + ':' + z + ':' + d.R) zones(p, d, z);
    });

    function trouverRemplace(p, ii) {
      for (var i = 0; i < p.annots.length; i++) if (p.annots[i].t === 'remplace' && p.annots[i].item === ii) return p.annots[i];
      return null;
    }

    function echantillonCanvas(b, d) {
      var s = S(), cv = s.feuille.querySelector('canvas');
      if (!cv) return { fond: '#ffffff', texte: '#000000' };
      var k = cv.width / d.w, c = cv.getContext('2d', { willReadFrequently: true });
      var x0 = Math.max(0, Math.floor(b.x * k)), y0 = Math.max(0, Math.floor(b.y * k));
      var x1 = Math.min(cv.width, Math.ceil((b.x + b.w) * k)), y1 = Math.min(cv.height, Math.ceil((b.y + b.h) * k));
      if (x1 - x0 < 1 || y1 - y0 < 1) return { fond: '#ffffff', texte: '#000000' };
      var interieur = c.getImageData(x0, y0, x1 - x0, y1 - y0).data;
      var e = Math.max(2, Math.round(k * 1.5)), anneau = [];
      [[x0 - e, y0 - e, x1 - x0 + 2 * e, e], [x0 - e, y1, x1 - x0 + 2 * e, e], [x0 - e, y0, e, y1 - y0], [x1, y0, e, y1 - y0]].forEach(function (r) {
        var rx = Math.max(0, r[0]), ry = Math.max(0, r[1]);
        var rw = Math.min(cv.width, r[0] + r[2]) - rx, rh = Math.min(cv.height, r[1] + r[3]) - ry;
        if (rw > 0 && rh > 0) { var dd = c.getImageData(rx, ry, rw, rh).data; for (var i = 0; i < dd.length; i++) anneau.push(dd[i]); }
      });
      return echantillonner(interieur, anneau);
    }
    function infoPolice(tc, it) {
      var info = { famille: (tc.styles[it.fontName] || {}).fontFamily };
      try {
        if (tc.pg && tc.pg.commonObjs.has(it.fontName)) {
          var f = tc.pg.commonObjs.get(it.fontName);
          info.nom = f.name || f.fallbackName || '';
          info.gras = !!(f.bold || f.black); info.italique = !!f.italic;
          info.mono = !!f.isMonospace; info.serif = !!f.isSerifFont;
        }
      } catch (e) { /* police pas encore chargée : on se contente du style */ }
      var r = correspondancePolice(info);
      r.nom = String(info.nom || '').replace(/^[A-Z]{6}\+/, '');
      return r;
    }

    /* ── Éditeur posé sur le texte ────────────────────────────────────── */
    function ouvrir(p, d, z, it, ii, b, tc) {
      var s = S();
      s.html.querySelectorAll('.tpdf-tx-edit').forEach(function (e) { e.remove(); });
      var a = trouverRemplace(p, ii), neuf = !a;
      if (neuf) {
        var col = echantillonCanvas(b, d);
        a = { id: api.nid('n'), t: 'remplace', item: ii, orig: it.str, texte: it.str,
          x: b.x, y: b.y, w: b.w, h: b.h, bx: b.bx, by: b.by, taille: b.taille,
          police: infoPolice(tc, it), couleur: col.texte, fond: col.fond };
      }
      editer(a, p, z, neuf);
    }
    function editer(a, p, z, neuf) {
      var s = S();
      var inp = document.createElement('input');
      inp.type = 'text'; inp.className = 'tpdf-tx-edit'; inp.value = a.texte;
      inp.style.left = (a.x * z) + 'px'; inp.style.top = (a.y * z) + 'px';
      inp.style.minWidth = (a.w * z + 8) + 'px'; inp.style.height = (a.h * z) + 'px';
      inp.style.fontSize = (a.taille * z) + 'px';
      inp.style.fontFamily = cssPolice(a.police);
      inp.style.fontWeight = a.police.gras ? '700' : '400';
      inp.style.fontStyle = a.police.italique ? 'italic' : 'normal';
      inp.style.color = a.couleur; inp.style.background = a.fond;
      inp.setAttribute('aria-label', 'Nouveau texte');
      var fini = false;
      function finir(garder) {
        if (fini) return; fini = true;
        var v = inp.value; inp.remove();
        if (!garder) return;
        var avant = api.snapshot();
        if (neuf) { if (v === a.orig) return; a.texte = v; p.annots.push(a); }
        else { if (v === a.texte) return; a.texte = v; }
        api.pushHist(avant);
        s.annSel = null;
        api.dessinerCalque(); api.majBadges(); api.rendreBarre(); api.rendreProps();
        var d = api.dims(p); zones(p, d, s.zoomCourant || 1);
      }
      inp.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter') { ev.preventDefault(); finir(true); }
        else if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); finir(false); }
      });
      inp.addEventListener('blur', function () { finir(true); });
      s.html.appendChild(inp);
      requestAnimationFrame(function () { inp.focus(); inp.select(); });
    }

    /* ── Type d'annotation « remplace » ───────────────────────────────── */
    EXT.types.remplace = {
      repere: 'pdf0', fixe: true,
      boite: function (a) { return { x: a.x, y: a.y, w: a.w, h: a.h }; },
      dessiner: function (a, g) {
        api.sv('rect', { x: a.x - 0.6, y: a.y - 0.6, width: a.w + 1.2, height: a.h + 1.2, fill: a.fond }, g);
        var t = api.sv('text', { x: a.bx, y: a.by, 'font-size': a.taille, 'font-family': cssPolice(a.police),
          'font-weight': a.police.gras ? 'bold' : 'normal', 'font-style': a.police.italique ? 'italic' : 'normal', fill: a.couleur }, g);
        t.textContent = a.texte;
      },
      dblclic: function (a) {
        var s = S(), p = api.pageCourante();
        if (api.dims(p).R !== 0) { api.toast('Remettre la page à l\'endroit pour modifier son texte.', 'info'); return; }
        editer(a, p, s.zoomCourant || 1, false);
      },
      props: function (sec, a) {
        if (!a) return;
        var ta = document.createElement('input'); ta.type = 'text'; ta.className = 'tpdf-champ'; ta.value = a.texte; ta.setAttribute('data-prop', 'texte');
        ta.addEventListener('input', function () { api.majProp('texte', ta.value, a); });
        ta.addEventListener('change', api.validerProp);
        sec.appendChild(api.champ('Nouveau texte', ta));
        var o = document.createElement('p'); o.className = 'tpdf-aide';
        o.textContent = 'Texte d\'origine : « ' + a.orig + ' »';
        sec.appendChild(o);
        var f = document.createElement('p'); f.className = 'tpdf-aide';
        var nf = { sans: 'Helvetica', serif: 'Times', mono: 'Courier' }[a.police.famille] + (a.police.gras ? ' gras' : '') + (a.police.italique ? ' italique' : '');
        f.textContent = 'Police : ' + nf + (a.police.nom ? ' (au plus près de « ' + a.police.nom + ' »)' : '') + '. Supprimer l\'annotation rétablit le texte d\'origine.';
        sec.appendChild(f);
        avertir(sec);
      },
      exporter: async function (a, c) {
        var L = c.L, f = api.hexRgb(a.fond), t = api.hexRgb(a.couleur);
        var p1 = c.P(a.x - 0.6, a.y - 0.6), p2 = c.P(a.x + a.w + 0.6, a.y + a.h + 0.6);
        c.pg.drawRectangle({ x: Math.min(p1[0], p2[0]), y: Math.min(p1[1], p2[1]), width: Math.abs(p2[0] - p1[0]), height: Math.abs(p2[1] - p1[1]), color: L.rgb(f[0], f[1], f[2]) });
        if (!a.texte) return;
        var font = await c.pol.police(a.texte, a.police), b = c.P(a.bx, a.by);
        c.pg.drawText(api.nettoyerTexte(font, a.texte), { x: b[0], y: b[1], size: a.taille, font: font, color: L.rgb(t[0], t[1], t[2]) });
      }
    };
  });
})();
