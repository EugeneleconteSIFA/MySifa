/*
 * MyTools — éditeur PDF : « Créer avec l'IA », mise en page pure de
 * static/mysifa_tools_pdf_iacreer.js (structure -> pages d'opérations).
 *
 * Lancer : node tests/test_tools_pdf_iacreer.js
 */
const path = require("path");
global.window = global;
const S = (f) => require(path.join(__dirname, "..", "static", f));
S("mysifa_tools_pdf.js");
S("mysifa_tools_pdf_iacreer.js");
const C = global.MyToolsPDF._interne.iacreer;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) console.log("  ok     " + cas);
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
// Police fictive : 0,5 em par caractère, 0,55 en gras.
const mesure = (s, t, g) => String(s).length * t * (g ? 0.55 : 0.5);
const textes = (page) => page.filter((o) => o.t === "texte");

// Coupure des lignes
const mes10 = (s) => s.length * 5;
verifier("couper : retour à la ligne au mot", egal(C.couper("un deux trois quatre", 60, mes10), ["un deux", "trois quatre"]));
verifier("couper : mot trop long coupé", egal(C.couper("abcdefghijklmnop", 40, mes10), ["abcdefgh", "ijklmnop"]));
verifier("couper : paragraphes gardés", egal(C.couper("a\n\nb", 100, mes10), ["a", "", "b"]));

// Courrier court : une page, marges respectées, numéro de page
const courrier = { titre: "Relance facture 123", blocs: [
  { type: "adresse", elements: ["Client X", "12 rue des Lilas", "75000 Paris"] },
  { type: "paragraphe", texte: "Madame, Monsieur, ".repeat(20) },
  { type: "liste", elements: ["Facture 123 du 01/09/2026", "Échéance dépassée de 30 jours"] },
  { type: "separateur" },
  { type: "signature", texte: "Fait le 22/10/2026", elements: ["E. Leconte", "Direction"] },
] };
const p1 = C.mettreEnPage(courrier, { format: "a4", mesure });
verifier("courrier : une page A4", p1.pages.length === 1 && p1.w === 595.28 && p1.h === 841.89);
const t1 = textes(p1.pages[0]);
verifier("courrier : chaque texte a une taille numérique", p1.pages.every((p) => textes(p).every((o) => typeof o.taille === "number" && o.taille > 0)));
verifier("courrier : le long paragraphe passe à la ligne", t1.filter((o) => /^Madame/.test(o.str)).length >= 2);
verifier("courrier : numéro de page", t1.some((o) => o.str === "Page 1 / 1"));
verifier("courrier : tout le texte dans les marges",
  t1.every((o) => o.x >= 56 - 1e-6 && o.x + mesure(o.str, o.taille, o.gras) <= 595.28 - 56 + 1e-6 && o.y > 0 && o.y < 841.89));
const adr = t1.find((o) => o.str === "Client X");
verifier("courrier : adresse alignée à droite", adr.x > 595.28 / 2);
const puce = t1.filter((o) => o.str === "•");
verifier("courrier : une puce par élément de liste", puce.length === 2);
const sig = t1.find((o) => o.str === "E. Leconte"), fait = t1.find((o) => o.str === "Fait le 22/10/2026");
verifier("courrier : signature à droite, nom en gras sous la date", sig.gras && sig.x > 595.28 / 2 && sig.y > fait.y);
verifier("courrier : un trait pour le séparateur", p1.pages[0].filter((o) => o.t === "trait").length === 1);

// Long tableau : pagination, en-tête répété, rangées jamais coupées
const lignes = Array.from({ length: 160 }, (_, i) => ["EPI-" + i, "Gants de protection niveau " + (i % 5), "Atelier " + (i % 3)]);
const p2 = C.mettreEnPage({ titre: "Fiche EPI", blocs: [{ type: "tableau", colonnes: ["Réf", "Équipement", "Zone"], lignes }] }, { format: "a4", mesure });
const N = p2.pages.length;
verifier("tableau long : plusieurs pages (" + N + ")", N >= 3);
verifier("tableau long : en-tête répété sur chaque page", p2.pages.every((p) => textes(p).some((o) => o.str === "Réf" && o.gras)));
verifier("tableau long : toutes les lignes présentes, une seule fois",
  lignes.every((l) => p2.pages.reduce((n, p) => n + textes(p).filter((o) => o.str === l[0]).length, 0) === 1));
const bas = 841.89 - 56 - 14;
verifier("tableau long : aucune cellule sous la marge basse", p2.pages.every((p) => p.filter((o) => o.t === "cadre").every((o) => o.y + o.h <= bas + 1e-6)));
verifier("tableau long : numéros « Page i / N »", p2.pages.every((p, i) => textes(p).some((o) => o.str === "Page " + (i + 1) + " / " + N)));
const cad = p2.pages[0].filter((o) => o.t === "cadre"), larg = cad.slice(0, 3).reduce((s, o) => s + o.w, 0);
verifier("tableau : colonnes sur toute la largeur utile", Math.abs(larg - (595.28 - 112)) < 1e-6);
verifier("tableau : colonne au contenu plus large que la référence", cad[1].w > cad[0].w);

// Titre de section jamais seul en bas de page
const remplissage = Array.from({ length: 60 }, () => ({ type: "paragraphe", texte: "Ligne de texte." }));
const p3 = C.mettreEnPage({ titre: "", blocs: remplissage.concat([{ type: "titre", texte: "Section 2" }, { type: "paragraphe", texte: "Suite." }]) }, { format: "a4", mesure });
const pageTitre = p3.pages.findIndex((p) => textes(p).some((o) => o.str === "Section 2"));
verifier("titre : suivi de son paragraphe sur la même page", textes(p3.pages[pageTitre]).some((o) => o.str === "Suite."));

// Formats et en-tête
const p4 = C.mettreEnPage({ titre: "Note", blocs: [{ type: "paragraphe", texte: "x" }] }, { format: "a5", mesure,
  entete: { nom: "ACME", adresse: ["1 rue A", "00000 Ville"], logo: { w: 200, h: 100 } } });
verifier("A5 : dimensions", p4.w === 419.53 && p4.h === 595.28);
const img = p4.pages[0].find((o) => o.t === "image"), nom = textes(p4.pages[0]).find((o) => o.str === "ACME");
verifier("en-tête : logo puis nom de l'organisation à sa droite, en gras", img && Math.abs(img.h - 34) < 1e-9 && nom.gras && nom.x > img.x + img.w);
verifier("en-tête : titre sous le trait", textes(p4.pages[0]).find((o) => o.str === "Note").y > p4.pages[0].find((o) => o.t === "trait").y1);
verifier("paysage : A4 paysage", C.mettreEnPage({ titre: "t", blocs: [] }, { format: "a4p", mesure }).w === 841.89);
verifier("nom de fichier : sans accents ni espaces", C.nomFichier("Relance — facture n°123 été") === "relance-facture-n-123-ete" && C.nomFichier("") === "document");

console.log(ECHECS.length ? "\n" + ECHECS.length + " échec(s)" : "\nTous les cas passent.");
process.exit(ECHECS.length ? 1 : 0);
