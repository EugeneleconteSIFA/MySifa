/*
 * MySifa — Inspections des produits finis : pesées par front et autres
 * mesures des alertes d'inspection (saisie prod : onglet Qualité ; MyProd :
 * fenêtre et fiche dossier).
 *
 * Des boutons choisissent les champs affichés (pesée par front par défaut,
 * grammage de colle, release… en plus) : une courbe et des colonnes par
 * champ choisi.
 *
 * Les pesées d'étiquettes se saisissent dans une alerte de maintenance, une
 * mesure par front. Ici elles se relisent dossier par dossier, le plus
 * récemment pesé en haut : une courbe (moyenne des fronts, écart entre le
 * plus léger et le plus lourd) puis les dernières pesées. Une mesure loin des
 * autres du dossier est marquée « à vérifier » — le calcul est fait côté
 * serveur (app/services/alertes_pesees.py, GET /api/maintenance/alertes/pesees).
 *
 *   MySifaPesees.ouvrir({machine, no_dossier, jours})   fenêtre (MyProd)
 *   MySifaPesees.fermer(sansAdresse)
 *   MySifaPesees.vue({machine, no_dossier, jours})       élément durable à
 *       poser dans la page (onglet Qualité) : le premier appel charge, les
 *       suivants rendent le même élément, état et défilement compris.
 *   MySifaPesees.allerVue(e)   applique un état lu dans l'adresse à la vue
 *   MySifaPesees.dossier(cible, no_dossier)   le même rendu (boutons de
 *       champs, courbes, tableau, valeurs à vérifier) pour un seul dossier,
 *       posé dans `cible` : fiche dossier de MyProd. État propre à la cible.
 *   MySifaPesees.surAdresse(fn)   fn({machine, no_dossier, jours}) à chaque
 *       changement de filtre, fn(null) à la fermeture de la fenêtre : la page
 *       porte l'état dans son adresse (url-etat.md). Une fermeture technique
 *       (Retour du navigateur) passe sansAdresse et ne prévient pas.
 *   MySifaPesees.adresse(e) / lireAdresse(u)   e ↔ paramètres d'URL
 *       (pesees=<machine|toutes>, pesees_dossier, pesees_periode,
 *       pesees_champs=<id de question>,… quand ce n'est pas le défaut).
 *   <button data-pesees data-pesees-machine="…" data-pesees-dossier="…">
 *       ouvre la fenêtre, sans rien brancher (écoute déléguée sur le document)
 *
 * Fenêtre et vue vivent hors du rendu de la page hôte : le render() de la
 * saisie prod, toutes les quelques secondes, ne les reconstruit pas. Tout
 * texte passe par textContent.
 */
(function (global) {
  "use strict";

  var PERIODES = [["3", "3 derniers jours"], ["7", "7 derniers jours"], ["30", "30 derniers jours"],
                  ["90", "90 derniers jours"], ["", "Tout l'historique"]];
  var DEFAUT = "3";
  var LIGNES_VISIBLES = 5;
  var SVG = "http://www.w3.org/2000/svg";
  var P = { filtres: null, data: null, charge: false, erreur: "", jeton: 0, abonnes: [],
            mode: "modale", vueEl: null, deplies: {}, defil: 0, focus: null };

  function signaler(e) {
    P.abonnes.forEach(function (fn) { try { fn(e); } catch (x) {} });
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function sv(tag, attrs) {
    var e = document.createElementNS(SVG, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
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
  function aVerifier(l, q, i) {
    var a = (l.aberrants || {})[String(q.index)];
    return !!(a && a.indexOf(i) >= 0) || hors(q, ((l.valeurs || {})[String(q.index)] || [])[i]);
  }
  function unite(q) { return q.unit ? " " + q.unit : ""; }

  // ── Fenêtre / vue ──────────────────────────────────────────────────────
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
    signaler(etat());
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

  function normaliser(opts) {
    opts = opts || {};
    return { machine: opts.machine || "", no_dossier: opts.no_dossier || "",
             jours: opts.jours != null ? String(opts.jours) : (opts.no_dossier ? "" : DEFAUT),
             champs: opts.champs && opts.champs.length ? opts.champs.slice() : null };
  }
  function etat() {
    var f = P.filtres;
    return f ? { machine: f.machine, no_dossier: f.no_dossier, jours: f.jours, champs: f.champs } : null;
  }
  function memesChamps(a, b) { return (a || []).join(",") === (b || []).join(","); }

  // ── Champs affichés ────────────────────────────────────────────────────
  function cleQ(q) { return q.id || String(q.index); }
  function champsDefaut(qs) {
    return qs.filter(function (q) { return q.multiple; }).map(cleQ);
  }
  // Questions choisies, dans l'ordre du questionnaire. Un choix qui ne
  // correspond à aucune question de l'alerte retombe sur le défaut.
  // X : contexte d'affichage — {etat: {champs}, deplies, redessiner(),
  // champsChanges(), titreClic(g) | null}. PRINCIPAL pour la fenêtre et
  // l'onglet ; un contexte par fiche dossier (dossier()).
  var PRINCIPAL = {
    get etat() { return P.filtres; },
    get deplies() { return P.deplies; },
    redessiner: function () { rendre(); },
    champsChanges: function () { signaler(etat()); },
    titreClic: function (g) { P.filtres.no_dossier = g.no_dossier; P.filtres.jours = ""; P.defil = 0; charger(); },
  };
  function choisies(qs, X) {
    var voulu = (X || PRINCIPAL).etat.champs || champsDefaut(qs);
    var r = qs.filter(function (q) { return voulu.indexOf(cleQ(q)) >= 0; });
    return r.length ? r : qs.filter(function (q) { return q.multiple; });
  }
  function boutonsChamps(qs, X) {
    var actifs = choisies(qs, X).map(cleQ);
    var barre = el("div", "pf-champs");
    barre.setAttribute("role", "group");
    barre.setAttribute("aria-label", "Champs affichés");
    qs.forEach(function (q) {
      var on = actifs.indexOf(cleQ(q)) >= 0;
      var b = el("button", "pf-champ-btn" + (on ? " actif" : ""), q.label + (q.unit ? " (" + q.unit + ")" : ""));
      b.type = "button";
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.addEventListener("click", function () {
        var n = on ? actifs.filter(function (k) { return k !== cleQ(q); }) : actifs.concat([cleQ(q)]);
        if (!n.length) return;  // au moins un champ affiché
        n = qs.map(cleQ).filter(function (k) { return n.indexOf(k) >= 0; });
        X.etat.champs = memesChamps(n, champsDefaut(qs)) ? null : n;
        X.champsChanges();
        X.redessiner();
      });
      barre.appendChild(b);
    });
    return barre;
  }
  function ouvrir(opts) {
    P.mode = "modale";
    P.defil = 0;
    P.filtres = normaliser(opts);
    P.data = null;
    calque();
    charger();
  }
  function vue(opts) {
    P.mode = "vue";
    if (!P.vueEl) {
      P.vueEl = el("div", "pf-vue");
      P.filtres = normaliser(opts);
      P.data = null;
      charger();
    }
    return P.vueEl;
  }
  function allerVue(e) {
    var f = normaliser(e), g = P.filtres;
    vue(e);
    if (g && f.machine === g.machine && f.no_dossier === g.no_dossier && f.jours === g.jours) {
      if (!memesChamps(f.champs, g.champs)) { g.champs = f.champs; rendre(); }
      return;
    }
    P.filtres = f;
    charger();
  }

  // ── Filtres ────────────────────────────────────────────────────────────
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
    inpD.id = "pf-dossier";
    inpD.placeholder = "Référence dossier";
    inpD.value = f.no_dossier;
    var minuteur = 0;
    inpD.addEventListener("input", function () {
      clearTimeout(minuteur);
      minuteur = setTimeout(function () { f.no_dossier = inpD.value.trim(); charger(); }, 400);
    });
    // Suivi du focus et du curseur : la page hôte peut sortir la vue du
    // document à tout moment (render() de la saisie prod), retablir() les rend.
    function noter() { P.focus = [inpD.selectionStart, inpD.selectionEnd]; }
    ["focus", "input", "keyup", "select", "click"].forEach(function (t) { inpD.addEventListener(t, noter); });
    inpD.addEventListener("blur", function () {
      setTimeout(function () { if (inpD.isConnected) P.focus = null; }, 0);
    });
    inpD.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && inpD.value) {
        e.stopPropagation();
        inpD.value = "";
        f.no_dossier = "";
        if (!f.jours) f.jours = DEFAUT;
        charger();
      }
    });
    barre.append(selM, selP, inpD);
    return barre;
  }

  // ── Courbe d'un dossier ────────────────────────────────────────────────
  // Abscisse : les pesées dans l'ordre, la plus ancienne à gauche. Ordonnée :
  // bornée par les mesures normales ; une mesure à vérifier hors de cette
  // échelle est posée au bord, flèche vers l'extérieur, pour ne pas écraser
  // la courbe (4,266 g au milieu de pesées à 1,4 g).
  // Une seule pesée : pas de courbe, le tableau suffit.
  function courbe(g, q, largeur) {
    var k = String(q.index);
    var lignes = g.lignes.slice().reverse().filter(function (l) { return (l.valeurs[k] || []).length; });
    if (lignes.length < 2) return null;
    var normales = [], toutes = [];
    lignes.forEach(function (l) {
      (l.valeurs[k] || []).forEach(function (v, i) {
        toutes.push(v);
        if (!aVerifier(l, q, i)) normales.push(v);
      });
    });
    var base = normales.length ? normales : toutes;
    var lo = Math.min.apply(null, base), hi = Math.max.apply(null, base);
    // Pesée par front : trois décimales ; grammage, release : selon l'écart.
    var dec = q.multiple ? 3 : (hi - lo < 1 ? 2 : 1);
    var marge = (hi - lo) * 0.15 || Math.abs(hi) * 0.05 || 1;
    lo -= marge; hi += marge;

    // Largeur réelle de la page : le texte du graphique garde sa taille.
    var W = Math.max(300, Math.round(largeur || 640)), H = 150, G = 52, D = 14, T = 12, B = 26;
    var larg = W - G - D, haut = H - T - B, n = lignes.length;
    function x(i) { return n === 1 ? G + larg / 2 : G + i * larg / (n - 1); }
    function y(v) { return T + (hi - v) / (hi - lo) * haut; }

    var wrap = el("div", "pf-courbe");
    var s = sv("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, role: "img",
                        "aria-label": q.label + " — " + n + " pesée" + (n > 1 ? "s" : "") });
    [lo + marge, (lo + hi) / 2, hi - marge].forEach(function (v) {
      s.appendChild(sv("line", { x1: G, x2: W - D, y1: y(v), y2: y(v), class: "pf-grille" }));
      var t = sv("text", { x: G - 6, y: y(v) + 4, "text-anchor": "end", class: "pf-axe" });
      t.textContent = fmt(v, dec);
      s.appendChild(t);
    });
    [[0, "start"], [n - 1, "end"]].forEach(function (p, j) {
      if (j && n === 1) return;
      var t = sv("text", { x: n === 1 ? x(0) : x(p[0]), y: H - 6,
                           "text-anchor": n === 1 ? "middle" : p[1], class: "pf-axe" });
      t.textContent = dateCourte(lignes[p[0]].ack_at);
      s.appendChild(t);
    });

    var moyennes = [];
    lignes.forEach(function (l, i) {
      var v = l.valeurs[k] || [], ok = v.filter(function (_, j) { return !aVerifier(l, q, j); });
      if (ok.length > 1) {
        s.appendChild(sv("line", { x1: x(i), x2: x(i), y1: y(Math.max.apply(null, ok)), y2: y(Math.min.apply(null, ok)),
                                   class: "pf-plage" }));
      }
      moyennes.push(ok.length ? ok.reduce(function (a, b) { return a + b; }, 0) / ok.length : null);
    });
    var d = "";
    moyennes.forEach(function (m, i) {
      if (m == null) return;
      d += (d ? " L" : "M") + x(i).toFixed(1) + " " + y(m).toFixed(1);
    });
    if (d) s.appendChild(sv("path", { d: d, class: "pf-moyenne" }));
    moyennes.forEach(function (m, i) {
      if (m != null) s.appendChild(sv("circle", { cx: x(i), cy: y(m), r: 4, class: "pf-point" }));
    });
    lignes.forEach(function (l, i) {
      (l.valeurs[k] || []).forEach(function (v, j) {
        if (!aVerifier(l, q, j)) return;
        var yy = y(v), dehors = yy < T ? -1 : (yy > T + haut ? 1 : 0);
        yy = Math.max(T, Math.min(T + haut, yy));
        if (dehors) {
          var p = dehors < 0 ? [x(i) - 5, yy + 1, x(i) + 5, yy + 1, x(i), yy - 7] : [x(i) - 5, yy - 1, x(i) + 5, yy - 1, x(i), yy + 7];
          s.appendChild(sv("polygon", { points: p.join(" "), class: "pf-alerte-point" }));
        } else {
          s.appendChild(sv("circle", { cx: x(i), cy: yy, r: 5, class: "pf-alerte-point" }));
        }
      });
    });

    // Survol : une colonne par pesée, plus large que la marque.
    var bulle = el("div", "pf-bulle");
    bulle.hidden = true;
    var pas = n === 1 ? larg : larg / (n - 1);
    lignes.forEach(function (l, i) {
      var cible = sv("rect", { x: x(i) - pas / 2, y: 0, width: pas, height: H, class: "pf-cible" });
      cible.addEventListener("mouseenter", function () {
        bulle.textContent = "";
        bulle.appendChild(el("div", "pf-bulle-titre", dateCourte(l.ack_at) + " · " + (l.operateur || "—")));
        (l.valeurs[k] || []).forEach(function (v, j) {
          var r = el("div", aVerifier(l, q, j) ? "pf-bulle-ligne pf-hors" : "pf-bulle-ligne",
                     (q.multiple ? q.libelle_point + " " + (j + 1) : q.label) + " : " + (q.multiple ? fmt(v, 3) : fmtLibre(v)) + unite(q)
                     + (aVerifier(l, q, j) ? " · à vérifier" : ""));
          bulle.appendChild(r);
        });
        bulle.hidden = false;
        bulle.style.left = (x(i) / W * 100) + "%";
        bulle.classList.toggle("pf-bulle-gauche", x(i) > W * 0.6);
      });
      cible.addEventListener("mouseleave", function () { bulle.hidden = true; });
      s.appendChild(cible);
    });
    var titre = el("div", "pf-courbe-titre");
    titre.appendChild(el("b", null, q.label + (q.unit ? " (" + q.unit + ")" : "")));
    if (q.multiple) {
      titre.appendChild(el("span", null, " · trait : moyenne des " + q.libelle_point.toLowerCase()
        + "s · barre : du plus léger au plus lourd · rouge : à vérifier"));
    }
    wrap.append(titre, s, bulle);
    return wrap;
  }

  // ── Tableau d'un dossier ───────────────────────────────────────────────
  function tableau(g, qs, nbF, cle, X) {
    var t = el("table", "pf-table"), thead = el("thead"), tr = el("tr");
    ["Date", "Opérateur"].forEach(function (h) { tr.appendChild(el("th", null, h)); });
    qs.forEach(function (q) {
      if (!q.multiple) { tr.appendChild(el("th", "num", q.label + (q.unit ? " (" + q.unit + ")" : ""))); return; }
      for (var i = 0; i < nbF; i++) tr.appendChild(el("th", "num", q.libelle_point + " " + (i + 1)));
    });
    thead.appendChild(tr);
    t.appendChild(thead);
    var tb = el("tbody"), toutes = !!X.deplies[cle];
    var lignes = toutes ? g.lignes : g.lignes.slice(0, LIGNES_VISIBLES);
    lignes.forEach(function (l) {
      var r = el("tr");
      if (l.nc) r.className = "pf-nc";
      r.appendChild(el("td", "pf-date", dateCourte(l.ack_at)));
      r.appendChild(el("td", null, l.operateur || "—"));
      qs.forEach(function (q) {
        var v = l.valeurs[String(q.index)] || [], med = (g.medianes || {})[String(q.index)];
        var cols = q.multiple ? nbF : 1;
        for (var i = 0; i < cols; i++) {
          var txt = q.multiple ? (v[i] != null ? fmt(v[i], 3) : "") : (v.length ? v.map(fmtLibre).join(" / ") : "—");
          var c = el("td", "num", txt);
          var douteux = q.multiple ? (v[i] != null && aVerifier(l, q, i))
                                   : v.some(function (_, j) { return aVerifier(l, q, j); });
          if (douteux) {
            c.classList.add("pf-hors");
            c.title = "À vérifier" + (med != null ? " — médiane du dossier : " + fmt(med, q.multiple ? 3 : 1) + unite(q) : "");
          }
          r.appendChild(c);
        }
      });
      tb.appendChild(r);
    });
    t.appendChild(tb);
    var w = el("div", "pf-table-wrap");
    w.appendChild(t);
    if (g.lignes.length > LIGNES_VISIBLES) {
      var plus = el("button", "pf-plus", toutes ? "Afficher les " + LIGNES_VISIBLES + " dernières"
                                                : "Afficher les " + g.lignes.length + " pesées");
      plus.type = "button";
      plus.addEventListener("click", function () { X.deplies[cle] = !toutes; X.redessiner(); });
      w.appendChild(plus);
    }
    return w;
  }

  function section(a, g, largeur, X) {
    X = X || PRINCIPAL;
    var qs = choisies(a.questions, X), qm = qs.filter(function (q) { return q.multiple; });
    var cle = a.id + "|" + g.no_dossier;
    var nbF = 0;
    g.lignes.forEach(function (l) {
      qm.forEach(function (q) { nbF = Math.max(nbF, (l.valeurs[String(q.index)] || []).length); });
    });
    var s = el("section", "pf-section");
    var tete = el("div", "pf-section-tete");
    var lien = !!(g.no_dossier && X.titreClic);
    var titre = el(lien ? "button" : "span", "pf-section-titre", g.no_dossier || "Sans dossier");
    if (lien) {
      titre.type = "button";
      titre.title = "Tout l'historique de ce dossier";
      titre.addEventListener("click", function () { X.titreClic(g); });
    }
    tete.appendChild(titre);
    var n = g.lignes.length, der = g.lignes[0], prem = g.lignes[n - 1];
    tete.appendChild(el("span", "pf-section-sous",
      (g.machines || []).join(", ") + (g.machines && g.machines.length ? " · " : "") +
      n + " pesée" + (n > 1 ? "s" : "") + " · " +
      (n > 1 ? dateCourte(prem.ack_at) + " → " + dateCourte(der.ack_at) : dateCourte(der.ack_at))));
    if (g.nb_aberrants) {
      tete.appendChild(el("span", "pf-badge-alerte",
        g.nb_aberrants + " valeur" + (g.nb_aberrants > 1 ? "s" : "") + " à vérifier"));
    }
    s.appendChild(tete);
    qs.forEach(function (q) {
      var c = courbe(g, q, largeur);
      if (c) s.appendChild(c);
    });
    s.appendChild(tableau(g, qs, nbF, cle, X));
    return s;
  }

  function contenu(corps, largeur) {
    var alertes = (P.data && P.data.alertes) || [];
    if (!alertes.length) {
      corps.appendChild(el("div", "pf-vide", "Aucune alerte ne demande de pesée par front. Une question « valeur » à mesures multiples, dans Maintenance › Alertes, les fait apparaître ici."));
      return;
    }
    var periode = (PERIODES.filter(function (p) { return p[0] === P.filtres.jours; })[0] || [0, ""])[1].toLowerCase();
    alertes.forEach(function (a) {
      if (alertes.length > 1) corps.appendChild(el("div", "pf-alerte", a.nom));
      var gs = a.dossiers || [];
      if (!gs.length) {
        corps.appendChild(el("div", "pf-vide", P.filtres.no_dossier
          ? "Aucune pesée pour « " + P.filtres.no_dossier + " »" + (P.filtres.jours ? " sur les " + periode + "." : ".")
          : "Aucune pesée sur les " + periode + "."));
        return;
      }
      corps.appendChild(boutonsChamps(a.questions, PRINCIPAL));
      gs.forEach(function (g) { corps.appendChild(section(a, g, largeur)); });
    });
  }

  function rendre() {
    var racine = P.mode === "vue" ? P.vueEl : document.getElementById("pf-overlay");
    if (!racine) return;
    // Largeur utile d'une section (bords et marges ôtés), mesurée avant de vider.
    var mesure = racine.querySelector(".pf-corps");
    if (mesure && mesure.clientWidth) {
      var cs = getComputedStyle(mesure);
      P.largeur = mesure.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    }
    else if (P.mode === "vue" && racine.clientWidth) P.largeur = racine.clientWidth;
    else if (P.mode !== "vue") P.largeur = Math.min(1100, window.innerWidth - 32) - 36;
    racine.textContent = "";
    var m = racine;
    if (P.mode !== "vue") {
      m = el("div", "pf-modal");
      m.setAttribute("role", "dialog");
      m.setAttribute("aria-label", "Inspections des produits finis");
      var tete = el("div", "pf-tete");
      tete.appendChild(el("div", "pf-titre", "Inspections des produits finis"));
      var x = el("button", "pf-fermer", "×");
      x.type = "button";
      x.setAttribute("aria-label", "Fermer");
      x.addEventListener("click", function () { fermer(); });
      tete.appendChild(x);
      m.appendChild(tete);
    }
    m.appendChild(filtres());
    var corps = el("div", "pf-corps");
    if (P.erreur) corps.appendChild(el("div", "pf-erreur", P.erreur));
    else if (P.charge && !P.data) corps.appendChild(el("div", "pf-vide", "Chargement…"));
    else contenu(corps, (P.largeur || 640) - 30);
    if (P.charge && P.data) corps.classList.add("pf-maj");
    m.appendChild(corps);
    if (m !== racine) racine.appendChild(m);
    corps.addEventListener("scroll", function () { P.defil = corps.scrollTop; });
    retablir();
  }

  // Défilement de la liste et focus du champ dossier, après une reconstruction
  // ou une remise de la vue dans la page.
  function retablir() {
    var racine = P.mode === "vue" ? P.vueEl : document.getElementById("pf-overlay");
    if (!racine || !racine.isConnected) return;
    var corps = racine.querySelector(".pf-corps");
    if (corps) corps.scrollTop = P.defil;
    var i = P.focus && racine.querySelector("#pf-dossier");
    if (i && document.activeElement !== i) {
      var f = P.focus;
      i.focus();
      try { i.setSelectionRange(f[0], f[1]); } catch (e) {}
    }
  }

  // ── Un dossier, dans une fiche ─────────────────────────────────────────
  // Tout l'historique du dossier ; la machine et le nombre de pesées sont
  // déjà dans la fiche, la section n'a pas de titre de dossier cliquable.
  function dossier(cible, no) {
    if (!cible || !no) return;
    var X = { etat: { champs: null }, deplies: {}, data: null, erreur: "",
              champsChanges: function () {}, titreClic: null };
    X.redessiner = function () {
      if (!cible.isConnected && X.data) return;
      var largeur = (cible.clientWidth || 640) - 30;
      cible.textContent = "";
      if (X.erreur) { cible.appendChild(el("div", "pf-erreur", X.erreur)); return; }
      if (!X.data) { cible.appendChild(el("div", "pf-vide", "Chargement des pesées…")); return; }
      var rien = true;
      (X.data.alertes || []).forEach(function (a) {
        var g = (a.dossiers || [])[0];
        if (!g) return;
        rien = false;
        var bloc = el("div", "pf-dossier-fiche");
        bloc.appendChild(boutonsChamps(a.questions, X));
        bloc.appendChild(section(a, g, largeur, X));
        cible.appendChild(bloc);
      });
      if (rien) cible.appendChild(el("div", "pf-vide", "Aucune pesée sur ce dossier."));
    };
    X.redessiner();
    fetch("/api/maintenance/alertes/pesees?no_dossier=" + encodeURIComponent(no),
          { credentials: "include", cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("Pesées indisponibles (" + r.status + ")."); return r.json(); })
      .then(function (d) { X.data = d; X.redessiner(); })
      .catch(function (e) { X.erreur = e.message || "Pesées indisponibles."; X.redessiner(); });
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
  // 3 derniers jours (tout l'historique quand un dossier est choisi).
  function adresse(e) {
    var p = { pesees: e.machine || "toutes" };
    if (e.no_dossier) p.pesees_dossier = e.no_dossier;
    var defaut = e.no_dossier ? "" : DEFAUT;
    if (e.jours !== defaut) p.pesees_periode = e.jours || "tout";
    if (e.champs && e.champs.length) p.pesees_champs = e.champs.join(",");
    return p;
  }
  function lireAdresse(u) {
    var v = u.get("pesees", null);
    if (!v || v.length > 80) return null;
    var dos = (u.get("pesees_dossier", "") || "").slice(0, 80);
    var per = u.get("pesees_periode", null, ["3", "7", "30", "90", "tout"]);
    var ch = (u.get("pesees_champs", "") || "").split(",").filter(function (c) { return /^[A-Za-z0-9_-]{1,40}$/.test(c); });
    return { machine: v === "toutes" ? "" : v, no_dossier: dos,
             jours: per === "tout" ? "" : (per || (dos ? "" : DEFAUT)), champs: ch.length ? ch : null };
  }

  global.MySifaPesees = {
    ouvrir: ouvrir, fermer: fermer, vue: vue, allerVue: allerVue, retablir: retablir, dossier: dossier,
    adresse: adresse, lireAdresse: lireAdresse,
    etat: etat,
    ouverte: function () { return !!document.getElementById("pf-overlay"); },
    surAdresse: function (fn) { if (typeof fn === "function") P.abonnes.push(fn); },
    CLES: ["pesees", "pesees_dossier", "pesees_periode", "pesees_champs"],
  };
})(window);
