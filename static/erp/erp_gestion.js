/* Nouvel ERP — accueil, stocks, échéances, paramètres. */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  function aujourdhui() { return new Date().toISOString().slice(0, 10); }

  // ── Accueil : ce qui attend une action ───────────────────────────
  ERP.ecrans['/'] = function (main, ctx) {
    ctx.titre('Accueil', 'ERP SIFA');
    var zone = h('div', null, ERP.chargement());
    main.appendChild(zone);
    Promise.all([
      ERP.meta(),
      ERP.api('/api/erp2/pieces?types=devis,commande,bl,cde_fournisseur,reception,facture,avoir'),
      ERP.api('/api/erp2/echeances'),
    ]).then(function (r) {
      var p = r[1], e = r[2], j = aujourdhui();
      function compte(type, statuts) { return p.filter(function (x) { return x.type === type && statuts.indexOf(x.statut) >= 0; }); }
      function somme(l, k) { return l.reduce(function (s, x) { return s + (x[k] || 0); }, 0); }
      var brouillons = p.filter(function (x) { return x.statut === 'brouillon'; });
      var aLivrer = compte('commande', ['valide', 'partiel']);
      var enRetard = aLivrer.filter(function (x) { return x.date_livraison && x.date_livraison < j; });
      var aFacturer = compte('bl', ['valide', 'partiel']);
      var devis = compte('devis', ['valide']);
      var aRecevoir = compte('cde_fournisseur', ['valide', 'partiel']);
      var echRetard = e.filter(function (x) { return x.type === 'facture' && x.reste_cents > 0 && x.date_echeance < j; });
      var annee = j.slice(0, 4);
      var ca = somme(compte('facture', ['valide', 'solde']).filter(function (x) { return x.date_piece.slice(0, 4) === annee; }), 'total_ht_cents') -
               somme(compte('avoir', ['valide', 'solde']).filter(function (x) { return x.date_piece.slice(0, 4) === annee; }), 'total_ht_cents');
      function tuile(titre, n, detail, chemin, ton) {
        return h('a', {className: 'erp-tuile' + (ton ? ' ton-' + ton : ''), href: chemin, onclick: function (ev) { ev.preventDefault(); ERP.aller(chemin); }},
          h('div', {className: 'erp-tuile-titre', text: titre}), h('div', {className: 'erp-tuile-n', text: String(n)}),
          h('div', {className: 'erp-tuile-detail', text: detail}));
      }
      zone.textContent = '';
      zone.appendChild(h('div', {className: 'erp-tuiles'},
        tuile('Devis en attente de réponse', devis.length, ERP.fmt.euros(somme(devis, 'total_ht_cents')) + ' HT', '/ventes/devis'),
        tuile('Commandes à livrer', aLivrer.length, enRetard.length ? enRetard.length + ' en retard' : 'aucune en retard', '/ventes/commandes', enRetard.length ? 'danger' : null),
        tuile('BL à facturer', aFacturer.length, ERP.fmt.euros(somme(aFacturer, 'total_ht_cents')) + ' HT', '/ventes/livraisons', aFacturer.length ? 'warn' : null),
        tuile('Échéances clients en retard', echRetard.length, ERP.fmt.euros(somme(echRetard, 'reste_cents')), '/compta/echeances', echRetard.length ? 'danger' : null),
        tuile('Commandes fournisseur à recevoir', aRecevoir.length, ERP.fmt.euros(somme(aRecevoir, 'total_ht_cents')) + ' HT', '/achats/commandes'),
        tuile('Chiffre d\'affaires ' + annee, ERP.fmt.euros(ca), 'facturé HT, avoirs déduits', '/ventes/factures')));
      if (brouillons.length) {
        zone.appendChild(ERP.carte('Brouillons en cours', h('div', {className: 'erp-liens'}, brouillons.map(function (x) {
          return h('div', {className: 'erp-liens-item'},
            ERP.lien((ERP.types[x.type] || {}).libelle + ' — ' + x.tiers_nom, ERP.cheminPiece(x.type, x.id)),
            h('span', {text: ERP.fmt.date(x.date_piece)}), h('b', {className: 'num', text: ERP.fmt.euros(x.total_ht_cents)}));
        }))));
      }
      if (!p.length) {
        zone.appendChild(h('div', {className: 'erp-vide'}, h('b', {text: 'Aucune pièce. '}),
          'Paramètres › Démonstration charge un petit jeu de données fictives pour essayer toute la chaîne.'));
      }
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  // ── Stocks ───────────────────────────────────────────────────────
  function saisieMouvement(apres) {
    return ERP.api('/api/erp2/articles').then(function (arts) {
      arts = arts.filter(function (a) { return a.gere_stock && a.actif; });
      var M = {type: 'inventaire', depot: (ERP.ref('depots', true)[0] || {}).code, date_mvt: aujourdhui(), article_id: null};
      var art = h('input', {className: 'erp-input', placeholder: 'Article (code ou libellé)'});
      var info = h('div', {className: 'erp-aide'});
      ERP.autocomplete(art, function (q) {
        return ERP.filtrer(arts, q, ['code', 'libelle']).map(function (a) {
          return {titre: a.code + ' — ' + a.libelle, sous: 'stock ' + ERP.fmt.qte(a.stock_milli) + ' ' + a.unite, valeur: a};
        });
      }, function (a) { M.article_id = a.id; art.value = a.code + ' — ' + a.libelle; info.textContent = 'Stock théorique : ' + ERP.fmt.qte(a.stock_milli) + ' ' + a.unite; });
      var qteLib = h('label', {className: 'erp-label', text: 'Quantité comptée'});
      var autres = ERP.ref('depots', true).filter(function (d) { return d.code !== M.depot; });
      M.depot_destination = (autres[0] || {}).code || null;
      var champDest = ERP.champ('Vers le dépôt', ERP.choix(M, 'depot_destination', ERP.optionsRef('depots')));
      champDest.style.display = 'none';
      var corps = h('div', {className: 'erp-form'},
        ERP.champ('Article', art, {plein: true}), info,
        ERP.champ('Type', ERP.choix(M, 'type', [{v: 'inventaire', l: 'Inventaire (quantité comptée)'},
                                                {v: 'ajustement', l: 'Ajustement (+ / − quantité)'},
                                                {v: 'transfert', l: 'Transfert entre dépôts'}],
          {change: function (v) {
            qteLib.textContent = v === 'inventaire' ? 'Quantité comptée' : v === 'transfert' ? 'Quantité à transférer' : 'Quantité (négative pour une sortie)';
            champDest.style.display = v === 'transfert' ? '' : 'none';
          }})),
        ERP.champ('Dépôt', ERP.choix(M, 'depot', ERP.optionsRef('depots'))),
        champDest,
        h('div', {className: 'erp-champ'}, qteLib, ERP.saisie(M, 'quantite_milli', 'qte')),
        ERP.champ('Date', ERP.saisie(M, 'date_mvt', 'date')),
        ERP.champ('Laize (1/10 mm)', ERP.saisie(M, 'laize_dmm', 'entier'), {aide: 'Matières : le stock est tenu par laize.'}),
        ERP.champ('Lot', ERP.saisie(M, 'lot', 'texte')),
        ERP.champ('Commentaire', ERP.saisie(M, 'commentaire', 'texte'), {plein: true}));
      ERP.modal('Mouvement de stock', corps, [
        {libelle: 'Annuler'},
        {libelle: 'Enregistrer', accent: true, action: async function () {
          if (!M.article_id) throw new Error('Choisir un article.');
          if (M.quantite_milli == null) throw new Error('Quantité obligatoire.');
          await ERP.api('/api/erp2/mouvements', {method: 'POST', body: M});
          ERP.toast('Mouvement enregistré.', 'success');
          if (apres) apres();
        }},
      ]);
    });
  }

  ERP.ecrans['/stocks/etat'] = function (main, ctx) {
    main.classList.add('plein');
    ctx.actions.appendChild(ERP.bouton('Inventaire, ajustement, transfert', function () { return saisieMouvement(ERP.rafraichir); }, {accent: true}));
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    Promise.all([ERP.meta(), ERP.api('/api/erp2/stock')]).then(function (r) {
      zone.textContent = '';
      var natures = {};
      Object.keys(ERP.M.natures).forEach(function (k) { natures[k] = {libelle: ERP.M.natures[k], ton: k === 'pf' ? 'accent' : 'warn'}; });
      r[1].forEach(function (s) {
        s.depot_lib = ERP.refLibelle('depots', s.depot);
        s.famille_lib = ERP.refLibelle('familles', s.famille);
      });
      var mm = function (d) { return d ? (d / 10).toLocaleString('fr-FR') : ''; };
      // TDB stock de RVGI : produits par client, matières par laize ; en rouge
      // l'article dont le stock total passe sous son stock mini.
      ERP.grille(zone, {
        nom: 'stock.etat', cle: 'cle', lignes: r[1], statuts: natures,
        colonnes: [
          {cle: 'nature', libelle: 'Nature', type: 'statut', largeur: 140},
          {cle: 'famille_lib', libelle: 'Famille / type', largeur: 140},
          {cle: 'client_nom', libelle: 'Client', largeur: 180},
          {cle: 'code', libelle: 'Article', largeur: 110},
          {cle: 'laize_dmm', libelle: 'Laize', largeur: 80, rendu: function (s) { return mm(s.laize_dmm); }},
          {cle: 'libelle', libelle: 'Libellé', largeur: 280},
          {cle: 'depot_lib', libelle: 'Dépôt', largeur: 130},
          {cle: 'quantite_milli', libelle: 'Stock réel', type: 'qte', largeur: 120, classe: function (s) { return s.sous_mini ? 'retard' : ''; }},
          {cle: 'stock_mini_milli', libelle: 'Stock mini', type: 'qte', largeur: 110},
          {cle: 'stock_maxi_milli', libelle: 'Stock maxi', type: 'qte', largeur: 110},
          {cle: 'unite', libelle: 'Unité', largeur: 70},
          {cle: 'format', libelle: 'Format', largeur: 110, rendu: function (s) {
            return s.nature === 'pf' && s.format_l_dmm ? mm(s.format_l_dmm) + ' × ' + mm(s.format_a_dmm) : ''; }},
          {cle: 'ref_client', libelle: 'Réf. client', largeur: 130},
          {cle: 'dernier_mvt', libelle: 'Dernier mouvement', type: 'date', largeur: 140},
        ],
        ouvrir: function (s) { ERP.aller('/fichiers/articles/' + s.id); },
      });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  ERP.ecrans['/stocks/mouvements'] = function (main, ctx) {
    main.classList.add('plein');
    ctx.actions.appendChild(ERP.bouton('Inventaire, ajustement, transfert', function () { return saisieMouvement(ERP.rafraichir); }, {accent: true}));
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    Promise.all([ERP.meta(), ERP.api('/api/erp2/mouvements')]).then(function (r) {
      zone.textContent = '';
      var types = {reception: {libelle: 'Réception', ton: 'ok'}, livraison: {libelle: 'Livraison', ton: 'accent'},
                   inventaire: {libelle: 'Inventaire', ton: 'neutre'}, ajustement: {libelle: 'Ajustement', ton: 'warn'},
                   production: {libelle: 'Production', ton: 'ok'}, consommation: {libelle: 'Consommation', ton: 'accent'},
                   transfert: {libelle: 'Transfert', ton: 'neutre'}};
      ERP.grille(zone, {
        nom: 'stock.mouvements', cle: 'id', lignes: r[1], statuts: types,
        colonnes: [
          {cle: 'date_mvt', libelle: 'Date', type: 'date', largeur: 100},
          {cle: 'type', libelle: 'Type', type: 'statut', largeur: 130},
          {cle: 'article_code', libelle: 'Article', largeur: 100},
          {cle: 'article_libelle', libelle: 'Libellé', largeur: 280},
          {cle: 'depot', libelle: 'Dépôt', largeur: 90},
          {cle: 'laize_dmm', libelle: 'Laize', largeur: 80, rendu: function (m) { return m.laize_dmm ? (m.laize_dmm / 10).toLocaleString('fr-FR') : ''; }},
          {cle: 'quantite_milli', libelle: 'Quantité', type: 'qte', largeur: 130},
          {cle: 'unite', libelle: 'Unité', largeur: 70},
          {cle: 'piece_numero', libelle: 'Pièce', largeur: 120},
          {cle: 'lot', libelle: 'Lot', largeur: 100},
          {cle: 'commentaire', libelle: 'Commentaire', largeur: 240},
        ],
        ouvrir: function (m) { ERP.aller(m.piece_id ? ERP.cheminPiece(m.piece_type, m.piece_id) : '/fichiers/articles/' + m.article_id); },
      });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  // ── Échéances ────────────────────────────────────────────────────
  ERP.ecrans['/compta/echeances'] = function (main) {
    main.classList.add('plein');
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    Promise.all([ERP.meta(), ERP.api('/api/erp2/echeances')]).then(function (r) {
      var j = aujourdhui();
      r[1].forEach(function (e) {
        e.sens = e.type === 'facture' ? 'Client' : 'Fournisseur';
        e.etat = e.reste_cents <= 0 ? 'reglee' : e.date_echeance < j ? 'retard' : 'avenir';
        e.mode_lib = ERP.refLibelle('modes_paiement', e.mode_paiement);
      });
      zone.textContent = '';
      ERP.grille(zone, {
        nom: 'compta.echeances', cle: 'id', lignes: r[1],
        statuts: {reglee: {libelle: 'Réglée', ton: 'ok'}, retard: {libelle: 'En retard', ton: 'danger'}, avenir: {libelle: 'À venir', ton: 'neutre'}},
        colonnes: [
          {cle: 'date_echeance', libelle: 'Échéance', type: 'date', largeur: 110},
          {cle: 'sens', libelle: 'Sens', largeur: 110},
          {cle: 'tiers_nom', libelle: 'Tiers', largeur: 260},
          {cle: 'numero', libelle: 'Facture', largeur: 120},
          {cle: 'date_piece', libelle: 'Date facture', type: 'date', largeur: 110},
          {cle: 'mode_lib', libelle: 'Mode', largeur: 120},
          {cle: 'montant_cents', libelle: 'Montant TTC', type: 'montant', largeur: 130, total: true},
          {cle: 'reste_cents', libelle: 'Reste dû', type: 'montant', largeur: 130, total: true},
          {cle: 'etat', libelle: 'État', type: 'statut', largeur: 120},
        ],
        ouvrir: function (e) { ERP.aller(ERP.cheminPiece(e.type, e.piece_id)); },
      });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  // ── Paramètres ───────────────────────────────────────────────────
  var ONGLETS = [
    {cle: 'societe', libelle: 'Société'},
    {cle: 'sequences', libelle: 'Numérotation'},
    {cle: 'tva', libelle: 'TVA'},
    {cle: 'conditions_paiement', libelle: 'Conditions de paiement'},
    {cle: 'modes_paiement', libelle: 'Modes de paiement'},
    {cle: 'unites', libelle: 'Unités'},
    {cle: 'familles', libelle: 'Familles'},
    {cle: 'depots', libelle: 'Dépôts'},
    {cle: 'pays', libelle: 'Pays'},
    {cle: 'devises', libelle: 'Devises'},
    {cle: 'banques', libelle: 'Banques'},
    {cle: 'types_contact', libelle: 'Types de contacts'},
    {cle: 'gammes', libelle: 'Gammes'},
    {cle: 'textes', libelle: 'Libellés automatiques'},
    {cle: 'comptabilite', libelle: 'Comptabilité'},
    {cle: 'demo', libelle: 'Démonstration'},
  ];
  // Colonnes éditables par référentiel : [cle, libellé, type]
  var COLS_REF = {
    tva: [['libelle', 'Libellé', 'texte'], ['taux_bp', 'Taux', 'pct'], ['mention', 'Mention sur facture', 'texte'], ['compte_collecte', 'Compte collectée', 'texte'], ['compte_deductible', 'Compte déductible', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    conditions_paiement: [['libelle', 'Libellé', 'texte'], ['jours', 'Jours', 'entier'], ['fin_de_mois', 'Fin de mois', 'case'], ['jour_du_mois', 'Le … du mois', 'entier'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    modes_paiement: [['libelle', 'Libellé', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    unites: [['libelle', 'Libellé', 'texte'], ['decimales', 'Décimales', 'entier'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    familles: [['libelle', 'Libellé', 'texte'], ['nature', 'Nature', 'nature'], ['compte_vente', 'Compte de vente', 'texte'], ['compte_achat', 'Compte d\'achat', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    depots: [['libelle', 'Libellé', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    sequences: [['libelle', 'Pièce', 'lecture'], ['format', 'Format', 'texte'], ['prochain', 'Prochain numéro', 'entier'], ['reinit', 'Remise à zéro', 'reinit']],
    pays: [['libelle', 'Pays', 'texte'], ['ue', 'Union européenne', 'case'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    devises: [['libelle', 'Devise', 'texte'], ['symbole', 'Symbole', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    banques: [['libelle', 'Banque', 'texte'], ['iban', 'IBAN', 'texte'], ['bic', 'BIC', 'texte'], ['compte', 'Compte comptable', 'texte'], ['journal', 'Journal', 'texte'], ['actif', 'Active', 'case']],
    types_contact: [['libelle', 'Type', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
    gammes: [['libelle', 'Gamme', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Active', 'case']],
    textes: [['libelle', 'Libellé', 'texte'], ['texte', 'Texte imprimé', 'texte'], ['rang', 'Ordre', 'entier'], ['actif', 'Actif', 'case']],
  };

  ERP.ecrans['/parametres'] = function (main, ctx) {
    var onglet = ctx.param && ONGLETS.some(function (o) { return o.cle === ctx.param; }) ? ctx.param : 'societe';
    var barre = h('div', {className: 'erp-onglets'}, ONGLETS.map(function (o) {
      return h('button', {type: 'button', className: 'erp-onglet' + (o.cle === onglet ? ' actif' : ''), text: o.libelle,
        onclick: function () { ERP.aller('/parametres/' + o.cle); }});
    }));
    var zone = h('div', null, ERP.chargement());
    main.appendChild(barre);
    main.appendChild(zone);
    ERP.meta(true).then(function () {
      zone.textContent = '';
      if (onglet === 'societe') zone.appendChild(ongletSociete(ctx));
      else if (onglet === 'demo') zone.appendChild(ongletDemo());
      else if (onglet === 'comptabilite') ongletCompta(zone, ctx);
      else zone.appendChild(ongletRef(onglet, ctx));
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  function ongletSociete(ctx) {
    var S = Object.assign({}, ERP.M.societe);
    var m = function () { ERP.garde = function () { return true; }; };
    var c = function (lib, cle, type, o) { return ERP.champ(lib, ERP.saisie(S, cle, type || 'texte', {change: m}), o); };
    ctx.actions.appendChild(ERP.bouton('Enregistrer', async function () {
      await ERP.api('/api/erp2/societe', {method: 'PUT', body: S});
      ERP.garde = null;
      ERP.toast('Société enregistrée.', 'success');
      await ERP.meta(true);
    }, {accent: true}));
    return ERP.carte('Société — mentions imprimées sur les pièces', h('div', {className: 'erp-form'},
      c('Raison sociale', 'raison_sociale', 'texte', {large: true}), c('Forme juridique', 'forme_juridique'),
      c('Capital', 'capital_cents', 'euros'), c('SIRET', 'siret'), c('RCS', 'rcs'), c('N° TVA intracommunautaire', 'tva_intra'),
      c('Code APE', 'ape'), c('Adresse', 'adresse1', 'texte', {large: true}), c('Complément', 'adresse2', 'texte', {large: true}),
      c('Code postal', 'code_postal'), c('Ville', 'ville'), c('Pays', 'pays'), c('Téléphone', 'telephone'), c('Email', 'email'),
      c('IBAN', 'iban', 'texte', {large: true}), c('BIC', 'bic'),
      c('Pénalités de retard (mention obligatoire)', 'penalites_retard', 'zone', {plein: true}),
      h('div', {className: 'erp-champ plein erp-section-form', text: 'FSC'}),
      c('Code de certificat FSC', 'fsc_certificat'), c('Licence FSC', 'fsc_licence'),
      h('div', {className: 'erp-champ plein erp-section-form', text: 'Textes des documents'}),
      c('Origine et nature (en tête de facture)', 'mention_origine', 'zone', {plein: true}),
      c('Pénalités et escompte (pied de facture)', 'texte_penalites', 'zone', {plein: true}),
      c('Affacturage (pied de facture, en rouge)', 'texte_affacturage', 'zone', {plein: true}),
      c('Réserve de propriété', 'texte_reserve_propriete', 'zone', {plein: true}),
      c('Clause attributive de juridiction (toutes les pièces de vente)', 'texte_juridiction', 'zone', {plein: true}),
      h('div', {className: 'erp-champ plein erp-cases'}, ERP.case(S, 'tva_sur_debits', 'TVA sur les débits', {change: m}))));
  }

  function ongletRef(nom, ctx) {
    var lignes = ERP.ref(nom).map(function (x) { return Object.assign({}, x); });
    var cols = COLS_REF[nom];
    var modifiees = {};
    var tbody = h('tbody');
    var natures = Object.keys(ERP.M.natures_famille || ERP.M.natures).map(function (k) { return {v: k, l: (ERP.M.natures_famille || ERP.M.natures)[k]}; });
    function m(l) { modifiees[l.code] = l; ERP.garde = function () { return true; }; }
    function dessiner() {
      tbody.textContent = '';
      lignes.forEach(function (l) {
        var tr = h('tr', null, h('td', null, l._nouveau ? (function () {
          var el = ERP.saisie(l, 'code', 'texte', {change: function () { m(l); }}); el.classList.add('erp-cell'); return el; })()
          : h('b', {text: l.code})));
        cols.forEach(function (c) {
          var el;
          if (c[2] === 'case') el = ERP.case(l, c[0], '', {change: function () { m(l); }});
          else if (c[2] === 'lecture') el = h('span', {text: l[c[0]]});
          else if (c[2] === 'nature') el = ERP.choix(l, c[0], natures, {change: function () { m(l); }});
          else if (c[2] === 'reinit') el = ERP.choix(l, c[0], [{v: 'annuelle', l: 'Chaque année'}, {v: 'mensuelle', l: 'Chaque mois'}, {v: 'jamais', l: 'Jamais'}], {change: function () { m(l); }});
          else el = ERP.saisie(l, c[0], c[2], {change: function () { m(l); }});
          if (el.classList && c[2] !== 'case') el.classList.add('erp-cell');
          tr.appendChild(h('td', null, el));
        });
        tbody.appendChild(tr);
      });
    }
    dessiner();
    ctx.actions.appendChild(ERP.bouton('Enregistrer', async function () {
      var envoi = Object.keys(modifiees).map(function (k) { return modifiees[k]; }).filter(function (l) { return l.code; });
      if (!envoi.length) { ERP.toast('Rien à enregistrer.', 'info'); return; }
      await ERP.api('/api/erp2/referentiels/' + nom, {method: 'PUT', body: {lignes: envoi}});
      ERP.garde = null;
      ERP.toast('Enregistré.', 'success');
      await ERP.meta(true);
      ERP.rafraichir();
    }, {accent: true}));
    var aide = nom === 'sequences'
      ? 'Jetons : {AAAA} année, {AA} année sur 2 chiffres, {MM} mois, {N:05} compteur sur 5 chiffres. Le numéro est attribué à la validation, sans trou possible.'
      : nom === 'tva' ? 'Taux en pourcentage (20 pour 20 %). La mention s\'imprime sur la facture (exonération, autoliquidation).'
      : nom === 'textes' ? 'Texte imprimé sur les pièces d\'un client qui l\'a choisi (fiche client › Commercial et livraison › Documents).'
      : nom === 'banques' ? 'Banque choisie à l\'encaissement : son compte et son journal servent à l\'export comptable.'
      : nom === 'familles' ? 'Familles de produits, de matières (types), de clients et de fournisseurs.' : '';
    var table = h('table', {className: 'erp-lignes'},
      h('thead', null, h('tr', null, h('th', {text: 'Code'}), cols.map(function (c) { return h('th', {text: c[1]}); }))), tbody);
    var titre = (ERP.M.referentiels_libelles || {})[nom] || nom;
    return ERP.carte(titre, h('div', null, aide ? h('p', {className: 'erp-aide', text: aide}) : null, h('div', {className: 'erp-lignes-defil'}, table)),
      nom === 'sequences' ? null : ERP.bouton('+ Ajouter', function () {
        var n = {_nouveau: true, code: '', actif: 1, rang: lignes.length + 1};
        lignes.push(n); dessiner();
      }, {petit: true}));
  }

  function ongletCompta(zone, ctx) {
    ERP.api('/api/erp2/compta/reglages').then(function (lignes) {
      var form = h('div', {className: 'erp-form'}, lignes.map(function (l) {
        return ERP.champ(l.libelle, ERP.saisie(l, 'valeur', 'texte', {change: function () { ERP.garde = function () { return true; }; }}));
      }));
      ctx.actions.appendChild(ERP.bouton('Enregistrer', async function () {
        await ERP.api('/api/erp2/compta/reglages', {method: 'PUT', body: {lignes: lignes}});
        ERP.garde = null;
        ERP.toast('Réglages comptables enregistrés.', 'success');
      }, {accent: true}));
      zone.appendChild(ERP.carte('Comptes et journaux de l\'export comptable', h('div', null,
        h('p', {className: 'erp-aide', text: 'Les comptes de TVA se règlent dans l\'onglet TVA, les comptes de vente et d\'achat par famille dans Familles, le compte auxiliaire sur la fiche du tiers (par défaut : son code).'}),
        form)));
    }).catch(function (e) { zone.appendChild(ERP.erreur(e)); });
  }

  // ── Export comptable ─────────────────────────────────────────────
  ERP.ecrans['/compta/export'] = function (main, ctx) {
    main.classList.add('plein');
    var j = new Date();
    var P = {debut: j.getFullYear() + '-01-01', fin: j.toISOString().slice(0, 10)};
    var info = h('div', {className: 'erp-export-info'});
    var zone = h('div', {className: 'erp-zone'});
    var barre = h('div', {className: 'erp-form erp-export-barre'},
      ERP.champ('Du', ERP.saisie(P, 'debut', 'date', {change: charger})),
      ERP.champ('Au', ERP.saisie(P, 'fin', 'date', {change: charger})));
    ctx.actions.appendChild(ERP.bouton('Télécharger le FEC', async function () {
      var r = await fetch('/api/erp2/compta/fec?debut=' + P.debut + '&fin=' + P.fin, {credentials: 'same-origin'});
      if (!r.ok) { var e = await r.json().catch(function () { return {}; }); throw new Error(e.detail || 'Export impossible.'); }
      var nom = (r.headers.get('Content-Disposition') || '').replace(/.*filename="([^"]+)".*/, '$1') || 'FEC.txt';
      var url = URL.createObjectURL(await r.blob());
      var a = h('a', {href: url, download: nom}); document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }, {accent: true}));
    main.appendChild(barre);
    main.appendChild(info);
    main.appendChild(zone);
    async function charger() {
      zone.textContent = ''; zone.appendChild(ERP.chargement());
      try {
        var r = await ERP.api('/api/erp2/compta/ecritures?debut=' + P.debut + '&fin=' + P.fin);
        info.textContent = '';
        if (r.controles.length) info.appendChild(h('div', {className: 'erp-vide erreur'}, r.controles.map(function (c) { return h('div', {text: c}); })));
        else info.appendChild(h('div', {className: 'erp-aide', text: r.lignes.length + ' lignes d\'écritures, toutes équilibrées.'}));
        zone.textContent = '';
        ERP.grille(zone, {
          nom: 'compta.ecritures', cle: 'EcritureNum', lignes: r.lignes,
          colonnes: [
            {cle: 'JournalCode', libelle: 'Journal', largeur: 80},
            {cle: 'EcritureNum', libelle: 'N°', largeur: 100},
            {cle: 'EcritureDate', libelle: 'Date', largeur: 100, rendu: function (l) { var d = l.EcritureDate; return d.slice(6, 8) + '/' + d.slice(4, 6) + '/' + d.slice(0, 4); }},
            {cle: 'CompteNum', libelle: 'Compte', largeur: 100},
            {cle: 'CompAuxNum', libelle: 'Auxiliaire', largeur: 100},
            {cle: 'PieceRef', libelle: 'Pièce', largeur: 120},
            {cle: 'EcritureLib', libelle: 'Libellé', largeur: 300},
            {cle: 'debit_cents', libelle: 'Débit', type: 'montant', largeur: 120, total: true},
            {cle: 'credit_cents', libelle: 'Crédit', type: 'montant', largeur: 120, total: true},
          ],
        });
      } catch (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); }
    }
    charger();
  };

  function ongletDemo() {
    return ERP.carte('Jeu de démonstration', h('div', null,
      h('p', {className: 'erp-modal-texte', text: 'Charge 5 clients, 3 fournisseurs, 10 articles et une douzaine de pièces fictives passées par toute la chaîne : devis accepté, commande livrée en deux fois, facture, BL à facturer, commande fournisseur reçue en partie, inventaire d\'ouverture.'}),
      h('p', {className: 'erp-modal-texte', text: 'Seules les données de démonstration sont effacées et recréées. Dès qu\'une pièce réelle existe, la réinitialisation est refusée.'}),
      ERP.bouton('Réinitialiser la démonstration', async function () {
        if (!(await ERP.confirmer('Effacer et recréer toutes les données de démonstration ? La numérotation repart à 1.', {danger: true, ok: 'Réinitialiser'}))) return;
        var r = await ERP.api('/api/erp2/demo/reinitialiser', {method: 'POST'});
        ERP.toast('Démonstration rechargée : ' + r.gc_pieces + ' pièces.', 'success');
        ERP.aller('/');
      }, {danger: true})));
  }
})();
