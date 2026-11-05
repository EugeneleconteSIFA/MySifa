// Étiquettes spécifiques — moteur de l'éditeur (static/mysifa_etiq_moteur.js).
//
// Rejoue tests/etiq_formules_cas.json, les mêmes cas que
// tests/test_etiq_avance.py : l'aperçu et l'impression doivent rendre la
// même valeur. Vérifie aussi la lecture d'un collage Excel / CSV, la
// correspondance colonnes → variables, la lisibilité des codes et
// l'étiquette logistique palette.
//
// Lancer : node tests/test_etiq_moteur.js
const path = require('path');
const fs = require('fs');
process.chdir(path.join(__dirname, '..'));
const M = require('../static/mysifa_etiq_moteur.js');
const CAS = JSON.parse(fs.readFileSync('tests/etiq_formules_cas.json', 'utf8'));

let ko = 0;
function check(label, got, attendu) {
  const ok = JSON.stringify(got) === JSON.stringify(attendu);
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + String(label).slice(0, 70).padEnd(72) + (ok ? '' : JSON.stringify(got) + '   attendu ' + JSON.stringify(attendu)));
}
const enDate = (s) => { const [d, t] = s.split('T'); const [a, m, j] = d.split('-').map(Number); const [h, mi] = t.split(':').map(Number); return new Date(a, m - 1, j, h, mi); };

for (const [expr, vals, att] of CAS.formules) check('formule ' + expr, M.evaluer(expr, vals).valeur, att);
for (const [expr, msg] of CAS.erreurs) check('erreur ' + expr, M.evaluer(expr, {}).erreur, msg);
for (const [expr, vals, att] of CAS.conditions) check('condition ' + expr + ' ' + JSON.stringify(vals), M.conditionVraie(expr, vals), att);
for (const [v, vals, maint, att] of CAS.dates) check('date ' + JSON.stringify(v), M.calculerDate(v, vals, enDate(maint)), att);
for (const [val, nb] of CAS.gs1) check('GS1 ' + val, M.controlerGs1(val).length, nb);
check('SSCC officiel GS1', M.sscc('1', '0614141', 234567890), '106141412345678908');

// Collage Excel (tabulations) et CSV point-virgule avec guillemets
const t1 = M.lireTableau('Lot\tQuantité\tClient\nL1\t12\tDupont\nL2\t24\t"Martin; fils"\n');
check('collage Excel : entêtes', t1.entetes, ['Lot', 'Quantité', 'Client']);
check('collage Excel : lignes', t1.lignes.length, 2);
const t2 = M.lireTableau('lot;client\r\n"A""1";"X;Y"\r\n\r\nB2;Z\r\n');
check('CSV ; guillemets doublés', t2.lignes, [['A"1', 'X;Y'], ['B2', 'Z']]);
const vars = [{ nom: 'lot', libelle: 'N° de lot', type: 'saisie' }, { nom: 'qte', libelle: 'Quantité', type: 'saisie' },
  { nom: 'client_nom', libelle: 'Client', type: 'source', champ: 'client.raison_sociale' }, { nom: 'n', libelle: 'N', type: 'compteur' }];
const corr = M.correspondanceAuto(t1.entetes, vars);
check('correspondance automatique', corr, { lot: 0, qte: 1, client_nom: 2 });
check('enregistrements', M.enregistrementsDepuis(t1, corr)[1], { lot: 'L2', qte: '24', client_nom: 'Martin; fils' });

// Valeurs + visibilité, identiques au serveur
const lay = { variables: [{ nom: 'lot', type: 'saisie', valeur: '' }, { nom: 'n', type: 'compteur', debut: 5, pas: 2, longueur: 3, prefixe: 'C' },
  { nom: 'f', type: 'formule', expression: 'n & "/" & lot' }] };
const v = M.valeurs(lay, { saisies: { lot: 'L9' }, index: 2 });
check('compteur au rang 2', v.n, 'C009');
check('formule', v.f, 'C009/L9');
check('masquer si vide', M.visible({ type: 'texte', valeur: 'Lot {{lot}}', masquer_si_vide: true }, { lot: '' }), false);
check('condition', M.visible({ type: 'texte', valeur: 'x', condition: 'lot = "L9"' }, v), true);

// Lisibilité
const ctx = { dpi: 203, L: 100, H: 150, voisins: [] };
const petit = M.lisibilite({ nom: 'c', symbologie: 'code128', module: 0.1, hauteur: 15, x: 10, y: 10 }, { w: 30, h: 15 }, ctx, 'ABC');
check('module trop fin bloquant', petit.some(a => a.gravite === 'bloquant'), true);
const bord = M.lisibilite({ nom: 'c', symbologie: 'code128', module: 0.375, hauteur: 15, x: 0.5, y: 10 }, { w: 30, h: 15 }, ctx, 'ABC');
check('trop près du bord', bord.some(a => /bord/.test(a.message)), true);
const bon = M.lisibilite({ nom: 'c', symbologie: 'code128', module: 0.375, hauteur: 15, x: 10, y: 10 }, { w: 30, h: 15 }, ctx, 'ABC');
check('code correct : aucune alerte', bon, []);
const sscc = M.lisibilite({ nom: 's', symbologie: 'gs1_128', module: 0.375, hauteur: 20, x: 10, y: 10 }, { w: 60, h: 20 }, ctx, '(00)106141412345678908');
check('SSCC logistique : X et hauteur GS1', sscc.filter(a => /SSCC logistique/.test(a.message)).length, 2);

// Étiquette logistique palette
const log = M.etiquetteLogistique({ prefixe: '3012345', ai: ['02', '37', '10', '15', '3102'] });
const codes = log.layout.elements.filter(e => e.type === 'code_barre');
check('logistique : SSCC le plus bas', codes[codes.length - 1].valeur, '(00){{sscc}}');
check('logistique : AI variable (10) en dernier', /\(10\)\{\{lot\}\}$/.test(codes[0].valeur), true);
const vl = M.valeurs(log.layout, { saisies: { gtin: '03012345000017', quantite: '24', lot: 'L1', poids_kg: '12,5' }, maintenant: new Date(2026, 9, 22) });
check('logistique : données GS1 conformes', M.controlerGs1(M.substituer(codes[0].valeur, vl)), []);
check('logistique : SSCC conforme', M.controlerGs1(M.substituer(codes[1].valeur, Object.assign({}, vl, { sscc: '030123450000000017' }))), []);
check('logistique : SSCC fourni par le client (saisie contrôlée)', log.layout.variables.find(v => v.nom === 'sscc').type, 'saisie');
// Plage confiée par le client : SSCC calculé sur son préfixe.
const logP = M.etiquetteLogistique({ fourni: false, prefixe: '3012345', serie_debut: 500, serie_fin: 900, ai: ['02'] });
const vs = logP.layout.variables.find(v => v.nom === 'sscc');
check('logistique : plage du client', [vs.type, vs.serie_debut, vs.serie_fin], ['sscc', 500, 900]);
const vlP = M.valeurs(logP.layout, { plan: { sscc: { premier: 500 } }, maintenant: new Date(2026, 9, 22) });
check('logistique : SSCC calculé conforme', M.controlerGs1('(00)' + vlP.sscc), []);
check('logistique : intitulés figés', log.layout.elements.filter(e => e.calque === 'fond').every(e => e.verrou), true);

console.log(ko ? '\n' + ko + ' échec(s)' : '\nTout est bon.');
process.exit(ko ? 1 : 0);
