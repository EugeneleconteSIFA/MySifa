// Un seul endroit écrit les prix matière : Coûts matières.
//
// Avant, quatre écrans pouvaient réécrire le même prix — la valorisation
// MyStock (saisie inline + deux modales + trois bascules), l'administration des
// matières MyStock, et la modale de réception de stock, qui recalculait un prix
// moyen pondéré sans laisser la moindre trace dans l'historique. Un écart de
// prix se constatait alors sans jamais pouvoir s'expliquer.
//
// Ce test garde la règle : ailleurs que dans Coûts matières, un prix s'affiche,
// il ne se saisit pas.
//
// Lancer : node tests/test_prix_verrouilles.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs');

const lire = (f) => fs.readFileSync(f, 'utf8').replace(/\r\n/g, '\n');
const stock = lire('app/web/stock_page.py');
const modals = lire('static/mysifa_stock_modals.js');
const pricing = lire('static/pricing_app.js');

let ko = 0;
function check(label, got, attendu) {
  const ok = got === attendu;
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(56) + got + (ok ? '' : '   attendu ' + attendu));
}

console.log('--- valorisation MyStock : plus de saisie de prix ---');
check('plus de saisie inline du prix unitaire', stock.includes('function saveValorisationPrice('), false);
check('plus de saisie inline du prix HT produit fini', stock.includes('async function savePFPrice('), false);
check('plus de bascule USD', stock.includes('function toggleValorisationUSD('), false);
check('plus de bascule taxe d\'importation', stock.includes('function toggleValorisationTaxe('), false);
check('plus de bascule transport container', stock.includes('function toggleValorisationTransport('), false);
check('aucun appel résiduel aux bascules', /toggleValorisation(USD|Taxe|Transport)\(/.test(stock), false);

console.log('\n--- les modales ne gardent que le conditionnement ---');
// La modale carton / adhésif / mandrin : unités par palette, plus le prix.
const modaleCond = stock.slice(
  stock.indexOf('async function openValorisationConditionnementModal('),
  stock.indexOf('function valBlocPrixLectureSeule('));
check('conditionnement : le prix n\'est plus envoyé', modaleCond.includes('prix_unitaire:'), false);
check('conditionnement : les unités par palette restent', modaleCond.includes('unites_par_palette: upp'), true);
check('conditionnement : le prix reste affiché', modaleCond.includes('valBlocPrixLectureSeule('), true);

// La modale des bobines laizées : métrage seul, plus le prix au m².
const modaleParams = stock.slice(
  stock.indexOf('async function openValorisationParamsModal('),
  stock.indexOf('function buildValorisationTable()'));
check('métrage : le prix m² n\'est plus envoyé', modaleParams.includes('prix_eur_m2: prix'), false);
check('métrage : le métrage reste enregistré',
  modaleParams.includes('metres_lineaires_par_bobine: metres'), true);
check('métrage : le prix m² reste affiché', modaleParams.includes('valBlocPrixLectureSeule('), true);

console.log('\n--- administration des matières MyStock ---');
check('le prix commun est verrouillé',
  /prixM2Inp\.value = String\(item\.prix_eur_m2[^]{0,120}mpVerrouillerPrix\(prixM2Inp\)/.test(stock), true);
check('le prix par laize est verrouillé aussi',
  /laizePriceInputs\[id\] = priceInp/.test(stock) && /mpVerrouillerPrix\(priceInp\)/.test(stock), true);
check('le verrou est réellement en lecture seule',
  /function mpVerrouillerPrix[^]{0,400}readOnly = true/.test(stock), true);
check('un renvoi vers Coûts matières accompagne le verrou',
  stock.includes('function mpNotePrixVerrouille('), true);

console.log('\n--- réception de stock : plus de recalcul de PMP ---');
const entree = modals.slice(modals.indexOf("if (typeMvt === 'entree')"), modals.indexOf("} else if (typeMvt === 'sortie')"));
check('la réception n\'envoie plus de prix', entree.includes('b.prix_eur_m2 = v'), false);
check('elle affiche le prix en vigueur', entree.includes('prixLecture'), true);
check('et dit où il se modifie', entree.includes('Coûts matières'), true);

console.log('\n--- le chemin de retour existe ---');
check('MyStock renvoie vers la fiche Coûts matières',
  stock.includes("'/pricing/materials' + (ref ? '?ref=' + encodeURIComponent(ref) : '')"), true);
check('Coûts matières sait lire ce ?ref=',
  pricing.includes('function appliquerParamsUrl()') && pricing.includes('params.get("ref")'), true);
check('et ouvre l\'onglet MyStock filtré',
  /S\.filters\.matTab = "mystock";\s*\n\s*S\.filters\.msQ = ref;/.test(pricing), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
