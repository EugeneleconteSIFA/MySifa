/*
 * MyTools — éditeur PDF : signets, liens, vue deux pages, défilement
 * synchronisé de deux PDF.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Les signets sont écrits à l'enregistrement en table des matières PDF
 * (/Outlines) ; les liens en annotations /Link (vers une page ou une adresse
 * web). Les liens déjà présents dans un fichier ouvert peuvent être retirés
 * ou repris en lien modifiable.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests) ──────────────────────────────────────── */
  // Titres : blocs dont le corps dépasse nettement le corps courant du document.
  function titresDepuisBlocs(blocsParPage) {
    var tailles = [];
    blocsParPage.forEach(function (l) { l.forEach(function (b) { tailles.push(Math.round(b.h * 10) / 10); }); });
    if (!tailles.length) return [];
    // Corps courant = taille la plus fréquente (le texte de lecture domine).
    var freq = {}, courant = tailles[0];
    tailles.forEach(function (t) { freq[t] = (freq[t] || 0) + 1; if (freq[t] > freq[courant] || (freq[t] === freq[courant] && t < courant)) courant = t; });
    var seuil = courant * 1.3;
    function eligible(b) { return b.h >= seuil && b.str && b.str.trim().length >= 3 && b.str.length <= 120; }
    var grands = [];
    blocsParPage.forEach(function (l) { l.forEach(function (b) { var t = Math.round(b.h * 10) / 10; if (eligible(b) && grands.indexOf(t) < 0) grands.push(t); }); });
    grands.sort(function (a, b) { return b - a; });
    var out = [];
    blocsParPage.forEach(function (l, i) {
      l.forEach(function (b) {
        if (!eligible(b)) return;
        var niveau = Math.min(2, grands.indexOf(Math.round(b.h * 10) / 10));
        out.push({ page: i, titre: b.str.trim(), y: b.y, niveau: Math.max(0, niveau) });
      });
    });
    return out;
  }
  function urlValide(u) { return /^(https?:\/\/[^\s]+|mailto:[^\s@]+@[^\s@]+)$/i.test(String(u || '').trim()); }

  M._interne = M._interne || {};
  M._interne.navigation = { titresDepuisBlocs: titresDepuisBlocs, urlValide: urlValide };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function bouton(txt, cls, bulle) { var b = el('button', 'tpdf-b' + (cls ? ' ' + cls : ''), txt); b.type = 'button'; b.setAttribute('data-bulle', bulle || txt); return b; }
    function mini(icone, bulle, fn) { var b = el('button', 'tpdf-btn tpdf-btn-mini'); b.type = 'button'; b.innerHTML = api.ico(icone, 14); b.setAttribute('data-bulle', bulle); b.setAttribute('aria-label', bulle); b.addEventListener('click', fn); return b; }

    Object.assign(api.IC, {
      signets: '<path d="M7 3.5h10a1 1 0 0 1 1 1V21l-6-4-6 4V4.5a1 1 0 0 1 1-1z"/>',
      lien: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
      deuxpages: '<rect x="3" y="4.5" width="8" height="15" rx="1"/><rect x="13" y="4.5" width="8" height="15" rx="1"/>',
      parallele: '<rect x="3" y="3.5" width="7.5" height="17" rx="1"/><rect x="13.5" y="3.5" width="7.5" height="17" rx="1"/><path d="M12 8v8M10.5 9.5L12 8l1.5 1.5M10.5 14.5L12 16l1.5-1.5"/>',
      monter: '<path d="M6 14.5l6-6 6 6"/>', descendre: '<path d="M6 9.5l6 6 6-6"/>',
      retrait: '<path d="M9 6l6 6-6 6"/>', desretrait: '<path d="M15 6l-6 6 6 6"/>'
    });
    api.BULLES.deuxpages = 'Deux pages';
    api.BULLES.lien = 'Lien';
    api.LIBELLES.lien = 'Lien';
    api.AIDE_OUTIL.lien = 'Tracer la zone cliquable, puis choisir la page ou l\'adresse.';
    EXT.boutons.push({ groupe: 'vue', html: api.bouton('deuxpages', 'deuxpages', 'Afficher deux pages côte à côte', { doc: 1 }) });
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('lien', 'lien', 'Créer un lien') });
    var mp = EXT.menus.pages || (EXT.menus.pages = { libelle: 'Pages', icone: 'pages', ordre: 1, items: [] });
    mp.items.push({ separe: true }, { act: 'signets', icone: 'signets', libelle: 'Signets (table des matières)…', bulle: 'Signets', doc: 1 },
      { act: 'liens', icone: 'lien', libelle: 'Liens de la page…', bulle: 'Liens', doc: 1 });
    var mr = EXT.menus.reviser || (EXT.menus.reviser = { libelle: 'Réviser', icone: 'reviser', ordre: 2, items: [] });
    mr.items.push({ act: 'parallele', icone: 'parallele', libelle: 'Lire deux PDF en parallèle…', bulle: 'Parallèle', doc: 1 });

    /* ── Signets ──────────────────────────────────────────────────────── */
    function signets() { var s = S(); if (!s.signets) s.signets = []; return s.signets; }
    function indexPage(uid) { return S().pages.findIndex(function (p) { return p.uid === uid; }); }
    async function importer() {
      var s = S(), n = 0;
      var ids = {}; s.pages.forEach(function (p) { ids[p.src] = 1; });
      for (var id in ids) {
        var src = s.sources[id], out = null;
        try { out = await src.pdf.getOutline(); } catch (e) { out = null; }
        if (!out) continue;
        var parcourir = async function (items, niveau) {
          for (var i = 0; i < items.length; i++) {
            var it = items[i], dest = it.dest, idx = -1;
            try {
              if (typeof dest === 'string') dest = await src.pdf.getDestination(dest);
              if (Array.isArray(dest) && dest[0]) idx = typeof dest[0] === 'number' ? dest[0] : await src.pdf.getPageIndex(dest[0]);
            } catch (e) { idx = -1; }
            var p = s.pages.find(function (q) { return q.src === id && q.idx === idx; });
            if (p) { signets().push({ id: api.nid('g'), titre: String(it.title || 'Sans titre').slice(0, 200), uid: p.uid, niveau: Math.min(2, niveau) }); n++; }
            if (it.items && it.items.length) await parcourir(it.items, niveau + 1);
          }
        };
        await parcourir(out, 0);
      }
      return n;
    }
    async function generer() {
      var s = S(), TX = M._interne.texte, parPage = [];
      for (var i = 0; i < s.pages.length; i++) {
        var p = s.pages[i], d = api.dims(p), items = await api.texteDe(p);
        parPage.push(TX.grouperItems(items).map(function (b) { return { str: b.str, h: b.h, y: d.meta.view[3] - b.Y }; }));
      }
      var t = titresDepuisBlocs(parPage);
      t.forEach(function (x) { signets().push({ id: api.nid('g'), titre: x.titre, uid: s.pages[x.page].uid, niveau: x.niveau, y: x.y }); });
      return t.length;
    }
    function panneauSignets() {
      var s = S(), corps = el('div'), liste = el('div', 'tpdf-signets');
      corps.appendChild(liste);
      function dessiner() {
        liste.textContent = '';
        var l = signets().filter(function (g) { return indexPage(g.uid) >= 0; });
        s.signets = l;
        if (!l.length) liste.appendChild(el('p', 'tpdf-aide', 'Aucun signet. Ajouter la page courante, importer ceux du PDF ou les générer depuis les titres.'));
        l.forEach(function (g, i) {
          var r = el('div', 'tpdf-signet'); r.style.paddingLeft = (g.niveau * 18) + 'px';
          var t = el('input', 'tpdf-champ'); t.type = 'text'; t.value = g.titre; t.setAttribute('aria-label', 'Titre du signet');
          t.addEventListener('change', function () { g.titre = t.value.trim() || g.titre; });
          var pg = el('button', 'tpdf-b', 'p. ' + (indexPage(g.uid) + 1)); pg.type = 'button'; pg.setAttribute('data-bulle', 'Aller');
          pg.addEventListener('click', function () { api.fermerModale(); api.allerPage(indexPage(g.uid), true); });
          r.appendChild(t); r.appendChild(pg);
          r.appendChild(mini('monter', 'Monter', function () { if (i > 0) { l.splice(i - 1, 0, l.splice(i, 1)[0]); dessiner(); } }));
          r.appendChild(mini('descendre', 'Descendre', function () { if (i < l.length - 1) { l.splice(i + 1, 0, l.splice(i, 1)[0]); dessiner(); } }));
          r.appendChild(mini('desretrait', 'Remonter d\'un niveau', function () { g.niveau = Math.max(0, g.niveau - 1); dessiner(); }));
          r.appendChild(mini('retrait', 'Sous-signet', function () { g.niveau = Math.min(2, g.niveau + 1); dessiner(); }));
          r.appendChild(mini('supprimer', 'Retirer', function () { l.splice(i, 1); dessiner(); }));
          liste.appendChild(r);
        });
      }
      dessiner();
      corps.appendChild(el('p', 'tpdf-aide', 'Écrits à l\'enregistrement en table des matières du PDF (volet Signets des lecteurs).'));
      api.ouvrirModale('Signets', corps, [
        { txt: 'Importer du PDF', bulle: 'Importer', fn: async function () { var n = await importer(); dessiner(); api.toast(n ? n + ' signet(s) importé(s).' : 'Aucun signet dans les fichiers ouverts.', n ? 'success' : 'info'); } },
        { txt: 'Depuis les titres', bulle: 'Générer', fn: async function () { api.occuper('Analyse…'); try { var n = await generer(); dessiner(); api.toast(n ? n + ' titre(s) trouvé(s).' : 'Aucun titre détecté.', n ? 'success' : 'info'); } finally { api.liberer(); } } },
        { txt: 'Ajouter la page', bulle: 'Ajouter', fn: function () { var p = api.pageCourante(); signets().push({ id: api.nid('g'), titre: 'Page ' + (s.cur + 1), uid: p.uid, niveau: 0 }); dessiner(); var x = liste.querySelectorAll('input'); if (x.length) { x[x.length - 1].focus(); x[x.length - 1].select(); } } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'signets', large: true });
    }
    EXT.actions.signets = { fn: panneauSignets }; EXT.panneaux.signets = panneauSignets;

    // Table des matières écrite sur le document final.
    EXT.hooks.exportApres = (EXT.hooks.exportApres || []).concat(function (ctx) {
      var l = (S().signets || []);
      if (!l.length) return;
      var L = ctx.L, doc = ctx.final || ctx.out, c = doc.context, N = L.PDFName, pages = doc.getPages();
      var items = [];
      l.forEach(function (g) {
        var i = ctx.pages.findIndex(function (p) { return p.uid === g.uid; });
        if (i < 0 || !pages[i]) return;
        var pg = pages[i], h = pg.getSize().height;
        items.push({ g: g, dict: c.obj({ Title: L.PDFHexString.fromText(g.titre), Dest: [pg.ref, 'XYZ', null, g.y != null ? Math.max(0, h - g.y + 10) : h, null] }) });
      });
      if (!items.length) return;
      var racine = c.obj({ Type: 'Outlines' }), refRacine = c.register(racine);
      items.forEach(function (it) { it.ref = c.register(it.dict); });
      // Hiérarchie : le parent d'un signet est le dernier signet de niveau inférieur.
      var pile = [{ ref: refRacine, dict: racine, enfants: [], niveau: -1 }];
      items.forEach(function (it) {
        while (pile.length > 1 && pile[pile.length - 1].niveau >= it.g.niveau) pile.pop();
        var parent = pile[pile.length - 1];
        parent.enfants.push(it); it.parent = parent; it.enfants = []; it.niveau = it.g.niveau;
        pile.push(it);
      });
      function lier(noeud) {
        var e = noeud.enfants;
        if (!e.length) return 0;
        noeud.dict.set(N.of('First'), e[0].ref); noeud.dict.set(N.of('Last'), e[e.length - 1].ref);
        var total = 0;
        e.forEach(function (x, k) {
          x.dict.set(N.of('Parent'), noeud.ref);
          if (k > 0) x.dict.set(N.of('Prev'), e[k - 1].ref);
          if (k < e.length - 1) x.dict.set(N.of('Next'), e[k + 1].ref);
          total += 1 + lier(x);
        });
        noeud.dict.set(N.of('Count'), L.PDFNumber.of(noeud === pile[0] ? total : e.length));
        return total;
      }
      lier(pile[0]);
      doc.catalog.set(N.of('Outlines'), refRacine);
      doc.catalog.set(N.of('PageMode'), N.of('UseOutlines'));
    });

    /* ── Liens ────────────────────────────────────────────────────────── */
    EXT.outils.lien = { down: function (pt) { return { t: 'lien', x: pt.x, y: pt.y, w: 0, h: 0, cible: 'page', uid: null, url: '' }; } };
    EXT.types.lien = {
      boiteTournante: true,
      tailleDefaut: function () { return [120, 18]; },
      apresCreation: function () { api.choisirOutil('select', true); },
      dessiner: function (a, g, z) {
        api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: 'transparent', 'class': 'tpdf-lien', 'stroke-width': 1.2 / z }, g);
        var t = api.sv('text', { x: a.x + 2, y: a.y - 2, 'font-size': 8 / z, 'font-family': api.POLICE, 'class': 'tpdf-lien-txt' }, g);
        t.textContent = a.cible === 'url' ? (a.url || 'adresse ?') : (a.uid && indexPage(a.uid) >= 0 ? '→ p. ' + (indexPage(a.uid) + 1) : '→ page ?');
      },
      props: function (sec, a) {
        if (!a) return;
        var s = S(), type = el('select', 'tpdf-champ');
        [['page', 'Vers une page du document'], ['url', 'Vers une adresse web ou un e-mail']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; type.appendChild(o); });
        type.value = a.cible;
        sec.appendChild(api.champ('Destination', type));
        var pg = el('select', 'tpdf-champ');
        s.pages.forEach(function (p, i) { var o = el('option', null, 'Page ' + (i + 1)); o.value = p.uid; pg.appendChild(o); });
        pg.value = a.uid || (s.pages[0] && s.pages[0].uid);
        var lp = api.champ('Page', pg);
        var url = el('input', 'tpdf-champ'); url.type = 'url'; url.placeholder = 'https://… ou mailto:…'; url.value = a.url || '';
        var lu = api.champ('Adresse', url);
        sec.appendChild(lp); sec.appendChild(lu);
        function maj() { lp.hidden = type.value !== 'page'; lu.hidden = type.value !== 'url'; }
        maj();
        type.addEventListener('change', function () { api.majProp('cible', type.value, a); if (type.value === 'page' && !a.uid) api.majProp('uid', pg.value, a); api.validerProp(); maj(); });
        pg.addEventListener('change', function () { api.majProp('uid', pg.value, a); api.validerProp(); });
        url.addEventListener('change', function () {
          if (url.value && !urlValide(url.value)) { api.toast('Adresse invalide — commencer par https:// ou mailto:.', 'danger'); return; }
          api.majProp('url', url.value.trim(), a); api.validerProp();
        });
        if (!a.uid && a.cible === 'page') { a.uid = pg.value; }
      },
      exporter: async function (a, c) {
        var p1 = c.P(a.x, a.y), p2 = c.P(a.x + a.w, a.y + a.h);
        var rect = [Math.min(p1[0], p2[0]), Math.min(p1[1], p2[1]), Math.max(p1[0], p2[0]), Math.max(p1[1], p2[1])];
        var ctx = c.out.context, L = c.L;
        if (a.cible === 'url') {
          if (!urlValide(a.url)) return;
          var an = ctx.obj({ Type: 'Annot', Subtype: 'Link', Rect: rect, Border: [0, 0, 0], F: 4, A: { Type: 'Action', S: 'URI', URI: L.PDFString.of(a.url) } });
          c.pg.node.addAnnot(ctx.register(an));
        } else if (a.uid) {
          // La page visée n'est peut-être pas encore écrite : lien posé en fin de construction.
          c.out.__liens = c.out.__liens || [];
          c.out.__liens.push({ pg: c.pg, rect: rect, uid: a.uid });
        }
      }
    };
    EXT.hooks.export = (EXT.hooks.export || []).concat(function (ctx) {
      var l = ctx.out.__liens; if (!l || !l.length) return;
      var pages = ctx.out.getPages(), c = ctx.out.context;
      l.forEach(function (x) {
        var i = ctx.pages.findIndex(function (p) { return p.uid === x.uid; });
        if (i < 0) return;
        var an = c.obj({ Type: 'Annot', Subtype: 'Link', Rect: x.rect, Border: [0, 0, 0], F: 4, Dest: [pages[i].ref, 'Fit'] });
        x.pg.node.addAnnot(c.register(an));
      });
    });
    // Liens d'origine retirés : retirés de la page copiée à l'export.
    EXT.hooks.exportPage = (EXT.hooks.exportPage || []).concat(function (pg, p, d, ctx) {
      if (!p.liensRetires || !p.liensRetires.length) return;
      var L = ctx.L, an = pg.node.Annots(); if (!an) return;
      for (var i = an.size() - 1; i >= 0; i--) {
        var o = ctx.out.context.lookup(an.get(i));
        if (!(o instanceof L.PDFDict) || String(o.get(L.PDFName.of('Subtype'))) !== '/Link') continue;
        var r = o.get(L.PDFName.of('Rect')); if (!(r instanceof L.PDFArray)) continue;
        var v = r.asArray().map(function (x) { return x.asNumber ? x.asNumber() : 0; });
        if (p.liensRetires.some(function (q) { return q.every(function (n, k) { return Math.abs(n - v[k]) < 0.5; }); })) an.remove(i);
      }
    });
    async function panneauLiens() {
      var s = S(), p = api.pageCourante(), src = s.sources[p.src], corps = el('div'), liste = el('div', 'tpdf-lc');
      corps.appendChild(el('p', 'tpdf-aide', 'Liens présents dans le fichier d\'origine, page ' + (s.cur + 1) + '. Pour en créer un : outil Lien de la barre.'));
      corps.appendChild(liste);
      var anns = [];
      try { anns = (await (await src.pdf.getPage(p.idx + 1)).getAnnotations()).filter(function (a) { return a.subtype === 'Link'; }); } catch (e) { anns = []; }
      p.liensRetires = p.liensRetires || [];
      function dessiner() {
        liste.textContent = '';
        if (!anns.length) liste.appendChild(el('p', 'tpdf-aide', 'Aucun lien d\'origine sur cette page.'));
        anns.forEach(function (an) {
          var retire = p.liensRetires.some(function (q) { return q.every(function (n, k) { return Math.abs(n - an.rect[k]) < 0.5; }); });
          var it = el('div', 'tpdf-lc-item');
          it.appendChild(el('span', 'tpdf-lc-nom', an.url || (an.dest ? 'Vers une page' : 'Action')));
          it.appendChild(el('span', 'tpdf-lc-type', retire ? 'Retiré à l\'enregistrement' : 'Conservé'));
          var lg = el('div', 'tpdf-ligne');
          var bR = bouton(retire ? 'Garder' : 'Retirer', '', retire ? 'Garder' : 'Retirer');
          bR.addEventListener('click', function () {
            if (retire) p.liensRetires = p.liensRetires.filter(function (q) { return !q.every(function (n, k) { return Math.abs(n - an.rect[k]) < 0.5; }); });
            else p.liensRetires.push(an.rect.slice());
            dessiner();
          });
          var bM = bouton('Modifier', '', 'Modifier');
          bM.addEventListener('click', function () {
            var d = api.dims(p), a1 = api.versVue(d.meta.view, d.R, an.rect[0], an.rect[1]), a2 = api.versVue(d.meta.view, d.R, an.rect[2], an.rect[3]);
            var avant = api.snapshot();
            p.liensRetires.push(an.rect.slice());
            var a = { id: api.nid('n'), t: 'lien', x: Math.min(a1[0], a2[0]), y: Math.min(a1[1], a2[1]), w: Math.abs(a2[0] - a1[0]), h: Math.abs(a2[1] - a1[1]),
              cible: an.url ? 'url' : 'page', url: an.url || '', uid: null };
            p.annots.push(a); s.annSel = a.id; api.pushHist(avant);
            api.fermerModale(); api.dessinerCalque(); api.rendreProps(); s.el.classList.add('tpdf-props-ouvert');
          });
          lg.appendChild(bM); lg.appendChild(bR); it.appendChild(lg);
          liste.appendChild(it);
        });
      }
      dessiner();
      api.ouvrirModale('Liens de la page', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'liens' });
    }
    EXT.actions.liens = { fn: panneauLiens }; EXT.panneaux.liens = panneauLiens;

    /* ── Vue deux pages ───────────────────────────────────────────────── */
    var _deux = { cle: null, url: null };
    EXT.actions.deuxpages = { fn: function (b) {
      var s = S(); s.deuxPages = !s.deuxPages;
      if (b) b.classList.toggle('tpdf-actif', s.deuxPages);
      if (!s.deuxPages) { var f = s.el.querySelector('.tpdf-feuille2'); if (f) f.remove(); }
      api.rendrePage();
    } };
    EXT.hooks.barre = (EXT.hooks.barre || []).concat(function () {
      var s = S(), b = s && s.el.querySelector('[data-act="deuxpages"]'); if (b) b.classList.toggle('tpdf-actif', !!s.deuxPages);
    });
    EXT.hooks.rendu = (EXT.hooks.rendu || []).concat(async function (p, d, z) {
      var s = S(); if (!s.deuxPages) return;
      var boite = s.el.querySelector('.tpdf-boite'), f = boite.querySelector('.tpdf-feuille2');
      var suiv = s.pages[s.cur + 1];
      if (!suiv) { if (f) f.remove(); return; }
      if (!f) {
        f = el('div', 'tpdf-feuille tpdf-feuille2'); f.setAttribute('data-bulle', 'Aller à cette page');
        f.addEventListener('click', function () { api.allerPage(s.cur + 1, true); });
        boite.appendChild(f);
      }
      var d2 = api.dims(suiv);
      f.style.width = Math.round(d2.w * z) + 'px'; f.style.height = Math.round(d2.h * z) + 'px';
      // Rendu fidèle (annotations comprises) : la page suivante est construite à part.
      var cle = JSON.stringify(suiv) + z;
      if (_deux.cle === cle && f.querySelector('img')) return;
      _deux.cle = cle;
      try {
        var b = await api.construire([suiv]), pj = await api.pdfjs();
        var doc = await pj.getDocument({ data: b.slice(), isEvalSupported: false }).promise, pg = await doc.getPage(1);
        var k = z * Math.min(window.devicePixelRatio || 1, 2), vp = pg.getViewport({ scale: k }), cv = el('canvas');
        cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
        await pg.render({ canvasContext: cv.getContext('2d'), viewport: vp, intent: 'print' }).promise;
        doc.destroy();
        if (_deux.cle !== cle) return;
        f.textContent = ''; var im = el('img'); im.alt = 'Page ' + (s.cur + 2); im.src = cv.toDataURL('image/png'); f.appendChild(im);
      } catch (e) { /* aperçu de la page suivante indisponible */ }
    });

    /* ── Deux PDF en parallèle, défilement synchronisé ────────────────── */
    async function colonne(octets, cible, etiquette) {
      var pj = await api.pdfjs(), doc = await pj.getDocument({ data: octets, isEvalSupported: false }).promise;
      cible.textContent = ''; cible.appendChild(el('div', 'tpdf-par-tete', etiquette + ' · ' + doc.numPages + ' page(s)'));
      for (var i = 1; i <= doc.numPages; i++) {
        var pg = await doc.getPage(i), vp1 = pg.getViewport({ scale: 1 }), k = Math.min(2, 760 / vp1.width), vp = pg.getViewport({ scale: k }), cv = el('canvas');
        cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
        var c = cv.getContext('2d'); c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
        await pg.render({ canvasContext: c, viewport: vp, intent: 'print' }).promise;
        cible.appendChild(cv);
      }
      doc.destroy();
    }
    function panneauParallele() {
      var corps = el('div', 'tpdf-par'), haut = el('div', 'tpdf-ligne tpdf-ligne-esp');
      var fic = el('input', 'tpdf-champ'); fic.type = 'file'; fic.accept = '.pdf,application/pdf';
      var sync = el('label', 'tpdf-case'), si = el('input'); si.type = 'checkbox'; si.checked = true; sync.appendChild(si); sync.appendChild(document.createTextNode(' Défilement synchronisé'));
      haut.appendChild(api.champ('Second PDF', fic)); haut.appendChild(sync); corps.appendChild(haut);
      var g = el('div', 'tpdf-par-cols'), ca = el('div', 'tpdf-par-col'), cb = el('div', 'tpdf-par-col');
      g.appendChild(ca); g.appendChild(cb); corps.appendChild(g);
      var verrou = false;
      function suivre(de, vers) {
        de.addEventListener('scroll', function () {
          if (!si.checked || verrou) return;
          verrou = true;
          var r = de.scrollTop / Math.max(1, de.scrollHeight - de.clientHeight);
          vers.scrollTop = r * (vers.scrollHeight - vers.clientHeight);
          requestAnimationFrame(function () { verrou = false; });
        });
      }
      suivre(ca, cb); suivre(cb, ca);
      api.ouvrirModale('Deux PDF en parallèle', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'parallele', large: true });
      ca.appendChild(el('p', 'tpdf-aide', 'Préparation…'));
      api.construire().then(function (b) { return colonne(b, ca, 'Document ouvert'); }).catch(function (e) { api.toast(api.msgErreur(e), 'danger'); });
      fic.addEventListener('change', async function () {
        var f = fic.files && fic.files[0]; if (!f) return;
        cb.textContent = ''; cb.appendChild(el('p', 'tpdf-aide', 'Chargement…'));
        try { await colonne(new Uint8Array(await f.arrayBuffer()), cb, f.name); }
        catch (e) { cb.textContent = ''; api.toast(e && e.name === 'PasswordException' ? 'PDF protégé par mot de passe.' : 'Fichier illisible — ce n\'est pas un PDF valide.', 'danger'); }
      });
    }
    EXT.actions.parallele = { fn: panneauParallele }; EXT.panneaux.parallele = panneauParallele;
  });
})();
