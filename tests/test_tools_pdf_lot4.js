/*
 * MyTools — éditeur PDF, lot 4 : fonctions pures des extensions navigation,
 * mesure, prépresse, formulaires avancés, contenu, lot.
 *
 * Lancer : node tests/test_tools_pdf_lot4.js
 */
const path = require("path");
global.window = global;
const S = (f) => require(path.join(__dirname, "..", "static", f));
S("mysifa_tools_pdf.js");
["texte", "formulaires", "creation", "flou", "pages", "revision", "securite", "ocr", "ia",
 "navigation", "mesure", "prepresse", "formavance", "contenu", "lot", "partage"].forEach((x) => S("mysifa_tools_pdf_" + x + ".js"));
const I = global.MyToolsPDF._interne;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) console.log("  ok     " + cas);
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const proche = (a, b, e) => Math.abs(a - b) < (e || 1e-6);

verifier("extensions du lot 4 chargées", ["navigation", "mesure", "prepresse", "formavance", "contenu", "lot"].every((k) => !!I[k]));

// Signets depuis les titres
const N = I.navigation;
const t = N.titresDepuisBlocs([
  [{ str: "Conditions générales", h: 18, y: 50 }, { str: "texte courant", h: 10, y: 80 }, { str: "encore du texte", h: 10, y: 95 }],
  [{ str: "Article 1 — Objet", h: 14, y: 60 }, { str: "texte", h: 10, y: 90 }, { str: "x", h: 30, y: 10 }]
]);
verifier("titres : deux niveaux, texte courant ignoré", egal(t.map((x) => [x.page, x.titre, x.niveau]), [[0, "Conditions générales", 0], [1, "Article 1 — Objet", 1]]));
verifier("titres : trop court écarté", !t.some((x) => x.titre === "x"));
verifier("adresse de lien", N.urlValide("https://www.exemple.fr/a?b=1") && N.urlValide("mailto:qualite@exemple.fr") && !N.urlValide("javascript:alert(1)") && !N.urlValide("www.exemple.fr"));

// Mesure
const ME = I.mesure;
verifier("longueur d'une ligne brisée", proche(ME.longueur([[0, 0], [3, 4], [3, 10]]), 11));
verifier("périmètre fermé", proche(ME.longueur([[0, 0], [10, 0], [10, 10], [0, 10]], true), 40));
verifier("aire (lacet)", proche(ME.aire([[0, 0], [10, 0], [10, 10], [0, 10]]), 100));
verifier("72 pt = 25,4 mm à l'échelle 1", proche(ME.valeurMesure("distance", [[0, 0], [72, 0]], 1), 25.4));
verifier("échelle 1:50", proche(ME.valeurMesure("distance", [[0, 0], [72, 0]], 50), 1270));
verifier("libellés", ME.libelleMesure("distance", 25.4) === "25,4 mm" && ME.libelleMesure("distance", 1270) === "1,270 m" && ME.libelleMesure("surface", 2500) === "25,00 cm²");
verifier("RVB -> CMJN", egal(ME.rvbVersCmjn(255, 0, 0), [0, 100, 100, 0]) && egal(ME.rvbVersCmjn(0, 0, 0), [0, 0, 0, 100]) && egal(ME.rvbVersCmjn(255, 255, 255), [0, 0, 0, 0]));

// Prépresse
const P = I.prepresse;
verifier("livret 8 pages", egal(P.ordreLivret(8), [[7, 0], [1, 6], [5, 2], [3, 4]]));
verifier("livret 6 pages : blancs complétés", egal(P.ordreLivret(6), [[-1, 0], [1, -1], [5, 2], [3, 4]]));
const g = P.grille(200, 100, 2, 1, 10, 4);
verifier("grille 2 colonnes", g.length === 2 && proche(g[0].w, 88) && proche(g[1].x, 102) && proche(g[0].y, 10));
const aj = P.ajuster(100, 50, 50, 50);
verifier("ajustement centré", proche(aj.k, 0.5) && proche(aj.dy, 12.5) && proche(aj.dx, 0));
const r = P.maxRepetition(300, 200, 90, 60, 5, 5);
verifier("step and repeat : poses maximales", r.nx * r.ny === 9);
verifier("couverture : noir pur 100 %, blanc 0 %", P.couverture(0, 0, 0).total === 100 && P.couverture(255, 255, 255).total === 0 && P.couverture(255, 0, 0).total === 200);
verifier("traits fins", egal(P.traitsFins("q 0.1 w 1 0 0 1 0 0 cm 2 w 0.2 w S", 0.25), [0.1, 0.2]));
verifier("opérateurs de couleur", egal(P.operateursCouleur("q 1 0 0 rg 0 0 1 RG 0 1 0 0 k f 0.5 g Q"), { rvb: 2, cmjn: 1 }));

// Formulaires avancés
const F = I.formavance;
verifier("CSV point-virgule et guillemets", egal(F.lireCsv('﻿nom;prix\r\n"Dupont; fils";"12,5"\r\n'), [["nom", "prix"], ["Dupont; fils", "12,5"]]));
verifier("CSV virgule", egal(F.lireCsv("a,b\n1,2\n"), [["a", "b"], ["1", "2"]]));
const sc = F.scripts({ format: "montant", calcul: { type: "somme", champs: "HT, Port" }, validation: { min: 0, max: 1000 } });
verifier("scripts : format, somme, plage", /AFNumber_Format/.test(sc.F) && /AFSimple_Calculate\("SUM", new Array\("HT", "Port"\)\)/.test(sc.C) && sc.V === "AFRange_Validate(true, 0, true, 1000);");
verifier("scripts : TVA", /getField\("HT"\)\.value\) \|\| 0\) \* 0\.2;/.test(F.scripts({ calcul: { type: "tva", champs: "HT", taux: 20 } }).C));
verifier("scripts : rien", egal(F.scripts({}), {}));

// Contenu : tableau, image
const C = I.contenu;
const items = [
  { x: 50, y: 700, w: 40, h: 10, str: "Réf" }, { x: 200, y: 700, w: 60, h: 10, str: "Quantité" },
  { x: 50, y: 680, w: 30, h: 10, str: "A12" }, { x: 202, y: 680, w: 25, h: 10, str: "500" },
  { x: 50, y: 660, w: 30, h: 10, str: "B7" }, { x: 84, y: 660, w: 30, h: 10, str: "bis" }, { x: 201, y: 660, w: 25, h: 10, str: "12" }
];
verifier("tableau : lignes et colonnes", egal(C.tableauDepuisItems(items), [["Réf", "Quantité"], ["A12", "500"], ["B7 bis", "12"]]));
verifier("boîte d'une image peinte", egal(C.boiteImage([100, 0, 0, 50, 10, 20]), [10, 20, 110, 70]) && egal(C.boiteImage([0, 50, -100, 0, 200, 20]), [100, 20, 200, 70]));

// Lot
const LO = I.lot;
verifier("renommage", LO.nomFichier("{nom}-{n}-{date}", "devis.pdf", 3, "22/10/2026") === "devis-3-22-10-2026.pdf" && LO.nomFichier("a/b", "x.pdf", 1) === "a-b.pdf");
verifier("étapes : inconnues retirées, défauts complétés", egal(LO.etapesValides([{ type: "inconnu" }, { type: "compression", p: { dpi: 100 } }]), [{ type: "compression", p: { dpi: 100, qualite: 70 } }]));

if (ECHECS.length) { console.log("\n" + ECHECS.length + " échec(s)"); process.exit(1); }
console.log("\nTous les cas passent.");
