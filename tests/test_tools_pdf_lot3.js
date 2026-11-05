/*
 * MyTools — éditeur PDF, lot 3 : fonctions pures des extensions
 * pages, révision, sécurité, OCR, IA (static/mysifa_tools_pdf_*.js).
 *
 * Lancer : node tests/test_tools_pdf_lot3.js
 */
const path = require("path");
global.window = global;
const S = (f) => require(path.join(__dirname, "..", "static", f));
S("mysifa_tools_pdf.js");
["texte", "formulaires", "creation", "flou", "pages", "revision", "securite", "ocr", "ia"].forEach((x) => S("mysifa_tools_pdf_" + x + ".js"));
const M = global.MyToolsPDF, I = M._interne;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) console.log("  ok     " + cas);
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const proche = (a, b, e) => Math.abs(a - b) < (e || 1e-6);
function leve(fn, motif) { try { fn(); return false; } catch (e) { return motif.test(e.message); } }

verifier("contrat : clés d'adresse page + panneau", egal(M.adresse.cles, ["page", "panneau"]));
verifier("extensions chargées", ["pages", "revision", "securite", "ocr", "ia"].every((k) => !!I[k]));

// Scinder toutes les N pages
verifier("toutes les 3 pages sur 7", egal(I.groupesParN(7, 3), [{ a: 1, b: 3 }, { a: 4, b: 6 }, { a: 7, b: 7 }]));
verifier("N invalide refusé", leve(() => I.groupesParN(5, 0), /au moins 1/));

// Pages : format, mise en page
const P = I.pages;
const a4 = P.ajusterFormat({ x: 0, y: 0, width: 612, height: 792 }, 0, "a4");
verifier("Lettre -> A4 : échelle", proche(a4.k, Math.min(595.28 / 612, 841.89 / 792)) && a4.largeur === 595.28 && a4.hauteur === 841.89);
const pay = P.ajusterFormat({ x: 0, y: 0, width: 842, height: 595 }, 0, "a4");
verifier("page paysage -> A4 paysage", pay.largeur === 841.89 && pay.hauteur === 595.28);
const piv = P.ajusterFormat({ x: 0, y: 0, width: 595, height: 842 }, 90, "a3");
verifier("page pivotée (affichée paysage) -> A3 paysage, cible dans le repère non pivoté", piv.largeur === 841.89 && piv.hauteur === 1190.55);
verifier("modèle de numérotation", P.remplirModele("Page {n} / {N} — {fichier}", { n: 2, N: 9, fichier: "devis" }) === "Page 2 / 9 — devis");
verifier("Bates : préfixe et zéros", P.numeroBates("SIFA-", 1, 6, 0) === "SIFA-000001" && P.numeroBates("", 98, 3, 3) === "101");
const pos = P.positionTexte("bas-droite", 595, 842, 24, 100, 9);
verifier("position bas-droite", pos.x === 595 - 24 - 100 && pos.y === 842 - 24);
verifier("position haut-centre", proche(P.positionTexte("haut-centre", 600, 800, 20, 100, 10).x, 250));
const o0 = P.origineTournee(100, 100, 40, 10, 0);
verifier("origine sans rotation : centrée", proche(o0.x, 80) && proche(o0.y, 105));
const o90 = P.origineTournee(100, 100, 40, 10, 90);
verifier("origine à 90° : le texte monte", proche(o90.x, 105) && proche(o90.y, 120));
verifier("pages visées : plage", P.pageVisee("2-3", 1, 5, I.lirePlages) && !P.pageVisee("2-3", 0, 5, I.lirePlages));
verifier("pages visées : sauf la première", !P.pageVisee("saufpremiere", 0, 5) && P.pageVisee("saufpremiere", 1, 5) && P.pageVisee("toutes", 0, 1));

// Révision : diff mot à mot, pixels, CSV
const R = I.revision;
const d1 = R.diffMots("le prix est de 100 euros".split(" "), "le prix est de 120 euros HT".split(" "));
verifier("diff : remplacement et ajout", egal(d1, [{ t: "=", m: ["le", "prix", "est", "de"] }, { t: "-", m: ["100"] }, { t: "+", m: ["120"] }, { t: "=", m: ["euros"] }, { t: "+", m: ["HT"] }]));
verifier("diff : identiques", egal(R.diffMots(["a", "b"], ["a", "b"]), [{ t: "=", m: ["a", "b"] }]));
verifier("diff : un côté vide", egal(R.diffMots([], ["x"]), [{ t: "+", m: ["x"] }]));
function img(W, H, f) { const d = new Uint8ClampedArray(W * H * 4); for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const v = f(x, y), i = (y * W + x) * 4; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; } return d; }
const A = img(40, 40, () => 255), B = img(40, 40, (x, y) => (x >= 5 && x < 9 && y >= 5 && y < 9) || (x >= 30 && y >= 30) ? 0 : 255);
const z = R.zonesDiff(A, B, 40, 40, 40, 4);
verifier("pixels : deux zones distinctes", z.length === 2);
verifier("pixels : zone englobante sur la grille", egal(z[0], { x: 4, y: 4, w: 8, h: 8 }));
verifier("pixels : rien de différent", R.zonesDiff(A, A, 40, 40, 40, 4).length === 0);
verifier("CSV : séparateur ; et guillemets", R.csv([["a", 'b"c'], ["x;y", "1"]]) === '﻿a;"b""c"\r\n"x;y";1');

// Sécurité : détection des données sensibles
const SE = I.securite;
verifier("IBAN valide (clé mod 97)", SE.ibanValide("FR76 3000 6000 0112 3456 7890 189") && !SE.ibanValide("FR76 3000 6000 0112 3456 7890 188"));
verifier("SIRET : Luhn", SE.luhn("73282932000074") && !SE.luhn("73282932000075"));
verifier("NIR : clé", SE.nirValide("1 85 05 78 006 084 91") && !SE.nirValide("1 85 05 78 006 084 92") && SE.nirValide("2 69 05 2A 123 456"));
const txt = "Contact : jean.dupont@exemple.fr ou 06 12 34 56 78, IBAN FR76 3000 6000 0112 3456 7890 189, SIRET 732 829 320 00074, NIR 1 85 05 78 006 084 91.";
const det = SE.detecterSensibles(txt);
verifier("détection : cinq types trouvés", egal(det.map((x) => x.type), ["email", "tel", "iban", "siret", "nir"]));
verifier("détection : valeurs exactes", det[0].valeur === "jean.dupont@exemple.fr" && det[1].valeur === "06 12 34 56 78" && txt.slice(det[3].debut, det[3].fin) === "732 829 320 00074");
verifier("détection : SIRET faux ignoré", SE.detecterSensibles("SIRET 732 829 320 00075").length === 0);
verifier("détection : téléphone international", SE.detecterSensibles("Tél. +33 6 12 34 56 78").some((x) => x.type === "tel"));
verifier("valeur masquée dans la liste", SE.masquerValeur("jean.dupont@exemple.fr").indexOf("dupont") < 0 && SE.masquerValeur("abc") === "••••");

// OCR
const O = I.ocr;
const mots = O.motsDepuisTesseract({ blocks: [{ paragraphs: [{ lines: [{ words: [
  { text: "Bonjour", confidence: 92, bbox: { x0: 30, y0: 60, x1: 150, y1: 90 } },
  { text: "bruit", confidence: 10, bbox: { x0: 0, y0: 0, x1: 3, y1: 3 } }] }] }] }] }, 3, 30);
verifier("OCR : mots en points, faible confiance écartée", egal(mots, [{ t: "Bonjour", x: 10, y: 20, w: 40, h: 10 }]));
verifier("OCR : échelle horizontale", O.echelleMot(50, 40) === 125 && O.echelleMot(10, 0) === 100 && O.echelleMot(1000, 1) === 500);

// IA
const IA = I.ia;
verifier("champ détecté -> points", egal(IA.boiteDetectee({ x: 100, y: 500, l: 300, h: 20 }, 600, 800), { x: 60, y: 400, w: 180, h: 16 }));
verifier("à traduire : texte oui, code ou nombre non", IA.aTraduire("Conditions générales") && !IA.aTraduire("12/10/2026") && !IA.aTraduire("REF-12"));
verifier("taille ajustée : réduite, bornée à 60 %", proche(IA.tailleAjustee(10, 100, 125), 8) && IA.tailleAjustee(10, 100, 500) === 6 && IA.tailleAjustee(10, 100, 90) === 10);

if (ECHECS.length) { console.log("\n" + ECHECS.length + " échec(s)"); process.exit(1); }
console.log("\nTous les cas passent.");
