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
    var base = role === 'client' ? '/fichiers/clients' : '/fichiers/fournisseurs';
    var nomRole = role === 'client' ? 'client' : 'fournisseur';
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
          if (el.classList) el.classList.add('erp-cell');
          tr.appendChild(h('td', {style: c.largeur ? 'width:' + c.largeur : null}, el));
        });
        tr.appendChild(h('td', {className: 'c-suppr'}, h('button', {type: 'button', className: 'erp-x', title: 'Retirer', text: '×',
          onclick: function () { lignes.splice(i, 1); marquer(); dessiner(); }})));
        tbody.appendChild(tr);
      });
    }
    dessiner();
    var table = h('table', {className: 'erp-lignes'},
      h('thead', null, h('tr', null, colonnes.map(function (c) { return h('th', {text: c.libelle}); }), h('th'))), tbody);
    return {
      el: h('div', null, h('div', {className: 'erp-lignes-defil'}, table)),
      ajouter: function () { lignes.push(Object.assign({}, vide)); marquer(); dessiner(); },
    };
  }

  function ficheTiers(main, ctx, role, base) {
    var nouveau = ctx.param === 'nouveau';
    var corps = h('div', {className: 'erp-fiche'}, ERP.chargement());
    main.appendChild(corps);
    var T, adresses, contacts, modifie = false;
    function marquer() { modifie = true; ERP.garde = function () { return modifie; }; }

    async function charger() {
      await ERP.meta();
      if (nouveau) {
        T = {est_client: role === 'client' ? 1 : 0, est_fournisseur: role === 'fournisseur' ? 1 : 0, actif: 1, raison_sociale: '',
             remise_bp: 0, adresses: [{type: 'facturation', libelle: 'Siège', pays: 'FR', par_defaut: 1}], contacts: [], pieces: [], tarifs: []};
      } else {
        T = await ERP.api('/api/erp2/tiers/' + parseInt(ctx.param, 10));
      }
      adresses = T.adresses.map(function (a) { return Object.assign({}, a); });
      contacts = T.contacts.map(function (c) { return Object.assign({}, c); });
      modifie = false; ERP.garde = null;
      dessiner();
    }

    async function enregistrer() {
      var champs = {};
      ['code', 'est_client', 'est_fournisseur', 'raison_sociale', 'siret', 'tva_intra', 'email', 'email_facturation', 'telephone',
       'condition_paiement', 'mode_paiement', 'tva_code', 'remise_bp', 'encours_max_cents', 'bloque', 'notes', 'actif', 'compte_auxiliaire']
        .forEach(function (k) { if (k in T) champs[k] = T[k]; });
      var r = await ERP.api('/api/erp2/tiers' + (nouveau ? '' : '/' + T.id), {
        method: nouveau ? 'POST' : 'PUT', body: {tiers: champs, adresses: adresses, contacts: contacts}});
      modifie = false; ERP.garde = null;
      ERP.toast('Fiche enregistrée.', 'success');
      if (nouveau) ERP.aller(base + '/' + r.id, true);
      else await charger();
    }

    function dessiner() {
      ctx.titre(nouveau ? (role === 'client' ? 'Nouveau client' : 'Nouveau fournisseur') : T.raison_sociale,
        'Fichiers › ' + (role === 'client' ? 'Clients' : 'Fournisseurs') + (nouveau ? '' : ' › ' + T.code));
      ctx.actions.textContent = '';
      if (!nouveau && T.est_client && role === 'client') {
        ctx.actions.appendChild(ERP.bouton('Nouveau devis', function () { return creerPour('devis'); }));
        ctx.actions.appendChild(ERP.bouton('Nouvelle commande', function () { return creerPour('commande'); }));
      }
      if (!nouveau && T.est_fournisseur && role === 'fournisseur') {
        ctx.actions.appendChild(ERP.bouton('Nouvelle commande', function () { return creerPour('cde_fournisseur'); }));
      }
      ctx.actions.appendChild(ERP.bouton('Enregistrer', enregistrer, {accent: true, titre: 'Ctrl+S'}));
      corps.textContent = '';

      var ident = h('div', {className: 'erp-form'},
        ERP.champ('Raison sociale', ERP.saisie(T, 'raison_sociale', 'texte', {change: marquer}), {large: true}),
        ERP.champ('Code', ERP.saisie(T, 'code', 'texte', {change: marquer, placeholder: nouveau ? 'automatique' : ''})),
        ERP.champ('SIRET', ERP.saisie(T, 'siret', 'texte', {change: marquer})),
        ERP.champ('N° TVA intracommunautaire', ERP.saisie(T, 'tva_intra', 'texte', {change: marquer})),
        ERP.champ('Téléphone', ERP.saisie(T, 'telephone', 'texte', {change: marquer})),
        ERP.champ('Email', ERP.saisie(T, 'email', 'texte', {change: marquer})),
        ERP.champ('Email de facturation', ERP.saisie(T, 'email_facturation', 'texte', {change: marquer})),
        h('div', {className: 'erp-champ plein erp-cases'},
          ERP.case(T, 'est_client', 'Client', {change: marquer}),
          ERP.case(T, 'est_fournisseur', 'Fournisseur', {change: marquer}),
          ERP.case(T, 'bloque', 'Bloqué (aucune pièce de vente ne se valide)', {change: marquer}),
          ERP.case(T, 'actif', 'Actif', {change: marquer})));

      var cond = h('div', {className: 'erp-form'},
        ERP.champ('Conditions de paiement', ERP.choix(T, 'condition_paiement', ERP.optionsRef('conditions_paiement'), {avecVide: '—', change: marquer})),
        ERP.champ('Mode de paiement', ERP.choix(T, 'mode_paiement', ERP.optionsRef('modes_paiement'), {avecVide: '—', change: marquer})),
        ERP.champ('Régime de TVA', ERP.choix(T, 'tva_code', ERP.optionsRef('tva'), {avecVide: 'Taux de l\'article', change: marquer}),
          {aide: 'Export ou livraison intracommunautaire : le taux du tiers remplace celui de l\'article.'}),
        role === 'client' ? ERP.champ('Remise habituelle', ERP.saisie(T, 'remise_bp', 'pct', {change: marquer, placeholder: '0'})) : null,
        role === 'client' ? ERP.champ('Encours maximum', ERP.saisie(T, 'encours_max_cents', 'euros', {change: marquer})) : null,
        ERP.champ('Compte auxiliaire', ERP.saisie(T, 'compte_auxiliaire', 'texte', {change: marquer, placeholder: T.code || 'code du tiers'})),
        ERP.champ('Notes', ERP.saisie(T, 'notes', 'zone', {change: marquer}), {plein: true}));

      var tAdr = tableEditable(adresses, [
        {cle: 'type', libelle: 'Type', type: 'choix', options: [{v: 'facturation', l: 'Facturation'}, {v: 'livraison', l: 'Livraison'}], largeur: '130px'},
        {cle: 'libelle', libelle: 'Libellé'}, {cle: 'adresse1', libelle: 'Adresse'}, {cle: 'adresse2', libelle: 'Complément'},
        {cle: 'code_postal', libelle: 'CP', largeur: '90px'}, {cle: 'ville', libelle: 'Ville'}, {cle: 'pays', libelle: 'Pays', largeur: '70px'},
        {cle: 'par_defaut', libelle: 'Défaut', type: 'case', largeur: '60px'},
      ], {type: 'livraison', pays: 'FR'}, marquer);
      var tCt = tableEditable(contacts, [
        {cle: 'nom', libelle: 'Nom'}, {cle: 'fonction', libelle: 'Fonction'}, {cle: 'email', libelle: 'Email'}, {cle: 'telephone', libelle: 'Téléphone'},
      ], {}, marquer);

      var gauche = h('div', {className: 'erp-piece-principal'},
        ERP.carte('Identité', ident),
        ERP.carte('Adresses', tAdr.el, ERP.bouton('+ Adresse', tAdr.ajouter, {petit: true})),
        ERP.carte('Contacts', tCt.el, ERP.bouton('+ Contact', tCt.ajouter, {petit: true})),
        ERP.carte('Conditions commerciales', cond));
      var droite = h('div', {className: 'erp-piece-cote'});
      if (!nouveau) {
        if (T.pieces.length) {
          droite.appendChild(ERP.carte('Pièces récentes', h('div', {className: 'erp-liens'}, T.pieces.slice(0, 25).map(function (p) {
            return h('div', {className: 'erp-liens-item'},
              ERP.lien(((ERP.types[p.type] || {}).libelle || p.type) + ' ' + (p.numero || 'brouillon'), ERP.cheminPiece(p.type, p.id)),
              h('span', {text: ERP.fmt.date(p.date_piece)}), ERP.pastille(p.type, p.statut));
          }))));
        }
        if (T.tarifs.length) {
          droite.appendChild(ERP.carte('Tarifs négociés', h('div', {className: 'erp-liens'}, T.tarifs.map(function (t) {
            return h('div', {className: 'erp-liens-item'}, ERP.lien(t.article_code, '/fichiers/articles/' + t.article_id),
              h('span', {text: t.qte_min_milli ? 'dès ' + ERP.fmt.qte(t.qte_min_milli) : ''}),
              h('b', {text: ERP.fmt.euros(t.prix_cents) + (t.base_prix > 1 ? ' / ' + ERP.fmt.qte(t.base_prix * 1000, 0) : '')}));
          }))));
        }
      }
      var g = h('div', {className: 'erp-piece-grille' + (droite.childNodes.length ? '' : ' seul')}, gauche);
      if (droite.childNodes.length) g.appendChild(droite);
      corps.appendChild(g);
      if (nouveau) requestAnimationFrame(function () { var f = corps.querySelector('input'); if (f) f.focus(); });
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
  ERP.ecrans['/fichiers/articles'] = function (main, ctx) {
    if (ctx.param) return ficheArticle(main, ctx);
    main.classList.add('plein');
    ctx.actions.appendChild(ERP.bouton('Nouvel article', function () { ERP.aller('/fichiers/articles/nouveau'); }, {accent: true}));
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    Promise.all([ERP.meta(), ERP.api('/api/erp2/articles')]).then(function (r) {
      zone.textContent = '';
      var natures = {};
      Object.keys(ERP.M.natures).forEach(function (k) { natures[k] = {libelle: ERP.M.natures[k], ton: k === 'pf' ? 'accent' : k === 'mp' ? 'warn' : 'neutre'}; });
      r[1].forEach(function (a) { a.famille_lib = ERP.refLibelle('familles', a.famille); });
      var g = ERP.grille(zone, {
        nom: 'articles', cle: 'id', lignes: r[1], statuts: natures,
        colonnes: [
          {cle: 'code', libelle: 'Code', largeur: 100},
          {cle: 'libelle', libelle: 'Libellé', largeur: 320},
          {cle: 'nature', libelle: 'Nature', type: 'statut', largeur: 150},
          {cle: 'famille_lib', libelle: 'Famille', largeur: 170},
          {cle: 'unite', libelle: 'Unité', largeur: 70},
          {cle: 'prix_vente_cents', libelle: 'Prix de vente', type: 'montant', largeur: 120},
          {cle: 'prix_achat_cents', libelle: 'Prix d\'achat', type: 'montant', largeur: 120},
          {cle: 'base_prix', libelle: 'Pour', type: 'nombre', largeur: 70},
          {cle: 'stock_milli', libelle: 'Stock', type: 'qte', largeur: 120},
        ],
        ouvrir: function (a) { ERP.aller('/fichiers/articles/' + a.id); },
      });
      requestAnimationFrame(function () { g.focus(); });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  function ficheArticle(main, ctx) {
    var nouveau = ctx.param === 'nouveau';
    var corps = h('div', {className: 'erp-fiche'}, ERP.chargement());
    main.appendChild(corps);
    var A, tarifs, tiers = [], bats = [], modifie = false;
    function marquer() { modifie = true; ERP.garde = function () { return modifie; }; }

    async function charger() {
      var r = await Promise.all([ERP.meta(), ERP.api('/api/erp2/tiers'), ERP.api('/api/erp2/bats')]);
      tiers = r[1];
      bats = r[2];
      if (nouveau) A = {nature: 'pf', unite: 'U', base_prix: 1, gere_stock: 1, actif: 1, libelle: '', tarifs: [], stock: [], mouvements: []};
      else A = await ERP.api('/api/erp2/articles/' + parseInt(ctx.param, 10));
      tarifs = A.tarifs.map(function (t) { return Object.assign({}, t); });
      modifie = false; ERP.garde = null;
      dessiner();
    }

    async function enregistrer() {
      var champs = {};
      ['code', 'libelle', 'libelle_client', 'nature', 'famille', 'unite', 'base_prix', 'prix_vente_cents', 'prix_achat_cents',
       'tva_code', 'gere_stock', 'fournisseur_id', 'client_id', 'notes', 'actif', 'ref_client', 'format_l_dmm', 'format_a_dmm',
       'conditionnement', 'origine_prod', 'bat_id'].forEach(function (k) { if (k in A) champs[k] = A[k]; });
      var r = await ERP.api('/api/erp2/articles' + (nouveau ? '' : '/' + A.id), {
        method: nouveau ? 'POST' : 'PUT',
        body: {article: champs, tarifs: tarifs.map(function (t) {
          return {tiers_id: t.tiers_id, sens: t.sens, qte_min_milli: t.qte_min_milli || 0, prix_cents: t.prix_cents, debut: t.debut, fin: t.fin};
        })}});
      modifie = false; ERP.garde = null;
      ERP.toast('Article enregistré.', 'success');
      if (nouveau) ERP.aller('/fichiers/articles/' + r.id, true);
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
            h('td', {className: 'c-suppr'}, h('button', {type: 'button', className: 'erp-x', text: '×', title: 'Retirer',
              onclick: function () { tarifs.splice(i, 1); marquer(); dessinerT(); }}))));
        });
      }
      dessinerT();
      var table = h('table', {className: 'erp-lignes'},
        h('thead', null, h('tr', null, ['Sens', 'Tiers', 'À partir de (qté)', 'Prix HT', 'Du', 'Au', ''].map(function (x) { return h('th', {text: x}); }))),
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
      var ident = h('div', {className: 'erp-form'},
        ERP.champ('Libellé', ERP.saisie(A, 'libelle', 'texte', {change: marquer}), {large: true}),
        ERP.champ('Code', ERP.saisie(A, 'code', 'texte', {change: marquer, placeholder: nouveau ? 'automatique' : ''})),
        ERP.champ('Nature', ERP.choix(A, 'nature', natures, {change: marquer})),
        ERP.champ('Famille', ERP.choix(A, 'famille', familles, {avecVide: '—', change: marquer})),
        ERP.champ('Libellé client', ERP.saisie(A, 'libelle_client', 'texte', {change: marquer}), {large: true,
          aide: 'Désignation imprimée sur les pièces du client, si elle diffère.'}),
        ERP.champ('Client propriétaire', ERP.choix(A, 'client_id', clients, {avecVide: '— (article catalogue)', nombre: true, change: marquer})),
        ERP.champ('Fournisseur habituel', ERP.choix(A, 'fournisseur_id', fourn, {avecVide: '—', nombre: true, change: marquer})),
        ERP.champ('Réf. produit client', ERP.saisie(A, 'ref_client', 'texte', {change: marquer})),
        ERP.champ('Laize (1/10 mm)', ERP.saisie(A, 'format_l_dmm', 'entier', {change: marquer}), {aide: '900 pour 90 mm'}),
        ERP.champ('Avance (1/10 mm)', ERP.saisie(A, 'format_a_dmm', 'entier', {change: marquer})),
        ERP.champ('Conditionnement', ERP.saisie(A, 'conditionnement', 'texte', {change: marquer}), {large: true}),
        ERP.champ('Origine habituelle', ERP.choix(A, 'origine_prod', Object.keys(ERP.M.origines || {}).map(function (k) { return {v: k, l: ERP.M.origines[k]}; }), {avecVide: '—', change: marquer})),
        ERP.champ('BAT (module BAT de MySifa)', ERP.choix(A, 'bat_id', bats.map(function (b) {
          return {v: b.id, l: b.description + ' / ' + b.numero_article + ' — ' + ((ERP.M.bat_libelles || {})[b.statut] || b.statut)}; }),
          {avecVide: '— aucun', nombre: true, change: marquer}), {large: true, aide: 'Exigé validé pour une ligne en création ou en modification.'}),
        ERP.champ('Notes', ERP.saisie(A, 'notes', 'zone', {change: marquer}), {plein: true}),
        h('div', {className: 'erp-champ plein erp-cases'},
          ERP.case(A, 'gere_stock', 'Géré en stock', {change: marquer}), ERP.case(A, 'actif', 'Actif', {change: marquer})));
      var prix = h('div', {className: 'erp-form'},
        ERP.champ('Unité', ERP.choix(A, 'unite', ERP.optionsRef('unites'), {change: marquer})),
        ERP.champ('Prix exprimé pour', ERP.saisie(A, 'base_prix', 'entier', {change: marquer}), {aide: '1000 pour un prix au mille.'}),
        ERP.champ('Prix de vente HT', ERP.saisie(A, 'prix_vente_cents', 'euros', {change: marquer})),
        ERP.champ('Prix d\'achat HT', ERP.saisie(A, 'prix_achat_cents', 'euros', {change: marquer})),
        ERP.champ('TVA', ERP.choix(A, 'tva_code', ERP.optionsRef('tva'), {avecVide: '—', change: marquer})));
      var gauche = h('div', {className: 'erp-piece-principal'}, ERP.carte('Article', ident), ERP.carte('Unité et prix', prix), blocTarifs());
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
  ERP.ecrans['/fichiers/fournisseurs'] = ecranTiers('fournisseur');
})();
