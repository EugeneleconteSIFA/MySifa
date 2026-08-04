// Réglages de matière : grammage + perte, taxes en %, marge optionnelle.
// Lancer : node tests/test_pricing_reglages_matiere.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8');

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
check('prix au kilo : le grammage est nécessaire',
  ctx.needsWeight({ price_basis: 'PER_KG', is_imported: false }), true);
check('prix au m² sans import : inutile',
  ctx.needsWeight({ price_basis: 'PER_M2', is_imported: false }), false);
check('prix au m² importé : nécessaire pour le transport',
  ctx.needsWeight({ price_basis: 'PER_M2', is_imported: true }), true);

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

// ─── Placement demandé dans le formulaire ───────────────────────────────────
const form = src.slice(src.indexOf('function renderMaterialForm('), src.indexOf('function syncMaterialFormFromDom('));
check('caractéristiques avant prix d\'achat',
  form.indexOf('<h3>Caractéristiques</h3>') < form.indexOf("<h3>Prix d'achat</h3>"), true);
const importBloc = form.slice(form.indexOf('id="import-block"'), form.indexOf('id="carac-section"') > form.indexOf('id="import-block"')
  ? form.indexOf('id="carac-section"') : form.length);
check('la taxe est dans l\'encadré import', importBloc.includes('id="f-tax"'), true);
check('la case marge est dans le bloc prix', form.includes('id="f-marge"'), true);
check('plus de champ poids kg/m²', form.includes('id="f-wm2"'), false);
check('un seul champ grammage', (form.match(/id="f-gsm"/g) || []).length, 1);
check('champ perte présent', form.includes('id="f-perte"'), true);
check('grammage retenu non saisissable', form.includes('id="f-gram-out"'), true);

// ─── Tableau récapitulatif ──────────────────────────────────────────────────
const recap = extraire('recapTableHtml');
check('les taxes précèdent le sous-total',
  recap.indexOf('label: "Taxes"') < recap.indexOf('label: "Sous-total achat"'), true);
check('plus de ligne « incidence taxes »', recap.includes('Incidence taxes'), false);
check('formule mise à jour',
  src.includes("(prix d'achat + transport + taxes) × change"), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
