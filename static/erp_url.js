/*
 * MySifa — ERP RVGI (/erp) : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * L'ERP garde son routage par ancre, « #/<écran>?<paramètres> », que les
 * tuiles, le menu, les tableaux de bord et les liens extérieurs écrivent déjà
 * (location.hash = …, puis appliquerHash()). Ce fichier complète l'ancre avec
 * tout ce qu'elle ne disait pas, et la tient à jour sans relancer l'écran.
 *
 * Chargé avant le script de app/web/erp_page.py ; boot() appelle
 * erpBrancherUrl() juste avant son premier appliquerHash().
 *
 * Inventaire du 20/10/2026, par nom d'état (S.…, FPOP) :
 *   écran       filtres du rail (<nom>=<valeur> ; un filtre par défaut effacé
 *               s'écrit vide, « position= », pour ne pas revenir au
 *               rechargement), vue=piece, ratt, tri=<colonne>:<asc|desc>,
 *               page, fc.<colonne>=<op:valeur> (filtres d'en-tête),
 *               depuis + depuis_id + lien (grille ouverte depuis une pièce liée)
 *   fiche       fiche=<écran>:<id>,<écran>:<id>… (la modale et son fil de
 *               pièces liées, du premier au dernier ouvert) — aussi sur un
 *               tableau de bord
 *   fenêtre     filtre_col=<colonne> (petit formulaire de l'entonnoir)
 * Hors adresse : recherche de l'écran (q, lue si présente mais jamais écrite)
 * et recherche globale (son panneau n'existe que par le texte tapé), menu des
 * services (liste de navigation), ordre et épinglage des colonnes
 * (préférences enregistrées), infobulles des tableaux de bord.
 */
let _erpPret = false;
let _erpRemplacer = true;     // prochaine écriture : l'entrée vient d'être créée par la page
let _erpPop = false;

const _ERP_EXTRAS = ['tri', 'page', 'fiche', 'filtre_col', 'depuis', 'depuis_id', 'lien'];

function _erpQs(pairs) {
  return pairs.map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v == null ? '' : v)).join('&');
}
function _erpFicheTexte() {
  const f = document.getElementById('detail-fond');
  if (!f || !f.classList.contains('ouvert') || !S.pile || !S.pile.length) return '';
  return S.pile.map(p => p.ecran + ':' + encodeURIComponent(String(p.id))).join(',');
}
function _erpFicheLire(v) {
  return String(v || '').split(',').map(b => {
    const i = b.indexOf(':');
    if (i < 1) return null;
    let id = b.slice(i + 1);
    try { id = decodeURIComponent(id); } catch (e) {}
    return { ecran: b.slice(0, i), id: id };
  }).filter(Boolean);
}
function _erpFpop() {
  return (typeof FPOP !== 'undefined' && FPOP && FPOP.isConnected) ? (FPOP.getAttribute('data-col') || '') : '';
}

// État courant → [écran, paires de base, fiche, filtre_col].
function _erpEtat() {
  if (!S.ecran) return null;
  const base = [];
  if (!estTdb(S.ecran) && S.def) {
    Object.keys(S.filtres || {}).forEach(k => { if (S.filtres[k] !== '' && S.filtres[k] != null) base.push([k, S.filtres[k]]); });
    if (!S.contexte) {
      (S.def.filtres || []).forEach(f => {
        if (f.defaut != null && f.defaut !== '' && !(S.filtres[f.nom] !== '' && S.filtres[f.nom] != null)) base.push([f.nom, '']);
      });
    } else {
      base.push(['depuis', S.contexte.depuis], ['depuis_id', S.contexte.depuis_id], ['lien', S.contexte.lien]);
    }
    if (S.vue === 'piece') base.push(['vue', 'piece']);
    if (S.ratt && S.vue !== 'piece') base.push(['ratt', S.ratt]);
    if (S.tri) base.push(['tri', S.tri + ':' + (S.sens === 'desc' ? 'desc' : 'asc')]);
    if (S.page > 1) base.push(['page', S.page]);
    Object.keys(S.filtresCol || {}).forEach(k => { if (S.filtresCol[k]) base.push(['fc.' + k, S.filtresCol[k]]); });
  }
  return { ecran: S.ecran, base, fiche: _erpFicheTexte(), fpop: _erpFpop() };
}
function _erpHash(e) {
  if (!e) return '';
  const pairs = e.base.slice();
  if (e.fiche) pairs.push(['fiche', e.fiche]);
  if (e.fpop) pairs.push(['filtre_col', e.fpop]);
  return '/' + e.ecran + (pairs.length ? '?' + _erpQs(pairs) : '');
}

function erpSyncUrl() {
  if (!_erpPret || !window.MySifaUrl) return;
  try {
    const e = _erpEtat();
    let nav = e ? e.ecran : 'menu';
    if (e && e.fiche) nav += '|fiche:' + e.fiche;
    if (e && e.fpop) nav += '|filtre_col:' + e.fpop;
    const r = _erpRemplacer; _erpRemplacer = false;
    MySifaUrl.ecrire({}, { hash: _erpHash(e), navigation: nav, remplacer: r });
  } catch (err) {}
}

// Ancre lue : écran, paramètres (objet), dans l'ordre.
function _erpDecoupe(h) {
  const m = String(h || '').match(/^#\/([a-z_]+)(?:\?(.*))?$/);
  if (!m) return null;
  return { ecran: m[1], params: lireParamsHash(m[2] || '') };
}
function _erpCleBase(ecran, params) {
  const p = Object.assign({}, params);
  delete p.fiche; delete p.filtre_col; delete p.q;
  return ecran + '?' + Object.keys(p).sort().map(k => k + '=' + p[k]).join('&');
}

function _erpOuvrirFiche(v) {
  const pile = _erpFicheLire(v);
  if (!pile.length) return;
  S.pile = pile;
  if (!estTdb(S.ecran) && pile[0].ecran === S.ecran) { S.selection = pile[0].id; try { renderGrille(); } catch (e) {} }
  rendreDetail();
}
function _erpOuvrirFpop(nom) {
  if (!nom) return;
  const th = [...document.querySelectorAll('#thead th[data-col]')].find(t => t.getAttribute('data-col') === nom);
  if (th && _erpFpop() !== nom) fpopOuvrir(nom, th);
}
// Fiche et entonnoir voulus par l'ancre, sur l'écran déjà affiché.
function _erpAjuster(params) {
  const voulue = params.fiche || '';
  if (voulue !== _erpFicheTexte()) {
    if (voulue) _erpOuvrirFiche(voulue); else fermerDetail();
  }
  const f = params.filtre_col || '';
  if (f !== _erpFpop()) { fpopFermer(); _erpOuvrirFpop(f); }
}

function erpBrancherUrl() {
  if (_erpPret || !window.MySifaUrl) return;

  // Un écran qui s'ouvre : les paramètres que la page ne connaît pas sont
  // posés une fois la grille montée (S.apresEcran), avant son premier chargement.
  const oe = window.ouvrirEcran;
  window.ouvrirEcran = function (cle, prefiltres) {
    const p = Object.assign({}, prefiltres || {});
    const x = {};
    Object.keys(p).forEach(k => { if (_ERP_EXTRAS.indexOf(k) !== -1 || k.indexOf('fc.') === 0) { x[k] = p[k]; delete p[k]; } });
    if (x.depuis && x.depuis_id && x.lien !== undefined && !S.ctxAttente) {
      S.ctxAttente = { cible: cle, depuis: x.depuis, depuis_id: x.depuis_id, lien: Number(x.lien) };
    }
    const reste = Object.keys(x).filter(k => ['depuis', 'depuis_id', 'lien'].indexOf(k) === -1);
    if (reste.length && !S.apresEcran) {
      S.apresEcran = async function () {
        const t = /^(.+):(asc|desc)$/.exec(x.tri || '');
        if (t) { S.tri = t[1]; S.sens = t[2]; }
        const pg = parseInt(x.page || '1', 10); if (pg > 1) S.page = pg;
        Object.keys(x).forEach(k => { if (k.indexOf('fc.') === 0 && x[k]) S.filtresCol[k.slice(3)] = x[k]; });
        await charger();
        if (x.fiche) _erpOuvrirFiche(x.fiche);
        if (x.filtre_col) _erpOuvrirFpop(x.filtre_col);
      };
    }
    return oe.call(this, cle, Object.keys(p).length ? p : (prefiltres ? {} : null));
  };

  // Tableau de bord : seule la fiche s'y ajoute.
  const ot = window.ouvrirTdb;
  window.ouvrirTdb = async function (cle) {
    const r = await ot.apply(this, arguments);
    const d = _erpDecoupe(location.hash);
    if (d && d.ecran === cle && S.ecran === cle && d.params.fiche) _erpOuvrirFiche(d.params.fiche);
    return r;
  };

  // Une ancre qui ne change que la fiche ou l'entonnoir (fermer une fiche,
  // Retour d'une pièce liée) ne relance pas l'écran : la grille garde ses
  // lignes et son défilement.
  const ah = window.appliquerHash;
  window.appliquerHash = function () {
    const d = _erpDecoupe(location.hash);
    const e = _erpEtat();
    // Une recherche portée par l'ancre (tuile, lien) relance l'écran.
    const qVise = d && d.params.q !== undefined && d.params.q !== (S.q || '');
    if (d && e && d.ecran === e.ecran && !qVise) {
      const cur = {};
      e.base.forEach(([k, v]) => { cur[k] = String(v); });
      if (_erpCleBase(d.ecran, d.params) === _erpCleBase(e.ecran, cur)) { _erpAjuster(d.params); return; }
    }
    return ah.apply(this, arguments);
  };

  // Entrée créée par la page (location.hash = …) : la mettre au propre sur
  // place. Au Retour, popstate arrive juste avant hashchange.
  window.addEventListener('popstate', () => { _erpPop = true; });
  window.addEventListener('hashchange', () => { if (!_erpPop) _erpRemplacer = true; _erpPop = false; });
  MySifaUrl.surRetour(() => { /* appliquerHash, sur hashchange, réapplique l'ancre */ });

  _erpPret = true;
  if (typeof MutationObserver !== 'undefined') {
    let attente = 0;
    new MutationObserver(() => {
      if (attente) return;
      attente = requestAnimationFrame(() => { attente = 0; erpSyncUrl(); });
    }).observe(document.body, { childList: true, subtree: true });
  }
}
