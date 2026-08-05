// Vue « Produits MyStock » (Coûts matières) : routes, composition, aperçu du coût.
// Lancer : node tests/test_pricing_produits_mystock.js
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
function constante(nom) {
  const i = src.indexOf('const ' + nom + ' =');
  if (i < 0) throw new Error('introuvable : ' + nom);
  return src.slice(i, src.indexOf('\n  ];', i) + 5);
}

let ko = 0;
function check(label, got, attendu) {
  const ok = JSON.stringify(got) === JSON.stringify(attendu);
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(56) + JSON.stringify(got)
    + (ok ? '' : '   attendu ' + JSON.stringify(attendu)));
}

const ctx = {
  window: { location: { pathname: '/' } }, S: {}, console, Math, Number,
  parseFloat, parseInt, document: { getElementById: () => null },
};
vm.createContext(ctx);
vm.runInContext([
  extraire('parseRoute'),
  constante('MSP_ROLES'),
  extraire('defaultMsProductForm'),
  extraire('msProductComposants'),
  extraire('refreshMsProductPreview'),
  // `const` reste dans la portée du script : on l'expose pour pouvoir l'inspecter.
  'globalThis.MSP_ROLES = MSP_ROLES;',
].join('\n'), ctx);

// ─── Routes ─────────────────────────────────────────────────────────────────
function route(p) { ctx.window.location.pathname = p; return ctx.parseRoute(); }
check('nouveau produit MyStock', route('/pricing/mystock/produit/new'), { name: 'msproduct-new', id: null });
check("édition d'un produit MyStock", route('/pricing/mystock/produit/8'), { name: 'msproduct-edit', id: '8' });
check('la fiche déclinaison reste joignable', route('/pricing/mystock/12'), { name: 'mystock-edit', id: '12' });
check('sans identifiant on retombe sur la liste', route('/pricing/mystock/produit'), { name: 'products', id: null });
check('les produits de la base CM ne bougent pas', route('/pricing/products/3'), { name: 'product-edit', id: '3' });

// ─── Composition envoyée à l'API ────────────────────────────────────────────
ctx.S.formMsProduct = { code: 'X', designation: 'Y', roles: { FRONTAL: 5, GLASSINE: 9 }, autres: [11, 0], custom_margin_pct: '' };
check("les rôles nommés sortent dans l'ordre", ctx.msProductComposants(), [
  { declinaison_id: 5, role: 'FRONTAL' },
  { declinaison_id: 9, role: 'GLASSINE' },
  { declinaison_id: 11, role: 'AUTRE' },
]);
check("un emplacement vide n'est pas envoyé",
  ctx.msProductComposants().some((c) => c.role === 'ADHESIF'), false);
ctx.S.formMsProduct = ctx.defaultMsProductForm();
check("un produit vierge n'a aucun composant", ctx.msProductComposants(), []);

// ─── Aperçu du coût ─────────────────────────────────────────────────────────
ctx.S.msDecls = [
  { id: 5, reference: 'F70', libelle: '330 mm', cout_eur_m2: 1.5 },
  { id: 9, reference: 'GL', libelle: '500 mm', cout_eur_m2: 0.5 },
  { id: 11, reference: 'CX', libelle: '330 mm', cout_eur_m2: null },
];
ctx.S.settings = { default_margin_pct: 6 };

ctx.S.formMsProduct = { code: '', designation: '', roles: { FRONTAL: 5, GLASSINE: 9 }, autres: [], custom_margin_pct: '' };
ctx.refreshMsProductPreview();
let p = ctx.S.msProdPreview;
check('coût = somme des déclinaisons', p.total_eur_per_m2, 2);
check('marge par défaut quand le champ est vide', p.margin_pct, 6);
check('prix de vente', p.sell_price_eur_m2, 2.12);
check('les parts font 100 %', p.components.reduce((a, c) => a + c.share_pct, 0), 100);
check('composition complète', !!p.incomplet, false);

ctx.S.formMsProduct.custom_margin_pct = '20';
ctx.refreshMsProductPreview();
check('la marge saisie prend le pas', ctx.S.msProdPreview.margin_pct, 20);
check('prix de vente avec marge propre', ctx.S.msProdPreview.sell_price_eur_m2, 2.4);

// Une matière sans coût ne doit pas passer pour gratuite en silence.
ctx.S.formMsProduct = { code: '', designation: '', roles: { FRONTAL: 5 }, autres: [11], custom_margin_pct: '' };
ctx.refreshMsProductPreview();
check('une matière non paramétrée est signalée', ctx.S.msProdPreview.incomplet, true);
check('et ne fausse pas le total affiché', ctx.S.msProdPreview.total_eur_per_m2, 1.5);

ctx.S.formMsProduct = ctx.defaultMsProductForm();
ctx.refreshMsProductPreview();
check("sans composant, pas d'aperçu", ctx.S.msProdPreview, null);

// ─── Cohérence avec le reste du fichier ─────────────────────────────────────
check('onglets sur la page Produits', src.includes('data-ptab="mystock"'), true);
check('trois emplacements nommés (MyStock n\'a pas de silicone)', ctx.MSP_ROLES.length, 3);
check('pas de rôle silicone', ctx.MSP_ROLES.some((r) => r.role === 'SILICONE'), false);
const save = extraire('saveMsProductForm');
for (const champ of ['code', 'designation', 'composants', 'custom_margin_pct']) {
  check('champ envoyé : ' + champ, save.includes(champ + ':'), true);
}
check('création en POST', save.includes('method: "POST"'), true);
check('modification en PATCH', save.includes('method: "PATCH"'), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
