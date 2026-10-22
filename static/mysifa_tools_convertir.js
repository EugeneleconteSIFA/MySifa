/* MyTools › Convertir — un fichier courant vers un autre format.
 *
 * Repris du convertisseur de Prismix (music/prismix/web/src/convertir.js et
 * conv/navigateur.js), adapté à MySifa. Le navigateur fait tout ce qu'il sait
 * faire, le fichier ne quitte alors pas le poste :
 *   images et SVG → PNG, JPEG, WebP, AVIF, BMP, ICO, PDF (une page par image),
 *   SVG vectorisé en couleurs (imagetracerjs) ;
 *   PDF → images par page, texte (pdf.js), fusion de plusieurs PDF (pdf-lib) ;
 *   CSV / TSV → JSON.
 * Le reste part sur le serveur (POST /api/tools/convertir, app/services/conversion.py) :
 * documents, présentations, tableurs (LibreOffice), audio et vidéo (ffmpeg), GIF /
 * TIFF / HEIC (ImageMagick), SVG noir et blanc (potrace), PDF → Word, compression.
 * Une conversion dont l'outil manque sur le serveur est grisée, avec le paquet à
 * installer (GET /api/tools/convertir/outils).
 *
 * Pas de lien YouTube ici, à la différence de Prismix : télécharger depuis
 * YouTube enfreint ses conditions d'utilisation.
 *
 *   MyToolsConvertir.mount(root, ctx)   ctx = { toast(msg, type) }
 */
(function () {
  'use strict';
  if (window.MyToolsConvertir) return;

  const URL_TRACER = 'https://cdn.jsdelivr.net/npm/imagetracerjs@1.2.6/imagetracer_v1.2.6.js';
  const URL_PDFLIB = 'https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js';
  const URL_PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs';
  const URL_PDFJS_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';

  const FAMILLES = {
    image: { lib: 'Image', ext: ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'avif', 'ico', 'tif', 'tiff', 'heic', 'heif'] },
    svg: { lib: 'Image vectorielle', ext: ['svg'] },
    pdf: { lib: 'PDF', ext: ['pdf'] },
    presentation: { lib: 'Présentation', ext: ['pptx', 'ppt', 'odp', 'key', 'pps', 'ppsx'] },
    document: { lib: 'Document', ext: ['docx', 'doc', 'odt', 'rtf', 'txt', 'md', 'html', 'htm', 'pages'] },
    tableur: { lib: 'Tableur', ext: ['xlsx', 'xls', 'ods', 'csv', 'tsv', 'numbers'] },
    audio: { lib: 'Audio', ext: ['mp3', 'wav', 'ogg', 'oga', 'm4a', 'aac', 'flac', 'opus', 'aiff', 'aif', 'wma'] },
    video: { lib: 'Vidéo', ext: ['mp4', 'mov', 'webm', 'mkv', 'avi', 'm4v', '3gp', 'wmv', 'mpg', 'mpeg', 'flv'] },
  };
  // Icônes des familles (grille 24, trait).
  const ICONES = {
    image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
    svg: '<path d="M4 20c4-1 6-5 8-8s4-6 8-8"/><circle cx="4" cy="20" r="1.6"/><circle cx="20" cy="4" r="1.6"/><path d="M12 12h.01"/>',
    pdf: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h8M8 17h5"/>',
    presentation: '<rect x="2" y="4" width="20" height="13" rx="2"/><path d="M12 17v4M8 21h8"/>',
    document: '<path d="M6 2h9l5 5v15H6z"/><path d="M9 11h7M9 15h7M9 19h4"/>',
    tableur: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    audio: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    video: '<rect x="2" y="5" width="15" height="14" rx="2"/><path d="M17 10l5-3v10l-5-3z"/>',
    convertir: '<path d="M4 7h11.5"/><path d="M12.5 3.5L16 7l-3.5 3.5"/><path d="M20 17H8.5"/><path d="M11.5 13.5L8 17l3.5 3.5"/>',
    deposer: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  };
  const svg = (k, t) => '<svg width="' + (t || 22) + '" height="' + (t || 22) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONES[k] + '</svg>';
  const extDe = f => ((f.name.match(/\.([a-z0-9]{1,6})$/i) || [])[1] || '').toLowerCase();
  const familleDe = f => Object.keys(FAMILLES).find(k => FAMILLES[k].ext.includes(extDe(f)));

  // ou : nav = navigateur ; auto = navigateur, serveur si le navigateur ne sait pas ; serveur.
  const IMG_OPT = ['largeur', 'qualite'];
  const CIBLES = {
    image: [
      { id: 'png', lib: 'PNG', ou: 'auto', opt: ['largeur'] }, { id: 'jpg', lib: 'JPEG', ou: 'auto', opt: IMG_OPT },
      { id: 'webp', lib: 'WebP', ou: 'auto', opt: IMG_OPT }, { id: 'avif', lib: 'AVIF', ou: 'auto', opt: IMG_OPT },
      { id: 'bmp', lib: 'BMP', ou: 'nav', opt: ['largeur'] }, { id: 'gif', lib: 'GIF', ou: 'serveur', opt: ['largeur'] },
      { id: 'tiff', lib: 'TIFF', ou: 'serveur', opt: ['largeur'] }, { id: 'ico', lib: 'Icône ICO', ou: 'nav' },
      { id: 'pdf', lib: 'PDF (une page par image)', ou: 'nav', opt: ['page'], groupe: true },
      { id: 'svg', lib: 'SVG vectorisé · couleurs', ou: 'nav', opt: ['detail'] },
      { id: 'svg-nb', lib: 'SVG vectorisé · noir et blanc', ou: 'serveur', opt: ['seuil'] },
    ],
    svg: [{ id: 'png', lib: 'PNG', ou: 'nav', opt: ['echelle'] }, { id: 'jpg', lib: 'JPEG', ou: 'nav', opt: ['echelle', 'qualite'] },
      { id: 'webp', lib: 'WebP', ou: 'nav', opt: ['echelle', 'qualite'] }, { id: 'ico', lib: 'Icône ICO', ou: 'nav' },
      { id: 'pdf', lib: 'PDF', ou: 'nav', opt: ['page'], groupe: true }],
    pdf: [{ id: 'png', lib: 'Images PNG (une par page)', ou: 'nav', opt: ['dpi'] }, { id: 'jpg', lib: 'Images JPEG (une par page)', ou: 'nav', opt: ['dpi'] },
      { id: 'txt', lib: 'Texte brut', ou: 'nav' }, { id: 'fusion', lib: 'Fusionner en un seul PDF', ou: 'nav', groupe: true, min: 2 },
      { id: 'docx', lib: 'Word (mise en page approchée)', ou: 'serveur' }, { id: 'compresser', lib: 'Compresser', ou: 'serveur', opt: ['niveau'] }],
    presentation: [{ id: 'pdf', lib: 'PDF', ou: 'serveur' }, { id: 'pptx', lib: 'PowerPoint', ou: 'serveur' }, { id: 'odp', lib: 'OpenDocument (ODP)', ou: 'serveur' },
      { id: 'png', lib: 'Images PNG (une par diapo)', ou: 'serveur', opt: ['dpi'] }, { id: 'jpg', lib: 'Images JPEG (une par diapo)', ou: 'serveur', opt: ['dpi'] }],
    document: [{ id: 'pdf', lib: 'PDF', ou: 'serveur' }, { id: 'docx', lib: 'Word', ou: 'serveur' }, { id: 'odt', lib: 'OpenDocument (ODT)', ou: 'serveur' },
      { id: 'rtf', lib: 'RTF', ou: 'serveur' }, { id: 'txt', lib: 'Texte brut', ou: 'serveur' }, { id: 'html', lib: 'Page web (HTML)', ou: 'serveur' }],
    tableur: [{ id: 'xlsx', lib: 'Excel', ou: 'serveur' }, { id: 'ods', lib: 'OpenDocument (ODS)', ou: 'serveur' }, { id: 'csv', lib: 'CSV', ou: 'serveur' },
      { id: 'pdf', lib: 'PDF', ou: 'serveur' }, { id: 'json', lib: 'JSON', ou: 'auto' }],
    audio: [{ id: 'mp3', lib: 'MP3', ou: 'serveur' }, { id: 'wav', lib: 'WAV', ou: 'serveur' }, { id: 'ogg', lib: 'OGG', ou: 'serveur' },
      { id: 'flac', lib: 'FLAC (sans perte)', ou: 'serveur' }, { id: 'm4a', lib: 'M4A (AAC)', ou: 'serveur' }, { id: 'opus', lib: 'Opus', ou: 'serveur' }, { id: 'aiff', lib: 'AIFF', ou: 'serveur' }],
    video: [{ id: 'mp4', lib: 'MP4', ou: 'serveur', opt: ['resolution', 'vqualite'] }, { id: 'webm', lib: 'WebM', ou: 'serveur', opt: ['resolution', 'vqualite'] },
      { id: 'mov', lib: 'MOV', ou: 'serveur', opt: ['resolution', 'vqualite'] }, { id: 'mkv', lib: 'MKV', ou: 'serveur', opt: ['resolution', 'vqualite'] },
      { id: 'gif', lib: 'GIF animé', ou: 'serveur', opt: ['glargeur'] }, { id: 'mp3', lib: 'Son seul · MP3', ou: 'serveur' },
      { id: 'm4a', lib: 'Son seul · M4A', ou: 'serveur' }, { id: 'wav', lib: 'Son seul · WAV', ou: 'serveur' }],
  };
  const OPTIONS = {
    largeur: { lib: 'Taille', cle: 'largeur', choix: [['0', 'Originale'], ['2048', '2048 px'], ['1080', '1080 px'], ['512', '512 px']] },
    qualite: { lib: 'Qualité', cle: 'qualite', choix: [['0.95', 'Haute'], ['0.88', 'Bonne'], ['0.72', 'Légère']], defaut: '0.88' },
    page: { lib: 'Pages', cle: 'page', choix: [['image', 'Taille de l\'image'], ['a4', 'A4']] },
    echelle: { lib: 'Taille', cle: 'echelle', choix: [['1', '×1'], ['2', '×2'], ['4', '×4']], defaut: '2' },
    detail: { lib: 'Détail', cle: 'detail', choix: [['logo', 'Logo (8 couleurs)'], ['illustration', 'Illustration (16)'], ['photo', 'Photo (32)']], defaut: 'logo' },
    seuil: { lib: 'Seuil', cle: 'seuil', choix: [['35', 'Clair'], ['50', 'Moyen'], ['65', 'Foncé']], defaut: '50' },
    dpi: { lib: 'Résolution', cle: 'dpi', choix: [['72', 'Écran'], ['150', 'Normale'], ['300', 'Impression']], defaut: '150' },
    niveau: { lib: 'Compression', cle: 'niveau', choix: [['normal', 'Normale'], ['fort', 'Forte']] },
    resolution: { lib: 'Résolution', cle: 'resolution', choix: [['0', 'Originale'], ['1080', '1080p'], ['720', '720p'], ['480', '480p']] },
    vqualite: { lib: 'Qualité', cle: 'qualite', choix: [['haute', 'Haute'], ['moyenne', 'Moyenne'], ['legere', 'Légère']], defaut: 'moyenne' },
    glargeur: { lib: 'Largeur', cle: 'largeur', choix: [['320', '320 px'], ['480', '480 px'], ['720', '720 px']], defaut: '480' },
  };
  // Outil serveur nécessaire par conversion (même règle que conversion.outil_requis).
  function outilRequis(fam, c) {
    if (fam === 'audio' || fam === 'video') return 'ffmpeg';
    if (fam === 'presentation' || fam === 'document' || fam === 'tableur') return 'soffice';
    if (fam === 'pdf') return c === 'compresser' ? 'gs' : 'soffice';
    if (fam === 'image') return c === 'svg-nb' ? 'potrace' : 'convert';
    return '';
  }

  let CTX = { toast: () => {} };
  const C = { host: null, fichiers: [], fam: null, cible: null, options: {}, resultats: [], serveur: null, enCours: false };

  // ── Utilitaires ──────────────────────────────────────────────────
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const base = f => f.name.replace(/\.[^.]+$/, '');
  const taille = n => (n > 1e6 ? (n / 1e6).toFixed(1).replace('.', ',') + ' Mo' : Math.max(1, Math.round(n / 1e3)) + ' Ko');
  const MIME = { png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp', avif: 'image/avif' };
  function charger(url) {
    return new Promise((ok, ko) => {
      if (document.querySelector('script[data-src="' + url + '"]')) { ok(); return; }
      const s = document.createElement('script');
      s.src = url; s.setAttribute('data-src', url);
      s.onload = () => ok(); s.onerror = () => ko(new Error('Bibliothèque indisponible — vérifier la connexion.'));
      document.head.appendChild(s);
    });
  }
  let _pdfjs = null;
  async function pdfjs() {
    if (!_pdfjs) { _pdfjs = await import(URL_PDFJS); _pdfjs.GlobalWorkerOptions.workerSrc = URL_PDFJS_WORKER; }
    return _pdfjs;
  }
  function telecharger(blob, nom) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = nom;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }
  const enBlob = (c, type, q) => new Promise((ok, ko) => c.toBlob(b => (b ? ok(b) : ko(new Error('Encodage impossible.'))), type, q));
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

  // ZIP sans compression (les formats produits sont déjà compressés).
  async function zip(fichiers) {
    const parts = [], central = [];
    let pos = 0;
    for (const f of fichiers) {
      const data = new Uint8Array(await f.blob.arrayBuffer());
      const nom = new TextEncoder().encode(f.nom), crc = crc32(data);
      const loc = new DataView(new ArrayBuffer(30));
      loc.setUint32(0, 0x04034b50, true); loc.setUint16(4, 20, true); loc.setUint16(6, 0x0800, true);
      loc.setUint32(14, crc, true); loc.setUint32(18, data.length, true); loc.setUint32(22, data.length, true); loc.setUint16(26, nom.length, true);
      const cen = new DataView(new ArrayBuffer(46));
      cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 20, true); cen.setUint16(6, 20, true); cen.setUint16(8, 0x0800, true);
      cen.setUint32(16, crc, true); cen.setUint32(20, data.length, true); cen.setUint32(24, data.length, true); cen.setUint16(28, nom.length, true);
      cen.setUint32(42, pos, true);
      parts.push(loc, nom, data); central.push(cen, nom);
      pos += 30 + nom.length + data.length;
    }
    const tailleC = central.reduce((s, x) => s + x.byteLength, 0);
    const fin = new DataView(new ArrayBuffer(22));
    fin.setUint32(0, 0x06054b50, true); fin.setUint16(8, fichiers.length, true); fin.setUint16(10, fichiers.length, true);
    fin.setUint32(12, tailleC, true); fin.setUint32(16, pos, true);
    return new Blob([...parts, ...central, fin], { type: 'application/zip' });
  }

  // ── Conversions dans le navigateur ───────────────────────────────
  async function svgBitmap(f, k) {
    const doc = new DOMParser().parseFromString(await f.text(), 'image/svg+xml'), svg = doc.documentElement;
    if (svg.nodeName !== 'svg') throw new Error(f.name + ' : SVG illisible.');
    const vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
    const w = parseFloat(svg.getAttribute('width')) || vb[2] || 512, h = parseFloat(svg.getAttribute('height')) || vb[3] || 512;
    svg.setAttribute('width', w * k); svg.setAttribute('height', h * k);
    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)], { type: 'image/svg+xml' }));
    try { const img = new Image(); img.src = url; await img.decode(); return await createImageBitmap(img, { resizeWidth: Math.round(w * k), resizeHeight: Math.round(h * k) }); }
    finally { URL.revokeObjectURL(url); }
  }
  async function bitmap(f) {
    if (/\.svg$/i.test(f.name)) return svgBitmap(f, 1);
    try { return await createImageBitmap(f, { imageOrientation: 'from-image' }); }
    catch (e) {
      // HEIC, TIFF… : le serveur les lit, et rend un PNG.
      const r = await serveur([f], 'png', {});
      return createImageBitmap(r[0].blob);
    }
  }
  function versCanvas(bmp, largeurMax, fondBlanc) {
    const k = largeurMax > 0 ? Math.min(1, largeurMax / Math.max(bmp.width, bmp.height)) : 1;
    const c = document.createElement('canvas');
    c.width = Math.max(1, Math.round(bmp.width * k)); c.height = Math.max(1, Math.round(bmp.height * k));
    const g = c.getContext('2d');
    if (fondBlanc) { g.fillStyle = 'white'; g.fillRect(0, 0, c.width, c.height); }
    g.drawImage(bmp, 0, 0, c.width, c.height);
    return c;
  }
  async function image(f, cible, o) {
    const bmp = /\.svg$/i.test(f.name) ? await svgBitmap(f, Number(o.echelle) || 1) : await bitmap(f);
    const c = versCanvas(bmp, Number(o.largeur) || 0, cible === 'jpg' || cible === 'bmp');
    if (cible === 'bmp') return [{ nom: base(f) + '.bmp', blob: bmpDe(c) }];
    const blob = await enBlob(c, MIME[cible], Number(o.qualite) || 0.88);
    if (blob.type !== MIME[cible]) return null; // AVIF non pris en charge ici : le serveur prend le relais
    return [{ nom: base(f) + '.' + cible, blob }];
  }
  function bmpDe(c) {
    const w = c.width, h = c.height, px = c.getContext('2d').getImageData(0, 0, w, h).data;
    const ligne = Math.ceil(w * 3 / 4) * 4, tailleImg = ligne * h;
    const b = new DataView(new ArrayBuffer(54 + tailleImg));
    b.setUint16(0, 0x4d42, true); b.setUint32(2, 54 + tailleImg, true); b.setUint32(10, 54, true);
    b.setUint32(14, 40, true); b.setInt32(18, w, true); b.setInt32(22, h, true); b.setUint16(26, 1, true); b.setUint16(28, 24, true);
    b.setUint32(34, tailleImg, true); b.setInt32(38, 2835, true); b.setInt32(42, 2835, true);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const s = ((h - 1 - y) * w + x) * 4, d = 54 + y * ligne + x * 3;
      b.setUint8(d, px[s + 2]); b.setUint8(d + 1, px[s + 1]); b.setUint8(d + 2, px[s]);
    }
    return new Blob([b], { type: 'image/bmp' });
  }
  async function ico(f) {
    const bmp = /\.svg$/i.test(f.name) ? await svgBitmap(f, 4) : await bitmap(f);
    const tailles = [16, 32, 48, 256], images = [];
    for (const t of tailles) {
      const c = document.createElement('canvas'); c.width = c.height = t;
      const g = c.getContext('2d'), k = Math.min(t / bmp.width, t / bmp.height);
      g.imageSmoothingQuality = 'high';
      g.drawImage(bmp, (t - bmp.width * k) / 2, (t - bmp.height * k) / 2, bmp.width * k, bmp.height * k);
      images.push(new Uint8Array(await (await enBlob(c, 'image/png')).arrayBuffer()));
    }
    const tete = new DataView(new ArrayBuffer(6 + 16 * images.length));
    tete.setUint16(2, 1, true); tete.setUint16(4, images.length, true);
    let pos = tete.byteLength;
    images.forEach((im, i) => {
      const o2 = 6 + i * 16, t = tailles[i] % 256;
      tete.setUint8(o2, t); tete.setUint8(o2 + 1, t); tete.setUint16(o2 + 4, 1, true); tete.setUint16(o2 + 6, 32, true);
      tete.setUint32(o2 + 8, im.length, true); tete.setUint32(o2 + 12, pos, true); pos += im.length;
    });
    return [{ nom: base(f) + '.ico', blob: new Blob([tete, ...images], { type: 'image/x-icon' }) }];
  }
  async function imagesEnPdf(fichiers, o) {
    await charger(URL_PDFLIB);
    const P = window.PDFLib, doc = await P.PDFDocument.create();
    for (const f of fichiers) {
      const bmp = /\.svg$/i.test(f.name) ? await svgBitmap(f, 2) : await bitmap(f);
      const c = versCanvas(bmp, 2400, true);
      const img = await doc.embedJpg(new Uint8Array(await (await enBlob(c, 'image/jpeg', 0.9)).arrayBuffer()));
      const A4 = [595.28, 841.89];
      const [pw, ph] = o.page === 'a4' ? (c.width > c.height ? [A4[1], A4[0]] : A4) : [c.width * 0.75, c.height * 0.75];
      const k = Math.min(pw / c.width, ph / c.height), w = c.width * k, h = c.height * k;
      doc.addPage([pw, ph]).drawImage(img, { x: (pw - w) / 2, y: (ph - h) / 2, width: w, height: h });
    }
    return [{ nom: base(fichiers[0]) + (fichiers.length > 1 ? '-' + fichiers.length + '-pages' : '') + '.pdf',
      blob: new Blob([await doc.save()], { type: 'application/pdf' }) }];
  }
  const DETAILS = {
    logo: { numberofcolors: 8, colorquantcycles: 3, pathomit: 12, ltres: 1, qtres: 1, blurradius: 0, max: 900 },
    illustration: { numberofcolors: 16, colorquantcycles: 3, pathomit: 8, ltres: 0.8, qtres: 0.8, blurradius: 1, blurdelta: 30, max: 1100 },
    photo: { numberofcolors: 32, colorquantcycles: 2, pathomit: 4, ltres: 0.5, qtres: 0.5, blurradius: 2, blurdelta: 40, max: 800 },
  };
  async function vectoriser(f, o) {
    await charger(URL_TRACER);
    const d = DETAILS[o.detail] || DETAILS.logo;
    const bmp = await bitmap(f);
    const c = versCanvas(bmp, d.max, false);
    const im = c.getContext('2d').getImageData(0, 0, c.width, c.height);
    await new Promise(r => setTimeout(r, 20));
    const opts = Object.assign({}, d, { viewbox: true, roundcoords: 1, linefilter: true, strokewidth: 1, desc: false });
    delete opts.max;
    const svg = window.ImageTracer.imagedataToSVG(im, opts).replace(/<svg /, '<svg width="' + bmp.width + '" height="' + bmp.height + '" ');
    return [{ nom: base(f) + '.svg', blob: new Blob([svg], { type: 'image/svg+xml' }) }];
  }
  async function pdfEnImages(f, cible, o, pas) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await f.arrayBuffer()) }).promise;
    const k = (Number(o.dpi) || 150) / 72, sortie = [];
    for (let i = 1; i <= doc.numPages; i++) {
      pas(i / doc.numPages);
      const page = await doc.getPage(i), vp = page.getViewport({ scale: k });
      const c = document.createElement('canvas'); c.width = Math.round(vp.width); c.height = Math.round(vp.height);
      const g = c.getContext('2d'); g.fillStyle = 'white'; g.fillRect(0, 0, c.width, c.height);
      await page.render({ canvasContext: g, viewport: vp, intent: 'print' }).promise;
      sortie.push({ nom: base(f) + '-page-' + String(i).padStart(String(doc.numPages).length, '0') + '.' + cible,
        blob: await enBlob(c, MIME[cible], 0.9) });
    }
    return sortie;
  }
  async function pdfEnTexte(f) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await f.arrayBuffer()) }).promise;
    const pages = [];
    for (let i = 1; i <= doc.numPages; i++) {
      const t = await (await doc.getPage(i)).getTextContent();
      let ligne = '', y = null; const lignes = [];
      t.items.forEach(it => {
        const yy = Math.round(it.transform[5]);
        if (y !== null && Math.abs(yy - y) > 2) { lignes.push(ligne); ligne = ''; }
        ligne += it.str + (it.hasEOL ? '' : ''); y = yy;
        if (it.hasEOL) { lignes.push(ligne); ligne = ''; y = null; }
      });
      if (ligne) lignes.push(ligne);
      pages.push(lignes.join('\n'));
    }
    return [{ nom: base(f) + '.txt', blob: new Blob([pages.join('\n\n\f')], { type: 'text/plain;charset=utf-8' }) }];
  }
  async function fusion(fichiers) {
    await charger(URL_PDFLIB);
    const P = window.PDFLib, doc = await P.PDFDocument.create();
    for (const f of fichiers) {
      let src;
      try { src = await P.PDFDocument.load(await f.arrayBuffer()); }
      catch (e) { throw new Error(f.name + ' : PDF protégé ou illisible.'); }
      (await doc.copyPages(src, src.getPageIndices())).forEach(p => doc.addPage(p));
    }
    return [{ nom: base(fichiers[0]) + '-fusion.pdf', blob: new Blob([await doc.save()], { type: 'application/pdf' }) }];
  }
  async function csvEnJson(f) {
    const txt = (await f.text()).replace(/^﻿/, '');
    const sep = /\.tsv$/i.test(f.name) ? '\t' : [',', ';', '\t'].map(s => [s, txt.split('\n')[0].split(s).length]).sort((a, b) => b[1] - a[1])[0][0];
    const lignes = []; let champ = '', ligne = [], guill = false;
    for (let i = 0; i < txt.length; i++) {
      const c = txt[i];
      if (guill) { if (c === '"' && txt[i + 1] === '"') { champ += '"'; i++; } else if (c === '"') guill = false; else champ += c; }
      else if (c === '"') guill = true;
      else if (c === sep) { ligne.push(champ); champ = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && txt[i + 1] === '\n') i++; ligne.push(champ); lignes.push(ligne); ligne = []; champ = ''; }
      else champ += c;
    }
    if (champ || ligne.length) { ligne.push(champ); lignes.push(ligne); }
    const non = lignes.filter(l => l.some(x => x !== ''));
    const tete = non[0] || [], rangs = non.slice(1);
    const valeur = v => (v !== '' && !isNaN(Number(v.replace(',', '.'))) && !/^0\d/.test(v) ? Number(v.replace(',', '.')) : v);
    const data = rangs.map(r => Object.fromEntries(tete.map((k, i) => [k || 'colonne_' + (i + 1), valeur(r[i] == null ? '' : r[i])])));
    return [{ nom: base(f) + '.json', blob: new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }) }];
  }

  // ── Serveur ──────────────────────────────────────────────────────
  function serveur(liste, cibleId, o, progres) {
    return new Promise((ok, ko) => {
      const fd = new FormData();
      fd.append('cible', cibleId); fd.append('options', JSON.stringify(o || {}));
      liste.forEach(f => fd.append('fichiers', f, f.name));
      const x = new XMLHttpRequest();
      x.open('POST', '/api/tools/convertir');
      x.withCredentials = true;
      x.responseType = 'blob';
      x.upload.onprogress = e => e.lengthComputable && progres && progres(e.loaded / e.total, 'envoi');
      x.upload.onload = () => progres && progres(1, 'traitement');
      x.onload = async () => {
        if (x.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); return; }
        if (x.status !== 200) {
          let m = 'La conversion a échoué.';
          try { const j = JSON.parse(await x.response.text()); m = typeof j.detail === 'string' ? j.detail : m; } catch (e) {}
          return ko(new Error(m));
        }
        const dispo = x.getResponseHeader('Content-Disposition') || '';
        const nom = decodeURIComponent(dispo.split("''")[1] || ('conversion.' + cibleId));
        ok([{ nom, blob: x.response }]);
      };
      x.onerror = () => ko(new Error('Connexion perdue pendant l\'envoi.'));
      x.send(fd);
    });
  }
  async function chargerOutils() {
    try {
      const r = await fetch('/api/tools/convertir/outils', { credentials: 'include' });
      C.serveur = r.ok ? await r.json() : { outils: {}, paquets: {} };
    } catch (e) { C.serveur = { outils: {}, paquets: {} }; }
    rendre();
  }
  function dispoServeur(c) {
    if (c.ou !== 'serveur') return true;
    if (!C.serveur) return true;
    const o = outilRequis(C.fam, c.id);
    return !o || !!(C.serveur.outils || {})[o];
  }

  // ── Écran ────────────────────────────────────────────────────────
  function ajouter(liste) {
    for (const f of liste) {
      const fa = familleDe(f);
      if (!fa) { CTX.toast(f.name + ' : type de fichier non pris en charge.', 'danger'); continue; }
      if (C.fam && fa !== C.fam) { CTX.toast(f.name + ' ignoré : un seul type de fichier à la fois (' + FAMILLES[C.fam].lib.toLowerCase() + ' ici).', 'info'); continue; }
      C.fam = fa; C.fichiers.push(f);
    }
    if (C.fichiers.length > 50) { C.fichiers = C.fichiers.slice(0, 50); CTX.toast('50 fichiers au plus à la fois.', 'info'); }
    if (C.cible && !CIBLES[C.fam].some(c => c.id === C.cible.id)) C.cible = null;
    C.resultats = [];
    rendre();
  }

  function construire() {
    const h = C.host;
    h.className = 'tconv';
    h.innerHTML =
      '<header class="tconv-tete"><span class="tconv-tete-ic">' + svg('convertir', 26) + '</span><div><h2>Convertir un fichier</h2>'
      + '<p>Plus de 50 formats. Ce qui peut se faire sur ce poste s\'y fait ; le reste passe par le serveur MySifa, qui efface tout aussitôt.</p></div></header>'
      + '<ol class="tconv-etapes" data-etapes>'
      + '<li data-n="1"><b>1</b><span>Déposer</span></li><li data-n="2"><b>2</b><span>Choisir le format</span></li><li data-n="3"><b>3</b><span>Convertir</span></li></ol>'
      + '<div class="tconv-carte">'
      + '<div class="tconv-depot" tabindex="0" role="button" data-a="choisir" data-bulle="Choisir des fichiers">'
      + '<span class="tconv-depot-ic">' + svg('deposer', 30) + '</span>'
      + '<strong>Déposer un ou plusieurs fichiers</strong><span>ou cliquer pour les choisir · 50 fichiers d\'un même type au plus</span></div>'
      + '<input type="file" multiple hidden data-fichiers>'
      + '<div data-zone="fichiers"></div><div data-zone="cibles"></div><div data-zone="options"></div><div data-zone="action"></div><div data-zone="resultats"></div>'
      + '</div>'
      + '<section class="tconv-familles" data-zone="familles"></section>';
    const inp = h.querySelector('[data-fichiers]');
    inp.addEventListener('change', () => { ajouter([...inp.files]); inp.value = ''; });
    const depot = h.querySelector('.tconv-depot');
    depot.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inp.click(); } });
    depot.addEventListener('dragover', e => { e.preventDefault(); depot.classList.add('tconv-survol'); });
    depot.addEventListener('dragleave', () => depot.classList.remove('tconv-survol'));
    depot.addEventListener('drop', e => { e.preventDefault(); depot.classList.remove('tconv-survol'); ajouter([...(e.dataTransfer.files || [])]); });
    h.addEventListener('click', async e => {
      const b = e.target.closest('[data-a],[data-cible],[data-opt],[data-retirer],[data-dl]');
      if (!b || b.disabled) return;
      const d = b.dataset;
      if (d.a === 'choisir') inp.click();
      else if (d.retirer != null) { C.fichiers.splice(Number(d.retirer), 1); if (!C.fichiers.length) { C.fam = null; C.cible = null; } C.resultats = []; rendre(); }
      else if (d.a === 'vider') { C.fichiers = []; C.fam = null; C.cible = null; C.resultats = []; rendre(); }
      else if (d.cible) { C.cible = CIBLES[C.fam].find(c => c.id === d.cible); C.resultats = []; rendre(); }
      else if (d.opt) { C.options[d.opt] = d.val; rendre(); }
      else if (d.a === 'go') lancer();
      else if (d.dl != null) { const x = C.resultats[Number(d.dl)]; telecharger(x.blob, x.nom); }
      else if (d.a === 'zip') telecharger(await zip(C.resultats), 'conversion-' + new Date().toISOString().slice(0, 10) + '.zip');
    });
    rendre();
  }

  function rendre() {
    const h = C.host; if (!h) return;
    const z = n => h.querySelector('[data-zone="' + n + '"]');
    const vide = !C.fichiers.length;
    z('fichiers').innerHTML = vide ? '' : '<div class="tconv-liste">' + C.fichiers.map((f, i) =>
      '<div class="tconv-fichier"><span class="tconv-nom">' + esc(f.name) + '</span><small>' + taille(f.size) + '</small>'
      + '<button type="button" class="tconv-x" data-retirer="' + i + '" data-bulle="Retirer" aria-label="Retirer">×</button></div>').join('')
      + '<button type="button" class="tconv-lien" data-a="vider">Tout retirer</button></div>';
    if (vide) { ['cibles', 'options', 'action', 'resultats'].forEach(k => { z(k).innerHTML = ''; }); }
    else {
      z('cibles').innerHTML = '<div class="tconv-titre">' + esc(FAMILLES[C.fam].lib) + ' → convertir en</div><div class="tconv-pastilles">'
        + CIBLES[C.fam].filter(c => !c.min || C.fichiers.length >= c.min).map(c => {
          const ok = dispoServeur(c), o = outilRequis(C.fam, c.id);
          const bulle = !ok ? 'Absent du serveur : ' + ((C.serveur.paquets || {})[o] || o) : (c.ou === 'serveur' ? 'Traité sur le serveur' : 'Sur ce poste');
          return '<span data-bulle="' + esc(bulle) + '"><button type="button" class="tconv-pastille' + (C.cible && C.cible.id === c.id ? ' actif' : '') + '" data-cible="' + c.id + '"'
            + (ok ? '' : ' disabled') + '>' + esc(c.lib) + (c.ou === 'serveur' ? ' <span class="tconv-srv">serveur</span>' : '') + '</button></span>';
        }).join('') + '</div>';
      const c = C.cible;
      z('options').innerHTML = !c || !c.opt ? '' : c.opt.map(k => {
        const o = OPTIONS[k], v = C.options[o.cle] != null ? C.options[o.cle] : (o.defaut || o.choix[0][0]);
        C.options[o.cle] = v;
        return '<div class="tconv-option"><span>' + esc(o.lib) + '</span><div class="tconv-pastilles">' + o.choix.map(([val, lib]) =>
          '<button type="button" class="tconv-pastille' + (String(v) === val ? ' actif' : '') + '" data-opt="' + o.cle + '" data-val="' + val + '">' + esc(lib) + '</button>').join('') + '</div></div>';
      }).join('');
      z('action').innerHTML = !c ? '' : '<div class="tconv-action"><p class="tconv-ou">'
        + (c.ou === 'serveur' ? 'Traité sur le serveur MySifa, puis effacé aussitôt.' : c.ou === 'nav' ? 'Converti sur ce poste : le fichier ne part nulle part.' : 'Converti sur ce poste (le serveur prend le relais si le navigateur ne lit pas ce format).')
        + '</p><button type="button" class="tconv-go" data-a="go"' + (C.enCours ? ' disabled' : '') + '>' + (C.enCours ? 'Conversion…' : 'Convertir') + '</button>'
        + '<div class="tconv-prog" data-prog hidden><span></span></div><p class="tconv-etape" data-etape></p></div>';
      z('resultats').innerHTML = !C.resultats.length ? '' : '<div class="tconv-titre">Prêt</div>' + C.resultats.map((x, i) =>
        '<div class="tconv-fichier">' + (x.apercu ? '<img src="' + x.apercu + '" alt="">' : '') + '<span class="tconv-nom">' + esc(x.nom) + '</span><small>' + taille(x.blob.size) + '</small>'
        + '<button type="button" class="tconv-btn" data-dl="' + i + '" data-bulle="Télécharger">Télécharger</button></div>').join('')
        + (C.resultats.length > 1 ? '<button type="button" class="tconv-btn" data-a="zip" data-bulle="Un seul fichier ZIP">Tout télécharger (ZIP)</button>' : '');
    }
    // Étapes : où en est-on ?
    const etape = vide ? 1 : (!C.cible ? 2 : 3);
    h.querySelectorAll('[data-etapes] li').forEach(li => {
      const n = Number(li.getAttribute('data-n'));
      li.classList.toggle('fait', n < etape); li.classList.toggle('actif', n === etape);
    });
    // Familles de formats, en tuiles, tant qu'aucun fichier n'est déposé ;
    // une fois déposé, seule la famille du fichier reste, en rappel.
    const fam = h.querySelector('[data-zone="familles"]');
    const tuile = (k, fa) => {
      const cibles = CIBLES[k], local = cibles.filter(c => c.ou !== 'serveur').length;
      const lieu = local === cibles.length ? 'Sur ce poste' : local ? 'Poste et serveur' : 'Sur le serveur';
      return '<div class="tconv-famille' + (C.fam === k ? ' actif' : '') + '"><span class="tconv-famille-ic">' + svg(k) + '</span>'
        + '<div class="tconv-famille-txt"><b>' + esc(fa.lib) + '</b>'
        + '<small>' + esc(fa.ext.slice(0, 6).join(', ').toUpperCase()) + (fa.ext.length > 6 ? '…' : '') + '</small>'
        + '<span class="tconv-famille-vers">→ ' + esc(cibles.slice(0, 4).map(c => c.lib.replace(/ \(.*\)$/, '').replace(/^Images? /, '')).join(', ')) + (cibles.length > 4 ? '…' : '') + '</span></div>'
        + '<span class="tconv-lieu' + (local === cibles.length ? ' local' : '') + '">' + lieu + '</span></div>';
    };
    if (vide) fam.innerHTML = '<div class="tconv-titre">Ce que l\'outil sait convertir</div><div class="tconv-grille">'
      + Object.entries(FAMILLES).map(([k, fa]) => tuile(k, fa)).join('') + '</div>';
    else fam.innerHTML = '';
  }

  function etape(texte, p) {
    const e = C.host.querySelector('[data-etape]'), b = C.host.querySelector('[data-prog]');
    if (e) e.textContent = texte;
    if (b) { b.hidden = p == null; if (p != null) b.firstElementChild.style.width = Math.round(p * 100) + '%'; }
  }

  async function navigateur(f, c, o, pas) {
    if (C.fam === 'tableur' && c.id === 'json') {
      if (/\.(csv|tsv)$/i.test(f.name)) return csvEnJson(f);
      const csv = (await serveur([f], 'csv', {}))[0];
      return csvEnJson(new File([csv.blob], csv.nom));
    }
    if (C.fam === 'pdf') return c.id === 'txt' ? pdfEnTexte(f) : pdfEnImages(f, c.id, o, pas);
    if (c.id === 'ico') return ico(f);
    if (c.id === 'svg') return vectoriser(f, o);
    return image(f, c.id, o);
  }

  async function lancer() {
    const c = C.cible, o = Object.assign({}, C.options), liste = C.fichiers.slice();
    C.enCours = true; C.resultats.forEach(x => x.apercu && URL.revokeObjectURL(x.apercu)); C.resultats = []; rendre();
    try {
      let sortie = [];
      if (c.groupe) {
        etape('Conversion…', 0.3);
        if (c.id === 'fusion') sortie = await fusion(liste);
        else if (c.ou === 'serveur') sortie = await serveur(liste, c.id, o, (p, q) => etape(q === 'envoi' ? 'Envoi…' : 'Conversion sur le serveur…', q === 'envoi' ? p * 0.6 : 0.7));
        else sortie = await imagesEnPdf(liste, o);
      } else {
        for (let i = 0; i < liste.length; i++) {
          const f = liste[i];
          const pas = (p, q) => etape((liste.length > 1 ? (i + 1) + ' / ' + liste.length + ' · ' : '')
            + (q === 'envoi' ? 'Envoi' : q === 'traitement' ? 'Conversion sur le serveur' : 'Conversion') + '…', (i + (p == null ? 0.5 : p)) / liste.length);
          pas(0.05);
          let res = c.ou !== 'serveur' ? await navigateur(f, c, o, p => pas(p)) : null;
          if (!res && c.ou === 'nav') throw new Error('Ce navigateur ne sait pas faire cette conversion.');
          if (!res) res = await serveur([f], c.id, o, (p, q) => pas(q === 'envoi' ? p * 0.5 : 0.7, q));
          sortie.push(...res);
        }
      }
      C.resultats = sortie.map(x => Object.assign({}, x, {
        apercu: /^image\/(png|jpeg|webp|avif|svg)/.test(x.blob.type) || /\.(png|jpe?g|webp|svg)$/i.test(x.nom) ? URL.createObjectURL(x.blob) : null }));
      C.enCours = false; rendre();
      etape('Terminé : ' + C.resultats.length + ' fichier' + (C.resultats.length > 1 ? 's' : '') + '.');
      if (C.resultats.length === 1) telecharger(C.resultats[0].blob, C.resultats[0].nom);
    } catch (e) {
      C.enCours = false; rendre();
      CTX.toast(e.message || 'La conversion a échoué.', 'danger');
    }
  }

  function mount(root, ctx) {
    if (ctx) CTX = Object.assign(CTX, ctx);
    if (!root) return;
    if (!C.host) { C.host = document.createElement('div'); root.appendChild(C.host); construire(); chargerOutils(); return; }
    root.appendChild(C.host);
  }

  window.MyToolsConvertir = { mount, _interne: { familleDe, crc32, outilRequis, CIBLES, FAMILLES } };
})();
