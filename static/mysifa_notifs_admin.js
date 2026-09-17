/**
 * MySifa — Paramètres › Notifications.
 *
 * Une carte par détecteur (catalogue défini dans app/services/notifications.py).
 * Réglages : active / inactive, rôles destinataires, push mobile.
 * Chaque changement est enregistré immédiatement (PUT) et tracé au Journal.
 *
 * Construit en DOM (textContent), aucune couleur en dur.
 * Le script est servi avec ?v=2 (settings_page.py).
 */
(function () {
  'use strict';
  if (window.MySifaNotifsAdmin) return;

  var root = null;
  var data = null;

  function api(url, opts) {
    opts = opts || {};
    opts.credentials = 'include';
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
      opts.headers = { 'Content-Type': 'application/json' };
    }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) throw new Error(j.detail || ('Erreur ' + r.status));
        return j;
      });
    });
  }
  function notifier(msg, erreur) {
    if (typeof window.toast === 'function') return window.toast(msg, erreur);
    if (typeof window.showToast === 'function') return window.showToast(msg, erreur ? 'danger' : 'success');
  }
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  function poserStyle() {
    if (document.getElementById('nadm-style')) return;
    var st = document.createElement('style');
    st.id = 'nadm-style';
    st.textContent = [
      '.nadm-intro{font-size:13px;color:var(--muted);line-height:1.55;margin-bottom:18px;max-width:760px}',
      '.nadm-app{font-size:12px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--muted);margin:22px 0 10px}',
      '.nadm-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:12px}',
      '.nadm-card.off{opacity:.62}',
      '.nadm-top{display:flex;align-items:flex-start;gap:14px}',
      '.nadm-titre{font-size:15px;font-weight:700;color:var(--text)}',
      '.nadm-desc{font-size:13px;color:var(--muted);margin-top:3px;line-height:1.45}',
      '.nadm-live{margin-left:auto;white-space:nowrap;font-size:12px;color:var(--text2);background:var(--bg);',
      ' border:1px solid var(--border);border-radius:10px;padding:4px 10px}',
      '.nadm-live b{color:var(--accent)}',
      '.nadm-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:14px}',
      '.nadm-lbl{font-size:12px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--muted);min-width:110px}',
      '.nadm-chip{background:var(--bg);border:1px solid var(--border);color:var(--text2);border-radius:999px;',
      ' padding:5px 12px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s}',
      '.nadm-chip:hover{border-color:var(--accent)}',
      '.nadm-chip.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}',
      '.nadm-sw{position:relative;width:40px;height:22px;border-radius:11px;background:var(--bg);border:1px solid var(--border);',
      ' cursor:pointer;flex:0 0 40px;transition:background .15s}',
      '.nadm-sw::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;',
      ' background:var(--muted);transition:left .15s,background .15s}',
      '.nadm-sw.on{background:var(--accent);border-color:var(--accent)}',
      '.nadm-sw.on::after{left:20px;background:white}',
      '.nadm-sw-txt{font-size:13px;color:var(--text2)}',
      '.nadm-meta{font-size:11px;color:var(--muted);margin-top:12px}',
      '.nadm-open{margin-left:auto;background:var(--bg);border:1px solid var(--border);color:var(--text2);border-radius:10px;',
      ' padding:6px 12px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;text-decoration:none}',
      '.nadm-open:hover{color:var(--accent);border-color:var(--accent)}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function interrupteur(on, onChange, titre) {
    var b = el('button', 'nadm-sw' + (on ? ' on' : ''));
    b.type = 'button';
    b.setAttribute('role', 'switch');
    b.setAttribute('aria-checked', on ? 'true' : 'false');
    b.title = titre || '';
    b.addEventListener('click', function () { onChange(!b.classList.contains('on')); });
    return b;
  }

  function enregistrer(d, patch) {
    var corps = {
      actif: 'actif' in patch ? patch.actif : d.actif,
      roles: 'roles' in patch ? patch.roles : d.roles,
      push: 'push' in patch ? patch.push : d.push
    };
    return api('/api/notifications/regles/' + encodeURIComponent(d.code), { method: 'PUT', body: corps })
      .then(function (r) {
        d.actif = r.actif; d.roles = r.roles; d.push = r.push;
        d.updated_at = r.updated_at; d.updated_by = r.updated_by;
        notifier('Notification enregistrée.');
        rendre();
        if (window.MySifaNotifs) window.MySifaNotifs.rafraichir();
      })
      .catch(function (e) { notifier(e.message, true); rendre(); });
  }

  function carte(d) {
    var c = el('div', 'nadm-card' + (d.actif ? '' : ' off'));
    var top = el('div', 'nadm-top');
    top.appendChild(interrupteur(d.actif, function (v) { enregistrer(d, { actif: v }); },
      d.actif ? 'Désactiver' : 'Activer'));
    var txt = el('div');
    txt.appendChild(el('div', 'nadm-titre', d.titre));
    txt.appendChild(el('div', 'nadm-desc', d.description));
    top.appendChild(txt);
    var live = el('div', 'nadm-live');
    live.appendChild(document.createTextNode('En ce moment : '));
    live.appendChild(el('b', null, String(d.en_cours)));
    top.appendChild(live);
    c.appendChild(top);

    var rRoles = el('div', 'nadm-row');
    rRoles.appendChild(el('span', 'nadm-lbl', 'Destinataires'));
    data.roles.forEach(function (ro) {
      var on = d.roles.indexOf(ro.code) !== -1;
      var chip = el('button', 'nadm-chip' + (on ? ' on' : ''), ro.label);
      chip.type = 'button';
      if (d.roles_suggeres.indexOf(ro.code) !== -1 && !on) chip.title = 'Rôle suggéré pour cette notification';
      chip.addEventListener('click', function () {
        var roles = d.roles.filter(function (x) { return x !== ro.code; });
        if (!on) roles.push(ro.code);
        enregistrer(d, { roles: roles });
      });
      rRoles.appendChild(chip);
    });
    c.appendChild(rRoles);

    var rPush = el('div', 'nadm-row');
    rPush.appendChild(el('span', 'nadm-lbl', 'Push mobile'));
    rPush.appendChild(interrupteur(d.push, function (v) { enregistrer(d, { push: v }); }));
    rPush.appendChild(el('span', 'nadm-sw-txt', d.push
      ? 'Envoyé aux appareils abonnés quand un nouvel élément apparaît (contrôle toutes les 5 min).'
      : 'Pastille sur l’écran d’accueil uniquement.'));
    var ouvrir = el('a', 'nadm-open', 'Ouvrir l’écran →');
    ouvrir.href = d.lien;
    rPush.appendChild(ouvrir);
    c.appendChild(rPush);

    if (d.updated_at) {
      c.appendChild(el('div', 'nadm-meta',
        'Modifié le ' + d.updated_at.replace('T', ' à ').slice(0, 18) + (d.updated_by ? ' par ' + d.updated_by : '')));
    }
    return c;
  }

  function rendre() {
    if (!root) return;
    root.textContent = '';
    root.appendChild(el('div', 'nadm-intro',
      'Chaque notification compte en direct ce qui attend un service et s’affiche en pastille rouge en haut à ' +
      'droite de l’appli concernée, sur l’écran d’accueil. Elle disparaît d’elle-même quand le travail ' +
      'est fait. Un utilisateur ne la voit que s’il a accès à l’application concernée.'));
    if (!data) { root.appendChild(el('div', 'nadm-desc', 'Chargement…')); return; }
    var parApp = {}, ordre = [];
    data.detecteurs.forEach(function (d) {
      if (!parApp[d.app_label]) { parApp[d.app_label] = []; ordre.push(d.app_label); }
      parApp[d.app_label].push(d);
    });
    ordre.forEach(function (app) {
      root.appendChild(el('div', 'nadm-app', app));
      parApp[app].forEach(function (d) { root.appendChild(carte(d)); });
    });
  }

  function init(el_) {
    root = el_ || root;
    if (!root) return;
    poserStyle();
    rendre();
    api('/api/notifications/regles').then(function (d) { data = d; rendre(); })
      .catch(function (e) { notifier(e.message, true); });
  }

  window.MySifaNotifsAdmin = { init: init };
})();
