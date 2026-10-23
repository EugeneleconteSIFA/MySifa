/* MyTools › Calculs bobine — schémas récapitulatifs, à l'échelle.
 *
 * Un schéma par calcul, dessiné à droite du formulaire et redessiné à chaque
 * saisie (static/mysifa_tools_calculs.js) :
 *
 *   metrage     coupe de la bobine : mandrin, épaisseur enroulée, Ø, tours
 *   fronts      la laize vue de dessus : fronts, espaces, chute de chaque côté, rive
 *   etiquettes  la bande déroulée depuis la bobine : étiquettes, pas, par mètre
 *   carton      le carton vu de dessus avec les bobines, vide coloré ;
 *               vue de côté quand il y a plusieurs couches
 *
 * Tant que les valeurs manquent, le schéma montre l'exemple des placeholders,
 * estompé et marqué « Exemple ».
 *
 * Couleurs : classes `tsch-*` de static/mysifa_tools_calculs.css, uniquement
 * des variables du thème (clair et sombre), texte blanc sur fond coloré.
 *
 *   MyToolsCalculsSchemas.metrage(v) | fronts(v) | etiquettes(v) | carton(v)
 *     → { svg, legende, exemple }
 *   MyToolsCalculsSchemas._geo : géométrie pure (tests/test_tools_calculs.js)
 */
(function () {
  'use strict';
  if (window.MyToolsCalculsSchemas) return;

  const n = v => { const x = parseFloat(String(v == null ? '' : v).replace(',', '.')); return isFinite(x) ? x : NaN; };
  const fmt = (x, dec) => Number(x).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: dec == null ? 1 : dec });
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const r1 = x => Math.round(x * 10) / 10;

  // ── Géométrie pure ─────────────────────────────────────────────────
  // Bobine en coupe : rayons en px pour un rayon extérieur `R` imposé.
  function geoBobine(dMandrin, dBobine, microns, R) {
    const d = n(dMandrin), D = n(dBobine), e = n(microns);
    if (!(d > 0) || !(D > d)) return null;
    const k = R / (D / 2);
    const enroule = (D - d) / 2;
    return { k, R, r: Math.max(d / 2 * k, 3), enroule, tours: e > 0 ? enroule * 1000 / e : null };
  }

  // Laize vue de dessus : fronts centrés, la moitié de l'espace de chaque côté
  // d'une étiquette (le module = étiquette + espace, comme le calcul), le
  // reste en chute répartie sur les deux bords. Positions en mm depuis le bord.
  function geoFronts(laize, largeur, espace, rive, nb) {
    const W = n(laize), l = n(largeur), g = Math.max(0, n(espace) || 0), r = Math.max(0, n(rive) || 0), N = Math.floor(n(nb));
    if (!(W > 0) || !(l > 0) || !(N >= 1)) return null;
    const module = l + g, utilisee = N * module, chute = W - utilisee;
    const x0 = chute / 2;
    const etiquettes = [];
    for (let i = 0; i < N; i++) etiquettes.push({ x: x0 + i * module + g / 2, w: l });
    return { W, l, g, r, N, module, utilisee, chute, chuteCote: chute / 2, etiquettes };
  }

  // Bande déroulée : pas, étiquettes par mètre (par front et en tout).
  function geoBande(hauteur, espace, nbFronts) {
    const h = n(hauteur), g = Math.max(0, n(espace) || 0), f = Math.max(1, Math.floor(n(nbFronts)) || 1);
    if (!(h > 0)) return null;
    const pas = h + g;
    return { h, g, f, pas, parMetre: 1000 / pas, parMetreTotal: 1000 / pas * f };
  }

  // Bobines dans le carton, en mm, depuis le coin intérieur (jeu/2 de marge).
  // `rang` vient de MyToolsCalculs._interne.rangement : a × b × c, `axe` =
  // 'v' (debout), 'l' (couchées, axe le long de la longueur), 'w' (le long de la largeur).
  function geoCarton(carton, D, L, jeu, rang) {
    if (!carton || !rang || !(D > 0) || !(L > 0)) return null;
    const j = Math.max(0, n(jeu) || 0), m = j / 2;
    const pasA = rang.axe === 'l' ? L : D;          // le long de la longueur
    const pasB = rang.axe === 'w' ? L : D;          // le long de la largeur
    const pasC = rang.axe === 'v' ? L : D;          // en hauteur
    const dessus = [];
    for (let i = 0; i < rang.a; i++) for (let k = 0; k < rang.b; k++) {
      dessus.push({ x: m + i * pasA, y: m + k * pasB, w: pasA, h: pasB, rond: rang.axe === 'v' });
    }
    // Vue de côté (longueur × hauteur) : une colonne par rang a, une ligne par couche.
    const cote = [];
    for (let i = 0; i < rang.a; i++) for (let c = 0; c < rang.c; c++) {
      cote.push({ x: m + i * pasA, y: carton.h - m - (c + 1) * pasC, w: pasA, h: pasC, rond: rang.axe === 'w' });
    }
    const occupeDessus = rang.a * pasA * rang.b * pasB;
    return {
      l: carton.l, w: carton.w, h: carton.h, j, dessus, cote,
      videL: carton.l - j - rang.a * pasA, videW: carton.w - j - rang.b * pasB, videH: carton.h - j - rang.c * pasC,
      occupeDessusPct: occupeDessus / (carton.l * carton.w) * 100,
    };
  }

  // ── Briques SVG ────────────────────────────────────────────────────
  const T = (x, y, txt, cls, anc) => '<text x="' + r1(x) + '" y="' + r1(y) + '" class="' + (cls || 'tsch-t') + '"' + (anc ? ' text-anchor="' + anc + '"' : ' text-anchor="middle"') + '>' + esc(txt) + '</text>';
  // Cote horizontale : trait, deux talons, texte au-dessus (ou dessous).
  function coteH(x1, x2, y, txt, dessous) {
    if (Math.abs(x2 - x1) < 1) return '';
    return '<g class="tsch-cote"><line x1="' + r1(x1) + '" y1="' + r1(y) + '" x2="' + r1(x2) + '" y2="' + r1(y) + '"/>'
      + '<line x1="' + r1(x1) + '" y1="' + r1(y - 4) + '" x2="' + r1(x1) + '" y2="' + r1(y + 4) + '"/>'
      + '<line x1="' + r1(x2) + '" y1="' + r1(y - 4) + '" x2="' + r1(x2) + '" y2="' + r1(y + 4) + '"/></g>'
      + T((x1 + x2) / 2, dessous ? y + 14 : y - 6, txt, 'tsch-t tsch-t--cote');
  }
  function coteV(x, y1, y2, txt, gauche) {
    if (Math.abs(y2 - y1) < 1) return '';
    const tx = gauche ? x - 7 : x + 7;
    return '<g class="tsch-cote"><line x1="' + r1(x) + '" y1="' + r1(y1) + '" x2="' + r1(x) + '" y2="' + r1(y2) + '"/>'
      + '<line x1="' + r1(x - 4) + '" y1="' + r1(y1) + '" x2="' + r1(x + 4) + '" y2="' + r1(y1) + '"/>'
      + '<line x1="' + r1(x - 4) + '" y1="' + r1(y2) + '" x2="' + r1(x + 4) + '" y2="' + r1(y2) + '"/></g>'
      + '<text x="' + r1(tx) + '" y="' + r1((y1 + y2) / 2 + 4) + '" class="tsch-t tsch-t--cote" text-anchor="' + (gauche ? 'end' : 'start') + '">' + esc(txt) + '</text>';
  }
  const enveloppe = (w, h, corps, titre) => '<svg class="tsch-svg" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="' + esc(titre) + '" preserveAspectRatio="xMidYMid meet">' + corps + '</svg>';
  const pastille = (cls, txt) => '<span class="tsch-leg"><i class="' + cls + '"></i>' + esc(txt) + '</span>';

  // ── Métrage ↔ diamètre : coupe de la bobine ────────────────────────
  function metrage(v) {
    let ex = false, d = n(v.dm), D = n(v.db), e = n(v.ep), L = n(v.metres);
    if (!(d > 0) || !(D > d)) { ex = true; d = 76; D = 1000; e = e > 0 ? e : 145; L = Math.PI * ((D / 2) ** 2 - (d / 2) ** 2) / e; }
    const W = 400, H = 340, cx = 200, cy = 158;
    const g = geoBobine(d, D, e, 120);
    let s = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r1(g.R) + '" class="tsch-matiere"/>';
    // Spires suggérées (dix cercles fins, régulièrement espacés dans l'enroulé).
    for (let i = 1; i < 10; i++) s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r1(g.r + (g.R - g.r) * i / 10) + '" class="tsch-spire"/>';
    const ep = Math.max(2, Math.min(g.r * 0.28, 9));
    s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r1(g.r) + '" class="tsch-mandrin"/>';
    s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r1(Math.max(1, g.r - ep)) + '" class="tsch-trou"/>';
    // Cotes : Ø bobine dessous, enroulé sur le rayon droit, Ø mandrin au centre.
    s += coteH(cx - g.R, cx + g.R, cy + g.R + 22, 'Ø ' + fmt(D, 0) + ' mm', true);
    s += '<line x1="' + r1(cx + g.r) + '" y1="' + cy + '" x2="' + r1(cx + g.R) + '" y2="' + cy + '" class="tsch-rayon"/>';
    s += T(cx + (g.r + g.R) / 2, cy - 8, fmt(g.enroule, 0) + ' mm', 'tsch-t tsch-t--sur');
    s += T(cx + (g.r + g.R) / 2, cy + 18, 'enroulé', 'tsch-t tsch-t--sur tsch-t--petit');
    s += T(cx - g.R + 6, 22, 'Mandrin Ø ' + fmt(d, 0) + ' mm', 'tsch-t tsch-t--petit', 'start');
    const legende = [pastille('tsch-p-matiere', 'Matière enroulée'), pastille('tsch-p-mandrin', 'Mandrin Ø ' + fmt(d, 0))].join('')
      + '<div class="tsch-chiffres">'
      + (L > 0 ? '<span><b>≈ ' + fmt(L, 0) + ' m</b> enroulés</span>' : '')
      + (g.tours ? '<span><b>≈ ' + fmt(g.tours, 0) + '</b> tours de ' + fmt(e, 1) + ' µm</span>' : '')
      + '<span>épaisseur enroulée <b>' + fmt(g.enroule, 0) + ' mm</b></span></div>';
    return { svg: enveloppe(W, H, s, 'Coupe de la bobine'), legende, exemple: ex };
  }

  // ── Fronts sur la laize : vue de dessus ────────────────────────────
  function fronts(v) {
    let ex = false, W0 = n(v.laize), l0 = n(v.larg), g0 = n(v.espl) || 0, rv = n(v.rive) || 0, N = v.nb;
    if (!(W0 > 0) || !(l0 > 0) || !(N >= 1)) { ex = true; W0 = 440; l0 = 104.5; g0 = 3.25; rv = 0; N = 4; }
    const g = geoFronts(W0, l0, g0, rv, N);
    const Wv = 400, x0 = 24, larg = 352, k = larg / g.W, yb = 58, hb = 150;
    const hEt = n(v.haut) > 0 ? n(v.haut) * k : l0 * k * 0.72;
    const vEsp = Math.max(2, (n(v.espa) || 0) * k);
    const pasV = Math.max(6, hEt) + vEsp;
    let s = '<defs><clipPath id="tsch-clip-laize"><rect x="' + x0 + '" y="' + yb + '" width="' + larg + '" height="' + hb + '"/></clipPath></defs>';
    s += '<rect x="' + x0 + '" y="' + yb + '" width="' + larg + '" height="' + hb + '" class="tsch-support"/>';
    s += '<g clip-path="url(#tsch-clip-laize)">';
    s += '<rect x="' + x0 + '" y="' + yb + '" width="' + r1(g.chuteCote * k) + '" height="' + hb + '" class="tsch-chute"/>';
    s += '<rect x="' + r1(x0 + (g.W - g.chuteCote) * k) + '" y="' + yb + '" width="' + r1(g.chuteCote * k) + '" height="' + hb + '" class="tsch-chute"/>';
    for (let y = yb + vEsp / 2 - pasV * 0.35; y < yb + hb; y += pasV) {
      g.etiquettes.forEach((e, i) => {
        s += '<rect x="' + r1(x0 + e.x * k) + '" y="' + r1(y) + '" width="' + r1(Math.max(1, e.w * k)) + '" height="' + r1(Math.max(6, hEt)) + '" rx="2" class="tsch-etiq"/>';
      });
    }
    // Numéros sur la rangée du milieu, quand l'étiquette est assez large.
    const yNum = yb + hb / 2 + 5;
    if (g.l * k >= 16) g.etiquettes.forEach((e, i) => { s += T(x0 + (e.x + e.w / 2) * k, yNum, String(i + 1), 'tsch-t tsch-t--blanc'); });
    s += '</g>';
    if (g.r > 0) {
      s += '<line x1="' + r1(x0 + g.r * k) + '" y1="' + yb + '" x2="' + r1(x0 + g.r * k) + '" y2="' + (yb + hb) + '" class="tsch-rive"/>';
      s += '<line x1="' + r1(x0 + (g.W - g.r) * k) + '" y1="' + yb + '" x2="' + r1(x0 + (g.W - g.r) * k) + '" y2="' + (yb + hb) + '" class="tsch-rive"/>';
    }
    s += coteH(x0, x0 + larg, 26, 'Laize ' + fmt(g.W, 2) + ' mm');
    s += coteH(x0 + g.chuteCote * k, x0 + (g.W - g.chuteCote) * k, 46, 'utilisée ' + fmt(g.utilisee, 2), false);
    const e1 = g.etiquettes[0], yc = yb + hb + 18;
    s += coteH(x0 + e1.x * k, x0 + (e1.x + e1.w) * k, yc, fmt(g.l, 2), true);
    if (g.N > 1 && g.g > 0) {
      const e2 = g.etiquettes[1];
      s += coteH(x0 + (e1.x + e1.w) * k, x0 + e2.x * k, yc + 30, 'espace ' + fmt(g.g, 2), true);
    }
    if (g.chuteCote > 0.05) s += T(x0 + (g.W - g.chuteCote / 2) * k, yc + 46, 'chute ' + fmt(g.chuteCote, 2), 'tsch-t tsch-t--danger', 'end');
    const legende = [pastille('tsch-p-etiq', 'Étiquette'), pastille('tsch-p-chute', 'Chute'), g.r > 0 ? pastille('tsch-p-rive', 'Rive ' + fmt(g.r, 2)) : ''].join('')
      + '<div class="tsch-chiffres"><span><b>' + g.N + ' front' + (g.N > 1 ? 's' : '') + '</b> de ' + fmt(g.l, 2) + ' mm</span>'
      + '<span>chute <b>' + fmt(g.chute, 2) + ' mm</b>' + (g.N ? ', soit ' + fmt(g.chuteCote, 2) + ' par bord' : '') + '</span></div>';
    return { svg: enveloppe(Wv, yc + 58, s, 'Laize vue de dessus'), legende, exemple: ex };
  }

  // ── Étiquettes par bobine : bande déroulée ─────────────────────────
  function etiquettes(v) {
    let ex = false, h = n(v.haut), esp = n(v.espa) || 0, f = Math.max(1, Math.floor(n(v.nbf)) || 1);
    if (!(h > 0)) { ex = true; h = 148.4; esp = 4; f = Math.max(1, Math.floor(n(v.nbf)) || 2); }
    const g = geoBande(h, esp, f);
    const largEt = n(v.larg) > 0 ? n(v.larg) : h * 0.62;
    const espL = n(v.espl) > 0 ? n(v.espl) : 3;
    const fVus = Math.min(g.f, 6);
    const W = 400, cx = 52, cy = 118, Rb = 40, xs = 100, longueur = W - xs - 14;
    let k = longueur / (3.4 * g.pas);
    let hBande = fVus * largEt * k + (fVus + 1) * espL * k;
    if (hBande > 168) { k *= 168 / hBande; hBande = 168; }
    const yt = cy - hBande / 2;
    let s = '<defs><clipPath id="tsch-clip-bande"><rect x="' + xs + '" y="' + r1(yt) + '" width="' + longueur + '" height="' + r1(hBande) + '"/></clipPath></defs>';
    // Bobine et départ de la bande.
    s += '<path d="M' + cx + ' ' + r1(cy - Rb) + ' L' + xs + ' ' + r1(yt) + ' L' + xs + ' ' + r1(yt + hBande) + ' L' + cx + ' ' + r1(cy + Rb) + ' Z" class="tsch-support"/>';
    s += '<circle cx="' + cx + '" cy="' + cy + '" r="' + Rb + '" class="tsch-matiere"/>';
    s += '<circle cx="' + cx + '" cy="' + cy + '" r="12" class="tsch-mandrin"/><circle cx="' + cx + '" cy="' + cy + '" r="8" class="tsch-trou"/>';
    s += '<rect x="' + xs + '" y="' + r1(yt) + '" width="' + longueur + '" height="' + r1(hBande) + '" class="tsch-support"/>';
    s += '<g clip-path="url(#tsch-clip-bande)">';
    for (let i = 0; i * g.pas * k < longueur; i++) {
      for (let j = 0; j < fVus; j++) {
        const x = xs + (g.g / 2 + i * g.pas) * k, y = yt + (espL + j * (largEt + espL)) * k;
        s += '<rect x="' + r1(x) + '" y="' + r1(y) + '" width="' + r1(g.h * k) + '" height="' + r1(Math.max(4, largEt * k)) + '" rx="2" class="tsch-etiq"/>';
        if (j === 0 && g.h * k > 26 && largEt * k > 14) s += T(x + g.h * k / 2, y + Math.max(4, largEt * k) / 2 + 4, String(i + 1), 'tsch-t tsch-t--blanc');
      }
    }
    s += '</g>';
    s += '<path d="M' + (W - 30) + ' ' + r1(yt - 12) + ' h18 m-5 -4 l5 4 l-5 4" class="tsch-fleche"/>';
    s += T(W - 34, yt - 8, 'déroulement', 'tsch-t tsch-t--petit', 'end');
    const x1 = xs + (g.g / 2) * k;
    s += coteH(x1, x1 + g.pas * k, r1(yt) - 30, 'pas ' + fmt(g.pas, 2) + ' mm');
    s += coteH(x1, x1 + g.h * k, r1(yt + hBande) + 18, 'hauteur ' + fmt(g.h, 2), true);
    if (g.g > 0) s += T(x1 + (g.h + g.g / 2) * k, r1(yt + hBande) + 50, 'espace ' + fmt(g.g, 2), 'tsch-t tsch-t--cote');
    if (g.f > fVus) s += T(xs + longueur / 2, r1(yt + hBande) + 66, g.f + ' fronts — ' + fVus + ' dessinés', 'tsch-t tsch-t--petit');
    const legende = [pastille('tsch-p-etiq', 'Étiquette'), pastille('tsch-p-matiere', 'Bobine')].join('')
      + '<div class="tsch-chiffres"><span><b>' + fmt(g.parMetre, 2) + '</b> étiquettes par mètre' + (g.f > 1 ? ' et par front' : '') + '</span>'
      + (g.f > 1 ? '<span><b>' + fmt(g.parMetreTotal, 1) + '</b> par mètre sur ' + g.f + ' fronts</span>' : '')
      + (v.total ? '<span><b>' + fmt(v.total, 0) + '</b> étiquettes sur ' + fmt(v.metres, 0) + ' m</span>' : '') + '</div>';
    return { svg: enveloppe(W, r1(yt + hBande) + 76, s, 'Bande déroulée'), legende, exemple: ex };
  }

  // ── Carton optimal : vue de dessus, vue de côté ────────────────────
  function carton(v) {
    const m = v.meilleur;
    if (!m) return { svg: '', legende: '<p class="tsch-vide">Le schéma apparaît dès qu\'un carton convient.</p>', exemple: true };
    const c = m.carton, r = m.rang, D = v.D, L = v.L;
    const g = geoCarton(c, D, L, v.jeu, r);
    if (!g) return { svg: '', legende: '', exemple: true };
    const W = 400, x0 = 40, larg = 330;
    const k = Math.min(larg / g.l, 210 / g.w);
    const yd = 44;
    let s = T(x0, 18, 'Vue de dessus', 'tsch-t tsch-t--titre', 'start');
    s += '<rect x="' + x0 + '" y="' + yd + '" width="' + r1(g.l * k) + '" height="' + r1(g.w * k) + '" class="tsch-vide-carton"/>';
    const plan = (items, ox, oy, kk) => items.map(it => it.rond
      ? '<circle cx="' + r1(ox + (it.x + it.w / 2) * kk) + '" cy="' + r1(oy + (it.y + it.h / 2) * kk) + '" r="' + r1(Math.max(1, Math.min(it.w, it.h) / 2 * kk - 0.6)) + '" class="tsch-bobine"/>'
        + (v.dm > 0 && v.dm < D ? '<circle cx="' + r1(ox + (it.x + it.w / 2) * kk) + '" cy="' + r1(oy + (it.y + it.h / 2) * kk) + '" r="' + r1(Math.max(0.8, v.dm / 2 * kk)) + '" class="tsch-trou"/>' : '')
      : '<rect x="' + r1(ox + it.x * kk + 0.6) + '" y="' + r1(oy + it.y * kk + 0.6) + '" width="' + r1(Math.max(1, it.w * kk - 1.2)) + '" height="' + r1(Math.max(1, it.h * kk - 1.2)) + '" rx="2" class="tsch-bobine"/>').join('');
    s += plan(g.dessus, x0, yd, k);
    s += '<rect x="' + x0 + '" y="' + yd + '" width="' + r1(g.l * k) + '" height="' + r1(g.w * k) + '" class="tsch-carton"/>';
    s += coteH(x0, x0 + g.l * k, yd - 8, fmt(g.l, 0) + ' mm');
    s += coteV(x0 - 12, yd, yd + g.w * k, fmt(g.w, 0), true);
    if (r.c > 1) {
      const txt = '× ' + r.c + ' couches', lb = 16 + txt.length * 6;
      s += '<g><rect x="' + r1(x0 + g.l * k - lb - 6) + '" y="' + (yd + 6) + '" width="' + lb + '" height="20" rx="10" class="tsch-badge"/>' + T(x0 + g.l * k - 6 - lb / 2, yd + 20, txt, 'tsch-t tsch-t--blanc tsch-t--petit') + '</g>';
    }
    let y = yd + g.w * k + 30;
    if (r.c > 1 || r.axe !== 'v') {
      const k2 = Math.min(k, 150 / g.h);
      s += T(x0, y + 4, 'Vue de côté', 'tsch-t tsch-t--titre', 'start');
      const yc = y + 22;
      s += '<rect x="' + x0 + '" y="' + yc + '" width="' + r1(g.l * k2) + '" height="' + r1(g.h * k2) + '" class="tsch-vide-carton"/>';
      s += plan(g.cote, x0, yc, k2);
      s += '<rect x="' + x0 + '" y="' + yc + '" width="' + r1(g.l * k2) + '" height="' + r1(g.h * k2) + '" class="tsch-carton"/>';
      s += coteV(x0 - 12, yc, yc + g.h * k2, fmt(g.h, 0), true);
      y = yc + g.h * k2 + 16;
    }
    const sens = r.axe === 'v' ? 'debout' : 'couchées';
    const legende = [pastille('tsch-p-bobine', 'Bobine Ø ' + fmt(D, 0) + ' × ' + fmt(L, 0)), pastille('tsch-p-vide', 'Vide')].join('')
      + '<div class="tsch-chiffres"><span><b>' + r.a + ' × ' + r.b + '</b> par couche, ' + sens + '</span>'
      + '<span><b>' + r.c + '</b> couche' + (r.c > 1 ? 's' : '') + ' · <b>' + m.parCarton + '</b> bobines</span>'
      + '<span>intérieur ' + fmt(g.l, 0) + ' × ' + fmt(g.w, 0) + ' × ' + fmt(g.h, 0) + ' mm, jeu ' + fmt(g.j, 0) + '</span>'
      + '<span>reste ' + fmt(Math.max(0, g.videL), 0) + ' × ' + fmt(Math.max(0, g.videW), 0) + ' × ' + fmt(Math.max(0, g.videH), 0) + ' mm</span></div>';
    return { svg: enveloppe(W, Math.max(120, r1(y)), s, 'Rangement dans le carton ' + c.libelle), legende, exemple: false };
  }

  window.MyToolsCalculsSchemas = {
    metrage, fronts, etiquettes, carton,
    _geo: { geoBobine, geoFronts, geoBande, geoCarton },
  };
})();
