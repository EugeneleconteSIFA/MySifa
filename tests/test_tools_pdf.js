/*
 * MyTools — éditeur PDF : fonctions pures de static/mysifa_tools_pdf.js.
 *
 * Le rendu et l'écriture du PDF passent par pdf.js et pdf-lib, chargés depuis
 * le CDN : ils se testent dans le navigateur. Ici, ce qui peut casser en
 * silence : la conversion des coordonnées (page pivotée), la rotation des
 * annotations, la lecture des plages « 1-3, 5 » et le réordonnancement.
 *
 * Lancer : node tests/test_tools_pdf.js
 */
const path = require("path");
global.window = global;
require(path.join(__dirname, "..", "static", "mysifa_tools_pdf.js"));
const M = global.MyToolsPDF;
const I = M._interne;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) console.log("  ok     " + cas);
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function leve(fn, motif) { try { fn(); return false; } catch (e) { return motif.test(e.message); } }

// Contrat de montage
verifier("contrat : mount, demonter, adresse", typeof M.mount === "function" && typeof M.demonter === "function"
  && typeof M.adresse.etat === "function" && typeof M.adresse.aller === "function" && egal(M.adresse.cles, ["page", "panneau"]));
verifier("adresse vide sans document", egal(M.adresse.etat(), {}));

// Coordonnées : page A4 avec une boîte décalée
const view = [10, 20, 605, 862]; // W = 595, H = 842
for (const R of [0, 90, 180, 270]) {
  const pts = [[0, 0], [100, 50], [300, 400]];
  verifier("versPdf / versVue réciproques, rotation " + R,
    pts.every(([u, v]) => { const [X, Y] = I.versPdf(view, R, u, v); const [u2, v2] = I.versVue(view, R, X, Y); return Math.abs(u - u2) < 1e-9 && Math.abs(v - v2) < 1e-9; }));
}
verifier("R=0 : coin haut-gauche affiché = (x0, y1)", egal(I.versPdf(view, 0, 0, 0), [10, 862]));
verifier("R=90 : coin haut-gauche affiché = (x0, y0)", egal(I.versPdf(view, 90, 0, 0), [10, 20]));
verifier("R=180 : coin haut-gauche affiché = (x1, y0)", egal(I.versPdf(view, 180, 0, 0), [605, 20]));
verifier("R=270 : coin haut-gauche affiché = (x1, y1)", egal(I.versPdf(view, 270, 0, 0), [605, 862]));
verifier("R=90 : coin bas-droit affiché (H, W) = (x1, y1)", egal(I.versPdf(view, 90, 842, 595), [605, 862]));

// Rotation d'une annotation avec la page
verifier("quart de tour horaire : coin haut-gauche -> haut-droit", egal(I.tournerPoint(0, 0, 595, 842, 1), [842, 0]));
verifier("quart de tour antihoraire : coin haut-gauche -> bas-gauche", egal(I.tournerPoint(0, 0, 595, 842, -1), [0, 595]));
const p0 = [123, 456], p1 = I.tournerPoint(p0[0], p0[1], 595, 842, 1);
verifier("horaire puis antihoraire = identité", egal(I.tournerPoint(p1[0], p1[1], 842, 595, -1), p0));

// Plages
verifier("plages 1-3, 5, 8-10", egal(I.lirePlages("1-3, 5, 8-10", 12), [{ a: 1, b: 3 }, { a: 5, b: 5 }, { a: 8, b: 10 }]));
verifier("plages : tiret long et point-virgule", egal(I.lirePlages("2–4;6", 6), [{ a: 2, b: 4 }, { a: 6, b: 6 }]));
verifier("plage vide refusée", leve(() => I.lirePlages("  ", 4), /Plage vide/));
verifier("plage hors document refusée", leve(() => I.lirePlages("1-9", 4), /Page 9 hors du document \(4 pages\)/));
verifier("plage à l'envers refusée", leve(() => I.lirePlages("5-3", 8), /écrire 3-5/));
verifier("texte libre refusé", leve(() => I.lirePlages("a-b", 8), /Plage invalide/));
verifier("page 0 refusée", leve(() => I.lirePlages("0-2", 8), /commence à 1/));

// Réordonnancement par glisser-déposer
const L = ["a", "b", "c", "d", "e"];
verifier("déplacer d en tête", egal(I.deplacerSelection(L, x => x === "d", 0), ["d", "a", "b", "c", "e"]));
verifier("déplacer a et c à la fin", egal(I.deplacerSelection(L, x => x === "a" || x === "c", 5), ["b", "d", "e", "a", "c"]));
verifier("déplacer b avant e", egal(I.deplacerSelection(L, x => x === "b", 4), ["a", "c", "d", "b", "e"]));
verifier("sans sélection : inchangé", egal(I.deplacerSelection(L, () => false, 2), L));

// Divers
verifier("recherche insensible aux accents", I.normaliser("Cohésion ÉTÉ") === "cohesion ete");
verifier("taille lisible", I.tailleLisible(512) === "512 o" && I.tailleLisible(2048) === "2 Ko" && I.tailleLisible(2.5 * 1048576) === "2,5 Mo");
verifier("hexRgb", egal(I.hexRgb("#ff0000"), [1, 0, 0]));
verifier("nom sans extension", I.sansExt("Rapport final.pdf") === "Rapport final" && I.sansExt("x.jpeg") === "x");
verifier("nom de fichier assaini", I.nomFichierSur('a/b:c*"d') === "a-b-c-d");
verifier("type d'image par signature", I.typeImage(new Uint8Array([0x89, 0x50, 0x4e, 0x47])) === "png"
  && I.typeImage(new Uint8Array([0xff, 0xd8, 0xff])) === "jpg" && I.typeImage(new Uint8Array([1, 2])) === null);

// ── Extensions du lot 2 (chargées dans l'ordre où la page les charge) ──
for (const f of ["mysifa_tools_pdf_texte.js", "mysifa_tools_pdf_formulaires.js", "mysifa_tools_pdf_creation.js"]) {
  require(path.join(__dirname, "..", "static", f));
}
const TX = I.texte, FO = I.formulaires, CR = I.creation;
verifier("extensions enregistrées", !!(TX && FO && CR));

// Correspondance de polices
const pol = (nom, autre) => { const r = TX.correspondancePolice(Object.assign({ nom }, autre || {})); return { famille: r.famille, gras: r.gras, italique: r.italique }; };
verifier("Arial-BoldMT -> sans gras", egal(pol("ABCDEF+Arial-BoldMT"), { famille: "sans", gras: true, italique: false }));
verifier("TimesNewRomanPS-ItalicMT -> serif italique", egal(pol("TimesNewRomanPS-ItalicMT"), { famille: "serif", gras: false, italique: true }));
verifier("CourierNewPS-BoldItalicMT -> mono gras italique", egal(pol("CourierNewPS-BoldItalicMT"), { famille: "mono", gras: true, italique: true }));
verifier("DejaVuSans -> sans (« sans » l'emporte sur « serif »)", pol("DejaVuSans").famille === "sans");
verifier("NotoSerif-Regular -> serif", pol("NotoSerif-Regular").famille === "serif");
verifier("indices pdf.js : style monospace", pol("g_d0_f3", { famille: "monospace" }).famille === "mono");
verifier("indices pdf.js : gras signalé par la police", pol("Calibri", { gras: true }).gras === true);

// Clé de police standard (fichier principal)
const cle = I.cleStandard;
verifier("clé standard sans", cle({}) === "Helvetica" && cle({ gras: true }) === "HelveticaBold" && cle({ italique: true }) === "HelveticaOblique");
verifier("clé standard serif / mono", cle({ famille: "serif", gras: true, italique: true }) === "TimesRomanBoldItalic" && cle({ famille: "mono", italique: true }) === "CourierOblique");

// Échantillonnage des couleurs
function px(n, c) { const a = []; for (let i = 0; i < n; i++) a.push(c[0], c[1], c[2], 255); return a; }
const fondBeige = [245, 235, 210], encre = [20, 40, 120];
const e1 = TX.echantillonner(px(80, fondBeige).concat(px(20, encre)), px(60, fondBeige).concat(px(3, encre)));
verifier("fond échantillonné = couleur dominante de l'anneau", e1.fond === "#f5ebd2");
verifier("texte échantillonné = pixels éloignés du fond", e1.texte === "#142878");
verifier("intérieur uni : texte noir sur fond clair", TX.echantillonner(px(10, [255, 255, 255]), px(10, [255, 255, 255])).texte === "#000000");

// Boîte d'un élément de texte pdf.js
const bi = TX.boiteItem([12, 0, 0, 12, 100, 700], 60, [0, 0, 595, 842]);
verifier("boîte d'un texte : ligne de base et taille", bi.bx === 100 && bi.by === 142 && bi.taille === 12 && bi.w === 60);
verifier("boîte d'un texte : englobe ascendantes et descendantes", bi.y < 142 - 9 && bi.y + bi.h > 142 + 2);
verifier("texte horizontal détecté", TX.estHorizontal([12, 0, 0, 12, 0, 0]) && !TX.estHorizontal([0, 12, -12, 0, 0, 0]));

// Regroupement des éléments de texte pdf.js en blocs (bug du titre coupé)
const it = (str, x, y, w, t) => ({ str, transform: [t || 16, 0, 0, t || 16, x, y], width: w });
const blocs = TX.grouperItems([
  it("DEMANDE DE SOUSCRIPTION", 60, 720, 230), it(" ", 290, 720, 4.4), it("DE COMPTE", 294.4, 720, 95),
  { str: "", transform: [1, 0, 0, 1, 0, 0], width: 0, hasEOL: true },
  it("CONDITIONS PARTICULIÈR", 60, 700, 225), it("ES", 285, 700.5, 22, 15),
  it("Page 1", 500, 700, 40, 10)
]);
verifier("blocs : trois blocs (deux lignes de titre + un texte éloigné)", blocs.length === 3);
verifier("blocs : « CONDITIONS PARTICULIÈR » + « ES » collés = un seul bloc", blocs[1].str === "CONDITIONS PARTICULIÈRES" && blocs[1].idx.length === 2);
verifier("blocs : largeur = union des éléments", blocs[1].X0 === 60 && blocs[1].X1 === 307);
verifier("blocs : l'espace séparé est conservé", blocs[0].str === "DEMANDE DE SOUSCRIPTION DE COMPTE" && Math.abs(blocs[0].X1 - 389.4) < 1e-9);
verifier("blocs : un texte loin sur la même ligne reste à part", blocs[2].str === "Page 1");
const ecarte = TX.grouperItems([it("A", 0, 100, 10, 10), it("B", 13, 100, 10, 10), it("C", 30, 100, 10, 10)]);
verifier("blocs : écart < 1,5 espace fusionné avec une espace, écart plus grand coupé", ecarte.length === 2 && ecarte[0].str === "A B" && ecarte[1].str === "C");
verifier("blocs : lignes de base différentes séparées", TX.grouperItems([it("A", 0, 100, 10, 10), it("B", 10, 96, 10, 10)]).length === 2);
const bb = TX.boiteBloc(blocs[1], [0, 0, 595, 842]);
verifier("boîte d'un bloc : toute la largeur", bb.x === 60 && bb.w === 247 && bb.largeur === 247);
const esp = TX.grouperItems([it("L E T T R E S", 60, 700, 90, 12), it("E S P A C E E S", 154, 700, 100, 12)]);
verifier("blocs : lettres espacées par pdf.js recollées, espace entre les mots gardée", esp.length === 1 && esp[0].str === "LETTRES ESPACEES");
verifier("espacement : police plus étroite -> espacement positif", Math.abs(TX.espacement(120, 100, 10, 16) - 2) < 1e-9);
verifier("espacement : borné", TX.espacement(400, 100, 10, 16) === 0.6 * 16 && TX.espacement(10, 100, 10, 16) === -1.6);
verifier("espacement : écart négligeable -> 0", TX.espacement(100.05, 100, 10, 16) === 0);

// Mesure de la boîte sur l'encre réelle (titre Hello bank coupé à « …DE COM »)
function matrice(W, H, fond, encres) {
  const d = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4, e = encres.some(([x0, x1, y0, y1]) => x >= x0 && x < x1 && y >= y0 && y < y1);
    const c = e ? [255, 255, 255] : fond; d[i] = c[0]; d[i + 1] = c[1]; d[i + 2] = c[2]; d[i + 3] = 255;
  }
  return d;
}
// Fond cyan (non blanc), texte blanc : mot 1 (5-14), espace de 3 px, mot 2 (17-27), grand écart, numéro (45-50).
const cyan = [0, 160, 200];
const mx = matrice(60, 20, cyan, [[5, 14, 8, 15], [17, 27, 8, 15], [45, 50, 8, 15], [20, 22, 6, 8]]);
const declaree = { x: 5, y: 6, w: 10, h: 11, base: 15, taille: 10 };
const me = TX.mesurerEncre(mx, 60, 20, declaree, {});
verifier("encre : fond coloré reconnu", egal(me.fond, cyan));
verifier("encre : l'espace entre mots est franchi (la boîte va jusqu'au bout du 2e mot)", me.x === 5 && me.x + me.w === 27);
verifier("encre : arrêt au grand écart (le numéro voisin n'est pas pris)", me.x + me.w < 45);
verifier("encre : hauteur de capitale = sommet médian, accent ignoré", me.cap === 7);
verifier("encre : le haut suit l'accent", me.y === 6);
const borne = TX.mesurerEncre(mx, 60, 20, declaree, { droite: 16 });
verifier("encre : borne du bloc voisin respectée", borne.x + borne.w <= 16);
const jamaisMoins = TX.mesurerEncre(matrice(60, 20, cyan, []), 60, 20, declaree, {});
const deuxLignes = matrice(60, 40, cyan, [[5, 30, 8, 15], [5, 30, 18, 20], [5, 30, 21, 28]]);
const l1 = TX.mesurerEncre(deuxLignes, 60, 40, { x: 5, y: 6, w: 25, h: 11, base: 15, taille: 10 }, {});
verifier("encre : l'accent de la ligne du dessous n'agrandit pas la boîte", l1.y + l1.h <= 18);
verifier("encre : jamais plus étroite que la boîte déclarée", jamaisMoins.x === 5 && jamaisMoins.w === 10 && jamaisMoins.h > 0);
// Logo collé sous la ligne (1 px de fond entre les deux) : la boîte s'arrête à la ligne.
const logo = matrice(60, 40, cyan, [[5, 30, 8, 15], [3, 35, 16, 30]].map(([a, b, c, d], i) => i ? [a, b, c + 1, d] : [a, b, c, d]));
const sansLogo = TX.mesurerEncre(logo, 60, 40, { x: 5, y: 6, w: 25, h: 11, base: 15, taille: 10 }, {});
verifier("encre : un logo sous la ligne, séparé par un liseré, n'est pas recouvert", sansLogo.y + sansLogo.h <= 17);
// Jambage : encre continue sous la ligne de base, prise en entier.
const jamb = matrice(60, 40, cyan, [[5, 30, 8, 15], [10, 12, 15, 18]]);
const avecJ = TX.mesurerEncre(jamb, 60, 40, { x: 5, y: 6, w: 25, h: 11, base: 15, taille: 10 }, {});
verifier("encre : le jambage collé à la lettre est couvert", avecJ.y + avecJ.h >= 18);
const gauche = TX.mesurerEncre(mx, 60, 20, { x: 18, y: 6, w: 9, h: 11, base: 15, taille: 10 }, {});
verifier("encre : extension vers la gauche aussi", gauche.x === 5);
const traits = matrice(40, 20, [255, 255, 255], []);
for (const [x0, x1] of [[2, 6], [10, 14], [20, 24]]) for (let y = 4; y < 16; y++) for (let x = x0; x < x1; x++) { const i = (y * 40 + x) * 4; traits[i] = traits[i + 1] = traits[i + 2] = 0; }
verifier("épaisseur : traits de 4 px sur une capitale de 12 px = 0,33", Math.abs(TX.epaisseurTraits(traits, 40, { x: 0, w: 40 }, 16, 12, [255, 255, 255]) - 4 / 12) < 1e-9);
const vois = TX.bornesVoisins([{ X0: 60, X1: 200, Y: 700, h: 16 }, { X0: 400, X1: 430, Y: 700, h: 10 }, { X0: 60, X1: 300, Y: 680, h: 16 }]);
verifier("bornes : voisin de droite sur la même ligne, pas celui de la ligne d'en dessous", egal(vois[0], [null, 400]) && egal(vois[1], [200, null]) && egal(vois[2], [null, null]));
verifier("police : « Gotham-Black » = gras, graisse connue", TX.correspondancePolice({ nom: "ABCDEF+Gotham-Black" }).gras === true && TX.correspondancePolice({ nom: "Gotham-Black" }).graisseConnue);
verifier("police : « Brandon-Medium » = normal, graisse connue", TX.correspondancePolice({ nom: "Brandon-Medium" }).gras === false && TX.correspondancePolice({ nom: "Brandon-Medium" }).graisseConnue);
verifier("police : nom sans graisse = à mesurer", TX.correspondancePolice({ nom: "HelloTitre" }).graisseConnue === false);

// Champs de formulaire
verifier("nom unique : premier libre", FO.nomUnique("Champ", ["Champ 1", "Champ 2", "client"]) === "Champ 3");
verifier("nom unique : liste vide", FO.nomUnique("Champ", []) === "Champ 1");
const bc = FO.boiteChamp([60, 600, 260, 624], [0, 0, 595, 842], 0, I.versVue);
verifier("rectangle PDF -> boîte affichée", egal(bc, { x: 60, y: 218, w: 200, h: 24 }));
const bc90 = FO.boiteChamp([60, 600, 260, 624], [0, 0, 595, 842], 90, I.versVue);
verifier("rectangle PDF -> boîte, page pivotée (largeur et hauteur échangées)", bc90.w === 24 && bc90.h === 200);
const P0 = (u, v) => I.versPdf([0, 0, 595, 842], 0, u, v);
verifier("boîte affichée -> rectangle pdf-lib (aller-retour)", egal(FO.rectPdf(bc, P0), { x: 60, y: 600, width: 200, height: 24 }));
verifier("genre de widget", FO.genreWidget({ fieldType: "Tx", multiLine: true }) === "multi" && FO.genreWidget({ fieldType: "Btn", checkBox: true }) === "case"
  && FO.genreWidget({ fieldType: "Btn", radioButton: true }) === "radio" && FO.genreWidget({ fieldType: "Ch", combo: true }) === "liste"
  && FO.genreWidget({ fieldType: "Btn", pushButton: true }) === null);

verifier("radio : état pdf-lib « 1 » -> libellé de l'option", FO.optionRadio({ options: ["camion", "retrait"] }, "1") === "retrait"
  && FO.optionRadio({ options: ["camion", "retrait"] }, "camion") === "camion" && FO.optionRadio(null, "Oui") === "Oui");

// Bloc de texte : retour à la ligne (mesure : 1 point par caractère)
const m1 = s => s.length;
verifier("couper : mots entiers", egal(CR.couperLignes("un deux trois quatre", 9, m1), ["un deux", "trois", "quatre"]));
verifier("couper : retours à la ligne conservés", egal(CR.couperLignes("a\n\nb", 10, m1), ["a", "", "b"]));
verifier("couper : mot trop long coupé", egal(CR.couperLignes("abcdefghij", 4, m1), ["abcd", "efgh", "ij"]));
verifier("couper : texte vide = une ligne vide", egal(CR.couperLignes("", 10, m1), [""]));

// Tableau
const tab = { x: 10, y: 20, w: 300, cols: [1, 1, 1], cells: [["A", "B", "C"], ["un texte assez long", "", ""]], entete: true, taille: 10, pad: 4 };
const G = CR.geometrieTableau(tab, (s) => s.length * 5);
verifier("tableau : bords de colonnes", egal(G.xs, [10, 110, 210, 310]));
verifier("tableau : la ligne longue passe sur deux lignes", G.lignes[1][0].length === 2 && G.ys.length === 3 && (G.ys[2] - G.ys[1]) > (G.ys[1] - G.ys[0]));
verifier("tableau : retailler sans perdre le contenu", egal(CR.retaillerCellules([["a", "b"], ["c", "d"]], 3, 1), [["a"], ["c"], [""]]));
verifier("tableau : colonnes renormalisées", Math.abs(CR.retaillerColonnes([0.5, 0.5], 3).reduce((s, x) => s + x, 0) - 1) < 1e-9);
const nb = CR.deplacerBord({ x: 0, w: 300, cols: [1, 1, 1] }, 1, 150, 12);
verifier("tableau : déplacer un bord élargit la colonne de gauche", Math.abs(nb[0] * 300 - 150) < 1e-9 && Math.abs(nb[1] * 300 - 50) < 1e-9 && Math.abs(nb[2] * 300 - 100) < 1e-9);
verifier("tableau : bord borné par la largeur minimale", Math.abs(CR.deplacerBord({ x: 0, w: 300, cols: [1, 1, 1] }, 1, 500, 12)[1] * 300 - 12) < 1e-9);

// Formats
verifier("format A4", egal(CR.dimensionsFormat("a4"), [595.28, 841.89]));
verifier("format personnalisé en mm", Math.abs(CR.dimensionsFormat("perso", 100, 50)[0] - 283.46) < 0.01);
verifier("format personnalisé hors bornes refusé", leve(() => CR.dimensionsFormat("perso", 5, 50), /entre 20 et 2000 mm/));

// ── Floutage ──
require(path.join(__dirname, "..", "static", "mysifa_tools_pdf_flou.js"));
const FL = I.flou;
verifier("extension floutage enregistrée", !!FL);
verifier("zone -> pixels (200 dpi)", egal(FL.zonePixels({ x: 72, y: 36, w: 36, h: 18 }, 200 / 72, 2000, 2000), { x: 200, y: 100, w: 100, h: 50 }));
verifier("zone -> pixels bornée au bord de l'image", egal(FL.zonePixels({ x: -10, y: 90, w: 30, h: 50 }, 1, 100, 100), { x: 0, y: 90, w: 20, h: 10 }));
verifier("zone hors image -> null", FL.zonePixels({ x: 200, y: 0, w: 10, h: 10 }, 1, 100, 100) === null);
function img(W, H, f) { const d = new Uint8ClampedArray(W * H * 4); for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const v = f(x, y), i = (y * W + x) * 4; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; } return d; }
const dam = img(4, 4, (x, y) => (x + y) % 2 ? 255 : 0);
FL.pixeliser(dam, 4, 4, { x: 0, y: 0, w: 4, h: 2 }, 2);
verifier("pixeliser : un bloc 2x2 de damier devient gris moyen", dam[0] === 128 && dam[4] === 128 && dam[(1 * 4 + 1) * 4] === 128);
verifier("pixeliser : rien hors de la zone", dam[(2 * 4 + 0) * 4] === 0 && dam[(2 * 4 + 1) * 4] === 255);
const raies = img(20, 20, (x) => x % 2 ? 255 : 0);
FL.flouter(raies, 20, 20, { x: 5, y: 5, w: 10, h: 10 }, 2, 3);
let ecart = 0; for (let y = 5; y < 15; y++) for (let x = 5; x < 15; x++) ecart = Math.max(ecart, Math.abs(raies[(y * 20 + x) * 4] - 127.5));
verifier("flouter : des raies d'un pixel deviennent un gris uniforme", ecart < 20);
verifier("flouter : rien hors de la zone", raies[(0 * 20 + 1) * 4] === 255 && raies[(0 * 20 + 0) * 4] === 0);
const blanc = img(4, 4, () => 255); FL.masquer(blanc, 4, 4, { x: 1, y: 1, w: 2, h: 2 }, [0, 0, 0]);
verifier("masquer : aplat noir dans la zone seulement", blanc[(1 * 4 + 1) * 4] === 0 && blanc[0] === 255);
const vue = [0, 0, 595, 842];
const bt = FL.boiteTexte([10, 0, 0, 10, 100, 700], 100, 0, 10, 10, vue, 0, I.versVue);
verifier("boîte d'un texte entier (page à l'endroit)", bt.x === 99 && bt.w === 102 && bt.y < 142 - 9 && bt.y + bt.h > 142);
const bp = FL.boiteTexte([10, 0, 0, 10, 100, 700], 100, 5, 5, 10, vue, 0, I.versVue);
verifier("boîte d'une partie du texte (occurrence)", Math.abs(bp.x - 149) < 1e-9 && Math.abs(bp.w - 52) < 1e-9);
const b90 = FL.boiteTexte([10, 0, 0, 10, 100, 700], 100, 0, 10, 10, vue, 90, I.versVue);
verifier("boîte d'un texte sur page pivotée : largeur et hauteur échangées", Math.abs(b90.h - 102) < 1e-9 && b90.w < 20 && Math.abs(b90.y - 99) < 1e-9);

if (ECHECS.length) { console.log("\n" + ECHECS.length + " échec(s)"); process.exit(1); }
console.log("\nTous les cas passent.");
