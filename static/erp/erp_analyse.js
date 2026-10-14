/* Nouvel ERP — annuaire des contacts, statistiques et palmarès
 * (RVGI : « Contacts », « Statistiques », « Hits parades »). */
(function () {
  'use strict';
  var ERP = window.ERP, h = ERP.h;

  // ── Contacts ─────────────────────────────────────────────────────
  ERP.ecrans['/fichiers/contacts'] = function (main) {
    main.classList.add('plein');
    var zone = h('div', {className: 'erp-zone'}, ERP.chargement());
    main.appendChild(zone);
    ERP.api('/api/erp2/contacts').then(function (l) {
      var envois = {envoi_devis: 'Devis', envoi_arc: 'ARC', envoi_bl: 'BL', envoi_facture: 'Facture', envoi_relance: 'Relance'};
      l.forEach(function (c) {
        c.recoit = Object.keys(envois).filter(function (k) { return c[k]; }).map(function (k) { return envois[k]; }).join(', ');
        c.genre = c.est_client ? 'Client' : 'Fournisseur';
      });
      zone.textContent = '';
      var g = ERP.grille(zone, {
        nom: 'contacts', cle: 'id', lignes: l,
        colonnes: [
          {cle: 'tiers_nom', libelle: 'Tiers', largeur: 230},
          {cle: 'genre', libelle: 'Type', largeur: 100},
          {cle: 'service', libelle: 'Service', largeur: 130},
          {cle: 'nom', libelle: 'Nom', largeur: 200},
          {cle: 'fonction', libelle: 'Fonction', largeur: 150},
          {cle: 'telephone', libelle: 'Téléphone', largeur: 130},
          {cle: 'gsm', libelle: 'GSM', largeur: 130},
          {cle: 'email', libelle: 'Email', largeur: 240},
          {cle: 'recoit', libelle: 'Reçoit', largeur: 200},
        ],
        ouvrir: function (c) { ERP.aller((c.est_client ? '/fichiers/clients/' : '/fichiers/fournisseurs/') + c.tiers_id); },
      });
      requestAnimationFrame(function () { g.focus(); });
    }).catch(function (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); });
  };

  // ── Statistiques ─────────────────────────────────────────────────
  var VUES = [
    {cle: 'par_client', libelle: 'Par client'},
    {cle: 'par_article', libelle: 'Par article'},
    {cle: 'par_representant', libelle: 'Par représentant'},
  ];

  ERP.ecrans['/analyse/statistiques'] = function (main, ctx) {
    var j = new Date();
    var P = {debut: j.getFullYear() + '-01-01', fin: j.toISOString().slice(0, 10)};
    var vue = 'par_client';
    var barre = h('div', {className: 'erp-form erp-export-barre'},
      ERP.champ('Du', ERP.saisie(P, 'debut', 'date', {change: charger})),
      ERP.champ('Au', ERP.saisie(P, 'fin', 'date', {change: charger})));
    var resume = h('div');
    var zone = h('div');
    main.appendChild(barre);
    main.appendChild(resume);
    main.appendChild(zone);
    var donnees = null;

    function mois(m) {
      var noms = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
      return noms[parseInt(m.slice(5, 7), 10) - 1] + ' ' + m.slice(2, 4);
    }

    function histogramme(par) {
      var max = Math.max.apply(null, par.map(function (x) { return Math.abs(x.ca_cents || 0); }).concat([1]));
      return h('div', {className: 'erp-histo', role: 'img', 'aria-label': 'Chiffre d\'affaires par mois'},
        par.map(function (x) {
          var pct = Math.round(100 * Math.abs(x.ca_cents || 0) / max);
          return h('div', {className: 'erp-histo-col', title: mois(x.mois) + ' : ' + ERP.fmt.euros(x.ca_cents)},
            h('div', {className: 'erp-histo-val', text: ERP.fmt.euros(x.ca_cents).replace(/,\d\d €$/, ' €')}),
            h('div', {className: 'erp-histo-barre' + ((x.ca_cents || 0) < 0 ? ' neg' : ''), style: 'height:' + Math.max(2, pct) + '%'}),
            h('div', {className: 'erp-histo-lib', text: mois(x.mois)}));
        }));
    }

    function dessinerVue() {
      zone.textContent = '';
      zone.appendChild(h('div', {className: 'erp-onglets'}, VUES.map(function (v) {
        return h('button', {type: 'button', className: 'erp-onglet' + (v.cle === vue ? ' actif' : ''), text: v.libelle,
          onclick: function () { vue = v.cle; dessinerVue(); }});
      })));
      var l = donnees[vue];
      var total = donnees.total_cents || 0;
      l.forEach(function (x, i) { x.rang = i + 1; x.part_bp = total ? Math.round(10000 * (x.ca_cents || 0) / total) : 0; });
      var cols = [{cle: 'rang', libelle: '#', type: 'nombre', largeur: 60}];
      if (vue === 'par_client') cols.push({cle: 'code', libelle: 'Code', largeur: 90}, {cle: 'libelle', libelle: 'Client', largeur: 280},
        {cle: 'nb_factures', libelle: 'Factures', type: 'nombre', largeur: 90});
      if (vue === 'par_article') cols.push({cle: 'code', libelle: 'Article', largeur: 120}, {cle: 'libelle', libelle: 'Libellé', largeur: 300},
        {cle: 'quantite_milli', libelle: 'Quantité', type: 'qte', largeur: 130}, {cle: 'unite', libelle: 'Unité', largeur: 70});
      if (vue === 'par_representant') cols.push({cle: 'libelle', libelle: 'Représentant', largeur: 280});
      cols.push({cle: 'ca_cents', libelle: 'CA HT', type: 'montant', largeur: 140, total: true},
        {cle: 'part', libelle: 'Part', largeur: 90, rendu: function (x) { return ERP.fmt.pct(x.part_bp) || '0 %'; }});
      var g = h('div', {className: 'erp-zone erp-stats-grille'});
      zone.appendChild(g);
      ERP.grille(g, {
        nom: 'stats.' + vue, cle: vue === 'par_representant' ? 'libelle' : 'id', lignes: l, colonnes: cols,
        ouvrir: function (x) {
          if (vue === 'par_client') ERP.aller('/fichiers/clients/' + x.id);
          else if (vue === 'par_article') ERP.aller('/fichiers/articles/' + x.id);
        },
      });
    }

    async function charger() {
      zone.textContent = ''; zone.appendChild(ERP.chargement());
      try {
        donnees = await ERP.api('/api/erp2/stats?debut=' + P.debut + '&fin=' + P.fin);
        resume.textContent = '';
        resume.appendChild(h('div', {className: 'erp-tuiles'},
          h('div', {className: 'erp-tuile'}, h('div', {className: 'erp-tuile-titre', text: 'Chiffre d\'affaires HT'}),
            h('div', {className: 'erp-tuile-n', text: ERP.fmt.euros(donnees.total_cents)}),
            h('div', {className: 'erp-tuile-detail', text: 'facturé, avoirs déduits'})),
          h('div', {className: 'erp-tuile'}, h('div', {className: 'erp-tuile-titre', text: 'Clients facturés'}),
            h('div', {className: 'erp-tuile-n', text: String(donnees.par_client.length)}),
            h('div', {className: 'erp-tuile-detail', text: donnees.par_client[0] ? '1er : ' + donnees.par_client[0].libelle : ''}))));
        if (donnees.par_mois.length) resume.appendChild(ERP.carte('Par mois', histogramme(donnees.par_mois)));
        dessinerVue();
      } catch (e) { zone.textContent = ''; zone.appendChild(ERP.erreur(e)); }
    }
    charger();
  };
})();
