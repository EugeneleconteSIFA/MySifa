/* Nouvel ERP — pièces : listes et écran de pièce (ventes et achats).
 *
 * Une adresse par liste (/ventes/commandes), une par pièce
 * (/ventes/commandes/12). L'écran de pièce :
 * - brouillon : en-tête et lignes modifiables, totaux recalculés à la frappe
 *   (ERP.calc, copie de calculs.py — le serveur recalcule à l'enregistrement) ;
 * - validée : lecture seule, quantités reprises par les pièces aval, actions
 *   de transformation (livrer, facturer, réceptionner, avoir).
 *
 * Clavier : Entrée dans une ligne passe à la suivante (et en crée une au bout),
 * Ctrl+S enregistre, ↑ ↓ Entrée dans la liste d'articles.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  var ROUTES = {
    '/ventes/devis': {types: ['devis'], nouveau: 'devis'},
    '/ventes/commandes': {types: ['commande'], nouveau: 'commande'},
    '/ventes/livraisons': {types: ['bl'], nouveau: 'bl'},
    '/ventes/factures': {types: ['facture', 'avoir'], nouveau: 'facture'},
    '/achats/commandes': {types: ['cde_fournisseur'], nouveau: 'cde_fournisseur'},
    '/achats/receptions': {types: ['reception'], nouveau: 'reception'},
    '/achats/factures': {types: ['facture_fournisseur'], nouveau: 'facture_fournisseur'},
  };

  // Libellé du bouton qui crée la pièce aval.
  var ACTION_AVAL = {
    commande: 'Transformer en commande', bl: 'Livrer', facture: 'Facturer', avoir: 'Faire un avoir',
    reception: 'Réceptionner', facture_fournisseur: 'Saisir la facture',
  };
  // Pièces qu'on peut regrouper dans une même pièce aval.
  var REGROUPABLE = {facture: 'bl', facture_fournisseur: 'reception'};
  var AVEC_STOCK = {bl: 1, reception: 1};
  var ARTICLES_PAR_SENS = {vente: ['pf', 'service'], achat: ['mp', 'service', 'pf']};

  function routeDe(type) {
    var r = null;
    Object.keys(ROUTES).forEach(function (k) { if (ROUTES[k].types.indexOf(type) >= 0) r = k; });
    return r;
  }
  ERP.cheminPiece = function (type, id) { return (routeDe(type) || '/') + '/' + id; };

  function libType(type) { return ((ERP.types || {})[type] || {}).libelle || type; }
  function sensDe(type) { return ((ERP.types || {})[type] || {}).sens || 'vente'; }
  function nomPiece(p) { return p.numero || 'Brouillon'; }

  // ── Choix du tiers pour une nouvelle pièce ───────────────────────
  async function choisirTiers(type) {
    var sens = sensDe(type);
    var tiers = await ERP.api('/api/erp2/tiers?role=' + (sens === 'vente' ? 'client' : 'fournisseur'));
    return new Promise(function (resoudre) {
      var choisi = null;
      var inp = h('input', {className: 'erp-input', placeholder: sens === 'vente' ? 'Client (nom ou code)' : 'Fournisseur (nom ou code)'});
      var m = ERP.modal('Nouveau : ' + libType(type).toLowerCase(), ERP.champ(sens === 'vente' ? 'Client' : 'Fournisseur', inp), [
        {libelle: 'Annuler'},
      ], {fermeture: function () { resoudre(choisi); }});
      ERP.autocomplete(inp, function (q) {
        return ERP.filtrer(tiers.filter(function (t) { return t.actif; }), q, ['code', 'raison_sociale', 'ville'])
          .map(function (t) { return {titre: t.raison_sociale, sous: t.code + (t.ville ? ' · ' + t.ville : '') + (t.bloque ? ' · bloqué' : ''), valeur: t}; });
      }, function (t) { choisi = t; m.fermer(); }, {ouvrirAuFocus: true});
    });
  }

  async function nouvellePiece(type) {
    var t = await choisirTiers(type);
    if (!t) return;
    var r = await ERP.api('/api/erp2/pieces', {method: 'POST', body: {type: type, tiers_id: t.id}});
    ERP.aller(ERP.cheminPiece(type, r.id));
  }

  // ── Regroupement (facturer plusieurs BL) ─────────────────────────
  async function choisirSources(p, cible) {
    var srcType = p.type;
    var liste = (await ERP.api('/api/erp2/pieces?types=' + srcType)).filter(function (x) {
      return x.tiers_id === p.tiers_id && (x.statut === 'valide' || x.statut === 'partiel');
    });
    if (liste.length <= 1) return [p.id];
    return new Promise(function (resoudre) {
      var coches = {}; coches[p.id] = true;
      var res = null;
      var corps = h('div', null,
        h('p', {className: 'erp-modal-texte', text: liste.length + ' ' + libType(srcType).toLowerCase() + '(s) de ' + p.tiers.raison_sociale + ' restent à reprendre. Cocher ceux à regrouper :'}),
        liste.map(function (x) {
          var c = h('input', {type: 'checkbox', checked: !!coches[x.id]});
          c.addEventListener('change', function () { coches[x.id] = c.checked; });
          return h('label', {className: 'erp-case ligne'}, c,
            h('b', {text: x.numero}), h('span', {text: ERP.fmt.date(x.date_piece)}),
            h('span', {className: 'num', text: ERP.fmt.euros(x.total_ht_cents) + ' HT'}));
        }));
      ERP.modal(ACTION_AVAL[cible] || 'Regrouper', corps, [
        {libelle: 'Annuler'},
        {libelle: 'Créer', accent: true, action: function () {
          res = Object.keys(coches).filter(function (k) { return coches[k]; }).map(Number);
          if (!res.length) { ERP.toast('Cocher au moins une pièce.', 'danger'); return false; }
        }},
      ], {fermeture: function () { resoudre(res); }});
    });
  }

  async function transformer(p, cible) {
    var sources = REGROUPABLE[cible] === p.type ? await choisirSources(p, cible) : [p.id];
    if (!sources) return;
    var r = await ERP.api('/api/erp2/pieces/transformer', {method: 'POST', body: {sources: sources, cible: cible}});
    ERP.toast(libType(cible) + ' créé(e) en brouillon.', 'success');
    ERP.aller(ERP.cheminPiece(cible, r.id));
  }

  // ── Liste ────────────────────────────────────────────────────────
  function ecranListe(route) {
    return function (main, ctx) {
      var conf = ROUTES[route];
      if (ctx.param) return ecranPiece(main, ctx, conf);
      main.classList.add('plein');
      var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
      main.appendChild(zone);
      Promise.all([ERP.meta(), ERP.api('/api/erp2/pieces?types=' + conf.types.join(','))]).then(function (r) {
        var lignes = r[1];
        if (conf.nouveau) {
          ctx.actions.appendChild(ERP.bouton('Nouveau : ' + libType(conf.nouveau).toLowerCase(), function () { return nouvellePiece(conf.nouveau); }, {accent: true}));
        }
        zone.textContent = '';
        var vente = sensDe(conf.types[0]) === 'vente';
        var cols = [
          {cle: 'numero', libelle: 'Numéro', largeur: 120, rendu: function (l) { return l.numero || h('i', {className: 'erp-muet', text: 'Brouillon'}); }},
        ];
        if (conf.types.length > 1) cols.push({cle: 'type', libelle: 'Type', largeur: 90, rendu: function (l) { return libType(l.type); }});
        cols.push(
          {cle: 'date_piece', libelle: 'Date', type: 'date', largeur: 100},
          {cle: 'tiers_nom', libelle: vente ? 'Client' : 'Fournisseur', largeur: 240},
          {cle: 'ref_tiers', libelle: vente ? 'Réf. client' : 'Réf. fournisseur', largeur: 130});
        if (/commande|cde_fournisseur/.test(conf.types[0])) cols.push({cle: 'date_livraison', libelle: 'Livraison', type: 'date', largeur: 100});
        cols.push(
          {cle: 'nb_lignes', libelle: 'Lignes', type: 'nombre', largeur: 70},
          {cle: 'total_ht_cents', libelle: 'Total HT', type: 'montant', largeur: 130, total: true},
          {cle: 'total_ttc_cents', libelle: 'Total TTC', type: 'montant', largeur: 130, total: true},
          {cle: 'statut', libelle: 'État', type: 'statut', largeur: 150});
        var g = ERP.grille(zone, {
          nom: 'pieces.' + conf.types.join('_'), cle: 'id', colonnes: cols, lignes: lignes,
          statuts: ERP.statutsPour(conf.types),
          ouvrir: function (l) { ERP.aller(ERP.cheminPiece(l.type, l.id)); },
        });
        requestAnimationFrame(function () { g.focus(); });
      }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
    };
  }

  // ── Écran de pièce ───────────────────────────────────────────────
  function ecranPiece(main, ctx, conf) {
    var id = parseInt(ctx.param, 10);
    var corps = h('div', {className: 'erp-piece'}, ERP.chargement());
    main.appendChild(corps);
    var articles = [], tiers = null, P = null, lignes = [], modifie = false;
    var tbody, totauxEl, focusApres = null;
    var enAttente = Promise.resolve();

    function marquer() {
      modifie = true;
      ERP.garde = function () { return modifie; };
      if (btnEnr) btnEnr.classList.add('erp-btn-accent');
    }
    var btnEnr = null;

    async function charger() {
      var r = await Promise.all([ERP.meta(), ERP.api('/api/erp2/pieces/' + id)]);
      P = r[1];
      if (conf.types.indexOf(P.type) < 0) { ERP.aller(ERP.cheminPiece(P.type, P.id), true); return; }
      var r2 = await Promise.all([
        ERP.api('/api/erp2/tiers/' + P.tiers_id),
        P.statut === 'brouillon' ? ERP.api('/api/erp2/articles') : Promise.resolve([]),
      ]);
      tiers = r2[0];
      var natures = ARTICLES_PAR_SENS[sensDe(P.type)];
      articles = r2[1].filter(function (a) { return a.actif && natures.indexOf(a.nature) >= 0; });
      // Un prix déjà enregistré ne bouge plus quand la quantité change : il a
      // été convenu (et sur une ligne reprise, il vient de la pièce amont).
      lignes = P.lignes.map(function (l) { return Object.assign({_prixManuel: !!l.prix_cents || !!l.ligne_amont_id}, l); });
      modifie = false;
      ERP.garde = null;
      dessiner();
    }

    function lecture() { return P.statut !== 'brouillon'; }

    function tvaTaux(code) {
      var t = ERP.ref('tva').filter(function (x) { return x.code === code; })[0];
      return t ? t.taux_bp : 0;
    }

    // ── En-tête ───────────────────────────────────────────────────
    function blocEntete() {
      var ro = lecture(), vente = sensDe(P.type) === 'vente';
      var adrs = function (type) {
        return tiers.adresses.filter(function (a) { return a.type === type; })
          .map(function (a) { return {v: a.id, l: (a.libelle ? a.libelle + ' — ' : '') + [a.adresse1, a.code_postal + ' ' + a.ville].join(', ')}; });
      };
      var champs = [
        ERP.champ('Date', ERP.saisie(P, 'date_piece', 'date', {lecture: ro, change: marquer})),
      ];
      if (P.type === 'devis') champs.push(ERP.champ('Valable jusqu\'au', ERP.saisie(P, 'date_validite', 'date', {lecture: ro, change: marquer})));
      if (/^(commande|cde_fournisseur|devis)$/.test(P.type)) champs.push(ERP.champ('Livraison prévue', ERP.saisie(P, 'date_livraison', 'date', {lecture: ro, change: marquer})));
      champs.push(ERP.champ(P.type === 'facture_fournisseur' ? 'N° de facture fournisseur' : vente ? 'Réf. commande client' : 'Réf. fournisseur',
        ERP.saisie(P, 'ref_tiers', 'texte', {lecture: ro, change: marquer})));
      champs.push(ERP.champ('Adresse de facturation', ERP.choix(P, 'adresse_facturation_id', adrs('facturation'), {lecture: ro, avecVide: '—', nombre: true, change: marquer}), {large: true}));
      if (vente) champs.push(ERP.champ('Adresse de livraison', ERP.choix(P, 'adresse_livraison_id', adrs('livraison'), {lecture: ro, avecVide: '—', nombre: true, change: marquer}), {large: true}));
      champs.push(ERP.champ('Conditions de paiement', ERP.choix(P, 'condition_paiement', ERP.optionsRef('conditions_paiement'), {lecture: ro, avecVide: '—', change: marquer})));
      champs.push(ERP.champ('Mode de paiement', ERP.choix(P, 'mode_paiement', ERP.optionsRef('modes_paiement'), {lecture: ro, avecVide: '—', change: marquer})));
      if (AVEC_STOCK[P.type]) champs.push(ERP.champ('Dépôt', ERP.choix(P, 'depot', ERP.optionsRef('depots'), {lecture: ro, change: marquer})));
      if (vente) champs.push(ERP.champ('Remise de pied', ERP.saisie(P, 'remise_bp', 'pct', {lecture: ro, placeholder: '0', change: function () { marquer(); majTotaux(); }})));
      if (!ro || P.notes) champs.push(ERP.champ('Notes imprimées', ERP.saisie(P, 'notes', 'zone', {lecture: ro, lignes: 2, change: marquer}), {plein: true}));
      if (!ro || P.notes_internes) champs.push(ERP.champ('Notes internes', ERP.saisie(P, 'notes_internes', 'zone', {lecture: ro, lignes: 2, change: marquer}), {plein: true}));
      return ERP.carte('En-tête', h('div', {className: 'erp-form'}, champs));
    }

    // ── Lignes ────────────────────────────────────────────────────
    function nouvelleLigne() {
      return {article_id: null, libelle: '', quantite_milli: null, base_prix: 1, prix_cents: null, remise_bp: 0,
              tva_code: null, taux_tva_bp: 0, montant_ht_cents: 0, _nouvelle: true};
    }

    function recalculer(l) {
      l.montant_ht_cents = l.article_id ? ERP.calc.montantLigne(l.quantite_milli || 0, l.prix_cents || 0, l.base_prix || 1, l.remise_bp || 0) : 0;
    }

    async function appliquerPrix(l) {
      if (!l.article_id) return;
      try {
        var p = await ERP.api('/api/erp2/prix?article_id=' + l.article_id + '&tiers_id=' + P.tiers_id +
          '&quantite_milli=' + (l.quantite_milli || 0) + '&sens=' + sensDe(P.type));
        l.prix_cents = p.prix_cents; l.base_prix = p.base_prix; l.tva_code = p.tva_code; l.taux_tva_bp = p.taux_tva_bp;
        l._source = p.source;
      } catch (e) { ERP.toast(e.message, 'danger'); }
    }

    function decimales(l) {
      var u = ERP.ref('unites').filter(function (x) { return x.code === l.unite; })[0];
      return u ? u.decimales : 3;
    }

    function celluleArticle(l, i) {
      var inp = h('input', {className: 'erp-input erp-cell', value: l.article_code || '', placeholder: 'Article…', 'data-f': 'article', 'data-i': i});
      ERP.autocomplete(inp, function (q) {
        return ERP.filtrer(articles, q, ['code', 'libelle']).map(function (a) {
          return {titre: a.code + ' — ' + a.libelle, sous: (ERP.M.natures[a.nature] || '') + (a.gere_stock ? ' · stock ' + ERP.fmt.qte(a.stock_milli) + ' ' + a.unite : ''), valeur: a};
        });
      }, async function (a) {
        l.article_id = a.id; l.article_code = a.code; l.libelle = a.libelle; l.unite = a.unite; l.base_prix = a.base_prix;
        l._prixManuel = false;
        await appliquerPrix(l);
        recalculer(l);
        marquer();
        focusApres = {i: i, f: 'qte'};
        dessinerLignes();
      }, {largeur: 460});
      return inp;
    }

    function allerLigneSuivante(i) {
      if (i >= lignes.length - 1) lignes.push(nouvelleLigne());
      focusApres = {i: i + 1, f: 'article'};
      dessinerLignes();
    }

    function saisieCellule(l, i, cle, type, f) {
      var inp = ERP.saisie(l, cle, type, {dec: decimales(l), change: function () {
        // Le calcul de prix est asynchrone : l'enregistrement l'attend
        // (enAttente), sinon Ctrl+S partirait avec l'ancien prix.
        enAttente = (async function () {
          if (cle === 'prix_cents') l._prixManuel = true;
          if (cle === 'quantite_milli' && !l._prixManuel && !l.ligne_amont_id) await appliquerPrix(l);
          if (lignes.indexOf(l) < 0) return;   // pièce rechargée entre-temps
          recalculer(l);
          marquer();
          majLigne(i);
        })();
      }});
      inp.classList.add('erp-cell');
      inp.setAttribute('data-f', f);
      inp.setAttribute('data-i', i);
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          inp.dispatchEvent(new Event('change'));
          if (f === 'remise' || f === 'libelle-texte') allerLigneSuivante(i);
          else {
            var ordre = ['qte', 'prix', 'remise'];
            var suiv = ordre[ordre.indexOf(f) + 1];
            var el = suiv && tbody.querySelector('[data-i="' + i + '"][data-f="' + suiv + '"]');
            if (el) { el.focus(); el.select && el.select(); } else allerLigneSuivante(i);
          }
        }
      });
      return inp;
    }

    function ligneEdition(l, i) {
      var tr = h('tr', {className: l.article_id ? '' : 'texte'});
      if (!l.article_id && l.libelle && !l._nouvelle) {
        // Ligne de texte libre : le libellé occupe la ligne.
        var t = saisieCellule(l, i, 'libelle', 'texte', 'libelle-texte');
        tr.appendChild(h('td', {className: 'rang', text: String(i + 1)}));
        tr.appendChild(h('td', {colSpan: '8'}, t));
      } else {
        var lib = h('input', {className: 'erp-input erp-cell', value: l.libelle || '', 'data-f': 'libelle', 'data-i': i});
        lib.addEventListener('change', function () { l.libelle = lib.value; marquer(); });
        tr.appendChild(h('td', {className: 'rang', text: String(i + 1)}));
        tr.appendChild(h('td', {className: 'c-article'}, celluleArticle(l, i)));
        tr.appendChild(h('td', {className: 'c-libelle'}, lib));
        tr.appendChild(h('td', {className: 'c-qte'}, saisieCellule(l, i, 'quantite_milli', 'qte', 'qte')));
        tr.appendChild(h('td', {className: 'c-unite', text: l.unite || ''}));
        var prix = saisieCellule(l, i, 'prix_cents', 'euros', 'prix');
        tr.appendChild(h('td', {className: 'c-prix'}, prix,
          l.base_prix > 1 ? h('span', {className: 'erp-base', text: '/ ' + ERP.fmt.qte(l.base_prix * 1000, 0)}) : null,
          l._source && l._source !== 'fiche' ? h('span', {className: 'erp-source', title: l._source === 'tarif_tiers' ? 'Tarif négocié du tiers' : 'Tarif général', text: 'T'}) : null));
        tr.appendChild(h('td', {className: 'c-remise'}, saisieCellule(l, i, 'remise_bp', 'pct', 'remise')));
        var tva = ERP.choix(l, 'tva_code', ERP.optionsRef('tva').map(function (o) { return {v: o.v, l: o.v}; }), {change: function () {
          l.taux_tva_bp = tvaTaux(l.tva_code); marquer(); majTotaux();
        }});
        tva.classList.add('erp-cell');
        tr.appendChild(h('td', {className: 'c-tva'}, tva));
        tr.appendChild(h('td', {className: 'c-montant num', 'data-montant': i, text: l.article_id ? ERP.fmt.euros(l.montant_ht_cents) : ''}));
      }
      tr.appendChild(h('td', {className: 'c-suppr'}, h('button', {type: 'button', className: 'erp-x', title: 'Supprimer la ligne', text: '×',
        onclick: function () { lignes.splice(i, 1); marquer(); dessinerLignes(); }})));
      return tr;
    }

    function ligneLecture(l, i) {
      var reste = l.article_id ? Math.max(0, l.quantite_milli - (l.qte_aval_milli || 0)) : 0;
      var suivi = P.statut !== 'annule' && /^(devis|commande|bl|cde_fournisseur|reception)$/.test(P.type);
      var tr = h('tr', {className: (l.article_id ? '' : 'texte') + (l.solde ? ' solde' : '')});
      tr.appendChild(h('td', {className: 'rang', text: String(i + 1)}));
      if (!l.article_id) {
        tr.appendChild(h('td', {colSpan: suivi ? '10' : '8', className: 'c-texte', text: l.libelle}));
        return tr;
      }
      tr.appendChild(h('td', {className: 'c-article'}, ERP.lien(l.article_code, '/fichiers/articles/' + l.article_id)));
      tr.appendChild(h('td', {className: 'c-libelle'}, h('span', {text: l.libelle}),
        l.amont ? h('div', {className: 'erp-amont'}, 'depuis ', ERP.lien(l.amont.numero || 'brouillon', ERP.cheminPiece(l.amont.type, l.amont.id))) : null));
      tr.appendChild(h('td', {className: 'c-qte num', text: ERP.fmt.qte(l.quantite_milli, decimales(l))}));
      tr.appendChild(h('td', {className: 'c-unite', text: l.unite || ''}));
      tr.appendChild(h('td', {className: 'c-prix num'}, ERP.fmt.euros(l.prix_cents),
        l.base_prix > 1 ? h('span', {className: 'erp-base', text: '/ ' + ERP.fmt.qte(l.base_prix * 1000, 0)}) : null));
      tr.appendChild(h('td', {className: 'c-remise num', text: ERP.fmt.pct(l.remise_bp)}));
      tr.appendChild(h('td', {className: 'c-tva', text: l.tva_code || ''}));
      tr.appendChild(h('td', {className: 'c-montant num', text: ERP.fmt.euros(l.montant_ht_cents)}));
      if (suivi) {
        tr.appendChild(h('td', {className: 'c-qte num', text: ERP.fmt.qte(l.qte_aval_milli, decimales(l))}));
        var td = h('td', {className: 'c-reste num'});
        if (l.solde) td.appendChild(h('span', {className: 'erp-pastille ton-neutre', text: 'Soldé'}));
        else td.appendChild(document.createTextNode(ERP.fmt.qte(reste, decimales(l))));
        if (P.statut === 'valide' || P.statut === 'partiel' || l.solde) {
          if (reste > 0 || l.solde) {
            td.appendChild(h('button', {type: 'button', className: 'erp-btn erp-btn-petit erp-solder',
              title: l.solde ? 'Rouvrir le reliquat' : 'Abandonner le reliquat de cette ligne',
              text: l.solde ? 'Rouvrir' : 'Solder',
              onclick: async function () {
                try {
                  await ERP.api('/api/erp2/lignes/' + l.id + '/solde', {method: 'POST', body: {solde: !l.solde}});
                  await charger();
                } catch (e) { ERP.toast(e.message, 'danger'); }
              }}));
          }
        }
        tr.appendChild(td);
      }
      return tr;
    }

    function enTetesLignes() {
      var suivi = lecture() && P.statut !== 'annule' && /^(devis|commande|bl|cde_fournisseur|reception)$/.test(P.type);
      var repris = {devis: 'Commandé', commande: 'Livré', bl: 'Facturé', cde_fournisseur: 'Reçu', reception: 'Facturé'}[P.type];
      return h('tr', null, h('th', {text: '#'}), h('th', {text: 'Article'}), h('th', {text: 'Désignation'}),
        h('th', {className: 'num', text: 'Quantité'}), h('th', {text: 'Unité'}), h('th', {className: 'num', text: 'Prix HT'}),
        h('th', {className: 'num', text: 'Remise'}), h('th', {text: 'TVA'}), h('th', {className: 'num', text: 'Montant HT'}),
        suivi ? h('th', {className: 'num', text: repris}) : null, suivi ? h('th', {className: 'num', text: 'Reste'}) : null,
        lecture() ? null : h('th'));
    }

    function dessinerLignes() {
      if (!tbody) return;
      var ae = document.activeElement, garde = null;
      if (!focusApres && ae && ae.getAttribute && ae.getAttribute('data-i') != null) {
        garde = {i: +ae.getAttribute('data-i'), f: ae.getAttribute('data-f')};
      }
      tbody.textContent = '';
      lignes.forEach(function (l, i) { tbody.appendChild(lecture() ? ligneLecture(l, i) : ligneEdition(l, i)); });
      var cible = focusApres || garde;
      focusApres = null;
      if (cible) {
        var el = tbody.querySelector('[data-i="' + cible.i + '"][data-f="' + cible.f + '"]');
        if (el) { el.focus(); if (el.select) el.select(); }
      }
      majTotaux();
    }

    function majLigne(i) {
      var c = tbody.querySelector('[data-montant="' + i + '"]');
      if (c) c.textContent = lignes[i].article_id ? ERP.fmt.euros(lignes[i].montant_ht_cents) : '';
      majTotaux();
    }

    function majTotaux() {
      if (!totauxEl) return;
      var t = ERP.calc.totaux(lignes, P.remise_bp || 0);
      totauxEl.textContent = '';
      var brut = t.bases.reduce(function (s, b) { return s + b.ht_brut; }, 0);
      var rows = [];
      if (t.remise) {
        rows.push(['Total HT brut', ERP.fmt.euros(brut)]);
        rows.push(['Remise ' + ERP.fmt.pct(P.remise_bp), '− ' + ERP.fmt.euros(t.remise)]);
      }
      rows.push(['Total HT', ERP.fmt.euros(t.ht), 'fort']);
      t.bases.forEach(function (b) { rows.push(['TVA ' + ERP.fmt.pct(b.taux_bp || 0).replace(/^$/, '0 %') + ' sur ' + ERP.fmt.euros(b.ht), ERP.fmt.euros(b.tva)]); });
      rows.push([P.type === 'avoir' ? 'Total TTC à rembourser' : 'Total TTC', ERP.fmt.euros(t.ttc), 'total']);
      rows.forEach(function (r) {
        totauxEl.appendChild(h('div', {className: 'erp-tot-ligne' + (r[2] ? ' ' + r[2] : '')}, h('span', {text: r[0]}), h('b', {text: r[1]})));
      });
    }

    function blocLignes() {
      var table = h('table', {className: 'erp-lignes' + (lecture() ? ' lecture' : '')});
      table.appendChild(h('thead', null, enTetesLignes()));
      tbody = h('tbody');
      table.appendChild(tbody);
      var actions = lecture() ? null : [
        ERP.bouton('+ Ligne', function () { lignes.push(nouvelleLigne()); focusApres = {i: lignes.length - 1, f: 'article'}; marquer(); dessinerLignes(); }, {petit: true}),
        ERP.bouton('+ Texte', function () { lignes.push({article_id: null, libelle: 'Texte', _nouvelle: false}); focusApres = {i: lignes.length - 1, f: 'libelle-texte'}; marquer(); dessinerLignes(); }, {petit: true}),
      ];
      totauxEl = h('div', {className: 'erp-totaux'});
      return ERP.carte('Lignes', h('div', null, h('div', {className: 'erp-lignes-defil'}, table), totauxEl), actions);
    }

    // ── Pièces liées, échéances, stock ────────────────────────────
    function blocLiens() {
      var items = [];
      function ajouterListe(titre, liste) {
        if (!liste.length) return;
        items.push(h('div', {className: 'erp-liens-titre', text: titre}));
        liste.forEach(function (x) {
          items.push(h('div', {className: 'erp-liens-item'},
            ERP.lien(libType(x.type) + ' ' + (x.numero || 'brouillon'), ERP.cheminPiece(x.type, x.id)),
            h('span', {text: ERP.fmt.date(x.date_piece)}), ERP.pastille(x.type, x.statut)));
        });
      }
      ajouterListe('En amont', P.amont);
      ajouterListe('En aval', P.aval);
      if (!items.length) return null;
      return ERP.carte('Pièces liées', h('div', {className: 'erp-liens'}, items));
    }

    function blocEcheances() {
      if (!P.echeances.length) return null;
      return ERP.carte('Échéances', h('div', {className: 'erp-liens'}, P.echeances.map(function (e) {
        return h('div', {className: 'erp-liens-item'}, h('b', {text: ERP.fmt.date(e.date_echeance)}),
          h('span', {text: ERP.fmt.euros(e.montant_cents)}),
          e.regle_cents >= e.montant_cents ? h('span', {className: 'erp-pastille ton-ok', text: 'Réglée'}) :
          h('span', {className: 'erp-pastille ton-' + (e.date_echeance < new Date().toISOString().slice(0, 10) ? 'danger' : 'neutre'),
            text: e.date_echeance < new Date().toISOString().slice(0, 10) ? 'En retard' : 'À venir'}));
      })));
    }

    function blocMouvements() {
      if (!P.mouvements.length) return null;
      return ERP.carte('Mouvements de stock', h('div', {className: 'erp-liens'}, P.mouvements.map(function (m) {
        return h('div', {className: 'erp-liens-item'}, h('b', {text: m.article_code}),
          h('span', {className: 'num ' + (m.quantite_milli < 0 ? 'neg' : 'pos'), text: (m.quantite_milli > 0 ? '+' : '') + ERP.fmt.qte(m.quantite_milli)}),
          h('span', {text: m.depot}), h('span', {className: 'erp-muet', text: m.commentaire || ''}));
      })));
    }

    // ── Actions ───────────────────────────────────────────────────
    function corpsEnvoi() {
      var ent = {};
      ['date_piece', 'date_livraison', 'date_validite', 'ref_tiers', 'adresse_facturation_id', 'adresse_livraison_id',
       'condition_paiement', 'mode_paiement', 'depot', 'remise_bp', 'notes', 'notes_internes'].forEach(function (k) { ent[k] = P[k]; });
      var ls = lignes.filter(function (l) { return l.article_id || (l.libelle && !l._nouvelle); }).map(function (l) {
        return {article_id: l.article_id, libelle: l.libelle, quantite_milli: l.quantite_milli, base_prix: l.base_prix,
                prix_cents: l.prix_cents, remise_bp: l.remise_bp, tva_code: l.tva_code, date_livraison: l.date_livraison,
                ligne_amont_id: l.ligne_amont_id, notes: l.notes};
      });
      return {entete: ent, lignes: ls};
    }

    async function enregistrer(silencieux) {
      await enAttente;
      var vides = lignes.filter(function (l) { return l.article_id && !(l.quantite_milli > 0); });
      if (vides.length) throw new Error('Quantité manquante sur ' + vides.length + ' ligne(s).');
      await ERP.api('/api/erp2/pieces/' + P.id, {method: 'PUT', body: corpsEnvoi()});
      modifie = false;
      ERP.garde = null;
      if (!silencieux) ERP.toast('Enregistré.', 'success');
      await charger();
    }

    async function valider() {
      var legal = (ERP.types[P.type] || {}).legal;
      var ok = await ERP.confirmer(
        legal ? 'Une fois validée, cette pièce reçoit son numéro définitif et ne se modifie plus. Une erreur se corrige par un avoir.'
              : 'La pièce reçoit son numéro' + (AVEC_STOCK[P.type] ? ' et passe ses mouvements de stock' : '') + '.',
        {titre: 'Valider : ' + libType(P.type).toLowerCase(), ok: 'Valider'});
      if (!ok) return;
      await enAttente;
      if (modifie) await enregistrer(true);
      var r = await ERP.api('/api/erp2/pieces/' + P.id + '/valider', {method: 'POST'});
      ERP.toast(libType(P.type) + ' ' + r.numero + ' validé(e).', 'success');
      await charger();
    }

    function boutonImprimer() {
      return ERP.bouton('Imprimer', async function () {
        if (modifie) await enregistrer(true);
        window.open('/imprimer/' + P.id, '_blank');
      }, {titre: 'Document A4 — imprimer ou enregistrer en PDF'});
    }

    function dessinerActions() {
      ctx.actions.textContent = '';
      var a = [];
      if (P.statut === 'brouillon') {
        btnEnr = ERP.bouton('Enregistrer', function () { return enregistrer(); }, {titre: 'Ctrl+S'});
        if (modifie) btnEnr.classList.add('erp-btn-accent');
        a.push(ERP.bouton('Supprimer', async function () {
          if (!(await ERP.confirmer('Supprimer ce brouillon ?', {danger: true, ok: 'Supprimer'}))) return;
          await ERP.api('/api/erp2/pieces/' + P.id, {method: 'DELETE'});
          modifie = false; ERP.garde = null;
          ERP.toast('Brouillon supprimé.', 'success');
          ERP.aller(routeDe(P.type));
        }, {danger: true}));
        a.push(boutonImprimer());
        a.push(btnEnr);
        a.push(ERP.bouton('Valider', valider, {accent: true}));
      } else {
        btnEnr = null;
        a.push(boutonImprimer());
        if (P.statut !== 'annule') {
          (P.aval_possibles || []).forEach(function (cible) {
            a.push(ERP.bouton(ACTION_AVAL[cible] || libType(cible), function () { return transformer(P, cible); }, {accent: cible !== 'avoir'}));
          });
          if (!(ERP.types[P.type] || {}).legal) {
            a.push(ERP.bouton('Annuler la pièce', async function () {
              if (!(await ERP.confirmer('Annuler ' + nomPiece(P) + ' ?' + (AVEC_STOCK[P.type] ? ' Ses mouvements de stock seront contrepassés.' : ''), {danger: true, ok: 'Annuler la pièce'}))) return;
              await ERP.api('/api/erp2/pieces/' + P.id + '/annuler', {method: 'POST'});
              ERP.toast('Pièce annulée.', 'success');
              await charger();
            }, {danger: true}));
          }
        }
      }
      a.forEach(function (b) { ctx.actions.appendChild(b); });
    }

    function dessiner() {
      var t = libType(P.type) + ' ' + nomPiece(P);
      ctx.titre(t, (sensDe(P.type) === 'vente' ? 'Ventes' : 'Achats') + ' › ' + libType(P.type));
      corps.textContent = '';
      var tete = h('div', {className: 'erp-piece-tete'},
        ERP.pastille(P.type, P.statut),
        h('span', {className: 'erp-piece-tiers'}, ERP.lien(tiers.raison_sociale,
          (sensDe(P.type) === 'vente' ? '/fichiers/clients/' : '/fichiers/fournisseurs/') + tiers.id),
          h('span', {className: 'erp-muet', text: ' · ' + tiers.code})),
        tiers.bloque ? h('span', {className: 'erp-pastille ton-danger', text: 'Client bloqué'}) : null,
        P.valide_le ? h('span', {className: 'erp-muet', text: 'Validé le ' + ERP.fmt.date(P.valide_le) + (P.valide_par ? ' par ' + P.valide_par : '')}) : null);
      corps.appendChild(tete);
      // Les lignes prennent toute la largeur : c'est là que l'ADV travaille.
      corps.appendChild(blocLignes());
      var grille = h('div', {className: 'erp-piece-grille'});
      var gauche = h('div', {className: 'erp-piece-principal'}, blocEntete());
      var droite = h('div', {className: 'erp-piece-cote'});
      [blocLiens(), blocEcheances(), blocMouvements()].forEach(function (b) { if (b) droite.appendChild(b); });
      grille.appendChild(gauche);
      if (droite.childNodes.length) grille.appendChild(droite);
      else grille.classList.add('seul');
      corps.appendChild(grille);
      if (!lecture() && !lignes.length) { lignes.push(nouvelleLigne()); focusApres = {i: 0, f: 'article'}; }
      dessinerLignes();
      dessinerActions();
    }

    function clavier(e) {
      if (!document.body.contains(corps)) { document.removeEventListener('keydown', clavier); return; }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (P && P.statut === 'brouillon') {
          if (document.activeElement && document.activeElement.dispatchEvent) document.activeElement.dispatchEvent(new Event('change'));
          enregistrer().catch(function (x) { ERP.toast(x.message, 'danger'); });
        }
      }
    }
    document.addEventListener('keydown', clavier);

    charger().catch(function (e) { corps.textContent = ''; corps.appendChild(ERP.erreur(e)); });
  }

  Object.keys(ROUTES).forEach(function (r) { ERP.ecrans[r] = ecranListe(r); });
  ERP.nouvellePiece = nouvellePiece;
})();
