/* MyTools › Étiquettes — chaîne d'impression (côté navigateur).
 *
 * API publique (window.MySifaEtiqImpression) :
 *
 *   imprimer({modele, enregistrements, quantite, serie, titre}) → Promise<résultat|null>
 *       modele         {id?, nom, largeur_mm, hauteur_mm, layout:{elements, variables}}
 *                      (un modèle enregistré peut être passé par son seul id)
 *       enregistrements [{nom_variable: valeur}, …] : une étiquette par ligne
 *       quantite       exemplaires identiques de chaque étiquette
 *       serie          N étiquettes distinctes (compteurs, SSCC) depuis un seul enregistrement
 *     Ouvre la fenêtre d'impression : imprimante, mode d'envoi, aperçu rendu
 *     par le serveur (aucun service extérieur), puis vérification par scan.
 *
 *   imprimerRendu({nom, pdf|image, largeur_mm, hauteur_mm, donnees, attendu, quantite, repli})
 *       Postes traça sans modèle vectoriel : le PDF (Blob, ArrayBuffer ou
 *       base64) ou l'image (dataURL, Blob, canvas) qu'ils produisent déjà est
 *       tramé par le serveur au format du profil. `attendu` :
 *       [{symbologie, donnee}] pour la vérification. `repli()` : impression
 *       navigateur d'origine, proposée si aucune imprimante n'est configurée.
 *
 *   choisirImprimante() → Promise<profil|null>   (mémorisée par poste, localStorage)
 *   ouvrirJournal(filtres?) · ouvrirProfils(id?) · verifier(journalId)
 *
 *   adresse = { etat(), aller(a), cles }   fenêtres et filtres du journal :
 *       journal_impression=liste|<id>, journal_du, journal_au, journal_imprimante,
 *       journal_utilisateur, journal_statut, journal_verif, profils_impression=liste|nouveau|<id>
 *     Le module enveloppe MySifaUrl.ecrire (comme chat_url.js) : ses clés
 *     suivent les écritures de la page, et une fenêtre ouverte s'ajoute à
 *     la navigation (Retour la ferme). La fenêtre d'impression elle-même
 *     n'entre pas dans l'adresse : c'est une sortie d'impression.
 *
 * API serveur : app/routers/etiq_impression.py (/api/tools/etiquettes/impression).
 */
(function () {
  'use strict';
  if (window.MySifaEtiqImpression) return;

  const API = '/api/tools/etiquettes/impression';
  const CLE_IMPRIMANTE = 'mysifa.etiq.imprimante';
  const I = {
    config: null, profils: null, agents: [], admin: false, bp: undefined,
    fen: null,                // fenêtre adressable ouverte : {cle, valeur, el}
    journal: { du: '', au: '', imprimante: '', utilisateur: '', statut: '', verif: '', q: '', detail: null },
    ecoute: [],
  };

  // ── Outils ──────────────────────────────────────────────────────────
  // replaceChildren insère « null » en texte : on filtre les absents.
  function remplacer(el, ...k) { el.replaceChildren(...k.flat().filter(c => c !== null && c !== undefined && c !== false)); }
  function h(tag, attrs, ...enfants) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'cls') e.className = v;
      else if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (k === 'value') e.value = v;
      else if (k === 'checked' || k === 'disabled' || k === 'selected') e[k] = !!v;
      else e.setAttribute(k, v === true ? '' : v);
    }
    enfants.flat(Infinity).forEach(c => {
      if (c === null || c === undefined || c === false) return;
      e.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
    });
    return e;
  }
  const ICONES = {
    printer: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/>',
    list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 1v3M12 20v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M1 12h3M20 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>',
    x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    repeat: '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    left: '<polyline points="15 18 9 12 15 6"/>', right: '<polyline points="9 18 15 12 9 6"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  };
  function ic(nom, taille) {
    const s = h('span', { cls: 'eqi-ic' });
    const n = taille || 15;
    s.innerHTML = '<svg width="' + n + '" height="' + n + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
      + 'stroke-linecap="round" stroke-linejoin="round">' + (ICONES[nom] || '') + '</svg>';
    return s;
  }
  function bouton(texte, bulle, onclick, variante, icone) {
    const cls = String(variante || '').split(/\s+/).filter(Boolean).map(v => v.startsWith('eqk') ? v : 'eqi-btn--' + v);
    return h('button', { type: 'button', cls: ['eqi-btn'].concat(cls).join(' '), 'data-bulle': bulle, onclick },
      icone ? ic(icone, 14) : null, texte ? h('span', { text: texte }) : null);
  }
  function toast(msg, type) {
    if (typeof window.showToast === 'function') window.showToast(msg, type === 'error' ? 'danger' : (type || 'success'));
  }
  async function api(chemin, opts) {
    opts = opts || {};
    const init = { method: opts.method || 'GET', credentials: 'include', cache: 'no-store', headers: {} };
    if (opts.body !== undefined) { init.body = JSON.stringify(opts.body); init.headers['Content-Type'] = 'application/json'; }
    const r = await fetch(API + chemin, init);
    if (r.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); throw new Error('Session expirée.'); }
    if (opts.brut) { if (!r.ok) throw new Error(await messageErreur(r)); return r; }
    if (!r.ok) throw new Error(await messageErreur(r));
    return r.json();
  }
  async function messageErreur(r) {
    try { const j = await r.json(); return typeof j.detail === 'string' ? j.detail : 'Erreur ' + r.status + '.'; }
    catch (e) { return 'Erreur ' + r.status + '.'; }
  }
  function lsLire(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsEcrire(k, v) { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }
  function fmtDate(s) {
    if (!s) return '';
    const [d, t] = String(s).split('T');
    const [a, m, j] = d.split('-');
    return j + '/' + m + '/' + a.slice(2) + ' ' + (t || '').slice(0, 5);
  }
  function b64VersBlob(b64, mime) {
    const bin = atob(b64);
    const u = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return new Blob([u], { type: mime || 'application/octet-stream' });
  }
  async function versB64(x) {
    if (!x) return null;
    if (typeof x === 'string') return x.startsWith('data:') ? x.split(',')[1] : x;
    if (x instanceof HTMLCanvasElement) return x.toDataURL('image/png').split(',')[1];
    const buf = x instanceof Blob ? await x.arrayBuffer() : x;
    const u = new Uint8Array(buf);
    let s = '';
    for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function telecharger(blob, nom) {
    const url = URL.createObjectURL(blob);
    const a = h('a', { href: url, download: nom });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  }
  function signaler() { I.ecoute.forEach(fn => { try { fn(); } catch (e) {} }); ecrireAdresse(); }

  // ── Données ─────────────────────────────────────────────────────────
  async function charger(force) {
    if (I.profils && !force) return;
    const [cfg, pr] = await Promise.all([I.config && !force ? I.config : api('/config'), api('/profils')]);
    I.config = cfg; I.profils = pr.profils; I.agents = pr.agents || []; I.admin = !!pr.peut_administrer;
  }
  function profilMemorise() {
    const id = lsLire(CLE_IMPRIMANTE);
    return (I.profils || []).find(p => String(p.id) === String(id)) || null;
  }
  function profilParDefaut() {
    return profilMemorise() || (I.profils || [])[0] || null;
  }

  // Zebra Browser Print : service local du poste (127.0.0.1), aucun tiers.
  async function browserPrint() {
    if (I.bp !== undefined) return I.bp;
    I.bp = null;
    for (const base of ['https://127.0.0.1:9101', 'http://127.0.0.1:9100']) {
      try {
        const ctl = new AbortController();
        const t = setTimeout(() => ctl.abort(), 900);
        const r = await fetch(base + '/default?type=printer', { signal: ctl.signal });
        clearTimeout(t);
        if (r.ok) {
          const txt = await r.text();
          if (txt && txt.trim()) { I.bp = { base, device: JSON.parse(txt) }; break; }
        }
      } catch (e) { /* absent : mode masqué */ }
    }
    return I.bp;
  }
  async function envoyerBrowserPrint(b64) {
    const bp = await browserPrint();
    if (!bp) throw new Error('Zebra Browser Print absent de ce poste.');
    const r = await fetch(bp.base + '/write', { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: JSON.stringify({ device: bp.device, data: atob(b64) }) });
    if (!r.ok) throw new Error('Browser Print a refusé l\'envoi (' + r.status + ').');
  }

  // ── Fenêtres ────────────────────────────────────────────────────────
  // Une seule pile : la fenêtre d'impression (hors adresse) peut s'ouvrir
  // par-dessus le journal (réimpression).
  function fenetre(titre, corps, opts) {
    opts = opts || {};
    const ov = h('div', { cls: 'eqi-ov' + (opts.large ? ' eqi-ov--large' : ''), role: 'dialog', 'aria-label': titre });
    const fermer = h('button', { type: 'button', cls: 'eqi-x', 'data-bulle': 'Fermer', 'aria-label': 'Fermer',
      onclick: () => opts.fermer ? opts.fermer() : ov.remove() }, ic('x', 16));
    const carte = h('div', { cls: 'eqi-carte' }, h('div', { cls: 'eqi-tete' }, h('div', { cls: 'eqi-titre', text: titre }),
      opts.actions || null, fermer), corps);
    ov.appendChild(carte);
    ov.addEventListener('mousedown', e => { if (e.target === ov) (opts.fermer ? opts.fermer() : ov.remove()); });
    ov.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); opts.fermer ? opts.fermer() : ov.remove(); } });
    document.body.appendChild(ov);
    return ov;
  }
  function ouvrirAdressable(cle, valeur, construire) {
    fermerAdressable(true);
    const el = construire();
    I.fen = { cle, valeur: String(valeur), el };
    signaler();
    return el;
  }
  function fermerAdressable(sansAdresse) {
    if (!I.fen) return;
    const f = I.fen; I.fen = null;
    if (f.el && f.el.isConnected) f.el.remove();
    if (!sansAdresse) signaler();
  }
  function champ(libelle, input, aide) {
    return h('label', { cls: 'eqi-champ' }, h('span', { cls: 'eqi-lib', text: libelle }), input,
      aide ? h('span', { cls: 'eqi-aide', text: aide }) : null);
  }
  function selectProfils(valeur, avecVide) {
    const s = h('select', { cls: 'eqi-in' });
    if (avecVide) s.appendChild(h('option', { value: '', text: avecVide }));
    (I.profils || []).forEach(p => s.appendChild(h('option', { value: p.id,
      text: p.nom + (p.poste ? ' · ' + p.poste : '') + ' · ' + String(p.langage).toUpperCase() + ' ' + p.dpi + ' dpi' })));
    if (valeur !== undefined && valeur !== null) s.value = String(valeur);
    return s;
  }
  function badgeStatut(statut, libelle) {
    const ton = { envoye: 'ok', imprime: 'ok', en_file: 'info', telecharge: 'neutre', pdf: 'neutre', prepare: 'neutre', erreur: 'danger' }[statut] || 'neutre';
    return h('span', { cls: 'eqi-badge eqi-badge--' + ton, text: libelle || statut });
  }
  function badgeVerif(v) {
    if (!v) return h('span', { cls: 'eqi-badge eqi-badge--neutre', text: 'Non vérifiée' });
    if (v === 'ok') return h('span', { cls: 'eqi-badge eqi-badge--ok', text: 'Conforme' });
    return h('span', { cls: 'eqi-badge eqi-badge--danger', text: 'Écart' });
  }

  // ── Fenêtre d'impression ────────────────────────────────────────────
  function sessionImpression(o) {
    // o : {titre, modele?, enregistrements?, quantite, serie, rendu?, repli?, reimpression?}
    return new Promise(async resolve => {
      try { await charger(); } catch (e) { toast(e.message, 'error'); resolve(null); return; }
      if (!(I.profils || []).length) {
        if (o.rendu && typeof o.repli === 'function') { o.repli(); resolve(null); return; }
        toast('Aucune imprimante configurée — à créer dans Profils d\'imprimante (administrateurs).', 'error');
        if (I.admin) ouvrirProfils('nouveau');
        resolve(null); return;
      }
      const etat = { profil: profilParDefaut(), index: 0, resultat: null, occupe: false };
      const recs = (o.enregistrements && o.enregistrements.length) ? o.enregistrements : [{}];
      let ov;
      const fin = () => { if (ov) ov.remove(); document.removeEventListener('keydown', echap, true); resolve(etat.resultat); };
      const echap = e => { if (e.key === 'Escape' && ov && ov.isConnected && !(window.MySifaScanner && MySifaScanner.actif())) { e.preventDefault(); fin(); } };

      const sel = selectProfils(etat.profil && etat.profil.id);
      const modeSel = h('select', { cls: 'eqi-in' });
      const qte = h('input', { cls: 'eqi-in', type: 'number', min: 1, max: (I.config && I.config.copies_max) || 999, value: o.quantite || 1 });
      const img = h('img', { cls: 'eqi-apercu-img', alt: 'Aperçu' });
      const apercuInfo = h('div', { cls: 'eqi-aide' });
      const nav = h('div', { cls: 'eqi-nav' });
      const zoneRes = h('div', { cls: 'eqi-resultat' });
      const go = bouton('Imprimer', 'Imprimer', () => lancer(), 'accent', 'printer');

      function remplirModes() {
        const p = etat.profil;
        remplacer(modeSel);
        const modes = (p && p.modes) || [];
        modeSel.appendChild(h('option', { value: '', text: 'Selon le profil (' + ((I.config && I.config.modes[p && p.mode_envoi]) || 'Automatique') + ')' }));
        modes.forEach(m => { if (m !== 'navigateur' || I.bp) modeSel.appendChild(h('option', { value: m, text: (I.config && I.config.modes[m]) || m })); });
      }
      let urlApercu = null;
      async function apercu() {
        if (o.rendu) {
          if (o.rendu.apercuUrl) { img.src = o.rendu.apercuUrl; img.hidden = false; }
          else { img.hidden = true; apercuInfo.textContent = 'Rendu PDF du poste : tramé au format de l\'imprimante à l\'envoi.'; }
          return;
        }
        apercuInfo.textContent = 'Aperçu en cours…';
        try {
          const r = await api('/apercu.png', { method: 'POST', brut: true, body: { modele: o.modele,
            enregistrement: recs[etat.index] || {}, profil_id: etat.profil && etat.profil.id } });
          const b = await r.blob();
          if (urlApercu) URL.revokeObjectURL(urlApercu);
          urlApercu = URL.createObjectURL(b);
          img.src = urlApercu; img.hidden = false;
          const p = etat.profil;
          apercuInfo.textContent = 'Rendu interne à ' + (p ? p.dpi : 203) + ' dpi — police interne approchée, codes exacts.';
        } catch (e) { img.hidden = true; apercuInfo.textContent = e.message; }
        remplacer(nav);
        if (recs.length > 1) nav.append(
          bouton('', 'Précédente', () => { if (etat.index > 0) { etat.index--; apercu(); } }, null, 'left'),
          h('span', { text: (etat.index + 1) + ' / ' + recs.length }),
          bouton('', 'Suivante', () => { if (etat.index < recs.length - 1) { etat.index++; apercu(); } }, null, 'right'));
      }
      sel.addEventListener('change', () => {
        etat.profil = (I.profils || []).find(p => String(p.id) === sel.value) || null;
        if (etat.profil) lsEcrire(CLE_IMPRIMANTE, String(etat.profil.id));
        remplirModes(); apercu();
      });

      async function lancer() {
        if (etat.occupe || !etat.profil) return;
        const q = parseInt(qte.value, 10);
        if (!(q >= 1)) { toast('Quantité invalide.', 'error'); return; }
        etat.occupe = true; go.disabled = true; remplacer(zoneRes, h('div', { cls: 'eqi-aide', text: 'Envoi…' }));
        try {
          let r;
          if (o.reimpression) r = await api('/journal/' + o.reimpression + '/reimprimer', { method: 'POST',
            body: { profil_id: etat.profil.id, mode: modeSel.value || null, quantite: q } });
          else if (o.rendu) r = await api('/rendu', { method: 'POST', body: Object.assign({}, o.rendu.corps,
            { profil_id: etat.profil.id, mode: modeSel.value || null, quantite: q }) });
          else r = await api('/imprimer', { method: 'POST', body: { modele: o.modele, enregistrements: recs,
            quantite: q, serie: o.serie || null, profil_id: etat.profil.id, mode: modeSel.value || null } });
          await livrer(r);
          etat.resultat = r;
          afficherResultat(r);
        } catch (e) {
          remplacer(zoneRes, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message }));
          if (o.rendu && typeof o.repli === 'function') zoneRes.appendChild(bouton('Impression navigateur', 'Navigateur', () => { fin(); o.repli(); }, null, 'printer'));
        } finally { etat.occupe = false; go.disabled = false; }
      }

      function afficherResultat(r) {
        const ton = r.statut === 'erreur' ? 'danger' : 'ok';
        remplacer(zoneRes, h('div', { cls: 'eqi-msg eqi-msg--' + ton },
          badgeStatut(r.statut, r.statut_libelle), ' ',
          r.erreur ? r.erreur : (r.etiquettes + ' étiquette' + (r.etiquettes > 1 ? 's' : '') + ' × ' + r.exemplaires
            + ' · ' + r.imprimante + ' · n°' + r.journal_id)));
        if (r.statut !== 'erreur' && (r.attendus || []).length) zoneRes.appendChild(blocVerification(r.journal_id));
        toast(r.statut === 'erreur' ? 'Impression en échec.' : 'Impression lancée.', r.statut === 'erreur' ? 'error' : 'success');
      }

      const corps = h('div', { cls: 'eqi-corps eqi-corps--imp' },
        h('div', { cls: 'eqi-col' },
          champ('Imprimante', sel), champ('Envoi', modeSel), champ('Exemplaires', qte,
            recs.length > 1 ? recs.length + ' étiquettes différentes, chacune en autant d\'exemplaires.' : (o.serie ? o.serie + ' étiquettes en série.' : null)),
          h('div', { cls: 'eqi-ligne' }, go,
            I.admin ? bouton('Profils', 'Profils', () => ouvrirProfils(etat.profil ? etat.profil.id : 'liste'), null, 'settings') : null,
            bouton('Journal', 'Journal', () => ouvrirJournal(), null, 'list'),
            window.MySifaEtiqImpression.ouvrirParc ? bouton('Parc', 'Parc', () => window.MySifaEtiqImpression.ouvrirParc(), null, 'activity') : null),
          zoneRes),
        h('div', { cls: 'eqi-col eqi-apercu' }, img, nav, apercuInfo));
      ov = fenetre(o.titre || 'Impression', corps, { large: true, fermer: fin });
      document.addEventListener('keydown', echap, true);
      browserPrint().then(() => remplirModes());
      remplirModes(); apercu();
      requestAnimationFrame(() => go.focus());
    });
  }

  async function livrer(r) {
    if (!r.contenu_b64) return;
    if (r.mode === 'fichier') telecharger(b64VersBlob(r.contenu_b64, r.mime), r.nom_fichier);
    else if (r.mode === 'pdf') {
      const url = URL.createObjectURL(b64VersBlob(r.contenu_b64, 'application/pdf'));
      const w = window.open(url, '_blank');
      if (!w) telecharger(b64VersBlob(r.contenu_b64, 'application/pdf'), r.nom_fichier);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } else if (r.mode === 'navigateur') {
      try {
        await envoyerBrowserPrint(r.contenu_b64);
        const s = await api('/journal/' + r.journal_id + '/resultat', { method: 'POST', body: { statut: 'envoye' } });
        r.statut = s.statut; r.statut_libelle = s.statut_libelle;
      } catch (e) {
        await api('/journal/' + r.journal_id + '/resultat', { method: 'POST', body: { statut: 'erreur', erreur: e.message } }).catch(() => {});
        r.statut = 'erreur'; r.statut_libelle = 'Erreur'; r.erreur = e.message;
      }
    }
  }

  // ── Vérification par scan ───────────────────────────────────────────
  // Lecture par la caméra (mysifa_scanner.js), ou au clavier : douchette ou
  // vérificateur branché en émulation clavier, qui saisit puis valide.
  function blocVerification(jid, apres) {
    const res = h('div', { cls: 'eqi-verif-res' });
    const saisie = h('input', { cls: 'eqi-in', placeholder: 'Douchette ou saisie du code lu', autocomplete: 'off' });
    async function soumettre(lu) {
      if (!String(lu || '').trim()) return;
      try {
        const r = await api('/journal/' + jid + '/verification', { method: 'POST', body: { lu: lu } });
        remplacer(res, r.statut === 'ok'
          ? h('div', { cls: 'eqi-msg eqi-msg--ok' }, badgeVerif('ok'), ' ', r.element ? 'Code « ' + r.element + ' » lu conforme.' : 'Lecture conforme.',
            r.note ? h('span', { cls: 'eqi-badge eqi-badge--info', text: 'Note ' + r.note }) : null)
          : h('div', { cls: 'eqi-msg eqi-msg--danger' }, badgeVerif('ecart'), ' ', 'Lu « ' + r.lu + ' »'
            + (r.attendu ? ', attendu « ' + r.attendu + ' ».' : '.')));
        saisie.value = '';
        if (typeof apres === 'function') apres(r);
      } catch (e) { remplacer(res, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); }
    }
    saisie.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); soumettre(saisie.value); } });
    const cam = bouton('Scanner', 'Caméra', () => {
      if (!window.MySifaScanner) { toast('Scanner indisponible sur cette page.', 'error'); return; }
      window.MySifaScanner.demarrer({ hint: 'Pointez le code imprimé', onCode: c => { try { MySifaScanner.arreter(); } catch (e) {} soumettre(c); } });
    }, null, 'scan');
    return h('div', { cls: 'eqi-verif' }, h('div', { cls: 'eqi-lib', text: 'Vérifier le code imprimé' }),
      h('div', { cls: 'eqi-ligne' }, cam, saisie, bouton('Valider', 'Comparer', () => soumettre(saisie.value))), res);
  }

  function verifier(jid) {
    const ov = fenetre('Vérification · impression n°' + jid, h('div', { cls: 'eqi-corps' }, blocVerification(jid, () => {
      if (I.fen && I.fen.cle === 'journal_impression') rafraichirJournal();
    })));
    requestAnimationFrame(() => { const i = ov.querySelector('input'); if (i) i.focus(); });
  }

  // ── Choix de l'imprimante ───────────────────────────────────────────
  function choisirImprimante() {
    return new Promise(async resolve => {
      try { await charger(); } catch (e) { toast(e.message, 'error'); resolve(null); return; }
      let ov;
      const fin = p => { if (ov) ov.remove(); if (p) lsEcrire(CLE_IMPRIMANTE, String(p.id)); resolve(p || null); };
      const memo = profilMemorise();
      const liste = h('div', { cls: 'eqi-choix' }, ...(I.profils || []).map(p => h('button', {
        type: 'button', cls: 'eqi-choix-item' + (memo && memo.id === p.id ? ' eqi-choix-item--actif' : ''),
        'data-bulle': 'Choisir', onclick: () => fin(p) },
        ic('printer', 18), h('span', { cls: 'eqi-choix-nom', text: p.nom }),
        h('span', { cls: 'eqi-aide', text: [p.poste, String(p.langage).toUpperCase(), p.dpi + ' dpi', p.largeur_mm + '×' + p.hauteur_mm + ' mm'].filter(Boolean).join(' · ') }))));
      ov = fenetre('Imprimante de ce poste', h('div', { cls: 'eqi-corps' },
        (I.profils || []).length ? liste : h('div', { cls: 'eqi-vide', text: 'Aucune imprimante configurée.' }),
        h('div', { cls: 'eqi-aide', text: 'Le choix est mémorisé sur ce poste.' })), { fermer: () => fin(null) });
    });
  }

  // ── Journal ─────────────────────────────────────────────────────────
  // Liste dans une fenêtre : pas de data-bloc. Un widget d'accueil charge la
  // page en mode embarqué, où aucune fenêtre ne s'ouvre ; le journal n'a donc
  // pas d'emplacement capturable (voir le rapport de mise en place).
  let journalRendu = null;
  function ouvrirJournal(filtres) {
    if (filtres) Object.assign(I.journal, filtres);
    return ouvrirAdressable('journal_impression', I.journal.detail || 'liste', () => {
      const corps = h('div', { cls: 'eqi-corps' });
      const ov = fenetre('Journal d\'impression', corps, { large: true, fermer: () => fermerAdressable(),
        actions: I.admin ? bouton('Profils', 'Profils', () => ouvrirProfils('liste'), null, 'settings') : null });
      journalRendu = corps;
      construireJournal(corps);
      return ov;
    });
  }
  function construireJournal(corps) {
    const J = I.journal;
    const du = h('input', { cls: 'eqi-in', type: 'date', value: J.du });
    const au = h('input', { cls: 'eqi-in', type: 'date', value: J.au });
    const imp = selectProfils(J.imprimante, 'Toutes');
    const uti = h('select', { cls: 'eqi-in' }, h('option', { value: '', text: 'Tous' }));
    const st = h('select', { cls: 'eqi-in' }, h('option', { value: '', text: 'Tous' }),
      ...Object.entries((I.config && I.config.statuts) || {}).map(([k, l]) => h('option', { value: k, text: l })));
    st.value = J.statut;
    const ve = h('select', { cls: 'eqi-in' }, h('option', { value: '', text: 'Toutes' }), h('option', { value: 'ok', text: 'Conformes' }),
      h('option', { value: 'ecart', text: 'Écarts' }), h('option', { value: 'aucune', text: 'Non vérifiées' }));
    ve.value = J.verif;
    const q = h('input', { cls: 'eqi-in', type: 'search', placeholder: 'Rechercher (modèle, données, imprimante, opérateur…)', value: J.q });
    const table = h('div', { cls: 'eqi-table-wrap' });
    const appliquer = () => {
      Object.assign(J, { du: du.value, au: au.value, imprimante: imp.value, utilisateur: uti.value, statut: st.value, verif: ve.value });
      signaler(); chargerJournal(table, uti);
    };
    [du, au, imp, uti, st, ve].forEach(x => x.addEventListener('change', appliquer));
    let t = null;
    q.addEventListener('input', () => { J.q = q.value; clearTimeout(t); t = setTimeout(() => chargerJournal(table, uti), 250); });
    q.addEventListener('keydown', e => { if (e.key === 'Escape' && q.value) { e.stopPropagation(); q.value = ''; J.q = ''; chargerJournal(table, uti); } });
    remplacer(corps, 
      h('div', { cls: 'eqi-filtres' }, champ('Du', du), champ('Au', au), champ('Imprimante', imp), champ('Opérateur', uti),
        champ('Statut', st), champ('Vérification', ve), h('div', { cls: 'eqi-champ eqi-champ--large' }, q)),
      table);
    chargerJournal(table, uti);
  }
  function rafraichirJournal() { if (journalRendu && journalRendu.isConnected) construireJournal(journalRendu); }

  async function chargerJournal(table, uti) {
    const J = I.journal;
    const p = new URLSearchParams();
    ['du', 'au', 'imprimante', 'utilisateur', 'statut', 'verif', 'q'].forEach(k => { if (J[k]) p.set(k, J[k]); });
    remplacer(table, h('div', { cls: 'eqi-aide', text: 'Chargement…' }));
    let d;
    try { d = await api('/journal?' + p.toString()); } catch (e) { remplacer(table, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); return; }
    if (uti && uti.options.length <= 1) {
      (d.utilisateurs || []).forEach(u => uti.appendChild(h('option', { value: u.email, text: u.nom || u.email })));
      uti.value = J.utilisateur;
    }
    if (!d.lignes.length) {
      remplacer(table, h('div', { cls: 'eqi-vide', text: J.q ? 'Aucun résultat pour « ' + J.q + ' »' : 'Aucune impression pour ces filtres.' }));
      return;
    }
    const lignes = [];
    d.lignes.forEach(l => {
      const ouverte = String(J.detail) === String(l.id);
      lignes.push(h('tr', { cls: ouverte ? 'eqi-tr--ouverte' : '' },
        h('td', { text: fmtDate(l.created_at) }),
        h('td', { text: l.created_by_nom || l.created_by || '' }),
        h('td', null, h('div', { text: l.modele_nom || (l.source === 'rendu' ? 'Rendu' : '—') }), h('div', { cls: 'eqi-aide', text: l.resume || '' })),
        h('td', { cls: 'eqi-num', text: l.etiquettes + ' × ' + l.exemplaires }),
        h('td', { text: l.imprimante_nom || '' }),
        h('td', null, badgeStatut(l.statut, l.statut_libelle), l.reimpression_de ? h('div', { cls: 'eqi-aide', text: 'Réimpression de n°' + l.reimpression_de }) : null),
        h('td', null, badgeVerif(l.verif_statut), l.verif_note ? h('span', { cls: 'eqi-badge eqi-badge--info', text: l.verif_note }) : null),
        h('td', { cls: 'eqi-actions' },
          bouton('', 'Détail', () => { J.detail = ouverte ? null : l.id; if (I.fen) I.fen.valeur = String(J.detail || 'liste'); signaler(); chargerJournal(table, uti); }, null, 'list'),
          bouton('', 'Réimprimer', () => reimprimer(l), null, 'repeat'),
          bouton('', 'Vérifier', () => verifier(l.id), null, 'scan'))));
      if (ouverte) lignes.push(h('tr', { cls: 'eqi-tr-detail' }, h('td', { colspan: 8 }, detailJournal(l.id))));
    });
    remplacer(table, h('table', { cls: 'eqi-table' },
      h('thead', null, h('tr', null, ...['Date', 'Par', 'Modèle · données', 'Étiq.', 'Imprimante', 'Statut', 'Vérif.', ''].map(t => h('th', { text: t })))),
      h('tbody', null, ...lignes)),
      d.total > d.lignes.length ? h('div', { cls: 'eqi-aide', text: d.lignes.length + ' sur ' + d.total + ' — affiner les filtres.' }) : null);
  }
  function detailJournal(jid) {
    const box = h('div', { cls: 'eqi-detail', text: 'Chargement…' });
    api('/journal/' + jid).then(d => {
      const vals = d.valeurs || [];
      const cles = [...new Set(vals.flatMap(v => Object.keys(v)))].slice(0, 12);
      remplacer(box, 
        h('div', { cls: 'eqi-aide', text: [d.langage && d.langage.toUpperCase(), d.mode_envoi, d.erreur].filter(Boolean).join(' · ') }),
        vals.length && cles.length ? h('table', { cls: 'eqi-table eqi-table--mini' },
          h('thead', null, h('tr', null, h('th', { text: '#' }), ...cles.map(c => h('th', { text: c })))),
          h('tbody', null, ...vals.slice(0, 50).map((v, i) => h('tr', null, h('td', { text: i + 1 }), ...cles.map(c => h('td', { text: v[c] == null ? '' : String(v[c]) })))))) : null,
        d.tronque ? h('div', { cls: 'eqi-aide', text: 'Série longue : 50 premières lignes affichées.' }) : null,
        (d.attendus || []).length ? h('div', { cls: 'eqi-aide', text: 'Codes attendus : ' + d.attendus.slice(0, 6).map(a => a.donnee).join(' · ') + (d.attendus.length > 6 ? ' …' : '') }) : null,
        d.verif_statut ? h('div', { cls: 'eqi-aide', text: 'Vérifiée le ' + fmtDate(d.verif_at) + ' par ' + (d.verif_par || '') + ' : « ' + (d.verif_lu || '') + ' »' + (d.verif_note ? ' · note ISO ' + d.verif_note : '') }) : null,
        d.origine ? h('div', { cls: 'eqi-aide', text: 'Origine : ' + d.origine }) : null);
    }).catch(e => { box.textContent = e.message; });
    return box;
  }
  function reimprimer(l) {
    sessionImpression({ titre: 'Réimpression · n°' + l.id + (l.modele_nom ? ' · ' + l.modele_nom : ''), reimpression: l.id,
      rendu: l.source === 'rendu' ? { corps: {} } : null, modele: { nom: l.modele_nom }, quantite: l.exemplaires })
      .then(r => { if (r) rafraichirJournal(); });
  }

  // ── Profils d'imprimante (administrateurs) ──────────────────────────
  function ouvrirProfils(id) {
    return ouvrirAdressable('profils_impression', id || 'liste', () => {
      const corps = h('div', { cls: 'eqi-corps' });
      const ov = fenetre('Profils d\'imprimante', corps, { large: true, fermer: () => fermerAdressable() });
      construireProfils(corps, id || 'liste');
      return ov;
    });
  }
  async function construireProfils(corps, id) {
    try {
      I.profils = null; await charger(true);
      const tous = await api('/profils?tous=1');
      remplacer(corps, 
        h('div', { cls: 'eqi-profils' },
          h('div', { cls: 'eqi-profils-liste' },
            I.admin ? bouton('Nouveau', 'Créer', () => allerProfil(corps, 'nouveau'), 'accent', 'plus') : null,
            ...tous.profils.map(p => h('button', { type: 'button', 'data-bulle': 'Modifier',
              cls: 'eqi-choix-item' + (String(id) === String(p.id) ? ' eqi-choix-item--actif' : '') + (p.actif ? '' : ' eqi-inactif'),
              onclick: () => allerProfil(corps, p.id) }, ic('printer', 16), h('span', { cls: 'eqi-choix-nom', text: p.nom }),
              h('span', { cls: 'eqi-aide', text: [p.poste, String(p.langage).toUpperCase(), p.ip ? p.ip + ':' + p.port : (p.agent_nom ? 'Agent ' + p.agent_nom : ''), p.actif ? '' : 'désactivée'].filter(Boolean).join(' · ') })))),
          h('div', { cls: 'eqi-profils-form' }, formulaireProfil(corps, id === 'liste' ? null : (id === 'nouveau' ? {} : tous.profils.find(p => String(p.id) === String(id)))))));
    } catch (e) { remplacer(corps, h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message })); }
  }
  function allerProfil(corps, id) {
    if (I.fen && I.fen.cle === 'profils_impression') I.fen.valeur = String(id);
    signaler();
    construireProfils(corps, id);
  }
  function formulaireProfil(corps, p) {
    if (!p) return h('div', { cls: 'eqi-vide', text: 'Choisir un profil, ou en créer un.' });
    const ro = !I.admin;
    const v = Object.assign({ nom: '', poste: '', langage: 'zpl', dpi: 203, largeur_mm: 100, hauteur_mm: 50, ip: '', port: 9100,
      agent_id: '', decalage_x_mm: 0, decalage_y_mm: 0, vitesse: '', contraste: '', ecart_mm: 2, mode_envoi: 'auto', note: '' }, p);
    const ch = {};
    const inp = (k, type, extra) => (ch[k] = h('input', Object.assign({ cls: 'eqi-in', type: type || 'text', value: v[k] == null ? '' : v[k], disabled: ro }, extra || {})));
    const sel = (k, opts) => { const s = h('select', { cls: 'eqi-in', disabled: ro }, ...opts.map(([val, lib]) => h('option', { value: val, text: lib }))); s.value = String(v[k] == null ? '' : v[k]); return (ch[k] = s); };
    const cfg = I.config || {};
    const form = h('div', { cls: 'eqi-form' },
      h('div', { cls: 'eqi-grille' },
        champ('Nom', inp('nom', 'text', { maxlength: 80 })), champ('Poste par défaut', inp('poste', 'text', { maxlength: 80 })),
        champ('Langage', sel('langage', (cfg.langages || ['zpl']).map(l => [l, l.toUpperCase()]))),
        champ('Résolution', sel('dpi', (cfg.dpi || [203]).map(d => [d, d + ' dpi']))),
        champ('Largeur (mm)', inp('largeur_mm', 'number', { min: 5, max: 400 })), champ('Hauteur (mm)', inp('hauteur_mm', 'number', { min: 5, max: 400 })),
        champ('Adresse réseau', inp('ip', 'text', { placeholder: 'IP ou nom' })),
        champ('Port', inp('port', 'number', { min: 1, max: 65535 }), 'Envoi direct possible sur : ' + (cfg.ports_reseau || []).join(', ')),
        champ('Agent local', sel('agent_id', [['', 'Aucun']].concat(I.agents.map(a => [a.id, a.nom])))),
        champ('Envoi par défaut', sel('mode_envoi', Object.entries(cfg.modes || { auto: 'Automatique' }))),
        champ('Décalage X (mm)', inp('decalage_x_mm', 'number', { step: 0.1, min: -50, max: 50 })),
        champ('Décalage Y (mm)', inp('decalage_y_mm', 'number', { step: 0.1, min: -50, max: 50 })),
        champ('Vitesse (po/s)', inp('vitesse', 'number', { min: 1, max: 14, placeholder: 'Imprimante' })),
        champ('Contraste', inp('contraste', 'number', { min: 0, max: 30, placeholder: 'Imprimante' }), 'ZPL 0-30, EPL/TSPL 0-15'),
        champ('Écart entre étiquettes (mm)', inp('ecart_mm', 'number', { step: 0.5, min: 0, max: 20 }), 'EPL et TSPL'),
        champ('Note', inp('note', 'text', { maxlength: 500 })),
        champ('Module RFID', (ch.rfid = h('input', { type: 'checkbox', checked: !!v.rfid, disabled: ro })), 'ZPL : EPC encodé avec l\'étiquette')),
      h('div', { cls: 'eqi-etat' }));
    if (ro) return form;
    const corpsReq = () => {
      const o = {};
      Object.entries(ch).forEach(([k, el]) => {
        let val = el.type === 'checkbox' ? el.checked : el.value;
        if (['dpi', 'port', 'vitesse', 'contraste', 'agent_id'].includes(k)) val = val === '' ? null : parseInt(val, 10);
        else if (['largeur_mm', 'hauteur_mm', 'decalage_x_mm', 'decalage_y_mm', 'ecart_mm'].includes(k)) val = val === '' ? 0 : parseFloat(String(val).replace(',', '.'));
        o[k] = val;
      });
      return o;
    };
    const enr = bouton('Enregistrer', 'Enregistrer', async () => {
      enr.disabled = true;
      try {
        const r = p.id ? await api('/profils/' + p.id, { method: 'PATCH', body: corpsReq() }) : await api('/profils', { method: 'POST', body: corpsReq() });
        toast('Profil enregistré.'); allerProfil(corps, r.id);
      } catch (e) { toast(e.message, 'error'); enr.disabled = false; }
    }, 'accent');
    const actions = [enr];
    if (p.id) {
      const etatBox = form.querySelector('.eqi-etat');
      actions.push(
        bouton('Test', 'Tester', async () => {
          try { const r = await api('/profils/' + p.id + '/test', { method: 'POST' }); await livrer(r);
            toast(r.statut === 'erreur' ? r.erreur : 'Étiquette de test : ' + r.statut_libelle + '.', r.statut === 'erreur' ? 'error' : 'success'); }
          catch (e) { toast(e.message, 'error'); }
        }, null, 'printer'),
        p.modes && p.modes.includes('reseau') ? bouton('État', 'Interroger', async () => {
          etatBox.textContent = 'Interrogation…';
          try { remplacer(etatBox, rendreEtat(await api('/profils/' + p.id + '/etat'))); } catch (e) { etatBox.textContent = e.message; }
        }, null, 'activity') : null,
        p.actif ? (function () {
          // Deux temps : le premier clic arme, le second désactive.
          const b = bouton('Désactiver', 'Désactiver', async () => {
            if (!b.dataset.arme) { b.dataset.arme = '1'; b.querySelector('span:last-child').textContent = 'Confirmer la désactivation'; return; }
            try { await api('/profils/' + p.id, { method: 'DELETE' }); toast('Imprimante désactivée.'); allerProfil(corps, 'liste'); } catch (e) { toast(e.message, 'error'); }
          }, 'danger');
          return b;
        })() : bouton('Réactiver', 'Réactiver', async () => {
          try { await api('/profils/' + p.id, { method: 'PATCH', body: { actif: true } }); toast('Imprimante réactivée.'); allerProfil(corps, p.id); } catch (e) { toast(e.message, 'error'); }
        }));
    }
    form.appendChild(h('div', { cls: 'eqi-ligne' }, actions));
    return form;
  }
  function rendreEtat(e) {
    if (e.repond === false) return h('div', { cls: 'eqi-msg eqi-msg--danger', text: e.message || 'Hors ligne.' });
    if (!e.lisible) return h('div', { cls: 'eqi-msg', text: e.message || 'Réponse illisible.' });
    const pb = [e.papier_epuise && 'papier épuisé', e.ruban_epuise && 'ruban épuisé', e.tete_ouverte && 'tête ouverte', e.en_pause && 'en pause'].filter(Boolean);
    return h('div', { cls: 'eqi-msg eqi-msg--' + (pb.length ? 'danger' : 'ok'), text: pb.length ? 'En ligne · ' + pb.join(', ') + '.' : 'En ligne, prête.' });
  }

  // ── Rendu des postes traça ──────────────────────────────────────────
  async function imprimerRendu(o) {
    o = o || {};
    let corps = { nom: o.nom || '', largeur_mm: o.largeur_mm || null, hauteur_mm: o.hauteur_mm || null,
      donnees: o.donnees || {}, attendu: o.attendu || [], seuil: o.seuil || 128, tramage: o.tramage || 'seuil' };
    let apercuUrl = null;
    try {
      if (o.pdf) corps.pdf_b64 = await versB64(o.pdf);
      else if (o.image) {
        corps.image_b64 = await versB64(o.image);
        apercuUrl = 'data:image/png;base64,' + corps.image_b64;
      } else throw new Error('Rendu manquant (PDF ou image).');
    } catch (e) { toast(e.message, 'error'); if (typeof o.repli === 'function') o.repli(); return null; }
    return sessionImpression({ titre: o.nom || 'Impression', rendu: { corps, apercuUrl }, quantite: o.quantite || 1, repli: o.repli });
  }

  // ── Adresse ─────────────────────────────────────────────────────────
  const CLES = ['journal_impression', 'journal_du', 'journal_au', 'journal_imprimante', 'journal_utilisateur',
    'journal_statut', 'journal_verif', 'profils_impression'];
  function adresseEtat() {
    const a = {};
    if (!I.fen) return a;
    a[I.fen.cle] = I.fen.valeur;
    if (I.fen.cle === 'journal_impression') {
      const J = I.journal;
      if (J.du) a.journal_du = J.du;
      if (J.au) a.journal_au = J.au;
      if (J.imprimante) a.journal_imprimante = J.imprimante;
      if (J.utilisateur) a.journal_utilisateur = J.utilisateur;
      if (J.statut) a.journal_statut = J.statut;
      if (J.verif) a.journal_verif = J.verif;
    }
    return a;
  }
  async function adresseAller(a) {
    a = a || {};
    const date = v => /^\d{4}-\d{2}-\d{2}$/.test(v || '') ? v : '';
    const jr = a.journal_impression, pr = a.profils_impression;
    if (jr && (jr === 'liste' || /^\d+$/.test(jr))) {
      try { await charger(); } catch (e) { return; }
      Object.assign(I.journal, { du: date(a.journal_du), au: date(a.journal_au),
        imprimante: /^\d+$/.test(a.journal_imprimante || '') ? a.journal_imprimante : '',
        utilisateur: String(a.journal_utilisateur || '').slice(0, 120),
        statut: ((I.config && I.config.statuts) || {})[a.journal_statut] ? a.journal_statut : '',
        verif: ['ok', 'ecart', 'aucune'].includes(a.journal_verif) ? a.journal_verif : '',
        detail: /^\d+$/.test(jr) ? jr : null });
      if (I.fen && I.fen.cle === 'journal_impression') { I.fen.valeur = jr; rafraichirJournal(); }
      else ouvrirJournal();
    } else if (pr && (pr === 'liste' || pr === 'nouveau' || /^\d+$/.test(pr))) {
      try { await charger(); } catch (e) { return; }
      if (!(I.fen && I.fen.cle === 'profils_impression' && I.fen.valeur === pr)) ouvrirProfils(pr);
    } else if (I.fen) fermerAdressable(true);
  }
  function lireAdresse() {
    const sp = new URLSearchParams(location.search);
    const a = {};
    if (sp.get('outil') !== 'etiquettes') return a;
    CLES.forEach(k => { const v = sp.get(k); if (v && v.length <= 120) a[k] = v; });
    return a;
  }
  // Enveloppe de MySifaUrl.ecrire : les clés du module suivent toute
  // écriture de la page ; une fenêtre ouverte prolonge la navigation.
  function envelopper() {
    const U = window.MySifaUrl;
    if (!U || !U.ecrire || U.ecrire.__etiqImpression) return;
    const orig = U.ecrire;
    U.ecrire = function (params, opts) {
      // Seulement sur l'outil Étiquettes, et tant que la page ne porte pas
      // elle-même ces clés (adresse.integree, voir l'en-tête).
      if ((params || {}).outil !== 'etiquettes' || window.MySifaEtiqImpression.adresse.integree) return orig.call(this, params, opts);
      const p = Object.assign({}, params || {});
      CLES.forEach(k => delete p[k]);
      Object.assign(p, adresseEtat());
      const o = Object.assign({}, opts || {});
      if (I.fen) o.navigation = String(o.navigation === undefined ? '' : o.navigation) + '/' + I.fen.cle;
      return orig.call(this, p, o);
    };
    U.ecrire.__etiqImpression = true;
  }
  function ecrireAdresse() {
    // La page réécrit son adresse à chaque changement du DOM (mysifa_tools.js) ;
    // hors MyTools, on écrit nous-mêmes en gardant la query existante.
    if (window.toolsSyncUrl) { try { window.toolsSyncUrl(); return; } catch (e) {} }
    if (!window.MySifaUrl) return;
    const sp = new URLSearchParams(location.search);
    const p = {};
    sp.forEach((v, k) => { if (!CLES.includes(k)) p[k] = v; });
    try { MySifaUrl.ecrire(p, {}); } catch (e) {}
  }
  function demarrerAdresse() {
    envelopper();
    const a = lireAdresse();
    if (Object.keys(a).length) setTimeout(() => adresseAller(a), 400);
    if (window.MySifaUrl && MySifaUrl.surRetour) MySifaUrl.surRetour(async () => { await adresseAller(lireAdresse()); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrerAdresse);
  else demarrerAdresse();

  // Barre d'accès aux écrans de la chaîne d'impression, à poser par le module
  // Étiquettes (grille des postes, outils) : Journal, Parc, Profils, Automatique, Kiosque.
  function barreOutils() {
    const M = window.MySifaEtiqImpression;
    const bar = h('div', { cls: 'eqi-ligne eqi-barre-outils' },
      bouton('Journal', 'Journal', () => M.ouvrirJournal(), null, 'list'),
      M.ouvrirParc ? bouton('Parc', 'Parc', () => M.ouvrirParc(), null, 'activity') : null,
      M.kiosque ? bouton('Kiosque', 'Atelier', () => M.kiosque.ouvrir(), null, 'printer') : null);
    charger().then(() => {
      if (!I.admin) return;
      bar.append(...[bouton('Profils', 'Profils', () => M.ouvrirProfils('liste'), null, 'settings'),
        M.ouvrirRegles ? bouton('Automatique', 'Règles', () => M.ouvrirRegles('liste'), null, 'repeat') : null].filter(Boolean));
    }).catch(() => {});
    return bar;
  }

  window.MySifaEtiqImpression = {
    barreOutils,
    imprimer: o => sessionImpression(Object.assign({ titre: (o && o.titre) || ('Imprimer · ' + ((o && o.modele && o.modele.nom) || 'étiquette')) }, o || {})),
    imprimerRendu, choisirImprimante, ouvrirJournal, ouvrirProfils, verifier,
    profils: async () => { await charger(); return I.profils.slice(); },
    surChange: fn => { if (typeof fn === 'function') I.ecoute.push(fn); },
    adresse: { etat: adresseEtat, aller: adresseAller, cles: CLES },
    _: { I, api, h, ic, bouton, fenetre, champ, toast, charger, livrer, blocVerification, rendreEtat, badgeStatut, selectProfils,
      ouvrirAdressable, fermerAdressable, signaler, CLES, sessionImpression },
  };
})();
