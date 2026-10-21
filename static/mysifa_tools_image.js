/* MyTools › Image — améliorer et vectoriser une image, dans le navigateur.
 *
 * Monté dans MyTools (/tools?outil=image) et dans MyBAT (bouton « Images » de
 * la barre latérale). Rien n'est envoyé au serveur : l'image reste sur le poste.
 *
 *   Améliorer   agrandir (×2 à ×4), débruiter, netteté, niveaux automatiques,
 *               luminosité / contraste / saturation, noir et blanc, fond rendu
 *               transparent, marges rognées ; export PNG / JPG / WebP avec la
 *               résolution d'impression inscrite dans le fichier.
 *   Vectoriser  tracé en aplats (imagetracerjs), couleurs, lissage, détails
 *               ignorés, fond retiré ; export SVG ou PDF vectoriel (pdf-lib).
 *
 * La vectorisation part de l'image améliorée : on nettoie d'abord, on trace
 * ensuite. Un PDF en entrée est rendu page par page (pdf.js) à 300 dpi.
 *
 *   MyToolsImage.mount(root, ctx)   ctx = { toast(msg, type), surChange() }
 *   MyToolsImage.demonter()
 *   MyToolsImage.adresse = { etat() → {mode}, aller({mode}) }
 *
 * Bibliothèques chargées au premier besoin, versions figées :
 *   imagetracerjs 1.2.6, pdf-lib 1.17.1, pdf.js 4.4.168.
 */
(function () {
  'use strict';
  if (window.MyToolsImage) return;

  const URL_TRACER = 'https://cdn.jsdelivr.net/npm/imagetracerjs@1.2.6/imagetracer_v1.2.6.js';
  const URL_PDFLIB = 'https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js';
  const URL_PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs';
  const URL_PDFJS_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';
  const MAX_PIXELS = 40e6;          // au-delà, l'agrandissement est plafonné
  const MAX_TRACE_COTE = 2000;      // la vectorisation travaille au plus sur 2000 px de côté
  const LS = 'mysifa_tools_image_v1';

  let CTX = { toast: () => {}, surChange: null };
  const I = {
    host: null, nom: 'image', original: null, resultat: null, mode: 'ameliorer',
    r: null, v: null, svg: null, traceInfo: null, enCours: false, comparaison: 50,
    pdf: null, pdfPage: 1, minuteur: 0, clavier: null,
  };
  const DEFAUT_R = { echelle: 1, bruit: 0, nettete: 0, auto: false, lum: 0, contraste: 0, satur: 100,
    nb: 'couleur', seuil: 128, transparent: false, tolerance: 12, rogner: false, dpi: 300, format: 'png', qualite: 92 };
  const DEFAUT_V = { couleurs: 4, lissage: 1, details: 8, fond: true };

  // ── Utilitaires ────────────────────────────────────────────────────
  function toast(m, t) { CTX.toast(m, t || 'info'); }
  function signaler() { if (typeof CTX.surChange === 'function') { try { CTX.surChange(); } catch (e) {} } }
  function charger(url) {
    return new Promise((ok, ko) => {
      if (document.querySelector('script[data-src="' + url + '"]')) { ok(); return; }
      const s = document.createElement('script');
      s.src = url; s.setAttribute('data-src', url);
      s.onload = () => ok(); s.onerror = () => ko(new Error('Bibliothèque indisponible — vérifier la connexion.'));
      document.head.appendChild(s);
    });
  }
  async function tracer() { if (!window.ImageTracer) await charger(URL_TRACER); return window.ImageTracer; }
  async function pdflib() { if (!window.PDFLib) await charger(URL_PDFLIB); return window.PDFLib; }
  let _pdfjs = null;
  async function pdfjs() {
    if (_pdfjs) return _pdfjs;
    _pdfjs = await import(URL_PDFJS);
    _pdfjs.GlobalWorkerOptions.workerSrc = URL_PDFJS_WORKER;
    return _pdfjs;
  }
  const pause = () => new Promise(r => setTimeout(r, 20));
  function toile(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; }
  function ctx2d(c) { return c.getContext('2d', { willReadFrequently: true }); }
  const fmtKo = o => o >= 1048576 ? (o / 1048576).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' Mo' : Math.max(1, Math.round(o / 1024)) + ' Ko';
  const clamp = v => v < 0 ? 0 : v > 255 ? 255 : v;
  function lirePrefs() { try { return JSON.parse(localStorage.getItem(LS) || '{}') || {}; } catch (e) { return {}; } }
  function garderPrefs() { try { localStorage.setItem(LS, JSON.stringify({ r: I.r, v: I.v, mode: I.mode })); } catch (e) {} }
  function telecharger(blob, nom) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = nom;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  // ── Filtres (sur ImageData, en place ou en copie) ──────────────────
  function agrandir(src, facteur) {
    let c = src;
    let reste = facteur;
    // Par paliers de ×2 au plus : un saut direct ×4 lisse moins bien.
    while (reste > 1.001) {
      const f = Math.min(2, reste);
      const n = toile(c.width * f, c.height * f);
      const x = ctx2d(n);
      x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
      x.drawImage(c, 0, 0, n.width, n.height);
      c = n; reste /= f;
    }
    return c;
  }

  function median(d, w, h) {
    const src = new Uint8ClampedArray(d.data);
    const o = d.data, v = new Array(9);
    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        const i = (y * w + x) * 4;
        for (let c = 0; c < 3; c++) {
          let k = 0;
          for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) v[k++] = src[i + (dy * w + dx) * 4 + c];
          v.sort((a, b) => a - b);
          o[i + c] = v[4];
        }
      }
    }
  }

  function flou121(src, w, h) {
    // Flou gaussien 3×3 séparable (1-2-1), base de la netteté.
    const tmp = new Float32Array(w * h * 3), out = new Float32Array(w * h * 3);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const xm = x > 0 ? x - 1 : x, xp = x < w - 1 ? x + 1 : x;
      for (let c = 0; c < 3; c++) tmp[(y * w + x) * 3 + c] = (src[(y * w + xm) * 4 + c] + 2 * src[(y * w + x) * 4 + c] + src[(y * w + xp) * 4 + c]) / 4;
    }
    for (let y = 0; y < h; y++) {
      const ym = y > 0 ? y - 1 : y, yp = y < h - 1 ? y + 1 : y;
      for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) out[(y * w + x) * 3 + c] = (tmp[(ym * w + x) * 3 + c] + 2 * tmp[(y * w + x) * 3 + c] + tmp[(yp * w + x) * 3 + c]) / 4;
    }
    return out;
  }

  function nettete(d, w, h, force) {
    const k = force / 100 * 1.5;
    const b = flou121(d.data, w, h), o = d.data;
    for (let i = 0, j = 0; i < o.length; i += 4, j += 3) {
      for (let c = 0; c < 3; c++) o[i + c] = clamp(o[i + c] + k * (o[i + c] - b[j + c]));
    }
  }

  function niveauxAuto(d) {
    const o = d.data, hist = new Uint32Array(256);
    let n = 0;
    for (let i = 0; i < o.length; i += 4) { if (o[i + 3] < 16) continue; hist[(o[i] * 77 + o[i + 1] * 150 + o[i + 2] * 29) >> 8]++; n++; }
    if (!n) return;
    let bas = 0, haut = 255, acc = 0;
    for (; bas < 255; bas++) { acc += hist[bas]; if (acc > n * 0.005) break; }
    acc = 0;
    for (; haut > 0; haut--) { acc += hist[haut]; if (acc > n * 0.005) break; }
    if (haut - bas < 10) return;
    const f = 255 / (haut - bas);
    for (let i = 0; i < o.length; i += 4) for (let c = 0; c < 3; c++) o[i + c] = clamp((o[i + c] - bas) * f);
  }

  function tons(d, lum, contraste, satur) {
    const o = d.data;
    const cf = (259 * (contraste + 255)) / (255 * (259 - contraste));
    const s = satur / 100, l = lum * 2.55;
    for (let i = 0; i < o.length; i += 4) {
      let r = o[i], g = o[i + 1], b = o[i + 2];
      if (s !== 1) { const y = 0.299 * r + 0.587 * g + 0.114 * b; r = y + (r - y) * s; g = y + (g - y) * s; b = y + (b - y) * s; }
      if (contraste) { r = cf * (r - 128) + 128; g = cf * (g - 128) + 128; b = cf * (b - 128) + 128; }
      o[i] = clamp(r + l); o[i + 1] = clamp(g + l); o[i + 2] = clamp(b + l);
    }
  }

  function noirBlanc(d, mode, seuil) {
    const o = d.data;
    for (let i = 0; i < o.length; i += 4) {
      const y = 0.299 * o[i] + 0.587 * o[i + 1] + 0.114 * o[i + 2];
      const v = mode === 'seuil' ? (y >= seuil ? 255 : 0) : y;
      o[i] = o[i + 1] = o[i + 2] = v;
    }
  }

  // Fond → transparent : remplissage depuis les bords, pour ne pas trouer
  // l'intérieur d'un logo qui reprendrait la couleur du fond.
  function fondTransparent(d, w, h, tol) {
    const o = d.data, vu = new Uint8Array(w * h);
    const coins = [0, w - 1, (h - 1) * w, h * w - 1].map(p => [o[p * 4], o[p * 4 + 1], o[p * 4 + 2]]);
    const ref = [0, 1, 2].map(c => coins.reduce((s, k) => s + k[c], 0) / 4);
    const seuil = (tol / 100) * 441;
    const proche = p => { const i = p * 4; const dr = o[i] - ref[0], dg = o[i + 1] - ref[1], db = o[i + 2] - ref[2]; return Math.sqrt(dr * dr + dg * dg + db * db) <= seuil; };
    const pile = [];
    for (let x = 0; x < w; x++) { pile.push(x, (h - 1) * w + x); }
    for (let y = 0; y < h; y++) { pile.push(y * w, y * w + w - 1); }
    while (pile.length) {
      const p = pile.pop();
      if (vu[p]) continue;
      vu[p] = 1;
      if (!proche(p)) continue;
      o[p * 4 + 3] = 0;
      const x = p % w, y = (p - x) / w;
      if (x > 0) pile.push(p - 1); if (x < w - 1) pile.push(p + 1);
      if (y > 0) pile.push(p - w); if (y < h - 1) pile.push(p + w);
    }
  }

  // Rognage : boîte englobante de ce qui n'est ni transparent ni du fond clair.
  function boiteUtile(d, w, h) {
    const o = d.data;
    let x0 = w, y0 = h, x1 = -1, y1 = -1;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const vide = o[i + 3] < 16 || (o[i] > 245 && o[i + 1] > 245 && o[i + 2] > 245);
      if (vide) continue;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    if (x1 < 0) return null;
    const m = Math.round(Math.min(w, h) * 0.01);
    return { x: Math.max(0, x0 - m), y: Math.max(0, y0 - m), w: Math.min(w, x1 + m + 1) - Math.max(0, x0 - m), h: Math.min(h, y1 + m + 1) - Math.max(0, y0 - m) };
  }

  // Libellé de l'étape en cours dans le voile « Traitement », puis une pause
  // pour que le navigateur l'affiche avant le calcul suivant.
  async function etape(texte) {
    const e = I.host && I.host.querySelector('[data-etape]');
    if (e) e.textContent = texte;
    await pause();
  }

  async function traiter() {
    const r = I.r;
    let c = I.original;
    const f = Math.min(r.echelle, Math.sqrt(MAX_PIXELS / (c.width * c.height)));
    if (f > 1.001) { await etape('Agrandissement ×' + Math.round(f * 10) / 10 + '…'); c = agrandir(c, f); }
    else { const n = toile(c.width, c.height); ctx2d(n).drawImage(c, 0, 0); c = n; }
    const x = ctx2d(c), w = c.width, h = c.height;
    const d = x.getImageData(0, 0, w, h);
    await pause();
    for (let k = 0; k < r.bruit; k++) { await etape('Débruitage' + (r.bruit > 1 ? ' ' + (k + 1) + '/' + r.bruit : '') + '…'); median(d, w, h); }
    if (r.auto || r.lum || r.contraste || r.satur !== 100) await etape('Réglage des tons…');
    if (r.auto) niveauxAuto(d);
    if (r.lum || r.contraste || r.satur !== 100) tons(d, r.lum, r.contraste, r.satur);
    if (r.nettete > 0) { await etape('Netteté…'); nettete(d, w, h, r.nettete); }
    if (r.nb !== 'couleur') noirBlanc(d, r.nb, r.seuil);
    if (r.transparent) { await etape('Détourage du fond…'); fondTransparent(d, w, h, r.tolerance); }
    x.putImageData(d, 0, 0);
    if (r.rogner) {
      const b = boiteUtile(d, w, h);
      if (b && (b.w < w || b.h < h)) { const n = toile(b.w, b.h); ctx2d(n).drawImage(c, b.x, b.y, b.w, b.h, 0, 0, b.w, b.h); c = n; }
    }
    return c;
  }

  // ── Résolution d'impression inscrite dans le fichier ───────────────
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
  function pngAvecDpi(buf, dpi) {
    const src = new Uint8Array(buf);
    const ppm = Math.round(dpi / 0.0254);
    const chunk = new Uint8Array(21);
    const dv = new DataView(chunk.buffer);
    dv.setUint32(0, 9); chunk.set([0x70, 0x48, 0x59, 0x73], 4);
    dv.setUint32(8, ppm); dv.setUint32(12, ppm); chunk[16] = 1;
    dv.setUint32(17, crc32(chunk.subarray(4, 17)));
    // Après IHDR (8 octets de signature + 25 octets de bloc IHDR).
    const out = new Uint8Array(src.length + 21);
    out.set(src.subarray(0, 33), 0); out.set(chunk, 33); out.set(src.subarray(33), 54);
    return out;
  }
  function jpgAvecDpi(buf, dpi) {
    const b = new Uint8Array(buf);
    // En-tête JFIF : FFD8 FFE0 len 'JFIF\0' ver(2) unités(1) Xdens(2) Ydens(2)
    if (b[2] === 0xff && b[3] === 0xe0 && b[6] === 0x4a && b[7] === 0x46) {
      b[13] = 1; b[14] = dpi >> 8; b[15] = dpi & 255; b[16] = dpi >> 8; b[17] = dpi & 255;
    }
    return b;
  }

  async function exporterImage() {
    if (!I.resultat) return;
    const r = I.r;
    const mime = { png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp' }[r.format];
    let c = I.resultat;
    if (r.format === 'jpg') {
      // Le JPG n'a pas de transparence : fond blanc plutôt que noir.
      const n = toile(c.width, c.height); const x = ctx2d(n);
      x.fillStyle = 'white'; x.fillRect(0, 0, n.width, n.height); x.drawImage(c, 0, 0); c = n;
    }
    const blob = await new Promise(ok => c.toBlob(ok, mime, r.qualite / 100));
    if (!blob) { toast('Export impossible dans ce navigateur.', 'danger'); return; }
    let octets = await blob.arrayBuffer();
    const dpi = Math.max(1, Math.min(4800, Math.round(r.dpi) || 300));
    if (r.format === 'png') octets = pngAvecDpi(octets, dpi);
    else if (r.format === 'jpg') octets = jpgAvecDpi(octets, dpi);
    telecharger(new Blob([octets], { type: mime }), I.nom + '-ameliore.' + r.format);
  }

  // ── Vectorisation ──────────────────────────────────────────────────
  async function vectoriser() {
    await etape('Chargement du traceur…');
    const IT = await tracer();
    let c = I.resultat;
    const f = Math.min(1, MAX_TRACE_COTE / Math.max(c.width, c.height));
    if (f < 1) { const n = toile(c.width * f, c.height * f); const x = ctx2d(n); x.imageSmoothingQuality = 'high'; x.drawImage(c, 0, 0, n.width, n.height); c = n; }
    const d = ctx2d(c).getImageData(0, 0, c.width, c.height);
    const v = I.v;
    const opts = {
      numberofcolors: Math.max(2, Math.min(32, v.couleurs)),
      ltres: v.lissage, qtres: v.lissage,
      pathomit: v.details, rightangleenhance: true,
      colorsampling: 2, colorquantcycles: 4, mincolorratio: 0,
      blurradius: 0, strokewidth: 0, linefilter: v.details > 0,
      roundcoords: 2, viewbox: true, desc: false, scale: 1,
    };
    await etape('Vectorisation en ' + opts.numberofcolors + ' couleurs…');
    const td = IT.imagedataToTracedata(d, opts);
    // Fond retiré : couches transparentes, et la couleur de fond si demandé
    // (la plus claire, si elle couvre les quatre coins).
    const garder = td.palette.map(p => p.a >= 128);
    if (v.fond) {
      const coin = idx => { const i = idx * 4; return [d.data[i], d.data[i + 1], d.data[i + 2], d.data[i + 3]]; };
      const coins = [0, c.width - 1, (c.height - 1) * c.width, c.width * c.height - 1].map(coin);
      const proche = (p, k) => Math.abs(p.r - k[0]) + Math.abs(p.g - k[1]) + Math.abs(p.b - k[2]) < 60;
      td.palette.forEach((p, i) => { if (coins.every(k => k[3] < 128 || proche(p, k))) garder[i] = false; });
    }
    let nbTraces = 0;
    td.layers = td.layers.map((couche, i) => { if (!garder[i]) return []; nbTraces += couche.length; return couche; });
    let svg = IT.getsvgstring(td, opts);
    // Dimensions réelles de l'image d'origine, viewBox à la taille tracée.
    svg = svg.replace(/<svg /, '<svg width="' + I.resultat.width + '" height="' + I.resultat.height + '" ').replace(/ desc="[^"]*"/, '');
    I.svg = svg;
    I.traceInfo = { couleurs: garder.filter(Boolean).length, traces: nbTraces, octets: new Blob([svg]).size, w: c.width, h: c.height };
  }

  async function exporterPdf() {
    if (!I.svg) return;
    const P = await pdflib();
    const doc = await P.PDFDocument.create();
    const dpi = Math.max(72, Math.round(I.r.dpi) || 300);
    const W = I.resultat.width / dpi * 72, H = I.resultat.height / dpi * 72;
    const page = doc.addPage([W, H]);
    const svg = new DOMParser().parseFromString(I.svg, 'image/svg+xml');
    const vb = (svg.documentElement.getAttribute('viewBox') || '').split(/\s+/).map(Number);
    const ech = vb.length === 4 && vb[2] ? W / vb[2] : 1;
    svg.querySelectorAll('path').forEach(p => {
      const m = /rgb\((\d+),(\d+),(\d+)\)/.exec(p.getAttribute('fill') || '');
      if (!m) return;
      const op = parseFloat(p.getAttribute('opacity') || p.getAttribute('fill-opacity') || '1');
      page.drawSvgPath(p.getAttribute('d'), {
        x: 0, y: H, scale: ech,
        color: P.rgb(+m[1] / 255, +m[2] / 255, +m[3] / 255),
        opacity: isFinite(op) ? op : 1, borderWidth: 0,
      });
    });
    telecharger(new Blob([await doc.save()], { type: 'application/pdf' }), I.nom + '-vectoriel.pdf');
  }

  // ── Chargement d'un fichier ────────────────────────────────────────
  async function ouvrirFichier(f) {
    if (!f) return;
    I.nom = (f.name || 'image').replace(/\.[^.]+$/, '').replace(/[^\w\- ]+/g, '').trim() || 'image';
    try {
      if (f.type === 'application/pdf' || /\.pdf$/i.test(f.name)) {
        const lib = await pdfjs();
        I.pdf = await lib.getDocument({ data: new Uint8Array(await f.arrayBuffer()) }).promise;
        I.pdfPage = 1;
        await rendrePagePdf();
        return;
      }
      if (!/^image\//.test(f.type)) { toast('Fichier non lu — image (PNG, JPG, WebP, GIF, BMP) ou PDF attendu.', 'danger'); return; }
      I.pdf = null;
      const bmp = await createImageBitmap(f);
      const c = toile(bmp.width, bmp.height);
      ctx2d(c).drawImage(bmp, 0, 0);
      I.original = c;
      await recalculer(true);
    } catch (e) {
      toast((e && /password/i.test(e.name || e.message || '')) ? 'PDF protégé par mot de passe — ouvrir une copie sans protection.' : 'Fichier illisible.', 'danger');
    }
  }

  async function rendrePagePdf() {
    const page = await I.pdf.getPage(I.pdfPage);
    const vp = page.getViewport({ scale: 300 / 72 });
    const s = Math.min(1, Math.sqrt(MAX_PIXELS / 4 / (vp.width * vp.height)));
    const v2 = page.getViewport({ scale: 300 / 72 * s });
    const c = toile(v2.width, v2.height);
    const x = ctx2d(c); x.fillStyle = 'white'; x.fillRect(0, 0, c.width, c.height);
    await page.render({ canvasContext: x, viewport: v2 }).promise;
    I.original = c;
    await recalculer(true);
  }

  // ── Interface ──────────────────────────────────────────────────────
  const $ = s => I.host.querySelector(s);

  function curseur(cle, label, min, max, pas, unite, bulle) {
    return '<label class="timg-champ"' + (bulle ? ' data-bulle="' + bulle + '"' : '') + '><span>' + label + ' <b data-val="' + cle + '"></b></span>'
      + '<input type="range" data-r="' + cle + '" min="' + min + '" max="' + max + '" step="' + pas + '" data-unite="' + (unite || '') + '"></label>';
  }
  function choix(cle, label, options) {
    return '<div class="timg-champ"><span>' + label + '</span><div class="timg-seg" data-choix="' + cle + '">'
      + options.map(o => '<button type="button" data-v="' + o[0] + '"' + (o[2] ? ' data-bulle="' + o[2] + '"' : '') + '>' + o[1] + '</button>').join('') + '</div></div>';
  }
  function case_(cle, label, bulle) {
    return '<label class="timg-case"' + (bulle ? ' data-bulle="' + bulle + '"' : '') + '><input type="checkbox" data-r="' + cle + '"> ' + label + '</label>';
  }

  function construire() {
    const h = I.host;
    h.className = 'timg';
    h.innerHTML =
      '<div class="timg-barre">'
      + '<div class="timg-seg timg-modes" data-mode-seg>'
      + '<button type="button" data-mode="ameliorer" data-bulle="Retoucher">Améliorer</button>'
      + '<button type="button" data-mode="vectoriser" data-bulle="Tracer en SVG">Vectoriser</button></div>'
      + '<button type="button" class="timg-btn" data-act="ouvrir" data-bulle="Image ou PDF">Ouvrir une image</button>'
      + '<span class="timg-pdfnav" hidden><button type="button" class="timg-btn" data-act="pdf-prec" aria-label="Page précédente" data-bulle="Page précédente">‹</button>'
      + '<span data-pdfpage></span><button type="button" class="timg-btn" data-act="pdf-suiv" aria-label="Page suivante" data-bulle="Page suivante">›</button></span>'
      + '<span class="timg-info" data-info></span>'
      + '<input type="file" accept="image/*,application/pdf" hidden data-fichier></div>'
      + '<div class="timg-corps">'
      + '<div class="timg-vue" data-vue>'
      + '<div class="timg-depot" data-depot><strong>Déposer une image ou un PDF</strong><span>ou cliquer pour choisir. Le fichier reste sur ce poste.</span></div>'
      + '<div class="timg-compare" data-compare hidden>'
      + '<div class="timg-damier"><canvas data-apres></canvas><div class="timg-avant" data-avant-clip><canvas data-avant></canvas></div>'
      + '<img data-svg alt="Aperçu vectoriel" hidden></div>'
      + '<input type="range" class="timg-glissiere" data-glissiere min="0" max="100" value="50" aria-label="Avant / après" data-bulle="Comparer">'
      + '<div class="timg-legende"><span>Avant</span><span data-legende-apres>Après</span></div></div>'
      + '<div class="timg-occupe" data-occupe hidden role="status" aria-live="polite"><div class="timg-occupe-carte">'
      + '<span class="timg-roue" aria-hidden="true"></span>'
      + '<div><div class="timg-occupe-t" data-etape>Traitement…</div><div class="timg-occupe-s">L\'image reste sur ce poste.</div></div>'
      + '<div class="timg-barre-prog" aria-hidden="true"><span></span></div></div></div>'
      + '</div>'
      + '<aside class="timg-panneau">'
      + '<section data-panneau="ameliorer">'
      + choix('echelle', 'Agrandir', [[1, '×1', 'Taille d\'origine'], [2, '×2', 'Double'], [3, '×3', 'Triple'], [4, '×4', 'Quadruple']])
      + choix('bruit', 'Débruiter', [[0, 'Non', 'Aucun lissage'], [1, 'Léger', 'Grain fin'], [2, 'Fort', 'Grain marqué']])
      + curseur('nettete', 'Netteté', 0, 200, 5, ' %', 'Contours')
      + case_('auto', 'Niveaux automatiques', 'Contraste auto')
      + curseur('lum', 'Luminosité', -100, 100, 1, '', 'Clair / sombre')
      + curseur('contraste', 'Contraste', -100, 100, 1, '', 'Écart des tons')
      + curseur('satur', 'Saturation', 0, 200, 5, ' %', 'Vivacité')
      + choix('nb', 'Couleurs', [['couleur', 'Couleur', 'Inchangé'], ['gris', 'Gris', 'Niveaux de gris'], ['seuil', 'Noir & blanc', 'Deux tons']])
      + '<div data-si="seuil">' + curseur('seuil', 'Seuil', 1, 254, 1, '', 'Limite noir / blanc') + '</div>'
      + case_('transparent', 'Fond transparent', 'Détourage')
      + '<div data-si="transparent">' + curseur('tolerance', 'Tolérance du fond', 1, 60, 1, ' %', 'Écart accepté') + '</div>'
      + case_('rogner', 'Rogner les marges', 'Recadrage')
      + '<div class="timg-sep"></div>'
      + choix('format', 'Format', [['png', 'PNG', 'Transparence'], ['jpg', 'JPG', 'Photo'], ['webp', 'WebP', 'Web']])
      + '<div data-si="qualite">' + curseur('qualite', 'Qualité', 50, 100, 1, ' %', 'Compression') + '</div>'
      + '<label class="timg-champ"><span>Résolution d\'impression (dpi)</span><input type="number" class="timg-in" data-r="dpi" min="72" max="4800" step="1"></label>'
      + '<div class="timg-note" data-taille></div>'
      + '<div class="timg-actions"><button type="button" class="timg-btn" data-act="reinit" data-bulle="Réglages d\'origine">Réinitialiser</button>'
      + '<button type="button" class="timg-btn timg-btn-accent" data-act="exporter" data-bulle="Télécharger">Enregistrer l\'image</button></div>'
      + '</section>'
      + '<section data-panneau="vectoriser" hidden>'
      + '<p class="timg-note">Le tracé part de l\'image améliorée : nettoyer d\'abord (contraste, débruitage, fond) donne des formes plus franches.</p>'
      + choix('couleurs', 'Couleurs', [[2, '2', '2 couleurs'], [3, '3', '3 couleurs'], [4, '4', '4 couleurs'], [6, '6', '6 couleurs'], [8, '8', '8 couleurs'], [16, '16', '16 couleurs']])
      + curseur('lissage', 'Lissage', 0.1, 5, 0.1, '', 'Courbes')
      + curseur('details', 'Ignorer les détails sous', 0, 60, 1, ' px²', 'Poussières')
      + case_('fond', 'Retirer le fond', 'Sans fond')
      + '<div class="timg-note" data-trace></div>'
      + '<div class="timg-actions"><button type="button" class="timg-btn" data-act="copier-svg" data-bulle="Presse-papiers">Copier le SVG</button>'
      + '<button type="button" class="timg-btn" data-act="svg" data-bulle="Vectoriel web">Enregistrer en SVG</button>'
      + '<button type="button" class="timg-btn timg-btn-accent" data-act="pdf" data-bulle="Vectoriel impression">Enregistrer en PDF</button></div>'
      + '</section>'
      + '</aside></div>';

    const fichier = $('[data-fichier]');
    fichier.addEventListener('change', () => { ouvrirFichier(fichier.files[0]); fichier.value = ''; });
    $('[data-depot]').addEventListener('click', () => fichier.click());
    const vue = $('[data-vue]');
    vue.addEventListener('dragover', e => { e.preventDefault(); vue.classList.add('timg-survol'); });
    vue.addEventListener('dragleave', () => vue.classList.remove('timg-survol'));
    vue.addEventListener('drop', e => { e.preventDefault(); vue.classList.remove('timg-survol'); ouvrirFichier(e.dataTransfer.files && e.dataTransfer.files[0]); });
    $('[data-glissiere]').addEventListener('input', e => { I.comparaison = +e.target.value; majComparaison(); });

    h.addEventListener('click', async e => {
      const m = e.target.closest('[data-mode]');
      if (m) { I.mode = m.getAttribute('data-mode'); garderPrefs(); majInterface(); if (I.mode === 'vectoriser' && I.resultat && !I.svg) relancer('v'); signaler(); return; }
      const ch = e.target.closest('[data-choix] [data-v]');
      if (ch) {
        const cle = ch.parentElement.getAttribute('data-choix');
        const brut = ch.getAttribute('data-v');
        const cible = cle in I.r ? I.r : I.v;
        cible[cle] = isNaN(+brut) ? brut : +brut;
        majInterface(); relancer(cible === I.v ? 'v' : 'r');
        return;
      }
      const a = e.target.closest('[data-act]');
      if (!a) return;
      const act = a.getAttribute('data-act');
      if (act === 'ouvrir') fichier.click();
      else if (act === 'reinit') { I.r = Object.assign({}, DEFAUT_R, { dpi: I.r.dpi, format: I.r.format }); majInterface(); relancer('r'); }
      else if (act === 'exporter') exporterImage();
      else if (act === 'svg') { if (I.svg) telecharger(new Blob([I.svg], { type: 'image/svg+xml' }), I.nom + '-vectoriel.svg'); }
      else if (act === 'pdf') { try { await exporterPdf(); } catch (err) { toast(err.message || 'Export PDF impossible.', 'danger'); } }
      else if (act === 'copier-svg') {
        if (!I.svg) return;
        try { await navigator.clipboard.writeText(I.svg); toast('SVG copié.', 'success'); } catch (err) { toast('Copie refusée par le navigateur.', 'info'); }
      } else if (act === 'pdf-prec' && I.pdf && I.pdfPage > 1) { I.pdfPage--; await rendrePagePdf(); }
      else if (act === 'pdf-suiv' && I.pdf && I.pdfPage < I.pdf.numPages) { I.pdfPage++; await rendrePagePdf(); }
    });
    h.addEventListener('input', e => {
      const k = e.target.getAttribute('data-r');
      if (!k) return;
      const cible = k in I.r ? I.r : I.v;
      cible[k] = e.target.type === 'checkbox' ? e.target.checked : +e.target.value;
      majValeurs();
      if (k === 'dpi' || k === 'qualite') { garderPrefs(); majTaille(); return; }
      relancer(cible === I.v ? 'v' : 'r');
    });
    majInterface();
  }

  function majValeurs() {
    I.host.querySelectorAll('[data-r]').forEach(e => {
      const k = e.getAttribute('data-r'); const src = k in I.r ? I.r : I.v;
      if (e.type === 'checkbox') e.checked = !!src[k]; else if (document.activeElement !== e) e.value = src[k];
      const b = I.host.querySelector('[data-val="' + k + '"]');
      if (b) b.textContent = (+src[k]).toLocaleString('fr-FR') + (e.getAttribute('data-unite') || '');
    });
    I.host.querySelectorAll('[data-choix]').forEach(g => {
      const k = g.getAttribute('data-choix'); const src = k in I.r ? I.r : I.v;
      g.querySelectorAll('[data-v]').forEach(b => b.classList.toggle('active', String(b.getAttribute('data-v')) === String(src[k])));
    });
    const si = (sel, v) => { const e = I.host.querySelector('[data-si="' + sel + '"]'); if (e) e.hidden = !v; };
    si('seuil', I.r.nb === 'seuil'); si('transparent', I.r.transparent); si('qualite', I.r.format !== 'png');
  }

  function majInterface() {
    if (!I.host) return;
    I.host.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('active', b.getAttribute('data-mode') === I.mode));
    I.host.querySelectorAll('[data-panneau]').forEach(p => { p.hidden = p.getAttribute('data-panneau') !== I.mode; });
    majValeurs();
    const a = !!I.original;
    $('[data-depot]').hidden = a;
    $('[data-compare]').hidden = !a;
    const pn = $('.timg-pdfnav');
    pn.hidden = !I.pdf;
    if (I.pdf) $('[data-pdfpage]').textContent = 'Page ' + I.pdfPage + ' / ' + I.pdf.numPages;
    $('[data-info]').textContent = a ? I.nom + ' · ' + I.original.width + ' × ' + I.original.height + ' px' : '';
    I.host.querySelectorAll('[data-act="exporter"],[data-act="svg"],[data-act="pdf"],[data-act="copier-svg"],[data-act="reinit"]').forEach(b => {
      b.disabled = !a || ((b.dataset.act === 'svg' || b.dataset.act === 'pdf' || b.dataset.act === 'copier-svg') && !I.svg);
    });
    majApercu(); majTaille();
  }

  function majTaille() {
    const t = $('[data-taille]');
    if (!I.resultat) { t.textContent = ''; return; }
    const dpi = Math.max(1, Math.round(I.r.dpi) || 300);
    const mm = px => (px / dpi * 25.4).toLocaleString('fr-FR', { maximumFractionDigits: 1 });
    t.textContent = I.resultat.width + ' × ' + I.resultat.height + ' px — ' + mm(I.resultat.width) + ' × ' + mm(I.resultat.height) + ' mm à ' + dpi + ' dpi';
  }

  function majComparaison() {
    const clip = $('[data-avant-clip]');
    if (clip) clip.style.width = I.comparaison + '%';
  }

  function majApercu() {
    if (!I.resultat) return;
    const avant = $('[data-avant]'), apres = $('[data-apres]'), img = $('[data-svg]');
    // Même cadre pour les deux : l'avant est mis à l'échelle de l'après.
    apres.width = I.resultat.width; apres.height = I.resultat.height;
    ctx2d(apres).drawImage(I.resultat, 0, 0);
    avant.width = I.resultat.width; avant.height = I.resultat.height;
    const xa = ctx2d(avant); xa.imageSmoothingEnabled = false;
    xa.clearRect(0, 0, avant.width, avant.height);
    xa.drawImage(I.original, 0, 0, avant.width, avant.height);
    const vect = I.mode === 'vectoriser' && I.svg;
    if (vect) {
      if (img.dataset.svgUrl) URL.revokeObjectURL(img.dataset.svgUrl);
      const u = URL.createObjectURL(new Blob([I.svg], { type: 'image/svg+xml' }));
      img.dataset.svgUrl = u; img.src = u;
    }
    img.hidden = !vect; apres.style.visibility = vect ? 'hidden' : 'visible';
    $('[data-legende-apres]').textContent = vect ? 'Vectoriel' : 'Après';
    const ti = $('[data-trace]');
    ti.textContent = I.traceInfo ? I.traceInfo.couleurs + ' couleur' + (I.traceInfo.couleurs > 1 ? 's' : '') + ' · ' + I.traceInfo.traces.toLocaleString('fr-FR')
      + ' tracé' + (I.traceInfo.traces > 1 ? 's' : '') + ' · SVG ' + fmtKo(I.traceInfo.octets) : '';
    majComparaison();
  }

  // Les réglages se suivent vite (curseurs) : on attend une courte pause.
  function relancer(quoi) {
    garderPrefs();
    clearTimeout(I.minuteur);
    I.minuteur = setTimeout(() => recalculer(quoi === 'r'), 250);
  }

  async function recalculer(depuisImage) {
    if (!I.original) return;
    if (I.enCours) { I.encore = I.encore || depuisImage || 'v'; return; }
    I.enCours = true;
    $('[data-etape]').textContent = 'Traitement…';
    $('[data-occupe]').hidden = false;
    $('[data-vue]').classList.add('timg-vue--occupe');
    try {
      if (depuisImage === true || !I.resultat) { I.resultat = await traiter(); I.svg = null; I.traceInfo = null; }
      if (I.mode === 'vectoriser') await vectoriser();
    } catch (e) {
      toast(e.message || 'Traitement impossible.', 'danger');
    } finally {
      I.enCours = false;
      if (I.host) { $('[data-occupe]').hidden = true; $('[data-vue]').classList.remove('timg-vue--occupe'); majInterface(); }
      if (I.encore) { const r = I.encore; I.encore = null; recalculer(r === true); }
    }
  }

  function mount(root, ctx) {
    if (ctx) CTX = Object.assign(CTX, ctx);
    if (!root) return;
    if (!I.host) {
      const p = lirePrefs();
      I.r = Object.assign({}, DEFAUT_R, { dpi: (p.r && p.r.dpi) || 300, format: (p.r && p.r.format) || 'png', qualite: (p.r && p.r.qualite) || 92 });
      I.v = Object.assign({}, DEFAUT_V, p.v || {});
      if (!I.modeAdresse) I.mode = p.mode === 'vectoriser' ? 'vectoriser' : 'ameliorer';
      I.host = document.createElement('div');
      root.appendChild(I.host);
      construire();
      signaler();
      return;
    }
    root.appendChild(I.host);
  }

  function demonter() {
    const img = I.host && I.host.querySelector('[data-svg]');
    if (img && img.dataset.svgUrl) { URL.revokeObjectURL(img.dataset.svgUrl); delete img.dataset.svgUrl; }
  }

  window.MyToolsImage = {
    mount, demonter,
    adresse: {
      etat: () => ({ mode: I.mode }),
      aller: a => {
        const m = a && a.mode === 'vectoriser' ? 'vectoriser' : 'ameliorer';
        I.modeAdresse = true;
        if (m !== I.mode) { I.mode = m; if (I.host) { majInterface(); if (m === 'vectoriser' && I.resultat && !I.svg) recalculer(false); } }
      },
    },
    _interne: { pngAvecDpi, jpgAvecDpi, crc32, boiteUtile, fondTransparent, niveauxAuto },
  };
})();
