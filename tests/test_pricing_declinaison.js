// Fiche de paramétrage d'une déclinaison MyStock (Coûts matières).
// Lancer : node tests/test_pricing_declinaison.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8').replace(/\r\n/g, '\n');

function extraire(nom) {
  const i = src.indexOf('function ' + nom + '(');
  if (i < 0) throw new Error('introuvable : ' + nom);
  let prof = 0, debut = src.indexOf('{', i);
  for (let j = debut; j < src.length; j++) {
    if (src[j] === '{') prof++;
    else if (src[j] === '}') { prof--; if (prof === 0) return src.slice(i, j + 1); }
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

// ─── Route ──────────────────────────────────────────────────────────────────
const ctx = { window: { location: { pathname: '/' } }, S: {}, console };
vm.createContext(ctx);
vm.runInContext(extraire('parseRoute') + '\n' + extraire('icon') + '\n' + extraire('declSaveBarHtml'), ctx);

function route(p) { ctx.window.location.pathname = p; return ctx.parseRoute(); }
check('une déclinaison ouvre sa fiche', route('/pricing/mystock/12'), { name: 'mystock-edit', id: '12' });
check('sans identifiant on retombe sur le tableau de bord',
  route('/pricing/mystock'), { name: 'dashboard', id: null });
check('un identifiant non numérique est refusé',
  route('/pricing/mystock/abc'), { name: 'dashboard', id: null });
check('les routes existantes ne bougent pas',
  route('/pricing/materials/7'), { name: 'material-edit', id: '7' });

// ─── Bandeau d'enregistrement ───────────────────────────────────────────────
ctx.S = { canWrite: true, declDirty: false, declForm: { matiere_id: 42 } };
let bar = ctx.declSaveBarHtml();
check('bouton enregistrer présent', bar.includes('id="btn-save-decl"'), true);
check('retour liste présent', bar.includes('id="btn-back-decl"'), true);
check('lien vers MyStock sur la bonne matière', bar.includes('matiere=42'), true);
check('drapeau masqué au chargement', bar.includes('id="decl-dirty" hidden'), true);

ctx.S.declDirty = true;
check('drapeau visible après saisie', ctx.declSaveBarHtml().includes('id="decl-dirty"><span'), true);

ctx.S = { canWrite: false, declDirty: false, declForm: { matiere_id: 42 } };
check('lecture seule : pas de bouton enregistrer',
  ctx.declSaveBarHtml().includes('btn-save-decl'), false);

// ─── L'appairage a bien disparu de l'interface ──────────────────────────────
check('plus de bouton appairer', /data-ms-pair|data-ms-unpair/.test(src), false);
check('plus de modale d\'appairage', src.includes('openAppairageModal'), false);
check('le coût ouvre la fiche', src.includes('data-ms-open="${d.id}"'), true);
check('colonne Coût €/m² dans le tableau', (src.match(/<th>Coût €\/m²<\/th>/g) || []).length, 2);

// ─── Le formulaire envoie bien ce que l'API attend ──────────────────────────
const save = extraire('saveDeclinaisonForm');
for (const champ of ['price_currency', 'price_basis', 'taxe_pct', 'is_imported',
                     'applique_marge', 'transport_mode', 'transport_unit_price',
                     'transport_pct', 'grammage_gsm', 'perte_pct']) {
  check('champ envoyé : ' + champ, save.includes(champ + ':'), true);
}
check('méthode PATCH', save.includes("method: \"PATCH\""), true);
check('drapeau remis à zéro après enregistrement', save.includes('S.declDirty = false'), true);
// Le poids n'est plus saisi : il découle du grammage et de la perte.
check('plus de poids envoyé à la main', save.includes('weight_per_m2'), false);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
