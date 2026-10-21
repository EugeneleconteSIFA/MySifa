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
  && typeof M.adresse.etat === "function" && typeof M.adresse.aller === "function" && egal(M.adresse.cles, ["page"]));
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

if (ECHECS.length) { console.log("\n" + ECHECS.length + " échec(s)"); process.exit(1); }
console.log("\nTous les cas passent.");
