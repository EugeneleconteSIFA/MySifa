// MyTools › Calculs bobine — formules (static/mysifa_tools_calculs.js).
// Lancer : node tests/test_tools_calculs.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'mysifa_tools_calculs.js'), 'utf8');
const ctx = { window: {}, document: {}, localStorage: { getItem() { return null; }, setItem() {} } };
vm.createContext(ctx);
vm.runInContext(src, ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'static', 'mysifa_tools_calculs_schemas.js'), 'utf8'), ctx);
const F = ctx.window.MyToolsCalculs._interne;
const SCH = ctx.window.MyToolsCalculsSchemas;
const G = SCH._geo;

let echecs = 0;
function ok(nom, v) { if (v) console.log('ok  ', nom); else { echecs++; console.log('ECHEC', nom); } }
const proche = (a, b, tol) => Math.abs(a - b) <= (tol || 0.5);

// Métrage : même formule que le widget de MyStock (mtrCalcul).
const m = F.metrage(145, 96, 1000);
ok('métrage 145 µm, Ø96 → Ø1000 ≈ 5 367 m', proche(m.metres, Math.PI * (500 * 500 - 48 * 48) / 145, 0.001) && proche(m.metres, 5367, 1));
ok('métrage : bobine plus petite que le mandrin refusée', !!F.metrage(145, 96, 90).erreur);
ok('métrage : saisie incomplète', F.metrage('', 96, 1000).vide === true);
ok('métrage : virgule décimale acceptée', proche(F.metrage('145,0', '96', '1000').metres, m.metres, 0.001));

// Diamètre : l'inverse exact du métrage.
const d = F.diametre(145, 96, m.metres);
ok('diamètre inverse du métrage', proche(d.mm, 1000, 0.001));
ok('diamètre d\'un métrage nul : vide', F.diametre(145, 96, 0).vide === true);

// Fronts : relevé de l'outil 2796 (of-fiches-techniques.md) — 104,5 mm,
// espace latéral 3,25, module 107,75, 4 fronts sur une bobine de 440.
const f = F.fronts(440, 104.5, 3.25, 0);
ok('outil 2796 : 4 fronts sur 440', f.nb === 4);
ok('outil 2796 : module 107,75', proche(f.module, 107.75, 1e-9));
ok('outil 2796 : laize utilisée 431, chute 9', proche(f.utilisee, 431, 1e-9) && proche(f.chute, 9, 1e-9));
ok('fronts : la rive réduit la laize utile', F.fronts(440, 104.5, 3.25, 4).nb === 4 && F.fronts(440, 104.5, 3.25, 5).nb === 3);
ok('fronts : laize exactement remplie', F.fronts(431, 104.5, 3.25, 0).nb === 4);
ok('fronts : étiquette plus large que la laize', !!F.fronts(100, 104.5, 3.25, 0).erreur);
ok('laize minimale pour 4 fronts = 431', proche(F.laizeMini(4, 104.5, 3.25, 0), 431, 1e-9));

// Étiquettes par bobine et quantité visée : métrage = qté ÷ fronts × module ÷ 1000.
const e = F.etiquettes(2000, 148.4, 4, 4);
ok('2 000 m, module 152,4 → 13 123 par front', e.parFront === 13123);
ok('4 fronts → 52 492 étiquettes', e.total === 52492);
ok('quantité visée 10 000 sur 4 fronts → 381 m', proche(F.metragePour(10000, 148.4, 4, 4), 381, 1e-9));
ok('aller-retour : le métrage calculé porte la quantité', F.etiquettes(F.metragePour(10000, 148.4, 4, 4), 148.4, 4, 4).total >= 10000);

// Carton : rangement en grille, debout ou couché, jeu retiré.
const sens = { debout: true, couche: true };
const c385 = { l: 385, w: 385, h: 208, libelle: 'Carton 385 x 385 x 208 mm' };
const r1 = F.rangement(90, 100, c385, 4, sens);
ok('Ø90 × 100 dans 385×385×208 : 4×4×2 debout = 32', r1.nb === 32 && r1.sens === 'debout' && r1.a === 4 && r1.c === 2);
const r2 = F.rangement(90, 100, c385, 4, { debout: false, couche: true });
ok('couchées seulement : 3×4×2 = 24', r2.nb === 24 && r2.sens === 'couchées');
ok('bobine trop grosse : aucun rangement', F.rangement(400, 100, c385, 4, sens) === null);
ok('le jeu compte : Ø96 × 4 = 384 > 381', F.rangement(96, 100, c385, 4, sens).a === 3);
const cartons = [c385, { l: 385, w: 385, h: 105, libelle: '105' }, { l: 200, w: 200, h: 115, libelle: 'petit' }];
const cl = F.classerCartons(cartons, 90, 100, 40, 4, sens);
// 3 × 385×385×105 (46,7 dm³) contiennent 40 bobines avec moins de vide que 2 × 385×385×208 (61,7 dm³).
ok('40 bobines : moins de vide, et à volume proche le moins de cartons', cl[0].carton.libelle === '105' && cl[0].nbCartons === 3);
ok('dix petits cartons après trois moyens (2 % de vide en moins seulement)', cl.findIndex(x => x.carton.libelle === 'petit') > 0);
const parNb = F.classerCartons(cartons, 90, 100, 40, 4, sens, 'cartons');
ok('priorité « moins de cartons » : 2 cartons de 32', parNb[0].carton.libelle === 'Carton 385 x 385 x 208 mm' && parNb[0].nbCartons === 2);
const avecBox = F.classerCartons(cartons.concat([{ l: 1180, w: 780, h: 1070, libelle: 'grand box' }]), 90, 100, 40, 4, sens);
ok('un grand box presque vide passe en dernier', avecBox[avecBox.length - 1].carton.libelle === 'grand box');
const sansQ = F.classerCartons(cartons, 90, 100, 0, 4, sens);
ok('sans quantité : meilleur remplissage d\'abord', sansQ[0].remplissage >= sansQ[1].remplissage);
ok('carton trop petit écarté', !cl.some(x => x.carton.libelle === 'petit' && x.parCarton < 1));

ok('rangement : axe du rangement retenu (v, l ou w)', r1.axe === 'v' && ['l', 'w'].includes(r2.axe));

// Épaisseur d'une matière composée : frontal + adhésif + glassine.
const ec = F.epaisseurCouches([{ libelle: 'Frontal', microns: 72 }, { libelle: 'Adhésif', microns: '20,5' }, { libelle: 'Glassine', microns: 52 }]);
ok('couches : 72 + 20,5 + 52 = 144,5 µm', proche(ec.total, 144.5, 1e-9) && ec.complet && ec.nb === 3);
const ei = F.epaisseurCouches([{ libelle: 'Frontal', microns: 72 }, { libelle: 'Adhésif', microns: '' }]);
ok('couches : épaisseur manquante signalée, pas devinée', !ei.complet && ei.total === 72 && ei.manquantes.length === 1 && ei.manquantes[0] === 'Adhésif');
ok('couches : aucune couche choisie → null', F.epaisseurCouches([]) === null && F.epaisseurCouches(null) === null);

// Schémas : géométrie à l'échelle.
const gb = G.geoBobine(76, 1000, 145, 120);
ok('bobine : mandrin à l\'échelle (76/1000 du rayon)', proche(gb.r, 120 * 76 / 1000, 1e-9) && proche(gb.enroule, 462, 1e-9));
ok('bobine : tours = enroulé ÷ épaisseur', proche(gb.tours, 462 * 1000 / 145, 1e-6));
ok('bobine : Ø inférieur au mandrin → pas de schéma', G.geoBobine(76, 70, 145, 120) === null);
const gf = G.geoFronts(440, 104.5, 3.25, 0, 4);
ok('fronts : 4 étiquettes centrées, chute 4,5 par bord', gf.etiquettes.length === 4 && proche(gf.chuteCote, 4.5, 1e-9));
ok('fronts : première étiquette après chute + demi-espace', proche(gf.etiquettes[0].x, 4.5 + 1.625, 1e-9));
ok('fronts : symétrie (même marge à droite)', proche(440 - (gf.etiquettes[3].x + 104.5), gf.etiquettes[0].x, 1e-9));
ok('fronts : pas entre deux étiquettes = module', proche(gf.etiquettes[1].x - gf.etiquettes[0].x, 107.75, 1e-9));
const gd = G.geoBande(148.4, 4, 4);
ok('bande : pas 152,4, 6,56 / m par front, 26,25 / m en tout', proche(gd.pas, 152.4, 1e-9) && proche(gd.parMetre, 1000 / 152.4, 1e-9) && proche(gd.parMetreTotal, 4000 / 152.4, 1e-9));
const gc = G.geoCarton(c385, 90, 100, 4, r1);
ok('carton debout : 16 bobines vues de dessus, 4 × 2 vues de côté', gc.dessus.length === 16 && gc.cote.length === 8 && gc.dessus.every(x => x.rond));
ok('carton : bobines dans le carton (jeu/2 de marge)', gc.dessus.every(x => x.x >= 2 && x.y >= 2 && x.x + x.w <= 385 - 2 + 1e-9 && x.y + x.h <= 385 - 2 + 1e-9));
ok('carton : reste 21 × 21 × 4 mm (381 − 4 × 90, 204 − 2 × 100)', proche(gc.videL, 21, 1e-9) && proche(gc.videW, 21, 1e-9) && proche(gc.videH, 4, 1e-9));
const gc2 = G.geoCarton(c385, 90, 100, 4, r2);
ok('carton couchées : rectangles de dessus, côté rond si axe en largeur', gc2.dessus.every(x => !x.rond) && gc2.dessus.length === r2.a * r2.b);
const sv = SCH.carton({ meilleur: { carton: c385, rang: r1, parCarton: 32 }, D: 90, L: 100, jeu: 4, dm: 76 });
ok('carton : schéma SVG produit, deux vues quand 2 couches', /<svg/.test(sv.svg) && /Vue de côté/.test(sv.svg) && !sv.exemple);
ok('métrage sans valeurs : exemple', SCH.metrage({}).exemple === true && /<svg/.test(SCH.metrage({}).svg));
ok('fronts : schéma sans couleur en dur', !/#[0-9a-f]{3,6}\b/i.test(SCH.fronts({ laize: 440, larg: 104.5, espl: 3.25, nb: 4 }).svg));

if (echecs) { console.log('\n' + echecs + ' cas en échec'); process.exit(1); }
console.log('\nTous les cas passent.');
