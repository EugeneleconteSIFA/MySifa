/*
 * MySifa — Paramètres sur téléphone : les tableaux deviennent des cartes.
 *
 * Revue du 08/11/2026 : en 375 px, un tableau de 8 colonnes (Opérations,
 * Clients, Seuils…) faisait 860 px dans un cadre de 313 : deux colonnes
 * visibles, boutons d'action hors de l'écran, titres de catégorie centrés
 * dans le vide. Plutôt que de réécrire chaque rendu, ce fichier pose sur
 * chaque cellule le libellé de sa colonne (data-label) ; la feuille
 * static/settings_mobile.css affiche alors une carte par ligne, sous 900 px
 * seulement. Le bureau n'est pas touché.
 *
 * Les grilles à double entrée gardent le défilement horizontal, avec leur
 * première colonne figée : matrice d'accès et rôles par défaut (.acc-matrix),
 * matrice d'un fournisseur (.f2-mat), résultats SQL (#diag-table).
 *
 * Les rendus refont leurs tableaux à chaque chargement : un observateur
 * repasse dessus (regroupé sur 80 ms).
 */
(function () {
  'use strict';
  var GRILLES = '.acc-matrix, .f2-mat, #diag-table';
  var MQ = window.matchMedia('(max-width:900px)');

  function libelles(table) {
    var tete = table.tHead && table.tHead.rows.length ? table.tHead.rows[table.tHead.rows.length - 1] : null;
    if (!tete) {
      var premiere = table.rows[0];
      if (premiere && premiere.querySelector('th') && !premiere.querySelector('td')) tete = premiere;
    }
    if (!tete) return null;
    var out = [];
    Array.prototype.forEach.call(tete.cells, function (th) {
      var t = (th.textContent || '').replace(/\s+/g, ' ').trim();
      for (var i = 0; i < (th.colSpan || 1); i++) out.push(t);
    });
    return { cellules: out, ligne: tete };
  }

  function preparer(table) {
    if (table.closest(GRILLES)) { table.classList.add('set-grille'); return; }
    var l = libelles(table);
    if (!l) return;
    var n = l.cellules.length;
    table.classList.add('set-cartes');
    Array.prototype.forEach.call(table.rows, function (tr) {
      if (tr === l.ligne || tr.parentNode === table.tHead) return;
      var cells = tr.cells;
      // Ligne d'une seule cellule qui couvre le tableau : intitulé de groupe
      // ou message « Aucun… » — affichée comme un titre, pas comme une carte.
      if (cells.length === 1 && (cells[0].colSpan || 1) >= Math.min(n, 2)) {
        tr.classList.add('set-cat');
        return;
      }
      tr.classList.remove('set-cat');
      var col = 0;
      Array.prototype.forEach.call(cells, function (td) {
        var lib = l.cellules[col] || '';
        col += td.colSpan || 1;
        var aBoutons = !!td.querySelector('button, a.btn, .btn');
        var aTexte = (td.textContent || '').replace(/\s+/g, '').length > 0;
        // Cellule d'actions (dernière, que des boutons) : rangée en pied de carte.
        var actions = aBoutons && (!lib || /^actions?$/i.test(lib) || col >= n) &&
          !Array.prototype.some.call(td.childNodes, function (c) { return c.nodeType === 3 && c.textContent.trim(); }) &&
          !td.querySelector('input, select, textarea');
        td.classList.toggle('set-actions', actions);
        // Plusieurs éléments dans une cellule de lecture (libellé + détail) :
        // regroupés en une colonne, sinon ils se partagent la largeur et le
        // texte se coupe lettre par lettre. Pas de regroupement s'il y a un
        // champ ou un bouton : le code de la page peut les viser directement.
        if (!actions && !td.querySelector('.set-val, input, select, textarea, button')) {
          var noeuds = Array.prototype.filter.call(td.childNodes, function (c) {
            return c.nodeType === 1 || (c.nodeType === 3 && c.textContent.trim());
          });
          if (noeuds.length > 1) {
            var val = document.createElement('span');
            val.className = 'set-val';
            while (td.firstChild) val.appendChild(td.firstChild);
            td.appendChild(val);
          }
        }
        td.classList.toggle('set-vide', !aTexte && !aBoutons && !td.querySelector('input, select, textarea, svg, img'));
        if (actions) td.setAttribute('data-label', '');
        else if (td.getAttribute('data-label') !== lib) td.setAttribute('data-label', lib);
      });
    });
  }

  function tout() {
    if (!MQ.matches) return;
    var main = document.querySelector('.main');
    if (!main) return;
    main.querySelectorAll('table').forEach(function (t) {
      try { preparer(t); } catch (e) { /* un tableau atypique reste tel quel */ }
    });
  }

  var prevu = null;
  function planifier() { clearTimeout(prevu); prevu = setTimeout(tout, 80); }

  function demarrer() {
    var main = document.querySelector('.main');
    if (!main) return;
    try { new MutationObserver(planifier).observe(main, { childList: true, subtree: true }); } catch (e) { /* sans observateur : passage au démarrage seulement */ }
    if (MQ.addEventListener) MQ.addEventListener('change', planifier);
    planifier();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();
