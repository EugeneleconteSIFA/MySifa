/* Nouvel ERP — fichiers de base : clients, fournisseurs, articles.
 *
 * Liste (grille) et fiche (formulaire) à la même adresse de base :
 * /fichiers/clients, /fichiers/clients/12, /fichiers/clients/nouveau.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  // ── Tiers ────────────────────────────────────────────────────────
  function ecranTiers(role) {
    var base = {client: '/fichiers/clients', prospect: '/fichiers/prospects', fournisseur: '/fichiers/fournisseurs'}[role];
    var nomRole = role;
    return function (main, ctx) {
      if (ctx.param) return ficheTiers(main, ctx, role, base);
      main.classList.add('plein');
      ctx.actions.appendChild(ERP.bouton('Nouveau ' + nomRole, function () { ERP.aller(base + '/nouveau'); }, {accent: true}));
      var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
      main.appendChild(zone);
      ERP.api('/api/erp2/tiers?role=' + role).then(function (l) {
        zone.textContent = '';
        var cols = [
          {cle: 'code', libelle: 'Code', largeur: 90},
          {cle: 'raison_sociale', libelle: 'Raison sociale', largeur: 280},
          {cle: 'ville', libelle: 'Ville', largeur: 160},
          {cle: 'telephone', libelle: 'Téléphone', largeur: 130},
          {cle: 'email', libelle: 'Email', largeur: 220},
          {cle: 'condition_paiement', libelle: 'Paiement', largeur: 110},
        ];
        if (role === 'client') cols.push({cle: 'encours_cents', libelle: 'Encours', type: 'montant', largeur: 120, total: true});
        cols.push({cle: 'etat', libelle: 'État', type: 'statut', largeur: 100});
        l.forEach(function (t) { t.etat = !t.actif ? 'inactif' : t.bloque ? 'bloque' : 'actif'; });
        var g = ERP.grille(zone, {
          nom: 'tiers.' + role, cle: 'id', colonnes: cols, lignes: l,
          statuts: {actif: {libelle: 'Actif', ton: 'ok'}, bloque: {libelle: 'Bloqué', ton: 'danger'}, inactif: {libelle: 'Inactif', ton: 'neutre'}},
          ouvrir: function (t) { ERP.aller(base + '/' + t.id); },
        });
        requestAnimationFrame(function () { g.focus(); });
      }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
    };
  }

  function tableEditable(lignes, colonnes, vide, marquer) {
    // colonnes : [{cle, libelle, type: texte|choix|case, options, largeur}]
    var tbody = h('tbody');
    function dessiner() {
      tbody.textContent = '';
      lignes.forEach(function (l, i) {
        var tr = h('tr');
        colonnes.forEach(function (c) {
          var el;
          if (c.type === 'choix') el = ERP.choix(l, c.cle, c.options, {change: marquer});
          else if (c.type === 'case') { el = h('input', {type: 'checkbox', checked: !!l[c.cle]}); el.addEventListener('change', function () { l[c.cle] = el.checked ? 1 : 0; marquer(); }); }
          else el = ERP.saisie(l, c.cle, 'texte', {change: marquer});
          if (el.classList && c.type !== 'case') el.classList.add('erp-cell');
          tr.appendChild(h('td', {style: c.largeur ? 'width:' + c.largeur : null, className: c.type === 'case' ? 'c-case' : null}, el));
        });
        tr.appendChild(h('td', {className: 'c-suppr'}, h('button', {type: 'button', className: 'erp-x', title: 'Retirer', text: '×',
          onclick: function () { lignes.splice(i, 1); marquer(); dessiner(); }})));
        tbody.appendChild(tr);
      });
    }
    dessiner();
    var table = h('table', {className: 'erp-lignes'},
      h('thead', null, h('tr', null, colonnes.map(function (c) { return h('th', {text: c.libelle, className: c.type === 'case' ? 'c-case' : null}); }), h('th'))), tbody);
    return {
      el: h('div', null, h('div', {className: 'erp-lignes-defil'}, table)),
      ajouter: function () { lignes.push(Object.assign({}, vide)); marquer(); dessiner(); },
    };
  }

  // Fiche tiers en onglets, comme RVGI : principal, interlocuteurs, adresses,
  // banques, commercial et livraison, facturation et comptabilité, pièces.
  var ONGLETS_TIERS = [
    {cle: 'principal', libelle: 'Principal'},
    {cle: 'interlocuteurs', libelle: 'Interlocuteurs'},
    {cle: 'adresses', libelle: 'Adresses'},
    {cle: 'banques', libelle: 'Banques'},
    {cle: 'commercial', libelle: 'Commercial et livraison'},
    {cle: 'facturation', libelle: 'Facturation et comptabilité'},
    {cle: 'pieces', libelle: 'Pièces et tarifs'},
  ];

  function ficheTiers(main, ctx, role, base) {
    var nouveau = ctx.param === 'nouveau';
    var corps = h('div', {className: 'erp-fiche'}, ERP.chargement());
    main.appendChild(corps);
    var T, adresses, contacts, banques, tiersListe = [], modifie = false;
    var onglet = 'principal';
    try { onglet = sessionStorage.getItem('erp_onglet_tiers') || 'principal'; } catch (e) { /* */ }
    function marquer() { modifie = true; ERP.garde = function () { return modifie; }; }

    async function charger() {
      var r = await Promise.all([ERP.meta(), ERP.api('/api/erp2/tiers?role=' + role)]);
      tiersListe = r[1];
      if (nouveau) {
        T = {est_client: role === 'client' ? 1 : 0, est_fournisseur: role === 'fournisseur' ? 1 : 0, est_prospect: role === 'prospect' ? 1 : 0,
             actif: 1, raison_sociale: '',
             etat: 'normal', remise_bp: 0, facturation_auto: 'par_bl', en_compte: 1, langue: 'fr', designation_docs: 'interne',
             adresses: [{type: 'principale', libelle: 'Siège', pays: 'FR', par_defaut: 1}], contacts: [], banques: [], pieces: [], tarifs: []};
      } else {
        T = await ERP.api('/api/erp2/tiers/' + parseInt(ctx.param, 10));
        T.etat = T.etat || (T.bloque ? 'bloque' : 'normal');
      }
      adresses = T.adresses.map(function (a) { return Object.assign({}, a); });
      contacts = T.contacts.map(function (c) { return Object.assign({}, c); });
      banques = (T.banques || []).map(function (b) { return Object.assign({}, b); });
      modifie = false; ERP.garde = null;
      dessiner();
    }

    var CHAMPS = ['code', 'est_client', 'est_fournisseur', 'raison_sociale', 'siret', 'tva_intra', 'email', 'email_facturation',
      'telephone', 'condition_paiement', 'mode_paiement', 'tva_code', 'remise_bp', 'encours_max_cents', 'notes', 'actif',
      'compte_auxiliaire', 'representant_id', 'transporteur_id', 'jours_expedition', 'nom_court', 'groupe_id', 'etat', 'fax',
      'site_web', 'rcs', 'ean', 'nif', 'adv_id', 'categorie1', 'categorie2', 'categorie3', 'langue', 'designation_docs',
      'bat_chaque_cde', 'fiche_conformite', 'facturation_auto', 'factor', 'en_compte', 'escompte_bp', 'franco_cents',
      'marge_brute_bp', 'marge_nette_bp', 'notre_no_fournisseur', 'commission_bp', 'est_prospect'];

    async function enregistrer() {
      var champs = {};
      CHAMPS.forEach(function (k) { if (k in T) champs[k] = T[k]; });
      var r = await ERP.api('/api/erp2/tiers' + (nouveau ? '' : '/' + T.id), {
        method: nouveau ? 'POST' : 'PUT', body: {tiers: champs, adresses: adresses, contacts: contacts, banques: banques}});
      modifie = false; ERP.garde = null;
      ERP.toast('Fiche enregistrée.', 'success');
      if (nouveau) ERP.aller(base + '/' + r.id, true);
      else await charger();
    }

    var opt = function (o) { return Object.keys(o || {}).map(function (k) { return {v: k, l: o[k]}; }); };
    var c = function (lib, cle, type, o) { return ERP.champ(lib, ERP.saisie(T, cle, type || 'texte', Object.assign({change: marquer}, o || {})), o); };
    var sel = function (lib, cle, options, o) { return ERP.champ(lib, ERP.choix(T, cle, options, Object.assign({change: marquer}, o || {})), o); };
    var section = function (t) { return h('div', {className: 'erp-champ plein erp-section-form', text: t}); };

    function ongletPrincipal() {
      var groupes = tiersListe.filter(function (x) { return x.id !== T.id; }).map(function (x) { return {v: x.id, l: x.raison_sociale + ' (' + x.code + ')'}; });
      return ERP.carte(null, h('div', {className: 'erp-form'},
        section('Index'),
        c('Raison sociale', 'raison_sociale', 'texte', {large: true}),
        c('Code', 'code', 'texte', {placeholder: nouveau ? 'automatique' : ''}),
        c('Nom court (code AN)', 'nom_court'),
        sel('Groupe', 'groupe_id', groupes, {avecVide: '—', nombre: true}),
        sel('État', 'etat', opt(ERP.M.etats_tiers), {aide: '« Bloqué » : aucune pièce de vente ne se valide.'}),
        section('Identifiants'),
        c('SIRET', 'siret'), c('RCS', 'rcs'), c('N° TVA intracommunautaire', 'tva_intra'), c('EAN', 'ean'), c('NIF', 'nif'),
        section('Coordonnées'),
        c('Téléphone', 'telephone'), c('Fax', 'fax'), c('Email', 'email'), c('Site', 'site_web'),
        h('div', {className: 'erp-champ plein erp-cases'},
          ERP.case(T, 'est_client', 'Client', {change: marquer}),
          ERP.case(T, 'est_prospect', 'Prospect', {change: marquer}),
          ERP.case(T, 'est_fournisseur', 'Fournisseur', {change: marquer}),
          ERP.case(T, 'actif', 'Actif', {change: marquer})),
        c('Notes', 'notes', 'zone', {plein: true})));
    }

    function ongletInterlocuteurs() {
      var t = tableEditable(contacts, [
        {cle: 'service', libelle: 'Service', largeur: '120px'}, {cle: 'civilite', libelle: 'Civ.', largeur: '60px'},
        {cle: 'nom', libelle: 'Nom'}, {cle: 'fonction', libelle: 'Fonction'}, {cle: 'telephone', libelle: 'Téléphone'},
        {cle: 'gsm', libelle: 'GSM'}, {cle: 'email', libelle: 'Email'},
        {cle: 'envoi_devis', libelle: 'Devis', type: 'case'}, {cle: 'envoi_arc', libelle: 'ARC', type: 'case'},
        {cle: 'envoi_bl', libelle: 'BL', type: 'case'}, {cle: 'envoi_facture', libelle: 'Facture', type: 'case'},
        {cle: 'envoi_relance', libelle: 'Relance', type: 'case'},
      ], {}, marquer);
      return ERP.carte('Interlocuteurs', h('div', null,
        h('p', {className: 'erp-aide', text: 'Les cases cochées désignent les destinataires automatiques de chaque document.'}), t.el),
        ERP.bouton('+ Interlocuteur', t.ajouter, {petit: true}));
    }

    function ongletAdresses() {
      var t = tableEditable(adresses, [
        {cle: 'type', libelle: 'Type', type: 'choix', options: [{v: 'principale', l: 'Principale'}, {v: 'facturation', l: 'Facturation'}, {v: 'livraison', l: 'Livraison'}], largeur: '130px'},
        {cle: 'libelle', libelle: 'Libellé'}, {cle: 'raison_sociale', libelle: 'Raison sociale'},
        {cle: 'adresse1', libelle: 'Adresse'}, {cle: 'adresse2', libelle: 'Complément'},
        {cle: 'code_postal', libelle: 'CP', largeur: '90px'}, {cle: 'ville', libelle: 'Ville'}, {cle: 'pays', libelle: 'Pays', largeur: '70px'},
        {cle: 'telephone', libelle: 'Téléphone'}, {cle: 'email', libelle: 'Email'}, {cle: 'siret', libelle: 'SIRET'},
        {cle: 'par_defaut', libelle: 'Défaut', type: 'case'},
      ], {type: 'livraison', pays: 'FR'}, marquer);
      return ERP.carte('Adresses', h('div', null,
        h('p', {className: 'erp-aide', text: 'Une pièce prend l\'adresse par défaut de son type, à défaut l\'adresse principale.'}), t.el),
        ERP.bouton('+ Adresse', t.ajouter, {petit: true}));
    }

    function ongletBanques() {
      var t = tableEditable(banques, [
        {cle: 'nom', libelle: 'Banque'}, {cle: 'ville', libelle: 'Ville'}, {cle: 'pays', libelle: 'Pays', largeur: '70px'},
        {cle: 'iban', libelle: 'IBAN'}, {cle: 'bic', libelle: 'BIC'},
      ], {pays: 'FR'}, marquer);
      return ERP.carte('Banques', t.el, ERP.bouton('+ Banque', t.ajouter, {petit: true}));
    }

    function ongletCommercial() {
      var M = ERP.M;
      var users = (M.utilisateurs || []).map(function (u) { return {v: u.id, l: u.nom}; });
      return ERP.carte(null, h('div', {className: 'erp-form'},
        section('Représentant et suivi'),
        sel('Représentant', 'representant_id', (M.representants || []).map(function (x) { return {v: x.id, l: x.nom}; }), {avecVide: '—', nombre: true}),
        c('Commission', 'commission_bp', 'pct'),
        sel('ADV', 'adv_id', users, {avecVide: '—', nombre: true}),
        c('Catégorie 1', 'categorie1'), c('Catégorie 2', 'categorie2'), c('Catégorie 3', 'categorie3'),
        section('Livraison'),
        sel('Mode de livraison', 'transporteur_id', (M.transporteurs || []).map(function (x) { return {v: x.id, l: x.nom}; }), {avecVide: 'Par nos soins', nombre: true}),
        c('Jours de livraison', 'jours_expedition', 'entier'),
        c('Franco de port pour', 'franco_cents', 'euros'),
        section('Documents'),
        sel('Langue', 'langue', [{v: 'fr', l: 'Français'}, {v: 'en', l: 'Anglais'}, {v: 'de', l: 'Allemand'}]),
        sel('Désignation imprimée', 'designation_docs', [{v: 'interne', l: 'Interne'}, {v: 'client', l: 'Client'}],
          {aide: 'Client : les pièces portent le libellé client de l\'article.'}),
        h('div', {className: 'erp-champ plein erp-cases'},
          ERP.case(T, 'bat_chaque_cde', 'BAT à chaque commande', {change: marquer}),
          ERP.case(T, 'fiche_conformite', 'Fiche de conformité', {change: marquer})),
        section('Devis'),
        c('Marge brute visée', 'marge_brute_bp', 'pct'), c('Marge nette visée', 'marge_nette_bp', 'pct')));
    }

    function ongletFacturation() {
      return ERP.carte(null, h('div', {className: 'erp-form'},
        section('Règlement'),
        sel('Conditions de paiement', 'condition_paiement', ERP.optionsRef('conditions_paiement'), {avecVide: '—'}),
        sel('Mode de paiement', 'mode_paiement', ERP.optionsRef('modes_paiement'), {avecVide: '—'}),
        sel('Facturation', 'facturation_auto', opt(ERP.M.facturation_auto)),
        c('Email de facturation', 'email_facturation', 'texte', {large: true}),
        section('Accords commerciaux'),
        c('Remise', 'remise_bp', 'pct'), c('Escompte', 'escompte_bp', 'pct'),
        c('Encours autorisé', 'encours_max_cents', 'euros'),
        h('div', {className: 'erp-champ plein erp-cases'},
          ERP.case(T, 'en_compte', 'En compte', {change: marquer}),
          ERP.case(T, 'factor', 'Factor (affacturage)', {change: marquer})),
        section('Comptabilité'),
        sel('Position fiscale', 'tva_code', ERP.optionsRef('tva'), {avecVide: 'Soumis à TVA (taux de l\'article)'}),
        c('Compte de tiers', 'compte_auxiliaire', 'texte', {placeholder: T.code || 'code du tiers'}),
        c('Notre n° chez ce tiers', 'notre_no_fournisseur')));
    }

    function ongletPieces() {
      var blocs = [];
      if (T.pieces.length) {
        blocs.push(ERP.carte('Pièces récentes', h('div', {className: 'erp-liens'}, T.pieces.slice(0, 50).map(function (p) {
          return h('div', {className: 'erp-liens-item'},
            ERP.lien(((ERP.types[p.type] || {}).libelle || p.type) + ' ' + (p.numero || 'brouillon'), ERP.cheminPiece(p.type, p.id)),
            h('span', {text: ERP.fmt.date(p.date_piece)}), h('b', {className: 'num', text: ERP.fmt.euros(p.total_ht_cents)}),
            ERP.pastille(p.type, p.statut));
        }))));
      }
      if (T.tarifs.length) {
        blocs.push(ERP.carte('Tarifs négociés', h('div', {className: 'erp-liens'}, T.tarifs.map(function (t) {
          return h('div', {className: 'erp-liens-item'}, ERP.lien(t.article_code, '/fichiers/articles/' + t.article_id),
            h('span', {text: t.qte_min_milli ? 'dès ' + ERP.fmt.qte(t.qte_min_milli) : ''}),
            h('b', {text: ERP.fmt.euros(t.prix_cents) + (t.base_prix > 1 ? ' / ' + ERP.fmt.qte(t.base_prix * 1000, 0) : '')}));
        }))));
      }
      return blocs.length ? h('div', null, blocs) : h('div', {className: 'erp-vide', text: 'Aucune pièce ni tarif pour ce tiers.'});
    }

    function dessiner() {
      ctx.titre(nouveau ? ({client: 'Nouveau client', prospect: 'Nouveau prospect', fournisseur: 'Nouveau fournisseur'}[role]) : T.raison_sociale,
        'Fichiers › ' + ({client: 'Clients', prospect: 'Prospects', fournisseur: 'Fournisseurs'}[role]) + (nouveau ? '' : ' › ' + T.code + (T.nom_court ? ' · ' + T.nom_court : '')));
      ctx.actions.textContent = '';
      if (!nouveau && T.est_prospect && !T.est_client && role === 'prospect') {
        ctx.actions.appendChild(ERP.bouton('Nouveau devis', function () { return creerPour('devis'); }));
        ctx.actions.appendChild(ERP.bouton('Passer en client', async function () {
          await ERP.api('/api/erp2/tiers/' + T.id, {method: 'PUT', body: {tiers: {est_client: 1, est_prospect: 0}}});
          ERP.toast('Le prospect est maintenant client.', 'success');
          ERP.aller('/fichiers/clients/' + T.id, true);
        }));
      }
      if (!nouveau && T.est_client && role === 'client') {
        ctx.actions.appendChild(ERP.bouton('Nouveau devis', function () { return creerPour('devis'); }));
        ctx.actions.appendChild(ERP.bouton('Nouvelle commande', function () { return creerPour('commande'); }));
      }
      if (!nouveau && T.est_fournisseur && role === 'fournisseur') {
        ctx.actions.appendChild(ERP.bouton('Nouvelle commande', function () { return creerPour('cde_fournisseur'); }));
      }
      ctx.actions.appendChild(ERP.bouton('Enregistrer', enregistrer, {accent: true, titre: 'Ctrl+S'}));
      corps.textContent = '';
      var onglets = ONGLETS_TIERS.filter(function (o) { return !(nouveau && o.cle === 'pieces'); });
      corps.appendChild(h('div', {className: 'erp-onglets'}, onglets.map(function (o) {
        return h('button', {type: 'button', className: 'erp-onglet' + (o.cle === onglet ? ' actif' : ''), text: o.libelle,
          onclick: function () {
            if (document.activeElement) document.activeElement.dispatchEvent(new Event('change'));
            onglet = o.cle;
            try { sessionStorage.setItem('erp_onglet_tiers', onglet); } catch (e) { /* */ }
            dessiner();
          }});
      })));
      var vue = {principal: ongletPrincipal, interlocuteurs: ongletInterlocuteurs, adresses: ongletAdresses, banques: ongletBanques,
                 commercial: ongletCommercial, facturation: ongletFacturation, pieces: ongletPieces}[onglet] || ongletPrincipal;
      corps.appendChild(vue());
      if (nouveau && onglet === 'principal') requestAnimationFrame(function () { var f = corps.querySelector('input'); if (f) f.focus(); });
    }

    async function creerPour(type) {
      var r = await ERP.api('/api/erp2/pieces', {method: 'POST', body: {type: type, tiers_id: T.id}});
      ERP.aller(ERP.cheminPiece(type, r.id));
    }

    function clavier(e) {
      if (!document.body.contains(corps)) { document.removeEventListener('keydown', clavier); return; }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (document.activeElement) document.activeElement.dispatchEvent(new Event('change'));
        enregistrer().catch(function (x) { ERP.toast(x.message, 'danger'); });
      }
    }
    document.addEventListener('keydown', clavier);
    charger().catch(function (e) { corps.textContent = ''; corps.appendChild(ERP.erreur(e)); });
  }

  // ── Articles ─────────────────────────────────────────────────────
  // Produits, matières, prestations : une liste par nature, comme le menu
  // Fichiers de RVGI. Les matières se rangent par type (familles de nature
  // « matière », réglables dans Paramètres › Familles).
  var LISTES_ARTICLES = {
    '/fichiers/produits': {nature: 'pf', nouveau: 'Nouveau produit'},
    '/fichiers/matieres': {nature: 'mp', nouveau: 'Nouvelle matière'},
    '/fichiers/prestations': {nature: 'service', nouveau: 'Nouvelle prestation'},
    '/fichiers/articles': {nature: null, nouveau: 'Nouvel article'},
  };

  function ecranArticles(base) {
    var conf = LISTES_ARTICLES[base];
    return function (main, ctx) {
      if (ctx.param) return ficheArticle(main, ctx, conf.nature, base);
      main.classList.add('plein');
      ctx.actions.appendChild(ERP.bouton(conf.nouveau, function () { ERP.aller(base + '/nouveau'); }, {accent: true}));
      var famille = null;
      try { famille = sessionStorage.getItem('erp_famille_' + base) || null; } catch (e) { /* */ }
      var onglets = h('div', {className: 'erp-onglets'});
      var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
      main.appendChild(onglets);
      main.appendChild(zone);
      Promise.all([ERP.meta(), ERP.api('/api/erp2/articles' + (conf.nature ? '?nature=' + conf.nature : ''))]).then(function (r) {
        var tous = r[1];
        tous.forEach(function (a) { a.famille_lib = ERP.refLibelle('familles', a.famille); });
        var g = null;
        function filtrees() { return famille ? tous.filter(function (a) { return a.famille === famille; }) : tous; }
        if (conf.nature === 'mp') {
          var fams = ERP.ref('familles', true).filter(function (f) { return f.nature === 'mp'; });
          var dessinerOnglets = function () {
            onglets.textContent = '';
            [{code: null, libelle: 'Toutes'}].concat(fams).forEach(function (f) {
              var n = f.code ? tous.filter(function (a) { return a.famille === f.code; }).length : tous.length;
              onglets.appendChild(h('button', {type: 'button', className: 'erp-onglet' + (f.code === famille ? ' actif' : ''),
                text: f.libelle + (n ? ' · ' + n : ''), onclick: function () {
                  famille = f.code;
                  try { sessionStorage.setItem('erp_famille_' + base, famille || ''); } catch (e) { /* */ }
                  dessinerOnglets(); if (g) g.maj(filtrees());
                }}));
            });
          };
          dessinerOnglets();
        }
        zone.textContent = '';
        var cols = [{cle: 'code', libelle: 'Code', largeur: 110}, {cle: 'libelle', libelle: 'Libellé', largeur: 320}];
        if (!conf.nature) {
          var natures = {};
          Object.keys(ERP.M.natures).forEach(function (k) { natures[k] = {libelle: ERP.M.natures[k], ton: k === 'pf' ? 'accent' : k === 'mp' ? 'warn' : 'neutre'}; });
          cols.push({cle: 'nature', libelle: 'Nature', type: 'statut', largeur: 150});
        }
        if (conf.nature !== 'mp' && conf.nature !== 'service') cols.push({cle: 'client_nom', libelle: 'Client', largeur: 200},
          {cle: 'ref_client', libelle: 'Réf. client', largeur: 130});
        cols.push({cle: 'format', libelle: conf.nature === 'mp' ? 'Laize (mm)' : 'Format (mm)', largeur: 110, rendu: function (a) {
          if (!a.format_l_dmm) return '';
          var l = (a.format_l_dmm / 10).toLocaleString('fr-FR');
          return conf.nature === 'mp' ? l : l + ' × ' + ((a.format_a_dmm || 0) / 10).toLocaleString('fr-FR'); }});
        cols.push({cle: 'famille_lib', libelle: conf.nature === 'mp' ? 'Type' : 'Famille', largeur: 160},
          {cle: 'sous_famille', libelle: 'Sous-famille', largeur: 120},
          {cle: 'unite', libelle: 'Unité', largeur: 70});
        if (conf.nature !== 'mp') cols.push({cle: 'prix_vente_cents', libelle: 'Prix de vente', type: 'montant', largeur: 120});
        if (conf.nature !== 'pf') cols.push({cle: 'prix_achat_cents', libelle: 'Prix d\'achat', type: 'montant', largeur: 120});
        cols.push({cle: 'base_prix', libelle: 'Pour', type: 'nombre', largeur: 70});
        if (conf.nature !== 'service') cols.push({cle: 'stock_milli', libelle: 'Stock', type: 'qte', largeur: 120});
        g = ERP.grille(zone, {
          nom: 'articles.' + (conf.nature || 'tous'), cle: 'id', lignes: filtrees(), colonnes: cols, statuts: natures,
          ouvrir: function (a) { ERP.aller(base + '/' + a.id); },
        });
        requestAnimationFrame(function () { g.focus(); });
      }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
    };
  }
  Object.keys(LISTES_ARTICLES).forEach(function (b) { ERP.ecrans[b] = ecranArticles(b); });
  ERP.cheminArticle = function (a) {
    return ({pf: '/fichiers/produits/', mp: '/fichiers/matieres/', service: '/fichiers/prestations/'}[a.nature] || '/fichiers/articles/') + a.id;
  };

  function ficheArticle(main, ctx, natureListe, base) {
    base = base || '/fichiers/articles';
    var nouveau = ctx.param === 'nouveau';
    var corps = h('div', {className: 'erp-fiche'}, ERP.chargement());
    main.appendChild(corps);
    var A, tarifs, tiers = [], bats = [], modifie = false;
    function marquer() { modifie = true; ERP.garde = function () { return modifie; }; }

    async function charger() {
      var r = await Promise.all([ERP.meta(), ERP.api('/api/erp2/tiers'), ERP.api('/api/erp2/bats')]);
      tiers = r[1];
      bats = r[2];
      if (nouveau) A = {nature: natureListe || 'pf', unite: natureListe === 'mp' ? 'ML' : natureListe === 'service' ? 'FORF' : 'ETQ',
                        base_prix: natureListe === 'pf' ? 1000 : 1, gere_stock: natureListe === 'service' ? 0 : 1, actif: 1, libelle: '',
                        tarifs: [], stock: [], mouvements: []};
      else A = await ERP.api('/api/erp2/articles/' + parseInt(ctx.param, 10));
      tarifs = A.tarifs.map(function (t) { return Object.assign({}, t); });
      modifie = false; ERP.garde = null;
      dessiner();
    }

    async function enregistrer() {
      var champs = {};
      ['code', 'libelle', 'libelle_client', 'nature', 'famille', 'unite', 'base_prix', 'prix_vente_cents', 'prix_achat_cents',
       'tva_code', 'gere_stock', 'fournisseur_id', 'client_id', 'notes', 'actif', 'ref_client', 'format_l_dmm', 'format_a_dmm',
       'conditionnement', 'origine_prod', 'bat_id', 'fsc_allegation', 'fsc_pct', 'fsc_bois', 'fsc_requis', 'designation',
       'code3', 'couleur', 'poids_g', 'sous_famille', 'gamme', 'cliche', 'ean', 'unite_achat', 'unite_conditionnement',
       'taxe_eco_cents', 'code_douane', 'prix_stock_cents', 'stock_mini_milli', 'stock_maxi_milli', 'zone',
       'ref_client2', 'ref_client3', 'ml_par_bobine_milli']
        .forEach(function (k) { if (k in A) champs[k] = A[k]; });
      var r = await ERP.api('/api/erp2/articles' + (nouveau ? '' : '/' + A.id), {
        method: nouveau ? 'POST' : 'PUT',
        body: {article: champs, tarifs: tarifs.map(function (t) {
          return {tiers_id: t.tiers_id, sens: t.sens, qte_min_milli: t.qte_min_milli || 0, prix_cents: t.prix_cents, debut: t.debut, fin: t.fin,
                  laize_dmm: t.laize_dmm, ml_par_bobine_milli: t.ml_par_bobine_milli, ref_fournisseur: t.ref_fournisseur};
        })}});
      modifie = false; ERP.garde = null;
      ERP.toast('Article enregistré.', 'success');
      if (nouveau) ERP.aller(base + '/' + r.id, true);
      else await charger();
    }

    function blocTarifs() {
      var tbody = h('tbody');
      var optTiers = tiers.map(function (t) { return {v: t.id, l: t.raison_sociale + ' (' + t.code + ')'}; });
      function dessinerT() {
        tbody.textContent = '';
        tarifs.forEach(function (t, i) {
          var cell = function (el) { if (el.classList) el.classList.add('erp-cell'); return h('td', null, el); };
          tbody.appendChild(h('tr', null,
            cell(ERP.choix(t, 'sens', [{v: 'vente', l: 'Vente'}, {v: 'achat', l: 'Achat'}], {change: marquer})),
            cell(ERP.choix(t, 'tiers_id', optTiers, {avecVide: 'Tous (tarif général)', nombre: true, change: marquer})),
            cell(ERP.saisie(t, 'qte_min_milli', 'qte', {change: marquer, placeholder: '0'})),
            cell(ERP.saisie(t, 'prix_cents', 'euros', {change: marquer})),
            cell(ERP.saisie(t, 'debut', 'date', {change: marquer})),
            cell(ERP.saisie(t, 'fin', 'date', {change: marquer})),
            cell(ERP.saisie(t, 'laize_dmm', 'entier', {change: marquer, placeholder: '1/10 mm'})),
            cell(ERP.saisie(t, 'ml_par_bobine_milli', 'qte', {change: marquer, placeholder: 'ML'})),
            cell(ERP.saisie(t, 'ref_fournisseur', 'texte', {change: marquer})),
            h('td', {className: 'c-suppr'}, h('button', {type: 'button', className: 'erp-x', text: '×', title: 'Retirer',
              onclick: function () { tarifs.splice(i, 1); marquer(); dessinerT(); }}))));
        });
      }
      dessinerT();
      var table = h('table', {className: 'erp-lignes'},
        h('thead', null, h('tr', null, ['Sens', 'Tiers', 'À partir de (qté)', 'Prix HT', 'Du', 'Au', 'Laize (1/10 mm)', 'Bobine (ML)', 'Réf. fournisseur', '']
          .map(function (x) { return h('th', {text: x}); }))),
        tbody);
      return ERP.carte('Tarifs', h('div', null,
        h('p', {className: 'erp-aide', text: 'Prix pour ' + ERP.fmt.qte((A.base_prix || 1) * 1000, 0) + ' ' + (A.unite || '') +
          '. Le plus grand palier atteint s\'applique ; un tarif du tiers passe avant le tarif général, qui passe avant le prix de la fiche.'}),
        h('div', {className: 'erp-lignes-defil'}, table)),
        ERP.bouton('+ Tarif', function () { tarifs.push({sens: A.nature === 'mp' ? 'achat' : 'vente', qte_min_milli: 0}); marquer(); dessinerT(); }, {petit: true}));
    }

    function dessiner() {
      ctx.titre(nouveau ? 'Nouvel article' : A.code + ' — ' + A.libelle, 'Fichiers › Articles');
      ctx.actions.textContent = '';
      ctx.actions.appendChild(ERP.bouton('Enregistrer', enregistrer, {accent: true, titre: 'Ctrl+S'}));
      corps.textContent = '';
      var natures = Object.keys(ERP.M.natures).map(function (k) { return {v: k, l: ERP.M.natures[k]}; });
      var familles = ERP.ref('familles', true).map(function (f) { return {v: f.code, l: f.libelle}; });
      var fourn = tiers.filter(function (t) { return t.est_fournisseur; }).map(function (t) { return {v: t.id, l: t.raison_sociale}; });
      var clients = tiers.filter(function (t) { return t.est_client; }).map(function (t) { return {v: t.id, l: t.raison_sociale}; });
      var sec = function (t) { return h('div', {className: 'erp-champ plein erp-section-form', text: t}); };
      var c = function (lib, cle, type, o) { return ERP.champ(lib, ERP.saisie(A, cle, type || 'texte', {change: marquer, placeholder: (o || {}).placeholder}), o); };
      var sel = function (lib, cle, options, o) { return ERP.champ(lib, ERP.choix(A, cle, options, Object.assign({change: marquer}, o || {})), o); };
      var unites = ERP.optionsRef('unites');
      // Disposition de la fiche produit de RVGI : index, informations générales,
      // index de recherche, gestion, stock, client.
      var ident = h('div', {className: 'erp-form'},
        sec('Index'),
        sel('Client', 'client_id', clients, {avecVide: '— (matière, prestation)', nombre: true,
          aide: 'Obligatoire pour un produit fini : il appartient à un client, son code est « code client / rang ».'}),
        c('Code', 'code', 'texte', {placeholder: nouveau ? 'automatique' : ''}),
        c('Code 3 (variante, laize)', 'code3'),
        sel('Nature', 'nature', natures),
        sec('Informations générales'),
        c('Libellé', 'libelle', 'texte', {large: true}),
        c('Désignation (lignes suivantes)', 'designation', 'zone', {plein: true, aide: 'Support, adhésif, conditionnement : une ligne par ligne imprimée.'}),
        c('Laize (1/10 mm)', 'format_l_dmm', 'entier', {aide: '450 pour 45 mm'}),
        c('Avance (1/10 mm)', 'format_a_dmm', 'entier'),
        c('Couleur', 'couleur'), c('Poids (g)', 'poids_g', 'entier'),
        c('Conditionnement', 'conditionnement', 'texte', {large: true}),
        sec('Index de recherche'),
        sel('Famille', 'famille', familles, {avecVide: '—'}),
        c('Sous-famille', 'sous_famille'), c('Gamme', 'gamme'), c('Cliché', 'cliche'), c('Code-barres EAN', 'ean'),
        sel('Origine habituelle', 'origine_prod', Object.keys(ERP.M.origines || {}).map(function (k) { return {v: k, l: ERP.M.origines[k]}; }), {avecVide: '—'}),
        sel('BAT (module BAT de MySifa)', 'bat_id', bats.map(function (b) {
          return {v: b.id, l: b.description + ' / ' + b.numero_article + ' — ' + ((ERP.M.bat_libelles || {})[b.statut] || b.statut)}; }),
          {avecVide: '— aucun', nombre: true, large: true, aide: 'Exigé validé pour une ligne en création ou en modification.'}),
        sec('Client'),
        c('Réf. produit client', 'ref_client'), c('Référence 2 client', 'ref_client2'), c('Référence 3 client', 'ref_client3'),
        c('Libellé client', 'libelle_client', 'zone', {plein: true, aide: 'Imprimé à la place du libellé quand la fiche client demande la désignation client.'}),
        sel('Fournisseur habituel', 'fournisseur_id', fourn, {avecVide: '—', nombre: true}),
        c('Notes', 'notes', 'zone', {plein: true}),
        h('div', {className: 'erp-champ plein erp-cases'},
          ERP.case(A, 'gere_stock', 'Géré en stock', {change: marquer}), ERP.case(A, 'actif', 'Actif', {change: marquer})));
      var prix = h('div', {className: 'erp-form'},
        sec('Gestion'),
        sel('Unité de vente', 'unite', unites),
        sel('Unité d\'achat', 'unite_achat', unites, {avecVide: '= unité de vente'}),
        sel('Unité de conditionnement', 'unite_conditionnement', unites, {avecVide: '= unité de vente'}),
        c('Prix exprimé pour', 'base_prix', 'entier', {aide: '1000 pour un prix au mille.'}),
        c('Prix de vente HT', 'prix_vente_cents', 'euros'), c('Prix d\'achat HT', 'prix_achat_cents', 'euros'),
        sel('TVA', 'tva_code', ERP.optionsRef('tva'), {avecVide: '—'}),
        c('Taxe écologique', 'taxe_eco_cents', 'euros'), c('Code douane', 'code_douane'),
        sec('Stock'),
        c('Prix de stock', 'prix_stock_cents', 'euros'), c('Zone', 'zone'),
        c('Stock mini', 'stock_mini_milli', 'qte'), c('Stock maxi', 'stock_maxi_milli', 'qte'),
        A.nature === 'mp' ? c('Longueur d\'une bobine (ML)', 'ml_par_bobine_milli', 'qte',
          {aide: 'Achat au m² : la commande affiche laize, nombre de bobines et mètres linéaires.'}) : null);
      // FSC : la matière porte son allégation ; le produit fini dit s'il est vendu certifié.
      // L'allégation d'un dossier se calcule des matières consommées (règle de l'affiche atelier).
      var fscOpts = Object.keys(ERP.M.fsc || {}).map(function (k) { return {v: k, l: ERP.M.fsc[k]}; });
      var blocFsc = A.nature === 'mp'
        ? h('div', {className: 'erp-form'},
            ERP.champ('Allégation FSC', ERP.choix(A, 'fsc_allegation', fscOpts, {avecVide: '— (non renseignée)', change: marquer})),
            ERP.champ('Pourcentage (Mix / Recycled)', ERP.saisie(A, 'fsc_pct', 'entier', {change: marquer})),
            h('div', {className: 'erp-champ plein erp-cases'}, ERP.case(A, 'fsc_bois', 'Matière à base de bois (papier). Décocher pour un film, une colle, une encre : ils ne comptent pas.', {change: marquer})))
        : h('div', {className: 'erp-form'},
            h('div', {className: 'erp-champ plein erp-cases'}, ERP.case(A, 'fsc_requis', 'Vendu certifié FSC : une alerte tombe si la matière consommée ne permet pas l\'allégation.', {change: marquer})));
      var gauche = h('div', {className: 'erp-piece-principal'}, ERP.carte('Produit', ident), ERP.carte('Gestion et stock', prix),
        A.nature !== 'service' ? ERP.carte('FSC', blocFsc) : null, blocTarifs());
      var droite = h('div', {className: 'erp-piece-cote'});
      if (!nouveau && A.gere_stock) {
        droite.appendChild(ERP.carte('Stock', h('div', {className: 'erp-liens'},
          A.stock.length ? A.stock.map(function (s) {
            return h('div', {className: 'erp-liens-item'}, h('span', {text: ERP.refLibelle('depots', s.depot)}),
              h('b', {className: 'num', text: ERP.fmt.qte(s.quantite_milli) + ' ' + A.unite}));
          }) : h('div', {className: 'erp-muet', text: 'Aucun mouvement.'}))));
        if (A.mouvements.length) {
          droite.appendChild(ERP.carte('Derniers mouvements', h('div', {className: 'erp-liens'}, A.mouvements.slice(0, 20).map(function (m) {
            return h('div', {className: 'erp-liens-item'}, h('span', {text: ERP.fmt.date(m.date_mvt)}),
              m.piece_id ? ERP.lien(m.numero || '—', ERP.cheminPiece(m.piece_type, m.piece_id)) : h('span', {text: m.type}),
              h('b', {className: 'num ' + (m.quantite_milli < 0 ? 'neg' : 'pos'), text: (m.quantite_milli > 0 ? '+' : '') + ERP.fmt.qte(m.quantite_milli)}));
          }))));
        }
      }
      var g = h('div', {className: 'erp-piece-grille' + (droite.childNodes.length ? '' : ' seul')}, gauche);
      if (droite.childNodes.length) g.appendChild(droite);
      corps.appendChild(g);
    }

    function clavier(e) {
      if (!document.body.contains(corps)) { document.removeEventListener('keydown', clavier); return; }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (document.activeElement) document.activeElement.dispatchEvent(new Event('change'));
        enregistrer().catch(function (x) { ERP.toast(x.message, 'danger'); });
      }
    }
    document.addEventListener('keydown', clavier);
    charger().catch(function (e) { corps.textContent = ''; corps.appendChild(ERP.erreur(e)); });
  }

  ERP.ecrans['/fichiers/clients'] = ecranTiers('client');
  ERP.ecrans['/fichiers/prospects'] = ecranTiers('prospect');
  ERP.ecrans['/fichiers/fournisseurs'] = ecranTiers('fournisseur');
})();
