/**
 * MySifa — Command Palette (⌘K / Ctrl+K).
 * Modal global accessible depuis n'importe quelle page :
 *   - changement d'application (filtré par rôle)
 *   - actions rapides (thème, profil, paramètres, déconnexion, retour portail)
 *   - recherche de dossier (n° dossier dans /api/filters)
 * Auto-init au DOMContentLoaded ; injection paresseuse du DOM à la première ouverture.
 */
(function () {
  'use strict';

  if (window.__MYSIFA_CMDK_LOADED__) return;
  window.__MYSIFA_CMDK_LOADED__ = true;

  var MAC = /Mac|iPod|iPhone|iPad/.test(navigator.platform || '');
  var KBD_LABEL = MAC ? '⌘ K' : 'Ctrl K';
  var KBD_SHORT = MAC ? '⌘K' : 'Ctrl K';

  var state = {
    user: null,
    dossiers: null,
    overlay: null,
    list: null,
    input: null,
    items: [],
    filtered: [],
    activeIdx: 0,
    open: false,
    fetchingUser: null,
    fetchingDossiers: null,
  };

  // ────────────────────────────────────────────────────────
  // ICONS — petite map locale (subset Lucide) pour pas dépendre de html.py
  // ────────────────────────────────────────────────────────
  var ICONS = {
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
  };
  function svgIcon(name, size) {
    size = size || 16;
    var inner = ICONS[name] || ICONS.search;
    return '<svg width="' + size + '" height="' + size +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      inner + '</svg>';
  }

  // ────────────────────────────────────────────────────────
  // ROLE LOGIC
  // ────────────────────────────────────────────────────────
  function hasRole(user, allowed) {
    if (!allowed || allowed === '*') return true;
    if (!user) return false;
    var role = user.role || '';
    if (role === 'superadmin') return true;
    return allowed.split(',').indexOf(role) !== -1;
  }

  function fetchUser() {
    if (state.user) return Promise.resolve(state.user);
    if (state.fetchingUser) return state.fetchingUser;
    state.fetchingUser = fetch('/api/auth/me', { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        state.user = u || { role: '' };
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

  // ────────────────────────────────────────────────────────
  // ITEMS — apps, actions, recherche dossier
  // ────────────────────────────────────────────────────────
  function buildBaseItems(user) {
    var role = (user && user.role) || '';
    var isSuper = role === 'superadmin';
    var isDirection = role === 'direction';
    var canPlanning = isSuper || isDirection || role === 'administration';

    var apps = [
      { type: 'app', title: 'Saisie Prod',   sub: 'Saisie opérateur — machine',           keywords: 'prod saisie operateur machine',     url: '/prod',          icon: 'edit',         roles: '*' },
      { type: 'app', title: 'MyProd',        sub: 'Suivi de production & planning',                 keywords: 'production suivi planning',         url: '/planning',      icon: 'wrench',       roles: '*' },
      { type: 'app', title: 'MyStock',       sub: 'Gestion des stocks produits',                    keywords: 'stock entrees sorties',             url: '/stock',         icon: 'package',      roles: '*' },
      { type: 'app', title: 'MyPrint',       sub: 'Étiquettes de traçabilité',       keywords: 'print impression etiquette',        url: '/print',         icon: 'printer',      roles: '*' },
      { type: 'app', title: 'MyCompta',      sub: 'Comptabilité',                              keywords: 'compta comptabilite finance',       url: '/compta',        icon: 'calculator',   roles: 'direction,comptabilite' },
      { type: 'app', title: 'MyExpé',   sub: 'Expédition & suivi',                        keywords: 'expedition livraison transporteur', url: '/expe',          icon: 'truck',        roles: '*' },
      { type: 'app', title: 'Planning RH',   sub: 'Planning personnel & congés',               keywords: 'rh personnel conges',               url: '/planning-rh',   icon: 'users',        roles: 'direction,administration' },
      { type: 'app', title: 'Coûts matières', sub: 'Matières, produits, €/m²', keywords: 'couts matieres prix pricing',     url: '/pricing',       icon: 'file-text',    roles: 'direction,commercial' },
      { type: 'app', title: 'MyAO',          sub: 'Appels d’offre fournisseurs',               keywords: 'ao appel offre fournisseur',        url: '/ao',            icon: 'clipboard',    roles: '*' },
      { type: 'app', title: 'MyBAT',         sub: 'Bons À Tirer — suivi client',          keywords: 'bat bon a tirer client',            url: '/bat',           icon: 'palette',      roles: '*' },
      { type: 'app', title: 'MyQualité', sub: 'Non-conformités & audits',                 keywords: 'qualite nc non conformite audit',   url: '/qualite',       icon: 'shield-check', roles: '*' },
      { type: 'app', title: 'Maintenance',   sub: 'Suivi et planification',                         keywords: 'maintenance interventions',         url: '/maintenance',   icon: 'tool',         roles: '*' },
    ];

    var actions = [
      { type: 'action', title: 'Retour au portail',    sub: 'Page d’accueil',                  keywords: 'portail accueil home',     url: '/',          icon: 'home',     roles: '*' },
      { type: 'action', title: 'Mon profil',           sub: 'Préférences, mot de passe',  keywords: 'profil compte preferences', url: '/profil',    icon: 'user',     roles: '*' },
      { type: 'action', title: 'Paramètres',      sub: 'Comptes, rôles, annonces',        keywords: 'settings parametres reglages', url: '/settings', icon: 'sliders', roles: 'direction' },
      { type: 'action', title: 'Messagerie',           sub: 'Discussions et notifications',         keywords: 'messages chat',            url: '/messages',  icon: 'mail',     roles: 'superadmin' },
      { type: 'action', title: 'Calendrier',           sub: 'Agenda partagé',                  keywords: 'calendrier agenda',        url: '/calendrier', icon: 'calendar', roles: 'direction,administration' },
      { type: 'action', title: 'Base de données', sub: 'Visualisation des tables',             keywords: 'db database sqlite tables', url: '/db',       icon: 'database', roles: 'direction' },
      { type: 'action', title: 'Basculer le thème clair/sombre', sub: 'Inverser le mode visuel', keywords: 'theme dark light sombre clair mode', action: 'toggle-theme', icon: 'moon', roles: '*' },
      { type: 'action', title: 'Déconnexion',     sub: 'Fermer la session en cours',           keywords: 'logout deconnexion',       action: 'logout',  icon: 'log-out',  roles: '*' },
    ];

    var visible = [];
    apps.forEach(function (a) { if (hasRole(user, a.roles)) visible.push(a); });
    actions.forEach(function (a) { if (hasRole(user, a.roles)) visible.push(a); });
    return visible;
  }

  function dossierItems(qRaw) {
    if (!state.dossiers || !state.dossiers.length) return [];
    var q = normalize(qRaw).trim();
    if (!q) return [];
    var out = [];
    for (var i = 0; i < state.dossiers.length && out.length < 8; i++) {
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

  // ────────────────────────────────────────────────────────
  // FILTER (fuzzy subsequence + score)
  // ────────────────────────────────────────────────────────
  function normalize(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function scoreItem(item, qNorm) {
    if (!qNorm) return 1;
    var hay = normalize(item.title + ' ' + (item.sub || '') + ' ' + (item.keywords || ''));
    if (hay.indexOf(qNorm) !== -1) {
      // direct substring → high score, boost if matches title prefix
      var titleNorm = normalize(item.title);
      if (titleNorm.indexOf(qNorm) === 0) return 100;
      if (titleNorm.indexOf(qNorm) !== -1) return 60;
      return 30;
    }
    // subsequence match
    var i = 0, count = 0;
    for (var k = 0; k < qNorm.length; k++) {
      var ch = qNorm[k];
      var p = hay.indexOf(ch, i);
      if (p === -1) return 0;
      i = p + 1;
      count++;
    }
    return count >= qNorm.length ? 8 : 0;
  }
  function filterItems(q) {
    var qNorm = normalize(q).trim();
    var base = state.items.slice();
    // recherche dossier si le query contient au moins un chiffre
    if (/\d/.test(qNorm)) {
      var doss = dossierItems(q);
      // mettre les dossiers en haut
      base = doss.concat(base);
    }
    if (!qNorm) return base;
    var scored = [];
    for (var i = 0; i < base.length; i++) {
      var s = scoreItem(base[i], qNorm);
      if (s > 0) scored.push({ item: base[i], score: s, idx: i });
    }
    scored.sort(function (a, b) { return b.score - a.score || a.idx - b.idx; });
    return scored.map(function (s) { return s.item; });
  }

  // ────────────────────────────────────────────────────────
  // DOM
  // ────────────────────────────────────────────────────────
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
      '    <input type="text" autocomplete="off" spellcheck="false" placeholder="Naviguer, rechercher un dossier, agir…">' +
      '    <span class="cmdk-search-kbd">Esc</span>' +
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

    ov.addEventListener('click', function (e) {
      if (e.target === ov) close();
    });
    state.input.addEventListener('input', function () {
      state.filtered = filterItems(state.input.value);
      state.activeIdx = 0;
      render();
    });
    state.input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
      else if (e.key === 'ArrowUp')   { e.preventDefault(); moveActive(-1); }
      else if (e.key === 'Enter')     { e.preventDefault(); executeActive(); }
    });
  }

  function render() {
    if (!state.list) return;
    if (!state.filtered.length) {
      state.list.innerHTML =
        '<div class="cmdk-empty">Aucun résultat pour <b>' +
        escapeHtml(state.input.value) + '</b>.</div>';
      return;
    }
    var html = '';
    var lastSection = null;
    state.filtered.forEach(function (item, idx) {
      var section = sectionFor(item);
      if (section !== lastSection) {
        html += '<div class="cmdk-section">' + section + '</div>';
        lastSection = section;
      }
      var shortcut = '';
      if (idx === 0 && state.activeIdx === 0 && !state.input.value) shortcut = '';
      html += '<button type="button" class="cmdk-row' +
        (idx === state.activeIdx ? ' cmdk-active' : '') +
        '" data-idx="' + idx + '" role="option" aria-selected="' +
        (idx === state.activeIdx ? 'true' : 'false') + '">' +
        '<span class="cmdk-row-ico">' + svgIcon(item.icon || 'folder', 16) + '</span>' +
        '<span class="cmdk-row-body">' +
        '<span class="cmdk-row-title">' + escapeHtml(item.title) + '</span>' +
        (item.sub ? '<span class="cmdk-row-sub">' + escapeHtml(item.sub) + '</span>' : '') +
        '</span>' +
        (shortcut ? '<span class="cmdk-row-shortcut">' + shortcut + '</span>' : '') +
        '</button>';
    });
    state.list.innerHTML = html;
    state.list.querySelectorAll('.cmdk-row').forEach(function (row) {
      row.addEventListener('click', function () {
        state.activeIdx = parseInt(row.getAttribute('data-idx'), 10) || 0;
        executeActive();
      });
      row.addEventListener('mousemove', function () {
        var idx = parseInt(row.getAttribute('data-idx'), 10);
        if (idx !== state.activeIdx) {
          state.activeIdx = idx;
          updateActiveClasses();
        }
      });
    });
    scrollActiveIntoView();
  }

  function updateActiveClasses() {
    state.list.querySelectorAll('.cmdk-row').forEach(function (row) {
      var idx = parseInt(row.getAttribute('data-idx'), 10);
      row.classList.toggle('cmdk-active', idx === state.activeIdx);
      row.setAttribute('aria-selected', idx === state.activeIdx ? 'true' : 'false');
    });
    scrollActiveIntoView();
  }

  function scrollActiveIntoView() {
    var row = state.list.querySelector('.cmdk-row.cmdk-active');
    if (row && row.scrollIntoView) row.scrollIntoView({ block: 'nearest' });
  }

  function sectionFor(item) {
    if (item.type === 'dossier') return 'Dossiers';
    if (item.type === 'app')     return 'Applications';
    return 'Actions rapides';
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
      } catch (e) { /* noop */ }
      return;
    }
    if (item.action === 'logout') {
      fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
        .catch(function () {})
        .then(function () { window.location.href = '/'; });
      return;
    }
    if (item.url) {
      window.location.href = item.url;
    }
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ────────────────────────────────────────────────────────
  // OPEN / CLOSE
  // ────────────────────────────────────────────────────────
  function open(prefill) {
    if (state.open) return;
    buildDom();
    state.open = true;
    state.overlay.classList.add('cmdk-open');
    document.body.classList.add('cmdk-locked');
    Promise.all([fetchUser(), fetchDossiers()]).then(function () {
      state.items = buildBaseItems(state.user);
      state.input.value = prefill || '';
      state.filtered = filterItems(state.input.value);
      state.activeIdx = 0;
      render();
      setTimeout(function () { state.input && state.input.focus(); }, 0);
    });
  }

  function close() {
    if (!state.open || !state.overlay) return;
    state.open = false;
    state.overlay.classList.remove('cmdk-open');
    document.body.classList.remove('cmdk-locked');
  }

  // ────────────────────────────────────────────────────────
  // GLOBAL HOOKS
  // ────────────────────────────────────────────────────────
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
      if (state.open) close();
      else open(isEditableTarget(e.target) ? '' : '');
      return;
    }
    if (key === 'escape' && state.open) {
      e.preventDefault();
      close();
    }
  }

  document.addEventListener('keydown', onKeydown, true);

  // expose
  window.MysifaCmdK = { open: open, close: close, label: KBD_LABEL, shortLabel: KBD_SHORT };

  // Optional badge wiring : tag a un bouton/lien avec data-cmdk-open et il déclenche l'ouverture
  function wireBadges() {
    document.querySelectorAll('[data-cmdk-open]').forEach(function (el) {
      if (el.__cmdkBound) return;
      el.__cmdkBound = true;
      el.addEventListener('click', function (e) {
        e.preventDefault();
        open('');
      });
    });
    // remplir le texte ⌘K / Ctrl+K sur les éléments [data-cmdk-label]
    document.querySelectorAll('[data-cmdk-label]').forEach(function (el) {
      if (!el.textContent.trim()) el.textContent = KBD_LABEL;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireBadges);
  } else {
    wireBadges();
  }
  // Re-wire à chaque render SPA (au cas où le portail reconstruit son DOM)
  if (window.MutationObserver) {
    var mo = new MutationObserver(function () { wireBadges(); });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
