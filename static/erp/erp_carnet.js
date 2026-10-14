/* Nouvel ERP — tableaux de bord par ligne (le « TDB » de RVGI).
 *
 * L'ADV travaille ligne par ligne : une commande de neuf lignes, ce sont neuf
 * dates d'expédition à tenir. Une ligne par ligne de pièce, les dates
 * dépassées en rouge, les lignes soldées masquées par défaut, et en bas le
 * détail de la ligne sélectionnée (quantités, stock, format).
 *
 * ERP.carnet(main, ctx, conf) est appelé par la liste de erp_pieces.js quand
 * la vue « Par ligne » est choisie.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  function aujourdhui() { return new Date().toISOString().slice(0, 10); }

  // Préfixe « of_ » : la grille n'a qu'une table d'états, partagée avec la
  // colonne Position dont les codes (valide, partiel, solde) sont les mêmes.
  var SITUATION_OF = {
    of_a_ordonnancer: {libelle: 'À ordonnancer', ton: 'warn'},
    of_valide: {libelle: 'Lancé', ton: 'accent'},
    of_partiel: {libelle: 'En production', ton: 'warn'},
    of_solde: {libelle: 'Terminé', ton: 'ok'},
    // BAT (module BAT de MySifa) — préfixe « bat_ » pour la même raison
    bat_non_rattache: {libelle: 'BAT à rattacher', ton: 'danger'},
    bat_a_faire: {libelle: 'BAT à faire', ton: 'danger'},
    bat_en_attente: {libelle: 'BAT en attente', ton: 'warn'},
    bat_valide: {libelle: 'BAT validé', ton: 'ok'},
  };

  // Ce que « repris » veut dire selon la pièce.
  var REPRIS = {devis: 'Commandé', marche: 'Appelé', commande: 'Livré', bl: 'Facturé', cde_fournisseur: 'Reçu',
                reception: 'Facturé', of: 'Produit'};

  function colonnes(type, j) {
    var vente = ((ERP.types[type] || {}).sens || 'vente') === 'vente';
    var enRetard = function (cle) {
      return function (l) { return l[cle] && l[cle] < j && l.reste_milli > 0 && l.position !== 'annule' ? 'retard' : ''; };
    };
    var cols = [
      {cle: 'numero', libelle: 'N°', largeur: 100, rendu: function (l) { return l.numero || h('i', {className: 'erp-muet', text: 'Brouillon'}); }},
      {cle: 'rang', libelle: 'Lg', type: 'nombre', largeur: 50},
      {cle: 'tiers_nom', libelle: vente ? 'Client' : 'Fournisseur', largeur: 200},
      {cle: 'date_piece', libelle: 'Date', type: 'date', largeur: 95},
    ];
    if (type === 'marche') {
      cols.push({cle: 'date_ouverture', libelle: 'Ouverture', type: 'date', largeur: 95});
      cols.push({cle: 'date_validite', libelle: 'Fermeture', type: 'date', largeur: 95, classe: enRetard('date_validite')});
    } else if (type === 'devis') {
      cols.push({cle: 'date_validite', libelle: 'Validité', type: 'date', largeur: 95, classe: enRetard('date_validite')});
    }
    if (type !== 'bl' && type !== 'reception') {
      cols.push({cle: 'date_expedition', libelle: 'Exp. prévue', type: 'date', largeur: 100, classe: enRetard('date_expedition')});
      cols.push({cle: 'date_livraison', libelle: 'Liv. prévue', type: 'date', largeur: 100, classe: enRetard('date_livraison')});
    }
    cols.push({cle: 'laboratoire_lib', libelle: 'Laboratoire', largeur: 130});
    if (/^(commande|marche|devis)$/.test(type)) cols.push({cle: 'bat', libelle: 'BAT', type: 'statut', largeur: 140});
    cols.push({cle: 'position', libelle: 'Position', type: 'statut', largeur: 150});
    cols.push({cle: 'quantite_milli', libelle: type === 'bl' ? 'Qté livrée' : 'Qté commandée', type: 'qte', largeur: 125});
    cols.push({cle: 'origine_lib', libelle: 'Origine', largeur: 115});
    if (/^(commande|marche)$/.test(type)) {
      cols.push({cle: 'situation_of', libelle: 'Situation OF', type: 'statut', largeur: 140});
      cols.push({cle: 'a_fabriquer_milli', libelle: 'À fabriquer', type: 'qte', largeur: 110});
    }
    cols.push({cle: 'type_ligne_lib', libelle: 'Type', largeur: 150});
    if (/^(commande|marche|bl)$/.test(type)) cols.push({cle: 'fsc', libelle: 'FSC', largeur: 130});
    cols.push({cle: 'repris_milli', libelle: REPRIS[type] || 'Repris', type: 'qte', largeur: 110});
    cols.push({cle: 'reste_milli', libelle: 'Reste', type: 'qte', largeur: 110, total: true});
    cols.push({cle: 'article_code', libelle: 'Article', largeur: 100});
    cols.push({cle: 'libelle', libelle: 'Désignation', largeur: 260});
    cols.push({cle: 'ref_client', libelle: 'Réf. client', largeur: 120});
    if (vente) {
      cols.push({cle: 'representant', libelle: 'Représentant', largeur: 140});
      cols.push({cle: 'transporteur', libelle: 'Transporteur', largeur: 130});
    }
    cols.push({cle: 'montant_ht_cents', libelle: 'Montant HT', type: 'montant', largeur: 120, total: true});
    // Colonnes proposées dans « Colonnes » (TDB RVGI : sélectionner les colonnes)
    var M = function (c) { c.masquee = true; cols.push(c); };
    var AMONT = {commande: 'Devis / marché', bl: 'Commande', facture: 'BL', avoir: 'Facture', reception: 'Commande fourn.',
                 facture_fournisseur: 'Réception', of: 'Commande'};
    if (AMONT[type]) {
      cols.splice(2, 0, {cle: 'amont_numero', libelle: AMONT[type], largeur: 110},
                         {cle: 'amont_rang', libelle: 'Lg ' + AMONT[type].toLowerCase(), type: 'nombre', largeur: 70, masquee: true});
      M({cle: 'amont_qte_milli', libelle: 'Qté ' + AMONT[type].toLowerCase(), type: 'qte', largeur: 120});
      M({cle: 'amont_reste_milli', libelle: type === 'bl' ? 'Reste à livrer' : 'Reste ' + AMONT[type].toLowerCase(), type: 'qte', largeur: 120});
      M({cle: 'amont_prix_cents', libelle: 'P.U. HT ' + AMONT[type].toLowerCase(), type: 'montant', largeur: 120});
      M({cle: 'amont_ref_tiers', libelle: 'Réf. ' + AMONT[type].toLowerCase(), largeur: 140});
    }
    M({cle: 'aval_numeros', libelle: {devis: 'Commandes', marche: 'Commandes', commande: 'BL', bl: 'Factures',
      cde_fournisseur: 'Réceptions', reception: 'Factures fourn.', of: 'Productions'}[type] || 'Pièces suivantes', largeur: 140});
    M({cle: 'tiers_code', libelle: vente ? 'Code client' : 'Code fournisseur', largeur: 100});
    M({cle: 'operateur', libelle: 'Opérateur', largeur: 140});
    M({cle: 'valide_par', libelle: 'Validé par', largeur: 140});
    if (vente) M({cle: 'adv', libelle: 'ADV', largeur: 140});
    M({cle: 'ref_tiers', libelle: vente ? 'Réf. commande client' : 'Réf. fournisseur', largeur: 150});
    M({cle: 'prix_cents', libelle: 'P.U. HT', type: 'montant', largeur: 110});
    M({cle: 'unite', libelle: 'Unité', largeur: 70});
    M({cle: 'code3', libelle: 'Code 3', largeur: 90});
    // RVGI met le type (famille) en tête de ses TDB d'achat.
    if (!vente) cols.splice(2, 0, {cle: 'famille_lib', libelle: 'Type', largeur: 130});
    else M({cle: 'famille_lib', libelle: 'Famille', largeur: 130});
    if (type === 'cde_fournisseur') M({cle: 'dates_conf', libelle: 'Dates confirmées', largeur: 120});
    if (type === 'reception') { M({cle: 'zone_rangement', libelle: 'Zone de rangement', largeur: 140}); M({cle: 'zone_douane', libelle: 'Zone douane', largeur: 120}); }
    M({cle: 'prix_net', libelle: 'P.U. HT net', type: 'montant', largeur: 110});
    M({cle: 'format_l', libelle: 'Format L', largeur: 90});
    M({cle: 'format_a', libelle: 'Format A', largeur: 90});
    M({cle: 'laize', libelle: 'Laize', largeur: 80});
    M({cle: 'designation2', libelle: 'Désignation 2', largeur: 220});
    M({cle: 'designation3', libelle: 'Désignation 3', largeur: 220});
    M({cle: 'designation4', libelle: 'Désignation 4', largeur: 220});
    M({cle: 'conditionnement', libelle: 'Conditionnement', largeur: 180});
    M({cle: 'stock_milli', libelle: 'Stock réel', type: 'qte', largeur: 110});
    if (vente) {
      M({cle: 'liv_raison_sociale', libelle: 'Raison sociale livraison', largeur: 200});
      M({cle: 'liv_adresse1', libelle: 'Adresse de livraison', largeur: 200});
      M({cle: 'liv_adresse2', libelle: 'Adresse de livraison 2', largeur: 180});
      M({cle: 'liv_cp', libelle: 'C.P.', largeur: 80});
      M({cle: 'liv_ville', libelle: 'Ville', largeur: 150});
      M({cle: 'liv_pays', libelle: 'Pays', largeur: 70});
    }
    M({cle: 'depot_lib', libelle: 'Dépôt', largeur: 120});
    M({cle: 'notes_ligne', libelle: 'Notes de ligne', largeur: 220});
    return cols;
  }

  function panneau(zone, l, type) {
    zone.textContent = '';
    if (!l) { zone.appendChild(h('div', {className: 'erp-muet', text: 'Sélectionner une ligne.'})); return; }
    var fmtF = function (v) { return v ? (v / 10).toLocaleString('fr-FR') : ''; };
    var bloc = function (titre, lignes) {
      return h('div', {className: 'erp-panneau-bloc'}, h('div', {className: 'erp-liens-titre', text: titre}),
        lignes.filter(function (x) { return x && x[1] !== '' && x[1] != null; }).map(function (x) {
          return h('div', {className: 'erp-panneau-ligne'}, h('span', {text: x[0]}), h('b', {text: String(x[1])}));
        }));
    };
    var u = ' ' + (l.unite || '');
    zone.appendChild(bloc(((ERP.types[type] || {}).libelle || '') + ' ' + (l.numero || 'brouillon') + ' — ligne ' + l.rang, [
      ['Date', ERP.fmt.date(l.date_piece)],
      ['Expédition', ERP.fmt.date(l.date_expedition)],
      ['Livraison', ERP.fmt.date(l.date_livraison)],
      ['Réf. client', l.ref_tiers],
    ]));
    zone.appendChild(bloc(l.tiers_nom, [
      ['Code', l.tiers_code], ['Représentant', l.representant], ['Transporteur', l.transporteur],
    ]));
    zone.appendChild(bloc(l.article_code + ' — ' + l.libelle, [
      ['Réf. produit client', l.ref_client],
      ['Format', l.format_l_dmm ? fmtF(l.format_l_dmm) + ' × ' + fmtF(l.format_a_dmm) + ' mm' : ''],
      ['Conditionnement', l.conditionnement],
    ]));
    zone.appendChild(bloc('Quantités', [
      ['Commandée', ERP.fmt.qte(l.quantite_milli) + u],
      [REPRIS[type] || 'Repris', ERP.fmt.qte(l.repris_milli) + u],
      ['Reste', ERP.fmt.qte(l.reste_milli) + u],
      ['En stock réel', ERP.fmt.qte(l.stock_milli) + u],
    ]));
    zone.appendChild(h('div', {className: 'erp-panneau-bloc actions'},
      ERP.bouton('Ouvrir la pièce', function () { ERP.aller(ERP.cheminPiece(l.type, l.piece_id)); }, {accent: true})));
  }

  ERP.carnet = function (main, ctx, conf) {
    var type = conf.types[0];
    var j = aujourdhui();
    var memo = 'erp_carnet_soldees_' + type;
    var avecSoldees = false;
    try { avecSoldees = localStorage.getItem(memo) === '1'; } catch (e) { /* stockage indisponible */ }
    var toutes = [];
    var grilleZone = h('div', {className: 'erp-zone'}, ERP.chargement());
    var detail = h('div', {className: 'erp-panneau'});
    var caseSoldees = h('input', {type: 'checkbox', checked: avecSoldees});
    var barre = h('label', {className: 'erp-case erp-carnet-barre'}, caseSoldees, h('span', {text: 'Afficher les lignes soldées et annulées'}));
    main.appendChild(barre);
    main.appendChild(grilleZone);
    main.appendChild(detail);
    var g = null;
    function filtrer() {
      return avecSoldees ? toutes : toutes.filter(function (l) { return l.position !== 'solde' && l.position !== 'annule'; });
    }
    caseSoldees.addEventListener('change', function () {
      avecSoldees = caseSoldees.checked;
      try { localStorage.setItem(memo, avecSoldees ? '1' : '0'); } catch (e) { /* stockage indisponible */ }
      if (g) g.maj(filtrer());
    });
    Promise.all([ERP.meta(), ERP.api('/api/erp2/carnet?types=' + conf.types.join(','))]).then(function (r) {
      toutes = r[1];
      toutes.forEach(function (l) {
        l.origine_lib = (ERP.M.origines || {})[l.origine_prod] || '';
        l.laboratoire_lib = (ERP.M.laboratoires || {})[l.laboratoire] || '';
        l.situation_of = l.situation_of ? 'of_' + l.situation_of : '';
        l.bat = l.bat ? 'bat_' + l.bat : '';
        l.type_ligne_lib = (ERP.M.types_ligne || {})[l.type_ligne] || '';
        var mm = function (d) { return d ? (d / 10).toLocaleString('fr-FR') : ''; };
        l.format_l = mm(l.format_l_dmm); l.format_a = mm(l.format_a_dmm); l.laize = mm(l.laize_dmm);
        l.famille_lib = l.famille ? ERP.refLibelle('familles', l.famille) : '';
        l.depot_lib = l.depot ? ERP.refLibelle('depots', l.depot) : '';
        if (l.aval_numeros) l.aval_numeros = l.aval_numeros.split(',').join(', ');
        l.dates_conf = l.dates_confirmees ? 'Oui' : 'Non';
        l.prix_net = l.prix_cents != null ? Math.round(l.prix_cents * (10000 - (l.remise_ligne_bp || 0)) / 10000) : null;
      });
      grilleZone.textContent = '';
      g = ERP.grille(grilleZone, {
        nom: 'carnet.' + type, cle: 'ligne_id', lignes: filtrer(), colonnes: colonnes(type, j),
        statuts: Object.assign({}, ERP.statutsPour([type]), SITUATION_OF),
        ouvrir: function (l) { ERP.aller(ERP.cheminPiece(l.type, l.piece_id)); },
        selection: function (l) { panneau(detail, l, type); },
      });
      requestAnimationFrame(function () { g.focus(); });
    }).catch(function (e) { grilleZone.textContent = ''; grilleZone.appendChild(ERP.erreur(e)); });
  };
})();
