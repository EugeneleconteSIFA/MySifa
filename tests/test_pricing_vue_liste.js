// Matières MyStock : la liste — une ligne par MATIÈRE, le prix saisi dessus.
//
// Le 28/08/2026, trois écrans répondaient à la même question « quel prix pour
// cette matière » : l'onglet « Base Coûts matières », la vue par référence à
// chevrons et la vue à plat par déclinaison. Le prix se saisissait dans la plus
// cachée des trois. Il n'en reste qu'une.
//
// Ce que ce test protège : que la liste montre bien une ligne par matière, que
// le prix s'y modifie, et qu'aucune référence ne disparaisse au passage — une
// matière sans déclinaison sortie de la liste sort de l'esprit.
//
// Lancer : node tests/test_pricing_vue_liste.js
const path = require('path');
process.chdir(path.join(__dirname, '..'));
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync('static/pricing_app.js', 'utf8').replace(/\r\n/g, '\n');
const css = fs.readFileSync('static/pricing_app.css', 'utf8').replace(/\r\n/g, '\n');
const api = fs.readFileSync('app/routers/pricing.py', 'utf8').replace(/\r\n/g, '\n');
const svc = fs.readFileSync('app/services/mystock_prix.py', 'utf8').replace(/\r\n/g, '\n');

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

const ctx = { S: { canWrite: true, filters: {}, mystock: [] }, Intl };
vm.createContext(ctx);
vm.runInContext(
  [
    extraire('icon'), extraire('escHtml'), extraire('escAttr'), extraire('fmtNum'),
    extraire('fmtPrixUnite'), extraire('categorieBadge'),
    extraire('actionBtn'), extraire('mystockPrixResume'),
    extraire('msFournisseursPrincipaux'),
    'const PRIX_VIEUX_JOURS = 365, PRIX_TRES_VIEUX_JOURS = 730;',
    extraire('joursDepuis'), extraire('ageTexte'), extraire('fmtJour'),
    extraire('dernierPrixCellHtml'),
    extraire('mystockMatiereRowHtml'),
  ].join('\n'),
  ctx
);

let ko = 0;
function check(label, got, attendu) {
  const ok = got === attendu;
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(56) + got + (ok ? '' : '   attendu ' + attendu));
}

// Dates relatives à aujourd'hui : un test qui code « 2026-08-30 » en dur vire
// au rouge tout seul dans dix-huit mois, sans qu'une ligne de code ait bougé.
const ilYA = (j) => new Date(Date.now() - j * 86400000).toISOString().slice(0, 19);
const hier = ilYA(1), vieux = ilYA(400), tresVieux = ilYA(900);

// Jeu d'essai : un adhésif à deux grammages au même prix (le cas normal), une
// glassine dont les déclinaisons ont deux fournisseurs différents, une
// référence orpheline, et une matière aux prix divergents.
const adhesif = {
  id: 1, reference: '1408', designation: 'Adhésif enlevable fort', categorie: 'adhesif',
  unite: '€/kg', type_declinaison: 'GRAMMAGE', prix_min: 4.2, prix_max: 4.2,
  prix_maj_le: hier, prix_maj_par: 'Eugene',
  declinaisons: [
    { id: 90, libelle: '17 g/m²', cout_eur_m2: 0.0885,
      lignes: [{ fournisseur_id: 7, fournisseur_nom: 'Meltavis', prix: 4.2, principal: true,
                 cout_eur_m2: 0.0885, a_tarif: true }] },
    { id: 91, libelle: '22 g/m²', cout_eur_m2: 0.1145,
      lignes: [{ fournisseur_id: 7, fournisseur_nom: 'Meltavis', prix: 4.2, principal: true,
                 cout_eur_m2: 0.1145, a_tarif: true }] },
  ],
};
const glassine = {
  id: 2, reference: 'GL80', designation: 'Glassine 80', categorie: 'glassine',
  unite: '€/m²', type_declinaison: 'LAIZE', prix_min: 0.08, prix_max: 0.09,
  prix_maj_le: vieux, prix_maj_par: 'Eugene',
  declinaisons: [
    { id: 92, libelle: '76 mm', cout_eur_m2: 0.08,
      lignes: [{ fournisseur_id: 3, fournisseur_nom: 'Coquelle', prix: 0.08, principal: true,
                 cout_eur_m2: 0.08, a_tarif: false }] },
    { id: 93, libelle: '102 mm', cout_eur_m2: 0.09,
      lignes: [{ fournisseur_id: 5, fournisseur_nom: 'Torrespapel', prix: 0.09, principal: true,
                 cout_eur_m2: 0.09, a_tarif: true }] },
  ],
};
const orpheline = {
  id: 3, reference: 'PP90', designation: 'PP blanc 90', categorie: 'frontal',
  unite: '€/m²', type_declinaison: 'LAIZE', prix_min: null, prix_max: null, declinaisons: [],
};
const diverge = {
  id: 4, reference: 'TH55', designation: 'Thermique 55', categorie: 'frontal',
  unite: '€/m²', type_declinaison: 'LAIZE', prix_min: 0.11, prix_max: 0.13,
  prix_maj_le: tresVieux, prix_maj_par: 'Eugene',
  declinaisons: [
    { id: 94, libelle: '76 mm', cout_eur_m2: 0.11,
      lignes: [{ fournisseur_id: 9, fournisseur_nom: 'UPM', prix: 0.11, principal: true, cout_eur_m2: 0.11, a_tarif: true }] },
    { id: 95, libelle: '102 mm', cout_eur_m2: 0.13,
      lignes: [{ fournisseur_id: 9, fournisseur_nom: 'UPM', prix: 0.13, principal: true, cout_eur_m2: 0.13, a_tarif: true }] },
  ],
};
ctx.S.mystock = [adhesif, glassine, orpheline, diverge];

const lAdh = ctx.mystockMatiereRowHtml(adhesif);
const lGla = ctx.mystockMatiereRowHtml(glassine);
const lOrp = ctx.mystockMatiereRowHtml(orpheline);
const lDiv = ctx.mystockMatiereRowHtml(diverge);

console.log('--- une ligne par matière, aucune référence perdue ---');
check('la ligne porte la matière, pas la déclinaison', lAdh.includes('data-ms-mat="1"'), true);
check('la référence', lAdh.includes('1408'), true);
check('la désignation revient dans la liste', lAdh.includes('Adhésif enlevable fort'), true);
check('la matière sans déclinaison est là', lOrp.includes('PP90'), true);

console.log('\n--- le prix ne dépend ni de la laize ni du grammage ---');
// Deux grammages, un seul prix au kilo : c'est tout l'objet du changement.
check('aucun grammage dans la ligne', lAdh.includes('17 g/m²'), false);
check('aucune laize non plus', lGla.includes('76 mm'), false);
check('un champ de prix, pas un texte', lAdh.includes('data-ms-prix="1"'), true);
check('avec la valeur en vigueur', lAdh.includes('value="4.2"'), true);
check('et son unité', lAdh.includes('€/kg'), true);
// Le 31/08/2026 : la notion de déclinaison quitte cet écran. Le prix d'achat
// est le même sur toutes, donc en compter deux n'apprenait rien à qui vient
// corriger un prix, et laissait croire qu'il y en avait deux à corriger.
check('plus de compteur de déclinaisons', lAdh.includes('msl-decl-nb'), false);
check('plus de colonne coût €/m²', lAdh.includes('msl-coutcell'), false);

console.log('\n--- ce qui se saisit et ce qui ne se saisit pas ---');
// Deux fournisseurs selon la déclinaison : un prix unique en écraserait un des
// deux avec le tarif de l'autre. On refuse, et on le dit.
check('fournisseurs différents : pas de champ', lGla.includes('data-ms-prix='), false);
check('la raison est donnée', lGla.includes('à régler sur la fiche'), true);
check('et le nombre de fournisseurs annoncé', lGla.includes('2 fournisseurs'), true);
// Prix divergents mais même fournisseur : le champ reste ouvert, il aligne.
check('prix divergents : champ ouvert', lDiv.includes('data-ms-prix="4"'), true);
check('mais aucune valeur affichée', /data-ms-prix="4"[^>]*value=""/.test(lDiv), true);
check('la fourchette est en filigrane', lDiv.includes('0,110 à 0,130'), true);
check('et la divergence signalée', lDiv.includes('msl-prix-diverge'), true);
check('matière sans déclinaison : pas de champ', lOrp.includes('data-ms-prix='), false);
ctx.S.canWrite = false;
check('lecture seule : aucun champ', ctx.mystockMatiereRowHtml(adhesif).includes('data-ms-prix='), false);
ctx.S.canWrite = true;

console.log('\n--- ce que la ligne garde, et ce qu\'elle a rendu ---');
// Le paramétrage détaillé — poids, devise, taxes, transport, et le coût €/m²
// qui en sort — vit sur la fiche. La liste y mène et ne le recopie plus.
check('la fiche reste accessible', lAdh.includes('href="/pricing/mystock/90"'), true);
check('aucun coût €/m² dans la ligne', lAdh.includes('0,0885') || lAdh.includes('0,1145'), false);
check('le camion ouvre le tarif', lAdh.includes('data-ms-tarif="7|1"'), true);
check('un fournisseur sans tarif propre se voit', lGla.includes('ms-tarif-manquant'), true);
// Créer une laize ou un grammage est un geste de MyStock : il n'a plus sa
// place sur un écran qui ne parle que de prix d'achat.
check('plus de flèche « dériver »', lAdh.includes('data-ms-deriver'), false);
check('plus de + « déclinaison vierge »', lAdh.includes('data-ms-new'), false);
check('rien non plus sur une matière orpheline', lOrp.includes('data-ms-new'), false);
check('les actions sont branchées', src.includes('function bindMsListeActions()')
  && src.includes('bindMsListeActions();'), true);

console.log('\n--- « Dernier prix » : quand ce prix a-t-il ete revu ---');
// Un prix d'achat ne se perime pas a date fixe, mais un prix qu'on n'a pas
// regarde depuis deux ans est presque surement faux, et rien ne le disait.
check('la date de derniere saisie', lAdh.includes(ctx.fmtJour(hier)), true);
check('et son age en clair', lAdh.includes('hier'), true);
check('un an : signale', lGla.includes('msl-maj vieux'), true);
check('deux ans : alerte', lDiv.includes('msl-maj tres-vieux'), true);
check('recent : rien de colore', /msl-maj"/.test(lAdh), true);
check('aucune trace : dit franchement', lOrp.includes('jamais revu'), true);
check('l\'auteur est dans l\'infobulle', lAdh.includes('par Eugene'), true);
// La cellule se reecrit apres une saisie : dire « il y a 2 ans » d'un prix
// qu'on vient de corriger serait le contraire de ce que la colonne promet.
check('la cellule se rafraichit apres enregistrement',
  /function bindMsPrixInline[^]{0,3000}dernierPrixCellHtml\(m\)/.test(src), true);
check('le service date les prix',
  svc.includes('def _dernier_prix_par_matiere(') && svc.includes('"prix_maj_le"'), true);
check('le repli ne prend que le prix principal',
  /_dernier_prix_par_matiere[^]{0,2500}p\.principal = 1/.test(svc), true);

console.log('\n--- le champ se donne pour ce qu\'il est ---');
// Le champ transparent au repos se lisait comme une colonne de chiffres :
// personne ne pensait à cliquer dedans. Bordure et crayon en permanence.
check('un crayon devant le champ', lAdh.includes('msl-prix-ico'), true);
check('le champ porte sa bordure au repos',
  /\.msl-prix-inp\{[^}]*border:1px solid var\(--border\)/.test(css), true);
check('l\'en-tête l\'annonce', src.includes('msl-th-hint'), true);
check('et le sous-titre aussi', src.includes('cliquez sur un prix d\'achat pour le modifier'), true);

console.log('\n--- la saisie en place ---');
check('elle est branchée', src.includes('function bindMsPrixInline()')
  && src.includes('bindMsPrixInline();'), true);
// Au `change`, pas à la frappe : un prix à moitié tapé ne part pas en base.
check('enregistrement à la sortie du champ',
  /function bindMsPrixInline[^]{0,3000}inp\.onchange = async/.test(src), true);
check('Échap annule', /function bindMsPrixInline[^]{0,3000}e\.key === "Escape"/.test(src), true);
check('la route existe', api.includes('@router.post("/api/pricing/mystock/prix-matiere")'), true);
check('elle exige le droit d\'écrire',
  /prix-matiere"\)[^]{0,900}_require_write\(request\)/.test(api), true);
check('le service pousse sur toutes les déclinaisons',
  svc.includes('def set_prix_matiere('), true);
check('et refuse plusieurs fournisseurs',
  svc.includes('"plusieurs fournisseurs en vigueur sur "'), true);
check('le tableau n\'est pas reconstruit après coup',
  /function bindMsPrixInline[^]{0,3000}renderMystockList\(\)/.test(src), false);

console.log('\n--- les vues retirées ne reviennent pas par la fenêtre ---');
check('plus de vue par référence', src.includes('data-ms-vue'), false);
check('plus de bascule', src.includes('function msVueSwitchHtml('), false);
check('plus de détail dépliable', src.includes('function mystockDetailHtml('), false);
check('plus de vue à plat par déclinaison', src.includes('function mystockDeclinaisonsAPlat('), false);
check('plus d\'onglet vers la base historique',
  src.includes('data-tab="couts"'), false);
// La base « Coûts matières » reste atteignable par son URL le temps que les
// fiches historiques finissent de vivre : ce qui disparaît, c'est l'aiguillage
// qui la présentait comme une vérité équivalente.
check('la base historique garde son chemin de retour',
  src.includes('data-tab="mystock"'), true);
check('/pricing ouvre les matières MyStock',
  /} else {[^]{0,300}await loadMystockList\(\);[^]{0,80}renderMystockList\(\);/.test(src), true);

console.log('\n--- tout tient dans la largeur ---');
check('les colonnes ont une largeur imposée', css.includes('table.msl-table{table-layout:fixed'), true);
const debutListe = src.indexOf('<table class="pr-table msl-table">');
const zoneListe = src.slice(debutListe, src.indexOf('</table>', debutListe));
check('un colgroup accompagne le tableau', zoneListe.includes('<colgroup>'), true);
check('une seule colonne élastique', (zoneListe.match(/<col>/g) || []).length, 1);
// Les en-têtes sont engendrés depuis la déclaration COLS : c'est elle qui fait
// foi. Autant de colonnes déclarées que de <col> et que de cellules — une
// colonne retirée d'un seul des trois endroits décale tout le tableau.
const rendu = src.slice(src.indexOf('function renderMystockList('));
const decl = rendu.slice(rendu.indexOf('const COLS = ['), rendu.indexOf('];'));
const nbCols = (decl.match(/\{ cle:/g) || []).length;
check('les colonnes sont déclarées une fois', nbCols > 0, true);
check('colonnes déclarées et cellules comptent pareil',
  nbCols, (lAdh.match(/<td[ >]/g) || []).length);
check('autant de <col> que de colonnes',
  (zoneListe.match(/<col[ >]/g) || []).length, nbCols);
check('la ligne vide occupe toute la largeur',
  zoneListe.includes('colspan="' + nbCols + '"'), true);

console.log('\n--- trier et filtrer par colonne ---');
// La recherche unique en haut de page repond a « ou est 1408 », jamais a
// « quels prix n'ont pas ete revus depuis deux ans ».
check('les en-tetes sont engendres', rendu.includes('enTetesTriables("matieres"'), true);
check('et branches', rendu.includes('bindEnTetes("matieres"'), true);
check('le prix se trie sur sa valeur, pas sur son texte',
  decl.includes('m.prix_min'), true);
check('la categorie se filtre par choix', /cle: "cat"[^]{0,120}filtre: "choix"/.test(decl), true);
check('la reference se filtre au texte', /cle: "ref"[^]{0,120}filtre: "texte"/.test(decl), true);
// Trois etats : croissant, decroissant, puis retour a l'ordre naturel. Sans le
// troisieme, un tri pose par erreur ne se retire plus.
check('le tri revient a l\'ordre naturel',
  /function triBascule[^]{0,600}S\.tri\[table\] = null/.test(src), true);
check('les valeurs manquantes restent en bas',
  /function triAppliquer[^]{0,900}if \(aVide\) return 1/.test(src), true);
check('la liste source n\'est pas triee en place',
  /function triAppliquer[^]{0,900}\[\.\.\.lignes\]\.sort/.test(src), true);
check('un filtre actif se voit et se relache',
  src.includes('function filtresActifsHtml') && src.includes('data-raz='), true);
check('le champ de prix a son style', css.includes('.msl-prix-inp{'), true);
check('la divergence aussi', css.includes('.msl-prix-diverge .msl-prix-inp{'), true);

console.log('\n--- le coût vient du serveur, jamais du navigateur ---');
check('le serveur chiffre chaque ligne',
  api.includes('ligne["cout_eur_m2"] = _cout_m2({**base, **ligne}, ligne.get("prix"))'), true);
check('le client n\'invente aucun coût', /cout_eur_m2\s*[*/]/.test(src), false);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
