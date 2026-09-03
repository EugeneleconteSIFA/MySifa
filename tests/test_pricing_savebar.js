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
vm.runInContext([extraire('icon'), extraire('heureCourte'),
                 extraire('saveStatusHtml'), extraire('matSaveBarHtml')].join('\n'), ctx);

function html(opts) { Object.assign(ctx.S, opts.S); return ctx.matSaveBarHtml(opts.isNew); }

let ko = 0;
function check(label, got, attendu) {
  const ok = got === attendu;
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(56) + got + (ok ? '' : '   attendu ' + attendu));
}

// Une matière existante s'enregistre pendant qu'on la modifie : plus de
// bouton « Enregistrer », plus de « Modifications non enregistrées » à
// gérer. La pastille dit où on en est.
const edition = html({ isNew: false, S: { canWrite: true, matSaveStatus: "vierge", matSavedAt: null } });
check('plus de bouton Enregistrer sur une matière existante',
  edition.includes('id="btn-save-mat"'), false);
check('un seul bouton Supprimer', (edition.match(/id="btn-del-mat"/g) || []).length, 1);
check('un seul retour liste', (edition.match(/id="btn-back-mat"/g) || []).length, 1);
check('pastille au chargement : Aucune modification',
  edition.includes('Aucune modification'), true);

const enFrappe = html({ isNew: false, S: { canWrite: true, matSaveStatus: "attente" } });
check('pastille pendant la frappe', enFrappe.includes('Modifications non enregistrées'), true);
const enCours = html({ isNew: false, S: { canWrite: true, matSaveStatus: "cours" } });
check('pastille pendant le PATCH', enCours.includes('Enregistrement'), true);
const succes = html({ isNew: false, S: { canWrite: true, matSaveStatus: "ok",
                                          matSavedAt: new Date(2026, 8, 3, 9, 42) } });
check('pastille après succès : heure', succes.includes('09:42'), true);
const echec = html({ isNew: false, S: { canWrite: true, matSaveStatus: "err" } });
check('pastille après échec : Erreur', echec.includes('Erreur'), true);

// Une matière neuve n'a pas d'ID : on ne peut pas PATCH, il faut d'abord
// POST. D'où le bouton « Créer » — la pastille suit ensuite.
const creation = html({ isNew: true, S: { canWrite: true, matSaveStatus: "vierge" } });
check('pas de Supprimer sur une création', creation.includes('btn-del-mat'), false);
check('bouton Créer présent sur une création', creation.includes('id="btn-save-mat"'), true);

const lecture = html({ isNew: false, S: { canWrite: false, matSaveStatus: "vierge" } });
check('lecture seule : aucun bouton d\'écriture',
  lecture.includes('btn-save-mat') || lecture.includes('btn-del-mat'), false);
check('lecture seule : retour liste conservé', lecture.includes('btn-back-mat'), true);

// Le formulaire ne doit plus porter de second jeu de boutons.
const zone = src.slice(src.indexOf('function renderMaterialForm('), src.indexOf('function syncMaterialFormFromDom('));
check('les boutons ne sont plus dans le corps du formulaire',
  zone.includes('id="btn-save-mat"') || zone.includes('id="btn-del-mat"'), false);
check('un seul btn-save-mat dans tout le fichier',
  (src.match(/id="btn-save-mat"/g) || []).length, 1);
check('un seul btn-del-mat dans tout le fichier',
  (src.match(/id="btn-del-mat"/g) || []).length, 1);
check('un seul btn-back-mat dans tout le fichier',
  (src.match(/id="btn-back-mat"/g) || []).length, 1);
check('plus de bloc form-actions dans la fiche matière', zone.includes('class="form-actions"'), false);

// L'état s'initialise proprement au chargement de la fiche.
check('état remis à zéro au chargement',
  /loadMaterialForm\(id\)\s*\{\s*S\.matSaveStatus = "vierge";/.test(src), true);
check('débounce d\'écriture annulé au chargement',
  /loadMaterialForm\(id\)[\s\S]{0,200}clearTimeout\(S\.debounceMatSave\)/.test(src), true);

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
// Le bandeau rouge de staging est fixe lui aussi : le `padding-top` posé sur le
// body décale le flux, pas un élément fixe. Sans règle dédiée, le bandeau
// d'actions passait par-dessus le rouge.
check('le bandeau passe sous celui de staging',
  css.includes('body.has-staging-bandeau .pr-savebar{top:44px}'), true);
check('chaque bandeau a son espaceur',
  (src.match(/class="savebar-spacer"/g) || []).length,
  (src.match(/class="pr-savebar"/g) || []).length);

// Sorti du flux, le bandeau recouvre ce qui est en tête de page : l'espaceur
// doit donc précéder le titre, pas le suivre.
for (const [nom, borneFin] of [
  ['renderMaterialForm(', 'function syncMaterialFormFromDom('],
  ['renderDeclinaisonForm(', 'function productsTabsHtml('],
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
