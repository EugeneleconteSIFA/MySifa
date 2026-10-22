/* MyTools › Étiquettes — atelier : kiosque, parc d'imprimantes, impression
 * automatique. Complète static/mysifa_etiq_impression.js (chargé avant).
 *
 *   MySifaEtiqImpression.ouvrirParc()      état de chaque imprimante (~HS, ~HQES, ~HQOD), compteurs
 *   MySifaEtiqImpression.ouvrirRegles(id?) règles d'impression automatique par machine (admin)
 *   MySifaEtiqImpression.kiosque.ouvrir()  écran atelier plein écran
 *
 * Kiosque : /tools?outil=etiquettes&mode=kiosque. Gros boutons, un champ de
 * scan qui accepte un n° de modèle (M12 ou 12), son nom, ou une référence
 * dossier (les champs liés au dossier se remplissent). Seuls les modèles
 * APPROUVÉS sont proposés, et c'est leur version approuvée qui s'imprime.
 * Le formulaire opérateur est celui de l'éditeur s'il l'expose
 * (EtiqSpec.formulaireOperateur(modele, valeurs) → {el, valeurs()}), sinon un
 * formulaire simple tiré des variables « saisie » et « source » du modèle.
 *
 * Adresse : mode=kiosque, kiosque_modele=<id>, kiosque_dossier=<réf> ;
 * fenêtres parc_impression=1 et regles_impression=liste|nouvelle|<id>.
 * API : app/routers/etiq_atelier.py (/api/tools/etiquettes/atelier).
 */
(function () {
  'use strict';
  const M = window.MySifaEtiqImpression;
  if (!M || M.kiosque) return;
  const X = M._;
  const { h, ic, bouton, fenetre, champ, toast } = X;
  const API = '/api/tools/etiquettes/atelier';
  const K = { actif: false, el: null, modeles: null, modele: null, dossier: null, champsDossier: {}, fen: null };

  // replaceChildren insère « null » en texte : on filtre les absents.
  function remplacer(el, ...k) { el.replaceChildren(...k.flat().filter(c => c !== null && c !== undefined && c !== false)); }
  async function api(chemin, opts) {
    opts = opts || {};
    const init = { method: opts.method || 'GET', credentials: 'include', cache: 'no-store', headers: {} };
    if (opts.body !== undefined) { init.body = JSON.stringify(opts.body); init.headers['Content-Type'] = 'application/json'; }
    const r = await fetch(API + chemin, init);
    if (r.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); throw new Error('Session expirée.'); }
    let j = null;
    try { j = await r.json(); } catch (e) {}
    if (!r.ok) throw new Error(j && typeof j.detail === 'string' ? j.detail : 'Erreur ' + r.status + '.');
    return j;
  }
  function fmtDate(s) { if (!s) return '—'; const [d, t] = String(s).split('T'); const [a, m, j] = d.split('-'); return j + '/' + m + ' ' + (t || '').slice(0, 5); }

  // ── Fenêtres adressables propres à ce fichier ───────────────────────
  function ouvrirFen(cle, valeur, construire) {
    fermerFen(true);
    if (X.I.fen) X.fermerAdressable(true);
    K.fen = { cle, valeur: String(valeur), el: construire() };
    X.signaler();
  }
  function fermerFen(sansAdresse) {
    if (!K.fen) return;
    const f = K.fen; K.fen = null;
    if (f.el && f.el.isConnected) f.el.remove();
    if (!sansAdresse) X.signaler();
  }

  // ── Parc ────────────────────────────────────────────────────────────
  function ouvrirParc() {
    ouvrirFen('parc_impression', '1', () => {
      const corps = h('div', { cls: 'eqi-corps' });
      const maj = bouton('Interroger', 'Actualiser', () => charger(1), null, 'activity');
      const ov = fenetre('Parc d\'imprimantes', corps, { large: true, fermer: () => fermerFen(), actions: maj });
      async function charger(rafraichir) {
        maj.disabled = true;
        remplacer(corps, h('div', { cls: 'eqi-aide', text: rafraichir ? 'Interrogation des imprimantes réseau…' : 'Chargement…' }));
        try {
          await X.charger().catch(() => {});
          const d = await api('/parc' + (rafraichir ? '?rafraichir=1' : ''));
          remplacer(corps, d.imprimantes.length
            ? h('div', { cls: 'eqi-parc' }, ...d.imprimantes.map(carteParc))
            : h('div', { cls: 'eqi-vide', text: 'Aucune imprimante active.' }),
            h('div', { cls: 'eqi-aide', text: 'Interrogation directe (ZPL, port ' + (d.ports_reseau || []).join(', ') + ') : ~HS, ~HQES, ~HQOD. Compteurs : étiquettes envoyées depuis MyTools.' }));
        } catch (e) { remplacer(corps, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); }
        maj.disabled = false;
      }
      charger(1);
      return ov;
    });
  }
  function carteParc(p) {
    const e = p.etat || {};
    let ton = '', etat;
    if (!p.interrogeable) etat = h('span', { cls: 'eqi-badge eqi-badge--neutre', text: p.modes.includes('agent') ? 'Via agent' : 'Non interrogeable' });
    else if (!p.vu_le) etat = h('span', { cls: 'eqi-badge eqi-badge--neutre', text: 'Jamais interrogée' });
    else if (!e.en_ligne) { ton = 'danger'; etat = h('span', { cls: 'eqi-badge eqi-badge--danger', text: 'Hors ligne' }); }
    else {
      const pb = [e.papier_epuise && 'Papier', e.ruban_epuise && 'Ruban', e.tete_ouverte && 'Tête ouverte', e.en_pause && 'Pause'].filter(Boolean)
        .concat(e.erreurs || []);
      ton = pb.length ? 'danger' : ((e.alertes || []).length ? 'warn' : 'ok');
      etat = h('span', { cls: 'eqi-badge eqi-badge--' + (pb.length ? 'danger' : 'ok'), text: pb.length ? pb.join(' · ') : 'En ligne' });
    }
    const alertes = (e.alertes || []).map(a => h('span', { cls: 'eqi-badge eqi-badge--' + (/usée/.test(a) ? 'danger' : 'warn'), text: a }));
    return h('div', { cls: 'eqi-parc-carte' + (ton ? ' eqi-parc-carte--' + ton : '') },
      h('div', { cls: 'eqi-ligne' }, h('span', { cls: 'eqi-parc-nom', text: p.nom }), etat),
      h('div', { cls: 'eqi-aide', text: [p.poste, String(p.langage).toUpperCase() + ' ' + p.dpi + ' dpi', p.ip ? p.ip + ':' + p.port : '', p.rfid ? 'RFID' : ''].filter(Boolean).join(' · ') }),
      alertes.length ? h('div', { cls: 'eqi-ligne' }, alertes) : null,
      h('div', { cls: 'eqi-parc-chiffres' },
        h('span', { text: p.etiquettes_30j + ' étiq. / 30 j' }),
        h('span', { text: p.etiquettes_total + ' au total' }),
        p.erreurs_30j ? h('span', { text: p.erreurs_30j + ' échec(s) / 30 j' }) : null,
        e.compteurs && e.compteurs.total ? h('span', { text: 'Odomètre ' + e.compteurs.total + ' ' + (e.compteurs.unite || '') }) : null),
      h('div', { cls: 'eqi-aide', text: 'Dernière impression ' + fmtDate(p.derniere_impression) + (p.vu_le ? ' · relevé ' + fmtDate(p.vu_le) : '') }),
      h('div', { cls: 'eqi-ligne' },
        bouton('Journal', 'Journal', () => { fermerFen(true); M.ouvrirJournal({ imprimante: String(p.id), detail: null }); }, null, 'list'),
        X.I.admin ? bouton('Profil', 'Profil', () => { fermerFen(true); M.ouvrirProfils(p.id); }, null, 'settings') : null));
  }

  // ── Règles d'impression automatique ─────────────────────────────────
  function ouvrirRegles(id) {
    ouvrirFen('regles_impression', id || 'liste', () => {
      const corps = h('div', { cls: 'eqi-corps' });
      const ov = fenetre('Impression automatique', corps, { large: true, fermer: () => fermerFen() });
      construireRegles(corps, id || 'liste');
      return ov;
    });
  }
  async function construireRegles(corps, id) {
    let d;
    try { d = await api('/regles'); } catch (e) { remplacer(corps, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); return; }
    const op = c => (d.operations.find(o => o.code === c) || { libelle: c }).libelle;
    const aller = v => { if (K.fen) K.fen.valeur = String(v); X.signaler(); construireRegles(corps, v); };
    const liste = h('div', { cls: 'eqi-profils-liste' },
      d.peut_administrer ? bouton('Nouvelle règle', 'Créer', () => aller('nouvelle'), 'accent', 'plus') : null,
      ...(d.regles.length ? d.regles.map(r => h('button', { type: 'button', 'data-bulle': 'Modifier',
        cls: 'eqi-choix-item' + (String(id) === String(r.id) ? ' eqi-choix-item--actif' : '') + (r.actif ? '' : ' eqi-inactif'),
        onclick: () => aller(r.id) }, ic('printer', 16), h('span', { cls: 'eqi-choix-nom', text: (r.machine_nom || '?') + ' · ' + op(r.operation_code) }),
        h('span', { cls: 'eqi-aide', text: (r.modele_nom || '?') + ' → ' + (r.imprimante_nom || '?') + ' · ×' + r.exemplaires + (r.actif ? '' : ' · inactive') })))
        : [h('div', { cls: 'eqi-vide', text: 'Aucune règle. Une saisie de production n\'imprime rien toute seule.' })]));
    remplacer(corps, h('div', { cls: 'eqi-profils' }, liste, h('div', { cls: 'eqi-profils-form' }, formRegle(d, id, aller))),
      h('div', { cls: 'eqi-aide', text: 'Saisie du code choisi sur la machine (Saisie Prod) → impression de la version approuvée du modèle sur l\'imprimante, sans attendre : la saisie n\'est jamais bloquée. Un échec apparaît au journal et dans les notifications MyProd.' }));
  }
  function formRegle(d, id, aller) {
    if (id === 'liste') return h('div', { cls: 'eqi-vide', text: 'Choisir une règle, ou en créer une.' });
    const r = id === 'nouvelle' ? { operation_code: '89', exemplaires: 1, actif: 1, fin_dossier_seulement: 0 } : d.regles.find(x => String(x.id) === String(id));
    if (!r) return h('div', { cls: 'eqi-vide', text: 'Règle introuvable.' });
    const ro = !d.peut_administrer;
    const sel = (opts, val) => { const s = h('select', { cls: 'eqi-in', disabled: ro }, h('option', { value: '', text: '—' }), ...opts.map(([v, l]) => h('option', { value: v, text: l }))); s.value = val == null ? '' : String(val); return s; };
    const mac = sel(d.machines.map(m => [m.id, m.nom]), r.machine_id);
    const cod = sel(d.operations.map(o => [o.code, o.code + ' · ' + o.libelle]), r.operation_code);
    const mod = sel(d.modeles.map(m => [m.id, m.nom + (m.approuve ? '' : ' (non approuvé)')]), r.modele_id);
    const imp = sel(d.imprimantes.filter(p => p.modes.includes('reseau') || p.modes.includes('agent')).map(p => [p.id, p.nom]), r.imprimante_id);
    const ex = h('input', { cls: 'eqi-in', type: 'number', min: 1, max: 99, value: r.exemplaires || 1, disabled: ro });
    const fin = h('input', { type: 'checkbox', checked: !!r.fin_dossier_seulement, disabled: ro });
    const act = h('input', { type: 'checkbox', checked: !!r.actif, disabled: ro });
    const dossier = h('input', { cls: 'eqi-in', placeholder: 'Référence dossier (facultatif)' });
    const res = h('div', { cls: 'eqi-resultat' });
    const corps = () => ({ machine_id: parseInt(mac.value, 10) || null, operation_code: cod.value, modele_id: parseInt(mod.value, 10) || null,
      imprimante_id: parseInt(imp.value, 10) || null, exemplaires: parseInt(ex.value, 10) || 1, fin_dossier_seulement: fin.checked, actif: act.checked });
    const actions = ro ? [] : [
      bouton('Enregistrer', 'Enregistrer', async () => {
        try { const x = r.id ? await api('/regles/' + r.id, { method: 'PATCH', body: corps() }) : await api('/regles', { method: 'POST', body: corps() });
          toast('Règle enregistrée.'); aller(x.id); } catch (e) { toast(e.message, 'error'); }
      }, 'accent')];
    if (r.id && !ro) {
      actions.push(bouton('Essai', 'Essayer', async () => {
        remplacer(res, h('div', { cls: 'eqi-aide', text: 'Impression d\'essai…' }));
        try {
          const x = await api('/regles/' + r.id + '/essai', { method: 'POST', body: { dossier: dossier.value || null } });
          remplacer(res, ...(x.resultats || []).map(y => h('div', { cls: 'eqi-msg eqi-msg--' + (y.statut === 'erreur' ? 'danger' : 'ok'),
            text: y.statut === 'erreur' ? y.erreur || 'Échec.' : (y.statut_libelle || y.statut) + ' · n°' + y.journal_id })));
          if (!(x.resultats || []).length) remplacer(res, h('div', { cls: 'eqi-msg', text: 'Règle inactive : rien à imprimer.' }));
        } catch (e) { remplacer(res, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); }
      }, null, 'printer'));
      const sup = bouton('Supprimer', 'Supprimer', async () => {
        if (!sup.dataset.arme) { sup.dataset.arme = '1'; sup.querySelector('span:last-child').textContent = 'Confirmer la suppression'; return; }
        try { await api('/regles/' + r.id, { method: 'DELETE' }); toast('Règle supprimée.'); aller('liste'); } catch (e) { toast(e.message, 'error'); }
      }, 'danger');
      actions.push(sup);
    }
    return h('div', { cls: 'eqi-form' },
      h('div', { cls: 'eqi-grille' }, champ('Machine', mac), champ('Code saisi', cod, '89 = fin de production'),
        champ('Modèle', mod, 'Imprimé dans sa version approuvée'), champ('Imprimante', imp, 'Réseau ou agent seulement'),
        champ('Exemplaires', ex), h('label', { cls: 'eqi-champ' }, h('span', { cls: 'eqi-lib', text: 'Fin de dossier seulement' }), fin),
        h('label', { cls: 'eqi-champ' }, h('span', { cls: 'eqi-lib', text: 'Active' }), act)),
      r.id && !ro ? champ('Essai avec un dossier', dossier) : null,
      h('div', { cls: 'eqi-ligne' }, actions), res);
  }

  // ── Kiosque ─────────────────────────────────────────────────────────
  function profil() {
    const id = (() => { try { return localStorage.getItem('mysifa.etiq.imprimante'); } catch (e) { return null; } })();
    return (X.I.profils || []).find(p => String(p.id) === String(id)) || null;
  }
  async function ouvrirKiosque() {
    if (K.actif) return;
    K.actif = true;
    K.el = h('div', { cls: 'eqk', role: 'main' });
    document.body.appendChild(K.el);
    try { await X.charger(); K.modeles = (await api('/kiosque')).modeles; } catch (e) { toast(e.message, 'error'); K.modeles = []; }
    rendreKiosque();
    X.signaler();
  }
  function fermerKiosque() {
    K.actif = false; K.modele = null; K.dossier = null; K.champsDossier = {};
    if (K.el) K.el.remove();
    K.el = null;
    X.signaler();
  }
  function rendreKiosque() {
    if (!K.el) return;
    const p = profil();
    const scan = h('input', { cls: 'eqi-in', placeholder: 'Scanner un modèle ou un dossier', autocomplete: 'off', 'aria-label': 'Scan' });
    scan.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); resoudre(scan.value); scan.value = ''; } });
    const barre = h('div', { cls: 'eqk-barre' }, ic('printer', 22), h('div', { cls: 'eqk-titre', text: K.modele ? K.modele.nom : 'Étiquettes · atelier' }),
      bouton(p ? p.nom : 'Choisir l\'imprimante', 'Imprimante', async () => { await M.choisirImprimante(); rendreKiosque(); }, p ? null : 'accent', 'settings'),
      bouton('Quitter', 'Quitter', () => fermerKiosque(), null, 'x'));
    const corps = h('div', { cls: 'eqk-corps' },
      h('div', { cls: 'eqk-scan' }, scan, bouton('Caméra', 'Caméra', () => {
        if (!window.MySifaScanner) { toast('Scanner indisponible sur cette page.', 'error'); return; }
        MySifaScanner.demarrer({ hint: 'Code du modèle ou du dossier', onCode: c => { try { MySifaScanner.arreter(); } catch (e) {} resoudre(c); } });
      }, 'eqk-gros', 'scan')),
      K.dossier ? h('div', { cls: 'eqi-msg eqi-msg--ok' }, 'Dossier ' + K.dossier, ' ', bouton('', 'Retirer', () => { K.dossier = null; K.champsDossier = {}; rendreKiosque(); X.signaler(); }, null, 'x')) : null,
      K.modele ? formulaire() : grille());
    remplacer(K.el, barre, corps);
    requestAnimationFrame(() => { const i = K.el && K.el.querySelector(K.modele ? '.eqk-form input' : '.eqk-scan input'); if (i) i.focus(); });
  }
  function grille() {
    if (!K.modeles || !K.modeles.length) return h('div', { cls: 'eqi-vide', text: 'Aucun modèle approuvé.' });
    return h('div', { cls: 'eqk-grille' }, ...K.modeles.map(m => h('button', { type: 'button', cls: 'eqk-tuile', 'data-bulle': 'Choisir',
      onclick: () => { K.modele = m; rendreKiosque(); X.signaler(); } },
      h('span', { cls: 'eqk-tuile-nom', text: m.nom }),
      h('span', { cls: 'eqi-aide', text: ['M' + m.id, m.usage, m.client, m.largeur_mm + '×' + m.hauteur_mm + ' mm'].filter(Boolean).join(' · ') }))));
  }
  function valeursDossier(m) {
    const out = {};
    (m.saisies || []).forEach(v => { if (v.type === 'source' && v.champ && K.champsDossier[v.champ] != null) out[v.nom] = K.champsDossier[v.champ]; });
    return out;
  }
  function formulaire() {
    const m = K.modele;
    const pre = valeursDossier(m);
    let lire;
    let zone;
    const E = window.EtiqSpec;
    if (E && typeof E.formulaireOperateur === 'function') {
      try { const f = E.formulaireOperateur(m, pre); zone = f.el; lire = f.valeurs; } catch (e) { zone = null; }
    }
    if (!zone) {
      const champs = {};
      zone = h('div', { cls: 'eqk-form' }, ...(m.saisies || []).map(v => {
        const i = h('input', { cls: 'eqi-in', value: pre[v.nom] != null ? pre[v.nom] : (v.valeur || ''), autocomplete: 'off' });
        champs[v.nom] = i;
        return champ(v.libelle + (v.obligatoire ? ' *' : ''), i);
      }));
      if (!(m.saisies || []).length) zone.appendChild(h('div', { cls: 'eqi-aide', text: 'Aucune donnée à saisir.' }));
      lire = () => Object.fromEntries(Object.entries(champs).map(([k, i]) => [k, i.value]));
    }
    const qte = h('input', { cls: 'eqi-in', type: 'number', min: 1, max: 999, value: 1 });
    const res = h('div', { cls: 'eqi-resultat' });
    const go = bouton('Imprimer', 'Imprimer', async () => {
      let p = profil();
      if (!p) {
        p = await M.choisirImprimante();
        if (!p) return;
        const nom = K.el && K.el.querySelector('.eqk-barre .eqi-btn span:last-child');
        if (nom) nom.textContent = p.nom;
      }
      const rec = lire();
      const manque = (m.saisies || []).filter(v => v.obligatoire && !String(rec[v.nom] || '').trim()).map(v => v.libelle);
      if (manque.length) { toast('À renseigner : ' + manque.join(', ') + '.', 'error'); return; }
      go.disabled = true;
      remplacer(res, h('div', { cls: 'eqi-aide', text: 'Envoi…' }));
      try {
        const r = await X.api('/imprimer', { method: 'POST', body: { modele: { id: m.id }, enregistrements: [rec],
          quantite: parseInt(qte.value, 10) || 1, profil_id: p.id, source: 'kiosque' } });
        await X.livrer(r);
        remplacer(res, h('div', { cls: 'eqi-msg eqi-msg--' + (r.statut === 'erreur' ? 'danger' : 'ok') },
          X.badgeStatut(r.statut, r.statut_libelle), ' ', r.erreur || (r.etiquettes + ' × ' + r.exemplaires + ' · ' + r.imprimante)));
        if (r.statut !== 'erreur' && (r.attendus || []).length) res.appendChild(X.blocVerification(r.journal_id));
      } catch (e) { remplacer(res, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); }
      go.disabled = false;
    }, 'accent eqk-gros', 'printer');
    return h('div', { cls: 'eqi-col' }, zone,
      h('div', { cls: 'eqi-ligne' }, champ('Exemplaires', qte), go,
        bouton('Autre modèle', 'Retour', () => { K.modele = null; rendreKiosque(); X.signaler(); }, 'eqk-gros', 'left')),
      res);
  }
  async function resoudre(code) {
    const c = String(code || '').trim();
    if (!c) return;
    try {
      const r = await api('/kiosque/scan?code=' + encodeURIComponent(c));
      if (r.type === 'modele') K.modele = r.modele;
      else { K.dossier = r.reference; K.champsDossier = r.champs || {}; toast('Dossier ' + r.reference + ' chargé.'); }
      rendreKiosque(); X.signaler();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Adresse ─────────────────────────────────────────────────────────
  const CLES = ['mode', 'kiosque_modele', 'kiosque_dossier', 'parc_impression', 'regles_impression'];
  function etat() {
    const a = {};
    if (K.actif) {
      a.mode = 'kiosque';
      if (K.modele) a.kiosque_modele = String(K.modele.id);
      if (K.dossier) a.kiosque_dossier = K.dossier;
    }
    if (K.fen) a[K.fen.cle] = K.fen.valeur;
    return a;
  }
  async function aller(a) {
    a = a || {};
    if (a.mode === 'kiosque') {
      if (!K.actif) await ouvrirKiosque();
      const mid = /^\d+$/.test(a.kiosque_modele || '') ? a.kiosque_modele : null;
      const doss = String(a.kiosque_dossier || '').slice(0, 60) || null;
      let change = false;
      if (doss !== K.dossier) {
        K.dossier = null; K.champsDossier = {};
        if (doss) { try { const r = await api('/kiosque/scan?code=' + encodeURIComponent(doss)); if (r.type === 'dossier') { K.dossier = r.reference; K.champsDossier = r.champs || {}; } } catch (e) {} }
        change = true;
      }
      const m = mid ? (K.modeles || []).find(x => String(x.id) === mid) || null : null;
      if ((m && m.id) !== (K.modele && K.modele.id)) { K.modele = m; change = true; }
      if (change) rendreKiosque();
    } else if (K.actif) fermerKiosque();
    if (a.parc_impression === '1') { if (!(K.fen && K.fen.cle === 'parc_impression')) ouvrirParc(); }
    else if (a.regles_impression && /^(liste|nouvelle|\d+)$/.test(a.regles_impression)) {
      if (!(K.fen && K.fen.cle === 'regles_impression' && K.fen.valeur === a.regles_impression)) ouvrirRegles(a.regles_impression);
    } else if (K.fen) fermerFen(true);
  }
  function lire() {
    const sp = new URLSearchParams(location.search);
    if (sp.get('outil') !== 'etiquettes') return {};
    const a = {};
    CLES.forEach(k => { const v = sp.get(k); if (v && v.length <= 120) a[k] = v; });
    return a;
  }
  function envelopper() {
    const U = window.MySifaUrl;
    if (!U || !U.ecrire || U.ecrire.__etiqKiosque) return;
    const orig = U.ecrire;
    U.ecrire = function (params, opts) {
      // Seulement sur l'outil Étiquettes, et seulement si la page n'a pas
      // repris ces clés elle-même (adresseAtelier.integree) : `mode` sert
      // aussi à d'autres outils (Image : mode=vectoriser).
      if ((params || {}).outil !== 'etiquettes' || M.adresseAtelier.integree) return orig.call(this, params, opts);
      const p = Object.assign({}, params);
      CLES.forEach(k => delete p[k]);
      Object.assign(p, etat());
      const o = Object.assign({}, opts || {});
      if (K.fen || K.modele) o.navigation = String(o.navigation === undefined ? '' : o.navigation) + '/' + (K.fen ? K.fen.cle : 'kiosque:' + K.modele.id);
      return orig.call(this, p, o);
    };
    U.ecrire.__etiqKiosque = true;
  }
  function demarrer() {
    envelopper();
    const a = lire();
    if (Object.keys(a).length) setTimeout(() => aller(a), 450);
    if (window.MySifaUrl && MySifaUrl.surRetour) MySifaUrl.surRetour(async () => { await aller(lire()); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();

  Object.assign(M, {
    ouvrirParc, ouvrirRegles,
    kiosque: { ouvrir: ouvrirKiosque, fermer: fermerKiosque },
    adresseAtelier: { etat, aller, cles: CLES },
  });
})();
