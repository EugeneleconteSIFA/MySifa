// MyTools › Image — fonctions pures (static/mysifa_tools_image.js).
// Lancer : node tests/test_tools_image.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const zlib = require('zlib');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'mysifa_tools_image.js'), 'utf8');
const ctx = { window: {}, document: {}, localStorage: { getItem() { return null; }, setItem() {} },
  URL: {}, Blob: function () {}, setTimeout, clearTimeout };
vm.createContext(ctx);
vm.runInContext(src, ctx);
const F = ctx.window.MyToolsImage._interne;

let echecs = 0;
function ok(nom, v) { if (v) console.log('ok  ', nom); else { echecs++; console.log('ECHEC', nom); } }

// CRC32 : valeur de référence de « 123456789 ».
ok('crc32 de référence', F.crc32(Buffer.from('123456789')) === 0xcbf43926);

// PNG minimal 1×1 fabriqué à la main, puis résolution inscrite à 300 dpi.
function bloc(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(F.crc32(td));
  return Buffer.concat([len, td, crc]);
}
const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(1, 0); ihdr.writeUInt32BE(1, 4); ihdr[8] = 8; ihdr[9] = 6;
const png = Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), bloc('IHDR', ihdr),
  bloc('IDAT', zlib.deflateSync(Buffer.from([0, 255, 0, 0, 255]))), bloc('IEND', Buffer.alloc(0))]);
const sortie = Buffer.from(F.pngAvecDpi(png, 300));
ok('pHYs inséré juste après IHDR', sortie.slice(37, 41).toString() === 'pHYs');
ok('pHYs = 11 811 pixels par mètre (300 dpi)', sortie.readUInt32BE(41) === 11811 && sortie.readUInt32BE(45) === 11811 && sortie[49] === 1);
ok('CRC du bloc pHYs valide', sortie.readUInt32BE(50) === F.crc32(sortie.slice(37, 50)));
ok('reste du fichier intact', sortie.slice(54).equals(png.slice(33)));

// JPG : en-tête JFIF, densité en points par pouce.
const jfif = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0, 16, 0x4a, 0x46, 0x49, 0x46, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0]);
const j = Buffer.from(F.jpgAvecDpi(jfif, 300));
ok('JFIF : unité dpi et densité 300', j[13] === 1 && j.readUInt16BE(14) === 300 && j.readUInt16BE(16) === 300);

// Fond transparent depuis les bords : le carré central, de la même couleur
// que le fond mais entouré d'un trait, reste opaque.
function image(w, h, fn) { const d = new Uint8ClampedArray(w * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const c = fn(x, y); d.set([c, c, c, 255], (y * w + x) * 4); } return { data: d }; }
const w = 9, h = 9;
const img = image(w, h, (x, y) => ((x === 2 || x === 6) && y >= 2 && y <= 6) || ((y === 2 || y === 6) && x >= 2 && x <= 6) ? 0 : 255);
F.fondTransparent(img, w, h, 10);
const a = (x, y) => img.data[(y * w + x) * 4 + 3];
ok('fond extérieur rendu transparent', a(0, 0) === 0 && a(8, 4) === 0);
ok('trait du logo conservé', a(2, 4) === 255);
ok('intérieur du logo non troué', a(4, 4) === 255);

// Rognage : boîte englobante du trait, avec 1 % de marge (0 px ici).
const b = F.boiteUtile(image(w, h, (x, y) => (x >= 3 && x <= 5 && y >= 1 && y <= 7) ? 0 : 255), w, h);
ok('boîte utile du dessin', b && b.x === 3 && b.y === 1 && b.w === 3 && b.h === 7);
ok('image vide : pas de boîte', F.boiteUtile(image(4, 4, () => 255), 4, 4) === null);

// Projets : réglages relus d'un projet enregistré, validés clé par clé.
const RV = F.reglagesValides, DR = F.DEFAUT_R, DV = F.DEFAUT_V;
const exact = { echelle: 3, bruit: 2, nettete: 40, auto: true, lum: -12, contraste: 25, satur: 140, nb: 'seuil', seuil: 90,
  transparent: true, tolerance: 20, rogner: true, dpi: 600, format: 'webp', qualite: 80 };
ok('réglages : restitués à l\'identique', JSON.stringify(RV(DR, exact)) === JSON.stringify(Object.assign({}, DR, exact)));
ok('réglages : absents → défauts', JSON.stringify(RV(DR, null)) === JSON.stringify(DR));
const r1 = RV(DR, { echelle: 7, format: 'exe', nb: 'rouge', lum: 900, dpi: -5, auto: 'oui', inconnu: 1, satur: NaN });
ok('réglages : choix hors liste → défaut', r1.echelle === 1 && r1.format === 'png' && r1.nb === 'couleur');
ok('réglages : curseurs bornés', r1.lum === 100 && r1.dpi === 72);
ok('réglages : type faux → défaut', r1.auto === false && r1.satur === 100);
ok('réglages : clé inconnue ignorée', !('inconnu' in r1));
const v1 = RV(DV, { couleurs: 16, lissage: 9, details: 12, fond: false });
ok('vectorisation : relue et bornée', v1.couleurs === 16 && v1.lissage === 5 && v1.details === 12 && v1.fond === false);
ok('vectorisation : couleurs hors liste → défaut', RV(DV, { couleurs: 5 }).couleurs === DV.couleurs);

if (echecs) { console.log('\n' + echecs + ' cas en échec'); process.exit(1); }
console.log('\nTous les cas passent.');
