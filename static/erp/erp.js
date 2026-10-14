/* Nouvel ERP — coque : navigation, routage par chemin, session.
 *
 * Toutes les URL de erp.mysifa.com renvoient la même page ; ce script lit le
 * chemin réel (location.pathname) et affiche l'écran correspondant.
 *
 * Un écran s'enregistre dans ERP.ecrans['/ventes/commandes'] = fn(main, ctx).
 * Une adresse plus longue (`/ventes/commandes/12`) est servie par l'écran du
 * plus long préfixe enregistré, avec ctx.param = '12'.
 *
 * L'écran n'est reconstruit qu'au changement d'adresse : changer de thème ou
 * recevoir le profil ne redessine que la barre latérale — une saisie en cours
 * ne se perd pas. Un écran qui a des modifications non enregistrées pose
 * ERP.garde = function () { return true; } : quitter demande confirmation.
 */
(function () {
  'use strict';

  var NAV = [
    {groupe: null, liens: [{chemin: '/', libelle: 'Accueil'}]},
    {groupe: 'Ventes', liens: [
      {chemin: '/ventes/devis', libelle: 'Devis'},
      {chemin: '/ventes/marches', libelle: 'Marchés'},
      {chemin: '/ventes/commandes', libelle: 'Commandes'},
      {chemin: '/ventes/livraisons', libelle: 'Livraisons'},
      {chemin: '/ventes/factures', libelle: 'Factures et avoirs'},
    ]},
    {groupe: 'Achats', liens: [
      {chemin: '/achats/commandes', libelle: 'Commandes fournisseur'},
      {chemin: '/achats/receptions', libelle: 'Réceptions'},
      {chemin: '/achats/factures', libelle: 'Factures fournisseur'},
    ]},
    {groupe: 'Stocks', liens: [
      {chemin: '/stocks/etat', libelle: 'État du stock'},
      {chemin: '/stocks/mouvements', libelle: 'Mouvements'},
    ]},
    {groupe: 'Production', liens: [
      {chemin: '/production/ordres', libelle: 'Ordres de fabrication'},
    ]},
    {groupe: 'Comptabilité', liens: [
      {chemin: '/compta/echeances', libelle: 'Échéances'},
      {chemin: '/compta/reglements', libelle: 'Règlements'},
    ]},
    {groupe: 'Fichiers', liens: [
      {chemin: '/fichiers/clients', libelle: 'Clients'},
      {chemin: '/fichiers/fournisseurs', libelle: 'Fournisseurs'},
      {chemin: '/fichiers/articles', libelle: 'Articles'},
    ]},
    {groupe: 'Paramètres', liens: [
      {chemin: '/parametres', libelle: 'Paramètres'},
      {chemin: '/parametres/composants', libelle: 'Composants'},
    ]},
  ];

  var S = {chemin: normaliser(location.pathname), user: null};
  var navEl = null;

  function normaliser(p) { return (p || '/').replace(/\/+$/, '') || '/'; }

  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'text') el.textContent = v;
      else if (k === 'className') el.className = v;
      else if (k === 'value') el.value = v;
      else if (k === 'checked') el.checked = !!v;
      else if (k === 'disabled') el.disabled = !!v;
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) ajouter(el, arguments[i]);
    return el;
  }
  function ajouter(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { ajouter(el, x); }); return; }
    el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }

  async function api(path, options) {
    var o = Object.assign({credentials: 'same-origin', headers: {}}, options || {});
    if (o.body && typeof o.body !== 'string') {
      o.headers['Content-Type'] = 'application/json';
      o.body = JSON.stringify(o.body);
    }
    var r = await fetch(path, o);
    if (r.status === 401) { location.reload(); throw new Error('Session expirée.'); }
    var data = null;
    try { data = await r.json(); } catch (e) { /* réponse vide */ }
    if (!r.ok) throw new Error((data && data.detail) || ('Erreur ' + r.status));
    return data;
  }

  // ── Toasts ───────────────────────────────────────────────────────
  function toast(msg, type) {
    var zone = document.getElementById('erp-toasts');
    if (!zone) { zone = h('div', {id: 'erp-toasts', className: 'erp-toasts'}); document.body.appendChild(zone); }
    var t = h('div', {className: 'erp-toast ' + (type || 'info'), role: 'status', text: msg});
    zone.appendChild(t);
    setTimeout(function () { t.classList.add('sortie'); setTimeout(function () { t.remove(); }, 250); }, type === 'danger' ? 6000 : 3000);
  }

  // ── Routage ──────────────────────────────────────────────────────
  function resoudre(chemin) {
    if (ERP.ecrans[chemin]) return {cle: chemin, param: ''};
    var meilleur = null;
    Object.keys(ERP.ecrans).forEach(function (k) {
      if (k !== '/' && chemin.indexOf(k + '/') === 0 && (!meilleur || k.length > meilleur.length)) meilleur = k;
    });
    return meilleur ? {cle: meilleur, param: chemin.slice(meilleur.length + 1)} : null;
  }

  function lienCourant() {
    var res = null;
    NAV.forEach(function (g) {
      g.liens.forEach(function (l) {
        if (S.chemin === l.chemin || (l.chemin !== '/' && S.chemin.indexOf(l.chemin + '/') === 0)) {
          if (!res || l.chemin.length > res.lien.chemin.length) res = {groupe: g.groupe, lien: l};
        }
      });
    });
    return res;
  }

  function quitterPossible() {
    if (ERP.garde && ERP.garde()) {
      if (!confirm('Des modifications ne sont pas enregistrées. Quitter quand même ?')) return false;
    }
    ERP.garde = null;
    return true;
  }

  function aller(chemin, remplacer) {
    chemin = normaliser(chemin);
    if (chemin === S.chemin && !remplacer) return;
    if (!quitterPossible()) return;
    history[remplacer ? 'replaceState' : 'pushState'](null, '', chemin);
    S.chemin = chemin;
    document.body.classList.remove('sb-open');
    renderEcran();
    renderNav();
  }

  window.addEventListener('popstate', function () {
    var cible = normaliser(location.pathname);
    if (ERP.garde && ERP.garde() && !confirm('Des modifications ne sont pas enregistrées. Quitter quand même ?')) {
      history.pushState(null, '', S.chemin);
      return;
    }
    ERP.garde = null;
    S.chemin = cible;
    renderEcran();
    renderNav();
  });
  window.addEventListener('beforeunload', function (e) {
    if (ERP.garde && ERP.garde()) { e.preventDefault(); e.returnValue = ''; }
  });

  // ── Barre latérale ───────────────────────────────────────────────
  var ICO = {
    soleil: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    lune: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    sortie: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    retour: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>',
    loupe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  };

  function ico(nom, classe) {
    var s = h('span', {className: classe || 'msb-ico'});
    s.innerHTML = ICO[nom];  // constante du fichier, aucune donnée utilisateur
    return s;
  }

  function estClair() {
    return window.MySifaTheme ? window.MySifaTheme.isLight() : document.body.classList.contains('light');
  }

  function renderNav() {
    var actif = lienCourant();
    var menu = h('div', {className: 'msb-nav'},
      h('a', {className: 'logo', href: '/', title: 'Accueil ERP', onclick: function (e) { e.preventDefault(); aller('/'); }},
        h('img', {src: '/static/erp/erp_icon_192.png', alt: ''}),
        h('div', null,
          h('div', {className: 'logo-brand'}, 'My', h('span', {text: 'ERP'})),
          h('div', {className: 'logo-sub', text: 'SIFA'}))),
      h('button', {className: 'erp-recherche-btn', type: 'button', onclick: ouvrirRecherche, title: 'Rechercher (Ctrl+K)'},
        ico('loupe'), h('span', {text: 'Rechercher'}), h('kbd', {text: 'Ctrl K'})));
    NAV.forEach(function (g) {
      if (g.groupe) menu.appendChild(h('div', {className: 'msb-section'}, h('span', {text: g.groupe})));
      g.liens.forEach(function (l) {
        menu.appendChild(h('a', {
          className: 'nav-btn' + (actif && actif.lien === l ? ' active' : ''),
          href: l.chemin,
          onclick: function (e) { e.preventDefault(); aller(l.chemin); },
        }, l.libelle));
      });
    });

    var u = S.user || {};
    var cfg = window.ERP_CONFIG || {};
    var clair = estClair();
    var pied = h('div', {className: 'sidebar-bottom msb-footer'},
      cfg.mysifa ? h('a', {className: 'back-mysifa', href: cfg.mysifa},
        ico('retour'), 'Retour à ', h('span', {className: 'wm'}, 'My', h('span', {text: 'Sifa'}))) : null,
      h('div', {className: 'user-chip'},
        h('div', {className: 'uc-top'},
          u.avatar_url ? h('img', {className: 'uc-avatar', src: u.avatar_url, alt: ''}) : null,
          h('div', {className: 'uc-info'},
            h('div', {className: 'uc-name', text: u.nom || ''}),
            h('div', {className: 'uc-role', text: u.role || ''})))),
      h('button', {className: 'theme-btn', type: 'button', onclick: function () {
        if (window.MySifaTheme) window.MySifaTheme.toggleMode();
        renderNav();
      }}, ico(clair ? 'lune' : 'soleil', 'theme-ico'), h('span', {className: 'theme-label', text: clair ? 'Mode sombre' : 'Mode clair'})),
      h('button', {className: 'logout-btn', type: 'button', onclick: async function () {
        if (!quitterPossible()) return;
        try { await api('/api/auth/logout', {method: 'POST'}); } catch (e) { /* recharge quand même */ }
        location.href = '/';
      }}, ico('sortie'), 'Déconnexion'),
      h('div', {className: 'version', text: cfg.version || ''}));
    var nouveau = h('nav', {className: 'erp-nav'}, menu, pied);
    if (navEl && navEl.parentNode) {
      var defil = navEl.scrollTop;
      navEl.replaceWith(nouveau);
      nouveau.scrollTop = defil;
    }
    navEl = nouveau;
    return nouveau;
  }

  // ── Écran ────────────────────────────────────────────────────────
  var mainEl = null;

  function renderEcran() {
    var main = h('main', {className: 'erp-main'});
    var r = resoudre(S.chemin);
    var c = lienCourant();
    var titreEl = h('h1', {className: 'erp-titre'});
    var arianeEl = h('div', {className: 'erp-ariane'});
    var entete = h('div', {className: 'erp-entete'}, h('div', {className: 'erp-entete-txt'}, titreEl, arianeEl));
    var actionsEl = h('div', {className: 'erp-entete-actions'});
    entete.appendChild(actionsEl);
    function titre(t, ariane) {
      titreEl.textContent = t;
      arianeEl.textContent = ariane || (c && c.groupe ? c.groupe + ' › ' + (c.lien.libelle) : 'ERP SIFA');
      document.title = t + ' — ERP';
    }
    titre(c ? c.lien.libelle : (S.chemin === '/' ? 'Accueil' : 'Page introuvable'));
    main.appendChild(entete);
    if (r) {
      try {
        ERP.ecrans[r.cle](main, {api: api, h: h, aller: aller, S: S, param: r.param, titre: titre,
                                  actions: actionsEl, toast: toast});
      } catch (e) {
        main.appendChild(h('div', {className: 'erp-vide', text: 'Erreur d\'affichage : ' + e.message}));
        console.error(e);
      }
    } else {
      main.appendChild(h('div', {className: 'erp-vide', text: c ? 'Écran pas encore construit.' : 'Aucun écran à cette adresse.'}));
    }
    if (mainEl && mainEl.parentNode) mainEl.replaceWith(main);
    mainEl = main;
    return main;
  }

  function render() {
    var racine = document.getElementById('erp-app');
    racine.textContent = '';
    var topbar = h('div', {className: 'erp-topbar'},
      h('button', {className: 'erp-btn', type: 'button', onclick: function () { document.body.classList.toggle('sb-open'); }}, 'Menu'),
      h('b', {text: 'ERP'}));
    racine.appendChild(topbar);
    racine.appendChild(h('div', {className: 'erp-coque'}, renderNav(), renderEcran()));
  }

  // ── Recherche globale (Ctrl+K) ───────────────────────────────────
  var GENRES = {tiers: 'Tiers', article: 'Article', piece: 'Pièce'};

  function ouvrirRecherche() {
    var res = [], sel = 0, minuterie = null;
    var liste = h('div', {className: 'erp-rech-liste'});
    var inp = h('input', {className: 'erp-input erp-rech-input', placeholder: 'Client, fournisseur, article, n° de pièce, réf. client…', 'aria-label': 'Rechercher'});
    var fond = h('div', {className: 'erp-modal-fond', onclick: function (e) { if (e.target === fond) fermer(); }},
      h('div', {className: 'erp-modal erp-rech'}, inp, liste));
    function fermer() { fond.remove(); document.removeEventListener('keydown', clavier, true); }
    function ouvrir(r) {
      fermer();
      if (r.genre === 'tiers') aller((r.client ? '/fichiers/clients/' : '/fichiers/fournisseurs/') + r.id);
      else if (r.genre === 'article') aller('/fichiers/articles/' + r.id);
      else aller(ERP.cheminPiece(r.type, r.id));
    }
    function dessiner() {
      liste.textContent = '';
      if (!inp.value.trim()) { liste.appendChild(h('div', {className: 'erp-rech-vide', text: 'Deux caractères au moins.'})); return; }
      if (!res.length) { liste.appendChild(h('div', {className: 'erp-rech-vide', text: 'Aucun résultat pour « ' + inp.value.trim() + ' »'})); return; }
      res.forEach(function (r, i) {
        liste.appendChild(h('div', {className: 'erp-rech-item' + (i === sel ? ' sel' : ''), onclick: function () { ouvrir(r); }},
          h('span', {className: 'erp-rech-genre', text: r.genre === 'piece' ? ((ERP.types[r.type] || {}).libelle || 'Pièce') : GENRES[r.genre]}),
          h('b', {text: r.titre || ''}), h('span', {className: 'erp-rech-sous', text: r.sous || ''})));
      });
    }
    function clavier(e) {
      if (e.key === 'Escape') { e.preventDefault(); fermer(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(res.length - 1, sel + 1); dessiner(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(0, sel - 1); dessiner(); }
      else if (e.key === 'Enter' && res[sel]) { e.preventDefault(); ouvrir(res[sel]); }
    }
    inp.addEventListener('input', function () {
      clearTimeout(minuterie);
      minuterie = setTimeout(async function () {
        var q = inp.value.trim();
        if (q.length < 2) { res = []; dessiner(); return; }
        try { res = await api('/api/erp2/recherche?q=' + encodeURIComponent(q)); } catch (e) { res = []; }
        sel = 0; dessiner();
      }, 150);
    });
    document.addEventListener('keydown', clavier, true);
    document.body.appendChild(fond);
    dessiner();
    requestAnimationFrame(function () { inp.focus(); });
  }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); ouvrirRecherche(); }
  });

  var ERP = window.ERP = {
    ecrans: {}, api: api, h: h, aller: aller, S: S, toast: toast, ico: ico, garde: null,
    types: {},
    cheminPiece: function (type, id) { return '/'; },   // défini par erp_pieces.js
    rafraichir: function () { renderEcran(); },
  };

  // Premier rendu une fois tous les scripts chargés : les écrans
  // s'enregistrent après ce fichier.
  function demarrer() {
    render();
    api('/api/auth/me').then(function (u) { S.user = u; renderNav(); }).catch(function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();
