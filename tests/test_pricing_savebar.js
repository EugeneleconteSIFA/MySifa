// Bandeau d'enregistrement de la fiche matière (Coûts matières).
// Lancer : node tests/test_pricing_savebar.js
// (les tests Python de ce dossier ne voient pas le JS : ces deux fichiers
//  couvrent le rendu côté navigateur, sans navigateur.)
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8').replace(/\r\n/g, '\n');

// On extrait matSaveBarHtml + icon et on les exécute isolément.
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

const ctx = { S: {} };
vm.createContext(ctx);
vm.runInContext(extraire('icon') + '\n' + extraire('matSaveBarHtml'), ctx);

function html(opts) { Object.assign(ctx.S, opts.S); return ctx.matSaveBarHtml(opts.isNew); }

let ko = 0;
function check(label, got, attendu) {
  const ok = got === attendu;
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(56) + got + (ok ? '' : '   attendu ' + attendu));
}

const edition = html({ isNew: false, S: { canWrite: true, matDirty: false } });
check('un seul bouton Enregistrer', (edition.match(/id="btn-save-mat"/g) || []).length, 1);
check('un seul bouton Supprimer', (edition.match(/id="btn-del-mat"/g) || []).length, 1);
check('un seul retour liste', (edition.match(/id="btn-back-mat"/g) || []).length, 1);
check('bandeau propre au chargement', edition.includes('id="mat-dirty" hidden'), true);

const sale = html({ isNew: false, S: { canWrite: true, matDirty: true } });
check('drapeau visible si saisie en cours', sale.includes('id="mat-dirty"><span'), true);

const creation = html({ isNew: true, S: { canWrite: true, matDirty: false } });
check('pas de Supprimer sur une création', creation.includes('btn-del-mat'), false);
check('Enregistrer présent sur une création', creation.includes('btn-save-mat'), true);

const lecture = html({ isNew: false, S: { canWrite: false, matDirty: false } });
check('lecture seule : aucun bouton d\'écriture',
  lecture.includes('btn-save-mat') || lecture.includes('btn-del-mat'), false);
check('lecture seule : retour liste conservé', lecture.includes('btn-back-mat'), true);

// Le formulaire ne doit plus porter de second jeu de boutons.
const zone = src.slice(src.indexOf('function renderMaterialForm('), src.indexOf('function saveMaterialForm('));
check('les boutons ne sont plus dans le corps du formulaire',
  zone.includes('id="btn-save-mat"') || zone.includes('id="btn-del-mat"'), false);
check('un seul btn-save-mat dans tout le fichier', (src.match(/id="btn-save-mat"/g) || []).length, 1);
check('un seul btn-del-mat dans tout le fichier', (src.match(/id="btn-del-mat"/g) || []).length, 1);
check('un seul btn-back-mat dans tout le fichier', (src.match(/id="btn-back-mat"/g) || []).length, 1);
check('plus de bloc form-actions dans la fiche matière', zone.includes('class="form-actions"'), false);

// Le drapeau doit être remis à zéro au chargement ET après un enregistrement.
check('drapeau remis à zéro au chargement', /loadMaterialForm\(id\)\s*\{\s*S\.matDirty = false;/.test(src), true);
check('drapeau remis à zéro après enregistrement',
  src.includes('showToast("Matière enregistrée.", "success");\n        S.matDirty = false;'), true);

// ─── Le bandeau reste visible en permanence (position:fixed) ────────────────
// En `sticky`, le bandeau ne colle qu'à l'intérieur de son conteneur ; en haut
// de fiche il se laissait recouvrir. En `fixed`, il flotte — d'où l'espaceur
// qui lui réserve sa hauteur, sinon il masque le haut de la page.
const css = fs.readFileSync('static/pricing_app.css', 'utf8').replace(/\r\n/g, '\n');
const regleBar = css.slice(css.indexOf('.pr-savebar{'), css.indexOf('}', css.indexOf('.pr-savebar{')));
check('le bandeau est fixe', regleBar.includes('position:fixed'), true);
check('il n\'est plus seulement collant', regleBar.includes('position:sticky'), false);
check('son fond est opaque', regleBar.includes('background-color:var(--card)'), true);
check('l\'espaceur a une hauteur de repli', /\.savebar-spacer\{height:\d+px\}/.test(css), true);
check('chaque bandeau a son espaceur',
  (src.match(/class="savebar-spacer"/g) || []).length,
  (src.match(/class="pr-savebar"/g) || []).length);

// Sorti du flux, le bandeau recouvre ce qui est en tête de page : l'espaceur
// doit donc précéder le titre, pas le suivre.
for (const [nom, borneFin] of [
  ['renderMaterialForm(', 'function syncMaterialFormFromDom('],
  ['renderDeclinaisonForm(', 'async function saveDeclinaisonForm('],
]) {
  const zone = src.slice(src.indexOf('function ' + nom), src.indexOf(borneFin));
  check(nom + ' : le bandeau précède le titre',
    zone.indexOf('SaveBarHtml(') < zone.indexOf('${pageHead('), true);
}

// L'espaceur reprend la hauteur réelle du bandeau (il passe sur deux lignes en
// écran étroit) : sans ça, la hauteur de repli suffirait rarement.
check('la hauteur de l\'espaceur est resynchronisée',
  src.includes('function syncSavebarSpacer()') && src.includes('syncSavebarSpacer();'), true);
check('l\'observateur précédent est débranché',
  /S\.savebarRO\.disconnect\(\)/.test(src), true);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
