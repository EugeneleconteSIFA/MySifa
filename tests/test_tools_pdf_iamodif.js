/*
 * MyTools — éditeur PDF : « Modifier avec l'IA », fonctions pures de
 * static/mysifa_tools_pdf_ia.js (validation des opérations rendues par l'IA,
 * application d'un lot coché, différence mot à mot, envoi borné).
 *
 * Lancer : node tests/test_tools_pdf_iamodif.js
 */
const path = require("path");
global.window = global;
const S = (f) => require(path.join(__dirname, "..", "static", f));
S("mysifa_tools_pdf.js");
S("mysifa_tools_pdf_ia.js");
const MD = global.MyToolsPDF._interne.ia.modif;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) console.log("  ok     " + cas);
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const textes = {
  "1.0": "Date : 12/10/2026",
  "1.4": "Téléphone : 01 02 03 04 05",
  "2.3": "Échéance le 12/10/2026, relance le 12/10/2026",
  "2.7": "Dossier 93257242464",
};
const op = (o) => Object.assign({ type: "remplacer", id: "1.0", ancien: "", nouveau: "", position: "dessous", motif: "" }, o);

// Identifiants et portée
verifier("id de bloc : page à partir de 1", MD.idBloc(0, 17) === "1.17" && MD.idBloc(4, 0) === "5.0");
verifier("zone : bloc dedans", MD.dansZone({ x: 60, y: 100 }, { x: 50, y: 80, w: 200, h: 30 }));
verifier("zone : bloc hors zone", !MD.dansZone({ x: 60, y: 140 }, { x: 50, y: 80, w: 200, h: 30 }) && !MD.dansZone({ x: 300, y: 100 }, { x: 50, y: 80, w: 200, h: 30 }));

// Envoi : texte et position seulement, bornes
const env = MD.blocsPourIa([{ id: "1.0", page: 0, texte: "Date", x: 60.4, y: 99.6, police: "secret" }, { id: "1.1", page: 0, texte: "   ", x: 0, y: 0 }]);
verifier("envoi : page à partir de 1, positions arrondies, blocs vides retirés",
  egal(env.blocs, [{ id: "1.0", page: 1, texte: "Date", x: 60, y: 100 }]) && !env.trop);
const gros = MD.blocsPourIa(Array.from({ length: 40 }, (_, i) => ({ id: "1." + i, page: 0, texte: "x".repeat(2000), x: 0, y: 0 })));
verifier("envoi : document trop long signalé (> " + MD.MAX_CARACTERES + " caractères)", gros.trop);

// Validation des ids et du texte
const v = MD.validerOps([
  op({ ancien: "12/10", nouveau: "14/11" }),
  op({ id: "9.9", ancien: "12/10", nouveau: "14/11" }),
  op({ id: "1.4", ancien: "absent", nouveau: "x" }),
  op({ id: "1.0", ancien: "12/10", nouveau: "12/10" }),
  op({ type: "detruire", id: "1.0" }),
  op({ type: "masquer", id: "1.4", nouveau: "ignoré" }),
  op({ type: "inserer", id: "2.7", nouveau: "  " }),
  op({ type: "inserer", id: "2.7", nouveau: " Visa ", position: "droite" }),
  op({ ancien: "12/10", nouveau: "14/11" }),
  null,
], textes);
verifier("validation : id inexistant, texte absent, sans changement, type inconnu, insertion vide, null écartés", v.ecartees === 6);
verifier("validation : doublon retiré, ordre gardé",
  egal(v.valides.map((o) => o.type + ":" + o.id), ["remplacer:1.0", "masquer:1.4", "inserer:2.7"]));
verifier("validation : masquer = tout le bloc vers rien", v.valides[1].ancien === textes["1.4"] && v.valides[1].nouveau === "");
verifier("validation : insertion nettoyée, position gardée", v.valides[2].nouveau === "Visa" && v.valides[2].position === "droite");
verifier("validation : liste absente = rien", egal(MD.validerOps(undefined, textes), { valides: [], ecartees: 0 }));

// Aperçu d'une proposition
verifier("aperçu : toutes les occurrences du bloc", MD.apres(op({ id: "2.3", ancien: "12/10", nouveau: "14/11" }), textes["2.3"]) === "Échéance le 14/11/2026, relance le 14/11/2026");
verifier("aperçu : masquer = vide", MD.apres({ type: "masquer" }, "x") === "");

// Lot coché
const lot = MD.planLot([
  op({ ancien: "12/10", nouveau: "14/11" }),
  op({ ancien: "2026", nouveau: "2027" }),
  op({ id: "2.7", ancien: "93257242464", nouveau: "93257240000" }),
  { type: "masquer", id: "1.4", ancien: textes["1.4"], nouveau: "" },
  op({ id: "1.4", ancien: "01", nouveau: "09" }),
  { type: "inserer", id: "2.7", nouveau: "Visa", position: "droite" },
  op({ id: "8.8", ancien: "a", nouveau: "b" }),
], textes);
verifier("lot : remplacements d'un même bloc enchaînés", lot.blocs["1.0"] === "Date : 14/11/2027");
verifier("lot : numéro de dossier remplacé", lot.blocs["2.7"] === "Dossier 93257240000");
verifier("lot : bloc masqué = texte vide, remplacement suivant sans effet", lot.blocs["1.4"] === "" && lot.sansEffet === 2);
verifier("lot : insertion à part", egal(lot.insertions, [{ id: "2.7", texte: "Visa", position: "droite" }]));
verifier("lot : bloc non coché intact", !("2.3" in lot.blocs));
const aller = MD.planLot([op({ ancien: "12/10", nouveau: "X" }), op({ ancien: "X", nouveau: "12/10" })], textes);
verifier("lot : aller-retour sans changement = rien à poser", egal(aller.blocs, {}));
const perime = MD.planLot([op({ ancien: "12/10", nouveau: "14/11" })], { "1.0": "Date : 01/01/2026" });
verifier("lot : texte changé depuis la proposition = sans effet", egal(perime.blocs, {}) && perime.sansEffet === 1);

// Différence mot à mot
const d = MD.diffMots("Date : 12/10/2026", "Date : 14/11/2026");
verifier("diff : seul le mot changé est marqué", egal(d, [["=", "Date : "], ["-", "12/10/2026"], ["+", "14/11/2026"]]));
verifier("diff : ajout pur", egal(MD.diffMots("", "Visa"), [["+", "Visa"]]));
verifier("diff : suppression d'un mot", egal(MD.diffMots("mets le client", "mets client"), [["=", "mets "], ["-", "le "], ["=", "client"]]));
const recompose = (dd, garder) => dd.filter((x) => x[0] === "=" || x[0] === garder).map((x) => x[1]).join("");
const a0 = "Corige les faute de la page deux", b0 = "Corrige les fautes de la page 2";
verifier("diff : avant et après se recomposent", recompose(MD.diffMots(a0, b0), "-") === a0 && recompose(MD.diffMots(a0, b0), "+") === b0);

// Place libre des insertions : page 200 × 100 pt, police fictive (0,5 em par caractère).
const mes = (txt) => (t) => ({ w: txt.length * 0.5 * t, h: 1.2 * t });
const ligne = { x: 10, y: 20, w: 60, h: 12 };
const placer = (g, txt, pos, lg) => MD.placerInsertion({ ligne: lg || ligne, taille: 10, mesure: mes(txt), position: pos || "dessous", grille: g });
const g1 = MD.grilleVide(200, 100); MD.marquer(g1, ligne);
const p1 = placer(g1, "Visa");
verifier("place : dessous quand l'espace jusqu'à la ligne suivante suffit", p1.mode === "dessous" && !p1.chevauche && p1.y >= 32 && p1.x === 10 && p1.taille === 10);
const g2 = MD.grilleVide(200, 100); MD.marquer(g2, ligne); MD.marquer(g2, { x: 10, y: 36, w: 180, h: 12 });
const p2 = placer(g2, "Visa");
verifier("place : ligne serrée dessous -> à droite dans la marge", p2.mode === "droite" && !p2.chevauche && p2.x > 70 && p2.taille === 10);
// Pas de marge à droite (texte trop long), dessous serré : réduction jusqu'à 80 %.
const g3 = MD.grilleVide(200, 100); MD.marquer(g3, ligne); MD.marquer(g3, { x: 10, y: 45.6, w: 180, h: 12 }); MD.marquer(g3, { x: 10, y: 0, w: 180, h: 19 });
const p3 = placer(g3, "Visa du responsable de production");
verifier("place : pas de marge -> taille réduite (80 % au plus bas)", p3.mode === "reduit" && !p3.chevauche && p3.taille < 10 && p3.taille >= 8);
// Colonne : dessous et droite pris, la place suivante libre plus bas.
const g4 = MD.grilleVide(200, 100); MD.marquer(g4, ligne); MD.marquer(g4, { x: 10, y: 34, w: 180, h: 20 }); MD.marquer(g4, { x: 72, y: 0, w: 128, h: 34 }); MD.marquer(g4, { x: 0, y: 0, w: 200, h: 19 });
const p4 = placer(g4, "Visa");
verifier("place : sinon l'espace libre le plus proche dans la colonne", p4.mode === "colonne" && !p4.chevauche && p4.y > 54 && p4.x === 10);
// Rien ne tient : position demandée, marquée, dans la page.
const g5 = MD.grilleVide(200, 100); MD.marquer(g5, { x: 0, y: 0, w: 200, h: 100 });
const p5 = placer(g5, "Visa", "dessous", { x: 10, y: 80, w: 60, h: 12 });
verifier("place : rien ne tient -> chevauche, position demandée gardée dans la page", p5.chevauche && p5.mode === "dessous" && p5.y + p5.h <= 100 && p5.y >= 0);
// Deux insertions sur la même ligne : la seconde évite la première.
const g6 = MD.grilleVide(200, 100); MD.marquer(g6, ligne);
const a6 = placer(g6, "Visa"); MD.reserver(g6, a6);
const b6 = placer(g6, "Cachet");
const croisent = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
verifier("place : deux insertions voisines ne se chevauchent pas", !b6.chevauche && !croisent(a6, b6));
const g7 = MD.grilleVide(200, 100);
const p7 = placer(g7, "Signature et cachet", "droite", { x: 120, y: 20, w: 60, h: 12 });
verifier("place : jamais hors de la page (droite impossible, dessous réduit)", p7.x + p7.w <= 200 && p7.mode === "reduit" && !p7.chevauche);
// À droite, ligne de base commune : un aplat collé sous la ligne de base ne bloque pas.
const g8 = MD.grilleVide(200, 100); const l8 = { x: 10, y: 20, w: 60, h: 12, base: 30 };
MD.marquer(g8, l8); MD.marquer(g8, { x: 10, y: 30, w: 190, h: 20 });
const p8 = placer(g8, "Visa", "dessous", l8);
verifier("place : à droite sur la ligne de base malgré un aplat juste dessous", p8.mode === "droite" && Math.abs(p8.y + 0.78 * 10 - 30) < 1e-9);
// Grille d'encre : pixel non blanc -> case occupée (2 px par point).
const px = new Uint8ClampedArray(8 * 4 * 4).fill(255); const i0 = (2 * 8 + 5) * 4; px[i0] = px[i0 + 1] = px[i0 + 2] = 0;
const ge = MD.grilleEncre(px, 8, 4, 2, 4, 2);
verifier("grille d'encre : seule la case du pixel encré est prise", ge.cases[1 * 4 + 2] === 1 && ge.cases.reduce((s, v) => s + v, 0) === 1);
verifier("libre : la ligne de référence ignorée", MD.estLibre(g1, { x: 10, y: 25, w: 5, h: 5 }, { rect: ligne }) && !MD.estLibre(g1, { x: 10, y: 25, w: 5, h: 5 }));

console.log(ECHECS.length ? "\n" + ECHECS.length + " échec(s)" : "\nTous les cas passent.");
process.exit(ECHECS.length ? 1 : 0);
