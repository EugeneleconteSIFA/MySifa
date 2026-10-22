/*
 * MyTools — Parapheur : envoyer un PDF à signer, suivre, signer.
 *
 * Contrat de montage (chargé à la demande par static/mysifa_tools.js) :
 *   window.MyToolsParapheurModule.mount(root, ctx)   ctx = {toast, surChange}
 *   window.MyToolsParapheurModule.demonter()
 *   window.MyToolsParapheurModule.adresse = {etat(), aller(a, complet), creation(), ouvrirCreation(), fermerCreation()}
 * API publique, appelée par l'Éditeur PDF (« Envoyer à signer ») :
 *   window.MyToolsParapheur.ouvrir({octets: Uint8Array, nom: string})
 *     ouvre la fenêtre de création par-dessus l'outil courant, document chargé.
 *
 * Adresse (écrite par mysifa_tools.js) : `statut` (filtre de la liste, défaut
 * en_cours), `demande=<id>` (demande ouverte), `signer=1` (fenêtre de
 * signature de la demande ouverte), `parapheur=nouvelle` (fenêtre de création,
 * valable sur tout outil : le document, lui, ne tient pas dans l'adresse et
 * se redemande au rechargement).
 * Hors adresse : recherche de signataires, confirmations (annuler, refuser).
 *
 * Bloc liste sans `data-bloc` : MyTools n'a ni appli dans le registre des
 * blocs ni icône dans mysifa_accueil.js, et la liste est personnelle (on n'y
 * voit que ses demandes et celles à signer) — elle irait en NON_RELEVES.
 * À ajouter avec l'appli « tools » du registre.
 *
 * Noyau de signature partagé avec l'Espace SIFA : static/mysifa_parapheur_signer.js.
 */
(function () {
  'use strict';

  var API = '/api/tools/parapheur';
  var BOOT = window.__MYTOOLS__ || { droits: {} };
  var FILTRES = [['a_signer', 'À signer'], ['en_cours', 'En cours'], ['signee', 'Signées'], ['refusee', 'Refusées'],
                 ['expiree', 'Expirées'], ['annulee', 'Annulées'], ['toutes', 'Toutes']];
  var STATUT_D = { en_cours: ['En cours', 'attente'], signee: ['Signée', 'ok'], refusee: ['Refusée', 'ko'],
                   expiree: ['Expirée', 'neutre'], annulee: ['Annulée', 'neutre'] };
  var STATUT_S = { attente: ['En attente', 'neutre'], a_signer: ['À signer', 'attente'], ouvert: ['Consulté', 'attente'],
                   signe: ['Signé', 'ok'], refuse: ['Refusé', 'ko'], expire: ['Expiré', 'neutre'], annule: ['Annulé', 'neutre'] };
  var TEINTES = ['var(--accent)', 'var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--success)', 'var(--warn)'];
  // Taille par défaut d'une zone, en points de page.
  var TAILLES = { signature: [170, 56], paraphe: [64, 40], date: [90, 20], nom: [150, 20] };
  var IC = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    retour: '<path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/>',
    haut: '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
    bas: '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
    suppr: '<path d="M4.5 7h15"/><path d="M9.5 4h5"/><path d="M6.5 7l.9 12.5a1 1 0 0 0 1 .9h7.2a1 1 0 0 0 1-.9L17.5 7"/>',
    envoyer: '<path d="M4 12l16-8-6 16-2.5-6.5z"/><path d="M11.5 13.5L20 4"/>',
    relancer: '<path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v5h-5"/>',
    fichier: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    annuler: '<circle cx="12" cy="12" r="8.5"/><path d="M6 6l12 12"/>',
    fermer: '<path d="M6 6l12 12M18 6L6 18"/>',
    parapheur: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M8.5 16.5c1.4 0 1.9-3.5 3-3.5s-.1 3.3 1 3.3c.8 0 1.1-1.2 1.8-1.2.6 0 .5.9 1.2.9"/>'
  };
  function ico(n, t) {
    return '<svg width="' + (t || 16) + '" height="' + (t || 16) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (IC[n] || '') + '</svg>';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  }
  function dateFr(s, heure) {
    if (!s) return '';
    var p = String(s).slice(0, 10).split('-');
    var j = p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : String(s);
    return heure && String(s).length >= 16 ? j + ' ' + String(s).slice(11, 16) : j;
  }
  function badge(table, cle) { var b = table[cle] || [cle, 'neutre']; return '<span class="ppx-badge ppx-badge-' + b[1] + '">' + esc(b[0]) + '</span>'; }
  function teinte(i) { return TEINTES[i % TEINTES.length]; }

  var P = {
    root: null, ctx: null, filtre: 'en_cours', demandeId: null, detail: null, liste: null, compteurs: {},
    peutCreer: !!(BOOT.droits && BOOT.droits.parapheur_creer), signer: false, sigFen: null, creation: null, gen: 0
  };
  function toast(m, t) { if (P.ctx && P.ctx.toast) P.ctx.toast(m, t); else if (typeof window.showToast === 'function') window.showToast(m, t); }
  function surChange() { if (P.ctx && P.ctx.surChange) { try { P.ctx.surChange(); } catch (e) { /* adresse */ } } else if (typeof window.toolsSyncUrl === 'function') window.toolsSyncUrl(); }

  async function api(chemin, opts) {
    opts = opts || {};
    var r = await fetch(API + chemin, Object.assign({ credentials: 'include' }, opts));
    if (r.status === 401) { location.href = '/?next=' + encodeURIComponent(location.pathname + location.search); throw new Error('Session expirée.'); }
    if (opts.binaire && r.ok) return new Uint8Array(await r.arrayBuffer());
    var j = null; try { j = await r.json(); } catch (e) { /* vide */ }
    if (!r.ok) {
      var d = j && j.detail;
      throw new Error(typeof d === 'string' ? d : (d && d.message) || ('Erreur ' + r.status));
    }
    return j;
  }
  function json(corps) { return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps || {}) }; }

  // Le noyau de signature (pdf.js, pad) est un second fichier, chargé une fois.
  var _noyau = null;
  function noyau() {
    if (window.ParapheurCore) return Promise.resolve(window.ParapheurCore);
    if (!_noyau) {
      _noyau = new Promise(function (ok, ko) {
        var s = document.createElement('script');
        s.src = '/static/mysifa_parapheur_signer.js' + (BOOT.version ? '?v=' + encodeURIComponent(BOOT.version) : '');
        s.onload = function () { ok(window.ParapheurCore); };
        s.onerror = function () { _noyau = null; ko(new Error('Module de signature indisponible.')); };
        document.head.appendChild(s);
      });
    }
    return _noyau;
  }

  /* ── Liste ─────────────────────────────────────────────────────────── */
  async function chargerListe() {
    var g = ++P.gen;
    try {
      var r = await api('?statut=' + encodeURIComponent(P.filtre));
      if (g !== P.gen) return;
      P.liste = r.demandes; P.compteurs = r.compteurs || {}; P.peutCreer = !!r.peut_creer;
    } catch (e) { if (g === P.gen) { P.liste = []; toast(e.message, 'danger'); } }
    rendre();
  }

  function rendreListe(root) {
    var c = P.compteurs || {};
    var filtres = FILTRES.map(function (f) {
      var n = c[f[0]] || 0;
      return '<button type="button" class="ppx-filtre' + (P.filtre === f[0] ? ' actif' : '') + '" data-a="filtre" data-v="' + f[0] + '" data-bulle="' + esc(f[1]) + '">'
        + esc(f[1]) + (n ? ' <span class="ppx-nb' + (f[0] === 'a_signer' ? ' ppx-nb-fort' : '') + '">' + n + '</span>' : '') + '</button>';
    }).join('');
    var lignes;
    if (P.liste === null) lignes = '<div class="ppx-vide"><span class="ppx-spin"></span> Chargement…</div>';
    else if (!P.liste.length) lignes = '<div class="ppx-vide">' + (P.filtre === 'a_signer' ? 'Aucun document ne vous attend.' : 'Aucune demande.') + '</div>';
    else lignes = P.liste.map(function (d) {
      var ratio = d.nb ? Math.round(100 * d.nb_signes / d.nb) : 0;
      var attente = d.statut === 'en_cours' && d.en_attente_de && d.en_attente_de.length ? 'En attente de ' + d.en_attente_de.slice(0, 3).join(', ') + (d.en_attente_de.length > 3 ? '…' : '') : '';
      var sous = [d.nom_fichier, 'émise par ' + (d.cree_par_nom || '?') + ' le ' + dateFr(d.cree_le), d.statut === 'en_cours' && d.echeance ? 'échéance ' + dateFr(d.echeance) : ''].filter(Boolean).join(' · ');
      return '<button type="button" class="ppx-ligne" data-a="ouvrir" data-id="' + d.id + '" data-bulle="Ouvrir">'
        + '<span class="ppx-ligne-ic">' + ico('parapheur', 20) + '</span>'
        + '<span class="ppx-ligne-txt"><span class="ppx-ligne-t">' + esc(d.titre) + '</span>'
        + '<span class="ppx-ligne-s">' + esc(sous) + '</span>'
        + (attente ? '<span class="ppx-ligne-s">' + esc(attente) + '</span>' : '') + '</span>'
        + '<span class="ppx-ligne-prog"><span class="ppx-prog"><span style="width:' + ratio + '%"></span></span><span class="ppx-prog-n">' + d.nb_signes + ' / ' + d.nb + '</span></span>'
        + (d.a_signer ? '<span class="ppx-badge ppx-badge-fort">À vous de signer</span>' : badge(STATUT_D, d.statut))
        + '</button>';
    }).join('');
    root.innerHTML = '<div class="ppx-ecran">'
      + '<div class="ppx-entete"><div><h1>' + ico('parapheur', 24) + 'Parapheur</h1><p>Envoyer un PDF à signer, dans un ordre défini, et suivre les signatures.</p></div>'
      + (P.peutCreer ? '<button type="button" class="ppx-btn ppx-btn-plein" data-a="nouvelle" data-bulle="Nouvelle">' + ico('plus') + 'Nouvelle demande</button>' : '')
      + '</div><div class="ppx-filtres" role="tablist">' + filtres + '</div>'
      + '<div class="ppx-liste">' + lignes + '</div></div>';
  }

  /* ── Détail ────────────────────────────────────────────────────────── */
  async function chargerDetail(id) {
    var g = ++P.gen;
    P.detail = null;
    rendre();
    try {
      var d = await api('/' + id);
      if (g !== P.gen || P.demandeId !== id) return;
      P.detail = d;
    } catch (e) {
      if (g !== P.gen) return;
      toast(e.message, 'danger');
      P.demandeId = null; P.signer = false;
      chargerListe();
      return;
    }
    rendre();
    if (P.signer) ouvrirSignature(true);
  }

  function rendreDetail(root) {
    var x = P.detail;
    if (!x) { root.innerHTML = '<div class="ppx-ecran"><div class="ppx-vide"><span class="ppx-spin"></span> Chargement…</div></div>'; return; }
    var d = x.demande, gere = x.droits && x.droits.gerer;
    var actions = '';
    if (x.moi && x.moi.peut_signer) actions += '<button type="button" class="ppx-btn ppx-btn-plein" data-a="signer" data-bulle="Signer">Signer le document</button>';
    actions += '<a class="ppx-btn" href="' + API + '/' + d.id + '/document" data-bulle="Original">' + ico('fichier') + 'Original</a>';
    if (d.final_disponible) actions += '<a class="ppx-btn ppx-btn-accent-l" href="' + API + '/' + d.id + '/final" data-bulle="Télécharger">' + ico('fichier') + 'Document signé</a>';
    if (gere) actions += '<button type="button" class="ppx-btn ppx-btn-danger-l" data-a="annuler" data-bulle="Annuler">' + ico('annuler') + 'Annuler</button>';
    var meta = [
      ['Document', d.nom_fichier + ' · ' + d.nb_pages + ' page' + (d.nb_pages > 1 ? 's' : '')],
      ['Ordre', d.mode === 'sequentiel' ? 'Séquentiel — un signataire après l\'autre' : 'Parallèle — tous en même temps'],
      ['Émise par', (d.cree_par_nom || '') + ' le ' + dateFr(d.cree_le, true)],
      ['Échéance', dateFr(d.echeance)],
      ['Relance', d.relance_jours ? 'tous les ' + d.relance_jours + ' jour' + (d.relance_jours > 1 ? 's' : '') : 'aucune']
    ];
    if (d.termine_le) meta.push(['Terminée le', dateFr(d.termine_le, true)]);
    if (d.motif_fin) meta.push(['Motif', d.motif_fin]);
    var sigs = x.signataires.map(function (s, i) {
      var dates = [];
      if (s.notifie_le) dates.push('prévenu le ' + dateFr(s.notifie_le, true));
      if (s.ouvert_le) dates.push('consulté le ' + dateFr(s.ouvert_le, true));
      if (s.signe_le) dates.push('signé le ' + dateFr(s.signe_le, true));
      if (s.refuse_le) dates.push('refusé le ' + dateFr(s.refuse_le, true));
      if (s.nb_relances) dates.push(s.nb_relances + ' relance' + (s.nb_relances > 1 ? 's' : ''));
      var peutRel = gere && d.statut === 'en_cours' && (s.statut === 'a_signer' || s.statut === 'ouvert');
      return '<div class="ppx-sig-ligne" style="--zc:' + teinte(i) + '">'
        + '<span class="ppx-sig-ordre">' + s.ordre + '</span>'
        + '<span class="ppx-sig-txt"><span class="ppx-sig-nom">' + esc(s.nom || s.email) + ' <span class="ppx-type">' + (s.type === 'interne' ? 'Interne' : 'Espace') + '</span></span>'
        + '<span class="ppx-sig-s">' + esc([s.organisation, s.email].filter(Boolean).join(' · ')) + '</span>'
        + (dates.length ? '<span class="ppx-sig-s">' + esc(dates.join(' · ')) + '</span>' : '')
        + (s.motif_refus ? '<span class="ppx-sig-s ppx-ko">Motif : ' + esc(s.motif_refus) + '</span>' : '')
        + (s.ip && s.signe_le ? '<span class="ppx-sig-s">IP ' + esc(s.ip) + '</span>' : '') + '</span>'
        + badge(STATUT_S, s.statut)
        + (peutRel ? '<button type="button" class="ppx-btn ppx-btn-sm" data-a="relancer" data-id="' + s.id + '" data-bulle="Relancer">' + ico('relancer', 14) + 'Relancer</button>' : '')
        + '</div>';
    }).join('');
    var empreintes = '<div class="ppx-carte"><div class="ppx-carte-t">Empreintes SHA-256</div>'
      + '<div class="ppx-kv"><span>Document d\'origine</span><code>' + esc(d.sha256_original) + '</code></div>'
      + (d.sha256_signe ? '<div class="ppx-kv"><span>Document signé (hors certificat)</span><code>' + esc(d.sha256_signe) + '</code></div>' : '')
      + (d.sha256_final ? '<div class="ppx-kv"><span>Fichier final complet</span><code>' + esc(d.sha256_final) + '</code></div>' : '')
      + '</div>';
    var hist = (x.evenements || []).slice().reverse().map(function (e) {
      return '<div class="ppx-ev"><span class="ppx-ev-d">' + esc(dateFr(e.le, true)) + '</span><span class="ppx-ev-t">' + esc(e.libelle)
        + '</span><span class="ppx-ev-x">' + esc([e.acteur, e.detail, e.ip ? 'IP ' + e.ip : ''].filter(Boolean).join(' · ')) + '</span></div>';
    }).join('');
    root.innerHTML = '<div class="ppx-ecran">'
      + '<button type="button" class="ppx-retour" data-a="retour" data-bulle="Liste">' + ico('retour') + 'Parapheur</button>'
      + '<div class="ppx-entete"><div><h1>' + esc(d.titre) + ' ' + badge(STATUT_D, d.statut) + '</h1>'
      + (d.message ? '<p class="ppx-message"></p>' : '') + '</div><div class="ppx-actions">' + actions + '</div></div>'
      + '<div class="ppx-grille"><div class="ppx-carte"><div class="ppx-carte-t">Signataires</div>' + sigs + '</div>'
      + '<div class="ppx-col"><div class="ppx-carte">' + meta.map(function (m) { return '<div class="ppx-kv"><span>' + esc(m[0]) + '</span><b>' + esc(m[1]) + '</b></div>'; }).join('') + '</div>'
      + empreintes + '</div></div>'
      + (hist ? '<div class="ppx-carte"><div class="ppx-carte-t">Historique</div>' + hist + '</div>' : '')
      + '</div>';
    if (d.message) root.querySelector('.ppx-message').textContent = d.message;
  }

  /* ── Fenêtre de signature (signataire interne) ─────────────────────── */
  function fermerSignature(sansAdresse) {
    if (P.sigFen) { P.sigFen.remove(); P.sigFen = null; }
    if (P.signer) { P.signer = false; if (sansAdresse !== true) surChange(); }
  }
  async function ouvrirSignature(depuisAdresse) {
    var x = P.detail;
    if (!x || !x.moi || !x.moi.peut_signer) { P.signer = false; if (depuisAdresse) surChange(); return; }
    if (P.sigFen) return;
    P.signer = true;
    var fen = document.createElement('div');
    fen.className = 'ppx-fenetre';
    fen.innerHTML = '<div class="ppx-fen-hd"><div class="ppx-fen-t">Signer le document</div>'
      + '<button type="button" class="ppx-x" data-bulle="Fermer" aria-label="Fermer">' + ico('fermer') + '</button></div>'
      + '<div class="ppx-fen-corps ppx-fen-sig"><div class="ppx-vide"><span class="ppx-spin"></span> Chargement…</div></div>';
    document.body.appendChild(fen);
    P.sigFen = fen;
    fen.querySelector('.ppx-x').addEventListener('click', function () { fermerSignature(); });
    surChange();
    var corps = fen.querySelector('.ppx-fen-corps');
    try {
      var C = await noyau();
      var res = await Promise.all([api('/' + x.demande.id + '/document', { binaire: true }), api('/ma-signature').catch(function () { return {}; })]);
      api('/' + x.demande.id + '/ouvrir', { method: 'POST' }).catch(function () {});
      if (P.sigFen !== fen) return;
      var d = x.demande, sid = x.moi.signataire_id;
      var mes = x.zones.filter(function (z) { return z.signataire_id === sid; });
      var user = (P.ctx && P.ctx.user) || BOOT.user || {};
      C.vueSignature(corps, {
        octets: res[0], zones: mes, nom: user.nom || '', titre: d.titre, message: d.message,
        detail: d.nom_fichier + ' · envoyé par ' + (d.cree_par_nom || '') + (d.echeance ? ' · à signer avant le ' + dateFr(d.echeance) : ''),
        circuit: x.signataires.map(function (s) { return { ordre: s.ordre, nom: s.nom || s.email, statut: s.statut, moi: s.id === sid }; }),
        reutilisables: C.signaturesReutilisables(res[1] && res[1].signature),
        consentement: "J'ai lu le document et je le signe. Mon nom, la date et mon adresse IP figureront sur le certificat de signature.",
        toast: toast,
        surSigner: async function (data) {
          var r = await api('/' + d.id + '/signer', json(data));
          toast(r.termine ? 'Signature enregistrée — document scellé.' : 'Signature enregistrée.', 'success');
          fermerSignature();
          chargerDetail(d.id);
        },
        surRefuser: async function (motif) {
          await api('/' + d.id + '/refuser', json({ motif: motif }));
          toast('Refus enregistré.', 'success');
          fermerSignature();
          chargerDetail(d.id);
        }
      });
    } catch (e) {
      corps.innerHTML = '<div class="ppx-vide"></div>';
      corps.firstChild.textContent = e.message || 'Document indisponible.';
    }
  }

  /* ── Fenêtre de création ───────────────────────────────────────────── */
  function nouvelleCreation(fichier) {
    var ech = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
    return { octets: fichier ? fichier.octets : null, nom: fichier ? (fichier.nom || 'document.pdf') : '', titre: fichier ? String(fichier.nom || '').replace(/\.pdf$/i, '') : '',
             message: '', mode: 'sequentiel', echeance: ech, relance: 3, signataires: [], zones: [], actif: 0, pages: [],
             type: 'interne', q: '', resultats: [], outil: null, envoi: false, el: null, seq: 0 };
  }

  function ouvrirCreation(fichier, sansAdresse) {
    if (P.creation) {
      if (fichier) { P.creation.octets = fichier.octets; P.creation.nom = fichier.nom || 'document.pdf'; P.creation.zones = []; rendreCreation(); }
      return;
    }
    P.creation = nouvelleCreation(fichier);
    var fen = document.createElement('div');
    fen.className = 'ppx-fenetre';
    P.creation.el = fen;
    document.body.appendChild(fen);
    rendreCreation();
    if (sansAdresse !== true) surChange();
  }
  function fermerCreation(sansAdresse) {
    if (!P.creation) return;
    if (P.creation.el) P.creation.el.remove();
    P.creation = null;
    document.removeEventListener('keydown', clavierCreation);
    if (sansAdresse !== true) surChange();
  }
  function clavierCreation(ev) {
    if (ev.key === 'Escape' && P.creation && !document.querySelector('.ppx-modale-fond')) {
      var a = document.activeElement;
      if (a && /INPUT|TEXTAREA|SELECT/.test(a.tagName)) { a.blur(); return; }
      fermerCreation();
    }
  }

  function rendreCreation() {
    var C = P.creation; if (!C) return;
    var fen = C.el;
    document.removeEventListener('keydown', clavierCreation);
    document.addEventListener('keydown', clavierCreation);
    fen.innerHTML = '<div class="ppx-fen-hd"><div class="ppx-fen-t">Nouvelle demande de signature</div>'
      + '<button type="button" class="ppx-btn ppx-btn-plein" data-c="envoyer" data-bulle="Envoyer">' + ico('envoyer') + 'Envoyer</button>'
      + '<button type="button" class="ppx-x" data-c="fermer" data-bulle="Fermer" aria-label="Fermer">' + ico('fermer') + '</button></div>'
      + '<div class="ppx-fen-corps ppx-creation"><aside class="ppx-cr-form"></aside><section class="ppx-cr-doc"></section></div>';
    fen.querySelector('[data-c="fermer"]').addEventListener('click', function () { fermerCreation(); });
    fen.querySelector('[data-c="envoyer"]').addEventListener('click', function (ev) { envoyer(ev.currentTarget); });
    rendreFormulaire();
    rendreDocument();
  }

  function rendreFormulaire() {
    var C = P.creation, f = C.el.querySelector('.ppx-cr-form');
    f.innerHTML = '<div class="ppx-cr-sec">Document</div>'
      + '<div class="ppx-cr-fichier"><span>' + ico('fichier') + '<b></b></span><label class="ppx-btn ppx-btn-sm" data-bulle="Changer">Changer<input type="file" accept="application/pdf,.pdf" hidden></label></div>'
      + '<label class="ppx-lab">Titre<input class="ppx-champ" data-k="titre" maxlength="200"></label>'
      + '<label class="ppx-lab">Message aux signataires<textarea class="ppx-champ" data-k="message" rows="3" maxlength="3000"></textarea></label>'
      + '<div class="ppx-lab">Ordre de signature<div class="ppx-seg">'
      + '<button type="button" data-mode="sequentiel" data-bulle="Séquentiel">Un par un, dans l\'ordre</button>'
      + '<button type="button" data-mode="parallele" data-bulle="Parallèle">Tous en même temps</button></div></div>'
      + '<div class="ppx-deux"><label class="ppx-lab">Échéance<input class="ppx-champ" type="date" data-k="echeance"></label>'
      + '<label class="ppx-lab">Relance auto.<select class="ppx-champ" data-k="relance">'
      + [[0, 'Aucune'], [1, 'Chaque jour'], [2, 'Tous les 2 jours'], [3, 'Tous les 3 jours'], [5, 'Tous les 5 jours'], [7, 'Chaque semaine']].map(function (o) { return '<option value="' + o[0] + '">' + o[1] + '</option>'; }).join('')
      + '</select></label></div>'
      + '<div class="ppx-cr-sec">Signataires</div><div class="ppx-cr-sigs"></div>'
      + '<div class="ppx-cr-ajout"><div class="ppx-seg ppx-seg-sm">'
      + [['interne', 'Interne'], ['fournisseur', 'Fournisseur'], ['client', 'Client'], ['libre', 'Adresse']].map(function (t) { return '<button type="button" data-type="' + t[0] + '" data-bulle="' + t[1] + '">' + t[1] + '</button>'; }).join('')
      + '</div><div class="ppx-cr-recherche"></div></div>';
    f.querySelector('.ppx-cr-fichier b').textContent = C.nom || 'Aucun fichier';
    f.querySelector('input[type=file]').addEventListener('change', function (ev) { lireFichier(ev.target.files && ev.target.files[0]); });
    f.querySelectorAll('[data-k]').forEach(function (i) {
      var k = i.getAttribute('data-k');
      i.value = C[k] == null ? '' : C[k];
      i.addEventListener('input', function () { C[k] = k === 'relance' ? Number(i.value) : i.value; });
      i.addEventListener('change', function () { C[k] = k === 'relance' ? Number(i.value) : i.value; });
    });
    f.querySelectorAll('[data-mode]').forEach(function (b) {
      b.classList.toggle('actif', b.getAttribute('data-mode') === C.mode);
      b.addEventListener('click', function () { C.mode = b.getAttribute('data-mode'); rendreFormulaire(); });
    });
    f.querySelectorAll('[data-type]').forEach(function (b) {
      b.classList.toggle('actif', b.getAttribute('data-type') === C.type);
      b.addEventListener('click', function () { C.type = b.getAttribute('data-type'); C.q = ''; C.resultats = []; rendreFormulaire(); });
    });
    rendreSignataires();
    rendreRecherche();
  }

  function rendreSignataires() {
    var C = P.creation, box = C.el.querySelector('.ppx-cr-sigs');
    if (!C.signataires.length) { box.innerHTML = '<div class="ppx-aide">Ajouter les signataires ci-dessous, puis placer leurs zones sur le document.</div>'; return; }
    box.innerHTML = C.signataires.map(function (s, i) {
      var n = C.zones.filter(function (z) { return z.signataire === i; });
      var nSig = n.filter(function (z) { return z.type === 'signature'; }).length;
      return '<div class="ppx-cr-sig' + (i === C.actif ? ' actif' : '') + '" style="--zc:' + teinte(i) + '" data-i="' + i + '">'
        + '<button type="button" class="ppx-cr-sig-main" data-s="choisir" data-bulle="Placer">'
        + '<span class="ppx-pastille"></span><span class="ppx-cr-sig-n">' + (C.mode === 'sequentiel' ? (i + 1) + '. ' : '') + esc(s.nom || s.email) + '</span>'
        + '<span class="ppx-cr-sig-s">' + esc([s.type === 'interne' ? 'Interne' : 'Espace', s.organisation, s.email].filter(Boolean).join(' · ')) + '</span>'
        + '<span class="ppx-cr-sig-z' + (nSig ? '' : ' ppx-ko') + '">' + (n.length ? n.length + ' zone' + (n.length > 1 ? 's' : '') : 'aucune zone') + (nSig ? '' : ' — signature à placer') + '</span></button>'
        + '<span class="ppx-cr-sig-act">'
        + (i > 0 ? '<button type="button" class="ppx-mini" data-s="haut" data-bulle="Monter" aria-label="Monter">' + ico('haut', 14) + '</button>' : '')
        + (i < C.signataires.length - 1 ? '<button type="button" class="ppx-mini" data-s="bas" data-bulle="Descendre" aria-label="Descendre">' + ico('bas', 14) + '</button>' : '')
        + '<button type="button" class="ppx-mini" data-s="suppr" data-bulle="Retirer" aria-label="Retirer">' + ico('suppr', 14) + '</button></span></div>';
    }).join('');
    box.querySelectorAll('[data-s]').forEach(function (b) {
      b.addEventListener('click', function () {
        var i = Number(b.closest('[data-i]').getAttribute('data-i')), a = b.getAttribute('data-s');
        if (a === 'choisir') C.actif = i;
        else if (a === 'suppr') {
          C.signataires.splice(i, 1);
          C.zones = C.zones.filter(function (z) { return z.signataire !== i; }).map(function (z) { if (z.signataire > i) z.signataire--; return z; });
          C.actif = Math.max(0, Math.min(C.actif, C.signataires.length - 1));
        } else {
          var j = a === 'haut' ? i - 1 : i + 1;
          var t = C.signataires[i]; C.signataires[i] = C.signataires[j]; C.signataires[j] = t;
          C.zones.forEach(function (z) { if (z.signataire === i) z.signataire = j; else if (z.signataire === j) z.signataire = i; });
          if (C.actif === i) C.actif = j; else if (C.actif === j) C.actif = i;
        }
        rendreSignataires(); rendreZones(); rendrePalette();
      });
    });
  }

  var _rech = 0;
  function rendreRecherche() {
    var C = P.creation, box = C.el.querySelector('.ppx-cr-recherche');
    if (C.type === 'libre') {
      box.innerHTML = '<input class="ppx-champ" data-l="nom" placeholder="Nom et prénom" maxlength="200">'
        + '<input class="ppx-champ" data-l="email" type="email" placeholder="Adresse email" maxlength="254">'
        + '<input class="ppx-champ" data-l="organisation" placeholder="Société (facultatif)" maxlength="200">'
        + '<button type="button" class="ppx-btn ppx-btn-sm" data-bulle="Ajouter">' + ico('plus', 14) + 'Ajouter</button>';
      box.querySelector('button').addEventListener('click', function () {
        var v = {}; box.querySelectorAll('[data-l]').forEach(function (i) { v[i.getAttribute('data-l')] = i.value.trim(); });
        if (!v.nom) { toast('Nom obligatoire — il figure sur le certificat.', 'danger'); return; }
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email)) { toast('Adresse email invalide.', 'danger'); return; }
        ajouter({ type: 'externe', nom: v.nom, email: v.email.toLowerCase(), organisation: v.organisation });
        box.querySelectorAll('[data-l]').forEach(function (i) { i.value = ''; });
      });
      return;
    }
    box.innerHTML = '<input class="ppx-champ" id="ppx-cr-q" placeholder="' + (C.type === 'interne' ? 'Rechercher (nom, email)' : 'Rechercher (société, contact, email)') + '" autocomplete="off">'
      + '<div class="ppx-cr-res"></div>';
    var inp = box.querySelector('input'), res = box.querySelector('.ppx-cr-res');
    inp.value = C.q;
    function afficher() {
      var deja = C.signataires.map(function (s) { return s.type === 'interne' ? 'u' + s.user_id : s.email; });
      var l = C.resultats.filter(function (r) { return deja.indexOf(r.type === 'interne' ? 'u' + r.user_id : r.email) === -1; }).slice(0, 8);
      res.innerHTML = l.length ? l.map(function (r, k) {
        return '<button type="button" class="ppx-cr-r" data-k="' + k + '" data-bulle="Ajouter"><b>' + esc(r.nom || r.email) + '</b><span>' + esc([r.organisation, r.email].filter(Boolean).join(' · ')) + '</span></button>';
      }).join('') : (C.q ? '<div class="ppx-aide">Aucun résultat pour « ' + esc(C.q) + ' »</div>' : '');
      res.querySelectorAll('[data-k]').forEach(function (b) {
        b.addEventListener('click', function () {
          var r = l[Number(b.getAttribute('data-k'))];
          if (r.type === 'externe' && !r.nom) {
            var nom = (r.organisation || r.email.split('@')[0]);
            r = Object.assign({}, r, { nom: nom });
          }
          ajouter(r);
        });
      });
    }
    async function chercher() {
      var n = ++_rech;
      try {
        var r = await api('/candidats?type=' + encodeURIComponent(C.type) + '&q=' + encodeURIComponent(C.q));
        if (n !== _rech || !P.creation) return;
        C.resultats = r.candidats || [];
      } catch (e) { C.resultats = []; toast(e.message, 'danger'); }
      afficher();
    }
    var t = 0;
    inp.addEventListener('input', function () { C.q = inp.value.trim(); clearTimeout(t); t = setTimeout(chercher, 180); });
    inp.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { ev.stopPropagation(); inp.value = ''; C.q = ''; chercher(); } });
    if (C.resultats.length) afficher(); else chercher();
  }

  function ajouter(s) {
    var C = P.creation;
    if (C.signataires.length >= 20) { toast('20 signataires au plus.', 'danger'); return; }
    C.signataires.push({ type: s.type, user_id: s.user_id, nom: s.nom || '', email: s.email || '', organisation: s.organisation || '' });
    C.actif = C.signataires.length - 1;
    rendreSignataires(); rendrePalette(); rendreRecherche();
  }

  function lireFichier(f) {
    if (!f) return;
    if (!/\.pdf$/i.test(f.name) && f.type !== 'application/pdf') { toast('Fichier PDF attendu.', 'danger'); return; }
    var r = new FileReader();
    r.onload = function () {
      var C = P.creation; if (!C) return;
      C.octets = new Uint8Array(r.result); C.nom = f.name; C.zones = [];
      if (!C.titre) C.titre = f.name.replace(/\.pdf$/i, '');
      rendreFormulaire(); rendreDocument();
    };
    r.onerror = function () { toast('Fichier illisible.', 'danger'); };
    r.readAsArrayBuffer(f);
  }

  function rendreDocument() {
    var C = P.creation, sec = C.el.querySelector('.ppx-cr-doc');
    if (!C.octets) {
      sec.innerHTML = '<label class="ppx-depot" data-bulle="Choisir">' + ico('fichier', 32)
        + '<b>Choisir le PDF à faire signer</b><span>ou le déposer ici</span><input type="file" accept="application/pdf,.pdf" hidden></label>';
      var dep = sec.querySelector('.ppx-depot');
      dep.querySelector('input').addEventListener('change', function (ev) { lireFichier(ev.target.files && ev.target.files[0]); });
      dep.addEventListener('dragover', function (ev) { ev.preventDefault(); dep.classList.add('survol'); });
      dep.addEventListener('dragleave', function () { dep.classList.remove('survol'); });
      dep.addEventListener('drop', function (ev) { ev.preventDefault(); dep.classList.remove('survol'); lireFichier(ev.dataTransfer.files && ev.dataTransfer.files[0]); });
      return;
    }
    sec.innerHTML = '<div class="ppx-palette"></div><div class="ppx-docs"><div class="ppx-vide"><span class="ppx-spin"></span> Chargement du document…</div></div>';
    rendrePalette();
    var seq = ++C.seq;
    noyau().then(function (K) { return K.rendrePages(sec.querySelector('.ppx-docs'), C.octets, { largeur: Math.min(900, sec.clientWidth - 24) }); })
      .then(function (pages) {
        if (!P.creation || P.creation !== C || seq !== C.seq) return;
        C.pages = pages;
        pages.forEach(function (p) { brancherPage(p); });
        rendreZones();
      })
      .catch(function (e) { var d = sec.querySelector('.ppx-docs'); if (d) { d.innerHTML = '<div class="ppx-vide"></div>'; d.firstChild.textContent = e.message || 'PDF illisible.'; } });
  }

  function rendrePalette() {
    var C = P.creation; if (!C) return;
    var pal = C.el.querySelector('.ppx-palette'); if (!pal) return;
    var s = C.signataires[C.actif];
    if (!s) { pal.innerHTML = '<span class="ppx-aide">Ajouter un signataire pour placer ses zones.</span>'; return; }
    pal.style.setProperty('--zc', teinte(C.actif));
    pal.innerHTML = '<span class="ppx-pal-qui"><span class="ppx-pastille"></span>Zones de ' + esc(s.nom || s.email) + '</span>'
      + ['signature', 'paraphe', 'date', 'nom'].map(function (t) {
        return '<button type="button" class="ppx-puce' + (C.outil === t ? ' actif' : '') + '" data-t="' + t + '" data-bulle="Glisser">' + esc(window.ParapheurCore ? window.ParapheurCore.LIB_ZONE[t] : t) + '</button>';
      }).join('')
      + '<span class="ppx-aide">Glisser sur la page, ou cliquer puis cliquer sur la page.</span>';
    pal.querySelectorAll('[data-t]').forEach(function (b) {
      b.addEventListener('pointerdown', function (ev) { debutGlisser(ev, b.getAttribute('data-t')); });
    });
  }

  // Glisser une puce de la palette sur une page ; un simple clic arme l'outil.
  function debutGlisser(ev, type) {
    var C = P.creation; if (!C || !C.signataires.length) return;
    ev.preventDefault();
    var x0 = ev.clientX, y0 = ev.clientY, fant = null;
    function bouger(e) {
      if (!fant && Math.hypot(e.clientX - x0, e.clientY - y0) > 6) {
        fant = document.createElement('div');
        fant.className = 'ppx-fantome';
        fant.style.setProperty('--zc', teinte(C.actif));
        fant.textContent = window.ParapheurCore.LIB_ZONE[type];
        document.body.appendChild(fant);
      }
      if (fant) { fant.style.left = e.clientX + 'px'; fant.style.top = e.clientY + 'px'; }
    }
    function lacher(e) {
      document.removeEventListener('pointermove', bouger);
      document.removeEventListener('pointerup', lacher);
      if (!fant) { C.outil = C.outil === type ? null : type; rendrePalette(); return; }
      fant.remove();
      var cible = document.elementFromPoint(e.clientX, e.clientY);
      var pg = cible && cible.closest && cible.closest('.ppx-page');
      if (pg && C.el.contains(pg)) poserZone(Number(pg.getAttribute('data-page')), type, e.clientX, e.clientY);
    }
    document.addEventListener('pointermove', bouger);
    document.addEventListener('pointerup', lacher);
  }

  function brancherPage(p) {
    p.calque.addEventListener('click', function (ev) {
      var C = P.creation;
      if (!C || !C.outil || ev.target !== p.calque) return;
      poserZone(p.num, C.outil, ev.clientX, ev.clientY);
      C.outil = null; rendrePalette();
    });
  }

  function poserZone(page, type, cx, cy) {
    var C = P.creation, p = C.pages[page - 1]; if (!p) return;
    var r = p.calque.getBoundingClientRect();
    var t = TAILLES[type], w = Math.min(0.9, t[0] / p.w), h = Math.min(0.5, t[1] / p.h);
    var x = (cx - r.left) / r.width - w / 2, y = (cy - r.top) / r.height - h / 2;
    C.zones.push({ signataire: C.actif, page: page, type: type, w: w, h: h,
                   x: Math.max(0, Math.min(1 - w, x)), y: Math.max(0, Math.min(1 - h, y)) });
    rendreZones(); rendreSignataires();
  }

  function rendreZones() {
    var C = P.creation; if (!C || !C.pages.length) return;
    C.pages.forEach(function (p) { p.calque.querySelectorAll('.ppx-zone').forEach(function (z) { z.remove(); }); });
    C.zones.forEach(function (z, k) {
      var p = C.pages[z.page - 1]; if (!p) return;
      var s = C.signataires[z.signataire] || {};
      var e = document.createElement('div');
      e.className = 'ppx-zone ppx-zone-' + z.type + (z.signataire === C.actif ? ' ppx-zone-active' : '');
      e.style.setProperty('--zc', teinte(z.signataire));
      e.style.left = (z.x * 100) + '%'; e.style.top = (z.y * 100) + '%';
      e.style.width = (z.w * 100) + '%'; e.style.height = (z.h * 100) + '%';
      e.innerHTML = '<span class="ppx-zone-lib"></span><button type="button" class="ppx-zone-x" data-bulle="Retirer" aria-label="Retirer la zone">' + ico('fermer', 12) + '</button><span class="ppx-zone-poignee" data-bulle="Taille"></span>';
      e.querySelector('.ppx-zone-lib').textContent = window.ParapheurCore.LIB_ZONE[z.type] + ' · ' + (s.nom || s.email || '');
      e.querySelector('.ppx-zone-x').addEventListener('click', function (ev) { ev.stopPropagation(); C.zones.splice(k, 1); rendreZones(); rendreSignataires(); });
      e.addEventListener('pointerdown', function (ev) { if (ev.target.closest('.ppx-zone-x')) return; manipuler(ev, z, e, p, ev.target.classList.contains('ppx-zone-poignee')); });
      p.calque.appendChild(e);
    });
  }

  function manipuler(ev, z, e, p, redim) {
    ev.preventDefault(); ev.stopPropagation();
    var r = p.calque.getBoundingClientRect(), x0 = ev.clientX, y0 = ev.clientY, z0 = { x: z.x, y: z.y, w: z.w, h: z.h };
    try { e.setPointerCapture(ev.pointerId); } catch (er) { /* ignoré */ }
    function bouger(m) {
      var dx = (m.clientX - x0) / r.width, dy = (m.clientY - y0) / r.height;
      if (redim) { z.w = Math.max(0.02, Math.min(1 - z.x, z0.w + dx)); z.h = Math.max(0.012, Math.min(1 - z.y, z0.h + dy)); }
      else { z.x = Math.max(0, Math.min(1 - z.w, z0.x + dx)); z.y = Math.max(0, Math.min(1 - z.h, z0.y + dy)); }
      e.style.left = (z.x * 100) + '%'; e.style.top = (z.y * 100) + '%'; e.style.width = (z.w * 100) + '%'; e.style.height = (z.h * 100) + '%';
    }
    function lacher() { e.removeEventListener('pointermove', bouger); e.removeEventListener('pointerup', lacher); e.removeEventListener('pointercancel', lacher); }
    e.addEventListener('pointermove', bouger); e.addEventListener('pointerup', lacher); e.addEventListener('pointercancel', lacher);
  }

  async function envoyer(btn) {
    var C = P.creation; if (!C || C.envoi) return;
    if (!C.octets) { toast('Choisir le PDF à faire signer.', 'danger'); return; }
    if (!String(C.titre || '').trim()) { toast('Titre obligatoire.', 'danger'); return; }
    if (!C.signataires.length) { toast('Ajouter au moins un signataire.', 'danger'); return; }
    var manque = C.signataires.findIndex(function (s, i) { return !C.zones.some(function (z) { return z.signataire === i && z.type === 'signature'; }); });
    if (manque !== -1) { C.actif = manque; rendreSignataires(); rendrePalette(); rendreZones(); toast('Placer une zone de signature pour ' + (C.signataires[manque].nom || C.signataires[manque].email) + '.', 'danger'); return; }
    var donnees = { titre: C.titre.trim(), message: C.message, mode: C.mode, echeance: C.echeance, relance_jours: C.relance,
                    signataires: C.signataires, zones: C.zones.map(function (z) { return { signataire: z.signataire, page: z.page, type: z.type, x: z.x, y: z.y, w: z.w, h: z.h }; }) };
    var fd = new FormData();
    fd.append('fichier', new Blob([C.octets], { type: 'application/pdf' }), C.nom || 'document.pdf');
    fd.append('donnees', JSON.stringify(donnees));
    C.envoi = true; btn.disabled = true; btn.lastChild.textContent = 'Envoi…';
    try {
      var r = await api('', { method: 'POST', body: fd });
      toast(r.echecs ? 'Demande créée — ' + r.echecs + ' invitation(s) non partie(s), à relancer.' : 'Demande envoyée.', r.echecs ? 'danger' : 'success');
      fermerCreation(true);
      if (typeof window.toolsAller === 'function' && window.S && window.S.outil !== 'parapheur') {
        window.__ppxApresMontage = { demande: r.id };
        window.toolsAller('parapheur');
      } else {
        P.demandeId = r.id; P.signer = false; chargerDetail(r.id); surChange();
      }
    } catch (e) {
      toast(e.message, 'danger');
      if (P.creation) { C.envoi = false; btn.disabled = false; btn.lastChild.textContent = 'Envoyer'; }
    }
  }

  /* ── Rendu, gestes ─────────────────────────────────────────────────── */
  function rendre() {
    if (!P.root || !P.root.isConnected) return;
    if (P.demandeId) rendreDetail(P.root); else rendreListe(P.root);
    surChange();
  }

  function clic(ev) {
    var b = ev.target.closest('[data-a]'); if (!b || !P.root.contains(b)) return;
    var a = b.getAttribute('data-a');
    if (a === 'filtre') { P.filtre = b.getAttribute('data-v'); P.liste = null; rendre(); chargerListe(); }
    else if (a === 'ouvrir') { P.demandeId = Number(b.getAttribute('data-id')); P.signer = false; chargerDetail(P.demandeId); }
    else if (a === 'retour') { P.demandeId = null; P.detail = null; P.liste = null; rendre(); chargerListe(); }
    else if (a === 'nouvelle') ouvrirCreation(null);
    else if (a === 'signer') ouvrirSignature(false);
    else if (a === 'relancer') relancer(Number(b.getAttribute('data-id')), b);
    else if (a === 'annuler') confirmerAnnulation();
  }

  async function relancer(sid, b) {
    b.disabled = true;
    try { await api('/' + P.demandeId + '/signataires/' + sid + '/relancer', { method: 'POST' }); toast('Relance envoyée.', 'success'); chargerDetail(P.demandeId); }
    catch (e) { toast(e.message, 'danger'); b.disabled = false; }
  }

  function confirmerAnnulation() {
    noyau().then(function (K) {
      var corps = document.createElement('div'); corps.className = 'ppx-modale-bd';
      corps.innerHTML = '<p class="ppx-aide">Les signataires qui n\'ont pas signé ne pourront plus le faire. Les signatures déjà posées restent dans l\'historique.</p>'
        + '<textarea class="ppx-champ" rows="3" maxlength="500" placeholder="Motif (facultatif)" aria-label="Motif"></textarea>';
      K.fenetre('Annuler la demande', corps, [
        { txt: 'Garder', fn: function (b, fermer) { fermer(); } },
        { txt: 'Annuler la demande', bulle: 'Annuler', danger: true, fn: async function (b, fermer) {
          b.disabled = true;
          try { await api('/' + P.demandeId + '/annuler', json({ motif: corps.querySelector('textarea').value })); fermer(); toast('Demande annulée.', 'success'); chargerDetail(P.demandeId); }
          catch (e) { toast(e.message, 'danger'); b.disabled = false; }
        } }
      ]);
    });
  }

  var M = {
    mount: function (root, ctx) {
      P.root = root; P.ctx = ctx || null;
      root.addEventListener('click', clic);
      var suite = window.__ppxApresMontage; window.__ppxApresMontage = null;
      if (suite && suite.demande) { P.demandeId = suite.demande; P.signer = false; }
      noyau().catch(function () {});
      if (P.demandeId) chargerDetail(P.demandeId); else { P.liste = null; rendre(); chargerListe(); }
    },
    demonter: function () {
      fermerSignature(true);
      if (P.root) P.root.removeEventListener('click', clic);
      P.root = null; P.demandeId = null; P.detail = null; P.liste = null; P.gen++;
    },
    ouvrir: function (f) {
      var fichier = f && f.octets ? { octets: f.octets instanceof Uint8Array ? f.octets : new Uint8Array(f.octets), nom: f.nom || 'document.pdf' } : null;
      return noyau().then(function () { ouvrirCreation(fichier); return true; });
    },
    adresse: {
      cles: ['statut', 'demande', 'signer', 'parapheur'],
      etat: function () { return { statut: P.filtre, demande: P.demandeId, signer: !!(P.demandeId && P.signer) }; },
      aller: function (a, complet) {
        a = a || {};
        var filtre = a.statut || 'en_cours';
        var id = a.demande ? Number(a.demande) : null;
        if (complet || a.statut) P.filtre = filtre;
        if (id !== P.demandeId) {
          fermerSignature(true);
          P.demandeId = id; P.signer = !!a.signer;
          if (!P.root) return;
          if (id) chargerDetail(id); else { P.liste = null; rendre(); chargerListe(); }
          return;
        }
        if (!id && P.root && (complet || a.statut)) { P.liste = null; rendre(); chargerListe(); }
        if (id && a.signer && !P.sigFen) { P.signer = true; if (P.detail) ouvrirSignature(true); }
        else if (id && !a.signer && P.sigFen) fermerSignature(true);
      },
      creation: function () { return !!P.creation; },
      ouvrirCreation: function () { return noyau().then(function () { ouvrirCreation(null, true); }); },
      fermerCreation: function () { fermerCreation(true); }
    }
  };
  window.MyToolsParapheurModule = M;
  window.MyToolsParapheur = M;
})();
