/* MyTools › Étiquettes spécifiques — données (EtiqSpec.donnees).
 *
 * - Champs variables liés aux données MySifa : choisir un dossier, un OF, un
 *   produit, un article, un client, une matière, un lot (ou un article RVGI)
 *   remplit toutes les variables « source » de l'étiquette
 *   (GET /sources/{type}/recherche, GET /sources/{type}/{id}).
 * - Formulaire de saisie opérateur : seuls les champs à saisir, listes de
 *   choix, contrôles (obligatoire, format, plage) — miroir de
 *   es.controle_saisie() côté serveur — et pesée sur balance (Web Serial,
 *   profils en base ; saisie manuelle si le navigateur ne le permet pas).
 * - Impression en série depuis un collage Excel, un CSV ou une liste MySifa :
 *   correspondance colonnes → variables, aperçu planche par planche.
 *
 * Les valeurs saisies s'affichent par textContent ou dans des champs, jamais
 * par innerHTML.
 */
(function () {
  'use strict';
  const X = () => window.EtiqSpec._;
  const E = () => window.EtiqSpec.editeur.api;
  const MO = () => window.EtiqMoteur;
  let balances = null;

  // ── Choix d'un enregistrement MySifa ────────────────────────────────
  function typesUtiles(lay) {
    const ref = X().ES.boot.referentiel.sources || {};
    const lies = new Set((lay.variables || []).filter(v => v.type === 'source' && v.champ).map(v => v.champ.split('.')[0]));
    // Un dossier remplit aussi OF, produit et client ; un lot sa matière et son dossier.
    const couvre = { dossier: ['dossier', 'of', 'produit', 'client'], of: ['of', 'produit'], lot: ['lot', 'matiere', 'dossier'], article: ['article', 'produit'] };
    return Object.keys(ref).filter(t => lies.has(t) || (couvre[t] || []).some(x => lies.has(x)));
  }
  function appliquerChamps(lay, champs, saisies) {
    let n = 0;
    for (const v of lay.variables) if (v.type === 'source' && v.champ && Object.prototype.hasOwnProperty.call(champs, v.champ)) { saisies[v.nom] = champs[v.champ]; n++; }
    return n;
  }
  async function lireSource(type, id) {
    const { api } = X();
    if (type === 'article_erp') {
      const r = await api('/articles/erp?q=' + encodeURIComponent(id) + '&limit=5');
      const it = (r.items || []).find(x => x.id === id);
      if (!it) throw new Error('Article RVGI introuvable dans le miroir.');
      return it.champs;
    }
    return (await api('/sources/' + type + '/' + encodeURIComponent(id))).champs;
  }
  /* Champ de recherche + liste ; onChoix(type, item, champs). */
  function selecteurSource(lay, onChoix, actuel) {
    const { h, api, toast } = X();
    const ref = X().ES.boot.referentiel.sources || {};
    const utiles = typesUtiles(lay);
    const types = utiles.length ? utiles : Object.keys(ref);
    let type = actuel && types.includes(actuel.type) ? actuel.type : types[0];
    const sel = h('select', { cls: 'es-input', 'aria-label': 'Type de donnée' }, ...types.map(t => h('option', { value: t, text: ref[t].libelle })));
    sel.value = type;
    const q = h('input', { cls: 'es-input', type: 'search', placeholder: 'Rechercher (référence, client, désignation…)', autocomplete: 'off', id: 'es-src-q' });
    const liste = h('div', { cls: 'es-src-liste', role: 'listbox' });
    let minut = null, items = [], actif = -1;
    const rendre = () => {
      liste.replaceChildren(...items.map((it, i) => h('div', { cls: 'es-src-item' + (i === actif ? ' actif' : ''), role: 'option',
        onclick: () => choisir(it) }, h('span', { cls: 'es-src-lib', text: it.libelle }), h('span', { cls: 'es-aide', text: it.detail || '' }))));
      if (!items.length) liste.appendChild(h('div', { cls: 'es-aide', text: q.value.trim() ? `Aucun résultat pour « ${q.value.trim()} »` : 'Taper pour chercher.' }));
    };
    const chercher = () => {
      clearTimeout(minut);
      minut = setTimeout(async () => {
        try {
          const r = type === 'article_erp' ? await api('/articles/erp?q=' + encodeURIComponent(q.value.trim())) : await api('/sources/' + type + '/recherche?q=' + encodeURIComponent(q.value.trim()));
          items = r.items || []; actif = items.length ? 0 : -1;
          if (type === 'article_erp' && r.miroir === false) items = [];
          rendre();
        } catch (e) { toast(e.message, 'danger'); }
      }, 180);
    };
    const choisir = async (it) => {
      try { const champs = it.champs || await lireSource(type, it.id); onChoix(type, it, champs); }
      catch (e) { toast(e.message, 'danger'); }
    };
    sel.addEventListener('change', () => { type = sel.value; chercher(); });
    q.addEventListener('input', chercher);
    q.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); actif = Math.min(items.length - 1, actif + 1); rendre(); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); actif = Math.max(0, actif - 1); rendre(); }
      else if (ev.key === 'Enter') { ev.preventDefault(); if (items[actif]) choisir(items[actif]); }
      else if (ev.key === 'Escape') { q.value = ''; chercher(); }
    });
    chercher();
    return h('div', { cls: 'es-form' }, h('div', { cls: 'es-ligne2' }, sel, q), liste);
  }

  // ── Onglet Données (conception) ─────────────────────────────────────
  function panneau() {
    const { h, bouton } = X();
    const ED = E().ED, lay = E().layout();
    const lies = lay.variables.filter(v => v.type === 'source');
    const etat = h('div', { cls: 'es-form' });
    const majEtat = () => etat.replaceChildren(...lies.map(v => h('div', { cls: 'es-src-val' },
      h('code', { text: '{{' + v.nom + '}}' }), h('span', { cls: 'es-aide', text: v.champ || 'non liée' }), h('span', { text: ED.saisies[v.nom] != null ? ED.saisies[v.nom] : (v.valeur || '—') }))));
    majEtat();
    return h('div', { cls: 'es-panneau' },
      h('div', { cls: 'es-panneau-titre', text: 'Données MySifa' }),
      lies.length ? null : h('div', { cls: 'es-aide', text: 'Aucune variable liée. Créer une variable de type « Donnée MySifa » et choisir le champ (dossier, client, lot…).' }),
      h('div', { cls: 'es-aide', text: ED.source ? 'Aperçu rempli avec : ' + ED.source.libelle : 'Choisir un enregistrement pour remplir l\'aperçu.' }),
      selecteurSource(lay, (type, it, champs) => {
        ED.source = { type, id: it.id, libelle: it.libelle };
        const n = appliquerChamps(lay, champs, ED.saisies);
        X().toast(n ? `${n} champ${n > 1 ? 's' : ''} rempli${n > 1 ? 's' : ''} depuis ${it.libelle}.` : 'Aucune variable de l\'étiquette ne lit ces données.', n ? 'success' : 'info');
        X().rendre();
      }, ED.source),
      lies.length ? h('div', { cls: 'es-panneau-titre', text: 'Valeurs liées' }) : null, etat,
      ED.source ? h('div', { cls: 'es-ligne-actions' }, bouton('Vider', () => { ED.source = null; ED.saisies = {}; X().rendre(); }, '', 'x')) : null);
  }

  // ── Formulaire de saisie opérateur ──────────────────────────────────
  // Miroir de etiq_specifiques.controle_saisie().
  function controleSaisie(v, val) {
    val = String(val || '').trim();
    const lib = v.libelle || v.nom;
    if (!val) return v.obligatoire ? `${lib} : obligatoire.` : '';
    const c = v.controle || {};
    if ((v.choix || []).length && !v.choix.includes(val)) return `${lib} : valeur hors de la liste.`;
    if (c.longueur_max && val.length > c.longueur_max) return `${lib} : ${c.longueur_max} caractères au plus.`;
    const t = c.type || 'texte';
    if (t === 'entier' || t === 'nombre') {
      const brut = val.replace(/ /g, '');
      if (!(t === 'entier' ? /^-?\d+$/ : /^-?\d+([.,]\d+)?$/).test(brut)) return `${lib} : ${t === 'entier' ? 'nombre entier' : 'nombre'} attendu.`;
      const n = parseFloat(brut.replace(',', '.'));
      if (c.min != null && n < c.min) return `${lib} : ${String(c.min).replace('.', ',')} au moins.`;
      if (c.max != null && n > c.max) return `${lib} : ${String(c.max).replace('.', ',')} au plus.`;
    } else if (t === 'date') {
      if (!MO().lireDate(val)) return `${lib} : date JJ/MM/AAAA attendue.`;
    } else if (t === 'sscc') {
      const d = val.replace(/\D/g, '');
      if (d.length !== 18) return `${lib} : SSCC de 18 chiffres attendu (${d.length} lus).`;
      const cle = MO().cleGs1(d.slice(0, 17));
      if (cle !== d[17]) return `${lib} : SSCC invalide — clé de contrôle ${cle} attendue.`;
    } else if (t === 'motif' && c.motif) {
      try { if (!new RegExp('^(?:' + c.motif + ')$').test(val)) return lib + ' : format attendu ' + c.motif + '.'; } catch (e) { return ''; }
    }
    return '';
  }
  function formulaire(lay, saisies, onChange) {
    const { h, champ } = X();
    const vars = lay.variables.filter(v => v.type === 'saisie' || v.type === 'source');
    const erreurs = {};
    const lignes = vars.map(v => {
      const err = h('span', { cls: 'es-champ-erreur' });
      const val = saisies[v.nom] != null ? saisies[v.nom] : (v.valeur || '');
      let input;
      if ((v.choix || []).length) {
        input = h('select', { cls: 'es-input' }, h('option', { value: '', text: '— Choisir —' }), ...v.choix.map(c => h('option', { value: c, text: c })));
        input.value = val;
      } else {
        const t = (v.controle || {}).type;
        input = h('input', { cls: 'es-input', value: val, maxlength: (v.controle || {}).longueur_max || 500,
          inputmode: t === 'entier' || t === 'nombre' ? 'decimal' : null, placeholder: t === 'date' ? 'JJ/MM/AAAA' : null });
      }
      const verif = () => { const m = controleSaisie(v, input.value); err.textContent = m; erreurs[v.nom] = m; input.classList.toggle('es-input-ko', !!m); };
      input.addEventListener(input.tagName === 'SELECT' ? 'change' : 'input', () => { saisies[v.nom] = input.value; verif(); if (onChange) onChange(v, input.value); });
      verif();
      const outils = [];
      if (v.pesee) outils.push(boutonPesee(v, (poids) => { input.value = poids; input.dispatchEvent(new Event('input')); }));
      const aide = v.type === 'source' ? 'Donnée MySifa : ' + (v.champ || '—') + ', modifiable.' : null;
      return champ(v.libelle + (v.obligatoire ? ' *' : ''), h('div', { cls: 'es-pile' }, h('div', { cls: 'es-ligne-champ' }, input, ...outils), err), aide);
    });
    return { el: h('div', { cls: 'es-form' }, ...(lignes.length ? lignes : [h('div', { cls: 'es-aide', text: 'Rien à saisir : l\'étiquette se remplit seule.' })])),
      valide: () => Object.values(erreurs).every(m => !m), erreurs: () => Object.values(erreurs).filter(Boolean) };
  }
  function panneauOperateur() {
    const { h, bouton } = X();
    const ED = E().ED, lay = E().layout();
    const f = formulaire(lay, ED.saisies, () => E().dessiner());
    const blocs = [];
    if (typesUtiles(lay).length) blocs.push(h('div', { cls: 'es-panneau' }, h('div', { cls: 'es-panneau-titre', text: 'Remplir depuis MySifa' }),
      ED.source ? h('div', { cls: 'es-aide', text: 'Rempli avec : ' + ED.source.libelle }) : null,
      selecteurSource(lay, (type, it, champs) => { ED.source = { type, id: it.id, libelle: it.libelle }; appliquerChamps(lay, champs, ED.saisies); X().rendre(); }, ED.source)));
    blocs.push(h('div', { cls: 'es-panneau' }, h('div', { cls: 'es-panneau-titre', text: 'À saisir' }), f.el,
      h('div', { cls: 'es-ligne-actions' },
        window.EtiqSpec.controle ? bouton('Contrôler', () => window.EtiqSpec.controle.modaleControle(), '', 'check') : null,
        bouton('Imprimer', () => { if (!f.valide()) { X().toast(f.erreurs()[0], 'danger'); return; } E().imprimer(); }, 'accent', 'printer'))));
    return h('div', { cls: 'es-pile' }, ...blocs);
  }

  // Réglages d'une variable « saisie » dans l'onglet Variables.
  function reglagesSaisie(v, ctx) {
    const { h, champ } = X();
    v.controle = v.controle || { type: 'texte' };
    const c = v.controle;
    const typ = h('select', { cls: 'es-input' }, ...Object.entries({ texte: 'Texte libre', entier: 'Nombre entier', nombre: 'Nombre', date: 'Date', motif: 'Format imposé', sscc: 'SSCC fourni par le client' }).map(([k, l]) => h('option', { value: k, text: l })));
    typ.value = c.type || 'texte';
    typ.addEventListener('change', () => { ctx.memoriser(); c.type = typ.value; ctx.salir(); X().rendre(); });
    const nb = (cle, label) => { const i = h('input', { cls: 'es-input', type: 'number', value: c[cle] ?? '' }); i.addEventListener('input', () => { c[cle] = i.value === '' ? null : parseFloat(i.value); ctx.salir(); }); return champ(label, i); };
    const blocs = [champ('Contrôle', typ)];
    if (c.type === 'entier' || c.type === 'nombre') blocs.push(h('div', { cls: 'es-ligne2' }, nb('min', 'Minimum'), nb('max', 'Maximum')));
    if (c.type === 'motif') {
      const m = h('input', { cls: 'es-input es-mono', value: c.motif || '', placeholder: '[A-Z]{2}\\d{4}' });
      m.addEventListener('input', () => { c.motif = m.value; ctx.salir(); });
      blocs.push(champ('Format (expression)', m, 'Ex. [A-Z]{2}\\d{4} : deux lettres puis quatre chiffres.'));
    }
    blocs.push(nb('longueur_max', 'Longueur max (0 = libre)'));
    const choix = h('textarea', { cls: 'es-input', rows: 2, value: (v.choix || []).join('\n'), placeholder: 'Une valeur par ligne' });
    choix.addEventListener('input', () => { v.choix = choix.value.split('\n').map(x => x.trim()).filter(Boolean).slice(0, 60); ctx.salir(); });
    blocs.push(champ('Liste de choix', choix, 'Vide = saisie libre.'));
    const pes = h('input', { type: 'checkbox', checked: !!v.pesee });
    pes.addEventListener('change', () => { ctx.memoriser(); v.pesee = pes.checked; ctx.salir(); X().rendre(); });
    blocs.push(h('label', { cls: 'es-case' }, pes, h('span', { text: 'Lire sur une balance' })));
    if (v.pesee) {
      const sel = h('select', { cls: 'es-input' }, h('option', { value: '', text: 'Balance du poste (choisie à la pesée)' }));
      chargerBalances().then(bs => { bs.forEach(b => sel.appendChild(h('option', { value: b.id, text: b.nom }))); sel.value = v.balance_id || ''; });
      sel.addEventListener('change', () => { v.balance_id = sel.value ? parseInt(sel.value, 10) : null; ctx.salir(); });
      blocs.push(champ('Profil de balance', sel), h('div', { cls: 'es-ligne-actions' }, X().bouton('Balances', () => modaleBalances(), '', 'settings')));
    }
    return h('div', { cls: 'es-form' }, ...blocs);
  }

  // ── Pesée (Web Serial) ──────────────────────────────────────────────
  async function chargerBalances() {
    if (balances) return balances;
    try { balances = (await X().api('/balances')).balances.filter(b => b.actif); } catch (e) { balances = []; }
    return balances;
  }
  const deseq = (t) => String(t || '').replace(/\\r/g, '\r').replace(/\\n/g, '\n').replace(/\\t/g, '\t');
  async function lireBalance(profil) {
    if (!('serial' in navigator)) throw new Error('Ce navigateur ne lit pas les balances (Web Serial : Chrome ou Edge). Saisir le poids à la main.');
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate: profil.vitesse || 9600, dataBits: profil.bits || 8, parity: profil.parite || 'none', stopBits: profil.stop || 1 });
    const enc = new TextEncoder(), dec = new TextDecoder();
    let tampon = '';
    try {
      if (profil.commande) { const w = port.writable.getWriter(); await w.write(enc.encode(deseq(profil.commande))); w.releaseLock(); }
      const lecteur = port.readable.getReader();
      const fin = Date.now() + 4000;
      const motif = new RegExp(profil.motif || '([-+]?\\d+[.,]?\\d*)', 'i');
      try {
        while (Date.now() < fin) {
          const r = await Promise.race([lecteur.read(), new Promise(ok => setTimeout(() => ok({ value: null, done: false, attente: true }), 800))]);
          if (r.done) break;
          if (r.value) tampon += dec.decode(r.value);
          const lignes = tampon.split(/\r?\n/);
          for (const l of lignes.slice(0, -1).reverse()) {
            if (profil.stable_seulement && /\b(US|MOT|M)\b/.test(l) && !/\bST\b/.test(l)) continue;   // poids instable
            const m = motif.exec(l);
            if (m) return parseFloat(m[1].replace(',', '.')).toFixed(profil.decimales ?? 2).replace('.', ',');
          }
        }
      } finally { try { await lecteur.cancel(); lecteur.releaseLock(); } catch (e) { /* déjà libéré */ } }
    } finally { try { await port.close(); } catch (e) { /* déjà fermé */ } }
    throw new Error('Aucun poids stable lu sur la balance. Vérifier le profil, ou saisir le poids.');
  }
  function boutonPesee(v, poser) {
    const { h, toast } = X();
    const b = h('button', { cls: 'es-btn', type: 'button', 'data-bulle': 'Peser', 'aria-label': 'Lire le poids sur la balance' }, X().ic('activity', 14), 'Peser');
    b.addEventListener('click', async () => {
      const bs = await chargerBalances();
      const profil = bs.find(x => x.id === v.balance_id) || bs[0];
      if (!profil) { toast('Aucun profil de balance — en créer un dans les réglages de pesée.', 'info'); return; }
      b.disabled = true;
      try { const p = await lireBalance(profil); poser(p); toast('Poids lu : ' + p + ' ' + (profil.unite || 'kg') + '.'); }
      catch (e) { if (e.name !== 'NotFoundError') toast(e.message, 'danger'); }
      b.disabled = false;
    });
    if (!('serial' in navigator)) { b.disabled = true; b.title = 'Lecture de balance impossible dans ce navigateur : saisir le poids.'; }
    return b;
  }
  async function modaleBalances() {
    const { h, champ, bouton, modale, fermerModale, api, toast, ES } = X();
    balances = null;
    let liste;
    try { liste = (await api('/balances')).balances; } catch (e) { toast(e.message, 'danger'); return; }
    const conc = ES.boot.referentiel.concepteur;
    const ligne = (b) => {
      const d = Object.assign({}, b);
      const ch = (cle, label, attrs) => { const i = h('input', Object.assign({ cls: 'es-input', value: d[cle] ?? '', disabled: conc ? null : true }, attrs || {})); i.addEventListener('input', () => { d[cle] = attrs && attrs.type === 'number' ? parseInt(i.value, 10) : i.value; }); return champ(label, i); };
      const par = h('select', { cls: 'es-input', disabled: conc ? null : true }, ...['none', 'even', 'odd'].map(x => h('option', { value: x, text: { none: 'Aucune', even: 'Paire', odd: 'Impaire' }[x] })));
      par.value = d.parite; par.addEventListener('change', () => { d.parite = par.value; });
      const ok = bouton('Enregistrer', async () => {
        try { await api(b.id ? '/balances/' + b.id : '/balances', { method: b.id ? 'PATCH' : 'POST', body: d }); toast('Balance enregistrée.'); modaleBalances(); }
        catch (e) { toast(e.message, 'danger'); }
      }, 'accent', 'save');
      return h('details', { cls: 'es-var', open: b.id ? null : true }, h('summary', {}, h('span', { text: b.nom || 'Nouvelle balance' }), h('span', { cls: 'es-aide', text: (b.vitesse || 9600) + ' bauds' })),
        h('div', { cls: 'es-form' }, ch('nom', 'Nom'), h('div', { cls: 'es-ligne3' }, ch('vitesse', 'Vitesse', { type: 'number' }), ch('bits', 'Bits', { type: 'number' }), champ('Parité', par)),
          h('div', { cls: 'es-ligne2' }, ch('commande', 'Commande', { cls: 'es-input es-mono', placeholder: 'P\\r\\n — vide si continue' }), ch('unite', 'Unité')),
          ch('motif', 'Lecture du poids (expression)', { cls: 'es-input es-mono' }), conc ? h('div', { cls: 'es-ligne-actions' }, ok) : null));
    };
    X().ES.adresseModale = { cle: 'balances', id: 'liste' };
    modale('Balances — pesée à l\'impression', h('div', { cls: 'es-form' },
      h('p', { cls: 'es-aide', text: 'La balance se branche sur le poste (port série ou USB). Le navigateur demande l\'autorisation à la première pesée.' }),
      ...liste.map(ligne), conc ? ligne({ nom: '', vitesse: 9600, bits: 8, parite: 'none', stop: 1, commande: '', motif: '([-+]?\\d+[.,]?\\d*)\\s*kg', unite: 'kg', decimales: 2 }) : null),
    [bouton('Fermer', fermerModale)]);
  }

  // ── Impression en série ─────────────────────────────────────────────
  async function modaleSerie(m) {
    const { h, champ, bouton, modale, fermerModale, api, toast, ES } = X();
    let modele;
    try { modele = await api('/modeles/' + m.id + '/production'); }
    catch (e) { toast(e.message, 'danger'); return; }
    const lay = E() && E().completerLayout ? E().completerLayout(modele.layout) : modele.layout;
    const vars = lay.variables.filter(v => ['saisie', 'source', 'fixe'].includes(v.type));
    const S = { tableau: { entetes: [], lignes: [] }, corr: {}, page: 0, quantite: 1, mode: 'coller' };
    const zoneDonnees = h('div', { cls: 'es-form' });
    const zoneCorr = h('div', { cls: 'es-form' });
    const zoneApercu = h('div', { cls: 'es-serie-apercu' });
    const resume = h('div', { cls: 'es-aide' });
    const enregs = () => MO().enregistrementsDepuis(S.tableau, S.corr);
    const parPlanche = () => { const pl = lay.planche || {}; return pl.type === 'a4' ? Math.max(1, (pl.poses || 3) * (pl.rangees || 4)) : Math.max(1, pl.poses || 1); };
    const rendreApercu = () => {
      const tous = enregs();
      const n = tous.length * S.quantite, pp = parPlanche(), pages = Math.max(1, Math.ceil(n / pp));
      S.page = Math.min(S.page, pages - 1);
      resume.textContent = tous.length ? `${tous.length} enregistrement${tous.length > 1 ? 's' : ''} × ${S.quantite} = ${n} étiquette${n > 1 ? 's' : ''} · planche ${S.page + 1} / ${pages}` : 'Aucun enregistrement.';
      const grille = h('div', { cls: 'es-serie-planche', style: { gridTemplateColumns: `repeat(${Math.min(pp, (lay.planche || {}).type === 'a4' ? (lay.planche.poses || 3) : pp)}, 1fr)` } });
      for (let i = S.page * pp; i < Math.min(n, (S.page + 1) * pp); i++) {
        const sa = Object.assign({}, tous[Math.floor(i / S.quantite)]);
        const vals = MO().valeurs(lay, { saisies: sa, index: i, systeme: { fsc_licence: ES.boot.referentiel.fsc_licence, gs1_prefixe: (ES.boot.referentiel.gs1 || {}).prefixe } });
        const svg = E().construireSvg(modele, lay, false, vals);
        const err = lay.variables.filter(v => v.type === 'saisie').map(v => controleSaisie(v, sa[v.nom] ?? v.valeur)).find(Boolean);
        grille.appendChild(h('div', { cls: 'es-serie-cellule' + (err ? ' es-serie-ko' : ''), title: err || '' }, svg, err ? h('div', { cls: 'es-champ-erreur', text: err }) : null));
      }
      zoneApercu.replaceChildren(h('div', { cls: 'es-ligne-actions es-serie-nav' },
        bouton('Précédente', () => { S.page = Math.max(0, S.page - 1); rendreApercu(); }, '', 'arrow-left'), resume,
        bouton('Suivante', () => { S.page += 1; rendreApercu(); }, '', 'arrow-right')), grille);
    };
    const rendreCorr = () => {
      zoneCorr.replaceChildren(...(vars.length ? vars.map(v => {
        const sel = h('select', { cls: 'es-input' }, h('option', { value: '', text: '— Valeur par défaut —' }), ...S.tableau.entetes.map((e, i) => h('option', { value: i, text: e })));
        sel.value = S.corr[v.nom] != null ? String(S.corr[v.nom]) : '';
        sel.addEventListener('change', () => { if (sel.value === '') delete S.corr[v.nom]; else S.corr[v.nom] = parseInt(sel.value, 10); rendreApercu(); });
        return h('div', { cls: 'es-ligne2' }, h('span', {}, h('code', { text: '{{' + v.nom + '}}' }), ' ', v.libelle), sel);
      }) : [h('div', { cls: 'es-aide', text: 'Aucune variable à remplir : chaque ligne donne une étiquette identique (compteurs et dates mis à part).' })]));
    };
    const charger = (tab) => { S.tableau = tab; S.corr = MO().correspondanceAuto(tab.entetes, lay.variables); S.page = 0; rendreCorr(); rendreApercu(); };
    // Onglet coller / CSV
    const zoneColler = () => {
      const t = h('textarea', { cls: 'es-input es-mono', rows: 6, placeholder: 'Coller ici des cellules Excel (avec la ligne d\'en-têtes), ou un CSV.' });
      t.addEventListener('input', () => charger(MO().lireTableau(t.value)));
      const f = h('input', { type: 'file', accept: '.csv,.txt,text/csv', hidden: true, onchange: async () => { const fi = f.files[0]; if (fi) { const txt = await fi.text(); t.value = txt; charger(MO().lireTableau(txt)); } } });
      return h('div', { cls: 'es-form' }, t, h('div', { cls: 'es-ligne-actions' }, bouton('Fichier CSV', () => f.click(), '', 'paperclip')), f);
    };
    // Onglet liste MySifa
    const zoneListe = () => {
      const choisis = new Map();
      const ref = ES.boot.referentiel.sources || {};
      const types = Object.keys(ref).filter(t => !ref[t].erp);
      const sel = h('select', { cls: 'es-input' }, ...types.map(t => h('option', { value: t, text: ref[t].libelle })));
      sel.value = typesUtiles(lay)[0] && types.includes(typesUtiles(lay)[0]) ? typesUtiles(lay)[0] : types[0];
      const q = h('input', { cls: 'es-input', type: 'search', placeholder: 'Rechercher… (lots : n° de dossier)' });
      const liste = h('div', { cls: 'es-src-liste' });
      let minut;
      const charge = async () => {
        try {
          const r = await api('/sources/' + sel.value + '/recherche?limit=100&q=' + encodeURIComponent(q.value.trim()) + (sel.value === 'lot' && /^\d/.test(q.value.trim()) ? '&dossier=' + encodeURIComponent(q.value.trim()) : ''));
          liste.replaceChildren(...r.items.map(it => {
            const c = h('input', { type: 'checkbox', checked: choisis.has(it.id) });
            c.addEventListener('change', () => { c.checked ? choisis.set(it.id, it) : choisis.delete(it.id); });
            return h('label', { cls: 'es-src-item' }, c, h('span', { cls: 'es-src-lib', text: it.libelle }), h('span', { cls: 'es-aide', text: it.detail || '' }));
          }));
        } catch (e) { toast(e.message, 'danger'); }
      };
      sel.addEventListener('change', () => { choisis.clear(); charge(); });
      q.addEventListener('input', () => { clearTimeout(minut); minut = setTimeout(charge, 200); });
      charge();
      const ok = bouton('Prendre la sélection', async () => {
        if (!choisis.size) { toast('Cocher au moins une ligne.', 'info'); return; }
        try {
          const r = await api('/sources/' + sel.value + '/lire', { method: 'POST', body: { ids: [...choisis.keys()] } });
          const cles = [...new Set(r.items.flatMap(x => Object.keys(x.champs)))];
          // Les colonnes portent la clé du champ : la correspondance se fait par le champ lié.
          const tab = { entetes: cles, lignes: r.items.map(x => cles.map(k => x.champs[k] || '')) };
          S.tableau = tab;
          S.corr = {};
          for (const v of lay.variables) if (v.type === 'source' && cles.includes(v.champ)) S.corr[v.nom] = cles.indexOf(v.champ);
          Object.assign(S.corr, MO().correspondanceAuto(cles, lay.variables.filter(v => S.corr[v.nom] == null)));
          S.page = 0; rendreCorr(); rendreApercu();
        } catch (e) { toast(e.message, 'danger'); }
      }, 'accent', 'check');
      return h('div', { cls: 'es-form' }, h('div', { cls: 'es-ligne2' }, sel, q), liste, h('div', { cls: 'es-ligne-actions' }, ok));
    };
    const onglets = h('div', { cls: 'es-bascule' });
    const majOnglets = () => {
      onglets.replaceChildren(
        h('button', { cls: 'es-puce' + (S.mode === 'coller' ? ' actif' : ''), type: 'button', text: 'Collage / CSV', onclick: () => { S.mode = 'coller'; majOnglets(); } }),
        h('button', { cls: 'es-puce' + (S.mode === 'liste' ? ' actif' : ''), type: 'button', text: 'Liste MySifa', onclick: () => { S.mode = 'liste'; majOnglets(); } }));
      zoneDonnees.replaceChildren(S.mode === 'coller' ? zoneColler() : zoneListe());
    };
    majOnglets();
    const qte = h('input', { cls: 'es-input es-court', type: 'number', min: 1, max: 999, value: 1 });
    qte.addEventListener('input', () => { S.quantite = Math.max(1, parseInt(qte.value, 10) || 1); rendreApercu(); });
    const go = bouton('Imprimer la série', async () => {
      const enr = enregs();
      if (!enr.length) { toast('Aucun enregistrement à imprimer.', 'danger'); return; }
      for (let i = 0; i < enr.length; i++) {
        for (const v of lay.variables.filter(x => x.type === 'saisie')) {
          const msg = controleSaisie(v, enr[i][v.nom] ?? v.valeur);
          if (msg) { toast(`Ligne ${i + 1} : ${msg}`, 'danger'); return; }
        }
      }
      const imp = window.MySifaEtiqImpression;
      if (imp && typeof imp.imprimer === 'function') {
        try { await imp.imprimer({ modele, enregistrements: enr, quantite: S.quantite }); fermerModale(); } catch (e) { toast(e.message, 'danger'); }
        return;
      }
      await imprimerIntegre(m, enr, S.quantite);
    }, 'accent', 'printer');
    ES.adresseModale = { cle: 'serie', id: m.id };
    modale('Impression en série — ' + m.nom + ' (version ' + modele.version + ')', h('div', { cls: 'es-serie' },
      h('div', { cls: 'es-serie-gauche' }, onglets, zoneDonnees,
        h('div', { cls: 'es-panneau-titre', text: 'Colonnes → variables' }), zoneCorr,
        champ('Étiquettes par enregistrement', qte)),
      h('div', { cls: 'es-serie-droite' }, zoneApercu)), [bouton('Annuler', fermerModale), go], true);
    rendreCorr(); rendreApercu();
    // Codes-barres : bwip-js se charge à la demande, l'aperçu se redessine à son arrivée.
    document.addEventListener('etiq-bwip-pret', () => { if (document.getElementById('es-modale')) rendreApercu(); }, { once: true });
    E().chargerBwip();
  }

  // Chemin intégré : choix de l'imprimante puis /imprimer-serie (ZPL ou PDF A4).
  async function imprimerIntegre(m, enr, quantite) {
    const { h, champ, bouton, api, toast, imprimantes } = X();
    let imps;
    try { imps = await imprimantes(); } catch (e) { toast(e.message, 'danger'); return; }
    const sel = h('select', { cls: 'es-input' }, h('option', { value: '', text: imps.length ? '— Choisir —' : 'Aucune imprimante active' }),
      ...imps.map(i => h('option', { value: i.id, text: i.nom + (i.poste ? ' · ' + i.poste : '') + ((i.langage || 'zpl') === 'zpl' ? '' : ' · PDF A4') })));
    try { const mem = localStorage.getItem('mysifa_etiq_spec_imprimante'); if (mem) sel.value = mem; } catch (e) { /* rien */ }
    const ok = bouton('Envoyer', async () => {
      if (!sel.value) { toast('Choisir une imprimante.', 'danger'); return; }
      ok.disabled = true;
      try {
        const r = await api('/modeles/' + m.id + '/imprimer-serie', { method: 'POST', body: { imprimante_id: parseInt(sel.value, 10), enregistrements: enr, quantite } });
        try { localStorage.setItem('mysifa_etiq_spec_imprimante', sel.value); } catch (e) { /* rien */ }
        X().fermerModale();
        toast(`${r.quantite} étiquette${r.quantite > 1 ? 's' : ''} envoyée${r.quantite > 1 ? 's' : ''} à ${r.imprimante}.`);
      } catch (e) { toast(e.message, 'danger'); ok.disabled = false; }
    }, 'accent', 'printer');
    X().ES.adresseModale = { cle: 'serie', id: m.id };
    X().modale('Imprimante — ' + m.nom, h('div', { cls: 'es-form' }, champ('Imprimante', sel),
      h('p', { cls: 'es-aide', text: `${enr.length * quantite} étiquette(s). Les compteurs et SSCC sont réservés à l'envoi.` })), [bouton('Annuler', () => modaleSerie(m)), ok]);
  }

  // Pour le kiosque (static/mysifa_etiq_kiosque.js) : le formulaire de saisie
  // opérateur d'un modèle, valeurs initiales comprises (données d'un dossier).
  function formulaireOperateur(modele, valeurs) {
    const lay = (modele && modele.layout) || modele || { variables: [] };
    lay.variables = lay.variables || [];
    const saisies = Object.assign({}, valeurs || {});
    const f = formulaire(lay, saisies);
    return { el: f.el, valeurs: () => Object.assign({}, saisies), valide: f.valide, erreurs: f.erreurs };
  }

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, {
    formulaireOperateur,
    donnees: { panneau, panneauOperateur, formulaire, reglagesSaisie, controleSaisie, modaleSerie, modaleBalances, lireBalance,
      selecteurSource, appliquerChamps, lireSource },
  });
})();
