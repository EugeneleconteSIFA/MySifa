/* MySifa — pied de sidebar commun à toutes les applis (v3.3.0, 11/09/2026).
 *
 * Un seul pied, dans cet ordre, sur chaque appli :
 *   ← Retour MySifa · profil (photo, rôle, Mon profil) · Contacter le support
 *   · Mode clair / sombre · Déconnexion · version
 *
 * Deux façons de l'utiliser, selon la manière dont la page construit sa sidebar :
 *
 * 1. Page qui construit son DOM en JS (el(), h(), createElement) :
 *      MySifaSidebar.footer({ app: 'MyStock', user: S.user, onTheme: render })
 *    rend un élément <div class="sidebar-bottom msb-footer"> prêt à insérer.
 *
 * 2. Page en HTML (gabarit serveur ou innerHTML) : poser un emplacement vide
 *      <div class="sidebar-bottom msb-footer" data-msb-footer data-msb-app="Tâches"></div>
 *    ou l'obtenir par MySifaSidebar.footerHtml({ app: 'Tâches' }).
 *    Il se remplit tout seul au chargement ET à chaque fois qu'un rendu le
 *    recrée (MutationObserver : le remplissage passe avant l'affichage).
 *
 * Réglages communs à toute la page (utile en mode 2) :
 *   MySifaSidebar.configure({ app, version, user, onSupport, onTheme, onLogout, backs })
 *
 * - user      : l'utilisateur (sinon lu une fois sur /api/auth/me et gardé)
 * - onSupport : remplace la fenêtre de support partagée (MySifaSupport.open)
 * - onTheme   : appelé APRÈS la bascule clair/sombre (ex. re-rendre la page)
 * - onLogout  : remplace la déconnexion par défaut (POST /api/auth/logout → /)
 * - backs     : liens de retour supplémentaires, avant « Retour MySifa »
 *               [{ label: 'Retour MyExpé', href: '/expe' }]
 * - version   : sinon data-msb-version, sinon window.__APP_VERSION__
 */
(function (global) {
  'use strict';
  if (global.MySifaSidebar) return;

  var conf = {};
  var userCache;          // undefined = pas encore lu ; null = pas de session
  var userPromise = null;

  var SVG = {
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    edit: '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>',
    support: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12a8 8 0 0 1 16 0"/><path d="M6 12v5a2 2 0 0 0 2 2h1v-7H8a2 2 0 0 0-2 2z"/><path d="M18 12v5a2 2 0 0 1-2 2h-1v-7h1a2 2 0 0 1 2 2z"/></svg>',
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function opt(o, k) {
    return (o && o[k] !== undefined) ? o[k] : conf[k];
  }

  // ── Utilisateur ──────────────────────────────────────────────────────
  function lireUtilisateur() {
    if (userCache !== undefined) return Promise.resolve(userCache);
    if (!userPromise) {
      userPromise = fetch('/api/auth/me', { credentials: 'include' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; })
        .then(function (u) { userCache = u || null; return userCache; });
    }
    return userPromise;
  }

  function setUser(u) {
    if (!u) return;
    userCache = u;
    document.querySelectorAll('.msb-footer').forEach(function (f) { remplirProfil(f, u); });
  }

  function remplirProfil(footerEl, u) {
    var slot = footerEl.querySelector('.msb-chip-slot, .user-chip');
    if (!slot) return;
    if (!u) { slot.remove(); return; }
    var chip = document.createElement('div');
    chip.className = 'user-chip';
    chip.title = 'Modifier mon profil';
    chip.setAttribute('role', 'link');
    chip.tabIndex = 0;
    var labels = (typeof global.ROLE_LABELS === 'object' && global.ROLE_LABELS) || undefined;
    if (global.MySifaUserChip) {
      chip.innerHTML = global.MySifaUserChip.innerHtml(u, { roleLabels: labels, editIconHtml: SVG.edit });
    } else {
      chip.innerHTML = '<div class="uc-name">' + esc(u.nom || '') + '</div>'
        + '<div class="uc-role">' + esc((labels && labels[u.role]) || u.role || '') + '</div>'
        + '<div class="uc-profil">' + SVG.edit + ' Mon profil</div>';
    }
    var aller = function () { global.location.href = '/profil'; };
    chip.addEventListener('click', aller);
    chip.addEventListener('keydown', function (e) { if (e.key === 'Enter') aller(); });
    slot.replaceWith(chip);
  }

  // ── Actions ──────────────────────────────────────────────────────────
  function toast(msg, type) {
    if (typeof global.showToast === 'function') {
      try { global.showToast(msg, type === 'error' ? 'error' : (type || 'success')); return; } catch (e) {}
    }
    var t = document.createElement('div');
    t.className = 'msb-toast' + (type === 'error' ? ' error' : '');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
  }

  function chargerSupport() {
    if (global.MySifaSupport && global.MySifaSupport.open) return Promise.resolve(global.MySifaSupport);
    return new Promise(function (resolve, reject) {
      if (!document.querySelector('link[href^="/static/support_widget.css"]')) {
        var l = document.createElement('link');
        l.rel = 'stylesheet'; l.href = '/static/support_widget.css';
        document.head.appendChild(l);
      }
      var s = document.createElement('script');
      s.src = '/static/support_widget.js';
      s.onload = function () { global.MySifaSupport ? resolve(global.MySifaSupport) : reject(new Error('support')); };
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function ouvrirSupport(o) {
    var perso = opt(o, 'onSupport');
    if (typeof perso === 'function') { perso(); return; }
    Promise.all([chargerSupport(), lireUtilisateur()]).then(function (r) {
      r[0].open({ user: r[1] || {}, page: opt(o, 'app') || global.location.pathname, notify: toast });
    }).catch(function () { toast('Fenêtre de support indisponible.', 'error'); });
  }

  function estClair() {
    if (global.MySifaTheme && global.MySifaTheme.isLight) return global.MySifaTheme.isLight();
    return document.body.classList.contains('light');
  }

  function majBoutonsTheme() {
    var clair = estClair();
    document.querySelectorAll('.msb-footer > .theme-btn').forEach(function (b) {
      b.querySelector('.theme-ico').innerHTML = clair ? SVG.sun : SVG.moon;
      b.querySelector('.theme-label').textContent = clair ? 'Mode clair' : 'Mode sombre';
    });
  }

  function basculerTheme(o) {
    if (global.MySifaTheme && global.MySifaTheme.toggleMode) {
      global.MySifaTheme.toggleMode();
    } else {
      document.body.classList.toggle('light');
    }
    majBoutonsTheme();
    try { global.dispatchEvent(new CustomEvent('mysifa:theme', { detail: { light: estClair() } })); } catch (e) {}
    var apres = opt(o, 'onTheme');
    if (typeof apres === 'function') apres();
  }

  function deconnecter(o) {
    var perso = opt(o, 'onLogout');
    if (typeof perso === 'function') { perso(); return; }
    fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
      .catch(function () {})
      .then(function () { global.location.href = '/'; });
  }

  // ── Construction ─────────────────────────────────────────────────────
  function versionTexte(o) {
    var v = opt(o, 'version') || global.__APP_VERSION__ || '';
    v = String(v || '').trim();
    if (v && /^\d/.test(v)) v = 'v' + v;
    var app = String(opt(o, 'app') || '').trim();
    return app && v ? app + ' · ' + v : (app || v);
  }

  function contenuHtml(o) {
    var clair = estClair();
    var backs = opt(o, 'backs') || [];
    var h = '';
    backs.forEach(function (b) {
      h += '<a class="nav-btn back-mysifa msb-back-extra" href="' + esc(b.href || '/') + '">← ' + esc(b.label || 'Retour') + '</a>';
    });
    h += '<a class="nav-btn back-mysifa" href="/" data-msb-back>← Retour <span class="wm">My<span>Sifa</span></span></a>'
      + '<div class="msb-chip-slot msb-chip-vide" aria-hidden="true"></div>'
      + '<button type="button" class="support-btn" data-msb-support><span class="support-ico">'
      + ((global.MySifaSupport && global.MySifaSupport.iconSvg) ? global.MySifaSupport.iconSvg() : SVG.support)
      + '</span><span>Contacter le support</span></button>'
      + '<button type="button" class="theme-btn" data-msb-theme><span class="theme-ico">' + (clair ? SVG.sun : SVG.moon)
      + '</span><span class="theme-label">' + (clair ? 'Mode clair' : 'Mode sombre') + '</span></button>'
      + '<button type="button" class="logout-btn" data-msb-logout><span class="msb-ico">' + SVG.logout
      + '</span><span>Déconnexion</span></button>';
    var v = versionTexte(o);
    if (v) h += '<div class="version">' + esc(v) + '</div>';
    return h;
  }

  function remplir(footerEl, o) {
    o = o || {};
    footerEl.classList.add('sidebar-bottom', 'msb-footer');
    footerEl.setAttribute('data-msb-mounted', '1');
    footerEl.innerHTML = contenuHtml(o);
    footerEl.querySelector('[data-msb-support]').addEventListener('click', function () { ouvrirSupport(o); });
    footerEl.querySelector('[data-msb-theme]').addEventListener('click', function () { basculerTheme(o); });
    footerEl.querySelector('[data-msb-logout]').addEventListener('click', function () { deconnecter(o); });
    var u = opt(o, 'user');
    if (u) { userCache = u; remplirProfil(footerEl, u); }
    else if (userCache !== undefined) { remplirProfil(footerEl, userCache); }
    else { lireUtilisateur().then(function (x) { remplirProfil(footerEl, x); }); }
    return footerEl;
  }

  function footer(o) {
    return remplir(document.createElement('div'), o);
  }

  function footerHtml(o) {
    o = o || {};
    return '<div class="sidebar-bottom msb-footer" data-msb-footer'
      + (o.app ? ' data-msb-app="' + esc(o.app) + '"' : '')
      + (o.version ? ' data-msb-version="' + esc(o.version) + '"' : '') + '></div>';
  }

  function optionsDepuisData(elm) {
    var o = {};
    if (elm.hasAttribute('data-msb-app')) o.app = elm.getAttribute('data-msb-app');
    if (elm.hasAttribute('data-msb-version')) o.version = elm.getAttribute('data-msb-version');
    return o;
  }

  function monterEmplacements(racine) {
    var liste = [];
    if (racine.matches && racine.matches('[data-msb-footer]:not([data-msb-mounted])')) liste.push(racine);
    if (racine.querySelectorAll) {
      racine.querySelectorAll('[data-msb-footer]:not([data-msb-mounted])').forEach(function (x) { liste.push(x); });
    }
    liste.forEach(function (x) { remplir(x, optionsDepuisData(x)); });
  }

  function configure(c) {
    Object.keys(c || {}).forEach(function (k) { conf[k] = c[k]; });
    if (c && c.user) setUser(c.user);
  }

  // ── Titres de section ────────────────────────────────────────────────
  // Pour les pages qui construisent leur menu en JS : un titre au bon
  // format, repliable si onToggle est fourni.
  function sectionHtml(label, opts) {
    opts = opts || {};
    var chev = opts.collapsible
      ? '<span class="ngl-chevron"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg></span>'
      : '';
    return '<div class="msb-section' + (opts.collapsible ? ' msb-toggle' : '') + (opts.collapsed ? ' ngl-collapsed' : '') + '"'
      + (opts.attrs || '') + '><span>' + esc(label) + '</span>' + chev + '</div>';
  }

  // ── Démarrage ────────────────────────────────────────────────────────
  function demarrer() {
    monterEmplacements(document);
    if (!global.MutationObserver) return;
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var add = muts[i].addedNodes;
        for (var j = 0; j < add.length; j++) {
          if (add[j].nodeType === 1) monterEmplacements(add[j]);
        }
      }
    }).observe(document.documentElement, { childList: true, subtree: true });
    // Une bascule de thème faite ailleurs remet les libellés d'aplomb : dans un
    // autre onglet (storage), ou dans la page elle-même — MySifaTheme.mergeFromUser
    // peut changer le mode APRÈS le montage du pied, en posant la classe `light`.
    global.addEventListener('storage', majBoutonsTheme);
    if (document.body) {
      new MutationObserver(majBoutonsTheme).observe(document.body, { attributes: true, attributeFilter: ['class'] });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();

  global.MySifaSidebar = {
    footer: footer,
    footerHtml: footerHtml,
    mount: remplir,
    configure: configure,
    setUser: setUser,
    sectionHtml: sectionHtml,
    refreshTheme: majBoutonsTheme,
    openSupport: function (o) { ouvrirSupport(o); },
  };
})(typeof window !== 'undefined' ? window : this);
