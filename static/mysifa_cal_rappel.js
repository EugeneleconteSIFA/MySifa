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

  var etat = { invitations: 0, timer: null, enCours: false, montres: {}, dernier: null };

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
      /* Vraie fenetre : au centre, sur un voile. Une carte discrete en bas a
         droite passait inapercue — un rappel a dix minutes doit arreter l'oeil. */
      /* Au-dessus de tout : le portail empile des elements fixes jusqu'a
         z-index 99998 (dock IA, bandeau staging, toasts). A 9600, la fenetre
         de rappel se retrouvait cachee derriere eux sur l'ecran d'accueil. */
      '#mysifa-cal-rappels{position:fixed;inset:0;z-index:2147483000;display:none;',
      'align-items:center;justify-content:center;padding:18px;',
      'background:rgba(2,6,23,.55);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px)}',
      '#mysifa-cal-rappels.ouvert{display:flex}',
      /* padding + box-sizing : la pile est un conteneur de defilement, elle
         rogne au ras de sa boite. Sans cette marge interieure, l'ombre portee
         et le halo des cartes etaient coupes net — d'ou un cadre gris a coins
         carres autour de la fenetre. */
      '#mysifa-cal-rappels .mcr-pile{display:flex;flex-direction:column;gap:14px;',
      'box-sizing:border-box;width:100%;max-width:436px;padding:18px;',
      'max-height:92vh;overflow-y:auto}',
      /* --mcr-ombre : l'ombre est reprise telle quelle dans les keyframes (une
         animation de box-shadow remplace la declaration de base), et allegee
         en theme clair ou une ombre noire a 50% fait sale. */
      '.mcr-card{background:var(--card,#111827);border:1px solid var(--border,#1e293b);',
      'border-top:3px solid var(--accent,#22d3ee);border-radius:14px;padding:18px 18px 16px;',
      '--mcr-ombre:0 24px 60px rgba(0,0,0,.5);box-shadow:var(--mcr-ombre);',
      /* Le rappel arrive par-dessus une page deja chargee : le lisere accent
         qui respire ramene l'oeil dessus. Anneaux en box-shadow plutot qu'un
         ::after borde : un box-shadow epouse exactement le border-radius, donc
         pas de double trait ni de coins decales, et rien ne bouge en geometrie. */
      'animation:mcrIn .22s ease-out,mcrHalo 2.4s ease-in-out .3s infinite}',
      'body.light .mcr-card{--mcr-ombre:0 18px 44px rgba(15,23,42,.22)}',
      '@keyframes mcrIn{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}',
      '@keyframes mcrHalo{0%,100%{box-shadow:var(--mcr-ombre),',
      '0 0 0 0 var(--accent,#22d3ee),0 0 0 0 var(--accent-bg,rgba(34,211,238,.12))}',
      '50%{box-shadow:var(--mcr-ombre),',
      '0 0 0 2px var(--accent,#22d3ee),0 0 0 9px var(--accent-bg,rgba(34,211,238,.12))}}',
      '@media(prefers-reduced-motion:reduce){.mcr-card{animation:mcrIn .22s ease-out}}',
      '.mcr-quand{font-size:11px;font-weight:800;letter-spacing:1.1px;text-transform:uppercase;',
      'color:var(--accent,#22d3ee)}',
      '.mcr-titre{font-size:17px;font-weight:800;color:var(--text,#f1f5f9);margin-top:5px;line-height:1.3}',
      '.mcr-sous{font-size:12px;color:var(--muted,#94a3b8);margin-top:5px}',
      '.mcr-lieu{font-size:12px;color:var(--text2,#cbd5e1);margin-top:7px}',
      '.mcr-lieu a{color:var(--accent,#22d3ee);font-weight:600}',
      '.mcr-rep{display:flex;gap:7px;margin-top:14px}',
      '.mcr-rep .mcr-btn{font-size:11px;padding:8px 4px}',
      '.mcr-rep .mcr-btn.actif{border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee);',
      'background:var(--accent-bg,rgba(34,211,238,.12))}',
      '.mcr-rep .mcr-btn{white-space:nowrap}',
      '.mcr-lien{display:block;width:100%;margin-top:8px;padding:0;border:none;background:none;',
      'color:var(--muted,#94a3b8);font-family:inherit;font-size:11px;font-weight:600;',
      'text-decoration:underline;cursor:pointer;text-align:center}',
      '.mcr-lien:hover{color:var(--accent,#22d3ee)}',
      '.mcr-actions{display:flex;gap:8px;margin-top:14px;padding-top:12px;',
      'border-top:1px solid var(--border,#1e293b)}',
      '.mcr-btn{flex:1;padding:9px 6px;border:1px solid var(--border,#1e293b);border-radius:9px;',
      'background:var(--bg,#0a0e17);color:var(--text2,#cbd5e1);font-family:inherit;font-size:12px;',
      'font-weight:600;cursor:pointer;transition:border-color .15s,color .15s}',
      '.mcr-btn:hover{border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}',
      '.mcr-btn.mcr-ouvrir{background:var(--accent,#22d3ee);border-color:var(--accent,#22d3ee);',
      /* Le rappel s'affiche sur toutes les pages, dont celles qui ne
         definissent pas --sur-accent : sans la regle body.light, le texte
         tombait sur le fallback sombre sur fond accent bleu — illisible.
         En theme sombre l'accent est cyan clair : le texte doit y rester
         sombre, d'ou les deux regles plutot qu'un blanc en dur. */
      'color:var(--sur-accent,#0a0e17);font-weight:700}',
      'body.light .mcr-btn.mcr-ouvrir{color:#ffffff}',
      '@media(max-width:520px){#mysifa-cal-rappels{align-items:flex-end;padding:10px}',
      '#mysifa-cal-rappels .mcr-pile{max-width:none}}',
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
      el.innerHTML = '<div class="mcr-pile"></div>';
      // Cliquer a cote repousse de 5 minutes plutot que de faire disparaitre :
      // un clic distrait ne doit pas escamoter le rappel jusqu'au lendemain.
      el.addEventListener('click', function (e) {
        if (e.target === el) reporterTout(SNOOZE_MIN);
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && el.classList.contains('ouvert')) reporterTout(SNOOZE_MIN);
      });
      document.body.appendChild(el);
    }
    return el.querySelector('.mcr-pile');
  }

  function majVoile() {
    var el = document.getElementById('mysifa-cal-rappels');
    if (!el) return;
    var pile = el.querySelector('.mcr-pile');
    el.classList.toggle('ouvert', !!(pile && pile.children.length));
  }

  function reporterTout(minutes) {
    Object.keys(etat.montres).forEach(function (id) {
      masquer(id, minutes);
      var c = etat.montres[id];
      if (c && c.parentNode) c.parentNode.removeChild(c);
      delete etat.montres[id];
    });
    majVoile();
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

  var REPONSES = [
    { cle: 'accepte', libelle: 'Oui' },
    { cle: 'peut_etre', libelle: 'Peut-être' },
    { cle: 'refuse', libelle: 'Non' }
  ];

  function repondre(id, statut) {
    var brut = String(id || '').replace(/^perso-/, '');
    return fetch('/api/calendrier/events/perso/' + encodeURIComponent(brut) + '/reponse', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ statut: statut })
    });
  }

  function afficher(r) {
    if (etat.montres[r.id] || estMasque(r.id)) return;
    var mins = minutesAvant(r.debut);
    var quand = 'Rappel · ' + (mins == null ? 'bientôt'
      : (mins <= 0 ? 'ça commence' : 'dans ' + mins + ' min'));
    var heure = String(r.debut || '').slice(11, 16);
    var sous = r.reunion
      ? (r.organisateur ? 'Réunion que vous organisez · ' + heure
                        : 'Réunion de ' + esc(r.organisateur_nom || '') + ' · ' + heure)
      : ('Créneau ' + heure);
    var lieu = '';
    if (r.lieu) lieu += '<div class="mcr-lieu">' + esc(r.lieu) + '</div>';
    if (r.visio) {
      lieu += '<div class="mcr-lieu"><a href="' + esc(r.visio) +
        '" target="_blank" rel="noopener">Rejoindre la visioconférence</a></div>';
    }
    // Un invité qui n'a pas encore tranché peut le faire ici : c'est le moment
    // où il y pense, pas quand il rouvrira le calendrier.
    var rep = '';
    if (r.mon_statut) {
      rep = '<div class="mcr-rep">' + REPONSES.map(function (x) {
        return '<button type="button" class="mcr-btn' +
          (r.mon_statut === x.cle ? ' actif' : '') +
          '" data-rep="' + x.cle + '">' + x.libelle + '</button>';
      }).join('') + '</div>' +
      '<button type="button" class="mcr-lien" data-mcr="autre">Proposer un autre horaire</button>';
    }
    var card = document.createElement('div');
    card.className = 'mcr-card';
    card.setAttribute('data-debut', String(r.debut || ''));
    card.innerHTML =
      '<div class="mcr-quand">' + esc(quand) + '</div>' +
      '<div class="mcr-titre">' + esc(r.titre) + '</div>' +
      '<div class="mcr-sous">' + sous + '</div>' + lieu + rep +
      '<div class="mcr-actions">' +
        '<button type="button" class="mcr-btn" data-mcr="snooze">Dans 5 min</button>' +
        '<button type="button" class="mcr-btn" data-mcr="ok">J\'ai vu</button>' +
        '<button type="button" class="mcr-btn mcr-ouvrir" data-mcr="ouvrir">Ouvrir</button>' +
      '</div>';
    etat.montres[r.id] = card;
    function fermer() {
      delete etat.montres[r.id];
      if (card.parentNode) card.parentNode.removeChild(card);
      majVoile();
    }
    card.querySelectorAll('[data-rep]').forEach(function (b) {
      b.onclick = function () {
        var statut = b.getAttribute('data-rep');
        repondre(r.id, statut).then(function () {
          if (statut === 'refuse') { masquer(r.id, 720); fermer(); return; }
          card.querySelectorAll('[data-rep]').forEach(function (x) {
            x.classList.toggle('actif', x.getAttribute('data-rep') === statut);
          });
        }).catch(function () { /* silencieux : le calendrier reste la source */ });
      };
    });
    card.querySelectorAll('[data-mcr]').forEach(function (b) {
      b.onclick = function () {
        var quoi = b.getAttribute('data-mcr');
        if (quoi === 'snooze') { masquer(r.id, SNOOZE_MIN); fermer(); return; }
        // « J'ai vu » vaut pour la journée : la réunion ne doit pas revenir
        // toquer toutes les minutes jusqu'à son début.
        masquer(r.id, 720);
        fermer();
        if (quoi === 'ouvrir') global.location.href = '/calendrier';
        if (quoi === 'autre') {
          global.location.href = '/calendrier?ev=' + encodeURIComponent(r.id) +
            '&jour=' + encodeURIComponent(String(r.debut || '').slice(0, 10)) +
            '&action=proposer';
        }
      };
    });
    racine().appendChild(card);
    majVoile();
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
        etat.dernier = j;
        // C'est ici, avec l'horloge du poste, qu'on decide ce qui est du :
        // le serveur ne fait que lister les creneaux des prochaines 48 h.
        (j.evenements || j.rappels || []).forEach(function (e) {
          var mins = minutesAvant(e.debut);
          if (mins === null) return;
          var seuil = Number(e.rappel || 10);
          if (seuil > 0 && mins <= seuil && mins >= -2) afficher(e);
        });
        diffuserInvitations(Number(j.invitations || 0));
      })
      .catch(function () { /* une pastille ne casse jamais une page */ })
      .then(function () { etat.enCours = false; });
  }

  /* Le « dans X min » se met a jour tout seul : la fenetre peut rester ouverte
     plusieurs minutes avant qu'on la regarde. */
  function majCompteurs() {
    Object.keys(etat.montres).forEach(function (id) {
      var card = etat.montres[id];
      if (!card) return;
      var debut = card.getAttribute('data-debut');
      var el = card.querySelector('.mcr-quand');
      if (!debut || !el) return;
      var mins = minutesAvant(debut);
      el.textContent = mins == null ? 'Bientôt'
        : (mins <= 0 ? 'Ça commence' : 'Dans ' + mins + ' min');
    });
  }

  function demarrer() {
    if (etat.timer) return;
    verifier();
    etat.timer = setInterval(function () {
      majCompteurs();
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
    invitations: function () { return etat.invitations; },
    /* Diagnostic : ce que le serveur a renvoye et ce que le module en a fait.
       MySifaCalRappel.diagnostic() dans la console. */
    diagnostic: function () {
      var evs = (etat.dernier && (etat.dernier.evenements || etat.dernier.rappels)) || [];
      return {
        maintenant: new Date().toString(),
        invitations: etat.invitations,
        recus: evs.length,
        details: evs.map(function (e) {
          return {
            titre: e.titre, debut: e.debut, rappel: e.rappel,
            minutes: minutesAvant(e.debut),
            masque: estMasque(e.id)
          };
        }),
        affiches: Object.keys(etat.montres)
      };
    },
    /* Pour voir la fenetre sans attendre le prochain rendez-vous :
       MySifaCalRappel.demo() dans la console. */
    demo: function () {
      var d = new Date(Date.now() + 9 * 60000);
      var p2 = function (n) { return (n < 10 ? '0' : '') + n; };
      var iso = d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()) +
        'T' + p2(d.getHours()) + ':' + p2(d.getMinutes());
      afficher({
        id: 'demo-' + Date.now(),
        titre: 'Comité de direction (démonstration)',
        debut: iso,
        reunion: true,
        organisateur: false,
        organisateur_nom: 'Loïc Gognau',
        lieu: 'Salle de réunion',
        visio: '',
        mon_statut: 'en_attente'
      });
    }
  };
})(typeof window !== 'undefined' ? window : this);
