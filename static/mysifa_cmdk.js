/**
 * MySifa — Command Palette (⌘K / Ctrl+K).
 * Modal global accessible depuis n'importe quelle page.
 * v2 : prefetch idle, rendu instantané, event delegation, rAF-batched.
 */
(function () {
  'use strict';

  if (window.__MYSIFA_CMDK_LOADED__) return;
  window.__MYSIFA_CMDK_LOADED__ = true;

  var MAC = /Mac|iPod|iPhone|iPad/.test(navigator.platform || '');
  var KBD_LABEL = MAC ? '⌘ K' : 'Ctrl K';
  var KBD_SHORT = MAC ? '⌘K' : 'Ctrl K';
  var DEBOUNCE_MS = 180;
  var LOCAL_RENDER_DEBOUNCE_MS = 20;

  var state = {
    user: null,
    dossiers: null,
    overlay: null,
    list: null,
    input: null,
    items: [],           // built base items (apps + actions + machines)
    asyncItems: [],      // async items (products, emplacements, clients)
    filtered: [],
    activeIdx: 0,
    open: false,
    fetchingUser: null,
    fetchingDossiers: null,
    searchTimer: null,
    localRenderTimer: null,
    searchToken: 0,
    clientsAllowed: true,
    prefetched: false,
    lastRenderedHtml: '',
    inFlightAsync: null, // AbortController
  };

  // ───── Icônes (subset Lucide) - cache compilé ────────────────────
  var ICON_PATHS = {
    'edit': '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    'wrench': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    'printer': '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    'calculator': '<rect x="6" y="2.5" width="12" height="19" rx="2"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="9" y1="11" x2="10" y2="11"/><line x1="12" y1="11" x2="13" y2="11"/><line x1="15" y1="11" x2="16" y2="11"/><line x1="9" y1="14" x2="10" y2="14"/><line x1="12" y1="14" x2="13" y2="14"/><line x1="15" y1="14" x2="16" y2="14"/><line x1="9" y1="17" x2="10" y2="17"/><line x1="12" y1="17" x2="13" y2="17"/><line x1="15" y1="17" x2="16" y2="17"/>',
    'truck': '<path d="M3 7h11v10H3z"/><path d="M14 10h4l3 3v4h-7z"/><circle cx="7.5" cy="17" r="2"/><circle cx="17.5" cy="17" r="2"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
    'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    'palette': '<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
    'shield-check': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    'tool': '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'toolbox': '<rect x="2" y="8" width="20" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>',
    'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    'sliders': '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    'mail': '<path d="M4 6h16v12H4z"/><path d="M4 7l8 6 8-6"/>',
    'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    'database': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'home': '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 10v11h14V10"/><path d="M10 21v-6h4v6"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    'map-pin': '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    'building': '<rect x="4" y="2" width="16" height="20" rx="2"/><line x1="9" y1="22" x2="9" y2="18"/><line x1="15" y1="22" x2="15" y2="18"/><line x1="8" y1="6" x2="10" y2="6"/><line x1="14" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="10" y2="10"/><line x1="14" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="10" y2="14"/><line x1="14" y1="14" x2="16" y2="14"/>',
    'box': '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
    'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  };
  // Cache pré-compilé des SVG (évite la reconstruction par render)
  var ICON_SVG_16 = {};
  var ICON_SVG_18 = {};
  Object.keys(ICON_PATHS).forEach(function (k) {
    ICON_SVG_16[k] = _buildSvg(k, 16);
    ICON_SVG_18[k] = _buildSvg(k, 18);
  });
  function _buildSvg(name, size) {
    var inner = ICON_PATHS[name] || ICON_PATHS.search;
    return '<svg width="' + size + '" height="' + size +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      inner + '</svg>';
  }
  function svgIcon(name, size) {
    if (size === 16) return ICON_SVG_16[name] || ICON_SVG_16.folder;
    if (size === 18) return ICON_SVG_18[name] || ICON_SVG_18.folder;
    return _buildSvg(name, size || 16);
  }

  // ───── Rôles ─────────────────────────────────────────────────────
  function hasRole(user, allowed) {
    if (!allowed || allowed === '*') return true;
    if (!user) return false;
    var role = user.role || '';
    if (role === 'superadmin') return true;
    return allowed.split(',').indexOf(role) !== -1;
  }

  // ───── Cache fetches ─────────────────────────────────────────────
  function fetchUser() {
    if (state.user) return Promise.resolve(state.user);
    if (state.fetchingUser) return state.fetchingUser;
    state.fetchingUser = fetch('/api/auth/me', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        state.user = u || { role: '' };
        // reset items pour reflet le user au prochain open
        state.items = [];
        return state.user;
      })
      .catch(function () { state.user = { role: '' }; return state.user; });
    return state.fetchingUser;
  }

  function fetchDossiers() {
    if (state.dossiers) return Promise.resolve(state.dossiers);
    if (state.fetchingDossiers) return state.fetchingDossiers;
    state.fetchingDossiers = fetch('/api/filters', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : { dossiers: [] }; })
      .then(function (d) {
        state.dossiers = (d && Array.isArray(d.dossiers)) ? d.dossiers : [];
        return state.dossiers;
      })
      .catch(function () { state.dossiers = []; return state.dossiers; });
    return state.fetchingDossiers;
  }

  // Prefetch idle : warm cache dès que la page est disponible
  function prefetchIdle() {
    if (state.prefetched) return;
    state.prefetched = true;
    var run = function () {
      fetchUser().catch(function () {});
      fetchDossiers().catch(function () {});
    };
    if (window.requestIdleCallback) {
      window.requestIdleCallback(run, { timeout: 2000 });
    } else {
      setTimeout(run, 800);
    }
  }

  // ───── Items statiques (apps + actions + machines) ───────────────
  function buildBaseItems(user) {
    var role = (user && user.role) || '';
    var apps = [
      { type: 'app', title: 'Saisie Prod',     sub: 'Saisie opérateur — machine',     keywords: 'prod saisie operateur machine',       url: '/prod',        icon: 'edit',         roles: '*' },
      { type: 'app', title: 'MyProd',          sub: 'Suivi de production & planning',           keywords: 'production suivi planning',           url: '/planning',    icon: 'wrench',       roles: '*' },
      { type: 'app', title: 'MyStock',         sub: 'Gestion des stocks produits',              keywords: 'stock entrees sorties',               url: '/stock',       icon: 'package',      roles: '*' },
      { type: 'app', title: 'MyPrint',         sub: 'Étiquettes de traçabilité', keywords: 'print impression etiquette',          url: '/print',       icon: 'printer',      roles: '*' },
      { type: 'app', title: 'MyCompta',        sub: 'Comptabilité',                        keywords: 'compta comptabilite finance',         url: '/compta',      icon: 'calculator',   roles: 'direction,comptabilite' },
      { type: 'app', title: 'MyExpé',     sub: 'Expédition & suivi',                  keywords: 'expedition livraison transporteur',   url: '/expe',        icon: 'truck',        roles: '*' },
      { type: 'app', title: 'Planning RH',     sub: 'Planning personnel & congés',         keywords: 'rh personnel conges',                 url: '/planning-rh', icon: 'users',        roles: 'direction,administration' },
      { type: 'app', title: 'Coûts matières', sub: 'Matières, produits, €/m²', keywords: 'couts matieres prix pricing',         url: '/pricing',     icon: 'file-text',    roles: 'direction,commercial' },
      { type: 'app', title: 'MyAO',            sub: 'Appels d’offre fournisseurs',         keywords: 'ao appel offre fournisseur',          url: '/ao',          icon: 'clipboard',    roles: '*' },
      { type: 'app', title: 'MyBAT',           sub: 'Bons À Tirer — suivi client',    keywords: 'bat bon a tirer client',              url: '/bat',         icon: 'palette',      roles: '*' },
      { type: 'app', title: 'MyQualité',   sub: 'Non-conformités & audits',           keywords: 'qualite nc non conformite audit',     url: '/qualite',     icon: 'shield-check', roles: '*' },
      { type: 'app', title: 'Maintenance',     sub: 'Suivi et planification',                   keywords: 'maintenance interventions',           url: '/maintenance', icon: 'toolbox',         roles: '*' },
    ];
    var actions = [
      { type: 'action', title: 'Retour au portail',                  sub: 'Page d’accueil',              keywords: 'portail accueil home',       url: '/',          icon: 'home',     roles: '*' },
      { type: 'action', title: 'Mon profil',                         sub: 'Préférences, mot de passe', keywords: 'profil compte preferences',  url: '/profil',    icon: 'user',     roles: '*' },
      { type: 'action', title: 'Paramètres',                    sub: 'Comptes, rôles, annonces',    keywords: 'settings parametres reglages',url: '/settings',  icon: 'sliders',  roles: 'direction' },
      { type: 'action', title: 'Messagerie',                         sub: 'Discussions et notifications',     keywords: 'messages chat',              url: '/messages',  icon: 'mail',     roles: 'superadmin' },
      { type: 'action', title: 'Calendrier',                         sub: 'Agenda partagé',              keywords: 'calendrier agenda',          url: '/calendrier',icon: 'calendar', roles: 'direction,administration' },
      { type: 'action', title: 'Base de données',               sub: 'Visualisation des tables',         keywords: 'db database sqlite tables',  url: '/db',        icon: 'database', roles: 'direction' },
      { type: 'action', title: 'Basculer le thème clair/sombre', sub: 'Inverser le mode visuel',     keywords: 'theme dark light sombre clair mode', action: 'toggle-theme', icon: 'moon', roles: '*' },
      { type: 'action', title: 'Déconnexion',                   sub: 'Fermer la session en cours',       keywords: 'logout deconnexion',         action: 'logout',  icon: 'log-out',  roles: '*' },
    ];
    var machines = [
      { type: 'machine', title: 'Cohésio 1', sub: 'Planning machine — Cohésio 1', keywords: 'cohesio 1 machine planning', url: '/planning?machine=1', icon: 'layers', roles: '*' },
      { type: 'machine', title: 'Cohésio 2', sub: 'Planning machine — Cohésio 2', keywords: 'cohesio 2 machine planning', url: '/planning?machine=2', icon: 'layers', roles: '*' },
      { type: 'machine', title: 'DSI',           sub: 'Planning machine — DSI',           keywords: 'dsi machine planning',           url: '/planning?machine=3', icon: 'layers', roles: '*' },
      { type: 'machine', title: 'Repiquage',     sub: 'Planning machine — Repiquage',     keywords: 'repiquage machine planning',     url: '/planning?machine=4', icon: 'layers', roles: '*' },
    ];
    var out = [];
    apps.forEach(function (a) { if (hasRole(user, a.roles)) out.push(a); });
    actions.forEach(function (a) { if (hasRole(user, a.roles)) out.push(a); });
    machines.forEach(function (m) { if (hasRole(user, m.roles)) out.push(m); });
    return out;
  }

  function dossierItems(qRaw) {
    if (!state.dossiers || !state.dossiers.length) return [];
    var q = normalize(qRaw).trim();
    if (!q) return [];
    var out = [];
    for (var i = 0; i < state.dossiers.length && out.length < 6; i++) {
      var no = String(state.dossiers[i] || '');
      if (!no) continue;
      if (normalize(no).indexOf(q) !== -1) {
        out.push({
          type: 'dossier',
          title: 'Dossier ' + no,
          sub: 'Ouvrir dans MyProd',
          keywords: no,
          url: '/planning?q=' + encodeURIComponent(no),
          icon: 'folder',
        });
      }
    }
    return out;
  }

  // ───── Async items : produits, emplacements, clients ─────────────
  function searchAsync(qRaw) {
    var token = ++state.searchToken;
    var q = (qRaw || '').trim();
    if (state.inFlightAsync && typeof state.inFlightAsync.abort === 'function') {
      try { state.inFlightAsync.abort(); } catch (e) {}
    }
    state.asyncItems = [];
    if (q.length < 2) { renderIfActive(token); return; }
    var ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    state.inFlightAsync = ctrl;
    var opts = { credentials: 'include' };
    if (ctrl) opts.signal = ctrl.signal;
    var encQ = encodeURIComponent(q);

    var pStock = fetch('/api/stock/search?q=' + encQ + '&limit=6', opts)
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
    var pClients = state.clientsAllowed
      ? fetch('/api/clients?search=' + encQ + '&limit=6', opts)
        .then(function (r) {
          if (r.status === 403 || r.status === 401) { state.clientsAllowed = false; return null; }
          return r.ok ? r.json() : null;
        })
        .catch(function () { return null; })
      : Promise.resolve(null);

    Promise.all([pStock, pClients]).then(function (results) {
      if (token !== state.searchToken) return;
      var stock = results[0] || {};
      var clients = results[1] || {};
      var items = [];

      var produits = Array.isArray(stock.produits) ? stock.produits : [];
      produits.forEach(function (p) {
        var ref = (p.reference || '').trim();
        if (!ref) return;
        var desig = (p.designation || '').trim();
        var stockTxt = (p.stock_total != null && p.stock_total !== '') ? (p.stock_total + ' ' + (p.unite || 'u')) : '';
        var subBase = desig || '—';
        items.push({ type: 'ref-stock', title: 'Stock — ' + ref,
          sub: subBase + (stockTxt ? ' · ' + stockTxt + ' en stock' : ''),
          keywords: ref + ' ' + desig + ' stock',
          url: '/stock?tab=produits-finis' + (p.id ? '&produit=' + p.id : '&ref=' + encodeURIComponent(ref)),
          icon: 'package' });
        items.push({ type: 'ref-fiche', title: 'Fiche technique — ' + ref, sub: subBase,
          keywords: ref + ' ' + desig + ' fiche technique',
          url: '/planning?q=' + encodeURIComponent(ref) + '&fiche=1', icon: 'file-text' });
        items.push({ type: 'ref-dossier', title: 'Dossier de fabrication — ' + ref, sub: subBase + ' · Planning de production',
          keywords: ref + ' ' + desig + ' dossier fabrication',
          url: '/planning?q=' + encodeURIComponent(ref), icon: 'wrench' });
      });

      var empls = Array.isArray(stock.emplacements) ? stock.emplacements : [];
      empls.forEach(function (e) {
        var code = (e.emplacement || '').trim();
        if (!code) return;
        var sub = (e.nb_refs != null && e.nb_refs !== '')
          ? (e.nb_refs + ' réf · ' + (e.total_unites || 0) + ' u')
          : 'Plan d’entrepôt';
        items.push({ type: 'emplacement', title: 'Emplacement ' + code, sub: sub,
          keywords: code + ' emplacement zone',
          url: '/stock?tab=plan-entrepot&emplacement=' + encodeURIComponent(code), icon: 'map-pin' });
      });

      var clientItems = Array.isArray(clients.items) ? clients.items : [];
      clientItems.forEach(function (c) {
        var name = (c.raison_sociale || c.code || '').trim();
        if (!name) return;
        var sub = [];
        if (c.code) sub.push(c.code);
        if (c.ville) sub.push(c.ville);
        items.push({ type: 'client', title: name, sub: 'Client · ' + (sub.length ? sub.join(' — ') : 'Dossiers de production'),
          keywords: name + ' ' + (c.code || '') + ' ' + (c.ville || '') + ' client',
          url: '/planning?q=' + encodeURIComponent(name), icon: 'building' });
      });

      var dateItem = parseDateQuery(q);
      if (dateItem) items.unshift(dateItem);

      state.asyncItems = items;
      renderIfActive(token);
    }).catch(function () {});
  }

  function parseDateQuery(q) {
    var qn = (q || '').toLowerCase().trim();
    var today = new Date(); today.setHours(0,0,0,0);
    function fmtIso(d){return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());}
    function pad(n){return n<10?('0'+n):(''+n);}
    var d = null, label = null;
    if (qn === 'aujourd’hui' || qn === "aujourd'hui" || qn === 'today' || qn === 'auj') {
      d = today; label = 'Aujourd’hui';
    } else if (qn === 'demain' || qn === 'tomorrow') {
      d = new Date(today.getTime()+86400000); label = 'Demain';
    } else if (qn === 'hier' || qn === 'yesterday') {
      d = new Date(today.getTime()-86400000); label = 'Hier';
    } else {
      var m = qn.match(/^(\d{1,2})[\/.\-](\d{1,2})(?:[\/.\-](\d{2,4}))?$/);
      if (m) {
        var day = parseInt(m[1],10), mon = parseInt(m[2],10), yr = m[3]?parseInt(m[3],10):today.getFullYear();
        if (yr < 100) yr += 2000;
        if (day>=1 && day<=31 && mon>=1 && mon<=12) {
          d = new Date(yr, mon-1, day);
          if (!isNaN(d.getTime())) label = pad(day)+'/'+pad(mon)+'/'+yr;
        }
      }
    }
    if (!d) return null;
    return { type: 'date', title: 'Planning du ' + label, sub: 'Sauter à cette date dans MyProd',
      keywords: 'date jour planning ' + label,
      url: '/planning?date=' + fmtIso(d), icon: 'calendar' };
  }

  // ───── Normalisation + score ─────────────────────────────────────
  function normalize(s) {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function scoreItem(item, qNorm) {
    if (!qNorm) return 1;
    var hay = normalize(item.title + ' ' + (item.sub || '') + ' ' + (item.keywords || ''));
    var titleNorm = normalize(item.title);
    if (titleNorm.indexOf(qNorm) === 0) return 100;
    if (titleNorm.indexOf(qNorm) !== -1) return 80;
    if (hay.indexOf(qNorm) !== -1) return 40;
    var i = 0;
    for (var k = 0; k < qNorm.length; k++) {
      var p = hay.indexOf(qNorm[k], i);
      if (p === -1) return 0;
      i = p + 1;
    }
    return 8;
  }

  function filterItems(q) {
    var qNorm = normalize(q).trim();
    var base = state.items.slice();
    var prepend = [];
    if (/\d/.test(qNorm)) prepend = prepend.concat(dossierItems(q));
    if (state.asyncItems && state.asyncItems.length) prepend = prepend.concat(state.asyncItems);
    if (!qNorm) return base;
    var scored = [];
    var combined = prepend.concat(base);
    for (var i = 0; i < combined.length; i++) {
      var s = scoreItem(combined[i], qNorm);
      if (s > 0) scored.push({ item: combined[i], score: s, idx: i });
    }
    scored.sort(function (a, b) { return b.score - a.score || a.idx - b.idx; });
    return scored.map(function (s) { return s.item; });
  }

  // ───── DOM ───────────────────────────────────────────────────────
  function buildDom() {
    if (state.overlay) return;
    var ov = document.createElement('div');
    ov.id = 'cmdk-overlay';
    ov.setAttribute('role', 'dialog');
    ov.setAttribute('aria-modal', 'true');
    ov.setAttribute('aria-label', 'Palette de commandes');
    ov.innerHTML =
      '<div class="cmdk-modal" role="document">' +
      '  <div class="cmdk-search">' +
      '    <span class="cmdk-search-ico">' + svgIcon('search', 18) + '</span>' +
      '    <input type="text" autocomplete="off" spellcheck="false" placeholder="Référence, emplacement, client, dossier, date…">' +
      '    <span class="cmdk-search-kbd">Esc</span>' +
      '    <button type="button" class="cmdk-close-btn" aria-label="Fermer">' +
      '      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
      '    </button>' +
      '  </div>' +
      '  <div class="cmdk-list" role="listbox"></div>' +
      '  <div class="cmdk-footer">' +
      '    <span class="cmdk-footer-hint"><kbd>↑</kbd><kbd>↓</kbd> Naviguer</span>' +
      '    <span class="cmdk-footer-hint"><kbd>↵</kbd> Ouvrir</span>' +
      '    <span class="cmdk-footer-hint"><kbd>Esc</kbd> Fermer</span>' +
      '    <span class="cmdk-footer-spacer"></span>' +
      '    <span class="cmdk-footer-brand">MySifa</span>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(ov);
    state.overlay = ov;
    state.list = ov.querySelector('.cmdk-list');
    state.input = ov.querySelector('.cmdk-search input');

    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    var closeBtn = ov.querySelector('.cmdk-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', function (e) { e.preventDefault(); close(); });

    // Event delegation pour clic/hover sur les lignes (une seule fois)
    state.list.addEventListener('click', function (e) {
      var row = e.target.closest && e.target.closest('.cmdk-row');
      if (!row) return;
      state.activeIdx = parseInt(row.getAttribute('data-idx'), 10) || 0;
      executeActive();
    });
    state.list.addEventListener('mousemove', function (e) {
      var row = e.target.closest && e.target.closest('.cmdk-row');
      if (!row) return;
      var idx = parseInt(row.getAttribute('data-idx'), 10);
      if (idx !== state.activeIdx) {
        state.activeIdx = idx;
        updateActiveClasses();
      }
    });

    state.input.addEventListener('input', function () {
      var q = state.input.value;
      // Rendu local rAF-batched
      if (state.localRenderTimer) cancelAnimationFrame(state.localRenderTimer);
      state.localRenderTimer = requestAnimationFrame(function () {
        state.filtered = filterItems(q);
        state.activeIdx = 0;
        render();
      });
      // Recherche async debounced
      if (state.searchTimer) clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(function () { searchAsync(q); }, DEBOUNCE_MS);
    });
    state.input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape')      { e.preventDefault(); close(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
      else if (e.key === 'ArrowUp')   { e.preventDefault(); moveActive(-1); }
      else if (e.key === 'Enter')     { e.preventDefault(); executeActive(); }
    });
  }

  function renderIfActive(token) {
    if (token !== state.searchToken) return;
    state.filtered = filterItems(state.input ? state.input.value : '');
    if (state.activeIdx >= state.filtered.length) state.activeIdx = 0;
    render();
  }

  function render() {
    if (!state.list) return;
    if (!state.filtered.length) {
      var empty = '<div class="cmdk-empty">Aucun résultat pour <b>' +
        escapeHtml(state.input.value) + '</b>.</div>';
      if (empty === state.lastRenderedHtml) return;
      state.list.innerHTML = empty;
      state.lastRenderedHtml = empty;
      return;
    }
    var html = '';
    var lastSection = null;
    var items = state.filtered;
    for (var idx = 0; idx < items.length; idx++) {
      var item = items[idx];
      var section = sectionFor(item);
      if (section !== lastSection) {
        html += '<div class="cmdk-section">' + section + '</div>';
        lastSection = section;
      }
      html += '<button type="button" class="cmdk-row' +
        (idx === state.activeIdx ? ' cmdk-active' : '') +
        '" data-idx="' + idx + '" role="option" aria-selected="' +
        (idx === state.activeIdx ? 'true' : 'false') + '">' +
        '<span class="cmdk-row-ico">' + svgIcon(item.icon || 'folder', 16) + '</span>' +
        '<span class="cmdk-row-body">' +
        '<span class="cmdk-row-title">' + escapeHtml(item.title) + '</span>' +
        (item.sub ? '<span class="cmdk-row-sub">' + escapeHtml(item.sub) + '</span>' : '') +
        '</span>' +
        '</button>';
    }
    if (html === state.lastRenderedHtml) return;
    state.list.innerHTML = html;
    state.lastRenderedHtml = html;
    scrollActiveIntoView();
  }

  function updateActiveClasses() {
    if (!state.list) return;
    var rows = state.list.querySelectorAll('.cmdk-row');
    for (var i = 0; i < rows.length; i++) {
      var idx = parseInt(rows[i].getAttribute('data-idx'), 10);
      var isActive = (idx === state.activeIdx);
      rows[i].classList.toggle('cmdk-active', isActive);
      rows[i].setAttribute('aria-selected', isActive ? 'true' : 'false');
    }
    scrollActiveIntoView();
  }
  function scrollActiveIntoView() {
    if (!state.list) return;
    var row = state.list.querySelector('.cmdk-row.cmdk-active');
    if (row && row.scrollIntoView) row.scrollIntoView({ block: 'nearest' });
  }
  function sectionFor(item) {
    switch (item.type) {
      case 'ref-stock':
      case 'ref-fiche':
      case 'ref-dossier': return 'Références produit';
      case 'emplacement': return 'Emplacements';
      case 'client':      return 'Clients';
      case 'dossier':     return 'Dossiers';
      case 'date':        return 'Dates';
      case 'machine':     return 'Machines';
      case 'app':         return 'Applications';
      default:            return 'Actions rapides';
    }
  }
  function moveActive(delta) {
    if (!state.filtered.length) return;
    state.activeIdx = (state.activeIdx + delta + state.filtered.length) % state.filtered.length;
    updateActiveClasses();
  }
  function executeActive() {
    var item = state.filtered[state.activeIdx];
    if (!item) return;
    close();
    if (item.action === 'toggle-theme') {
      try {
        if (window.MySifaTheme && typeof window.MySifaTheme.toggleMode === 'function') {
          window.MySifaTheme.toggleMode();
          if (typeof window.render === 'function') window.render();
        }
      } catch (e) {}
      return;
    }
    if (item.action === 'logout') {
      fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
        .catch(function () {})
        .then(function () { window.location.href = '/'; });
      return;
    }
    if (item.url) window.location.href = item.url;
  }
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ───── Open / Close ──────────────────────────────────────────────
  function open(prefill) {
    if (state.open) return;
    buildDom();
    state.open = true;
    state.overlay.classList.add('cmdk-open');
    document.body.classList.add('cmdk-locked');

    // 1. Rendu instantané avec cache si dispo (aucune attente réseau)
    state.input.value = prefill || '';
    state.asyncItems = [];
    state.lastRenderedHtml = '';
    if (!state.items.length && state.user) {
      state.items = buildBaseItems(state.user);
    }
    if (state.items.length) {
      state.filtered = filterItems(state.input.value);
      state.activeIdx = 0;
      render();
    } else {
      // Skeleton minimal en attendant fetchUser
      state.list.innerHTML = '<div class="cmdk-empty">Chargement…</div>';
      state.lastRenderedHtml = state.list.innerHTML;
    }
    // Focus immédiat (pas dans un setTimeout)
    state.input.focus();

    // 2. Hydratation asynchrone : quand user/dossiers sont prêts, on re-render
    Promise.all([fetchUser(), fetchDossiers()]).then(function () {
      if (!state.open) return;
      state.items = buildBaseItems(state.user);
      state.filtered = filterItems(state.input.value);
      if (state.activeIdx >= state.filtered.length) state.activeIdx = 0;
      render();
      if (state.input.value) searchAsync(state.input.value);
    });
  }
  function close() {
    if (!state.open || !state.overlay) return;
    state.open = false;
    state.overlay.classList.remove('cmdk-open');
    document.body.classList.remove('cmdk-locked');
    if (state.inFlightAsync && typeof state.inFlightAsync.abort === 'function') {
      try { state.inFlightAsync.abort(); } catch (e) {}
    }
  }

  // ───── Hooks globaux ─────────────────────────────────────────────
  function isEditableTarget(t) {
    if (!t) return false;
    var tag = (t.tagName || '').toUpperCase();
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if (t.isContentEditable) return true;
    return false;
  }
  function onKeydown(e) {
    var key = (e.key || '').toLowerCase();
    var modCmd = MAC ? e.metaKey : e.ctrlKey;
    var modOther = MAC ? e.ctrlKey : e.metaKey;
    if (key === 'k' && modCmd && !modOther && !e.altKey) {
      e.preventDefault();
      if (state.open) close(); else open('');
      return;
    }
    if (key === 'escape' && state.open) { e.preventDefault(); close(); }
  }
  document.addEventListener('keydown', onKeydown, true);

  window.MysifaCmdK = { open: open, close: close, toggle: function(prefill){ if(state.open) close(); else open(prefill||''); }, isOpen: function(){ return !!state.open; }, label: KBD_LABEL, shortLabel: KBD_SHORT };

  // Event delegation globale pour [data-cmdk-open] et [data-cmdk-label]
  // Plus économe qu'un MutationObserver sur documentElement.
  function onDelegatedClick(e) {
    var el = e.target && e.target.closest && e.target.closest('[data-cmdk-open]');
    if (!el) return;
    e.preventDefault();
    open('');
  }
  document.addEventListener('click', onDelegatedClick, true);

  // Prefetch idle : warm user + dossiers dès que la page est disponible.
  // Le MutationObserver global a été supprimé (grosse charge sur pages riches) :
  //  - [data-cmdk-open]  → event delegation ci-dessus, aucune liaison par élément.
  //  - [data-cmdk-label] → aucun usage dans l'app (les badges sont écrits par html.py directement).
  function onReady() { prefetchIdle(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onReady);
  else onReady();
})();
