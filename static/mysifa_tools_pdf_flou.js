/*
 * MyTools — éditeur PDF : flouter une information (nom, adresse, prix…).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Sécurité : un rectangle flou posé par-dessus laisserait le texte d'origine
 * extractible. À l'export, toute page qui porte une zone de floutage est donc
 * rendue en image (pdf.js), l'effet est appliqué AUX PIXELS, et la page est
 * reconstruite dans un document neuf qui ne recopie que les autres pages
 * (copyPages ne recopie que les objets référencés : l'ancien flux de contenu
 * de la page floutée n'y est pas).
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // Zone en points -> rectangle de pixels entier, borné à l'image (null si vide).
  function zonePixels(a, k, W, H) {
    var x0 = Math.max(0, Math.floor(a.x * k)), y0 = Math.max(0, Math.floor(a.y * k));
    var x1 = Math.min(W, Math.ceil((a.x + a.w) * k)), y1 = Math.min(H, Math.ceil((a.y + a.h) * k));
    return x1 > x0 && y1 > y0 ? { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } : null;
  }
  // Pixelisation : chaque bloc prend la couleur moyenne de ses pixels.
  function pixeliser(d, W, H, r, bloc) {
    var b = Math.max(1, Math.round(bloc));
    for (var by = r.y; by < r.y + r.h; by += b) {
      for (var bx = r.x; bx < r.x + r.w; bx += b) {
        var ex = Math.min(bx + b, r.x + r.w), ey = Math.min(by + b, r.y + r.h), s = [0, 0, 0], n = 0, x, y, i;
        for (y = by; y < ey; y++) for (x = bx; x < ex; x++) { i = (y * W + x) * 4; s[0] += d[i]; s[1] += d[i + 1]; s[2] += d[i + 2]; n++; }
        for (y = by; y < ey; y++) for (x = bx; x < ex; x++) { i = (y * W + x) * 4; d[i] = s[0] / n; d[i + 1] = s[1] / n; d[i + 2] = s[2] / n; d[i + 3] = 255; }
      }
    }
  }
  // Flou : trois passes de flou boîte séparable (≈ gaussien), sur la zone
  // élargie de la portée du flou pour l'échantillonnage, écrit dans la zone seule.
  function flouter(d, W, H, r, rayon, passes) {
    var R = Math.max(1, Math.round(rayon)), np = passes || 3, m = R * np;
    var x0 = Math.max(0, r.x - m), y0 = Math.max(0, r.y - m), x1 = Math.min(W, r.x + r.w + m), y1 = Math.min(H, r.y + r.h + m);
    var w = x1 - x0, h = y1 - y0, a = new Float32Array(w * h * 3), b = new Float32Array(w * h * 3), x, y, c, i;
    for (y = 0; y < h; y++) for (x = 0; x < w; x++) { i = ((y0 + y) * W + x0 + x) * 4; for (c = 0; c < 3; c++) a[(y * w + x) * 3 + c] = d[i + c]; }
    var div = 2 * R + 1;
    function cl(v, n) { return v < 0 ? 0 : v >= n ? n - 1 : v; }
    for (var p = 0; p < np; p++) {
      for (y = 0; y < h; y++) for (c = 0; c < 3; c++) {
        var s = 0, base = y * w;
        for (x = -R; x <= R; x++) s += a[(base + cl(x, w)) * 3 + c];
        for (x = 0; x < w; x++) {
          b[(base + x) * 3 + c] = s / div;
          s += a[(base + cl(x + R + 1, w)) * 3 + c] - a[(base + cl(x - R, w)) * 3 + c];
        }
      }
      for (x = 0; x < w; x++) for (c = 0; c < 3; c++) {
        var t = 0;
        for (y = -R; y <= R; y++) t += b[(cl(y, h) * w + x) * 3 + c];
        for (y = 0; y < h; y++) {
          a[(y * w + x) * 3 + c] = t / div;
          t += b[(cl(y + R + 1, h) * w + x) * 3 + c] - b[(cl(y - R, h) * w + x) * 3 + c];
        }
      }
    }
    for (y = r.y; y < r.y + r.h; y++) for (x = r.x; x < r.x + r.w; x++) {
      i = (y * W + x) * 4; var j = ((y - y0) * w + x - x0) * 3;
      d[i] = a[j]; d[i + 1] = a[j + 1]; d[i + 2] = a[j + 2]; d[i + 3] = 255;
    }
  }
  function masquer(d, W, H, r, rgb) {
    for (var y = r.y; y < r.y + r.h; y++) for (var x = r.x; x < r.x + r.w; x++) {
      var i = (y * W + x) * 4; d[i] = rgb[0]; d[i + 1] = rgb[1]; d[i + 2] = rgb[2]; d[i + 3] = 255;
    }
  }
  // Applique l'effet d'une zone ; k = pixels par point.
  function appliquer(d, W, H, a, k) {
    var r = zonePixels(a, k, W, H); if (!r) return null;
    if (a.effet === 'pixeliser') pixeliser(d, W, H, r, (a.bloc || 8) * k);
    else if (a.effet === 'masquer') masquer(d, W, H, r, a.masque === 'blanc' ? [255, 255, 255] : [0, 0, 0]);
    else flouter(d, W, H, r, (a.rayon || 8) * k / 3, 3);
    return r;
  }
  function normaliser(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  // Boîte (affichée, page pivotée de R) d'un morceau d'élément de texte pdf.js :
  // caractères [k, k+n) d'une chaîne de longueur len.
  function boiteTexte(tr, largeur, k, n, len, view, R, versVue) {
    var h = Math.abs(tr[3]) || Math.hypot(tr[2], tr[3]) || 10, L = len || 1;
    var X0 = tr[4] + largeur * k / L, X1 = tr[4] + largeur * (k + n) / L;
    var a = versVue(view, R, X0 - 1, tr[5] - h * 0.28), b = versVue(view, R, X1 + 1, tr[5] + h * 0.95);
    return { x: Math.min(a[0], b[0]), y: Math.min(a[1], b[1]), w: Math.abs(b[0] - a[0]), h: Math.abs(b[1] - a[1]) };
  }

  M._interne = M._interne || {};
  M._interne.flou = { zonePixels: zonePixels, pixeliser: pixeliser, flouter: flouter, masquer: masquer, appliquer: appliquer, boiteTexte: boiteTexte, normaliser: normaliser };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    var AVERT = 'Les pages floutées sont enregistrées en image : le texte caché est réellement supprimé, et le reste de la page n\'est plus sélectionnable.';
    var EFFETS = [['flou', 'Flou'], ['pixeliser', 'Pixeliser'], ['masquer', 'Masquer']];

    api.IC.flou = '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="M7 9h2.5v2.5H7zM12 9h2.5v2.5H12zM9.5 11.5H12V14H9.5zM14.5 11.5H17V14h-2.5zM7 14h2.5v1.5H7z"/>';
    api.LIBELLES.flou = 'Floutage';
    api.AIDE_OUTIL.flou = 'Cliquer-glisser sur l\'information à cacher, ou cliquer un texte pour l\'entourer exactement.';
    api.BULLES.flou = 'Flouter';
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('flou', 'flou', 'Flouter une information') });

    function st() { var s = S().style; return { effet: s.effet || 'flou', rayon: s.rayon || 8, bloc: s.bloc || 8, masque: s.masque || 'noir', dpi: s.flouDpi || 200 }; }

    /* ── Texte de la page (cliquer un texte = zone ajustée) ───────────── */
    function textes(src, idx) {
      src._txf = src._txf || {};
      if (!src._txf[idx]) {
        src._txf[idx] = src.pdf.getPage(idx + 1).then(function (pg) { return pg.getTextContent(); })
          .then(function (tc) { return tc.items.filter(function (it) { return it.str && it.str.trim() && it.transform[0] > 0 && Math.abs(it.transform[1]) < 1e-3; }); })
          .catch(function () { return []; });
        src._txf[idx].then(function (l) { src._txfPret = src._txfPret || {}; src._txfPret[idx] = l; });
      }
      return src._txf[idx];
    }
    function precharger() {
      var s = S(), p = api.pageCourante();
      if (s && p && s.outil === 'flou') textes(s.sources[p.src], p.idx);
    }
    function texteSous(p, pt) {
      var s = S(), src = s.sources[p.src], l = src._txfPret && src._txfPret[p.idx];
      if (!l) return null;
      var d = api.dims(p);
      for (var i = 0; i < l.length; i++) {
        var it = l[i], b = boiteTexte(it.transform, it.width, 0, it.str.length, it.str.length, d.meta.view, d.R, api.versVue);
        if (pt.x >= b.x && pt.x <= b.x + b.w && pt.y >= b.y && pt.y <= b.y + b.h) return b;
      }
      return null;
    }

    /* ── Outil et type d'annotation ───────────────────────────────────── */
    EXT.outils.flou = {
      down: function (pt, p, ev) {
        if (ev && ev.detail >= 2) return true; // second clic d'un double-clic : la zone est déjà posée
        var o = st();
        return { t: 'flou', effet: o.effet, rayon: o.rayon, bloc: o.bloc, masque: o.masque, x: pt.x, y: pt.y, w: 0, h: 0 };
      },
      props: function (sec) { propsFlou(sec, null); }
    };
    EXT.types.flou = {
      boiteTournante: true,
      tailleDefaut: function (a) {
        var b = texteSous(api.pageCourante(), { x: a.x, y: a.y });
        if (b) { a._cible = b; return [b.w, b.h]; }
        a._centrer = 1; return [140, 24];
      },
      apresCreation: function (a) {
        if (a._cible) { a.x = a._cible.x; a.y = a._cible.y; a.w = a._cible.w; a.h = a._cible.h; }
        else if (a._centrer) { a.x -= 70; a.y -= 12; }
        delete a._cible; delete a._centrer;
      },
      dessiner: function (a, g) {
        var url = apercu(a);
        if (url) api.sv('image', { x: a.x, y: a.y, width: a.w, height: a.h, href: url, preserveAspectRatio: 'none' }, g);
        else api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, 'class': 'tpdf-flou-attente' }, g);
        api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: 'transparent', 'class': 'tpdf-flou-cadre' }, g);
      },
      props: function (sec, a) { propsFlou(sec, a); },
      exporter: async function () { /* rien en vectoriel : la page entière passe en image (exportFinal) */ }
    };

    // Aperçu fidèle : l'effet est calculé sur les pixels du rendu affiché,
    // à la même échelle (points -> pixels) que l'export.
    function apercu(a) {
      var s = S(), p = api.pageCourante(), cv = s && s.feuille.querySelector('canvas');
      if (!cv || !p) return null;
      var d = api.dims(p), k = cv.width / d.w, r = zonePixels(a, k, cv.width, cv.height);
      if (!r) return null;
      var cle = [r.x, r.y, r.w, r.h, a.effet, a.rayon, a.bloc, a.masque].join(':');
      cv._flou = cv._flou || {};
      if (cv._flou[cle]) return cv._flou[cle];
      var marge = Math.ceil((a.rayon || 8) * k) + 2;
      var ex = { x: Math.max(0, r.x - marge), y: Math.max(0, r.y - marge) };
      ex.w = Math.min(cv.width, r.x + r.w + marge) - ex.x; ex.h = Math.min(cv.height, r.y + r.h + marge) - ex.y;
      var img = cv.getContext('2d').getImageData(ex.x, ex.y, ex.w, ex.h);
      var loc = { x: (r.x - ex.x) / k, y: (r.y - ex.y) / k, w: r.w / k, h: r.h / k };
      appliquer(img.data, ex.w, ex.h, { x: loc.x, y: loc.y, w: loc.w, h: loc.h, effet: a.effet, rayon: a.rayon, bloc: a.bloc, masque: a.masque }, k);
      var t = document.createElement('canvas'); t.width = r.w; t.height = r.h;
      t.getContext('2d').putImageData(img, ex.x - r.x, ex.y - r.y);
      var url = t.toDataURL('image/png');
      var cles = Object.keys(cv._flou); if (cles.length > 40) delete cv._flou[cles[0]];
      cv._flou[cle] = url;
      return url;
    }

    /* ── Crochets ─────────────────────────────────────────────────────── */
    function aFlou(p) { return p.annots.some(function (a) { return a.t === 'flou'; }); }
    EXT.hooks.rendu = (EXT.hooks.rendu || []).concat(function (p) { if (aFlou(p)) api.dessinerCalque(); });
    EXT.hooks.page = (EXT.hooks.page || []).concat(precharger);
    EXT.hooks.barre = (EXT.hooks.barre || []).concat(precharger);
    EXT.hooks.vignette = (EXT.hooks.vignette || []).concat(function (p, v) { pastille(v, aFlou(p)); });
    function pastille(v, oui) {
      var pied = v && v.querySelector('.tpdf-vig-pied'); if (!pied) return;
      var e = pied.querySelector('.tpdf-vig-flou');
      if (!oui) { if (e) e.remove(); return; }
      if (e) return;
      e = document.createElement('span'); e.className = 'tpdf-vig-flou'; e.setAttribute('data-bulle', 'Floutée');
      e.innerHTML = api.ico('flou', 12);
      pied.appendChild(e);
    }
    // Aperçu cohérent : un contrôle de formulaire sous une zone floutée est masqué,
    // sinon sa valeur s'afficherait par-dessus le flou.
    EXT.hooks.calque = (EXT.hooks.calque || []).concat(function (p) {
      var s = S(), z = s.zoomCourant || 1, zones = p.annots.filter(function (a) { return a.t === 'flou'; });
      s.html.querySelectorAll('.tpdf-fc').forEach(function (e) {
        var x = parseFloat(e.style.left) / z, y = parseFloat(e.style.top) / z, w = parseFloat(e.style.width) / z, h = parseFloat(e.style.height) / z;
        var dessous = zones.some(function (a) { return x < a.x + a.w && x + w > a.x && y < a.y + a.h && y + h > a.y; });
        e.style.visibility = dessous ? 'hidden' : '';
      });
      pastille(s.vig.querySelector('[data-uid="' + p.uid + '"]'), zones.length > 0);
    });

    /* ── Rechercher et flouter ────────────────────────────────────────── */
    async function rechercherEtFlouter(q) {
      var s = S(), qn = normaliser(q).trim(), o = st();
      if (!qn) { api.toast('Saisir le texte à flouter.', 'danger'); return 0; }
      var avant = api.snapshot(), n = 0, pages = {};
      for (var i = 0; i < s.pages.length; i++) {
        var p = s.pages[i], src = s.sources[p.src], items = await textes(src, p.idx), d = api.dims(p);
        items.forEach(function (it) {
          var t = normaliser(it.str), k = t.indexOf(qn);
          while (k >= 0) {
            var b = boiteTexte(it.transform, it.width, k, qn.length, t.length, d.meta.view, d.R, api.versVue);
            p.annots.push({ id: api.nid('n'), t: 'flou', effet: o.effet, rayon: o.rayon, bloc: o.bloc, masque: o.masque, x: b.x, y: b.y, w: b.w, h: b.h });
            n++; pages[p.uid] = 1;
            k = t.indexOf(qn, k + qn.length);
          }
        });
      }
      if (n) {
        api.pushHist(avant);
        api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre();
        var np = Object.keys(pages).length;
        api.toast(n + ' zone' + (n > 1 ? 's posées' : ' posée') + ' sur ' + np + ' page' + (np > 1 ? 's' : '') + '.', 'success');
      } else api.toast('Aucun résultat pour « ' + q + ' ».', 'info');
      return n;
    }

    /* ── Panneau ──────────────────────────────────────────────────────── */
    function propsFlou(sec, a) {
      var s = S(), o = a || st();
      var seg = document.createElement('div'); seg.className = 'tpdf-seg';
      EFFETS.forEach(function (x) {
        var b = document.createElement('button'); b.type = 'button'; b.className = 'tpdf-btn' + (o.effet === x[0] ? ' tpdf-actif' : '');
        b.textContent = x[1];
        b.addEventListener('click', function () { api.majProp('effet', x[0], a); api.validerProp(); api.rendreProps(); });
        seg.appendChild(b);
      });
      sec.appendChild(api.champ('Effet', seg));
      if (o.effet === 'masquer') {
        var sm = document.createElement('div'); sm.className = 'tpdf-seg';
        [['noir', 'Noir'], ['blanc', 'Blanc']].forEach(function (x) {
          var b = document.createElement('button'); b.type = 'button'; b.className = 'tpdf-btn' + ((o.masque || 'noir') === x[0] ? ' tpdf-actif' : '');
          b.textContent = x[1];
          b.addEventListener('click', function () { api.majProp('masque', x[0], a); api.validerProp(); api.rendreProps(); });
          sm.appendChild(b);
        });
        sec.appendChild(api.champ('Couleur', sm));
      } else {
        var cle = o.effet === 'pixeliser' ? 'bloc' : 'rayon';
        var rg = document.createElement('input'); rg.type = 'range'; rg.min = 3; rg.max = 24; rg.step = 1; rg.value = o[cle] || 8;
        rg.addEventListener('input', function () { api.majProp(cle, parseFloat(rg.value), a); });
        rg.addEventListener('change', api.validerProp);
        sec.appendChild(api.champ(o.effet === 'pixeliser' ? 'Taille des blocs' : 'Intensité du flou', rg));
      }
      var dp = document.createElement('select'); dp.className = 'tpdf-champ';
      [150, 200, 300].forEach(function (v) { var op = document.createElement('option'); op.value = v; op.textContent = v + ' dpi'; dp.appendChild(op); });
      dp.value = String(st().dpi);
      dp.addEventListener('change', function () { s.style.flouDpi = parseInt(dp.value, 10); });
      sec.appendChild(api.champ('Résolution des pages floutées', dp));
      var av = document.createElement('p'); av.className = 'tpdf-aide tpdf-avert'; av.textContent = AVERT;
      sec.appendChild(av);
      if (a) return;
      var lab = document.createElement('div'); lab.className = 'tpdf-ligne';
      var q = document.createElement('input'); q.type = 'search'; q.className = 'tpdf-champ'; q.placeholder = 'Mot, nom, numéro…';
      q.setAttribute('aria-label', 'Texte à flouter dans tout le document');
      var go = document.createElement('button'); go.type = 'button'; go.className = 'tpdf-b'; go.textContent = 'Flouter partout';
      go.setAttribute('data-bulle', 'Partout');
      var res = document.createElement('p'); res.className = 'tpdf-aide';
      async function lancer() {
        go.disabled = true;
        try { var n = await rechercherEtFlouter(q.value); res.textContent = n ? n + ' zone' + (n > 1 ? 's posées.' : ' posée.') : 'Aucune occurrence.'; }
        finally { go.disabled = false; }
      }
      go.addEventListener('click', lancer);
      q.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); lancer(); } });
      lab.appendChild(q); lab.appendChild(go);
      sec.appendChild(api.champ('Rechercher et flouter', lab));
      sec.appendChild(res);
    }

    /* ── Export : pages floutées refaites en image ────────────────────── */
    EXT.hooks.exportFinal = (EXT.hooks.exportFinal || []).concat(async function (ctx) {
      var idx = {}, n = ctx.pages.length, nb = 0;
      ctx.pages.forEach(function (p, i) { if (aFlou(p)) { idx[i] = p; nb++; } });
      if (!nb) return;
      var L = ctx.L, dpi = st().dpi, k = dpi / 72;
      var octets = await ctx.out.save(ctx.optionsSave || {});
      var pj = await api.pdfjs();
      var doc = await pj.getDocument({ data: octets.slice(), isEvalSupported: false }).promise;
      var tmp = await L.PDFDocument.load(octets, { updateMetadata: false });
      var fin = await L.PDFDocument.create();
      var garder = []; for (var g = 0; g < n; g++) if (!idx[g]) garder.push(g);
      var copies = garder.length ? await fin.copyPages(tmp, garder) : [];
      try {
        for (var i = 0; i < n; i++) {
          if (!idx[i]) { fin.addPage(copies.shift()); continue; }
          var pg = await doc.getPage(i + 1);
          var vp1 = pg.getViewport({ scale: 1 }), vp = pg.getViewport({ scale: k });
          var cv = document.createElement('canvas'); cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
          var c = cv.getContext('2d', { willReadFrequently: true });
          c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
          // intent « print » : champs dessinés dans l'image, pas de requestAnimationFrame.
          await pg.render({ canvasContext: c, viewport: vp, intent: 'print' }).promise;
          var kx = cv.width / vp1.width;
          var data = c.getImageData(0, 0, cv.width, cv.height);
          idx[i].annots.forEach(function (a) { if (a.t === 'flou') appliquer(data.data, cv.width, cv.height, a, kx); });
          c.putImageData(data, 0, 0);
          var blob = await new Promise(function (ok) { cv.toBlob(ok, 'image/jpeg', 0.92); });
          var img = await fin.embedJpg(new Uint8Array(await blob.arrayBuffer()));
          var np = fin.addPage([vp1.width, vp1.height]);
          np.drawImage(img, { x: 0, y: 0, width: vp1.width, height: vp1.height });
          cv.width = cv.height = 0;
        }
      } finally { try { doc.destroy(); } catch (e) { /* déjà libéré */ } }
      if (EXT.reconstruireFormulaire) EXT.reconstruireFormulaire(fin, L);
      ctx.final = fin;
    });
  });
})();
