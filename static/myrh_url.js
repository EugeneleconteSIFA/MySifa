/*
 * MySifa — MyRH : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Servie par le gabarit commun app/web/html.py (code « RH outil » de
 * compta_rh_outil*_assets.py) : chargé sur toutes ses applis, inactif hors
 * de /rh. Ne fait que déclarer des fonctions.
 *
 * Inventaire du 18/10/2026, par nom d'état : filtres du tableau (dossier
 * complet / incomplet, service, contrat) ; fenêtres : nouvel employé,
 * contrat d'un employé (`nouvel_employe=existant|nouveau` : suivre un compte
 * ou en créer un), pièces d'un élément, catégories de formations,
 * justificatifs d'une formation, « exigé pour ».
 * 31/10/2026 : onglet Catalogues (`onglet=catalogues`, `liste=documents` ;
 * formations par défaut), qui remplace la fenêtre du catalogue. L'ancien
 * `catalogue=<liste>` mène à l'onglet.
 * Hors adresse : les confirmations et le petit sélecteur d'ajout (sous-étape
 * d'un geste).
 *
 * Les fenêtres (rhOutilFenetre) s'EMPILENT — les justificatifs s'ouvrent
 * au-dessus du catalogue : l'adresse porte celle du dessus ; à sa fermeture,
 * elle revient à celle d'en dessous.
 */
let _myrhUrlPrete = false;
let _myrhDemarre = false;
const _myrhSurPage = () => location.pathname === '/rh';
let _myrhPile = [];                  // [{ cle, id, el, avant, essais }]

function myrhFenetreOuverte(cle, id) {
  _myrhPile.push({ cle, id: String(id), el: null, essais: 0, avant: new Set(document.querySelectorAll('.rho-ov')) });
  myrhSyncUrl();
}
// Une fenêtre change d'état sans se fermer (Ajouter un employé : compte
// existant / nouveau compte) : l'entrée du dessus suit.
function myrhFenetreChange(cle, id) {
  const f = [..._myrhPile].reverse().find(x => x.cle === cle);
  if (f) { f.id = String(id); myrhSyncUrl(); }
}
function _myrhDessus() {
  // Repère l'élément des fenêtres qui viennent de s'ouvrir, oublie les fermées.
  _myrhPile.forEach(f => {
    if (!f.el && f.avant) {
      const c = [...document.querySelectorAll('.rho-ov')].filter(n => !f.avant.has(n)).pop();
      if (c) { f.el = c; f.avant = null; } else if (++f.essais > 200) f.mort = true;
    }
  });
  _myrhPile = _myrhPile.filter(f => !f.mort && (!f.el || f.el.isConnected));
  return _myrhPile[_myrhPile.length - 1] || null;
}

const _MYRH_OUVREURS = [
  ['rhOutilNouvelEmploye',   'nouvel_employe', a => (a[0] === 'nouveau' && S.rhOutilPeutCreer) ? 'nouveau' : 'existant'],
  ['rhOutilModifierContrat', 'contrat',        a => a[0] && a[0].id],
  ['rhOutilPieces',          'pieces',         a => (a[0] && a[1] && a[2]) ? a[0].cle + ':' + a[1].id + ':' + a[2].id : null],
  ['rhOutilGererCategories', 'categories',     () => 'formations'],
  ['rhOutilJustificatifs',   'justificatifs',  a => a[0] && a[0].id],
  ['rhOutilExigePour',       'exigee_pour',    a => (a[0] && a[1]) ? a[0].cle + ':' + a[1].id : null],
];
function myrhEnvelopper() {
  _MYRH_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      let v = null;
      try { v = valeur(arguments); } catch (e) {}
      if (v !== null && v !== undefined && v !== '') myrhFenetreOuverte(cle, v);
      return orig.apply(this, arguments);
    };
    env.__adresse = true;
    window[nom] = env;
  });
}

const _MYRH_ONGLETS = ['employes', 'catalogues'];
const _myrhListes = () => (typeof RH_OUTIL_LISTES !== 'undefined' ? RH_OUTIL_LISTES : []).map(L => L.cle);

function myrhParams() {
  const p = {};
  let nav = 'tableau';
  if (S.rhOnglet === 'catalogues') {
    // Filtres du tableau : propres à l'onglet Employés.
    p.onglet = 'catalogues';
    const liste = S.rhCatalogue || _myrhListes()[0];
    if (liste !== _myrhListes()[0]) p.liste = liste;
    nav = 'catalogues:' + liste;
  } else {
    if (S.rhOutilFiltre && S.rhOutilFiltre !== 'tous') p.dossier = S.rhOutilFiltre;
    if (S.rhOutilFiltreService) p.service = S.rhOutilFiltreService;
    if (S.rhOutilFiltreContrat) p.contrat_type = S.rhOutilFiltreContrat;
  }
  const f = _myrhDessus();
  if (f) { p[f.cle] = f.id; nav += '/' + f.cle + ':' + f.id; }
  return { params: p, nav };
}

function myrhSyncUrl() {
  if (!_myrhUrlPrete || !_myrhSurPage() || !window.MySifaUrl || !S.user || S.app !== 'myrh') return;
  try { const r = myrhParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function myrhUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; myrhSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

function _myrhAttendre(cond) {
  return new Promise(ok => { let n = 0; const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250); });
}
const _myrhListe = cle => (typeof RH_OUTIL_LISTES !== 'undefined' ? RH_OUTIL_LISTES : []).find(L => L.cle === cle);
const _myrhMembre = id => (S.rhOutilMembres || []).find(m => String(m.id) === String(id));
async function _myrhElementCatalogue(L, id) {
  try { const d = await api('/api/rh-outil/' + L.cle + '/catalogue'); return (d.elements || []).find(x => String(x.id) === String(id)) || null; }
  catch (e) { return null; }
}
const _myrhRafraichir = () => {
  if (typeof rhOutilLoad === 'function') rhOutilLoad();
  if (typeof rhOutilCataloguesRafraichir === 'function') rhOutilCataloguesRafraichir();
};

const _MYRH_REOUVRIR = {
  // `formulaire` : lien d'avant le 31/10/2026, quand la fenêtre ne faisait que créer.
  nouvel_employe: v => rhOutilNouvelEmploye(v === 'nouveau' || v === 'formulaire' ? 'nouveau' : 'existant'),
  contrat: v => { const m = _myrhMembre(v); if (m) rhOutilModifierContrat(m); },
  pieces: v => {
    const [cle, mid, xid] = v.split(':'); const L = _myrhListe(cle), m = _myrhMembre(mid);
    const x = m && (m[cle] || []).find(i => String(i.id) === xid);
    if (L && m && x) rhOutilPieces(L, m, x);
  },
  categories: () => rhOutilGererCategories(_myrhRafraichir),
  justificatifs: async v => { const L = _myrhListe('formations'); const x = L && await _myrhElementCatalogue(L, v); if (x) rhOutilJustificatifs(x, _myrhRafraichir); },
  exigee_pour: async v => {
    const [cle, xid] = v.split(':'); const L = _myrhListe(cle); const x = L && await _myrhElementCatalogue(L, xid);
    if (x) rhOutilExigePour(L, x, _myrhRafraichir);
  },
};

async function myrhAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const ou = (k, def) => (u.a(k) ? u.get(k, def) : (complet ? def : undefined));
  const patch = {};
  // Onglet et liste. Ancien lien `catalogue=<liste>` (fenêtre) : l'onglet.
  const ancien = u.get('catalogue', null, _myrhListes());
  let onglet = ancien ? 'catalogues' : ou('onglet', 'employes');
  if (onglet !== undefined && _MYRH_ONGLETS.indexOf(onglet) === -1) onglet = 'employes';
  if (onglet !== undefined && onglet !== (S.rhOnglet || 'employes')) patch.rhOnglet = onglet;
  const liste = ancien || ou('liste', _myrhListes()[0]);
  if (liste !== undefined && _myrhListes().indexOf(liste) !== -1 && liste !== (S.rhCatalogue || _myrhListes()[0])) patch.rhCatalogue = liste;
  if ((onglet || S.rhOnglet) !== 'catalogues') {
    const d = ou('dossier', 'tous'); if (d !== undefined && ['tous', 'complet', 'incomplet'].indexOf(d) !== -1 && d !== (S.rhOutilFiltre || 'tous')) patch.rhOutilFiltre = d;
    const s = ou('service', ''); if (s !== undefined && s !== (S.rhOutilFiltreService || '')) patch.rhOutilFiltreService = s;
    const c = ou('contrat_type', ''); if (c !== undefined && c !== (S.rhOutilFiltreContrat || '')) patch.rhOutilFiltreContrat = c;
  }
  if (Object.keys(patch).length) set(patch);
  if (patch.rhOnglet === 'catalogues' && typeof rhOutilCataloguesRafraichir === 'function') rhOutilCataloguesRafraichir();
  // Fenêtre : celle du dessus seulement.
  let voulue = null;
  Object.keys(_MYRH_REOUVRIR).forEach(k => { const v = u.get(k, null); if (v && v.length <= 120) voulue = { cle: k, id: v }; });
  const dessus = _myrhDessus();
  if (dessus && (!voulue || dessus.cle !== voulue.cle || dessus.id !== voulue.id)) {
    // Retour depuis une fenêtre empilée : on ferme celle du dessus seulement.
    // Un clic sur le fond passe par la fermeture de la fenêtre elle-même
    // (rhOutilFenetre), qui retire aussi son écouteur clavier.
    _myrhPile.pop();
    if (dessus.el) dessus.el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  }
  const apres = _myrhDessus();
  if (voulue && !(apres && apres.cle === voulue.cle && apres.id === voulue.id)) {
    await _myrhAttendre(() => S.rhOutilLoaded);
    try { await _MYRH_REOUVRIR[voulue.cle](voulue.id); } catch (e) {}
  }
}

// Appelé par renderMyRH() à chaque rendu ; ne démarre qu'une fois.
function myrhDemarrerUrl() {
  if (_myrhDemarre || !_myrhSurPage() || !window.MySifaUrl) return;
  _myrhDemarre = true;
  myrhEnvelopper();
  setTimeout(async () => {
    try { await myrhAllerUrl(false); } catch (e) {}
    _myrhUrlPrete = true;
    myrhSyncUrl();
    myrhUrlObserver();
  }, 0);
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_myrhUrlPrete && _myrhSurPage() && S.user) await myrhAllerUrl(true); });
}
