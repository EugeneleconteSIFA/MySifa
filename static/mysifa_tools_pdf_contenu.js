/*
 * MyTools — éditeur PDF : contenu du document.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   remplacer une image (même place, même taille) ; extraire les images ;
 *   extraire un tableau de la page en CSV ou Excel ; pièces jointes (joindre,
 *   lister, extraire) ; PDF/A (vérification indicative, conversion serveur
 *   par ghostscript) ; accessibilité (titre, langue, textes alternatifs,
 *   contrôle du balisage).
 *
 * Limites : l'image remplacée est recouverte par la nouvelle, pas retirée du
 * fichier ; pdf-lib ne sait pas baliser un PDF (structure, ordre de lecture) —
 * l'éditeur pose titre et langue, garde les textes alternatifs et dit ce qui
 * manque, sans prétendre à la conformité PDF/UA.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests) ──────────────────────────────────────── */
  // Éléments de texte (x, y = ligne de base en points PDF, w, h, str) -> lignes de cellules.
  function tableauDepuisItems(items) {
    var l = items.filter(function (i) { return i.str && i.str.trim(); }).map(function (i) { return { x: i.x, y: i.y, w: i.w, h: i.h || 10, s: i.str.trim() }; });
    if (!l.length) return [];
    l.sort(function (a, b) { return b.y - a.y || a.x - b.x; });
    var lignes = [], cur = null;
    l.forEach(function (i) {
      if (cur && Math.abs(cur.y - i.y) <= Math.max(cur.h, i.h) * 0.5) cur.items.push(i);
      else { cur = { y: i.y, h: i.h, items: [i] }; lignes.push(cur); }
    });
    // Cellules : mots d'une même ligne séparés de moins d'un corps.
    lignes.forEach(function (r) {
      r.items.sort(function (a, b) { return a.x - b.x; });
      r.cells = [];
      r.items.forEach(function (i) {
        var d = r.cells[r.cells.length - 1];
        if (d && i.x - (d.x + d.w) < Math.max(i.h, d.h) * 1.0) { d.s += ' ' + i.s; d.w = i.x + i.w - d.x; }
        else r.cells.push({ x: i.x, w: i.w, h: i.h, s: i.s });
      });
    });
    // Colonnes : débuts de cellules regroupés (tolérance 8 pt).
    var debuts = [];
    lignes.forEach(function (r) { r.cells.forEach(function (c) { debuts.push(c.x); }); });
    debuts.sort(function (a, b) { return a - b; });
    var cols = [];
    debuts.forEach(function (x) { var d = cols[cols.length - 1]; if (d != null && x - d.max <= 8) { d.max = x; } else cols.push({ min: x, max: x }); });
    return lignes.map(function (r) {
      var out = cols.map(function () { return ''; });
      r.cells.forEach(function (c) {
        var k = 0, best = Infinity;
        cols.forEach(function (col, j) { var dd = c.x < col.min ? col.min - c.x : c.x > col.max ? c.x - col.max : 0; if (dd < best) { best = dd; k = j; } });
        out[k] = out[k] ? out[k] + ' ' + c.s : c.s;
      });
      return out;
    });
  }
  // Boîte (espace PDF) d'une image peinte avec la matrice m (carré unité).
  function boiteImage(m) {
    var pts = [[m[4], m[5]], [m[0] + m[4], m[1] + m[5]], [m[2] + m[4], m[3] + m[5]], [m[0] + m[2] + m[4], m[1] + m[3] + m[5]]];
    var xs = pts.map(function (p) { return p[0]; }), ys = pts.map(function (p) { return p[1]; });
    return [Math.min.apply(null, xs), Math.min.apply(null, ys), Math.max.apply(null, xs), Math.max.apply(null, ys)];
  }

  M._interne = M._interne || {};
  M._interne.contenu = { tableauDepuisItems: tableauDepuisItems, boiteImage: boiteImage };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function bouton(t, cls, bulle) { var b = el('button', 'tpdf-b' + (cls ? ' ' + cls : ''), t); b.type = 'button'; b.setAttribute('data-bulle', bulle || t); return b; }
    function telechargerBlob(blob, nom) { var u = api.urlObjet(blob), a = el('a'); a.href = u; a.download = nom; a.style.display = 'none'; S().el.appendChild(a); a.click(); a.remove(); }
    function choisirFichiers(accept, multiple) {
      return new Promise(function (ok) {
        var i = el('input'); i.type = 'file'; i.accept = accept || ''; i.multiple = !!multiple; i.hidden = true; S().el.appendChild(i);
        i.addEventListener('change', function () { ok(Array.prototype.slice.call(i.files || [])); i.remove(); }); i.click();
      });
    }

    Object.assign(api.IC, {
      remplacerImage: '<rect x="3.5" y="5" width="12" height="10" rx="1.5"/><path d="M5 13.5l3-3 2.5 2 2-1.5 2.5 2.5"/><path d="M17.5 11v8.5M14.5 16.5l3 3 3-3"/>',
      extraireImages: '<rect x="3.5" y="4" width="14" height="11" rx="1.5"/><path d="M5 13l3.5-3 3 2.5 2-1.5 3 2.5"/><path d="M19.5 9v11M16.5 17l3 3 3-3"/>',
      tableauCsv: '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M3.5 14.5h17M9.5 4.5v15M15 4.5v15"/>',
      trombone: '<path d="M8 12.5l6.5-6.5a3 3 0 0 1 4.2 4.2l-8 8a5 5 0 0 1-7-7l7.5-7.5"/>',
      pdfa: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M9 16l1.5-4.5L12 16M9.5 14.5h2M14 12v4"/>',
      acces: '<circle cx="12" cy="5" r="1.8"/><path d="M5 9l7 1.5L19 9M12 10.5V15l-3 5M12 15l3 5"/>'
    });
    api.LIBELLES.remplacerImage = 'Remplacer une image';
    api.AIDE_OUTIL.remplacerImage = 'Cliquer sur l\'image à remplacer, puis choisir la nouvelle.';
    var mp = EXT.menus.pages || (EXT.menus.pages = { libelle: 'Pages', icone: 'pages', ordre: 1, items: [] });
    mp.items.push({ separe: true },
      { act: 'remplacerImage', icone: 'remplacerImage', libelle: 'Remplacer une image', bulle: 'Remplacer', doc: 1 },
      { act: 'extraireImages', icone: 'extraireImages', libelle: 'Extraire les images', bulle: 'Images', doc: 1 },
      { act: 'tableauCsv', icone: 'tableauCsv', libelle: 'Extraire le tableau de la page…', bulle: 'Tableau', doc: 1 },
      { act: 'piecesJointes', icone: 'trombone', libelle: 'Pièces jointes…', bulle: 'Pièces', doc: 1 },
      { separe: true },
      { act: 'pdfa', icone: 'pdfa', libelle: 'PDF/A (archivage)…', bulle: 'PDF/A', doc: 1 },
      { act: 'accessibilite', icone: 'acces', libelle: 'Accessibilité…', bulle: 'Accessibilité', doc: 1 });

    /* ── Remplacer une image ──────────────────────────────────────────── */
    async function imagesDeLaPage(p) {
      var s = S(), src = s.sources[p.src], pg = await src.pdf.getPage(p.idx + 1), pj = await api.pdfjs(), O = pj.OPS;
      var ops = await pg.getOperatorList(), pile = [], m = [1, 0, 0, 1, 0, 0], l = [];
      function mul(a, b) { return [a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3], a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5]]; }
      for (var k = 0; k < ops.fnArray.length; k++) {
        var f = ops.fnArray[k];
        if (f === O.save) pile.push(m.slice());
        else if (f === O.restore) m = pile.pop() || [1, 0, 0, 1, 0, 0];
        else if (f === O.transform) m = mul(m, ops.argsArray[k]);
        else if (f === O.paintImageXObject || f === O.paintInlineImageXObject || f === O.paintImageMaskXObject) l.push(boiteImage(m));
      }
      return l;
    }
    EXT.actions.remplacerImage = { fn: function () { api.choisirOutil('remplacerImage'); } };
    EXT.outils.remplacerImage = {
      down: function (pt, p) {
        (async function () {
          var d = api.dims(p), X = api.versPdf(d.meta.view, d.R, pt.x, pt.y), boites = await imagesDeLaPage(p);
          var b = boites.filter(function (r) { return X[0] >= r[0] && X[0] <= r[2] && X[1] >= r[1] && X[1] <= r[3]; })
            .sort(function (u, v) { return (u[2] - u[0]) * (u[3] - u[1]) - (v[2] - v[0]) * (v[3] - v[1]); })[0];
          if (!b) { api.toast('Pas d\'image à cet endroit.', 'info'); return; }
          var f = (await choisirFichiers('image/png,image/jpeg'))[0]; if (!f) return;
          var id; try { id = await api.enregistrerImage(new Uint8Array(await f.arrayBuffer())); } catch (e) { api.toast(api.msgErreur(e), 'danger'); return; }
          var c1 = api.versVue(d.meta.view, d.R, b[0], b[1]), c2 = api.versVue(d.meta.view, d.R, b[2], b[3]);
          var avant = api.snapshot(), a = { id: api.nid('n'), t: 'image', img: id, x: Math.min(c1[0], c2[0]), y: Math.min(c1[1], c2[1]), w: Math.abs(c2[0] - c1[0]), h: Math.abs(c2[1] - c1[1]) };
          p.annots.push(a); S().annSel = a.id; api.pushHist(avant);
          api.choisirOutil('select', true); api.dessinerCalque(); api.majBadges();
          api.toast('Image remplacée à la même place et à la même taille. L\'ancienne est recouverte, pas retirée du fichier.', 'success');
        })().catch(function (e) { api.toast(api.msgErreur(e), 'danger'); });
        return true;
      }
    };

    /* ── Extraire les images ──────────────────────────────────────────── */
    EXT.actions.extraireImages = { fn: async function () {
      var s = S(), L = await api.pdflib(), N = L.PDFName, n = 0, vus = {};
      api.occuper('Extraction…');
      try {
        for (var i = 0; i < s.pages.length; i++) {
          var p = s.pages[i], doc = s.sources[p.src].lib, pg = doc.getPage(p.idx), res = pg.node.Resources();
          var xo = res && doc.context.lookup(res.get(N.of('XObject')));
          if (!(xo instanceof L.PDFDict)) continue;
          var refs = xo.keys().map(function (k) { return xo.get(k); });
          for (var k = 0; k < refs.length; k++) {
            var cle = p.src + ':' + refs[k].toString(); if (vus[cle]) continue; vus[cle] = 1;
            var o = doc.context.lookup(refs[k]); if (!o || !o.dict || String(o.dict.get(N.of('Subtype'))) !== '/Image' || o.dict.get(N.of('ImageMask'))) continue;
            var f = String(o.dict.get(N.of('Filter')) || ''), W = o.dict.get(N.of('Width')).asNumber(), H = o.dict.get(N.of('Height')).asNumber();
            var nom = api.nomBase() + '-p' + (i + 1) + '-' + (n + 1);
            if (f === '/DCTDecode') { telechargerBlob(new Blob([o.contents], { type: 'image/jpeg' }), nom + '.jpg'); n++; }
            else if (f === '/JPXDecode') { telechargerBlob(new Blob([o.contents], { type: 'image/jp2' }), nom + '.jp2'); n++; }
            else {
              var brut; try { brut = L.decodePDFRawStream(o).decode(); } catch (e) { continue; }
              var comp = brut.length >= W * H * 3 ? 3 : brut.length >= W * H ? 1 : 0; if (!comp) continue;
              var cv = el('canvas'); cv.width = W; cv.height = H; var c = cv.getContext('2d'), id = c.createImageData(W, H);
              for (var q = 0, j = 0; q < W * H; q++, j += comp) { id.data[q * 4] = brut[j]; id.data[q * 4 + 1] = brut[comp === 3 ? j + 1 : j]; id.data[q * 4 + 2] = brut[comp === 3 ? j + 2 : j]; id.data[q * 4 + 3] = 255; }
              c.putImageData(id, 0, 0);
              telechargerBlob(await new Promise(function (ok) { cv.toBlob(ok, 'image/png'); }), nom + '.png'); n++;
            }
            await new Promise(function (r) { setTimeout(r, 250); });
          }
        }
        api.toast(n ? n + ' image(s) extraite(s).' : 'Aucune image extractible dans ce document.', n ? 'success' : 'info');
      } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      finally { api.liberer(); }
    } };

    /* ── Tableau de la page ───────────────────────────────────────────── */
    async function panneauTableau() {
      var s = S(), p = api.pageCourante(), corps = el('div');
      var items = (await api.texteDe(p)).filter(function (it) { return it.transform && it.transform[0] > 0 && Math.abs(it.transform[1]) < 1e-3; })
        .map(function (it) { return { x: it.transform[4], y: it.transform[5], w: it.width, h: Math.abs(it.transform[3]) || 10, str: it.str }; });
      var lignes = tableauDepuisItems(items);
      if (!lignes.length) corps.appendChild(el('p', 'tpdf-aide', 'Pas de texte sur cette page (scan ?) : lancer l\'OCR d\'abord, ou IA › Extraire des données.'));
      else {
        var w = el('div', 'tpdf-ia-tablewrap'), t = el('table', 'tpdf-ia-table');
        lignes.slice(0, 200).forEach(function (r) { var tr = el('tr'); r.forEach(function (c) { tr.appendChild(el('td', null, c)); }); t.appendChild(tr); });
        w.appendChild(t); corps.appendChild(w);
        corps.appendChild(el('p', 'tpdf-aide', lignes.length + ' ligne(s), ' + lignes[0].length + ' colonne(s) reconstituées depuis la position du texte. Tableaux complexes (cellules fusionnées) : IA › Extraire des données.'));
      }
      var csvTxt = function () { return M._interne.revision.csv(lignes); };
      api.ouvrirModale('Tableau de la page ' + (s.cur + 1), corps, [
        { txt: 'CSV', bulle: 'CSV', fn: function () { if (lignes.length) telechargerBlob(new Blob([csvTxt()], { type: 'text/csv;charset=utf-8' }), api.nomBase() + '-p' + (s.cur + 1) + '.csv'); } },
        { txt: 'Excel', bulle: 'Excel', fn: async function () {
          if (!lignes.length) return;
          api.occuper('Conversion…');
          try {
            var fd = new FormData(); fd.append('cible', 'xlsx'); fd.append('options', '{}');
            fd.append('fichiers', new Blob([csvTxt()], { type: 'text/csv' }), api.nomBase() + '-p' + (s.cur + 1) + '.csv');
            var r = await fetch('/api/tools/convertir', { method: 'POST', body: fd, credentials: 'same-origin' });
            if (!r.ok) { var j = null; try { j = await r.json(); } catch (e) { j = null; } throw new Error((j && j.detail) || 'Conversion Excel indisponible.'); }
            telechargerBlob(await r.blob(), api.nomBase() + '-p' + (s.cur + 1) + '.xlsx');
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); } finally { api.liberer(); }
        } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'tableau', large: true });
    }
    EXT.actions.tableauCsv = { fn: panneauTableau }; EXT.panneaux.tableau = panneauTableau;

    /* ── Pièces jointes ───────────────────────────────────────────────── */
    async function jointesSources() {
      var s = S(), ids = {}, l = [];
      s.pages.forEach(function (p) { ids[p.src] = 1; });
      for (var id in ids) {
        var a = null; try { a = await s.sources[id].pdf.getAttachments(); } catch (e) { a = null; }
        Object.keys(a || {}).forEach(function (k) { l.push({ nom: a[k].filename || k, octets: a[k].content, source: s.sources[id].nom }); });
      }
      return l;
    }
    async function panneauJointes() {
      var s = S(); s.piecesJointes = s.piecesJointes || [];
      if (s.garderJointes == null) s.garderJointes = true;
      var corps = el('div'), zone = el('div', 'tpdf-lc'), origine = await jointesSources();
      corps.appendChild(zone);
      function dessiner() {
        zone.textContent = '';
        origine.forEach(function (j) {
          var it = el('div', 'tpdf-lc-item'); it.appendChild(el('span', 'tpdf-lc-nom', j.nom)); it.appendChild(el('span', 'tpdf-lc-type', 'Dans ' + j.source + ' · ' + api.tailleLisible(j.octets.length)));
          var b = bouton('Extraire', '', 'Extraire'); b.addEventListener('click', function () { telechargerBlob(new Blob([j.octets]), j.nom); });
          it.appendChild(b); zone.appendChild(it);
        });
        s.piecesJointes.forEach(function (j, i) {
          var it = el('div', 'tpdf-lc-item'); it.appendChild(el('span', 'tpdf-lc-nom', j.nom)); it.appendChild(el('span', 'tpdf-lc-type', 'Ajoutée · ' + api.tailleLisible(j.octets.length)));
          var b = bouton('Retirer', '', 'Retirer'); b.addEventListener('click', function () { s.piecesJointes.splice(i, 1); dessiner(); });
          it.appendChild(b); zone.appendChild(it);
        });
        if (!origine.length && !s.piecesJointes.length) zone.appendChild(el('p', 'tpdf-aide', 'Aucune pièce jointe.'));
      }
      dessiner();
      var g = el('label', 'tpdf-case'), gi = el('input'); gi.type = 'checkbox'; gi.checked = s.garderJointes; gi.addEventListener('change', function () { s.garderJointes = gi.checked; });
      g.appendChild(gi); g.appendChild(document.createTextNode(' Garder les pièces jointes d\'origine à l\'enregistrement'));
      corps.appendChild(g);
      api.ouvrirModale('Pièces jointes', corps, [
        { txt: 'Joindre un fichier', bulle: 'Joindre', fn: async function () {
          var f = await choisirFichiers('', true);
          for (var k = 0; k < f.length; k++) {
            if (f[k].size > 25 * 1024 * 1024) { api.toast('« ' + f[k].name + ' » trop lourd — 25 Mo au plus.', 'danger'); continue; }
            s.piecesJointes.push({ nom: f[k].name, mime: f[k].type || 'application/octet-stream', octets: new Uint8Array(await f[k].arrayBuffer()) });
          }
          dessiner();
        } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'jointes' });
    }
    EXT.actions.piecesJointes = { fn: panneauJointes }; EXT.panneaux.jointes = panneauJointes;
    EXT.hooks.exportApres = (EXT.hooks.exportApres || []).concat(async function (ctx) {
      var s = S(), doc = ctx.final || ctx.out, l = (s.piecesJointes || []).slice();
      if (s.garderJointes !== false) (await jointesSources()).forEach(function (j) { l.push({ nom: j.nom, octets: j.octets, mime: 'application/octet-stream' }); });
      for (var i = 0; i < l.length; i++) {
        try { await doc.attach(l[i].octets, l[i].nom, { mimeType: l[i].mime || 'application/octet-stream', description: l[i].nom }); } catch (e) { /* pièce ignorée */ }
      }
      // Accessibilité : titre et langue.
      var a = s.a11y;
      if (a && a.titre) doc.setTitle(a.titre, { showInWindowTitleBar: true });
      if (a && a.langue) doc.setLanguage(a.langue);
    });

    /* ── PDF/A ────────────────────────────────────────────────────────── */
    async function verifierPdfa(octets) {
      var L = await api.pdflib(), d = await L.PDFDocument.load(octets, { updateMetadata: false, ignoreEncryption: true }), N = L.PDFName, pb = [];
      if (d.isEncrypted) pb.push('Document chiffré (interdit en PDF/A).');
      var cat = d.catalog;
      if (!cat.get(N.of('Metadata'))) pb.push('Métadonnées XMP absentes.');
      if (!cat.get(N.of('OutputIntents'))) pb.push('Profil de sortie (OutputIntent) absent.');
      var noms = d.context.lookup(cat.get(N.of('Names')));
      if (noms instanceof L.PDFDict && noms.get(N.of('JavaScript'))) pb.push('JavaScript présent (interdit).');
      var polices = 0;
      d.context.enumerateIndirectObjects().forEach(function (x) {
        var o = x[1];
        if (!(o instanceof L.PDFDict) || String(o.get(N.of('Type'))) !== '/Font') return;
        var st = String(o.get(N.of('Subtype')));
        if (st === '/Type0' || st === '/Type3') return;
        var fd = d.context.lookup(o.get(N.of('FontDescriptor')));
        if (!(fd instanceof L.PDFDict) || !(fd.get(N.of('FontFile')) || fd.get(N.of('FontFile2')) || fd.get(N.of('FontFile3')))) polices++;
      });
      if (polices) pb.push(polices + ' police(s) non incorporée(s).');
      return pb;
    }
    function panneauPdfa() {
      var corps = el('div'), res = el('div', 'tpdf-lc');
      corps.appendChild(el('p', 'tpdf-aide', 'Vérification indicative des points bloquants les plus courants (pas un validateur certifié). La conversion PDF/A-2b se fait sur le serveur MySifa (ghostscript) : le PDF y est envoyé, rien n\'est conservé.'));
      corps.appendChild(res);
      async function afficher(octets, titre) {
        res.textContent = ''; res.appendChild(el('div', 'tpdf-lab', titre));
        var pb = await verifierPdfa(octets);
        if (!pb.length) res.appendChild(el('p', 'tpdf-resultat', 'Aucun point bloquant détecté.'));
        pb.forEach(function (x) { res.appendChild(el('div', 'tpdf-lc-item', x)); });
      }
      api.ouvrirModale('PDF/A (archivage)', corps, [
        { txt: 'Vérifier', fn: async function () { api.occuper('Vérification…'); try { await afficher(await api.construire(), 'Document actuel'); } catch (e) { api.toast(api.msgErreur(e), 'danger'); } finally { api.liberer(); } } },
        { txt: 'Convertir en PDF/A et télécharger', plein: true, fn: async function () {
          api.occuper('Conversion PDF/A…');
          try {
            var fd = new FormData(); fd.append('pdf', new Blob([await api.construire()], { type: 'application/pdf' }), api.nomBase() + '.pdf');
            var r = await fetch('/api/tools/pdf/pdfa', { method: 'POST', body: fd, credentials: 'same-origin' });
            if (!r.ok) { var j = null; try { j = await r.json(); } catch (e) { j = null; } throw new Error((j && j.detail) || 'Conversion PDF/A indisponible.'); }
            var b = new Uint8Array(await r.arrayBuffer());
            api.telecharger(b, api.nomBase() + '-pdfa.pdf');
            await afficher(b, 'Fichier converti');
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); } finally { api.liberer(); }
        } }
      ], { cle: 'pdfa' });
    }
    EXT.actions.pdfa = { fn: panneauPdfa }; EXT.panneaux.pdfa = panneauPdfa;

    /* ── Accessibilité ────────────────────────────────────────────────── */
    EXT.hooks.props = (EXT.hooks.props || []).concat(function (box) {
      var s = S(), a = api.trouverAnnot(s.annSel);
      if (!a || a.t !== 'image') return;
      var sec = api.section('Accessibilité'), t = el('textarea', 'tpdf-champ'); t.rows = 2; t.value = a.alt || ''; t.placeholder = 'Ce que montre l\'image, en une phrase';
      t.addEventListener('input', function () { api.majProp('alt', t.value, a); }); t.addEventListener('change', api.validerProp);
      sec.appendChild(api.champ('Texte alternatif', t)); box.appendChild(sec);
    });
    async function panneauAcces() {
      var s = S(); s.a11y = s.a11y || { titre: api.nomBase(), langue: 'fr-FR' };
      var corps = el('div'), titre = el('input', 'tpdf-champ'); titre.type = 'text'; titre.value = s.a11y.titre;
      var langue = el('select', 'tpdf-champ');
      [['fr-FR', 'Français'], ['en-GB', 'Anglais'], ['de-DE', 'Allemand'], ['es-ES', 'Espagnol'], ['it-IT', 'Italien'], ['nl-NL', 'Néerlandais']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; langue.appendChild(o); });
      langue.value = s.a11y.langue;
      corps.appendChild(api.champ('Titre du document', titre)); corps.appendChild(api.champ('Langue', langue));
      var rapport = el('div', 'tpdf-lc'); corps.appendChild(rapport);
      var balise = 0;
      for (var i = 0; i < s.pages.length && i < 30; i++) {
        var p = s.pages[i];
        try { var st = await (await s.sources[p.src].pdf.getPage(p.idx + 1)).getStructTree(); if (st && st.children && st.children.length) balise++; } catch (e) { /* pas de structure */ }
      }
      var sansAlt = 0; s.pages.forEach(function (p) { p.annots.forEach(function (a) { if (a.t === 'image' && !a.alt) sansAlt++; }); });
      [(balise ? 'Structure (balisage) présente sur ' + balise + ' page(s) d\'origine.' : 'Document non balisé : ordre de lecture et structure absents (l\'éditeur ne sait pas en créer).'),
        sansAlt ? sansAlt + ' image(s) ajoutée(s) sans texte alternatif (à saisir dans Propriétés).' : 'Images ajoutées : textes alternatifs saisis.',
        'Le balisage d\'origine n\'est pas recopié dans le document enregistré ; titre et langue y sont écrits.']
        .forEach(function (x) { rapport.appendChild(el('div', 'tpdf-lc-item', x)); });
      api.ouvrirModale('Accessibilité', corps, [{ txt: 'Valider', plein: true, fn: function () {
        s.a11y = { titre: titre.value.trim(), langue: langue.value }; api.fermerModale(); api.toast('Titre et langue écrits à l\'enregistrement.', 'success');
      } }], { cle: 'accessibilite' });
    }
    EXT.actions.accessibilite = { fn: panneauAcces }; EXT.panneaux.accessibilite = panneauAcces;
  });
})();
