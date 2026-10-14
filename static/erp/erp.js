/* Nouvel ERP — coque : navigation, routage par chemin, session.
 *
 * Toutes les URL de erp.mysifa.com renvoient la même page ; ce script lit le
 * chemin réel (location.pathname) et affiche l'écran correspondant. Les écrans
 * métier s'enregistrent dans ERP.ecrans[chemin] au fil des lots.
 */
(function () {
  'use strict';

  // Navigation par domaine. `lot` renvoie au lot de docs/erp/ROADMAP.md qui
  // construit l'écran : affiché tant que l'écran n'existe pas.
  var NAV = [
    {groupe: null, liens: [{chemin: '/', libelle: 'Accueil'}]},
    {groupe: 'Ventes', liens: [
      {chemin: '/ventes/devis', libelle: 'Devis'},
      {chemin: '/ventes/marches', libelle: 'Marchés'},
      {chemin: '/ventes/commandes', libelle: 'Commandes'},
      {chemin: '/ventes/livraisons', libelle: 'Livraisons'},
      {chemin: '/ventes/factures', libelle: 'Factures'},
    ]},
    {groupe: 'Achats', liens: [
      {chemin: '/achats/commandes', libelle: 'Commandes fournisseur'},
      {chemin: '/achats/receptions', libelle: 'Réceptions'},
      {chemin: '/achats/factures', libelle: 'Factures fournisseur'},
    ]},
    {groupe: 'Stocks', liens: [
      {chemin: '/stocks/matieres', libelle: 'Matières premières'},
      {chemin: '/stocks/produits-finis', libelle: 'Produits finis'},
      {chemin: '/stocks/mouvements', libelle: 'Mouvements'},
    ]},
    {groupe: 'Production', liens: [
      {chemin: '/production/ordres', libelle: 'Ordres de fabrication'},
    ]},
    {groupe: 'Comptabilité', liens: [
      {chemin: '/compta/echeances', libelle: 'Échéances'},
      {chemin: '/compta/reglements', libelle: 'Règlements'},
      {chemin: '/compta/exports', libelle: 'Exports comptables'},
    ]},
    {groupe: 'Fichiers', liens: [
      {chemin: '/fichiers/clients', libelle: 'Clients'},
      {chemin: '/fichiers/fournisseurs', libelle: 'Fournisseurs'},
      {chemin: '/fichiers/articles', libelle: 'Articles'},
    ]},
    {groupe: 'Paramètres', liens: [
      {chemin: '/parametres', libelle: 'Paramètres'},
    ]},
  ];

  var S = {chemin: location.pathname.replace(/\/+$/, '') || '/', user: null};

  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') el.textContent = attrs[k];
      else if (k === 'className') el.className = attrs[k];
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k]);
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null || c === false) continue;
      el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return el;
  }

  async function api(path, options) {
    var o = Object.assign({credentials: 'same-origin', headers: {}}, options || {});
    if (o.body && typeof o.body !== 'string') {
      o.headers['Content-Type'] = 'application/json';
      o.body = JSON.stringify(o.body);
    }
    var r = await fetch(path, o);
    if (r.status === 401) { location.reload(); throw new Error('Session expirée'); }
    var data = null;
    try { data = await r.json(); } catch (e) { /* réponse vide */ }
    if (!r.ok) throw new Error((data && data.detail) || ('Erreur ' + r.status));
    return data;
  }

  function lienCourant() {
    for (var i = 0; i < NAV.length; i++)
      for (var j = 0; j < NAV[i].liens.length; j++)
        if (NAV[i].liens[j].chemin === S.chemin) return {groupe: NAV[i].groupe, lien: NAV[i].liens[j]};
    return null;
  }

  function aller(chemin) {
    if (chemin === S.chemin) return;
    history.pushState(null, '', chemin);
    S.chemin = chemin;
    document.body.classList.remove('sb-open');
    render();
  }

  function renderNav() {
    var nav = h('nav', {className: 'erp-nav'},
      h('a', {className: 'erp-logo', href: '/', title: 'Accueil ERP', onclick: function (e) { e.preventDefault(); aller('/'); }},
        'ERP', h('span', {text: '·'}), 'SIFA'));
    NAV.forEach(function (g) {
      if (g.groupe) nav.appendChild(h('div', {className: 'erp-nav-groupe', text: g.groupe}));
      g.liens.forEach(function (l) {
        nav.appendChild(h('a', {
          className: 'erp-nav-lien' + (l.chemin === S.chemin ? ' actif' : ''),
          href: l.chemin,
          onclick: function (e) { e.preventDefault(); aller(l.chemin); },
        }, l.libelle));
      });
    });
    var u = S.user || {};
    nav.appendChild(h('div', {className: 'erp-nav-pied'},
      h('div', {className: 'erp-nav-user'}, h('b', {text: u.nom || ''}), h('small', {text: u.role || ''})),
      h('button', {className: 'erp-btn', type: 'button', onclick: function () {
        if (window.MySifaTheme) window.MySifaTheme.toggleMode();
      }}, 'Thème clair / sombre'),
      h('button', {className: 'erp-btn', type: 'button', onclick: async function () {
        try { await api('/api/auth/logout', {method: 'POST'}); } catch (e) { /* recharge quand même */ }
        location.href = '/';
      }}, 'Déconnexion'),
      h('div', {className: 'erp-nav-version', text: (window.ERP_CONFIG || {}).version || ''})));
    return nav;
  }

  function renderEcran() {
    var main = h('main', {className: 'erp-main'});
    var ecran = ERP.ecrans[S.chemin];
    var c = lienCourant();
    var titre = c ? c.lien.libelle : (S.chemin === '/' ? 'Accueil' : 'Page introuvable');
    document.title = titre + ' — ERP';
    main.appendChild(h('h1', {className: 'erp-titre', text: titre}));
    main.appendChild(h('div', {className: 'erp-ariane', text: c && c.groupe ? c.groupe + ' › ' + titre : 'ERP SIFA'}));
    if (ecran) {
      ecran(main, {api: api, h: h, aller: aller, S: S});
    } else if (S.chemin === '/') {
      main.appendChild(h('div', {className: 'erp-vide'},
        h('b', {text: 'ERP en construction.'}),
        ' Les modules apparaissent ici au fil de la feuille de route.'));
    } else {
      main.appendChild(h('div', {className: 'erp-vide', text: c ? 'Écran pas encore construit.' : 'Aucun écran à cette adresse.'}));
    }
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

  window.addEventListener('popstate', function () {
    S.chemin = location.pathname.replace(/\/+$/, '') || '/';
    render();
  });

  var ERP = window.ERP = {ecrans: {}, api: api, h: h, aller: aller, S: S};

  api('/api/auth/me').then(function (u) { S.user = u; render(); })
    .catch(function () { render(); });
  render();
})();
