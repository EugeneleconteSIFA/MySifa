// Les trois portes d'entrée du tarif fournisseur.
//
// Un tarif se règle depuis trois endroits : l'onglet Fournisseurs de Coûts
// matières, la ligne de prix d'une déclinaison, et la fiche fournisseur de
// Réglages. Trois portes, mais UNE seule pièce — un seul formulaire, une seule
// route d'écriture. Le jour où l'un des trois se met à écrire autrement, c'est
// celui qu'on oublie qui pose des chiffres faux.
//
// Lancer : node tests/test_tarif_ecrans.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs');

const lire = (f) => fs.readFileSync(f, 'utf8').replace(/\r\n/g, '\n');
const app = lire('static/pricing_app.js');
const css = lire('static/pricing_app.css');
const api = lire('app/routers/pricing.py');
const svc = lire('app/services/mystock_prix.py');
const reglages = lire('app/web/settings_page.py');

let ko = 0;
function check(label, got, attendu) {
  const ok = got === attendu;
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(58) + got + (ok ? '' : '   attendu ' + attendu));
}

console.log('--- une seule pièce derrière les trois portes ---');
check('un seul formulaire de tarif', (app.match(/function openTarifModal\(/g) || []).length, 1);
check('une seule route d\'écriture',
  (api.match(/@router\.patch\("\/api\/pricing\/tarifs\/\{fournisseur_id\}\/\{matiere_id\}"\)/g) || []).length, 1);
check('un seul service qui écrit', (svc.match(/^def set_tarif\(/gm) || []).length, 1);

console.log('\n--- porte 1 : l\'onglet Fournisseurs de Coûts matières ---');
check('l\'entrée existe dans la barre latérale',
  app.includes('label: "Fournisseurs", route: "fournisseurs"'), true);
check('la liste a sa route', app.includes('return { name: "fournisseurs", id: null }'), true);
check('la fiche aussi', app.includes('return { name: "fournisseur-edit", id: parts[2] }'), true);
check('elles sont câblées au démarrage',
  app.includes('r === "fournisseurs"') && app.includes('r === "fournisseur-edit"'), true);
check('la fiche ouvre le formulaire', app.includes('data-tarif-mat'), true);
// Une route cliente sans route serveur = page noire au rechargement. On l'a
// déjà payé une fois sur /pricing/mystock/90.
const routes = lire('app/web/pricing_page.py');
check('le rechargement de la liste ne tombe pas en 404',
  routes.includes('"/pricing/fournisseurs"'), true);
check('celui de la fiche non plus',
  routes.includes('"/pricing/fournisseurs/{fournisseur_id}"'), true);

console.log('\n--- porte 2 : depuis la ligne de prix ---');
check('chaque ligne porte son raccourci', app.includes('data-ms-tarif'), true);
check('il est branché', app.includes('btn.getAttribute("data-ms-tarif").split("|")'), true);
check('il ouvre la même modale',
  /data-ms-tarif[^]{0,600}openTarifModal\(/.test(app), true);
// Un fournisseur sans tarif propre calcule sur un repli : il faut que ça se
// voie, sinon personne ne va le régler.
check('l\'absence de tarif se signale', app.includes('ms-tarif-manquant'), true);
check('et a son style', css.includes('.ms-tarif-manquant{'), true);
check('le serveur dit si le tarif existe', svc.includes('ligne["a_tarif"] = tarif is not None'), true);

console.log('\n--- porte 3 : la fiche fournisseur de Réglages ---');
check('l\'onglet existe', reglages.includes("k:'tarif'"), true);
check('il a son rendu', reglages.includes('function _f2TabTarif('), true);
check('déclaré dans les renderers', reglages.includes('tarif: _f2TabTarif'), true);
check('et dans les binders', reglages.includes('tarif: _f2BindTarif'), true);
check('les données sont chargées avec la fiche',
  reglages.includes("api('/api/pricing/tarifs/fournisseur/' + id)"), true);
// Réglages ne doit PAS savoir écrire un tarif : sinon deux formulaires à tenir
// d'accord. Il lit, et renvoie vers Coûts matières.
// Le corps de `_f2TabTarif` seul : ailleurs dans Réglages, des PATCH légitimes
// existent (identité, FSC…), on ne les cherche pas ici.
const ongletTarif = reglages.slice(reglages.indexOf('function _f2TabTarif('),
                                   reglages.indexOf('function _f2BindTarif('));
check('Réglages n\'écrit aucun tarif', /method:\s*'(PATCH|PUT|POST)'/.test(ongletTarif), false);
check('il renvoie vers Coûts matières',
  reglages.includes("'/pricing/fournisseurs/' + f.id"), true);
check('un échec de chargement ne casse pas la fiche',
  reglages.includes('erreur:') && reglages.includes('t.erreur'), true);

console.log('\n--- ce que le formulaire doit dire ---');
const modale = app.slice(app.indexOf('async function openTarifModal('),
                         app.indexOf('function categorieBadge('));
check('la portée du réglage est annoncée',
  modale.includes('toutes les déclinaisons de cette matière chez ce fournisseur'), true);
// Enregistrer un transport déplace le sous-total de la valorisation MyStock :
// le dire AVANT, pas le découvrir après.
check('l\'effet sur MyStock est annoncé avant', modale.includes('nb_principal ?'), true);
check('et confirmé après', modale.includes('declinaisons_touchees'), true);
check('la devise est en lecture ici', modale.includes('Se règle sur sa fiche'), true);
check('chaque méthode n\'affiche que ses champs',
  modale.includes("if (mode === \"PCT\")") && modale.includes('TRANSPORT_CHAMPS[mode]'), true);
check('avec l\'aide de la méthode choisie', modale.includes('transportAideHtml(mode)'), true);

// Un transitaire ne change pas de méthode d'un frontal à l'autre : le réglage
// doit pouvoir se poser une fois pour toute la catégorie, sans dix allers-retours.
console.log('\n--- appliquer le transport aux autres matières du fournisseur ---');
check('le bouton existe', app.includes('function transportPropagerHtml('), true);
check('et son style', css.includes('.transport-propage{'), true);
check('la modale tarif le pose', modale.includes('transportPropagerHtml("tf-prop"'), true);
const fiche = app.slice(app.indexOf('function renderDeclinaisonForm('),
                        app.indexOf('function productsTabsHtml('));
check('la fiche déclinaison aussi', fiche.includes('"d-tprop"'), true);
// La grille est en deux colonnes : l'action se pose DANS la field-row, à côté
// des taxes, plutôt qu'en pied de bloc où elle laissait une colonne vide.
check('posée dans la grille, pas en dessous',
  /transportPropagerHtml\([^]{0,200}\n\s*<\/div>\n\s*<\/div>\n\s*<\/div>/.test(fiche), true);
check('et son bouton a son propre style lisible',
  app.includes('btn-propage') && css.includes('.btn-propage{'), true);
// Sans fournisseur identifié, il n'y a aucun tarif à propager : le bouton
// disparaît plutôt que d'échouer au clic. Idem en lecture seule.
check('pas de fournisseur (ni de droit d\'écrire), pas de bouton',
  app.includes('if (!fournisseurNom || !S.canWrite) return "";'), true);
// On annonce le nombre exact AVANT d'écrire : « appliquer à 7 matières ? » se
// refuse en connaissance de cause, « appliquer partout ? » non.
check('le périmètre est demandé avant', app.includes('perimetre = await api(url)'), true);
check('et confirmé', app.includes('confirmerAction({'), true);
// La confirmation s'ouvre par-dessus la modale tarif : écrire dans le même
// conteneur effacerait la modale qui l'a demandée.
check('la confirmation a son propre calque',
  app.includes('document.body.appendChild(calque)'), true);
check('seuls le transport et les taxes voyagent',
  app.includes('function transportPayload(') && !/function transportPayload\([^]{0,600}price_basis/.test(app), true);

console.log('\n--- l\'API ---');
for (const route of [
  '/api/pricing/tarifs/fournisseurs',
  '/api/pricing/tarifs/fournisseur/{fournisseur_id}',
  '/api/pricing/tarifs/matiere/{matiere_id}',
  '/api/pricing/tarifs/fournisseur/{fournisseur_id}/devise',
  '/api/pricing/tarifs/{fournisseur_id}/{matiere_id}',
  '/api/pricing/tarifs/{fournisseur_id}/{matiere_id}/propager',
]) {
  check('route ' + route, api.includes('"' + route + '"'), true);
}
check('l\'annuaire porte la devise', api.includes('"price_currency": devises.get(int(r["id"]), "EUR")'), true);
check('les écritures exigent le droit d\'écrire',
  (api.match(/tarifs[^]{0,900}_require_write\(request\)/g) || []).length >= 1, true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
