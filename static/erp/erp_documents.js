/* Nouvel ERP — documents fournisseurs (BL, factures) lus par l'IA.
 *
 * Achats › Documents fournisseurs : déposer un PDF ou une photo, l'IA le lit,
 * l'ERP retrouve le fournisseur, la commande et ses lignes et montre les
 * écarts ; un clic prépare la réception ou la facture fournisseur en
 * brouillon. Rien n'est validé automatiquement.
 *
 * ERP.carteDocuments(piece) : la même chose depuis une pièce d'achat.
 */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  var STATUTS = {depose: {libelle: 'Déposé', ton: 'neutre'}, analyse: {libelle: 'Lu', ton: 'accent'},
                 erreur: {libelle: 'Erreur de lecture', ton: 'danger'}, traite: {libelle: 'Traité', ton: 'ok'}};
  var NATURES = {bl: 'Bon de livraison', facture: 'Facture', autre: 'Autre'};

  async function deposer(fichier, pieceId) {
    var fd = new FormData();
    fd.append('fichier', fichier);
    if (pieceId) fd.append('piece_id', String(pieceId));
    var r = await fetch('/api/erp2/documents', {method: 'POST', body: fd, credentials: 'include'});
    var j = await r.json().catch(function () { return {}; });
    if (!r.ok) throw new Error(j.detail || 'Dépôt refusé.');
    return j.id;
  }

  // Dépôt puis lecture ; ouvre le document lu.
  async function deposerEtLire(fichiers, pieceId, apres) {
    for (var i = 0; i < fichiers.length; i++) {
      var id = await deposer(fichiers[i], pieceId);
      ERP.toast('Lecture de ' + fichiers[i].name + '…', 'info');
      try {
        await ERP.api('/api/erp2/documents/' + id + '/analyser', {method: 'POST'});
      } catch (e) { ERP.toast(e.message, 'danger'); }
      if (apres) apres();
      if (fichiers.length === 1) ouvrir(id, apres);
    }
  }

  function choisirFichiers(pieceId, apres) {
    var inp = h('input', {type: 'file', accept: '.pdf,.png,.jpg,.jpeg,.webp', multiple: true, style: 'display:none'});
    inp.addEventListener('change', function () {
      if (inp.files.length) deposerEtLire(Array.prototype.slice.call(inp.files), pieceId, apres).catch(function (e) { ERP.toast(e.message, 'danger'); });
      inp.remove();
    });
    document.body.appendChild(inp);
    inp.click();
  }

  function zoneDepot(pieceId, apres) {
    var z = h('div', {className: 'erp-depot', tabindex: '0', role: 'button'},
      h('b', {text: 'Déposer un BL ou une facture fournisseur'}),
      h('span', {text: 'PDF ou photo — glisser ici ou cliquer. L\'IA le lit et retrouve la commande.'}));
    z.addEventListener('click', function () { choisirFichiers(pieceId, apres); });
    z.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choisirFichiers(pieceId, apres); } });
    z.addEventListener('dragover', function (e) { e.preventDefault(); z.classList.add('survol'); });
    z.addEventListener('dragleave', function () { z.classList.remove('survol'); });
    z.addEventListener('drop', function (e) {
      e.preventDefault(); z.classList.remove('survol');
      var f = Array.prototype.slice.call(e.dataTransfer.files || []);
      if (f.length) deposerEtLire(f, pieceId, apres).catch(function (x) { ERP.toast(x.message, 'danger'); });
    });
    return z;
  }

  // ── Fiche d'un document (fenêtre) ────────────────────────────────
  async function ouvrir(id, apres, commandeId) {
    var D = await ERP.api('/api/erp2/documents/' + id + (commandeId ? '?commande_id=' + commandeId : ''));
    var ex = D.extraction || {};
    var R = D.rapprochement;
    var corps = h('div', {className: 'erp-doc'});
    var lien = h('a', {href: '/api/erp2/documents/' + id + '/fichier', text: D.nom_fichier, target: '_blank', rel: 'noopener'});
    corps.appendChild(h('div', {className: 'erp-doc-tete'},
      h('div', null, h('div', {className: 'erp-muet', text: 'Fichier'}), lien),
      h('div', null, h('div', {className: 'erp-muet', text: 'Nature lue'}), h('b', {text: NATURES[D.nature] || '—'})),
      h('div', null, h('div', {className: 'erp-muet', text: 'N° et date'}), h('b', {text: (ex.numero || '—') + (ex.date ? ' du ' + ERP.fmt.date(ex.date) : '')})),
      h('div', null, h('div', {className: 'erp-muet', text: 'Fournisseur lu'}), h('b', {text: (ex.fournisseur || {}).nom || '—'})),
      h('div', null, h('div', {className: 'erp-muet', text: 'Notre commande citée'}), h('b', {text: ex.ref_commande || '—'}))));
    if (D.statut === 'erreur') corps.appendChild(h('p', {className: 'erp-aide neg', text: D.erreur || 'Lecture en échec.'}));
    if (!D.extraction) {
      return ERP.modal('Document ' + D.nom_fichier, corps, [
        {libelle: 'Fermer'},
        {libelle: 'Lire avec l\'IA', accent: true, action: async function () {
          await ERP.api('/api/erp2/documents/' + id + '/analyser', {method: 'POST'});
          if (apres) apres();
          setTimeout(function () { ouvrir(id, apres); }, 50);
        }}]);
    }
    var fen = null;
    var C = {tiers_id: D.tiers_id, commande_id: R && R.commande ? R.commande.id : null};
    var fourn = await ERP.api('/api/erp2/tiers?role=fournisseur');
    var form = h('div', {className: 'erp-form'},
      ERP.champ('Fournisseur ERP', ERP.choix(C, 'tiers_id', fourn.map(function (t) { return {v: t.id, l: t.raison_sociale + ' (' + t.code + ')'}; }),
        {avecVide: '— non reconnu', nombre: true}), {large: true}),
      ERP.champ('Commande fournisseur', ERP.choix(C, 'commande_id', (R ? R.candidates : []).map(function (c) {
        return {v: c.id, l: (c.numero || 'brouillon') + ' (' + c.statut + ')'}; }),
        {avecVide: '— aucune', nombre: true, change: function (v) { if (fen) fen.fermer(); ouvrir(id, apres, v); }}), {large: true}));
    corps.appendChild(form);
    (R ? R.alertes : []).forEach(function (a) { corps.appendChild(h('p', {className: 'erp-aide neg', text: a})); });
    if (R && R.lignes.length) {
      corps.appendChild(h('div', {className: 'erp-lignes-defil'}, h('table', {className: 'erp-lignes'},
        h('thead', null, h('tr', null, ['Document', 'Qté', 'Prix', 'Article commandé', 'Reste à recevoir', 'Prix commandé', 'Contrôle']
          .map(function (x) { return h('th', {text: x}); }))),
        h('tbody', null, R.lignes.map(function (l) {
          return h('tr', null,
            h('td', null, h('b', {text: l.reference || ''}), h('div', {text: l.designation || ''})),
            h('td', {className: 'num', text: l.quantite_doc == null ? '—' : String(l.quantite_doc).replace('.', ',') + ' ' + (l.unite_doc || '')}),
            h('td', {className: 'num', text: l.prix_doc == null ? '—' : String(l.prix_doc).replace('.', ',')}),
            h('td', {text: l.article_code || '—'}),
            h('td', {className: 'num', text: l.reste_commande_milli == null ? '—' : ERP.fmt.qte(l.reste_commande_milli) + ' ' + (l.unite || '')}),
            h('td', {className: 'num', text: l.prix_commande_cents == null ? '—' : ERP.fmt.euros(l.prix_commande_cents)}),
            h('td', null, l.ecarts.length ? h('span', {className: 'erp-pastille ton-danger', text: l.ecarts.join(' · ')})
                                          : h('span', {className: 'erp-pastille ton-ok', text: 'Conforme'})));
        })))));
    }
    if (ex.commentaire) corps.appendChild(h('p', {className: 'erp-aide', text: 'Remarque de lecture : ' + ex.commentaire}));
    var boutons = [{libelle: 'Fermer'}];
    if (D.statut !== 'traite' && R && R.commande) {
      var prep = function (cible, lib) {
        return {libelle: lib, accent: (D.nature === 'facture') === (cible === 'facture_fournisseur'), action: async function () {
          var r = await ERP.api('/api/erp2/documents/' + id + '/preparer', {method: 'POST',
            body: {cible: cible, commande_id: C.commande_id, tiers_id: C.tiers_id}});
          ERP.toast((cible === 'reception' ? 'Réception' : 'Facture fournisseur') + ' préparée en brouillon.', 'success');
          ERP.aller(ERP.cheminPiece(cible, r.id));
        }};
      };
      boutons.push(prep('reception', 'Préparer la réception'), prep('facture_fournisseur', 'Préparer la facture'));
    } else if (D.piece_id) {
      boutons.push({libelle: 'Ouvrir la pièce', accent: true, action: function () { ERP.aller(ERP.cheminPiece(D.piece_type || 'reception', D.piece_id)); }});
    }
    fen = ERP.modal('Document fournisseur', corps, boutons, {large: true});
  }
  ERP.ouvrirDocument = ouvrir;

  // ── Carte sur une pièce d'achat ──────────────────────────────────
  ERP.carteDocuments = function (P) {
    var boite = h('div');
    function charger() {
      ERP.api('/api/erp2/documents?piece_id=' + P.id).then(function (l) {
        boite.textContent = '';
        l.forEach(function (d) {
          boite.appendChild(h('div', {className: 'erp-liens-item'},
            h('a', {href: '#', text: d.nom_fichier, onclick: function (e) { e.preventDefault(); ouvrir(d.id, charger); }}),
            h('span', {className: 'erp-pastille ton-' + ((STATUTS[d.statut] || {}).ton || 'neutre'), text: (STATUTS[d.statut] || {}).libelle || d.statut})));
        });
        boite.appendChild(zoneDepot(P.id, charger));
      }).catch(function (e) { boite.textContent = ''; boite.appendChild(ERP.erreur(e)); });
    }
    charger();
    return ERP.carte('Documents fournisseur', boite);
  };

  // ── Écran Achats › Documents fournisseurs ───────────────────────
  ERP.ecrans['/achats/documents'] = function (main) {
    main.classList.add('plein');
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    var g = null;
    function charger() {
      ERP.api('/api/erp2/documents').then(function (l) {
        l.forEach(function (d) { d.nature_lib = NATURES[d.nature] || ''; d.piece = d.piece_numero || (d.piece_id ? 'brouillon' : ''); });
        if (g) { g.maj(l); return; }
        zone.textContent = '';
        g = ERP.grille(zone, {
          nom: 'achats.documents', cle: 'id', lignes: l, statuts: STATUTS,
          colonnes: [
            {cle: 'cree_le', libelle: 'Déposé le', type: 'date', largeur: 100},
            {cle: 'nom_fichier', libelle: 'Fichier', largeur: 240},
            {cle: 'statut', libelle: 'État', type: 'statut', largeur: 140},
            {cle: 'nature_lib', libelle: 'Nature', largeur: 140},
            {cle: 'tiers_nom', libelle: 'Fournisseur', largeur: 200},
            {cle: 'numero_document', libelle: 'N° document', largeur: 130},
            {cle: 'date_document', libelle: 'Date', type: 'date', largeur: 100},
            {cle: 'ref_commande_lue', libelle: 'Commande citée', largeur: 130},
            {cle: 'nb_lignes', libelle: 'Lignes', type: 'nombre', largeur: 70},
            {cle: 'piece', libelle: 'Pièce ERP', largeur: 120},
            {cle: 'cree_par', libelle: 'Déposé par', largeur: 140, masquee: true},
          ],
          ouvrir: function (d) { ouvrir(d.id, charger).catch(function (e) { ERP.toast(e.message, 'danger'); }); },
        });
      }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
    }
    main.appendChild(zoneDepot(null, charger));
    main.appendChild(zone);
    charger();
  };
})();
