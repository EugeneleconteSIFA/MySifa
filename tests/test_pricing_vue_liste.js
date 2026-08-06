// Matières MyStock : la vue « liste » (une ligne par déclinaison).
//
// La vue par référence groupe et permet la saisie ; la vue liste met à plat et
// se lit. Ce test vérifie qu'aplatir ne perd rien — surtout pas une référence
// sans déclinaison, qui disparaîtrait de la liste et donc de l'esprit.
//
// Lancer : node tests/test_pricing_vue_liste.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8').replace(/\r\n/g, '\n');
const css = fs.readFileSync('static/pricing_app.css', 'utf8').replace(/\r\n/g, '\n');

function extraire(nom) {
  const i = src.indexOf('function ' + nom + '(');
  if (i < 0) throw new Error('introuvable : ' + nom);
  let prof = 0;
  const debut = src.indexOf('{', i);
  for (let j = debut; j < src.length; j++) {
    if (src[j] === '{') prof++;
    else if (src[j] === '}') { prof--; if (prof === 0) return src.slice(i, j + 1); }
  }
  throw new Error('accolades non fermées : ' + nom);
}

const ctx = { S: { canWrite: true, filters: { msVue: 'reference' }, mystock: [] }, Intl };
vm.createContext(ctx);
vm.runInContext(
  [
    'const DECL_LABEL = { LAIZE: "laize", GRAMMAGE: "grammage" };',
    extraire('icon'), extraire('escHtml'), extraire('escAttr'), extraire('fmtNum'),
    extraire('fmtEurM2'), extraire('fmtPrixUnite'), extraire('categorieBadge'),
    extraire('actionBtn'), extraire('mystockDeclinaisonsAPlat'),
    extraire('mystockFlatRowHtml'), extraire('msVueSwitchHtml'),
  ].join('\n'),
  ctx
);

let ko = 0;
function check(label, got, attendu) {
  const ok = got === attendu;
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(56) + got + (ok ? '' : '   attendu ' + attendu));
}

// Jeu d'essai : une référence à grammages (deux déclinaisons, dont une avec
// plusieurs fournisseurs et une non paramétrée), et une référence orpheline.
ctx.S.mystock = [
  {
    id: 1, reference: '1408', designation: 'Adhésif enlevable fort', categorie: 'adhesif',
    unite: '€/kg', type_declinaison: 'GRAMMAGE',
    declinaisons: [
      {
        id: 90, libelle: '17 g/m²', cout_eur_m2: 0.0885,
        lignes: [
          { fournisseur_id: 3, fournisseur_nom: 'Coquelle', prix: 4.5, principal: false },
          { fournisseur_id: 7, fournisseur_nom: 'Meltavis', prix: 4.2, principal: true },
        ],
      },
      { id: 91, libelle: '', cout_eur_m2: 0, lignes: [] },
    ],
  },
  {
    id: 2, reference: 'GL80', designation: 'Glassine 80', categorie: 'glassine',
    unite: '€/m²', type_declinaison: 'LAIZE', declinaisons: [],
  },
];

const plat = ctx.mystockDeclinaisonsAPlat();

console.log('--- une ligne par déclinaison, sans rien perdre ---');
check('3 lignes pour 2 références', plat.length, 3);
check('la référence sans déclinaison est là', plat.filter(e => e.d === null).length, 1);
check('elle garde sa matière', plat[2].m.reference, 'GL80');

console.log('\n--- le prix affiché est celui qui fait foi ---');
check('principal retenu, pas le premier venu', plat[0].principal.fournisseur_nom, 'Meltavis');
check('les autres fournisseurs sont comptés', plat[0].autres, 1);
// Sans principal désigné, on montre quand même un prix plutôt qu'un tiret.
ctx.S.mystock[0].declinaisons[0].lignes.forEach(l => { l.principal = false; });
check('à défaut, le premier prix connu', ctx.mystockDeclinaisonsAPlat()[0].principal.fournisseur_nom, 'Coquelle');
ctx.S.mystock[0].declinaisons[0].lignes[1].principal = true;

console.log('\n--- ce que la ligne montre ---');
const l0 = ctx.mystockFlatRowHtml(plat[0]);
check('la référence', l0.includes('1408'), true);
check('le grammage', l0.includes('17 g/m²'), true);
check('le fournisseur principal', l0.includes('Meltavis'), true);
check('le prix en vigueur', l0.includes('4,200'), true);
check('le coût au m², mis en avant', l0.includes('msl-cout') && l0.includes('0,0885'), true);
check('le compteur des autres fournisseurs', l0.includes('>+1<'), true);
check('la ligne ouvre la fiche', l0.includes('data-ms-line="90"'), true);

const l1 = ctx.mystockFlatRowHtml(plat[1]);
check('une déclinaison sans valeur le dit', l1.includes('grammage à définir'), true);
check('et se signale non paramétrée', l1.includes('à paramétrer'), true);

const l2 = ctx.mystockFlatRowHtml(plat[2]);
check('la référence orpheline le dit', l2.includes('sans déclinaison'), true);
check('elle n\'est pas cliquable', l2.includes('data-ms-line'), false);
check('elle propose de créer une laize', l2.includes('data-ms-new="2"'), true);

console.log('\n--- rien ne se saisit dans cette vue ---');
[l0, l1, l2].forEach((ligne, i) => {
  check('ligne ' + i + ' : aucun champ de saisie',
    /<input|<select/.test(ligne), false);
});

console.log('\n--- la bascule ---');
ctx.S.filters.msVue = 'reference';
const swRef = ctx.msVueSwitchHtml();
check('deux boutons', (swRef.match(/data-ms-vue=/g) || []).length, 2);
check('un seul actif', (swRef.match(/class="vs-btn on"/g) || []).length, 1);
check('l\'actif est la vue par référence', swRef.includes('class="vs-btn on" data-ms-vue="reference"'), true);
ctx.S.filters.msVue = 'liste';
check('la bascule suit l\'état', ctx.msVueSwitchHtml().includes('class="vs-btn on" data-ms-vue="liste"'), true);
check('les deux ont une infobulle', (ctx.msVueSwitchHtml().match(/title="Vue/g) || []).length, 2);

console.log('\n--- câblage et persistance ---');
check('la bascule est posée dans l\'en-tête',
  src.includes('materialsTabsHtml() + msVueSwitchHtml()'), true);
check('elle est branchée', src.includes('function bindMsVueSwitch()') && src.includes('bindMsVueSwitch();'), true);
check('le choix survit au rechargement',
  src.includes('function chargerVueMystock()') && src.includes('chargerVueMystock();'), true);
check('un stockage refusé ne casse pas la page',
  /function chargerVueMystock\(\)[^]{0,400}catch \(e\)/.test(src), true);
check('la vue par référence reste le défaut', /msVue: "reference"/.test(src), true);
check('la bascule a son style', css.includes('.view-switch{') && css.includes('.vs-btn.on{'), true);

console.log('\n--- tout tient dans la largeur ---');
// Sans largeurs fixées, la désignation s'étale et pousse le coût €/m² hors de
// l'écran — la colonne pour laquelle on ouvre cette vue.
check('les colonnes ont une largeur imposée', css.includes('table.msl-table{table-layout:fixed'), true);
const zoneListe = src.slice(src.indexOf('const plat = S.filters.msVue'), src.indexOf('setContent(`', src.indexOf('const plat = S.filters.msVue')));
check('un colgroup accompagne le tableau', zoneListe.includes('<colgroup>'), true);
check('une largeur par colonne sauf la désignation',
  (zoneListe.match(/<col style="width:/g) || []).length, 7);
check('la désignation est la seule élastique',
  /<col>\s/.test(zoneListe) || zoneListe.includes('<col>'), true);
check('elle se coupe au lieu de pousser',
  css.includes('.msl-des{color:var(--text2);overflow:hidden;text-overflow:ellipsis'), true);
// Texte coupé = texte perdu, sauf si l'infobulle le rend.
check('la désignation garde son infobulle', src.includes('class="msl-des" title="${escAttr(m.designation'), true);
check('la déclinaison aussi', src.includes('title="${escAttr(d.libelle)}"'), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
