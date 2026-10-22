/* MyTools — page /tools : la boîte à outils transverse de MySifa.
 *
 * Remplace MyPrint (21/10/2026). Chaque outil est un module autonome, monté
 * dans #content ; cette page ne fait que la navigation, les droits et
 * l'adresse.
 *
 *   accueil      tuiles des outils ouverts à l'utilisateur
 *   etiquettes   postes d'étiquetage + étiquettes spécifiques
 *                (static/mysifa_tools_etiquettes.js, static/mysifa_etiq_specifiques.js)
 *   formulaires  création et suivi des formulaires (ex-MyQualité › Formulaires,
 *                FORMULAIRES_JS de app/web/qualite_formulaires_assets.py)
 *   pdf          éditeur PDF dans le navigateur (static/mysifa_tools_pdf.js, chargé à la demande)
 *   traduction   traducteur DeepL (static/mysifa_tools_traduction.js)
 *   parapheur    envoi de PDF à signer, suivi, signature (static/mysifa_tools_parapheur.js,
 *                chargé à la demande ; noyau de signature static/mysifa_parapheur_signer.js)
 *   convertir    convertisseur de formats (static/mysifa_tools_convertir.js, chargé à la demande)
 *   calculs      calculs bobine : métrage ↔ diamètre, fronts, étiquettes par bobine
 *                (static/mysifa_tools_calculs.js)
 *   utilitaires  codes, scanner, comparer, unités et couleurs, renommer, archives
 *                (static/mysifa_tools_utilitaires.js, chargé à la demande ; un fichier
 *                static/mysifa_tools_util_<sous>.js par sous-onglet, clé d'adresse `sous`)
 *
 * Adresse : /tools?outil=<id>&… — chaque module dit ce qu'il montre par son
 * `adresse.etat()` et sait y retourner par `adresse.aller()`. La page observe
 * le DOM et réécrit l'adresse après chaque changement d'affichage (modèle
 * MyStock) : aucun geste n'a à y penser.
 *
 * Le module Formulaires a été écrit pour MyQualité : il attend un `S` global,
 * `setView()`, un `api()` qui rend la Response, `showToast()`, `closeMroot()`.
 * On lui fournit ces noms ici plutôt que de le réécrire.
 */
'use strict';

const TOOLS = window.__MYTOOLS__ || { droits: {}, user: {}, org: '' };

// État central. `view` et `formu` appartiennent au module Formulaires.
var S = {
  outil: 'accueil',
  view: 'menu',
  user: TOOLS.user || {},
  isQualiteAdmin: !!(TOOLS.droits && TOOLS.droits.formulaires_admin),
  isQualiteReadonly: !!(TOOLS.droits && TOOLS.droits.formulaires && !TOOLS.droits.formulaires_admin),
};

const TOOLS_OUTILS = [
  { id: 'etiquettes', label: 'Étiquettes', titre: 'Étiquettes', ia: true, onglet: 'Étiquettes',
    desc: 'Étiquettes de traçabilité par poste, étiquettes spécifiques par client, création depuis une photo.',
    icon: '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>' },
  { id: 'formulaires', label: 'Formulaires', titre: 'Formulaires', ia: true,
    desc: 'Questionnaires pour fournisseurs, personnel et clients : création, envoi, relances, réponses.',
    icon: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>' },
  { id: 'pdf', label: 'Éditeur PDF', titre: 'Éditeur PDF', onglet: 'Éditer un PDF',
    desc: 'Fusionner, découper, annoter, remplir, compresser ; scanner un document ; envoyer à signer (parapheur).',
    icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15l2 2 4-4"/>' },
  { id: 'parapheur', label: 'Parapheur', titre: 'Parapheur', parent: 'pdf', onglet: 'Parapheur',
    desc: 'Envoyer un PDF à signer à une ou plusieurs personnes, dans un ordre défini, avec relances et certificat.',
    icon: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M8.5 16.5c1.4 0 1.9-3.5 3-3.5s-.1 3.3 1 3.3c.8 0 1.1-1.2 1.8-1.2.6 0 .5.9 1.2.9"/>' },
  { id: 'image', label: 'Image et BAT', titre: 'Image et BAT',
    desc: 'Agrandir, nettoyer, détourer une image ; la vectoriser en SVG ou PDF. Les fichiers restent sur le poste.',
    icon: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 16l5-5 4 4"/><path d="M14 13l2-2 5 5"/><circle cx="8.5" cy="8" r="1.5"/>' },
  { id: 'convertir', label: 'Convertir', titre: 'Convertir', onglet: 'Convertir',
    desc: 'Plus de 50 formats ; renommer des fichiers en lot, créer ou ouvrir un zip, comparer deux textes ou tableaux.',
    icon: '<path d="M4 7h11.5"/><path d="M12.5 3.5L16 7l-3.5 3.5"/><path d="M20 17H8.5"/><path d="M11.5 13.5L8 17l3.5 3.5"/>' },
  { id: 'calculs', label: 'Calculs bobine', titre: 'Calculs bobine', onglet: 'Bobine',
    desc: 'Métrage ↔ diamètre, fronts sur la laize, étiquettes par bobine, carton optimal ; unités et couleurs.',
    icon: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v6"/>' },
  { id: 'traduction', label: 'Traducteur', titre: 'Traducteur', ia: true,
    desc: 'Traduire un texte ou un courrier dans huit langues, vouvoiement ou tutoiement.',
    icon: '<path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/>' },
  // Sous-outils : un onglet de leur outil parent, pas une entrée du menu.
  // `util` : sous-outil de static/mysifa_tools_utilitaires.js monté seul.
  { id: 'scanner', parent: 'pdf', util: 'scanner', onglet: 'Scanner', label: 'Scanner', titre: 'Scanner un document',
    desc: 'Photo d\'un document → page redressée et contrastée, en PDF.', icon: '' },
  { id: 'codes', parent: 'etiquettes', util: 'qr', onglet: 'Code rapide', label: 'Code rapide', titre: 'Code QR ou code-barres',
    desc: 'QR, Code 128, EAN-13, DataMatrix à copier ou télécharger.', icon: '' },
  { id: 'unites', parent: 'calculs', util: 'unites', onglet: 'Unités et couleurs', label: 'Unités et couleurs', titre: 'Unités et couleurs',
    desc: 'Longueurs, grammage, laize ↔ m², CMJN, contraste, Pantone.', icon: '' },
  { id: 'renommer', parent: 'convertir', util: 'renommer', onglet: 'Renommer en lot', label: 'Renommer', titre: 'Renommer des fichiers',
    desc: 'Préfixe, numéro, date, remplacement sur tout un lot.', icon: '' },
  { id: 'archives', parent: 'convertir', util: 'archives', onglet: 'Zip', label: 'Zip', titre: 'Créer ou ouvrir un zip',
    desc: 'Créer un zip, ouvrir un zip et en extraire un fichier.', icon: '' },
  { id: 'comparer', parent: 'convertir', util: 'comparer', onglet: 'Comparer', label: 'Comparer', titre: 'Comparer deux textes ou tableaux',
    desc: 'Deux textes, deux listes ou deux tableaux CSV.', icon: '' },
];
// `utilitaires` : ancienne page, ses adresses mènent au sous-outil (toolsLegacy).
const TOOLS_IDS = ['accueil', 'utilitaires'].concat(TOOLS_OUTILS.map(o => o.id));
const _TOOLS_UTIL_IDS = { qr: 'codes', scanner: 'scanner', unites: 'unites', renommer: 'renommer', archives: 'archives', comparer: 'comparer' };
// Ancienne adresse ?outil=utilitaires&sous=<x> → l'outil qui porte ce sous-outil.
function toolsLegacy(outil, u) {
  if (outil !== 'utilitaires') return outil;
  return _TOOLS_UTIL_IDS[u.get('sous', 'qr')] || 'codes';
}
const toolsParent = id => { const o = toolsOutil(id); return (o && o.parent) || id; };
const toolsOnglets = id => { const p = toolsParent(id); return TOOLS_OUTILS.filter(o => (o.id === p || o.parent === p) && toolsPermis(o.id)); };
// Icône de l'appli (même tracé que 'mytools' de html.py et mysifa_cmdk.js).
const TOOLS_ICONE = '<rect x="2.5" y="14" width="19" height="6.5" rx="3.25"/><path d="M6.5 14c3.5-4.5 8-7.8 14-9.5L10 14"/><path d="M15.5 14l2.2-3.6"/><path d="M6 17.25h.01M18 17.25h.01"/>';

function toolsPermis(id) {
  if (id === 'accueil') return true;
  const o = TOOLS_OUTILS.find(x => x.id === id);
  if (o && o.util) return !!(TOOLS.droits && TOOLS.droits.utilitaires) && toolsPermis(o.parent);
  return !!(TOOLS.droits && TOOLS.droits[id]);
}
function toolsOutil(id) { return TOOLS_OUTILS.find(o => o.id === id) || null; }
function toolsSvg(paths, n) {
  const s = n || 16;
  return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    + 'stroke-linecap="round" stroke-linejoin="round">' + paths + '</svg>';
}

// ── Environnement attendu par le module Formulaires ─────────────────
function escHtml(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function escAttr(s) { return escHtml(s); }
async function api(path, opts) {
  const r = await fetch(path, Object.assign({ credentials: 'include' }, opts || {}));
  if (r.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); throw new Error('unauth'); }
  return r;
}
function showToast(msg, type) {
  const wrap = document.getElementById('toast-wrap');
  if (!wrap) return;
  const t = type === 'error' ? 'danger' : (type === 'warn' ? 'info' : (type || 'info'));
  const el = document.createElement('div');
  el.className = 'toast ' + t;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}
function closeMroot() { const m = document.getElementById('mroot'); if (m) m.innerHTML = ''; }
function ico(paths) { return toolsSvg(paths, 18); }
// Les visites guidées restent dans MyQualité tant que l'outil n'a pas son guide.
function openGuide() {}
function _refreshHelpBadges() {}
function _renderTaskSectionsFor() { return ''; }
// Registre des tâches des guides de MyQualité, que le module complète.
var QUALITE_TASKS_MODULES = {};
// Icônes de secours pour les modules qui les cherchent dans un `iconEl` global
// (static/mysifa_etiq_specifiques.js et l'éditeur, écrits pour MyStock).
// Tracés repris de la fonction icon() de MyStock.
const _TOOLS_ICONES = {
"arrow-left": "<line x1=\"19\" y1=\"12\" x2=\"5\" y2=\"12\"/><polyline points=\"12 19 5 12 12 5\"/>",
"clock": "<circle cx=\"12\" cy=\"12\" r=\"10\"/><polyline points=\"12 6 12 12 16 14\"/>",
"copy": "<rect x=\"9\" y=\"9\" width=\"13\" height=\"13\" rx=\"2\" ry=\"2\"/><path d=\"M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1\"/>",
"edit": "<path d=\"M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7\"/><path d=\"M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z\"/>",
"plus": "<line x1=\"12\" y1=\"5\" x2=\"12\" y2=\"19\"/><line x1=\"5\" y1=\"12\" x2=\"19\" y2=\"12\"/>",
"trash-2": "<polyline points=\"3 6 5 6 21 6\"/><path d=\"M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2\"/><line x1=\"10\" y1=\"11\" x2=\"10\" y2=\"17\"/><line x1=\"14\" y1=\"11\" x2=\"14\" y2=\"17\"/>",
"rotate-ccw": "<polyline points=\"1 4 1 10 7 10\"/><path d=\"M3.51 15a9 9 0 1 0 .49-4.5\"/>",
"printer": "<polyline points=\"6 9 6 2 18 2 18 9\"/><path d=\"M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2\"/><rect x=\"6\" y=\"14\" width=\"12\" height=\"8\"/>",
"tag": "<path d=\"M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z\"/><line x1=\"7\" y1=\"7\" x2=\"7.01\" y2=\"7\"/>",
"download": "<path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"/><polyline points=\"7 10 12 15 17 10\"/><line x1=\"12\" y1=\"15\" x2=\"12\" y2=\"3\"/>",
"upload": "<path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"/><polyline points=\"17 8 12 3 7 8\"/><line x1=\"12\" y1=\"3\" x2=\"12\" y2=\"15\"/>",
"search": "<circle cx=\"11\" cy=\"11\" r=\"8\"/><line x1=\"21\" y1=\"21\" x2=\"16.65\" y2=\"16.65\"/>",
"settings": "<circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z\"/>",
"layers": "<polygon points=\"12 2 2 7 12 12 22 7 12 2\"/><polyline points=\"2 17 12 22 22 17\"/><polyline points=\"2 12 12 17 22 12\"/>",
"file-text": "<path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"/><polyline points=\"14 2 14 8 20 8\"/><line x1=\"16\" y1=\"13\" x2=\"8\" y2=\"13\"/><line x1=\"16\" y1=\"17\" x2=\"8\" y2=\"17\"/><polyline points=\"10 9 9 9 8 9\"/>",
"eye": "<path d=\"M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/>",
"save": "<path d=\"M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z\"/><polyline points=\"17 21 17 13 7 13 7 21\"/><polyline points=\"7 3 7 8 15 8\"/>",
"folder": "<path d=\"M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z\"/>",
"x": "<line x1=\"18\" y1=\"6\" x2=\"6\" y2=\"18\"/><line x1=\"6\" y1=\"6\" x2=\"18\" y2=\"18\"/>",
"inbox": "<polyline points=\"22 12 16 12 14 15 10 15 8 12 2 12\"/><path d=\"M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z\"/>",
"message-square": "<path d=\"M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z\"/>"
};
function iconEl(name, size) {
  const s = document.createElement('span');
  s.style.cssText = 'display:inline-flex;align-items:center;flex-shrink:0';
  s.innerHTML = toolsSvg(_TOOLS_ICONES[name] || '', size || 16);
  return s;
}
function toggleSidebar() { document.body.classList.toggle('sb-open'); }
function closeSidebar() { document.body.classList.remove('sb-open'); }

// Navigation interne du module Formulaires (« ← Formulaires », ouverture
// d'un formulaire, suppression). `menu` ramène à l'accueil de MyTools.
function setView(v) {
  if (S.view === 'formulaire-edit' && v !== 'formulaire-edit' && typeof formuQuitter === 'function') formuQuitter();
  if (v === 'formulaires-list' || v === 'formulaire-edit') {
    S.outil = 'formulaires';
    S.view = v;
    toolsRendre();
    return;
  }
  S.view = 'menu';
  toolsAller('accueil');
}

// ── Rendu ────────────────────────────────────────────────────────────
function toolsNav() {
  document.querySelectorAll('.nav-btn[data-outil]').forEach(b => {
    const id = b.getAttribute('data-outil');
    b.style.display = toolsPermis(id) ? '' : 'none';
    b.classList.toggle('active', id === toolsParent(S.outil));
  });
  const o = toolsOutil(S.outil);
  const sub = document.getElementById('mobile-sub');
  if (sub) sub.textContent = o ? o.titre : 'Boîte à outils';
  document.title = (o ? o.titre + ' — ' : '') + 'MyTools — MySifa';
}

function toolsAccueil(root) {
  const tuiles = TOOLS_OUTILS.filter(o => !o.parent && toolsPermis(o.id)).map(o =>
    '<button type="button" class="tools-tile" onclick="toolsAller(\'' + o.id + '\')">'
    + '<span class="tools-tile-ic">' + toolsSvg(o.icon, 22) + '</span>'
    + '<span class="tools-tile-txt"><span class="tools-tile-t">' + escHtml(o.titre)
    + (o.ia ? ' <span class="ia-badge" data-bulle="Utilise l\'IA">IA</span>' : '') + '</span>'
    + '<span class="tools-tile-d">' + escHtml(o.desc) + '</span></span></button>').join('');
  root.innerHTML = '<div class="tools-page">'
    + '<div class="tools-hero"><h1><span class="tools-hero-ic">' + toolsSvg(TOOLS_ICONE, 28) + '</span><span>My<span>Tools</span></span></h1>'
    + '<p>Les outils du quotidien, au même endroit. <span class="ia-badge">IA</span> signale les outils qui font appel à l\'intelligence artificielle.</p></div>'
    + '<div class="tools-grid">' + (tuiles || '<div class="tools-empty">Aucun outil ouvert à votre profil.</div>') + '</div></div>';
}

// Modules lourds chargés au premier usage (script + feuille de style).
const _TOOLS_DIFFERES = {
  pdf:   { js: 'mysifa_tools_pdf.js', css: 'mysifa_tools_pdf.css', glob: 'MyToolsPDF', nom: 'Éditeur PDF' },
  image: { js: 'mysifa_tools_image.js', css: 'mysifa_tools_image.css', glob: 'MyToolsImage', nom: 'Outil image' },
  convertir: { js: 'mysifa_tools_convertir.js', css: 'mysifa_tools_convertir.css', glob: 'MyToolsConvertir', nom: 'Convertisseur' },
  parapheur: { js: 'mysifa_tools_parapheur.js', css: 'mysifa_tools_parapheur.css', glob: 'MyToolsParapheurModule', nom: 'Parapheur' },
  utilitaires: { js: 'mysifa_tools_utilitaires.js', css: 'mysifa_tools_utilitaires.css', glob: 'MyToolsUtilitaires', nom: 'Utilitaires' },
};
const _toolsCharges = {};
function toolsCharger(id) {
  const d = _TOOLS_DIFFERES[id];
  if (window[d.glob]) return Promise.resolve();
  if (_toolsCharges[id]) return _toolsCharges[id];
  _toolsCharges[id] = new Promise((ok, ko) => {
    const v = TOOLS.version ? '?v=' + encodeURIComponent(TOOLS.version) : '';
    if (!document.getElementById('tools-css-' + id)) {
      const l = document.createElement('link');
      l.id = 'tools-css-' + id; l.rel = 'stylesheet'; l.href = '/static/' + d.css + v;
      document.head.appendChild(l);
    }
    const sc = document.createElement('script');
    sc.src = '/static/' + d.js + v;
    sc.onload = () => ok(); sc.onerror = () => { _toolsCharges[id] = null; ko(new Error(d.nom + ' indisponible.')); };
    document.head.appendChild(sc);
  });
  return _toolsCharges[id];
}
// API de l'Éditeur PDF (« Envoyer à signer ») : charge le Parapheur au besoin,
// puis ouvre sa fenêtre de création avec le document. Le module, une fois
// chargé, remplace cet objet par le sien.
if (!window.MyToolsParapheur) window.MyToolsParapheur = {
  ouvrir: function (f) {
    if (!(TOOLS.droits && TOOLS.droits.parapheur_creer)) {
      showToast('Votre profil ne permet pas d\'envoyer un document à signer.', 'danger');
      return Promise.resolve(false);
    }
    return toolsCharger('parapheur').then(() => window.MyToolsParapheurModule.ouvrir(f));
  },
};

const _toolsCtx = {
  toast: (m, t) => showToast(m, t),
  user: S.user,
  org: TOOLS.org || '',
  surChange: () => toolsSyncUrl(),
};

// Un module démonté libère ses écouteurs globaux (raccourcis clavier).
let _toolsMonte = null;
function toolsDemonter(sauf) {
  if (_toolsMonte && _toolsMonte !== sauf) {
    const m = { etiquettes: window.MyToolsEtiquettes, pdf: window.MyToolsPDF, traduction: window.MyToolsTraduction,
                image: window.MyToolsImage, parapheur: window.MyToolsParapheurModule,
                utilitaires: window.MyToolsUtilitaires }[_toolsMonte] || (toolsOutil(_toolsMonte) && toolsOutil(_toolsMonte).util ? window.MyToolsUtilitaires : null);
    if (m && typeof m.demonter === 'function') { try { m.demonter(); } catch (e) {} }
  }
  _toolsMonte = sauf || null;
}

function toolsRendre() {
  if (!toolsPermis(S.outil)) S.outil = 'accueil';
  toolsNav();
  const content = document.getElementById('content');
  if (!content) return;
  content.classList.toggle('content--large', ['pdf', 'etiquettes', 'image'].includes(toolsParent(S.outil)));
  toolsDemonter(S.outil);
  if (S.outil === 'formulaires') {
    if (S.view === 'formulaire-edit' && S.formu && S.formu.courant) { if (typeof formuRenderEdition === 'function') formuRenderEdition(); }
    else { S.view = 'formulaires-list'; if (typeof formuEnter === 'function') formuEnter(); }
    return;
  }
  if (S.view === 'formulaire-edit' && typeof formuQuitter === 'function') formuQuitter();
  S.view = 'menu';
  if (S.outil === 'accueil') { toolsAccueil(content); return; }
  content.innerHTML = '';
  const ongl = toolsOnglets(S.outil);
  if (ongl.length > 1) {
    const bar = document.createElement('div');
    bar.className = 'tools-onglets'; bar.setAttribute('role', 'tablist');
    bar.innerHTML = ongl.map(o => '<button type="button" role="tab" class="tools-onglet' + (o.id === S.outil ? ' actif' : '') + '"'
      + ' aria-selected="' + (o.id === S.outil) + '" data-bulle="' + escAttr(o.titre) + '" onclick="toolsAller(\'' + o.id + '\')">'
      + escHtml(o.onglet || o.label) + (o.ia ? ' <span class="ia-badge">IA</span>' : '') + '</button>').join('');
    content.appendChild(bar);
  }
  const root = document.createElement('div');
  root.className = 'tools-module';
  content.appendChild(root);
  const so = toolsOutil(S.outil);
  if (so && so.util) {
    const id = S.outil;
    root.classList.add('tools-util-seul');
    root.innerHTML = '<div class="tools-empty"><span class="spin"></span> Chargement…</div>';
    const a = _toolsAttente.utilitaires;
    if (!a || a.sous !== so.util) _toolsAttente.utilitaires = { sous: so.util, params: {} };
    toolsCharger('utilitaires').then(() => {
      if (S.outil !== id || !root.isConnected) return;
      root.innerHTML = '';
      window.MyToolsUtilitaires.mount(root, _toolsCtx);
      const at = _toolsAttente.utilitaires || { sous: so.util, params: {} };
      _toolsAttente.utilitaires = null;
      try { window.MyToolsUtilitaires.adresse.aller(at); } catch (e) {}
      toolsSyncUrl();
    }).catch(e => { root.innerHTML = '<div class="tools-empty">' + escHtml(e.message) + '</div>'; });
    return;
  }
  if (S.outil === 'etiquettes') {
    if (window.MyToolsEtiquettes) window.MyToolsEtiquettes.mount(root, _toolsCtx);
    else root.innerHTML = '<div class="tools-empty">Module Étiquettes indisponible.</div>';
  } else if (S.outil === 'calculs') {
    if (window.MyToolsCalculs) window.MyToolsCalculs.mount(root, _toolsCtx);
    else root.innerHTML = '<div class="tools-empty">Calculs indisponibles.</div>';
  } else if (S.outil === 'traduction') {
    if (window.MyToolsTraduction) window.MyToolsTraduction.mount(root, _toolsCtx);
    else root.innerHTML = '<div class="tools-empty">Traducteur indisponible.</div>';
  } else if (_TOOLS_DIFFERES[S.outil]) {
    const id = S.outil, d = _TOOLS_DIFFERES[id];
    root.innerHTML = '<div class="tools-empty"><span class="spin"></span> Chargement…</div>';
    toolsCharger(id).then(() => {
      if (S.outil !== id || !root.isConnected) return;
      root.innerHTML = '';
      window[d.glob].mount(root, _toolsCtx);
      const a = _toolsAttente[id];
      if (a) { _toolsAttente[id] = null; try { window[d.glob].adresse.aller(a); } catch (e) {} }
      toolsSyncUrl();
    }).catch(e => { root.innerHTML = '<div class="tools-empty">' + escHtml(e.message) + '</div>'; });
  }
}

function toolsAller(id) {
  const cible = TOOLS_IDS.indexOf(id) !== -1 && toolsPermis(id) ? id : 'accueil';
  if (cible === 'formulaires') { setView('formulaires-list'); closeSidebar(); return; }
  S.outil = cible;
  closeSidebar();
  toolsRendre();
}

// ── Adresse ──────────────────────────────────────────────────────────
// Fenêtres du module Formulaires, suivies comme dans MyQualité
// (static/qualite_url.js) : la fonction d'ouverture est enveloppée, la
// fenêtre est réputée fermée dès que #mroot se vide.
const _TOOLS_OUVREURS = [
  ['formuIaOuvrir',     'ia_formulaire',      a => a[0] === 'modifier' ? 'modifier' : 'nouveau'],
  ['formuEnvoiOuvrir',  'envoi_formulaire',   a => a[0]],
  ['formuReponseVoir',  'reponse_formulaire', a => a[0]],
];
let _toolsFen = null, _toolsOuvrant = 0, _toolsUrlPrete = false;
// Adresse demandée pour un module pas encore chargé, appliquée au montage.
const _toolsAttente = {};

function toolsEnvelopper() {
  _TOOLS_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      if (!_toolsOuvrant) {
        let v = null;
        try { v = valeur(arguments); } catch (e) {}
        if (v !== null && v !== undefined && v !== '') _toolsFen = { cle, id: String(v), vu: false, depuis: Date.now() };
      }
      _toolsOuvrant++;
      try { return orig.apply(this, arguments); }
      finally { _toolsOuvrant--; toolsSyncUrl(); }
    };
    env.__adresse = true;
    window[nom] = env;
  });
}
function _toolsFenetre() {
  const f = _toolsFen;
  if (!f) return null;
  const m = document.getElementById('mroot');
  if (m && m.childElementCount) { f.vu = true; return f; }
  if (f.vu || Date.now() - f.depuis > 5000) { _toolsFen = null; return null; }
  return f;
}

function toolsParams() {
  const p = {};
  let nav = S.outil;
  if (S.outil !== 'accueil') p.outil = S.outil;
  if (S.outil === 'etiquettes' && window.MyToolsEtiquettes) {
    const a = window.MyToolsEtiquettes.adresse.etat();
    if (a.poste) { p.poste = a.poste; nav += '/' + a.poste; }
    if (a.impression) p.impression = a.impression;
    // Étiquettes spécifiques : le module dit ce qu'il montre (vue, dossier,
    // étiquette ouverte dans l'éditeur, demande, fenêtre) — mêmes clés que
    // sous MyStock, pour que les anciens liens se traduisent tels quels.
    const ad = a.poste === 'specifiques' && window.EtiqSpec && window.EtiqSpec.adresse;
    if (ad) {
      const e = ad.etat();
      if (e.dossier != null) p.dossier = String(e.dossier);
      if (e.modele) { p.modele = String(e.modele); nav += '/modele:' + e.modele; }
      else if (e.vue === 'demandes') { p.vue = 'demandes'; nav += '/demandes'; if (e.demande != null) p.demande = String(e.demande); }
      if (e.modale && e.modale.cle) { p[e.modale.cle] = String(e.modale.id); nav += '/' + e.modale.cle; }
      // Filtres, mode, onglet, langue, enregistrement : clés déclarées par le module.
      for (const [k, v] of Object.entries(e.extra || {})) {
        if (v == null || v === '') continue;
        p[k] = String(v);
        if (k === 'edition' || k === 'panneau') nav += '/' + v;
      }
    }
  } else if (S.outil === 'formulaires' && S.formu) {
    if (S.view === 'formulaire-edit' && S.formu.courant) {
      p.formulaire = S.formu.courant.id; nav += ':' + p.formulaire;
      if (S.formu.onglet === 'suivi') { p.onglet = 'suivi'; nav += '/suivi'; }
    } else if (S.formu.filtre && S.formu.filtre !== 'actifs') {
      p.filtre = S.formu.filtre;
    }
    const f = _toolsFenetre();
    if (f) { p[f.cle] = f.id; nav += '/' + f.cle; }
  } else if (S.outil === 'pdf' && window.MyToolsPDF && window.MyToolsPDF.adresse) {
    try {
      const e = window.MyToolsPDF.adresse.etat() || {};
      if (e.page && Number(e.page) > 1) p.page = String(e.page);
      // Fenêtre ouverte de l'éditeur (comparer, protéger, IA…) : un endroit, donc empilé.
      if (e.panneau) { p.panneau = String(e.panneau); nav += '/' + p.panneau; }
    } catch (e) {}
  } else if (S.outil === 'parapheur') {
    // Module pas encore chargé : l'adresse demandée fait foi en attendant.
    const m = window.MyToolsParapheurModule;
    const e = (m && m.adresse) ? m.adresse.etat() : (_toolsAttente.parapheur || {});
    if (e.statut && e.statut !== 'en_cours') p.statut = e.statut;
    if (e.demande) { p.demande = String(e.demande); nav += ':' + e.demande; if (e.signer) { p.signer = '1'; nav += '/signer'; } }
  } else if (toolsOutil(S.outil) && toolsOutil(S.outil).util) {
    // Sous-outil de Utilitaires : ses options ; l'adresse demandée fait foi
    // tant que le module n'est pas chargé.
    const m = window.MyToolsUtilitaires, a = _toolsAttente.utilitaires;
    const e = (m && !a) ? m.adresse.etat() : { options: (a && a.params) || {} };
    Object.keys(e.options || {}).forEach(k => { if (!(k in p)) p[k] = String(e.options[k]); });
  } else if (S.outil === 'calculs' && window.MyToolsCalculs && window.MyToolsCalculs.adresse) {
    const e = window.MyToolsCalculs.adresse.etat();
    if (e.calcul && e.calcul !== 'metrage') { p.calcul = e.calcul; nav += '/' + e.calcul; }
  } else if (S.outil === 'image' && window.MyToolsImage) {
    if (window.MyToolsImage.adresse.etat().mode === 'vectoriser') { p.mode = 'vectoriser'; nav += '/vectoriser'; }
  } else if (S.outil === 'traduction' && window.MyToolsTraduction) {
    const e = window.MyToolsTraduction.adresse.etat();
    if (e.de && e.de !== 'auto') p.de = e.de;
    if (e.vers && e.vers !== 'EN') p.vers = e.vers;
  }
  // Fenêtre de création du Parapheur : ouverte par-dessus n'importe quel outil
  // (l'Éditeur PDF l'ouvre avec son document).
  const ppx = window.MyToolsParapheurModule;
  if ((ppx && ppx.adresse.creation()) || (!ppx && _toolsAttente.parapheurCreation)) { p.parapheur = 'nouvelle'; nav += '/parapheur'; }
  return { params: p, nav: nav };
}

function toolsSyncUrl() {
  if (!_toolsUrlPrete || !window.MySifaUrl) return;
  try { const r = toolsParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}

function toolsObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    // setTimeout plutôt que requestAnimationFrame : un onglet en arrière-plan
    // ne rend plus d'images, et l'adresse doit suivre quand même.
    attente = setTimeout(() => { attente = 0; toolsSyncUrl(); }, 60);
  }).observe(document.body, { childList: true, subtree: true });
}

function _toolsAttendre(cond) {
  return new Promise(ok => {
    let n = 0;
    const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250);
  });
}

// Applique l'adresse. `complet` : retour du navigateur — une clé absente
// remet le défaut. Toute valeur lue est validée.
async function toolsLireUrl(u, complet) {
  const outil = toolsLegacy(u.get('outil', 'accueil', TOOLS_IDS), u);
  const cible = toolsPermis(outil) ? outil : 'accueil';

  if (cible === 'formulaires') {
    const id = u.get('formulaire');
    const fi = u.get('filtre', 'actifs', ['actifs', 'brouillon', 'publie', 'archive']);
    if (S.formu && (complet || u.a('filtre'))) S.formu.filtre = fi;
    if (/^\d+$/.test(String(id || ''))) {
      S.outil = 'formulaires';
      if (!(S.view === 'formulaire-edit' && S.formu && S.formu.courant && String(S.formu.courant.id) === String(id))) {
        toolsNav();
        if (typeof formuOuvrir === 'function') await formuOuvrir(Number(id));
      }
      const og = u.get('onglet', 'questions', ['questions', 'suivi']);
      if (S.view === 'formulaire-edit' && S.formu.onglet !== og && typeof formuSetOnglet === 'function') formuSetOnglet(og);
    } else if (S.outil !== 'formulaires' || S.view !== 'formulaires-list' || complet) {
      setView('formulaires-list');
    }
    // Fenêtres
    const ia = u.get('ia_formulaire', null, ['nouveau', 'modifier']);
    const env = u.get('envoi_formulaire'), rep = u.get('reponse_formulaire');
    const f = _toolsFenetre();
    if (ia && !(f && f.cle === 'ia_formulaire')) {
      if (ia === 'modifier') { if (S.view === 'formulaire-edit') formuIaOuvrir('modifier'); } else formuIaOuvrir('nouveau');
    } else if (env && /^\d+$/.test(env) && S.view === 'formulaire-edit' && !(f && f.cle === 'envoi_formulaire')) {
      formuEnvoiOuvrir(Number(env));
    } else if (rep && /^\d+$/.test(rep) && S.view === 'formulaire-edit' && !(f && f.cle === 'reponse_formulaire')) {
      formuReponseVoir(Number(rep));
    } else if (!ia && !env && !rep && f && complet) {
      _toolsFen = null; closeMroot();
    }
    return;
  }

  if (cible !== S.outil) { S.outil = cible; toolsRendre(); }
  else if (complet && cible === 'accueil') toolsRendre();

  if (cible === 'etiquettes' && window.MyToolsEtiquettes) {
    const poste = u.get('poste');
    await window.MyToolsEtiquettes.adresse.aller({ poste: poste, impression: u.get('impression') });
    const ad = poste === 'specifiques' && window.EtiqSpec && window.EtiqSpec.adresse;
    if (ad) {
      const a = { vue: u.get('vue', null), dossier: u.get('dossier', null), demande: u.get('demande', null),
                  modele: u.get('modele', null), modale: null };
      (ad.cles || []).forEach(k => { const v = u.get(k, null); if (v && v.length <= 60) a.modale = { cle: k, id: v }; });
      a.extra = {};
      (ad.clesExtra || []).forEach(k => { const v = u.get(k, null); if (v && v.length <= 120) a.extra[k] = v; });
      try { await ad.aller(a); } catch (e) {}
    }
  } else if (cible === 'traduction' && window.MyToolsTraduction) {
    window.MyToolsTraduction.adresse.aller({ de: u.get('de'), vers: u.get('vers') }, complet);
  } else if (cible === 'pdf') {
    const pg = u.get('page'), pan = u.get('panneau', null);
    const a = { page: /^\d+$/.test(String(pg || '')) ? Number(pg) : 1,
                panneau: pan && /^[a-z][a-z-]{1,30}$/.test(pan) ? pan : (complet ? null : undefined) };
    if (window.MyToolsPDF && window.MyToolsPDF.adresse) { try { window.MyToolsPDF.adresse.aller(a); } catch (e) {} }
    else _toolsAttente.pdf = a;
  } else if (cible === 'parapheur') {
    const id = u.get('demande');
    const a = { statut: u.get('statut', 'en_cours', ['a_signer', 'en_cours', 'signee', 'refusee', 'expiree', 'annulee', 'toutes']),
                demande: /^\d+$/.test(String(id || '')) ? Number(id) : null, signer: u.get('signer') === '1' };
    if (window.MyToolsParapheurModule) window.MyToolsParapheurModule.adresse.aller(a, complet);
    else _toolsAttente.parapheur = a;
  } else if (toolsOutil(cible) && toolsOutil(cible).util) {
    // Chaque sous-outil valide ses propres clés (MyToolsUtilitaires.CLES).
    const params = {};
    try { u.brut.forEach((v, k) => { if (!['outil', 'sous', 'parapheur'].includes(k) && /^[a-z_]{1,20}$/.test(k) && v.length <= 40) params[k] = v; }); } catch (e) {}
    const a = { sous: toolsOutil(cible).util, params: params };
    const m = window.MyToolsUtilitaires;
    if (m && document.querySelector('.tools-util-seul .tut')) m.adresse.aller(a);
    else _toolsAttente.utilitaires = a;
  } else if (cible === 'calculs' && window.MyToolsCalculs && window.MyToolsCalculs.adresse) {
    if (complet || u.a('calcul')) window.MyToolsCalculs.adresse.aller({ calcul: u.get('calcul', 'metrage', ['metrage', 'fronts', 'etiquettes', 'carton']) });
  } else if (cible === 'image') {
    const a = { mode: u.get('mode', 'ameliorer', ['ameliorer', 'vectoriser']) };
    if (window.MyToolsImage) { if (complet || u.a('mode')) window.MyToolsImage.adresse.aller(a); }
    else if (complet || u.a('mode')) _toolsAttente.image = a;
  }
  // Fenêtre de création du Parapheur, sur tout outil.
  const pn = u.get('parapheur', null, ['nouvelle']);
  const ppx = window.MyToolsParapheurModule;
  if (pn && TOOLS.droits && TOOLS.droits.parapheur_creer && !(ppx && ppx.adresse.creation())) {
    _toolsAttente.parapheurCreation = true;
    toolsCharger('parapheur')
      .then(() => window.MyToolsParapheurModule.adresse.ouvrirCreation())
      .catch(() => {})
      .then(() => { _toolsAttente.parapheurCreation = false; toolsSyncUrl(); });
  } else if (!pn && complet && ppx && ppx.adresse.creation()) ppx.adresse.fermerCreation();
}

// ── Démarrage ────────────────────────────────────────────────────────
async function toolsBoot() {
  toolsEnvelopper();
  const u = window.MySifaUrl ? MySifaUrl.lire() : { get: (k, d) => d, a: () => false };
  const outil = toolsLegacy(u.get('outil', 'accueil', TOOLS_IDS), u);
  S.outil = toolsPermis(outil) ? outil : 'accueil';
  // Formulaires et étiquettes ont besoin de leurs données avant de rouvrir
  // l'objet de l'adresse : on rend d'abord, on applique ensuite.
  if (S.outil !== 'formulaires') toolsRendre();
  try { await toolsLireUrl(u, false); } catch (e) {}
  _toolsUrlPrete = true;
  toolsSyncUrl();
  toolsObserver();
  if (window.MySifaUrl) MySifaUrl.surRetour(async v => { await toolsLireUrl(v, true); });
}

document.addEventListener('DOMContentLoaded', () => { toolsBoot(); });
