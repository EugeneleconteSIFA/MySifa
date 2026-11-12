/**
 * MySifa — Mes notes sur téléphone et tablette (écran tactile).
 *
 * - Barre d'outils posée au-dessus du clavier pendant l'écriture : insérer
 *   (« / »), lien MySifa (« @ »), photo, case, puce, titre, gras / italique /
 *   souligné, retrait, annuler / rétablir, commenter, fermer le clavier. Elle
 *   suit le clavier par l'API visualViewport (iOS ne redimensionne pas la
 *   page quand le clavier s'ouvre).
 * - Panneau (actions, commentaires) en feuille qui monte du bas, refermée par
 *   le fond, la poignée ou un glissé vers le bas.
 * Sur ordinateur (pointeur fin), ce fichier ne fait rien.
 */
(function () {
  'use strict';
  var PAGE = window.MySifaNotesPage;
  if (!PAGE) return;
  var S = PAGE.S;

  var tactile = window.matchMedia ? window.matchMedia('(pointer: coarse)') : { matches: false };
  var vv = window.visualViewport;
  var barre = null;
  var _cacher = null;

  var I = {
    texte_insere: '<b>/</b>',
    arobase: '<b>@</b>',
    photo: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>',
    galerie: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/></svg>',
    todo: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="3"/><polyline points="8 12 11 15 16 9"/></svg>',
    puce: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="5" cy="7" r="1.3" fill="currentColor"/><circle cx="5" cy="12" r="1.3" fill="currentColor"/><circle cx="5" cy="17" r="1.3" fill="currentColor"/><line x1="9" y1="7" x2="20" y2="7"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="17" x2="20" y2="17"/></svg>',
    titre: '<b>H</b>',
    gras: '<b>G</b>',
    italique: '<i>I</i>',
    souligne: '<u>S</u>',
    recaler: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 8 5 12 9 16"/><line x1="12" y1="8" x2="20" y2="8"/><line x1="12" y1="16" x2="20" y2="16"/><line x1="5" y1="20" x2="20" y2="20"/><line x1="5" y1="4" x2="20" y2="4"/></svg>',
    decaler: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 8 9 12 5 16"/><line x1="12" y1="8" x2="20" y2="8"/><line x1="12" y1="16" x2="20" y2="16"/><line x1="5" y1="20" x2="20" y2="20"/><line x1="5" y1="4" x2="20" y2="4"/></svg>',
    annuler: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/></svg>',
    retablir: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/></svg>',
    commenter: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4z"/></svg>',
    fini: 'OK',
    styles: '<span style="border-bottom:3px solid var(--ntc-rouge,var(--danger));line-height:1">A</span>',
  };
  var BOUTONS = [
    ['texte_insere', 'Insérer un bloc'], ['arobase', 'Lier un dossier, une machine, une note'],
    ['photo', 'Prendre une photo'], ['galerie', 'Image de la galerie'],
    ['todo', 'Case à cocher'], ['puce', 'Liste à puces'], ['titre', 'Titre'],
    ['gras', 'Gras'], ['italique', 'Italique'], ['souligne', 'Souligné'],
    ['recaler', 'Retrait vers la gauche'], ['decaler', 'Retrait vers la droite'],
    ['styles', 'Couleur, taille, police, alignement'],
    ['annuler', 'Annuler'], ['retablir', 'Rétablir'], ['commenter', 'Commenter la sélection'],
  ];

  function editable(el) {
    return el && el.closest && el.closest('#nt-corps') &&
      (el.classList.contains('pb-txt') || el.classList.contains('pb-cellule')) && el.isContentEditable;
  }

  function creerBarre() {
    if (barre) return barre;
    barre = document.createElement('div');
    barre.id = 'nt-clavier';
    barre.className = 'nt-clavier';
    barre.setAttribute('role', 'toolbar');
    barre.setAttribute('aria-label', 'Outils d\'écriture');
    barre.innerHTML = '<div class="nt-clavier-defile">' + BOUTONS.map(function (b) {
      return '<button type="button" data-k="' + b[0] + '" title="' + b[1] + '" aria-label="' + b[1] + '">' + I[b[0]] + '</button>';
    }).join('') + '</div><button type="button" class="nt-clavier-fini" data-k="fini" aria-label="Fermer le clavier">' + I.fini + '</button>' +
      '<div class="nt-clavier-styles nted" hidden>' + window.MySifaNotesEditeur.sousMenu('couleur') +
      window.MySifaNotesEditeur.sousMenu('texte') + window.MySifaNotesEditeur.sousMenu('aligne') + '</div>';
    document.body.appendChild(barre);
    /* Le doigt ne doit pas retirer le curseur du texte (sinon le clavier se
       ferme) : le focus change au « mousedown » simulé après le toucher. Le
       « touchstart » reste libre, pour faire défiler la barre. */
    barre.addEventListener('mousedown', function (e) {
      if (e.target.closest('[data-k], [data-cmd]')) e.preventDefault();
    });
    barre.addEventListener('click', function (e) {
      var st = e.target.closest('[data-cmd]');
      if (st && S.ed) { S.ed.commande(st.dataset.cmd); return; }
      var b = e.target.closest('[data-k]');
      if (!b || !S.ed) return;
      var k = b.dataset.k;
      if (k === 'fini') { var ae = document.activeElement; if (ae && ae.blur) ae.blur(); return cacher(); }
      if (k === 'titre') return S.ed.commande('h2');
      if (k === 'styles') {
        var pan = barre.querySelector('.nt-clavier-styles');
        pan.hidden = !pan.hidden;
        b.classList.toggle('actif', !pan.hidden);
        return placer();
      }
      S.ed.commande(k);
    });
    return barre;
  }

  /* La barre se pose juste au-dessus du clavier (bord bas de la zone visible). */
  function placer() {
    if (!barre || barre.hidden) return;
    var bas = vv ? vv.offsetTop + vv.height : window.innerHeight;
    barre.style.top = (bas - barre.offsetHeight) + 'px';
    garderCurseurVisible();
  }

  function garderCurseurVisible() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !barre || barre.hidden) return;
    var r = sel.getRangeAt(0).getBoundingClientRect();
    if (!r || (!r.top && !r.bottom)) return;
    var limite = barre.getBoundingClientRect().top - 12;
    var main = document.getElementById('nt-main');
    if (main && r.bottom > limite) main.scrollTop += r.bottom - limite;
  }

  function montrer() {
    if (!tactile.matches || document.body.classList.contains('nt-panneau-ouvert')) return;
    clearTimeout(_cacher);
    creerBarre();
    barre.hidden = false;
    document.body.classList.add('nt-clavier-actif');
    var c = barre.querySelector('[data-k="commenter"]');
    if (c) c.hidden = !(S.ed && S.ed.opts.surCommenter);
    var lecture = S.ed && S.ed.lecture;
    barre.classList.toggle('lecture', !!lecture);
    placer();
  }

  function cacher() {
    if (!barre) return;
    barre.hidden = true;
    document.body.classList.remove('nt-clavier-actif');
  }

  document.addEventListener('focusin', function (e) {
    if (editable(e.target)) montrer();
  });
  document.addEventListener('focusout', function () {
    clearTimeout(_cacher);
    _cacher = setTimeout(function () {
      if (!editable(document.activeElement)) cacher();
    }, 120);
  });
  if (vv) {
    vv.addEventListener('resize', placer);
    vv.addEventListener('scroll', placer);
  }
  window.addEventListener('resize', placer);
  document.addEventListener('selectionchange', function () {
    if (barre && !barre.hidden) garderCurseurVisible();
  });

  /* ── Panneau en feuille du bas ── */

  var fond = null;
  function feuille() {
    if (fond) return;
    fond = document.createElement('div');
    fond.className = 'nt-feuille-fond';
    fond.addEventListener('click', function () { PAGE.basculerPanneau(false); });
    document.body.appendChild(fond);
    var panneau = document.getElementById('nt-panneau');
    if (!panneau) return;
    /* Glisser vers le bas depuis le haut de la feuille la referme. */
    var y0 = null;
    panneau.addEventListener('touchstart', function (e) {
      if (panneau.scrollTop > 0 || window.innerWidth > 768) { y0 = null; return; }
      y0 = e.touches[0].clientY;
    }, { passive: true });
    panneau.addEventListener('touchmove', function (e) {
      if (y0 == null) return;
      var dy = e.touches[0].clientY - y0;
      if (dy > 0) panneau.style.transform = 'translateY(' + dy + 'px)';
    }, { passive: true });
    panneau.addEventListener('touchend', function (e) {
      if (y0 == null) return;
      var dy = (e.changedTouches[0] ? e.changedTouches[0].clientY : y0) - y0;
      panneau.style.transform = '';
      y0 = null;
      if (dy > 90) PAGE.basculerPanneau(false);
    });
  }

  PAGE.sur('note', function () {
    feuille();
    if (document.body.classList.contains('nt-panneau-ouvert')) cacher();
  });
})();
