/* Nouvel ERP — demandes de prix MyAO (Achats › Demandes MyAO).
 *
 * MyAO consulte les fournisseurs et clôture la demande ; ici, une demande
 * clôturée devient une commande fournisseur en brouillon chez le fournisseur
 * retenu. Les correspondances (fournisseur ERP, article de chaque ligne) sont
 * proposées d'après les passages précédents et restent modifiables.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  var STATUTS = {brouillon: {libelle: 'Brouillon', ton: 'neutre'}, envoyee: {libelle: 'Envoyée', ton: 'warn'},
                 cloturee: {libelle: 'Clôturée', ton: 'ok'}};

  function liste(main, ctx) {
    main.classList.add('plein');
    main.appendChild(h('p', {className: 'erp-aide', text: 'Les demandes de prix se préparent, s\'envoient et se clôturent dans MyAO. ' +
      'Une demande clôturée avec un fournisseur retenu se transforme ici en commande fournisseur.'}));
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    ERP.api('/api/erp2/myao').then(function (l) {
      zone.textContent = '';
      l.forEach(function (d) { d.commande = d.commande_numero || (d.statut === 'cloturee' && d.fournisseur_retenu ? 'À commander' : ''); });
      var g = ERP.grille(zone, {
        nom: 'achats.myao', cle: 'id', lignes: l, statuts: STATUTS,
        colonnes: [
          {cle: 'reference', libelle: 'Référence', largeur: 130},
          {cle: 'titre', libelle: 'Titre', largeur: 300},
          {cle: 'date_creation', libelle: 'Créée le', type: 'date', largeur: 100},
          {cle: 'date_limite', libelle: 'Date limite', type: 'date', largeur: 100},
          {cle: 'statut', libelle: 'État', type: 'statut', largeur: 120},
          {cle: 'nb_lignes', libelle: 'Lignes', type: 'nombre', largeur: 80},
          {cle: 'nb_reponses', libelle: 'Réponses', type: 'nombre', largeur: 90},
          {cle: 'fournisseur_retenu', libelle: 'Fournisseur retenu', largeur: 220},
          {cle: 'commande', libelle: 'Commande ERP', largeur: 140},
          {cle: 'date_cloture', libelle: 'Clôturée le', type: 'date', largeur: 100, masquee: true},
        ],
        ouvrir: function (d) { ERP.aller('/achats/myao/' + d.id); },
      });
      requestAnimationFrame(function () { g.focus(); });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  }

  async function fiche(main, ctx) {
    var corps = h('div', {className: 'erp-fiche'}, ERP.chargement());
    main.appendChild(corps);
    var r = await Promise.all([ERP.api('/api/erp2/myao/' + parseInt(ctx.param, 10)), ERP.api('/api/erp2/tiers?role=fournisseur'),
                               ERP.api('/api/erp2/articles')]);
    var D = r[0], fourn = r[1], arts = r[2].filter(function (a) { return a.actif && a.nature !== 'service'; });
    ctx.titre('Demande MyAO ' + D.demande.reference, 'Achats › Demandes MyAO');
    corps.textContent = '';
    var C = {tiers_id: D.tiers_id};
    var choix = D.lignes.map(function (L) {
      var o = L.options[0];
      return {ligne_id: L.ligne_id, serie_id: o.serie_id, article_id: L.article_id, quantite_milli: o.quantite_milli,
              prix_cents: o.prix_cents, base_prix: o.base_prix || 1000};
    });
    var possible = D.demande.statut === 'cloturee' && D.retenu && !D.commande;

    corps.appendChild(ERP.carte(null, h('div', {className: 'erp-form'},
      ERP.champ('Demande', h('div', {className: 'erp-lecture', text: D.demande.reference + ' — ' + (D.demande.titre || '')}), {large: true}),
      ERP.champ('État', h('div', {className: 'erp-lecture', text: (STATUTS[D.demande.statut] || {}).libelle || D.demande.statut})),
      ERP.champ('Fournisseur retenu (MyAO)', h('div', {className: 'erp-lecture', text: D.retenu ? D.retenu.nom_fournisseur : '— aucun'})),
      possible ? ERP.champ('Fournisseur ERP', ERP.choix(C, 'tiers_id', fourn.map(function (t) { return {v: t.id, l: t.raison_sociale + ' (' + t.code + ')'}; }),
        {avecVide: '— choisir', nombre: true}), {large: true, aide: 'Retenu pour les prochaines demandes de ce fournisseur.'}) : null,
      D.commande ? ERP.champ('Commande fournisseur', ERP.lien(D.commande.numero || 'Brouillon', ERP.cheminPiece('cde_fournisseur', D.commande.id))) : null)));

    var tbody = h('tbody');
    D.lignes.forEach(function (L, i) {
      var c = choix[i];
      var art = h('input', {className: 'erp-input erp-cell', placeholder: 'Article ERP (vide : ne pas commander)', disabled: !possible});
      var a0 = arts.find(function (a) { return a.id === c.article_id; });
      if (a0) art.value = a0.code + ' — ' + a0.libelle;
      ERP.autocomplete(art, function (q) {
        return ERP.filtrer(arts, q, ['code', 'libelle', 'ref_client']).map(function (a) { return {titre: a.code + ' — ' + a.libelle, sous: a.unite, valeur: a}; });
      }, function (a) { c.article_id = a.id; art.value = a.code + ' — ' + a.libelle; });
      art.addEventListener('change', function () { if (!art.value.trim()) c.article_id = null; });
      var note = h('div', {className: 'erp-aide'});
      var prix = {v: c.prix_cents};
      var qte = {v: c.quantite_milli};
      function majOption() {
        var o = L.options.find(function (x) { return (x.serie_id || null) === (c.serie_id || null); }) || L.options[0];
        c.quantite_milli = qte.v = o.quantite_milli; c.prix_cents = prix.v = o.prix_cents; c.base_prix = o.base_prix || 1000;
        note.textContent = o.note || '';
        note.classList.toggle('neg', !!o.a_saisir);
        champQ.replaceWith(champQ = ERP.saisie(qte, 'v', 'qte', {change: function (v) { c.quantite_milli = v; }, lecture: !possible}));
        champP.replaceWith(champP = ERP.saisie(prix, 'v', 'euros', {change: function (v) { c.prix_cents = v; }, lecture: !possible}));
      }
      var champQ = ERP.saisie(qte, 'v', 'qte', {change: function (v) { c.quantite_milli = v; }, lecture: !possible});
      var champP = ERP.saisie(prix, 'v', 'euros', {change: function (v) { c.prix_cents = v; }, lecture: !possible});
      var serie = L.options.length > 1
        ? ERP.choix(c, 'serie_id', L.options.map(function (o) { return {v: o.serie_id, l: o.serie || ERP.fmt.qte(o.quantite_milli)}; }),
            {nombre: true, change: majOption})
        : h('span', {className: 'erp-muet', text: '—'});
      note.textContent = L.options[0].note || '';
      note.classList.toggle('neg', !!L.options[0].a_saisir);
      tbody.appendChild(h('tr', null,
        h('td', null, h('b', {text: L.ref_produit || ''}), h('div', {text: L.designation || ''}), note),
        h('td', null, serie), h('td', null, champQ), h('td', null, champP),
        h('td', {className: 'erp-muet', text: 'pour 1 000'}), h('td', {style: 'min-width:280px'}, art)));
    });
    corps.appendChild(ERP.carte('Lignes de la demande', h('div', {className: 'erp-lignes-defil'}, h('table', {className: 'erp-lignes'},
      h('thead', null, h('tr', null, ['Produit demandé', 'Série', 'Quantité', 'Prix HT', '', 'Article ERP'].map(function (x) { return h('th', {text: x}); }))),
      tbody))));

    if (possible) {
      ctx.actions.appendChild(ERP.bouton('Créer la commande fournisseur', async function () {
        if (!C.tiers_id) throw new Error('Choisir le fournisseur ERP.');
        var res = await ERP.api('/api/erp2/myao/' + D.demande.id + '/commande', {method: 'POST', body: {tiers_id: C.tiers_id, lignes: choix}});
        ERP.toast('Commande fournisseur créée (brouillon).', 'success');
        ERP.aller(ERP.cheminPiece('cde_fournisseur', res.id));
      }, {accent: true}));
    } else if (!D.commande) {
      corps.appendChild(h('p', {className: 'erp-aide', text: 'La demande doit être clôturée dans MyAO avec un fournisseur retenu pour devenir une commande.'}));
    }
  }

  ERP.ecrans['/achats/myao'] = function (main, ctx) {
    if (ctx.param) return fiche(main, ctx).catch(function (e) { main.textContent = ''; main.appendChild(ERP.erreur(e)); });
    liste(main, ctx);
  };
})();
