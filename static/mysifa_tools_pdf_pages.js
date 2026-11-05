/*
 * MyTools — éditeur PDF : pages et document (menu « Pages »).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   insérer les pages d'un autre PDF, scinder (par page, toutes les N pages,
 *   par plages), extraire, recadrer, redimensionner (A4, A3, A5, Lettre),
 *   numérotation / en-têtes / pieds / Bates / filigrane, compression
 *   (images rééchantillonnées ou pages en image), export image ou Word,
 *   « Envoyer à signer » (parapheur, écrit par ailleurs).
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  var FORMATS = { a4: [595.28, 841.89, 'A4'], a3: [841.89, 1190.55, 'A3'], a5: [419.53, 595.28, 'A5'], letter: [612, 792, 'Lettre'], legal: [612, 1008, 'Légal'] };
  // Facteur et boîte (espace PDF non pivoté) pour ramener une page à un format,
  // orientation conservée, contenu centré.
  function ajusterFormat(box, R, format) {
    var f = FORMATS[format]; if (!f) return null;
    var dispW = R % 180 ? box.height : box.width, dispH = R % 180 ? box.width : box.height;
    var tw = f[0], th = f[1];
    if ((dispW > dispH) !== (tw > th)) { var t = tw; tw = th; th = t; }
    // cible dans l'espace non pivoté
    var uw = R % 180 ? th : tw, uh = R % 180 ? tw : th;
    var k = Math.min(uw / box.width, uh / box.height);
    return { k: k, largeur: uw, hauteur: uh };
  }
  function remplirModele(modele, v) {
    return String(modele || '').replace(/\{(n|N|date|nom|fichier)\}/g, function (_, c) { return v[c] != null ? String(v[c]) : ''; });
  }
  function numeroBates(prefixe, debut, chiffres, i) {
    var n = String((parseInt(debut, 10) || 1) + i);
    while (n.length < (parseInt(chiffres, 10) || 0)) n = '0' + n;
    return (prefixe || '') + n;
  }
  // Ligne de base (coin gauche) d'un texte dans la page affichée W×H.
  function positionTexte(position, W, H, marge, largeur, taille) {
    var bas = position.indexOf('bas') === 0;
    var y = bas ? H - marge : marge + taille * 0.75;
    var x = /gauche$/.test(position) ? marge : /droite$/.test(position) ? W - marge - largeur : (W - largeur) / 2;
    return { x: x, y: y };
  }
  // Origine (ligne de base, gauche) d'un objet w×h centré en C et tourné de θ
  // degrés dans le sens visuel antihoraire (repère affiché, y vers le bas).
  function origineTournee(cx, cy, w, h, angle) {
    var t = angle * Math.PI / 180, u = [Math.cos(t), -Math.sin(t)], n = [-Math.sin(t), -Math.cos(t)];
    return { x: cx - u[0] * w / 2 - n[0] * h / 2, y: cy - u[1] * w / 2 - n[1] * h / 2 };
  }
  function pageVisee(cible, i, total, lirePlages) {
    if (!cible || cible === 'toutes') return true;
    if (cible === 'saufpremiere') return i > 0;
    try { return lirePlages(cible, total).some(function (g) { return i + 1 >= g.a && i + 1 <= g.b; }); } catch (e) { return false; }
  }

  M._interne = M._interne || {};
  M._interne.pages = { ajusterFormat: ajusterFormat, remplirModele: remplirModele, numeroBates: numeroBates,
    positionTexte: positionTexte, origineTournee: origineTournee, pageVisee: pageVisee, FORMATS: FORMATS };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function choix(options, val) {
      var s = el('select', 'tpdf-champ');
      options.forEach(function (o) { var x = el('option', null, o[1]); x.value = o[0]; s.appendChild(x); });
      if (val != null) s.value = val;
      return s;
    }
    function nombreChamp(val, min, max, pas) { var n = el('input', 'tpdf-champ'); n.type = 'number'; n.min = min; n.max = max; n.step = pas || 1; n.value = val; return n; }
    function texteChamp(val, ph) { var n = el('input', 'tpdf-champ'); n.type = 'text'; n.value = val || ''; if (ph) n.placeholder = ph; return n; }
    function coche(lib, val) { var l = el('label', 'tpdf-case'), i = el('input'); i.type = 'checkbox'; i.checked = !!val; l.appendChild(i); l.appendChild(document.createTextNode(' ' + lib)); l.input = i; return l; }

    Object.assign(api.IC, {
      pages: '<rect x="7" y="3.5" width="12" height="15" rx="1.5"/><path d="M5 7v12a1.5 1.5 0 0 0 1.5 1.5H15"/>',
      inserer: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M8.5 14.5h7M12.5 11.5l3 3-3 3"/>',
      recadrer: '<path d="M6.5 3v13.5H21"/><path d="M3 6.5h13.5V21"/>',
      format: '<rect x="4" y="4" width="16" height="16" rx="1.5"/><path d="M9 4v4.5H4.5M15 20v-4.5h4.5"/>',
      misepage: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M8.5 6.5h3M8.5 17.5h7M14 13.5l-3-3M11 13.5l3-3"/>',
      exporter: '<rect x="3.5" y="5" width="12" height="11" rx="1.5"/><path d="M5 14l3.5-3 2.5 2 2-1.5 2.5 2"/><path d="M18 9v10.5M15 16.5l3 3 3-3"/>',
      parapheur: '<path d="M4 20l4-1 10.5-10.5a2.1 2.1 0 0 0-3-3L5 16z"/><path d="M13.5 7.5l3 3"/><path d="M14 20h6"/>'
    });
    api.BULLES.parapheur = 'Signer à distance';
    EXT.boutons.push({ groupe: 'fichier', html: api.bouton('parapheur', 'parapheur', 'Envoyer à signer', { doc: 1 }) });
    EXT.menus.pages = { libelle: 'Pages', icone: 'pages', ordre: 1, items: [
      { act: 'inserer', icone: 'inserer', libelle: 'Insérer un PDF après la page', bulle: 'Insérer', doc: 1 },
      { act: 'extraire', icone: 'extraire', libelle: 'Extraire la sélection', bulle: 'Extraire', doc: 1 },
      { act: 'decouper', icone: 'decouper', libelle: 'Scinder en plusieurs fichiers…', bulle: 'Scinder', doc: 1 },
      { separe: true },
      { act: 'recadrer', icone: 'recadrer', libelle: 'Recadrer la page', bulle: 'Recadrer', doc: 1 },
      { act: 'format', icone: 'format', libelle: 'Redimensionner (A4, A3, Lettre)…', bulle: 'Format', doc: 1 },
      { act: 'misepage', icone: 'misepage', libelle: 'Numéros, en-têtes, Bates, filigrane…', bulle: 'Numéroter', doc: 1 },
      { separe: true },
      { act: 'compresser', icone: 'compresser', libelle: 'Compresser…', bulle: 'Compresser', doc: 1 },
      { act: 'exporter', icone: 'exporter', libelle: 'Exporter en image ou Word…', bulle: 'Exporter', doc: 1 }
    ] };

    /* ── Insérer les pages d'un autre PDF ─────────────────────────────── */
    var entree = null;
    EXT.actions.inserer = { fn: function () {
      if (!entree) {
        entree = el('input'); entree.type = 'file'; entree.multiple = true; entree.hidden = true;
        entree.accept = '.pdf,application/pdf,image/png,image/jpeg';
        entree.addEventListener('change', function () { var f = Array.prototype.slice.call(entree.files || []); entree.value = ''; inserer(f); });
      }
      S().el.appendChild(entree);
      entree.click();
    } };
    async function inserer(fichiers) {
      var s = S(); if (!fichiers.length) return;
      var avant = api.snapshot(), pos = s.cur + 1, nouv = [];
      api.occuper('Insertion…');
      try {
        for (var i = 0; i < fichiers.length; i++) {
          var f = fichiers[i], b = new Uint8Array(await f.arrayBuffer());
          try {
            if (!/\.pdf$/i.test(f.name) && f.type !== 'application/pdf') b = await api.imageVersPdf(b);
            var src = await api.ajouterSource(f.name, b);
            for (var k = 0; k < src.metas.length; k++) nouv.push(api.nouvellePage(src.id, k));
          } catch (e) { api.toast('« ' + f.name + ' » : ' + api.msgErreur(e), 'danger'); }
        }
      } finally { api.liberer(); }
      if (!nouv.length) return;
      s.pages.splice.apply(s.pages, [pos, 0].concat(nouv));
      s.cur = pos; s.sel = {}; s.sel[nouv[0].uid] = 1; s.ancre = nouv[0].uid;
      api.pushHist(avant); api.toutRendre(); api.notifier();
      api.toast(nouv.length + ' page' + (nouv.length > 1 ? 's insérées' : ' insérée') + ' après la page ' + pos + '.', 'success');
    }

    /* ── Scinder ──────────────────────────────────────────────────────── */
    function panneauScinder() {
      var s = S(), n = s.pages.length, corps = el('div');
      var mode = choix([['page', 'Un fichier par page (' + n + ')'], ['n', 'Toutes les N pages'], ['plages', 'Par plages']], 'n');
      var nb = nombreChamp(2, 1, Math.max(1, n), 1), pl = texteChamp('', '1-3, 5, 8-10');
      var lnb = api.champ('Pages par fichier', nb), lpl = api.champ('Plages', pl);
      corps.appendChild(api.champ('Découpage', mode)); corps.appendChild(lnb); corps.appendChild(lpl);
      var info = el('p', 'tpdf-aide');
      corps.appendChild(info);
      function maj() {
        lnb.hidden = mode.value !== 'n'; lpl.hidden = mode.value !== 'plages';
        try { info.textContent = groupes().length + ' fichier(s) à télécharger. Numéros de l\'ordre actuel des vignettes.'; }
        catch (e) { info.textContent = e.message; }
      }
      function groupes() {
        if (mode.value === 'page') return api.groupesParN(n, 1);
        if (mode.value === 'n') return api.groupesParN(n, nb.value);
        return api.lirePlages(pl.value, n);
      }
      [mode, nb, pl].forEach(function (x) { x.addEventListener('input', maj); x.addEventListener('change', maj); });
      maj();
      api.ouvrirModale('Scinder le document', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Scinder', plein: true, fn: async function () {
          var g; try { g = groupes(); } catch (e) { api.toast(e.message, 'danger'); return; }
          api.fermerModale();
          api.occuper('Découpage…');
          try {
            for (var i = 0; i < g.length; i++) {
              var b = await api.construire(s.pages.slice(g[i].a - 1, g[i].b));
              api.telecharger(b, api.nomBase() + '-p' + g[i].a + (g[i].b > g[i].a ? '-' + g[i].b : '') + '.pdf');
              await new Promise(function (r) { setTimeout(r, 350); });
            }
            api.toast(g.length + ' fichier' + (g.length > 1 ? 's téléchargés.' : ' téléchargé.'), 'success');
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); } finally { api.liberer(); }
        } }
      ], { cle: 'scinder' });
    }
    EXT.actions.decouper = { fn: panneauScinder };
    EXT.panneaux.scinder = panneauScinder;

    /* ── Recadrer ─────────────────────────────────────────────────────── */
    api.LIBELLES.recadrage = 'Recadrage';
    api.AIDE_OUTIL.recadrer = 'Tracer le cadre à garder, puis « Appliquer ».';
    EXT.actions.recadrer = { fn: function () { api.choisirOutil('recadrer'); } };
    EXT.outils.recadrer = {
      down: function (pt, p) {
        p.annots = p.annots.filter(function (a) { return a.t !== 'recadrage'; });
        return { t: 'recadrage', x: pt.x, y: pt.y, w: 0, h: 0 };
      },
      props: function (sec) { propsRecadrage(sec, null); }
    };
    EXT.types.recadrage = {
      boiteTournante: true,
      tailleDefaut: function (a) { var d = api.dims(api.pageCourante()); a.x = d.w * 0.05; a.y = d.h * 0.05; return [d.w * 0.9, d.h * 0.9]; },
      dessiner: function (a, g) {
        var d = api.dims(api.pageCourante());
        api.sv('path', { d: 'M0 0H' + d.w + 'V' + d.h + 'H0Z M' + a.x + ' ' + a.y + 'v' + a.h + 'h' + a.w + 'v' + (-a.h) + 'Z',
          'fill-rule': 'evenodd', 'class': 'tpdf-recadre-voile' }, g);
        api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: 'transparent', 'class': 'tpdf-recadre-cadre' }, g);
      },
      props: function (sec, a) { propsRecadrage(sec, a); },
      exporter: async function () { /* cadre de travail : jamais exporté */ }
    };
    function decaler(p, dx, dy, d0) {
      // Décale les annotations quand l'origine de la page change de (dx, dy)
      // dans le repère affiché, (d0x, d0y) dans le repère non pivoté.
      p.annots.forEach(function (a) {
        var T = EXT.types[a.t];
        if (T && T.repere === 'pdf0') { a.x -= d0[0]; a.y -= d0[1]; if (a.bx != null) { a.bx -= d0[0]; a.by -= d0[1]; } return; }
        api.deplacer(a, JSON.parse(JSON.stringify(a)), -dx, -dy);
      });
    }
    function appliquerRecadrage(p, a) {
      var d = api.dims(p), v = d.meta.view;
      var c1 = api.versPdf(v, d.R, a.x, a.y), c2 = api.versPdf(v, d.R, a.x + a.w, a.y + a.h);
      var box = [Math.min(c1[0], c2[0]), Math.min(c1[1], c2[1]), Math.max(c1[0], c2[0]), Math.max(c1[1], c2[1])];
      p.annots = p.annots.filter(function (x) { return x !== a && x.t !== 'recadrage'; });
      decaler(p, a.x, a.y, [box[0] - v[0], v[3] - box[3]]);
      p.crop = box;
    }
    function propsRecadrage(sec, a) {
      var s = S(), p = api.pageCourante();
      if (a) {
        var tous = coche('Appliquer aussi aux pages sélectionnées de même format', false);
        sec.appendChild(tous);
        var ok = el('button', 'tpdf-b tpdf-b-plein', 'Appliquer le recadrage'); ok.type = 'button'; ok.setAttribute('data-bulle', 'Appliquer');
        ok.addEventListener('click', function () {
          var avant = api.snapshot(), d = api.dims(p), n = 1;
          var cadre = { x: a.x, y: a.y, w: a.w, h: a.h };
          appliquerRecadrage(p, a);
          if (tous.input.checked) api.pagesCiblees().forEach(function (q) {
            if (q === p) return;
            var dq = api.dims(q);
            if (Math.abs(dq.w - d.w) > 1 || Math.abs(dq.h - d.h) > 1 || dq.R !== d.R) return;
            appliquerRecadrage(q, cadre); n++;
          });
          s.annSel = null; api.pushHist(avant); api.choisirOutil('select'); api.toutRendre();
          api.toast(n > 1 ? n + ' pages recadrées.' : 'Page recadrée.', 'success');
        });
        sec.appendChild(ok);
      }
      if (p && p.crop) {
        var raz = el('button', 'tpdf-b', 'Rétablir la page entière'); raz.type = 'button'; raz.setAttribute('data-bulle', 'Rétablir');
        raz.addEventListener('click', function () {
          var avant = api.snapshot(), crop = p.crop, R = api.dims(p).R, orig = s.sources[p.src].metas[p.idx].view;
          // Coin haut-gauche (affiché) de l'ancien cadre, dans la page entière.
          var X = api.versPdf(crop, R, 0, 0), c = api.versVue(orig, R, X[0], X[1]);
          p.crop = null;
          decaler(p, -c[0], -c[1], [-(crop[0] - orig[0]), -(orig[3] - crop[3])]);
          api.pushHist(avant); api.toutRendre();
        });
        sec.appendChild(raz);
      }
    }

    /* ── Redimensionner ───────────────────────────────────────────────── */
    function panneauFormat() {
      var s = S(), corps = el('div'), p = api.pageCourante();
      var f = choix([['', 'Format d\'origine'], ['a4', 'A4'], ['a3', 'A3'], ['a5', 'A5'], ['letter', 'Lettre US'], ['legal', 'Légal US']], (p && p.format) || '');
      var cible = choix([['courante', 'Page courante'], ['selection', 'Pages sélectionnées'], ['toutes', 'Toutes les pages']], 'toutes');
      corps.appendChild(api.champ('Format', f)); corps.appendChild(api.champ('Pages', cible));
      corps.appendChild(el('p', 'tpdf-aide', 'Le contenu est mis à l\'échelle et centré, orientation conservée. Appliqué à l\'enregistrement.'));
      api.ouvrirModale('Redimensionner', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Appliquer', plein: true, fn: function () {
          var avant = api.snapshot();
          var l = cible.value === 'toutes' ? s.pages : cible.value === 'selection' ? api.pagesCiblees() : [p];
          l.forEach(function (q) { q.format = f.value || null; });
          api.pushHist(avant); api.fermerModale(); api.rendreVignettes(); api.dessinerCalque();
          api.toast(f.value ? l.length + ' page' + (l.length > 1 ? 's' : '') + ' au format ' + FORMATS[f.value][2] + ' à l\'enregistrement.' : 'Format d\'origine rétabli.', 'success');
        } }
      ], { cle: 'format' });
    }
    EXT.actions.format = { fn: panneauFormat };
    EXT.panneaux.format = panneauFormat;

    /* ── Mise en page : numérotation, en-têtes, pieds, Bates, filigrane ── */
    var POSITIONS = [['bas-centre', 'Bas, centré'], ['bas-droite', 'Bas, à droite'], ['bas-gauche', 'Bas, à gauche'],
      ['haut-centre', 'Haut, centré'], ['haut-droite', 'Haut, à droite'], ['haut-gauche', 'Haut, à gauche']];
    function reglages() {
      var s = S();
      if (!s.misePage) s.misePage = {
        numero: { actif: false, modele: 'Page {n} / {N}', position: 'bas-centre', taille: 9 },
        entete: { gauche: '', centre: '', droite: '', taille: 9 },
        pied: { gauche: '', centre: '', droite: '', taille: 9 },
        bates: { actif: false, prefixe: '', debut: 1, chiffres: 6, position: 'bas-droite', taille: 9 },
        filigrane: { actif: false, type: 'texte', texte: 'CONFIDENTIEL', taille: 60, couleur: '#d92626', opacite: 0.15, angle: 45, image: null, echelle: 50 },
        pages: 'toutes', marge: 24
      };
      return s.misePage;
    }
    function actif(r) {
      return r.numero.actif || r.bates.actif || r.filigrane.actif ||
        ['gauche', 'centre', 'droite'].some(function (k) { return r.entete[k] || r.pied[k]; });
    }
    // Ce qu'il faut écrire sur la page i : [{texte, position, taille}] + filigrane.
    function elements(r, i, total) {
      var s = S(), v = { n: i + 1, N: total, date: api.dateDuJour(), nom: api.nomUtilisateur(), fichier: api.nomBase() };
      var l = [];
      if (!pageVisee(r.pages, i, total, api.lirePlages)) return l;
      if (r.numero.actif) l.push({ texte: remplirModele(r.numero.modele, v), position: r.numero.position, taille: r.numero.taille });
      ['gauche', 'centre', 'droite'].forEach(function (k) {
        if (r.entete[k]) l.push({ texte: remplirModele(r.entete[k], v), position: 'haut-' + k, taille: r.entete.taille });
        if (r.pied[k]) l.push({ texte: remplirModele(r.pied[k], v), position: 'bas-' + k, taille: r.pied.taille });
      });
      if (r.bates.actif) l.push({ texte: numeroBates(r.bates.prefixe, r.bates.debut, r.bates.chiffres, i), position: r.bates.position, taille: r.bates.taille });
      void s;
      return l;
    }
    var _cm = null;
    function largeurCss(t, taille) { if (!_cm) _cm = document.createElement('canvas').getContext('2d'); _cm.font = taille + 'px ' + api.POLICE; return _cm.measureText(t).width; }

    // Aperçu sur la page affichée (rien n'est écrit dans les annotations).
    EXT.hooks.calque = (EXT.hooks.calque || []).concat(function (p, d) {
      var s = S(), r = s.misePage; if (!r || !actif(r)) return;
      var i = s.pages.indexOf(p), g = api.sv('g', { 'class': 'tpdf-apercu-mp' });
      s.svg.insertBefore(g, s.svg.firstChild);
      elements(r, i, s.pages.length).forEach(function (e) {
        var w = largeurCss(e.texte, e.taille), o = positionTexte(e.position, d.w, d.h, r.marge, w, e.taille);
        var t = api.sv('text', { x: o.x, y: o.y, 'font-size': e.taille, 'font-family': api.POLICE, fill: '#333333' }, g);
        t.textContent = e.texte;
      });
      var f = r.filigrane;
      if (f.actif && pageVisee(r.pages, i, s.pages.length, api.lirePlages)) {
        if (f.type === 'texte' && f.texte) {
          var tw = largeurCss(f.texte, f.taille), o2 = origineTournee(d.w / 2, d.h / 2, tw, f.taille * 0.72, f.angle);
          var tt = api.sv('text', { x: o2.x, y: o2.y, 'font-size': f.taille, 'font-family': api.POLICE, 'font-weight': 'bold', fill: f.couleur,
            'fill-opacity': f.opacite, transform: 'rotate(' + (-f.angle) + ' ' + o2.x + ' ' + o2.y + ')' }, g);
          tt.textContent = f.texte;
        } else if (f.type === 'image' && f.image && s.images[f.image]) {
          var im = s.images[f.image], iw = d.w * f.echelle / 100, ih = iw * im.h / im.w;
          api.sv('image', { x: (d.w - iw) / 2, y: (d.h - ih) / 2, width: iw, height: ih, href: im.url, opacity: f.opacite,
            transform: 'rotate(' + (-f.angle) + ' ' + d.w / 2 + ' ' + d.h / 2 + ')' }, g);
        }
      }
    });

    function panneauMisePage() {
      var r = reglages(), corps = el('div', 'tpdf-mp');
      function bloc(titre) { var s = el('section', 'tpdf-section'); s.appendChild(el('h3', null, titre)); corps.appendChild(s); return s; }
      function lier(champ, obj, cle, conv) {
        var ev = champ.type === 'checkbox' ? 'change' : 'input';
        champ.addEventListener(ev, function () { obj[cle] = champ.type === 'checkbox' ? champ.checked : conv ? conv(champ.value) : champ.value; api.dessinerCalque(); });
      }
      var bn = bloc('Numérotation');
      var cn = coche('Numéroter les pages', r.numero.actif); lier(cn.input, r.numero, 'actif'); bn.appendChild(cn);
      var mn = texteChamp(r.numero.modele); lier(mn, r.numero, 'modele'); bn.appendChild(api.champ('Modèle ({n} page, {N} total)', mn));
      var pn = choix(POSITIONS, r.numero.position); lier(pn, r.numero, 'position'); bn.appendChild(api.champ('Position', pn));
      var be = bloc('En-tête et pied de page');
      be.appendChild(el('p', 'tpdf-aide', 'Variables : {n}, {N}, {date}, {nom}, {fichier}.'));
      ['entete', 'pied'].forEach(function (z) {
        var ligne = el('div', 'tpdf-ligne tpdf-ligne-esp');
        ['gauche', 'centre', 'droite'].forEach(function (k) {
          var t = texteChamp(r[z][k], z === 'entete' ? 'En-tête ' + k : 'Pied ' + k); lier(t, r[z], k);
          ligne.appendChild(api.champ((z === 'entete' ? 'Haut ' : 'Bas ') + k, t));
        });
        be.appendChild(ligne);
      });
      var bb = bloc('Numérotation Bates');
      var cb = coche('Numéros Bates', r.bates.actif); lier(cb.input, r.bates, 'actif'); bb.appendChild(cb);
      var lb = el('div', 'tpdf-ligne tpdf-ligne-esp');
      var pf = texteChamp(r.bates.prefixe, 'Préfixe'); lier(pf, r.bates, 'prefixe');
      var db = nombreChamp(r.bates.debut, 0, 99999999); lier(db, r.bates, 'debut', function (x) { return parseInt(x, 10) || 0; });
      var ch = nombreChamp(r.bates.chiffres, 1, 12); lier(ch, r.bates, 'chiffres', function (x) { return parseInt(x, 10) || 1; });
      lb.appendChild(api.champ('Préfixe', pf)); lb.appendChild(api.champ('Premier numéro', db)); lb.appendChild(api.champ('Chiffres', ch));
      bb.appendChild(lb);
      var pb = choix(POSITIONS, r.bates.position); lier(pb, r.bates, 'position'); bb.appendChild(api.champ('Position', pb));
      var bf = bloc('Filigrane');
      var cf = coche('Filigrane', r.filigrane.actif); lier(cf.input, r.filigrane, 'actif'); bf.appendChild(cf);
      var tf = choix([['texte', 'Texte'], ['image', 'Image']], r.filigrane.type);
      bf.appendChild(api.champ('Type', tf));
      var zt = el('div'), zi = el('div');
      var tx = texteChamp(r.filigrane.texte); lier(tx, r.filigrane, 'texte'); zt.appendChild(api.champ('Texte', tx));
      var tt = nombreChamp(r.filigrane.taille, 10, 200); lier(tt, r.filigrane, 'taille', parseFloat); zt.appendChild(api.champ('Taille', tt));
      var pal = el('div', 'tpdf-palette');
      api.COULEURS.forEach(function (c) {
        var b = el('button', 'tpdf-pastille' + (r.filigrane.couleur === c ? ' tpdf-actif' : '')); b.type = 'button';
        b.style.background = c; b.setAttribute('data-bulle', api.NOMS_COULEURS[c] || 'Couleur'); b.setAttribute('aria-label', 'Couleur ' + (api.NOMS_COULEURS[c] || c));
        b.addEventListener('click', function () { r.filigrane.couleur = c; pal.querySelectorAll('.tpdf-pastille').forEach(function (x) { x.classList.toggle('tpdf-actif', x === b); }); api.dessinerCalque(); });
        pal.appendChild(b);
      });
      zt.appendChild(api.champ('Couleur', pal));
      var fi = el('input'); fi.type = 'file'; fi.accept = 'image/png,image/jpeg'; fi.className = 'tpdf-champ';
      fi.addEventListener('change', async function () {
        var f = fi.files && fi.files[0]; if (!f) return;
        try { r.filigrane.image = await api.enregistrerImage(new Uint8Array(await f.arrayBuffer())); api.dessinerCalque(); }
        catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      });
      zi.appendChild(api.champ('Image (PNG ou JPG)', fi));
      var ec = nombreChamp(r.filigrane.echelle, 5, 100); lier(ec, r.filigrane, 'echelle', parseFloat); zi.appendChild(api.champ('Largeur (% de la page)', ec));
      bf.appendChild(zt); bf.appendChild(zi);
      var op = el('input'); op.type = 'range'; op.min = 0.05; op.max = 1; op.step = 0.05; op.value = r.filigrane.opacite; lier(op, r.filigrane, 'opacite', parseFloat);
      bf.appendChild(api.champ('Opacité', op));
      var an = nombreChamp(r.filigrane.angle, -180, 180, 5); lier(an, r.filigrane, 'angle', function (x) { return parseFloat(x) || 0; });
      bf.appendChild(api.champ('Angle (degrés)', an));
      function majType() { zt.hidden = tf.value !== 'texte'; zi.hidden = tf.value !== 'image'; r.filigrane.type = tf.value; api.dessinerCalque(); }
      tf.addEventListener('change', majType); majType();
      var bp = bloc('Pages concernées');
      var pv = texteChamp(r.pages === 'toutes' ? '' : r.pages === 'saufpremiere' ? '' : r.pages, '1-3, 5 (vide : toutes)');
      var sp = coche('Sauf la première page', r.pages === 'saufpremiere');
      function majPages() { r.pages = sp.input.checked ? 'saufpremiere' : (pv.value.trim() || 'toutes'); api.dessinerCalque(); }
      pv.addEventListener('input', majPages); sp.input.addEventListener('change', majPages);
      bp.appendChild(api.champ('Plages', pv)); bp.appendChild(sp);
      corps.appendChild(el('p', 'tpdf-aide', 'Aperçu sur la page affichée ; écrit dans le PDF à l\'enregistrement.'));
      api.ouvrirModale('Numéros, en-têtes, Bates, filigrane', corps, [
        { txt: 'Tout retirer', fn: function () { S().misePage = null; api.fermerModale(); api.dessinerCalque(); api.toast('Mise en page retirée.', 'info'); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'misepage', large: true });
    }
    EXT.actions.misepage = { fn: panneauMisePage };
    EXT.panneaux.misepage = panneauMisePage;

    /* ── Export page par page : format, puis mise en page ─────────────── */
    EXT.hooks.exportPageFin = (EXT.hooks.exportPageFin || []).concat(async function (pg, p, d, ctx, i, total) {
      var L = ctx.L;
      if (p.format && FORMATS[p.format]) {
        var box = pg.getCropBox(), aj = ajusterFormat(box, d.R, p.format);
        pg.scale(aj.k, aj.k);
        // pdf-lib referme la mise à l'échelle par un « Q » ajouté en fin de page :
        // un dessin fait ensuite dans le flux déjà ouvert serait lui aussi mis à
        // l'échelle. On force un flux neuf, placé après.
        pg.contentStream = undefined; pg.contentStreamRef = undefined;
        var b2 = pg.getCropBox();
        var x = b2.x - (aj.largeur - b2.width) / 2, y = b2.y - (aj.hauteur - b2.height) / 2;
        pg.setMediaBox(x, y, aj.largeur, aj.hauteur); pg.setCropBox(x, y, aj.largeur, aj.hauteur);
      }
      var r = S().misePage; if (!r || !actif(r)) return;
      var cb = pg.getCropBox(), view = [cb.x, cb.y, cb.x + cb.width, cb.y + cb.height];
      var W = d.R % 180 ? cb.height : cb.width, H = d.R % 180 ? cb.width : cb.height;
      var gris = L.rgb(0.2, 0.2, 0.2);
      var els = elements(r, i, total);
      for (var k = 0; k < els.length; k++) {
        var e = els[k], font = await ctx.pol.police(e.texte, {}), t = api.nettoyerTexte(font, e.texte);
        var o = positionTexte(e.position, W, H, r.marge, font.widthOfTextAtSize(t, e.taille), e.taille);
        var q = api.versPdf(view, d.R, o.x, o.y);
        pg.drawText(t, { x: q[0], y: q[1], size: e.taille, font: font, color: gris, rotate: L.degrees(d.R) });
      }
      var f = r.filigrane;
      if (!f.actif || !pageVisee(r.pages, i, total, api.lirePlages)) return;
      if (f.type === 'texte' && f.texte) {
        var fb = await ctx.pol.police(f.texte, { gras: true }), ft = api.nettoyerTexte(fb, f.texte);
        var w = fb.widthOfTextAtSize(ft, f.taille), o2 = origineTournee(W / 2, H / 2, w, f.taille * 0.72, f.angle);
        var q2 = api.versPdf(view, d.R, o2.x, o2.y), c = api.hexRgb(f.couleur);
        pg.drawText(ft, { x: q2[0], y: q2[1], size: f.taille, font: fb, color: L.rgb(c[0], c[1], c[2]), opacity: f.opacite, rotate: L.degrees(f.angle + d.R) });
      } else if (f.type === 'image' && f.image) {
        var im = S().images[f.image]; if (!im) return;
        ctx.imgFil = ctx.imgFil || {};
        var emb = ctx.imgFil[f.image] || (ctx.imgFil[f.image] = im.type === 'png' ? await ctx.out.embedPng(im.bytes) : await ctx.out.embedJpg(im.bytes));
        var iw = W * f.echelle / 100, ih = iw * im.h / im.w, o3 = origineTournee(W / 2, H / 2, iw, ih, f.angle);
        var q3 = api.versPdf(view, d.R, o3.x, o3.y);
        pg.drawImage(emb, { x: q3[0], y: q3[1], width: iw, height: ih, opacity: f.opacite, rotate: L.degrees(f.angle + d.R) });
      }
    });
    // Pastille du format sur la vignette.
    EXT.hooks.vignette = (EXT.hooks.vignette || []).concat(function (p, v) {
      if (!p.format && !p.crop) return;
      var pied = v.querySelector('.tpdf-vig-pied'); if (!pied) return;
      var e = el('span', 'tpdf-vig-format', p.format ? FORMATS[p.format][2] : '');
      if (p.crop) { e.appendChild(document.createRange().createContextualFragment(api.ico('recadrer', 11))); }
      e.setAttribute('data-bulle', p.format ? 'Format ' + FORMATS[p.format][2] : 'Recadrée');
      pied.appendChild(e);
    });

    /* ── Compression ──────────────────────────────────────────────────── */
    // Rééchantillonne les images d'un PDF (JPEG et images brutes 8 bits RVB
    // ou gris) ; le texte et le vectoriel restent intacts.
    async function optimiserImages(octets, dpi, qualite, suivi) {
      var L = await api.pdflib(), d = await L.PDFDocument.load(octets, { updateMetadata: false }), N = L.PDFName;
      var cote = 0;
      d.getPages().forEach(function (pg) { var s = pg.getSize(); cote = Math.max(cote, s.width, s.height); });
      var limite = Math.ceil(cote / 72 * dpi), images = [], gain = 0, n = 0;
      d.context.enumerateIndirectObjects().forEach(function (x) {
        var o = x[1];
        if (o instanceof L.PDFRawStream && String(o.dict.get(N.of('Subtype'))) === '/Image') images.push(x);
      });
      function num(v) { v = v && d.context.lookup(v); return v && v.asNumber ? v.asNumber() : null; }
      // Un prédicteur PNG/TIFF (> 1) n'est pas décodé ici : image laissée telle quelle.
      function predicteur(dict) { var dp = d.context.lookup(dict.get(N.of('DecodeParms'))); return dp instanceof L.PDFDict && (num(dp.get(N.of('Predictor'))) || 1) > 1; }
      for (var i = 0; i < images.length; i++) {
        if (suivi) suivi(i + 1, images.length);
        var ref = images[i][0], o = images[i][1], dict = o.dict;
        if (dict.get(N.of('ImageMask')) || dict.get(N.of('Decode'))) continue;
        var W = num(dict.get(N.of('Width'))), H = num(dict.get(N.of('Height'))), bpc = num(dict.get(N.of('BitsPerComponent')));
        var filtre = dict.get(N.of('Filter')), nf = filtre ? String(filtre instanceof L.PDFArray ? (filtre.size() === 1 ? filtre.get(0) : '') : filtre) : '';
        var cs = d.context.lookup(dict.get(N.of('ColorSpace'))), comp = null;
        if (cs instanceof L.PDFName) comp = { '/DeviceRGB': 3, '/DeviceGray': 1 }[String(cs)] || null;
        else if (cs instanceof L.PDFArray && String(cs.get(0)) === '/ICCBased') { var icc = d.context.lookup(cs.get(1)); comp = icc ? num(icc.dict.get(N.of('N'))) : null; if (comp !== 1 && comp !== 3) comp = null; }
        if (!W || !H) continue;
        var source = null;
        try {
          if (nf === '/DCTDecode' && comp) {
            source = await createImageBitmap(new Blob([o.contents], { type: 'image/jpeg' }));
          } else if ((nf === '/FlateDecode' || nf === '') && comp && bpc === 8 && !predicteur(dict)) {
            var brut = L.decodePDFRawStream(o).decode();
            if (brut.length < W * H * comp) continue;
            var c0 = document.createElement('canvas'); c0.width = W; c0.height = H;
            var id = c0.getContext('2d').createImageData(W, H);
            for (var k = 0, j = 0; k < W * H; k++, j += comp) {
              id.data[k * 4] = brut[j]; id.data[k * 4 + 1] = brut[comp === 3 ? j + 1 : j]; id.data[k * 4 + 2] = brut[comp === 3 ? j + 2 : j]; id.data[k * 4 + 3] = 255;
            }
            c0.getContext('2d').putImageData(id, 0, 0);
            source = c0;
          } else continue;
        } catch (e) { continue; }
        var s = Math.min(1, limite / Math.max(W, H)), W2 = Math.max(1, Math.round(W * s)), H2 = Math.max(1, Math.round(H * s));
        var cv = document.createElement('canvas'); cv.width = W2; cv.height = H2;
        var cx = cv.getContext('2d'); cx.fillStyle = 'white'; cx.fillRect(0, 0, W2, H2); cx.drawImage(source, 0, 0, W2, H2);
        var blob = await new Promise(function (ok) { cv.toBlob(ok, 'image/jpeg', qualite); });
        var jpg = new Uint8Array(await blob.arrayBuffer());
        if (jpg.length >= o.contents.length * 0.92) continue;
        var nd = { Type: 'XObject', Subtype: 'Image', Width: W2, Height: H2, ColorSpace: 'DeviceRGB', BitsPerComponent: 8, Filter: 'DCTDecode' };
        var flux = d.context.stream(jpg, nd);
        var sm = dict.get(N.of('SMask')); if (sm) flux.dict.set(N.of('SMask'), sm);
        d.context.assign(ref, flux);
        gain += o.contents.length - jpg.length; n++;
      }
      return { octets: await d.save({ useObjectStreams: true }), images: images.length, reduites: n, gain: gain };
    }
    M._interne.pages.optimiserImages = optimiserImages;

    function panneauCompresser() {
      var s = S(), corps = el('div');
      var mode = choix([['images', 'Réduire les images (texte conservé)'], ['pages', 'Pages en image (scans)']], 'images');
      var dpi = choix([['72', '72 dpi (écran)'], ['100', '100 dpi'], ['150', '150 dpi'], ['200', '200 dpi']], '150');
      var q = el('input'); q.type = 'range'; q.min = 30; q.max = 95; q.step = 5; q.value = 70;
      var qv = el('b', null, '70'); q.addEventListener('input', function () { qv.textContent = q.value; });
      var lq = api.champ('Qualité JPEG', q); lq.querySelector('.tpdf-lab').appendChild(document.createTextNode(' ')); lq.querySelector('.tpdf-lab').appendChild(qv);
      corps.appendChild(api.champ('Méthode', mode)); corps.appendChild(api.champ('Résolution maximale', dpi)); corps.appendChild(lq);
      var aide = el('p', 'tpdf-aide'); corps.appendChild(aide);
      var res = el('div', 'tpdf-resultat'); corps.appendChild(res);
      function maj() {
        aide.textContent = mode.value === 'images'
          ? 'Les images trop fines pour la page sont rééchantillonnées en JPEG ; texte, vectoriel et formulaires restent intacts.'
          : 'Chaque page devient une image : texte non sélectionnable, champs aplatis. Pour les scans lourds.';
      }
      mode.addEventListener('change', maj); maj();
      var m = api.ouvrirModale('Compresser', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Compresser et télécharger', plein: true, cle: 'go', fn: async function () {
          var go = m.pied.querySelector('[data-cle="go"]'); go.disabled = true;
          var ids = {}; s.pages.forEach(function (p) { ids[p.src] = 1; });
          var avant = Object.keys(ids).reduce(function (t, id) { return t + s.sources[id].bytes.length; }, 0);
          res.textContent = 'Compression en cours…'; api.occuper('Compression…');
          try {
            var b = await api.construire(), qual = parseInt(q.value, 10) / 100, d = parseInt(dpi.value, 10), info = '';
            if (mode.value === 'images') {
              var r = await optimiserImages(b, d, qual, function (i, n) { res.textContent = 'Images : ' + i + ' / ' + n + '…'; });
              b = r.octets; info = ' · ' + r.reduites + ' image' + (r.reduites > 1 ? 's réduites' : ' réduite') + ' sur ' + r.images;
            } else {
              b = await api.rasteriser(b, d, qual, function (i, n) { res.textContent = 'Page ' + i + ' / ' + n + '…'; });
            }
            var gain = avant ? Math.min(99, Math.round((1 - b.length / avant) * 100)) : 0;
            res.textContent = 'Avant : ' + api.tailleLisible(avant) + ' → Après : ' + api.tailleLisible(b.length) + (gain > 0 ? ' (−' + gain + ' %)' : '') + info;
            if (gain <= 0) { res.textContent += ' — rien à gagner, fichier non téléchargé.'; api.toast('Pas de gain sur ce document.', 'info'); }
            else { api.telecharger(b, api.nomBase() + '-compresse.pdf'); api.toast('PDF compressé — ' + gain + ' % de moins.', 'success'); }
          } catch (e) { res.textContent = ''; api.toast(api.msgErreur(e), 'danger'); }
          finally { api.liberer(); go.disabled = false; }
        } }
      ], { cle: 'compresser' });
    }
    EXT.actions.compresser = { fn: panneauCompresser };
    EXT.panneaux.compresser = panneauCompresser;

    /* ── Export image / Word ──────────────────────────────────────────── */
    function telechargerBlob(blob, nom) {
      var u = api.urlObjet(blob), a = el('a'); a.href = u; a.download = nom; a.style.display = 'none';
      S().el.appendChild(a); a.click(); a.remove();
    }
    function panneauExporter() {
      var s = S(), corps = el('div');
      var fmt = choix([['png', 'Image PNG'], ['jpg', 'Image JPG'], ['docx', 'Word (.docx)']], 'png');
      var dpi = choix([['100', '100 dpi'], ['150', '150 dpi'], ['200', '200 dpi'], ['300', '300 dpi']], '150');
      var pages = choix([['courante', 'Page courante'], ['selection', 'Pages sélectionnées'], ['toutes', 'Toutes les pages']], 'courante');
      var ld = api.champ('Résolution', dpi), lp = api.champ('Pages', pages);
      corps.appendChild(api.champ('Format', fmt)); corps.appendChild(ld); corps.appendChild(lp);
      var aide = el('p', 'tpdf-aide'); corps.appendChild(aide);
      function maj() {
        var w = fmt.value === 'docx'; ld.hidden = w; lp.hidden = w;
        aide.textContent = w ? 'Le PDF est envoyé au serveur MySifa pour la conversion (outil Convertir). Pour un tableau en CSV : IA › Extraire des données.'
          : 'Une image par page, calculée sur ce poste.';
      }
      fmt.addEventListener('change', maj); maj();
      api.ouvrirModale('Exporter', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Exporter', plein: true, fn: async function () {
          api.fermerModale(); api.occuper('Export…');
          try {
            if (fmt.value === 'docx') {
              var b = await api.construire(), fd = new FormData();
              fd.append('cible', 'docx'); fd.append('options', '{}');
              fd.append('fichiers', new Blob([b], { type: 'application/pdf' }), api.nomBase() + '.pdf');
              var r = await fetch('/api/tools/convertir', { method: 'POST', body: fd, credentials: 'same-origin' });
              if (!r.ok) { var j = null; try { j = await r.json(); } catch (e) { j = null; } throw new Error((j && j.detail) || ('conversion refusée (' + r.status + ')')); }
              telechargerBlob(await r.blob(), api.nomBase() + '.docx');
              api.toast('Document Word téléchargé.', 'success');
              return;
            }
            var l = pages.value === 'toutes' ? s.pages : pages.value === 'selection' ? api.pagesCiblees() : [api.pageCourante()];
            var octets = await api.construire(l), pj = await api.pdfjs();
            var doc = await pj.getDocument({ data: octets.slice(), isEvalSupported: false }).promise, k = parseInt(dpi.value, 10) / 72;
            try {
              for (var i = 1; i <= doc.numPages; i++) {
                var pg = await doc.getPage(i), vp = pg.getViewport({ scale: k }), cv = el('canvas');
                cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
                var c = cv.getContext('2d'); c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
                await pg.render({ canvasContext: c, viewport: vp, intent: 'print' }).promise;
                var blob = await new Promise(function (ok) { cv.toBlob(ok, fmt.value === 'png' ? 'image/png' : 'image/jpeg', 0.9); });
                telechargerBlob(blob, api.nomBase() + '-p' + (s.pages.indexOf(l[i - 1]) + 1) + '.' + fmt.value);
                await new Promise(function (r2) { setTimeout(r2, 300); });
              }
            } finally { try { doc.destroy(); } catch (e) { /* déjà libéré */ } }
            api.toast(l.length + ' image' + (l.length > 1 ? 's téléchargées.' : ' téléchargée.'), 'success');
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
          finally { api.liberer(); }
        } }
      ], { cle: 'exporter' });
    }
    EXT.actions.exporter = { fn: panneauExporter };
    EXT.panneaux.exporter = panneauExporter;

    /* ── Envoyer à signer (parapheur, autre module) ───────────────────── */
    EXT.actions.parapheur = { fn: async function () {
      if (!window.MyToolsParapheur && api.MON_SRC) {
        try { await api.chargerScript(api.MON_SRC.replace(/mysifa_tools_pdf\.js/, 'mysifa_tools_parapheur.js')); } catch (e) { /* signalé ci-dessous */ }
      }
      if (!window.MyToolsParapheur || typeof window.MyToolsParapheur.ouvrir !== 'function') {
        api.toast('Parapheur indisponible pour le moment.', 'info'); return;
      }
      api.occuper('Préparation…');
      try { var b = await api.construire(); window.MyToolsParapheur.ouvrir({ octets: b, nom: api.nomBase() + '.pdf' }); }
      catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      finally { api.liberer(); }
    } };
  });
})();
