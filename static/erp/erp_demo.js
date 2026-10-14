/* Nouvel ERP — vitrine des composants (Paramètres › Composants).
 *
 * Données fictives générées dans le navigateur, toujours les mêmes (graine
 * fixe) : sert à valider le design system avant les écrans métier.
 */
(function () {
  'use strict';

  function alea(graine) {
    var s = graine >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  var CLIENTS = ['Atelier Durand', 'Brasserie du Nord', 'Cave Saint-Martin', 'Domaine des Côtes', 'Épicerie Lemoine',
    'Fromagerie Blanc', 'Laboratoires Orsel', 'Maison Perrin', 'Parfums Azur', 'Pharma Delvaux',
    'Biscuiterie Morel', 'Conserverie Ouest', 'Distillerie Garnier', 'Cosmétiques Iris', 'Huilerie Fabre'];
  var ARTICLES = ['Étiquette 100x150 couché', 'Étiquette vin 90x120 vergé', 'Bobine thermique 58mm', 'Étiquette PP blanc 50x30',
    'Sleeve PET 250ml', 'Étiquette or à chaud', 'Étiquette transparente 80x40', 'Étiquette pharma 35x20'];
  var STATUTS = {
    attente: {libelle: 'En attente', ton: 'neutre'},
    en_cours: {libelle: 'En cours', ton: 'accent'},
    partielle: {libelle: 'Livrée partiellement', ton: 'warn'},
    soldee: {libelle: 'Soldée', ton: 'ok'},
    bloquee: {libelle: 'Bloquée', ton: 'danger'},
  };
  var CLES_STATUTS = Object.keys(STATUTS);

  function iso(d) { return d.toISOString().slice(0, 10); }

  function commandes(n) {
    var r = alea(20261014), out = [], t0 = Date.UTC(2025, 0, 2);
    for (var i = 0; i < n; i++) {
      var d = new Date(t0 + Math.floor(r() * 650) * 86400000);
      var liv = new Date(d.getTime() + (7 + Math.floor(r() * 35)) * 86400000);
      var qte = (1 + Math.floor(r() * 80)) * 1000;
      var pu = 8 + Math.floor(r() * 60);                       // centimes le mille → €/mille
      out.push({
        id: i + 1,
        numero: 'C' + String(26000 + i).padStart(6, '0'),
        date: iso(d),
        client: CLIENTS[Math.floor(r() * CLIENTS.length)],
        article: ARTICLES[Math.floor(r() * ARTICLES.length)],
        quantite: qte,
        montant_ht: Math.round(qte * pu * 10),                   // centimes
        livraison: iso(liv),
        statut: CLES_STATUTS[Math.floor(r() * r() * CLES_STATUTS.length)],
      });
    }
    return out;
  }

  window.ERP.ecrans['/parametres/composants'] = function (main, ctx) {
    var h = ctx.h;
    main.classList.add('plein');
    var info = h('p', {className: 'erp-demo-info'},
      'Grille : 10 000 commandes fictives. Clic sur un en-tête pour trier (3 états), filtres sous les en-têtes ',
      '(montant : « >5000 », « 1000..2000 » ; date : « 2026-03 »), ↑ ↓ PageUp PageDown Début Fin, Entrée pour ouvrir, Ctrl+F pour filtrer.');
    var sortie = h('p', {className: 'erp-demo-info', text: 'Ligne ouverte : —'});
    var zone = h('div', {className: 'erp-zone'});
    main.appendChild(info);
    main.appendChild(sortie);
    main.appendChild(zone);
    var g = window.ERP.grille(zone, {
      nom: 'demo.commandes',
      cle: 'id',
      colonnes: [
        {cle: 'numero', libelle: 'N° commande', largeur: 120},
        {cle: 'date', libelle: 'Date', type: 'date', largeur: 100},
        {cle: 'client', libelle: 'Client', largeur: 190},
        {cle: 'article', libelle: 'Article', largeur: 230},
        {cle: 'quantite', libelle: 'Quantité', type: 'nombre', largeur: 110, total: true},
        {cle: 'montant_ht', libelle: 'Montant HT', type: 'montant', largeur: 130, total: true},
        {cle: 'livraison', libelle: 'Livraison', type: 'date', largeur: 100},
        {cle: 'statut', libelle: 'Statut', type: 'statut', largeur: 170},
      ],
      statuts: STATUTS,
      lignes: commandes(10000),
      ouvrir: function (l) { sortie.textContent = 'Ligne ouverte : ' + l.numero + ' · ' + l.client; },
    });
    requestAnimationFrame(function () { g.focus(); });
  };
})();
