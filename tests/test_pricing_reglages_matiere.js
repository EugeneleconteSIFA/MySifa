// Réglages de matière : grammage + perte, taxes en %, marge optionnelle.
// Lancer : node tests/test_pricing_reglages_matiere.js
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

let ko = 0;
function check(label, got, attendu) {
  const ok = JSON.stringify(got) === JSON.stringify(attendu);
  if (!ok) ko++;
  console.log((ok ? 'ok   ' : 'KO   ') + label.padEnd(58) + JSON.stringify(got)
    + (ok ? '' : '   attendu ' + JSON.stringify(attendu)));
}

const ctx = { console, Math, parseFloat, S: {} };
vm.createContext(ctx);
vm.runInContext([extraire('poidsRetenu'), extraire('grammageRetenu'), extraire('needsWeight')].join('\n'), ctx);

// ─── Grammage et perte ──────────────────────────────────────────────────────
check('70 g/m² sans perte = 0,070 kg/m²', ctx.poidsRetenu(70, 0), 0.07);
check('70 g/m² avec 9 % de perte', ctx.poidsRetenu(70, 9), 0.0763);
check('le grammage retenu est affiché en g/m²', ctx.grammageRetenu(70, 9), 76.3);
check('champs vides = zéro, pas NaN', ctx.poidsRetenu('', ''), 0);
check('une perte de 100 % double le grammage', ctx.grammageRetenu(50, 100), 100);
check('grammage saisi avec décimales', ctx.grammageRetenu(22.5, 9), 24.53);

// ─── La section n'apparaît que si le poids sert ─────────────────────────────
// Le grammage ne sert qu'à passer du kilo au m² : un prix déjà au m² n'en a
// aucun usage, importé ou pas.
check('prix au kilo : le grammage est nécessaire',
  ctx.needsWeight({ price_basis: 'PER_KG', is_imported: false }), true);
check('prix au kilo importé : toujours nécessaire',
  ctx.needsWeight({ price_basis: 'PER_KG', is_imported: true }), true);
check('prix au m² : inutile',
  ctx.needsWeight({ price_basis: 'PER_M2', is_imported: false }), false);
check('prix au m² importé : inutile aussi',
  ctx.needsWeight({ price_basis: 'PER_M2', is_imported: true }), false);

// ─── Ce que les deux fiches envoient au serveur ─────────────────────────────
// Le grammage ne se saisit plus sur une matière (31/08/2026), mais les deux
// fiches ne s'en séparent pas de la même façon :
//
//  - fiche MyStock : elle ne l'envoie PLUS DU TOUT. Sur un adhésif, le
//    grammage envoyé DÉPLACE la déclinaison (`set_declinaison_valeur`) — le
//    laisser partir avec une valeur d'écran devenue fantôme rebaptiserait la
//    matière à chaque enregistrement.
//  - fiche matière (base CM, l'ancêtre) : elle le renvoie tel quel, inchangé.
//    Ses propres produits (`mc_product`) calculent encore en €/m² et ont besoin
//    de ce poids ; le champ a disparu de l'écran, la valeur reste en base.
check('fiche MyStock : grammage plus envoyé',
  extraire('autoEnregistrerDecl').includes('grammage_gsm:'), false);
check('fiche MyStock : perte plus envoyée',
  extraire('autoEnregistrerDecl').includes('perte_pct:'), false);
check('fiche matière : le grammage fait l\'aller-retour sans être saisi',
  extraire('saveMaterialForm').includes('grammage_gsm:'), true);

for (const [nom, fn] of [['fiche matière', 'saveMaterialForm'], ['fiche MyStock', 'autoEnregistrerDecl']]) {
  const code = extraire(fn);
  check(nom + ' : taxe en pourcentage', code.includes('taxe_pct:'), true);
  check(nom + ' : choix de marge envoyé', code.includes('applique_marge:'), true);
  check(nom + ' : plus de multiplicateur', code.includes('tax_incidence'), false);
  check(nom + ' : plus de poids saisi', code.includes('weight_per_m2:'), false);
}

// ─── Chaque méthode de transport est expliquée, exemple à l'appui ───────────
// Quatre méthodes dont deux font la même division sur des données différentes :
// sans explication ni exemple chiffré, le choix se fait au hasard.
const aide = src.slice(src.indexOf('const TRANSPORT_AIDE = {'), src.indexOf('function transportModeOptions('));
for (const m of ['AMOUNT', 'PCT', 'CONTENEUR', 'FORFAIT']) {
  const bloc = aide.slice(aide.indexOf(m + ': {'), aide.indexOf('},', aide.indexOf(m + ': {')));
  check('méthode expliquée : ' + m, bloc.includes('quoi:'), true);
  check('exemple chiffré : ' + m, /exemple:\s*"[^"]*\d/.test(bloc), true);
}
check('l\'aide est rendue sous le sélecteur', src.includes('function transportAideHtml('), true);
for (const prefixe of ['f', 'd']) {
  check('sélecteur ' + prefixe + '-tmode suivi de son aide',
    new RegExp('id="' + prefixe + '-tmode">\\$\\{transportModeOptions[^]{0,80}transportAideHtml').test(src), true);
}
// L'aide dépend de la méthode : le formulaire doit se re-rendre au changement.
check('changer de méthode redessine la fiche', /"f-cur", "f-basis", "f-imp", "f-tmode"/.test(src), true);

// ─── Placement demandé dans le formulaire ───────────────────────────────────
const form = src.slice(src.indexOf('function renderMaterialForm('), src.indexOf('function syncMaterialFormFromDom('));
check('caractéristiques avant prix d\'achat',
  form.indexOf('<h3>Caractéristiques</h3>') < form.indexOf("<h3>Prix d'achat</h3>"), true);
const importBloc = form.slice(form.indexOf('id="import-block"'), form.indexOf('id="carac-section"') > form.indexOf('id="import-block"')
  ? form.indexOf('id="carac-section"') : form.length);
check('la taxe est dans l\'encadré import', importBloc.includes('id="f-tax"'), true);
// La case « Appliquer la marge » a quitté le bloc Prix d'achat : elle vit
// maintenant dans le panneau latéral Paramètres, bloc « Cette matière ».
const panneau = src.slice(src.indexOf('function inlineSettingsHtml('), src.indexOf('function bindInlineSettings('));
check('la case marge n\'est plus dans le corps du formulaire', form.includes('id="f-marge"'), false);
check('le formulaire monte le panneau Paramètres', form.includes('inlineSettingsHtml("f", f)'), true);
check('la fiche MyStock monte le même panneau', src.includes('inlineSettingsHtml("d", f)'), true);
check('la case marge est dans le panneau Paramètres', panneau.includes('${prefixe}-marge'), true);
check('le panneau distingue les deux portées',
  panneau.includes('Cette matière') && panneau.includes('Toutes les matières'), true);
check('le panneau ne s\'appelle plus « Paramètres globaux »',
  panneau.includes('Paramètres globaux'), false);
check('plus de champ poids kg/m²', form.includes('id="f-wm2"'), false);
// ─── Le grammage a quitté les fiches matière (31/08/2026) ───────────────────
// Un adhésif ne s'achète pas plus cher en 22 g/m² qu'en 17 : le prix est au
// kilo. Ce que le grammage fait varier, c'est la quantité posée — une décision
// de produit — et elle se saisit sur le composant, dans la fiche produit.
check('plus de champ grammage sur la fiche matière', form.includes('id="f-gsm"'), false);
check('ni sur la fiche MyStock', src.includes('id="d-gsm"'), false);
check('plus de perte non plus',
  src.includes('id="f-perte"') || src.includes('id="d-perte"'), false);
check('plus de section Caractéristiques', src.includes('<h3>Caractéristiques</h3>'), false);
check('la grille du grammage a disparu avec elle',
  (src.match(/class="gram-row"/g) || []).length, 0);

// ─── Tableau récapitulatif ──────────────────────────────────────────────────
const recap = extraire('recapTableHtml');
check('les taxes précèdent le sous-total',
  recap.indexOf('label: "Taxes"') < recap.indexOf('label: "Sous-total achat"'), true);
check('plus de ligne « incidence taxes »', recap.includes('Incidence taxes'), false);
check('formule mise à jour',
  src.includes("(prix d'achat + transport + taxes) × change"), true);

// ─── Méthodes de transport ──────────────────────────────────────────────────
const modes = src.slice(src.indexOf('const TRANSPORT_MODES ='),
                        src.indexOf('];', src.indexOf('const TRANSPORT_MODES =')));
for (const m of ['AMOUNT', 'PCT', 'CONTENEUR', 'FORFAIT']) {
  check('méthode proposée : ' + m, modes.includes('"' + m + '"'), true);
}
const champs = extraire('transportChampsHtml');
check('le pourcentage a son champ', champs.includes('% du prix'), true);
check('conteneur et forfait ont coût + quantité',
  champs.includes('-tcout') && champs.includes('-tqte'), true);
check('les libellés changent selon la méthode',
  src.includes('Coût du conteneur') && src.includes('Forfait de commande'), true);
for (const [nom, fn] of [['fiche matière', 'saveMaterialForm'], ['fiche MyStock', 'autoEnregistrerDecl']]) {
  const code = extraire(fn);
  check(nom + ' : coût envoyé', code.includes('transport_cout:'), true);
  check(nom + ' : quantité envoyée', code.includes('transport_quantite:'), true);
}

// ─── Créer une déclinaison a quitté la liste des matières ───────────────────
// Le 31/08/2026 : le prix d'achat ne varie pas d'une déclinaison à l'autre,
// donc l'écran des prix n'a plus à en parler du tout. Créer une laize ou un
// grammage reste un geste de MyStock, sur la fiche.
check('plus de flèche « dériver » dans la liste', src.includes('data-ms-deriver'), false);
check('plus de + « déclinaison vierge »', src.includes('data-ms-new'), false);
check('plus de duplication de ligne fournisseur', src.includes('data-ms-dup"'), false);

// ─── Bandeaux d'explication retirés ─────────────────────────────────────────
check('plus de note sur la page Matières MyStock',
  src.includes('Le prix saisi ici est'), false);
check('plus de note sur la page Produits MyStock',
  src.includes('Ces produits sont composés de'), false);
check('colonne fournisseur principal', src.includes('Fournisseur principal'), true);

// ─── Le taux de change s'essaie à la frappe ─────────────────────────────────
// Le taux vaut pour tout le catalogue : on le juge sur le prix qu'il donne
// AVANT qu'il soit gravé. Le champ recalcule donc la fiche pendant la frappe
// (fxEssai), puis le débounce d'enregistrement écrit la valeur posée.
const ctxFx = {
  console, Math, Number, parseFloat,
  S: { fxDraft: null, settings: { eur_usd_rate: 0.86 } },
};
vm.createContext(ctxFx);
vm.runInContext([extraire('fxEssai'), extraire('tauxCourant')].join('\n'), ctxFx);
check('rien tapé : aucun taux d\'essai', ctxFx.fxEssai(), undefined);
check('c\'est le taux enregistré qui vaut', ctxFx.tauxCourant(), 0.86);
ctxFx.S.fxDraft = '0.9123';
check('un taux tapé est essayé', ctxFx.fxEssai(), 0.9123);
check('et prend la main à l\'écran', ctxFx.tauxCourant(), 0.9123);
ctxFx.S.fxDraft = '';
check('champ vidé : on retombe sur l\'enregistré', ctxFx.tauxCourant(), 0.86);
ctxFx.S.fxDraft = '0';
check('un taux nul n\'annule pas les prix', ctxFx.fxEssai(), undefined);
check('les deux aperçus envoient le taux essayé',
  extraire('materialPreviewPayload').includes('eur_usd_rate: fxEssai()')
    && extraire('refreshDeclPreview').includes('eur_usd_rate: fxEssai()'), true);
const panneauFx = extraire('bindInlineSettings');
check('la frappe alimente l\'essai', panneauFx.includes('S.fxDraft = champTaux.value'), true);
check('et déclenche un recalcul', panneauFx.includes('recalculerApercu'), true);
check('enregistrer efface l\'essai', panneauFx.includes('S.fxDraft = null'), true);


// ─── Le panneau Paramètres s'enregistre à la frappe ─────────────────────────
// Régression : taux et marge par défaut attendaient un clic sur « Appliquer ».
// Un bouton qu'on oublie, c'est un réglage qui n'a jamais changé — et rien à
// l'écran ne le disait. Même patron que les fiches : débounce + pastille.
check('plus de bouton Appliquer', src.includes('id="si-save"'), false);
check('le panneau a sa pastille', panneau.includes('id="si-save-status"'), true);
check('la pastille utilise le même rendu d\'état',
  panneau.includes('saveStatusHtml(S.settingsSaveStatus'), true);
check('« Rafraîchir le taux » reste un bouton', panneau.includes('id="si-fx"'), true);
check('le taux enregistre à la frappe',
  panneauFx.includes('autoEnregistrerSettings(recalculerApercu)'), true);
check('la marge par défaut aussi', panneauFx.includes('champMarge'), true);
const autoSet = extraire('autoEnregistrerSettings');
check('un seul PATCH, sur les paramètres',
  autoSet.includes('"/api/pricing/settings"'), true);
check('taux et marge partent ensemble',
  autoSet.includes('eur_usd_rate: taux') && autoSet.includes('default_margin_pct: marge'), true);
check('un champ vide n\'écrit rien', autoSet.includes('if (!(taux > 0)'), true);
check('la pastille passe par « cours »', autoSet.includes('setSettingsSaveStatus("cours")'), true);
check('et par « err » sur erreur', autoSet.includes('setSettingsSaveStatus("err")'), true);
check('enregistré, le taux n\'est plus un essai', autoSet.includes('S.fxDraft = null'), true);
check('pas de re-render pendant la frappe', autoSet.includes('redessiner('), false);
for (const fn of ['loadMaterialForm', 'loadDeclinaisonForm']) {
  check('pastille remise à neuf : ' + fn,
    extraire(fn).includes('reinitSettingsSave()'), true);
}
check('plus de mention du bouton Enregistrer du bandeau',
  src.includes('par le bouton Enregistrer du bandeau'), false);

console.log(ko === 0 ? '\nTOUT EST VERT' : '\n' + ko + ' ECHEC(S)');
process.exit(ko === 0 ? 0 : 1);
