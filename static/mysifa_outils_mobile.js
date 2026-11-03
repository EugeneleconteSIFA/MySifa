/* MySifa — les outils flottants passent dans une feuille, sur téléphone.
 *
 * Messagerie, assistant IA, calculette, post-it, capture, outils propres à une
 * appli : empilés en bas à droite, ces boutons recouvraient le contenu de toutes
 * les pages. Sous 900 px ils sont masqués, et une seule entrée les remplace : une
 * poignée fine au bord droit, que le doigt peut déplacer si elle gêne, ou
 * l'onglet « Outils » de la barre du bas quand la page en a un.
 *
 * Les boutons d'origine restent dans la page, invisibles : la feuille les
 * déclenche par un clic, et chaque outil garde son code et ses réglages. Un
 * bouton coupé dans Paramètres (display:none) n'apparaît donc pas dans la feuille.
 *
 * Injecté par main.py avec les boutons flottants (_BOUTONS_JS). Sur ordinateur,
 * ce fichier ne change rien.
 */
(function () {
  'use strict';
  if (window.__mysifaOutilsMobile || window.top !== window) return;
  window.__mysifaOutilsMobile = true;

  var ecran = window.matchMedia('(max-width: 900px)');
  var CLE_POS = 'mysifa_outils_poignee_y';
  var SEUIL_GLISSER = 8;
  var ICONE_POIGNEE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 6 9 12 15 18"/></svg>';

  // Les libellés des outils connus ; un outil propre à une page (.mysifa-dock-extra)
  // inconnu ici prend son aria-label.
  var LIBELLES = {
    'cw-bubble': 'Messagerie',
    'cw-bar': 'Messagerie',
    'ai-chat-btn': 'Agent IA',
    '_calc_fab': 'Calculette',
    'postit-dock-btn': 'Post-it',
    'mysifa-cap-fab': 'Ajouter à l\'accueil',
    'mtr-fab': 'Métrage bobine',
    'expe-carte-fab': 'Carte de France',
  };

  var st = document.createElement('style');
  st.textContent =
    '@media (max-width: 900px){' +
    '.mysifa-dock-fab,.calc-fab,#cw-bubble,#cw-bar,#ai-chat-btn,#postit-dock-btn,#mysifa-dock-toggle,#mysifa-dock-barre' +
    '{opacity:0!important;pointer-events:none!important;visibility:hidden!important}' +
    // La bulle d'annonce de l'agent désigne un bouton qui n'est plus là.
    '#ai-annonce{display:none!important}' +
    // Une fenêtre d'accueil à la fois : la suivante attend que la première soit fermée.
    'body:has(.upd-overlay) .mguide-ov,' +
    'body:has(.upd-overlay) #cw-notif-modal,' +
    'body:has(.mguide-ov) #cw-notif-modal{display:none!important}' +
    '#msf-outils-poignee{position:fixed;right:0;z-index:8001;width:20px;height:64px;padding:0;' +
    'display:flex;align-items:center;justify-content:center;touch-action:none;cursor:pointer;' +
    'background:var(--card);color:var(--muted);border:1px solid var(--border);border-right:0;' +
    'border-radius:10px 0 0 10px;box-shadow:0 2px 10px rgba(0,0,0,.14);-webkit-tap-highlight-color:transparent}' +
    '#msf-outils-poignee[hidden]{display:none}' +
    // Cible tactile élargie vers l'intérieur de l'écran, sans masquer davantage.
    '#msf-outils-poignee::before{content:"";position:absolute;inset:-6px 0 -6px -10px}' +
    '#msf-outils-poignee.glisse{color:var(--accent);border-color:var(--accent)}' +
    '#msf-outils-pastille{position:absolute;top:-5px;left:-5px;min-width:16px;height:16px;padding:0 4px;' +
    'border-radius:8px;background:var(--danger);color:#fff;font-size:10px;font-weight:800;line-height:16px;text-align:center}' +
    '#msf-outils-pastille:empty{display:none}' +
    'body.mysifa-dock-sous-fenetre #msf-outils-poignee,html.mysifa-capture #msf-outils-poignee{display:none}' +
    '.msf-outils-voile{position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.45)}' +
    '.msf-outils-feuille{position:fixed;left:0;right:0;bottom:0;z-index:9001;background:var(--card);' +
    'border-top:1px solid var(--border);border-radius:20px 20px 0 0;max-height:80vh;overflow-y:auto;' +
    'padding:8px 8px calc(14px + env(safe-area-inset-bottom,0px));box-shadow:0 -8px 40px rgba(0,0,0,.25)}' +
    '.msf-outils-trait{width:38px;height:4px;border-radius:2px;background:var(--border);margin:6px auto 10px}' +
    '.msf-outils-item{display:flex;align-items:center;gap:14px;width:100%;min-height:52px;padding:8px 14px;' +
    'background:none;border:0;border-radius:12px;color:var(--text);font:inherit;font-size:15px;font-weight:500;' +
    'text-align:left;cursor:pointer;-webkit-tap-highlight-color:transparent}' +
    '.msf-outils-item:active{background:var(--accent-bg)}' +
    '.msf-outils-ico{width:32px;height:32px;flex:0 0 32px;border-radius:10px;display:flex;align-items:center;' +
    'justify-content:center;background:var(--bg);border:1px solid var(--border);color:var(--text2)}' +
    '.msf-outils-ico svg{width:18px;height:18px;color:currentColor}' +
    '.msf-outils-lib{flex:1;min-width:0}' +
    '.msf-outils-n{min-width:20px;height:20px;padding:0 6px;border-radius:10px;background:var(--danger);color:#fff;' +
    'font-size:11px;font-weight:800;line-height:20px;text-align:center}' +
    '.msf-outils-vide{padding:14px;font-size:14px;color:var(--muted);text-align:center}' +
    '}' +
    // Bandeau superadmin de 24 px : le titre et « Simuler : » ne tiennent pas à côté des listes.
    '@media (max-width: 600px){' +
    '.staging-bandeau:has(.msf-imp-slot:not([hidden]))>.msf-imp-msg{display:none}' +
    '.staging-bandeau .msf-imp-slot{margin-left:0;flex:1;min-width:0}' +
    '.staging-bandeau .msf-imp-slot>span{display:none}' +
    '.staging-bandeau .msf-imp-slot select{flex:1;min-width:0;max-width:none;padding:0 4px;line-height:1}' +
    '.staging-bandeau .msf-imp-slot button{padding:0 6px;font-size:10px;line-height:1;flex:0 0 auto}' +
    '}' +
    '@media (min-width: 901px){#msf-outils-poignee{display:none}}';
  document.head.appendChild(st);

  var poignee = null;
  var pastille = null;

  function nonLus() {
    var b = document.getElementById('cw-bubble-badge');
    return b && getComputedStyle(b).display !== 'none' ? (b.textContent || '').trim() : '';
  }

  function outilsDisponibles() {
    var els = Object.keys(LIBELLES).map(function (id) { return document.getElementById(id); });
    Array.prototype.forEach.call(document.querySelectorAll('.mysifa-dock-extra'), function (el) {
      if (els.indexOf(el) < 0) els.push(el);
    });
    // Sans boîte = masqué par display:none, le sien ou celui d'un parent (réglage
    // de Paramètres, post-it réservé au bureau, assistant non ouvert à ce rôle).
    return els.filter(function (el) {
      return el && el.getClientRects().length > 0;
    }).map(function (el) {
      return { el: el, libelle: LIBELLES[el.id] || el.getAttribute('aria-label') || el.title || 'Outil' };
    });
  }

  function fermer() {
    var v = document.querySelector('.msf-outils-voile');
    var f = document.querySelector('.msf-outils-feuille');
    if (v) v.remove();
    if (f) f.remove();
    document.removeEventListener('keydown', surTouche);
  }
  function surTouche(e) { if (e.key === 'Escape') fermer(); }

  function ouvrir() {
    fermer();
    var voile = document.createElement('div');
    voile.className = 'msf-outils-voile';
    voile.addEventListener('click', fermer);
    var feuille = document.createElement('div');
    feuille.className = 'msf-outils-feuille';
    feuille.setAttribute('role', 'menu');
    feuille.setAttribute('aria-label', 'Outils');
    var trait = document.createElement('div');
    trait.className = 'msf-outils-trait';
    feuille.appendChild(trait);

    var outils = outilsDisponibles();
    if (!outils.length) {
      var vide = document.createElement('div');
      vide.className = 'msf-outils-vide';
      vide.textContent = 'Aucun outil sur cette page.';
      feuille.appendChild(vide);
    }
    outils.forEach(function (o) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'msf-outils-item';
      b.setAttribute('role', 'menuitem');
      var ico = document.createElement('span');
      ico.className = 'msf-outils-ico';
      var svg = o.el.querySelector('svg');
      if (svg) ico.appendChild(svg.cloneNode(true));
      var lib = document.createElement('span');
      lib.className = 'msf-outils-lib';
      lib.textContent = o.libelle;
      b.appendChild(ico);
      b.appendChild(lib);
      if (o.libelle === LIBELLES['cw-bubble'] && nonLus()) {
        var n = document.createElement('span');
        n.className = 'msf-outils-n';
        n.textContent = nonLus();
        b.appendChild(n);
      }
      b.addEventListener('click', function () {
        fermer();
        // Différé : plusieurs outils se ferment sur un clic du document, ce clic-ci
        // les refermerait aussitôt ouverts.
        setTimeout(function () { o.el.click(); }, 0);
      });
      feuille.appendChild(b);
    });
    document.body.appendChild(voile);
    document.body.appendChild(feuille);
    document.addEventListener('keydown', surTouche);
  }

  function hauteurMin() { return 70; }
  function hauteurMax() { return innerHeight - 64 - 90; }
  function borner(y) { return Math.max(hauteurMin(), Math.min(hauteurMax(), y)); }

  function placer(y) {
    poignee.style.top = borner(y) + 'px';
  }
  function positionEnregistree() {
    var f = NaN;
    try { f = parseFloat(localStorage.getItem(CLE_POS)); } catch (e) { /* stockage indisponible */ }
    return (isNaN(f) ? 0.62 : f) * innerHeight;
  }

  function brancherGeste() {
    var g = null;
    var vientDeGlisser = false;
    poignee.addEventListener('pointerdown', function (e) {
      g = { y0: e.clientY, top0: poignee.getBoundingClientRect().top, bouge: false, id: e.pointerId };
      try { poignee.setPointerCapture(e.pointerId); } catch (err) { /* navigateur ancien */ }
    });
    poignee.addEventListener('pointermove', function (e) {
      if (!g || e.pointerId !== g.id) return;
      var dy = e.clientY - g.y0;
      if (!g.bouge && Math.abs(dy) < SEUIL_GLISSER) return;
      g.bouge = true;
      poignee.classList.add('glisse');
      placer(g.top0 + dy);
    });
    function lacher(e) {
      if (!g || e.pointerId !== g.id) return;
      var geste = g;
      g = null;
      poignee.classList.remove('glisse');
      vientDeGlisser = geste.bouge;
      if (geste.bouge) {
        try { localStorage.setItem(CLE_POS, String(poignee.getBoundingClientRect().top / innerHeight)); } catch (err) { /* stockage indisponible */ }
      }
    }
    poignee.addEventListener('pointerup', lacher);
    poignee.addEventListener('pointercancel', lacher);
    // Sur le clic, pas au lâcher : ouverte plus tôt, la feuille se glisse sous le
    // doigt et reçoit ce clic, qui déclenche l'outil placé là.
    poignee.addEventListener('click', function () {
      if (!vientDeGlisser) ouvrir();
      vientDeGlisser = false;
    });
  }

  function majPoignee() {
    if (!poignee) return;
    // La barre du bas a déjà son onglet Outils : pas de seconde entrée.
    var onglet = document.querySelector('.mobile-navbar-tab[data-nav="outils"]');
    var viaOnglet = !!(onglet && onglet.getBoundingClientRect().width > 0);
    poignee.hidden = !ecran.matches || viaOnglet || !outilsDisponibles().length;
    var n = nonLus();
    if (pastille.textContent !== n) pastille.textContent = n;
    // L'assistant s'annonce après le premier dessin de la barre du bas.
    var ia = document.getElementById('ai-chat-root');
    if (ia && ia.style.display === 'block' && document.querySelector('.mobile-navbar') &&
        !document.querySelector('.mobile-navbar-tab[data-nav="ai"]') && typeof window.renderMobileNavbar === 'function') {
      window.renderMobileNavbar();
    }
  }

  function demarrer() {
    poignee = document.createElement('button');
    poignee.type = 'button';
    poignee.id = 'msf-outils-poignee';
    poignee.setAttribute('aria-label', 'Outils');
    poignee.title = 'Outils';
    poignee.innerHTML = ICONE_POIGNEE;
    pastille = document.createElement('span');
    pastille.id = 'msf-outils-pastille';
    poignee.appendChild(pastille);
    document.body.appendChild(poignee);
    placer(positionEnregistree());
    brancherGeste();
    majPoignee();
    // Les outils arrivent après le chargement, l'onglet aussi, et les non-lus changent.
    setInterval(majPoignee, 3000);
    setTimeout(majPoignee, 800);
    window.addEventListener('resize', function () {
      placer(positionEnregistree());
      majPoignee();
    });
  }

  window.MySifaOutilsMobile = { ouvrir: ouvrir };

  if (document.body) demarrer();
  else document.addEventListener('DOMContentLoaded', demarrer);
})();
