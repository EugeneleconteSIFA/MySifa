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
vm.runInContext([extraire('parseRoute'), extraire('icon'),
                 extraire('heureCourte'), extraire('saveStatusHtml'),
                 extraire('declSaveBarHtml')].join('\n'), ctx);

function route(p) { ctx.window.location.pathname = p; return ctx.parseRoute(); }
check('une déclinaison ouvre sa fiche', route('/pricing/mystock/12'), { name: 'mystock-edit', id: '12' });
// Plus de tableau de bord : la liste des matières est la page d'accueil.
check('sans identifiant on retombe sur la liste',
  route('/pricing/mystock'), { name: 'materials', id: null });
check('un identifiant non numérique est refusé',
  route('/pricing/mystock/abc'), { name: 'materials', id: null });
check('la racine du module ouvre les matières',
  route('/pricing'), { name: 'materials', id: null });
check('plus de route tableau de bord', src.includes('renderDashboard'), false);
check('les routes existantes ne bougent pas',
  route('/pricing/materials/7'), { name: 'material-edit', id: '7' });

// ─── Bandeau d'enregistrement — pastille automatique ────────────────────────
// Plus de bouton « Enregistrer » : la saisie s'écrit à la volée. La pastille
// dit où on en est (vierge / attente / cours / ok / err), pas d'action à
// prendre par l'utilisateur pour valider ce qu'il vient de taper.
ctx.S = { canWrite: true, declSaveStatus: "vierge", declSavedAt: null,
          declForm: { matiere_id: 42 } };
let bar = ctx.declSaveBarHtml();
check('plus de bouton Enregistrer', bar.includes('id="btn-save-decl"'), false);
check('retour liste présent', bar.includes('id="btn-back-decl"'), true);
check('lien vers MyStock sur la bonne matière', bar.includes('matiere=42'), true);
check('pastille au chargement : Aucune modification',
  bar.includes('Aucune modification'), true);

ctx.S.declSaveStatus = "attente";
check('pastille pendant la frappe : attente',
  ctx.declSaveBarHtml().includes('Modifications non enregistrées'), true);
ctx.S.declSaveStatus = "cours";
check('pastille pendant le PATCH : Enregistrement…',
  ctx.declSaveBarHtml().includes('Enregistrement'), true);
ctx.S.declSaveStatus = "ok"; ctx.S.declSavedAt = new Date(2026, 8, 3, 14, 7);
check('pastille après succès : heure de sauvegarde',
  ctx.declSaveBarHtml().includes('14:07'), true);
ctx.S.declSaveStatus = "err";
check('pastille après échec : Erreur — réessayer',
  ctx.declSaveBarHtml().includes('Erreur'), true);

ctx.S = { canWrite: false, declSaveStatus: "vierge", declForm: { matiere_id: 42 } };
check('lecture seule : bar sans action d\'écriture',
  ctx.declSaveBarHtml().includes('btn-save-decl'), false);

// ─── L'appairage a bien disparu de l'interface ──────────────────────────────
check('plus de bouton appairer', /data-ms-pair|data-ms-unpair/.test(src), false);
check('plus de modale d\'appairage', src.includes('openAppairageModal'), false);
// Le 31/08/2026, le coût €/m² quitte la liste des matières : c'est un résultat
// de paramétrage, il se lit et se règle sur la fiche. La liste ne sert plus
// qu'à corriger un prix d'achat, et la fiche reste à un clic.
const vueListe = src.slice(src.indexOf('function renderMystockList('), src.indexOf('function bindMsPrixInline('));
check('plus de colonne Coût €/m² dans la liste', /Coût €\/m²/.test(vueListe), false);
check('la fiche reste le chemin vers le paramétrage',
  src.includes('href="/pricing/mystock/${decls[0].id}"'), true);

// ─── L'enregistrement automatique envoie ce que l'API attend ─────────────────
const save = extraire('autoEnregistrerDecl');
for (const champ of ['price_currency', 'price_basis', 'taxe_pct', 'is_imported',
                     'applique_marge', 'transport_mode', 'transport_unit_price',
                     'transport_pct']) {
  check('champ envoyé : ' + champ, save.includes(champ + ':'), true);
}
// Le grammage a quitté la matière le 31/08/2026 : il se saisit sur le composant
// du produit. L'envoyer d'ici ne serait pas seulement inutile — sur un adhésif,
// il DÉPLACE la déclinaison (set_declinaison_valeur).
for (const champ of ['grammage_gsm', 'perte_pct']) {
  check('champ retiré : ' + champ, save.includes(champ + ':'), false);
}
check('méthode PATCH', save.includes("method: \"PATCH\""), true);
check('débounce d\'écriture', save.includes('DELAI_SAVE_MS'), true);
check('la pastille passe à « cours »', save.includes('setDeclSaveStatus("cours")'), true);
check('puis à « ok » sur succès', save.includes('setDeclSaveStatus("ok")'), true);
check('à « err » sur erreur', save.includes('setDeclSaveStatus("err")'), true);
// Le poids n'est plus saisi : il découle du grammage et de la perte.
check('plus de poids envoyé à la main', save.includes('weight_per_m2'), false);

// ─── Historique des prix ────────────────────────────────────────────────────
vm.runInContext([
  extraire('escHtml'), extraire('fmtNum'), extraire('fmt4'),
  extraire('fmtDateHeure'), extraire('declHistoriqueHtml'),
].join('\n'), ctx);

check('date lisible', ctx.fmtDateHeure('2026-08-05T07:42:11'), '05/08/2026 · 07:42');
check('date absente sans plantage', ctx.fmtDateHeure(null), '');

const vide = ctx.declHistoriqueHtml([]);
check('historique vide : message clair', vide.includes('Aucun mouvement'), true);
check('et pas de tableau', vide.includes('<table'), false);

const hist = ctx.declHistoriqueHtml([
  { date: '2026-08-05T07:42:11', origine: 'MyStock — valorisation', auteur: 'Eugene',
    fournisseur_nom: 'Meltavis', prix_avant: 2.0, prix_apres: 2.31,
    sous_total_avant: 2.0, sous_total_apres: 2.31, note: null },
  { date: '2026-08-04T09:00:00', origine: 'Coûts matières — paramétrage', auteur: 'Eugene',
    prix_avant: 2.0, prix_apres: 2.0, sous_total_avant: 2.0, sous_total_apres: 2.12,
    note: 'transport / taxes modifiés' },
  { date: '2026-08-03T08:00:00', origine: 'Coûts matières', auteur: null,
    prix_avant: 2.5, prix_apres: 2.0, sous_total_apres: 2.0, note: null },
]);
for (const attendu of ['MyStock — valorisation', 'Coûts matières — paramétrage',
                       'Eugene', 'Meltavis', 'transport / taxes modifiés',
                       '05/08/2026', 'Sous-total']) {
  check('historique montre : ' + attendu, hist.includes(attendu), true);
}
check('une hausse est signalée', hist.includes('hist-hausse'), true);
check('une baisse aussi', hist.includes('hist-baisse'), true);
check('un prix inchangé n\'est ni l\'un ni l\'autre',
  (hist.match(/hist-hausse|hist-baisse/g) || []).length, 2);
check('auteur inconnu reste neutre', hist.includes('—'), true);
check('les balises sont équilibrées',
  (hist.match(/<td/g) || []).length, (hist.match(/<\/td>/g) || []).length);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
