/* MyTools › Utilitaires › Scanner — photo d'un document → PDF propre.
 *
 * Pour chaque photo (appareil du téléphone, webcam, ou fichier) :
 *   1. bords du document détectés (seuil d'Otsu sur l'image réduite, plus
 *      grande zone claire ou sombre la plus « rectangulaire », coins extrêmes) ;
 *      les quatre coins restent déplaçables à la main ;
 *   2. perspective redressée (homographie, échantillonnage bilinéaire) ;
 *   3. rendu « document » (fond blanchi par estimation de l'éclairage, texte
 *      noirci), niveaux de gris ou couleur d'origine ;
 * puis toutes les pages → un PDF (pdf-lib), en A4 ou à la taille de l'image.
 * OCR facultatif (tesseract.js, français + anglais) : texte invisible posé
 * sous l'image, le PDF devient cherchable ; le texte reconnu se copie aussi.
 *
 * Les photos ne quittent pas le poste. Seuls les fichiers du moteur OCR et
 * ses dictionnaires sont téléchargés depuis leur CDN au premier usage.
 * La caméra (getUserMedia) est une étape de geste : hors adresse.
 *
 * Adresse : rendu (document par défaut, gris, couleur), mise (a4 par défaut, image).
 */
(function () {
  'use strict';
  if (window.MyToolsUtil_scanner) return;

  const URL_PDFLIB = 'https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js';
  const URL_TESSERACT = 'https://cdn.jsdelivr.net/npm/tesseract.js@7.0.0/dist/tesseract.min.js';
  const RENDUS = [['document', 'Document', 'Noir sur blanc'], ['gris', 'Niveaux de gris', 'Gris'], ['couleur', 'Couleur', 'Original']];
  const MISES = [['a4', 'Pages A4', 'A4'], ['image', 'Taille de la photo', 'Image']];
  const MAX_TRAVAIL = 2200, MAX_DETECTION = 360;

  // ── Logique pure (tests/test_tools_utilitaires.js) ────────────────
  function niveauxGris(rgba, w, h) {
    const g = new Uint8Array(w * h);
    for (let i = 0, p = 0; i < g.length; i++, p += 4) g[i] = (rgba[p] * 77 + rgba[p + 1] * 150 + rgba[p + 2] * 29) >> 8;
    return g;
  }
  // Flou boîte séparable, rayon r.
  function flouBoite(src, w, h, r) {
    if (r < 1) return Uint8Array.from(src);
    const tmp = new Float32Array(w * h), out = new Uint8Array(w * h), n = 2 * r + 1;
    for (let y = 0; y < h; y++) {
      let s = 0;
      for (let x = -r; x <= r; x++) s += src[y * w + Math.min(w - 1, Math.max(0, x))];
      for (let x = 0; x < w; x++) {
        tmp[y * w + x] = s / n;
        s += src[y * w + Math.min(w - 1, x + r + 1)] - src[y * w + Math.max(0, x - r)];
      }
    }
    for (let x = 0; x < w; x++) {
      let s = 0;
      for (let y = -r; y <= r; y++) s += tmp[Math.min(h - 1, Math.max(0, y)) * w + x];
      for (let y = 0; y < h; y++) {
        out[y * w + x] = Math.round(s / n);
        s += tmp[Math.min(h - 1, y + r + 1) * w + x] - tmp[Math.max(0, y - r) * w + x];
      }
    }
    return out;
  }
  function otsu(g) {
    const hist = new Float64Array(256);
    for (let i = 0; i < g.length; i++) hist[g[i]]++;
    let somme = 0; for (let t = 0; t < 256; t++) somme += t * hist[t];
    let sB = 0, wB = 0, mieux = 0, seuil = 127;
    for (let t = 0; t < 256; t++) {
      wB += hist[t]; if (!wB) continue;
      const wF = g.length - wB; if (!wF) break;
      sB += t * hist[t];
      const mB = sB / wB, mF = (somme - sB) / wF, v = wB * wF * (mB - mF) * (mB - mF);
      if (v > mieux) { mieux = v; seuil = t; }
    }
    return seuil;
  }
  // Plus grande composante 4-connexe de `mask` (1 = dedans) → { aire, idx (Int32Array), bords }.
  function plusGrandeComposante(mask, w, h) {
    const vu = new Uint8Array(w * h), pile = new Int32Array(w * h);
    let mieux = { aire: 0, idx: null, bords: 0 };
    for (let d = 0; d < w * h; d++) {
      if (!mask[d] || vu[d]) continue;
      let n = 0, haut = 0; const liste = [];
      pile[haut++] = d; vu[d] = 1;
      let bH = 0, bB = 0, bG = 0, bD = 0;
      while (haut) {
        const p = pile[--haut]; liste.push(p); n++;
        const x = p % w, y = (p - x) / w;
        if (y === 0) bH = 1; if (y === h - 1) bB = 1; if (x === 0) bG = 1; if (x === w - 1) bD = 1;
        if (x > 0 && mask[p - 1] && !vu[p - 1]) { vu[p - 1] = 1; pile[haut++] = p - 1; }
        if (x < w - 1 && mask[p + 1] && !vu[p + 1]) { vu[p + 1] = 1; pile[haut++] = p + 1; }
        if (y > 0 && mask[p - w] && !vu[p - w]) { vu[p - w] = 1; pile[haut++] = p - w; }
        if (y < h - 1 && mask[p + w] && !vu[p + w]) { vu[p + w] = 1; pile[haut++] = p + w; }
      }
      if (n > mieux.aire) mieux = { aire: n, idx: Int32Array.from(liste), bords: bH + bB + bG + bD };
    }
    return mieux;
  }
  // Coins extrêmes d'un ensemble de pixels : HG, HD, BD, BG.
  function coinsExtremes(idx, w) {
    let hg = null, hd = null, bd = null, bg = null, vHg = Infinity, vHd = -Infinity, vBd = -Infinity, vBg = Infinity;
    for (let i = 0; i < idx.length; i++) {
      const p = idx[i], x = p % w, y = (p - x) / w;
      if (x + y < vHg) { vHg = x + y; hg = [x, y]; }
      if (x + y > vBd) { vBd = x + y; bd = [x, y]; }
      if (x - y > vHd) { vHd = x - y; hd = [x, y]; }
      if (x - y < vBg) { vBg = x - y; bg = [x, y]; }
    }
    return [hg, hd, bd, bg];
  }
  function aireQuad(q) {
    let a = 0;
    for (let i = 0; i < 4; i++) { const p = q[i], r = q[(i + 1) % 4]; a += p[0] * r[1] - r[0] * p[1]; }
    return Math.abs(a) / 2;
  }
  const marge = (w, h) => [[0.03 * w, 0.03 * h], [0.97 * w, 0.03 * h], [0.97 * w, 0.97 * h], [0.03 * w, 0.97 * h]];
  // Bords d'un document dans une image en niveaux de gris → 4 coins (pixels), ou
  // les marges de l'image si rien de net ne ressort (`trouve: false`).
  function detecterBords(gris, w, h) {
    const f = flouBoite(gris, w, h, 2), t = otsu(f), total = w * h;
    let mieux = null;
    [true, false].forEach(clair => {
      const m = new Uint8Array(total);
      for (let i = 0; i < total; i++) m[i] = clair ? (f[i] > t ? 1 : 0) : (f[i] <= t ? 1 : 0);
      const c = plusGrandeComposante(m, w, h);
      if (!c.idx || c.aire < 0.12 * total || c.aire > 0.97 * total || c.bords >= 3) return;
      const q = coinsExtremes(c.idx, w), aq = aireQuad(q);
      if (aq < 0.1 * total) return;
      const rect = Math.min(c.aire / aq, aq / c.aire), score = rect * Math.sqrt(aq / total);
      if (rect > 0.82 && (!mieux || score > mieux.score)) mieux = { score, q };
    });
    return mieux ? { coins: mieux.q, trouve: true } : { coins: marge(w, h), trouve: false };
  }
  // Homographie 3×3 qui envoie src[i] sur dst[i] (4 points).
  function homographie(src, dst) {
    const A = [], b = [];
    for (let i = 0; i < 4; i++) {
      const [x, y] = src[i], [X, Y] = dst[i];
      A.push([x, y, 1, 0, 0, 0, -x * X, -y * X]); b.push(X);
      A.push([0, 0, 0, x, y, 1, -x * Y, -y * Y]); b.push(Y);
    }
    for (let c = 0; c < 8; c++) {
      let p = c;
      for (let r = c + 1; r < 8; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
      if (Math.abs(A[p][c]) < 1e-12) return null;
      [A[c], A[p]] = [A[p], A[c]]; [b[c], b[p]] = [b[p], b[c]];
      for (let r = 0; r < 8; r++) {
        if (r === c) continue;
        const k = A[r][c] / A[c][c];
        if (!k) continue;
        for (let j = c; j < 8; j++) A[r][j] -= k * A[c][j];
        b[r] -= k * b[c];
      }
    }
    const h = b.map((v, i) => v / A[i][i]);
    return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
  }
  function projeter(H, x, y) {
    const z = H[6] * x + H[7] * y + H[8];
    return [(H[0] * x + H[1] * y + H[2]) / z, (H[3] * x + H[4] * y + H[5]) / z];
  }
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  // Taille de la page redressée : moyenne des côtés opposés, bornée à `max`.
  function tailleSortie(q, max) {
    let w = (dist(q[0], q[1]) + dist(q[3], q[2])) / 2, h = (dist(q[0], q[3]) + dist(q[1], q[2])) / 2;
    const k = max && Math.max(w, h) > max ? max / Math.max(w, h) : 1;
    return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)) };
  }
  // Redresse le quadrilatère `q` de l'image source (RGBA) en ow × oh.
  function redresser(src, sw, sh, q, ow, oh) {
    const H = homographie([[0, 0], [ow - 1, 0], [ow - 1, oh - 1], [0, oh - 1]], q);
    const out = new Uint8ClampedArray(ow * oh * 4);
    if (!H) return out;
    for (let v = 0; v < oh; v++) {
      for (let u = 0; u < ow; u++) {
        const z = H[6] * u + H[7] * v + 1;
        let x = (H[0] * u + H[1] * v + H[2]) / z, y = (H[3] * u + H[4] * v + H[5]) / z;
        x = Math.min(sw - 1.001, Math.max(0, x)); y = Math.min(sh - 1.001, Math.max(0, y));
        const x0 = x | 0, y0 = y | 0, fx = x - x0, fy = y - y0;
        const p00 = (y0 * sw + x0) * 4, p10 = p00 + 4, p01 = p00 + sw * 4, p11 = p01 + 4, o = (v * ow + u) * 4;
        for (let c = 0; c < 3; c++) {
          const a = src[p00 + c] + (src[p10 + c] - src[p00 + c]) * fx, b = src[p01 + c] + (src[p11 + c] - src[p01 + c]) * fx;
          out[o + c] = a + (b - a) * fy;
        }
        out[o + 3] = 255;
      }
    }
    return out;
  }
  function percentiles(g, bas, haut) {
    const hist = new Uint32Array(256);
    for (let i = 0; i < g.length; i++) hist[g[i]]++;
    const n = g.length; let c = 0, lo = 0, hi = 255;
    for (let t = 0; t < 256; t++) { c += hist[t]; if (c >= n * bas) { lo = t; break; } }
    c = 0;
    for (let t = 255; t >= 0; t--) { c += hist[t]; if (c >= n * (1 - haut)) { hi = t; break; } }
    return [lo, Math.max(lo + 1, hi)];
  }
  // Rendus, en place sur des données RGBA.
  function filtrer(rgba, w, h, rendu) {
    const g = niveauxGris(rgba, w, h);
    if (rendu === 'couleur') {
      const [lo, hi] = percentiles(g, 0.01, 0.99), k = 255 / (hi - lo);
      for (let p = 0; p < rgba.length; p += 4) for (let c = 0; c < 3; c++) rgba[p + c] = (rgba[p + c] - lo) * k;
      return rgba;
    }
    if (rendu === 'gris') {
      const [lo, hi] = percentiles(g, 0.01, 0.99), k = 255 / (hi - lo);
      for (let i = 0, p = 0; i < g.length; i++, p += 4) { const v = (g[i] - lo) * k; rgba[p] = rgba[p + 1] = rgba[p + 2] = v; }
      return rgba;
    }
    // Document : éclairage estimé (maximum par blocs de s × s, lissé), divisé.
    const s = Math.max(4, Math.round(Math.max(w, h) / 120)), bw = Math.ceil(w / s), bh = Math.ceil(h / s);
    const bloc = new Uint8Array(bw * bh);
    for (let by = 0; by < bh; by++) for (let bx = 0; bx < bw; bx++) {
      let m = 0;
      for (let y = by * s; y < Math.min(h, by * s + s); y++) for (let x = bx * s; x < Math.min(w, bx * s + s); x++) { const v = g[y * w + x]; if (v > m) m = v; }
      bloc[by * bw + bx] = m;
    }
    const fond = flouBoite(bloc, bw, bh, 2);
    for (let y = 0; y < h; y++) {
      const fy = Math.min(bh - 1.001, Math.max(0, y / s - 0.5)), y0 = fy | 0, ty = fy - y0;
      for (let x = 0; x < w; x++) {
        const fx = Math.min(bw - 1.001, Math.max(0, x / s - 0.5)), x0 = fx | 0, tx = fx - x0;
        const a = fond[y0 * bw + x0] + (fond[y0 * bw + x0 + 1] - fond[y0 * bw + x0]) * tx;
        const b = fond[(y0 + 1) * bw + x0] + (fond[(y0 + 1) * bw + x0 + 1] - fond[(y0 + 1) * bw + x0]) * tx;
        const bg = Math.max(24, a + (b - a) * ty);
        let v = g[y * w + x] / bg * 255;
        v = (v - 70) * 255 / 170;
        const p = (y * w + x) * 4;
        rgba[p] = rgba[p + 1] = rgba[p + 2] = v;
      }
    }
    return rgba;
  }
  // Place une image (iw × ih px) sur la page : A4 portrait ou paysage, ou taille réelle à 200 dpi.
  function miseEnPage(iw, ih, mise) {
    if (mise === 'image') { const k = 72 / 200; return { pw: iw * k, ph: ih * k, x: 0, y: 0, w: iw * k, h: ih * k }; }
    const portrait = ih >= iw, pw = portrait ? 595.28 : 841.89, ph = portrait ? 841.89 : 595.28, m = 14;
    const k = Math.min((pw - 2 * m) / iw, (ph - 2 * m) / ih), w = iw * k, h = ih * k;
    return { pw, ph, x: (pw - w) / 2, y: (ph - h) / 2, w, h };
  }

  // ── Interface ──────────────────────────────────────────────────────
  let U = null;
  const K = { host: null, rendu: 'document', mise: 'a4', pages: [], sel: null, seq: 0, flux: null, texte: '' };
  const $ = s => K.host.querySelector(s);

  function construire() {
    const h = K.host;
    h.appendChild(U.tete('scanner'));
    const c1 = U.el('section', 'tut-carte');
    const act = U.el('div', 'tut-actions');
    const iPhoto = U.el('input'); iPhoto.type = 'file'; iPhoto.accept = 'image/*'; iPhoto.setAttribute('capture', 'environment'); iPhoto.hidden = true;
    const iFich = U.el('input'); iFich.type = 'file'; iFich.accept = 'image/*'; iFich.multiple = true; iFich.hidden = true;
    const bPhoto = U.bouton('tut-btn tut-btn--plein', 'camera', 'Prendre une photo', 'Photo');
    const bCam = U.bouton('tut-btn', 'camera', 'Webcam', 'Caméra');
    bPhoto.addEventListener('click', () => iPhoto.click());
    bCam.addEventListener('click', ouvrirCamera);
    [iPhoto, iFich].forEach(i => i.addEventListener('change', () => { ajouter(Array.from(i.files)); i.value = ''; }));
    act.append(bPhoto, bCam, iPhoto, iFich);
    c1.appendChild(act);
    c1.appendChild(U.depot({ multiple: true, accept: 'image/*', titre: 'Ou déposer des photos ici', aide: 'JPEG, PNG, HEIC si le navigateur le lit — une photo par page', surFichiers: ajouter }));
    const vig = U.el('div', 'tut-scan-pages'); vig.id = 'tut-s-pages';
    c1.appendChild(vig);
    h.appendChild(c1);

    const c2 = U.el('section', 'tut-carte'); c2.id = 'tut-s-edit';
    const l = U.el('div', 'tut-ligne');
    l.appendChild(U.el('span', 'tut-lib', 'Rendu'));
    K.choixRendu = U.pastilles(RENDUS, K.rendu, v => { K.rendu = v; K.pages.forEach(p => { p.resultat = null; }); traiterTout(); U.signaler(); });
    l.appendChild(K.choixRendu);
    c2.appendChild(l);
    const ed = U.el('div', 'tut-scan-edit');
    const gauche = U.el('div', 'tut-scan-src');
    gauche.appendChild(U.el('div', 'tut-titre', 'Photo — ajuster les quatre coins'));
    const cadre = U.el('div', 'tut-scan-cadre'); cadre.id = 'tut-s-cadre';
    gauche.appendChild(cadre);
    const ga = U.el('div', 'tut-actions');
    const bDet = U.bouton('tut-btn', '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/>', 'Détecter les bords', 'Auto');
    const bTout = U.bouton('tut-btn', '<rect x="4" y="4" width="16" height="16" rx="1"/>', 'Photo entière', 'Entière');
    const bRot = U.bouton('tut-btn', 'tourner', 'Pivoter', 'Pivoter');
    bDet.addEventListener('click', () => { const p = page(); if (p) { p.coins = p.auto.slice(); p.resultat = null; rendreEditeur(); traiter(p); } });
    bTout.addEventListener('click', () => { const p = page(); if (p) { p.coins = [[0, 0], [p.w - 1, 0], [p.w - 1, p.h - 1], [0, p.h - 1]]; p.resultat = null; rendreEditeur(); traiter(p); } });
    bRot.addEventListener('click', () => { const p = page(); if (p) { p.rotation = ((p.rotation || 0) + 90) % 360; p.resultat = null; traiter(p); } });
    ga.append(bDet, bTout, bRot);
    gauche.appendChild(ga);
    const droite = U.el('div', 'tut-scan-res');
    droite.appendChild(U.el('div', 'tut-titre', 'Résultat'));
    const cv = U.el('canvas', 'tut-scan-apercu'); cv.id = 'tut-s-res';
    droite.appendChild(cv);
    ed.append(gauche, droite);
    c2.appendChild(ed);
    h.appendChild(c2);

    const c3 = U.el('section', 'tut-carte'); c3.id = 'tut-s-pdf';
    const l3 = U.el('div', 'tut-ligne');
    l3.appendChild(U.el('span', 'tut-lib', 'Pages'));
    K.choixMise = U.pastilles(MISES, K.mise, v => { K.mise = v; U.signaler(); });
    l3.appendChild(K.choixMise);
    const lo = U.el('label', 'tut-case'); lo.setAttribute('data-bulle', 'OCR');
    const io = U.el('input'); io.type = 'checkbox'; io.id = 'tut-s-ocr';
    lo.append(io, document.createTextNode(' Texte cherchable (OCR français + anglais)'));
    l3.appendChild(lo);
    c3.appendChild(l3);
    const a3 = U.el('div', 'tut-actions');
    const bPdf = U.bouton('tut-btn tut-btn--plein', 'telecharger', 'Créer le PDF', 'PDF'); bPdf.id = 'tut-s-go';
    bPdf.addEventListener('click', creerPdf);
    const bTxt = U.bouton('tut-btn', 'copier', 'Copier le texte', 'Copier'); bTxt.id = 'tut-s-txt'; bTxt.hidden = true;
    bTxt.addEventListener('click', async () => { const ok = await U.copierTexte(K.texte); U.toast(ok ? 'Texte copié.' : 'Copie refusée.', ok ? 'success' : 'danger'); });
    a3.append(bPdf, bTxt);
    c3.appendChild(a3);
    c3.appendChild(U.el('div', 'tut-etape', '')).id = 'tut-s-etape';
    c3.appendChild(U.el('p', 'tut-aide', 'Les photos restent sur le poste. L\'OCR télécharge son moteur et ses dictionnaires (environ 15 Mo) au premier usage.'));
    h.appendChild(c3);
    rendrePages();
  }

  const page = () => K.pages.find(p => p.id === K.sel) || null;
  function chargerImage(f) {
    return new Promise((ok, ko) => {
      const url = URL.createObjectURL(f), im = new Image();
      im.onload = () => { URL.revokeObjectURL(url); ok(im); };
      im.onerror = () => { URL.revokeObjectURL(url); ko(new Error(f.name + ' : image illisible par ce navigateur.')); };
      im.src = url;
    });
  }
  async function ajouter(fichiers) {
    for (const f of fichiers) {
      if (!/^image\//.test(f.type) && !/\.(jpe?g|png|webp|heic|heif|bmp|gif)$/i.test(f.name)) { U.toast(f.name + ' n\'est pas une image.', 'danger'); continue; }
      try { ajouterImage(await chargerImage(f), f.name); }
      catch (e) { U.toast(e.message, 'danger'); }
    }
  }
  function ajouterImage(source, nom) {
    const sw = source.naturalWidth || source.videoWidth || source.width, sh = source.naturalHeight || source.videoHeight || source.height;
    const k = Math.min(1, MAX_TRAVAIL / Math.max(sw, sh));
    const c = document.createElement('canvas');
    c.width = Math.round(sw * k); c.height = Math.round(sh * k);
    c.getContext('2d').drawImage(source, 0, 0, c.width, c.height);
    const p = { id: ++K.seq, nom, src: c, w: c.width, h: c.height, rotation: 0, resultat: null };
    const kd = Math.min(1, MAX_DETECTION / Math.max(p.w, p.h)), dw = Math.round(p.w * kd), dh = Math.round(p.h * kd);
    const d = document.createElement('canvas'); d.width = dw; d.height = dh;
    const dx = d.getContext('2d'); dx.drawImage(c, 0, 0, dw, dh);
    const r = detecterBords(niveauxGris(dx.getImageData(0, 0, dw, dh).data, dw, dh), dw, dh);
    p.auto = r.coins.map(q => [q[0] / kd, q[1] / kd]);
    p.coins = p.auto.slice();
    p.trouve = r.trouve;
    K.pages.push(p);
    K.sel = p.id;
    if (!r.trouve) U.toast('Bords non détectés : ajuster les coins à la main.', 'info');
    rendrePages(); rendreEditeur(); traiter(p);
  }

  function traiter(p) {
    const q = p.coins, t = tailleSortie(q, MAX_TRAVAIL);
    const src = p.src.getContext('2d').getImageData(0, 0, p.w, p.h).data;
    const data = filtrer(redresser(src, p.w, p.h, q, t.w, t.h), t.w, t.h, K.rendu);
    let c = document.createElement('canvas');
    c.width = t.w; c.height = t.h;
    c.getContext('2d').putImageData(new ImageData(data, t.w, t.h), 0, 0);
    if (p.rotation) {
      const r = document.createElement('canvas'), droit = p.rotation % 180 === 0;
      r.width = droit ? c.width : c.height; r.height = droit ? c.height : c.width;
      const x = r.getContext('2d');
      x.translate(r.width / 2, r.height / 2); x.rotate(p.rotation * Math.PI / 180); x.drawImage(c, -c.width / 2, -c.height / 2);
      c = r;
    }
    p.resultat = c;
    rendrePages();
    if (p.id === K.sel) apercu();
  }
  function traiterTout() { K.pages.forEach(traiter); }
  function apercu() {
    const p = page(), cv = $('#tut-s-res');
    if (!p || !p.resultat) return;
    cv.width = p.resultat.width; cv.height = p.resultat.height;
    cv.getContext('2d').drawImage(p.resultat, 0, 0);
  }

  function rendrePages() {
    const z = $('#tut-s-pages');
    z.textContent = '';
    $('#tut-s-edit').hidden = !K.pages.length;
    $('#tut-s-pdf').hidden = !K.pages.length;
    K.choixRendu.choisir(K.rendu); K.choixMise.choisir(K.mise);
    K.pages.forEach((p, i) => {
      const v = U.el('div', 'tut-scan-vig' + (p.id === K.sel ? ' actif' : ''));
      const b = U.el('button', 'tut-scan-vig-im'); b.type = 'button'; b.setAttribute('data-bulle', 'Ajuster');
      if (p.resultat) { const im = U.el('canvas'); const k = 120 / Math.max(p.resultat.width, p.resultat.height); im.width = Math.max(1, Math.round(p.resultat.width * k)); im.height = Math.max(1, Math.round(p.resultat.height * k)); im.getContext('2d').drawImage(p.resultat, 0, 0, im.width, im.height); b.appendChild(im); }
      b.addEventListener('click', () => { K.sel = p.id; rendrePages(); rendreEditeur(); apercu(); });
      v.appendChild(b);
      const pied = U.el('div', 'tut-scan-vig-pied');
      pied.appendChild(U.el('span', null, 'Page ' + (i + 1)));
      const haut = U.bouton('tut-x', 'haut', '', 'Avancer'), bas = U.bouton('tut-x', 'bas', '', 'Reculer'), x = U.bouton('tut-x', 'retirer', '', 'Retirer');
      haut.disabled = i === 0; bas.disabled = i === K.pages.length - 1;
      haut.addEventListener('click', () => { K.pages.splice(i - 1, 0, K.pages.splice(i, 1)[0]); rendrePages(); });
      bas.addEventListener('click', () => { K.pages.splice(i + 1, 0, K.pages.splice(i, 1)[0]); rendrePages(); });
      x.addEventListener('click', () => {
        K.pages.splice(i, 1);
        if (K.sel === p.id) K.sel = K.pages.length ? K.pages[Math.min(i, K.pages.length - 1)].id : null;
        rendrePages(); rendreEditeur(); apercu();
      });
      pied.append(haut, bas, x);
      v.appendChild(pied);
      z.appendChild(v);
    });
  }

  // Éditeur des coins : la photo en fond, un polygone SVG et quatre poignées.
  function rendreEditeur() {
    const cadre = $('#tut-s-cadre'), p = page();
    cadre.textContent = '';
    if (!p) return;
    const im = U.el('canvas', 'tut-scan-photo');
    im.width = p.w; im.height = p.h;
    im.getContext('2d').drawImage(p.src, 0, 0);
    cadre.appendChild(im);
    const NS = 'http://www.w3.org/2000/svg';
    const s = document.createElementNS(NS, 'svg');
    s.setAttribute('viewBox', '0 0 ' + p.w + ' ' + p.h); s.setAttribute('class', 'tut-scan-svg');
    s.setAttribute('preserveAspectRatio', 'none');
    const poly = document.createElementNS(NS, 'polygon'); poly.setAttribute('class', 'tut-scan-poly');
    s.appendChild(poly);
    const r = Math.max(p.w, p.h) / 40;
    const poignees = p.coins.map((c, i) => {
      const o = document.createElementNS(NS, 'circle');
      o.setAttribute('r', String(r)); o.setAttribute('class', 'tut-scan-coin');
      o.setAttribute('data-coin', String(i));
      s.appendChild(o);
      return o;
    });
    const dessiner = () => {
      poly.setAttribute('points', p.coins.map(c => c[0] + ',' + c[1]).join(' '));
      poignees.forEach((o, i) => { o.setAttribute('cx', String(p.coins[i][0])); o.setAttribute('cy', String(p.coins[i][1])); });
    };
    dessiner();
    let actif = -1;
    const pos = e => { const b = s.getBoundingClientRect(); return [Math.min(p.w - 1, Math.max(0, (e.clientX - b.left) / b.width * p.w)), Math.min(p.h - 1, Math.max(0, (e.clientY - b.top) / b.height * p.h))]; };
    s.addEventListener('pointerdown', e => {
      const q = pos(e);
      let mieux = -1, d = Infinity;
      p.coins.forEach((c, i) => { const x = dist(c, q); if (x < d) { d = x; mieux = i; } });
      if (d > r * 4) return;
      actif = mieux; s.setPointerCapture(e.pointerId); e.preventDefault();
    });
    s.addEventListener('pointermove', e => { if (actif < 0) return; p.coins[actif] = pos(e); dessiner(); });
    const fin = () => { if (actif < 0) return; actif = -1; p.resultat = null; traiter(p); };
    s.addEventListener('pointerup', fin); s.addEventListener('pointercancel', fin);
    cadre.appendChild(s);
  }

  async function ouvrirCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { U.toast('Caméra indisponible sur ce navigateur.', 'danger'); return; }
    let flux;
    try { flux = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1440 } }, audio: false }); }
    catch (e) { U.toast('Accès à la caméra refusé ou impossible.', 'danger'); return; }
    K.flux = flux;
    const o = U.el('div', 'tut-cam');
    const v = U.el('video', 'tut-cam-video'); v.autoplay = true; v.playsInline = true; v.muted = true; v.srcObject = flux;
    const a = U.el('div', 'tut-actions');
    const bp = U.bouton('tut-btn tut-btn--plein', 'camera', 'Capturer la page', 'Capturer');
    const bf = U.bouton('tut-btn', 'retirer', 'Fermer', 'Fermer');
    bp.addEventListener('click', () => { if (v.videoWidth) { ajouterImage(v, 'webcam-' + (K.pages.length + 1)); U.toast('Page ajoutée.', 'success'); } });
    bf.addEventListener('click', fermerCamera);
    a.append(bp, bf);
    o.append(v, a);
    document.body.appendChild(o);
    K.cam = o;
  }
  function fermerCamera() {
    if (K.flux) { K.flux.getTracks().forEach(t => t.stop()); K.flux = null; }
    if (K.cam) { K.cam.remove(); K.cam = null; }
  }

  const vers = c => new Promise(ok => c.toBlob(b => ok(b), 'image/jpeg', 0.86));
  const texteSur = t => String(t).replace(/[’‘]/g, '\'').replace(/[“”«»]/g, '"').replace(/œ/g, 'oe').replace(/Œ/g, 'OE').replace(/[–—]/g, '-').replace(/[^\x20-\x7e\xa0-\xff]/g, '');
  async function creerPdf() {
    if (!K.pages.length) return;
    const go = $('#tut-s-go'), et = $('#tut-s-etape'), ocr = $('#tut-s-ocr').checked;
    go.disabled = true;
    let worker = null;
    try {
      et.textContent = 'Préparation…';
      await U.chargerScript(URL_PDFLIB);
      const L = window.PDFLib, doc = await L.PDFDocument.create();
      doc.setCreator('MySifa · MyTools'); doc.setProducer('pdf-lib');
      const police = ocr ? await doc.embedFont(L.StandardFonts.Helvetica) : null;
      const textes = [];
      if (ocr) {
        et.textContent = 'Chargement du moteur OCR…';
        await U.chargerScript(URL_TESSERACT);
        worker = await window.Tesseract.createWorker('fra+eng', 1, { logger: x => { if (x && x.status === 'recognizing text' && typeof x.progress === 'number') et.dataset.p = String(Math.round(x.progress * 100)); } });
      }
      for (let i = 0; i < K.pages.length; i++) {
        const p = K.pages[i];
        if (!p.resultat) traiter(p);
        et.textContent = 'Page ' + (i + 1) + ' / ' + K.pages.length + (ocr ? ' — reconnaissance du texte…' : '…');
        const c = p.resultat, img = await doc.embedJpg(await (await vers(c)).arrayBuffer());
        const m = miseEnPage(c.width, c.height, K.mise), pg = doc.addPage([m.pw, m.ph]);
        pg.drawImage(img, { x: m.x, y: m.y, width: m.w, height: m.h });
        if (worker) {
          const r = await worker.recognize(c, {}, { blocks: true, text: true });
          textes.push(r.data.text || '');
          const k = m.w / c.width;
          const mots = [];
          (r.data.blocks || []).forEach(b => (b.paragraphs || []).forEach(pa => (pa.lines || []).forEach(li => (li.words || []).forEach(w => mots.push(w)))));
          mots.forEach(w => {
            const t = texteSur(String(w.text || '').trim()), bb = w.bbox;
            if (!t || !bb || (w.confidence != null && w.confidence < 30)) return;
            const taille = Math.max(2, (bb.y1 - bb.y0) * k * 0.9), larg = police.widthOfTextAtSize(t, taille);
            try {
              pg.pushOperators(L.pushGraphicsState(), L.setTextRenderingMode(L.TextRenderingMode.Invisible),
                L.setCharacterSqueeze(Math.max(20, Math.min(500, larg > 0 ? 100 * (bb.x1 - bb.x0) * k / larg : 100))));
              pg.drawText(t, { x: m.x + bb.x0 * k, y: m.y + m.h - bb.y1 * k + (bb.y1 - bb.y0) * k * 0.2, size: taille, font: police });
              pg.pushOperators(L.popGraphicsState());
            } catch (e) { /* mot hors de l'alphabet de la police : ignoré */ }
          });
        }
      }
      const octets = await doc.save();
      const nom = 'scan-' + new Date().toISOString().slice(0, 16).replace(/[T:]/g, '-') + '.pdf';
      U.telecharger(new Blob([octets], { type: 'application/pdf' }), nom);
      K.texte = textes.map((t, i) => (textes.length > 1 ? '— Page ' + (i + 1) + ' —\n' : '') + t.trim()).join('\n\n');
      $('#tut-s-txt').hidden = !K.texte.trim();
      et.textContent = nom + ' · ' + K.pages.length + ' page' + (K.pages.length > 1 ? 's' : '') + ' · ' + U.taille(octets.length);
      U.toast('PDF prêt.', 'success');
    } catch (e) {
      et.textContent = '';
      U.toast(e && e.message ? e.message : 'PDF impossible.', 'danger');
    } finally {
      if (worker) { try { await worker.terminate(); } catch (e) { /* déjà arrêté */ } }
      go.disabled = false;
    }
  }

  window.MyToolsUtil_scanner = {
    cles: ['rendu', 'mise'],
    mount(host, outils) { U = outils; K.host = host; construire(); },
    masquer: fermerCamera,
    etat: () => {
      const e = {};
      if (K.rendu !== 'document') e.rendu = K.rendu;
      if (K.mise !== 'a4') e.mise = K.mise;
      return e;
    },
    aller(p) {
      p = p || {};
      const r = RENDUS.some(x => x[0] === p.rendu) ? p.rendu : 'document';
      const changeRendu = r !== K.rendu;
      K.rendu = r;
      K.mise = p.mise === 'image' ? 'image' : 'a4';
      if (K.host) { if (changeRendu) traiterTout(); rendrePages(); }
    },
    _interne: { niveauxGris, flouBoite, otsu, plusGrandeComposante, coinsExtremes, aireQuad, detecterBords, homographie, projeter, tailleSortie, redresser, filtrer, miseEnPage },
  };
})();
