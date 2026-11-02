// Saisie prod › widget Poids de colle — formule (static/mysifa_poids_colle.js),
// rejouée sur le classeur « application excel calcul de poids adhésif ».
// Lancer : node tests/test_poids_colle.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'mysifa_poids_colle.js'), 'utf8');
const ctx = { window: {}, document: {}, localStorage: { getItem() { return null; }, setItem() {} } };
vm.createContext(ctx);
vm.runInContext(src, ctx);
const W = ctx.window.MySifaPoidsColle;

let echecs = 0;
function ok(nom, v) { if (v) console.log('ok  ', nom); else { echecs++; console.log('ECHEC', nom); } }
const proche = (a, b, tol) => Math.abs(a - b) <= tol;

// Feuil1 ligne 5 : 148 × 208,725, rayon 6, frontal 70, 1 étiquette, 3,043 g.
// Le classeur prend π = 3,14 : 28,60 g/m² ; avec Math.PI l'écart est de 0,0003.
const r = W._calcul({ forme: 'rectangle', laize: 148, hauteur: 208.725, rayon: 6, frontal: 70,
                      encre: 0, couverture: 0, nombre: 1, pese: 3.043 });
const surfXl = 148 * 208.725 - (6 * 6 - (3.14 * 6 * 6) / 4) * 4;
ok('rectangle : adhésif du classeur (28,60 g/m²)', proche(r.adhesif, (3.043 - surfXl * 70 / 1e6) / surfXl * 1e6, 0.01));
ok('rectangle : surface coins arrondis (π contre 3,14 : 0,06 mm²)', proche(r.surface, surfXl, 0.1));

// Ligne 11 : rond Ø50, frontal 91, 4 étiquettes, 0,87 g.
const rd = W._calcul({ forme: 'ronde', diametre: 50, frontal: 91, nombre: 4, pese: 0.87 });
const sR = 25 * 25 * 3.14;
ok('ronde : adhésif du classeur', proche(rd.adhesif, (0.87 - sR * 91 * 4 / 1e6) / (sR * 4) * 1e6, 0.3));

// Encre : grammage × couverture, comme (D + E × F / 100).
const en = W._calcul({ forme: 'rectangle', laize: '100', hauteur: '50', rayon: '0', frontal: '70',
                       encre: '2', couverture: '50', nombre: '2', pese: '0,8' });
ok('encre à 50 % comptée dans le théorique', proche(en.theorique, 100 * 50 * 2 * 71 / 1e6, 1e-9));
ok('virgule décimale acceptée', proche(en.adhesif, (0.8 - en.theorique) / (100 * 50 * 2) * 1e6, 1e-9));

ok('poids manquant : théorique rendu, pas d\'adhésif', W._calcul({ forme: 'rectangle', laize: 100, hauteur: 50, frontal: 70, nombre: 1 }).adhesif === undefined);
ok('rayon plus grand que le format refusé', !!W._calcul({ forme: 'rectangle', laize: 10, hauteur: 10, rayon: 6, frontal: 70, nombre: 1, pese: 1 }).manque);
ok('papier manquant signalé', /papier/i.test(W._calcul({ forme: 'ronde', diametre: 40, nombre: 1, pese: 1 }).manque));

console.log(echecs ? echecs + ' échec(s)' : 'Tout est vert.');
process.exit(echecs ? 1 : 0);
