/**
 * MySifa — Mes notes : barre de mise en forme en haut de la note (ordinateur).
 *
 * Comme dans un traitement de texte : annuler / rétablir, style du paragraphe,
 * police (chaque nom écrit dans sa police), taille en points (− [n] +), gras,
 * italique, souligné, barré, couleur du texte et surlignage (nuancier, couleur
 * personnalisée, couleurs récentes), lien, alignement, listes, casse
 * (MAJUSCULES, minuscules, Première Lettre…), effacer la mise en forme.
 * La barre suit la sélection : police, taille, couleurs et styles affichés
 * sont ceux du texte sous le curseur.
 *
 * Les menus viennent de l'éditeur (MySifaNotesEditeur.sousMenu) : mêmes
 * commandes que la barre flottante, le panneau et la barre du téléphone.
 * Sur écran tactile, c'est la barre posée au-dessus du clavier qui sert.
 * Rien dans l'adresse : ni la barre ni ses menus ne sont un endroit (url-etat).
 */
(function () {
  'use strict';
  var PAGE = window.MySifaNotesPage;
  var E = window.MySifaNotesEditeur;
  if (!PAGE || !E) return;
  var S = PAGE.S;

  var tactile = window.matchMedia ? window.matchMedia('(pointer: coarse)') : { matches: false };
  var CLE_REPLIEE = 'mysifa.notes.format_repliee';

  var STYLES_PARA = [
    ['p', 'Texte normal'], ['h1', 'Titre 1'], ['h2', 'Titre 2'], ['h3', 'Titre 3'],
    ['citation', 'Citation'], ['encadre', 'Encadré'], ['code', 'Code'],
  ];

  function svg(corps, w) {
    return '<svg width="' + (w || 16) + '" height="' + (w || 16) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + corps + '</svg>';
  }
  var I = {
    annuler: svg('<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>'),
    retablir: svg('<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>'),
    lien: svg('<path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>'),
    surligneur: svg('<path d="M15 4l5 5-9 9H6v-5z"/><path d="M4 21h8"/>'),
    puce: svg('<circle cx="5" cy="7" r="1.2" fill="currentColor"/><circle cx="5" cy="12" r="1.2" fill="currentColor"/><circle cx="5" cy="17" r="1.2" fill="currentColor"/><line x1="9" y1="7" x2="20" y2="7"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="17" x2="20" y2="17"/>'),
    num: svg('<path d="M4 5h2v4"/><path d="M4 15h3l-3 4h3"/><line x1="10" y1="7" x2="20" y2="7"/><line x1="10" y1="17" x2="20" y2="17"/>'),
    todo: svg('<rect x="4" y="4" width="16" height="16" rx="3"/><polyline points="8 12 11 15 16 9"/>'),
    effacer: svg('<path d="M6 5h12"/><path d="M12 5l-3 14"/><line x1="15" y1="14" x2="21" y2="20"/><line x1="21" y1="14" x2="15" y2="20"/>'),
    plier: svg('<polyline points="6 15 12 9 18 15"/>', 14),
    deplier: svg('<polyline points="6 9 12 15 18 9"/>', 14),
    fleche: '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>',
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function lire(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
  function ecrire(cle, v) { try { if (v == null) localStorage.removeItem(cle); else localStorage.setItem(cle, v); } catch (e) {} }

  var barre = null;
  var pop = null;
  var _plage = null;

  function bouton(cmd, contenu, titre, classe) {
    return '<button type="button" class="ntf-btn' + (classe ? ' ' + classe : '') + '" data-cmd="' + cmd + '" title="' + esc(titre) + '" aria-label="' + esc(titre) + '">' + contenu + '</button>';
  }
  function menu(quoi, contenu, titre, classe) {
    return '<button type="button" class="ntf-btn ntf-menu' + (classe ? ' ' + classe : '') + '" data-pop="' + quoi + '" title="' + esc(titre) + '" aria-label="' + esc(titre) + '" aria-haspopup="true">' + contenu + '</button>';
  }
  var SEP = '<span class="ntf-sep" aria-hidden="true"></span>';

  function html() {
    return '<div class="ntf-ligne" role="toolbar" aria-label="Mise en forme">' +
      bouton('annuler', I.annuler, 'Annuler (Cmd/Ctrl + Z)') +
      bouton('retablir', I.retablir, 'Rétablir (Cmd/Ctrl + Maj + Z)') + SEP +
      menu('para', '<span class="ntf-lib" data-v="para">Texte normal</span>' + I.fleche, 'Style du paragraphe', 'ntf-large') + SEP +
      menu('police', '<span class="ntf-lib" data-v="police">Standard</span>' + I.fleche, 'Police', 'ntf-large ntf-police') + SEP +
      '<span class="ntf-taille">' + bouton('taille:-1', '−', 'Réduire la taille') +
      '<input type="text" inputmode="numeric" class="ntf-taille-val" aria-label="Taille du texte, en points" title="Taille du texte (points)">' +
      bouton('taille:+1', '+', 'Agrandir la taille') + '</span>' + SEP +
      bouton('gras', '<b>G</b>', 'Gras (Cmd/Ctrl + B)') +
      bouton('italique', '<i>I</i>', 'Italique (Cmd/Ctrl + I)') +
      bouton('souligne', '<u>S</u>', 'Souligné (Cmd/Ctrl + U)') +
      bouton('barre', '<s>B</s>', 'Barré (Cmd/Ctrl + Maj + S)') +
      menu('couleur', '<span class="ntf-a">A<i class="ntf-trait" data-v="couleur"></i></span>', 'Couleur du texte') +
      menu('fond', '<span class="ntf-a">' + I.surligneur + '<i class="ntf-trait" data-v="fond"></i></span>', 'Couleur de surlignage') + SEP +
      bouton('lien_texte', I.lien, 'Lien (Cmd/Ctrl + K)') + SEP +
      menu('aligne', '<span data-v="aligne">' + E.ICONES_ALIGNE.gauche + '</span>' + I.fleche, 'Alignement') +
      bouton('puce', I.puce, 'Liste à puces') +
      bouton('num', I.num, 'Liste numérotée') +
      bouton('todo', I.todo, 'Case à cocher') + SEP +
      menu('casse', 'aA' + I.fleche, 'Majuscules, minuscules') +
      bouton('effacer_format', I.effacer, 'Effacer la mise en forme') +
      '</div>' +
      '<button type="button" class="ntf-plier" data-plier="1" title="Masquer la barre de mise en forme" aria-label="Masquer la barre de mise en forme">' + I.plier + '</button>';
  }

  function contenuPop(quoi) {
    if (quoi === 'para') {
      return '<div class="ntf-paras">' + STYLES_PARA.map(function (s) {
        return '<button type="button" class="ntf-para ntf-para-' + s[0] + '" data-para="' + s[0] + '">' + esc(s[1]) + '</button>';
      }).join('') + '</div>';
    }
    if (quoi === 'couleur') return E.sousMenu('couleur:texte');
    if (quoi === 'fond') return E.sousMenu('couleur:fond');
    return E.sousMenu(quoi);
  }

  function monter() {
    var hote = document.querySelector('.nt-barre');
    if (!hote || !S.ed || S.ed.lecture || tactile.matches) { demonter(); return; }
    if (barre && hote.contains(barre)) return peindre();
    barre = document.createElement('div');
    barre.className = 'ntf';
    barre.id = 'nt-format';
    barre.innerHTML = html();
    hote.appendChild(barre);
    barre.classList.toggle('repliee', lire(CLE_REPLIEE) === '1');
    majPlier();

    /* Le clic ne doit pas retirer le curseur du texte. */
    barre.addEventListener('mousedown', function (e) {
      if (e.target.closest('.ntf-taille-val, .nted-plus')) return;
      e.preventDefault();
    });
    barre.addEventListener('click', function (e) {
      if (e.target.closest('[data-plier]')) {
        var r = !barre.classList.contains('repliee');
        barre.classList.toggle('repliee', r);
        ecrire(CLE_REPLIEE, r ? '1' : null);
        fermerPop();
        return majPlier();
      }
      var m = e.target.closest('[data-pop]');
      if (m) return ouvrirPop(m);
      var p = e.target.closest('[data-para]');
      if (p) {
        var etat = E.etat(S.ed);
        fermerPop();
        if (etat.type !== p.dataset.para && !etat.cellule) S.ed.commande(p.dataset.para);
        return;
      }
      var b = e.target.closest('[data-cmd]');
      if (!b || !S.ed) return;
      var cmd = b.dataset.cmd;
      /* Sélecteurs de couleur : le menu reste ouvert pendant le choix. */
      var garder = /^taille:[+-]1$/.test(cmd);
      S.ed.commande(cmd);
      if (!garder) fermerPop();
      peindre();
    });

    var inp = barre.querySelector('.ntf-taille-val');
    inp.addEventListener('focus', function () {
      _plage = _derniere ? _derniere.cloneRange() : null;
      inp.select();
      inp._vientDe = true;
    });
    /* Le relâchement du clic qui donne le focus désélectionnerait la valeur. */
    inp.addEventListener('mouseup', function (e) {
      if (inp._vientDe) { e.preventDefault(); inp._vientDe = false; }
    });
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); appliquerTaille(); }
      if (e.key === 'Escape') { e.preventDefault(); rendrePlage(); peindre(); }
    });
    inp.addEventListener('input', function () { inp.value = inp.value.replace(/[^0-9]/g, '').slice(0, 2); });
    peindre();
  }

  function majPlier() {
    var b = barre && barre.querySelector('[data-plier]');
    if (!b) return;
    var r = barre.classList.contains('repliee');
    b.innerHTML = r ? I.deplier : I.plier;
    b.title = r ? 'Afficher la barre de mise en forme' : 'Masquer la barre de mise en forme';
    b.setAttribute('aria-label', b.title);
  }

  function rendrePlage() {
    if (!_plage) return false;
    var n = _plage.startContainer;
    var el = (n.nodeType === 1 ? n : n.parentNode).closest('.pb-txt, .pb-cellule');
    if (!el || !document.body.contains(el)) { _plage = null; return false; }
    el.focus();
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(_plage);
    _plage = null;
    return true;
  }

  function appliquerTaille() {
    var inp = barre.querySelector('.ntf-taille-val');
    var t = parseInt(inp.value, 10);
    if (!rendrePlage()) {
      if (S.ed.opts.signaler) S.ed.opts.signaler('Sélectionnez d\'abord le texte à mettre en forme.', 'info');
      return peindre();
    }
    if (!(t >= 6 && t <= 96)) {
      if (S.ed.opts.signaler) S.ed.opts.signaler('Taille invalide — valeur entre 6 et 96 points.', 'erreur');
      return peindre();
    }
    S.ed.commande('style:taille:' + t);
    peindre();
  }

  function ouvrirPop(btn) {
    var quoi = btn.dataset.pop;
    if (pop && pop.dataset.quoi === quoi) return fermerPop();
    fermerPop();
    pop = document.createElement('div');
    pop.className = 'ntf-pop nted ntf-pop-' + quoi;
    pop.dataset.quoi = quoi;
    pop.setAttribute('role', 'menu');
    pop.innerHTML = contenuPop(quoi);
    barre.appendChild(pop);
    btn.classList.add('ouvert');
    document.body.classList.add('ntf-menu-ouvert');
    var rb = btn.getBoundingClientRect();
    var rh = barre.getBoundingClientRect();
    var gauche = rb.left - rh.left;
    var max = rh.width - pop.offsetWidth - 4;
    pop.style.left = Math.max(0, Math.min(gauche, max)) + 'px';
    pop.addEventListener('mousedown', function (e) {
      if (e.target.closest('.nted-plus')) return;
      e.preventDefault();
    });
    peindre();
  }

  function fermerPop() {
    if (pop) { pop.remove(); pop = null; }
    document.body.classList.remove('ntf-menu-ouvert');
    if (barre) barre.querySelectorAll('.ouvert').forEach(function (b) { b.classList.remove('ouvert'); });
  }

  function demonter() {
    fermerPop();
    if (barre) { barre.remove(); barre = null; }
  }

  var LIB_PARA = {};
  STYLES_PARA.forEach(function (s) { LIB_PARA[s[0]] = s[1]; });

  function peindre() {
    if (!barre || !S.ed) return;
    var sel = window.getSelection();
    var dans = sel && sel.rangeCount && S.ed.corps.contains(sel.getRangeAt(0).commonAncestorContainer);
    var etat = dans ? E.etat(S.ed) : null;
    barre.classList.toggle('inactive', !etat);
    if (!etat) return;
    var lp = barre.querySelector('[data-v="para"]');
    if (lp) lp.textContent = etat.cellule ? 'Tableau' : (LIB_PARA[etat.type] || 'Texte normal');
    var police = null;
    E.POLICES.forEach(function (p) { if (p.cle === etat.police) police = p; });
    var lpo = barre.querySelector('[data-v="police"]');
    if (lpo && police) { lpo.textContent = police.nom; lpo.style.fontFamily = police.pile || ''; }
    var inp = barre.querySelector('.ntf-taille-val');
    if (inp && document.activeElement !== inp) inp.value = etat.taille || '';
    var tc = barre.querySelector('[data-v="couleur"]');
    if (tc) tc.style.background = etat.couleur || 'currentColor';
    var tf = barre.querySelector('[data-v="fond"]');
    if (tf) { tf.style.background = etat.fond || 'transparent'; tf.classList.toggle('vide', !etat.fond); }
    var al = barre.querySelector('[data-v="aligne"]');
    if (al) al.innerHTML = E.ICONES_ALIGNE[etat.aligne] || E.ICONES_ALIGNE.gauche;
    var actifs = { gras: etat.gras, italique: etat.italique, souligne: etat.souligne, barre: etat.barre,
      puce: etat.type === 'puce', num: etat.type === 'num', todo: etat.type === 'todo' };
    barre.querySelectorAll('.ntf-ligne > [data-cmd]').forEach(function (b) {
      b.classList.toggle('actif', !!actifs[b.dataset.cmd]);
    });
    /* Le panneau d'actions montre les mêmes menus : même état. */
    var pa = document.querySelector('.nt-pa-styles');
    if (pa) E.peindreEtat(pa, S.ed, etat);
    if (pop) {
      E.peindreEtat(pop, S.ed, etat);
      pop.querySelectorAll('[data-para]').forEach(function (b) { b.classList.toggle('actif', b.dataset.para === etat.type); });
    }
  }

  /* Dernière sélection faite dans la note : le champ de taille prend le focus,
     il faut pouvoir la rendre au moment d'appliquer. */
  var _derniere = null;
  var _t = null;
  document.addEventListener('selectionchange', function () {
    if (!barre) return;
    var sel = window.getSelection();
    if (sel && sel.rangeCount && S.ed && S.ed.corps.contains(sel.getRangeAt(0).commonAncestorContainer)) {
      _derniere = sel.isCollapsed ? null : sel.getRangeAt(0).cloneRange();
    }
    clearTimeout(_t);
    _t = setTimeout(peindre, 50);
  });
  document.addEventListener('mousedown', function (e) {
    if (pop && !e.target.closest('#nt-format')) fermerPop();
  }, true);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && pop) { fermerPop(); }
  });
  /* Ctrl/Cmd + Z, raccourcis, frappe d'un collègue : l'état suit. */
  document.addEventListener('input', function (e) {
    if (barre && S.ed && S.ed.corps.contains(e.target)) { clearTimeout(_t); _t = setTimeout(peindre, 80); }
  }, true);

  PAGE.sur('note', function () { setTimeout(monter, 0); });
  PAGE.sur('fermeture', demonter);
  if (tactile.addEventListener) tactile.addEventListener('change', function () { if (S.ed) monter(); else demonter(); });
})();
