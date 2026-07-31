/**
 * MySifa — Création rapide de tâche (raccourci global + hooks applicatifs).
 *
 * Chargé sur TOUTES les pages HTML via le middleware d'injection de main.py :
 * un seul point d'insertion plutôt qu'un <script> à ajouter dans chacune des
 * vingt pages standalone.
 *
 * Deux entrées :
 *   - Option/Alt + T  → capture la page courante, ouvre la modale pré-remplie
 *     (module déduit de la page, type « Évolution », assignée à moi, capture
 *     jointe en pièce de contexte).
 *   - MySifaTacheRapide.ouvrir({...}) → appelé par la messagerie (action
 *     « Créer une tâche » du menu ⋮ d'un message).
 *
 * Réservé au super administrateur : le raccourci ne fait rien pour les autres
 * rôles, et l'API refuserait de toute façon.
 *
 * Coût au chargement : nul. Aucun appel réseau, aucune CSS injectée tant que
 * le raccourci n'a pas servi. html2canvas (198 Ko) n'est téléchargé qu'à la
 * première capture.
 */
(function () {
  'use strict';
  if (window.MySifaTacheRapide) return;

  var H2C_URL = '/static/html2canvas.min.js';
  var role = null;          // résolu paresseusement
  var meta = null;          // référentiels /api/taches/meta
  var moi = null;           // utilisateur courant
  var cssPose = false;
  var ouverte = false;
  var h2cPromise = null;

  // ── Utilitaires ─────────────────────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function api(url, opts) {
    opts = opts || {};
    opts.credentials = 'include';
    return fetch(url, opts).then(function (r) {
      if (!r.ok) {
        return r.json().then(
          function (j) { throw new Error(j.detail || j.message || 'Erreur'); },
          function () { throw new Error('Erreur ' + r.status); }
        );
      }
      return r.json();
    });
  }
  function toast(msg, type) {
    try {
      if (typeof window.showToast === 'function') { window.showToast(msg, type); return; }
    } catch (e) {}
    var d = document.createElement('div');
    d.className = 'mtq-toast' + (type === 'err' ? ' err' : '');
    d.textContent = msg;
    document.body.appendChild(d);
    setTimeout(function () { d.remove(); }, 3600);
  }

  // ── Détection du module courant ─────────────────────────────────────────
  // Le code module vient du référentiel serveur (config.taches_modules) : on ne
  // fait que rapprocher l'URL de la page d'un de ces codes. Aucun libellé en
  // dur ici — un client Kernse qui renomme ses modules reste cohérent.
  var ROUTES = [
    ['/planning-rh', 'planning_rh'],
    ['/planning',    'planning'],
    ['/fabrication', 'fabrication'],
    ['/stock',       'stock'],
    ['/compta',      'compta'],
    ['/expe',        'expe'],
    ['/qualite',     'qualite'],
    ['/maintenance', 'maintenance'],
    ['/ao',          'ao'],
    ['/bat',         'bat'],
    ['/print',       'print'],
    ['/pricing',     'pricing'],
    ['/paie',        'compta'],
    ['/coffre',      'coffre'],
    ['/rh/coffre',   'coffre'],
    ['/settings',    'settings'],
    ['/prod',        'prod'],
    ['/taches',      'autre'],
  ];
  function moduleCourant() {
    var codes = {};
    ((meta && meta.modules) || []).forEach(function (m) { codes[m.code] = 1; });
    // L'app SPA expose son écran courant : plus fiable que l'URL sur le portail.
    var app = window.__MYSIFA_APP__ || '';
    if (app && codes[app]) return app;
    var p = (location.pathname || '').toLowerCase();
    for (var i = 0; i < ROUTES.length; i++) {
      if (p.indexOf(ROUTES[i][0]) === 0 && codes[ROUTES[i][1]]) return ROUTES[i][1];
    }
    return codes.portail ? 'portail' : '';
  }
  function titrePage() {
    var t = (document.title || '').replace(/\s*[—–|]\s*MySifa.*$/i, '').trim();
    return t || location.pathname;
  }

  // ── Chargements paresseux ───────────────────────────────────────────────
  function chargerRole() {
    if (role !== null) return Promise.resolve(role);
    var r = window.__MYSIFA_ROLE__;
    if (r) { role = r; return Promise.resolve(role); }
    return api('/api/auth/me').then(function (u) {
      moi = u; role = (u && u.role) || '';
      return role;
    }, function () { role = ''; return role; });
  }
  function chargerMeta() {
    if (meta) return Promise.resolve(meta);
    return api('/api/taches/meta').then(function (m) { meta = m; return m; });
  }
  function chargerMoi() {
    if (moi && moi.id) return Promise.resolve(moi);
    return api('/api/auth/me').then(function (u) { moi = u; return u; });
  }
  function chargerH2C() {
    if (window.html2canvas) return Promise.resolve(window.html2canvas);
    if (h2cPromise) return h2cPromise;
    h2cPromise = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = H2C_URL;
      s.onload = function () { resolve(window.html2canvas); };
      s.onerror = function () { reject(new Error('Capture indisponible')); };
      document.head.appendChild(s);
    });
    return h2cPromise;
  }

  // ── Capture de la page ──────────────────────────────────────────────────
  // On capture la zone visible uniquement : une page longue produirait une
  // image de plusieurs Mo pour un contexte que personne ne lit en entier.
  function capturer() {
    return chargerH2C().then(function (h2c) {
      if (!h2c) return null;
      return h2c(document.body, {
        backgroundColor: getComputedStyle(document.body).backgroundColor || '#ffffff',
        scale: Math.min(window.devicePixelRatio || 1, 2),
        logging: false,
        useCORS: true,
        allowTaint: false,
        width: window.innerWidth,
        height: window.innerHeight,
        x: window.scrollX,
        y: window.scrollY,
        scrollX: 0,
        scrollY: 0,
        ignoreElements: function (el) {
          // Ne pas capturer nos propres surcouches (modale, toasts).
          return el.id === 'mtq-root' || (el.classList && el.classList.contains('mtq-toast'));
        }
      }).then(function (canvas) {
        return new Promise(function (resolve) {
          canvas.toBlob(function (blob) { resolve(blob); }, 'image/png', 0.92);
        });
      });
    }).catch(function () { return null; });
  }

  function initiales(nom) {
    var p = String(nom || '').trim().split(/\s+/).filter(Boolean);
    if (!p.length) return '?';
    if (p.length === 1) return p[0].slice(0, 2).toUpperCase();
    return (p[0][0] + p[p.length - 1][0]).toUpperCase();
  }

  function horodatage() {
    var d = new Date();
    function p(n) { return String(n).padStart(2, '0'); }
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds());
  }

  // ── CSS (injectée à la première ouverture) ──────────────────────────────
  function poserCSS() {
    if (cssPose) return;
    cssPose = true;
    var st = document.createElement('style');
    st.textContent =
      '#mtq-root{position:fixed;inset:0;z-index:99000;display:flex;align-items:center;justify-content:center;padding:18px;' +
      'background:rgba(0,0,0,.58);backdrop-filter:blur(3px);font-family:"Segoe UI",system-ui,-apple-system,sans-serif}' +
      '.mtq-modal{background:var(--card,#111827);border:1px solid var(--border,#1e293b);border-radius:16px;padding:22px;' +
      'max-width:600px;width:100%;max-height:92vh;overflow:auto;color:var(--text,#f1f5f9);box-shadow:0 24px 64px rgba(0,0,0,.5)}' +
      '.mtq-modal h3{margin:0 0 4px;font-size:16px;font-weight:700}' +
      '.mtq-sub{font-size:11.5px;color:var(--muted,#94a3b8);margin-bottom:16px}' +
      '.mtq-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}' +
      '.mtq-f{min-width:0}.mtq-f.full{grid-column:1/-1}' +
      '.mtq-f label{display:block;font-size:10px;font-weight:700;color:var(--muted,#94a3b8);' +
      'text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}' +
      '.mtq-f input,.mtq-f select,.mtq-f textarea{width:100%;background:var(--bg,#0a0e17);' +
      'border:1px solid var(--border,#1e293b);border-radius:9px;padding:9px 11px;color:var(--text,#f1f5f9);' +
      'font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}' +
      '.mtq-f input:focus,.mtq-f select:focus,.mtq-f textarea:focus{border-color:var(--accent,#22d3ee)}' +
      '.mtq-f textarea{min-height:88px;resize:vertical;line-height:1.55}' +
      '.mtq-who{display:flex;flex-wrap:wrap;gap:6px}' +
      '.mtq-who button{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;' +
      'border:1px solid var(--border,#1e293b);background:var(--bg,#0a0e17);color:var(--text2,#cbd5e1);' +
      'font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;transition:all .15s}' +
      '.mtq-who button:hover{border-color:var(--accent,#22d3ee);color:var(--accent,#22d3ee)}' +
      '.mtq-who button.on{background:var(--accent-bg,rgba(34,211,238,.12));border-color:var(--accent,#22d3ee);' +
      'color:var(--accent,#22d3ee)}' +
      '.mtq-who .ini{width:19px;height:19px;border-radius:50%;background:var(--border,#1e293b);' +
      'display:inline-flex;align-items:center;justify-content:center;font-size:8px;font-weight:800;flex-shrink:0;overflow:hidden}' +
      '.mtq-who .ini img{width:100%;height:100%;object-fit:cover}' +
      '.mtq-shot{grid-column:1/-1;display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:10px;' +
      'background:var(--bg,#0a0e17);border:1px solid var(--border,#1e293b);font-size:12px;color:var(--text2,#cbd5e1)}' +
      '.mtq-shot img{width:74px;height:46px;object-fit:cover;border-radius:6px;border:1px solid var(--border,#1e293b);flex-shrink:0}' +
      '.mtq-shot .mtq-i{flex:1;min-width:0}' +
      '.mtq-shot label{display:inline-flex;align-items:center;gap:7px;font-size:12px;cursor:pointer;color:var(--text2,#cbd5e1);' +
      'text-transform:none;letter-spacing:0;font-weight:500;margin:0}' +
      '.mtq-shot input[type=checkbox]{width:15px;height:15px;accent-color:var(--accent,#22d3ee);cursor:pointer}' +
      '.mtq-act{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}' +
      '.mtq-btn{padding:10px 16px;border-radius:10px;border:none;background:var(--accent,#22d3ee);color:var(--bg,#0a0e17);' +
      'font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s}' +
      '.mtq-btn:hover{filter:brightness(1.08)}' +
      '.mtq-btn:disabled{opacity:.55;cursor:not-allowed;filter:none}' +
      '.mtq-btn.ghost{background:var(--bg,#0a0e17);border:1px solid var(--border,#1e293b);color:var(--text2,#cbd5e1)}' +
      '.mtq-toast{position:fixed;top:22px;right:22px;background:var(--card,#111827);border:1px solid var(--border,#1e293b);' +
      'border-left:3px solid var(--accent,#22d3ee);border-radius:9px;padding:12px 18px;font-size:13px;' +
      'color:var(--text,#f1f5f9);z-index:99500;box-shadow:0 10px 26px rgba(0,0,0,.35);' +
      'font-family:"Segoe UI",system-ui,sans-serif}' +
      '.mtq-toast.err{border-left-color:var(--danger,#f87171)}' +
      '@media(max-width:640px){.mtq-grid{grid-template-columns:1fr}}';
    document.head.appendChild(st);
  }

  // ── Modale ──────────────────────────────────────────────────────────────
  function fermer() {
    ouverte = false;
    var r = document.getElementById('mtq-root');
    if (r) r.remove();
    document.removeEventListener('keydown', onEchap, true);
  }
  function onEchap(e) {
    if (e.key === 'Escape') { e.stopPropagation(); fermer(); }
  }

  function ouvrir(opts) {
    opts = opts || {};
    if (ouverte) return Promise.resolve();
    ouverte = true;
    return chargerRole().then(function (r) {
      if (r !== 'superadmin') { ouverte = false; return; }
      return Promise.all([chargerMeta(), chargerMoi()]).then(function () {
        poserCSS();
        rendre(opts);
      });
    }).catch(function (e) {
      ouverte = false;
      toast(e.message || 'Création de tâche indisponible.', 'err');
    });
  }

  function rendre(opts) {
    var mods = (meta.modules || []);
    var types = (meta.types || []);
    var prios = (meta.priorites || []);
    var statuts = (meta.statuts || []);
    var modDefaut = opts.module || moduleCourant();
    var typeDefaut = opts.type || 'evolution';
    var statutDefaut = opts.statut || (statuts[0] && statuts[0].code) || '';
    var aMoi = opts.assignerAMoi !== false;
    var capture = opts.capture || null;

    var root = document.createElement('div');
    root.id = 'mtq-root';
    root.innerHTML =
      '<div class="mtq-modal" role="dialog" aria-modal="true" aria-label="Créer une tâche">' +
        '<h3>Créer une tâche</h3>' +
        '<div class="mtq-sub">' + esc(opts.origine || ('Depuis ' + titrePage())) + '</div>' +
        '<div class="mtq-grid">' +
          '<div class="mtq-f full"><label>Titre</label>' +
            '<input type="text" id="mtq-titre" maxlength="300" value="' + esc(opts.titre || '') + '" placeholder="Ce qu\'il y a à faire"></div>' +
          '<div class="mtq-f full"><label>Description</label>' +
            '<textarea id="mtq-desc" placeholder="Contexte, attendu, critères d’acceptation…">' + esc(opts.description || '') + '</textarea></div>' +
          '<div class="mtq-f"><label>Statut</label><select id="mtq-statut">' +
            statuts.map(function (s) { return '<option value="' + esc(s.code) + '"' + (s.code === statutDefaut ? ' selected' : '') + '>' + esc(s.label) + '</option>'; }).join('') +
          '</select></div>' +
          '<div class="mtq-f"><label>Priorité</label><select id="mtq-prio">' +
            prios.map(function (p) { return '<option value="' + esc(p.code) + '"' + (p.code === (opts.priorite || 'normale') ? ' selected' : '') + '>' + esc(p.label) + '</option>'; }).join('') +
          '</select></div>' +
          '<div class="mtq-f"><label>Type</label><select id="mtq-type">' +
            types.map(function (t) { return '<option value="' + esc(t.code) + '"' + (t.code === typeDefaut ? ' selected' : '') + '>' + esc(t.label) + '</option>'; }).join('') +
          '</select></div>' +
          '<div class="mtq-f"><label>Module</label><select id="mtq-module">' +
            '<option value="">Aucun</option>' +
            mods.map(function (m) { return '<option value="' + esc(m.code) + '"' + (m.code === modDefaut ? ' selected' : '') + '>' + esc(m.label) + '</option>'; }).join('') +
          '</select></div>' +
          '<div class="mtq-f full"><label>Assigné à</label><div class="mtq-who" id="mtq-assigne">' +
            (meta.users || []).map(function (u) {
              var sel = (aMoi && moi && u.id === moi.id) || (opts.assignes || []).indexOf(u.id) !== -1;
              return '<button type="button" class="' + (sel ? 'on' : '') + '" data-uid="' + u.id +
                '" aria-pressed="' + (sel ? 'true' : 'false') + '">' +
                '<span class="ini">' + (u.avatar_url
                  ? '<img src="' + esc(u.avatar_url) + '" alt="">'
                  : esc(initiales(u.nom))) + '</span>' + esc(u.nom || '') + '</button>';
            }).join('') +
          '</div></div>' +
          (capture
            ? '<div class="mtq-shot">' +
                '<img src="' + URL.createObjectURL(capture) + '" alt="Aperçu de la capture">' +
                '<div class="mtq-i"><label><input type="checkbox" id="mtq-joindre" checked>' +
                'Joindre la capture de la page</label>' +
                '<div style="font-size:10.5px;color:var(--muted,#94a3b8);margin-top:3px">' +
                Math.round(capture.size / 1024) + ' Ko · ajoutée aux fichiers de la tâche</div></div>' +
              '</div>'
            : '') +
        '</div>' +
        '<div class="mtq-act">' +
          '<button type="button" class="mtq-btn ghost" id="mtq-annuler">Annuler</button>' +
          '<button type="button" class="mtq-btn" id="mtq-creer">Créer la tâche</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(root);
    document.addEventListener('keydown', onEchap, true);

    root.addEventListener('click', function (e) { if (e.target === root) fermer(); });
    root.querySelector('#mtq-annuler').onclick = fermer;

    var champTitre = root.querySelector('#mtq-titre');
    requestAnimationFrame(function () { champTitre.focus(); champTitre.select(); });

    root.querySelectorAll('#mtq-assigne button').forEach(function (b) {
      b.addEventListener('click', function () {
        var on = b.classList.toggle('on');
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    });

    var btn = root.querySelector('#mtq-creer');
    function creer() {
      var titre = (champTitre.value || '').trim();
      if (!titre) { toast('Titre obligatoire.', 'err'); champTitre.focus(); return; }
      var assignes = Array.prototype.slice.call(root.querySelectorAll('#mtq-assigne button.on'))
        .map(function (b) { return Number(b.dataset.uid); });
      var corps = {
        titre: titre,
        description: (root.querySelector('#mtq-desc').value || '').trim() || null,
        statut: root.querySelector('#mtq-statut').value,
        priorite: root.querySelector('#mtq-prio').value,
        type: root.querySelector('#mtq-type').value,
        module: root.querySelector('#mtq-module').value || null,
        assignes: assignes
      };
      btn.disabled = true;
      btn.textContent = 'Création…';
      api('/api/taches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corps)
      }).then(function (j) {
        var joindre = root.querySelector('#mtq-joindre');
        if (capture && joindre && joindre.checked) {
          var fd = new FormData();
          fd.append('fichier', capture, 'capture-' + horodatage() + '.png');
          return fetch('/api/taches/' + j.id + '/fichiers', {
            method: 'POST', credentials: 'include', body: fd
          }).then(function () { return j; }, function () { return j; });
        }
        return j;
      }).then(function (j) {
        fermer();
        toast('Tâche créée.');
        // Si on est déjà sur /taches, on rafraîchit la vue plutôt que de naviguer.
        if (location.pathname.indexOf('/taches') === 0 && typeof window.chargerTaches === 'function') {
          try { window.chargerTaches(); window.chargerStats && window.chargerStats(); } catch (e) {}
        }
      }).catch(function (e) {
        btn.disabled = false;
        btn.textContent = 'Créer la tâche';
        toast(e.message || 'Création impossible.', 'err');
      });
    }
    btn.onclick = creer;
    // Ctrl/Cmd + Entrée valide depuis n'importe quel champ.
    root.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); creer(); }
    });
  }

  // ── Raccourci clavier ───────────────────────────────────────────────────
  // macOS : Option+T produit le caractère « † » ; e.key vaut donc '†' et non
  // 't'. On teste aussi e.code, seul repère fiable de la touche physique.
  function estRaccourci(e) {
    if (!e.altKey || e.ctrlKey || e.metaKey) return false;
    if (e.code === 'KeyT') return true;
    var k = (e.key || '').toLowerCase();
    return k === 't' || k === '†';
  }
  function dansUneSaisie(e) {
    var el = e.target;
    if (!el) return false;
    var tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable;
  }

  document.addEventListener('keydown', function (e) {
    if (!estRaccourci(e)) return;
    if (ouverte) return;
    // On ne vole pas la frappe dans un champ de saisie : « † » y est légitime.
    if (dansUneSaisie(e)) return;
    e.preventDefault();
    chargerRole().then(function (r) {
      if (r !== 'superadmin') return;
      toast('Capture de la page…');
      return capturer().then(function (blob) {
        return ouvrir({
          capture: blob,
          type: 'evolution',
          assignerAMoi: true,
          origine: 'Depuis ' + titrePage() + ' · ' + location.pathname
        });
      });
    });
  }, true);

  // ── API publique ────────────────────────────────────────────────────────
  window.MySifaTacheRapide = {
    ouvrir: ouvrir,
    capturer: capturer,
    /** Action « Créer une tâche » du menu ⋮ d'un message de la messagerie. */
    depuisMessage: function (msg, canal) {
      // Le corps d'un message de la messagerie est dans `body` (chat_widget.js) ;
      // les autres clés sont des replis défensifs si le schéma évolue.
      var texte = String((msg && (msg.body || msg.contenu || msg.message)) || '').trim();
      var auteur = (msg && (msg.user_nom || msg.auteur_nom)) || '';
      var ligne1 = texte.split('\n')[0];
      var titre = ligne1.length > 120 ? ligne1.slice(0, 117) + '…' : ligne1;
      var desc = 'Depuis la messagerie' + (canal ? ' · canal « ' + canal + ' »' : '') +
        (auteur ? '\nMessage de ' + auteur : '') + '\n\n' + texte;
      return ouvrir({
        titre: titre || 'Demande de la messagerie',
        description: desc,
        type: 'evolution',
        assignerAMoi: true,
        origine: 'Depuis la messagerie' + (canal ? ' · ' + canal : '')
      });
    }
  };
})();
