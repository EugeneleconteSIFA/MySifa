/*
 * MySifa — Sources des widgets d'accueil.
 *
 * Un widget n'affiche que des valeurs. Plutôt que de charger toute la page du
 * bloc pour les lire (≈ 400 Ko et 50 requêtes par widget), l'accueil interroge
 * directement l'API que la page appelle déjà, et en extrait les mêmes chiffres.
 * Un bloc sans source ici retombe sur le chargement de page (mysifa_accueil.js).
 *
 * Règle d'or : une source REPREND le calcul de la page, elle n'en invente pas
 * un autre. Même API, mêmes champs, même mise en forme — sinon le widget et la
 * page donnent deux chiffres pour la même chose. Toute modification du calcul
 * dans une page doit être reportée ici (voir .claude/rules/widgets-blocs.md).
 *
 * Une source reçoit `ctx` :
 *   ctx.json(url)   GET mis en cache le temps d'un rafraîchissement (plusieurs
 *                   widgets sur la même API = un seul appel)
 *   ctx.objet       l'objet suivi (id de machine…), ou null
 *   ctx.params      URLSearchParams de l'URL capturée (période, filtres)
 * et rend { valeurs: {cle: texte}, nombres: {cle: nombre} }, ou
 * { introuvable: true } quand l'objet suivi n'existe plus.
 */
(function () {
  "use strict";

  /* ── Mises en forme, identiques à celles des pages ─────────────────── */
  // MyProd (mysifa_prod_core.js) : fN, fMin
  function fN(n) { return n ? Number(n).toLocaleString("fr-FR") : "0"; }
  function fMin(m) {
    if (!m && m !== 0) return "-";
    var hh = Math.floor(m / 60), mm = Math.round(m % 60);
    return hh > 0 ? hh + "h " + String(mm).padStart(2, "0") + "min" : mm + "min";
  }
  function iso(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function r(valeurs, nombres) { return { valeurs: valeurs, nombres: nombres || {} }; }
  // Des nombres seuls : affichés tels quels, comparés tels quels.
  function rN(v, fmt) {
    var t = {};
    Object.keys(v).forEach(function (k) { t[k] = fmt ? fmt(v[k]) : String(v[k]); });
    return r(t, v);
  }
  // MyStock › Valorisation (stock_page.py) : valFormatEuro
  function fEuro(n) {
    return Number(n || 0).toLocaleString("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + " €";
  }
  // ERP (erp_page.py) : fmtNb(n, 0) et tdbEurTxt — au-delà du millier on abrège.
  function fNb0(n) { return Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 0 }); }
  function fNbDec(n, d) {
    return Number(n).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function fEurAbrege(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    if (!isFinite(n)) return null;
    var a = Math.abs(n);
    if (a >= 1e6) return fNbDec(n / 1e6, 2) + " M€";
    if (a >= 1000) return fNbDec(n / 1000, a < 1e5 ? 1 : 0) + " k€";
    return fNbDec(n, 0) + " €";
  }
  // Palettes Europe (expe_assets.py) : _expePalFmt
  function fPal(v) {
    var n = Number(v);
    n = isFinite(n) ? n : 0;
    return (Math.round(n * 100) / 100).toLocaleString("fr-FR");
  }

  /* ── Période de MyProd ─────────────────────────────────────────────────
     La capture enregistre le raccourci de période (bloc_periode=last7…), pas
     des dates : « 7 derniers jours » reste glissant. Mêmes bornes que
     _datePresets() de mysifa_prod_core.js ; sans raccourci, le défaut de la
     page : la dernière journée travaillée avant aujourd'hui. */
  function periodeProd(ctx) {
    var now = new Date();
    var hier = new Date(now); hier.setDate(now.getDate() - 1);
    var cle = ctx.params.get("bloc_periode") || "yesterday";
    function plage(a, b) { return Promise.resolve({ from: iso(a), to: iso(b) }); }
    if (cle === "today") return plage(now, now);
    if (cle === "last7") { var a7 = new Date(now); a7.setDate(now.getDate() - 6); return plage(a7, now); }
    if (cle === "last30") { var a30 = new Date(now); a30.setDate(now.getDate() - 29); return plage(a30, now); }
    if (cle === "thisMonth") return plage(new Date(now.getFullYear(), now.getMonth(), 1), now);
    if (cle === "prevMonth") return plage(new Date(now.getFullYear(), now.getMonth() - 1, 1), new Date(now.getFullYear(), now.getMonth(), 0));
    if (cle === "dates" && ctx.params.get("bloc_du")) {
      return Promise.resolve({ from: ctx.params.get("bloc_du"), to: ctx.params.get("bloc_au") || ctx.params.get("bloc_du") });
    }
    return ctx.json("/api/production/dernier-jour-saisi?avant=" + encodeURIComponent(iso(hier)))
      .then(function (d) { var j = (d && d.jour) || iso(hier); return { from: j, to: j }; })
      .catch(function () { return { from: iso(hier), to: iso(hier) }; });
  }

  function paramsProd(ctx) {
    return periodeProd(ctx).then(function (p) {
      var q = new URLSearchParams();
      ctx.params.getAll("bloc_machine").forEach(function (m) { q.append("machine", m); });
      q.set("date_from", p.from);
      q.set("date_to", p.to);
      return q.toString();
    });
  }

  function prodDashboard(ctx) {
    return paramsProd(ctx).then(function (qs) { return ctx.json("/api/dashboard/production?" + qs); });
  }

  /* ── MyExpé › Taxe carburant : _expeCarbPct, _expeCarbAge ──────────── */
  var CARB_JOURS_ANCIEN = 45;   // EXPE_CARB_JOURS_ANCIEN
  function carbPct(v) {
    if (v == null || !isFinite(Number(v))) return "—";
    return String(Number(Number(v).toFixed(2))).replace(".", ",") + " %";
  }
  function carbAge(isoDate) {
    if (!isoDate) return null;
    var d = new Date(String(isoDate).slice(0, 10) + "T00:00:00");
    if (isNaN(d)) return null;
    return Math.floor((Date.now() - d.getTime()) / 86400000);
  }
  function carbAncien(t) { var a = carbAge(t.maj_le); return a != null && a > CARB_JOURS_ANCIEN; }

  /* ── ERP : une valeur absente reste absente ────────────────────────── */
  function erpCompte(v) {
    var res = r({}, {});
    Object.keys(v).forEach(function (k) {
      if (v[k] == null) return;
      res.valeurs[k] = fNb0(v[k]);
      res.nombres[k] = Number(v[k]);
    });
    return res;
  }
  function erpEuros(v) {
    var res = r({}, {});
    Object.keys(v).forEach(function (k) {
      var t = fEurAbrege(v[k]);
      if (t == null) return;
      res.valeurs[k] = t;
      res.nombres[k] = Math.round(Number(v[k]));
    });
    return res;
  }

  var SOURCES = {
    /* ── MyStock › Tableau de bord ─────────────────────────────────────── */
    "stock.dashboard.reappro": function (ctx) {
      return ctx.json("/api/stock/dashboard").then(function (d) {
        var n = (d.alertes_mp || []).length;
        return r({ lignes: String(n) }, { lignes: n });
      });
    },
    "stock.dashboard.kpis": function (ctx) {
      return ctx.json("/api/stock/dashboard").then(function (d) {
        var s = d.stats || {};
        var v = {
          mp: d.nb_mp_a_approvisionner || 0,
          "a-expedier": d.nb_refs_a_expedier || 0,
          departs: d.nb_departs_aujourd_hui || 0,
          refs: s.nb_refs || 0
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = fN(v[k]); });
        return r(t, v);
      });
    },

    "stock.besoins.kpis": function (ctx) {
      return Promise.all([
        ctx.json("/api/stock/besoins-matieres/par-echeance"),
        ctx.json("/api/stock/besoins-matieres/par-dossier")
      ]).then(function (x) {
        var lignes = (x[0] && x[0].lignes) || [];
        var nonMappes = lignes.filter(function (l) { return !l.mapped; }).length;
        var v = {
          dossiers: ((x[1] && x[1].dossiers) || []).length,
          mappees: lignes.length - nonMappes,
          "a-associer": nonMappes
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── MyExpé › Départs programmés ───────────────────────────────────── */
    "expe.departs.programmes": function (ctx) {
      return ctx.json("/api/expe/departs/jour").then(function (rows) {
        var n = Array.isArray(rows) ? rows.length : 0;
        return r({ lignes: String(n) }, { lignes: n });
      });
    },

    /* ── MyExpé › Pilotage (app/web/expe_pilotage_assets.py) ─────────── */
    "expe.pilotage.resume": function (ctx) {
      return ctx.json("/api/expe/pilotage").then(function (d) {
        var x = (d && d.resume) || {};
        var v = {
          retard: x.retard || 0, "a-programmer": x.a_commander || 0,
          palettes: x.palettes_a_reserver || 0, programme: x.transport_commande || 0,
          "sans-bl": x.bl_manquant || 0
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },
    "expe.pilotage.envois": function (ctx) {
      return ctx.json("/api/expe/pilotage").then(function (d) {
        // Même tri que _expePilFiltre() de la page, recherche texte exclue.
        var f = ctx.params.get("bloc_filtre") || "a_faire";
        var n = ((d && d.envois) || []).filter(function (e) {
          if (f === "tout") return true;
          if (f === "retard") return e.alerte === "retard";
          if (f === "commande") return e.jalons && e.jalons.transport && e.jalons.transport.fait && e.alerte !== "parti";
          if (f === "parti") return e.alerte === "parti";
          return e.alerte === "retard" || e.alerte === "urgent" || e.alerte === "a_commander";
        }).length;
        return r({ lignes: String(n) }, { lignes: n });
      });
    },

    /* ── Planning machine (app/web/planning_page.py) ─────────────────────
       Même calcul que majBlocDossiers() de la page. */
    "planning.dossiers": function (ctx) {
      return ctx.json("/api/planning/machines/" + encodeURIComponent(ctx.objet) + "/entries").then(function (all) {
        all = Array.isArray(all) ? all : [];
        var cours = all.filter(function (e) { return e.statut === "en_cours"; })[0];
        var att = all.filter(function (e) { return e.statut === "attente"; });
        var h = att.reduce(function (t, e) { return t + (parseFloat(e.duree_heures) || 0); }, 0);
        return r({
          "en-cours": cours ? String(cours.reference || "") : "",
          attente: String(att.length),
          charge: h.toFixed(1).replace(".", ",") + " h"
        }, { attente: att.length, charge: Math.round(h * 10) / 10 });
      });
    },

    /* ── MyStock › Matières premières : tuile d'une catégorie ────────────
       Même API et même rapprochement que buildMatieresAccueil / mpPillMatch
       (app/web/stock_page.py). L'objet est l'id de la tuile : « carton »,
       « tout », ou « frontal:<slug> » pour une sous-section des frontaux. */
    "stock.matieres.categorie": function (ctx) {
      return ctx.json("/api/stock/matieres").then(function (list) {
        list = Array.isArray(list) ? list : [];
        var id = String(ctx.objet || "");
        var PREFIXE = "frontal:";
        function slug(x) {
          return String(x || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "");
        }
        var garde;
        if (id === "tout") {
          garde = function () { return true; };
        } else if (id.indexOf(PREFIXE) === 0) {
          var sl = id.slice(PREFIXE.length), libelle = null;
          if (sl) {
            // Libellé de la sous-section : celui de sa première matière, comme mpFrontalSousSections.
            list.some(function (m) {
              var ss = (m.sous_section || "").trim();
              if (String(m.categorie || "").toLowerCase() === "frontal" && ss && slug(ss) === sl) { libelle = ss; return true; }
              return false;
            });
            if (!libelle) return { introuvable: true };
          }
          garde = function (m) {
            if (m.categorie !== "frontal") return false;
            var ss = (m.sous_section || "").trim();
            return libelle ? ss.toLowerCase() === libelle.toLowerCase() : !ss;
          };
        } else {
          garde = function (m) { return m.categorie === id; };
        }
        var items = list.filter(garde);
        var sous = items.filter(function (m) { return m.en_alerte; }).length;
        return r({ references: String(items.length), "sous-seuil": String(sous) },
                 { references: items.length, "sous-seuil": sous });
      });
    },

    /* ── MyStock › Contrôle › Monitoring stocks PF ──────────────────────
       Dernier import ERP, comme à l'ouverture de l'écran (loadMonitoring).
       Même calcul que buildMonitoringKpis : « Sans correspondance » ajoute
       aux références ERP sans correspondance les lignes MySifa sans
       correspondance (seules ces lignes sont demandées). */
    "stock.monitoring.kpis": function (ctx) {
      return ctx.json("/api/reconciliation/snapshots").then(function (snaps) {
        var snap = Array.isArray(snaps) && snaps.length ? snaps[0] : null;
        if (!snap) {
          return r({ comparees: "0", ecarts: "0", "sans-corresp": "0", negatifs: "0" },
                   { comparees: 0, ecarts: 0, "sans-corresp": 0, negatifs: 0 });
        }
        return ctx.json("/api/reconciliation/snapshots/" + snap.id + "?statut=sans_corresp_mysifa").then(function (d) {
          var v = {
            comparees: snap.nb_matched || 0,
            ecarts: snap.nb_ecarts || 0,
            "sans-corresp": (snap.nb_sans_corresp || 0) + ((d && d.lines) || []).length,
            negatifs: snap.nb_negatifs || 0
          };
          var t = {};
          Object.keys(v).forEach(function (k) { t[k] = fN(v[k]); });
          return r(t, v);
        });
      });
    },

    /* ── MyStock › Produits finis ──────────────────────────────────────
       Les trois cartes de buildProduitsFinisTab, calculées par le serveur. */
    "stock.pf.kpis": function (ctx) {
      return ctx.json("/api/stock/produits-finis").then(function (d) {
        var k = (d && d.kpis) || {};
        return rN({
          references: Number(k.references || 0),
          mouvements: Number(k.mouvements_aujourdhui || 0),
          emplacements: Number(k.emplacements_occupes || 0)
        });
      });
    },

    /* ── MyStock › Contrôle › Valorisation ─────────────────────────────
       Même calcul que buildValorisationKpis : le montant mis en avant par
       chaque carte — « réel » (taux USD, taxe, transport, charges de
       production) pour la direction quand il diffère de la base, la base
       sinon. Toujours la valorisation du jour. */
    "stock.valorisation.kpis": function (ctx) {
      // Date figée capturée (bloc_date) : mêmes appels que la page, avec ?date=.
      var jour = ctx.params.get("bloc_date");
      var qs = jour ? "?date=" + encodeURIComponent(jour) : "";
      return Promise.all([
        ctx.json("/api/stock/valorisation" + qs),
        ctx.json("/api/stock/valorisation/pf" + qs)
      ]).then(function (x) {
        var s = (x[0] && x[0].summary) || {}, pf = (x[1] && x[1].summary) || {};
        var voitReel = !!s.can_see_usd;
        var nbFlags = Number(s.nb_refs_usd_only || 0) + Number(s.nb_refs_tax_only || 0)
          + Number(s.nb_refs_usd_and_tax || 0) + Number(s.nb_refs_transport || 0);
        var reelMP = voitReel && nbFlags > 0 && (Number(s.taux_eur_usd || 0) > 0
          || Number(s.import_tax_pct || 0) > 0 || Number(s.transport_cost_fixed_eur || 0) > 0);
        var chargesPF = voitReel && (Number(pf.charge_production_pct || 0) > 0 || Number(pf.storage_fees_pct || 0) > 0);
        var mpBase = Number(s.total_mp || 0), mpReel = Number(s.total_mp_reel || s.total_mp || 0);
        var pfBase = Number(pf.total_pf || 0), pfReel = chargesPF ? Number(pf.total_pf_avec_charges || 0) : pfBase;
        var total = (reelMP || chargesPF) ? mpReel + pfReel : mpBase + pfBase;
        var mp = reelMP ? mpReel : mpBase, pfAff = chargesPF ? pfReel : pfBase;
        var sansPrix = Number(pf.nb_refs_sans_prix || 0);
        return r(
          { total: fEuro(total), mp: fEuro(mp), pf: fEuro(pfAff), "pf-sans-prix": String(sansPrix) },
          { total: Math.round(total), mp: Math.round(mp), pf: Math.round(pfAff), "pf-sans-prix": sansPrix }
        );
      });
    },

    /* ── MyStock › Outils › Traçabilité (bobines) ──────────────────────
       Mêmes appels que loadBobines, pour l'état capturé (bloc_etat). Le
       total et le métrage portent sur tout le filtre, pas sur la page : une
       seule ligne demandée suffit. */
    "stock.bobines.kpis": function (ctx) {
      var etat = ctx.params.get("bloc_etat") || "stock";
      return Promise.all([
        ctx.json("/api/stock/bobines?etat=" + encodeURIComponent(etat) + "&limit=1"),
        ctx.json("/api/stock/bobines/coherence").catch(function () { return null; })
      ]).then(function (x) {
        var b = x[0] || {}, c = x[1];
        var m = Number(b.metrage_total || 0);
        var t = {
          bobines: String(Number(b.total || 0)),
          metrage: m.toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " m"
        };
        var n = { bobines: Number(b.total || 0), metrage: Math.round(m) };
        if (c) {
          n.ecarts = (c.ecarts || []).length;
          n["sans-matiere"] = Number(c.bobines_sans_matiere || 0);
          t.ecarts = String(n.ecarts);
          t["sans-matiere"] = String(n["sans-matiere"]);
        }
        return r(t, n);
      });
    },

    /* ── MyStock › Produits › Inventaire ───────────────────────────────
       Même décompte que buildInventaireLegende : la couleur de chaque
       emplacement vient du serveur. */
    "stock.inventaire.anciennete": function (ctx) {
      return ctx.json("/api/stock/inventaire-v2/emplacements").then(function (list) {
        list = Array.isArray(list) ? list : [];
        function n(c) { return list.filter(function (e) { return e.couleur === c; }).length; }
        return rN({
          rouge: n("rouge"), orange: n("orange"), "a-jour": n("vert") + n("jaune"),
          emplacements: list.length
        });
      });
    },

    /* ── MyExpé › Palettes Europe ──────────────────────────────────────
       Totaux et comptes transporteurs ne dépendent d'aucun filtre de
       l'écran. Le filtre « perdue » ne sert qu'à alléger la liste des
       départs, que le widget ne lit pas. */
    "expe.palettes.totaux": function (ctx) {
      return ctx.json("/api/expe/palettes-europe?statut=perdue").then(function (d) {
        var t = (d && d.totaux) || {};
        var solde = Number(t.solde_transporteurs || 0), lit = Number(t.nb_pal_contestees || 0);
        return r({
          solde: fPal(solde), envoyees: String(t.nb_pal_envoyees || 0),
          retournees: String(t.nb_pal_retournees || 0), litiges: fPal(lit)
        }, {
          solde: solde, envoyees: Number(t.nb_pal_envoyees || 0),
          retournees: Number(t.nb_pal_retournees || 0), litiges: lit
        });
      });
    },
    "expe.palettes.transporteur": function (ctx) {
      return ctx.json("/api/expe/palettes-europe?statut=perdue").then(function (d) {
        var t = ((d && d.recap_transporteurs) || []).filter(function (x) {
          return String(x.key) === String(ctx.objet);
        })[0];
        if (!t) return { introuvable: true };
        var v = {
          solde: Number(t.solde || 0), donnees: Number(t.donnees || 0),
          rendues: Number(t.rendues || 0), litiges: Number(t.nb_pal_contestees || 0)
        };
        return rN(v, fPal);
      });
    },

    /* ── MyExpé › Taxe carburant (app/web/expe_carburant_assets.py) ─────
       Mêmes règles que _expeCarbTuiles. */
    "expe.carburant.resume": function (ctx) {
      return ctx.json("/api/expe/carburant").then(function (d) {
        var list = (d && d.transporteurs) || [];
        function n(k) { return list.filter(function (t) { return t.statut === k; }).length; }
        var rens = list.filter(function (t) { return t.maj_le || t.pct; });
        var moy = rens.length ? rens.reduce(function (s, t) { return s + Number(t.pct || 0); }, 0) / rens.length : null;
        var v = {
          actifs: list.length, "a-jour": n("a_jour"), "en-attente": n("en_attente"),
          jamais: n("jamais"), anciens: list.filter(carbAncien).length
        };
        var res = rN(v);
        res.valeurs.moyen = moy == null ? "—" : carbPct(moy);
        if (moy != null) res.nombres.moyen = Number(moy.toFixed(2));
        return res;
      });
    },
    /* ── ERP RVGI › Tableaux de bord (app/web/erp_page.py) ──────────────
       Mêmes champs que htmlTdbAdv, htmlTdbDirection et htmlTdbAchats. Le
       serveur garde le calcul deux minutes (app/routers/erp.py) : le miroir
       ne change qu'à la synchro. Un bloc muet (table absente du miroir)
       laisse sa valeur vide plutôt qu'un zéro. */
    "erp.adv.kpis": function (ctx) {
      return ctx.json("/api/erp/tdb/adv").then(function (d) {
        var c = d.carnet || null;
        return erpCompte({
          commandes: c && c.commandes, semaine: c && c.semaine && c.semaine.commandes,
          retard: c && c.retard && c.retard.commandes, "a-facturer": d.a_facturer && d.a_facturer.bl,
          "sans-dossier": d.sans_dossier && d.sans_dossier.commandes
        });
      });
    },
    "erp.direction.kpis": function (ctx) {
      return ctx.json("/api/erp/tdb/direction").then(function (d) {
        return erpEuros({
          "rentre-mois": d.rentre && d.rentre.mois, facturable: d.facturable && d.facturable.montant,
          "facture-mois": d.facture && d.facture.mois, carnet: d.carnet && d.carnet.montant
        });
      });
    },
    "erp.direction.hier": function (ctx) {
      return ctx.json("/api/erp/tdb/direction").then(function (d) {
        var h = d.hier || {};
        var res = erpEuros({ montant: h.date ? h.montant : null });
        if (h.date && h.commandes != null) {
          res.valeurs.commandes = fNb0(h.commandes);
          res.nombres.commandes = Number(h.commandes);
        }
        if (h.date && h.moyenne_30j && h.montant != null) {
          var e = Math.round((h.montant / h.moyenne_30j - 1) * 100);
          res.valeurs.ecart = (e >= 0 ? "+" : "") + e + " %";
          res.nombres.ecart = e;
        }
        return res;
      });
    },
    "erp.achats.kpis": function (ctx) {
      return ctx.json("/api/erp/tdb/achats").then(function (d) {
        var o = d.ouvertes || null;
        return erpCompte({
          ouvertes: o && o.commandes, semaine: o && o.semaine && o.semaine.commandes,
          retard: o && o.retard && o.retard.commandes, receptions: d.receptions && d.receptions.lignes
        });
      });
    },

    /* ── Maintenance (app/web/maintenance_page.py) ─────────────────────
       Le calcul des statuts vit côté serveur (app/services/maintenance_statuts.py),
       traduction exacte de celui de la page. Sans machine ni catégorie
       capturées (widget antérieur), le serveur prend ses défauts. */
    "maintenance.statuts": function (ctx) {
      var q = new URLSearchParams();
      if (ctx.params.get("bloc_machine")) q.set("machine", ctx.params.get("bloc_machine"));
      if (ctx.params.get("bloc_categorie")) q.set("categorie", ctx.params.get("bloc_categorie"));
      return ctx.json("/api/maintenance/statuts?" + q.toString()).then(function (d) {
        var v = d.valeurs || {};
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      }, function (e) {
        // Machine supprimée ou désactivée : l'indicateur suit son objet.
        if (e && e.status === 404) return { introuvable: true };
        throw e;
      });
    },

    /* ── Gestionnaire de tâches (app/web/taches_page.py) ─────────────── */
    "taches.compteurs": function (ctx) {
      return Promise.all([
        ctx.json("/api/taches/badge").catch(function () { return {}; }),
        ctx.json("/api/taches/stats").catch(function () { return {}; })
      ]).then(function (x) {
        var b = x[0] || {}, st = x[1] || {};
        var v = {
          "mes-taches": Number(b.count || 0), "mes-retards": Number(b.en_retard || 0),
          "en-retard": Number(st.en_retard || 0), "non-assignees": Number(st.non_assignees || 0)
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── MyQualité › Non-conformités (app/web/qualite_page.py) ────────── */
    "qualite.nc.statuts": function (ctx) {
      return Promise.all([
        ctx.json("/api/qualite/nc"),
        ctx.json("/api/qualite/badges").catch(function () { return {}; })
      ]).then(function (x) {
        var ncs = Array.isArray(x[0]) ? x[0] : [];
        function n(st) { return ncs.filter(function (c) { return c.statut === st; }).length; }
        var v = {
          ouvertes: ncs.length - n("cloturee"), "en-analyse": n("en_analyse"),
          "action-corrective": n("action_corrective"), "en-verification": n("en_verification"),
          "non-lues": Number((x[1] || {}).nc_unread || 0)
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── Coffre RH › Notes de frais (app/web/rh_coffre_page.py) ──────── */
    "rh-coffre.ndf": function (ctx) {
      return ctx.json("/api/rh-coffre/ndf?statut=soumise").then(function (d) {
        var notes = (d && d.notes) || [];
        var tot = notes.reduce(function (t, n) { return t + (Number(n.montant_ttc) || 0); }, 0);
        return r({
          "a-valider": String(notes.length),
          montant: tot.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"
        }, { "a-valider": notes.length, montant: Math.round(tot * 100) / 100 });
      });
    },

    /* ── Messagerie (app/web/messages_page.py) ─────────────────────────── */
    "messages.non-lus": function (ctx) {
      return ctx.json("/api/chat/channels").then(function (ch) {
        ch = Array.isArray(ch) ? ch : [];
        function nl(l) { return l.reduce(function (t, c) { return t + (Number(c.unread_count) || 0); }, 0); }
        var v = {
          "non-lus": nl(ch),
          directs: nl(ch.filter(function (c) { return c.type === "direct"; })),
          mentions: ch.filter(function (c) { return Number(c.mention_count) > 0; }).length
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── MyBAT (app/web/bat_page.py) ───────────────────────────────────── */
    "bat.statuts": function (ctx) {
      return ctx.json("/api/bat").then(function (rows) {
        rows = Array.isArray(rows) ? rows : [];
        function n(st) { return rows.filter(function (e) { return e.statut === st; }).length; }
        var v = { "a-faire": n("a_faire"), "en-attente": n("en_attente"), valides: n("valide") };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── MyAO (app/web/ao_page.py) ─────────────────────────────────────── */
    "ao.appels": function (ctx) {
      return ctx.json("/api/ao").then(function (all) {
        all = Array.isArray(all) ? all : [];
        var env = all.filter(function (a) { return a.statut === "envoyee"; });
        var v = {
          envoyees: env.length,
          brouillons: all.filter(function (a) { return a.statut === "brouillon"; }).length,
          reponses: env.reduce(function (t, a) { return t + (Number(a.nb_reponses) || 0); }, 0)
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── Calendrier (app/web/calendrier_page.py) ─────────────────────────
       Même comptage que majBlocAgenda() : un événement compte pour chaque
       jour qu'il couvre. Le filtre « par collègue » de la page n'est pas
       repris : tous les événements des calendriers capturés comptent. */
    "calendrier.agenda": function (ctx) {
      var cals = ctx.params.getAll("bloc_calendriers");
      var auj = new Date(), dem = new Date(); dem.setDate(auj.getDate() + 1);
      var j0 = iso(auj), j1 = iso(dem);
      if (!cals.length) return r({ aujourdhui: "0", demain: "0" }, { aujourdhui: 0, demain: 0 });
      var q = new URLSearchParams({ date_debut: j0, date_fin: j1, calendriers: cals.join(",") });
      return ctx.json("/api/calendrier/events?" + q.toString()).then(function (res) {
        var evs = Array.isArray(res) ? res : ((res && res.events) || []);
        function compte(j) {
          return evs.filter(function (ev) {
            var a = String(ev.debut || "").slice(0, 10), b = String(ev.fin || ev.debut || "").slice(0, 10);
            return a <= j && b >= j;
          }).length;
        }
        var v = { aujourdhui: compte(j0), demain: compte(j1) };
        return r({ aujourdhui: String(v.aujourdhui), demain: String(v.demain) }, v);
      });
    },

    /* ── Planning RH › Congés (app/web/planning_rh_page.py) ──────────── */
    "planning-rh.conges": function (ctx) {
      var scope = ctx.params.get("bloc_scope") === "rh" ? "rh" : "atelier";
      return ctx.json("/api/rh/conges" + (scope === "rh" ? "?scope=rh" : "")).then(function (d) {
        var cs = (d && d.conges) || [];
        var auj = iso(new Date());
        var v = {
          absents: cs.filter(function (c) { return c.statut !== "refuse" && c.date_debut <= auj && c.date_fin >= auj; }).length,
          "a-valider": cs.filter(function (c) { return c.statut === "pose"; }).length
        };
        return r({ absents: String(v.absents), "a-valider": String(v["a-valider"]) }, v);
      });
    },

    /* ── MyCompta › Outil RH (app/web/compta_rh_outil_assets.py) ──────────
       Mêmes règles que rhOutilEtatContrat() et rhOutilComplet() ; les listes
       suivies sont celles de RH_OUTIL_LISTES (formations, documents). */
    "compta.rh.contrats": function (ctx) {
      return Promise.all([ctx.json("/api/rh-outil/membres"), ctx.json("/api/rh-outil/services")]).then(function (x) {
        var list = (x[0] && x[0].membres) || [];
        var sv = x[1] || {};
        var sansFin = sv.contrats_sans_fin || [];
        var alerte = Number(sv.alerte_fin_contrat_jours) || 15;
        var auj = new Date(); auj.setHours(0, 0, 0, 0);
        function proche(m) {
          if (!m.contrat_type || sansFin.indexOf(m.contrat_type) !== -1 || !m.contrat_fin) return false;
          var r_ = String(m.contrat_fin).match(/^(\d{4})-(\d{2})-(\d{2})$/);
          if (!r_) return false;
          var j = Math.round((new Date(+r_[1], +r_[2] - 1, +r_[3]) - auj) / 86400000);
          return j <= alerte;
        }
        function complet(m) {
          return ["formations", "documents"].every(function (cle) {
            var it = m[cle] || [];
            return it.length > 0 && it.every(function (e) {
              return e.fait && (e.justificatifs || []).every(function (j) { return j.fait; });
            });
          });
        }
        var v = {
          "fin-proche": list.filter(proche).length,
          "a-renseigner": list.filter(function (m) { return !m.contrat_type; }).length,
          incomplets: list.filter(function (m) { return !complet(m); }).length
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },

    /* ── Accueil › Atelier maintenant ──────────────────────────────────── */
    "portail.atelier.machine": function (ctx) {
      return ctx.json("/api/portail/atelier").then(function (d) {
        var ms = (d && d.machines) || [];
        var m = ms.filter(function (x) { return String(x.id) === String(ctx.objet); })[0];
        if (!m) return ms.length ? { introuvable: true } : r({});
        var lib = { prod: "En production", planifie: "Planifié, sans saisie", libre: "Libre" };
        var pct = m.avancement_pct;
        return r(
          { etat: lib[m.etat] || String(m.etat || ""), avancement: pct == null ? "" : String(pct) },
          { avancement: pct }
        );
      });
    },

    /* ── MyProd › Production › Vue d'ensemble ──────────────────────────── */
    "prod.ensemble.machines": function (ctx) {
      return ctx.json("/api/production/machine-status").then(function (ms) {
        var n = ["C1", "C2"].filter(function (k) {
          return ms && ms[k] && (ms[k].statut_key || "eteinte") !== "eteinte";
        }).length;
        return r({ "en-marche": String(n) }, { "en-marche": n });
      });
    },
    "prod.ensemble.machine": function (ctx) {
      return ctx.json("/api/production/machine-status").then(function (ms) {
        var m = ms && ms[ctx.objet];
        if (!m) return r({ etat: "Éteinte" });
        var duree = m.duree_min;
        var dureeTxt = duree == null || duree < 0 ? "" : duree < 1 ? "à l'instant"
          : (Math.floor(duree / 60) === 0 ? (duree % 60) + " min"
            : (duree % 60 === 0 ? Math.floor(duree / 60) + "h" : Math.floor(duree / 60) + "h " + (duree % 60) + "min"));
        return r({
          etat: m.statut_label || "Éteinte",
          operateur: m.operateur || "",
          dossier: m.dossier && m.dossier.no_dossier ? String(m.dossier.no_dossier) : "",
          depuis: dureeTxt
        }, { depuis: duree });
      });
    },
    "prod.ensemble.sanity": function (ctx) {
      return paramsProd(ctx).then(function (qs) {
        return ctx.json("/api/dashboard/historique?" + qs);
      }).then(function (d) {
        var sc = (d && d.sanity && d.sanity.score) || 0;
        return r({ score: String(sc) }, { score: sc });
      });
    },
    /* ── MyProd › Erreurs & Qualité (renderHist) : même API et mêmes
       filtres que la Vue d'ensemble ; les compteurs sont ceux des cartes. */
    "prod.erreurs.score": function (ctx) {
      return paramsProd(ctx).then(function (qs) {
        return ctx.json("/api/dashboard/historique?" + qs);
      }).then(function (d) {
        var s = (d && d.sanity) || {};
        var sc = Number(s.score || 0), j = Number(s.journees || 0);
        return r({ score: String(sc), mention: String(s.mention || ""), journees: String(j) },
                 { score: sc, journees: j });
      });
    },
    "prod.erreurs.kpis": function (ctx) {
      return paramsProd(ctx).then(function (qs) {
        return ctx.json("/api/dashboard/historique?" + qs);
      }).then(function (d) {
        d = d || {};
        var c = d.severity_counts || {};
        var v = {
          operations: Number(d.total_operations || 0), critique: Number(c.critique || 0),
          attention: Number(c.attention || 0), normal: Number(c.info || 0),
          erreurs: Number(d.saisie_errors_count || 0)
        };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = fN(v[k]); });
        return r(t, v);
      });
    },
    "prod.ensemble.quantites": function (ctx) {
      return prodDashboard(ctx).then(function (d) {
        var p = d.produit || {};
        var vit = d.vitesse_m_min;
        return r({
          dossiers: fN(p.dossiers || 0),
          metrage: fN(p.metrage_m || 0) + " m",
          vitesse: (vit != null ? Number(vit).toFixed(2) : "0.00") + " m/min"
        }, { dossiers: p.dossiers || 0, metrage: p.metrage_m || 0, vitesse: vit || 0 });
      });
    },
    "prod.ensemble.temps": function (ctx) {
      return prodDashboard(ctx).then(function (d) {
        var tt = d.temps_totaux || {};
        // Comme la page : la production affichée inclut les arrêts.
        var prod = Number(tt.production_min || 0) + Number(tt.arret_min || 0);
        return r({
          calage: fMin(tt.calage_min), production: fMin(prod), arrets: fMin(tt.arret_min)
        }, {
          calage: Math.round(Number(tt.calage_min || 0)), production: Math.round(prod),
          arrets: Math.round(Number(tt.arret_min || 0))
        });
      });
    },
    "prod.of.a-traiter": function (ctx) {
      return ctx.json("/api/admin/of-link-pending/count").then(function (d) {
        var v = { total: Number(d && d.count || 0), mappings: Number(d && d.ambigus || 0), "sans-of": Number(d && d.sans_of || 0) };
        var t = {};
        Object.keys(v).forEach(function (k) { t[k] = String(v[k]); });
        return r(t, v);
      });
    },
    // prod.ensemble.par-* : regroupements calculés dans la page
    // (_prodAggBy, hors repiquage) — chargement de page en attendant.
  };

  window.MySifaBlocsSources = SOURCES;
})();
