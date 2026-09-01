// Vue « Produits MyStock » (Coûts matières) : routes, composition, aperçu du coût.
// Lancer : node tests/test_pricing_produits_mystock.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8').replace(/\r\n/g, '\n');
const svcProd = fs.readFileSync('app/services/mystock_produits.py', 'utf8').replace(/\r\n/g, '\n');
const api = fs.readFileSync('app/routers/pricing.py', 'utf8').replace(/\r\n/g, '\n');
const svc = fs.readFileSync('app/services/mystock_prix.py', 'utf8').replace(/\r\n/g, '\n');
const css = fs.readFileSync('static/pricing_app.css', 'utf8');

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

/** Constante objet : on suit les accolades plutôt que de deviner la fin. */
function constanteObjet(nom) {
  const i = src.indexOf('const ' + nom + ' =');
  if (i < 0) throw new Error('introuvable : ' + nom);
  let prof = 0;
  const debut = src.indexOf('{', i);
  for (let j = debut; j < src.length; j++) {
    if (src[j] === '{') prof++;
    else if (src[j] === '}') { prof--; if (!prof) return src.slice(i, j + 2); }
  }
  throw new Error('accolades non fermées : ' + nom);
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
// Depuis le 31/08/2026, un emplacement porte la matière ET ce que le produit en
// consomme : le grammage a quitté la matière, où il n'avait rien à faire — un
// adhésif ne s'achète pas plus cher en 22 g/m² qu'en 17.
const slot = (id, gram, perte) => ({
  id: id,
  gram: gram == null ? '' : String(gram),
  perte: perte == null ? '' : String(perte),
});

ctx.S.formMsProduct = {
  code: 'X', designation: 'Y',
  roles: { FRONTAL: slot(5), GLASSINE: slot(9) },
  autres: [slot(11, 22, 9), slot('')],
  custom_margin_pct: '',
};
check("les rôles nommés sortent dans l'ordre", ctx.msProductComposants(), [
  { declinaison_id: 5, role: 'FRONTAL', grammage_gsm: null, perte_pct: null },
  { declinaison_id: 9, role: 'GLASSINE', grammage_gsm: null, perte_pct: null },
  { declinaison_id: 11, role: 'AUTRE', grammage_gsm: 22, perte_pct: 9 },
]);
check("un emplacement vide n'est pas envoyé",
  ctx.msProductComposants().some((c) => c.role === 'ADHESIF'), false);
check('la consommation voyage avec le composant',
  ctx.msProductComposants().find((c) => c.declinaison_id === 11).grammage_gsm, 22);
check('un composant sans grammage envoie null, pas zéro',
  ctx.msProductComposants().find((c) => c.declinaison_id === 5).grammage_gsm, null);
ctx.S.formMsProduct = ctx.defaultMsProductForm();
check("un produit vierge n'a aucun composant", ctx.msProductComposants(), []);

// ─── L'aperçu passe par le moteur, plus par le navigateur ───────────────────
// Il additionnait les coûts déjà chiffrés par l'API pour chaque matière. Ça ne
// tient plus : le coût d'un composant au kilo dépend d'un poids qu'on vient de
// taper, et le refaire ici supposerait d'y réimplémenter transport, taxes et
// change — trois occasions de diverger du moteur.
const apercu = extraire('demanderApercuMsProduct');
check("l'aperçu appelle le serveur",
  apercu.includes('/api/pricing/mystock/produits/preview'), true);
check('il envoie la composition et la marge',
  apercu.includes('composants: comps') && apercu.includes('custom_margin_pct'), true);
check('une réponse en retard est jetée', apercu.includes('serie !== mspApercuSerie'), true);
check('la frappe est différée',
  extraire('refreshMsProductPreview').includes('setTimeout'), true);
check("la route d'aperçu existe côté serveur",
  api.includes('@router.post("/api/pricing/mystock/produits/preview")'), true);
check("elle ne demande que le droit de lire",
  /produits\/preview"\)[^]*?_require_read\(request\)/.test(api), true);

// Un composant au kilo sans grammage compte pour 0 : le total reste crédible,
// et c'est exactement ce qui le rend dangereux. L'écran doit le dire.
check('les composants sans grammage sont comptés',
  extraire('peindreApercuMsProduct').includes('sans grammage'), true);
check('le service met le poids du composant dans le moteur',
  /def cout_produit[^]{0,1500}poids_retenu\(c\.get\("grammage_gsm"\)/.test(svcProd), true);
check('et ne réutilise pas celui de la matière',
  /def cout_produit[^]{0,1500}"weight_per_m2": poids_retenu/.test(svcProd), true);

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
  extraire('supportCle'), constanteObjet('SUPPORT_LABELS'),
  extraire('supportBadge'), extraire('msProductComp'),
  extraire('msProductCompLabel'), extraire('msProductGrammage'),
  extraire('msProductSupport'),
  extraire('msProductSupportTexte'), extraire('msProductDetailHtml'),
  'globalThis.CUR_SYM = {EUR:"\u20ac",USD:"$"};',
].join('\n'), ctx);

const produit = {
  id: 1, code: '886-0001', designation: 'Thermique Pro 70g',
  composants: [
    { role: 'FRONTAL', reference: '70gsm TOP Thermal', libelle: 'Toutes déclinaisons' },
    { role: 'ADHESIF', reference: '1408', libelle: '22 g/m²', grammage_gsm: 22, perte_pct: 9 },
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

// La cellule d'un composant ne porte plus que sa reference : le grammage a sa
// propre colonne, et l'ecrire aux deux endroits ferait chercher lequel des deux
// fait foi le jour ou ils different.
check('la cellule ne porte que la référence',
  ctx.msProductCompLabel(produit, 'FRONTAL'), '70gsm TOP Thermal');
check('plus de grammage dans la cellule adhésif',
  ctx.msProductCompLabel(produit, 'ADHESIF').includes('g/m²'), false);
check('un emplacement vide reste neutre',
  ctx.msProductCompLabel(produit, 'GLASSINE').includes('—'), true);
// C'est LUI qui separe quatre produits portant le meme 2028Y.
check('le grammage sort dans sa propre colonne', ctx.msProductGrammage(produit), 22);
check('et vaut null quand il manque',
  ctx.msProductGrammage({ composants: [{ role: 'ADHESIF', reference: 'X' }] }), null);

console.log('\n--- le support remplace le code ---');
// 886-0001 n'apprend rien qu'on cherche du regard ; le support, si. Le code
// reste dans la recherche, sur la fiche et en infobulle — il quitte
// l'affichage, pas l'usage.
const liste = src.slice(src.indexOf('function renderMsProductsList('));
const declProd = liste.slice(liste.indexOf('const COLS = ['), liste.indexOf('];'));
check('plus de colonne Code', /cle: "code"/.test(declProd), false);
// La designation recopiait en prose, sur trois lignes, ce que les colonnes
// disent en un coup d'oeil : un produit fini EST sa composition.
check('plus de colonne Désignation', /cle: "des"/.test(declProd), false);
check('une colonne Support a la place', /cle: "support"/.test(declProd), true);
check('et une colonne Grammage', /cle: "gram"/.test(declProd), true);
check('le grammage se filtre par choix', /cle: "gram"[^]{0,300}filtre: "choix"/.test(declProd), true);
check('avec son unité dans la liste', declProd.includes('g/m²'), true);
// Ni le code ni la designation ne sont perdus : la recherche porte sur les
// deux cote serveur, et la ligne les montre au survol.
check('la recherche porte encore sur les deux',
  api.includes('code LIKE ? OR designation LIKE ?')
  || svcProd.includes('code LIKE ? OR designation LIKE ?'), true);
check('la ligne les donne au survol',
  liste.includes('title="${escAttr((p.code || "") + " — " + (p.designation || ""))}"'), true);
// Le badge reprend les teintes de MyStock : deux applications qui parlent du
// meme papier doivent lui donner la meme couleur.
check('le support sort en badge',
  ctx.msProductSupport({ composants: [{ role: 'FRONTAL', sous_section: 'thermiques',
    categorie: 'frontal' }] }).includes('mps-support-thermiques'), true);
check('avec le libelle lisible',
  ctx.msProductSupport({ composants: [{ role: 'FRONTAL', sous_section: 'thermiques',
    categorie: 'frontal' }] }).includes('Thermique'), true);
check('les accents ne cassent pas la classe',
  ctx.supportCle('Synthétique'), 'synthetique');
// Sans sous-section, on retombe sur la categorie : mieux vaut « frontal » que
// rien du tout sur une ligne dont le support n'est pas renseigne.
check('repli sur la categorie',
  ctx.msProductSupport({ composants: [{ role: 'FRONTAL', categorie: 'frontal' }] })
    .includes('mps-support-cat-frontal'), true);
check('aucun frontal : rien a afficher',
  ctx.msProductSupport({ composants: [] }), '');
check('les teintes sont celles de MyStock',
  css.includes('.mps-support-thermiques') && css.includes('#4f46e5'), true);
check('le serveur envoie la sous-section',
  svcProd.includes('mp.sous_section') && svcProd.includes('"sous_section": r["sous_section"]'), true);

console.log('\n--- trier et filtrer la liste des produits ---');
check('les en-tetes sont engendres', liste.includes('enTetesTriables("produits"'), true);
check('et branches', liste.includes('bindEnTetes("produits"'), true);
check('le support se filtre par choix', /cle: "support"[^]{0,140}filtre: "choix"/.test(declProd), true);
check('le cout se trie sur sa valeur', declProd.includes('total_eur_per_m2'), true);
check('un produit sans cout ne remonte pas en tete', declProd.includes(': null'), true);

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
// La cellule qui CONTIENT le détail doit être couverte, sinon la règle
// générique `table.pr-table tr:hover td` la teinte au passage de la souris.
check('la cellule conteneur est protégée',
  css.includes('table.pr-table tr.msp-detail-row:hover td'), true);
check('les lignes du détail aussi',
  css.includes('tr.msp-detail-row table.msp-detail tr:hover td'), true);

// ─── « Ce qui fait bouger ce coût » : laize et grammage ─────────────────────
//
// Le prix d'achat d'une matiere ne depend ni de sa laize ni de son grammage :
// on l'achete au m² ou au kilo. Le cout d'un PRODUIT, lui, depend du grammage
// — une matiere payee au kilo coute au m² son prix multiplie par son poids au
// m², et ce poids EST le grammage majore de la perte. La laize, elle, ne
// change rien au €/m² : elle joue sur les QUANTITES consommees, chiffrees
// dans Besoins matieres.
//
// Ce bloc existe pour que la difference se lise a l'ecran plutot que de se
// deviner. Ces cas verrouillent qu'il dise bien l'un ET l'autre.

console.log('\n--- le serveur expose les leviers ---');
check('la laize voyage avec la declinaison', svc.includes('"laize_mm": _f(r["valeur_mm"])'), true);
[['price_basis'], ['grammage_gsm'], ['perte_pct'], ['weight_per_m2'], ['laize_mm']].forEach(([champ]) => {
  check('le selecteur de declinaisons porte ' + champ,
    api.includes('"' + champ + '": d.get("' + champ + '")')
    || api.includes('"' + champ + '": d.get("' + champ + '"),'), true);
});

console.log('\n--- ce que le bloc dit de chaque composant ---');
const ctx2 = {
  S: {}, console, Math, Number, JSON, parseFloat, parseInt,
  document: { querySelectorAll: () => [], getElementById: () => null },
};
vm.createContext(ctx2);
vm.runInContext([
  extraire('escHtml'), extraire('escAttr'), extraire('fmtNum'), extraire('fmtEurM2'),
  constante('MSP_ROLES'),
  'const CUR_SYM = { EUR: "€", USD: "$" };',
  extraire('fmtPct'), extraire('grammageRetenu'), extraire('msLevierBlocHtml'),
  'globalThis.MSP_ROLES = MSP_ROLES;',
].join('\n'), ctx2);

// Un adhesif paye au kilo : c'est le grammage POSE PAR LE PRODUIT qui fait le
// cout au m². La matiere ne porte plus que son prix — 31/08/2026.
const adh = { id: 90, matiere_id: 1, reference: '1408', designation: 'Adhesif enlevable',
  price_basis: 'PER_KG', unit_price: 4.2, fournisseur_id: 7, fournisseur_nom: 'Meltavis' };
// Un frontal paye au m² : la quantite posee ne change pas son cout au m².
const pp = { id: 92, matiere_id: 2, reference: 'PP90', designation: 'PP blanc',
  price_basis: 'PER_M2', unit_price: 0.08 };
ctx2.S.msDecls = [adh, pp];
// La decomposition arrive avec le cout : sans elle, l'ecran affichait
// « 4,200 EUR/kg x 0,0240 kg/m2 -> 0,1098 EUR/m2 », une multiplication qui ne
// tombe pas juste parce que le transport y etait fondu sans etre nomme.
ctx2.S.msProdPreview = { components: [
  { material_id: 90, price_eur_per_m2: 0.1098, breakdown: {
      currency: 'EUR', price_basis: 'PER_KG', fx_rate: 1,
      unit_price_src: 4.2, transport_src: 0.3788, taxes_src: 0,
      subtotal_src: 4.5788, transport_eur_m2: 0.0091,
      transport_pct_effective: 9.02, taxe_pct: 0 } },
  { material_id: 92, price_eur_per_m2: 0.11, breakdown: {
      currency: 'EUR', price_basis: 'PER_M2', fx_rate: 1,
      unit_price_src: 0.11, transport_src: 0, taxes_src: 0,
      subtotal_src: 0.11, transport_eur_m2: 0, transport_pct_effective: 0, taxe_pct: 0 } },
] };

const bAdh = ctx2.msLevierBlocHtml(
  { declinaison_id: 90, role: 'ADHESIF', grammage_gsm: 22, perte_pct: 9 }, 'Adhésif');
const bPP = ctx2.msLevierBlocHtml(
  { declinaison_id: 92, role: 'FRONTAL', grammage_gsm: null, perte_pct: null }, 'Frontal');
const bVide = ctx2.msLevierBlocHtml(
  { declinaison_id: 90, role: 'ADHESIF', grammage_gsm: null, perte_pct: null }, 'Adhésif');

check('au kilo : la chaine complete est montree',
  bAdh.includes('€/kg') && bAdh.includes('kg/m²') && bAdh.includes('0,1098'), true);

console.log('\n--- le transport est nomme, plus fondu dans le resultat ---');
// 4,200 + 0,379 = 4,579 EUR/kg, x 0,0240 kg/m2 = 0,1098. La multiplication
// tombe juste parce que TOUS ses termes sont a l'ecran.
check('le prix nu est montre', bAdh.includes('4,200'), true);
check('le transport aussi', bAdh.includes('0,379') && bAdh.includes('transport'), true);
check('et le sous-total qui en resulte', bAdh.includes('4,579'), true);
check('le transport a sa propre precision',
  /9,02\s%/.test(bAdh) && bAdh.includes("du prix d'achat"), true);
check('et sa part sur CE produit', bAdh.includes('0,0091'), true);
check('avec le chemin pour le corriger', bAdh.includes('tarif fournisseur'), true);
check('un composant sans transport ne l\'invente pas',
  bPP.includes('transport'), false);
check('le serveur envoie la decomposition',
  /_cout_produit_mystock[^]*?breakdown=\(/.test(api), true);
check('la part de transport a sa ligne dans le recap',
  extraire('transportRecapHtml').includes('dont transport'), true);
check('et sa colonne dans le detail deplie', src.includes('msp-transp'), true);

console.log('\n--- la part de transport DANS chaque jauge ---');
// Le transport n'est pas un composant de plus : il vit dans le prix de chaque
// matiere. Il prend donc la fin du segment auquel il appartient, jamais un
// segment a lui — sinon il serait compte deux fois et suggererait une
// quatrieme matiere.
const bk = extraire('priceBreakdownHtml');
check('le segment porte sa part de transport', bk.includes('seg-transport'), true);
check('calculee sur le cout de CE composant',
  bk.includes('(t / v) * 100'), true);
check('la hachure est expliquee', bk.includes('part de transport, comprise dans le co'), true);
check('et seulement s\'il y a du transport', bk.includes('aDuTransport'), true);
check('la jauge de la colonne Part fait pareil',
  src.includes('transpPart') && src.includes('(transp / prix) * 100'), true);
// La hachure est faite avec --text : elle bascule avec le theme. Un noir fixe
// disparaissait en thème sombre, ou le repere se confondait avec la piste vide.
check('la hachure suit le theme',
  /\.seg-transport\{[^}]*var\(--text\)/.test(css), true);
check('le repere de la jauge aussi',
  /\.msp-jauge i b\{[^}]*var\(--text\)/.test(css), true);
check('le poids vient du grammage du PRODUIT',
  bAdh.includes('le grammage de ce produit') && bAdh.includes('22 g/m²'), true);
check('la perte y est comptee', bAdh.includes('9 % de perte'), true);
check('et le prix d\'achat est dit hors de cause',
  bAdh.includes("sans toucher au prix d'achat"), true);
check('au m² : la quantite posee est declaree hors jeu',
  bPP.includes('ne change pas ce coût au m²'), true);
check('sans grammage, le composant est annonce a zero',
  bVide.includes('compte pour <strong>0</strong>'), true);

console.log('\n--- les declinaisons voisines ne sont plus proposees ---');
// Comparer un 17 et un 22 g/m² se fait maintenant en changeant le grammage
// dans le champ : le total suit a la frappe, sans changer de matiere.
check('plus de pastille de bascule', bAdh.includes('data-msp-switch'), false);
check('plus de notion de declinaison voisine', bAdh.includes('Autres déclinaisons'), false);
check('la laize a disparu du bloc', bPP.includes('sans effet'), false);


console.log('\n--- cable des deux cotes ---');
check('le bloc est pose dans le formulaire', src.includes('id="msp-leviers"'), true);
check('il suit l\'apercu', src.includes('lev.innerHTML = msProductLeviersHtml();'), true);
check('le bloc a son style', css.includes('.msp-lev{'), true);

console.log('\n--- la consommation se saisit sur l\'emplacement ---');
// Le grammage vit sous la matiere qui le concerne, dans la fiche produit.
check('un emplacement porte ses champs de consommation',
  src.includes('data-msp-gram=') && src.includes('data-msp-perte='), true);
check('le poids retenu est affiche en clair', src.includes('Poids retenu'), true);
check('les champs n\'apparaissent que sur un achat au kilo',
  /function mspSlotHtml[^]*?perKg\s*\?/.test(src), true);
check('taper un grammage ne redessine pas le formulaire',
  src.includes('data-msp-gram], [data-msp-perte]') && src.includes('inp.oninput = majAperçu'), true);
check('le style de l\'emplacement existe', css.includes('.msp-conso{'), true);

console.log('\n--- les fiches matiere ne parlent plus de grammage ---');
check('plus de section Caracteristiques', src.includes('<h3>Caractéristiques</h3>'), false);
check('plus de champ grammage cote matiere',
  src.includes('id="f-gsm"') || src.includes('id="d-gsm"'), false);
check('la fiche declinaison n\'envoie plus de grammage',
  extraire('saveDeclinaisonForm').includes('grammage_gsm'), false);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
