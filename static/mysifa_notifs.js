/**
 * MySifa — Cloche des notifications par service (en haut à droite).
 *
 * Injecté sur TOUTES les pages HTML par le middleware de main.py.
 *
 * Données : GET /api/notifications
 *   { concerne, items:[{code, app_label, libelle, n, lien, nouveau}], nouveaux, total }
 * Une notification = un détecteur côté serveur (app/services/notifications.py)
 * qui compte ce qui attend l'utilisateur. Elle disparaît quand le travail est fait.
 *
 * Comportement :
 *   - rien n'est affiché tant que l'utilisateur n'est destinataire d'aucune
 *     notification (réglage Paramètres › Notifications) ;
 *   - la cloche se pose en haut à droite (dans la topbar sur mobile) ;
 *   - pastille = nombre d'éléments en attente, pleine quand il y a du nouveau ;
 *   - une bulle s'affiche quelques secondes quand une nouveauté arrive pendant
 *     que la page est ouverte ;
 *   - ouvrir le panneau marque les notifications comme vues.
 *
 * Aucune couleur en dur : tout passe par les variables du thème.
 */
(function () {
  'use strict';
  if (window.MySifaNotifs) return;

  var POLL_ACTIF = 60000;      // destinataire d'au moins une notification
  var POLL_VEILLE = 300000;    // destinataire de rien : on revérifie de loin
  var etat = { data: null, ouvert: false, timer: null, dejaBulle: {} };
  var btn, badge, panel;

  function api(url, opts) {
    opts = opts || {};
    opts.credentials = 'include';
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
      opts.headers = { 'Content-Type': 'application/json' };
    }
    return fetch(url, opts).then(function (r) {
      if (r.status === 401 || r.status === 403) return null;
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  var ICONE_CLOCHE =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>';

  function poserStyle() {
    if (document.getElementById('mnotif-style')) return;
    var st = document.createElement('style');
    st.id = 'mnotif-style';
    st.textContent = [
      '.mnotif-btn{position:fixed;top:14px;right:18px;z-index:8004;width:40px;height:40px;border-radius:12px;',
      ' border:1px solid var(--border);background:var(--card);color:var(--text2);cursor:pointer;display:none;',
      ' align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(0,0,0,.18);transition:background .15s,color .15s;font-family:inherit}',
      '.mnotif-btn.on{display:inline-flex}',
      '.mnotif-btn:hover,.mnotif-btn.open{background:var(--bg);color:var(--accent);border-color:var(--accent)}',
      'body.staging-on .mnotif-btn{top:38px}',
      '.mnotif-btn.in-topbar{position:relative;top:auto;right:auto;box-shadow:none;margin-left:auto;flex:0 0 auto}',
      '.mnotif-btn.in-topbar + .mobile-home-btn{margin-left:0}',
      '.mnotif-badge{position:absolute;top:-6px;right:-6px;min-width:18px;height:18px;padding:0 5px;border-radius:9px;',
      ' font-size:11px;font-weight:700;line-height:18px;text-align:center;display:none;',
      ' background:var(--bg);color:var(--text2);border:1px solid var(--border)}',
      '.mnotif-badge.on{display:block}',
      '.mnotif-badge.neuf{background:var(--danger);color:white;border-color:var(--danger)}',
      '.mnotif-badge.neuf::after{content:"";position:absolute;inset:-3px;border-radius:12px;border:2px solid var(--danger);',
      ' opacity:0;animation:mnotif-pulse 2s ease-out infinite}',
      '@keyframes mnotif-pulse{0%{opacity:.6;transform:scale(.9)}100%{opacity:0;transform:scale(1.5)}}',
      '.perf-eco .mnotif-badge.neuf::after,.reduce-anim .mnotif-badge.neuf::after{animation:none}',
      '.mnotif-panel{position:fixed;top:62px;right:18px;z-index:8005;width:340px;max-width:calc(100vw - 32px);',
      ' max-height:70vh;overflow:auto;background:var(--card);border:1px solid var(--border);border-radius:12px;',
      ' box-shadow:0 12px 32px rgba(0,0,0,.28);color:var(--text);font-family:\'Segoe UI\',system-ui,sans-serif;display:none}',
      'body.staging-on .mnotif-panel{top:86px}',
      '.mnotif-panel.on{display:block}',
      '.mnotif-head{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid var(--border)}',
      '.mnotif-head b{font-size:14px}',
      '.mnotif-lien{background:var(--bg);border:1px solid var(--border);color:var(--text2);border-radius:8px;',
      ' font-size:12px;padding:4px 8px;cursor:pointer;font-family:inherit}',
      '.mnotif-lien:hover{color:var(--accent);border-color:var(--accent)}',
      '.mnotif-app{padding:10px 14px 4px;font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--muted)}',
      '.mnotif-item{display:flex;align-items:center;gap:10px;width:100%;padding:10px 14px;border:none;background:none;',
      ' color:var(--text);font-size:13px;text-align:left;cursor:pointer;font-family:inherit}',
      '.mnotif-item:hover{background:var(--accent-bg)}',
      '.mnotif-item .lbl{flex:1}',
      '.mnotif-dot{width:8px;height:8px;border-radius:50%;background:var(--danger);flex:0 0 8px}',
      '.mnotif-dot.vu{background:transparent}',
      '.mnotif-n{min-width:24px;padding:2px 7px;border-radius:10px;background:var(--accent-bg);color:var(--accent);font-weight:700;font-size:12px;text-align:center}',
      '.mnotif-vide{padding:22px 14px;text-align:center;color:var(--muted);font-size:13px}',
      '.mnotif-bulle{position:fixed;top:64px;right:18px;z-index:8006;max-width:320px;background:var(--card);',
      ' border:1px solid var(--accent);border-left:4px solid var(--accent);border-radius:10px;padding:10px 14px;',
      ' box-shadow:0 10px 28px rgba(0,0,0,.28);color:var(--text);font-size:13px;cursor:pointer;',
      ' font-family:\'Segoe UI\',system-ui,sans-serif;animation:mnotif-in .25s ease-out}',
      'body.staging-on .mnotif-bulle{top:88px}',
      '.mnotif-bulle small{display:block;color:var(--muted);font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;margin-bottom:2px}',
      '@keyframes mnotif-in{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}',
      '.perf-eco .mnotif-bulle,.reduce-anim .mnotif-bulle{animation:none}',
      '@media (max-width:900px){.mnotif-panel,.mnotif-bulle{top:64px;right:12px}}',
      '@media print{.mnotif-btn,.mnotif-panel,.mnotif-bulle{display:none!important}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function poserBouton() {
    if (btn) return;
    poserStyle();
    if (document.querySelector('.staging-bandeau')) document.body.classList.add('staging-on');
    btn = el('button', 'mnotif-btn');
    btn.type = 'button';
    btn.title = 'Notifications';
    btn.setAttribute('aria-label', 'Notifications');
    btn.innerHTML = ICONE_CLOCHE;   // SVG statique, aucune donnée utilisateur
    badge = el('span', 'mnotif-badge');
    btn.appendChild(badge);
    btn.addEventListener('click', function (ev) { ev.stopPropagation(); basculer(); });

    // Mobile : la topbar fixe occupe le haut — la cloche s'y range, avant
    // le bouton accueil, plutôt que de flotter par-dessus.
    var topbar = document.querySelector('.mobile-topbar');
    var mobile = window.matchMedia && window.matchMedia('(max-width:900px)').matches;
    if (topbar && mobile && getComputedStyle(topbar).display !== 'none') {
      btn.classList.add('in-topbar');
      var home = topbar.querySelector('.mobile-home-btn');
      if (home) topbar.insertBefore(btn, home); else topbar.appendChild(btn);
    } else {
      document.body.appendChild(btn);
    }

    panel = el('div', 'mnotif-panel');
    panel.setAttribute('role', 'dialog');
    panel.addEventListener('click', function (ev) { ev.stopPropagation(); });
    document.body.appendChild(panel);

    document.addEventListener('click', function () { if (etat.ouvert) fermer(); });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && etat.ouvert) fermer(); });
  }

  function rendreBadge() {
    var d = etat.data;
    if (!d || !d.concerne) { if (btn) btn.classList.remove('on'); return; }
    poserBouton();
    btn.classList.add('on');
    var total = d.items.length;
    badge.textContent = total > 99 ? '99+' : String(total);
    badge.classList.toggle('on', total > 0);
    badge.classList.toggle('neuf', d.nouveaux > 0);
    btn.title = total ? (total + ' notification' + (total > 1 ? 's' : '')) : 'Aucune notification';
  }

  function rendrePanel() {
    if (!panel) return;
    panel.textContent = '';
    var d = etat.data || { items: [] };
    var head = el('div', 'mnotif-head');
    head.appendChild(el('b', null, 'Notifications'));
    if (d.nouveaux > 0) {
      var tout = el('button', 'mnotif-lien', 'Tout marquer comme vu');
      tout.type = 'button';
      tout.addEventListener('click', function () {
        marquerVu(d.items.map(function (i) { return i.code; })).then(rafraichir);
      });
      head.appendChild(tout);
    }
    panel.appendChild(head);
    if (!d.items.length) {
      panel.appendChild(el('div', 'mnotif-vide', 'Rien en attente.'));
      return;
    }
    var groupes = {};
    var ordre = [];
    d.items.forEach(function (i) {
      if (!groupes[i.app_label]) { groupes[i.app_label] = []; ordre.push(i.app_label); }
      groupes[i.app_label].push(i);
    });
    ordre.forEach(function (app) {
      panel.appendChild(el('div', 'mnotif-app', app));
      groupes[app].forEach(function (i) {
        var b = el('button', 'mnotif-item');
        b.type = 'button';
        b.appendChild(el('span', 'mnotif-dot' + (i.nouveau ? '' : ' vu')));
        b.appendChild(el('span', 'lbl', i.titre));
        b.appendChild(el('span', 'mnotif-n', String(i.n)));
        b.addEventListener('click', function () { aller(i); });
        panel.appendChild(b);
      });
    });
  }

  function aller(item) {
    marquerVu([item.code]).catch(function () {}).then(function () {
      fermer();
      var cible = new URL(item.lien, location.origin);
      var memePage = cible.pathname === location.pathname && cible.search === location.search;
      location.href = cible.href;
      // Même page, seul le hash change : pas de rechargement ; si le hash est
      // déjà le bon, on recharge pour que la page rouvre le bon onglet.
      if (memePage && cible.hash === location.hash) location.reload();
    });
  }

  function marquerVu(codes) {
    if (!codes || !codes.length) return Promise.resolve();
    return api('/api/notifications/vu', { method: 'POST', body: { codes: codes } });
  }

  function ouvrir() {
    etat.ouvert = true;
    btn.classList.add('open');
    rendrePanel();
    panel.classList.add('on');
    fermerBulle();
    var neufs = (etat.data && etat.data.items || []).filter(function (i) { return i.nouveau; })
      .map(function (i) { return i.code; });
    if (neufs.length) {
      // Les points « nouveau » restent visibles tant que le panneau est ouvert ;
      // seule la pastille de la cloche s'éteint.
      marquerVu(neufs).then(function () {
        if (etat.data) { etat.data.nouveaux = 0; rendreBadge(); }
      }).catch(function () {});
    }
  }

  function fermer() {
    etat.ouvert = false;
    if (btn) btn.classList.remove('open');
    if (panel) panel.classList.remove('on');
    rafraichir();
  }

  function basculer() { if (etat.ouvert) fermer(); else ouvrir(); }

  var bulleEl = null, bulleTimer = null;
  function fermerBulle() {
    if (bulleEl) { bulleEl.remove(); bulleEl = null; }
    if (bulleTimer) { clearTimeout(bulleTimer); bulleTimer = null; }
  }
  function bulle(item) {
    fermerBulle();
    bulleEl = el('div', 'mnotif-bulle');
    bulleEl.appendChild(el('small', null, item.app_label));
    bulleEl.appendChild(document.createTextNode(item.libelle));
    bulleEl.addEventListener('click', function () { fermerBulle(); aller(item); });
    document.body.appendChild(bulleEl);
    bulleTimer = setTimeout(fermerBulle, 8000);
  }

  function rafraichir() {
    return api('/api/notifications').then(function (d) {
      var avant = etat.data;
      etat.data = d;
      rendreBadge();
      if (etat.ouvert) rendrePanel();
      // Bulle : seulement pour une nouveauté apparue pendant que la page est
      // ouverte (pas au chargement — la pastille suffit), une fois par signature.
      if (d && avant && !etat.ouvert) {
        var neuf = (d.items || []).filter(function (i) {
          var cle = i.code + '|' + i.signature;
          if (!i.nouveau || etat.dejaBulle[cle]) return false;
          var prec = (avant.items || []).filter(function (a) { return a.code === i.code; })[0];
          return !prec || prec.signature !== i.signature;
        })[0];
        if (neuf) { etat.dejaBulle[neuf.code + '|' + neuf.signature] = 1; bulle(neuf); }
      }
      if (d) (d.items || []).forEach(function (i) { etat.dejaBulle[i.code + '|' + i.signature] = 1; });
      return d;
    }).catch(function () { return null; }).then(function (d) {
      planifier(d && d.concerne ? POLL_ACTIF : POLL_VEILLE);
    });
  }

  function planifier(delai) {
    if (etat.timer) clearTimeout(etat.timer);
    etat.timer = setTimeout(function () {
      if (document.hidden) { planifier(delai); return; }
      rafraichir();
    }, delai);
  }

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && etat.data && etat.data.concerne) rafraichir();
  });

  function boot() {
    // Pages publiques / login : pas de session, l'API répond 401 et on s'arrête.
    if (/^\/(portail|login)(\/|$)/.test(location.pathname)) return;
    api('/api/notifications').then(function (d) {
      if (d === null) return;   // pas connecté
      etat.data = d;
      if (d) (d.items || []).forEach(function (i) { etat.dejaBulle[i.code + '|' + i.signature] = 1; });
      rendreBadge();
      planifier(d && d.concerne ? POLL_ACTIF : POLL_VEILLE);
    }).catch(function () { planifier(POLL_VEILLE); });
  }

  window.MySifaNotifs = { rafraichir: rafraichir };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
