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

// ─── Liste dépliable ────────────────────────────────────────────────────────
vm.runInContext([
  extraire('escHtml'), extraire('escAttr'), extraire('fmtNum'),
  extraire('fmtEurM2'), extraire('fmtPct'),
  src.slice(src.indexOf('const MSP_ROLE_LABEL ='),
            src.indexOf('};', src.indexOf('const MSP_ROLE_LABEL =')) + 2),
  extraire('msProductCompLabel'), extraire('msProductDetailHtml'),
  'globalThis.CUR_SYM = {EUR:"\u20ac",USD:"$"};',
].join('\n'), ctx);

const produit = {
  id: 1, code: '886-0001', designation: 'Thermique Pro 70g',
  composants: [
    { role: 'FRONTAL', reference: '70gsm TOP Thermal', libelle: 'Toutes déclinaisons' },
    { role: 'ADHESIF', reference: '1408', libelle: '22 g/m²' },
  ],
  cost: {
    total_eur_per_m2: 0.2993, margin_pct: 6, margin_eur_m2: 0.018,
    sell_price_eur_m2: 0.3173,
    components: [
      { role: 'frontal', name: '70gsm TOP Thermal', price_eur_per_m2: 0.1512, share_pct: 50.52 },
      { role: 'adhesif', name: '1408 — 22 g/m²', price_eur_per_m2: 0.1053, share_pct: 35.18 },
    ],
  },
};

// « Toutes déclinaisons » n'apprend rien : la colonne ne montre que la référence.
check('une matière sans déclinaison affiche sa seule référence',
  ctx.msProductCompLabel(produit, 'FRONTAL'), '70gsm TOP Thermal');
check('une déclinaison porteuse de sens est affichée',
  ctx.msProductCompLabel(produit, 'ADHESIF').includes('22 g/m²'), true);
check('un emplacement vide reste neutre',
  ctx.msProductCompLabel(produit, 'GLASSINE').includes('—'), true);

const detail = ctx.msProductDetailHtml(produit);
for (const attendu of ['Frontal', 'Adhésif', '0,1512', '50,52', 'Prix de revient',
                       'Prix de vente', 'msp-jauge']) {
  check('le détail montre : ' + attendu, detail.includes(attendu), true);
}
check('les balises du détail sont équilibrées',
  (detail.match(/<div/g) || []).length, (detail.match(/<\/div>/g) || []).length);
check('pas de matière sans prix ici', detail.includes('msp-alerte'), false);

// Une matière sans prix ne doit pas passer pour gratuite en silence.
const incomplet = JSON.parse(JSON.stringify(produit));
incomplet.cost.components[1].price_eur_per_m2 = 0;
const detail2 = ctx.msProductDetailHtml(incomplet);
check('une matière sans prix est signalée', detail2.includes('msp-alerte'), true);
check('et dite telle quelle dans la ligne', detail2.includes('sans prix'), true);

const vide = { id: 2, code: 'X', designation: 'Y', composants: [], cost: null };
check('un produit sans coût ne casse pas le rendu',
  ctx.msProductDetailHtml(vide).includes('Aucun coût calculable'), true);

// La jauge ne doit jamais déborder, même sur une part aberrante.
const fou = JSON.parse(JSON.stringify(produit));
fou.cost.components[0].share_pct = 240;
check('la jauge est bornée à 100 %',
  ctx.msProductDetailHtml(fou).includes('width:100%'), true);

check('la ligne déplie, le bouton édite',
  src.includes('data-msp-row') && src.includes('data-msp-edit'), true);

// ─── Actions de la liste ────────────────────────────────────────────────────
check('modifier et dupliquer sont des icônes',
  src.includes('actionBtn("data-msp-edit"') && src.includes('actionBtn("data-msp-dup"'), true);
// Les autres listes gardent leur bouton texte : on ne regarde que celle-ci.
const listeMs = src.slice(src.indexOf('function renderMsProductsList('),
                          src.indexOf('function saveMsProductForm('));
check('plus de bouton texte dans cette liste', listeMs.includes('>Éditer</button>'), false);
check('la duplication ouvre le formulaire de création',
  src.includes('navigate("/pricing/mystock/produit/new")'), true);
check('le formulaire pré-rempli survit au chargement',
  src.includes('if (!S.formMsProduct) S.formMsProduct = defaultMsProductForm();'), true);
const dup = src.slice(src.indexOf('data-msp-dup]'), src.indexOf('data-msp-mat]'));
for (const champ of ['code:', 'designation:', 'roles', 'autres', 'custom_margin_pct:']) {
  check('la copie reprend : ' + champ, dup.includes(champ), true);
}
check('le code copié est signalé', dup.includes('"-copie"'), true);

// ─── Aucun survol coloré dans la zone dépliée ───────────────────────────────
const css = fs.readFileSync('static/pricing_app.css', 'utf8');
// La cellule qui CONTIENT le détail doit être couverte, sinon la règle
// générique `table.pr-table tr:hover td` la teinte au passage de la souris.
check('la cellule conteneur est protégée',
  css.includes('table.pr-table tr.msp-detail-row:hover td'), true);
check('les lignes du détail aussi',
  css.includes('tr.msp-detail-row table.msp-detail tr:hover td'), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
