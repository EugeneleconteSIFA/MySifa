/* Vectorisation fine, partagée par MyTools › Image (mysifa_tools_image.js)
 * et MyTools › Convertir (mysifa_tools_convertir.js). Tout se fait dans le
 * navigateur ; le traceur (imagetracerjs) est chargé par l'outil appelant.
 *
 * Une image d'étiquette ou un logo pris dans un PDF est petit et anticrénelé.
 * Tracé tel quel, il donne des contours en escalier et des liserés de couleurs
 * intermédiaires. On procède donc ainsi :
 *   1. palette prise sur les seules zones franches (pixels entourés de pixels
 *      identiques) : les bords n'inventent pas de couleurs ;
 *   2. agrandissement lissé jusqu'à ×8 (précision sous le pixel) ;
 *   3. chaque pixel rangé dans une couleur de la palette ; un pixel de bord,
 *      mélange de deux couleurs, va à la dominante ;
 *   4. chaque couleur tracée seule, recadrée sur sa boîte pour tenir en mémoire.
 *
 *   MySifaVecto.classer(img, couleurs, etape)  img = {data, w, h} RGBA
 *        → classes {pal, idx, w, h, f, coins}  (coûteux : à garder en cache)
 *   MySifaVecto.tracer(IT, classes, {lissage, details, fond})
 *        → {td, opts, garder, traces}
 *   MySifaVecto.svg(IT, trace, largeur, hauteur)  → texte SVG
 *   MySifaVecto.dessinerPdf(PDFLib, page, svg, x, y, echelle)
 *        dessine les tracés d'un SVG dans une page pdf-lib, coin haut-gauche en (x, y)
 *   MySifaVecto.boiteUtile(img)  → {x, y, w, h} de ce qui n'est pas blanc, ou null
 *
 * Fichier chargé avec un ?v= figé par les deux outils : toute modification
 * oblige à incrémenter ce numéro dans URL_VECTO des deux fichiers.
 */
(function () {
  'use strict';
  if (window.MySifaVecto) return;

  // Pixels de l'image agrandie sur laquelle on trace (×8 au plus).
  const BUDGET_TRACE = 6e6;

  const VF = {
  // Palette : k-means sur les pixels « francs » (voisins quasi identiques),
  // les bords anticrénelés n'inventent donc pas de couleurs intermédiaires.
  palette(img, k) {
    const { data: o, w, h } = img;
    const pas = Math.max(1, Math.floor(Math.sqrt(w * h / 250000)));
    const ech = [];
    for (let y = 1; y < h - 1; y += pas) for (let x = 1; x < w - 1; x += pas) {
      const i = (y * w + x) * 4;
      if (o[i + 3] < 128) continue;
      let ecart = 0;
      for (const d of [-4, 4, -4 * w, 4 * w]) for (let c = 0; c < 3; c++) ecart = Math.max(ecart, Math.abs(o[i + c] - o[i + d + c]));
      if (ecart <= 20) ech.push(o[i], o[i + 1], o[i + 2]);
    }
    const n = ech.length / 3;
    if (!n) return [];
    const d2 = (j, c) => { const a = ech[j * 3] - c[0], b = ech[j * 3 + 1] - c[1], e = ech[j * 3 + 2] - c[2]; return a * a + b * b + e * e; };
    // Départ déterministe : la couleur moyenne, puis le point le plus éloigné à chaque fois.
    const moy = [0, 0, 0]; for (let j = 0; j < n; j++) for (let c = 0; c < 3; c++) moy[c] += ech[j * 3 + c] / n;
    const cen = [];
    let best = 0, bd = -1;
    for (let j = 0; j < n; j++) { const v = d2(j, moy); if (v > bd) { bd = v; best = j; } }
    cen.push([ech[best * 3], ech[best * 3 + 1], ech[best * 3 + 2]]);
    const dmin = new Float64Array(n).fill(Infinity);
    while (cen.length < k) {
      const c = cen[cen.length - 1]; best = -1; bd = -1;
      for (let j = 0; j < n; j++) { const v = d2(j, c); if (v < dmin[j]) dmin[j] = v; if (dmin[j] > bd) { bd = dmin[j]; best = j; } }
      if (bd < 1600) break;              // plus de couleur vraiment distincte (écart < 40)
      cen.push([ech[best * 3], ech[best * 3 + 1], ech[best * 3 + 2]]);
    }
    const lab = new Uint8Array(n);
    for (let it = 0; it < 10; it++) {
      const acc = cen.map(() => [0, 0, 0, 0]);
      for (let j = 0; j < n; j++) {
        let m = 0, mv = Infinity;
        for (let q = 0; q < cen.length; q++) { const v = d2(j, cen[q]); if (v < mv) { mv = v; m = q; } }
        lab[j] = m; const a = acc[m]; a[0] += ech[j * 3]; a[1] += ech[j * 3 + 1]; a[2] += ech[j * 3 + 2]; a[3]++;
      }
      cen.forEach((c, q) => { const a = acc[q]; if (a[3]) { c[0] = a[0] / a[3]; c[1] = a[1] / a[3]; c[2] = a[2] / a[3]; } });
    }
    return cen.map(c => ({ r: Math.round(c[0]), g: Math.round(c[1]), b: Math.round(c[2]), a: 255 }));
  },
  // Couleur de frange : mélange de deux autres couleurs de la palette qui ne
  // vit qu'en bandes fines (bord rose d'un trait rouge sur blanc, bleu pâle
  // autour d'un filet bleu, gris entre un texte noir et le fond). On la juge
  // sur l'image agrandie déjà classée : une vraie couleur, même mélange
  // possible de deux autres (gris d'une ombre, entre noir et blanc), a une part
  // de pixels « pleins » (entourés de 8 voisins de la même couleur) ; une
  // frange n'en a presque pas. Chaque couleur est jugée contre la palette
  // complète : l'ordre ne compte pas. Renvoie, par couleur, s'il faut la garder.
  sansFranges(idx, w, h, pal) {
    const n = pal.length, MIN_PLEINS = 40, MIN_PART = 0.008;
    const P = pal.map(p => [p.r, p.g, p.b]);
    const melange = q => {
      for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) {
        if (a === q || b === q) continue;
        const d = [P[b][0] - P[a][0], P[b][1] - P[a][1], P[b][2] - P[a][2]], L = d[0] * d[0] + d[1] * d[1] + d[2] * d[2] || 1;
        const x = P[q][0] - P[a][0], y = P[q][1] - P[a][1], z = P[q][2] - P[a][2];
        const t = (x * d[0] + y * d[1] + z * d[2]) / L;
        if (t < 0.08 || t > 0.92) continue;
        const ex = x - t * d[0], ey = y - t * d[1], ez = z - t * d[2];
        if (ex * ex + ey * ey + ez * ez < 20 * 20) return true;
      }
      return false;
    };
    const total = new Uint32Array(n), pleins = new Uint32Array(n);
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const p = y * w + x, q = idx[p];
      if (q === 255) continue;
      total[q]++;
      if (idx[p - 1] === q && idx[p + 1] === q && idx[p - w] === q && idx[p + w] === q
        && idx[p - w - 1] === q && idx[p - w + 1] === q && idx[p + w - 1] === q && idx[p + w + 1] === q) pleins[q]++;
    }
    return pal.map((p, q) => {
      if (n < 3 || !melange(q)) return true;
      const part = total[q] ? pleins[q] / total[q] : 0;
      return pleins[q] >= MIN_PLEINS && part >= MIN_PART;
    });
  },
  // Agrandissement bilinéaire d'un facteur f.
  agrandir(img, f) {
    const { data: o, w, h } = img, W = Math.max(1, Math.round(w * f)), H = Math.max(1, Math.round(h * f));
    const out = new Uint8ClampedArray(W * H * 4);
    for (let Y = 0; Y < H; Y++) {
      const sy = Math.min(h - 1, Math.max(0, (Y + 0.5) / f - 0.5)), y0 = Math.floor(sy), y1 = Math.min(h - 1, y0 + 1), fy = sy - y0;
      for (let X = 0; X < W; X++) {
        const sx = Math.min(w - 1, Math.max(0, (X + 0.5) / f - 0.5)), x0 = Math.floor(sx), x1 = Math.min(w - 1, x0 + 1), fx = sx - x0;
        const a = (y0 * w + x0) * 4, b = (y0 * w + x1) * 4, c = (y1 * w + x0) * 4, d = (y1 * w + x1) * 4, j = (Y * W + X) * 4;
        for (let k = 0; k < 4; k++) out[j + k] = (o[a + k] * (1 - fx) + o[b + k] * fx) * (1 - fy) + (o[c + k] * (1 - fx) + o[d + k] * fx) * fy;
      }
    }
    return { data: out, w: W, h: H };
  },
  // Flou quasi gaussien : deux passes de flou boîte séparable, rayon r.
  flou(img, r) {
    if (r < 1) return img;
    const { w, h } = img; let a = new Float32Array(img.data), b = new Float32Array(a.length);
    const passe = (src, dst, horiz) => {
      const L = horiz ? w : h, N = horiz ? h : w, st = horiz ? 4 : 4 * w, lg = horiz ? 4 * w : 4;
      for (let n = 0; n < N; n++) {
        const base = n * lg;
        for (let c = 0; c < 4; c++) {
          let s = 0;
          for (let t = -r; t <= r; t++) s += src[base + Math.min(L - 1, Math.max(0, t)) * st + c];
          for (let t = 0; t < L; t++) {
            dst[base + t * st + c] = s / (2 * r + 1);
            s += src[base + Math.min(L - 1, t + r + 1) * st + c] - src[base + Math.max(0, t - r) * st + c];
          }
        }
      }
    };
    for (let k = 0; k < 2; k++) { passe(a, b, true); passe(b, a, false); }
    return { data: new Uint8ClampedArray(a), w, h };
  },
  // Indice de couleur de chaque pixel agrandi (255 = transparent). Proche
  // d'une couleur de la palette : il la prend. Sinon c'est un bord anticrénelé,
  // lu comme le mélange de deux couleurs : il va à la dominante. Sans ce
  // second cas, le rose entre rouge et blanc partirait vers le gris.
  classer(img, pal) {
    const { data: o, w, h } = img, idx = new Uint8Array(w * h), n = pal.length, PROCHE = 14 * 14;
    const P = pal.map(p => [p.r, p.g, p.b]), masque = (1 << n) - 1;
    for (let Y = 0, p = 0; Y < h; Y++) {
      for (let X = 0; X < w; X++, p++) {
        const i = p * 4;
        if (o[i + 3] < 128) { idx[p] = 255; continue; }
        const r = o[i], g = o[i + 1], bl = o[i + 2];
        let m = 0, mv = Infinity;
        for (let q = 0; q < n; q++) { if (!(masque >> q & 1)) continue; const x = r - P[q][0], y = g - P[q][1], z = bl - P[q][2], v = x * x + y * y + z * z; if (v < mv) { mv = v; m = q; } }
        if (mv > PROCHE) {
          let pv = Infinity;
          for (let a = 0; a < n; a++) { if (!(masque >> a & 1)) continue;
            for (let b = a + 1; b < n; b++) { if (!(masque >> b & 1)) continue;
              const d0 = P[b][0] - P[a][0], d1 = P[b][1] - P[a][1], d2 = P[b][2] - P[a][2], L = d0 * d0 + d1 * d1 + d2 * d2 || 1;
              const x = r - P[a][0], y = g - P[a][1], z = bl - P[a][2];
              const t = Math.min(1, Math.max(0, (x * d0 + y * d1 + z * d2) / L));
              const ex = x - t * d0, ey = y - t * d1, ez = z - t * d2, v = ex * ex + ey * ey + ez * ez;
              // Le gris est sur la droite noir–blanc : à erreur égale, le mélange
              // des deux couleurs les plus éloignées l'emporte (bord noir/blanc).
              const score = Math.max(v, 18 * 18) - L * 0.002;
              if (score < pv) { pv = score; m = t < 0.5 ? a : b; }
            } }
        }
        idx[p] = m;
      }
    }
    return idx;
  },
  // Tracé : chaque couleur seule, recadrée sur sa boîte, puis recollée.
  tracer(IT, idx, w, h, pal, garder, opts) {
    const layers = [];
    pal.forEach((p, q) => {
      layers[q] = [];
      if (!garder[q]) return;
      let x0 = w, y0 = h, x1 = -1, y1 = -1;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (idx[y * w + x] === q) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      if (x1 < 0) return;
      x0 = Math.max(0, x0 - 2); y0 = Math.max(0, y0 - 2); x1 = Math.min(w - 1, x1 + 2); y1 = Math.min(h - 1, y1 + 2);
      const cw = x1 - x0 + 1, ch = y1 - y0 + 1, d = new Uint8ClampedArray(cw * ch * 4);
      for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
        const j = (y * cw + x) * 4, v = idx[(y + y0) * w + x + x0] === q ? 0 : 255;
        d[j] = d[j + 1] = d[j + 2] = v; d[j + 3] = 255;
      }
      const o = Object.assign({}, opts, { pal: [{ r: 0, g: 0, b: 0, a: 255 }, { r: 255, g: 255, b: 255, a: 255 }],
        colorsampling: 0, colorquantcycles: 1, numberofcolors: 2, blurradius: 0, mincolorratio: 0 });
      const td = IT.imagedataToTracedata({ width: cw, height: ch, data: d }, o);
      layers[q] = td.layers[0].map(path => {
        path.segments.forEach(s => { s.x1 += x0; s.y1 += y0; s.x2 += x0; s.y2 += y0; if (s.type === 'Q') { s.x3 += x0; s.y3 += y0; } });
        path.boundingbox = [path.boundingbox[0] + x0, path.boundingbox[1] + y0, path.boundingbox[2] + x0, path.boundingbox[3] + y0];
        return path;
      });
    });
    return { layers, palette: pal, width: w, height: h };
  },
};

  const pause = () => new Promise(r => setTimeout(r, 20));

  async function classer(img, couleurs, etape) {
    const dire = async t => { if (etape) await etape(t); else await pause(); };
    await dire('Lecture des couleurs…');
    let pal = VF.palette(img, Math.max(2, Math.min(32, couleurs)));
    if (!pal.length) throw new Error('Image vide — rien à vectoriser.');
    const f = Math.max(1, Math.min(8, Math.sqrt(BUDGET_TRACE / (img.w * img.h))));
    await dire('Agrandissement lissé ×' + Math.round(f * 10) / 10 + '…');
    let big = f > 1.001 ? VF.agrandir(img, f) : img;
    big = VF.flou(big, Math.round(f * 0.35));
    await dire('Répartition en ' + pal.length + ' couleurs…');
    let idx = VF.classer(big, pal);
    // Couleurs de franges écartées, puis nouvelle répartition sans elles.
    const garder = VF.sansFranges(idx, big.w, big.h, pal);
    if (garder.some(g => !g)) {
      pal = pal.filter((p, q) => garder[q]);
      await dire('Répartition en ' + pal.length + ' couleurs…');
      idx = VF.classer(big, pal);
    }
    // Couleurs des quatre coins : sert à retirer le fond.
    const coins = [0, img.w - 1, (img.h - 1) * img.w, img.w * img.h - 1].map(p => { const i = p * 4; return [img.data[i], img.data[i + 1], img.data[i + 2], img.data[i + 3]]; });
    return { pal, idx, w: big.w, h: big.h, f, coins };
  }

  function tracer(IT, k, v) {
    const proche = (p, c) => Math.abs(p.r - c[0]) + Math.abs(p.g - c[1]) + Math.abs(p.b - c[2]) < 60;
    // Fond retiré : la couleur qui occupe les quatre coins de l'image.
    const garder = k.pal.map(p => !(v.fond && k.coins.every(c => c[3] < 128 || proche(p, c))));
    const opts = {
      ltres: v.lissage, qtres: v.lissage,
      // Seuil de détails exprimé à l'échelle de l'image, ramené à l'image agrandie.
      pathomit: Math.round(v.details * k.f / 2), rightangleenhance: false,
      strokewidth: 0, linefilter: v.details > 0,
      roundcoords: 2, viewbox: true, desc: false, scale: 1 / k.f,
    };
    const td = VF.tracer(IT, k.idx, k.w, k.h, k.pal, garder, opts);
    const traces = td.layers.reduce((n, c) => n + c.filter(p => !p.isholepath).length, 0);
    return { td, opts, garder, traces };
  }

  function svg(IT, t, largeur, hauteur) {
    // Dimensions réelles de l'image d'origine, viewBox à la taille tracée.
    return IT.getsvgstring(t.td, t.opts).replace(/<svg /, '<svg width="' + largeur + '" height="' + hauteur + '" ').replace(/ desc="[^"]*"/, '');
  }

  function dessinerPdf(P, page, texte, x, y, echelle) {
    const doc = new DOMParser().parseFromString(texte, 'image/svg+xml');
    doc.querySelectorAll('path').forEach(p => {
      const m = /rgb\((\d+),(\d+),(\d+)\)/.exec(p.getAttribute('fill') || '');
      if (!m) return;
      const op = parseFloat(p.getAttribute('opacity') || p.getAttribute('fill-opacity') || '1');
      page.drawSvgPath(p.getAttribute('d'), {
        x, y, scale: echelle,
        color: P.rgb(+m[1] / 255, +m[2] / 255, +m[3] / 255),
        opacity: isFinite(op) ? op : 1, borderWidth: 0,
      });
    });
  }

  // Boîte de ce qui n'est ni transparent ni presque blanc, avec une marge.
  function boiteUtile(img) {
    const { data: o, w, h } = img;
    let x0 = w, y0 = h, x1 = -1, y1 = -1;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      if (o[i + 3] < 16 || (o[i] > 245 && o[i + 1] > 245 && o[i + 2] > 245)) continue;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    if (x1 < 0) return null;
    const m = 8;
    x0 = Math.max(0, x0 - m); y0 = Math.max(0, y0 - m); x1 = Math.min(w - 1, x1 + m); y1 = Math.min(h - 1, y1 + m);
    return { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
  }

  window.MySifaVecto = { classer, tracer, svg, dessinerPdf, boiteUtile, VF, BUDGET_TRACE };
})();
