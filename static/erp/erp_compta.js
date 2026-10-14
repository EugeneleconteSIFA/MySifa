/* Nouvel ERP — règlements et lettrage.
 *
 * Saisie d'un règlement : tiers, montant, puis affectation aux échéances
 * ouvertes du tiers. L'affectation se pré-remplit de la plus ancienne à la
 * plus récente ; chaque montant reste modifiable. Le serveur refuse une
 * affectation au-delà du reste dû ou du montant reçu.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  function aujourdhui() { return new Date().toISOString().slice(0, 10); }

  // o : {tiers: {id, raison_sociale}, sens, echeanceId}
  ERP.saisirReglement = async function (o, apres) {
    o = o || {};
    await ERP.meta();
    var sens = o.sens || 'encaissement';
    var R = {tiers_id: o.tiers ? o.tiers.id : null, sens: sens, date_reglement: aujourdhui(),
             mode_paiement: 'VIR', montant_cents: null, reference: ''};
    var echeances = [], affect = {};
    var zoneEch = h('div', {className: 'erp-regl-ech'});
    var resteEl = h('div', {className: 'erp-aide'});
    var tiersInp = h('input', {className: 'erp-input', placeholder: 'Client ou fournisseur', value: o.tiers ? o.tiers.raison_sociale : ''});

    function totalAffecte() { return Object.keys(affect).reduce(function (s, k) { return s + (affect[k] || 0); }, 0); }
    function majReste() {
      var t = totalAffecte();
      resteEl.textContent = 'Affecté : ' + ERP.fmt.euros(t) + (R.montant_cents != null ? ' · non affecté : ' + ERP.fmt.euros(R.montant_cents - t) : '');
      resteEl.classList.toggle('erreur', R.montant_cents != null && t > R.montant_cents);
    }
    function repartir() {
      affect = {};
      var reste = R.montant_cents || 0;
      // L'échéance demandée d'abord, puis de la plus ancienne à la plus récente.
      var ordre = echeances.slice().sort(function (a, b) {
        if (a.id === o.echeanceId) return -1;
        if (b.id === o.echeanceId) return 1;
        return a.date_echeance < b.date_echeance ? -1 : 1;
      });
      ordre.forEach(function (e) { var m = Math.min(reste, e.reste_cents); if (m > 0) { affect[e.id] = m; reste -= m; } });
    }
    function dessinerEch() {
      zoneEch.textContent = '';
      if (!R.tiers_id) { zoneEch.appendChild(h('div', {className: 'erp-muet', text: 'Choisir un tiers pour voir ses échéances ouvertes.'})); return; }
      if (!echeances.length) { zoneEch.appendChild(h('div', {className: 'erp-muet', text: 'Aucune échéance ouverte : le règlement restera non affecté.'})); majReste(); return; }
      var tbody = h('tbody');
      echeances.forEach(function (e) {
        var obj = {v: affect[e.id] || null};
        var inp = ERP.saisie(obj, 'v', 'euros', {change: function (v) { affect[e.id] = v || 0; majReste(); }});
        inp.classList.add('erp-cell');
        tbody.appendChild(h('tr', null,
          h('td', null, h('b', {text: e.numero})), h('td', {text: ERP.fmt.date(e.date_echeance)}),
          h('td', {className: 'num', text: ERP.fmt.euros(e.reste_cents)}), h('td', {className: 'c-qte'}, inp)));
      });
      zoneEch.appendChild(h('table', {className: 'erp-lignes'},
        h('thead', null, h('tr', null, h('th', {text: 'Facture'}), h('th', {text: 'Échéance'}), h('th', {className: 'num', text: 'Reste dû'}), h('th', {className: 'num', text: 'Affecté'}))),
        tbody));
      majReste();
    }
    async function chargerEch() {
      echeances = R.tiers_id ? (await ERP.api('/api/erp2/echeances?ouvertes=true&tiers_id=' + R.tiers_id)).filter(function (e) {
        return (sens === 'encaissement') === (e.type === 'facture');
      }) : [];
      if (R.montant_cents == null && o.echeanceId) {
        var e = echeances.filter(function (x) { return x.id === o.echeanceId; })[0];
        if (e) { R.montant_cents = e.reste_cents; montantInp.value = ERP.fmt.eurosNu(e.reste_cents); }
      }
      repartir();
      dessinerEch();
    }

    var tiersListe = await ERP.api('/api/erp2/tiers?role=' + (sens === 'encaissement' ? 'client' : 'fournisseur'));
    ERP.autocomplete(tiersInp, function (q) {
      return ERP.filtrer(tiersListe, q, ['code', 'raison_sociale']).map(function (t) {
        return {titre: t.raison_sociale, sous: t.code + (t.encours_cents ? ' · encours ' + ERP.fmt.euros(t.encours_cents) : ''), valeur: t};
      });
    }, function (t) { R.tiers_id = t.id; tiersInp.value = t.raison_sociale; chargerEch(); }, {ouvrirAuFocus: !o.tiers});

    var montantInp = ERP.saisie(R, 'montant_cents', 'euros', {change: function () { repartir(); dessinerEch(); }});
    var corps = h('div', null,
      h('div', {className: 'erp-form'},
        ERP.champ(sens === 'encaissement' ? 'Client' : 'Fournisseur', tiersInp, {large: true}),
        ERP.champ('Date', ERP.saisie(R, 'date_reglement', 'date')),
        ERP.champ('Montant reçu', montantInp),
        ERP.champ('Mode', ERP.choix(R, 'mode_paiement', ERP.optionsRef('modes_paiement'))),
        ERP.champ('Référence (libellé bancaire, n° de chèque)', ERP.saisie(R, 'reference', 'texte'), {large: true})),
      h('div', {className: 'erp-liens-titre', text: 'Affectation aux échéances'}), zoneEch, resteEl);
    dessinerEch();
    if (R.tiers_id) chargerEch();
    ERP.modal(sens === 'encaissement' ? 'Encaissement client' : 'Paiement fournisseur', corps, [
      {libelle: 'Annuler'},
      {libelle: 'Enregistrer', accent: true, action: async function () {
        if (!R.tiers_id) throw new Error('Choisir un tiers.');
        if (!(R.montant_cents > 0)) throw new Error('Montant obligatoire.');
        if (totalAffecte() > R.montant_cents) throw new Error('Les affectations dépassent le montant reçu.');
        await ERP.api('/api/erp2/reglements', {method: 'POST', body: Object.assign({}, R, {
          affectations: Object.keys(affect).map(function (k) { return {echeance_id: +k, montant_cents: affect[k]}; })})});
        ERP.toast('Règlement enregistré.', 'success');
        if (apres) apres();
      }},
    ], {large: true});
  };

  // ── Relances ─────────────────────────────────────────────────────
  var NIVEAUX = {1: 'Rappel', 2: 'Relance', 3: 'Mise en demeure'};

  function ouvrirRelance(r) {
    return ERP.api('/api/erp2/compta/relances/' + r.tiers_id).then(function (d) {
      var R = {niveau: r.niveau_propose, notes: ''};
      var corps = h('div', null,
        h('p', {className: 'erp-modal-texte', text: d.echeances.length + ' facture(s) échue(s), ' + ERP.fmt.euros(r.echu_cents) +
          ' dus, plus ancien retard ' + r.jours_retard + ' jours.'}),
        h('table', {className: 'erp-lignes lecture'},
          h('thead', null, h('tr', null, h('th', {text: 'Facture'}), h('th', {text: 'Échéance'}), h('th', {className: 'num', text: 'Reste dû'}))),
          h('tbody', null, d.echeances.map(function (e) {
            return h('tr', null, h('td', null, ERP.lien(e.numero, ERP.cheminPiece('facture', e.piece_id))),
              h('td', {text: ERP.fmt.date(e.date_echeance)}), h('td', {className: 'num', text: ERP.fmt.euros(e.reste_cents)}));
          }))),
        h('div', {className: 'erp-form'},
          ERP.champ('Niveau', ERP.choix(R, 'niveau', [1, 2, 3].map(function (n) { return {v: n, l: n + ' — ' + NIVEAUX[n]}; }), {nombre: true})),
          ERP.champ('Note (appel, promesse de paiement…)', ERP.saisie(R, 'notes', 'texte'), {large: true})),
        d.historique.length ? h('div', null, h('div', {className: 'erp-liens-titre', text: 'Relances précédentes'}),
          h('div', {className: 'erp-liens'}, d.historique.map(function (x) {
            return h('div', {className: 'erp-liens-item'}, h('span', {text: ERP.fmt.date(x.date_relance)}),
              h('b', {text: NIVEAUX[x.niveau]}), h('span', {text: ERP.fmt.euros(x.montant_cents)}),
              h('span', {className: 'erp-muet', text: x.notes || ''}));
          }))) : null);
      ERP.modal('Relancer ' + r.raison_sociale, corps, [
        {libelle: 'Fermer'},
        {libelle: 'Imprimer la lettre', action: function () { window.open('/imprimer-relance/' + r.tiers_id + '?niveau=' + R.niveau, '_blank'); return false; }},
        {libelle: 'Enregistrer la relance', accent: true, action: async function () {
          await ERP.api('/api/erp2/compta/relances/' + r.tiers_id, {method: 'POST', body: R});
          ERP.toast('Relance enregistrée.', 'success');
          ERP.rafraichir();
        }},
      ], {large: true});
    });
  }

  ERP.ecrans['/compta/relances'] = function (main) {
    main.classList.add('plein');
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    Promise.all([ERP.meta(), ERP.api('/api/erp2/compta/relances')]).then(function (r) {
      zone.textContent = '';
      r[1].forEach(function (x) { x.niveau_lib = String(x.niveau_propose); x.dernier = x.dernier_niveau ? NIVEAUX[x.dernier_niveau] : ''; });
      if (!r[1].length) { zone.appendChild(h('div', {className: 'erp-vide', text: 'Aucune facture échue : rien à relancer.'})); return; }
      var g = ERP.grille(zone, {
        nom: 'compta.relances', cle: 'tiers_id', lignes: r[1],
        statuts: {'1': {libelle: 'Rappel', ton: 'warn'}, '2': {libelle: 'Relance', ton: 'danger'}, '3': {libelle: 'Mise en demeure', ton: 'danger'}},
        colonnes: [
          {cle: 'raison_sociale', libelle: 'Client', largeur: 260},
          {cle: 'nb', libelle: 'Factures', type: 'nombre', largeur: 90},
          {cle: 'echu_cents', libelle: 'Échu', type: 'montant', largeur: 130, total: true},
          {cle: 'plus_ancienne', libelle: 'Plus ancienne échéance', type: 'date', largeur: 170},
          {cle: 'jours_retard', libelle: 'Retard (j)', type: 'nombre', largeur: 100},
          {cle: 'derniere_relance', libelle: 'Dernière relance', type: 'date', largeur: 140},
          {cle: 'dernier', libelle: 'Niveau envoyé', largeur: 140},
          {cle: 'niveau_lib', libelle: 'À envoyer', type: 'statut', largeur: 150},
        ],
        ouvrir: function (x) { ouvrirRelance(x).catch(function (e) { ERP.toast(e.message, 'danger'); }); },
      });
      requestAnimationFrame(function () { g.focus(); });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  ERP.ecrans['/compta/reglements'] = function (main, ctx) {
    main.classList.add('plein');
    ctx.actions.appendChild(ERP.bouton('Paiement fournisseur', function () { return ERP.saisirReglement({sens: 'decaissement'}, ERP.rafraichir); }));
    ctx.actions.appendChild(ERP.bouton('Encaissement client', function () { return ERP.saisirReglement({sens: 'encaissement'}, ERP.rafraichir); }, {accent: true}));
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    Promise.all([ERP.meta(), ERP.api('/api/erp2/reglements')]).then(function (r) {
      zone.textContent = '';
      r[1].forEach(function (x) {
        x.non_affecte_cents = x.montant_cents - x.affecte_cents;
        x.mode_lib = ERP.refLibelle('modes_paiement', x.mode_paiement);
      });
      ERP.grille(zone, {
        nom: 'compta.reglements', cle: 'id', lignes: r[1],
        statuts: {encaissement: {libelle: 'Encaissement', ton: 'ok'}, decaissement: {libelle: 'Décaissement', ton: 'warn'}},
        colonnes: [
          {cle: 'date_reglement', libelle: 'Date', type: 'date', largeur: 100},
          {cle: 'sens', libelle: 'Sens', type: 'statut', largeur: 140},
          {cle: 'tiers_nom', libelle: 'Tiers', largeur: 240},
          {cle: 'mode_lib', libelle: 'Mode', largeur: 120},
          {cle: 'reference', libelle: 'Référence', largeur: 200},
          {cle: 'montant_cents', libelle: 'Montant', type: 'montant', largeur: 120, total: true},
          {cle: 'non_affecte_cents', libelle: 'Non affecté', type: 'montant', largeur: 120, total: true},
          {cle: 'factures', libelle: 'Factures réglées', largeur: 220},
          {cle: 'id', libelle: '', largeur: 110, rendu: function (x) {
            return h('button', {type: 'button', className: 'erp-btn erp-btn-petit', text: 'Supprimer', onclick: async function (e) {
              e.stopPropagation();
              if (!(await ERP.confirmer('Supprimer ce règlement ? Les factures concernées redeviennent dues.', {danger: true, ok: 'Supprimer'}))) return;
              try { await ERP.api('/api/erp2/reglements/' + x.id, {method: 'DELETE'}); ERP.toast('Règlement supprimé.', 'success'); ERP.rafraichir(); }
              catch (er) { ERP.toast(er.message, 'danger'); }
            }});
          }},
        ],
      });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };
})();
