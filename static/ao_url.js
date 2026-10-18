/*
 * MySifa — MyAO : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Chargé AVANT le script principal de /ao ; ne fait que déclarer des
 * fonctions. S, render(), openDetail()… appartiennent au script principal.
 *
 * Inventaire du 18/10/2026 (ao_page.py + ao_produit_form.py, par nom
 * d'état) : section (appels d'offres, produits, fournisseurs), filtre de la
 * liste, AO ouvert et son onglet, fiche produit ; fenêtres : nouvel AO
 * (formulaire et assistant), ligne, série, ajout de fournisseur (deux
 * versions), fournisseur de l'AO, suivi d'un fournisseur, clôture, saisie
 * manuelle d'un prix, duplication, entrées des carnets fournisseurs et
 * clients, fiche et contact d'un fournisseur du référentiel, aperçus BAT et
 * étiquette d'un produit.
 * Hors adresse : les confirmations (envoi, suppression), le choix et la
 * création d'un client (sous-étapes d'un autre formulaire, rappel perdu au
 * rechargement), la création rapide d'un produit depuis l'assistant, les
 * recherches texte, les lignes dépliées.
 */
let _aoUrlPrete = false;

// Fenêtres posées dans #mroot (ou sur body) par une fonction : enveloppées,
// retenues par leur élément, fermées dès qu'il quitte la page.
let _aoSuivi = null;
function aoFenetreOuverte(cle, id) {
  const m = document.getElementById('mroot');
  _aoSuivi = { cle, id: String(id), el: null, essais: 0,
    avant: new Set([...document.body.children, ...(m ? m.children : [])]) };
  aoSyncUrl();
}
function _aoSuiviVivant() {
  const f = _aoSuivi;
  if (!f) return null;
  if (!f.el) {
    const m = document.getElementById('mroot');
    const dansMroot = m ? [...m.children].filter(n => !f.avant.has(n)) : [];
    const surBody = [...document.body.children].filter(n => !f.avant.has(n)
      && /-ov\b|overlay|modal/i.test(String(n.className || '')) && !/toast/i.test(String(n.className || '')));
    const c = dansMroot[dansMroot.length - 1] || surBody[surBody.length - 1];
    if (c) { f.el = c; f.avant = null; return f; }
    if (++f.essais > 200) { _aoSuivi = null; return null; }
    return f;
  }
  if (!f.el.isConnected) { _aoSuivi = null; return null; }
  return f;
}
const _AO_OUVREURS = [
  ['openTimelineModal',          'suivi_fournisseur', a => a[0]],
  ['openCloturerAoModal',        'cloture',           () => 'ao'],
  ['openCreateAoWizard',         'nouvel_ao',         () => 'assistant'],
  ['openAddFournisseurModalV2',  'ajout_fournisseur', () => 'assistant'],
  ['openEditFournisseurAoModal', 'fournisseur_ao',    a => a[0]],
  ['openBatPreview',             'apercu_bat',        a => a[0]],
  ['openEtiquettePreview',       'apercu_etiquette',  a => a[0]],
];
function aoEnvelopper() {
  _AO_OUVREURS.forEach(([nom, cle, valeur]) => {
    const orig = window[nom];
    if (typeof orig !== 'function' || orig.__adresse) return;
    const env = function () {
      let v = null;
      try { v = valeur(arguments); } catch (e) {}
      if (v !== null && v !== undefined && v !== '') aoFenetreOuverte(cle, v);
      return orig.apply(this, arguments);
    };
    env.__adresse = true;
    window[nom] = env;
  });
}

// Fenêtres décrites par S.modal (rendues par renderModal).
function _aoModaleS() {
  const d = S.modalData || {};
  switch (S.modal) {
    case 'create': return { cle: 'nouvel_ao', id: 'formulaire' };
    case 'ligne': return { cle: 'ligne', id: d.id || 'nouvelle' };
    case 'serie': return { cle: 'serie', id: d.ligne_id + ':' + (d.id || 'nouvelle') };
    case 'fourni': return { cle: 'ajout_fournisseur', id: 'formulaire' };
    case 'carnet-entry': return { cle: 'contact_carnet', id: d.id || 'nouveau' };
    case 'carnet-client-entry': return { cle: 'client_carnet', id: d.id || 'nouveau' };
    case 'fourni-ref': return { cle: 'fournisseur', id: d.id || 'nouveau' };
    case 'contact-ref': return { cle: 'contact', id: d.fournisseur_id + ':' + (d.id || 'nouveau') };
    case 'saisie-manuelle': return d.ctx ? { cle: 'saisie_prix', id: d.ctx.ligne_id + ':' + d.ctx.ao_fournisseur_id } : null;
    case 'duplicate-ao': return { cle: 'dupliquer_ao', id: d.id };
    default: return null;
  }
}
function _aoModale() { const f = _aoSuiviVivant(); return f ? { cle: f.cle, id: f.id } : _aoModaleS(); }

function aoParams() {
  const p = {};
  const sec = S.section || 'ao';
  if (sec !== 'ao') p.section = sec;
  let nav = sec;
  if (sec === 'ao') {
    if (S.view === 'detail' && S.ao) {
      p.ao = String(S.ao.id); nav += '/ao:' + S.ao.id;
      if (S.tab && S.tab !== 'comparaison') { p.onglet = S.tab; nav += '/' + S.tab; }
    } else if (S.filtre && S.filtre !== 'tous') p.filtre = S.filtre;
  } else if (sec === 'produits' && S.produitView === 'form' && S.produitForm) {
    const ref = S.produitForm.ref || '';
    p.produit = S.produitForm.id ? ref || String(S.produitForm.id) : 'nouveau';
    nav += '/produit:' + p.produit;
  }
  const mo = _aoModale();
  if (mo && mo.id != null && mo.id !== '') { p[mo.cle] = String(mo.id); nav += '/' + mo.cle; }
  return { params: p, nav };
}

function aoSyncUrl() {
  if (!_aoUrlPrete || !window.MySifaUrl || !S.user || !S.user.id) return;
  try { const r = aoParams(); MySifaUrl.ecrire(r.params, { navigation: r.nav }); } catch (e) {}
}
function aoUrlObserver() {
  if (typeof MutationObserver === 'undefined') return;
  let attente = 0;
  new MutationObserver(() => {
    if (attente) return;
    attente = requestAnimationFrame(() => { attente = 0; aoSyncUrl(); });
  }).observe(document.body, { childList: true, subtree: true });
}

const _aoDeux = v => { const i = String(v).indexOf(':'); return i < 0 ? [String(v), ''] : [String(v).slice(0, i), String(v).slice(i + 1)]; };
const _aoNum = v => (/^[0-9]+$/.test(String(v)) ? Number(v) : v);
const _aoLignes = () => (S.detail && S.detail.lignes) || [];
// Attend une liste chargée en arrière-plan (10 s au plus).
function _aoAttendre(cond) {
  return new Promise(ok => { let n = 0; const t = setInterval(() => { let v = false; try { v = !!cond(); } catch (e) {} if (v || ++n > 40) { clearInterval(t); ok(v); } }, 250); });
}

const _AO_REOUVRIR = {
  nouvel_ao: v => (v === 'assistant' ? openCreateAoWizard() : openModalCreate()),
  ligne: v => { if (v === 'nouvelle') return openModalLigne(null); const l = _aoLignes().find(x => String(x.id) === v); if (l) openModalLigne(l); },
  serie: v => {
    const [lid, sid] = _aoDeux(v); const l = _aoLignes().find(x => String(x.id) === lid); if (!l) return;
    if (sid === 'nouvelle') return openModalSerie(Number(lid), null);
    const s = (l.series || []).find(x => String(x.id) === sid); if (s) openModalSerie(Number(lid), s);
  },
  ajout_fournisseur: v => (v === 'assistant' ? openAddFournisseurModalV2() : openModalFourni()),
  contact_carnet: v => { if (v === 'nouveau') return openModalCarnetEntry(null); const c = (S.carnet || []).find(x => String(x.id) === v); if (c) openModalCarnetEntry(c); },
  client_carnet: v => { if (v === 'nouveau') return openModalCarnetClientEntry(null); const c = (S.carnetClients || []).find(x => String(x.id) === v); if (c) openModalCarnetClientEntry(c); },
  fournisseur: async v => { if (v === 'nouveau') return openModalFourniRef(null); await _aoAttendre(() => (S.fournisseurs || []).length); const f = (S.fournisseurs || []).find(x => String(x.id) === v); if (f) openModalFourniRef(f); },
  contact: async v => {
    const [fid, cid] = _aoDeux(v); await _aoAttendre(() => (S.fournisseurs || []).length); const f = (S.fournisseurs || []).find(x => String(x.id) === fid); if (!f) return;
    if (cid === 'nouveau') return openModalContact(Number(fid), null);
    const c = (f.contacts || []).find(x => String(x.id) === cid); if (c) openModalContact(Number(fid), c);
  },
  saisie_prix: v => {
    const [lid, fid] = _aoDeux(v);
    const l = _aoLignes().find(x => String(x.id) === lid);
    const f = ((S.detail && S.detail.fournisseurs) || []).find(x => String(x.id) === fid);
    if (l && f) openModalSaisieManuelle({ ligne_id: Number(lid), ao_fournisseur_id: Number(fid),
      nom_fournisseur: f.nom_fournisseur || f.nom || '', ref_produit: l.ref_produit || '' });
  },
  dupliquer_ao: v => { const a = (S.aos || []).find(x => String(x.id) === v); if (a) openModalDuplicate(a.id, a.reference, a.titre); },
  suivi_fournisseur: v => openTimelineModal(_aoNum(v)),
  cloture: () => openCloturerAoModal(),
  fournisseur_ao: v => openEditFournisseurAoModal(_aoNum(v)),
  apercu_bat: v => openBatPreview(_aoNum(v), (S.produitForm && S.produitForm.ref) || ''),
  apercu_etiquette: v => openEtiquettePreview(_aoNum(v), (S.produitForm && S.produitForm.ref) || '',
    typeof pfRefSifaValue === 'function' ? pfRefSifaValue() : ''),
};

function _aoFermer(mo) {
  if (!mo) return;
  if (_aoSuivi && mo.cle === _aoSuivi.cle) {
    const el = _aoSuivi.el, m = document.getElementById('mroot'); _aoSuivi = null;
    if (mo.cle === 'apercu_bat' && typeof closeBatPreview === 'function') closeBatPreview();
    else if (mo.cle === 'apercu_etiquette' && typeof closeEtiquettePreview === 'function') closeEtiquettePreview();
    else if (el) { if (m && m.contains(el)) m.innerHTML = ''; else el.remove(); }
    return;
  }
  closeModal();
}

// Applique l'adresse : section, AO ouvert, onglet, produit, puis fenêtre.
async function aoAllerUrl(complet) {
  const u = MySifaUrl.lire();
  const sec = u.get('section', 'ao', ['ao', 'produits', 'fournisseurs']);
  if (sec !== (S.section || 'ao')) goToAoSection(sec);
  if (sec === 'ao') {
    const id = u.get('ao', null);
    if (id && /^[0-9]+$/.test(id)) {
      if (!(S.view === 'detail' && S.ao && String(S.ao.id) === id)) await openDetail(Number(id));
      const t = u.get('onglet', null);
      if (t && t !== S.tab && /^[a-z_]{1,30}$/.test(t)) setTab(t);
      else if (!t && complet && S.tab !== 'comparaison') setTab('comparaison');
    } else {
      if (S.view === 'detail') backToList();
      const f = u.get('filtre', complet ? 'tous' : null, ['tous', 'brouillon', 'envoyee', 'cloturee', 'corbeille']);
      if (f && f !== S.filtre) { S.filtre = f; await loadList(); render(); }
    }
  } else if (sec === 'produits') {
    const ref = u.get('produit', null);
    if (ref === 'nouveau') { if (!(S.produitView === 'form' && S.produitForm && !S.produitForm.id)) await openProduitForm(null); }
    else if (ref) { if (!(S.produitView === 'form' && S.produitForm && S.produitForm.ref === ref)) await openProduitByRef(ref); }
    else if (complet && S.produitView === 'form') { S.produitView = 'list'; S.produitForm = null; render(); }
  }
  let voulue = null;
  Object.keys(_AO_REOUVRIR).forEach(cle => { const v = u.get(cle, null); if (v && v.length <= 120) voulue = { cle, id: v }; });
  const cour = _aoModale();
  if (cour && (!voulue || cour.cle !== voulue.cle || String(cour.id) !== String(voulue.id))) _aoFermer(cour);
  if (voulue && !_aoModale()) { try { await _AO_REOUVRIR[voulue.cle](voulue.id); } catch (e) {} }
}

// Fin du démarrage (après les chargements d'init()).
async function aoDemarrerUrl() {
  if (!window.MySifaUrl) return;
  aoEnvelopper();
  try { await aoAllerUrl(false); } catch (e) {}
  _aoUrlPrete = true;
  aoSyncUrl();
  aoUrlObserver();
}

if (window.MySifaUrl) {
  MySifaUrl.surRetour(async () => { if (_aoUrlPrete && S.user && S.user.id) await aoAllerUrl(true); });
}
