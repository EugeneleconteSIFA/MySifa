// MyTools › Utilitaires — logique pure des sous-outils (static/mysifa_tools_util_*.js).
// Lancer : node tests/test_tools_utilitaires.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function charger(nom) {
  const src = fs.readFileSync(path.join(__dirname, '..', 'static', nom), 'utf8');
  const ctx = { window: {}, document: {}, TextEncoder, URL, console };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return ctx.window;
}
let echecs = 0;
function ok(nom, v) { if (v) console.log('ok  ', nom); else { echecs++; console.log('ECHEC', nom); } }
const proche = (a, b, tol) => Math.abs(a - b) <= (tol == null ? 1e-6 : tol);
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ── Codes ────────────────────────────────────────────────────────────
const Q = charger('mysifa_tools_util_qr.js').MyToolsUtil_qr._interne;
ok('EAN-13 : clé de 400638133393 = 1', Q.ean13Cle('400638133393') === 1);
ok('EAN-13 : clé de 978020137962 = 4', Q.ean13Cle('978020137962') === 4);
ok('EAN-13 : 12 chiffres → clé ajoutée', Q.verifier('ean13', '4006381 33393').texte === '4006381333931');
ok('EAN-13 : clé fausse refusée', !!Q.verifier('ean13', '4006381333932').erreur);
ok('EAN-13 : lettres refusées', !!Q.verifier('ean13', '40063813339A').erreur);
ok('EAN-13 : longueur fausse refusée', !!Q.verifier('ean13', '12345').erreur);
ok('Code 128 : accents refusés', !!Q.verifier('code128', 'Réf 12').erreur);
ok('Code 128 : ASCII accepté', Q.verifier('code128', 'LOT-2026/42').ok === true);
ok('QR : saisie vide', Q.verifier('qr', '  ').vide === true);
ok('QR : texte accentué passé en UTF-8 binaire', Q.optionsBwip('qr', 'é', 3).binarytext === true && Q.optionsBwip('qr', 'é', 3).text.length === 2);
ok('Linéaire : texte lisible sous le code', Q.optionsBwip('code128', 'A1', 3).includetext === true && !Q.optionsBwip('qr', 'A1', 3).includetext);

// ── Unités et couleurs ───────────────────────────────────────────────
const V = charger('mysifa_tools_util_unites.js').MyToolsUtil_unites._interne;
const l = V.longueur('1', 'po');
ok('1 pouce = 25,4 mm', proche(l.mm, 25.4));
ok('1 pouce = 72 points', proche(l.pt, 72));
ok('1 pouce = 6 picas', proche(l.pica, 6));
ok('100 µm = 0,1 mm', proche(V.longueur('100', 'um').mm, 0.1));
ok('virgule décimale acceptée', proche(V.longueur('2,5', 'cm').mm, 25));
ok('unité inconnue → null', V.longueur('1', 'yard') === null);
const g1 = V.grammage(80, 100, '');
ok('80 g/m² sur 100 µm → densité 0,8', g1.calcule === 'dens' && proche(g1.dens, 0.8));
const g2 = V.grammage(80, '', 0.8);
ok('80 g/m² à 0,8 → 100 µm', g2.calcule === 'ep' && proche(g2.ep, 100));
const g3 = V.grammage('', 50, 1.4);
ok('PET 50 µm à 1,4 → 70 g/m²', g3.calcule === 'g' && proche(g3.g, 70));
ok('grammage : une seule valeur → vide', V.grammage(80, '', '').vide === true);
const z1 = V.laize(330, 2000, '', 80);
ok('laize 330 × 2 000 m = 660 m²', z1.calcule === 'm2' && proche(z1.m2, 660));
ok('660 m² à 80 g/m² = 52,8 kg', proche(z1.kg, 52.8));
const z2 = V.laize(330, '', 660);
ok('660 m² en laize 330 = 2 000 m', z2.calcule === 'metres' && proche(z2.metres, 2000));
ok('laize absente → vide', V.laize('', 2000).vide === true);
ok('couleur #0085CA lue', egal(V.lireCouleur('#0085CA'), [0, 133, 202]));
ok('couleur abrégée #fff lue', egal(V.lireCouleur('fff'), [255, 255, 255]));
ok('couleur RVB « 0, 133, 202 » lue', egal(V.lireCouleur('0, 133, 202'), [0, 133, 202]));
ok('couleur rgb(…) lue', egal(V.lireCouleur('rgb(10 20 30)'), [10, 20, 30]));
ok('couleur hors bornes refusée', V.lireCouleur('300, 0, 0') === null && V.lireCouleur('#12345') === null);
ok('hex en majuscules', V.hex([0, 133, 202]) === '0085CA');
ok('CMJN du rouge pur = 0/100/100/0', egal(V.rvbVersCmjn([255, 0, 0]), [0, 100, 100, 0]));
ok('CMJN du noir = 0/0/0/100', egal(V.rvbVersCmjn([0, 0, 0]), [0, 0, 0, 100]));
ok('CMJN du blanc = 0/0/0/0', egal(V.rvbVersCmjn([255, 255, 255]), [0, 0, 0, 0]));
ok('CMJN → RVB : cyan pur', egal(V.cmjnVersRvb([100, 0, 0, 0]), [0, 255, 255]));
const aller = [37, 120, 201], retour = V.cmjnVersRvb(V.rvbVersCmjn(aller));
ok('RVB → CMJN → RVB à 3 près', retour.every((v, i) => Math.abs(v - aller[i]) <= 3));
ok('contraste noir / blanc = 21', proche(V.contraste([0, 0, 0], [255, 255, 255]), 21, 1e-9));
ok('contraste d\'une couleur avec elle-même = 1', proche(V.contraste([90, 90, 90], [90, 90, 90]), 1));
ok('contraste #777 sur blanc ≈ 4,48 (échoue AA)', proche(V.contraste([119, 119, 119], [255, 255, 255]), 4.48, 0.01) && !V.verdicts(4.48).aaNormal && V.verdicts(4.48).aaGrand);
ok('ΔE d\'une couleur avec elle-même = 0', proche(V.deltaE(V.lab([10, 200, 30]), V.lab([10, 200, 30])), 0));
// Paires de référence de Sharma et al. (2005), ΔE 2000.
ok('ΔE 2000 : paire 1 de Sharma = 2,0425', proche(V.deltaE([50, 2.6772, -79.7751], [50, 0, -82.7485]), 2.0425, 1e-4));
ok('ΔE 2000 : paire 7 de Sharma = 2,3669', proche(V.deltaE([50, 0, 0], [50, -1, 2]), 2.3669, 1e-4));
ok('Lab du blanc ≈ (100, 0, 0)', (() => { const x = V.lab([255, 255, 255]); return proche(x[0], 100, 0.01) && proche(x[1], 0, 0.01) && proche(x[2], 0, 0.01); })());
const P = charger('mysifa_tools_pantone.js').MyToolsPantone;
ok('table Pantone chargée (60 teintes au moins)', Array.isArray(P) && P.length >= 60 && P.every(p => /^[0-9A-F]{6}$/.test(p[1])));
const pp = V.pantoneProches([0, 133, 202], P, 3);
ok('Pantone le plus proche de #0085CA = Process Blue C', pp[0].nom === 'Process Blue C' && pp[0].de < 0.5 && pp.length === 3);
ok('Pantone : classés du plus proche au plus éloigné', pp[0].de <= pp[1].de && pp[1].de <= pp[2].de);

// ── Comparer ─────────────────────────────────────────────────────────
const D = charger('mysifa_tools_util_comparer.js').MyToolsUtil_comparer._interne;
const rejouer = (a, b, ops) => {
  // Les opérations doivent reconstruire B depuis A, dans l'ordre.
  const sortie = []; let ia = 0, ib = 0, bon = true;
  ops.forEach(o => {
    if (o.t === '=') { bon = bon && o.i === ia && o.j === ib && a[ia] === b[ib]; sortie.push(a[ia]); ia++; ib++; }
    else if (o.t === '-') { bon = bon && o.i === ia; ia++; }
    else { bon = bon && o.j === ib; sortie.push(b[ib]); ib++; }
  });
  return bon && ia === a.length && ib === b.length && egal(sortie, b);
};
const A1 = 'ABCABBA'.split(''), B1 = 'CBABAC'.split('');
const o1 = D.diffSeq(A1, B1);
ok('Myers : ABCABBA → CBABAC reconstruit', rejouer(A1, B1, o1));
ok('Myers : distance minimale 5', o1.filter(o => o.t !== '=').length === 5);
ok('Myers : séquences vides', D.diffSeq([], []).length === 0 && rejouer([], ['x'], D.diffSeq([], ['x'])) && rejouer(['x'], [], D.diffSeq(['x'], [])));
let rnd = 7; const alea = () => (rnd = (rnd * 1103515245 + 12345) % 2147483648) / 2147483648;
let toutBon = true;
for (let k = 0; k < 200; k++) {
  const a = Array.from({ length: Math.floor(alea() * 30) }, () => 'abcd'[Math.floor(alea() * 4)]);
  const b = Array.from({ length: Math.floor(alea() * 30) }, () => 'abcd'[Math.floor(alea() * 4)]);
  if (!rejouer(a, b, D.diffSeq(a, b))) toutBon = false;
}
ok('Myers : 200 paires aléatoires reconstruites', toutBon);
const dt = D.diffTextes('un\ndeux\ntrois\n', 'un\nDEUX\ntrois\nquatre');
ok('texte : 1 retirée, 2 ajoutées, 2 identiques', dt.stats.retirees === 1 && dt.stats.ajoutees === 2 && dt.stats.egales === 2);
ok('texte : casse ignorée', D.diffTextes('un\ndeux', 'UN\nDeux', { casse: true }).stats.egales === 2);
ok('texte : espaces ignorés', D.diffTextes('a  b \n', ' a b', { espaces: true }).stats.egales === 1);
ok('texte : fins de ligne Windows', D.diffTextes('a\r\nb\r\n', 'a\nb').stats.egales === 2);
ok('texte annoté', D.texteAnnote(D.diffTextes('a\nb', 'a\nc')) === '  a\n- b\n+ c\n');
const dm = D.diffMots('Le chat noir dort', 'Le chien noir dort', {});
ok('mots : seul « chat » retiré, « chien » ajouté', egal(dm.a.filter(x => x.t === '-').map(x => x.v), ['chat']) && egal(dm.b.filter(x => x.t === '+').map(x => x.v), ['chien']));
const bl = D.blocs(D.diffSeq(['a', 'b', 'c'], ['a', 'x', 'y', 'c']));
ok('blocs : un changement apparié entre deux identiques', bl.length === 3 && bl[1].t === 'x' && bl[1].moins.length === 1 && bl[1].plus.length === 2);
const li = D.diffListes('A1\nB2\nB2\n\nC3', 'c3\nD4\n', { casse: true });
ok('listes : seulement A, seulement B, communs', egal(li.seulA, ['A1', 'B2']) && egal(li.seulB, ['D4']) && egal(li.communs, ['C3']));
ok('listes : doublon compté', li.doublonsA === 1);
ok('listes : casse respectée par défaut', D.diffListes('abc', 'ABC').communs.length === 0);
ok('CSV : séparateur point-virgule deviné', D.separateur('ref;nom;qte\n1;a;2') === ';');
ok('CSV : séparateur tabulation deviné', D.separateur('ref\tnom\n1\ta') === '\t');
ok('CSV : guillemets et séparateur dans une cellule', egal(D.lireCsv('a;b\n"x;y";"il dit ""oui"""\n'), [['a', 'b'], ['x;y', 'il dit "oui"']]));
ok('CSV : retour à la ligne dans une cellule', egal(D.lireCsv('a,b\r\n"l1\nl2",z'), [['a', 'b'], ['l1\nl2', 'z']]));
ok('CSV : BOM retiré', D.lireCsv('\uFEFFref;nom\n1;a')[0][0] === 'ref');
const dc = D.diffCsv('ref;nom;qte;vieux\n1;Alpha;10;x\n2;Beta;5;y\n3;Gamma;1;z', 'ref;qte;nom;neuf\n1;10;Alpha;p\n2;6;Beta;q\n4;9;Delta;r', 'ref');
ok('CSV : colonne clé et colonnes communes', dc.cle === 'ref' && egal(dc.communes, ['ref', 'nom', 'qte']));
ok('CSV : ligne 3 seulement dans A, ligne 4 seulement dans B', dc.retirees.length === 1 && dc.retirees[0][0] === '3' && dc.ajoutees.length === 1 && dc.ajoutees[0][0] === '4');
ok('CSV : ligne 2 modifiée sur qte seulement (colonnes dans un autre ordre)', dc.modifiees.length === 1 && dc.modifiees[0].cle === '2' && egal(dc.modifiees[0].diffs, [{ col: 'qte', a: '5', b: '6' }]));
ok('CSV : ligne 1 identique', dc.identiques === 1);
ok('CSV : colonnes propres à chaque fichier', egal(dc.seulColA, ['vieux']) && egal(dc.seulColB, ['neuf']));
ok('CSV : sans colonne commune → erreur', !!D.diffCsv('a;b\n1;2', 'c;d\n1;2').erreur);
const ex = D.exportCsvDiff(dc);
ok('CSV : export avec BOM et point-virgule', ex.charCodeAt(0) === 0xFEFF && ex.indexOf('2;Modifiée;qte;5;6') !== -1 && ex.indexOf('3;Seulement dans A') !== -1);
ok('CSV : cellule avec ; protégée à l\'export', D.ecrireCsv([['a;b', 'c']]).indexOf('"a;b";c') !== -1);

// ── Renommer ─────────────────────────────────────────────────────────
const R = charger('mysifa_tools_util_renommer.js').MyToolsUtil_renommer._interne;
const fic = [
  { nom: 'IMG_0003.JPG', date: new Date(2026, 9, 3, 10).getTime(), taille: 300 },
  { nom: 'IMG_0001.JPG', date: new Date(2026, 9, 1, 10).getTime(), taille: 500 },
  { nom: 'IMG_0010.JPG', date: new Date(2026, 9, 2, 10).getTime(), taille: 100 },
];
ok('tri par nom, numérique', egal(R.trier(fic, 'nom').map(f => f.nom), ['IMG_0001.JPG', 'IMG_0003.JPG', 'IMG_0010.JPG']));
ok('tri par date', egal(R.trier(fic, 'date').map(f => f.nom), ['IMG_0001.JPG', 'IMG_0010.JPG', 'IMG_0003.JPG']));
ok('tri par taille', egal(R.trier(fic, 'taille').map(f => f.nom), ['IMG_0010.JPG', 'IMG_0003.JPG', 'IMG_0001.JPG']));
ok('tri par ajout : ordre conservé', egal(R.trier(fic, 'ajout').map(f => f.nom), fic.map(f => f.nom)));
const r1 = R.appliquerRegles(R.trier(fic, 'nom'), { nouveau: 'Photo chantier', numero: { actif: true, position: 'fin', depart: 1, pas: 1, chiffres: 2, sep: '-' }, ext: 'min' }).lignes;
ok('nouveau nom + numéro + extension en minuscules', egal(r1.map(x => x.nouveau), ['Photo chantier-01.jpg', 'Photo chantier-02.jpg', 'Photo chantier-03.jpg']));
const r2 = R.appliquerRegles([fic[0]], { chercher: 'img_', remplacer: 'BAT-', prefixe: 'X', suffixe: '_v2' }).lignes[0];
ok('remplacement insensible à la casse + préfixe + suffixe', r2.nouveau === 'XBAT-0003_v2.JPG' && r2.change === true);
const r3 = R.appliquerRegles([fic[0]], { chercher: '^IMG_(\\d+)$', remplacer: 'scan$1', regex: true }).lignes[0];
ok('expression régulière avec groupe', r3.nouveau === 'scan0003.JPG');
ok('expression régulière invalide signalée', !!R.appliquerRegles(fic, { chercher: '(', regex: true }).erreur);
const r4 = R.appliquerRegles([fic[1]], { date: { actif: true, source: 'fichier', format: 'aaaa-mm-jj', position: 'debut', sep: '_' } }).lignes[0];
ok('date du fichier en tête', r4.nouveau === '2026-10-01_IMG_0001.JPG');
const r5 = R.appliquerRegles([fic[1]], { date: { actif: true, source: 'jour', format: 'aaaammjj', position: 'fin', sep: '' } }, new Date(2026, 9, 22).getTime()).lignes[0];
ok('date du jour en fin, AAAAMMJJ', r5.nouveau === 'IMG_000120261022.JPG');
const r6 = R.appliquerRegles(fic, { nouveau: 'plan' }).lignes;
ok('doublons numérotés (2), (3)', egal(r6.map(x => x.nouveau), ['plan.JPG', 'plan (2).JPG', 'plan (3).JPG']) && r6[1].conflit && !r6[0].conflit);
ok('doublons insensibles à la casse', R.appliquerRegles([{ nom: 'a.txt' }, { nom: 'A.TXT' }], { casse: 'min', ext: 'min' }).lignes[1].nouveau === 'a (2).txt');
ok('caractères interdits retirés', R.nettoyer('a/b:c*?"<>|d. ') === 'abcd');
ok('nom vide → « fichier »', R.appliquerRegles([{ nom: 'x.pdf' }], { chercher: 'x' }).lignes[0].nouveau === 'fichier.pdf');
ok('fichier sans extension', R.decouper('LISEZMOI').ext === '' && R.decouper('archive.tar.gz').ext === '.gz');
ok('casse majuscules', R.appliquerRegles([{ nom: 'devis été.pdf' }], { casse: 'maj' }).lignes[0].nouveau === 'DEVIS ÉTÉ.pdf');
ok('numéro au début, pas de 10', egal(R.appliquerRegles(fic.slice(0, 2), { numero: { actif: true, position: 'debut', depart: 10, pas: 10, chiffres: 3, sep: ' ' } }).lignes.map(x => x.nouveau), ['010 IMG_0003.JPG', '020 IMG_0001.JPG']));

// ── Archives ─────────────────────────────────────────────────────────
const Z = charger('mysifa_tools_util_archives.js').MyToolsUtil_archives._interne;
ok('chemin sûr : « .. » et racine retirés', Z.cheminSur('/../../etc/passwd') === 'etc/passwd' && Z.cheminSur('C:\\Users\\..\\a.txt') === 'Users/a.txt');
ok('chemin sûr : « ./ » retiré', Z.cheminSur('./dossier//fichier.txt') === 'dossier/fichier.txt');
ok('nom seul pour l\'extraction', Z.nomSeul('a/b/../c.pdf') === 'c.pdf' && Z.nomSeul('') === 'fichier');
ok('compression stockage / forte', Z.optionsCompression('stockage').compression === 'STORE' && Z.optionsCompression('forte').compressionOptions.level === 9 && Z.optionsCompression('normale').compressionOptions.level === 6);
ok('doublons dans le zip', egal(Z.dedoublonner(['a.txt', 'A.txt', 'd/a.txt', 'a.txt']), ['a.txt', 'A (2).txt', 'd/a.txt', 'a (3).txt']));
const la = Z.lignesArchive([{ chemin: 'z.txt' }, { chemin: 'doc/', dossier: true }, { chemin: 'doc/b.txt' }, { chemin: 'a.txt' }, { chemin: 'doc/sous/c.txt' }, { chemin: '../x' }]);
ok('archive : dossiers d\'abord, puis ordre alphabétique', egal(la.map(x => x.chemin), ['doc', 'doc/sous/c.txt', 'doc/b.txt', 'a.txt', 'x', 'z.txt']));
ok('archive : profondeur', la.find(x => x.chemin === 'doc/sous/c.txt').profondeur === 2);

// ── Scanner ──────────────────────────────────────────────────────────
const K = charger('mysifa_tools_util_scanner.js').MyToolsUtil_scanner._interne;
const src = [[10, 20], [200, 30], [190, 300], [5, 280]], dst = [[0, 0], [100, 0], [100, 150], [0, 150]];
const H = K.homographie(src, dst);
ok('homographie : les quatre coins tombent juste', src.every((p, i) => { const q = K.projeter(H, p[0], p[1]); return proche(q[0], dst[i][0], 1e-6) && proche(q[1], dst[i][1], 1e-6); }));
ok('homographie dégénérée → null', K.homographie([[0, 0], [0, 0], [0, 0], [0, 0]], dst) === null);
ok('taille de sortie : moyenne des côtés', egal(K.tailleSortie([[0, 0], [100, 0], [100, 50], [0, 50]]), { w: 100, h: 50 }));
ok('taille de sortie bornée', K.tailleSortie([[0, 0], [4000, 0], [4000, 2000], [0, 2000]], 2000).w === 2000);
ok('aire d\'un quadrilatère', K.aireQuad([[0, 0], [10, 0], [10, 5], [0, 5]]) === 50);
ok('Otsu sépare deux niveaux', (() => { const g = new Uint8Array(200); g.fill(40, 0, 100); g.fill(210, 100); const t = K.otsu(g); return t >= 40 && t < 210; })());
// Feuille claire inclinée sur fond sombre : les coins détectés sont ceux de la feuille.
const W = 160, Hh = 120, gris = new Uint8Array(W * Hh).fill(50);
const feuille = [[30, 20], [130, 28], [124, 100], [24, 92]];
const dedans = (x, y) => {
  let c = false;
  for (let i = 0, j = 3; i < 4; j = i++) {
    const [xi, yi] = feuille[i], [xj, yj] = feuille[j];
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) c = !c;
  }
  return c;
};
for (let y = 0; y < Hh; y++) for (let x = 0; x < W; x++) if (dedans(x, y)) gris[y * W + x] = 225;
const det = K.detecterBords(gris, W, Hh);
ok('bords détectés sur une feuille inclinée', det.trouve === true);
ok('coins détectés à 4 px près', det.coins.every((c, i) => Math.hypot(c[0] - feuille[i][0], c[1] - feuille[i][1]) <= 4));
ok('rien de net → marges de l\'image', (() => { const u = K.detecterBords(new Uint8Array(W * Hh).fill(128), W, Hh); return u.trouve === false && proche(u.coins[0][0], 0.03 * W); })());
// Redressement : un damier carré 2×2 reste un damier.
const sw = 40, sh = 40, rgba = new Uint8ClampedArray(sw * sh * 4);
for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) { const v = ((x < 20) !== (y < 20)) ? 255 : 0, p = (y * sw + x) * 4; rgba[p] = rgba[p + 1] = rgba[p + 2] = v; rgba[p + 3] = 255; }
const out = K.redresser(rgba, sw, sh, [[0, 0], [39, 0], [39, 39], [0, 39]], 20, 20);
ok('redressement : coin haut-gauche noir, haut-droit blanc', out[0] === 0 && out[(0 * 20 + 19) * 4] === 255 && out[(19 * 20 + 0) * 4] === 255 && out[(19 * 20 + 19) * 4] === 0);
const doc = new Uint8ClampedArray(30 * 30 * 4);
for (let i = 0; i < 900; i++) { const x = i % 30, v = 120 + x * 2; doc[i * 4] = doc[i * 4 + 1] = doc[i * 4 + 2] = v; doc[i * 4 + 3] = 255; }
for (let y = 12; y < 18; y++) for (let x = 5; x < 25; x++) { const p = (y * 30 + x) * 4; doc[p] = doc[p + 1] = doc[p + 2] = 40; }
K.filtrer(doc, 30, 30, 'document');
ok('rendu document : fond inégal blanchi, texte noir', doc[(2 * 30 + 2) * 4] > 230 && doc[(2 * 30 + 27) * 4] > 230 && doc[(15 * 30 + 15) * 4] < 40);
const mA4 = K.miseEnPage(1000, 1414, 'a4');
ok('mise en page A4 portrait centrée', proche(mA4.pw, 595.28) && mA4.w <= mA4.pw && proche(mA4.x * 2 + mA4.w, mA4.pw, 1e-6));
ok('mise en page A4 paysage pour une photo large', K.miseEnPage(1414, 1000, 'a4').pw > 800);
ok('mise en page à la taille de la photo (200 dpi)', proche(K.miseEnPage(200, 400, 'image').pw, 72));

console.log(echecs ? '\n' + echecs + ' échec(s)' : '\nTout est bon.');
process.exit(echecs ? 1 : 0);
