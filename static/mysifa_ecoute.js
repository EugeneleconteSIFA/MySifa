/* MySifa — Réunions : la page d'écoute (/reunions/ecoute).
 *
 * Un bouton : on enregistre, on arrête. Pensée pour un téléphone posé sur la
 * table, elle marche aussi sur un ordinateur.
 *
 * L'audio part au serveur par morceaux de 30 s (MediaRecorder, timeslice) ;
 * un morceau qui n'a pas pu partir (réseau coupé) attend dans IndexedDB et
 * repart dans l'ordre, y compris après un rechargement de la page. À l'arrêt,
 * la page annonce combien de morceaux elle a produits : le serveur compare et
 * signale les trous sur l'écran de validation, il ne les masque pas.
 *
 * Écran maintenu allumé (Wake Lock) : iOS coupe le micro quand l'écran se
 * verrouille. Le navigateur prévient si on quitte la page pendant l'écoute.
 *
 * Hors adresse : tout. La page n'a qu'un écran, et sa fenêtre de rangement
 * (type, titre, réunion) est une étape du geste d'arrêt (url-etat.md).
 */
(function () {
  'use strict';

  var BOOT = window.__REUNIONS__ || {};
  var MORCEAU_MS = 30000;
  var PREF_TYPE = 'reu.ecoute.type';
  var S = {
    etat: 'chargement',      // chargement | pret | reprise | enregistre | envoi | range | fini | erreur
    ecoute: null,            // écoute en cours (serveur)
    enCours: null,           // écoute restée ouverte d'une session précédente
    debut: 0,
    numero: 0,               // prochain numéro de morceau
    file: [],                // morceaux à envoyer : {n, blob}
    envoiEnCours: false,
    echecs: 0,
    mime: '',
    erreur: '',
    fin: null,               // réponse de l'arrêt
    types: [],
    reunions: []
  };
  var recorder = null, flux = null, wakeLock = null, analyseur = null, ctxAudio = null;
  var minuteurChrono = null, animNiveau = null, minuteurEnvoi = null;

  /* ── Outils ─────────────────────────────────────────────────── */

  function h(tag, attrs) {
    var el = document.createElement(tag);
    var a = attrs || {};
    Object.keys(a).forEach(function (k) {
      var v = a[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'className') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'html') el.innerHTML = v;            // SVG statiques uniquement
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'value') el.value = v;
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c === null || c === undefined || c === false) continue;
      el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return el;
  }
  function toast(msg, type) {
    var w = document.getElementById('toast-wrap');
    if (!w) return;
    var t = h('div', {className: 'toast ' + (type || 'success'), text: msg});
    w.appendChild(t);
    setTimeout(function () { t.remove(); }, 3500);
  }
  async function api(chemin, init) {
    var opts = Object.assign({credentials: 'include', headers: {}}, init || {});
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof Blob)) {
      opts.body = JSON.stringify(opts.body);
      opts.headers['Content-Type'] = 'application/json';
    }
    var r = await fetch(chemin, opts);
    var d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) {
      var err = new Error((d && d.detail) || ('Erreur ' + r.status));
      err.status = r.status;
      throw err;
    }
    return d;
  }
  function chrono(ms) {
    var s = Math.floor(ms / 1000), hh = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
    return (hh ? hh + ':' + String(mm).padStart(2, '0') : String(mm).padStart(2, '0')) + ':' + String(ss).padStart(2, '0');
  }
  function heureFr(s) { return s && String(s).length >= 16 ? String(s).slice(11, 16) : ''; }
  function lirePref(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function ecrirePref(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* confort */ } }
  var ICONE_MICRO = '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 10.5a6.5 6.5 0 0 0 13 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8.5" y1="21" x2="15.5" y2="21"/></svg>';
  var ICONE_STOP = '<svg width="36" height="36" viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';

  /* ── Morceaux en attente (IndexedDB) ────────────────────────── */

  var idb = null;
  function ouvrirIdb() {
    if (idb) return Promise.resolve(idb);
    return new Promise(function (ok) {
      try {
        var req = indexedDB.open('mysifa-ecoute', 1);
        req.onupgradeneeded = function () { req.result.createObjectStore('morceaux', {keyPath: 'cle'}); };
        req.onsuccess = function () { idb = req.result; ok(idb); };
        req.onerror = function () { ok(null); };
      } catch (e) { ok(null); }
    });
  }
  function idbFaire(mode, fn) {
    return ouvrirIdb().then(function (db) {
      if (!db) return null;
      return new Promise(function (ok) {
        try {
          var tx = db.transaction('morceaux', mode);
          var res = fn(tx.objectStore('morceaux'));
          tx.oncomplete = function () { ok(res && res.result !== undefined ? res.result : null); };
          tx.onerror = function () { ok(null); };
        } catch (e) { ok(null); }
      });
    });
  }
  function garder(m) { return idbFaire('readwrite', function (st) { return st.put(m); }); }
  function oublier(cle) { return idbFaire('readwrite', function (st) { return st.delete(cle); }); }
  function enAttente() { return idbFaire('readonly', function (st) { return st.getAll(); }); }

  /* ── Envoi ──────────────────────────────────────────────────── */

  function poserMorceau(blob) {
    if (!blob || !blob.size || !S.ecoute) return;
    var m = {cle: S.ecoute.id + ':' + S.numero, ecoute: S.ecoute.id, n: S.numero, blob: blob, mime: S.mime || blob.type || ''};
    S.numero += 1;
    S.file.push(m);
    garder(m);
    envoyer();
  }

  async function envoyer() {
    if (S.envoiEnCours) return;
    S.envoiEnCours = true;
    clearTimeout(minuteurEnvoi);
    try {
      while (S.file.length) {
        var m = S.file[0];
        try {
          await fetch('/api/reunions/ecoutes/' + m.ecoute + '/morceau?n=' + m.n + '&mime=' + encodeURIComponent(m.mime),
            {method: 'POST', credentials: 'include', headers: {'Content-Type': m.mime || 'application/octet-stream'}, body: m.blob})
            .then(function (r) {
              if (r.ok || r.status === 409 || r.status === 404) return r;   // reçu, ou plus attendu
              throw new Error('HTTP ' + r.status);
            });
          S.file.shift();
          oublier(m.cle);
          S.echecs = 0;
        } catch (e) {
          S.echecs += 1;
          peindreEtat();
          minuteurEnvoi = setTimeout(envoyer, Math.min(30000, 2000 * S.echecs));
          return;
        }
      }
    } finally {
      S.envoiEnCours = false;
      peindreEtat();
    }
  }

  async function reprendreAttente() {
    var restes = (await enAttente()) || [];
    restes.sort(function (a, b) { return a.ecoute - b.ecoute || a.n - b.n; });
    restes.forEach(function (m) { S.file.push(m); });
    if (restes.length) envoyer();
  }

  function attendreFile(maxMs) {
    var debut = Date.now();
    return new Promise(function (ok) {
      (function tour() {
        if (!S.file.length || Date.now() - debut > maxMs) return ok(!S.file.length);
        envoyer();
        setTimeout(tour, 500);
      })();
    });
  }

  /* ── Micro, niveau, écran allumé ────────────────────────────── */

  function choisirMime() {
    if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return '';
    var c = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
    for (var i = 0; i < c.length; i++) if (MediaRecorder.isTypeSupported(c[i])) return c[i];
    return '';
  }
  async function garderEcran() {
    try { if (navigator.wakeLock && !wakeLock) { wakeLock = await navigator.wakeLock.request('screen'); wakeLock.addEventListener('release', function () { wakeLock = null; }); } }
    catch (e) { wakeLock = null; }
  }
  function niveau() {
    if (!analyseur) return;
    var buf = new Uint8Array(analyseur.fftSize);
    var barre = document.getElementById('ec-niveau');
    (function tour() {
      if (!analyseur) return;
      analyseur.getByteTimeDomainData(buf);
      var max = 0;
      for (var i = 0; i < buf.length; i++) max = Math.max(max, Math.abs(buf[i] - 128));
      if (barre) barre.style.width = Math.min(100, Math.round(max / 128 * 160)) + '%';
      animNiveau = requestAnimationFrame(tour);
    })();
  }
  function couperMicro() {
    if (animNiveau) cancelAnimationFrame(animNiveau);
    analyseur = null;
    try { if (ctxAudio) ctxAudio.close(); } catch (e) { /* déjà fermé */ }
    ctxAudio = null;
    if (flux) flux.getTracks().forEach(function (t) { t.stop(); });
    flux = null;
    try { if (wakeLock) wakeLock.release(); } catch (e) { /* déjà relâché */ }
    wakeLock = null;
    clearInterval(minuteurChrono);
  }

  /* ── Gestes ─────────────────────────────────────────────────── */

  async function demarrer() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      S.etat = 'erreur'; S.erreur = 'Ce navigateur ne sait pas enregistrer le son. Utiliser Chrome, Edge ou Safari à jour.'; render(); return;
    }
    try {
      flux = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    } catch (e) {
      S.etat = 'erreur'; S.erreur = 'Accès au micro refusé — l’autoriser dans les réglages du navigateur, puis recharger la page.'; render(); return;
    }
    try {
      S.ecoute = await api('/api/reunions/ecoutes', {method: 'POST', body: {type_id: lirePref(PREF_TYPE) || null}});
    } catch (e) {
      couperMicro(); S.etat = 'erreur'; S.erreur = e.message; render(); return;
    }
    S.mime = choisirMime();
    S.numero = 0;
    try {
      recorder = S.mime ? new MediaRecorder(flux, {mimeType: S.mime, audioBitsPerSecond: 32000}) : new MediaRecorder(flux);
    } catch (e) {
      recorder = new MediaRecorder(flux);
    }
    S.mime = S.mime || recorder.mimeType || '';
    recorder.ondataavailable = function (ev) { poserMorceau(ev.data); };
    recorder.start(MORCEAU_MS);
    try {
      ctxAudio = new (window.AudioContext || window.webkitAudioContext)();
      analyseur = ctxAudio.createAnalyser();
      analyseur.fftSize = 512;
      ctxAudio.createMediaStreamSource(flux).connect(analyseur);
    } catch (e) { analyseur = null; }
    S.debut = Date.now();
    S.etat = 'enregistre';
    garderEcran();
    render();
    niveau();
    minuteurChrono = setInterval(function () {
      var el = document.getElementById('ec-chrono');
      if (el) el.textContent = chrono(Date.now() - S.debut);
      if (BOOT.duree_max_h && Date.now() - S.debut > BOOT.duree_max_h * 3600000) {
        toast('Durée maximale atteinte — écoute arrêtée.', 'danger');
        arreter();
      }
    }, 500);
  }

  async function arreter() {
    if (S.etat !== 'enregistre') return;
    S.etat = 'envoi';
    var duree = (Date.now() - S.debut) / 1000;
    render();
    await new Promise(function (ok) {
      if (!recorder || recorder.state === 'inactive') return ok();
      recorder.addEventListener('stop', function () { ok(); }, {once: true});
      try { recorder.stop(); } catch (e) { ok(); }
    });
    couperMicro();
    var complet = await attendreFile(60000);
    if (!complet) toast('Réseau lent : les derniers morceaux partiront dès que possible.', 'danger');
    try {
      S.fin = await api('/api/reunions/ecoutes/' + S.ecoute.id + '/arreter', {method: 'POST',
        body: {nb_morceaux: S.numero, duree_s: duree}});
    } catch (e) {
      S.fin = null;
      toast(e.message, 'danger');
    }
    await chargerRangement();
    S.etat = 'range';
    render();
  }

  async function terminerAncienne() {
    // Les morceaux restés dans le navigateur partent d'abord : sinon l'arrêt
    // les déclarerait manquants.
    await attendreFile(30000);
    try {
      S.fin = await api('/api/reunions/ecoutes/' + S.enCours.id + '/arreter', {method: 'POST', body: {}});
      S.ecoute = S.enCours; S.enCours = null;
      await chargerRangement();
      S.etat = 'range';
    } catch (e) { toast(e.message, 'danger'); }
    render();
  }

  async function chargerRangement() {
    try {
      var res = await Promise.all([api('/api/reunions/types'), api('/api/reunions?limite=20')]);
      S.types = res[0].types || [];
      S.reunions = res[1].reunions || [];
    } catch (e) { S.types = []; S.reunions = []; }
  }

  async function ranger(d) {
    if (d.type_id) ecrirePref(PREF_TYPE, d.type_id);
    try {
      S.fin = await api('/api/reunions/ecoutes/' + S.ecoute.id + '/arreter', {method: 'POST', body: d});
      S.etat = 'fini';
      render();
    } catch (e) { toast(e.message, 'danger'); }
  }

  /* ── Rendu ──────────────────────────────────────────────────── */

  function peindreEtat() {
    var el = document.getElementById('ec-envoi');
    if (!el) return;
    el.textContent = '';
    if (S.file.length > 1 || S.echecs) {
      el.appendChild(h('span', {className: 'reu-pastille warn', text: S.file.length + ' morceau(x) en attente d’envoi' + (S.echecs ? ' — réseau indisponible, nouvel essai automatique' : '')}));
    } else if (S.etat === 'enregistre') {
      el.appendChild(h('span', {className: 'reu-pastille ok', text: 'Envoi à jour'}));
    }
  }

  function render() {
    var c = document.getElementById('content');
    if (!c) return;
    c.innerHTML = '';
    var scene = h('div', {className: 'ec-scene'});
    c.appendChild(scene);

    if (S.etat === 'chargement') { scene.appendChild(h('div', {className: 'reu-chargement', text: 'Chargement…'})); return; }

    if (S.etat === 'erreur') {
      scene.appendChild(h('div', {className: 'ec-titre', text: 'Écoute impossible'}));
      scene.appendChild(h('div', {className: 'reu-avert', text: S.erreur}));
      scene.appendChild(h('a', {className: 'btn', href: '/reunions', text: 'Retour aux réunions'}));
      return;
    }

    if (S.etat === 'reprise') {
      scene.appendChild(h('div', {className: 'ec-titre', text: 'Une écoute est restée ouverte'}));
      scene.appendChild(h('div', {className: 'ec-sous', text: 'Démarrée à ' + heureFr(S.enCours.demarre_le) + ', ' + (S.enCours.nb_morceaux || 0) + ' morceau(x) reçu(s). Elle ne peut pas reprendre là où elle s’est arrêtée : la terminer envoie ce qui a été reçu en transcription.'}));
      scene.appendChild(h('div', {className: 'reu-rangee', style: 'justify-content:center'},
        h('button', {type: 'button', className: 'btn btn-accent', text: 'Terminer cette écoute', onClick: terminerAncienne})));
      return;
    }

    if (S.etat === 'pret') {
      scene.appendChild(h('div', {className: 'ec-titre', text: 'Écouter une réunion'}));
      scene.appendChild(h('div', {className: 'ec-sous', text: 'MySifa enregistre la réunion, la transcrit sur le serveur et propose un compte-rendu à relire : notes, décisions, actions.'}));
      scene.appendChild(h('button', {type: 'button', className: 'ec-bouton', 'aria-label': 'Démarrer l’écoute', onClick: demarrer,
        html: ICONE_MICRO + '<span>Démarrer</span>'}));
      scene.appendChild(h('div', {className: 'ec-rappel'}, h('strong', {text: 'Prévenez les participants que la réunion est enregistrée. '}),
        'Posez le téléphone au centre de la table et laissez l’écran allumé : un écran verrouillé coupe le micro.'));
      return;
    }

    if (S.etat === 'enregistre' || S.etat === 'envoi') {
      scene.appendChild(h('div', {className: 'ec-etat'}, h('span', {className: 'ec-point'}), h('span', {className: 'reu-etat-enreg', style: 'font-weight:700', text: S.etat === 'envoi' ? 'Envoi des derniers morceaux…' : 'Écoute en cours'})));
      scene.appendChild(h('div', {className: 'ec-chrono', id: 'ec-chrono', text: chrono(Date.now() - S.debut)}));
      scene.appendChild(h('div', {className: 'ec-niveau', 'aria-hidden': 'true'}, h('div', {id: 'ec-niveau'})));
      scene.appendChild(h('div', {id: 'ec-envoi', className: 'ec-etat'}));
      scene.appendChild(h('button', {type: 'button', className: 'ec-bouton arreter', disabled: S.etat === 'envoi', 'aria-label': 'Arrêter l’écoute', onClick: arreter,
        html: ICONE_STOP + '<span>Arrêter</span>'}));
      scene.appendChild(h('div', {className: 'ec-rappel', text: 'Ne verrouillez pas l’écran et ne quittez pas cette page pendant la réunion.'}));
      peindreEtat();
      return;
    }

    if (S.etat === 'range') {
      var d = {type_id: (S.fin && S.fin.type_id) ? String(S.fin.type_id) : (lirePref(PREF_TYPE) || ''), titre: '', reunion_id: ''};
      if (!d.type_id && S.types[0]) d.type_id = String(S.types[0].id);
      var selType = h('select', {'aria-label': 'Type', onChange: function () { d.type_id = selType.value; }});
      S.types.forEach(function (t) { selType.appendChild(h('option', {value: String(t.id), text: t.libelle})); });
      selType.value = d.type_id;
      var selReu = h('select', {'aria-label': 'Réunion', onChange: function () { d.reunion_id = selReu.value; }});
      selReu.appendChild(h('option', {value: '', text: 'Une nouvelle réunion'}));
      S.reunions.forEach(function (r) {
        var j = String(r.date_debut || '').slice(0, 10).split('-').reverse().join('/');
        selReu.appendChild(h('option', {value: String(r.id), text: j + ' · ' + r.titre}));
      });
      var titre = h('input', {type: 'text', placeholder: 'Facultatif — le brief en proposera un', 'aria-label': 'Titre', onInput: function (ev) { d.titre = ev.target.value; }});
      scene.appendChild(h('div', {className: 'ec-titre', text: 'Écoute terminée'}));
      if (S.fin && S.fin.statut === 'abandonnee') {
        scene.appendChild(h('div', {className: 'reu-avert', text: S.fin.erreur || 'Aucun son reçu : rien à transcrire.'}));
        scene.appendChild(h('a', {className: 'btn', href: '/reunions', text: 'Retour aux réunions'}));
        return;
      }
      if (S.fin && S.fin.morceaux_manquants && S.fin.morceaux_manquants.length) {
        scene.appendChild(h('div', {className: 'reu-avert'}, h('strong', {text: 'Passages manquants. '}),
          S.fin.morceaux_manquants.length + ' morceau(x) de 30 s ne sont pas arrivés : ils seront signalés sur le brief.'));
      }
      var carte = h('div', {className: 'reu-carte', style: 'width:100%;text-align:left'},
        h('label', {className: 'reu-label', text: 'Type de réunion'}), selType,
        h('label', {className: 'reu-label', text: 'Titre'}), titre,
        h('label', {className: 'reu-label', text: 'Enregistrer dans'}), selReu,
        h('div', {className: 'reu-rangee', style: 'justify-content:flex-end;margin-top:16px'},
          h('button', {type: 'button', className: 'btn btn-accent', text: 'Continuer', onClick: function () { ranger({type_id: d.type_id || null, titre: d.titre, reunion_id: d.reunion_id || null}); }})));
      scene.appendChild(carte);
      return;
    }

    if (S.etat === 'fini') {
      var min = S.fin && S.fin.attente_min;
      scene.appendChild(h('div', {className: 'ec-titre', text: 'Transcription en cours'}));
      scene.appendChild(h('div', {className: 'ec-sous', text: (min ? 'Le brief sera prêt dans ~' + min + ' min. ' : '') + 'Une notification vous préviendra ; il apparaît aussi dans Réunions › Mes écoutes.'}));
      scene.appendChild(h('div', {className: 'reu-rangee', style: 'justify-content:center'},
        h('a', {className: 'btn btn-accent', href: '/reunions?ecoute=' + S.ecoute.id, text: 'Suivre l’écoute'}),
        h('button', {type: 'button', className: 'btn', text: 'Nouvelle écoute', onClick: function () { S.ecoute = null; S.fin = null; S.etat = 'pret'; render(); }})));
    }
  }

  /* ── Démarrage ──────────────────────────────────────────────── */

  window.toggleSidebar = function () { document.body.classList.toggle('sb-open'); };
  window.closeSidebar = function () { document.body.classList.remove('sb-open'); };
  window.addEventListener('beforeunload', function (ev) {
    if (S.etat === 'enregistre' || S.etat === 'envoi' || S.file.length) { ev.preventDefault(); ev.returnValue = ''; }
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && S.etat === 'enregistre') garderEcran();
  });
  window.addEventListener('online', function () { envoyer(); });

  (async function () {
    await reprendreAttente();
    try {
      var d = await api('/api/reunions/ecoutes');
      if (d.en_cours) { S.enCours = d.en_cours; S.etat = 'reprise'; }
      else S.etat = 'pret';
    } catch (e) {
      if (e.status === 401) { location.href = '/?next=/reunions/ecoute'; return; }
      S.etat = 'erreur'; S.erreur = e.message;
    }
    render();
  })();
})();
