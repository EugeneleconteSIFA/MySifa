/*
 * MySifa — Filtres des indicateurs d'accueil.
 *
 * Certains blocs dépendent de filtres de leur page (période et machines de
 * MyProd, machine de Maintenance…). La page les déclare à la capture
 * (window.mysifaBlocsContexte → paramètres bloc_… de l'adresse capturée) et
 * les relit à l'ouverture. Ce fichier décrit ces filtres bloc par bloc pour :
 *   - les afficher en clair sous le nom de l'indicateur (« 7 derniers jours ·
 *     Cohésio 2 ») : deux indicateurs du même bloc se distinguent ;
 *   - les afficher et les modifier dans le questionnaire, à la capture comme
 *     dans « Modifier l'indicateur ».
 *
 * Un nouveau filtre déclaré dans mysifaBlocsContexte s'ajoute ici, avec les
 * mêmes valeurs et les mêmes libellés que la page.
 *
 * Types : « periode » (raccourcis de MyProd, ou dates fixes bloc_du/bloc_au),
 * « choix » (une valeur), « multi » (plusieurs valeurs, aucune = « vide »),
 * « jour » (aujourd'hui, ou une date fixe AAAA-MM-JJ).
 * `options(api)` rend [{ v, l }] ; `defaut` est la valeur de la page quand
 * l'adresse n'en porte pas.
 */
(function () {
  "use strict";

  function liste(paires) {
    return function () {
      return Promise.resolve(paires.map(function (p) { return { v: p[0], l: p[1] }; }));
    };
  }

  // Mêmes raccourcis que _datePresets() de mysifa_prod_core.js.
  var PERIODES = [
    ["today", "Aujourd'hui"], ["yesterday", "Dernier jour travaillé"],
    ["last7", "7 derniers jours"], ["last30", "30 derniers jours"],
    ["thisMonth", "Mois en cours"], ["prevMonth", "Mois dernier"],
    ["dates", "Dates choisies"]
  ];

  function chargerScript(src, pret) {
    if (pret()) return Promise.resolve();
    return new Promise(function (ok) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = s.onerror = function () { ok(); };
      document.head.appendChild(s);
    });
  }

  var PERIODE = { cle: "bloc_periode", libelle: "Période", type: "periode", defaut: "yesterday", options: liste(PERIODES) };
  var MACHINES_PROD = {
    cle: "bloc_machine", libelle: "Machines", type: "multi", vide: "Toutes les machines",
    options: function (api) {
      return api("/api/filters").then(function (d) {
        return ((d && d.machines) || []).map(function (m) { return { v: m, l: m }; });
      });
    }
  };
  var PROD = [PERIODE, MACHINES_PROD];

  var FILTRES = {
    "prod.ensemble.sanity": PROD,
    "prod.ensemble.quantites": PROD,
    "prod.ensemble.temps": PROD,
    "prod.ensemble.par-dossier": PROD,
    "prod.ensemble.par-operateur": PROD,
    "prod.ensemble.par-machine": PROD,
    "prod.ensemble.par-jour": PROD,

    // EXPE_PIL_FILTRES (expe_pilotage_assets.py)
    "expe.pilotage.envois": [{
      cle: "bloc_filtre", libelle: "Liste", type: "choix", defaut: "a_faire",
      options: liste([["a_faire", "À traiter"], ["retard", "En retard"], ["commande", "Transport programmé"],
                      ["parti", "Partis"], ["tout", "Tout"]])
    }],

    // Boutons machine et catégorie de l'accueil Maintenance
    "maintenance.statuts": [{
      cle: "bloc_machine", libelle: "Machine", type: "choix", defaut: null,
      options: function (api) {
        return api("/api/maintenance/statuts").then(function (d) {
          return ((d && d.machines) || []).map(function (m) { return { v: m, l: m }; });
        });
      }
    }, {
      cle: "bloc_categorie", libelle: "Catégorie", type: "choix", defaut: "entretien",
      options: liste([["entretien", "Entretien"], ["remplacements", "Interventions"], ["all", "Tous"]])
    }],

    // Calendriers de MySifaCalendar (static/mysifa_calendar.js)
    "calendrier.agenda": [{
      cle: "bloc_calendriers", libelle: "Calendriers", type: "multi", vide: "Aucun calendrier",
      options: function () {
        return chargerScript("/static/mysifa_calendar.js", function () { return !!window.MySifaCalendar; })
          .then(function () {
            var defs = (window.MySifaCalendar && window.MySifaCalendar.CAL_DEFS) || [];
            return defs.map(function (c) { return { v: c.id, l: c.label }; });
          });
      }
    }],

    "planning-rh.conges": [{
      cle: "bloc_scope", libelle: "Vue", type: "choix", defaut: "atelier",
      options: liste([["atelier", "Atelier"], ["rh", "RH"]])
    }],

    // Sélecteur « Valorisation au » de MyStock (stock_page.py) : vide = du jour.
    "stock.valorisation.kpis": [{
      cle: "bloc_date", libelle: "Valorisation au", type: "jour", defaut: "",
      options: liste([])
    }],

    // Sélecteur d'état des bobines (stock_page.py)
    "stock.bobines.kpis": [{
      cle: "bloc_etat", libelle: "État", type: "choix", defaut: "stock",
      options: liste([["stock", "En stock"], ["consommee", "Consommées"], ["rebut", "Rebut"], ["tous", "Tous les états"]])
    }]
  };

  /* Options chargées une fois par session de page : la machine de Cohésio 2
     ne change pas de nom d'une minute à l'autre. */
  var cache = {};
  function preparer(nom, api) {
    var defs = FILTRES[nom];
    if (!defs) return Promise.resolve([]);
    return Promise.all(defs.map(function (f) {
      var k = nom + "|" + f.cle;
      if (!cache[k]) cache[k] = Promise.resolve().then(function () { return f.options(api); })
        .catch(function () { delete cache[k]; return []; });
      return cache[k].then(function (opts) {
        return { cle: f.cle, libelle: f.libelle, type: f.type, defaut: f.defaut, vide: f.vide, choix: opts };
      });
    }));
  }

  function params(url) {
    try { return new URL(url, location.origin).searchParams; } catch (e) { return new URLSearchParams(); }
  }

  /* État courant des filtres d'une adresse : { bloc_periode: "last7",
     bloc_du: …, bloc_au: …, bloc_machine: [..] }. Sans valeur, le défaut. */
  function lire(defs, url) {
    var p = params(url), etat = {};
    defs.forEach(function (f) {
      if (f.type === "multi") {
        etat[f.cle] = p.getAll(f.cle).filter(Boolean);
      } else {
        var v = p.get(f.cle);
        if (!v && f.defaut === null && f.choix && f.choix.length) v = f.choix[0].v;
        etat[f.cle] = v || f.defaut || "";
      }
      if (f.type === "periode") {
        etat.bloc_du = p.get("bloc_du") || "";
        etat.bloc_au = p.get("bloc_au") || "";
      }
    });
    return etat;
  }

  /* Adresse capturée, filtres remplacés par `etat`. */
  function ecrire(defs, url, etat) {
    var u;
    try { u = new URL(url, location.origin); } catch (e) { return url; }
    defs.forEach(function (f) {
      u.searchParams.delete(f.cle);
      if (f.type === "periode") { u.searchParams.delete("bloc_du"); u.searchParams.delete("bloc_au"); }
      var v = etat[f.cle];
      if (f.type === "multi") {
        (v || []).forEach(function (x) { u.searchParams.append(f.cle, x); });
      } else if (v) {
        u.searchParams.set(f.cle, v);
        if (f.type === "periode" && v === "dates") {
          if (etat.bloc_du) u.searchParams.set("bloc_du", etat.bloc_du);
          if (etat.bloc_au) u.searchParams.set("bloc_au", etat.bloc_au);
        }
      }
    });
    return u.pathname + u.search + u.hash;
  }

  function jjmm(iso) {
    var m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? m[3] + "/" + m[2] : String(iso || "");
  }

  /* Résumé en clair : « 7 derniers jours · Cohésio 2 ». Un filtre multiple
     vide n'apparaît pas (c'est « tout ») ; une période glissante reste écrite
     comme telle, jamais en dates. */
  function decrire(defs, etat) {
    var morceaux = [];
    defs.forEach(function (f) {
      var lib = function (v) {
        var o = (f.choix || []).filter(function (x) { return x.v === v; })[0];
        return o ? o.l : v;
      };
      var v = etat[f.cle];
      if (f.type === "multi") {
        if (v && v.length) morceaux.push(v.map(lib).join(", "));
      } else if (f.type === "jour") {
        morceaux.push(v ? "au " + jjmm(v) + "/" + String(v).slice(0, 4) : "Aujourd'hui");
      } else if (f.type === "periode" && v === "dates") {
        if (etat.bloc_du) morceaux.push(etat.bloc_au && etat.bloc_au !== etat.bloc_du
          ? "du " + jjmm(etat.bloc_du) + " au " + jjmm(etat.bloc_au) : "le " + jjmm(etat.bloc_du));
      } else if (v) {
        morceaux.push(lib(v));
      }
    });
    return morceaux.join(" · ");
  }

  window.MySifaBlocsFiltres = {
    existe: function (nom) { return !!FILTRES[nom]; },
    preparer: preparer,
    lire: lire,
    ecrire: ecrire,
    decrire: decrire
  };
})();
