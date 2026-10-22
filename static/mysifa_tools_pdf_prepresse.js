/*
 * MyTools — éditeur PDF : prépresse (menu « Prépresse »).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   preflight BAT (polices non incorporées, images sous la résolution voulue,
 *     couleurs RVB, fond perdu, traits trop fins — seuils de config.py via
 *     /api/tools/pdf/reglages), rapport cliquable ;
 *   séparations C, M, J, N et couverture d'encre au point survolé ;
 *   traits de coupe, fond perdu, repères de pliage, gamme de contrôle ;
 *   imposition (2 ou 4 en 1, livret, step and repeat) ;
 *   aplatir (champs, pages en image).
 *
 * Limite assumée : pdf.js ne livre que le rendu RVB. Les séparations sont
 * calculées depuis ce rendu (conversion sans profil) : les valeurs d'encre
 * d'origine et les tons directs ne sont pas lus pixel par pixel ; les tons
 * directs sont seulement listés (espaces Separation / DeviceN des ressources).
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  var MM = 72 / 25.4;
  /* ── Fonctions pures (tests) ──────────────────────────────────────── */
  // Ordre d'impression d'un livret (piqûre à cheval) : par feuille, recto
  // [gauche, droite] puis verso ; -1 = page blanche.
  function ordreLivret(n) {
    var t = Math.ceil(n / 4) * 4, faces = [];
    for (var i = 0; i < t / 2; i += 2) {
      faces.push([t - 1 - i, i]);
      faces.push([i + 1, t - 2 - i]);
    }
    return faces.map(function (f) { return f.map(function (x) { return x < n ? x : -1; }); });
  }
  function grille(W, H, nx, ny, marge, gouttiere) {
    var cw = (W - 2 * marge - (nx - 1) * gouttiere) / nx, ch = (H - 2 * marge - (ny - 1) * gouttiere) / ny, out = [];
    for (var j = 0; j < ny; j++) for (var i = 0; i < nx; i++) out.push({ x: marge + i * (cw + gouttiere), y: H - marge - (j + 1) * ch - j * gouttiere, w: cw, h: ch });
    return out;
  }
  function ajuster(pw, ph, cw, ch) {
    var k = Math.min(cw / pw, ch / ph);
    return { k: k, dx: (cw - pw * k) / 2, dy: (ch - ph * k) / 2 };
  }
  // Nombre d'exemplaires qui tiennent (step and repeat), orientation comprise.
  function maxRepetition(W, H, pw, ph, marge, gouttiere) {
    function n(a, b) { var nx = Math.floor((W - 2 * marge + gouttiere) / (a + gouttiere)), ny = Math.floor((H - 2 * marge + gouttiere) / (b + gouttiere)); return { nx: Math.max(0, nx), ny: Math.max(0, ny), tourne: false }; }
    var d = n(pw, ph), r = n(ph, pw); r.tourne = true;
    return d.nx * d.ny >= r.nx * r.ny ? d : r;
  }
  function couverture(r, g, b) {
    var R = r / 255, G = g / 255, B = b / 255, K = 1 - Math.max(R, G, B);
    var c = K >= 0.9999 ? [0, 0, 0, 1] : [(1 - R - K) / (1 - K), (1 - G - K) / (1 - K), (1 - B - K) / (1 - K), K];
    return { c: c, total: Math.round((c[0] + c[1] + c[2] + c[3]) * 100) };
  }
  // Épaisseurs de trait (opérateur « w ») d'un flux de contenu décodé.
  function traitsFins(contenu, min) {
    var re = /(?:^|[\s\]])(-?\d*\.?\d+)\s+w(?=\s)/g, r, l = [];
    // « 0 w » est écrit par la plupart des outils avant un simple remplissage : ignoré.
    while ((r = re.exec(contenu))) { var v = parseFloat(r[1]); if (v > 0 && v < min) l.push(v); }
    return l;
  }
  function operateursCouleur(contenu) {
    function n(re) { var m = contenu.match(re); return m ? m.length : 0; }
    return { rvb: n(/(?:\s|^)(?:-?\d*\.?\d+\s+){3}(?:rg|RG)(?=\s)/g), cmjn: n(/(?:\s|^)(?:-?\d*\.?\d+\s+){4}(?:k|K)(?=\s)/g) };
  }

  M._interne = M._interne || {};
  M._interne.prepresse = { ordreLivret: ordreLivret, grille: grille, ajuster: ajuster, maxRepetition: maxRepetition, couverture: couverture, traitsFins: traitsFins, operateursCouleur: operateursCouleur };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function choix(opts, v) { var s = el('select', 'tpdf-champ'); opts.forEach(function (o) { var x = el('option', null, o[1]); x.value = o[0]; s.appendChild(x); }); if (v != null) s.value = v; return s; }
    function nombre(v, min, max, pas) { var n = el('input', 'tpdf-champ'); n.type = 'number'; n.min = min; n.max = max; n.step = pas || 1; n.value = v; return n; }
    function coche(lib, v) { var l = el('label', 'tpdf-case'), i = el('input'); i.type = 'checkbox'; i.checked = !!v; l.appendChild(i); l.appendChild(document.createTextNode(' ' + lib)); l.input = i; return l; }

    Object.assign(api.IC, {
      prepresse: '<circle cx="12" cy="12" r="7.5"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/>',
      preflight: '<path d="M9 11.5l2 2 4-4"/><path d="M12 3l7.5 3v5.5c0 4.5-3.2 8-7.5 9.5-4.3-1.5-7.5-5-7.5-9.5V6z"/>',
      separations: '<circle cx="9" cy="9" r="5.5"/><circle cx="15" cy="9" r="5.5"/><circle cx="12" cy="14.5" r="5.5"/>',
      marques: '<path d="M3 7h4M7 3v4M17 3v4M17 7h4M3 17h4M7 17v4M17 17v4M17 17h4"/><rect x="9" y="9" width="6" height="6"/>',
      imposition: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M12 4v16M3 12h18"/>',
      aplatir: '<path d="M4 15.5l8 4 8-4"/><path d="M4 11.5l8 4 8-4"/><path d="M12 3.5l8 4-8 4-8-4z"/>'
    });
    EXT.menus.prepresse = { libelle: 'Prépresse', icone: 'prepresse', ordre: 4, items: [
      { act: 'preflight', icone: 'preflight', libelle: 'Preflight BAT…', bulle: 'Preflight', doc: 1 },
      { act: 'separations', icone: 'separations', libelle: 'Séparations et couverture d\'encre…', bulle: 'Séparations', doc: 1 },
      { separe: true },
      { act: 'marques', icone: 'marques', libelle: 'Traits de coupe, fond perdu, repères…', bulle: 'Repères', doc: 1 },
      { act: 'imposition', icone: 'imposition', libelle: 'Imposition…', bulle: 'Imposer', doc: 1 },
      { act: 'aplatir', icone: 'aplatir', libelle: 'Aplatir…', bulle: 'Aplatir', doc: 1 }
    ] };

    var _reglages = null;
    function reglages() {
      if (!_reglages) _reglages = fetch('/api/tools/pdf/reglages', { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : {}; })
        .then(function (j) { return j.preflight || {}; }).catch(function () { return {}; })
        .then(function (p) { return { dpi: p.dpi_min || 300, trait: p.trait_min_pt != null ? p.trait_min_pt : 0.25, fond: p.fond_perdu_mm != null ? p.fond_perdu_mm : 3 }; });
      return _reglages;
    }
    function decoder(L, doc, flux) {
      var l = flux instanceof L.PDFArray ? flux.asArray() : [flux], t = '';
      l.forEach(function (r) { var s = doc.context.lookup(r); try { t += new TextDecoder('latin1').decode(L.decodePDFRawStream(s).decode()) + '\n'; } catch (e) { try { t += new TextDecoder('latin1').decode(s.getContents()) + '\n'; } catch (x) { /* flux illisible */ } } });
      return t;
    }
    function flash(i, r) {
      api.fermerModale(); api.allerPage(i, true);
      setTimeout(function () {
        var s = S(); if (!r) return;
        var f = api.sv('rect', { x: r.x - 3, y: r.y - 3, width: r.w + 6, height: r.h + 6, 'class': 'tpdf-flash' }, s.svg);
        setTimeout(function () { f.remove(); }, 2500);
      }, 300);
    }

    /* ── Preflight ────────────────────────────────────────────────────── */
    async function analyser(seuils, progres) {
      var s = S(), L = await api.pdflib(), pj = await api.pdfjs(), octets = await api.construire();
      var doc = await L.PDFDocument.load(octets, { updateMetadata: false }), N = L.PDFName;
      var pdf = await pj.getDocument({ data: octets.slice(), isEvalSupported: false }).promise, pb = [];
      try {
        for (var i = 0; i < doc.getPageCount(); i++) {
          if (progres) progres(i + 1, doc.getPageCount());
          var pg = doc.getPage(i), p = s.pages[i], d = api.dims(p), res = pg.node.Resources();
          // Polices
          var polices = res && doc.context.lookup(res.get(N.of('Font'))), dejaVues = {};
          if (polices instanceof L.PDFDict) polices.keys().forEach(function (k) {
            var f = doc.context.lookup(polices.get(k)); if (!(f instanceof L.PDFDict)) return;
            var nom = String(f.get(N.of('BaseFont')) || k).replace(/^\/([A-Z]{6}\+)?/, ''), fd = f.get(N.of('FontDescriptor'));
            if (String(f.get(N.of('Subtype'))) === '/Type0') { var desc = doc.context.lookup(f.get(N.of('DescendantFonts'))); var df = desc instanceof L.PDFArray ? doc.context.lookup(desc.get(0)) : null; fd = df && df.get(N.of('FontDescriptor')); }
            if (String(f.get(N.of('Subtype'))) === '/Type3') return;
            fd = fd && doc.context.lookup(fd);
            var inc = fd instanceof L.PDFDict && (fd.get(N.of('FontFile')) || fd.get(N.of('FontFile2')) || fd.get(N.of('FontFile3')));
            if (!inc && !dejaVues[nom]) { dejaVues[nom] = 1; pb.push({ type: 'police', page: i, msg: 'Police non incorporée : ' + nom }); }
          });
          // Couleurs et traits (contenu de la page)
          var contenu = pg.node.Contents() ? decoder(L, doc, pg.node.get(N.of('Contents'))) : '';
          var oc = operateursCouleur(contenu);
          if (oc.rvb) pb.push({ type: 'rvb', page: i, msg: oc.rvb + ' couleur(s) en RVB dans le contenu' + (oc.cmjn ? ' (et ' + oc.cmjn + ' en CMJN)' : '') });
          var fins = traitsFins(contenu, seuils.trait);
          if (fins.length) pb.push({ type: 'trait', page: i, msg: fins.length + ' trait(s) sous ' + seuils.trait + ' pt (le plus fin : ' + Math.min.apply(null, fins) + ' pt)' });
          // Images en RVB (ressources de la page)
          var xo = res && doc.context.lookup(res.get(N.of('XObject')));
          if (xo instanceof L.PDFDict) xo.keys().forEach(function (k) {
            var o = doc.context.lookup(xo.get(k)); if (!o || !o.dict || String(o.dict.get(N.of('Subtype'))) !== '/Image') return;
            var cs = doc.context.lookup(o.dict.get(N.of('ColorSpace'))), rvb = String(cs) === '/DeviceRGB';
            if (cs instanceof L.PDFArray && String(cs.get(0)) === '/ICCBased') { var icc = doc.context.lookup(cs.get(1)); rvb = icc && icc.dict && String(icc.dict.get(N.of('N'))) === '3'; }
            if (rvb) pb.push({ type: 'rvb', page: i, msg: 'Image en RVB (' + String(k).slice(1) + ')' });
          });
          // Fond perdu
          var trim = pg.node.get(N.of('TrimBox')), bleed = pg.node.get(N.of('BleedBox'));
          if (!trim || !bleed) pb.push({ type: 'fond', page: i, msg: 'Pas de fond perdu défini (TrimBox / BleedBox absents)' });
          else {
            var t = pg.getTrimBox(), b = pg.getBleedBox(), mg = Math.min(t.x - b.x, t.y - b.y, b.x + b.width - t.x - t.width, b.y + b.height - t.y - t.height) / MM;
            if (mg < seuils.fond - 0.05) pb.push({ type: 'fond', page: i, msg: 'Fond perdu de ' + mg.toFixed(1) + ' mm (attendu ' + seuils.fond + ' mm)' });
          }
          // Résolution des images (rendu pdf.js : taille affichée × pixels)
          var page = await pdf.getPage(i + 1), ops = await page.getOperatorList(), O = pj.OPS, pile = [], ctm = [1, 0, 0, 1, 0, 0];
          function mul(m, n) { return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3], m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]]; }
          for (var k = 0; k < ops.fnArray.length; k++) {
            var fn = ops.fnArray[k], a = ops.argsArray[k];
            if (fn === O.save) pile.push(ctm.slice());
            else if (fn === O.restore) ctm = pile.pop() || [1, 0, 0, 1, 0, 0];
            else if (fn === O.transform) ctm = mul(ctm, a);
            else if ((fn === O.paintImageXObject || fn === O.paintInlineImageXObject) && a) {
              var wpx = a[1] || (a[0] && a[0].width), hpx = a[2] || (a[0] && a[0].height);
              var wpt = Math.hypot(ctm[0], ctm[1]), hpt = Math.hypot(ctm[2], ctm[3]);
              if (!wpx || !wpt) continue;
              var dpi = Math.min(wpx / (wpt / 72), hpx / (hpt / 72));
              if (dpi < seuils.dpi - 0.5) {
                var c1 = api.versVue(d.meta.view, d.R, ctm[4], ctm[5]), c2 = api.versVue(d.meta.view, d.R, ctm[4] + ctm[0] + ctm[2], ctm[5] + ctm[1] + ctm[3]);
                pb.push({ type: 'image', page: i, msg: 'Image à ' + Math.round(dpi) + ' dpi (minimum ' + seuils.dpi + ')',
                  rect: { x: Math.min(c1[0], c2[0]), y: Math.min(c1[1], c2[1]), w: Math.abs(c2[0] - c1[0]), h: Math.abs(c2[1] - c1[1]) } });
              }
            }
          }
        }
      } finally { try { pdf.destroy(); } catch (e) { /* libéré */ } }
      return pb;
    }
    var TITRES = { police: 'Polices', image: 'Résolution des images', rvb: 'Couleurs RVB', fond: 'Fond perdu', trait: 'Traits trop fins' };
    async function panneauPreflight() {
      var corps = el('div'), res = el('div', 'tpdf-resultat', 'Analyse…'), liste = el('div', 'tpdf-lc');
      corps.appendChild(res); corps.appendChild(liste);
      api.ouvrirModale('Preflight BAT', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'preflight', large: true });
      try {
        var seuils = await reglages();
        var pb = await analyser(seuils, function (i, n) { res.textContent = 'Analyse — page ' + i + ' / ' + n + '…'; });
        res.textContent = pb.length ? pb.length + ' point(s) à vérifier.' : 'Aucun problème détecté.';
        corps.insertBefore(el('p', 'tpdf-aide', 'Seuils : images ≥ ' + seuils.dpi + ' dpi, traits ≥ ' + seuils.trait + ' pt, fond perdu ≥ ' + seuils.fond + ' mm. Analyse du PDF tel qu\'il sera enregistré (annotations comprises). Les traits sont lus sans tenir compte des mises à l\'échelle du contenu.'), liste);
        Object.keys(TITRES).forEach(function (t) {
          var l = pb.filter(function (x) { return x.type === t; }); if (!l.length) return;
          liste.appendChild(el('div', 'tpdf-lab', TITRES[t] + ' (' + l.length + ')'));
          l.forEach(function (x) {
            var b = el('button', 'tpdf-lc-item'); b.type = 'button';
            b.appendChild(el('span', 'tpdf-lc-nom', 'Page ' + (x.page + 1))); b.appendChild(el('span', 'tpdf-lc-val', x.msg));
            b.addEventListener('click', function () { flash(x.page, x.rect); });
            liste.appendChild(b);
          });
        });
      } catch (e) { res.textContent = ''; api.toast(api.msgErreur(e), 'danger'); }
    }
    EXT.actions.preflight = { fn: panneauPreflight }; EXT.panneaux.preflight = panneauPreflight;

    /* ── Séparations ──────────────────────────────────────────────────── */
    async function tonsDirects() {
      var s = S(), L = await api.pdflib(), noms = {}, ids = {};
      s.pages.forEach(function (p) { ids[p.src] = 1; });
      function nom(n) { return String(n).replace(/^\//, '').replace(/#20/g, ' '); }
      Object.keys(ids).forEach(function (id) {
        var doc = s.sources[id].lib;
        doc.context.enumerateIndirectObjects().forEach(function (x) {
          var o = x[1];
          if (!(o instanceof L.PDFArray) || o.size() < 2) return;
          var t = String(o.get(0));
          if (t === '/Separation') noms[nom(o.get(1))] = 1;
          if (t === '/DeviceN') { var a = doc.context.lookup(o.get(1)); if (a instanceof L.PDFArray) a.asArray().forEach(function (n) { noms[nom(n)] = 1; }); }
        });
      });
      return Object.keys(noms).filter(function (n) { return !/^(Cyan|Magenta|Yellow|Black|All|None)$/.test(n); });
    }
    async function panneauSeparations() {
      var corps = el('div', 'tpdf-sep'), haut = el('div', 'tpdf-ligne tpdf-ligne-esp'), plaque = el('div', 'tpdf-seg');
      var etat = { plaque: 'toutes' };
      [['toutes', 'Toutes'], ['0', 'Cyan'], ['1', 'Magenta'], ['2', 'Jaune'], ['3', 'Noir']].forEach(function (x) {
        var b = el('button', 'tpdf-btn' + (x[0] === etat.plaque ? ' tpdf-actif' : ''), x[1]); b.type = 'button'; b.setAttribute('data-bulle', x[1]);
        b.addEventListener('click', function () { etat.plaque = x[0]; plaque.querySelectorAll('button').forEach(function (y) { y.classList.toggle('tpdf-actif', y === b); }); dessiner(); });
        plaque.appendChild(b);
      });
      haut.appendChild(api.champ('Plaque', plaque));
      var lecture = el('div', 'tpdf-sep-lecture', 'Survoler la page.'); haut.appendChild(lecture);
      corps.appendChild(haut);
      var vue = el('canvas', 'tpdf-sep-vue'); corps.appendChild(vue);
      var info = el('p', 'tpdf-aide'); corps.appendChild(info);
      api.ouvrirModale('Séparations — page ' + (S().cur + 1), corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'separations', large: true });
      var src = null, W = 0, H = 0, cmjn = null, max = 0;
      try {
        var b = await api.construire([api.pageCourante()]), pj = await api.pdfjs();
        var doc = await pj.getDocument({ data: b.slice(), isEvalSupported: false }).promise, pg = await doc.getPage(1);
        var v1 = pg.getViewport({ scale: 1 }), k = Math.min(2, 900 / v1.width), vp = pg.getViewport({ scale: k });
        var cv = el('canvas'); cv.width = W = Math.ceil(vp.width); cv.height = H = Math.ceil(vp.height);
        var c = cv.getContext('2d', { willReadFrequently: true }); c.fillStyle = 'white'; c.fillRect(0, 0, W, H);
        await pg.render({ canvasContext: c, viewport: vp, intent: 'print' }).promise; doc.destroy();
        src = c.getImageData(0, 0, W, H);
        cmjn = new Uint8Array(W * H * 4);
        for (var i = 0, j = 0; i < src.data.length; i += 4, j += 4) {
          var r = couverture(src.data[i], src.data[i + 1], src.data[i + 2]);
          for (var q = 0; q < 4; q++) cmjn[j + q] = Math.round(r.c[q] * 255);
          if (r.total > max) max = r.total;
        }
        var directs = await tonsDirects();
        info.textContent = 'Couverture maximale sur la page : ' + max + ' %. Calcul depuis le rendu écran (RVB → CMJN sans profil) : indicatif, pas les valeurs d\'encre du fichier.' +
          (directs.length ? ' Tons directs présents (sans plaque propre ici) : ' + directs.join(', ') + '.' : ' Aucun ton direct déclaré.');
        dessiner();
      } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      function dessiner() {
        if (!src) return;
        vue.width = W; vue.height = H;
        var x = vue.getContext('2d');
        if (etat.plaque === 'toutes') { x.putImageData(src, 0, 0); return; }
        var p = +etat.plaque, img = x.createImageData(W, H), teinte = [[0, 160, 227], [229, 0, 126], [255, 237, 0], [0, 0, 0]][p];
        for (var i = 0; i < cmjn.length; i += 4) {
          var a = cmjn[i + p] / 255;
          img.data[i] = Math.round(255 - a * (255 - teinte[0])); img.data[i + 1] = Math.round(255 - a * (255 - teinte[1])); img.data[i + 2] = Math.round(255 - a * (255 - teinte[2])); img.data[i + 3] = 255;
        }
        x.putImageData(img, 0, 0);
      }
      vue.addEventListener('mousemove', function (ev) {
        if (!cmjn) return;
        var r = vue.getBoundingClientRect(), x = Math.floor((ev.clientX - r.left) * W / r.width), y = Math.floor((ev.clientY - r.top) * H / r.height);
        if (x < 0 || y < 0 || x >= W || y >= H) return;
        var i = (y * W + x) * 4, v = [0, 1, 2, 3].map(function (q) { return Math.round(cmjn[i + q] / 2.55); });
        lecture.textContent = 'C ' + v[0] + ' % · M ' + v[1] + ' % · J ' + v[2] + ' % · N ' + v[3] + ' % — total ' + (v[0] + v[1] + v[2] + v[3]) + ' %';
      });
    }
    EXT.actions.separations = { fn: panneauSeparations }; EXT.panneaux.separations = panneauSeparations;

    /* ── Repères d'impression ─────────────────────────────────────────── */
    function marques() {
      var s = S();
      if (!s.marques) s.marques = { actif: false, coupe: true, fond: 3, pliage: 'aucun', gamme: true };
      return s.marques;
    }
    function panneauMarques() {
      var m = marques(), corps = el('div');
      var a = coche('Ajouter les repères à l\'enregistrement', m.actif), c = coche('Traits de coupe', m.coupe), g = coche('Gamme de contrôle (C, M, J, N, 50 %)', m.gamme);
      var f = nombre(m.fond, 0, 20, 0.5), p = choix([['aucun', 'Aucun'], ['vertical', 'Pli vertical au milieu'], ['horizontal', 'Pli horizontal au milieu'], ['tiers', 'Pli roulé en trois (vertical)']], m.pliage);
      [a, c, g].forEach(function (x) { corps.appendChild(x); });
      corps.appendChild(api.champ('Fond perdu (mm)', f)); corps.appendChild(api.champ('Repères de pliage', p));
      corps.appendChild(el('p', 'tpdf-aide', 'La page grandit autour du format fini (TrimBox) ; le fond perdu (BleedBox) montre ce qui dépasse déjà du format dans le document — il ne l\'invente pas.'));
      api.ouvrirModale('Traits de coupe et repères', corps, [{ txt: 'Valider', plein: true, fn: function () {
        m.actif = a.input.checked; m.coupe = c.input.checked; m.gamme = g.input.checked; m.fond = Math.max(0, parseFloat(f.value) || 0); m.pliage = p.value;
        api.fermerModale(); api.toast(m.actif ? 'Repères ajoutés à l\'enregistrement.' : 'Repères désactivés.', 'success');
      } }], { cle: 'marques' });
    }
    EXT.actions.marques = { fn: panneauMarques }; EXT.panneaux.marques = panneauMarques;
    EXT.hooks.exportPageMarques = (EXT.hooks.exportPageMarques || []).concat(function (pg, p, d, ctx) {
      var m = S().marques; if (!m || !m.actif) return;
      var L = ctx.L, t = pg.getCropBox(), bleed = m.fond * MM, marge = 12 * MM + bleed;
      var X = t.x - marge, Y = t.y - marge, W = t.width + 2 * marge, H = t.height + 2 * marge;
      pg.setMediaBox(X, Y, W, H); pg.setCropBox(X, Y, W, H);
      pg.setTrimBox(t.x, t.y, t.width, t.height); pg.setBleedBox(t.x - bleed, t.y - bleed, t.width + 2 * bleed, t.height + 2 * bleed);
      var reg = L.cmyk(1, 1, 1, 1), ep = 0.25, lg = 8 * MM, ecart = bleed + 1 * MM;
      function trait(x1, y1, x2, y2, dash) { pg.drawLine({ start: { x: x1, y: y1 }, end: { x: x2, y: y2 }, thickness: ep, color: reg, dashArray: dash }); }
      var x0 = t.x, y0 = t.y, x1 = t.x + t.width, y1 = t.y + t.height;
      if (m.coupe) [[x0, y0, -1, -1], [x1, y0, 1, -1], [x0, y1, -1, 1], [x1, y1, 1, 1]].forEach(function (c) {
        trait(c[0] + c[2] * ecart, c[1], c[0] + c[2] * (ecart + lg), c[1]);
        trait(c[0], c[1] + c[3] * ecart, c[0], c[1] + c[3] * (ecart + lg));
      });
      var plis = m.pliage === 'vertical' ? [['v', 0.5]] : m.pliage === 'horizontal' ? [['h', 0.5]] : m.pliage === 'tiers' ? [['v', 1 / 3], ['v', 2 / 3]] : [];
      plis.forEach(function (q) {
        if (q[0] === 'v') { var x = x0 + t.width * q[1]; trait(x, y1 + ecart, x, y1 + ecart + lg, [2, 2]); trait(x, y0 - ecart, x, y0 - ecart - lg, [2, 2]); }
        else { var y = y0 + t.height * q[1]; trait(x0 - ecart, y, x0 - ecart - lg, y, [2, 2]); trait(x1 + ecart, y, x1 + ecart + lg, y, [2, 2]); }
      });
      if (m.gamme) {
        var c5 = 5 * MM, gx = x0, gy = y0 - ecart - c5 - 1 * MM;
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [0.5, 0, 0, 0], [0, 0.5, 0, 0], [0, 0, 0.5, 0], [0, 0, 0, 0.5], [1, 1, 1, 1]].forEach(function (v, i) {
          pg.drawRectangle({ x: gx + i * c5, y: gy, width: c5, height: c5, color: L.cmyk(v[0], v[1], v[2], v[3]) });
        });
      }
    });

    /* ── Imposition ───────────────────────────────────────────────────── */
    var FEUILLES = { a4: [595.28, 841.89], a3: [841.89, 1190.55], sra3: [907.09, 1275.59] };
    function panneauImposition() {
      var corps = el('div');
      var mode = choix([['2', '2 pages par feuille'], ['4', '4 pages par feuille'], ['livret', 'Livret (piqûre à cheval)'], ['step', 'Step and repeat (page courante)']], '2');
      var feuille = choix([['a4', 'A4'], ['a3', 'A3'], ['sra3', 'SRA3 (320 × 450 mm)']], 'a3');
      var marge = nombre(5, 0, 50, 0.5), gout = nombre(4, 0, 50, 0.5), coupe = coche('Traits de coupe autour de chaque pose', true);
      corps.appendChild(api.champ('Mode', mode)); corps.appendChild(api.champ('Feuille', feuille));
      var lg = el('div', 'tpdf-ligne tpdf-ligne-esp'); lg.appendChild(api.champ('Marge (mm)', marge)); lg.appendChild(api.champ('Gouttière (mm)', gout)); corps.appendChild(lg);
      corps.appendChild(coupe);
      corps.appendChild(el('p', 'tpdf-aide', 'Produit un nouveau PDF à imprimer ; le document ouvert ne change pas. Les pages sont posées à taille réelle si elles tiennent, réduites sinon (step and repeat : taille réelle, nombre de poses maximal).'));
      api.ouvrirModale('Imposition', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Imposer et télécharger', plein: true, fn: async function () {
          api.fermerModale(); api.occuper('Imposition…');
          try {
            var L = await api.pdflib(), s = S(), liste = mode.value === 'step' ? [api.pageCourante()] : s.pages;
            var b = await api.construire(liste), srcDoc = await L.PDFDocument.load(b), out = await L.PDFDocument.create();
            var emb = await out.embedPages(srcDoc.getPages()), F = FEUILLES[feuille.value], mg = parseFloat(marge.value) * MM, gt = parseFloat(gout.value) * MM;
            function poser(sheet, e, cel) {
              if (!e) return;
              var a = ajuster(e.width, e.height, cel.w, cel.h), k = Math.min(1, a.k), w = e.width * k, h = e.height * k;
              var x = cel.x + (cel.w - w) / 2, y = cel.y + (cel.h - h) / 2;
              sheet.drawPage(e, { x: x, y: y, width: w, height: h });
              if (coupe.input.checked) {
                var reg = L.cmyk(1, 1, 1, 1), l = 4 * MM, o = 1 * MM;
                [[x, y, -1, -1], [x + w, y, 1, -1], [x, y + h, -1, 1], [x + w, y + h, 1, 1]].forEach(function (c) {
                  sheet.drawLine({ start: { x: c[0] + c[2] * o, y: c[1] }, end: { x: c[0] + c[2] * (o + l), y: c[1] }, thickness: 0.25, color: reg });
                  sheet.drawLine({ start: { x: c[0], y: c[1] + c[3] * o }, end: { x: c[0], y: c[1] + c[3] * (o + l) }, thickness: 0.25, color: reg });
                });
              }
            }
            var n = emb.length;
            if (mode.value === '2' || mode.value === 'livret') {
              var W = F[1], H = F[0]; // paysage, deux colonnes
              var cel = grille(W, H, 2, 1, mg, gt);
              if (mode.value === '2') for (var i = 0; i < n; i += 2) { var sh = out.addPage([W, H]); poser(sh, emb[i], cel[0]); poser(sh, emb[i + 1], cel[1]); }
              else ordreLivret(n).forEach(function (f) { var sh = out.addPage([W, H]); poser(sh, f[0] >= 0 ? emb[f[0]] : null, cel[0]); poser(sh, f[1] >= 0 ? emb[f[1]] : null, cel[1]); });
            } else if (mode.value === '4') {
              var c4 = grille(F[0], F[1], 2, 2, mg, gt);
              for (var j = 0; j < n; j += 4) { var s4 = out.addPage(F); for (var q = 0; q < 4; q++) poser(s4, emb[j + q], c4[q]); }
            } else {
              var e = emb[0], r = maxRepetition(F[0], F[1], e.width, e.height, mg, gt);
              if (!r.nx || !r.ny) throw new Error('La page ne tient pas sur cette feuille.');
              var sr = out.addPage(F), pw = r.tourne ? e.height : e.width, ph = r.tourne ? e.width : e.height;
              for (var yy = 0; yy < r.ny; yy++) for (var xx = 0; xx < r.nx; xx++) {
                var cx = mg + xx * (pw + gt), cy = F[1] - mg - (yy + 1) * ph - yy * gt;
                if (r.tourne) sr.drawPage(e, { x: cx + pw, y: cy, width: e.width, height: e.height, rotate: L.degrees(90) });
                else poser(sr, e, { x: cx, y: cy, w: pw, h: ph });
              }
              var np = r.nx * r.ny;
              api.toast(np + (np > 1 ? ' poses' : ' pose') + ' sur la feuille' + (r.tourne ? (np > 1 ? ' (pivotées)' : ' (pivotée)') : '') + '.', 'info');
            }
            api.telecharger(await out.save(), api.nomBase() + '-impose.pdf');
            api.toast('Imposition téléchargée.', 'success');
          } catch (e2) { api.toast(api.msgErreur(e2), 'danger'); }
          finally { api.liberer(); }
        } }
      ], { cle: 'imposition' });
    }
    EXT.actions.imposition = { fn: panneauImposition }; EXT.panneaux.imposition = panneauImposition;

    /* ── Aplatir ──────────────────────────────────────────────────────── */
    function panneauAplatir() {
      var s = S(), a = s.aplatirTout || {}, corps = el('div');
      var ch = coche('Champs de formulaire (existants et créés) : figés dans la page', a.champs);
      var im = coche('Pages en image : aplatit annotations, calques et transparence', a.images);
      var dpi = choix([['150', '150 dpi'], ['200', '200 dpi'], ['300', '300 dpi']], String(a.dpi || 300));
      corps.appendChild(ch); corps.appendChild(im); corps.appendChild(api.champ('Résolution des pages en image', dpi));
      corps.appendChild(el('p', 'tpdf-aide', 'Appliqué à chaque enregistrement tant que coché. Pages en image : texte non sélectionnable.'));
      api.ouvrirModale('Aplatir', corps, [{ txt: 'Valider', plein: true, fn: function () {
        s.aplatirTout = { champs: ch.input.checked, images: im.input.checked, dpi: parseInt(dpi.value, 10) };
        if (ch.input.checked) s.aplatir = true;
        api.fermerModale(); api.toast('Réglage d\'aplatissement enregistré.', 'success');
      } }], { cle: 'aplatir' });
    }
    EXT.actions.aplatir = { fn: panneauAplatir }; EXT.panneaux.aplatir = panneauAplatir;
    EXT.hooks.exportDernier = (EXT.hooks.exportDernier || []).concat(async function (ctx) {
      var a = S().aplatirTout; if (!a) return;
      var doc = ctx.final || ctx.out;
      if (a.champs) { try { doc.getForm().flatten({ updateFieldAppearances: false }); } catch (e) { /* aucun champ */ } }
      if (a.images) {
        var b = await doc.save(ctx.optionsSave || {});
        var r = await api.rasteriser(b, a.dpi || 300, 0.92);
        ctx.final = await ctx.L.PDFDocument.load(r);
        ctx.optionsSave = {};
      }
    });
  });
})();
