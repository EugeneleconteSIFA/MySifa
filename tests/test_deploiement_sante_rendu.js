// Rendu de la vue « Santé du dépôt » (Paramètres > Promouvoir > Déployer).
// Lancer : node tests/test_deploiement_sante_rendu.js
// (les tests Python de ce dossier ne voient pas le JS : ces deux fichiers
//  couvrent le rendu côté navigateur, sans navigateur.)
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('static/mysifa_promote.js', 'utf8');

const elts = {};
function mk(id) { return elts[id] = { id, innerHTML: '', textContent: '', style: {}, classList: { toggle(){}, add(){}, remove(){} }, dataset: {} }; }
mk('ds-body');

const payload = {
  instance: 'v2', version_app: '2.7.0',
  migrations: {
    appliquees: [
      { cle: 'mp_declinaisons_appairage', nom: 'mp_declinaisons_appairage', date: '2026-08-03T10:12:00', source: 'fichier' },
      { cle: '225', nom: 'mc_transport_pct', date: '2026-08-02T18:00:00', source: 'numérotée' },
    ],
    nb_appliquees: 227, derniere: null,
    en_attente: [{ nom: 'imprimantes_type_connexion_windows_local', fichier: '2026_08_03_imprimantes_windows.py' }],
    nb_fichiers: 4,
    doublons: [{ cle: '195', noms: ['imprimantes_windows', 'autre_migration'] }],
  },
  branches: [
    { nom: 'staging', date: '2026-08-04 09:00', auteur: 'Eugène', dernier_commit: 'merge <feature>', jours: 0, fusionnee: true, protegee: true, a_nettoyer: false },
    { nom: 'feature/vieille', date: '2026-06-01 09:00', auteur: 'X & Y', dernier_commit: "fix d'un truc", jours: 64, fusionnee: true, protegee: false, a_nettoyer: true },
    { nom: 'feature/en-cours', date: '2026-08-03 09:00', auteur: 'Eugène', dernier_commit: 'wip', jours: 1, fusionnee: false, protegee: false, a_nettoyer: false },
  ],
  dossier: { branche: 'feature/etiquette-carton', nb_modifies: 2, nb_non_suivis: 1, modifies: ['app/x.py', 'static/y.js'], non_suivis: ['tmp.txt'], verrou_git: true, propre: false },
  alertes: ['1 migration(s) en attente.', 'Un verrou git traîne.'],
};

const ctx = {
  console,
  document: { getElementById: (id) => elts[id] || null, querySelectorAll: () => [] },
  requestAnimationFrame: (f) => f(),
  setTimeout,
  fetch: async () => ({ ok: true, json: async () => payload, text: async () => '' }),
};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(src, ctx);

(async () => {
  await ctx.window.loadDeploiementSante();
  const html = elts['ds-body'].innerHTML;
  if (!html || html.length < 500) { console.error('RENDU VIDE'); process.exit(1); }
  for (const attendu of ['Migrations de base de données', 'Branches sur le dépôt distant', 'Dossier de travail', '227 appliquées', '1 à nettoyer', 'verrou git']) {
    if (!html.includes(attendu)) { console.error('MANQUE: ' + attendu); process.exit(1); }
  }
  // sections repliées par défaut : on déplie et on revérifie
  ctx.window.dsToggle('migrations'); ctx.window.dsToggle('branches'); ctx.window.dsToggle('dossier');
  const html2 = elts['ds-body'].innerHTML;
  for (const attendu of ['mp_declinaisons_appairage', 'v225', 'feature/en-cours', 'feature/vieille', 'à supprimer', 'tmp.txt', 'app/x.py', '64 j', 'index.lock', 'Numéros en double']) {
    if (!html2.includes(attendu)) { console.error('MANQUE (déplié): ' + attendu); process.exit(1); }
  }
  // pas de balise cassée / undefined qui fuit
  if (/undefined|NaN|\[object Object\]/.test(html2)) { console.error('FUITE undefined/NaN dans le rendu'); process.exit(1); }
  const ouv = (html2.match(/<div/g)||[]).length, fer = (html2.match(/<\/div>/g)||[]).length;
  console.log('rendu OK — ' + html2.length + ' car., <div>=' + ouv + ' </div>=' + fer);
  if (ouv !== fer) { console.error('DIVS DÉSÉQUILIBRÉS'); process.exit(1); }
  const to = (html2.match(/<table/g)||[]).length, tf = (html2.match(/<\/table>/g)||[]).length;
  if (to !== tf) { console.error('TABLES DÉSÉQUILIBRÉES'); process.exit(1); }
  console.log('toutes les vérifications passent');
})();
