/**
 * MySifa — rappel avant une réunion (MyCalendrier).
 *
 * Chargé sur toutes les pages du portail : une réunion qui commence dans dix
 * minutes doit prévenir là où l'utilisateur travaille, pas seulement sur la
 * page Calendrier qu'il n'a pas ouverte.
 *
 * Le même appel sert la pastille d'invitations en attente : un seul aller-retour
 * toutes les minutes, diffusé aux pages intéressées par l'événement
 * `mysifa:cal-invitations`.
 */
(function (global) {
  'use strict';

  var URL_API = '/api/calendrier/notifications';
  var PERIODE_MS = 60000;
  var LS_VUS = 'mysifa_cal_rappels_vus';
  var SNOOZE_MIN = 5;

  var etat = { invitations: 0, timer: null, enCours: false, montres: {} };

  function maintenant() { return Date.now(); }

  function lireVus() {
    try {
      var raw = localStorage.getItem(LS_VUS);
      var o = raw ? JSON.parse(raw) : null;
      if (!o || typeof o !== 'object') return {};
      // Purge des entrées expirées — sinon la clé grossit indéfiniment.
      var out = {}, t = maintenant();
      Object.keys(o).forEach(function (k) {
        if (typeof o[k] === 'number' && o[k] > t) out[k] = o[k];
      });
      return out;
    } catch (e) { return {}; }
  }

  function masquer(id, minutes) {
    try {
      var o = lireVus();
      o[id] = maintenant() + (minutes || 60) * 60000;
      localStorage.setItem(LS_VUS, JSON.stringify(o));
    } catch (e) { /* ignore */ }
  }

  function estMasque(id) {
    var o = lireVus();
    return typeof o[id] === 'number' && o[id] > maintenant();
  }

  function injecterCss() {
    if (document.getElementById('mysifa-cal-rappel-css')) return;
    var st = document.createElement('style');
    st.id = 'mysifa-cal-rappel-css';
    st.textContent = [
      '#mysifa-cal-rappels{position:fixed;right:20px;bottom:96px;z-index:9500;',
      'display:flex;flex-direction:column;gap:10px;max-width:330px;pointer-events:none}',
      '.mcr-card{pointer-events:auto;background:var(--card,#111827);border:1px solid var(--border,#1e293b);',
      'border-left:3px solid var(--accent,#22d3ee);border-radius:12px;padding:13px 14px;',
      'box-shadow:0 12px 32px rgba(0,0,0,.35);animation:mcrIn .22s ease-out}',
      '@keyframes mcrIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}',
      '.mcr-quand{font-size:10px;font-weight:800;letter-spacing:1px;text-transform:uppercase;',
      'color:var(--accent,#22d3ee)}',
      '.mcr-titre{font-size:13px;font-weight:700;color:var(--text,#f1f5f9);margin-top:3px;line-height:1.35}',
      '.mcr-sous{font-size:11px;color:var(--muted,#94a3b8);margin-top:3px}',
      '.mcr-actions{display:flex;gap:7px;margin-top:11px}',
      '.mcr-btn{flex:1;padding:7px 6px;border:1px solid var(--border,#1e293b);border-radius:8px;',
      'background:var(--bg,#0a0e17);color:var(--text2,#cbd5e1);font-family:inherit;font-size:11px;',
      'font-weight:600;cursor:pointer;transition:border-color .15s,color .15s}',
      '.mcr-btn:hover{border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}',
      '.mcr-btn.mcr-ouvrir{border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}',
      '@media(max-width:720px){#mysifa-cal-rappels{left:12px;right:12px;bottom:12px;max-width:none}}',
      '@media print{#mysifa-cal-rappels{display:none!important}}'
    ].join('');
    document.head.appendChild(st);
  }

  function racine() {
    var el = document.getElementById('mysifa-cal-rappels');
    if (!el) {
      injecterCss();
      el = document.createElement('div');
      el.id = 'mysifa-cal-rappels';
      document.body.appendChild(el);
    }
    return el;
  }

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function minutesAvant(debut) {
    var d = new Date(String(debut || '').replace(' ', 'T'));
    if (isNaN(d.getTime())) return null;
    return Math.round((d.getTime() - maintenant()) / 60000);
  }

  function afficher(r) {
    if (etat.montres[r.id] || estMasque(r.id)) return;
    var mins = minutesAvant(r.debut);
    var quand = mins == null ? 'Bientôt'
      : (mins <= 0 ? 'Ça commence' : 'Dans ' + mins + ' min');
    var heure = String(r.debut || '').slice(11, 16);
    var sous = r.reunion
      ? (r.organisateur ? 'Réunion que vous organisez · ' + heure
                        : 'Réunion de ' + esc(r.organisateur_nom || '') + ' · ' + heure)
      : ('Créneau ' + heure);
    var card = document.createElement('div');
    card.className = 'mcr-card';
    card.innerHTML =
      '<div class="mcr-quand">' + esc(quand) + '</div>' +
      '<div class="mcr-titre">' + esc(r.titre) + '</div>' +
      '<div class="mcr-sous">' + sous + '</div>' +
      '<div class="mcr-actions">' +
        '<button type="button" class="mcr-btn" data-mcr="snooze">Dans 5 min</button>' +
        '<button type="button" class="mcr-btn" data-mcr="ok">J\'ai vu</button>' +
        '<button type="button" class="mcr-btn mcr-ouvrir" data-mcr="ouvrir">Ouvrir</button>' +
      '</div>';
    etat.montres[r.id] = card;
    function fermer() {
      delete etat.montres[r.id];
      if (card.parentNode) card.parentNode.removeChild(card);
    }
    card.querySelectorAll('[data-mcr]').forEach(function (b) {
      b.onclick = function () {
        var quoi = b.getAttribute('data-mcr');
        if (quoi === 'snooze') { masquer(r.id, SNOOZE_MIN); fermer(); return; }
        // « J'ai vu » vaut pour la journée : la réunion ne doit pas revenir
        // toquer toutes les minutes jusqu'à son début.
        masquer(r.id, 720);
        fermer();
        if (quoi === 'ouvrir') global.location.href = '/calendrier';
      };
    });
    racine().appendChild(card);
  }

  function diffuserInvitations(n) {
    etat.invitations = n;
    try {
      global.dispatchEvent(new CustomEvent('mysifa:cal-invitations', { detail: { nombre: n } }));
    } catch (e) { /* ignore */ }
  }

  function verifier() {
    if (etat.enCours) return Promise.resolve();
    etat.enCours = true;
    return fetch(URL_API, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) return;
        (j.rappels || []).forEach(afficher);
        diffuserInvitations(Number(j.invitations || 0));
      })
      .catch(function () { /* une pastille ne casse jamais une page */ })
      .then(function () { etat.enCours = false; });
  }

  function demarrer() {
    if (etat.timer) return;
    verifier();
    etat.timer = setInterval(function () {
      if (document.hidden) return;
      verifier();
    }, PERIODE_MS);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) verifier();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', demarrer);
  } else {
    demarrer();
  }

  global.MySifaCalRappel = {
    rafraichir: verifier,
    invitations: function () { return etat.invitations; }
  };
})(typeof window !== 'undefined' ? window : this);
