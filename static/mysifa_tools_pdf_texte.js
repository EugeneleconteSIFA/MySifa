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
  // pdf.js découpe souvent une ligne en plusieurs éléments (changement de
  // police, accent, crénage, lettres espacées). Un bloc = les éléments
  // consécutifs d'une même ligne de base (±25 % de la hauteur), séparés de
  // moins d'1,5 espace. Largeur = union des éléments, pas celle d'un seul.
  function grouperItems(items) {
    var blocs = [], cur = null;
    (items || []).forEach(function (it, i) {
      var tr = it.transform, str = it.str || '';
      // Lettres espacées : pdf.js rend « L E T T R E S » ; on retrouve « LETTRES ».
      if (str.length >= 5 && /^(\S )+\S$/.test(str)) str = str.replace(/ /g, '');
      if (!tr || (!str && !(it.width > 0))) { if (it.hasEOL) cur = null; return; }
      if (!estHorizontal(tr)) { cur = null; return; }
      var h = Math.abs(tr[3]) || Math.hypot(tr[2], tr[3]) || 10, x0 = tr[4], x1 = tr[4] + (it.width || 0), vide = !str.trim();
      if (cur) {
        var H = Math.max(h, cur.h), gap = x0 - cur.X1;
        if (Math.abs(tr[5] - cur.Y) <= 0.25 * H && gap < 1.5 * 0.28 * H && gap > -H) {
          if (gap > 0.15 * H && !/\s$/.test(cur.str) && !/^\s/.test(str)) cur.str += ' ';
          cur.str += str; cur.X1 = Math.max(cur.X1, x1); cur.X0 = Math.min(cur.X0, x0); cur.h = H; cur.idx.push(i);
          if (!vide && str.trim().length > cur.principal.str.trim().length) cur.principal = it;
          if (it.hasEOL) cur = null;
          return;
        }
      }
      if (vide) { cur = null; return; }
      cur = { idx: [i], premier: i, str: str, X0: x0, X1: x1, Y: tr[5], h: h, principal: it };
      blocs.push(cur);
      if (it.hasEOL) cur = null;
    });
    blocs.forEach(function (b) { b.str = b.str.replace(/\s+$/, ''); });
    return blocs;
  }
  function boiteBloc(b, view) {
    var r = boiteItem([b.h, 0, 0, b.h, b.X0, b.Y], b.X1 - b.X0, view);
    r.largeur = b.X1 - b.X0;
    return r;
  }
  // Espacement par caractère pour qu'un texte mesuré `mesure` occupe `cible`.
  function espacement(cible, mesure, n, taille) {
    if (!(cible > 0) || !(n > 0)) return 0;
    var e = (cible - mesure) / n;
    e = Math.max(-0.1 * taille, Math.min(0.6 * taille, e));
    return Math.abs(e) < 0.01 ? 0 : e;
  }
  // Nom de police PDF + indices pdf.js -> famille standard, gras, italique.
  function correspondancePolice(info) {
    info = info || {};
    var nom = String(info.nom || '').replace(/^[A-Z]{6}\+/, '').toLowerCase();
    var css = String(info.famille || '').toLowerCase();
    var mono = !!info.mono || /courier|mono|consol|menlo|inconsolata|fixed/.test(nom) || css === 'monospace';
    var serif = !mono && (!!info.serif || css === 'serif' ||
      (/times|georgia|garamond|cambria|minion|book|roman|palatino|baskerville|bodoni|caslon|century|serif/.test(nom) && !/sans/.test(nom)));
    var gras = /bold|black|heavy|semibold|semi-bold|demi|extrabold|ultra|[-,]bd\b|[-,]blk\b/.test(nom);
    var maigre = /light|thin|hairline|regular|book|roman|normal|medium|[-,]rg\b|[-,]lt\b/.test(nom);
    return {
      famille: mono ? 'mono' : serif ? 'serif' : 'sans',
      gras: !!info.gras || gras,
      italique: !!info.italique || /italic|oblique|[-,]it\b/.test(nom),
      // La graisse se lit-elle dans le nom ? Sinon on la mesure sur les pixels.
      graisseConnue: !!info.gras || gras || maigre
    };
  }
  /* Mesure sur les pixels : la largeur déclarée par getTextContent ne colle
     pas toujours à ce qui est dessiné (police intégrée, Tc, Tz). On part de la
     boîte déclarée et on suit l'encre réelle. Coordonnées en pixels. */
  function dist2(d, i, f) { var a = d[i] - f[0], b = d[i + 1] - f[1], c = d[i + 2] - f[2]; return a * a + b * b + c * c; }
  // Fond = médiane, canal par canal, des pixels du bord de la bande.
  function fondBande(d, W, H, x0, x1, y0, y1) {
    var r = [], g = [], b = [];
    function prendre(x, y) { if (x < 0 || y < 0 || x >= W || y >= H) return; var i = (y * W + x) * 4; r.push(d[i]); g.push(d[i + 1]); b.push(d[i + 2]); }
    for (var x = x0; x < x1; x++) { prendre(x, y0); prendre(x, y1 - 1); }
    for (var y = y0; y < y1; y++) { prendre(x0, y); prendre(x1 - 1, y); }
    function med(t) { t.sort(function (u, v) { return u - v; }); return t.length ? t[t.length >> 1] : 255; }
    return [med(r), med(g), med(b)];
  }
  // b : boîte déclarée {x, y, w, h, base, taille} en pixels.
  // o : {gauche, droite} bornes (bloc voisin), seuil (écart d'encre).
  function mesurerEncre(d, W, H, b, o) {
    o = o || {};
    var t = b.taille, base = Math.round(b.base);
    var c0 = Math.max(0, Math.round(base - 0.72 * t)), c1 = Math.min(H, Math.round(base - 0.05 * t));
    // Bande verticale : des accents sur capitales (base − 1,05 corps) aux
    // jambages (base + 0,3 corps), pas plus : au-delà, c'est la ligne voisine.
    var y0 = Math.max(0, Math.round(base - 1.05 * t)), y1 = Math.min(H, Math.round(base + 0.3 * t));
    var gMin = Math.max(0, Math.round(o.gauche != null ? o.gauche : b.x - 40 * t));
    var dMax = Math.min(W, Math.round(o.droite != null ? o.droite : b.x + b.w + 40 * t));
    var fond = o.fond || fondBande(d, W, H, Math.max(gMin, Math.round(b.x - t)), Math.min(dMax, Math.round(b.x + b.w + t)), y0, y1);
    var s2 = Math.pow(o.seuil || 70, 2), trou = Math.max(2, Math.round((o.trou || 0.6) * t));
    function encre(x, ya, yb) { for (var y = ya; y < yb; y++) if (dist2(d, (y * W + x) * 4, fond) > s2) return true; return false; }
    var xl = Math.round(b.x), xr = Math.round(b.x + b.w), x, vide;
    for (x = xr, vide = 0; x < dMax; x++) { if (encre(x, c0, c1)) { xr = x + 1; vide = 0; } else if (++vide > trou) break; }
    for (x = xl - 1, vide = 0; x >= gMin; x--) { if (encre(x, c0, c1)) { xl = x; vide = 0; } else if (++vide > trou) break; }
    // Haut et bas : encre réelle dans la largeur trouvée ; hauteur de capitale
    // = médiane des sommets des colonnes encrées les plus hautes (accents exclus).
    var haut = Math.round(b.y), bas = Math.round(b.y + b.h), sommets = [], y;
    for (x = xl; x < xr; x++) {
      var premier = -1, dernier = -1;
      for (y = y0; y < y1; y++) if (dist2(d, (y * W + x) * 4, fond) > s2) { if (premier < 0) premier = y; dernier = y; }
      if (premier >= 0) { sommets.push(premier); haut = Math.min(haut, premier); bas = Math.max(bas, dernier + 1); }
    }
    sommets.sort(function (u, v) { return u - v; });
    var cap = sommets.length ? base - sommets[Math.min(sommets.length - 1, Math.floor(sommets.length * 0.5))] : null;
    return { x: xl, y: haut, w: xr - xl, h: bas - haut, cap: cap, fond: fond };
  }
  // Épaisseur des traits / hauteur de capitale, sur une ligne à mi-hauteur.
  function epaisseurTraits(d, W, m, base, cap, fond, seuil) {
    if (!cap) return null;
    var y = Math.round(base - cap * 0.45), s2 = Math.pow(seuil || 110, 2), runs = [], n = 0;
    for (var x = m.x; x < m.x + m.w; x++) {
      if (dist2(d, (y * W + x) * 4, fond) > s2) n++;
      else if (n) { runs.push(n); n = 0; }
    }
    if (n) runs.push(n);
    if (!runs.length) return null;
    runs.sort(function (u, v) { return u - v; });
    return runs[runs.length >> 1] / cap;
  }
  // Pour chaque bloc, abscisses (PDF) du voisin de gauche et de droite sur sa ligne.
  function bornesVoisins(blocs) {
    return blocs.map(function (b) {
      var g = null, dr = null;
      blocs.forEach(function (o) {
        if (o === b || Math.abs(o.Y - b.Y) > 0.25 * Math.max(o.h, b.h)) return;
        if (o.X1 <= b.X0 + 0.5) g = g == null ? o.X1 : Math.max(g, o.X1);
        else if (o.X0 >= b.X1 - 0.5) dr = dr == null ? o.X0 : Math.min(dr, o.X0);
      });
      return [g, dr];
    });
  }
  var CAPITALE = { sans: 0.718, serif: 0.662, mono: 0.571 };
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
  M._interne.texte = { mesurerEncre: mesurerEncre, fondBande: fondBande, epaisseurTraits: epaisseurTraits, bornesVoisins: bornesVoisins, boiteItem: boiteItem, estHorizontal: estHorizontal, grouperItems: grouperItems, boiteBloc: boiteBloc, espacement: espacement, correspondancePolice: correspondancePolice, echantillonner: echantillonner, rgbHex: rgbHex };

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
        var n = 0, blocs = grouperItems(tc.items), bornes = bornesVoisins(blocs), divs = [];
        blocs.forEach(function (bl, bi) {
          var ii = bl.premier, b = boiteBloc(bl, d.meta.view);
          var z0 = document.createElement('div');
          z0.className = 'tpdf-tx';
          var deja = trouverRemplace(p, ii);
          if (deja) z0.classList.add('tpdf-tx-fait');
          z0.style.left = (b.x * z) + 'px'; z0.style.top = (b.y * z) + 'px';
          z0.style.width = (b.w * z) + 'px'; z0.style.height = (b.h * z) + 'px';
          z0.setAttribute('data-bulle', deja ? 'Reprendre' : 'Modifier');
          z0.addEventListener('click', function (ev) { ev.stopPropagation(); ouvrir(p, d, z, bl, tc, bornes[bi]); });
          s.html.appendChild(z0); n++; divs.push([z0, bl, bi]);
        });
        // Puis la boîte réelle, mesurée sur l'encre du rendu.
        if (n) rendu2(src, p.idx).then(function (px) {
          if (S() !== s || _zonesPour !== cle) return;
          divs.forEach(function (x) {
            var m = x[1].mes || (x[1].mes = mesureBloc(x[1], px, d.meta.view, bornes[x[2]]));
            x[0].style.left = (m.box.x * z) + 'px'; x[0].style.top = (m.box.y * z) + 'px';
            x[0].style.width = (m.box.w * z) + 'px'; x[0].style.height = (m.box.h * z) + 'px';
          });
        }).catch(function () { /* boîtes déclarées conservées */ });
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
    var _cm = null;
    function mesureCss(txt, a) {
      if (!_cm) _cm = document.createElement('canvas').getContext('2d');
      _cm.font = (a.police.italique ? 'italic ' : '') + (a.police.gras ? 'bold ' : '') + a.taille + 'px ' + cssPolice(a.police);
      return _cm.measureText(txt).width;
    }
    // Rendu dédié de la page (non pivotée, 2,5 px par point) pour mesurer
    // l'encre ; un seul gardé par source.
    var K2 = 2.5;
    function rendu2(src, idx) {
      if (src._px && src._px.idx === idx) return src._px.p;
      var pr = src.pdf.getPage(idx + 1).then(function (pg) {
        var vp = pg.getViewport({ scale: K2, rotation: 0 }), cv = document.createElement('canvas');
        cv.width = Math.ceil(vp.width); cv.height = Math.ceil(vp.height);
        var c = cv.getContext('2d', { willReadFrequently: true });
        c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
        // intent « print » : pas d'attente d'affichage (onglet en arrière-plan).
        return pg.render({ canvasContext: c, viewport: vp, intent: 'print' }).promise.then(function () {
          return { data: c.getImageData(0, 0, cv.width, cv.height).data, W: cv.width, H: cv.height, k: K2 };
        });
      });
      src._px = { idx: idx, p: pr };
      pr.catch(function () { if (src._px && src._px.p === pr) src._px = null; });
      return pr;
    }
    function mesureBloc(bl, px, view, bornes) {
      var b = boiteBloc(bl, view), k = px.k;
      var bp = { x: b.x * k, y: b.y * k, w: b.w * k, h: b.h * k, base: b.by * k, taille: b.taille * k };
      var o = {};
      if (bornes && bornes[0] != null) o.gauche = (bornes[0] - view[0]) * k + 1;
      if (bornes && bornes[1] != null) o.droite = (bornes[1] - view[0]) * k - 1;
      var m = mesurerEncre(px.data, px.W, px.H, bp, o);
      return {
        decl: b, box: { x: m.x / k, y: m.y / k, w: m.w / k, h: m.h / k },
        cap: m.cap ? m.cap / k : null, fond: m.fond,
        ep: epaisseurTraits(px.data, px.W, m, bp.base, m.cap, m.fond)
      };
    }
    function echantillonPx(px, b) {
      var k = px.k, W = px.W, H = px.H, d = px.data;
      function zone(x0, y0, x1, y1, out) {
        x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0)); x1 = Math.min(W, Math.ceil(x1)); y1 = Math.min(H, Math.ceil(y1));
        for (var y = y0; y < y1; y++) for (var x = x0; x < x1; x++) { var i = (y * W + x) * 4; out.push(d[i], d[i + 1], d[i + 2], 255); }
      }
      var x0 = b.x * k, y0 = b.y * k, x1 = (b.x + b.w) * k, y1 = (b.y + b.h) * k, e = 2 * k, int = [], an = [];
      zone(x0, y0, x1, y1, int);
      zone(x0 - e, y0 - e, x1 + e, y0, an); zone(x0 - e, y1, x1 + e, y1 + e, an);
      zone(x0 - e, y0, x0, y1, an); zone(x1, y0, x1 + e, y1, an);
      return echantillonner(int, an);
    }
    // Prépare la correction d'un bloc (mesures, police, couleurs), sans la poser.
    async function preparer(p, d, bl, tc, bornes) {
      var src = S().sources[p.src], ii = bl.premier, str = bl.str, px = null;
      try { px = await rendu2(src, p.idx); } catch (e) { px = null; }
      var b = boiteBloc(bl, d.meta.view), m = px ? (bl.mes || (bl.mes = mesureBloc(bl, px, d.meta.view, bornes))) : null;
      var box = m ? m.box : b, pol = infoPolice(tc, bl.principal);
      // Graisse absente du nom de la police : on la lit sur l'épaisseur des traits.
      if (m && !pol.graisseConnue && m.ep != null && m.ep > 0.16) pol.gras = true;
      // Taille : hauteur de capitale mesurée, si elle reste plausible.
      var taille = b.taille;
      if (m && m.cap) { var t2 = m.cap / CAPITALE[pol.famille]; if (t2 > 0.75 * taille && t2 < 1.35 * taille) taille = t2; }
      var col = px ? echantillonPx(px, box) : echantillonCanvas(b, d);
      var bx = box.x < b.bx - 1 ? box.x : b.bx;
      var a = { id: api.nid('n'), t: 'remplace', item: ii, orig: str, texte: str,
        x: box.x, y: box.y, w: box.w, h: box.h, bx: bx, by: b.by, taille: taille,
        // Largeur d'encre + approche des deux lettres extrêmes ≈ largeur d'avance.
        largeur: m ? box.w + 0.06 * taille : b.largeur,
        police: pol, couleur: col.texte, fond: col.fond };
      // Même texte, même largeur : l'écart de police se rattrape par l'espacement.
      a.esp = espacement(a.largeur, mesureCss(str, a), str.length, a.taille);
      return a;
    }
    async function ouvrir(p, d, z, bl, tc, bornes) {
      var s = S(), ii = bl.premier;
      s.html.querySelectorAll('.tpdf-tx-edit').forEach(function (e) { e.remove(); });
      var a = trouverRemplace(p, ii), neuf = !a;
      if (neuf) a = await preparer(p, d, bl, tc, bornes);
      editer(a, p, z, neuf);
    }
    // Blocs de texte modifiables d'une page (null si la page ne s'y prête pas).
    async function blocsPage(p) {
      var s = S(), d = api.dims(p);
      if (d.R !== 0 || p.crop) return null;
      var tc = await contenu(s.sources[p.src], p.idx), blocs = grouperItems(tc.items);
      return { d: d, tc: tc, blocs: blocs, bornes: bornesVoisins(blocs) };
    }
    function echapperRe(t) { return String(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
    // Rechercher et remplacer dans tout le document : une correction par bloc
    // touché (ou mise à jour de la correction existante). Rend {n, blocs, ignorees}.
    async function remplacerPartout(q, rep, opts) {
      opts = opts || {};
      var s = S(), avant = api.snapshot(), n = 0, nb = 0, ignorees = 0;
      var motif = echapperRe(q);
      if (opts.mot) motif = '(?<![\\p{L}\\p{N}])' + motif + '(?![\\p{L}\\p{N}])';
      var re = new RegExp(motif, 'gu' + (opts.casse ? '' : 'i'));
      for (var i = 0; i < s.pages.length; i++) {
        var p = s.pages[i];
        var info = await blocsPage(p);
        if (!info) { ignorees++; continue; }
        for (var k = 0; k < info.blocs.length; k++) {
          var bl = info.blocs[k], deja = trouverRemplace(p, bl.premier), base = deja ? deja.texte : bl.str;
          var trouves = base.match(re); if (!trouves) continue;
          n += trouves.length; nb++;
          var nouveau = base.replace(re, function () { return rep; });
          if (deja) { deja.texte = nouveau; continue; }
          var a = await preparer(p, info.d, bl, info.tc, info.bornes);
          a.texte = nouveau; p.annots.push(a);
        }
      }
      if (nb) { api.pushHist(avant); api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre(); }
      return { n: n, blocs: nb, ignorees: ignorees };
    }
    EXT.texte = { blocsPage: blocsPage, preparer: preparer, trouverRemplace: trouverRemplace,
      remplacerPartout: remplacerPartout, mesure: mesureCss, AVERTISSEMENT: AVERTISSEMENT };
    function editer(a, p, z, neuf) {
      var s = S();
      var inp = document.createElement('input');
      inp.type = 'text'; inp.className = 'tpdf-tx-edit'; inp.value = a.texte;
      inp.style.left = (a.x * z) + 'px'; inp.style.top = (a.y * z) + 'px';
      inp.style.minWidth = (a.w * z + 2) + 'px'; inp.style.height = (a.h * z) + 'px';
      inp.style.width = Math.max(a.w * z + 2, (mesureCss(a.texte, a) + (a.esp || 0) * a.texte.length) * z + 12) + 'px';
      inp.style.letterSpacing = ((a.esp || 0) * z) + 'px';
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
        api.sv('rect', { x: a.x - 1, y: a.y - 1, width: a.w + 2, height: a.h + 2, fill: a.fond }, g);
        var t = api.sv('text', { x: a.bx, y: a.by, 'font-size': a.taille, 'letter-spacing': a.esp || 0, 'font-family': cssPolice(a.police),
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
        // Toute la boîte d'origine + 1 pt, quelle que soit la longueur du nouveau texte.
        var p1 = c.P(a.x - 1, a.y - 1), p2 = c.P(a.x + a.w + 1, a.y + a.h + 1);
        c.pg.drawRectangle({ x: Math.min(p1[0], p2[0]), y: Math.min(p1[1], p2[1]), width: Math.abs(p2[0] - p1[0]), height: Math.abs(p2[1] - p1[1]), color: L.rgb(f[0], f[1], f[2]) });
        if (!a.texte) return;
        var font = await c.pol.police(a.texte + a.orig, a.police), b = c.P(a.bx, a.by);
        var orig = api.nettoyerTexte(font, a.orig || '');
        var cs = a.largeur ? espacement(a.largeur, font.widthOfTextAtSize(orig, a.taille), orig.length, a.taille) : 0;
        if (cs) c.pg.pushOperators(L.pushGraphicsState(), L.setCharacterSpacing(cs));
        c.pg.drawText(api.nettoyerTexte(font, a.texte), { x: b[0], y: b[1], size: a.taille, font: font, color: L.rgb(t[0], t[1], t[2]) });
        if (cs) c.pg.pushOperators(L.popGraphicsState());
      }
    };
  });
})();
