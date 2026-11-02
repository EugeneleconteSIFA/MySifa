/*
 * MySifa — Historique des pesées par front (saisie prod, MyProd).
 *
 * Les pesées d'étiquettes se saisissent dans une alerte de maintenance, une
 * mesure par front. Ici elles se relisent en tableau : quand, qui, quel
 * dossier, la valeur de chaque front, et les autres mesures de la même
 * validation (grammage de colle…). Données : GET /api/maintenance/alertes/pesees
 * (app/services/alertes_pesees.py) — aucune question n'est nommée ici.
 *
 *   MySifaPesees.ouvrir({machine, no_dossier, jours})   ouvre la fenêtre
 *   MySifaPesees.fermer(sansAdresse)
 *   MySifaPesees.surAdresse(fn)   fn({machine, no_dossier, jours}) à chaque
 *       ouverture ou changement de filtre, fn(null) à la fermeture : la page
 *       porte la fenêtre dans son adresse (url-etat.md). Une fermeture
 *       technique (Retour du navigateur) passe sansAdresse et ne prévient pas.
 *   MySifaPesees.adresse(e) / lireAdresse(u)   e ↔ paramètres d'URL
 *       (pesees=<machine|toutes>, pesees_dossier, pesees_periode).
 *   <button data-pesees data-pesees-machine="…" data-pesees-dossier="…">
 *       ouvre aussi, sans rien brancher (écoute déléguée sur le document)
 *
 * La fenêtre vit dans son propre calque sous <body> : le re-rendu de la page
 * hôte (render() toutes les quelques secondes en saisie prod) ne la touche
 * pas. Tout texte passe par textContent.
 */
(function (global) {
  "use strict";

  var PERIODES = [["7", "7 derniers jours"], ["30", "30 derniers jours"], ["90", "90 derniers jours"], ["", "Tout l'historique"]];
  var P = { filtres: null, data: null, charge: false, erreur: "", jeton: 0, abonnes: [] };

  function signaler(e) {
    P.abonnes.forEach(function (fn) { try { fn(e); } catch (x) {} });
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function fmt(v, d) {
    if (v == null || isNaN(v)) return "—";
    return Number(v).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  // Une mesure simple garde ses décimales (7, 23,6) ; une pesée par front en
  // a toujours trois, pour distinguer deux fronts : 1,419 et 1,444 g.
  function fmtLibre(v) {
    if (v == null || isNaN(v)) return "—";
    return Number(v).toLocaleString("fr-FR", { maximumFractionDigits: 3 });
  }
  function dateCourte(iso) {
    var s = String(iso || "");
    return s.length >= 16 ? s.slice(8, 10) + "/" + s.slice(5, 7) + " " + s.slice(11, 16) : s;
  }
  function isoJour(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function hors(q, v) {
    return (q.min != null && v < q.min) || (q.max != null && v > q.max);
  }

  function calque() {
    var o = document.getElementById("pf-overlay");
    if (o) return o;
    o = el("div", "pf-overlay");
    o.id = "pf-overlay";
    o.addEventListener("click", function (e) { if (e.target === o) fermer(); });
    document.body.appendChild(o);
    return o;
  }
  function fermer(sansAdresse) {
    var o = document.getElementById("pf-overlay");
    if (!o) return;
    o.remove();
    P.jeton++;
    if (sansAdresse !== true) signaler(null);
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && document.getElementById("pf-overlay")) fermer();
  });

  async function charger() {
    var f = P.filtres, qs = [];
    if (f.machine) qs.push("machine=" + encodeURIComponent(f.machine));
    if (f.no_dossier) qs.push("no_dossier=" + encodeURIComponent(f.no_dossier));
    if (f.jours) {
      var d = new Date();
      d.setDate(d.getDate() - (parseInt(f.jours, 10) - 1));
      qs.push("du=" + isoJour(d));
    }
    var jeton = ++P.jeton;
    P.charge = true; P.erreur = "";
    signaler({ machine: f.machine, no_dossier: f.no_dossier, jours: f.jours });
    rendre();
    try {
      var r = await fetch("/api/maintenance/alertes/pesees" + (qs.length ? "?" + qs.join("&") : ""),
                          { credentials: "include", cache: "no-store" });
      if (!r.ok) throw new Error("Lecture impossible (" + r.status + ").");
      var d2 = await r.json();
      if (jeton !== P.jeton) return;
      P.data = d2;
    } catch (e) {
      if (jeton !== P.jeton) return;
      P.erreur = e.message || "Lecture impossible.";
    }
    P.charge = false;
    rendre();
  }

  function ouvrir(opts) {
    opts = opts || {};
    P.filtres = { machine: opts.machine || "", no_dossier: opts.no_dossier || "",
                  jours: opts.jours != null ? String(opts.jours) : (opts.no_dossier ? "" : "30") };
    P.data = null;
    calque();
    charger();
  }

  function filtres() {
    var f = P.filtres, barre = el("div", "pf-filtres");
    var machines = ((P.data && P.data.machines) || []).slice();
    if (f.machine && machines.indexOf(f.machine) < 0) machines.unshift(f.machine);
    var selM = el("select", "pf-champ");
    selM.appendChild(new Option("Toutes les machines", ""));
    machines.forEach(function (m) { selM.appendChild(new Option(m, m)); });
    selM.value = f.machine;
    selM.addEventListener("change", function () { f.machine = selM.value; charger(); });

    var selP = el("select", "pf-champ");
    PERIODES.forEach(function (p) { selP.appendChild(new Option(p[1], p[0])); });
    selP.value = f.jours;
    selP.addEventListener("change", function () { f.jours = selP.value; charger(); });

    var inpD = el("input", "pf-champ pf-dossier");
    inpD.type = "search";
    inpD.placeholder = "Référence dossier";
    inpD.value = f.no_dossier;
    var minuteur = 0;
    inpD.addEventListener("input", function () {
      clearTimeout(minuteur);
      minuteur = setTimeout(function () { f.no_dossier = inpD.value.trim(); charger(); }, 400);
    });
    barre.append(selM, selP, inpD);
    return barre;
  }

  function synthese(q) {
    var fr = (q.par_front || []).filter(function (x) { return x.n; });
    if (!fr.length) return null;
    var b = el("div", "pf-synthese");
    fr.forEach(function (x) {
      var c = el("div", "pf-front");
      c.appendChild(el("div", "pf-front-nom", q.libelle_point + " " + x.position));
      c.appendChild(el("div", "pf-front-val", fmt(x.moyenne, 3) + (q.unit ? " " + q.unit : "")));
      c.appendChild(el("div", "pf-front-sous", fmt(x.min, 3) + " – " + fmt(x.max, 3) + " · " + x.n + " pesée" + (x.n > 1 ? "s" : "")));
      b.appendChild(c);
    });
    return b;
  }

  function tableau(a) {
    var qs = a.questions, nbF = a.nb_fronts || 0;
    var t = el("table", "pf-table"), thead = el("thead"), tr = el("tr");
    ["Date", "Machine", "Opérateur", "Dossier"].forEach(function (h) { tr.appendChild(el("th", null, h)); });
    qs.forEach(function (q) {
      var u = q.unit ? " (" + q.unit + ")" : "";
      if (!q.multiple) { tr.appendChild(el("th", "num", q.label + u)); return; }
      for (var i = 0; i < nbF; i++) {
        var th = el("th", "num pf-col-front", q.libelle_point + " " + (i + 1));
        th.title = q.label + u;
        tr.appendChild(th);
      }
      var te = el("th", "num", "Écart");
      te.title = "Plus lourd moins plus léger, sur la même validation";
      tr.appendChild(te);
    });
    thead.appendChild(tr);
    t.appendChild(thead);
    var tb = el("tbody");
    a.lignes.forEach(function (l) {
      var r = el("tr");
      if (l.nc) r.className = "pf-nc";
      r.appendChild(el("td", "pf-date", dateCourte(l.ack_at)));
      r.appendChild(el("td", null, l.machine || "—"));
      r.appendChild(el("td", null, l.operateur || "—"));
      var td = el("td", "pf-dos", l.no_dossier || "—");
      if (l.no_dossier) {
        td.title = "Filtrer sur ce dossier";
        td.addEventListener("click", function () { P.filtres.no_dossier = l.no_dossier; P.filtres.jours = ""; charger(); });
      }
      r.appendChild(td);
      qs.forEach(function (q) {
        var v = l.valeurs[String(q.index)] || [];
        if (!q.multiple) {
          var c = el("td", "num", v.length ? v.map(fmtLibre).join(" / ") : "—");
          if (v.some(function (x) { return hors(q, x); })) c.classList.add("pf-hors");
          r.appendChild(c);
          return;
        }
        for (var i = 0; i < nbF; i++) {
          var cf = el("td", "num", v[i] != null ? fmt(v[i], 3) : "");
          if (v[i] != null && hors(q, v[i])) cf.classList.add("pf-hors");
          r.appendChild(cf);
        }
        r.appendChild(el("td", "num pf-ecart", v.length > 1 ? fmt(Math.max.apply(null, v) - Math.min.apply(null, v), 3) : ""));
      });
      tb.appendChild(r);
    });
    t.appendChild(tb);
    var w = el("div", "pf-table-wrap");
    w.appendChild(t);
    return w;
  }

  function rendre() {
    var o = document.getElementById("pf-overlay");
    if (!o) return;
    o.textContent = "";
    var m = el("div", "pf-modal");
    m.setAttribute("role", "dialog");
    m.setAttribute("aria-label", "Pesées par front");
    var tete = el("div", "pf-tete");
    tete.appendChild(el("div", "pf-titre", "Pesées par front"));
    var x = el("button", "pf-fermer", "×");
    x.type = "button";
    x.setAttribute("aria-label", "Fermer");
    x.addEventListener("click", function () { fermer(); });
    tete.appendChild(x);
    m.appendChild(tete);
    m.appendChild(filtres());
    var corps = el("div", "pf-corps");
    if (P.erreur) corps.appendChild(el("div", "pf-erreur", P.erreur));
    else if (P.charge && !P.data) corps.appendChild(el("div", "pf-vide", "Chargement…"));
    else {
      var alertes = (P.data && P.data.alertes) || [];
      if (!alertes.length) {
        corps.appendChild(el("div", "pf-vide", "Aucune alerte ne demande de pesée par front. Une question « valeur » à mesures multiples, dans Maintenance › Alertes, les fait apparaître ici."));
      }
      alertes.forEach(function (a) {
        if (alertes.length > 1) corps.appendChild(el("div", "pf-alerte", a.nom));
        if (!a.lignes.length) {
          corps.appendChild(el("div", "pf-vide", "Aucune pesée sur cette sélection."));
          return;
        }
        a.questions.filter(function (q) { return q.multiple; }).forEach(function (q) {
          var s = synthese(q);
          if (s) {
            corps.appendChild(el("div", "pf-sous-titre", "Moyenne par " + q.libelle_point.toLowerCase() + " — " + q.label));
            corps.appendChild(s);
          }
        });
        corps.appendChild(el("div", "pf-sous-titre", a.lignes.length + " validation" + (a.lignes.length > 1 ? "s" : "") + ", la plus récente en haut"));
        corps.appendChild(tableau(a));
      });
    }
    if (P.charge && P.data) corps.classList.add("pf-maj");
    m.appendChild(corps);
    o.appendChild(m);
  }

  document.addEventListener("click", function (e) {
    var b = e.target && e.target.closest && e.target.closest("[data-pesees]");
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    ouvrir({ machine: b.getAttribute("data-pesees-machine") || "",
             no_dossier: b.getAttribute("data-pesees-dossier") || "" });
  });

  // Paramètres d'adresse d'un état, et l'inverse. Défaut non écrit :
  // 30 derniers jours (tout l'historique quand un dossier est choisi).
  function adresse(e) {
    var p = { pesees: e.machine || "toutes" };
    if (e.no_dossier) p.pesees_dossier = e.no_dossier;
    var defaut = e.no_dossier ? "" : "30";
    if (e.jours !== defaut) p.pesees_periode = e.jours || "tout";
    return p;
  }
  function lireAdresse(u) {
    var v = u.get("pesees", null);
    if (!v || v.length > 80) return null;
    var dos = (u.get("pesees_dossier", "") || "").slice(0, 80);
    var per = u.get("pesees_periode", null, ["7", "30", "90", "tout"]);
    return { machine: v === "toutes" ? "" : v, no_dossier: dos,
             jours: per === "tout" ? "" : (per || (dos ? "" : "30")) };
  }

  global.MySifaPesees = {
    ouvrir: ouvrir, fermer: fermer, adresse: adresse, lireAdresse: lireAdresse,
    ouverte: function () { return !!document.getElementById("pf-overlay"); },
    surAdresse: function (fn) { if (typeof fn === "function") P.abonnes.push(fn); },
    CLES: ["pesees", "pesees_dossier", "pesees_periode"],
  };
})(window);
