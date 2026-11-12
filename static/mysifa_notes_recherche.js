/**
 * MySifa — Mes notes : rechercher dans la note ouverte (Cmd/Ctrl + F).
 *
 * Les occurrences sont surlignées par l'API CSS Custom Highlight : rien n'est
 * inséré dans le texte, donc ni la frappe ni la rédaction à plusieurs ne
 * sont dérangées. Sans cette API (navigateur ancien), seule l'occurrence
 * courante est sélectionnée. Recherche sans casse ni accents.
 * Hors adresse : c'est une saisie en cours (règle url-etat).
 */
(function () {
  'use strict';
  var PAGE = window.MySifaNotesPage;
  if (!PAGE) return;

  var etat = { ouvert: false, q: '', trouves: [], k: -1 };
  var HL = !!(window.CSS && CSS.highlights && window.Highlight);
  var _obs = null;
  var _t = null;

  function plier(c) {
    return c.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().charAt(0) || c;
  }

  /* Texte de chaque bloc, avec la position de chaque nœud texte. */
  function morceaux() {
    var corps = document.getElementById('nt-corps');
    if (!corps) return [];
    var out = [];
    corps.querySelectorAll('.pb-txt, .pb-legende, .pb-cellule').forEach(function (el) {
      var noeuds = [];
      var txt = '';
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      var n;
      while ((n = w.nextNode())) {
        noeuds.push({ n: n, debut: txt.length });
        txt += n.data;
      }
      if (txt) out.push({ el: el, txt: txt, noeuds: noeuds });
    });
    return out;
  }

  function position(m, i) {
    for (var k = m.noeuds.length - 1; k >= 0; k--) {
      if (i >= m.noeuds[k].debut) return { n: m.noeuds[k].n, o: i - m.noeuds[k].debut };
    }
    return { n: m.noeuds[0].n, o: 0 };
  }

  function chercher() {
    etat.trouves = [];
    var q = etat.q.trim();
    if (!q) return peindre();
    var cible = Array.prototype.map.call(q, plier).join('');
    morceaux().forEach(function (m) {
      var plie = Array.prototype.map.call(m.txt, plier).join('');
      var i = plie.indexOf(cible);
      while (i >= 0) {
        var a = position(m, i);
        var b = position(m, i + cible.length);
        try {
          var r = document.createRange();
          r.setStart(a.n, a.o);
          r.setEnd(b.n, b.o);
          etat.trouves.push(r);
        } catch (e) {}
        i = plie.indexOf(cible, i + cible.length);
      }
    });
    if (etat.k >= etat.trouves.length) etat.k = etat.trouves.length - 1;
    if (etat.k < 0 && etat.trouves.length) etat.k = 0;
    peindre();
  }

  function peindre() {
    var nb = document.getElementById('nt-cherche-nb');
    if (nb) {
      nb.textContent = !etat.q.trim() ? '' : etat.trouves.length ? (etat.k + 1) + ' / ' + etat.trouves.length : 'Aucun résultat';
      nb.classList.toggle('vide', !!etat.q.trim() && !etat.trouves.length);
    }
    if (!HL) return;
    CSS.highlights.delete('nt-cherche');
    CSS.highlights.delete('nt-cherche-cur');
    if (!etat.trouves.length) return;
    CSS.highlights.set('nt-cherche', new Highlight(...etat.trouves));
    if (etat.k >= 0) CSS.highlights.set('nt-cherche-cur', new Highlight(etat.trouves[etat.k]));
  }

  function montrer() {
    var r = etat.trouves[etat.k];
    if (!r) return;
    var main = document.getElementById('nt-main');
    var rect = r.getBoundingClientRect();
    if (main && (rect.top < 120 || rect.bottom > window.innerHeight - 80)) {
      main.scrollTop += rect.top - window.innerHeight / 3;
    }
    if (!HL) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r.cloneRange());
    }
  }

  function aller(sens) {
    if (!etat.trouves.length) return;
    etat.k = (etat.k + sens + etat.trouves.length) % etat.trouves.length;
    peindre();
    montrer();
  }

  function ouvrir() {
    if (!document.getElementById('nt-corps')) return;
    var barre = document.getElementById('nt-cherche');
    if (!barre) {
      barre = document.createElement('div');
      barre.id = 'nt-cherche';
      barre.className = 'nt-cherche';
      barre.setAttribute('role', 'search');
      barre.innerHTML =
        '<input type="search" id="nt-cherche-q" placeholder="Rechercher dans la note" autocomplete="off" spellcheck="false">' +
        '<span class="nt-cherche-nb" id="nt-cherche-nb"></span>' +
        '<button type="button" data-s="-1" title="Précédent (Maj + Entrée)" aria-label="Précédent">↑</button>' +
        '<button type="button" data-s="1" title="Suivant (Entrée)" aria-label="Suivant">↓</button>' +
        '<button type="button" data-s="0" title="Fermer (Échap)" aria-label="Fermer">×</button>';
      document.getElementById('nt-main').appendChild(barre);
      var inp = barre.querySelector('input');
      inp.addEventListener('input', function () { etat.q = inp.value; etat.k = 0; chercher(); montrer(); });
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); aller(e.shiftKey ? -1 : 1); }
        if (e.key === 'Escape') { e.preventDefault(); fermer(true); }
      });
      barre.addEventListener('mousedown', function (e) {
        var b = e.target.closest('[data-s]');
        if (!b) return;
        e.preventDefault();
        var s = Number(b.dataset.s);
        if (s) aller(s); else fermer(false);
      });
    }
    etat.ouvert = true;
    barre.hidden = false;
    /* Le texte sélectionné devient la recherche, comme partout ailleurs. */
    var sel = window.getSelection();
    var choisi = sel && !sel.isCollapsed ? sel.toString().trim() : '';
    var inp2 = barre.querySelector('input');
    if (choisi && choisi.length < 80 && choisi.indexOf('\n') < 0) { inp2.value = choisi; etat.q = choisi; }
    inp2.focus();
    inp2.select();
    chercher();
    surveiller();
  }

  /* Le texte change (frappe, autre éditeur) : on recalcule les occurrences. */
  function surveiller() {
    if (_obs) _obs.disconnect();
    var corps = document.getElementById('nt-corps');
    if (!corps || !window.MutationObserver) return;
    _obs = new MutationObserver(function () {
      clearTimeout(_t);
      _t = setTimeout(chercher, 150);
    });
    _obs.observe(corps, { childList: true, subtree: true, characterData: true });
  }

  function fermer(placerCurseur) {
    var r = etat.trouves[etat.k];
    etat.ouvert = false;
    etat.trouves = [];
    if (_obs) { _obs.disconnect(); _obs = null; }
    if (HL) { CSS.highlights.delete('nt-cherche'); CSS.highlights.delete('nt-cherche-cur'); }
    var barre = document.getElementById('nt-cherche');
    if (barre) barre.hidden = true;
    /* Échap : on reprend l'écriture sur l'occurrence trouvée. */
    if (placerCurseur && r) {
      var el = r.startContainer.parentElement && r.startContainer.parentElement.closest('[contenteditable="true"]');
      if (el) {
        el.focus();
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      }
    }
  }

  document.addEventListener('keydown', function (e) {
    var mod = e.metaKey || e.ctrlKey;
    if (mod && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'f' && document.getElementById('nt-corps')) {
      e.preventDefault();
      ouvrir();
    }
    if (mod && e.key.toLowerCase() === 'g' && etat.ouvert) {
      e.preventDefault();
      aller(e.shiftKey ? -1 : 1);
    }
  });

  PAGE.actions.chercher = function () { ouvrir(); };
  PAGE.sur('fermeture', function () { if (etat.ouvert) fermer(false); });
  PAGE.chercher = { ouvrir: ouvrir, fermer: fermer };
})();
