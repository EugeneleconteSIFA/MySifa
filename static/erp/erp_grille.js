/* Nouvel ERP — grille de données.
 *
 *   var g = ERP.grille(conteneur, {
 *     colonnes: [{cle, libelle, type, largeur, total, rendu}],  // type : texte | nombre | qte | montant | date | statut
 *                                                       // qte : millièmes ; rendu(ligne) -> nœud DOM (facultatif)
 *     lignes: [...],                                       // objets, toutes en mémoire
 *     cle: 'id',                                           // identifiant de ligne
 *     ouvrir: function (ligne) {},                         // Entrée ou double-clic
 *     statuts: {valeur: {libelle, ton}},                   // pour type statut ; ton : ok | warn | danger | neutre | accent
 *     nom: 'ventes.commandes',                             // mémorise tri et filtres (localStorage)
 *     selection: function (ligne) {},                      // ligne courante (clavier ou clic)
 *     // colonne : classe(ligne) -> classe CSS de la cellule (ex. 'retard')
 *   });
 *   g.maj(nouvellesLignes);
 *
 * Rendu virtualisé : seules les lignes visibles existent dans le DOM, une
 * grille de 10 000 lignes défile comme une de 50. L'en-tête et ses filtres ne
 * sont jamais reconstruits : un filtre garde son focus pendant la frappe.
 *
 * Montants en centimes entiers (principe 4 de docs/erp/ROADMAP.md).
 *
 * Clavier, une fois la grille focalisée : ↑ ↓ PageUp PageDown Début Fin pour
 * se déplacer, Entrée pour ouvrir, Ctrl+F pour le premier filtre, Échap dans un
 * filtre pour le vider.
 */
(function () {
  'use strict';

  var HAUTEUR = 34;         // hauteur de ligne, px — doit suivre .erp-g-ligne
  var MARGE = 8;            // lignes rendues en plus hors écran

  var NF_MONTANT = new Intl.NumberFormat('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  var NF_NOMBRE = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 3});

  function fmt(type, v) {
    if (v == null || v === '') return '';
    if (type === 'montant') return NF_MONTANT.format(v / 100) + ' €';
    if (type === 'nombre') return NF_NOMBRE.format(v);
    if (type === 'qte') return NF_NOMBRE.format(v / 1000);
    if (type === 'date') {
      var s = String(v);
      return s.length >= 10 ? s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) : s;
    }
    return String(v);
  }

  function sansAccents(s) {
    return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  // Filtre de colonne. Texte : contient (insensible aux accents). Nombre /
  // montant : « >100 », « <=5 », « 10..20 », ou valeur exacte. Date : « 2026-10 »
  // préfixe ISO, ou « 14/10 », « 10/2026 » dans le format affiché.
  function predicat(col, saisie) {
    var q = saisie.trim();
    if (!q) return null;
    if (col.type === 'nombre' || col.type === 'montant' || col.type === 'qte') {
      var mult = col.type === 'montant' ? 100 : col.type === 'qte' ? 1000 : 1;
      var num = function (t) { return parseFloat(t.replace(/\s/g, '').replace(',', '.')) * mult; };
      var m = q.match(/^(>=|<=|>|<|=)?\s*(-?[\d\s,.]+)$/);
      var r = q.match(/^(-?[\d\s,.]+)\s*\.\.\s*(-?[\d\s,.]+)$/);
      if (r) { var a = num(r[1]), b = num(r[2]); return function (v) { return v != null && v >= a && v <= b; }; }
      if (m) {
        var x = num(m[2]), op = m[1] || '=';
        if (isNaN(x)) return function () { return false; };
        return function (v) {
          if (v == null) return false;
          return op === '>' ? v > x : op === '<' ? v < x : op === '>=' ? v >= x : op === '<=' ? v <= x : Math.abs(v - x) < 0.5;
        };
      }
      return function () { return false; };
    }
    if (col.type === 'date') {
      return function (v) { return v != null && (String(v).indexOf(q) === 0 || fmt('date', v).indexOf(q) >= 0); };
    }
    var n = sansAccents(q);
    return function (v, ligne) {
      var aff = col.type === 'statut' && col._statuts && col._statuts[v] ? col._statuts[v].libelle : v;
      return v != null && sansAccents(aff).indexOf(n) >= 0;
    };
  }

  function lireMemoire(nom) {
    if (!nom) return null;
    try { return JSON.parse(localStorage.getItem('erp_grille_' + nom) || 'null'); } catch (e) { return null; }
  }
  function ecrireMemoire(nom, v) {
    if (!nom) return;
    try { localStorage.setItem('erp_grille_' + nom, JSON.stringify(v)); } catch (e) { /* stockage indisponible */ }
  }

  function grille(conteneur, opts) {
    var h = window.ERP.h;
    var cols = opts.colonnes.map(function (c) {
      return Object.assign({type: 'texte', largeur: 140}, c, {_statuts: opts.statuts || null});
    });
    var memo = lireMemoire(opts.nom) || {};
    var G = {
      toutes: opts.lignes || [],
      vues: [],
      tri: memo.tri || null,              // {cle, sens: 1 | -1}
      filtres: memo.filtres || {},        // cle -> saisie
      courant: 0,
    };

    var gabarit = cols.map(function (c) { return c.largeur + 'px'; }).join(' ');
    var largeurTotale = cols.reduce(function (s, c) { return s + c.largeur; }, 0);

    // ── Structure ────────────────────────────────────────────────────
    var racine = h('div', {className: 'erp-g', tabindex: '0', role: 'grid', 'aria-rowcount': '0'});
    var barre = h('div', {className: 'erp-g-barre'});
    var compte = h('span', {className: 'erp-g-compte'});
    var btnRaz = h('button', {className: 'erp-btn erp-btn-petit', type: 'button', onclick: function () {
      G.filtres = {};
      entrees.forEach(function (i) { i.value = ''; });
      appliquer(true);
    }}, 'Effacer les filtres');
    var btnCsv = h('button', {className: 'erp-btn erp-btn-petit', type: 'button', onclick: exporter}, 'Exporter CSV');
    barre.appendChild(compte);
    barre.appendChild(h('span', {className: 'erp-g-espace'}));
    barre.appendChild(btnRaz);
    barre.appendChild(btnCsv);

    var defil = h('div', {className: 'erp-g-defil'});
    var tete = h('div', {className: 'erp-g-tete', style: 'grid-template-columns:' + gabarit + ';width:' + largeurTotale + 'px'});
    var filtresL = h('div', {className: 'erp-g-filtres', style: 'grid-template-columns:' + gabarit + ';width:' + largeurTotale + 'px'});
    var corps = h('div', {className: 'erp-g-corps', style: 'width:' + largeurTotale + 'px'});
    var pied = h('div', {className: 'erp-g-pied', style: 'grid-template-columns:' + gabarit + ';width:' + largeurTotale + 'px'});
    var entetes = [], entrees = [];

    cols.forEach(function (c, i) {
      var th = h('div', {
        className: 'erp-g-th' + (/^(nombre|montant|qte)$/.test(c.type) ? ' num' : ''),
        role: 'columnheader', title: 'Trier par ' + c.libelle,
        onclick: function () { trier(c.cle); },
      }, h('span', {text: c.libelle}), h('span', {className: 'erp-g-sens'}));
      entetes.push(th);
      tete.appendChild(th);
      var ph = /^(nombre|montant|qte)$/.test(c.type) ? '>100, 10..20' : c.type === 'date' ? 'aaaa-mm, jj/mm' : 'Filtrer';
      var inp = h('input', {className: 'erp-g-filtre', type: 'text', placeholder: ph, 'aria-label': 'Filtre ' + c.libelle});
      inp.value = G.filtres[c.cle] || '';
      inp.addEventListener('input', function () { G.filtres[c.cle] = inp.value; appliquer(true); });
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { inp.value = ''; G.filtres[c.cle] = ''; appliquer(true); e.stopPropagation(); }
        if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); racine.focus(); }
      });
      entrees.push(inp);
      filtresL.appendChild(h('div', {className: 'erp-g-fcell'}, inp));
    });

    defil.appendChild(tete);
    defil.appendChild(filtresL);
    defil.appendChild(corps);
    defil.appendChild(pied);
    racine.appendChild(barre);
    racine.appendChild(defil);
    conteneur.appendChild(racine);

    // ── Données ──────────────────────────────────────────────────────
    // Un nouveau tri ou un nouveau filtre ramène en tête de liste : la ligne
    // courante d'avant n'a plus de sens dans la nouvelle vue.
    function appliquer(enTete) {
      var preds = [];
      cols.forEach(function (c) {
        var p = predicat(c, G.filtres[c.cle] || '');
        if (p) preds.push([c.cle, p]);
      });
      var v = preds.length ? G.toutes.filter(function (l) {
        for (var i = 0; i < preds.length; i++) if (!preds[i][1](l[preds[i][0]], l)) return false;
        return true;
      }) : G.toutes.slice();
      if (G.tri) {
        var k = G.tri.cle, s = G.tri.sens;
        v.sort(function (a, b) {
          var x = a[k], y = b[k];
          if (x == null && y == null) return 0;
          if (x == null) return 1;
          if (y == null) return -1;
          if (typeof x === 'number' && typeof y === 'number') return (x - y) * s;
          return String(x).localeCompare(String(y), 'fr', {numeric: true}) * s;
        });
      }
      G.vues = v;
      G.courant = enTete ? 0 : Math.min(G.courant, Math.max(0, v.length - 1));
      if (enTete) defil.scrollTop = 0;
      ecrireMemoire(opts.nom, {tri: G.tri, filtres: G.filtres});
      corps.style.height = (v.length * HAUTEUR) + 'px';
      racine.setAttribute('aria-rowcount', String(v.length));
      var filtre = preds.length > 0;
      compte.textContent = NF_NOMBRE.format(v.length) + (filtre ? ' / ' + NF_NOMBRE.format(G.toutes.length) : '') + ' ligne' + (v.length > 1 ? 's' : '');
      btnRaz.style.display = filtre ? '' : 'none';
      entetes.forEach(function (th, i) {
        var c = cols[i], actif = G.tri && G.tri.cle === c.cle;
        th.classList.toggle('trie', !!actif);
        th.lastChild.textContent = actif ? (G.tri.sens > 0 ? '▲' : '▼') : '';
        entrees[i].classList.toggle('actif', !!(G.filtres[c.cle] || '').trim());
      });
      renderTotaux();
      renderLignes(true);
      if (opts.selection) opts.selection(G.vues[G.courant] || null);
    }

    function trier(cle) {
      if (!G.tri || G.tri.cle !== cle) G.tri = {cle: cle, sens: 1};
      else if (G.tri.sens === 1) G.tri.sens = -1;
      else G.tri = null;
      appliquer(true);
    }

    function renderTotaux() {
      pied.textContent = '';
      var a = false;
      cols.forEach(function (c, i) {
        var txt = '';
        if (c.total) {
          a = true;
          var s = 0;
          for (var j = 0; j < G.vues.length; j++) s += G.vues[j][c.cle] || 0;
          txt = fmt(c.type, s);
        } else if (i === 0) txt = 'Total';
        pied.appendChild(h('div', {className: 'erp-g-td' + (c.total ? ' num' : ''), text: txt}));
      });
      pied.style.display = a ? '' : 'none';
    }

    var dernier = {debut: -1, fin: -1};
    function renderLignes(force) {
      var haut = defil.scrollTop, vis = defil.clientHeight;
      var debut = Math.max(0, Math.floor(haut / HAUTEUR) - MARGE);
      var fin = Math.min(G.vues.length, Math.ceil((haut + vis) / HAUTEUR) + MARGE);
      if (!force && debut === dernier.debut && fin === dernier.fin) return;
      dernier = {debut: debut, fin: fin};
      var frag = document.createDocumentFragment();
      for (var i = debut; i < fin; i++) frag.appendChild(ligneDom(G.vues[i], i));
      corps.textContent = '';
      corps.appendChild(frag);
    }

    function ligneDom(l, i) {
      var tr = h('div', {
        className: 'erp-g-ligne' + (i === G.courant ? ' courant' : '') + (i % 2 ? ' impaire' : ''),
        role: 'row', 'aria-rowindex': String(i + 1),
        style: 'top:' + (i * HAUTEUR) + 'px;grid-template-columns:' + gabarit,
      });
      tr.addEventListener('click', function () { allerA(i, false); });
      tr.addEventListener('dblclick', function () { if (opts.ouvrir) opts.ouvrir(l); });
      cols.forEach(function (c) {
        var v = l[c.cle];
        var td = h('div', {className: 'erp-g-td' + (/^(nombre|montant|qte)$/.test(c.type) ? ' num' : '') + (c.classe ? ' ' + (c.classe(l) || '') : ''), role: 'gridcell'});
        if (c.rendu) {
          var n = c.rendu(l);
          if (n != null) td.appendChild(typeof n === 'string' ? document.createTextNode(n) : n);
        } else if (c.type === 'statut' && v != null) {
          var st = (opts.statuts || {})[v] || {libelle: String(v), ton: 'neutre'};
          td.appendChild(h('span', {className: 'erp-pastille ton-' + st.ton, text: st.libelle}));
        } else {
          td.textContent = fmt(c.type, v);
        }
        tr.appendChild(td);
      });
      return tr;
    }

    // ── Clavier et défilement ────────────────────────────────────────
    function allerA(i, defiler) {
      if (!G.vues.length) return;
      G.courant = Math.max(0, Math.min(G.vues.length - 1, i));
      if (opts.selection) opts.selection(G.vues[G.courant]);
      if (defiler !== false) {
        var y = G.courant * HAUTEUR;
        var entete = tete.offsetHeight + filtresL.offsetHeight;
        var vis = defil.clientHeight - entete - pied.offsetHeight;
        if (y < defil.scrollTop) defil.scrollTop = y;
        else if (y + HAUTEUR > defil.scrollTop + vis) defil.scrollTop = y + HAUTEUR - vis;
      }
      renderLignes(true);
    }

    racine.addEventListener('keydown', function (e) {
      if (e.target.tagName === 'INPUT') return;
      var page = Math.max(1, Math.floor(defil.clientHeight / HAUTEUR) - 3);
      var k = e.key;
      if (k === 'ArrowDown') allerA(G.courant + 1);
      else if (k === 'ArrowUp') allerA(G.courant - 1);
      else if (k === 'PageDown') allerA(G.courant + page);
      else if (k === 'PageUp') allerA(G.courant - page);
      else if (k === 'Home') allerA(0);
      else if (k === 'End') allerA(G.vues.length - 1);
      else if (k === 'Enter') { if (opts.ouvrir && G.vues[G.courant]) opts.ouvrir(G.vues[G.courant]); }
      else if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === 'f') { entrees[0].focus(); }
      else return;
      e.preventDefault();
    });

    var rafPrevu = false;
    defil.addEventListener('scroll', function () {
      if (rafPrevu) return;
      rafPrevu = true;
      requestAnimationFrame(function () { rafPrevu = false; renderLignes(false); });
    });
    // La hauteur visible n'est connue qu'une fois la grille posée dans la page,
    // et change avec la fenêtre : on redessine à chaque changement de taille.
    if (window.ResizeObserver) new ResizeObserver(function () { renderLignes(true); }).observe(defil);
    else window.addEventListener('resize', function () { renderLignes(true); });

    // ── Export ───────────────────────────────────────────────────────
    function exporter() {
      var cel = function (s) { s = String(s == null ? '' : s); return /[";\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
      var lignes = [cols.map(function (c) { return cel(c.libelle); }).join(';')];
      G.vues.forEach(function (l) {
        lignes.push(cols.map(function (c) {
          var v = l[c.cle];
          if (c.type === 'montant') return v == null ? '' : NF_MONTANT.format(v / 100);
          if (c.type === 'statut' && opts.statuts && opts.statuts[v]) return cel(opts.statuts[v].libelle);
          return cel(fmt(c.type, v));
        }).join(';'));
      });
      var blob = new Blob(['﻿' + lignes.join('\r\n')], {type: 'text/csv;charset=utf-8'});
      var a = h('a', {href: URL.createObjectURL(blob), download: (opts.nom || 'export') + '.csv'});
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    }

    appliquer();

    return {
      maj: function (lignes) { G.toutes = lignes || []; appliquer(); },
      lignesVisibles: function () { return G.vues.slice(); },
      focus: function () { racine.focus(); },
    };
  }

  window.ERP.grille = grille;
  window.ERP.fmtGrille = fmt;
})();
