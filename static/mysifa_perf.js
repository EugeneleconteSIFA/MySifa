/* ============================================================
   MySifa — mysifa_perf.js
   Sait si MySifa rame sur ce poste, et allège l'affichage si oui.

   Chargé dans <head> sans defer : le verdict d'une visite précédente doit
   être appliqué AVANT le premier rendu, sinon le poste lent paie quand même
   la première frame — celle qui coûte le plus cher.

   Trois modes, préférence `mysifa_perf_mode` en localStorage :
     'auto'   (défaut) — la sonde décide
     'normal'           — tout est affiché, quoi que dise la mesure
     'eco'              — allégé en permanence

   La sonde, elle, ne devine pas : elle compte les images réellement
   affichées pendant une seconde, sur la vraie page, avec ses vrais effets.
   Un poste qui tient 12 images par seconde est lent — son âge, sa RAM et son
   nombre de cœurs ne servent qu'à confirmer.

   Verdict collant : une fois un poste passé en éco, on n'y revient pas tout
   seul. Remesurer en mode éco donnerait forcément un bon score (les effets
   sont coupés) et le poste oscillerait à chaque visite. Le retour se fait
   depuis Mon profil, bouton « Refaire la mesure ».

   API : window.MySifaPerf {mode, setMode, actif, dernier, remesurer}
   ============================================================ */
(function (global) {
  'use strict';

  var LS_MODE = 'mysifa_perf_mode';
  var LS_VERDICT = 'mysifa_perf_verdict';
  var LS_POSTE = 'mysifa_perf_poste';
  var LS_NOTE = 'mysifa_perf_note_vue';
  var SS_ENVOYE = 'mysifa_perf_envoye';

  var SEUIL_FPS_DUR = 30;    // en dessous : éco sans discussion
  var SEUIL_SCORE = 4;       // sinon : faisceau d'indices
  var DUREE_MESURE = 1100;   // ms de comptage d'images
  var PEREMPTION_J = 60;     // au-delà, on remesure un poste resté « normal »

  var Perf = {};
  var dernier = null;

  // ---------- petits utilitaires localStorage (jamais fatals) ----------
  function lire(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
  function ecrire(cle, val) { try { localStorage.setItem(cle, val); } catch (e) {} }

  function mode() {
    var m = lire(LS_MODE);
    return (m === 'eco' || m === 'normal') ? m : 'auto';
  }

  function verdict() {
    try { return JSON.parse(lire(LS_VERDICT) || 'null'); } catch (e) { return null; }
  }

  // Identifiant de machine : tiré au sort, gardé localement, ne dit rien de
  // la personne. Sert uniquement à recoller les relevés d'un même poste.
  function poste() {
    var p = lire(LS_POSTE);
    if (!p) {
      p = 'p' + Math.random().toString(36).slice(2, 10) + Math.random().toString(36).slice(2, 6);
      ecrire(LS_POSTE, p);
    }
    return p;
  }

  // ---------- application ----------
  function ecoVoulu() {
    var m = mode();
    if (m === 'eco') return true;
    if (m === 'normal') return false;
    var v = verdict();
    return !!(v && v.niveau === 'eco');
  }

  function appliquer(eco) {
    var html = document.documentElement;
    if (html) html.classList.toggle('perf-eco', !!eco);
    var b = document.body;
    if (b) {
      b.classList.toggle('perf-eco', !!eco);
      // motion.js lit cette classe pour désactiver ses six patterns.
      b.classList.toggle('reduce-anim', !!eco);
    }
  }

  appliquer(ecoVoulu());  // avant le premier rendu

  function surBody(fn) {
    if (document.body) { fn(); return; }
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  }
  surBody(function () { appliquer(ecoVoulu()); });

  // ---------- la mesure ----------
  // Compte les images affichées pendant DUREE_MESURE ms. Abandonne si l'onglet
  // passe en arrière-plan : le navigateur y bride requestAnimationFrame, et on
  // conclurait qu'un poste sain est à 2 images par seconde.
  function mesurerFps(cb) {
    if (typeof requestAnimationFrame !== 'function' || document.hidden) { cb(null); return; }

    var frames = 0, durees = [], t0 = performance.now(), tPrec = t0, abandon = false;

    function onCache() { if (document.hidden) abandon = true; }
    document.addEventListener('visibilitychange', onCache);

    function tick(t) {
      if (abandon) { document.removeEventListener('visibilitychange', onCache); cb(null); return; }
      frames++;
      durees.push(t - tPrec);
      tPrec = t;
      var ecoule = t - t0;
      if (ecoule < DUREE_MESURE) { requestAnimationFrame(tick); return; }
      document.removeEventListener('visibilitychange', onCache);
      durees.sort(function (a, b) { return a - b; });
      var pire = durees[Math.floor(durees.length * 0.95)] || durees[durees.length - 1] || 0;
      cb({
        fps: Math.round((frames / ecoule) * 1000 * 10) / 10,
        // Le creux : la fluidité perçue tient au pire moment, pas à la moyenne.
        fps_bas: pire > 0 ? Math.round((1000 / pire) * 10) / 10 : null
      });
    }
    requestAnimationFrame(tick);
  }

  // Temps de blocage du fil principal pendant la mesure : une page peut
  // afficher 60 images par seconde et rester impossible à cliquer.
  function observerBlocage() {
    var total = 0, obs = null;
    try {
      obs = new PerformanceObserver(function (list) {
        list.getEntries().forEach(function (e) { total += Math.max(0, e.duration - 50); });
      });
      obs.observe({ entryTypes: ['longtask'] });
    } catch (e) { obs = null; }
    return function () { try { if (obs) obs.disconnect(); } catch (e) {} return Math.round(total); };
  }

  function tempsNavigation() {
    try {
      var n = (performance.getEntriesByType('navigation') || [])[0];
      if (!n) return {};
      return {
        t_reponse_ms: Math.round(n.responseEnd - n.requestStart),
        // Ce que le poste met à construire la page une fois les octets reçus :
        // c'est là que se voit un CPU faible, pas dans le temps réseau.
        t_rendu_ms: Math.round(n.domContentLoadedEventEnd - n.responseEnd),
        t_charge_ms: Math.round(n.loadEventEnd - n.startTime)
      };
    } catch (e) { return {}; }
  }

  function noter(m) {
    var s = 0;
    if (m.fps != null) {
      if (m.fps < 20) s += 4;
      else if (m.fps < 32) s += 3;
      else if (m.fps < 45) s += 2;
      else if (m.fps < 55) s += 1;
    }
    if (m.fps_bas != null && m.fps_bas < 15) s += 1;
    if (m.blocage_ms > 500) s += 1;
    if (m.cores != null) { if (m.cores <= 2) s += 2; else if (m.cores <= 4) s += 1; }
    if (m.memoire_go != null) { if (m.memoire_go <= 2) s += 2; else if (m.memoire_go <= 4) s += 1; }
    if (m.t_rendu_ms != null) { if (m.t_rendu_ms > 2500) s += 2; else if (m.t_rendu_ms > 1200) s += 1; }
    return s;
  }

  function collecter(cb) {
    var finBlocage = observerBlocage();
    mesurerFps(function (fps) {
      var blocage = finBlocage();
      if (!fps) { cb(null); return; }   // onglet caché : rien de fiable à dire
      var nav = tempsNavigation();
      var m = {
        poste: poste(),
        fps: fps.fps,
        fps_bas: fps.fps_bas,
        blocage_ms: blocage,
        cores: (navigator.hardwareConcurrency != null) ? navigator.hardwareConcurrency : null,
        memoire_go: (navigator.deviceMemory != null) ? navigator.deviceMemory : null,
        dpr: window.devicePixelRatio || 1,
        ecran: (screen && screen.width) ? (screen.width + 'x' + screen.height) : null,
        t_reponse_ms: nav.t_reponse_ms != null ? nav.t_reponse_ms : null,
        t_rendu_ms: nav.t_rendu_ms != null ? nav.t_rendu_ms : null,
        t_charge_ms: nav.t_charge_ms != null ? nav.t_charge_ms : null,
        page: (location.pathname || '/').slice(0, 120),
        navigateur: (navigator.userAgent || '').slice(0, 240),
        mesure_le: new Date().toISOString()
      };
      m.score = noter(m);
      // Ce que la mesure conclut...
      m.verdict = (m.fps != null && m.fps < SEUIL_FPS_DUR) || m.score >= SEUIL_SCORE ? 'eco' : 'normal';
      // ...et ce que le poste affiche réellement en ce moment. Les deux
      // diffèrent dès qu'un poste est déjà en éco : il mesure alors sans les
      // effets, donc bien. C'est le second qui part au serveur, sinon la vue
      // superadmin dirait « tout va bien » de tous les postes allégés.
      m.niveau = ecoVoulu() ? 'eco' : 'normal';
      cb(m);
    });
  }

  // ---------- remontée au serveur ----------
  // Un envoi par session : de quoi voir quels postes rament dans la durée,
  // sans transformer chaque navigation en trafic.
  function envoyer(m, forceMain) {
    try {
      if (sessionStorage.getItem(SS_ENVOYE)) return;
      sessionStorage.setItem(SS_ENVOYE, '1');
    } catch (e) {}
    var corps = JSON.stringify({
      poste: m.poste, niveau: m.niveau, score: m.score, force_main: forceMain ? 1 : 0,
      fps: m.fps, fps_bas: m.fps_bas, blocage_ms: m.blocage_ms,
      cores: m.cores, memoire_go: m.memoire_go, dpr: m.dpr, ecran: m.ecran,
      t_reponse_ms: m.t_reponse_ms, t_rendu_ms: m.t_rendu_ms, t_charge_ms: m.t_charge_ms,
      page: m.page, navigateur: m.navigateur
    });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/perf/releve', new Blob([corps], { type: 'application/json' }));
        return;
      }
    } catch (e) {}
    try {
      fetch('/api/perf/releve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: corps, credentials: 'same-origin', keepalive: true
      }).catch(function () {});
    } catch (e) {}
  }

  // ---------- bandeau d'information ----------
  // Affiché une seule fois par poste : il faut que la personne comprenne
  // pourquoi son MySifa n'a pas le même fond que celui du voisin.
  function annoncer() {
    if (lire(LS_NOTE) === '1') return;
    if (!document.body) return;
    ecrire(LS_NOTE, '1');
    var d = document.createElement('div');
    d.className = 'perf-note';
    d.innerHTML =
      '<div class="perf-note-txt"><b>Affichage allégé activé</b>' +
      '<div class="perf-note-sub">Cet ordinateur n\'affichait pas MySifa de façon fluide. ' +
      'Les effets d\'arrière-plan sont désactivés — réglable dans Mon profil.</div></div>' +
      '<button type="button">OK</button>';
    d.querySelector('button').addEventListener('click', function () { d.remove(); });
    document.body.appendChild(d);
    setTimeout(function () { if (d.parentNode) d.remove(); }, 12000);
  }

  // ---------- orchestration ----------
  function faut_il_mesurer() {
    if (mode() !== 'auto') return true;      // on mesure quand même, pour la télémétrie
    var v = verdict();
    if (!v) return true;
    if (v.niveau === 'eco') return false;    // verdict collant, voir l'en-tête
    var age = (Date.now() - (v.t || 0)) / 86400000;
    return age > PEREMPTION_J;
  }

  function lancer() {
    var forceMain = mode() !== 'auto';
    // On mesure à chaque session, même quand le verdict est figé : c'est ce qui
    // permet de voir un poste se dégrader dans le temps. Ce qui est conditionnel,
    // c'est le droit de changer le verdict, pas la mesure.
    var peutTrancher = mode() === 'auto' && faut_il_mesurer();

    collecter(function (m) {
      if (!m) return;
      dernier = m;
      if (peutTrancher) {
        var avant = ecoVoulu();
        ecrire(LS_VERDICT, JSON.stringify({
          niveau: m.verdict, fps: m.fps, score: m.score, t: Date.now()
        }));
        if (m.verdict === 'eco' && !avant) {
          appliquer(true);
          m.niveau = 'eco';
          annoncer();
        }
      }
      envoyer(m, forceMain);
    });
  }

  // Après le load complet, plus une respiration : mesurer pendant que la page
  // se monte reviendrait à mesurer le montage, pas le poste.
  function planifier() { setTimeout(lancer, 700); }
  if (document.readyState === 'complete') planifier();
  else window.addEventListener('load', planifier, { once: true });

  // ---------- API publique ----------
  Perf.mode = mode;
  Perf.poste = poste;
  Perf.actif = ecoVoulu;
  Perf.dernier = function () { return dernier || verdict(); };

  Perf.setMode = function (m) {
    ecrire(LS_MODE, (m === 'eco' || m === 'normal') ? m : 'auto');
    appliquer(ecoVoulu());
    return mode();
  };

  // Remesure explicite (Mon profil). En mode éco, les effets sont coupés :
  // on les rallume le temps de la mesure, sinon on mesurerait le vide.
  Perf.remesurer = function (cb) {
    var etait = ecoVoulu();
    appliquer(false);
    setTimeout(function () {
      collecter(function (m) {
        if (!m) { appliquer(etait); if (cb) cb(null); return; }
        dernier = m;
        ecrire(LS_VERDICT, JSON.stringify({ niveau: m.verdict, fps: m.fps, score: m.score, t: Date.now() }));
        if (mode() === 'auto') appliquer(m.verdict === 'eco');
        else appliquer(etait);
        m.niveau = ecoVoulu() ? 'eco' : 'normal';
        try { sessionStorage.removeItem(SS_ENVOYE); } catch (e) {}
        envoyer(m, mode() !== 'auto');
        if (cb) cb(m);
      });
    }, 400);   // laisser le fond animé reprendre avant de compter
  };

  global.MySifaPerf = Perf;
})(window);
