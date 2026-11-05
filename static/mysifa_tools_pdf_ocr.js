/*
 * MyTools — éditeur PDF : OCR des scans (menu « Réviser »).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * tesseract.js (version figée, cdn jsdelivr) reconnaît le texte dans le
 * navigateur ; seuls le moteur et les dictionnaires fra + eng sont téléchargés,
 * l'image de la page ne quitte pas le poste. Les mots reconnus sont rangés sur
 * la page (p.ocr, repère de la page non pivotée) et écrits à l'enregistrement
 * en texte invisible (mode de rendu 3), aux bonnes positions : le PDF produit
 * devient cherchable et sélectionnable, son aspect ne change pas.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  var URL_TESSERACT = 'https://cdn.jsdelivr.net/npm/tesseract.js@7.0.0/dist/tesseract.min.js';
  var ECHELLE = 3; // 216 dpi

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // Mots de tesseract (pixels du rendu, échelle k) -> mots en points.
  function motsDepuisTesseract(data, k, confianceMin) {
    var l = [];
    function prendre(w) {
      var t = String(w.text || '').trim(), b = w.bbox;
      if (!t || !b || (w.confidence != null && w.confidence < (confianceMin || 30))) return;
      l.push({ t: t, x: b.x0 / k, y: b.y0 / k, w: (b.x1 - b.x0) / k, h: (b.y1 - b.y0) / k });
    }
    if (data && data.words && data.words.length) data.words.forEach(prendre);
    else (data && data.blocks || []).forEach(function (bk) {
      (bk.paragraphs || []).forEach(function (pa) { (pa.lines || []).forEach(function (li) { (li.words || []).forEach(prendre); }); });
    });
    return l;
  }
  // Échelle horizontale (Tz, %) pour qu'un mot écrit en `largeurPolice` occupe `largeur`.
  function echelleMot(largeur, largeurPolice) {
    if (!(largeurPolice > 0)) return 100;
    return Math.max(20, Math.min(500, 100 * largeur / largeurPolice));
  }

  M._interne = M._interne || {};
  M._interne.ocr = { motsDepuisTesseract: motsDepuisTesseract, echelleMot: echelleMot };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

    api.IC.ocr = '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/><path d="M8 9h8M8 12h8M8 15h5"/>';
    var menu = EXT.menus.reviser || (EXT.menus.reviser = { libelle: 'Réviser', icone: 'reviser', ordre: 2, items: [] });
    menu.items.push({ act: 'ocr', icone: 'ocr', libelle: 'Reconnaître le texte (OCR)…', bulle: 'OCR', doc: 1 });

    var _tess = null;
    function tesseract() {
      if (window.Tesseract) return Promise.resolve(window.Tesseract);
      if (!_tess) _tess = api.chargerScript(URL_TESSERACT).then(function () {
        if (!window.Tesseract) throw new Error('bibli'); return window.Tesseract;
      }, function (e) { _tess = null; throw e; });
      return _tess;
    }
    async function rendre(p) {
      var src = S().sources[p.src], pg = await src.pdf.getPage(p.idx + 1);
      var vpp = api.viewportPour(pg, p, ECHELLE, 0), cv = el('canvas');
      cv.width = Math.ceil(vpp.w); cv.height = Math.ceil(vpp.h);
      var c = cv.getContext('2d'); c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
      await pg.render({ canvasContext: c, viewport: vpp.vp, intent: 'print' }).promise;
      return cv;
    }
    async function sansTexte(p) { var it = await api.texteDe(p); return !it.some(function (x) { return x.str && x.str.trim(); }); }

    function panneauOcr() {
      var s = S(), corps = el('div');
      var cible = el('select', 'tpdf-champ');
      [['sans', 'Pages sans texte (scans)'], ['courante', 'Page courante'], ['toutes', 'Toutes les pages']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; cible.appendChild(o); });
      corps.appendChild(api.champ('Pages', cible));
      corps.appendChild(el('p', 'tpdf-aide', 'Langues : français et anglais. Reconnaissance faite sur ce poste ; seuls le moteur et les dictionnaires sont téléchargés (une fois). Le texte reconnu est ajouté, invisible, à l\'enregistrement : le PDF devient cherchable et sélectionnable.'));
      var res = el('div', 'tpdf-resultat'); corps.appendChild(res);
      var deja = s.pages.filter(function (p) { return p.ocr; }).length;
      if (deja) corps.appendChild(el('p', 'tpdf-aide', deja + ' page' + (deja > 1 ? 's ont' : ' a') + ' déjà une couche de texte reconnue : elle sera refaite.'));
      var m = api.ouvrirModale('Reconnaître le texte (OCR)', corps, [
        { txt: 'Retirer l\'OCR', fn: function () {
          var av = api.snapshot(), n = 0; s.pages.forEach(function (p) { if (p.ocr) { delete p.ocr; n++; } });
          if (n) { api.pushHist(av); api.rendreVignettes(); }
          api.toast(n ? 'Couche OCR retirée de ' + n + ' page' + (n > 1 ? 's.' : '.') : 'Aucune couche OCR.', 'info');
        } },
        { txt: 'Fermer', fn: api.fermerModale },
        { txt: 'Lancer l\'OCR', plein: true, cle: 'go', fn: async function () {
          var go = m.pied.querySelector('[data-cle="go"]'); go.disabled = true;
          var pages = cible.value === 'courante' ? [api.pageCourante()] : s.pages.slice();
          if (cible.value === 'sans') { var l = []; for (var i = 0; i < pages.length; i++) if (await sansTexte(pages[i])) l.push(pages[i]); pages = l; }
          if (!pages.length) { res.textContent = 'Aucune page à traiter : toutes ont déjà du texte.'; go.disabled = false; return; }
          var worker = null, avant = api.snapshot(), total = 0;
          api.occuper('OCR…');
          try {
            res.textContent = 'Chargement du moteur OCR…';
            var T = await tesseract();
            worker = await T.createWorker('fra+eng', 1, { logger: function (x) { if (x && x.status === 'recognizing text' && typeof x.progress === 'number') res.dataset.p = Math.round(x.progress * 100); } });
            for (var k = 0; k < pages.length; k++) {
              var p = pages[k];
              res.textContent = 'Page ' + (s.pages.indexOf(p) + 1) + ' (' + (k + 1) + ' / ' + pages.length + ')…';
              var cv = await rendre(p);
              var r = await worker.recognize(cv, {}, { blocks: true, text: true });
              var mots = motsDepuisTesseract(r.data, ECHELLE, 30);
              p.ocr = { mots: mots, langue: 'fra+eng' };
              total += mots.length;
              cv.width = cv.height = 0;
            }
            api.pushHist(avant); api.rendreVignettes();
            res.textContent = total + ' mot' + (total > 1 ? 's reconnus' : ' reconnu') + ' sur ' + pages.length + ' page' + (pages.length > 1 ? 's' : '') + '. Ils seront écrits à l\'enregistrement.';
            api.toast('OCR terminé — ' + total + ' mots.', 'success');
          } catch (e) { res.textContent = ''; api.toast(api.msgErreur(e), 'danger'); }
          finally {
            if (worker) { try { await worker.terminate(); } catch (e) { /* déjà arrêté */ } }
            api.liberer(); go.disabled = false;
          }
        } }
      ], { cle: 'ocr' });
    }
    // Pour les traitements par lot : reconnaît les pages données (p.ocr posé).
    EXT.ocr = { reconnaitre: async function (pages, progres) {
      var T = await tesseract(), w = await T.createWorker('fra+eng', 1, {}), total = 0;
      try {
        for (var k = 0; k < pages.length; k++) {
          if (progres) progres(k + 1, pages.length);
          var cv = await rendre(pages[k]), r = await w.recognize(cv, {}, { blocks: true, text: true });
          pages[k].ocr = { mots: motsDepuisTesseract(r.data, ECHELLE, 30), langue: 'fra+eng' }; total += pages[k].ocr.mots.length;
          cv.width = cv.height = 0;
        }
      } finally { try { await w.terminate(); } catch (e) { /* arrêté */ } }
      return total;
    }, sansTexte: sansTexte };
    EXT.actions.ocr = { fn: panneauOcr };
    EXT.panneaux.ocr = panneauOcr;

    // Texte invisible (Tr 3) mot par mot, échelle horizontale ajustée à la largeur reconnue.
    EXT.hooks.exportPage = (EXT.hooks.exportPage || []).concat(async function (pg, p, d, ctx) {
      if (!p.ocr || !p.ocr.mots || !p.ocr.mots.length) return;
      var L = ctx.L, v = d.meta.view;
      var font = await ctx.pol.police(p.ocr.mots.map(function (m) { return m.t; }).join(' '), {});
      p.ocr.mots.forEach(function (m) {
        var t = api.nettoyerTexte(font, m.t), taille = Math.max(2, m.h * 0.9), w = font.widthOfTextAtSize(t, taille);
        var q = api.versPdf(v, 0, m.x, m.y + m.h * 0.8);
        pg.pushOperators(L.pushGraphicsState(), L.setTextRenderingMode(L.TextRenderingMode.Invisible), L.setCharacterSqueeze(echelleMot(m.w, w)));
        pg.drawText(t, { x: q[0], y: q[1], size: taille, font: font });
        pg.pushOperators(L.popGraphicsState());
      });
    });
    EXT.hooks.vignette = (EXT.hooks.vignette || []).concat(function (p, v) {
      if (!p.ocr) return;
      var pied = v.querySelector('.tpdf-vig-pied'); if (!pied) return;
      var e = el('span', 'tpdf-vig-format', 'OCR'); e.setAttribute('data-bulle', 'Texte reconnu');
      pied.appendChild(e);
    });
  });
})();
