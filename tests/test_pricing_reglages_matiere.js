// Réglages de matière : grammage + perte, taxes en %, marge optionnelle.
// Lancer : node tests/test_pricing_reglages_matiere.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8').replace(/\r\n/g, '\n');

function extraire(nom) {
  const i = src.indexOf('function ' + nom + '(');
  if (i < 0) throw new Error('introuvable : ' + nom);
  let prof = 0;
  for (let j = src.indexOf('{', i); j < src.length; j++) {
    if (src[j] === '{') prof++;
    else if (src[j] === '}') { prof--; if (prof === 0) return src.slice(i, j + 1); }
  }
  throw new Error('accolades non fermées : ' + nom);
}

let ko = 0;
function check(label, got, attendu) {
  const ok = JSON.stringify(got) === JSON.stringify(attendu);
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(58) + JSON.stringify(got)
    + (ok ? '' : '   attendu ' + JSON.stringify(attendu)));
}

const ctx = { console, Math, parseFloat, S: {} };
vm.createContext(ctx);
vm.runInContext([extraire('poidsRetenu'), extraire('grammageRetenu'), extraire('needsWeight')].join('\n'), ctx);

// ─── Grammage et perte ──────────────────────────────────────────────────────
check('70 g/m² sans perte = 0,070 kg/m²', ctx.poidsRetenu(70, 0), 0.07);
check('70 g/m² avec 9 % de perte', ctx.poidsRetenu(70, 9), 0.0763);
check('le grammage retenu est affiché en g/m²', ctx.grammageRetenu(70, 9), 76.3);
check('champs vides = zéro, pas NaN', ctx.poidsRetenu('', ''), 0);
check('une perte de 100 % double le grammage', ctx.grammageRetenu(50, 100), 100);
check('grammage saisi avec décimales', ctx.grammageRetenu(22.5, 9), 24.53);

// ─── La section n'apparaît que si le poids sert ─────────────────────────────
// Le grammage ne sert qu'à passer du kilo au m² : un prix déjà au m² n'en a
// aucun usage, importé ou pas.
check('prix au kilo : le grammage est nécessaire',
  ctx.needsWeight({ price_basis: 'PER_KG', is_imported: false }), true);
check('prix au kilo importé : toujours nécessaire',
  ctx.needsWeight({ price_basis: 'PER_KG', is_imported: true }), true);
check('prix au m² : inutile',
  ctx.needsWeight({ price_basis: 'PER_M2', is_imported: false }), false);
check('prix au m² importé : inutile aussi',
  ctx.needsWeight({ price_basis: 'PER_M2', is_imported: true }), false);

// ─── Ce que les deux fiches envoient au serveur ─────────────────────────────
for (const [nom, fn] of [['fiche matière', 'saveMaterialForm'], ['fiche MyStock', 'saveDeclinaisonForm']]) {
  const code = extraire(fn);
  check(nom + ' : grammage envoyé', code.includes('grammage_gsm:'), true);
  check(nom + ' : perte envoyée', code.includes('perte_pct:'), true);
  check(nom + ' : taxe en pourcentage', code.includes('taxe_pct:'), true);
  check(nom + ' : choix de marge envoyé', code.includes('applique_marge:'), true);
  check(nom + ' : plus de multiplicateur', code.includes('tax_incidence'), false);
  check(nom + ' : plus de poids saisi', code.includes('weight_per_m2:'), false);
}

// ─── Chaque méthode de transport est expliquée, exemple à l'appui ───────────
// Quatre méthodes dont deux font la même division sur des données différentes :
// sans explication ni exemple chiffré, le choix se fait au hasard.
const aide = src.slice(src.indexOf('const TRANSPORT_AIDE = {'), src.indexOf('function transportModeOptions('));
for (const m of ['AMOUNT', 'PCT', 'CONTENEUR', 'FORFAIT']) {
  const bloc = aide.slice(aide.indexOf(m + ': {'), aide.indexOf('},', aide.indexOf(m + ': {')));
  check('méthode expliquée : ' + m, bloc.includes('quoi:'), true);
  check('exemple chiffré : ' + m, /exemple:\s*"[^"]*\d/.test(bloc), true);
}
check('l\'aide est rendue sous le sélecteur', src.includes('function transportAideHtml('), true);
for (const prefixe of ['f', 'd']) {
  check('sélecteur ' + prefixe + '-tmode suivi de son aide',
    new RegExp('id="' + prefixe + '-tmode">\\$\\{transportModeOptions[^]{0,80}transportAideHtml').test(src), true);
}
// L'aide dépend de la méthode : le formulaire doit se re-rendre au changement.
check('changer de méthode redessine la fiche', /"f-cur", "f-basis", "f-imp", "f-tmode"/.test(src), true);

// ─── Placement demandé dans le formulaire ───────────────────────────────────
const form = src.slice(src.indexOf('function renderMaterialForm('), src.indexOf('function syncMaterialFormFromDom('));
check('caractéristiques avant prix d\'achat',
  form.indexOf('<h3>Caractéristiques</h3>') < form.indexOf("<h3>Prix d'achat</h3>"), true);
const importBloc = form.slice(form.indexOf('id="import-block"'), form.indexOf('id="carac-section"') > form.indexOf('id="import-block"')
  ? form.indexOf('id="carac-section"') : form.length);
check('la taxe est dans l\'encadré import', importBloc.includes('id="f-tax"'), true);
// La case « Appliquer la marge » a quitté le bloc Prix d'achat : elle vit
// maintenant dans le panneau latéral Paramètres, bloc « Cette matière ».
const panneau = src.slice(src.indexOf('function inlineSettingsHtml('), src.indexOf('function bindInlineSettings('));
check('la case marge n\'est plus dans le corps du formulaire', form.includes('id="f-marge"'), false);
check('le formulaire monte le panneau Paramètres', form.includes('inlineSettingsHtml("f", f)'), true);
check('la fiche MyStock monte le même panneau', src.includes('inlineSettingsHtml("d", f)'), true);
check('la case marge est dans le panneau Paramètres', panneau.includes('${prefixe}-marge'), true);
check('le panneau distingue les deux portées',
  panneau.includes('Cette matière') && panneau.includes('Toutes les matières'), true);
check('le panneau ne s\'appelle plus « Paramètres globaux »',
  panneau.includes('Paramètres globaux'), false);
check('plus de champ poids kg/m²', form.includes('id="f-wm2"'), false);
check('un seul champ grammage', (form.match(/id="f-gsm"/g) || []).length, 1);
check('champ perte présent', form.includes('id="f-perte"'), true);
check('grammage retenu non saisissable', form.includes('id="f-gram-out"'), true);
// .field-row est une grille à 2 colonnes : la suite en a 5, elle a sa grille.
check('la ligne grammage a sa propre grille', form.includes('class="gram-row"'), true);
check('les deux fiches utilisent la même grille',
  (src.match(/class="gram-row"/g) || []).length, 2);

// ─── Tableau récapitulatif ──────────────────────────────────────────────────
const recap = extraire('recapTableHtml');
check('les taxes précèdent le sous-total',
  recap.indexOf('label: "Taxes"') < recap.indexOf('label: "Sous-total achat"'), true);
check('plus de ligne « incidence taxes »', recap.includes('Incidence taxes'), false);
check('formule mise à jour',
  src.includes("(prix d'achat + transport + taxes) × change"), true);

// ─── Méthodes de transport ──────────────────────────────────────────────────
const modes = src.slice(src.indexOf('const TRANSPORT_MODES ='),
                        src.indexOf('];', src.indexOf('const TRANSPORT_MODES =')));
for (const m of ['AMOUNT', 'PCT', 'CONTENEUR', 'FORFAIT']) {
  check('méthode proposée : ' + m, modes.includes('"' + m + '"'), true);
}
const champs = extraire('transportChampsHtml');
check('le pourcentage a son champ', champs.includes('% du prix'), true);
check('conteneur et forfait ont coût + quantité',
  champs.includes('-tcout') && champs.includes('-tqte'), true);
check('les libellés changent selon la méthode',
  src.includes('Coût du conteneur') && src.includes('Forfait de commande'), true);
for (const [nom, fn] of [['fiche matière', 'saveMaterialForm'], ['fiche MyStock', 'saveDeclinaisonForm']]) {
  const code = extraire(fn);
  check(nom + ' : coût envoyé', code.includes('transport_cout:'), true);
  check(nom + ' : quantité envoyée', code.includes('transport_quantite:'), true);
}

// ─── Créer une déclinaison : dériver ou vierge ──────────────────────────────
check('la flèche coudée existe', src.includes('"corner-down-right"'), true);
check('dériver reprend les réglages', src.includes('data-ms-deriver'), true);
check('le + crée une déclinaison vierge', src.includes('vierge'), true);
check('plus de duplication de ligne fournisseur', src.includes('data-ms-dup"'), false);

// ─── Bandeaux d'explication retirés ─────────────────────────────────────────
check('plus de note sur la page Matières MyStock',
  src.includes('Le prix saisi ici est'), false);
check('plus de note sur la page Produits MyStock',
  src.includes('Ces produits sont composés de'), false);
check('colonne fournisseur principal', src.includes('Fournisseur principal'), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
