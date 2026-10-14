/* MyPrint — étiquettes spécifiques : bibliothèque, impression en série,
 * historique, demandes de nouveau format.
 *
 * Monté dans MyStock › Traçabilité (poste « specifiques ») par
 * `EtiqSpec.mount(conteneur)`. L'état vit dans `ES` et le DOM dans
 * `ES.host`, un nœud créé une seule fois : quand MyStock reconstruit son
 * contenu, mount() rattache le même nœud au nouveau conteneur au lieu de
 * tout redessiner — l'éditeur garde ses saisies en cours.
 *
 * L'éditeur vit dans mysifa_etiq_editeur.js (EtiqSpec.editeur).
 * Les données saisies s'affichent par textContent, jamais par innerHTML.
 */
(function () {
  'use strict';

  const API = '/api/print/specifiques';
  const FORMATS = [
    [100, 150], [100, 100], [100, 50], [105, 50], [120, 105], [148, 105], [60, 40], [50, 25],
  ];
  const LS_IMPRIMANTE = 'mysifa_etiq_spec_imprimante';
  const LS_MODELE_IA = 'mysifa_etiq_spec_modele_ia';

  const ES = {
    host: null, view: 'liste', boot: null, dossierId: null, q: '',
    demandes: null, demandeSel: null, imprimantes: null,
  };

  // ── Outils ──────────────────────────────────────────────────────────
  function h(tag, attrs, ...enfants) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'cls') n.className = v;
      else if (k === 'text') n.textContent = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(n.style, v);
      else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
      else if (k === 'value') n.value = v;
      else if (k === 'checked') n.checked = !!v;
      else n.setAttribute(k, v === true ? '' : v);
    }
    for (const e of enfants.flat()) {
      if (e === null || e === undefined || e === false) continue;
      n.appendChild(typeof e === 'string' || typeof e === 'number' ? document.createTextNode(String(e)) : e);
    }
    return n;
  }
  // Icônes absentes du jeu de MyStock. Chaînes constantes, aucune donnée.
  const ICONES = {
    'message-square': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    'paperclip': '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
    'type': '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/>',
    'barcode': '<path d="M3 5v14M6 5v14M10 5v14M13 5v14M15 5v14M18 5v14M21 5v14"/>',
    'square': '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>',
    'minus': '<line x1="5" y1="12" x2="19" y2="12"/>',
    'arrow-up': '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
    'arrow-down': '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
    'check': '<polyline points="20 6 9 17 4 12"/>',
    'save': '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  };
  function ic(nom, taille) {
    taille = taille || 15;
    if (ICONES[nom]) {
      const t = document.createElement('template');
      t.innerHTML = `<svg width="${taille}" height="${taille}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONES[nom]}</svg>`;
      return t.content.firstChild;
    }
    try { if (typeof window.iconEl === 'function') return window.iconEl(nom, taille); } catch (e) {}
    return document.createTextNode('');
  }
  function toast(m, t) {
    if (typeof window.showToast === 'function') window.showToast(m, t || 'success');
  }
  async function api(chemin, opts) {
    opts = opts || {};
    const init = { credentials: 'include', cache: 'no-store', method: opts.method || 'GET' };
    if (opts.form) init.body = opts.form;
    else if (opts.body !== undefined) {
      init.body = JSON.stringify(opts.body);
      init.headers = { 'Content-Type': 'application/json' };
    }
    const r = await fetch((opts.brut ? '' : API) + chemin, init);
    if (r.status === 401) { window.location.href = '/'; throw new Error('Session expirée.'); }
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      const d = e.detail;
      throw new Error(typeof d === 'string' ? d : ('Erreur ' + r.status));
    }
    if (opts.blob) return r.blob();
    return r.json();
  }
  function fmtDate(s) {
    if (!s) return '';
    const [d, t] = String(s).split('T');
    const [y, m, j] = d.split('-');
    return `${j}/${m}/${y}` + (t ? ' ' + t.slice(0, 5) : '');
  }
  function fmtNum(n) {
    const x = parseFloat(n);
    return Number.isFinite(x) ? String(Math.round(x * 10) / 10).replace('.', ',') : '';
  }
  function fmtFormat(m) { return `${fmtNum(m.largeur_mm)} × ${fmtNum(m.hauteur_mm)} mm · ${m.dpi} dpi`; }
  function dossierNom(id) {
    const d = (ES.boot?.dossiers || []).find(x => x.id === id);
    return d ? d.nom : '';
  }
  function champ(label, input, aide) {
    return h('label', { cls: 'es-champ' },
      h('span', { cls: 'es-champ-label', text: label }), input,
      aide ? h('span', { cls: 'es-champ-aide', text: aide }) : null);
  }
  function selectDossiers(valeur, avecVide) {
    const s = h('select', { cls: 'es-input' });
    if (avecVide) s.appendChild(h('option', { value: '', text: '— Aucun —' }));
    for (const d of ES.boot.dossiers) s.appendChild(h('option', { value: d.id, text: d.nom }));
    if (valeur) s.value = String(valeur);
    return s;
  }
  // Choix du modèle de l'assistant : liste servie par le serveur (config.py),
  // dernier choix retenu sur le poste. L'aide sous la liste suit la sélection.
  function selectModeleIa() {
    const ref = ES.boot.referentiel;
    const liste = ref.modeles_ia || [];
    const s = h('select', { cls: 'es-input', title: 'Modèle utilisé par l\'assistant' },
      ...liste.map(m => h('option', { value: m.id, text: m.libelle })));
    let mem = null;
    try { mem = localStorage.getItem(LS_MODELE_IA); } catch (e) {}
    s.value = liste.some(m => m.id === mem) ? mem : ref.modele_ia_defaut;
    const aide = h('span', { cls: 'es-champ-aide' });
    const maj = () => { aide.textContent = (liste.find(m => m.id === s.value) || {}).aide || ''; };
    s.addEventListener('change', () => { try { localStorage.setItem(LS_MODELE_IA, s.value); } catch (e) {} maj(); });
    maj();
    return { select: s, bloc: h('label', { cls: 'es-champ' }, h('span', { cls: 'es-champ-label', text: 'Modèle' }), s, aide) };
  }

  function bouton(label, onclick, variante, icone) {
    return h('button', { cls: 'es-btn' + (variante ? ' es-btn-' + variante : ''), type: 'button', onclick },
      icone ? ic(icone, 15) : null, label);
  }
  function occupe(btn, oui, texte) {
    if (!btn) return;
    if (oui) { btn.dataset.lbl = btn.textContent; btn.disabled = true; if (texte) btn.textContent = texte; }
    else { btn.disabled = false; if (btn.dataset.lbl) btn.textContent = btn.dataset.lbl; }
  }

  // ── Modale ──────────────────────────────────────────────────────────
  // Posée sur document.body, pas dans MyStock : un rafraîchissement de la
  // page hôte ne la détruit pas pendant qu'on la remplit.
  function modale(titre, corps, actions, large) {
    fermerModale();
    const fond = h('div', { cls: 'es-modale-fond', id: 'es-modale',
      onmousedown: (e) => { if (e.target === fond) fermerModale(); } });
    const boite = h('div', { cls: 'es-modale' + (large ? ' es-modale-large' : ''), role: 'dialog' },
      h('div', { cls: 'es-modale-tete' },
        h('div', { cls: 'es-modale-titre', text: titre }),
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Fermer', onclick: fermerModale }, '×')),
      h('div', { cls: 'es-modale-corps' }, corps),
      actions && actions.length ? h('div', { cls: 'es-modale-pied' }, actions) : null);
    fond.appendChild(boite);
    document.body.appendChild(fond);
    document.addEventListener('keydown', escModale);
    requestAnimationFrame(() => boite.querySelector('input:not([type=file]),textarea,select')?.focus());
    return boite;
  }
  function escModale(e) { if (e.key === 'Escape') fermerModale(); }
  function fermerModale() {
    document.getElementById('es-modale')?.remove();
    document.removeEventListener('keydown', escModale);
  }
  function confirmer(message, libelle, action) {
    const b = bouton(libelle, async () => { occupe(b, true); try { await action(); fermerModale(); } catch (e) { toast(e.message, 'danger'); occupe(b, false); } }, 'danger');
    modale('Confirmer', h('p', { cls: 'es-texte', text: message }), [bouton('Annuler', fermerModale), b]);
  }

  // ── Chargement ──────────────────────────────────────────────────────
  async function charger() {
    ES.boot = await api('/bootstrap');
    if (ES.dossierId && !ES.boot.dossiers.some(d => d.id === ES.dossierId)) ES.dossierId = null;
  }
  async function imprimantes() {
    if (!ES.imprimantes) ES.imprimantes = await api('/api/print/my-imprimantes', { brut: true });
    return ES.imprimantes;
  }

  function rendre() {
    if (!ES.host) return;
    ES.host.replaceChildren();
    if (!ES.boot) { ES.host.appendChild(h('div', { cls: 'es-vide', text: 'Chargement…' })); return; }
    // Le contenu qui dépend d'éléments déjà dans la page se remplit après
    // l'insertion, et pas dans un requestAnimationFrame : un onglet en
    // arrière-plan ne les déclenche pas, l'écran resterait vide.
    if (ES.view === 'editeur' && window.EtiqSpec.editeur) {
      ES.host.appendChild(window.EtiqSpec.editeur.vue());
      window.EtiqSpec.editeur.apres();
    } else if (ES.view === 'demandes') ES.host.appendChild(vueDemandes());
    else { ES.host.appendChild(vueListe()); rendreCartes(); }
  }

  // ── Vue liste ───────────────────────────────────────────────────────
  function vueListe() {
    const b = ES.boot;
    const recherche = h('input', { cls: 'es-input es-recherche', id: 'es-recherche', type: 'search',
      placeholder: 'Rechercher (nom, description, format, dossier)…', value: ES.q, autocomplete: 'off',
      oninput: (e) => { ES.q = e.target.value; rendreCartes(); },
      onkeydown: (e) => { if (e.key === 'Escape') { e.target.value = ''; ES.q = ''; rendreCartes(); } } });

    const tete = h('div', { cls: 'es-tete' },
      h('div', { cls: 'es-titre' }, 'Étiquettes spécifiques',
        h('span', { cls: 'es-sous-titre', text: `${b.modeles.length} étiquette${b.modeles.length > 1 ? 's' : ''} · ${b.dossiers.length} dossier${b.dossiers.length > 1 ? 's' : ''}` })),
      h('div', { cls: 'es-actions' },
        bouton(b.is_super ? `Demandes${b.demandes_ouvertes ? ' (' + b.demandes_ouvertes + ')' : ''}` : 'Mes demandes',
          () => { ES.view = 'demandes'; ES.demandeSel = null; chargerDemandes(); }, b.demandes_ouvertes ? 'actif' : '', 'inbox'),
        bouton('Demander un nouveau format', modaleDemande, '', 'message-square'),
        bouton('Nouvelle étiquette', () => modaleNouvelle(), 'accent', 'plus')));

    const listeDossiers = h('div', { cls: 'es-dossiers' },
      h('div', { cls: 'es-dossiers-titre' }, 'Dossiers',
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Nouveau dossier', onclick: () => modaleDossier() }, ic('plus', 14))),
      ligneDossier(null, 'Toutes les étiquettes', b.modeles.length),
      ...b.dossiers.map(d => ligneDossier(d, d.nom, d.nb)),
      b.dossiers.length ? null : h('div', { cls: 'es-aide', text: 'Créer un premier dossier (un par client, par exemple) pour y ranger les étiquettes.' }));

    const cartes = h('div', { cls: 'es-cartes', id: 'es-cartes' });
    const corps = h('div', { cls: 'es-corps' }, listeDossiers,
      h('div', { cls: 'es-principal' }, h('div', { cls: 'es-barre-recherche' }, recherche), cartes));
    return h('div', { cls: 'es-liste' }, tete, corps);
  }

  function ligneDossier(d, nom, nb) {
    const id = d ? d.id : null;
    return h('div', { cls: 'es-dossier' + (ES.dossierId === id ? ' actif' : ''),
      onclick: () => { ES.dossierId = id; rendre(); } },
      ic(d ? 'folder' : 'layers', 15),
      h('span', { cls: 'es-dossier-nom', text: nom }),
      h('span', { cls: 'es-badge', text: String(nb) }),
      d ? h('span', { cls: 'es-dossier-outils' },
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Renommer',
          onclick: (e) => { e.stopPropagation(); modaleDossier(d); } }, ic('edit', 13)),
        d.nb ? null : h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Archiver le dossier',
          onclick: (e) => { e.stopPropagation(); confirmer(`Archiver le dossier « ${d.nom} » ?`, 'Archiver', async () => {
            await api('/dossiers/' + d.id, { method: 'DELETE' }); toast('Dossier archivé.'); await charger(); rendre(); }); } }, ic('trash-2', 13))) : null);
  }

  function rendreCartes() {
    const zone = ES.host && ES.host.querySelector('#es-cartes');
    if (!zone) return;
    const q = ES.q.trim().toLowerCase();
    let liste = ES.boot.modeles.filter(m => ES.dossierId === null || m.dossier_id === ES.dossierId);
    if (q) liste = liste.filter(m => [m.nom, m.description, fmtFormat(m), dossierNom(m.dossier_id)]
      .some(x => String(x || '').toLowerCase().includes(q)));
    zone.replaceChildren();
    if (!liste.length) {
      zone.appendChild(h('div', { cls: 'es-vide' },
        q ? `Aucun résultat pour « ${ES.q.trim()} »` :
          (ES.boot.dossiers.length ? 'Aucune étiquette dans ce dossier.' : 'Aucune étiquette pour l\'instant.')));
      return;
    }
    for (const m of liste) zone.appendChild(carte(m));
  }

  function carte(m) {
    const ratio = Math.max(0.35, Math.min(2.2, m.hauteur_mm / m.largeur_mm));
    return h('div', { cls: 'es-carte' },
      h('div', { cls: 'es-carte-haut', onclick: () => ouvrirEditeur(m.id), title: 'Ouvrir dans l\'éditeur' },
        h('div', { cls: 'es-vignette', style: { width: (34 / Math.max(1, ratio)) + 'px', height: Math.min(44, 34 * ratio) + 'px' } }),
        h('div', { cls: 'es-carte-info' },
          h('div', { cls: 'es-carte-nom', text: m.nom }),
          h('div', { cls: 'es-carte-format', text: fmtFormat(m) + (ES.dossierId === null ? ' · ' + dossierNom(m.dossier_id) : '') }))),
      m.description ? h('div', { cls: 'es-carte-desc', text: m.description }) : null,
      h('div', { cls: 'es-carte-pied' },
        bouton('Imprimer', () => modaleImpression(m), 'accent', 'printer'),
        bouton('Modifier', () => ouvrirEditeur(m.id), '', 'edit'),
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Dupliquer', onclick: () => modaleDupliquer(m) }, ic('copy', 15)),
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Historique des impressions', onclick: () => modaleHistorique(m) }, ic('clock', 15)),
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', title: 'Archiver', onclick: () => confirmer(
          `Archiver l'étiquette « ${m.nom} » ? Son historique d'impression est conservé.`, 'Archiver', async () => {
            await api('/modeles/' + m.id, { method: 'DELETE' }); toast('Étiquette archivée.'); await charger(); rendre(); }) }, ic('trash-2', 15))));
  }

  // ── Dossiers / création / duplication ─────────────────────────────
  function modaleDossier(d) {
    const nom = h('input', { cls: 'es-input', value: d ? d.nom : '', maxlength: 80, placeholder: 'Ex. nom du client' });
    const desc = h('input', { cls: 'es-input', value: d ? (d.description || '') : '', maxlength: 500 });
    const ok = bouton(d ? 'Renommer' : 'Créer', async () => {
      occupe(ok, true);
      try {
        const r = await api(d ? '/dossiers/' + d.id : '/dossiers', { method: d ? 'PATCH' : 'POST', body: { nom: nom.value, description: desc.value } });
        if (!d) ES.dossierId = r.id;
        fermerModale(); toast(d ? 'Dossier renommé.' : 'Dossier créé.'); await charger(); rendre();
      } catch (e) { toast(e.message, 'danger'); occupe(ok, false); }
    }, 'accent');
    nom.addEventListener('keydown', e => { if (e.key === 'Enter') ok.click(); });
    modale(d ? 'Renommer le dossier' : 'Nouveau dossier', h('div', { cls: 'es-form' },
      champ('Nom', nom), champ('Description', desc, 'Facultatif.')), [bouton('Annuler', fermerModale), ok]);
  }

  function modaleNouvelle() {
    if (!ES.boot.dossiers.length) { toast('Créer d\'abord un dossier.', 'info'); modaleDossier(); return; }
    const nom = h('input', { cls: 'es-input', maxlength: 120, placeholder: 'Ex. Palette SSCC 100×150' });
    const dossier = selectDossiers(ES.dossierId || ES.boot.dossiers[0].id);
    const desc = h('textarea', { cls: 'es-input', rows: 2, maxlength: 1000 });
    const larg = h('input', { cls: 'es-input', type: 'number', step: '0.5', min: 10, value: 100 });
    const haut = h('input', { cls: 'es-input', type: 'number', step: '0.5', min: 5, value: 150 });
    const dpi = h('select', { cls: 'es-input' }, ...ES.boot.referentiel.dpi.map(x => h('option', { value: x, text: x + ' dpi' })));
    const formats = h('div', { cls: 'es-puces' }, ...FORMATS.map(([l, ht]) =>
      h('button', { cls: 'es-puce', type: 'button', onclick: () => { larg.value = l; haut.value = ht; }, text: `${l}×${ht}` })));
    const ok = bouton('Créer et ouvrir', async () => {
      occupe(ok, true);
      try {
        const r = await api('/modeles', { method: 'POST', body: {
          dossier_id: parseInt(dossier.value, 10), nom: nom.value, description: desc.value,
          largeur_mm: parseFloat(larg.value), hauteur_mm: parseFloat(haut.value), dpi: parseInt(dpi.value, 10) } });
        fermerModale(); toast('Étiquette créée.'); await charger(); ouvrirEditeur(r.id);
      } catch (e) { toast(e.message, 'danger'); occupe(ok, false); }
    }, 'accent');
    modale('Nouvelle étiquette', h('div', { cls: 'es-form' },
      champ('Nom', nom), champ('Dossier', dossier), champ('Description', desc, 'Ce qui distingue cette étiquette des autres du dossier.'),
      h('div', { cls: 'es-champ' }, h('span', { cls: 'es-champ-label', text: 'Format' }), formats,
        h('div', { cls: 'es-ligne3' }, champ('Largeur (mm)', larg), champ('Hauteur (mm)', haut), champ('Résolution', dpi)))),
      [bouton('Annuler', fermerModale), ok]);
  }

  function modaleDupliquer(m) {
    const nom = h('input', { cls: 'es-input', value: m.nom + ' (copie)', maxlength: 120 });
    const dossier = selectDossiers(m.dossier_id);
    const ok = bouton('Dupliquer', async () => {
      occupe(ok, true);
      try {
        const r = await api('/modeles/' + m.id + '/dupliquer', { method: 'POST', body: { nom: nom.value, dossier_id: parseInt(dossier.value, 10) } });
        fermerModale(); toast('Étiquette dupliquée.'); await charger(); ouvrirEditeur(r.id);
      } catch (e) { toast(e.message, 'danger'); occupe(ok, false); }
    }, 'accent');
    modale('Dupliquer « ' + m.nom + ' »', h('div', { cls: 'es-form' }, champ('Nom de la copie', nom), champ('Dossier', dossier),
      h('p', { cls: 'es-aide', text: 'Les compteurs de la copie repartent de leur valeur de départ. Les SSCC restent partagés : un même préfixe GS1 ne réémet jamais un numéro.' })),
    [bouton('Annuler', fermerModale), ok]);
  }

  async function ouvrirEditeur(id) {
    try {
      const m = await api('/modeles/' + id);
      window.EtiqSpec.editeur.ouvrir(m);
      ES.view = 'editeur';
      rendre();
    } catch (e) { toast(e.message, 'danger'); }
  }

  // ── Impression en série ─────────────────────────────────────────────
  async function modaleImpression(m) {
    let modele, imps;
    try { [modele, imps] = await Promise.all([api('/modeles/' + m.id), imprimantes()]); }
    catch (e) { toast(e.message, 'danger'); return; }
    const vars = modele.layout.variables;
    // Toutes les imprimantes actives : ZPL pour les Zebra, PDF (planche A4,
    // étiquettes à taille réelle) pour les imprimantes de bureau.
    const estZpl = i => (i.langage || 'zpl') === 'zpl';
    const selImp = h('select', { cls: 'es-input' },
      h('option', { value: '', text: imps.length ? '— Choisir —' : 'Aucune imprimante active' }),
      ...imps.map(i => h('option', { value: i.id,
        text: i.nom + (i.poste ? ' · ' + i.poste : '') + (estZpl(i) ? '' : ' · PDF A4') })));
    try { const mem = localStorage.getItem(LS_IMPRIMANTE); if (mem && imps.some(i => String(i.id) === mem)) selImp.value = mem; } catch (e) {}
    const aideImp = h('span', { cls: 'es-champ-aide' });
    const majAideImp = () => {
      const i = imps.find(x => String(x.id) === selImp.value);
      aideImp.textContent = !i ? '' : estZpl(i)
        ? 'Étiquettes en ZPL, au format du rouleau.'
        : 'Imprimante de bureau : PDF, étiquettes à taille réelle posées en planche sur A4.';
    };
    selImp.addEventListener('change', majAideImp);
    majAideImp();
    const qte = h('input', { cls: 'es-input', type: 'number', min: 1, max: ES.boot.referentiel.quantite_max, value: 1 });
    const ex = h('input', { cls: 'es-input', type: 'number', min: 1, max: 99, value: 1 });
    const saisies = {}, departs = {};
    const blocs = [];
    for (const v of vars.filter(x => x.type === 'saisie')) {
      saisies[v.nom] = h('input', { cls: 'es-input', value: v.valeur || '', maxlength: 500 });
      blocs.push(champ(v.libelle + (v.obligatoire ? ' *' : ''), saisies[v.nom]));
    }
    for (const v of vars.filter(x => x.type === 'compteur' || x.type === 'sscc')) {
      departs[v.nom] = h('input', { cls: 'es-input', type: 'number', min: 0, placeholder: 'Suite automatique' });
      blocs.push(champ(`Départ — ${v.libelle}`, departs[v.nom],
        v.type === 'sscc' ? 'Laisser vide. Un numéro déjà émis est refusé.' : 'Laisser vide pour reprendre après la dernière impression.'));
    }
    const plage = h('div', { cls: 'es-plage' });
    const lire = () => ({
      quantite: parseInt(qte.value, 10) || 1,
      saisies: Object.fromEntries(Object.entries(saisies).map(([k, i]) => [k, i.value])),
      departs: Object.fromEntries(Object.entries(departs).filter(([, i]) => i.value !== '').map(([k, i]) => [k, i.value])),
    });
    let minuterie = null;
    const majPlage = () => {
      clearTimeout(minuterie);
      if (!Object.keys(departs).length) { plage.replaceChildren(); return; }
      minuterie = setTimeout(async () => {
        try {
          const r = await api('/modeles/' + m.id + '/plan', { method: 'POST', body: lire() });
          plage.replaceChildren(h('div', { cls: 'es-champ-label', text: 'Numéros qui vont sortir' }),
            ...Object.entries(r.plages).map(([nom, p]) => {
              const v = vars.find(x => x.nom === nom);
              return h('div', { cls: 'es-plage-ligne' }, h('span', { text: (v ? v.libelle : nom) + ' : ' }),
                h('code', { text: p.premier }), p.premier !== p.dernier ? h('span', { text: ' → ' }) : null,
                p.premier !== p.dernier ? h('code', { text: p.dernier }) : null);
            }));
          plage.classList.remove('es-erreur');
        } catch (e) { plage.replaceChildren(h('span', { text: e.message })); plage.classList.add('es-erreur'); }
      }, 250);
    };
    [qte, ...Object.values(departs)].forEach(i => i.addEventListener('input', majPlage));
    majPlage();

    const ok = bouton('Imprimer', async () => {
      if (!selImp.value) { toast('Choisir une imprimante.', 'danger'); return; }
      occupe(ok, true, 'Envoi…');
      try {
        const corps = Object.assign(lire(), { imprimante_id: parseInt(selImp.value, 10), exemplaires: parseInt(ex.value, 10) || 1 });
        const r = await api('/modeles/' + m.id + '/imprimer', { method: 'POST', body: corps });
        try { localStorage.setItem(LS_IMPRIMANTE, selImp.value); } catch (e) {}
        fermerModale();
        toast(`${r.quantite} étiquette${r.quantite > 1 ? 's' : ''} envoyée${r.quantite > 1 ? 's' : ''} à ${r.imprimante}.`);
      } catch (e) { toast(e.message, 'danger'); occupe(ok, false); majPlage(); }
    }, 'accent', 'printer');

    modale('Imprimer « ' + m.nom + ' »', h('div', { cls: 'es-form' },
      h('label', { cls: 'es-champ' }, h('span', { cls: 'es-champ-label', text: 'Imprimante' }), selImp, aideImp),
      h('div', { cls: 'es-ligne2' },
        champ('Quantité (série)', qte, 'Nombre d\'étiquettes différentes.'),
        champ('Exemplaires', ex, 'Copies identiques de chacune.')),
      ...blocs, plage), [bouton('Annuler', fermerModale), ok]);
  }

  async function modaleHistorique(m) {
    let rows;
    try { rows = await api('/modeles/' + m.id + '/impressions'); } catch (e) { toast(e.message, 'danger'); return; }
    const STATUT = { pending: 'En attente', picked: 'Envoyée', done: 'Imprimée', ok: 'Imprimée', error: 'Erreur' };
    const corps = rows.length ? h('table', { cls: 'es-table' },
      h('thead', {}, h('tr', {}, ...['Date', 'Par', 'Qté', 'Imprimante', 'Numéros', 'État', ''].map(t => h('th', { text: t })))),
      h('tbody', {}, ...rows.map(r => h('tr', {},
        h('td', { text: fmtDate(r.created_at) }),
        h('td', { text: (r.created_by || '').split('@')[0] }),
        h('td', { text: r.quantite + (r.exemplaires > 1 ? ' × ' + r.exemplaires : '') }),
        h('td', { text: r.imprimante || '—' }),
        h('td', {}, ...Object.values(r.plages).map(p => h('div', { cls: 'es-mono', text: p.premier === p.dernier ? p.premier : p.premier + ' → ' + p.dernier })),
          r.reimpression_de ? h('div', { cls: 'es-aide', text: 'Réimpression' }) : null),
        h('td', {}, h('span', { cls: 'es-etat es-etat-' + (r.job_status || 'pending'), title: r.job_erreur || '', text: STATUT[r.job_status] || r.job_status || '—' })),
        h('td', {}, bouton('Réimprimer', async (e) => {
          const b = e.currentTarget; occupe(b, true);
          try { const x = await api('/impressions/' + r.id + '/reimprimer', { method: 'POST', body: {} }); toast('Réimpression envoyée à ' + x.imprimante + '.'); fermerModale(); }
          catch (err) { toast(err.message, 'danger'); occupe(b, false); }
        })))))) : h('div', { cls: 'es-vide', text: 'Aucune impression pour cette étiquette.' });
    modale('Historique — ' + m.nom, h('div', {},
      h('p', { cls: 'es-aide', text: 'La réimpression renvoie exactement les mêmes étiquettes, avec les mêmes numéros. Aucun compteur n\'avance.' }),
      h('div', { cls: 'es-table-wrap' }, corps)), [bouton('Fermer', fermerModale)], true);
  }

  // ── Demandes de nouveau format ──────────────────────────────────────
  function modaleDemande() {
    const titre = h('input', { cls: 'es-input', maxlength: 150, placeholder: 'Ex. Étiquette carton avec SSCC sous le code produit' });
    const client = h('input', { cls: 'es-input', maxlength: 120 });
    const dossier = selectDossiers(ES.dossierId, true);
    const larg = h('input', { cls: 'es-input', type: 'number', step: '0.5', min: 10, placeholder: 'mm' });
    const haut = h('input', { cls: 'es-input', type: 'number', step: '0.5', min: 5, placeholder: 'mm' });
    const desc = h('textarea', { cls: 'es-input', rows: 6, maxlength: 5000,
      placeholder: 'Ce qui doit figurer sur l\'étiquette, les codes-barres attendus, ce qui change d\'une étiquette à l\'autre, la norme client à respecter…' });
    const fichiers = h('input', { cls: 'es-input', type: 'file', multiple: true,
      accept: '.pdf,.png,.jpg,.jpeg,.webp,.gif,.xlsx,.docx,.txt,.csv' });
    const ok = bouton('Envoyer la demande', async () => {
      const fd = new FormData();
      fd.append('titre', titre.value); fd.append('description', desc.value); fd.append('client', client.value);
      if (dossier.value) fd.append('dossier_id', dossier.value);
      if (larg.value) fd.append('largeur_mm', larg.value);
      if (haut.value) fd.append('hauteur_mm', haut.value);
      for (const f of fichiers.files) fd.append('fichiers', f);
      occupe(ok, true, 'Envoi…');
      try { await api('/demandes', { method: 'POST', form: fd }); fermerModale(); toast('Demande envoyée.'); await charger(); rendre(); }
      catch (e) { toast(e.message, 'danger'); occupe(ok, false); }
    }, 'accent');
    modale('Demander un nouveau format', h('div', { cls: 'es-form' },
      champ('Titre', titre),
      h('div', { cls: 'es-ligne2' }, champ('Client', client), champ('Dossier', dossier, 'Facultatif.')),
      h('div', { cls: 'es-ligne2' }, champ('Largeur', larg), champ('Hauteur', haut)),
      champ('Description', desc),
      champ('Pièces jointes', fichiers, 'Photo ou PDF d\'une étiquette existante, cahier des charges client. 15 Mo max par fichier.')),
    [bouton('Annuler', fermerModale), ok]);
  }

  async function chargerDemandes() {
    rendre();
    try { ES.demandes = await api('/demandes'); } catch (e) { toast(e.message, 'danger'); ES.demandes = []; }
    rendre();
  }

  function vueDemandes() {
    const b = ES.boot;
    const tete = h('div', { cls: 'es-tete' },
      h('div', { cls: 'es-titre' },
        h('button', { cls: 'es-btn', type: 'button', onclick: () => { ES.view = 'liste'; charger().then(rendre); } }, ic('arrow-left', 15), 'Étiquettes'),
        h('span', { text: b.is_super ? 'Demandes de nouveau format' : 'Mes demandes' })),
      h('div', { cls: 'es-actions' }, bouton('Demander un nouveau format', modaleDemande, 'accent', 'plus')));
    if (ES.demandes === null) return h('div', {}, tete, h('div', { cls: 'es-vide', text: 'Chargement…' }));
    const liste = h('div', { cls: 'es-demandes-liste' },
      ES.demandes.length ? null : h('div', { cls: 'es-vide', text: 'Aucune demande.' }),
      ...ES.demandes.map(d => h('div', { cls: 'es-demande' + (ES.demandeSel === d.id ? ' actif' : ''),
        onclick: () => { ES.demandeSel = d.id; rendre(); } },
        h('div', { cls: 'es-demande-haut' },
          h('span', { cls: 'es-demande-titre', text: d.titre }),
          h('span', { cls: 'es-statut es-statut-' + d.statut, text: d.statut_label })),
        h('div', { cls: 'es-aide', text: [d.client, fmtDate(d.created_at), (d.created_by || '').split('@')[0]].filter(Boolean).join(' · ') }))));
    const sel = ES.demandes.find(d => d.id === ES.demandeSel);
    return h('div', {}, tete, h('div', { cls: 'es-corps' }, liste,
      h('div', { cls: 'es-principal' }, sel ? detailDemande(sel) : h('div', { cls: 'es-vide', text: 'Choisir une demande.' }))));
  }

  function detailDemande(d) {
    const sup = ES.boot.is_super;
    const blocs = [
      h('div', { cls: 'es-demande-entete' },
        h('div', { cls: 'es-titre', text: d.titre }),
        h('span', { cls: 'es-statut es-statut-' + d.statut, text: d.statut_label })),
      h('div', { cls: 'es-aide', text: [
        d.client ? 'Client : ' + d.client : '', d.dossier_nom ? 'Dossier : ' + d.dossier_nom : '',
        d.largeur_mm ? `Format souhaité : ${fmtNum(d.largeur_mm)} × ${fmtNum(d.hauteur_mm)} mm` : '',
        'Demandé le ' + fmtDate(d.created_at) + ' par ' + (d.created_by || '')].filter(Boolean).join(' · ') }),
      h('div', { cls: 'es-bloc-texte', text: d.description }),
    ];
    if (d.pieces.length) blocs.push(h('div', { cls: 'es-pieces' }, ...d.pieces.map(p =>
      h('a', { cls: 'es-piece', href: API + '/pieces/' + p.id, target: '_blank', rel: 'noopener' }, ic('paperclip', 14), p.original_name))));
    if (d.modele_id) blocs.push(h('div', { cls: 'es-ligne-actions' },
      bouton('Ouvrir l\'étiquette', () => ouvrirEditeur(d.modele_id), 'accent', 'edit')));
    if (d.reponse && !sup) blocs.push(h('div', { cls: 'es-bloc-texte es-reponse', text: d.reponse }));
    if (sup) {
      const dossier = selectDossiers(d.dossier_id, true);
      const consigne = h('textarea', { cls: 'es-input', rows: 3, maxlength: 4000,
        placeholder: 'Facultatif : précision pour Claude (préfixe GS1 à utiliser, zone à ignorer sur la photo…)' });
      const modeleIa = selectModeleIa();
      const gen = bouton(d.modele_id ? 'Générer un nouveau brouillon avec Claude' : 'Générer le brouillon avec Claude', async () => {
        if (!dossier.value) { toast('Choisir le dossier où créer l\'étiquette.', 'danger'); return; }
        occupe(gen, true, 'Claude prépare l\'étiquette…');
        try {
          const r = await api('/demandes/' + d.id + '/generer', { method: 'POST', body: { dossier_id: parseInt(dossier.value, 10), consigne: consigne.value, modele: modeleIa.select.value } });
          toast(`Brouillon créé par ${r.modele_libelle} — à relire avant livraison.`);
          await charger(); ES.demandes = await api('/demandes');
          ouvrirEditeur(r.modele_id);
        } catch (e) { toast(e.message, 'danger'); occupe(gen, false); }
      }, 'accent', 'zap');
      const statut = h('select', { cls: 'es-input' }, ...Object.entries(ES.boot.referentiel.statuts_demande).map(([k, l]) => h('option', { value: k, text: l })));
      statut.value = d.statut;
      const reponse = h('textarea', { cls: 'es-input', rows: 3, maxlength: 3000, value: d.reponse || '', placeholder: 'Réponse visible par le demandeur' });
      const enr = bouton('Enregistrer', async () => {
        occupe(enr, true);
        try { await api('/demandes/' + d.id, { method: 'PATCH', body: { statut: statut.value, reponse: reponse.value } });
          toast('Demande mise à jour.'); ES.demandes = await api('/demandes'); await charger(); rendre(); }
        catch (e) { toast(e.message, 'danger'); occupe(enr, false); }
      });
      blocs.push(h('div', { cls: 'es-encart' },
        h('div', { cls: 'es-encart-titre', text: 'Paramétrer avec Claude' }),
        h('p', { cls: 'es-aide', text: 'Claude lit la description et les pièces jointes (images, PDF), crée l\'étiquette dans le dossier choisi et passe la demande en cours. Le brouillon s\'ouvre dans l\'éditeur.' }),
        champ('Dossier', dossier), modeleIa.bloc, champ('Consigne', consigne), h('div', { cls: 'es-ligne-actions' }, gen)));
      blocs.push(h('div', { cls: 'es-encart' },
        h('div', { cls: 'es-encart-titre', text: 'Suivi' }),
        champ('Statut', statut), champ('Réponse', reponse), h('div', { cls: 'es-ligne-actions' }, enr)));
    }
    return h('div', { cls: 'es-demande-detail' }, ...blocs);
  }

  // ── Montage ─────────────────────────────────────────────────────────
  async function mount(conteneur) {
    if (!conteneur) return;
    if (!ES.host) {
      ES.host = h('div', { cls: 'es-racine' });
      conteneur.appendChild(ES.host);
      rendre();
      try { await charger(); } catch (e) { toast(e.message, 'danger'); }
      rendre();
      return;
    }
    conteneur.appendChild(ES.host);
  }

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, {
    mount, _: { ES, h, ic, api, toast, champ, bouton, occupe, modale, fermerModale, confirmer,
      selectDossiers, selectModeleIa, fmtNum, fmtFormat, rendre, charger, modaleImpression, modaleHistorique, API },
  });
})();
