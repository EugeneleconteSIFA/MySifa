/*
 * MyTools — éditeur PDF (lot 1).
 *
 * Tout se passe dans le navigateur : aucun octet ne part vers le serveur.
 * pdf.js (rendu, vignettes, recherche) et pdf-lib (écriture) sont chargés à la
 * demande depuis cdnjs, au premier fichier ouvert.
 *
 * Contrat de montage :
 *   window.MyToolsPDF.mount(root, ctx)   ctx = { toast(msg, type), surChange(etat) }
 *   window.MyToolsPDF.demonter()
 *   window.MyToolsPDF.adresse = { etat(), aller(a), cles: ['page'] }
 *
 * Coordonnées : une annotation est rangée en points PDF dans le repère de la
 * page TELLE QU'AFFICHÉE (origine en haut à gauche, rotation appliquée). Le
 * zoom n'y entre jamais : l'overlay SVG porte un viewBox en points. La
 * conversion vers l'espace utilisateur PDF (origine en bas à gauche, page non
 * pivotée) se fait à l'export par versPdf().
 */
(function () {
  'use strict';

  var CDN_PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/';
  var URL_PDFJS = CDN_PDFJS + 'pdf.min.mjs';
  var URL_WORKER = CDN_PDFJS + 'pdf.worker.min.mjs';
  var URL_PDFLIB = 'https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js';

  /* Couleurs proposées à l'utilisateur pour ses annotations : ce sont des
     données (elles finissent dans le PDF), pas des couleurs d'interface. */
  var COULEURS = ['#d92626', '#e8590c', '#f2b705', '#2f9e44', '#1971c2', '#7048e8', '#1a1a1a', '#ffffff'];
  var ENCRES = ['#1a1a1a', '#1c3f94'];
  var TAMPONS = ['Approuvé', 'Refusé', 'BAT validé', 'Copie', 'Confidentiel'];
  var COULEUR_TAMPON = { 'Approuvé': '#2f9e44', 'Refusé': '#d92626', 'BAT validé': '#2f9e44', 'Copie': '#1971c2', 'Confidentiel': '#d92626' };
  var ASC = 0.78, INTERLIGNE = 1.2;
  var CLE_SIGNATURE = 'mytools_pdf_signature';
  var ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3];
  var NS = 'http://www.w3.org/2000/svg';
  var POLICE = 'Helvetica, Arial, sans-serif';
  var OUTILS_TRACE = { surligneur: 1, rect: 1, ellipse: 1, ligne: 1, fleche: 1, main: 1, texte: 1, tampon: 1 };
  var AIDE_OUTIL = {
    select: 'Cliquer une annotation pour la sélectionner, la déplacer ou la redimensionner.',
    texte: 'Cliquer sur la page pour poser un texte.',
    surligneur: 'Cliquer-glisser sur la zone à surligner.',
    rect: 'Cliquer-glisser pour tracer un rectangle. Maj : carré.',
    ellipse: 'Cliquer-glisser pour tracer une ellipse. Maj : cercle.',
    ligne: 'Cliquer-glisser pour tracer une ligne. Maj : angle de 45°.',
    fleche: 'Cliquer-glisser pour tracer une flèche. Maj : angle de 45°.',
    main: 'Dessiner librement sur la page.',
    tampon: 'Cliquer sur la page pour poser le tampon.'
  };
  var LIBELLES = {
    texte: 'Texte', surligneur: 'Surlignage', rect: 'Rectangle', ellipse: 'Ellipse', ligne: 'Ligne',
    fleche: 'Flèche', main: 'Trait libre', tampon: 'Tampon', image: 'Image'
  };

  /* ── Icônes : dessinées à la main, grille 24, currentColor ─────────── */
  var IC = {
    ouvrir: '<path d="M3.5 7.5V6a2 2 0 0 1 2-2h3.6l2 2H18a2 2 0 0 1 2 2v1"/><path d="M3.5 18.5l2.3-7.1A2 2 0 0 1 7.7 10H20.6a1 1 0 0 1 .95 1.3l-2 6.3A2 2 0 0 1 17.65 19H5.5a2 2 0 0 1-2-2V7.5"/>',
    enregistrer: '<path d="M12 4v10.5"/><path d="M7.5 10.5L12 15l4.5-4.5"/><path d="M5 19.5h14"/>',
    imprimer: '<path d="M7 9V4.5h10V9"/><rect x="3.5" y="9" width="17" height="7.5" rx="2"/><path d="M7 14h10v5.5H7z"/>',
    annuler: '<path d="M9 13.5L4.5 9 9 4.5"/><path d="M4.5 9h10a5 5 0 0 1 0 10H11"/>',
    retablir: '<path d="M15 13.5L19.5 9 15 4.5"/><path d="M19.5 9h-10a5 5 0 0 0 0 10H13"/>',
    select: '<path d="M6 3.5l12.5 7-5.6 1.6-2.1 5.4z"/><path d="M12.9 12.1l4.6 5.4"/>',
    texte: '<path d="M5.5 7V4.5h13V7"/><path d="M12 4.5v15"/><path d="M9 19.5h6"/>',
    surligneur: '<path d="M14.8 4.2l5 5-8.3 8.3H6.5v-5z"/><path d="M12.3 6.7l5 5"/><path d="M4 20.5h16"/>',
    rect: '<rect x="4" y="6" width="16" height="12" rx="1.5"/>',
    ellipse: '<ellipse cx="12" cy="12" rx="8.5" ry="6.5"/>',
    ligne: '<path d="M5 19L19 5"/>',
    fleche: '<path d="M5 19L18.5 5.5"/><path d="M10.5 5h8.5v8.5"/>',
    main: '<path d="M3.5 16c2.2-4.6 4.2-7.4 5.8-6.4 1.7 1-1.4 5.3.6 6.2 2 .9 4.1-6.3 6.2-6 1.8.3.9 3.6 4.4 4.2"/>',
    tampon: '<path d="M9.5 4h5l-.9 7h-3.2z"/><path d="M5 14a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v2H5z"/><path d="M6 20h12"/>',
    image: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 17.5l5-4.5 3.5 3 3-2.5 4.5 4"/>',
    signature: '<path d="M3.5 16.5c2.8 0 3.8-9 6-9s-.2 8.5 2 8.5c1.6 0 2.2-3 3.6-3 1.2 0 .9 2.2 2.4 2.2 1 0 1.6-.8 3-1.6"/><path d="M3.5 20h17"/>',
    pivg: '<path d="M4 4.5v5h5"/><path d="M4.8 9.5A7.8 7.8 0 1 1 6.3 17"/>',
    pivd: '<path d="M20 4.5v5h-5"/><path d="M19.2 9.5A7.8 7.8 0 1 0 17.7 17"/>',
    dupliquer: '<rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2"/><path d="M15.5 8.5V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7.5a2 2 0 0 0 2 2h2.5"/>',
    blanche: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 11.5v6M9 14.5h6"/>',
    supprimer: '<path d="M4.5 7h15"/><path d="M9.5 4h5"/><path d="M6.5 7l.9 12.5a1 1 0 0 0 1 .9h7.2a1 1 0 0 0 1-.9L17.5 7"/><path d="M10 11v5.5M14 11v5.5"/>',
    extraire: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 17.5v-6.5M9.3 13.5L12 10.8l2.7 2.7"/>',
    decouper: '<circle cx="6.5" cy="7" r="2.5"/><circle cx="6.5" cy="17" r="2.5"/><path d="M8.6 8.4L20 16.5M8.6 15.6L20 7.5"/>',
    compresser: '<path d="M12 3v6M9 6l3 3 3-3"/><path d="M12 21v-6M9 18l3-3 3 3"/><path d="M4.5 12h15"/>',
    formulaire: '<rect x="4" y="3.5" width="16" height="17" rx="2"/><rect x="7.5" y="7" width="9" height="3" rx=".8"/><path d="M7.5 14h9M7.5 17h5"/>',
    zmoins: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8M7.8 10.5h5.4"/>',
    zplus: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8M7.8 10.5h5.4M10.5 7.8v5.4"/>',
    prec: '<path d="M14.5 5.5L8 12l6.5 6.5"/>',
    suiv: '<path d="M9.5 5.5L16 12l-6.5 6.5"/>',
    haut: '<path d="M6 14.5l6-6 6 6"/>',
    bas: '<path d="M6 9.5l6 6 6-6"/>',
    chercher: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8"/>',
    reglages: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    fermer: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    depot: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 11v6.5M9.3 14.8L12 17.5l2.7-2.7"/>'
  };
  function ico(n, t) {
    t = t || 18;
    return '<svg width="' + t + '" height="' + t + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (IC[n] || '') + '</svg>';
  }

  /* ── Bibliothèques, chargées à la demande ──────────────────────────── */
  var _pdfjs = null, _pdflib = null;
  function pdfjs() {
    if (!_pdfjs) {
      _pdfjs = import(URL_PDFJS).then(function (m) {
        m.GlobalWorkerOptions.workerSrc = URL_WORKER;
        return m;
      }, function () { _pdfjs = null; throw new Error('bibli'); });
    }
    return _pdfjs;
  }
  function pdflib() {
    if (window.PDFLib) return Promise.resolve(window.PDFLib);
    if (!_pdflib) {
      _pdflib = new Promise(function (ok, ko) {
        var s = document.createElement('script');
        s.src = URL_PDFLIB; s.async = true;
        s.onload = function () { if (window.PDFLib) ok(window.PDFLib); else { _pdflib = null; ko(new Error('bibli')); } };
        s.onerror = function () { _pdflib = null; ko(new Error('bibli')); };
        document.head.appendChild(s);
      });
    }
    return _pdflib;
  }

  /* ── Fonctions pures (testées dans tests/test_tools_pdf.js) ───────── */

  // Point de la page affichée (u, v en points, origine haut-gauche) vers
  // l'espace utilisateur PDF. view = [x0, y0, x1, y1], R = rotation affichée.
  function versPdf(view, R, u, v) {
    var x0 = view[0], y0 = view[1], x1 = view[2], y1 = view[3];
    switch (R) {
      case 90: return [x0 + v, y0 + u];
      case 180: return [x1 - u, y0 + v];
      case 270: return [x1 - v, y1 - u];
      default: return [x0 + u, y1 - v];
    }
  }
  function versVue(view, R, X, Y) {
    var x0 = view[0], y0 = view[1], x1 = view[2], y1 = view[3];
    switch (R) {
      case 90: return [Y - y0, X - x0];
      case 180: return [x1 - X, Y - y0];
      case 270: return [y1 - Y, x1 - X];
      default: return [X - x0, y1 - Y];
    }
  }
  // Rotation d'un point quand la page pivote d'un quart de tour.
  // W, H : dimensions affichées AVANT la rotation ; sens +1 horaire, -1 antihoraire.
  function tournerPoint(u, v, W, H, sens) {
    return sens > 0 ? [H - v, u] : [v, W - u];
  }
  // « 1-3, 5, 8-10 » -> [{a:1,b:3},{a:5,b:5},{a:8,b:10}] (numéros 1-based)
  function lirePlages(txt, n) {
    var parts = String(txt || '').split(/[,;]+/).map(function (s) { return s.trim(); }).filter(Boolean);
    if (!parts.length) throw new Error('Plage vide — exemple : 1-3, 5, 8-10.');
    return parts.map(function (part) {
      var m = /^(\d+)\s*(?:[-–]\s*(\d+))?$/.exec(part);
      if (!m) throw new Error('Plage invalide « ' + part + ' » — exemple : 1-3, 5, 8-10.');
      var a = parseInt(m[1], 10), b = m[2] ? parseInt(m[2], 10) : a;
      if (a > b) throw new Error('Plage à l\'envers « ' + part + ' » — écrire ' + b + '-' + a + '.');
      if (a < 1) throw new Error('La numérotation commence à 1.');
      if (b > n) throw new Error('Page ' + b + ' hors du document (' + n + ' page' + (n > 1 ? 's' : '') + ').');
      return { a: a, b: b };
    });
  }
  // Groupes de N pages consécutives : [{a, b}] (numéros 1-based).
  function groupesParN(total, n) {
    n = parseInt(n, 10);
    if (!(n >= 1)) throw new Error('Nombre de pages invalide — au moins 1.');
    var g = [];
    for (var a = 1; a <= total; a += n) g.push({ a: a, b: Math.min(total, a + n - 1) });
    return g;
  }
  // Déplace les éléments sélectionnés pour qu'ils s'insèrent avant la position
  // `cible` du tableau d'origine (cible = longueur : à la fin).
  function deplacerSelection(liste, estSel, cible) {
    var sel = [], reste = [], avant = 0;
    liste.forEach(function (x, i) {
      if (estSel(x)) sel.push(x);
      else { if (i < cible) avant++; reste.push(x); }
    });
    if (!sel.length) return liste.slice();
    return reste.slice(0, avant).concat(sel, reste.slice(avant));
  }
  function normaliser(s) {
    return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }
  function tailleLisible(n) {
    if (n < 1024) return n + ' o';
    if (n < 1024 * 1024) return Math.round(n / 1024) + ' Ko';
    return (n / 1048576).toFixed(1).replace('.', ',') + ' Mo';
  }
  function hexRgb(h) {
    var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(h || '');
    if (!m) return [0, 0, 0];
    return [parseInt(m[1], 16) / 255, parseInt(m[2], 16) / 255, parseInt(m[3], 16) / 255];
  }
  function sansExt(n) { return String(n || 'document').replace(/\.[a-z0-9]{2,4}$/i, '') || 'document'; }
  function nomFichierSur(n) { return String(n || 'document').replace(/[\\/:*?"<>|]+/g, '-').trim() || 'document'; }
  function typeImage(b) {
    if (b && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'png';
    if (b && b[0] === 0xff && b[1] === 0xd8) return 'jpg';
    return null;
  }
  function pointesFleche(a) {
    var ang = Math.atan2(a.y2 - a.y1, a.x2 - a.x1), L = Math.max(8, a.ep * 4), o = 0.45;
    return [[a.x2, a.y2],
      [a.x2 - L * Math.cos(ang - o), a.y2 - L * Math.sin(ang - o)],
      [a.x2 - L * Math.cos(ang + o), a.y2 - L * Math.sin(ang + o)]];
  }

  /* ── Extensions (texte existant, formulaires, création) ───────────── */
  // Chargées par ce fichier, avec la même querystring de version que lui.
  var MON_SRC = (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) || '';
  var EXTENSIONS = ['mysifa_tools_pdf_texte.js', 'mysifa_tools_pdf_formulaires.js', 'mysifa_tools_pdf_creation.js', 'mysifa_tools_pdf_flou.js',
    'mysifa_tools_pdf_pages.js', 'mysifa_tools_pdf_revision.js', 'mysifa_tools_pdf_securite.js', 'mysifa_tools_pdf_ocr.js', 'mysifa_tools_pdf_ia.js',
    'mysifa_tools_pdf_navigation.js', 'mysifa_tools_pdf_mesure.js', 'mysifa_tools_pdf_prepresse.js', 'mysifa_tools_pdf_formavance.js',
    'mysifa_tools_pdf_contenu.js', 'mysifa_tools_pdf_lot.js', 'mysifa_tools_pdf_partage.js'];
  // menus : groupes de la barre (Pages, Réviser, Protéger, IA) ; panneaux :
  // fenêtres qui ont une adresse (clé « panneau » de l'URL).
  var EXT = { types: {}, outils: {}, actions: {}, hooks: {}, boutons: [], modeAnnot: null, docPourExport: null,
    menus: {}, panneaux: {} };
  function hook(nom) {
    var args = Array.prototype.slice.call(arguments, 1);
    (EXT.hooks[nom] || []).forEach(function (fn) {
      try { fn.apply(null, args); } catch (e) { if (window.console) console.error(e); }
    });
  }
  async function hookAsync(nom) {
    var args = Array.prototype.slice.call(arguments, 1), l = EXT.hooks[nom] || [];
    for (var i = 0; i < l.length; i++) await l[i].apply(null, args);
  }
  function chargerScript(url) {
    return new Promise(function (ok, ko) {
      var s = document.createElement('script');
      s.src = url; s.async = true;
      s.onload = function () { ok(); };
      s.onerror = function () { ko(new Error('bibli')); };
      document.head.appendChild(s);
    });
  }
  var _extCharge = null;
  function chargerExtensions() {
    if (_extCharge) return _extCharge;
    if (!MON_SRC) return Promise.resolve();
    _extCharge = Promise.all(EXTENSIONS.map(function (f) {
      return chargerScript(MON_SRC.replace(/mysifa_tools_pdf\.js/, f)).catch(function () {
        if (window.console) console.warn('[MyTools PDF] extension indisponible : ' + f);
      });
    }));
    return _extCharge;
  }

  /* ── Polices : standard tant que possible, Unicode si le texte l'exige ── */
  var URL_FONTKIT = 'https://cdn.jsdelivr.net/npm/@pdf-lib/fontkit@1.1.1/dist/fontkit.umd.min.js';
  var URL_NOTO = 'https://cdn.jsdelivr.net/npm/@expo-google-fonts/noto-sans@0.2.3/NotoSans_';
  var _fontkit = null, _noto = {};
  function fontkit() {
    if (window.fontkit) return Promise.resolve(window.fontkit);
    if (!_fontkit) {
      _fontkit = chargerScript(URL_FONTKIT).then(function () {
        if (!window.fontkit) throw new Error('bibli');
        return window.fontkit;
      }, function (e) { _fontkit = null; throw e; });
    }
    return _fontkit;
  }
  function octetsNoto(gras) {
    var k = gras ? '700Bold' : '400Regular';
    if (!_noto[k]) {
      _noto[k] = fetch(URL_NOTO + k + '.ttf').then(function (r) {
        if (!r.ok) throw new Error('police');
        return r.arrayBuffer();
      }).catch(function (e) { _noto[k] = null; throw e; });
    }
    return _noto[k];
  }
  // {famille: 'sans'|'serif'|'mono', gras, italique} -> clé de StandardFonts (pdf-lib)
  function cleStandard(st) {
    st = st || {};
    var f = st.famille === 'serif' ? 'TimesRoman' : st.famille === 'mono' ? 'Courier' : 'Helvetica';
    var it = f === 'TimesRoman' ? 'Italic' : 'Oblique';
    return f + (st.gras && st.italique ? 'Bold' + it : st.gras ? 'Bold' : st.italique ? it : '');
  }
  function encodable(font, s) { try { font.encodeText(s); return true; } catch (e) { return false; } }
  async function policePour(c, txt, st) {
    var k = cleStandard(st);
    if (!c.std[k]) c.std[k] = await c.out.embedFont(c.L.StandardFonts[k]);
    if (encodable(c.std[k], String(txt || '').replace(/[\r\n]/g, ''))) return c.std[k];
    var g = st && st.gras ? 1 : 0;
    if (!c.uni[g]) {
      try {
        var fk = await fontkit();
        c.out.registerFontkit(fk);
        // Police entière : le sous-ensemble de pdf-lib perd des glyphes avec
        // cette police (vérifié : « Œuvre » sortait « Œuv »). ~550 Ko de plus,
        // seulement quand le texte sort de WinAnsi.
        c.uni[g] = await c.out.embedFont(await octetsNoto(g), { subset: false });
      } catch (e) {
        c.uni[g] = c.std[k];
        toast('Police Unicode indisponible — caractères spéciaux remplacés par « ? ».', 'info');
      }
    }
    return c.uni[g];
  }

  /* ── État ─────────────────────────────────────────────────────────── */
  var S = null;
  var _n = 0;
  function nid(p) { return (p || 'a') + (++_n).toString(36) + Math.random().toString(36).slice(2, 6); }

  function etatNeuf(root, ctx) {
    return {
      root: root, ctx: ctx || {}, el: null,
      sources: {}, images: {}, pages: [], cur: 0,
      sel: {}, ancre: null, outil: 'select', annSel: null,
      zoom: 'fit', nom: '', aplatir: true,
      style: { couleur: COULEURS[0], ep: 2, taille: 14, opacite: 0.35, tampon: TAMPONS[0], date: true, signataire: true },
      hist: [], redo: [], drag: null, propAvant: null,
      vigCache: {}, vigAttente: {}, vigFile: Promise.resolve(),
      textes: {}, rech: { q: '', res: [], i: -1 }, rechJeton: 0,
      jeton: 0, tache: null, occupe: false, modale: null,
      urls: [], blancs: {}, pageDemandee: null, ro: null, ecoute: null
    };
  }

  function toast(m, t) {
    try { if (S && S.ctx && typeof S.ctx.toast === 'function') return S.ctx.toast(m, t || 'info'); } catch (e) { /* toast de la page indisponible */ }
    if (window.console) console.log('[MyTools PDF] ' + m);
  }
  function msgErreur(e) {
    var m = e && e.message;
    if (m === 'bibli') return 'Bibliothèque PDF indisponible — vérifiez la connexion internet.';
    if (m === 'chiffre') return 'PDF protégé (chiffré ou par mot de passe) — retirez la protection avant de l\'ouvrir ici.';
    if (m === 'invalide') return 'Fichier illisible — ce n\'est pas un PDF valide.';
    if (m === 'image') return 'Image illisible — PNG ou JPG attendu.';
    // Message déjà rédigé (phrase finie, ex. détail renvoyé par le serveur) : tel quel.
    if (m && /[.!?]$/.test(m) && /^[A-ZÀ-Ý]/.test(m)) return m;
    return 'Opération impossible — ' + (m || 'erreur inconnue') + '.';
  }
  function notifier() {
    try { if (S && S.ctx && typeof S.ctx.surChange === 'function') S.ctx.surChange(etatAdresse()); } catch (e) { /* page sans suivi d'adresse */ }
  }
  function etatAdresse() {
    if (!S || !S.pages.length) return {};
    var e = { page: String(S.cur + 1) };
    if (S.modaleCle) e.panneau = S.modaleCle;
    return e;
  }

  function snapshot() { return JSON.stringify({ pages: S.pages, cur: S.cur }); }
  function pushHist(avant) {
    S.hist.push(avant);
    if (S.hist.length > 80) S.hist.shift();
    S.redo = [];
  }
  function restaurer(str) {
    var o = JSON.parse(str);
    S.pages = o.pages; S.cur = Math.min(o.cur, Math.max(0, S.pages.length - 1));
    var uids = {}; S.pages.forEach(function (p) { uids[p.uid] = 1; });
    Object.keys(S.sel).forEach(function (k) { if (!uids[k]) delete S.sel[k]; });
    S.annSel = null;
  }
  function annuler() {
    if (!S.hist.length) return;
    S.redo.push(snapshot()); restaurer(S.hist.pop()); toutRendre();
  }
  function retablir() {
    if (!S.redo.length) return;
    S.hist.push(snapshot()); restaurer(S.redo.pop()); toutRendre();
  }

  function pageCourante() { return S.pages[S.cur] || null; }
  function dims(p) {
    var meta = S.sources[p.src].metas[p.idx];
    if (p.crop) meta = { view: p.crop, rotate: meta.rotate };
    var v = meta.view;
    var W = v[2] - v[0], H = v[3] - v[1], R = ((meta.rotate || 0) + p.rot) % 360;
    return R % 180 ? { w: H, h: W, R: R, meta: meta } : { w: W, h: H, R: R, meta: meta };
  }
  function trouverAnnot(id) {
    var p = pageCourante();
    if (!p || !id) return null;
    for (var i = 0; i < p.annots.length; i++) if (p.annots[i].id === id) return p.annots[i];
    return null;
  }

  function occuper(txt) {
    S.occupe = true;
    var e = S.el && S.el.querySelector('.tpdf-etat');
    if (e) e.textContent = txt || 'Traitement…';
    if (S.el) S.el.setAttribute('aria-busy', 'true');
  }
  function liberer() {
    S.occupe = false;
    var e = S.el && S.el.querySelector('.tpdf-etat');
    if (e) e.textContent = '';
    if (S.el) S.el.removeAttribute('aria-busy');
  }
  function urlObjet(blob) { var u = URL.createObjectURL(blob); S.urls.push(u); return u; }
  function telecharger(bytes, nom) {
    var u = urlObjet(new Blob([bytes], { type: 'application/pdf' }));
    var a = document.createElement('a');
    a.href = u; a.download = nom; a.style.display = 'none';
    S.el.appendChild(a); a.click(); a.remove();
  }
  function attendre(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  /* ── Sources (fichiers ouverts) ───────────────────────────────────── */
  async function ajouterSource(nom, bytes) {
    var pj = await pdfjs(), L = await pdflib();
    var doc;
    try {
      doc = await pj.getDocument({ data: bytes.slice(), isEvalSupported: false }).promise;
    } catch (e) {
      if (e && e.name === 'PasswordException') throw new Error('chiffre');
      throw new Error('invalide');
    }
    var lib;
    try {
      lib = await L.PDFDocument.load(bytes, { updateMetadata: false });
    } catch (e) {
      try { doc.destroy(); } catch (x) { /* déjà libéré */ }
      if (/encrypt/i.test(String((e && (e.message || e.name)) || ''))) throw new Error('chiffre');
      throw new Error('invalide');
    }
    var metas = [];
    for (var i = 1; i <= doc.numPages; i++) {
      var pg = await doc.getPage(i);
      metas.push({ view: pg.view.slice(), rotate: pg.rotate || 0 });
    }
    var src = { id: nid('s'), nom: nom, bytes: bytes, pdf: doc, lib: lib, metas: metas, champs: [], valeurs: {} };
    S.sources[src.id] = src;
    hook('source', src, L, lib);
    return src;
  }

  async function imageVersPdf(bytes) {
    var L = await pdflib();
    var t = typeImage(bytes);
    if (!t) throw new Error('image');
    var d = await L.PDFDocument.create(), img;
    try { img = t === 'png' ? await d.embedPng(bytes) : await d.embedJpg(bytes); }
    catch (e) { throw new Error('image'); }
    var w = img.width * 0.75, h = img.height * 0.75, m = Math.max(w, h);
    if (m > 842) { w = w * 842 / m; h = h * 842 / m; }
    var p = d.addPage([w, h]);
    p.drawImage(img, { x: 0, y: 0, width: w, height: h });
    return d.save();
  }

  async function sourceBlanche(w, h) {
    var cle = Math.round(w) + 'x' + Math.round(h);
    if (S.blancs[cle] && S.sources[S.blancs[cle]]) return S.sources[S.blancs[cle]];
    var L = await pdflib();
    var d = await L.PDFDocument.create();
    d.addPage([w, h]);
    var src = await ajouterSource('Page blanche', await d.save());
    S.blancs[cle] = src.id;
    return src;
  }

  function nouvellePage(srcId, idx) { return { uid: nid('p'), src: srcId, idx: idx, rot: 0, annots: [] }; }

  async function ouvrirFichiers(liste) {
    var fichiers = Array.prototype.slice.call(liste || []);
    if (!fichiers.length) return;
    if (S.occupe) { toast('Opération en cours — patientez.', 'info'); return; }
    occuper('Ouverture…');
    var avant = snapshot(), ajout = 0, premier = S.pages.length === 0, nbFichiers = 0;
    for (var k = 0; k < fichiers.length; k++) {
      var f = fichiers[k];
      var nom = f.name || 'document', ext = (nom.split('.').pop() || '').toLowerCase();
      var estPdf = f.type === 'application/pdf' || ext === 'pdf';
      var estImg = /^image\/(png|jpe?g)$/.test(f.type) || ext === 'png' || ext === 'jpg' || ext === 'jpeg';
      if (!estPdf && !estImg) { toast('« ' + nom + ' » ignoré — formats acceptés : PDF, PNG, JPG.', 'danger'); continue; }
      try {
        var bytes = new Uint8Array(await f.arrayBuffer());
        if (estImg) bytes = await imageVersPdf(bytes);
        var src = await ajouterSource(nom, bytes);
        for (var i = 0; i < src.metas.length; i++) S.pages.push(nouvellePage(src.id, i));
        ajout += src.metas.length; nbFichiers++;
        if (!S.nom) S.nom = sansExt(nom);
      } catch (e) {
        toast('« ' + nom + ' » : ' + msgErreur(e), 'danger');
      }
    }
    liberer();
    if (!ajout) { toutRendre(); return; }
    pushHist(avant);
    if (premier) {
      var dem = S.pageDemandee;
      S.cur = dem && dem >= 1 && dem <= S.pages.length ? dem - 1 : 0;
      S.pageDemandee = null;
      if (S.panneauDemande && EXT.panneaux[S.panneauDemande]) { var pd = S.panneauDemande; S.panneauDemande = null; setTimeout(function () { EXT.panneaux[pd](); }, 0); }
      S.sel = {}; S.sel[S.pages[S.cur].uid] = 1; S.ancre = S.pages[S.cur].uid;
    }
    if (!premier || nbFichiers > 1) toast(ajout + ' page' + (ajout > 1 ? 's' : '') + ' ajoutée' + (ajout > 1 ? 's' : '') + ' au document.', 'success');
    toutRendre();
    notifier();
  }

  /* ── Construction du DOM ──────────────────────────────────────────── */
  /* Infobulles : mécanisme commun static/mysifa_bulles.js (data-bulle, un ou
     deux mots). Posées sur une enveloppe : un bouton désactivé ne reçoit pas
     le survol, son enveloppe si. */
  var BULLES = {
    ouvrir: 'Ouvrir', enregistrer: 'Enregistrer', imprimer: 'Imprimer', annuler: 'Annuler', retablir: 'Rétablir',
    image: 'Image', signer: 'Signer', pivg: 'Pivoter gauche', pivd: 'Pivoter droite', dupliquer: 'Dupliquer',
    blanche: 'Page blanche', supprimerPages: 'Supprimer', extraire: 'Extraire', decouper: 'Découper',
    compresser: 'Compresser', formulaire: 'Formulaire', zmoins: 'Zoom −', zplus: 'Zoom +', pagePrec: 'Précédente',
    pageSuiv: 'Suivante', rechPrec: 'Précédent', rechSuiv: 'Suivant', props: 'Propriétés', nouveau: 'Nouveau',
    select: 'Sélection', texte: 'Texte', surligneur: 'Surligneur', rect: 'Rectangle', ellipse: 'Ellipse', ligne: 'Ligne',
    fleche: 'Flèche', main: 'Main levée', tampon: 'Tampon', champ: 'Champ', editer: 'Modifier texte', bloc: 'Bloc texte', tableau: 'Tableau'
  };
  var NOMS_COULEURS = { '#d92626': 'Rouge', '#e8590c': 'Orange', '#f2b705': 'Jaune', '#2f9e44': 'Vert', '#1971c2': 'Bleu', '#7048e8': 'Violet', '#1a1a1a': 'Noir', '#ffffff': 'Blanc', '#1c3f94': 'Bleu' };
  var MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');
  function touche(k, maj) {
    var t = window.MySifaBulles && window.MySifaBulles.touche ? window.MySifaBulles.touche(k) : (MAC ? '⌘' : 'Ctrl+') + k;
    return maj ? (MAC ? '⇧' : 'Maj+') + t : t;
  }
  var TOUCHES = { annuler: ['Z'], retablir: ['Z', 1], enregistrer: ['S'] };
  function attrBulle(mot, tch) {
    return ' data-bulle="' + mot + '" data-bulle-base="' + mot + '"' + (tch ? ' data-bulle-touche="' + tch + '"' : '');
  }
  function bouton(act, icone, titre, extra) {
    extra = extra || {};
    var mot = extra.bulle || BULLES[extra.outil || act] || titre, t = TOUCHES[act];
    return '<span class="tpdf-bw' + (extra.cls ? ' tpdf-bw-' + extra.cls.split(' ')[0].replace('tpdf-', '') : '') + '"' + attrBulle(mot, t ? touche(t[0], t[1]) : '') + '>' +
      '<button type="button" class="tpdf-btn' + (extra.cls ? ' ' + extra.cls : '') + '" data-act="' + act + '"' +
      (extra.doc ? ' data-doc="1"' : '') + (extra.outil ? ' data-outil="' + extra.outil + '"' : '') +
      ' aria-label="' + titre + '">' + ico(icone) +
      (extra.txt ? '<span>' + extra.txt + '</span>' : '') + '</button></span>';
  }
  function outilBtn(o, icone, titre) { return bouton('outil', icone, titre, { doc: 1, outil: o }); }

  function construireDom() {
    var el = document.createElement('div');
    el.className = 'tpdf tpdf-sans-doc';
    var zooms = '<option value="fit">Ajuster</option>' + ZOOMS.map(function (z) { return '<option value="' + z + '">' + Math.round(z * 100) + ' %</option>'; }).join('');
    el.innerHTML =
      '<div class="tpdf-barre" role="toolbar" aria-label="Outils PDF">' +
        '<div class="tpdf-groupe">' +
          bouton('ouvrir', 'ouvrir', 'Ouvrir ou ajouter des fichiers', { txt: 'Ouvrir', cls: 'tpdf-btn-txt' }) +
          '<span class="tpdf-ext" data-ext="fichier"></span>' +
          bouton('enregistrer', 'enregistrer', 'Enregistrer le PDF (Ctrl+S)', { doc: 1, txt: 'Enregistrer', cls: 'tpdf-btn-plein' }) +
          bouton('imprimer', 'imprimer', 'Imprimer', { doc: 1 }) +
        '</div>' +
        '<div class="tpdf-groupe">' +
          bouton('annuler', 'annuler', 'Annuler (Ctrl+Z)', { doc: 1 }) +
          bouton('retablir', 'retablir', 'Rétablir (Maj+Ctrl+Z)', { doc: 1 }) +
        '</div>' +
        '<div class="tpdf-groupe">' +
          outilBtn('select', 'select', 'Sélection') +
          outilBtn('texte', 'texte', 'Texte libre') +
          outilBtn('surligneur', 'surligneur', 'Surligneur') +
          outilBtn('rect', 'rect', 'Rectangle') +
          outilBtn('ellipse', 'ellipse', 'Ellipse') +
          outilBtn('ligne', 'ligne', 'Ligne') +
          outilBtn('fleche', 'fleche', 'Flèche') +
          outilBtn('main', 'main', 'Trait à main levée') +
          outilBtn('tampon', 'tampon', 'Tampon') +
          bouton('image', 'image', 'Insérer une image', { doc: 1 }) +
          bouton('signer', 'signature', 'Signer', { doc: 1 }) +
          '<span class="tpdf-ext" data-ext="outils"></span>' +
        '</div>' +
        '<div class="tpdf-groupe">' +
          bouton('pivg', 'pivg', 'Pivoter à gauche', { doc: 1 }) +
          bouton('pivd', 'pivd', 'Pivoter à droite', { doc: 1 }) +
          bouton('dupliquer', 'dupliquer', 'Dupliquer la page', { doc: 1 }) +
          bouton('blanche', 'blanche', 'Insérer une page blanche', { doc: 1 }) +
          bouton('supprimerPages', 'supprimer', 'Supprimer les pages sélectionnées', { doc: 1 }) +
        '</div>' +
        '<div class="tpdf-groupe tpdf-groupe-menus">' +
          '<span class="tpdf-ext" data-ext="menus"></span>' +
          '<span class="tpdf-ext" data-ext="export"></span>' +
        '</div>' +
        '<div class="tpdf-groupe">' +
          bouton('zmoins', 'zmoins', 'Zoom arrière', { doc: 1 }) +
          '<span class="tpdf-bw" data-bulle="Zoom"><select class="tpdf-zoom" data-doc="1" aria-label="Zoom">' + zooms + '</select></span>' +
          bouton('zplus', 'zplus', 'Zoom avant', { doc: 1 }) +
          '<span class="tpdf-ext" data-ext="vue"></span>' +
        '</div>' +
        '<div class="tpdf-groupe">' +
          bouton('pagePrec', 'prec', 'Page précédente', { doc: 1 }) +
          '<span class="tpdf-nav" data-bulle="Page"><input class="tpdf-champ tpdf-num" type="text" inputmode="numeric" data-doc="1" aria-label="Page"><span class="tpdf-total">/ 0</span></span>' +
          bouton('pageSuiv', 'suiv', 'Page suivante', { doc: 1 }) +
        '</div>' +
        '<div class="tpdf-groupe tpdf-recherche">' +
          '<span class="tpdf-loupe">' + ico('chercher', 16) + '</span>' +
          '<input class="tpdf-champ tpdf-q" type="search" data-doc="1" placeholder="Rechercher dans le texte" aria-label="Rechercher dans le texte">' +
          '<span class="tpdf-compte"></span>' +
          bouton('rechPrec', 'haut', 'Résultat précédent', { doc: 1 }) +
          bouton('rechSuiv', 'bas', 'Résultat suivant', { doc: 1 }) +
        '</div>' +
        '<div class="tpdf-groupe tpdf-fin">' +
          '<span class="tpdf-etat" aria-live="polite"></span>' +
          bouton('props', 'reglages', 'Propriétés', { doc: 1, cls: 'tpdf-btn-props' }) +
        '</div>' +
      '</div>' +
      '<div class="tpdf-corps">' +
        '<aside class="tpdf-vignettes" aria-label="Pages"></aside>' +
        '<main class="tpdf-scene">' +
          '<div class="tpdf-vide">' +
            '<button type="button" class="tpdf-vide-zone" data-act="ouvrir">' +
              '<span class="tpdf-vide-ico">' + ico('depot', 40) + '</span>' +
              '<span class="tpdf-vide-titre">Déposer un PDF ou une image, ou cliquer pour choisir</span>' +
              '<span class="tpdf-vide-sous">Les fichiers restent sur ce poste.</span>' +
            '</button>' +
            '<div class="tpdf-vide-actions tpdf-ext" data-ext="vide"></div>' +
          '</div>' +
          '<div class="tpdf-boite"><div class="tpdf-feuille"><svg class="tpdf-calque" xmlns="' + NS + '"></svg><div class="tpdf-html"></div></div></div>' +
        '</main>' +
        '<aside class="tpdf-props" aria-label="Propriétés"></aside>' +
      '</div>' +
      '<div class="tpdf-depot-voile"><span>Déposer pour ajouter au document</span></div>' +
      '<input type="file" class="tpdf-fichier" multiple accept=".pdf,application/pdf,image/png,image/jpeg" hidden>' +
      '<input type="file" class="tpdf-fichier-image" accept="image/png,image/jpeg" hidden>';
    S.el = el;
    S.scene = el.querySelector('.tpdf-scene');
    S.feuille = el.querySelector('.tpdf-feuille');
    S.svg = el.querySelector('.tpdf-calque');
    S.html = el.querySelector('.tpdf-html');
    S.vig = el.querySelector('.tpdf-vignettes');
    S.props = el.querySelector('.tpdf-props');
    brancher();
    placerBoutonsExt();
  }
  function placerBoutonsExt() {
    if (!S || !S.el) return;
    S.el.querySelectorAll('[data-ext]').forEach(function (c) { c.textContent = ''; });
    EXT.boutons.forEach(function (b) {
      var c = S.el.querySelector('[data-ext="' + b.groupe + '"]');
      if (c) c.insertAdjacentHTML('beforeend', b.html);
    });
    var cm = S.el.querySelector('[data-ext="menus"]');
    if (cm) Object.keys(EXT.menus).sort(function (a, b) { return (EXT.menus[a].ordre || 0) - (EXT.menus[b].ordre || 0); }).forEach(function (id) {
      var m = EXT.menus[id];
      if (!m.items.length) return;
      cm.insertAdjacentHTML('beforeend', '<span class="tpdf-bw" data-bulle="' + m.libelle + '" data-bulle-base="' + m.libelle + '">' +
        '<button type="button" class="tpdf-btn tpdf-btn-menu' + (m.ia ? ' ia-btn' : '') + '" data-act="menu" data-menu="' + id + '" aria-haspopup="true" aria-expanded="false" aria-label="' + m.libelle + '">' +
        ico(m.icone || 'reglages', 16) + '<span>' + m.libelle + '</span>' + ico('bas', 12) + '</button></span>');
    });
  }
  // Menu déroulant d'un groupe : position fixe, jamais coupé par la barre.
  function ouvrirMenu(b) {
    var id = b.getAttribute('data-menu'), deja = S.menuOuvert === id;
    fermerMenu();
    if (deja) return;
    var m = EXT.menus[id]; if (!m) return;
    var d = document.createElement('div');
    d.className = 'tpdf-menu' + (m.ia ? ' ia-zone' : ''); d.setAttribute('role', 'menu');
    m.items.forEach(function (it) {
      if (it.separe) { var hr = document.createElement('div'); hr.className = 'tpdf-menu-sep'; d.appendChild(hr); return; }
      var x = document.createElement('button');
      x.type = 'button'; x.className = 'tpdf-menu-item'; x.setAttribute('role', 'menuitem');
      x.setAttribute('data-act', it.act); x.setAttribute('data-bulle', it.bulle || it.libelle.split(' ')[0]);
      x.disabled = !!it.doc && !S.pages.length;
      x.innerHTML = ico(it.icone || 'reglages', 16);
      var l = document.createElement('span'); l.textContent = it.libelle; x.appendChild(l);
      d.appendChild(x);
    });
    S.el.appendChild(d);
    var r = b.getBoundingClientRect(), w = d.offsetWidth, vw = document.documentElement.clientWidth;
    d.style.top = Math.round(r.bottom + 4) + 'px';
    d.style.left = Math.round(Math.max(8, Math.min(vw - w - 8, r.left))) + 'px';
    S.menuOuvert = id; S.menuEl = d; b.setAttribute('aria-expanded', 'true');
    S.menuFermer = function (ev) { if (!d.contains(ev.target) && !b.contains(ev.target)) fermerMenu(); };
    setTimeout(function () { document.addEventListener('pointerdown', S.menuFermer, true); }, 0);
  }
  function fermerMenu() {
    if (!S || !S.menuEl) return;
    S.menuEl.remove(); S.menuEl = null; S.menuOuvert = null;
    S.el.querySelectorAll('[data-act="menu"][aria-expanded="true"]').forEach(function (x) { x.setAttribute('aria-expanded', 'false'); });
    if (S.menuFermer) document.removeEventListener('pointerdown', S.menuFermer, true);
    S.menuFermer = null;
  }

  /* ── Écouteurs ────────────────────────────────────────────────────── */
  function brancher() {
    var el = S.el;
    el.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-act]');
      if (!b || !el.contains(b) || b.disabled) return;
      action(b.getAttribute('data-act'), b);
    });
    el.querySelector('.tpdf-fichier').addEventListener('change', function (ev) {
      var f = ev.target.files; ouvrirFichiers(f); ev.target.value = '';
    });
    el.querySelector('.tpdf-fichier-image').addEventListener('change', function (ev) {
      var f = ev.target.files && ev.target.files[0]; ev.target.value = '';
      if (f) insererImageFichier(f);
    });
    el.querySelector('.tpdf-zoom').addEventListener('change', function (ev) {
      var v = ev.target.value; S.zoom = v === 'fit' ? 'fit' : parseFloat(v); rendrePage();
    });
    var num = el.querySelector('.tpdf-num');
    num.addEventListener('change', function () {
      var n = parseInt(num.value, 10);
      if (n >= 1 && n <= S.pages.length) allerPage(n - 1, true);
      else { num.value = S.cur + 1; toast('Page inexistante — entre 1 et ' + S.pages.length + '.', 'danger'); }
    });
    num.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') num.blur(); });
    var q = el.querySelector('.tpdf-q'), minuteur = null;
    q.addEventListener('input', function () {
      clearTimeout(minuteur); minuteur = setTimeout(function () { chercher(q.value); }, 250);
    });
    q.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') { ev.preventDefault(); if (S.rech.q !== q.value) chercher(q.value); else allerResultat(ev.shiftKey ? -1 : 1); }
      else if (ev.key === 'Escape') { q.value = ''; chercher(''); }
    });

    // Glisser-déposer de fichiers sur tout le module.
    var compteur = 0;
    el.addEventListener('dragenter', function (ev) {
      if (!aDesFichiers(ev)) return;
      compteur++; el.classList.add('tpdf-depot');
    });
    el.addEventListener('dragleave', function (ev) {
      if (!aDesFichiers(ev)) return;
      compteur = Math.max(0, compteur - 1); if (!compteur) el.classList.remove('tpdf-depot');
    });
    el.addEventListener('dragover', function (ev) {
      if (aDesFichiers(ev)) { ev.preventDefault(); ev.dataTransfer.dropEffect = 'copy'; }
    });
    el.addEventListener('drop', function (ev) {
      if (!aDesFichiers(ev)) return;
      ev.preventDefault(); compteur = 0; el.classList.remove('tpdf-depot');
      ouvrirFichiers(ev.dataTransfer.files);
    });

    brancherVignettes();
    brancherCalque();

    S.ecoute = onKey;
    document.addEventListener('keydown', onKey);
    if (window.ResizeObserver) {
      var tempo = null, largeur = 0;
      S.ro = new ResizeObserver(function () {
        var w = S.scene.clientWidth;
        // Une variation de l'ordre d'une barre de défilement n'est pas un vrai
        // redimensionnement : la suivre relançait le rendu en boucle (page
        // pivotée qui sautille).
        if (Math.abs(w - largeur) <= 24) return; largeur = w;
        if (S.zoom !== 'fit' || !S.pages.length) return;
        clearTimeout(tempo); tempo = setTimeout(rendrePage, 120);
      });
      S.ro.observe(S.scene);
    }
  }
  function aDesFichiers(ev) {
    var t = ev.dataTransfer && ev.dataTransfer.types;
    return !!t && Array.prototype.indexOf.call(t, 'Files') >= 0;
  }

  function action(act, b) {
    if (act === 'menu') { ouvrirMenu(b); return; }
    if (S.menuEl && b && S.menuEl.contains(b)) fermerMenu();
    if (act === 'ouvrir') { S.el.querySelector('.tpdf-fichier').click(); return; }
    var E = EXT.actions[act];
    if (E && E.sansDoc) return E.fn(b);
    if (!S.pages.length) return;
    if (E) return E.fn(b);
    switch (act) {
      case 'enregistrer': return enregistrer();
      case 'imprimer': return imprimer();
      case 'annuler': return annuler();
      case 'retablir': return retablir();
      case 'outil': return choisirOutil(b.getAttribute('data-outil'));
      case 'image': S.el.querySelector('.tpdf-fichier-image').click(); return;
      case 'signer': return modaleSignature();
      case 'pivg': return pivoter(-1);
      case 'pivd': return pivoter(1);
      case 'dupliquer': return dupliquer();
      case 'blanche': return pageBlanche();
      case 'supprimerPages': return supprimerPages();
      case 'extraire': return extraireSelection();
      case 'decouper': return modaleDecouper();
      case 'compresser': return modaleCompresser();
      case 'zmoins': return zoomPas(-1);
      case 'zplus': return zoomPas(1);
      case 'pagePrec': return allerPage(S.cur - 1, true);
      case 'pageSuiv': return allerPage(S.cur + 1, true);
      case 'rechPrec': return allerResultat(-1);
      case 'rechSuiv': return allerResultat(1);
      case 'props': S.el.classList.toggle('tpdf-props-ouvert'); return;
      case 'fermerProps': S.el.classList.remove('tpdf-props-ouvert'); return;
    }
  }

  function enSaisie(t) {
    return !!t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
  }
  function onKey(ev) {
    if (!S || !S.el || !S.el.isConnected || !S.el.offsetParent) return;
    if (S.menuEl && ev.key === 'Escape') { ev.preventDefault(); fermerMenu(); return; }
    if (S.modale) {
      if (ev.key === 'Escape') { ev.preventDefault(); fermerModale(); }
      return;
    }
    if (enSaisie(ev.target) || !S.pages.length) return;
    var mod = ev.metaKey || ev.ctrlKey, k = ev.key;
    if (mod && (k === 'z' || k === 'Z')) { ev.preventDefault(); if (ev.shiftKey) retablir(); else annuler(); return; }
    if (mod && (k === 'y' || k === 'Y')) { ev.preventDefault(); retablir(); return; }
    if (mod && (k === 's' || k === 'S')) { ev.preventDefault(); enregistrer(); return; }
    if (mod) return;
    if (k === 'Delete' || k === 'Backspace') {
      if (S.annSel) { ev.preventDefault(); supprimerAnnot(); }
      return;
    }
    if (k === 'Escape') {
      if (S.annSel || S.outil !== 'select') { S.annSel = null; choisirOutil('select'); }
      return;
    }
    var fl = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[k];
    if (fl && S.annSel) {
      ev.preventDefault();
      var a = trouverAnnot(S.annSel); if (!a) return;
      var avant = snapshot(), pas = ev.shiftKey ? 10 : 1, o = JSON.parse(JSON.stringify(a));
      deplacer(a, o, fl[0] * pas, fl[1] * pas);
      pushHist(avant); dessinerCalque();
      return;
    }
    if (k === 'ArrowLeft' || k === 'PageUp') { ev.preventDefault(); allerPage(S.cur - 1, true); }
    else if (k === 'ArrowRight' || k === 'PageDown') { ev.preventDefault(); allerPage(S.cur + 1, true); }
    else if (k === 'Home') { ev.preventDefault(); allerPage(0, true); }
    else if (k === 'End') { ev.preventDefault(); allerPage(S.pages.length - 1, true); }
  }

  /* ── Rendu global ─────────────────────────────────────────────────── */
  function toutRendre() {
    if (!S || !S.el) return;
    var vide = !S.pages.length;
    S.el.classList.toggle('tpdf-sans-doc', vide);
    if (vide) { S.cur = 0; S.annSel = null; }
    rendreBarre();
    rendreVignettes();
    rendreProps();
    if (!vide) rendrePage();
    else { S.jeton++; S.svg.textContent = ''; var c = S.feuille.querySelector('canvas'); if (c) c.remove(); }
  }

  function rendreBarre() {
    var el = S.el, vide = !S.pages.length;
    el.querySelectorAll('[data-doc]').forEach(function (b) { b.disabled = vide; });
    el.querySelectorAll('.tpdf-barre [data-bulle-base]').forEach(function (w) {
      var b = w.querySelector('[data-doc]');
      w.setAttribute('data-bulle', w.getAttribute('data-bulle-base') + (vide && b ? ' · aucun document' : ''));
    });
    if (!vide) {
      el.querySelector('[data-act="annuler"]').disabled = !S.hist.length;
      el.querySelector('[data-act="retablir"]').disabled = !S.redo.length;
      el.querySelector('[data-act="pagePrec"]').disabled = S.cur <= 0;
      el.querySelector('[data-act="pageSuiv"]').disabled = S.cur >= S.pages.length - 1;
      var aRes = S.rech.res.length > 0;
      el.querySelector('[data-act="rechPrec"]').disabled = !aRes;
      el.querySelector('[data-act="rechSuiv"]').disabled = !aRes;
    }
    el.querySelectorAll('[data-outil]').forEach(function (b) {
      var on = b.getAttribute('data-outil') === S.outil;
      b.classList.toggle('tpdf-actif', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    var num = el.querySelector('.tpdf-num');
    if (document.activeElement !== num) num.value = vide ? '' : S.cur + 1;
    el.querySelector('.tpdf-total').textContent = '/ ' + S.pages.length;
    el.querySelector('.tpdf-zoom').value = S.zoom === 'fit' ? 'fit' : String(S.zoom);
    var c = el.querySelector('.tpdf-compte');
    c.textContent = S.rech.q ? (S.rech.res.length ? (S.rech.i + 1) + ' / ' + S.rech.res.length : 'Aucun résultat pour « ' + S.rech.q + ' »') : '';
    S.svg.setAttribute('data-outil', S.outil);
    S.html.setAttribute('data-outil', S.outil);
    hook('barre');
  }

  function zoomEffectif(d) {
    if (S.zoom !== 'fit') return S.zoom;
    var dispo = Math.max(120, S.scene.clientWidth - 48);
    if (S.deuxPages) dispo = Math.max(120, dispo / 2 - 12);
    return Math.max(0.25, Math.min(3, dispo / d.w));
  }
  function zoomPas(sens) {
    var p = pageCourante(); if (!p) return;
    var z = zoomEffectif(dims(p)), suiv = null;
    if (sens > 0) { for (var i = 0; i < ZOOMS.length; i++) if (ZOOMS[i] > z + 0.01) { suiv = ZOOMS[i]; break; } }
    else { for (var j = ZOOMS.length - 1; j >= 0; j--) if (ZOOMS[j] < z - 0.01) { suiv = ZOOMS[j]; break; } }
    if (suiv == null) return;
    S.zoom = suiv; rendreBarre(); rendrePage();
  }

  // Viewport pdf.js d'une page, recadrage compris : la boîte recadrée est
  // ramenée à l'origine du canvas (pdf.js n'expose pas de viewBox libre).
  function viewportPour(pg, p, scale, R) {
    var plein = pg.getViewport({ scale: scale, rotation: R });
    if (!p || !p.crop) return { vp: plein, w: plein.width, h: plein.height };
    var a = plein.convertToViewportPoint(p.crop[0], p.crop[1]), b = plein.convertToViewportPoint(p.crop[2], p.crop[3]);
    var vp = pg.getViewport({ scale: scale, rotation: R, offsetX: -Math.min(a[0], b[0]), offsetY: -Math.min(a[1], b[1]) });
    return { vp: vp, w: Math.abs(b[0] - a[0]), h: Math.abs(b[1] - a[1]) };
  }
  async function rendrePage() {
    var p = pageCourante(); if (!p) return;
    var jeton = ++S.jeton;
    var src = S.sources[p.src], d = dims(p), z = zoomEffectif(d);
    S.zoomCourant = z;
    S.feuille.style.width = Math.round(d.w * z) + 'px';
    S.feuille.style.height = Math.round(d.h * z) + 'px';
    dessinerCalque();
    hook('page', p, d, z);
    var pg;
    try { pg = await src.pdf.getPage(p.idx + 1); } catch (e) { return; }
    if (jeton !== S.jeton) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var vpp = viewportPour(pg, p, z * dpr, d.R), vp = vpp.vp;
    var cv = document.createElement('canvas');
    cv.width = Math.floor(vpp.w); cv.height = Math.floor(vpp.h);
    cv.className = 'tpdf-toile';
    if (S.tache) { try { S.tache.cancel(); } catch (e) { /* rendu déjà fini */ } }
    var opts = { canvasContext: cv.getContext('2d'), viewport: vp };
    if (EXT.modeAnnot != null) opts.annotationMode = EXT.modeAnnot;
    var tache = pg.render(opts);
    S.tache = tache;
    try { await tache.promise; } catch (e) { return; }
    if (jeton !== S.jeton) return;
    var ancien = S.feuille.querySelector('canvas');
    if (ancien) ancien.remove();
    S.feuille.insertBefore(cv, S.svg);
    hook('rendu', p, d, z, cv, pg);
  }

  function allerPage(i, notif) {
    if (!S.pages.length) return;
    i = Math.max(0, Math.min(S.pages.length - 1, i));
    if (i === S.cur && S.feuille.querySelector('canvas')) return;
    S.cur = i; S.annSel = null;
    var uid = S.pages[i].uid;
    if (!S.sel[uid]) { S.sel = {}; S.sel[uid] = 1; S.ancre = uid; }
    rendreBarre(); majVignettesEtat(); rendreProps(); rendrePage();
    var v = S.vig.querySelector('[data-uid="' + uid + '"]');
    if (v && v.scrollIntoView) v.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    S.scene.scrollTop = 0;
    if (notif) notifier();
  }

  /* ── Vignettes ────────────────────────────────────────────────────── */
  function cleVig(p) { return p.src + ':' + p.idx + ':' + dims(p).R + (p.crop ? ':' + p.crop.map(Math.round).join(',') : ''); }

  function rendreVignettes() {
    var box = S.vig;
    box.textContent = '';
    S.pages.forEach(function (p, i) {
      var d = dims(p), cle = cleVig(p);
      var v = document.createElement('div');
      v.className = 'tpdf-vig';
      v.draggable = true;
      v.setAttribute('data-uid', p.uid);
      v.setAttribute('role', 'button');
      v.setAttribute('tabindex', '0');
      v.setAttribute('aria-label', 'Page ' + (i + 1));
      var fig = document.createElement('div');
      fig.className = 'tpdf-vig-img';
      fig.setAttribute('data-cle', cle);
      fig.style.aspectRatio = d.w + ' / ' + d.h;
      if (S.vigCache[cle]) { var img = document.createElement('img'); img.src = S.vigCache[cle]; img.alt = ''; fig.appendChild(img); }
      else demanderVignette(p);
      v.appendChild(fig);
      var pied = document.createElement('div');
      pied.className = 'tpdf-vig-pied';
      var n = document.createElement('span'); n.textContent = i + 1; pied.appendChild(n);
      if (p.annots.length) {
        var b = document.createElement('span'); b.className = 'tpdf-vig-badge';
        b.setAttribute('data-bulle', p.annots.length > 1 ? 'Annotations' : 'Annotation');
        b.textContent = p.annots.length; pied.appendChild(b);
      }
      v.appendChild(pied);
      hook('vignette', p, v);
      box.appendChild(v);
    });
    majVignettesEtat();
  }
  function majVignettesEtat() {
    var cur = S.pages[S.cur] && S.pages[S.cur].uid;
    S.vig.querySelectorAll('.tpdf-vig').forEach(function (v) {
      var u = v.getAttribute('data-uid');
      v.classList.toggle('tpdf-vig-sel', !!S.sel[u]);
      v.classList.toggle('tpdf-vig-cur', u === cur);
    });
  }
  function demanderVignette(p) {
    var cle = cleVig(p);
    if (S.vigCache[cle] || S.vigAttente[cle]) return;
    S.vigAttente[cle] = 1;
    var srcId = p.src, idx = p.idx, R = dims(p).R, etat = S, crop = p.crop;
    S.vigFile = S.vigFile.then(function () {
      if (etat !== S) return null;
      return rendreVignette(srcId, idx, R, cle, crop);
    }).catch(function () { /* vignette ratée : la page reste affichable */ });
  }
  async function rendreVignette(srcId, idx, R, cle, crop) {
    var src = S.sources[srcId]; if (!src) return;
    var pg = await src.pdf.getPage(idx + 1), pc = crop ? { crop: crop } : null;
    var v1 = viewportPour(pg, pc, 1, R);
    var vpp = viewportPour(pg, pc, 220 / Math.max(v1.w, v1.h), R), vp = vpp.vp;
    var cv = document.createElement('canvas');
    cv.width = Math.ceil(vpp.w); cv.height = Math.ceil(vpp.h);
    await pg.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise;
    if (!S) return;
    S.vigCache[cle] = cv.toDataURL('image/jpeg', 0.75);
    delete S.vigAttente[cle];
    S.vig.querySelectorAll('.tpdf-vig-img[data-cle="' + cle + '"]').forEach(function (f) {
      f.textContent = '';
      var img = document.createElement('img'); img.src = S.vigCache[cle]; img.alt = ''; f.appendChild(img);
    });
  }

  function brancherVignettes() {
    var box = S.vig;
    box.addEventListener('click', function (ev) {
      var v = ev.target.closest('.tpdf-vig'); if (!v) return;
      cliquerVignette(v.getAttribute('data-uid'), ev);
    });
    box.addEventListener('keydown', function (ev) {
      var v = ev.target.closest('.tpdf-vig'); if (!v) return;
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); cliquerVignette(v.getAttribute('data-uid'), ev); }
    });
    var glisse = false;
    function marque(v, apres) {
      box.querySelectorAll('.tpdf-vig-avant,.tpdf-vig-apres').forEach(function (x) { x.classList.remove('tpdf-vig-avant', 'tpdf-vig-apres'); });
      if (v) v.classList.add(apres ? 'tpdf-vig-apres' : 'tpdf-vig-avant');
    }
    function cible(ev) {
      var items = box.querySelectorAll('.tpdf-vig');
      var horiz = box.scrollWidth > box.clientWidth + 4 || getComputedStyle(box).flexDirection === 'row';
      for (var i = 0; i < items.length; i++) {
        var r = items[i].getBoundingClientRect();
        var milieu = horiz ? r.left + r.width / 2 : r.top + r.height / 2;
        if ((horiz ? ev.clientX : ev.clientY) < milieu) return { i: i, v: items[i], apres: false };
      }
      return { i: items.length, v: items[items.length - 1], apres: true };
    }
    box.addEventListener('dragstart', function (ev) {
      var v = ev.target.closest('.tpdf-vig'); if (!v) return;
      var u = v.getAttribute('data-uid');
      if (!S.sel[u]) { S.sel = {}; S.sel[u] = 1; S.ancre = u; majVignettesEtat(); }
      glisse = true;
      ev.dataTransfer.effectAllowed = 'move';
      try { ev.dataTransfer.setData('application/x-tpdf', u); } catch (e) { ev.dataTransfer.setData('text/plain', u); }
      v.classList.add('tpdf-vig-glisse');
    });
    box.addEventListener('dragover', function (ev) {
      if (!glisse) return;
      ev.preventDefault(); ev.stopPropagation();
      ev.dataTransfer.dropEffect = 'move';
      var c = cible(ev); marque(c.v, c.apres);
    });
    box.addEventListener('drop', function (ev) {
      if (!glisse) return;
      ev.preventDefault(); ev.stopPropagation();
      var c = cible(ev);
      glisse = false; marque(null);
      var avant = snapshot(), curUid = S.pages[S.cur].uid;
      var nouv = deplacerSelection(S.pages, function (p) { return !!S.sel[p.uid]; }, c.i);
      var change = nouv.some(function (p, i) { return p !== S.pages[i]; });
      if (!change) return;
      S.pages = nouv;
      S.cur = Math.max(0, S.pages.findIndex(function (p) { return p.uid === curUid; }));
      pushHist(avant); rendreVignettes(); rendreBarre(); notifier();
    });
    box.addEventListener('dragend', function () {
      glisse = false; marque(null);
      box.querySelectorAll('.tpdf-vig-glisse').forEach(function (x) { x.classList.remove('tpdf-vig-glisse'); });
    });
  }

  function cliquerVignette(uid, ev) {
    var i = S.pages.findIndex(function (p) { return p.uid === uid; });
    if (i < 0) return;
    if (ev.shiftKey && S.ancre) {
      var a = S.pages.findIndex(function (p) { return p.uid === S.ancre; });
      if (a < 0) a = i;
      S.sel = {};
      for (var k = Math.min(a, i); k <= Math.max(a, i); k++) S.sel[S.pages[k].uid] = 1;
    } else if (ev.metaKey || ev.ctrlKey) {
      if (S.sel[uid] && Object.keys(S.sel).length > 1) delete S.sel[uid]; else S.sel[uid] = 1;
      S.ancre = uid;
    } else {
      S.sel = {}; S.sel[uid] = 1; S.ancre = uid;
    }
    if (i !== S.cur) { S.cur = i; S.annSel = null; rendreBarre(); rendreProps(); rendrePage(); notifier(); }
    majVignettesEtat();
  }

  function pagesCiblees() {
    var l = S.pages.filter(function (p) { return S.sel[p.uid]; });
    return l.length ? l : [pageCourante()].filter(Boolean);
  }

  /* ── Opérations sur les pages ─────────────────────────────────────── */
  function tournerAnnots(p, sens) {
    var d = dims(p), W = d.w, H = d.h;
    function tp(x, y) { return tournerPoint(x, y, W, H, sens); }
    p.annots.forEach(function (a) {
      var T = EXT.types[a.t];
      if (T && T.repere === 'pdf0') return; // rangé dans le repère de la page non pivotée
      if (a.t === 'ligne' || a.t === 'fleche') {
        var q1 = tp(a.x1, a.y1), q2 = tp(a.x2, a.y2);
        a.x1 = q1[0]; a.y1 = q1[1]; a.x2 = q2[0]; a.y2 = q2[1];
      } else if (a.t === 'main') {
        a.pts = a.pts.map(function (q) { return tp(q[0], q[1]); });
      } else if (a.t === 'rect' || a.t === 'ellipse' || a.t === 'surligneur' || (T && T.boiteTournante)) {
        var c1 = tp(a.x, a.y), c2 = tp(a.x + a.w, a.y + a.h);
        a.x = Math.min(c1[0], c2[0]); a.y = Math.min(c1[1], c2[1]);
        a.w = Math.abs(c2[0] - c1[0]); a.h = Math.abs(c2[1] - c1[1]);
      } else {
        // Texte, tampon, image : restent droits, seul leur centre suit la page.
        var b = boite(a), c = tp(b.x + b.w / 2, b.y + b.h / 2);
        a.x = c[0] - b.w / 2; a.y = c[1] - b.h / 2;
      }
    });
  }
  function pivoter(sens) {
    var avant = snapshot();
    pagesCiblees().forEach(function (p) {
      tournerAnnots(p, sens);
      p.rot = (p.rot + (sens > 0 ? 90 : 270)) % 360;
    });
    pushHist(avant); S.annSel = null;
    toutRendre();
  }
  function dupliquer() {
    var avant = snapshot(), cibles = pagesCiblees(), nouv = [], derniere = null;
    S.pages.forEach(function (p) {
      nouv.push(p);
      if (cibles.indexOf(p) >= 0) {
        var c = JSON.parse(JSON.stringify(p));
        c.uid = nid('p'); c.annots.forEach(function (a) { a.id = nid('n'); });
        nouv.push(c); derniere = c;
      }
    });
    S.pages = nouv;
    if (derniere) { S.cur = S.pages.indexOf(derniere); S.sel = {}; S.sel[derniere.uid] = 1; S.ancre = derniere.uid; }
    pushHist(avant);
    toast(cibles.length > 1 ? cibles.length + ' pages dupliquées.' : 'Page dupliquée.', 'success');
    toutRendre(); notifier();
  }
  async function pageBlanche() {
    var p = pageCourante(), d = p ? dims(p) : { w: 595.28, h: 841.89 };
    try {
      var src = await sourceBlanche(d.w, d.h);
      var avant = snapshot(), np = nouvellePage(src.id, 0);
      S.pages.splice(S.cur + 1, 0, np);
      S.cur = S.cur + 1; S.sel = {}; S.sel[np.uid] = 1; S.ancre = np.uid;
      pushHist(avant); toutRendre(); notifier();
    } catch (e) { toast(msgErreur(e), 'danger'); }
  }
  function supprimerPages() {
    var cibles = pagesCiblees(); if (!cibles.length) return;
    var avant = snapshot();
    S.pages = S.pages.filter(function (p) { return cibles.indexOf(p) < 0; });
    S.sel = {}; S.annSel = null;
    S.cur = Math.min(S.cur, Math.max(0, S.pages.length - 1));
    if (S.pages[S.cur]) { S.sel[S.pages[S.cur].uid] = 1; S.ancre = S.pages[S.cur].uid; }
    pushHist(avant);
    var n = cibles.length;
    toast((n > 1 ? n + ' pages supprimées' : 'Page supprimée') + ' — Ctrl+Z pour annuler.', 'info');
    toutRendre(); notifier();
  }

  /* ── Annotations : géométrie ──────────────────────────────────────── */
  var _ctxMesure = null;
  function mesureTexte(txt, taille) {
    if (!_ctxMesure) _ctxMesure = document.createElement('canvas').getContext('2d');
    _ctxMesure.font = taille + 'px ' + POLICE;
    var lignes = String(txt).split('\n'), w = 0;
    lignes.forEach(function (l) { w = Math.max(w, _ctxMesure.measureText(l).width); });
    return { w: Math.max(w, taille * 0.6), h: lignes.length * taille * INTERLIGNE };
  }
  function boite(a) {
    if (EXT.types[a.t] && EXT.types[a.t].boite) return EXT.types[a.t].boite(a);
    if (a.t === 'texte') { var m = mesureTexte(a.texte, a.taille); return { x: a.x, y: a.y, w: m.w, h: m.h }; }
    if (a.t === 'ligne' || a.t === 'fleche') {
      return { x: Math.min(a.x1, a.x2), y: Math.min(a.y1, a.y2), w: Math.abs(a.x2 - a.x1), h: Math.abs(a.y2 - a.y1) };
    }
    if (a.t === 'main') {
      var xs = a.pts.map(function (q) { return q[0]; }), ys = a.pts.map(function (q) { return q[1]; });
      var x = Math.min.apply(null, xs), y = Math.min.apply(null, ys);
      return { x: x, y: y, w: Math.max.apply(null, xs) - x, h: Math.max.apply(null, ys) - y };
    }
    return { x: a.x, y: a.y, w: a.w, h: a.h };
  }
  function deplacer(a, o, dx, dy) {
    if (EXT.types[a.t] && EXT.types[a.t].fixe) return;
    if (o.x != null) { a.x = o.x + dx; a.y = o.y + dy; }
    if (o.x1 != null) { a.x1 = o.x1 + dx; a.y1 = o.y1 + dy; a.x2 = o.x2 + dx; a.y2 = o.y2 + dy; }
    if (o.pts) a.pts = o.pts.map(function (q) { return [q[0] + dx, q[1] + dy]; });
  }
  function redimensionner(a, o, poignee, pt, garderRatio) {
    var T = EXT.types[a.t];
    if (T && T.fixe) return;
    if (T && T.redim) { T.redim(a, o, poignee, pt, garderRatio); return; }
    if (poignee === 'p1') { a.x1 = pt.x; a.y1 = pt.y; return; }
    if (poignee === 'p2') { a.x2 = pt.x; a.y2 = pt.y; return; }
    var ob = boite(o);
    var fx = poignee.indexOf('w') >= 0 ? ob.x + ob.w : ob.x;
    var fy = poignee.indexOf('n') >= 0 ? ob.y + ob.h : ob.y;
    var w = Math.max(4, Math.abs(pt.x - fx)), h = Math.max(4, Math.abs(pt.y - fy));
    if (garderRatio && ob.w > 0 && ob.h > 0) {
      var r = Math.max(w / ob.w, h / ob.h); w = ob.w * r; h = ob.h * r;
    }
    var nx = poignee.indexOf('w') >= 0 ? fx - w : fx, ny = poignee.indexOf('n') >= 0 ? fy - h : fy;
    if (a.t === 'texte') {
      var k = h / (ob.h || 1);
      a.taille = Math.max(4, Math.min(300, o.taille * k));
      var nb = mesureTexte(a.texte, a.taille);
      a.x = poignee.indexOf('w') >= 0 ? fx - nb.w : fx;
      a.y = poignee.indexOf('n') >= 0 ? fy - nb.h : fy;
    } else if (a.t === 'main') {
      var sx = w / (ob.w || 1), sy = h / (ob.h || 1);
      a.pts = o.pts.map(function (q) { return [nx + (q[0] - ob.x) * sx, ny + (q[1] - ob.y) * sy]; });
    } else { a.x = nx; a.y = ny; a.w = w; a.h = h; }
  }

  /* ── Calque d'annotations (SVG, viewBox en points) ────────────────── */
  function sv(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function cheminPts(pts) {
    return pts.map(function (q, i) { return (i ? 'L' : 'M') + q[0].toFixed(2) + ' ' + q[1].toFixed(2); }).join(' ');
  }
  // Matrice SVG qui passe du repère de la page non pivotée à la page affichée.
  function matriceR0(d) {
    if (!d.R) return null;
    var v = d.meta.view;
    function f(u, w) { var q = versPdf(v, 0, u, w); return versVue(v, d.R, q[0], q[1]); }
    var e = f(0, 0), x = f(1, 0), y = f(0, 1);
    return 'matrix(' + [x[0] - e[0], x[1] - e[1], y[0] - e[0], y[1] - e[1], e[0], e[1]].join(' ') + ')';
  }
  function dessinerAnnot(a, svg) {
    var g = sv('g', { 'data-id': a.id, 'class': 'tpdf-annot' }, svg);
    var b, T = EXT.types[a.t];
    if (T) {
      if (T.repere === 'pdf0') { var m = matriceR0(dims(pageCourante())); if (m) g.setAttribute('transform', m); }
      if (T.dessiner) T.dessiner(a, g, S.zoomCourant || 1);
      return;
    }
    switch (a.t) {
      case 'texte': {
        b = boite(a);
        sv('rect', { x: b.x, y: b.y, width: b.w, height: b.h, fill: 'transparent' }, g);
        var t = sv('text', { 'font-family': POLICE, 'font-size': a.taille, fill: a.couleur }, g);
        String(a.texte).split('\n').forEach(function (l, i) {
          var ts = sv('tspan', { x: a.x, y: a.y + a.taille * ASC + i * a.taille * INTERLIGNE }, t);
          ts.textContent = l || ' ';
        });
        break;
      }
      case 'surligneur':
        sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: a.couleur, 'fill-opacity': a.opacite, style: 'mix-blend-mode:multiply' }, g);
        break;
      case 'rect':
        sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: 'transparent', stroke: a.couleur, 'stroke-width': a.ep }, g);
        break;
      case 'ellipse':
        sv('ellipse', { cx: a.x + a.w / 2, cy: a.y + a.h / 2, rx: a.w / 2, ry: a.h / 2, fill: 'transparent', stroke: a.couleur, 'stroke-width': a.ep }, g);
        break;
      case 'ligne':
      case 'fleche':
        sv('line', { x1: a.x1, y1: a.y1, x2: a.x2, y2: a.y2, stroke: 'transparent', 'stroke-width': Math.max(a.ep, 12 / (S.zoomCourant || 1)) }, g);
        sv('line', { x1: a.x1, y1: a.y1, x2: a.x2, y2: a.y2, stroke: a.couleur, 'stroke-width': a.ep, 'stroke-linecap': 'round' }, g);
        if (a.t === 'fleche') sv('polygon', { points: pointesFleche(a).map(function (q) { return q.join(','); }).join(' '), fill: a.couleur }, g);
        break;
      case 'main':
        sv('path', { d: cheminPts(a.pts), fill: 'none', stroke: 'transparent', 'stroke-width': Math.max(a.ep, 12 / (S.zoomCourant || 1)), 'stroke-linecap': 'round' }, g);
        sv('path', { d: cheminPts(a.pts), fill: 'none', stroke: a.couleur, 'stroke-width': a.ep, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
        break;
      case 'tampon': {
        var ep = a.h * 0.06;
        sv('rect', { x: a.x + ep / 2, y: a.y + ep / 2, width: Math.max(1, a.w - ep), height: Math.max(1, a.h - ep), fill: 'transparent', stroke: a.couleur, 'stroke-width': ep }, g);
        var l1 = sv('text', { x: a.x + a.w / 2, y: a.y + (a.date ? a.h * 0.56 : a.h * 0.68), 'text-anchor': 'middle', 'font-family': POLICE, 'font-weight': 'bold', 'font-size': a.date ? a.h * 0.36 : a.h * 0.5, fill: a.couleur }, g);
        l1.textContent = a.libelle.toUpperCase();
        if (a.date) {
          var l2 = sv('text', { x: a.x + a.w / 2, y: a.y + a.h * 0.84, 'text-anchor': 'middle', 'font-family': POLICE, 'font-size': a.h * 0.19, fill: a.couleur }, g);
          l2.textContent = a.date;
        }
        break;
      }
      case 'image': {
        var im = S.images[a.img];
        if (im) sv('image', { x: a.x, y: a.y, width: a.w, height: a.h, href: im.url, preserveAspectRatio: 'none' }, g);
        sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: 'transparent' }, g);
        break;
      }
    }
  }
  function dessinerCalque() {
    var p = pageCourante(), svg = S.svg;
    svg.textContent = '';
    if (!p) return;
    var d = dims(p), z = S.zoomCourant || 1;
    svg.setAttribute('viewBox', '0 0 ' + d.w + ' ' + d.h);
    svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%');
    p.annots.forEach(function (a) { dessinerAnnot(a, svg); });
    dessinerResultats(p, d);
    hook('calque', p, d);
    var a = trouverAnnot(S.annSel);
    if (!a) return;
    var t = 8 / z, cadre = sv('g', { 'class': 'tpdf-sel' }, svg), T = EXT.types[a.t];
    if (T && T.repere === 'pdf0') { var mx = matriceR0(d); if (mx) cadre.setAttribute('transform', mx); }
    if (a.t === 'ligne' || a.t === 'fleche') {
      [['p1', a.x1, a.y1], ['p2', a.x2, a.y2]].forEach(function (h) {
        sv('circle', { cx: h[1], cy: h[2], r: t * 0.7, 'class': 'tpdf-poignee', 'data-poignee': h[0], 'stroke-width': 1.5 / z }, cadre);
      });
      return;
    }
    var b = boite(a), m = 3 / z;
    sv('rect', { x: b.x - m, y: b.y - m, width: b.w + 2 * m, height: b.h + 2 * m, 'class': 'tpdf-cadre', 'stroke-width': 1.2 / z, 'stroke-dasharray': (4 / z) + ' ' + (3 / z) }, cadre);
    if (T && T.decorations) T.decorations(a, cadre, z);
    if (T && T.fixe) return;
    [['nw', b.x - m, b.y - m], ['ne', b.x + b.w + m, b.y - m], ['sw', b.x - m, b.y + b.h + m], ['se', b.x + b.w + m, b.y + b.h + m]].forEach(function (h) {
      sv('rect', { x: h[1] - t / 2, y: h[2] - t / 2, width: t, height: t, 'class': 'tpdf-poignee tpdf-poignee-' + h[0], 'data-poignee': h[0], 'stroke-width': 1.5 / z }, cadre);
    });
  }

  function pointSvg(ev) {
    var m = S.svg.getScreenCTM();
    if (!m) return { x: 0, y: 0 };
    var pt = S.svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    var r = pt.matrixTransform(m.inverse());
    return { x: r.x, y: r.y };
  }
  // Nom de l'utilisateur connecté (ctx.user de la page), pour les tampons.
  function nomUtilisateur() {
    var u = (S && S.ctx && S.ctx.user) || {};
    return String(u.nom || u.name || [u.prenom, u.nom_famille].filter(Boolean).join(' ') || u.email || '').trim();
  }
  function dateDuJour() {
    var d = new Date();
    return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + '/' + d.getFullYear();
  }

  function brancherCalque() {
    var svg = S.svg;
    svg.addEventListener('pointerdown', function (ev) {
      if (ev.pointerType === 'mouse' && ev.button !== 0) return;
      var p = pageCourante(); if (!p) return;
      var pt = pointSvg(ev), st = S.style;
      var poignee = ev.target.closest('[data-poignee]'), g = ev.target.closest('[data-id]');
      var avant = snapshot();
      if (S.outil === 'select') {
        if (poignee && S.annSel) {
          var a0 = trouverAnnot(S.annSel);
          S.drag = { mode: 'taille', id: a0.id, poignee: poignee.getAttribute('data-poignee'), orig: JSON.parse(JSON.stringify(a0)), avant: avant };
        } else if (g) {
          var id = g.getAttribute('data-id'), a1 = trouverAnnot(id);
          var changeSel = S.annSel !== id;
          S.annSel = id;
          S.drag = { mode: 'deplacer', id: id, debut: pt, orig: JSON.parse(JSON.stringify(a1)), avant: avant };
          dessinerCalque();
          if (changeSel) rendreProps();
          if (ev.detail === 2 && a1.t === 'texte') focaliserTexte();
        } else {
          if (S.annSel) { S.annSel = null; dessinerCalque(); rendreProps(); }
          return;
        }
      } else if (OUTILS_TRACE[S.outil]) {
        var a = { id: nid('n'), t: S.outil, couleur: st.couleur };
        if (S.outil === 'texte') {
          a.texte = 'Texte'; a.taille = st.taille; a.x = pt.x; a.y = pt.y - st.taille * 0.6;
          p.annots.push(a); S.annSel = a.id; pushHist(avant);
          choisirOutil('select', true); focaliserTexte();
          ev.preventDefault();
          return;
        }
        if (S.outil === 'tampon') {
          a.libelle = st.tampon; a.couleur = COULEUR_TAMPON[st.tampon] || st.couleur;
          a.date = [st.date ? dateDuJour() : '', st.signataire ? nomUtilisateur() : ''].filter(Boolean).join(' · ');
          a.h = 44; a.w = Math.max(120, mesureTexte(a.libelle.toUpperCase(), 16).w * 1.25 + 24);
          a.x = pt.x - a.w / 2; a.y = pt.y - a.h / 2;
          p.annots.push(a); S.annSel = a.id; pushHist(avant);
          choisirOutil('select', true);
          ev.preventDefault();
          return;
        }
        if (S.outil === 'ligne' || S.outil === 'fleche') { a.x1 = a.x2 = pt.x; a.y1 = a.y2 = pt.y; a.ep = st.ep; }
        else if (S.outil === 'main') { a.pts = [[pt.x, pt.y]]; a.ep = st.ep; }
        else {
          a.x = pt.x; a.y = pt.y; a.w = 0; a.h = 0;
          if (S.outil === 'surligneur') { a.opacite = st.opacite; if (a.couleur === COULEURS[0]) a.couleur = COULEURS[2]; }
          else a.ep = st.ep;
        }
        p.annots.push(a);
        S.drag = { mode: 'creer', id: a.id, debut: pt, avant: avant };
      } else if (EXT.outils[S.outil] && EXT.outils[S.outil].down) {
        var r = EXT.outils[S.outil].down(pt, p, ev, avant);
        if (!r) return;
        if (r === true) { ev.preventDefault(); return; }
        if (!r.id) r.id = nid('n');
        p.annots.push(r);
        S.drag = { mode: 'creer', id: r.id, debut: pt, avant: avant };
      } else return;
      ev.preventDefault();
      try { svg.setPointerCapture(ev.pointerId); } catch (e) { /* pointeur déjà relâché */ }
    });
    svg.addEventListener('pointermove', function (ev) {
      var dg = S.drag; if (!dg) return;
      var a = trouverAnnot(dg.id); if (!a) return;
      var pt = pointSvg(ev);
      if (dg.mode === 'deplacer') deplacer(a, dg.orig, pt.x - dg.debut.x, pt.y - dg.debut.y);
      else if (dg.mode === 'taille') redimensionner(a, dg.orig, dg.poignee, pt, a.t === 'image' || ev.shiftKey);
      else if (dg.mode === 'creer') {
        if (a.t === 'main') {
          var der = a.pts[a.pts.length - 1];
          if (Math.hypot(pt.x - der[0], pt.y - der[1]) >= 0.8) a.pts.push([pt.x, pt.y]);
        } else if (a.t === 'ligne' || a.t === 'fleche') {
          var x = pt.x, y = pt.y;
          if (ev.shiftKey) {
            var ang = Math.round(Math.atan2(y - a.y1, x - a.x1) / (Math.PI / 4)) * (Math.PI / 4), L = Math.hypot(x - a.x1, y - a.y1);
            x = a.x1 + L * Math.cos(ang); y = a.y1 + L * Math.sin(ang);
          }
          a.x2 = x; a.y2 = y;
        } else {
          var w = pt.x - dg.debut.x, h = pt.y - dg.debut.y;
          if (ev.shiftKey && a.t !== 'surligneur') { var m = Math.max(Math.abs(w), Math.abs(h)); w = w < 0 ? -m : m; h = h < 0 ? -m : m; }
          a.x = w < 0 ? dg.debut.x + w : dg.debut.x; a.y = h < 0 ? dg.debut.y + h : dg.debut.y;
          a.w = Math.abs(w); a.h = Math.abs(h);
        }
      }
      dessinerCalque();
    });
    function fin() {
      var dg = S.drag; if (!dg) return;
      S.drag = null;
      var p = pageCourante(), a = trouverAnnot(dg.id);
      if (dg.mode === 'creer' && a) {
        if (a.t === 'main') {
          if (a.pts.length < 2) p.annots.splice(p.annots.indexOf(a), 1), a = null;
        } else if (a.t === 'ligne' || a.t === 'fleche') {
          if (Math.hypot(a.x2 - a.x1, a.y2 - a.y1) < 3) { a.x2 = a.x1 + 100; a.y2 = a.y1; }
        } else if (a.w < 3 && a.h < 3) {
          var T = EXT.types[a.t], dz = T && T.tailleDefaut ? T.tailleDefaut(a) : null;
          var dw = dz ? dz[0] : a.t === 'surligneur' ? 120 : 100, dh = dz ? dz[1] : a.t === 'surligneur' ? 16 : 60;
          if (dz) { a.w = dw; a.h = dh; } else { a.x -= dw / 2; a.y -= dh / 2; a.w = dw; a.h = dh; }
        }
        if (a && EXT.types[a.t] && EXT.types[a.t].apresCreation) EXT.types[a.t].apresCreation(a);
        if (a) S.annSel = a.id;
        rendreProps();
      }
      if (snapshot() !== dg.avant) { pushHist(dg.avant); rendreBarre(); majBadges(); }
      dessinerCalque();
    }
    svg.addEventListener('pointerup', fin);
    svg.addEventListener('pointercancel', fin);
    svg.addEventListener('dblclick', function (ev) {
      var g = ev.target.closest('[data-id]'); if (!g) return;
      var a = trouverAnnot(g.getAttribute('data-id'));
      if (a && a.t === 'texte') focaliserTexte();
      else if (a && EXT.types[a.t] && EXT.types[a.t].dblclic) EXT.types[a.t].dblclic(a, pointSvg(ev));
    });
  }
  function majBadges() {
    // Le compteur d'annotations des vignettes, sans reconstruire le panneau.
    var p = pageCourante(); if (!p) return;
    var v = S.vig.querySelector('[data-uid="' + p.uid + '"] .tpdf-vig-pied'); if (!v) return;
    var b = v.querySelector('.tpdf-vig-badge');
    if (!p.annots.length) { if (b) b.remove(); return; }
    if (!b) { b = document.createElement('span'); b.className = 'tpdf-vig-badge'; v.appendChild(b); }
    b.textContent = p.annots.length;
  }
  function focaliserTexte() {
    S.el.classList.add('tpdf-props-ouvert');
    requestAnimationFrame(function () {
      var t = S.props.querySelector('textarea[data-prop="texte"]');
      if (t) { t.focus(); t.select(); }
    });
  }
  function choisirOutil(o, garderSel) {
    S.outil = o || 'select';
    if (!garderSel && S.outil !== 'select') S.annSel = null;
    rendreBarre(); rendreProps(); dessinerCalque();
  }
  function supprimerAnnot() {
    var p = pageCourante(), a = trouverAnnot(S.annSel); if (!a) return;
    var avant = snapshot();
    p.annots.splice(p.annots.indexOf(a), 1);
    S.annSel = null; pushHist(avant);
    dessinerCalque(); rendreProps(); rendreBarre(); majBadges();
  }

  /* ── Images et signature ──────────────────────────────────────────── */
  function enregistrerImage(bytes) {
    var t = typeImage(bytes);
    if (!t) return Promise.reject(new Error('image'));
    var url = urlObjet(new Blob([bytes], { type: t === 'png' ? 'image/png' : 'image/jpeg' }));
    return new Promise(function (ok, ko) {
      var im = new Image();
      im.onload = function () {
        var id = nid('i');
        S.images[id] = { bytes: bytes, type: t, url: url, w: im.naturalWidth * 0.75, h: im.naturalHeight * 0.75 };
        ok(id);
      };
      im.onerror = function () { ko(new Error('image')); };
      im.src = url;
    });
  }
  function placerImage(id, largeur) {
    var p = pageCourante(); if (!p) return;
    var d = dims(p), im = S.images[id];
    var w = Math.min(largeur || d.w * 0.4, im.w, d.w * 0.9), h = w * im.h / im.w;
    if (h > d.h * 0.6) { h = d.h * 0.6; w = h * im.w / im.h; }
    var avant = snapshot();
    var a = { id: nid('n'), t: 'image', img: id, x: (d.w - w) / 2, y: (d.h - h) / 2, w: w, h: h };
    p.annots.push(a); S.annSel = a.id; pushHist(avant);
    S.outil = 'select';
    rendreBarre(); rendreProps(); dessinerCalque(); majBadges();
  }
  async function insererImageFichier(f) {
    try {
      var id = await enregistrerImage(new Uint8Array(await f.arrayBuffer()));
      placerImage(id);
    } catch (e) { toast(msgErreur(e), 'danger'); }
  }
  function octetsDeDataUrl(u) {
    var b = atob(u.split(',')[1] || ''), out = new Uint8Array(b.length);
    for (var i = 0; i < b.length; i++) out[i] = b.charCodeAt(i);
    return out;
  }
  function lireSignature() { try { return localStorage.getItem(CLE_SIGNATURE) || ''; } catch (e) { return ''; } }
  function ecrireSignature(v) {
    try { if (v) localStorage.setItem(CLE_SIGNATURE, v); else localStorage.removeItem(CLE_SIGNATURE); } catch (e) { /* stockage indisponible */ }
  }
  async function poserSignatureDataUrl(u) {
    try { var id = await enregistrerImage(octetsDeDataUrl(u)); placerImage(id, 160); toast('Signature posée — déplacez-la à l\'endroit voulu.', 'success'); }
    catch (e) { toast(msgErreur(e), 'danger'); }
  }

  function modaleSignature() {
    var corps = document.createElement('div');
    corps.className = 'tpdf-sig';
    var memo = lireSignature();
    if (memo) {
      var bloc = document.createElement('div');
      bloc.className = 'tpdf-sig-memo';
      var im = document.createElement('img'); im.src = memo; im.alt = 'Signature enregistrée';
      var bt = document.createElement('div'); bt.className = 'tpdf-ligne';
      bt.innerHTML = '<button type="button" class="tpdf-b tpdf-b-plein" data-m="utiliser">Utiliser cette signature</button><button type="button" class="tpdf-b" data-m="oublier">Oublier</button>';
      bloc.appendChild(im); bloc.appendChild(bt);
      corps.appendChild(bloc);
    }
    var aide = document.createElement('div'); aide.className = 'tpdf-aide';
    aide.textContent = memo ? 'Ou tracer une nouvelle signature :' : 'Tracer la signature à la souris ou au doigt.';
    corps.appendChild(aide);
    var cv = document.createElement('canvas'); cv.className = 'tpdf-sig-zone';
    corps.appendChild(cv);
    var opts = document.createElement('div'); opts.className = 'tpdf-ligne tpdf-ligne-esp';
    opts.innerHTML = '<span class="tpdf-encres"></span><label class="tpdf-case"><input type="checkbox" data-m="memo" checked> Mémoriser sur ce poste</label>';
    corps.appendChild(opts);
    var encre = ENCRES[0], enc = opts.querySelector('.tpdf-encres');
    ENCRES.forEach(function (c, i) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'tpdf-pastille' + (i ? '' : ' tpdf-actif');
      b.style.background = c; b.setAttribute('aria-label', i ? 'Encre bleue' : 'Encre noire'); b.setAttribute('data-bulle', i ? 'Bleu' : 'Noir');
      b.addEventListener('click', function () { encre = c; enc.querySelectorAll('.tpdf-pastille').forEach(function (x) { x.classList.toggle('tpdf-actif', x === b); }); });
      enc.appendChild(b);
    });

    var m = ouvrirModale('Signer', corps, [
      { txt: 'Effacer', fn: function () { effacer(); } },
      { txt: 'Annuler', fn: function () { fermerModale(); } },
      { txt: 'Poser la signature', plein: true, fn: function () { poser(); } }
    ]);
    var ctx2 = cv.getContext('2d'), dpr = Math.min(window.devicePixelRatio || 1, 2), vide = true, bx = null, der = null;
    function taille() { cv.width = Math.round(cv.clientWidth * dpr); cv.height = Math.round(cv.clientHeight * dpr); }
    function effacer() { ctx2.clearRect(0, 0, cv.width, cv.height); vide = true; bx = null; }
    requestAnimationFrame(taille);
    function pos(ev) { var r = cv.getBoundingClientRect(); return [(ev.clientX - r.left) * dpr, (ev.clientY - r.top) * dpr]; }
    function etendre(q) {
      var r = 3 * dpr;
      if (!bx) bx = [q[0] - r, q[1] - r, q[0] + r, q[1] + r];
      else { bx[0] = Math.min(bx[0], q[0] - r); bx[1] = Math.min(bx[1], q[1] - r); bx[2] = Math.max(bx[2], q[0] + r); bx[3] = Math.max(bx[3], q[1] + r); }
    }
    cv.addEventListener('pointerdown', function (ev) {
      ev.preventDefault(); try { cv.setPointerCapture(ev.pointerId); } catch (e) { /* ignoré */ }
      der = pos(ev); etendre(der);
      ctx2.fillStyle = encre; ctx2.beginPath(); ctx2.arc(der[0], der[1], 1.1 * dpr, 0, Math.PI * 2); ctx2.fill();
      vide = false;
    });
    cv.addEventListener('pointermove', function (ev) {
      if (!der) return;
      var q = pos(ev);
      ctx2.strokeStyle = encre; ctx2.lineWidth = 2.4 * dpr; ctx2.lineCap = 'round'; ctx2.lineJoin = 'round';
      ctx2.beginPath(); ctx2.moveTo(der[0], der[1]); ctx2.lineTo(q[0], q[1]); ctx2.stroke();
      der = q; etendre(q);
    });
    function lever() { der = null; }
    cv.addEventListener('pointerup', lever); cv.addEventListener('pointercancel', lever);

    corps.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-m]'); if (!b) return;
      var k = b.getAttribute('data-m');
      if (k === 'utiliser') { fermerModale(); poserSignatureDataUrl(memo); }
      else if (k === 'oublier') { ecrireSignature(''); var bl = corps.querySelector('.tpdf-sig-memo'); if (bl) bl.remove(); aide.textContent = 'Tracer la signature à la souris ou au doigt.'; toast('Signature oubliée sur ce poste.', 'info'); }
    });
    function poser() {
      if (vide || !bx) { toast('Signature vide — tracez-la dans le cadre.', 'danger'); return; }
      var x0 = Math.max(0, Math.floor(bx[0])), y0 = Math.max(0, Math.floor(bx[1]));
      var w = Math.min(cv.width, Math.ceil(bx[2])) - x0, h = Math.min(cv.height, Math.ceil(bx[3])) - y0;
      var c2 = document.createElement('canvas'); c2.width = w; c2.height = h;
      c2.getContext('2d').drawImage(cv, x0, y0, w, h, 0, 0, w, h);
      var u = c2.toDataURL('image/png');
      if (corps.querySelector('[data-m="memo"]').checked) ecrireSignature(u);
      fermerModale();
      poserSignatureDataUrl(u);
    }
    return m;
  }

  /* ── Modale générique ─────────────────────────────────────────────── */
  // opts : {cle: nom du panneau dans l'adresse, large: true, ia: true}
  function ouvrirModale(titre, corps, actions, opts) {
    fermerModale(true);
    opts = opts || {};
    var fond = document.createElement('div');
    fond.className = 'tpdf-modale-fond';
    var m = document.createElement('div');
    m.className = 'tpdf-modale' + (opts.large ? ' tpdf-modale-large' : '') + (opts.ia ? ' ia-zone' : ''); m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
    var tete = document.createElement('div'); tete.className = 'tpdf-modale-tete';
    var h = document.createElement('div'); h.className = 'tpdf-modale-titre'; h.textContent = titre;
    var x = document.createElement('button'); x.type = 'button'; x.className = 'tpdf-btn tpdf-btn-mini'; x.setAttribute('data-bulle', 'Fermer'); x.setAttribute('aria-label', 'Fermer');
    x.innerHTML = ico('fermer', 16); x.addEventListener('click', fermerModale);
    tete.appendChild(h); tete.appendChild(x);
    var pied = document.createElement('div'); pied.className = 'tpdf-modale-pied';
    (actions || []).forEach(function (a) {
      var b = document.createElement('button'); b.type = 'button';
      b.className = 'tpdf-b' + (a.plein ? ' tpdf-b-plein' : '') + (a.ia ? ' ia-btn' : '');
      if (a.bulle) b.setAttribute('data-bulle', a.bulle);
      b.textContent = a.txt; b.addEventListener('click', a.fn);
      if (a.cle) b.setAttribute('data-cle', a.cle);
      pied.appendChild(b);
    });
    corps.classList.add('tpdf-modale-corps');
    m.appendChild(tete); m.appendChild(corps); m.appendChild(pied);
    fond.appendChild(m);
    fond.addEventListener('pointerdown', function (ev) { if (ev.target === fond) fermerModale(); });
    S.el.appendChild(fond);
    S.modale = fond;
    S.modaleCle = opts.cle || null;
    if (S.modaleCle) notifier();
    return { fond: fond, pied: pied, modale: m, titre: h };
  }
  function fermerModale(sansAdresse) {
    if (!S || !S.modale) return;
    S.modale.remove(); S.modale = null;
    var avait = S.modaleCle; S.modaleCle = null;
    if (avait && sansAdresse !== true) notifier();
  }

  /* ── Panneau des propriétés ───────────────────────────────────────── */
  function champ(label, input) {
    var l = document.createElement('label'); l.className = 'tpdf-prop';
    var s = document.createElement('span'); s.className = 'tpdf-lab'; s.textContent = label;
    l.appendChild(s); l.appendChild(input);
    return l;
  }
  function section(titre) {
    var s = document.createElement('section'); s.className = 'tpdf-section';
    var h = document.createElement('h3'); h.textContent = titre; s.appendChild(h);
    return s;
  }
  function majProp(cle, val, a) {
    if (a) {
      if (!S.propAvant) S.propAvant = snapshot();
      a[cle] = val;
      if (cle === 'libelle' && COULEUR_TAMPON[val]) a.couleur = COULEUR_TAMPON[val];
      dessinerCalque();
    }
    if (cle === 'libelle') S.style.tampon = val;
    else if (cle === 'date') S.style.date = !!val;
    else if (cle !== 'texte') S.style[cle] = val;
  }
  function validerProp() {
    if (S.propAvant && S.propAvant !== snapshot()) { pushHist(S.propAvant); rendreBarre(); }
    S.propAvant = null;
  }

  function rendreProps() {
    var box = S.props;
    box.textContent = '';
    var tete = document.createElement('div'); tete.className = 'tpdf-props-tete';
    tete.innerHTML = '<span>Propriétés</span>';
    var xb = document.createElement('button'); xb.type = 'button'; xb.className = 'tpdf-btn tpdf-btn-mini tpdf-props-fermer';
    xb.setAttribute('data-act', 'fermerProps'); xb.setAttribute('data-bulle', 'Fermer'); xb.setAttribute('aria-label', 'Fermer'); xb.innerHTML = ico('fermer', 16);
    tete.appendChild(xb); box.appendChild(tete);
    if (!S.pages.length) return;
    var a = trouverAnnot(S.annSel);
    var type = a ? a.t : (OUTILS_TRACE[S.outil] || EXT.outils[S.outil] ? S.outil : null);
    var E = type ? EXT.types[type] || EXT.outils[type] : null;
    var src = S.style;
    var ref = a || {
      couleur: type === 'surligneur' && src.couleur === COULEURS[0] ? COULEURS[2] : src.couleur,
      ep: src.ep, taille: src.taille, opacite: src.opacite, libelle: src.tampon, date: src.date
    };

    if (type) {
      var s = section(a ? LIBELLES[a.t] : 'Outil : ' + LIBELLES[type]);
      if (!a && AIDE_OUTIL[type]) { var ai = document.createElement('p'); ai.className = 'tpdf-aide'; ai.textContent = AIDE_OUTIL[type]; s.appendChild(ai); }
      if (E && E.props) E.props(s, a);
      if (type === 'texte') {
        if (a) {
          var ta = document.createElement('textarea'); ta.className = 'tpdf-champ'; ta.rows = 3; ta.value = a.texte; ta.setAttribute('data-prop', 'texte');
          ta.addEventListener('input', function () { majProp('texte', ta.value, a); });
          ta.addEventListener('change', validerProp);
          s.appendChild(champ('Texte', ta));
        }
        var nt = document.createElement('input'); nt.type = 'number'; nt.min = 6; nt.max = 144; nt.className = 'tpdf-champ'; nt.value = Math.round(ref.taille);
        nt.addEventListener('input', function () { var v = parseFloat(nt.value); if (v >= 4 && v <= 300) majProp('taille', v, a); });
        nt.addEventListener('change', validerProp);
        s.appendChild(champ('Taille (pt)', nt));
      }
      if (type === 'tampon') {
        var se = document.createElement('select'); se.className = 'tpdf-champ';
        TAMPONS.forEach(function (t) { var o = document.createElement('option'); o.value = t; o.textContent = t; se.appendChild(o); });
        se.value = ref.libelle;
        se.addEventListener('change', function () { majProp('libelle', se.value, a); validerProp(); rendreProps(); });
        s.appendChild(champ('Tampon', se));
        var cd = document.createElement('label'); cd.className = 'tpdf-case';
        var ci = document.createElement('input'); ci.type = 'checkbox'; ci.checked = !!ref.date;
        ci.addEventListener('change', function () { majProp('date', ci.checked ? dateDuJour() : '', a); validerProp(); });
        cd.appendChild(ci); cd.appendChild(document.createTextNode(' Date du jour'));
        s.appendChild(cd);
        if (!a && nomUtilisateur()) {
          var cn = document.createElement('label'); cn.className = 'tpdf-case';
          var ni = document.createElement('input'); ni.type = 'checkbox'; ni.checked = S.style.signataire !== false;
          ni.addEventListener('change', function () { S.style.signataire = ni.checked; });
          cn.appendChild(ni); cn.appendChild(document.createTextNode(' Nom : ' + nomUtilisateur()));
          s.appendChild(cn);
        }
      }
      if (type !== 'image' && !E) {
        var pal = document.createElement('div'); pal.className = 'tpdf-palette';
        COULEURS.forEach(function (c) {
          var b = document.createElement('button'); b.type = 'button';
          b.className = 'tpdf-pastille' + (ref.couleur && ref.couleur.toLowerCase() === c ? ' tpdf-actif' : '');
          b.style.background = c; b.setAttribute('data-bulle', NOMS_COULEURS[c] || 'Couleur'); b.setAttribute('aria-label', 'Couleur ' + (NOMS_COULEURS[c] || c).toLowerCase());
          b.addEventListener('click', function () {
            majProp('couleur', c, a); validerProp();
            pal.querySelectorAll('.tpdf-pastille').forEach(function (x) { x.classList.toggle('tpdf-actif', x === b); });
          });
          pal.appendChild(b);
        });
        s.appendChild(champ('Couleur', pal));
      }
      if (type === 'rect' || type === 'ellipse' || type === 'ligne' || type === 'fleche' || type === 'main') {
        var ep = document.createElement('input'); ep.type = 'range'; ep.min = 0.5; ep.max = 12; ep.step = 0.5; ep.value = ref.ep;
        ep.addEventListener('input', function () { majProp('ep', parseFloat(ep.value), a); });
        ep.addEventListener('change', validerProp);
        s.appendChild(champ('Épaisseur', ep));
      }
      if (type === 'surligneur') {
        var op = document.createElement('input'); op.type = 'range'; op.min = 0.1; op.max = 0.8; op.step = 0.05; op.value = ref.opacite;
        op.addEventListener('input', function () { majProp('opacite', parseFloat(op.value), a); });
        op.addEventListener('change', validerProp);
        s.appendChild(champ('Opacité', op));
      }
      if (a) {
        var del = document.createElement('button'); del.type = 'button'; del.className = 'tpdf-b tpdf-b-danger';
        del.textContent = 'Supprimer l\'annotation';
        del.addEventListener('click', supprimerAnnot);
        s.appendChild(del);
      }
      box.appendChild(s);
    } else {
      var s0 = section('Annotations');
      var p0 = document.createElement('p'); p0.className = 'tpdf-aide';
      p0.textContent = 'Choisir un outil dans la barre, puis agir sur la page. Suppr retire l\'annotation sélectionnée.';
      s0.appendChild(p0); box.appendChild(s0);
    }

    var sd = section('Document');
    var nm = document.createElement('input'); nm.type = 'text'; nm.className = 'tpdf-champ'; nm.value = S.nom;
    nm.addEventListener('input', function () { S.nom = nm.value.trim(); });
    sd.appendChild(champ('Nom du fichier', nm));
    var inf = document.createElement('p'); inf.className = 'tpdf-aide';
    var nbSrc = {}; S.pages.forEach(function (p) { nbSrc[p.src] = 1; });
    var nf = Object.keys(nbSrc).length;
    inf.textContent = S.pages.length + ' page' + (S.pages.length > 1 ? 's' : '') + (nf > 1 ? ' · ' + nf + ' fichiers fusionnés' : '') + ' · enregistré sous « ' + nomFichierSur(S.nom || 'document') + '-modifie.pdf »';
    sd.appendChild(inf);
    box.appendChild(sd);

    hook('props', box);
  }

  /* ── Recherche ────────────────────────────────────────────────────── */
  function texteDe(p) {
    var cle = p.src + ':' + p.idx;
    if (!S.textes[cle]) {
      S.textes[cle] = S.sources[p.src].pdf.getPage(p.idx + 1)
        .then(function (pg) { return pg.getTextContent(); })
        .then(function (tc) { return tc.items.filter(function (it) { return typeof it.str === 'string'; }); })
        .catch(function () { return []; });
    }
    return S.textes[cle];
  }
  async function chercher(q) {
    var jeton = ++S.rechJeton;
    q = String(q || '').trim();
    S.rech = { q: q, res: [], i: -1 };
    if (!q.length) { rendreBarre(); dessinerCalque(); return; }
    var qn = normaliser(q), res = [];
    for (var pi = 0; pi < S.pages.length; pi++) {
      var p = S.pages[pi], items = await texteDe(p);
      if (jeton !== S.rechJeton) return;
      items.forEach(function (it, ii) {
        var s = normaliser(it.str), k = s.indexOf(qn);
        while (k >= 0) { res.push({ uid: p.uid, ii: ii, k: k, n: qn.length, len: s.length }); k = s.indexOf(qn, k + 1); }
      });
    }
    S.rech.res = res;
    if (res.length) {
      var debut = 0;
      var ordre = {}; S.pages.forEach(function (p, i) { ordre[p.uid] = i; });
      for (var r = 0; r < res.length; r++) if (ordre[res[r].uid] >= S.cur) { debut = r; break; }
      S.rech.i = debut - 1;
      allerResultat(1);
    } else { rendreBarre(); dessinerCalque(); }
  }
  function allerResultat(sens) {
    var r = S.rech; if (!r.res.length) return;
    r.i = (r.i + sens + r.res.length) % r.res.length;
    var cible = r.res[r.i], i = S.pages.findIndex(function (p) { return p.uid === cible.uid; });
    if (i < 0) return;
    if (i !== S.cur) allerPage(i, true);
    else dessinerCalque();
    rendreBarre();
  }
  function dessinerResultats(p, d) {
    var r = S.rech; if (!r.res.length) return;
    var cle = p.src + ':' + p.idx, prom = S.textes[cle];
    if (!prom) return;
    var actif = r.res[r.i], svg = S.svg, uid = p.uid;
    prom.then(function (items) {
      if (!S || pageCourante() !== p) return;
      var g = sv('g', { 'class': 'tpdf-trouves' });
      r.res.forEach(function (x) {
        if (x.uid !== uid) return;
        var it = items[x.ii]; if (!it) return;
        var tr = it.transform, h = it.height || Math.hypot(tr[2], tr[3]) || 10;
        var w = it.width || 0, X0 = tr[4] + w * x.k / (x.len || 1), X1 = tr[4] + w * (x.k + x.n) / (x.len || 1);
        var c1 = versVue(d.meta.view, d.R, X0, tr[5] - h * 0.22), c2 = versVue(d.meta.view, d.R, X1, tr[5] + h * 0.88);
        sv('rect', {
          x: Math.min(c1[0], c2[0]), y: Math.min(c1[1], c2[1]), width: Math.abs(c2[0] - c1[0]), height: Math.abs(c2[1] - c1[1]),
          'class': 'tpdf-trouve' + (x === actif ? ' tpdf-trouve-actif' : '')
        }, g);
      });
      var ancien = svg.querySelector('.tpdf-trouves'); if (ancien) ancien.remove();
      svg.insertBefore(g, svg.firstChild);
      var act = g.querySelector('.tpdf-trouve-actif');
      if (act && act.scrollIntoView) act.scrollIntoView({ block: 'center', inline: 'nearest' });
    });
  }

  /* ── Export (pdf-lib) ─────────────────────────────────────────────── */
  function nettoyerTexte(font, s) {
    try { font.encodeText(s); return s; } catch (e) { /* caractère hors WinAnsi : filtré ci-dessous */ }
    var out = '';
    for (var ch of s) { try { font.encodeText(ch); out += ch; } catch (e) { out += '?'; } }
    return out;
  }
  async function dessinerPdf(L, out, pg, a, view, R, pol, imgs) {
    var T = EXT.types[a.t];
    if (T) {
      if (!T.exporter) return;
      var R2 = T.repere === 'pdf0' ? 0 : R;
      return T.exporter(a, {
        L: L, out: out, pg: pg, view: view, R: R2, rot: L.degrees(R2), pol: pol, imgs: imgs,
        P: function (u, v) { return versPdf(view, R2, u, v); }
      });
    }
    function P(u, v) { return versPdf(view, R, u, v); }
    var c = hexRgb(a.couleur), col = L.rgb(c[0], c[1], c[2]), rot = L.degrees(R);
    function boiteTexte(txt, font, size, u, v) {
      var q = P(u, v);
      pg.drawText(nettoyerTexte(font, txt), { x: q[0], y: q[1], size: size, font: font, color: col, rotate: rot });
    }
    switch (a.t) {
      case 'surligneur':
      case 'rect': {
        var c1 = P(a.x, a.y), c2 = P(a.x + a.w, a.y + a.h);
        var o = { x: Math.min(c1[0], c2[0]), y: Math.min(c1[1], c2[1]), width: Math.abs(c2[0] - c1[0]), height: Math.abs(c2[1] - c1[1]) };
        if (a.t === 'surligneur') { o.color = col; o.opacity = a.opacite; o.blendMode = L.BlendMode.Multiply; }
        else { o.borderColor = col; o.borderWidth = a.ep; }
        pg.drawRectangle(o);
        break;
      }
      case 'ellipse': {
        var ce = P(a.x + a.w / 2, a.y + a.h / 2), rx = a.w / 2, ry = a.h / 2;
        if (R % 180) { var t = rx; rx = ry; ry = t; }
        pg.drawEllipse({ x: ce[0], y: ce[1], xScale: rx, yScale: ry, borderColor: col, borderWidth: a.ep });
        break;
      }
      case 'ligne':
      case 'fleche': {
        var p1 = P(a.x1, a.y1), p2 = P(a.x2, a.y2);
        pg.drawLine({ start: { x: p1[0], y: p1[1] }, end: { x: p2[0], y: p2[1] }, thickness: a.ep, color: col, lineCap: L.LineCapStyle.Round });
        if (a.t === 'fleche') {
          var tri = pointesFleche(a).map(function (q) { var r = P(q[0], q[1]); return r[0].toFixed(2) + ' ' + (-r[1]).toFixed(2); });
          pg.drawSvgPath('M' + tri[0] + ' L' + tri[1] + ' L' + tri[2] + ' Z', { x: 0, y: 0, color: col });
        }
        break;
      }
      case 'main': {
        var d = a.pts.map(function (q, i) { var r = P(q[0], q[1]); return (i ? 'L' : 'M') + r[0].toFixed(2) + ' ' + (-r[1]).toFixed(2); }).join(' ');
        pg.drawSvgPath(d, { x: 0, y: 0, borderColor: col, borderWidth: a.ep, borderLineCap: L.LineCapStyle.Round });
        break;
      }
      case 'texte': {
        var ft = await pol.police(a.texte, {});
        String(a.texte).split('\n').forEach(function (l, i) {
          if (l) boiteTexte(l, ft, a.taille, a.x, a.y + a.taille * ASC + i * a.taille * INTERLIGNE);
        });
        break;
      }
      case 'tampon': {
        var ep = a.h * 0.06, k1 = P(a.x + ep / 2, a.y + ep / 2), k2 = P(a.x + a.w - ep / 2, a.y + a.h - ep / 2);
        pg.drawRectangle({ x: Math.min(k1[0], k2[0]), y: Math.min(k1[1], k2[1]), width: Math.abs(k2[0] - k1[0]), height: Math.abs(k2[1] - k1[1]), borderColor: col, borderWidth: ep });
        var lib = nettoyerTexte(pol.g, a.libelle.toUpperCase()), s1 = a.date ? a.h * 0.36 : a.h * 0.5;
        var w1 = pol.g.widthOfTextAtSize(lib, s1);
        boiteTexte(lib, pol.g, s1, a.x + (a.w - w1) / 2, a.y + (a.date ? a.h * 0.56 : a.h * 0.68));
        if (a.date) {
          var s2 = a.h * 0.19, w2 = pol.n.widthOfTextAtSize(a.date, s2);
          boiteTexte(a.date, pol.n, s2, a.x + (a.w - w2) / 2, a.y + a.h * 0.84);
        }
        break;
      }
      case 'image': {
        var im = S.images[a.img]; if (!im) break;
        if (!imgs[a.img]) imgs[a.img] = im.type === 'png' ? await out.embedPng(im.bytes) : await out.embedJpg(im.bytes);
        var bl = P(a.x, a.y + a.h);
        pg.drawImage(imgs[a.img], { x: bl[0], y: bl[1], width: a.w, height: a.h, rotate: rot });
        break;
      }
    }
  }

  async function construire(pages) {
    var L = await pdflib();
    var out = await L.PDFDocument.create();
    var cpol = { out: out, L: L, std: {}, uni: {} };
    var pol = {
      n: await policePour(cpol, '', {}), g: await policePour(cpol, '', { gras: true }),
      police: function (txt, st) { return policePour(cpol, txt, st); },
      nettoyer: nettoyerTexte
    };
    var ctx = { L: L, out: out, pol: pol, pages: pages, optionsSave: null };
    var parSrc = {}, ordre = [];
    pages.forEach(function (p) {
      if (!parSrc[p.src]) { parSrc[p.src] = []; ordre.push(p.src); }
      parSrc[p.src].push(p.idx);
    });
    var copies = {};
    for (var i = 0; i < ordre.length; i++) {
      var id = ordre[i], doc = EXT.docPourExport ? await EXT.docPourExport(S.sources[id], L, ctx) : S.sources[id].lib;
      copies[id] = await out.copyPages(doc, parSrc[id]);
    }
    var imgs = {};
    for (var j = 0; j < pages.length; j++) {
      var p = pages[j], pg = copies[p.src].shift();
      out.addPage(pg);
      var d = dims(p);
      pg.setRotation(L.degrees(d.R));
      if (p.crop) pg.setCropBox(p.crop[0], p.crop[1], p.crop[2] - p.crop[0], p.crop[3] - p.crop[1]);
      for (var k = 0; k < p.annots.length; k++) await dessinerPdf(L, out, pg, p.annots[k], d.meta.view, d.R, pol, imgs);
      // Par page, après les annotations : format, numérotation, filigrane, OCR…
      await hookAsync('exportPage', pg, p, d, ctx, j, pages.length);
      // Puis ce qui change la page elle-même (format) et l'habille (numéros, filigrane).
      await hookAsync('exportPageFin', pg, p, d, ctx, j, pages.length);
      // En dernier : repères d'impression (la page grandit autour du format fini).
      await hookAsync('exportPageMarques', pg, p, d, ctx, j, pages.length);
    }
    await hookAsync('export', ctx);
    // Dernière passe : une extension peut remplacer le document produit
    // (floutage : pages refaites en image dans un document neuf).
    await hookAsync('exportFinal', ctx);
    // Toute dernière passe, sur le document qui sera écrit (nettoyage des métadonnées).
    await hookAsync('exportDernier', ctx);
    // Après tout remaniement du document (aplatissement en image compris) :
    // signets, pièces jointes, métadonnées, nettoyage.
    await hookAsync('exportApres', ctx);
    return (ctx.final || out).save(ctx.optionsSave || {});
  }
  function nomBase() { return nomFichierSur(S.nom || 'document'); }

  async function enregistrer() {
    if (!S.pages.length) return;
    if (S.occupe) { toast('Opération en cours — patientez.', 'info'); return; }
    occuper('Enregistrement…');
    try {
      var b = await construire(S.pages);
      telecharger(b, nomBase() + '-modifie.pdf');
      toast('PDF enregistré — ' + tailleLisible(b.length) + '.', 'success');
    } catch (e) { toast(msgErreur(e), 'danger'); }
    finally { liberer(); }
  }

  async function imprimer() {
    if (S.occupe) { toast('Opération en cours — patientez.', 'info'); return; }
    occuper('Préparation de l\'impression…');
    try {
      var b = await construire(S.pages);
      var u = urlObjet(new Blob([b], { type: 'application/pdf' }));
      var ancien = S.el.querySelector('.tpdf-impression'); if (ancien) ancien.remove();
      var f = document.createElement('iframe');
      f.className = 'tpdf-impression'; f.setAttribute('aria-hidden', 'true'); f.title = 'Impression';
      f.onload = function () {
        setTimeout(function () {
          try { f.contentWindow.focus(); f.contentWindow.print(); }
          catch (e) { window.open(u, '_blank'); }
        }, 300);
      };
      f.src = u;
      S.el.appendChild(f);
    } catch (e) { toast(msgErreur(e), 'danger'); }
    finally { liberer(); }
  }

  async function extraireSelection() {
    var l = S.pages.filter(function (p) { return S.sel[p.uid]; });
    if (!l.length) { toast('Aucune page sélectionnée — cliquer une vignette.', 'info'); return; }
    if (S.occupe) return;
    occuper('Export…');
    try {
      var b = await construire(l);
      telecharger(b, nomBase() + '-extrait.pdf');
      toast(l.length + ' page' + (l.length > 1 ? 's exportées' : ' exportée') + ' — ' + tailleLisible(b.length) + '.', 'success');
    } catch (e) { toast(msgErreur(e), 'danger'); }
    finally { liberer(); }
  }

  function modaleDecouper() {
    var n = S.pages.length;
    var corps = document.createElement('div');
    corps.innerHTML =
      '<label class="tpdf-case"><input type="radio" name="tpdf-dec" value="page" checked> Un fichier par page (' + n + ' fichier' + (n > 1 ? 's' : '') + ')</label>' +
      '<label class="tpdf-case"><input type="radio" name="tpdf-dec" value="plages"> Par plages</label>' +
      '<label class="tpdf-prop"><span class="tpdf-lab">Plages</span><input type="text" class="tpdf-champ" data-m="plages" placeholder="1-3, 5, 8-10"></label>' +
      '<p class="tpdf-aide">Chaque plage donne un fichier. Numéros de page de l\'ordre actuel des vignettes.</p>';
    var inp = corps.querySelector('[data-m="plages"]');
    function versPlages() { corps.querySelector('input[value="plages"]').checked = true; }
    inp.addEventListener('focus', versPlages);
    inp.addEventListener('input', versPlages);
    inp.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); lancer(); } });
    ouvrirModale('Découper le document', corps, [
      { txt: 'Annuler', fn: fermerModale },
      { txt: 'Découper', plein: true, fn: lancer }
    ]);
    async function lancer() {
      var groupes;
      if (corps.querySelector('input[value="page"]').checked) {
        groupes = S.pages.map(function (_, i) { return { a: i + 1, b: i + 1 }; });
      } else {
        try { groupes = lirePlages(inp.value, n); } catch (e) { toast(e.message, 'danger'); inp.focus(); return; }
      }
      fermerModale();
      if (S.occupe) return;
      try {
        for (var i = 0; i < groupes.length; i++) {
          occuper('Découpage ' + (i + 1) + ' / ' + groupes.length + '…');
          var g = groupes[i], b = await construire(S.pages.slice(g.a - 1, g.b));
          telecharger(b, nomBase() + '-p' + g.a + (g.b > g.a ? '-' + g.b : '') + '.pdf');
          await attendre(350);
        }
        toast(groupes.length + ' fichier' + (groupes.length > 1 ? 's téléchargés' : ' téléchargé') + '.', 'success');
      } catch (e) { toast(msgErreur(e), 'danger'); }
      finally { liberer(); }
    }
  }

  async function rasteriser(bytes, dpi, qualite, suivi) {
    var pj = await pdfjs(), L = await pdflib();
    var doc = await pj.getDocument({ data: bytes.slice(), isEvalSupported: false }).promise;
    var out = await L.PDFDocument.create();
    try {
      for (var i = 1; i <= doc.numPages; i++) {
        if (suivi) suivi(i, doc.numPages);
        var pg = await doc.getPage(i);
        var vp1 = pg.getViewport({ scale: 1 }), vp = pg.getViewport({ scale: dpi / 72 });
        var cv = document.createElement('canvas');
        cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
        var c = cv.getContext('2d'); c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
        // intent « print » : pas de requestAnimationFrame, donc la compression
        // continue si l'utilisateur passe sur un autre onglet.
        await pg.render({ canvasContext: c, viewport: vp, intent: 'print' }).promise;
        var blob = await new Promise(function (ok) { cv.toBlob(ok, 'image/jpeg', qualite); });
        var img = await out.embedJpg(new Uint8Array(await blob.arrayBuffer()));
        var np = out.addPage([vp1.width, vp1.height]);
        np.drawImage(img, { x: 0, y: 0, width: vp1.width, height: vp1.height });
        cv.width = cv.height = 0;
      }
    } finally { try { doc.destroy(); } catch (e) { /* déjà libéré */ } }
    return out.save();
  }

  function modaleCompresser() {
    var corps = document.createElement('div');
    corps.innerHTML =
      '<label class="tpdf-case"><input type="checkbox" data-m="raster" checked> Convertir les pages en images (réduit fortement les scans)</label>' +
      '<div class="tpdf-ligne tpdf-ligne-esp">' +
        '<label class="tpdf-prop"><span class="tpdf-lab">Résolution</span><select class="tpdf-champ" data-m="dpi"><option value="100">100 dpi</option><option value="150" selected>150 dpi</option><option value="200">200 dpi</option></select></label>' +
        '<label class="tpdf-prop"><span class="tpdf-lab">Qualité JPEG <b data-m="qv">70</b></span><input type="range" min="30" max="95" step="5" value="70" data-m="q"></label>' +
      '</div>' +
      '<p class="tpdf-aide">Une page convertie en image n\'a plus de texte sélectionnable ni de champ de formulaire.</p>' +
      '<div class="tpdf-resultat" data-m="res"></div>';
    var q = corps.querySelector('[data-m="q"]'), qv = corps.querySelector('[data-m="qv"]'), res = corps.querySelector('[data-m="res"]');
    q.addEventListener('input', function () { qv.textContent = q.value; });
    var m = ouvrirModale('Compresser', corps, [
      { txt: 'Annuler', fn: fermerModale },
      { txt: 'Compresser et télécharger', plein: true, fn: lancer, cle: 'go' }
    ]);
    var go = m.pied.querySelector('[data-cle="go"]');
    async function lancer() {
      if (S.occupe) return;
      go.disabled = true;
      var raster = corps.querySelector('[data-m="raster"]').checked;
      var dpi = parseInt(corps.querySelector('[data-m="dpi"]').value, 10), qual = parseInt(q.value, 10) / 100;
      var ids = {}; S.pages.forEach(function (p) { ids[p.src] = 1; });
      var avant = Object.keys(ids).reduce(function (t, id) { return t + S.sources[id].bytes.length; }, 0);
      res.textContent = 'Compression en cours…';
      occuper('Compression…');
      try {
        var b = await construire(S.pages);
        if (raster) b = await rasteriser(b, dpi, qual, function (i, n) { res.textContent = 'Compression — page ' + i + ' / ' + n + '…'; });
        var gain = avant ? Math.min(99, Math.round((1 - b.length / avant) * 100)) : 0;
        res.textContent = 'Avant : ' + tailleLisible(avant) + ' → Après : ' + tailleLisible(b.length) + (gain > 0 ? ' (−' + gain + ' %)' : gain < 0 ? ' (+' + (-gain) + ' %)' : '');
        if (gain <= 0) {
          res.textContent += ' — rien à gagner, fichier non téléchargé.';
          toast('Pas de gain sur ce document' + (raster ? ' : son contenu est déjà vectoriel, l\'image pèse plus lourd.' : '.'), 'info');
        } else {
          telecharger(b, nomBase() + '-compresse.pdf');
          toast('PDF compressé — ' + gain + ' % de moins.', 'success');
        }
      } catch (e) { res.textContent = ''; toast(msgErreur(e), 'danger'); }
      finally { liberer(); go.disabled = false; }
    }
  }

  /* ── Montage ──────────────────────────────────────────────────────── */
  function mount(root, ctx) {
    if (!root) return;
    if (S && S.el) {
      if (ctx) S.ctx = ctx;
      S.root = root;
      if (S.el.parentNode !== root) root.appendChild(S.el);
      if (S.pages.length) rendrePage();
      return;
    }
    S = etatNeuf(root, ctx);
    construireDom();
    root.appendChild(S.el);
    toutRendre();
    var monEtat = S;
    chargerExtensions().then(function () {
      if (S !== monEtat || !S.el) return;
      placerBoutonsExt(); hook('monte'); toutRendre();
    });
  }
  function demonter() {
    if (!S) return;
    var s = S;
    hook('demonter');
    if (s.menuFermer) document.removeEventListener('pointerdown', s.menuFermer, true);
    if (s.ecoute) document.removeEventListener('keydown', s.ecoute);
    if (s.ro) { try { s.ro.disconnect(); } catch (e) { /* déjà déconnecté */ } }
    if (s.tache) { try { s.tache.cancel(); } catch (e) { /* rendu fini */ } }
    s.urls.forEach(function (u) { try { URL.revokeObjectURL(u); } catch (e) { /* déjà libérée */ } });
    Object.keys(s.sources).forEach(function (k) { try { s.sources[k].pdf.destroy(); } catch (e) { /* déjà libéré */ } });
    if (s.el && s.el.parentNode) s.el.parentNode.removeChild(s.el);
    S = null;
  }
  function aller(a) {
    a = a || {};
    var n = parseInt(a.page, 10), pan = a.panneau && EXT.panneaux[a.panneau] ? a.panneau : null;
    if (!S || !S.pages.length) {
      if (S) { if (n >= 1) S.pageDemandee = n; S.panneauDemande = pan; }
      return;
    }
    if (n >= 1 && n <= S.pages.length) allerPage(n - 1, false);
    if (pan && S.modaleCle !== pan) EXT.panneaux[pan]();
    else if (!pan && S.modaleCle && a.panneau !== undefined) fermerModale(true);
  }

  // Ce que voient les extensions (mysifa_tools_pdf_*.js). Elles ne lisent l'état
  // qu'à l'appel : etat() rend l'objet courant, null hors montage.
  var API = {
    ext: EXT, etat: function () { return S; }, IC: IC, ico: ico, bouton: bouton, outilBtn: outilBtn,
    COULEURS: COULEURS, NOMS_COULEURS: NOMS_COULEURS, BULLES: BULLES, touche: touche, LIBELLES: LIBELLES, AIDE_OUTIL: AIDE_OUTIL, ASC: ASC, INTERLIGNE: INTERLIGNE, POLICE: POLICE,
    pdfjs: pdfjs, pdflib: pdflib, fontkit: fontkit, octetsNoto: octetsNoto, cleStandard: cleStandard, encodable: encodable,
    nid: nid, toast: toast, msgErreur: msgErreur, snapshot: snapshot, pushHist: pushHist, notifier: notifier,
    pageCourante: pageCourante, dims: dims, trouverAnnot: trouverAnnot, versPdf: versPdf, versVue: versVue,
    hexRgb: hexRgb, sv: sv, boite: boite, mesureTexte: mesureTexte, nettoyerTexte: nettoyerTexte,
    dessinerCalque: dessinerCalque, rendreProps: rendreProps, rendreBarre: rendreBarre, toutRendre: toutRendre,
    rendrePage: rendrePage, rendreVignettes: rendreVignettes, allerPage: allerPage, choisirOutil: choisirOutil, majBadges: majBadges,
    champ: champ, section: section, majProp: majProp, validerProp: validerProp, focaliserTexte: focaliserTexte,
    ouvrirModale: ouvrirModale, fermerModale: fermerModale, ajouterSource: ajouterSource, nouvellePage: nouvellePage,
    occuper: occuper, liberer: liberer, construire: function (pages) { return construire(pages || S.pages); },
    // Lot 3
    TAMPONS: TAMPONS, COULEUR_TAMPON: COULEUR_TAMPON, viewportPour: viewportPour, rasteriser: rasteriser,
    telecharger: telecharger, urlObjet: urlObjet, lirePlages: lirePlages, groupesParN: groupesParN,
    deplacer: deplacer, nomBase: nomBase, nomUtilisateur: nomUtilisateur, imageVersPdf: imageVersPdf,
    enregistrerImage: enregistrerImage, tailleLisible: tailleLisible, chargerScript: chargerScript,
    pagesCiblees: pagesCiblees, normaliser: normaliser, texteDe: texteDe, dateDuJour: dateDuJour, MON_SRC: MON_SRC,
    fermerMenu: fermerMenu, pdflibModule: pdflib, ajouterSourceFichier: ouvrirFichiers, enregistrer: enregistrer
  };
  function etendre(fn) { try { fn(API); } catch (e) { if (window.console) console.error(e); } }

  window.MyToolsPDF = {
    mount: mount,
    etendre: etendre,
    demonter: demonter,
    adresse: { etat: function () { return etatAdresse(); }, aller: aller, cles: ['page', 'panneau'] },
    // Fonctions pures, exposées pour tests/test_tools_pdf.js.
    _interne: {
      versPdf: versPdf, versVue: versVue, tournerPoint: tournerPoint, lirePlages: lirePlages,
      deplacerSelection: deplacerSelection, normaliser: normaliser, tailleLisible: tailleLisible,
      hexRgb: hexRgb, cleStandard: cleStandard, groupesParN: groupesParN, sansExt: sansExt, nomFichierSur: nomFichierSur, typeImage: typeImage,
      etat: function () { return S; }, ouvrirFichiers: function (f) { return S && ouvrirFichiers(f); },
      construire: function () { return S && construire(S.pages); }
    }
  };
})();
