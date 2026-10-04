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
    }
    // prod.ensemble.par-* : regroupements calculés dans la page
    // (_prodAggBy, hors repiquage) — chargement de page en attendant.
  };

  window.MySifaBlocsSources = SOURCES;
})();
